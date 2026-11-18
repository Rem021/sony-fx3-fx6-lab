#!/usr/bin/env python3
"""Unit tests for Phase 309 (Stage 63 — 63/63 VM Stages Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-53
`[Lens Compensation]` Shading Auto/Off vs Dormant Auto:Low & SteadyShot Active Distortion Lock,
Built-in Front AF Illuminator LED #8 (`0.3..3.0 m`) + MI-Shoe Flash Still AF-S Only vs
Zero-Illuminator FX6 + Movie AF Kinematics (`[AF Transition Speed]` / `[AF Subj. Shift Sens.]` /
`[AF Assist]`),
AF Behavior & Initialize-Only Persistence (5 settings surviving `[Camera Settings Reset]`:
`[Aperture Drive in AF]`, `[AF w/ Shutter]`, `[Pre-AF]`, `[Circ. of Focus Point]`,
`[Focus Area Color]`), and
`[File/Folder Settings]` / `[Select REC Folder]` / `[Create New Folder]` + Playback `[Rating]`
(1..5 Stars) Slot-1 Tier-0 Recovery Vault Firewall HIL Co-Emulator (88 dual-mode tests).
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
import realhw_lens_comp_af_illuminator_folder_rating_coemulator as p309  # noqa: E402

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
        include_stage62=False,
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
]


class TestPhase309DonorInspection(unittest.TestCase):
    """Dual-mode 12-donor O_RDONLY & clean-room verification tests."""

    def test_01_schema_and_milestone_constants(self) -> None:
        self.assertEqual(
            p309.SCHEMA_ID,
            "realhw_lens_comp_af_illuminator_folder_rating_coemulator_v1",
        )
        self.assertEqual(p309.PHASE_NUMBER, 309)
        self.assertEqual(p309.STAGE_INDEX, 63)
        self.assertEqual(p309.STAGE_TOTAL, 63)
        self.assertEqual(p309.MILESTONE_LABEL, "63/63")
        self.assertEqual(p309.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p309.BOUNDED_WINDOW_MAX_BYTES, 4096)

    def test_02_donor_audit_current_mode_12_donors(self) -> None:
        audit = p309.inspect_phase309_donors()
        self.assertTrue(audit.all_contracts_verified, audit.errors)
        self.assertEqual(audit.donor_files_inspected, 12)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertIn(
            audit.source_mode,
            (p309.SOURCE_MODE_LOCAL_DONOR, p309.SOURCE_MODE_CLEAN_ROOM),
        )
        self.assertTrue(audit.lens_comp_and_dormant_auto_low_proven)
        self.assertTrue(audit.af_illuminator_and_kinematics_proven)
        self.assertTrue(audit.af_behavior_initialize_proven)
        self.assertTrue(audit.folder_rating_vault_proven)
        max_elapsed = 17.0 if IS_CI else 2.0
        self.assertLess(audit.inspection_elapsed_s, max_elapsed)

    def test_03_force_clean_room_both_env_vars(self) -> None:
        for env_key in (p309.ENV_CLEAN_ROOM_TEST, p309.ENV_FORCE_CLEAN_ROOM):
            audit = p309.inspect_phase309_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p309.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_files_inspected, 12)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_missing_donor_dir_falls_back_clean_room(self) -> None:
        audit = p309.inspect_phase309_donors(
            env={p309.ENV_MAC_WORK_ROOT: "/nonexistent/fx3/__missing__"}
        )
        self.assertEqual(audit.source_mode, p309.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_compact_donor_byte_lengths_and_containers(self) -> None:
        audit = p309.inspect_phase309_donors()
        for attr in (
            "fx3_string_en_f",
            "fx3_string_sc_f",
            "fx3_string_tc_f",
            "fx3_string_ja_f",
            "fx3_string_en",
            "fx3_string_en_g",
            "fx3_lens_comm",
            "fx6_string_en",
            "fx6_string_en_2",
        ):
            item = getattr(audit, attr)
            self.assertEqual(item.byte_length, p309.EXPECTED_DONOR_BYTES[attr])
            self.assertTrue(item.sha256_verified, attr)
            self.assertTrue(item.container_ok, attr)
            self.assertTrue(all(v == 1 for v in item.marker_hits.values()), attr)

    def test_06_large_donor_bounded_windows_verified(self) -> None:
        audit = p309.inspect_phase309_donors()
        for attr in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
            lg = getattr(audit, attr)
            self.assertEqual(lg.byte_length, p309.EXPECTED_DONOR_BYTES[attr])
            self.assertTrue(lg.head_sha256_verified, attr)
            self.assertTrue(lg.elf64_le_ok, attr)
            self.assertTrue(all(v == 1 for v in lg.window_hits.values()), attr)

    def test_07_bounded_read_rejects_oversized_window(self) -> None:
        with self.assertRaises(ValueError):
            p309._read_bounded_o_rdonly(Path(__file__), 0, 4097)

    def test_08_negative_bounded_read_rejected(self) -> None:
        with self.assertRaises(ValueError):
            p309._read_bounded_o_rdonly(Path(__file__), 0, -1)

    def test_09_fx3_has_builtin_led8_and_fx6_zero_illuminator_constants(self) -> None:
        self.assertTrue(p309.FX3_HAS_BUILTIN_AF_ILLUMINATOR)
        self.assertFalse(p309.FX6_HAS_BUILTIN_AF_ILLUMINATOR)
        self.assertEqual(p309.FX3_BUILTIN_LED8_RANGE_M, (0.3, 3.0))

    def test_10_all_hardware_write_constants_locked_safe(self) -> None:
        self.assertTrue(p309.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p309.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p309.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p309.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p309.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p309.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p309.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p309.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p309.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p309.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p309.RAW_FIRMWARE_BYTES_LEAKED, 0)


class TestSubModel63ALensCompensation(unittest.TestCase):
    """Wave-53 [Lens Compensation] Shading Auto/Off vs Dormant Auto:Low & Active Locks."""

    def test_11_fx3_exposes_only_auto_and_off_for_shading(self) -> None:
        for mode in (p309.COMP_AUTO, p309.COMP_OFF):
            r = p309.simulate_lens_compensation_hil(shading_comp=mode)
            self.assertTrue(r.admitted)
            self.assertEqual(r.exposed_shading_options, ("Auto", "Off"))
            self.assertEqual(r.effective_shading_comp, mode)
            self.assertEqual(r.dormant_shading_auto_low_exposed_events, 0)

    def test_12_dormant_shading_auto_low_and_low_rejected_eopnotsupp(self) -> None:
        for dormant in (p309.COMP_DORMANT_AUTO_LOW, p309.COMP_DORMANT_LOW):
            r = p309.simulate_lens_compensation_hil(shading_comp=dormant)
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.dormant_shading_auto_low_exposed_events, 0)

    def test_13_fx6_also_rejects_dormant_auto_low(self) -> None:
        r = p309.simulate_lens_compensation_hil(
            body_profile=p309.BODY_MODEL_FX6,
            shading_comp=p309.COMP_DORMANT_AUTO_LOW,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_14_chromatic_aberration_auto_and_off_admitted(self) -> None:
        for ca in (p309.COMP_AUTO, p309.COMP_OFF):
            r = p309.simulate_lens_compensation_hil(chromatic_aberration_comp=ca)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_ca_comp, ca)

    def test_15_steadyshot_active_forces_distortion_auto_and_blocks_off(self) -> None:
        r_blk = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            steadyshot_mode=p309.STEADYSHOT_ACTIVE,
            distortion_comp=p309.COMP_OFF,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p309.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_blk.distortion_forced_auto)
        self.assertEqual(r_blk.steadyshot_active_distortion_bypass_events, 0)

        r_ok = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            steadyshot_mode=p309.STEADYSHOT_ACTIVE,
            distortion_comp=p309.COMP_AUTO,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_distortion_comp, p309.COMP_AUTO)

    def test_16_sq_steadyshot_active_also_forces_distortion_auto(self) -> None:
        r = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_SQ,
            steadyshot_mode=p309.STEADYSHOT_ACTIVE,
            distortion_comp=p309.COMP_OFF,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_17_distortion_forced_auto_lenses_block_off(self) -> None:
        for lens in p309.DISTORTION_LOCKED_AUTO_LENSES:
            r_blk = p309.simulate_lens_compensation_hil(
                lens_profile=lens, distortion_comp=p309.COMP_OFF
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, p309.EOPNOTSUPP_ERRNO)
            self.assertTrue(r_blk.distortion_forced_auto)

            r_ok = p309.simulate_lens_compensation_hil(
                lens_profile=lens, distortion_comp=p309.COMP_AUTO
            )
            self.assertTrue(r_ok.admitted)
            self.assertEqual(r_ok.effective_distortion_comp, p309.COMP_AUTO)

    def test_18_unchipped_manual_lens_rejected_eopnotsupp(self) -> None:
        r = p309.simulate_lens_compensation_hil(lens_profile=p309.LENS_UNCHIPPED_MANUAL_PL)
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_19_arw_pixel_immutability_vs_shading_gain(self) -> None:
        for arw_fmt in (
            p309.CAPTURE_FMT_ARW_COMPRESSED,
            p309.CAPTURE_FMT_ARW_UNCOMPRESSED,
        ):
            r_auto = p309.simulate_lens_compensation_hil(
                capture_format=arw_fmt,
                shading_comp=p309.COMP_AUTO,
                distortion_comp=p309.COMP_AUTO,
            )
            self.assertTrue(r_auto.admitted)
            self.assertFalse(r_auto.distortion_baked_into_arw_pixels)
            self.assertTrue(r_auto.shading_applies_to_arw_gain)

            r_off = p309.simulate_lens_compensation_hil(
                capture_format=arw_fmt,
                shading_comp=p309.COMP_OFF,
                distortion_comp=p309.COMP_AUTO,
            )
            self.assertTrue(r_off.admitted)
            self.assertFalse(r_off.shading_applies_to_arw_gain)

    def test_20_fx3_breathing_comp_movie_only_and_raw_lockout(self) -> None:
        r_still = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_STILL, breathing_comp=p309.COMP_ON
        )
        self.assertFalse(r_still.admitted)
        self.assertEqual(r_still.errno_code, p309.EOPNOTSUPP_ERRNO)

        r_raw = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            breathing_comp=p309.COMP_ON,
            codec_is_raw=True,
        )
        self.assertFalse(r_raw.admitted)
        self.assertEqual(r_raw.errno_code, p309.EOPNOTSUPP_ERRNO)

        r_ok = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE, breathing_comp=p309.COMP_ON
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_breathing_comp, p309.COMP_ON)

    def test_21_lens_comp_reset_split_cam_reset_vs_initialize(self) -> None:
        r_csr = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            shading_comp=p309.COMP_OFF,
            chromatic_aberration_comp=p309.COMP_OFF,
            distortion_comp=p309.COMP_AUTO,
            breathing_comp=p309.COMP_ON,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_shading_comp, p309.COMP_OFF)
        self.assertEqual(r_csr.effective_ca_comp, p309.COMP_OFF)
        self.assertEqual(r_csr.effective_distortion_comp, p309.COMP_AUTO)
        self.assertEqual(r_csr.effective_breathing_comp, p309.COMP_OFF)

        r_init = p309.simulate_lens_compensation_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            shading_comp=p309.COMP_OFF,
            chromatic_aberration_comp=p309.COMP_OFF,
            distortion_comp=p309.COMP_AUTO,
            breathing_comp=p309.COMP_ON,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_shading_comp, p309.COMP_AUTO)
        self.assertEqual(r_init.effective_ca_comp, p309.COMP_AUTO)
        self.assertEqual(r_init.effective_distortion_comp, p309.COMP_OFF)
        self.assertEqual(r_init.effective_breathing_comp, p309.COMP_OFF)

    def test_22_fx6_technical_lens_all_file_and_breathing_lockouts(self) -> None:
        r_ok = p309.simulate_lens_compensation_hil(
            body_profile=p309.BODY_MODEL_FX6,
            shooting_domain=p309.DOMAIN_MOVIE,
            distortion_comp=p309.COMP_AUTO,
            breathing_comp=p309.COMP_AUTO,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.config_storage_scope, "FX6_ALL_FILE")

        for kwargs in (
            dict(distortion_comp=p309.COMP_OFF, breathing_comp=p309.COMP_AUTO),
            dict(shooting_domain=p309.DOMAIN_SQ, distortion_comp=p309.COMP_AUTO, breathing_comp=p309.COMP_AUTO),
            dict(codec_is_raw=True, distortion_comp=p309.COMP_AUTO, breathing_comp=p309.COMP_AUTO),
        ):
            r_blk = p309.simulate_lens_compensation_hil(
                body_profile=p309.BODY_MODEL_FX6, **kwargs
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_23_fx6_white_black_shading_sensor_cal_distinction(self) -> None:
        d = p309.evaluate_fx6_white_black_shading_distinction()
        self.assertFalse(d["is_optical_lens_shading"])
        self.assertTrue(d["distinct_from_lens_shading_comp"])
        self.assertEqual(d["fx6_optical_lens_comp_menu"], "Technical > Lens")

    def test_24_invalid_lens_comp_inputs_rejected_einval(self) -> None:
        self.assertEqual(
            p309.simulate_lens_compensation_hil(body_profile="ILCE-9M3").errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_lens_compensation_hil(lens_profile="UNKNOWN_LENS").errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_lens_compensation_hil(capture_format="DNG").errno_code,
            p309.EINVAL_ERRNO,
        )


class TestSubModel63BAfIlluminatorAndKinematics(unittest.TestCase):
    """Wave-53 Built-in Front AF Illuminator LED (#8) vs Zero-Illuminator FX6 & Kinematics."""

    def test_25_fx3_still_afs_fires_builtin_led8_and_mishoe_flash(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            body_profile=p309.BODY_MODEL_FX3,
            shooting_domain=p309.DOMAIN_STILL,
            focus_mode=p309.FOCUS_MODE_AFS,
            af_illuminator=p309.AF_ILLUMINATOR_AUTO,
            mishoe_flash_mounted=True,
            mishoe_flash_powered_on=True,
            mishoe_flash_has_af_illuminator=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.fx3_has_builtin_af_illuminator)
        self.assertEqual(r.builtin_led8_range_m, (0.3, 3.0))
        self.assertTrue(r.builtin_led8_fired)
        self.assertTrue(r.mishoe_flash_af_illuminator_fired)
        self.assertEqual(r.illuminator_lockout_reasons, ())

    def test_26_fx3_movie_and_sq_lockout_af_illuminator(self) -> None:
        for dom in (p309.DOMAIN_MOVIE, p309.DOMAIN_SQ):
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=dom, focus_mode=p309.FOCUS_MODE_AFS
            )
            self.assertTrue(r.admitted)
            self.assertFalse(r.builtin_led8_fired)

            r_force = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=dom,
                focus_mode=p309.FOCUS_MODE_AFS,
                force_fire_illuminator=True,
            )
            self.assertFalse(r_force.admitted)
            self.assertEqual(r_force.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_27_fx3_still_afc_mf_afa_dmf_do_not_fire_illuminator(self) -> None:
        for fm in (
            p309.FOCUS_MODE_AFC,
            p309.FOCUS_MODE_MF,
            p309.FOCUS_MODE_AFA,
            p309.FOCUS_MODE_DMF,
        ):
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_STILL, focus_mode=fm
            )
            self.assertTrue(r.admitted)
            self.assertFalse(r.builtin_led8_fired, fm)
            r_force = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_STILL,
                focus_mode=fm,
                force_fire_illuminator=True,
            )
            self.assertFalse(r_force.admitted)
            self.assertEqual(r_force.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_28_silent_mode_magnifier_adaptor_moving_afa_and_off_lockout_led8(self) -> None:
        lockout_cases = (
            dict(silent_mode_on=True),
            dict(focus_magnifier_active=True),
            dict(mount_adaptor_attached=True),
            dict(subject_moving_in_afa=True),
            dict(af_illuminator=p309.AF_ILLUMINATOR_OFF),
        )
        for kw in lockout_cases:
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_STILL,
                focus_mode=p309.FOCUS_MODE_AFS,
                mishoe_flash_mounted=True,
                mishoe_flash_powered_on=True,
                **kw,
            )
            self.assertTrue(r.admitted)
            self.assertFalse(r.builtin_led8_fired, kw)
            self.assertFalse(r.mishoe_flash_af_illuminator_fired, kw)

            r_force = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_STILL,
                focus_mode=p309.FOCUS_MODE_AFS,
                force_fire_illuminator=True,
                **kw,
            )
            self.assertFalse(r_force.admitted)
            self.assertEqual(r_force.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_29_fx6_has_zero_builtin_af_illuminator_and_rejects_fire(self) -> None:
        r_ok = p309.simulate_af_illuminator_and_kinematics_hil(
            body_profile=p309.BODY_MODEL_FX6,
            shooting_domain=p309.DOMAIN_MOVIE,
            focus_mode=p309.FOCUS_MODE_AFC,
        )
        self.assertTrue(r_ok.admitted)
        self.assertFalse(r_ok.fx6_has_builtin_af_illuminator)
        self.assertFalse(r_ok.builtin_led8_fired)

        r_force = p309.simulate_af_illuminator_and_kinematics_hil(
            body_profile=p309.BODY_MODEL_FX6,
            force_fire_illuminator=True,
        )
        self.assertFalse(r_force.admitted)
        self.assertEqual(r_force.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_30_movie_af_transition_speed_and_shift_sensitivity_ranges(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            focus_mode=p309.FOCUS_MODE_AFC,
            af_transition_speed=2,
            af_subj_shift_sens=1,
            af_assist_on=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_af_transition_speed, 2)
        self.assertEqual(r.effective_af_subj_shift_sens, 1)
        self.assertTrue(r.effective_af_assist_on)

        self.assertEqual(
            p309.simulate_af_illuminator_and_kinematics_hil(af_transition_speed=8).errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_af_illuminator_and_kinematics_hil(af_subj_shift_sens=6).errno_code,
            p309.EINVAL_ERRNO,
        )

    def test_31_af_assist_gates_and_incompatible_lenses(self) -> None:
        for dom, fm in (
            (p309.DOMAIN_STILL, p309.FOCUS_MODE_AFC),
            (p309.DOMAIN_MOVIE, p309.FOCUS_MODE_MF),
            (p309.DOMAIN_SQ, p309.FOCUS_MODE_AFS),
        ):
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=dom, focus_mode=fm, af_assist_on=True
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

        for lens in p309.AF_ASSIST_INCOMPATIBLE_LENSES:
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_MOVIE,
                focus_mode=p309.FOCUS_MODE_AFC,
                af_assist_on=True,
                lens_profile=lens,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_32_kinematics_and_illuminator_reset_on_camera_settings_reset(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            shooting_domain=p309.DOMAIN_MOVIE,
            focus_mode=p309.FOCUS_MODE_AFC,
            af_transition_speed=1,
            af_subj_shift_sens=2,
            af_assist_on=True,
            af_illuminator=p309.AF_ILLUMINATOR_OFF,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_af_transition_speed, 5)
        self.assertEqual(r.effective_af_subj_shift_sens, 5)
        self.assertFalse(r.effective_af_assist_on)
        self.assertEqual(r.af_illuminator, p309.AF_ILLUMINATOR_AUTO)

    def test_33_mishoe_unpowered_or_no_led_flash_does_not_fire(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            shooting_domain=p309.DOMAIN_STILL,
            focus_mode=p309.FOCUS_MODE_AFS,
            mishoe_flash_mounted=True,
            mishoe_flash_powered_on=False,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.builtin_led8_fired)
        self.assertFalse(r.mishoe_flash_af_illuminator_fired)


class TestSubModel63CAfBehaviorInitializePersistence(unittest.TestCase):
    """Wave-53 AF Behavior 5 Initialize-Only Settings & Orthogonal Focus Point Circulation."""

    def test_34_all_5_settings_survive_camera_settings_and_network_reset(self) -> None:
        r = p309.simulate_af_behavior_initialize_persistence_hil(
            shooting_domain=p309.DOMAIN_STILL,
            aperture_drive_in_af=p309.APERTURE_DRIVE_FOCUS_PRIORITY,
            af_w_shutter=False,
            pre_af=True,
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area_color=p309.FOCUS_AREA_COLOR_RED,
            camera_settings_reset_applied=True,
            reset_network_settings_applied=True,
            initialize_applied=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_aperture_drive_in_af, p309.APERTURE_DRIVE_FOCUS_PRIORITY)
        self.assertFalse(r.effective_af_w_shutter)
        self.assertTrue(r.effective_pre_af)
        self.assertEqual(r.effective_circ_of_focus_point, p309.CIRC_CIRCULATE)
        self.assertEqual(r.effective_focus_area_color, p309.FOCUS_AREA_COLOR_RED)
        self.assertEqual(r.initialize_only_af_reset_wipe_events, 0)

    def test_35_initialize_only_resets_all_5_settings_to_factory_defaults(self) -> None:
        r = p309.simulate_af_behavior_initialize_persistence_hil(
            shooting_domain=p309.DOMAIN_STILL,
            aperture_drive_in_af=p309.APERTURE_DRIVE_SILENT_PRIORITY,
            af_w_shutter=False,
            pre_af=True,
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area_color=p309.FOCUS_AREA_COLOR_RED,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_aperture_drive_in_af, p309.APERTURE_DRIVE_STANDARD)
        self.assertTrue(r.effective_af_w_shutter)
        self.assertFalse(r.effective_pre_af)
        self.assertEqual(r.effective_circ_of_focus_point, p309.CIRC_DOES_NOT_CIRCULATE)
        self.assertEqual(r.effective_focus_area_color, p309.FOCUS_AREA_COLOR_WHITE)

    def test_36_aperture_drive_focus_priority_warnings_and_silent_link(self) -> None:
        r_fp = p309.simulate_af_behavior_initialize_persistence_hil(
            aperture_drive_in_af=p309.APERTURE_DRIVE_FOCUS_PRIORITY
        )
        self.assertTrue(r_fp.aperture_audible_noise_warning)
        self.assertTrue(r_fp.live_view_dof_mismatch_possible)
        self.assertTrue(r_fp.burst_speed_may_decrease)
        self.assertFalse(r_fp.low_light_af_speed_may_decrease)

        r_sp = p309.simulate_af_behavior_initialize_persistence_hil(
            aperture_drive_in_af=p309.APERTURE_DRIVE_SILENT_PRIORITY,
            silent_mode_on=True,
        )
        self.assertTrue(r_sp.low_light_af_speed_may_decrease)
        self.assertEqual(r_sp.silent_aperture_drive_linked, p309.APERTURE_DRIVE_SILENT_PRIORITY)

    def test_37_still_only_gates_in_movie_and_sq(self) -> None:
        for dom in (p309.DOMAIN_MOVIE, p309.DOMAIN_SQ):
            self.assertEqual(
                p309.simulate_af_behavior_initialize_persistence_hil(
                    shooting_domain=dom,
                    aperture_drive_in_af=p309.APERTURE_DRIVE_FOCUS_PRIORITY,
                ).errno_code,
                p309.EOPNOTSUPP_ERRNO,
            )
            self.assertEqual(
                p309.simulate_af_behavior_initialize_persistence_hil(
                    shooting_domain=dom,
                    af_w_shutter=False,
                ).errno_code,
                p309.EOPNOTSUPP_ERRNO,
            )
            self.assertEqual(
                p309.simulate_af_behavior_initialize_persistence_hil(
                    shooting_domain=dom,
                    pre_af=True,
                ).errno_code,
                p309.EOPNOTSUPP_ERRNO,
            )

    def test_38_pre_af_lens_gate_rejects_unsupported_lens(self) -> None:
        r = p309.simulate_af_behavior_initialize_persistence_hil(
            pre_af=True, lens_pre_af_supported=False
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_39_circ_of_focus_point_orthogonal_horizontal_and_vertical_wrap(self) -> None:
        r_left = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area=p309.FOCUS_AREA_SPOT_M,
            step_from_x=0,
            step_from_y=5,
            step_dx=-1,
            step_dy=0,
        )
        self.assertTrue(r_left.admitted)
        self.assertEqual((r_left.step_to_x, r_left.step_to_y), (14, 5))
        self.assertTrue(r_left.orthogonal_wrap_occurred)
        self.assertFalse(r_left.diagonal_wrap_occurred)

        r_up = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area=p309.FOCUS_AREA_ZONE,
            step_from_x=7,
            step_from_y=0,
            step_dx=0,
            step_dy=-1,
        )
        self.assertTrue(r_up.admitted)
        self.assertEqual((r_up.step_to_x, r_up.step_to_y), (7, 10))
        self.assertTrue(r_up.orthogonal_wrap_occurred)

    def test_40_circ_of_focus_point_rejects_diagonal_wrap(self) -> None:
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            r = p309.simulate_af_behavior_initialize_persistence_hil(
                circ_of_focus_point=p309.CIRC_CIRCULATE,
                step_from_x=0,
                step_from_y=0,
                step_dx=dx,
                step_dy=dy,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.diagonal_wrap_occurred)
            self.assertEqual(r.diagonal_focus_point_wrap_events, 0)

    def test_41_does_not_circulate_or_wide_clamps_focus_point(self) -> None:
        r_clamp = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_DOES_NOT_CIRCULATE,
            step_from_x=0,
            step_from_y=5,
            step_dx=-1,
            step_dy=0,
        )
        self.assertTrue(r_clamp.admitted)
        self.assertEqual((r_clamp.step_to_x, r_clamp.step_to_y), (0, 5))
        self.assertFalse(r_clamp.orthogonal_wrap_occurred)

        r_wide = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area=p309.FOCUS_AREA_WIDE,
            step_from_x=0,
            step_from_y=5,
            step_dx=-1,
            step_dy=0,
        )
        self.assertTrue(r_wide.admitted)
        self.assertFalse(r_wide.orthogonal_wrap_occurred)

    def test_42_focus_area_color_white_red_and_reject_legacy_focus_frame_color(self) -> None:
        for color in (p309.FOCUS_AREA_COLOR_WHITE, p309.FOCUS_AREA_COLOR_RED):
            r = p309.simulate_af_behavior_initialize_persistence_hil(focus_area_color=color)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_focus_area_color, color)

        r_leg = p309.simulate_af_behavior_initialize_persistence_hil(
            requested_legacy_name=p309.DORMANT_FOCUS_AREA_COLOR_LABEL
        )
        self.assertFalse(r_leg.admitted)
        self.assertEqual(r_leg.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_43_fx6_lacks_5_settings_and_uses_cinema_iris(self) -> None:
        r_ok = p309.simulate_af_behavior_initialize_persistence_hil(
            body_profile=p309.BODY_MODEL_FX6,
            fx6_iris_mode="Push Auto Iris",
            fx6_iris_override_ev=-0.5,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_aperture_drive_in_af, "FX6_NA")

        r_bad = p309.simulate_af_behavior_initialize_persistence_hil(
            body_profile=p309.BODY_MODEL_FX6,
            circ_of_focus_point=p309.CIRC_CIRCULATE,
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p309.EOPNOTSUPP_ERRNO)


class TestSubModel63DFolderRatingVaultFirewall(unittest.TestCase):
    """Wave-53 [Create New Folder] & Playback [Rating] (1..5 Stars) Slot-1 Tier-0 Vault Firewall."""

    def test_44_critical_slot1_tier0_vault_create_new_folder_blocked_erofs(self) -> None:
        r = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CREATE_NEW_FOLDER,
            target_slot=p309.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EROFS_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.slot1_vault_folder_or_rating_mutation_bytes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)
        self.assertEqual(r.physical_device_writes, 0)

    def test_45_critical_slot1_tier0_vault_forced_file_number_reset_blocked_erofs(self) -> None:
        r = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_FORCED_FILE_NUMBER_RESET,
            target_slot=p309.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EROFS_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_46_critical_slot1_tier0_vault_playback_rating_and_add_rating_blocked_erofs(self) -> None:
        for op in (
            p309.OP_PLAYBACK_RATING,
            p309.OP_CUSTOM_KEY_RATING_TOGGLE,
            p309.OP_SHOOTING_ADD_RATING,
        ):
            for stars in range(1, 6):
                r = p309.simulate_folder_and_rating_vault_firewall_hil(
                    operation=op,
                    target_slot=p309.SLOT_1,
                    slot1_is_tier0_vault=True,
                    requested_rating_stars=stars,
                )
                self.assertFalse(r.admitted, (op, stars))
                self.assertEqual(r.errno_code, p309.EROFS_ERRNO, (op, stars))
                self.assertTrue(r.tier0_vault_firewall_triggered)
                self.assertFalse(r.avf_info_exif_mutated)
                self.assertFalse(r.slot1_avf_info_mutated)
                self.assertEqual(r.slot1_data_sector_writes, 0)
                self.assertEqual(r.slot1_vault_folder_or_rating_mutation_bytes, 0)

    def test_47_dual_slot_simultaneous_create_folder_or_rating_touches_slot1_and_blocks(self) -> None:
        for op in (
            p309.OP_CREATE_NEW_FOLDER,
            p309.OP_SELECT_REC_FOLDER,
            p309.OP_PLAYBACK_RATING,
        ):
            r = p309.simulate_folder_and_rating_vault_firewall_hil(
                operation=op,
                target_slot=p309.SLOT_2,
                dual_slot_simultaneous=True,
                slot1_is_tier0_vault=True,
                requested_rating_stars=4 if op == p309.OP_PLAYBACK_RATING else 0,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p309.EROFS_ERRNO, op)
            self.assertTrue(r.tier0_vault_firewall_triggered)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_48_slot2_virtual_create_new_folder_allocates_max_plus_1(self) -> None:
        r = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CREATE_NEW_FOLDER,
            target_slot=p309.SLOT_2,
            slot1_is_tier0_vault=True,
            slot2_max_folder_num=107,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.allocated_folder_name, "DCIM/108MSDCF")
        self.assertEqual(r.physical_device_writes, 0)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_49_slot2_virtual_rating_1_to_5_stars_zero_physical_writes(self) -> None:
        for stars in range(1, 6):
            r = p309.simulate_folder_and_rating_vault_firewall_hil(
                operation=p309.OP_PLAYBACK_RATING,
                target_slot=p309.SLOT_2,
                slot1_is_tier0_vault=True,
                requested_rating_stars=stars,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_rating_stars, stars)
            self.assertTrue(r.avf_info_exif_mutated)
            self.assertFalse(r.slot1_avf_info_mutated)
            self.assertEqual(r.physical_device_writes, 0)

    def test_50_add_rating_rejects_already_rated_0x627d_and_movie_rec(self) -> None:
        r_dup = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SHOOTING_ADD_RATING,
            target_slot=p309.SLOT_2,
            requested_rating_stars=3,
            existing_rating_stars=2,
        )
        self.assertFalse(r_dup.admitted)
        self.assertEqual(r_dup.errno_code, p309.EOPNOTSUPP_ERRNO)

        r_mv = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SHOOTING_ADD_RATING,
            target_slot=p309.SLOT_2,
            is_movie_recording=True,
            requested_rating_stars=3,
        )
        self.assertFalse(r_mv.admitted)
        self.assertEqual(r_mv.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_51_rating_set_custom_key_checkbox_subset_enforced(self) -> None:
        r_ok = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CUSTOM_KEY_RATING_TOGGLE,
            target_slot=p309.SLOT_2,
            rating_set_checkboxes=(1, 3, 5),
            requested_rating_stars=3,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_rating_stars, 3)

        r_blk = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CUSTOM_KEY_RATING_TOGGLE,
            target_slot=p309.SLOT_2,
            rating_set_checkboxes=(1, 3, 5),
            requested_rating_stars=4,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_52_background_ftp_transfer_blocks_rating_ebusy(self) -> None:
        r = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_PLAYBACK_RATING,
            target_slot=p309.SLOT_2,
            background_transfer_active=True,
            requested_rating_stars=5,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EBUSY_ERRNO)

    def test_53_date_form_disables_select_rec_folder_and_simult_mismatch_rejected(self) -> None:
        r_df = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SELECT_REC_FOLDER,
            target_slot=p309.SLOT_2,
            folder_name_style=p309.FOLDER_STYLE_DATE,
        )
        self.assertFalse(r_df.admitted)
        self.assertEqual(r_df.errno_code, p309.EOPNOTSUPP_ERRNO)

        r_mm = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SELECT_REC_FOLDER,
            target_slot=p309.SLOT_2,
            dual_slot_simultaneous=True,
            slot1_is_tier0_vault=False,
            folder_exists_on_both_slots=False,
        )
        self.assertFalse(r_mm.admitted)
        self.assertEqual(r_mm.errno_code, p309.EINVAL_ERRNO)

    def test_54_file_name_prefix_rejects_leading_underscore_and_survives_reset(self) -> None:
        r_bad = p309.simulate_folder_and_rating_vault_firewall_hil(file_name_prefix="_FX")
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p309.EINVAL_ERRNO)

        r_csr = p309.simulate_folder_and_rating_vault_firewall_hil(
            file_name_prefix="FX3",
            folder_name_style=p309.FOLDER_STYLE_DATE,
            file_number_mode=p309.FILE_NUMBER_RESET,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_file_name_prefix, "FX3")
        self.assertEqual(r_csr.effective_folder_name_style, p309.FOLDER_STYLE_DATE)
        self.assertEqual(r_csr.effective_file_number_mode, p309.FILE_NUMBER_RESET)

    def test_55_folder_999_max_cap_and_write_protected_card(self) -> None:
        r_999 = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CREATE_NEW_FOLDER,
            target_slot=p309.SLOT_2,
            slot2_max_folder_num=999,
        )
        self.assertFalse(r_999.admitted)
        self.assertEqual(r_999.errno_code, p309.EOPNOTSUPP_ERRNO)

        r_ro = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CREATE_NEW_FOLDER,
            target_slot=p309.SLOT_2,
            card_write_protected=True,
        )
        self.assertFalse(r_ro.admitted)
        self.assertEqual(r_ro.errno_code, p309.EROFS_ERRNO)

    def test_56_fx6_uses_clip_flag_and_rejects_100msdcf_and_5star_rating(self) -> None:
        r_fx6_ok = p309.simulate_folder_and_rating_vault_firewall_hil(
            body_profile=p309.BODY_MODEL_FX6,
            target_slot=p309.SLOT_2,
            fx6_clip_flag="KEEP",
        )
        self.assertTrue(r_fx6_ok.admitted)
        self.assertEqual(r_fx6_ok.effective_folder_name_style, "XAVC_ROOT_FOLDER")

        r_fx6_vault = p309.simulate_folder_and_rating_vault_firewall_hil(
            body_profile=p309.BODY_MODEL_FX6,
            target_slot=p309.SLOT_1,
            slot1_is_tier0_vault=True,
            fx6_clip_flag="OK",
        )
        self.assertFalse(r_fx6_vault.admitted)
        self.assertEqual(r_fx6_vault.errno_code, p309.EROFS_ERRNO)

        for op in (p309.OP_CREATE_NEW_FOLDER, p309.OP_PLAYBACK_RATING):
            r_blk = p309.simulate_folder_and_rating_vault_firewall_hil(
                body_profile=p309.BODY_MODEL_FX6, operation=op
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, p309.EOPNOTSUPP_ERRNO)


class TestRedlinesAndSuiteIntegration(unittest.TestCase):
    """Hard safety redlines, standalone CLI, and full 63/63 suite orchestration."""

    def test_57_full_phase309_report_all_checks_passed(self) -> None:
        rep = p309.run_phase309_lens_comp_af_illuminator_folder_rating_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_63rd_stage_milestone"])
        self.assertEqual(rep["milestone"], "63/63")
        self.assertEqual(rep["stage_index"], 63)
        self.assertEqual(rep["stage_total"], 63)

    def test_58_clean_room_report_deterministic_digest(self) -> None:
        r1 = p309.run_phase309_lens_comp_af_illuminator_folder_rating_coemulation(
            force_clean_room=True
        )
        r2 = p309.run_phase309_lens_comp_af_illuminator_folder_rating_coemulation(
            env={p309.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["source_mode"], p309.SOURCE_MODE_CLEAN_ROOM)

    def test_59_all_hardware_write_redlines_locked_false_and_zero(self) -> None:
        rep = p309.run_phase309_lens_comp_af_illuminator_folder_rating_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        self.assertTrue(red["fx3_has_builtin_af_illuminator"])
        for false_key in (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "fx6_has_builtin_af_illuminator",
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
            "dormant_shading_auto_low_exposed_events",
            "steadyshot_active_distortion_bypass_events",
            "af_illuminator_non_afs_or_silent_fire_events",
            "initialize_only_af_reset_wipe_events",
            "diagonal_focus_point_wrap_events",
            "slot1_data_sector_writes",
            "slot1_vault_folder_or_rating_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_60_standalone_cli_help_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_lens_comp_af_illuminator_folder_rating_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)

    def test_61_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p309.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 309 Stage 63 (63/63 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p309.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "63/63")
        self.assertTrue(parsed["all_checks_passed"])

    def test_62_suite_default_config_enables_stage63(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase309_realhw_lens_comp_af_illuminator_folder_rating_hil)
        self.assertTrue(cfg.include_stage63)
        self.assertTrue(cfg.stage63_realhw_lens_comp_af_illuminator_folder_rating_hil)

    def test_63_suite_full_run_contains_at_least_63_stages(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 63)
        s63 = rep["stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"]
        self.assertTrue(s63["all_checks_passed"])
        self.assertTrue(s63["is_63rd_stage_milestone"])
        self.assertEqual(s63["milestone"], "63/63")
        self.assertEqual(s63["phase_number"], 309)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_64_suite_fast_isolated_stage63_only_pass(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(rep["all_checks_passed"])
        self.assertIsNone(rep.get("stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"))
        self.assertIsNotNone(rep.get("stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"))

    def test_65_suite_skip_flags_disable_stage63(self) -> None:
        for flag in ("--skip-stage63", "--no-include-stage63", "--skip-phase309"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn("stage63_realhw_lens_comp_af_illuminator_folder_rating_hil", data)
            self.assertFalse(data["config"]["include_stage63"])

    def test_66_suite_cli_help_and_summary_include_stage63(self) -> None:
        proc_help = subprocess.run(
            [sys.executable, "-B", str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_help.returncode, 0, proc_help.stderr)
        self.assertIn("--include-stage63", proc_help.stdout)
        self.assertIn("--skip-phase309", proc_help.stdout)
        self.assertIn("100%", proc_help.stdout)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--include-stage63", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_lens_comp_af_illuminator_folder_rating_hil=CLEAN_ROOM_SYNTHETIC",
            buf.getvalue(),
        )

    def test_67_no_raw_firmware_bytes_in_json_output(self) -> None:
        rep = p309.run_phase309_lens_comp_af_illuminator_folder_rating_coemulation()
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)


class TestWave53MatrixExtensions(unittest.TestCase):
    """Granular Wave-53 boundary and multi-condition assertions (tests 68..88)."""

    def test_68_fx3_jpeg_and_heif_bake_distortion_without_arw_bake(self) -> None:
        for fmt in (p309.CAPTURE_FMT_JPEG, p309.CAPTURE_FMT_HEIF):
            r = p309.simulate_lens_compensation_hil(
                capture_format=fmt,
                distortion_comp=p309.COMP_AUTO,
                shading_comp=p309.COMP_AUTO,
            )
            self.assertTrue(r.admitted)
            self.assertFalse(r.distortion_baked_into_arw_pixels)
            self.assertFalse(r.shading_applies_to_arw_gain)

    def test_69_fx3_breathing_comp_off_admitted_in_still_and_sq(self) -> None:
        for dom in (p309.DOMAIN_STILL, p309.DOMAIN_SQ):
            r = p309.simulate_lens_compensation_hil(
                shooting_domain=dom, breathing_comp=p309.COMP_OFF
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_breathing_comp, p309.COMP_OFF)

    def test_70_fx3_breathing_comp_rejected_for_incompatible_pz_le_lenses(self) -> None:
        for lens in p309.AF_ASSIST_INCOMPATIBLE_LENSES:
            r = p309.simulate_lens_compensation_hil(
                shooting_domain=p309.DOMAIN_MOVIE,
                lens_profile=lens,
                breathing_comp=p309.COMP_ON,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p309.EOPNOTSUPP_ERRNO)

    def test_71_fx3_steadyshot_standard_and_off_allow_distortion_off(self) -> None:
        for ss in (p309.STEADYSHOT_OFF, p309.STEADYSHOT_STANDARD):
            r = p309.simulate_lens_compensation_hil(
                shooting_domain=p309.DOMAIN_MOVIE,
                steadyshot_mode=ss,
                distortion_comp=p309.COMP_OFF,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_distortion_comp, p309.COMP_OFF)

    def test_72_fx3_initialize_overrides_forced_auto_error_path_safely(self) -> None:
        r = p309.simulate_lens_compensation_hil(
            lens_profile=p309.LENS_SELP1650,
            distortion_comp=p309.COMP_AUTO,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_distortion_comp, p309.COMP_AUTO)

    def test_73_fx6_distortion_off_without_breathing_admitted(self) -> None:
        r = p309.simulate_lens_compensation_hil(
            body_profile=p309.BODY_MODEL_FX6,
            distortion_comp=p309.COMP_OFF,
            breathing_comp=p309.COMP_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_distortion_comp, p309.COMP_OFF)

    def test_74_fx3_still_afs_without_external_flash_still_fires_led8(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            shooting_domain=p309.DOMAIN_STILL,
            focus_mode=p309.FOCUS_MODE_AFS,
            mishoe_flash_mounted=False,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.builtin_led8_fired)
        self.assertFalse(r.mishoe_flash_af_illuminator_fired)

    def test_75_fx3_af_transition_speed_and_shift_sens_full_valid_ranges(self) -> None:
        for spd in range(1, 8):
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_MOVIE, af_transition_speed=spd
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_af_transition_speed, spd)
        for sens in range(1, 6):
            r = p309.simulate_af_illuminator_and_kinematics_hil(
                shooting_domain=p309.DOMAIN_SQ, af_subj_shift_sens=sens
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_af_subj_shift_sens, sens)

    def test_76_sq_afc_allows_af_assist_on_with_compatible_lens(self) -> None:
        r = p309.simulate_af_illuminator_and_kinematics_hil(
            shooting_domain=p309.DOMAIN_SQ,
            focus_mode=p309.FOCUS_MODE_AFC,
            af_assist_on=True,
            lens_profile=p309.LENS_FE_2470GM2,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.effective_af_assist_on)
        self.assertFalse(r.builtin_led8_fired)

    def test_77_circ_of_focus_point_right_and_bottom_edge_orthogonal_wrap(self) -> None:
        r_right = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area=p309.FOCUS_AREA_SPOT_L,
            step_from_x=14,
            step_from_y=3,
            step_dx=1,
            step_dy=0,
        )
        self.assertTrue(r_right.admitted)
        self.assertEqual((r_right.step_to_x, r_right.step_to_y), (0, 3))
        self.assertTrue(r_right.orthogonal_wrap_occurred)

        r_bot = p309.simulate_af_behavior_initialize_persistence_hil(
            circ_of_focus_point=p309.CIRC_CIRCULATE,
            focus_area=p309.FOCUS_AREA_EXPAND_SPOT,
            step_from_x=4,
            step_from_y=10,
            step_dx=0,
            step_dy=1,
        )
        self.assertTrue(r_bot.admitted)
        self.assertEqual((r_bot.step_to_x, r_bot.step_to_y), (4, 0))
        self.assertTrue(r_bot.orthogonal_wrap_occurred)

    def test_78_circ_of_focus_point_and_color_allowed_in_movie_and_sq(self) -> None:
        for dom in (p309.DOMAIN_MOVIE, p309.DOMAIN_SQ):
            r = p309.simulate_af_behavior_initialize_persistence_hil(
                shooting_domain=dom,
                circ_of_focus_point=p309.CIRC_CIRCULATE,
                focus_area_color=p309.FOCUS_AREA_COLOR_RED,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_circ_of_focus_point, p309.CIRC_CIRCULATE)
            self.assertEqual(r.effective_focus_area_color, p309.FOCUS_AREA_COLOR_RED)

    def test_79_invalid_legacy_name_and_circ_coords_rejected_einval(self) -> None:
        self.assertEqual(
            p309.simulate_af_behavior_initialize_persistence_hil(
                requested_legacy_name="Unknown Label"
            ).errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_af_behavior_initialize_persistence_hil(step_from_x=99).errno_code,
            p309.EINVAL_ERRNO,
        )

    def test_80_slot2_select_rec_folder_and_date_form_create_folder(self) -> None:
        r_sel = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SELECT_REC_FOLDER,
            target_slot=p309.SLOT_2,
            slot2_max_folder_num=105,
        )
        self.assertTrue(r_sel.admitted)
        self.assertEqual(r_sel.allocated_folder_name, "DCIM/105MSDCF")

        r_df_new = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_CREATE_NEW_FOLDER,
            target_slot=p309.SLOT_2,
            folder_name_style=p309.FOLDER_STYLE_DATE,
            slot2_max_folder_num=105,
        )
        self.assertTrue(r_df_new.admitted)
        self.assertEqual(r_df_new.allocated_folder_name, "DCIM/10621117")

    def test_81_slot2_clear_rating_0_stars_and_shooting_add_rating_ok(self) -> None:
        r_clr = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_PLAYBACK_RATING,
            target_slot=p309.SLOT_2,
            existing_rating_stars=4,
            requested_rating_stars=0,
        )
        self.assertTrue(r_clr.admitted)
        self.assertEqual(r_clr.effective_rating_stars, 0)

        r_add = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_SHOOTING_ADD_RATING,
            target_slot=p309.SLOT_2,
            existing_rating_stars=0,
            requested_rating_stars=5,
        )
        self.assertTrue(r_add.admitted)
        self.assertEqual(r_add.effective_rating_stars, 5)

    def test_82_folder_settings_reset_only_on_initialize(self) -> None:
        r_init = p309.simulate_folder_and_rating_vault_firewall_hil(
            file_name_prefix="A1_",
            folder_name_style=p309.FOLDER_STYLE_DATE,
            file_number_mode=p309.FILE_NUMBER_RESET,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_file_name_prefix, "DSC")
        self.assertEqual(r_init.effective_folder_name_style, p309.FOLDER_STYLE_STANDARD)
        self.assertEqual(r_init.effective_file_number_mode, p309.FILE_NUMBER_SERIES)

    def test_83_invalid_slot_prefix_and_stars_rejected_einval(self) -> None:
        self.assertEqual(
            p309.simulate_folder_and_rating_vault_firewall_hil(target_slot="Slot 3").errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_folder_and_rating_vault_firewall_hil(file_name_prefix="ABCD").errno_code,
            p309.EINVAL_ERRNO,
        )
        self.assertEqual(
            p309.simulate_folder_and_rating_vault_firewall_hil(requested_rating_stars=6).errno_code,
            p309.EINVAL_ERRNO,
        )

    def test_84_write_protected_slot2_rating_blocked_erofs(self) -> None:
        r = p309.simulate_folder_and_rating_vault_firewall_hil(
            operation=p309.OP_PLAYBACK_RATING,
            target_slot=p309.SLOT_2,
            card_write_protected=True,
            requested_rating_stars=2,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p309.EROFS_ERRNO)

    def test_85_no_legacy_bin_python3_hardcoded_in_new_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_lens_comp_af_illuminator_folder_rating_coemulator.py"
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
        self.assertIn("s1_wr=0", proc.stdout)
        self.assertIn("s1_mut=0", proc.stdout)

    def test_87_stage63_payload_keys_present_and_complete(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        s63 = rep["stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"]
        for key in (
            "pillar_a_lens_comp_shading_auto_off_and_active_lock_hil",
            "pillar_b_builtin_af_illuminator_led8_vs_zero_led_fx6_hil",
            "pillar_c_af_behavior_initialize_only_persistence_hil",
            "pillar_d_create_folder_rating_slot1_vault_and_redlines",
            "phase309_audit_digest_sha256",
            "donor_audit",
        ):
            self.assertIn(key, s63)

    def test_88_stage63_config_serialization_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        cfg = rep["config"]
        self.assertTrue(cfg["include_phase309_realhw_lens_comp_af_illuminator_folder_rating_hil"])
        self.assertTrue(cfg["include_stage63"])
        self.assertTrue(cfg["stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"])


if __name__ == "__main__":
    unittest.main()
