#!/usr/bin/env python3
"""Unit tests for Phase 369 (Stage 84 — 84/84 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-74:
- 84A: `Focus -> [AF/MF]` & `[Focus Area]` 5-Item Matrix & Shared `5_RESPONSICE`
  ELF Typo (`[AF Transition Speed]` `1..7` def `5`, `[AF Subj. Shift Sens.]`
  `1..5` def `5`, `[AF Assist]` `AF-C` Movie/S&Q only w/ `SELP1650`/`SEL18200LE`
  exclusions, Reset-resistant `[Circ. of Focus Point]` single-axis non-diagonal
  wrap, Reset-resistant `[Focus Area Color]` `White`/`Red` zero dormant colors)
  vs FX6 `AF Transition Speed 1..7`, `AF Subj. Shift Sens. 1..5` (1..7 disproof),
  assignable `AF Speed/Sens.`, `PUSH AUTO`, & `Wide / Zone / Flexible Spot`,
- 84B: `Exposure/Color -> [Zebra Display]` `Custom1/2` (`Std+Range` `0..109% +-1..10%`
  vs `Lower Limit` `0..109+`), S-Log3 `41%/61%/94%` IRE Law & `Display LUT=On`
  shift, Clean-HDMI `0 px` Zebra isolation, Reset immunity, vs FX6 strictly
  single-select `Off / Zebra1 / Zebra2` (`0..109%`, `Zebra1 Aperture 2..20%`,
  zero `Both` enum),
- 84C: `Shooting -> [Marker Display]` Movie/S&Q-only 15-Aspect Matrix (`Off` +
  15 active ratios = 16 states, `Safety Zone 80%/90%`, `Guideframe`, Focus
  Magnifier auto-hide, Clean-HDMI `0 px` vs `[Grid Line Display]`, Reset immunity)
  vs FX6 `Monitoring > Marker` (7 colors, `Center Marker 1..4/Off`, `Safety Area
  80/90/92.5/95%`, `Aspect Mask 0..15` def `12`, pixel `User Box`, & `Output
  Display SDI/HDMI`),
- 84D: `Setup -> [Reset/Save Settings] -> [Save/Load Settings]` (`Slot 1`-locked
  `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, `G92` errata reconciliation, `0`
  `PRO/CAMERA` hits, Ver. 1.01 -> 2.00+ block, `MR` `EBUSY=16`, auto-reboot on
  Load, `15+` exclusions) vs `[Camera Set. Memory]` (`1..3` NVRAM + `M1..M4`
  `CAMPR%02d%c.DAT` selectable Slot 1/2 live recall) & Tier-0 `Slot 1 EROFS=30`
  Firewall vs FX6 `Project > All File` (`Media(B)` `1..64` `.ALL`, PIN excluded)
HIL (100 four-mode tests).
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
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulator as p369  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..83 for Stage 84 isolation."""
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
        include_stage67=False,
        include_stage68=False,
        include_stage69=False,
        include_stage70=False,
        include_stage71=False,
        include_stage72=False,
        include_stage73=False,
        include_stage74=False,
        include_stage75=False,
        include_stage76=False,
        include_stage77=False,
        include_stage78=False,
        include_stage79=False,
        include_stage80=False,
        include_stage81=False,
        include_stage82=False,
        include_stage83=False,
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
    "--skip-stage67",
    "--skip-stage68",
    "--skip-stage69",
    "--skip-stage70",
    "--skip-stage71",
    "--skip-stage72",
    "--skip-stage73",
    "--skip-stage74",
    "--skip-stage75",
    "--skip-stage76",
    "--skip-stage77",
    "--skip-stage78",
    "--skip-stage79",
    "--skip-stage80",
    "--skip-stage81",
    "--skip-stage82",
    "--skip-stage83",
]


class TestRealHwStage84Wave74CoEmulator(unittest.TestCase):
    # =========================================================================
    # Tests 01..15: Schema, Milestone 84/84, Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_milestone_84_of_84_and_phase_constants(self) -> None:
        self.assertEqual(
            p369.SCHEMA_ID,
            "phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation_v1",
        )
        self.assertEqual(p369.PHASE_NUMBER, 369)
        self.assertEqual(p369.STAGE_INDEX, 84)
        self.assertEqual(p369.STAGE_TOTAL, 84)
        self.assertEqual(p369.MILESTONE_LABEL, "84/84")
        self.assertTrue(p369.IS_84TH_STAGE_MILESTONE)

    def test_02_tier0_redlines_hard_locked_zero_writes_zero_leak(self) -> None:
        self.assertFalse(p369.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertTrue(p369.P8_CP_MUTATION_FORBIDDEN)
        self.assertEqual(p369.NOP_COUNT, 0)
        self.assertEqual(p369.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p369.CP_MUTATION_BYTES, 0)
        self.assertEqual(p369.WBI_MUTATION_BYTES, 0)
        self.assertEqual(p369.CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(p369.CNFLASHA_MUTATION_BYTES, 0)
        self.assertTrue(p369.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p369.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p369.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p369.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p369.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p369.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p369.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertEqual(p369.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p369.SLOT1_SECTOR_WRITES, 0)
        self.assertEqual(p369.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertFalse(p369.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p369.RF_TX_PACKETS, 0)
        self.assertEqual(p369.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_posix_errno_and_wave74_enum_contracts(self) -> None:
        self.assertEqual(p369.EROFS_ERRNO, 30)
        self.assertEqual(p369.EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(p369.EINVAL_ERRNO, 22)
        self.assertEqual(p369.EBUSY_ERRNO, 16)
        self.assertEqual(p369.EPERM_ERRNO, 1)
        self.assertEqual(p369.ENODEV_ERRNO, 19)
        self.assertEqual(p369.FX3_AF_TRANSITION_SPEED_DEFAULT, 5)
        self.assertEqual(p369.FX3_AF_SUBJ_SHIFT_SENS_DEFAULT, 5)
        self.assertIn("5_RESPONSICE", p369.SHARED_SONY_ELF_TYPO_SYMBOL)
        self.assertEqual(p369.FX3_FOCUS_AREA_COLORS, ("White", "Red"))
        self.assertEqual(len(p369.FX3_ZEBRA_LEVEL_STANDARD_OPTIONS), 10)
        self.assertEqual(p369.FX6_ZEBRA_DISPLAY_MODES, ("Off", "Zebra1", "Zebra2"))
        self.assertEqual(len(p369.FX3_MARKER_5_ITEMS), 5)
        self.assertEqual(len(p369.FX3_MARKER_15_ACTIVE_ASPECTS), 15)
        self.assertEqual(len(p369.FX6_MARKER_7_COLORS), 7)
        self.assertGreaterEqual(len(p369.FX3_CAMSET_EXCLUSIONS), 15)
        self.assertEqual(p369.FX6_ALL_FILE_MAX_SLOTS, 64)

    def test_04_donor_specs_15_compact_plus_3_window_total_18(self) -> None:
        self.assertEqual(len(p369.PHASE369_COMPACT_DONORS), 15)
        self.assertEqual(len(p369.PHASE369_WINDOW_DONORS), 3)
        names = [d.name for d in p369.PHASE369_COMPACT_DONORS] + [
            w.name for w in p369.PHASE369_WINDOW_DONORS
        ]
        self.assertEqual(len(names), 18)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("fx3_lib_saveload_settings", names)
        self.assertIn("fx3_appfw", names)
        self.assertIn("fx3_bk4", names)
        self.assertIn("fx6_appfw", names)

    def test_05_clean_room_test_env_triggers_synthetic(self) -> None:
        da = p369.inspect_phase369_wave74_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(da["compact_donors_count"], 15)
        self.assertEqual(da["window_donors_count"], 3)
        self.assertEqual(da["total_donors_count"], 18)
        self.assertTrue(da["all_donors_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_06_force_clean_room_env_triggers_synthetic(self) -> None:
        da = p369.inspect_phase369_wave74_donors(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da["forced_clean_room"])
        self.assertEqual(da["total_donors_count"], 18)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_07_mocked_donorless_work_root_none_triggers_synthetic(self) -> None:
        da = p369.inspect_phase369_wave74_donors(work_root=None)
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(da["work_root_available"])
        self.assertTrue(da["all_donors_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_08_mac_work_root_sentinel_and_nonexistent_path_synthetic(self) -> None:
        da1 = p369.inspect_phase369_wave74_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": "__fx3_fx6_clean_room_donor_disabled__"}
        )
        da2 = p369.inspect_phase369_wave74_donors(
            work_root="/nonexistent/phase369_missing_dir"
        )
        self.assertEqual(da1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da2["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da1["total_donors_count"], 18)
        self.assertEqual(da2["total_donors_count"], 18)

    def test_09_bounded_pread_rejects_oversize_over_4096_bytes(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"X" * 8192)
            p = Path(tf.name)
        try:
            with self.assertRaises(p369.Stage84Phase369Error):
                p369._read_bounded_window_o_rdonly(p, 0, 4097)
        finally:
            p.unlink(missing_ok=True)

    def test_10_compact_read_rejects_over_1mib(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"Z" * (p369._COMPACT_MAX_READ_BYTES + 1))
            p = Path(tf.name)
        try:
            with self.assertRaises(p369.Stage84Phase369Error):
                p369._read_full_compact_o_rdonly(p)
        finally:
            p.unlink(missing_ok=True)

    def test_11_o_rdonly_local_donor_verification_when_present(self) -> None:
        if IS_CI or p369.is_forced_clean_room():
            self.skipTest("Clean-room / CI mode active")
        root = p369.resolve_mac_work_root()
        if root is None or not root.exists():
            self.skipTest("Local Mac/work donors absent")
        da = p369.inspect_phase369_wave74_donors(force_clean_room=False)
        self.assertEqual(da["source_mode"], "LOCAL_O_RDONLY_REAL_DONORS")
        self.assertEqual(da["donor_access_mode"], "O_RDONLY_BOUNDED_4K_AND_COMPACT")
        self.assertEqual(da["total_donors_count"], 18)
        self.assertTrue(da["all_donors_verified"])
        for w in da["window_donors"]:
            self.assertLessEqual(w["max_pread_bytes"], 4096)

    def test_12_full_coemulation_passes_in_forced_clean_room(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["milestone"], "84/84")
        self.assertTrue(rep["is_84th_stage_milestone"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep["submodel_84a_af_speed_shift_circ_color"]["passed"])
        self.assertTrue(rep["submodel_84b_zebra_custom_slog3_fx6"]["passed"])
        self.assertTrue(rep["submodel_84c_marker_15aspect_clean_hdmi_fx6"]["passed"])
        self.assertTrue(rep["submodel_84d_saveload_camset_vs_campr_erofs"]["passed"])

    def test_13_full_coemulation_passes_with_mocked_work_root_none(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(rep["slot1_data_sector_writes"], 0)
        self.assertFalse(rep["slot1_avf_info_mutated"])
        self.assertFalse(rep["ready_for_live_camera_attach"])

    def test_14_strip_wall_clock_strips_nested_elapsed_seconds(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.123,
            "nested": [{"elapsed_seconds": 9.9, "keep": "ok"}],
        }
        cleaned = p369._strip_wall_clock(sample)
        self.assertNotIn("elapsed_seconds", cleaned)
        self.assertEqual(cleaned["nested"], [{"keep": "ok"}])

    def test_15_stage84_milestone_probe_flags(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        probe = rep["stage84_milestone_probe"]
        self.assertEqual(probe["stage_index"], 84)
        self.assertEqual(probe["stage_total"], 84)
        self.assertEqual(probe["milestone_label"], "84/84")
        self.assertTrue(probe["is_84th_stage_milestone"])
        self.assertTrue(probe["submodel_84a_passed"])
        self.assertTrue(probe["submodel_84b_passed"])
        self.assertTrue(probe["submodel_84c_passed"])
        self.assertTrue(probe["submodel_84d_passed"])
        self.assertFalse(probe["ready_for_live_camera_attach"])

    # =========================================================================
    # Tests 16..38: Sub-Model 84A — [AF Transition Speed], [AF Subj. Shift Sens.]
    #               (5_RESPONSICE!), [AF Assist], [Circ. of Focus Point],
    #               [Focus Area Color] Zero-Dormant vs FX6 AF Speed/Sens. & PUSH AUTO
    # =========================================================================

    def test_16_84a_fx3_af_transition_speed_1_to_7_movie_and_sq(self) -> None:
        for mode in ("Movie", "S&Q"):
            for spd in range(1, 8):
                r = p369.simulate_84a_af_transition_shift_circ_color(
                    operation="fx3_af_transition_speed",
                    shoot_mode=mode,
                    af_transition_speed=spd,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.errno, 0)
                self.assertEqual(r.af_transition_speed, spd)

    def test_17_84a_fx3_af_transition_speed_still_locked_eopnotsupp(self) -> None:
        r = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_af_transition_speed",
            shoot_mode="Still",
            af_transition_speed=5,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)

    def test_18_84a_fx3_af_transition_speed_out_of_range_einval(self) -> None:
        for bad in (0, 8, -1):
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_transition_speed",
                shoot_mode="Movie",
                af_transition_speed=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_19_84a_fx3_af_subj_shift_sens_1_to_5_and_5_responsice_typo(self) -> None:
        for mode in ("Movie", "S&Q"):
            for sens in range(1, 6):
                r = p369.simulate_84a_af_transition_shift_circ_color(
                    operation="fx3_af_subj_shift_sens",
                    shoot_mode=mode,
                    af_subj_shift_sensitivity=sens,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.af_subj_shift_sensitivity, sens)
                self.assertIn("5_RESPONSICE", r.shared_elf_typo_symbol)

    def test_20_84a_fx3_af_subj_shift_sens_rejects_6_7_and_still(self) -> None:
        for bad in (0, 6, 7):
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_subj_shift_sens",
                shoot_mode="Movie",
                af_subj_shift_sensitivity=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)

        r_still = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_af_subj_shift_sens",
            shoot_mode="Still",
            af_subj_shift_sensitivity=5,
        )
        self.assertFalse(r_still.allowed)
        self.assertEqual(r_still.errno, p369.EOPNOTSUPP_ERRNO)

    def test_21_84a_fx3_af_assist_movie_sq_afc_allowed(self) -> None:
        for mode in ("Movie", "S&Q"):
            for req in (False, True):
                r = p369.simulate_84a_af_transition_shift_circ_color(
                    operation="fx3_af_assist",
                    shoot_mode=mode,
                    focus_mode="AF-C",
                    lens_id="SEL2470GM2",
                    af_assist_requested=req,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.af_assist_enabled, req)

    def test_22_84a_fx3_af_assist_rejects_still_and_non_afc(self) -> None:
        r_still = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_af_assist",
            shoot_mode="Still",
            focus_mode="AF-C",
            af_assist_requested=True,
        )
        self.assertFalse(r_still.allowed)
        self.assertEqual(r_still.errno, p369.EOPNOTSUPP_ERRNO)

        for fm in ("AF-S", "DMF", "MF"):
            r_fm = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_assist",
                shoot_mode="Movie",
                focus_mode=fm,
                af_assist_requested=True,
            )
            self.assertFalse(r_fm.allowed)
            self.assertEqual(r_fm.errno, p369.EOPNOTSUPP_ERRNO)

    def test_23_84a_fx3_af_assist_incompatible_lenses_enodev(self) -> None:
        for lens in p369.FX3_AF_ASSIST_INCOMPATIBLE_LENSES:
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_assist",
                shoot_mode="Movie",
                focus_mode="AF-C",
                lens_id=lens,
                af_assist_requested=True,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.ENODEV_ERRNO)
            self.assertFalse(r.af_assist_enabled)

    def test_24_84a_fx3_circ_of_focus_point_all_modes_movable_areas(self) -> None:
        for shoot_mode in p369.VALID_SHOOT_MODES:
            for area in ("Zone", "Spot: S", "Spot: M", "Spot: L", "Tracking: Zone"):
                for circ in p369.FX3_CIRC_FOCUS_POINT_MODES:
                    r = p369.simulate_84a_af_transition_shift_circ_color(
                        operation="fx3_circ_of_focus_point",
                        shoot_mode=shoot_mode,
                        focus_area=area,
                        circ_mode=circ,
                    )
                    self.assertTrue(r.allowed)
                    self.assertTrue(r.diagonal_wrap_blocked)

    def test_25_84a_fx3_circ_rejects_fixed_area_and_diagonal_wrap(self) -> None:
        for fixed_area in ("Wide", "Center Fix"):
            r_fix = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_circ_of_focus_point",
                shoot_mode="Movie",
                focus_area=fixed_area,
                circ_mode="Circulate",
            )
            self.assertFalse(r_fix.allowed)
            self.assertEqual(r_fix.errno, p369.EOPNOTSUPP_ERRNO)

        r_diag = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_circ_of_focus_point",
            shoot_mode="Movie",
            focus_area="Spot: M",
            circ_mode="Circulate",
            diagonal_wrap_requested=True,
        )
        self.assertFalse(r_diag.allowed)
        self.assertEqual(r_diag.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_diag.diagonal_wrap_blocked)

    def test_26_84a_fx3_circ_invalid_mode_einval(self) -> None:
        r = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_circ_of_focus_point",
            circ_mode="Diagonal",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_27_84a_fx3_focus_area_color_white_red_only_zero_dormant(self) -> None:
        for col in p369.FX3_FOCUS_AREA_COLORS:
            for shoot_mode in p369.VALID_SHOOT_MODES:
                r = p369.simulate_84a_af_transition_shift_circ_color(
                    operation="fx3_focus_area_color",
                    shoot_mode=shoot_mode,
                    focus_area_color=col,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.focus_area_color, col)
                self.assertEqual(r.dormant_focus_area_color_exposed_events, 0)

    def test_28_84a_fx3_focus_area_color_rejects_dormant_yellow_green_blue(self) -> None:
        for dormant in p369.FX3_DORMANT_FOCUS_AREA_COLORS:
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_focus_area_color",
                focus_area_color=dormant,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.dormant_focus_area_color_exposed_events, 0)

    def test_29_84a_fx3_camera_settings_reset_splits_3_resettable_vs_2_immune(self) -> None:
        r_pre = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_reset_af_matrix_split",
            af_transition_speed=1,
            af_subj_shift_sensitivity=2,
            af_assist_requested=True,
            circ_mode="Circulate",
            focus_area_color="Red",
            camera_reset_triggered=False,
        )
        self.assertTrue(r_pre.allowed)
        self.assertFalse(r_pre.resettable_items_reverted)
        self.assertEqual(r_pre.af_transition_speed, 1)
        self.assertTrue(r_pre.af_assist_enabled)

        r_post = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_reset_af_matrix_split",
            af_transition_speed=1,
            af_subj_shift_sensitivity=2,
            af_assist_requested=True,
            circ_mode="Circulate",
            focus_area_color="Red",
            camera_reset_triggered=True,
        )
        self.assertTrue(r_post.allowed)
        self.assertTrue(r_post.resettable_items_reverted)
        self.assertTrue(r_post.reset_immune_items_preserved)
        self.assertEqual(r_post.af_transition_speed, 5)
        self.assertEqual(r_post.af_subj_shift_sensitivity, 5)
        self.assertFalse(r_post.af_assist_enabled)
        self.assertEqual(r_post.circ_of_focus_point, "Circulate")
        self.assertEqual(r_post.focus_area_color, "Red")

    def test_30_84a_fx6_af_speed_sens_wide_zone_flexible_spot(self) -> None:
        for area in p369.FX6_FOCUS_AREAS:
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx6_af_speed_sens_and_push_auto",
                body_model=p369.BODY_MODEL_FX6,
                focus_area=area,
                af_transition_speed=7,
                af_subj_shift_sensitivity=5,
                af_assist_requested=True,
            )
            self.assertTrue(r.allowed)
            self.assertIn("5_RESPONSICE", r.shared_elf_typo_symbol)

    def test_31_84a_fx6_disproves_1_to_7_shift_sens_rumor(self) -> None:
        for bad_sens in (6, 7):
            r = p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx6_af_speed_sens_and_push_auto",
                body_model=p369.BODY_MODEL_FX6,
                focus_area="Zone",
                af_subj_shift_sensitivity=bad_sens,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)

    def test_32_84a_fx6_rejects_fx3_only_focus_area_and_oob_speed(self) -> None:
        r_area = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx6_af_speed_sens_and_push_auto",
            body_model=p369.BODY_MODEL_FX6,
            focus_area="Spot: M",
        )
        self.assertFalse(r_area.allowed)
        self.assertEqual(r_area.errno, p369.EOPNOTSUPP_ERRNO)

        r_spd = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx6_af_speed_sens_and_push_auto",
            body_model=p369.BODY_MODEL_FX6,
            focus_area="Wide",
            af_transition_speed=8,
        )
        self.assertFalse(r_spd.allowed)
        self.assertEqual(r_spd.errno, p369.EINVAL_ERRNO)

    def test_33_84a_cross_body_operations_rejected_eopnotsupp(self) -> None:
        r1 = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_af_transition_speed",
            body_model=p369.BODY_MODEL_FX6,
        )
        r2 = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx6_af_speed_sens_and_push_auto",
            body_model=p369.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p369.EOPNOTSUPP_ERRNO)

    def test_34_84a_invalid_dispatch_raises_stage84_error(self) -> None:
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84a_af_transition_shift_circ_color(operation="unknown_op")
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_transition_speed", body_model="ILME-FX9"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_transition_speed", shoot_mode="TimeLapse"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84a_af_transition_shift_circ_color(
                operation="fx3_af_assist", focus_mode="AF-A"
            )

    def test_35_84a_zero_writes_and_zero_leak_on_all_results(self) -> None:
        r = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_af_transition_speed", af_transition_speed=6
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_36_84a_orchestrator_metrics_alignment(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        s84a = rep["submodel_84a_af_speed_shift_circ_color"]
        self.assertEqual(s84a["fx3_af_transition_speed_steps"], 7)
        self.assertEqual(s84a["fx3_af_transition_speed_default"], 5)
        self.assertEqual(s84a["fx3_af_subj_shift_sens_steps"], 5)
        self.assertEqual(s84a["fx3_af_subj_shift_sens_default"], 5)
        self.assertEqual(s84a["fx3_focus_area_colors_count"], 2)
        self.assertEqual(s84a["fx3_dormant_focus_area_colors_exposed_events"], 0)
        self.assertEqual(s84a["fx3_diagonal_focus_point_wrap_events"], 0)
        self.assertEqual(s84a["fx3_reset_immune_af_wipe_events"], 0)
        self.assertTrue(s84a["fx6_af_subj_shift_7step_rumor_disproved"])

    def test_37_84a_fx3_reset_split_defaults_invalid_circ_falls_back(self) -> None:
        r = p369.simulate_84a_af_transition_shift_circ_color(
            operation="fx3_reset_af_matrix_split",
            circ_mode="Invalid",
            focus_area_color="Yellow",
            camera_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.circ_of_focus_point, "Does Not Circulate")
        self.assertEqual(r.focus_area_color, "White")

    def test_38_84a_shared_elf_typo_symbol_exact_string(self) -> None:
        self.assertEqual(
            p369.SHARED_SONY_ELF_TYPO_SYMBOL,
            "VAL_setting_movie_af_subj_shift_sens_MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE",
        )

    # =========================================================================
    # Tests 39..58: Sub-Model 84B — [Zebra Display] Custom1/2, S-Log3 41/61/94%
    #               IRE Law, Clean-HDMI 0 px vs FX6 Single-Select Off/Zebra1/Zebra2
    # =========================================================================

    def test_39_84b_fx3_zebra_all_10_levels_across_all_modes(self) -> None:
        for mode in p369.VALID_SHOOT_MODES:
            for lvl in p369.FX3_ZEBRA_LEVEL_STANDARD_OPTIONS:
                r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                    operation="fx3_zebra_standard_and_custom12",
                    shoot_mode=mode,
                    zebra_level_mode=lvl,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.zebra_level_mode, lvl)

    def test_40_84b_fx3_custom1_std_range_bounds(self) -> None:
        for std in (0, 41, 109):
            for rng in (1, 5, 10):
                r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                    operation="fx3_zebra_standard_and_custom12",
                    zebra_level_mode="Custom1",
                    custom_type="Std+Range",
                    custom_std_ire=std,
                    custom_range_pct=rng,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.custom_type, "Std+Range")

    def test_41_84b_fx3_custom2_lower_limit_bounds(self) -> None:
        for lower in (0, 94, 109):
            r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx3_zebra_standard_and_custom12",
                zebra_level_mode="Custom2",
                custom_type="Lower Limit",
                custom_lower_limit_ire=lower,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.custom_type, "Lower Limit")
            self.assertEqual(r.custom_lower_limit_ire, lower)

    def test_42_84b_fx3_zebra_oob_ire_and_range_einval(self) -> None:
        for kw in (
            {"custom_std_ire": -1},
            {"custom_std_ire": 110},
            {"custom_range_pct": 0},
            {"custom_range_pct": 11},
            {"custom_lower_limit_ire": -1},
            {"custom_lower_limit_ire": 110},
        ):
            r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx3_zebra_standard_and_custom12",
                zebra_level_mode="Custom1",
                **kw,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_43_84b_fx3_zebra_invalid_level_or_custom_type_einval(self) -> None:
        r_lvl = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_standard_and_custom12",
            zebra_level_mode="Custom3",
        )
        r_ct = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_standard_and_custom12",
            zebra_level_mode="Custom1",
            custom_type="Both",
        )
        self.assertEqual(r_lvl.errno, p369.EINVAL_ERRNO)
        self.assertEqual(r_ct.errno, p369.EINVAL_ERRNO)

    def test_44_84b_fx3_slog3_ire_landmarks_and_display_lut_shift(self) -> None:
        r_native = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_slog3_ire_and_lut_shift",
            display_lut_on=False,
        )
        self.assertTrue(r_native.allowed)
        self.assertEqual(r_native.slog3_18pct_grey_ire, 41)
        self.assertEqual(r_native.slog3_90pct_white_ire, 61)
        self.assertEqual(r_native.slog3_clip_ire, 94)
        self.assertEqual(r_native.effective_display_grey_ire, 41)

        r_lut = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_slog3_ire_and_lut_shift",
            display_lut_on=True,
        )
        self.assertTrue(r_lut.allowed)
        self.assertEqual(r_lut.effective_display_grey_ire, 48)

    def test_45_84b_fx3_hdmi_zebra_zero_pixels_even_with_hdmi_info_on(self) -> None:
        for info_on in (True, False):
            r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx3_zebra_hdmi_clean_feed",
                zebra_display=True,
                hdmi_info_display_on=info_on,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.hdmi_zebra_leaked_pixels, 0)

    def test_46_84b_fx3_zebra_reset_immunity_preserved(self) -> None:
        r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_reset_immunity",
            zebra_display=True,
            zebra_level_mode="Custom1",
            camera_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.reset_immune_preserved)
        self.assertTrue(r.zebra_display_enabled)
        self.assertEqual(r.zebra_level_mode, "Custom1")

    def test_47_84b_fx6_zebra_single_select_off_zebra1_zebra2_0_to_109(self) -> None:
        for zmode in p369.FX6_ZEBRA_DISPLAY_MODES:
            for ire in (0, 70, 109):
                r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                    operation="fx6_zebra_single_select_and_aperture",
                    body_model=p369.BODY_MODEL_FX6,
                    fx6_zebra_mode=zmode,
                    custom_std_ire=ire,
                    custom_lower_limit_ire=ire,
                    fx6_zebra1_aperture_pct=10,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.fx6_zebra_mode, zmode)
                self.assertEqual(r.fx6_zebra_both_exposed_events, 0)
                self.assertEqual(r.zebra_display_enabled, zmode != "Off")

    def test_48_84b_fx6_zebra_rejects_simultaneous_both_eopnotsupp(self) -> None:
        r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX6,
            fx6_zebra_mode="Both",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.fx6_zebra_both_exposed_events, 0)

    def test_49_84b_fx6_zebra1_aperture_2_to_20_and_bounds(self) -> None:
        for ap in (2, 10, 20):
            r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx6_zebra_single_select_and_aperture",
                body_model=p369.BODY_MODEL_FX6,
                fx6_zebra_mode="Zebra1",
                fx6_zebra1_aperture_pct=ap,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_zebra1_aperture_pct, ap)

        for bad_ap in (1, 21):
            r_bad = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx6_zebra_single_select_and_aperture",
                body_model=p369.BODY_MODEL_FX6,
                fx6_zebra_mode="Zebra1",
                fx6_zebra1_aperture_pct=bad_ap,
            )
            self.assertFalse(r_bad.allowed)
            self.assertEqual(r_bad.errno, p369.EINVAL_ERRNO)

    def test_50_84b_fx6_zebra_oob_ire_einval(self) -> None:
        for bad in (-1, 110):
            r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx6_zebra_single_select_and_aperture",
                body_model=p369.BODY_MODEL_FX6,
                fx6_zebra_mode="Zebra2",
                custom_lower_limit_ire=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_51_84b_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_standard_and_custom12",
            body_model=p369.BODY_MODEL_FX6,
        )
        r2 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p369.EOPNOTSUPP_ERRNO)

    def test_52_84b_invalid_dispatch_raises_stage84_error(self) -> None:
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="bad_84b"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx3_zebra_hdmi_clean_feed", body_model="FX30"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
                operation="fx3_zebra_hdmi_clean_feed", shoot_mode="RAW"
            )

    def test_53_84b_slog3_skin_band_constants(self) -> None:
        self.assertEqual(p369.FX3_SLOG3_GREY_18_IRE, 41)
        self.assertEqual(p369.FX3_SLOG3_SKIN_LOW_IRE, 48)
        self.assertEqual(p369.FX3_SLOG3_SKIN_HIGH_IRE, 60)
        self.assertEqual(p369.FX3_SLOG3_WHITE_90_IRE, 61)
        self.assertEqual(p369.FX3_SLOG3_CLIP_IRE, 94)

    def test_54_84b_fx6_zebra_disproves_50_to_107_rumor_at_0_and_109(self) -> None:
        r0 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX6,
            fx6_zebra_mode="Zebra1",
            custom_std_ire=0,
        )
        r109 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX6,
            fx6_zebra_mode="Zebra2",
            custom_lower_limit_ire=109,
        )
        self.assertTrue(r0.allowed)
        self.assertTrue(r109.allowed)

    def test_55_84b_fx3_zebra_off_still_zero_hdmi_leak(self) -> None:
        r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_standard_and_custom12",
            zebra_display=False,
            hdmi_info_display_on=True,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.zebra_display_enabled)
        self.assertEqual(r.hdmi_zebra_leaked_pixels, 0)

    def test_56_84b_fx6_zebra_custom_type_label_split(self) -> None:
        r1 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX6,
            fx6_zebra_mode="Zebra1",
        )
        r2 = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx6_zebra_single_select_and_aperture",
            body_model=p369.BODY_MODEL_FX6,
            fx6_zebra_mode="Zebra2",
        )
        self.assertEqual(r1.custom_type, "Zebra1 Aperture")
        self.assertEqual(r2.custom_type, "Zebra2 Level")

    def test_57_84b_orchestrator_metrics_alignment(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        s84b = rep["submodel_84b_zebra_custom_slog3_fx6"]
        self.assertEqual(s84b["fx3_zebra_level_options_count"], 10)
        self.assertEqual(s84b["fx3_zebra_ire_range"], [0, 109])
        self.assertEqual(s84b["fx3_hdmi_zebra_leaked_pixels"], 0)
        self.assertEqual(s84b["fx3_zebra_reset_wipe_events"], 0)
        self.assertEqual(s84b["fx6_zebra_display_modes_count"], 3)
        self.assertEqual(s84b["fx6_zebra_simultaneous_both_exposed_events"], 0)

    def test_58_84b_zero_writes_and_zero_leak(self) -> None:
        r = p369.simulate_84b_zebra_custom_slog3_and_fx6_single_select(
            operation="fx3_zebra_standard_and_custom12"
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    # =========================================================================
    # Tests 59..76: Sub-Model 84C — [Marker Display] 15-Aspect Matrix,
    #               Clean-HDMI 0 px Iron Law vs FX6 Aspect Mask 0..15 & User Box
    # =========================================================================

    def test_59_84c_fx3_marker_all_15_active_aspects_plus_off(self) -> None:
        aspects = ("Off",) + p369.FX3_MARKER_15_ACTIVE_ASPECTS
        self.assertEqual(len(aspects), 16)
        for mode in ("Movie", "S&Q"):
            for asp in aspects:
                r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                    operation="fx3_marker_15aspect_matrix",
                    shoot_mode=mode,
                    aspect_marker=asp,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.aspect_marker, asp)
                self.assertEqual(r.hdmi_marker_leaked_pixels, 0)

    def test_60_84c_fx3_marker_still_mode_locked_eopnotsupp(self) -> None:
        r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_15aspect_matrix",
            shoot_mode="Still",
            aspect_marker="16:9",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.markers_visible_on_lcd)

    def test_61_84c_fx3_marker_invalid_aspect_einval(self) -> None:
        for bad in ("2.40:1", "21:9", "Custom"):
            r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx3_marker_15aspect_matrix",
                shoot_mode="Movie",
                aspect_marker=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_62_84c_fx3_safety_zone_off_80_90_only_rejects_925_95(self) -> None:
        for ok_sz in p369.FX3_SAFETY_ZONE_MODES:
            r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx3_marker_15aspect_matrix",
                shoot_mode="Movie",
                safety_zone=ok_sz,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.safety_zone, ok_sz)

        for fx6_only_sz in ("92.5%", "95%"):
            r_bad = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx3_marker_15aspect_matrix",
                shoot_mode="Movie",
                safety_zone=fx6_only_sz,
            )
            self.assertFalse(r_bad.allowed)
            self.assertEqual(r_bad.errno, p369.EOPNOTSUPP_ERRNO)

    def test_63_84c_fx3_focus_magnifier_auto_hides_markers(self) -> None:
        r_hidden = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_clean_hdmi_and_focusmag",
            shoot_mode="Movie",
            marker_display=True,
            focus_mag_active=True,
            hdmi_info_display_on=True,
        )
        self.assertTrue(r_hidden.allowed)
        self.assertTrue(r_hidden.marker_display_enabled)
        self.assertFalse(r_hidden.markers_visible_on_lcd)
        self.assertEqual(r_hidden.hdmi_marker_leaked_pixels, 0)

        r_vis = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_clean_hdmi_and_focusmag",
            shoot_mode="Movie",
            marker_display=True,
            focus_mag_active=False,
            hdmi_info_display_on=True,
        )
        self.assertTrue(r_vis.allowed)
        self.assertTrue(r_vis.markers_visible_on_lcd)
        self.assertEqual(r_vis.hdmi_marker_leaked_pixels, 0)

    def test_64_84c_fx3_clean_hdmi_zero_pixels_even_with_guideframe_on(self) -> None:
        r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_clean_hdmi_and_focusmag",
            shoot_mode="S&Q",
            marker_display=True,
            center_marker=True,
            aspect_marker="9:16",
            safety_zone="80%",
            guideframe=True,
            hdmi_info_display_on=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.guideframe_enabled)
        self.assertEqual(r.hdmi_marker_leaked_pixels, 0)

    def test_65_84c_fx3_marker_reset_immunity_preserved(self) -> None:
        r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_reset_immunity",
            shoot_mode="Movie",
            aspect_marker="1.85:1",
            camera_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.reset_immune_preserved)
        self.assertEqual(r.aspect_marker, "1.85:1")

    def test_66_84c_fx6_aspect_mask_0_to_15_bounds(self) -> None:
        for mask in (0, 12, 15):
            r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx6_marker_aspect_mask_and_user_box",
                body_model=p369.BODY_MODEL_FX6,
                fx6_aspect_mask=mask,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_aspect_mask, mask)

        for bad_mask in (-1, 16):
            r_bad = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx6_marker_aspect_mask_and_user_box",
                body_model=p369.BODY_MODEL_FX6,
                fx6_aspect_mask=bad_mask,
            )
            self.assertFalse(r_bad.allowed)
            self.assertEqual(r_bad.errno, p369.EINVAL_ERRNO)

    def test_67_84c_fx6_user_box_pixel_bounds_and_oob_einval(self) -> None:
        r_min = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx6_marker_aspect_mask_and_user_box",
            body_model=p369.BODY_MODEL_FX6,
            fx6_user_box_width=3,
            fx6_user_box_height=3,
            fx6_user_box_h_pos=-476,
            fx6_user_box_v_pos=-266,
        )
        r_max = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx6_marker_aspect_mask_and_user_box",
            body_model=p369.BODY_MODEL_FX6,
            fx6_user_box_width=479,
            fx6_user_box_height=269,
            fx6_user_box_h_pos=476,
            fx6_user_box_v_pos=266,
        )
        self.assertTrue(r_min.allowed)
        self.assertTrue(r_max.allowed)

        for oob_kw in (
            {"fx6_user_box_width": 2},
            {"fx6_user_box_width": 480},
            {"fx6_user_box_height": 2},
            {"fx6_user_box_height": 270},
            {"fx6_user_box_h_pos": -477},
            {"fx6_user_box_h_pos": 477},
            {"fx6_user_box_v_pos": -267},
            {"fx6_user_box_v_pos": 267},
        ):
            r_oob = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx6_marker_aspect_mask_and_user_box",
                body_model=p369.BODY_MODEL_FX6,
                **oob_kw,
            )
            self.assertFalse(r_oob.allowed)
            self.assertEqual(r_oob.errno, p369.EINVAL_ERRNO)

    def test_68_84c_fx6_safety_area_includes_925_and_95(self) -> None:
        for sz in p369.FX6_SAFETY_AREA_MODES:
            r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx6_marker_aspect_mask_and_user_box",
                body_model=p369.BODY_MODEL_FX6,
                safety_zone=sz,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.safety_zone, sz)

        r_bad = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx6_marker_aspect_mask_and_user_box",
            body_model=p369.BODY_MODEL_FX6,
            safety_zone="75%",
        )
        self.assertFalse(r_bad.allowed)
        self.assertEqual(r_bad.errno, p369.EINVAL_ERRNO)

    def test_69_84c_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_15aspect_matrix",
            body_model=p369.BODY_MODEL_FX6,
        )
        r2 = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx6_marker_aspect_mask_and_user_box",
            body_model=p369.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p369.EOPNOTSUPP_ERRNO)

    def test_70_84c_invalid_dispatch_raises_stage84_error(self) -> None:
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(operation="bad_84c")
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx3_marker_15aspect_matrix", body_model="FX9"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
                operation="fx3_marker_15aspect_matrix", shoot_mode="Playback"
            )

    def test_71_84c_fx3_aspect_list_contains_vertical_tv_and_cinema(self) -> None:
        for expected in ("9:16", "4:5", "1:1", "16:9", "1.85:1", "2.35:1", "2.39:1"):
            self.assertIn(expected, p369.FX3_MARKER_15_ACTIVE_ASPECTS)

    def test_72_84c_fx3_marker_display_off_hides_lcd_markers(self) -> None:
        r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_15aspect_matrix",
            shoot_mode="Movie",
            marker_display=False,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.markers_visible_on_lcd)
        self.assertEqual(r.hdmi_marker_leaked_pixels, 0)

    def test_73_84c_fx6_aspect_mask_default_is_12(self) -> None:
        self.assertEqual(p369.FX6_ASPECT_MASK_DEFAULT, 12)
        self.assertEqual(p369.FX6_ASPECT_MASK_MIN, 0)
        self.assertEqual(p369.FX6_ASPECT_MASK_MAX, 15)

    def test_74_84c_fx3_5_items_list_completeness(self) -> None:
        self.assertEqual(
            p369.FX3_MARKER_5_ITEMS,
            (
                "[Marker Display]",
                "[Center Marker]",
                "[Aspect Marker]",
                "[Safety Zone]",
                "[Guideframe]",
            ),
        )

    def test_75_84c_orchestrator_metrics_alignment(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        s84c = rep["submodel_84c_marker_15aspect_clean_hdmi_fx6"]
        self.assertEqual(s84c["fx3_marker_5_items_count"], 5)
        self.assertEqual(s84c["fx3_marker_active_aspect_ratios_count"], 15)
        self.assertEqual(s84c["fx3_marker_aspect_total_states"], 16)
        self.assertEqual(s84c["fx3_hdmi_marker_leaked_pixels"], 0)
        self.assertEqual(s84c["fx3_marker_reset_wipe_events"], 0)
        self.assertEqual(s84c["fx6_marker_colors_count"], 7)
        self.assertEqual(s84c["fx6_aspect_mask_max"], 15)

    def test_76_84c_zero_writes_and_zero_leak(self) -> None:
        r = p369.simulate_84c_marker_15aspect_clean_hdmi_and_fx6(
            operation="fx3_marker_15aspect_matrix"
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    # =========================================================================
    # Tests 77..95: Sub-Model 84D — [Save/Load Settings] Slot 1 CAMSET*.DAT
    #               (G92 Errata Reconciliation!) vs [Camera Set. Memory]
    #               CAMPR*.DAT & Tier-0 Slot 1 EROFS=30 Firewall vs FX6 All File
    # =========================================================================

    def test_77_84d_saveload_menu_path_and_slot1_locked_reconciles_g92(self) -> None:
        self.assertEqual(
            p369.FX3_SAVELOAD_MENU_PATH,
            "Setup -> [Reset/Save Settings] -> [Save/Load Settings]",
        )
        r_slot2 = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Slot 2",
            action="Load",
        )
        self.assertFalse(r_slot2.allowed)
        self.assertEqual(r_slot2.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_slot2.camset_slot1_locked)
        self.assertEqual(r_slot2.fx3_pro_camera_path_hits, 0)

    def test_78_84d_saveload_sd_vs_cfexpress_and_cloud_paths(self) -> None:
        r_sd = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Slot 1",
            card_type="SD",
            action="Load",
            slot_index=1,
        )
        self.assertTrue(r_sd.allowed)
        self.assertEqual(
            r_sd.resolved_file_path,
            "1:/PRIVATE/SONY/SETTING/ILME-FX3/CAMSET/CAMSET01.DAT",
        )
        self.assertTrue(r_sd.auto_reboot_required)
        self.assertEqual(r_sd.fx3_pro_camera_path_hits, 0)

        r_cf = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Slot 1",
            card_type="CFexpress",
            action="Load",
            slot_index=10,
        )
        self.assertTrue(r_cf.allowed)
        self.assertEqual(
            r_cf.resolved_file_path,
            "1:/SONY/SETTING/ILME-FX3/CAMSET/CAMSET10.DAT",
        )

        for cloud in ("Cloud(Private)", "Cloud(Share)"):
            r_cl = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit",
                media_slot=cloud,
                action="Load",
                slot_index=60,
            )
            self.assertTrue(r_cl.allowed)
            self.assertEqual(r_cl.resolved_file_path, f"{cloud}/CAMSET60.DAT")

    def test_79_84d_saveload_slot_bounds_einval(self) -> None:
        for bad_slot in (0, 11):
            r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit",
                media_slot="Slot 1",
                action="Load",
                slot_index=bad_slot,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

        r_cloud_oob = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Cloud(Private)",
            action="Load",
            slot_index=61,
        )
        self.assertFalse(r_cloud_oob.allowed)
        self.assertEqual(r_cloud_oob.errno, p369.EINVAL_ERRNO)

    def test_80_84d_saveload_blocks_v101_to_v200_plus_and_mr_mode(self) -> None:
        for target_fw in (p369.FW_VER_200, p369.FW_VER_500, p369.FW_VER_702):
            r_v = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit",
                media_slot="Slot 1",
                action="Load",
                source_fw_version=p369.FW_VER_101,
                fw_version=target_fw,
            )
            self.assertFalse(r_v.allowed)
            self.assertEqual(r_v.errno, p369.EINVAL_ERRNO)

        r_mr = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Slot 1",
            action="Load",
            in_mr_mode=True,
        )
        self.assertFalse(r_mr.allowed)
        self.assertEqual(r_mr.errno, p369.EBUSY_ERRNO)

    def test_81_84d_saveload_exclusions_count_and_contents(self) -> None:
        self.assertGreaterEqual(len(p369.FX3_CAMSET_EXCLUSIONS), 15)
        joined = " | ".join(p369.FX3_CAMSET_EXCLUSIONS)
        for must_have in (
            "FTPSET",
            "White Balance: Custom 1..3",
            "Face Memory",
            "IPTC",
            "Copyright",
            ".cube",
        ):
            self.assertIn(must_have, joined)

    def test_82_84d_tier0_slot1_erofs_30_blocks_camset_save_and_delete(self) -> None:
        for op in ("fx3_saveload_camset_slot1_audit", "fx3_tier0_slot1_erofs_firewall"):
            for act in ("Save", "Delete"):
                r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                    operation=op,
                    media_slot="Slot 1",
                    action=act,
                    slot_index=1,
                )
                self.assertFalse(r.allowed)
                self.assertEqual(r.errno, p369.EROFS_ERRNO)
                self.assertTrue(r.tier0_erofs_enforced)
                self.assertEqual(r.slot1_data_sector_writes, 0)
                self.assertEqual(r.emmc_nflasha_write_count, 0)
                self.assertFalse(r.slot1_avf_info_mutated)

    def test_83_84d_camera_set_memory_nvram_1_to_3_and_card_m1_to_m4(self) -> None:
        for slot in p369.FX3_CAMERA_SET_MEMORY_NVRAM_SLOTS:
            r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_camera_set_memory_campr_audit",
                media_slot="RAM",
                action="Recall",
                ram_slot_code=slot,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.resolved_file_path, f"NVRAM:MR_{slot}")
            self.assertFalse(r.auto_reboot_required)
            self.assertTrue(r.camera_set_memory_recall_active)

        for mslot in p369.FX3_CAMERA_SET_MEMORY_CARD_SLOTS:
            r_sd = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_camera_set_memory_campr_audit",
                media_slot="Slot 2",
                card_type="SD",
                action="Save",
                ram_slot_code=mslot,
            )
            self.assertTrue(r_sd.allowed)
            self.assertIn(f"CAMPR0{mslot[1:]}S.DAT", r_sd.resolved_file_path)

            r_cf = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_camera_set_memory_campr_audit",
                media_slot="Slot 2",
                card_type="CFexpress",
                action="Save",
                ram_slot_code=mslot,
            )
            self.assertTrue(r_cf.allowed)
            self.assertIn(f"CAMPR0{mslot[1:]}C.DAT", r_cf.resolved_file_path)

    def test_84_84d_camera_set_memory_slot1_save_delete_blocked_erofs_30(self) -> None:
        for act in ("Save", "Delete"):
            r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_camera_set_memory_campr_audit",
                media_slot="Slot 1",
                action=act,
                ram_slot_code="M1",
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EROFS_ERRNO)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_85_84d_camera_set_memory_slot1_load_recall_allowed_and_no_reboot(self) -> None:
        r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_camera_set_memory_campr_audit",
            media_slot="Slot 1",
            action="Recall",
            ram_slot_code="M2",
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.auto_reboot_required)
        self.assertTrue(r.camera_set_memory_recall_active)

    def test_86_84d_camera_set_memory_invalid_slot_code_einval(self) -> None:
        for bad in ("0", "4", "M0", "M5"):
            r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_camera_set_memory_campr_audit",
                media_slot="Slot 2",
                action="Recall",
                ram_slot_code=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p369.EINVAL_ERRNO)

    def test_87_84d_fx6_all_file_mediab_1_to_64_and_pin_exclusion(self) -> None:
        for idx in (1, 32, 64):
            r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx6_all_file_mediab_and_pin_exclusion",
                body_model=p369.BODY_MODEL_FX6,
                media_slot="Media(B)",
                action="Save",
                slot_index=idx,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(
                r.resolved_file_path, f"B:/SONY/PRO/CAMERA/ILME-FX6/FX6_{idx:02d}.ALL"
            )
            self.assertTrue(r.fx6_user_menu_lock_pin_excluded)

        r_load = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx6_all_file_mediab_and_pin_exclusion",
            body_model=p369.BODY_MODEL_FX6,
            media_slot="Media(B)",
            action="Load",
            slot_index=1,
        )
        self.assertTrue(r_load.allowed)
        self.assertTrue(r_load.auto_reboot_required)

    def test_88_84d_fx6_all_file_rejects_media_a_oob_and_pin_inclusion(self) -> None:
        r_ma = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx6_all_file_mediab_and_pin_exclusion",
            body_model=p369.BODY_MODEL_FX6,
            media_slot="Media(A)",
            action="Save",
        )
        self.assertFalse(r_ma.allowed)
        self.assertEqual(r_ma.errno, p369.EOPNOTSUPP_ERRNO)

        r_oob = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx6_all_file_mediab_and_pin_exclusion",
            body_model=p369.BODY_MODEL_FX6,
            media_slot="Media(B)",
            slot_index=65,
        )
        self.assertFalse(r_oob.allowed)
        self.assertEqual(r_oob.errno, p369.EINVAL_ERRNO)

        r_pin = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx6_all_file_mediab_and_pin_exclusion",
            body_model=p369.BODY_MODEL_FX6,
            media_slot="Media(B)",
            user_menu_pin_included=True,
        )
        self.assertFalse(r_pin.allowed)
        self.assertEqual(r_pin.errno, p369.EPERM_ERRNO)

    def test_89_84d_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            body_model=p369.BODY_MODEL_FX6,
        )
        r2 = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx6_all_file_mediab_and_pin_exclusion",
            body_model=p369.BODY_MODEL_FX3,
            media_slot="Media(B)",
        )
        self.assertEqual(r1.errno, p369.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p369.EOPNOTSUPP_ERRNO)

    def test_90_84d_invalid_dispatch_raises_stage84_error(self) -> None:
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84d_saveload_camset_vs_campr_and_erofs(operation="bad_84d")
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit", body_model="A7S3"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit", media_slot="Slot 3"
            )
        with self.assertRaises(p369.Stage84Phase369Error):
            p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
                operation="fx3_saveload_camset_slot1_audit", fw_version="9.99"
            )

    def test_91_84d_path_templates_exact_strings(self) -> None:
        self.assertEqual(
            p369.FX3_CAMSET_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
        )
        self.assertEqual(
            p369.FX3_CAMPR_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
        )
        self.assertEqual(
            p369.FX6_ALL_FILE_PATH_TEMPLATE, "%c:%s/SONY/PRO/CAMERA/%s/%s.ALL"
        )
        self.assertEqual(
            p369.FX6_SCENE_FILE_PATH_TEMPLATE, "%c:%s/SONY/PRO/SCENE/%s.SCN"
        )

    def test_92_84d_camera_set_memory_exclusions_present(self) -> None:
        self.assertIn("Program Shift", p369.FX3_CAMERA_SET_MEMORY_EXCLUSIONS)
        self.assertIn("Custom Key/Dial Set.", p369.FX3_CAMERA_SET_MEMORY_EXCLUSIONS)

    def test_93_84d_cloud_save_allowed_with_zero_slot1_writes(self) -> None:
        r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_saveload_camset_slot1_audit",
            media_slot="Cloud(Share)",
            action="Save",
            slot_index=5,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.auto_reboot_required)

    def test_94_84d_orchestrator_metrics_alignment(self) -> None:
        rep = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        s84d = rep["submodel_84d_saveload_camset_vs_campr_erofs"]
        self.assertTrue(s84d["g92_errata_reconciled"])
        self.assertTrue(s84d["fx3_saveload_slot1_locked"])
        self.assertEqual(s84d["fx3_pro_camera_path_hits"], 0)
        self.assertEqual(s84d["fx3_saveload_card_max_slots"], 10)
        self.assertEqual(s84d["fx3_saveload_cloud_max_slots"], 60)
        self.assertGreaterEqual(s84d["fx3_saveload_exclusions_count"], 15)
        self.assertEqual(s84d["fx3_campr_nvram_slots_count"], 3)
        self.assertEqual(s84d["fx3_campr_card_slots_count"], 4)
        self.assertEqual(s84d["fx3_slot1_erofs_bypass_events"], 0)
        self.assertEqual(s84d["fx6_all_file_max_slots"], 64)
        self.assertEqual(s84d["fx6_user_menu_lock_pin_leaked_events"], 0)

    def test_95_84d_zero_writes_and_zero_leak(self) -> None:
        r = p369.simulate_84d_saveload_camset_vs_campr_and_erofs(
            operation="fx3_tier0_slot1_erofs_firewall",
            media_slot="Slot 1",
            action="Save",
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    # =========================================================================
    # Tests 96..100: 4-Mode Determinism, Digest Distinction, CLI, Portability
    #                & Suite 84/84 Integration
    # =========================================================================

    def test_96_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            force_clean_room=True
        )
        r_f2 = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(
            r_f1["phase369_audit_digest_sha256"],
            r_f2["phase369_audit_digest_sha256"],
        )
        self.assertEqual(
            r_f1["phase369_audit_digest_sha256"],
            r_f3["phase369_audit_digest_sha256"],
        )
        self.assertRegex(r_f1["phase369_audit_digest_sha256"], r"^[0-9a-f]{64}$")

        r_dl1 = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root=None
        )
        r_dl2 = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
            work_root="/nonexistent/phase369_stage84_test"
        )
        self.assertEqual(
            r_dl1["phase369_audit_digest_sha256"],
            r_dl2["phase369_audit_digest_sha256"],
        )

        r_norm = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation()
        if r_norm["source_mode"] == "LOCAL_O_RDONLY_REAL_DONORS":
            self.assertNotEqual(
                r_norm["phase369_audit_digest_sha256"],
                r_f1["phase369_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase369_audit_digest_sha256"],
                r_dl1["phase369_audit_digest_sha256"],
            )

    def test_97_standalone_cli_self_test_summary_json_and_help(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p369.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 369 Stage 84 (84/84)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p369.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "84/84")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p369.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("84/84", buf_help.getvalue())

    def test_98_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p369.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_99_suite_default_config_and_84_of_84_stage_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil
        )
        self.assertTrue(default_cfg.include_stage84)
        self.assertTrue(
            default_cfg.stage84_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s84 = rep[
            "stage84_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil"
        ]
        self.assertTrue(s84["all_checks_passed"])
        self.assertEqual(s84["phase_number"], 369)
        self.assertEqual(s84["milestone"], "84/84")
        self.assertTrue(s84["is_84th_stage_milestone"])
        self.assertEqual(s84["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s84["slot1_data_sector_writes"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Base 3 stages (stage1, stage2, stage3) + optional phase flags must reach >= 84
        self.assertGreaterEqual(len(stage_keys) + 3, 84)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil=",
            buf.getvalue(),
        )
        self.assertIn("m84=84/84", buf.getvalue())

        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc2 = suite.main([*_FAST_CLI_FLAGS, "--skip-stage84", "--json"])
        self.assertEqual(rc2, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertNotIn(
            "stage84_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil",
            rep_skip,
        )

        buf_skip_p = io.StringIO()
        with contextlib.redirect_stdout(buf_skip_p):
            rc3 = suite.main([*_FAST_CLI_FLAGS, "--skip-phase369", "--json"])
        self.assertEqual(rc3, 0)
        rep_skip_p = json.loads(buf_skip_p.getvalue())
        self.assertNotIn(
            "stage84_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_hil",
            rep_skip_p,
        )

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p369.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Phase 369 Stage 84 (84/84)", proc.stdout)

        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        with unittest.mock.patch.object(
            p369,
            "run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation",
            wraps=p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation,
        ) as m_run:
            real = p369.run_phase369_realhw_afspeed_shift_zebra_custom_marker15_saveload_camset_coemulation(
                force_clean_room=True
            )
            bad = dict(real)
            bad["milestone"] = "83/83"
            m_run.return_value = bad
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
