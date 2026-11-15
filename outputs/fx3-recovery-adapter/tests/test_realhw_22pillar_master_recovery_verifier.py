"""Phase 166 (Pillar 22 / 22/22 Recovery Pillars) Dual-Mode Fast Unit Tests (50 tests):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports & zero symbol shadowing,
  O_RDONLY donor inspection, FX3_FX6_FORCE_CLEAN_ROOM=1 fallback & zero raw bytes in JSON
- Group A (11..24): FX3RCPT1 528B receipt, dual-media independent storage enforcement
  (media_a != media_b, 16 surfaces, p2 psd/defdet/Backup, p18 LENSFILE.BIN, Stage-A gate) & 6/6 Pillar 22A suite
- Group B (25..36): GF(256) (0x11d) RAID-6 P+Q parity archive, 0/1/2-chunk bit-rot healing,
  >=3-chunk quorum fail-closed, cross-domain/write-unlock blocking, 16/16 pre-restore RAM dry-run & 6/6 Pillar 22B suite
- Group C (37..44): Pillar 22 standalone & unified 22/22 Master Aggregator in both modes (<2.0s budget),
  determinism, safety counters == 0, and fault_inject_pillar fail-closed gate
- Group D (45..50): CLI `verify-22pillar-recovery` (summary, --json, --out, exit code 2) &
  `verify-all-recovery --with-phase166` (22/22) while preserving 7/7 default backward compatibility
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
import struct
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import ROOT, resolve_donor_path
from fx3_recovery.realhw_22pillar_master_recovery_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH,
    BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED,
    BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT,
    BLOCKED_GF256_QUORUM_EXCEEDED_3_CHUNKS,
    BLOCKED_INVALID_FX3RCPT1_RECEIPT,
    BLOCKED_MISSING_16_SURFACE_COLD_BACKUP,
    BLOCKED_MISSING_CRITICAL_CAL_FILES,
    BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION,
    BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN,
    BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_22_PILLAR_COUNT,
    MASTER_22_PILLAR_IDS,
    MASTER_22_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P166_DONOR_FX3_BACKUP_BIN_RELPATH,
    P166_DONOR_FX3_LOADER_NOR_RELPATH,
    P166_DONOR_FX3_MOUNT_RELPATH,
    P166_DONOR_FX3_P1_205_RELPATH,
    P166_DONOR_FX3_PARTINF_RELPATH,
    P166_FX3RCPT1_BYTES,
    P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
    P166_FX3RCPT1_MAGIC,
    P166_FX3_MODEL_ID,
    P166_GF256_MAX_CHUNKS_HEALABLE,
    P166_GF256_POLYNOMIAL,
    P166_MANDATORY_16_SURFACES,
    P166_MANDATORY_P18_LENS_FILES,
    P166_MANDATORY_P2_SETTING_FILES,
    P166_PILLAR_A_SCENARIO_IDS,
    P166_PILLAR_B_SCENARIO_IDS,
    P166_STATUS_FAIL_22OF22_AGGREGATOR,
    P166_STATUS_VERIFIED_22OF22_AGGREGATOR,
    P166_STATUS_VERIFIED_PILLAR_A,
    P166_STATUS_VERIFIED_PILLAR_B,
    P166_STATUS_VERIFIED_SUITE,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE166_SCHEMA,
    PHASE166_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    ColdBackupMediaCopy,
    Master22PillarRecoveryReport,
    build_fx3rcpt1_receipt,
    build_synthetic_16_surface_chunks,
    build_synthetic_dual_media_cold_backup,
    encode_16_surface_gf256_archive,
    evaluate_22pillar_recovery_master,
    inspect_phase166_donors_readonly,
    parse_fx3rcpt1_receipt,
    run_pillar22_a_dual_media_6_scenario_suite,
    run_pillar22_b_gf256_scrub_6_scenario_suite,
    run_pillar22_standalone_suite,
    scrub_and_rehearse_dual_media_bitrot_recovery,
    verify_22pillar_recovery_suite,
    verify_dual_media_cold_backup_vault,
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


class TestRealHw22PillarMasterRecoveryVerifier(unittest.TestCase):
    _cached_clean_master: Master22PillarRecoveryReport | None = None
    _cached_default_master: Master22PillarRecoveryReport | None = None

    @classmethod
    def _clean_master(cls) -> Master22PillarRecoveryReport:
        if cls._cached_clean_master is None:
            cls._cached_clean_master = verify_22pillar_recovery_suite(force_clean_room=True)
        return cls._cached_clean_master

    @classmethod
    def _default_master(cls) -> Master22PillarRecoveryReport:
        if cls._cached_default_master is None:
            cls._cached_default_master = verify_22pillar_recovery_suite()
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
        self.assertIn("realhw_22pillar_master_recovery_verifier", fx3_recovery.__all__)
        self.assertIn("verify_22pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("evaluate_22pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("run_pillar22_standalone_suite", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.verify_22pillar_recovery_suite, verify_22pillar_recovery_suite)
        self.assertIs(fx3_recovery.evaluate_22pillar_recovery_master, evaluate_22pillar_recovery_master)
        # Ensure Phase 155/160 exports remain intact and unshadowed
        self.assertEqual(fx3_recovery.PHASE160_SCHEMA, "fx3-realhw-bootrom-el3-and-ufu-stock-reflash-verifier-v1")
        self.assertEqual(fx3_recovery.PHASE166_SCHEMA, PHASE166_SCHEMA)
        self.assertEqual(fx3_recovery.PHASE166_VERSION, PHASE166_VERSION)

    def test_03_master_22_pillar_registry_integrity(self) -> None:
        self.assertEqual(MASTER_22_PILLAR_COUNT, 22)
        self.assertEqual(len(MASTER_22_PILLAR_SPECS), 22)
        self.assertEqual([s[0] for s in MASTER_22_PILLAR_SPECS], list(range(1, 23)))
        self.assertEqual(len(set(MASTER_22_PILLAR_IDS)), 22)
        self.assertIn("realhw_service_usb_session_and_libjit_elf_hardener", MASTER_22_PILLAR_IDS)
        self.assertIn("realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier", MASTER_22_PILLAR_IDS)
        self.assertIn("realhw_uart_460800_post_triage_and_isp_guard", MASTER_22_PILLAR_IDS)
        self.assertIn("realhw_bootrom_el3_and_ufu_stock_reflash_verifier", MASTER_22_PILLAR_IDS)
        self.assertEqual(MASTER_22_PILLAR_IDS[-1], "realhw_22pillar_master_recovery_verifier")

    def test_04_donor_inspection_clean_room_forced(self) -> None:
        snap = inspect_phase166_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(len(snap.artifacts), 7)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.partinf_partition_count, 30)
        self.assertTrue(snap.mount_entries_verified)
        self.assertTrue(snap.loader_nor_el3_ok)
        self.assertTrue(snap.backup_bin_bk4_fx3_ok)
        self.assertTrue(snap.nflasha15_ext2_magic_ok)
        _assert_json_has_no_raw_bytes(snap.to_dict())

    def test_05_donor_inspection_env_clean_room_parity(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap_a = inspect_phase166_donors_readonly()
            snap_b = inspect_phase166_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_a.snapshot_sha256, snap_b.snapshot_sha256)
        self.assertEqual(snap_a.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_inspection_o_rdonly_flag_and_local_mode(self) -> None:
        orig_open = os.open
        seen_flags: list[int] = []

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)

        has_local = (
            os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") != "1"
            and resolve_donor_path(P166_DONOR_FX3_PARTINF_RELPATH, require_file=True) is not None
        )
        with mock.patch("fx3_recovery.realhw_22pillar_master_recovery_verifier.os.open", side_effect=_spy_open):
            snap = inspect_phase166_donors_readonly()
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if has_local:
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertGreaterEqual(len(seen_flags), 7)
            for flg in seen_flags:
                self.assertEqual(flg & os.O_ACCMODE, os.O_RDONLY)
                self.assertNotEqual(flg & os.O_NOFOLLOW, 0)
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_pinned_digests_valid_hex(self) -> None:
        snap = inspect_phase166_donors_readonly()
        self.assertTrue(snap.all_passed)
        for art in snap.artifacts:
            self.assertTrue(art.passed)
            self.assertEqual(len(art.sha256_digest), 64)
            int(art.sha256_digest, 16)
            self.assertGreater(art.byte_length, 0)

    def test_08_donor_fallback_when_all_donors_absent(self) -> None:
        with mock.patch(
            "fx3_recovery.realhw_22pillar_master_recovery_verifier.resolve_donor_path",
            return_value=None,
        ):
            snap = inspect_phase166_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_09_donor_json_zero_raw_firmware_bytes(self) -> None:
        for mode in (True, False):
            snap = inspect_phase166_donors_readonly(force_clean_room=mode)
            text = _assert_json_has_no_raw_bytes(snap.to_dict())
            self.assertNotIn("BYTEARRAY", text.upper())
            self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_10_mandatory_16_surfaces_and_cal_file_constants(self) -> None:
        self.assertEqual(len(P166_MANDATORY_16_SURFACES), 16)
        self.assertEqual(
            P166_MANDATORY_P2_SETTING_FILES,
            ("psd.bin", "defdet.bin", "Backup.bin"),
        )
        self.assertEqual(P166_MANDATORY_P18_LENS_FILES, ("LENSFILE.BIN",))
        self.assertEqual(P166_GF256_POLYNOMIAL, 0x11D)
        self.assertEqual(P166_GF256_MAX_CHUNKS_HEALABLE, 2)

    # ------------------------------------------------------------------
    # Group A (11..24): FX3RCPT1 528B & Dual-Media Tier-0 Vault Gate
    # ------------------------------------------------------------------

    def test_11_fx3rcpt1_build_and_parse_roundtrip(self) -> None:
        b = "a" * 64
        c = "b" * 64
        m = "c" * 64
        p2 = "d" * 64
        p18 = "e" * 64
        raw = build_fx3rcpt1_receipt(
            body_serial_sha256=b,
            emmc_cid_sha256=c,
            manifest_sha256=m,
            p2_cal_bundle_sha256=p2,
            p18_lensfile_sha256=p18,
        )
        self.assertEqual(len(raw), P166_FX3RCPT1_BYTES)
        self.assertEqual(len(raw), 528)
        self.assertTrue(raw.startswith(P166_FX3RCPT1_MAGIC))
        parsed = parse_fx3rcpt1_receipt(raw)
        self.assertTrue(parsed.valid)
        self.assertTrue(parsed.crc32_valid)
        self.assertEqual(parsed.model_id, P166_FX3_MODEL_ID)
        self.assertEqual(parsed.surface_count, 16)
        self.assertEqual(parsed.flags, P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY)
        self.assertEqual(parsed.body_serial_sha256, b)
        self.assertEqual(parsed.emmc_cid_sha256, c)
        self.assertEqual(parsed.manifest_sha256, m)
        self.assertEqual(parsed.p2_cal_bundle_sha256, p2)
        self.assertEqual(parsed.p18_lensfile_sha256, p18)

    def test_12_fx3rcpt1_rejects_bad_length_magic_and_crc(self) -> None:
        raw = build_fx3rcpt1_receipt(
            body_serial_sha256="1" * 64,
            emmc_cid_sha256="2" * 64,
            manifest_sha256="3" * 64,
            p2_cal_bundle_sha256="4" * 64,
            p18_lensfile_sha256="5" * 64,
        )
        short = parse_fx3rcpt1_receipt(raw[:500])
        self.assertFalse(short.valid)

        bad_magic = b"BADRCPT1" + raw[8:]
        self.assertFalse(parse_fx3rcpt1_receipt(bad_magic).valid)

        bad_crc = bytearray(raw)
        bad_crc[32] ^= 0x01
        res_crc = parse_fx3rcpt1_receipt(bytes(bad_crc))
        self.assertFalse(res_crc.valid)
        self.assertFalse(res_crc.crc32_valid)

    def test_13_dual_media_happy_path_nvme_plus_ssd(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test13")
        rep = verify_dual_media_cold_backup_vault(copy_a, copy_b)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P166_STATUS_VERIFIED_PILLAR_A)
        self.assertTrue(rep.stage_a_staging_permitted)
        self.assertTrue(rep.distinct_physical_media)
        self.assertTrue(rep.all_16_surfaces_present)
        self.assertTrue(rep.dual_media_manifest_match)
        self.assertTrue(rep.p2_setting_files_verified)
        self.assertTrue(rep.p18_lensfile_verified)
        self.assertTrue(rep.fx3rcpt1_valid)
        self.assertTrue(rep.identity_bound_ok)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_14_dual_media_blocks_single_medium_only(self) -> None:
        copy_a, _, _ = build_synthetic_dual_media_cold_backup(body_tag="test14")
        rep = verify_dual_media_cold_backup_vault(copy_a, None)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.stage_a_staging_permitted)
        self.assertIn(BLOCKED_SINGLE_MEDIA_COLD_BACKUP_INSUFFICIENT, rep.blocked_codes)

    def test_15_dual_media_blocks_same_device_id(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test15")
        same_dev = ColdBackupMediaCopy(**{**asdict(copy_b), "device_id": copy_a.device_id})
        rep = verify_dual_media_cold_backup_vault(copy_a, same_dev)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.stage_a_staging_permitted)
        self.assertIn(BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN, rep.blocked_codes)

    def test_16_dual_media_blocks_same_hardware_uuid_or_mount(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test16")
        same_uuid = ColdBackupMediaCopy(**{**asdict(copy_b), "hardware_uuid": copy_a.hardware_uuid})
        rep_u = verify_dual_media_cold_backup_vault(copy_a, same_uuid)
        self.assertFalse(rep_u.passed)
        self.assertIn(BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN, rep_u.blocked_codes)

        same_mnt = ColdBackupMediaCopy(**{**asdict(copy_b), "mount_point": copy_a.mount_point})
        rep_m = verify_dual_media_cold_backup_vault(copy_a, same_mnt)
        self.assertFalse(rep_m.passed)
        self.assertIn(BLOCKED_SAME_PHYSICAL_MEDIUM_FORBIDDEN, rep_m.blocked_codes)

    def test_17_dual_media_blocks_missing_surface_from_16(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test17")
        s_less = dict(copy_a.surface_sha256s)
        s_less.pop("spi_nor_mtd0ro")
        missing_a = ColdBackupMediaCopy(**{**asdict(copy_a), "surface_sha256s": s_less})
        rep = verify_dual_media_cold_backup_vault(missing_a, copy_b)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.stage_a_staging_permitted)
        self.assertIn(BLOCKED_MISSING_16_SURFACE_COLD_BACKUP, rep.blocked_codes)

    def test_18_dual_media_blocks_missing_p2_setting_files(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test18")
        for missing_name in P166_MANDATORY_P2_SETTING_FILES:
            p2_partial = {k: v for k, v in copy_a.p2_setting_files.items() if k != missing_name}
            bad_a = ColdBackupMediaCopy(**{**asdict(copy_a), "p2_setting_files": p2_partial})
            rep = verify_dual_media_cold_backup_vault(bad_a, copy_b)
            self.assertFalse(rep.passed)
            self.assertIn(BLOCKED_MISSING_CRITICAL_CAL_FILES, rep.blocked_codes)

    def test_19_dual_media_blocks_missing_p18_lensfile(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test19")
        bad_a = ColdBackupMediaCopy(**{**asdict(copy_a), "p18_lens_files": {}})
        rep = verify_dual_media_cold_backup_vault(bad_a, copy_b)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.stage_a_staging_permitted)
        self.assertIn(BLOCKED_MISSING_CRITICAL_CAL_FILES, rep.blocked_codes)

    def test_20_dual_media_blocks_manifest_drift_between_media(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test20")
        drifted = dict(copy_b.surface_sha256s)
        drifted["p2"] = "f" * 64
        bad_b = ColdBackupMediaCopy(**{**asdict(copy_b), "surface_sha256s": drifted})
        rep = verify_dual_media_cold_backup_vault(copy_a, bad_b)
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_DUAL_MEDIA_MANIFEST_DRIFT, rep.blocked_codes)

    def test_21_dual_media_blocks_cross_camera_identity_mismatch(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test21")
        other_cam = ColdBackupMediaCopy(**{**asdict(copy_b), "emmc_cid_sha256": "9" * 64})
        rep = verify_dual_media_cold_backup_vault(copy_a, other_cam)
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH, rep.blocked_codes)

        rep2 = verify_dual_media_cold_backup_vault(
            copy_a,
            copy_b,
            expected_body_serial_sha256="8" * 64,
        )
        self.assertFalse(rep2.passed)
        self.assertIn(BLOCKED_CROSS_CAMERA_VAULT_IDENTITY_MISMATCH, rep2.blocked_codes)

    def test_22_dual_media_blocks_tampered_fx3rcpt1(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test22")
        bad_hex = bytearray.fromhex(copy_a.fx3rcpt1_receipt_hex)
        bad_hex[40] ^= 0x55
        bad_a = ColdBackupMediaCopy(**{**asdict(copy_a), "fx3rcpt1_receipt_hex": bytes(bad_hex).hex()})
        rep = verify_dual_media_cold_backup_vault(bad_a, copy_b)
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_INVALID_FX3RCPT1_RECEIPT, rep.blocked_codes)

    def test_23_stage_a_staging_not_permitted_unless_requested_and_passed(self) -> None:
        copy_a, copy_b, _ = build_synthetic_dual_media_cold_backup(body_tag="test23")
        rep = verify_dual_media_cold_backup_vault(copy_a, copy_b, stage_a_staging_requested=False)
        self.assertTrue(rep.passed)
        self.assertFalse(rep.stage_a_staging_permitted)

    def test_24_pillar22_a_6_scenario_suite_passes(self) -> None:
        res = run_pillar22_a_dual_media_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P166_STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P166_PILLAR_A_SCENARIO_IDS)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # Group B (25..36): GF(256) (0x11d) Scrub & 16/16 Pre-Restore Dry-Run
    # ------------------------------------------------------------------

    def test_25_encode_16_surface_gf256_archive_requires_all_16(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test25")
        archive = encode_16_surface_gf256_archive(chunks)
        self.assertEqual(archive.surface_order, P166_MANDATORY_16_SURFACES)
        self.assertEqual(len(archive.shards_bytes), 16)
        self.assertEqual(len(archive.p_parity), archive.stripe_bytes)
        self.assertEqual(len(archive.q_parity), archive.stripe_bytes)

        partial = dict(chunks)
        partial.pop("p18")
        with self.assertRaises(ValueError):
            encode_16_surface_gf256_archive(partial)

    def test_26_zero_bitrot_clean_16of16_prerestore_dryrun(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test26")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(archive)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P166_STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(rep.gf256_polynomial_hex, "0x11d")
        self.assertEqual(rep.corrupted_chunk_count, 0)
        self.assertEqual(rep.surfaces_verified_count, 16)
        self.assertTrue(rep.prerestore_16of16_exact)
        self.assertEqual(rep.reconstructed_manifest_sha256, rep.archive_manifest_sha256)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_27_single_chunk_silent_bitrot_pure_gf256_syndrome_heal(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test27")
        archive = encode_16_surface_gf256_archive(chunks)
        for target in ("p18", "p2", "spi_nor_mtd0ro"):
            rep = scrub_and_rehearse_dual_media_bitrot_recovery(
                archive,
                corrupt_chunks=(target,),
                use_pure_syndrome_for_single_bitrot=True,
            )
            self.assertTrue(rep.passed)
            self.assertEqual(rep.repair_mode, "SYNDROME_SINGLE_CORRUPT_HEAL")
            self.assertIn(target, rep.healed_chunks)
            self.assertTrue(rep.prerestore_16of16_exact)
            self.assertEqual(rep.surfaces_verified_count, 16)

    def test_28_two_chunk_simultaneous_bitrot_gf256_pq_heal(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test28")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("p2", "spi_nor_mtd0ro"),
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.corrupted_chunk_count, 2)
        self.assertEqual(set(rep.healed_chunks), {"p2", "spi_nor_mtd0ro"})
        self.assertTrue(rep.prerestore_16of16_exact)
        self.assertEqual(rep.reconstructed_manifest_sha256, rep.archive_manifest_sha256)

    def test_29_two_chunk_adjacent_partitions_p1_and_p15_heal(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test29")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("p1", "p15"),
            bitrot_pattern=0x5A,
        )
        self.assertTrue(rep.passed)
        self.assertEqual(set(rep.healed_chunks), {"p1", "p15"})
        self.assertTrue(rep.prerestore_16of16_exact)

    def test_30_data_plus_q_parity_simultaneous_bitrot_heal(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test30")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("p15", "Q"),
        )
        self.assertTrue(rep.passed)
        self.assertIn("p15", rep.healed_chunks)
        self.assertIn("Q", rep.healed_chunks)
        self.assertTrue(rep.prerestore_16of16_exact)

    def test_31_data_plus_p_parity_simultaneous_bitrot_heal(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test31")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("sector0", "P"),
        )
        self.assertTrue(rep.passed)
        self.assertIn("sector0", rep.healed_chunks)
        self.assertIn("P", rep.healed_chunks)
        self.assertTrue(rep.prerestore_16of16_exact)

    def test_32_p_and_q_both_corrupted_still_verifies_16_data_surfaces(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test32")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("P", "Q"),
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.prerestore_16of16_exact)
        self.assertEqual(rep.surfaces_verified_count, 16)

    def test_33_three_chunk_quorum_loss_fails_closed(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test33")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            corrupt_chunks=("p2", "p15", "p18"),
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.prerestore_16of16_exact)
        self.assertIn(BLOCKED_GF256_QUORUM_EXCEEDED_3_CHUNKS, rep.blocked_codes)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_34_cross_domain_surface_mismatch_fails_closed(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test34")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            cross_domain_inject_surface="p15",
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.prerestore_16of16_exact)
        self.assertIn(BLOCKED_CROSS_DOMAIN_RESTORE_OR_WRITE_LOCKED, rep.blocked_codes)

    def test_35_write_unlock_request_rejected_fail_closed(self) -> None:
        chunks, _, _ = build_synthetic_16_surface_chunks(body_tag="test35")
        archive = encode_16_surface_gf256_archive(chunks)
        rep = scrub_and_rehearse_dual_media_bitrot_recovery(
            archive,
            request_persistent_write_unlock=True,
        )
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_SAFETY_POLICY_INVARIANT_VIOLATION, rep.blocked_codes)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)

    def test_36_pillar22_b_6_scenario_suite_passes(self) -> None:
        res = run_pillar22_b_gf256_scrub_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P166_STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P166_PILLAR_B_SCENARIO_IDS)
        self.assertEqual(res.physical_device_writes, 0)

    # ------------------------------------------------------------------
    # Group C (37..44): Standalone Pillar 22 & 22/22 Master Aggregator
    # ------------------------------------------------------------------

    def test_37_pillar22_standalone_suite_clean_room_determinism(self) -> None:
        r1 = run_pillar22_standalone_suite(force_clean_room=True)
        r2 = run_pillar22_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, P166_STATUS_VERIFIED_SUITE)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        _assert_json_has_no_raw_bytes(r1.to_dict())

    def test_38_pillar22_standalone_suite_default_mode(self) -> None:
        r = run_pillar22_standalone_suite()
        self.assertTrue(r.all_passed)
        self.assertEqual(r.status, P166_STATUS_VERIFIED_SUITE)
        self.assertTrue(r.pillar_a_dual_media_6_scenarios.passed)
        self.assertTrue(r.pillar_b_gf256_scrub_6_scenarios.passed)

    def test_39_master_22pillar_clean_room_passes_under_2s(self) -> None:
        rep = self._clean_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P166_STATUS_VERIFIED_22OF22_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 22)
        self.assertEqual(rep.pillars_passed, 22)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, 2.0)
        self.assertTrue(rep.under_2s_budget)
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_22_PILLAR_IDS)
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 23)))
        for p in rep.pillars:
            self.assertTrue(p.passed, f"Pillar {p.pillar_id} failed: {p.errors}")

    def test_40_master_22pillar_default_mode_passes_under_2s(self) -> None:
        rep = self._default_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P166_STATUS_VERIFIED_22OF22_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 22)
        self.assertEqual(rep.pillars_passed, 22)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, 2.0)
        self.assertTrue(rep.under_2s_budget)

    def test_41_master_22pillar_safety_assertions_all_zero_and_false(self) -> None:
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
            self.assertEqual(rep.errors, ())

    def test_42_master_22pillar_clean_room_digest_determinism(self) -> None:
        r1 = self._clean_master()
        r2 = evaluate_22pillar_recovery_master(force_clean_room=True)
        self.assertEqual(r1.master_22pillar_sha256, r2.master_22pillar_sha256)
        self.assertEqual(len(r1.master_22pillar_sha256), 64)
        _assert_json_has_no_raw_bytes(r1.to_dict())

    def test_43_master_22pillar_fault_injection_fails_closed(self) -> None:
        target = "realhw_bootrom_el3_and_ufu_stock_reflash_verifier"
        rep = evaluate_22pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=target,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P166_STATUS_FAIL_22OF22_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 22)
        self.assertEqual(rep.pillars_passed, 21)
        self.assertEqual(rep.failed_pillars, (target,))
        p21 = [p for p in rep.pillars if p.pillar_id == target][0]
        self.assertFalse(p21.passed)
        self.assertIn(f"FAULT_INJECTED:{target}", p21.errors)

    def test_44_master_22pillar_unknown_fault_target_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_22pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar",
            )

    # ------------------------------------------------------------------
    # Group D (45..50): CLI Integration & Backward Compatibility
    # ------------------------------------------------------------------

    def test_45_cli_verify_22pillar_recovery_summary_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-22pillar-recovery", "--clean-room"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue().strip()
        self.assertIn("status=VERIFIED_22OF22_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=22/22", out)
        self.assertIn("under_2s_budget=True", out)
        self.assertIn("otp_fuse_touches=0", out)
        self.assertIn("rpmb_counter_increments=0", out)
        self.assertIn("passive_tx_bytes_emitted=0", out)
        self.assertIn("physical_usb_packets_emitted=0", out)
        self.assertIn("el3_payload_transmit_authorized=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

    def test_46_cli_verify_22pillar_recovery_json_and_out_dir(self) -> None:
        out_dir = ROOT / "work" / "_tests" / "test_p166_cli_out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-22pillar-recovery", "--clean-room", "--json", "--out", str(out_dir)],
            ):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["pillar_count"], 22)
            self.assertEqual(payload["pillars_passed"], 22)
            self.assertTrue(payload["all_passed"])
            self.assertTrue(payload["under_2s_budget"])
            self.assertEqual(len(payload["pillars"]), 22)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            _assert_json_has_no_raw_bytes(payload)

            written = out_dir / "22pillar-recovery-master-report.json"
            self.assertTrue(written.is_file())
            written_obj = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(written_obj["master_22pillar_sha256"], payload["master_22pillar_sha256"])
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir)

    def test_47_cli_verify_22pillar_recovery_returns_2_on_failure(self) -> None:
        failed_rep = evaluate_22pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="macos_usb_transport_guard",
        )
        buf = io.StringIO()
        with mock.patch.object(
            fx3_cli,
            "verify_22pillar_recovery_suite",
            return_value=failed_rep,
        ):
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-22pillar-recovery", "--clean-room"]):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        self.assertIn("all_passed=False", buf.getvalue())
        self.assertIn("pillars=21/22", buf.getvalue())

    def test_48_cli_verify_all_recovery_with_phase166_clean_room_22_of_22(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-all-recovery",
                "--with-phase94",
                "--with-phase101",
                "--with-phase106",
                "--with-phase113",
                "--with-phase119",
                "--with-phase124",
                "--with-phase126",
                "--with-phase134",
                "--with-phase138",
                "--with-phase139",
                "--with-phase144",
                "--with-phase151",
                "--with-phase155",
                "--with-phase160",
                "--with-phase166",
                "--clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["pillar_count"], 22)
        self.assertEqual(payload["pillars_passed"], 22)
        self.assertTrue(payload["all_passed"])
        self.assertIn("phase166_pillar22_dual_media_cold_backup_gf256", payload)

    def test_49_cli_verify_all_recovery_default_backward_compat_7_of_7(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["pillar_count"], 7)
        self.assertEqual(payload["pillars_passed"], 7)
        self.assertTrue(payload["all_passed"])

    def test_50_dual_mode_env_clean_room_via_cli(self) -> None:
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-22pillar-recovery", "--json"]):
                with redirect_stdout(buf):
                    rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["pillars_passed"], 22)


if __name__ == "__main__":
    unittest.main()
