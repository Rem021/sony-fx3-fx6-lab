"""Phase 184 (Pillar 25 — Air-Gapped Bench Guard) Dual-Mode Fast Unit Tests (50 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY | O_NOFOLLOW | O_NONBLOCK donor inspection (<0.15s), bounded reads,
  FX3_FX6_FORCE_CLEAN_ROOM=1 fallback, zero raw firmware bytes & zero network sockets
- Group A (11..26): Pillar 25A — Per-camera FX3RCPT1 (528 B) dual-copy hardware-bound
  FX3BNDL1 (HMAC-SHA256 + CRC32) manifest verifier (cross-camera mismatch, non-FX3
  0x91030084/0x91020080, <7.02, single-media st_dev, 5 Tier-0 H0 digests, tamper)
- Group B (27..42): Pillar 25B — macOS/Linux ExFAT staging hygiene, AppleDouble (._*)
  temp-dir scrubber, ELF64 EM_AARCH64 shims (fx6-stage-a-verify, libJit.so <= 64 KiB,
  libgrm-fbinit9.so), BODYDATA.DAT mutual-exclusion firewall & zero-socket guard
- Group C (43..46): Unified Pillar 25 suite runner in both modes (<6.0s budget) &
  22-pillar / 24-pillar backward compatibility
- Group D (47..50): CLI `verify-airgap-sd-bundle` (--json, --force-clean-room, --out,
  exit code 2 on failure) + legacy `verify-22pillar-recovery` & `verify-24pillar-recovery`
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import asdict
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import tempfile
import time
import typing
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery import realhw_airgap_sd_bundle_manifest_verifier as p25_mod
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import (
    evaluate_22pillar_recovery_master,
)
from fx3_recovery.realhw_24pillar_master_recovery_verifier import (
    evaluate_24pillar_recovery_master,
)
from fx3_recovery.realhw_airgap_sd_bundle_manifest_verifier import (
    AIRGAP_NETWORK_VIOLATION,
    AIRGAP_SOCKETS_OPENED,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION,
    BODY_FIRMWARE_VERSION_NOT_702,
    CAMERA_SERIAL_RECEIPT_MISMATCH,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3BNDL1_CRC32_OR_HMAC_INVALID,
    ISP_WRITE_AUTHORIZED,
    LIBJIT_EXCEEDS_64KIB_LIMIT,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MACOS_EXFAT_JUNK_DETECTED,
    NON_FX3_MODEL_ID_FORBIDDEN,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P184_BLOCKED_SAFETY_POLICY_VIOLATION,
    P184_CONCURRENT_CEILING_SECONDS,
    P184_DONOR_BODYDATA_RELPATH,
    P184_DONOR_INSPECT_BUDGET_SECONDS,
    P184_DONOR_LIBGRM_FBINIT9_RELPATH,
    P184_DONOR_LIBJIRITSU_RELPATH,
    P184_DONOR_LIBJIT_TEST_RELPATH,
    P184_DONOR_NFLASHA15_RELPATH,
    P184_DONOR_PARTINF_RELPATH,
    P184_DONOR_WBI2_RELPATH,
    P184_ELF_MACHINE_AARCH64,
    P184_ELF_TYPE_DYN,
    P184_ELF_TYPE_EXEC,
    P184_FX30_MODEL_ID,
    P184_FX3_MODEL_ID,
    P184_FX6_MODEL_ID,
    P184_LIBJIT_MAX_BYTES,
    P184_MANIFEST_MAGIC,
    P184_MANIFEST_VERSION,
    P184_PILLAR_25A_SCENARIO_IDS,
    P184_PILLAR_25B_SCENARIO_IDS,
    P184_PINNED_BODYDATA_BYTES,
    P184_PINNED_BODYDATA_HDR4K_SHA256,
    P184_PINNED_LIBGRM_FBINIT9_BYTES,
    P184_PINNED_LIBGRM_FBINIT9_SHA256,
    P184_PINNED_LIBJIRITSU_BYTES,
    P184_PINNED_LIBJIRITSU_SHA256,
    P184_PINNED_LIBJIT_TEST_BYTES,
    P184_PINNED_LIBJIT_TEST_SHA256,
    P184_PINNED_NFLASHA15_BYTES,
    P184_PINNED_NFLASHA15_HDR4K_SHA256,
    P184_PINNED_PARTINF_BYTES,
    P184_PINNED_PARTINF_SHA256,
    P184_PINNED_WBI2_BYTES,
    P184_PINNED_WBI2_HDR4K_SHA256,
    P184_STAGEB_DIR_NAME,
    P184_STATUS_VERIFIED_25A,
    P184_STATUS_VERIFIED_25B,
    P184_STATUS_VERIFIED_SUITE,
    P184_UFU_MAGIC,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE184_SCHEMA,
    PHASE184_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH,
    SHIM_NOT_ELF64_AARCH64,
    SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED,
    SPI_NOR_WRITE_AUTHORIZED,
    TIER0_PARTITION_H0_MISMATCH,
    BundleFileEntry,
    Fx3Bndl1Manifest,
    Pillar25AirgapSdBundleReport,
    audit_exfat_staging_directory,
    build_fx3bndl1_manifest,
    build_synthetic_aarch64_elf64_shim,
    build_synthetic_camera_tier0_profile,
    inspect_phase184_donors_readonly,
    parse_elf64_aarch64_shim_bytes,
    run_airgap_sd_bundle_manifest_suite,
    run_pillar25a_fx3bndl1_binding_8_scenario_suite,
    run_pillar25b_exfat_hygiene_8_scenario_suite,
    scrub_exfat_staging_tree_tempdir_dry_run,
    verify_fx3bndl1_manifest,
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


class TestRealHwAirgapSdBundleManifestVerifier(unittest.TestCase):
    _cached_clean_suite: Pillar25AirgapSdBundleReport | None = None
    _cached_default_suite: Pillar25AirgapSdBundleReport | None = None

    @classmethod
    def _clean_suite(cls) -> Pillar25AirgapSdBundleReport:
        if cls._cached_clean_suite is None:
            cls._cached_clean_suite = run_airgap_sd_bundle_manifest_suite(force_clean_room=True)
        return cls._cached_clean_suite

    @classmethod
    def _default_suite(cls) -> Pillar25AirgapSdBundleReport:
        if cls._cached_default_suite is None:
            cls._cached_default_suite = run_airgap_sd_bundle_manifest_suite()
        return cls._cached_default_suite

    # ------------------------------------------------------------------
    # Group 0 (01..10): Safety Constants, Exports, Donor Inspection & Airgap
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
        self.assertEqual(AIRGAP_SOCKETS_OPENED, 0)

    def test_02_package_exports_and_backward_compat(self) -> None:
        self.assertIn("realhw_airgap_sd_bundle_manifest_verifier", fx3_recovery.__all__)
        self.assertIn("run_airgap_sd_bundle_manifest_suite", fx3_recovery.__all__)
        self.assertIn("verify_fx3bndl1_manifest", fx3_recovery.__all__)
        self.assertIn("audit_exfat_staging_directory", fx3_recovery.__all__)
        self.assertIn("scrub_exfat_staging_tree_tempdir_dry_run", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.run_airgap_sd_bundle_manifest_suite, run_airgap_sd_bundle_manifest_suite)
        self.assertIs(fx3_recovery.verify_fx3bndl1_manifest, verify_fx3bndl1_manifest)
        # Backward compatibility for 22-pillar and 24-pillar master evaluators
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_24pillar_recovery_master, evaluate_24pillar_recovery_master)
        hints = typing.get_type_hints(p25_mod._open_rdonly_regular)
        self.assertEqual(hints["path"], Path)

    def test_03_clean_room_donor_snapshot_synthetic_only(self) -> None:
        snap = inspect_phase184_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.libgrm_fbinit9_elf64_aarch64_ok)
        self.assertTrue(snap.libjit_test_under_64k_ok)
        self.assertTrue(snap.libjiritsu_elf64_aarch64_ok)
        self.assertTrue(snap.partinf_30_partitions_ok)
        self.assertTrue(snap.wbi2_header_ok)
        self.assertTrue(snap.nflasha15_ext2_magic_ok)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertEqual(len(snap.artifacts), 7)

    def test_04_missing_donor_triggers_clean_room_fallback(self) -> None:
        with mock.patch.object(p25_mod, "resolve_donor_path", return_value=None):
            snap = inspect_phase184_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_env_force_clean_room_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase184_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    def test_06_local_donor_o_rdonly_and_bounded_reads(self) -> None:
        donors_present = all(
            resolve_donor_path(rel, require_file=True) is not None
            for rel in (
                P184_DONOR_LIBGRM_FBINIT9_RELPATH,
                P184_DONOR_LIBJIT_TEST_RELPATH,
                P184_DONOR_LIBJIRITSU_RELPATH,
                P184_DONOR_PARTINF_RELPATH,
                P184_DONOR_WBI2_RELPATH,
                P184_DONOR_NFLASHA15_RELPATH,
                P184_DONOR_BODYDATA_RELPATH,
            )
        )
        if not donors_present or p25_mod.is_forced_clean_room():
            self.skipTest("Pinned FX3 7.02 local donors unavailable or clean-room forced")

        seen_flags: list[int] = []
        orig_open = os.open

        def spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(p25_mod.os, "open", side_effect=spy_open):
            snap = inspect_phase184_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(snap.access_mode, "O_RDONLY|O_NOFOLLOW|O_NONBLOCK")
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, P184_DONOR_INSPECT_BUDGET_SECONDS)
        expected_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        self.assertEqual(len(seen_flags), 7)
        self.assertTrue(all((f & expected_flags) == expected_flags for f in seen_flags))

        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["libgrm_fbinit9_so"].byte_length, P184_PINNED_LIBGRM_FBINIT9_BYTES)
        self.assertEqual(by_id["libgrm_fbinit9_so"].sha256_digest, P184_PINNED_LIBGRM_FBINIT9_SHA256)
        self.assertEqual(by_id["libjit_test_so"].byte_length, P184_PINNED_LIBJIT_TEST_BYTES)
        self.assertEqual(by_id["libjit_test_so"].sha256_digest, P184_PINNED_LIBJIT_TEST_SHA256)
        self.assertEqual(by_id["fx3_libjiritsu_so"].byte_length, P184_PINNED_LIBJIRITSU_BYTES)
        self.assertEqual(by_id["fx3_libjiritsu_so"].sha256_digest, P184_PINNED_LIBJIRITSU_SHA256)
        self.assertEqual(by_id["fx3_partinf_conf"].byte_length, P184_PINNED_PARTINF_BYTES)
        self.assertEqual(by_id["fx3_partinf_conf"].sha256_digest, P184_PINNED_PARTINF_SHA256)
        self.assertEqual(by_id["fx3_nflasha5_wbi2"].byte_length, P184_PINNED_WBI2_BYTES)
        self.assertEqual(by_id["fx3_nflasha5_wbi2"].header_sha256, P184_PINNED_WBI2_HDR4K_SHA256)
        self.assertEqual(by_id["fx3_nflasha15_ext2"].byte_length, P184_PINNED_NFLASHA15_BYTES)
        self.assertEqual(by_id["fx3_nflasha15_ext2"].header_sha256, P184_PINNED_NFLASHA15_HDR4K_SHA256)
        self.assertEqual(by_id["fx3_702_bodydata_dat"].byte_length, P184_PINNED_BODYDATA_BYTES)
        self.assertEqual(by_id["fx3_702_bodydata_dat"].header_sha256, P184_PINNED_BODYDATA_HDR4K_SHA256)

    def test_07_donor_snapshot_json_determinism_and_no_raw_bytes(self) -> None:
        s1 = inspect_phase184_donors_readonly(force_clean_room=True)
        s2 = inspect_phase184_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)
        _assert_json_has_no_raw_bytes(s1.to_dict())

    def test_08_open_rdonly_rejects_symlink_in_tempdir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_sym_") as td:
            real_f = Path(td) / "real.bin"
            real_f.write_bytes(b"hello")
            sym_f = Path(td) / "sym.bin"
            sym_f.symlink_to(real_f)
            with self.assertRaises(ValueError):
                p25_mod._open_rdonly_regular(sym_f, allow_donor_roots=False)

    def test_09_read_bounded_donor_rejects_oversized_full_read(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_big_") as td:
            big_f = Path(td) / "big.img"
            big_f.write_bytes(b"\x00" * 1024)
            with mock.patch.object(p25_mod, "resolve_donor_path", return_value=big_f), \
                 mock.patch.object(p25_mod, "local_path", return_value=big_f):
                with self.assertRaises(ValueError):
                    p25_mod._read_bounded_donor_rdonly("fake/big.img", max_full_limit=512)

    def test_10_airgap_zero_network_sockets_opened_during_suite(self) -> None:
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network socket forbidden")):
            report = run_airgap_sd_bundle_manifest_suite(force_clean_room=True)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.airgap_sockets_opened, 0)

    # ------------------------------------------------------------------
    # Group A (11..26): Pillar 25A — FX3RCPT1 <-> FX3BNDL1 Cross-Binding
    # ------------------------------------------------------------------

    def test_11_synthetic_camera_profile_builds_dual_copy_fx3rcpt1(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-cam-01")
        self.assertEqual(cam.model_id, P184_FX3_MODEL_ID)
        self.assertEqual(cam.body_fw, "7.02")
        self.assertNotEqual(cam.st_dev_primary, cam.st_dev_secondary)
        self.assertEqual(len(bytes.fromhex(cam.receipt_copy_a_hex)), 528)
        self.assertEqual(cam.receipt_copy_a_hex, cam.receipt_copy_b_hex)

    def test_12_p25a1_happy_fx3_702_dual_copy_fx3rcpt1_bound_fx3bndl1(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-alpha")
        entries = p25_mod._default_synthetic_bundle_entries()
        manifest = build_fx3bndl1_manifest(cam, entries)
        rep = verify_fx3bndl1_manifest(manifest, cam)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.bundle_authorized)
        self.assertEqual(rep.blocked_codes, ())
        self.assertTrue(rep.dual_copy_receipt_ok)
        self.assertTrue(rep.distinct_st_dev_ok)
        self.assertTrue(rep.serial_binding_ok)
        self.assertTrue(rep.tier0_5surface_h0_ok)
        self.assertTrue(rep.crc32_ok)
        self.assertTrue(rep.hmac_sha256_ok)

    def test_13_p25a2_cross_camera_serial_transplant_rejected(self) -> None:
        cam_a = build_synthetic_camera_tier0_profile(camera_label="fx3-camera-A")
        cam_b = build_synthetic_camera_tier0_profile(camera_label="fx3-camera-B")
        manifest_a = build_fx3bndl1_manifest(cam_a, p25_mod._default_synthetic_bundle_entries())
        rep = verify_fx3bndl1_manifest(manifest_a, cam_b)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.bundle_authorized)
        self.assertIn(CAMERA_SERIAL_RECEIPT_MISMATCH, rep.blocked_codes)

    def test_14_p25a3_non_fx3_fx30_0x91030084_rejected(self) -> None:
        cam_fx30 = build_synthetic_camera_tier0_profile(camera_label="fx30-body", model_id=P184_FX30_MODEL_ID)
        manifest = build_fx3bndl1_manifest(cam_fx30, p25_mod._default_synthetic_bundle_entries())
        rep = verify_fx3bndl1_manifest(manifest, cam_fx30)
        self.assertFalse(rep.passed)
        self.assertIn(NON_FX3_MODEL_ID_FORBIDDEN, rep.blocked_codes)

    def test_15_p25a4_non_fx3_fx6_0x91020080_rejected(self) -> None:
        cam_fx6 = build_synthetic_camera_tier0_profile(camera_label="fx6-body", model_id=P184_FX6_MODEL_ID)
        manifest = build_fx3bndl1_manifest(cam_fx6, p25_mod._default_synthetic_bundle_entries())
        rep = verify_fx3bndl1_manifest(manifest, cam_fx6)
        self.assertFalse(rep.passed)
        self.assertIn(NON_FX3_MODEL_ID_FORBIDDEN, rep.blocked_codes)

    def test_16_p25a5_body_firmware_below_702_rejected(self) -> None:
        for fw in ("2.00", "2.05", "5.00", "6.01", "7.01"):
            cam_old = build_synthetic_camera_tier0_profile(camera_label=f"fx3-{fw}", body_fw=fw)
            manifest = build_fx3bndl1_manifest(cam_old, p25_mod._default_synthetic_bundle_entries())
            rep = verify_fx3bndl1_manifest(manifest, cam_old)
            self.assertFalse(rep.passed)
            self.assertIn(BODY_FIRMWARE_VERSION_NOT_702, rep.blocked_codes)

    def test_17_p25a6_single_media_same_st_dev_rejected(self) -> None:
        cam_single = build_synthetic_camera_tier0_profile(
            camera_label="fx3-same-dev",
            st_dev_primary=1001,
            st_dev_secondary=1001,
        )
        manifest = build_fx3bndl1_manifest(cam_single, p25_mod._default_synthetic_bundle_entries())
        rep = verify_fx3bndl1_manifest(manifest, cam_single)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.distinct_st_dev_ok)
        self.assertIn(SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED, rep.blocked_codes)

    def test_18_single_copy_or_corrupt_copy_b_fx3rcpt1_rejected(self) -> None:
        entries = p25_mod._default_synthetic_bundle_entries()
        cam_single_copy = build_synthetic_camera_tier0_profile(camera_label="fx3-no-b", single_copy_only=True)
        rep1 = verify_fx3bndl1_manifest(build_fx3bndl1_manifest(cam_single_copy, entries), cam_single_copy)
        self.assertFalse(rep1.passed)
        self.assertIn(SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED, rep1.blocked_codes)

        cam_corrupt_b = build_synthetic_camera_tier0_profile(camera_label="fx3-bad-b", corrupt_copy_b=True)
        rep2 = verify_fx3bndl1_manifest(build_fx3bndl1_manifest(cam_corrupt_b, entries), cam_corrupt_b)
        self.assertFalse(rep2.passed)
        self.assertIn(SINGLE_MEDIA_COLD_BACKUP_UNVERIFIED, rep2.blocked_codes)

    def test_19_p25a7_all_five_tier0_h0_digests_checked(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-h0")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries())
        for fld in (
            "p2_setting_h0_sha256",
            "p5_wbi2_h0_sha256",
            "p12_cert_h0_sha256",
            "p15_usr_h0_sha256",
            "p18_lens_h0_sha256",
        ):
            mut_man = Fx3Bndl1Manifest(**{**asdict(man), fld: "e" * 64, "bundle_entries": man.bundle_entries})
            rep = verify_fx3bndl1_manifest(mut_man, cam)
            self.assertFalse(rep.passed, f"Expected failure when {fld} tampered")
            self.assertIn(TIER0_PARTITION_H0_MISMATCH, rep.blocked_codes)

    def test_20_p25a8_crc32_and_hmac_tamper_rejected(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-tamper")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries())
        bad_crc = Fx3Bndl1Manifest(**{**asdict(man), "payload_crc32": man.payload_crc32 ^ 0x42, "bundle_entries": man.bundle_entries})
        rep_crc = verify_fx3bndl1_manifest(bad_crc, cam)
        self.assertFalse(rep_crc.passed)
        self.assertFalse(rep_crc.crc32_ok)
        self.assertIn(FX3BNDL1_CRC32_OR_HMAC_INVALID, rep_crc.blocked_codes)

        bad_mac = ("a" if man.hmac_sha256[0] != "a" else "b") + man.hmac_sha256[1:]
        bad_hmac = Fx3Bndl1Manifest(**{**asdict(man), "hmac_sha256": bad_mac, "bundle_entries": man.bundle_entries})
        rep_hmac = verify_fx3bndl1_manifest(bad_hmac, cam)
        self.assertFalse(rep_hmac.passed)
        self.assertFalse(rep_hmac.hmac_sha256_ok)
        self.assertIn(FX3BNDL1_CRC32_OR_HMAC_INVALID, rep_hmac.blocked_codes)

    def test_21_wrong_bench_secret_rejected_with_hmac_invalid(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-secret")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries(), bench_secret=b"BENCH-SECRET-1")
        rep = verify_fx3bndl1_manifest(man, cam, bench_secret=b"BENCH-SECRET-2")
        self.assertFalse(rep.passed)
        self.assertTrue(rep.crc32_ok)
        self.assertFalse(rep.hmac_sha256_ok)
        self.assertIn(FX3BNDL1_CRC32_OR_HMAC_INVALID, rep.blocked_codes)

    def test_22_bad_manifest_magic_or_version_rejected(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-magic")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries())
        bad = Fx3Bndl1Manifest(**{**asdict(man), "magic": "BADMAGIC", "version": 99, "bundle_entries": man.bundle_entries})
        rep = verify_fx3bndl1_manifest(bad, cam)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.manifest_magic_ok)
        self.assertIn(FX3BNDL1_CRC32_OR_HMAC_INVALID, rep.blocked_codes)

    def test_23_request_persistent_write_unlock_rejected_fail_closed(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-write-lock")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries())
        rep = verify_fx3bndl1_manifest(man, cam, request_persistent_write_unlock=True)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.bundle_authorized)
        self.assertIn(P184_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_24_build_fx3bndl1_manifest_entry_order_invariant(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-order")
        entries = list(p25_mod._default_synthetic_bundle_entries())
        m1 = build_fx3bndl1_manifest(cam, entries)
        m2 = build_fx3bndl1_manifest(cam, list(reversed(entries)))
        self.assertEqual(m1.payload_crc32, m2.payload_crc32)
        self.assertEqual(m1.hmac_sha256, m2.hmac_sha256)
        self.assertEqual(m1.magic, P184_MANIFEST_MAGIC)
        self.assertEqual(m1.version, P184_MANIFEST_VERSION)

    def test_25_fx3bndl1_verification_report_json_safe_and_safety_locked(self) -> None:
        cam = build_synthetic_camera_tier0_profile(camera_label="fx3-json")
        man = build_fx3bndl1_manifest(cam, p25_mod._default_synthetic_bundle_entries())
        _assert_json_has_no_raw_bytes(man.to_dict())
        rep = verify_fx3bndl1_manifest(man, cam)
        _assert_json_has_no_raw_bytes(rep.to_dict())
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.airgap_sockets_opened, 0)

    def test_26_run_pillar25a_8_scenario_suite_passes_all_8(self) -> None:
        res = run_pillar25a_fx3bndl1_binding_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P184_STATUS_VERIFIED_25A)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P184_PILLAR_25A_SCENARIO_IDS)
        _assert_json_has_no_raw_bytes(res.to_dict())

    # ------------------------------------------------------------------
    # Group B (27..42): Pillar 25B — ExFAT Hygiene, AppleDouble, ELF64 & BODYDATA
    # ------------------------------------------------------------------

    def test_27_build_and_parse_elf64_aarch64_shim_exec_and_dyn(self) -> None:
        exec_blob = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_EXEC, target_size=4096)
        dyn_blob = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, target_size=7664)
        e_info = parse_elf64_aarch64_shim_bytes(exec_blob, expected_sha256=sha256(exec_blob).hexdigest())
        d_info = parse_elf64_aarch64_shim_bytes(dyn_blob, expected_sha256=sha256(dyn_blob).hexdigest(), max_bytes=P184_LIBJIT_MAX_BYTES)
        self.assertTrue(e_info.valid and e_info.is_aarch64 and e_info.e_machine == P184_ELF_MACHINE_AARCH64)
        self.assertTrue(d_info.valid and d_info.within_size_ceiling and d_info.sha256_matched)

    def test_28_parse_elf64_rejects_bad_magic_32bit_big_endian_truncated_empty(self) -> None:
        empty = parse_elf64_aarch64_shim_bytes(b"")
        self.assertFalse(empty.valid)
        short = parse_elf64_aarch64_shim_bytes(b"\x7fELF" + b"\x00" * 16)
        self.assertFalse(short.valid)
        bad_magic = bytearray(build_synthetic_aarch64_elf64_shim())
        bad_magic[0:4] = b"NOPE"
        self.assertFalse(parse_elf64_aarch64_shim_bytes(bytes(bad_magic)).valid)
        elf32 = build_synthetic_aarch64_elf64_shim(ei_class=1)
        self.assertFalse(parse_elf64_aarch64_shim_bytes(elf32).valid)
        be = build_synthetic_aarch64_elf64_shim(ei_data=2)
        self.assertFalse(parse_elf64_aarch64_shim_bytes(be).valid)

    def test_29_p25b1_clean_exfat_stageb_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_clean_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.staging_ready)
        self.assertTrue(rep.exfat_junk_free)
        self.assertEqual(rep.appledouble_count, 0)
        self.assertTrue(rep.shims_all_elf64_aarch64_ok)
        self.assertTrue(rep.libjit_under_64kib_ok)
        self.assertTrue(rep.bodydata_mutual_exclusion_ok)
        self.assertTrue(rep.airgap_zero_sockets_ok)

    def test_30_p25b2_ds_store_and_appledouble_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_ad_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            (root / P184_STAGEB_DIR_NAME / ".DS_Store").write_bytes(b"DS")
            (root / P184_STAGEB_DIR_NAME / "._libJit.so").write_bytes(b"AD1")
            (root / P184_STAGEB_DIR_NAME / "._fx6-stage-a-verify").write_bytes(b"AD2")
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.exfat_junk_free)
        self.assertEqual(rep.appledouble_count, 2)
        self.assertIn(MACOS_EXFAT_JUNK_DETECTED, rep.blocked_codes)

    def test_31_spotlight_fseventsd_trashes_temporaryitems_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_meta_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            for dn in (".Spotlight-V100", ".fseventsd", ".Trashes", ".TemporaryItems"):
                (root / dn).mkdir()
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertIn(MACOS_EXFAT_JUNK_DETECTED, rep.blocked_codes)
        self.assertEqual(len(rep.macos_metadata_hits), 4)

    def test_32_p25b3_tempdir_scrubber_removes_junk_and_preserves_shim_sha256(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_scrub_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            (root / ".DS_Store").write_bytes(b"DS")
            (root / ".Spotlight-V100").mkdir()
            (root / ".Spotlight-V100" / "Store-V2").mkdir()
            (root / ".fseventsd").mkdir()
            (root / ".fseventsd" / "no_log").write_bytes(b"x")
            (root / P184_STAGEB_DIR_NAME / "._libJit.so").write_bytes(b"AD")
            scrub = scrub_exfat_staging_tree_tempdir_dry_run(root)
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertTrue(scrub.performed_in_tempdir)
        self.assertEqual(scrub.removed_count, 4)
        self.assertEqual(scrub.preserved_files_count, 3)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.shim_digests, digests)

    def test_33_tempdir_scrubber_refuses_outside_system_tempdir(self) -> None:
        scrub = scrub_exfat_staging_tree_tempdir_dry_run(HERE)
        self.assertFalse(scrub.performed_in_tempdir)
        self.assertEqual(scrub.removed_count, 0)
        self.assertTrue(len(scrub.errors) > 0)

    def test_34_p25b4_truncated_or_bitrot_shim_sha256_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_trunc_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            (root / P184_STAGEB_DIR_NAME / "fx6-stage-a-verify").write_bytes(b"\x7fELF")
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertIn(SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH, rep.blocked_codes)

    def test_35_missing_required_shim_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_miss_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            (root / P184_STAGEB_DIR_NAME / "libgrm-fbinit9.so").unlink()
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.shims_all_elf64_aarch64_ok)
        self.assertIn(SHIM_ELF_TRUNCATED_OR_SHA256_MISMATCH, rep.blocked_codes)

    def test_36_p25b5_wrong_arch_x86_64_or_arm32_shim_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_arch_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            arm32 = build_synthetic_aarch64_elf64_shim(e_machine=40, target_size=4096)
            (root / P184_STAGEB_DIR_NAME / "fx6-stage-a-verify").write_bytes(arm32)
            digests["fx6-stage-a-verify"] = sha256(arm32).hexdigest()
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertIn(SHIM_NOT_ELF64_AARCH64, rep.blocked_codes)

    def test_37_p25b6_libjit_exact_64kib_accepted_and_64kib_plus_1_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_jitlim_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            exact = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, target_size=P184_LIBJIT_MAX_BYTES)
            (root / P184_STAGEB_DIR_NAME / "libJit.so").write_bytes(exact)
            digests["libJit.so"] = sha256(exact).hexdigest()
            ok_rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
            self.assertTrue(ok_rep.passed and ok_rep.libjit_under_64kib_ok)

            over = build_synthetic_aarch64_elf64_shim(e_type=P184_ELF_TYPE_DYN, target_size=P184_LIBJIT_MAX_BYTES + 1)
            (root / P184_STAGEB_DIR_NAME / "libJit.so").write_bytes(over)
            digests["libJit.so"] = sha256(over).hexdigest()
            bad_rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
            self.assertFalse(bad_rep.passed)
            self.assertFalse(bad_rep.libjit_under_64kib_ok)
            self.assertIn(LIBJIT_EXCEEDS_64KIB_LIMIT, bad_rep.blocked_codes)

    def test_38_p25b7_bodydata_dat_and_duplicate_conflict_rejected(self) -> None:
        for fn in ("BODYDATA.DAT", "BODYDATA (1).DAT", "BODYDATA_OLD.DAT"):
            with tempfile.TemporaryDirectory(prefix="fx3_p25_ufu_") as td:
                root = Path(td)
                digests = p25_mod._populate_temp_stageb_tree(root)
                (root / fn).write_bytes(P184_UFU_MAGIC + b"\x00" * 32)
                rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests, p1_service_trigger_active=True)
            self.assertFalse(rep.passed, f"Expected failure for {fn}")
            self.assertFalse(rep.bodydata_mutual_exclusion_ok)
            self.assertIn(BODYDATA_DAT_MUTUAL_EXCLUSION_VIOLATION, rep.blocked_codes)

    def test_39_symlink_inside_stageb_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_symsub_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            (root / P184_STAGEB_DIR_NAME / "link_in_dir").symlink_to(root / P184_STAGEB_DIR_NAME / "libJit.so")
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        self.assertFalse(rep.passed)
        self.assertIn(MACOS_EXFAT_JUNK_DETECTED, rep.blocked_codes)

    def test_40_p25b8_airgap_socket_and_write_unlock_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_net_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            rep = audit_exfat_staging_directory(
                root,
                expected_shim_sha256s=digests,
                airgap_sockets_opened=2,
                request_persistent_write_unlock=True,
            )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.airgap_zero_sockets_ok)
        self.assertIn(AIRGAP_NETWORK_VIOLATION, rep.blocked_codes)
        self.assertIn(P184_BLOCKED_SAFETY_POLICY_VIOLATION, rep.blocked_codes)

    def test_41_exfat_audit_report_json_safe_and_safety_locked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx3_p25_json_") as td:
            root = Path(td)
            digests = p25_mod._populate_temp_stageb_tree(root)
            rep = audit_exfat_staging_directory(root, expected_shim_sha256s=digests)
        _assert_json_has_no_raw_bytes(rep.to_dict())
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)

    def test_42_run_pillar25b_8_scenario_suite_passes_all_8(self) -> None:
        res = run_pillar25b_exfat_hygiene_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P184_STATUS_VERIFIED_25B)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P184_PILLAR_25B_SCENARIO_IDS)
        _assert_json_has_no_raw_bytes(res.to_dict())

    # ------------------------------------------------------------------
    # Group C (43..46): Unified Suite Runner & Legacy Compatibility
    # ------------------------------------------------------------------

    def test_43_unified_suite_clean_room_under_6s_budget(self) -> None:
        t0 = time.monotonic()
        rep = run_airgap_sd_bundle_manifest_suite(force_clean_room=True)
        dt = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.schema, PHASE184_SCHEMA)
        self.assertEqual(rep.version, PHASE184_VERSION)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P184_STATUS_VERIFIED_SUITE)
        self.assertTrue(rep.under_6s_budget)
        self.assertLess(dt, P184_CONCURRENT_CEILING_SECONDS)
        self.assertEqual(rep.pillar_25a_fx3bndl1_binding.scenarios_passed, 8)
        self.assertEqual(rep.pillar_25b_exfat_hygiene.scenarios_passed, 8)

    def test_44_unified_suite_default_mode_under_6s_budget(self) -> None:
        rep = self._default_suite()
        self.assertTrue(rep.all_passed)
        self.assertTrue(rep.under_6s_budget)
        self.assertLess(rep.elapsed_seconds, P184_CONCURRENT_CEILING_SECONDS)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.airgap_sockets_opened, 0)

    def test_45_unified_suite_json_roundtrip_and_zero_raw_bytes(self) -> None:
        rep = self._clean_suite()
        encoded = _assert_json_has_no_raw_bytes(rep.to_dict())
        decoded = json.loads(encoded)
        self.assertEqual(decoded["schema"], PHASE184_SCHEMA)
        self.assertEqual(decoded["suite_sha256"], rep.suite_sha256)
        self.assertTrue(decoded["all_passed"])

    def test_46_backward_compat_22pillar_and_24pillar_evaluators_intact(self) -> None:
        r22 = evaluate_22pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r22.all_passed)
        self.assertEqual(r22.pillar_count, 22)
        self.assertEqual(r22.pillars_passed, 22)

        r24 = evaluate_24pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r24.all_passed)
        self.assertEqual(r24.pillar_count, 24)
        self.assertEqual(r24.pillars_passed, 24)

    # ------------------------------------------------------------------
    # Group D (47..50): CLI `verify-airgap-sd-bundle` & Legacy CLI Compat
    # ------------------------------------------------------------------

    def test_47_cli_verify_airgap_sd_bundle_json_and_out_dir(self) -> None:
        out_dir = ROOT / "work" / "_tests" / f"phase184_cli_out_{os.getpid()}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-airgap-sd-bundle", "--force-clean-room", "--json", "--out", str(out_dir)]), \
                 redirect_stdout(buf):
                rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            _assert_json_has_no_raw_bytes(payload)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["status"], P184_STATUS_VERIFIED_SUITE)
            written = out_dir / "pillar25-airgap-sd-bundle-report.json"
            self.assertTrue(written.is_file())
            self.assertEqual(json.loads(written.read_text("utf-8"))["suite_sha256"], payload["suite_sha256"])
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir)

    def test_48_cli_verify_airgap_sd_bundle_text_summary_and_clean_room_alias(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-airgap-sd-bundle", "--clean-room"]), \
             redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("pillar_25a=8/8", out)
        self.assertIn("pillar_25b=8/8", out)
        self.assertIn("airgap_sockets_opened=0", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_49_cli_verify_airgap_sd_bundle_returns_exit_2_on_failure(self) -> None:
        failing_report = self._clean_suite()
        bad_dict = failing_report.to_dict()
        bad_report = mock.MagicMock()
        bad_report.all_passed = False
        bad_report.to_dict.return_value = {**bad_dict, "all_passed": False, "status": "FAIL_PILLAR25_AIRGAP_SD_BUNDLE_MANIFEST"}

        buf = io.StringIO()
        with mock.patch.object(fx3_cli, "run_airgap_sd_bundle_manifest_suite", return_value=bad_report), \
             mock.patch.object(sys, "argv", ["fx3_recovery", "verify-airgap-sd-bundle", "--json"]), \
             redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        self.assertFalse(json.loads(buf.getvalue())["all_passed"])

    def test_50_cli_legacy_22pillar_and_24pillar_still_exit_0(self) -> None:
        buf22 = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-22pillar-recovery", "--clean-room", "--json"]), \
             redirect_stdout(buf22):
            rc22 = fx3_cli.main()
        self.assertEqual(rc22, 0)
        self.assertEqual(json.loads(buf22.getvalue())["pillars_passed"], 22)

        buf24 = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-24pillar-recovery", "--force-clean-room", "--json"]), \
             redirect_stdout(buf24):
            rc24 = fx3_cli.main()
        self.assertEqual(rc24, 0)
        self.assertEqual(json.loads(buf24.getvalue())["pillars_passed"], 24)


if __name__ == "__main__":
    unittest.main()
