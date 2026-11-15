#!/usr/bin/env python3
"""Phase 103 Test Suite — Stage 17 Wireless Video TX Near-Field EMI / D-Tap Hot-Plug ESD /
Multi-Port 3.3V LTC Clamp HIL, 12-Hour Continuous exFAT Seamless Clip-Spanning & CFexpress
NVMe SMART Wear-Leveling HIL, and 43,200-Second Zero-eMMC-NVRAM-Churn Endurance Co-Emulation.

Exercises 36 fast unit, simulation, fail-closed guard, Stage 17 suite integration,
CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
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
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import wireless_emi_exfat_endurance_emulator as p103  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p103.run_phase103_emi_exfat_endurance_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase103DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p103.inspect_wireless_emi_exfat_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 25)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p103.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p103.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p103.is_forced_clean_room(env))
        paths = p103.resolve_phase103_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p103.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p103.inspect_wireless_emi_exfat_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p103.is_forced_clean_room():
            audit = p103.inspect_wireless_emi_exfat_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p103.resolve_phase103_donor_paths()
        audit = p103.inspect_wireless_emi_exfat_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p103.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p103.ENV_MAC_WORK_ROOT: "/nonexistent_phase103_mac_work_root",
            p103.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase103_main_work_root",
        }
        audit = p103.inspect_wireless_emi_exfat_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_emmc_and_zero_drops(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["stock_cp_fault_count"], 0)
        self.assertEqual(red["emmc_sector_writes"], 0)
        self.assertEqual(red["emmc_wear_level_increments"], 0)
        self.assertEqual(red["cxd90057_gpio_damage_events"], 0)
        self.assertEqual(red["dropped_audio_samples"], 0)
        self.assertEqual(red["dropped_video_frames"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestLongformExfatAndSmartWearHil(unittest.TestCase):
    """Verify 12h (~3.24 TB) exFAT spanning, FAT32 rejection, and SMART thermal/wear rollover."""

    def test_06_12h_4k5994_exfat_session_spans_3_24tb_with_zero_drops(self) -> None:
        res = p103.simulate_longform_exfat_smart_hil(duration_seconds=43_200)
        self.assertTrue(res.passed)
        self.assertEqual(res.duration_seconds, 43_200)
        self.assertAlmostEqual(res.total_recorded_tb, 3.24, places=4)
        self.assertEqual(res.total_recorded_bytes, 3_240_000_000_000)
        self.assertEqual(res.four_gib_boundaries_crossed, 754)
        self.assertEqual(res.sixty_four_gib_boundaries_crossed, 47)
        self.assertEqual(res.dropped_video_frames, 0)
        self.assertEqual(res.dropped_audio_samples, 0)
        self.assertTrue(res.ltc_continuity_verified)
        self.assertEqual(res.ltc_discontinuities, 0)
        self.assertTrue(res.co64_64bit_chunk_offsets_used)
        self.assertEqual(res.relay_rollover_count, 1)
        self.assertEqual(res.active_slot_end, "SLOT_B")
        self.assertGreater(res.nonrealtimemeta_clips_linked, 45)

    def test_07_fat32_sdhc_16gb_and_32gb_fail_closed_for_longform_takes(self) -> None:
        for cap_gb in (16.0, 32.0):
            res = p103.simulate_longform_exfat_smart_hil(
                duration_seconds=1800,
                slot_a=p103.MediaSlotSmartState(
                    slot_id="SLOT_A",
                    card_type="SDHC_UHS_I",
                    filesystem="FAT32",
                    capacity_gb=cap_gb,
                    sustained_write_mb_s=95.0,
                    smart_percentage_used=5.0,
                    spare_blocks_pct=98.0,
                    nand_temp_c=42.0,
                ),
            )
            self.assertFalse(res.passed)
            self.assertTrue(res.fat32_sdhc_rejected)
            self.assertEqual(res.violation_code, "BLOCKED_FAT32_4GIB_SPANNING_TRAP")

    def test_08_cfexpress_nand_over_78c_triggers_ps1_throttle_and_preemptive_rollover(self) -> None:
        res = p103.simulate_longform_exfat_smart_hil(
            duration_seconds=14_400,
            peak_slot_a_nand_temp_c=79.8,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.nvme_ps1_thermal_throttled)
        self.assertEqual(res.nvme_power_state, "PS1")
        self.assertTrue(res.preemptive_rollover_executed)
        self.assertEqual(res.active_slot_end, "SLOT_B")
        self.assertIn("NAND_TEMP_GT_78C_PS1_THROTTLE", res.rollover_trigger_reason)
        self.assertEqual(res.dropped_video_frames, 0)
        self.assertEqual(res.dropped_audio_samples, 0)

    def test_09_smart_spare_below_10pct_triggers_preemptive_rollover_to_healthy_slot_b(self) -> None:
        res = p103.simulate_longform_exfat_smart_hil(
            duration_seconds=14_400,
            slot_a_end_spare_blocks_pct=7.5,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.preemptive_rollover_executed)
        self.assertEqual(res.active_slot_end, "SLOT_B")
        self.assertIn("SMART_SPARE_LT_10PCT", res.rollover_trigger_reason)
        self.assertEqual(res.dropped_video_frames, 0)

    def test_10_dual_slot_smart_exhaustion_without_healthy_failover_blocks_fail_closed(self) -> None:
        unhealthy_b = p103.MediaSlotSmartState(
            slot_id="SLOT_B",
            card_type="CFEXPRESS_TYPE_A",
            filesystem="exFAT",
            capacity_gb=1920.0,
            sustained_write_mb_s=700.0,
            smart_percentage_used=94.0,
            spare_blocks_pct=6.0,
            nand_temp_c=81.0,
        )
        res = p103.simulate_longform_exfat_smart_hil(
            duration_seconds=14_400,
            slot_b=unhealthy_b,
            peak_slot_a_nand_temp_c=80.0,
            slot_a_end_spare_blocks_pct=8.0,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION")
        self.assertEqual(res.active_slot_end, "NONE")

    def test_11_insufficient_media_write_speed_rejected_fail_closed(self) -> None:
        slow_a = p103.MediaSlotSmartState(
            slot_id="SLOT_A",
            card_type="SDXC_V90",
            filesystem="exFAT",
            capacity_gb=512.0,
            sustained_write_mb_s=30.0,
            smart_percentage_used=10.0,
            spare_blocks_pct=98.0,
            nand_temp_c=40.0,
        )
        res = p103.simulate_longform_exfat_smart_hil(duration_seconds=3600, slot_a=slow_a)
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_MEDIA_SPEED_CLASS_INSUFFICIENT")

    def test_12_longform_audio_sample_and_frame_counts_exact_for_12h(self) -> None:
        res = p103.simulate_longform_exfat_smart_hil(duration_seconds=43_200)
        self.assertEqual(res.total_audio_sample_frames, 43_200 * 48_000)
        self.assertGreater(res.total_video_frames, 2_589_000)
        self.assertLess(res.total_video_frames, 2_590_000)

    def test_13_invalid_longform_parameters_raise_domain_error(self) -> None:
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_longform_exfat_smart_hil(duration_seconds=0)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_longform_exfat_smart_hil(video_bitrate_mbps=-5.0)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_longform_exfat_smart_hil(peak_slot_a_nand_temp_c=200.0)


class TestWirelessEmiHotplugAndLtcClampHil(unittest.TestCase):
    """Verify 1000 mW 5/6 GHz EMI desense/shielding, D-Tap hot-plug ESD, and 3.3V LTC clamp."""

    def test_14_1000mw_5ghz_and_6ghz_shielded_coax_and_tmds_eq_pass(self) -> None:
        for band in (5.0, 5.8, 6.0, 6.4):
            res = p103.simulate_wireless_emi_hotplug_ltc_hil(
                tx_power_mw=1000.0,
                tx_band_ghz=band,
                antenna_distance_mm=20.0,
                shielded_coax_hdmi_cable=True,
                audio_shield_isolation=True,
                tmds_re_equalization_active=True,
                multiport_tc_input_vpp=3.3,
            )
            self.assertTrue(res.passed, msg=f"Band {band} GHz failed")
            self.assertGreaterEqual(res.tmds_eye_height_mv, p103.TMDS_MIN_EYE_HEIGHT_MV)
            self.assertLess(res.tmds_ber_estimate, 1e-10)
            self.assertLess(res.mi_shoe_audio_noise_floor_dbfs, -90.0)
            self.assertEqual(res.cxd90057_gpio_damage_events, 0)
            self.assertEqual(res.cxd90057_tmds_damage_events, 0)

    def test_15_unshielded_nearfield_1000mw_tx_raises_fail_closed_emi_desense(self) -> None:
        res = p103.simulate_wireless_emi_hotplug_ltc_hil(
            tx_power_mw=1000.0,
            tx_band_ghz=5.8,
            antenna_distance_mm=20.0,
            shielded_coax_hdmi_cable=False,
            audio_shield_isolation=False,
            tmds_re_equalization_active=False,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.emi_desense_alert_raised)
        self.assertIn("BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE", res.violation_codes)
        self.assertLess(res.tmds_eye_height_mv, p103.TMDS_MIN_EYE_HEIGHT_MV)
        self.assertGreater(res.mi_shoe_audio_noise_floor_dbfs, -50.0)

    def test_16_dtap_live_unisolated_hdmi_hotplug_surge_blocked_before_silicon_damage(self) -> None:
        res = p103.simulate_wireless_emi_hotplug_ltc_hil(
            dtap_powered_tx=True,
            power_on_sequence="DTAP_LIVE_FIRST_HDMI_LATE",
            hot_plug_while_dtap_live_unisolated=True,
            hpd_debounce_ms=10.0,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.dtap_hdmi_surge_blocked)
        self.assertIn("BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE", res.violation_codes)
        self.assertEqual(res.cxd90057_tmds_damage_events, 0)
        self.assertEqual(res.cxd90057_gpio_damage_events, 0)

    def test_17_gnd_first_power_second_signal_last_with_100ms_hpd_passes(self) -> None:
        res = p103.simulate_wireless_emi_hotplug_ltc_hil(
            dtap_powered_tx=True,
            power_on_sequence=p103.POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST,
            hot_plug_while_dtap_live_unisolated=False,
            hpd_debounce_ms=100.0,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.dtap_hdmi_surge_blocked)
        self.assertEqual(res.status, "VERIFIED_EMI_SHIELDED_HOTPLUG_AND_LTC_CLAMP_SAFE")

    def test_18_short_hpd_debounce_under_50ms_blocked(self) -> None:
        res = p103.simulate_wireless_emi_hotplug_ltc_hil(hpd_debounce_ms=25.0)
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE", res.violation_codes)

    def test_19_multiport_ltc_over_5vpp_clamped_below_3v35_and_blocks_fail_closed(self) -> None:
        for vpp in (5.5, 8.5, 12.0):
            res = p103.simulate_wireless_emi_hotplug_ltc_hil(multiport_tc_input_vpp=vpp)
            self.assertFalse(res.passed)
            self.assertTrue(res.ltc_clamp_tripped)
            self.assertLessEqual(res.multiport_ltc_clamped_peak_v, p103.MULTIPORT_LTC_CLAMP_RAIL_V)
            self.assertIn("BLOCKED_TIMECODE_BNC_OVER_VOLTAGE", res.violation_codes)
            self.assertEqual(res.cxd90057_gpio_damage_events, 0)

    def test_20_multiport_ltc_at_or_below_5vpp_passes_without_clamp_trip(self) -> None:
        for vpp in (1.5, 3.0, 5.0):
            res = p103.simulate_wireless_emi_hotplug_ltc_hil(multiport_tc_input_vpp=vpp)
            self.assertTrue(res.passed)
            self.assertFalse(res.ltc_clamp_tripped)
            self.assertEqual(res.cxd90057_gpio_damage_events, 0)

    def test_21_nearfield_efield_physics_decreases_inversely_with_distance(self) -> None:
        e_20mm = p103.compute_nearfield_efield_v_per_m(1000.0, 20.0)
        e_40mm = p103.compute_nearfield_efield_v_per_m(1000.0, 40.0)
        self.assertAlmostEqual(e_20mm / e_40mm, 2.0, places=5)
        self.assertGreater(e_20mm, 300.0)

    def test_22_invalid_emi_parameters_raise_domain_error(self) -> None:
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.compute_nearfield_efield_v_per_m(-10.0, 20.0)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.compute_nearfield_efield_v_per_m(1000.0, 0.0)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_wireless_emi_hotplug_ltc_hil(tx_band_ghz=2.4)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_wireless_emi_hotplug_ltc_hil(multiport_tc_input_vpp=-1.0)


class TestZeroEmmcNvramChurnEndurance(unittest.TestCase):
    """Verify 43,200-second RAM-shadow BKID routing and zero physical eMMC writes."""

    def test_23_12h_43200s_endurance_routes_100pct_bkid_updates_to_ram_shadow(self) -> None:
        res = p103.simulate_12h_zero_emmc_nvram_churn(simulated_seconds=43_200)
        self.assertTrue(res.passed)
        self.assertEqual(res.simulated_seconds, 43_200)
        self.assertEqual(res.reel_increment_events, 800)
        self.assertEqual(res.wb_shift_events, 144)
        self.assertEqual(res.lut_toggle_events, 72)
        self.assertEqual(res.shotmark_events, 240)
        self.assertEqual(res.tally_cycle_events, 720)
        self.assertEqual(res.total_bkid_updates, 1976)
        self.assertEqual(res.ram_shadow_updates, 1976)
        self.assertEqual(res.ram_shadow_hit_rate_pct, 100.0)
        self.assertEqual(res.emmc_sector_writes, 0)
        self.assertEqual(res.emmc_wear_level_increments, 0)
        self.assertEqual(res.nvram_persistent_writes, 0)
        self.assertEqual(res.bk4_persistent_nvram_writes, 0)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(len(res.final_ram_shadow_sha256), 64)

    def test_24_all_emmc_p1_to_p15_and_rpmb_partitions_are_monitored(self) -> None:
        res = p103.simulate_12h_zero_emmc_nvram_churn(simulated_seconds=3600)
        self.assertEqual(len(res.emmc_partitions_monitored), 16)
        for idx in range(1, 16):
            self.assertIn(f"/dev/mmcblk0p{idx}", res.emmc_partitions_monitored)
        self.assertIn("/dev/mmcblk0rpmb", res.emmc_partitions_monitored)

    def test_25_periodic_nvram_flush_hz_gt_zero_blocked_fail_closed(self) -> None:
        res = p103.simulate_12h_zero_emmc_nvram_churn(
            simulated_seconds=600,
            ram_shadow_bkid_enabled=True,
            runtime_nvram_flush_hz=0.2,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_PERIODIC_EMMC_NVRAM_CHURN")
        self.assertEqual(res.emmc_sector_writes, 0)
        self.assertEqual(res.emmc_wear_level_increments, 0)

    def test_26_disabled_ram_shadow_bkid_blocked_fail_closed(self) -> None:
        res = p103.simulate_12h_zero_emmc_nvram_churn(
            simulated_seconds=600,
            ram_shadow_bkid_enabled=False,
            runtime_nvram_flush_hz=0.0,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.violation_code, "BLOCKED_PERIODIC_EMMC_NVRAM_CHURN")
        self.assertEqual(res.emmc_sector_writes, 0)

    def test_27_invalid_endurance_parameters_raise_domain_error(self) -> None:
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_12h_zero_emmc_nvram_churn(simulated_seconds=-10)
        with self.assertRaises(p103.WirelessEmiExfatEnduranceError):
            p103.simulate_12h_zero_emmc_nvram_churn(runtime_nvram_flush_hz=-0.5)

    def test_28_endurance_ram_shadow_hash_is_deterministic_across_runs(self) -> None:
        r1 = p103.simulate_12h_zero_emmc_nvram_churn(simulated_seconds=43_200)
        r2 = p103.simulate_12h_zero_emmc_nvram_churn(simulated_seconds=43_200)
        self.assertEqual(r1, r2)


class TestStage17SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 17 suite integration, CLI flags, determinism & strict hygiene."""

    def test_29_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p103.run_phase103_emi_exfat_endurance_audit(force_clean_room=True)
        rep2 = p103.run_phase103_emi_exfat_endurance_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_30_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--exfat-matrix"],
            ["--clean-room", "--emi-matrix"],
            ["--clean-room", "--endurance-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p103.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_31_suite_in_process_stage17_and_skip_phase103_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage17_phase103_emi_exfat_endurance", rep_on)
        self.assertTrue(rep_on["stage17_phase103_emi_exfat_endurance"]["all_checks_passed"])

        cfg_skip = suite.CoEmulationConfig(force_clean_room=True, include_phase103_emi_exfat_endurance=False)
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage17_phase103_emi_exfat_endurance", rep_skip)

    def test_32_suite_subprocess_summary_and_skip_phase103_flag(self) -> None:
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
        self.assertIn("emi_exfat_12h=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase103",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("emi_exfat_12h=", proc_skip.stdout)

    def test_33_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768(self) -> None:
        src = (FX3_VM_DIR / "wireless_emi_exfat_endurance_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_34_combined_simultaneous_emi_hotplug_and_ltc_faults_accumulate_all_codes(self) -> None:
        res = p103.simulate_wireless_emi_hotplug_ltc_hil(
            tx_power_mw=1000.0,
            antenna_distance_mm=15.0,
            shielded_coax_hdmi_cable=False,
            audio_shield_isolation=False,
            tmds_re_equalization_active=False,
            hot_plug_while_dtap_live_unisolated=True,
            multiport_tc_input_vpp=9.5,
        )
        self.assertFalse(res.passed)
        self.assertEqual(len(res.violation_codes), 3)
        self.assertIn("BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE", res.violation_codes)
        self.assertIn("BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE", res.violation_codes)
        self.assertIn("BLOCKED_TIMECODE_BNC_OVER_VOLTAGE", res.violation_codes)
        self.assertEqual(res.cxd90057_gpio_damage_events, 0)

    def test_35_stage17_local_donor_or_clean_room_mode_via_suite(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        self.assertTrue(rep["all_checks_passed"])
        s17 = rep["stage17_phase103_emi_exfat_endurance"]
        self.assertTrue(s17["all_checks_passed"])
        self.assertIn(s17["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(s17["emmc_sector_writes"], 0)
        self.assertEqual(s17["dropped_video_frames"], 0)
        self.assertEqual(s17["dropped_audio_samples"], 0)

    def test_36_no_unexpected_files_or_raw_bytes_in_json_suite_payload(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
