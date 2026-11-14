#!/usr/bin/env python3
"""Phase 53 Test Suite — Stage 6 Virtual FX3 HIL Dynamic Fault-Injection & Thermal / C2PA Harness.

Exercises 28 fast unit, fault-injection, integration, CLI, and hygiene tests across
BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import cxd90057_dtb_and_mhlx_emulator as p41  # noqa: E402
import dual_ap_cp_ivshmem_bridge as p24  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402
import fx3_vm_hil_fault_harness as p53  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p53.run_phase53_hil_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestHilDonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and hard-locked redlines."""

    def test_01_clean_room_donor_audit_verifies_all_markers(self) -> None:
        audit = p53.inspect_hil_donor_artifacts(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 5)
        self.assertEqual(audit.missing_markers, ())
        self.assertEqual(audit.wlan_rsrc_sha256, p53.FX6_WLAN_RSRC_DONOR_SHA256)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p53.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p53.is_forced_clean_room(env))
        paths = p53.resolve_phase53_donor_paths(env=env)
        for path in paths.values():
            self.assertIn(p53.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p53.inspect_hil_donor_artifacts(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p53.is_forced_clean_room():
            audit = p53.inspect_hil_donor_artifacts()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p53.resolve_phase53_donor_paths()
        audit = p53.inspect_hil_donor_artifacts()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 5)
            self.assertEqual(audit.wlan_rsrc_sha256, p53.FX6_WLAN_RSRC_DONOR_SHA256)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_gracefully(self) -> None:
        env = {
            p53.ENV_MAC_WORK_ROOT: "/nonexistent_phase53_mac_work_root",
            p53.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase53_main_work_root",
        }
        audit = p53.inspect_hil_donor_artifacts(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)


class TestHil01To04NominalThermalAudioPower(unittest.TestCase):
    """Verify HIL-01..HIL-04: Nominal 4K60, OFF_IN_REC Thermal Climb, XLR-H1 Detach, NP-FZ100/VBUS."""

    def test_05_hil01_nominal_4k60_cine_ei_xlr_h1_and_ext_lk(self) -> None:
        s1 = _get_clean_room_audit()["scenarios"]["HIL-01"]
        self.assertTrue(s1["passed"])
        self.assertEqual(s1["status"], "HIL_NOMINAL_OK")
        self.assertEqual(s1["soc_temp_c"], 54.0)
        self.assertEqual(s1["battery_mv"], 7980)
        self.assertEqual(s1["battery_soc_pct"], 88)
        self.assertEqual(s1["usbpd_mv"], 9000)
        self.assertEqual(s1["audio_source"], p53.AUDIO_SOURCE_XLR_H1)
        self.assertTrue(s1["vmc_bncm1_ext_lk_locked"])
        self.assertEqual(s1["dropped_frames"], 0)
        self.assertTrue(s1["rtmd_all_packets_valid"])
        self.assertEqual(s1["cp_mutation_bytes"], 0)
        self.assertEqual(s1["wdt_resets"], 0)

    def test_06_hil02_off_in_rec_thermal_climb_48_64_83_91(self) -> None:
        s2 = _get_clean_room_audit()["scenarios"]["HIL-02"]
        self.assertTrue(s2["passed"])
        self.assertEqual(s2["status"], "GRACEFUL_THERMAL_TEARDOWN_CLEAN")
        self.assertTrue(s2["fan_pwm_override_engaged"])
        self.assertTrue(s2["amber_hud_warning_triggered"])
        self.assertTrue(s2["graceful_teardown_triggered"])
        self.assertTrue(s2["xavc_trailer_flushed"])
        self.assertTrue(s2["tmpfs_overlay_torn_down"])
        self.assertFalse(s2["exfat_volume_dirty"])
        self.assertEqual(s2["unfinalized_rsv_count"], 0)

        tl = s2["timeline"]
        self.assertEqual(len(tl), 4)
        # Step 0 (48C): OFF_IN_REC idle
        self.assertFalse(tl[0]["fan_pwm_override_active"])
        self.assertEqual(tl[0]["pwm_duty_pct"], 0)
        # Step 1 (64C): automatic PWM override active
        self.assertTrue(tl[1]["fan_pwm_override_active"])
        self.assertEqual(tl[1]["effective_fan_mode"], p53.FAN_MODE_AUTO_COOLING_OVERRIDE)
        self.assertGreater(tl[1]["pwm_duty_pct"], 0)
        # Step 2 (83C): amber HUD thermal warning
        self.assertTrue(tl[2]["hud_thermal_warning"])
        self.assertFalse(tl[2]["graceful_teardown_triggered"])
        # Step 3 (91C): graceful teardown & clean exFAT unmount
        self.assertTrue(tl[3]["graceful_teardown_triggered"])
        self.assertEqual(tl[3]["exfat_volume_flags_hex"], "0x0000")

    def test_07_hil02_cfexpress_68c_triggers_fan_pwm_override_even_when_soc_cool(self) -> None:
        out = p53.evaluate_thermal_pwm_step(
            0,
            soc_temp_c=55.0,
            cfexpress_temp_c=68.0,
            requested_fan_mode=p53.FAN_MODE_OFF_IN_REC,
        )
        self.assertTrue(out.fan_pwm_override_active)
        self.assertEqual(out.effective_fan_mode, p53.FAN_MODE_AUTO_COOLING_OVERRIDE)
        self.assertGreaterEqual(out.pwm_duty_pct, 50)
        self.assertFalse(out.hud_thermal_warning)

    def test_08_hil02_rejects_implausible_temp_or_bad_fan_mode(self) -> None:
        with self.assertRaises(p53.HilHarnessError):
            p53.evaluate_thermal_pwm_step(0, soc_temp_c=-30.0)
        with self.assertRaises(p53.HilHarnessError):
            p53.evaluate_thermal_pwm_step(0, soc_temp_c=50.0, cfexpress_temp_c=140.0)
        with self.assertRaises(p53.HilHarnessError):
            p53.evaluate_thermal_pwm_step(0, soc_temp_c=50.0, requested_fan_mode="TURBO_MAX")

    def test_09_hil03_live_xlr_h1_hot_detach_p11_fallback_without_cp_wake(self) -> None:
        s3 = _get_clean_room_audit()["scenarios"]["HIL-03"]
        self.assertTrue(s3["passed"])
        self.assertEqual(s3["status"], "P11_FALLBACK_TO_INTERNAL_STEREO_OK")
        self.assertEqual(s3["p11_queue_id"], "0x91db059b")
        self.assertEqual(s3["detach_evt_cmd"], "0x88000002")
        self.assertTrue(s3["intercepted_by_p11"])
        self.assertTrue(s3["ivshmem_tx_ring_clean"])
        self.assertFalse(s3["cp_woken_or_crashed"])
        self.assertFalse(s3["xlr_h1_attached"])
        self.assertEqual(s3["audio_source"], p53.AUDIO_SOURCE_INTERNAL_STEREO)
        self.assertEqual(s3["dropped_frames"], 0)
        self.assertEqual(s3["cp_mutation_bytes"], 0)

    def test_10_hil04_npfz100_7200mv_immune_to_bpu_11500mv_cutoff(self) -> None:
        s4 = _get_clean_room_audit()["scenarios"]["HIL-04"]
        self.assertTrue(s4["passed"])
        self.assertTrue(s4["bpu_false_cutoff_immune"])
        nom = s4["nominal_npfz100"]
        self.assertEqual(nom["battery_mv"], 7200)
        self.assertEqual(nom["bpu_cutoff_mv"], 11500)
        self.assertTrue(nom["would_trip_naive_bpu_comparator"])
        self.assertTrue(nom["bpu_false_cutoff_blocked"])
        self.assertTrue(nom["runs_normally"])
        self.assertTrue(nom["h0_h1_entry_allowed"])

    def test_11_hil04_vbus_droop_over_450mv_blocks_h0_h1_fail_closed(self) -> None:
        s4 = _get_clean_room_audit()["scenarios"]["HIL-04"]
        self.assertTrue(s4["vbus_droop_blocks_h0_h1"])
        fault = s4["vbus_droop_fault"]
        self.assertTrue(fault["vbus_droop_exceeded"])
        self.assertTrue(fault["h0_h1_entry_blocked"])
        self.assertEqual(fault["status"], "BLOCKED_BY_USBPD_VBUS_DROOP")
        self.assertFalse(fault["persistent_emmc_writes_authorized"])

        boundary_ok = p53.evaluate_npfz100_and_vbus_power(battery_mv=7200, battery_soc_pct=85, vbus_droop_mv=450)
        self.assertTrue(boundary_ok["h0_h1_entry_allowed"])
        boundary_fail = p53.evaluate_npfz100_and_vbus_power(battery_mv=7200, battery_soc_pct=85, vbus_droop_mv=451)
        self.assertTrue(boundary_fail["h0_h1_entry_blocked"])

    def test_12_hil04_low_battery_soc_or_brownout_blocks_h0_h1(self) -> None:
        low_soc = p53.evaluate_npfz100_and_vbus_power(battery_mv=7200, battery_soc_pct=70, vbus_droop_mv=100)
        self.assertTrue(low_soc["h0_h1_entry_blocked"])
        self.assertEqual(low_soc["status"], "BLOCKED_BY_H0_H1_SOC_THRESHOLD")

        brownout = p53.evaluate_npfz100_and_vbus_power(battery_mv=5900, battery_soc_pct=10, vbus_droop_mv=100)
        self.assertTrue(brownout["h0_h1_entry_blocked"])
        self.assertEqual(brownout["status"], "BLOCKED_BY_NPFZ100_BROWNOUT")

    def test_13_hud_amber_fx6_px_parity_and_gpe0_gpe1_flush(self) -> None:
        s2_hud = _get_clean_room_audit()["scenarios"]["HIL-02"]["hud"]
        self.assertTrue(s2_hud["ui_responsive"])
        self.assertTrue(s2_hud["fx6_px_amber_parity_ok"])
        self.assertTrue(s2_hud["gpe0_gpe1_parity_ok"])
        self.assertEqual(s2_hud["amber_px_hex"], "0xfff08018")
        self.assertEqual(s2_hud["thermal_badge_px_hex"], "0xfff08018")

    def test_14_hil_01_and_03_reuse_shared_dual_isa_session_cleanly(self) -> None:
        sess = p24.create_dual_ap_cp_session(force_clean_room=True)
        bus = p41.MmioWindowBus(cp_bytes=sess.cp_bytes)
        r1 = p53.run_hil_scenario("HIL-01", force_clean_room=True, session=sess, bus=bus)
        r3 = p53.run_hil_scenario("HIL-03", force_clean_room=True, session=sess, bus=bus)
        self.assertTrue(r1["passed"])
        self.assertTrue(r3["passed"])
        self.assertEqual(sess.verify_cp_immutability().cp_mutation_bytes, 0)


class TestHil05To08C2paNdWlanMedia(unittest.TestCase):
    """Verify HIL-05..HIL-08: C2PA/SPACC trap, P4 ND clamp, P12/WF-12, Dual CFexpress relay + V30 reject."""

    def test_15_hil05_c2pa_rq_lic_and_spacc_0xf7fc0000_cnflasha_trap(self) -> None:
        s5 = _get_clean_room_audit()["scenarios"]["HIL-05"]
        self.assertTrue(s5["passed"])
        self.assertEqual(s5["status"], "C2PA_AND_CALIBRATION_IMMUTABLE")
        self.assertEqual(s5["spacc_mmio_base"], "0xf7fc0000")
        self.assertTrue(s5["spacc_userland_write_trapped"])
        self.assertTrue(s5["spacc_userland_read_trapped"])
        self.assertGreaterEqual(s5["spacc_blocked_userland_ops"], 2)
        self.assertTrue(s5["all_targets_trapped"])
        self.assertTrue(s5["c2pa_rq_lic_preserved"])
        self.assertEqual(s5["calibration_mutation_bytes"], 0)
        self.assertEqual(s5["cp_mutation_bytes"], 0)
        self.assertEqual(s5["persistent_emmc_writes"], 0)

    def test_16_hil05_allows_volatile_tmpfs_overlay_while_blocking_cal_paths(self) -> None:
        tmp_ok = p53.evaluate_c2pa_and_spacc_target_trap("/tmp/fx6_overlay/stage_b.sh", operation="write")
        self.assertFalse(tmp_ok["trapped"])
        self.assertEqual(tmp_ok["status"], "ALLOWED_VOLATILE_TMPFS")

        for blocked in (
            "/dev/cnflasha2",
            "p12:/cert/RQ_LIC.DAT",
            "p18:/lens/lensfile.bin",
            "/dev/mtd0/ddrtraining.dat",
        ):
            res = p53.evaluate_c2pa_and_spacc_target_trap(blocked, operation="mount")
            self.assertTrue(res["trapped"], msg=f"Expected trap for {blocked}")

    def test_17_hil06_p4_optical_nd_commands_clamped_to_clear_zero_timeouts(self) -> None:
        s6 = _get_clean_room_audit()["scenarios"]["HIL-06"]
        self.assertTrue(s6["passed"])
        self.assertEqual(s6["status"], "P4_ND_CLAMPED_TO_CLEAR_OK")
        self.assertEqual(s6["effective_nd_state"], "ND=Clear")
        self.assertEqual(s6["effective_nd_mode_code"], 4)
        self.assertEqual(s6["effective_nd_value_pair"], [1, 1])
        self.assertEqual(s6["injected_count"], 5)
        self.assertEqual(s6["actuator_timeouts"], 0)
        self.assertTrue(s6["non_clear_rtmd_rejected"])
        self.assertTrue(s6["rtmd_0xe107_nd_clear_verified"])

    def test_18_hil07_p12_wlan_0x70d4_and_ttyama3_timeout_allowed_degraded(self) -> None:
        s7 = _get_clean_room_audit()["scenarios"]["HIL-07"]
        self.assertTrue(s7["passed"])
        self.assertEqual(s7["status"], "ALLOWED_DEGRADED")
        self.assertEqual(s7["degraded_state"], "ALLOWED_DEGRADED")
        self.assertEqual(s7["p12_wlan_vma"], "0x70d4")
        self.assertEqual(s7["p12_patched_rc"], 0)
        self.assertEqual(s7["notice_id"], "00342260")
        self.assertTrue(s7["infinite_hang_neutralized"])
        self.assertEqual(s7["ttyama3_timeout_hal_rc"], "0x0bb9")
        self.assertTrue(s7["patchram_nack_latched"])
        self.assertEqual(s7["wdt_resets"], 0)
        self.assertTrue(s7["ui_responsive"])
        self.assertTrue(s7["shooting_unaffected"])
        self.assertEqual(s7["cp_mutation_bytes"], 0)

    def test_19_hil08_dual_cfexpress_relay_auto_switch_zero_drops(self) -> None:
        s8 = _get_clean_room_audit()["scenarios"]["HIL-08"]
        self.assertTrue(s8["passed"])
        self.assertTrue(s8["relay_switched"])
        self.assertGreater(s8["relay_switch_frame_index"], 0)
        self.assertLess(s8["relay_switch_frame_index"], 10)
        self.assertGreater(s8["slot_a_frames"], 0)
        self.assertGreater(s8["slot_b_frames"], 0)
        self.assertEqual(s8["slot_a_frames"] + s8["slot_b_frames"], 10)
        self.assertEqual(s8["dropped_frames"], 0)
        self.assertTrue(s8["rtmd_all_packets_valid"])

    def test_20_hil08_v30_card_speed_class_reject_without_crash(self) -> None:
        s8 = _get_clean_room_audit()["scenarios"]["HIL-08"]
        self.assertEqual(s8["v30_reject_status"], "SPEED_CLASS_REJECT")
        self.assertIn("600MBPS", s8["v30_caution_id"])
        self.assertFalse(s8["v30_appfw_crashed"])
        self.assertEqual(s8["v30_wdt_resets"], 0)

    def test_21_unknown_scenario_id_raises_hil_harness_error(self) -> None:
        with self.assertRaises(p53.HilHarnessError):
            p53.run_hil_scenario("HIL-99", force_clean_room=True)
        with self.assertRaises(p53.HilHarnessError):
            p53.run_phase53_hil_audit(scenario_filter=("HIL-99",), force_clean_room=True)

    def test_22_scenario_filter_runs_subset_deterministically(self) -> None:
        rep = p53.run_phase53_hil_audit(scenario_filter=("HIL-02", "HIL-05"), force_clean_room=True)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["scenarios_total"], 2)
        self.assertEqual(rep["scenarios_passed"], 2)
        self.assertEqual(set(rep["scenarios"].keys()), {"HIL-02", "HIL-05"})


class TestStage6CoEmulationSuiteCliAndHygiene(unittest.TestCase):
    """Verify Stage 6 audit determinism, co-emulation suite wiring, CLI, and hygiene."""

    def test_23_phase53_audit_determinism_and_digest_verification(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p53.run_phase53_hil_audit(force_clean_room=True)
        self.assertEqual(r1, r2)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["scenarios_total"], 8)
        self.assertEqual(r1["scenarios_passed"], 8)

        copy_rep = dict(r1)
        recorded = copy_rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_24_coemulation_suite_wires_stage6_and_allows_skip(self) -> None:
        rep_with = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=True,
            )
        )
        self.assertTrue(rep_with["all_checks_passed"])
        self.assertIn("stage6_phase53_hil_fault_harness", rep_with)
        s6 = rep_with["stage6_phase53_hil_fault_harness"]
        self.assertTrue(s6["all_checks_passed"])
        self.assertEqual(s6["scenarios_total"], 8)
        self.assertEqual(s6["scenarios_passed"], 8)
        self.assertEqual(s6["cp_mutation_bytes"], 0)
        self.assertEqual(s6["calibration_mutation_bytes"], 0)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_bt_containment_matrix=False,
                include_phase41_dtb_mhlx=False,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage6_phase53_hil_fault_harness", rep_skip)

    def test_25_suite_cli_skip_phase53_and_summary_output(self) -> None:
        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc = suite.main(
                ["--clean-room", "--skip-phase41", "--skip-phase45", "--skip-phase53", "--json"]
            )
        self.assertEqual(rc, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage6_phase53_hil_fault_harness", rep_skip)

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main(["--clean-room", "--skip-phase41", "--skip-phase45", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("hil=CLEAN_ROOM_SYNTHETIC(8/8)", buf_sum.getvalue())

    def test_26_harness_cli_subprocess_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_hil_fault_harness.py"),
                "--self-test",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], p53.PHASE_53_SCHEMA)
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["scenarios_passed"], 8)
        self.assertEqual(payload["redlines"]["cp_mutation_bytes"], 0)
        self.assertEqual(payload["redlines"]["calibration_mutation_bytes"], 0)

    def test_27_harness_cli_summary_and_scenario_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p53.main(["--clean-room", "--summary", "--scenario", "HIL-01", "--scenario", "HIL-08"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 53 FX3-VM HIL Fault Harness", out)
        self.assertIn("scenarios=2/2", out)
        self.assertIn("cp_mut=0", out)
        self.assertIn("cal_mut=0", out)

    def test_28_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        mod_src = (FX3_VM_DIR / "fx3_vm_hil_fault_harness.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", mod_src)
        self.assertNotIn("os.O_WRONLY", mod_src)
        self.assertNotIn("os.O_RDWR", mod_src)
        self.assertNotIn(forbidden_port, mod_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertNotIn("pkill", mod_src)
        self.assertNotIn("killall", mod_src)
        self.assertIn("CP_MUTATION_BYTES = 0", mod_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", mod_src)
        self.assertIn("CALIBRATION_MUTATION_BYTES = 0", mod_src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", mod_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", mod_src)


if __name__ == "__main__":
    unittest.main()
