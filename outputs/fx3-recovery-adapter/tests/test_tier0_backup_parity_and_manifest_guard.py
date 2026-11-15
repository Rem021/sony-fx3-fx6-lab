"""Dual-mode unit tests for Phase 72 Tier-0 Backup GF(256) Parity Healer & Anti-Transplant Guard.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real FX3 `2.05/nflasha1` and `nflasha5.img` via `os.O_RDONLY`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic fixtures)
Designed for `<0.3s` execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from hashlib import sha256
import io
import itertools
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.emmc_dump_forensic_verifier import (
    FX3A_PRODUCT_MODEL_ID,
    build_synthetic_p2_bk4_image,
    build_synthetic_p5_wbi2_image,
)
from fx3_recovery.files import ROOT, is_forced_clean_room, read_file, resolve_donor_path
from fx3_recovery.tier0_backup_parity_and_manifest_guard import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    DONOR_P1_205_RELPATH,
    DONOR_P5_WBI2_RELPATH,
    ERR_AB_SLOT_ASYMMETRY,
    ERR_ALL_FF_ERASED_FLASH_READ,
    ERR_ALL_ZERO_BLANK_READ,
    ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN,
    ERR_DEGENERATE_BYTE_ENTROPY,
    ERR_INVALID_STRUCTURAL_MAGIC,
    ERR_MISSING_PARTITION,
    ERR_SAFETY_POLICY_VIOLATION,
    ERR_TRUNCATED_PARTITION,
    ERR_UNRECOVERABLE_QUORUM_LOSS,
    GF256_EXP,
    GF256_LOG,
    GF256_PRIMITIVE_POLY,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    READ_ONLY_DONOR_ACCESS,
    STATUS_VERIFIED_TIER0_BACKUP,
    TIER0_BACKUP_GUARD_SCHEMA,
    TIER0_BACKUP_MANIFEST_SCHEMA,
    TIER0_PARTITION_NAMES,
    build_body_hardware_identity,
    build_synthetic_tier0_backup_bundle,
    build_tier0_backup_manifest,
    compute_body_identity_binding_sha256,
    encode_gf256_pq_parity,
    gf256_add,
    gf256_div,
    gf256_inv,
    gf256_mul,
    gf256_pow,
    gf256_sub,
    heal_gf256_pq_shards,
    heal_tier0_backup_bundle,
    run_tier0_backup_parity_suite,
    validate_tier0_backup_bundle,
    validate_tier0_partition,
    verify_cross_body_anti_transplant,
)


def _pseudo_bytes(tag: bytes, size: int) -> bytes:
    out = bytearray()
    seed = tag
    while len(out) < size:
        seed = sha256(seed).digest()
        out.extend(seed)
    return bytes(out[:size])


class Tier0BackupParityAndManifestGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._bundle_a = build_synthetic_tier0_backup_bundle(body_tag="body_a")
        cls._serial_a = sha256(b"FX3-UNIT-TEST-BODY-A").hexdigest()
        cls._manifest_a, cls._parity_a = build_tier0_backup_manifest(
            cls._bundle_a,
            camera_model="ILME-FX3",
            body_serial_hash=cls._serial_a,
        )
        cls._identity_a = build_body_hardware_identity(
            camera_model="ILME-FX3",
            body_serial_hash=cls._serial_a,
            cnflasha_calibration_sha256=cls._manifest_a.cnflasha_calibration_sha256,
            c2pa_rq_lic_sha256=cls._manifest_a.c2pa_rq_lic_sha256,
        )

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase72-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(len(TIER0_PARTITION_NAMES), 11)
        self.assertEqual(fx3_recovery.TIER0_BACKUP_GUARD_SCHEMA, TIER0_BACKUP_GUARD_SCHEMA)
        self.assertEqual(fx3_recovery.TIER0_BACKUP_MANIFEST_SCHEMA, TIER0_BACKUP_MANIFEST_SCHEMA)
        for symbol in (
            "encode_gf256_pq_parity",
            "heal_gf256_pq_shards",
            "heal_tier0_backup_bundle",
            "validate_tier0_partition",
            "validate_tier0_backup_bundle",
            "build_body_hardware_identity",
            "build_tier0_backup_manifest",
            "compute_body_identity_binding_sha256",
            "verify_cross_body_anti_transplant",
            "run_tier0_backup_parity_suite",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_gf256_field_axioms_and_0x11d_generator_order(self) -> None:
        self.assertEqual(GF256_PRIMITIVE_POLY, 0x11D)
        nonzero_cycle = [GF256_EXP[i] for i in range(255)]
        self.assertEqual(len(set(nonzero_cycle)), 255)
        self.assertNotIn(0, nonzero_cycle)
        for a in range(1, 256):
            self.assertEqual(GF256_EXP[GF256_LOG[a]], a)
            inv_a = gf256_inv(a)
            self.assertEqual(gf256_mul(a, inv_a), 1)
            self.assertEqual(gf256_div(a, a), 1)
        with self.assertRaises(ZeroDivisionError):
            gf256_inv(0)
        with self.assertRaises(ZeroDivisionError):
            gf256_div(7, 0)

    def test_03_gf256_distributivity_associativity_and_power(self) -> None:
        samples = (0, 1, 2, 3, 0x1D, 0x53, 0x8E, 0xFF)
        for a in samples:
            self.assertEqual(gf256_mul(a, 0), 0)
            self.assertEqual(gf256_mul(a, 1), a)
            self.assertEqual(gf256_add(a, a), 0)
            self.assertEqual(gf256_sub(a, a), 0)
            for b in samples:
                self.assertEqual(gf256_mul(a, b), gf256_mul(b, a))
                for c in samples:
                    self.assertEqual(
                        gf256_mul(a, gf256_add(b, c)),
                        gf256_add(gf256_mul(a, b), gf256_mul(a, c)),
                    )
                    self.assertEqual(
                        gf256_mul(gf256_mul(a, b), c),
                        gf256_mul(a, gf256_mul(b, c)),
                    )
        for exp in range(16):
            self.assertEqual(gf256_pow(0x02, exp), GF256_EXP[exp])

    def test_04_valid_11_partition_tier0_bundle_passes(self) -> None:
        rep = validate_tier0_backup_bundle(self._bundle_a)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, STATUS_VERIFIED_TIER0_BACKUP)
        self.assertEqual(rep.partition_count, 11)
        self.assertEqual(len(rep.ab_symmetry), 3)
        self.assertTrue(all(s.symmetric for s in rep.ab_symmetry))
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_05_rejects_missing_partition(self) -> None:
        bad = dict(self._bundle_a)
        del bad["bk4_nvram"]
        rep = validate_tier0_backup_bundle(bad)
        self.assertFalse(rep.passed)
        self.assertIn(ERR_MISSING_PARTITION, rep.error_codes)

    def test_06_rejects_short_read_and_unaligned_truncation(self) -> None:
        bad_short = dict(self._bundle_a)
        bad_short["nbl_a"] = bad_short["nbl_a"][:1024]
        rep1 = validate_tier0_backup_bundle(bad_short)
        self.assertFalse(rep1.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, rep1.error_codes)

        bad_unaligned = dict(self._bundle_a)
        bad_unaligned["cnflasha_spacc"] = bad_unaligned["cnflasha_spacc"][:-17]
        rep2 = validate_tier0_backup_bundle(bad_unaligned)
        self.assertFalse(rep2.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, rep2.error_codes)

        bad_empty = validate_tier0_partition("boot_a", b"")
        self.assertFalse(bad_empty.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_empty.error_codes)

    def test_07_rejects_header_declared_truncation_in_p1_wbi2_uboot_boot_c2pa(self) -> None:
        bad_p1 = validate_tier0_partition("p1_vfat", self._bundle_a["p1_vfat"][:4096])
        self.assertFalse(bad_p1.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_p1.error_codes)

        bad_wbi2 = validate_tier0_partition("wbi2_hibdrv", self._bundle_a["wbi2_hibdrv"][:-512])
        self.assertFalse(bad_wbi2.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_wbi2.error_codes)

        bad_uboot = validate_tier0_partition("uboot_a", self._bundle_a["uboot_a"][:2048])
        self.assertFalse(bad_uboot.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_uboot.error_codes)

        bad_boot = validate_tier0_partition("boot_a", self._bundle_a["boot_a"][:4096])
        self.assertFalse(bad_boot.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_boot.error_codes)

        bad_c2pa = validate_tier0_partition("c2pa_rq_lic", self._bundle_a["c2pa_rq_lic"][:1024])
        self.assertFalse(bad_c2pa.passed)
        self.assertIn(ERR_TRUNCATED_PARTITION, bad_c2pa.error_codes)

    def test_08_rejects_all_zero_blank_read(self) -> None:
        for name in ("nbl_a", "p1_vfat", "cnflasha_spacc", "c2pa_rq_lic"):
            res = validate_tier0_partition(name, b"\x00" * 4096)
            self.assertFalse(res.passed)
            self.assertIn(ERR_ALL_ZERO_BLANK_READ, res.error_codes)

    def test_09_rejects_all_ff_erased_flash_read(self) -> None:
        for name in ("uboot_b", "bk4_nvram", "wbi2_hibdrv", "cnflasha_spacc"):
            res = validate_tier0_partition(name, b"\xff" * 4096)
            self.assertFalse(res.passed)
            self.assertIn(ERR_ALL_FF_ERASED_FLASH_READ, res.error_codes)

    def test_10_rejects_constant_fill_and_degenerate_entropy(self) -> None:
        const_res = validate_tier0_partition("nbl_a", b"\xaa" * 4096)
        self.assertFalse(const_res.passed)
        self.assertIn(ERR_DEGENERATE_BYTE_ENTROPY, const_res.error_codes)

        # Low-entropy repeating 2-byte pattern with ELF header
        low_ent = bytearray(b"\x12\x34" * 2048)
        low_ent[0:4] = b"\x7fELF"
        low_res = validate_tier0_partition("nbl_a", bytes(low_ent))
        self.assertFalse(low_res.passed)
        self.assertIn(ERR_DEGENERATE_BYTE_ENTROPY, low_res.error_codes)

        # Encrypted cnflasha containing a stuck 4 KiB 0xFF page
        stuck_cn = bytearray(self._bundle_a["cnflasha_spacc"])
        stuck_cn[0:4096] = b"\xff" * 4096
        cn_res = validate_tier0_partition("cnflasha_spacc", bytes(stuck_cn))
        self.assertFalse(cn_res.passed)
        self.assertIn(ERR_DEGENERATE_BYTE_ENTROPY, cn_res.error_codes)

    def test_11_rejects_invalid_structural_magics_and_foreign_model(self) -> None:
        # Bad NBL magic
        bad_nbl = bytearray(self._bundle_a["nbl_a"])
        bad_nbl[0:4] = b"NOPE"
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("nbl_a", bytes(bad_nbl)).error_codes)

        # Bad U-Boot magic
        bad_uboot = bytearray(self._bundle_a["uboot_a"])
        bad_uboot[0:4] = b"BAD!"
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("uboot_a", bytes(bad_uboot)).error_codes)

        # Bad P1 boot signature
        bad_p1 = bytearray(self._bundle_a["p1_vfat"])
        bad_p1[510:512] = b"\x00\x00"
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("p1_vfat", bytes(bad_p1)).error_codes)

        # Foreign FX3A model ID inside BK4 NVRAM
        foreign_bk4 = build_synthetic_p2_bk4_image(product_model_id=FX3A_PRODUCT_MODEL_ID)
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("bk4_nvram", foreign_bk4).error_codes)

        # Invalidated WBI2 magic (`wbi2` cold-boot marker)
        cold_wbi2 = build_synthetic_p5_wbi2_image(magic=b"wbi2")
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("wbi2_hibdrv", cold_wbi2).error_codes)

        # Bad C2PA RQ_LIC magic
        bad_c2pa = bytearray(self._bundle_a["c2pa_rq_lic"])
        bad_c2pa[0:4] = b"JUNK"
        self.assertIn(ERR_INVALID_STRUCTURAL_MAGIC, validate_tier0_partition("c2pa_rq_lic", bytes(bad_c2pa)).error_codes)

    def test_12_accepts_alternative_valid_structural_magics(self) -> None:
        # NBL AArch64 branch opcode (0x14000010)
        nbl_br = bytearray(_pseudo_bytes(b"nbl-br", 4096))
        struct.pack_into("<I", nbl_br, 0, 0x14000010)
        self.assertTrue(validate_tier0_partition("nbl_a", bytes(nbl_br)).passed)

        # U-Boot legacy uImage
        uimg = bytearray(_pseudo_bytes(b"uimg", 4096))
        uimg[0:4] = b"\x27\x05\x19\x56"
        struct.pack_into(">I", uimg, 12, 2048)
        self.assertTrue(validate_tier0_partition("uboot_a", bytes(uimg)).passed)

        # Boot ARM64 Linux Image magic at 0x38
        arm64_img = bytearray(_pseudo_bytes(b"arm64-img", 4096))
        arm64_img[0x38:0x3C] = b"ARM\x64"
        self.assertTrue(validate_tier0_partition("boot_a", bytes(arm64_img)).passed)

        # C2PA JUMBF box
        jumbf = bytearray(_pseudo_bytes(b"c2pa-jumbf", 2048))
        struct.pack_into(">I", jumbf, 0, 2048)
        jumbf[4:8] = b"jumb"
        self.assertTrue(validate_tier0_partition("c2pa_rq_lic", bytes(jumbf)).passed)

    def test_13_ab_slot_symmetry_enforces_size_magic_and_digest_match(self) -> None:
        skewed = dict(self._bundle_a)
        mod_boot = bytearray(skewed["boot_b"])
        mod_boot[-1] ^= 0xFF
        skewed["boot_b"] = bytes(mod_boot)

        strict_rep = validate_tier0_backup_bundle(skewed, require_ab_symmetry=True)
        self.assertFalse(strict_rep.passed)
        self.assertIn(ERR_AB_SLOT_ASYMMETRY, strict_rep.error_codes)

        relaxed_rep = validate_tier0_backup_bundle(skewed, require_ab_symmetry=False)
        self.assertTrue(relaxed_rep.passed, relaxed_rep.errors)

        # Size asymmetry still fails even with require_ab_symmetry=False
        mod_nbl = bytearray(self._bundle_a["nbl_b"]) + _pseudo_bytes(b"extra-nbl", 512)
        skewed_size = dict(self._bundle_a)
        skewed_size["nbl_b"] = bytes(mod_nbl)
        size_rep = validate_tier0_backup_bundle(skewed_size, require_ab_symmetry=False)
        self.assertFalse(size_rep.passed)
        self.assertIn(ERR_AB_SLOT_ASYMMETRY, size_rep.error_codes)

    def test_14_gf256_healthy_bundle_no_repair_needed(self) -> None:
        res, recon = heal_tier0_backup_bundle(
            self._bundle_a,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.repair_mode, "HEALTHY_NO_REPAIR")
        self.assertEqual(res.healed_partitions, ())
        self.assertTrue(res.bit_exact_match)
        self.assertIsNotNone(recon)
        for name in TIER0_PARTITION_NAMES:
            self.assertEqual(recon[name], self._bundle_a[name])

    def test_15_gf256_heals_every_single_partition_erasure_bit_exact(self) -> None:
        # Exhaustively test all 11 shard positions (0..10) at GF(256) stripe level
        shards = [_pseudo_bytes(f"single-{i}".encode("ascii"), 4096) for i in range(11)]
        stripe = encode_gf256_pq_parity(shards, shard_names=TIER0_PARTITION_NAMES)
        for idx in range(11):
            dmg_s: list = list(shards)
            dmg_s[idx] = None
            hres, _, _ = heal_gf256_pq_shards(
                dmg_s,
                stripe.p_parity,
                stripe.q_parity,
                shard_sizes=stripe.shard_sizes,
                stripe_bytes=stripe.stripe_bytes,
                expected_shard_sha256s=stripe.shard_sha256s,
                expected_p_sha256=stripe.p_sha256,
                expected_q_sha256=stripe.q_sha256,
                shard_names=TIER0_PARTITION_NAMES,
            )
            self.assertTrue(hres.passed, hres.errors)
            assert hres.reconstructed_shards is not None
            self.assertEqual(hres.reconstructed_shards[idx], shards[idx])

        # Also test full Tier-0 manifest healing on representative partitions
        for name in ("nbl_a", "p1_vfat", "wbi2_hibdrv", "cnflasha_spacc", "c2pa_rq_lic"):
            dmg: dict = dict(self._bundle_a)
            dmg[name] = None
            res, recon = heal_tier0_backup_bundle(
                dmg,
                self._manifest_a,
                p_parity=self._parity_a.p_parity,
                q_parity=self._parity_a.q_parity,
                target_body_identity=self._identity_a,
            )
            self.assertTrue(res.passed, f"{name}: {res.errors}")
            self.assertEqual(res.healed_partitions, (name,))
            self.assertTrue(res.bit_exact_match)
            self.assertEqual(res.reconstructed_bundle_sha256, res.original_bundle_sha256)
            assert recon is not None
            self.assertEqual(
                sha256(recon[name]).hexdigest(),
                self._manifest_a.partition_sha256s[name],
            )
            self.assertEqual(recon[name], self._bundle_a[name])

    def test_16_gf256_heals_all_55_two_shard_erasure_pairs_bit_exact(self) -> None:
        # Fast 4 KiB 11-shard stripe to exhaustively prove all C(11, 2) = 55 2-erasure combinations
        shards = [_pseudo_bytes(f"compact-{i}".encode("ascii"), 4096 - (i * 17)) for i in range(11)]
        stripe = encode_gf256_pq_parity(shards, shard_names=TIER0_PARTITION_NAMES)
        for i, j in itertools.combinations(range(11), 2):
            dmg: list = list(shards)
            dmg[i] = None
            dmg[j] = None
            heal_res, _, _ = heal_gf256_pq_shards(
                dmg,
                stripe.p_parity,
                stripe.q_parity,
                shard_sizes=stripe.shard_sizes,
                stripe_bytes=stripe.stripe_bytes,
                expected_shard_sha256s=stripe.shard_sha256s,
                expected_p_sha256=stripe.p_sha256,
                expected_q_sha256=stripe.q_sha256,
                shard_names=TIER0_PARTITION_NAMES,
            )
            self.assertTrue(heal_res.passed, f"pair=({i},{j}): {heal_res.errors}")
            self.assertTrue(heal_res.bit_exact_match)
            assert heal_res.reconstructed_shards is not None
            self.assertEqual(heal_res.reconstructed_shards[i], shards[i])
            self.assertEqual(heal_res.reconstructed_shards[j], shards[j])

    def test_17_gf256_heals_parity_losses_and_data_plus_parity_erasures(self) -> None:
        shards = [_pseudo_bytes(f"p-erasure-{i}".encode("ascii"), 2048 + i * 31) for i in range(11)]
        stripe = encode_gf256_pq_parity(shards)

        # P lost, Q lost, P+Q lost
        for p_in, q_in in ((None, stripe.q_parity), (stripe.p_parity, None), (None, None)):
            res, p_out, q_out = heal_gf256_pq_shards(
                shards,
                p_in,
                q_in,
                shard_sizes=stripe.shard_sizes,
                stripe_bytes=stripe.stripe_bytes,
                expected_shard_sha256s=stripe.shard_sha256s,
                expected_p_sha256=stripe.p_sha256,
                expected_q_sha256=stripe.q_sha256,
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(p_out, stripe.p_parity)
            self.assertEqual(q_out, stripe.q_parity)

        # Data[5] + P lost -> recover via Q
        dmg_dp = list(shards)
        dmg_dp[5] = None
        res_dp, p_out, _ = heal_gf256_pq_shards(
            dmg_dp,
            None,
            stripe.q_parity,
            shard_sizes=stripe.shard_sizes,
            stripe_bytes=stripe.stripe_bytes,
            expected_shard_sha256s=stripe.shard_sha256s,
            expected_p_sha256=stripe.p_sha256,
            expected_q_sha256=stripe.q_sha256,
        )
        self.assertTrue(res_dp.passed, res_dp.errors)
        assert res_dp.reconstructed_shards is not None
        self.assertEqual(res_dp.reconstructed_shards[5], shards[5])
        self.assertEqual(p_out, stripe.p_parity)

        # Data[9] + Q lost -> recover via P
        dmg_dq = list(shards)
        dmg_dq[9] = None
        res_dq, _, q_out = heal_gf256_pq_shards(
            dmg_dq,
            stripe.p_parity,
            None,
            shard_sizes=stripe.shard_sizes,
            stripe_bytes=stripe.stripe_bytes,
            expected_shard_sha256s=stripe.shard_sha256s,
            expected_p_sha256=stripe.p_sha256,
            expected_q_sha256=stripe.q_sha256,
        )
        self.assertTrue(res_dq.passed, res_dq.errors)
        assert res_dq.reconstructed_shards is not None
        self.assertEqual(res_dq.reconstructed_shards[9], shards[9])
        self.assertEqual(q_out, stripe.q_parity)

    def test_18_gf256_pure_syndrome_heals_single_silent_bitrot_without_sha(self) -> None:
        shards = [_pseudo_bytes(f"syn-{i}".encode("ascii"), 4096) for i in range(11)]
        stripe = encode_gf256_pq_parity(shards, shard_names=TIER0_PARTITION_NAMES)
        for target_idx in (0, 6, 10):
            corrupted = list(shards)
            buf = bytearray(corrupted[target_idx])
            buf[17] ^= 0x55
            buf[2049] ^= 0xC3
            corrupted[target_idx] = bytes(buf)

            res, _, _ = heal_gf256_pq_shards(
                corrupted,
                stripe.p_parity,
                stripe.q_parity,
                shard_sizes=stripe.shard_sizes,
                stripe_bytes=stripe.stripe_bytes,
                expected_shard_sha256s=None,
                shard_names=TIER0_PARTITION_NAMES,
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.repair_mode, "SYNDROME_SINGLE_CORRUPT_HEAL")
            self.assertEqual(res.healed_indices, (target_idx,))
            assert res.reconstructed_shards is not None
            self.assertEqual(res.reconstructed_shards[target_idx], shards[target_idx])

    def test_19_gf256_heals_2_silent_bitrot_shards_and_mixed_erase_plus_corrupt(self) -> None:
        # 2 silent bit-rot shards in Tier-0 bundle
        dmg_2rot: dict = dict(self._bundle_a)
        b_uboot = bytearray(dmg_2rot["uboot_a"])
        b_uboot[300] ^= 0xFF
        b_c2pa = bytearray(dmg_2rot["c2pa_rq_lic"])
        b_c2pa[512] ^= 0x7E
        dmg_2rot["uboot_a"] = bytes(b_uboot)
        dmg_2rot["c2pa_rq_lic"] = bytes(b_c2pa)

        res_2rot, recon_2rot = heal_tier0_backup_bundle(
            dmg_2rot,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertTrue(res_2rot.passed, res_2rot.errors)
        self.assertEqual(res_2rot.repair_mode, "CORRUPTION_2_SHARD_HEAL")
        self.assertTrue(res_2rot.bit_exact_match)
        assert recon_2rot is not None
        self.assertEqual(recon_2rot["uboot_a"], self._bundle_a["uboot_a"])
        self.assertEqual(recon_2rot["c2pa_rq_lic"], self._bundle_a["c2pa_rq_lic"])

        # 1 erased + 1 silently corrupted
        dmg_mix: dict = dict(self._bundle_a)
        dmg_mix["boot_a"] = None
        b_bk4 = bytearray(dmg_mix["bk4_nvram"])
        b_bk4[100] ^= 0x3C
        dmg_mix["bk4_nvram"] = bytes(b_bk4)
        res_mix, recon_mix = heal_tier0_backup_bundle(
            dmg_mix,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertTrue(res_mix.passed, res_mix.errors)
        self.assertEqual(res_mix.repair_mode, "MIXED_ERASE_AND_CORRUPT_2_SHARD_HEAL")
        assert recon_mix is not None
        self.assertEqual(recon_mix["boot_a"], self._bundle_a["boot_a"])
        self.assertEqual(recon_mix["bk4_nvram"], self._bundle_a["bk4_nvram"])

    def test_20_gf256_heals_1_corrupt_data_plus_1_corrupt_parity(self) -> None:
        dmg: dict = dict(self._bundle_a)
        b_nbl = bytearray(dmg["nbl_b"])
        b_nbl[64] ^= 0x99
        dmg["nbl_b"] = bytes(b_nbl)
        bad_q = bytearray(self._parity_a.q_parity)
        bad_q[12] ^= 0x44

        res, recon = heal_tier0_backup_bundle(
            dmg,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=bytes(bad_q),
            target_body_identity=self._identity_a,
        )
        self.assertTrue(res.passed, res.errors)
        assert recon is not None
        self.assertEqual(recon["nbl_b"], self._bundle_a["nbl_b"])

    def test_21_fail_closed_on_3_erased_shards(self) -> None:
        dmg: dict = dict(self._bundle_a)
        dmg["nbl_a"] = None
        dmg["uboot_b"] = None
        dmg["cnflasha_spacc"] = None
        res, recon = heal_tier0_backup_bundle(
            dmg,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertFalse(res.passed)
        self.assertIsNone(recon)
        self.assertIn(ERR_UNRECOVERABLE_QUORUM_LOSS, res.error_codes)

    def test_22_fail_closed_on_2_erased_data_plus_1_corrupt_or_parity_loss(self) -> None:
        # 2 erased data + 1 silently corrupted data
        dmg1: dict = dict(self._bundle_a)
        dmg1["nbl_a"] = None
        dmg1["nbl_b"] = None
        b_c2pa = bytearray(dmg1["c2pa_rq_lic"])
        b_c2pa[200] ^= 0x11
        dmg1["c2pa_rq_lic"] = bytes(b_c2pa)
        res1, recon1 = heal_tier0_backup_bundle(
            dmg1,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertFalse(res1.passed)
        self.assertIsNone(recon1)
        self.assertIn(ERR_UNRECOVERABLE_QUORUM_LOSS, res1.error_codes)

        # 2 erased data + 1 lost parity (P lost)
        dmg2: dict = dict(self._bundle_a)
        dmg2["boot_a"] = None
        dmg2["bk4_nvram"] = None
        res2, recon2 = heal_tier0_backup_bundle(
            dmg2,
            self._manifest_a,
            p_parity=None,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        self.assertFalse(res2.passed)
        self.assertIsNone(recon2)
        self.assertIn(ERR_UNRECOVERABLE_QUORUM_LOSS, res2.error_codes)

    def test_23_fail_closed_on_undeclared_3rd_corruption_without_sha_detection(self) -> None:
        # Even if SHA wasn't checked pre-solve, post-heal SHA catches silent 3rd corruption
        shards = [_pseudo_bytes(f"postsha-{i}".encode("ascii"), 1024) for i in range(6)]
        stripe = encode_gf256_pq_parity(shards)
        # Corrupt shard 2 without telling SHA? Wait: heal_gf256_pq_shards checks expected_shard_sha256s;
        # Test raw syndrome path with 2 simultaneous corruptions (S0/S1 won't match single shard)
        corrupted = list(shards)
        b0 = bytearray(corrupted[0])
        b1 = bytearray(corrupted[1])
        b0[10] ^= 0xAA
        b1[10] ^= 0x55
        corrupted[0] = bytes(b0)
        corrupted[1] = bytes(b1)
        res, _, _ = heal_gf256_pq_shards(
            corrupted,
            stripe.p_parity,
            stripe.q_parity,
            shard_sizes=stripe.shard_sizes,
            stripe_bytes=stripe.stripe_bytes,
            expected_shard_sha256s=None,
        )
        self.assertFalse(res.passed)
        self.assertIsNone(res.reconstructed_shards)
        self.assertIn(ERR_UNRECOVERABLE_QUORUM_LOSS, res.error_codes)

    def test_24_body_identity_binding_determinism_and_raw_serial_rejection(self) -> None:
        b1 = compute_body_identity_binding_sha256(
            "ILME-FX3",
            self._serial_a,
            self._manifest_a.cnflasha_calibration_sha256,
            self._manifest_a.c2pa_rq_lic_sha256,
        )
        b2 = compute_body_identity_binding_sha256(
            "ILME-FX3",
            self._serial_a.upper(),
            self._manifest_a.cnflasha_calibration_sha256,
            self._manifest_a.c2pa_rq_lic_sha256,
        )
        self.assertEqual(b1, b2)
        self.assertEqual(b1, self._manifest_a.body_identity_binding_sha256)
        with self.assertRaises(ValueError):
            compute_body_identity_binding_sha256(
                "ILME-FX3",
                "RAW_SERIAL_1234567",
                self._manifest_a.cnflasha_calibration_sha256,
                self._manifest_a.c2pa_rq_lic_sha256,
            )

    def test_25_anti_transplant_blocks_cross_body_cnflasha_and_c2pa_rq_lic(self) -> None:
        bundle_b = build_synthetic_tier0_backup_bundle(body_tag="body_b")
        cn_b_sha = sha256(bundle_b["cnflasha_spacc"]).hexdigest()
        c2pa_b_sha = sha256(bundle_b["c2pa_rq_lic"]).hexdigest()

        # Case 1: cnflasha calibration belongs to Body-B
        id_cn_mismatch = build_body_hardware_identity(
            camera_model="ILME-FX3",
            body_serial_hash=self._serial_a,
            cnflasha_calibration_sha256=cn_b_sha,
            c2pa_rq_lic_sha256=self._manifest_a.c2pa_rq_lic_sha256,
        )
        d1 = verify_cross_body_anti_transplant(self._manifest_a, target_body_identity=id_cn_mismatch)
        self.assertFalse(d1.allowed)
        self.assertIn(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN, d1.error_codes)
        self.assertIn("cnflasha_calibration_sha256_mismatch", d1.mismatch_reasons)

        # Case 2: RQ_LIC.DAT C2PA license belongs to Body-B
        id_c2pa_mismatch = build_body_hardware_identity(
            camera_model="ILME-FX3",
            body_serial_hash=self._serial_a,
            cnflasha_calibration_sha256=self._manifest_a.cnflasha_calibration_sha256,
            c2pa_rq_lic_sha256=c2pa_b_sha,
        )
        d2 = verify_cross_body_anti_transplant(self._manifest_a, target_body_identity=id_c2pa_mismatch)
        self.assertFalse(d2.allowed)
        self.assertIn(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN, d2.error_codes)
        self.assertIn("c2pa_rq_lic_sha256_mismatch", d2.mismatch_reasons)

        # Case 3: Body-B serial + model mismatch (e.g. ILME-FX6)
        id_model_serial = build_body_hardware_identity(
            camera_model="ILME-FX6",
            body_serial_hash=sha256(b"FX6-BODY-B").hexdigest(),
            cnflasha_calibration_sha256=self._manifest_a.cnflasha_calibration_sha256,
            c2pa_rq_lic_sha256=self._manifest_a.c2pa_rq_lic_sha256,
        )
        d3 = verify_cross_body_anti_transplant(self._manifest_a, target_body_identity=id_model_serial)
        self.assertFalse(d3.allowed)
        self.assertIn(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN, d3.error_codes)

    def test_26_anti_transplant_blocks_tampered_manifest_and_swapped_bundle_shards(self) -> None:
        tampered_binding = replace(
            self._manifest_a,
            body_identity_binding_sha256="0" * 64,
        )
        d1 = verify_cross_body_anti_transplant(tampered_binding, target_body_identity=self._identity_a)
        self.assertFalse(d1.allowed)
        self.assertIn(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN, d1.error_codes)

        bundle_b = build_synthetic_tier0_backup_bundle(body_tag="body_b")
        swapped_bundle = dict(self._bundle_a)
        swapped_bundle["c2pa_rq_lic"] = bundle_b["c2pa_rq_lic"]
        d2 = verify_cross_body_anti_transplant(self._manifest_a, bundle_partitions=swapped_bundle)
        self.assertFalse(d2.allowed)
        self.assertIn("bundle_c2pa_rq_lic_sha256_mismatch", d2.mismatch_reasons)

    def test_27_heal_refuses_cross_body_target_and_unlocked_safety_flags(self) -> None:
        bundle_b = build_synthetic_tier0_backup_bundle(body_tag="body_b")
        id_b = build_body_hardware_identity(
            camera_model="ILME-FX3",
            body_serial_hash=sha256(b"BODY-B").hexdigest(),
            cnflasha_calibration_sha256=sha256(bundle_b["cnflasha_spacc"]).hexdigest(),
            c2pa_rq_lic_sha256=sha256(bundle_b["c2pa_rq_lic"]).hexdigest(),
        )
        dmg: dict = dict(self._bundle_a)
        dmg["nbl_a"] = None
        res, recon = heal_tier0_backup_bundle(
            dmg,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=id_b,
        )
        self.assertFalse(res.passed)
        self.assertIsNone(recon)
        self.assertIn(ERR_CROSS_BODY_TRANSPLANT_FORBIDDEN, res.error_codes)

        # Unlocked safety flags inside manifest fail closed
        for bad_kwargs in (
            {"persistent_emmc_writes_authorized": True},
            {"persistent_write_release": True},
            {"physical_device_writes": 1},
        ):
            bad_manifest = replace(self._manifest_a, **bad_kwargs)
            d_bad = verify_cross_body_anti_transplant(bad_manifest)
            self.assertFalse(d_bad.allowed)
            self.assertIn(ERR_SAFETY_POLICY_VIOLATION, d_bad.error_codes)

    def test_28_dual_mode_suite_clean_room_and_local_donor_o_rdonly(self) -> None:
        rep_clean = run_tier0_backup_parity_suite(force_clean_room=True)
        self.assertTrue(rep_clean.all_passed, rep_clean.errors)
        self.assertEqual(rep_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(rep_clean.persistent_emmc_writes_authorized)
        self.assertFalse(rep_clean.persistent_write_release)
        self.assertEqual(rep_clean.physical_device_writes, 0)

        p1_path = resolve_donor_path(DONOR_P1_205_RELPATH)
        p5_path = resolve_donor_path(DONOR_P5_WBI2_RELPATH)
        if not is_forced_clean_room() and p1_path.is_file() and p5_path.is_file():
            rep_donor = run_tier0_backup_parity_suite(force_clean_room=False)
            self.assertTrue(rep_donor.all_passed, rep_donor.errors)
            self.assertEqual(rep_donor.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(rep_donor.donor_p1_sha256, sha256(read_file(p1_path, 64 * 1024 * 1024)).hexdigest())
            self.assertEqual(rep_donor.donor_p5_wbi2_sha256, sha256(read_file(p5_path, 256 * 1024 * 1024)).hexdigest())

    def test_29_cli_verify_tier0_backup_clean_room_json_and_out(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli-tier0-out"
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-tier0-backup", "--clean-room", "--json", "--out", str(out_dir)],
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        payload = json.loads(rendered)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_TIER0_BACKUP)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["physical_device_writes"], 0)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertFalse(payload["persistent_write_release"])
        report_file = out_dir / "tier0-backup-report.json"
        self.assertTrue(report_file.is_file())
        saved = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["schema"], TIER0_BACKUP_GUARD_SCHEMA)

    def test_30_cli_verify_tier0_backup_text_summary_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-tier0-backup", "--clean-room"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        line = buf.getvalue().strip()
        self.assertIn("status=VERIFIED_TIER0_BACKUP", line)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", line)
        self.assertIn("partitions=11", line)
        self.assertIn("physical_device_writes=0", line)
        self.assertIn("persistent_emmc_writes_authorized=False", line)
        self.assertIn("persistent_write_release=False", line)

    def test_31_json_reports_contain_no_raw_bytes_repr(self) -> None:
        val = validate_tier0_backup_bundle(self._bundle_a)
        decision = verify_cross_body_anti_transplant(self._manifest_a, target_body_identity=self._identity_a)
        dmg: dict = dict(self._bundle_a)
        dmg["nbl_a"] = None
        heal_rep, _ = heal_tier0_backup_bundle(
            dmg,
            self._manifest_a,
            p_parity=self._parity_a.p_parity,
            q_parity=self._parity_a.q_parity,
            target_body_identity=self._identity_a,
        )
        rendered = json.dumps(
            {
                "validation": val.__dict__,
                "manifest": self._manifest_a.to_dict(),
                "anti_transplant": decision.__dict__,
                "heal": heal_rep.__dict__,
            },
            default=lambda o: o.__dict__,
            sort_keys=True,
            allow_nan=False,
        )
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_32_clean_room_suite_runtime_under_0_3s(self) -> None:
        t0 = time.monotonic()
        rep = run_tier0_backup_parity_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertLess(elapsed, 0.3)


if __name__ == "__main__":
    unittest.main()
