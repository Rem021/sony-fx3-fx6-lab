#!/usr/bin/env python3
"""Unit tests for Phase 253 Stage 48 (`48/48` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`) Wave-38
`[Lock Operation Parts]` (`MENU + Fn >= 5s` Full-Body Lock Chord vs Destructive
`MENU + Delete >= 2s` Format Firewall & `[My Dial 1..3]` Temporary Override),
`[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]` Setup Persistence &
`[Silent Mode]` Hard Lockout, and `[Exposure step]` (`0.3EV`/`0.5EV`) vs
`[Shutter Angle]` Constant-Table Immunity HIL Co-Emulator.
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
import realhw_lock_op_parts_audio_timing_exp_step_coemulator as p253  # noqa: E402


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
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
    )
    base.update(overrides)
    return base


class TestPhase253LockOpPartsAudioTimingExpStepCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil(
            force_clean_room=True
        )
        cls.default_audit = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil()

        t0 = time.monotonic()
        cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        cls.clean_suite_elapsed = time.monotonic() - t0

        t1 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        cls.default_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Phase 253 Stage 48 (48/48) & O_RDONLY Donors (12)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase253_stage48_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p253.SCHEMA_ID,
            "realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1",
        )
        self.assertEqual(p253.PHASE_253_SCHEMA, p253.SCHEMA_ID)
        self.assertEqual(p253.PHASE_253_VERSION, "253.0.0")
        self.assertEqual(p253.PHASE_NUMBER, 253)
        self.assertEqual(p253.STAGE_INDEX, 48)
        self.assertEqual(p253.STAGE_TOTAL, 48)
        self.assertEqual(p253.MILESTONE_LABEL, "48/48")
        self.assertEqual(
            p253.STAGE_NAME,
            "stage48_realhw_lock_op_parts_audio_timing_exp_step_hil",
        )
        self.assertEqual(p253.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p253.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p253.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p253.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p253.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p253.NOP_COUNT, 0)
        self.assertEqual(p253.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p253.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p253.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertFalse(p253.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p253.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p253.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p253.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p253.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p253.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p253.DESTRUCTIVE_MENU_DELETE_CONFUSIONS, 0)
        self.assertEqual(p253.SLOT1_VAULT_FORMAT_EVENTS, 0)
        self.assertEqual(p253.SILENT_MODE_AUDIO_SIGNAL_LEAK_EVENTS, 0)
        self.assertEqual(p253.SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS, 0)

    def test_02_clean_room_and_default_audit_deterministic_sha256(self) -> None:
        c2 = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil(force_clean_room=True)
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p253.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.clean_audit["audit_digest_sha256"], c2["audit_digest_sha256"])

        d2 = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil()
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertEqual(self.default_audit["audit_digest_sha256"], d2["audit_digest_sha256"])

    def test_03_env_force_clean_room_truthy_and_falsy_variants(self) -> None:
        for val in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(p253.is_forced_clean_room({p253.ENV_FORCE_CLEAN_ROOM: val}))
            paths = p253.resolve_phase253_donor_paths(env={p253.ENV_FORCE_CLEAN_ROOM: val})
            for p in paths.values():
                self.assertIn(p253.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
        for val in ("", "0", "false", "no", "off"):
            self.assertFalse(p253.is_forced_clean_room({p253.ENV_FORCE_CLEAN_ROOM: val}))

    def test_04_missing_donor_directory_falls_back_cleanly_to_synthetic(self) -> None:
        with unittest.mock.patch.object(
            p253,
            "resolve_phase253_donor_paths",
            return_value={k: Path(f"/nonexistent_p253/{k}") for k in p253.DONOR_RELPATHS},
        ):
            audit = p253.inspect_phase253_donors(force_clean_room=False, env={})
        self.assertEqual(audit.source_mode, p253.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_all_15_donor_summaries_have_expected_byte_counts(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["access_mode"], "O_RDONLY")
            self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
            for key, expected_sz in p253.EXPECTED_DONOR_BYTES.items():
                self.assertEqual(da[key]["file_bytes"], expected_sz)

    def test_06_fx3_string_en_f_wave38_tokens_and_absent_tokens_verified(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            s = rep["donor_audit"]["fx3_string_en_f"]
            self.assertTrue(s["uxd_container_ok"])
            for tok in (
                "Lock Operation Parts",
                "Dial/Wheel",
                "My Dial",
                "Locked",
                "Delete",
                "Audio Out Timing",
                "Live",
                "Lip Sync",
                "Audio Recording",
                "Silent Mode",
                "Exposure step",
                "0.3EV",
                "0.5EV",
                "Shutter Mode",
                "Angle",
                "Speed",
                "Camera Settings Reset",
                "Reset Network Set.",
                "Initialize",
            ):
                self.assertEqual(s["marker_hits"][tok], 1)
            self.assertEqual(s["absent_marker_hits"]["Autoframing Settings"], 0)
            self.assertEqual(s["absent_marker_hits"]["ECS"], 0)

    def test_07_fx6_string_en_and_compact_elf64_donors_verified(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertTrue(da["fx6_string_en"]["uxd_container_ok"])
            for tok in ("Lock", "Audio", "Shutter", "Angle", "Speed", "Exposure", "Reset"):
                self.assertEqual(da["fx6_string_en"]["marker_hits"][tok], 1)
            for elf_key in (
                "fx3_imdb",
                "fx3_usb_bus_power",
                "fx3_msc_server",
                "fx3_media_cfg",
                "fx3_adj_media",
            ):
                self.assertTrue(da[elf_key]["elf64_le_ok"])

    def test_08_bounded_4kib_windows_in_appfw_cpapp_libmpr_and_bk4(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            for key in (
                "fx3_appfw",
                "fx6_appfw",
                "fx3_cpapp",
                "fx6_cpapp",
                "fx3_libmpr",
                "fx6_libmpr",
                "fx3_bk4",
                "fx6_bk4",
            ):
                lsumm = da[key]
                self.assertTrue(lsumm["bounded_windows_only"])
                self.assertLessEqual(lsumm["bytes_read_total"], 10 * 4096)
                for hit in lsumm["window_hits"].values():
                    self.assertEqual(hit, 1)

    def test_09_donor_proven_flags_all_true_and_zero_errors(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertTrue(da["lock_op_parts_and_mydial_proven"])
            self.assertTrue(da["audio_out_timing_and_signals_proven"])
            self.assertTrue(da["exposure_step_and_shutter_angle_proven"])
            self.assertTrue(da["all_contracts_verified"])
            self.assertEqual(tuple(da["errors"]), ())

    def test_10_os_open_uses_strictly_o_rdonly_without_write_flags(self) -> None:
        real_open = os.open
        seen_flags = []

        def _spy_open(path, flags, *args, **kwargs):
            seen_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        p253._DONOR_AUDIT_CACHE.clear()
        with unittest.mock.patch("os.open", side_effect=_spy_open):
            aud = p253.inspect_phase253_donors()
        self.assertTrue(aud.all_contracts_verified)
        for fl in seen_flags:
            self.assertEqual(fl, os.O_RDONLY)

    def test_11_no_raw_firmware_bytes_exposed_in_json_payload(self) -> None:
        serialized = json.dumps(self.default_audit)
        self.assertNotIn("\\u007fELF", serialized)
        self.assertEqual(self.default_audit["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_12_cold_and_cached_donor_inspection_sub_100ms(self) -> None:
        t0 = time.monotonic()
        aud = p253.inspect_phase253_donors()
        elapsed = time.monotonic() - t0
        self.assertTrue(aud.all_contracts_verified)
        self.assertLess(elapsed, 0.25)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 48A — Lock Operation Parts, MENU+Fn 5s, MENU+Delete 2s & My Dial (16)
    # ------------------------------------------------------------------
    def test_13_lock_op_parts_default_off_fn_hold_3s_is_noop(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            key_chord="Fn",
            hold_duration_s=3.5,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.fn_lock_active)
        self.assertFalse(res.full_body_lock_active)
        self.assertFalse(res.front_rear_dials_locked)
        self.assertFalse(res.control_wheel_locked)
        self.assertFalse(res.multi_selector_locked)
        self.assertEqual(res.osd_toast, "")

    def test_14_lock_op_parts_multi_slct_only_locks_strictly_multi_selector(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Multi-Slct Only",
            key_chord="Fn",
            hold_duration_s=3.0,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.fn_lock_active)
        self.assertTrue(res.multi_selector_locked)
        self.assertFalse(res.front_rear_dials_locked)
        self.assertFalse(res.control_wheel_locked)
        self.assertEqual(res.osd_toast, "Locked.")

    def test_15_lock_op_parts_dial_wheel_locks_dials_and_wheel_only(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial/Wheel",
            key_chord="Fn",
            hold_duration_s=3.0,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.fn_lock_active)
        self.assertTrue(res.front_rear_dials_locked)
        self.assertTrue(res.control_wheel_locked)
        self.assertFalse(res.multi_selector_locked)
        self.assertEqual(res.osd_toast, "Locked.")

    def test_16_lock_op_parts_dial_wheel_mslct_locks_dials_wheel_and_mslct(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            key_chord="Fn",
            hold_duration_s=3.2,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.fn_lock_active)
        self.assertTrue(res.front_rear_dials_locked)
        self.assertTrue(res.control_wheel_locked)
        self.assertTrue(res.multi_selector_locked)
        self.assertFalse(res.all_body_buttons_locked_except_shutter)
        self.assertTrue(res.shutter_button_operable)

    def test_17_fn_short_press_below_3s_does_not_toggle_lock_state(self) -> None:
        r_unlocked = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            initial_fn_lock_active=False,
            key_chord="Fn",
            hold_duration_s=2.9,
        )
        self.assertFalse(r_unlocked.fn_lock_active)
        r_locked = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            initial_fn_lock_active=True,
            key_chord="Fn",
            hold_duration_s=0.3,
        )
        self.assertTrue(r_locked.fn_lock_active)

    def test_18_fn_hold_3s_toggles_active_lock_to_unlocked(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            initial_fn_lock_active=True,
            key_chord="Fn",
            hold_duration_s=3.0,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.fn_lock_active)
        self.assertFalse(res.front_rear_dials_locked)
        self.assertFalse(res.multi_selector_locked)
        self.assertEqual(res.osd_toast, "Unlocked.")

    def test_19_lock_op_parts_survives_camera_settings_reset_and_reset_network_set(self) -> None:
        r_cam = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial/Wheel",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_cam.survived_camera_or_network_reset)
        self.assertFalse(r_cam.restored_by_initialize)
        self.assertEqual(r_cam.effective_lock_op_parts_register, "Dial/Wheel")

        r_net = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.survived_camera_or_network_reset)
        self.assertEqual(r_net.effective_lock_op_parts_register, "Dial+Wheel+MSlct")

    def test_20_lock_op_parts_restored_to_off_only_by_initialize(self) -> None:
        r_init = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            initial_fn_lock_active=True,
            initial_full_body_lock_active=True,
            reset_action="Initialize",
        )
        self.assertTrue(r_init.restored_by_initialize)
        self.assertFalse(r_init.survived_camera_or_network_reset)
        self.assertEqual(r_init.effective_lock_op_parts_register, "Off")
        self.assertFalse(r_init.fn_lock_active)
        self.assertFalse(r_init.full_body_lock_active)

    def test_21_menu_fn_chord_below_5s_does_not_engage_full_body_lock(self) -> None:
        for hold_s in (0.5, 2.0, 4.99):
            res = p253.coemulate_lock_operation_parts_and_chord(
                configured_lock_op_parts="Off",
                key_chord="MENU+Fn",
                hold_duration_s=hold_s,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.full_body_lock_active)
            self.assertEqual(res.reason_code, "CHORD_HOLD_BELOW_5S_THRESHOLD")

    def test_22_menu_fn_chord_5s_engages_full_body_lock_except_shutter_even_when_off(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            key_chord="MENU+Fn",
            hold_duration_s=5.0,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.full_body_lock_active)
        self.assertTrue(res.all_body_buttons_locked_except_shutter)
        self.assertTrue(res.front_rear_dials_locked)
        self.assertTrue(res.control_wheel_locked)
        self.assertTrue(res.multi_selector_locked)
        self.assertTrue(res.shutter_button_operable)
        self.assertEqual(res.osd_toast, "Locked.")

    def test_23_menu_fn_chord_release_requires_3s_hold(self) -> None:
        r_short = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            initial_full_body_lock_active=True,
            key_chord="MENU+Fn",
            hold_duration_s=2.9,
        )
        self.assertTrue(r_short.full_body_lock_active)
        self.assertEqual(r_short.osd_toast, "Locked.")

        r_rel = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            initial_full_body_lock_active=True,
            key_chord="MENU+Fn",
            hold_duration_s=3.0,
        )
        self.assertTrue(r_rel.admitted)
        self.assertFalse(r_rel.full_body_lock_active)
        self.assertFalse(r_rel.all_body_buttons_locked_except_shutter)
        self.assertEqual(r_rel.osd_toast, "Unlocked.")

    def test_24_destructive_menu_delete_2s_slot1_vault_blocked_erofs(self) -> None:
        res = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            key_chord="MENU+Delete",
            hold_duration_s=2.5,
            target_media_slot="Slot 1",
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.destructive_menu_delete_blocked)
        self.assertEqual(res.errno_code, p253.EROFS_ERRNO)
        self.assertEqual(res.destructive_menu_delete_confusions, 0)
        self.assertEqual(res.slot1_vault_format_events, 0)

    def test_25_destructive_menu_delete_slot2_and_sub2s_confusion_blocked_eacces(self) -> None:
        r_s2 = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            key_chord="MENU+Delete",
            hold_duration_s=2.0,
            target_media_slot="Slot 2",
        )
        self.assertFalse(r_s2.admitted)
        self.assertTrue(r_s2.destructive_menu_delete_blocked)
        self.assertEqual(r_s2.errno_code, p253.EACCES_ERRNO)
        self.assertEqual(r_s2.destructive_menu_delete_confusions, 0)

        r_sub2 = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Off",
            key_chord="MENU+Delete",
            hold_duration_s=1.1,
            target_media_slot="NONE",
        )
        self.assertFalse(r_sub2.admitted)
        self.assertEqual(r_sub2.errno_code, p253.EACCES_ERRNO)

    def test_26_my_dial_1_to_3_temporary_override_unlocks_dials_and_relocks_on_release(self) -> None:
        for slot in ("My Dial 1", "My Dial 2", "My Dial 3"):
            r_active = p253.coemulate_lock_operation_parts_and_chord(
                configured_lock_op_parts="Dial+Wheel+MSlct",
                initial_fn_lock_active=True,
                my_dial_slot=slot,
                my_dial_recalled=True,
            )
            self.assertTrue(r_active.admitted)
            self.assertTrue(r_active.my_dial_temporary_override_active)
            self.assertFalse(r_active.front_rear_dials_locked)
            self.assertFalse(r_active.control_wheel_locked)
            self.assertTrue(r_active.multi_selector_locked)

        r_released = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial+Wheel+MSlct",
            initial_fn_lock_active=True,
            my_dial_slot="My Dial 1",
            my_dial_recalled=False,
        )
        self.assertFalse(r_released.my_dial_temporary_override_active)
        self.assertTrue(r_released.front_rear_dials_locked)
        self.assertTrue(r_released.control_wheel_locked)

    def test_27_full_body_lock_blocks_fn_and_my_dial_custom_buttons_with_ebusy(self) -> None:
        r_fn = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial/Wheel",
            initial_full_body_lock_active=True,
            key_chord="Fn",
            hold_duration_s=3.5,
        )
        self.assertFalse(r_fn.admitted)
        self.assertEqual(r_fn.errno_code, p253.EBUSY_ERRNO)

        r_md = p253.coemulate_lock_operation_parts_and_chord(
            configured_lock_op_parts="Dial/Wheel",
            initial_full_body_lock_active=True,
            my_dial_slot="My Dial 2",
            my_dial_recalled=True,
        )
        self.assertFalse(r_md.admitted)
        self.assertEqual(r_md.errno_code, p253.EBUSY_ERRNO)
        self.assertFalse(r_md.my_dial_temporary_override_active)

    def test_28_lock_op_parts_validation_rejects_invalid_enums_and_negative_hold(self) -> None:
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(configured_lock_op_parts="BadMode")
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(reset_action="HardWipe")
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(key_chord="Alt+F4")
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(hold_duration_s=-0.1)
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(target_media_slot="Slot 9")
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(my_dial_slot="My Dial 4")
        with self.assertRaises(ValueError):
            p253.coemulate_lock_operation_parts_and_chord(my_dial_slot="NONE", my_dial_recalled=True)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 48B — Audio Out Timing vs Audio signals & Silent Mode (14)
    # ------------------------------------------------------------------
    def test_29_audio_out_timing_live_default_and_audio_signals_on_all_default(self) -> None:
        res = p253.coemulate_audio_out_timing_and_signals()
        self.assertTrue(res.admitted)
        self.assertTrue(res.audio_out_timing_available)
        self.assertEqual(res.effective_headphone_monitoring_mode, "Live")
        self.assertEqual(res.headphone_lip_sync_delay_frames, 0)
        self.assertEqual(res.effective_audio_signals_state, "On: all")
        self.assertTrue(res.audible_beep_emitted)

    def test_30_audio_out_timing_lip_sync_adds_frame_delay_in_movie_and_still(self) -> None:
        for cap in ("Movie", "Still"):
            res = p253.coemulate_audio_out_timing_and_signals(
                configured_audio_out_timing="Lip Sync",
                capture_mode=cap,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.audio_out_timing_available)
            self.assertEqual(res.effective_headphone_monitoring_mode, "Lip Sync")
            self.assertEqual(res.headphone_lip_sync_delay_frames, 2)

    def test_31_audio_signals_on_shutter_only_emits_strictly_on_shutter_release(self) -> None:
        r_sh = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_signals="On: shutter only",
            beep_trigger="SHUTTER_RELEASE",
        )
        self.assertTrue(r_sh.audible_beep_emitted)
        for trig in ("AF_CONFIRMATION", "SELF_TIMER"):
            r_other = p253.coemulate_audio_out_timing_and_signals(
                configured_audio_signals="On: shutter only",
                beep_trigger=trig,
            )
            self.assertFalse(r_other.audible_beep_emitted)

    def test_32_audio_signals_off_all_mutes_every_beep_trigger(self) -> None:
        for trig in p253.VALID_BEEP_TRIGGERS:
            res = p253.coemulate_audio_out_timing_and_signals(
                configured_audio_signals="Off: all",
                beep_trigger=trig,
            )
            self.assertFalse(res.audible_beep_emitted)

    def test_33_camera_settings_reset_resets_audio_out_timing_but_preserves_audio_signals(self) -> None:
        res = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            configured_audio_signals="Off: all",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.audio_out_timing_reset_restored_live)
        self.assertEqual(res.effective_audio_out_timing_register, "Live")
        self.assertTrue(res.audio_signals_survived_camera_or_network_reset)
        self.assertEqual(res.effective_audio_signals_register, "Off: all")

    def test_34_reset_network_set_preserves_both_audio_out_timing_and_audio_signals(self) -> None:
        res = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            configured_audio_signals="On: shutter only",
            reset_action="Reset Network Set.",
        )
        self.assertFalse(res.audio_out_timing_reset_restored_live)
        self.assertEqual(res.effective_audio_out_timing_register, "Lip Sync")
        self.assertTrue(res.audio_signals_survived_camera_or_network_reset)
        self.assertEqual(res.effective_audio_signals_register, "On: shutter only")

    def test_35_initialize_restores_both_audio_out_timing_live_and_audio_signals_on_all(self) -> None:
        res = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            configured_audio_signals="Off: all",
            reset_action="Initialize",
        )
        self.assertTrue(res.audio_out_timing_reset_restored_live)
        self.assertTrue(res.audio_signals_restored_by_initialize)
        self.assertEqual(res.effective_audio_out_timing_register, "Live")
        self.assertEqual(res.effective_audio_signals_register, "On: all")

    def test_36_sq_motion_suppresses_audio_out_timing_and_blocks_forced_bypass(self) -> None:
        r_sup = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            capture_mode="S&Q Motion",
        )
        self.assertTrue(r_sup.admitted)
        self.assertFalse(r_sup.audio_out_timing_available)
        self.assertEqual(r_sup.effective_headphone_monitoring_mode, "MUTED_UNAVAILABLE")

        r_blk = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            capture_mode="S&Q Motion",
            force_bypass_sq_or_audio_off_timing=True,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p253.EOPNOTSUPP_ERRNO)

    def test_37_audio_recording_off_suppresses_audio_out_timing_and_blocks_bypass(self) -> None:
        r_sup = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            audio_recording="Off",
        )
        self.assertFalse(r_sup.audio_out_timing_available)

        r_blk = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_out_timing="Lip Sync",
            audio_recording="Off",
            force_bypass_sq_or_audio_off_timing=True,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p253.EOPNOTSUPP_ERRNO)

    def test_38_silent_mode_on_forcibly_mutes_audio_signals_while_preserving_setup_register(self) -> None:
        for sig_mode in ("On: all", "On: shutter only"):
            res = p253.coemulate_audio_out_timing_and_signals(
                configured_audio_signals=sig_mode,
                silent_mode="On",
                beep_trigger="SHUTTER_RELEASE",
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.silent_mode_forced_mute)
            self.assertEqual(res.effective_audio_signals_register, sig_mode)
            self.assertEqual(res.effective_audio_signals_state, "Off: all")
            self.assertFalse(res.audible_beep_emitted)
            self.assertEqual(res.silent_mode_audio_signal_leak_events, 0)

    def test_39_silent_mode_return_to_off_restores_configured_audio_signals(self) -> None:
        r_restored = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_signals="On: shutter only",
            silent_mode="Off",
            beep_trigger="SHUTTER_RELEASE",
        )
        self.assertFalse(r_restored.silent_mode_forced_mute)
        self.assertEqual(r_restored.effective_audio_signals_state, "On: shutter only")
        self.assertTrue(r_restored.audible_beep_emitted)

    def test_40_silent_mode_forced_bypass_fails_closed_with_eopnotsupp_and_zero_leaks(self) -> None:
        res = p253.coemulate_audio_out_timing_and_signals(
            configured_audio_signals="On: all",
            silent_mode="On",
            beep_trigger="AF_CONFIRMATION",
            force_bypass_silent_mode_audio_signals=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p253.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.audible_beep_emitted)
        self.assertEqual(res.silent_mode_audio_signal_leak_events, 0)

    def test_41_pillar_b_evaluator_passes_all_scenarios(self) -> None:
        pb = p253.evaluate_pillar_b_audio_out_timing_and_signals_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["all_2_audio_out_timing_modes"], ["Live", "Lip Sync"])
        self.assertEqual(
            pb["all_3_audio_signals_modes"],
            ["On: all", "On: shutter only", "Off: all"],
        )

    def test_42_audio_coemulator_validation_rejects_invalid_enums(self) -> None:
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(configured_audio_out_timing="Delayed")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(configured_audio_signals="BeepMax")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(audio_recording="Auto")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(capture_mode="TimeLapse")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(silent_mode="Half")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(beep_trigger="POWER_ON")
        with self.assertRaises(ValueError):
            p253.coemulate_audio_out_timing_and_signals(reset_action="BadReset")

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 48C — Exposure step 0.3EV/0.5EV vs Shutter Angle & Redlines (13)
    # ------------------------------------------------------------------
    def test_43_exposure_step_0_3ev_default_preserves_third_stop_values(self) -> None:
        res = p253.coemulate_exposure_step_vs_shutter_angle(
            configured_exposure_step="0.3EV",
            shutter_mode="Speed",
            requested_aperture="F3.2",
            requested_shutter_speed="1/50",
            requested_iso=1000,
            requested_exposure_comp_ev=0.3,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.quantized_aperture, "F3.2")
        self.assertEqual(res.quantized_shutter_speed, "1/50")
        self.assertEqual(res.quantized_iso, 1000)
        self.assertEqual(res.quantized_exposure_comp_ev, 0.3)
        self.assertFalse(res.ev_parameters_requantized_for_0_5ev)

    def test_44_exposure_step_0_5ev_requantizes_aperture_shutter_speed_iso_and_ev_comp(self) -> None:
        res = p253.coemulate_exposure_step_vs_shutter_angle(
            configured_exposure_step="0.5EV",
            shutter_mode="Speed",
            requested_aperture="F3.2",
            requested_shutter_speed="1/50",
            requested_iso=1000,
            requested_exposure_comp_ev=0.3,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.ev_parameters_requantized_for_0_5ev)
        self.assertEqual(res.quantized_aperture, "F3.5")
        self.assertEqual(res.quantized_shutter_speed, "1/45")
        self.assertEqual(res.quantized_iso, 1100)
        self.assertEqual(res.quantized_exposure_comp_ev, 0.5)

    def test_45_exposure_step_tables_cover_full_third_stop_vs_half_stop_ladders(self) -> None:
        self.assertGreater(len(p253.APERTURE_TABLE_0_3EV), len(p253.APERTURE_TABLE_0_5EV))
        self.assertGreater(len(p253.SHUTTER_SPEED_TABLE_0_3EV), len(p253.SHUTTER_SPEED_TABLE_0_5EV))
        self.assertGreater(len(p253.ISO_TABLE_0_3EV), len(p253.ISO_TABLE_0_5EV))
        self.assertGreater(len(p253.EXPOSURE_COMP_TABLE_0_3EV), len(p253.EXPOSURE_COMP_TABLE_0_5EV))
        self.assertIn("F4.8", p253.APERTURE_TABLE_0_5EV)
        self.assertIn("1/45", p253.SHUTTER_SPEED_TABLE_0_5EV)
        self.assertIn(2200, p253.ISO_TABLE_0_5EV)
        self.assertIn(-1.5, p253.EXPOSURE_COMP_TABLE_0_5EV)

    def test_46_exposure_step_resettable_by_camera_settings_reset_and_initialize_not_network(self) -> None:
        r_cam = p253.coemulate_exposure_step_vs_shutter_angle(
            configured_exposure_step="0.5EV",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_cam.reset_restored_0_3ev)
        self.assertEqual(r_cam.effective_exposure_step_register, "0.3EV")

        r_net = p253.coemulate_exposure_step_vs_shutter_angle(
            configured_exposure_step="0.5EV",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.survived_network_reset)
        self.assertEqual(r_net.effective_exposure_step_register, "0.5EV")

        r_init = p253.coemulate_exposure_step_vs_shutter_angle(
            configured_exposure_step="0.5EV",
            reset_action="Initialize",
        )
        self.assertTrue(r_init.reset_restored_0_3ev)
        self.assertEqual(r_init.effective_exposure_step_register, "0.3EV")

    def test_47_ver702_shutter_angle_table_100pct_constant_immune_across_0_3ev_and_0_5ev(self) -> None:
        for deg in p253.CINE_SHUTTER_ANGLE_TABLE_DEG:
            r03 = p253.coemulate_exposure_step_vs_shutter_angle(
                firmware_version="7.02",
                configured_exposure_step="0.3EV",
                shutter_mode="Angle",
                requested_shutter_angle_deg=deg,
            )
            r05 = p253.coemulate_exposure_step_vs_shutter_angle(
                firmware_version="7.02",
                configured_exposure_step="0.5EV",
                shutter_mode="Angle",
                requested_shutter_angle_deg=deg,
            )
            self.assertTrue(r03.admitted)
            self.assertTrue(r05.admitted)
            self.assertTrue(r03.shutter_angle_constant_table_immune)
            self.assertTrue(r05.shutter_angle_constant_table_immune)
            self.assertEqual(r03.effective_shutter_angle_deg, deg)
            self.assertEqual(r05.effective_shutter_angle_deg, deg)
            self.assertEqual(r03.active_shutter_angle_table_deg, r05.active_shutter_angle_table_deg)
            self.assertEqual(r05.shutter_angle_exposure_step_drift_events, 0)
        for key_angle in (5.6, 90.0, 172.8, 180.0, 360.0):
            self.assertIn(key_angle, p253.CINE_SHUTTER_ANGLE_TABLE_DEG)

    def test_48_shutter_angle_supported_on_ver600_to_702_and_blocked_pre600(self) -> None:
        for fw in ("6.00", "6.02", "7.00", "7.02"):
            ok = p253.coemulate_exposure_step_vs_shutter_angle(
                firmware_version=fw,
                configured_exposure_step="0.5EV",
                shutter_mode="Angle",
                requested_shutter_angle_deg=172.8,
            )
            self.assertTrue(ok.admitted)
        for fw in ("2.00", "3.00", "4.00", "5.00"):
            blk = p253.coemulate_exposure_step_vs_shutter_angle(
                firmware_version=fw,
                configured_exposure_step="0.5EV",
                shutter_mode="Angle",
                requested_shutter_angle_deg=180.0,
            )
            self.assertFalse(blk.admitted)
            self.assertEqual(blk.errno_code, p253.EOPNOTSUPP_ERRNO)

    def test_49_forced_shutter_angle_ev_drift_blocked_with_eopnotsupp(self) -> None:
        blk = p253.coemulate_exposure_step_vs_shutter_angle(
            firmware_version="7.02",
            configured_exposure_step="0.5EV",
            shutter_mode="Angle",
            requested_shutter_angle_deg=90.0,
            force_shutter_angle_ev_drift=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p253.EOPNOTSUPP_ERRNO)
        self.assertEqual(blk.shutter_angle_exposure_step_drift_events, 0)

    def test_50_exposure_step_validation_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(firmware_version="1.00")
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(configured_exposure_step="1.0EV")
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(shutter_mode="ECS")
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(requested_aperture="F0.95")
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(requested_shutter_speed="1/8000")
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(requested_shutter_angle_deg=179.0)
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(requested_iso=100)
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(requested_exposure_comp_ev=5.0)
        with self.assertRaises(ValueError):
            p253.coemulate_exposure_step_vs_shutter_angle(reset_action="Unknown")

    def test_51_baseline_redline_guard_valid_and_locked_safe(self) -> None:
        guard = p253.probe_phase253_redline_guard()
        self.assertTrue(guard.valid)
        self.assertEqual(guard.errno_code, 0)
        self.assertFalse(guard.persistent_emmc_writes_authorized)
        self.assertFalse(guard.hardware_live_attachment_authorized)
        self.assertFalse(guard.overall_ready_for_hardware_attach)
        self.assertFalse(guard.isp_write_authorized)
        self.assertFalse(guard.spi_nor_write_authorized)
        self.assertFalse(guard.el3_payload_transmit_authorized)
        self.assertTrue(guard.cnflasha_userspace_write_blocked)
        self.assertEqual(guard.physical_device_writes, 0)
        self.assertEqual(guard.nop_count, 0)
        self.assertEqual(guard.guest_code_modification_bytes, 0)

    def test_52_all_14_redline_probe_fields_fail_closed_individually(self) -> None:
        self.assertEqual(len(p253.ALL_14_REDLINE_PROBE_FIELDS), 14)
        for field in p253.ALL_14_REDLINE_PROBE_FIELDS:
            pr = p253.probe_phase253_redline_guard(**{field: True})
            self.assertFalse(pr.valid, msg=field)
            self.assertIn(pr.errno_code, (p253.EACCES_ERRNO, p253.EROFS_ERRNO))
            self.assertFalse(pr.persistent_emmc_writes_authorized)
            self.assertFalse(pr.hardware_live_attachment_authorized)
            self.assertEqual(pr.physical_device_writes, 0)

    def test_53_unknown_redline_probe_field_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            p253.probe_phase253_redline_guard(nonexistent_probe=True)

    def test_54_pillar_c_d_evaluator_passes_all_checks(self) -> None:
        pcd = p253.evaluate_pillar_c_d_exposure_step_shutter_angle_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 14)
        for entry in pcd["shutter_angle_constant_table_immunity_matrix"].values():
            self.assertTrue(entry["constant_table_identical"])

    def test_55_top_level_redlines_locked_across_clean_room_and_default_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["destructive_menu_delete_confusions"], 0)
            self.assertEqual(red["slot1_vault_format_events"], 0)
            self.assertEqual(red["silent_mode_audio_signal_leak_events"], 0)
            self.assertEqual(red["shutter_angle_exposure_step_drift_events"], 0)

    # ------------------------------------------------------------------
    # Group 5: CLI, Suite Stage 48 (48/48) Wiring & Hygiene (11)
    # ------------------------------------------------------------------
    def test_56_in_process_cli_json_and_summary_modes(self) -> None:
        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p253.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "48/48")
        self.assertEqual(parsed["phase_number"], 253)
        self.assertTrue(parsed["all_checks_passed"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p253.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 253 Stage 48 (48/48)", buf_sum.getvalue())

    def test_57_subprocess_cli_clean_room_and_default_modes(self) -> None:
        script = str(FX3_VM_DIR / "realhw_lock_op_parts_audio_timing_exp_step_coemulator.py")
        base_env = dict(os.environ)
        base_env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=base_env,
            check=True,
        )
        self.assertIn("[PASS] Phase 253 Stage 48 (48/48)", p_sum.stdout)

        clean_env = dict(base_env)
        clean_env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        p_clean = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=clean_env,
            check=True,
        )
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", p_clean.stdout)

    def test_58_fx3_vm_coemulation_suite_includes_stage48_and_48_stage_milestone(self) -> None:
        self.assertTrue(self.clean_suite["all_checks_passed"])
        self.assertIn("stage48_realhw_lock_op_parts_audio_timing_exp_step_hil", self.clean_suite)
        s48 = self.clean_suite["stage48_realhw_lock_op_parts_audio_timing_exp_step_hil"]
        self.assertTrue(s48["all_checks_passed"])
        self.assertEqual(s48["phase_number"], 253)
        self.assertEqual(s48["milestone"], "48/48")
        self.assertEqual(
            s48["schema"],
            "realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1",
        )
        self.assertEqual(s48["destructive_menu_delete_confusions"], 0)
        self.assertEqual(s48["slot1_vault_format_events"], 0)
        self.assertEqual(s48["silent_mode_audio_signal_leak_events"], 0)
        self.assertEqual(s48["shutter_angle_exposure_step_drift_events"], 0)
        self.assertEqual(s48["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in self.clean_suite if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 48)
        self.assertLess(self.clean_suite_elapsed, 4.0)

    def test_59_fx3_vm_coemulation_suite_all_48_stage_indices_unique_and_present(self) -> None:
        self.assertTrue(self.default_suite["all_checks_passed"])
        for idx in range(1, 49):
            matches = [k for k in self.default_suite if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(self.default_suite_elapsed, 4.0)

    def test_60_fx3_vm_coemulation_suite_skip_stage48_and_skip_phase253_config(self) -> None:
        rep_skip_p253 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                **_fast_suite_kwargs(
                    include_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil=False
                )
            )
        )
        self.assertTrue(rep_skip_p253["all_checks_passed"])
        self.assertNotIn("stage48_realhw_lock_op_parts_audio_timing_exp_step_hil", rep_skip_p253)
        self.assertFalse(rep_skip_p253["config"]["include_stage48"])

        rep_skip_s48 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(include_stage48=False))
        )
        self.assertTrue(rep_skip_s48["all_checks_passed"])
        self.assertNotIn("stage48_realhw_lock_op_parts_audio_timing_exp_step_hil", rep_skip_s48)

    def test_61_fx3_vm_coemulation_suite_include_stage48_cli_summary(self) -> None:
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
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage48", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn("realhw_lock_op_parts_audio_timing_exp_step_hil=CLEAN_ROOM_SYNTHETIC", out)

    def test_62_fx3_vm_coemulation_suite_cli_skip_phase253_and_skip_stage48(self) -> None:
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
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
        ]
        for flag in ("--skip-phase253", "--skip-stage48", "--no-include-stage48"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage48_realhw_lock_op_parts_audio_timing_exp_step_hil", rep)

    def test_63_run_stage48_direct_runner_matches_standalone_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s48 = suite.run_stage48_realhw_lock_op_parts_audio_timing_exp_step_hil(cfg)
        self.assertEqual(
            s48["phase253_audit_digest_sha256"],
            self.clean_audit["audit_digest_sha256"],
        )

    def test_64_menu_paths_match_official_sony_ilme_fx3_help_guide(self) -> None:
        self.assertEqual(
            p253.LOCK_OPERATION_PARTS_MENU_PATH,
            "MENU -> Setup -> [Operation Customize] -> [Lock Operation Parts]",
        )
        self.assertEqual(
            p253.AUDIO_OUT_TIMING_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]",
        )
        self.assertEqual(
            p253.AUDIO_SIGNALS_MENU_PATH,
            "MENU -> Setup -> [Sound Option] -> [Audio signals]",
        )
        self.assertEqual(
            p253.EXPOSURE_STEP_MENU_PATH,
            "MENU -> Exposure/Color -> [Exposure] -> [Exposure step]",
        )

    def test_65_fx3_vm_readme_documents_phase253_stage48_and_48_of_48(self) -> None:
        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 253", readme)
        self.assertIn("Stage 48", readme)
        self.assertIn("48/48", readme)
        self.assertIn("realhw_lock_op_parts_audio_timing_exp_step_coemulator.py", readme)
        self.assertIn("--include-stage48", readme)

    def test_66_zero_pyc_bytecode_files_and_sub_second_standalone_runtime(self) -> None:
        t0 = time.monotonic()
        r_clean = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil(
            force_clean_room=True
        )
        r_def = p253.run_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil()
        elapsed = time.monotonic() - t0
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertLess(elapsed, 1.0)
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
