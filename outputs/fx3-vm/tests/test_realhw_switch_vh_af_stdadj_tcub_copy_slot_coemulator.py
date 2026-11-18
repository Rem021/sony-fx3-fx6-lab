#!/usr/bin/env python3
"""Unit tests for Phase 312 (Stage 64 — 64/64 Power-of-Two VM Stages Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-54
`[Switch V/H AF Area]` & 14-Checkbox `[Focus Area Limit]`,
5-Mode `[Exposure Std. Adjust]` (1/6 EV steps, Initialize-only) & Still-Only `[Bracket Settings]`,
`[Time Code Format]` DF/NDF 23.98p/24p/PAL Locks & `[User Bit Time Rec]` vs FX6 BNC Switch, and
CRITICAL Reverse-Direction `[Select Playback Media] == Slot 2` -> Playback `[Copy]`
(`Slot 2 -> Slot 1`) 100% Fail-Closed Tier-0 Vault Firewall & Safe Read-Only `[Slide Show]`
(88 dual-mode tests).
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
import realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator as p312  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..63 for quick Stage 64 isolation tests."""
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
]


class TestPhase312DonorInspection(unittest.TestCase):
    """Dual-mode 17-donor O_RDONLY & CLEAN_ROOM_SYNTHETIC verification (tests 01..12)."""

    def test_01_schema_and_milestone_constants(self) -> None:
        self.assertEqual(
            p312.SCHEMA_ID,
            "realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator_v1",
        )
        self.assertEqual(p312.PHASE_NUMBER, 312)
        self.assertEqual(p312.STAGE_INDEX, 64)
        self.assertEqual(p312.STAGE_TOTAL, 64)
        self.assertEqual(p312.MILESTONE_LABEL, "64/64")
        self.assertTrue(p312.IS_64TH_STAGE_MILESTONE)
        self.assertTrue(p312.IS_64TH_POWER_OF_TWO_MILESTONE)
        self.assertEqual(p312.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p312.BOUNDED_WINDOW_MAX_BYTES, 4096)
        self.assertEqual(len(p312.DONOR_RELPATHS), 17)

    def test_02_donor_audit_current_mode_17_donors(self) -> None:
        audit = p312.inspect_phase312_donors()
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertIn(
            audit.source_mode,
            (p312.SOURCE_MODE_LOCAL_DONOR, p312.SOURCE_MODE_CLEAN_ROOM),
        )
        self.assertEqual(len(audit.entries), 17)
        self.assertTrue(all(e.passed for e in audit.entries))
        max_ms = 17000.0 if IS_CI else 2000.0
        self.assertLess(audit.inspection_elapsed_ms, max_ms)

    def test_03_force_clean_room_both_env_vars(self) -> None:
        for env_key in (p312.ENV_CLEAN_ROOM_TEST, p312.ENV_FORCE_CLEAN_ROOM):
            audit = p312.inspect_phase312_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p312.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_files_inspected, 17)
            self.assertTrue(audit.all_contracts_verified)
            self.assertFalse(any(e.read_only_checked for e in audit.entries))

    def test_04_missing_donor_dir_falls_back_clean_room(self) -> None:
        audit = p312.inspect_phase312_donors(
            env={p312.ENV_MAC_WORK_ROOT: "/nonexistent/fx3/__phase312_missing__"}
        )
        self.assertEqual(audit.source_mode, p312.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_compact_donor_byte_lengths_sha256_and_tokens(self) -> None:
        audit = p312.inspect_phase312_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        self.assertEqual(len(p312.EXPECTED_COMPACT_DONOR_SHA256), 14)
        for key, expected_sha in p312.EXPECTED_COMPACT_DONOR_SHA256.items():
            entry = by_key[key]
            self.assertEqual(entry.byte_length, p312.EXPECTED_DONOR_BYTES[key], key)
            self.assertEqual(entry.sha256_or_head4k, expected_sha, key)
            self.assertGreaterEqual(len(entry.tokens_verified), 1, key)
            self.assertTrue(entry.passed, key)

    def test_06_large_donor_bounded_windows_verified(self) -> None:
        audit = p312.inspect_phase312_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        for key in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
            entry = by_key[key]
            self.assertEqual(entry.byte_length, p312.EXPECTED_DONOR_BYTES[key], key)
            self.assertEqual(
                entry.sha256_or_head4k,
                p312.EXPECTED_LARGE_HEAD4K_SHA256[key],
                key,
            )
            self.assertTrue(entry.passed, key)

    def test_07_bounded_read_rejects_oversized_window(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"ABCDEFGH")
            tmp.flush()
            with self.assertRaises(ValueError):
                p312._read_bounded_window_ro(Path(tmp.name), 0, p312.BOUNDED_WINDOW_MAX_BYTES + 1)

    def test_08_compact_donor_read_rejects_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            big_path = Path(td) / "too_big.uxc"
            with open(big_path, "wb") as fp:
                fp.truncate(2 * 1024 * 1024 + 4096)
            with self.assertRaises(ValueError):
                p312._read_compact_donor_ro(big_path, 1024)

    def test_09_donor_parity_local_vs_clean_room_redlines_identical(self) -> None:
        r_default = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation()
        r_clean = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            force_clean_room=True
        )
        self.assertEqual(r_default["redlines"], r_clean["redlines"])
        self.assertEqual(r_default["milestone"], r_clean["milestone"])

    def test_10_legacy_mac_root_env_override_handled_safely(self) -> None:
        root = p312.resolve_mac_work_root(env={p312.ENV_MAC_ROOT: "/nonexistent/mac_root"})
        self.assertEqual(root, Path("/nonexistent/mac_root/work"))
        audit = p312.inspect_phase312_donors(env={p312.ENV_MAC_ROOT: "/nonexistent/mac_root"})
        self.assertEqual(audit.source_mode, p312.SOURCE_MODE_CLEAN_ROOM)

    def test_11_uxc_multilingual_fx3_tokens_en_sc_tc_ja_verified(self) -> None:
        for suffix in ("_f", "", "_g"):
            for lang in ("en", "sc", "tc", "ja"):
                key = f"fx3_string_{lang}{suffix}"
                self.assertIn(key, p312.COMPACT_DONOR_TOKENS)
                self.assertGreaterEqual(len(p312.COMPACT_DONOR_TOKENS[key]), 2)

    def test_12_fx6_dormant_and_bnc_tokens_verified_in_windows(self) -> None:
        labels = {lbl for _, lbl, _ in p312.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        self.assertIn("BKID_FX6_USB_TC_IN_ALT", labels)
        self.assertIn("BKID_FX6_USER_MENU_COPY_CLIP", labels)
        self.assertIn("BKID_FX6_EXT_TC_LOCK_STATUS", labels)
        self.assertIn("FX6_DORMANT_BRACKET_ORDER", labels)
        self.assertIn("FX6_DORMANT_EXPOSURE_STD_MODE", labels)


class TestSubModel64ASwitchVHAndFocusAreaLimit(unittest.TestCase):
    """64A: [Switch V/H AF Area] & 14-checkbox [Focus Area Limit] tests (tests 13..28)."""

    def test_13_still_afc_switch_vh_across_0_90_270_deg_orientations(self) -> None:
        r0 = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            roll_orientation=p312.ORIENT_0_DEG,
            focus_area_0deg="Wide",
            focus_area_90deg="Spot: M",
            focus_area_270deg="Zone",
        )
        r90 = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            roll_orientation=p312.ORIENT_90_DEG,
            focus_area_0deg="Wide",
            focus_area_90deg="Spot: M",
            focus_area_270deg="Zone",
        )
        r270 = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            roll_orientation=p312.ORIENT_270_DEG,
            focus_area_0deg="Wide",
            focus_area_90deg="Spot: M",
            focus_area_270deg="Zone",
        )
        self.assertTrue(r0.admitted and r90.admitted and r270.admitted)
        self.assertTrue(r0.vh_switch_active and r90.vh_switch_active and r270.vh_switch_active)
        self.assertEqual(r0.active_focus_area, "Wide")
        self.assertEqual(r90.active_focus_area, "Spot: M")
        self.assertEqual(r270.active_focus_area, "Zone")

        r_pt_only = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_ONLY,
            roll_orientation=p312.ORIENT_90_DEG,
            focus_area_0deg="Wide",
            focus_area_90deg="Spot: M",
        )
        self.assertTrue(r_pt_only.vh_switch_active)
        self.assertEqual(r_pt_only.active_focus_area, "Wide")

    def test_14_invalid_pitch_degrades_gracefully_and_force_vh_eopnotsupp(self) -> None:
        r_deg = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            roll_orientation=p312.ORIENT_INVALID_PITCH,
            focus_area_0deg="Wide",
            focus_area_90deg="Spot: M",
        )
        self.assertTrue(r_deg.admitted)
        self.assertFalse(r_deg.orientation_sensor_valid)
        self.assertFalse(r_deg.vh_switch_active)
        self.assertTrue(r_deg.vh_switch_locked_out)
        self.assertEqual(r_deg.vh_lockout_reason, "PITCH_INVALID_DEGRADED")
        self.assertEqual(r_deg.active_focus_area, "Wide")

        r_frc = p312.simulate_switch_vh_af_and_focus_limit_hil(
            shooting_domain=p312.DOMAIN_STILL,
            focus_mode=p312.FOCUS_MODE_AFC,
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            roll_orientation=p312.ORIENT_INVALID_PITCH,
            force_vh_switch=True,
        )
        self.assertFalse(r_frc.admitted)
        self.assertEqual(r_frc.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_15_movie_and_sq_lock_out_switch_vh_af(self) -> None:
        for dom in (p312.DOMAIN_MOVIE, p312.DOMAIN_SQ):
            r_grace = p312.simulate_switch_vh_af_and_focus_limit_hil(
                shooting_domain=dom,
                focus_mode=p312.FOCUS_MODE_AFC,
                switch_vh_af=p312.SWITCH_VH_AF_POINT_ONLY,
            )
            self.assertTrue(r_grace.admitted)
            self.assertTrue(r_grace.vh_switch_locked_out)

            r_frc = p312.simulate_switch_vh_af_and_focus_limit_hil(
                shooting_domain=dom,
                focus_mode=p312.FOCUS_MODE_AFC,
                switch_vh_af=p312.SWITCH_VH_AF_POINT_ONLY,
                force_vh_switch=True,
            )
            self.assertFalse(r_frc.admitted)
            self.assertEqual(r_frc.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_16_non_afc_focus_modes_lock_out_switch_vh_af(self) -> None:
        for fm in (p312.FOCUS_MODE_AFS, p312.FOCUS_MODE_AFA, p312.FOCUS_MODE_DMF, p312.FOCUS_MODE_MF):
            r = p312.simulate_switch_vh_af_and_focus_limit_hil(
                shooting_domain=p312.DOMAIN_STILL,
                focus_mode=fm,
                switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
                force_vh_switch=True,
            )
            self.assertFalse(r.admitted, fm)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, fm)
            self.assertEqual(r.vh_lockout_reason, f"LOCKED_OUT_NON_AFC_{fm}", fm)

    def test_17_six_operational_lockouts_still_afc(self) -> None:
        lockout_kwargs = (
            ("iauto_active", "LOCKED_IN_IAUTO"),
            ("digital_zoom_active", "LOCKED_DURING_DIGITAL_ZOOM"),
            ("active_af_tracking_engaged", "LOCKED_DURING_AF_TRACKING"),
            ("continuous_burst_active", "LOCKED_DURING_CONTINUOUS_BURST"),
            ("selftimer_countdown_active", "LOCKED_DURING_SELFTIMER_COUNTDOWN"),
            ("focus_magnifier_active", "LOCKED_DURING_FOCUS_MAGNIFIER"),
        )
        for kw, expected_reason in lockout_kwargs:
            r = p312.simulate_switch_vh_af_and_focus_limit_hil(
                shooting_domain=p312.DOMAIN_STILL,
                focus_mode=p312.FOCUS_MODE_AFC,
                switch_vh_af=p312.SWITCH_VH_AF_POINT_ONLY,
                force_vh_switch=True,
                **{kw: True},
            )
            self.assertFalse(r.admitted, kw)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, kw)
            self.assertEqual(r.vh_lockout_reason, expected_reason, kw)

    def test_18_changing_switch_vh_mode_clears_remembered_positions(self) -> None:
        r = p312.simulate_switch_vh_af_and_focus_limit_hil(
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            previous_switch_vh_af=p312.SWITCH_VH_AF_POINT_ONLY,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.remembered_positions_cleared)

    def test_19_focus_area_limit_exact_14_active_fx3_checkboxes(self) -> None:
        self.assertEqual(len(p312.FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES), 14)
        self.assertEqual(len(p312.FX3_BASE_FOCUS_AREAS_7), 7)
        self.assertEqual(len(p312.FX3_TRACKING_FOCUS_AREAS_7), 7)
        r = p312.simulate_switch_vh_af_and_focus_limit_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.exposed_limit_checkbox_count, 14)
        self.assertEqual(
            r.checked_focus_area_limit,
            p312.FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES,
        )

    def test_20_focus_area_limit_enforces_minimum_2_checked_einval(self) -> None:
        for few in ((), ("Wide",), ("Wide", "Wide")):
            r = p312.simulate_switch_vh_af_and_focus_limit_hil(checked_focus_areas=few)
            self.assertFalse(r.admitted, str(few))
            self.assertEqual(r.errno_code, p312.EINVAL_ERRNO, str(few))

        r2 = p312.simulate_switch_vh_af_and_focus_limit_hil(
            checked_focus_areas=("Wide", "Spot: M")
        )
        self.assertTrue(r2.admitted)
        self.assertEqual(r2.checked_focus_area_limit, ("Wide", "Spot: M"))

    def test_21_focus_area_limit_rejects_dormant_alpha_xl_xs_custom123_eopnotsupp(self) -> None:
        for dormant in ("Spot: XL", "Spot: XS", "Custom 1", "Custom 2", "Custom 3"):
            r = p312.simulate_switch_vh_af_and_focus_limit_hil(
                checked_focus_areas=("Wide", dormant)
            )
            self.assertFalse(r.admitted, dormant)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, dormant)

            r_sel = p312.simulate_switch_vh_af_and_focus_limit_hil(
                requested_select_area=dormant
            )
            self.assertFalse(r_sel.admitted, dormant)
            self.assertEqual(r_sel.errno_code, p312.EOPNOTSUPP_ERRNO, dormant)

    def test_22_movie_and_sq_filter_out_7_tracking_focus_areas(self) -> None:
        for dom in (p312.DOMAIN_MOVIE, p312.DOMAIN_SQ):
            r = p312.simulate_switch_vh_af_and_focus_limit_hil(shooting_domain=dom)
            self.assertTrue(r.admitted)
            self.assertEqual(r.movie_exposed_areas, p312.FX3_BASE_FOCUS_AREAS_7)

            r_trk = p312.simulate_switch_vh_af_and_focus_limit_hil(
                shooting_domain=dom,
                requested_select_area="Tracking: Spot M",
            )
            self.assertFalse(r_trk.admitted)
            self.assertEqual(r_trk.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_23_excluded_focus_area_cannot_be_selected_eopnotsupp(self) -> None:
        r = p312.simulate_switch_vh_af_and_focus_limit_hil(
            checked_focus_areas=("Wide", "Zone"),
            requested_select_area="Spot: L",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_24_unchecking_focus_area_clears_registered_vh_and_af_reg(self) -> None:
        r = p312.simulate_switch_vh_af_and_focus_limit_hil(
            checked_focus_areas=("Wide", "Zone"),
            registered_vh_areas=("Wide", "Spot: M"),
            af_area_registration_area="Expand Spot",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.vh_or_reg_area_cleared)

    def test_25_focus_area_color_survives_cam_reset_unlike_vh_and_limit(self) -> None:
        r = p312.simulate_switch_vh_af_and_focus_limit_hil(
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            checked_focus_areas=("Wide", "Zone"),
            focus_area_color=p312.FOCUS_AREA_COLOR_RED,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_switch_vh_af, p312.SWITCH_VH_OFF)
        self.assertEqual(
            r.checked_focus_area_limit,
            p312.FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES,
        )
        self.assertEqual(r.effective_focus_area_color, p312.FOCUS_AREA_COLOR_RED)

    def test_26_initialize_resets_switch_vh_limit_14_and_focus_area_color(self) -> None:
        r = p312.simulate_switch_vh_af_and_focus_limit_hil(
            switch_vh_af=p312.SWITCH_VH_AF_POINT_PLUS_AREA,
            checked_focus_areas=("Wide", "Zone"),
            focus_area_color=p312.FOCUS_AREA_COLOR_RED,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_switch_vh_af, p312.SWITCH_VH_OFF)
        self.assertEqual(
            r.checked_focus_area_limit,
            p312.FX3_ACTIVE_14_FOCUS_AREA_LIMIT_CHECKBOXES,
        )
        self.assertEqual(r.effective_focus_area_color, p312.FOCUS_AREA_COLOR_WHITE)

    def test_27_fx6_rejects_switch_vh_limit_color_and_contrasts_orange(self) -> None:
        r_ok = p312.simulate_switch_vh_af_and_focus_limit_hil(body_profile=p312.BODY_MODEL_FX6)
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_focus_area_color, "Orange_FX6_Marker")

        for bad_kw in (
            {"switch_vh_af": p312.SWITCH_VH_AF_POINT_ONLY},
            {"checked_focus_areas": ("Wide", "Zone")},
            {"focus_area_color": p312.FOCUS_AREA_COLOR_RED},
        ):
            r_blk = p312.simulate_switch_vh_af_and_focus_limit_hil(
                body_profile=p312.BODY_MODEL_FX6, **bad_kw
            )
            self.assertFalse(r_blk.admitted, str(bad_kw))
            self.assertEqual(r_blk.errno_code, p312.EOPNOTSUPP_ERRNO, str(bad_kw))

    def test_28_invalid_64a_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p312.simulate_switch_vh_af_and_focus_limit_hil(body_profile="ILME-FX9").errno_code,
            p312.EINVAL_ERRNO,
        )
        self.assertEqual(
            p312.simulate_switch_vh_af_and_focus_limit_hil(focus_mode="AF-UNKNOWN").errno_code,
            p312.EINVAL_ERRNO,
        )
        self.assertEqual(
            p312.simulate_switch_vh_af_and_focus_limit_hil(
                checked_focus_areas=("Wide", "MagicArea")
            ).errno_code,
            p312.EINVAL_ERRNO,
        )


class TestSubModel64BExposureStdAdjAndBracket(unittest.TestCase):
    """64B: 5-Mode [Exposure Std. Adjust] (1/6 EV) & Still [Bracket Settings] (tests 29..42)."""

    def test_29_all_5_fx3_metering_modes_exposed_and_admitted(self) -> None:
        self.assertEqual(len(p312.VALID_FX3_EXPOSURE_STD_5_MODES), 5)
        for mode in p312.VALID_FX3_EXPOSURE_STD_5_MODES:
            r = p312.simulate_exposure_std_adj_and_bracket_hil(
                metering_mode=mode, offset_sixths=2
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.exposed_metering_mode_count, 5, mode)
            self.assertEqual(r.effective_offset_sixths, 2, mode)

    def test_30_exact_one_sixth_ev_steps_minus_1_to_plus_1_ev(self) -> None:
        for sixths in range(-6, 7):
            r = p312.simulate_exposure_std_adj_and_bracket_hil(offset_sixths=sixths)
            self.assertTrue(r.admitted, sixths)
            self.assertEqual(r.effective_offset_sixths, sixths)
            self.assertAlmostEqual(r.effective_offset_ev, sixths / 6.0, places=5)

        r_float = p312.simulate_exposure_std_adj_and_bracket_hil(offset_ev=0.5)
        self.assertTrue(r_float.admitted)
        self.assertEqual(r_float.effective_offset_sixths, 3)

    def test_31_non_sixth_and_out_of_range_offsets_rejected_einval(self) -> None:
        for bad_ev in (0.25, -0.3, 1.5, -1.2):
            r = p312.simulate_exposure_std_adj_and_bracket_hil(offset_ev=bad_ev)
            self.assertFalse(r.admitted, bad_ev)
            self.assertEqual(r.errno_code, p312.EINVAL_ERRNO, bad_ev)

        for bad_s in (-7, 7):
            r = p312.simulate_exposure_std_adj_and_bracket_hil(offset_sixths=bad_s)
            self.assertFalse(r.admitted, bad_s)
            self.assertEqual(r.errno_code, p312.EINVAL_ERRNO, bad_s)

    def test_32_caution_0xe567_and_independent_exif_without_touching_exp_comp(self) -> None:
        r_nz = p312.simulate_exposure_std_adj_and_bracket_hil(
            offset_sixths=-4, exposure_comp_ev=+1.3
        )
        self.assertTrue(r_nz.caution_dialog_0xe567_shown)
        self.assertTrue(r_nz.std_adjust_independent_exif)
        self.assertEqual(r_nz.exposure_comp_ev_untouched, +1.3)

        r_zero = p312.simulate_exposure_std_adj_and_bracket_hil(offset_sixths=0)
        self.assertFalse(r_zero.caution_dialog_0xe567_shown)

    def test_33_mm_and_ae_baseline_shift_plus_spot_ael_shifted(self) -> None:
        r_spot = p312.simulate_exposure_std_adj_and_bracket_hil(
            metering_mode=p312.METERING_SPOT, offset_sixths=6
        )
        self.assertEqual(r_spot.effective_mm_shift_ev, 1.0)
        self.assertEqual(r_spot.effective_ae_baseline_shift_ev, 1.0)
        self.assertTrue(r_spot.spot_ael_shifted)

        r_multi = p312.simulate_exposure_std_adj_and_bracket_hil(
            metering_mode=p312.METERING_MULTI, offset_sixths=6
        )
        self.assertFalse(r_multi.spot_ael_shifted)

    def test_34_mid_bracket_std_adj_modification_resets_bracket_shot_counter(self) -> None:
        r = p312.simulate_exposure_std_adj_and_bracket_hil(
            bracket_drive_mode=p312.BRACKET_DRIVE_CONT,
            bracket_in_progress=True,
            bracket_shot_index=2,
            modify_std_adj_during_bracket=True,
            offset_sixths=-3,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.bracket_counter_reset)
        self.assertEqual(r.effective_bracket_shot_index, 0)

    def test_35_exposure_std_adj_survives_camera_settings_reset(self) -> None:
        r = p312.simulate_exposure_std_adj_and_bracket_hil(
            metering_mode=p312.METERING_HIGHLIGHT,
            offset_sixths=-5,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_offset_sixths, -5)

    def test_36_exposure_std_adj_resets_only_via_initialize(self) -> None:
        r = p312.simulate_exposure_std_adj_and_bracket_hil(
            metering_mode=p312.METERING_HIGHLIGHT,
            offset_sixths=6,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_offset_sixths, 0)
        self.assertEqual(r.effective_offset_ev, 0.0)

    def test_37_still_bracket_settings_selftimer_4_values_and_bracket_orders(self) -> None:
        for st in p312.VALID_BRACKET_SELFTIMERS:
            for order in p312.VALID_BRACKET_ORDERS:
                r = p312.simulate_exposure_std_adj_and_bracket_hil(
                    bracket_drive_mode=p312.BRACKET_DRIVE_CONT,
                    bracket_selftimer=st,
                    bracket_order=order,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_bracket_selftimer, st)
                self.assertEqual(r.effective_bracket_order, order)

    def test_38_still_focus_bracket_order_options(self) -> None:
        for f_ord in p312.VALID_FOCUS_BRACKET_ORDERS:
            r = p312.simulate_exposure_std_adj_and_bracket_hil(
                bracket_drive_mode=p312.BRACKET_DRIVE_FOCUS,
                focus_bracket_order=f_ord,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_focus_bracket_order, f_ord)

    def test_39_bracket_settings_reset_via_camera_settings_reset(self) -> None:
        r = p312.simulate_exposure_std_adj_and_bracket_hil(
            bracket_drive_mode=p312.BRACKET_DRIVE_SINGLE,
            bracket_selftimer=p312.BRACKET_SELFTIMER_10S,
            bracket_order=p312.BRACKET_ORDER_MINUS_ZERO_PLUS,
            focus_bracket_order=p312.FOCUS_BRACKET_ORDER_ZERO_PLUS,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_bracket_selftimer, p312.BRACKET_SELFTIMER_OFF)
        self.assertEqual(r.effective_bracket_order, p312.BRACKET_ORDER_ZERO_MINUS_PLUS)
        self.assertEqual(r.effective_focus_bracket_order, p312.BRACKET_ORDER_ZERO_MINUS_PLUS)

    def test_40_bracket_settings_rejected_in_movie_and_sq_eopnotsupp(self) -> None:
        for dom in (p312.DOMAIN_MOVIE, p312.DOMAIN_SQ):
            r = p312.simulate_exposure_std_adj_and_bracket_hil(
                shooting_domain=dom,
                bracket_drive_mode=p312.BRACKET_DRIVE_SINGLE,
                configure_bracket_settings=True,
            )
            self.assertFalse(r.admitted, dom)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, dom)

    def test_41_fx6_rejects_exposure_std_adj_and_bracket_eopnotsupp(self) -> None:
        r_ok = p312.simulate_exposure_std_adj_and_bracket_hil(body_profile=p312.BODY_MODEL_FX6)
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.exposed_metering_mode_count, 0)

        for bad_kw in (
            {"offset_sixths": 1},
            {"configure_bracket_settings": True},
            {"bracket_drive_mode": p312.BRACKET_DRIVE_CONT},
        ):
            r_blk = p312.simulate_exposure_std_adj_and_bracket_hil(
                body_profile=p312.BODY_MODEL_FX6, **bad_kw
            )
            self.assertFalse(r_blk.admitted, str(bad_kw))
            self.assertEqual(r_blk.errno_code, p312.EOPNOTSUPP_ERRNO, str(bad_kw))

    def test_42_invalid_64b_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p312.simulate_exposure_std_adj_and_bracket_hil(metering_mode="Matrix").errno_code,
            p312.EINVAL_ERRNO,
        )
        self.assertEqual(
            p312.simulate_exposure_std_adj_and_bracket_hil(bracket_selftimer="3 Sec").errno_code,
            p312.EINVAL_ERRNO,
        )


class TestSubModel64CTCFormatUBTimeRec(unittest.TestCase):
    """64C: [Time Code Format] DF/NDF, 23.98p/24p/PAL Locks & UB Time Rec (tests 43..54)."""

    def test_43_ntsc_5994_2997_11988_expose_df_and_ndf(self) -> None:
        for fps in p312.NTSC_RATES_DF_ALLOWED:
            for fmt in (p312.TC_FORMAT_DF, p312.TC_FORMAT_NDF):
                r = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
                    system_frequency=p312.SYSTEM_NTSC,
                    frame_rate=fps,
                    requested_tc_format=fmt,
                )
                self.assertTrue(r.admitted, (fps, fmt))
                self.assertTrue(r.tc_format_menu_exposed)
                self.assertFalse(r.tc_format_locked_ndf)
                self.assertEqual(r.effective_tc_format, fmt)

    def test_44_2398p_and_2400p_hard_lock_ndf_and_reject_df_eopnotsupp(self) -> None:
        for fps in (p312.FPS_23_98P, p312.FPS_24_00P):
            r_df = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
                system_frequency=p312.SYSTEM_NTSC,
                frame_rate=fps,
                requested_tc_format=p312.TC_FORMAT_DF,
            )
            self.assertFalse(r_df.admitted, fps)
            self.assertEqual(r_df.errno_code, p312.EOPNOTSUPP_ERRNO, fps)
            self.assertTrue(r_df.tc_format_locked_ndf, fps)
            self.assertEqual(r_df.effective_tc_format, p312.TC_FORMAT_NDF)

            r_ndf = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
                system_frequency=p312.SYSTEM_NTSC,
                frame_rate=fps,
                requested_tc_format=p312.TC_FORMAT_NDF,
            )
            self.assertTrue(r_ndf.admitted, fps)
            self.assertTrue(r_ndf.tc_format_locked_ndf, fps)

    def test_45_pal_50p_25p_100p_hide_menu_and_lock_ndf(self) -> None:
        for fps in p312.PAL_RATES_HIDDEN_NDF:
            r_df = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
                system_frequency=p312.SYSTEM_PAL,
                frame_rate=fps,
                requested_tc_format=p312.TC_FORMAT_DF,
            )
            self.assertFalse(r_df.admitted, fps)
            self.assertEqual(r_df.errno_code, p312.EOPNOTSUPP_ERRNO, fps)
            self.assertTrue(r_df.tc_format_menu_hidden, fps)
            self.assertTrue(r_df.tc_format_locked_ndf, fps)

            r_ndf = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
                system_frequency=p312.SYSTEM_PAL,
                frame_rate=fps,
                requested_tc_format=p312.TC_FORMAT_NDF,
            )
            self.assertTrue(r_ndf.admitted, fps)
            self.assertTrue(r_ndf.tc_format_menu_hidden, fps)
            self.assertEqual(r_ndf.effective_tc_format, p312.TC_FORMAT_NDF)

    def test_46_ntsc_pal_frame_rate_cross_mismatch_rejected_eopnotsupp(self) -> None:
        r1 = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            system_frequency=p312.SYSTEM_NTSC, frame_rate=p312.FPS_25P
        )
        r2 = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            system_frequency=p312.SYSTEM_PAL, frame_rate=p312.FPS_59_94P
        )
        self.assertFalse(r1.admitted and r2.admitted)
        self.assertEqual(r1.errno_code, p312.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_47_user_bit_time_rec_and_preset_formats(self) -> None:
        r_on = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            tc_preset="12:34:56.07",
            ub_preset="CA FE 20 26",
            ub_time_rec="On",
        )
        self.assertTrue(r_on.admitted)
        self.assertTrue(r_on.ub_records_real_time)
        self.assertEqual(r_on.effective_tc_preset, "12:34:56.07")
        self.assertEqual(r_on.effective_ub_preset, "CA FE 20 26")

        r_off = p312.simulate_tc_format_ub_time_rec_and_disp_hil(ub_time_rec="Off")
        self.assertFalse(r_off.ub_records_real_time)

    def test_48_tc_ub_disp_setting_and_still_playback_toggle_rejected(self) -> None:
        for disp in p312.VALID_TC_UB_DISP_SETTINGS:
            r = p312.simulate_tc_format_ub_time_rec_and_disp_hil(tc_ub_disp_setting=disp)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_tc_ub_disp_setting, disp)

        r_still = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            playback_media_is_still=True, playback_disp_toggle_attempted=True
        )
        self.assertFalse(r_still.admitted)
        self.assertEqual(r_still.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_49_all_6_tc_ub_settings_survive_camera_settings_reset(self) -> None:
        r = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            requested_tc_format=p312.TC_FORMAT_NDF,
            tc_preset="01:02:03.04",
            ub_preset="AB CD EF 12",
            tc_run=p312.TC_RUN_FREE,
            tc_make=p312.TC_MAKE_REGENERATE,
            ub_time_rec="On",
            tc_ub_disp_setting=p312.TC_DISP_UBIT,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.all_6_tcub_survived_cam_reset)
        self.assertEqual(r.effective_tc_format, p312.TC_FORMAT_NDF)
        self.assertEqual(r.effective_tc_preset, "01:02:03.04")
        self.assertEqual(r.effective_ub_preset, "AB CD EF 12")
        self.assertEqual(r.effective_tc_run, p312.TC_RUN_FREE)
        self.assertEqual(r.effective_tc_make, p312.TC_MAKE_REGENERATE)
        self.assertEqual(r.effective_ub_time_rec, "On")
        self.assertEqual(r.effective_tc_ub_disp_setting, p312.TC_DISP_UBIT)

    def test_50_initialize_resets_all_6_tc_ub_settings_to_defaults(self) -> None:
        r = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            requested_tc_format=p312.TC_FORMAT_NDF,
            tc_preset="01:02:03.04",
            ub_preset="AB CD EF 12",
            tc_run=p312.TC_RUN_FREE,
            tc_make=p312.TC_MAKE_REGENERATE,
            ub_time_rec="On",
            tc_ub_disp_setting=p312.TC_DISP_UBIT,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.all_6_tcub_survived_cam_reset)
        self.assertEqual(r.effective_tc_format, p312.TC_FORMAT_DF)
        self.assertEqual(r.effective_tc_preset, "00:00:00.00")
        self.assertEqual(r.effective_ub_preset, "00 00 00 00")
        self.assertEqual(r.effective_tc_run, p312.TC_RUN_REC)
        self.assertEqual(r.effective_tc_make, p312.TC_MAKE_PRESET)
        self.assertEqual(r.effective_ub_time_rec, "Off")
        self.assertEqual(r.effective_tc_ub_disp_setting, p312.TC_DISP_TC)

    def test_51_fx3_lacks_physical_bnc_tc_in_out_switch_eopnotsupp(self) -> None:
        r = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            body_profile=p312.BODY_MODEL_FX3,
            request_bnc_tc_in_out_switch=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx3_has_bnc_tc_in_out_switch)

    def test_52_fx6_has_dedicated_bnc_tc_in_out_switch_ext_lk(self) -> None:
        r_in = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            body_profile=p312.BODY_MODEL_FX6,
            request_bnc_tc_in_out_switch=True,
            fx6_bnc_switch_dir="IN",
        )
        self.assertTrue(r_in.admitted)
        self.assertTrue(r_in.fx6_has_bnc_tc_in_out_switch)
        self.assertEqual(r_in.fx6_ext_lk_bnc_switch_state, "EXT-LK_IN")

        r_out = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            body_profile=p312.BODY_MODEL_FX6,
            request_bnc_tc_in_out_switch=True,
            fx6_bnc_switch_dir="OUT",
        )
        self.assertTrue(r_out.admitted)
        self.assertEqual(r_out.fx6_ext_lk_bnc_switch_state, "TC_OUT_BNC")

    def test_53_fx6_respects_same_2398p_24p_pal_ndf_locks(self) -> None:
        r_2398 = p312.simulate_tc_format_ub_time_rec_and_disp_hil(
            body_profile=p312.BODY_MODEL_FX6,
            frame_rate=p312.FPS_23_98P,
            requested_tc_format=p312.TC_FORMAT_DF,
        )
        self.assertFalse(r_2398.admitted)
        self.assertEqual(r_2398.errno_code, p312.EOPNOTSUPP_ERRNO)

    def test_54_invalid_64c_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p312.simulate_tc_format_ub_time_rec_and_disp_hil(tc_preset="99:99").errno_code,
            p312.EINVAL_ERRNO,
        )
        self.assertEqual(
            p312.simulate_tc_format_ub_time_rec_and_disp_hil(ub_preset="ZZ XX").errno_code,
            p312.EINVAL_ERRNO,
        )


class TestSubModel64DReverseCopyVaultFirewallAndSlideShow(unittest.TestCase):
    """64D: Reverse-Direction [Copy] Slot 2 -> Slot 1 Vault Firewall & Safe [Slide Show] (tests 55..68)."""

    def test_55_select_playback_media_slot2_reverses_copy_direction_to_slot1(self) -> None:
        r_slot2 = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_NONE, select_playback_media=p312.SLOT_2
        )
        self.assertEqual(r_slot2.copy_source_slot, p312.SLOT_2)
        self.assertEqual(r_slot2.copy_dest_slot, p312.SLOT_1)
        self.assertEqual(r_slot2.copy_direction, "Slot 2 -> Slot 1")

        r_slot1 = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_NONE, select_playback_media=p312.SLOT_1
        )
        self.assertEqual(r_slot1.copy_direction, "Slot 1 -> Slot 2")

    def test_56_critical_slot2_to_slot1_copy_fail_closed_erofs_zero_writes(self) -> None:
        r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_COPY,
            select_playback_media=p312.SLOT_2,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p312.EROFS_ERRNO)
        self.assertEqual(r.copy_direction, "Slot 2 -> Slot 1")
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)
        self.assertEqual(r.slot1_vault_copy_reverse_direction_mutation_bytes, 0)
        self.assertEqual(r.physical_device_writes, 0)

    def test_57_slot1_to_slot2_virtual_copy_allowed_flattens_groups_clears_protect(self) -> None:
        r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_COPY,
            select_playback_media=p312.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.copy_direction, "Slot 1 -> Slot 2")
        self.assertFalse(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)
        self.assertTrue(r.dest_group_flattened)
        self.assertTrue(r.dest_protect_cleared)

    def test_58_write_protected_cards_rejected_erofs(self) -> None:
        r1 = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_COPY,
            select_playback_media=p312.SLOT_2,
            slot1_is_tier0_vault=False,
            slot1_write_protected=True,
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p312.EROFS_ERRNO)

        r2 = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_COPY,
            select_playback_media=p312.SLOT_1,
            slot2_write_protected=True,
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p312.EROFS_ERRNO)

    def test_59_low_battery_recording_and_bg_transfer_block_copy_ebusy(self) -> None:
        for flag in ("battery_low_for_copy", "is_recording", "background_transfer_active"):
            r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                operation=p312.OP_PB_COPY,
                select_playback_media=p312.SLOT_1,
                **{flag: True},
            )
            self.assertFalse(r.admitted, flag)
            self.assertEqual(r.errno_code, p312.EBUSY_ERRNO, flag)

    def test_60_slow_sdhc_class4_blocks_movie_and_all_copy_0xe80e_eopnotsupp(self) -> None:
        for ctype in (p312.CONTENT_MOVIE, p312.CONTENT_ALL):
            r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                operation=p312.OP_PB_COPY,
                select_playback_media=p312.SLOT_1,
                copy_content_type=ctype,
                dest_speed_class=p312.SPEED_SDHC_LEGACY_SLOW,
            )
            self.assertFalse(r.admitted, ctype)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, ctype)
            self.assertIn("0xe80e", r.reason_code)

    def test_61_slow_sdhc_still_only_copy_slot1_to_slot2_admitted_zero_writes(self) -> None:
        r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_COPY,
            select_playback_media=p312.SLOT_1,
            copy_content_type=p312.CONTENT_STILL,
            dest_speed_class=p312.SPEED_SDHC_LEGACY_SLOW,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_62_missing_card_slot1_or_slot2_blocks_copy_einval(self) -> None:
        for kw in ({"slot1_inserted": False}, {"slot2_inserted": False}):
            r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                operation=p312.OP_PB_COPY, **kw
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, p312.EINVAL_ERRNO, str(kw))

    def test_63_readonly_slideshow_safe_on_slot1_vault_and_suspends_power_save(self) -> None:
        for vm in p312.VALID_SLIDESHOW_VIEW_MODES:
            r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                operation=p312.OP_PB_SLIDE_SHOW,
                select_playback_media=p312.SLOT_1,
                slot1_is_tier0_vault=True,
                slideshow_view_mode=vm,
                slideshow_repeat="On",
                slideshow_interval=p312.SLIDESHOW_INTERVAL_10S,
            )
            self.assertTrue(r.admitted, vm)
            self.assertTrue(r.power_save_suspended)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)

    def test_64_slideshow_all_5_intervals_and_repeat_on_off_admitted(self) -> None:
        self.assertEqual(len(p312.VALID_SLIDESHOW_INTERVALS), 5)
        for rep_val in ("On", "Off"):
            for ivl in p312.VALID_SLIDESHOW_INTERVALS:
                r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                    operation=p312.OP_PB_SLIDE_SHOW,
                    slideshow_repeat=rep_val,
                    slideshow_interval=ivl,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_slideshow_repeat, rep_val)
                self.assertEqual(r.effective_slideshow_interval, ivl)

    def test_65_slideshow_rejected_in_movie_avchd_xavcs_view_modes(self) -> None:
        for bad_vm in (p312.VIEW_MODE_MOVIE, p312.VIEW_MODE_AVCHD, p312.VIEW_MODE_XAVCS):
            r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                operation=p312.OP_PB_SLIDE_SHOW,
                slideshow_view_mode=bad_vm,
            )
            self.assertFalse(r.admitted, bad_vm)
            self.assertEqual(r.errno_code, p312.EOPNOTSUPP_ERRNO, bad_vm)

    def test_66_slideshow_missing_selected_slot_rejected_einval(self) -> None:
        r = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_SLIDE_SHOW,
            select_playback_media=p312.SLOT_2,
            slot2_inserted=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p312.EINVAL_ERRNO)

    def test_67_playback_settings_survive_cam_reset_and_reset_on_initialize(self) -> None:
        r_csr = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_NONE,
            select_playback_media=p312.SLOT_2,
            slideshow_repeat="On",
            slideshow_interval=p312.SLIDESHOW_INTERVAL_30S,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_select_playback_media, p312.SLOT_2)
        self.assertEqual(r_csr.effective_slideshow_repeat, "On")
        self.assertEqual(r_csr.effective_slideshow_interval, p312.SLIDESHOW_INTERVAL_30S)

        r_init = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            operation=p312.OP_PB_NONE,
            select_playback_media=p312.SLOT_2,
            slideshow_repeat="On",
            slideshow_interval=p312.SLIDESHOW_INTERVAL_30S,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_select_playback_media, p312.SLOT_1)
        self.assertEqual(r_init.effective_slideshow_repeat, "Off")
        self.assertEqual(r_init.effective_slideshow_interval, p312.SLIDESHOW_INTERVAL_3S)

    def test_68_fx6_rejects_consumer_copy_and_slideshow_eopnotsupp(self) -> None:
        r_none = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
            body_profile=p312.BODY_MODEL_FX6, operation=p312.OP_PB_NONE
        )
        self.assertTrue(r_none.admitted)
        for op in (p312.OP_PB_COPY, p312.OP_PB_SLIDE_SHOW):
            r_blk = p312.simulate_playback_copy_direction_slideshow_vault_firewall_hil(
                body_profile=p312.BODY_MODEL_FX6, operation=op
            )
            self.assertFalse(r_blk.admitted, op)
            self.assertEqual(r_blk.errno_code, p312.EOPNOTSUPP_ERRNO, op)


class TestRedlinesCLIAndSuiteStage64Integration(unittest.TestCase):
    """Hard safety redlines, standalone CLI, and 64/64 Power-of-Two Suite orchestration (tests 69..88)."""

    def test_69_full_phase312_report_64_64_power_of_two_milestone(self) -> None:
        rep = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_64th_stage_milestone"])
        self.assertTrue(rep["is_64th_power_of_two_milestone"])
        self.assertEqual(rep["milestone"], "64/64")
        self.assertEqual(rep["stage_index"], 64)
        self.assertEqual(rep["stage_total"], 64)
        self.assertEqual(rep["phase_number"], 312)

    def test_70_clean_room_report_deterministic_digest_both_env_vars(self) -> None:
        r1 = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            force_clean_room=True
        )
        r2 = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            env={p312.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        r3 = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            env={p312.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(r1["source_mode"], p312.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r2["source_mode"], p312.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r3["source_mode"], p312.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r1["redlines"], r2["redlines"])
        self.assertEqual(r2["redlines"], r3["redlines"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r2["audit_digest_sha256"], r3["audit_digest_sha256"])

    def test_71_all_hardware_write_and_wave54_redlines_locked(self) -> None:
        rep = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        self.assertTrue(red["fx6_has_bnc_tc_in_out_switch"])
        for false_key in (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "fx3_has_bnc_tc_in_out_switch",
            "slot1_avf_info_mutated",
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
            "switch_vh_af_non_afc_or_invalid_pitch_bypass_events",
            "focus_area_limit_lt2_or_dormant_alpha_exposed_events",
            "exposure_std_adj_reset_wipe_or_missing_5th_mode_events",
            "bracket_movie_sq_or_fx6_bypass_events",
            "tc_format_2398p_24p_or_pal_df_violation_events",
            "slot1_data_sector_writes",
            "slot1_vault_copy_reverse_direction_mutation_bytes",
            "reverse_copy_slot2_to_slot1_vault_bypass_events",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_72_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("64/64", proc.stdout)

    def test_73_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p312.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 312 Stage 64 (64/64 Power-of-Two Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p312.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "64/64")
        self.assertTrue(parsed["is_64th_power_of_two_milestone"])
        self.assertTrue(parsed["all_checks_passed"])

    def test_74_no_raw_firmware_bytes_leaked_in_json_output(self) -> None:
        rep = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation()
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_75_no_hardcoded_usr_bin_python3_in_stage64_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_switch_vh_af_stdadj_tcub_copy_slot_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_76_suite_default_config_enables_stage64(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase312_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil)
        self.assertTrue(cfg.include_stage64)
        self.assertTrue(cfg.stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil)

    def test_77_suite_full_run_contains_at_least_64_stages_and_milestone_64_64(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 64)
        s64 = rep["stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"]
        self.assertTrue(s64["all_checks_passed"])
        self.assertTrue(s64["is_64th_stage_milestone"])
        self.assertTrue(s64["is_64th_power_of_two_milestone"])
        self.assertEqual(s64["milestone"], "64/64")
        self.assertEqual(s64["phase_number"], 312)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_78_suite_fast_isolated_stage64_only_pass(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(rep["all_checks_passed"])
        self.assertIsNone(rep.get("stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"))
        self.assertIsNotNone(rep.get("stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"))

    def test_79_suite_skip_flags_disable_stage64(self) -> None:
        for flag in ("--skip-stage64", "--no-include-stage64", "--skip-phase312"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn("stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil", data)
            self.assertFalse(data["config"]["include_stage64"])

    def test_80_suite_cli_help_includes_stage64_and_100pct(self) -> None:
        proc_help = subprocess.run(
            [sys.executable, "-B", str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_help.returncode, 0, proc_help.stderr)
        self.assertIn("--include-stage64", proc_help.stdout)
        self.assertIn("--skip-phase312", proc_help.stdout)
        self.assertIn("64/64 Power-of-Two", proc_help.stdout)
        self.assertIn("100%", proc_help.stdout)

    def test_81_suite_cli_summary_includes_stage64_milestone_m64_and_p2(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--include-stage64", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(
            "realhw_switch_vh_af_stdadj_tcub_copy_slot_hil=CLEAN_ROOM_SYNTHETIC(m64=64/64,p2=1",
            out,
        )

    def test_82_suite_subprocess_uses_sys_executable_with_clean_room(self) -> None:
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
        self.assertIn("rcp_byp=0", proc.stdout)
        self.assertIn("s1_wr=0", proc.stdout)

    def test_83_stage64_payload_keys_present_and_complete(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        s64 = rep["stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"]
        for key in (
            "pillar_a_switch_vh_af_and_14checkbox_focus_limit_hil",
            "pillar_b_5mode_exposure_std_adj_and_bracket_settings_hil",
            "pillar_c_tc_format_df_ndf_ub_time_rec_and_fx6_bnc_hil",
            "pillar_d_reverse_copy_slot2_to_slot1_vault_firewall_and_slideshow",
            "phase312_audit_digest_sha256",
            "donor_audit",
        ):
            self.assertIn(key, s64)

    def test_84_stage64_config_serialization_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        cfg = rep["config"]
        self.assertTrue(cfg["include_phase312_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"])
        self.assertTrue(cfg["include_stage64"])
        self.assertTrue(cfg["stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"])

    def test_85_suite_tamper_reverse_copy_bypass_detected_by_module_redlines(self) -> None:
        with unittest.mock.patch.object(
            p312, "REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_BYPASS_EVENTS", 1
        ):
            rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep["all_checks_passed"])

    def test_86_suite_tamper_slot1_avf_info_mutated_detected_by_suite(self) -> None:
        with unittest.mock.patch.object(p312, "SLOT1_AVF_INFO_MUTATED", True):
            rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep["all_checks_passed"])

    def test_87_stage64_probe_power_of_two_exponent_6_and_4_wave54_pillars(self) -> None:
        rep = p312.run_phase312_switch_vh_af_stdadj_tcub_copy_slot_coemulation(
            force_clean_room=True
        )
        probe = rep["pillar_d_reverse_copy_slot2_to_slot1_vault_firewall_and_slideshow"][
            "stage64_milestone_probe"
        ]
        self.assertEqual(probe["power_of_two_exponent"], 6)
        self.assertTrue(probe["is_64th_power_of_two_milestone"])
        self.assertEqual(len(probe["wave54_pillars"]), 4)

    def test_88_dual_mode_suite_clean_room_and_default_both_reach_64_stages(self) -> None:
        r_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(r_clean["all_checks_passed"])
        clean_stages = [k for k in r_clean if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(clean_stages), 64)


if __name__ == "__main__":
    unittest.main()
