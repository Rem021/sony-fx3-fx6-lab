"""Fast dual-mode unit tests for Phase 50 — 16-Gate Master Safety Preflight Engine (`G01..G16`)."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.crsdk_mishoe_ltc_spacc_guard import (
    STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
    STATUS_BLOCKED_CRSDK_NVRAM_TAMPER,
    STATUS_BLOCKED_MULTIPORT_PIN_SHARING,
    STATUS_BLOCKED_SMART_HANDLE_COLLISION,
)
from fx3_safety.master_16gate_preflight import (
    BK4_AIRPLANE_SHADOW_REQUIRED,
    DEFAULT_REPO_ROOT,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_DONOR_SIZE,
    FX6_WLAN_RSRC_P12_ORIG_HEX,
    FX6_WLAN_RSRC_P12_PATCHED_HEX,
    G13_GATE_CODE,
    G13_GATE_ID,
    G14_GATE_CODE,
    G14_GATE_ID,
    G15_GATE_CODE,
    G15_GATE_ID,
    G16_GATE_CODE,
    G16_GATE_ID,
    MASTER_16GATE_PREFLIGHT_SCHEMA,
    MASTER_16GATE_PREFLIGHT_VERSION,
    P12_WLAN_FATAL_GUARD_VMA,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SOC_START_HEADROOM_CEILING_C,
    STATUS_BLOCKED_G13_HARNESS_OPEN_DRAIN,
    STATUS_BLOCKED_G15_C2PA_KEYSTORE,
    STATUS_BLOCKED_G15_CALIBRATION_MUTATION,
    STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB,
    STATUS_BLOCKED_G15_EXFAT_HYGIENE,
    STATUS_BLOCKED_G16_P12_WF12_GUARD,
    STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_SOC_START_HEADROOM,
    STATUS_VERIFIED_G13,
    STATUS_VERIFIED_G14,
    STATUS_VERIFIED_G15,
    STATUS_VERIFIED_G16,
    evaluate_16_master_safety_gates,
    evaluate_g13_multiport_and_mishoe_isolation,
    evaluate_g14_thermal_and_power_envelope,
    evaluate_g15_c2pa_and_calibration,
    evaluate_g16_stage_b_p12_and_wbi2_lock,
    main as module_cli_main,
    verify_c2pa_and_factory_calibration_immutability,
    verify_stage_b_p12_wf12_and_wbi2_lock,
)
from fx3_safety.thermal_pwm_and_power_guard import (
    COMPARATOR_RAW_BPU_11500MV,
    FAIL_CLOSED_TEARDOWN_TEMP_C,
    STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH,
    STATUS_BLOCKED_NPFZ100_BROWNOUT,
    STATUS_BLOCKED_THERMAL_RUNAWAY,
    STATUS_BLOCKED_USBPD_VBUS_DROOP,
)


class Master16GatePreflightTests(unittest.TestCase):
    # --- Redlines & Exports ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(MASTER_16GATE_PREFLIGHT_SCHEMA, "fx3-master-16gate-preflight-v1")
        self.assertEqual(MASTER_16GATE_PREFLIGHT_VERSION, "1.0.0")
        for sym in (
            "MASTER_16GATE_PREFLIGHT_SCHEMA",
            "G13_GATE_ID",
            "G14_GATE_ID",
            "G15_GATE_ID",
            "G16_GATE_ID",
            "evaluate_16_master_safety_gates",
            "evaluate_g13_multiport_and_mishoe_isolation",
            "evaluate_g14_thermal_and_power_envelope",
            "evaluate_g15_c2pa_and_calibration",
            "evaluate_g16_stage_b_p12_and_wbi2_lock",
            "verify_c2pa_and_factory_calibration_immutability",
            "verify_stage_b_p12_wf12_and_wbi2_lock",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    # --- Full G01..G16 Composition (Dual-Mode & Offline Dry-Run) ---

    def test_02_master_16_gates_default_repo_passes_offline_13_gates(self) -> None:
        report = evaluate_16_master_safety_gates(DEFAULT_REPO_ROOT)
        self.assertEqual(len(report.gates), 16)
        self.assertEqual(report.summary["total_gates"], 16)
        self.assertEqual(report.summary["g13_to_g16_verified"], 4)
        self.assertTrue(report.g13_to_g16_all_passed)
        self.assertTrue(report.offline_13_gates_verified)
        self.assertFalse(report.all_16_gates_verified)
        self.assertEqual(report.status, "VERIFIED_G01_G09_AND_G13_G16_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        gate_ids = [g["gate_id"] for g in report.gates]
        self.assertEqual(gate_ids[-4:], [G13_GATE_ID, G14_GATE_ID, G15_GATE_ID, G16_GATE_ID])
        gate_codes = [g.get("gate_code") for g in report.gates[-4:]]
        self.assertEqual(gate_codes, [G13_GATE_CODE, G14_GATE_CODE, G15_GATE_CODE, G16_GATE_CODE])

    def test_03_master_16_gates_clean_room_dry_run_tier0_passes_all_16(self) -> None:
        report = evaluate_16_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(report.clean_room_forced)
        self.assertTrue(report.all_16_gates_verified)
        self.assertEqual(report.summary["verified_gates"], 16)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(report.status, "VERIFIED_ALL_16_GATES_OFFLINE_DRY_RUN")
        self.assertFalse(report.persistent_emmc_writes_authorized)

    def test_04_donor_reads_use_strict_o_rdonly(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            report = evaluate_16_master_safety_gates(DEFAULT_REPO_ROOT)

        self.assertTrue(report.g13_to_g16_all_passed)
        donor_calls = [
            (p, f)
            for p, f in observed_flags
            if "libWlanResource.so" in p or "libfan.so" in p or "Backup.bin" in p
        ]
        for path, flags in donor_calls:
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

    # --- Gate G13: MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION ---

    def test_05_g13_blocks_vmc_bncm1_ltc_with_uart_boot_pin_conflict(self) -> None:
        verdict, p38, _ = evaluate_g13_multiport_and_mishoe_isolation(
            ltc_kwargs={"ltc_cable_attached": True, "uart_boot_harness_attached": True}
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.status, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
        self.assertFalse(p38.ltc_guard.valid)

    def test_06_g13_blocks_push_pull_or_pico_or_overvoltage_harness(self) -> None:
        for bad_kwargs in (
            {"open_drain": False},
            {"board": "raspberry_pi_pico"},
            {"io_voltage_v": 3.3},
        ):
            verdict, _, harness = evaluate_g13_multiport_and_mishoe_isolation(
                harness_kwargs=bad_kwargs
            )
            self.assertFalse(verdict.passed, f"Expected G13 block for {bad_kwargs}")
            self.assertEqual(verdict.status, STATUS_BLOCKED_G13_HARNESS_OPEN_DRAIN)
            self.assertFalse(harness.valid and harness.open_drain_enforced)

    def test_07_g13_blocks_p11_spoofed_xlr_h1_handle_and_passes_valid_coexistence(self) -> None:
        ok_verdict, ok_p38, ok_harness = evaluate_g13_multiport_and_mishoe_isolation()
        self.assertTrue(ok_verdict.passed)
        self.assertEqual(ok_verdict.status, STATUS_VERIFIED_G13)
        self.assertTrue(ok_p38.mishoe_guard.xlr_h1_preserved)
        self.assertTrue(ok_harness.open_drain_enforced)

        bad_verdict, bad_p38, _ = evaluate_g13_multiport_and_mishoe_isolation(
            mishoe_kwargs={"p11_smart_handle_ack_cmd": 0x88000001}
        )
        self.assertFalse(bad_verdict.passed)
        self.assertEqual(bad_verdict.status, STATUS_BLOCKED_SMART_HANDLE_COLLISION)
        self.assertFalse(bad_p38.mishoe_guard.xlr_h1_preserved)

    def test_08_g13_propagates_crsdk_and_spacc_faults(self) -> None:
        v_crsdk, _, _ = evaluate_g13_multiport_and_mishoe_isolation(
            crsdk_requests=[{"opcode": 0x9205, "property": "PRODUCT_MODEL"}]
        )
        self.assertFalse(v_crsdk.passed)
        self.assertEqual(v_crsdk.status, STATUS_BLOCKED_CRSDK_NVRAM_TAMPER)

        v_spacc, _, _ = evaluate_g13_multiport_and_mishoe_isolation(
            spacc_operations=[{"device": "/dev/nflasha3", "op": "mount", "partition_type": 5, "partition_flag": 1}]
        )
        self.assertFalse(v_spacc.passed)
        self.assertEqual(v_spacc.status, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)

    # --- Gate G14: THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE ---

    def test_09_g14_enforces_soc_below_62c_start_headroom_and_90c_teardown(self) -> None:
        v_ok, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            fan_kwargs={"cxd90057_soc_c": 61.9},
        )
        self.assertTrue(v_ok.passed)
        self.assertEqual(v_ok.status, STATUS_VERIFIED_G14)
        self.assertEqual(SOC_START_HEADROOM_CEILING_C, 62.0)

        v_hot_start, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            fan_kwargs={"cxd90057_soc_c": 62.0},
        )
        self.assertFalse(v_hot_start.passed)
        self.assertEqual(v_hot_start.status, STATUS_BLOCKED_SOC_START_HEADROOM)

        v_runaway, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            fan_kwargs={"cxd90057_soc_c": FAIL_CLOSED_TEARDOWN_TEMP_C},
        )
        self.assertFalse(v_runaway.passed)
        self.assertEqual(v_runaway.status, STATUS_BLOCKED_THERMAL_RUNAWAY)

    def test_10_g14_enforces_npfz100_80pct_7800mv_and_rejects_bpu_comparator(self) -> None:
        v_low_soc, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            power_kwargs={"raw_batt_mv": 7900, "infolithium_soc_pct": 79.0},
        )
        self.assertFalse(v_low_soc.passed)
        self.assertEqual(v_low_soc.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        v_low_mv, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            power_kwargs={"raw_batt_mv": 7750, "infolithium_soc_pct": 85.0},
        )
        self.assertFalse(v_low_mv.passed)
        self.assertEqual(v_low_mv.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        v_bpu_cmp, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            power_kwargs={"comparator_mode": COMPARATOR_RAW_BPU_11500MV},
        )
        self.assertFalse(v_bpu_cmp.passed)
        self.assertEqual(v_bpu_cmp.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

    def test_11_g14_enforces_usbpd_9v3a_vbus_droop_limit(self) -> None:
        v_ok, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            power_kwargs={"usbpd_measured_vbus_mv": 8550},
        )
        self.assertTrue(v_ok.passed)

        v_droop, _ = evaluate_g14_thermal_and_power_envelope(
            force_clean_room=True,
            power_kwargs={"usbpd_measured_vbus_mv": 8549},
        )
        self.assertFalse(v_droop.passed)
        self.assertEqual(v_droop.status, STATUS_BLOCKED_USBPD_VBUS_DROOP)

    # --- Gate G15: C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY ---

    def test_12_g15_passes_volatile_tmpfs_ram_overlay_only(self) -> None:
        verdict, res = evaluate_g15_c2pa_and_calibration(
            planned_mounts=["mount --bind /tmp/fx6_overlay/appFw.so /usr/lib/appFw.so"],
            planned_writes=["/tmp/mod_arm_once", "/run/fx6_stage_b.json"],
            c2pa_calibration_script_text="# Stage-B RAM overlay\ntouch /tmp/mod_arm_once\n",
            calibration_mutation_bytes=0,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.status, STATUS_VERIFIED_G15)
        self.assertTrue(res.cnflasha_protected)
        self.assertTrue(res.rpmb_protected)
        self.assertTrue(res.trustzone_c2pa_keystore_protected)
        self.assertTrue(res.factory_sensor_ibis_protected)
        self.assertTrue(res.exfat_media_hygiene_ok)
        self.assertTrue(res.volatile_tmpfs_ram_overlay_only)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_13_g15_blocks_cnflasha_and_rpmb_mounts_or_writes(self) -> None:
        res_cn = verify_c2pa_and_factory_calibration_immutability(
            planned_mounts=["/dev/cnflasha3 /mnt/usr"],
        )
        self.assertFalse(res_cn.valid)
        self.assertFalse(res_cn.cnflasha_protected)
        self.assertEqual(res_cn.status, STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB)

        res_rpmb = verify_c2pa_and_factory_calibration_immutability(
            planned_writes=["/dev/mmcblk0rpmb"],
        )
        self.assertFalse(res_rpmb.valid)
        self.assertFalse(res_rpmb.rpmb_protected)
        self.assertEqual(res_rpmb.status, STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB)

    def test_14_g15_blocks_c2pa_rq_lic_sigcert_p12_and_trustzone_targets(self) -> None:
        for bad_target in (
            "/media/card/RQ_LIC.DAT",
            "/tmp/sigcert.p12",
            "p12:/cert/c2pa_root.der",
            "/dev/tee0",
            "/dev/nflasha12",
        ):
            res = verify_c2pa_and_factory_calibration_immutability(planned_writes=[bad_target])
            self.assertFalse(res.valid, f"Expected G15 C2PA block for {bad_target}")
            self.assertFalse(res.trustzone_c2pa_keystore_protected)
            self.assertEqual(res.status, STATUS_BLOCKED_G15_C2PA_KEYSTORE)

        res_flag = verify_c2pa_and_factory_calibration_immutability(
            c2pa_keystore_writes_attempted=True
        )
        self.assertFalse(res_flag.valid)
        self.assertEqual(res_flag.status, STATUS_BLOCKED_G15_C2PA_KEYSTORE)

    def test_15_g15_blocks_factory_sensor_ibis_lens_calibration_targets_and_adjstctl(self) -> None:
        for bad_path in (
            "/setting/psd.bin",
            "/setting/defdet.bin",
            "/setting/Backup.bin",
            "p6:/tmp/jiritsu/cal.dat",
            "p18:/lens/lensfile.bin",
            "/dev/mtd0:ddrtraining.dat",
        ):
            res = verify_c2pa_and_factory_calibration_immutability(planned_writes=[bad_path])
            self.assertFalse(res.valid, f"Expected G15 calibration block for {bad_path}")
            self.assertFalse(res.factory_sensor_ibis_protected)
            self.assertEqual(res.status, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)

        res_script = verify_c2pa_and_factory_calibration_immutability(
            c2pa_calibration_script_text="adjstctl.elf A_PIXEL_DEFECT_WRITE\n"
        )
        self.assertFalse(res_script.valid)
        self.assertEqual(res_script.status, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)

    def test_16_g15_blocks_nonzero_calibration_mutation_and_write_override(self) -> None:
        res_mut = verify_c2pa_and_factory_calibration_immutability(
            calibration_mutation_bytes=64
        )
        self.assertFalse(res_mut.valid)
        self.assertEqual(res_mut.status, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)

        res_ovr = verify_c2pa_and_factory_calibration_immutability(
            allow_c2pa_or_calibration_write=True
        )
        self.assertFalse(res_ovr.valid)
        self.assertEqual(res_ovr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_17_g15_blocks_exfat_volume_dirty_bit_and_unfinalized_rsv(self) -> None:
        res_dirty = verify_c2pa_and_factory_calibration_immutability(
            exfat_dirty_bit_present=True
        )
        self.assertFalse(res_dirty.valid)
        self.assertFalse(res_dirty.exfat_media_hygiene_ok)
        self.assertEqual(res_dirty.status, STATUS_BLOCKED_G15_EXFAT_HYGIENE)

        res_rsv = verify_c2pa_and_factory_calibration_immutability(
            exfat_unfinalized_rsv_present=True
        )
        self.assertFalse(res_rsv.valid)
        self.assertFalse(res_rsv.exfat_media_hygiene_ok)
        self.assertEqual(res_rsv.status, STATUS_BLOCKED_G15_EXFAT_HYGIENE)

    # --- Gate G16: STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK ---

    def test_18_g16_verifies_p12_0x70d4_and_bk4_airplane_shadow_dual_mode(self) -> None:
        v_cur, r_cur = evaluate_g16_stage_b_p12_and_wbi2_lock()
        self.assertTrue(v_cur.passed)
        self.assertEqual(v_cur.status, STATUS_VERIFIED_G16)
        self.assertEqual(r_cur.p12_vma_hex, hex(P12_WLAN_FATAL_GUARD_VMA))
        self.assertEqual(r_cur.p12_patched_rc, 0)
        self.assertTrue(r_cur.bk4_airplane_shadow_verified)
        self.assertTrue(r_cur.wf12_bootloop_immune)
        self.assertEqual(r_cur.details["libwlan_resource_sha256"], FX6_WLAN_RSRC_DONOR_SHA256)
        self.assertEqual(r_cur.details["p12_orig_hex"], FX6_WLAN_RSRC_P12_ORIG_HEX)
        self.assertEqual(r_cur.details["p12_patched_hex"], FX6_WLAN_RSRC_P12_PATCHED_HEX)

        v_cr, r_cr = evaluate_g16_stage_b_p12_and_wbi2_lock(force_clean_room=True)
        self.assertTrue(v_cr.passed)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(r_cr.details["donor_o_rdonly_checked"])

    def test_19_g16_blocks_wrong_p12_vma_nonzero_rc_or_disabled_guard(self) -> None:
        for bad_kwargs in (
            {"p12_vma": 0x70D8},
            {"p12_patched_rc": 1},
            {"p12_guard_enabled": False},
            {"wf12_bootloop_immune": False},
        ):
            res = verify_stage_b_p12_wf12_and_wbi2_lock(force_clean_room=True, **bad_kwargs)
            self.assertFalse(res.valid, f"Expected G16 P12 block for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G16_P12_WF12_GUARD)

    def test_20_g16_blocks_missing_or_nonzero_bk4_airplane_shadow(self) -> None:
        for key in BK4_AIRPLANE_SHADOW_REQUIRED:
            bad_shadow = dict(BK4_AIRPLANE_SHADOW_REQUIRED)
            bad_shadow[key] = 1
            res = verify_stage_b_p12_wf12_and_wbi2_lock(
                force_clean_room=True,
                bk4_airplane_shadow=bad_shadow,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.bk4_airplane_shadow_verified)
            self.assertEqual(res.status, STATUS_BLOCKED_G16_P12_WF12_GUARD)

    def test_21_g16_blocks_wbi2_cp_nvram_mutation_and_emmc_write_request(self) -> None:
        for bad_mut in (
            {"wbi_mutation_bytes": 16},
            {"cp_mutation_bytes": 32},
            {"nvram_persistent_writes": 1},
        ):
            res = verify_stage_b_p12_wf12_and_wbi2_lock(force_clean_room=True, **bad_mut)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION)

        res_emmc = verify_stage_b_p12_wf12_and_wbi2_lock(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_22_master_16_gates_surfaces_first_g13_to_g16_failure_cleanly(self) -> None:
        rep_g15 = evaluate_16_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            planned_writes=["p18:/lens/lensfile.bin"],
        )
        self.assertFalse(rep_g15.g13_to_g16_all_passed)
        self.assertFalse(rep_g15.all_16_gates_verified)
        self.assertEqual(rep_g15.status, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)

        rep_g16 = evaluate_16_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
            wbi_mutation_bytes=4096,
        )
        self.assertFalse(rep_g16.g13_to_g16_all_passed)
        self.assertEqual(rep_g16.status, STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION)

    def test_23_clean_room_env_var_overrides_donor_lookup(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_16_master_safety_gates(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_13_gates_verified)
        self.assertEqual(FX6_WLAN_RSRC_DONOR_SIZE, 56464)

    # --- CLI Entrypoint Coverage (`python3 -m fx3_safety verify-16-gates`) ---

    def test_24_package_cli_verify_16_gates_json_and_clean_room_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-16-gates", "--clean-room", "--dry-run-tier0", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], MASTER_16GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(payload["summary"]["verified_gates"], 16)
        self.assertTrue(payload["all_16_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_25_package_cli_verify_16_gates_summary_text(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-16-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=13/16", out)
        self.assertIn("g13_to_g16_all_passed=True", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_26_module_cli_json_and_missing_repo_failure_exit_code(self) -> None:
        buf_ok = io.StringIO()
        with contextlib.redirect_stdout(buf_ok):
            rc_ok = module_cli_main(["--clean-room", "--dry-run-tier0", "--json"])
        self.assertEqual(rc_ok, 0)
        self.assertTrue(json.loads(buf_ok.getvalue())["all_16_gates_verified"])

        buf_fail = io.StringIO()
        with contextlib.redirect_stdout(buf_fail):
            rc_fail = module_cli_main(["--repo-root", "/tmp/nonexistent-fx3-lab-root-phase50", "--clean-room"])
        self.assertEqual(rc_fail, 1)
        self.assertIn("BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING", buf_fail.getvalue())


if __name__ == "__main__":
    unittest.main()
