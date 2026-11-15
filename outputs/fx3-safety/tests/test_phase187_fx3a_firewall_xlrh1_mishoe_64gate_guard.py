"""Fast dual-mode unit tests for Phase 187 — Real-Hardware Main Track Part 19:
Gate G63 (`ILME-FX3` vs `ILME-FX3A` LCD/NFC/IR Hardware-Branch Firewall &
`BODYDATA.DAT` / `CAMSET` Cross-Branch Isolation),
Gate G64 (`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Digital Audio Routing vs Body `3.5mm`
Jack Physical Override, `S&Q` Mute Consistency, `+48V` Stage-Handoff Glitch &
Fake Standalone USB Payload Guard),
and 64-Gate Master Preflight (`G01..G64` / `verify-64-gates`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
    evaluate_58gate_preflight,
)
from fx3_safety.realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
    STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
    evaluate_60gate_preflight,
)
from fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
    STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
    evaluate_62gate_preflight,
)
from fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX30_BRANCH_NAME,
    FX30_MODEL_ID,
    FX30_MODEL_ID_HEX,
    FX30_MODEL_NAME,
    FX3A_BRANCH_NAME,
    FX3A_FIRMWARE_VERSION_202,
    FX3A_HW_REVISION_2025,
    FX3A_MODEL_NAME,
    FX3A_XGA_LCD_DOT_COUNT,
    FX3A_XGA_LCD_PANEL_SPEC,
    FX3_BRANCH_NAME,
    FX3_FAIL_CLOSED_MAX_LATENCY_US,
    FX3_LCD_DOT_COUNT,
    FX3_LCD_PANEL_SPEC,
    FX3_MIN_BRANCH_MAJOR,
    FX3_MODEL_ID,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_NAME,
    FX3_ORIGINAL_HW_REVISION,
    FX3_TARGET_FIRMWARE_VERSION,
    G63,
    G63_GATE_CODE,
    G63_GATE_ID,
    G64,
    G64_GATE_CODE,
    G64_GATE_ID,
    GATE_G63_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL,
    GATE_G64_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE187_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_SCHEMA,
    REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_VERSION,
    REJECTED_CROSS_BRANCH_MODELS,
    REJECTED_CROSS_BRANCH_MODEL_IDS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X,
    STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT,
    STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
    STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH,
    STATUS_BLOCKED_G63_TELEMETRY_INVALID,
    STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
    STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD,
    STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH,
    STATUS_BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY,
    STATUS_BLOCKED_G64_TELEMETRY_INVALID,
    STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G63,
    STATUS_VERIFIED_G64,
    STATUS_VERIFIED_SAFE,
    XLRH1_AUDIO_SAMPLE_RATE_HZ,
    XLRH1_DEFAULT_FORMAT_MODE,
    XLRH1_EXPECTED_IN1_IN2_ROUTE,
    XLRH1_EXPECTED_IN3_ROUTE,
    XLRH1_HANDLE_MODEL,
    XLRH1_HEADPHONE_MONITOR_MATRICES,
    XLRH1_POST_BODYDATA_RESET_DEFAULT,
    XLRH1_VALID_AUDIO_PROFILES,
    XLRH1_VALID_STAGE_TRANSITIONS,
    audit_phase187_donor_contracts,
    evaluate_64_master_safety_gates,
    evaluate_64gate_preflight,
    evaluate_g63_fx3a_branch_firewall,
    evaluate_g64_xlrh1_mishoe_guard,
    main as module_cli_main,
    validate_body_35mm_jack_override_and_sq_mute,
    validate_bodydata_fx3_vs_fx3a_branch,
    validate_camset_branch_isolation,
    validate_fx3_lcd_nfc_ir_hardware_parity,
    validate_fx3_vs_fx3a_body_hardware_signature,
    validate_xlrh1_mishoe_digital_audio_routing,
    validate_xlrh1_no_fake_usb_firmware_payload,
    validate_xlrh1_phantom_48v_stage_handoff,
    verify_fx3_vs_fx3a_branch_firewall,
    verify_xlrh1_mishoe_4ch_vs_35mm_override_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwFx3aFirewallXlrH1MiShoe64GateTests(unittest.TestCase):
    # --- 1. Hard-Locked Redlines, Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

        self.assertEqual(
            G63,
            GATE_G63_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL,
        )
        self.assertEqual(
            G64,
            GATE_G64_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD,
        )
        self.assertEqual(fx3_safety.G63, G63_GATE_CODE)
        self.assertEqual(fx3_safety.G64, G64_GATE_CODE)
        self.assertIs(fx3_safety.evaluate_64gate_preflight, evaluate_64gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_64_master_safety_gates,
            evaluate_64_master_safety_gates,
        )
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(
            REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_SCHEMA,
            "fx3-realhw-fx3a-firewall-xlrh1-mishoe-64gate-preflight-v1",
        )
        self.assertEqual(REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_VERSION, "1.0.0")

    def test_02_constants_match_wave23_real_hardware_specs(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_MODEL_ID_HEX, "0x91030080")
        self.assertEqual(FX3_TARGET_FIRMWARE_VERSION, "7.02")
        self.assertEqual(FX3_MIN_BRANCH_MAJOR, 7)
        self.assertEqual(FX3_LCD_DOT_COUNT, 1_440_000)

        self.assertEqual(FX3A_MODEL_NAME, "ILME-FX3A")
        self.assertEqual(FX3A_FIRMWARE_VERSION_202, "2.02")
        self.assertEqual(FX3A_XGA_LCD_DOT_COUNT, 2_359_296)
        self.assertEqual(FX30_MODEL_NAME, "ILME-FX30")
        self.assertEqual(FX30_MODEL_ID, 0x91030084)
        self.assertEqual(FX30_MODEL_ID_HEX, "0x91030084")
        self.assertIn("ILME-FX3A", REJECTED_CROSS_BRANCH_MODELS)
        self.assertIn("ILME-FX30", REJECTED_CROSS_BRANCH_MODELS)
        self.assertIn(FX30_MODEL_ID, REJECTED_CROSS_BRANCH_MODEL_IDS)
        self.assertEqual(FX3_FAIL_CLOSED_MAX_LATENCY_US, 50.0)

        self.assertEqual(XLRH1_HANDLE_MODEL, "XLR-H1")
        self.assertEqual(XLRH1_AUDIO_SAMPLE_RATE_HZ, 48_000)
        self.assertEqual(XLRH1_DEFAULT_FORMAT_MODE, "48KHZ_24BIT_4CH")
        self.assertEqual(XLRH1_POST_BODYDATA_RESET_DEFAULT, "48KHZ_16BIT_2CH")
        self.assertEqual(
            set(XLRH1_VALID_AUDIO_PROFILES.keys()),
            {"48KHZ_24BIT_4CH", "48KHZ_24BIT_2CH", "48KHZ_16BIT_2CH"},
        )
        self.assertEqual(
            XLRH1_HEADPHONE_MONITOR_MATRICES,
            ("CH1_2", "CH3_4", "CH1+3_CH2+4"),
        )
        self.assertEqual(XLRH1_EXPECTED_IN1_IN2_ROUTE, "CH1_CH2")
        self.assertEqual(XLRH1_EXPECTED_IN3_ROUTE, "CH3_CH4")
        self.assertIn("STAGE_A_TO_STAGE_B", XLRH1_VALID_STAGE_TRANSITIONS)

    def test_03_donor_audit_auto_detect_dual_mode(self) -> None:
        res = audit_phase187_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.hotshoe_contracts_verified)
        self.assertEqual(res.missing_markers, ())
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1"
        if env_clean:
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)
        else:
            self.assertIn(
                res.verification_mode,
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_04_donor_audit_clean_room_forced(self) -> None:
        res = audit_phase187_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), len(PINNED_PHASE187_DONOR_SPECS))
        self.assertEqual(res.missing_markers, ())

    def test_05_donor_audit_missing_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase187_donor_contracts(
                work_root=Path(tmp) / "nonexistent_work_dir",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_06_donor_audit_detects_corrupted_donor_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wroot = Path(tmp)
            for _key, (_body, rel, _sz, _sha, toks, _lbl) in (
                PINNED_PHASE187_DONOR_SPECS.items()
            ):
                p = wroot / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"".join(toks))
            res = audit_phase187_donor_contracts(work_root=wroot, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, len(PINNED_PHASE187_DONOR_SPECS))

    def test_07_donor_audit_synthetic_matching_specs_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wroot = Path(tmp)
            payload_a = b"\x7fELF ILME-FX3 ILME-FX3A ILME-FX30 MI_SHOE HOTSHOE 48kHz 24bit 4ch XLR HANDLE"
            payload_b = b"\x7fELF CAMSET NFC HOTSHOE 24bit 4ch XLR HANDLE S&Q"
            payload_c = b"\x7fELF HOTSHOE Hotshoe HANDLE"
            custom_specs = {}
            files_map = {
                "fx3_cpapp_b": ("fx3", "a/cpapp-b.bin", payload_a, (b"ILME-FX3", b"ILME-FX3A", b"MI_SHOE")),
                "fx3_appfw_so": ("fx3", "b/appFw.so", payload_b, (b"\x7fELF", b"CAMSET", b"NFC")),
                "fx6_hotshoe_so": ("hotshoe", "c/libInfraHotshoe.so", payload_c, (b"\x7fELF", b"HOTSHOE", b"HANDLE")),
            }
            for key, (body, rel, blob, toks) in files_map.items():
                p = wroot / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(blob)
                sha = hashlib.sha256(blob).hexdigest()
                custom_specs[key] = (body, rel, len(blob), sha, toks, f"lbl:{key}")

            with patch(
                "fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard.PINNED_PHASE187_DONOR_SPECS",
                custom_specs,
            ):
                res = audit_phase187_donor_contracts(work_root=wroot, force_clean_room=False)
                self.assertTrue(res.valid, res.errors)
                self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(res.files_inspected, 3)
                self.assertTrue(res.fx3_contracts_verified)
                self.assertTrue(res.hotshoe_contracts_verified)

    # --- 2. Gate G63 (`ILME-FX3` vs `ILME-FX3A` Hardware-Branch Firewall) ---

    def test_08_g63_nominal_fx3_702_passes(self) -> None:
        res = verify_fx3_vs_fx3a_branch_firewall()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G63)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.body_model_name, "ILME-FX3")
        self.assertEqual(res.body_model_id_hex, "0x91030080")
        self.assertEqual(res.lcd_dot_count, 1_440_000)
        self.assertTrue(res.nfc_hardware_present)
        self.assertTrue(res.ir_receiver_present)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_09_g63_blocks_ilme_fx3a_body_and_donor_signatures(self) -> None:
        ok, code, _ = validate_fx3_vs_fx3a_body_hardware_signature(
            body_model_name=FX3A_MODEL_NAME
        )
        self.assertFalse(ok)
        self.assertEqual(code, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

        res_body = verify_fx3_vs_fx3a_branch_firewall(
            body_model_name=FX3A_MODEL_NAME,
            body_branch=FX3A_BRANCH_NAME,
        )
        self.assertFalse(res_body.valid)
        self.assertEqual(res_body.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

        res_donor = verify_fx3_vs_fx3a_branch_firewall(
            donor_model_name="FX3A",
        )
        self.assertFalse(res_donor.valid)
        self.assertIn(STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE, res_donor.violation_codes)

    def test_10_g63_blocks_ilme_fx30_model_id_0x91030084_and_fx6(self) -> None:
        res_fx30_id = verify_fx3_vs_fx3a_branch_firewall(
            body_model_name=FX30_MODEL_NAME,
            body_model_id=FX30_MODEL_ID,
            body_branch=FX30_BRANCH_NAME,
        )
        self.assertFalse(res_fx30_id.valid)
        self.assertEqual(res_fx30_id.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

        res_donor_fx30 = verify_fx3_vs_fx3a_branch_firewall(
            donor_model_id=FX30_MODEL_ID_HEX,
        )
        self.assertFalse(res_donor_fx30.valid)
        self.assertEqual(res_donor_fx30.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

        res_fx6 = verify_fx3_vs_fx3a_branch_firewall(
            donor_model_name="ILME-FX6",
        )
        self.assertFalse(res_fx6.valid)
        self.assertEqual(res_fx6.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

    def test_11_g63_blocks_fx3a_firmware_ver_1x_and_202(self) -> None:
        for fw in ("1.00", "2.02", "5.00", "6.02"):
            res = verify_fx3_vs_fx3a_branch_firewall(body_firmware_version=fw)
            self.assertFalse(res.valid, f"Expected fw={fw} to be rejected")
            self.assertEqual(res.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE)

        res_ok = verify_fx3_vs_fx3a_branch_firewall(body_firmware_version="7.02")
        self.assertTrue(res_ok.valid)

    def test_12_g63_blocks_fx3a_2025_revision_and_xga_2359296_lcd(self) -> None:
        res_rev = verify_fx3_vs_fx3a_branch_firewall(
            hardware_revision=FX3A_HW_REVISION_2025,
            lcd_dot_count=FX3A_XGA_LCD_DOT_COUNT,
            lcd_panel_spec=FX3A_XGA_LCD_PANEL_SPEC,
            display_shim_target="FX3A_2359K_XGA_LCD",
        )
        self.assertFalse(res_rev.valid)
        self.assertEqual(res_rev.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH)

        res_dots = verify_fx3_vs_fx3a_branch_firewall(
            lcd_dot_count=FX3A_XGA_LCD_DOT_COUNT,
        )
        self.assertFalse(res_dots.valid)
        self.assertEqual(res_dots.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH)

    def test_13_g63_blocks_omitted_nfc_or_omitted_ir_receiver(self) -> None:
        res_no_nfc = verify_fx3_vs_fx3a_branch_firewall(nfc_hardware_present=False)
        self.assertFalse(res_no_nfc.valid)
        self.assertEqual(res_no_nfc.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH)

        res_no_ir = verify_fx3_vs_fx3a_branch_firewall(ir_receiver_present=False)
        self.assertFalse(res_no_ir.valid)
        self.assertEqual(res_no_ir.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH)

    def test_14_g63_enforces_50us_fail_closed_latency_and_stock_fallback(self) -> None:
        res_slow = verify_fx3_vs_fx3a_branch_firewall(fail_closed_latency_us=50.0)
        self.assertFalse(res_slow.valid)
        self.assertEqual(res_slow.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH)

        res_nofallback = verify_fx3_vs_fx3a_branch_firewall(stock_fallback_armed=False)
        self.assertFalse(res_nofallback.valid)
        self.assertEqual(
            res_nofallback.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH
        )

        ok, _, _ = validate_fx3_lcd_nfc_ir_hardware_parity(fail_closed_latency_us=49.9)
        self.assertTrue(ok)

    def test_15_g63_rejects_fx3a_ver_1x_2x_and_fx30_bodydata_packages(self) -> None:
        for ver, model, mid, branch in (
            ("1.01", FX3A_MODEL_NAME, FX3_MODEL_ID, FX3A_BRANCH_NAME),
            (FX3A_FIRMWARE_VERSION_202, FX3_MODEL_NAME, FX3_MODEL_ID, FX3_BRANCH_NAME),
            ("2.02", FX3A_MODEL_NAME, FX3_MODEL_ID, FX3A_BRANCH_NAME),
            ("7.02", FX30_MODEL_NAME, FX30_MODEL_ID, FX30_BRANCH_NAME),
        ):
            res = verify_fx3_vs_fx3a_branch_firewall(
                bodydata_present=True,
                bodydata_target_model=model,
                bodydata_target_model_id=mid,
                bodydata_version=ver,
                bodydata_branch=branch,
            )
            self.assertFalse(res.valid, f"Expected BODYDATA {model} {ver} blocked")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X
            )

        ok, _, _ = validate_bodydata_fx3_vs_fx3a_branch(
            bodydata_present=True,
            bodydata_target_model=FX3_MODEL_NAME,
            bodydata_target_model_id=FX3_MODEL_ID,
            bodydata_version="7.02",
            bodydata_branch=FX3_BRANCH_NAME,
        )
        self.assertTrue(ok)

    def test_16_g63_blocks_cross_branch_camset_settings_import(self) -> None:
        for src_m, dst_m, src_b, dst_b in (
            (FX3A_MODEL_NAME, FX3_MODEL_NAME, FX3A_BRANCH_NAME, FX3_BRANCH_NAME),
            (FX3_MODEL_NAME, FX3A_MODEL_NAME, FX3_BRANCH_NAME, FX3A_BRANCH_NAME),
            (FX30_MODEL_NAME, FX3_MODEL_NAME, FX30_BRANCH_NAME, FX3_BRANCH_NAME),
        ):
            res = verify_fx3_vs_fx3a_branch_firewall(
                camset_import_requested=True,
                camset_source_model=src_m,
                camset_target_model=dst_m,
                camset_source_branch=src_b,
                camset_target_branch=dst_b,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT
            )

        res_unblocked = verify_fx3_vs_fx3a_branch_firewall(
            camset_cross_branch_blocked=False
        )
        self.assertFalse(res_unblocked.valid)
        self.assertEqual(
            res_unblocked.status, STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT
        )

        ok, _, _ = validate_camset_branch_isolation(
            camset_import_requested=True,
            camset_source_model=FX3_MODEL_NAME,
            camset_target_model=FX3_MODEL_NAME,
            camset_source_branch=FX3_BRANCH_NAME,
            camset_target_branch=FX3_BRANCH_NAME,
            camset_cross_branch_blocked=True,
        )
        self.assertTrue(ok)

    def test_17_g63_rejects_malformed_telemetry_and_persistent_write_request(self) -> None:
        res_bad = verify_fx3_vs_fx3a_branch_firewall(
            lcd_dot_count=-1,
            fail_closed_latency_us=float("nan"),
            body_model_name="",
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_G63_TELEMETRY_INVALID)

        verdict, g63 = evaluate_g63_fx3a_branch_firewall(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(g63.valid)
        self.assertEqual(g63.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(g63.persistent_emmc_writes_authorized)

    def test_18_g63_evaluate_propagates_corrupted_donor_integrity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wroot = Path(tmp)
            for _key, (_body, rel, _sz, _sha, toks, _lbl) in (
                PINNED_PHASE187_DONOR_SPECS.items()
            ):
                p = wroot / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"".join(toks))
            verdict, res = evaluate_g63_fx3a_branch_firewall(
                work_root=wroot,
                force_clean_room=False,
            )
            self.assertFalse(verdict.passed)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY)

    # --- 3. Gate G64 (`XLR-H1` MI-Shoe 48kHz/24bit 4ch vs Body 3.5mm Override Guard) ---

    def test_19_g64_nominal_xlrh1_48khz_24bit_4ch_passes(self) -> None:
        res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G64)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.handle_model, "XLR-H1")
        self.assertEqual(res.audio_format_mode, "48KHZ_24BIT_4CH")
        self.assertEqual(res.sample_rate_hz, 48_000)
        self.assertEqual(res.bit_depth, 24)
        self.assertEqual(res.channel_count, 4)
        self.assertTrue(res.routing_and_format_valid)
        self.assertTrue(res.body_35mm_and_sq_valid)
        self.assertTrue(res.phantom_handoff_valid)
        self.assertTrue(res.usb_fw_payload_guard_valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_20_g64_supports_all_valid_profiles_and_4ch_headphone_matrices(self) -> None:
        for hp in ("CH1_2", "CH3_4", "CH1+3_CH2+4"):
            res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
                headphone_monitor_matrix=hp
            )
            self.assertTrue(res.valid, f"Expected hp matrix {hp} valid: {res.errors}")

        for mode, depth, ch, in3, hp in (
            ("48KHZ_24BIT_2CH", 24, 2, "DISABLED_2CH", "CH1_2"),
            ("48KHZ_16BIT_2CH", 16, 2, "DISABLED_2CH", "CH1_2"),
        ):
            res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
                audio_format_mode=mode,
                bit_depth=depth,
                channel_count=ch,
                in3_35mm_route=in3,
                headphone_monitor_matrix=hp,
            )
            self.assertTrue(res.valid, f"Expected mode {mode} valid: {res.errors}")

    def test_21_g64_blocks_disabled_handle_audio_and_invalid_routing_or_format(self) -> None:
        res_off = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            xlrh1_attached=True,
            handle_audio_enabled=False,
        )
        self.assertFalse(res_off.valid)
        self.assertEqual(res_off.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID)

        res_sr = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            sample_rate_hz=44_100,
        )
        self.assertFalse(res_sr.valid)
        self.assertEqual(res_sr.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID)

        res_mismatch = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            audio_format_mode="48KHZ_24BIT_4CH",
            bit_depth=16,
            channel_count=2,
        )
        self.assertFalse(res_mismatch.valid)
        self.assertEqual(
            res_mismatch.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID
        )

        res_route = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            in1_in2_xlr_route="CH3_CH4",
        )
        self.assertFalse(res_route.valid)
        self.assertEqual(res_route.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID)

        res_hp = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            headphone_monitor_matrix="MONO_MIX_INVALID",
        )
        self.assertFalse(res_hp.valid)
        self.assertEqual(res_hp.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID)

    def test_22_g64_blocks_unreconciled_post_bodydata_16bit_2ch_reset(self) -> None:
        res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            post_bodydata_reset_unreconciled=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID)

    def test_23_g64_detects_body_35mm_mic_jack_physical_override(self) -> None:
        res_plug = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            body_35mm_mic_plugged=True,
            mi_shoe_audio_set_locked_out=True,
        )
        self.assertFalse(res_plug.valid)
        self.assertTrue(res_plug.body_35mm_override_detected)
        self.assertEqual(
            res_plug.status, STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE
        )

        res_lock_only = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            body_35mm_mic_plugged=False,
            mi_shoe_audio_set_locked_out=True,
        )
        self.assertFalse(res_lock_only.valid)
        self.assertEqual(
            res_lock_only.status, STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE
        )

    def test_24_g64_enforces_sq_audio_mute_consistency(self) -> None:
        ok_sq, _, _ = validate_body_35mm_jack_override_and_sq_mute(
            sq_mode_active=True,
            mi_shoe_audio_muted=True,
        )
        self.assertTrue(ok_sq)

        res_sq_unmuted = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            sq_mode_active=True,
            mi_shoe_audio_muted=False,
        )
        self.assertFalse(res_sq_unmuted.valid)
        self.assertEqual(
            res_sq_unmuted.status, STATUS_BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY
        )

        res_normal_muted = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            sq_mode_active=False,
            mi_shoe_audio_muted=True,
        )
        self.assertFalse(res_normal_muted.valid)
        self.assertEqual(
            res_normal_muted.status, STATUS_BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY
        )

    def test_25_g64_blocks_phantom_48v_stage_handoff_glitches(self) -> None:
        for bad_kwargs in (
            {"phantom_48v_rail_stable": False},
            {"phantom_48v_glitch_events": 1},
            {"phantom_48v_slew_controlled": False},
            {"adc_soft_mute_during_handoff": False},
            {"hotshoe_gpio_glitch_detected": True},
            {"stage_transition": "UNKNOWN_UNSAFE_STAGE"},
        ):
            res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"Expected failure for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH
            )

        for tr in XLRH1_VALID_STAGE_TRANSITIONS:
            ok, _, _ = validate_xlrh1_phantom_48v_stage_handoff(stage_transition=tr)
            self.assertTrue(ok)

    def test_26_g64_rejects_fake_standalone_xlrh1_usb_firmware_payloads(self) -> None:
        for bad_kwargs in (
            {"xlrh1_usb_fw_update_attempted": True},
            {"xlrh1_standalone_usb_payload_present": True},
            {"xlrh1_usb_payload_filename": "XLR-H1_v2.00_Update.bin"},
            {"xlrh1_standalone_usb_fw_rejected": False},
        ):
            res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(**bad_kwargs)
            self.assertFalse(res.valid, f"Expected fake USB FW blocked for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD
            )

        ok, _, _ = validate_xlrh1_no_fake_usb_firmware_payload()
        self.assertTrue(ok)

    def test_27_g64_rejects_malformed_telemetry_and_persistent_write_request(self) -> None:
        res_bad = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            sample_rate_hz=-48000,
            phantom_48v_glitch_events=-1,
            handle_model="",
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_G64_TELEMETRY_INVALID)

        verdict, g64 = evaluate_g64_xlrh1_mishoe_guard(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(g64.valid)
        self.assertEqual(g64.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(g64.persistent_emmc_writes_authorized)

    def test_28_g64_evaluate_propagates_corrupted_donor_integrity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wroot = Path(tmp)
            for _key, (_body, rel, _sz, _sha, toks, _lbl) in (
                PINNED_PHASE187_DONOR_SPECS.items()
            ):
                p = wroot / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"".join(toks))
            verdict, res = evaluate_g64_xlrh1_mishoe_guard(
                work_root=wroot,
                force_clean_room=False,
            )
            self.assertFalse(verdict.passed)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY)

    # --- 4. Master 64-Gate Preflight (`evaluate_64gate_preflight` / `verify-64-gates`) ---

    def test_29_evaluate_64gate_preflight_offline_61_of_64_clean_room(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(report.clean_room_forced)
        self.assertFalse(report.dry_run_rehearsal_only)
        self.assertTrue(report.offline_61_gates_verified)
        self.assertFalse(report.all_64_gates_verified)
        self.assertTrue(report.g13_to_g64_all_passed)
        self.assertTrue(report.g63_to_g64_all_passed)
        self.assertTrue(report.h0_h1_trial_entry_allowed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertEqual(report.status, "VERIFIED_61_OF_64_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(report.summary["total_gates"], 64)
        self.assertEqual(report.summary["verified_gates"], 61)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g01_to_g12_verified"], 9)
        self.assertEqual(report.summary["g13_to_g62_verified"], 50)
        self.assertEqual(report.summary["g63_to_g64_verified"], 2)
        self.assertEqual(len(report.gates), 64)
        for idx in (9, 10, 11):
            self.assertFalse(report.gates[idx]["passed"])
            self.assertEqual(
                report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_30_evaluate_64gate_preflight_dry_run_64_of_64_clean_room(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(report.all_64_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.g63_to_g64_all_passed)
        self.assertTrue(report.g13_to_g64_all_passed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)
        self.assertEqual(
            report.status, "VERIFIED_ALL_64_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(report.summary["verified_gates"], 64)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(all(g["passed"] for g in report.gates))

    def test_31_evaluate_64gate_preflight_default_mode_matches_env(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        self.assertTrue(report.all_64_gates_verified)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertEqual(report.summary["verified_gates"], 64)
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1"
        if env_clean:
            self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(
                report.verification_mode,
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_32_evaluate_64gate_preflight_propagates_g63_faults(self) -> None:
        r_fx3a = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fx3a_firewall_kwargs={
                "body_model_name": FX3A_MODEL_NAME,
                "body_firmware_version": FX3A_FIRMWARE_VERSION_202,
                "body_branch": FX3A_BRANCH_NAME,
            },
        )
        self.assertFalse(r_fx3a.all_64_gates_verified)
        self.assertFalse(r_fx3a.offline_61_gates_verified)
        self.assertFalse(r_fx3a.g63_to_g64_all_passed)
        self.assertEqual(
            r_fx3a.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE
        )

        r_camset = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fx3a_firewall_kwargs={
                "camset_import_requested": True,
                "camset_source_model": FX3A_MODEL_NAME,
                "camset_source_branch": FX3A_BRANCH_NAME,
            },
        )
        self.assertFalse(r_camset.all_64_gates_verified)
        self.assertEqual(
            r_camset.status, STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT
        )

    def test_33_evaluate_64gate_preflight_propagates_g64_faults(self) -> None:
        r_35mm = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            xlrh1_mishoe_kwargs={
                "body_35mm_mic_plugged": True,
                "mi_shoe_audio_set_locked_out": True,
            },
        )
        self.assertFalse(r_35mm.all_64_gates_verified)
        self.assertFalse(r_35mm.offline_61_gates_verified)
        self.assertFalse(r_35mm.g63_to_g64_all_passed)
        self.assertEqual(
            r_35mm.status, STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE
        )

        r_48v = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            xlrh1_mishoe_kwargs={"phantom_48v_glitch_events": 2},
        )
        self.assertFalse(r_48v.all_64_gates_verified)
        self.assertEqual(
            r_48v.status, STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH
        )

        r_usb = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            xlrh1_mishoe_kwargs={"xlrh1_usb_payload_filename": "XLRH1_FW.BIN"},
        )
        self.assertFalse(r_usb.all_64_gates_verified)
        self.assertEqual(
            r_usb.status, STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD
        )

    def test_34_evaluate_64gate_preflight_propagates_upstream_g58_to_g62_faults(
        self,
    ) -> None:
        r_g62 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            hdmi_raw_kwargs={"sdi_mmio_probes_emitted": 1},
        )
        self.assertFalse(r_g62.all_64_gates_verified)
        self.assertEqual(
            r_g62.status, STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED
        )

        r_g61 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            emount_breathing_kwargs={"lens_id": 0x0001},
        )
        self.assertFalse(r_g61.all_64_gates_verified)
        self.assertEqual(
            r_g61.status, STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED
        )

        r_g60 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            slot1_ufu_c2pa_kwargs={"body_firmware_version": "2.02"},
        )
        self.assertFalse(r_g60.all_64_gates_verified)
        self.assertEqual(r_g60.status, STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR)

        r_g59 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            ssboot_wbi2_kwargs={"blkroset_nflasha5": 0},
        )
        self.assertFalse(r_g59.all_64_gates_verified)
        self.assertEqual(
            r_g59.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

        r_g58 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            bench_interlock_kwargs={"auto_flash_requested": True},
        )
        self.assertFalse(r_g58.all_64_gates_verified)
        self.assertEqual(
            r_g58.status, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION
        )

    def test_35_evaluate_64gate_preflight_blocks_persistent_write_request(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(report.all_64_gates_verified)
        self.assertFalse(report.h0_h1_trial_entry_allowed)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertEqual(report.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_36_backward_compatibility_58_60_62gate_preflights_intact(self) -> None:
        r58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(r58.summary["total_gates"], 58)
        self.assertEqual(r58.summary["verified_gates"], 58)
        self.assertTrue(r58.all_58_gates_verified)

        r60 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r60.summary["total_gates"], 60)
        self.assertEqual(r60.summary["verified_gates"], 60)
        self.assertTrue(r60.all_60_gates_verified)

        r62 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r62.summary["total_gates"], 62)
        self.assertEqual(r62.summary["verified_gates"], 62)
        self.assertTrue(r62.all_62_gates_verified)

        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)

    def test_37_gate_order_g63_and_g64_ids_in_master_report(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.gates[62]["gate_id"], G63_GATE_ID)
        self.assertEqual(report.gates[62]["gate_code"], G63_GATE_CODE)
        self.assertEqual(report.gates[63]["gate_id"], G64_GATE_ID)
        self.assertEqual(report.gates[63]["gate_code"], G64_GATE_CODE)

    def test_38_dry_run_simulated_backup_alias_flag_supported(self) -> None:
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertTrue(report.all_64_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 64)

    def test_39_g63_body_branch_and_bodydata_cross_branch_matrix(self) -> None:
        res_branch = verify_fx3_vs_fx3a_branch_firewall(body_branch=FX3A_BRANCH_NAME)
        self.assertFalse(res_branch.valid)
        self.assertEqual(
            res_branch.status, STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE
        )

        res_bd_fx6 = verify_fx3_vs_fx3a_branch_firewall(
            bodydata_present=True,
            bodydata_target_model="ILME-FX6",
            bodydata_branch="FX6",
            bodydata_version="5.01",
        )
        self.assertFalse(res_bd_fx6.valid)
        self.assertEqual(
            res_bd_fx6.status, STATUS_BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X
        )

    def test_40_g63_display_shim_and_xga_panel_spec_string_blocked(self) -> None:
        res_shim = verify_fx3_vs_fx3a_branch_firewall(
            display_shim_target="FX3A_XGA_PANEL_SHIM"
        )
        self.assertFalse(res_shim.valid)
        self.assertEqual(
            res_shim.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH
        )

        res_spec = verify_fx3_vs_fx3a_branch_firewall(
            lcd_panel_spec="3.0_2359K_DOT_XGA"
        )
        self.assertFalse(res_spec.valid)
        self.assertEqual(
            res_spec.status, STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH
        )

    def test_41_g64_detached_xlrh1_does_not_trigger_handle_off_or_35mm_override(
        self,
    ) -> None:
        res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            xlrh1_attached=False,
            handle_audio_enabled=False,
            body_35mm_mic_plugged=True,
            mi_shoe_audio_set_locked_out=False,
            audio_format_mode="48KHZ_24BIT_2CH",
            bit_depth=24,
            channel_count=2,
            in3_35mm_route="DISABLED_2CH",
            headphone_monitor_matrix="CH1_2",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G64)

    def test_42_g64_2ch_profile_rejects_ch3_4_headphone_matrix(self) -> None:
        res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            audio_format_mode="48KHZ_16BIT_2CH",
            bit_depth=16,
            channel_count=2,
            in3_35mm_route="DISABLED_2CH",
            headphone_monitor_matrix="CH3_4",
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID
        )

    def test_43_g64_invalid_handle_model_and_in3_route_blocked(self) -> None:
        res_handle = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            handle_model="ECM-B1M"
        )
        self.assertFalse(res_handle.valid)
        self.assertEqual(
            res_handle.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID
        )

        res_in3 = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            channel_count=4,
            in3_35mm_route="CH1_CH2",
        )
        self.assertFalse(res_in3.valid)
        self.assertEqual(
            res_in3.status, STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID
        )

    def test_44_g64_multiple_simultaneous_violations_accumulated(self) -> None:
        res = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
            body_35mm_mic_plugged=True,
            mi_shoe_audio_set_locked_out=True,
            phantom_48v_glitch_events=3,
            xlrh1_usb_payload_filename="fake_xlrh1_fw.dat",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
            res.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH,
            res.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD,
            res.violation_codes,
        )

    # --- 5. CLI Entrypoints, Zero Raw Firmware Leakage & Performance ---

    def test_45_cli_verify_g63_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g63-fx3a-branch-firewall", "--force-clean-room", "--json"],
            ["verify-g63-fx3a-branch-firewall", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G63)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertEqual(
                    data["fx3a_branch_firewall"]["body_model_name"], "ILME-FX3"
                )
            else:
                self.assertIn("gate=G63_fx3_vs_fx3a_lcd_nfc_ir_firmware_branch_firewall", buf.getvalue())

    def test_46_cli_verify_g64_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g64-xlrh1-mishoe-guard", "--force-clean-room", "--json"],
            ["verify-g64-xlrh1-mishoe-guard", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G64)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertEqual(
                    data["xlrh1_mishoe_guard"]["audio_format_mode"],
                    "48KHZ_24BIT_4CH",
                )
            else:
                self.assertIn("gate=G64_xlrh1_mishoe_4ch_24bit_vs_body_35mm_override_guard", buf.getvalue())

    def test_47_cli_verify_64_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-64-gates", "--force-clean-room", "--json"], 61),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 64),
            (["verify-64-gates", "--force-clean-room"], None),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated"], None),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if expected_count is not None:
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["summary"]["verified_gates"], expected_count)
                self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_48_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 64)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_49_module_cli_text_output_smoke(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=64/64", out)
        self.assertIn("g63_to_g64_all_passed=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_50_verify_64_gates_fast_runtime_under_6s(self) -> None:
        t0 = time.monotonic()
        report = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(report.all_64_gates_verified)
        self.assertLess(elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
