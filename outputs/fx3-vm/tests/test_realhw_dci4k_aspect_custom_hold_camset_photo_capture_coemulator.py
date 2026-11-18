#!/usr/bin/env python3
"""Unit tests for Phase 301 (Stage 61 — 61/61 VM Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-51
`[XAVC S-I DCI 4K]` (4096x2160 17:9) + `24.00p` Reboot & Slot-1 Tier-0 Vault Quarantine,
Still `[Aspect Ratio]` (`3:2`/`4:3`/`16:9`/`1:1`) vs Movie/S&Q Format-Driven Aspect Lock,
`[Reg. Custom Shoot Set]` 11 Hold Checkboxes (`is_checked_recall_custom_hold0..10`) + `AF On`
& `[Recall Custom hold 1..3]` vs `Cine EI` `Exposure Comp.` Masking,
`%c:%s/SONY/SETTING/%s/` (`CAMPR%02d%c.DAT` `M1..M4` & `CAMSET01..10.DAT`) Path Isolation
with Cross-Model FX6 Import Firewall & Slot-1 Tier-0 Vault Fail-Closed `EROFS`/`EBUSY`,
and `[Photo Capture]` (`8.3M` / `2.1M`) DCI 4K Lockout (`0x60ce`) + `[Enlarge Image]` HIL
Co-Emulator (84 dual-mode tests).
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
import realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator as p301  # noqa: E402

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
        include_stage60=False,
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
]


class TestPhase301Stage61Wave51HilCoEmulator(unittest.TestCase):
    """84 dual-mode tests for Phase 301 Stage 61 (61/61 VM Stages Milestone)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_audit = p301.run_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil()
        cls.clean_audit = p301.run_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil(
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
    # Group 1: Dual-Mode 11-Donor O_RDONLY Audit & Clean-Room Parity (12 tests)
    # ------------------------------------------------------------------
    def test_01_top_level_schema_stage61_milestone_and_flags(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            self.assertEqual(rep["schema"], p301.PHASE_301_SCHEMA)
            self.assertEqual(rep["version"], p301.PHASE_301_VERSION)
            self.assertEqual(rep["phase_number"], 301)
            self.assertEqual(rep["stage_index"], 61)
            self.assertEqual(rep["stage_total"], 61)
            self.assertEqual(rep["milestone"], "61/61")
            self.assertEqual(rep["stage"], p301.STAGE_NAME)
            self.assertTrue(rep["is_61st_stage_milestone"])
            self.assertTrue(rep["all_checks_passed"])

    def test_02_source_mode_selection_local_vs_env_clean_room_flags(self) -> None:
        self.assertEqual(self.clean_audit["source_mode"], p301.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.default_audit["donor_audit"]["access_mode"], "O_RDONLY")
        rep_cr = p301.run_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil(
            env={p301.ENV_CLEAN_ROOM_TEST: "1"}
        )
        rep_fc = p301.run_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil(
            env={p301.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(rep_cr["source_mode"], p301.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep_fc["source_mode"], p301.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep_cr["audit_digest_sha256"], rep_fc["audit_digest_sha256"])

    def test_03_eleven_donor_contracts_verified_and_strict_o_rdonly(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["donor_files_inspected"], 11)
            self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(da["all_contracts_verified"])
            self.assertEqual(len(da["errors"]), 0)
            self.assertTrue(da["dci4k_and_aspect_proven"])
            self.assertTrue(da["custom_hold_and_camset_paths_proven"])
            self.assertTrue(da["photo_capture_and_enlarge_proven"])

    def test_04_bounded_windows_prevent_full_read_of_multi_megabyte_donors(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            fx3_elf = da["fx3_appfw"]
            fx6_elf = da["fx6_appfw"]
            fx3_bk4 = da["fx3_bk4"]
            self.assertTrue(fx3_elf["bounded_windows_only"])
            self.assertTrue(fx3_elf["elf64_le_ok"])
            self.assertLess(fx3_elf["bytes_read_total"], 100_000)
            self.assertEqual(fx3_elf["file_bytes"], 79_015_712)
            self.assertTrue(fx6_elf["bounded_windows_only"])
            self.assertTrue(fx6_elf["elf64_le_ok"])
            self.assertLess(fx6_elf["bytes_read_total"], 40_000)
            self.assertEqual(fx6_elf["file_bytes"], 50_520_424)
            self.assertTrue(fx3_bk4["bounded_windows_only"])
            self.assertLessEqual(fx3_bk4["bytes_read_total"], 16_384)
            self.assertEqual(fx3_bk4["file_bytes"], 2_229_740)

    def test_05_eight_compact_string_packs_all_marker_hits_and_sha256_match(self) -> None:
        keys = (
            "fx3_string_en_f",
            "fx3_string_sc_f",
            "fx3_string_tc_f",
            "fx3_string_ja_f",
            "fx3_string_en",
            "fx3_string_en_g",
            "fx6_string_en",
            "fx6_string_en_2",
        )
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            for k in keys:
                item = da[k]
                self.assertTrue(item["uxd_container_ok"], msg=k)
                self.assertTrue(item["sha256_verified"], msg=k)
                self.assertTrue(all(v == 1 for v in item["marker_hits"].values()), msg=k)

    def test_06_clean_room_deterministic_digest_and_elapsed_budget(self) -> None:
        rep2 = p301.run_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil(
            force_clean_room=True
        )
        self.assertEqual(self.clean_audit["audit_digest_sha256"], rep2["audit_digest_sha256"])
        max_s = 15.0 if IS_CI else 2.0
        self.assertLess(self.default_audit["donor_audit"]["inspection_elapsed_s"], max_s)

    def test_07_zero_raw_firmware_bytes_leaked_and_hardware_flags_locked_false(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            red = rep["redlines"]
            self.assertTrue(red["p8_cp_mutation_forbidden"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertFalse(red["fx3_pro_camera_path_exposed"])
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(red["physical_device_writes"], 0)

    def test_08_large_donor_tokens_dci4k_hold_camset_photocapture_all_hit(self) -> None:
        da = self.default_audit["donor_audit"]
        fx3_hits = da["fx3_appfw"]["window_hits"]
        fx6_hits = da["fx6_appfw"]["window_hits"]
        for tok in (
            "BKID_DCI4K_FRAME_RATE",
            "VAL_MOVIE_XAVC_SI_DCI_4K_24_00P",
            "VAL_HAITA_MOVIE_ASPECT_NOT_16_9",
            "IS_CHECKED_RECALL_CUSTOM_HOLD0",
            "IS_CHECKED_RECALL_CUSTOM_HOLD10",
            "FX3_CAMSET_PATH",
            "FX3_CAMPR_PATH",
            "ENTER_PHOTO_CAPTURE_MODE",
            "BKID_PHOTO_CAPTURE_FILE_TYPE",
        ):
            self.assertEqual(fx3_hits[tok], 1, msg=tok)
        for tok in (
            "FX6_EXTERN_DCI_4K_REC_FRAME_RATE",
            "FX6_PRO_CAMERA_PATH",
            "FX6_PRO_SCENE_PATH",
            "FX6_MARKER_CUSTOM_ASPECT_WIDTH",
            "FX6_ALL_FILE0",
        ):
            self.assertEqual(fx6_hits[tok], 1, msg=tok)

    def test_09_clean_room_and_local_donor_pillars_match_identically(self) -> None:
        for pk in (
            "pillar_a_dci4k_24p_quarantine_and_aspect_hil",
            "pillar_b_custom_hold_and_camset_path_hil",
            "pillar_c_d_photo_capture_enlarge_and_redlines",
        ):
            self.assertEqual(self.default_audit[pk], self.clean_audit[pk], msg=pk)

    def test_10_fx3_en_g_quarantine_and_dci4k_photo_capture_message_tokens(self) -> None:
        hits = self.default_audit["donor_audit"]["fx3_string_en_g"]["marker_hits"]
        self.assertEqual(hits['set to "XAVC S-I DCI 4K"'], 1)
        self.assertEqual(hits["24.00p cannot be played back"], 1)

    def test_11_resolve_mac_work_root_honors_env_overrides(self) -> None:
        custom_root = str(REPO_ROOT / "work")
        self.assertEqual(
            p301.resolve_mac_work_root(env={p301.ENV_MAC_WORK_ROOT: custom_root}),
            Path(custom_root),
        )
        self.assertEqual(
            p301.resolve_mac_work_root(env={p301.ENV_MAIN_LAB_WORK_ROOT: custom_root}),
            Path(custom_root),
        )
        self.assertEqual(
            p301.resolve_mac_work_root(env={p301.ENV_MAC_ROOT: "/tmp/mock_mac"}),
            Path("/tmp/mock_mac/work"),
        )

    def test_12_inspect_phase301_donors_is_forced_clean_room_env_parsing(self) -> None:
        self.assertTrue(p301.is_forced_clean_room({p301.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p301.is_forced_clean_room({p301.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertFalse(p301.is_forced_clean_room({p301.ENV_CLEAN_ROOM_TEST: "0"}))
        da = p301.inspect_phase301_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, p301.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(da.all_contracts_verified)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 61A — XAVC S-I DCI 4K, 24.00p Quarantine, & Still Aspect Ratio (22 tests)
    # ------------------------------------------------------------------
    def test_13_fx3_xavc_si_dci4k_all_6_frame_rates_and_bitrates(self) -> None:
        expected = {
            "59.94p": 600,
            "50p": 500,
            "29.97p": 300,
            "25p": 250,
            "24.00p": 240,
            "23.98p": 240,
        }
        for fps, mbps in expected.items():
            r = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate=fps,
                previous_frame_rate=fps,
                media_speed_grade=p301.CARD_MEDIA_CFEXPRESS_VPG200,
            )
            self.assertTrue(r.admitted, msg=fps)
            self.assertEqual(r.output_width, 4096, msg=fps)
            self.assertEqual(r.output_height, 2160, msg=fps)
            self.assertEqual(r.aspect_ratio, "17:9", msg=fps)
            self.assertEqual(r.bitrate_mbps, mbps, msg=fps)
            self.assertEqual(r.codec_family, "MP4_XAVC_S_I_DCI_4K_ALL_INTRA_422_10BIT")

    def test_14_fx3_dci4k_no_100p_or_120p_eopnotsupp(self) -> None:
        for fps in ("100p", "119.88p", "120p"):
            r = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate=fps,
            )
            self.assertFalse(r.admitted, msg=fps)
            self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO, msg=fps)
            self.assertEqual(r.reason_code, "FX3_XAVC_SI_DCI4K_NO_100P_120P")

    def test_15_fx3_dci4k_sq_valid_1_to_48fps_and_rejects_above_48fps(self) -> None:
        for sq in (1, 2, 3, 6, 12, 24, 48):
            r = p301.simulate_dci4k_24p_quarantine_hil(
                shooting_domain=p301.EXPOSURE_MODE_SQ,
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate="24.00p",
                previous_frame_rate="24.00p",
                sq_fps=sq,
            )
            self.assertTrue(r.admitted, msg=sq)
            self.assertEqual(r.output_width, 4096)
        for bad_sq in (60, 100, 120):
            r = p301.simulate_dci4k_24p_quarantine_hil(
                shooting_domain=p301.EXPOSURE_MODE_SQ,
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate="24.00p",
                sq_fps=bad_sq,
            )
            self.assertFalse(r.admitted, msg=bad_sq)
            self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_16_fx3_dci4k_500m_600m_requires_vpg200_or_v90_rejects_v60_v30(self) -> None:
        for ok_media in (
            p301.CARD_MEDIA_CFEXPRESS_VPG200,
            p301.CARD_MEDIA_CFEXPRESS_VPG400,
            p301.CARD_MEDIA_SDXC_V90,
            p301.CARD_MEDIA_SDHC_32GB_V90,
        ):
            r = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate="59.94p",
                previous_frame_rate="59.94p",
                media_speed_grade=ok_media,
            )
            self.assertTrue(r.admitted, msg=ok_media)
        for slow_media in (p301.CARD_MEDIA_SDXC_V60, p301.CARD_MEDIA_SDXC_V30):
            r = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                frame_rate="59.94p",
                previous_frame_rate="59.94p",
                media_speed_grade=slow_media,
            )
            self.assertFalse(r.admitted, msg=slow_media)
            self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_17_fx3_dci4k_240m_at_2398p_or_2400p_allows_v60(self) -> None:
        r = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="23.98p",
            previous_frame_rate="23.98p",
            media_speed_grade=p301.CARD_MEDIA_SDXC_V60,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.bitrate_mbps, 240)

    def test_18_fx3_longgop_and_si4k_strictly_uhd_3840x2160_16_9_no_24_00p(self) -> None:
        for fmt in (
            p301.FILE_FORMAT_XAVC_HS_4K,
            p301.FILE_FORMAT_XAVC_S_4K,
            p301.FILE_FORMAT_XAVC_SI_4K,
        ):
            ok = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=fmt,
                frame_rate="59.94p",
                previous_frame_rate="59.94p",
            )
            self.assertTrue(ok.admitted, msg=fmt)
            self.assertEqual(ok.output_width, 3840, msg=fmt)
            self.assertEqual(ok.output_height, 2160, msg=fmt)
            self.assertEqual(ok.aspect_ratio, "16:9", msg=fmt)
            bad24 = p301.simulate_dci4k_24p_quarantine_hil(
                file_format=fmt,
                frame_rate="24.00p",
            )
            self.assertFalse(bad24.admitted, msg=fmt)
            self.assertEqual(bad24.errno_code, p301.EOPNOTSUPP_ERRNO, msg=fmt)

    def test_19_fx3_24_00p_enter_exit_and_ntsc_pal_toggle_require_reboot_and_quarantine(self) -> None:
        enter_24 = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="24.00p",
            previous_frame_rate="23.98p",
        )
        self.assertTrue(enter_24.admitted)
        self.assertTrue(enter_24.reboot_required)
        self.assertTrue(enter_24.playback_quarantine_24_00p_active)

        exit_24 = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="23.98p",
            previous_frame_rate="24.00p",
        )
        self.assertTrue(exit_24.admitted)
        self.assertTrue(exit_24.reboot_required)
        self.assertFalse(exit_24.playback_quarantine_24_00p_active)

        ntsc_pal = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="50p",
            previous_frame_rate="59.94p",
            video_system=p301.VIDEO_SYSTEM_PAL,
            previous_video_system=p301.VIDEO_SYSTEM_NTSC,
        )
        self.assertTrue(ntsc_pal.admitted)
        self.assertTrue(ntsc_pal.reboot_required)

    def test_20_reboot_24_00p_blocks_card_reinit_on_slot1_vault_and_unverified_cards(self) -> None:
        vault_blk = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="24.00p",
            previous_frame_rate="23.98p",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
            card_reinit_requested=True,
        )
        self.assertFalse(vault_blk.admitted)
        self.assertEqual(vault_blk.errno_code, p301.EROFS_ERRNO)
        self.assertTrue(vault_blk.card_reinit_blocked)
        self.assertTrue(vault_blk.reboot_required)
        self.assertEqual(vault_blk.physical_device_writes, 0)

        unver_blk = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="24.00p",
            target_slot=p301.SLOT_2,
            slot1_is_tier0_vault=True,
            card_verified=False,
            card_reinit_requested=True,
        )
        self.assertFalse(unver_blk.admitted)
        self.assertEqual(unver_blk.errno_code, p301.EROFS_ERRNO)
        self.assertTrue(unver_blk.card_reinit_blocked)

    def test_21_slot2_verified_scratch_card_allows_24_00p_reinit_without_touching_hw(self) -> None:
        r = p301.simulate_dci4k_24p_quarantine_hil(
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="24.00p",
            previous_frame_rate="23.98p",
            target_slot=p301.SLOT_2,
            slot1_is_tier0_vault=True,
            card_verified=True,
            card_reinit_requested=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.card_reinit_blocked)
        self.assertEqual(r.physical_device_writes, 0)

    def test_22_fx3_hdmi_raw_outputs_4264x2408_16_9_with_log_only(self) -> None:
        rejected = p301.simulate_dci4k_24p_quarantine_hil(
            hdmi_raw_output=True,
            log_shooting_mode=p301.LOG_SHOOTING_OFF,
        )
        self.assertFalse(rejected.admitted)
        self.assertEqual(rejected.errno_code, p301.EOPNOTSUPP_ERRNO)

        admitted = p301.simulate_dci4k_24p_quarantine_hil(
            hdmi_raw_output=True,
            log_shooting_mode=p301.LOG_SHOOTING_CINE_EI,
            frame_rate="24.00p",
            previous_frame_rate="24.00p",
        )
        self.assertTrue(admitted.admitted)
        self.assertEqual(admitted.output_width, 4264)
        self.assertEqual(admitted.output_height, 2408)
        self.assertEqual(admitted.aspect_ratio, "16:9")
        self.assertFalse(admitted.steadyshot_active_allowed)
        self.assertFalse(admitted.desqueeze_display_allowed)

    def test_23_fx3_rejects_fx6_mxf_wrapper_while_fx6_allows_mxf_dci4k_120p(self) -> None:
        fx3_mxf = p301.simulate_dci4k_24p_quarantine_hil(
            body_profile=p301.BODY_MODEL_FX3,
            file_format=p301.FX6_FILE_FORMAT_MXF_XAVC_I_DCI_4K,
        )
        self.assertFalse(fx3_mxf.admitted)
        self.assertEqual(fx3_mxf.errno_code, p301.EOPNOTSUPP_ERRNO)

        fx6_mxf = p301.simulate_dci4k_24p_quarantine_hil(
            body_profile=p301.BODY_MODEL_FX6,
            shooting_domain=p301.EXPOSURE_MODE_SQ,
            file_format=p301.FX6_FILE_FORMAT_MXF_XAVC_I_DCI_4K,
            frame_rate="59.94p",
            sq_fps=120,
        )
        self.assertTrue(fx6_mxf.admitted)
        self.assertEqual(fx6_mxf.output_width, 4096)
        self.assertEqual(fx6_mxf.aspect_ratio, "17:9")
        self.assertFalse(fx6_mxf.reboot_required)
        self.assertFalse(fx6_mxf.playback_quarantine_24_00p_active)

    def test_24_fx3a_body_parity_on_dci4k_and_24_00p_quarantine(self) -> None:
        r = p301.simulate_dci4k_24p_quarantine_hil(
            body_profile=p301.BODY_MODEL_FX3A,
            file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            frame_rate="24.00p",
            previous_frame_rate="23.98p",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.reboot_required)
        self.assertTrue(r.playback_quarantine_24_00p_active)
        self.assertEqual(r.output_width, 4096)

    def test_25_still_aspect_ratio_all_4_ratios_and_sizes(self) -> None:
        expected_l = {
            "3:2": (4240, 2832, "12M"),
            "4:3": (3776, 2832, "11M"),
            "16:9": (4240, 2384, "10M"),
            "1:1": (2832, 2832, "8.0M"),
        }
        for ar, (w, h, mp) in expected_l.items():
            r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
                shooting_domain=p301.EXPOSURE_MODE_STILL,
                requested_still_aspect=ar,
                requested_still_size=p301.STILL_SIZE_L,
            )
            self.assertTrue(r.admitted, msg=ar)
            self.assertEqual(r.effective_aspect_ratio, ar, msg=ar)
            self.assertEqual((r.output_width, r.output_height, r.megapixels_label), (w, h, mp))
            self.assertFalse(r.movie_aspect_locked_by_format)

    def test_26_still_raw_retains_full_3_2_pixels_with_aspect_crop_metadata(self) -> None:
        for ar in p301.VALID_STILL_ASPECT_RATIOS:
            r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
                shooting_domain=p301.EXPOSURE_MODE_STILL,
                requested_still_aspect=ar,
                still_raw_enabled=True,
            )
            self.assertTrue(r.admitted, msg=ar)
            self.assertTrue(r.raw_retains_full_3_2_pixels, msg=ar)
            self.assertEqual(r.raw_aspect_crop_metadata, ar, msg=ar)

    def test_27_still_apsc_s35_steps_large_to_medium(self) -> None:
        r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            shooting_domain=p301.EXPOSURE_MODE_STILL,
            requested_still_aspect="16:9",
            requested_still_size=p301.STILL_SIZE_L,
            apsc_s35_on=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_still_size, p301.STILL_SIZE_M)
        self.assertEqual((r.output_width, r.output_height, r.megapixels_label), (2768, 1560, "4.3M"))

    def test_28_movie_and_sq_lock_out_still_aspect_ratio_changes_eperm(self) -> None:
        for dom in (p301.EXPOSURE_MODE_MOVIE, p301.EXPOSURE_MODE_SQ):
            r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
                shooting_domain=dom,
                movie_file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                requested_still_aspect="3:2",
                still_aspect_change_requested=True,
            )
            self.assertFalse(r.admitted, msg=dom)
            self.assertEqual(r.errno_code, p301.EPERM_ERRNO, msg=dom)
            self.assertEqual(r.effective_aspect_ratio, "17:9", msg=dom)
            self.assertTrue(r.movie_aspect_locked_by_format, msg=dom)

    def test_29_movie_aspect_follows_file_format_17_9_vs_16_9(self) -> None:
        dci = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            shooting_domain=p301.EXPOSURE_MODE_MOVIE,
            movie_file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
        )
        uhd = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            shooting_domain=p301.EXPOSURE_MODE_MOVIE,
            movie_file_format=p301.FILE_FORMAT_XAVC_HS_4K,
        )
        fhd = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            shooting_domain=p301.EXPOSURE_MODE_MOVIE,
            movie_file_format=p301.FILE_FORMAT_XAVC_SI_HD,
        )
        self.assertEqual((dci.effective_aspect_ratio, dci.output_width, dci.output_height), ("17:9", 4096, 2160))
        self.assertEqual((uhd.effective_aspect_ratio, uhd.output_width, uhd.output_height), ("16:9", 3840, 2160))
        self.assertEqual((fhd.effective_aspect_ratio, fhd.output_width, fhd.output_height), ("16:9", 1920, 1080))

    def test_30_still_aspect_resets_to_3_2_on_camera_settings_reset_and_initialize(self) -> None:
        for act in (p301.RESET_ACTION_CAMERA_SETTINGS_RESET, p301.RESET_ACTION_INITIALIZE):
            r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
                shooting_domain=p301.EXPOSURE_MODE_STILL,
                requested_still_aspect="1:1",
                requested_still_size="S",
                reset_action=act,
            )
            self.assertTrue(r.admitted, msg=act)
            self.assertEqual(r.effective_aspect_ratio, "3:2", msg=act)
            self.assertEqual(r.effective_still_size, "L", msg=act)

    def test_31_fx6_still_aspect_blocked_and_movie_custom_marker_supported(self) -> None:
        blk = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            body_profile=p301.BODY_MODEL_FX6,
            shooting_domain=p301.EXPOSURE_MODE_STILL,
            still_aspect_change_requested=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p301.EOPNOTSUPP_ERRNO)

        ok = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(
            body_profile=p301.BODY_MODEL_FX6,
            shooting_domain=p301.EXPOSURE_MODE_MOVIE,
            movie_file_format=p301.FX6_FILE_FORMAT_MXF_XAVC_I_DCI_4K,
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.fx6_custom_aspect_marker_supported)
        self.assertEqual(ok.effective_aspect_ratio, "17:9")

    def test_32_dci4k_quarantine_rejects_invalid_inputs_with_einval(self) -> None:
        for bad in (
            {"body_profile": "ILME-FX9"},
            {"shooting_domain": "UNKNOWN_DOMAIN"},
            {"file_format": "PRORES_RAW_INT"},
            {"video_system": "SECAM"},
            {"media_speed_grade": "UHS_I_CLASS4"},
            {"target_slot": "Slot 3"},
            {"log_shooting_mode": "S-Log2"},
            {"sq_fps": 0},
            {"sq_fps": True},
        ):
            r = p301.simulate_dci4k_24p_quarantine_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=str(bad))

    def test_33_aspect_ratio_rejects_invalid_inputs_with_einval(self) -> None:
        for bad in (
            {"body_profile": "ILME-FX30"},
            {"shooting_domain": "INVALID"},
            {"movie_file_format": "BAD_FMT"},
            {"requested_still_aspect": "2.39:1"},
            {"requested_still_size": "XL"},
            {"reset_action": "Reboot"},
        ):
            r = p301.simulate_still_aspect_ratio_vs_movie_lock_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=str(bad))

    def test_34_pillar_a_dict_passed_and_contains_all_sub_audits(self) -> None:
        pa = self.default_audit["pillar_a_dci4k_24p_quarantine_and_aspect_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["still_aspect_4_matrix"]), 4)
        self.assertEqual(len(pa["fx3_dci4k_frame_rate_bitrates_mbps"]), 6)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 61B — [Reg. Custom Shoot Set] 11 Hold Checkboxes & /SONY/SETTING/%s/ CAMSET/M1..M4 (23 tests)
    # ------------------------------------------------------------------
    def test_35_all_11_hold_checkbox_keys_labels_and_appfw_bkids(self) -> None:
        self.assertEqual(len(p301.HOLD_CHECKBOX_KEYS), 11)
        self.assertEqual(len(p301.HOLD_CHECKBOX_LABELS), 11)
        self.assertEqual(len(p301.FX3_APPFW_REGISTRATION_BKIDS), 11)
        self.assertEqual(p301.HOLD_CHECKBOX_KEYS[0], "is_checked_recall_custom_hold0")
        self.assertEqual(p301.HOLD_CHECKBOX_KEYS[-1], "is_checked_recall_custom_hold10")

    def test_36_recall_custom_hold_1_2_3_pressed_and_af_on_toggle(self) -> None:
        for idx in (1, 2, 3):
            r = p301.simulate_reg_custom_shoot_set_hold_hil(
                hold_index=idx,
                hold_pressed=True,
                af_on_toggle=True,
            )
            self.assertTrue(r.admitted, msg=idx)
            self.assertEqual(len(r.checkbox_mask), 11)
            self.assertTrue(all(r.checkbox_mask))
            self.assertEqual(r.effective_settings["Shooting Mode"], "S")
            self.assertEqual(r.effective_settings["Aperture"], "F2.8")
            self.assertEqual(r.effective_settings["Shutter Speed"], "1/1000")
            self.assertEqual(r.effective_settings["Focus Area"], "Tracking: Spot S")
            self.assertTrue(r.effective_settings["AF On"])
            self.assertTrue(r.hlg_still_forced_off_while_held)
            self.assertEqual(r.effective_settings["HLG Still Image"], p301.TOGGLE_OFF)

    def test_37_release_restores_baseline_settings_and_unmasked_checkboxes_keep_base(self) -> None:
        rel = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=1,
            hold_pressed=False,
        )
        self.assertTrue(rel.admitted)
        self.assertTrue(rel.baseline_restored_on_release)
        self.assertEqual(rel.effective_settings["Aperture"], "F4.0")
        self.assertEqual(rel.effective_settings["Shutter Speed"], "1/125")
        self.assertEqual(rel.effective_settings["HLG Still Image"], p301.TOGGLE_ON)

        partial = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=2,
            hold_pressed=True,
            checkbox_overrides={
                "is_checked_recall_custom_hold1": False,
                "is_checked_recall_custom_hold5": False,
            },
        )
        self.assertTrue(partial.admitted)
        self.assertEqual(partial.effective_settings["Aperture"], "F4.0")
        self.assertEqual(partial.effective_settings["ISO"], 800)
        self.assertEqual(partial.effective_settings["Shutter Speed"], "1/1000")
        self.assertFalse(partial.hlg_still_forced_off_while_held)

    def test_38_out_of_range_or_bool_hold_indices_rejected_einval(self) -> None:
        for bad_idx in (0, -1, 4, 99, True, False):
            r = p301.simulate_reg_custom_shoot_set_hold_hil(hold_index=bad_idx)  # type: ignore[arg-type]
            self.assertFalse(r.admitted, msg=repr(bad_idx))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=repr(bad_idx))

    def test_39_unknown_checkbox_key_rejected_einval(self) -> None:
        r = p301.simulate_reg_custom_shoot_set_hold_hil(
            checkbox_overrides={"is_checked_recall_custom_hold11": True}
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p301.EINVAL_ERRNO)
        self.assertEqual(r.reason_code, "UNKNOWN_CUSTOM_HOLD_CHECKBOX_KEY")

    def test_40_self_timer_excluded_from_reg_custom_shoot_set_einval(self) -> None:
        r = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=1,
            hold_pressed=True,
            hold_settings={"Drive Mode": p301.DRIVE_MODE_SELF_TIMER},
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p301.EINVAL_ERRNO)
        self.assertEqual(r.reason_code, "SELF_TIMER_EXCLUDED_FROM_REG_CUSTOM_SHOOT_SET")

    def test_41_dro_bracket_hold_also_forces_hlg_still_off(self) -> None:
        r = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=1,
            hold_pressed=True,
            checkbox_overrides={"is_checked_recall_custom_hold5": False},
            hold_settings={"Drive Mode": p301.DRIVE_MODE_DRO_BRACKET},
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.hlg_still_forced_off_while_held)
        self.assertEqual(r.effective_settings["HLG Still Image"], p301.TOGGLE_OFF)

    def test_42_non_still_domains_and_fx6_reject_reg_custom_shoot_set_eopnotsupp(self) -> None:
        for dom in (p301.EXPOSURE_MODE_MOVIE, p301.EXPOSURE_MODE_SQ, p301.EXPOSURE_MODE_IAUTO):
            r = p301.simulate_reg_custom_shoot_set_hold_hil(shooting_domain=dom)
            self.assertFalse(r.admitted, msg=dom)
            self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO, msg=dom)
        fx6 = p301.simulate_reg_custom_shoot_set_hold_hil(body_profile=p301.BODY_MODEL_FX6)
        self.assertFalse(fx6.admitted)
        self.assertEqual(fx6.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_43_cine_ei_masks_exposure_comp_hold_and_blocks_explicit_bypass(self) -> None:
        for ei_mode in (p301.LOG_SHOOTING_CINE_EI, p301.LOG_SHOOTING_CINE_EI_QUICK):
            masked = p301.simulate_reg_custom_shoot_set_hold_hil(
                log_shooting_mode=ei_mode,
                hold_index=2,
                hold_pressed=True,
            )
            self.assertTrue(masked.admitted, msg=ei_mode)
            self.assertTrue(masked.exposure_comp_hold_masked_under_cine_ei, msg=ei_mode)
            self.assertEqual(masked.effective_settings["Exposure Comp."], "+0.0")

            bypass = p301.simulate_reg_custom_shoot_set_hold_hil(
                log_shooting_mode=ei_mode,
                hold_index=2,
                hold_pressed=True,
                explicit_cine_ei_exp_comp_bypass_requested=True,
            )
            self.assertFalse(bypass.admitted, msg=ei_mode)
            self.assertEqual(bypass.errno_code, p301.EOPNOTSUPP_ERRNO, msg=ei_mode)

    def test_44_reg_custom_shoot_set_survives_camera_reset_and_wiped_on_initialize(self) -> None:
        cam_rst = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=3,
            hold_pressed=True,
            reset_action=p301.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(cam_rst.admitted)
        self.assertTrue(cam_rst.registered_hold_survived_camera_reset)
        self.assertFalse(cam_rst.registered_hold_wiped_on_initialize)

        init_rst = p301.simulate_reg_custom_shoot_set_hold_hil(
            hold_index=3,
            hold_pressed=True,
            reset_action=p301.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(init_rst.admitted)
        self.assertTrue(init_rst.registered_hold_wiped_on_initialize)
        self.assertFalse(init_rst.registered_hold_survived_camera_reset)
        self.assertEqual(init_rst.effective_settings["Aperture"], "F4.0")

    def test_45_fx3_m1_m4_paths_on_cfexpress_and_sdxc_zero_pro_camera_path(self) -> None:
        cfex_m1 = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_MEMORY_BANK,
            bank_id="M1",
            target_slot=p301.SLOT_2,
            card_fs_type=p301.CARD_FS_CFEXPRESS,
        )
        self.assertTrue(cfex_m1.admitted)
        self.assertEqual(cfex_m1.resolved_fx3_setting_path, "B:/SONY/SETTING/FX3/CAMPR01B.DAT")
        self.assertFalse(cfex_m1.fx3_pro_camera_path_exposed)
        self.assertNotIn("PRO/CAMERA", cfex_m1.resolved_fx3_setting_path)

        sdxc_m4 = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_MEMORY_BANK,
            bank_id="M4",
            target_slot=p301.SLOT_2,
            card_fs_type=p301.CARD_FS_SDXC,
        )
        self.assertTrue(sdxc_m4.admitted)
        self.assertEqual(sdxc_m4.resolved_fx3_setting_path, "B:/PRIVATE/SONY/SETTING/FX3/CAMPR04B.DAT")
        self.assertFalse(sdxc_m4.fx3_pro_camera_path_exposed)

    def test_46_fx3_body_banks_1_to_3_and_recall_from_vault_read_only_allowed(self) -> None:
        for b in ("1", "2", "3"):
            r = p301.simulate_camset_memory_recall_path_hil(
                operation=p301.CAM_OP_SAVE_MEMORY_BANK,
                bank_id=b,
                target_slot=p301.SLOT_1,
                slot1_is_tier0_vault=True,
            )
            self.assertTrue(r.admitted, msg=b)
            self.assertEqual(r.resolved_fx3_setting_path, f"NVRAM://FX3/CAMERA_SET_MEMORY/BANK_{b}")

        recall_m1 = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_RECALL_MEMORY_BANK,
            bank_id="M1",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertTrue(recall_m1.admitted)
        self.assertEqual(recall_m1.resolved_fx3_setting_path, "A:/SONY/SETTING/FX3/CAMPR01A.DAT")

        load_camset = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_LOAD_CAMSET,
            camset_filename="CAMSET10.DAT",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertTrue(load_camset.admitted)
        self.assertEqual(load_camset.resolved_fx3_setting_path, "A:/SONY/SETTING/FX3/CAMSET/CAMSET10.DAT")

    def test_47_slot1_tier0_vault_blocks_camset_save_with_erofs_or_ebusy(self) -> None:
        ro = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_CAMSET,
            camset_filename="CAMSET01.DAT",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
            vault_busy=False,
        )
        self.assertFalse(ro.admitted)
        self.assertEqual(ro.errno_code, p301.EROFS_ERRNO)
        self.assertTrue(ro.slot1_vault_blocked)
        self.assertEqual(ro.physical_device_writes, 0)
        self.assertEqual(ro.emmc_nflasha_write_count, 0)

        busy = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_CAMSET,
            camset_filename="CAMSET02.DAT",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
            vault_busy=True,
        )
        self.assertFalse(busy.admitted)
        self.assertEqual(busy.errno_code, p301.EBUSY_ERRNO)
        self.assertTrue(busy.slot1_vault_blocked)

    def test_48_slot1_tier0_vault_blocks_m1_m4_save_and_card_format(self) -> None:
        for bank in ("M1", "M2", "M3", "M4"):
            r = p301.simulate_camset_memory_recall_path_hil(
                operation=p301.CAM_OP_SAVE_MEMORY_BANK,
                bank_id=bank,
                target_slot=p301.SLOT_1,
                slot1_is_tier0_vault=True,
            )
            self.assertFalse(r.admitted, msg=bank)
            self.assertEqual(r.errno_code, p301.EROFS_ERRNO, msg=bank)
            self.assertTrue(r.slot1_vault_blocked, msg=bank)

        fmt = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_RECALL_MEMORY_BANK,
            bank_id="M1",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
            reset_action=p301.RESET_ACTION_CARD_FORMAT,
        )
        self.assertFalse(fmt.admitted)
        self.assertEqual(fmt.errno_code, p301.EROFS_ERRNO)
        self.assertTrue(fmt.slot1_vault_blocked)

    def test_49_camset_all_10_filenames_admitted_on_non_vault_slot1_sdxc_and_cfex(self) -> None:
        for i in range(1, 11):
            fname = f"CAMSET{i:02d}.DAT"
            r = p301.simulate_camset_memory_recall_path_hil(
                operation=p301.CAM_OP_SAVE_CAMSET,
                camset_filename=fname,
                target_slot=p301.SLOT_1,
                card_fs_type=p301.CARD_FS_SDXC,
                slot1_is_tier0_vault=False,
            )
            self.assertTrue(r.admitted, msg=fname)
            self.assertEqual(r.resolved_fx3_setting_path, f"A:/PRIVATE/SONY/SETTING/FX3/CAMSET/{fname}")

    def test_50_camset_save_load_requires_slot1_and_blocked_in_mr_mode(self) -> None:
        slot2_bad = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_CAMSET,
            camset_filename="CAMSET01.DAT",
            target_slot=p301.SLOT_2,
            slot1_is_tier0_vault=False,
        )
        self.assertFalse(slot2_bad.admitted)
        self.assertEqual(slot2_bad.errno_code, p301.EINVAL_ERRNO)

        mr_bad = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_SAVE_CAMSET,
            camset_filename="CAMSET01.DAT",
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=False,
            in_mr_mode=True,
        )
        self.assertFalse(mr_bad.admitted)
        self.assertEqual(mr_bad.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_51_block_cross_model_fx6_camset_and_all_file_imports(self) -> None:
        cset = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_IMPORT_FX6_CAMSET,
            source_model=p301.BODY_MODEL_FX6,
        )
        self.assertFalse(cset.admitted)
        self.assertEqual(cset.errno_code, p301.EINVAL_ERRNO)
        self.assertTrue(cset.fx6_cross_model_import_blocked)

        allf = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_IMPORT_FX6_ALL_FILE,
            source_model=p301.BODY_MODEL_FX6,
        )
        self.assertFalse(allf.admitted)
        self.assertEqual(allf.errno_code, p301.EPERM_ERRNO)
        self.assertTrue(allf.fx6_cross_model_import_blocked)

        src_fx6 = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_LOAD_CAMSET,
            source_model=p301.BODY_MODEL_FX6,
        )
        self.assertFalse(src_fx6.admitted)
        self.assertTrue(src_fx6.fx6_cross_model_import_blocked)

    def test_52_fx6_contrasting_pro_camera_path_and_no_m1_m4(self) -> None:
        fx6_cam = p301.simulate_camset_memory_recall_path_hil(
            body_profile=p301.BODY_MODEL_FX6,
            operation=p301.CAM_OP_SAVE_CAMSET,
            target_slot=p301.SLOT_2,
            card_fs_type=p301.CARD_FS_SDXC,
        )
        self.assertTrue(fx6_cam.admitted)
        self.assertIn("/SONY/PRO/CAMERA/", fx6_cam.resolved_fx3_setting_path)

        fx6_m1 = p301.simulate_camset_memory_recall_path_hil(
            body_profile=p301.BODY_MODEL_FX6,
            operation=p301.CAM_OP_SAVE_MEMORY_BANK,
            bank_id="M1",
        )
        self.assertFalse(fx6_m1.admitted)
        self.assertEqual(fx6_m1.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_53_camera_reset_resets_memory_recall_media_to_slot1_while_body_banks_survive(self) -> None:
        r = p301.simulate_camset_memory_recall_path_hil(
            operation=p301.CAM_OP_RECALL_MEMORY_BANK,
            bank_id="1",
            target_slot=p301.SLOT_2,
            reset_action=p301.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.memory_recall_media_reset_to_slot1)
        self.assertTrue(r.body_banks_1_3_survived_camera_reset)

    def test_54_custom_hold_rejects_invalid_inputs_einval(self) -> None:
        for bad in (
            {"body_profile": "ILME-FX9"},
            {"shooting_domain": "BAD"},
            {"pasm_mode": "iAuto"},
            {"log_shooting_mode": "S-Log2"},
            {"reset_action": "Reboot"},
        ):
            r = p301.simulate_reg_custom_shoot_set_hold_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=str(bad))

    def test_55_camset_rejects_invalid_inputs_einval(self) -> None:
        for bad in (
            {"body_profile": "ILME-FX9"},
            {"operation": "DELETE_CAMSET"},
            {"target_slot": "Slot 9"},
            {"card_fs_type": "NTFS"},
            {"source_model": "ZV-E1"},
            {"reset_action": "Factory"},
            {"operation": p301.CAM_OP_SAVE_CAMSET, "camset_filename": "CAMSET99.DAT"},
            {"operation": p301.CAM_OP_SAVE_MEMORY_BANK, "bank_id": "M9"},
        ):
            r = p301.simulate_camset_memory_recall_path_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=str(bad))

    def test_56_fx3a_body_parity_on_hold_and_camset(self) -> None:
        hold = p301.simulate_reg_custom_shoot_set_hold_hil(body_profile=p301.BODY_MODEL_FX3A)
        cam = p301.simulate_camset_memory_recall_path_hil(
            body_profile=p301.BODY_MODEL_FX3A,
            operation=p301.CAM_OP_SAVE_MEMORY_BANK,
            bank_id="M2",
            target_slot=p301.SLOT_2,
            card_fs_type=p301.CARD_FS_CFEXPRESS,
        )
        self.assertTrue(hold.admitted)
        self.assertTrue(cam.admitted)
        self.assertEqual(cam.resolved_fx3_setting_path, "B:/SONY/SETTING/FX3/CAMPR02B.DAT")

    def test_57_pillar_b_dict_passed_and_zero_pro_path(self) -> None:
        pb = self.default_audit["pillar_b_custom_hold_and_camset_path_hil"]
        self.assertTrue(pb["passed"])
        self.assertFalse(pb["fx3_pro_camera_path_exposed"])
        self.assertEqual(len(pb["hold_checkbox_keys"]), 11)
        self.assertEqual(pb["fx3_campr_path_format"], "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT")
        self.assertEqual(pb["fx3_camset_path_format"], "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT")

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 61C — [Photo Capture] (8.3M / 2.1M) DCI 4K Lockout & [Enlarge Image] (16 tests)
    # ------------------------------------------------------------------
    def test_58_photo_capture_uhd_extracts_8_3mp_across_jpeg_heif420_heif422(self) -> None:
        for clip_fmt in (
            p301.FILE_FORMAT_XAVC_SI_4K,
            p301.FILE_FORMAT_XAVC_HS_4K,
            p301.FILE_FORMAT_XAVC_S_4K,
        ):
            for ftype in p301.VALID_PHOTO_CAPTURE_FILE_TYPES:
                r = p301.simulate_photo_capture_and_enlarge_hil(
                    playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
                    clip_file_format=clip_fmt,
                    capture_file_type=ftype,
                    target_slot=p301.SLOT_2,
                )
                self.assertTrue(r.admitted, msg=(clip_fmt, ftype))
                self.assertEqual(r.extracted_megapixels_label, "8.3M")
                self.assertEqual((r.extracted_width, r.extracted_height), (3840, 2160))
                self.assertTrue(r.playback_filter_canceled)

    def test_59_photo_capture_fhd_extracts_2_1mp_for_movie_and_sq_playback(self) -> None:
        for media_t in (p301.PLAYBACK_MEDIA_MOVIE, p301.PLAYBACK_MEDIA_SQ):
            for fmt in (p301.FILE_FORMAT_XAVC_SI_HD, p301.FILE_FORMAT_XAVC_S_HD):
                r = p301.simulate_photo_capture_and_enlarge_hil(
                    playback_media_type=media_t,
                    clip_file_format=fmt,
                    capture_file_type=p301.PHOTO_CAPTURE_HEIF_422,
                    target_slot=p301.SLOT_2,
                )
                self.assertTrue(r.admitted, msg=(media_t, fmt))
                self.assertEqual(r.extracted_megapixels_label, "2.1M")
                self.assertEqual((r.extracted_width, r.extracted_height), (1920, 1080))

    def test_60_photo_capture_strictly_locked_out_on_dci4k_clips_eopnotsupp(self) -> None:
        for media_t in (p301.PLAYBACK_MEDIA_MOVIE, p301.PLAYBACK_MEDIA_SQ):
            r = p301.simulate_photo_capture_and_enlarge_hil(
                playback_media_type=media_t,
                clip_file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
                target_slot=p301.SLOT_2,
            )
            self.assertFalse(r.admitted, msg=media_t)
            self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.reason_code, "PHOTO_CAPTURE_LOCKED_OUT_ON_XAVC_SI_DCI_4K_0x60CE")
            self.assertEqual(r.extracted_width, 0)

    def test_61_photo_capture_rejected_on_still_playback_eopnotsupp(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_STILL,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            target_slot=p301.SLOT_2,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "PHOTO_CAPTURE_REQUIRES_MOVIE_OR_SQ_CLIP")

    def test_62_photo_capture_fail_closed_erofs_on_slot1_tier0_vault_and_write_protect(self) -> None:
        vault = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(vault.admitted)
        self.assertEqual(vault.errno_code, p301.EROFS_ERRNO)
        self.assertEqual(
            vault.reason_code,
            "PHOTO_CAPTURE_TARGET_SLOT1_VAULT_OR_WRITE_PROTECTED_FAIL_CLOSED_EROFS",
        )
        self.assertEqual(vault.physical_device_writes, 0)
        self.assertEqual(vault.slot1_vault_photo_capture_mutation_bytes, 0)

        wp = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            target_slot=p301.SLOT_2,
            slot_write_protected=True,
        )
        self.assertFalse(wp.admitted)
        self.assertEqual(wp.errno_code, p301.EROFS_ERRNO)

    def test_63_photo_capture_allowed_on_slot1_when_not_tier0_vault_and_not_wp(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=False,
            slot_write_protected=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.extracted_megapixels_label, "8.3M")

    def test_64_enlarge_image_still_only_and_locked_out_on_movies(self) -> None:
        still_ok = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_STILL,
            capture_requested=False,
            enlarge_requested=True,
            enlarge_init_mag=p301.ENLARGE_MAG_PREVIOUS,
            enlarge_init_pos=p301.ENLARGE_POS_CENTER,
        )
        self.assertTrue(still_ok.admitted)
        self.assertEqual(still_ok.enlarge_init_mag, p301.ENLARGE_MAG_PREVIOUS)
        self.assertEqual(still_ok.enlarge_init_pos, p301.ENLARGE_POS_CENTER)

        for mv in (p301.PLAYBACK_MEDIA_MOVIE, p301.PLAYBACK_MEDIA_SQ):
            mv_blk = p301.simulate_photo_capture_and_enlarge_hil(
                playback_media_type=mv,
                capture_requested=False,
                enlarge_requested=True,
            )
            self.assertFalse(mv_blk.admitted, msg=mv)
            self.assertEqual(mv_blk.errno_code, p301.EOPNOTSUPP_ERRNO, msg=mv)

    def test_65_jpeg_heif_switch_and_enlarge_prefs_survive_camera_reset_only_initialize_resets(self) -> None:
        cam_pc = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            capture_file_type=p301.PHOTO_CAPTURE_HEIF_420,
            target_slot=p301.SLOT_2,
            reset_action=p301.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(cam_pc.admitted)
        self.assertTrue(cam_pc.jpeg_heif_switch_survived_camera_reset)
        self.assertEqual(cam_pc.capture_file_type, p301.PHOTO_CAPTURE_HEIF_420)

        init_pc = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            capture_file_type=p301.PHOTO_CAPTURE_HEIF_420,
            target_slot=p301.SLOT_2,
            reset_action=p301.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(init_pc.admitted)
        self.assertFalse(init_pc.jpeg_heif_switch_survived_camera_reset)
        self.assertEqual(init_pc.capture_file_type, p301.PHOTO_CAPTURE_JPEG)

        cam_enl = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_STILL,
            capture_requested=False,
            enlarge_requested=True,
            enlarge_init_mag=p301.ENLARGE_MAG_PREVIOUS,
            enlarge_init_pos=p301.ENLARGE_POS_CENTER,
            reset_action=p301.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(cam_enl.enlarge_prefs_survived_camera_reset)
        self.assertEqual(cam_enl.enlarge_init_mag, p301.ENLARGE_MAG_PREVIOUS)

        init_enl = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_STILL,
            capture_requested=False,
            enlarge_requested=True,
            enlarge_init_mag=p301.ENLARGE_MAG_PREVIOUS,
            enlarge_init_pos=p301.ENLARGE_POS_CENTER,
            reset_action=p301.RESET_ACTION_INITIALIZE,
        )
        self.assertEqual(init_enl.enlarge_init_mag, p301.ENLARGE_MAG_STANDARD)
        self.assertEqual(init_enl.enlarge_init_pos, p301.ENLARGE_POS_FOCUSED)

    def test_66_fx6_has_no_photo_capture_or_still_enlarge_eopnotsupp(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            body_profile=p301.BODY_MODEL_FX6,
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_67_fx3a_body_parity_on_photo_capture_and_dci4k_lockout(self) -> None:
        ok = p301.simulate_photo_capture_and_enlarge_hil(
            body_profile=p301.BODY_MODEL_FX3A,
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            target_slot=p301.SLOT_2,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.extracted_megapixels_label, "8.3M")

        blk = p301.simulate_photo_capture_and_enlarge_hil(
            body_profile=p301.BODY_MODEL_FX3A,
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            target_slot=p301.SLOT_2,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p301.EOPNOTSUPP_ERRNO)

    def test_68_photo_capture_rejects_invalid_inputs_einval(self) -> None:
        for bad in (
            {"body_profile": "ILME-FX9"},
            {"playback_media_type": "AUDIO_ONLY"},
            {"clip_file_format": "PRORES_RAW"},
            {"capture_file_type": "TIFF"},
            {"target_slot": "Slot 3"},
            {"enlarge_init_mag": "Max Mag."},
            {"enlarge_init_pos": "TopLeft"},
            {"reset_action": "Reboot"},
        ):
            r = p301.simulate_photo_capture_and_enlarge_hil(**bad)
            self.assertFalse(r.admitted, msg=str(bad))
            self.assertEqual(r.errno_code, p301.EINVAL_ERRNO, msg=str(bad))

    def test_69_no_extract_photo_capture_false_leaves_playback_filter_uncanceled(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            capture_requested=False,
            enlarge_requested=False,
            capture_file_type=p301.PHOTO_CAPTURE_HEIF_422,
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.playback_filter_canceled)
        self.assertEqual(r.capture_file_type, p301.PHOTO_CAPTURE_HEIF_422)
        self.assertEqual(r.slot1_vault_photo_capture_mutation_bytes, 0)

    def test_70_pillar_cd_dict_passed_and_covers_all_16_redlines(self) -> None:
        pcd = self.default_audit["pillar_c_d_photo_capture_enlarge_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["valid_photo_capture_file_types"]), 3)
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])

    def test_71_photo_capture_menu_paths_match_ver_7_02(self) -> None:
        self.assertIn("[Photo Capture]", p301.PHOTO_CAPTURE_MENU_PATH)
        self.assertIn("[JPEG/HEIF Switch]", p301.PHOTO_CAPTURE_SWITCH_MENU_PATH)
        self.assertIn("[Enlarge Image]", p301.ENLARGE_IMAGE_MENU_PATH)

    def test_72_photo_capture_dci4k_reason_matches_0x60ce_contract(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_DCI_4K,
            target_slot=p301.SLOT_2,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertIn("DCI_4K", r.reason_code)

    def test_73_photo_capture_slot1_vault_blocked_even_on_heif_switch(self) -> None:
        r = p301.simulate_photo_capture_and_enlarge_hil(
            playback_media_type=p301.PLAYBACK_MEDIA_MOVIE,
            clip_file_format=p301.FILE_FORMAT_XAVC_SI_4K,
            capture_file_type=p301.PHOTO_CAPTURE_HEIF_420,
            target_slot=p301.SLOT_1,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p301.EROFS_ERRNO)
        self.assertEqual(r.slot1_vault_photo_capture_mutation_bytes, 0)

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 61 (61/61 Milestone!) Suite,
    #          CI Headroom & Portability Hygiene (11 tests -> Total 84)
    # ------------------------------------------------------------------
    def test_74_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p301.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p301.probe_phase301_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p301.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p301.probe_phase301_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.dci4k_120p_or_longgop_bypass_events, 0)
            self.assertEqual(blocked.reboot_24_00p_slot1_vault_reinit_events, 0)
            self.assertEqual(blocked.movie_still_aspect_override_events, 0)
            self.assertEqual(blocked.custom_hold_invalid_or_cineei_bypass_events, 0)
            self.assertFalse(blocked.fx3_pro_camera_path_exposed)
            self.assertEqual(blocked.fx6_cross_model_camset_import_events, 0)
            self.assertEqual(blocked.slot1_vault_camset_or_campr_mutation_bytes, 0)
            self.assertEqual(blocked.dci4k_photo_capture_bypass_events, 0)
            self.assertEqual(blocked.slot1_vault_photo_capture_mutation_bytes, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p301.probe_phase301_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p301.EINVAL_ERRNO)

    def test_75_standalone_cli_self_test_summary_json_and_help_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p301.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(
            FX3_VM_DIR / "realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py"
        )

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 301 Stage 61 (61/61)", proc_sum.stdout)
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
        self.assertEqual(data["milestone"], "61/61")
        self.assertEqual(data["phase_number"], 301)
        self.assertTrue(data["is_61st_stage_milestone"])

        proc_help = subprocess.run(
            [sys.executable, "-B", script, "--help"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--clean-room", proc_help.stdout)

    def test_76_standalone_cli_in_process_clean_room_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p301.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 301 Stage 61 (61/61)", buf.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf.getvalue())

    def test_77_suite_stage61_61_of_61_milestone_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s61 = rep["stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil"]
            self.assertTrue(s61["all_checks_passed"])
            self.assertEqual(s61["phase_number"], 301)
            self.assertEqual(s61["milestone"], "61/61")
            self.assertTrue(s61["is_61st_stage_milestone"])
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            self.assertGreaterEqual(len(stage_keys), 61)

    def test_78_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 15.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_79_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_80_suite_stage61_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil)
        self.assertTrue(default_cfg.include_stage61)
        self.assertTrue(
            default_cfg.include_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil
        )

        for override in (
            {"stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil": False},
            {"include_stage61": False},
            {"include_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage61"])
            self.assertFalse(
                rep["config"]["stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil"]
            )

    def test_81_fx3_vm_coemulation_suite_include_stage61_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage61", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_82_fx3_vm_coemulation_suite_cli_skip_phase301_and_skip_stage61(self) -> None:
        for skip_flag in ("--skip-phase301", "--skip-stage61", "--no-include-stage61"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0, msg=skip_flag)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"], msg=skip_flag)
            self.assertNotIn(
                "stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil", rep
            )

    def test_83_suite_help_works_without_argparse_percent_errors(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                suite.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("--include-stage61", buf.getvalue())
        self.assertIn("--skip-stage61", buf.getvalue())
        self.assertIn("--skip-phase301", buf.getvalue())

    def test_84_cross_platform_ci_portability_hygiene(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py"
        ).read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")
        forbidden_bin = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden_bin, mod_src)
        self.assertNotIn(forbidden_bin, test_src)
        self.assertIn("sys.executable", test_src)
        self.assertIn("15.0 if IS_CI", test_src)


if __name__ == "__main__":
    unittest.main()
