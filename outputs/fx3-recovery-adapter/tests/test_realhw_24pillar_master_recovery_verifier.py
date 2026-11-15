"""Phase 180 (Pillar 24 / 24/24 Recovery Master) Dual-Mode Fast Unit Tests (50 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection, bounded reads, FX3_FX6_FORCE_CLEAN_ROOM=1
  fallback, determinism & zero raw firmware bytes in JSON
- Group A (11..24): Pillar 24A — Official Sony ILME-FX3 Ver. 7.02 Slot-1 BODYDATA.DAT
  (811,876,768 B, \\x89UFU) post-uninstall stock-reflash readiness (>=2.04 floor / <=2.02 7L+7S
  block, Slot-2/duplicate block, p1/p15/p5 H0==H3, NP-FZ100 >=3 bars/>=7.2V, C2PA <=100 RO) & 6/6 suite
- Group B (25..36): Pillar 24B — Volatile network (WPA2/WPA3 only, rejecting WEP/WPA1/IPsec),
  zero tmpfs Wi-Fi cred / .cube 3D LUT / HDMI-BRAW leak into p2:/setting/Backup.bin & p30 H0==H3,
  write-unlock fail-closed & 6/6 suite
- Group C (37..44): Pillar 24 standalone, Unified 24/24 Recovery Master Aggregator in both
  LOCAL_DONOR_O_RDONLY & CLEAN_ROOM_SYNTHETIC modes (<6.0s concurrency-safe budget), safety
  counters == 0, fault_inject_pillar fail-closed & Milestone Phase 175 (22/22) backward compat
- Group D (45..50): CLI `verify-slot1-ufu-reflash-readiness` & `verify-24pillar-recovery`
  (--json, --force-clean-room, --out, exit code 2 on failure) + `verify-22pillar-recovery` compat
"""

from __future__ import annotations

from contextlib import redirect_stdout
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
from fx3_recovery import realhw_24pillar_master_recovery_verifier as p24_mod
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import (
    MASTER_22_PILLAR_IDS,
    evaluate_22pillar_recovery_master,
)
from fx3_recovery.realhw_24pillar_master_recovery_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S,
    BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH,
    BLOCKED_CUBE_LUT_STAGING_LEAK_OR_P30_DRIFT,
    BLOCKED_HDMI_BRAW_STATE_LEAK_TO_BACKUP_BIN,
    BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC,
    BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_FLOOR,
    BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED,
    BLOCKED_PERSISTENT_WRITE_OR_BACKUP_BIN_DRIFT,
    BLOCKED_SAFETY_POLICY_VIOLATION,
    BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA,
    BLOCKED_UFU_SIZE_MAGIC_OR_MODEL_MISMATCH,
    BLOCKED_VOLATILE_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_24_PILLAR_COUNT,
    MASTER_24_PILLAR_IDS,
    MASTER_24_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P180_BODYDATA_702_BYTES,
    P180_C2PA_MAX_LICENSES,
    P180_CONCURRENT_CEILING_SECONDS,
    P180_DONOR_FX3_BACKUP_BIN_RELPATH,
    P180_DONOR_FX3_BODYDATA_RELPATH,
    P180_DONOR_FX3_MOUNT_RELPATH,
    P180_DONOR_FX3_NFLASHA15_RELPATH,
    P180_DONOR_FX3_PARTINF_RELPATH,
    P180_DONOR_FX3_WBI2_RELPATH,
    P180_FX3_MIN_BODY_FLOOR_VERSION,
    P180_FX3_MODEL_ID,
    P180_NP_FZ100_MIN_BARS,
    P180_NP_FZ100_MIN_VOLTAGE_V,
    P180_PILLAR_24A_SCENARIO_IDS,
    P180_PILLAR_24B_SCENARIO_IDS,
    P180_PINNED_FX3_BACKUP_BIN_SHA256,
    P180_PINNED_FX3_BODYDATA_BYTES,
    P180_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P180_PINNED_FX3_NFLASHA15_BYTES,
    P180_PINNED_FX3_WBI2_SECTIONS,
    P180_PINNED_FX3_WBI2_TOTAL_BYTES,
    P180_STATUS_FAIL_24OF24_AGGREGATOR,
    P180_STATUS_VERIFIED_24OF24_AGGREGATOR,
    P180_STATUS_VERIFIED_PILLAR24_SUITE,
    P180_STATUS_VERIFIED_PILLAR_24A,
    P180_STATUS_VERIFIED_PILLAR_24B,
    P180_UFU_MAGIC_HEX,
    P180_WBI2_HEADER_PREFIX_HEX,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE180_SCHEMA,
    PHASE180_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Master24PillarRecoveryReport,
    RollbackHygieneAuditSpec,
    Slot1UfuReflashReadinessSpec,
    evaluate_24pillar_recovery_master,
    evaluate_slot1_ufu_stock_reflash_readiness,
    evaluate_volatile_network_braw_lut_hygiene,
    inspect_phase180_donors_readonly,
    run_pillar24_standalone_suite,
    run_pillar24a_slot1_ufu_readiness_6_scenario_suite,
    run_pillar24b_rollback_hygiene_6_scenario_suite,
    verify_24pillar_recovery_suite,
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


class TestRealHw24PillarMasterRecoveryVerifier(unittest.TestCase):
    _cached_clean_master: Master24PillarRecoveryReport | None = None
    _cached_default_master: Master24PillarRecoveryReport | None = None
    _cached_default_dt: float = 0.0
    _cached_clean_dt: float = 0.0

    @classmethod
    def _clean_master(cls) -> Master24PillarRecoveryReport:
        if cls._cached_clean_master is None:
            t0 = time.monotonic()
            cls._cached_clean_master = verify_24pillar_recovery_suite(force_clean_room=True)
            cls._cached_clean_dt = time.monotonic() - t0
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master24PillarRecoveryReport:
        if cls._cached_default_master is None:
            t0 = time.monotonic()
            cls._cached_default_master = verify_24pillar_recovery_suite()
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
        self.assertIn("realhw_24pillar_master_recovery_verifier", fx3_recovery.__all__)
        self.assertIn("evaluate_24pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_24pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_slot1_ufu_stock_reflash_readiness", fx3_recovery.__all__)
        self.assertIn("evaluate_volatile_network_braw_lut_hygiene", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_24pillar_recovery_suite, verify_24pillar_recovery_suite)
        # Milestone Phase 175 22-pillar exports stay completely intact
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        # Type hints resolve cleanly
        hints = typing.get_type_hints(p24_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase180_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_702_bytes, P180_BODYDATA_702_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertEqual(snap.wbi2_header_prefix_hex, P180_WBI2_HEADER_PREFIX_HEX)
        self.assertEqual(snap.wbi2_sections, P180_PINNED_FX3_WBI2_SECTIONS)
        self.assertTrue(snap.nflasha15_ext2_magic_ok)
        self.assertTrue(snap.partinf_30_partitions_ok)
        self.assertTrue(snap.mount_conf_p12_p15_p30_ok)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p24_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase180_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase180_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P180_DONOR_FX3_BODYDATA_RELPATH,
                P180_DONOR_FX3_WBI2_RELPATH,
                P180_DONOR_FX3_NFLASHA15_RELPATH,
                P180_DONOR_FX3_PARTINF_RELPATH,
                P180_DONOR_FX3_MOUNT_RELPATH,
                P180_DONOR_FX3_BACKUP_BIN_RELPATH,
            )
        )
        if not donors_present or p24_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 local donors unavailable or clean-room forced")

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

        with mock.patch.object(p24_mod.os, "open", side_effect=spy_open), mock.patch.object(
            p24_mod.os, "pread", side_effect=spy_pread
        ):
            snap = inspect_phase180_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertGreaterEqual(len(flags_seen), 6)
        for fl in flags_seen:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
            self.assertTrue(fl & os.O_NOFOLLOW)
            self.assertTrue(fl & os.O_NONBLOCK)
        # Bounded reads on huge BODYDATA.DAT (811 MB), nflasha15 (479 MB), nflasha5 (209 MB)
        self.assertTrue(all(sz <= 1024 * 1024 for sz in pread_sizes))
        self.assertIn(4096, pread_sizes)
        self.assertEqual(snap.artifacts[0].sha256_digest, P180_PINNED_FX3_BODYDATA_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[5].sha256_digest, P180_PINNED_FX3_BACKUP_BIN_SHA256)

    def test_07_clean_room_snapshot_determinism(self) -> None:
        s1 = inspect_phase180_donors_readonly(force_clean_room=True)
        s2 = inspect_phase180_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        self.assertEqual(s1.artifacts, s2.artifacts)

    def test_08_zero_raw_firmware_bytes_in_json_reports(self) -> None:
        standalone = run_pillar24_standalone_suite(force_clean_room=True).to_dict()
        master = self._clean_master().to_dict()
        j1 = _assert_json_has_no_raw_bytes(standalone)
        j2 = _assert_json_has_no_raw_bytes(master)
        self.assertIn(PHASE180_SCHEMA, j1)
        self.assertIn(P180_STATUS_VERIFIED_24OF24_AGGREGATOR, j2)

    def test_09_master_24_pillar_registry_matches_1_through_24(self) -> None:
        self.assertEqual(MASTER_24_PILLAR_COUNT, 24)
        self.assertEqual(len(MASTER_24_PILLAR_SPECS), 24)
        self.assertEqual(tuple(s[0] for s in MASTER_24_PILLAR_SPECS), tuple(range(1, 25)))
        self.assertEqual(MASTER_24_PILLAR_IDS[:22], MASTER_22_PILLAR_IDS)
        self.assertEqual(
            MASTER_24_PILLAR_IDS[22], "realhw_wbi_powerloss_and_100cycle_transition_verifier"
        )
        self.assertEqual(MASTER_24_PILLAR_IDS[23], "realhw_24pillar_master_recovery_verifier")

    def test_10_default_pinned_bodydata_and_backup_constants(self) -> None:
        self.assertEqual(P180_PINNED_FX3_BODYDATA_BYTES, 811_876_768)
        self.assertEqual(P180_PINNED_FX3_WBI2_TOTAL_BYTES, 209_112_512)
        self.assertEqual(P180_PINNED_FX3_NFLASHA15_BYTES, 479_846_400)
        self.assertEqual(P180_FX3_MIN_BODY_FLOOR_VERSION, "2.04")
        self.assertEqual(P180_C2PA_MAX_LICENSES, 100)

    # ------------------------------------------------------------------
    # Group A (11..24): Pillar 24A — Slot-1 BODYDATA.DAT Readiness
    # ------------------------------------------------------------------

    def test_11_pillar24a_happy_204_floor_ready(self) -> None:
        rep = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(body_firmware_version="2.04")
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.reflash_ready)
        self.assertTrue(rep.body_floor_204_ok)
        self.assertTrue(rep.slot1_root_and_unique_ok)
        self.assertTrue(rep.bodydata_811m_and_ufu_ok)
        self.assertTrue(rep.p1_arming_flag_clean)
        self.assertTrue(rep.p15_orig_h0_eq_h3)
        self.assertTrue(rep.p5_wbi2_h0_eq_h3)
        self.assertTrue(rep.np_fz100_power_ok)
        self.assertTrue(rep.c2pa_under_100_and_p12_ro_ok)
        self.assertEqual(rep.blocked_codes, ())

    def test_12_pillar24a_happy_702_and_300_versions_ready(self) -> None:
        for ver in ("3.00", "6.01", "7.02"):
            rep = evaluate_slot1_ufu_stock_reflash_readiness(
                Slot1UfuReflashReadinessSpec(body_firmware_version=ver)
            )
            self.assertTrue(rep.passed, f"Expected version {ver} to pass floor >=2.04")

    def test_13_pillar24a_blocks_below_204_floor_7l7s_risk(self) -> None:
        for bad_ver in ("1.00", "2.00", "2.02", "2.03", "invalid"):
            rep = evaluate_slot1_ufu_stock_reflash_readiness(
                Slot1UfuReflashReadinessSpec(body_firmware_version=bad_ver)
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.reflash_ready)
            self.assertFalse(rep.body_floor_204_ok)
            self.assertIn(BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S, rep.blocked_codes)

    def test_14_pillar24a_blocks_target_downgrade_below_body(self) -> None:
        rep = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(body_firmware_version="7.02", target_firmware_version="6.01")
        )
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_BODY_VERSION_BELOW_204_FLOOR_7L7S, rep.blocked_codes)

    def test_15_pillar24a_blocks_slot2_and_subdir_paths(self) -> None:
        r_slot2 = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(update_slot=2)
        )
        r_subdir = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(sd_file_path="/PRIVATE/SONY/BODYDATA.DAT")
        )
        for rep in (r_slot2, r_subdir):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.slot1_root_and_unique_ok)
            self.assertIn(BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA, rep.blocked_codes)

    def test_16_pillar24a_blocks_duplicate_renamed_bodydata_files(self) -> None:
        for siblings in (
            ("BODYDATA.DAT", "BODYDATA (1).DAT"),
            ("BODYDATA.DAT", "BODYDATA_OLD.DAT"),
            ("bodydata.dat",),
            ("BODYDATA.DAT", "BODYDATA.DAT"),
        ):
            rep = evaluate_slot1_ufu_stock_reflash_readiness(
                Slot1UfuReflashReadinessSpec(sibling_filenames_on_card=siblings)
            )
            self.assertFalse(rep.passed, f"Expected siblings {siblings} to fail")
            self.assertIn(BLOCKED_SLOT1_ROOT_OR_DUPLICATE_BODYDATA, rep.blocked_codes)

    def test_17_pillar24a_blocks_wrong_size_magic_or_cross_body_model(self) -> None:
        r_sz = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(bodydata_byte_length=811_876_767)
        )
        r_mag = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(ufu_magic_hex="deadbeef")
        )
        r_mod = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(target_model_id=0x910300A0, target_model_name="ILME-FX30")
        )
        for rep in (r_sz, r_mag, r_mod):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.bodydata_811m_and_ufu_ok)
            self.assertIn(BLOCKED_UFU_SIZE_MAGIC_OR_MODEL_MISMATCH, rep.blocked_codes)

    def test_18_pillar24a_blocks_dirty_p1_arming_flag(self) -> None:
        rep = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p1_update_arming_flag=1)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.p1_arming_flag_clean)
        self.assertIn(BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED, rep.blocked_codes)

    def test_19_pillar24a_blocks_unrestored_p15_orig_or_p5_wbi2(self) -> None:
        r_p15 = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p15_orig_restored=False)
        )
        r_p15_hash = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p15_h3_sha256="0" * 64)
        )
        r_p5_prefix = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p5_wbi2_prefix_hex=b"WBI3\x00\x00\x00\x00".hex())
        )
        r_p5_hash = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p5_h3_sha256="e" * 64)
        )
        for rep in (r_p15, r_p15_hash, r_p5_prefix, r_p5_hash):
            self.assertFalse(rep.passed)
            self.assertIn(BLOCKED_P1_FLAG_OR_P15_P5_H0_H3_NOT_RESTORED, rep.blocked_codes)

    def test_20_pillar24a_np_fz100_battery_floor_exact_boundary(self) -> None:
        r_ok = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(
                np_fz100_bars=P180_NP_FZ100_MIN_BARS,
                np_fz100_voltage_v=P180_NP_FZ100_MIN_VOLTAGE_V,
            )
        )
        self.assertTrue(r_ok.passed)
        r_low_bars = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(np_fz100_bars=2, np_fz100_voltage_v=7.40)
        )
        r_low_volt = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(np_fz100_bars=3, np_fz100_voltage_v=7.19)
        )
        for rep in (r_low_bars, r_low_volt):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.np_fz100_power_ok)
            self.assertIn(BLOCKED_NP_FZ100_BELOW_3BARS_OR_7V2_FLOOR, rep.blocked_codes)

    def test_21_pillar24a_c2pa_license_ceiling_100_boundary(self) -> None:
        r_100 = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(c2pa_license_count=100)
        )
        self.assertTrue(r_100.passed)
        r_101 = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(c2pa_license_count=101)
        )
        self.assertFalse(r_101.passed)
        self.assertFalse(r_101.c2pa_under_100_and_p12_ro_ok)
        self.assertIn(BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH, r_101.blocked_codes)

    def test_22_pillar24a_blocks_p12_rq_lic_ro_or_sha_breach(self) -> None:
        r_ro = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p12_blkroset_locked=False, p12_ms_rdonly=False)
        )
        r_sha = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(p12_rq_lic_h3_sha256="f" * 64)
        )
        for rep in (r_ro, r_sha):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.c2pa_under_100_and_p12_ro_ok)
            self.assertIn(BLOCKED_C2PA_100_LICENSE_CEILING_OR_P12_RO_BREACH, rep.blocked_codes)

    def test_23_pillar24a_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_slot1_ufu_stock_reflash_readiness(
            Slot1UfuReflashReadinessSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_24_pillar24a_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar24a_slot1_ufu_readiness_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P180_STATUS_VERIFIED_PILLAR_24A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P180_PILLAR_24A_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    # ------------------------------------------------------------------
    # Group B (25..36): Pillar 24B — Volatile WPA2/WPA3 & BRAW/LUT Hygiene
    # ------------------------------------------------------------------

    def test_25_pillar24b_happy_h2_h3_and_eh1_hygiene(self) -> None:
        for tr in ("H2_TO_H3_CLEAN_UNINSTALL", "EH1_SD_EJECT_47US"):
            rep = evaluate_volatile_network_braw_lut_hygiene(
                RollbackHygieneAuditSpec(
                    transition_kind=tr,
                    wireless_profiles=("WPA2", "WPA2-PSK", "WPA3", "WPA3-SAE", "ACCESS_AUTHENTICATION"),
                )
            )
            self.assertTrue(rep.passed)
            self.assertTrue(rep.hygiene_clean)
            self.assertTrue(rep.wireless_wpa2_wpa3_only_ok)
            self.assertTrue(rep.zero_wifi_cred_leak_ok)
            self.assertTrue(rep.zero_cube_lut_leak_and_p30_ok)
            self.assertTrue(rep.zero_hdmi_braw_leak_ok)
            self.assertTrue(rep.p2_backup_bin_h0_eq_h3)
            self.assertEqual(rep.blocked_codes, ())

    def test_26_pillar24b_blocks_wep_and_wpa1(self) -> None:
        for bad_prof in ("WEP", "WPA1", "WPA-PSK"):
            rep = evaluate_volatile_network_braw_lut_hygiene(
                RollbackHygieneAuditSpec(wireless_profiles=("WPA2", bad_prof))
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.wireless_wpa2_wpa3_only_ok)
            self.assertIn(BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC, rep.blocked_codes)

    def test_27_pillar24b_blocks_legacy_ipsec_and_empty_profiles(self) -> None:
        r_ipsec = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(wireless_profiles=("LEGACY_IPSEC",))
        )
        r_empty = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(wireless_profiles=())
        )
        for rep in (r_ipsec, r_empty):
            self.assertFalse(rep.passed)
            self.assertIn(BLOCKED_INSECURE_WIRELESS_WEP_WPA1_IPSEC, rep.blocked_codes)

    def test_28_pillar24b_blocks_tmpfs_wifi_credential_leak(self) -> None:
        r_tmpfs = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(tmpfs_wifi_creds_present_after_rollback=1)
        )
        r_bak = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(backup_bin_wifi_cred_bytes_leaked=32)
        )
        for rep in (r_tmpfs, r_bak):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.zero_wifi_cred_leak_ok)
            self.assertIn(BLOCKED_VOLATILE_WIFI_CREDENTIAL_LEAK_TO_BACKUP_BIN, rep.blocked_codes)

    def test_29_pillar24b_blocks_cube_lut_leak_or_p30_drift(self) -> None:
        r_tmpfs = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(tmpfs_cube_lut_files_present_after_rollback=1)
        )
        r_bak = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(backup_bin_cube_lut_bytes_leaked=256)
        )
        r_p30 = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(p30_lut_h3_sha256="9" * 64)
        )
        for rep in (r_tmpfs, r_bak, r_p30):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.zero_cube_lut_leak_and_p30_ok)
            self.assertIn(BLOCKED_CUBE_LUT_STAGING_LEAK_OR_P30_DRIFT, rep.blocked_codes)

    def test_30_pillar24b_blocks_hdmi_braw_state_leak(self) -> None:
        r_flag = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(tmpfs_hdmi_braw_flags_present_after_rollback=1)
        )
        r_bak = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(backup_bin_hdmi_braw_bytes_leaked=16)
        )
        for rep in (r_flag, r_bak):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.zero_hdmi_braw_leak_ok)
            self.assertIn(BLOCKED_HDMI_BRAW_STATE_LEAK_TO_BACKUP_BIN, rep.blocked_codes)

    def test_31_pillar24b_blocks_backup_bin_drift_or_ro_unlock(self) -> None:
        r_drift = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(p2_backup_bin_h3_sha256="e" * 64)
        )
        r_ro = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(p2_blkroset_locked=False)
        )
        for rep in (r_drift, r_ro):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.p2_backup_bin_h0_eq_h3)
            self.assertIn(BLOCKED_PERSISTENT_WRITE_OR_BACKUP_BIN_DRIFT, rep.blocked_codes)

    def test_32_pillar24b_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_33_pillar24b_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar24b_rollback_hygiene_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P180_STATUS_VERIFIED_PILLAR_24B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P180_PILLAR_24B_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    def test_34_pillar24b_hygiene_report_to_dict_serializable(self) -> None:
        rep = evaluate_volatile_network_braw_lut_hygiene().to_dict()
        dumped = _assert_json_has_no_raw_bytes(rep)
        self.assertIn("H2_TO_H3_CLEAN_UNINSTALL", dumped)

    def test_35_pillar24a_report_to_dict_serializable(self) -> None:
        rep = evaluate_slot1_ufu_stock_reflash_readiness().to_dict()
        dumped = _assert_json_has_no_raw_bytes(rep)
        self.assertIn("body_floor_204_ok", dumped)

    def test_36_pillar24_combined_fault_accumulation(self) -> None:
        rep = evaluate_volatile_network_braw_lut_hygiene(
            RollbackHygieneAuditSpec(
                wireless_profiles=("WEP",),
                tmpfs_wifi_creds_present_after_rollback=1,
                tmpfs_cube_lut_files_present_after_rollback=1,
                tmpfs_hdmi_braw_flags_present_after_rollback=1,
                p2_blkroset_locked=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(len(rep.blocked_codes), 5)

    # ------------------------------------------------------------------
    # Group C (37..44): Pillar 24 Standalone & Unified 24/24 Master
    # ------------------------------------------------------------------

    def test_37_pillar24_standalone_clean_room_passes(self) -> None:
        rep = run_pillar24_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P180_STATUS_VERIFIED_PILLAR24_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_24a_slot1_ufu_readiness.scenarios_passed, 6)
        self.assertEqual(rep.pillar_24b_rollback_hygiene.scenarios_passed, 6)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_38_master_24pillar_clean_room_24of24_and_budget(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P180_STATUS_VERIFIED_24OF24_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 24)
        self.assertEqual(rep.pillars_passed, 24)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P180_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_clean_dt, P180_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_1_8s_budget)
        self.assertEqual(tuple(p.pillar_number for p in rep.pillars), tuple(range(1, 25)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_24_PILLAR_IDS)
        self.assertTrue(all(p.passed for p in rep.pillars))

    def test_39_master_24pillar_default_mode_24of24_and_budget(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P180_STATUS_VERIFIED_24OF24_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 24)
        self.assertEqual(rep.pillars_passed, 24)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P180_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_default_dt, P180_CONCURRENT_CEILING_SECONDS)
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if p24_mod.is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)

    def test_40_master_24pillar_safety_counters_all_zero_and_locked(self) -> None:
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

    def test_41_master_24pillar_deterministic_sha256_in_clean_room(self) -> None:
        r1 = self._clean_master()
        r2 = verify_24pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_24pillar_sha256, r2.master_24pillar_sha256)
        self.assertEqual(len(r1.master_24pillar_sha256), 64)

    def test_42_master_24pillar_fault_injection_fail_closed(self) -> None:
        for pid in (
            MASTER_24_PILLAR_IDS[0],
            MASTER_24_PILLAR_IDS[22],
            MASTER_24_PILLAR_IDS[23],
        ):
            rep = evaluate_24pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, P180_STATUS_FAIL_24OF24_AGGREGATOR)
            self.assertEqual(rep.pillar_count, 24)
            self.assertEqual(rep.pillars_passed, 23)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_43_master_24pillar_unknown_fault_inject_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_24pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_25",
            )

    def test_44_backward_compat_22pillar_master_intact(self) -> None:
        m22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m22.all_passed)
        self.assertEqual(m22.pillar_count, 22)
        self.assertEqual(m22.pillars_passed, 22)

    # ------------------------------------------------------------------
    # Group D (45..50): CLI Entrypoints & Backward Compatibility
    # ------------------------------------------------------------------

    def test_45_cli_verify_slot1_ufu_reflash_readiness_summary_and_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-slot1-ufu-reflash-readiness", "--force-clean-room"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_PILLAR24_SLOT1_UFU_REFLASH_AND_HYGIENE", buf.getvalue())
        self.assertIn("pillar_24a=6/6", buf.getvalue())
        self.assertIn("pillar_24b=6/6", buf.getvalue())

        buf_json = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-slot1-ufu-reflash-readiness", "--force-clean-room", "--json"]
        ):
            with redirect_stdout(buf_json):
                rc_j = fx3_cli.main()
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P180_STATUS_VERIFIED_PILLAR24_SUITE)
        _walk_check_no_bytes(payload)

    def test_46_cli_verify_24pillar_recovery_summary(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-24pillar-recovery", "--force-clean-room"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=VERIFIED_24OF24_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=24/24", out)
        self.assertIn("pillar24_a=6/6", out)
        self.assertIn("pillar24_b=6/6", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_47_cli_verify_24pillar_recovery_json_and_out_dir(self) -> None:
        scratch_dir = ROOT / "work" / "_tests" / "phase180_cli_out"
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
                    "verify-24pillar-recovery",
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
            self.assertEqual(payload["schema"], PHASE180_SCHEMA)
            self.assertEqual(payload["version"], PHASE180_VERSION)
            self.assertEqual(payload["pillar_count"], 24)
            self.assertEqual(payload["pillars_passed"], 24)
            out_file = scratch_dir / "24pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            saved = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["master_24pillar_sha256"], payload["master_24pillar_sha256"])
        finally:
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir)

    def test_48_cli_verify_24pillar_recovery_fail_exit_code_2(self) -> None:
        failing = evaluate_24pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_24_PILLAR_IDS[23],
        )
        buf = io.StringIO()
        with mock.patch.object(fx3_cli, "verify_24pillar_recovery_suite", return_value=failing):
            with mock.patch.object(
                sys, "argv", ["fx3_recovery", "verify-24pillar-recovery", "--force-clean-room", "--json"]
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["all_passed"])
        self.assertEqual(payload["status"], P180_STATUS_FAIL_24OF24_AGGREGATOR)

    def test_49_cli_verify_slot1_fail_exit_code_2(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            fx3_cli,
            "run_pillar24_standalone_suite",
            side_effect=RuntimeError("simulated safety gate halt"),
        ):
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-slot1-ufu-reflash-readiness", "--force-clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "REJECTED")
        self.assertEqual(payload["camera_operations"], 0)

    def test_50_cli_backward_compat_verify_22pillar_recovery(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-22pillar-recovery", "--clean-room", "--json"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 22)
        self.assertEqual(payload["pillars_passed"], 22)


if __name__ == "__main__":
    unittest.main()
