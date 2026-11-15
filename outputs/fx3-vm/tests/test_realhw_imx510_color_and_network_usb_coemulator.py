#!/usr/bin/env python3
"""Phase 157 Test Suite — Stage 27 (`27/27`) Real-Hardware Main Track Part 10:
`IMX510` Dual-Base ISO `800/12800`, `psd.bin/defdet.bin` Sensor NVS, `.cube` 3D MLUT,
`CDC-NCM` USB-LAN `Monitor & Control` & `054C:0DA1` Recovery-Port HIL Co-Emulator.

Exercises 46 fast dual-mode unit, integration, Pillar A-D HIL, Stage 27 suite
orchestration (`27/27` stages), CLI, runtime-budget, and clean-room hygiene checks.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_imx510_color_and_network_usb_coemulator as p157  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_default_audit() -> dict:
    key = ("default", p157.is_forced_clean_room())
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p157.run_phase157_realhw_imx510_network_usb_hil(env=os.environ)
    return _AUDIT_CACHE[key]


def _get_clean_room_audit() -> dict:
    key = ("clean_room", True)
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p157.run_phase157_realhw_imx510_network_usb_hil(
            force_clean_room=True,
            env=os.environ,
        )
    return _AUDIT_CACHE[key]


class TestStage27DualModeDonorsAndRedlines(unittest.TestCase):
    """Dual-mode O_RDONLY donor inspection, clean-room fallback, and safety redlines."""

    def test_01_donor_path_resolution_matches_clean_room_toggle(self) -> None:
        paths_clean = p157.resolve_phase157_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 16)
        for p in paths_clean.values():
            self.assertIn(p157.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_02_clean_room_synthetic_fixtures_valid_elf_cpapp_and_bk4(self) -> None:
        fx = p157.build_clean_room_phase157_fixtures()
        self.assertEqual(len(fx), 16)
        for k in (
            "fx3_msc",
            "fx6_msc",
            "fx3_usb",
            "fx6_usb",
            "fx3_wlan_adjust",
            "fx6_wlan_adjust",
            "fx3_wlan_resource",
            "fx6_wlan_resource",
            "fx3_sencore",
            "fx6_sencore",
            "fx3_libmpr",
            "fx6_libmpr",
        ):
            self.assertEqual(fx[k][:4], b"\x7fELF")
        self.assertEqual(fx["fx3_backup"][12:16], b"BK4\x00")
        self.assertEqual(fx["fx6_backup"][12:16], b"BK4\x00")

    def test_03_clean_room_donor_audit_verifies_all_16_contracts(self) -> None:
        da = p157.inspect_phase157_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da.access_mode, "O_RDONLY")
        self.assertEqual(da.donor_files_inspected, 16)
        self.assertTrue(da.msc_abi_zero_diff)
        self.assertTrue(da.usb_abi_zero_diff)
        self.assertTrue(da.wlan_adjust_abi_zero_diff)
        self.assertTrue(da.wlan_resource_abi_zero_diff)
        self.assertTrue(da.sencore_symbol_parity)
        self.assertTrue(da.all_contracts_verified, msg=str(da.errors))

    def test_04_missing_donor_directory_falls_back_deterministically(self) -> None:
        fake_env = {
            "FX3_FX6_MAC_WORK_ROOT": "/nonexistent/fx3/work/path",
            "FX3_FX6_MAIN_LAB_WORK_ROOT": "/nonexistent/fx3/main/path",
            "FX3_FX6_MAC_ROOT": "/nonexistent/fx3/mac/path",
        }
        da = p157.inspect_phase157_donors(force_clean_room=True, env=fake_env)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)

    def test_05_stage27_clean_room_execution_fast_and_redlines_locked(self) -> None:
        t0 = time.monotonic()
        rep = _get_clean_room_audit()
        dt = time.monotonic() - t0
        self.assertLess(dt, 0.25)
        self.assertEqual(rep["schema"], p157.PHASE_157_SCHEMA)
        self.assertEqual(rep["version"], p157.PHASE_157_VERSION)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["sensor_cal_mutation_bytes"], 0)
        self.assertFalse(red["psd_defdet_writes_permitted"])
        self.assertFalse(red["rf_nvs_p12_p13_writes_permitted"])
        self.assertEqual(red["rf_nvs_p12_p13_mutation_bytes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["emmc_nflasha_write_count"], 0)
        self.assertFalse(red["slog3_master_double_baked"])
        self.assertEqual(red["bt_hci_blocking_wait_ms"], 0)
        self.assertTrue(red["bt_hci_blocking_wait_eliminated"])
        self.assertTrue(red["usb_msc_0da1_recovery_intact"])
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_06_local_or_clean_default_mode_passes_all_checks(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 16)
        self.assertTrue(rep["donor_audit"]["all_contracts_verified"])

    @unittest.skipUnless(
        (not p157.is_forced_clean_room())
        and all(p.is_file() for p in p157.resolve_phase157_donor_paths().values()),
        "Local FX3/FX6 donor images absent or FX3_FX6_FORCE_CLEAN_ROOM=1",
    )
    def test_07_local_rdonly_donors_exact_bytes_abi_and_imx510_markers(self) -> None:
        rep = _get_default_audit()
        self.assertEqual(rep["source_mode"], "LOCAL_DONOR_RDONLY")
        da = rep["donor_audit"]
        self.assertEqual(da["fx3_msc"]["file_bytes"], 64_456)
        self.assertEqual(da["fx6_msc"]["file_bytes"], 64_456)
        self.assertEqual(da["fx3_usb"]["file_bytes"], 135_424)
        self.assertEqual(da["fx6_usb"]["file_bytes"], 135_424)
        self.assertEqual(da["fx3_wlan_adjust"]["file_bytes"], 73_168)
        self.assertEqual(da["fx6_wlan_adjust"]["file_bytes"], 73_168)
        self.assertEqual(da["fx3_wlan_resource"]["file_bytes"], 56_464)
        self.assertEqual(da["fx6_wlan_resource"]["file_bytes"], 56_464)
        self.assertEqual(da["fx3_sencore"]["file_bytes"], 377_328)
        self.assertEqual(da["fx6_sencore"]["file_bytes"], 401_952)
        self.assertEqual(da["fx3_libmpr"]["file_bytes"], 3_517_008)
        self.assertEqual(da["fx6_libmpr"]["file_bytes"], 28_921_824)
        self.assertEqual(da["fx3_cpapp"]["file_bytes"], 15_980_568)
        self.assertEqual(da["fx6_cpapp"]["file_bytes"], 17_952_816)
        self.assertGreaterEqual(da["fx3_cpapp"]["marker_hits"]["IMX510"], 1)
        self.assertGreaterEqual(da["fx3_cpapp"]["marker_hits"]["defdet.bin"], 1)
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

    def test_08_zero_diff_shared_libraries_contract_parity(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertEqual(da["fx3_msc"]["export_count"], 125)
        self.assertEqual(da["fx6_msc"]["export_count"], 125)
        self.assertEqual(da["fx3_usb"]["export_count"], 351)
        self.assertEqual(da["fx6_usb"]["export_count"], 351)
        self.assertEqual(da["fx3_wlan_adjust"]["export_count"], 188)
        self.assertEqual(da["fx6_wlan_adjust"]["export_count"], 188)
        self.assertEqual(da["fx3_wlan_resource"]["export_count"], 94)
        self.assertEqual(da["fx6_wlan_resource"]["export_count"], 94)
        self.assertEqual(da["fx3_sencore"]["export_count"], 355)
        self.assertEqual(da["fx6_sencore"]["export_count"], 355)

    def test_09_libmpr_setlutdata_and_rec_markers_present_both_bodies(self) -> None:
        da = _get_default_audit()["donor_audit"]
        for key in ("fx3_libmpr", "fx6_libmpr"):
            hits = da[key]["marker_hits"]
            for tok in p157.LIBMPR_COLOR_REC_MARKERS:
                self.assertGreaterEqual(hits[tok], 1, msg=f"Missing {tok} in {key}")


class TestPillarAImx510CineEiAndSensorNvs(unittest.TestCase):
    """Pillar A: IMX510 Dual-Base ISO 800/12800 Cine EI & psd.bin/defdet.bin RO guard."""

    def test_10_lcg_base_800_nominal_ei_800(self) -> None:
        r = p157.evaluate_imx510_dual_base_cine_ei(base_iso=800, ei_index=800)
        self.assertTrue(r.valid)
        self.assertEqual(r.analog_gain_stage, "LCG_800")
        self.assertFalse(r.hcg_analog_transition_at_12800)
        self.assertEqual(r.ei_ev_offset, 0.0)
        self.assertTrue(r.xavc_master_unbaked_slog3)
        self.assertTrue(r.ei_xml_metadata_embedded)
        self.assertGreaterEqual(r.dynamic_range_stops, 15.0)
        self.assertEqual(r.sensor_cal_mutation_bytes, 0)

    def test_11_lcg_base_800_boundary_ei_200_and_3200(self) -> None:
        r_low = p157.evaluate_imx510_dual_base_cine_ei(base_iso=800, ei_index=200)
        r_hi = p157.evaluate_imx510_dual_base_cine_ei(base_iso=800, ei_index=3200)
        self.assertTrue(r_low.valid)
        self.assertEqual(r_low.ei_ev_offset, -2.0)
        self.assertTrue(r_hi.valid)
        self.assertEqual(r_hi.ei_ev_offset, 2.0)

    def test_12_hcg_transition_exact_at_iso_12800(self) -> None:
        r = p157.evaluate_imx510_dual_base_cine_ei(base_iso=12800, ei_index=12800)
        self.assertTrue(r.valid)
        self.assertEqual(r.analog_gain_stage, "HCG_12800")
        self.assertTrue(r.hcg_analog_transition_at_12800)
        self.assertEqual(r.ei_ev_offset, 0.0)
        self.assertTrue(r.xavc_master_unbaked_slog3)
        self.assertGreaterEqual(r.dynamic_range_stops, 15.0)

    def test_13_hcg_base_12800_boundary_ei_3200_and_51200(self) -> None:
        r_low = p157.evaluate_imx510_dual_base_cine_ei(base_iso=12800, ei_index=3200)
        r_hi = p157.evaluate_imx510_dual_base_cine_ei(base_iso=12800, ei_index=51200)
        self.assertTrue(r_low.valid)
        self.assertEqual(r_low.ei_ev_offset, -2.0)
        self.assertTrue(r_hi.valid)
        self.assertEqual(r_hi.ei_ev_offset, 2.0)

    def test_14_invalid_base_iso_or_out_of_range_ei_raises(self) -> None:
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_imx510_dual_base_cine_ei(base_iso=3200, ei_index=3200)
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_imx510_dual_base_cine_ei(base_iso=800, ei_index=6400)
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_imx510_dual_base_cine_ei(base_iso=12800, ei_index=1600)

    def test_15_psd_bin_write_blocked_zero_sensor_cal_mutation(self) -> None:
        for path in ("p2:/setting/psd.bin", "/dev/nflasha2", "p2:/setting/defdet.bin"):
            r = p157.evaluate_imx510_dual_base_cine_ei(
                base_iso=800,
                ei_index=800,
                target_cal_write_path=path,
            )
            self.assertFalse(r.valid)
            self.assertTrue(r.write_blocked)
            self.assertFalse(r.psd_defdet_writes_permitted)
            self.assertEqual(r.sensor_cal_mutation_bytes, 0)

    def test_16_cross_body_fx6_psd_defdet_override_blocked(self) -> None:
        r = p157.evaluate_imx510_dual_base_cine_ei(
            base_iso=12800,
            ei_index=12800,
            cross_body_cal_override=True,
        )
        self.assertFalse(r.valid)
        self.assertTrue(r.write_blocked)
        self.assertEqual(r.sensor_cal_mutation_bytes, 0)

    def test_17_pillar_a_report_and_ddr_cal_offsets(self) -> None:
        pa = _get_clean_room_audit()["pillar_a_imx510_cine_ei_and_sensor_nvs"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["sensor_cal_mutation_bytes"], 0)
        self.assertFalse(pa["psd_defdet_writes_permitted"])
        self.assertEqual(pa["ddr_bank1_cal_offsets"]["psd_delta"], "+0xe0000")
        self.assertEqual(pa["ddr_bank1_cal_offsets"]["defdet_delta"], "+0x14000")


class TestPillarBCubeMlut16SlotAndSlog3Guard(unittest.TestCase):
    """Pillar B: 16-slot SD .cube User 3D MLUT & S-Log3 non-double-bake guard."""

    def test_18_valid_17cube_and_33cube_stage_into_volatile_tmp(self) -> None:
        c17 = p157.build_synthetic_cube_text(size=17, title="T17")
        r17 = p157.parse_and_validate_cube_lut(
            c17,
            slot_index=3,
            lut_name="T17",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}T17.cube",
        )
        self.assertTrue(r17.valid)
        self.assertEqual(r17.cube_size, 17)
        self.assertEqual(r17.entry_count, 17 ** 3)
        self.assertTrue(r17.volatile_ram_staged)
        self.assertTrue(r17.volatile_ram_path.startswith(p157.VOLATILE_LUT_RAM_DIR))
        self.assertEqual(r17.emmc_nflasha_write_count, 0)

        c33 = p157.build_synthetic_cube_text(size=33, title="T33")
        r33 = p157.parse_and_validate_cube_lut(
            c33,
            slot_index=16,
            lut_name="T33",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}T33.cube",
        )
        self.assertTrue(r33.valid)
        self.assertEqual(r33.cube_size, 33)
        self.assertEqual(r33.entry_count, 33 ** 3)

    def test_19_nan_and_inf_cube_rejected_fail_closed(self) -> None:
        c17 = p157.build_synthetic_cube_text(size=17)
        nan_txt = c17.replace("0.0000 0.0000 0.0000", "NaN 0.0000 0.0000", 1)
        inf_txt = c17.replace("0.0000 0.0000 0.0000", "inf 0.0000 0.0000", 1)
        for bad in (nan_txt, inf_txt):
            r = p157.parse_and_validate_cube_lut(
                bad,
                slot_index=1,
                lut_name="Bad",
                sd_source_path=f"{p157.SD_CUBE_LUT_DIR}Bad.cube",
            )
            self.assertFalse(r.valid)
            self.assertTrue(r.rejected_fail_closed)
            self.assertFalse(r.volatile_ram_staged)

    def test_20_truncated_and_unsupported_65cube_rejected_fail_closed(self) -> None:
        r_trunc = p157.parse_and_validate_cube_lut(
            "LUT_3D_SIZE 17\n0.0 0.0 0.0\n",
            slot_index=2,
            lut_name="Trunc",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}Trunc.cube",
        )
        self.assertFalse(r_trunc.valid)
        self.assertTrue(r_trunc.rejected_fail_closed)

        r_65 = p157.parse_and_validate_cube_lut(
            "LUT_3D_SIZE 65\n0.0 0.0 0.0\n",
            slot_index=2,
            lut_name="SixtyFive",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}SixtyFive.cube",
        )
        self.assertFalse(r_65.valid)
        self.assertTrue(r_65.rejected_fail_closed)

    def test_21_slot_out_of_bounds_and_path_traversal_rejected(self) -> None:
        c17 = p157.build_synthetic_cube_text(size=17)
        r0 = p157.parse_and_validate_cube_lut(
            c17,
            slot_index=0,
            lut_name="Slot0",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}Slot0.cube",
        )
        r17 = p157.parse_and_validate_cube_lut(
            c17,
            slot_index=17,
            lut_name="Slot17",
            sd_source_path=f"{p157.SD_CUBE_LUT_DIR}Slot17.cube",
        )
        r_trav = p157.parse_and_validate_cube_lut(
            c17,
            slot_index=1,
            lut_name="Trav",
            sd_source_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/../../nflasha2/bad.cube",
        )
        self.assertFalse(r0.valid)
        self.assertFalse(r17.valid)
        self.assertFalse(r_trav.valid)
        self.assertTrue(r_trav.rejected_fail_closed)

    def test_22_mlut_monitoring_burn_in_off_never_double_bakes_slog3(self) -> None:
        r = p157.evaluate_mlut_monitoring_route(
            slot_index=1,
            cube_size=33,
            lut_burn_in=False,
            lcd_preview_mlut=True,
            hdmi_type_a_clean_mlut=True,
            raw_16bit_hdmi_out=False,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slog3_master_double_baked)
        self.assertEqual(r.xavc_master_gamut, "S-Log3/S-Gamut3.Cine")
        self.assertTrue(r.hdmi_output_lut_applied)

    def test_23_hdmi_raw16_bypasses_mlut_and_burn_in_attempt_blocked(self) -> None:
        r_raw = p157.evaluate_mlut_monitoring_route(
            slot_index=1,
            cube_size=33,
            lut_burn_in=False,
            lcd_preview_mlut=True,
            hdmi_type_a_clean_mlut=True,
            raw_16bit_hdmi_out=True,
        )
        self.assertTrue(r_raw.valid)
        self.assertFalse(r_raw.hdmi_output_lut_applied)
        self.assertFalse(r_raw.slog3_master_double_baked)

        r_dbl = p157.evaluate_mlut_monitoring_route(
            slot_index=1,
            cube_size=33,
            lut_burn_in=True,
            cine_ei_preserve_slog3=True,
        )
        self.assertFalse(r_dbl.valid)
        self.assertTrue(r_dbl.double_bake_blocked)
        self.assertFalse(r_dbl.slog3_master_double_baked)

    def test_24_invalid_mlut_route_args_raise(self) -> None:
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_mlut_monitoring_route(slot_index=17, cube_size=33)
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_mlut_monitoring_route(slot_index=1, cube_size=65)

    def test_25_pillar_b_all_16_slots_verified(self) -> None:
        pb = _get_clean_room_audit()["pillar_b_cube_mlut_16slot_and_slog3_guard"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["active_slots_count"], 16)
        self.assertFalse(pb["slog3_master_double_baked"])
        self.assertEqual(pb["emmc_nflasha_write_count"], 0)


class TestPillarCConnectivityAndRfNvsLock(unittest.TestCase):
    """Pillar C: 802.11ac, CDC-NCM PTP-IP 15740 + FTPES, BLE 0ms shim & p12/p13 lock."""

    def test_26_wifi_80211ac_5ghz_active_when_p12_off(self) -> None:
        r = p157.evaluate_connectivity_and_rf_lock(transport="WIFI_80211AC_5GHZ", airplane_p12_on=False)
        self.assertTrue(r.valid)
        self.assertTrue(r.wlan0_up)
        self.assertTrue(r.rf_tx_active)
        self.assertTrue(r.ptpip_15740_ready)
        self.assertTrue(r.ftpes_ready)
        self.assertEqual(r.rf_nvs_p12_p13_mutation_bytes, 0)

    def test_27_p12_airplane_mode_hard_kills_wlan0_and_rf_tx(self) -> None:
        for wifi in ("WIFI_80211AC_5GHZ", "WIFI_80211N_24GHZ"):
            r = p157.evaluate_connectivity_and_rf_lock(transport=wifi, airplane_p12_on=True)
            self.assertFalse(r.valid)
            self.assertTrue(r.airplane_p12_on)
            self.assertFalse(r.wlan0_up)
            self.assertFalse(r.rf_tx_active)

    def test_28_cdc_ncm_gigabit_monitor_control_ptpip_15740_works_under_p12(self) -> None:
        for nic in ("CDC_NCM_RTL8153_GIGABIT", "CDC_NCM_AX88179_GIGABIT"):
            r = p157.evaluate_connectivity_and_rf_lock(transport=nic, airplane_p12_on=True)
            self.assertTrue(r.valid)
            self.assertFalse(r.wlan0_up)
            self.assertFalse(r.rf_tx_active)
            self.assertEqual(r.link_speed_mbps, 1000)
            self.assertTrue(r.ptpip_15740_ready)
            self.assertTrue(r.ftpes_ready)

    def test_29_ble_ttyama3_blocking_wait_eliminated_and_unmasked_caught(self) -> None:
        r_ok = p157.evaluate_connectivity_and_rf_lock(
            transport="BLE_TTYAMA3_DAEMON",
            bt_daemon_shim_enabled=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(r_ok.bt_hci_blocking_wait_ms, 0)
        self.assertTrue(r_ok.bt_hci_blocking_wait_eliminated)

        r_fail = p157.evaluate_connectivity_and_rf_lock(
            transport="BLE_TTYAMA3_DAEMON",
            bt_daemon_shim_enabled=False,
        )
        self.assertFalse(r_fail.valid)
        self.assertGreater(r_fail.bt_hci_blocking_wait_ms, 0)
        self.assertFalse(r_fail.bt_hci_blocking_wait_eliminated)

    def test_30_fx6_wiredlan_wol_mask_0ms_and_unmasked_caught(self) -> None:
        r_ok = p157.evaluate_connectivity_and_rf_lock(transport="FX6_WIREDLAN_WOL", wol_mask_enabled=True)
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.wol_masked)

        r_fail = p157.evaluate_connectivity_and_rf_lock(transport="FX6_WIREDLAN_WOL", wol_mask_enabled=False)
        self.assertFalse(r_fail.valid)
        self.assertFalse(r_fail.wol_masked)

    def test_31_rf_nvs_p12_p13_writes_blocked_zero_bytes(self) -> None:
        for path in p157.RF_NVS_IMMUTABLE_PARTITIONS:
            r = p157.evaluate_connectivity_and_rf_lock(
                transport="WIFI_80211AC_5GHZ",
                requested_nvs_write_path=path,
            )
            self.assertFalse(r.valid)
            self.assertTrue(r.write_blocked)
            self.assertFalse(r.rf_nvs_p12_p13_writes_permitted)
            self.assertEqual(r.rf_nvs_p12_p13_mutation_bytes, 0)

    def test_32_invalid_transport_raises(self) -> None:
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_connectivity_and_rf_lock(transport="INVALID_RF")


class TestPillarDUsbTypeCRecoveryPreservation(unittest.TestCase):
    """Pillar D: USB Type-C multi-role switching & 054C:0DA1 / 054C:0336 preservation."""

    def test_33_full_role_switch_cycle_preserves_054c_0da1_and_0336(self) -> None:
        chain = [
            ("MSC_054C_0DA1", "MTP_PTP_REMOTE", "054C:0D59"),
            ("MTP_PTP_REMOTE", "CDC_NCM_USB_LAN", "054C:CDC-NCM"),
            ("CDC_NCM_USB_LAN", "HDMI_UVC_BRIDGE", "HDMI-TO-UVC-EXT"),
            ("HDMI_UVC_BRIDGE", "MSC_054C_0DA1", "054C:0DA1"),
            ("MSC_054C_0DA1", "SERVICE_054C_0336", "054C:0336"),
        ]
        for src_role, dst_role, vid_pid in chain:
            r = p157.evaluate_usb_role_switch(from_role=src_role, to_role=dst_role)
            self.assertTrue(r.valid)
            self.assertEqual(r.usb_vid_pid, vid_pid)
            self.assertTrue(r.usb_msc_0da1_recovery_intact)
            self.assertTrue(r.service_0336_reachable)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_34_hijack_msc_0da1_attempt_blocked_fail_closed(self) -> None:
        r = p157.evaluate_usb_role_switch(
            from_role="MSC_054C_0DA1",
            to_role="HDMI_UVC_BRIDGE",
            hijack_msc_0da1=True,
        )
        self.assertFalse(r.valid)
        self.assertTrue(r.hijack_blocked)
        self.assertTrue(r.usb_msc_0da1_recovery_intact)

    def test_35_unauthorized_emmc_write_attempt_blocked(self) -> None:
        r = p157.evaluate_usb_role_switch(
            from_role="MSC_054C_0DA1",
            to_role="SERVICE_054C_0336",
            authorize_emmc_write=True,
        )
        self.assertFalse(r.valid)
        self.assertTrue(r.emmc_write_blocked)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_36_invalid_usb_roles_raise(self) -> None:
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_usb_role_switch(from_role="BAD", to_role="MSC_054C_0DA1")
        with self.assertRaises(p157.RealHwImx510NetworkUsbError):
            p157.evaluate_usb_role_switch(from_role="MSC_054C_0DA1", to_role="BAD")

    def test_37_pillar_d_report_contract(self) -> None:
        pd = _get_clean_room_audit()["pillar_d_usbc_multirole_0da1_recovery"]
        self.assertTrue(pd["passed"])
        self.assertTrue(pd["usb_msc_0da1_recovery_intact"])
        self.assertFalse(pd["persistent_emmc_writes_authorized"])
        self.assertEqual(pd["emmc_nflasha_write_count"], 0)


class TestStage27SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Stage 27 Suite Integration (27/27), CLI, Runtime Budget (<1.0s/<2.4s), and Hygiene."""

    def test_38_standalone_cli_summary_and_json_clean_room(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p157.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc_sum, 0)
        out_sum = buf_sum.getvalue()
        self.assertIn("[PASS] Phase 157 Stage 27 Real-HW IMX510/Color/Network/USB HIL", out_sum)
        self.assertIn("mlut_slots=16/16", out_sum)
        self.assertIn("msc_0da1=True", out_sum)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p157.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["schema"], p157.PHASE_157_SCHEMA)
        self.assertTrue(data["all_checks_passed"])

    def test_39_standalone_cli_rejects_unknown_flag(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                p157.main(["--no-such-flag"])
            self.assertNotEqual(ctx.exception.code, 0)

    def test_40_suite_in_process_27_stages_and_skip_phase157_config(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage27_realhw_imx510_network_usb_hil", rep_on)
        s27 = rep_on["stage27_realhw_imx510_network_usb_hil"]
        self.assertTrue(s27["all_checks_passed"])
        self.assertFalse(s27["persistent_emmc_writes_authorized"])
        self.assertEqual(s27["sensor_cal_mutation_bytes"], 0)
        self.assertEqual(s27["rf_nvs_p12_p13_mutation_bytes"], 0)
        self.assertFalse(s27["slog3_master_double_baked"])
        self.assertEqual(s27["bt_hci_blocking_wait_ms"], 0)
        self.assertTrue(s27["usb_msc_0da1_recovery_intact"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 27)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase157_realhw_imx510_network_usb_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage27_realhw_imx510_network_usb_hil", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_41_suite_subprocess_summary_and_skip_phase157_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("realhw_imx510_network_usb_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase157",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_imx510_network_usb_hil=", proc_skip.stdout)

    def test_42_suite_27_stages_clean_room_lt_1p0s_and_local_lt_2p4s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 27)
        self.assertLess(dt_clean, 1.00)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 27)
        self.assertLess(dt_mode, 2.40)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_clean.returncode, 0, msg=p_clean.stderr)
        d_clean = json.loads(p_clean.stdout)
        self.assertTrue(d_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 27)

    def test_43_all_27_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 28):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_44_stage27_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_45_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_imx510_color_and_network_usb_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_46_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p157.run_phase157_realhw_imx510_network_usb_hil(force_clean_room=True)
        r2 = p157.run_phase157_realhw_imx510_network_usb_hil(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

        copy = dict(r1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)


if __name__ == "__main__":
    unittest.main()
