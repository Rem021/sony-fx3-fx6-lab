"""Fast dual-mode unit tests for Milestone Phase 120 — Unnegotiated 20V USB-C PD
Trigger-Cable / Dual-Source D-Tap+USB-PD Cross-Feed & Isochronous UVC 1.5 Thermal
Firewall (Gate G37), Sony 15-Pin Multi-Terminal LTC +5V Clash / 3.3V UART Over-Drive
& Destructive CRSDK PTP Flash-Opcode Hardware Guard (Gate G38), and Unified
38-Gate Master Safety Preflight (`G01..G38`).
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
from fx3_safety.hdmi_aoc_5v_cfexpress_and_36gate_guard import (
    STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR,
    STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH,
    evaluate_36gate_preflight,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.usbpd_trigger_multiterminal_and_38gate_guard import (
    CXD90057_UART_IO_ABSOLUTE_MAX_V,
    CXD90057_UART_NOMINAL_V,
    G37_GATE_CODE,
    G37_GATE_ID,
    G38_GATE_CODE,
    G38_GATE_ID,
    MULTITERMINAL_LTC_MAX_VPP,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PTP_DESTRUCTIVE_FW_FLASH_OPCODES,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH,
    STATUS_BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE,
    STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD,
    STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED,
    STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE,
    STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID,
    STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION,
    STATUS_SAFE,
    STATUS_VERIFIED_G37,
    STATUS_VERIFIED_G38,
    STATUS_VERIFIED_SAFE,
    USBC_VBUS_UNNEGOTIATED_MAX_V,
    USBPD_MULTITERMINAL_38GATE_SCHEMA,
    USBPD_MULTITERMINAL_38GATE_VERSION,
    UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C,
    UVC_4K30P_THERMAL_SATURATION_HOURS,
    audit_phase120_donor_contracts,
    compute_uart_pad_overdrive_ratio,
    compute_usbpd_contract_watts,
    estimate_uvc_4k30p_thermal_rise_c,
    evaluate_38_master_safety_gates,
    evaluate_38gate_preflight,
    evaluate_g37_usbpd_trigger_and_uvc_thermal,
    evaluate_g38_multiterminal_ltc_uart_and_ptp,
    main as module_cli_main,
    verify_multiterminal_ltc_uart_and_ptp_guard,
    verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall,
)


class UsbPdTriggerMultiTerminalAnd38GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            USBPD_MULTITERMINAL_38GATE_SCHEMA,
            "fx3-usbpd-trigger-multiterminal-38gate-preflight-v1",
        )
        self.assertEqual(USBPD_MULTITERMINAL_38GATE_VERSION, "1.0.0")
        for sym in (
            "USBPD_MULTITERMINAL_38GATE_SCHEMA",
            "G37_GATE_ID",
            "G37_GATE_CODE",
            "G38_GATE_ID",
            "G38_GATE_CODE",
            "STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE",
            "STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED",
            "STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION",
            "STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH",
            "STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD",
            "STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE",
            "audit_phase120_donor_contracts",
            "compute_usbpd_contract_watts",
            "estimate_uvc_4k30p_thermal_rise_c",
            "compute_uart_pad_overdrive_ratio",
            "verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall",
            "verify_multiterminal_ltc_uart_and_ptp_guard",
            "evaluate_g37_usbpd_trigger_and_uvc_thermal",
            "evaluate_g38_multiterminal_ltc_uart_and_ptp",
            "evaluate_38gate_preflight",
            "evaluate_38_master_safety_gates",
            "usbpd_trigger_multiterminal_and_38gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain intact
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(
            fx3_safety.HDMI_AOC_CFEXPRESS_36GATE_SCHEMA,
            "fx3-hdmi-aoc-5v-cfexpress-36gate-preflight-v1",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase120_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.usbpd_buspower_tokens_verified)
        self.assertTrue(res_default.multiport_usbctrl_tokens_verified)
        self.assertTrue(res_default.ptp_crsdk_control_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libBusPower",
                    "libUsbBusPower",
                    "libUsbControl",
                    "libInfraPtpControl",
                )
            ):
                self.assertEqual(
                    flags & os.O_ACCMODE,
                    os.O_RDONLY,
                    f"Non-O_RDONLY open on {path}",
                )

        res_clean = audit_phase120_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 8)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = (
                tmp
                / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            )
            fx6_lib = (
                tmp
                / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            )
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for d in (fx3_lib, fx6_lib):
                for name in (
                    "libBusPower.so",
                    "libUsbBusPower.so",
                    "libUsbControl.so",
                    "libInfraPtpControl.so",
                ):
                    (d / name).write_bytes(b"corrupt")
            res = audit_phase120_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 8)
        self.assertFalse(res.usbpd_buspower_tokens_verified)
        self.assertFalse(res.multiport_usbctrl_tokens_verified)
        self.assertFalse(res.ptp_crsdk_control_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase120_donor_contracts(
            force_clean_room=True, include_large_binaries=True
        )
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase120_donor_contracts(
                work_root=Path(empty_dir), force_clean_room=False
            )
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Electrical, UVC Thermal & 1.8V UART Over-Drive Helpers ---

    def test_05_usbpd_contract_watts_and_uart_overdrive_helpers(self) -> None:
        self.assertAlmostEqual(compute_usbpd_contract_watts(9.0, 3.0), 27.0, places=6)
        self.assertAlmostEqual(compute_usbpd_contract_watts(20.0, 3.0), 60.0, places=6)
        self.assertAlmostEqual(
            compute_uart_pad_overdrive_ratio(3.3), 3.3 / 1.8, places=6
        )
        self.assertAlmostEqual(
            compute_uart_pad_overdrive_ratio(1.8), 1.0, places=6
        )
        with self.assertRaises(ValueError):
            compute_usbpd_contract_watts(-9.0, 3.0)
        with self.assertRaises(ValueError):
            compute_uart_pad_overdrive_ratio(-1.0)
        with self.assertRaises(ValueError):
            compute_uart_pad_overdrive_ratio(1.8, nominal_pad_v=0.0)

    def test_06_uvc_4k30p_thermal_rise_helper(self) -> None:
        t_no_chg = estimate_uvc_4k30p_thermal_rise_c(
            2.0, 36.0, internal_np_fz100_charging_while_streaming=False
        )
        t_with_chg = estimate_uvc_4k30p_thermal_rise_c(
            2.0, 36.0, internal_np_fz100_charging_while_streaming=True
        )
        self.assertGreater(t_with_chg, t_no_chg)
        self.assertAlmostEqual(t_with_chg - t_no_chg, 9.0, places=6)
        with self.assertRaises(ValueError):
            estimate_uvc_4k30p_thermal_rise_c(-0.5, 25.0)
        with self.assertRaises(ValueError):
            estimate_uvc_4k30p_thermal_rise_c(1.0, 120.0)

    # --- 3. Gate G37 — USB-C PD 20V Trigger, Dual-Source Cross-Feed & UVC Thermal ---

    def test_07_g37_default_safe_profile_passes(self) -> None:
        res = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.usbc_trigger_cable_safe)
        self.assertTrue(res.dual_power_crossfeed_safe)
        self.assertTrue(res.uvc_thermal_saturation_safe)
        self.assertTrue(res.valid_9v_3a_pd_pdo_contract)
        self.assertAlmostEqual(res.pd_contract_power_w, 27.0, places=2)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g37_blocks_unnegotiated_20v_trigger_cable_and_cc_short(self) -> None:
        res_20v = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            power_profile="PASSIVE_DTAP_TO_USBC_20V_TRIGGER_CABLE",
            usbc_vbus_measured_v=20.0,
            valid_9v_3a_pd_pdo_contract=False,
        )
        self.assertFalse(res_20v.valid)
        self.assertFalse(res_20v.usbc_trigger_cable_safe)
        self.assertEqual(
            res_20v.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )

        res_14v8 = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=14.8,
            valid_9v_3a_pd_pdo_contract=False,
        )
        self.assertFalse(res_14v8.valid)
        self.assertEqual(
            res_14v8.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )

        res_cc = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=9.0,
            cc_pin_short_to_vbus=True,
        )
        self.assertFalse(res_cc.valid)
        self.assertEqual(
            res_cc.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )

        # Exact 9.6V boundary passes
        res_edge = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=USBC_VBUS_UNNEGOTIATED_MAX_V,
            valid_9v_3a_pd_pdo_contract=True,
        )
        self.assertTrue(res_edge.valid)

        # Standard 5V USB-C data-only rail passes
        res_5v = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=5.0,
            valid_9v_3a_pd_pdo_contract=False,
        )
        self.assertTrue(res_5v.valid)

    def test_09_g37_blocks_unisolated_dtap_usbpd_dual_power_crossfeed(self) -> None:
        res_bad = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            unregulated_dummy_battery_active=True,
            usbc_pd_power_sink_active=True,
            common_vmount_battery_shared_without_dc_isolator=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.dual_power_crossfeed_safe)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED,
        )

        # DC-DC isolated dual source passes with advisory warning
        res_iso = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            unregulated_dummy_battery_active=True,
            usbc_pd_power_sink_active=True,
            common_vmount_battery_shared_without_dc_isolator=False,
        )
        self.assertTrue(res_iso.valid)
        self.assertGreaterEqual(len(res_iso.warnings), 1)

        # Single source (USB-PD off) passes
        res_single = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            unregulated_dummy_battery_active=True,
            usbc_pd_power_sink_active=False,
            common_vmount_battery_shared_without_dc_isolator=True,
        )
        self.assertTrue(res_single.valid)

    def test_10_g37_blocks_uvc_4k30p_continuous_thermal_saturation(self) -> None:
        res_bad = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            uvc_4k30p_streaming_hours=2.0,
            ambient_temp_c=37.5,
            internal_np_fz100_charging_while_streaming=True,
            auto_power_off_temp_standard=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.uvc_thermal_saturation_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION
        )

        # Exact 35.0 C ambient boundary passes
        res_amb_edge = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            uvc_4k30p_streaming_hours=2.5,
            ambient_temp_c=UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C,
            internal_np_fz100_charging_while_streaming=True,
            auto_power_off_temp_standard=True,
        )
        self.assertTrue(res_amb_edge.valid)

        # Below 2.0h passes
        res_short = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            uvc_4k30p_streaming_hours=1.95,
            ambient_temp_c=38.0,
            internal_np_fz100_charging_while_streaming=True,
            auto_power_off_temp_standard=True,
        )
        self.assertTrue(res_short.valid)

        # Auto Power OFF Temp=High mitigates
        res_high = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            uvc_4k30p_streaming_hours=3.0,
            ambient_temp_c=38.0,
            internal_np_fz100_charging_while_streaming=True,
            auto_power_off_temp_standard=False,
        )
        self.assertTrue(res_high.valid)
        self.assertGreaterEqual(len(res_high.warnings), 1)

        # Internal charging disabled while streaming mitigates
        res_nochg = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            uvc_4k30p_streaming_hours=3.0,
            ambient_temp_c=38.0,
            internal_np_fz100_charging_while_streaming=False,
            auto_power_off_temp_standard=True,
        )
        self.assertTrue(res_nochg.valid)

    def test_11_g37_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"usbc_vbus_measured_v": float("nan")},
            {"usbc_vbus_measured_v": -1.0},
            {"pd_contract_voltage_v": float("inf")},
            {"pd_contract_current_a": -0.5},
            {"uvc_4k30p_streaming_hours": -0.1},
            {"ambient_temp_c": -60.0},
            {"ambient_temp_c": 95.0},
        ):
            res_bad = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)

        res_emmc = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g37_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=20.0,
            valid_9v_3a_pd_pdo_contract=False,
            cc_pin_short_to_vbus=True,
            unregulated_dummy_battery_active=True,
            usbc_pd_power_sink_active=True,
            common_vmount_battery_shared_without_dc_isolator=True,
            uvc_4k30p_streaming_hours=2.5,
            ambient_temp_c=39.0,
            internal_np_fz100_charging_while_streaming=True,
            auto_power_off_temp_standard=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE,
                STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED,
                STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION,
            },
        )

    # --- 4. Gate G38 — Multi-Terminal LTC +5V Clash, 1.8V UART & PTP Flash Guard ---

    def test_13_g38_default_safe_profile_passes(self) -> None:
        res = verify_multiterminal_ltc_uart_and_ptp_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.multiterminal_ltc_voltage_safe)
        self.assertTrue(res.uart_1v8_rx_only_safe)
        self.assertTrue(res.ptp_fw_flash_opcode_guard_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(
            len(res.blocked_ptp_opcodes_hex), len(PTP_DESTRUCTIVE_FW_FLASH_OPCODES)
        )

    def test_14_g38_blocks_multiterminal_ltc_voltage_clash_and_id_short(self) -> None:
        res_over = verify_multiterminal_ltc_uart_and_ptp_guard(
            ltc_bnc_adapter_attached=True,
            ltc_peak_to_peak_v=6.2,
        )
        self.assertFalse(res_over.valid)
        self.assertFalse(res_over.multiterminal_ltc_voltage_safe)
        self.assertEqual(
            res_over.status, STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH
        )

        res_id = verify_multiterminal_ltc_uart_and_ptp_guard(
            ltc_bnc_adapter_attached=True,
            ltc_peak_to_peak_v=2.0,
            third_party_non_sony_id_resistor_short=True,
        )
        self.assertFalse(res_id.valid)
        self.assertEqual(
            res_id.status, STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH
        )

        # Exact 5.0 Vpp boundary with valid Sony 680 kOhm ID resistor passes
        res_edge = verify_multiterminal_ltc_uart_and_ptp_guard(
            ltc_bnc_adapter_attached=True,
            ltc_peak_to_peak_v=MULTITERMINAL_LTC_MAX_VPP,
            third_party_non_sony_id_resistor_short=False,
        )
        self.assertTrue(res_edge.valid)
        self.assertGreaterEqual(len(res_edge.warnings), 1)

        # Detached LTC adapter ignores LTC voltage clash
        res_det = verify_multiterminal_ltc_uart_and_ptp_guard(
            ltc_bnc_adapter_attached=False,
            ltc_peak_to_peak_v=6.2,
            third_party_non_sony_id_resistor_short=True,
        )
        self.assertTrue(res_det.valid)

    def test_15_g38_blocks_uart_3v3_5v_overdrive_and_tx_connection(self) -> None:
        for bad_v in (3.3, 5.0, 2.0):
            res_over = verify_multiterminal_ltc_uart_and_ptp_guard(
                uart_probe_attached=True,
                uart_logic_level_v=bad_v,
                uart_tx_line_physically_connected=False,
            )
            self.assertFalse(res_over.valid)
            self.assertFalse(res_over.uart_1v8_rx_only_safe)
            self.assertEqual(
                res_over.status, STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD
            )

        # Connecting TX line physically even at 1.8V is blocked (strictly passive RX-only)
        res_tx = verify_multiterminal_ltc_uart_and_ptp_guard(
            uart_probe_attached=True,
            uart_logic_level_v=CXD90057_UART_NOMINAL_V,
            uart_tx_line_physically_connected=True,
        )
        self.assertFalse(res_tx.valid)
        self.assertEqual(
            res_tx.status, STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD
        )

        # Exact 1.95V boundary with TX disconnected passes
        res_edge = verify_multiterminal_ltc_uart_and_ptp_guard(
            uart_probe_attached=True,
            uart_logic_level_v=CXD90057_UART_IO_ABSOLUTE_MAX_V,
            uart_tx_line_physically_connected=False,
        )
        self.assertTrue(res_edge.valid)
        self.assertGreaterEqual(len(res_edge.warnings), 1)

    def test_16_g38_blocks_ptp_firmware_update_opcode_in_hybrid_mode(self) -> None:
        res_bad = verify_multiterminal_ltc_uart_and_ptp_guard(
            usb_ptp_crsdk_session_active=True,
            ptp_fw_flash_opcodes_blocked_in_filter=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.ptp_fw_flash_opcode_guard_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE
        )

        res_inactive = verify_multiterminal_ltc_uart_and_ptp_guard(
            usb_ptp_crsdk_session_active=False,
            ptp_fw_flash_opcodes_blocked_in_filter=False,
        )
        self.assertTrue(res_inactive.valid)

        res_filtered = verify_multiterminal_ltc_uart_and_ptp_guard(
            usb_ptp_crsdk_session_active=True,
            ptp_fw_flash_opcodes_blocked_in_filter=True,
        )
        self.assertTrue(res_filtered.valid)

    def test_17_g38_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"ltc_peak_to_peak_v": float("nan")},
            {"ltc_peak_to_peak_v": -0.5},
            {"uart_logic_level_v": float("inf")},
            {"uart_logic_level_v": -1.8},
        ):
            res_bad = verify_multiterminal_ltc_uart_and_ptp_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID
            )

        res_emmc = verify_multiterminal_ltc_uart_and_ptp_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_18_g38_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_multiterminal_ltc_uart_and_ptp_guard(
            ltc_bnc_adapter_attached=True,
            ltc_peak_to_peak_v=6.5,
            third_party_non_sony_id_resistor_short=True,
            uart_probe_attached=True,
            uart_logic_level_v=3.3,
            uart_tx_line_physically_connected=True,
            usb_ptp_crsdk_session_active=True,
            ptp_fw_flash_opcodes_blocked_in_filter=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH,
                STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD,
                STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE,
            },
        )

    # --- 5. Gate G37 & G38 Evaluators & Unified 38-Gate Master Preflight ---

    def test_19_g37_and_g38_verdicts_dual_mode(self) -> None:
        v37, r37 = evaluate_g37_usbpd_trigger_and_uvc_thermal(force_clean_room=True)
        self.assertTrue(v37.passed)
        self.assertEqual(v37.gate_id, G37_GATE_ID)
        self.assertEqual(v37.gate_code, G37_GATE_CODE)
        self.assertEqual(v37.status, STATUS_VERIFIED_G37)
        self.assertFalse(r37.persistent_emmc_writes_authorized)

        v38, r38 = evaluate_g38_multiterminal_ltc_uart_and_ptp(force_clean_room=True)
        self.assertTrue(v38.passed)
        self.assertEqual(v38.gate_id, G38_GATE_ID)
        self.assertEqual(v38.gate_code, G38_GATE_CODE)
        self.assertEqual(v38.status, STATUS_VERIFIED_G38)
        self.assertFalse(r38.persistent_emmc_writes_authorized)

    def test_20_38gate_offline_default_35_of_38_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_38gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, USBPD_MULTITERMINAL_38GATE_SCHEMA)
        self.assertGreaterEqual(len(rep.gates), 38)
        self.assertEqual(len(rep.gates), 38)
        self.assertGreaterEqual(rep.summary["total_gates"], 38)
        self.assertGreaterEqual(rep.summary["verified_gates"], 35)
        self.assertEqual(rep.summary["verified_gates"], 35)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_35_gates_verified)
        self.assertFalse(rep.all_38_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_35_OF_38_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_21_38gate_dry_run_simulated_backup_38_of_38_and_redlines_locked(self) -> None:
        rep = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(rep.gates), 38)
        self.assertGreaterEqual(rep.summary["verified_gates"], 38)
        self.assertEqual(rep.summary["verified_gates"], 38)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g36_verified"], 24)
        self.assertEqual(rep.summary["g37_to_g38_verified"], 2)
        self.assertTrue(rep.all_38_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_38_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_22_38gate_propagates_g37_trigger_crossfeed_and_uvc_failures(self) -> None:
        rep_trig = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            usbpd_uvc_kwargs={
                "usbc_vbus_measured_v": 20.0,
                "valid_9v_3a_pd_pdo_contract": False,
            },
        )
        self.assertFalse(rep_trig.all_38_gates_verified)
        self.assertFalse(rep_trig.g37_to_g38_all_passed)
        self.assertFalse(rep_trig.gates[36]["passed"])
        self.assertEqual(
            rep_trig.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )

        rep_cf = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            usbpd_uvc_kwargs={
                "unregulated_dummy_battery_active": True,
                "usbc_pd_power_sink_active": True,
                "common_vmount_battery_shared_without_dc_isolator": True,
            },
        )
        self.assertFalse(rep_cf.all_38_gates_verified)
        self.assertEqual(
            rep_cf.status, STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED
        )

        rep_uvc = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            usbpd_uvc_kwargs={
                "uvc_4k30p_streaming_hours": 2.5,
                "ambient_temp_c": 38.0,
                "internal_np_fz100_charging_while_streaming": True,
                "auto_power_off_temp_standard": True,
            },
        )
        self.assertFalse(rep_uvc.all_38_gates_verified)
        self.assertEqual(
            rep_uvc.status, STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION
        )

    def test_23_38gate_propagates_g38_ltc_uart_and_ptp_failures(self) -> None:
        rep_ltc = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            multiterminal_ptp_kwargs={
                "ltc_bnc_adapter_attached": True,
                "ltc_peak_to_peak_v": 6.0,
            },
        )
        self.assertFalse(rep_ltc.all_38_gates_verified)
        self.assertFalse(rep_ltc.gates[37]["passed"])
        self.assertEqual(
            rep_ltc.status, STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH
        )

        rep_uart = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            multiterminal_ptp_kwargs={
                "uart_probe_attached": True,
                "uart_logic_level_v": 3.3,
            },
        )
        self.assertFalse(rep_uart.all_38_gates_verified)
        self.assertEqual(
            rep_uart.status, STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD
        )

        rep_ptp = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            multiterminal_ptp_kwargs={
                "usb_ptp_crsdk_session_active": True,
                "ptp_fw_flash_opcodes_blocked_in_filter": False,
            },
        )
        self.assertFalse(rep_ptp.all_38_gates_verified)
        self.assertEqual(
            rep_ptp.status, STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE
        )

    def test_24_38gate_propagates_g35_g36_and_emmc_redline(self) -> None:
        rep_g35_g36 = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            hdmi_aoc_kwargs={
                "hdmi_pin18_draw_ma": 90.0,
                "external_hdmi_5v_power_injector": False,
            },
            cfexpress_media_kwargs={
                "slot_door_open_detected": True,
                "media_flush_or_fat_commit_pending": True,
            },
        )
        self.assertFalse(rep_g35_g36.all_38_gates_verified)
        self.assertFalse(rep_g35_g36.gates[34]["passed"])
        self.assertFalse(rep_g35_g36.gates[35]["passed"])
        self.assertEqual(
            rep_g35_g36.gates[34]["status"],
            STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR,
        )
        self.assertEqual(
            rep_g35_g36.gates[35]["status"],
            STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH,
        )
        self.assertEqual(
            rep_g35_g36.status, STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR
        )

        rep_emmc = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_38_gates_verified)
        self.assertFalse(rep_emmc.offline_35_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_25_38gate_preserves_g01_to_g36_untouched(self) -> None:
        r36 = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r38 = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r36.gates), 36)
        self.assertGreaterEqual(len(r38.gates), 38)
        self.assertEqual(
            [g["gate_id"] for g in r36.gates],
            [g["gate_id"] for g in r38.gates[:36]],
        )
        self.assertEqual(
            [g["status"] for g in r36.gates],
            [g["status"] for g in r38.gates[:36]],
        )

    def test_26_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_27_cli_verify_38_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-38-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], USBPD_MULTITERMINAL_38GATE_SCHEMA)
        self.assertGreaterEqual(p_off["summary"]["verified_gates"], 35)
        self.assertEqual(p_off["summary"]["verified_gates"], 35)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-38-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertGreaterEqual(p_dry["summary"]["verified_gates"], 38)
        self.assertTrue(p_dry["all_38_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_28_cli_verify_38_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=35/38", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-38-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=35/38", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-38-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_29_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], USBPD_MULTITERMINAL_38GATE_SCHEMA)
        self.assertTrue(payload["all_38_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_30_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_38gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_35_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_31_evaluate_38_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_38_master_safety_gates, evaluate_38gate_preflight)
        rep = evaluate_38_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_38_gates_verified)
        self.assertGreaterEqual(rep.summary["verified_gates"], 38)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_32_donor_corruption_propagates_to_g37_g38_and_38gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = (
                tmp
                / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            )
            fx6_lib = (
                tmp
                / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            )
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for d in (fx3_lib, fx6_lib):
                for name in (
                    "libBusPower.so",
                    "libUsbBusPower.so",
                    "libUsbControl.so",
                    "libInfraPtpControl.so",
                ):
                    (d / name).write_bytes(b"bad")
            v37, r37 = evaluate_g37_usbpd_trigger_and_uvc_thermal(
                work_root=tmp, force_clean_room=False
            )
            v38, r38 = evaluate_g38_multiterminal_ltc_uart_and_ptp(
                work_root=tmp, force_clean_room=False
            )
        self.assertFalse(v37.passed)
        self.assertFalse(r37.valid)
        self.assertEqual(v37.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v38.passed)
        self.assertFalse(r38.valid)
        self.assertEqual(v38.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_33_prior_cli_subcommands_verify_16_through_36_remain_intact(self) -> None:
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
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_34_g37_g38_gate_ids_and_soc_passthrough_in_38gate_report(self) -> None:
        rep = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_38_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[36]["gate_id"], G37_GATE_ID)
        self.assertEqual(rep.gates[36]["gate_code"], G37_GATE_CODE)
        self.assertEqual(rep.gates[37]["gate_id"], G38_GATE_ID)
        self.assertEqual(rep.gates[37]["gate_code"], G38_GATE_CODE)

    def test_35_38gate_summary_blocks_if_g37_or_g38_requests_emmc_write(self) -> None:
        rep_37 = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            usbpd_uvc_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_37.all_38_gates_verified)
        self.assertFalse(rep_37.g37_to_g38_all_passed)
        self.assertFalse(rep_37.gates[36]["passed"])
        self.assertEqual(rep_37.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_37.persistent_emmc_writes_authorized)

        rep_38 = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            multiterminal_ptp_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_38.all_38_gates_verified)
        self.assertFalse(rep_38.g37_to_g38_all_passed)
        self.assertFalse(rep_38.gates[37]["passed"])
        self.assertEqual(rep_38.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_38.persistent_emmc_writes_authorized)

    def test_36_g37_12v_and_15v_decoy_cables_also_blocked(self) -> None:
        for decoy_v in (12.0, 15.0, 20.0):
            res = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
                usbc_vbus_measured_v=decoy_v,
                valid_9v_3a_pd_pdo_contract=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
            )

    def test_37_g38_uart_1v8_passive_rx_only_explicit_safe_mode(self) -> None:
        res = verify_multiterminal_ltc_uart_and_ptp_guard(
            interface_profile="RP2040_ZERO_1V8_OPEN_DRAIN_RX_ONLY",
            uart_probe_attached=True,
            uart_logic_level_v=1.8,
            uart_tx_line_physically_connected=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.uart_1v8_rx_only_safe)
        self.assertAlmostEqual(res.uart_pad_overdrive_ratio, 1.0, places=3)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_38_g37_9v3a_nominal_contract_and_pdo_power_validation(self) -> None:
        res = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
            usbc_vbus_measured_v=9.05,
            valid_9v_3a_pd_pdo_contract=True,
            pd_contract_voltage_v=9.0,
            pd_contract_current_a=3.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.valid_9v_3a_pd_pdo_contract)
        self.assertAlmostEqual(res.pd_contract_power_w, 27.0, places=2)

    def test_39_donor_audit_large_binaries_dual_mode(self) -> None:
        res = audit_phase120_donor_contracts(include_large_binaries=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertTrue(res.large_binaries_scanned)
            self.assertGreaterEqual(res.files_inspected, 8)
        else:
            self.assertFalse(res.large_binaries_scanned)

    def test_40_h0_h1_trial_entry_allowed_and_g13_to_g38_flags(self) -> None:
        rep_off = evaluate_38gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g38_all_passed)
        self.assertTrue(rep_off.g37_to_g38_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            usbpd_uvc_kwargs={"cc_pin_short_to_vbus": True},
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g38_all_passed)
        self.assertFalse(rep_bad.offline_35_gates_verified)

    def test_41_g38_sony_vmc_bncm1_safe_ltc_2vpp_passes(self) -> None:
        res = verify_multiterminal_ltc_uart_and_ptp_guard(
            interface_profile="SONY_VMC_BNCM1_680KOHM_LTC_IN",
            ltc_bnc_adapter_attached=True,
            ltc_peak_to_peak_v=2.0,
            third_party_non_sony_id_resistor_short=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.multiterminal_ltc_voltage_safe)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_42_38gate_report_to_dict_has_expected_top_level_keys(self) -> None:
        rep = evaluate_38gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        for key in (
            "schema",
            "version",
            "verification_mode",
            "offline_35_gates_verified",
            "all_38_gates_verified",
            "g13_to_g38_all_passed",
            "g37_to_g38_all_passed",
            "overall_ready_for_hardware_attach",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "summary",
            "gates",
            "master_36_report",
            "g37_result",
            "g38_result",
        ):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
