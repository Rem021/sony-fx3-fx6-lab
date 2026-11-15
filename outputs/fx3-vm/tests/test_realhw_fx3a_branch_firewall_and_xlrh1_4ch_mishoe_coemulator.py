#!/usr/bin/env python3
"""Unit tests for Phase 188 Stage 33 (`33/33`):
Real-Hardware `ILME-FX3` vs `ILME-FX3A` (`2.36M` XGA / No-NFC-IR) Branch Firewall &
`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Override HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

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
import realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator as p188  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p188.run_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p188.run_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil()
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE
    if _CLEAN_SUITE_CACHE is None:
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
    return _CLEAN_SUITE_CACHE


class TestPhase188Fx3aFirewallAndXlrH1MiShoeCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_33_and_redline_constants(self) -> None:
        self.assertEqual(p188.STAGE_INDEX, 33)
        self.assertEqual(p188.STAGE_TOTAL, 33)
        self.assertEqual(p188.MILESTONE_LABEL, "33/33")
        self.assertEqual(p188.STAGE_NAME, "stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil")
        self.assertTrue(p188.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p188.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p188.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p188.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p188.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p188.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p188.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p188.FX6_RIBBON_MMIO_FAULTS, 0)
        self.assertEqual(p188.AUDIO_POP_CLICK_EVENTS, 0)
        self.assertEqual(p188.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p188._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p188.inspect_phase188_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p188.inspect_phase188_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.10)
        self.assertLess(dt2, 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p188.inspect_phase188_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p188.inspect_phase188_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p188.resolve_phase188_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p188.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p188.inspect_phase188_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_contracts(self) -> None:
        da = p188.inspect_phase188_donors()
        self.assertEqual(da.fx3_nfc.file_bytes, 52_280)
        self.assertEqual(da.fx6_nfc.file_bytes, 56_376)
        self.assertEqual(da.fx6_hotshoe.file_bytes, 47_808)
        self.assertEqual(da.fx6_sircs.file_bytes, 27_072)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx6_string_en.file_bytes, 118_208)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_bodydata.file_bytes, 811_876_768)
        self.assertEqual(da.fx6_bodydata.file_bytes, 847_081_840)
        self.assertTrue(da.nfc_sircs_abi_proven)
        self.assertTrue(da.xlrh1_mishoe_tokens_proven)
        self.assertTrue(da.fx3_fx6_audio_mon_and_camset_proven)
        self.assertTrue(da.fx3_fx6_bodydata_ufu_proven)

    def test_06_large_donors_bounded_windows_max_4096b_each(self) -> None:
        da = p188.inspect_phase188_donors()
        for item in (
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_bodydata,
            da.fx6_bodydata,
        ):
            self.assertTrue(item.bounded_windows_only)
            self.assertLessEqual(item.bytes_read_total, 28_672)
            self.assertTrue(all(v == 1 for v in item.window_hits.values()))

    def test_07_hardware_body_profiles_exact_fx3_vs_fx3a_vs_fx30(self) -> None:
        fx3 = p188.HARDWARE_BODY_PROFILES[p188.MODEL_ILME_FX3]
        fx3a = p188.HARDWARE_BODY_PROFILES[p188.MODEL_ILME_FX3A]
        fx30 = p188.HARDWARE_BODY_PROFILES[p188.MODEL_ILME_FX30]
        self.assertEqual(fx3.model_id, 0x91030080)
        self.assertEqual(fx3.fw_version, "7.02")
        self.assertEqual(fx3.lcd_panel_dots, 1_440_000)
        self.assertTrue(fx3.nfc_present)
        self.assertTrue(fx3.ir_sircs_present)

        self.assertEqual(fx3a.model_id, 0x9103008A)
        self.assertEqual(fx3a.fw_version, "2.02")
        self.assertEqual(fx3a.lcd_panel_dots, 2_359_296)
        self.assertFalse(fx3a.nfc_present)
        self.assertFalse(fx3a.ir_sircs_present)

        self.assertEqual(fx30.model_id, 0x91030030)
        self.assertEqual(fx30.lcd_panel_dots, 2_359_296)
        self.assertFalse(fx30.nfc_present)
        self.assertFalse(fx30.ir_sircs_present)

    def test_08_pillar_a_fx3_702_native_admitted_to_stage_b(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(model_name=p188.MODEL_ILME_FX3)
        self.assertTrue(res.admitted_to_stage_b)
        self.assertFalse(res.stock_bypass_triggered)
        self.assertTrue(res.display_shim_loaded)
        self.assertEqual(res.detected_model_id_hex, "0x91030080")
        self.assertEqual(res.lcd_panel_dots, 1_440_000)
        self.assertTrue(res.nfc_present)
        self.assertTrue(res.ir_sircs_present)
        self.assertEqual(res.nvram_persistent_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(res.status_code, "STAGE_A_ILME_FX3_702_144M_NFC_IR_ADMITTED_OK")

    def test_09_pillar_a_fx3a_202_fail_closed_stock_bypass_under_50us(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3A,
            bodydata_target_model=p188.MODEL_ILME_FX3A,
            bodydata_fw_branch="2.02",
            camset_source_model=p188.MODEL_ILME_FX3A,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)
        self.assertTrue(res.within_50us_ceiling)
        self.assertLess(res.bypass_latency_us, 50.0)
        self.assertFalse(res.display_shim_loaded)
        self.assertEqual(res.lcd_panel_dots, 2_359_296)
        self.assertFalse(res.nfc_present)
        self.assertFalse(res.ir_sircs_present)
        self.assertEqual(res.nvram_persistent_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(res.status_code, "FAIL_CLOSED_STOCK_BYPASS_ILME_FX3A")

    def test_10_pillar_a_fx30_fail_closed_stock_bypass_under_50us(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX30,
            bodydata_target_model=p188.MODEL_ILME_FX30,
            bodydata_fw_branch="5.02",
            camset_source_model=p188.MODEL_ILME_FX30,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)
        self.assertTrue(res.within_50us_ceiling)
        self.assertLess(res.bypass_latency_us, 50.0)
        self.assertFalse(res.display_shim_loaded)
        self.assertEqual(res.status_code, "FAIL_CLOSED_STOCK_BYPASS_ILME_FX30")

    def test_11_pillar_a_236m_lcd_dotclock_mismatch_triggers_stock_bypass(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            lcd_panel_dots=2_359_296,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)
        self.assertFalse(res.display_shim_loaded)
        self.assertEqual(res.status_code, "FAIL_CLOSED_STOCK_BYPASS_HW_DTB_MISMATCH")

    def test_12_pillar_a_missing_nfc_triggers_stock_bypass(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            nfc_present=False,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)
        self.assertFalse(res.display_shim_loaded)

    def test_13_pillar_a_missing_ir_sircs_triggers_stock_bypass(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            ir_sircs_present=False,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)
        self.assertFalse(res.display_shim_loaded)

    def test_14_pillar_a_fw_below_2_04_floor_triggers_stock_bypass(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            fw_version="2.02",
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertTrue(res.stock_bypass_triggered)

    def test_15_pillar_a_rejects_fx3a_bodydata_on_fx3(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            bodydata_target_model=p188.MODEL_ILME_FX3A,
            bodydata_fw_branch="2.02",
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertFalse(res.bodydata_import_admitted)
        self.assertEqual(res.status_code, "BLOCKED_CROSS_MODEL_BODYDATA_BRANCH")

    def test_16_pillar_a_rejects_fx3_bodydata_on_fx3a(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3A,
            bodydata_target_model=p188.MODEL_ILME_FX3,
            bodydata_fw_branch="7.02",
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertFalse(res.bodydata_import_admitted)
        self.assertTrue(res.stock_bypass_triggered)

    def test_17_pillar_a_rejects_cross_model_camset_fx3a_to_fx3(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3,
            camset_source_model=p188.MODEL_ILME_FX3A,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertFalse(res.camset_import_admitted)
        self.assertEqual(res.status_code, "BLOCKED_CROSS_MODEL_CAMSET_IMPORT")

    def test_18_pillar_a_rejects_cross_model_camset_fx3_to_fx3a(self) -> None:
        res = p188.probe_stage_a_fx3_branch_firewall(
            model_name=p188.MODEL_ILME_FX3A,
            bodydata_target_model=p188.MODEL_ILME_FX3A,
            bodydata_fw_branch="2.02",
            camset_source_model=p188.MODEL_ILME_FX3,
        )
        self.assertFalse(res.admitted_to_stage_b)
        self.assertFalse(res.camset_import_admitted)

    def test_19_pillar_a_rejects_unknown_body_model_and_bad_fw_str(self) -> None:
        with self.assertRaises(p188.RealHwFx3aFirewallXlrH1Error):
            p188.probe_stage_a_fx3_branch_firewall(model_name="ILME-FX9")
        with self.assertRaises(p188.RealHwFx3aFirewallXlrH1Error):
            p188.probe_stage_a_fx3_branch_firewall(model_name=p188.MODEL_ILME_FX3, fw_version="bad")

    def test_20_pillar_a_matrix_passes(self) -> None:
        pa = p188.evaluate_pillar_a_fx3a_branch_firewall()
        self.assertTrue(pa["passed"])

    def test_21_pillar_b_xlrh1_48khz_24bit_4ch_big6_routing_ok(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_24B_4CH,
            headphone_monitoring_matrix=p188.MONITOR_MATRIX_CH_MIX_ALL,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.mi_shoe_digital_rx_active)
        self.assertFalse(res.mi_shoe_audio_set_locked)
        self.assertEqual(res.sample_rate_hz, 48_000)
        self.assertEqual(res.bit_depth, 24)
        self.assertEqual(res.active_channels, 4)
        self.assertEqual(res.channel_routing["CH1"], "XLR_IN1")
        self.assertEqual(res.channel_routing["CH2"], "XLR_IN2")
        self.assertEqual(res.channel_routing["CH3"], "IN3_35MM_STEREO_L")
        self.assertEqual(res.channel_routing["CH4"], "IN3_35MM_STEREO_R")
        self.assertTrue(all(res.big6_level_meters_dbfs[c] is not None for c in p188.BIG6_AUDIO_CHANNELS))
        self.assertTrue(res.fx6_ribbon_mmio_masked)
        self.assertEqual(res.fx6_ribbon_mmio_faults, 0)
        self.assertEqual(res.status_code, "XLR_H1_MISHOE_48KHZ_24BIT_4CH_BIG6_OK")

    def test_22_pillar_b_headphone_monitoring_matrix_all_3_modes(self) -> None:
        r12 = p188.coemulate_xlrh1_mishoe_audio(headphone_monitoring_matrix=p188.MONITOR_MATRIX_CH1_2)
        r34 = p188.coemulate_xlrh1_mishoe_audio(headphone_monitoring_matrix=p188.MONITOR_MATRIX_CH3_4)
        rmix = p188.coemulate_xlrh1_mishoe_audio(headphone_monitoring_matrix=p188.MONITOR_MATRIX_CH_MIX_ALL)
        self.assertEqual((r12.headphone_mix_left, r12.headphone_mix_right), ("CH1(XLR_IN1)", "CH2(XLR_IN2)"))
        self.assertEqual((r34.headphone_mix_left, r34.headphone_mix_right), ("CH3(IN3_L)", "CH4(IN3_R)"))
        self.assertEqual((rmix.headphone_mix_left, rmix.headphone_mix_right), ("CH1+CH3", "CH2+CH4"))

    def test_23_pillar_b_xlrh1_24bit_2ch_and_16bit_2ch_modes(self) -> None:
        r24 = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_24B_2CH
        )
        r16 = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_16B_2CH
        )
        self.assertEqual((r24.bit_depth, r24.active_channels), (24, 2))
        self.assertEqual((r16.bit_depth, r16.active_channels), (16, 2))
        self.assertIsNone(r24.big6_level_meters_dbfs["CH3"])
        self.assertIsNone(r24.big6_level_meters_dbfs["CH4"])

    def test_24_pillar_b_body_35mm_jack_overrides_mishoe_and_locks_menu(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_24B_4CH,
            body_35mm_jack_inserted=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.body_35mm_jack_inserted)
        self.assertEqual(res.active_audio_source, "BODY_35MM_ANALOG_OVERRIDE")
        self.assertFalse(res.mi_shoe_digital_rx_active)
        self.assertTrue(res.mi_shoe_audio_set_locked)
        self.assertTrue(res.mi_shoe_audio_set_grayed_out)
        self.assertEqual(res.active_channels, 2)
        self.assertEqual(res.status_code, "BODY_35MM_OVERRIDE_LOCKS_MI_SHOE_AUDIO_SET")

    def test_25_pillar_b_sq_off_speed_clean_mute_zero_pop(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_24B_4CH,
            sq_off_speed_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.sq_off_speed_active)
        self.assertTrue(res.audio_muted)
        self.assertFalse(res.mi_shoe_digital_rx_active)
        self.assertEqual(res.active_channels, 0)
        self.assertEqual(res.audio_pop_click_events, 0)
        self.assertEqual(res.status_code, "SQ_MODE_CLEAN_AUDIO_MUTE_OK")

    def test_26_pillar_b_major_bodydata_upgrade_resets_mishoe_to_16bit_2ch(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(
            mi_shoe_audio_setting=p188.MI_SHOE_AUDIO_MODE_48K_24B_4CH,
            major_bodydata_upgrade_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.bodydata_upgrade_reset_triggered)
        self.assertEqual(res.effective_mi_shoe_setting, p188.MI_SHOE_AUDIO_MODE_48K_16B_2CH)
        self.assertEqual(res.bit_depth, 16)
        self.assertEqual(res.active_channels, 2)
        self.assertEqual(res.status_code, "BODYDATA_UPGRADE_RESET_TO_16BIT_2CH_OK")

    def test_27_pillar_b_handle_audio_off_or_detached_falls_back_to_internal_mic(self) -> None:
        r_off = p188.coemulate_xlrh1_mishoe_audio(handle_audio_switch_on=False)
        r_det = p188.coemulate_xlrh1_mishoe_audio(xlrh1_attached=False)
        self.assertEqual(r_off.active_audio_source, "INTERNAL_CAPSULE_STEREO")
        self.assertEqual(r_det.active_audio_source, "INTERNAL_CAPSULE_STEREO")
        self.assertFalse(r_off.mi_shoe_digital_rx_active)
        self.assertEqual(r_off.active_channels, 2)

    def test_28_pillar_b_fx6_dedicated_ribbon_mmio_masked_zero_faults(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(fx6_dedicated_ribbon_probe_requested=True)
        self.assertFalse(res.admitted)
        self.assertTrue(res.fx6_ribbon_mmio_masked)
        self.assertEqual(res.fx6_ribbon_mmio_faults, 0)
        self.assertEqual(res.appfw_crashes, 0)
        self.assertEqual(res.status_code, "BLOCKED_FX6_DEDICATED_RIBBON_MASKED_ON_FX3")

    def test_29_pillar_b_xlrh1_standalone_firmware_flash_blocked(self) -> None:
        res = p188.coemulate_xlrh1_mishoe_audio(xlr_h1_firmware_update_requested=True)
        self.assertFalse(res.admitted)
        self.assertEqual(res.status_code, "BLOCKED_XLR_H1_HAS_NO_STANDALONE_FW_PACKAGE")

    def test_30_pillar_b_rejects_invalid_audio_setting_or_matrix(self) -> None:
        with self.assertRaises(p188.RealHwFx3aFirewallXlrH1Error):
            p188.coemulate_xlrh1_mishoe_audio(mi_shoe_audio_setting="96kHz/32bit")
        with self.assertRaises(p188.RealHwFx3aFirewallXlrH1Error):
            p188.coemulate_xlrh1_mishoe_audio(headphone_monitoring_matrix="CH9/10")

    def test_31_pillar_b_matrix_passes(self) -> None:
        pb = p188.evaluate_pillar_b_xlrh1_mishoe_4ch_hil()
        self.assertTrue(pb["passed"])

    def test_32_pillar_c_fx3bndl1_clean_airgapped_hygiene_ok(self) -> None:
        res = p188.validate_fx3bndl1_bundle_hygiene()
        self.assertTrue(res.valid)
        self.assertEqual(res.bundle_magic, p188.FX3BNDL1_MAGIC)
        self.assertEqual(res.target_model, p188.MODEL_ILME_FX3)
        self.assertEqual(res.target_model_id_hex, "0x91030080")
        self.assertEqual(res.target_fw_branch, "7.02")
        self.assertTrue(res.air_gapped_sd_only)
        self.assertTrue(res.sanitization_passed)
        self.assertTrue(res.cross_model_contamination_free)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(res.status_code, "FX3BNDL1_AIRGAPPED_HYGIENE_OK")

    def test_33_pillar_c_fx3bndl1_rejects_bad_magic_and_fx3a_branch(self) -> None:
        bad_magic = p188.validate_fx3bndl1_bundle_hygiene(bundle_magic="WRONG123")
        self.assertFalse(bad_magic.valid)
        self.assertEqual(bad_magic.status_code, "BLOCKED_INVALID_FX3BNDL1_MAGIC")

        fx3a_branch = p188.validate_fx3bndl1_bundle_hygiene(
            target_model=p188.MODEL_ILME_FX3A,
            target_model_id=p188.FX3A_MODEL_ID,
            target_fw_branch="2.02",
        )
        self.assertFalse(fx3a_branch.valid)
        self.assertFalse(fx3a_branch.cross_model_contamination_free)
        self.assertEqual(fx3a_branch.status_code, "BLOCKED_CROSS_MODEL_FX3BNDL1_BRANCH")

    def test_34_pillar_c_fx3bndl1_rejects_non_airgapped_or_raw_blob(self) -> None:
        non_ag = p188.validate_fx3bndl1_bundle_hygiene(air_gapped_sd_only=False)
        self.assertFalse(non_ag.valid)
        self.assertEqual(non_ag.status_code, "BLOCKED_NON_AIRGAPPED_BUNDLE_TRANSPORT")

        raw_blob = p188.validate_fx3bndl1_bundle_hygiene(contains_raw_sony_firmware_blob=True)
        self.assertFalse(raw_blob.valid)
        self.assertEqual(raw_blob.status_code, "BLOCKED_RAW_SONY_FIRMWARE_BLOB_IN_BUNDLE")

    def test_35_pillar_c_fx3bndl1_rejects_traversal_and_cross_model_files(self) -> None:
        for bad_path in (
            "../../nflasha15/lib/appFw.so",
            "/dev/nflasha5",
            "fx3/stage-b/fx3a_display.ko",
            "fx3/stage-b/BODYDATA.DAT",
            "fx3/stage-b/cpapp-b.bin",
        ):
            res = p188.validate_fx3bndl1_bundle_hygiene(member_paths=(bad_path,))
            self.assertFalse(res.valid, msg=bad_path)
            self.assertFalse(res.sanitization_passed, msg=bad_path)

    def test_36_pillar_d_baseline_redline_lock_ok(self) -> None:
        lock = p188.probe_hard_safety_redline()
        self.assertTrue(lock.valid)
        self.assertFalse(lock.persistent_emmc_writes_authorized)
        self.assertFalse(lock.spi_nor_write_authorized)
        self.assertFalse(lock.el3_payload_transmit_authorized)
        self.assertEqual(lock.physical_usb_packets_emitted, 0)
        self.assertEqual(lock.otp_fuse_touches, 0)
        self.assertEqual(lock.rpmb_counter_increments, 0)
        self.assertEqual(lock.fx6_ribbon_mmio_faults, 0)
        self.assertEqual(lock.blocked_action, "NONE")

    def test_37_pillar_d_blocks_every_forbidden_hw_write_and_emit(self) -> None:
        cases = (
            dict(authorize_persistent_emmc_writes=True),
            dict(authorize_spi_nor_write=True),
            dict(authorize_el3_payload_transmit=True),
            dict(emit_physical_usb_packet=True),
            dict(touch_otp_fuse=True),
            dict(increment_rpmb_counter=True),
            dict(trigger_fx6_ribbon_mmio=True),
        )
        for kw in cases:
            res = p188.probe_hard_safety_redline(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)
            self.assertEqual(res.otp_fuse_touches, 0)
            self.assertEqual(res.rpmb_counter_increments, 0)
            self.assertEqual(res.fx6_ribbon_mmio_faults, 0)

    def test_38_pillar_c_d_matrix_passes(self) -> None:
        pcd = p188.evaluate_pillar_c_d_fx3bndl1_hygiene_and_redlines()
        self.assertTrue(pcd["passed"])

    def test_39_unified_phase188_clean_room_passes_with_zero_leaked_raw_bytes(self) -> None:
        rep = _get_clean_room_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["stage_index"], 33)
        self.assertEqual(rep["stage_total"], 33)
        self.assertEqual(rep["milestone"], "33/33")
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        dumped = json.dumps(rep)
        self.assertNotIn("7f454c46", dumped.lower())

    def test_40_unified_phase188_default_mode_passes_with_all_pillars(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_fx3a_branch_firewall_hil"]["passed"])
        self.assertTrue(rep["pillar_b_xlrh1_mishoe_4ch_override_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_fx3bndl1_hygiene_and_redlines"]["passed"])
        self.assertEqual(rep["redlines"]["fx6_ribbon_mmio_faults"], 0)
        self.assertEqual(rep["redlines"]["emmc_nflasha_write_count"], 0)

    def test_41_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py"),
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
        self.assertIn("[PASS] Phase 188 Stage 33 (33/33)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py"),
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
        self.assertEqual(parsed["stage_index"], 33)

    def test_42_fx3_vm_coemulation_suite_includes_stage33_and_skip_phase188(self) -> None:
        rep_on = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil", rep_on)
        s33 = rep_on["stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil"]
        self.assertTrue(s33["all_checks_passed"])
        self.assertEqual(s33["fx6_ribbon_mmio_faults"], 0)
        self.assertEqual(s33["audio_pop_click_events"], 0)
        self.assertFalse(s33["persistent_emmc_writes_authorized"])
        self.assertFalse(s33["spi_nor_write_authorized"])
        self.assertFalse(s33["el3_payload_transmit_authorized"])
        self.assertEqual(s33["physical_usb_packets_emitted"], 0)
        self.assertEqual(s33["otp_fuse_touches"], 0)
        self.assertEqual(s33["rpmb_counter_increments"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertEqual(len(stage_keys), 33)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil", rep_skip)
        self.assertEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 32)

    def test_43_all_33_of_33_stages_present_and_passing_in_suite(self) -> None:
        rep = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 34):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_44_suite_subprocess_summary_and_skip_phase188_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
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
        self.assertIn("realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase188",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=", proc_skip.stdout)

    def test_45_suite_33_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 33)
        self.assertLess(dt_clean, 6.0)

        t1 = time.monotonic()
        rep_def = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 33)
        self.assertLess(dt_def, 6.0)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
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
        d_json = json.loads(p_json.stdout)
        self.assertTrue(d_json["all_checks_passed"])
        self.assertEqual(len([k for k in d_json if re.match(r"^stage\d+_", k)]), 33)

    def test_46_source_hygiene_rdonly_and_no_forbidden_flags_or_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("sys.dont_write_bytecode = True", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        forbidden_port = str(87 * 100 + 68)
        self.assertNotIn(forbidden_port, src)

    def test_47_audit_digest_deterministic_across_repeated_clean_room_runs(self) -> None:
        r1 = p188.run_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil(force_clean_room=True)
        r2 = p188.run_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil(force_clean_room=True)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_48_stage33_wall_clock_standalone_well_below_6s(self) -> None:
        t0 = time.monotonic()
        r = p188.run_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil()
        dt = time.monotonic() - t0
        self.assertTrue(r["all_checks_passed"])
        self.assertLess(dt, 6.0)


if __name__ == "__main__":
    unittest.main()
