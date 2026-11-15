"""Fast dual-mode unit tests for Milestone Phase 100 — Cinema Wireless Video TX EMI &
D-Tap/HDMI Hot-Plug ESD Guard (G29), Long-Form exFAT Clip-Spanning / CFexpress SMART Wear /
Zero-NVRAM-Churn Endurance Guard (G30), and Unified 30-Gate Master Safety Preflight (`G01..G30`).
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
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.sensor_curtain_subzero_and_28gate_guard import (
    STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD,
    STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK,
    evaluate_28gate_preflight,
)
from fx3_safety.wireless_tx_emi_endurance_and_30gate_guard import (
    FAT32_4GIB_WALL_BYTES,
    FAT32_SPANNING_MAX_CONTINUOUS_MIN,
    FILESYSTEM_EXFAT,
    G29_GATE_CODE,
    G29_GATE_ID,
    G30_GATE_CODE,
    G30_GATE_ID,
    LONGFORM_DEFAULT_CONTINUOUS_MIN,
    MEDIA_NAND_MAX_TEMP_C,
    MEDIA_SMART_MAX_USED_PCT,
    MEDIA_SPARE_BLOCKS_MIN_PCT,
    MULTIPORT_TC_MAX_SAFE_VPP,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID,
    STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP,
    STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION,
    STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE,
    STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE,
    STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE,
    STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID,
    STATUS_SAFE,
    STATUS_VERIFIED_G29,
    STATUS_VERIFIED_G30,
    STATUS_VERIFIED_SAFE,
    WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA,
    WIRELESS_EMI_ENDURANCE_30GATE_VERSION,
    WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM,
    WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW,
    audit_phase100_donor_contracts,
    compute_emmc_nvram_wear_cycles,
    compute_nearfield_efield_v_per_m,
    estimate_recording_footprint_gib,
    evaluate_30_master_safety_gates,
    evaluate_30gate_preflight,
    evaluate_g29_wireless_tx_emi_and_hotplug_esd,
    evaluate_g30_longform_endurance_and_nvram,
    main as module_cli_main,
    verify_longform_exfat_smart_and_nvram_guard,
    verify_wireless_tx_emi_and_hotplug_esd_guard,
)


class WirelessTxEmiEnduranceAnd30GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA,
            "fx3-wireless-tx-emi-endurance-30gate-preflight-v1",
        )
        self.assertEqual(WIRELESS_EMI_ENDURANCE_30GATE_VERSION, "1.0.0")
        for sym in (
            "WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA",
            "G29_GATE_ID",
            "G30_GATE_ID",
            "STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE",
            "STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE",
            "STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE",
            "STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP",
            "STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION",
            "STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN",
            "audit_phase100_donor_contracts",
            "compute_nearfield_efield_v_per_m",
            "estimate_recording_footprint_gib",
            "compute_emmc_nvram_wear_cycles",
            "verify_wireless_tx_emi_and_hotplug_esd_guard",
            "verify_longform_exfat_smart_and_nvram_guard",
            "evaluate_g29_wireless_tx_emi_and_hotplug_esd",
            "evaluate_g30_longform_endurance_and_nvram",
            "evaluate_30gate_preflight",
            "evaluate_30_master_safety_gates",
            "wireless_tx_emi_endurance_and_30gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Ensure prior Phase 44/61/97 exports were NOT clobbered
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY, "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH")
        self.assertEqual(fx3_safety.NP_FZ100_NOMINAL_MV, 7200)

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase100_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.exfat_relay_rec_tokens_verified)
        self.assertTrue(res_default.smart_media_life_tokens_verified)
        self.assertTrue(res_default.hdmi_hpd_debounce_tokens_verified)
        self.assertTrue(res_default.nvram_backup_write_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libInfraMediaMount",
                    "libInfraMediaCommon",
                    "libbackup.so",
                    "libBackupManager",
                    "libInfraFsys",
                    "libHotplug",
                )
            ):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase100_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 6)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for name in (
                "libInfraMediaMount.so",
                "libInfraMediaCommon.so",
                "libbackup.so",
                "libBackupManager.so",
                "libInfraFsys.so",
            ):
                (fx3_lib / name).write_bytes(b"corrupt")
            (fx6_lib / "libHotplug.so").write_bytes(b"corrupt")
            res = audit_phase100_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 6)
        self.assertFalse(res.smart_media_life_tokens_verified)
        self.assertFalse(res.nvram_backup_write_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase100_donor_contracts(force_clean_room=True, include_large_binaries=True)
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase100_donor_contracts(work_root=Path(empty_dir), force_clean_room=False)
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Physics & Endurance Helpers ---

    def test_05_nearfield_efield_and_endurance_physics_helpers(self) -> None:
        e_unshielded = compute_nearfield_efield_v_per_m(1000.0, 20.0)
        e_shielded = compute_nearfield_efield_v_per_m(1000.0, 20.0, shielding_attenuation_db=20.0)
        self.assertGreater(e_unshielded, 200.0)
        self.assertAlmostEqual(e_shielded, e_unshielded * 0.1, places=4)
        self.assertEqual(compute_nearfield_efield_v_per_m(0.0, 25.0), 0.0)
        with self.assertRaises(ValueError):
            compute_nearfield_efield_v_per_m(500.0, 0.0)

        gib_8h = estimate_recording_footprint_gib(480.0, 200.0)
        self.assertGreater(gib_8h, 600.0)
        self.assertGreater(gib_8h * (1024 ** 3), FAT32_4GIB_WALL_BYTES)
        with self.assertRaises(ValueError):
            estimate_recording_footprint_gib(-1.0, 200.0)

        self.assertEqual(compute_emmc_nvram_wear_cycles(0.0, 480.0), 0)
        self.assertEqual(compute_emmc_nvram_wear_cycles(1.0, 480.0), 28800)
        with self.assertRaises(ValueError):
            compute_emmc_nvram_wear_cycles(-0.5, 60.0)

    # --- 3. Gate G29 — Wireless TX Near-Field EMI, D-Tap/HDMI ESD & LTC ---

    def test_06_g29_default_healthy_configuration_passes(self) -> None:
        res = verify_wireless_tx_emi_and_hotplug_esd_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.nearfield_emi_safe)
        self.assertTrue(res.hdmi_hotplug_esd_safe)
        self.assertTrue(res.timecode_bnc_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_07_g29_blocks_nearfield_5ghz_6ghz_tx_emi_desense(self) -> None:
        res = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_profile="Teradek_Bolt6_XT",
            wireless_band="6GHz",
            wireless_tx_power_mw=500.0,
            antenna_to_mishoe_or_hdmi_mm=20.0,
            shielded_coax_hdmi_cable=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.nearfield_emi_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)
        self.assertGreater(res.predicted_nearfield_e_field_v_per_m, 15.0)

    def test_08_g29_nearfield_emi_boundaries_and_shielded_coax_mitigation(self) -> None:
        # Power at exact 250.0 mW threshold passes
        res_pow_edge = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_power_mw=WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW,
            antenna_to_mishoe_or_hdmi_mm=20.0,
            shielded_coax_hdmi_cable=False,
        )
        self.assertTrue(res_pow_edge.valid)

        # Separation at exact 35.0 mm threshold passes
        res_dist_edge = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_power_mw=1000.0,
            antenna_to_mishoe_or_hdmi_mm=WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM,
            shielded_coax_hdmi_cable=False,
        )
        self.assertTrue(res_dist_edge.valid)

        # Shielded coax HDMI cable mitigates close high-power TX with advisory warning
        res_shielded = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_power_mw=1000.0,
            antenna_to_mishoe_or_hdmi_mm=20.0,
            shielded_coax_hdmi_cable=True,
        )
        self.assertTrue(res_shielded.valid)
        self.assertTrue(res_shielded.nearfield_emi_safe)
        self.assertGreaterEqual(len(res_shielded.warnings), 1)

    def test_09_g29_blocks_dtap_power_sequence_violation(self) -> None:
        res = verify_wireless_tx_emi_and_hotplug_esd_guard(
            dtap_powered_wireless_tx=True,
            power_on_sequence="HDMI_FIRST_DTAP_LAST",
            hot_plug_while_dtap_live_unisolated=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.hdmi_hotplug_esd_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE)

    def test_10_g29_blocks_live_dtap_hdmi_hotplug_and_allows_safe_sequence(self) -> None:
        res_live = verify_wireless_tx_emi_and_hotplug_esd_guard(
            dtap_powered_wireless_tx=True,
            power_on_sequence=POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST,
            hot_plug_while_dtap_live_unisolated=True,
        )
        self.assertFalse(res_live.valid)
        self.assertFalse(res_live.hdmi_hotplug_esd_safe)
        self.assertEqual(res_live.status, STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE)

        res_standalone_hotplug = verify_wireless_tx_emi_and_hotplug_esd_guard(
            dtap_powered_wireless_tx=False,
            hot_plug_while_dtap_live_unisolated=True,
        )
        self.assertFalse(res_standalone_hotplug.valid)
        self.assertEqual(res_standalone_hotplug.status, STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE)

        res_safe = verify_wireless_tx_emi_and_hotplug_esd_guard(
            dtap_powered_wireless_tx=True,
            power_on_sequence=POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST,
            hot_plug_while_dtap_live_unisolated=False,
        )
        self.assertTrue(res_safe.valid)
        self.assertTrue(res_safe.hdmi_hotplug_esd_safe)

    def test_11_g29_blocks_multiport_timecode_over_voltage_and_checks_boundary(self) -> None:
        res_12v = verify_wireless_tx_emi_and_hotplug_esd_guard(multiport_tc_input_vpp=12.0)
        self.assertFalse(res_12v.valid)
        self.assertFalse(res_12v.timecode_bnc_safe)
        self.assertEqual(res_12v.status, STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE)

        res_edge_over = verify_wireless_tx_emi_and_hotplug_esd_guard(multiport_tc_input_vpp=5.01)
        self.assertFalse(res_edge_over.valid)
        self.assertEqual(res_edge_over.status, STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE)

        res_edge_ok = verify_wireless_tx_emi_and_hotplug_esd_guard(
            multiport_tc_input_vpp=MULTIPORT_TC_MAX_SAFE_VPP,
        )
        self.assertTrue(res_edge_ok.valid)
        self.assertTrue(res_edge_ok.timecode_bnc_safe)

    def test_12_g29_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"wireless_tx_power_mw": float("nan")},
            {"wireless_tx_power_mw": -10.0},
            {"antenna_to_mishoe_or_hdmi_mm": 0.0},
            {"hdmi_hpd_debounce_ms": -5.0},
            {"multiport_tc_input_vpp": -1.0},
        ):
            res_bad = verify_wireless_tx_emi_and_hotplug_esd_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID)

        res_hpd_warn = verify_wireless_tx_emi_and_hotplug_esd_guard(hdmi_hpd_debounce_ms=10.0)
        self.assertTrue(res_hpd_warn.valid)
        self.assertGreaterEqual(len(res_hpd_warn.warnings), 1)

        res_emmc = verify_wireless_tx_emi_and_hotplug_esd_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_13_g29_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_power_mw=800.0,
            antenna_to_mishoe_or_hdmi_mm=15.0,
            shielded_coax_hdmi_cable=False,
            dtap_powered_wireless_tx=True,
            power_on_sequence="POWER_LAST",
            hot_plug_while_dtap_live_unisolated=True,
            multiport_tc_input_vpp=12.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE,
                STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE,
                STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE,
            },
        )

    # --- 4. Gate G30 — Long-Form exFAT Spanning, CFexpress SMART & Zero NVRAM Churn ---

    def test_14_g30_default_healthy_8h_configuration_passes(self) -> None:
        res = verify_longform_exfat_smart_and_nvram_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.planned_continuous_min, LONGFORM_DEFAULT_CONTINUOUS_MIN)
        self.assertEqual(res.filesystem, FILESYSTEM_EXFAT)
        self.assertTrue(res.fat32_4gib_trap_free)
        self.assertTrue(res.media_smart_endurance_safe)
        self.assertTrue(res.zero_nvram_churn_safe)
        self.assertEqual(res.estimated_emmc_nvram_write_cycles, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_15_g30_blocks_fat32_4gib_spanning_trap_and_checks_boundaries(self) -> None:
        res_fat32 = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=360.0,
            filesystem="FAT32",
        )
        self.assertFalse(res_fat32.valid)
        self.assertFalse(res_fat32.fat32_4gib_trap_free)
        self.assertEqual(res_fat32.status, STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)

        res_edge_over = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=10.1,
            filesystem="vfat",
        )
        self.assertFalse(res_edge_over.valid)
        self.assertEqual(res_edge_over.status, STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)

        res_edge_ok = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=FAT32_SPANNING_MAX_CONTINUOUS_MIN,
            filesystem="FAT32",
        )
        self.assertTrue(res_edge_ok.valid)

        res_24h_exfat = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=1440.0,
            filesystem=FILESYSTEM_EXFAT,
        )
        self.assertTrue(res_24h_exfat.valid)
        self.assertGreater(res_24h_exfat.estimated_recording_gib, 2000.0)

    def test_16_g30_blocks_smart_percentage_used_over_90(self) -> None:
        res_bad = verify_longform_exfat_smart_and_nvram_guard(smart_percentage_used=91)
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.media_smart_endurance_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION)

        res_edge = verify_longform_exfat_smart_and_nvram_guard(smart_percentage_used=MEDIA_SMART_MAX_USED_PCT)
        self.assertTrue(res_edge.valid)

    def test_17_g30_blocks_low_spare_blocks_and_high_nand_temp(self) -> None:
        res_spare_bad = verify_longform_exfat_smart_and_nvram_guard(spare_blocks_pct=9.9)
        self.assertFalse(res_spare_bad.valid)
        self.assertFalse(res_spare_bad.media_smart_endurance_safe)
        self.assertEqual(res_spare_bad.status, STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION)

        res_spare_ok = verify_longform_exfat_smart_and_nvram_guard(spare_blocks_pct=MEDIA_SPARE_BLOCKS_MIN_PCT)
        self.assertTrue(res_spare_ok.valid)

        res_temp_bad = verify_longform_exfat_smart_and_nvram_guard(media_nand_temp_c=78.1)
        self.assertFalse(res_temp_bad.valid)
        self.assertFalse(res_temp_bad.media_smart_endurance_safe)
        self.assertEqual(res_temp_bad.status, STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION)

        res_temp_ok = verify_longform_exfat_smart_and_nvram_guard(media_nand_temp_c=MEDIA_NAND_MAX_TEMP_C)
        self.assertTrue(res_temp_ok.valid)

    def test_18_g30_blocks_periodic_emmc_nvram_churn_and_disabled_ram_shadow(self) -> None:
        res_hz = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=480.0,
            runtime_nvram_flush_hz=0.25,
        )
        self.assertFalse(res_hz.valid)
        self.assertFalse(res_hz.zero_nvram_churn_safe)
        self.assertEqual(res_hz.status, STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN)
        self.assertEqual(res_hz.estimated_emmc_nvram_write_cycles, 7200)

        res_no_shadow = verify_longform_exfat_smart_and_nvram_guard(
            runtime_nvram_flush_hz=0.0,
            ram_shadow_bkid_enabled=False,
        )
        self.assertFalse(res_no_shadow.valid)
        self.assertEqual(res_no_shadow.status, STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN)

    def test_19_g30_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"planned_continuous_min": float("nan")},
            {"planned_continuous_min": -5.0},
            {"bitrate_mbps": 0.0},
            {"smart_percentage_used": 300.0},
            {"spare_blocks_pct": -1.0},
            {"spare_blocks_pct": 105.0},
            {"media_nand_temp_c": 150.0},
            {"runtime_nvram_flush_hz": -0.01},
        ):
            res_bad = verify_longform_exfat_smart_and_nvram_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)

        res_emmc = verify_longform_exfat_smart_and_nvram_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_20_g30_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=600.0,
            filesystem="FAT32",
            smart_percentage_used=96,
            spare_blocks_pct=4.5,
            media_nand_temp_c=83.0,
            runtime_nvram_flush_hz=1.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP,
                STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION,
                STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN,
            },
        )

    # --- 5. Gate G29 & G30 Evaluators & Unified 30-Gate Master Preflight ---

    def test_21_g29_and_g30_verdicts_dual_mode(self) -> None:
        v29, r29 = evaluate_g29_wireless_tx_emi_and_hotplug_esd(force_clean_room=True)
        self.assertTrue(v29.passed)
        self.assertEqual(v29.gate_id, G29_GATE_ID)
        self.assertEqual(v29.gate_code, G29_GATE_CODE)
        self.assertEqual(v29.status, STATUS_VERIFIED_G29)
        self.assertFalse(r29.persistent_emmc_writes_authorized)

        v30, r30 = evaluate_g30_longform_endurance_and_nvram(force_clean_room=True)
        self.assertTrue(v30.passed)
        self.assertEqual(v30.gate_id, G30_GATE_ID)
        self.assertEqual(v30.gate_code, G30_GATE_CODE)
        self.assertEqual(v30.status, STATUS_VERIFIED_G30)
        self.assertFalse(r30.persistent_emmc_writes_authorized)

    def test_22_30gate_offline_default_27_of_30_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_30gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 30)
        self.assertEqual(rep.summary["total_gates"], 30)
        self.assertEqual(rep.summary["verified_gates"], 27)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_27_gates_verified)
        self.assertFalse(rep.all_30_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_27_OF_30_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_23_30gate_dry_run_simulated_backup_30_of_30_and_redlines_locked(self) -> None:
        rep = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 30)
        self.assertEqual(rep.summary["verified_gates"], 30)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g28_verified"], 16)
        self.assertEqual(rep.summary["g29_to_g30_verified"], 2)
        self.assertTrue(rep.all_30_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_30_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_24_30gate_propagates_g29_emi_hotplug_and_tc_failures(self) -> None:
        rep_emi = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            wireless_tx_emi_kwargs={
                "wireless_tx_power_mw": 600.0,
                "antenna_to_mishoe_or_hdmi_mm": 18.0,
                "shielded_coax_hdmi_cable": False,
            },
        )
        self.assertFalse(rep_emi.all_30_gates_verified)
        self.assertFalse(rep_emi.g29_to_g30_all_passed)
        self.assertFalse(rep_emi.gates[28]["passed"])
        self.assertEqual(rep_emi.status, STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)

        rep_esd = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            wireless_tx_emi_kwargs={
                "dtap_powered_wireless_tx": True,
                "power_on_sequence": "HDMI_FIRST_GND_LAST",
            },
        )
        self.assertFalse(rep_esd.all_30_gates_verified)
        self.assertEqual(rep_esd.status, STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE)

        rep_tc = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            wireless_tx_emi_kwargs={"multiport_tc_input_vpp": 12.0},
        )
        self.assertFalse(rep_tc.all_30_gates_verified)
        self.assertEqual(rep_tc.status, STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE)

    def test_25_30gate_propagates_g30_fat32_smart_and_nvram_failures(self) -> None:
        rep_fat = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            longform_endurance_kwargs={"planned_continuous_min": 420.0, "filesystem": "FAT32"},
        )
        self.assertFalse(rep_fat.all_30_gates_verified)
        self.assertFalse(rep_fat.gates[29]["passed"])
        self.assertEqual(rep_fat.status, STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)

        rep_smart = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            longform_endurance_kwargs={"smart_percentage_used": 95},
        )
        self.assertFalse(rep_smart.all_30_gates_verified)
        self.assertEqual(rep_smart.status, STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION)

        rep_nvram = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            longform_endurance_kwargs={"runtime_nvram_flush_hz": 0.5},
        )
        self.assertFalse(rep_nvram.all_30_gates_verified)
        self.assertEqual(rep_nvram.status, STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN)

    def test_26_30gate_propagates_g27_g28_and_emmc_redline(self) -> None:
        rep_g27_g28 = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            sensor_curtain_kwargs={"concert_show_laser_or_automotive_lidar_env": True},
            subzero_altitude_kwargs={"battery_cell_temp_c": -20.0, "battery_soc_pct": 45.0},
        )
        self.assertFalse(rep_g27_g28.all_30_gates_verified)
        self.assertFalse(rep_g27_g28.gates[26]["passed"])
        self.assertFalse(rep_g27_g28.gates[27]["passed"])
        self.assertEqual(rep_g27_g28.gates[26]["status"], STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)
        self.assertEqual(rep_g27_g28.gates[27]["status"], STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK)
        self.assertEqual(rep_g27_g28.status, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

        rep_emmc = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_30_gates_verified)
        self.assertFalse(rep_emmc.offline_27_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_27_30gate_preserves_g01_to_g28_untouched(self) -> None:
        r28 = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r30 = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r28.gates), 28)
        self.assertEqual(len(r30.gates), 30)
        self.assertEqual(
            [g["gate_id"] for g in r28.gates],
            [g["gate_id"] for g in r30.gates[:28]],
        )
        self.assertEqual(
            [g["status"] for g in r28.gates],
            [g["status"] for g in r30.gates[:28]],
        )

    def test_28_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_29_cli_verify_30_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-30-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 27)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-30-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 30)
        self.assertTrue(p_dry["all_30_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_30_cli_verify_30_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=27/30", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-30-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=27/30", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-30-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_31_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_30gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_27_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_32_evaluate_30_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_30_master_safety_gates, evaluate_30gate_preflight)
        rep = evaluate_30_master_safety_gates(DEFAULT_REPO_ROOT, dry_run_simulated_backup=True)
        self.assertTrue(rep.all_30_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 30)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_33_donor_corruption_propagates_to_g29_g30_and_30gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for name in (
                "libInfraMediaMount.so",
                "libInfraMediaCommon.so",
                "libbackup.so",
                "libBackupManager.so",
                "libInfraFsys.so",
            ):
                (fx3_lib / name).write_bytes(b"bad")
            (fx6_lib / "libHotplug.so").write_bytes(b"bad")
            v29, r29 = evaluate_g29_wireless_tx_emi_and_hotplug_esd(work_root=tmp, force_clean_room=False)
            v30, r30 = evaluate_g30_longform_endurance_and_nvram(work_root=tmp, force_clean_room=False)
        self.assertFalse(v29.passed)
        self.assertFalse(r29.valid)
        self.assertEqual(v29.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v30.passed)
        self.assertFalse(r30.valid)
        self.assertEqual(v30.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_34_prior_cli_subcommands_verify_16_through_28_remain_intact(self) -> None:
        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
            "verify-28-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_35_g29_boundary_1000mw_unshielded_34_9mm_and_dtap_safe_off(self) -> None:
        res_unshielded = verify_wireless_tx_emi_and_hotplug_esd_guard(
            wireless_tx_profile="DJI_SDR",
            wireless_band="DFS",
            wireless_tx_power_mw=1000.0,
            antenna_to_mishoe_or_hdmi_mm=34.9,
            shielded_coax_hdmi_cable=False,
        )
        self.assertFalse(res_unshielded.valid)
        self.assertEqual(res_unshielded.status, STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)

        res_dtap_off = verify_wireless_tx_emi_and_hotplug_esd_guard(
            dtap_powered_wireless_tx=False,
            power_on_sequence="ANY_ORDER_NO_DTAP",
            hot_plug_while_dtap_live_unisolated=False,
        )
        self.assertTrue(res_dtap_off.valid)

    def test_36_g30_optional_large_binary_audit_and_soc_passthrough_in_30gate(self) -> None:
        rep = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_30_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[28]["gate_id"], G29_GATE_ID)
        self.assertEqual(rep.gates[29]["gate_id"], G30_GATE_ID)

    def test_37_g30_nand_temp_78c_and_smart_90pct_exact_boundaries(self) -> None:
        res_ok = verify_longform_exfat_smart_and_nvram_guard(
            planned_continuous_min=720.0,
            filesystem=FILESYSTEM_EXFAT,
            smart_percentage_used=90,
            spare_blocks_pct=10.0,
            media_nand_temp_c=78.0,
            runtime_nvram_flush_hz=0.0,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.media_smart_endurance_safe)
        self.assertTrue(res_ok.fat32_4gib_trap_free)
        self.assertTrue(res_ok.zero_nvram_churn_safe)

    def test_38_30gate_summary_blocks_if_g29_or_g30_requests_emmc_write(self) -> None:
        rep = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            wireless_tx_emi_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep.all_30_gates_verified)
        self.assertFalse(rep.g29_to_g30_all_passed)
        self.assertFalse(rep.gates[28]["passed"])
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.persistent_emmc_writes_authorized)


if __name__ == "__main__":
    unittest.main()
