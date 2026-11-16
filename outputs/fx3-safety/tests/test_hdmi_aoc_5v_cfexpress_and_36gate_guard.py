"""Fast dual-mode unit tests for Phase 115 — Active Optical HDMI (AOC) Pin-18 +5V
Over-Current / Reverse Backfeed & Unclamped Type-A Port Shear Firewall (Gate G35),
CFexpress Type-A / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal-Throttle
& Door-Open Flush Guard (Gate G36), and Unified 36-Gate Master Safety Preflight
(`G01..G36`).
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
    CFEXPRESS_NVME_THERMAL_THROTTLE_MAX_C,
    DUAL_SLOT_4K120P_HIGH_AMBIENT_MAX_C,
    DUAL_SLOT_SIMULTANEOUS_OVERHEAD_MARGIN,
    G35_GATE_CODE,
    G35_GATE_ID,
    G36_GATE_CODE,
    G36_GATE_ID,
    HDMI_AOC_CFEXPRESS_36GATE_SCHEMA,
    HDMI_AOC_CFEXPRESS_36GATE_VERSION,
    HDMI_PIN18_MAX_UNINJECTED_DRAW_MA,
    HDMI_PIN18_POWER_OFF_BACKFEED_MAX_MA,
    HDMI_PIN18_REVERSE_BACKFEED_MAX_V,
    HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SINGLE_SLOT_CODEC_OVERHEAD_MARGIN,
    STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR,
    STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID,
    STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD,
    STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID,
    STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC,
    STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR,
    STATUS_SAFE,
    STATUS_VERIFIED_G35,
    STATUS_VERIFIED_G36,
    STATUS_VERIFIED_SAFE,
    VPG200_MIN_WRITE_MB_S,
    VPG400_MIN_WRITE_MB_S,
    XAVC_SI_4K120P_BITRATE_MBPS,
    audit_phase115_donor_contracts,
    compute_hdmi_pin18_power_mw,
    compute_hdmi_type_a_cantilever_moment_nm,
    compute_required_sustained_write_mb_s,
    evaluate_36_master_safety_gates,
    evaluate_36gate_preflight,
    evaluate_g35_hdmi_aoc_5v_and_port_shear,
    evaluate_g36_cfexpress_vpg_thermal_and_door_flush,
    main as module_cli_main,
    verify_cfexpress_vpg_thermal_and_door_guard,
    verify_hdmi_aoc_5v_and_port_shear_firewall,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.saltspray_haze_followfocus_and_34gate_guard import (
    STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT,
    STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION,
    evaluate_34gate_preflight,
)


class HdmiAoc5vCfexpressAnd36GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            HDMI_AOC_CFEXPRESS_36GATE_SCHEMA,
            "fx3-hdmi-aoc-5v-cfexpress-36gate-preflight-v1",
        )
        self.assertEqual(HDMI_AOC_CFEXPRESS_36GATE_VERSION, "1.0.0")
        for sym in (
            "HDMI_AOC_CFEXPRESS_36GATE_SCHEMA",
            "G35_GATE_ID",
            "G35_GATE_CODE",
            "G36_GATE_ID",
            "G36_GATE_CODE",
            "STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR",
            "STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD",
            "STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR",
            "STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC",
            "STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT",
            "STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH",
            "audit_phase115_donor_contracts",
            "compute_hdmi_pin18_power_mw",
            "compute_hdmi_type_a_cantilever_moment_nm",
            "compute_required_sustained_write_mb_s",
            "verify_hdmi_aoc_5v_and_port_shear_firewall",
            "verify_cfexpress_vpg_thermal_and_door_guard",
            "evaluate_g35_hdmi_aoc_5v_and_port_shear",
            "evaluate_g36_cfexpress_vpg_thermal_and_door_flush",
            "evaluate_36gate_preflight",
            "evaluate_36_master_safety_gates",
            "hdmi_aoc_5v_cfexpress_and_36gate_guard",
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
            fx3_safety.SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA,
            "fx3-saltspray-haze-followfocus-34gate-preflight-v1",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase115_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.hdmi_display_tokens_verified)
        self.assertTrue(res_default.media_slot_config_tokens_verified)
        self.assertTrue(res_default.media_thermal_nvme_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libInfraAdjMedia",
                    "libInfraMediaConfig",
                    "libInfraMediaDetect",
                    "libInfraMediaCommon",
                )
            ):
                self.assertEqual(
                    flags & os.O_ACCMODE,
                    os.O_RDONLY,
                    f"Non-O_RDONLY open on {path}",
                )

        res_clean = audit_phase115_donor_contracts(force_clean_room=True)
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
                    "libInfraAdjMedia.so",
                    "libInfraMediaConfig.so",
                    "libInfraMediaDetect.so",
                    "libInfraMediaCommon.so",
                ):
                    (d / name).write_bytes(b"corrupt")
            res = audit_phase115_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 8)
        self.assertFalse(res.hdmi_display_tokens_verified)
        self.assertFalse(res.media_slot_config_tokens_verified)
        self.assertFalse(res.media_thermal_nvme_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase115_donor_contracts(
            force_clean_room=True, include_large_binaries=True
        )
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase115_donor_contracts(
                work_root=Path(empty_dir), force_clean_room=False
            )
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Electrical, Mechanical & Media Write-Floor Helpers ---

    def test_05_hdmi_pin18_power_and_cantilever_moment_helpers(self) -> None:
        mw = compute_hdmi_pin18_power_mw(55.0, 5.0)
        self.assertAlmostEqual(mw, 275.0, places=6)
        moment = compute_hdmi_type_a_cantilever_moment_nm(
            0.35, 200.0, shock_factor_g=2.0
        )
        self.assertAlmostEqual(moment, 0.35 * 9.80665 * 0.2 * 2.0, places=6)
        with self.assertRaises(ValueError):
            compute_hdmi_pin18_power_mw(-1.0, 5.0)
        with self.assertRaises(ValueError):
            compute_hdmi_type_a_cantilever_moment_nm(-0.1, 100.0)
        with self.assertRaises(ValueError):
            compute_hdmi_type_a_cantilever_moment_nm(0.2, 100.0, shock_factor_g=0.0)

    def test_06_required_sustained_write_floor_helper(self) -> None:
        single_vpg200 = compute_required_sustained_write_mb_s(
            XAVC_SI_4K120P_BITRATE_MBPS,
            dual_slot_simultaneous_4k120p=False,
            vpg_profile="VPG200",
        )
        self.assertAlmostEqual(single_vpg200, VPG200_MIN_WRITE_MB_S, places=6)

        dual_vpg200 = compute_required_sustained_write_mb_s(
            XAVC_SI_4K120P_BITRATE_MBPS,
            dual_slot_simultaneous_4k120p=True,
            vpg_profile="VPG200",
        )
        self.assertAlmostEqual(
            dual_vpg200,
            VPG200_MIN_WRITE_MB_S * DUAL_SLOT_SIMULTANEOUS_OVERHEAD_MARGIN,
            places=6,
        )

        v90_codec_floor = compute_required_sustained_write_mb_s(
            600.0,
            dual_slot_simultaneous_4k120p=False,
            vpg_profile="V90",
        )
        self.assertAlmostEqual(
            v90_codec_floor,
            (600.0 / 8.0) * SINGLE_SLOT_CODEC_OVERHEAD_MARGIN,
            places=6,
        )

        with self.assertRaises(ValueError):
            compute_required_sustained_write_mb_s(-10.0)
        with self.assertRaises(ValueError):
            compute_required_sustained_write_mb_s(600.0, vpg_profile="VPG999")

    # --- 3. Gate G35 — AOC HDMI Pin-18 +5V & Port Leverage Firewall ---

    def test_07_g35_default_safe_profile_passes(self) -> None:
        res = verify_hdmi_aoc_5v_and_port_shear_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.pin18_overcurrent_safe)
        self.assertTrue(res.pin18_reverse_backfeed_safe)
        self.assertTrue(res.hdmi_port_leverage_shear_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g35_blocks_aoc_hdmi_5v_overcurrent_without_injector(self) -> None:
        res_bad = verify_hdmi_aoc_5v_and_port_shear_firewall(
            recorder_profile="ATOMOS_NINJA_ULTRA_15M_AOC",
            hdmi_pin18_draw_ma=95.0,
            external_hdmi_5v_power_injector=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.pin18_overcurrent_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR
        )

        # Exact 55.0 mA boundary passes without injector
        res_edge = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_pin18_draw_ma=HDMI_PIN18_MAX_UNINJECTED_DRAW_MA,
            external_hdmi_5v_power_injector=False,
        )
        self.assertTrue(res_edge.valid)

        # High draw passes when external +5V power injector is active
        res_inj = verify_hdmi_aoc_5v_and_port_shear_firewall(
            recorder_profile="ATOMOS_NINJA_ULTRA_15M_AOC",
            hdmi_pin18_draw_ma=110.0,
            external_hdmi_5v_power_injector=True,
        )
        self.assertTrue(res_inj.valid)
        self.assertGreaterEqual(len(res_inj.warnings), 1)

    def test_09_g35_blocks_reverse_backfeed_overvoltage(self) -> None:
        res_bad = verify_hdmi_aoc_5v_and_port_shear_firewall(
            recorder_profile="BMD_VIDEO_ASSIST_12G_BACKFEED",
            sink_backfeed_voltage_v=5.42,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.pin18_reverse_backfeed_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD)

        # Exact 5.35 V boundary passes
        res_edge = verify_hdmi_aoc_5v_and_port_shear_firewall(
            sink_backfeed_voltage_v=HDMI_PIN18_REVERSE_BACKFEED_MAX_V,
        )
        self.assertTrue(res_edge.valid)

    def test_10_g35_blocks_power_off_backfeed_leak_without_diode(self) -> None:
        res_bad = verify_hdmi_aoc_5v_and_port_shear_firewall(
            camera_power_off=True,
            sink_pin18_backfeed_ma=4.5,
            hdmi_reverse_blocking_diode_verified=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.pin18_reverse_backfeed_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD)

        # Exact 2.0 mA boundary passes
        res_edge = verify_hdmi_aoc_5v_and_port_shear_firewall(
            camera_power_off=True,
            sink_pin18_backfeed_ma=HDMI_PIN18_POWER_OFF_BACKFEED_MAX_MA,
            hdmi_reverse_blocking_diode_verified=False,
        )
        self.assertTrue(res_edge.valid)

        # Verified reverse blocking diode blocks backfeed path safely
        res_diode = verify_hdmi_aoc_5v_and_port_shear_firewall(
            camera_power_off=True,
            sink_pin18_backfeed_ma=4.5,
            hdmi_reverse_blocking_diode_verified=True,
        )
        self.assertTrue(res_diode.valid)

    def test_11_g35_blocks_unclamped_hdmi_port_leverage_shear(self) -> None:
        res_moment = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_cable_bend_moment_nm=1.65,
            heavy_braided_or_coiled_hdmi_cable=False,
            cage_hdmi_cable_clamp_locked=False,
        )
        self.assertFalse(res_moment.valid)
        self.assertFalse(res_moment.hdmi_port_leverage_shear_safe)
        self.assertEqual(
            res_moment.status, STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR
        )

        res_heavy = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_cable_bend_moment_nm=0.4,
            heavy_braided_or_coiled_hdmi_cable=True,
            cage_hdmi_cable_clamp_locked=False,
        )
        self.assertFalse(res_heavy.valid)
        self.assertEqual(
            res_heavy.status, STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR
        )

        # Exact 1.2 N*m without heavy braided cable passes
        res_edge = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_cable_bend_moment_nm=HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM,
            heavy_braided_or_coiled_hdmi_cable=False,
            cage_hdmi_cable_clamp_locked=False,
        )
        self.assertTrue(res_edge.valid)

        # Locked cage clamp mitigates both moment and heavy cable
        res_clamped = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_cable_bend_moment_nm=2.1,
            heavy_braided_or_coiled_hdmi_cable=True,
            cage_hdmi_cable_clamp_locked=True,
        )
        self.assertTrue(res_clamped.valid)
        self.assertGreaterEqual(len(res_clamped.warnings), 1)

    def test_12_g35_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"hdmi_pin18_draw_ma": float("nan")},
            {"hdmi_pin18_draw_ma": -2.0},
            {"sink_backfeed_voltage_v": float("inf")},
            {"sink_backfeed_voltage_v": -0.5},
            {"sink_pin18_backfeed_ma": -1.0},
            {"hdmi_cable_bend_moment_nm": -0.2},
        ):
            res_bad = verify_hdmi_aoc_5v_and_port_shear_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID)

        res_emmc = verify_hdmi_aoc_5v_and_port_shear_firewall(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_13_g35_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_hdmi_aoc_5v_and_port_shear_firewall(
            hdmi_pin18_draw_ma=90.0,
            external_hdmi_5v_power_injector=False,
            sink_backfeed_voltage_v=5.55,
            hdmi_cable_bend_moment_nm=1.9,
            heavy_braided_or_coiled_hdmi_cable=True,
            cage_hdmi_cable_clamp_locked=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR,
                STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD,
                STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR,
            },
        )

    # --- 4. Gate G36 — CFexpress / SDXC VPG Sustained Write, Thermal & Door Guard ---

    def test_14_g36_default_safe_profile_passes(self) -> None:
        res = verify_cfexpress_vpg_thermal_and_door_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.sustained_write_floor_safe)
        self.assertTrue(res.nvme_thermal_throttle_safe)
        self.assertTrue(res.door_open_flush_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_15_g36_blocks_sustained_write_floor_below_codec(self) -> None:
        res_bad = verify_cfexpress_vpg_thermal_and_door_guard(
            media_profile="UNRATED_CFEXPRESS_CLONE",
            vpg_profile="VPG200",
            sustained_p99_write_mb_s=175.0,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.sustained_write_floor_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )

        # Explicit required_min_write_mb_s exact boundary passes
        res_edge = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=150.0,
            required_min_write_mb_s=150.0,
        )
        self.assertTrue(res_edge.valid)

        # Uncertified VPG200 fails even if momentary speed >= 200
        res_uncert = verify_cfexpress_vpg_thermal_and_door_guard(
            vpg_profile="VPG200",
            vpg_certified=False,
            sustained_p99_write_mb_s=280.0,
        )
        self.assertFalse(res_uncert.valid)
        self.assertEqual(
            res_uncert.status, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )

    def test_16_g36_enforces_dual_slot_simultaneous_overhead_margin(self) -> None:
        # 220 MB/s passes single-slot VPG200 (200 MB/s), fails dual-slot (240 MB/s)
        res_single = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=220.0,
            dual_slot_simultaneous_4k120p=False,
            vpg_profile="VPG200",
        )
        self.assertTrue(res_single.valid)

        res_dual_fail = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=220.0,
            dual_slot_simultaneous_4k120p=True,
            vpg_profile="VPG200",
            ambient_temp_c=25.0,
            sigma_fan_mode="AUTO1",
        )
        self.assertFalse(res_dual_fail.valid)
        self.assertEqual(
            res_dual_fail.status, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )
        self.assertAlmostEqual(res_dual_fail.required_min_write_mb_s, 240.0, places=2)

        res_dual_ok = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=260.0,
            dual_slot_simultaneous_4k120p=True,
            vpg_profile="VPG200",
            ambient_temp_c=25.0,
            sigma_fan_mode="AUTO1",
        )
        self.assertTrue(res_dual_ok.valid)
        self.assertGreaterEqual(len(res_dual_ok.warnings), 1)

    def test_17_g36_blocks_nvme_controller_overtemp_and_boundary(self) -> None:
        res_bad = verify_cfexpress_vpg_thermal_and_door_guard(
            cfexpress_controller_temp_c=84.5,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.nvme_thermal_throttle_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT
        )

        # Exact 82.0 C boundary passes
        res_edge = verify_cfexpress_vpg_thermal_and_door_guard(
            cfexpress_controller_temp_c=CFEXPRESS_NVME_THERMAL_THROTTLE_MAX_C,
        )
        self.assertTrue(res_edge.valid)

    def test_18_g36_blocks_dual_slot_4k120p_high_ambient_weak_fan(self) -> None:
        for weak_fan in ("OFF_IN_REC", "MINIMUM"):
            res_bad = verify_cfexpress_vpg_thermal_and_door_guard(
                sustained_p99_write_mb_s=280.0,
                dual_slot_simultaneous_4k120p=True,
                ambient_temp_c=40.5,
                sigma_fan_mode=weak_fan,
            )
            self.assertFalse(res_bad.valid)
            self.assertFalse(res_bad.nvme_thermal_throttle_safe)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT,
            )

        # Active AUTO1/AUTO2 passes at 40.5 C when controller temp <= 82 C
        res_auto = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=280.0,
            dual_slot_simultaneous_4k120p=True,
            ambient_temp_c=40.5,
            sigma_fan_mode="AUTO1",
            cfexpress_controller_temp_c=74.0,
        )
        self.assertTrue(res_auto.valid)

        # Exact 38.0 C boundary passes
        res_edge = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=280.0,
            dual_slot_simultaneous_4k120p=True,
            ambient_temp_c=DUAL_SLOT_4K120P_HIGH_AMBIENT_MAX_C,
            sigma_fan_mode="MINIMUM",
        )
        self.assertTrue(res_edge.valid)

    def test_19_g36_blocks_media_door_open_during_flush(self) -> None:
        res_bad = verify_cfexpress_vpg_thermal_and_door_guard(
            slot_door_open_detected=True,
            media_flush_or_fat_commit_pending=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.door_open_flush_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH)

        # Idle card swap (door open, no pending flush/commit) passes with warning
        res_idle = verify_cfexpress_vpg_thermal_and_door_guard(
            slot_door_open_detected=True,
            media_flush_or_fat_commit_pending=False,
        )
        self.assertTrue(res_idle.valid)
        self.assertGreaterEqual(len(res_idle.warnings), 1)

    def test_20_g36_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"codec_bitrate_mbps": -100.0},
            {"sustained_p99_write_mb_s": float("nan")},
            {"sustained_p99_write_mb_s": -1.0},
            {"required_min_write_mb_s": -5.0},
            {"cfexpress_controller_temp_c": float("inf")},
            {"cfexpress_controller_temp_c": 200.0},
            {"ambient_temp_c": -60.0},
            {"vpg_profile": "UNKNOWN_TIER"},
            {"sigma_fan_mode": "TURBO_INVALID"},
        ):
            res_bad = verify_cfexpress_vpg_thermal_and_door_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID
            )

        res_emmc = verify_cfexpress_vpg_thermal_and_door_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_21_g36_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_cfexpress_vpg_thermal_and_door_guard(
            sustained_p99_write_mb_s=110.0,
            cfexpress_controller_temp_c=86.0,
            dual_slot_simultaneous_4k120p=True,
            ambient_temp_c=42.0,
            sigma_fan_mode="OFF_IN_REC",
            slot_door_open_detected=True,
            media_flush_or_fat_commit_pending=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC,
                STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT,
                STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH,
            },
        )

    # --- 5. Gate G35 & G36 Evaluators & Unified 36-Gate Master Preflight ---

    def test_22_g35_and_g36_verdicts_dual_mode(self) -> None:
        v35, r35 = evaluate_g35_hdmi_aoc_5v_and_port_shear(force_clean_room=True)
        self.assertTrue(v35.passed)
        self.assertEqual(v35.gate_id, G35_GATE_ID)
        self.assertEqual(v35.gate_code, G35_GATE_CODE)
        self.assertEqual(v35.status, STATUS_VERIFIED_G35)
        self.assertFalse(r35.persistent_emmc_writes_authorized)

        v36, r36 = evaluate_g36_cfexpress_vpg_thermal_and_door_flush(
            force_clean_room=True
        )
        self.assertTrue(v36.passed)
        self.assertEqual(v36.gate_id, G36_GATE_ID)
        self.assertEqual(v36.gate_code, G36_GATE_CODE)
        self.assertEqual(v36.status, STATUS_VERIFIED_G36)
        self.assertFalse(r36.persistent_emmc_writes_authorized)

    def test_23_36gate_offline_default_33_of_36_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_36gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, HDMI_AOC_CFEXPRESS_36GATE_SCHEMA)
        self.assertGreaterEqual(len(rep.gates), 36)
        self.assertEqual(len(rep.gates), 36)
        self.assertEqual(rep.summary["total_gates"], 36)
        self.assertGreaterEqual(rep.summary["verified_gates"], 33)
        self.assertEqual(rep.summary["verified_gates"], 33)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_33_gates_verified)
        self.assertFalse(rep.all_36_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_33_OF_36_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_24_36gate_dry_run_simulated_backup_36_of_36_and_redlines_locked(self) -> None:
        rep = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(rep.gates), 36)
        self.assertEqual(rep.summary["verified_gates"], 36)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g34_verified"], 22)
        self.assertEqual(rep.summary["g35_to_g36_verified"], 2)
        self.assertTrue(rep.all_36_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_36_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_25_36gate_propagates_g35_aoc_backfeed_and_shear_failures(self) -> None:
        rep_oc = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            hdmi_aoc_kwargs={
                "hdmi_pin18_draw_ma": 88.0,
                "external_hdmi_5v_power_injector": False,
            },
        )
        self.assertFalse(rep_oc.all_36_gates_verified)
        self.assertFalse(rep_oc.g35_to_g36_all_passed)
        self.assertFalse(rep_oc.gates[34]["passed"])
        self.assertEqual(
            rep_oc.status, STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR
        )

        rep_bf = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            hdmi_aoc_kwargs={"sink_backfeed_voltage_v": 5.50},
        )
        self.assertFalse(rep_bf.all_36_gates_verified)
        self.assertEqual(rep_bf.status, STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD)

        rep_shear = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            hdmi_aoc_kwargs={
                "hdmi_cable_bend_moment_nm": 1.6,
                "cage_hdmi_cable_clamp_locked": False,
            },
        )
        self.assertFalse(rep_shear.all_36_gates_verified)
        self.assertEqual(
            rep_shear.status, STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR
        )

    def test_26_36gate_propagates_g36_write_thermal_and_door_failures(self) -> None:
        rep_wr = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_media_kwargs={"sustained_p99_write_mb_s": 140.0},
        )
        self.assertFalse(rep_wr.all_36_gates_verified)
        self.assertFalse(rep_wr.gates[35]["passed"])
        self.assertEqual(
            rep_wr.status, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )

        rep_th = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_media_kwargs={"cfexpress_controller_temp_c": 85.0},
        )
        self.assertFalse(rep_th.all_36_gates_verified)
        self.assertEqual(
            rep_th.status, STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT
        )

        rep_door = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_media_kwargs={
                "slot_door_open_detected": True,
                "media_flush_or_fat_commit_pending": True,
            },
        )
        self.assertFalse(rep_door.all_36_gates_verified)
        self.assertEqual(rep_door.status, STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH)

    def test_27_36gate_propagates_g33_g34_and_emmc_redline(self) -> None:
        rep_g33_g34 = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            saltspray_haze_kwargs={
                "coastal_salt_spray_env": True,
                "hydrophobic_vent_membrane_or_housing": False,
            },
            followfocus_gimbal_kwargs={
                "gimbal_mounted": True,
                "zoom_cog_shift_mm": 20.0,
                "gimbal_autotune_after_zoom": False,
            },
        )
        self.assertFalse(rep_g33_g34.all_36_gates_verified)
        self.assertFalse(rep_g33_g34.gates[32]["passed"])
        self.assertFalse(rep_g33_g34.gates[33]["passed"])
        self.assertEqual(
            rep_g33_g34.gates[32]["status"],
            STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT,
        )
        self.assertEqual(
            rep_g33_g34.gates[33]["status"],
            STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION,
        )
        self.assertEqual(
            rep_g33_g34.status, STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT
        )

        rep_emmc = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_36_gates_verified)
        self.assertFalse(rep_emmc.offline_33_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_28_36gate_preserves_g01_to_g34_untouched(self) -> None:
        r34 = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r36 = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r34.gates), 34)
        self.assertGreaterEqual(len(r36.gates), 36)
        self.assertEqual(
            [g["gate_id"] for g in r34.gates],
            [g["gate_id"] for g in r36.gates[:34]],
        )
        self.assertEqual(
            [g["status"] for g in r34.gates],
            [g["status"] for g in r36.gates[:34]],
        )

    def test_29_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_30_cli_verify_36_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-36-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], HDMI_AOC_CFEXPRESS_36GATE_SCHEMA)
        self.assertGreaterEqual(p_off["summary"]["verified_gates"], 33)
        self.assertEqual(p_off["summary"]["verified_gates"], 33)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-36-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertGreaterEqual(p_dry["summary"]["verified_gates"], 36)
        self.assertTrue(p_dry["all_36_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_31_cli_verify_36_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=33/36", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-36-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=33/36", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-36-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_32_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], HDMI_AOC_CFEXPRESS_36GATE_SCHEMA)
        self.assertTrue(payload["all_36_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_33_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_36gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_33_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_34_evaluate_36_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_36_master_safety_gates, evaluate_36gate_preflight)
        rep = evaluate_36_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_36_gates_verified)
        self.assertGreaterEqual(rep.summary["verified_gates"], 36)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_35_donor_corruption_propagates_to_g35_g36_and_36gate_report(self) -> None:
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
                    "libInfraAdjMedia.so",
                    "libInfraMediaConfig.so",
                    "libInfraMediaDetect.so",
                    "libInfraMediaCommon.so",
                ):
                    (d / name).write_bytes(b"bad")
            v35, r35 = evaluate_g35_hdmi_aoc_5v_and_port_shear(
                work_root=tmp, force_clean_room=False
            )
            v36, r36 = evaluate_g36_cfexpress_vpg_thermal_and_door_flush(
                work_root=tmp, force_clean_room=False
            )
        self.assertFalse(v35.passed)
        self.assertFalse(r35.valid)
        self.assertEqual(v35.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v36.passed)
        self.assertFalse(r36.valid)
        self.assertEqual(v36.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_36_prior_cli_subcommands_verify_16_through_34_remain_intact(self) -> None:
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
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_37_g35_g36_gate_ids_and_soc_passthrough_in_36gate_report(self) -> None:
        rep = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_36_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[34]["gate_id"], G35_GATE_ID)
        self.assertEqual(rep.gates[34]["gate_code"], G35_GATE_CODE)
        self.assertEqual(rep.gates[35]["gate_id"], G36_GATE_ID)
        self.assertEqual(rep.gates[35]["gate_code"], G36_GATE_CODE)

    def test_38_36gate_summary_blocks_if_g35_or_g36_requests_emmc_write(self) -> None:
        rep_35 = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            hdmi_aoc_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_35.all_36_gates_verified)
        self.assertFalse(rep_35.g35_to_g36_all_passed)
        self.assertFalse(rep_35.gates[34]["passed"])
        self.assertEqual(rep_35.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_35.persistent_emmc_writes_authorized)

        rep_36 = evaluate_36gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_media_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_36.all_36_gates_verified)
        self.assertFalse(rep_36.g35_to_g36_all_passed)
        self.assertFalse(rep_36.gates[35]["passed"])
        self.assertEqual(rep_36.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_36.persistent_emmc_writes_authorized)

    def test_39_g36_vpg400_and_sdxc_v90_codec_floor_validation(self) -> None:
        # VPG400 requires >= 400 MB/s
        res_vpg400_bad = verify_cfexpress_vpg_thermal_and_door_guard(
            vpg_profile="VPG400",
            sustained_p99_write_mb_s=350.0,
        )
        self.assertFalse(res_vpg400_bad.valid)
        self.assertAlmostEqual(
            res_vpg400_bad.required_min_write_mb_s, VPG400_MIN_WRITE_MB_S, places=2
        )

        res_vpg400_ok = verify_cfexpress_vpg_thermal_and_door_guard(
            vpg_profile="VPG400",
            sustained_p99_write_mb_s=420.0,
        )
        self.assertTrue(res_vpg400_ok.valid)

        # SDXC V90 (90 MB/s) fails 600 Mbps XAVC S-I 4K 120p (75 * 1.25 = 93.75 MB/s)
        res_v90_bad = verify_cfexpress_vpg_thermal_and_door_guard(
            media_profile="SDXC_UHS_II_V90",
            vpg_profile="V90",
            codec_bitrate_mbps=600.0,
            sustained_p99_write_mb_s=90.0,
        )
        self.assertFalse(res_v90_bad.valid)
        self.assertEqual(
            res_v90_bad.status, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )

    def test_40_g35_camera_powered_on_small_sink_leak_vs_overvoltage(self) -> None:
        # When camera is ON and voltage <= 5.35V, small 3mA idle bias doesn't trigger power-off leak fault
        res_on = verify_hdmi_aoc_5v_and_port_shear_firewall(
            camera_power_off=False,
            sink_backfeed_voltage_v=5.10,
            sink_pin18_backfeed_ma=3.0,
            hdmi_reverse_blocking_diode_verified=False,
        )
        self.assertTrue(res_on.valid)
        self.assertTrue(res_on.pin18_reverse_backfeed_safe)


if __name__ == "__main__":
    unittest.main()
