"""Fast dual-mode unit tests for Milestone Phase 125 — Tropical Monsoon Rain / Wet
MI-Shoe 24-Pin Contact Short-Circuit Firewall (Gate G39), FX3 Top-Plate 1/4"-20
Thread Shear / XLR-H1 Whip-Leverage & Cage-Twist Flange-Focal-Distance Guard
(Gate G40), and Unified 40-Gate Master Safety Preflight (`G01..G40`).
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
    BODY_QUARTER20_TORQUE_MAX_NM,
    CAGE_UNSHIMMED_SIDE_GAP_MAX_MM,
    EMOUNT_FFD_TILT_MAX_UM,
    G39_GATE_CODE,
    G39_GATE_ID,
    G40_GATE_CODE,
    G40_GATE_ID,
    MISHOE_MIN_DRY_CONTACT_RESISTANCE_KOHM,
    MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA,
    MONSOON_MISHOE_CAGETWIST_40GATE_VERSION,
    MONSOON_RAIN_NONGASKETED_ACC_MAX_MM_HR,
    MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE,
    STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP,
    STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID,
    STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN,
    STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT,
    STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR,
    STATUS_SAFE,
    STATUS_VERIFIED_G39,
    STATUS_VERIFIED_G40,
    STATUS_VERIFIED_SAFE,
    XLR_H1_SUSPENDED_MASS_MAX_KG,
    XLR_H1_TOP_HANDLE_MOMENT_MAX_NM,
    audit_phase125_donor_contracts,
    compute_mishoe_galvanic_leakage_current_ma,
    compute_xlr_h1_whip_moment_nm,
    estimate_emount_ffd_tilt_um,
    estimate_mishoe_pin_electrolysis_power_mw,
    evaluate_40_master_safety_gates,
    evaluate_40gate_preflight,
    evaluate_g39_monsoon_rain_and_mishoe,
    evaluate_g40_xlr_h1_quarter20_and_cage_twist,
    main as module_cli_main,
    verify_monsoon_rain_mishoe_firewall,
    verify_xlr_h1_quarter20_and_cage_twist_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.usbpd_trigger_multiterminal_and_38gate_guard import (
    STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD,
    STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE,
    evaluate_38gate_preflight,
)


class MonsoonMiShoeCageTwistAnd40GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA,
            "fx3-monsoon-mishoe-cagetwist-40gate-preflight-v1",
        )
        self.assertEqual(MONSOON_MISHOE_CAGETWIST_40GATE_VERSION, "1.0.0")
        for sym in (
            "MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA",
            "G39_GATE_ID",
            "G39_GATE_CODE",
            "G40_GATE_ID",
            "G40_GATE_CODE",
            "STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT",
            "STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN",
            "STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS",
            "STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR",
            "STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP",
            "STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE",
            "audit_phase125_donor_contracts",
            "compute_mishoe_galvanic_leakage_current_ma",
            "estimate_mishoe_pin_electrolysis_power_mw",
            "compute_xlr_h1_whip_moment_nm",
            "estimate_emount_ffd_tilt_um",
            "verify_monsoon_rain_mishoe_firewall",
            "verify_xlr_h1_quarter20_and_cage_twist_guard",
            "evaluate_g39_monsoon_rain_and_mishoe",
            "evaluate_g40_xlr_h1_quarter20_and_cage_twist",
            "evaluate_40gate_preflight",
            "evaluate_40_master_safety_gates",
            "monsoon_mishoe_cagetwist_and_40gate_guard",
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
            fx3_safety.USBPD_MULTITERMINAL_38GATE_SCHEMA,
            "fx3-usbpd-trigger-multiterminal-38gate-preflight-v1",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase125_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.mishoe_hotshoe_tokens_verified)
        self.assertTrue(res_default.lens_mount_comm_tokens_verified)
        self.assertTrue(res_default.ext_cmd_buspower_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libInfraHotshoe",
                    "libInfraLensCommunicator",
                    "libInfraExtCmdSvc",
                    "libBusPower",
                )
            ):
                self.assertEqual(
                    flags & os.O_ACCMODE,
                    os.O_RDONLY,
                    f"Non-O_RDONLY open on {path}",
                )

        res_clean = audit_phase125_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 7)

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
            for name in (
                "libInfraLensCommunicator.so",
                "libInfraExtCmdSvc.so",
                "libBusPower.so",
            ):
                (fx3_lib / name).write_bytes(b"corrupt")
                (fx6_lib / name).write_bytes(b"corrupt")
            (fx6_lib / "libInfraHotshoe.so").write_bytes(b"corrupt")
            res = audit_phase125_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 7)
        self.assertFalse(res.mishoe_hotshoe_tokens_verified)
        self.assertFalse(res.lens_mount_comm_tokens_verified)
        self.assertFalse(res.ext_cmd_buspower_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase125_donor_contracts(
            force_clean_room=True, include_large_binaries=True
        )
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase125_donor_contracts(
                work_root=Path(empty_dir), force_clean_room=False
            )
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Wet MI-Shoe Electrolysis & XLR-H1 / Cage-Twist Physics Helpers ---

    def test_05_mishoe_galvanic_leakage_and_electrolysis_helpers(self) -> None:
        self.assertAlmostEqual(
            compute_mishoe_galvanic_leakage_current_ma(5.0, 10.0), 0.5, places=6
        )
        self.assertAlmostEqual(
            estimate_mishoe_pin_electrolysis_power_mw(5.0, 10.0), 2.5, places=6
        )
        self.assertAlmostEqual(
            compute_mishoe_galvanic_leakage_current_ma(0.0, 50.0), 0.0, places=6
        )
        with self.assertRaises(ValueError):
            compute_mishoe_galvanic_leakage_current_ma(-3.15, 10.0)
        with self.assertRaises(ValueError):
            compute_mishoe_galvanic_leakage_current_ma(5.0, 0.0)
        with self.assertRaises(ValueError):
            estimate_mishoe_pin_electrolysis_power_mw(float("nan"), 10.0)

    def test_06_xlr_h1_whip_moment_and_emount_ffd_tilt_helpers(self) -> None:
        m = compute_xlr_h1_whip_moment_nm(2.0, 0.15, dynamic_whip_g=1.5)
        self.assertAlmostEqual(m, 2.0 * 9.80665 * 0.15 * 1.5, places=6)
        self.assertAlmostEqual(estimate_emount_ffd_tilt_um(0.25), 12.0, places=6)
        self.assertGreater(estimate_emount_ffd_tilt_um(0.30), EMOUNT_FFD_TILT_MAX_UM)
        with self.assertRaises(ValueError):
            compute_xlr_h1_whip_moment_nm(-1.0, 0.1)
        with self.assertRaises(ValueError):
            compute_xlr_h1_whip_moment_nm(1.0, 0.1, dynamic_whip_g=0.0)
        with self.assertRaises(ValueError):
            estimate_emount_ffd_tilt_um(-0.05)

    # --- 3. Gate G39 — Monsoon Rain, Wet 24-Pin MI-Shoe & Port-Flap Capillary ---

    def test_07_g39_default_safe_profile_passes(self) -> None:
        res = verify_monsoon_rain_mishoe_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.uncapped_mishoe_rain_safe)
        self.assertTrue(res.gasketed_mishoe_accessory_safe)
        self.assertTrue(res.side_port_flap_capillary_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g39_blocks_uncapped_mishoe_rain_and_wet_pin_bridge(self) -> None:
        res_uncapped = verify_monsoon_rain_mishoe_firewall(
            weather_profile="TROPICAL_SQUALL_UNCAPPED",
            precipitation_mm_hr=8.5,
            mi_shoe_accessory_attached=False,
            mi_shoe_weather_cap_installed=False,
        )
        self.assertFalse(res_uncapped.valid)
        self.assertFalse(res_uncapped.uncapped_mishoe_rain_safe)
        self.assertEqual(
            res_uncapped.status, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )

        res_wet_bridge = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=0.0,
            mi_shoe_weather_cap_installed=True,
            mi_shoe_contact_resistance_kohm=12.0,
            mi_shoe_power_rail_enabled=True,
        )
        self.assertFalse(res_wet_bridge.valid)
        self.assertEqual(
            res_wet_bridge.status, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )
        self.assertGreater(res_wet_bridge.estimated_leakage_current_ma, 0.4)

        # Exact 0.5 mm/hr & 50.0 kOhm boundaries pass
        res_edge = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=MONSOON_RAIN_UNCAPPED_MISHOE_MAX_MM_HR,
            mi_shoe_accessory_attached=False,
            mi_shoe_weather_cap_installed=False,
            mi_shoe_contact_resistance_kohm=MISHOE_MIN_DRY_CONTACT_RESISTANCE_KOHM,
            mi_shoe_power_rail_enabled=True,
        )
        self.assertTrue(res_edge.valid)

        # Capped MI-Shoe passes even in heavy monsoon rain
        res_capped = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=35.0,
            mi_shoe_accessory_attached=False,
            mi_shoe_weather_cap_installed=True,
        )
        self.assertTrue(res_capped.valid)
        self.assertGreaterEqual(len(res_capped.warnings), 1)

    def test_09_g39_blocks_non_gasketed_mishoe_accessory_in_rain(self) -> None:
        res_bad = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=5.0,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_perimeter_gasket_sealed=False,
            rain_cover_installed=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.gasketed_mishoe_accessory_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN
        )

        # Exact 2.0 mm/hr boundary passes
        res_edge = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=MONSOON_RAIN_NONGASKETED_ACC_MAX_MM_HR,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_perimeter_gasket_sealed=False,
            rain_cover_installed=False,
        )
        self.assertTrue(res_edge.valid)

        # Silicone perimeter gasket OR rain cover mitigates
        res_gasket = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=20.0,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_perimeter_gasket_sealed=True,
            rain_cover_installed=False,
        )
        self.assertTrue(res_gasket.valid)

        res_cover = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=20.0,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_perimeter_gasket_sealed=False,
            rain_cover_installed=True,
        )
        self.assertTrue(res_cover.valid)

    def test_10_g39_blocks_open_side_port_flap_capillary_ingress(self) -> None:
        res_rain = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=3.0,
            mi_shoe_weather_cap_installed=True,
            open_rubber_port_flaps_count=2,
            weather_sealed_cable_gland_or_rain_slicker=False,
        )
        self.assertFalse(res_rain.valid)
        self.assertFalse(res_rain.side_port_flap_capillary_safe)
        self.assertEqual(
            res_rain.status, STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS
        )

        res_spray = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=0.0,
            water_spray_rig=True,
            open_rubber_port_flaps_count=1,
            weather_sealed_cable_gland_or_rain_slicker=False,
        )
        self.assertFalse(res_spray.valid)
        self.assertEqual(
            res_spray.status, STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS
        )

        # Sealed cable gland / rain slicker mitigates
        res_sealed = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=15.0,
            water_spray_rig=True,
            mi_shoe_weather_cap_installed=True,
            open_rubber_port_flaps_count=2,
            weather_sealed_cable_gland_or_rain_slicker=True,
        )
        self.assertTrue(res_sealed.valid)
        self.assertGreaterEqual(len(res_sealed.warnings), 1)

    def test_11_g39_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"precipitation_mm_hr": float("nan")},
            {"precipitation_mm_hr": -0.1},
            {"mi_shoe_contact_resistance_kohm": 0.0},
            {"mi_shoe_contact_resistance_kohm": -5.0},
            {"mi_shoe_contact_resistance_kohm": float("inf")},
            {"open_rubber_port_flaps_count": -1},
            {"open_rubber_port_flaps_count": True},
        ):
            res_bad = verify_monsoon_rain_mishoe_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_MONSOON_MISHOE_TELEMETRY_INVALID
            )

        res_emmc = verify_monsoon_rain_mishoe_firewall(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g39_accumulates_all_three_violations_deterministically(self) -> None:
        # Both uncapped rain & non-gasketed accessory trigger when wet bridge + attached ungasketed accessory
        res = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=12.0,
            water_spray_rig=True,
            mi_shoe_accessory_attached=True,
            mi_shoe_weather_cap_installed=False,
            mi_shoe_silicone_perimeter_gasket_sealed=False,
            rain_cover_installed=False,
            mi_shoe_contact_resistance_kohm=5.0,
            mi_shoe_power_rail_enabled=True,
            open_rubber_port_flaps_count=2,
            weather_sealed_cable_gland_or_rain_slicker=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT,
                STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN,
                STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS,
            },
        )

    # --- 4. Gate G40 — XLR-H1 Whip Shear, 1/4"-20 Thread Strip & Cage-Twist FFD ---

    def test_13_g40_default_safe_profile_passes(self) -> None:
        res = verify_xlr_h1_quarter20_and_cage_twist_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.xlr_h1_whip_shear_safe)
        self.assertTrue(res.quarter20_thread_torque_safe)
        self.assertTrue(res.asymmetric_cage_twist_ffd_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_g40_blocks_xlr_h1_top_handle_overload_whip_shear(self) -> None:
        res_mass = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=3.4,
            top_handle_monitor_moment_nm=1.5,
            metal_cage_nato_top_handle_reinforcement=False,
        )
        self.assertFalse(res_mass.valid)
        self.assertFalse(res_mass.xlr_h1_whip_shear_safe)
        self.assertEqual(
            res_mass.status, STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR
        )

        res_moment = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=2.0,
            top_handle_monitor_moment_nm=3.8,
            metal_cage_nato_top_handle_reinforcement=False,
        )
        self.assertFalse(res_moment.valid)
        self.assertEqual(
            res_moment.status, STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR
        )

        # Exact 2.8 kg & 3.2 N*m boundary passes
        res_edge = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=XLR_H1_SUSPENDED_MASS_MAX_KG,
            top_handle_monitor_moment_nm=XLR_H1_TOP_HANDLE_MOMENT_MAX_NM,
            metal_cage_nato_top_handle_reinforcement=False,
        )
        self.assertTrue(res_edge.valid)

        # NATO top-handle cage reinforcement mitigates heavy load
        res_nato = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=4.2,
            top_handle_monitor_moment_nm=4.5,
            metal_cage_nato_top_handle_reinforcement=True,
        )
        self.assertTrue(res_nato.valid)
        self.assertGreaterEqual(len(res_nato.warnings), 1)

    def test_15_g40_blocks_body_quarter20_overtorque_thread_strip(self) -> None:
        res_bad = verify_xlr_h1_quarter20_and_cage_twist_guard(
            body_thread_fastener_torque_nm=4.5
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.quarter20_thread_torque_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP
        )

        # Exact 3.5 N*m boundary passes
        res_edge = verify_xlr_h1_quarter20_and_cage_twist_guard(
            body_thread_fastener_torque_nm=BODY_QUARTER20_TORQUE_MAX_NM
        )
        self.assertTrue(res_edge.valid)

    def test_16_g40_blocks_asymmetric_cage_twist_ffd_warpage(self) -> None:
        res_bad = verify_xlr_h1_quarter20_and_cage_twist_guard(
            cage_multi_point_locked=True,
            unshimmed_side_screw_gap_mm=0.40,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.asymmetric_cage_twist_ffd_safe)
        self.assertGreater(res_bad.estimated_emount_ffd_tilt_um, EMOUNT_FFD_TILT_MAX_UM)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE
        )

        # Exact 0.25 mm boundary (12.0 um FFD tilt) passes
        res_edge = verify_xlr_h1_quarter20_and_cage_twist_guard(
            cage_multi_point_locked=True,
            unshimmed_side_screw_gap_mm=CAGE_UNSHIMMED_SIDE_GAP_MAX_MM,
        )
        self.assertTrue(res_edge.valid)
        self.assertAlmostEqual(res_edge.estimated_emount_ffd_tilt_um, 12.0, places=3)

        # Single-point bottom mount (cage_multi_point_locked=False) does not twist E-Mount
        res_unlocked = verify_xlr_h1_quarter20_and_cage_twist_guard(
            cage_multi_point_locked=False,
            unshimmed_side_screw_gap_mm=0.50,
        )
        self.assertTrue(res_unlocked.valid)

    def test_17_g40_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"total_rig_mass_suspended_from_xlr_h1_kg": -0.1},
            {"top_handle_monitor_moment_nm": float("nan")},
            {"body_thread_fastener_torque_nm": float("inf")},
            {"unshimmed_side_screw_gap_mm": -0.01},
            {"estimated_emount_ffd_tilt_um": -1.0},
        ):
            res_bad = verify_xlr_h1_quarter20_and_cage_twist_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_CAGETWIST_XLRH1_TELEMETRY_INVALID
            )

        res_emmc = verify_xlr_h1_quarter20_and_cage_twist_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_18_g40_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=3.6,
            top_handle_monitor_moment_nm=4.0,
            metal_cage_nato_top_handle_reinforcement=False,
            body_thread_fastener_torque_nm=5.2,
            cage_multi_point_locked=True,
            unshimmed_side_screw_gap_mm=0.45,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR,
                STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP,
                STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE,
            },
        )

    # --- 5. Gate G39 & G40 Evaluators & Unified 40-Gate Master Preflight ---

    def test_19_g39_and_g40_verdicts_dual_mode(self) -> None:
        v39, r39 = evaluate_g39_monsoon_rain_and_mishoe(force_clean_room=True)
        self.assertTrue(v39.passed)
        self.assertEqual(v39.gate_id, G39_GATE_ID)
        self.assertEqual(v39.gate_code, G39_GATE_CODE)
        self.assertEqual(v39.status, STATUS_VERIFIED_G39)
        self.assertFalse(r39.persistent_emmc_writes_authorized)

        v40, r40 = evaluate_g40_xlr_h1_quarter20_and_cage_twist(force_clean_room=True)
        self.assertTrue(v40.passed)
        self.assertEqual(v40.gate_id, G40_GATE_ID)
        self.assertEqual(v40.gate_code, G40_GATE_CODE)
        self.assertEqual(v40.status, STATUS_VERIFIED_G40)
        self.assertFalse(r40.persistent_emmc_writes_authorized)

    def test_20_40gate_offline_default_37_of_40_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_40gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA)
        self.assertGreaterEqual(len(rep.gates), 40)
        self.assertGreaterEqual(rep.summary["total_gates"], 40)
        self.assertGreaterEqual(rep.summary["verified_gates"], 37)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_37_gates_verified)
        self.assertFalse(rep.all_40_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_37_OF_40_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_21_40gate_dry_run_simulated_backup_40_of_40_and_redlines_locked(self) -> None:
        rep = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(rep.gates), 40)
        self.assertGreaterEqual(rep.summary["verified_gates"], 40)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g38_verified"], 26)
        self.assertEqual(rep.summary["g39_to_g40_verified"], 2)
        self.assertTrue(rep.all_40_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_40_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_22_40gate_propagates_g39_rain_mishoe_and_port_flap_failures(self) -> None:
        rep_uncapped = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            monsoon_mishoe_kwargs={
                "precipitation_mm_hr": 5.0,
                "mi_shoe_accessory_attached": False,
                "mi_shoe_weather_cap_installed": False,
            },
        )
        self.assertFalse(rep_uncapped.all_40_gates_verified)
        self.assertFalse(rep_uncapped.g39_to_g40_all_passed)
        self.assertFalse(rep_uncapped.gates[38]["passed"])
        self.assertEqual(
            rep_uncapped.status, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )

        rep_acc = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            monsoon_mishoe_kwargs={
                "precipitation_mm_hr": 4.0,
                "mi_shoe_accessory_attached": True,
                "mi_shoe_silicone_perimeter_gasket_sealed": False,
                "rain_cover_installed": False,
            },
        )
        self.assertFalse(rep_acc.all_40_gates_verified)
        self.assertEqual(
            rep_acc.status, STATUS_BLOCKED_NON_GASKETED_MISHOE_ACCESSORY_IN_RAIN
        )

        rep_flap = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            monsoon_mishoe_kwargs={
                "water_spray_rig": True,
                "open_rubber_port_flaps_count": 1,
                "weather_sealed_cable_gland_or_rain_slicker": False,
            },
        )
        self.assertFalse(rep_flap.all_40_gates_verified)
        self.assertEqual(
            rep_flap.status, STATUS_BLOCKED_OPEN_SIDE_PORT_FLAP_CAPILLARY_INGRESS
        )

    def test_23_40gate_propagates_g40_xlr_h1_torque_and_cagetwist_failures(self) -> None:
        rep_whip = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cagetwist_xlrh1_kwargs={
                "xlr_h1_handle_installed": True,
                "total_rig_mass_suspended_from_xlr_h1_kg": 3.5,
            },
        )
        self.assertFalse(rep_whip.all_40_gates_verified)
        self.assertFalse(rep_whip.gates[39]["passed"])
        self.assertEqual(
            rep_whip.status, STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR
        )

        rep_strip = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cagetwist_xlrh1_kwargs={
                "body_thread_fastener_torque_nm": 4.8,
            },
        )
        self.assertFalse(rep_strip.all_40_gates_verified)
        self.assertEqual(
            rep_strip.status, STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP
        )

        rep_ffd = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cagetwist_xlrh1_kwargs={
                "cage_multi_point_locked": True,
                "unshimmed_side_screw_gap_mm": 0.4,
            },
        )
        self.assertFalse(rep_ffd.all_40_gates_verified)
        self.assertEqual(
            rep_ffd.status, STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE
        )

    def test_24_40gate_propagates_g37_g38_and_emmc_redline(self) -> None:
        rep_g37_g38 = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            usbpd_uvc_kwargs={
                "usbc_vbus_measured_v": 20.0,
                "valid_9v_3a_pd_pdo_contract": False,
            },
            multiterminal_ptp_kwargs={
                "uart_probe_attached": True,
                "uart_logic_level_v": 3.3,
            },
        )
        self.assertFalse(rep_g37_g38.all_40_gates_verified)
        self.assertFalse(rep_g37_g38.gates[36]["passed"])
        self.assertFalse(rep_g37_g38.gates[37]["passed"])
        self.assertEqual(
            rep_g37_g38.gates[36]["status"],
            STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE,
        )
        self.assertEqual(
            rep_g37_g38.gates[37]["status"],
            STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD,
        )
        self.assertEqual(
            rep_g37_g38.status, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )

        rep_emmc = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_40_gates_verified)
        self.assertFalse(rep_emmc.offline_37_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_25_40gate_preserves_g01_to_g38_untouched(self) -> None:
        r38 = evaluate_38gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r40 = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(r38.gates), 38)
        self.assertGreaterEqual(len(r40.gates), 40)
        self.assertEqual(
            [g["gate_id"] for g in r38.gates],
            [g["gate_id"] for g in r40.gates[:38]],
        )
        self.assertEqual(
            [g["status"] for g in r38.gates],
            [g["status"] for g in r40.gates[:38]],
        )

    def test_26_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_27_cli_verify_40_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-40-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA)
        self.assertGreaterEqual(p_off["summary"]["verified_gates"], 37)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-40-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertGreaterEqual(p_dry["summary"]["verified_gates"], 40)
        self.assertTrue(p_dry["all_40_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_28_cli_verify_40_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=37/40", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-40-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=37/40", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-40-gates", "--repo-root", empty_dir, "--clean-room"]
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
        self.assertEqual(payload["schema"], MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA)
        self.assertTrue(payload["all_40_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_30_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_40gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_37_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_31_evaluate_40_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_40_master_safety_gates, evaluate_40gate_preflight)
        rep = evaluate_40_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_40_gates_verified)
        self.assertGreaterEqual(rep.summary["verified_gates"], 40)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_32_donor_corruption_propagates_to_g39_g40_and_40gate_report(self) -> None:
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
            for name in (
                "libInfraLensCommunicator.so",
                "libInfraExtCmdSvc.so",
                "libBusPower.so",
            ):
                (fx3_lib / name).write_bytes(b"bad")
                (fx6_lib / name).write_bytes(b"bad")
            (fx6_lib / "libInfraHotshoe.so").write_bytes(b"bad")
            v39, r39 = evaluate_g39_monsoon_rain_and_mishoe(
                work_root=tmp, force_clean_room=False
            )
            v40, r40 = evaluate_g40_xlr_h1_quarter20_and_cage_twist(
                work_root=tmp, force_clean_room=False
            )
        self.assertFalse(v39.passed)
        self.assertFalse(r39.valid)
        self.assertEqual(v39.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v40.passed)
        self.assertFalse(r40.valid)
        self.assertEqual(v40.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_33_prior_cli_subcommands_verify_16_through_38_remain_intact(self) -> None:
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
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_34_g39_g40_gate_ids_and_soc_passthrough_in_40gate_report(self) -> None:
        rep = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_40_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[38]["gate_id"], G39_GATE_ID)
        self.assertEqual(rep.gates[38]["gate_code"], G39_GATE_CODE)
        self.assertEqual(rep.gates[39]["gate_id"], G40_GATE_ID)
        self.assertEqual(rep.gates[39]["gate_code"], G40_GATE_CODE)

    def test_35_40gate_summary_blocks_if_g39_or_g40_requests_emmc_write(self) -> None:
        rep_39 = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            monsoon_mishoe_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_39.all_40_gates_verified)
        self.assertFalse(rep_39.g39_to_g40_all_passed)
        self.assertFalse(rep_39.gates[38]["passed"])
        self.assertEqual(rep_39.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_39.persistent_emmc_writes_authorized)

        rep_40 = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cagetwist_xlrh1_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_40.all_40_gates_verified)
        self.assertFalse(rep_40.g39_to_g40_all_passed)
        self.assertFalse(rep_40.gates[39]["passed"])
        self.assertEqual(rep_40.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_40.persistent_emmc_writes_authorized)

    def test_36_g39_tropical_downpour_with_full_sealing_passes(self) -> None:
        res = verify_monsoon_rain_mishoe_firewall(
            weather_profile="MONSOON_EXTREME_50MM_HR_SEALED",
            precipitation_mm_hr=50.0,
            water_spray_rig=True,
            mi_shoe_accessory_attached=True,
            mi_shoe_silicone_perimeter_gasket_sealed=True,
            rain_cover_installed=True,
            mi_shoe_contact_resistance_kohm=250.0,
            mi_shoe_power_rail_enabled=True,
            open_rubber_port_flaps_count=1,
            weather_sealed_cable_gland_or_rain_slicker=True,
        )
        self.assertTrue(res.valid)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_37_g40_whip_moment_helper_feeds_xlr_h1_guard(self) -> None:
        moment_nm = compute_xlr_h1_whip_moment_nm(1.8, 0.14, dynamic_whip_g=1.6)
        self.assertGreater(moment_nm, XLR_H1_TOP_HANDLE_MOMENT_MAX_NM)
        res = verify_xlr_h1_quarter20_and_cage_twist_guard(
            xlr_h1_handle_installed=True,
            total_rig_mass_suspended_from_xlr_h1_kg=1.8,
            top_handle_monitor_moment_nm=moment_nm,
            metal_cage_nato_top_handle_reinforcement=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_XLR_H1_TOP_HANDLE_OVERLOAD_WHIP_SHEAR
        )

    def test_38_donor_audit_large_binaries_dual_mode(self) -> None:
        res = audit_phase125_donor_contracts(include_large_binaries=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertTrue(res.large_binaries_scanned)
            self.assertGreaterEqual(res.files_inspected, 7)
        else:
            self.assertFalse(res.large_binaries_scanned)

    def test_39_h0_h1_trial_entry_allowed_and_g13_to_g40_flags(self) -> None:
        rep_off = evaluate_40gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g40_all_passed)
        self.assertTrue(rep_off.g39_to_g40_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            monsoon_mishoe_kwargs={
                "mi_shoe_contact_resistance_kohm": 10.0,
                "mi_shoe_power_rail_enabled": True,
            },
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g40_all_passed)
        self.assertFalse(rep_bad.offline_37_gates_verified)

    def test_40_g40_explicit_estimated_tilt_override(self) -> None:
        # Shimmed low tilt (< 12.0 um) passes even if gap > 0.25 mm
        res_low = verify_xlr_h1_quarter20_and_cage_twist_guard(
            cage_multi_point_locked=True,
            unshimmed_side_screw_gap_mm=0.35,
            estimated_emount_ffd_tilt_um=8.5,
        )
        self.assertTrue(res_low.valid)

        # Explicit > 12.0 um tilt blocks
        res_high = verify_xlr_h1_quarter20_and_cage_twist_guard(
            cage_multi_point_locked=True,
            unshimmed_side_screw_gap_mm=0.35,
            estimated_emount_ffd_tilt_um=15.0,
        )
        self.assertFalse(res_high.valid)
        self.assertEqual(
            res_high.status, STATUS_BLOCKED_ASYMMETRIC_CAGE_TWIST_FFD_WARPAGE
        )

    def test_41_g39_low_resistance_unpowered_rail_vs_powered_rail(self) -> None:
        res_unpowered = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=0.0,
            mi_shoe_contact_resistance_kohm=10.0,
            mi_shoe_power_rail_enabled=False,
        )
        self.assertTrue(res_unpowered.valid)
        self.assertAlmostEqual(res_unpowered.estimated_leakage_current_ma, 0.0, places=6)

        res_powered = verify_monsoon_rain_mishoe_firewall(
            precipitation_mm_hr=0.0,
            mi_shoe_contact_resistance_kohm=10.0,
            mi_shoe_power_rail_enabled=True,
        )
        self.assertFalse(res_powered.valid)
        self.assertEqual(
            res_powered.status, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )

    def test_42_40gate_report_to_dict_has_expected_top_level_keys(self) -> None:
        rep = evaluate_40gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        for key in (
            "schema",
            "version",
            "verification_mode",
            "offline_37_gates_verified",
            "all_40_gates_verified",
            "g13_to_g40_all_passed",
            "g39_to_g40_all_passed",
            "overall_ready_for_hardware_attach",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "summary",
            "gates",
            "master_38_report",
            "g39_result",
            "g40_result",
        ):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
