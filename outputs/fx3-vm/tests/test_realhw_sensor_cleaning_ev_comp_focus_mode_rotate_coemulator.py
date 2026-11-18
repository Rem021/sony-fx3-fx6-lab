#!/usr/bin/env python3
"""Unit tests for Phase 306 (Stage 62 — 62/62 VM Stages Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-52
`[Sensor Cleaning]` >= 51%% NP-FZ100 Battery Gate + Mandatory Physical Power-OFF vs IBIS-less
FX6 e-ND & Technical > APR,
`[Exposure Comp.]` +-5.0 EV Still / +-2.0 EV Movie & S&Q + Total `[Cine EI]` Lockout +
Initialize-only `[Exposure step]`,
`[Focus Mode]` 5-Still vs 2-Movie/S&Q Split + `[Priority Set in AF-S/AF-C]` + `[AF Assist]` /
`[AF Illuminator]`, and
Playback `[View Mode]`, Exact `9`/`25` `[Image Index]`, `[Display as Group]`, `[Display Rotation]`,
and `[Rotate]` Slot-1 Tier-0 Recovery Vault Firewall HIL Co-Emulator (88 dual-mode tests).
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
import realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator as p306  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated stages for quick flag/override tests."""
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
        include_stage51=False,
        include_stage52=False,
        include_stage53=False,
        include_stage54=False,
        include_stage55=False,
        include_stage56=False,
        include_stage57=False,
        include_stage58=False,
        include_stage59=False,
        include_stage60=False,
        include_stage61=False,
    )
    base.update(overrides)
    return base


_FAST_CLI_FLAGS = [
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
    "--skip-stage51",
    "--skip-stage52",
    "--skip-stage53",
    "--skip-stage54",
    "--skip-stage55",
    "--skip-stage56",
    "--skip-stage57",
    "--skip-stage58",
    "--skip-stage59",
    "--skip-stage60",
    "--skip-stage61",
]


class TestPhase306DonorInspection(unittest.TestCase):
    """Dual-mode 11-donor O_RDONLY & clean-room verification tests."""

    def test_01_schema_and_milestone_constants(self) -> None:
        self.assertEqual(
            p306.SCHEMA_ID,
            "realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator_v1",
        )
        self.assertEqual(p306.PHASE_NUMBER, 306)
        self.assertEqual(p306.STAGE_INDEX, 62)
        self.assertEqual(p306.STAGE_TOTAL, 62)
        self.assertEqual(p306.MILESTONE_LABEL, "62/62")
        self.assertEqual(p306.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p306.BOUNDED_WINDOW_MAX_BYTES, 4096)

    def test_02_donor_audit_current_mode_11_donors(self) -> None:
        audit = p306.inspect_phase306_donors()
        self.assertTrue(audit.all_contracts_verified, audit.errors)
        self.assertEqual(audit.donor_files_inspected, 11)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertIn(
            audit.source_mode,
            (p306.SOURCE_MODE_LOCAL_DONOR, p306.SOURCE_MODE_CLEAN_ROOM),
        )
        self.assertTrue(audit.sensor_cleaning_apr_end_proven)
        self.assertTrue(audit.ev_comp_cine_ei_proven)
        self.assertTrue(audit.focus_mode_priority_split_proven)
        self.assertTrue(audit.playback_view_index_rotate_proven)
        max_elapsed = 15.0 if IS_CI else 2.0
        self.assertLess(audit.inspection_elapsed_s, max_elapsed)

    def test_03_force_clean_room_both_env_vars(self) -> None:
        for env_key in (p306.ENV_CLEAN_ROOM_TEST, p306.ENV_FORCE_CLEAN_ROOM):
            audit = p306.inspect_phase306_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p306.SOURCE_MODE_CLEAN_ROOM)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_missing_donor_dir_falls_back_clean_room(self) -> None:
        audit = p306.inspect_phase306_donors(
            env={p306.ENV_MAC_WORK_ROOT: "/nonexistent/fx3/__missing__"}
        )
        self.assertEqual(audit.source_mode, p306.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_compact_donor_byte_lengths_and_sha_prefixes(self) -> None:
        audit = p306.inspect_phase306_donors()
        for attr in (
            "fx3_string_en_f",
            "fx3_string_sc_f",
            "fx3_string_tc_f",
            "fx3_string_ja_f",
            "fx3_string_en",
            "fx3_string_en_g",
            "fx6_string_en",
            "fx6_string_en_2",
        ):
            item = getattr(audit, attr)
            self.assertEqual(item.byte_length, p306.EXPECTED_DONOR_BYTES[attr])
            self.assertTrue(item.sha256_verified)
            self.assertTrue(item.uxc_container_ok)
            self.assertTrue(all(v == 1 for v in item.marker_hits.values()))

    def test_06_large_donor_elf64_bk4_headers_and_windows(self) -> None:
        audit = p306.inspect_phase306_donors()
        for attr in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
            item = getattr(audit, attr)
            self.assertEqual(item.byte_length, p306.EXPECTED_DONOR_BYTES[attr])
            self.assertTrue(item.head_sha256_verified)
            self.assertTrue(item.elf64_le_ok)
            self.assertTrue(all(v == 1 for v in item.window_hits.values()))

    def test_07_bounded_o_rdonly_rejects_oversized_window(self) -> None:
        with self.assertRaises(ValueError):
            p306._read_bounded_o_rdonly(Path(__file__), 0, p306.BOUNDED_WINDOW_MAX_BYTES + 1)

    def test_08_o_rdonly_strictly_read_only_when_local_donors_present(self) -> None:
        if p306.is_forced_clean_room():
            self.skipTest("Clean-room forced in environment")
        work_root = p306.resolve_mac_work_root()
        if not (work_root / p306.DONOR_RELPATHS["fx3_string_en_f"]).is_file():
            self.skipTest("Local Mac/work donors absent")
        opened_flags = []
        orig_open = os.open

        def _spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            opened_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)

        with unittest.mock.patch("os.open", side_effect=_spy_open):
            audit = p306.inspect_phase306_donors(force_clean_room=False)
        self.assertEqual(audit.source_mode, p306.SOURCE_MODE_LOCAL_DONOR)
        self.assertGreaterEqual(len(opened_flags), 11)
        for fl in opened_flags:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)


class TestSubModel62ASensorCleaningVsFX6EndApr(unittest.TestCase):
    """62A: [Sensor Cleaning] >= 51% Battery Gate + Mandatory Power-OFF vs FX6 e-ND & APR."""

    def test_09_fx3_50pct_battery_strictly_rejected_0xe574(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(battery_percent=50, request_ibis_shake=True)
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EACCES_ERRNO)
        self.assertEqual(r.uxc_lock_id, "0xe574")
        self.assertFalse(r.ibis_sensor_shake_actuated)

    def test_10_fx3_0pct_and_1pct_rejected_with_zero_writes(self) -> None:
        for pct in (0, 1, 25, 49, 50):
            r = p306.simulate_sensor_cleaning_hil(battery_percent=pct, request_ibis_shake=True)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EACCES_ERRNO)
            self.assertEqual(r.physical_device_writes, 0)

    def test_11_fx3_51pct_exact_threshold_admitted_and_actuates_ibis_shake(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            battery_percent=51,
            request_ibis_shake=True,
            power_switch_turned_off=True,
            lens_detach_requested=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.uxc_prompt_id, "0x67d6")
        self.assertEqual(r.uxc_lock_id, "0x6221")
        self.assertTrue(r.ibis_sensor_shake_actuated)
        self.assertTrue(r.sensor_centered)
        self.assertTrue(r.mandatory_power_off_required)
        self.assertTrue(r.lens_swap_cleared)

    def test_12_fx3_100pct_battery_power_off_cycle_admitted(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            battery_percent=100,
            request_ibis_shake=True,
            power_switch_turned_off=True,
            resume_shooting_requested=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.shooting_resumed)

    def test_13_fx3_lens_detach_without_power_off_blocked_ebusy(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            battery_percent=80,
            request_ibis_shake=True,
            power_switch_turned_off=False,
            lens_detach_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EBUSY_ERRNO)
        self.assertTrue(r.mandatory_power_off_required)
        self.assertFalse(r.lens_swap_cleared)

    def test_14_fx3_resume_shooting_without_power_off_blocked_ebusy(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            battery_percent=80,
            request_ibis_shake=True,
            power_switch_turned_off=False,
            resume_shooting_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EBUSY_ERRNO)
        self.assertFalse(r.shooting_resumed)

    def test_15_fx3_legacy_v1_le_2_bars_rejected_e7d7_e574(self) -> None:
        for bars in (0, 1, 2):
            r = p306.simulate_sensor_cleaning_hil(
                body_profile=p306.BODY_MODEL_FX3_LEGACY_V1,
                battery_percent=60,
                legacy_battery_bars=bars,
                request_ibis_shake=True,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EACCES_ERRNO)
            self.assertEqual(r.uxc_prompt_id, "0xe7d7")
            self.assertEqual(r.uxc_lock_id, "0xe574")

    def test_16_fx3_legacy_v1_3_4_bars_admitted(self) -> None:
        for bars in (3, 4):
            r = p306.simulate_sensor_cleaning_hil(
                body_profile=p306.BODY_MODEL_FX3_LEGACY_V1,
                battery_percent=60,
                legacy_battery_bars=bars,
                request_ibis_shake=True,
                power_switch_turned_off=True,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.uxc_prompt_id, "0xe7d7")

    def test_17_fx6_ibis_less_rejects_ultrasonic_ibis_shake(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            body_profile=p306.BODY_MODEL_FX6,
            request_ibis_shake=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_has_ibis_sensor_shake)
        self.assertEqual(r.fx6_ibis_sensor_shake_spoof_events, 0)

    def test_18_fx6_variable_e_nd_all_stops_plus_apr_admitted(self) -> None:
        for stop in p306.FX6_END_STOPS:
            r = p306.simulate_sensor_cleaning_hil(
                body_profile=p306.BODY_MODEL_FX6,
                request_ibis_shake=False,
                fx6_nd_filter=stop,
                request_fx6_apr=(stop == "CLEAR"),
            )
            self.assertTrue(r.admitted)
            self.assertFalse(r.fx6_has_ibis_sensor_shake)
            if stop == "CLEAR":
                self.assertTrue(r.apr_executed)

    def test_19_fx3_rejects_builtin_end_filter_and_fx6_apr(self) -> None:
        r_nd = p306.simulate_sensor_cleaning_hil(
            body_profile=p306.BODY_MODEL_FX3,
            request_ibis_shake=False,
            fx6_nd_filter="1/8",
        )
        r_apr = p306.simulate_sensor_cleaning_hil(
            body_profile=p306.BODY_MODEL_FX3,
            request_ibis_shake=False,
            request_fx6_apr=True,
        )
        self.assertFalse(r_nd.admitted)
        self.assertEqual(r_nd.errno_code, p306.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_nd.fx3_has_builtin_end_filter)
        self.assertFalse(r_apr.admitted)
        self.assertEqual(r_apr.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_20_invalid_sensor_cleaning_inputs_rejected_einval(self) -> None:
        self.assertEqual(
            p306.simulate_sensor_cleaning_hil(battery_percent=101).errno_code, p306.EINVAL_ERRNO
        )
        self.assertEqual(
            p306.simulate_sensor_cleaning_hil(battery_percent=-1).errno_code, p306.EINVAL_ERRNO
        )
        self.assertEqual(
            p306.simulate_sensor_cleaning_hil(fx6_nd_filter="1/256").errno_code, p306.EINVAL_ERRNO
        )
        self.assertEqual(
            p306.simulate_sensor_cleaning_hil(body_profile="FX9").errno_code, p306.EINVAL_ERRNO
        )


class TestSubModel62BExposureCompAndCineEiLockout(unittest.TestCase):
    """62B: [Exposure Comp.] +-5.0/+-2.0 EV, M+ISO AUTO, Reset Split & Cine EI Total Lockout."""

    def test_21_still_pas_admits_full_plus_minus_5ev_and_clamps_meter_3ev(self) -> None:
        for mode in (p306.EXP_MODE_P, p306.EXP_MODE_A, p306.EXP_MODE_S):
            for ev in (-5.0, -3.0, 0.0, 3.0, 5.0):
                r = p306.simulate_exposure_comp_and_cine_ei_hil(
                    shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
                    exposure_mode=mode,
                    requested_ev=ev,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_ev, ev)
                self.assertEqual(r.ev_comp_range_min, -5.0)
                self.assertEqual(r.ev_comp_range_max, 5.0)
                self.assertGreaterEqual(r.live_meter_clamped_ev, -3.0)
                self.assertLessEqual(r.live_meter_clamped_ev, 3.0)

    def test_22_still_beyond_5ev_rejected(self) -> None:
        for ev in (-5.3, 5.3):
            r = p306.simulate_exposure_comp_and_cine_ei_hil(
                shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
                exposure_mode=p306.EXP_MODE_A,
                requested_ev=ev,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_23_movie_and_sq_strictly_clamped_plus_minus_2ev(self) -> None:
        for dom in (p306.EXPOSURE_DOMAIN_MOVIE, p306.EXPOSURE_DOMAIN_SQ):
            for ev in (-2.0, 0.0, 2.0):
                r = p306.simulate_exposure_comp_and_cine_ei_hil(
                    shooting_domain=dom,
                    exposure_mode=p306.EXP_MODE_A,
                    log_shooting_mode=p306.LOG_SHOOTING_OFF,
                    requested_ev=ev,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.ev_comp_range_min, -2.0)
                self.assertEqual(r.ev_comp_range_max, 2.0)
            for bad_ev in (-5.0, -2.3, 2.3, 5.0):
                r_bad = p306.simulate_exposure_comp_and_cine_ei_hil(
                    shooting_domain=dom,
                    exposure_mode=p306.EXP_MODE_A,
                    requested_ev=bad_ev,
                )
                self.assertFalse(r_bad.admitted)
                self.assertEqual(r_bad.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_24_iauto_disables_exposure_comp(self) -> None:
        for dom in p306.VALID_EXPOSURE_DOMAINS:
            r = p306.simulate_exposure_comp_and_cine_ei_hil(
                shooting_domain=dom,
                exposure_mode=p306.EXP_MODE_IAUTO,
                requested_ev=0.3,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_25_manual_m_fixed_iso_disabled_vs_m_iso_auto_active(self) -> None:
        r_fixed = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            exposure_mode=p306.EXP_MODE_M,
            iso_auto=False,
            requested_ev=1.0,
        )
        r_auto = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            exposure_mode=p306.EXP_MODE_M,
            iso_auto=True,
            requested_ev=-4.0,
        )
        self.assertFalse(r_fixed.admitted)
        self.assertEqual(r_fixed.errno_code, p306.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_auto.admitted)
        self.assertEqual(r_auto.effective_ev, -4.0)

    def test_26_cine_ei_and_cine_ei_quick_100pct_lockout_across_all_modes(self) -> None:
        for log_mode in p306.CINE_EI_LOCKOUT_MODES:
            for exp_mode in p306.VALID_PASM_MODES:
                for iso_auto in (False, True):
                    r = p306.simulate_exposure_comp_and_cine_ei_hil(
                        shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
                        exposure_mode=exp_mode,
                        iso_auto=iso_auto,
                        log_shooting_mode=log_mode,
                        requested_ev=0.0,
                    )
                    self.assertFalse(r.admitted)
                    self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)
                    self.assertFalse(r.cine_ei_exp_comp_enabled)
                    self.assertEqual(r.ev_comp_cine_ei_or_mode_bypass_events, 0)

    def test_27_flexible_iso_retains_2ev_exposure_comp(self) -> None:
        r = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            exposure_mode=p306.EXP_MODE_M,
            iso_auto=True,
            log_shooting_mode=p306.LOG_SHOOTING_FLEXIBLE_ISO,
            requested_ev=1.7,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_ev, 1.7)

    def test_28_camera_settings_reset_zeros_ev_but_preserves_0_5ev_step(self) -> None:
        r_csr = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            exposure_mode=p306.EXP_MODE_A,
            requested_ev=3.5,
            exposure_step=p306.EXP_STEP_0_5EV,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_ev, 0.0)
        self.assertEqual(r_csr.effective_exposure_step, p306.EXP_STEP_0_5EV)

        r_init = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            exposure_mode=p306.EXP_MODE_A,
            requested_ev=3.5,
            exposure_step=p306.EXP_STEP_0_5EV,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_ev, 0.0)
        self.assertEqual(r_init.effective_exposure_step, p306.EXP_STEP_0_3EV)

    def test_29_dormant_reset_ev_comp_and_dial_ev_comp_rejected(self) -> None:
        for feat in p306.DORMANT_EV_FEATURES:
            r = p306.simulate_exposure_comp_and_cine_ei_hil(
                requested_dormant_feature=feat,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_30_fx6_uses_auto_exposure_level_not_fx3_5ev_comp(self) -> None:
        r = p306.simulate_exposure_comp_and_cine_ei_hil(
            body_profile=p306.BODY_MODEL_FX6,
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            requested_ev=1.0,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_31_cine_ei_monitoring_profile_800_and_12800(self) -> None:
        p1 = p306.evaluate_cine_ei_monitoring_profile(
            log_shooting_mode=p306.LOG_SHOOTING_CINE_EI,
            base_iso=800,
            exposure_index_ev=-1.0,
        )
        p2 = p306.evaluate_cine_ei_monitoring_profile(
            log_shooting_mode=p306.LOG_SHOOTING_CINE_EI_QUICK,
            base_iso=12800,
            exposure_index_ev=1.0,
        )
        self.assertEqual(p1["monitoring_ei_iso"], 1600)
        self.assertEqual(p2["monitoring_ei_iso"], 6400)
        self.assertFalse(p1["cine_ei_exp_comp_enabled"])
        self.assertEqual(p1["exposure_comp_errno_when_attempted"], p306.EOPNOTSUPP_ERRNO)

    def test_32_invalid_exposure_comp_args_einval(self) -> None:
        self.assertEqual(
            p306.simulate_exposure_comp_and_cine_ei_hil(exposure_step="1.0EV").errno_code,
            p306.EINVAL_ERRNO,
        )
        self.assertEqual(
            p306.simulate_exposure_comp_and_cine_ei_hil(exposure_mode="AUTO+").errno_code,
            p306.EINVAL_ERRNO,
        )
        self.assertEqual(
            p306.simulate_exposure_comp_and_cine_ei_hil(base_iso=640).errno_code,
            p306.EINVAL_ERRNO,
        )


class TestSubModel62CFocusModeSplitAndPrioritySet(unittest.TestCase):
    """62C: [Focus Mode] 5-Still vs 2-Movie/S&Q Split + Priority Set + AF Assist/Illuminator."""

    def test_33_still_exposes_all_5_focus_modes(self) -> None:
        self.assertEqual(p306.STILL_FOCUS_MODES, ("AF-S", "AF-A", "AF-C", "DMF", "MF"))
        for mode in p306.STILL_FOCUS_MODES:
            r = p306.simulate_focus_mode_split_hil(
                shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
                requested_focus_mode=mode,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_focus_mode, mode)
            self.assertEqual(r.exposed_modes, p306.STILL_FOCUS_MODES)

    def test_34_movie_and_sq_strictly_clamp_to_2_modes_afc_mf(self) -> None:
        self.assertEqual(p306.MOVIE_SQ_FOCUS_MODES, ("AF-C", "MF"))
        for dom in (p306.EXPOSURE_DOMAIN_MOVIE, p306.EXPOSURE_DOMAIN_SQ):
            for ok_mode in p306.MOVIE_SQ_FOCUS_MODES:
                r = p306.simulate_focus_mode_split_hil(
                    shooting_domain=dom,
                    requested_focus_mode=ok_mode,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.exposed_modes, ("AF-C", "MF"))

    def test_35_movie_and_sq_reject_afs_afa_dmf_eopnotsupp(self) -> None:
        for dom in (p306.EXPOSURE_DOMAIN_MOVIE, p306.EXPOSURE_DOMAIN_SQ):
            for bad_mode in (p306.FOCUS_MODE_AFS, p306.FOCUS_MODE_AFA, p306.FOCUS_MODE_DMF):
                r = p306.simulate_focus_mode_split_hil(
                    shooting_domain=dom,
                    requested_focus_mode=bad_mode,
                )
                self.assertFalse(r.admitted)
                self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)
                self.assertEqual(r.movie_sq_invalid_focus_mode_bypass_events, 0)

    def test_36_dormant_pf_and_semi_manual_rejected_everywhere(self) -> None:
        for dom in p306.VALID_EXPOSURE_DOMAINS:
            for dormant in p306.DORMANT_FOCUS_MODES:
                r = p306.simulate_focus_mode_split_hil(
                    shooting_domain=dom,
                    requested_focus_mode=dormant,
                )
                self.assertFalse(r.admitted)
                self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_37_priority_set_and_af_assist_survive_camera_settings_reset(self) -> None:
        r = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_MF,
            priority_set_af_s=p306.AF_PRIORITY_RELEASE,
            priority_set_af_c=p306.AF_PRIORITY_AF,
            af_assist_on=True,
            af_illuminator=p306.AF_ILLUMINATOR_OFF,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_focus_mode, p306.FOCUS_MODE_AFA)
        self.assertEqual(r.effective_illuminator if False else r.effective_af_illuminator, p306.AF_ILLUMINATOR_AUTO)
        self.assertEqual(r.effective_priority_af_s, p306.AF_PRIORITY_RELEASE)
        self.assertEqual(r.effective_priority_af_c, p306.AF_PRIORITY_AF)
        self.assertTrue(r.effective_af_assist_on)

    def test_38_initialize_clears_priority_set_and_af_assist_to_balanced_off(self) -> None:
        r = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            requested_focus_mode=p306.FOCUS_MODE_MF,
            priority_set_af_s=p306.AF_PRIORITY_AF,
            priority_set_af_c=p306.AF_PRIORITY_RELEASE,
            af_assist_on=True,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_focus_mode, p306.FOCUS_MODE_AFC)
        self.assertEqual(r.effective_priority_af_s, p306.AF_PRIORITY_BALANCED)
        self.assertEqual(r.effective_priority_af_c, p306.AF_PRIORITY_BALANCED)
        self.assertFalse(r.effective_af_assist_on)

    def test_39_af_illuminator_still_eligible_vs_locked_in_afc_movie_mag_adaptor(self) -> None:
        r_ok = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFS,
        )
        r_afc = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFC,
        )
        r_mov = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            requested_focus_mode=p306.FOCUS_MODE_AFC,
        )
        r_mag = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFS,
            focus_magnifier_active=True,
        )
        r_adp = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_DMF,
            mount_adaptor_attached=True,
        )
        self.assertTrue(r_ok.af_illuminator_active_now)
        self.assertFalse(r_afc.af_illuminator_active_now)
        self.assertFalse(r_mov.af_illuminator_active_now)
        self.assertFalse(r_mag.af_illuminator_active_now)
        self.assertFalse(r_adp.af_illuminator_active_now)

    def test_40_fx6_physical_af_mf_and_push_af_contrast(self) -> None:
        r_ok = p306.simulate_focus_mode_split_hil(
            body_profile=p306.BODY_MODEL_FX6,
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            requested_focus_mode=p306.FOCUS_MODE_AFC,
            fx6_push_af_mode="Single-shot AF(AF-S)",
        )
        r_bad = p306.simulate_focus_mode_split_hil(
            body_profile=p306.BODY_MODEL_FX6,
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFA,
        )
        self.assertTrue(r_ok.admitted)
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p306.EOPNOTSUPP_ERRNO)


class TestSubModel62DPlaybackViewIndexRotateVaultFirewall(unittest.TestCase):
    """62D: Playback [View Mode], 9/25 [Image Index], [Display as Group] & [Rotate] Vault Firewall."""

    def test_41_all_supported_view_modes_admitted(self) -> None:
        for vm in p306.ALL_SUPPORTED_VIEW_MODES:
            r = p306.simulate_playback_view_index_rotate_vault_hil(view_mode=vm)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_view_mode, vm)

    def test_42_dormant_folder_view_mp4_rejected(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            view_mode=p306.VIEW_MODE_DORMANT_FOLDER_MP4,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_43_exact_9_25_image_index_admitted_while_12_30_rejected(self) -> None:
        for ok_idx in p306.VALID_FX3_IMAGE_INDEX_MODES:
            r = p306.simulate_playback_view_index_rotate_vault_hil(image_index=ok_idx)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_image_index, ok_idx)
        for bad_idx in p306.DORMANT_IMAGE_INDEX_MODES:
            r_bad = p306.simulate_playback_view_index_rotate_vault_hil(image_index=bad_idx)
            self.assertFalse(r_bad.admitted)
            self.assertEqual(r_bad.errno_code, p306.EOPNOTSUPP_ERRNO)
            self.assertEqual(r_bad.dormant_12_30_image_index_exposed_events, 0)

    def test_44_display_as_group_and_display_rotation_all_modes(self) -> None:
        for grp in (False, True):
            for rot in p306.VALID_DISPLAY_ROTATION_MODES:
                r = p306.simulate_playback_view_index_rotate_vault_hil(
                    display_as_group=grp,
                    display_rotation=rot,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_display_as_group, grp)
                self.assertEqual(r.effective_display_rotation, rot)

    def test_45_playback_prefs_survive_cam_reset_and_reset_on_initialize(self) -> None:
        r_csr = p306.simulate_playback_view_index_rotate_vault_hil(
            view_mode=p306.VIEW_MODE_XAVCS,
            image_index=p306.IMAGE_INDEX_25,
            display_as_group=True,
            display_rotation=p306.DISPLAY_ROTATION_OFF,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_view_mode, p306.VIEW_MODE_XAVCS)
        self.assertEqual(r_csr.effective_image_index, p306.IMAGE_INDEX_25)
        self.assertTrue(r_csr.effective_display_as_group)
        self.assertEqual(r_csr.effective_display_rotation, p306.DISPLAY_ROTATION_OFF)

        r_init = p306.simulate_playback_view_index_rotate_vault_hil(
            view_mode=p306.VIEW_MODE_AVCHD,
            image_index=p306.IMAGE_INDEX_25,
            display_as_group=True,
            display_rotation=p306.DISPLAY_ROTATION_OFF,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_view_mode, p306.VIEW_MODE_DATE)
        self.assertEqual(r_init.effective_image_index, p306.IMAGE_INDEX_9)
        self.assertFalse(r_init.effective_display_as_group)
        self.assertEqual(r_init.effective_display_rotation, p306.DISPLAY_ROTATION_AUTO)

    def test_46_critical_slot1_tier0_vault_rotate_fail_closed_erofs(self) -> None:
        for media in (
            p306.MEDIA_KIND_STILL_JPEG,
            p306.MEDIA_KIND_STILL_HEIF,
            p306.MEDIA_KIND_STILL_RAW,
        ):
            r = p306.simulate_playback_view_index_rotate_vault_hil(
                playback_slot=p306.SLOT_1,
                slot1_is_tier0_vault=True,
                media_kind=media,
                rotate_requested=True,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EROFS_ERRNO)
            self.assertTrue(r.tier0_vault_firewall_triggered)
            self.assertFalse(r.avf_info_exif_mutated)
            self.assertEqual(r.slot1_vault_rotate_mutation_bytes, 0)
            self.assertEqual(r.physical_device_writes, 0)

    def test_47_slot2_virtual_still_rotate_90ccw_steps_zero_physical_writes(self) -> None:
        deg = 0
        for expected in (90, 180, 270, 0):
            r = p306.simulate_playback_view_index_rotate_vault_hil(
                playback_slot=p306.SLOT_2,
                slot1_is_tier0_vault=True,
                media_kind=p306.MEDIA_KIND_STILL_JPEG,
                rotate_requested=True,
                initial_orientation_deg=deg,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_orientation_deg, expected)
            self.assertTrue(r.avf_info_exif_mutated)
            self.assertEqual(r.physical_device_writes, 0)
            self.assertEqual(r.slot1_vault_rotate_mutation_bytes, 0)
            deg = expected

    def test_48_write_protected_card_rotate_blocked_erofs(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            playback_slot=p306.SLOT_2,
            card_write_protected=True,
            media_kind=p306.MEDIA_KIND_STILL_JPEG,
            rotate_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EROFS_ERRNO)

    def test_49_background_ftp_transfer_blocks_rotate_ebusy(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            playback_slot=p306.SLOT_2,
            background_transfer_active=True,
            media_kind=p306.MEDIA_KIND_STILL_HEIF,
            rotate_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EBUSY_ERRNO)

    def test_50_movie_clip_rotate_rejected_eopnotsupp(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            playback_slot=p306.SLOT_2,
            media_kind=p306.MEDIA_KIND_MOVIE_XAVCS,
            rotate_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EOPNOTSUPP_ERRNO)

    def test_51_invalid_playback_args_rejected_einval(self) -> None:
        self.assertEqual(
            p306.simulate_playback_view_index_rotate_vault_hil(playback_slot="Slot 3").errno_code,
            p306.EINVAL_ERRNO,
        )
        self.assertEqual(
            p306.simulate_playback_view_index_rotate_vault_hil(display_rotation="Vertical").errno_code,
            p306.EINVAL_ERRNO,
        )
        self.assertEqual(
            p306.simulate_playback_view_index_rotate_vault_hil(initial_orientation_deg=45).errno_code,
            p306.EINVAL_ERRNO,
        )


class TestRedlinesAndSuiteIntegration(unittest.TestCase):
    """Hard safety redlines, standalone CLI, and full 62/62 suite orchestration."""

    def test_52_full_phase306_report_all_checks_passed(self) -> None:
        rep = p306.run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_62nd_stage_milestone"])
        self.assertEqual(rep["milestone"], "62/62")
        self.assertEqual(rep["stage_index"], 62)
        self.assertEqual(rep["stage_total"], 62)

    def test_53_clean_room_report_deterministic_digest(self) -> None:
        r1 = p306.run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation(
            force_clean_room=True
        )
        r2 = p306.run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation(
            env={p306.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["source_mode"], p306.SOURCE_MODE_CLEAN_ROOM)

    def test_54_all_hardware_write_redlines_locked_false_and_zero(self) -> None:
        rep = p306.run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        for false_key in (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "fx3_has_builtin_end_filter",
            "fx6_has_ibis_sensor_shake",
            "cine_ei_exp_comp_enabled",
        ):
            self.assertFalse(red[false_key], false_key)
        for zero_key in (
            "nop_count",
            "guest_code_modification_bytes",
            "cp_mutation_bytes",
            "wbi_mutation_bytes",
            "calibration_mutation_bytes",
            "cnflasha_mutation_bytes",
            "nvram_persistent_writes",
            "bk4_persistent_nvram_writes",
            "physical_device_writes",
            "emmc_nflasha_write_count",
            "emmc_mutation_bytes",
            "emmc_corruptions",
            "spi_nor_mutation_bytes",
            "otp_fuse_touches",
            "rpmb_counter_increments",
            "physical_usb_packets_emitted",
            "passive_tx_bytes_emitted",
            "sensor_cleaning_low_battery_bypass_events",
            "sensor_cleaning_mandatory_poweroff_bypass_events",
            "fx6_ibis_sensor_shake_spoof_events",
            "ev_comp_cine_ei_or_mode_bypass_events",
            "movie_sq_invalid_focus_mode_bypass_events",
            "dormant_12_30_image_index_exposed_events",
            "slot1_vault_rotate_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_55_standalone_cli_help_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("51%", proc.stdout)

    def test_56_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p306.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 306 Stage 62 (62/62 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p306.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "62/62")
        self.assertTrue(parsed["all_checks_passed"])

    def test_57_suite_default_config_enables_stage62(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase306_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil)
        self.assertTrue(cfg.include_stage62)
        self.assertTrue(cfg.stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil)

    def test_58_suite_full_run_contains_at_least_62_stages(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 62)
        s62 = rep["stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"]
        self.assertTrue(s62["all_checks_passed"])
        self.assertTrue(s62["is_62nd_stage_milestone"])
        self.assertEqual(s62["milestone"], "62/62")
        self.assertEqual(s62["phase_number"], 306)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_59_suite_fast_isolated_stage62_only_pass(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(rep["all_checks_passed"])
        self.assertIsNone(rep.get("stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil"))
        self.assertIsNotNone(rep.get("stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"))

    def test_60_suite_skip_flags_disable_stage62(self) -> None:
        for flag in ("--skip-stage62", "--no-include-stage62", "--skip-phase306"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn("stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil", data)
            self.assertFalse(data["config"]["include_stage62"])

    def test_61_suite_cli_help_and_summary_include_stage62(self) -> None:
        proc_help = subprocess.run(
            [sys.executable, "-B", str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_help.returncode, 0, proc_help.stderr)
        self.assertIn("--include-stage62", proc_help.stdout)
        self.assertIn("--skip-phase306", proc_help.stdout)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--include-stage62", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil=CLEAN_ROOM_SYNTHETIC", buf.getvalue())

    def test_62_no_raw_firmware_bytes_in_json_output(self) -> None:
        rep = p306.run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation()
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)


# Additional fine-grained matrix coverage (tests 63..88)
class TestWave52MatrixExtensions(unittest.TestCase):
    """Granular Wave-52 boundary and multi-condition assertions (tests 63..88)."""

    def test_63_battery_boundary_sweep_48_to_53(self) -> None:
        for pct in (48, 49, 50):
            r = p306.simulate_sensor_cleaning_hil(battery_percent=pct, request_ibis_shake=True)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p306.EACCES_ERRNO)
        for pct in (51, 52, 53):
            r = p306.simulate_sensor_cleaning_hil(
                battery_percent=pct, request_ibis_shake=True, power_switch_turned_off=True
            )
            self.assertTrue(r.admitted)

    def test_64_sensor_cleaning_standby_eligibility_without_shake(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(battery_percent=51, request_ibis_shake=False)
        self.assertTrue(r.admitted)
        self.assertFalse(r.ibis_sensor_shake_actuated)
        self.assertFalse(r.mandatory_power_off_required)

    def test_65_sensor_cleaning_awaited_off_without_detach_still_marks_power_off_required(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            battery_percent=70,
            request_ibis_shake=True,
            power_switch_turned_off=False,
            lens_detach_requested=False,
            resume_shooting_requested=False,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.mandatory_power_off_required)
        self.assertFalse(r.lens_swap_cleared)
        self.assertFalse(r.shooting_resumed)

    def test_66_fx6_end_without_apr_succeeds(self) -> None:
        r = p306.simulate_sensor_cleaning_hil(
            body_profile=p306.BODY_MODEL_FX6,
            request_ibis_shake=False,
            fx6_nd_filter="1/64",
            request_fx6_apr=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.apr_executed)

    def test_67_still_m_iso_auto_allows_extremes_plus_minus_5ev(self) -> None:
        for ev in (-5.0, 5.0):
            r = p306.simulate_exposure_comp_and_cine_ei_hil(
                shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
                exposure_mode=p306.EXP_MODE_M,
                iso_auto=True,
                requested_ev=ev,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_ev, ev)

    def test_68_movie_m_iso_auto_clamped_to_2ev(self) -> None:
        r_ok = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            exposure_mode=p306.EXP_MODE_M,
            iso_auto=True,
            requested_ev=2.0,
        )
        r_bad = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            exposure_mode=p306.EXP_MODE_M,
            iso_auto=True,
            requested_ev=2.3,
        )
        self.assertTrue(r_ok.admitted)
        self.assertFalse(r_bad.admitted)

    def test_69_sq_flexible_iso_admits_2ev_comp(self) -> None:
        r = p306.simulate_exposure_comp_and_cine_ei_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_SQ,
            exposure_mode=p306.EXP_MODE_A,
            log_shooting_mode=p306.LOG_SHOOTING_FLEXIBLE_ISO,
            requested_ev=-1.7,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_ev, -1.7)

    def test_70_cine_ei_exposure_index_rejects_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            p306.evaluate_cine_ei_monitoring_profile(exposure_index_ev=2.3)

    def test_71_still_exposure_step_0_5ev_retained_across_reset(self) -> None:
        r = p306.simulate_exposure_comp_and_cine_ei_hil(
            exposure_step=p306.EXP_STEP_0_5EV,
            requested_ev=-2.5,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_exposure_step, p306.EXP_STEP_0_5EV)
        self.assertEqual(r.effective_ev, 0.0)

    def test_72_live_meter_clamps_negative_values_at_minus_3ev(self) -> None:
        r = p306.simulate_exposure_comp_and_cine_ei_hil(requested_ev=-5.0)
        self.assertEqual(r.effective_ev, -5.0)
        self.assertEqual(r.live_meter_clamped_ev, -3.0)

    def test_73_focus_mode_cam_reset_restores_afa_in_still_and_afc_in_movie(self) -> None:
        rs = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFS,
            camera_settings_reset_applied=True,
        )
        rm = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_MOVIE,
            requested_focus_mode=p306.FOCUS_MODE_MF,
            camera_settings_reset_applied=True,
        )
        self.assertEqual(rs.effective_focus_mode, p306.FOCUS_MODE_AFA)
        self.assertEqual(rm.effective_focus_mode, p306.FOCUS_MODE_AFC)

    def test_74_af_illuminator_off_disables_active_now(self) -> None:
        r = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_AFS,
            af_illuminator=p306.AF_ILLUMINATOR_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.af_illuminator_active_now)

    def test_75_still_mf_disables_af_illuminator(self) -> None:
        r = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=p306.FOCUS_MODE_MF,
            af_illuminator=p306.AF_ILLUMINATOR_AUTO,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.af_illuminator_active_now)

    def test_76_priority_set_all_3_options_accepted_for_afs_and_afc(self) -> None:
        for prio in p306.VALID_AF_PRIORITIES:
            r = p306.simulate_focus_mode_split_hil(
                priority_set_af_s=prio,
                priority_set_af_c=prio,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_priority_af_s, prio)
            self.assertEqual(r.effective_priority_af_c, prio)

    def test_77_sq_af_illuminator_always_locked_out(self) -> None:
        r = p306.simulate_focus_mode_split_hil(
            shooting_domain=p306.EXPOSURE_DOMAIN_SQ,
            requested_focus_mode=p306.FOCUS_MODE_AFC,
            af_illuminator=p306.AF_ILLUMINATOR_AUTO,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.af_illuminator_active_now)

    def test_78_invalid_focus_mode_rejected_einval(self) -> None:
        r = p306.simulate_focus_mode_split_hil(requested_focus_mode="TRACKING_MAGIC")
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EINVAL_ERRNO)

    def test_79_slot2_heif_and_raw_rotate_admitted_zero_writes(self) -> None:
        for media in (p306.MEDIA_KIND_STILL_HEIF, p306.MEDIA_KIND_STILL_RAW):
            r = p306.simulate_playback_view_index_rotate_vault_hil(
                playback_slot=p306.SLOT_2,
                slot1_is_tier0_vault=True,
                media_kind=media,
                rotate_requested=True,
                initial_orientation_deg=90,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_orientation_deg, 180)
            self.assertEqual(r.physical_device_writes, 0)

    def test_80_slot1_non_vault_still_rotate_virtual_zero_physical_writes(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            playback_slot=p306.SLOT_1,
            slot1_is_tier0_vault=False,
            media_kind=p306.MEDIA_KIND_STILL_JPEG,
            rotate_requested=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.physical_device_writes, 0)
        self.assertEqual(r.slot1_vault_rotate_mutation_bytes, 0)

    def test_81_slot1_vault_without_rotate_requested_allows_view_mode_only(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            playback_slot=p306.SLOT_1,
            slot1_is_tier0_vault=True,
            view_mode=p306.VIEW_MODE_XAVCS,
            image_index=p306.IMAGE_INDEX_25,
            rotate_requested=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.avf_info_exif_mutated)
        self.assertFalse(r.tier0_vault_firewall_triggered)

    def test_82_fx6_playback_also_enforces_tier0_slot1_vault_firewall(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(
            body_profile=p306.BODY_MODEL_FX6,
            playback_slot=p306.SLOT_1,
            slot1_is_tier0_vault=True,
            media_kind=p306.MEDIA_KIND_STILL_JPEG,
            rotate_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EROFS_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)

    def test_83_invalid_image_index_einval(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(image_index="64 Images")
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EINVAL_ERRNO)

    def test_84_invalid_view_mode_einval(self) -> None:
        r = p306.simulate_playback_view_index_rotate_vault_hil(view_mode="Proxy View")
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p306.EINVAL_ERRNO)

    def test_85_no_legacy_bin_python3_hardcoded_in_new_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_86_suite_subprocess_uses_sys_executable_with_clean_room(self) -> None:
        env = dict(os.environ)
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                *_FAST_CLI_FLAGS,
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[PASS]", proc.stdout)
        self.assertIn("s1_rot=0", proc.stdout)

    def test_87_stage62_payload_keys_present_and_complete(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        s62 = rep["stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"]
        for key in (
            "pillar_a_sensor_cleaning_battery_poweroff_and_fx6_end_apr_hil",
            "pillar_b_exposure_comp_and_cine_ei_total_lockout_hil",
            "pillar_c_focus_mode_5still_vs_2movie_split_and_priority_hil",
            "pillar_d_playback_view_index_rotate_vault_and_redlines",
            "phase306_audit_digest_sha256",
            "donor_audit",
        ):
            self.assertIn(key, s62)

    def test_88_stage62_config_serialization_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        cfg = rep["config"]
        self.assertTrue(cfg["include_phase306_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"])
        self.assertTrue(cfg["include_stage62"])
        self.assertTrue(cfg["stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"])


if __name__ == "__main__":
    unittest.main()
