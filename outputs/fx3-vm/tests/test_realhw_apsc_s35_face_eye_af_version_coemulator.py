#!/usr/bin/env python3
"""Unit tests for Phase 267 Stage 52 (`52/52`):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) Wave-42
`[APS-C S35 Shooting]` `12.1 MP` `4K` / `HDMI RAW` Hard-Lockout & `Clear Image Zoom`
Distinction, BIONZ XR `[Face/Eye AF]` (4 Items, AI-Coprocessor Subject Spoof
Rejection, Clean-HDMI Frame Isolation & `[Face Memory]` Reset Survival), and
`[Version]` Read-Only Inspection, `Airplane Mode = On` Zero-RF Badge Suppression
& `BODYDATA.DAT` Hard-Blocked Flash Guard HIL Co-Emulator (70 dual-mode tests).
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
import realhw_apsc_s35_face_eye_af_version_coemulator as p267  # noqa: E402


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
        include_stage51=False,
    )
    base.update(overrides)
    return base


class TestPhase267ApscS35FaceEyeAfVersionCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p267.run_phase267_realhw_apsc_s35_face_eye_af_version_hil(
            force_clean_room=True
        )
        cls.default_audit = p267.run_phase267_realhw_apsc_s35_face_eye_af_version_hil()

        forced = p267.is_forced_clean_room()
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True if forced else None)
        )
        cls.default_suite_elapsed = time.monotonic() - t0

        if forced:
            cls.clean_suite = cls.default_suite
            cls.clean_suite_elapsed = cls.default_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
            )
            cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Phase 267 Stage 52 (52/52) & O_RDONLY 18-Donor SHA-256 (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase267_stage52_and_redline_constants(self) -> None:
        self.assertEqual(
            p267.SCHEMA_ID,
            "realhw_apsc_s35_face_eye_af_version_coemulator_v1",
        )
        self.assertEqual(p267.PHASE_267_SCHEMA, p267.SCHEMA_ID)
        self.assertEqual(p267.PHASE_267_VERSION, "267.0.0")
        self.assertEqual(p267.PHASE_NUMBER, 267)
        self.assertEqual(p267.STAGE_INDEX, 52)
        self.assertEqual(p267.STAGE_TOTAL, 52)
        self.assertEqual(p267.MILESTONE_LABEL, "52/52")
        self.assertEqual(
            p267.STAGE_NAME,
            "stage52_realhw_apsc_s35_face_eye_af_version_hil",
        )
        self.assertEqual(p267.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p267.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p267.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p267.BODYDATA_UPDATE_EXECUTION_BLOCKED)
        self.assertTrue(p267.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p267.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p267.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p267.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_sha256_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p267.SOURCE_MODE_CLEAN_ROOM)
        again = p267.run_phase267_realhw_apsc_s35_face_eye_af_version_hil(force_clean_room=True)
        self.assertEqual(self.clean_audit["audit_digest_sha256"], again["audit_digest_sha256"])
        self.assertEqual(len(self.clean_audit["audit_digest_sha256"]), 64)

    def test_03_default_audit_18_donors_o_rdonly_fast_and_zero_leakage(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["donor_files_inspected"], 18)
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertLess(da["inspection_elapsed_s"], 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.1)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_04_all_18_donor_expected_byte_sizes_verified(self) -> None:
        self.assertEqual(len(p267.EXPECTED_DONOR_BYTES), 18)
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key, expected_size in p267.EXPECTED_DONOR_BYTES.items():
                self.assertEqual(audit[key]["file_bytes"], expected_size)

    def test_05_pinned_sha256_hashes_verified_on_compact_and_large_donors(self) -> None:
        self.assertEqual(len(p267.EXPECTED_COMPACT_DONOR_SHA256), 10)
        self.assertEqual(len(p267.EXPECTED_LARGE_HEAD4K_SHA256), 8)
        da = self.default_audit["donor_audit"]
        for key, expected_sha in p267.EXPECTED_COMPACT_DONOR_SHA256.items():
            self.assertEqual(len(expected_sha), 64)
            self.assertTrue(da[key]["sha256_verified"])
            if da["source_mode"] == p267.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(da[key]["sha256"], expected_sha)
        for key, expected_hsha in p267.EXPECTED_LARGE_HEAD4K_SHA256.items():
            self.assertEqual(len(expected_hsha), 64)
            self.assertTrue(da[key]["head_sha256_verified"])
            if da["source_mode"] == p267.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(da[key]["head_sha256"], expected_hsha)

    def test_06_fx3_version_and_updater_ufp_bodydata_donor_symbols_verified(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            gv = audit["fx3_get_version"]
            self.assertTrue(gv["elf64_le_ok"])
            self.assertEqual(gv["marker_hits"]["InfraGetVersion"], 1)
            self.assertEqual(gv["marker_hits"]["InfraGetVersionLens"], 1)
            up = audit["fx3_updater_ufp"]
            self.assertTrue(up["elf64_le_ok"])
            self.assertEqual(up["marker_hits"]["/BODYDATA.DAT"], 1)
            self.assertEqual(up["marker_hits"]["LENSDATA.DAT"], 1)
            self.assertEqual(up["marker_hits"]["/dev/nflasha1"], 1)

    def test_07_fx3_and_fx6_uxc_wave42_ui_markers_and_absent_markers(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            fx3_s = audit["fx3_string_en_f"]
            self.assertTrue(fx3_s["uxd_container_ok"])
            for tok in (
                "APS-C/Super 35mm",
                "Clear Image Zoom",
                "XAVC HS 4K",
                "XAVC S 4K",
                "XAVC S-I 4K",
                "XAVC S HD",
                "XAVC S-I HD",
                "RAW Output",
                "Face/Eye AF",
                "Face/Eye Priority in AF",
                "Face/Eye Subject",
                "Right/Left Eye Select",
                "Face/Eye Frame Display",
                "Regist. Faces Priority",
                "Face Memory",
                "HDMI Info. Display",
                "Version",
                "Airplane Mode",
            ):
                self.assertEqual(fx3_s["marker_hits"][tok], 1)
            for absent in ("Autoframing Settings", "Version Update", "ECS"):
                self.assertEqual(fx3_s["absent_marker_hits"][absent], 0)

    def test_08_large_donors_strictly_bounded_4096_byte_windows(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key in p267.LARGE_DONOR_WINDOWS:
                ls = audit[key]
                self.assertTrue(ls["bounded_windows_only"])
                self.assertLessEqual(ls["bytes_read_total"], 12 * p267.BOUNDED_WINDOW_MAX_BYTES)
                for val in ls["window_hits"].values():
                    self.assertEqual(val, 1)

    def test_09_fx3_clean_room_test_and_force_clean_room_env_parity(self) -> None:
        self.assertTrue(p267.is_forced_clean_room({"FX3_CLEAN_ROOM_TEST": "1"}))
        self.assertTrue(p267.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p267.is_forced_clean_room({}))
        rep_crt = p267.run_phase267_realhw_apsc_s35_face_eye_af_version_hil(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        rep_fcr = p267.run_phase267_realhw_apsc_s35_face_eye_af_version_hil(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(rep_crt["source_mode"], p267.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep_crt["audit_digest_sha256"], rep_fcr["audit_digest_sha256"])

    def test_10_clean_room_donor_path_resolution_uses_nonexistent_sentinel(self) -> None:
        paths = p267.resolve_phase267_donor_paths(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(len(paths), 18)
        for p in paths.values():
            self.assertIn(p267.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_11_missing_donor_directory_falls_back_to_clean_room_synthetic(self) -> None:
        with unittest.mock.patch.object(
            p267, "_iter_work_roots", return_value=(Path("/nonexistent_wave42_stage52_root"),)
        ):
            da = p267.inspect_phase267_donors(force_clean_room=False, env={})
        self.assertEqual(da.source_mode, p267.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(da.all_contracts_verified)

    def test_12_donor_audit_proves_all_three_wave42_domains(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            self.assertTrue(audit["apsc_s35_4k_lockout_proven"])
            self.assertTrue(audit["face_eye_af_clean_hdmi_proven"])
            self.assertTrue(audit["version_readonly_and_bodydata_guard_proven"])
            self.assertTrue(audit["all_contracts_verified"])
            self.assertEqual(tuple(audit["errors"]), ())

    def test_13_no_raw_firmware_bytes_in_serialized_json_payload(self) -> None:
        blob = json.dumps(self.default_audit)
        self.assertNotIn("\\u007fELF", blob)
        self.assertEqual(self.default_audit["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_14_work_root_deduplication_with_custom_env_overrides(self) -> None:
        roots = p267._iter_work_roots(
            env={
                "FX3_FX6_MAC_WORK_ROOT": "/tmp/fx3_w42_a",
                "FX3_FX6_MAIN_LAB_WORK_ROOT": "/tmp/fx3_w42_a",
                "FX3_FX6_MAC_ROOT": "/tmp/fx3_w42_mac",
            }
        )
        self.assertEqual(len(roots), len(set(str(r) for r in roots)))
        self.assertEqual(str(roots[0]), "/tmp/fx3_w42_a")

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 52A — [APS-C S35 Shooting] 12.1MP 4K/RAW Lockout (18 tests: 15..32)
    # ------------------------------------------------------------------
    def test_15_apsc_s35_menu_paths_and_sensor_pixel_constants(self) -> None:
        self.assertEqual(
            p267.APSC_S35_MENU_PATH,
            "MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]",
        )
        self.assertEqual(
            p267.APSC_S35_CANONICAL_UI_PATH,
            "MENU > Shooting > Image Quality > APS-C S35 Shooting",
        )
        self.assertEqual(p267.FX3_FF_SENSOR_STILL_PIXELS, (4240, 2832))
        self.assertEqual(p267.FX3_APSC_16_9_SUBWINDOW_PIXELS[0], 2560)
        self.assertLess(p267.FX3_APSC_16_9_SUBWINDOW_PIXELS[0], 3840)

    def test_16_apsc_s35_hard_locked_off_in_xavc_hs_4k(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC HS 4K",
            attached_lens_id="SELP18105G_APSC",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.apsc_s35_menu_available)
        self.assertTrue(res.apsc_s35_hard_locked_off)
        self.assertEqual(res.effective_apsc_s35_mode, "Off")
        self.assertFalse(res.apsc_s35_crop_active)
        self.assertEqual(res.effective_sensor_fov_crop, 1.0)

    def test_17_apsc_s35_hard_locked_off_in_xavc_s_4k_and_xavc_si_4k(self) -> None:
        for fmt in ("XAVC S 4K", "XAVC S-I 4K"):
            res = p267.simulate_apsc_s35_shooting_hil(
                configured_apsc_s35_mode="Auto",
                capture_format=fmt,
                attached_lens_id="SEL1655G_APSC",
            )
            self.assertTrue(res.apsc_s35_hard_locked_off)
            self.assertFalse(res.apsc_s35_menu_available)
            self.assertEqual(res.effective_apsc_s35_mode, "Off")
            self.assertFalse(res.apsc_s35_crop_active)

    def test_18_apsc_s35_hard_locked_off_in_dci_4k_4096x2160(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="DCI 4K",
            attached_lens_id="SEL2470GM2",
        )
        self.assertTrue(res.apsc_s35_hard_locked_off)
        self.assertEqual(res.output_frame_pixels, (4096, 2160))
        self.assertFalse(res.apsc_s35_crop_active)

    def test_19_apsc_s35_hard_locked_off_in_hdmi_raw_4264x2408(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="HDMI RAW Output",
            attached_lens_id="SELP18105G_APSC",
        )
        self.assertTrue(res.apsc_s35_hard_locked_off)
        self.assertFalse(res.apsc_s35_menu_available)
        self.assertEqual(res.output_frame_pixels, (4264, 2408))
        self.assertIn("HDMI_RAW_4264X2408_REQUIRES_FULL_FRAME_READOUT", res.active_lockout_reasons)

    def test_20_strict_menu_selection_of_apsc_s35_in_4k_or_raw_rejected_eacces(self) -> None:
        for fmt in p267.HARD_LOCKED_4K_OR_RAW_FORMATS:
            res = p267.simulate_apsc_s35_shooting_hil(
                configured_apsc_s35_mode="On",
                capture_format=fmt,
                strict_menu_select_apsc_on_or_auto=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p267.EACCES_ERRNO)
            self.assertEqual(res.apsc_s35_4k_or_raw_bypass_events, 0)

    def test_21_forced_bypass_of_apsc_4k_or_raw_lockout_blocked_eacces(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S 4K",
            force_bypass_apsc_4k_or_raw_lockout=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EACCES_ERRNO)
        self.assertEqual(res.apsc_s35_4k_or_raw_bypass_events, 0)

    def test_22_hd_xavc_s_hd_auto_mode_switches_by_full_frame_vs_apsc_lens(self) -> None:
        ff = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Auto",
            capture_format="XAVC S HD",
            attached_lens_id="SEL2470GM2",
        )
        self.assertTrue(ff.apsc_s35_menu_available)
        self.assertFalse(ff.apsc_s35_crop_active)
        self.assertEqual(ff.effective_sensor_fov_crop, 1.0)

        apsc = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Auto",
            capture_format="XAVC S HD",
            attached_lens_id="SELP18105G_APSC",
        )
        self.assertTrue(apsc.apsc_s35_menu_available)
        self.assertTrue(apsc.apsc_s35_crop_active)
        self.assertEqual(apsc.effective_sensor_fov_crop, 1.5)
        self.assertEqual(apsc.output_frame_pixels, (1920, 1080))

    def test_23_hd_xavc_si_hd_manual_on_and_off_override_lens_type(self) -> None:
        on_ff = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S-I HD",
            attached_lens_id="SEL50F12GM",
        )
        self.assertTrue(on_ff.apsc_s35_crop_active)
        self.assertEqual(on_ff.effective_sensor_fov_crop, 1.5)

        off_apsc = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Off",
            capture_format="XAVC S-I HD",
            attached_lens_id="SEL1655G_APSC",
        )
        self.assertFalse(off_apsc.apsc_s35_crop_active)
        self.assertEqual(off_apsc.effective_sensor_fov_crop, 1.0)

    def test_24_still_image_apsc_s35_crop_5_1mp_vs_full_frame_12_1mp(self) -> None:
        crop = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="Still Image",
            attached_lens_id="SEL2470GM2",
        )
        self.assertTrue(crop.apsc_s35_crop_active)
        self.assertEqual(crop.output_frame_pixels, (2768, 1848))
        self.assertEqual(crop.still_megapixels_approx, 5.1)

        ff = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Off",
            capture_format="Still Image",
            attached_lens_id="SEL2470GM2",
        )
        self.assertFalse(ff.apsc_s35_crop_active)
        self.assertEqual(ff.output_frame_pixels, (4240, 2832))
        self.assertEqual(ff.still_megapixels_approx, 12.1)

    def test_25_clear_image_zoom_1_5x_in_4k_distinct_from_locked_apsc_s35(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Auto",
            capture_format="XAVC S 4K",
            attached_lens_id="SEL2470GM2",
            clear_image_zoom_factor=1.5,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.apsc_s35_hard_locked_off)
        self.assertFalse(res.apsc_s35_crop_active)
        self.assertTrue(res.clear_image_zoom_active)
        self.assertTrue(res.clear_image_zoom_distinct_from_apsc_s35)
        self.assertEqual(res.effective_sensor_fov_crop, 1.0)
        self.assertEqual(res.effective_total_fov_multiplier, 1.5)

    def test_26_clear_image_zoom_range_limits_4k_1_5x_hd_2_0x_and_raw_1_0x(self) -> None:
        over_4k = p267.simulate_apsc_s35_shooting_hil(
            capture_format="XAVC S 4K",
            clear_image_zoom_factor=2.0,
        )
        self.assertFalse(over_4k.admitted)
        self.assertEqual(over_4k.errno_code, p267.EINVAL_ERRNO)

        ok_hd_2x = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S HD",
            clear_image_zoom_factor=2.0,
        )
        self.assertTrue(ok_hd_2x.admitted)
        self.assertEqual(ok_hd_2x.effective_total_fov_multiplier, 3.0)

        over_raw = p267.simulate_apsc_s35_shooting_hil(
            capture_format="HDMI RAW Output",
            clear_image_zoom_factor=1.2,
        )
        self.assertFalse(over_raw.admitted)
        self.assertEqual(over_raw.errno_code, p267.EINVAL_ERRNO)

    def test_27_apsc_s35_reset_scope_camera_settings_reset_vs_network_reset_vs_initialize(self) -> None:
        csr = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Off",
            capture_format="XAVC S HD",
            attached_lens_id="SELP18105G_APSC",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(csr.restored_by_camera_settings_reset)
        self.assertEqual(csr.persisted_apsc_s35_register, "Auto")
        self.assertTrue(csr.apsc_s35_crop_active)

        net = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S HD",
            attached_lens_id="SEL2470GM2",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(net.survived_reset_network_set)
        self.assertEqual(net.persisted_apsc_s35_register, "On")
        self.assertTrue(net.apsc_s35_crop_active)

        init = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S HD",
            attached_lens_id="SEL2470GM2",
            reset_action="Initialize",
        )
        self.assertTrue(init.restored_by_initialize)
        self.assertEqual(init.persisted_apsc_s35_register, "Auto")
        self.assertFalse(init.apsc_s35_crop_active)

    def test_28_manual_pl_adapter_lens_auto_stays_full_frame_in_hd_manual_on_crops(self) -> None:
        auto_pl = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="Auto",
            capture_format="XAVC S HD",
            attached_lens_id="MANUAL_PL_ADAPTER",
        )
        self.assertFalse(auto_pl.apsc_s35_crop_active)

        on_pl = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S HD",
            attached_lens_id="MANUAL_PL_ADAPTER",
        )
        self.assertTrue(on_pl.apsc_s35_crop_active)

    def test_29_exhaustive_144_state_apsc_lockout_matrix_zero_bypasses(self) -> None:
        mat = p267.compute_apsc_s35_lockout_matrix()
        self.assertEqual(mat["total_states_evaluated"], 144)
        self.assertEqual(mat["locked_4k_and_raw_states"], 90)
        self.assertEqual(mat["bypass_states"], 0)
        self.assertTrue(mat["zero_4k_raw_bypass_proven"])

    def test_30_invalid_apsc_s35_parameters_rejected_einval(self) -> None:
        for kw in (
            {"configured_apsc_s35_mode": "2xCrop"},
            {"capture_format": "8K RAW"},
            {"attached_lens_id": "FAKE_LENS"},
            {"clear_image_zoom_factor": 0.8},
        ):
            bad = p267.simulate_apsc_s35_shooting_hil(**kw)
            self.assertFalse(bad.admitted)
            self.assertEqual(bad.errno_code, p267.EINVAL_ERRNO)

    def test_31_apsc_s35_persisted_register_survives_4k_lockout_clamp(self) -> None:
        res = p267.simulate_apsc_s35_shooting_hil(
            configured_apsc_s35_mode="On",
            capture_format="XAVC S 4K",
        )
        self.assertEqual(res.persisted_apsc_s35_register, "On")
        self.assertEqual(res.effective_apsc_s35_mode, "Off")
        self.assertEqual(res.reason_code, "APSC_S35_CLAMPED_OFF_IN_4K_OR_RAW")

    def test_32_pillar_a_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pa = rep["pillar_a_apsc_s35_4k_raw_lockout_hil"]
            self.assertTrue(pa["passed"])
            self.assertEqual(len(pa["hard_locked_4k_and_raw_formats"]), 5)
            self.assertEqual(pa["exhaustive_144_state_matrix"]["bypass_states"], 0)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 52B — BIONZ XR [Face/Eye AF], AI Spoof Rejection,
    #          Clean-HDMI Isolation & [Face Memory] Survival (16 tests: 33..48)
    # ------------------------------------------------------------------
    def test_33_face_eye_af_menu_paths_and_exact_4_bionz_xr_items(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.menu_path, "MENU -> Focus -> [Face/Eye AF]")
        self.assertEqual(res.canonical_ui_path, "MENU > Focus > Face/Eye AF")
        self.assertEqual(
            res.menu_items,
            (
                "Face/Eye Priority in AF",
                "Subject Recognition in AF",
                "Right/Left Eye Select",
                "Face/Eye Frame Display",
            ),
        )

    def test_34_bionz_xr_human_and_animal_subjects_admitted(self) -> None:
        h = p267.simulate_face_eye_af_clean_hdmi_hil(configured_subject_recognition_in_af="Human")
        self.assertTrue(h.admitted)
        self.assertTrue(h.right_left_eye_select_applicable)

        a = p267.simulate_face_eye_af_clean_hdmi_hil(configured_subject_recognition_in_af="Animal")
        self.assertTrue(a.admitted)
        self.assertFalse(a.right_left_eye_select_applicable)

    def test_35_spoofed_ai_coprocessor_subjects_bird_insect_cartrain_airplane_rejected(self) -> None:
        for spoof in ("Bird", "Insect", "Car/Train", "Airplane"):
            res = p267.simulate_face_eye_af_clean_hdmi_hil(
                configured_subject_recognition_in_af=spoof
            )
            self.assertFalse(res.admitted, msg=f"Spoofed AI subject {spoof} must be rejected")
            self.assertEqual(res.errno_code, p267.EOPNOTSUPP_ERRNO)
            self.assertIn("DEDICATED_AI_COPROCESSOR_SUBJECT_SPOOF_REJECTED", res.reason_code)
            self.assertEqual(res.ai_coprocessor_subject_spoof_events, 0)

    def test_36_right_left_eye_select_auto_right_left_and_custom_key_toggle(self) -> None:
        for opt in ("Auto", "Right Eye", "Left Eye"):
            r = p267.simulate_face_eye_af_clean_hdmi_hil(configured_right_left_eye_select=opt)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_right_left_eye_select, opt)

        t1 = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_right_left_eye_select="Auto",
            custom_key_switch_right_left_eye_pressed=True,
        )
        self.assertEqual(t1.effective_right_left_eye_select, "Right Eye")

        t2 = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_right_left_eye_select="Right Eye",
            custom_key_switch_right_left_eye_pressed=True,
        )
        self.assertEqual(t2.effective_right_left_eye_select, "Left Eye")

    def test_37_intelligent_auto_locks_face_eye_priority_on(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_priority_in_af="Off",
            intelligent_auto_mode=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_face_eye_priority_in_af, "On")

    def test_38_clean_hdmi_info_display_off_renders_box_on_lcd_only_never_hdmi(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_frame_display="On",
            subject_detected_in_scene=True,
            hdmi_connected=True,
            hdmi_info_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.lcd_tracking_box_rendered)
        self.assertFalse(res.hdmi_tracking_box_rendered)
        self.assertTrue(res.hdmi_clean_feed_isolated)
        self.assertEqual(res.hdmi_clean_feed_eye_frame_baked_pixels, 0)

    def test_39_hdmi_raw_output_on_enforces_clean_hdmi_isolation_even_if_info_on(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_frame_display="On",
            subject_detected_in_scene=True,
            hdmi_connected=True,
            hdmi_info_display="On",
            hdmi_raw_output_on=True,
        )
        self.assertTrue(res.lcd_tracking_box_rendered)
        self.assertFalse(res.hdmi_tracking_box_rendered)
        self.assertTrue(res.hdmi_clean_feed_isolated)
        self.assertEqual(res.hdmi_clean_feed_eye_frame_baked_pixels, 0)

    def test_40_hdmi_info_display_on_routes_osd_to_hdmi_and_blanks_lcd_osd(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_frame_display="On",
            subject_detected_in_scene=True,
            hdmi_connected=True,
            hdmi_info_display="On",
            hdmi_raw_output_on=False,
        )
        self.assertFalse(res.lcd_tracking_box_rendered)
        self.assertTrue(res.hdmi_tracking_box_rendered)
        self.assertFalse(res.hdmi_clean_feed_isolated)

    def test_41_af_area_auto_clear_hides_tracking_frame_after_focus_lock(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_frame_display="On",
            af_area_auto_clear="On",
            focus_locked=True,
            subject_detected_in_scene=True,
            hdmi_info_display="Off",
        )
        self.assertFalse(res.lcd_tracking_box_rendered)
        self.assertFalse(res.hdmi_tracking_box_rendered)

    def test_42_face_memory_survives_camera_settings_reset_while_4_items_reset(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_face_eye_priority_in_af="Off",
            configured_subject_recognition_in_af="Animal",
            configured_right_left_eye_select="Left Eye",
            configured_face_eye_frame_display="On",
            configured_registered_faces_priority="Off",
            registered_face_ids=("TALENT_A", "TALENT_B", "TALENT_C"),
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.settings_restored_by_camera_settings_reset)
        self.assertTrue(res.face_memory_survived_camera_settings_reset)
        self.assertEqual(res.effective_face_eye_priority_in_af, "On")
        self.assertEqual(res.effective_subject_recognition_in_af, "Human")
        self.assertEqual(res.effective_right_left_eye_select, "Auto")
        self.assertEqual(res.effective_face_eye_frame_display, "Off")
        self.assertEqual(res.effective_registered_faces_priority, "On")
        self.assertEqual(res.effective_registered_face_ids, ("TALENT_A", "TALENT_B", "TALENT_C"))
        self.assertEqual(res.effective_face_memory_count, 3)

    def test_43_face_memory_and_settings_survive_reset_network_set(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_subject_recognition_in_af="Animal",
            registered_face_ids=("TALENT_A",),
            reset_action="Reset Network Set.",
        )
        self.assertTrue(res.survived_reset_network_set)
        self.assertEqual(res.effective_subject_recognition_in_af, "Animal")
        self.assertEqual(res.effective_face_memory_count, 1)

    def test_44_face_memory_cleared_only_by_delete_or_initialize(self) -> None:
        by_del = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_subject_recognition_in_af="Animal",
            registered_face_ids=("TALENT_A", "TALENT_B"),
            face_memory_action="Delete",
        )
        self.assertTrue(by_del.cleared_by_delete_or_initialize)
        self.assertEqual(by_del.effective_face_memory_count, 0)
        self.assertEqual(by_del.effective_subject_recognition_in_af, "Animal")

        by_init = p267.simulate_face_eye_af_clean_hdmi_hil(
            configured_subject_recognition_in_af="Animal",
            registered_face_ids=("TALENT_A", "TALENT_B"),
            reset_action="Initialize",
        )
        self.assertTrue(by_init.cleared_by_delete_or_initialize)
        self.assertEqual(by_init.effective_face_memory_count, 0)
        self.assertEqual(by_init.effective_subject_recognition_in_af, "Human")

    def test_45_forced_clean_hdmi_tracking_box_bake_blocked_eacces(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            hdmi_info_display="Off",
            force_bake_eye_frame_into_clean_hdmi=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EACCES_ERRNO)
        self.assertEqual(res.hdmi_clean_feed_eye_frame_baked_pixels, 0)

    def test_46_forced_face_memory_wipe_on_camera_settings_reset_blocked_eacces(self) -> None:
        res = p267.simulate_face_eye_af_clean_hdmi_hil(
            reset_action="Camera Settings Reset",
            force_wipe_face_memory_on_camera_reset=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EACCES_ERRNO)
        self.assertEqual(res.face_memory_camera_reset_wipe_events, 0)

    def test_47_invalid_face_eye_af_parameters_and_slot_overflow_rejected_einval(self) -> None:
        too_many_faces = tuple(f"F{i}" for i in range(9))
        res1 = p267.simulate_face_eye_af_clean_hdmi_hil(registered_face_ids=too_many_faces)
        self.assertFalse(res1.admitted)
        self.assertEqual(res1.errno_code, p267.EINVAL_ERRNO)

        res2 = p267.simulate_face_eye_af_clean_hdmi_hil(configured_right_left_eye_select="Both")
        self.assertFalse(res2.admitted)
        self.assertEqual(res2.errno_code, p267.EINVAL_ERRNO)

    def test_48_pillar_b_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pb = rep["pillar_b_face_eye_af_clean_hdmi_and_face_memory_hil"]
            self.assertTrue(pb["passed"])
            self.assertEqual(len(pb["four_menu_items"]), 4)
            self.assertEqual(len(pb["spoofed_ai_coprocessor_subjects"]), 4)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 52C & Redlines — [Version] Read-Only, Airplane Mode
    #          Badge Suppression & BODYDATA.DAT Hard-Block (13 tests: 49..61)
    # ------------------------------------------------------------------
    def test_49_version_menu_paths_and_read_only_body_702_plus_lens_inspection(self) -> None:
        res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            attached_lens_id="SEL2470GM2",
            mount_adaptor_attached=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.menu_path, "MENU -> Setup -> [Setup Option] -> [Version]")
        self.assertEqual(res.canonical_ui_path, "MENU > Setup > Setup Option > Version")
        self.assertEqual(res.body_model, "ILME-FX3")
        self.assertEqual(res.body_firmware_version, "Ver. 7.02")
        self.assertEqual(res.attached_lens_version, "Ver. 02")
        self.assertEqual(res.mount_adaptor_version, "Ver. 02")
        self.assertTrue(res.version_dialog_read_only)
        self.assertEqual(res.flash_partitions_touched, 0)

    def test_50_manual_pl_adapter_reports_placeholder_lens_version(self) -> None:
        res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            attached_lens_id="MANUAL_PL_ADAPTER",
            mount_adaptor_attached=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.attached_lens_version, "--")
        self.assertEqual(res.mount_adaptor_version, "--")

    def test_51_airplane_mode_on_suppresses_creators_app_update_badge_zero_tx(self) -> None:
        on_res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            airplane_mode="On",
            creators_app_remote_update_flag_cached=True,
        )
        self.assertTrue(on_res.creators_app_update_badge_suppressed)
        self.assertFalse(on_res.creators_app_update_badge_displayed)
        self.assertEqual(on_res.passive_tx_bytes_emitted, 0)

        off_res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            airplane_mode="Off",
            creators_app_remote_update_flag_cached=True,
        )
        self.assertFalse(off_res.creators_app_update_badge_suppressed)
        self.assertTrue(off_res.creators_app_update_badge_displayed)
        self.assertEqual(off_res.passive_tx_bytes_emitted, 0)

    def test_52_forced_rf_update_check_in_airplane_mode_blocked_eacces(self) -> None:
        res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            airplane_mode="On",
            force_emit_rf_update_check_in_airplane_mode=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EACCES_ERRNO)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_53_bodydata_dat_firmware_update_execution_hard_blocked_erofs(self) -> None:
        res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            slot1_bodydata_dat_present=True,
            execute_bodydata_update_requested=True,
            np_fz100_battery_percent=100,
            np_fz100_battery_bars=4,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EROFS_ERRNO)
        self.assertTrue(res.bodydata_update_execution_blocked)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertEqual(res.emmc_corruptions, 0)
        self.assertEqual(res.bodydata_flash_execution_events, 0)

    def test_54_lensdata_dat_firmware_update_execution_hard_blocked_erofs(self) -> None:
        res = p267.simulate_version_readonly_and_bodydata_guard_hil(
            execute_lensdata_update_requested=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p267.EROFS_ERRNO)
        self.assertTrue(res.bodydata_update_execution_blocked)
        self.assertEqual(res.physical_device_writes, 0)

    def test_55_body_and_lens_firmware_versions_invariant_across_all_resets(self) -> None:
        for act in ("Camera Settings Reset", "Reset Network Set.", "Initialize"):
            res = p267.simulate_version_readonly_and_bodydata_guard_hil(
                attached_lens_id="SEL50F12GM",
                reset_action=act,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.body_firmware_version, "Ver. 7.02")
            self.assertEqual(res.attached_lens_version, "Ver. 01")
            self.assertTrue(res.version_invariant_across_resets)

    def test_56_np_fz100_human_bench_battery_prerequisite_3_bars_51_percent(self) -> None:
        low = p267.simulate_version_readonly_and_bodydata_guard_hil(
            np_fz100_battery_percent=50,
            np_fz100_battery_bars=2,
        )
        self.assertFalse(low.human_bench_battery_prerequisite_met)

        high = p267.simulate_version_readonly_and_bodydata_guard_hil(
            np_fz100_battery_percent=51,
            np_fz100_battery_bars=3,
        )
        self.assertTrue(high.human_bench_battery_prerequisite_met)
        self.assertTrue(high.bodydata_update_execution_blocked)

    def test_57_invalid_version_and_battery_parameters_rejected_einval(self) -> None:
        bad = p267.simulate_version_readonly_and_bodydata_guard_hil(
            np_fz100_battery_percent=120,
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p267.EINVAL_ERRNO)

    def test_58_baseline_redline_guard_valid_and_bodydata_blocked(self) -> None:
        pr = p267.probe_phase267_redline_guard()
        self.assertTrue(pr.valid)
        self.assertEqual(pr.errno_code, 0)
        self.assertEqual(pr.reason_code, "REDLINES_INTACT")
        self.assertTrue(pr.bodydata_update_execution_blocked)
        self.assertTrue(pr.cnflasha_userspace_write_blocked)
        self.assertFalse(pr.persistent_emmc_writes_authorized)
        self.assertFalse(pr.hardware_live_attachment_authorized)
        self.assertEqual(pr.physical_device_writes, 0)
        self.assertEqual(pr.emmc_corruptions, 0)

    def test_59_all_16_stage52_redline_probes_individually_blocked_eacces_or_erofs(self) -> None:
        self.assertEqual(len(p267.ALL_16_REDLINE_PROBE_FIELDS), 16)
        for field in p267.ALL_16_REDLINE_PROBE_FIELDS:
            pr = p267.probe_phase267_redline_guard(**{field: True})
            self.assertFalse(pr.valid)
            if field in (
                "cnflasha_userspace_write_requested",
                "bodydata_dat_flash_execution_requested",
            ):
                self.assertEqual(pr.errno_code, p267.EROFS_ERRNO)
            else:
                self.assertEqual(pr.errno_code, p267.EACCES_ERRNO)

    def test_60_unknown_redline_probe_field_rejected_einval(self) -> None:
        bad = p267.probe_phase267_redline_guard(bogus_stage52_probe=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p267.EINVAL_ERRNO)

    def test_61_pillar_c_d_aggregate_passed_in_both_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            pcd = rep["pillar_c_d_version_readonly_bodydata_guard_and_redlines"]
            self.assertTrue(pcd["passed"])
            self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)

    # ------------------------------------------------------------------
    # Group 5: CLI, 52/52 Suite Integration & Hygiene (9 tests: 62..70)
    # ------------------------------------------------------------------
    def test_62_standalone_cli_json_and_summary_in_process_both_modes(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc1 = p267.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc1, 0)
        self.assertIn("[PASS] Phase 267 Stage 52 (52/52)", buf_sum.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p267.main(["--self-test", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["milestone"], "52/52")

    def test_63_standalone_subprocess_cli_clean_room_test_and_force_clean_room_pass(self) -> None:
        script = str(FX3_VM_DIR / "realhw_apsc_s35_face_eye_af_version_coemulator.py")
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            env_clean = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            env_clean[env_key] = "1"
            proc = subprocess.run(
                [sys.executable, "-B", script, "--self-test", "--summary"],
                cwd=str(REPO_ROOT),
                env=env_clean,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("[PASS] Phase 267 Stage 52 (52/52)", proc.stdout)
            self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)

    def test_64_fx3_vm_coemulation_suite_includes_stage52_52_of_52(self) -> None:
        self.assertTrue(self.clean_suite["all_checks_passed"])
        self.assertIn(
            "stage52_realhw_apsc_s35_face_eye_af_version_hil",
            self.clean_suite,
        )
        s52 = self.clean_suite["stage52_realhw_apsc_s35_face_eye_af_version_hil"]
        self.assertTrue(s52["all_checks_passed"])
        self.assertEqual(s52["phase_number"], 267)
        self.assertEqual(s52["milestone"], "52/52")
        self.assertEqual(
            s52["schema"],
            "realhw_apsc_s35_face_eye_af_version_coemulator_v1",
        )
        self.assertTrue(s52["bodydata_update_execution_blocked"])
        self.assertEqual(s52["apsc_s35_4k_or_raw_bypass_events"], 0)
        self.assertEqual(s52["ai_coprocessor_subject_spoof_events"], 0)
        self.assertEqual(s52["hdmi_clean_feed_eye_frame_baked_pixels"], 0)
        self.assertEqual(s52["passive_tx_bytes_emitted"], 0)
        self.assertEqual(s52["physical_device_writes"], 0)
        self.assertEqual(s52["emmc_corruptions"], 0)
        self.assertEqual(s52["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in self.default_suite if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 52)
        self.assertLess(self.clean_suite_elapsed, 4.0)

    def test_65_fx3_vm_coemulation_suite_all_52_stage_indices_1_to_52_unique_and_present(self) -> None:
        self.assertTrue(self.default_suite["all_checks_passed"])
        for idx in range(1, 53):
            matches = [k for k in self.default_suite if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(self.default_suite_elapsed, 4.0)

    def test_66_coemulation_config_stage52_flags_default_true_and_skippable(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage52_realhw_apsc_s35_face_eye_af_version_hil)
        self.assertTrue(default_cfg.include_stage52)
        self.assertTrue(default_cfg.include_phase267_realhw_apsc_s35_face_eye_af_version_hil)

        for override in (
            {"stage52_realhw_apsc_s35_face_eye_af_version_hil": False},
            {"include_stage52": False},
            {"include_phase267_realhw_apsc_s35_face_eye_af_version_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage52_realhw_apsc_s35_face_eye_af_version_hil", rep)
            self.assertFalse(rep["config"]["include_stage52"])
            self.assertFalse(rep["config"]["stage52_realhw_apsc_s35_face_eye_af_version_hil"])

    def test_67_fx3_vm_coemulation_suite_include_stage52_cli_summary(self) -> None:
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
            "--skip-stage51",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage52", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_apsc_s35_face_eye_af_version_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_68_fx3_vm_coemulation_suite_cli_skip_phase267_and_skip_stage52(self) -> None:
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
            "--skip-stage51",
        ]
        for skip_flag in ("--skip-phase267", "--skip-stage52", "--no-include-stage52"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn("stage52_realhw_apsc_s35_face_eye_af_version_hil", parsed)

    def test_69_all_safety_and_byof_redlines_locked_across_stage52_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertTrue(red["bodydata_update_execution_blocked"])
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["emmc_corruptions"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_70_no_pyc_bytecode_files_emitted_under_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
