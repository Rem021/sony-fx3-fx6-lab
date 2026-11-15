"""Fast dual-mode unit tests for Phase 153 — Real-Hardware Main Track Part 11:
Gate G47 (Dual-Layer `pnflasha/cnflasha` SPACC Cipher-Pairing, Per-Camera `CID`
OTP Binding & `/dev/mtd0ro` SPI-NOR Guard), Gate G48 (`p12/p13` RF Regulatory NVS
Firewall, `USB MSC 054C:0DA1` Preservation, `Off-in-Rec` `>=65°C` `100% PWM`
Thermal Override & `<=6100 mV` `EncWfiStop` Guard), and Unified 48-Gate Master
Safety Preflight (`G01..G48` / `verify-48-gates`).
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
from fx3_safety.monsoon_mishoe_cagetwist_and_40gate_guard import (
    evaluate_40gate_preflight,
)
from fx3_safety.realhw_jiritsu_cnflasha_and_44gate_guard import (
    REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
    evaluate_44gate_preflight,
)
from fx3_safety.realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import (
    ALLOWED_MTD_RO_IOCTLS,
    CANONICAL_MTD_RO_NODE,
    CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
    CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
    DEFAULT_SYNTHETIC_CAMERA_CID_SHA256,
    FAN_MODE_ALWAYS_OFF,
    FAN_MODE_AUTO1,
    FAN_MODE_OFF_IN_REC,
    FAN_OVERRIDE_FULL_PWM_PCT,
    FAN_OVERRIDE_FULL_TEMP_C,
    FAN_OVERRIDE_WARM_MIN_PWM_PCT,
    FAN_OVERRIDE_WARM_TEMP_C,
    FAN_SET_FAN_EQ_ID_CMD,
    FAN_THERMAL_ENCWFISTOP_TEMP_C,
    FORBIDDEN_MTD_IOCTLS,
    G47_GATE_CODE,
    G47_GATE_ID,
    G48_GATE_CODE,
    G48_GATE_ID,
    NPFZ100_ENCWFISTOP_MV,
    NPFZ100_ENCWFISTOP_SOC_PCT,
    NPFZ100_NEAR_END_MV,
    NPFZ100_NEAR_END_SOC_PCT,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_PHASE153_DONOR_SPECS,
    REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA,
    REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION,
    RF_NVS_PARTITIONS,
    RF_NVS_REQUIRED_MOUNT_FLAG,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH,
    STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH,
    STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE,
    STATUS_BLOCKED_G47_TELEMETRY_INVALID,
    STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM,
    STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION,
    STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION,
    STATUS_BLOCKED_G48_TELEMETRY_INVALID,
    STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_SAFE,
    STATUS_VERIFIED_G47,
    STATUS_VERIFIED_G48,
    STATUS_VERIFIED_SAFE,
    USB_MSC_RECOVERY_VID_PID,
    audit_phase153_donor_contracts,
    compute_cpapp_fan_override_pwm_pct,
    evaluate_48_master_safety_gates,
    evaluate_48gate_preflight,
    evaluate_g47_pnflasha_mtdro_vault,
    evaluate_g48_rfnvs_fan_power_guard,
    evaluate_npfz100_6100mv_encwfistop,
    main as module_cli_main,
    validate_camera_cid_binding,
    validate_dual_layer_cipher_pairing,
    validate_mtd_readonly_guard,
    verify_pnflasha_cnflasha_cid_and_mtdro_guard,
    verify_rfnvs_msc_fan_override_and_power_guard,
)
from fx3_safety.realhw_service0336_mpr_ibis_and_46gate_guard import (
    REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
    STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE,
    STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD,
    evaluate_46gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwPnflashaMtdroRfnvsAnd48GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertEqual(RF_NVS_PARTITIONS, ("p12", "p13"))
        self.assertEqual(
            REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA,
            "fx3-realhw-pnflasha-mtdro-rfnvs-48gate-preflight-v1",
        )
        self.assertEqual(REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION, "1.0.0")
        for sym in (
            "ALLOWED_MTD_RO_IOCTLS",
            "CANONICAL_MTD_RO_NODE",
            "CIPHER_DOMAIN_RAW_PNFLASHA_ISP",
            "CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL",
            "DEFAULT_SYNTHETIC_CAMERA_CID_SHA256",
            "FAN_OVERRIDE_FULL_PWM_PCT",
            "FAN_OVERRIDE_FULL_TEMP_C",
            "FAN_OVERRIDE_WARM_MIN_PWM_PCT",
            "FAN_OVERRIDE_WARM_TEMP_C",
            "FAN_SET_FAN_EQ_ID_CMD",
            "FAN_THERMAL_ENCWFISTOP_TEMP_C",
            "FORBIDDEN_FALSE_DCIN_ALARM_VOLTAGES_V",
            "FORBIDDEN_MTD_IOCTLS",
            "G47_GATE_ID",
            "G47_GATE_CODE",
            "G48_GATE_ID",
            "G48_GATE_CODE",
            "NPFZ100_ENCWFISTOP_MV",
            "NPFZ100_ENCWFISTOP_SOC_PCT",
            "NPFZ100_NEAR_END_MV",
            "NPFZ100_NEAR_END_SOC_PCT",
            "PINNED_PHASE153_DONOR_SPECS",
            "REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA",
            "REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION",
            "RF_NVS_PARTITIONS",
            "RF_NVS_REQUIRED_MOUNT_FLAG",
            "SAFE_REALHW_FAN_MODES",
            "SPI_NOR_WRITE_AUTHORIZED",
            "STATUS_VERIFIED_G47",
            "STATUS_VERIFIED_G48",
            "STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH",
            "STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH",
            "STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE",
            "STATUS_BLOCKED_G47_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION",
            "STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE",
            "STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION",
            "STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM",
            "STATUS_BLOCKED_G48_TELEMETRY_INVALID",
            "USB_MSC_RECOVERY_VID_PID",
            "VALID_CIPHER_DOMAINS",
            "Phase153DonorAuditResult",
            "PnflashaMtdroVaultGuardResult",
            "RfnvsMscFanPowerGuardResult",
            "G47PnflashaMtdroVaultResult",
            "G48RfnvsFanPowerGuardResult",
            "Master48GateReport",
            "audit_phase153_donor_contracts",
            "validate_dual_layer_cipher_pairing",
            "validate_camera_cid_binding",
            "validate_mtd_readonly_guard",
            "compute_cpapp_fan_override_pwm_pct",
            "evaluate_npfz100_6100mv_encwfistop",
            "verify_pnflasha_cnflasha_cid_and_mtdro_guard",
            "verify_rfnvs_msc_fan_override_and_power_guard",
            "evaluate_g47_pnflasha_mtdro_vault",
            "evaluate_g48_rfnvs_fan_power_guard",
            "evaluate_48gate_preflight",
            "evaluate_48_master_safety_gates",
            "realhw_pnflasha_mtdro_rfnvs_and_48gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

        # Prior Phase exports must remain completely intact (zero collision)
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(
            fx3_safety.REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
            REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
        )
        self.assertEqual(
            fx3_safety.REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
            REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase153_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertTrue(res_default.sencore_mpr_contracts_verified)
        self.assertTrue(res_default.im_elf_contracts_verified)
        self.assertTrue(res_default.cpapp_backup_contracts_verified)
        self.assertEqual(res_default.missing_markers, ())

        if res_default.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res_default.files_inspected, 5)
            self.assertGreaterEqual(len(observed_flags), 5)
            for _path, flags in observed_flags:
                self.assertEqual(flags & 3, os.O_RDONLY)
        else:
            self.assertEqual(res_default.files_inspected, 0)

        res_clean = audit_phase153_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 5)

        with tempfile.TemporaryDirectory() as missing_dir:
            res_missing = audit_phase153_donor_contracts(
                work_root=Path(missing_dir), force_clean_room=False
            )
            self.assertTrue(res_missing.valid)
            self.assertEqual(res_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_donor_audit_integrity_mismatch_and_missing_marker_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for _key, (
                _body,
                rel_path,
                _sz,
                _sha,
                _toks,
                _lbl,
            ) in PINNED_PHASE153_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"corrupted-phase153-donor")
            res = audit_phase153_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(res.sencore_mpr_contracts_verified)
        self.assertFalse(res.im_elf_contracts_verified)
        self.assertFalse(res.cpapp_backup_contracts_verified)
        self.assertEqual(len(res.missing_markers), 5)

    def test_04_donor_audit_pinned_hashes_sizes_and_zero_raw_bytes(self) -> None:
        for forced in (False, True):
            res = audit_phase153_donor_contracts(force_clean_room=forced)
            self.assertTrue(res.valid)
            for key, (_body, _rel, exp_sz, exp_sha, _toks, _lbl) in PINNED_PHASE153_DONOR_SPECS.items():
                self.assertEqual(res.bytes_by_artifact[key], exp_sz)
                self.assertEqual(res.sha256_by_artifact[key], exp_sha)
            rendered = json.dumps(res.to_dict(), ensure_ascii=False)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    # --- 2. Pure Helper Functions ---

    def test_05_helper_validate_dual_layer_cipher_pairing(self) -> None:
        self.assertTrue(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "/dev/cnflasha15",
                "/dev/cnflasha15",
            )
        )
        self.assertTrue(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                "/dev/pnflasha15",
                "/dev/pnflasha15",
            )
        )
        # Cross-domain forbidden
        self.assertFalse(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                "/dev/cnflasha15",
                "/dev/pnflasha15",
            )
        )
        self.assertFalse(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "/dev/pnflasha15",
                "/dev/cnflasha15",
            )
        )
        # Device prefix mismatch
        self.assertFalse(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "/dev/pnflasha15",
                "/dev/cnflasha15",
            )
        )
        self.assertFalse(
            validate_dual_layer_cipher_pairing(
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                "/dev/pnflasha15",
                "/dev/cnflasha15",
            )
        )
        self.assertFalse(validate_dual_layer_cipher_pairing("UNKNOWN", "UNKNOWN"))

    def test_06_helper_validate_camera_cid_binding(self) -> None:
        cid_a = "a" * 64
        cid_b = "b" * 64
        self.assertTrue(validate_camera_cid_binding(cid_a, cid_a))
        self.assertTrue(validate_camera_cid_binding(cid_a.upper(), cid_a))
        self.assertFalse(validate_camera_cid_binding(cid_a, cid_b))
        self.assertFalse(validate_camera_cid_binding("short", "short"))
        self.assertFalse(validate_camera_cid_binding("g" * 64, "g" * 64))
        self.assertFalse(validate_camera_cid_binding(123, cid_a))  # type: ignore[arg-type]

    def test_07_helper_validate_mtd_readonly_guard(self) -> None:
        self.assertTrue(validate_mtd_readonly_guard("/dev/mtd0ro", "O_RDONLY", ("MEMGETINFO",)))
        self.assertTrue(validate_mtd_readonly_guard("/dev/mtd1ro", "O_RDONLY", ALLOWED_MTD_RO_IOCTLS))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0", "O_RDONLY", ("MEMGETINFO",)))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtdblock0", "O_RDONLY", ("MEMGETINFO",)))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0ro", "O_RDWR", ("MEMGETINFO",)))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0ro", "O_WRONLY", ()))
        for ioctl_bad in FORBIDDEN_MTD_IOCTLS:
            self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0ro", "O_RDONLY", (ioctl_bad,)))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0ro", "O_RDONLY", ("UNKNOWN_IOCTL",)))
        self.assertFalse(validate_mtd_readonly_guard("/dev/mtd0ro", "O_RDONLY", "MEMGETINFO"))  # type: ignore[arg-type]

    def test_08_helper_compute_cpapp_fan_override_pwm_pct(self) -> None:
        self.assertEqual(compute_cpapp_fan_override_pwm_pct(FAN_MODE_OFF_IN_REC, 45.0), (0.0, False))
        self.assertEqual(compute_cpapp_fan_override_pwm_pct(FAN_MODE_AUTO1, 45.0), (25.0, False))
        self.assertEqual(
            compute_cpapp_fan_override_pwm_pct(FAN_MODE_OFF_IN_REC, FAN_OVERRIDE_WARM_TEMP_C),
            (FAN_OVERRIDE_WARM_MIN_PWM_PCT, False),
        )
        self.assertEqual(
            compute_cpapp_fan_override_pwm_pct(FAN_MODE_OFF_IN_REC, FAN_OVERRIDE_FULL_TEMP_C),
            (FAN_OVERRIDE_FULL_PWM_PCT, False),
        )
        self.assertEqual(
            compute_cpapp_fan_override_pwm_pct(FAN_MODE_OFF_IN_REC, FAN_THERMAL_ENCWFISTOP_TEMP_C),
            (FAN_OVERRIDE_FULL_PWM_PCT, True),
        )
        with self.assertRaises(ValueError):
            compute_cpapp_fan_override_pwm_pct(FAN_MODE_ALWAYS_OFF, 30.0)
        with self.assertRaises(ValueError):
            compute_cpapp_fan_override_pwm_pct(FAN_MODE_OFF_IN_REC, float("nan"))

    def test_09_helper_evaluate_npfz100_6100mv_encwfistop(self) -> None:
        self.assertEqual(evaluate_npfz100_6100mv_encwfistop(7600.0, 85.0), "NOMINAL")
        self.assertEqual(evaluate_npfz100_6100mv_encwfistop(NPFZ100_NEAR_END_MV, 10.0), "NEAR_END")
        self.assertEqual(evaluate_npfz100_6100mv_encwfistop(6600.0, NPFZ100_NEAR_END_SOC_PCT), "NEAR_END")
        self.assertEqual(evaluate_npfz100_6100mv_encwfistop(NPFZ100_ENCWFISTOP_MV, 10.0), "ENC_WFI_STOP")
        self.assertEqual(evaluate_npfz100_6100mv_encwfistop(6400.0, NPFZ100_ENCWFISTOP_SOC_PCT), "ENC_WFI_STOP")
        self.assertEqual(
            evaluate_npfz100_6100mv_encwfistop(6000.0, 1.0, usb_pd_attached=True),
            "USB_PD_ASSISTED",
        )
        with self.assertRaises(ValueError):
            evaluate_npfz100_6100mv_encwfistop(0.0, 50.0)
        with self.assertRaises(ValueError):
            evaluate_npfz100_6100mv_encwfistop(7200.0, 101.0)

    # --- 3. Gate G47 Unit & Fault-Injection Tests ---

    def test_10_g47_default_safe_cnflasha_profile_passes(self) -> None:
        res = verify_pnflasha_cnflasha_cid_and_mtdro_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.backup_cipher_domain, CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL)
        self.assertEqual(res.restore_target_domain, CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL)
        self.assertEqual(res.mtd_device_node, CANONICAL_MTD_RO_NODE)
        self.assertTrue(res.cipher_pairing_safe)
        self.assertTrue(res.camera_cid_binding_safe)
        self.assertTrue(res.mtd_readonly_guard_safe)
        self.assertFalse(res.spi_nor_write_authorized)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_11_g47_same_body_raw_pnflasha_isp_passes_with_warning(self) -> None:
        res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            backup_cipher_domain=CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
            restore_target_domain=CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
            source_block_device="/dev/pnflasha15",
            target_block_device="/dev/pnflasha15",
            backup_camera_cid_sha256="b" * 64,
            target_camera_cid_sha256="b" * 64,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertGreaterEqual(len(res.warnings), 1)
        self.assertFalse(res.spi_nor_write_authorized)

    def test_12_g47_blocks_cross_domain_cipher_pairing(self) -> None:
        for kw in (
            {
                "backup_cipher_domain": CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "restore_target_domain": CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                "source_block_device": "/dev/cnflasha15",
                "target_block_device": "/dev/pnflasha15",
            },
            {
                "backup_cipher_domain": CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                "restore_target_domain": CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "source_block_device": "/dev/pnflasha15",
                "target_block_device": "/dev/cnflasha15",
            },
            {
                "backup_cipher_domain": CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "restore_target_domain": CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                "source_block_device": "/dev/pnflasha15",
                "target_block_device": "/dev/cnflasha15",
            },
        ):
            res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.cipher_pairing_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH)

    def test_13_g47_blocks_mismatched_camera_cid_otp_key(self) -> None:
        res_mismatch = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            backup_cipher_domain=CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
            restore_target_domain=CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
            source_block_device="/dev/pnflasha15",
            target_block_device="/dev/pnflasha15",
            backup_camera_cid_sha256="a" * 64,
            target_camera_cid_sha256="c" * 64,
        )
        self.assertFalse(res_mismatch.valid)
        self.assertFalse(res_mismatch.camera_cid_binding_safe)
        self.assertEqual(res_mismatch.status, STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH)

        res_unverified = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            cid_otp_key_binding_verified=False
        )
        self.assertFalse(res_unverified.valid)
        self.assertFalse(res_unverified.camera_cid_binding_safe)
        self.assertEqual(res_unverified.status, STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH)

    def test_14_g47_blocks_non_ro_mtd_node_and_open_modes(self) -> None:
        for kw in (
            {"mtd_device_node": "/dev/mtd0"},
            {"mtd_device_node": "/dev/mtdblock0"},
            {"mtd_open_mode": "O_RDWR"},
            {"mtd_open_mode": "O_WRONLY"},
            {"spi_nor_write_attempts_blocked": False},
            {"spi_nor_mutation_bytes": 4},
            {"request_spi_nor_writes": True},
        ):
            res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.mtd_readonly_guard_safe)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertEqual(res.status, STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE)

    def test_15_g47_blocks_memerase_and_memwriteoob_ioctls(self) -> None:
        for ioctl_name in ("MEMERASE", "MEMERASE64", "MEMWRITEOOB", "MEMWRITEOOB64", "MEMWRITE"):
            res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
                requested_mtd_ioctls=("MEMGETINFO", ioctl_name)
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.mtd_readonly_guard_safe)
            self.assertIn(ioctl_name, res.forbidden_mtd_ioctls_detected)
            self.assertEqual(res.status, STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE)

    def test_16_g47_blocks_invalid_telemetry_and_emmc_redline(self) -> None:
        for kw in (
            {"backup_cipher_domain": ""},
            {"backup_camera_cid_sha256": "not-a-sha256"},
            {"requested_mtd_ioctls": "MEMGETINFO"},
            {"spi_nor_mutation_bytes": -1},
        ):
            res = verify_pnflasha_cnflasha_cid_and_mtdro_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G47_TELEMETRY_INVALID, res.violation_codes)

        res_emmc = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    # --- 4. Gate G48 Unit & Fault-Injection Tests ---

    def test_17_g48_default_safe_profile_passes(self) -> None:
        res = verify_rfnvs_msc_fan_override_and_power_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.p12_mount_flags, RF_NVS_REQUIRED_MOUNT_FLAG)
        self.assertEqual(res.p13_mount_flags, RF_NVS_REQUIRED_MOUNT_FLAG)
        self.assertEqual(res.rf_nvs_mutation_bytes, 0)
        self.assertEqual(res.usb_msc_recovery_vid_pid, USB_MSC_RECOVERY_VID_PID)
        self.assertEqual(res.fan_mode, FAN_MODE_OFF_IN_REC)
        self.assertEqual(res.set_fan_eq_id_cmd, FAN_SET_FAN_EQ_ID_CMD)
        self.assertAlmostEqual(res.sensor_temp_c, 65.0)
        self.assertAlmostEqual(res.fan_pwm_pct, 100.0)
        self.assertAlmostEqual(res.expected_min_pwm_pct, 100.0)
        self.assertTrue(res.rf_nvs_lock_safe)
        self.assertTrue(res.usb_msc_0da1_safe)
        self.assertTrue(res.fan_thermal_override_safe)
        self.assertTrue(res.battery_6100mv_encwfistop_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_18_g48_blocks_p12_p13_rf_nvs_rw_or_mutation_or_mac_regdomain(self) -> None:
        for kw in (
            {"p12_mount_flags": "MS_RDWR"},
            {"p13_mount_flags": "rw,relatime"},
            {"p12_device_node": "/dev/nflasha15"},
            {"p13_device_node": "/dev/nflasha15"},
            {"rf_nvs_write_attempts_blocked": False},
            {"rf_nvs_mutation_bytes": 16},
            {"rf_nvs_writes_requested": 1},
            {"mac_address_override_attempted": True},
            {"regdomain_override_attempted": True},
        ):
            res = verify_rfnvs_msc_fan_override_and_power_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.rf_nvs_lock_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION)

    def test_19_g48_blocks_usb_msc_0da1_unreachable_or_phy_masked_or_spoofed(self) -> None:
        for kw in (
            {"usb_msc_recovery_vid_pid": "054C:0994"},
            {"usb_msc_0da1_reachable": False},
            {"usb_phy_disabled_or_masked": True},
            {"usb_descriptor_spoofed": True},
        ):
            res = verify_rfnvs_msc_fan_override_and_power_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.usb_msc_0da1_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE)

    def test_20_g48_enforces_off_in_rec_58c_65c_72c_fan_override_and_rejects_always_off(self) -> None:
        ok_warm = verify_rfnvs_msc_fan_override_and_power_guard(
            fan_mode=FAN_MODE_OFF_IN_REC, sensor_temp_c=58.0, fan_pwm_pct=45.0
        )
        self.assertTrue(ok_warm.valid)
        self.assertAlmostEqual(ok_warm.expected_min_pwm_pct, 45.0)

        ok_hot = verify_rfnvs_msc_fan_override_and_power_guard(
            fan_mode=FAN_MODE_OFF_IN_REC,
            sensor_temp_c=72.0,
            fan_pwm_pct=100.0,
            thermal_encwfistop_triggered=True,
        )
        self.assertTrue(ok_hot.valid)

        for kw in (
            {"fan_mode": FAN_MODE_ALWAYS_OFF, "sensor_temp_c": 35.0, "fan_pwm_pct": 0.0},
            {"fan_mode": FAN_MODE_OFF_IN_REC, "sensor_temp_c": 58.0, "fan_pwm_pct": 44.0},
            {"fan_mode": FAN_MODE_OFF_IN_REC, "sensor_temp_c": 65.0, "fan_pwm_pct": 99.0},
            {
                "fan_mode": FAN_MODE_OFF_IN_REC,
                "sensor_temp_c": 72.0,
                "fan_pwm_pct": 100.0,
                "thermal_encwfistop_triggered": False,
            },
            {"stock_cp_thermal_override_masked": True},
            {"set_fan_eq_id_cmd": "UNKNOWN_FAN_CMD"},
        ):
            res = verify_rfnvs_msc_fan_override_and_power_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.fan_thermal_override_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION)

    def test_21_g48_enforces_6100mv_encwfistop_and_zero_false_19v5_dcin_alarms(self) -> None:
        ok_wfi = verify_rfnvs_msc_fan_override_and_power_guard(
            battery_mv=6100.0, battery_soc_pct=2.0, batt_encwfistop_triggered=True
        )
        self.assertTrue(ok_wfi.valid)
        self.assertEqual(ok_wfi.batt_power_state, "ENC_WFI_STOP")

        ok_near = verify_rfnvs_msc_fan_override_and_power_guard(
            battery_mv=6350.0, battery_soc_pct=5.0
        )
        self.assertTrue(ok_near.valid)
        self.assertEqual(ok_near.batt_power_state, "NEAR_END")
        self.assertGreaterEqual(len(ok_near.warnings), 1)

        for kw in (
            {"battery_mv": 6100.0, "battery_soc_pct": 2.0, "batt_encwfistop_triggered": False},
            {"battery_mv": 6050.0, "battery_soc_pct": 1.5, "batt_encwfistop_triggered": False},
            {"battery_mv": 6400.0, "battery_soc_pct": 2.0, "batt_encwfistop_triggered": False},
            {"false_19v5_dcin_alarms": 1},
            {"dcin_18v_19v5_comparator_masked": False},
            {"rsv_orphan_risk": True},
        ):
            res = verify_rfnvs_msc_fan_override_and_power_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.battery_6100mv_encwfistop_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM)

    def test_22_g48_usb_pd_assisted_avoids_batt_wfi_requirement(self) -> None:
        res = verify_rfnvs_msc_fan_override_and_power_guard(
            battery_mv=6100.0,
            battery_soc_pct=2.0,
            usb_pd_attached=True,
            batt_encwfistop_triggered=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.batt_power_state, "USB_PD_ASSISTED")

    def test_23_g48_blocks_invalid_telemetry_and_emmc_redline(self) -> None:
        for kw in (
            {"p12_mount_flags": ""},
            {"rf_nvs_mutation_bytes": -1},
            {"false_19v5_dcin_alarms": -2},
            {"sensor_temp_c": float("nan")},
            {"fan_pwm_pct": 105.0},
            {"battery_mv": 0.0},
            {"battery_soc_pct": 101.0},
        ):
            res = verify_rfnvs_msc_fan_override_and_power_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G48_TELEMETRY_INVALID, res.violation_codes)

        res_emmc = verify_rfnvs_msc_fan_override_and_power_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    # --- 5. Gate G47/G48 Evaluators & Master 48-Gate Preflight ---

    def test_24_evaluate_g47_and_g48_dual_mode_verdicts(self) -> None:
        for forced in (True, False):
            v47, r47 = evaluate_g47_pnflasha_mtdro_vault(force_clean_room=forced)
            self.assertTrue(v47.passed)
            self.assertTrue(r47.valid)
            self.assertEqual(v47.gate_id, G47_GATE_ID)
            self.assertEqual(v47.gate_code, G47_GATE_CODE)
            self.assertEqual(v47.status, STATUS_VERIFIED_G47)
            self.assertFalse(r47.spi_nor_write_authorized)
            self.assertFalse(r47.persistent_emmc_writes_authorized)

            v48, r48 = evaluate_g48_rfnvs_fan_power_guard(force_clean_room=forced)
            self.assertTrue(v48.passed)
            self.assertTrue(r48.valid)
            self.assertEqual(v48.gate_id, G48_GATE_ID)
            self.assertEqual(v48.gate_code, G48_GATE_CODE)
            self.assertEqual(v48.status, STATUS_VERIFIED_G48)
            self.assertFalse(r48.persistent_emmc_writes_authorized)

    def test_25_master_48gate_offline_mode_45_of_48(self) -> None:
        rep = evaluate_48gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA)
        self.assertEqual(rep.version, REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_VERSION)
        self.assertEqual(len(rep.gates), 48)
        self.assertEqual(rep.summary["total_gates"], 48)
        self.assertEqual(rep.summary["verified_gates"], 45)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g46_verified"], 34)
        self.assertEqual(rep.summary["g47_to_g48_verified"], 2)
        self.assertTrue(rep.offline_45_gates_verified)
        self.assertFalse(rep.all_48_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_45_OF_48_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)
        self.assertTrue(rep.gates[46]["passed"])
        self.assertEqual(rep.gates[46]["gate_id"], G47_GATE_ID)
        self.assertTrue(rep.gates[47]["passed"])
        self.assertEqual(rep.gates[47]["gate_id"], G48_GATE_ID)

    def test_26_master_48gate_dry_run_simulated_backup_48_of_48(self) -> None:
        rep = evaluate_48gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 48)
        self.assertEqual(rep.summary["verified_gates"], 48)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_45_gates_verified)
        self.assertTrue(rep.all_48_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_48_GATES_DRY_RUN_SIMULATED_BACKUP")
        for g in rep.gates:
            self.assertTrue(g["passed"], f"Gate {g['gate_id']} failed: {g['status']}")

    def test_27_48gate_propagates_g47_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {
                    "backup_cipher_domain": CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
                    "restore_target_domain": CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
                    "source_block_device": "/dev/cnflasha15",
                    "target_block_device": "/dev/pnflasha15",
                },
                STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH,
            ),
            (
                {
                    "backup_camera_cid_sha256": "a" * 64,
                    "target_camera_cid_sha256": "f" * 64,
                },
                STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH,
            ),
            (
                {"mtd_device_node": "/dev/mtd0"},
                STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE,
            ),
            (
                {"requested_mtd_ioctls": ("MEMERASE",)},
                STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE,
            ),
        ):
            rep = evaluate_48gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                pnflasha_mtdro_kwargs=kwargs,
            )
            self.assertFalse(rep.all_48_gates_verified)
            self.assertFalse(rep.offline_45_gates_verified)
            self.assertFalse(rep.g47_to_g48_all_passed)
            self.assertFalse(rep.gates[46]["passed"])
            self.assertEqual(rep.gates[46]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_28_48gate_propagates_g48_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {"p12_mount_flags": "MS_RDWR"},
                STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION,
            ),
            (
                {"usb_msc_0da1_reachable": False},
                STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE,
            ),
            (
                {"fan_mode": FAN_MODE_OFF_IN_REC, "sensor_temp_c": 65.0, "fan_pwm_pct": 80.0},
                STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION,
            ),
            (
                {"battery_mv": 6100.0, "battery_soc_pct": 2.0, "batt_encwfistop_triggered": False},
                STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM,
            ),
            (
                {"false_19v5_dcin_alarms": 1},
                STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM,
            ),
        ):
            rep = evaluate_48gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                rfnvs_fan_power_kwargs=kwargs,
            )
            self.assertFalse(rep.all_48_gates_verified)
            self.assertFalse(rep.offline_45_gates_verified)
            self.assertFalse(rep.g47_to_g48_all_passed)
            self.assertFalse(rep.gates[47]["passed"])
            self.assertEqual(rep.gates[47]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_29_48gate_propagates_g45_g46_and_emmc_redline(self) -> None:
        rep_45_46 = evaluate_48gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            service_0336_canary_kwargs={
                "op_ff_canary_executed_before_op_00": False,
                "op_00_frame_queued": True,
            },
            stageb_mpr_ibis_p18_kwargs={"ibis_floating_coil_fault": True},
        )
        self.assertFalse(rep_45_46.all_48_gates_verified)
        self.assertFalse(rep_45_46.gates[44]["passed"])
        self.assertFalse(rep_45_46.gates[45]["passed"])
        self.assertEqual(
            rep_45_46.gates[44]["status"],
            STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE,
        )
        self.assertEqual(
            rep_45_46.gates[45]["status"],
            STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD,
        )
        self.assertEqual(rep_45_46.status, STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE)

        for emmc_kw in (
            {"request_persistent_emmc_writes": True},
            {"pnflasha_mtdro_kwargs": {"request_persistent_emmc_writes": True}},
            {"rfnvs_fan_power_kwargs": {"request_persistent_emmc_writes": True}},
        ):
            rep_emmc = evaluate_48gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                **emmc_kw,
            )
            self.assertFalse(rep_emmc.all_48_gates_verified)
            self.assertFalse(rep_emmc.offline_45_gates_verified)
            self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
            self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
            self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_30_donor_corruption_propagates_to_g47_g48_and_48gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for _key, (
                _body,
                rel_path,
                _sz,
                _sha,
                _toks,
                _lbl,
            ) in PINNED_PHASE153_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"corrupted")
            v47, r47 = evaluate_g47_pnflasha_mtdro_vault(
                work_root=tmp, force_clean_room=False
            )
            v48, r48 = evaluate_g48_rfnvs_fan_power_guard(
                work_root=tmp, force_clean_room=False
            )
            rep = evaluate_48gate_preflight(
                DEFAULT_REPO_ROOT,
                work_root=tmp,
                force_clean_room=False,
                dry_run_simulated_backup=True,
            )
        self.assertFalse(v47.passed)
        self.assertFalse(r47.valid)
        self.assertEqual(v47.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v48.passed)
        self.assertFalse(r48.valid)
        self.assertEqual(v48.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(rep.all_48_gates_verified)
        self.assertFalse(rep.gates[46]["passed"])
        self.assertFalse(rep.gates[47]["passed"])

    def test_31_h0_h1_trial_entry_allowed_and_g13_to_g48_flags(self) -> None:
        rep_off = evaluate_48gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g48_all_passed)
        self.assertTrue(rep_off.g47_to_g48_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_48gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            pnflasha_mtdro_kwargs={"mtd_device_node": "/dev/mtd0"},
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g48_all_passed)
        self.assertFalse(rep_bad.offline_45_gates_verified)

    def test_32_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        for forced in (True, False):
            rep = evaluate_48gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=forced,
                dry_run_simulated_backup=True,
            )
            rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    # --- 6. CLI & Backward-Compatibility Tests ---

    def test_33_cli_verify_g47_pnflasha_mtdro_vault_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g47-pnflasha-mtdro-vault", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G47_GATE_ID}", out)
        self.assertIn("mtd=/dev/mtd0ro(O_RDONLY)", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g47-pnflasha-mtdro-vault", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G47)
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_34_cli_verify_g48_rfnvs_fan_power_guard_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g48-rfnvs-fan-power-guard", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G48_GATE_ID}", out)
        self.assertIn("p12_flags=MS_RDONLY", out)
        self.assertIn("rf_mut=0B", out)
        self.assertIn("msc=054C:0DA1", out)
        self.assertIn("fan=100%@65C", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g48-rfnvs-fan-power-guard", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G48)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_35_cli_verify_48_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-48-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 45)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["spi_nor_write_authorized"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-48-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 48)
        self.assertTrue(p_dry["all_48_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["spi_nor_write_authorized"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_36_cli_verify_48_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=45/48", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-48-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=45/48", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-48-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_37_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_PNFLASHA_MTDRO_RFNVS_48GATE_SCHEMA)
        self.assertTrue(payload["all_48_gates_verified"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_38_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_48gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_45_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_39_evaluate_48_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_48_master_safety_gates, evaluate_48gate_preflight)
        rep = evaluate_48_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_48_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 48)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_40_prior_cli_subcommands_verify_16_through_46_remain_intact(self) -> None:
        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
            "verify-28-gates",
            "verify-30-gates",
            "verify-32-gates",
            "verify-34-gates",
            "verify-36-gates",
            "verify-38-gates",
            "verify-40-gates",
            "verify-42-gates",
            "verify-44-gates",
            "verify-46-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")

    def test_41_backward_compatibility_40_44_46_reports_unmodified(self) -> None:
        r40 = evaluate_40gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(r40.gates), 40)
        self.assertEqual(r40.summary["verified_gates"], 37)
        self.assertTrue(r40.offline_37_gates_verified)
        self.assertFalse(r40.persistent_emmc_writes_authorized)

        r44 = evaluate_44gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(r44.gates), 44)
        self.assertEqual(r44.summary["verified_gates"], 41)
        self.assertTrue(r44.offline_41_gates_verified)
        self.assertFalse(r44.persistent_emmc_writes_authorized)

        r46 = evaluate_46gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(r46.gates), 46)
        self.assertEqual(r46.summary["verified_gates"], 43)
        self.assertTrue(r46.offline_43_gates_verified)
        self.assertFalse(r46.persistent_emmc_writes_authorized)

    def test_42_g47_boundary_values_exact_cid_and_mtd_node_variants(self) -> None:
        ok = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            mtd_device_node="/dev/mtd2ro",
            mtd_open_mode="O_RDONLY",
            requested_mtd_ioctls=ALLOWED_MTD_RO_IOCTLS,
            backup_camera_cid_sha256="0123456789abcdef" * 4,
            target_camera_cid_sha256=("0123456789ABCDEF" * 4),
        )
        self.assertTrue(ok.valid)

        bad_otp = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            requested_mtd_ioctls=("OTPLOCK",)
        )
        self.assertFalse(bad_otp.valid)
        self.assertEqual(bad_otp.status, STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE)

    def test_43_g48_boundary_values_exact_fan_and_battery_thresholds(self) -> None:
        ok_below_warm = verify_rfnvs_msc_fan_override_and_power_guard(
            fan_mode=FAN_MODE_OFF_IN_REC,
            sensor_temp_c=57.9,
            fan_pwm_pct=0.0,
            battery_mv=6101.0,
            battery_soc_pct=2.1,
            batt_encwfistop_triggered=False,
        )
        self.assertTrue(ok_below_warm.valid)
        self.assertEqual(ok_below_warm.batt_power_state, "NEAR_END")

        ok_65c = verify_rfnvs_msc_fan_override_and_power_guard(
            fan_mode=FAN_MODE_OFF_IN_REC,
            sensor_temp_c=65.0,
            fan_pwm_pct=100.0,
        )
        self.assertTrue(ok_65c.valid)

        bad_65c = verify_rfnvs_msc_fan_override_and_power_guard(
            fan_mode=FAN_MODE_OFF_IN_REC,
            sensor_temp_c=65.0,
            fan_pwm_pct=99.9,
        )
        self.assertFalse(bad_65c.valid)
        self.assertEqual(bad_65c.status, STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION)

    def test_44_g48_allows_ro_flag_variations_and_blocks_combined_rw(self) -> None:
        ok_flags = verify_rfnvs_msc_fan_override_and_power_guard(
            p12_device_node="/dev/cnflasha12",
            p13_device_node="/dev/cnflasha13",
            p12_mount_flags="MS_RDONLY,MS_NOSUID",
            p13_mount_flags="MS_RDONLY|MS_NOATIME",
        )
        self.assertTrue(ok_flags.valid)

        bad_combo = verify_rfnvs_msc_fan_override_and_power_guard(
            p12_mount_flags="MS_RDONLY,RW"
        )
        self.assertFalse(bad_combo.valid)
        self.assertEqual(bad_combo.status, STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION)

    def test_45_g47_g48_multi_fault_accumulation_records_all_violation_codes(self) -> None:
        bad_g47 = verify_pnflasha_cnflasha_cid_and_mtdro_guard(
            backup_cipher_domain=CIPHER_DOMAIN_SPACC_CNFLASHA_LOGICAL,
            restore_target_domain=CIPHER_DOMAIN_RAW_PNFLASHA_ISP,
            backup_camera_cid_sha256="a" * 64,
            target_camera_cid_sha256="b" * 64,
            mtd_device_node="/dev/mtd0",
            requested_mtd_ioctls=("MEMERASE",),
        )
        self.assertFalse(bad_g47.valid)
        self.assertIn(STATUS_BLOCKED_G47_CROSS_DOMAIN_CIPHER_MISMATCH, bad_g47.violation_codes)
        self.assertIn(STATUS_BLOCKED_G47_CAMERA_CID_OTP_KEY_MISMATCH, bad_g47.violation_codes)
        self.assertIn(STATUS_BLOCKED_G47_MTD_NON_RO_OR_IOCTL_WRITE, bad_g47.violation_codes)

        bad_g48 = verify_rfnvs_msc_fan_override_and_power_guard(
            p12_mount_flags="MS_RDWR",
            usb_msc_0da1_reachable=False,
            fan_mode=FAN_MODE_ALWAYS_OFF,
            battery_mv=6100.0,
            batt_encwfistop_triggered=False,
        )
        self.assertFalse(bad_g48.valid)
        self.assertIn(STATUS_BLOCKED_G48_RF_NVS_OR_MAC_MUTATION, bad_g48.violation_codes)
        self.assertIn(STATUS_BLOCKED_G48_USB_MSC_0DA1_UNREACHABLE, bad_g48.violation_codes)
        self.assertIn(STATUS_BLOCKED_G48_FAN_THERMAL_OVERRIDE_VIOLATION, bad_g48.violation_codes)
        self.assertIn(STATUS_BLOCKED_G48_BATT_6100MV_OR_FALSE_DCIN_ALARM, bad_g48.violation_codes)

    def test_46_48gate_report_nested_subreports_present_and_consistent(self) -> None:
        rep = evaluate_48gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(rep.master_46_report["schema"], REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA)
        self.assertEqual(rep.g47_result["status"], STATUS_VERIFIED_G47)
        self.assertEqual(rep.g48_result["status"], STATUS_VERIFIED_G48)
        self.assertFalse(rep.g47_result["spi_nor_write_authorized"])
        self.assertFalse(rep.g47_result["persistent_emmc_writes_authorized"])
        self.assertFalse(rep.g48_result["persistent_emmc_writes_authorized"])


if __name__ == "__main__":
    unittest.main()
