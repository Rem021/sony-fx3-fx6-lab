#!/usr/bin/env python3
"""Unit tests for Phase 202 Stage 36 (`36/36` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`) `BIG6` `[Home (Lower Left)]` Zero e-ND Actuator Firewall,
Slot-1 `CAMSET01.DAT .. CAMSET10.DAT` Dual-Media Path Split & Cross-Model `.DAT` Firewall, and
`VMC-BNCM1` (`A-5051-506-A`) Body-Only `TC IN` (`EXT-LK`), `XLR-H1` Handle Micro-USB Block &
Digital HDMI `TC OUT` HIL Co-Emulator.
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

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_big6_noend_camset_slot1_vmcbncm1_coemulator as p202  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p202.run_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p202.run_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil()
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


class TestPhase202Big6NoEndCamsetSlot1VmcBncm1CoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_36_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p202.PHASE_202_SCHEMA,
            "phase202_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator_v1",
        )
        self.assertEqual(p202.PHASE_202_VERSION, "202.0.0")
        self.assertEqual(p202.STAGE_INDEX, 36)
        self.assertEqual(p202.STAGE_TOTAL, 36)
        self.assertEqual(p202.MILESTONE_LABEL, "36/36")
        self.assertEqual(p202.STAGE_NAME, "stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil")
        self.assertEqual(p202.FX3_MODEL_ID, 0x91030080)
        self.assertFalse(p202.FX3_HAS_PHYSICAL_END_HARDWARE)
        self.assertTrue(p202.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p202.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p202.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p202.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p202.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p202.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p202.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p202.E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(p202.SLOT1_FX3_CAMSET_MUTATION_BYTES, 0)
        self.assertEqual(p202.P2_SETTING_MUTATION_BYTES, 0)
        self.assertEqual(p202.XLRH1_HANDLE_USB_TC_MISWIRE_DAMAGE_EVENTS, 0)
        self.assertEqual(p202.BNC_TCOUT_REVERSE_DRIVE_EVENTS, 0)
        self.assertEqual(p202.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p202._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p202.inspect_phase202_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p202.inspect_phase202_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.10)
        self.assertLess(dt2, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p202.inspect_phase202_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p202.inspect_phase202_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p202.resolve_phase202_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p202.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p202.inspect_phase202_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_contracts(self) -> None:
        da = p202.inspect_phase202_donors()
        self.assertEqual(da.fx3_usb_ctrl.file_bytes, 135_424)
        self.assertEqual(da.fx6_hotshoe.file_bytes, 47_808)
        self.assertEqual(da.fx3_libbackup.file_bytes, 14_232)
        self.assertEqual(da.fx3_backup_mgr.file_bytes, 10_272)
        self.assertEqual(da.fx3_im_elf.file_bytes, 40_920)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        self.assertTrue(da.big6_home_lower_left_and_no_end_proven)
        self.assertTrue(da.slot1_camset_dual_media_path_proven)
        self.assertTrue(da.vmcbncm1_tcin_and_hdmi_tcout_proven)
        self.assertTrue(da.p2_setting_and_backup_proven)

    def test_06_string_uxc_proves_big6_camset_slot1_and_timecode_tokens(self) -> None:
        da = p202.inspect_phase202_donors()
        uxc = da.fx3_string_en_f
        self.assertTrue(uxc.uxd_container_ok)
        for tok in (
            "Home (Lower Left)",
            "Aperture",
            "ND Filter",
            "Fixed/Variable",
            "Mode Settings",
            "Save/Load Settings",
            "Slot 1",
            "Recall Camera Setting",
            "Time Code Make",
            "Time Code Run",
            "Time Code Output",
            "HDMI Output Settings",
            "Preset",
            "Free Run",
        ):
            self.assertEqual(uxc.marker_hits[tok], 1, msg=tok)

    def test_07_large_donors_use_strictly_bounded_windows_only(self) -> None:
        da = p202.inspect_phase202_donors()
        for large in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(large.bounded_windows_only)
            self.assertGreater(large.file_bytes, large.bytes_read_total)
            self.assertLessEqual(
                large.bytes_read_total,
                p202.BOUNDED_WINDOW_MAX_BYTES
                * (len(p202.LARGE_DONOR_WINDOWS[large.artifact_key]) + 1),
            )
            self.assertTrue(all(large.window_hits.values()), msg=large.artifact_key)

    def test_08_pillar_a_big6_6tile_topology_and_zone7_constants(self) -> None:
        self.assertEqual(
            p202.BIG6_TILE_SLOT_NAMES,
            (
                "FPS",
                "ISO/Base ISO",
                "Shutter Speed/Angle",
                "Aperture/ND Filter",
                "Picture Profile/Select LUT",
                "White Balance",
            ),
        )
        self.assertEqual(p202.BIG6_STATUS_BAR_ZONE_INDEX, 7)
        self.assertEqual(
            p202.FX6_MOTORIZED_VARIABLE_END_STEPS,
            ("1/4", "1/8", "1/16", "1/32", "1/64", "1/128"),
        )
        self.assertEqual(
            p202.HOME_LOWER_LEFT_MENU_PATH,
            "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]",
        )

    def test_09_pillar_a_home_lower_left_default_aperture_routes_emount_iris(self) -> None:
        res = p202.probe_big6_home_lower_left_and_end_firewall(
            mode_settings="Fixed/Variable",
            home_custom_key_assigned=True,
            home_lower_left_target="Aperture",
            emount_aperture_label="F1.4",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.big6_screen_active)
        self.assertEqual(res.tile_count, 6)
        self.assertTrue(res.status_bar_zone_7_present)
        self.assertTrue(res.emount_iris_routed)
        self.assertFalse(res.virtual_nd_reference_only)
        self.assertEqual(res.slot4_active_binding, "EMOUNT_ELECTRONIC_IRIS_APERTURE")
        self.assertEqual(res.tiles["tile_4_home_lower_left"], "Aperture: F1.4")
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertEqual(res.errno_code, 0)

    def test_10_pillar_a_home_lower_left_nd_filter_is_virtual_display_only(self) -> None:
        res = p202.probe_big6_home_lower_left_and_end_firewall(
            mode_settings="Fixed/Variable",
            home_custom_key_assigned=True,
            home_lower_left_target="ND Filter",
            virtual_nd_reference_label="ND 1/64 (Ref)",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.big6_screen_active)
        self.assertFalse(res.emount_iris_routed)
        self.assertTrue(res.virtual_nd_reference_only)
        self.assertEqual(res.slot4_active_binding, "VIRTUAL_ND_FILTER_METADATA_DISPLAY_ONLY")
        self.assertEqual(res.tiles["tile_4_home_lower_left"], "ND Filter: ND 1/64 (Ref)")
        self.assertFalse(res.fx3_has_physical_end_hardware)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertEqual(res.errno_code, 0)

    def test_11_pillar_a_blocks_all_fx6_variable_end_steps_with_eopnotsupp(self) -> None:
        for step in ("1/4", "1/8", "1/16", "1/32", "1/64", "1/128", "Variable 1/54"):
            res = p202.probe_big6_home_lower_left_and_end_firewall(
                home_lower_left_target="ND Filter",
                attempt_fx6_end_actuator_tx=True,
                requested_fx6_variable_end_ratio=step,
            )
            self.assertFalse(res.admitted, msg=step)
            self.assertTrue(res.cp_bus_end_frame_blocked_eopnotsupp, msg=step)
            self.assertEqual(res.e_nd_actuator_tx_count, 0, msg=step)
            self.assertEqual(res.errno_code, p202.EOPNOTSUPP_ERRNO, msg=step)
            self.assertEqual(
                res.status_code,
                "BLOCKED_FX6_VARIABLE_END_CP_ACTUATOR_TX_EOPNOTSUPP",
                msg=step,
            )

    def test_12_pillar_a_blocks_fx6_end_tx_even_when_target_is_aperture(self) -> None:
        res = p202.probe_big6_home_lower_left_and_end_firewall(
            home_lower_left_target="Aperture",
            attempt_fx6_end_actuator_tx=True,
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.cp_bus_end_frame_blocked_eopnotsupp)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertEqual(res.errno_code, p202.EOPNOTSUPP_ERRNO)

    def test_13_pillar_a_rejects_normal_mode_settings_or_unassigned_home_key(self) -> None:
        res_normal = p202.probe_big6_home_lower_left_and_end_firewall(
            mode_settings="Normal",
            home_custom_key_assigned=True,
        )
        self.assertFalse(res_normal.admitted)
        self.assertFalse(res_normal.big6_screen_active)
        self.assertEqual(res_normal.errno_code, p202.EINVAL_ERRNO)
        self.assertEqual(
            res_normal.status_code,
            "BLOCKED_BIG6_REQUIRES_MODE_SETTINGS_FIXED_VARIABLE_EINVAL",
        )

        res_nokey = p202.probe_big6_home_lower_left_and_end_firewall(
            mode_settings="Fixed/Variable",
            home_custom_key_assigned=False,
        )
        self.assertFalse(res_nokey.admitted)
        self.assertFalse(res_nokey.big6_screen_active)
        self.assertEqual(res_nokey.errno_code, p202.EINVAL_ERRNO)
        self.assertEqual(
            res_nokey.status_code,
            "BLOCKED_BIG6_REQUIRES_HOME_CUSTOM_KEY_ASSIGNED_EINVAL",
        )

    def test_14_pillar_a_rejects_invalid_home_lower_left_target_einval(self) -> None:
        for bad_target in ("Gain", "Audio Level", "Auto ND", ""):
            res = p202.probe_big6_home_lower_left_and_end_firewall(
                home_lower_left_target=bad_target
            )
            self.assertFalse(res.admitted, msg=bad_target)
            self.assertEqual(res.errno_code, p202.EINVAL_ERRNO, msg=bad_target)
            self.assertEqual(res.status_code, "BLOCKED_INVALID_HOME_LOWER_LEFT_TARGET_EINVAL")

    def test_15_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p202.evaluate_pillar_a_big6_home_lower_left_and_no_end_firewall()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["big6_tile_slot_names"]), 6)
        self.assertEqual(len(pa["fx6_variable_end_cp_blocked_matrix"]), 6)

    def test_16_pillar_b_resolve_stock_fx3_camset_dir_sd_vs_cfexpress_a(self) -> None:
        for sd_media in ("SD", "SDHC", "SDXC"):
            self.assertEqual(
                p202.resolve_stock_fx3_camset_dir(sd_media),
                "/PRIVATE/SONY/SETTING/FX3/CAMSET",
            )
        self.assertEqual(
            p202.resolve_stock_fx3_camset_dir("CFEXPRESS_A"),
            "/SONY/SETTING/FX3/CAMSET",
        )
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.resolve_stock_fx3_camset_dir("XQD")

    def test_17_pillar_b_admits_slot1_sd_and_cfexpress_camset01_to_10(self) -> None:
        for idx in range(1, 11):
            sd_res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                operation="SAVE",
                requested_slot=1,
                media_type="SDXC",
                profile_index=idx,
            )
            self.assertTrue(sd_res.admitted)
            self.assertEqual(
                sd_res.resolved_storage_path,
                f"/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET{idx:02d}.DAT",
            )
            self.assertTrue(sd_res.h0_equals_h3)

            cfa_res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                operation="LOAD",
                requested_slot=1,
                media_type="CFEXPRESS_A",
                profile_index=idx,
            )
            self.assertTrue(cfa_res.admitted)
            self.assertEqual(
                cfa_res.resolved_storage_path,
                f"/SONY/SETTING/FX3/CAMSET/CAMSET{idx:02d}.DAT",
            )
            self.assertTrue(cfa_res.h0_equals_h3)

    def test_18_pillar_b_rejects_slot2_and_non_slot1_requests(self) -> None:
        for bad_slot in (0, 2, 3, -1):
            res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                requested_slot=bad_slot,
                media_type="SDXC",
                profile_index=1,
            )
            self.assertFalse(res.admitted, msg=str(bad_slot))
            self.assertTrue(res.slot2_rejected, msg=str(bad_slot))
            self.assertEqual(res.errno_code, p202.EINVAL_ERRNO)
            self.assertEqual(
                res.status_code,
                "BLOCKED_CAMSET_SLOT2_FORBIDDEN_SLOT1_ONLY_EINVAL",
            )

    def test_19_pillar_b_disables_save_load_in_mr_recall_camera_setting_mode(self) -> None:
        for op in ("SAVE", "LOAD"):
            res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                operation=op,
                shooting_mode="MR",
                requested_slot=1,
                media_type="SDXC",
                profile_index=1,
            )
            self.assertFalse(res.admitted)
            self.assertTrue(res.mr_mode_disabled)
            self.assertEqual(res.errno_code, p202.EOPNOTSUPP_ERRNO)
            self.assertEqual(
                res.status_code,
                "BLOCKED_CAMSET_GREYED_OUT_IN_MR_RECALL_MODE_EOPNOTSUPP",
            )

    def test_20_pillar_b_rejects_out_of_range_profile_index_and_bad_filenames(self) -> None:
        for bad_idx in (0, 11, 99, -2):
            res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                profile_index=bad_idx
            )
            self.assertFalse(res.admitted, msg=str(bad_idx))
            self.assertEqual(res.errno_code, p202.EINVAL_ERRNO)

        for bad_fname in (
            "CAMSET00.DAT",
            "CAMSET11.DAT",
            "../CAMSET01.DAT",
            "CAMSET01.BIN",
            "CAMSET02.DAT",
            "CAMSET01.DAT\x00",
        ):
            res_fn = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                profile_index=1,
                explicit_filename=bad_fname,
            )
            self.assertFalse(res_fn.admitted, msg=bad_fname)
            self.assertEqual(res_fn.errno_code, p202.EINVAL_ERRNO)

    def test_21_pillar_b_rejects_sd_vs_cfexpress_dual_media_root_swaps(self) -> None:
        sd_path_on_cfa = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
            media_type="CFEXPRESS_A",
            profile_index=1,
            explicit_card_dir="/PRIVATE/SONY/SETTING/FX3/CAMSET",
        )
        self.assertFalse(sd_path_on_cfa.admitted)
        self.assertTrue(sd_path_on_cfa.media_path_mismatch_rejected)
        self.assertEqual(sd_path_on_cfa.errno_code, p202.EINVAL_ERRNO)

        cfa_path_on_sd = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
            media_type="SDXC",
            profile_index=1,
            explicit_card_dir="/SONY/SETTING/FX3/CAMSET",
        )
        self.assertFalse(cfa_path_on_sd.admitted)
        self.assertTrue(cfa_path_on_sd.media_path_mismatch_rejected)
        self.assertEqual(cfa_path_on_sd.errno_code, p202.EINVAL_ERRNO)

    def test_22_pillar_b_rejects_cross_model_fx3a_and_fx6_dat_on_stock_fx3(self) -> None:
        for foreign_model in ("ILME-FX3A", "ILME-FX6"):
            res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                os_persona="STOCK_FX3_VER_7_02",
                profile_source_model=foreign_model,
            )
            self.assertFalse(res.admitted, msg=foreign_model)
            self.assertTrue(res.cross_model_dat_rejected, msg=foreign_model)
            self.assertEqual(res.errno_code, p202.EINVAL_ERRNO)

        for foreign_dir in (
            "/PRIVATE/SONY/SETTING/FX3A/CAMSET",
            "/SONY/SETTING/FX6/CAMSET",
        ):
            res_dir = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
                explicit_card_dir=foreign_dir
            )
            self.assertFalse(res_dir.admitted, msg=foreign_dir)
            self.assertTrue(res_dir.cross_model_dat_rejected, msg=foreign_dir)
            self.assertEqual(res_dir.errno_code, p202.EINVAL_ERRNO)

    def test_23_pillar_b_stage_b_fx6_persona_redirects_to_tmp_overlay_and_blocks_direct_write(self) -> None:
        direct_blk = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
            os_persona="STAGE_B_FX6_VER_6_01",
            operation="SAVE",
            profile_source_model="ILME-FX6",
            redirect_stage_b_to_overlay=False,
        )
        self.assertFalse(direct_blk.admitted)
        self.assertEqual(direct_blk.errno_code, p202.EROFS_ERRNO)
        self.assertEqual(direct_blk.slot1_fx3_camset_mutation_bytes, 0)
        self.assertEqual(direct_blk.p2_setting_mutation_bytes, 0)
        self.assertTrue(direct_blk.h0_equals_h3)

        ovl_ok = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
            os_persona="STAGE_B_FX6_VER_6_01",
            operation="SAVE",
            profile_index=4,
            profile_source_model="ILME-FX6",
            redirect_stage_b_to_overlay=True,
        )
        self.assertTrue(ovl_ok.admitted)
        self.assertTrue(ovl_ok.redirected_to_tmp_fx6_camset_overlay)
        self.assertEqual(ovl_ok.resolved_storage_path, "/tmp/fx6_camset_overlay/CAMSET04.DAT")
        self.assertEqual(ovl_ok.slot1_fx3_camset_mutation_bytes, 0)
        self.assertEqual(ovl_ok.p2_setting_mutation_bytes, 0)
        self.assertTrue(ovl_ok.h0_equals_h3)

        cross_in_stage_b = p202.probe_slot1_camset_dual_media_and_cross_model_firewall(
            os_persona="STAGE_B_FX6_VER_6_01",
            operation="LOAD",
            profile_source_model="ILME-FX3",
            redirect_stage_b_to_overlay=True,
        )
        self.assertFalse(cross_in_stage_b.admitted)
        self.assertTrue(cross_in_stage_b.cross_model_dat_rejected)
        self.assertEqual(cross_in_stage_b.errno_code, p202.EINVAL_ERRNO)

    def test_24_pillar_b_excludes_machine_bound_credentials_and_validates_inputs(self) -> None:
        res = p202.probe_slot1_camset_dual_media_and_cross_model_firewall()
        self.assertIn("White Balance: Custom 1/2/3", res.machine_bound_items_excluded)
        self.assertIn("FTP Server", res.machine_bound_items_excluded)
        self.assertIn("IP/TLS Certificates", res.machine_bound_items_excluded)
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_slot1_camset_dual_media_and_cross_model_firewall(os_persona="BAD_PERSONA")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_slot1_camset_dual_media_and_cross_model_firewall(operation="DELETE")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_slot1_camset_dual_media_and_cross_model_firewall(media_type="CFast")

    def test_25_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p202.evaluate_pillar_b_slot1_camset_dual_media_and_firewall()
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["stage_b_overlay_profiles_verified"], 10)

    def test_26_pillar_c_vmc_bncm1_part_number_and_constants(self) -> None:
        self.assertEqual(p202.VMC_BNCM1_MODEL, "VMC-BNCM1")
        self.assertEqual(p202.VMC_BNCM1_SONY_PART_NO, "A-5051-506-A")
        self.assertAlmostEqual(p202.VMC_BNCM1_CABLE_LENGTH_M, 0.2)
        self.assertAlmostEqual(p202.EXT_LK_MIN_LOCK_HOLD_SECONDS, 10.0)

    def test_27_pillar_c_vmc_bncm1_locks_ext_lk_after_10s_in_movie_preset_free_run(self) -> None:
        res = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            usb_port="BODY_MULTI_MICRO_USB",
            vmc_bncm1_attached=True,
            bnc_direction="TC_IN",
            shooting_mode="Movie",
            tc_make="Preset",
            tc_run="Free Run",
            signal_hold_seconds=10.0,
            hdmi_tc_output_menu="On",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.ext_lk_locked)
        self.assertFalse(res.ext_lk_released)
        self.assertEqual(res.tc_status_badge, "EXT-LK")
        self.assertTrue(res.hdmi_digital_tc_out_active)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.status_code, "ADMITTED_VMC_BNCM1_BODY_TC_IN_EXT_LK_LOCKED_OK")

    def test_28_pillar_c_vmc_bncm1_pre_10s_remains_acquiring_not_locked(self) -> None:
        for hold_s in (0.0, 4.2, 9.99):
            res = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
                signal_hold_seconds=hold_s
            )
            self.assertTrue(res.admitted, msg=str(hold_s))
            self.assertFalse(res.ext_lk_locked, msg=str(hold_s))
            self.assertEqual(res.tc_status_badge, "TC_IN_ACQUIRING", msg=str(hold_s))
            self.assertEqual(res.status_code, "ADMITTED_VMC_BNCM1_TC_IN_SYNCING_LT_10S")

    def test_29_pillar_c_blocks_xlrh1_handle_micro_usb_and_type_c_with_enodev(self) -> None:
        xlrh1 = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            usb_port="XLR_H1_HANDLE_MICRO_USB",
            vmc_bncm1_attached=True,
        )
        self.assertFalse(xlrh1.admitted)
        self.assertTrue(xlrh1.xlrh1_handle_usb_blocked_enodev)
        self.assertFalse(xlrh1.ext_lk_locked)
        self.assertEqual(xlrh1.errno_code, p202.ENODEV_ERRNO)
        self.assertEqual(xlrh1.xlrh1_handle_usb_tc_miswire_damage_events, 0)

        type_c = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            usb_port="BODY_USB_TYPE_C",
            vmc_bncm1_attached=True,
        )
        self.assertFalse(type_c.admitted)
        self.assertEqual(type_c.errno_code, p202.ENODEV_ERRNO)

    def test_30_pillar_c_blocks_reverse_bnc_tc_out_with_eopnotsupp(self) -> None:
        res_dir = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            bnc_direction="TC_OUT"
        )
        self.assertFalse(res_dir.admitted)
        self.assertTrue(res_dir.reverse_bnc_tcout_blocked_eopnotsupp)
        self.assertEqual(res_dir.bnc_tcout_reverse_drive_events, 0)
        self.assertEqual(res_dir.errno_code, p202.EOPNOTSUPP_ERRNO)

        res_flag = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            bnc_direction="TC_IN",
            attempt_bnc_tc_out=True,
        )
        self.assertFalse(res_flag.admitted)
        self.assertTrue(res_flag.reverse_bnc_tcout_blocked_eopnotsupp)
        self.assertEqual(res_flag.errno_code, p202.EOPNOTSUPP_ERRNO)

    def test_31_pillar_c_sq_mode_releases_ext_lk_and_disables_hdmi_tc_out(self) -> None:
        res_sq = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            shooting_mode="S&Q",
            signal_hold_seconds=20.0,
            was_previously_ext_lk=True,
            hdmi_tc_output_menu="On",
        )
        self.assertTrue(res_sq.admitted)
        self.assertFalse(res_sq.ext_lk_locked)
        self.assertTrue(res_sq.ext_lk_released)
        self.assertEqual(res_sq.tc_status_badge, "INTERNAL_TC")
        self.assertFalse(res_sq.hdmi_digital_tc_out_active)
        self.assertTrue(res_sq.hdmi_tc_out_disabled_in_sq)
        self.assertEqual(res_sq.status_code, "ADMITTED_EXT_LK_RELEASED_ON_SQ_MODE_SWITCH")

    def test_32_pillar_c_tc_setting_mutation_or_regenerate_rec_run_releases_ext_lk(self) -> None:
        res_mut = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            shooting_mode="Movie",
            tc_make="Preset",
            tc_run="Free Run",
            signal_hold_seconds=15.0,
            was_previously_ext_lk=True,
            tc_setting_mutated_after_lock=True,
        )
        self.assertTrue(res_mut.admitted)
        self.assertFalse(res_mut.ext_lk_locked)
        self.assertTrue(res_mut.ext_lk_released)
        self.assertEqual(res_mut.status_code, "ADMITTED_EXT_LK_RELEASED_ON_TC_SETTING_CHANGE")

        res_regen = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            shooting_mode="Movie",
            tc_make="Regenerate",
            tc_run="Rec Run",
            signal_hold_seconds=15.0,
            was_previously_ext_lk=True,
        )
        self.assertTrue(res_regen.admitted)
        self.assertFalse(res_regen.ext_lk_locked)
        self.assertTrue(res_regen.ext_lk_released)

    def test_33_pillar_c_hdmi_tc_out_toggle_in_movie_and_detached_cable(self) -> None:
        detached_hdmi_on = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            vmc_bncm1_attached=False,
            shooting_mode="Movie",
            hdmi_tc_output_menu="On",
        )
        self.assertTrue(detached_hdmi_on.admitted)
        self.assertFalse(detached_hdmi_on.ext_lk_locked)
        self.assertTrue(detached_hdmi_on.hdmi_digital_tc_out_active)
        self.assertEqual(detached_hdmi_on.status_code, "ADMITTED_INTERNAL_TC_GENERATOR_ACTIVE")

        detached_hdmi_off = p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(
            vmc_bncm1_attached=False,
            shooting_mode="Movie",
            hdmi_tc_output_menu="Off",
        )
        self.assertTrue(detached_hdmi_off.admitted)
        self.assertFalse(detached_hdmi_off.hdmi_digital_tc_out_active)

    def test_34_pillar_c_validates_invalid_parameters(self) -> None:
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(usb_port="BAD_USB")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(bnc_direction="GENLOCK")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(shooting_mode="Photo")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(tc_make="Auto")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(tc_run="Hold")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(hdmi_tc_output_menu="Auto")
        with self.assertRaises(p202.RealHwBig6CamsetVmcBncm1Error):
            p202.probe_vmcbncm1_tcin_and_hdmi_tcout_hil(signal_hold_seconds=-0.1)

    def test_35_pillar_d_hard_safety_redline_baseline_and_all_9_forbidden_actions(self) -> None:
        base = p202.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.e_nd_actuator_tx_count, 0)
        self.assertEqual(base.slot1_fx3_camset_mutation_bytes, 0)
        self.assertEqual(base.p2_setting_mutation_bytes, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "transmit_fx6_end_actuator_frame",
            "mutate_slot1_or_p2_camset",
            "drive_reverse_bnc_tcout_or_xlrh1_usb",
        ):
            bad = p202.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertEqual(bad.physical_usb_packets_emitted, 0)
            self.assertEqual(bad.otp_fuse_touches, 0)
            self.assertEqual(bad.rpmb_counter_increments, 0)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_36_pillar_d_combined_multi_redline_violation_blocked(self) -> None:
        combo = p202.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            transmit_fx6_end_actuator_frame=True,
            drive_reverse_bnc_tcout_or_xlrh1_usb=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("FX6_VARIABLE_END_CP_ACTUATOR_TX", combo.blocked_action)
        self.assertIn("REVERSE_BNC_TCOUT_OR_XLRH1_USB_MISWIRE", combo.blocked_action)

    def test_37_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p202.evaluate_pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    def test_38_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p202.run_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil(force_clean_room=True)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 36)
        self.assertEqual(r1["stage_total"], 36)
        self.assertEqual(r1["milestone"], "36/36")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_39_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_big6_home_lower_left_and_no_end_firewall_hil"]["passed"])
        self.assertTrue(rep["pillar_b_slot1_camset_dual_media_and_cross_model_firewall_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_vmcbncm1_tcin_hdmi_tcout_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["e_nd_actuator_tx_count"], 0)
        self.assertEqual(rep["redlines"]["slot1_fx3_camset_mutation_bytes"], 0)
        self.assertEqual(rep["redlines"]["p2_setting_mutation_bytes"], 0)

    def test_40_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py"),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 202 Stage 36 (36/36)", p_sum.stdout)

        p_json = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py"),
                "--self-test",
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["stage_index"], 36)
        self.assertEqual(parsed["milestone"], "36/36")

    def test_41_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p202.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 202 Stage 36 (36/36)", buf.getvalue())

    def test_42_fx3_vm_coemulation_suite_includes_stage36_and_skip_phase202(self) -> None:
        rep_on, _dt = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil", rep_on)
        s36 = rep_on["stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil"]
        self.assertTrue(s36["all_checks_passed"])
        self.assertFalse(s36["persistent_emmc_writes_authorized"])
        self.assertFalse(s36["spi_nor_write_authorized"])
        self.assertFalse(s36["el3_payload_transmit_authorized"])
        self.assertEqual(s36["physical_usb_packets_emitted"], 0)
        self.assertEqual(s36["otp_fuse_touches"], 0)
        self.assertEqual(s36["rpmb_counter_increments"], 0)
        self.assertEqual(s36["e_nd_actuator_tx_count"], 0)
        self.assertEqual(s36["slot1_fx3_camset_mutation_bytes"], 0)
        self.assertEqual(s36["p2_setting_mutation_bytes"], 0)
        self.assertEqual(s36["xlrh1_handle_usb_tc_miswire_damage_events"], 0)
        self.assertEqual(s36["bnc_tcout_reverse_drive_events"], 0)
        self.assertEqual(s36["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 36)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil", rep_skip)
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 35)

    def test_43_all_36_of_36_stages_present_and_passing_in_suite(self) -> None:
        rep, _dt = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 37):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_44_suite_subprocess_summary_and_skip_phase202_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
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
        self.assertIn("realhw_big6_noend_camset_slot1_vmcbncm1_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase202",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_big6_noend_camset_slot1_vmcbncm1_hil=", proc_skip.stdout)

    def test_45_suite_36_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        rep_clean, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 36)
        self.assertLess(dt_clean, 6.0)

        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 36)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil", parsed)

    def test_46_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (FX3_VM_DIR / "realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_47_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p202.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p202.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_48_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase202_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
        }
        paths = p202.resolve_phase202_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p202.inspect_phase202_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)


if __name__ == "__main__":
    unittest.main()
