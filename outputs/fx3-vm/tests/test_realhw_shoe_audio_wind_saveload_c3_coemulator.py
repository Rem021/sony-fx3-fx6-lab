#!/usr/bin/env python3
"""Unit tests for Phase 244 Stage 46 (`46/46` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 2.00..7.02`) Wave-36 `[Shoe Audio Set.]`
`48kHz/24bit 4ch` Meter Expansion vs `3.5mm` Jack, `ANALOG` Switch & `S&Q` Lockouts,
`[Wind Noise Reduct.]` Built-In Stereo Mic Exclusivity & Indoor Low-Cut Warning, and
`[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Privacy/Calibration
Firewall & Slot-1 Tier-0 Vault Write Guard HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_shoe_audio_wind_saveload_c3_coemulator as p244  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil()
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase244ShoeAudioWindSaveLoadC3CoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 46/46 & O_RDONLY Donor Inspection (10)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_46_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p244.SCHEMA_ID,
            "realhw_shoe_audio_wind_saveload_c3_coemulator_v1",
        )
        self.assertEqual(p244.PHASE_244_SCHEMA, p244.SCHEMA_ID)
        self.assertEqual(p244.PHASE_244_VERSION, "244.0.0")
        self.assertEqual(p244.STAGE_INDEX, 46)
        self.assertEqual(p244.STAGE_TOTAL, 46)
        self.assertEqual(p244.MILESTONE_LABEL, "46/46")
        self.assertEqual(
            p244.STAGE_NAME,
            "stage46_realhw_shoe_audio_wind_saveload_c3_hil",
        )
        self.assertEqual(p244.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p244.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p244.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p244.CNFLASHA_MUTATION_BYTES, 0)
        self.assertEqual(p244.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p244.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p244.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p244.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p244.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p244.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p244.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p244.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p244.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p244.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p244.SHOE_AUDIO_4CH_DISQUALIFICATION_BYPASS_EVENTS, 0)
        self.assertEqual(p244.EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES, 0)
        self.assertEqual(p244.EXCLUDED_SECRET_OR_CALIBRATION_LEAK_EVENTS, 0)
        self.assertEqual(p244.TIER0_SLOT1_UNVERIFIED_CAMSET_SAVE_EVENTS, 0)
        self.assertEqual(p244.CROSS_MODEL_FX6_CAMSET_LOAD_EVENTS, 0)
        self.assertEqual(p244.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p244.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_sub_100ms_bounded_and_cached(self) -> None:
        p244._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p244.inspect_phase244_donors()
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p244.inspect_phase244_donors()
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 14)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.1)
        self.assertLess(dt2, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p244.inspect_phase244_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.shoe_audio_4ch_and_3lockouts_proven)
        self.assertTrue(da.wind_noise_reduct_builtin_only_proven)
        self.assertTrue(da.saveload_camset_c3_exclusion_firewall_proven)
        self.assertEqual(da.donor_files_inspected, 14)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p244.is_forced_clean_room({p244.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p244.is_forced_clean_room({p244.ENV_FORCE_CLEAN_ROOM: falsy}))

    def test_05_env_clean_room_sentinel_paths_never_touch_local_donors(self) -> None:
        paths = p244.resolve_phase244_donor_paths(env={p244.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 14)
        for p in paths.values():
            self.assertIn(p244.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_06_nonexistent_donor_paths_fall_back_cleanly_to_synthetic(self) -> None:
        missing_paths = {
            k: Path("/nonexistent_phase244_work_root_xyz") / rel
            for k, rel in p244.DONOR_RELPATHS.items()
        }
        with unittest.mock.patch.object(
            p244, "resolve_phase244_donor_paths", return_value=missing_paths
        ):
            da = p244.inspect_phase244_donors(force_clean_room=False)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_07_compact_donor_tokens_verified_for_shoe_audio_wind_and_saveload(self) -> None:
        for da in (p244.inspect_phase244_donors(force_clean_room=True), p244.inspect_phase244_donors()):
            for tok in (
                "Shoe Audio Set.",
                "48kHz",
                "16bit",
                "24bit",
                "2ch",
                "4ch",
                "Audio Recording",
                "Audio Level Display",
                "Wind Noise Reduct.",
                "Save/Load Settings",
                "Cloud(Private)",
                "Cloud(Share)",
                "IPTC Information",
                "Copyright Info",
                "Face Memory",
                "FTP Transfer Func.",
                "Streaming",
                "Wi-Fi",
            ):
                self.assertEqual(da.fx3_string_en_f.marker_hits[tok], 1)
            self.assertEqual(da.fx3_saveload.marker_hits["infra_saveLoadSettings_init"], 1)

    def test_08_bounded_window_large_donors_stay_within_cap(self) -> None:
        da = p244.inspect_phase244_donors()
        for lrg in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
            da.fx3_bk4,
            da.fx6_bk4,
        ):
            self.assertTrue(lrg.bounded_windows_only)
            self.assertLessEqual(lrg.bytes_read_total, 12 * p244.BOUNDED_WINDOW_MAX_BYTES)
            for lbl, hit in lrg.window_hits.items():
                self.assertEqual(hit, 1, msg=f"Missing window {lbl} in {lrg.artifact_key}")

    def test_09_no_raw_firmware_blobs_present_in_serialized_json(self) -> None:
        for rep in (_get_clean_room_audit(), _get_default_audit()):
            blob = json.dumps(rep)
            self.assertNotIn("\x7fELF", blob)
            self.assertNotIn("uxc\x07", blob)
            self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_10_deterministic_audit_digest_sha256_in_both_modes(self) -> None:
        c1 = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(force_clean_room=True)
        c2 = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(force_clean_room=True)
        self.assertEqual(c1["audit_digest_sha256"], c2["audit_digest_sha256"])
        self.assertEqual(len(c1["audit_digest_sha256"]), 64)
        d1 = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil()
        d2 = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil()
        self.assertEqual(d1["audit_digest_sha256"], d2["audit_digest_sha256"])

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 46A — [Shoe Audio Set.] 4ch Meter & 3 Lockouts (13)
    # ------------------------------------------------------------------
    def test_11_shoe_audio_factory_default_48khz_16bit_2ch_on_xlrh1_digital(self) -> None:
        res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/16bit 2ch",
            mi_shoe_accessory="XLR-H1",
            xlr_h1_slide_switch="DIGITAL",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_sample_rate_hz, 48_000)
        self.assertEqual(res.effective_bit_depth, 16)
        self.assertEqual(res.effective_recorded_channels, 2)
        self.assertEqual(res.osd_audio_level_meter_channels, ("CH1", "CH2"))
        self.assertFalse(res.osd_meter_expanded_to_4ch)

    def test_12_shoe_audio_48khz_24bit_2ch_on_xlrh1_digital(self) -> None:
        res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 2ch",
            mi_shoe_accessory="XLR-H1",
            xlr_h1_slide_switch="DIGITAL",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_bit_depth, 24)
        self.assertEqual(res.effective_recorded_channels, 2)
        self.assertEqual(res.osd_audio_level_meter_channels, ("CH1", "CH2"))
        self.assertFalse(res.osd_meter_expanded_to_4ch)

    def test_13_shoe_audio_48khz_24bit_4ch_expands_osd_meters_on_xlrh1_and_ecm_m1(self) -> None:
        for acc in ("XLR-H1", "ECM-M1"):
            res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
                configured_shoe_audio_set="48kHz/24bit 4ch",
                mi_shoe_accessory=acc,
                xlr_h1_slide_switch="DIGITAL",
                audio_level_display="On",
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_sample_rate_hz, 48_000)
            self.assertEqual(res.effective_bit_depth, 24)
            self.assertEqual(res.effective_recorded_channels, 4)
            self.assertEqual(res.osd_audio_level_meter_channels, ("CH1", "CH2", "CH3", "CH4"))
            self.assertTrue(res.osd_meter_expanded_to_4ch)

    def test_14_audio_level_display_off_hides_meters_while_recording_4ch(self) -> None:
        res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="XLR-H1",
            xlr_h1_slide_switch="DIGITAL",
            audio_level_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_recorded_channels, 4)
        self.assertEqual(res.osd_audio_level_meter_channels, ())
        self.assertFalse(res.osd_meter_expanded_to_4ch)

    def test_15_shoe_audio_reset_by_camera_settings_reset_and_initialize(self) -> None:
        for action in ("Camera Settings Reset", "Initialize"):
            res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
                configured_shoe_audio_set="48kHz/24bit 4ch",
                reset_action=action,
                mi_shoe_accessory="XLR-H1",
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.reset_by_camera_settings_reset)
            self.assertEqual(res.effective_shoe_audio_set_register, "48kHz/16bit 2ch")
            self.assertEqual(res.effective_recorded_channels, 2)
            self.assertEqual(res.effective_bit_depth, 16)

    def test_16_shoe_audio_slot1_camset_zero_nvram_recall_lifecycle(self) -> None:
        lc = p244.run_shoe_audio_reset_and_camset_recall_lifecycle()
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(
            lc["after_slot1_camset01_recall_4ch"]["slot1_camset_restored"], "CAMSET01.DAT"
        )
        self.assertEqual(
            lc["after_slot1_camset01_recall_4ch"]["bk4_persistent_nvram_writes"], 0
        )

    def test_17_lockout_1_audio_recording_off_and_sq_motion_force_0_tracks(self) -> None:
        r_off = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            audio_recording="Off",
            mi_shoe_accessory="XLR-H1",
        )
        r_sq = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            shooting_mode="S&Q Motion",
            mi_shoe_accessory="XLR-H1",
        )
        for r in (r_off, r_sq):
            self.assertTrue(r.admitted)
            self.assertTrue(r.shoe_audio_menu_grayed_out)
            self.assertEqual(r.effective_recorded_channels, 0)
            self.assertEqual(r.osd_audio_level_meter_channels, ())
            self.assertIn(p244.LOCKOUT_AUDIO_REC_OFF_OR_SQ, r.active_lockouts)

    def test_18_lockout_2_body_35mm_mic_plug_overrides_mishoe_to_2ch_analog(self) -> None:
        res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="XLR-H1",
            xlr_h1_slide_switch="DIGITAL",
            body_35mm_mic_plugged=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.shoe_audio_menu_grayed_out)
        self.assertEqual(res.active_audio_input_route, "BODY_35MM_ANALOG_ADC_2CH")
        self.assertEqual(res.effective_sample_rate_hz, 48_000)
        self.assertEqual(res.effective_bit_depth, 16)
        self.assertEqual(res.effective_recorded_channels, 2)
        self.assertEqual(res.osd_audio_level_meter_channels, ("CH1", "CH2"))
        self.assertIn(p244.LOCKOUT_BODY_35MM_JACK_PRIORITY, res.active_lockouts)

    def test_19_lockout_3_xlrh1_analog_switch_and_analog_shoe_mic_force_2ch_16bit(self) -> None:
        r_sw = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="XLR-H1",
            xlr_h1_slide_switch="ANALOG",
        )
        r_ana = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="ANALOG_SHOE_MIC",
        )
        for r in (r_sw, r_ana):
            self.assertTrue(r.admitted)
            self.assertTrue(r.shoe_audio_menu_grayed_out)
            self.assertEqual(r.effective_bit_depth, 16)
            self.assertEqual(r.effective_recorded_channels, 2)
            self.assertIn(p244.LOCKOUT_XLR_H1_ANALOG_SWITCH, r.active_lockouts)

    def test_20_builtin_mic_and_2ch_digital_shoe_mic_clamp_safely_to_2ch(self) -> None:
        r_builtin = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="NONE",
        )
        self.assertEqual(r_builtin.effective_recorded_channels, 2)
        self.assertEqual(r_builtin.effective_bit_depth, 16)

        r_b1m = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_accessory="ECM-B1M",
        )
        self.assertEqual(r_b1m.effective_recorded_channels, 2)
        self.assertEqual(r_b1m.effective_bit_depth, 24)

    def test_21_all_three_4ch_lockout_bypass_attempts_fail_closed_eopnotsupp(self) -> None:
        cases = (
            {"shooting_mode": "S&Q Motion", "mi_shoe_accessory": "XLR-H1"},
            {"audio_recording": "Off", "mi_shoe_accessory": "XLR-H1"},
            {"body_35mm_mic_plugged": True, "mi_shoe_accessory": "XLR-H1"},
            {"mi_shoe_accessory": "XLR-H1", "xlr_h1_slide_switch": "ANALOG"},
        )
        for kw in cases:
            res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
                configured_shoe_audio_set="48kHz/24bit 4ch",
                attempt_force_4ch_bypass=True,
                **kw,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.shoe_audio_4ch_disqualification_bypass_events, 0)

    def test_22_shoe_audio_invalid_inputs_rejected_einval(self) -> None:
        for bad_kw in (
            {"firmware_version": "1.00"},
            {"configured_shoe_audio_set": "96kHz/32bit 8ch"},
            {"mi_shoe_accessory": "SDI_EMBEDDED_AUDIO"},
            {"xlr_h1_slide_switch": "AES_EBU"},
            {"slot1_camset_filename": "CAMSET11.DAT"},
        ):
            res = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(**bad_kw)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EINVAL_ERRNO)

    def test_23_pillar_a_evaluator_passes_completely(self) -> None:
        pa = p244.evaluate_pillar_a_shoe_audio_4ch_and_3lockouts_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["all_3_shoe_audio_modes"]), 3)
        self.assertEqual(len(pa["all_3_lockout_ids"]), 3)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 46B — [Wind Noise Reduct.] Built-In Only (10)
    # ------------------------------------------------------------------
    def test_24_wind_noise_reduct_factory_default_off_and_reset_behavior(self) -> None:
        r_def = p244.simulate_wind_noise_reduct_builtin_only_hil()
        self.assertTrue(r_def.admitted)
        self.assertEqual(r_def.effective_wind_noise_reduct_register, "Off")
        self.assertFalse(r_def.builtin_mic_dsp_wind_hpf_active)

        r_csr = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_wind_noise_reduct_register, "Off")
        self.assertFalse(r_csr.builtin_mic_dsp_wind_hpf_active)

    def test_25_wind_noise_reduct_outdoor_builtin_stereo_mic_on_active(self) -> None:
        res = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            mi_shoe_accessory="NONE",
            body_35mm_mic_plugged=False,
            acoustic_environment="OUTDOOR_STRONG_WIND",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.active_mic_source, "BUILTIN_STEREO_MIC")
        self.assertTrue(res.builtin_mic_dsp_wind_hpf_active)
        self.assertFalse(res.indoor_low_freq_attenuation_warning)
        self.assertEqual(res.external_mic_wind_reduct_applied_frames, 0)

    def test_26_wind_noise_reduct_does_not_function_on_35mm_external_mic(self) -> None:
        res = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            body_35mm_mic_plugged=True,
            acoustic_environment="OUTDOOR_STRONG_WIND",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.active_mic_source, "BODY_35MM_EXTERNAL_MIC")
        self.assertFalse(res.builtin_mic_dsp_wind_hpf_active)
        self.assertEqual(res.external_mic_wind_reduct_applied_frames, 0)

    def test_27_wind_noise_reduct_does_not_function_on_xlrh1_or_ecm_m1_mishoe(self) -> None:
        for sw, hz in (("Off", 0), ("100Hz", 100), ("300Hz", 300)):
            res = p244.simulate_wind_noise_reduct_builtin_only_hil(
                configured_wind_noise_reduct="On",
                mi_shoe_accessory="XLR-H1",
                xlr_h1_low_cut_switch=sw,
                acoustic_environment="OUTDOOR_STRONG_WIND",
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.active_mic_source, "MI_SHOE_EXTERNAL_MIC")
            self.assertFalse(res.builtin_mic_dsp_wind_hpf_active)
            self.assertEqual(res.xlr_h1_hardware_low_cut_hz, hz)
            self.assertEqual(res.external_mic_wind_reduct_applied_frames, 0)

    def test_28_forcing_body_wind_dsp_onto_external_mic_blocked_eopnotsupp(self) -> None:
        for kw in (
            {"body_35mm_mic_plugged": True},
            {"mi_shoe_accessory": "XLR-H1"},
            {"mi_shoe_accessory": "ECM-M1"},
        ):
            res = p244.simulate_wind_noise_reduct_builtin_only_hil(
                configured_wind_noise_reduct="On",
                attempt_force_external_mic_wind_dsp=True,
                **kw,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.external_mic_wind_reduct_applied_frames, 0)

    def test_29_indoor_bench_wind_noise_reduct_on_warns_and_suppresses_ebusy(self) -> None:
        r_sup = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            acoustic_environment="INDOOR_BENCH",
            enforce_indoor_bench_guard=True,
        )
        self.assertFalse(r_sup.admitted)
        self.assertEqual(r_sup.errno_code, p244.EBUSY_ERRNO)
        self.assertTrue(r_sup.indoor_low_freq_attenuation_warning)
        self.assertTrue(r_sup.indoor_bench_wind_reduct_suppressed)
        self.assertFalse(r_sup.builtin_mic_dsp_wind_hpf_active)

        r_warn = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            acoustic_environment="INDOOR_BENCH",
            enforce_indoor_bench_guard=False,
        )
        self.assertTrue(r_warn.admitted)
        self.assertTrue(r_warn.indoor_low_freq_attenuation_warning)
        self.assertTrue(r_warn.builtin_mic_dsp_wind_hpf_active)

    def test_30_wind_noise_reduct_locked_out_in_sq_motion_and_audio_off(self) -> None:
        for kw in ({"shooting_mode": "S&Q Motion"}, {"audio_recording": "Off"}):
            r_passive = p244.simulate_wind_noise_reduct_builtin_only_hil(
                configured_wind_noise_reduct="On",
                acoustic_environment="OUTDOOR_STRONG_WIND",
                **kw,
            )
            self.assertTrue(r_passive.admitted)
            self.assertTrue(r_passive.wind_noise_menu_grayed_out)
            self.assertFalse(r_passive.builtin_mic_dsp_wind_hpf_active)

            r_force = p244.simulate_wind_noise_reduct_builtin_only_hil(
                configured_wind_noise_reduct="On",
                attempt_force_sq_or_audio_off_wind_dsp=True,
                **kw,
            )
            self.assertFalse(r_force.admitted)
            self.assertEqual(r_force.errno_code, p244.EOPNOTSUPP_ERRNO)

    def test_31_wind_noise_reduct_camset_recall_zero_nvram_writes(self) -> None:
        res = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            reset_action="Camera Settings Reset",
            slot1_camset_restore_wind="On",
            slot1_camset_filename="CAMSET02.DAT",
            acoustic_environment="OUTDOOR_STRONG_WIND",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.slot1_camset_restored, "CAMSET02.DAT")
        self.assertTrue(res.builtin_mic_dsp_wind_hpf_active)
        self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    def test_32_wind_noise_reduct_invalid_parameters_rejected_einval(self) -> None:
        for bad_kw in (
            {"configured_wind_noise_reduct": "Auto"},
            {"xlr_h1_low_cut_switch": "500Hz"},
            {"acoustic_environment": "UNDERWATER"},
            {"slot1_camset_restore_wind": "On"},
        ):
            res = p244.simulate_wind_noise_reduct_builtin_only_hil(**bad_kw)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EINVAL_ERRNO)

    def test_33_pillar_b_evaluator_passes_completely(self) -> None:
        pb = p244.evaluate_pillar_b_wind_noise_reduct_builtin_only_hil()
        self.assertTrue(pb["passed"])

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 46C — [Save/Load Settings] CAMSET/C3 Firewall (16)
    # ------------------------------------------------------------------
    def test_34_saveload_slot2_camset01_to_camset10_all_10_slots_admitted(self) -> None:
        for idx in range(1, 11):
            res = p244.simulate_saveload_camset_c3_firewall_hil(
                operation="Save",
                target="Slot 2",
                camset_slot_index=idx,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.camset_filename, f"CAMSET{idx:02d}.DAT")
            self.assertEqual(
                res.camset_media_path,
                f"/PRIVATE/SONY/PRO/CAMERA/ILME-FX3/CAMSET{idx:02d}.DAT",
            )
            self.assertEqual(res.saved_payload_excluded_keys, ())
            self.assertTrue(res.excluded_items_stripped_on_save)

    def test_35_saveload_camset_slot_index_out_of_range_rejected_einval(self) -> None:
        for bad_idx in (0, -1, 11, 99, True):
            res = p244.simulate_saveload_camset_c3_firewall_hil(
                operation="Save",
                target="Slot 2",
                camset_slot_index=bad_idx,  # type: ignore[arg-type]
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EINVAL_ERRNO)

    def test_36_saveload_invalid_operation_or_target_rejected_einval(self) -> None:
        for kw in (
            {"operation": "Delete"},
            {"target": "Slot 3"},
            {"firmware_version": "0.99"},
        ):
            res = p244.simulate_saveload_camset_c3_firewall_hil(**kw)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EINVAL_ERRNO)

    def test_37_saveload_cloud_private_and_cloud_share_ver_400_to_702_admitted(self) -> None:
        for fw in ("4.00", "5.00", "6.00", "6.02", "7.00", "7.02"):
            for tgt in ("Cloud(Private)", "Cloud(Share)"):
                for op in ("Save", "Load"):
                    res = p244.simulate_saveload_camset_c3_firewall_hil(
                        firmware_version=fw,
                        operation=op,
                        target=tgt,
                        camset_slot_index=1,
                    )
                    self.assertTrue(res.admitted)
                    self.assertTrue(res.c3_portal_cloud_sync_used)
                    self.assertEqual(res.card_sector_writes, 0)
                    self.assertEqual(res.excluded_secret_or_calibration_leak_events, 0)

    def test_38_saveload_cloud_c3_rejected_on_firmware_200_and_300(self) -> None:
        for fw in ("2.00", "3.00"):
            for tgt in ("Cloud(Private)", "Cloud(Share)"):
                res = p244.simulate_saveload_camset_c3_firewall_hil(
                    firmware_version=fw,
                    operation="Save",
                    target=tgt,
                )
                self.assertFalse(res.admitted)
                self.assertEqual(res.errno_code, p244.EOPNOTSUPP_ERRNO)

    def test_39_saveload_same_model_ilme_fx3_lock_rejects_fx6_and_fx3a(self) -> None:
        for foreign_model in ("ILME-FX6", "ILME-FX3A", "ILME-FX30", "ALL_FILE_FX6"):
            res = p244.simulate_saveload_camset_c3_firewall_hil(
                operation="Load",
                target="Slot 2",
                dat_model_header=foreign_model,
            )
            self.assertFalse(res.admitted)
            self.assertFalse(res.same_model_ilme_fx3_verified)
            self.assertEqual(res.errno_code, p244.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.cross_model_fx6_camset_load_events, 0)

    def test_40_saveload_save_strips_iptc_and_copyright_info(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Cloud(Share)",
        )
        self.assertTrue(res.admitted)
        for k in p244.EXCLUDED_REGISTER_KEYS_BY_CATEGORY[p244.EXCLUDED_CAT_IPTC_COPYRIGHT]:
            self.assertNotIn(k, res.saved_included_keys)
        self.assertEqual(res.saved_payload_excluded_keys, ())

    def test_41_saveload_save_strips_custom_wb_1_2_3_calibration_registers(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Slot 2",
        )
        self.assertTrue(res.admitted)
        for k in p244.EXCLUDED_REGISTER_KEYS_BY_CATEGORY[p244.EXCLUDED_CAT_CUSTOM_WB_1_3]:
            self.assertNotIn(k, res.saved_included_keys)

    def test_42_saveload_save_strips_face_memory_and_network_credentials(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Cloud(Private)",
        )
        self.assertTrue(res.admitted)
        for cat in (p244.EXCLUDED_CAT_FACE_MEMORY, p244.EXCLUDED_CAT_NETWORK_SECRETS):
            for k in p244.EXCLUDED_REGISTER_KEYS_BY_CATEGORY[cat]:
                self.assertNotIn(k, res.saved_included_keys)
        self.assertEqual(res.excluded_secret_or_calibration_leak_events, 0)

    def test_43_saveload_load_updates_camera_menus_without_touching_excluded_items(self) -> None:
        smuggled_payload = {
            "shoe_audio_set": "48kHz/24bit 4ch",
            "wind_noise_reduct": "On",
            "cine_ei_base_iso": 12800,
            "iptc_information": "MALICIOUS_IPTC",
            "write_copyright_info": "Off",
            "custom_wb_1_kelvin_gm": "9000K_FOREIGN",
            "custom_wb_2_kelvin_gm": "9000K_FOREIGN",
            "custom_wb_3_kelvin_gm": "9000K_FOREIGN",
            "face_memory_biometric_templates": ("SPOOF_FACE",),
            "ftp_server_account_password": "sftp://hijack.invalid",
            "streaming_rtmps_srt_key": "rtmps://hijack.invalid/key",
            "wifi_registered_ssid_passphrase": "ROGUE_AP:PASSWORD",
            "static_ip_dns_config": "192.0.2.99/24",
            "imported_tls_root_client_certs": "ROGUE_ROOT_CA",
        }
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Load",
            target="Cloud(Share)",
            incoming_load_payload=smuggled_payload,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.loaded_camera_registers["shoe_audio_set"], "48kHz/24bit 4ch")
        self.assertEqual(res.loaded_camera_registers["cine_ei_base_iso"], 12800)
        self.assertEqual(
            res.inbody_excluded_registers_after_op,
            dict(p244.DEFAULT_INBODY_EXCLUDED_REGISTERS),
        )
        self.assertEqual(res.excluded_secret_or_calibration_leak_events, 0)

    def test_44_saveload_explicit_excluded_item_bypass_blocked_eopnotsupp(self) -> None:
        for op in ("Save", "Load"):
            res = p244.simulate_saveload_camset_c3_firewall_hil(
                operation=op,
                target="Slot 2",
                attempt_include_excluded_secrets_or_cal=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p244.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.excluded_secret_or_calibration_leak_events, 0)

    def test_45_slot1_tier0_vault_load_remains_o_rdonly_zero_sector_writes(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Load",
            target="Slot 1",
            camset_slot_index=1,
            slot1_tier0_vault_active=True,
            slot1_wp_locked=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.donor_or_card_access_mode, "O_RDONLY")
        self.assertEqual(res.card_sector_writes, 0)
        self.assertEqual(res.tier0_slot1_unverified_camset_save_events, 0)

    def test_46_slot1_tier0_wp_locked_save_blocked_erofs(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Slot 1",
            slot1_tier0_vault_active=True,
            slot1_wp_locked=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p244.EROFS_ERRNO)
        self.assertEqual(res.card_sector_writes, 0)
        self.assertEqual(res.tier0_slot1_unverified_camset_save_events, 0)

    def test_47_slot1_tier0_unverified_unlocked_save_blocked_ebusy(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Slot 1",
            slot1_tier0_vault_active=True,
            slot1_wp_locked=False,
            slot1_tier0_offline_sha256_verified_and_retired=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p244.EBUSY_ERRNO)
        self.assertEqual(res.card_sector_writes, 0)
        self.assertEqual(res.tier0_slot1_unverified_camset_save_events, 0)

    def test_48_slot1_save_admitted_only_after_tier0_offline_sha256_retired(self) -> None:
        res = p244.simulate_saveload_camset_c3_firewall_hil(
            operation="Save",
            target="Slot 1",
            camset_slot_index=3,
            slot1_tier0_vault_active=True,
            slot1_wp_locked=False,
            slot1_tier0_offline_sha256_verified_and_retired=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.camset_filename, "CAMSET03.DAT")
        self.assertEqual(res.tier0_slot1_unverified_camset_save_events, 0)

    def test_49_pillar_c_d_evaluator_passes_completely(self) -> None:
        pcd = p244.evaluate_pillar_c_d_saveload_camset_c3_firewall_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["all_10_camset_filenames"]), 10)
        self.assertEqual(len(pcd["all_4_excluded_categories"]), 4)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 12)

    # ------------------------------------------------------------------
    # Group 5: Redlines, CLI, 46/46 Suite Wiring & Bytecode Hygiene (15)
    # ------------------------------------------------------------------
    def test_50_baseline_redline_guard_and_all_12_negative_probes_fail_closed(self) -> None:
        base = p244.probe_stage46_redline_guard()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.hardware_live_attachment_authorized)
        self.assertFalse(base.overall_ready_for_hardware_attach)
        self.assertFalse(base.isp_write_authorized)
        self.assertTrue(base.cnflasha_userspace_write_blocked)
        self.assertEqual(base.cnflasha_mutation_bytes, 0)
        self.assertEqual(base.physical_device_writes, 0)
        self.assertEqual(base.raw_firmware_bytes_leaked, 0)

        for field in (
            "request_persistent_emmc_write",
            "request_live_hardware_attach",
            "request_overall_ready_attach",
            "request_spi_nor_write",
            "request_el3_payload_tx",
            "request_isp_write",
            "request_cnflasha_userspace_write",
            "request_usb_packet_tx",
            "request_shoe_audio_4ch_lockout_bypass",
            "request_external_mic_wind_dsp_bypass",
            "request_excluded_secret_or_cal_leak",
            "request_unverified_slot1_tier0_camset_save",
        ):
            probe = p244.probe_stage46_redline_guard(**{field: True})
            self.assertFalse(probe.valid, msg=f"Expected {field} to fail closed")

    def test_51_full_audit_payload_passes_in_both_clean_room_and_default_modes(self) -> None:
        c1 = _get_clean_room_audit()
        d1 = _get_default_audit()
        for rep in (c1, d1):
            self.assertTrue(rep["all_checks_passed"])
            self.assertEqual(rep["schema"], "realhw_shoe_audio_wind_saveload_c3_coemulator_v1")
            self.assertEqual(rep["milestone"], "46/46")
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["cnflasha_mutation_bytes"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["shoe_audio_4ch_disqualification_bypass_events"], 0)
            self.assertEqual(red["external_mic_wind_reduct_applied_frames"], 0)
            self.assertEqual(red["excluded_secret_or_calibration_leak_events"], 0)
            self.assertEqual(red["tier0_slot1_unverified_camset_save_events"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_52_in_process_cli_json_and_summary_modes(self) -> None:
        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p244.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "46/46")
        self.assertTrue(parsed["all_checks_passed"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p244.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 244 Stage 46 (46/46)", buf_sum.getvalue())

    def test_53_subprocess_cli_clean_room_and_default_modes(self) -> None:
        script = str(FX3_VM_DIR / "realhw_shoe_audio_wind_saveload_c3_coemulator.py")
        base_env = dict(os.environ)
        base_env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=base_env,
            check=True,
        )
        self.assertIn("[PASS] Phase 244 Stage 46 (46/46)", p_sum.stdout)

        clean_env = dict(base_env)
        clean_env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        p_clean = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=clean_env,
            check=True,
        )
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", p_clean.stdout)

    def test_54_fx3_vm_coemulation_suite_includes_stage46_and_46_stage_milestone(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage46_realhw_shoe_audio_wind_saveload_c3_hil", rep_on)
        s46 = rep_on["stage46_realhw_shoe_audio_wind_saveload_c3_hil"]
        self.assertTrue(s46["all_checks_passed"])
        self.assertEqual(s46["milestone"], "46/46")
        self.assertEqual(s46["schema"], "realhw_shoe_audio_wind_saveload_c3_coemulator_v1")
        self.assertEqual(s46["shoe_audio_4ch_disqualification_bypass_events"], 0)
        self.assertEqual(s46["external_mic_wind_reduct_applied_frames"], 0)
        self.assertEqual(s46["excluded_secret_or_calibration_leak_events"], 0)
        self.assertEqual(s46["tier0_slot1_unverified_camset_save_events"], 0)
        self.assertEqual(s46["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 46)
        self.assertLess(dt_clean, 4.5)

    def test_55_fx3_vm_coemulation_suite_all_46_stage_indices_unique_and_present(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        for idx in range(1, 47):
            matches = [k for k in rep_def if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(dt_def, 5.0)

    def test_56_fx3_vm_coemulation_suite_skip_stage46_and_skip_phase244_config(self) -> None:
        rep_skip_p244 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase244_realhw_shoe_audio_wind_saveload_c3_hil=False,
            )
        )
        self.assertTrue(rep_skip_p244["all_checks_passed"])
        self.assertNotIn("stage46_realhw_shoe_audio_wind_saveload_c3_hil", rep_skip_p244)
        self.assertFalse(rep_skip_p244["config"]["include_stage46"])

        rep_skip_s46 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_stage46=False,
            )
        )
        self.assertTrue(rep_skip_s46["all_checks_passed"])
        self.assertNotIn("stage46_realhw_shoe_audio_wind_saveload_c3_hil", rep_skip_s46)

    def test_57_fx3_vm_coemulation_suite_include_stage46_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--include-stage46", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn("realhw_shoe_audio_wind_saveload_c3_hil=CLEAN_ROOM_SYNTHETIC", out)

    def test_58_fx3_vm_coemulation_suite_cli_skip_phase244_and_skip_stage46(self) -> None:
        for flag in ("--skip-phase244", "--skip-stage46", "--no-include-stage46"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(["--clean-room", flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage46_realhw_shoe_audio_wind_saveload_c3_hil", rep)

    def test_59_run_stage46_direct_runner_matches_standalone_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s46 = suite.run_stage46_realhw_shoe_audio_wind_saveload_c3_hil(cfg)
        c1 = _get_clean_room_audit()
        self.assertEqual(s46["phase244_audit_digest_sha256"], c1["audit_digest_sha256"])

    def test_60_menu_paths_match_official_sony_ilme_fx3_help_guide(self) -> None:
        self.assertEqual(
            p244.SHOE_AUDIO_SET_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]",
        )
        self.assertEqual(
            p244.WIND_NOISE_REDUCT_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]",
        )
        self.assertEqual(
            p244.SAVE_LOAD_SETTINGS_MENU_PATH,
            "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]",
        )

    def test_61_reset_behavior_contrast_shoe_and_wind_both_resettable(self) -> None:
        s_shoe = p244.simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set="48kHz/24bit 4ch",
            reset_action="Camera Settings Reset",
        )
        s_wind = p244.simulate_wind_noise_reduct_builtin_only_hil(
            configured_wind_noise_reduct="On",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(s_shoe.effective_shoe_audio_set_register, "48kHz/16bit 2ch")
        self.assertEqual(s_wind.effective_wind_noise_reduct_register, "Off")

    def test_62_fx3_vm_readme_documents_phase244_stage46_and_46_of_46_milestone(self) -> None:
        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 244", readme)
        self.assertIn("Stage 46", readme)
        self.assertIn("46/46", readme)
        self.assertIn("realhw_shoe_audio_wind_saveload_c3_coemulator.py", readme)
        self.assertIn("--include-stage46", readme)

    def test_63_dual_mode_standalone_runtime_well_under_1_second(self) -> None:
        t0 = time.monotonic()
        r_clean = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(force_clean_room=True)
        r_def = p244.run_phase244_realhw_shoe_audio_wind_saveload_c3_hil()
        elapsed = time.monotonic() - t0
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertLess(elapsed, 5.00 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 1.0)

    def test_64_zero_pyc_bytecode_files_in_fx3_vm_tree(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
