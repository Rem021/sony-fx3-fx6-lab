"""Phase 225 — Dual-mode unit tests for Pillar 33 (`Power Save Start Time` 9-condition air-gap
backup interlock, `Auto Power OFF Temp.` + `Fan Control` thermal vault & `SteadyShot Active` /
`Clear Image Zoom` `Backup.bin`/`CAMSET` parity) and unified `33/33` recovery master."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fx3_recovery
from fx3_recovery import realhw_33pillar_powersave_9cond_temp_vault_verifier as p225
from fx3_recovery.realhw_33pillar_powersave_9cond_temp_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_33_PILLAR_COUNT,
    MASTER_33_PILLAR_IDS,
    MASTER_33_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P225_AIRGAP_SAFE_POWERSAVE_TIMERS,
    P225_BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT,
    P225_BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD,
    P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD,
    P225_BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT,
    P225_BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION,
    P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE,
    P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK,
    P225_BLOCKED_INVALID_FX3_FAN_MODE,
    P225_BLOCKED_INVALID_POWERSAVE_TIMER,
    P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P225_BLOCKED_SAFETY_POLICY_VIOLATION,
    P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION,
    P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P225_BLOCKED_TIER0_LOW_BATTERY_FLOOR,
    P225_CAMSET_FILENAMES,
    P225_POWERSAVE_9_BYPASS_CONDITIONS,
    P225_POWERSAVE_DEFAULT,
    P225_STATUS_FAIL_33OF33_AGGREGATOR,
    P225_STATUS_VERIFIED_33OF33_AGGREGATOR,
    P225_STATUS_VERIFIED_PILLAR33_SUITE,
    P225_STATUS_VERIFIED_PILLAR_33A,
    P225_STATUS_VERIFIED_PILLAR_33B,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE225_SCHEMA,
    PHASE225_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    PowerSave9CondAndAutoTempVaultSpec,
    PowerSave9ConditionFlags,
    SteadyShotActiveAndCizCamsetVaultSpec,
    build_default_safe_powersave_autotemp_spec,
    build_default_safe_steadyshot_ciz_spec,
    evaluate_33pillar_recovery_master,
    evaluate_powersave_9cond_and_autotemp_fan_vault,
    evaluate_realhw_33pillar_recovery_master,
    evaluate_steadyshot_active_and_ciz_camset_vault,
    inspect_phase225_donors_readonly,
    run_pillar33_standalone_suite,
    run_pillar33a_powersave_9cond_autotemp_6_scenario_suite,
    run_pillar33b_steadyshot_ciz_camset_6_scenario_suite,
    verify_33pillar_recovery_suite,
    verify_powersave_9cond_and_autotemp_steadyshot_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


class TestPhase225SafetyAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_constants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_non_shadowing(self) -> None:
        for sym in (
            "realhw_33pillar_powersave_9cond_temp_vault_verifier",
            "MASTER_33_PILLAR_COUNT",
            "MASTER_33_PILLAR_IDS",
            "MASTER_33_PILLAR_SPECS",
            "PHASE225_SCHEMA",
            "verify_powersave_9cond_and_autotemp_steadyshot_vault",
            "evaluate_realhw_33pillar_recovery_master",
            "evaluate_33pillar_recovery_master",
            "verify_33pillar_recovery_suite",
            "run_pillar33_standalone_suite",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_32_PILLAR_COUNT, 32)
        self.assertEqual(fx3_recovery.MASTER_33_PILLAR_COUNT, 33)

    def test_03_master_33_pillar_registry_extends_32(self) -> None:
        self.assertEqual(MASTER_33_PILLAR_COUNT, 33)
        self.assertEqual(len(MASTER_33_PILLAR_SPECS), 33)
        self.assertEqual(len(MASTER_33_PILLAR_IDS), 33)
        self.assertEqual(len(set(MASTER_33_PILLAR_IDS)), 33)
        self.assertEqual([s[0] for s in MASTER_33_PILLAR_SPECS], list(range(1, 34)))
        self.assertEqual(MASTER_33_PILLAR_SPECS[:32], fx3_recovery.MASTER_32_PILLAR_SPECS)
        self.assertEqual(
            MASTER_33_PILLAR_SPECS[32],
            (
                33,
                "pillar_33_powersave_9cond_autotemp_steadyshot_vault",
                "Phase 225",
                "fx3_recovery.realhw_33pillar_powersave_9cond_temp_vault_verifier",
            ),
        )

    def test_04_powersave_9_conditions_and_camset_constants(self) -> None:
        self.assertEqual(P225_POWERSAVE_DEFAULT, "5 Min")
        self.assertEqual(P225_AIRGAP_SAFE_POWERSAVE_TIMERS, ("30 Min", "Off"))
        self.assertEqual(len(P225_POWERSAVE_9_BYPASS_CONDITIONS), 9)
        self.assertEqual(len(P225_CAMSET_FILENAMES), 10)
        self.assertEqual(P225_CAMSET_FILENAMES[0], "CAMSET01.DAT")
        self.assertEqual(P225_CAMSET_FILENAMES[-1], "CAMSET10.DAT")


class TestPhase225ReadOnlyDonorInspection(unittest.TestCase):
    def test_05_donor_inspect_default_mode_under_budget(self) -> None:
        snap = inspect_phase225_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_06_donor_inspect_forced_clean_room(self) -> None:
        snap = inspect_phase225_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_07_donor_inspect_env_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase225_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_08_donor_open_uses_strict_o_rdonly_flags_never_write(self) -> None:
        observed_flags = []
        real_open = os.open

        def _spy_open(path: str, flags: int, *args: object) -> int:
            observed_flags.append(flags)
            return real_open(path, flags, *args)

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
            with mock.patch("os.open", side_effect=_spy_open):
                snap = inspect_phase225_donors_readonly(force_clean_room=False)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(observed_flags), 6)
            for fl in observed_flags:
                self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)

    def test_09_donor_missing_file_falls_back_to_clean_room_synthetic(self) -> None:
        with mock.patch.object(p225, "resolve_donor_path", return_value=None):
            snap = inspect_phase225_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)


class TestPillar33APowerSave9CondAndAutoTempVault(unittest.TestCase):
    def test_10_default_safe_30min_airgap_battery_spec_passes(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(build_default_safe_powersave_autotemp_spec())
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_PILLAR_33A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.bypass_condition_count, 0)
        self.assertFalse(rep.powersave_auto_deactivated)
        self.assertTrue(rep.airgap_cold_dump_antisleep_verified)
        self.assertTrue(rep.auto_power_off_temp_verified)
        self.assertTrue(rep.fan_prebackup_cooldown_verified)
        self.assertTrue(rep.h0_equals_h3_verified)

    def test_11_airgap_powersave_off_passes_without_bypass(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(power_save_start_time="Off")
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.airgap_cold_dump_antisleep_verified)

    def test_12_airgap_short_powersave_timers_blocked_when_no_bypass(self) -> None:
        for short_timer in ("10 Sec", "1 Min", "2 Min", "5 Min"):
            with self.subTest(timer=short_timer):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(
                        power_save_start_time=short_timer,
                        bypass_flags=PowerSave9ConditionFlags(),
                        air_gapped_internal_battery=True,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_AIRGAP_POWERSAVE_SLEEP_HAZARD)

    def test_13_each_of_9_bypass_conditions_individually_deactivates_powersave(self) -> None:
        for cond_name in P225_POWERSAVE_9_BYPASS_CONDITIONS:
            with self.subTest(condition=cond_name):
                flags = PowerSave9ConditionFlags(**{cond_name: True})
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(
                        power_save_start_time="5 Min",
                        bypass_flags=flags,
                        strict_airgap_enforced=False,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.powersave_auto_deactivated)
                self.assertEqual(rep.active_bypass_conditions, (cond_name,))
                self.assertEqual(rep.bypass_condition_count, 1)

    def test_14_strict_airgap_blocks_network_and_pc_bypasses(self) -> None:
        for net_cond in ("ftp_transfer", "pc_connection", "streaming_or_creators_cloud"):
            with self.subTest(net_cond=net_cond):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(
                        power_save_start_time="5 Min",
                        bypass_flags=PowerSave9ConditionFlags(**{net_cond: True}),
                        strict_airgap_enforced=True,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_AIRGAP_NETWORK_BYPASS_CONFLICT)

    def test_15_strict_airgap_allows_local_hardware_bypasses(self) -> None:
        for hw_cond in (
            "usb_power_supply",
            "slideshow_playback",
            "movie_recording",
            "tv_hdmi_connection",
            "ir_remote_ctrl_on",
            "bluetooth_rmt_ctrl_on",
        ):
            with self.subTest(hw_cond=hw_cond):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(
                        power_save_start_time="5 Min",
                        bypass_flags=PowerSave9ConditionFlags(**{hw_cond: True}),
                        strict_airgap_enforced=True,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.powersave_auto_deactivated)

    def test_16_invalid_powersave_timer_rejected(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(power_save_start_time="15 Min")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_INVALID_POWERSAVE_TIMER)

    def test_17_low_np_fz100_battery_blocked_below_51pct(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(battery_pct=50)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_TIER0_LOW_BATTERY_FLOOR)

    def test_18_battery_low_warning_blocked_even_with_usb_pd(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(
                battery_pct=70,
                battery_low_warning=True,
                bypass_flags=PowerSave9ConditionFlags(usb_power_supply=True),
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_TIER0_LOW_BATTERY_FLOOR)

    def test_19_autotemp_high_tripod_mounted_passes(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(
                auto_power_off_temp="High",
                tripod_mounted=True,
                handheld_prolonged_operation=False,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.auto_power_off_temp_verified)

    def test_20_autotemp_high_without_tripod_or_handheld_blocked(self) -> None:
        for tripod, handheld in ((False, False), (True, True), (False, True)):
            with self.subTest(tripod=tripod, handheld=handheld):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(
                        auto_power_off_temp="High",
                        tripod_mounted=tripod,
                        handheld_prolonged_operation=handheld,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD)

    def test_21_autotemp_invalid_token_blocked(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(auto_power_off_temp="UltraHigh")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_AUTOTEMP_HIGH_HANDHELD_BURN_HAZARD)

    def test_22_fan_always_off_prebackup_cooldown_to_auto_passes(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(
                configured_fan_control="Always Off",
                pre_backup_fan_cooldown_to_auto=True,
                effective_fan_control="Auto",
                soc_temp_c=61.0,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.fan_prebackup_cooldown_verified)

    def test_23_fan_always_off_without_cooldown_to_auto_blocked(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(
                configured_fan_control="Always Off",
                pre_backup_fan_cooldown_to_auto=False,
                effective_fan_control="Always Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK)

    def test_24_fan_invalid_fx6_auto1_auto2_tokens_blocked(self) -> None:
        for bad_fan in ("Auto1", "Auto2", "Fast"):
            with self.subTest(bad_fan=bad_fan):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(configured_fan_control=bad_fan)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_INVALID_FX3_FAN_MODE)

    def test_25_soc_overheat_or_thermal_warning_before_backup_blocked(self) -> None:
        for temp_c, warn in ((85.0, False), (88.4, False), (72.0, True)):
            with self.subTest(temp_c=temp_c, warn=warn):
                rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
                    PowerSave9CondAndAutoTempVaultSpec(soc_temp_c=temp_c, thermal_shutdown_warning=warn)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_FAN_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK)

    def test_26_pillar33a_persistent_overlay_escape_and_h0_h3_drift_blocked(self) -> None:
        rep_esc = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(overlay_dir="/setting/powersave_patch")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_drift = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_27_pillar33a_persistent_unlock_request_blocked(self) -> None:
        rep = evaluate_powersave_9cond_and_autotemp_fan_vault(
            PowerSave9CondAndAutoTempVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_28_pillar33a_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar33a_powersave_9cond_autotemp_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P225_STATUS_VERIFIED_PILLAR_33A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestPillar33BSteadyShotActiveAndCizCamsetVault(unittest.TestCase):
    def test_29_default_safe_steadyshot_active_and_ciz_spec_passes(self) -> None:
        rep = evaluate_steadyshot_active_and_ciz_camset_vault(build_default_safe_steadyshot_ciz_spec())
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_PILLAR_33B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.steadyshot_cutoff_verified)
        self.assertTrue(rep.ciz_availability_verified)
        self.assertTrue(rep.ciz_four_state_locks_verified)
        self.assertTrue(rep.camset_slot1_profile_parity_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_surfaces_intact, 16)

    def test_30_steadyshot_active_blocked_at_11988p_and_100p(self) -> None:
        for hfr in ("119.88p", "100p"):
            with self.subTest(hfr=hfr):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(
                        steadyshot_mode="Active",
                        rec_frame_rate=hfr,
                        zoom_range="Optical zoom only",
                        current_zoom_scale=1.0,
                        saved_profile_zoom_range="Optical zoom only",
                        restored_profile_zoom_range="Optical zoom only",
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION)

    def test_31_steadyshot_active_blocked_at_sq_100_120_200_240fps(self) -> None:
        for sq_fps in (100, 120, 200, 240):
            with self.subTest(sq_fps=sq_fps):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(
                        steadyshot_mode="Active",
                        sq_mode_enabled=True,
                        sq_frame_rate_fps=sq_fps,
                        zoom_range="Optical zoom only",
                        current_zoom_scale=1.0,
                        saved_profile_zoom_range="Optical zoom only",
                        restored_profile_zoom_range="Optical zoom only",
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION)

    def test_32_steadyshot_active_blocked_when_hdmi_raw_output_enabled(self) -> None:
        rep = evaluate_steadyshot_active_and_ciz_camset_vault(
            SteadyShotActiveAndCizCamsetVaultSpec(
                steadyshot_mode="Active",
                hdmi_raw_output_enabled=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION)

    def test_33_steadyshot_active_blocked_if_1_1x_crop_unacknowledged(self) -> None:
        rep = evaluate_steadyshot_active_and_ciz_camset_vault(
            SteadyShotActiveAndCizCamsetVaultSpec(
                steadyshot_mode="Active",
                active_crop_factor_acknowledged=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P225_BLOCKED_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION)

    def test_34_steadyshot_standard_and_off_allowed_with_hfr_and_hdmi_raw(self) -> None:
        for mode in ("Standard", "Off"):
            with self.subTest(mode=mode):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(
                        steadyshot_mode=mode,
                        rec_frame_rate="119.88p",
                        hdmi_raw_output_enabled=True,
                        zoom_range="Optical zoom only",
                        current_zoom_scale=1.0,
                        saved_profile_steadyshot=mode,
                        restored_profile_steadyshot=mode,
                        saved_profile_zoom_range="Optical zoom only",
                        restored_profile_zoom_range="Optical zoom only",
                    )
                )
                self.assertTrue(rep.passed)

    def test_35_ciz_and_digital_zoom_blocked_in_still_raw_formats(self) -> None:
        for raw_fmt in ("RAW", "RAW & JPEG", "RAW & HEIF"):
            with self.subTest(raw_fmt=raw_fmt):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(
                        zoom_range="Clear Image Zoom",
                        still_file_format=raw_fmt,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE)

    def test_36_ciz_and_digital_zoom_blocked_in_hfr_and_sq(self) -> None:
        for zr in ("Clear Image Zoom", "Digital Zoom"):
            rep_hfr = evaluate_steadyshot_active_and_ciz_camset_vault(
                SteadyShotActiveAndCizCamsetVaultSpec(
                    steadyshot_mode="Standard",
                    rec_frame_rate="100p",
                    zoom_range=zr,
                    saved_profile_steadyshot="Standard",
                    restored_profile_steadyshot="Standard",
                    saved_profile_zoom_range=zr,
                    restored_profile_zoom_range=zr,
                )
            )
            self.assertFalse(rep_hfr.passed)
            self.assertEqual(rep_hfr.block_code, P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE)

            rep_sq = evaluate_steadyshot_active_and_ciz_camset_vault(
                SteadyShotActiveAndCizCamsetVaultSpec(
                    steadyshot_mode="Standard",
                    sq_mode_enabled=True,
                    sq_frame_rate_fps=240,
                    zoom_range=zr,
                    saved_profile_steadyshot="Standard",
                    restored_profile_steadyshot="Standard",
                    saved_profile_zoom_range=zr,
                    restored_profile_zoom_range=zr,
                )
            )
            self.assertFalse(rep_sq.passed)
            self.assertEqual(rep_sq.block_code, P225_BLOCKED_CIZ_HFR_OR_RAW_UNAVAILABLE)

    def test_37_ciz_each_of_4_automatic_state_locks_enforced(self) -> None:
        bad_overrides = (
            {"focus_area_disabled_center_locked": False},
            {"effective_metering_mode": "Center"},
            {"effective_metering_mode": "Spot"},
            {"face_eye_prior_af_available": True},
            {"face_priority_multi_metering_available": True},
            {"realtime_tracking_available": True},
        )
        for kw in bad_overrides:
            with self.subTest(override=kw):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(
                        zoom_range="Clear Image Zoom",
                        current_zoom_scale=1.5,
                        **kw,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_CIZ_AF_METERING_TRACKING_LOCK_VIOLATION)

    def test_38_camset_01_through_10_on_slot1_all_pass(self) -> None:
        for fname in P225_CAMSET_FILENAMES:
            with self.subTest(fname=fname):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(camset_filename=fname, camset_slot=1)
                )
                self.assertTrue(rep.passed)

    def test_39_camset_slot2_or_invalid_filename_or_profile_drift_blocked(self) -> None:
        for bad_kw in (
            {"camset_slot": 2},
            {"camset_filename": "CAMSET11.DAT"},
            {"restored_profile_powersave": "5 Min"},
            {"restored_profile_autotemp": "High"},
            {"restored_profile_steadyshot": "Off"},
            {"restored_profile_zoom_range": "Digital Zoom"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_steadyshot_active_and_ciz_camset_vault(
                    SteadyShotActiveAndCizCamsetVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P225_BLOCKED_CAMSET_OR_BACKUP_PROFILE_PARITY_DRIFT)

    def test_40_pillar33b_overlay_escape_and_h0_h3_drift_blocked(self) -> None:
        rep_esc = evaluate_steadyshot_active_and_ciz_camset_vault(
            SteadyShotActiveAndCizCamsetVaultSpec(stage_b_overlay_dir="/dev/cnflasha/ciz")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P225_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_drift = evaluate_steadyshot_active_and_ciz_camset_vault(
            SteadyShotActiveAndCizCamsetVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P225_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_41_pillar33b_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar33b_steadyshot_ciz_camset_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P225_STATUS_VERIFIED_PILLAR_33B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestPillar33CombinedAnd33PillarMaster(unittest.TestCase):
    def test_42_combined_pillar33_verifier_normal_mode(self) -> None:
        rep = verify_powersave_9cond_and_autotemp_steadyshot_vault()
        self.assertTrue(rep.all_passed)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_PILLAR33_SUITE)
        self.assertEqual(rep.schema, PHASE225_SCHEMA)
        self.assertEqual(rep.version, PHASE225_VERSION)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_43_combined_pillar33_verifier_clean_room_mode(self) -> None:
        rep = verify_powersave_9cond_and_autotemp_steadyshot_vault(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_PILLAR33_SUITE)

    def test_44_pillar33_standalone_suite_normal_and_clean_room(self) -> None:
        rep_norm = run_pillar33_standalone_suite()
        self.assertTrue(rep_norm.all_passed)
        self.assertEqual(rep_norm.pillar_33a_powersave_autotemp_vault.scenarios_passed, 6)
        self.assertEqual(rep_norm.pillar_33b_steadyshot_ciz_vault.scenarios_passed, 6)
        self.assertEqual(len(rep_norm.suite_sha256), 64)

        rep_cr = run_pillar33_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr.all_passed)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(len(rep_cr.suite_sha256), 64)

    def test_45_master_33pillar_aggregator_normal_mode(self) -> None:
        rep = evaluate_realhw_33pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_33OF33_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 33)
        self.assertEqual(rep.pillars_passed, 33)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertEqual(len(rep.pillars), 33)
        self.assertEqual(rep.pillars[-1].pillar_number, 33)
        self.assertEqual(rep.pillars[-1].pillar_id, "pillar_33_powersave_9cond_autotemp_steadyshot_vault")
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)

    def test_46_master_33pillar_aggregator_clean_room_mode(self) -> None:
        rep = evaluate_realhw_33pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P225_STATUS_VERIFIED_33OF33_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 33)
        self.assertEqual(rep.pillar_count, 33)
        self.assertTrue(all(p.verification_mode == "CLEAN_ROOM_SYNTHETIC" for p in rep.pillars))

    def test_47_master_33pillar_deterministic_sha256_in_clean_room(self) -> None:
        r1 = evaluate_33pillar_recovery_master(force_clean_room=True)
        r2 = verify_33pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_33pillar_sha256, r2.master_33pillar_sha256)
        self.assertEqual(len(r1.master_33pillar_sha256), 64)

    def test_48_master_33pillar_fault_injection_on_pillar_33(self) -> None:
        rep = evaluate_realhw_33pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_33_powersave_9cond_autotemp_steadyshot_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P225_STATUS_FAIL_33OF33_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 32)
        self.assertEqual(rep.failed_pillars, ("pillar_33_powersave_9cond_autotemp_steadyshot_vault",))

    def test_49_master_33pillar_fault_injection_on_pillar_1(self) -> None:
        first_id = MASTER_33_PILLAR_IDS[0]
        rep = evaluate_realhw_33pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=first_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 32)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_50_master_33pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_33pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_51_json_serialization_roundtrip(self) -> None:
        rep = evaluate_realhw_33pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P225_STATUS_VERIFIED_33OF33_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 33)
        self.assertEqual(decoded["pillars_passed"], 33)


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_52_backward_compatibility_with_32pillar_master(self) -> None:
        rep32 = fx3_recovery.evaluate_realhw_32pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep32.all_passed)
        self.assertEqual(rep32.pillar_count, 32)
        self.assertEqual(rep32.pillars_passed, 32)

    def test_53_backward_compatibility_across_22_to_31_pillar_masters(self) -> None:
        for count, fn in (
            (22, fx3_recovery.evaluate_22pillar_recovery_master),
            (24, fx3_recovery.evaluate_24pillar_recovery_master),
            (26, fx3_recovery.evaluate_26pillar_recovery_master),
            (27, fx3_recovery.evaluate_27pillar_recovery_master),
            (28, fx3_recovery.evaluate_28pillar_recovery_master),
            (29, fx3_recovery.evaluate_29pillar_recovery_master),
            (30, fx3_recovery.evaluate_realhw_30pillar_recovery_master),
            (31, fx3_recovery.evaluate_realhw_31pillar_recovery_master),
        ):
            with self.subTest(pillars=count):
                rep = fn(force_clean_room=True)
                self.assertTrue(rep.all_passed)
                self.assertEqual(rep.pillar_count, count)

    def _run_cli(self, *cli_args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", *cli_args],
            cwd=str(ADAPTER_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_54_cli_verify_powersave_9cond_temp_vault_json(self) -> None:
        proc = self._run_cli("verify-powersave-9cond-temp-vault", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P225_STATUS_VERIFIED_PILLAR33_SUITE)

    def test_55_cli_verify_powersave_9cond_temp_vault_clean_room_summary(self) -> None:
        proc = self._run_cli("verify-powersave-9cond-temp-vault", "--clean-room")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_PILLAR33_POWERSAVE_9COND_AUTOTEMP_STEADYSHOT_VAULT", proc.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
        self.assertIn("pillar_33a=6/6", proc.stdout)
        self.assertIn("pillar_33b=6/6", proc.stdout)

    def test_56_cli_verify_33pillar_recovery_normal_json(self) -> None:
        proc = self._run_cli("verify-33pillar-recovery", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P225_STATUS_VERIFIED_33OF33_AGGREGATOR)
        self.assertEqual(data["pillar_count"], 33)
        self.assertEqual(data["pillars_passed"], 33)

    def test_57_cli_verify_33pillar_recovery_clean_room_env_and_flag(self) -> None:
        proc = self._run_cli(
            "verify-33pillar-recovery",
            "--force-clean-room",
            "--json",
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["pillars_passed"], 33)

    def test_58_cli_verify_33pillar_recovery_out_directory(self) -> None:
        import shutil

        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p225_m33_{os.getpid()}"
        p33_dir = here / f"_tmp_p225_p33_{os.getpid()}"
        for d in (out_dir, p33_dir):
            if d.exists():
                shutil.rmtree(d)
        try:
            proc = self._run_cli("verify-33pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            report_file = out_dir / "33pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], P225_STATUS_VERIFIED_33OF33_AGGREGATOR)
            self.assertEqual(saved["pillars_passed"], 33)

            proc_dup = self._run_cli("verify-33pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc_dup.returncode, 2)

            proc_p33 = self._run_cli("verify-powersave-9cond-temp-vault", "--clean-room", "--out", str(p33_dir))
            self.assertEqual(proc_p33.returncode, 0, msg=proc_p33.stderr or proc_p33.stdout)
            self.assertTrue((p33_dir / "pillar33-powersave-9cond-temp-vault-report.json").is_file())
        finally:
            for d in (out_dir, p33_dir):
                if d.exists():
                    shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
