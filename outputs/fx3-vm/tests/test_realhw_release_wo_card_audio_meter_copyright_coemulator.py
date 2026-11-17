#!/usr/bin/env python3
"""Unit tests for Phase 270 (270th Milestone, Stage 53, 53/53):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) Wave-43
`[Release w/o Card]` Still-Only Scope vs Movie Internal Media Gate &
`[Release w/o Lens]` (`e_nd_actuator_tx_count == 0`, Zero E-Mount Lens UART),
`Ver. 2.00+`/`7.02` Exact 5-Item `[Audio Recording]` vs `Ver. 1.x` (`ilc/2035`)
`[Audio Level Display]` Spoof Rejection & `[DISP (Screen Disp) Set]` Audio Meter,
and `[Copyright Info]` `<= 46`-Char Still-JPEG/HEIF EXIF Hygiene & Clean-Room
Operator PII Zeroing HIL Co-Emulator (70 dual-mode tests).
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
import realhw_release_wo_card_audio_meter_copyright_coemulator as p270  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


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
        include_stage52=False,
    )
    base.update(overrides)
    return base


class TestPhase270ReleaseWoCardAudioMeterCopyrightCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p270.run_phase270_realhw_release_wo_card_audio_meter_copyright_hil(
            force_clean_room=True
        )
        cls.default_audit = p270.run_phase270_realhw_release_wo_card_audio_meter_copyright_hil()

        forced = p270.is_forced_clean_room()
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
    # Group 1: Schema, Phase 270 Stage 53 (53/53) & O_RDONLY 18-Donor SHA-256 (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase270_stage53_and_redline_constants(self) -> None:
        self.assertEqual(
            p270.SCHEMA_ID,
            "realhw_release_wo_card_audio_meter_copyright_coemulator_v1",
        )
        self.assertEqual(p270.PHASE_270_SCHEMA, p270.SCHEMA_ID)
        self.assertEqual(p270.PHASE_270_VERSION, "270.0.0")
        self.assertEqual(p270.PHASE_NUMBER, 270)
        self.assertEqual(p270.STAGE_INDEX, 53)
        self.assertEqual(p270.STAGE_TOTAL, 53)
        self.assertEqual(p270.MILESTONE_LABEL, "53/53")
        self.assertEqual(
            p270.STAGE_NAME,
            "stage53_realhw_release_wo_card_audio_meter_copyright_hil",
        )
        self.assertTrue(p270.IS_270TH_PHASE_MILESTONE)
        self.assertEqual(p270.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p270.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p270.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(p270.FORBIDDEN_LEGACY_V1_HELP_GUIDE_ID, "ilc/2035")
        self.assertTrue(p270.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p270.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p270.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p270.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_sha256_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p270.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(self.clean_audit["is_270th_phase_milestone"])
        again = p270.run_phase270_realhw_release_wo_card_audio_meter_copyright_hil(
            force_clean_room=True
        )
        self.assertEqual(
            self.clean_audit["audit_digest_sha256"], again["audit_digest_sha256"]
        )
        self.assertEqual(len(self.clean_audit["audit_digest_sha256"]), 64)

    def test_03_default_audit_18_donors_o_rdonly_fast_and_zero_leakage(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["donor_files_inspected"], 18)
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertLess(da["inspection_elapsed_s"], 0.2 if IS_CI else 0.1)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_04_all_18_donor_expected_byte_sizes_verified(self) -> None:
        self.assertEqual(len(p270.EXPECTED_DONOR_BYTES), 18)
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key, expected_size in p270.EXPECTED_DONOR_BYTES.items():
                self.assertEqual(audit[key]["file_bytes"], expected_size)

    def test_05_pinned_sha256_hashes_verified_on_compact_and_large_donors(self) -> None:
        self.assertEqual(len(p270.EXPECTED_COMPACT_DONOR_SHA256), 10)
        self.assertEqual(len(p270.EXPECTED_LARGE_HEAD4K_SHA256), 8)
        da = self.default_audit["donor_audit"]
        for key, expected_sha in p270.EXPECTED_COMPACT_DONOR_SHA256.items():
            self.assertEqual(len(expected_sha), 64)
            self.assertTrue(da[key]["sha256_verified"])
            if da["source_mode"] == p270.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(da[key]["sha256"], expected_sha)
        for key, expected_h4k in p270.EXPECTED_LARGE_HEAD4K_SHA256.items():
            self.assertEqual(len(expected_h4k), 64)
            self.assertTrue(da[key]["head_sha256_verified"])

    def test_06_clean_room_env_vars_both_supported(self) -> None:
        self.assertTrue(p270.is_forced_clean_room({p270.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p270.is_forced_clean_room({p270.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p270.is_forced_clean_room({p270.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertFalse(p270.is_forced_clean_room({}))

    def test_07_compact_donor_tokens_and_absent_tokens_verified(self) -> None:
        for audit in (self.clean_audit["donor_audit"], self.default_audit["donor_audit"]):
            for key in ("fx3_string_en_f", "fx6_string_en"):
                self.assertTrue(audit[key]["marker_hits"])
                self.assertTrue(all(v == 1 for v in audit[key]["marker_hits"].values()))
                self.assertTrue(
                    all(v == 0 for v in audit[key]["absent_marker_hits"].values())
                )

    def test_08_large_donor_bounded_windows_within_4096_bytes(self) -> None:
        for key, windows in p270.LARGE_DONOR_WINDOWS.items():
            self.assertGreaterEqual(len(windows), 3)
            for audit in (
                self.clean_audit["donor_audit"],
                self.default_audit["donor_audit"],
            ):
                self.assertTrue(audit[key]["bounded_windows_only"])
                self.assertTrue(all(v == 1 for v in audit[key]["window_hits"].values()))
                self.assertLessEqual(
                    audit[key]["bytes_read_total"],
                    p270.BOUNDED_WINDOW_MAX_BYTES * (len(windows) + 1),
                )

    def test_09_donor_paths_fallback_when_root_disabled_triggers_clean_room(self) -> None:
        with unittest.mock.patch.object(p270, "_iter_work_roots", return_value=()):
            rep = p270.inspect_phase270_donors(force_clean_room=False, env={})
        self.assertEqual(rep.source_mode, p270.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_10_bounded_window_rdonly_helper_enforces_4096_limit(self) -> None:
        fsize, bread, head, hits = p270._read_bounded_windows_rdonly(
            Path(__file__), ((0, "SHEBANG", b"#!/usr/bin/env python3"),)
        )
        self.assertGreater(fsize, 0)
        self.assertLessEqual(bread, p270.BOUNDED_WINDOW_MAX_BYTES)
        self.assertLessEqual(len(head), p270.BOUNDED_WINDOW_MAX_BYTES)
        self.assertEqual(hits, {"SHEBANG": 1})

    def test_11_fx3_iptc_and_meta_supplier_and_saveload_donors_verified(self) -> None:
        for key in ("fx3_iptc", "fx3_meta_supplier", "fx3_saveload", "fx3_lens_comm"):
            self.assertTrue(
                all(v == 1 for v in self.default_audit["donor_audit"][key]["marker_hits"].values())
            )
            self.assertTrue(
                all(v == 1 for v in self.clean_audit["donor_audit"][key]["marker_hits"].values())
            )

    def test_12_fx3_media_detect_media_cfg_and_fx6_hotshoe_verified(self) -> None:
        for key in ("fx3_media_detect", "fx3_media_cfg", "fx6_hotshoe", "fx3_adj_media"):
            self.assertTrue(
                all(v == 1 for v in self.default_audit["donor_audit"][key]["marker_hits"].values())
            )
            self.assertTrue(
                all(v == 1 for v in self.clean_audit["donor_audit"][key]["marker_hits"].values())
            )

    def test_13_default_vs_clean_room_pillar_parity(self) -> None:
        for k in (
            "pillar_a_release_wo_card_and_lens_hil",
            "pillar_b_audio_recording_5item_and_disp_meter_hil",
            "pillar_c_d_copyright_info_46char_exif_and_redlines",
        ):
            self.assertEqual(self.default_audit[k], self.clean_audit[k])

    def test_14_redlines_dict_locked_across_both_audits(self) -> None:
        for audit in (self.default_audit, self.clean_audit):
            red = audit["redlines"]
            self.assertEqual(red["donor_access_mode"], "O_RDONLY")
            self.assertEqual(red["e_nd_actuator_tx_count"], 0)
            self.assertEqual(red["legacy_v1_audio_level_menu_spoof_events"], 0)
            self.assertEqual(red["hdmi_clean_feed_audio_meter_baked_pixels"], 0)
            self.assertEqual(red["photographer_copyright_pii_leaked_bytes"], 0)
            self.assertEqual(red["slot1_copyright_vault_mutation_bytes"], 0)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 53A [Release w/o Card] & [Release w/o Lens] HIL (18 tests)
    # ------------------------------------------------------------------
    def test_15_pillar_a_menu_paths_and_exhaustive_768_state_matrix_pass(self) -> None:
        pa = self.clean_audit["pillar_a_release_wo_card_and_lens_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["exhaustive_matrix_states"], 768)
        self.assertTrue(pa["zero_cardless_movie_bypasses"])
        self.assertTrue(pa["zero_body_only_uart_leaks"])
        self.assertTrue(pa["zero_end_tx"])
        self.assertEqual(
            pa["release_wo_card_menu_path"],
            "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]",
        )
        self.assertEqual(
            pa["release_wo_lens_menu_path"],
            "MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Lens]",
        )

    def test_16_factory_defaults_both_release_wo_settings_enable(self) -> None:
        self.assertEqual(p270.RELEASE_WO_CARD_DEFAULT, "Enable")
        self.assertEqual(p270.RELEASE_WO_LENS_DEFAULT, "Enable")

    def test_17_cardless_diagnostic_bench_still_shutter_allowed_zero_card_writes(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_STILL,
            slot_state=p270.SLOT_STATE_EMPTY,
            configured_release_wo_card=p270.ENABLE_STATE,
            configured_release_wo_lens=p270.ENABLE_STATE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertTrue(res.still_shutter_actuation_allowed)
        self.assertFalse(res.movie_internal_recording_allowed)
        self.assertEqual(res.card_bytes_written, 0)
        self.assertEqual(res.emount_lens_uart_tx_bytes, 0)

    def test_18_cardless_movie_internal_recording_blocked_even_with_enable(self) -> None:
        for posture in (
            p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            p270.POSTURE_PRODUCTION_SHOOT,
        ):
            res = p270.simulate_release_wo_card_lens_hil(
                bench_posture=posture,
                shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
                slot_state=p270.SLOT_STATE_EMPTY,
                configured_release_wo_card=p270.ENABLE_STATE,
                hdmi_connected=False,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
            self.assertFalse(res.movie_internal_recording_allowed)
            self.assertEqual(res.cardless_unrecorded_production_violations, 0)

    def test_19_cardless_sq_internal_recording_blocked_even_with_enable(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_SQ,
            slot_state=p270.SLOT_STATE_EMPTY,
            configured_release_wo_card=p270.ENABLE_STATE,
            hdmi_connected=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
        self.assertFalse(res.movie_internal_recording_allowed)

    def test_20_cardless_external_hdmi_capture_governed_by_rec_media_dur_hdmi(self) -> None:
        # With Slot-2 present, Rec. Media dur HDMI Output=Off suppresses internal card rec while HDMI stays live
        res_ext = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
            configured_release_wo_card=p270.ENABLE_STATE,
            hdmi_connected=True,
            rec_media_dur_hdmi_output=p270.TOGGLE_OFF,
        )
        self.assertTrue(res_ext.admitted)
        self.assertTrue(res_ext.external_hdmi_capture_allowed)
        self.assertFalse(res_ext.movie_internal_recording_allowed)
        self.assertEqual(res_ext.card_bytes_written, 0)

        # With Slot-2 present and Rec. Media dur HDMI Output=On, both internal and external HDMI allowed
        res_both = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
            configured_release_wo_card=p270.ENABLE_STATE,
            hdmi_connected=True,
            rec_media_dur_hdmi_output=p270.TOGGLE_ON,
        )
        self.assertTrue(res_both.admitted)
        self.assertTrue(res_both.external_hdmi_capture_allowed)
        self.assertTrue(res_both.movie_internal_recording_allowed)

        # Cardless + HDMI disconnected + Movie => blocked EACCES
        res_nocard = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_EMPTY,
            configured_release_wo_card=p270.ENABLE_STATE,
            hdmi_connected=False,
            rec_media_dur_hdmi_output=p270.TOGGLE_ON,
        )
        self.assertFalse(res_nocard.admitted)
        self.assertEqual(res_nocard.errno_code, p270.EACCES_ERRNO)

    def test_21_production_shoot_disable_blocks_cardless_still_and_movie(self) -> None:
        for domain in (
            p270.SHOOTING_DOMAIN_STILL,
            p270.SHOOTING_DOMAIN_MOVIE,
            p270.SHOOTING_DOMAIN_SQ,
        ):
            res = p270.simulate_release_wo_card_lens_hil(
                bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
                shooting_domain=domain,
                slot_state=p270.SLOT_STATE_EMPTY,
                configured_release_wo_card=p270.DISABLE_STATE,
                lens_mount_kind=p270.LENS_MOUNT_EMOUNT_ELECTRONIC,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
            self.assertEqual(res.cardless_unrecorded_production_violations, 0)

    def test_22_force_cardless_production_bypass_blocked_eacces(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
            shooting_domain=p270.SHOOTING_DOMAIN_STILL,
            slot_state=p270.SLOT_STATE_EMPTY,
            configured_release_wo_card=p270.DISABLE_STATE,
            force_cardless_production_bypass=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
        self.assertEqual(res.cardless_unrecorded_production_violations, 0)

    def test_23_slot1_only_ro_vault_cannot_satisfy_writable_production_card(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_SLOT1_RO_VAULT,
            configured_release_wo_card=p270.DISABLE_STATE,
            lens_mount_kind=p270.LENS_MOUNT_EMOUNT_ELECTRONIC,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EROFS_ERRNO)
        self.assertFalse(res.movie_internal_recording_allowed)

    def test_24_force_slot1_vault_card_write_blocked_erofs(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_SLOT1_RO_VAULT,
            force_slot1_vault_card_write=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EROFS_ERRNO)
        self.assertEqual(res.card_bytes_written, 0)

    def test_25_slot2_scratch_with_disable_permits_still_movie_sq(self) -> None:
        for domain in p270.VALID_SHOOTING_DOMAINS:
            res = p270.simulate_release_wo_card_lens_hil(
                bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
                shooting_domain=domain,
                slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
                configured_release_wo_card=p270.DISABLE_STATE,
                configured_release_wo_lens=p270.DISABLE_STATE,
                lens_mount_kind=p270.LENS_MOUNT_EMOUNT_ELECTRONIC,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.card_bytes_written, 0)
            if domain == p270.SHOOTING_DOMAIN_STILL:
                self.assertTrue(res.still_shutter_actuation_allowed)
            else:
                self.assertTrue(res.movie_internal_recording_allowed)

    def test_26_release_wo_lens_enable_allows_body_pl_and_telescope_across_all_domains(self) -> None:
        for mount in (
            p270.LENS_MOUNT_BODY_ONLY_CAP,
            p270.LENS_MOUNT_PL_MECHANICAL,
            p270.LENS_MOUNT_TELESCOPE_T,
        ):
            for domain in p270.VALID_SHOOTING_DOMAINS:
                res = p270.simulate_release_wo_card_lens_hil(
                    bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
                    shooting_domain=domain,
                    slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
                    lens_mount_kind=mount,
                    configured_release_wo_card=p270.DISABLE_STATE,
                    configured_release_wo_lens=p270.ENABLE_STATE,
                )
                self.assertTrue(res.admitted)
                self.assertEqual(res.emount_lens_uart_tx_bytes, 0)
                self.assertFalse(res.fx3_has_builtin_end_filter)
                self.assertEqual(res.e_nd_actuator_tx_count, 0)

    def test_27_release_wo_lens_disable_blocks_body_pl_and_telescope_across_all_domains(self) -> None:
        for mount in (
            p270.LENS_MOUNT_BODY_ONLY_CAP,
            p270.LENS_MOUNT_PL_MECHANICAL,
            p270.LENS_MOUNT_TELESCOPE_T,
        ):
            for domain in p270.VALID_SHOOTING_DOMAINS:
                res = p270.simulate_release_wo_card_lens_hil(
                    bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
                    shooting_domain=domain,
                    slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
                    lens_mount_kind=mount,
                    configured_release_wo_card=p270.DISABLE_STATE,
                    configured_release_wo_lens=p270.DISABLE_STATE,
                )
                self.assertFalse(res.admitted)
                self.assertEqual(res.errno_code, p270.EACCES_ERRNO)

    def test_28_force_end_actuator_tx_blocked_eopnotsupp(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            force_end_actuator_tx=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.fx3_has_builtin_end_filter)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)

    def test_29_electronic_emount_lens_has_nonzero_uart_tx_even_with_release_wo_lens_enable(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            slot_state=p270.SLOT_STATE_BOTH,
            lens_mount_kind=p270.LENS_MOUNT_EMOUNT_ELECTRONIC,
            configured_release_wo_card=p270.DISABLE_STATE,
            configured_release_wo_lens=p270.ENABLE_STATE,
        )
        self.assertTrue(res.admitted)
        self.assertGreater(res.emount_lens_uart_tx_bytes, 0)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)

    def test_30_release_wo_card_and_lens_survive_camera_settings_and_network_reset(self) -> None:
        for action in (
            p270.RESET_ACTION_CAMERA_SETTINGS_RESET,
            p270.RESET_ACTION_RESET_NETWORK_SET,
        ):
            res = p270.simulate_release_wo_card_lens_hil(
                bench_posture=p270.POSTURE_PRODUCTION_SHOOT,
                shooting_domain=p270.SHOOTING_DOMAIN_STILL,
                slot_state=p270.SLOT_STATE_SLOT2_SCRATCH,
                lens_mount_kind=p270.LENS_MOUNT_EMOUNT_ELECTRONIC,
                configured_release_wo_card=p270.DISABLE_STATE,
                configured_release_wo_lens=p270.DISABLE_STATE,
                reset_action=action,
            )
            self.assertEqual(res.effective_release_wo_card, p270.DISABLE_STATE)
            self.assertEqual(res.effective_release_wo_lens, p270.DISABLE_STATE)

    def test_31_initialize_resets_both_release_wo_settings_to_enable(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            bench_posture=p270.POSTURE_CARDLESS_DIAGNOSTIC_BENCH,
            shooting_domain=p270.SHOOTING_DOMAIN_STILL,
            slot_state=p270.SLOT_STATE_EMPTY,
            lens_mount_kind=p270.LENS_MOUNT_BODY_ONLY_CAP,
            configured_release_wo_card=p270.DISABLE_STATE,
            configured_release_wo_lens=p270.DISABLE_STATE,
            reset_action=p270.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_release_wo_card, p270.ENABLE_STATE)
        self.assertEqual(res.effective_release_wo_lens, p270.ENABLE_STATE)

    def test_32_invalid_release_wo_param_rejected_einval(self) -> None:
        res = p270.simulate_release_wo_card_lens_hil(
            shooting_domain="InvalidDomain",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EINVAL_ERRNO)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 53B Ver. 7.02 Exact 5-Item [Audio Recording] vs DISP Meter (16 tests)
    # ------------------------------------------------------------------
    def test_33_pillar_b_exact_5_audio_items_and_72_state_matrix_pass(self) -> None:
        pb = self.clean_audit["pillar_b_audio_recording_5item_and_disp_meter_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["state_space_count"], 72)
        self.assertTrue(pb["zero_sq_meter_leaks"])
        self.assertTrue(pb["zero_clean_hdmi_baked"])
        self.assertEqual(
            pb["exact_5_audio_items"],
            [
                "Audio Recording",
                "Audio Rec Level",
                "Audio Out Timing",
                "Wind Noise Reduct.",
                "Shoe Audio Set.",
            ],
        )
        self.assertEqual(pb["forbidden_legacy_v1_item"], "Audio Level Display")

    def test_34_legacy_v1_ilc2035_helpguide_rejected_eopnotsupp(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            helpguide_id=p270.FORBIDDEN_LEGACY_V1_HELP_GUIDE_ID,
            firmware_version="1.00",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.legacy_v1_audio_level_menu_spoof_events, 0)

    def test_35_legacy_v1_audio_level_display_item_rejected_even_on_v702(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            helpguide_id=p270.FX3_HELP_GUIDE_ID,
            firmware_version="7.02",
            audio_menu_items=p270.AUDIO_RECORDING_EXACT_5_ITEMS + ("Audio Level Display",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.legacy_v1_audio_level_menu_spoof_events, 0)

    def test_36_force_inject_v1_audio_level_display_rejected_eopnotsupp(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            force_inject_v1_audio_level_display=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.legacy_v1_audio_level_menu_spoof_events, 0)

    def test_37_audio_rec_level_bounds_0_to_31_and_out_of_range_einval(self) -> None:
        ok0 = p270.simulate_audio_recording_and_disp_meter_hil(configured_audio_rec_level=0)
        ok31 = p270.simulate_audio_recording_and_disp_meter_hil(configured_audio_rec_level=31)
        self.assertTrue(ok0.admitted)
        self.assertTrue(ok31.admitted)
        for bad in (-1, 32, 99):
            res = p270.simulate_audio_recording_and_disp_meter_hil(
                configured_audio_rec_level=bad
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p270.EINVAL_ERRNO)

    def test_38_audio_out_timing_live_and_lip_sync_and_wind_noise_modes(self) -> None:
        for timing in (p270.AUDIO_OUT_TIMING_LIVE, p270.AUDIO_OUT_TIMING_LIP_SYNC):
            for wind in (p270.TOGGLE_ON, p270.TOGGLE_OFF):
                res = p270.simulate_audio_recording_and_disp_meter_hil(
                    configured_audio_out_timing=timing,
                    configured_wind_noise_reduct=wind,
                )
                self.assertTrue(res.admitted)
                self.assertEqual(res.effective_audio_out_timing, timing)
                self.assertEqual(res.effective_wind_noise_reduct, wind)

    def test_39_mi_shoe_4ch_xlr_h1_renders_4ch_audio_meter_on_lcd(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_shoe_audio_set=p270.SHOE_AUDIO_48K_24B_4CH,
            audio_input_source=p270.AUDIO_INPUT_MI_SHOE_4CH,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            disp_audio_level_enabled=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.audio_meter_visible_on_lcd)
        self.assertEqual(res.audio_meter_channels_rendered, 4)
        self.assertFalse(res.audio_meter_suppressed_by_sq)
        self.assertEqual(res.hdmi_clean_feed_audio_meter_baked_pixels, 0)

    def test_40_mi_shoe_2ch_and_builtin_mic_render_2ch_audio_meter_on_lcd(self) -> None:
        for src in (
            p270.AUDIO_INPUT_BUILTIN_MIC,
            p270.AUDIO_INPUT_MI_SHOE_2CH,
            p270.AUDIO_INPUT_35MM_ANALOG,
        ):
            res = p270.simulate_audio_recording_and_disp_meter_hil(
                configured_shoe_audio_set=p270.SHOE_AUDIO_48K_24B_2CH,
                audio_input_source=src,
                shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
                disp_audio_level_enabled=True,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.audio_meter_visible_on_lcd)
            self.assertEqual(res.audio_meter_channels_rendered, 2)

    def test_41_shoe_audio_4ch_setting_with_builtin_mic_falls_back_to_2ch_meter(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_shoe_audio_set=p270.SHOE_AUDIO_48K_24B_4CH,
            audio_input_source=p270.AUDIO_INPUT_BUILTIN_MIC,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            disp_audio_level_enabled=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.audio_meter_visible_on_lcd)
        self.assertEqual(res.audio_meter_channels_rendered, 2)

    def test_42_sq_motion_suppresses_audio_meter_across_all_sources(self) -> None:
        for src in p270.VALID_AUDIO_INPUT_SOURCES:
            res = p270.simulate_audio_recording_and_disp_meter_hil(
                configured_shoe_audio_set=p270.SHOE_AUDIO_48K_24B_4CH,
                audio_input_source=src,
                shooting_domain=p270.SHOOTING_DOMAIN_SQ,
                disp_audio_level_enabled=True,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.audio_meter_visible_on_lcd)
            self.assertTrue(res.audio_meter_suppressed_by_sq)
            self.assertEqual(res.audio_meter_channels_rendered, 0)

    def test_43_audio_recording_off_suppresses_audio_meter_even_when_disp_enabled(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_audio_recording=p270.TOGGLE_OFF,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            disp_audio_level_enabled=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.audio_meter_visible_on_lcd)
        self.assertEqual(res.audio_meter_channels_rendered, 0)

    def test_44_disp_audio_level_disabled_hides_meter_even_when_audio_recording_on(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_audio_recording=p270.TOGGLE_ON,
            shooting_domain=p270.SHOOTING_DOMAIN_MOVIE,
            disp_audio_level_enabled=False,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.audio_meter_visible_on_lcd)
        self.assertEqual(res.audio_meter_channels_rendered, 0)

    def test_45_force_bake_audio_meter_into_clean_hdmi_blocked_eacces(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            hdmi_info_display=p270.TOGGLE_OFF,
            force_bake_audio_meter_into_clean_hdmi=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
        self.assertEqual(res.hdmi_clean_feed_audio_meter_baked_pixels, 0)

    def test_46_camera_settings_reset_resets_5_audio_items_but_preserves_disp_set(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_audio_recording=p270.TOGGLE_OFF,
            configured_audio_rec_level=9,
            configured_audio_out_timing=p270.AUDIO_OUT_TIMING_LIP_SYNC,
            configured_wind_noise_reduct=p270.TOGGLE_ON,
            configured_shoe_audio_set=p270.SHOE_AUDIO_48K_24B_4CH,
            disp_audio_level_enabled=False,
            reset_action=p270.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_recording, p270.TOGGLE_ON)
        self.assertEqual(res.effective_audio_rec_level, p270.AUDIO_REC_LEVEL_DEFAULT)
        self.assertEqual(res.effective_audio_out_timing, p270.AUDIO_OUT_TIMING_LIVE)
        self.assertEqual(res.effective_wind_noise_reduct, p270.TOGGLE_OFF)
        self.assertEqual(res.effective_shoe_audio_set, p270.SHOE_AUDIO_48K_24B_2CH)
        self.assertFalse(res.effective_disp_audio_level_enabled)

    def test_47_reset_network_set_preserves_all_audio_and_disp_settings(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_audio_recording=p270.TOGGLE_OFF,
            configured_audio_rec_level=15,
            configured_audio_out_timing=p270.AUDIO_OUT_TIMING_LIP_SYNC,
            configured_wind_noise_reduct=p270.TOGGLE_ON,
            configured_shoe_audio_set=p270.SHOE_AUDIO_48K_16B_2CH,
            disp_audio_level_enabled=False,
            reset_action=p270.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_recording, p270.TOGGLE_OFF)
        self.assertEqual(res.effective_audio_rec_level, 15)
        self.assertEqual(res.effective_audio_out_timing, p270.AUDIO_OUT_TIMING_LIP_SYNC)
        self.assertEqual(res.effective_wind_noise_reduct, p270.TOGGLE_ON)
        self.assertEqual(res.effective_shoe_audio_set, p270.SHOE_AUDIO_48K_16B_2CH)
        self.assertFalse(res.effective_disp_audio_level_enabled)

    def test_48_initialize_resets_both_audio_5items_and_disp_set(self) -> None:
        res = p270.simulate_audio_recording_and_disp_meter_hil(
            configured_audio_recording=p270.TOGGLE_OFF,
            configured_audio_rec_level=5,
            disp_audio_level_enabled=False,
            reset_action=p270.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_recording, p270.TOGGLE_ON)
        self.assertEqual(res.effective_audio_rec_level, p270.AUDIO_REC_LEVEL_DEFAULT)
        self.assertTrue(res.effective_disp_audio_level_enabled)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 53C [Copyright Info] <=46-Char Still EXIF Hygiene & PII Zeroing (12 tests)
    # ------------------------------------------------------------------
    def test_49_pillar_c_d_exact_4_subitems_and_46_char_max(self) -> None:
        pcd = self.clean_audit["pillar_c_d_copyright_info_46char_exif_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(pcd["max_chars"], 46)
        self.assertEqual(
            pcd["subitems"],
            [
                "Write Copyright Info",
                "Set Photographer",
                "Set Copyright",
                "Disp. Copyright Info",
            ],
        )

    def test_50_exact_46_ascii_chars_accepted_on_still_targets_slot2(self) -> None:
        s46 = "A" * 46
        c46 = "C" * 46
        for tgt in p270.STILL_CAPTURE_TARGETS:
            res = p270.simulate_copyright_info_46char_exif_hil(
                configured_write_copyright_info=p270.TOGGLE_ON,
                configured_photographer=s46,
                configured_copyright=c46,
                capture_target=tgt,
                target_slot=2,
                clean_room_mode=False,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.still_exif_copyright_written)
            self.assertFalse(res.movie_xavc_or_raw_copyright_mutated)
            self.assertEqual(res.photographer_char_len, 46)
            self.assertEqual(res.copyright_char_len, 46)

    def test_51_47_char_overflow_blocked_einval(self) -> None:
        s47 = "X" * 47
        for kw in (
            {"configured_photographer": s47},
            {"configured_copyright": s47},
        ):
            res = p270.simulate_copyright_info_46char_exif_hil(
                configured_write_copyright_info=p270.TOGGLE_ON,
                target_slot=2,
                **kw,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p270.EINVAL_ERRNO)
            self.assertEqual(res.copyright_char_overflow_or_movie_mutation_events, 0)

    def test_52_control_chars_and_non_ascii_rejected_einval(self) -> None:
        for bad in ("Bad\nLine", "Null\x00Byte", "Unicode©2026", "Tab\tChar"):
            res = p270.simulate_copyright_info_46char_exif_hil(
                configured_write_copyright_info=p270.TOGGLE_ON,
                configured_photographer=bad,
                target_slot=2,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p270.EINVAL_ERRNO)

    def test_53_movie_xavc_and_hdmi_raw_targets_never_mutated_by_copyright(self) -> None:
        for tgt in p270.MOVIE_STREAM_CAPTURE_TARGETS:
            res = p270.simulate_copyright_info_46char_exif_hil(
                configured_write_copyright_info=p270.TOGGLE_ON,
                configured_photographer="Bench Op",
                configured_copyright="(c) 2026 Lab",
                capture_target=tgt,
                target_slot=2,
                clean_room_mode=True,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.still_exif_copyright_written)
            self.assertFalse(res.movie_xavc_or_raw_copyright_mutated)

    def test_54_force_movie_stream_copyright_write_blocked_eopnotsupp(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Op",
            configured_copyright="Lab",
            capture_target=p270.CAPTURE_TARGET_MOVIE_XAVC_SI,
            target_slot=2,
            force_movie_stream_copyright_write=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.movie_xavc_or_raw_copyright_mutated)
        self.assertEqual(res.copyright_char_overflow_or_movie_mutation_events, 0)

    def test_55_slot1_tier0_vault_copyright_write_blocked_erofs(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Op",
            configured_copyright="Lab",
            capture_target=p270.CAPTURE_TARGET_STILL_JPEG,
            target_slot=1,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EROFS_ERRNO)
        self.assertEqual(res.slot1_copyright_vault_mutation_bytes, 0)

    def test_56_clean_room_mode_zeroes_operator_pii_and_blocks_pii_leak(self) -> None:
        res_ok = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Real Operator Name",
            configured_copyright="Copyright Real Studio",
            capture_target=p270.CAPTURE_TARGET_STILL_JPEG,
            target_slot=2,
            clean_room_mode=True,
        )
        self.assertTrue(res_ok.admitted)
        self.assertEqual(res_ok.configured_photographer, "")
        self.assertEqual(res_ok.configured_copyright, "")
        self.assertEqual(res_ok.effective_photographer, "")
        self.assertEqual(res_ok.effective_copyright, "")
        self.assertEqual(res_ok.photographer_copyright_pii_leaked_bytes, 0)

        res_leak = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Real Operator Name",
            configured_copyright="Copyright Real Studio",
            clean_room_mode=True,
            force_emit_operator_pii_in_clean_room=True,
        )
        self.assertFalse(res_leak.admitted)
        self.assertEqual(res_leak.errno_code, p270.EACCES_ERRNO)
        self.assertEqual(res_leak.photographer_copyright_pii_leaked_bytes, 0)

    def test_57_camset_export_copyright_pii_leak_blocked_eacces(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Operator",
            configured_copyright="Studio",
            force_camset_export_pii_leak=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p270.EACCES_ERRNO)
        self.assertFalse(res.camset_export_includes_copyright_pii)
        self.assertEqual(res.camset_copyright_pii_leaked_bytes, 0)

    def test_58_camera_settings_reset_resets_write_flag_off_while_preserving_strings(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Unit Test Photographer",
            configured_copyright="Unit Test Copyright",
            clean_room_mode=False,
            reset_action=p270.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_write_copyright_info, p270.TOGGLE_OFF)
        self.assertEqual(res.effective_photographer, "Unit Test Photographer")
        self.assertEqual(res.effective_copyright, "Unit Test Copyright")
        self.assertFalse(res.still_exif_copyright_written)

    def test_59_reset_network_set_preserves_copyright_toggle_and_strings(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Unit Test Photographer",
            configured_copyright="Unit Test Copyright",
            clean_room_mode=False,
            reset_action=p270.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_write_copyright_info, p270.TOGGLE_ON)
        self.assertEqual(res.effective_photographer, "Unit Test Photographer")
        self.assertEqual(res.effective_copyright, "Unit Test Copyright")
        self.assertTrue(res.still_exif_copyright_written)

    def test_60_initialize_wipes_copyright_strings_and_resets_toggle_off(self) -> None:
        res = p270.simulate_copyright_info_46char_exif_hil(
            configured_write_copyright_info=p270.TOGGLE_ON,
            configured_photographer="Unit Test Photographer",
            configured_copyright="Unit Test Copyright",
            clean_room_mode=False,
            reset_action=p270.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_write_copyright_info, p270.TOGGLE_OFF)
        self.assertEqual(res.effective_photographer, "")
        self.assertEqual(res.effective_copyright, "")

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 53 (53/53) Suite & Subprocess Hygiene (10 tests)
    # ------------------------------------------------------------------
    def test_61_all_16_redline_probes_fail_closed_and_baseline_valid(self) -> None:
        self.assertEqual(len(p270.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p270.probe_phase270_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p270.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p270.probe_phase270_redline_guard(**{field: True})
            self.assertFalse(blocked.valid)
            self.assertGreater(blocked.errno_code, 0)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p270.probe_phase270_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p270.EINVAL_ERRNO)

    def test_62_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p270.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_release_wo_card_audio_meter_copyright_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 270 Stage 53 (53/53)", proc_sum.stdout)
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
        self.assertEqual(data["milestone"], "53/53")
        self.assertTrue(data["is_270th_phase_milestone"])

    def test_63_suite_stage53_53_of_53_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s53 = rep["stage53_realhw_release_wo_card_audio_meter_copyright_hil"]
            self.assertTrue(s53["all_checks_passed"])
            self.assertEqual(s53["phase_number"], 270)
            self.assertEqual(s53["milestone"], "53/53")
            self.assertTrue(s53["is_270th_phase_milestone"])
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 53)

    def test_64_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 12.0 if IS_CI else 5.0
        max_clean_s = 6.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_65_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_66_suite_stage53_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage53_realhw_release_wo_card_audio_meter_copyright_hil)
        self.assertTrue(default_cfg.include_stage53)
        self.assertTrue(
            default_cfg.include_phase270_realhw_release_wo_card_audio_meter_copyright_hil
        )

        for override in (
            {"stage53_realhw_release_wo_card_audio_meter_copyright_hil": False},
            {"include_stage53": False},
            {"include_phase270_realhw_release_wo_card_audio_meter_copyright_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage53_realhw_release_wo_card_audio_meter_copyright_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage53"])
            self.assertFalse(
                rep["config"]["stage53_realhw_release_wo_card_audio_meter_copyright_hil"]
            )

    def test_67_fx3_vm_coemulation_suite_include_stage53_cli_summary(self) -> None:
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
            "--skip-stage52",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage53", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_release_wo_card_audio_meter_copyright_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_68_fx3_vm_coemulation_suite_cli_skip_phase270_and_skip_stage53(self) -> None:
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
            "--skip-stage52",
        ]
        for skip_flag in ("--skip-phase270", "--skip-stage53", "--no-include-stage53"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage53_realhw_release_wo_card_audio_meter_copyright_hil", parsed
            )

    def test_69_all_safety_and_byof_redlines_locked_across_stage53_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertFalse(red["fx3_has_builtin_end_filter"])
            self.assertEqual(red["e_nd_actuator_tx_count"], 0)
            self.assertEqual(red["cardless_unrecorded_production_violations"], 0)
            self.assertEqual(red["legacy_v1_audio_level_menu_spoof_events"], 0)
            self.assertEqual(red["hdmi_clean_feed_audio_meter_baked_pixels"], 0)
            self.assertEqual(red["photographer_copyright_pii_leaked_bytes"], 0)
            self.assertEqual(red["slot1_copyright_vault_mutation_bytes"], 0)
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
