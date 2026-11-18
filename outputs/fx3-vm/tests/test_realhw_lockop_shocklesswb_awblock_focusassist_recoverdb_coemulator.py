#!/usr/bin/env python3
"""Unit tests for Phase 367 (Stage 83 — 83/83 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-73:
- 83A: `Setup -> [Dial Customize] -> [Lock Operation Parts]` (`Off`/`Multi-Selector
  Only`/`Dial + Wheel`/`All`, Reset-resistant `Not available`, non-assignable
  Custom Key, forced `Off` by `[AF Area Registration]=On`, temporarily unlocked
  during `My Dial 1..3` recall, toggled by long-press `Fn` -> `"Locked."`) +
  `MENU + Fn` 5s global lock (locks all buttons/dials/wheel except `SHUTTER`,
  Touch governed by `[Touch Operation]`), dormant Alpha lock rejection
  (`UIBIZ_SLIKEY_LOCK` `EOPNOTSUPP=95`), vs FX6 dual physical `HOLD` switches +
  4-digit `User Menu with Lock` (`0000..9999`),
- 83B: `[Shockless WB]` (`Off`/`1 (Fast)`/`2`/`3 (Slow)`, Movie/`S&Q` only,
  `Can be reset`, smooths preset/`[Priority Set in AWB]` without affecting Auto
  tracking speed or `C.Temp.`/`A-B`/`G-M`), `[Priority Set in AWB]` (disabled
  in `Cine EI`), Still-only Reset-resistant `[Shutter AWB Lock]` (`Shutter Half
  Press`/`Cont. Shooting`/`Off` rejecting legacy strings `EOPNOTSUPP=95`) &
  Movie Custom Key `[AWB Lock Hold/Toggle]`, vs FX6 `WHT BAL` `B/A/PRESET`,
  `ATW Speed 1..5` (disabled in `Cine EI`), `Shockless White Off/1/2/3` & zero
  UI `Warm Cool`,
- 83C: Reset-resistant `[Focus Assistant]` 4 persistent sub-items (`[Auto
  Magnifier in MF]`, `[Focus Magnif. Time]`, `[Initial Focus Mag.]` Still FF
  `x1.0/x2.1 -> x4.1`, APS-C `x1.0/x1.5 -> x3.0`, Movie/`S&Q` `x1.0/x4.0`,
  `[AF in Focus Mag.]`), Clean-HDMI/XAVC isolation (`0` leaked pixels), and
  dormant `[Focus Ring Rotate]` (`_f 0x7b28`) `0` `appFw.so` enum disproof
  (`EOPNOTSUPP=95`), vs FX6 `AF Assist`, `Push AF Mode`, active `FOCUS_RING_ROTATE`,
  VF `x3/x6` & Ver. 6.0 `HDMI Focus Mag x2/x4`,
- 83D: Reset-resistant Playback `[Delete]` 5 batch modes, `[Delete confirm.]`
  `"Cancel" first`, `[Delete pressing twice]`, `[Protect]` 7 modes (zero
  `"Cancel All Images"` `EOPNOTSUPP=95`, atomic Main + `*S03.MP4` proxy
  co-binding), read-only `[Display Media Info.]` (`40,000`/`9999`), dual-immune
  `[Recover Image DB]` (`/AVF_INFO/AVIN0001.{INP,BNP,INT}`, `<20%` battery
  `EAGAIN=11`) & card-insert boot-prompt trap blocked by Tier-0 `Slot 1 EROFS=30`
  (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`), vs FX6
  `Update Media` / `Restore Media` WP check (`ng_write_protected`) & `Clip Lock`
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
import realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulator as p367  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..82 for Stage 83 isolation tests."""
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
]


class TestRealHwStage83Wave73CoEmulator(unittest.TestCase):
    # =========================================================================
    # Tests 01..15: Schema, Milestone 83/83, Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_milestone_83_of_83_and_phase_constants(self) -> None:
        self.assertEqual(
            p367.SCHEMA_ID,
            "phase367_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation_v1",
        )
        self.assertEqual(p367.PHASE_NUMBER, 367)
        self.assertEqual(p367.STAGE_INDEX, 83)
        self.assertEqual(p367.STAGE_TOTAL, 83)
        self.assertEqual(p367.MILESTONE_LABEL, "83/83")
        self.assertTrue(p367.IS_83RD_STAGE_MILESTONE)

    def test_02_tier0_redlines_hard_locked_zero_writes_zero_leak(self) -> None:
        self.assertFalse(p367.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertTrue(p367.P8_CP_MUTATION_FORBIDDEN)
        self.assertEqual(p367.NOP_COUNT, 0)
        self.assertEqual(p367.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p367.CP_MUTATION_BYTES, 0)
        self.assertEqual(p367.WBI_MUTATION_BYTES, 0)
        self.assertEqual(p367.CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(p367.CNFLASHA_MUTATION_BYTES, 0)
        self.assertTrue(p367.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p367.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p367.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p367.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(p367.SLOT1_SECTOR_WRITES, 0)
        self.assertEqual(p367.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertFalse(p367.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p367.RF_TX_PACKETS, 0)
        self.assertEqual(p367.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_wave73_numeric_and_enum_contracts(self) -> None:
        self.assertEqual(p367.FX3_LOCK_OP_PARTS_OPTIONS_COUNT, 4)
        self.assertEqual(len(p367.FX3_LOCK_OP_PARTS_4_MODES), 4)
        self.assertEqual(p367.FX3_MENU_FN_GLOBAL_LOCK_HOLD_SECONDS, 5.0)
        self.assertFalse(p367.FX3_MENU_FN_LOCKS_SHUTTER)
        self.assertEqual(p367.FX6_PHYSICAL_HOLD_SWITCH_COUNT, 2)
        self.assertFalse(p367.FX6_LCD_HOLD_SWITCH_PRESENT)
        self.assertEqual(p367.FX3_SHOCKLESS_WB_OPTIONS_COUNT, 4)
        self.assertEqual(p367.FX3_SHOCKLESS_WB_DEFAULT, "1 (Fast)")
        self.assertEqual(p367.FX3_FOCUS_ASSISTANT_PERSISTENT_ITEMS_COUNT, 4)
        self.assertEqual(len(p367.FX3_FOCUS_ASSISTANT_4_ITEMS), 4)
        self.assertEqual(p367.FX3_APPFW_FOCUS_RING_ROTATE_ENUMS_COUNT, 0)
        self.assertEqual(p367.FX3_PLAYBACK_DELETE_BATCH_MODES_COUNT, 5)
        self.assertEqual(len(p367.FX3_DELETE_5_BATCH_MODES), 5)
        self.assertEqual(p367.FX3_PLAYBACK_PROTECT_MODES_COUNT, 7)
        self.assertEqual(len(p367.FX3_PROTECT_7_MODES), 7)

    def test_04_donor_specs_14_compact_plus_4_window_total_18(self) -> None:
        self.assertEqual(len(p367.PHASE367_COMPACT_DONORS), 14)
        self.assertEqual(len(p367.PHASE367_WINDOW_DONORS), 4)
        names = [d.name for d in p367.PHASE367_COMPACT_DONORS] + [
            w.name for w in p367.PHASE367_WINDOW_DONORS
        ]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("fx3_libmpr", names)
        self.assertIn("fx3_appfw", names)
        self.assertIn("fx6_appfw", names)

    def test_05_clean_room_test_env_triggers_synthetic(self) -> None:
        da = p367.inspect_phase367_wave73_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da["total_donors_count"], 18)
        self.assertTrue(da["all_donors_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_06_force_clean_room_env_triggers_synthetic(self) -> None:
        da = p367.inspect_phase367_wave73_donors(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da["forced_clean_room"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_07_mocked_donorless_work_root_none_triggers_synthetic(self) -> None:
        da = p367.inspect_phase367_wave73_donors(work_root=None)
        self.assertEqual(da["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(da["work_root_available"])
        self.assertTrue(da["all_donors_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)

    def test_08_mac_work_root_sentinel_and_nonexistent_path_synthetic(self) -> None:
        da1 = p367.inspect_phase367_wave73_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": "__fx3_fx6_clean_room_donor_disabled__"}
        )
        da2 = p367.inspect_phase367_wave73_donors(
            work_root="/nonexistent/phase367_missing_dir"
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
            with self.assertRaises(p367.Stage83Phase367Error):
                p367._read_bounded_window_o_rdonly(p, 0, 4097)
        finally:
            p.unlink(missing_ok=True)

    def test_10_compact_read_rejects_over_1mib(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"Z" * (p367._COMPACT_MAX_READ_BYTES + 1))
            p = Path(tf.name)
        try:
            with self.assertRaises(p367.Stage83Phase367Error):
                p367._read_full_compact_o_rdonly(p)
        finally:
            p.unlink(missing_ok=True)

    def test_11_o_rdonly_local_donor_verification_when_present(self) -> None:
        if IS_CI or p367.is_forced_clean_room():
            self.skipTest("Clean-room / CI mode active")
        root = p367.resolve_mac_work_root()
        if root is None or not root.exists():
            self.skipTest("Local Mac/work donors absent")
        da = p367.inspect_phase367_wave73_donors(force_clean_room=False)
        self.assertEqual(da["source_mode"], "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(da["donor_access_mode"], "O_RDONLY")
        self.assertEqual(da["total_donors_count"], 18)
        self.assertTrue(da["all_donors_verified"])
        for w in da["window_donors"]:
            self.assertLessEqual(w["max_pread_bytes"], 4096)

    def test_12_full_coemulation_passes_in_forced_clean_room(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["milestone"], "83/83")
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep["pillar_a_lock_op_parts_menu_fn_vs_fx6_hold_hil"]["passed"])
        self.assertTrue(rep["pillar_b_shockless_wb_priority_awb_lock_vs_fx6_hil"]["passed"])
        self.assertTrue(
            rep["pillar_c_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil"][
                "passed"
            ]
        )
        self.assertTrue(
            rep["pillar_d_playback_delete_protect_recoverdb_vs_slot1_erofs_fx6_hil"][
                "passed"
            ]
        )

    def test_13_full_coemulation_passes_with_mocked_work_root_none(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(rep["redlines"]["slot1_data_sector_writes"], 0)
        self.assertFalse(rep["redlines"]["slot1_avf_info_mutated"])

    def test_14_strip_wall_clock_strips_nested_elapsed_seconds(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.99,
            "nested": [{"elapsed_seconds": 0.1, "k": "v"}],
        }
        cleaned = p367._strip_wall_clock(sample)
        self.assertEqual(cleaned, {"a": 1, "nested": [{"k": "v"}]})

    def test_15_resolve_mac_work_root_handles_sentinel_and_empty(self) -> None:
        self.assertIsNone(
            p367.resolve_mac_work_root(
                env={"FX3_FX6_MAC_WORK_ROOT": "__fx3_fx6_clean_room_donor_disabled__"}
            )
        )
        self.assertIsNone(p367.resolve_mac_work_root(env={"FX3_FX6_MAC_WORK_ROOT": "   "}))
        self.assertIsNone(p367.resolve_mac_work_root(work_root=None))

    # =========================================================================
    # Tests 16..37: Sub-Model 83A — [Lock Operation Parts] & MENU+Fn 5s vs FX6
    # =========================================================================

    def test_16_83a_fx3_exact_menu_path_and_4_options_admitted(self) -> None:
        for opt in p367.FX3_LOCK_OP_PARTS_4_MODES:
            r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
                operation="fx3_lock_op_config", lock_op_parts_setting=opt
            )
            self.assertTrue(r.admitted)
            self.assertEqual(
                r.menu_path, "Setup -> [Dial Customize] -> [Lock Operation Parts]"
            )
            self.assertEqual(r.lock_op_parts_setting, opt)

    def test_17_83a_fx3_wrong_operation_customize_path_rejected_eopnotsupp(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config", wrong_menu_path_requested=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_18_83a_fx3_assign_to_custom_key_rejected_eopnotsupp(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config", assign_to_custom_key_requested=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_19_83a_fx3_lock_op_parts_reset_resistant_cleared_by_initialize(self) -> None:
        r_rst = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config",
            lock_op_parts_setting="Multi-Selector Only",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.lock_op_parts_setting, "Multi-Selector Only")
        self.assertFalse(r_rst.resettable_via_camera_settings_reset)

        r_init = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config",
            lock_op_parts_setting="Multi-Selector Only",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.lock_op_parts_setting, "Off")

    def test_20_83a_fx3_af_area_registration_forces_lock_op_off(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config",
            lock_op_parts_setting="All",
            af_area_registration_on=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.af_area_registration_forced_off)
        self.assertEqual(r.lock_op_parts_setting, "Off")

        r_fn = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="All",
            af_area_registration_on=True,
            fn_long_press_toggled=True,
        )
        self.assertFalse(r_fn.admitted)
        self.assertEqual(r_fn.errno_code, p367.EBUSY_ERRNO)

    def test_21_83a_fx3_fn_long_press_lock_parts_breakdown(self) -> None:
        r_ms = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="Multi-Selector Only",
            fn_long_press_toggled=True,
        )
        self.assertTrue(r_ms.admitted)
        self.assertTrue(r_ms.locked_banner_shown)
        self.assertTrue(r_ms.multi_selector_locked)
        self.assertFalse(r_ms.dials_wheel_locked)
        self.assertFalse(r_ms.shutter_locked)

        r_dw = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="Dial + Wheel",
            fn_long_press_toggled=True,
        )
        self.assertFalse(r_dw.multi_selector_locked)
        self.assertTrue(r_dw.dials_wheel_locked)
        self.assertFalse(r_dw.shutter_locked)

    def test_22_83a_fx3_my_dial_recall_temporarily_unlocks_dials_wheel(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="All",
            fn_long_press_toggled=True,
            my_dial_recall_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.my_dial_temp_unlocked)
        self.assertTrue(r.multi_selector_locked)
        self.assertFalse(r.dials_wheel_locked)

        r_exit = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="All",
            fn_long_press_toggled=True,
            my_dial_recall_active=False,
        )
        self.assertFalse(r_exit.my_dial_temp_unlocked)
        self.assertTrue(r_exit.dials_wheel_locked)

    def test_23_83a_fx3_menu_fn_5s_global_lock_locks_all_except_shutter(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_menu_fn_5s_global_lock",
            menu_fn_hold_seconds=5.0,
            touch_operation="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.menu_fn_5s_global_lock_active)
        self.assertTrue(r.multi_selector_locked)
        self.assertTrue(r.dials_wheel_locked)
        self.assertTrue(r.buttons_locked)
        self.assertFalse(r.shutter_locked)
        self.assertTrue(r.touch_governed_by_touch_op)
        self.assertTrue(r.touch_screen_active)

    def test_24_83a_fx3_menu_fn_touch_remains_independent(self) -> None:
        r_off = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_menu_fn_5s_global_lock",
            menu_fn_hold_seconds=5.0,
            touch_operation="Off",
        )
        self.assertTrue(r_off.menu_fn_5s_global_lock_active)
        self.assertFalse(r_off.touch_screen_active)

    def test_25_83a_fx3_menu_fn_under_5s_returns_eagain_and_unlock_after_5s(self) -> None:
        r_short = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_menu_fn_5s_global_lock", menu_fn_hold_seconds=3.2
        )
        self.assertFalse(r_short.admitted)
        self.assertEqual(r_short.errno_code, p367.EAGAIN_ERRNO)

        r_unlock = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_menu_fn_5s_global_lock",
            menu_fn_hold_seconds=5.0,
            menu_fn_unlock_requested=True,
        )
        self.assertTrue(r_unlock.admitted)
        self.assertFalse(r_unlock.menu_fn_5s_global_lock_active)
        self.assertFalse(r_unlock.buttons_locked)

    def test_26_83a_fx3_dormant_alpha_lock_symbols_rejected_eopnotsupp(self) -> None:
        for sym in p367.FX3_DORMANT_LOCK_SYMBOLS:
            r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
                operation="fx3_dormant_alpha_lock", dormant_symbol=sym
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.dormant_sli_key_lock_exposed)

    def test_27_83a_fx6_dual_physical_hold_switches_and_zero_lcd_hold(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_body_hold_on=True,
            fx6_handle_hold_on=True,
            fx6_hold_with_rec_button=True,
            fx6_handle_hold_mode="Rec Button Only",
            fx6_menu_lock_mode="User Menu Only",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx6_physical_hold_switches_count, 2)
        self.assertFalse(r.fx6_lcd_hold_switch_present)
        self.assertTrue(r.shutter_locked)
        self.assertTrue(r.fx6_user_menu_unlocked)

    def test_28_83a_fx6_user_menu_with_lock_4digit_passcode_success_and_eacces(self) -> None:
        r_ok = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_menu_lock_mode="User Menu with Lock",
            fx6_passcode_configured="4321",
            fx6_passcode_entered="4321",
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.fx6_user_menu_unlocked)

        r_bad = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_menu_lock_mode="User Menu with Lock",
            fx6_passcode_configured="4321",
            fx6_passcode_entered="0000",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p367.EACCES_ERRNO)
        self.assertFalse(r_bad.fx6_user_menu_unlocked)

    def test_29_83a_fx6_invalid_passcode_format_einval(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_menu_lock_mode="User Menu with Lock",
            fx6_passcode_configured="12a4",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EINVAL_ERRNO)

    def test_30_83a_fx6_dormant_key_lock_rejected_eopnotsupp(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_dormant_key_lock_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_31_83a_cross_profile_operations_return_eopnotsupp(self) -> None:
        r1 = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX3, operation="fx6_hold_and_user_menu_lock"
        )
        r2 = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx3_menu_fn_5s_global_lock",
        )
        self.assertEqual(r1.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_32_83a_invalid_lock_op_parts_enum_einval(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_lock_op_config", lock_op_parts_setting="Dial Lock"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EINVAL_ERRNO)

    def test_33_83a_fx6_invalid_handle_hold_or_menu_mode_einval(self) -> None:
        r1 = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_handle_hold_mode="LCD Only",
        )
        r2 = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_menu_lock_mode="Admin Lock",
        )
        self.assertEqual(r1.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r2.errno_code, p367.EINVAL_ERRNO)

    def test_34_83a_invalid_dispatch_raises_stage83_error(self) -> None:
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
                body_profile="ILME-FX30"
            )
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
                operation="bad_83a_op"
            )
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
                touch_operation="Always"
            )

    def test_35_83a_fn_long_press_off_refused_ebusy(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            operation="fx3_fn_long_press_lock",
            lock_op_parts_setting="Off",
            fn_long_press_toggled=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EBUSY_ERRNO)

    def test_36_83a_fx6_handle_hold_normal_locks_handle_buttons(self) -> None:
        r = p367.simulate_lock_op_parts_menu_fn_vs_fx6_hold_lock_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_hold_and_user_menu_lock",
            fx6_body_hold_on=False,
            fx6_handle_hold_on=True,
            fx6_handle_hold_mode="Normal",
            fx6_menu_lock_mode="Off",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.buttons_locked)
        self.assertFalse(r.shutter_locked)

    def test_37_83a_pillar_a_payload_and_redlines(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        pa = rep["pillar_a_lock_op_parts_menu_fn_vs_fx6_hold_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(rep["redlines"]["fx3_lock_op_parts_options_count"], 4)
        self.assertEqual(rep["redlines"]["fx3_menu_fn_global_lock_hold_seconds"], 5.0)
        self.assertFalse(rep["redlines"]["fx3_menu_fn_locks_shutter"])
        self.assertEqual(rep["redlines"]["fx3_dormant_slikey_lock_exposed_events"], 0)
        self.assertEqual(rep["redlines"]["fx6_physical_hold_switch_count"], 2)

    # =========================================================================
    # Tests 38..59: Sub-Model 83B — [Shockless WB], [Priority Set in AWB],
    #              [Shutter AWB Lock] & Movie AWB Lock vs FX6 WHT BAL / ATW
    # =========================================================================

    def test_38_83b_fx3_shockless_wb_4_modes_movie_and_sq_admitted(self) -> None:
        for mode in ("Movie", "S&Q"):
            for opt in p367.FX3_SHOCKLESS_WB_4_MODES:
                r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                    operation="fx3_shockless_wb", shoot_mode=mode, shockless_wb=opt
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.shockless_wb, opt)

    def test_39_83b_fx3_shockless_wb_still_disabled_eopnotsupp(self) -> None:
        r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb", shoot_mode="Still", shockless_wb="1 (Fast)"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_40_83b_fx3_shockless_wb_can_be_reset_to_1_fast(self) -> None:
        r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            shoot_mode="Movie",
            shockless_wb="3 (Slow)",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.shockless_resettable)
        self.assertEqual(r.shockless_wb, "1 (Fast)")

    def test_41_83b_fx3_shockless_wb_smooths_preset_not_auto_or_ctemp_abgm(self) -> None:
        r_preset = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            shockless_wb="2",
            wb_change_kind="wb_preset_switch",
        )
        self.assertTrue(r_preset.transition_smoothed)
        self.assertFalse(r_preset.auto_tracking_speed_affected)

        r_ctemp = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            shockless_wb="3 (Slow)",
            wb_change_kind="ctemp_filter",
        )
        self.assertFalse(r_ctemp.transition_smoothed)
        self.assertTrue(r_ctemp.ctemp_ab_gm_immediate)

        r_abgm = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            shockless_wb="3 (Slow)",
            wb_change_kind="ab_gm_shift",
        )
        self.assertTrue(r_abgm.ctemp_ab_gm_immediate)

    def test_42_83b_fx3_cine_ei_locks_auto_wb_allows_fixed_presets(self) -> None:
        r_auto = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            log_shooting="Cine EI",
            wb_mode="Auto",
        )
        self.assertFalse(r_auto.admitted)
        self.assertEqual(r_auto.errno_code, p367.EBUSY_ERRNO)
        self.assertTrue(r_auto.auto_wb_locked_out_in_cine_ei)

        r_fixed = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb",
            log_shooting="Cine EI Quick",
            wb_mode="5500K",
            shockless_wb="2",
        )
        self.assertTrue(r_fixed.admitted)

    def test_43_83b_fx3_priority_set_in_awb_3_modes_can_be_reset(self) -> None:
        for p in p367.FX3_AWB_PRIORITY_3_MODES:
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_priority_set_in_awb", priority_set_in_awb=p
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.priority_set_in_awb, p)

        r_rst = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_priority_set_in_awb",
            priority_set_in_awb="White",
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r_rst.priority_set_in_awb, "Standard")

    def test_44_83b_fx3_priority_set_in_awb_disabled_in_cine_ei(self) -> None:
        for lm in ("Cine EI", "Cine EI Quick"):
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_priority_set_in_awb",
                log_shooting=lm,
                priority_set_in_awb="Ambience",
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p367.EBUSY_ERRNO)

    def test_45_83b_fx3_shutter_awb_lock_still_only_and_exact_labels(self) -> None:
        for lbl in p367.FX3_SHUTTER_AWB_LOCK_3_MODES:
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_shutter_awb_lock",
                shoot_mode="Still",
                shutter_awb_lock=lbl,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.shutter_awb_lock, lbl)

        for mode in ("Movie", "S&Q"):
            r_mv = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_shutter_awb_lock",
                shoot_mode=mode,
                shutter_awb_lock="Shutter Half Press",
            )
            self.assertFalse(r_mv.admitted)
            self.assertEqual(r_mv.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_46_83b_fx3_shutter_awb_lock_rejects_legacy_errata_labels(self) -> None:
        for bad in p367.FX3_SHUTTER_AWB_LOCK_ERRATA_MODES:
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_shutter_awb_lock",
                shoot_mode="Still",
                shutter_awb_lock=bad,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_47_83b_fx3_shutter_awb_lock_reset_resistant_not_available(self) -> None:
        r_rst = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shutter_awb_lock",
            shoot_mode="Still",
            shutter_awb_lock="Cont. Shooting",
            cont_shooting_active=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.shutter_awb_lock, "Cont. Shooting")
        self.assertFalse(r_rst.shutter_awb_lock_resettable_by_camera_reset)
        self.assertTrue(r_rst.awb_locked_active)

        r_init = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shutter_awb_lock",
            shoot_mode="Still",
            shutter_awb_lock="Cont. Shooting",
            initialize_applied=True,
        )
        self.assertEqual(r_init.shutter_awb_lock, "Off")

    def test_48_83b_fx3_shutter_awb_lock_requires_auto_or_underwater_auto(self) -> None:
        r_uw = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shutter_awb_lock",
            shoot_mode="Still",
            wb_mode="Underwater Auto",
            shutter_awb_lock="Shutter Half Press",
            shutter_half_pressed=True,
        )
        self.assertTrue(r_uw.awb_locked_active)

        r_fixed = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shutter_awb_lock",
            shoot_mode="Still",
            wb_mode="Daylight",
            shutter_awb_lock="Shutter Half Press",
            shutter_half_pressed=True,
        )
        self.assertFalse(r_fixed.awb_locked_active)

    def test_49_83b_fx3_movie_awb_lock_custom_key_hold_and_toggle(self) -> None:
        for ck in p367.FX3_MOVIE_AWB_LOCK_CUSTOM_KEYS:
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                operation="fx3_movie_awb_lock_custom_key",
                shoot_mode="Movie",
                movie_awb_lock_custom_key=ck,
                movie_awb_lock_engaged=True,
            )
            self.assertTrue(r.admitted)
            self.assertTrue(r.awb_locked_active)

        r_none = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_movie_awb_lock_custom_key",
            shoot_mode="Movie",
            movie_awb_lock_custom_key=None,
        )
        self.assertFalse(r_none.admitted)
        self.assertEqual(r_none.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_50_83b_fx3_movie_awb_lock_fixed_wb_ebusy(self) -> None:
        r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_movie_awb_lock_custom_key",
            shoot_mode="Movie",
            wb_mode="5600K",
            movie_awb_lock_custom_key="AWB Lock Hold",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EBUSY_ERRNO)

    def test_51_83b_fx6_wht_bal_switch_and_atw_speed_1_to_5(self) -> None:
        for pos in p367.FX6_WHT_BAL_SWITCH_POSITIONS:
            for spd in range(1, 6):
                r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                    body_profile=p367.BODY_MODEL_FX6,
                    fw_version=p367.FW_VER_601,
                    operation="fx6_wb_atw_shockless",
                    fx6_wht_bal_switch=pos,
                    fx6_atw_speed=spd,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.fx6_atw_speed, spd)

    def test_52_83b_fx6_atw_disabled_in_cine_ei_ebusy(self) -> None:
        r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_wb_atw_shockless",
            log_shooting="Cine EI",
            fx6_wht_bal_switch="B",
            fx6_white_switch_b_mode="ATW",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EBUSY_ERRNO)

    def test_53_83b_fx6_warm_cool_ui_disproved_eopnotsupp(self) -> None:
        r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_wb_atw_shockless",
            request_fx6_warm_cool_ui=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_warm_cool_ui_exposed)

    def test_54_83b_fx6_invalid_atw_speed_or_color_temp_einval(self) -> None:
        r1 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_wb_atw_shockless",
            fx6_atw_speed=6,
        )
        r2 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_wb_atw_shockless",
            fx6_color_temp_k=16000,
        )
        self.assertEqual(r1.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r2.errno_code, p367.EINVAL_ERRNO)

    def test_55_83b_cross_profile_operations_return_eopnotsupp(self) -> None:
        r1 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX3, operation="fx6_wb_atw_shockless"
        )
        r2 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx3_shockless_wb",
        )
        self.assertEqual(r1.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_56_83b_invalid_fx3_enum_values_einval(self) -> None:
        r1 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shockless_wb", shockless_wb="4"
        )
        r2 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_priority_set_in_awb", priority_set_in_awb="Warm"
        )
        r3 = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
            operation="fx3_shutter_awb_lock", shoot_mode="Still", shutter_awb_lock="Bad"
        )
        self.assertEqual(r1.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r2.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r3.errno_code, p367.EINVAL_ERRNO)

    def test_57_83b_invalid_dispatch_raises_stage83_error(self) -> None:
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                shoot_mode="Panorama"
            )
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                log_shooting="S-Log2"
            )

    def test_58_83b_fx6_shockless_white_4_options_verified(self) -> None:
        for sw in p367.FX6_SHOCKLESS_WHITE_4_MODES:
            r = p367.simulate_shockless_wb_priority_awb_lock_vs_fx6_hil(
                body_profile=p367.BODY_MODEL_FX6,
                fw_version=p367.FW_VER_601,
                operation="fx6_wb_atw_shockless",
                fx6_shockless_white=sw,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_shockless_white, sw)

    def test_59_83b_pillar_b_payload_and_redlines(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        pb = rep["pillar_b_shockless_wb_priority_awb_lock_vs_fx6_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(rep["redlines"]["fx3_shockless_wb_default"], "1 (Fast)")
        self.assertTrue(rep["redlines"]["fx3_shutter_awb_lock_still_only"])
        self.assertEqual(rep["redlines"]["fx3_shutter_awb_lock_reset_wipe_events"], 0)
        self.assertFalse(rep["redlines"]["fx6_warm_cool_ui_exposed"])

    # =========================================================================
    # Tests 60..79: Sub-Model 83C — [Focus Assistant] 4-Item Split, Ratios &
    #              Dormant [Focus Ring Rotate] 0-Enum Disproof vs FX6
    # =========================================================================

    def test_60_83c_fx3_focus_assistant_4_items_all_reset_resistant(self) -> None:
        r_rst = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_assistant_config",
            shoot_mode="Still",
            sensor_crop="FF",
            auto_magnifier_in_mf="Off",
            focus_magnif_time="2 Sec",
            initial_focus_mag="x2.1",
            af_in_focus_mag="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.persistent_items_count, 4)
        self.assertFalse(r_rst.resettable_via_camera_settings_reset)
        self.assertEqual(r_rst.auto_magnifier_in_mf, "Off")
        self.assertEqual(r_rst.focus_magnif_time, "2 Sec")
        self.assertEqual(r_rst.initial_focus_mag, "x2.1")
        self.assertEqual(r_rst.af_in_focus_mag, "Off")

        r_init = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_assistant_config",
            shoot_mode="Still",
            sensor_crop="FF",
            auto_magnifier_in_mf="Off",
            focus_magnif_time="2 Sec",
            initial_focus_mag="x2.1",
            af_in_focus_mag="Off",
            initialize_applied=True,
        )
        self.assertEqual(r_init.auto_magnifier_in_mf, "On")
        self.assertEqual(r_init.focus_magnif_time, "No Limit")
        self.assertEqual(r_init.initial_focus_mag, "x1.0")
        self.assertEqual(r_init.af_in_focus_mag, "On")

    def test_61_83c_fx3_still_ff_x2_1_steps_to_x4_1_and_rejects_x4_1_initial(self) -> None:
        r1 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            sensor_crop="FF",
            initial_focus_mag="x2.1",
            press_count=1,
        )
        self.assertEqual(r1.active_magnification_ratio, "x2.1")
        self.assertEqual(r1.second_press_ratio, "x4.1")

        r2 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            sensor_crop="FF",
            initial_focus_mag="x2.1",
            press_count=2,
        )
        self.assertEqual(r2.active_magnification_ratio, "x4.1")

        r_bad = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_assistant_config",
            shoot_mode="Still",
            sensor_crop="FF",
            initial_focus_mag="x4.1",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_62_83c_fx3_still_apsc_x1_5_steps_to_x3_0(self) -> None:
        r1 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            sensor_crop="APS-C",
            initial_focus_mag="x1.5",
            press_count=1,
        )
        self.assertTrue(r1.admitted)
        self.assertEqual(r1.active_magnification_ratio, "x1.5")
        self.assertEqual(r1.second_press_ratio, "x3.0")

        r2 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            sensor_crop="APS-C",
            initial_focus_mag="x1.5",
            press_count=2,
        )
        self.assertEqual(r2.active_magnification_ratio, "x3.0")

    def test_63_83c_fx3_movie_sq_initial_x1_0_or_x4_0(self) -> None:
        for mode in ("Movie", "S&Q"):
            r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="fx3_focus_mag_activate",
                shoot_mode=mode,
                initial_focus_mag="x4.0",
                press_count=1,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.active_magnification_ratio, "x4.0")

    def test_64_83c_fx3_dormant_high_mp_ratios_rejected_eopnotsupp(self) -> None:
        for ratio in p367.FX3_DORMANT_HIGH_MP_MAG_RATIOS:
            r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="fx3_focus_assistant_config",
                shoot_mode="Still",
                sensor_crop="FF",
                initial_focus_mag=ratio,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_65_83c_fx3_auto_magnifier_in_mf_still_mf_dmf_only(self) -> None:
        r_ok = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="MF",
            trigger_auto_mag_in_mf=True,
        )
        self.assertTrue(r_ok.admitted)

        for bad_mode in ("Movie", "S&Q"):
            r_mv = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="fx3_focus_mag_activate",
                shoot_mode=bad_mode,
                focus_mode="MF",
                trigger_auto_mag_in_mf=True,
            )
            self.assertFalse(r_mv.admitted)
            self.assertEqual(r_mv.errno_code, p367.EBUSY_ERRNO)

        r_ma = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="MF",
            mount_adaptor_attached=True,
            trigger_auto_mag_in_mf=True,
        )
        self.assertEqual(r_ma.errno_code, p367.EBUSY_ERRNO)

    def test_66_83c_fx3_af_in_focus_mag_still_and_mode_locks(self) -> None:
        r_ok = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="AF-S",
            trigger_af_in_mag=True,
        )
        self.assertTrue(r_ok.admitted)

        r_afc = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="AF-C",
            trigger_af_in_mag=True,
        )
        self.assertEqual(r_afc.errno_code, p367.EBUSY_ERRNO)

        r_cont = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="AF-S",
            cont_shooting_active=True,
            trigger_af_in_mag=True,
        )
        self.assertEqual(r_cont.errno_code, p367.EBUSY_ERRNO)

        r_mv = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Movie",
            focus_mode="AF-S",
            trigger_af_in_mag=True,
        )
        self.assertEqual(r_mv.errno_code, p367.EBUSY_ERRNO)

    def test_67_83c_fx3_clean_hdmi_and_xavc_zero_leaked_pixels(self) -> None:
        r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Movie",
            initial_focus_mag="x4.0",
        )
        self.assertEqual(r.hdmi_mag_leaked_pixels, 0)
        self.assertEqual(r.xavc_mag_leaked_pixels, 0)

    def test_68_83c_fx3_dormant_focus_ring_rotate_0_enums_disproved(self) -> None:
        for item in ("Focus Ring Rotate", "Previous Mag."):
            r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="fx3_dormant_focus_ring_rotate", dormant_item=item
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p367.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.fx3_appfw_focus_ring_rotate_enums_count, 0)
            self.assertFalse(r.dormant_focus_ring_rotate_exposed)

    def test_69_83c_fx6_focus_ring_rotate_and_af_assist_active(self) -> None:
        for frr in p367.FX6_FOCUS_RING_ROTATE_MODES:
            for push_mode in p367.FX6_PUSH_AF_MODES:
                r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                    body_profile=p367.BODY_MODEL_FX6,
                    fw_version=p367.FW_VER_601,
                    operation="fx6_focus_assist_and_mag",
                    fx6_focus_ring_rotate_mode=frr,
                    fx6_push_af_mode=push_mode,
                    fx6_focus_mag_button_target="VF Focus Mag",
                    fx6_hdmi_mag_step=1,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.active_magnification_ratio, "x3.0")
                self.assertEqual(r.second_press_ratio, "x6.0")

    def test_70_83c_fx6_ver60_hdmi_focus_mag_x2_x4_vs_pre_ver60_eopnotsupp(self) -> None:
        r_ok1 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_focus_assist_and_mag",
            fx6_focus_mag_button_target="HDMI Focus Mag",
            fx6_hdmi_mag_step=1,
        )
        self.assertEqual(r_ok1.active_magnification_ratio, "x2.0")

        r_ok2 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_600,
            operation="fx6_focus_assist_and_mag",
            fx6_focus_mag_button_target="HDMI Focus Mag",
            fx6_hdmi_mag_step=2,
        )
        self.assertEqual(r_ok2.active_magnification_ratio, "x4.0")

        r_old = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_500,
            operation="fx6_focus_assist_and_mag",
            fx6_focus_mag_button_target="HDMI Focus Mag",
        )
        self.assertFalse(r_old.admitted)
        self.assertEqual(r_old.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_71_83c_cross_profile_operations_return_eopnotsupp(self) -> None:
        r1 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX3, operation="fx6_focus_assist_and_mag"
        )
        r2 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx3_focus_mag_activate",
        )
        self.assertEqual(r1.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_72_83c_invalid_focus_magnif_time_or_fx6_enum_einval(self) -> None:
        r1 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_assistant_config", focus_magnif_time="10 Sec"
        )
        r2 = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_focus_assist_and_mag",
            fx6_hdmi_mag_step=3,
        )
        self.assertEqual(r1.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r2.errno_code, p367.EINVAL_ERRNO)

    def test_73_83c_invalid_dispatch_raises_stage83_error(self) -> None:
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                sensor_crop="MFT"
            )
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="bad_83c"
            )

    def test_74_83c_fx3_focus_magnif_time_all_3_modes_admitted(self) -> None:
        for t in p367.FX3_FOCUS_MAGNIF_TIME_MODES:
            r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
                operation="fx3_focus_assistant_config", focus_magnif_time=t
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.focus_magnif_time, t)

    def test_75_83c_fx3_still_ff_x1_0_stays_x1_0_on_first_and_x4_1_second(self) -> None:
        r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            sensor_crop="FF",
            initial_focus_mag="x1.0",
            press_count=1,
        )
        self.assertEqual(r.active_magnification_ratio, "x1.0")
        self.assertEqual(r.second_press_ratio, "x4.1")

    def test_76_83c_fx3_af_a_outside_pasms_blocks_af_in_mag(self) -> None:
        r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="AF-A",
            pasms_mode=False,
            trigger_af_in_mag=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EBUSY_ERRNO)

    def test_77_83c_fx3_dmf_allows_auto_magnifier_in_mf(self) -> None:
        r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            operation="fx3_focus_mag_activate",
            shoot_mode="Still",
            focus_mode="DMF",
            trigger_auto_mag_in_mf=True,
        )
        self.assertTrue(r.admitted)

    def test_78_83c_fx6_vf_focus_mag_step2_is_x6_0(self) -> None:
        r = p367.simulate_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_focus_assist_and_mag",
            fx6_focus_mag_button_target="VF Focus Mag",
            fx6_hdmi_mag_step=2,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.active_magnification_ratio, "x6.0")

    def test_79_83c_pillar_c_payload_and_redlines(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        pc = rep["pillar_c_focus_assistant_4item_split_vs_focus_ring_rotate_fx6_hil"]
        self.assertTrue(pc["passed"])
        self.assertEqual(
            rep["redlines"]["fx3_focus_assistant_persistent_items_count"], 4
        )
        self.assertEqual(
            rep["redlines"]["fx3_appfw_focus_ring_rotate_enums_count"], 0
        )
        self.assertEqual(rep["redlines"]["fx3_focus_mag_hdmi_leaked_pixels"], 0)
        self.assertTrue(rep["redlines"]["fx6_focus_ring_rotate_active"])
        self.assertTrue(rep["redlines"]["fx6_hdmi_focus_mag_ver60_supported"])

    # =========================================================================
    # Tests 80..95: Sub-Model 83D — Playback [Delete] 5-Mode / [Protect] 7-Mode
    #              Proxy Co-Binding & [Recover Image DB] Tier-0 Slot 1 EROFS=30
    # =========================================================================

    def test_80_83d_fx3_delete_5_batch_modes_admitted_on_virtual_slot2(self) -> None:
        for mode in p367.FX3_DELETE_5_BATCH_MODES:
            r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
                operation="fx3_delete_config_and_exec",
                target_slot="Slot 2",
                delete_mode=mode,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.delete_mode, mode)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_81_83d_fx3_delete_confirm_reset_resistant_vs_initialize(self) -> None:
        r_rst = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec",
            target_slot="Slot 2",
            delete_confirm='"Delete" first',
            delete_pressing_twice="On",
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r_rst.delete_confirm, '"Delete" first')
        self.assertEqual(r_rst.delete_pressing_twice, "On")

        r_init = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec",
            target_slot="Slot 2",
            delete_confirm='"Delete" first',
            delete_pressing_twice="On",
            initialize_applied=True,
        )
        self.assertEqual(r_init.delete_confirm, '"Cancel" first')
        self.assertEqual(r_init.delete_pressing_twice, "Off")

    def test_82_83d_fx3_delete_protected_and_split_proxy_forbidden_eperm(self) -> None:
        r_prot = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec",
            target_slot="Slot 2",
            clip_is_protected=True,
        )
        self.assertFalse(r_prot.admitted)
        self.assertEqual(r_prot.errno_code, p367.EPERM_ERRNO)

        r_split = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec",
            target_slot="Slot 2",
            split_main_proxy_requested=True,
        )
        self.assertFalse(r_split.admitted)
        self.assertEqual(r_split.errno_code, p367.EPERM_ERRNO)
        self.assertTrue(r_split.proxy_cobound_atomic)

    def test_83_83d_fx3_delete_on_tier0_slot1_blocked_erofs_30(self) -> None:
        r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec",
            target_slot="Slot 1",
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EROFS_ERRNO)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)

    def test_84_83d_fx3_protect_exact_7_modes_and_zero_cancel_all_images(self) -> None:
        for pm in p367.FX3_PROTECT_7_MODES:
            r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
                operation="fx3_protect_7mode",
                target_slot="Slot 2",
                protect_mode=pm,
                copy_requested=True,
            )
            self.assertTrue(r.admitted)
            self.assertTrue(r.proxy_cobound_atomic)
            self.assertTrue(r.copy_strips_protect_flag)

        r_bad = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_protect_7mode",
            target_slot="Slot 2",
            protect_mode="Cancel All Images",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_bad.cancel_all_images_exposed)

    def test_85_83d_fx3_protect_split_proxy_eperm_and_slot1_erofs_30(self) -> None:
        r_split = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_protect_7mode",
            target_slot="Slot 2",
            split_main_proxy_requested=True,
        )
        self.assertFalse(r_split.admitted)
        self.assertEqual(r_split.errno_code, p367.EPERM_ERRNO)

        r_s1 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_protect_7mode",
            target_slot="Slot 1",
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r_s1.admitted)
        self.assertEqual(r_s1.errno_code, p367.EROFS_ERRNO)
        self.assertEqual(r_s1.slot1_data_sector_writes, 0)

    def test_86_83d_fx3_display_media_info_read_only_on_slot1(self) -> None:
        r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_display_media_info", target_slot="Slot 1"
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.card_still_cap, 40000)
        self.assertEqual(r.live_view_cap, 9999)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)

    def test_87_83d_fx3_recover_image_db_dual_immune_on_virtual_slot2(self) -> None:
        r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_recover_image_db",
            target_slot="Slot 2",
            camera_settings_reset_applied=True,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.survives_camera_settings_reset)
        self.assertTrue(r.survives_initialize)
        self.assertTrue(r.ftp_transfer_result_cleared)
        self.assertEqual(r.avf_info_paths, p367.FX3_AVF_INFO_FILES)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_88_83d_fx3_recover_image_db_boot_prompt_trap_blocked_on_slot1_erofs_30(self) -> None:
        r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_recover_image_db",
            target_slot="Slot 1",
            slot1_is_tier0_vault=True,
            auto_confirm_boot_prompt=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EROFS_ERRNO)
        self.assertTrue(r.boot_prompt_trapped)
        self.assertFalse(r.slot1_avf_info_mutated)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_89_83d_fx3_recover_image_db_low_battery_eagain_and_sd_wp_erofs(self) -> None:
        r_bat = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_recover_image_db",
            target_slot="Slot 2",
            battery_pct=15,
        )
        self.assertFalse(r_bat.admitted)
        self.assertEqual(r_bat.errno_code, p367.EAGAIN_ERRNO)

        r_wp = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_recover_image_db",
            target_slot="Slot 2",
            sd_write_protect_on=True,
        )
        self.assertFalse(r_wp.admitted)
        self.assertEqual(r_wp.errno_code, p367.EROFS_ERRNO)

    def test_90_83d_fx6_restore_update_media_and_clip_lock_with_wp_check(self) -> None:
        for act in ("update_media", "restore_media", "clip_lock", "delete_clip"):
            for cm in p367.FX6_CLIP_LOCK_MODES:
                r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
                    body_profile=p367.BODY_MODEL_FX6,
                    fw_version=p367.FW_VER_601,
                    operation="fx6_media_restore_update_clip_lock",
                    target_slot="Slot 2",
                    fx6_action=act,
                    fx6_clip_lock_mode=cm,
                )
                self.assertTrue(r.admitted)

        r_wp = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_media_restore_update_clip_lock",
            target_slot="Slot 2",
            sd_write_protect_on=True,
            fx6_action="restore_media",
        )
        self.assertFalse(r_wp.admitted)
        self.assertEqual(r_wp.errno_code, p367.EROFS_ERRNO)

    def test_91_83d_fx6_slot1_tier0_vault_blocked_erofs_30(self) -> None:
        r = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_media_restore_update_clip_lock",
            target_slot="Slot 1",
            slot1_is_tier0_vault=True,
            fx6_action="update_media",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p367.EROFS_ERRNO)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_92_83d_cross_profile_operations_return_eopnotsupp(self) -> None:
        r1 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            body_profile=p367.BODY_MODEL_FX3,
            operation="fx6_media_restore_update_clip_lock",
        )
        r2 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx3_recover_image_db",
        )
        self.assertEqual(r1.errno_code, p367.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno_code, p367.EOPNOTSUPP_ERRNO)

    def test_93_83d_invalid_delete_protect_or_fx6_action_einval(self) -> None:
        r1 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_delete_config_and_exec", delete_mode="Delete Everything"
        )
        r2 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            operation="fx3_protect_7mode", protect_mode="All Images"
        )
        r3 = p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
            body_profile=p367.BODY_MODEL_FX6,
            fw_version=p367.FW_VER_601,
            operation="fx6_media_restore_update_clip_lock",
            fx6_action="reformat_all",
        )
        self.assertEqual(r1.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r2.errno_code, p367.EINVAL_ERRNO)
        self.assertEqual(r3.errno_code, p367.EINVAL_ERRNO)

    def test_94_83d_invalid_dispatch_raises_stage83_error(self) -> None:
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
                target_slot="Slot 3"
            )
        with self.assertRaises(p367.Stage83Phase367Error):
            p367.simulate_playback_delete_protect_recoverdb_vs_slot1_erofs_hil(
                battery_pct=150
            )

    def test_95_83d_pillar_d_payload_and_redlines(self) -> None:
        rep = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        pd = rep["pillar_d_playback_delete_protect_recoverdb_vs_slot1_erofs_fx6_hil"]
        self.assertTrue(pd["passed"])
        self.assertEqual(rep["redlines"]["fx3_playback_delete_batch_modes_count"], 5)
        self.assertEqual(rep["redlines"]["fx3_delete_confirm_default"], '"Cancel" first')
        self.assertEqual(rep["redlines"]["fx3_playback_protect_modes_count"], 7)
        self.assertEqual(
            rep["redlines"]["fx3_protect_cancel_all_images_exposed_events"], 0
        )
        self.assertEqual(rep["redlines"]["fx3_proxy_cobinding_split_events"], 0)
        self.assertTrue(rep["redlines"]["fx3_recover_image_db_dual_immune"])
        self.assertEqual(
            rep["redlines"]["fx3_slot1_avf_info_prompt_bypass_events"], 0
        )

    # =========================================================================
    # Tests 96..100: 4-Mode Determinism, Digest Distinction, CLI, Portability
    #                & Suite 83/83 Integration
    # =========================================================================

    def test_96_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            force_clean_room=True
        )
        r_f2 = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["audit_digest_sha256"], r_f2["audit_digest_sha256"])
        self.assertEqual(r_f1["audit_digest_sha256"], r_f3["audit_digest_sha256"])
        self.assertRegex(r_f1["audit_digest_sha256"], r"^[0-9a-f]{64}$")

        r_dl1 = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root=None
        )
        r_dl2 = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
            work_root="/nonexistent/phase367_stage83_test"
        )
        self.assertEqual(r_dl1["audit_digest_sha256"], r_dl2["audit_digest_sha256"])

        r_norm = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["audit_digest_sha256"], r_f1["audit_digest_sha256"]
            )
            self.assertNotEqual(
                r_norm["audit_digest_sha256"], r_dl1["audit_digest_sha256"]
            )

    def test_97_standalone_cli_self_test_summary_json_and_help(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p367.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 367 Stage 83/83", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p367.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "83/83")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p367.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("83/83", buf_help.getvalue())

    def test_98_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p367.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_99_suite_default_config_and_83_of_83_stage_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase367_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil
        )
        self.assertTrue(default_cfg.include_stage83)
        self.assertTrue(
            default_cfg.stage83_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s83 = rep["stage83_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil"]
        self.assertTrue(s83["all_checks_passed"])
        self.assertEqual(s83["phase_number"], 367)
        self.assertEqual(s83["milestone"], "83/83")
        self.assertTrue(s83["is_83rd_stage_milestone"])
        self.assertEqual(s83["raw_firmware_bytes_leaked"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Base 3 stages (stage1, stage2, stage3) + optional phase flags must reach >= 83
        self.assertGreaterEqual(len(stage_keys) + 3, 83)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil=",
            buf.getvalue(),
        )
        self.assertIn("m83=83/83", buf.getvalue())

        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc2 = suite.main([*_FAST_CLI_FLAGS, "--skip-stage83", "--json"])
        self.assertEqual(rc2, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertNotIn(
            "stage83_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil",
            rep_skip,
        )

        buf_skip_p = io.StringIO()
        with contextlib.redirect_stdout(buf_skip_p):
            rc3 = suite.main([*_FAST_CLI_FLAGS, "--skip-phase367", "--json"])
        self.assertEqual(rc3, 0)
        rep_skip_p = json.loads(buf_skip_p.getvalue())
        self.assertNotIn(
            "stage83_realhw_lockop_shocklesswb_awblock_focusassist_recoverdb_hil",
            rep_skip_p,
        )

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p367.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Phase 367 Stage 83/83", proc.stdout)

        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        with unittest.mock.patch.object(
            p367,
            "run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation",
            wraps=p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation,
        ) as m_run:
            real = p367.run_phase367_lockop_shocklesswb_awblock_focusassist_recoverdb_coemulation(
                force_clean_room=True
            )
            bad = dict(real)
            bad["milestone"] = "82/82"
            m_run.return_value = bad
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
