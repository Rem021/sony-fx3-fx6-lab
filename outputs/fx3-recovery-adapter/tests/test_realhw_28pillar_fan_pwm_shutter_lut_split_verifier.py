"""Phase 198 (Pillar 28 / 28/28 Recovery Master) Dual-Mode Fast Unit Tests (52 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection, bounded 4 KiB reads, FX3_FX6_FORCE_CLEAN_ROOM=1
  fallback, determinism, zero raw firmware bytes in JSON & Master 28-pillar registry
- Group A (11..23): Pillar 28A — ILME-FX3 exact 4-mode [Fan Control] (Auto, Minimum, Off in Rec,
  Always Off — rejecting Auto1/Auto2), Always Off -> Auto pre-backup (75 MiB p3 AdjustControl 0x40)
  & Stage-B thermal interlock, Standard/High Auto Power OFF Temp, Off in Rec MAX PWM vs 0% + >=82C
  emergency thermal override
- Group B (24..36): Pillar 28B — Ver. 6.01 vs Ver. 7.00/7.02 p2:/setting User1..User16 LUT binary
  slot anti-pollution (/tmp/fx6_lut_overlay tmpfs isolation) & independent Backup.bin Shutter
  [Speed]/[Angle] slot integrity (5.6°..64F normal vs 119.88p/100p & S&Q 5.6°..360°, 0.3EV/0.5EV
  Exposure step decoupling, 16/16 H0 == H3)
- Group C (37..46): Pillar 28 standalone, Unified 28/28 Recovery Master in LOCAL_DONOR_O_RDONLY &
  CLEAN_ROOM_SYNTHETIC (<6.0s ceiling), safety counters == 0, fault_inject_pillar & 22/24/26/27 compat
- Group D (47..52): CLI `verify-fan-pwm-lut-split-vault` & `verify-28pillar-recovery` + 22/24/26/27 CLI
"""

from __future__ import annotations

from contextlib import redirect_stdout
import dataclasses
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import typing
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery import realhw_28pillar_fan_pwm_shutter_lut_split_verifier as p28_mod
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import evaluate_22pillar_recovery_master
from fx3_recovery.realhw_24pillar_master_recovery_verifier import evaluate_24pillar_recovery_master
from fx3_recovery.realhw_26pillar_master_recovery_verifier import evaluate_26pillar_recovery_master
from fx3_recovery.realhw_27pillar_dcc1_pd_lut_vault_verifier import (
    MASTER_27_PILLAR_IDS,
    evaluate_27pillar_recovery_master,
)
from fx3_recovery.realhw_28pillar_fan_pwm_shutter_lut_split_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_28_PILLAR_COUNT,
    MASTER_28_PILLAR_IDS,
    MASTER_28_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P198_AUTO_POWER_OFF_TEMP_HIGH,
    P198_AUTO_POWER_OFF_TEMP_STANDARD,
    P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK,
    P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE,
    P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION,
    P198_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP,
    P198_BLOCKED_NON_TMPFS_LUT_OVERLAY_PATH,
    P198_BLOCKED_OFF_IN_REC_PWM_CURVE_VIOLATION,
    P198_BLOCKED_SAFETY_POLICY_VIOLATION,
    P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE,
    P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER,
    P198_BLOCKED_SOC_OVERHEAT_PREBACKUP_ABORT,
    P198_BLOCKED_UNKNOWN_FAN_STAGE_OPERATION,
    P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT,
    P198_CONCURRENT_CEILING_SECONDS,
    P198_DONOR_FX3_APPFW_702_RELPATH,
    P198_DONOR_FX3_BACKUP_BIN_RELPATH,
    P198_DONOR_FX3_BODYDATA_RELPATH,
    P198_DONOR_FX3_LIBBACKUP_SO_RELPATH,
    P198_DONOR_FX3_LIBFAN_SO_RELPATH,
    P198_DONOR_FX6_APPFW_601_RELPATH,
    P198_FAN_MODE_ALWAYS_OFF,
    P198_FAN_MODE_AUTO,
    P198_FAN_MODE_MINIMUM,
    P198_FAN_MODE_OFF_IN_REC,
    P198_FX3_EXACT_4_FAN_MODES,
    P198_HIGH_FPS_RATES_NARROWED_360,
    P198_LUT_GEN_LEGACY_601,
    P198_LUT_GEN_OPTIMIZED_700_PLUS,
    P198_NOMINAL_BUDGET_SECONDS,
    P198_NORMAL_FPS_RATES_ALLOWING_64F,
    P198_OP_COLD_BACKUP_P3_75MIB,
    P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL,
    P198_OP_STOCK_SHOOTING_OBSERVATION,
    P198_P3_COLD_BACKUP_MIB,
    P198_PILLAR_28A_SCENARIO_IDS,
    P198_PILLAR_28B_SCENARIO_IDS,
    P198_PINNED_FX3_APPFW_702_BYTES,
    P198_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P198_PINNED_FX3_BACKUP_BIN_SHA256,
    P198_PINNED_FX3_BODYDATA_BYTES,
    P198_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P198_PINNED_FX3_LIBBACKUP_SO_SHA256,
    P198_PINNED_FX3_LIBFAN_SO_BYTES,
    P198_PINNED_FX3_LIBFAN_SO_SHA256,
    P198_PINNED_FX6_APPFW_601_BYTES,
    P198_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG,
    P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG,
    P198_SHUTTER_MIN_ANGLE_DEG,
    P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR,
    P198_STATUS_FAIL_28OF28_AGGREGATOR,
    P198_STATUS_VERIFIED_28OF28_AGGREGATOR,
    P198_STATUS_VERIFIED_PILLAR28_SUITE,
    P198_STATUS_VERIFIED_PILLAR_28A,
    P198_STATUS_VERIFIED_PILLAR_28B,
    P198_USER_LUT_SLOT_NAMES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE198_SCHEMA,
    PHASE198_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    FanPwmThermalInterlockSpec,
    LutSplitShutterVaultSpec,
    Master28PillarRecoveryReport,
    evaluate_28pillar_recovery_master,
    evaluate_fan_pwm_prebackup_thermal_interlock,
    evaluate_lut_split_and_shutter_angle_vault,
    inspect_phase198_donors_readonly,
    run_pillar28_standalone_suite,
    run_pillar28a_fan_pwm_thermal_6_scenario_suite,
    run_pillar28b_lut_split_shutter_6_scenario_suite,
    verify_28pillar_recovery_suite,
)

_BYTES_REPR_RE = re.compile(r"(?:^|[^A-Za-z0-9_])b['\"]")


def _walk_check_no_bytes(node: object) -> None:
    if isinstance(node, (bytes, bytearray, memoryview)):
        raise AssertionError(f"Raw binary object {type(node).__name__} leaked into JSON payload")
    if isinstance(node, str):
        assert not _BYTES_REPR_RE.search(node), f"Raw bytes repr leaked in string: {node!r}"
        return
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_check_no_bytes(k)
            _walk_check_no_bytes(v)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk_check_no_bytes(item)


def _assert_json_has_no_raw_bytes(obj: object) -> str:
    _walk_check_no_bytes(obj)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False)


class TestRealHw28PillarFanPwmShutterLutSplitVerifier(unittest.TestCase):
    _cached_clean_master: Master28PillarRecoveryReport | None = None
    _cached_default_master: Master28PillarRecoveryReport | None = None
    _cached_default_dt: float = 0.0
    _cached_clean_dt: float = 0.0

    @classmethod
    def _clean_master(cls) -> Master28PillarRecoveryReport:
        if cls._cached_clean_master is None:
            t0 = time.monotonic()
            cls._cached_clean_master = verify_28pillar_recovery_suite(force_clean_room=True)
            cls._cached_clean_dt = time.monotonic() - t0
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master28PillarRecoveryReport:
        if cls._cached_default_master is None:
            t0 = time.monotonic()
            cls._cached_default_master = verify_28pillar_recovery_suite()
            cls._cached_default_dt = time.monotonic() - t0
        return cls._cached_default_master

    # ------------------------------------------------------------------
    # Group 0 (01..10): Safety Constants, Exports & Donor O_RDONLY Audit
    # ------------------------------------------------------------------

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
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_zero_shadowing(self) -> None:
        self.assertIn("realhw_28pillar_fan_pwm_shutter_lut_split_verifier", fx3_recovery.__all__)
        self.assertIn("evaluate_28pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_28pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_fan_pwm_prebackup_thermal_interlock", fx3_recovery.__all__)
        self.assertIn("evaluate_lut_split_and_shutter_angle_vault", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.evaluate_28pillar_recovery_master, evaluate_28pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_28pillar_recovery_suite, verify_28pillar_recovery_suite)
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_26pillar_recovery_master, evaluate_26pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_27pillar_recovery_master, evaluate_27pillar_recovery_master)
        hints = typing.get_type_hints(p28_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase198_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_702_bytes, P198_PINNED_FX3_BODYDATA_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertTrue(snap.fx3_appfw_702_elf64_ok)
        self.assertTrue(snap.fx6_appfw_601_elf64_ok)
        self.assertTrue(snap.lut_601_vs_702_binary_split_confirmed)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertTrue(snap.libfan_so_elf64_ok)
        self.assertTrue(snap.libbackup_so_elf64_ok)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p28_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase198_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase198_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P198_DONOR_FX3_BODYDATA_RELPATH,
                P198_DONOR_FX3_APPFW_702_RELPATH,
                P198_DONOR_FX6_APPFW_601_RELPATH,
                P198_DONOR_FX3_BACKUP_BIN_RELPATH,
                P198_DONOR_FX3_LIBFAN_SO_RELPATH,
                P198_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            )
        )
        if not donors_present or p28_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 / FX6 6.01 / libfan.so local donors unavailable or clean-room forced")

        flags_seen: list[int] = []
        pread_sizes: list[int] = []
        real_open = os.open
        real_pread = os.pread

        def spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            flags_seen.append(flags)
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        def spy_pread(fd: int, length: int, offset: int) -> bytes:
            pread_sizes.append(length)
            return real_pread(fd, length, offset)

        with mock.patch.object(p28_mod.os, "open", side_effect=spy_open), mock.patch.object(
            p28_mod.os, "pread", side_effect=spy_pread
        ):
            snap = inspect_phase198_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(snap.lut_601_vs_702_binary_split_confirmed)
        for fl in flags_seen:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
            self.assertTrue(fl & os.O_NOFOLLOW)
            self.assertTrue(fl & os.O_NONBLOCK)
        self.assertEqual(pread_sizes, [4096, 4096, 4096])
        self.assertEqual(snap.artifacts[0].sha256_digest, P198_PINNED_FX3_BODYDATA_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[1].sha256_digest, P198_PINNED_FX3_APPFW_702_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[2].sha256_digest, P198_PINNED_FX6_APPFW_601_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[3].sha256_digest, P198_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(snap.artifacts[4].sha256_digest, P198_PINNED_FX3_LIBFAN_SO_SHA256)
        self.assertEqual(snap.artifacts[5].sha256_digest, P198_PINNED_FX3_LIBBACKUP_SO_SHA256)

    def test_07_clean_room_snapshot_determinism(self) -> None:
        s1 = inspect_phase198_donors_readonly(force_clean_room=True)
        s2 = inspect_phase198_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        self.assertEqual(s1.artifacts, s2.artifacts)

    def test_08_zero_raw_firmware_bytes_in_json_reports(self) -> None:
        standalone = run_pillar28_standalone_suite(force_clean_room=True).to_dict()
        master = self._clean_master().to_dict()
        j1 = _assert_json_has_no_raw_bytes(standalone)
        j2 = _assert_json_has_no_raw_bytes(master)
        self.assertIn(PHASE198_SCHEMA, j1)
        self.assertIn(P198_STATUS_VERIFIED_28OF28_AGGREGATOR, j2)

    def test_09_master_28_pillar_registry_matches_1_through_28(self) -> None:
        self.assertEqual(MASTER_28_PILLAR_COUNT, 28)
        self.assertEqual(len(MASTER_28_PILLAR_SPECS), 28)
        self.assertEqual(tuple(s[0] for s in MASTER_28_PILLAR_SPECS), tuple(range(1, 29)))
        self.assertEqual(MASTER_28_PILLAR_IDS[:27], MASTER_27_PILLAR_IDS)
        self.assertEqual(MASTER_28_PILLAR_IDS[27], "realhw_28pillar_fan_pwm_shutter_lut_split_verifier")

    def test_10_pinned_wave25_fan_shutter_and_lut_split_constants(self) -> None:
        self.assertEqual(P198_FX3_EXACT_4_FAN_MODES, ("Auto", "Minimum", "Off in Rec", "Always Off"))
        self.assertEqual(P198_PINNED_FX3_APPFW_702_BYTES, 79_015_712)
        self.assertEqual(P198_PINNED_FX6_APPFW_601_BYTES, 50_520_424)
        self.assertEqual(P198_PINNED_FX3_LIBFAN_SO_BYTES, 27_280)
        self.assertEqual(P198_P3_COLD_BACKUP_MIB, 75)
        self.assertEqual(P198_NOMINAL_BUDGET_SECONDS, 2.4)
        self.assertEqual(P198_CONCURRENT_CEILING_SECONDS, 6.0)
        self.assertEqual(P198_SHUTTER_MIN_ANGLE_DEG, 5.6)
        self.assertEqual(P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG, 360.0)
        self.assertEqual(P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG, 23040.0)
        self.assertEqual(P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR, "/tmp/fx6_lut_overlay")
        self.assertEqual(len(P198_USER_LUT_SLOT_NAMES), 16)

    # ------------------------------------------------------------------
    # Group A (11..23): Pillar 28A — 4-Mode Fan PWM & Thermal Interlock
    # ------------------------------------------------------------------

    def test_11_pillar28a_exact_4_fan_modes_accepted_in_shooting_observation(self) -> None:
        for mode in P198_FX3_EXACT_4_FAN_MODES:
            rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                FanPwmThermalInterlockSpec(
                    stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                    stock_fan_control_mode=mode,
                )
            )
            self.assertTrue(rep.passed, f"Expected valid FX3 fan mode {mode} to pass")
            self.assertTrue(rep.fan_mode_enum_valid)
            self.assertTrue(rep.bogus_auto1_auto2_rejected)

    def test_12_pillar28a_prebackup_75mib_p3_and_stage_b_admit_auto_standard_and_high(self) -> None:
        for op in (P198_OP_COLD_BACKUP_P3_75MIB, P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL):
            for apo in (P198_AUTO_POWER_OFF_TEMP_STANDARD, P198_AUTO_POWER_OFF_TEMP_HIGH):
                rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                    FanPwmThermalInterlockSpec(
                        stage_operation=op,
                        stock_fan_control_mode=P198_FAN_MODE_AUTO,
                        auto_power_off_temp=apo,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.stage_entry_admitted)
                self.assertFalse(rep.pre_backup_aborted)
                self.assertEqual(rep.p3_cold_backup_size_mib, 75)

    def test_13_pillar28a_always_off_switched_to_auto_admitted_before_backup_and_stage_b(self) -> None:
        rep = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_COLD_BACKUP_P3_75MIB,
                stock_fan_control_mode=P198_FAN_MODE_ALWAYS_OFF,
                switched_to_auto_before_stage=True,
                auto_power_off_temp=P198_AUTO_POWER_OFF_TEMP_HIGH,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.stage_entry_admitted)
        self.assertEqual(rep.effective_fan_mode, P198_FAN_MODE_AUTO)
        self.assertGreater(rep.expected_pwm_duty_pct, 0)

    def test_14_pillar28a_always_off_left_active_aborts_75mib_p3_cold_backup_and_stage_b(self) -> None:
        for op in (P198_OP_COLD_BACKUP_P3_75MIB, P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL):
            rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                FanPwmThermalInterlockSpec(
                    stage_operation=op,
                    stock_fan_control_mode=P198_FAN_MODE_ALWAYS_OFF,
                    switched_to_auto_before_stage=False,
                )
            )
            self.assertFalse(rep.passed)
            self.assertTrue(rep.pre_backup_aborted)
            self.assertIn(P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK, rep.blocked_codes)

    def test_15_pillar28a_minimum_or_off_in_rec_aborts_75mib_p3_backup_until_auto(self) -> None:
        for mode in (P198_FAN_MODE_MINIMUM, P198_FAN_MODE_OFF_IN_REC):
            rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                FanPwmThermalInterlockSpec(
                    stage_operation=P198_OP_COLD_BACKUP_P3_75MIB,
                    stock_fan_control_mode=mode,
                )
            )
            self.assertFalse(rep.passed)
            self.assertTrue(rep.pre_backup_aborted)
            self.assertIn(P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK, rep.blocked_codes)

    def test_16_pillar28a_rejects_bogus_auto1_auto2_and_non_fx3_fan_tokens(self) -> None:
        for bogus in ("Auto1", "Auto2", "auto_1", "auto_2", "Normal", "Fast", "Slow"):
            rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                FanPwmThermalInterlockSpec(
                    stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                    stock_fan_control_mode=bogus,
                )
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.fan_mode_enum_valid)
            self.assertFalse(rep.bogus_auto1_auto2_rejected)
            self.assertIn(P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE, rep.blocked_codes)

    def test_17_pillar28a_off_in_rec_standby_max_pwm_vs_recording_zero_pwm(self) -> None:
        r_standby = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                stock_fan_control_mode=P198_FAN_MODE_OFF_IN_REC,
                is_recording=False,
                soc_temp_c=50.0,
            )
        )
        r_rec = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                stock_fan_control_mode=P198_FAN_MODE_OFF_IN_REC,
                is_recording=True,
                soc_temp_c=55.0,
            )
        )
        self.assertTrue(r_standby.passed)
        self.assertEqual(r_standby.expected_pwm_duty_pct, 100)
        self.assertTrue(r_rec.passed)
        self.assertEqual(r_rec.expected_pwm_duty_pct, 0)

    def test_18_pillar28a_off_in_rec_emergency_thermal_override_forces_100pct_pwm(self) -> None:
        rep = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                stock_fan_control_mode=P198_FAN_MODE_OFF_IN_REC,
                is_recording=True,
                soc_temp_c=82.5,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.emergency_thermal_override_engaged)
        self.assertEqual(rep.expected_pwm_duty_pct, 100)

    def test_19_pillar28a_blocks_off_in_rec_pwm_curve_inversion(self) -> None:
        rep = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
                stock_fan_control_mode=P198_FAN_MODE_OFF_IN_REC,
                observed_standby_pwm_pct=40,
                observed_recording_pwm_pct=40,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.off_in_rec_curve_verified)
        self.assertIn(P198_BLOCKED_OFF_IN_REC_PWM_CURVE_VIOLATION, rep.blocked_codes)

    def test_20_pillar28a_blocks_invalid_auto_power_off_temp_tokens(self) -> None:
        for bad_apo in ("Low", "Off", "UltraHigh", ""):
            rep = evaluate_fan_pwm_prebackup_thermal_interlock(
                FanPwmThermalInterlockSpec(auto_power_off_temp=bad_apo)
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.auto_power_off_temp_valid)
            self.assertIn(P198_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP, rep.blocked_codes)

    def test_21_pillar28a_blocks_soc_overheat_before_backup_or_stage_b(self) -> None:
        rep = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(
                stage_operation=P198_OP_COLD_BACKUP_P3_75MIB,
                stock_fan_control_mode=P198_FAN_MODE_AUTO,
                soc_temp_c=85.0,
            )
        )
        self.assertFalse(rep.passed)
        self.assertTrue(rep.pre_backup_aborted)
        self.assertIn(P198_BLOCKED_SOC_OVERHEAT_PREBACKUP_ABORT, rep.blocked_codes)

    def test_22_pillar28a_blocks_unknown_operation_and_persistent_write_unlock(self) -> None:
        r_op = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(stage_operation="FLASH_RAW_BOOT0")
        )
        r_wr = evaluate_fan_pwm_prebackup_thermal_interlock(
            FanPwmThermalInterlockSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(r_op.passed)
        self.assertIn(P198_BLOCKED_UNKNOWN_FAN_STAGE_OPERATION, r_op.blocked_codes)
        self.assertFalse(r_wr.passed)
        self.assertIn(P198_BLOCKED_SAFETY_POLICY_VIOLATION, r_wr.blocked_codes)
        self.assertEqual(r_wr.physical_device_writes, 0)

    def test_23_pillar28a_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar28a_fan_pwm_thermal_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P198_STATUS_VERIFIED_PILLAR_28A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P198_PILLAR_28A_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group B (24..36): Pillar 28B — 6.01 vs 7.02 LUT Split & Shutter
    # ------------------------------------------------------------------

    def test_24_pillar28b_happy_volatile_tmpfs_lut_overlay_preserves_16_of_16_slots(self) -> None:
        rep = evaluate_lut_split_and_shutter_angle_vault(LutSplitShutterVaultSpec())
        self.assertTrue(rep.passed)
        self.assertTrue(rep.vault_preserved)
        self.assertTrue(rep.lut_gen_split_detected)
        self.assertTrue(rep.legacy_601_pollution_blocked_or_isolated)
        self.assertTrue(rep.volatile_lut_overlay_ok)
        self.assertEqual(rep.stage_b_lut_write_target, P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR)
        self.assertEqual(rep.user1_16_h0_eq_h3_count, 16)
        self.assertTrue(rep.backup_bin_h0_eq_h3)

    def test_25_pillar28b_blocks_fx6_601_legacy_lut_write_to_p2_setting_paths(self) -> None:
        for bad_target in (
            "p2:/setting/lut_slots",
            "/setting/user_lut",
            "/mnt/p2/setting",
            "/dev/mmcblk0p2",
        ):
            rep = evaluate_lut_split_and_shutter_angle_vault(
                LutSplitShutterVaultSpec(stage_b_lut_write_target=bad_target)
            )
            self.assertFalse(rep.passed)
            self.assertIn(P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION, rep.blocked_codes)

    def test_26_pillar28b_blocks_legacy_601_serialized_slot_in_h3_user1_16(self) -> None:
        slots_h3 = p28_mod._default_fx3_702_user1_16_lut_slots()
        slots_h3["User8"] = {
            "serialization_gen": P198_LUT_GEN_LEGACY_601,
            "fw_origin": "6.01",
            "cube_name": "FX6_Legacy601.cube",
            "grid_size": 33,
            "slot_sha256": "e" * 64,
        }
        rep = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(user1_16_slots_h3=slots_h3)
        )
        self.assertFalse(rep.passed)
        self.assertIn(P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION, rep.blocked_codes)
        self.assertIn(P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT, rep.blocked_codes)
        self.assertEqual(rep.user1_16_h0_eq_h3_count, 15)

    def test_27_pillar28b_blocks_non_tmpfs_lut_overlay_escape(self) -> None:
        rep = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(
                stage_b_lut_write_target="/var/tmp/lut_cache",
                stage_b_overlay_is_tmpfs=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.volatile_lut_overlay_ok)
        self.assertIn(P198_BLOCKED_NON_TMPFS_LUT_OVERLAY_PATH, rep.blocked_codes)

    def test_28_pillar28b_normal_fps_allows_5_6_deg_through_64f_shutter_angle(self) -> None:
        for fps in P198_NORMAL_FPS_RATES_ALLOWING_64F:
            for angle in (P198_SHUTTER_MIN_ANGLE_DEG, 180.0, P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG):
                rep = evaluate_lut_split_and_shutter_angle_vault(
                    LutSplitShutterVaultSpec(rec_frame_rate=fps, sq_mode_active=False, shutter_angle_deg=angle)
                )
                self.assertTrue(rep.passed, f"Expected {fps} @ {angle} deg to pass")
                self.assertEqual(rep.max_allowed_angle_deg, P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG)

    def test_29_pillar28b_119_88p_100p_and_sq_narrow_shutter_angle_ceiling_to_360_deg(self) -> None:
        for fps in P198_HIGH_FPS_RATES_NARROWED_360:
            ok_rep = evaluate_lut_split_and_shutter_angle_vault(
                LutSplitShutterVaultSpec(rec_frame_rate=fps, shutter_angle_deg=360.0)
            )
            bad_rep = evaluate_lut_split_and_shutter_angle_vault(
                LutSplitShutterVaultSpec(rec_frame_rate=fps, shutter_angle_deg=720.0)
            )
            self.assertTrue(ok_rep.passed)
            self.assertEqual(ok_rep.max_allowed_angle_deg, P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG)
            self.assertFalse(bad_rep.passed)
            self.assertIn(P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE, bad_rep.blocked_codes)

        sq_ok = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(rec_frame_rate="23.98p", sq_mode_active=True, shutter_angle_deg=360.0)
        )
        sq_bad = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(rec_frame_rate="23.98p", sq_mode_active=True, shutter_angle_deg=360.5)
        )
        self.assertTrue(sq_ok.passed)
        self.assertFalse(sq_bad.passed)
        self.assertIn(P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE, sq_bad.blocked_codes)

    def test_30_pillar28b_blocks_shutter_angle_below_5_6_deg_or_invalid_mode_or_fps(self) -> None:
        r_low = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(shutter_angle_deg=5.5)
        )
        r_mode = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(shutter_mode="ECS_BOGUS")
        )
        r_fps = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(rec_frame_rate="999p")
        )
        for rep in (r_low, r_mode, r_fps):
            self.assertFalse(rep.passed)
            self.assertIn(P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE, rep.blocked_codes)

    def test_31_pillar28b_independent_speed_and_angle_slots_preserved_across_03ev_05ev(self) -> None:
        for step in ("0.3EV", "0.5EV"):
            for mode in ("Speed", "Angle"):
                rep = evaluate_lut_split_and_shutter_angle_vault(
                    LutSplitShutterVaultSpec(
                        shutter_mode=mode,
                        exposure_step=step,
                        speed_slot_h0_value="1/50",
                        speed_slot_h3_value="1/50",
                        angle_slot_h0_deg=172.8,
                        angle_slot_h3_deg=172.8,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.shutter_independent_slots_ok)
                self.assertTrue(rep.exposure_step_decoupled_ok)

    def test_32_pillar28b_blocks_coupled_speed_angle_slot_key_or_value_clobber(self) -> None:
        r_shared = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(speed_slot_key="SAME_KEY", angle_slot_key="SAME_KEY")
        )
        r_speed_drift = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(speed_slot_h0_value="1/48", speed_slot_h3_value="1/96")
        )
        r_angle_drift = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(angle_slot_h0_deg=180.0, angle_slot_h3_deg=90.0)
        )
        for rep in (r_shared, r_speed_drift, r_angle_drift):
            self.assertFalse(rep.passed)
            self.assertIn(P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER, rep.blocked_codes)

    def test_33_pillar28b_blocks_exposure_step_mutation_or_invalid_step(self) -> None:
        r_mut = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(exposure_step_mutated_angle_slot=True)
        )
        r_bad_step = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(exposure_step="1.0EV")
        )
        for rep in (r_mut, r_bad_step):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.exposure_step_decoupled_ok)
            self.assertIn(P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER, rep.blocked_codes)

    def test_34_pillar28b_blocks_user1_16_or_backup_bin_h0_h3_drift_or_unlocked_p2(self) -> None:
        r_p2 = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(p2_blkroset_locked=False)
        )
        r_bak = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(backup_bin_h3_sha256="f" * 64)
        )
        r_cold = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(cold_boot_returned_to_stock_702=False)
        )
        for rep in (r_p2, r_bak, r_cold):
            self.assertFalse(rep.passed)
            self.assertIn(P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT, rep.blocked_codes)

    def test_35_pillar28b_blocks_persistent_write_unlock_request(self) -> None:
        rep = evaluate_lut_split_and_shutter_angle_vault(
            LutSplitShutterVaultSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertIn(P198_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_36_pillar28b_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar28b_lut_split_shutter_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P198_STATUS_VERIFIED_PILLAR_28B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P198_PILLAR_28B_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group C (37..46): Standalone Pillar 28 & Unified 28/28 Master
    # ------------------------------------------------------------------

    def test_37_pillar28_standalone_clean_room_passes(self) -> None:
        rep = run_pillar28_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P198_STATUS_VERIFIED_PILLAR28_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_28a_fan_pwm_interlock.scenarios_passed, 6)
        self.assertEqual(rep.pillar_28b_lut_split_shutter_vault.scenarios_passed, 6)

    def test_38_pillar28_standalone_default_mode_passes(self) -> None:
        rep = run_pillar28_standalone_suite()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P198_STATUS_VERIFIED_PILLAR28_SUITE)
        self.assertIn(rep.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_39_master_28pillar_clean_room_28_of_28_within_6s_ceiling(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P198_STATUS_VERIFIED_28OF28_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 28)
        self.assertEqual(rep.pillars_passed, 28)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(self._cached_clean_dt, P198_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)

    def test_40_master_28pillar_default_mode_28_of_28_within_6s_ceiling(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P198_STATUS_VERIFIED_28OF28_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 28)
        self.assertEqual(rep.pillars_passed, 28)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(self._cached_default_dt, P198_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)

    def test_41_master_28pillar_zero_hardware_mutation_counters(self) -> None:
        rep = self._clean_master()
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.live_usb_iokit_transmit_enabled)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.otp_fuse_writes, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_42_master_28pillar_clean_room_digest_determinism(self) -> None:
        r1 = self._clean_master()
        r2 = evaluate_28pillar_recovery_master(force_clean_room=True)
        self.assertEqual(r1.master_28pillar_sha256, r2.master_28pillar_sha256)
        self.assertEqual(tuple(p.digest_sha256 for p in r1.pillars), tuple(p.digest_sha256 for p in r2.pillars))

    def test_43_master_28pillar_fault_injection_pillar28_fails_closed_27_of_28(self) -> None:
        rep = evaluate_28pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="realhw_28pillar_fan_pwm_shutter_lut_split_verifier",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P198_STATUS_FAIL_28OF28_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 27)
        self.assertEqual(rep.failed_pillars, ("realhw_28pillar_fan_pwm_shutter_lut_split_verifier",))

    def test_44_master_28pillar_fault_injection_upstream_pillar_fails_closed(self) -> None:
        rep = evaluate_28pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="realhw_27pillar_dcc1_pd_lut_vault_verifier",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 27)
        self.assertEqual(rep.failed_pillars, ("realhw_27pillar_dcc1_pd_lut_vault_verifier",))

    def test_45_master_28pillar_rejects_unknown_fault_injection_pillar_id(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_28pillar_recovery_master(force_clean_room=True, fault_inject_pillar="non_existent_pillar")

    def test_46_backward_compatibility_22_24_26_27_pillar_evaluators_intact(self) -> None:
        r22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        r24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        r26 = evaluate_26pillar_recovery_master(force_clean_room=True)
        r27 = evaluate_27pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r22.all_passed)
        self.assertEqual(r22.pillars_passed, 22)
        self.assertTrue(r24.all_passed)
        self.assertEqual(r24.pillars_passed, 24)
        self.assertTrue(r26.all_passed)
        self.assertEqual(r26.pillars_passed, 26)
        self.assertTrue(r27.all_passed)
        self.assertEqual(r27.pillars_passed, 27)

    # ------------------------------------------------------------------
    # Group D (47..52): CLI Subcommands & Backward-Compat CLI Regressions
    # ------------------------------------------------------------------

    @staticmethod
    def _run_cli(argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
            rc = fx3_cli.main()
        return rc, buf.getvalue()

    def test_47_cli_verify_fan_pwm_lut_split_vault_json_and_text(self) -> None:
        rc_json, out_json = self._run_cli(["verify-fan-pwm-lut-split-vault", "--force-clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        payload = json.loads(out_json)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P198_STATUS_VERIFIED_PILLAR28_SUITE)
        _assert_json_has_no_raw_bytes(payload)

        rc_txt, out_txt = self._run_cli(["verify-fan-pwm-lut-split-vault", "--clean-room"])
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillar_28a=6/6", out_txt)
        self.assertIn("pillar_28b=6/6", out_txt)

    def test_48_cli_verify_28pillar_recovery_json_clean_room_and_default(self) -> None:
        for extra in (["--force-clean-room"], []):
            rc, out = self._run_cli(["verify-28pillar-recovery", *extra, "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillar_count"], 28)
            self.assertEqual(payload["pillars_passed"], 28)
            self.assertEqual(payload["status"], P198_STATUS_VERIFIED_28OF28_AGGREGATOR)
            _assert_json_has_no_raw_bytes(payload)

    def test_49_cli_verify_28pillar_recovery_text_and_out_artifact(self) -> None:
        tmp_out = HERE / f"_tmp_p198_cli_{os.getpid()}"
        if tmp_out.exists():
            shutil.rmtree(tmp_out)
        try:
            rc, out = self._run_cli(["verify-28pillar-recovery", "--force-clean-room", "--out", str(tmp_out)])
            self.assertEqual(rc, 0)
            self.assertIn("pillars=28/28", out)
            report_file = tmp_out / "28pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillars_passed"], 28)
        finally:
            if tmp_out.exists():
                shutil.rmtree(tmp_out)

    def test_50_cli_verify_28pillar_recovery_returns_exit_code_2_on_failure(self) -> None:
        failed_rep = dataclasses.replace(
            self._clean_master(),
            all_passed=False,
            status=P198_STATUS_FAIL_28OF28_AGGREGATOR,
            pillars_passed=27,
            failed_pillars=("realhw_28pillar_fan_pwm_shutter_lut_split_verifier",),
        )
        with mock.patch.object(fx3_cli, "verify_28pillar_recovery_suite", return_value=failed_rep):
            rc, _ = self._run_cli(["verify-28pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc, 2)

    def test_51_cli_backward_compatibility_22_24_26_27_pillar_subcommands(self) -> None:
        for cmd, flag, expected in (
            ("verify-22pillar-recovery", "--clean-room", 22),
            ("verify-24pillar-recovery", "--force-clean-room", 24),
            ("verify-26pillar-recovery", "--force-clean-room", 26),
            ("verify-27pillar-recovery", "--force-clean-room", 27),
        ):
            rc, out = self._run_cli([cmd, flag, "--json"])
            self.assertEqual(rc, 0, f"CLI {cmd} failed")
            payload = json.loads(out)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], expected)

    def test_52_schema_and_version_metadata_pinned(self) -> None:
        rep = self._clean_master()
        self.assertEqual(rep.schema, PHASE198_SCHEMA)
        self.assertEqual(rep.version, PHASE198_VERSION)
        self.assertEqual(len(rep.pillars), 28)


if __name__ == "__main__":
    unittest.main()
