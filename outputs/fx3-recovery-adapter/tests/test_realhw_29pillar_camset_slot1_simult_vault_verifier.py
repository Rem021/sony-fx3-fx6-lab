"""Phase 208 (Pillar 29 / 29/29 Recovery Master) Dual-Mode Fast Unit Tests (52 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection, bounded 4 KiB reads, FX3_FX6_FORCE_CLEAN_ROOM=1
  fallback, determinism, zero raw firmware bytes in JSON & Master 29-pillar registry
- Group A (11..23): Pillar 29A — Slot-1-only CAMSET01..10.DAT (Slot 2 / >10 / MR mode rejected,
  machine-bound WB Custom/FTP/Cert excluded), SD (/PRIVATE/SONY/SETTING/FX3/CAMSET/) vs CFexpress-A
  (/SONY/SETTING/FX3/CAMSET/) split, FX3 vs FX3A vs FX6 cross-model firewall with /tmp/fx6_camset_overlay
  tmpfs sandboxing, and BIG6 (Home) zero e-ND bus TX (e_nd_actuator_tx_count == 0)
- Group B (24..36): Pillar 29B — Dual-slot [Simult. Recording] + [Auto Switch Media = Off] strict
  vault redundancy, VMC-BNCM1 body Multi/Micro USB TC IN (blocking XLR-H1 handle Micro-USB & reverse
  BNC TC OUT EOPNOTSUPP), [De-Squeeze Display] 1.6x == 1.65x + 4 hardware locks & HDMI RAW suppression,
  external-only M&C Focus Map (<150fps), and [Shockless WB] C.Temp bypass + p2:/setting 16/16 H0 == H3
- Group C (37..46): Pillar 29 standalone, Unified 29/29 Recovery Master in LOCAL_DONOR_O_RDONLY &
  CLEAN_ROOM_SYNTHETIC (<6.0s ceiling), safety counters == 0, fault_inject_pillar & 22/24/26/27/28 compat
- Group D (47..52): CLI `verify-camset-simult-vault` & `verify-29pillar-recovery` + 22/24/26/27/28 CLI
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
from fx3_recovery import realhw_29pillar_camset_slot1_simult_vault_verifier as p29_mod
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import evaluate_22pillar_recovery_master
from fx3_recovery.realhw_24pillar_master_recovery_verifier import evaluate_24pillar_recovery_master
from fx3_recovery.realhw_26pillar_master_recovery_verifier import evaluate_26pillar_recovery_master
from fx3_recovery.realhw_27pillar_dcc1_pd_lut_vault_verifier import evaluate_27pillar_recovery_master
from fx3_recovery.realhw_28pillar_fan_pwm_shutter_lut_split_verifier import (
    MASTER_28_PILLAR_IDS,
    evaluate_28pillar_recovery_master,
)
from fx3_recovery.realhw_29pillar_camset_slot1_simult_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_29_PILLAR_COUNT,
    MASTER_29_PILLAR_IDS,
    MASTER_29_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P208_BIG6_LOWER_LEFT_APERTURE,
    P208_BIG6_LOWER_LEFT_ND_FILTER,
    P208_BLOCKED_BIG6_END_ACTUATOR_TX_OR_TILE_INVALID,
    P208_BLOCKED_CAMSET_H0_H3_VAULT_DRIFT,
    P208_BLOCKED_CAMSET_MACHINE_BOUND_ITEMS_INCLUDED,
    P208_BLOCKED_CAMSET_MEDIA_PATH_ASYMMETRY,
    P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE,
    P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE,
    P208_BLOCKED_DESQUEEZE_165X_OR_4LOCKS_VIOLATION,
    P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS,
    P208_BLOCKED_SAFETY_POLICY_VIOLATION,
    P208_BLOCKED_SHOCKLESS_WB_OR_16OF16_H0_H3_DRIFT,
    P208_BLOCKED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_DROP,
    P208_BLOCKED_VMC_BNCM1_HANDLE_PORT_OR_BNC_TC_OUT,
    P208_CAMSET_MAX_FILES,
    P208_CAMSET_ORIGIN_FX3,
    P208_CAMSET_ORIGIN_FX3A,
    P208_CAMSET_ORIGIN_FX6,
    P208_CFEXPRESS_A_CAMSET_DIR,
    P208_CONCURRENT_CEILING_SECONDS,
    P208_DESQUEEZE_ENUM_TO_FACTOR,
    P208_DONOR_FX3_APPFW_702_RELPATH,
    P208_DONOR_FX3_BACKUP_BIN_RELPATH,
    P208_DONOR_FX3_BODYDATA_RELPATH,
    P208_DONOR_FX3_CPAPP_B_RELPATH,
    P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
    P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
    P208_FOCUS_MAP_EXTERNAL_CUTOFF_FPS,
    P208_MEDIA_CFEXPRESS_A,
    P208_MEDIA_SDXC,
    P208_NOMINAL_BUDGET_SECONDS,
    P208_PILLAR_29A_SCENARIO_IDS,
    P208_PILLAR_29B_SCENARIO_IDS,
    P208_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P208_PINNED_FX3_BACKUP_BIN_SHA256,
    P208_PINNED_FX3_BODYDATA_BYTES,
    P208_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
    P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
    P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
    P208_REC_MODE_EXTENDED_OBSERVATION,
    P208_REC_MODE_SIMULT_STRICT_VAULT,
    P208_SD_CAMSET_DIR,
    P208_SHOCKLESS_WB_VALID_MODES,
    P208_STAGE_B_CAMSET_OVERLAY_DIR,
    P208_STATUS_FAIL_29OF29_AGGREGATOR,
    P208_STATUS_VERIFIED_29OF29_AGGREGATOR,
    P208_STATUS_VERIFIED_PILLAR29_SUITE,
    P208_STATUS_VERIFIED_PILLAR_29A,
    P208_STATUS_VERIFIED_PILLAR_29B,
    P208_TC_DIRECTION_BNC_OUT,
    P208_TC_PORT_BODY_MULTI_USB,
    P208_TC_PORT_XLRH1_HANDLE_MICRO_USB,
    P208_VALID_CAMSET_FILENAMES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE208_SCHEMA,
    PHASE208_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    CamsetSlot1Big6VaultSpec,
    Master29PillarRecoveryReport,
    SimultVaultTcInDesqueezeSpec,
    evaluate_29pillar_recovery_master,
    evaluate_simult_autoswitch_tcin_and_desqueeze_vault,
    evaluate_slot1_camset_and_big6_end_guard,
    inspect_phase208_donors_readonly,
    run_pillar29_standalone_suite,
    run_pillar29a_camset_slot1_big6_6_scenario_suite,
    run_pillar29b_simult_tcin_desqueeze_6_scenario_suite,
    verify_29pillar_recovery_suite,
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


class TestRealHw29PillarCamsetSlot1SimultVaultVerifier(unittest.TestCase):
    _cached_clean_master: Master29PillarRecoveryReport | None = None
    _cached_default_master: Master29PillarRecoveryReport | None = None
    _cached_default_dt: float = 0.0
    _cached_clean_dt: float = 0.0

    @classmethod
    def _clean_master(cls) -> Master29PillarRecoveryReport:
        if cls._cached_clean_master is None:
            t0 = time.monotonic()
            cls._cached_clean_master = verify_29pillar_recovery_suite(force_clean_room=True)
            cls._cached_clean_dt = time.monotonic() - t0
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master29PillarRecoveryReport:
        if cls._cached_default_master is None:
            t0 = time.monotonic()
            cls._cached_default_master = verify_29pillar_recovery_suite()
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
        self.assertIn("realhw_29pillar_camset_slot1_simult_vault_verifier", fx3_recovery.__all__)
        self.assertIn("evaluate_29pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_29pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_slot1_camset_and_big6_end_guard", fx3_recovery.__all__)
        self.assertIn("evaluate_simult_autoswitch_tcin_and_desqueeze_vault", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.evaluate_29pillar_recovery_master, evaluate_29pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_29pillar_recovery_suite, verify_29pillar_recovery_suite)
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_26pillar_recovery_master, evaluate_26pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_27pillar_recovery_master, evaluate_27pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_28pillar_recovery_master, evaluate_28pillar_recovery_master)
        hints = typing.get_type_hints(p29_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase208_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_702_bytes, P208_PINNED_FX3_BODYDATA_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertTrue(snap.cpapp_b_arm_vec_ok)
        self.assertTrue(snap.fx3_appfw_702_elf64_ok)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertTrue(snap.libinframediaconfig_elf64_ok)
        self.assertTrue(snap.libbackupmanager_elf64_ok)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p29_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase208_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase208_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P208_DONOR_FX3_BODYDATA_RELPATH,
                P208_DONOR_FX3_CPAPP_B_RELPATH,
                P208_DONOR_FX3_APPFW_702_RELPATH,
                P208_DONOR_FX3_BACKUP_BIN_RELPATH,
                P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
                P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            )
        )
        if not donors_present or p29_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 / cpapp-b / InfraMediaConfig donors unavailable or clean-room forced")

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

        with mock.patch.object(p29_mod.os, "open", side_effect=spy_open), mock.patch.object(
            p29_mod.os, "pread", side_effect=spy_pread
        ):
            snap = inspect_phase208_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(snap.donor_files_inspected, 6)
        for fl in flags_seen:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
            self.assertTrue(fl & os.O_NOFOLLOW)
            self.assertTrue(fl & os.O_NONBLOCK)
        self.assertEqual(pread_sizes, [4096, 4096, 4096])
        self.assertEqual(snap.artifacts[0].sha256_digest, P208_PINNED_FX3_BODYDATA_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[1].sha256_digest, P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[2].sha256_digest, P208_PINNED_FX3_APPFW_702_HDR4K_SHA256)
        self.assertEqual(snap.artifacts[3].sha256_digest, P208_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(snap.artifacts[4].sha256_digest, P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256)
        self.assertEqual(snap.artifacts[5].sha256_digest, P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256)

    def test_07_clean_room_snapshot_determinism(self) -> None:
        s1 = inspect_phase208_donors_readonly(force_clean_room=True)
        s2 = inspect_phase208_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        self.assertEqual(s1.artifacts, s2.artifacts)

    def test_08_zero_raw_firmware_bytes_in_json_reports(self) -> None:
        standalone = run_pillar29_standalone_suite(force_clean_room=True).to_dict()
        master = self._clean_master().to_dict()
        j1 = _assert_json_has_no_raw_bytes(standalone)
        j2 = _assert_json_has_no_raw_bytes(master)
        self.assertIn(PHASE208_SCHEMA, j1)
        self.assertIn(P208_STATUS_VERIFIED_29OF29_AGGREGATOR, j2)

    def test_09_master_29_pillar_registry_matches_1_through_29(self) -> None:
        self.assertEqual(MASTER_29_PILLAR_COUNT, 29)
        self.assertEqual(len(MASTER_29_PILLAR_SPECS), 29)
        self.assertEqual(tuple(s[0] for s in MASTER_29_PILLAR_SPECS), tuple(range(1, 30)))
        self.assertEqual(MASTER_29_PILLAR_IDS[:28], MASTER_28_PILLAR_IDS)
        self.assertEqual(MASTER_29_PILLAR_IDS[28], "realhw_29pillar_camset_slot1_simult_vault_verifier")

    def test_10_pinned_wave26_wave27_constants(self) -> None:
        self.assertEqual(P208_SD_CAMSET_DIR, "/PRIVATE/SONY/SETTING/FX3/CAMSET")
        self.assertEqual(P208_CFEXPRESS_A_CAMSET_DIR, "/SONY/SETTING/FX3/CAMSET")
        self.assertEqual(P208_STAGE_B_CAMSET_OVERLAY_DIR, "/tmp/fx6_camset_overlay")
        self.assertEqual(P208_CAMSET_MAX_FILES, 10)
        self.assertEqual(P208_DESQUEEZE_ENUM_TO_FACTOR["1.6x"], 1.65)
        self.assertEqual(P208_FOCUS_MAP_EXTERNAL_CUTOFF_FPS, 150)
        self.assertEqual(P208_NOMINAL_BUDGET_SECONDS, 2.5)
        self.assertEqual(P208_CONCURRENT_CEILING_SECONDS, 6.0)

    # ------------------------------------------------------------------
    # Group A (11..23): Pillar 29A — Slot-1 CAMSET & BIG6 Zero e-ND Guard
    # ------------------------------------------------------------------

    def test_11_pillar29a_slot1_sd_and_cfexpress_a_camset_paths_accepted(self) -> None:
        r_sd = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_SDXC, camset_dir_path=P208_SD_CAMSET_DIR)
        )
        r_cfa = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_CFEXPRESS_A, camset_dir_path=P208_CFEXPRESS_A_CAMSET_DIR)
        )
        self.assertTrue(r_sd.passed)
        self.assertTrue(r_cfa.passed)
        self.assertEqual(r_sd.expected_camset_dir, P208_SD_CAMSET_DIR)
        self.assertEqual(r_cfa.expected_camset_dir, P208_CFEXPRESS_A_CAMSET_DIR)

    def test_12_pillar29a_accepts_up_to_10_valid_camset_dat_files(self) -> None:
        rep = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(camset_filenames=P208_VALID_CAMSET_FILENAMES)
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.dat_count_and_names_ok)

    def test_13_pillar29a_rejects_slot2_camset_access(self) -> None:
        rep = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(target_slot=2))
        self.assertFalse(rep.passed)
        self.assertFalse(rep.slot1_exclusivity_ok)
        self.assertIn(P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE, rep.blocked_codes)

    def test_14_pillar29a_rejects_over_10_or_malformed_camset_filenames(self) -> None:
        r_over = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(camset_filenames=P208_VALID_CAMSET_FILENAMES + ("CAMSET11.DAT",))
        )
        r_bad_name = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(camset_filenames=("CAMSET00.DAT",))
        )
        for rep in (r_over, r_bad_name):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE, rep.blocked_codes)

    def test_15_pillar29a_rejects_camset_in_mr_recall_camera_setting_mode(self) -> None:
        rep = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(mr_recall_mode_active=True))
        self.assertFalse(rep.passed)
        self.assertFalse(rep.mr_mode_guard_ok)
        self.assertIn(P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE, rep.blocked_codes)

    def test_16_pillar29a_blocks_sd_vs_cfexpress_a_root_path_swap(self) -> None:
        r1 = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_SDXC, camset_dir_path=P208_CFEXPRESS_A_CAMSET_DIR)
        )
        r2 = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_CFEXPRESS_A, camset_dir_path=P208_SD_CAMSET_DIR)
        )
        for rep in (r1, r2):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_CAMSET_MEDIA_PATH_ASYMMETRY, rep.blocked_codes)

    def test_17_pillar29a_blocks_cross_model_fx3a_and_stock_fx6_camset_import(self) -> None:
        r_fx3a = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(camset_model_origin=P208_CAMSET_ORIGIN_FX3A)
        )
        r_fx6_stock = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(camset_model_origin=P208_CAMSET_ORIGIN_FX6, stage_b_active=False)
        )
        for rep in (r_fx3a, r_fx6_stock):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE, rep.blocked_codes)

    def test_18_pillar29a_allows_fx6_camset_only_in_stage_b_tmpfs_overlay(self) -> None:
        r_ok = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(
                camset_model_origin=P208_CAMSET_ORIGIN_FX6,
                stage_b_active=True,
                stage_b_camset_write_target=P208_STAGE_B_CAMSET_OVERLAY_DIR,
                stage_b_overlay_is_tmpfs=True,
            )
        )
        r_esc = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(
                camset_model_origin=P208_CAMSET_ORIGIN_FX6,
                stage_b_active=True,
                stage_b_camset_write_target="p2:/setting/camset",
            )
        )
        self.assertTrue(r_ok.passed)
        self.assertFalse(r_esc.passed)
        self.assertIn(P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE, r_esc.blocked_codes)

    def test_19_pillar29a_big6_aperture_and_nd_filter_metadata_only_zero_cp_tx(self) -> None:
        r_ap = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(big6_lower_left_mode=P208_BIG6_LOWER_LEFT_APERTURE, e_nd_actuator_tx_count=0)
        )
        r_nd = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(big6_lower_left_mode=P208_BIG6_LOWER_LEFT_ND_FILTER, e_nd_actuator_tx_count=0)
        )
        self.assertTrue(r_ap.passed)
        self.assertFalse(r_ap.big6_nd_metadata_only)
        self.assertTrue(r_nd.passed)
        self.assertTrue(r_nd.big6_nd_metadata_only)
        self.assertEqual(r_nd.e_nd_actuator_tx_count, 0)

    def test_20_pillar29a_blocks_big6_e_nd_actuator_tx_or_missing_home_prerequisites(self) -> None:
        r_tx = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(e_nd_actuator_tx_count=1))
        r_mode = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(big6_mode_fixed_variable=False))
        r_key = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(big6_home_custom_key_bound=False))
        for rep in (r_tx, r_mode, r_key):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_BIG6_END_ACTUATOR_TX_OR_TILE_INVALID, rep.blocked_codes)

    def test_21_pillar29a_blocks_machine_bound_wb_custom_ftp_cert_in_camset(self) -> None:
        for bad_key in ("WB_CUSTOM_1", "FTP_SERVER_CREDENTIAL", "IP_TLS_CERTIFICATE", "RTC_DATE_TIME"):
            rep = evaluate_slot1_camset_and_big6_end_guard(
                CamsetSlot1Big6VaultSpec(included_setting_keys=(bad_key,))
            )
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_CAMSET_MACHINE_BOUND_ITEMS_INCLUDED, rep.blocked_codes)

    def test_22_pillar29a_blocks_h0_h3_drift_and_persistent_write_unlock(self) -> None:
        rep = evaluate_slot1_camset_and_big6_end_guard(
            CamsetSlot1Big6VaultSpec(slot1_camset_h3_sha256="9" * 64, request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertIn(P208_BLOCKED_CAMSET_H0_H3_VAULT_DRIFT, rep.blocked_codes)
        self.assertIn(P208_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_23_pillar29a_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar29a_camset_slot1_big6_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P208_STATUS_VERIFIED_PILLAR_29A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P208_PILLAR_29A_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group B (24..36): Pillar 29B — Simult Vault, VMC-BNCM1 & 1.65x
    # ------------------------------------------------------------------

    def test_24_pillar29b_happy_simult_autoswitch_off_strict_vault_passes(self) -> None:
        rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(SimultVaultTcInDesqueezeSpec())
        self.assertTrue(rep.passed)
        self.assertTrue(rep.simult_strict_vault_ok)
        self.assertTrue(rep.auto_switch_media_off_enforced)
        self.assertEqual(rep.h0_eq_h3_surface_count, 16)

    def test_25_pillar29b_blocks_auto_switch_on_in_strict_dual_vault_mode(self) -> None:
        rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(
                vault_rec_policy=P208_REC_MODE_SIMULT_STRICT_VAULT,
                auto_switch_media_enabled=True,
                dropped_to_single_card=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertIn(P208_BLOCKED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_DROP, rep.blocked_codes)

    def test_26_pillar29b_allows_auto_switch_on_only_in_non_vault_extended_observation(self) -> None:
        rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(
                vault_rec_policy=P208_REC_MODE_EXTENDED_OBSERVATION,
                auto_switch_media_enabled=True,
                dropped_to_single_card=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertFalse(rep.auto_switch_media_off_enforced)

    def test_27_pillar29b_vmc_bncm1_body_tcin_ext_lk_and_sq_unlock_behavior(self) -> None:
        r_movie = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(vmc_bncm1_port=P208_TC_PORT_BODY_MULTI_USB, tc_shooting_mode="Movie")
        )
        r_sq = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(tc_shooting_mode="S&Q", hdmi_tc_out_enabled=True)
        )
        self.assertTrue(r_movie.passed)
        self.assertTrue(r_movie.ext_lk_timecode_locked)
        self.assertTrue(r_movie.hdmi_tc_out_effective)
        self.assertTrue(r_sq.passed)
        self.assertFalse(r_sq.ext_lk_timecode_locked)
        self.assertFalse(r_sq.hdmi_tc_out_effective)

    def test_28_pillar29b_blocks_vmc_bncm1_on_xlrh1_handle_micro_usb_or_bnc_tc_out(self) -> None:
        r_handle = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(vmc_bncm1_port=P208_TC_PORT_XLRH1_HANDLE_MICRO_USB)
        )
        r_bnc_out = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(tc_direction=P208_TC_DIRECTION_BNC_OUT, multi_usb_bnc_tc_out_tx_count=1)
        )
        for rep in (r_handle, r_bnc_out):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_VMC_BNCM1_HANDLE_PORT_OR_BNC_TC_OUT, rep.blocked_codes)

    def test_29_pillar29b_desqueeze_all_5_choices_and_exact_165x_cinema_scope(self) -> None:
        for label, factor in P208_DESQUEEZE_ENUM_TO_FACTOR.items():
            rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
                SimultVaultTcInDesqueezeSpec(desqueeze_menu_choice=label, applied_desqueeze_factor=factor)
            )
            self.assertTrue(rep.passed, f"Expected De-Squeeze {label} -> {factor}x to pass")
            self.assertEqual(rep.effective_desqueeze_factor, factor)

    def test_30_pillar29b_blocks_desqueeze_16x_applied_as_160_or_violated_4_locks(self) -> None:
        r_160 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(desqueeze_menu_choice="1.6x", applied_desqueeze_factor=1.60)
        )
        r_af = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(focus_mode="AF-C")
        )
        r_area = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(focus_area="Zone")
        )
        r_face = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(face_priority_multi_metering="On")
        )
        for rep in (r_160, r_af, r_area, r_face):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_DESQUEEZE_165X_OR_4LOCKS_VIOLATION, rep.blocked_codes)

    def test_31_pillar29b_desqueeze_suppressed_under_hdmi_raw_or_log_off(self) -> None:
        r_raw = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(hdmi_raw_output_on=True, applied_desqueeze_factor=1.0)
        )
        r_log_off = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(log_shooting_on=False, applied_desqueeze_factor=1.0)
        )
        self.assertTrue(r_raw.passed)
        self.assertTrue(r_raw.desqueeze_suppressed_by_mode)
        self.assertTrue(r_log_off.passed)
        self.assertTrue(r_log_off.desqueeze_suppressed_by_mode)

    def test_32_pillar29b_blocks_in_body_focus_map_and_ge_150fps_external_stream(self) -> None:
        r_ok_120 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(external_mc_focus_map_active=True, sensor_fps=120)
        )
        r_bad_150 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(external_mc_focus_map_active=True, sensor_fps=150)
        )
        r_inbody = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(in_body_focus_map_overlay_injected=True)
        )
        self.assertTrue(r_ok_120.passed)
        self.assertFalse(r_bad_150.passed)
        self.assertIn(P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS, r_bad_150.blocked_codes)
        self.assertFalse(r_inbody.passed)
        self.assertIn(P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS, r_inbody.blocked_codes)

    def test_33_pillar29b_shockless_wb_valid_modes_and_ctemp_immediate_bypass(self) -> None:
        for mode in P208_SHOCKLESS_WB_VALID_MODES:
            rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
                SimultVaultTcInDesqueezeSpec(shockless_wb_mode=mode, sensor_fps=120, external_mc_focus_map_active=False)
            )
            self.assertTrue(rep.passed)
            self.assertTrue(rep.shockless_wb_and_bypass_ok)

    def test_34_pillar29b_blocks_shockless_wb_invalid_mode_or_p2_setting_drift(self) -> None:
        r_wb = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(shockless_wb_mode="4 (Invalid)")
        )
        r_p2 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(p2_blkroset_locked=False, stage_b_p2_setting_writes=1)
        )
        for rep in (r_wb, r_p2):
            self.assertFalse(rep.passed)
            self.assertIn(P208_BLOCKED_SHOCKLESS_WB_OR_16OF16_H0_H3_DRIFT, rep.blocked_codes)

    def test_35_pillar29b_blocks_persistent_write_unlock_request(self) -> None:
        rep = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
            SimultVaultTcInDesqueezeSpec(request_persistent_write_unlock=True)
        )
        self.assertFalse(rep.passed)
        self.assertIn(P208_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_36_pillar29b_6_scenario_suite_passes_all(self) -> None:
        res = run_pillar29b_simult_tcin_desqueeze_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P208_STATUS_VERIFIED_PILLAR_29B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P208_PILLAR_29B_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group C (37..46): Standalone Pillar 29 & Unified 29/29 Master
    # ------------------------------------------------------------------

    def test_37_pillar29_standalone_clean_room_passes(self) -> None:
        rep = run_pillar29_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P208_STATUS_VERIFIED_PILLAR29_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_29a_camset_big6_vault.scenarios_passed, 6)
        self.assertEqual(rep.pillar_29b_simult_tcin_desqueeze_vault.scenarios_passed, 6)

    def test_38_pillar29_standalone_default_mode_passes(self) -> None:
        rep = run_pillar29_standalone_suite()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P208_STATUS_VERIFIED_PILLAR29_SUITE)
        self.assertIn(rep.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_39_master_29pillar_clean_room_29_of_29_within_6s_ceiling(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P208_STATUS_VERIFIED_29OF29_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 29)
        self.assertEqual(rep.pillars_passed, 29)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(self._cached_clean_dt, P208_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)

    def test_40_master_29pillar_default_mode_29_of_29_within_6s_ceiling(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P208_STATUS_VERIFIED_29OF29_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 29)
        self.assertEqual(rep.pillars_passed, 29)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(self._cached_default_dt, P208_CONCURRENT_CEILING_SECONDS)
        self.assertTrue(rep.under_6s_budget)

    def test_41_master_29pillar_zero_hardware_mutation_counters(self) -> None:
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

    def test_42_master_29pillar_clean_room_digest_determinism(self) -> None:
        r1 = self._clean_master()
        r2 = evaluate_29pillar_recovery_master(force_clean_room=True)
        self.assertEqual(r1.master_29pillar_sha256, r2.master_29pillar_sha256)
        self.assertEqual(tuple(p.digest_sha256 for p in r1.pillars), tuple(p.digest_sha256 for p in r2.pillars))

    def test_43_master_29pillar_fault_injection_pillar29_fails_closed_28_of_29(self) -> None:
        rep = evaluate_29pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="realhw_29pillar_camset_slot1_simult_vault_verifier",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P208_STATUS_FAIL_29OF29_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 28)
        self.assertEqual(rep.failed_pillars, ("realhw_29pillar_camset_slot1_simult_vault_verifier",))

    def test_44_master_29pillar_fault_injection_upstream_pillar28_fails_closed(self) -> None:
        rep = evaluate_29pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="realhw_28pillar_fan_pwm_shutter_lut_split_verifier",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 28)
        self.assertEqual(rep.failed_pillars, ("realhw_28pillar_fan_pwm_shutter_lut_split_verifier",))

    def test_45_master_29pillar_rejects_unknown_fault_injection_pillar_id(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_29pillar_recovery_master(force_clean_room=True, fault_inject_pillar="non_existent_pillar")

    def test_46_backward_compatibility_22_24_26_27_28_pillar_evaluators_intact(self) -> None:
        r22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        r24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        r26 = evaluate_26pillar_recovery_master(force_clean_room=True)
        r27 = evaluate_27pillar_recovery_master(force_clean_room=True)
        r28 = evaluate_28pillar_recovery_master(force_clean_room=True)
        for rep, expected in ((r22, 22), (r24, 24), (r26, 26), (r27, 27), (r28, 28)):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.pillars_passed, expected)

    # ------------------------------------------------------------------
    # Group D (47..52): CLI Subcommands & Backward-Compat CLI Regressions
    # ------------------------------------------------------------------

    @staticmethod
    def _run_cli(argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
            rc = fx3_cli.main()
        return rc, buf.getvalue()

    def test_47_cli_verify_camset_simult_vault_json_and_text(self) -> None:
        rc_json, out_json = self._run_cli(["verify-camset-simult-vault", "--force-clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        payload = json.loads(out_json)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P208_STATUS_VERIFIED_PILLAR29_SUITE)
        _assert_json_has_no_raw_bytes(payload)

        rc_txt, out_txt = self._run_cli(["verify-camset-simult-vault", "--clean-room"])
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillar_29a=6/6", out_txt)
        self.assertIn("pillar_29b=6/6", out_txt)

    def test_48_cli_verify_29pillar_recovery_json_clean_room_and_default(self) -> None:
        for extra in (["--force-clean-room"], []):
            rc, out = self._run_cli(["verify-29pillar-recovery", *extra, "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillar_count"], 29)
            self.assertEqual(payload["pillars_passed"], 29)
            self.assertEqual(payload["status"], P208_STATUS_VERIFIED_29OF29_AGGREGATOR)
            _assert_json_has_no_raw_bytes(payload)

    def test_49_cli_verify_29pillar_recovery_text_and_out_artifact(self) -> None:
        tmp_out = HERE / f"_tmp_p208_cli_{os.getpid()}"
        if tmp_out.exists():
            shutil.rmtree(tmp_out)
        try:
            rc, out = self._run_cli(["verify-29pillar-recovery", "--force-clean-room", "--out", str(tmp_out)])
            self.assertEqual(rc, 0)
            self.assertIn("pillars=29/29", out)
            report_file = tmp_out / "29pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillars_passed"], 29)
        finally:
            if tmp_out.exists():
                shutil.rmtree(tmp_out)

    def test_50_cli_verify_29pillar_recovery_returns_exit_code_2_on_failure(self) -> None:
        failed_rep = dataclasses.replace(
            self._clean_master(),
            all_passed=False,
            status=P208_STATUS_FAIL_29OF29_AGGREGATOR,
            pillars_passed=28,
            failed_pillars=("realhw_29pillar_camset_slot1_simult_vault_verifier",),
        )
        with mock.patch.object(fx3_cli, "verify_29pillar_recovery_suite", return_value=failed_rep):
            rc, _ = self._run_cli(["verify-29pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc, 2)

    def test_51_cli_backward_compatibility_22_24_26_27_28_pillar_subcommands(self) -> None:
        for cmd, flag, expected in (
            ("verify-22pillar-recovery", "--clean-room", 22),
            ("verify-24pillar-recovery", "--force-clean-room", 24),
            ("verify-26pillar-recovery", "--force-clean-room", 26),
            ("verify-27pillar-recovery", "--force-clean-room", 27),
            ("verify-28pillar-recovery", "--force-clean-room", 28),
        ):
            rc, out = self._run_cli([cmd, flag, "--json"])
            self.assertEqual(rc, 0, f"CLI {cmd} failed")
            payload = json.loads(out)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], expected)

    def test_52_schema_and_version_metadata_pinned(self) -> None:
        rep = self._clean_master()
        self.assertEqual(rep.schema, PHASE208_SCHEMA)
        self.assertEqual(rep.version, PHASE208_VERSION)
        self.assertEqual(len(rep.pillars), 29)


if __name__ == "__main__":
    unittest.main()
