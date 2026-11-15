"""Phase 195 (Pillar 27 / 27/27 Recovery Master) Dual-Mode Fast Unit Tests (50 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection, bounded reads, FX3_FX6_FORCE_CLEAN_ROOM=1
  fallback, determinism, zero raw firmware bytes in JSON & Master 27-pillar registry
- Group A (11..22): Pillar 27A — NP-FZ100 (>=51% / >=3 bars) & DC-C1 (>=65W + 5A e-marked cable)
  cold-backup (0x40) & UFU power-brownout interlock, Micro-USB rejection, blinking LED fault block,
  mid-Stage-B DC-C1 power-drop zero eMMC damage (16/16 Tier-0 H0 == H3), dirty overlay/drift fail-closed
- Group B (23..34): Pillar 27B — Dual-media .cube User LUT (User1..User16) ephemeral overlay vs
  Stock p2:/setting vault preservation (SDXC vs CFexpress-A path asymmetry, 17pt/33pt & <=63B ASCII,
  /tmp/fx6_lut_overlay tmpfs containment, User1..User16 + AE Level Offset 0..+2 EV 1/3 steps, H0 == H3)
- Group C (35..44): Pillar 27 standalone, Unified 27/27 Recovery Master Aggregator in both
  LOCAL_DONOR_O_RDONLY & CLEAN_ROOM_SYNTHETIC modes (<6.0s concurrency-safe ceiling), safety
  counters == 0, fault_inject_pillar fail-closed & 22/22 + 24/24 + 26/26 backward compatibility
- Group D (45..50): CLI `verify-dcc1-pd-lut-vault` & `verify-27pillar-recovery`
  (--json, --force-clean-room, --out, exit code 2 on failure) + 22/24/26-pillar CLI compat
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
from fx3_recovery import realhw_27pillar_dcc1_pd_lut_vault_verifier as p27_mod
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import evaluate_22pillar_recovery_master
from fx3_recovery.realhw_24pillar_master_recovery_verifier import evaluate_24pillar_recovery_master
from fx3_recovery.realhw_26pillar_master_recovery_verifier import (
    MASTER_26_PILLAR_IDS,
    evaluate_26pillar_recovery_master,
)
from fx3_recovery.realhw_27pillar_dcc1_pd_lut_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_27_PILLAR_COUNT,
    MASTER_27_PILLAR_IDS,
    MASTER_27_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE,
    P195_BLOCKED_INVALID_CUBE_LUT_SPEC,
    P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY,
    P195_BLOCKED_MICRO_USB_POWER_FORBIDDEN,
    P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT,
    P195_BLOCKED_P2_SETTING_H0_H3_DRIFT,
    P195_BLOCKED_P2_SETTING_VAULT_WRITE_OR_NON_TMPFS_OVERLAY,
    P195_BLOCKED_SAFETY_POLICY_VIOLATION,
    P195_BLOCKED_STAGE_B_OVERLAY_NOT_WIPED_ON_DROP,
    P195_BLOCKED_TIER0_16OF16_H0_H3_DRIFT,
    P195_BLOCKED_UNKNOWN_POWER_OR_STAGE_MODE,
    P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID,
    P195_CFEXPRESS_A_USER_LUT_DIR,
    P195_CONCURRENT_CEILING_SECONDS,
    P195_CUBE_MAX_FILENAME_BYTES,
    P195_DC_C1_MIN_EMARKED_AMPS,
    P195_DC_C1_MIN_PD_WATTS,
    P195_DONOR_FX3_APPFW_SO_RELPATH,
    P195_DONOR_FX3_BACKUP_BIN_RELPATH,
    P195_DONOR_FX3_BODYDATA_RELPATH,
    P195_DONOR_FX3_CPAPP_B_RELPATH,
    P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH,
    P195_DONOR_FX3_PARTINF_RELPATH,
    P195_MEDIA_CFEXPRESS_A,
    P195_MEDIA_SDXC,
    P195_NP_FZ100_MIN_BATTERY_BARS,
    P195_NP_FZ100_MIN_BATTERY_PCT,
    P195_PILLAR_27A_SCENARIO_IDS,
    P195_PILLAR_27B_SCENARIO_IDS,
    P195_PINNED_FX3_APPFW_SO_BYTES,
    P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
    P195_PINNED_FX3_BACKUP_BIN_SHA256,
    P195_PINNED_FX3_BODYDATA_BYTES,
    P195_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P195_PINNED_FX3_CPAPP_B_BYTES,
    P195_PINNED_FX3_LIBUSBBUSPOWER_BYTES,
    P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256,
    P195_POWER_SOURCE_DC_C1_COUPLER,
    P195_POWER_SOURCE_MICRO_USB,
    P195_POWER_SOURCE_USB_PD_BODY,
    P195_SDXC_USER_LUT_DIR,
    P195_STAGE_B_EPHEMERAL_LUT_OVERLAY_DIR,
    P195_STAGE_OPERATION_COLD_BACKUP_0X40,
    P195_STAGE_OPERATION_STAGE_B_BOOT,
    P195_STAGE_OPERATION_UFU_BODYDATA,
    P195_STATUS_FAIL_27OF27_AGGREGATOR,
    P195_STATUS_VERIFIED_27OF27_AGGREGATOR,
    P195_STATUS_VERIFIED_PILLAR27_SUITE,
    P195_STATUS_VERIFIED_PILLAR_27A,
    P195_STATUS_VERIFIED_PILLAR_27B,
    P195_TIER0_16_SURFACES,
    P195_USER_LUT_SLOT_NAMES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE195_SCHEMA,
    PHASE195_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Dcc1PowerBrownoutInterlockSpec,
    DualMediaCubeLutVaultSpec,
    Master27PillarRecoveryReport,
    evaluate_27pillar_recovery_master,
    evaluate_dcc1_power_brownout_interlock,
    evaluate_dual_media_cube_lut_vault,
    inspect_phase195_donors_readonly,
    run_pillar27_standalone_suite,
    run_pillar27a_power_interlock_6_scenario_suite,
    run_pillar27b_lut_vault_6_scenario_suite,
    verify_27pillar_recovery_suite,
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


class TestRealHw27PillarDcc1PdLutVaultVerifier(unittest.TestCase):
    _cached_clean_master: Master27PillarRecoveryReport | None = None
    _cached_default_master: Master27PillarRecoveryReport | None = None
    _cached_default_dt: float = 0.0
    _cached_clean_dt: float = 0.0

    @classmethod
    def _clean_master(cls) -> Master27PillarRecoveryReport:
        if cls._cached_clean_master is None:
            t0 = time.monotonic()
            cls._cached_clean_master = verify_27pillar_recovery_suite(force_clean_room=True)
            cls._cached_clean_dt = time.monotonic() - t0
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master27PillarRecoveryReport:
        if cls._cached_default_master is None:
            t0 = time.monotonic()
            cls._cached_default_master = verify_27pillar_recovery_suite()
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
        self.assertIn("realhw_27pillar_dcc1_pd_lut_vault_verifier", fx3_recovery.__all__)
        self.assertIn("evaluate_27pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_27pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_dcc1_power_brownout_interlock", fx3_recovery.__all__)
        self.assertIn("evaluate_dual_media_cube_lut_vault", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.evaluate_27pillar_recovery_master, evaluate_27pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_27pillar_recovery_suite, verify_27pillar_recovery_suite)
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_26pillar_recovery_master, evaluate_26pillar_recovery_master)
        hints = typing.get_type_hints(p27_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase195_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_702_bytes, P195_PINNED_FX3_BODYDATA_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertEqual(snap.cpapp_b_bytes, P195_PINNED_FX3_CPAPP_B_BYTES)
        self.assertTrue(snap.appfw_so_elf64_aarch64_ok)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertTrue(snap.partinf_30_partitions_ok)
        self.assertTrue(snap.libusbbuspower_elf64_aarch64_ok)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p27_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase195_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase195_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P195_DONOR_FX3_BODYDATA_RELPATH,
                P195_DONOR_FX3_CPAPP_B_RELPATH,
                P195_DONOR_FX3_APPFW_SO_RELPATH,
                P195_DONOR_FX3_BACKUP_BIN_RELPATH,
                P195_DONOR_FX3_PARTINF_RELPATH,
                P195_DONOR_FX3_LIBUSBBUSPOWER_RELPATH,
            )
        )
        if not donors_present or p27_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 / libUsbBusPower local donors unavailable or clean-room forced")

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

        with mock.patch.object(p27_mod.os, "open", side_effect=spy_open), mock.patch.object(
            p27_mod.os, "pread", side_effect=spy_pread
        ):
            snap = inspect_phase195_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertGreaterEqual(len(flags_seen), 6)
        for fl in flags_seen:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
            self.assertTrue(fl & os.O_NOFOLLOW)
            self.assertTrue(fl & os.O_NONBLOCK)
        # Bounded 4 KiB reads on BODYDATA.DAT (811 MB), cpapp-b.bin (16 MB), appFw.so (79 MB)
        self.assertEqual(pread_sizes, [4096, 4096, 4096])
        self.assertEqual(snap.artifacts[0].sha256_digest, P195_PINNED_FX3_BODYDATA_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[2].sha256_digest, P195_PINNED_FX3_APPFW_SO_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[3].sha256_digest, P195_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(snap.artifacts[5].sha256_digest, P195_PINNED_FX3_LIBUSBBUSPOWER_SHA256)

    def test_07_clean_room_snapshot_determinism(self) -> None:
        s1 = inspect_phase195_donors_readonly(force_clean_room=True)
        s2 = inspect_phase195_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        self.assertEqual(s1.artifacts, s2.artifacts)

    def test_08_zero_raw_firmware_bytes_in_json_reports(self) -> None:
        standalone = run_pillar27_standalone_suite(force_clean_room=True).to_dict()
        master = self._clean_master().to_dict()
        j1 = _assert_json_has_no_raw_bytes(standalone)
        j2 = _assert_json_has_no_raw_bytes(master)
        self.assertIn(PHASE195_SCHEMA, j1)
        self.assertIn(P195_STATUS_VERIFIED_27OF27_AGGREGATOR, j2)

    def test_09_master_27_pillar_registry_matches_1_through_27(self) -> None:
        self.assertEqual(MASTER_27_PILLAR_COUNT, 27)
        self.assertEqual(len(MASTER_27_PILLAR_SPECS), 27)
        self.assertEqual(tuple(s[0] for s in MASTER_27_PILLAR_SPECS), tuple(range(1, 28)))
        self.assertEqual(MASTER_27_PILLAR_IDS[:26], MASTER_26_PILLAR_IDS)
        self.assertEqual(MASTER_27_PILLAR_IDS[26], "realhw_27pillar_dcc1_pd_lut_vault_verifier")

    def test_10_pinned_wave24_hardware_and_lut_constants(self) -> None:
        self.assertEqual(P195_PINNED_FX3_APPFW_SO_BYTES, 79_015_712)
        self.assertEqual(P195_PINNED_FX3_LIBUSBBUSPOWER_BYTES, 48_232)
        self.assertEqual(P195_NP_FZ100_MIN_BATTERY_PCT, 51)
        self.assertEqual(P195_NP_FZ100_MIN_BATTERY_BARS, 3)
        self.assertEqual(P195_DC_C1_MIN_PD_WATTS, 65.0)
        self.assertEqual(P195_DC_C1_MIN_EMARKED_AMPS, 5.0)
        self.assertEqual(len(P195_TIER0_16_SURFACES), 16)
        self.assertEqual(P195_SDXC_USER_LUT_DIR, "/Private/Sony/PRO/LUT/")
        self.assertEqual(P195_CFEXPRESS_A_USER_LUT_DIR, "/Sony/PRO/LUT/")
        self.assertEqual(P195_STAGE_B_EPHEMERAL_LUT_OVERLAY_DIR, "/tmp/fx6_lut_overlay")
        self.assertEqual(P195_CUBE_MAX_FILENAME_BYTES, 63)
        self.assertEqual(len(P195_USER_LUT_SLOT_NAMES), 16)
        self.assertEqual(P195_USER_LUT_SLOT_NAMES[0], "User1")
        self.assertEqual(P195_USER_LUT_SLOT_NAMES[-1], "User16")

    # ------------------------------------------------------------------
    # Group A (11..22): Pillar 27A — NP-FZ100 & DC-C1 Brownout Interlock
    # ------------------------------------------------------------------

    def test_11_pillar27a_happy_usb_pd_with_npfz100_51pct_3bars(self) -> None:
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                stage_operation=P195_STAGE_OPERATION_COLD_BACKUP_0X40,
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                np_fz100_inserted=True,
                battery_pct=51,
                battery_bars=3,
                battery_voltage_v=7.20,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.stage_entry_admitted)
        self.assertFalse(rep.pre_stage_aborted)
        self.assertTrue(rep.np_fz100_precondition_ok)
        self.assertEqual(rep.tier0_h0_eq_h3_count, 16)
        self.assertEqual(rep.blocked_codes, ())

    def test_12_pillar27a_happy_dcc1_65w_5a_cold_backup_and_ufu(self) -> None:
        for op in (P195_STAGE_OPERATION_COLD_BACKUP_0X40, P195_STAGE_OPERATION_UFU_BODYDATA):
            rep = evaluate_dcc1_power_brownout_interlock(
                Dcc1PowerBrownoutInterlockSpec(
                    stage_operation=op,
                    power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                    usb_pd_watts=65.0,
                    emarked_5a_cable=True,
                    cable_max_amps=5.0,
                )
            )
            self.assertTrue(rep.passed)
            self.assertTrue(rep.stage_entry_admitted)
            self.assertTrue(rep.dc_c1_65w_5a_interlock_ok)
            self.assertEqual(rep.tier0_h0_eq_h3_count, 16)

    def test_13_pillar27a_blocks_usb_pd_without_physical_npfz100(self) -> None:
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                stage_operation=P195_STAGE_OPERATION_UFU_BODYDATA,
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                np_fz100_inserted=False,
                battery_pct=100,
                battery_bars=4,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.stage_entry_admitted)
        self.assertTrue(rep.pre_stage_aborted)
        self.assertFalse(rep.np_fz100_precondition_ok)
        self.assertIn(P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT, rep.blocked_codes)

    def test_14_pillar27a_blocks_npfz100_below_51pct_3bars_or_low_voltage(self) -> None:
        r_pct = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                battery_pct=50,
                battery_bars=3,
            )
        )
        r_bars = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                battery_pct=55,
                battery_bars=2,
            )
        )
        r_volt = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                battery_pct=60,
                battery_bars=3,
                battery_voltage_v=6.95,
            )
        )
        for rep in (r_pct, r_bars, r_volt):
            self.assertFalse(rep.passed)
            self.assertTrue(rep.pre_stage_aborted)
            self.assertIn(P195_BLOCKED_MISSING_NPFZ100_OR_LOW_BATT, rep.blocked_codes)

    def test_15_pillar27a_blocks_micro_usb_power_attempt(self) -> None:
        r1 = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(power_source=P195_POWER_SOURCE_MICRO_USB)
        )
        r2 = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_USB_PD_BODY,
                micro_usb_power_attempted=True,
            )
        )
        for rep in (r1, r2):
            self.assertFalse(rep.passed)
            self.assertTrue(rep.pre_stage_aborted)
            self.assertFalse(rep.micro_usb_rejected_ok)
            self.assertIn(P195_BLOCKED_MICRO_USB_POWER_FORBIDDEN, rep.blocked_codes)

    def test_16_pillar27a_blocks_dcc1_below_65w_or_non_5a_cable_or_fault_led(self) -> None:
        r_watts = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                usb_pd_watts=45.0,
                emarked_5a_cable=True,
                cable_max_amps=5.0,
            )
        )
        r_cable = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                usb_pd_watts=100.0,
                emarked_5a_cable=False,
                cable_max_amps=3.0,
            )
        )
        r_led = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                usb_pd_watts=65.0,
                emarked_5a_cable=True,
                cable_max_amps=5.0,
                dc_c1_blinking_led_fault=True,
            )
        )
        for rep in (r_watts, r_cable, r_led):
            self.assertFalse(rep.passed)
            self.assertTrue(rep.pre_stage_aborted)
            self.assertFalse(rep.dc_c1_65w_5a_interlock_ok)
            self.assertIn(P195_BLOCKED_DCC1_INSUFFICIENT_PD_OR_NON_5A_CABLE, rep.blocked_codes)

    def test_17_pillar27a_dcc1_mid_stage_b_power_drop_proves_zero_emmc_damage(self) -> None:
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                stage_operation=P195_STAGE_OPERATION_STAGE_B_BOOT,
                power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                power_drop_mid_stage_b=True,
                stage_b_volatile_overlay_wiped=True,
                cold_reboot_to_stock_702_clean=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.power_drop_mid_stage_b)
        self.assertTrue(rep.zero_emmc_damage_proven)
        self.assertEqual(rep.tier0_h0_eq_h3_count, 16)
        self.assertEqual(rep.tier0_surface_count, 16)
        self.assertEqual(rep.emmc_damage_count, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_18_pillar27a_blocks_stage_b_overlay_residue_on_power_drop(self) -> None:
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(
                stage_operation=P195_STAGE_OPERATION_STAGE_B_BOOT,
                power_source=P195_POWER_SOURCE_DC_C1_COUPLER,
                power_drop_mid_stage_b=True,
                stage_b_volatile_overlay_wiped=False,
                cold_reboot_to_stock_702_clean=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.zero_emmc_damage_proven)
        self.assertIn(P195_BLOCKED_STAGE_B_OVERLAY_NOT_WIPED_ON_DROP, rep.blocked_codes)

    def test_19_pillar27a_blocks_tier0_16_surface_h0_h3_drift(self) -> None:
        drifted = p27_mod._default_tier0_16_surface_digests()
        drifted["spi_nor_mtd0ro"] = "0" * 64
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(tier0_h3_digests=drifted)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.zero_emmc_damage_proven)
        self.assertEqual(rep.tier0_h0_eq_h3_count, 15)
        self.assertEqual(rep.emmc_damage_count, 1)
        self.assertIn(P195_BLOCKED_TIER0_16OF16_H0_H3_DRIFT, rep.blocked_codes)

    def test_20_pillar27a_blocks_unknown_stage_or_power_topology(self) -> None:
        r_op = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(stage_operation="RAW_NAND_WRITE")
        )
        r_src = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(power_source="D_TAP_UNREGULATED")
        )
        for rep in (r_op, r_src):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.stage_entry_admitted)
            self.assertIn(P195_BLOCKED_UNKNOWN_POWER_OR_STAGE_MODE, rep.blocked_codes)

    def test_21_pillar27a_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_dcc1_power_brownout_interlock(
            Dcc1PowerBrownoutInterlockSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(P195_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_22_pillar27a_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar27a_power_interlock_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P195_STATUS_VERIFIED_PILLAR_27A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P195_PILLAR_27A_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    # ------------------------------------------------------------------
    # Group B (23..34): Pillar 27B — Dual-Media .cube LUT & p2:/setting
    # ------------------------------------------------------------------

    def test_23_pillar27b_happy_sdxc_17pt_and_cfexpress_33pt_in_tmpfs_overlay(self) -> None:
        r_sd = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(
                media_type=P195_MEDIA_SDXC,
                media_lut_directory=P195_SDXC_USER_LUT_DIR,
                cube_filename="FX3_User01_S709_17pt.cube",
                cube_grid_size=17,
                cube_header_text="LUT_3D_SIZE 17\n",
                ae_level_offset_ev=0.0,
            )
        )
        r_cfa = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(
                media_type=P195_MEDIA_CFEXPRESS_A,
                media_lut_directory=P195_CFEXPRESS_A_USER_LUT_DIR,
                cube_filename="FX3_User16_Rec709_33pt.cube",
                cube_grid_size=33,
                cube_header_text="LUT_3D_SIZE 33\n",
                user_slot_name="User16",
                ae_level_offset_ev=2.0,
            )
        )
        for rep in (r_sd, r_cfa):
            self.assertTrue(rep.passed)
            self.assertTrue(rep.vault_preserved)
            self.assertTrue(rep.media_path_asymmetry_ok)
            self.assertTrue(rep.cube_spec_ok)
            self.assertTrue(rep.ephemeral_tmp_overlay_ok)
            self.assertTrue(rep.user_slot_and_ae_offset_ok)
            self.assertTrue(rep.p2_setting_h0_eq_h3)
            self.assertTrue(rep.user1_16_slots_bit_identical)
            self.assertEqual(rep.blocked_codes, ())

    def test_24_pillar27b_blocks_swapped_sdxc_vs_cfexpress_lut_directories(self) -> None:
        r_sd_wrong = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(
                media_type=P195_MEDIA_SDXC,
                media_lut_directory=P195_CFEXPRESS_A_USER_LUT_DIR,
            )
        )
        r_cfa_wrong = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(
                media_type=P195_MEDIA_CFEXPRESS_A,
                media_lut_directory=P195_SDXC_USER_LUT_DIR,
            )
        )
        for rep in (r_sd_wrong, r_cfa_wrong):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.media_path_asymmetry_ok)
            self.assertIn(P195_BLOCKED_MEDIA_LUT_PATH_ASYMMETRY, rep.blocked_codes)

    def test_25_pillar27b_enforces_exact_63_byte_cube_filename_boundary(self) -> None:
        exact_63b = ("L" * 58) + ".cube"  # 58 + 5 = 63 bytes
        over_64b = ("L" * 59) + ".cube"   # 59 + 5 = 64 bytes
        r_ok = evaluate_dual_media_cube_lut_vault(DualMediaCubeLutVaultSpec(cube_filename=exact_63b))
        r_bad = evaluate_dual_media_cube_lut_vault(DualMediaCubeLutVaultSpec(cube_filename=over_64b))
        self.assertTrue(r_ok.passed)
        self.assertEqual(r_ok.cube_filename_bytes, 63)
        self.assertFalse(r_bad.passed)
        self.assertFalse(r_bad.cube_spec_ok)
        self.assertEqual(r_bad.cube_filename_bytes, 64)
        self.assertIn(P195_BLOCKED_INVALID_CUBE_LUT_SPEC, r_bad.blocked_codes)

    def test_26_pillar27b_blocks_non_ascii_filename_65pt_or_1d_lut(self) -> None:
        r_non_ascii = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(cube_filename="FX3_测试.cube")
        )
        r_65pt = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(cube_grid_size=65, cube_header_text="LUT_3D_SIZE 65\n")
        )
        r_1d = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(
                cube_grid_size=33,
                cube_header_text="LUT_1D_SIZE 33\nLUT_3D_SIZE 33\n",
            )
        )
        for rep in (r_non_ascii, r_65pt, r_1d):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.cube_spec_ok)
            self.assertIn(P195_BLOCKED_INVALID_CUBE_LUT_SPEC, rep.blocked_codes)

    def test_27_pillar27b_accepts_all_valid_one_third_ev_offsets_0_to_2ev(self) -> None:
        for thirds in range(0, 7):
            ev = round(thirds / 3.0, 2)
            rep = evaluate_dual_media_cube_lut_vault(
                DualMediaCubeLutVaultSpec(ae_level_offset_ev=ev)
            )
            self.assertTrue(rep.passed, f"Expected valid 1/3 EV step {ev} to pass")
            self.assertTrue(rep.user_slot_and_ae_offset_ok)

    def test_28_pillar27b_blocks_user17_overflow_and_invalid_ae_offset(self) -> None:
        r_slot_name = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(user_slot_name="User17")
        )
        r_slot_cnt = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(registered_user_slot_count=17)
        )
        r_ae_neg = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(ae_level_offset_ev=-0.33)
        )
        r_ae_high = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(ae_level_offset_ev=2.33)
        )
        r_ae_half = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(ae_level_offset_ev=0.50)
        )
        for rep in (r_slot_name, r_slot_cnt, r_ae_neg, r_ae_high, r_ae_half):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.user_slot_and_ae_offset_ok)
            self.assertIn(P195_BLOCKED_USER_LUT_SLOT_OR_AE_OFFSET_INVALID, rep.blocked_codes)

    def test_29_pillar27b_blocks_non_tmpfs_overlay_and_p2_setting_writes(self) -> None:
        r_path = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(stage_b_overlay_mount_path="/p2/setting/lut")
        )
        r_tmpfs = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(stage_b_overlay_is_tmpfs=False)
        )
        r_writes = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(stage_b_p2_setting_writes=1)
        )
        for rep in (r_path, r_tmpfs, r_writes):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.ephemeral_tmp_overlay_ok)
            self.assertIn(P195_BLOCKED_P2_SETTING_VAULT_WRITE_OR_NON_TMPFS_OVERLAY, rep.blocked_codes)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_30_pillar27b_blocks_p2_setting_h0_h3_drift_or_blkroset_unlock(self) -> None:
        r_sha = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(p2_setting_h3_sha256="a" * 64)
        )
        r_ro = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(p2_blkroset_locked=False)
        )
        r_reboot = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(rebooted_to_stock_fx3_702=False)
        )
        for rep in (r_sha, r_ro, r_reboot):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.p2_setting_h0_eq_h3)
            self.assertIn(P195_BLOCKED_P2_SETTING_H0_H3_DRIFT, rep.blocked_codes)

    def test_31_pillar27b_blocks_user1_16_slot_mutation_on_reboot(self) -> None:
        drifted_slots = p27_mod._default_user_lut_slots_snapshot()
        drifted_slots["User8"]["ae_level_offset_ev"] = 1.67
        drifted_slots["User8"]["slot_sha256"] = "c" * 64
        rep = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(p2_user1_16_slots_h3=drifted_slots)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.user1_16_slots_bit_identical)
        self.assertFalse(rep.p2_setting_h0_eq_h3)
        self.assertIn(P195_BLOCKED_P2_SETTING_H0_H3_DRIFT, rep.blocked_codes)

    def test_32_pillar27b_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_dual_media_cube_lut_vault(
            DualMediaCubeLutVaultSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(P195_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_33_pillar27b_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar27b_lut_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P195_STATUS_VERIFIED_PILLAR_27B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P195_PILLAR_27B_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    def test_34_pillar27_reports_json_serializable_no_raw_bytes(self) -> None:
        d1 = evaluate_dcc1_power_brownout_interlock().to_dict()
        d2 = evaluate_dual_media_cube_lut_vault().to_dict()
        _assert_json_has_no_raw_bytes(d1)
        _assert_json_has_no_raw_bytes(d2)

    # ------------------------------------------------------------------
    # Group C (35..44): Pillar 27 Standalone & Unified 27/27 Master
    # ------------------------------------------------------------------

    def test_35_pillar27_standalone_clean_room_passes(self) -> None:
        rep = run_pillar27_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P195_STATUS_VERIFIED_PILLAR27_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_27a_dcc1_pd_interlock.scenarios_passed, 6)
        self.assertEqual(rep.pillar_27b_cube_lut_vault.scenarios_passed, 6)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_36_pillar27_standalone_default_mode_passes(self) -> None:
        rep = run_pillar27_standalone_suite()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P195_STATUS_VERIFIED_PILLAR27_SUITE)
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if p27_mod.is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertEqual(rep.pillar_27a_dcc1_pd_interlock.scenarios_passed, 6)
        self.assertEqual(rep.pillar_27b_cube_lut_vault.scenarios_passed, 6)

    def test_37_master_27pillar_clean_room_27of27_and_budget(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P195_STATUS_VERIFIED_27OF27_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 27)
        self.assertEqual(rep.pillars_passed, 27)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P195_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_clean_dt, P195_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)
        self.assertEqual(tuple(p.pillar_number for p in rep.pillars), tuple(range(1, 28)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_27_PILLAR_IDS)
        self.assertTrue(all(p.passed for p in rep.pillars))

    def test_38_master_27pillar_default_mode_27of27_and_budget(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P195_STATUS_VERIFIED_27OF27_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 27)
        self.assertEqual(rep.pillars_passed, 27)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P195_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_default_dt, P195_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if p27_mod.is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)

    def test_39_master_27pillar_safety_counters_all_zero_and_locked(self) -> None:
        for rep in (self._clean_master(), self._default_master()):
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.otp_fuse_writes, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.isp_write_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.allow_boot_partition_targeting)
            self.assertFalse(rep.allow_destructive_fastboot)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)

    def test_40_master_27pillar_deterministic_sha256_in_clean_room(self) -> None:
        r1 = self._clean_master()
        r2 = verify_27pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_27pillar_sha256, r2.master_27pillar_sha256)
        self.assertEqual(len(r1.master_27pillar_sha256), 64)

    def test_41_master_27pillar_fault_injection_fail_closed(self) -> None:
        for pid in (
            MASTER_27_PILLAR_IDS[0],
            MASTER_27_PILLAR_IDS[24],
            MASTER_27_PILLAR_IDS[25],
            MASTER_27_PILLAR_IDS[26],
        ):
            rep = evaluate_27pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, P195_STATUS_FAIL_27OF27_AGGREGATOR)
            self.assertEqual(rep.pillar_count, 27)
            self.assertEqual(rep.pillars_passed, 26)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_42_master_27pillar_unknown_fault_inject_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_27pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_28",
            )

    def test_43_master_27pillar_detects_safety_counter_violation_from_subsuite(self) -> None:
        bad_p27 = run_pillar27_standalone_suite(force_clean_room=True)
        tampered = dataclasses.replace(bad_p27, physical_device_writes=1)
        with mock.patch.object(p27_mod, "run_pillar27_standalone_suite", return_value=tampered):
            rep = evaluate_27pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P195_STATUS_FAIL_27OF27_AGGREGATOR)
        self.assertTrue(any("physical_device_writes" in e for e in rep.errors))

    def test_44_backward_compat_22_24_and_26_pillar_master_intact(self) -> None:
        m22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m22.all_passed)
        self.assertEqual(m22.pillar_count, 22)
        self.assertEqual(m22.pillars_passed, 22)

        m24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m24.all_passed)
        self.assertEqual(m24.pillar_count, 24)
        self.assertEqual(m24.pillars_passed, 24)

        m26 = evaluate_26pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m26.all_passed)
        self.assertEqual(m26.pillar_count, 26)
        self.assertEqual(m26.pillars_passed, 26)

    # ------------------------------------------------------------------
    # Group D (45..50): CLI Entrypoints & Backward Compatibility
    # ------------------------------------------------------------------

    def test_45_cli_verify_dcc1_pd_lut_vault_summary_and_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-dcc1-pd-lut-vault", "--force-clean-room"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn(f"status={P195_STATUS_VERIFIED_PILLAR27_SUITE}", buf.getvalue())
        self.assertIn("pillar_27a=6/6", buf.getvalue())
        self.assertIn("pillar_27b=6/6", buf.getvalue())

        buf_json = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-dcc1-pd-lut-vault", "--force-clean-room", "--json"]
        ):
            with redirect_stdout(buf_json):
                rc_j = fx3_cli.main()
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P195_STATUS_VERIFIED_PILLAR27_SUITE)
        _walk_check_no_bytes(payload)

    def test_46_cli_verify_27pillar_recovery_summary(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-27pillar-recovery", "--force-clean-room"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(f"status={P195_STATUS_VERIFIED_27OF27_AGGREGATOR}", out)
        self.assertIn("pillars=27/27", out)
        self.assertIn("pillar27_a=6/6", out)
        self.assertIn("pillar27_b=6/6", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_47_cli_verify_27pillar_recovery_json_and_out_dir(self) -> None:
        scratch_dir = ROOT / "work" / "_tests" / "phase195_cli_out"
        if scratch_dir.exists():
            shutil.rmtree(scratch_dir)
        scratch_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-27pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(scratch_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["schema"], PHASE195_SCHEMA)
            self.assertEqual(payload["version"], PHASE195_VERSION)
            self.assertEqual(payload["pillar_count"], 27)
            self.assertEqual(payload["pillars_passed"], 27)
            out_file = scratch_dir / "27pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            saved = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["master_27pillar_sha256"], payload["master_27pillar_sha256"])
        finally:
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir)

    def test_48_cli_verify_27pillar_recovery_fail_exit_code_2(self) -> None:
        failing = evaluate_27pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_27_PILLAR_IDS[26],
        )
        buf = io.StringIO()
        with mock.patch.object(fx3_cli, "verify_27pillar_recovery_suite", return_value=failing):
            with mock.patch.object(
                sys, "argv", ["fx3_recovery", "verify-27pillar-recovery", "--force-clean-room", "--json"]
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["all_passed"])
        self.assertEqual(payload["status"], P195_STATUS_FAIL_27OF27_AGGREGATOR)

    def test_49_cli_verify_dcc1_pd_lut_vault_fail_exit_code_2(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            fx3_cli,
            "run_pillar27_standalone_suite",
            side_effect=RuntimeError("simulated pillar27 safety gate halt"),
        ):
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-dcc1-pd-lut-vault", "--force-clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "REJECTED")
        self.assertEqual(payload["camera_operations"], 0)

    def test_50_cli_backward_compat_verify_22_24_and_26_pillar_recovery(self) -> None:
        for cmd, expected_count in (
            ("verify-22pillar-recovery", 22),
            ("verify-24pillar-recovery", 24),
            ("verify-26pillar-recovery", 26),
        ):
            buf = io.StringIO()
            with mock.patch.object(
                sys, "argv", ["fx3_recovery", cmd, "--clean-room", "--json"]
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillar_count"], expected_count)
            self.assertEqual(payload["pillars_passed"], expected_count)


if __name__ == "__main__":
    unittest.main()
