#!/usr/bin/env python3
"""Unit tests for Phase 298 (Stage 60 — 60/60 VM Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-50
`[Focus Area]` 14-Area Hierarchy (7 Universal vs 7 Still-Only `Tracking:`),
`[AF Area Registration]` (`Lock Operation Parts = Off` Coupling) & `[Focus Area Limit]` (`>= 2`),
Body `W/T` `[Zoom Lever Speed]` (`1st=3 / 2nd=8` STBY/REC), `[Custom Key Z. Speed]`,
`[Remote Zoom Speed]` (`Variable / Fixed 1..8`) & Handle-Less `XLR-H1` Myth-Bust,
`[ISO Range Limit]` & Still-Only `[ISO AUTO Min. SS]` vs `Cine EI` Base ISO `800 / 12800`,
and `[Flash Mode]` Mechanical-Still Gate (`1/250 s`) vs `[Video Light Mode]`
`PMIC 5V <= 900 mA` Rail Guard HIL Co-Emulator (80 dual-mode tests).
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
import realhw_focus_area_zoom_lever_iso_minss_flash_coemulator as p298  # noqa: E402

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
        include_stage58=False,
        include_stage59=False,
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
]


class TestPhase298Stage60Wave50HilCoEmulator(unittest.TestCase):
    """80 dual-mode tests for Phase 298 Stage 60 (60/60 VM Stages Milestone)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_audit = p298.run_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil()
        cls.clean_audit = p298.run_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil(
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
    def test_01_schema_phase_and_60_of_60_milestone_constants(self) -> None:
        self.assertEqual(
            p298.SCHEMA_ID, "realhw_focus_area_zoom_lever_iso_minss_flash_coemulator_v1"
        )
        self.assertEqual(p298.PHASE_298_SCHEMA, p298.SCHEMA_ID)
        self.assertEqual(p298.PHASE_298_VERSION, "298.0.0")
        self.assertEqual(p298.PHASE_NUMBER, 298)
        self.assertEqual(p298.STAGE_INDEX, 60)
        self.assertEqual(p298.STAGE_TOTAL, 60)
        self.assertEqual(p298.MILESTONE_LABEL, "60/60")
        self.assertEqual(
            p298.STAGE_NAME, "stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil"
        )
        self.assertEqual(p298.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p298.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p298.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(self.default_audit["is_60th_stage_milestone"])
        self.assertTrue(self.clean_audit["is_60th_stage_milestone"])

    def test_02_hard_safety_redline_constants_locked(self) -> None:
        self.assertTrue(p298.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p298.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p298.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p298.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p298.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p298.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p298.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p298.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p298.XLR_H1_HAS_ZOOM_LEVER)
        self.assertFalse(p298.XLR_H1_HAS_REC_BUTTON)
        self.assertFalse(p298.XLR_H1_HAS_HOLD_SWITCH)
        for zero_val in (
            p298.NOP_COUNT,
            p298.GUEST_CODE_MODIFICATION_BYTES,
            p298.CP_MUTATION_BYTES,
            p298.WBI_MUTATION_BYTES,
            p298.CALIBRATION_MUTATION_BYTES,
            p298.CNFLASHA_MUTATION_BYTES,
            p298.NVRAM_PERSISTENT_WRITES,
            p298.BK4_PERSISTENT_NVRAM_WRITES,
            p298.PHYSICAL_DEVICE_WRITES,
            p298.EMMC_NFLASHA_WRITE_COUNT,
            p298.EMMC_MUTATION_BYTES,
            p298.EMMC_CORRUPTIONS,
            p298.SPI_NOR_MUTATION_BYTES,
            p298.OTP_FUSE_TOUCHES,
            p298.RPMB_COUNTER_INCREMENTS,
            p298.PHYSICAL_USB_PACKETS_EMITTED,
            p298.PASSIVE_TX_BYTES_EMITTED,
            p298.STILL_ONLY_TRACKING_EXPOSED_IN_MOVIE_EVENTS,
            p298.AF_AREA_REG_LOCK_OP_PARTS_CONFLICT_EVENTS,
            p298.FOCUS_AREA_LIMIT_UNDER_TWO_EVENTS,
            p298.XLR_H1_PHANTOM_ZOOM_OR_HOLD_EVENTS,
            p298.FX6_ZOOM_POSITION_0_99_CONFLATION_EVENTS,
            p298.CINE_EI_ISO_RANGE_OR_MINSS_BYPASS_EVENTS,
            p298.FLASH_NON_MECH_OR_MOVIE_BYPASS_EVENTS,
            p298.MISHOE_PMIC_5V_900MA_OVERCURRENT_EVENTS,
            p298.RSV_ORPHAN_COUNT,
            p298.WF12_00342260_HITS,
            p298.APPFW_CRASHES,
            p298.NULL_GPIO_DEREFS,
            p298.MAILBOX_STALLS,
            p298.STOCK_CP_FAULT_COUNT,
            p298.RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_val, 0)

    def test_03_default_and_clean_room_reports_both_pass(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p298.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.default_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.clean_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.default_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.clean_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_04_is_forced_clean_room_both_env_vars(self) -> None:
        self.assertFalse(p298.is_forced_clean_room({}))
        self.assertTrue(p298.is_forced_clean_room({p298.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p298.is_forced_clean_room({p298.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertTrue(p298.is_forced_clean_room({p298.ENV_FORCE_CLEAN_ROOM: "YES"}))
        self.assertFalse(p298.is_forced_clean_room({p298.ENV_CLEAN_ROOM_TEST: "0"}))

    def test_05_all_11_donors_verified_in_donor_audit(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        self.assertTrue(da["focus_area_14_and_reg_proven"])
        self.assertTrue(da["zoom_lever_and_fx6_handle_proven"])
        self.assertTrue(da["iso_minss_and_flash_videolight_proven"])
        self.assertEqual(da["errors"], ())
        self.assertEqual(len(p298.DONOR_RELPATHS), 11)
        self.assertEqual(len(p298.EXPECTED_DONOR_BYTES), 11)

    def test_06_clean_room_11_donors_synthetic_parity(self) -> None:
        da = self.clean_audit["donor_audit"]
        self.assertEqual(da["source_mode"], p298.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(da["access_mode"], p298.DONOR_ACCESS_MODE)
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["fx3_appfw"]["file_bytes"], p298.EXPECTED_DONOR_BYTES["fx3_appfw"])
        self.assertEqual(da["fx3_bk4"]["file_bytes"], p298.EXPECTED_DONOR_BYTES["fx3_bk4"])
        self.assertEqual(da["fx6_appfw"]["file_bytes"], p298.EXPECTED_DONOR_BYTES["fx6_appfw"])
        self.assertTrue(da["fx3_appfw"]["bounded_windows_only"])

    def test_07_bounded_windows_never_exceed_4096_bytes_and_o_rdonly(self) -> None:
        self.assertLessEqual(p298.BOUNDED_WINDOW_MAX_BYTES, 4096)
        for key, windows in p298.LARGE_DONOR_WINDOWS.items():
            offsets = sorted({w[0] for w in windows})
            self.assertGreaterEqual(len(offsets), 2, msg=key)
            self.assertEqual(
                self.clean_audit["donor_audit"][key]["bytes_read_total"],
                len(offsets) * p298.BOUNDED_WINDOW_MAX_BYTES,
                msg=key,
            )

    def test_08_missing_mac_root_falls_back_to_clean_room_without_error(self) -> None:
        with unittest.mock.patch.object(
            p298,
            "_iter_work_roots",
            return_value=(Path("/nonexistent/phase298/missing_work"),),
        ):
            missing = p298.inspect_phase298_donors(env={})
        self.assertEqual(missing.source_mode, p298.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(missing.all_contracts_verified)
        self.assertEqual(missing.raw_firmware_bytes_leaked, 0)

    def test_09_bounded_o_rdonly_rejects_oversized_or_negative_reads(self) -> None:
        dummy_path = Path(__file__)
        with self.assertRaises(ValueError):
            p298._read_bounded_o_rdonly(dummy_path, 0, p298.BOUNDED_WINDOW_MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            p298._read_bounded_o_rdonly(dummy_path, 0, -1)

    def test_10_donor_audit_cache_and_singleton_identity(self) -> None:
        c1 = p298.inspect_phase298_donors(force_clean_room=True)
        c2 = p298.inspect_phase298_donors(force_clean_room=True)
        self.assertIs(c1, c2)
        d1 = p298.inspect_phase298_donors(force_clean_room=False)
        d2 = p298.inspect_phase298_donors(force_clean_room=False)
        self.assertIs(d1, d2)

    def test_11_deterministic_audit_digest_sha256(self) -> None:
        rep_a = p298.run_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil(
            force_clean_room=True
        )
        rep_b = p298.run_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil(
            force_clean_room=True
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])
        self.assertEqual(len(str(rep_a["audit_digest_sha256"])), 64)

    def test_12_no_write_open_flags_and_zero_raw_firmware_bytes_in_json(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("O_WRONLY", src)
        self.assertNotIn("O_RDWR", src)
        self.assertNotIn("O_CREAT", src)
        dumped = json.dumps(self.clean_audit)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(self.clean_audit["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_13_resolve_donor_paths_clean_room_sentinel_and_env_roots(self) -> None:
        paths_clean = p298.resolve_phase298_donor_paths(env={p298.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths_clean), 11)
        for p in paths_clean.values():
            self.assertIn(p298.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
        roots = p298._iter_work_roots(env={p298.ENV_MAC_WORK_ROOT: "/tmp/custom_fx3_work"})
        self.assertEqual(roots[0], Path("/tmp/custom_fx3_work"))

    def test_14_compact_donor_markers_verified_in_4_languages(self) -> None:
        da = self.clean_audit["donor_audit"]
        for key in ("fx3_string_en_f", "fx3_string_sc_f", "fx3_string_tc_f", "fx3_string_ja_f"):
            self.assertTrue(da[key]["uxd_container_ok"], msg=key)
            self.assertTrue(all(v == 1 for v in da[key]["marker_hits"].values()), msg=key)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 60A — [Focus Area] 14-Area Hierarchy (7 Universal
    #          vs 7 Still-Only Tracking:), [AF Area Registration] &
    #          [Focus Area Limit] >= 2 (17 tests)
    # ------------------------------------------------------------------
    def test_15_fx3_exposes_exact_7_universal_plus_7_tracking_equals_14_areas(self) -> None:
        self.assertEqual(len(p298.FX3_7_UNIVERSAL_FOCUS_AREAS), 7)
        self.assertEqual(len(p298.FX3_7_STILL_ONLY_TRACKING_AREAS), 7)
        self.assertEqual(len(p298.FX3_14_FOCUS_AREAS), 14)
        self.assertTrue(
            all(a.startswith("Tracking: ") for a in p298.FX3_7_STILL_ONLY_TRACKING_AREAS)
        )
        self.assertTrue(
            all(not a.startswith("Tracking: ") for a in p298.FX3_7_UNIVERSAL_FOCUS_AREAS)
        )

    def test_16_7_universal_focus_areas_admitted_in_still_movie_and_sq(self) -> None:
        for domain in (
            p298.EXPOSURE_MODE_STILL,
            p298.EXPOSURE_MODE_MOVIE,
            p298.EXPOSURE_MODE_SQ,
        ):
            for area in p298.FX3_7_UNIVERSAL_FOCUS_AREAS:
                r = p298.simulate_focus_area_tracking_and_af_reg_hil(
                    shooting_domain=domain,
                    requested_focus_area=area,
                )
                self.assertTrue(r.admitted, msg=f"{domain}:{area}")
                self.assertEqual(r.effective_focus_area, area)
                self.assertFalse(r.is_still_only_tracking_area)

    def test_17_all_7_tracking_areas_admitted_in_still_af_and_blocked_in_mf(self) -> None:
        for area in p298.FX3_7_STILL_ONLY_TRACKING_AREAS:
            r = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=p298.EXPOSURE_MODE_STILL,
                af_mode=p298.AF_MODE_AFC,
                requested_focus_area=area,
            )
            self.assertTrue(r.admitted, msg=area)
            self.assertTrue(r.is_still_only_tracking_area)
        mf_rej = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            af_mode=p298.AF_MODE_MF,
            requested_focus_area="Tracking: Wide",
        )
        self.assertFalse(mf_rej.admitted)
        self.assertEqual(mf_rej.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_18_all_7_still_only_tracking_areas_rejected_eopnotsupp_in_movie_and_sq(self) -> None:
        for domain in (p298.EXPOSURE_MODE_MOVIE, p298.EXPOSURE_MODE_SQ):
            for area in p298.FX3_7_STILL_ONLY_TRACKING_AREAS:
                r = p298.simulate_focus_area_tracking_and_af_reg_hil(
                    shooting_domain=domain,
                    requested_focus_area=area,
                )
                self.assertFalse(r.admitted, msg=f"{domain}:{area}")
                self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
                self.assertEqual(r.still_only_tracking_exposed_in_movie_events, 0)

    def test_19_movie_sq_touch_tracking_allowed_with_af_and_optical_zoom_only(self) -> None:
        for domain in (p298.EXPOSURE_MODE_MOVIE, p298.EXPOSURE_MODE_SQ):
            ok = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=domain,
                af_mode=p298.AF_MODE_AFC,
                requested_focus_area="Wide",
                touch_tracking_requested=True,
                optical_zoom_active=True,
            )
            self.assertTrue(ok.admitted, msg=domain)
            self.assertTrue(ok.touch_tracking_used_for_movie)
        mf_blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_MOVIE,
            af_mode=p298.AF_MODE_MF,
            touch_tracking_requested=True,
        )
        self.assertFalse(mf_blk.admitted)
        self.assertEqual(mf_blk.errno_code, p298.EOPNOTSUPP_ERRNO)

        ciz_blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_MOVIE,
            af_mode=p298.AF_MODE_AFC,
            touch_tracking_requested=True,
            optical_zoom_active=False,
        )
        self.assertFalse(ciz_blk.admitted)
        self.assertEqual(ciz_blk.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_20_iauto_locks_focus_area_strictly_to_wide(self) -> None:
        wide_ok = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_IAUTO,
            requested_focus_area="Wide",
        )
        self.assertTrue(wide_ok.admitted)
        for area in ("Zone", "Spot: M", "Tracking: Wide"):
            blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=p298.EXPOSURE_MODE_IAUTO,
                requested_focus_area=area,
            )
            self.assertFalse(blk.admitted, msg=area)
            self.assertEqual(blk.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_21_af_area_registration_forces_lock_operation_parts_off(self) -> None:
        forced = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            af_area_registration=p298.TOGGLE_ON,
            requested_lock_op_parts=p298.LOCK_OP_PARTS_ALL,
        )
        self.assertTrue(forced.admitted)
        self.assertEqual(forced.effective_lock_op_parts, p298.LOCK_OP_PARTS_OFF)

        conflict = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            af_area_registration=p298.TOGGLE_ON,
            requested_lock_op_parts=p298.LOCK_OP_PARTS_MULTI_SELECTOR,
            require_lock_op_parts_active_with_af_reg=True,
        )
        self.assertFalse(conflict.admitted)
        self.assertEqual(conflict.errno_code, p298.EOPNOTSUPP_ERRNO)
        self.assertEqual(conflict.af_area_reg_lock_op_parts_conflict_events, 0)

    def test_22_af_area_registration_disabled_in_movie_sq_and_iauto(self) -> None:
        for domain in (
            p298.EXPOSURE_MODE_MOVIE,
            p298.EXPOSURE_MODE_SQ,
            p298.EXPOSURE_MODE_IAUTO,
        ):
            r = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=domain,
                af_area_registration=p298.TOGGLE_ON,
            )
            self.assertFalse(r.admitted, msg=domain)
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_23_af_reg_and_focus_color_survive_cam_reset_but_wiped_by_initialize(self) -> None:
        csr = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            requested_focus_area="Spot: M",
            af_area_registration=p298.TOGGLE_ON,
            focus_area_color=p298.FOCUS_COLOR_RED,
            switch_vh_af_area=p298.SWITCH_VH_AF_POINT_AND_AREA,
            circ_of_focus_point=p298.CIRC_CIRCULATE,
            reset_action=p298.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(csr.admitted)
        self.assertTrue(csr.focus_area_reset_to_wide)
        self.assertEqual(csr.effective_focus_area, "Wide")
        self.assertTrue(csr.af_area_reg_survived_camera_reset)
        self.assertTrue(csr.focus_color_survived_camera_reset)
        self.assertEqual(csr.focus_area_color, p298.FOCUS_COLOR_RED)
        self.assertEqual(csr.switch_vh_af_area, p298.SWITCH_VH_OFF)
        self.assertEqual(csr.circ_of_focus_point, p298.CIRC_DOES_NOT_CIRCULATE)

        ini = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            requested_focus_area="Spot: M",
            af_area_registration=p298.TOGGLE_ON,
            focus_area_color=p298.FOCUS_COLOR_RED,
            reset_action=p298.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(ini.admitted)
        self.assertEqual(ini.af_area_registration, p298.TOGGLE_OFF)
        self.assertTrue(ini.registered_af_area_cleared)
        self.assertEqual(ini.focus_area_color, p298.FOCUS_COLOR_WHITE)

    def test_24_del_regist_af_area_clears_registration(self) -> None:
        r = p298.simulate_focus_area_tracking_and_af_reg_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            af_area_registration=p298.TOGGLE_ON,
            delete_registered_af_area=True,
            reset_action=p298.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.registered_af_area_cleared)
        self.assertFalse(r.af_area_reg_survived_camera_reset)

    def test_25_focus_area_limit_enforces_min_2_and_blocks_excluded_area(self) -> None:
        for bad_lim in ((), ("Wide",), ("Wide", "Wide")):
            rej = p298.simulate_focus_area_tracking_and_af_reg_hil(
                enabled_limit_areas=bad_lim,
                requested_focus_area="Wide",
            )
            self.assertFalse(rej.admitted, msg=str(bad_lim))
            self.assertEqual(rej.errno_code, p298.EINVAL_ERRNO)
            self.assertEqual(rej.focus_area_limit_under_two_events, 0)

        excl = p298.simulate_focus_area_tracking_and_af_reg_hil(
            enabled_limit_areas=("Wide", "Zone"),
            requested_focus_area="Center Fix",
        )
        self.assertFalse(excl.admitted)
        self.assertEqual(excl.errno_code, p298.EOPNOTSUPP_ERRNO)

        ok = p298.simulate_focus_area_tracking_and_af_reg_hil(
            enabled_limit_areas=("Wide", "Tracking: Spot S"),
            requested_focus_area="Tracking: Spot S",
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.enabled_limit_areas_count, 2)

    def test_26_switch_vh_af_area_still_pasm_only(self) -> None:
        for mode in (p298.SWITCH_VH_AF_POINT_ONLY, p298.SWITCH_VH_AF_POINT_AND_AREA):
            ok = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=p298.EXPOSURE_MODE_STILL,
                switch_vh_af_area=mode,
            )
            self.assertTrue(ok.admitted, msg=mode)
            blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
                shooting_domain=p298.EXPOSURE_MODE_MOVIE,
                switch_vh_af_area=mode,
            )
            self.assertFalse(blk.admitted, msg=mode)
            self.assertEqual(blk.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_27_focus_area_color_and_circ_of_focus_point_options(self) -> None:
        for color in p298.VALID_FOCUS_COLORS:
            for circ in p298.VALID_CIRC_MODES:
                r = p298.simulate_focus_area_tracking_and_af_reg_hil(
                    focus_area_color=color,
                    circ_of_focus_point=circ,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.focus_area_color, color)
                self.assertEqual(r.circ_of_focus_point, circ)

    def test_28_fx6_3_area_contrast_blocks_tracking_limit_and_af_reg(self) -> None:
        self.assertEqual(p298.FX6_3_FOCUS_AREAS, ("Wide", "Zone", "Flexible Spot"))
        for area in p298.FX6_3_FOCUS_AREAS:
            ok = p298.simulate_focus_area_tracking_and_af_reg_hil(
                body_profile=p298.BODY_MODEL_FX6,
                shooting_domain=p298.EXPOSURE_MODE_MOVIE,
                requested_focus_area=area,
            )
            self.assertTrue(ok.admitted, msg=area)
        for bad_area in ("Tracking: Wide", "Spot: S"):
            rej = p298.simulate_focus_area_tracking_and_af_reg_hil(
                body_profile=p298.BODY_MODEL_FX6,
                requested_focus_area=bad_area,
            )
            self.assertFalse(rej.admitted, msg=bad_area)
            self.assertEqual(rej.errno_code, p298.EOPNOTSUPP_ERRNO)

        reg_blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
            body_profile=p298.BODY_MODEL_FX6,
            requested_focus_area="Wide",
            af_area_registration=p298.TOGGLE_ON,
        )
        self.assertFalse(reg_blk.admitted)
        self.assertEqual(reg_blk.errno_code, p298.EOPNOTSUPP_ERRNO)

        lim_blk = p298.simulate_focus_area_tracking_and_af_reg_hil(
            body_profile=p298.BODY_MODEL_FX6,
            requested_focus_area="Wide",
            enabled_limit_areas=("Wide", "Zone"),
        )
        self.assertFalse(lim_blk.admitted)
        self.assertEqual(lim_blk.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_29_invalid_pillar_a_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"shooting_domain": "RAW_ONLY"},
            {"af_mode": "AF-Z"},
            {"requested_focus_area": "Flexible Spot: M"},
            {"enabled_limit_areas": ("Wide", "BogusArea")},
            {"af_area_registration": "Auto"},
            {"requested_lock_op_parts": "Trigger"},
            {"switch_vh_af_area": "Full"},
            {"focus_area_color": "Green"},
            {"circ_of_focus_point": "Diagonal"},
            {"reset_action": "FactoryWipe"},
        ):
            r = p298.simulate_focus_area_tracking_and_af_reg_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO, msg=str(kwargs))

    def test_30_fx3a_body_profile_parity_with_fx3_for_pillar_a(self) -> None:
        r = p298.simulate_focus_area_tracking_and_af_reg_hil(
            body_profile=p298.BODY_MODEL_FX3A,
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            requested_focus_area="Tracking: Expand Spot",
            af_area_registration=p298.TOGGLE_ON,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_lock_op_parts, p298.LOCK_OP_PARTS_OFF)

    def test_31_pillar_a_dict_passed_and_zero_physical_writes(self) -> None:
        pa = self.default_audit["pillar_a_focus_area_14_and_reg_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["fx3_14_focus_areas"]), 14)
        self.assertEqual(len(pa["fx3_7_movie_tracking_blocked_eopnotsupp"]), 7)
        self.assertEqual(pa["af_reg_survives_cam_reset"]["physical_device_writes"], 0)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 60B — Body W/T [Zoom Lever Speed],
    #          [Custom Key Z. Speed], [Remote Zoom Speed] &
    #          Handle-Less XLR-H1 Myth-Bust (16 tests)
    # ------------------------------------------------------------------
    def test_32_fx3_body_wt_zoom_lever_and_remote_defaults(self) -> None:
        r = p298.simulate_zoom_lever_speed_and_xlrh1_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.active_lever_1st_speed, 3)
        self.assertEqual(r.active_lever_2nd_speed, 8)
        self.assertEqual(r.active_custom_key_speed, 3)
        self.assertEqual(r.remote_speed_type, p298.REMOTE_SPEED_TYPE_VARIABLE)
        self.assertEqual(r.active_remote_speed, 0)

    def test_33_separate_stby_and_rec_registers_for_all_zoom_speeds(self) -> None:
        stby = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            recording_active=False,
            lever_1st_stby=1,
            lever_1st_rec=4,
            lever_2nd_stby=5,
            lever_2nd_rec=8,
            custom_key_stby=2,
            custom_key_rec=6,
            remote_speed_type=p298.REMOTE_SPEED_TYPE_FIXED,
            remote_fixed_stby=3,
            remote_fixed_rec=7,
        )
        self.assertTrue(stby.admitted)
        self.assertEqual(stby.active_lever_1st_speed, 1)
        self.assertEqual(stby.active_lever_2nd_speed, 5)
        self.assertEqual(stby.active_custom_key_speed, 2)
        self.assertEqual(stby.active_remote_speed, 3)

        rec = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            recording_active=True,
            lever_1st_stby=1,
            lever_1st_rec=4,
            lever_2nd_stby=5,
            lever_2nd_rec=8,
            custom_key_stby=2,
            custom_key_rec=6,
            remote_speed_type=p298.REMOTE_SPEED_TYPE_FIXED,
            remote_fixed_stby=3,
            remote_fixed_rec=7,
        )
        self.assertTrue(rec.admitted)
        self.assertEqual(rec.active_lever_1st_speed, 4)
        self.assertEqual(rec.active_lever_2nd_speed, 8)
        self.assertEqual(rec.active_custom_key_speed, 6)
        self.assertEqual(rec.active_remote_speed, 7)

    def test_34_remote_zoom_speed_variable_vs_fixed_1_to_8(self) -> None:
        var = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            remote_speed_type=p298.REMOTE_SPEED_TYPE_VARIABLE,
        )
        self.assertTrue(var.admitted)
        self.assertEqual(var.active_remote_speed, 0)
        for spd in (1, 4, 8):
            fix = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                remote_speed_type=p298.REMOTE_SPEED_TYPE_FIXED,
                remote_fixed_stby=spd,
            )
            self.assertTrue(fix.admitted, msg=str(spd))
            self.assertEqual(fix.active_remote_speed, spd)

    def test_35_xlr_h1_hardware_topology_zero_zoom_zero_rec_zero_hold(self) -> None:
        r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(xlr_h1_attached=True)
        self.assertTrue(r.admitted)
        self.assertTrue(r.xlr_h1_attached)
        self.assertFalse(r.xlr_h1_has_zoom_lever)
        self.assertFalse(r.xlr_h1_has_rec_button)
        self.assertFalse(r.xlr_h1_has_hold_switch)

    def test_36_xlr_h1_handle_zoom_injection_rejected_eopnotsupp(self) -> None:
        r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            xlr_h1_attached=True,
            handle_zoom_action_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "FX3_XLR_H1_HAS_NO_ZOOM_LEVER_OR_HOLD_SWITCH")
        self.assertEqual(r.xlr_h1_phantom_zoom_or_hold_events, 0)

    def test_37_xlr_h1_handle_hold_switch_injection_rejected_eopnotsupp(self) -> None:
        r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            xlr_h1_attached=True,
            handle_hold_switch_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.xlr_h1_phantom_zoom_or_hold_events, 0)

    def test_38_zoom_range_all_3_modes_admitted_in_standard_non_raw(self) -> None:
        for zr in p298.VALID_ZOOM_RANGES:
            r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                zoom_range=zr,
                shooting_raw=False,
                frame_rate_fps=23.98,
            )
            self.assertTrue(r.admitted, msg=zr)
            self.assertEqual(r.zoom_range, zr)

    def test_39_zoom_range_non_optical_locked_in_raw(self) -> None:
        for zr in (p298.ZOOM_RANGE_CLEAR_IMAGE, p298.ZOOM_RANGE_DIGITAL):
            r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                zoom_range=zr,
                shooting_raw=True,
            )
            self.assertFalse(r.admitted, msg=zr)
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_40_zoom_range_non_optical_locked_at_100p_and_119_88p(self) -> None:
        for fps in (100.0, 119.88):
            for zr in (p298.ZOOM_RANGE_CLEAR_IMAGE, p298.ZOOM_RANGE_DIGITAL):
                r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                    zoom_range=zr,
                    frame_rate_fps=fps,
                )
                self.assertFalse(r.admitted, msg=f"{zr}@{fps}")
                self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_41_zoom_speeds_reset_by_camera_reset_while_zoom_range_survives(self) -> None:
        csr = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            zoom_range=p298.ZOOM_RANGE_CLEAR_IMAGE,
            lever_1st_stby=1,
            lever_2nd_stby=5,
            custom_key_stby=7,
            remote_speed_type=p298.REMOTE_SPEED_TYPE_FIXED,
            remote_fixed_stby=6,
            reset_action=p298.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(csr.admitted)
        self.assertTrue(csr.zoom_range_survived_camera_reset)
        self.assertEqual(csr.zoom_range, p298.ZOOM_RANGE_CLEAR_IMAGE)
        self.assertTrue(csr.zoom_speeds_reset_to_defaults)
        self.assertEqual(csr.active_lever_1st_speed, 3)
        self.assertEqual(csr.active_lever_2nd_speed, 8)
        self.assertEqual(csr.active_custom_key_speed, 3)
        self.assertEqual(csr.remote_speed_type, p298.REMOTE_SPEED_TYPE_VARIABLE)

        ini = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            zoom_range=p298.ZOOM_RANGE_DIGITAL,
            reset_action=p298.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(ini.admitted)
        self.assertEqual(ini.zoom_range, p298.ZOOM_RANGE_OPTICAL)

    def test_42_fx6_smart_handle_zoom_and_handle_hold_switch_contrast(self) -> None:
        for hm in p298.FX6_HANDLE_ZOOM_MODES:
            for hh in p298.FX6_HANDLE_HOLD_MODES:
                r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                    body_profile=p298.BODY_MODEL_FX6,
                    fx6_handle_zoom_mode=hm,
                    fx6_handle_hold_mode=hh,
                    fx6_zoom_position_display=50,
                )
                self.assertTrue(r.admitted, msg=f"{hm}/{hh}")
                self.assertEqual(r.fx6_handle_zoom_mode, hm)
                self.assertEqual(r.fx6_handle_hold_mode, hh)
                self.assertEqual(r.fx6_zoom_position_display, 50)

    def test_43_fx6_zoom_position_0_99_not_speed_scale_conflation_rejected(self) -> None:
        confl = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            body_profile=p298.BODY_MODEL_FX6,
            zoom_position_display_0_99_conflation_requested=True,
        )
        self.assertFalse(confl.admitted)
        self.assertEqual(confl.errno_code, p298.EINVAL_ERRNO)
        self.assertEqual(confl.fx6_zoom_position_0_99_conflation_events, 0)

        for bad_pos in (-1, 100, True):
            r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
                body_profile=p298.BODY_MODEL_FX6,
                fx6_zoom_position_display=bad_pos,  # type: ignore[arg-type]
            )
            self.assertFalse(r.admitted, msg=str(bad_pos))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO)

    def test_44_zoom_speed_1_to_8_bounds_enforced_einval(self) -> None:
        for field in (
            "lever_1st_stby",
            "lever_1st_rec",
            "lever_2nd_stby",
            "lever_2nd_rec",
            "custom_key_stby",
            "custom_key_rec",
            "remote_fixed_stby",
            "remote_fixed_rec",
        ):
            for bad in (0, 9, True):
                r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(**{field: bad})
                self.assertFalse(r.admitted, msg=f"{field}={bad}")
                self.assertEqual(r.errno_code, p298.EINVAL_ERRNO)

    def test_45_invalid_pillar_b_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"zoom_range": "Teleconverter"},
            {"remote_speed_type": "Stepwise"},
            {"reset_action": "Reboot"},
            {"frame_rate_fps": 0.0},
            {"frame_rate_fps": True},
            {"body_profile": p298.BODY_MODEL_FX6, "fx6_handle_zoom_mode": "Ultra"},
            {"body_profile": p298.BODY_MODEL_FX6, "fx6_handle_hold_mode": "ZoomOnly"},
        ):
            r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO, msg=str(kwargs))

    def test_46_fx3a_body_profile_parity_with_fx3_for_pillar_b(self) -> None:
        r = p298.simulate_zoom_lever_speed_and_xlrh1_hil(
            body_profile=p298.BODY_MODEL_FX3A,
            handle_zoom_action_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_47_pillar_b_dict_passed_and_zero_physical_writes(self) -> None:
        pb = self.default_audit["pillar_b_zoom_lever_and_xlrh1_hil"]
        self.assertTrue(pb["passed"])
        self.assertFalse(pb["xlr_h1_has_zoom_lever"])
        self.assertFalse(pb["xlr_h1_has_rec_button"])
        self.assertFalse(pb["xlr_h1_has_hold_switch"])
        self.assertEqual(pb["body_wt_stby_defaults"]["physical_device_writes"], 0)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 60C — [ISO Range Limit], Still-Only
    #          [ISO AUTO Min. SS] vs Cine EI Base ISO 800 / 12800,
    #          [Flash Mode] Mechanical-Still vs [Video Light Mode]
    #          PMIC 5V <= 900 mA (22 tests)
    # ------------------------------------------------------------------
    def test_48_iso_range_limit_clamps_iso_and_validates_bounds(self) -> None:
        hi_clamp = p298.simulate_iso_minss_flash_and_videolight_hil(
            iso_mode=p298.ISO_MODE_MANUAL,
            iso_range_limit_min=400,
            iso_range_limit_max=6400,
            requested_manual_iso=25600,
        )
        self.assertTrue(hi_clamp.admitted)
        self.assertEqual(hi_clamp.effective_manual_iso, 6400)

        lo_clamp = p298.simulate_iso_minss_flash_and_videolight_hil(
            iso_mode=p298.ISO_MODE_MANUAL,
            iso_range_limit_min=400,
            iso_range_limit_max=6400,
            requested_manual_iso=100,
        )
        self.assertTrue(lo_clamp.admitted)
        self.assertEqual(lo_clamp.effective_manual_iso, 400)

        for bad in (
            {"iso_range_limit_min": 6400, "iso_range_limit_max": 400},
            {"iso_range_limit_min": 25},
            {"iso_range_limit_max": 819200},
        ):
            rej = p298.simulate_iso_minss_flash_and_videolight_hil(**bad)
            self.assertFalse(rej.admitted, msg=str(bad))
            self.assertEqual(rej.errno_code, p298.EINVAL_ERRNO)

    def test_49_iso_auto_min_ss_presets_and_thresholds_admitted_in_still_p_a_m(self) -> None:
        for pasm in (p298.PASM_P, p298.PASM_A, p298.PASM_M):
            for preset in (
                p298.ISO_MIN_SS_SLOWER,
                p298.ISO_MIN_SS_STANDARD,
                p298.ISO_MIN_SS_FASTER,
                "1/8000",
                "1/250",
                '30"',
            ):
                r = p298.simulate_iso_minss_flash_and_videolight_hil(
                    shooting_domain=p298.EXPOSURE_MODE_STILL,
                    pasm_mode=pasm,
                    iso_mode=p298.ISO_MODE_AUTO,
                    iso_auto_min_ss=preset,
                    iso_auto_min_ss_explicit_requested=True,
                )
                self.assertTrue(r.admitted, msg=f"{pasm}:{preset}")
                self.assertEqual(r.effective_iso_auto_min_ss, preset)

    def test_50_iso_auto_min_ss_rejected_in_s_mode_and_manual_iso(self) -> None:
        s_rej = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            pasm_mode=p298.PASM_S,
            iso_mode=p298.ISO_MODE_AUTO,
            iso_auto_min_ss=p298.ISO_MIN_SS_FAST,
            iso_auto_min_ss_explicit_requested=True,
        )
        self.assertFalse(s_rej.admitted)
        self.assertEqual(s_rej.errno_code, p298.EOPNOTSUPP_ERRNO)

        man_rej = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            pasm_mode=p298.PASM_A,
            iso_mode=p298.ISO_MODE_MANUAL,
            iso_auto_min_ss=p298.ISO_MIN_SS_FAST,
            iso_auto_min_ss_explicit_requested=True,
        )
        self.assertFalse(man_rej.admitted)
        self.assertEqual(man_rej.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_51_iso_auto_min_ss_strictly_still_only_rejected_in_movie_sq_iauto(self) -> None:
        for domain in (
            p298.EXPOSURE_MODE_MOVIE,
            p298.EXPOSURE_MODE_SQ,
            p298.EXPOSURE_MODE_IAUTO,
        ):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                shooting_domain=domain,
                pasm_mode=p298.PASM_A,
                iso_mode=p298.ISO_MODE_AUTO,
                iso_auto_min_ss=p298.ISO_MIN_SS_FAST,
                iso_auto_min_ss_explicit_requested=True,
            )
            self.assertFalse(r.admitted, msg=domain)
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_52_iso_auto_max_reached_triggers_slower_shutter_override(self) -> None:
        r = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            pasm_mode=p298.PASM_A,
            iso_mode=p298.ISO_MODE_AUTO,
            iso_auto_min_ss="1/250",
            iso_auto_max_reached=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_iso_auto_min_ss, "ISO_AUTO_MAX_SLOWER_OVERRIDE")

    def test_53_cine_ei_and_cine_ei_quick_pin_base_iso_800_and_12800(self) -> None:
        for mode in (p298.LOG_SHOOTING_CINE_EI, p298.LOG_SHOOTING_CINE_EI_QUICK):
            for base in (800, 12800):
                r = p298.simulate_iso_minss_flash_and_videolight_hil(
                    shooting_domain=p298.EXPOSURE_MODE_MOVIE,
                    log_shooting_mode=mode,
                    cine_ei_base_iso=base,
                    requested_manual_iso=3200,
                )
                self.assertTrue(r.admitted, msg=f"{mode}:{base}")
                self.assertTrue(r.cine_ei_locked_iso_controls)
                self.assertEqual(r.effective_manual_iso, base)

    def test_54_cine_ei_locks_out_iso_range_limit_and_min_ss_eopnotsupp(self) -> None:
        for field in ("iso_range_limit_explicit_requested", "iso_auto_min_ss_explicit_requested"):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                shooting_domain=p298.EXPOSURE_MODE_MOVIE,
                log_shooting_mode=p298.LOG_SHOOTING_CINE_EI,
                **{field: True},
            )
            self.assertFalse(r.admitted, msg=field)
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.cine_ei_iso_range_or_minss_bypass_events, 0)

    def test_55_flexible_iso_retains_variable_iso_in_movie(self) -> None:
        r = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_MOVIE,
            log_shooting_mode=p298.LOG_SHOOTING_FLEXIBLE_ISO,
            iso_mode=p298.ISO_MODE_MANUAL,
            requested_manual_iso=3200,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.cine_ei_locked_iso_controls)
        self.assertEqual(r.effective_manual_iso, 3200)

    def test_56_flash_mode_5_modes_mechanical_still_1_250s_sync_ceiling(self) -> None:
        self.assertEqual(len(p298.VALID_FLASH_MODES), 5)
        self.assertEqual(p298.DEFAULT_FLASH_MODE, p298.FLASH_MODE_FILL)
        self.assertAlmostEqual(p298.FLASH_SYNC_CEILING_SEC, 1.0 / 250.0, places=6)
        for fm in p298.VALID_FLASH_MODES:
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                shooting_domain=p298.EXPOSURE_MODE_STILL,
                shutter_type=p298.SHUTTER_TYPE_MECHANICAL,
                silent_mode=p298.TOGGLE_OFF,
                flash_mode=fm,
            )
            self.assertTrue(r.admitted, msg=fm)
            self.assertEqual(r.flash_mode, fm)
            if fm != p298.FLASH_MODE_OFF:
                self.assertTrue(r.flash_active)
                self.assertIn("1/250 s", r.effective_iso_auto_min_ss)

    def test_57_flash_strictly_still_only_rejected_in_movie_sq_iauto(self) -> None:
        for domain in (
            p298.EXPOSURE_MODE_MOVIE,
            p298.EXPOSURE_MODE_SQ,
            p298.EXPOSURE_MODE_IAUTO,
        ):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                shooting_domain=domain,
                shutter_type=p298.SHUTTER_TYPE_MECHANICAL,
                flash_mode=p298.FLASH_MODE_FILL,
            )
            self.assertFalse(r.admitted, msg=domain)
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.flash_non_mech_or_movie_bypass_events, 0)

    def test_58_flash_rejected_under_electronic_shutter_eopnotsupp(self) -> None:
        r = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            shutter_type=p298.SHUTTER_TYPE_ELECTRONIC,
            flash_mode=p298.FLASH_MODE_AUTO,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.flash_non_mech_or_movie_bypass_events, 0)

    def test_59_flash_rejected_under_silent_mode_on_eopnotsupp(self) -> None:
        for kw in (
            {"flash_mode": p298.FLASH_MODE_FILL},
            {"wireless_flash": p298.TOGGLE_ON},
            {"red_eye_reduction": p298.TOGGLE_ON},
            {"flash_comp_ev": 1.0},
        ):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                shooting_domain=p298.EXPOSURE_MODE_STILL,
                shutter_type=p298.SHUTTER_TYPE_MECHANICAL,
                silent_mode=p298.TOGGLE_ON,
                **kw,
            )
            self.assertFalse(r.admitted, msg=str(kw))
            self.assertEqual(r.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_60_fx6_rejected_for_still_flash_and_iso_auto_min_ss(self) -> None:
        fl = p298.simulate_iso_minss_flash_and_videolight_hil(
            body_profile=p298.BODY_MODEL_FX6,
            shutter_type=p298.SHUTTER_TYPE_ELECTRONIC,
            flash_mode=p298.FLASH_MODE_FILL,
        )
        self.assertFalse(fl.admitted)
        self.assertEqual(fl.errno_code, p298.EOPNOTSUPP_ERRNO)

        ss = p298.simulate_iso_minss_flash_and_videolight_hil(
            body_profile=p298.BODY_MODEL_FX6,
            iso_auto_min_ss_explicit_requested=True,
        )
        self.assertFalse(ss.admitted)
        self.assertEqual(ss.errno_code, p298.EOPNOTSUPP_ERRNO)

    def test_61_video_light_mode_4_modes_admitted_across_still_movie_sq_within_900ma(self) -> None:
        self.assertEqual(len(p298.VALID_VIDEO_LIGHT_MODES), 4)
        for domain in (
            p298.EXPOSURE_MODE_STILL,
            p298.EXPOSURE_MODE_MOVIE,
            p298.EXPOSURE_MODE_SQ,
        ):
            for vl in p298.VALID_VIDEO_LIGHT_MODES:
                r = p298.simulate_iso_minss_flash_and_videolight_hil(
                    shooting_domain=domain,
                    video_light_mode=vl,
                    video_light_active=True,
                    mishoe_current_ma=900,
                )
                self.assertTrue(r.admitted, msg=f"{domain}:{vl}")
                self.assertTrue(r.video_light_active)
                self.assertFalse(r.pmic_5v_overcurrent_tripped)

    def test_62_mishoe_pmic_5v_gt_900ma_overcurrent_blocked_eacces(self) -> None:
        r = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_MOVIE,
            video_light_mode=p298.VIDEO_LIGHT_REC_LINK_STBY,
            video_light_active=True,
            mishoe_current_ma=901,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p298.EACCES_ERRNO)
        self.assertTrue(r.pmic_5v_overcurrent_tripped)
        self.assertFalse(r.video_light_active)
        self.assertEqual(r.mishoe_pmic_5v_900ma_overcurrent_events, 0)

    def test_63_mishoe_non_sony_sync_gt_250v_blocked_eacces(self) -> None:
        ok_250 = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            flash_mode=p298.FLASH_MODE_FILL,
            mishoe_non_sony_sync_volts=250,
        )
        self.assertTrue(ok_250.admitted)

        bad_251 = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            flash_mode=p298.FLASH_MODE_FILL,
            mishoe_non_sony_sync_volts=251,
        )
        self.assertFalse(bad_251.admitted)
        self.assertEqual(bad_251.errno_code, p298.EACCES_ERRNO)

    def test_64_pillar_c_reset_lifecycle_split_cam_reset_vs_initialize(self) -> None:
        csr = p298.simulate_iso_minss_flash_and_videolight_hil(
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            iso_range_limit_min=200,
            iso_range_limit_max=12800,
            iso_auto_min_ss=p298.ISO_MIN_SS_FASTER,
            flash_comp_ev=1.7,
            exp_comp_set=p298.EXP_COMP_AMBIENT_ONLY,
            video_light_mode=p298.VIDEO_LIGHT_REC_LINK,
            reset_action=p298.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(csr.admitted)
        self.assertTrue(csr.iso_range_limit_survived_camera_reset)
        self.assertTrue(csr.iso_auto_min_ss_reset_to_standard)
        self.assertEqual(csr.effective_iso_auto_min_ss, p298.ISO_MIN_SS_STANDARD)
        self.assertTrue(csr.flash_comp_reset_to_zero)
        self.assertEqual(csr.flash_comp_ev, 0.0)
        self.assertTrue(csr.exp_comp_set_survived_camera_reset)
        self.assertTrue(csr.video_light_survived_camera_reset)

        ini = p298.simulate_iso_minss_flash_and_videolight_hil(
            iso_range_limit_min=200,
            iso_range_limit_max=12800,
            exp_comp_set=p298.EXP_COMP_AMBIENT_ONLY,
            video_light_mode=p298.VIDEO_LIGHT_REC_LINK,
            reset_action=p298.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(ini.admitted)
        self.assertEqual(ini.iso_range_limit_min, 100)
        self.assertEqual(ini.iso_range_limit_max, 102400)
        self.assertEqual(ini.exp_comp_set, p298.EXP_COMP_AMBIENT_AND_FLASH)
        self.assertEqual(ini.video_light_mode, p298.VIDEO_LIGHT_POWER_LINK)

    def test_65_invalid_cine_ei_base_iso_rejected_einval(self) -> None:
        for bad_base in (400, 1600, 6400, True):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(
                cine_ei_base_iso=bad_base,  # type: ignore[arg-type]
            )
            self.assertFalse(r.admitted, msg=str(bad_base))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO)

    def test_66_invalid_flash_comp_and_mishoe_numeric_params_rejected_einval(self) -> None:
        for bad in (
            {"flash_comp_ev": -3.3},
            {"flash_comp_ev": 3.3},
            {"flash_comp_ev": True},
            {"mishoe_current_ma": -1},
            {"mishoe_current_ma": True},
            {"mishoe_non_sony_sync_volts": -5},
            {"mishoe_non_sony_sync_volts": True},
        ):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO)

    def test_67_invalid_pillar_c_enum_params_rejected_einval(self) -> None:
        for bad in (
            {"body_profile": "UNKNOWN"},
            {"shooting_domain": "UNKNOWN"},
            {"pasm_mode": "SCN"},
            {"log_shooting_mode": "LogC"},
            {"iso_mode": "Extended"},
            {"iso_auto_min_ss": "1/32000"},
            {"shutter_type": "Auto"},
            {"silent_mode": "Half"},
            {"flash_mode": "Strobe"},
            {"exp_comp_set": "FlashOnly"},
            {"wireless_flash": "Maybe"},
            {"video_light_mode": "AlwaysOn"},
            {"reset_action": "Reboot"},
        ):
            r = p298.simulate_iso_minss_flash_and_videolight_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p298.EINVAL_ERRNO, msg=str(bad))

    def test_68_fx3a_body_profile_parity_with_fx3_for_pillar_c(self) -> None:
        r = p298.simulate_iso_minss_flash_and_videolight_hil(
            body_profile=p298.BODY_MODEL_FX3A,
            shooting_domain=p298.EXPOSURE_MODE_STILL,
            shutter_type=p298.SHUTTER_TYPE_MECHANICAL,
            flash_mode=p298.FLASH_MODE_REAR_SYNC,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.flash_active)

    def test_69_pillar_cd_dict_passed_and_covers_all_16_redlines(self) -> None:
        pcd = self.default_audit["pillar_c_d_iso_minss_flash_videolight_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["flash_5modes_mech_still_ok"]), 5)
        self.assertEqual(len(pcd["video_light_4modes_850ma_ok"]), 4)
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 60 (60/60 Milestone!) Suite,
    #          CI Headroom & Portability Hygiene (11 tests -> Total 80)
    # ------------------------------------------------------------------
    def test_70_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p298.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p298.probe_phase298_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p298.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p298.probe_phase298_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.still_only_tracking_exposed_in_movie_events, 0)
            self.assertEqual(blocked.af_area_reg_lock_op_parts_conflict_events, 0)
            self.assertEqual(blocked.xlr_h1_phantom_zoom_or_hold_events, 0)
            self.assertEqual(blocked.cine_ei_iso_range_or_minss_bypass_events, 0)
            self.assertEqual(blocked.flash_non_mech_or_movie_bypass_events, 0)
            self.assertEqual(blocked.mishoe_pmic_5v_900ma_overcurrent_events, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p298.probe_phase298_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p298.EINVAL_ERRNO)

    def test_71_standalone_cli_self_test_summary_json_and_help_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p298.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(
            FX3_VM_DIR / "realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py"
        )

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 298 Stage 60 (60/60 Milestone)", proc_sum.stdout)
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
        self.assertEqual(data["milestone"], "60/60")
        self.assertEqual(data["phase_number"], 298)
        self.assertTrue(data["is_60th_stage_milestone"])

        proc_help = subprocess.run(
            [sys.executable, "-B", script, "--help"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--clean-room", proc_help.stdout)

    def test_72_standalone_cli_in_process_clean_room_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p298.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 298 Stage 60 (60/60 Milestone)", buf.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf.getvalue())

    def test_73_suite_stage60_60_of_60_milestone_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s60 = rep["stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil"]
            self.assertTrue(s60["all_checks_passed"])
            self.assertEqual(s60["phase_number"], 298)
            self.assertEqual(s60["milestone"], "60/60")
            self.assertTrue(s60["is_60th_stage_milestone"])
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            self.assertGreaterEqual(len(stage_keys), 60)

    def test_74_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 15.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_75_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_76_suite_stage60_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil)
        self.assertTrue(default_cfg.include_stage60)
        self.assertTrue(
            default_cfg.include_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil
        )

        for override in (
            {"stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil": False},
            {"include_stage60": False},
            {"include_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil", rep)
            self.assertFalse(rep["config"]["include_stage60"])
            self.assertFalse(
                rep["config"]["stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil"]
            )

    def test_77_fx3_vm_coemulation_suite_include_stage60_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage60", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_focus_area_zoom_lever_iso_minss_flash_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_78_fx3_vm_coemulation_suite_cli_skip_phase298_and_skip_stage60(self) -> None:
        for skip_flag in ("--skip-phase298", "--skip-stage60", "--no-include-stage60"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0, msg=skip_flag)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"], msg=skip_flag)
            self.assertNotIn("stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil", rep)

    def test_79_suite_help_works_without_argparse_percent_errors(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                suite.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("--include-stage60", buf.getvalue())
        self.assertIn("--skip-stage60", buf.getvalue())
        self.assertIn("--skip-phase298", buf.getvalue())

    def test_80_cross_platform_ci_portability_hygiene(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py"
        ).read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")
        forbidden_bin = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden_bin, mod_src)
        self.assertNotIn(forbidden_bin, test_src)
        self.assertIn("sys.executable", test_src)
        self.assertIn("15.0 if IS_CI", test_src)


if __name__ == "__main__":
    unittest.main()
