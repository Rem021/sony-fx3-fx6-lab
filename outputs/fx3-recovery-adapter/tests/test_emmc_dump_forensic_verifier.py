"""Dual-mode tests for Phase 42 Tier-4 Offline Read-Only eMMC Dump Forensic Verifier.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real FX3 `2.05/nflasha1`, `nflasha8.img`, `nflasha5.img`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic synthetic fixtures, <4s runtime)
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery.emmc_dump_forensic_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    A7IV_PRODUCT_MODEL_ID,
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    FORENSIC_VERIFIER_SCHEMA,
    FX3A_PRODUCT_MODEL_ID,
    FX3_PRODUCT_MODEL_ENUM,
    FX3_PRODUCT_MODEL_ID,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    READ_ONLY_DONOR_ACCESS,
    SONY_PTBL_SIZE,
    WBI2_XOR_MASK,
    ForensicVerificationError,
    analyze_bus_and_entropy,
    audit_boot_chain_immutability,
    build_synthetic_encrypted_cnflasha,
    build_synthetic_ext_csd,
    build_synthetic_p1_vfat_image,
    build_synthetic_p2_bk4_image,
    build_synthetic_p5_wbi2_image,
    build_synthetic_p8_cp_image,
    build_synthetic_sector0_fx3,
    compute_shannon_entropy,
    read_two_pass_sha256_readonly,
    report_to_dict,
    run_clean_room_forensic_suite,
    verify_emmc_dump_bytes,
    verify_emmc_dump_file,
    verify_ext_csd_dump,
    verify_p1_vfat_dump,
    verify_p2_bk4_nvram_dump,
    verify_p5_wbi2_dump,
    verify_p8_cp_rtos_dump,
    verify_sector0_dump,
    verify_two_pass_provider_stability,
)
from fx3_recovery.files import ROOT, is_clean_room_or_donor_unavailable, resolve_donor_path

DONOR_P1_205 = resolve_donor_path(
    "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
)
DONOR_P8_IMG = resolve_donor_path("sony-firmware-20261024/stage2/extraction/nflasha8.img")
DONOR_P5_IMG = resolve_donor_path("sony-firmware-20261024/stage2/extraction/nflasha5.img")


class EmmcDumpForensicVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self._sandbox = ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-forensic-test-{os.getpid()}-{time.time_ns()}"
        self._sandbox.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertFalse(fx3_recovery.ALLOW_BOOT_PARTITION_TARGETING)
        self.assertEqual(fx3_recovery.FORENSIC_VERIFIER_SCHEMA, FORENSIC_VERIFIER_SCHEMA)
        self.assertIn("verify_emmc_dump_file", fx3_recovery.__all__)
        self.assertIn("audit_boot_chain_immutability", fx3_recovery.__all__)

    def test_02_shannon_entropy_edge_cases(self) -> None:
        self.assertEqual(compute_shannon_entropy(b""), 0.0)
        self.assertEqual(compute_shannon_entropy(b"\x00" * 4096), 0.0)
        self.assertEqual(compute_shannon_entropy(b"\xff" * 4096), 0.0)
        uniform = bytes(range(256)) * 16
        self.assertAlmostEqual(compute_shannon_entropy(uniform), 8.0, places=3)

    def test_03_detects_all_zero_stuck_bus_dump(self) -> None:
        rep = analyze_bus_and_entropy(b"\x00" * 16384, role="generic")
        self.assertFalse(rep.passed)
        self.assertTrue(rep.stuck_bus_detected)
        self.assertEqual(rep.constant_fill_byte, 0x00)
        self.assertIn("ALL_ZERO_DUMP", rep.anomalies)

    def test_04_detects_all_ff_stuck_bus_dump(self) -> None:
        rep = analyze_bus_and_entropy(b"\xff" * 16384, role="generic")
        self.assertFalse(rep.passed)
        self.assertTrue(rep.stuck_bus_detected)
        self.assertEqual(rep.constant_fill_byte, 0xFF)
        self.assertIn("ALL_FF_DUMP", rep.anomalies)

    def test_05_detects_constant_non_zero_fill_pattern(self) -> None:
        rep = analyze_bus_and_entropy(b"\xaa" * 16384, role="generic")
        self.assertFalse(rep.passed)
        self.assertTrue(rep.stuck_bus_detected)
        self.assertEqual(rep.constant_fill_byte, 0xAA)
        self.assertTrue(any("CONSTANT_FILL_ANOMALY:0xaa" in a for a in rep.anomalies))

    def test_06_detects_contiguous_0xff_pullup_run_in_mixed_dump(self) -> None:
        good = build_synthetic_encrypted_cnflasha(32768)
        stuck = good + (b"\xff" * (20 * 4096)) + good
        rep = analyze_bus_and_entropy(stuck, role="generic", max_contig_ff_pages=16)
        self.assertFalse(rep.passed)
        self.assertTrue(rep.stuck_bus_detected)
        self.assertGreaterEqual(rep.max_contiguous_ff_pages, 20)
        self.assertTrue(any("STUCK_BUS_0xFF_RUN" in a for a in rep.anomalies))

    def test_07_detects_truncated_and_unaligned_reads(self) -> None:
        base = build_synthetic_encrypted_cnflasha(16384)
        rep_short = analyze_bus_and_entropy(base, expected_size=32768, role="cnflasha", expect_encrypted=True)
        self.assertFalse(rep_short.passed)
        self.assertTrue(rep_short.truncation_detected)
        self.assertTrue(any("TRUNCATED_OR_SIZE_MISMATCH" in a for a in rep_short.anomalies))

        rep_unaligned = analyze_bus_and_entropy(base[:-13], role="p1")
        self.assertFalse(rep_unaligned.passed)
        self.assertTrue(rep_unaligned.truncation_detected)
        self.assertTrue(any("UNALIGNED_SECTOR_READ" in a for a in rep_unaligned.anomalies))

        rep_empty = analyze_bus_and_entropy(b"", role="generic")
        self.assertFalse(rep_empty.passed)
        self.assertIn("TRUNCATED_EMPTY_DUMP", rep_empty.anomalies)

    def test_08_detects_entropy_collapse_in_compressed_and_encrypted_dumps(self) -> None:
        # Low-entropy repeating buffer fails compressed p1 role
        flat = (b"SONY-BOOT-PAD000" * 1024)[:16384]
        rep_p1 = analyze_bus_and_entropy(flat, role="p1", expect_compressed=True)
        self.assertFalse(rep_p1.passed)
        self.assertTrue(rep_p1.entropy_collapse_detected)

        # Clean high-entropy cnflasha passes
        cipher = build_synthetic_encrypted_cnflasha(131072)
        rep_ok = analyze_bus_and_entropy(cipher, role="cnflasha", expect_encrypted=True)
        self.assertTrue(rep_ok.passed, rep_ok.anomalies)

        # Inject a localized 64 KiB low-entropy window inside cnflasha -> fails window collapse
        collapsed_win = cipher[:65536] + (b"ABCD1234" * 8192)
        rep_win = analyze_bus_and_entropy(collapsed_win, role="cnflasha", expect_encrypted=True)
        self.assertFalse(rep_win.passed)
        self.assertTrue(rep_win.entropy_collapse_detected)
        self.assertTrue(any("ENCRYPTED_WINDOW_ENTROPY_COLLAPSE" in a for a in rep_win.anomalies))

    def test_09_encrypted_cnflasha_rejects_even_single_zero_or_ff_page(self) -> None:
        cipher = build_synthetic_encrypted_cnflasha(32768)
        with_zero_page = cipher[:4096] + (b"\x00" * 4096) + cipher[8192:]
        rep = analyze_bus_and_entropy(with_zero_page, role="cnflasha", expect_encrypted=True)
        self.assertFalse(rep.passed)
        self.assertTrue(rep.stuck_bus_detected)
        self.assertTrue(any("STUCK_BUS_IN_ENCRYPTED_IMAGE" in a for a in rep.anomalies))

    def test_10_two_pass_o_rdonly_sha256_stability_and_symlink_rejection(self) -> None:
        dump_path = self._sandbox / "sector0_fx3.dat"
        raw = build_synthetic_sector0_fx3()
        dump_path.write_bytes(raw)

        stab, data = read_two_pass_sha256_readonly(dump_path)
        self.assertTrue(stab.stable, stab.errors)
        self.assertEqual(data, raw)
        self.assertEqual(stab.pass1_sha256, sha256(raw).hexdigest())
        self.assertEqual(stab.pass1_sha256, stab.pass2_sha256)

        # Symlink must be rejected by O_NOFOLLOW / local_path
        link_path = self._sandbox / "sector0_link.dat"
        os.symlink(dump_path, link_path)
        with self.assertRaises(ValueError):
            read_two_pass_sha256_readonly(link_path)

    def test_11_two_pass_provider_catches_bitflip_and_length_drift(self) -> None:
        raw = build_synthetic_sector0_fx3()

        def flaky_bitflip(pass_num: int) -> bytes:
            if pass_num == 1:
                return raw
            mut = bytearray(raw)
            mut[64] ^= 0x01
            return bytes(mut)

        rep_flip, buf_flip = verify_two_pass_provider_stability(flaky_bitflip, source_label="flaky-spi")
        self.assertFalse(rep_flip.stable)
        self.assertIsNone(buf_flip)
        self.assertTrue(any("TWO_PASS_SHA256_MISMATCH" in e for e in rep_flip.errors))

        rep_len, buf_len = verify_two_pass_provider_stability(
            lambda p: raw if p == 1 else raw[:-8], source_label="short-read"
        )
        self.assertFalse(rep_len.stable)
        self.assertIsNone(buf_len)
        self.assertTrue(any("TWO_PASS_LENGTH_MISMATCH" in e for e in rep_len.errors))

    def test_12_sector0_valid_fx3_702_and_bad_magic_version(self) -> None:
        sec0 = build_synthetic_sector0_fx3()
        rep = verify_sector0_dump(sec0)
        self.assertTrue(rep.valid, rep.errors)
        self.assertTrue(rep.magic_ok)
        self.assertTrue(rep.geometry_ok)
        self.assertTrue(rep.fx3_immutability_ok)
        self.assertEqual(rep.details["layout_profile"], "FX3_702")

        bad_magic = b"8247" + sec0[4:]
        rep_bad = verify_sector0_dump(bad_magic)
        self.assertFalse(rep_bad.valid)
        self.assertFalse(rep_bad.magic_ok)
        self.assertTrue(any("SECTOR0_BAD_MAGIC" in e for e in rep_bad.errors))

    def test_13_sector0_rejects_overlap_and_below_0x80_collision(self) -> None:
        sec0 = bytearray(build_synthetic_sector0_fx3())
        # Force p15 to overlap p12 (start at 0x00210000)
        off_p15 = 32 + 14 * 16
        struct.pack_into("<I", sec0, off_p15, 0x00210000)
        rep = verify_sector0_dump(bytes(sec0))
        self.assertFalse(rep.valid)
        self.assertFalse(rep.geometry_ok)
        self.assertTrue(any("SECTOR0_PARTITION_OVERLAP" in e for e in rep.errors))

        # Force p19 to start below 0x80 (table zone collision)
        sec0_b = bytearray(build_synthetic_sector0_fx3())
        off_p19 = 32 + 18 * 16
        struct.pack_into("<IIII", sec0_b, off_p19, 0x00000010, 0x100, 4, 1)
        rep_b = verify_sector0_dump(bytes(sec0_b))
        self.assertFalse(rep_b.valid)
        self.assertTrue(any("SECTOR0_COLLISION_BELOW_0x80" in e for e in rep_b.errors))

    def test_14_sector0_catches_fx6_p18_shift_hazard(self) -> None:
        buf = bytearray(SONY_PTBL_SIZE)
        buf[0:4] = b"8246"
        buf[4:8] = b"2.00"
        struct.pack_into("<I", buf, 8, 30)
        # Keep calibrated p1, p2, p6, set FX6 6.01 layout for p7, p12, p18@0x312000, p20, p21
        fx6_entries = {
            1: (0x00000080, 0x0000BF80, 4, 1),
            2: (0x0000C000, 0x0000A000, 4, 1),
            6: (0x000D8000, 0x0000C800, 4, 1),
            12: (0x0020C000, 0x0000A000, 5, 1),
            18: (0x00312000, 0x0000A000, 4, 1),
            20: (0x00220000, 0x00032000, 5, 1),
            21: (0x00252000, 0x00016400, 5, 1),
        }
        for pid, vals in fx6_entries.items():
            struct.pack_into("<IIII", buf, 32 + (pid - 1) * 16, *vals)
        rep = verify_sector0_dump(bytes(buf))
        self.assertFalse(rep.valid)
        self.assertFalse(rep.fx3_immutability_ok)
        self.assertEqual(rep.details["layout_profile"], "FX6_601")
        self.assertTrue(any("FX6_SECTOR0_P18_SHIFT_HAZARD" in e for e in rep.errors))

    def test_15_p1_vfat_geometry_and_fat_copy_mismatch(self) -> None:
        p1 = build_synthetic_p1_vfat_image()
        rep = verify_p1_vfat_dump(p1)
        self.assertTrue(rep.valid, rep.errors)
        self.assertEqual(rep.details["cluster_count"], 8)
        self.assertEqual(rep.details["file_count"], 2)

        bad_sig = bytearray(p1)
        bad_sig[510:512] = b"\x00\x00"
        self.assertFalse(verify_p1_vfat_dump(bytes(bad_sig)).valid)

        bad_fat2 = bytearray(p1)
        bad_fat2[512 + 32 * 512 + 10] ^= 0xFF
        rep_fat = verify_p1_vfat_dump(bytes(bad_fat2))
        self.assertFalse(rep_fat.valid)
        self.assertTrue(any("P1_FAT_VALIDATION_FAILED" in e for e in rep_fat.errors))

    def test_16_p2_bk4_raw_and_vfat_wrapped_pass(self) -> None:
        bk4 = build_synthetic_p2_bk4_image()
        rep = verify_p2_bk4_nvram_dump(bk4)
        self.assertTrue(rep.valid, rep.errors)
        self.assertTrue(rep.fx3_immutability_ok)
        self.assertEqual(rep.details["container"], "RAW_BK4")
        self.assertEqual(rep.details["observed_product_model_id"], hex(FX3_PRODUCT_MODEL_ID))
        self.assertEqual(rep.details["observed_product_model_enum"], FX3_PRODUCT_MODEL_ENUM)

        # Wrap BK4 inside a simulated VFAT p2 partition container at sector offset 4096
        wrapped = bytearray(16384)
        wrapped[510:512] = b"\x55\xaa"
        wrapped[4096 : 4096 + len(bk4)] = bk4
        rep_w = verify_p2_bk4_nvram_dump(bytes(wrapped))
        self.assertTrue(rep_w.valid, rep_w.errors)
        self.assertEqual(rep_w.details["container"], "VFAT_P2_CONTAINING_BK4")
        self.assertEqual(rep_w.details["bk4_offset"], 4096)

    def test_17_p2_bk4_checksum_tamper_and_fx3_immutability_rejection(self) -> None:
        bk4 = bytearray(build_synthetic_p2_bk4_image())
        bk4[BK4_HEADER_SIZE + 18] ^= 0x55
        rep_ck = verify_p2_bk4_nvram_dump(bytes(bk4))
        self.assertFalse(rep_ck.valid)
        self.assertTrue(any("P2_BK4_CHECKSUM_MISMATCH" in e for e in rep_ck.errors))

        # Foreign FX3A model ID (0x91030082) must be blocked
        fx3a_bk4 = build_synthetic_p2_bk4_image(product_model_id=FX3A_PRODUCT_MODEL_ID, product_model_enum=4)
        rep_fx3a = verify_p2_bk4_nvram_dump(fx3a_bk4)
        self.assertFalse(rep_fx3a.valid)
        self.assertFalse(rep_fx3a.fx3_immutability_ok)
        self.assertTrue(any("FX3_PRODUCT_MODEL_ID_IMMUTABILITY_VIOLATION" in e for e in rep_fx3a.errors))

        # Foreign A7IV model ID (0x01030081) + wrong enum must be blocked
        a7iv_bk4 = build_synthetic_p2_bk4_image(product_model_id=A7IV_PRODUCT_MODEL_ID, product_model_enum=3)
        rep_a7iv = verify_p2_bk4_nvram_dump(a7iv_bk4)
        self.assertFalse(rep_a7iv.valid)
        self.assertFalse(rep_a7iv.fx3_immutability_ok)

    def test_18_p5_wbi2_valid_and_invalidated_magic_detection(self) -> None:
        wbi = build_synthetic_p5_wbi2_image()
        rep = verify_p5_wbi2_dump(wbi)
        self.assertTrue(rep.valid, rep.errors)
        self.assertEqual(rep.details["sections"], 2)
        self.assertEqual(rep.details["zero_sections"], 1)
        self.assertTrue(rep.details["resume_covered"])

        for cold_magic in (b"wbi2", b"WBI3"):
            wbi_cold = build_synthetic_p5_wbi2_image(magic=cold_magic)
            rep_cold = verify_p5_wbi2_dump(wbi_cold)
            self.assertFalse(rep_cold.valid)
            self.assertFalse(rep_cold.magic_ok)
            self.assertTrue(any("P5_WBI2_MAGIC_INVALIDATED_COLD_BOOT_FORCED" in e for e in rep_cold.errors))

    def test_19_p5_wbi2_xor_metadata_and_resume_vector_tamper(self) -> None:
        wbi = bytearray(build_synthetic_p5_wbi2_image())
        r_data_size = struct.unpack_from("<Q", wbi, 48)[0]
        table_off = 512 + r_data_size
        # Corrupt section 0 meta_cksum (offset +48 inside 64B descriptor)
        cur_meta = struct.unpack_from("<Q", wbi, table_off + 48)[0]
        struct.pack_into("<Q", wbi, table_off + 48, cur_meta ^ WBI2_XOR_MASK)
        rep_xor = verify_p5_wbi2_dump(bytes(wbi))
        self.assertFalse(rep_xor.valid)
        self.assertTrue(any("P5_WBI2_SECTION_META_XOR_MISMATCH" in e for e in rep_xor.errors))

        # Corrupt resume_vector to point outside any non-zero snapshot section
        wbi2 = bytearray(build_synthetic_p5_wbi2_image())
        struct.pack_into("<Q", wbi2, 24, 0x4DEAD0000)
        rep_vec = verify_p5_wbi2_dump(bytes(wbi2))
        self.assertFalse(rep_vec.valid)
        self.assertTrue(any("P5_WBI2_RESUME_VECTOR_UNCOVERED" in e for e in rep_vec.errors))

    def test_20_p8_cp_rtos_fat12_and_raw_cpapp_validation(self) -> None:
        p8 = build_synthetic_p8_cp_image(include_tomco=True, valid_vector=True)
        rep = verify_p8_cp_rtos_dump(p8)
        self.assertTrue(rep.valid, rep.errors)
        self.assertTrue(rep.details["has_cpapp_b_bin"])
        self.assertTrue(rep.details["tomco_marker_ok"])
        self.assertEqual(rep.details["reserved_sectors"], 32)

        bad_vec = build_synthetic_p8_cp_image(include_tomco=True, valid_vector=False)
        rep_bad = verify_p8_cp_rtos_dump(bad_vec)
        self.assertFalse(rep_bad.valid)
        self.assertTrue(any("P8_CPAPP_INVALID_ARM_RESET_VECTOR" in e for e in rep_bad.errors))

        # Raw cpapp-b.bin mode
        raw_cp = bytearray(4096)
        struct.pack_into("<4I", raw_cp, 0, 0xE59F1004, 0xE2811004, 0xE1A0F001, 0x0010800C)
        raw_cp[64:73] = b"TOPPERS> "
        self.assertTrue(verify_p8_cp_rtos_dump(bytes(raw_cp)).valid)
        self.assertFalse(verify_p8_cp_rtos_dump(b"\x00" * 4096).valid)

    def test_21_ext_csd_part_config_sanity_and_brick_risk_detection(self) -> None:
        valid_csd = build_synthetic_ext_csd(part_config=0x48, boot_size_mult=32)
        rep = verify_ext_csd_dump(valid_csd)
        self.assertTrue(rep.valid, rep.errors)
        self.assertEqual(rep.boot_ack, 1)
        self.assertEqual(rep.boot_partition_name, "BOOT0")
        self.assertEqual(rep.partition_access_name, "USER_AREA")
        self.assertEqual(rep.boot_size_bytes, 4 * 1024 * 1024)

        # Boot partition disabled (0x00) is an immediate brick hazard
        disabled_csd = build_synthetic_ext_csd(part_config=0x00)
        rep_dis = verify_ext_csd_dump(disabled_csd)
        self.assertFalse(rep_dis.valid)
        self.assertTrue(any("BRICK_RISK" in e for e in rep_dis.errors))

        # Reserved bit 7 set must error
        res_csd = build_synthetic_ext_csd(part_config=0xC8)
        self.assertFalse(verify_ext_csd_dump(res_csd).valid)

        # Leftover PARTITION_ACCESS=BOOT0 (0x49) & high EOL produce warnings while remaining valid
        warn_csd = build_synthetic_ext_csd(part_config=0x49, pre_eol_info=0x03, life_time_a=0x0B)
        rep_warn = verify_ext_csd_dump(warn_csd)
        self.assertTrue(rep_warn.valid)
        self.assertTrue(any("PARTITION_ACCESS_NOT_RESET_TO_UDA" in w for w in rep_warn.warnings))
        self.assertTrue(any("PRE_EOL_URGENT_WEAR_RISK" in w for w in rep_warn.warnings))

    def test_22_boot_chain_firewall_blocks_protected_targets_and_writes(self) -> None:
        forbidden = (
            {"target": "/dev/nflashaB0", "operation": "write"},
            {"target": "BOOT1", "operation": "flash"},
            {"target": "/dev/mmcblk0rpmb", "operation": "erase"},
            {"target": "nflasha1", "operation": "patch"},
            {"target": "nflasha5", "operation": "write"},
            {"target": "nflasha8", "operation": "format"},
            {"target": "sector0", "operation": "dd"},
            {"target": "loader_nor", "operation": "modify"},
            {"target": "UDA", "cmd42_force_erase": True},
            {"target": "p1", "persistent_emmc_writes_authorized": True},
        )
        for manifest in forbidden:
            dec = audit_boot_chain_immutability(manifest)
            self.assertFalse(dec.allowed, f"expected firewall block for {manifest}")
            self.assertFalse(dec.persistent_emmc_writes_authorized)
            self.assertFalse(dec.allow_boot_partition_targeting)

    def test_23_boot_chain_firewall_permits_strictly_readonly_audits(self) -> None:
        for target in ("/dev/nflashaB0", "BOOT1", "nflasha5", "sector0", "nflasha10"):
            dec = audit_boot_chain_immutability({"target": target, "operation": "read_verify"})
            self.assertTrue(dec.allowed, dec.errors)
            self.assertFalse(dec.persistent_emmc_writes_authorized)
            self.assertEqual(dec.blocked_targets, ())

    def test_24_clean_room_forensic_suite_passes_all_7_roles(self) -> None:
        res = run_clean_room_forensic_suite()
        self.assertTrue(res["all_passed"])
        self.assertEqual(res["status"], "VERIFIED_READONLY")
        self.assertFalse(res["persistent_emmc_writes_authorized"])
        self.assertFalse(res["allow_boot_partition_targeting"])
        self.assertTrue(res["boot_chain_firewall_blocks_boot0_flash"])
        self.assertEqual(sorted(res["roles_verified"].keys()), ["cnflasha", "ext_csd", "p1", "p2", "p5", "p8", "sector0"])
        for role, info in res["roles_verified"].items():
            self.assertTrue(info["passed"], role)

    def test_25_verify_emmc_dump_bytes_integrates_manifest_firewall_and_ext_csd(self) -> None:
        cipher = build_synthetic_encrypted_cnflasha(32768)
        good_ext = build_synthetic_ext_csd(part_config=0x48)
        rep_ok = verify_emmc_dump_bytes(
            cipher,
            role="cnflasha",
            expect_encrypted=True,
            ext_csd_bytes=good_ext,
            manifest={"target": "cnflasha3", "operation": "read_verify"},
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        # Same payload with a mutating manifest targeting nflasha3 fails firewall
        rep_fw = verify_emmc_dump_bytes(
            cipher,
            role="cnflasha",
            expect_encrypted=True,
            ext_csd_bytes=good_ext,
            manifest={"target": "nflasha3", "operation": "flash"},
        )
        self.assertFalse(rep_fw.passed)
        self.assertFalse(rep_fw.boot_chain_firewall.allowed)

    def test_26_verify_emmc_dump_file_and_no_raw_bytes_repr_in_cli(self) -> None:
        sec_path = self._sandbox / "sec0.dat"
        ext_path = self._sandbox / "ext_csd.dat"
        out_dir = self._sandbox / "report_out"
        sec_path.write_bytes(build_synthetic_sector0_fx3())
        ext_path.write_bytes(build_synthetic_ext_csd())

        rep = verify_emmc_dump_file(sec_path, role="sector0", ext_csd_path=ext_path)
        self.assertTrue(rep.passed, rep.errors)
        as_json = json.dumps(report_to_dict(rep), sort_keys=True)
        self.assertNotIn("b'\\", as_json)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ROOT / 'outputs' / 'fx3-safety'}:{ROOT / 'outputs' / 'fx3-recovery-adapter'}"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-emmc-forensics",
                "--input",
                str(sec_path),
                "--role",
                "sector0",
                "--ext-csd",
                str(ext_path),
                "--out",
                str(out_dir),
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertNotIn("b'", proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["passed"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertTrue((out_dir / "forensic-report.json").is_file())

    def test_27_cli_fails_closed_on_tampered_p2_and_missing_input(self) -> None:
        bad_p2 = self._sandbox / "bad_p2.dat"
        bad_p2.write_bytes(build_synthetic_p2_bk4_image(product_model_id=FX3A_PRODUCT_MODEL_ID))

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ROOT / 'outputs' / 'fx3-safety'}:{ROOT / 'outputs' / 'fx3-recovery-adapter'}"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-emmc-forensics",
                "--input",
                str(bad_p2),
                "--role",
                "p2",
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "REJECTED")
        self.assertFalse(payload["passed"])

    def test_28_real_fx3_donor_images_o_rdonly_audit(self) -> None:
        if is_clean_room_or_donor_unavailable((DONOR_P1_205, DONOR_P8_IMG, DONOR_P5_IMG)):
            raise unittest.SkipTest("clean-room mode active or FX3 donor images unavailable")

        r_p1 = verify_emmc_dump_file(DONOR_P1_205, role="p1")
        self.assertTrue(r_p1.passed, r_p1.errors)
        self.assertEqual(r_p1.two_pass_stability.pass1_sha256, r_p1.two_pass_stability.pass2_sha256)
        self.assertGreaterEqual(r_p1.partition_magic.details["file_count"], 5)

        r_p8 = verify_emmc_dump_file(DONOR_P8_IMG, role="p8")
        self.assertTrue(r_p8.passed, r_p8.errors)
        self.assertTrue(r_p8.partition_magic.details["has_cpapp_b_bin"])
        self.assertTrue(r_p8.partition_magic.details["tomco_marker_ok"])

        r_p5 = verify_emmc_dump_file(DONOR_P5_IMG, role="p5")
        self.assertTrue(r_p5.passed, r_p5.errors)
        self.assertGreater(r_p5.partition_magic.details["sections"], 100)
        self.assertTrue(r_p5.partition_magic.details["resume_covered"])


if __name__ == "__main__":
    unittest.main()
