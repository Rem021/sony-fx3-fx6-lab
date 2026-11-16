#!/usr/bin/env python3
"""Unit tests for Phase 250 (250th Phase Milestone!) Stage 47 (`47/47` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`) Wave-37
`[Framing Settings]` Asymmetric `Full`/`Crop` Stream Co-Emulation & HDMI `RAW`
Mutual Exclusion, `[USB Power Supply]` Mandatory `NP-FZ100` Insertion + `USB Type-C`
Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup Persistence, and
`[Anti-flicker Shoot.]` Mechanical-Still-Only Boundary & Stock `ILME-FX3` Absence
of `[Var. Shutter]` HIL Co-Emulator.
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
import realhw_framing_usbpower_lun_antiflicker_coemulator as p250  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil()
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase250FramingUsbPowerLunAntiFlickerCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, 250th Milestone (47/47) & O_RDONLY Donor Audit (12)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase250_stage47_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p250.SCHEMA_ID,
            "realhw_framing_usbpower_lun_antiflicker_coemulator_v1",
        )
        self.assertEqual(p250.PHASE_250_SCHEMA, p250.SCHEMA_ID)
        self.assertEqual(p250.PHASE_250_VERSION, "250.0.0")
        self.assertEqual(p250.PHASE_NUMBER, 250)
        self.assertTrue(p250.IS_250TH_PHASE_MILESTONE)
        self.assertEqual(p250.STAGE_INDEX, 47)
        self.assertEqual(p250.STAGE_TOTAL, 47)
        self.assertEqual(p250.MILESTONE_LABEL, "47/47")
        self.assertEqual(
            p250.STAGE_NAME,
            "stage47_realhw_framing_usbpower_lun_antiflicker_hil",
        )
        self.assertEqual(p250.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p250.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p250.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p250.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p250.CNFLASHA_MUTATION_BYTES, 0)
        self.assertEqual(p250.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p250.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p250.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p250.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p250.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p250.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p250.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p250.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p250.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p250.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p250.FRAMING_CROP_HDMI_RAW_CONFLICT_EVENTS, 0)
        self.assertEqual(p250.ZVE1_AUTOFRAMING_CONFLATION_EVENTS, 0)
        self.assertEqual(p250.UNBUFFERED_USB_PD_BATTERY_PULL_EVENTS, 0)
        self.assertEqual(p250.MULTI_MICRO_USB_POWER_BYPASS_EVENTS, 0)
        self.assertEqual(p250.ANTIFLICKER_MOVIE_OR_ESHUTTER_BYPASS_EVENTS, 0)
        self.assertEqual(p250.FALSE_VAR_SHUTTER_OR_ECS_NODE_EVENTS, 0)
        self.assertFalse(p250.FX3_HAS_VAR_SHUTTER)
        self.assertFalse(p250.FX3_HAS_ECS)
        self.assertEqual(p250.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p250.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_sub_100ms_bounded_and_cached(self) -> None:
        p250._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p250.inspect_phase250_donors()
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p250.inspect_phase250_donors()
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 15)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.1)
        self.assertLess(dt2, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p250.inspect_phase250_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.framing_asymmetric_and_no_zve1_autoframing_proven)
        self.assertTrue(da.usb_power_npfz100_typec_and_lun_setup_proven)
        self.assertTrue(da.antiflicker_still_mech_and_no_fx3_varshutter_proven)
        self.assertEqual(da.donor_files_inspected, 15)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p250.is_forced_clean_room({p250.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p250.is_forced_clean_room({p250.ENV_FORCE_CLEAN_ROOM: falsy}))

    def test_05_env_clean_room_sentinel_paths_never_touch_local_donors(self) -> None:
        paths = p250.resolve_phase250_donor_paths(env={p250.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 15)
        for p in paths.values():
            self.assertIn(p250.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_06_nonexistent_donor_paths_fall_back_cleanly_to_synthetic(self) -> None:
        missing_paths = {
            k: Path("/nonexistent_phase250_work_root_xyz") / rel
            for k, rel in p250.DONOR_RELPATHS.items()
        }
        with unittest.mock.patch.object(
            p250, "resolve_phase250_donor_paths", return_value=missing_paths
        ):
            da = p250.inspect_phase250_donors(force_clean_room=False)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_07_compact_donor_tokens_verified_for_framing_usbpower_lun_and_antiflicker(self) -> None:
        for da in (p250.inspect_phase250_donors(), p250.inspect_phase250_donors(force_clean_room=True)):
            self.assertEqual(da.fx3_usb_bus_power.marker_hits["_ZN11UsbBusPower4MainEv"], 1)
            self.assertEqual(da.fx3_msc_server.marker_hits["MassStorageServer_Create"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Framing Settings"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Recording/Streaming"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Crop"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Full"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["USB Power Supply"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["USB LUN Setting"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["USB Connection Mode"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Sel. When Connect"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Multi"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Single"], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Anti-flicker Shoot."], 1)
            self.assertEqual(da.fx3_string_en_f.marker_hits["Silent Mode"], 1)

    def test_08_absent_tokens_verified_no_zve1_autoframing_and_fx3_vs_fx6_ecs(self) -> None:
        for da in (p250.inspect_phase250_donors(), p250.inspect_phase250_donors(force_clean_room=True)):
            self.assertEqual(da.fx3_string_en_f.absent_marker_hits["Autoframing Settings"], 0)
            self.assertEqual(da.fx3_string_en_f.absent_marker_hits["ECS"], 0)
            self.assertEqual(da.fx6_string_en.absent_marker_hits["Autoframing Settings"], 0)
            self.assertEqual(da.fx6_string_en.marker_hits["ECS"], 1)

    def test_09_large_donor_bounded_4k_windows_verified(self) -> None:
        for da in (p250.inspect_phase250_donors(), p250.inspect_phase250_donors(force_clean_room=True)):
            for lrg in (
                da.fx3_appfw,
                da.fx6_appfw,
                da.fx3_cpapp,
                da.fx6_cpapp,
                da.fx3_libmpr,
                da.fx6_libmpr,
                da.fx3_bk4,
                da.fx6_bk4,
            ):
                self.assertTrue(lrg.bounded_windows_only)
                self.assertLessEqual(lrg.bytes_read_total, 12 * p250.BOUNDED_WINDOW_MAX_BYTES)
                for hit in lrg.window_hits.values():
                    self.assertEqual(hit, 1)

    def test_10_os_open_uses_strictly_o_rdonly_zero_write_flags(self) -> None:
        opened_flags = []
        real_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            opened_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        p250._DONOR_AUDIT_CACHE.clear()
        with unittest.mock.patch("os.open", side_effect=spy_open):
            da = p250.inspect_phase250_donors()
        self.assertTrue(da.all_contracts_verified)
        for fl in opened_flags:
            self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            self.assertEqual(fl, os.O_RDONLY)

    def test_11_serialized_audit_json_leaks_zero_raw_firmware_bytes(self) -> None:
        for rep in (_get_default_audit(), _get_clean_room_audit()):
            raw_json = json.dumps(rep)
            self.assertNotIn("\\x7fELF", raw_json)
            self.assertLess(len(raw_json), 65_536)
            self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_12_deterministic_sha256_audit_digest_in_both_modes(self) -> None:
        r_clean_1 = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(force_clean_room=True)
        r_clean_2 = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(force_clean_room=True)
        self.assertEqual(r_clean_1["audit_digest_sha256"], r_clean_2["audit_digest_sha256"])

        r_def_1 = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil()
        r_def_2 = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil()
        self.assertEqual(r_def_1["audit_digest_sha256"], r_def_2["audit_digest_sha256"])

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 47A — [Framing Settings] Asymmetric Full/Crop (14)
    # ------------------------------------------------------------------
    def test_13_framing_settings_factory_default_off_passthrough_full(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.effective_framing_register, "Off")
        self.assertEqual(res.effective_recording_streaming_register, "Full")
        self.assertEqual(res.effective_hdmi_register, "Crop")
        self.assertFalse(res.framing_active)
        self.assertEqual(res.effective_recording_stream_output, "Full")
        self.assertEqual(res.effective_hdmi_monitor_output, "Full")
        self.assertFalse(res.asymmetric_master_full_monitor_crop)

    def test_14_framing_on_factory_asymmetric_full_master_vs_crop_hdmi(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(configured_framing="On")
        self.assertTrue(res.admitted)
        self.assertTrue(res.framing_active)
        self.assertEqual(res.effective_recording_stream_output, "Full")
        self.assertEqual(res.effective_hdmi_monitor_output, "Crop")
        self.assertTrue(res.asymmetric_master_full_monitor_crop)
        self.assertEqual(res.reason_code, "OK_47A_FRAMING_ASYMMETRIC_FULL_MASTER_CROP_HDMI")

    def test_15_monitor_and_control_remote_control_source_parity(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            control_source=p250.FRAMING_CONTROL_MONITOR_AND_CONTROL,
            configured_framing="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.control_source, "MONITOR_AND_CONTROL_REMOTE")
        self.assertTrue(res.asymmetric_master_full_monitor_crop)

    def test_16_all_4_framing_stream_routing_combinations_admitted(self) -> None:
        for rec_mode in ("Full", "Crop"):
            for hdmi_mode in ("Full", "Crop"):
                res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
                    configured_framing="On",
                    configured_recording_streaming=rec_mode,
                    configured_hdmi=hdmi_mode,
                )
                self.assertTrue(res.admitted)
                self.assertEqual(res.effective_recording_stream_output, rec_mode)
                self.assertEqual(res.effective_hdmi_monitor_output, hdmi_mode)
                self.assertEqual(
                    res.asymmetric_master_full_monitor_crop,
                    rec_mode == "Full" and hdmi_mode == "Crop",
                )

    def test_17_camera_settings_reset_restores_all_3_framing_items(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            configured_recording_streaming="Crop",
            configured_hdmi="Full",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.reset_restored_factory_defaults)
        self.assertEqual(res.effective_framing_register, "Off")
        self.assertEqual(res.effective_recording_streaming_register, "Full")
        self.assertEqual(res.effective_hdmi_register, "Crop")
        self.assertFalse(res.framing_active)

    def test_18_initialize_restores_all_3_framing_items(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            configured_recording_streaming="Crop",
            configured_hdmi="Full",
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.reset_restored_factory_defaults)
        self.assertEqual(res.effective_framing_register, "Off")
        self.assertEqual(res.effective_recording_streaming_register, "Full")
        self.assertEqual(res.effective_hdmi_register, "Crop")

    def test_19_hdmi_raw_mutual_exclusion_blocks_framing_on_with_ebusy(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            hdmi_raw_output="On",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EBUSY_ERRNO)
        self.assertTrue(res.hdmi_raw_framing_conflict_blocked)
        self.assertEqual(res.framing_crop_hdmi_raw_conflict_events, 0)

    def test_20_hdmi_raw_forced_bypass_fails_closed_with_eopnotsupp(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            hdmi_raw_output="On",
            force_bypass_hdmi_raw_lock=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.hdmi_raw_framing_conflict_blocked)
        self.assertEqual(res.framing_crop_hdmi_raw_conflict_events, 0)

    def test_21_hdmi_raw_admitted_when_framing_is_off(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="Off",
            hdmi_raw_output="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertFalse(res.framing_active)

    def test_22_camera_settings_reset_clears_framing_on_and_resolves_hdmi_raw_conflict(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            hdmi_raw_output="On",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_framing_register, "Off")
        self.assertFalse(res.hdmi_raw_framing_conflict_blocked)

    def test_23_zve1_autoframing_settings_menu_conflation_rejected(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            menu_node_name="Autoframing Settings",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.zve1_autoframing_conflation_blocked)
        self.assertEqual(res.zve1_autoframing_conflation_events, 0)

    def test_24_zve1_body_model_rejected_on_ilme_fx3(self) -> None:
        res = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            body_model="ZV-E1",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.zve1_autoframing_conflation_blocked)

    def test_25_invalid_framing_parameters_rejected_with_einval(self) -> None:
        r_ctrl = p250.simulate_framing_settings_asymmetric_crop_full_hil(control_source="BLUETOOTH_INVALID")
        r_stream = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_recording_streaming="Super35_Invalid"
        )
        r_reset = p250.simulate_framing_settings_asymmetric_crop_full_hil(reset_action="BAD_RESET")
        for r in (r_ctrl, r_stream, r_reset):
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p250.EINVAL_ERRNO)

    def test_26_framing_lifecycle_and_pillar_a_pass_completely(self) -> None:
        lc = p250.run_framing_settings_reset_and_mc_remote_lifecycle()
        pa = p250.evaluate_pillar_a_framing_asymmetric_and_hdmi_raw_hil()
        self.assertTrue(lc["lifecycle_passed"])
        self.assertTrue(pa["passed"])

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 47B — [USB Power Supply] & [USB LUN Setting] (14)
    # ------------------------------------------------------------------
    def test_27_usb_setup_factory_defaults_with_npfz100_and_typec_pd(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_usb_connection_mode, "Sel. When Connect")
        self.assertEqual(res.effective_usb_lun_setting, "Multi")
        self.assertEqual(res.effective_usb_power_supply, "On")
        self.assertTrue(res.camera_powered_on)
        self.assertEqual(res.usb_power_delivered_mw, 18_000)
        self.assertEqual(res.msc_enumerated_luns, ("Slot 1", "Slot 2"))
        self.assertEqual(res.physical_usb_packets_emitted, 0)

    def test_28_setup_usb_all_3_items_survive_camera_settings_reset(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Single",
            configured_usb_power_supply="Off",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.setup_usb_survived_camera_settings_reset)
        self.assertFalse(res.setup_usb_restored_by_initialize)
        self.assertEqual(res.effective_usb_connection_mode, "MassStorage(MSC)")
        self.assertEqual(res.effective_usb_lun_setting, "Single")
        self.assertEqual(res.effective_usb_power_supply, "Off")
        self.assertEqual(res.msc_enumerated_luns, ("Slot 1",))

    def test_29_setup_usb_all_3_items_restored_only_by_initialize(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Single",
            configured_usb_power_supply="Off",
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.setup_usb_survived_camera_settings_reset)
        self.assertTrue(res.setup_usb_restored_by_initialize)
        self.assertEqual(res.effective_usb_connection_mode, "Sel. When Connect")
        self.assertEqual(res.effective_usb_lun_setting, "Multi")
        self.assertEqual(res.effective_usb_power_supply, "On")
        self.assertEqual(res.msc_enumerated_luns, ("Slot 1", "Slot 2"))

    def test_30_power_on_without_npfz100_battery_refused_with_eacces(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            battery_bay_state="NONE",
            camera_power_switch_on=True,
            usb_port="USB Type-C",
            external_usb_pd_source_attached=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EACCES_ERRNO)
        self.assertFalse(res.camera_powered_on)
        self.assertEqual(res.usb_power_delivered_mw, 0)

    def test_31_mid_session_npfz100_battery_pull_triggers_immediate_unbuffered_poweroff(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            battery_bay_state="NP-FZ100",
            camera_power_switch_on=True,
            mid_session_battery_removed=True,
            usb_port="USB Type-C",
            external_usb_pd_source_attached=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EBUSY_ERRNO)
        self.assertTrue(res.immediate_unbuffered_poweroff)
        self.assertFalse(res.camera_powered_on)
        self.assertEqual(res.unbuffered_usb_pd_battery_pull_events, 0)

    def test_32_dcc1_dc_coupler_in_battery_bay_sustains_typec_pd_power(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            battery_bay_state="DC-C1",
            camera_power_switch_on=True,
            usb_port="USB Type-C",
            external_usb_pd_source_attached=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.camera_powered_on)
        self.assertEqual(res.usb_power_delivered_mw, 18_000)
        self.assertFalse(res.internal_charging_active)

    def test_33_power_switch_off_with_npfz100_on_typec_charges_battery(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            battery_bay_state="NP-FZ100",
            camera_power_switch_on=False,
            usb_port="USB Type-C",
            external_usb_pd_source_attached=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.camera_powered_on)
        self.assertTrue(res.internal_charging_active)
        self.assertEqual(res.usb_power_delivered_mw, 15_000)

    def test_34_multi_micro_usb_zero_power_and_zero_charge_boundary_enforced(self) -> None:
        for sw_on in (True, False):
            res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
                camera_power_switch_on=sw_on,
                usb_port="Multi/Micro USB",
                external_usb_pd_source_attached=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.usb_power_delivered_mw, 0)
            self.assertFalse(res.internal_charging_active)
            self.assertEqual(res.multi_micro_usb_power_bypass_events, 0)

    def test_35_usb_power_supply_off_runs_cleanly_on_internal_npfz100_battery(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_power_supply="Off",
            battery_bay_state="NP-FZ100",
            camera_power_switch_on=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.camera_powered_on)
        self.assertEqual(res.usb_power_delivered_mw, 0)
        self.assertEqual(res.reason_code, "OK_47B_INTERNAL_BATTERY_ONLY_OPERATION")

    def test_36_usb_lun_multi_dual_vs_single_populated_slot_visibility(self) -> None:
        r_dual = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Multi",
            dual_slots_populated=True,
        )
        r_one = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Multi",
            dual_slots_populated=False,
        )
        self.assertEqual(r_dual.msc_enumerated_luns, ("Slot 1", "Slot 2"))
        self.assertEqual(r_dual.msc_lun_count, 2)
        self.assertEqual(r_one.msc_enumerated_luns, ("Slot 1",))
        self.assertEqual(r_one.msc_lun_count, 1)

    def test_37_usb_lun_single_restricts_msc_enumeration_to_primary_slot(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Single",
            dual_slots_populated=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.msc_enumerated_luns, ("Slot 1",))
        self.assertEqual(res.msc_lun_count, 1)

    def test_38_live_host_usb_attachment_hard_blocked_zero_packets(self) -> None:
        res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            live_host_usb_attach_requested=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EACCES_ERRNO)
        self.assertEqual(res.physical_usb_packets_emitted, 0)

    def test_39_usb_connection_modes_admitted_and_invalid_enums_rejected(self) -> None:
        for conn in p250.VALID_USB_CONNECTION_MODES:
            res = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
                configured_usb_connection_mode=conn
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_usb_connection_mode, conn)

        bad_lun = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_lun_setting="Triple_Invalid"
        )
        bad_port = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            usb_port="Lightning_Invalid"
        )
        self.assertFalse(bad_lun.admitted)
        self.assertEqual(bad_lun.errno_code, p250.EINVAL_ERRNO)
        self.assertFalse(bad_port.admitted)
        self.assertEqual(bad_port.errno_code, p250.EINVAL_ERRNO)

    def test_40_usb_setup_lifecycle_and_pillar_b_pass_completely(self) -> None:
        lc = p250.run_usb_setup_reset_survival_and_initialize_lifecycle()
        pb = p250.evaluate_pillar_b_usb_power_npfz100_typec_and_lun_setup_hil()
        self.assertTrue(lc["lifecycle_passed"])
        self.assertTrue(pb["passed"])

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 47C — [Anti-flicker Shoot.] & No [Var. Shutter] (12)
    # ------------------------------------------------------------------
    def test_41_antiflicker_factory_default_off_in_mechanical_still_mode(self) -> None:
        res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_anti_flicker_register, "Off")
        self.assertFalse(res.anti_flicker_active)
        self.assertFalse(res.anti_flicker_menu_grayed_out)
        self.assertEqual(res.detected_flicker_hz, 0)
        self.assertFalse(res.fx3_has_var_shutter)

    def test_42_antiflicker_detects_100hz_and_120hz_in_mechanical_still_mode(self) -> None:
        for hz in (100, 120):
            res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
                configured_anti_flicker_shoot="On",
                capture_mode="Still",
                shutter_type="Mechanical",
                silent_mode="Off",
                ambient_flicker_hz=hz,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.anti_flicker_active)
            self.assertFalse(res.anti_flicker_menu_grayed_out)
            self.assertEqual(res.detected_flicker_hz, hz)

    def test_43_camera_settings_reset_and_initialize_restore_antiflicker_off(self) -> None:
        for rst in ("Camera Settings Reset", "Initialize"):
            res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
                configured_anti_flicker_shoot="On",
                reset_action=rst,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.reset_restored_off)
            self.assertEqual(res.effective_anti_flicker_register, "Off")
            self.assertFalse(res.anti_flicker_active)

    def test_44_antiflicker_suppressed_and_grayed_out_in_movie_and_sq_modes(self) -> None:
        for mode in ("Movie", "S&Q Motion"):
            res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
                configured_anti_flicker_shoot="On",
                capture_mode=mode,
                ambient_flicker_hz=100,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.anti_flicker_menu_grayed_out)
            self.assertFalse(res.anti_flicker_active)
            self.assertEqual(res.detected_flicker_hz, 0)

    def test_45_antiflicker_suppressed_in_silent_mode_or_electronic_shutter(self) -> None:
        r_silent = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
            configured_anti_flicker_shoot="On",
            capture_mode="Still",
            shutter_type="Mechanical",
            silent_mode="On",
        )
        r_elec = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
            configured_anti_flicker_shoot="On",
            capture_mode="Still",
            shutter_type="Electronic",
            silent_mode="Off",
        )
        for r in (r_silent, r_elec):
            self.assertTrue(r.admitted)
            self.assertTrue(r.anti_flicker_menu_grayed_out)
            self.assertFalse(r.anti_flicker_active)
            self.assertEqual(r.detected_flicker_hz, 0)

    def test_46_forced_bypass_of_mechanical_still_scope_fails_closed_with_eopnotsupp(self) -> None:
        for kwargs in (
            {"capture_mode": "Movie"},
            {"capture_mode": "S&Q Motion"},
            {"capture_mode": "Still", "silent_mode": "On"},
            {"capture_mode": "Still", "shutter_type": "Electronic"},
        ):
            res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
                configured_anti_flicker_shoot="On",
                force_bypass_mechanical_still_scope=True,
                **kwargs,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.antiflicker_movie_or_eshutter_bypass_events, 0)

    def test_47_stock_ilme_fx3_locks_has_var_shutter_false_and_has_ecs_false(self) -> None:
        res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil()
        self.assertFalse(res.fx3_has_var_shutter)
        self.assertFalse(res.fx3_has_ecs)
        self.assertEqual(res.false_var_shutter_or_ecs_node_events, 0)

    def test_48_requesting_fx30_var_shutter_on_fx3_fails_closed_with_eopnotsupp(self) -> None:
        res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
            requested_var_shutter=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.fx3_has_var_shutter)
        self.assertEqual(res.false_var_shutter_or_ecs_node_events, 0)

    def test_49_requesting_fx6_ecs_on_fx3_fails_closed_with_eopnotsupp(self) -> None:
        res = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
            requested_fx6_ecs=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p250.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.fx3_has_ecs)
        self.assertEqual(res.false_var_shutter_or_ecs_node_events, 0)

    def test_50_invalid_antiflicker_parameters_rejected_with_einval(self) -> None:
        r_body = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(body_model="ILME-FX30")
        r_hz = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(ambient_flicker_hz=77)
        r_cap = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(capture_mode="Timelapse_Invalid")
        for r in (r_body, r_hz, r_cap):
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p250.EINVAL_ERRNO)

    def test_51_reset_asymmetry_framing_and_antiflicker_reset_while_setup_usb_survives(self) -> None:
        r_fr = p250.simulate_framing_settings_asymmetric_crop_full_hil(
            configured_framing="On",
            configured_recording_streaming="Crop",
            configured_hdmi="Full",
            reset_action="Camera Settings Reset",
        )
        r_af = p250.simulate_antiflicker_still_mech_and_no_varshutter_hil(
            configured_anti_flicker_shoot="On",
            reset_action="Camera Settings Reset",
        )
        r_usb = p250.simulate_usb_power_npfz100_typec_and_lun_setup_hil(
            configured_usb_connection_mode="MassStorage(MSC)",
            configured_usb_lun_setting="Single",
            configured_usb_power_supply="Off",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(r_fr.effective_framing_register, "Off")
        self.assertEqual(r_af.effective_anti_flicker_register, "Off")
        self.assertEqual(r_usb.effective_usb_connection_mode, "MassStorage(MSC)")
        self.assertEqual(r_usb.effective_usb_lun_setting, "Single")
        self.assertEqual(r_usb.effective_usb_power_supply, "Off")

    def test_52_pillar_cd_antiflicker_no_varshutter_and_redlines_passes(self) -> None:
        pcd = p250.evaluate_pillar_c_d_antiflicker_no_varshutter_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertFalse(pcd["fx3_has_var_shutter"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 14)

    # ------------------------------------------------------------------
    # Group 5: 14-Probe Redlines, CLI, 47/47 Suite Wiring & Hygiene (14)
    # ------------------------------------------------------------------
    def test_53_stage47_redline_guard_baseline_and_all_14_fault_probes(self) -> None:
        base = p250.probe_stage47_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.hardware_live_attachment_authorized)
        self.assertFalse(base.overall_ready_for_hardware_attach)
        self.assertFalse(base.isp_write_authorized)
        self.assertTrue(base.cnflasha_userspace_write_blocked)
        self.assertEqual(base.cnflasha_mutation_bytes, 0)
        self.assertEqual(base.physical_device_writes, 0)
        self.assertEqual(base.raw_firmware_bytes_leaked, 0)

        for field in p250.ALL_14_REDLINE_PROBE_FIELDS:
            probe = p250.probe_stage47_redline_guard(**{field: True})
            self.assertFalse(probe.valid, msg=f"Redline probe {field} failed to trip")
            self.assertEqual(probe.errno_code, p250.EACCES_ERRNO)
            self.assertIn(field, probe.reason_code)

    def test_54_multi_fault_redline_probe_reports_all_tripped_flags(self) -> None:
        probe = p250.probe_stage47_redline_guard(
            authorize_persistent_emmc_writes=True,
            allow_framing_crop_hdmi_raw_conflict=True,
            allow_unbuffered_usb_pd_battery_pull=True,
            allow_false_var_shutter_or_ecs_on_fx3=True,
        )
        self.assertFalse(probe.valid)
        self.assertIn("authorize_persistent_emmc_writes", probe.reason_code)
        self.assertIn("allow_framing_crop_hdmi_raw_conflict", probe.reason_code)
        self.assertIn("allow_unbuffered_usb_pd_battery_pull", probe.reason_code)
        self.assertIn("allow_false_var_shutter_or_ecs_on_fx3", probe.reason_code)

    def test_55_full_phase250_report_passes_in_both_modes_with_locked_redlines(self) -> None:
        for rep in (_get_default_audit(), _get_clean_room_audit()):
            self.assertTrue(rep["all_checks_passed"])
            self.assertEqual(rep["phase_number"], 250)
            self.assertTrue(rep["is_250th_phase_milestone"])
            self.assertEqual(rep["milestone"], "47/47")
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["cnflasha_mutation_bytes"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["physical_usb_packets_emitted"], 0)
            self.assertEqual(red["framing_crop_hdmi_raw_conflict_events"], 0)
            self.assertEqual(red["unbuffered_usb_pd_battery_pull_events"], 0)
            self.assertEqual(red["false_var_shutter_or_ecs_node_events"], 0)
            self.assertFalse(red["fx3_has_var_shutter"])
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_56_in_process_cli_json_and_summary_modes(self) -> None:
        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p250.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "47/47")
        self.assertEqual(parsed["phase_number"], 250)
        self.assertTrue(parsed["all_checks_passed"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p250.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 250 (250th Milestone) Stage 47 (47/47)", buf_sum.getvalue())

    def test_57_subprocess_cli_clean_room_and_default_modes(self) -> None:
        script = str(FX3_VM_DIR / "realhw_framing_usbpower_lun_antiflicker_coemulator.py")
        base_env = dict(os.environ)
        base_env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=base_env,
            check=True,
        )
        self.assertIn("[PASS] Phase 250 (250th Milestone) Stage 47 (47/47)", p_sum.stdout)

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

    def test_58_fx3_vm_coemulation_suite_includes_stage47_and_47_stage_milestone(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage47_realhw_framing_usbpower_lun_antiflicker_hil", rep_on)
        s47 = rep_on["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]
        self.assertTrue(s47["all_checks_passed"])
        self.assertEqual(s47["phase_number"], 250)
        self.assertTrue(s47["is_250th_phase_milestone"])
        self.assertEqual(s47["milestone"], "47/47")
        self.assertEqual(s47["schema"], "realhw_framing_usbpower_lun_antiflicker_coemulator_v1")
        self.assertEqual(s47["framing_crop_hdmi_raw_conflict_events"], 0)
        self.assertEqual(s47["unbuffered_usb_pd_battery_pull_events"], 0)
        self.assertEqual(s47["false_var_shutter_or_ecs_node_events"], 0)
        self.assertFalse(s47["fx3_has_var_shutter"])
        self.assertEqual(s47["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 47)
        self.assertLess(dt_clean, 4.5)

    def test_59_fx3_vm_coemulation_suite_all_47_stage_indices_unique_and_present(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        for idx in range(1, 48):
            matches = [k for k in rep_def if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(dt_def, 5.0)

    def test_60_fx3_vm_coemulation_suite_skip_stage47_and_skip_phase250_config(self) -> None:
        rep_skip_p250 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_phase250_realhw_framing_usbpower_lun_antiflicker_hil=False,
            )
        )
        self.assertTrue(rep_skip_p250["all_checks_passed"])
        self.assertNotIn("stage47_realhw_framing_usbpower_lun_antiflicker_hil", rep_skip_p250)
        self.assertFalse(rep_skip_p250["config"]["include_stage47"])

        rep_skip_s47 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase45_imx510_xavc=False,
                include_phase53_hil_fault_harness=False,
                include_stage47=False,
            )
        )
        self.assertTrue(rep_skip_s47["all_checks_passed"])
        self.assertNotIn("stage47_realhw_framing_usbpower_lun_antiflicker_hil", rep_skip_s47)

    def test_61_fx3_vm_coemulation_suite_include_stage47_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--include-stage47", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn("realhw_framing_usbpower_lun_antiflicker_hil=CLEAN_ROOM_SYNTHETIC", out)

    def test_62_fx3_vm_coemulation_suite_cli_skip_phase250_and_skip_stage47(self) -> None:
        for flag in ("--skip-phase250", "--skip-stage47", "--no-include-stage47"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(["--clean-room", "--skip-phase45", "--skip-phase53", flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage47_realhw_framing_usbpower_lun_antiflicker_hil", rep)

    def test_63_run_stage47_direct_runner_matches_standalone_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s47 = suite.run_stage47_realhw_framing_usbpower_lun_antiflicker_hil(cfg)
        c1 = _get_clean_room_audit()
        self.assertEqual(s47["phase250_audit_digest_sha256"], c1["audit_digest_sha256"])

    def test_64_menu_paths_match_official_sony_ilme_fx3_help_guide(self) -> None:
        self.assertEqual(
            p250.FRAMING_SETTINGS_MENU_PATH,
            "MENU -> Shooting -> [Framing Settings]",
        )
        self.assertEqual(
            p250.SETUP_USB_MENU_PATH,
            "MENU -> Setup -> [USB]",
        )
        self.assertEqual(
            p250.ANTI_FLICKER_SHOOT_MENU_PATH,
            "MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]",
        )

    def test_65_fx3_vm_readme_documents_phase250_250th_milestone_stage47_and_47_of_47(self) -> None:
        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 250", readme)
        self.assertIn("250th", readme)
        self.assertIn("Stage 47", readme)
        self.assertIn("47/47", readme)
        self.assertIn("realhw_framing_usbpower_lun_antiflicker_coemulator.py", readme)
        self.assertIn("--include-stage47", readme)

    def test_66_zero_pyc_bytecode_files_and_sub_second_standalone_runtime(self) -> None:
        t0 = time.monotonic()
        r_clean = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil(force_clean_room=True)
        r_def = p250.run_phase250_realhw_framing_usbpower_lun_antiflicker_hil()
        elapsed = time.monotonic() - t0
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertLess(elapsed, 5.00 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 1.0)
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
