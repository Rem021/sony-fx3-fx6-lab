#!/usr/bin/env python3
"""Unit tests for Phase 289 (Stage 58, 58/58):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-48
Picture Profile `PP1..PP11` (`PP11 = S-Cinetone` Out-of-Box Default for BOTH Movie AND Still),
`Creative Look` 10 Presets + `Custom Look 1..6` & `D-Range Optimizer` Lockout, `Log Shooting`
Mutual Exclusion & `[Picture Profile] -> [Reset]` Persistence Split HIL,
`[White Balance]` 13-Mode & `Custom 1..3` Reset Survival vs `CAMSET01..10.DAT` Card Exclusion &
`Cine EI` Auto-WB Lockout HIL, and
`[Metering Mode]` 5-Mode, `[Spot Metering Point]` (`Focus Point Link`) & `Clear Image Zoom`
`[Multi]` Clamp HIL Co-Emulator (76 dual-mode tests).
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
import realhw_pp_scinetone_creativelook_wb_metering_coemulator as p289  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated stages for <50ms flag/override tests."""
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
]


class TestPhase289Stage58Wave48HilCoEmulator(unittest.TestCase):
    """76 dual-mode tests for Phase 289 Stage 58 (58/58)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_audit = p289.run_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil()
        cls.clean_audit = p289.run_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil(
            force_clean_room=True
        )
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite()
        cls.default_suite_elapsed = time.monotonic() - t0

        t1 = time.monotonic()
        cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Redlines & Dual-Mode 11-Donor O_RDONLY Audit (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_phase_and_milestone_constants(self) -> None:
        self.assertEqual(p289.SCHEMA_ID, "realhw_pp_scinetone_creativelook_wb_metering_coemulator_v1")
        self.assertEqual(p289.PHASE_289_SCHEMA, p289.SCHEMA_ID)
        self.assertEqual(p289.PHASE_289_VERSION, "289.0.0")
        self.assertEqual(p289.PHASE_NUMBER, 289)
        self.assertEqual(p289.STAGE_INDEX, 58)
        self.assertEqual(p289.STAGE_TOTAL, 58)
        self.assertEqual(p289.MILESTONE_LABEL, "58/58")
        self.assertEqual(p289.STAGE_NAME, "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil")
        self.assertEqual(p289.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p289.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p289.FX3_HELP_GUIDE_ID, "ilc/2210")

    def test_02_hard_safety_redline_constants_locked(self) -> None:
        self.assertTrue(p289.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p289.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p289.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p289.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p289.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p289.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p289.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p289.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        for zero_val in (
            p289.NOP_COUNT,
            p289.GUEST_CODE_MODIFICATION_BYTES,
            p289.CP_MUTATION_BYTES,
            p289.WBI_MUTATION_BYTES,
            p289.CALIBRATION_MUTATION_BYTES,
            p289.CNFLASHA_MUTATION_BYTES,
            p289.NVRAM_PERSISTENT_WRITES,
            p289.BK4_PERSISTENT_NVRAM_WRITES,
            p289.PHYSICAL_DEVICE_WRITES,
            p289.EMMC_NFLASHA_WRITE_COUNT,
            p289.EMMC_MUTATION_BYTES,
            p289.EMMC_CORRUPTIONS,
            p289.SPI_NOR_MUTATION_BYTES,
            p289.OTP_FUSE_TOUCHES,
            p289.RPMB_COUNTER_INCREMENTS,
            p289.PHYSICAL_USB_PACKETS_EMITTED,
            p289.PASSIVE_TX_BYTES_EMITTED,
            p289.PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
            p289.WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
            p289.METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
            p289.RSV_ORPHAN_COUNT,
            p289.WF12_00342260_HITS,
            p289.APPFW_CRASHES,
            p289.NULL_GPIO_DEREFS,
            p289.MAILBOX_STALLS,
            p289.STOCK_CP_FAULT_COUNT,
            p289.RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_val, 0)

    def test_03_default_and_clean_room_reports_both_pass(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p289.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.default_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.clean_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.default_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.clean_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_04_is_forced_clean_room_both_env_vars(self) -> None:
        self.assertFalse(p289.is_forced_clean_room({}))
        self.assertTrue(p289.is_forced_clean_room({p289.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p289.is_forced_clean_room({p289.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertTrue(p289.is_forced_clean_room({p289.ENV_CLEAN_ROOM_TEST: "yes"}))
        self.assertTrue(p289.is_forced_clean_room({p289.ENV_FORCE_CLEAN_ROOM: "on"}))

    def test_05_clean_room_override_disables_disk_reads(self) -> None:
        env = {p289.ENV_CLEAN_ROOM_TEST: "1"}
        resolved = p289.resolve_phase289_donor_paths(env=env)
        for p in resolved.values():
            self.assertIn(p289.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
        with unittest.mock.patch("os.open", side_effect=AssertionError("disk read in clean-room")):
            p289._CLEAN_ROOM_AUDIT_SINGLETON = None
            audit = p289.inspect_phase289_donors(env=env)
        self.assertEqual(audit.source_mode, p289.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreater(audit.fx3_appfw.bytes_read_total, 0)

    def test_06_clean_room_deterministic_digest(self) -> None:
        rep2 = p289.run_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil(
            force_clean_room=True
        )
        self.assertEqual(self.clean_audit["audit_digest_sha256"], rep2["audit_digest_sha256"])

    def test_07_local_donor_uses_bounded_o_rdonly_windows(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertLess(da["inspection_elapsed_s"], 1.0)
        for large_key in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
            self.assertTrue(da[large_key]["bounded_windows_only"])
            if da["source_mode"] == p289.SOURCE_MODE_LOCAL_DONOR:
                self.assertGreater(da[large_key]["bytes_read_total"], 0)
                self.assertLessEqual(da[large_key]["bytes_read_total"], 150_000)

    def test_08_open_os_o_rdonly_only_no_write_flags(self) -> None:
        sample = FX3_VM_DIR / "README.md"
        with unittest.mock.patch("os.open", wraps=os.open) as mock_open:
            raw = p289._read_bounded_o_rdonly(sample, 0, 128)
            self.assertEqual(len(raw), 128)
            mock_open.assert_called_once()
            flags = mock_open.call_args.args[1]
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)

    def test_09_read_bounded_o_rdonly_rejects_above_4096_bytes(self) -> None:
        with self.assertRaises(ValueError):
            p289._read_bounded_o_rdonly(FX3_VM_DIR / "README.md", 0, 4097)

    def test_10_all_11_donors_sizes_and_hashes_verified(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        for key, expected_size in p289.EXPECTED_DONOR_BYTES.items():
            self.assertEqual(da[key]["file_bytes"], expected_size, msg=key)
        for key in p289.EXPECTED_COMPACT_DONOR_SHA256:
            self.assertTrue(da[key]["sha256_verified"], msg=key)
            self.assertTrue(da[key]["uxd_container_ok"], msg=key)
        for key in p289.EXPECTED_LARGE_HEAD4K_SHA256:
            self.assertTrue(da[key]["head_sha256_verified"], msg=key)

    def test_11_missing_donor_root_gracefully_uses_clean_room(self) -> None:
        missing = {
            k: REPO_ROOT / "__nonexistent_phase289_missing__" / rel
            for k, rel in p289.DONOR_RELPATHS.items()
        }
        with unittest.mock.patch.object(p289, "resolve_phase289_donor_paths", return_value=missing):
            audit = p289.inspect_phase289_donors(force_clean_room=False, env={})
        self.assertEqual(audit.source_mode, p289.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)

    def test_12_four_language_uxc_marker_parity_verified(self) -> None:
        da = self.default_audit["donor_audit"]
        for key in ("fx3_string_en_f", "fx3_string_sc_f", "fx3_string_tc_f", "fx3_string_ja_f"):
            hits = da[key]["marker_hits"]
            self.assertTrue(all(v == 1 for v in hits.values()), msg=f"{key}: {hits}")

    def test_13_fx3_and_fx6_appfw_wave48_window_tokens_verified(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["pp_scinetone_creativelook_proven"])
        self.assertTrue(da["wb_13mode_cineei_custom_proven"])
        self.assertTrue(da["metering_5mode_spot_link_proven"])
        self.assertTrue(all(v == 1 for v in da["fx3_appfw"]["window_hits"].values()))
        self.assertTrue(all(v == 1 for v in da["fx6_appfw"]["window_hits"].values()))

    def test_14_redlines_block_in_report_all_locked_zero(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["emmc_nflasha_write_count"], 0)
            self.assertEqual(red["physical_usb_packets_emitted"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(red["pp_creative_look_or_reset_wipe_misroute_events"], 0)
            self.assertEqual(red["wb_cine_ei_auto_or_camset_custom_leak_events"], 0)
            self.assertEqual(red["metering_spot_link_or_ciz_multi_bypass_events"], 0)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 58A — PP1..PP11 (PP11 Out-of-Box Default), Creative
    #          Look & DRO Lockout, Log Shooting & Reset Split (19 tests)
    # ------------------------------------------------------------------
    def test_15_pp11_scinetone_is_out_of_box_default_for_both_movie_and_still(self) -> None:
        for mode in (p289.SHOOT_MODE_MOVIE, p289.SHOOT_MODE_SQ, p289.SHOOT_MODE_STILL):
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(shoot_mode=mode)
            self.assertTrue(r.admitted, msg=mode)
            self.assertEqual(r.out_of_box_default_pp, "PP11")
            self.assertTrue(r.out_of_box_default_applies_movie_and_still)
            self.assertEqual(r.effective_picture_profile, "PP11")
            self.assertEqual(r.effective_pp_gamma, "S-Cinetone")
            self.assertEqual(r.effective_pp_color_mode, "S-Cinetone")
            self.assertFalse(r.different_set_still_mv_pp)

    def test_16_all_pp1_to_pp11_recipes_verified(self) -> None:
        self.assertEqual(len(p289.PP1_TO_PP11), 11)
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP7"]["gamma"], "S-Log2")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP8"]["gamma"], "S-Log3")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP8"]["color_mode"], "S-Gamut3.Cine")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP9"]["color_mode"], "S-Gamut3")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP10"]["gamma"], "HLG2")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP10"]["color_mode"], "BT.2020")
        self.assertEqual(p289.PP_FACTORY_RECIPES["PP11"]["gamma"], "S-Cinetone")
        for pp in p289.PP1_TO_PP11 + p289.PPLUT_MODES:
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(configured_picture_profile=pp)
            self.assertTrue(r.admitted, msg=pp)
            self.assertEqual(r.effective_picture_profile, pp)
            self.assertEqual(r.effective_creative_look, "-")
            self.assertTrue(r.creative_look_hard_locked)
            self.assertEqual(r.effective_dro, "Off")
            self.assertTrue(r.dro_forced_off)

    def test_17_pp_active_hard_locks_creative_look_override_eopnotsupp(self) -> None:
        for pp in ("PP1", "PP8", "PP11", "PPLUT1"):
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                configured_picture_profile=pp,
                configured_creative_look="VV2",
                requested_creative_look_override=True,
            )
            self.assertFalse(r.admitted, msg=pp)
            self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.reason_code, "PICTURE_PROFILE_ACTIVE_LOCKS_CREATIVE_LOOK")

    def test_18_pp_active_hard_locks_dro_override_eopnotsupp(self) -> None:
        for dro in p289.DRO_MODES[1:]:
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                configured_picture_profile="PP11",
                configured_dro=dro,
                requested_dro_override=True,
            )
            self.assertFalse(r.admitted, msg=dro)
            self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.reason_code, "PICTURE_PROFILE_ACTIVE_FORCES_DRO_OFF")

    def test_19_pp_off_unlocks_creative_look_10_presets_and_custom_1_to_6(self) -> None:
        self.assertEqual(len(p289.CREATIVE_LOOK_10_PRESETS), 10)
        self.assertEqual(len(p289.CREATIVE_LOOK_CUSTOM_SLOTS), 6)
        self.assertEqual(len(p289.CREATIVE_LOOK_8_PARAMS), 8)
        for look in p289.VALID_CREATIVE_LOOK_CHOICES:
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                shoot_mode=p289.SHOOT_MODE_MOVIE,
                configured_picture_profile=p289.PP_OFF,
                configured_creative_look=look,
                configured_dro="D-Range Optimizer: Auto",
            )
            self.assertTrue(r.admitted, msg=look)
            self.assertEqual(r.effective_creative_look, look)
            self.assertFalse(r.creative_look_hard_locked)
            self.assertEqual(r.effective_dro, "D-Range Optimizer: Auto")
            self.assertFalse(r.dro_forced_off)

    def test_20_clarity_allowed_only_in_single_still_and_locked_in_movie_sq_cont(self) -> None:
        ok = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            shoot_mode=p289.SHOOT_MODE_STILL,
            drive_mode=p289.DRIVE_MODE_SINGLE,
            configured_picture_profile=p289.PP_OFF,
            configured_creative_look="ST",
            requested_clarity_edit=True,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.clarity_param_locked)

        for sm, dm in (
            (p289.SHOOT_MODE_MOVIE, p289.DRIVE_MODE_SINGLE),
            (p289.SHOOT_MODE_SQ, p289.DRIVE_MODE_SINGLE),
            (p289.SHOOT_MODE_STILL, p289.DRIVE_MODE_CONTINUOUS),
        ):
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                shoot_mode=sm,
                drive_mode=dm,
                configured_picture_profile=p289.PP_OFF,
                configured_creative_look="FL",
                requested_clarity_edit=True,
            )
            self.assertFalse(r.admitted, msg=f"{sm}/{dm}")
            self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.reason_code, "CREATIVE_LOOK_CLARITY_LOCKED_IN_MOVIE_OR_CONT")

    def test_21_sharpness_range_locked_in_movie_and_saturation_locked_in_bw_se(self) -> None:
        sr_blk = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            shoot_mode=p289.SHOOT_MODE_MOVIE,
            configured_picture_profile=p289.PP_OFF,
            requested_sharpness_range_edit=True,
        )
        self.assertFalse(sr_blk.admitted)
        self.assertEqual(sr_blk.errno_code, p289.EOPNOTSUPP_ERRNO)

        for mono in ("BW", "SE"):
            sat_blk = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                shoot_mode=p289.SHOOT_MODE_STILL,
                configured_picture_profile=p289.PP_OFF,
                configured_creative_look=mono,
                requested_saturation_edit=True,
            )
            self.assertFalse(sat_blk.admitted, msg=mono)
            self.assertEqual(sat_blk.errno_code, p289.EOPNOTSUPP_ERRNO)

    def test_22_log_shooting_3_modes_hard_lock_pp_creative_look_dro_and_route_display_lut(self) -> None:
        self.assertEqual(len(p289.DISPLAY_LUT_OPTIONS), 19)
        for lm, lut in (
            (p289.LOG_SHOOTING_FLEXIBLE_ISO, "s709"),
            (p289.LOG_SHOOTING_CINE_EI_QUICK, "709(800%)"),
            (p289.LOG_SHOOTING_CINE_EI, "User16"),
        ):
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                configured_picture_profile="PP11",
                configured_log_shooting=lm,
                selected_display_lut=lut,
            )
            self.assertTrue(r.admitted, msg=lm)
            self.assertEqual(r.effective_picture_profile, "Locked (Log Shooting)")
            self.assertEqual(r.effective_creative_look, "-")
            self.assertTrue(r.creative_look_hard_locked)
            self.assertEqual(r.effective_dro, "Off")
            self.assertTrue(r.dro_forced_off)
            self.assertEqual(r.effective_display_lut, lut)

    def test_23_log_shooting_rejects_creative_look_and_dro_overrides_eopnotsupp(self) -> None:
        r1 = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            configured_log_shooting=p289.LOG_SHOOTING_CINE_EI,
            requested_creative_look_override=True,
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p289.EOPNOTSUPP_ERRNO)
        self.assertEqual(r1.reason_code, "LOG_SHOOTING_LOCKS_CREATIVE_LOOK")

        r2 = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            configured_log_shooting=p289.LOG_SHOOTING_FLEXIBLE_ISO,
            requested_dro_override=True,
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p289.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.reason_code, "LOG_SHOOTING_LOCKS_DRO")

    def test_24_camera_settings_reset_restores_pp11_but_preserves_pp1_11_internal_edits(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            different_set_still_mv_pp=True,
            configured_picture_profile="PP8",
            pp_internal_edits_present=True,
            reset_action=p289.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, "PP11")
        self.assertTrue(r.different_set_still_mv_pp)
        self.assertTrue(r.pp_internal_edits_survived)
        self.assertFalse(r.pp_recipe_restored_to_factory)

    def test_25_initialize_also_preserves_pp1_11_internal_edits_while_clearing_diff_set(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            different_set_still_mv_pp=True,
            configured_picture_profile="PP8",
            pp_internal_edits_present=True,
            reset_action=p289.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, "PP11")
        self.assertFalse(r.different_set_still_mv_pp)
        self.assertTrue(r.pp_internal_edits_survived)
        self.assertFalse(r.pp_recipe_restored_to_factory)

    def test_26_only_explicit_picture_profile_reset_restores_factory_recipe(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            configured_picture_profile="PP8",
            pp_internal_edits_present=True,
            reset_action=p289.RESET_ACTION_PICTURE_PROFILE_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, "PP8")
        self.assertFalse(r.pp_internal_edits_survived)
        self.assertTrue(r.pp_recipe_restored_to_factory)

    def test_27_wiping_pp_internals_on_camera_reset_rejected_eopnotsupp(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            pp_internal_edits_present=True,
            reset_action=p289.RESET_ACTION_CAMERA_SETTINGS_RESET,
            wipe_pp_internals_on_camera_reset=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "PP_INTERNALS_SURVIVE_CAMERA_RESET_AND_INITIALIZE")

    def test_28_fx6_base_look_scene_file_contrast_verified(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            body_profile=p289.BODY_MODEL_FX6,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, p289.FX6_BASE_LOOK_SCINETONE)
        self.assertFalse(r.out_of_box_default_applies_movie_and_still)
        self.assertIn("Base Look", r.pp_menu_path)
        self.assertIn("Scene File", r.fx6_contrast_model)

    def test_29_fx3a_inherits_identical_pp11_creative_look_rules(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            body_profile=p289.BODY_MODEL_FX3A,
            shoot_mode=p289.SHOOT_MODE_STILL,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, "PP11")
        self.assertTrue(r.creative_look_hard_locked)

    def test_30_all_dro_modes_valid_when_pp_off_and_log_off(self) -> None:
        self.assertEqual(len(p289.DRO_MODES), 7)
        for dro in p289.DRO_MODES:
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
                configured_picture_profile=p289.PP_OFF,
                configured_dro=dro,
            )
            self.assertTrue(r.admitted, msg=dro)
            self.assertEqual(r.effective_dro, dro)
            self.assertFalse(r.dro_forced_off)

    def test_31_invalid_pp_creative_look_dro_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"shoot_mode": "Timelapse"},
            {"drive_mode": "Bulb"},
            {"configured_picture_profile": "PP12"},
            {"configured_log_shooting": "S-Log2 Auto"},
            {"selected_display_lut": "User99"},
            {"configured_creative_look": "MONOCHROME"},
            {"configured_dro": "HDR Auto"},
            {"reset_action": "UNKNOWN"},
        ):
            r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p289.EINVAL_ERRNO, msg=str(kwargs))

    def test_32_pillar_a_passed_and_zero_physical_writes(self) -> None:
        pa = self.clean_audit["pillar_a_pp_scinetone_creativelook_dro_reset_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["fx3_oob_movie_pp11"]["physical_device_writes"], 0)
        self.assertEqual(pa["camera_settings_reset_preserves_pp_edits"]["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(pa["explicit_pp_reset_restores_factory"]["pp_creative_look_or_reset_wipe_misroute_events"], 0)

    def test_33_network_reset_does_not_wipe_pp_profile_selection(self) -> None:
        r = p289.simulate_pp_scinetone_creativelook_dro_reset_hil(
            configured_picture_profile="PP8",
            pp_internal_edits_present=True,
            reset_action=p289.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_picture_profile, "PP8")
        self.assertTrue(r.pp_internal_edits_survived)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 58B — White Balance 13-Mode, Cine EI Auto-WB
    #          Lockout & Custom 1..3 CAMSET vs M1..M4 & Reset Split (18 tests)
    # ------------------------------------------------------------------
    def test_34_wb_13_base_and_15_discrete_modes_all_modeled(self) -> None:
        self.assertEqual(len(p289.FX3_WB_13_BASE_MODES), 13)
        self.assertEqual(len(p289.VALID_FX3_WB_MODES), 15)
        pb = self.clean_audit["pillar_b_wb_13mode_cineei_camset_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(len(pb["wb_mode_matrix"]), 15)
        self.assertTrue(all(v["admitted"] for v in pb["wb_mode_matrix"].values()))

    def test_35_flash_wb_still_only_and_rejected_in_movie_sq(self) -> None:
        ok = p289.simulate_white_balance_13mode_cineei_camset_hil(
            shoot_mode=p289.SHOOT_MODE_STILL,
            requested_wb_mode=p289.WB_FLASH,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_wb_mode, p289.WB_FLASH)

        for sm in (p289.SHOOT_MODE_MOVIE, p289.SHOOT_MODE_SQ):
            blk = p289.simulate_white_balance_13mode_cineei_camset_hil(
                shoot_mode=sm,
                requested_wb_mode=p289.WB_FLASH,
            )
            self.assertFalse(blk.admitted, msg=sm)
            self.assertEqual(blk.errno_code, p289.EOPNOTSUPP_ERRNO)
            self.assertEqual(blk.reason_code, "FLASH_WB_STILL_ONLY_LOCKED_IN_MOVIE_SQ")

    def test_36_ctemp_filter_2500k_to_9900k_and_gm_ab_axes_bounds(self) -> None:
        for kelvin, gm, ab in ((2500, -7, -7), (5600, 0, 0), (9900, 7, 7)):
            r = p289.simulate_white_balance_13mode_cineei_camset_hil(
                requested_wb_mode=p289.WB_CTEMP_FILTER,
                ctemp_kelvin=kelvin,
                gm_axis=gm,
                ab_axis=ab,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.ctemp_kelvin, kelvin)
            self.assertEqual(r.gm_axis, gm)
            self.assertEqual(r.ab_axis, ab)

    def test_37_cine_ei_and_quick_lock_out_auto_and_underwater_auto_wb(self) -> None:
        for log_m in (p289.LOG_SHOOTING_CINE_EI, p289.LOG_SHOOTING_CINE_EI_QUICK):
            for auto_wb in (p289.WB_AUTO, p289.WB_UNDERWATER_AUTO):
                r = p289.simulate_white_balance_13mode_cineei_camset_hil(
                    configured_log_shooting=log_m,
                    requested_wb_mode=auto_wb,
                )
                self.assertFalse(r.admitted, msg=f"{log_m}/{auto_wb}")
                self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
                self.assertEqual(r.reason_code, "CINE_EI_LOCKS_OUT_AUTO_AND_UNDERWATER_AUTO_WB")

    def test_38_cine_ei_admits_presets_ctemp_and_custom_1_to_3(self) -> None:
        for wb in (
            p289.WB_DAYLIGHT,
            p289.WB_CTEMP_FILTER,
            p289.WB_CUSTOM_1,
            p289.WB_CUSTOM_2,
            p289.WB_CUSTOM_3,
        ):
            r = p289.simulate_white_balance_13mode_cineei_camset_hil(
                configured_log_shooting=p289.LOG_SHOOTING_CINE_EI,
                requested_wb_mode=wb,
                ctemp_kelvin=4300,
            )
            self.assertTrue(r.admitted, msg=wb)
            self.assertEqual(r.effective_wb_mode, wb)
            self.assertTrue(r.cine_ei_auto_wb_locked)

    def test_39_flexible_iso_allows_auto_wb_unlike_cine_ei(self) -> None:
        r = p289.simulate_white_balance_13mode_cineei_camset_hil(
            configured_log_shooting=p289.LOG_SHOOTING_FLEXIBLE_ISO,
            requested_wb_mode=p289.WB_AUTO,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_wb_mode, p289.WB_AUTO)

    def test_40_priority_set_in_awb_and_shutter_awb_lock_still_scope(self) -> None:
        for prio in p289.AWB_PRIORITY_MODES:
            for lock_m in ("Shut. Halfway", "Cont. Shooting"):
                r = p289.simulate_white_balance_13mode_cineei_camset_hil(
                    shoot_mode=p289.SHOOT_MODE_STILL,
                    requested_wb_mode=p289.WB_AUTO,
                    awb_priority_mode=prio,
                    shutter_awb_lock_mode=lock_m,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.awb_priority_mode, prio)
                self.assertTrue(r.shutter_awb_lock_active)

        # In Movie mode, Shutter AWB Lock is inactive
        mv = p289.simulate_white_balance_13mode_cineei_camset_hil(
            shoot_mode=p289.SHOOT_MODE_MOVIE,
            requested_wb_mode=p289.WB_AUTO,
            shutter_awb_lock_mode="Shut. Halfway",
        )
        self.assertTrue(mv.admitted)
        self.assertFalse(mv.shutter_awb_lock_active)

    def test_41_shockless_wb_active_only_in_movie_and_sq(self) -> None:
        for sw in ("1 (Fast)", "2", "3 (Slow)"):
            mv = p289.simulate_white_balance_13mode_cineei_camset_hil(
                shoot_mode=p289.SHOOT_MODE_MOVIE,
                requested_wb_mode=p289.WB_DAYLIGHT,
                shockless_wb_mode=sw,
            )
            self.assertTrue(mv.admitted)
            self.assertTrue(mv.shockless_wb_active)

        st = p289.simulate_white_balance_13mode_cineei_camset_hil(
            shoot_mode=p289.SHOOT_MODE_STILL,
            requested_wb_mode=p289.WB_DAYLIGHT,
            shockless_wb_mode="2",
        )
        self.assertTrue(st.admitted)
        self.assertFalse(st.shockless_wb_active)

    def test_42_custom_wb_capture_blocked_in_log_or_slog3_or_pplut(self) -> None:
        blk_log = p289.simulate_white_balance_13mode_cineei_camset_hil(
            configured_log_shooting=p289.LOG_SHOOTING_CINE_EI,
            requested_wb_mode=p289.WB_CUSTOM_1,
            custom_wb_capture_requested=True,
        )
        self.assertFalse(blk_log.admitted)
        self.assertEqual(blk_log.errno_code, p289.EOPNOTSUPP_ERRNO)

        blk_pp8 = p289.simulate_white_balance_13mode_cineei_camset_hil(
            configured_picture_profile="PP8",
            requested_wb_mode=p289.WB_CUSTOM_2,
            custom_wb_capture_requested=True,
        )
        self.assertFalse(blk_pp8.admitted)
        self.assertEqual(blk_pp8.errno_code, p289.EOPNOTSUPP_ERRNO)

        ok_pp11 = p289.simulate_white_balance_13mode_cineei_camset_hil(
            configured_log_shooting=p289.LOG_SHOOTING_OFF,
            configured_picture_profile="PP11",
            requested_wb_mode=p289.WB_CUSTOM_1,
            custom_wb_capture_requested=True,
        )
        self.assertTrue(ok_pp11.admitted)

    def test_43_custom_1_to_3_survive_camera_settings_reset_but_wiped_by_initialize(self) -> None:
        for slot in p289.CUSTOM_WB_SLOTS:
            csr = p289.simulate_white_balance_13mode_cineei_camset_hil(
                requested_wb_mode=slot,
                reset_action=p289.RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(csr.admitted)
            self.assertEqual(csr.effective_wb_mode, p289.WB_AUTO)
            self.assertTrue(csr.custom_wb_1_3_survived)
            self.assertFalse(csr.custom_wb_1_3_wiped_by_initialize)

            ini = p289.simulate_white_balance_13mode_cineei_camset_hil(
                requested_wb_mode=slot,
                reset_action=p289.RESET_ACTION_INITIALIZE,
            )
            self.assertTrue(ini.admitted)
            self.assertFalse(ini.custom_wb_1_3_survived)
            self.assertTrue(ini.custom_wb_1_3_wiped_by_initialize)

    def test_44_custom_1_to_3_excluded_from_camset_dat_and_saved_only_to_m1_m4(self) -> None:
        for slot in p289.CUSTOM_WB_SLOTS:
            camset = p289.simulate_white_balance_13mode_cineei_camset_hil(
                requested_wb_mode=slot,
                storage_target=p289.STORAGE_TARGET_CAMSET,
            )
            self.assertFalse(camset.admitted, msg=slot)
            self.assertEqual(camset.errno_code, p289.EOPNOTSUPP_ERRNO)
            self.assertFalse(camset.custom_wb_saved_to_camset)

            m14 = p289.simulate_white_balance_13mode_cineei_camset_hil(
                requested_wb_mode=slot,
                storage_target=p289.STORAGE_TARGET_MEMORY_M1_M4,
            )
            self.assertTrue(m14.admitted, msg=slot)
            self.assertTrue(m14.custom_wb_saved_to_m1_m4)
            self.assertFalse(m14.custom_wb_saved_to_camset)

    def test_45_camset_allows_fixed_presets_or_ctemp_while_blocking_custom_1_3(self) -> None:
        ok = p289.simulate_white_balance_13mode_cineei_camset_hil(
            requested_wb_mode=p289.WB_CTEMP_FILTER,
            ctemp_kelvin=5600,
            storage_target=p289.STORAGE_TARGET_CAMSET,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.custom_wb_saved_to_camset)

    def test_46_slot1_tier0_vault_wb_save_blocked_erofs(self) -> None:
        r = p289.simulate_white_balance_13mode_cineei_camset_hil(
            requested_wb_mode=p289.WB_CUSTOM_1,
            storage_target=p289.STORAGE_TARGET_SLOT1_VAULT,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p289.EROFS_ERRNO)
        self.assertEqual(r.physical_device_writes, 0)

    def test_47_fx6_wht_bal_switch_and_cine_ei_atw_lockout_contrast(self) -> None:
        ok = p289.simulate_white_balance_13mode_cineei_camset_hil(
            body_profile=p289.BODY_MODEL_FX6,
            requested_wb_mode=p289.WB_DAYLIGHT,
        )
        self.assertTrue(ok.admitted)
        self.assertIn("WHT BAL", ok.wb_menu_path)

        atw_blk = p289.simulate_white_balance_13mode_cineei_camset_hil(
            body_profile=p289.BODY_MODEL_FX6,
            configured_log_shooting=p289.LOG_SHOOTING_CINE_EI,
            requested_wb_mode=p289.WB_AUTO,
        )
        self.assertFalse(atw_blk.admitted)
        self.assertEqual(atw_blk.errno_code, p289.EOPNOTSUPP_ERRNO)
        self.assertEqual(atw_blk.reason_code, "FX6_CINE_EI_LOCKS_ATW_AUTO_WB")

    def test_48_invalid_wb_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"shoot_mode": "PhotoBurst"},
            {"configured_log_shooting": "RawLog"},
            {"requested_wb_mode": "KelvinAuto"},
            {"ctemp_kelvin": 2400},
            {"ctemp_kelvin": 10000},
            {"ctemp_kelvin": 5550},
            {"ctemp_kelvin": True},
            {"gm_axis": -8},
            {"gm_axis": 8},
            {"ab_axis": -8},
            {"ab_axis": 8},
            {"awb_priority_mode": "Cinema"},
            {"shutter_awb_lock_mode": "Always"},
            {"shockless_wb_mode": "4"},
            {"storage_target": "EEPROM"},
        ):
            r = p289.simulate_white_balance_13mode_cineei_camset_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p289.EINVAL_ERRNO, msg=str(kwargs))

    def test_49_all_4_fluorescent_variants_modeled_distinctly(self) -> None:
        fluor_modes = (
            p289.WB_FLUOR_WARM,
            p289.WB_FLUOR_COOL,
            p289.WB_FLUOR_DAY_WHITE,
            p289.WB_FLUOR_DAYLIGHT,
        )
        for fm in fluor_modes:
            r = p289.simulate_white_balance_13mode_cineei_camset_hil(
                configured_log_shooting=p289.LOG_SHOOTING_CINE_EI,
                requested_wb_mode=fm,
            )
            self.assertTrue(r.admitted, msg=fm)
            self.assertEqual(r.effective_wb_mode, fm)

    def test_50_network_reset_does_not_wipe_custom_wb_1_to_3(self) -> None:
        r = p289.simulate_white_balance_13mode_cineei_camset_hil(
            requested_wb_mode=p289.WB_CUSTOM_3,
            reset_action=p289.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_wb_mode, p289.WB_CUSTOM_3)
        self.assertTrue(r.custom_wb_1_3_survived)

    def test_51_pillar_b_zero_physical_writes_and_zero_leaks(self) -> None:
        pb = self.default_audit["pillar_b_wb_13mode_cineei_camset_hil"]
        for entry in pb["wb_mode_matrix"].values():
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(entry["wb_cine_ei_auto_or_camset_custom_leak_events"], 0)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 58C — Metering 5-Mode, Spot Point Link,
    #          Clear Image Zoom [Multi] Clamp & FX6 Contrast (15 tests)
    # ------------------------------------------------------------------
    def test_52_metering_5_base_and_6_discrete_modes_verified(self) -> None:
        self.assertEqual(len(p289.FX3_METERING_5_BASE_MODES), 5)
        self.assertEqual(len(p289.VALID_FX3_METERING_MODES), 6)
        pcd = self.clean_audit["pillar_c_d_metering_spot_link_ciz_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["metering_matrix"]), 6)
        self.assertTrue(all(v["admitted"] for v in pcd["metering_matrix"].values()))

    def test_53_spot_focus_point_link_couples_under_flexible_and_expand_spot(self) -> None:
        for spot_m in (p289.METERING_SPOT_STANDARD, p289.METERING_SPOT_LARGE):
            for fa in (p289.FOCUS_AREA_FLEXIBLE_SPOT, p289.FOCUS_AREA_EXPAND_SPOT):
                r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                    configured_metering_mode=spot_m,
                    focus_area=fa,
                    configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
                )
                self.assertTrue(r.admitted, msg=f"{spot_m}/{fa}")
                self.assertEqual(r.effective_spot_metering_point, p289.SPOT_POINT_FOCUS_LINK)
                self.assertTrue(r.spot_coupled_to_af_point)

    def test_54_spot_focus_point_link_collapses_to_center_under_wide_zone_center_fix(self) -> None:
        for fa in (p289.FOCUS_AREA_WIDE, p289.FOCUS_AREA_ZONE, p289.FOCUS_AREA_CENTER_FIX):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                configured_metering_mode=p289.METERING_SPOT_STANDARD,
                focus_area=fa,
                configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
            )
            self.assertTrue(r.admitted, msg=fa)
            self.assertEqual(r.effective_spot_metering_point, p289.SPOT_POINT_CENTER)
            self.assertFalse(r.spot_coupled_to_af_point)

    def test_55_ciz_gt_1_0x_clamps_to_multi_and_disables_face_priority(self) -> None:
        for ratio in (1.1, 1.5, 2.0):
            for m in (p289.METERING_SPOT_STANDARD, p289.METERING_SPOT_LARGE, p289.METERING_HIGHLIGHT):
                r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                    configured_metering_mode=m,
                    focus_area=p289.FOCUS_AREA_FLEXIBLE_SPOT,
                    configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
                    configured_face_prio_multi=p289.TOGGLE_ON,
                    clear_image_zoom_ratio=ratio,
                )
                self.assertTrue(r.admitted, msg=f"{ratio}/{m}")
                self.assertTrue(r.ciz_forced_multi_clamp_active)
                self.assertEqual(r.effective_metering_mode, p289.METERING_MULTI)
                self.assertEqual(r.effective_spot_metering_point, p289.SPOT_POINT_CENTER)
                self.assertFalse(r.spot_coupled_to_af_point)
                self.assertEqual(r.effective_face_prio_multi, p289.TOGGLE_OFF)
                self.assertFalse(r.restored_prior_metering_at_1x)

    def test_56_ciz_bypass_non_multi_rejected_eopnotsupp(self) -> None:
        r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_HIGHLIGHT,
            clear_image_zoom_ratio=1.5,
            force_non_multi_during_ciz=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "CIZ_ZOOM_FORCES_MULTI_METERING_CLAMP")

    def test_57_zoom_return_to_1_0x_cleanly_restores_spot_link_and_face_prio(self) -> None:
        spot_restore = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_SPOT_LARGE,
            focus_area=p289.FOCUS_AREA_FLEXIBLE_SPOT,
            configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
            clear_image_zoom_ratio=1.0,
        )
        self.assertTrue(spot_restore.admitted)
        self.assertFalse(spot_restore.ciz_forced_multi_clamp_active)
        self.assertTrue(spot_restore.restored_prior_metering_at_1x)
        self.assertEqual(spot_restore.effective_metering_mode, p289.METERING_SPOT_LARGE)
        self.assertEqual(spot_restore.effective_spot_metering_point, p289.SPOT_POINT_FOCUS_LINK)
        self.assertTrue(spot_restore.spot_coupled_to_af_point)

        multi_restore = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_MULTI,
            configured_face_prio_multi=p289.TOGGLE_ON,
            clear_image_zoom_ratio=1.0,
        )
        self.assertTrue(multi_restore.admitted)
        self.assertEqual(multi_restore.effective_face_prio_multi, p289.TOGGLE_ON)

    def test_58_desqueeze_display_locks_face_priority_in_multi_metering_off(self) -> None:
        r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_MULTI,
            configured_face_prio_multi=p289.TOGGLE_ON,
            desqueeze_display="1.33x",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_face_prio_multi, p289.TOGGLE_OFF)

        blk = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_MULTI,
            configured_face_prio_multi=p289.TOGGLE_ON,
            desqueeze_display="1.33x",
            force_face_prio_during_desqueeze=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p289.EOPNOTSUPP_ERRNO)

    def test_59_force_spot_link_under_wide_af_rejected_eopnotsupp(self) -> None:
        r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            configured_metering_mode=p289.METERING_SPOT_STANDARD,
            focus_area=p289.FOCUS_AREA_WIDE,
            configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
            force_spot_link_under_wide_af=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p289.EOPNOTSUPP_ERRNO)

    def test_60_exposure_std_adjust_one_sixth_ev_range_validated(self) -> None:
        for sixth in (-6, -3, 0, 3, 6):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                exposure_std_adjust_sixth_ev=sixth
            )
            self.assertTrue(r.admitted, msg=str(sixth))
            self.assertEqual(r.exposure_std_adjust_sixth_ev, sixth)

        for bad in (-7, 7, True):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                exposure_std_adjust_sixth_ev=bad
            )
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p289.EINVAL_ERRNO)

    def test_61_ael_with_shutter_all_3_modes_validated(self) -> None:
        for mode in p289.AEL_SHUTTER_MODES:
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                shoot_mode=p289.SHOOT_MODE_STILL,
                ael_with_shutter=mode,
            )
            self.assertTrue(r.admitted, msg=mode)
            self.assertEqual(r.ael_with_shutter, mode)

    def test_62_fx6_metering_workflow_contrast_verified(self) -> None:
        r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
            body_profile=p289.BODY_MODEL_FX6,
        )
        self.assertTrue(r.admitted)
        self.assertIn("Auto Exp", r.effective_metering_mode)
        self.assertIn("Waveform/Zebra", r.fx6_metering_contrast)

    def test_63_non_spot_metering_modes_never_enable_spot_af_coupling(self) -> None:
        for m in (
            p289.METERING_MULTI,
            p289.METERING_CENTER,
            p289.METERING_ENTIRE_SCREEN_AVG,
            p289.METERING_HIGHLIGHT,
        ):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                configured_metering_mode=m,
                focus_area=p289.FOCUS_AREA_FLEXIBLE_SPOT,
                configured_spot_metering_point=p289.SPOT_POINT_FOCUS_LINK,
            )
            self.assertTrue(r.admitted, msg=m)
            self.assertEqual(r.effective_metering_mode, m)
            self.assertFalse(r.spot_coupled_to_af_point)

    def test_64_invalid_metering_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"shoot_mode": "Bulb"},
            {"focus_area": "Matrix99"},
            {"clear_image_zoom_ratio": 0.9},
            {"clear_image_zoom_ratio": 4.5},
            {"clear_image_zoom_ratio": True},
            {"configured_metering_mode": "Spot: Tiny"},
            {"configured_spot_metering_point": "Eye"},
            {"configured_face_prio_multi": "Auto"},
            {"ael_with_shutter": "HalfOnly"},
        ):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p289.EINVAL_ERRNO, msg=str(kwargs))

    def test_65_pillar_cd_zero_physical_writes_and_16_redlines_covered(self) -> None:
        pcd = self.default_audit["pillar_c_d_metering_spot_link_ciz_and_redlines"]
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])
        for entry in pcd["metering_matrix"].values():
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(entry["metering_spot_link_or_ciz_multi_bypass_events"], 0)

    def test_66_spot_metering_still_and_movie_both_supported(self) -> None:
        for sm in (p289.SHOOT_MODE_MOVIE, p289.SHOOT_MODE_STILL):
            r = p289.simulate_metering_spot_link_ciz_and_redlines_hil(
                shoot_mode=sm,
                configured_metering_mode=p289.METERING_HIGHLIGHT,
            )
            self.assertTrue(r.admitted, msg=sm)
            self.assertEqual(r.effective_metering_mode, p289.METERING_HIGHLIGHT)

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 58 (58/58) Suite & Subprocess
    #          Portability Hygiene (10 tests -> Total 76)
    # ------------------------------------------------------------------
    def test_67_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p289.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p289.probe_phase289_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p289.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p289.probe_phase289_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.pp_creative_look_or_reset_wipe_misroute_events, 0)
            self.assertEqual(blocked.wb_cine_ei_auto_or_camset_custom_leak_events, 0)
            self.assertEqual(blocked.metering_spot_link_or_ciz_multi_bypass_events, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p289.probe_phase289_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p289.EINVAL_ERRNO)

    def test_68_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p289.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_pp_scinetone_creativelook_wb_metering_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 289 Stage 58 (58/58)", proc_sum.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc_sum.stdout)

        proc_json = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc_json.stdout)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["milestone"], "58/58")
        self.assertEqual(data["phase_number"], 289)

    def test_69_suite_stage58_58_of_58_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s58 = rep["stage58_realhw_pp_scinetone_creativelook_wb_metering_hil"]
            self.assertTrue(s58["all_checks_passed"])
            self.assertEqual(s58["phase_number"], 289)
            self.assertEqual(s58["milestone"], "58/58")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 58)

    def test_70_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 15.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_71_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_72_suite_stage58_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.stage58_realhw_pp_scinetone_creativelook_wb_metering_hil
        )
        self.assertTrue(default_cfg.include_stage58)
        self.assertTrue(
            default_cfg.include_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil
        )

        for override in (
            {"stage58_realhw_pp_scinetone_creativelook_wb_metering_hil": False},
            {"include_stage58": False},
            {"include_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage58"])
            self.assertFalse(
                rep["config"]["stage58_realhw_pp_scinetone_creativelook_wb_metering_hil"]
            )

    def test_73_fx3_vm_coemulation_suite_include_stage58_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage58", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_pp_scinetone_creativelook_wb_metering_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_74_fx3_vm_coemulation_suite_cli_skip_phase289_and_skip_stage58(self) -> None:
        for skip_flag in ("--skip-phase289", "--skip-stage58", "--no-include-stage58"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil",
                parsed,
            )

    def test_75_test_source_has_no_hardcoded_usr_bin_python3(self) -> None:
        src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, src)

    def test_76_suite_argparse_help_escapes_percent_cleanly_for_py314(self) -> None:
        script = str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py")
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", script, "--help"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--include-stage58", proc.stdout)
        self.assertIn("--skip-stage58", proc.stdout)
        self.assertIn("--skip-phase289", proc.stdout)


if __name__ == "__main__":
    unittest.main()
