#!/usr/bin/env python3
"""Unit tests for Phase 322 (Stage 67 — 67/67 Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-57:
5-Axis IBIS `[SteadyShot]` (`Active`/`Standard`/`Off` Movie + `On`/`Off` Still,
4-Condition `Active` Lockout & Exact `47`-Step `[Focal Length]` Table vs Zero-IBIS `FX6`),
Dormant Movie `[Self-timer]` Rejection vs Still `[Drive Mode]` Self-Timer, Front LED `#8` & `[Audio signals]`,
`[Zebra Display]` (`Custom1` `Std+Range` / `Custom2` `Lower Limit`) & 4-Color `[Peaking]` Clean-HDMI vs `FX6`,
and `[Network Streaming]` (`RTMP`/`RTMPS`/`SRT`) + Zero-RF / `Slot-1` `EROFS=30` Vault Firewall HIL
(90 dual-mode tests).
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
import tempfile
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_steadyshot_47focal_selftimer_zebra_streaming_coemulator as p322  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..66 for quick Stage 67 isolation tests."""
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
        include_stage62=False,
        include_stage63=False,
        include_stage64=False,
        include_stage65=False,
        include_stage66=False,
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
    "--skip-stage62",
    "--skip-stage63",
    "--skip-stage64",
    "--skip-stage65",
    "--skip-stage66",
]


class TestPhase322Stage67CoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit & Dual-Mode Architecture (Tests 01..15)
    # ------------------------------------------------------------------

    def test_01_stage67_identity_constants(self) -> None:
        self.assertEqual(p322.PHASE_NUMBER, 322)
        self.assertEqual(p322.STAGE_INDEX, 67)
        self.assertEqual(p322.STAGE_TOTAL, 67)
        self.assertEqual(p322.MILESTONE_LABEL, "67/67")
        self.assertTrue(p322.IS_67TH_STAGE_MILESTONE)
        self.assertEqual(
            p322.STAGE_NAME,
            "stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil",
        )
        self.assertEqual(p322.BOUNDED_WINDOW_MAX_BYTES, 4096)

    def test_02_17_donor_tables_consistent(self) -> None:
        self.assertEqual(len(p322.DONOR_RELPATHS), 17)
        self.assertEqual(len(p322.EXPECTED_DONOR_BYTES), 17)
        self.assertEqual(len(p322.EXPECTED_COMPACT_DONOR_SHA256), 14)
        self.assertEqual(len(p322.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(set(p322.COMPACT_DONOR_TOKENS.keys()), set(p322.EXPECTED_COMPACT_DONOR_SHA256.keys()))
        self.assertEqual(set(p322.LARGE_DONOR_WINDOWS.keys()), set(p322.EXPECTED_LARGE_HEAD4K_SHA256.keys()))

    def test_03_clean_room_test_mode_env_flags(self) -> None:
        self.assertFalse(p322.clean_room_test_mode(force_clean_room=False, env={}))
        self.assertTrue(p322.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertTrue(p322.clean_room_test_mode(env={"FX3_CLEAN_ROOM_TEST": "1"}))
        self.assertTrue(p322.clean_room_test_mode(env={"FX3_FX6_FORCE_CLEAN_ROOM": "true"}))

    def test_04_donorless_work_root_none_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p322._DONOR_AUDIT_CACHE.clear()
            env = {
                "FX3_FX6_MAC_WORK_ROOT": td,
                "FX3_FX6_MAIN_LAB_WORK_ROOT": td,
                "FX3_FX6_MAC_ROOT": td,
            }
            with unittest.mock.patch.object(p322, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p322, "LEGACY_MAC_ROOT", Path(td) / "missing"):
                    wr = p322.resolve_mac_work_root(env=env)
                    self.assertIsNone(wr)
                    rep = p322.inspect_phase322_donors(env=env)
                    self.assertEqual(rep.source_mode, p322.SOURCE_MODE_CLEAN_ROOM)
                    self.assertTrue(rep.all_contracts_verified)
                    self.assertEqual(rep.donor_files_inspected, 17)
                    self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_05_clean_room_synthetic_audit_parity(self) -> None:
        rep = p322.inspect_phase322_donors(force_clean_room=True)
        self.assertEqual(rep.source_mode, p322.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep.access_mode, p322.DONOR_ACCESS_MODE)
        self.assertEqual(rep.donor_files_inspected, 17)
        self.assertEqual(rep.compact_donors_verified, 14)
        self.assertEqual(rep.large_donors_verified, 3)
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_audit_when_available(self) -> None:
        if p322.resolve_mac_work_root(force_clean_room=False, env={}) is None:
            self.skipTest("Donorless environment")
        rep = p322.inspect_phase322_donors(force_clean_room=False, env={})
        self.assertEqual(rep.source_mode, p322.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.compact_donors_verified, 14)
        self.assertEqual(rep.large_donors_verified, 3)
        self.assertGreater(rep.total_tokens_verified, 100)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_07_bounded_window_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEF")
            tf.flush()
            with self.assertRaises(p322.Stage67Phase322Error):
                p322._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p322.Stage67Phase322Error):
                p322._read_window_readonly_bytes(Path(tf.name), -1, 16)
            with self.assertRaises(p322.Stage67Phase322Error):
                p322._read_window_readonly_bytes(Path(tf.name), 0, 0)

    def test_08_large_donor_windows_all_within_4096_bytes(self) -> None:
        for key, wins in p322.LARGE_DONOR_WINDOWS.items():
            for off, lbl, needle in wins:
                self.assertEqual(off % 4096, 0, f"{key}:{lbl} not 4k aligned")
                self.assertLessEqual(len(needle), 4096)

    def test_09_donor_size_mismatch_detected(self) -> None:
        if p322.resolve_mac_work_root(force_clean_room=False, env={}) is None:
            self.skipTest("Donorless environment")
        with unittest.mock.patch.dict(
            p322.EXPECTED_DONOR_BYTES, {"fx3_string_en_f": 12345}
        ):
            p322._DONOR_AUDIT_CACHE.clear()
            rep = p322.inspect_phase322_donors(force_clean_room=False, env={})
            self.assertFalse(rep.all_contracts_verified)
        p322._DONOR_AUDIT_CACHE.clear()

    def test_10_donor_sha_mismatch_detected(self) -> None:
        if p322.resolve_mac_work_root(force_clean_room=False, env={}) is None:
            self.skipTest("Donorless environment")
        with unittest.mock.patch.dict(
            p322.EXPECTED_COMPACT_DONOR_SHA256, {"fx3_string_en_f": "0" * 64}
        ):
            p322._DONOR_AUDIT_CACHE.clear()
            rep = p322.inspect_phase322_donors(force_clean_room=False, env={})
            self.assertFalse(rep.all_contracts_verified)
        p322._DONOR_AUDIT_CACHE.clear()

    def test_11_large_window_missing_needle_detected(self) -> None:
        if p322.resolve_mac_work_root(force_clean_room=False, env={}) is None:
            self.skipTest("Donorless environment")
        with unittest.mock.patch.dict(
            p322.LARGE_DONOR_WINDOWS,
            {"fx3_appfw": ((0, "BOGUS", b"__NO_SUCH_TOKEN__"),)},
        ):
            p322._DONOR_AUDIT_CACHE.clear()
            rep = p322.inspect_phase322_donors(force_clean_room=False, env={})
            self.assertFalse(rep.all_contracts_verified)
        p322._DONOR_AUDIT_CACHE.clear()

    def test_12_sentinel_dirname_disables_mac_work_root(self) -> None:
        wr = p322.resolve_mac_work_root(
            env={"FX3_FX6_MAC_WORK_ROOT": f"/tmp/{p322.CLEAN_ROOM_SENTINEL_DIRNAME}"}
        )
        self.assertIsNone(wr)

    def test_13_top_level_orchestrator_passes_clean_room(self) -> None:
        rep = p322.run_phase322_steadyshot_47focal_selftimer_zebra_streaming_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["milestone"], "67/67")
        self.assertTrue(rep["is_67th_stage_milestone"])

    def test_14_top_level_orchestrator_passes_default_mode(self) -> None:
        rep = p322.run_phase322_steadyshot_47focal_selftimer_zebra_streaming_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(rep["redlines"]["physical_device_writes"], 0)

    def test_15_donor_audit_fast_under_1s(self) -> None:
        p322._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        rep = p322.inspect_phase322_donors(force_clean_room=True)
        self.assertTrue(rep.all_contracts_verified)
        self.assertLess(time.monotonic() - t0, 1.0)

    # ------------------------------------------------------------------
    # Sub-Model 67A — 5-Axis IBIS [SteadyShot], 4-Lock Active & 47-Step Focal Length (Tests 16..34)
    # ------------------------------------------------------------------

    def test_16_fx3_image_stabilization_exact_4_items(self) -> None:
        self.assertEqual(len(p322.FX3_IMAGE_STABILIZATION_4_ITEMS), 4)
        self.assertEqual(
            p322.FX3_IMAGE_STABILIZATION_4_ITEMS,
            ("Movie SteadyShot", "Still SteadyShot", "SteadyShot Adjust.", "Focal Length"),
        )

    def test_17_fx3_exact_47_step_focal_length_table(self) -> None:
        expected = (
            8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25,
            28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105,
            120, 135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000,
        )
        self.assertEqual(len(p322.FX3_47_FOCAL_LENGTHS_MM), 47)
        self.assertEqual(p322.FX3_47_FOCAL_LENGTHS_MM, expected)
        self.assertEqual(p322.DEFAULT_FOCAL_LENGTH_MM, 8)

    def test_18_all_47_focal_lengths_admitted_in_manual_mode(self) -> None:
        for mm in p322.FX3_47_FOCAL_LENGTHS_MM:
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_STILL,
                requested_steadyshot_mode="On",
                steadyshot_adjustment="Manual",
                requested_focal_length_mm=mm,
            )
            self.assertTrue(r.admitted, f"mm={mm}")
            self.assertEqual(r.effective_focal_length_mm, mm)

    def test_19_non_table_focal_lengths_rejected_einval(self) -> None:
        for bad_mm in (7, 22, 23, 38, 95, 750, 1200):
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_STILL,
                steadyshot_adjustment="Manual",
                requested_focal_length_mm=bad_mm,
            )
            self.assertFalse(r.admitted, f"bad_mm={bad_mm}")
            self.assertEqual(r.errno_code, p322.EINVAL_ERRNO)

    def test_20_movie_steadyshot_active_narrows_fov_and_locks_distortion_auto(self) -> None:
        r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            movie_rec_frame_rate="59.94p",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_steadyshot_mode, "Active")
        self.assertTrue(r.fov_narrowed_by_active)
        self.assertTrue(r.distortion_comp_locked_auto)
        self.assertAlmostEqual(r.active_crop_factor, 1.104, places=3)

    def test_21_movie_steadyshot_standard_default_no_crop(self) -> None:
        r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_steadyshot_mode, "Standard")
        self.assertFalse(r.fov_narrowed_by_active)
        self.assertFalse(r.distortion_comp_locked_auto)
        self.assertEqual(r.active_crop_factor, 1.0)

    def test_22_active_lockout_1_movie_rec_frame_rate_ge_100p_11988p(self) -> None:
        for rate in ("100p", "119.88p"):
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_MOVIE,
                requested_steadyshot_mode="Active",
                movie_rec_frame_rate=rate,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.active_lockout_triggered)
            self.assertEqual(r.effective_steadyshot_mode, "Standard")

    def test_23_active_lockout_2_sq_frame_rate_ge_100fps_120fps(self) -> None:
        for fps in (100, 120, 240):
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_SQ,
                requested_steadyshot_mode="Active",
                sq_frame_rate_fps=fps,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.active_lockout_triggered)
            self.assertEqual(r.effective_steadyshot_mode, "Standard")

    def test_24_active_lockout_3_hdmi_raw_output_on(self) -> None:
        r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            hdmi_raw_output_on=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
        self.assertIn("hdmi_raw_output_on", r.active_lockout_reasons)

    def test_25_active_lockout_4_desqueeze_display_enabled(self) -> None:
        for ratio in ("1.3x", "1.33x", "1.5x", "1.6x", "1.65x", "1.8x", "2.0x"):
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_MOVIE,
                requested_steadyshot_mode="Active",
                desqueeze_display_ratio=ratio,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.active_lockout_triggered)

    def test_26_active_autofallback_mode_yields_standard_on_lockout(self) -> None:
        r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            hdmi_raw_output_on=True,
            reject_on_active_lockout=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_steadyshot_mode, "Standard")
        self.assertFalse(r.fov_narrowed_by_active)

    def test_27_dormant_dynamic_active_fail_closed_eopnotsupp(self) -> None:
        for dyn in p322.DORMANT_DYNAMIC_ACTIVE_MODES:
            r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
                shoot_mode=p322.SHOOT_MODE_MOVIE,
                requested_steadyshot_mode=dyn,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_dynamic_active_blocked)

    def test_28_ciz_stacks_with_active_crop_and_blocks_at_100p_120fps(self) -> None:
        ok = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            movie_rec_frame_rate="23.98p",
            clear_image_zoom_ratio=1.5,
        )
        self.assertTrue(ok.admitted)
        self.assertAlmostEqual(ok.effective_total_crop_factor, 1.656, places=3)

        blk = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_SQ,
            requested_steadyshot_mode="Standard",
            sq_frame_rate_fps=120,
            clear_image_zoom_ratio=1.5,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p322.EOPNOTSUPP_ERRNO)

    def test_29_still_steadyshot_defaults_on_and_rejects_movie_active(self) -> None:
        r_ok = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_steadyshot_mode, "On")

        r_bad = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_steadyshot_mode="Active",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p322.EINVAL_ERRNO)

    def test_30_all_4_image_stabilization_items_reset_on_cam_settings_reset(self) -> None:
        r_mv = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            steadyshot_adjustment="Manual",
            requested_focal_length_mm=500,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_mv.admitted)
        self.assertEqual(r_mv.effective_steadyshot_mode, "Standard")
        self.assertEqual(r_mv.effective_steadyshot_adj, "Auto")
        self.assertEqual(r_mv.effective_focal_length_mm, 8)
        self.assertEqual(r_mv.reset_applied, "CameraSettingsReset")

        r_st = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_steadyshot_mode="Off",
            steadyshot_adjustment="Manual",
            requested_focal_length_mm=1000,
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r_st.effective_steadyshot_mode, "On")
        self.assertEqual(r_st.effective_steadyshot_adj, "Auto")
        self.assertEqual(r_st.effective_focal_length_mm, 8)

    def test_31_fx6_has_zero_ibis_and_rejects_inbody_active_or_47focal(self) -> None:
        r_active = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            body_profile=p322.BODY_MODEL_FX6,
            requested_steadyshot_mode="Active",
        )
        self.assertFalse(r_active.admitted)
        self.assertEqual(r_active.errno_code, p322.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_active.fx6_has_ibis)

        r_foc = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            body_profile=p322.BODY_MODEL_FX6,
            steadyshot_adjustment="Manual",
            requested_focal_length_mm=50,
        )
        self.assertFalse(r_foc.admitted)
        self.assertEqual(r_foc.errno_code, p322.EOPNOTSUPP_ERRNO)

    def test_32_fx6_catalyst_workflow_requires_lens_oss_off(self) -> None:
        r_oss_on = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_lens_oss_enabled=True,
            fx6_catalyst_stabilize_workflow=True,
        )
        self.assertFalse(r_oss_on.admitted)
        self.assertEqual(r_oss_on.errno_code, p322.EINVAL_ERRNO)

        r_oss_off = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_lens_oss_enabled=False,
            fx6_catalyst_stabilize_workflow=True,
        )
        self.assertTrue(r_oss_off.admitted)
        self.assertTrue(r_oss_off.fx6_gyro_rtmd_recorded)
        self.assertEqual(r_oss_off.effective_steadyshot_mode, "Lens_OSS_Off")

    def test_33_invalid_ciz_ratio_or_body_raises_error(self) -> None:
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(clear_image_zoom_ratio=2.5)
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(body_profile="ILME-FX9")

    def test_34_movie_sq_240fps_lockout(self) -> None:
        r = p322.simulate_steadyshot_47focal_and_fx6_ibis_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_steadyshot_mode="Active",
            movie_rec_frame_rate="240p",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)

    # ------------------------------------------------------------------
    # Sub-Model 67B — Dormant Movie Self-Timer vs Still Drive Mode, LED #8 & Audio Signals (Tests 35..52)
    # ------------------------------------------------------------------

    def test_35_dormant_movie_selftimer_variants_all_rejected_eopnotsupp(self) -> None:
        for feat in p322.DORMANT_MOVIE_SELFTIMER_REQUESTS:
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                shoot_mode=p322.SHOOT_MODE_MOVIE,
                requested_drive_or_feature=feat,
            )
            self.assertFalse(r.admitted, feat)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_variant_blocked)

    def test_36_dormant_audio_signal_volume_and_start_end_rejected(self) -> None:
        for feat in ("Audio Signal(Start/End)", "Audio Signal Volume"):
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                requested_drive_or_feature=feat,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)

    def test_37_still_selftimer_single_3_modes_drive_led8(self) -> None:
        self.assertEqual(len(p322.FX3_STILL_SELFTIMER_SINGLE_MODES), 3)
        for m in p322.FX3_STILL_SELFTIMER_SINGLE_MODES:
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                shoot_mode=p322.SHOOT_MODE_STILL,
                requested_drive_or_feature=m,
            )
            self.assertTrue(r.admitted)
            self.assertTrue(r.front_module8_led_blinking)
            self.assertTrue(r.front_module8_accelerated_last2s)
            self.assertTrue(r.front_module8_distinct_from_rec_tally_lamp)

    def test_38_still_selftimer_cont_exact_6_modes(self) -> None:
        self.assertEqual(len(p322.FX3_STILL_SELFTIMER_CONT_MODES), 6)
        for m in p322.FX3_STILL_SELFTIMER_CONT_MODES:
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                shoot_mode=p322.SHOOT_MODE_STILL,
                requested_drive_or_feature=m,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_drive_mode, m)
            self.assertTrue(r.front_module8_led_blinking)

    def test_39_bracket_selftimer_exact_4_modes(self) -> None:
        self.assertEqual(p322.FX3_BRACKET_SELFTIMER_MODES, ("Off", "2 Sec", "5 Sec", "10 Sec"))
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="Single Shooting",
            bracket_selftimer="5 Sec",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.front_module8_led_blinking)

    def test_40_still_selftimer_blocked_in_movie_and_sq_ebusy(self) -> None:
        for mode in (p322.SHOOT_MODE_MOVIE, p322.SHOOT_MODE_SQ):
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                shoot_mode=mode,
                requested_drive_or_feature="10 sec",
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EBUSY_ERRNO)

    def test_41_selftimer_countdown_canceled_by_shutter_repress(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="10 sec",
            cancel_during_countdown=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.countdown_canceled_by_shutter_repress)
        self.assertFalse(r.shutter_released)

    def test_42_audio_signals_muted_by_silent_mode_or_movie_hdmi_audio(self) -> None:
        r_sil = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="2 sec",
            audio_signals="On",
            silent_mode_on=True,
        )
        self.assertFalse(r_sil.audio_beep_audible)
        self.assertIn("silent_mode_on", r_sil.audio_muted_reasons)

        r_hdmi = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_MOVIE,
            requested_drive_or_feature="Single Shooting",
            audio_signals="On",
            movie_hdmi_audio_output=True,
        )
        self.assertFalse(r_hdmi.audio_beep_audible)
        self.assertIn("movie_hdmi_audio_output_on", r_hdmi.audio_muted_reasons)

    def test_43_audio_signals_initialize_only_survives_cam_reset_unlike_drive_mode(self) -> None:
        r_cam = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="10 sec",
            bracket_selftimer="5 Sec",
            audio_signals="Off",
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r_cam.effective_drive_mode, "Single Shooting")
        self.assertEqual(r_cam.effective_bracket_selftimer, "Off")
        self.assertEqual(r_cam.effective_audio_signals, "Off")

        r_init = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="10 sec",
            bracket_selftimer="5 Sec",
            audio_signals="Off",
            initialize_applied=True,
        )
        self.assertEqual(r_init.effective_audio_signals, "On")

    def test_44_fx6_rejects_still_selftimer_with_eopnotsupp(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="10 sec",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dormant_movie_selftimer_blocked)

    def test_45_fx6_picture_cache_rec_forces_free_run_tc(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_picture_cache_rec=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.fx6_picture_cache_rec_active)
        self.assertTrue(r.fx6_timecode_forced_free_run)

    def test_46_fx6_picture_cache_mutually_exclusive_with_interval_simul_proxy(self) -> None:
        for kw in (
            {"fx6_interval_rec": True},
            {"fx6_simul_rec": True},
            {"fx6_proxy_rec": True},
        ):
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                body_profile=p322.BODY_MODEL_FX6,
                fx6_picture_cache_rec=True,
                **kw,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EBUSY_ERRNO)

    def test_47_fx6_interval_rec_and_pre_lighting_modes(self) -> None:
        for pre in p322.FX6_PRE_LIGHTING_MODES:
            r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                body_profile=p322.BODY_MODEL_FX6,
                fx6_interval_rec=True,
                fx6_interval_frames=6,
                fx6_pre_lighting=pre,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_pre_lighting, pre)

    def test_48_fx6_interval_rec_invalid_frame_count_einval(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_interval_rec=True,
            fx6_interval_frames=5,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p322.EINVAL_ERRNO)

    def test_49_single_shooting_leaves_led8_off(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="Single Shooting",
            bracket_selftimer="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.front_module8_led_blinking)
        self.assertTrue(r.audio_beep_audible)

    def test_50_led8_distinct_from_rec_tally_lamp_invariant(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="5 Sec. 3 Img.",
        )
        self.assertTrue(r.front_module8_distinct_from_rec_tally_lamp)

    def test_51_audio_signals_off_silences_beep(self) -> None:
        r = p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
            shoot_mode=p322.SHOOT_MODE_STILL,
            requested_drive_or_feature="2 sec",
            audio_signals="Off",
        )
        self.assertFalse(r.audio_beep_audible)
        self.assertIn("audio_signals_off", r.audio_muted_reasons)

    def test_52_invalid_drive_or_bracket_raises(self) -> None:
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(
                requested_drive_or_feature="Bogus Drive"
            )
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_selftimer_led8_audio_signals_and_fx6_hil(bracket_selftimer="99 Sec")

    # ------------------------------------------------------------------
    # Sub-Model 67C — Zebra Custom1/2 & 4-Color Peaking Clean-HDMI vs FX6 (Tests 53..70)
    # ------------------------------------------------------------------

    def test_53_fx3_zebra_level_10_options_and_custom_defaults(self) -> None:
        self.assertEqual(
            p322.FX3_ZEBRA_LEVEL_OPTIONS,
            ("70", "75", "80", "85", "90", "95", "100", "100+", "Custom1", "Custom2"),
        )

    def test_54_fx3_custom1_std_plus_range_slog3_18pct_gray_41_ire(self) -> None:
        r_hit = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom1",
            custom1_type="Std+Range",
            custom1_std_pct=41,
            custom1_range_pct=2,
            sample_ire_pct=42.5,
        )
        self.assertTrue(r_hit.admitted)
        self.assertTrue(r_hit.zebra_triggered_on_lcd)

        r_miss = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom1",
            custom1_type="Std+Range",
            custom1_std_pct=41,
            custom1_range_pct=2,
            sample_ire_pct=45.0,
        )
        self.assertFalse(r_miss.zebra_triggered_on_lcd)

    def test_55_fx3_custom2_lower_limit_94_ire_vs_107plus_slog3_trap(self) -> None:
        r_94 = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom2",
            custom2_type="Lower Limit",
            custom2_lower_limit_pct=94,
            display_lut_on=False,
            sample_ire_pct=94.0,
        )
        self.assertTrue(r_94.zebra_triggered_on_lcd)
        self.assertFalse(r_94.slog3_clip_missed_by_107plus_warning)

        r_107 = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom2",
            custom2_type="Lower Limit",
            custom2_lower_limit_pct=107,
            display_lut_on=False,
            sample_ire_pct=94.0,
        )
        self.assertFalse(r_107.zebra_triggered_on_lcd)
        self.assertTrue(r_107.slog3_clip_missed_by_107plus_warning)

    def test_56_display_lut_on_shifts_zebra_sampling_domain(self) -> None:
        r_off = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            display_lut_on=False,
        )
        self.assertEqual(r_off.zebra_sampling_domain, "raw_slog3_ire")

        r_on = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            display_lut_on=True,
        )
        self.assertEqual(r_on.zebra_sampling_domain, "post_lut_display_luma")

    def test_57_zebra_custom_bounds_enforced_einval(self) -> None:
        for kw in (
            {"custom1_std_pct": 110},
            {"custom1_range_pct": 0},
            {"custom1_range_pct": 11},
            {"custom2_lower_limit_pct": 110},
        ):
            r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(**kw)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EINVAL_ERRNO)

    def test_58_fx3_4color_peaking_and_levels(self) -> None:
        self.assertEqual(p322.FX3_PEAKING_COLORS, ("Red", "Yellow", "Blue", "White"))
        self.assertEqual(p322.FX3_PEAKING_LEVELS, ("High", "Mid", "Low"))
        for col in p322.FX3_PEAKING_COLORS:
            for lvl in p322.FX3_PEAKING_LEVELS:
                r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
                    peaking_display="On",
                    peaking_level=lvl,
                    peaking_color=col,
                )
                self.assertTrue(r.admitted)
                self.assertTrue(r.peaking_display_active)
                self.assertEqual(r.effective_peaking_color, col)

    def test_59_zebra_and_peaking_never_output_over_clean_hdmi(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            peaking_display="On",
            hdmi_output_connected=True,
        )
        self.assertEqual(r.hdmi_clean_feed_zebra_peaking_leaked_pixels, 0)

    def test_60_all_zebra_and_peaking_settings_resist_camera_settings_reset(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom2",
            custom2_lower_limit_pct=93,
            peaking_display="On",
            peaking_level="High",
            peaking_color="Yellow",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.resisted_camera_settings_reset)
        self.assertTrue(r.zebra_display_active)
        self.assertEqual(r.effective_zebra_setting, "On:Custom2")
        self.assertEqual(r.custom2_lower_limit_pct, 93)
        self.assertTrue(r.peaking_display_active)
        self.assertEqual(r.effective_peaking_level, "High")
        self.assertEqual(r.effective_peaking_color, "Yellow")

    def test_61_initialize_resets_zebra_and_peaking_to_defaults(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="Custom2",
            custom2_lower_limit_pct=93,
            peaking_display="On",
            peaking_level="High",
            peaking_color="Red",
            initialize_applied=True,
        )
        self.assertFalse(r.zebra_display_active)
        self.assertEqual(r.effective_zebra_setting, "Off:70")
        self.assertFalse(r.peaking_display_active)
        self.assertEqual(r.effective_peaking_level, "Mid")
        self.assertEqual(r.effective_peaking_color, "White")

    def test_62_fx3_control_wheel_left_and_right_defaults(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil()
        self.assertEqual(r.left_wheel_button_default, "Zebra Display Select")
        self.assertEqual(r.right_wheel_button_default, "Peaking Display Select")

    def test_63_fx6_zebra_3way_exclusive_selector_rejects_simultaneous_both(self) -> None:
        self.assertEqual(p322.FX6_ZEBRA_SETTINGS, ("Off", "Zebra1", "Zebra2"))
        for bad in ("Both", "Zebra1+Zebra2", "Simultaneous"):
            r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
                body_profile=p322.BODY_MODEL_FX6,
                fx6_zebra_setting=bad,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.fx6_exclusive_3way_selector_enforced)

    def test_64_fx6_zebra1_window_and_zebra2_threshold(self) -> None:
        r1 = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_zebra_setting="Zebra1",
            fx6_zebra1_level_pct=70,
            fx6_zebra1_aperture_pct=10,
            sample_ire_pct=79.0,
        )
        self.assertTrue(r1.admitted)
        self.assertTrue(r1.zebra_triggered_on_lcd)

        r2 = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_zebra_setting="Zebra2",
            fx6_zebra2_level_pct=100,
            sample_ire_pct=99.0,
        )
        self.assertTrue(r2.admitted)
        self.assertFalse(r2.zebra_triggered_on_lcd)

    def test_65_fx6_zebra1_aperture_bounds_2_to_20(self) -> None:
        for ap in (1, 21):
            r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
                body_profile=p322.BODY_MODEL_FX6,
                fx6_zebra_setting="Zebra1",
                fx6_zebra1_aperture_pct=ap,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EINVAL_ERRNO)

    def test_66_fx6_peaking_color_uses_bw_and_rejects_fx3_white_literal(self) -> None:
        self.assertEqual(p322.FX6_PEAKING_COLORS, ("B&W", "Red", "Yellow", "Blue"))
        r_ok = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_peaking_color="B&W",
        )
        self.assertTrue(r_ok.admitted)

        r_bad = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            body_profile=p322.BODY_MODEL_FX6,
            fx6_peaking_color="White",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p322.EOPNOTSUPP_ERRNO)

    def test_67_zebra_preset_100plus_evaluates_correctly(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="100+",
            sample_ire_pct=101.0,
        )
        self.assertTrue(r.zebra_triggered_on_lcd)

    def test_68_zebra_preset_70_midpoint_window(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="On",
            zebra_level="70",
            sample_ire_pct=71.0,
        )
        self.assertTrue(r.zebra_triggered_on_lcd)

    def test_69_zebra_off_never_triggers_even_at_109(self) -> None:
        r = p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(
            zebra_display="Off",
            zebra_level="Custom2",
            custom2_lower_limit_pct=50,
            sample_ire_pct=109.0,
        )
        self.assertFalse(r.zebra_triggered_on_lcd)

    def test_70_invalid_peaking_color_or_zebra_level_raises(self) -> None:
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(peaking_color="Green")
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_zebra_custom12_peaking_clean_hdmi_and_fx6_hil(zebra_level="55")

    # ------------------------------------------------------------------
    # Sub-Model 67D & Redlines — Network Streaming & Zero-RF / Slot-1 Vault (Tests 71..84)
    # ------------------------------------------------------------------

    def test_71_fx3_rtmp_rtmps_srt_supported_over_wired_usblan(self) -> None:
        r_rtmp = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="RTMP",
            video_codec="H.264",
            resolution="HD_1080p",
            streaming_fps="59.94p",
        )
        self.assertTrue(r_rtmp.admitted)
        self.assertEqual(r_rtmp.bitrate_mbps, 9.0)

        r_rtmps = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="RTMPS",
            video_codec="H.264",
            resolution="2K",
            streaming_fps="29.97p",
        )
        self.assertTrue(r_rtmps.admitted)
        self.assertEqual(r_rtmps.srt_encryption, "TLS")
        self.assertEqual(r_rtmps.bitrate_mbps, 13.0)

        r_srt = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="SRT",
            video_codec="H.265",
            srt_encryption="AES-128",
            resolution="4K",
            streaming_fps="50p",
        )
        self.assertTrue(r_srt.admitted)
        self.assertEqual(r_srt.bitrate_mbps, 38.0)

    def test_72_streaming_2398p_and_24p_unsupported_eopnotsupp(self) -> None:
        for fps in ("23.98p", "24p", "24.00p"):
            r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
                protocol="SRT",
                video_codec="H.265",
                resolution="4K",
                streaming_fps=fps,
            )
            self.assertFalse(r.admitted, fps)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.streaming_24p_rejected)

    def test_73_rtmp_rtmps_reject_h265_and_bad_keys(self) -> None:
        r_codec = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="RTMP",
            video_codec="H.265",
        )
        self.assertFalse(r_codec.admitted)
        self.assertEqual(r_codec.errno_code, p322.EINVAL_ERRNO)

        r_key = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="RTMP",
            video_codec="H.264",
            rtmp_stream_key_valid=False,
        )
        self.assertFalse(r_key.admitted)
        self.assertEqual(r_key.errno_code, p322.EINVAL_ERRNO)

        r_srt_key = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="SRT",
            video_codec="H.265",
            srt_encryption="AES-256",
            srt_passphrase="short",
        )
        self.assertFalse(r_srt_key.admitted)
        self.assertEqual(r_srt_key.errno_code, p322.EINVAL_ERRNO)

    def test_74_rtmps_untrusted_cert_blocked_eacces(self) -> None:
        r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            protocol="RTMPS",
            video_codec="H.264",
            rtmps_cert_trusted=False,
            root_cert_error_mode="Does Not Connect",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p322.EACCES_ERRNO)

    def test_75_movie_rec_during_streaming_blocks_internal_4k_on_4k_or_2k_hfr(self) -> None:
        for res, fps in (("4K", "29.97p"), ("4K", "59.94p"), ("2K", "59.94p"), ("2K", "50p")):
            r_blk = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
                protocol="SRT",
                video_codec="H.265",
                resolution=res,
                streaming_fps=fps,
                movie_rec_during_streaming="Enable",
                requested_internal_rec_resolution="4K",
                target_slot=p322.SLOT_2,
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, p322.EOPNOTSUPP_ERRNO)
            self.assertTrue(r_blk.internal_4k_rec_blocked)

            r_hd = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
                protocol="SRT",
                video_codec="H.265",
                resolution=res,
                streaming_fps=fps,
                movie_rec_during_streaming="Enable",
                requested_internal_rec_resolution="HD",
                target_slot=p322.SLOT_2,
            )
            self.assertTrue(r_hd.admitted)
            self.assertTrue(r_hd.menu_playback_ftp_sleep_locked)

    def test_76_zero_rf_firewall_blocks_wifi_and_airplane_off(self) -> None:
        for kw in (
            {"transport": p322.TRANSPORT_WIFI},
            {"transport": p322.TRANSPORT_BLE_TETHER},
            {"airplane_mode": "Off"},
        ):
            r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(**kw)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EPERM_ERRNO)
            self.assertTrue(r.zero_rf_firewall_triggered)
            self.assertEqual(r.rf_packets_transmitted, 0)
            self.assertEqual(r.rf_nvs_mutation_bytes, 0)

    def test_77_slot1_tier0_vault_blocks_rec_during_streaming_and_ftp_writes_erofs(self) -> None:
        for kw in (
            {
                "movie_rec_during_streaming": "Enable",
                "requested_internal_rec_resolution": "HD",
                "target_slot": p322.SLOT_1,
            },
            {"operation": "FTP_Write_Slot1", "target_slot": p322.SLOT_1},
            {"operation": "Slot1_Create_Dir", "target_slot": p322.SLOT_1},
        ):
            r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(**kw)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p322.EROFS_ERRNO)
            self.assertTrue(r.tier0_vault_firewall_triggered)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)
            self.assertEqual(r.slot1_vault_streaming_mutation_bytes, 0)

    def test_78_passive_ftp_readonly_pull_allowed_zero_slot1_writes(self) -> None:
        r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            operation="FTP_ReadOnly_Pull",
            target_slot=p322.SLOT_1,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.rf_packets_transmitted, 0)

    def test_79_reset_network_set_preserves_airplane_mode_on(self) -> None:
        r_cam = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r_cam.reset_applied, "CameraSettingsReset_Resisted_Network")
        self.assertEqual(r_cam.airplane_mode, "On")

        r_net = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            reset_network_settings_applied=True,
        )
        self.assertEqual(r_net.reset_applied, "ResetNetworkSet_Preserves_AirplaneMode_On")
        self.assertEqual(r_net.airplane_mode, "On")

    def test_80_fx6_dormant_rtmp_srt_qos_rejected_eopnotsupp(self) -> None:
        for proto in ("RTMP", "RTMPS", "SRT", "QoS_Streaming"):
            r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
                body_profile=p322.BODY_MODEL_FX6,
                protocol=proto,
            )
            self.assertFalse(r.admitted, proto)
            self.assertEqual(r.errno_code, p322.EOPNOTSUPP_ERRNO)

    def test_81_fx6_ftp_readonly_pull_allowed(self) -> None:
        r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
            body_profile=p322.BODY_MODEL_FX6,
            operation="FTP_ReadOnly_Pull",
            protocol="FTPES",
            target_slot=p322.SLOT_2,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.rf_packets_transmitted, 0)

    def test_82_all_streaming_resolutions_and_bitrates_valid(self) -> None:
        for res in p322.FX3_STREAMING_RESOLUTIONS:
            for fps in p322.FX3_STREAMING_FPS:
                r = p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(
                    protocol="SRT",
                    video_codec="H.265",
                    resolution=res,
                    streaming_fps=fps,
                )
                self.assertTrue(r.admitted)
                self.assertGreater(r.bitrate_mbps, 0.0)

    def test_83_invalid_streaming_args_raise(self) -> None:
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(protocol="WEBRTC")
        with self.assertRaises(p322.Stage67Phase322Error):
            p322.simulate_network_streaming_and_zero_rf_slot1_vault_hil(target_slot=3)

    def test_84_redline_zero_fault_counters_in_payload(self) -> None:
        rep = p322.run_phase322_steadyshot_47focal_selftimer_zebra_streaming_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertEqual(red["fx3_focal_length_steps_count"], 47)
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
            "steadyshot_active_lockout_bypass_events",
            "dormant_dynamic_active_exposed_events",
            "dormant_movie_selftimer_exposed_events",
            "fx3_led8_tally_confusion_events",
            "zebra_peaking_hdmi_clean_feed_leaked_pixels",
            "fx6_zebra_simultaneous_both_bypass_events",
            "streaming_24p_bypass_events",
            "streaming_rec_4k_lock_bypass_events",
            "rf_packets_transmitted",
            "rf_nvs_mutation_bytes",
            "slot1_data_sector_writes",
            "slot1_vault_streaming_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 67 Wiring (Tests 85..90)
    # ------------------------------------------------------------------

    def test_85_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_steadyshot_47focal_selftimer_zebra_streaming_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("67/67", proc.stdout)

    def test_86_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p322.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 322 Stage 67 (67/67 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p322.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "67/67")
        self.assertTrue(parsed["is_67th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_87_no_hardcoded_usr_bin_python3_in_stage67_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_steadyshot_47focal_selftimer_zebra_streaming_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_88_suite_default_config_enables_stage67_and_full_run_contains_67_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase322_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil)
        self.assertTrue(cfg.include_stage67)
        self.assertTrue(cfg.stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil)

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 67)
        s67 = rep["stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil"]
        self.assertTrue(s67["all_checks_passed"])
        self.assertTrue(s67["is_67th_stage_milestone"])
        self.assertEqual(s67["milestone"], "67/67")
        self.assertEqual(s67["phase_number"], 322)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_89_suite_skip_flags_and_summary_cli_for_stage67(self) -> None:
        for flag in ("--skip-stage67", "--no-include-stage67", "--skip-phase322"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage67"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage67", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_steadyshot_47focal_selftimer_zebra_streaming_hil=CLEAN_ROOM_SYNTHETIC("
            "m67=67/67,focal=47,ss_byp=0,dyn_byp=0,mst_byp=0,hdmi_px=0,s24p_byp=0,rf_tx=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_90_suite_tamper_47focal_rf_tx_or_slot1_vault_detected(self) -> None:
        with unittest.mock.patch.object(p322, "FX3_FOCAL_LENGTH_STEPS_COUNT", 46):
            r1 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(r1["all_checks_passed"])

        with unittest.mock.patch.object(p322, "RF_PACKETS_TRANSMITTED", 1):
            r2 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(r2["all_checks_passed"])

        with unittest.mock.patch.object(p322, "SLOT1_AVF_INFO_MUTATED", True):
            r3 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(r3["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
