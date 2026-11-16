#!/usr/bin/env python3
"""Unit tests for Phase 262 Stage 51 (`51/51`):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`) Wave-41
`[Auto Slow Shutter]` 6-Condition Lockout & `Ver. 7.02` `[Shutter Angle]`
Disjointness, `[HDMI Output Settings]` `REC Control` <- `Time Code Output` Gate
& `4ch Audio Output` + Slot-1 Vault Guard, and `[Lens Compensation]` ->
`[Breathing Comp.]` Movie-Only Compliant-Lens Crop & `RAW` / `240p` Lockout
HIL Co-Emulator (66 dual-mode tests).
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
import realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator as p262  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated imaging/fault Unicorn loops for <50ms flag tests."""
    base = dict(
        force_clean_room=True,
        include_phase41_dtb_mhlx=False,
        include_phase45_imx510_xavc=False,
        include_phase53_hil_fault_harness=False,
        include_phase58_qmp_introspection=False,
        include_phase63_hdmi_raw_uvc=False,
        include_phase67_tc_lens_paint=False,
        include_phase71_dualslot_ups_salvage=False,
        include_phase78_touchaf_ciz_assignable=False,
        include_phase82_camset_lpcm_tcub=False,
        include_phase87_playback_shotmark_dewpoint=False,
        include_phase91_gyroflow_rtmd_anamorphic=False,
        include_phase96_interval_cache_ftp_fan=False,
        include_phase99_lut3d_subzero_sdi=False,
        include_phase103_emi_exfat_endurance=False,
        include_phase107_c2pa_shading_mcfleet_ovp=False,
        include_phase112_hdr_hlg_fiz_gimbal=False,
        include_phase117_proresraw_breathing_mishoe_hil=False,
        include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        include_phase132_vp_ledwall_freed_artnet_hil=False,
        include_phase141_realhw_preflash_dualboot_hil=False,
        include_phase145_realhw_mpr_dmm_rec=False,
        include_phase150_realhw_body_peripheral_hil=False,
        include_phase157_realhw_imx510_network_usb_hil=False,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
        include_phase167_realhw_cxd90058_sabin_seal_hil=False,
        include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
        include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
        include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
        include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
        include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
        include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
        include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
        include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=False,
        include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=False,
        include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=False,
        include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=False,
        include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=False,
        include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=False,
        include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=False,
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
        include_stage49=False,
        include_stage50=False,
    )
    base.update(overrides)
    return base


class TestPhase262AutoSlowShutterHdmiRecControlBreathingCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = (
            p262.run_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil(
                force_clean_room=True
            )
        )
        cls.default_audit = (
            p262.run_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil()
        )

        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        cls.default_suite_elapsed = time.monotonic() - t0

        if p262.is_forced_clean_room():
            cls.clean_suite = cls.default_suite
            cls.clean_suite_elapsed = cls.default_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
            )
            cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Phase 262 Stage 51 (51/51) & O_RDONLY Donors (12)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase262_stage51_and_redlines(self) -> None:
        self.assertEqual(
            p262.SCHEMA_ID,
            "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1",
        )
        self.assertEqual(p262.PHASE_262_SCHEMA, p262.SCHEMA_ID)
        self.assertEqual(p262.PHASE_262_VERSION, "262.0.0")
        self.assertEqual(p262.PHASE_NUMBER, 262)
        self.assertEqual(p262.STAGE_INDEX, 51)
        self.assertEqual(p262.STAGE_TOTAL, 51)
        self.assertEqual(p262.MILESTONE_LABEL, "51/51")
        self.assertEqual(
            p262.STAGE_NAME,
            "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
        )
        self.assertEqual(p262.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p262.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p262.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p262.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p262.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p262.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p262.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p262.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p262.SOURCE_MODE_CLEAN_ROOM)
        again = p262.run_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil(
            force_clean_room=True
        )
        self.assertEqual(self.clean_audit["audit_digest_sha256"], again["audit_digest_sha256"])
        self.assertEqual(len(self.clean_audit["audit_digest_sha256"]), 64)

    def test_03_default_audit_fast_and_zero_leakage(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["donor_files_inspected"], 15)
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertLess(da["inspection_elapsed_s"], 0.1)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_04_all_15_donor_expected_byte_sizes_verified(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key, expected_size in p262.EXPECTED_DONOR_BYTES.items():
                self.assertEqual(audit[key]["file_bytes"], expected_size)

    def test_05_fx3_and_fx6_uxc_wave41_string_markers_and_absent_markers(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            fx3_s = audit["fx3_string_en_f"]
            self.assertTrue(fx3_s["uxd_container_ok"])
            for tok in (
                "Auto Slow Shutter",
                "Exposure",
                "Shutter Mode",
                "Angle",
                "Speed",
                "Flexible Exp. Mode",
                "Log Shooting",
                "Cine EI Quick",
                "Cine EI",
                "ISO AUTO",
                "HDMI Output Settings",
                "REC Control",
                "Time Code Output",
                "4ch Audio Output",
                "CH1/CH2",
                "CH3/CH4",
                "Rec. Media dur HDMI Output",
                "Proxy Recording",
                "RAW Output",
                "Lens Compensation",
                "Breathing Comp.",
                "Camera Settings Reset",
                "Reset Network Set.",
                "Initialize",
            ):
                self.assertEqual(fx3_s["marker_hits"][tok], 1)
            self.assertEqual(fx3_s["absent_marker_hits"]["Autoframing Settings"], 0)
            self.assertEqual(fx3_s["absent_marker_hits"]["ECS"], 0)
            fx6_s = audit["fx6_string_en"]
            self.assertTrue(fx6_s["uxd_container_ok"])
            for tok in ("Shutter", "Angle", "HDMI", "Timecode", "Audio", "Breathing", "Reset"):
                self.assertEqual(fx6_s["marker_hits"][tok], 1)

    def test_06_appfw_bounded_windows_4kib_verified(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key in ("fx3_appfw", "fx6_appfw"):
                entry = audit[key]
                self.assertTrue(entry["bounded_windows_only"])
                self.assertTrue(entry["elf64_le_ok"])
                for lbl in (
                    "ELF64",
                    "SHUTTER",
                    "HDMI",
                    "AUDIO",
                    "TIMECODE",
                    "BREATH",
                    "LENS",
                    "PROXY",
                    "RESET",
                ):
                    self.assertEqual(entry["window_hits"][lbl], 1)

    def test_07_cpapp_libmpr_and_bk4_bounded_windows_verified(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key in ("fx3_cpapp", "fx6_cpapp"):
                hits = audit[key]["window_hits"]
                for lbl in (
                    "AUDIO",
                    "INITIALIZE",
                    "LENS",
                    "SHUTTER",
                    "RESET",
                    "HDMI",
                    "BREATHING",
                    "TIMECODE",
                ):
                    self.assertEqual(hits[lbl], 1)
            self.assertEqual(audit["fx3_bk4"]["window_hits"]["BK4"], 1)
            self.assertEqual(audit["fx6_bk4"]["window_hits"]["BK4"], 1)
            self.assertEqual(audit["fx3_libmpr"]["window_hits"]["XAVC"], 1)
            self.assertEqual(audit["fx6_libmpr"]["window_hits"]["MXF"], 1)

    def test_08_compact_shared_libs_elf64_and_hdmi_audio_markers(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key in (
                "fx3_imdb",
                "fx3_usb_bus_power",
                "fx3_msc_server",
                "fx3_media_cfg",
                "fx3_adj_media",
            ):
                self.assertTrue(audit[key]["elf64_le_ok"])
            self.assertEqual(audit["fx3_adj_media"]["marker_hits"]["AVBB_SCN_START_HDMI"], 1)
            self.assertEqual(audit["fx3_adj_media"]["marker_hits"]["AUDIO"], 1)

    def test_09_env_force_clean_room_sentinel_resolution(self) -> None:
        env = {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        self.assertTrue(p262.is_forced_clean_room(env))
        paths = p262.resolve_phase262_donor_paths(env=env)
        self.assertEqual(len(paths), 15)
        for p in paths.values():
            self.assertIn(p262.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_10_nonexistent_work_root_falls_back_to_clean_room(self) -> None:
        with unittest.mock.patch.object(
            p262, "_iter_work_roots", return_value=(Path("/nonexistent_wave41_stage51_root"),)
        ):
            da = p262.inspect_phase262_donors(force_clean_room=False, env={})
        self.assertEqual(da.source_mode, p262.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(da.all_contracts_verified)

    def test_11_local_donor_opens_strictly_o_rdonly(self) -> None:
        if p262.is_forced_clean_room():
            da = p262.inspect_phase262_donors(force_clean_room=True)
            self.assertEqual(da.access_mode, "O_RDONLY")
            return
        seen_flags: list[int] = []
        real_open = os.open

        def _spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)

        saved_cache = dict(p262._DONOR_AUDIT_CACHE)
        try:
            p262._DONOR_AUDIT_CACHE.clear()
            with unittest.mock.patch("os.open", side_effect=_spy_open):
                da = p262.inspect_phase262_donors(force_clean_room=False)
            if da.source_mode == p262.SOURCE_MODE_LOCAL_DONOR:
                self.assertGreaterEqual(len(seen_flags), 15)
                for fl in seen_flags:
                    self.assertEqual(fl, os.O_RDONLY)
        finally:
            p262._DONOR_AUDIT_CACHE.clear()
            p262._DONOR_AUDIT_CACHE.update(saved_cache)

    def test_12_serialized_payload_leaks_zero_proprietary_firmware_bytes(self) -> None:
        blob = json.dumps(self.default_audit)
        self.assertNotIn("\\x7fELF", blob)
        self.assertEqual(self.default_audit["redlines"]["raw_firmware_bytes_leaked"], 0)
        for k, summ in self.default_audit["donor_audit"].items():
            if isinstance(summ, dict) and "sha256_prefix16" in summ:
                self.assertEqual(len(summ["sha256_prefix16"]), 16)
            if isinstance(summ, dict) and "head_sha256_prefix16" in summ:
                self.assertEqual(len(summ["head_sha256_prefix16"]), 16)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 51A — [Auto Slow Shutter] 6-Condition Lockout &
    #          Ver. 7.02 [Shutter Angle] Disjointness (18 tests: 13..30)
    # ------------------------------------------------------------------
    def test_13_auto_slow_shutter_menu_path_and_factory_default_on_engages_low_light(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(ambient_lux=5.0)
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.menu_path,
            "MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]",
        )
        self.assertEqual(res.effective_auto_slow_shutter_register, "On")
        self.assertTrue(res.auto_slow_shutter_functionally_available)
        self.assertTrue(res.auto_slow_shutter_engaged)
        self.assertEqual(res.effective_shutter_speed, "1/30")
        self.assertEqual(res.active_lockout_reasons, ())

    def test_14_auto_slow_shutter_bright_light_nominal_and_pal_50p_slows_to_1_25(self) -> None:
        bright = p262.simulate_auto_slow_shutter_hil(ambient_lux=100.0, frame_rate="59.94p")
        self.assertTrue(bright.admitted)
        self.assertTrue(bright.auto_slow_shutter_functionally_available)
        self.assertFalse(bright.auto_slow_shutter_engaged)
        self.assertEqual(bright.effective_shutter_speed, "1/60")

        pal_dark = p262.simulate_auto_slow_shutter_hil(ambient_lux=4.0, frame_rate="50p")
        self.assertTrue(pal_dark.auto_slow_shutter_engaged)
        self.assertEqual(pal_dark.effective_shutter_speed, "1/25")

    def test_15_auto_slow_shutter_explicit_off_stays_nominal_in_dark_scene(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            configured_auto_slow_shutter="Off",
            ambient_lux=3.0,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_auto_slow_shutter_register, "Off")
        self.assertFalse(res.auto_slow_shutter_functionally_available)
        self.assertFalse(res.auto_slow_shutter_engaged)
        self.assertEqual(res.effective_shutter_speed, "1/60")

    def test_16_lockout_1_sq_shooting_disables_auto_slow_shutter(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(shooting_mode="S&Q", ambient_lux=2.0)
        self.assertTrue(res.admitted)
        self.assertIn(p262.LOCKOUT_1_SQ_SHOOTING, res.active_lockout_reasons)
        self.assertFalse(res.auto_slow_shutter_functionally_available)
        self.assertFalse(res.auto_slow_shutter_engaged)

    def test_17_lockout_2_shutter_priority_disables_auto_slow_shutter(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            exposure_ctrl_type="P/A/S/M Mode",
            exposure_mode="Shutter Priority",
            ambient_lux=2.0,
        )
        self.assertTrue(res.admitted)
        self.assertIn(p262.LOCKOUT_2_SHUTTER_PRIORITY_S, res.active_lockout_reasons)
        self.assertFalse(res.auto_slow_shutter_functionally_available)
        self.assertFalse(res.auto_slow_shutter_engaged)

    def test_18_lockout_3_manual_exposure_disables_auto_slow_shutter(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            exposure_ctrl_type="P/A/S/M Mode",
            exposure_mode="Manual Exposure",
            ambient_lux=2.0,
        )
        self.assertTrue(res.admitted)
        self.assertIn(p262.LOCKOUT_3_MANUAL_EXPOSURE_M, res.active_lockout_reasons)
        self.assertFalse(res.auto_slow_shutter_functionally_available)
        self.assertFalse(res.auto_slow_shutter_engaged)

    def test_19_lockout_4_fixed_iso_other_than_iso_auto_disables_auto_slow_shutter(self) -> None:
        for fixed_iso in ("ISO 800", "ISO 1600", "ISO 12800"):
            res = p262.simulate_auto_slow_shutter_hil(iso_setting=fixed_iso, ambient_lux=2.0)
            self.assertTrue(res.admitted)
            self.assertIn(p262.LOCKOUT_4_ISO_NOT_AUTO, res.active_lockout_reasons)
            self.assertFalse(res.auto_slow_shutter_engaged)

    def test_20_lockout_5_flexible_exp_manual_shutter_vs_auto_shutter(self) -> None:
        locked = p262.simulate_auto_slow_shutter_hil(
            exposure_ctrl_type="Flexible Exp. Mode",
            flex_shutter_auto_manual="Manual",
            iso_setting="ISO AUTO",
            ambient_lux=2.0,
        )
        self.assertIn(p262.LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER, locked.active_lockout_reasons)
        self.assertFalse(locked.auto_slow_shutter_engaged)

        allowed = p262.simulate_auto_slow_shutter_hil(
            exposure_ctrl_type="Flexible Exp. Mode",
            flex_shutter_auto_manual="Auto",
            iso_setting="ISO AUTO",
            log_shooting_mode="Flexible ISO",
            ambient_lux=2.0,
        )
        self.assertEqual(allowed.active_lockout_reasons, ())
        self.assertTrue(allowed.auto_slow_shutter_engaged)

    def test_21_lockout_6_cine_ei_and_cine_ei_quick_disable_auto_slow_shutter(self) -> None:
        for mode in ("Cine EI Quick", "Cine EI"):
            res = p262.simulate_auto_slow_shutter_hil(log_shooting_mode=mode, ambient_lux=2.0)
            self.assertIn(p262.LOCKOUT_6_LOG_SHOOTING_CINE_EI, res.active_lockout_reasons)
            self.assertFalse(res.auto_slow_shutter_functionally_available)
            self.assertFalse(res.auto_slow_shutter_engaged)

    def test_22_multiple_simultaneous_lockout_conditions_enumerated(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            shooting_mode="S&Q",
            exposure_ctrl_type="P/A/S/M Mode",
            exposure_mode="Manual Exposure",
            iso_setting="ISO 800",
            log_shooting_mode="Cine EI",
            ambient_lux=1.0,
        )
        self.assertEqual(
            res.active_lockout_reasons,
            (
                p262.LOCKOUT_1_SQ_SHOOTING,
                p262.LOCKOUT_3_MANUAL_EXPOSURE_M,
                p262.LOCKOUT_4_ISO_NOT_AUTO,
                p262.LOCKOUT_6_LOG_SHOOTING_CINE_EI,
            ),
        )
        self.assertFalse(res.auto_slow_shutter_engaged)

    def test_23_still_shooting_mode_does_not_engage_movie_auto_slow_shutter(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(shooting_mode="Still", ambient_lux=2.0)
        self.assertTrue(res.admitted)
        self.assertFalse(res.auto_slow_shutter_functionally_available)
        self.assertFalse(res.auto_slow_shutter_engaged)

    def test_24_auto_slow_shutter_reset_scope_camera_reset_vs_network_reset_vs_initialize(self) -> None:
        csr = p262.simulate_auto_slow_shutter_hil(
            configured_auto_slow_shutter="Off",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(csr.restored_by_camera_settings_reset)
        self.assertEqual(csr.effective_auto_slow_shutter_register, "On")

        net = p262.simulate_auto_slow_shutter_hil(
            configured_auto_slow_shutter="Off",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(net.survived_reset_network_set)
        self.assertEqual(net.effective_auto_slow_shutter_register, "Off")

        init = p262.simulate_auto_slow_shutter_hil(
            configured_auto_slow_shutter="Off",
            reset_action="Initialize",
        )
        self.assertTrue(init.restored_by_initialize)
        self.assertEqual(init.effective_auto_slow_shutter_register, "On")

    def test_25_ver702_shutter_angle_governs_manual_shutter_and_pre600_blocked(self) -> None:
        v702 = p262.simulate_auto_slow_shutter_hil(
            firmware_version="7.02",
            exposure_mode="Manual Exposure",
            shutter_mode="Angle",
            shutter_angle="180.0 deg",
        )
        self.assertTrue(v702.admitted)
        self.assertTrue(v702.shutter_angle_governing_exposure)
        self.assertFalse(v702.auto_slow_shutter_functionally_available)
        self.assertEqual(v702.effective_shutter_speed, "180.0 deg")

        v500 = p262.simulate_auto_slow_shutter_hil(
            firmware_version="5.00",
            exposure_mode="Manual Exposure",
            shutter_mode="Angle",
        )
        self.assertFalse(v500.admitted)
        self.assertEqual(v500.errno_code, p262.EOPNOTSUPP_ERRNO)

    def test_26_exhaustive_768_state_disjointness_matrix_zero_overlap(self) -> None:
        mat = p262.compute_auto_slow_shutter_angle_disjointness_matrix()
        self.assertEqual(mat["total_states_evaluated"], 768)
        self.assertGreater(mat["auto_slow_shutter_active_states"], 0)
        self.assertGreater(mat["shutter_angle_active_states"], 0)
        self.assertEqual(mat["overlap_states"], 0)
        self.assertTrue(mat["strictly_disjoint"])

    def test_27_forced_auto_slow_shutter_lockout_bypass_blocked_eacces(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            log_shooting_mode="Cine EI",
            force_bypass_auto_slow_shutter_lockout=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p262.EACCES_ERRNO)
        self.assertEqual(res.auto_slow_shutter_lockout_bypass_events, 0)

    def test_28_forced_shutter_angle_overlap_blocked_einval(self) -> None:
        res = p262.simulate_auto_slow_shutter_hil(
            exposure_mode="Manual Exposure",
            shutter_mode="Angle",
            force_shutter_angle_overlap=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p262.EINVAL_ERRNO)
        self.assertEqual(res.auto_slow_shutter_angle_overlap_events, 0)

    def test_29_invalid_auto_slow_shutter_parameters_rejected_einval(self) -> None:
        bad = p262.simulate_auto_slow_shutter_hil(configured_auto_slow_shutter="AutoBogus")
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p262.EINVAL_ERRNO)

    def test_30_pillar_a_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pa = rep["pillar_a_auto_slow_shutter_6locks_and_angle_disjoint_hil"]
            self.assertTrue(pa["passed"])
            self.assertEqual(len(pa["all_6_lockout_ids"]), 6)
            self.assertEqual(pa["disjointness_768_state_matrix"]["overlap_states"], 0)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 51B — [HDMI Output Settings] REC Control <- Time Code
    #          Output Gate, 4ch Audio Output & Slot-1 Vault Guard (14 tests: 31..44)
    # ------------------------------------------------------------------
    def test_31_hdmi_output_settings_menu_path_and_factory_defaults(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.menu_path,
            "MENU -> Setup -> [External Output] -> [HDMI Output Settings]",
        )
        self.assertEqual(res.effective_time_code_output, "Off")
        self.assertEqual(res.effective_rec_control, "Off")
        self.assertEqual(res.effective_hdmi_4ch_audio_output, "CH1/CH2")
        self.assertEqual(res.effective_rec_media_dur_hdmi_output, "On")

    def test_32_hdmi_rec_control_rejected_when_time_code_output_is_off(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="Off",
            configured_rec_control="On",
            strict_menu_set_rec_ctrl=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p262.EACCES_ERRNO)
        self.assertEqual(res.effective_rec_control, "Off")
        self.assertEqual(res.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_33_hdmi_rec_control_admitted_and_triggers_recorder_when_tc_output_on(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            camera_rec_button_pressed=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.rec_control_prerequisite_tc_satisfied)
        self.assertEqual(res.effective_rec_control, "On")
        self.assertTrue(res.external_recorder_rec_trigger_emitted)
        self.assertEqual(res.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_34_turning_time_code_output_off_auto_disables_rec_control(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            transition_tc_output_to_off=True,
            camera_rec_button_pressed=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_time_code_output, "Off")
        self.assertEqual(res.effective_rec_control, "Off")
        self.assertFalse(res.external_recorder_rec_trigger_emitted)
        self.assertEqual(res.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_35_non_strict_persisted_state_clamps_rec_control_off_when_tc_off(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="Off",
            configured_rec_control="On",
            strict_menu_set_rec_ctrl=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_rec_control, "Off")
        self.assertEqual(res.reason_code, "HDMI_REC_CTRL_AUTO_DISABLED_WHEN_TC_OFF")

    def test_36_hdmi_4ch_audio_output_ch1_ch2_routing_with_mishoe(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_hdmi_4ch_audio_output="CH1/CH2",
            mi_shoe_4ch_audio_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.hdmi_4ch_routing_active)
        self.assertEqual(res.hdmi_routed_audio_pair, ("CH1_L", "CH2_R"))

    def test_37_hdmi_4ch_audio_output_ch3_ch4_routing_and_2ch_fallback_without_mishoe(self) -> None:
        active = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_hdmi_4ch_audio_output="CH3/CH4",
            mi_shoe_4ch_audio_active=True,
        )
        self.assertTrue(active.hdmi_4ch_routing_active)
        self.assertEqual(active.hdmi_routed_audio_pair, ("CH3_L", "CH4_R"))

        fallback = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_hdmi_4ch_audio_output="CH3/CH4",
            mi_shoe_4ch_audio_active=False,
        )
        self.assertFalse(fallback.hdmi_4ch_routing_active)
        self.assertEqual(fallback.hdmi_routed_audio_pair, ("CH1_L", "CH2_R"))

    def test_38_rec_media_dur_hdmi_output_off_inhibits_cards_and_proxy_writes(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            configured_rec_media_dur_hdmi_output="Off",
            proxy_recording_requested=True,
            camera_rec_button_pressed=True,
            slot1_is_tier0_recovery_vault=False,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.external_recorder_rec_trigger_emitted)
        self.assertFalse(res.internal_slot1_clip_recording_active)
        self.assertFalse(res.internal_slot2_clip_recording_active)
        self.assertFalse(res.internal_proxy_recording_active)
        self.assertEqual(res.slot1_hdmi_rec_vault_mutation_bytes, 0)

    def test_39_rec_media_dur_hdmi_on_protects_slot1_vault_while_slot2_records(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_rec_media_dur_hdmi_output="On",
            proxy_recording_requested=True,
            camera_rec_button_pressed=True,
            slot1_is_tier0_recovery_vault=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.internal_slot1_clip_recording_active)
        self.assertTrue(res.internal_slot2_clip_recording_active)
        self.assertTrue(res.internal_proxy_recording_active)
        self.assertEqual(res.slot1_hdmi_rec_vault_mutation_bytes, 0)

    def test_40_hdmi_output_settings_survive_camera_and_network_reset_cleared_by_initialize(self) -> None:
        csr = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            configured_hdmi_4ch_audio_output="CH3/CH4",
            configured_rec_media_dur_hdmi_output="Off",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(csr.survived_camera_settings_reset)
        self.assertEqual(csr.effective_rec_control, "On")
        self.assertEqual(csr.effective_hdmi_4ch_audio_output, "CH3/CH4")
        self.assertEqual(csr.effective_rec_media_dur_hdmi_output, "Off")

        net = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            configured_hdmi_4ch_audio_output="CH3/CH4",
            configured_rec_media_dur_hdmi_output="Off",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(net.survived_reset_network_set)
        self.assertEqual(net.effective_rec_control, "On")

        init = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_time_code_output="On",
            configured_rec_control="On",
            configured_hdmi_4ch_audio_output="CH3/CH4",
            configured_rec_media_dur_hdmi_output="Off",
            reset_action="Initialize",
        )
        self.assertTrue(init.restored_by_initialize)
        self.assertEqual(init.effective_time_code_output, "Off")
        self.assertEqual(init.effective_rec_control, "Off")
        self.assertEqual(init.effective_hdmi_4ch_audio_output, "CH1/CH2")
        self.assertEqual(init.effective_rec_media_dur_hdmi_output, "On")

    def test_41_forced_slot1_tier0_vault_hdmi_rec_write_blocked_erofs(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            force_slot1_vault_hdmi_rec_write=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p262.EROFS_ERRNO)
        self.assertEqual(res.slot1_hdmi_rec_vault_mutation_bytes, 0)

    def test_42_forced_hdmi_rec_ctrl_without_tc_bypass_blocked_eacces(self) -> None:
        res = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            force_rec_ctrl_without_tc_bypass=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p262.EACCES_ERRNO)
        self.assertEqual(res.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_43_invalid_hdmi_output_settings_parameters_rejected_einval(self) -> None:
        bad = p262.simulate_hdmi_output_reccontrol_4chaudio_hil(
            configured_hdmi_4ch_audio_output="CH5/CH6",
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p262.EINVAL_ERRNO)

    def test_44_pillar_b_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pb = rep["pillar_b_hdmi_reccontrol_tcout_4chaudio_and_vault_hil"]
            self.assertTrue(pb["passed"])
            self.assertEqual(pb["all_2_hdmi_4ch_audio_modes"], ["CH1/CH2", "CH3/CH4"])

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 51C & Redlines — [Lens Compensation] -> [Breathing
    #          Comp.] & 15-Field Redline Guard (13 tests: 45..57)
    # ------------------------------------------------------------------
    def test_45_breathing_comp_menu_path_and_factory_default_off_uncropped(self) -> None:
        res = p262.simulate_breathing_comp_lens_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.menu_path,
            "MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]",
        )
        self.assertEqual(res.effective_breathing_comp_register, "Off")
        self.assertFalse(res.effective_breathing_comp_applied)
        self.assertEqual(res.fov_crop_factor, 1.0)
        self.assertTrue(res.still_image_untouched)

    def test_46_compliant_sony_emount_lenses_apply_movie_fov_crop_when_on(self) -> None:
        for lens_id, expected_crop in p262.COMPLIANT_BREATHING_EMOUNT_LENSES.items():
            res = p262.simulate_breathing_comp_lens_hil(
                configured_breathing_comp="On",
                shooting_scope="Movie",
                attached_lens_id=lens_id,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.lens_is_breathing_compliant)
            self.assertTrue(res.effective_breathing_comp_applied)
            self.assertEqual(res.fov_crop_factor, expected_crop)

    def test_47_still_shooting_scope_never_applies_breathing_comp_crop(self) -> None:
        res = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            shooting_scope="Still",
            attached_lens_id="SEL2470GM2",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.effective_breathing_comp_applied)
        self.assertEqual(res.fov_crop_factor, 1.0)
        self.assertTrue(res.still_image_untouched)

    def test_48_non_compliant_and_manual_adapter_lenses_stay_uncropped(self) -> None:
        for lens_id in p262.NON_COMPLIANT_EMOUNT_LENSES:
            res = p262.simulate_breathing_comp_lens_hil(
                configured_breathing_comp="On",
                shooting_scope="Movie",
                attached_lens_id=lens_id,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.lens_is_breathing_compliant)
            self.assertFalse(res.effective_breathing_comp_applied)
            self.assertEqual(res.fov_crop_factor, 1.0)

    def test_49_sq_11988p_allowed_vs_sq_23976p_and_200p_locked_out(self) -> None:
        sq120 = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            shooting_scope="S&Q",
            attached_lens_id="SEL50F12GM",
            frame_rate="119.88p",
        )
        self.assertTrue(sq120.effective_breathing_comp_applied)
        self.assertEqual(sq120.fov_crop_factor, 1.08)

        for hfr in ("239.76p", "200p"):
            locked = p262.simulate_breathing_comp_lens_hil(
                configured_breathing_comp="On",
                shooting_scope="S&Q",
                attached_lens_id="SEL50F12GM",
                frame_rate=hfr,
            )
            self.assertTrue(locked.admitted)
            self.assertTrue(locked.breathing_comp_locked_out)
            self.assertFalse(locked.effective_breathing_comp_applied)
            self.assertEqual(locked.fov_crop_factor, 1.0)

    def test_50_hdmi_raw_4264x2408_output_locks_out_breathing_comp(self) -> None:
        res = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            shooting_scope="Movie",
            attached_lens_id="SEL2470GM2",
            hdmi_raw_output_on=True,
            raw_resolution="4264x2408",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.breathing_comp_locked_out)
        self.assertIn("HDMI_RAW_4264X2408_OUTPUT_ACTIVE", res.active_breathing_lockout_reasons)
        self.assertFalse(res.effective_breathing_comp_applied)
        self.assertEqual(res.fov_crop_factor, 1.0)

    def test_51_pre_ver300_firmware_rejects_breathing_comp_on_eopnotsupp(self) -> None:
        v200 = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            firmware_version="2.00",
        )
        self.assertFalse(v200.admitted)
        self.assertEqual(v200.errno_code, p262.EOPNOTSUPP_ERRNO)

        v300 = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            firmware_version="3.00",
        )
        self.assertTrue(v300.admitted)
        self.assertTrue(v300.effective_breathing_comp_applied)

    def test_52_breathing_comp_reset_scope_camera_reset_vs_network_reset_vs_initialize(self) -> None:
        csr = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(csr.restored_by_camera_settings_reset)
        self.assertEqual(csr.effective_breathing_comp_register, "Off")
        self.assertFalse(csr.effective_breathing_comp_applied)

        net = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(net.survived_reset_network_set)
        self.assertEqual(net.effective_breathing_comp_register, "On")
        self.assertTrue(net.effective_breathing_comp_applied)

        init = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            reset_action="Initialize",
        )
        self.assertTrue(init.restored_by_initialize)
        self.assertEqual(init.effective_breathing_comp_register, "Off")

    def test_53_forced_bypass_of_raw_or_240p_lockout_blocked_eacces(self) -> None:
        raw_byp = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            hdmi_raw_output_on=True,
            force_bypass_breathing_raw_or_240p_lockout=True,
        )
        self.assertFalse(raw_byp.admitted)
        self.assertEqual(raw_byp.errno_code, p262.EACCES_ERRNO)
        self.assertEqual(raw_byp.breathing_comp_raw_or_240p_bypass_events, 0)

        sq_byp = p262.simulate_breathing_comp_lens_hil(
            configured_breathing_comp="On",
            shooting_scope="S&Q",
            frame_rate="239.76p",
            force_bypass_breathing_raw_or_240p_lockout=True,
        )
        self.assertFalse(sq_byp.admitted)
        self.assertEqual(sq_byp.errno_code, p262.EACCES_ERRNO)
        self.assertEqual(sq_byp.breathing_comp_raw_or_240p_bypass_events, 0)

    def test_54_invalid_breathing_comp_parameters_rejected_einval(self) -> None:
        bad = p262.simulate_breathing_comp_lens_hil(attached_lens_id="UNKNOWN_LENS")
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p262.EINVAL_ERRNO)

    def test_55_baseline_redline_guard_valid_and_zero_faults(self) -> None:
        pr = p262.probe_phase262_redline_guard()
        self.assertTrue(pr.valid)
        self.assertEqual(pr.errno_code, 0)
        self.assertEqual(pr.reason_code, "REDLINES_INTACT")
        self.assertFalse(pr.persistent_emmc_writes_authorized)
        self.assertFalse(pr.hardware_live_attachment_authorized)
        self.assertFalse(pr.overall_ready_for_hardware_attach)
        self.assertTrue(pr.cnflasha_userspace_write_blocked)

    def test_56_all_15_stage51_redline_probes_individually_blocked_eacces_or_erofs(self) -> None:
        self.assertEqual(len(p262.ALL_15_REDLINE_PROBE_FIELDS), 15)
        for field in p262.ALL_15_REDLINE_PROBE_FIELDS:
            pr = p262.probe_phase262_redline_guard(**{field: True})
            self.assertFalse(pr.valid)
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_hdmi_rec_vault_write_requested",
            ):
                self.assertEqual(pr.errno_code, p262.EROFS_ERRNO)
            else:
                self.assertEqual(pr.errno_code, p262.EACCES_ERRNO)
        bad = p262.probe_phase262_redline_guard(bogus_stage51_probe=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p262.EINVAL_ERRNO)

    def test_57_pillar_c_d_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pcd = rep["pillar_c_d_breathing_comp_and_redlines"]
            self.assertTrue(pcd["passed"])
            self.assertEqual(len(pcd["all_15_redline_probe_fields"]), 15)

    # ------------------------------------------------------------------
    # Group 5: CLI, 51/51 Suite Integration & Hygiene (9 tests: 58..66)
    # ------------------------------------------------------------------
    def test_58_standalone_cli_json_and_summary_in_process_both_modes(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc1 = p262.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc1, 0)
        self.assertIn("[PASS] Phase 262 Stage 51 (51/51)", buf_sum.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p262.main(["--self-test", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["milestone"], "51/51")

    def test_59_standalone_subprocess_cli_clean_room_and_default_pass(self) -> None:
        script = str(FX3_VM_DIR / "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py")
        env_clean = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", FX3_FX6_FORCE_CLEAN_ROOM="1")
        p_clean = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env_clean,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 262 Stage 51 (51/51)", p_clean.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", p_clean.stdout)

    def test_60_fx3_vm_coemulation_suite_includes_stage51_51_of_51(self) -> None:
        self.assertTrue(self.clean_suite["all_checks_passed"])
        self.assertIn(
            "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
            self.clean_suite,
        )
        s51 = self.clean_suite["stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil"]
        self.assertTrue(s51["all_checks_passed"])
        self.assertEqual(s51["phase_number"], 262)
        self.assertEqual(s51["milestone"], "51/51")
        self.assertEqual(
            s51["schema"],
            "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1",
        )
        self.assertEqual(s51["auto_slow_shutter_lockout_bypass_events"], 0)
        self.assertEqual(s51["auto_slow_shutter_angle_overlap_events"], 0)
        self.assertEqual(s51["hdmi_rec_ctrl_without_tc_violations"], 0)
        self.assertEqual(s51["slot1_hdmi_rec_vault_mutation_bytes"], 0)
        self.assertEqual(s51["breathing_comp_raw_or_240p_bypass_events"], 0)
        self.assertEqual(s51["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in self.default_suite if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 51)
        self.assertLess(self.clean_suite_elapsed, 4.0)

    def test_61_fx3_vm_coemulation_suite_all_51_stage_indices_1_to_51_unique_and_present(self) -> None:
        self.assertTrue(self.default_suite["all_checks_passed"])
        for idx in range(1, 52):
            matches = [k for k in self.default_suite if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(self.default_suite_elapsed, 4.0)

    def test_62_fx3_vm_coemulation_suite_skip_stage51_and_skip_phase262_config(self) -> None:
        rep_skip_p262 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                **_fast_suite_kwargs(
                    include_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil=False
                )
            )
        )
        self.assertTrue(rep_skip_p262["all_checks_passed"])
        self.assertNotIn(
            "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
            rep_skip_p262,
        )
        self.assertFalse(rep_skip_p262["config"]["include_stage51"])

        rep_skip_s51 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(include_stage51=False))
        )
        self.assertTrue(rep_skip_s51["all_checks_passed"])
        self.assertNotIn(
            "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
            rep_skip_s51,
        )

    def test_63_fx3_vm_coemulation_suite_include_stage51_cli_summary(self) -> None:
        fast_flags = [
            "--clean-room",
            "--skip-phase41",
            "--skip-phase45",
            "--skip-phase53",
            "--skip-phase58",
            "--skip-phase63",
            "--skip-phase67",
            "--skip-phase71",
            "--skip-phase78",
            "--skip-phase82",
            "--skip-phase87",
            "--skip-phase91",
            "--skip-phase96",
            "--skip-phase99",
            "--skip-phase103",
            "--skip-phase107",
            "--skip-phase112",
            "--skip-phase117",
            "--skip-phase121",
            "--skip-phase127",
            "--skip-phase132",
            "--skip-phase141",
            "--skip-phase145",
            "--skip-phase150",
            "--skip-phase157",
            "--skip-phase162",
            "--skip-phase167",
            "--skip-phase172",
            "--skip-phase178",
            "--skip-phase182",
            "--skip-phase188",
            "--skip-phase194",
            "--skip-phase200",
            "--skip-phase202",
            "--skip-phase207",
            "--skip-phase213",
            "--skip-phase217",
            "--skip-phase222",
            "--skip-phase226",
            "--skip-phase232",
            "--skip-phase236",
            "--skip-stage44",
            "--skip-stage45",
            "--skip-stage46",
            "--skip-stage47",
            "--skip-stage48",
            "--skip-stage49",
            "--skip-stage50",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage51", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_64_fx3_vm_coemulation_suite_cli_skip_phase262_and_skip_stage51(self) -> None:
        fast_flags = [
            "--clean-room",
            "--skip-phase41",
            "--skip-phase45",
            "--skip-phase53",
            "--skip-phase58",
            "--skip-phase63",
            "--skip-phase67",
            "--skip-phase71",
            "--skip-phase78",
            "--skip-phase82",
            "--skip-phase87",
            "--skip-phase91",
            "--skip-phase96",
            "--skip-phase99",
            "--skip-phase103",
            "--skip-phase107",
            "--skip-phase112",
            "--skip-phase117",
            "--skip-phase121",
            "--skip-phase127",
            "--skip-phase132",
            "--skip-phase141",
            "--skip-phase145",
            "--skip-phase150",
            "--skip-phase157",
            "--skip-phase162",
            "--skip-phase167",
            "--skip-phase172",
            "--skip-phase178",
            "--skip-phase182",
            "--skip-phase188",
            "--skip-phase194",
            "--skip-phase200",
            "--skip-phase202",
            "--skip-phase207",
            "--skip-phase213",
            "--skip-phase217",
            "--skip-phase222",
            "--skip-phase226",
            "--skip-phase232",
            "--skip-phase236",
            "--skip-stage44",
            "--skip-stage45",
            "--skip-stage46",
            "--skip-stage47",
            "--skip-stage48",
            "--skip-stage49",
            "--skip-stage50",
        ]
        for flag in ("--skip-phase262", "--skip-stage51", "--no-include-stage51"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil",
                rep,
            )

    def test_65_all_safety_and_byof_redlines_locked_across_stage51_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            r = rep["redlines"]
            self.assertFalse(r["persistent_emmc_writes_authorized"])
            self.assertFalse(r["hardware_live_attachment_authorized"])
            self.assertFalse(r["overall_ready_for_hardware_attach"])
            self.assertFalse(r["isp_write_authorized"])
            self.assertFalse(r["spi_nor_write_authorized"])
            self.assertFalse(r["el3_payload_transmit_authorized"])
            self.assertTrue(r["cnflasha_userspace_write_blocked"])
            self.assertEqual(r["physical_device_writes"], 0)
            self.assertEqual(r["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(r["nop_count"], 0)
            self.assertEqual(r["guest_code_modification_bytes"], 0)

    def test_66_zero_bytecode_or_pycache_artifacts_in_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        pycache_dirs = list(FX3_VM_DIR.rglob("__pycache__"))
        self.assertEqual(pyc_files, [])
        self.assertEqual(pycache_dirs, [])


if __name__ == "__main__":
    unittest.main()
