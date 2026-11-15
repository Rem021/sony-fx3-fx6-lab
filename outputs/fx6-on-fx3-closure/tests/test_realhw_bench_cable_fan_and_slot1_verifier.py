"""Dual-mode unit tests (>= 48 cases) for Phase 204 (`preflight-bench-cable-fan-slot1`):
Real-Hardware Operator Pre-Bench Power/Cable (`DC-C1` / `NP-FZ100` / `VMC-BNCM1`),
4-Mode Fan Thermal (`Always Off` Block) & Slot-1 `CAMSET`/`.cube` Vault Readiness Verifier.

Runs deterministically in both `LOCAL_DONOR_O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes with zero `.pyc` emission, zero persistent mutations, and a `< 6.0s` wall-clock ceiling.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx6-on-fx3-closure",
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as cli_main  # noqa: E402
from fx6_closure.realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS,
    B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT,
    B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH,
    B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE,
    B1_ERR_FX3_USB_STREAMING_UVC_UNSUPPORTED,
    B1_ERR_HDMI_TC_OUT_FORBIDDEN_IN_SQ_MODE,
    B1_ERR_MICRO_USB_POWER_FORBIDDEN,
    B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION,
    B1_ERR_POWER_SOURCE_INVALID,
    B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN,
    B1_ERR_VMC_BNCM1_TC_IN_EXT_LK_PREREQ_FAILED,
    B1_ERR_VMC_BNCM1_XLR_H1_HANDLE_PORT_FORBIDDEN,
    B2_ERR_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB,
    B2_ERR_AUTO_POWER_OFF_TEMP_ENUM_INVALID,
    B2_ERR_BIG6_LOWER_LEFT_MODE_INVALID,
    B2_ERR_BIG6_PREREQ_OR_SHUTTER_ANGLE_INVALID,
    B2_ERR_BODY_THERMAL_OVERLIMIT,
    B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2,
    B2_ERR_OFF_IN_REC_STANDBY_MAX_PWM_VIOLATION,
    B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO,
    B2_ERR_PREBACKUP_REQUIRES_FAN_SWITCHED_TO_AUTO,
    B2_ERR_UNKNOWN_FAN_CONTROL_MODE,
    B3_ERR_CAMSET_DISABLED_IN_MR_RECALL_MODE,
    B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING,
    B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY,
    B3_ERR_CROSS_MODEL_CAMSET_DAT_CONTAMINATION,
    B3_ERR_CUBE_LUT_SPEC_OR_16_SLOT_CEILING,
    B3_ERR_H0_H3_16_SURFACE_PARITY_DRIFT,
    B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION,
    B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH,
    B3_ERR_STAGEB_CAMSET_OVERLAY_SANDBOX_VIOLATION,
    B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE,
    B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    B3_ERR_UNSUPPORTED_MEDIA_TYPE,
    BENCH_PREFLIGHT_CHECK_GROUP_IDS,
    CFEXPRESS_A_CANONICAL_CAMSET_DIR,
    CFEXPRESS_A_CANONICAL_LUT_DIR,
    CHECK_GROUP_B1_ID,
    CHECK_GROUP_B2_ID,
    CHECK_GROUP_B3_ID,
    DONOR_INSPECTION_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FAN_MODE_ALWAYS_OFF,
    FAN_MODE_AUTO,
    FAN_MODE_MINIMUM,
    FAN_MODE_OFF_IN_REC,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SDXC,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_204_SCHEMA,
    PHASE_204_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    POWER_MODE_DC_C1_COUPLER,
    POWER_MODE_USB_PD_BODY,
    RAW_FIRMWARE_BYTES_LEAKED,
    SD_PHYSICAL_MEDIA_WRITTEN,
    SDXC_CANONICAL_CAMSET_DIR,
    SDXC_CANONICAL_LUT_DIR,
    SPI_NOR_WRITE_AUTHORIZED,
    VMC_DIRECTION_TC_IN,
    VMC_PORT_BODY_MULTI_MICRO_USB,
    VMC_PORT_XLR_H1_HANDLE_MICRO_USB,
    _canonical_sha256_dict,
    build_simulated_phase204_tier0_receipts,
    evaluate_check_group_1_power_cable_harness,
    evaluate_check_group_2_fan_thermal_and_big6,
    evaluate_check_group_3_slot1_lut_camset_vault,
    inspect_phase204_donors_bounded,
    model_fx3_702_fan_pwm_profile,
    render_phase204_markdown,
    run_bench_cable_fan_and_slot1_preflight,
    verify_phase204_report,
)


class TestPhase204BenchCableFanAndSlot1Verifier(unittest.TestCase):
    """Comprehensive dual-mode test suite (>= 48 tests) for Phase 204."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        if elapsed >= 6.0:
            raise AssertionError(
                f"Phase 204 test suite exceeded 6.0s wall-clock ceiling: {elapsed:.3f}s"
            )

    # ------------------------------------------------------------------
    # Exports, Hard-Locked Safety Constants & Bounded O_RDONLY Donors
    # ------------------------------------------------------------------

    def test_01_package_exports_and_hard_safety_locks(self) -> None:
        self.assertEqual(fx6_closure.PHASE_204_SCHEMA, PHASE_204_SCHEMA)
        self.assertEqual(fx6_closure.PHASE_204_VERSION, PHASE_204_VERSION)
        self.assertEqual(fx6_closure.PHASE204_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(
            fx6_closure.run_bench_cable_fan_and_slot1_preflight,
            run_bench_cable_fan_and_slot1_preflight,
        )
        self.assertIs(fx6_closure.verify_phase204_report, verify_phase204_report)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SD_PHYSICAL_MEDIA_WRITTEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(len(BENCH_PREFLIGHT_CHECK_GROUP_IDS), 3)

    def test_02_donor_inspection_bounded_under_150ms(self) -> None:
        res = inspect_phase204_donors_bounded()
        self.assertTrue(res.passed, msg=res.errors)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.inspected_artifacts), 7)

    def test_03_donor_inspection_clean_room_forced_and_env(self) -> None:
        res_flag = inspect_phase204_donors_bounded(force_clean_room=True)
        self.assertTrue(res_flag.passed)
        self.assertEqual(res_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res_env = inspect_phase204_donors_bounded()
            self.assertTrue(res_env.passed)
            self.assertEqual(res_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_inspection_missing_local_dir_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bogus = Path(td) / "missing_donors"
            res = inspect_phase204_donors_bounded(
                fx6_lib_dir=bogus, fx3_modules_dir=bogus, force_clean_room=False
            )
            self.assertFalse(res.passed)
            self.assertGreater(len(res.errors), 0)

    # ------------------------------------------------------------------
    # Check Group 1: Power/Cable (`NP-FZ100` / `DC-C1` / `VMC-BNCM1` / No-UVC)
    # ------------------------------------------------------------------

    def test_05_b1_nominal_body_usb_pd_with_np_fz100_ge_51pct(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_inserted=True,
            np_fz100_soc_pct=88.0,
            np_fz100_voltage_v=8.00,
        )
        self.assertTrue(r.passed, msg=r.errors)
        self.assertEqual(r.check_group_id, CHECK_GROUP_B1_ID)
        self.assertEqual(r.physical_usb_packets_emitted, 0)

    def test_06_b1_body_usb_pd_exact_51pct_boundary_passes(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_inserted=True,
            np_fz100_soc_pct=51.0,
            np_fz100_voltage_v=7.20,
        )
        self.assertTrue(r.passed, msg=r.errors)

    def test_07_b1_rejects_body_usb_pd_without_np_fz100_inserted(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_inserted=False,
            np_fz100_soc_pct=95.0,
        )
        self.assertFalse(r.passed)
        self.assertIn(B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT, r.error_codes)

    def test_08_b1_rejects_body_usb_pd_under_51pct_soc(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_inserted=True,
            np_fz100_soc_pct=50.9,
        )
        self.assertFalse(r.passed)
        self.assertIn(B1_ERR_BODY_USB_PD_REQUIRES_NP_FZ100_GE_51PCT, r.error_codes)

    def test_09_b1_rejects_np_fz100_undervoltage_and_dummy_overvoltage(self) -> None:
        low = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_voltage_v=7.10,
        )
        high = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_USB_PD_BODY,
            np_fz100_voltage_v=14.8,
        )
        self.assertFalse(low.passed)
        self.assertFalse(high.passed)
        self.assertIn(B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS, low.error_codes)
        self.assertIn(B1_ERR_BATTERY_VOLTAGE_OUT_OF_SAFE_BOUNDS, high.error_codes)

    def test_10_b1_nominal_dc_c1_65w_5a_emarked_passes(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_DC_C1_COUPLER,
            np_fz100_inserted=False,
            np_fz100_soc_pct=0.0,
            dc_c1_pd_watts=65.0,
            dc_c1_cable_amps=5.0,
            dc_c1_emarked_5a=True,
        )
        self.assertTrue(r.passed, msg=r.errors)
        self.assertTrue(r.dc_c1_65w_5a_contract_ok)

    def test_11_b1_rejects_dc_c1_under_65w_adapter(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_DC_C1_COUPLER,
            dc_c1_pd_watts=45.0,
            dc_c1_cable_amps=5.0,
            dc_c1_emarked_5a=True,
        )
        self.assertFalse(r.passed)
        self.assertIn(B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE, r.error_codes)

    def test_12_b1_rejects_dc_c1_3a_or_non_emarked_cable(self) -> None:
        r_3a = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_DC_C1_COUPLER,
            dc_c1_pd_watts=100.0,
            dc_c1_cable_amps=3.0,
            dc_c1_emarked_5a=True,
        )
        r_no_em = evaluate_check_group_1_power_cable_harness(
            power_source=POWER_MODE_DC_C1_COUPLER,
            dc_c1_pd_watts=100.0,
            dc_c1_cable_amps=5.0,
            dc_c1_emarked_5a=False,
        )
        self.assertFalse(r_3a.passed)
        self.assertFalse(r_no_em.passed)
        self.assertIn(B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE, r_3a.error_codes)
        self.assertIn(B1_ERR_DC_C1_UNDER_65W_OR_NON_5A_EMARKED_CABLE, r_no_em.error_codes)

    def test_13_b1_rejects_micro_usb_and_unknown_power_sources(self) -> None:
        r_micro = evaluate_check_group_1_power_cable_harness(power_source="MICRO_USB")
        r_bad = evaluate_check_group_1_power_cable_harness(power_source="SOLAR_12V")
        self.assertFalse(r_micro.passed)
        self.assertFalse(r_bad.passed)
        self.assertIn(B1_ERR_MICRO_USB_POWER_FORBIDDEN, r_micro.error_codes)
        self.assertIn(B1_ERR_POWER_SOURCE_INVALID, r_bad.error_codes)

    def test_14_b1_rejects_usb_streaming_uvc_on_ilme_fx3(self) -> None:
        r1 = evaluate_check_group_1_power_cable_harness(expect_usb_streaming_uvc=True)
        r2 = evaluate_check_group_1_power_cable_harness(usb_connection_mode="[USB Streaming]")
        r3 = evaluate_check_group_1_power_cable_harness(streaming_4k_transport="UVC")
        for res in (r1, r2, r3):
            self.assertFalse(res.passed)
            self.assertIn(B1_ERR_FX3_USB_STREAMING_UVC_UNSUPPORTED, res.error_codes)

    def test_15_b1_accepts_rtmps_srt_and_hdmi_4k_transports(self) -> None:
        for tr in ("RTMPS", "SRT", "HDMI_TYPE_A"):
            r = evaluate_check_group_1_power_cable_harness(streaming_4k_transport=tr)
            self.assertTrue(r.passed, msg=f"{tr}: {r.errors}")

    def test_16_b1_rejects_wrong_model_id_or_old_firmware(self) -> None:
        r_mod = evaluate_check_group_1_power_cable_harness(body_model_id=0x91020080)
        r_fw = evaluate_check_group_1_power_cable_harness(body_fw="2.00")
        self.assertFalse(r_mod.passed)
        self.assertFalse(r_fw.passed)
        self.assertIn(B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH, r_mod.error_codes)
        self.assertIn(B1_ERR_CAMERA_MODEL_OR_FW_MISMATCH, r_fw.error_codes)

    def test_17_b1_nominal_vmc_bncm1_on_body_multi_usb_tc_in(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            vmc_bncm1_attached=True,
            vmc_bncm1_port=VMC_PORT_BODY_MULTI_MICRO_USB,
            vmc_bncm1_direction=VMC_DIRECTION_TC_IN,
            shoot_mode="MOVIE",
            tc_make_mode="PRESET",
            tc_run_mode="FREE_RUN",
            uart_rx_1v8_attached=False,
        )
        self.assertTrue(r.passed, msg=r.errors)
        self.assertEqual(r.vmc_bncm1_part_number, "A-5051-506-A")

    def test_18_b1_rejects_vmc_bncm1_on_xlr_h1_handle_micro_usb(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            vmc_bncm1_attached=True,
            vmc_bncm1_port=VMC_PORT_XLR_H1_HANDLE_MICRO_USB,
            vmc_bncm1_direction=VMC_DIRECTION_TC_IN,
            uart_rx_1v8_attached=False,
        )
        self.assertFalse(r.passed)
        self.assertIn(B1_ERR_VMC_BNCM1_XLR_H1_HANDLE_PORT_FORBIDDEN, r.error_codes)

    def test_19_b1_rejects_vmc_bncm1_reverse_bnc_tc_out(self) -> None:
        r = evaluate_check_group_1_power_cable_harness(
            vmc_bncm1_attached=True,
            vmc_bncm1_port=VMC_PORT_BODY_MULTI_MICRO_USB,
            vmc_bncm1_direction="TC_OUT",
            uart_rx_1v8_attached=False,
        )
        self.assertFalse(r.passed)
        self.assertIn(B1_ERR_VMC_BNCM1_REVERSE_BNC_TC_OUT_FORBIDDEN, r.error_codes)

    def test_20_b1_rejects_vmc_bncm1_ext_lk_prereq_violation_and_sq_hdmi_tcout(self) -> None:
        r_tc = evaluate_check_group_1_power_cable_harness(
            vmc_bncm1_attached=True,
            vmc_bncm1_port=VMC_PORT_BODY_MULTI_MICRO_USB,
            vmc_bncm1_direction=VMC_DIRECTION_TC_IN,
            tc_run_mode="REC_RUN",
            uart_rx_1v8_attached=False,
        )
        r_sq = evaluate_check_group_1_power_cable_harness(
            shoot_mode="S&Q",
            hdmi_tc_out_enabled=True,
        )
        self.assertFalse(r_tc.passed)
        self.assertIn(B1_ERR_VMC_BNCM1_TC_IN_EXT_LK_PREREQ_FAILED, r_tc.error_codes)
        self.assertFalse(r_sq.passed)
        self.assertIn(B1_ERR_HDMI_TC_OUT_FORBIDDEN_IN_SQ_MODE, r_sq.error_codes)

    def test_21_b1_rejects_multiusb_pin_8_9_10_uart_contention_and_3v3_uart(self) -> None:
        r_cont = evaluate_check_group_1_power_cable_harness(
            vmc_bncm1_attached=True,
            vmc_bncm1_port=VMC_PORT_BODY_MULTI_MICRO_USB,
            vmc_bncm1_direction=VMC_DIRECTION_TC_IN,
            uart_rx_1v8_attached=True,
        )
        r_3v3 = evaluate_check_group_1_power_cable_harness(
            uart_rx_1v8_attached=True,
            uart_logic_voltage_v=3.3,
        )
        self.assertFalse(r_cont.passed)
        self.assertFalse(r_3v3.passed)
        self.assertIn(B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION, r_cont.error_codes)
        self.assertIn(B1_ERR_MULTIUSB_PIN_8_9_10_UART_CONTENTION, r_3v3.error_codes)

    # ------------------------------------------------------------------
    # Check Group 2: 4-Mode `[Fan Control]` Thermal & `BIG6` Zero e-ND
    # ------------------------------------------------------------------

    def test_22_b2_all_4_valid_fx3_fan_modes_recognized_outside_prebackup(self) -> None:
        for mode in ("Auto", "Minimum", "Off in Rec", "Always Off"):
            r = evaluate_check_group_2_fan_thermal_and_big6(
                fan_mode=mode,
                pre_p3_75mib_backup_or_stageb_rehearsal=False,
            )
            self.assertTrue(r.passed, msg=f"{mode}: {r.errors}")
            self.assertTrue(r.valid_fx3_4mode_fan)

    def test_23_b2_rejects_bogus_auto1_and_auto2_fan_modes(self) -> None:
        for bogus in ("Auto1", "Auto2", "Auto 1", "Auto_2"):
            r = evaluate_check_group_2_fan_thermal_and_big6(fan_mode=bogus)
            self.assertFalse(r.passed)
            self.assertFalse(r.bogus_auto1_auto2_rejected)
            self.assertIn(B2_ERR_BOGUS_NON_FX3_FAN_MODE_AUTO1_AUTO2, r.error_codes)

    def test_24_b2_rejects_unknown_fan_mode(self) -> None:
        r = evaluate_check_group_2_fan_thermal_and_big6(fan_mode="TurboMax")
        self.assertFalse(r.passed)
        self.assertIn(B2_ERR_UNKNOWN_FAN_CONTROL_MODE, r.error_codes)

    def test_25_b2_blocks_75mib_p3_backup_and_stageb_when_always_off(self) -> None:
        r = evaluate_check_group_2_fan_thermal_and_big6(
            fan_mode="Always Off",
            pre_p3_75mib_backup_or_stageb_rehearsal=True,
        )
        self.assertFalse(r.passed)
        self.assertTrue(r.always_off_prebackup_blocked)
        self.assertIn(B2_ERR_ALWAYS_OFF_BLOCKS_75MIB_P3_BACKUP_AND_STAGEB, r.error_codes)

    def test_26_b2_requires_switch_to_auto_before_prebackup_when_minimum_or_off_in_rec(self) -> None:
        for mode in ("Minimum", "Off in Rec"):
            r = evaluate_check_group_2_fan_thermal_and_big6(
                fan_mode=mode,
                pre_p3_75mib_backup_or_stageb_rehearsal=True,
                require_fan_auto_for_prebackup=True,
            )
            self.assertFalse(r.passed)
            self.assertIn(B2_ERR_PREBACKUP_REQUIRES_FAN_SWITCHED_TO_AUTO, r.error_codes)

    def test_27_b2_validates_auto_power_off_temp_standard_and_high(self) -> None:
        for apo in ("Standard", "High"):
            r = evaluate_check_group_2_fan_thermal_and_big6(auto_power_off_temp=apo)
            self.assertTrue(r.passed, msg=r.errors)
        r_bad = evaluate_check_group_2_fan_thermal_and_big6(auto_power_off_temp="Unlimited")
        self.assertFalse(r_bad.passed)
        self.assertIn(B2_ERR_AUTO_POWER_OFF_TEMP_ENUM_INVALID, r_bad.error_codes)

    def test_28_b2_rejects_body_start_temperature_at_or_above_45c(self) -> None:
        r = evaluate_check_group_2_fan_thermal_and_big6(body_temp_c=45.0)
        self.assertFalse(r.passed)
        self.assertIn(B2_ERR_BODY_THERMAL_OVERLIMIT, r.error_codes)

    def test_29_b2_off_in_rec_pwm_model_standby_100pct_rec_0pct_emergency_100pct(self) -> None:
        self.assertEqual(
            model_fx3_702_fan_pwm_profile(FAN_MODE_OFF_IN_REC, is_recording=False, body_temp_c=28.0),
            100.0,
        )
        self.assertEqual(
            model_fx3_702_fan_pwm_profile(FAN_MODE_OFF_IN_REC, is_recording=True, body_temp_c=52.0),
            0.0,
        )
        self.assertEqual(
            model_fx3_702_fan_pwm_profile(FAN_MODE_OFF_IN_REC, is_recording=True, body_temp_c=78.0),
            100.0,
        )
        self.assertEqual(
            model_fx3_702_fan_pwm_profile(FAN_MODE_ALWAYS_OFF, is_recording=False, body_temp_c=60.0),
            0.0,
        )
        self.assertGreater(
            model_fx3_702_fan_pwm_profile(FAN_MODE_AUTO, is_recording=True, body_temp_c=70.0),
            model_fx3_702_fan_pwm_profile(FAN_MODE_MINIMUM, is_recording=True, body_temp_c=40.0),
        )

    def test_30_b2_rejects_violated_off_in_rec_standby_pwm_telemetry(self) -> None:
        r = evaluate_check_group_2_fan_thermal_and_big6(
            observed_off_in_rec_standby_pwm_pct=45.0
        )
        self.assertFalse(r.passed)
        self.assertIn(B2_ERR_OFF_IN_REC_STANDBY_MAX_PWM_VIOLATION, r.error_codes)

    def test_31_b2_big6_lower_left_aperture_and_software_nd_filter_zero_end_tx(self) -> None:
        r_ap = evaluate_check_group_2_fan_thermal_and_big6(big6_home_lower_left="Aperture")
        r_nd = evaluate_check_group_2_fan_thermal_and_big6(big6_home_lower_left="ND Filter")
        self.assertTrue(r_ap.passed)
        self.assertFalse(r_ap.big6_lower_left_software_only_nd)
        self.assertTrue(r_nd.passed)
        self.assertTrue(r_nd.big6_lower_left_software_only_nd)
        self.assertFalse(r_nd.has_physical_internal_end_hardware)
        self.assertEqual(r_nd.e_nd_actuator_tx_count, 0)

    def test_32_b2_rejects_nonzero_e_nd_actuator_tx_or_motor_drive(self) -> None:
        r_tx = evaluate_check_group_2_fan_thermal_and_big6(e_nd_actuator_tx_count=1)
        r_drv = evaluate_check_group_2_fan_thermal_and_big6(cp_end_motor_drive_attempted=True)
        self.assertFalse(r_tx.passed)
        self.assertFalse(r_drv.passed)
        self.assertIn(B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO, r_tx.error_codes)
        self.assertIn(B2_ERR_PHYSICAL_E_ND_ACTUATOR_TX_NONZERO, r_drv.error_codes)

    def test_33_b2_validates_shutter_angle_bounds_and_independent_slots(self) -> None:
        r_slow_ok = evaluate_check_group_2_fan_thermal_and_big6(
            rec_fps=23.98, shutter_angle_deg=720.0
        )
        self.assertTrue(r_slow_ok.passed, msg=r_slow_ok.errors)
        r_120p_bad = evaluate_check_group_2_fan_thermal_and_big6(
            rec_fps=119.88, shutter_angle_deg=720.0
        )
        r_slot_collision = evaluate_check_group_2_fan_thermal_and_big6(
            shutter_speed_slot_key="0x01120024", shutter_angle_slot_key="0x01120024"
        )
        r_ll_bad = evaluate_check_group_2_fan_thermal_and_big6(big6_home_lower_left="Gain_dB")
        self.assertFalse(r_120p_bad.passed)
        self.assertIn(B2_ERR_BIG6_PREREQ_OR_SHUTTER_ANGLE_INVALID, r_120p_bad.error_codes)
        self.assertFalse(r_slot_collision.passed)
        self.assertFalse(r_ll_bad.passed)
        self.assertIn(B2_ERR_BIG6_LOWER_LEFT_MODE_INVALID, r_ll_bad.error_codes)

    # ------------------------------------------------------------------
    # Check Group 3: Slot-1 Dual-Media `.cube` LUT & `CAMSET` Vault
    # ------------------------------------------------------------------

    def _sim_kwargs(self) -> dict:
        sim = build_simulated_phase204_tier0_receipts()
        return {
            "receipt_a_bytes": sim["receipt_a_bytes"],
            "receipt_b_bytes": sim["receipt_b_bytes"],
            "st_dev_a_override": sim["st_dev_a"],
            "st_dev_b_override": sim["st_dev_b"],
            "body_serial": sim["body_serial"],
            "emmc_cid": sim["emmc_cid"],
            "h0_baselines_a": sim["h0_baselines_a"],
            "h0_baselines_b": sim["h0_baselines_b"],
        }

    def test_34_b3_sdxc_canonical_lut_and_camset_paths_pass(self) -> None:
        r = evaluate_check_group_3_slot1_lut_camset_vault(
            slot1_media_type=MEDIA_TYPE_SDXC,
            lut_dir_path=SDXC_CANONICAL_LUT_DIR,
            camset_dir_path=SDXC_CANONICAL_CAMSET_DIR,
            **self._sim_kwargs(),
        )
        self.assertTrue(r.passed, msg=r.errors)
        self.assertEqual(r.check_group_id, CHECK_GROUP_B3_ID)
        self.assertTrue(r.dual_media_path_matched)

    def test_35_b3_cfexpress_a_canonical_lut_and_camset_paths_omit_private(self) -> None:
        r = evaluate_check_group_3_slot1_lut_camset_vault(
            slot1_media_type=MEDIA_TYPE_CFEXPRESS_A,
            lut_dir_path=CFEXPRESS_A_CANONICAL_LUT_DIR,
            camset_dir_path=CFEXPRESS_A_CANONICAL_CAMSET_DIR,
            **self._sim_kwargs(),
        )
        self.assertTrue(r.passed, msg=r.errors)
        self.assertEqual(r.expected_lut_dir, "/Sony/PRO/LUT/")
        self.assertEqual(r.expected_camset_dir, "/SONY/SETTING/FX3/CAMSET/")

    def test_36_b3_rejects_swapped_sdxc_vs_cfexpress_a_paths(self) -> None:
        r_cfe_with_priv = evaluate_check_group_3_slot1_lut_camset_vault(
            slot1_media_type=MEDIA_TYPE_CFEXPRESS_A,
            lut_dir_path=SDXC_CANONICAL_LUT_DIR,
            camset_dir_path=SDXC_CANONICAL_CAMSET_DIR,
            **self._sim_kwargs(),
        )
        r_sd_no_priv = evaluate_check_group_3_slot1_lut_camset_vault(
            slot1_media_type=MEDIA_TYPE_SDXC,
            lut_dir_path=CFEXPRESS_A_CANONICAL_LUT_DIR,
            camset_dir_path=CFEXPRESS_A_CANONICAL_CAMSET_DIR,
            **self._sim_kwargs(),
        )
        self.assertFalse(r_cfe_with_priv.passed)
        self.assertFalse(r_sd_no_priv.passed)
        self.assertIn(B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH, r_cfe_with_priv.error_codes)
        self.assertIn(B3_ERR_MEDIA_PATH_ASYMMETRY_MISMATCH, r_sd_no_priv.error_codes)

    def test_37_b3_rejects_unsupported_slot1_media_type(self) -> None:
        r = evaluate_check_group_3_slot1_lut_camset_vault(
            slot1_media_type="XQD_LEGACY", **self._sim_kwargs()
        )
        self.assertFalse(r.passed)
        self.assertIn(B3_ERR_UNSUPPORTED_MEDIA_TYPE, r.error_codes)

    def test_38_b3_rejects_slot2_and_mr_recall_mode(self) -> None:
        r_slot2 = evaluate_check_group_3_slot1_lut_camset_vault(
            camset_target_slot=2, **self._sim_kwargs()
        )
        r_mr = evaluate_check_group_3_slot1_lut_camset_vault(
            camera_exposure_mode="MR1", **self._sim_kwargs()
        )
        self.assertFalse(r_slot2.passed)
        self.assertIn(B3_ERR_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY, r_slot2.error_codes)
        self.assertFalse(r_mr.passed)
        self.assertIn(B3_ERR_CAMSET_DISABLED_IN_MR_RECALL_MODE, r_mr.error_codes)

    def test_39_b3_rejects_camset11_or_duplicate_camset_files(self) -> None:
        r_11 = evaluate_check_group_3_slot1_lut_camset_vault(
            camset_filenames=("CAMSET11.DAT",), **self._sim_kwargs()
        )
        r_dup = evaluate_check_group_3_slot1_lut_camset_vault(
            camset_filenames=("CAMSET01.DAT", "CAMSET01.DAT"), **self._sim_kwargs()
        )
        self.assertFalse(r_11.passed)
        self.assertFalse(r_dup.passed)
        self.assertIn(B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING, r_11.error_codes)
        self.assertIn(B3_ERR_CAMSET_FILENAME_OR_10_SLOT_CEILING, r_dup.error_codes)

    def test_40_b3_rejects_cross_model_fx3a_and_fx6_camset_dat(self) -> None:
        for foreign in ("ILME-FX3A", "ILME-FX6"):
            r = evaluate_check_group_3_slot1_lut_camset_vault(
                camset_dat_model_tags=("ILME-FX3", foreign),
                **self._sim_kwargs(),
            )
            self.assertFalse(r.passed)
            self.assertIn(B3_ERR_CROSS_MODEL_CAMSET_DAT_CONTAMINATION, r.error_codes)

    def test_41_b3_rejects_non_sandboxed_camset_or_lut_overlay_and_601_p2_split(self) -> None:
        r_cs = evaluate_check_group_3_slot1_lut_camset_vault(
            stageb_camset_overlay_path="p2:/setting/camset", **self._sim_kwargs()
        )
        r_lut_p2 = evaluate_check_group_3_slot1_lut_camset_vault(
            p2_setting_lut_writes=1, **self._sim_kwargs()
        )
        r_stale_601 = evaluate_check_group_3_slot1_lut_camset_vault(
            legacy_v601_unreregistered_slots_on_p2=2, **self._sim_kwargs()
        )
        self.assertFalse(r_cs.passed)
        self.assertIn(B3_ERR_STAGEB_CAMSET_OVERLAY_SANDBOX_VIOLATION, r_cs.error_codes)
        self.assertFalse(r_lut_p2.passed)
        self.assertIn(B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION, r_lut_p2.error_codes)
        self.assertFalse(r_stale_601.passed)
        self.assertIn(B3_ERR_LUT_601_VS_702_P2_SETTING_SPLIT_VIOLATION, r_stale_601.error_codes)

    def test_42_b3_rejects_invalid_cube_grid_filename_slots_or_ae_ev(self) -> None:
        r_65 = evaluate_check_group_3_slot1_lut_camset_vault(
            cube_grid_sizes=(65,), **self._sim_kwargs()
        )
        r_long = evaluate_check_group_3_slot1_lut_camset_vault(
            cube_filenames=("A" * 60 + ".cube",), **self._sim_kwargs()
        )
        r_slots = evaluate_check_group_3_slot1_lut_camset_vault(
            user_lut_slot_count=17, **self._sim_kwargs()
        )
        r_ev = evaluate_check_group_3_slot1_lut_camset_vault(
            user_lut_ae_offset_ev=2.5, **self._sim_kwargs()
        )
        for res in (r_65, r_long, r_slots, r_ev):
            self.assertFalse(res.passed)
            self.assertIn(B3_ERR_CUBE_LUT_SPEC_OR_16_SLOT_CEILING, res.error_codes)

    def test_43_b3_slot1_dir_hygiene_rejects_appledouble_bodydata_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clean_dir = root / "clean_slot1"
            (clean_dir / "Private/Sony/PRO/LUT").mkdir(parents=True)
            (clean_dir / "Private/Sony/PRO/LUT/Look33.cube").write_text(
                "LUT_3D_SIZE 17\n", encoding="ascii"
            )
            r_clean = evaluate_check_group_3_slot1_lut_camset_vault(
                slot1_dir=clean_dir, **self._sim_kwargs()
            )
            self.assertTrue(r_clean.passed, msg=r_clean.errors)

            dirty_dir = root / "dirty_slot1"
            dirty_dir.mkdir()
            (dirty_dir / "._CAMSET01.DAT").write_bytes(b"junk")
            (dirty_dir / "BODYDATA (1).DAT").write_bytes(b"ota")
            os.symlink(dirty_dir / "._CAMSET01.DAT", dirty_dir / "sym.cube")
            r_dirty = evaluate_check_group_3_slot1_lut_camset_vault(
                slot1_dir=dirty_dir, **self._sim_kwargs()
            )
            self.assertFalse(r_dirty.passed)
            self.assertIn(B3_ERR_SYMLINK_OR_APPLEDOUBLE_HYGIENE, r_dirty.error_codes)

    def test_44_b3_detects_h0_h3_surface_drift(self) -> None:
        r = evaluate_check_group_3_slot1_lut_camset_vault(
            inject_h0_h3_drift_surface="p2", **self._sim_kwargs()
        )
        self.assertFalse(r.passed)
        self.assertEqual(r.h0_equals_h3_count, 15)
        self.assertIn(B3_ERR_H0_H3_16_SURFACE_PARITY_DRIFT, r.error_codes)

    def test_45_b3_rejects_same_st_dev_or_corrupted_tier0_receipt(self) -> None:
        kw_same = self._sim_kwargs()
        kw_same["st_dev_b_override"] = kw_same["st_dev_a_override"]
        r_same = evaluate_check_group_3_slot1_lut_camset_vault(**kw_same)
        self.assertFalse(r_same.passed)
        self.assertIn(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID, r_same.error_codes)

        kw_corrupt = self._sim_kwargs()
        bad = bytearray(kw_corrupt["receipt_b_bytes"])
        bad[-1] ^= 0xFF
        kw_corrupt["receipt_b_bytes"] = bytes(bad)
        r_corrupt = evaluate_check_group_3_slot1_lut_camset_vault(**kw_corrupt)
        self.assertFalse(r_corrupt.passed)
        self.assertIn(B3_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID, r_corrupt.error_codes)

    # ------------------------------------------------------------------
    # Unified Orchestrator, Verdicts, Tamper Verifier & CLI Subcommand
    # ------------------------------------------------------------------

    def test_46_orchestrator_offline_default_fails_closed_awaiting_tier0(self) -> None:
        rep = run_bench_cable_fan_and_slot1_preflight(simulate_ready_bench=False)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.check_groups_passed, 2)
        self.assertTrue(verify_phase204_report(rep.to_dict()).valid)

    def test_47_orchestrator_simulate_ready_bench_never_authorizes_live_attach(self) -> None:
        rep = run_bench_cable_fan_and_slot1_preflight(simulate_ready_bench=True)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep.all_3_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase204_report(rep.to_dict()).valid)

    def test_48_orchestrator_real_dual_file_receipts_keep_live_attach_false(self) -> None:
        sim = build_simulated_phase204_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "rcpt_a.bin"
            p_b = Path(td) / "rcpt_b.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])
            rep = run_bench_cable_fan_and_slot1_preflight(
                simulate_ready_bench=False,
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=0x101,
                st_dev_b_override=0x202,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(verify_phase204_report(rep.to_dict()).valid)

    def test_49_orchestrator_blocks_on_check_group_failure_even_with_simulate_ready(self) -> None:
        rep = run_bench_cable_fan_and_slot1_preflight(
            simulate_ready_bench=True,
            fan_mode="Always Off",
        )
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_BENCH_CHECK_FAILURE)
        self.assertFalse(rep.all_3_check_groups_passed)
        self.assertTrue(verify_phase204_report(rep.to_dict()).valid)

    def test_50_verify_phase204_report_catches_hash_and_safety_lock_tampering(self) -> None:
        base = run_bench_cable_fan_and_slot1_preflight(simulate_ready_bench=True).to_dict()

        tampered_sha = dict(base)
        tampered_sha["h0_equals_h3_count"] = 15
        self.assertFalse(verify_phase204_report(tampered_sha).valid)

        tampered_live = dict(base)
        tampered_live["hardware_live_attachment_authorized"] = True
        tampered_live["report_sha256"] = _canonical_sha256_dict(
            tampered_live, exclude_key="report_sha256"
        )
        self.assertFalse(verify_phase204_report(tampered_live).valid)

        tampered_end = dict(base)
        tampered_end["e_nd_actuator_tx_count"] = 2
        tampered_end["report_sha256"] = _canonical_sha256_dict(
            tampered_end, exclude_key="report_sha256"
        )
        self.assertFalse(verify_phase204_report(tampered_end).valid)

        tampered_sim_go = dict(base)
        tampered_sim_go["go_no_go"] = GO_NO_GO_READONLY_BENCH_PREFLIGHT_VERIFIED
        tampered_sim_go["report_sha256"] = _canonical_sha256_dict(
            tampered_sim_go, exclude_key="report_sha256"
        )
        self.assertFalse(verify_phase204_report(tampered_sim_go).valid)

    def test_51_render_phase204_markdown_contains_key_sections(self) -> None:
        rep = run_bench_cable_fan_and_slot1_preflight(
            simulate_ready_bench=False, fan_mode="Always Off"
        )
        md = render_phase204_markdown(rep)
        self.assertIn("Phase 204", md)
        self.assertIn(CHECK_GROUP_B1_ID, md)
        self.assertIn(CHECK_GROUP_B2_ID, md)
        self.assertIn(CHECK_GROUP_B3_ID, md)
        self.assertIn("## Required Actions", md)

    def test_52_deterministic_report_sha256_in_clean_room(self) -> None:
        r1 = run_bench_cable_fan_and_slot1_preflight(
            simulate_ready_bench=True, force_clean_room=True
        )
        r2 = run_bench_cable_fan_and_slot1_preflight(
            simulate_ready_bench=True, force_clean_room=True
        )
        d1 = r1.to_dict()
        d2 = r2.to_dict()
        d1["donor_inspection"]["elapsed_seconds"] = 0.0001
        d2["donor_inspection"]["elapsed_seconds"] = 0.0001
        self.assertEqual(
            _canonical_sha256_dict(d1, exclude_key="report_sha256"),
            _canonical_sha256_dict(d2, exclude_key="report_sha256"),
        )

    def test_53_cli_preflight_bench_cable_fan_slot1_simulate_ready_json_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "phase204.json"
            out_md = Path(td) / "phase204.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-bench-cable-fan-slot1",
                        "--simulate-ready-bench",
                        "--force-clean-room",
                        "--json",
                        "--output",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["schema"], PHASE_204_SCHEMA)
            self.assertEqual(parsed["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertFalse(parsed["hardware_live_attachment_authorized"])
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())

    def test_54_cli_preflight_bench_cable_fan_slot1_offline_blocks_exit_1(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(["preflight-bench-cable-fan-slot1", "--force-clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn(GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
