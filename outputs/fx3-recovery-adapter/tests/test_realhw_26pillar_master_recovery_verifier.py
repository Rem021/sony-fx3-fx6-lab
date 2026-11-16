"""Phase 190 (Pillar 26 / 26/26 Recovery Master) Dual-Mode Fast Unit Tests (50 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection, bounded reads, FX3_FX6_FORCE_CLEAN_ROOM=1
  fallback, determinism, zero raw firmware bytes in JSON & Master 26-pillar registry
- Group A (11..24): Pillar 26A — ILME-FX3 (Ver. 7.02, 1.44M LCD + NFC + IR) vs ILME-FX3A
  (Ver. 2.02, 2.36M XGA LCD, no NFC/IR) recovery & BODYDATA.DAT / CAMSET branch firewall
  (bidirectional FX3 <-> FX3A/FX30/FX6 blocks, CAMSET01..10 guard, Backup.bin H0==H3, <50us)
- Group B (25..36): Pillar 26B — XLR-H1 MI-Shoe 48kHz/24bit 4ch post-recovery & post-UFU
  48kHz/16bit 2ch reset audio hygiene (zero handle FW writes, body 3.5mm override safety,
  S&Q mute, +48V transition glitch, Stage-B zero Backup.bin dirtying)
- Group C (37..44): Pillar 26 standalone, Unified 26/26 Recovery Master Aggregator in both
  LOCAL_DONOR_O_RDONLY & CLEAN_ROOM_SYNTHETIC modes (<6.0s concurrency-safe ceiling), safety
  counters == 0, fault_inject_pillar fail-closed & 22/22 + 24/24 backward compatibility
- Group D (45..50): CLI `verify-fx3a-branch-recovery-firewall` & `verify-26pillar-recovery`
  (--json, --force-clean-room, --out, exit code 2 on failure) + 22/24-pillar CLI compat
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
from fx3_recovery import realhw_26pillar_master_recovery_verifier as p26_mod
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import evaluate_22pillar_recovery_master
from fx3_recovery.realhw_24pillar_master_recovery_verifier import (
    MASTER_24_PILLAR_IDS,
    evaluate_24pillar_recovery_master,
)
from fx3_recovery.realhw_26pillar_master_recovery_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_26_PILLAR_COUNT,
    MASTER_26_PILLAR_IDS,
    MASTER_26_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P190_BLOCKED_BACKUP_BIN_H0_H3_OR_RO_DRIFT,
    P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE,
    P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE,
    P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT,
    P190_BLOCKED_LATENCY_BUDGET_EXCEEDED,
    P190_BLOCKED_LCD_NFC_IR_SIGNATURE_MISMATCH,
    P190_BLOCKED_NON_FX3_HARDWARE_BRANCH,
    P190_BLOCKED_POST_UFU_XLRH1_RESET_UNAUDITED,
    P190_BLOCKED_SAFETY_POLICY_VIOLATION,
    P190_BLOCKED_SQ_MUTE_OR_48V_TRANSITION_GLITCH,
    P190_BLOCKED_STAGE_B_BACKUP_BIN_DIRTY,
    P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN,
    P190_BLOCKED_XLRH1_FORMAT_OR_ROUTING_INVALID,
    P190_CONCURRENT_CEILING_SECONDS,
    P190_DONOR_FX3_APPFW_SO_RELPATH,
    P190_DONOR_FX3_BACKUP_BIN_RELPATH,
    P190_DONOR_FX3_BODYDATA_RELPATH,
    P190_DONOR_FX3_CPAPP_B_RELPATH,
    P190_DONOR_FX3_PARTINF_RELPATH,
    P190_DONOR_HOTSHOE_SO_RELPATH,
    P190_FX30_MODEL_ID,
    P190_FX3A_LCD_DOTS,
    P190_FX3_LCD_DOTS,
    P190_FX3_MODEL_ID,
    P190_FX6_MODEL_ID,
    P190_PILLAR_26A_SCENARIO_IDS,
    P190_PILLAR_26B_SCENARIO_IDS,
    P190_PINNED_FX3_APPFW_SO_BYTES,
    P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256,
    P190_PINNED_FX3_BACKUP_BIN_SHA256,
    P190_PINNED_FX3_BODYDATA_BYTES,
    P190_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P190_PINNED_FX3_CPAPP_B_BYTES,
    P190_PINNED_HOTSHOE_SO_BYTES,
    P190_PINNED_HOTSHOE_SO_SHA256,
    P190_STATUS_FAIL_26OF26_AGGREGATOR,
    P190_STATUS_VERIFIED_26OF26_AGGREGATOR,
    P190_STATUS_VERIFIED_PILLAR26_SUITE,
    P190_STATUS_VERIFIED_PILLAR_26A,
    P190_STATUS_VERIFIED_PILLAR_26B,
    P190_VALID_CAMSET_FILENAMES,
    P190_XLRH1_STANDALONE_FW_SHIPPED,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE190_SCHEMA,
    PHASE190_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Fx3BranchRecoveryFirewallSpec,
    Master26PillarRecoveryReport,
    Xlrh1AudioHygieneSpec,
    evaluate_26pillar_recovery_master,
    evaluate_fx3a_branch_recovery_firewall,
    evaluate_xlrh1_mishoe_audio_hygiene,
    inspect_phase190_donors_readonly,
    run_pillar26_standalone_suite,
    run_pillar26a_fx3a_branch_firewall_6_scenario_suite,
    run_pillar26b_xlrh1_hygiene_6_scenario_suite,
    verify_26pillar_recovery_suite,
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


class TestRealHw26PillarMasterRecoveryVerifier(unittest.TestCase):
    _cached_clean_master: Master26PillarRecoveryReport | None = None
    _cached_default_master: Master26PillarRecoveryReport | None = None
    _cached_default_dt: float = 0.0
    _cached_clean_dt: float = 0.0

    @classmethod
    def _clean_master(cls) -> Master26PillarRecoveryReport:
        if cls._cached_clean_master is None:
            t0 = time.monotonic()
            cls._cached_clean_master = verify_26pillar_recovery_suite(force_clean_room=True)
            cls._cached_clean_dt = time.monotonic() - t0
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master26PillarRecoveryReport:
        if cls._cached_default_master is None:
            t0 = time.monotonic()
            cls._cached_default_master = verify_26pillar_recovery_suite()
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
        self.assertFalse(P190_XLRH1_STANDALONE_FW_SHIPPED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_zero_shadowing(self) -> None:
        self.assertIn("realhw_26pillar_master_recovery_verifier", fx3_recovery.__all__)
        self.assertIn("evaluate_26pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_26pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_fx3a_branch_recovery_firewall", fx3_recovery.__all__)
        self.assertIn("evaluate_xlrh1_mishoe_audio_hygiene", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.evaluate_26pillar_recovery_master, evaluate_26pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_26pillar_recovery_suite, verify_26pillar_recovery_suite)
        # Backward compatibility for 22-pillar and 24-pillar exports
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        # Type hints resolve cleanly
        hints = typing.get_type_hints(p26_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase190_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_702_bytes, P190_PINNED_FX3_BODYDATA_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertEqual(snap.cpapp_b_bytes, P190_PINNED_FX3_CPAPP_B_BYTES)
        self.assertTrue(snap.appfw_so_elf64_aarch64_ok)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertTrue(snap.partinf_30_partitions_ok)
        self.assertTrue(snap.hotshoe_so_elf64_aarch64_ok)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p26_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase190_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase190_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P190_DONOR_FX3_BODYDATA_RELPATH,
                P190_DONOR_FX3_CPAPP_B_RELPATH,
                P190_DONOR_FX3_APPFW_SO_RELPATH,
                P190_DONOR_FX3_BACKUP_BIN_RELPATH,
                P190_DONOR_FX3_PARTINF_RELPATH,
                P190_DONOR_HOTSHOE_SO_RELPATH,
            )
        )
        if not donors_present or p26_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 / Hotshoe local donors unavailable or clean-room forced")

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

        with mock.patch.object(p26_mod.os, "open", side_effect=spy_open), mock.patch.object(
            p26_mod.os, "pread", side_effect=spy_pread
        ):
            snap = inspect_phase190_donors_readonly(force_clean_room=False)

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
        self.assertEqual(snap.artifacts[0].sha256_digest, P190_PINNED_FX3_BODYDATA_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[2].sha256_digest, P190_PINNED_FX3_APPFW_SO_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[3].sha256_digest, P190_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(snap.artifacts[5].sha256_digest, P190_PINNED_HOTSHOE_SO_SHA256)

    def test_07_clean_room_snapshot_determinism(self) -> None:
        s1 = inspect_phase190_donors_readonly(force_clean_room=True)
        s2 = inspect_phase190_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        self.assertEqual(s1.artifacts, s2.artifacts)

    def test_08_zero_raw_firmware_bytes_in_json_reports(self) -> None:
        standalone = run_pillar26_standalone_suite(force_clean_room=True).to_dict()
        master = self._clean_master().to_dict()
        j1 = _assert_json_has_no_raw_bytes(standalone)
        j2 = _assert_json_has_no_raw_bytes(master)
        self.assertIn(PHASE190_SCHEMA, j1)
        self.assertIn(P190_STATUS_VERIFIED_26OF26_AGGREGATOR, j2)

    def test_09_master_26_pillar_registry_matches_1_through_26(self) -> None:
        self.assertEqual(MASTER_26_PILLAR_COUNT, 26)
        self.assertEqual(len(MASTER_26_PILLAR_SPECS), 26)
        self.assertEqual(tuple(s[0] for s in MASTER_26_PILLAR_SPECS), tuple(range(1, 27)))
        self.assertEqual(MASTER_26_PILLAR_IDS[:24], MASTER_24_PILLAR_IDS)
        self.assertEqual(MASTER_26_PILLAR_IDS[24], "realhw_airgap_sd_bundle_manifest_verifier")
        self.assertEqual(MASTER_26_PILLAR_IDS[25], "realhw_26pillar_master_recovery_verifier")

    def test_10_pinned_hardware_and_camset_constants(self) -> None:
        self.assertEqual(P190_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P190_FX30_MODEL_ID, 0x91030084)
        self.assertEqual(P190_FX6_MODEL_ID, 0x91020080)
        self.assertEqual(P190_FX3_LCD_DOTS, 1_440_000)
        self.assertEqual(P190_FX3A_LCD_DOTS, 2_359_296)
        self.assertEqual(P190_PINNED_FX3_APPFW_SO_BYTES, 79_015_712)
        self.assertEqual(P190_PINNED_HOTSHOE_SO_BYTES, 47_808)
        self.assertEqual(len(P190_VALID_CAMSET_FILENAMES), 10)
        self.assertEqual(P190_VALID_CAMSET_FILENAMES[0], "CAMSET01.DAT")
        self.assertEqual(P190_VALID_CAMSET_FILENAMES[-1], "CAMSET10.DAT")

    # ------------------------------------------------------------------
    # Group A (11..24): Pillar 26A — ILME-FX3 vs ILME-FX3A & CAMSET Guard
    # ------------------------------------------------------------------

    def test_11_pillar26a_happy_fx3_702_144m_nfc_ir_ready(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(Fx3BranchRecoveryFirewallSpec())
        self.assertTrue(rep.passed)
        self.assertTrue(rep.recovery_admitted)
        self.assertFalse(rep.fail_closed_triggered)
        self.assertTrue(rep.body_branch_fx3_verified)
        self.assertTrue(rep.lcd_nfc_ir_signature_ok)
        self.assertTrue(rep.recovery_image_branch_ok)
        self.assertTrue(rep.camset_import_ok)
        self.assertTrue(rep.p2_backup_bin_h0_eq_h3)
        self.assertTrue(rep.latency_under_50us_ok)
        self.assertEqual(rep.blocked_codes, ())

    def test_12_pillar26a_blocks_fx3a_236m_xga_no_nfc_ir_body(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(
                body_branch="FX3A",
                body_model_name="ILME-FX3A",
                body_firmware_version="2.02",
                body_lcd_dots=P190_FX3A_LCD_DOTS,
                body_has_nfc=False,
                body_has_ir_receiver=False,
                recovery_image_branch="FX3A",
                recovery_image_fw_version="2.02",
                display_shim_branch="FX3A",
                camset_source_branch="FX3A",
                camset_source_fw_version="2.02",
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.recovery_admitted)
        self.assertTrue(rep.fail_closed_triggered)
        self.assertFalse(rep.body_branch_fx3_verified)
        self.assertFalse(rep.lcd_nfc_ir_signature_ok)
        self.assertIn(P190_BLOCKED_NON_FX3_HARDWARE_BRANCH, rep.blocked_codes)
        self.assertIn(P190_BLOCKED_LCD_NFC_IR_SIGNATURE_MISMATCH, rep.blocked_codes)

    def test_13_pillar26a_blocks_fx3a_v1xx_and_v2xx_bodydata_on_fx3(self) -> None:
        for fx3a_ver in ("1.00", "1.01", "2.00", "2.02"):
            rep = evaluate_fx3a_branch_recovery_firewall(
                Fx3BranchRecoveryFirewallSpec(
                    recovery_image_branch="FX3A",
                    recovery_image_fw_version=fx3a_ver,
                )
            )
            self.assertFalse(rep.passed, f"Expected FX3A {fx3a_ver} BODYDATA on FX3 to be blocked")
            self.assertFalse(rep.recovery_image_branch_ok)
            self.assertIn(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE, rep.blocked_codes)

    def test_14_pillar26a_blocks_fx3_bodydata_on_fx3a_vice_versa(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(
                body_branch="FX3A",
                body_model_name="ILME-FX3A",
                body_firmware_version="2.02",
                body_lcd_dots=P190_FX3A_LCD_DOTS,
                body_has_nfc=False,
                body_has_ir_receiver=False,
                recovery_image_branch="FX3",
                recovery_image_fw_version="7.02",
            )
        )
        self.assertFalse(rep.passed)
        self.assertIn(P190_BLOCKED_NON_FX3_HARDWARE_BRANCH, rep.blocked_codes)
        self.assertIn(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE, rep.blocked_codes)

    def test_15_pillar26a_blocks_fx30_and_fx6_recovery_images_on_fx3(self) -> None:
        r_fx30 = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(
                recovery_image_branch="FX30",
                recovery_image_model_id=P190_FX30_MODEL_ID,
                recovery_image_fw_version="5.00",
            )
        )
        r_fx6 = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(
                recovery_image_branch="FX6",
                recovery_image_model_id=P190_FX6_MODEL_ID,
                recovery_image_fw_version="5.00",
            )
        )
        for rep in (r_fx30, r_fx6):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.recovery_image_branch_ok)
            self.assertIn(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE, rep.blocked_codes)

    def test_16_pillar26a_blocks_fx3_recovery_image_on_fx30_or_fx6_vice_versa(self) -> None:
        for b_branch, b_name, b_id in (
            ("FX30", "ILME-FX30", P190_FX30_MODEL_ID),
            ("FX6", "ILME-FX6", P190_FX6_MODEL_ID),
        ):
            rep = evaluate_fx3a_branch_recovery_firewall(
                Fx3BranchRecoveryFirewallSpec(
                    body_branch=b_branch,
                    body_model_name=b_name,
                    body_model_id=b_id,
                    body_firmware_version="5.00",
                    recovery_image_branch="FX3",
                    recovery_image_model_id=P190_FX3_MODEL_ID,
                    recovery_image_fw_version="7.02",
                )
            )
            self.assertFalse(rep.passed)
            self.assertIn(P190_BLOCKED_NON_FX3_HARDWARE_BRANCH, rep.blocked_codes)
            self.assertIn(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE, rep.blocked_codes)

    def test_17_pillar26a_blocks_fx3a_display_shim_transplant_on_fx3(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(display_shim_branch="FX3A")
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.recovery_image_branch_ok)
        self.assertIn(P190_BLOCKED_CROSS_BRANCH_BODYDATA_IMAGE, rep.blocked_codes)

    def test_18_pillar26a_admits_all_valid_fx3_camset01_to_camset10_slots(self) -> None:
        for fn in P190_VALID_CAMSET_FILENAMES:
            rep = evaluate_fx3a_branch_recovery_firewall(
                Fx3BranchRecoveryFirewallSpec(camset_filename=fn)
            )
            self.assertTrue(rep.passed, f"Expected {fn} from FX3 7.02 to be admitted")
            self.assertTrue(rep.camset_import_ok)

    def test_19_pillar26a_blocks_cross_branch_camset_imports_fx3a_fx30_fx6(self) -> None:
        for src_branch, src_id, src_fw in (
            ("FX3A", P190_FX3_MODEL_ID, "2.02"),
            ("FX30", P190_FX30_MODEL_ID, "5.00"),
            ("FX6", P190_FX6_MODEL_ID, "5.00"),
        ):
            rep = evaluate_fx3a_branch_recovery_firewall(
                Fx3BranchRecoveryFirewallSpec(
                    camset_filename="CAMSET05.DAT",
                    camset_source_branch=src_branch,
                    camset_source_model_id=src_id,
                    camset_source_fw_version=src_fw,
                )
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.camset_import_ok)
            self.assertIn(P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT, rep.blocked_codes)

    def test_20_pillar26a_blocks_invalid_camset_slot_names(self) -> None:
        for bad_name in ("CAMSET00.DAT", "CAMSET11.DAT", "CAMSET99.DAT", "camset01.dat", "EVIL.BIN"):
            rep = evaluate_fx3a_branch_recovery_firewall(
                Fx3BranchRecoveryFirewallSpec(camset_filename=bad_name)
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.camset_import_ok)
            self.assertIn(P190_BLOCKED_CROSS_BRANCH_CAMSET_IMPORT, rep.blocked_codes)

    def test_21_pillar26a_blocks_backup_bin_h0_h3_drift_or_blkroset_unlock(self) -> None:
        r_hash = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(p2_backup_bin_h3_sha256="1" * 64)
        )
        r_ro = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(p2_blkroset_locked=False)
        )
        for rep in (r_hash, r_ro):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.p2_backup_bin_h0_eq_h3)
            self.assertIn(P190_BLOCKED_BACKUP_BIN_H0_H3_OR_RO_DRIFT, rep.blocked_codes)

    def test_22_pillar26a_blocks_latency_over_50us_ceiling(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(detection_latency_us=50.1)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.latency_under_50us_ok)
        self.assertIn(P190_BLOCKED_LATENCY_BUDGET_EXCEEDED, rep.blocked_codes)

    def test_23_pillar26a_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_fx3a_branch_recovery_firewall(
            Fx3BranchRecoveryFirewallSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(P190_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_24_pillar26a_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar26a_fx3a_branch_firewall_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P190_STATUS_VERIFIED_PILLAR_26A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P190_PILLAR_26A_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    # ------------------------------------------------------------------
    # Group B (25..36): Pillar 26B — XLR-H1 MI-Shoe Audio Hygiene
    # ------------------------------------------------------------------

    def test_25_pillar26b_happy_xlrh1_48khz_24bit_4ch_and_all_valid_profiles(self) -> None:
        for prof, in3 in (
            ("48KHZ_24BIT_4CH", "CH3_CH4"),
            ("48KHZ_24BIT_2CH", "OFF"),
            ("48KHZ_16BIT_2CH", "OFF"),
        ):
            for matrix in ("CH1_2", "CH3_4", "CH1+3_CH2+4"):
                rep = evaluate_xlrh1_mishoe_audio_hygiene(
                    Xlrh1AudioHygieneSpec(
                        audio_profile=prof,
                        in3_route=in3,
                        headphone_monitor_matrix=matrix,
                    )
                )
                self.assertTrue(rep.passed, f"Expected profile={prof}, matrix={matrix} to pass")
                self.assertTrue(rep.hygiene_clean)
                self.assertTrue(rep.zero_handle_fw_write_ok)
                self.assertTrue(rep.audio_format_and_routing_ok)
                self.assertTrue(rep.stage_b_zero_backup_bin_dirty_ok)

    def test_26_pillar26b_blocks_standalone_xlrh1_firmware_write_attempt(self) -> None:
        r_req = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(standalone_handle_fw_write_requested=True)
        )
        r_file = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(standalone_handle_fw_files_present=("XLRH1_BODYDATA.DAT",))
        )
        for rep in (r_req, r_file):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.zero_handle_fw_write_ok)
            self.assertIn(P190_BLOCKED_XLRH1_FIRMWARE_WRITE_FORBIDDEN, rep.blocked_codes)

    def test_27_pillar26b_body_35mm_override_safe_in_muted_cold_boot_recovery(self) -> None:
        rep = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(
                body_35mm_mic_plug_inserted=True,
                mi_shoe_active_audio_expected=False,
                cold_boot_recovery_active=True,
                mi_shoe_audio_muted=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.body_35mm_override_safe)
        self.assertEqual(rep.blocked_codes, ())

    def test_28_pillar26b_body_35mm_override_blocks_when_mi_shoe_active_expected(self) -> None:
        rep = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(
                body_35mm_mic_plug_inserted=True,
                mi_shoe_active_audio_expected=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.body_35mm_override_safe)
        self.assertIn(P190_BLOCKED_BODY_35MM_MIC_JACK_OVERRIDE, rep.blocked_codes)

    def test_29_pillar26b_blocks_sq_unmuted_and_48v_stage_b_glitch(self) -> None:
        r_sq = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(sq_slow_quick_active=True, mi_shoe_audio_muted=False)
        )
        r_48v = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(phantom_48v_stage_b_transition_glitch=True)
        )
        for rep in (r_sq, r_48v):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.sq_and_48v_transition_ok)
            self.assertIn(P190_BLOCKED_SQ_MUTE_OR_48V_TRANSITION_GLITCH, rep.blocked_codes)

    def test_30_pillar26b_audits_post_ufu_48khz_16bit_2ch_reset_and_rearm(self) -> None:
        r_reset = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(
                post_ufu_upgrade_performed=True,
                audio_profile="48KHZ_16BIT_2CH",
                in3_route="OFF",
            )
        )
        self.assertTrue(r_reset.passed)
        self.assertTrue(r_reset.post_ufu_reset_audited_ok)
        self.assertTrue(r_reset.post_ufu_reset_to_16bit_2ch_documented)

        r_rearmed = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(
                post_ufu_upgrade_performed=True,
                post_ufu_rearmed_to_24bit_4ch=True,
                audio_profile="48KHZ_24BIT_4CH",
            )
        )
        self.assertTrue(r_rearmed.passed)
        self.assertTrue(r_rearmed.post_ufu_reset_audited_ok)

    def test_31_pillar26b_blocks_unaudited_post_ufu_24bit_4ch_claim(self) -> None:
        rep = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(
                post_ufu_upgrade_performed=True,
                audio_profile="48KHZ_24BIT_4CH",
                post_ufu_rearmed_to_24bit_4ch=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.post_ufu_reset_audited_ok)
        self.assertIn(P190_BLOCKED_POST_UFU_XLRH1_RESET_UNAUDITED, rep.blocked_codes)

    def test_32_pillar26b_blocks_stage_b_backup_bin_dirtying_or_ro_breach(self) -> None:
        r_wr = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(stage_b_backup_bin_writes=1)
        )
        r_sha = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(p2_backup_bin_h3_sha256="2" * 64)
        )
        r_ro = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(p2_blkroset_locked=False)
        )
        for rep in (r_wr, r_sha, r_ro):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.stage_b_zero_backup_bin_dirty_ok)
            self.assertIn(P190_BLOCKED_STAGE_B_BACKUP_BIN_DIRTY, rep.blocked_codes)

    def test_33_pillar26b_blocks_invalid_routing_or_monitor_matrix(self) -> None:
        r_prof = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(audio_profile="96KHZ_32BIT_8CH")
        )
        r_mat = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(headphone_monitor_matrix="INVALID")
        )
        for rep in (r_prof, r_mat):
            self.assertFalse(rep.passed)
            self.assertFalse(rep.audio_format_and_routing_ok)
            self.assertIn(P190_BLOCKED_XLRH1_FORMAT_OR_ROUTING_INVALID, rep.blocked_codes)

    def test_34_pillar26b_blocks_persistent_write_unlock(self) -> None:
        rep = evaluate_xlrh1_mishoe_audio_hygiene(
            Xlrh1AudioHygieneSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertIn(P190_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_35_pillar26b_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar26b_xlrh1_hygiene_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P190_STATUS_VERIFIED_PILLAR_26B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P190_PILLAR_26B_SCENARIO_IDS)
        self.assertTrue(all(o.passed for o in res.scenarios))

    def test_36_pillar26_reports_json_serializable_no_raw_bytes(self) -> None:
        d1 = evaluate_fx3a_branch_recovery_firewall().to_dict()
        d2 = evaluate_xlrh1_mishoe_audio_hygiene().to_dict()
        _assert_json_has_no_raw_bytes(d1)
        _assert_json_has_no_raw_bytes(d2)

    # ------------------------------------------------------------------
    # Group C (37..44): Pillar 26 Standalone & Unified 26/26 Master
    # ------------------------------------------------------------------

    def test_37_pillar26_standalone_clean_room_passes(self) -> None:
        rep = run_pillar26_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P190_STATUS_VERIFIED_PILLAR26_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_26a_fx3a_firewall.scenarios_passed, 6)
        self.assertEqual(rep.pillar_26b_xlrh1_hygiene.scenarios_passed, 6)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_38_master_26pillar_clean_room_26of26_and_budget(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P190_STATUS_VERIFIED_26OF26_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 26)
        self.assertEqual(rep.pillars_passed, 26)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P190_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_clean_dt, P190_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)
        self.assertEqual(tuple(p.pillar_number for p in rep.pillars), tuple(range(1, 27)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_26_PILLAR_IDS)
        self.assertTrue(all(p.passed for p in rep.pillars))

    def test_39_master_26pillar_default_mode_26of26_and_budget(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P190_STATUS_VERIFIED_26OF26_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 26)
        self.assertEqual(rep.pillars_passed, 26)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, P190_CONCURRENT_CEILING_SECONDS)
        self.assertLess(self._cached_default_dt, P190_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if p26_mod.is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)

    def test_40_master_26pillar_safety_counters_all_zero_and_locked(self) -> None:
        for rep in (self._clean_master(), self._default_master()):
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.otp_fuse_writes, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.pillar25_airgap_sd_bundle.airgap_sockets_opened, 0)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.isp_write_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.allow_boot_partition_targeting)
            self.assertFalse(rep.allow_destructive_fastboot)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)

    def test_41_master_26pillar_deterministic_sha256_in_clean_room(self) -> None:
        r1 = self._clean_master()
        r2 = verify_26pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_26pillar_sha256, r2.master_26pillar_sha256)
        self.assertEqual(len(r1.master_26pillar_sha256), 64)

    def test_42_master_26pillar_fault_injection_fail_closed(self) -> None:
        for pid in (
            MASTER_26_PILLAR_IDS[0],
            MASTER_26_PILLAR_IDS[23],
            MASTER_26_PILLAR_IDS[24],
            MASTER_26_PILLAR_IDS[25],
        ):
            rep = evaluate_26pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, P190_STATUS_FAIL_26OF26_AGGREGATOR)
            self.assertEqual(rep.pillar_count, 26)
            self.assertEqual(rep.pillars_passed, 25)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_43_master_26pillar_unknown_fault_inject_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_26pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_27",
            )

    def test_44_backward_compat_22pillar_and_24pillar_master_intact(self) -> None:
        m22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m22.all_passed)
        self.assertEqual(m22.pillar_count, 22)
        self.assertEqual(m22.pillars_passed, 22)

        m24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m24.all_passed)
        self.assertEqual(m24.pillar_count, 24)
        self.assertEqual(m24.pillars_passed, 24)

    # ------------------------------------------------------------------
    # Group D (45..50): CLI Entrypoints & Backward Compatibility
    # ------------------------------------------------------------------

    def test_45_cli_verify_fx3a_branch_recovery_firewall_summary_and_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-fx3a-branch-recovery-firewall", "--force-clean-room"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_PILLAR26_FX3A_BRANCH_FIREWALL_AND_XLRH1_HYGIENE", buf.getvalue())
        self.assertIn("pillar_26a=6/6", buf.getvalue())
        self.assertIn("pillar_26b=6/6", buf.getvalue())

        buf_json = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-fx3a-branch-recovery-firewall", "--force-clean-room", "--json"],
        ):
            with redirect_stdout(buf_json):
                rc_j = fx3_cli.main()
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P190_STATUS_VERIFIED_PILLAR26_SUITE)
        _walk_check_no_bytes(payload)

    def test_46_cli_verify_26pillar_recovery_summary(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["fx3_recovery", "verify-26pillar-recovery", "--force-clean-room"]
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=VERIFIED_26OF26_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=26/26", out)
        self.assertIn("pillar26_a=6/6", out)
        self.assertIn("pillar26_b=6/6", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_47_cli_verify_26pillar_recovery_json_and_out_dir(self) -> None:
        scratch_dir = ROOT / "work" / "_tests" / "phase190_cli_out"
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
                    "verify-26pillar-recovery",
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
            self.assertEqual(payload["schema"], PHASE190_SCHEMA)
            self.assertEqual(payload["version"], PHASE190_VERSION)
            self.assertEqual(payload["pillar_count"], 26)
            self.assertEqual(payload["pillars_passed"], 26)
            out_file = scratch_dir / "26pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            saved = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["master_26pillar_sha256"], payload["master_26pillar_sha256"])
        finally:
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir)

    def test_48_cli_verify_26pillar_recovery_fail_exit_code_2(self) -> None:
        failing = evaluate_26pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_26_PILLAR_IDS[25],
        )
        buf = io.StringIO()
        with mock.patch.object(fx3_cli, "verify_26pillar_recovery_suite", return_value=failing):
            with mock.patch.object(
                sys, "argv", ["fx3_recovery", "verify-26pillar-recovery", "--force-clean-room", "--json"]
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["all_passed"])
        self.assertEqual(payload["status"], P190_STATUS_FAIL_26OF26_AGGREGATOR)

    def test_49_cli_verify_fx3a_branch_firewall_fail_exit_code_2(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            fx3_cli,
            "run_pillar26_standalone_suite",
            side_effect=RuntimeError("simulated pillar26 safety gate halt"),
        ):
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-fx3a-branch-recovery-firewall", "--force-clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "REJECTED")
        self.assertEqual(payload["camera_operations"], 0)

    def test_50_cli_backward_compat_verify_22_and_24_pillar_recovery(self) -> None:
        for cmd, expected_count in (
            ("verify-22pillar-recovery", 22),
            ("verify-24pillar-recovery", 24),
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
