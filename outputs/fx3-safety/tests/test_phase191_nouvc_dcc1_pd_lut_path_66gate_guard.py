"""Fast dual-mode unit tests for Phase 191 — Real-Hardware Main Track Part 20:
Gate G65 (`ILME-FX3` `0x91030080` No-UVC USB Gadget Firewall & `USB-PD`
`NP-FZ100` / `DC-C1` `>=65W / 5A` Electrical Interlock),
Gate G66 (Dual-Media `.cube` User LUT Path-Asymmetry `SD` vs `CFexpress-A`,
`Cine EI` `800 / 12800` Base Sensitivity & `RMT-P1BT` BT/IR Mutual-Exclusion Guard),
and 66-Gate Master Preflight (`G01..G66` / `verify-66-gates` / `run_66_gate_preflight`).
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
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
    STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
    evaluate_64gate_preflight,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    ALLOWED_4K_STREAMING_TRANSPORTS,
    ALLOWED_FX3_USB_CONNECTION_MODES,
    ALLOWED_NOUVC_BODY_MODELS,
    CFEXPRESS_A_USER_LUT_DIR,
    CINE_EI_BASE_ISOS,
    CINE_EI_RANGE_BY_BASE,
    CUBE_ALLOWED_3D_SIZES,
    CUBE_MAX_FILENAME_BYTES,
    DC_C1_MIN_CABLE_AMPS,
    DC_C1_MIN_USB_PD_WATTS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FORBIDDEN_FX3_UVC_MODES,
    FORBIDDEN_STAGEB_LUT_WRITE_PREFIXES,
    FX3_KERNEL_RELEASE,
    G65,
    G65_GATE_CODE,
    G65_GATE_ID,
    G66,
    G66_GATE_CODE,
    G66_GATE_ID,
    GATE_G65_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD,
    GATE_G66_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MAX_NETWORK_STREAMING_BITRATE_MBPS,
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SD,
    MEDIA_TYPE_SDXC,
    NETWORK_STREAMING_TRANSPORTS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE191_DONOR_SPECS,
    POWER_SOURCE_DC_C1_COUPLER,
    POWER_SOURCE_USB_PD_BODY,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_SCHEMA,
    REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_VERSION,
    RMT_P1BT_BT_VERSION,
    RMT_P1BT_MODEL,
    SD_USER_LUT_DIR,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE,
    STATUS_BLOCKED_G65_INVALID_STREAMING_TRANSPORT,
    STATUS_BLOCKED_G65_MICRO_USB_POWER_REJECTED,
    STATUS_BLOCKED_G65_TELEMETRY_INVALID,
    STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT,
    STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN,
    STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS,
    STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING,
    STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE,
    STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION,
    STATUS_BLOCKED_G66_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G65,
    STATUS_VERIFIED_G66,
    STATUS_VERIFIED_SAFE,
    USB_PD_BODY_MIN_BATTERY_BARS,
    USB_PD_BODY_MIN_BATTERY_PCT,
    USER_LUT_AE_OFFSET_MAX_EV,
    USER_LUT_AE_OFFSET_MIN_EV,
    USER_LUT_MAX_SLOTS,
    VALID_POWER_SOURCES,
    audit_phase191_donor_contracts,
    evaluate_66_master_safety_gates,
    evaluate_66gate_preflight,
    evaluate_g65_nouvc_dcc1_pd_guard,
    evaluate_g66_lut_path_cineei_bt_guard,
    main as module_cli_main,
    run_66_gate_preflight,
    validate_cine_ei_base_iso_bounds,
    validate_fx3_nouvc_usb_gadget_firewall,
    validate_rmt_p1bt_bt_ir_mutual_exclusion,
    validate_usbpd_body_vs_dcc1_power_supply,
    validate_user_cube_lut_and_media_path_asymmetry,
    verify_dualmedia_lut_path_cineei_and_bt_guard,
    verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard,
)


def _create_synthetic_donor_tree(base: Path, *, corrupt_power: bool = False) -> Path:
    for key, (_body, rel_path, exp_size, _sha, markers, _lbl) in PINNED_PHASE191_DONOR_SPECS.items():
        p = base / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray(exp_size)
        cursor = 0
        for tok in markers:
            if corrupt_power and key == "fx3_libusbbuspower_so" and b"IsVbusReady" in tok:
                tok = b"CORRUPTED_MARKER"
            payload[cursor : cursor + len(tok)] = tok
            cursor += len(tok) + 16
        p.write_bytes(bytes(payload))
    return base


class Phase191NoUvcDcc1PdLutPath66GateGuardTests(unittest.TestCase):
    # --- 1. Hard-Locked Safety Redlines & Public Package Exports ---

    def test_01_hard_locked_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(
            G65, GATE_G65_FX3_NOUVC_GADGET_AND_USBPD_DCC1_ELECTRICAL_GUARD
        )
        self.assertEqual(
            G66, GATE_G66_DUALMEDIA_CUBE_LUT_PATH_CINEEI_AND_RMT_P1BT_BT_GUARD
        )
        self.assertIs(run_66_gate_preflight, evaluate_66gate_preflight)
        self.assertIs(evaluate_66_master_safety_gates, evaluate_66gate_preflight)
        for name in (
            "G65",
            "G66",
            "run_66_gate_preflight",
            "evaluate_66gate_preflight",
            "evaluate_66_master_safety_gates",
            "evaluate_g65_nouvc_dcc1_pd_guard",
            "evaluate_g66_lut_path_cineei_bt_guard",
            "realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, name), f"missing fx3_safety.{name}")
            self.assertIn(name, fx3_safety.__all__)

    def test_02_schema_version_and_wave24_constants(self) -> None:
        self.assertEqual(
            REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_SCHEMA,
            "fx3-realhw-nouvc-dcc1-pd-lut-path-66gate-preflight-v1",
        )
        self.assertEqual(REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_VERSION, "1.0.0")
        self.assertEqual(FX3_KERNEL_RELEASE, "4.9.337-scel+")
        self.assertEqual(MAX_NETWORK_STREAMING_BITRATE_MBPS, 38.0)
        self.assertEqual(USB_PD_BODY_MIN_BATTERY_PCT, 51)
        self.assertEqual(USB_PD_BODY_MIN_BATTERY_BARS, 3)
        self.assertEqual(DC_C1_MIN_USB_PD_WATTS, 65.0)
        self.assertEqual(DC_C1_MIN_CABLE_AMPS, 5.0)
        self.assertEqual(SD_USER_LUT_DIR, "/Private/Sony/PRO/LUT/")
        self.assertEqual(CFEXPRESS_A_USER_LUT_DIR, "/Sony/PRO/LUT/")
        self.assertEqual(CUBE_ALLOWED_3D_SIZES, (17, 33))
        self.assertEqual(CUBE_MAX_FILENAME_BYTES, 63)
        self.assertEqual(USER_LUT_MAX_SLOTS, 16)
        self.assertEqual(CINE_EI_BASE_ISOS, (800, 12800))
        self.assertEqual(RMT_P1BT_MODEL, "RMT-P1BT")
        self.assertEqual(RMT_P1BT_BT_VERSION, "4.2")

    # --- 2. Strictly O_RDONLY Donor Audit & Clean-Room Dual Mode ---

    def test_03_donor_audit_matches_environment_mode_and_has_no_missing_markers(self) -> None:
        res = audit_phase191_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.power_contracts_verified)
        self.assertEqual(res.missing_markers, ())

    def test_04_donor_audit_clean_room_forced_skips_file_reads(self) -> None:
        res = audit_phase191_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), 3)

    def test_05_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase191_donor_contracts(
                work_root=Path(tmp) / "nonexistent",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_06_donor_audit_synthetic_tree_detects_corrupted_sha_and_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _create_synthetic_donor_tree(Path(tmp), corrupt_power=True)
            res = audit_phase191_donor_contracts(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE191_DONOR_INTEGRITY)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 3)
            self.assertFalse(res.power_contracts_verified)

    def test_07_donor_audit_passes_with_patched_sha_matching_synthetic_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _create_synthetic_donor_tree(Path(tmp), corrupt_power=False)
            patched_specs = {}
            for k, (body, rel_path, exp_size, _old_sha, toks, lbl) in PINNED_PHASE191_DONOR_SPECS.items():
                sha = hashlib.sha256((work / rel_path).read_bytes()).hexdigest()
                patched_specs[k] = (body, rel_path, exp_size, sha, toks, lbl)
            with patch(
                "fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard.PINNED_PHASE191_DONOR_SPECS",
                patched_specs,
            ):
                res = audit_phase191_donor_contracts(
                    work_root=work,
                    force_clean_room=False,
                )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 3)

    # --- 3. Gate G65: No-UVC Gadget Firewall & USB-PD / DC-C1 Electrical Interlock ---

    def test_08_g65_allows_all_five_canonical_usb_modes(self) -> None:
        for mode in (
            "Sel. When Connect",
            "MassStorage(MSC)",
            "MTP",
            "Remote Shooting",
            "USB-LAN",
            "RNDIS",
            "CDC-NCM",
        ):
            res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
                usb_connection_mode=mode,
                streaming_transport="HDMI_TYPE_A",
                streaming_bitrate_mbps=0.0,
            )
            self.assertTrue(res.valid, f"failed for mode={mode}: {res.errors}")
            self.assertTrue(res.uvc_gadget_blocked)
            self.assertEqual(res.status, STATUS_VERIFIED_G65)

    def test_09_g65_allows_fx3a_and_network_streaming_under_38mbps(self) -> None:
        for tr in ("RTMP", "RTMPS", "SRT"):
            res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
                body_model_name=FX3A_MODEL_NAME,
                body_model_id=FX3_MODEL_ID,
                usb_connection_mode="CDC-NCM",
                streaming_transport=tr,
                streaming_bitrate_mbps=38.0,
            )
            self.assertTrue(res.valid, f"failed for transport={tr}: {res.errors}")

    def test_10_g65_blocks_uvc_uac_and_usb_streaming_gadget_requests(self) -> None:
        for kwargs in (
            {"usb_connection_mode": "USB Streaming"},
            {"usb_connection_mode": "UVC/UAC"},
            {"usb_connection_mode": "USB_WEBCAM"},
            {"uvc_uac_gadget_requested": True},
            {"usb_streaming_mode_requested": True},
        ):
            res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN)
            self.assertFalse(res.uvc_gadget_blocked)

    def test_11_g65_blocks_uvc_transport_or_network_bitrate_above_38mbps(self) -> None:
        res_uvc = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            streaming_transport="UVC",
            streaming_bitrate_mbps=30.0,
        )
        self.assertFalse(res_uvc.valid)
        self.assertEqual(res_uvc.status, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN)

        res_bw = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            streaming_transport="SRT",
            streaming_bitrate_mbps=38.5,
        )
        self.assertFalse(res_bw.valid)
        self.assertEqual(res_bw.status, STATUS_BLOCKED_G65_INVALID_STREAMING_TRANSPORT)

        res_bad_tr = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            streaming_transport="FIREWIRE_DV",
        )
        self.assertFalse(res_bad_tr.valid)
        self.assertEqual(res_bad_tr.status, STATUS_BLOCKED_G65_INVALID_STREAMING_TRANSPORT)

    def test_12_g65_blocks_wrong_body_model_id_or_non_fx3_kernel(self) -> None:
        res_fx30 = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            body_model_name="ILME-FX30",
            body_model_id=0x91030084,
        )
        self.assertFalse(res_fx30.valid)
        self.assertEqual(res_fx30.status, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN)

        res_kern = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            kernel_release="5.15.0-generic",
        )
        self.assertFalse(res_kern.valid)
        self.assertEqual(res_kern.status, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN)

    def test_13_g65_usbpd_body_requires_npfz100_and_51pct_3bars(self) -> None:
        ok_min = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=51,
            battery_bars=3,
        )
        self.assertTrue(ok_min.valid, ok_min.errors)

        no_batt = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=False,
            battery_pct=90,
            battery_bars=4,
        )
        self.assertFalse(no_batt.valid)
        self.assertEqual(
            no_batt.status, STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT
        )

        low_pct = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=50,
            battery_bars=3,
        )
        self.assertFalse(low_pct.valid)
        self.assertEqual(
            low_pct.status, STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT
        )

        low_bars = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=55,
            battery_bars=2,
        )
        self.assertFalse(low_bars.valid)
        self.assertEqual(
            low_bars.status, STATUS_BLOCKED_G65_USB_PD_BODY_MISSING_NPFZ100_OR_LOW_BATT
        )

    def test_14_g65_rejects_micro_usb_power_delivery(self) -> None:
        for kwargs in (
            {"power_source": "MICRO_USB"},
            {"micro_usb_power_attempted": True},
            {"micro_usb_power_rejected": False},
        ):
            res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(**kwargs)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G65_MICRO_USB_POWER_REJECTED)

    def test_15_g65_dcc1_coupler_requires_65w_and_5a_emarked_cable(self) -> None:
        ok_dcc1 = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            np_fz100_inserted=False,
            battery_pct=0,
            battery_bars=0,
            usb_pd_watts=65.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
            dc_c1_blinking_led_fault=False,
            lcd_max_brightness_locked=True,
        )
        self.assertTrue(ok_dcc1.valid, ok_dcc1.errors)
        self.assertTrue(any("LCD maximum brightness" in w for w in ok_dcc1.warnings))

        low_watts = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=45.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
        )
        self.assertFalse(low_watts.valid)
        self.assertEqual(
            low_watts.status, STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE
        )

        cable_3a = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=100.0,
            emarked_5a_cable=False,
            cable_max_amps=3.0,
        )
        self.assertFalse(cable_3a.valid)
        self.assertEqual(
            cable_3a.status, STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE
        )

        led_fault = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=65.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
            dc_c1_blinking_led_fault=True,
        )
        self.assertFalse(led_fault.valid)
        self.assertEqual(
            led_fault.status, STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE
        )

    def test_16_g65_rejects_malformed_telemetry_and_persistent_writes(self) -> None:
        bad_tel = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            battery_pct=120,
            power_source="UNKNOWN_RAIL",
        )
        self.assertFalse(bad_tel.valid)
        self.assertEqual(bad_tel.status, STATUS_BLOCKED_G65_TELEMETRY_INVALID)

        verdict, res = evaluate_g65_nouvc_dcc1_pd_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 4. Gate G66: Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT BT/IR ---

    def test_17_g66_validates_17_and_33_pt_cube_and_63_byte_ascii_filename(self) -> None:
        exact_63 = "A" * 58 + ".cube"
        self.assertEqual(len(exact_63.encode("ascii")), 63)
        res17 = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_3d_size=17,
            lut_filename=exact_63,
            cube_text="TITLE \"FX3 Test\"\nLUT_3D_SIZE 17\n",
        )
        self.assertTrue(res17.valid, res17.errors)
        self.assertEqual(res17.lut_filename_bytes, 63)

        res33 = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_3d_size=33,
            cube_text="LUT_3D_SIZE 33\n",
        )
        self.assertTrue(res33.valid, res33.errors)

        too_long_64 = "A" * 59 + ".cube"
        res_64 = verify_dualmedia_lut_path_cineei_and_bt_guard(lut_filename=too_long_64)
        self.assertFalse(res_64.valid)
        self.assertEqual(res_64.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING)

        non_ascii = "日本_LUT.cube"
        res_uni = verify_dualmedia_lut_path_cineei_and_bt_guard(lut_filename=non_ascii)
        self.assertFalse(res_uni.valid)
        self.assertEqual(res_uni.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING)

        bad_65pt = verify_dualmedia_lut_path_cineei_and_bt_guard(lut_3d_size=65)
        self.assertFalse(bad_65pt.valid)
        self.assertEqual(bad_65pt.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING)

        mismatch_text = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_3d_size=33,
            cube_text="LUT_3D_SIZE 65\n",
        )
        self.assertFalse(mismatch_text.valid)
        self.assertEqual(
            mismatch_text.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

    def test_18_g66_enforces_16_user_slots_and_one_third_ev_ae_offset(self) -> None:
        ok_slot16 = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_slot_index=16,
            registered_lut_count=16,
            ae_level_offset_ev=1.3,
        )
        self.assertTrue(ok_slot16.valid, ok_slot16.errors)

        ok_2ev = verify_dualmedia_lut_path_cineei_and_bt_guard(ae_level_offset_ev=2.0)
        self.assertTrue(ok_2ev.valid, ok_2ev.errors)

        over_17 = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_slot_index=17,
            registered_lut_count=17,
        )
        self.assertFalse(over_17.valid)
        self.assertEqual(over_17.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING)

        bad_ev_step = verify_dualmedia_lut_path_cineei_and_bt_guard(
            ae_level_offset_ev=0.5,
        )
        self.assertFalse(bad_ev_step.valid)
        self.assertEqual(
            bad_ev_step.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

        over_2ev = verify_dualmedia_lut_path_cineei_and_bt_guard(
            ae_level_offset_ev=2.3,
        )
        self.assertFalse(over_2ev.valid)
        self.assertEqual(
            over_2ev.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

    def test_19_g66_enforces_sd_vs_cfexpress_lut_path_asymmetry_and_blocks_swapped_or_p2(
        self,
    ) -> None:
        ok_sd = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_SD,
            lut_directory="/Private/Sony/PRO/LUT/",
        )
        self.assertTrue(ok_sd.valid, ok_sd.errors)

        ok_cfe = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_CFEXPRESS_A,
            lut_directory="/Sony/PRO/LUT/",
        )
        self.assertTrue(ok_cfe.valid, ok_cfe.errors)

        swap_sd = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_SDXC,
            lut_directory="/Sony/PRO/LUT/",
        )
        self.assertFalse(swap_sd.valid)
        self.assertEqual(
            swap_sd.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        )

        swap_cfe = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_CFEXPRESS_A,
            lut_directory="/Private/Sony/PRO/LUT/",
        )
        self.assertFalse(swap_cfe.valid)
        self.assertEqual(
            swap_cfe.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        )

        p2_dir = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_SDXC,
            lut_directory="p2:/setting/lut/",
        )
        self.assertFalse(p2_dir.valid)
        self.assertEqual(
            p2_dir.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        )

        p2_flag = verify_dualmedia_lut_path_cineei_and_bt_guard(
            stage_b_p2_setting_write_attempted=True,
        )
        self.assertFalse(p2_flag.valid)
        self.assertEqual(
            p2_flag.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        )

    def test_20_g66_enforces_cine_ei_800_and_12800_bounds_without_gain_mutation(
        self,
    ) -> None:
        for base, lo, hi in ((800, 200, 3200), (12800, 3200, 51200)):
            for ei in (lo, base, hi):
                res = verify_dualmedia_lut_path_cineei_and_bt_guard(
                    cine_ei_base_iso=base,
                    cine_ei_index=ei,
                )
                self.assertTrue(res.valid, f"failed base={base} ei={ei}: {res.errors}")

        out_low = verify_dualmedia_lut_path_cineei_and_bt_guard(
            cine_ei_base_iso=800,
            cine_ei_index=4000,
        )
        self.assertFalse(out_low.valid)
        self.assertEqual(
            out_low.status, STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS
        )

        out_high = verify_dualmedia_lut_path_cineei_and_bt_guard(
            cine_ei_base_iso=12800,
            cine_ei_index=1600,
        )
        self.assertFalse(out_high.valid)
        self.assertEqual(
            out_high.status, STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS
        )

        bad_base = verify_dualmedia_lut_path_cineei_and_bt_guard(
            cine_ei_base_iso=1600,
            cine_ei_index=1600,
        )
        self.assertFalse(bad_base.valid)
        self.assertEqual(
            bad_base.status, STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS
        )

        cmos_mut = verify_dualmedia_lut_path_cineei_and_bt_guard(
            cine_ei_base_iso=800,
            cine_ei_index=1600,
            cmos_analog_gain_mutated=True,
        )
        self.assertFalse(cmos_mut.valid)
        self.assertEqual(
            cmos_mut.status, STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS
        )

    def test_21_g66_enforces_rmt_p1bt_bt_42_ir_and_gps_mutual_exclusion(self) -> None:
        ok_bt = verify_dualmedia_lut_path_cineei_and_bt_guard(
            remote_model="RMT-P1BT",
            bt_spec_version="4.2",
            bluetooth_rmt_ctrl_enabled=True,
            ir_remote_receiver_disabled=True,
            ir_remote_active=False,
            smartphone_gps_location_link_active=False,
        )
        self.assertTrue(ok_bt.valid, ok_bt.errors)

        bad_ir_rx = verify_dualmedia_lut_path_cineei_and_bt_guard(
            bluetooth_rmt_ctrl_enabled=True,
            ir_remote_receiver_disabled=False,
        )
        self.assertFalse(bad_ir_rx.valid)
        self.assertEqual(
            bad_ir_rx.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

        bad_ir_active = verify_dualmedia_lut_path_cineei_and_bt_guard(
            bluetooth_rmt_ctrl_enabled=True,
            ir_remote_receiver_disabled=True,
            ir_remote_active=True,
        )
        self.assertFalse(bad_ir_active.valid)
        self.assertEqual(
            bad_ir_active.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

        bad_gps = verify_dualmedia_lut_path_cineei_and_bt_guard(
            bluetooth_rmt_ctrl_enabled=True,
            smartphone_gps_location_link_active=True,
        )
        self.assertFalse(bad_gps.valid)
        self.assertEqual(
            bad_gps.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

        bad_fx3a_ir = verify_dualmedia_lut_path_cineei_and_bt_guard(
            body_model_name=FX3A_MODEL_NAME,
            bluetooth_rmt_ctrl_enabled=False,
            ir_remote_receiver_disabled=False,
            ir_remote_active=True,
        )
        self.assertFalse(bad_fx3a_ir.valid)
        self.assertEqual(
            bad_fx3a_ir.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

    def test_22_g66_rejects_malformed_telemetry_and_persistent_writes(self) -> None:
        bad_tel = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_filename="",
            lut_3d_size=-1,
        )
        self.assertFalse(bad_tel.valid)
        self.assertEqual(bad_tel.status, STATUS_BLOCKED_G66_TELEMETRY_INVALID)

        verdict, res = evaluate_g66_lut_path_cineei_bt_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 5. Pure Helpers & Multi-Violation Accumulation ---

    def test_23_pure_validators_return_expected_tuples(self) -> None:
        ok, code, errs = validate_fx3_nouvc_usb_gadget_firewall()
        self.assertTrue(ok)
        self.assertEqual(code, "")
        self.assertEqual(errs, [])

        ok_p, code_p, errs_p = validate_usbpd_body_vs_dcc1_power_supply()
        self.assertTrue(ok_p)
        self.assertEqual(code_p, "")
        self.assertEqual(errs_p, [])

        ok_l, code_l, errs_l = validate_user_cube_lut_and_media_path_asymmetry()
        self.assertTrue(ok_l)
        self.assertEqual(code_l, "")
        self.assertEqual(errs_l, [])

        ok_c, code_c, errs_c = validate_cine_ei_base_iso_bounds()
        self.assertTrue(ok_c)
        self.assertEqual(code_c, "")
        self.assertEqual(errs_c, [])

        ok_b, code_b, errs_b = validate_rmt_p1bt_bt_ir_mutual_exclusion()
        self.assertTrue(ok_b)
        self.assertEqual(code_b, "")
        self.assertEqual(errs_b, [])

    def test_24_g65_accumulates_gadget_and_power_violations_simultaneously(self) -> None:
        res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            uvc_uac_gadget_requested=True,
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=27.0,
            emarked_5a_cable=False,
            cable_max_amps=3.0,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN, res.violation_codes)
        self.assertIn(
            STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE,
            res.violation_codes,
        )

    def test_25_g66_accumulates_lut_cineei_and_bt_violations_simultaneously(self) -> None:
        res = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type=MEDIA_TYPE_SDXC,
            lut_directory="/Sony/PRO/LUT/",
            cine_ei_base_iso=800,
            cine_ei_index=6400,
            bluetooth_rmt_ctrl_enabled=True,
            smartphone_gps_location_link_active=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE,
            res.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G66_CINEEI_BASE_ISO_OR_EI_OUT_OF_BOUNDS,
            res.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION,
            res.violation_codes,
        )

    # --- 6. 66-Gate Master Preflight (`G01..G66` / `run_66_gate_preflight`) ---

    def test_26_preflight_offline_mode_verifies_63_of_66_and_locks_attach(self) -> None:
        report = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=False,
        )
        self.assertEqual(len(report.gates), 66)
        self.assertTrue(report.offline_63_gates_verified)
        self.assertFalse(report.all_66_gates_verified)
        self.assertTrue(report.g65_to_g66_all_passed)
        self.assertTrue(report.g13_to_g66_all_passed)
        self.assertEqual(report.summary["total_gates"], 66)
        self.assertEqual(report.summary["verified_gates"], 63)
        self.assertEqual(report.summary["technical_gates_passed"], 63)
        self.assertEqual(report.summary["g65_to_g66_verified"], 2)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_27_preflight_dry_run_mode_verifies_66_of_66_with_redlines_locked(self) -> None:
        report = run_66_gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.all_66_gates_verified)
        self.assertEqual(report.summary["verified_gates"], 66)
        self.assertEqual(report.summary["technical_gates_passed"], 66)
        self.assertEqual(report.status, "VERIFIED_ALL_66_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_28_preflight_clean_room_mode_verifies_63_offline_and_66_dry_run(self) -> None:
        r_off = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(r_off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_off.offline_63_gates_verified)
        self.assertEqual(r_off.summary["verified_gates"], 63)

        r_dry = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r_dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_dry.all_66_gates_verified)
        self.assertEqual(r_dry.summary["verified_gates"], 66)

    def test_29_preflight_gate_order_places_g65_and_g66_at_indices_64_and_65(self) -> None:
        report = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.gates[64]["gate_id"], G65_GATE_ID)
        self.assertEqual(report.gates[64]["gate_code"], G65_GATE_CODE)
        self.assertEqual(report.gates[65]["gate_id"], G66_GATE_ID)
        self.assertEqual(report.gates[65]["gate_code"], G66_GATE_CODE)

    def test_30_preflight_propagates_g65_uvc_or_dcc1_fault(self) -> None:
        r_uvc = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            nouvc_dcc1_pd_kwargs={"uvc_uac_gadget_requested": True},
        )
        self.assertFalse(r_uvc.all_66_gates_verified)
        self.assertFalse(r_uvc.g65_to_g66_all_passed)
        self.assertEqual(r_uvc.status, STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN)
        self.assertEqual(r_uvc.summary["verified_gates"], 65)

        r_dcc1 = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            nouvc_dcc1_pd_kwargs={
                "power_source": POWER_SOURCE_DC_C1_COUPLER,
                "usb_pd_watts": 30.0,
                "emarked_5a_cable": False,
                "cable_max_amps": 3.0,
            },
        )
        self.assertFalse(r_dcc1.all_66_gates_verified)
        self.assertEqual(
            r_dcc1.status, STATUS_BLOCKED_G65_DC_C1_INSUFFICIENT_PD_OR_NON_5A_CABLE
        )

    def test_31_preflight_propagates_g66_lut_path_cineei_or_bt_fault(self) -> None:
        r_path = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_path_cineei_bt_kwargs={
                "media_type": MEDIA_TYPE_CFEXPRESS_A,
                "lut_directory": SD_USER_LUT_DIR,
            },
        )
        self.assertFalse(r_path.all_66_gates_verified)
        self.assertFalse(r_path.g65_to_g66_all_passed)
        self.assertEqual(
            r_path.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
        )
        self.assertEqual(r_path.summary["verified_gates"], 65)

        r_bt = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_path_cineei_bt_kwargs={"smartphone_gps_location_link_active": True},
        )
        self.assertFalse(r_bt.all_66_gates_verified)
        self.assertEqual(
            r_bt.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

    def test_32_preflight_propagates_g58_to_g64_faults_and_persistent_write_block(
        self,
    ) -> None:
        for kwargs, expected_status in (
            (
                {"bench_interlock_kwargs": {"auto_flash_requested": True}},
                STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
            ),
            (
                {"ssboot_wbi2_kwargs": {"blkroset_nflasha5": 0}},
                STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
            ),
            (
                {"slot1_ufu_c2pa_kwargs": {"body_firmware_version": "2.02"}},
                STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
            ),
            (
                {"emount_breathing_kwargs": {"lens_id": 0x0001}},
                STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
            ),
            (
                {"hdmi_raw_kwargs": {"sdi_mmio_probes_emitted": 1}},
                STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
            ),
            (
                {"fx3a_firewall_kwargs": {"body_model_name": FX3A_MODEL_NAME}},
                STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
            ),
            (
                {"xlrh1_mishoe_kwargs": {"body_35mm_mic_plugged": True}},
                STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
            ),
        ):
            r = evaluate_66gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated=True,
                **kwargs,
            )
            self.assertFalse(r.all_66_gates_verified)
            self.assertEqual(r.status, expected_status)

        r_pw = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r_pw.all_66_gates_verified)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_33_dry_run_simulated_backup_alias_flag_works(self) -> None:
        report = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertTrue(report.all_66_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 66)

    # --- 7. Backward Compatibility: 58/60/62/64-Gate Preflights & CLIs Intact ---

    def test_34_backward_compatibility_58_60_62_64_preflights_intact(self) -> None:
        r58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r58.summary["verified_gates"], 58)
        self.assertTrue(r58.all_58_gates_verified)

        r60 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r60.summary["verified_gates"], 60)
        self.assertTrue(r60.all_60_gates_verified)

        r62 = evaluate_62gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r62.summary["verified_gates"], 62)
        self.assertTrue(r62.all_62_gates_verified)

        r64 = evaluate_64gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r64.summary["verified_gates"], 64)
        self.assertTrue(r64.all_64_gates_verified)

        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 64),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)

    # --- 8. Edge-Case Coverage Matrix for G65 & G66 ---

    def test_35_g65_hdmi_and_none_streaming_transports_allowed(self) -> None:
        for tr in ("HDMI", "HDMI_TYPE_A", "TYPE_A_HDMI", "NONE"):
            res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
                usb_connection_mode="MTP",
                streaming_transport=tr,
                streaming_bitrate_mbps=0.0,
            )
            self.assertTrue(res.valid, f"failed for transport={tr}: {res.errors}")

    def test_36_g65_body_model_id_hex_string_normalization(self) -> None:
        res = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            body_model_name="ILME-FX3",
            body_model_id="0x91030080",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.body_model_id, 0x91030080)
        self.assertEqual(res.body_model_id_hex, "0x91030080")

    def test_37_g65_usb_pd_body_100pct_and_dcc1_100w_boundary(self) -> None:
        r_body = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_USB_PD_BODY,
            np_fz100_inserted=True,
            battery_pct=100,
            battery_bars=5,
        )
        self.assertTrue(r_body.valid, r_body.errors)

        r_dcc1 = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            power_source=POWER_SOURCE_DC_C1_COUPLER,
            usb_pd_watts=100.0,
            emarked_5a_cable=True,
            cable_max_amps=5.0,
            lcd_max_brightness_locked=False,
        )
        self.assertTrue(r_dcc1.valid, r_dcc1.errors)
        self.assertEqual(r_dcc1.warnings, ())

    def test_38_g65_rejects_negative_bitrate_and_non_bool_flags(self) -> None:
        r_neg = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            streaming_bitrate_mbps=-1.0,
        )
        self.assertFalse(r_neg.valid)
        self.assertEqual(r_neg.status, STATUS_BLOCKED_G65_TELEMETRY_INVALID)

        r_bool = verify_fx3_nouvc_gadget_and_usbpd_dcc1_guard(
            emarked_5a_cable="yes",  # type: ignore[arg-type]
        )
        self.assertFalse(r_bool.valid)
        self.assertEqual(r_bool.status, STATUS_BLOCKED_G65_TELEMETRY_INVALID)

    def test_39_g66_allows_sony_third_ev_ui_labels_and_rejects_negative_ev(self) -> None:
        for ev in (0.0, 0.3, 0.333, 0.7, 0.667, 1.0, 1.3, 1.7, 2.0):
            res = verify_dualmedia_lut_path_cineei_and_bt_guard(ae_level_offset_ev=ev)
            self.assertTrue(res.valid, f"failed for ev={ev}: {res.errors}")

        res_neg = verify_dualmedia_lut_path_cineei_and_bt_guard(ae_level_offset_ev=-0.3)
        self.assertFalse(res_neg.valid)
        self.assertEqual(
            res_neg.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

    def test_40_g66_rejects_slot_index_exceeding_registered_count_or_zero(self) -> None:
        res_zero = verify_dualmedia_lut_path_cineei_and_bt_guard(lut_slot_index=0)
        self.assertFalse(res_zero.valid)
        self.assertEqual(
            res_zero.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

        res_gt = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_slot_index=5,
            registered_lut_count=4,
        )
        self.assertFalse(res_gt.valid)
        self.assertEqual(res_gt.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING)

    def test_41_g66_blocks_dev_nflasha_and_setting_lut_paths(self) -> None:
        for bad_dir in (
            "/setting/lut/",
            "/dev/nflasha2/lut/",
            "/dev/cnflasha15/lut/",
            "/DCIM/",
        ):
            res = verify_dualmedia_lut_path_cineei_and_bt_guard(lut_directory=bad_dir)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE
            )

    def test_42_g66_normalizes_trailing_slash_on_media_lut_dir(self) -> None:
        res_sd = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type="SDXC",
            lut_directory="/Private/Sony/PRO/LUT",
        )
        self.assertTrue(res_sd.valid, res_sd.errors)

        res_cfe = verify_dualmedia_lut_path_cineei_and_bt_guard(
            media_type="CFexpress Type A",
            lut_directory="/Sony/PRO/LUT",
        )
        self.assertTrue(res_cfe.valid, res_cfe.errors)

    def test_43_g66_requires_cube_extension_and_rejects_wrong_bt_version_or_remote(
        self,
    ) -> None:
        res_ext = verify_dualmedia_lut_path_cineei_and_bt_guard(
            lut_filename="SLog3_to_Rec709.3dl"
        )
        self.assertFalse(res_ext.valid)
        self.assertEqual(
            res_ext.status, STATUS_BLOCKED_G66_CUBE_LUT_SPEC_OR_SLOT_CEILING
        )

        res_btver = verify_dualmedia_lut_path_cineei_and_bt_guard(bt_spec_version="5.3")
        self.assertFalse(res_btver.valid)
        self.assertEqual(
            res_btver.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

        res_rmt = verify_dualmedia_lut_path_cineei_and_bt_guard(remote_model="RMT-DSLR2")
        self.assertFalse(res_rmt.valid)
        self.assertEqual(
            res_rmt.status, STATUS_BLOCKED_G66_RMT_P1BT_BT_IR_GPS_MUTEX_VIOLATION
        )

    def test_44_g66_allows_ir_remote_on_original_fx3_when_bt_rmt_ctrl_off(self) -> None:
        res = verify_dualmedia_lut_path_cineei_and_bt_guard(
            body_model_name=FX3_MODEL_NAME,
            bluetooth_rmt_ctrl_enabled=False,
            ir_remote_receiver_disabled=False,
            ir_remote_active=True,
        )
        self.assertTrue(res.valid, res.errors)

    # --- 9. CLI Subcommands, Zero Raw Firmware Leakage & Runtime Budget ---

    def test_45_cli_verify_g65_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g65-nouvc-dcc1-pd", "--force-clean-room", "--json"],
            ["verify-g65-nouvc-dcc1-pd", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G65)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(data["nouvc_dcc1_pd_guard"]["uvc_gadget_blocked"])
            else:
                self.assertIn(f"gate={G65_GATE_ID}", buf.getvalue())

    def test_46_cli_verify_g66_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g66-lut-path-cineei-bt", "--force-clean-room", "--json"],
            ["verify-g66-lut-path-cineei-bt", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G66)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertEqual(
                    data["lut_path_cineei_bt_guard"]["expected_lut_directory"],
                    SD_USER_LUT_DIR,
                )
            else:
                self.assertIn(f"gate={G66_GATE_ID}", buf.getvalue())

    def test_47_cli_verify_66_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-66-gates", "--force-clean-room", "--json"], 63),
            (["verify-66-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 66),
            (["verify-66-gates", "--force-clean-room"], None),
            (["verify-66-gates", "--force-clean-room", "--dry-run-simulated"], None),
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
        self.assertEqual(payload["summary"]["verified_gates"], 66)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["human_hardware_attach_token"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_49_module_cli_text_output_smoke(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=66/66", out)
        self.assertIn("g65_to_g66_all_passed=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_50_verify_66_gates_fast_runtime_under_6s(self) -> None:
        t0 = time.monotonic()
        report = evaluate_66gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(report.all_66_gates_verified)
        self.assertLess(elapsed, 6.0)

    def test_51_status_constants_and_allowed_collections_consistency(self) -> None:
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(STATUS_VERIFIED_SAFE, "VERIFIED_SAFE")
        self.assertIn("ILME-FX3", ALLOWED_NOUVC_BODY_MODELS)
        self.assertIn("ILME-FX3A", ALLOWED_NOUVC_BODY_MODELS)
        self.assertIn("USB_LAN", ALLOWED_FX3_USB_CONNECTION_MODES)
        self.assertIn("UVC_UAC", FORBIDDEN_FX3_UVC_MODES)
        self.assertIn("RTMP", NETWORK_STREAMING_TRANSPORTS)
        self.assertIn("HDMI_TYPE_A", ALLOWED_4K_STREAMING_TRANSPORTS)
        self.assertEqual(VALID_POWER_SOURCES, ("USB_PD_BODY", "DC_C1_COUPLER"))
        self.assertEqual(CINE_EI_RANGE_BY_BASE[800], (200, 3200))
        self.assertEqual(CINE_EI_RANGE_BY_BASE[12800], (3200, 51200))
        self.assertIn("p2:", FORBIDDEN_STAGEB_LUT_WRITE_PREFIXES)
        self.assertEqual(USER_LUT_AE_OFFSET_MIN_EV, 0.0)
        self.assertEqual(USER_LUT_AE_OFFSET_MAX_EV, 2.0)

    def test_52_report_serialization_roundtrip_is_pure_json(self) -> None:
        report = run_66_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        serialized = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(serialized)
        self.assertEqual(parsed["schema"], REALHW_NOUVC_DCC1_PD_LUT_PATH_66GATE_SCHEMA)
        self.assertEqual(len(parsed["gates"]), 66)
        self.assertEqual(parsed["summary"]["technical_gates_passed"], 66)


if __name__ == "__main__":
    unittest.main()
