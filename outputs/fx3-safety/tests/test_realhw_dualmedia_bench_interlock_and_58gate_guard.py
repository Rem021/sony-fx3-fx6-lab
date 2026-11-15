"""Fast dual-mode unit tests for Phase 173 — Real-Hardware Main Track Part 16:
Gate G57 (Dual-Media Independent Tier-0 Cold-Backup Device-ID Separation,
16/16 SHA-256 Parity & `GF(256)` `0x11d` RAID-6 Bit-Rot Scrub Guard),
Gate G58 (Two-Step Explicit Human Bench Authorization, Pre-Install
`NP-FZ100 >= 80%` / `>= 7400 mV`, `op=0xFF` RAM Canary Receipt, Dual-Media
`FX3RCPT1` Match & Zero-Auto-Flash Interlock), and
Unified 58-Gate Master Safety Preflight (`G01..G58` / `verify-58-gates`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_c2pa_tc_gyro_and_56gate_guard import (
    STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY,
    STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED,
    evaluate_56gate_preflight,
)
from fx3_safety.realhw_cxd90058_sabin_seal_and_54gate_guard import (
    CANONICAL_16_STORAGE_SURFACES,
    CANONICAL_16_SURFACE_COUNT,
)
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    ALLOWED_DUAL_MEDIA_ROLES,
    DEFAULT_MEDIA_A_ROLE,
    DEFAULT_MEDIA_A_ST_DEV,
    DEFAULT_MEDIA_B_ROLE,
    DEFAULT_MEDIA_B_ST_DEV,
    DEFAULT_SYNTHETIC_CAMERA_CID_SHA256,
    DEFAULT_SYNTHETIC_FX3RCPT1_SHA256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_ID_INT,
    FX3_MODEL_NAME,
    FX3RCPT1_MAGIC,
    FX3RCPT1_PACKET_BYTES,
    FX3S0OK_HEADER_MAGIC,
    FX3S0OK_PACKET_BYTES,
    G57_GATE_CODE,
    G57_GATE_ID,
    G58_GATE_CODE,
    G58_GATE_ID,
    GF256_GENERATOR,
    GF256_MAX_RECOVERABLE_ERASURES,
    GF256_PRIMITIVE_POLY,
    OP_FF_CANARY_OPCODE,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PINNED_PHASE173_DONOR_SPECS,
    PREFLASH_BATTERY_MODEL,
    PREFLASH_MAX_BATTERY_MV,
    PREFLASH_MIN_BATTERY_MV,
    PREFLASH_MIN_BATTERY_SOC_PCT,
    PREFLASH_MIN_USBPD_CONTRACT_MW,
    REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA,
    REALHW_DUALMEDIA_BENCH_58GATE_VERSION,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH,
    STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS,
    STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV,
    STATUS_BLOCKED_G57_TELEMETRY_INVALID,
    STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
    STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD,
    STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED,
    STATUS_BLOCKED_G58_TELEMETRY_INVALID,
    STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G57,
    STATUS_VERIFIED_G58,
    STATUS_VERIFIED_SAFE,
    audit_phase173_donor_contracts,
    build_synthetic_16_surface_chunks,
    default_verified_16_surface_hashes,
    encode_gf256_pq_parity,
    evaluate_58_master_safety_gates,
    evaluate_58gate_preflight,
    evaluate_g57_dualmedia_vault,
    evaluate_g58_bench_interlock,
    gf256_div,
    gf256_inv,
    gf256_mul,
    main as module_cli_main,
    recover_gf256_pq_chunks,
    validate_dual_media_16_surface_sha256_parity,
    validate_dual_media_device_id_separation,
    validate_gf256_bitrot_scrub_guard,
    verify_dual_media_vault_and_gf256_scrub_guard,
    verify_two_step_bench_interlock_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwDualMediaBenchInterlockAnd58GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(
            REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA,
            "fx3-realhw-dualmedia-bench-58gate-preflight-v1",
        )
        self.assertEqual(REALHW_DUALMEDIA_BENCH_58GATE_VERSION, "1.0.0")
        self.assertEqual(FX3_MODEL_ID_INT, 0x91030080)
        self.assertEqual(FX3_MODEL_ID_HEX, "0x91030080")
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(GF256_PRIMITIVE_POLY, 0x11D)
        self.assertEqual(GF256_GENERATOR, 0x02)
        self.assertEqual(GF256_MAX_RECOVERABLE_ERASURES, 2)
        self.assertEqual(PREFLASH_BATTERY_MODEL, "NP-FZ100")
        self.assertEqual(PREFLASH_MIN_BATTERY_SOC_PCT, 80.0)
        self.assertEqual(PREFLASH_MIN_BATTERY_MV, 7400)
        self.assertEqual(PREFLASH_MAX_BATTERY_MV, 8500)
        self.assertEqual(PREFLASH_MIN_USBPD_CONTRACT_MW, 27_000)
        self.assertEqual(OP_FF_CANARY_OPCODE, 0xFF)
        self.assertEqual(FX3S0OK_HEADER_MAGIC, "FX3S0OK")
        self.assertEqual(FX3S0OK_PACKET_BYTES, 528)
        self.assertEqual(FX3RCPT1_MAGIC, "FX3RCPT1")
        self.assertEqual(FX3RCPT1_PACKET_BYTES, 528)
        self.assertEqual(STATUS_SAFE, "SAFE")

        for sym in (
            "ALLOWED_DUAL_MEDIA_ROLES",
            "DEFAULT_MEDIA_A_ROLE",
            "DEFAULT_MEDIA_A_ST_DEV",
            "DEFAULT_MEDIA_B_ROLE",
            "DEFAULT_MEDIA_B_ST_DEV",
            "DEFAULT_SYNTHETIC_FX3RCPT1_SHA256",
            "EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE",
            "FX3RCPT1_MAGIC",
            "FX3RCPT1_PACKET_BYTES",
            "G57_GATE_CODE",
            "G57_GATE_ID",
            "G58_GATE_CODE",
            "G58_GATE_ID",
            "GF256_EXP",
            "GF256_GENERATOR",
            "GF256_INV",
            "GF256_LOG",
            "GF256_MAX_RECOVERABLE_ERASURES",
            "GF256_MUL_TABLES",
            "GF256_PRIMITIVE_POLY",
            "PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED",
            "PINNED_PHASE173_DONOR_SPECS",
            "PREFLASH_BATTERY_MODEL",
            "PREFLASH_MAX_BATTERY_MV",
            "PREFLASH_MIN_BATTERY_MV",
            "PREFLASH_MIN_BATTERY_SOC_PCT",
            "PREFLASH_MIN_USBPD_CONTRACT_MW",
            "REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA",
            "REALHW_DUALMEDIA_BENCH_58GATE_VERSION",
            "STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH",
            "STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS",
            "STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV",
            "STATUS_BLOCKED_G57_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION",
            "STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD",
            "STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED",
            "STATUS_BLOCKED_G58_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING",
            "STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY",
            "STATUS_VERIFIED_G57",
            "STATUS_VERIFIED_G58",
            "DualMediaVaultGuardResult",
            "G57DualMediaVaultResult",
            "G58BenchInterlockResult",
            "Gf256RecoveryResult",
            "Master58GateReport",
            "Phase173DonorAuditResult",
            "TwoStepBenchInterlockGuardResult",
            "audit_phase173_donor_contracts",
            "build_synthetic_16_surface_chunks",
            "default_verified_16_surface_hashes",
            "encode_gf256_pq_parity",
            "evaluate_58_master_safety_gates",
            "evaluate_58gate_preflight",
            "evaluate_g57_dualmedia_vault",
            "evaluate_g58_bench_interlock",
            "gf256_div",
            "gf256_inv",
            "gf256_mul",
            "realhw_dualmedia_bench_interlock_and_58gate_guard",
            "recover_gf256_pq_chunks",
            "validate_dual_media_16_surface_sha256_parity",
            "validate_dual_media_device_id_separation",
            "validate_gf256_bitrot_scrub_guard",
            "verify_dual_media_vault_and_gf256_scrub_guard",
            "verify_two_step_bench_interlock_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing package export: {sym}")

        # Prior colliding constants must remain untouched
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.MEDIA_TYPE_CFEXPRESS_A, "CFEXPRESS_TYPE_A")

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        clean_res = audit_phase173_donor_contracts(force_clean_room=True)
        self.assertTrue(clean_res.valid)
        self.assertEqual(clean_res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(clean_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_res.access_mode, "O_RDONLY")
        self.assertEqual(clean_res.files_inspected, 0)
        self.assertEqual(
            len(clean_res.checked_markers), len(PINNED_PHASE173_DONOR_SPECS)
        )
        self.assertEqual(clean_res.missing_markers, ())
        self.assertTrue(clean_res.fx3_contracts_verified)

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_res = audit_phase173_donor_contracts(
                work_root=Path(tmpdir), force_clean_room=False
            )
            self.assertTrue(missing_res.valid)
            self.assertEqual(missing_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        orig_open = os.open
        seen_flags: list[int] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with patch(
            "fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard.os.open",
            side_effect=spy_open,
        ):
            auto_res = audit_phase173_donor_contracts(repo_root=DEFAULT_REPO_ROOT)

        self.assertTrue(auto_res.valid)
        self.assertEqual(auto_res.access_mode, "O_RDONLY")
        if auto_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(
                auto_res.files_inspected, len(PINNED_PHASE173_DONOR_SPECS)
            )
            self.assertEqual(len(seen_flags), len(PINNED_PHASE173_DONOR_SPECS))
            for fl in seen_flags:
                self.assertEqual(fl & 3, os.O_RDONLY)

        dumped = json.dumps(auto_res.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)
        self.assertNotIn("b'BK4", dumped)

    def test_03_donor_audit_fails_closed_on_tampered_sha_or_missing_marker(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, toks, _lbl) in (
                PINNED_PHASE173_DONOR_SPECS.items()
            ):
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(t + b"\x00" for t in toks)
                if len(payload) < size:
                    payload = payload + b"\x00" * (size - len(payload))
                p.write_bytes(payload[:size])

            bad_res = audit_phase173_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(bad_res.valid)
            self.assertEqual(bad_res.status, STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY)
            self.assertFalse(bad_res.fx3_contracts_verified)
            self.assertGreater(len(bad_res.errors), 0)

    def test_04_donor_audit_fails_when_marker_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, _toks, _lbl) in (
                PINNED_PHASE173_DONOR_SPECS.items()
            ):
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * min(size, 64))

            bad_res = audit_phase173_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(bad_res.valid)
            self.assertEqual(bad_res.status, STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY)
            self.assertEqual(
                len(bad_res.missing_markers), len(PINNED_PHASE173_DONOR_SPECS)
            )

    # --- 2. Pure-Python GF(256) (0x11d) RAID-6 Arithmetic & Scrub Recovery ---

    def test_05_gf256_field_arithmetic_identities(self) -> None:
        self.assertEqual(gf256_mul(0, 0xA7), 0)
        self.assertEqual(gf256_mul(0xA7, 0), 0)
        self.assertEqual(gf256_mul(1, 0xA7), 0xA7)
        self.assertEqual(gf256_mul(0x80, 0x02), 0x1D)
        for val in (1, 2, 3, 17, 99, 255):
            inv_v = gf256_inv(val)
            self.assertEqual(gf256_mul(val, inv_v), 1)
            self.assertEqual(gf256_div(val, val), 1)
            self.assertEqual(gf256_div(0x7C, val), gf256_mul(0x7C, inv_v))
        with self.assertRaises(ZeroDivisionError):
            gf256_inv(0)
        with self.assertRaises(ZeroDivisionError):
            gf256_div(1, 0)

    def test_06_gf256_pq_zero_loss_clean_scrub_passes(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(128)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]
        rec, healed, p_out, q_out = recover_gf256_pq_chunks(
            chunks, p_chunk, q_chunk, expected_sha256s=expected
        )
        self.assertTrue(rec.valid)
        self.assertEqual(rec.primitive_poly_hex, "0x11d")
        self.assertEqual(rec.data_chunk_count, 16)
        self.assertEqual(rec.stripe_bytes, 128)
        self.assertEqual(rec.corrupted_indices, ())
        self.assertEqual(rec.healed_indices, ())
        self.assertFalse(rec.p_repaired)
        self.assertFalse(rec.q_repaired)
        self.assertEqual(rec.unrecoverable_chunk_count, 0)
        self.assertTrue(rec.syndrome_zero_after_heal)
        self.assertEqual(healed, chunks)
        self.assertEqual(p_out, p_chunk)
        self.assertEqual(q_out, q_chunk)

    def test_07_gf256_pq_heals_silent_single_shard_bitrot_without_sha(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(128)
        # Silent single-data-chunk bit-rot localized purely by S1/S0 == g^x
        rot_chunks = list(chunks)
        bad = bytearray(rot_chunks[7])
        bad[0] ^= 0xFF
        bad[63] ^= 0x3C
        rot_chunks[7] = bytes(bad)

        rec_d, healed_d, _, _ = recover_gf256_pq_chunks(rot_chunks, p_chunk, q_chunk)
        self.assertTrue(rec_d.valid)
        self.assertEqual(rec_d.healed_indices, (7,))
        self.assertEqual(rec_d.unrecoverable_chunk_count, 0)
        self.assertTrue(rec_d.syndrome_zero_after_heal)
        self.assertEqual(healed_d, chunks)

        # Silent bit-rot in P alone
        bad_p = bytearray(p_chunk)
        bad_p[12] ^= 0x81
        rec_p, _, p_healed, _ = recover_gf256_pq_chunks(chunks, bytes(bad_p), q_chunk)
        self.assertTrue(rec_p.valid)
        self.assertTrue(rec_p.p_repaired)
        self.assertEqual(p_healed, p_chunk)

        # Silent bit-rot in Q alone
        bad_q = bytearray(q_chunk)
        bad_q[99] ^= 0x19
        rec_q, _, _, q_healed = recover_gf256_pq_chunks(chunks, p_chunk, bytes(bad_q))
        self.assertTrue(rec_q.valid)
        self.assertTrue(rec_q.q_repaired)
        self.assertEqual(q_healed, q_chunk)

    def test_08_gf256_pq_heals_single_data_erasure_with_p_or_q(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(64)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]

        # 1 data erasure + Q missing (recovered via P, Q rebuilt)
        probe_p = list(chunks)
        probe_p[11] = None
        rec1, healed1, _, q1 = recover_gf256_pq_chunks(
            probe_p, p_chunk, None, expected_sha256s=expected
        )
        self.assertTrue(rec1.valid)
        self.assertEqual(rec1.healed_indices, (11,))
        self.assertTrue(rec1.q_repaired)
        self.assertEqual(healed1, chunks)
        self.assertEqual(q1, q_chunk)

        # 1 data erasure + P missing (recovered via Q * g^-x, P rebuilt)
        probe_q = list(chunks)
        probe_q[5] = None
        rec2, healed2, p2, _ = recover_gf256_pq_chunks(
            probe_q, None, q_chunk, expected_sha256s=expected
        )
        self.assertTrue(rec2.valid)
        self.assertEqual(rec2.healed_indices, (5,))
        self.assertTrue(rec2.p_repaired)
        self.assertEqual(healed2, chunks)
        self.assertEqual(p2, p_chunk)

    def test_09_gf256_pq_heals_two_erasures_and_pq_dual_loss(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(96)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]

        # Two simultaneous data shard erasures/bit-rots
        probe = list(chunks)
        probe[0] = None
        probe[15] = b"\x00" * 96  # corrupted and detected via SHA-256
        rec, healed, _, _ = recover_gf256_pq_chunks(
            probe, p_chunk, q_chunk, expected_sha256s=expected
        )
        self.assertTrue(rec.valid)
        self.assertEqual(rec.corrupted_indices, (0, 15))
        self.assertEqual(rec.healed_indices, (0, 15))
        self.assertEqual(rec.unrecoverable_chunk_count, 0)
        self.assertEqual(healed, chunks)

        # Both P and Q missing while all 16 data chunks are intact
        rec_pq, healed_pq, p_re, q_re = recover_gf256_pq_chunks(
            chunks, None, None, expected_sha256s=expected
        )
        self.assertTrue(rec_pq.valid)
        self.assertTrue(rec_pq.p_repaired)
        self.assertTrue(rec_pq.q_repaired)
        self.assertEqual(healed_pq, chunks)
        self.assertEqual(p_re, p_chunk)
        self.assertEqual(q_re, q_chunk)

    def test_10_gf256_pq_fails_closed_on_quorum_loss_and_bad_inputs(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(64)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]

        # 3 erased data shards exceeds P+Q recovery capability
        probe_3 = list(chunks)
        probe_3[1] = None
        probe_3[4] = None
        probe_3[9] = None
        rec3, _, _, _ = recover_gf256_pq_chunks(
            probe_3, p_chunk, q_chunk, expected_sha256s=expected
        )
        self.assertFalse(rec3.valid)
        self.assertEqual(rec3.unrecoverable_chunk_count, 3)
        self.assertFalse(rec3.syndrome_zero_after_heal)

        # 2 data + 1 parity lost = 3 shards lost
        probe_2p = list(chunks)
        probe_2p[2] = None
        probe_2p[8] = None
        rec_2p, _, _, _ = recover_gf256_pq_chunks(
            probe_2p, None, q_chunk, expected_sha256s=expected
        )
        self.assertFalse(rec_2p.valid)
        self.assertEqual(rec_2p.unrecoverable_chunk_count, 3)

        with self.assertRaises(ValueError):
            encode_gf256_pq_parity([])
        with self.assertRaises(ValueError):
            encode_gf256_pq_parity([b"abc", b"ab"])

    # --- 3. Gate G57 — Dual-Media Device-ID Separation & GF(256) Scrub ---

    def test_11_g57_default_passes_with_hard_locked_persistent_write_false(self) -> None:
        res = verify_dual_media_vault_and_gf256_scrub_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G57)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.device_ids_separated)
        self.assertTrue(res.same_filesystem_blocked)
        self.assertEqual(res.expected_surface_count, CANONICAL_16_SURFACE_COUNT)
        self.assertEqual(res.parity_matched_count, 16)
        self.assertTrue(res.dual_media_sha256_parity_ok)
        self.assertEqual(res.gf256_primitive_poly_hex, "0x11d")
        self.assertTrue(res.gf256_pq_verified)
        self.assertTrue(res.scrub_passed)
        self.assertEqual(res.unrecoverable_chunk_count, 0)
        self.assertTrue(res.gf256_scrub_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_12_g57_blocks_same_st_dev_and_same_host_filesystem_dirs(self) -> None:
        r_same = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_st_dev=16_777_220,
            media_b_st_dev=16_777_220,
        )
        self.assertFalse(r_same.valid)
        self.assertEqual(r_same.status, STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV)
        self.assertFalse(r_same.device_ids_separated)

        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = Path(tmpdir) / "media_a"
            dir_b = Path(tmpdir) / "media_b"
            dir_a.mkdir()
            dir_b.mkdir()
            r_paths = verify_dual_media_vault_and_gf256_scrub_guard(
                media_a_path=dir_a,
                media_b_path=dir_b,
            )
            self.assertFalse(r_paths.valid)
            self.assertIn(
                STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV,
                r_paths.violation_codes,
            )
            self.assertEqual(r_paths.media_a_st_dev, r_paths.media_b_st_dev)

    def test_13_g57_blocks_allow_same_fs_same_role_and_symlinks(self) -> None:
        r_allow = verify_dual_media_vault_and_gf256_scrub_guard(
            allow_same_filesystem=True
        )
        self.assertFalse(r_allow.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV,
            r_allow.violation_codes,
        )

        r_role = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_role="MAC_HOST_VAULT",
            media_b_role="MAC_HOST_VAULT",
        )
        self.assertFalse(r_role.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV,
            r_role.violation_codes,
        )

        r_bad_role = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_role="SINGLE_TEMP_RAMDISK",
        )
        self.assertFalse(r_bad_role.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV,
            r_bad_role.violation_codes,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            real_dir = Path(tmpdir) / "real"
            link_dir = Path(tmpdir) / "link"
            real_dir.mkdir()
            link_dir.symlink_to(real_dir)
            ok, _, _ = validate_dual_media_device_id_separation(
                media_a_path=link_dir,
                media_b_st_dev=DEFAULT_MEDIA_B_ST_DEV,
            )
            self.assertFalse(ok)

    def test_14_g57_accepts_all_valid_distinct_role_pairs(self) -> None:
        for role_a in ALLOWED_DUAL_MEDIA_ROLES:
            for role_b in ALLOWED_DUAL_MEDIA_ROLES:
                if role_a == role_b:
                    continue
                res = verify_dual_media_vault_and_gf256_scrub_guard(
                    media_a_role=role_a,
                    media_b_role=role_b,
                    media_a_st_dev=101,
                    media_b_st_dev=202,
                )
                self.assertTrue(res.valid, f"Failed for {role_a} vs {role_b}")

    def test_15_g57_blocks_16_surface_sha256_mismatch_or_missing(self) -> None:
        hashes_a = default_verified_16_surface_hashes()
        hashes_b = dict(hashes_a)
        hashes_b["p5_wbi"] = hashlib.sha256(b"corrupted").hexdigest()

        r_drift = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_surface_hashes=hashes_a,
            media_b_surface_hashes=hashes_b,
        )
        self.assertFalse(r_drift.valid)
        self.assertEqual(r_drift.status, STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH)
        self.assertEqual(r_drift.parity_matched_count, 15)
        self.assertEqual(r_drift.mismatched_surfaces, ("p5_wbi",))

        hashes_zero = dict(hashes_a)
        hashes_zero["p1_updater"] = "0" * 64
        r_zero = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_surface_hashes=hashes_zero,
            media_b_surface_hashes=hashes_zero,
        )
        self.assertFalse(r_zero.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH, r_zero.violation_codes
        )

        hashes_missing = dict(hashes_a)
        del hashes_missing["spi_nor_ro"]
        ok_p, cnt, mis = validate_dual_media_16_surface_sha256_parity(
            media_a_surface_hashes=hashes_a,
            media_b_surface_hashes=hashes_missing,
        )
        self.assertFalse(ok_p)
        self.assertEqual(cnt, 15)
        self.assertEqual(mis, ("spi_nor_ro",))

    def test_16_g57_blocks_gf256_poly_mismatch_scrub_fail_and_unrecoverable(self) -> None:
        r_poly = verify_dual_media_vault_and_gf256_scrub_guard(
            gf256_primitive_poly=0x11B
        )
        self.assertFalse(r_poly.valid)
        self.assertEqual(r_poly.status, STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS)

        r_pq = verify_dual_media_vault_and_gf256_scrub_guard(gf256_pq_verified=False)
        self.assertFalse(r_pq.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS, r_pq.violation_codes
        )

        r_scrub = verify_dual_media_vault_and_gf256_scrub_guard(scrub_passed=False)
        self.assertFalse(r_scrub.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS, r_scrub.violation_codes
        )

        r_unrec = verify_dual_media_vault_and_gf256_scrub_guard(
            unrecoverable_chunk_count=1
        )
        self.assertFalse(r_unrec.valid)
        self.assertEqual(r_unrec.unrecoverable_chunk_count, 1)

        r_quorum = verify_dual_media_vault_and_gf256_scrub_guard(
            corrupted_chunk_count=3
        )
        self.assertFalse(r_quorum.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS, r_quorum.violation_codes
        )

        # Within P+Q budget (<= 2) with zero unrecoverable and passing scrub succeeds
        r_healed = verify_dual_media_vault_and_gf256_scrub_guard(
            corrupted_chunk_count=2, unrecoverable_chunk_count=0
        )
        self.assertTrue(r_healed.valid)

    def test_17_g57_rejects_malformed_and_bool_spoofed_telemetry(self) -> None:
        for bad_kwargs in (
            {"media_a_st_dev": True},
            {"gf256_primitive_poly": True},
            {"allow_same_filesystem": "no"},
            {"unrecoverable_chunk_count": -1},
            {"media_a_surface_hashes": "not-a-dict"},
            {"guard_profile": ""},
        ):
            res = verify_dual_media_vault_and_gf256_scrub_guard(**bad_kwargs)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G57_TELEMETRY_INVALID)

        ok_val, eff = validate_gf256_bitrot_scrub_guard(corrupted_chunk_count=True)  # type: ignore[arg-type]
        self.assertFalse(ok_val)
        self.assertEqual(eff, -1)

    def test_18_evaluate_g57_blocks_persistent_writes_and_bad_donor(self) -> None:
        verdict, res = evaluate_g57_dualmedia_vault(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        bad_audit = audit_phase173_donor_contracts(force_clean_room=True)
        tampered = bad_audit.__class__(
            **{
                **bad_audit.to_dict(),
                "valid": False,
                "status": STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY,
                "errors": ("tampered",),
            }
        )
        v_bad, r_bad = evaluate_g57_dualmedia_vault(donor_audit=tampered)
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertIn(STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY, r_bad.violation_codes)

    # --- 4. Gate G58 — Two-Step Human Bench Auth & Zero-Auto-Flash Interlock ---

    def test_19_g58_default_passes_with_zero_auto_flash_interlock_locked(self) -> None:
        res = verify_two_step_bench_interlock_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G58)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.agent_auto_flash_blocked)
        self.assertFalse(res.auto_flash_requested)
        self.assertFalse(res.ai_agent_self_authorize_attempted)
        self.assertFalse(res.physical_flash_auto_exec_authorized)
        self.assertTrue(res.auto_flash_interlock_safe)
        self.assertTrue(res.two_step_interlock_armed)
        self.assertFalse(res.bench_execution_requested)
        self.assertFalse(res.human_bench_authorized)
        self.assertTrue(res.battery_preflash_safe)
        self.assertTrue(res.op_ff_ram_canary_verified)
        self.assertTrue(res.msc_return_054c_0da1_verified)
        self.assertTrue(res.dual_media_fx3rcpt1_match)
        self.assertTrue(res.canary_and_fx3rcpt1_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_20_g58_blocks_auto_flash_and_ai_self_authorization(self) -> None:
        for bad_kwargs in (
            {"agent_auto_flash_blocked": False},
            {"auto_flash_requested": True},
            {"ai_agent_self_authorize_attempted": True},
            {"two_step_interlock_armed": False},
            {"target_model_id": 0x91030070},
            {"target_model_name": "ILME-FX6"},
        ):
            res = verify_two_step_bench_interlock_guard(**bad_kwargs)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"Expected fail for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION
            )
            self.assertFalse(res.physical_flash_auto_exec_authorized)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_21_g58_blocks_bench_execution_without_two_step_human_auth(self) -> None:
        # Missing both steps
        r0 = verify_two_step_bench_interlock_guard(bench_execution_requested=True)
        self.assertFalse(r0.valid)
        self.assertEqual(r0.status, STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING)
        self.assertFalse(r0.two_step_human_auth_satisfied)
        self.assertFalse(r0.human_bench_authorized)

        # Only step 1 provided
        r1 = verify_two_step_bench_interlock_guard(
            bench_execution_requested=True,
            human_operator_id="kafu",
            human_step1_acknowledged=True,
            human_step1_token="STEP1-OK-01",
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING, r1.violation_codes)

        # Wrong step 2 phrase
        r2 = verify_two_step_bench_interlock_guard(
            bench_execution_requested=True,
            human_operator_id="kafu",
            human_step1_acknowledged=True,
            human_step1_token="STEP1-OK-01",
            human_step2_acknowledged=True,
            human_step2_phrase="YES",
        )
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING, r2.violation_codes)

        # Identical token & phrase rejected (must be distinct two-step)
        r3 = verify_two_step_bench_interlock_guard(
            bench_execution_requested=True,
            human_operator_id="kafu",
            human_step1_acknowledged=True,
            human_step1_token=EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE,
            human_step2_acknowledged=True,
            human_step2_phrase=EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE,
        )
        self.assertFalse(r3.valid)
        self.assertIn(STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING, r3.violation_codes)

    def test_22_g58_accepts_valid_two_step_human_auth_while_redlines_locked(self) -> None:
        res = verify_two_step_bench_interlock_guard(
            bench_execution_requested=True,
            human_operator_id="kafu",
            human_step1_acknowledged=True,
            human_step1_token="BENCH-CHECK-2026-11-15-STEP1",
            human_step2_acknowledged=True,
            human_step2_phrase=EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G58)
        self.assertTrue(res.two_step_human_auth_satisfied)
        self.assertTrue(res.human_bench_authorized)
        self.assertFalse(res.physical_flash_auto_exec_authorized)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_23_g58_enforces_battery_80pct_7400mv_preflash_threshold(self) -> None:
        # Exact boundary passes
        r_ok = verify_two_step_bench_interlock_guard(
            battery_soc_pct=80.0,
            battery_mv=7400,
            usb_pd_contract_mw=27_000,
        )
        self.assertTrue(r_ok.valid)

        # Violations
        for bad_kwargs in (
            {"battery_soc_pct": 79.9},
            {"battery_soc_pct": 100.1},
            {"battery_mv": 7399},
            {"battery_mv": 8501},
            {"battery_model": "BP-U35"},
            {"usb_pd_contract_mw": 26_999},
        ):
            res = verify_two_step_bench_interlock_guard(**bad_kwargs)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"Expected fail for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD
            )
            self.assertFalse(res.battery_preflash_safe)

    def test_24_g58_enforces_op_ff_canary_and_dual_media_fx3rcpt1_match(self) -> None:
        other_sha = hashlib.sha256(b"mismatch_fx3rcpt1").hexdigest()
        for bad_kwargs in (
            {"op_ff_canary_opcode": 0xFE},
            {"op_ff_ram_canary_verified": False},
            {"fx3s0ok_header_magic": "FX3BAD0"},
            {"fx3s0ok_packet_bytes": 512},
            {"msc_return_054c_0da1_verified": False},
            {"fx3rcpt1_magic": "BADMAGIC"},
            {"fx3rcpt1_packet_bytes": 256},
            {"camera_cid_sha256": "0" * 64},
            {"media_a_fx3rcpt1_sha256": other_sha},
            {"fx3rcpt1_dual_media_match": False},
        ):
            res = verify_two_step_bench_interlock_guard(**bad_kwargs)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"Expected fail for {bad_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED
            )
            self.assertFalse(res.canary_and_fx3rcpt1_safe)

    def test_25_g58_rejects_malformed_nan_inf_and_bool_telemetry(self) -> None:
        for bad_kwargs in (
            {"battery_soc_pct": math.nan},
            {"battery_soc_pct": math.inf},
            {"battery_soc_pct": True},
            {"battery_mv": True},
            {"usb_pd_contract_mw": -1},
            {"target_model_id": "not-hex"},
            {"agent_auto_flash_blocked": "yes"},
            {"camera_cid_sha256": ""},
        ):
            res = verify_two_step_bench_interlock_guard(**bad_kwargs)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"Expected telemetry fail for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G58_TELEMETRY_INVALID)

    def test_26_evaluate_g58_blocks_persistent_writes_and_bad_donor(self) -> None:
        verdict, res = evaluate_g58_bench_interlock(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        bad_audit = audit_phase173_donor_contracts(force_clean_room=True)
        tampered = bad_audit.__class__(
            **{
                **bad_audit.to_dict(),
                "valid": False,
                "status": STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY,
                "errors": ("tampered",),
            }
        )
        v_bad, r_bad = evaluate_g58_bench_interlock(donor_audit=tampered)
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertIn(STATUS_BLOCKED_PHASE173_DONOR_INTEGRITY, r_bad.violation_codes)

    # --- 5. Unified 58-Gate Master Preflight Engine (G01..G58) ---

    def test_27_58gate_offline_default_reports_55_of_58_and_redlines_false(self) -> None:
        report = evaluate_58gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(report.schema, REALHW_DUALMEDIA_BENCH_58GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_DUALMEDIA_BENCH_58GATE_VERSION)
        self.assertTrue(report.offline_55_gates_verified)
        self.assertFalse(report.all_58_gates_verified)
        self.assertTrue(report.g13_to_g58_all_passed)
        self.assertTrue(report.g57_to_g58_all_passed)
        self.assertTrue(report.h0_h1_trial_entry_allowed)
        self.assertTrue(report.agent_auto_flash_blocked)
        self.assertFalse(report.dry_run_rehearsal_only)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.status, "VERIFIED_55_OF_58_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(report.summary["total_gates"], 58)
        self.assertEqual(report.summary["verified_gates"], 55)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g01_to_g12_verified"], 9)
        self.assertEqual(report.summary["g13_to_g56_verified"], 44)
        self.assertEqual(report.summary["g57_to_g58_verified"], 2)
        for idx in (9, 10, 11):
            self.assertFalse(report.gates[idx]["passed"])
            self.assertEqual(
                report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_28_58gate_dry_run_simulated_backup_reports_58_of_58_still_no_writes(
        self,
    ) -> None:
        report = evaluate_58_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(report.offline_55_gates_verified)
        self.assertTrue(report.all_58_gates_verified)
        self.assertTrue(report.g13_to_g58_all_passed)
        self.assertTrue(report.g57_to_g58_all_passed)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.agent_auto_flash_blocked)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(
            report.status, "VERIFIED_ALL_58_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(report.summary["verified_gates"], 58)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(report.summary["g01_to_g12_verified"], 12)
        self.assertEqual(report.summary["g13_to_g56_verified"], 44)
        self.assertEqual(report.summary["g57_to_g58_verified"], 2)

    def test_29_58gate_propagates_g55_g56_g57_and_g58_failures(self) -> None:
        r_g55 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            c2pa_cert_kwargs={"cross_model_signing_attempted": True},
        )
        self.assertFalse(r_g55.all_58_gates_verified)
        self.assertFalse(r_g55.g13_to_g58_all_passed)
        self.assertEqual(r_g55.status, STATUS_BLOCKED_G55_CROSS_MODEL_SIGNING_KEY)

        r_g56 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tc_gyro_meta_kwargs={"fx6_tc_out_bnc_masked": False},
        )
        self.assertFalse(r_g56.all_58_gates_verified)
        self.assertEqual(r_g56.status, STATUS_BLOCKED_G56_FX6_TC_OUT_BNC_UNMASKED)

        r_g57 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dualmedia_vault_kwargs={"media_b_st_dev": DEFAULT_MEDIA_A_ST_DEV},
        )
        self.assertFalse(r_g57.all_58_gates_verified)
        self.assertFalse(r_g57.g57_to_g58_all_passed)
        self.assertFalse(r_g57.h0_h1_trial_entry_allowed)
        self.assertEqual(r_g57.status, STATUS_BLOCKED_G57_SINGLE_MEDIA_OR_SAME_ST_DEV)

        r_g58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            bench_interlock_kwargs={"battery_mv": 7399},
        )
        self.assertFalse(r_g58.all_58_gates_verified)
        self.assertFalse(r_g58.g57_to_g58_all_passed)
        self.assertFalse(r_g58.h0_h1_trial_entry_allowed)
        self.assertEqual(
            r_g58.status, STATUS_BLOCKED_G58_BATTERY_BELOW_PREFLASH_THRESHOLD
        )

    def test_30_58gate_unique_gate_ids_and_56gate_unchanged(self) -> None:
        m56 = evaluate_56gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        m58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(len(m56.gates), 56)
        self.assertEqual(len(m58.gates), 58)
        gate_ids = [g["gate_id"] for g in m58.gates]
        self.assertEqual(len(set(gate_ids)), 58)
        self.assertEqual(gate_ids[56], G57_GATE_ID)
        self.assertEqual(gate_ids[57], G58_GATE_ID)

    def test_31_json_serializable_without_raw_binary_leakage(self) -> None:
        report = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        dumped = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["summary"]["verified_gates"], 58)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("b'\\x89UFU", dumped)
        self.assertNotIn("b'BK4", dumped)

    # --- 6. CLI Tests (fx3_safety.__main__ & module main) ---

    def test_32_cli_verify_g57_dualmedia_vault_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g57-dualmedia-vault", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G57)
        self.assertTrue(data["dualmedia_vault_guard"]["device_ids_separated"])
        self.assertTrue(data["dualmedia_vault_guard"]["gf256_pq_verified"])
        self.assertEqual(data["dualmedia_vault_guard"]["unrecoverable_chunk_count"], 0)
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_33_cli_verify_g58_bench_interlock_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g58-bench-interlock", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G58)
        self.assertTrue(data["bench_interlock_guard"]["agent_auto_flash_blocked"])
        self.assertTrue(data["bench_interlock_guard"]["two_step_interlock_armed"])
        self.assertTrue(data["bench_interlock_guard"]["dual_media_fx3rcpt1_match"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_34_cli_verify_58_gates_offline_and_dry_run(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-58-gates", "--clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=55/58", buf_off.getvalue())
        self.assertIn("agent_auto_flash_blocked=True", buf_off.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf_off.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf_off.getvalue())
        self.assertIn("spi_nor_write_authorized=False", buf_off.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_off.getvalue())

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        data = json.loads(buf_dry.getvalue())
        self.assertTrue(data["all_58_gates_verified"])
        self.assertEqual(data["summary"]["verified_gates"], 58)
        self.assertTrue(data["agent_auto_flash_blocked"])
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_35_module_cli_main_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--clean-room", "--dry-run-simulated-backup"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=58/58", out)
        self.assertIn("agent_auto_flash_blocked=True", out)
        self.assertIn("el3_payload_transmit_authorized=False", out)
        self.assertIn("spi_nor_write_authorized=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_j = io.StringIO()
        with contextlib.redirect_stdout(buf_j):
            rc_j = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(buf_j.getvalue())
        self.assertTrue(parsed["all_58_gates_verified"])

    # --- 7. Additional Boundary & Edge-Case Coverage Tests (48 Total) ---

    def test_36_g57_supports_two_distinct_st_dev_paths_or_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = Path(tmpdir) / "sd_vault"
            dir_a.mkdir()
            real_dev = os.stat(dir_a).st_dev
            res = verify_dual_media_vault_and_gf256_scrub_guard(
                media_a_path=dir_a,
                media_b_st_dev=real_dev + 7,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.media_a_st_dev, real_dev)
            self.assertEqual(res.media_b_st_dev, real_dev + 7)
            self.assertTrue(res.device_ids_separated)

    def test_37_g57_active_gf256_recovery_disabled_still_checks_flags(self) -> None:
        r_ok = verify_dual_media_vault_and_gf256_scrub_guard(
            run_active_gf256_recovery_check=False
        )
        self.assertTrue(r_ok.valid)
        r_bad = verify_dual_media_vault_and_gf256_scrub_guard(
            run_active_gf256_recovery_check=False,
            scrub_passed=False,
        )
        self.assertFalse(r_bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_GF256_SCRUB_OR_QUORUM_LOSS, r_bad.violation_codes
        )

    def test_38_g57_rejects_f_all_hex64_and_short_hashes(self) -> None:
        hashes_a = default_verified_16_surface_hashes()
        hashes_f = dict(hashes_a)
        hashes_f["p15_usr"] = "f" * 64
        r_f = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_surface_hashes=hashes_f,
            media_b_surface_hashes=hashes_f,
        )
        self.assertFalse(r_f.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH, r_f.violation_codes
        )

        hashes_short = dict(hashes_a)
        hashes_short["p15_usr"] = "abcd"
        r_s = verify_dual_media_vault_and_gf256_scrub_guard(
            media_a_surface_hashes=hashes_short,
            media_b_surface_hashes=hashes_short,
        )
        self.assertFalse(r_s.valid)
        self.assertIn(
            STATUS_BLOCKED_G57_16_SURFACE_SHA256_MISMATCH, r_s.violation_codes
        )

    def test_39_g57_rejects_non_existent_path(self) -> None:
        ok, dev_a, dev_b = validate_dual_media_device_id_separation(
            media_a_path=Path("/nonexistent/fx3_sd_cold_backup_path_173"),
            media_b_st_dev=DEFAULT_MEDIA_B_ST_DEV,
        )
        self.assertFalse(ok)
        self.assertEqual((dev_a, dev_b), (-1, -1))

    def test_40_g58_accepts_string_hex_model_id_and_case_insensitive_hashes(self) -> None:
        cid_upper = DEFAULT_SYNTHETIC_CAMERA_CID_SHA256.upper()
        rcpt_upper = DEFAULT_SYNTHETIC_FX3RCPT1_SHA256.upper()
        res = verify_two_step_bench_interlock_guard(
            target_model_id="0x91030080",
            camera_cid_sha256=cid_upper,
            media_a_fx3rcpt1_sha256=rcpt_upper,
            media_b_fx3rcpt1_sha256=DEFAULT_SYNTHETIC_FX3RCPT1_SHA256,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.target_model_id_hex, "0x91030080")
        self.assertTrue(res.dual_media_fx3rcpt1_match)

    def test_41_g58_blocks_blank_operator_id_even_with_tokens(self) -> None:
        res = verify_two_step_bench_interlock_guard(
            bench_execution_requested=True,
            human_operator_id="   ",
            human_step1_acknowledged=True,
            human_step1_token="TOKEN-A",
            human_step2_acknowledged=True,
            human_step2_phrase=EXPECTED_STEP2_HUMAN_CONFIRM_PHRASE,
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G58_TWO_STEP_HUMAN_AUTH_MISSING, res.violation_codes)

    def test_42_g58_blocks_trivial_all_f_cid_and_rcpt_hashes(self) -> None:
        r_cid = verify_two_step_bench_interlock_guard(camera_cid_sha256="f" * 64)
        self.assertFalse(r_cid.valid)
        self.assertIn(
            STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED, r_cid.violation_codes
        )

        r_rcpt = verify_two_step_bench_interlock_guard(
            media_a_fx3rcpt1_sha256="0" * 64,
            media_b_fx3rcpt1_sha256="0" * 64,
        )
        self.assertFalse(r_rcpt.valid)
        self.assertIn(
            STATUS_BLOCKED_G58_CANARY_OR_FX3RCPT1_UNVERIFIED, r_rcpt.violation_codes
        )

    def test_43_58gate_blocks_persistent_write_request_and_locks_redlines(self) -> None:
        report = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(report.all_58_gates_verified)
        self.assertFalse(report.offline_55_gates_verified)
        self.assertFalse(report.h0_h1_trial_entry_allowed)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_44_gf256_pq_exhaustively_recovers_all_adjacent_2_shard_pairs(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(64)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]
        for idx in range(len(chunks) - 1):
            probe: list[bytes | None] = list(chunks)
            probe[idx] = None
            probe[idx + 1] = None
            rec, healed, _, _ = recover_gf256_pq_chunks(
                probe, p_chunk, q_chunk, expected_sha256s=expected
            )
            self.assertTrue(rec.valid, f"Failed adjacent recovery ({idx}, {idx + 1})")
            self.assertEqual(healed, chunks)

    def test_45_gf256_pq_recovers_data_plus_q_and_data_plus_p(self) -> None:
        chunks, hashes, p_chunk, q_chunk = build_synthetic_16_surface_chunks(64)
        expected = [hashes[s] for s in CANONICAL_16_STORAGE_SURFACES]

        probe_dq: list[bytes | None] = list(chunks)
        probe_dq[14] = None
        r1, h1, _, q1 = recover_gf256_pq_chunks(
            probe_dq, p_chunk, None, expected_sha256s=expected
        )
        self.assertTrue(r1.valid)
        self.assertEqual(h1, chunks)
        self.assertEqual(q1, q_chunk)

        probe_dp: list[bytes | None] = list(chunks)
        probe_dp[15] = None
        r2, h2, p2, _ = recover_gf256_pq_chunks(
            probe_dp, None, q_chunk, expected_sha256s=expected
        )
        self.assertTrue(r2.valid)
        self.assertEqual(h2, chunks)
        self.assertEqual(p2, p_chunk)

    def test_46_clean_room_env_var_overrides_local_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            report = evaluate_58gate_preflight(
                DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
            )
            self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(report.clean_room_forced)
            self.assertTrue(report.all_58_gates_verified)
            self.assertEqual(report.summary["verified_gates"], 58)
            self.assertTrue(report.agent_auto_flash_blocked)
            self.assertFalse(report.overall_ready_for_hardware_attach)
            self.assertFalse(report.el3_payload_transmit_authorized)
            self.assertFalse(report.spi_nor_write_authorized)
            self.assertFalse(report.persistent_emmc_writes_authorized)
            self.assertFalse(report.persistent_write_release)

    def test_47_text_cli_output_for_g57_and_g58(self) -> None:
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = package_cli_main(["verify-g57-dualmedia-vault", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn(STATUS_VERIFIED_G57, buf1.getvalue())
        self.assertIn("sep=True", buf1.getvalue())
        self.assertIn("parity=16/16", buf1.getvalue())
        self.assertIn("gf256=0x11d", buf1.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf1.getvalue())

        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = package_cli_main(["verify-g58-bench-interlock", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn(STATUS_VERIFIED_G58, buf2.getvalue())
        self.assertIn("auto_flash_blocked=True", buf2.getvalue())
        self.assertIn("canary_ok=True", buf2.getvalue())
        self.assertIn("fx3rcpt1_match=True", buf2.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf2.getvalue())

    def test_48_g57_and_g58_gate_verdicts_include_expected_ids_and_codes(self) -> None:
        v57, _r57 = evaluate_g57_dualmedia_vault(force_clean_room=True)
        self.assertEqual(v57.gate_id, G57_GATE_ID)
        self.assertEqual(v57.gate_code, G57_GATE_CODE)
        self.assertTrue(v57.passed)
        self.assertEqual(v57.status, STATUS_VERIFIED_G57)

        v58, _r58 = evaluate_g58_bench_interlock(force_clean_room=True)
        self.assertEqual(v58.gate_id, G58_GATE_ID)
        self.assertEqual(v58.gate_code, G58_GATE_CODE)
        self.assertTrue(v58.passed)
        self.assertEqual(v58.status, STATUS_VERIFIED_G58)


if __name__ == "__main__":
    unittest.main()
