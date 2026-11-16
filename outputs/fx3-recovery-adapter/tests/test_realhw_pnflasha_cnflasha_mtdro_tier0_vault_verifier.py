"""Phase 151 (Pillar 19) Dual-Mode Fast Unit Tests (46 tests, <1.5s):

- Group 0 (01..08): Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room parity
- Group A (09..28): Sector 0 30-partition geometry, 16-surface Dual-Layer Vault, Cross-Domain Firewall (8 scenarios) & GF(256) healing
- Group B (29..41): /proc/mtd -> /dev/mtd*ro SPI NOR audit, IPL/BLoader/BL31/BootConfig envelope & p12/p13/p18/p23/p30 Factory Cal Gate
- Group C (42..46): Suite determinism, `verify-tier0-dual-layer-vault` CLI & `verify-all-recovery --with-phase151` (>= 19 pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
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
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK,
    BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH,
    BLOCKED_CROSS_DOMAIN_CNFLASHA_TO_PNFLASHA,
    BLOCKED_CROSS_DOMAIN_PNFLASHA_TO_CNFLASHA,
    BLOCKED_DUAL_COPY_BITROT_DETECTED,
    BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN,
    BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE,
    BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE,
    BLOCKED_SECTOR0_LBA_GEOMETRY_MISMATCH,
    BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID,
    DOMAIN_EMMC_REG_METADATA,
    DOMAIN_RAW_PNFLASHA_ISP,
    DOMAIN_SPACC_CNFLASHA_LOGICAL,
    DOMAIN_SPI_NOR_MTDRO,
    ERR_GF256_UNHEALABLE_BITROT,
    ERR_INVALID_MAGIC_OR_LOW_ENTROPY,
    ERR_MISSING_TIER0_SURFACES,
    ERR_WRITE_AUTH_LOCKED,
    EXT2_SUPER_MAGIC,
    FORBIDDEN_MTD_IOCTLS,
    FORBIDDEN_MTD_OPEN_MODES,
    FX3_30_PARTITION_TABLE,
    LENS_VX8900_MAGIC,
    MANDATORY_16_SURFACE_IDS,
    MTD_RW_OPENS_OR_ERASE_IOCTLS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P151_DONOR_FX3_CPAPP_B_RELPATH,
    P151_DONOR_FX3_IM_ELF_RELPATH,
    P151_DONOR_FX3_INSMOD_DRV1_RELPATH,
    P151_DONOR_FX3_LIBSENCORE_RELPATH,
    P151_DONOR_FX3_LOADER_NOR_BIN_RELPATH,
    P151_DONOR_FX3_MOUNT_RELPATH,
    P151_DONOR_FX3_NFLASHA15_RELPATH,
    P151_DONOR_FX3_NOR_LOADER_WRITER_RELPATH,
    P151_DONOR_FX3_PARTINF_RELPATH,
    P151_DONOR_FX3_PFORMAT_CONFIG_RELPATH,
    P151_DONOR_FX3_SETUP_NFLASH_RELPATH,
    P151_PINNED_FX3_CPAPP_B_BYTES,
    P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
    P151_PINNED_FX3_IM_ELF_BYTES,
    P151_PINNED_FX3_IM_ELF_SHA256,
    P151_PINNED_FX3_INSMOD_DRV1_BYTES,
    P151_PINNED_FX3_INSMOD_DRV1_SHA256,
    P151_PINNED_FX3_LIBSENCORE_BYTES,
    P151_PINNED_FX3_LIBSENCORE_SHA256,
    P151_PINNED_FX3_LOADER_NOR_BIN_BYTES,
    P151_PINNED_FX3_LOADER_NOR_BIN_SHA256,
    P151_PINNED_FX3_MOUNT_BYTES,
    P151_PINNED_FX3_MOUNT_SHA256,
    P151_PINNED_FX3_NFLASHA15_BYTES,
    P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
    P151_PINNED_FX3_NOR_LOADER_WRITER_BYTES,
    P151_PINNED_FX3_NOR_LOADER_WRITER_SHA256,
    P151_PINNED_FX3_PARTINF_BYTES,
    P151_PINNED_FX3_PARTINF_SHA256,
    P151_PINNED_FX3_PFORMAT_CONFIG_BYTES,
    P151_PINNED_FX3_PFORMAT_CONFIG_SHA256,
    P151_PINNED_FX3_SETUP_NFLASH_BYTES,
    P151_PINNED_FX3_SETUP_NFLASH_SHA256,
    PASSIVE_TX_BYTES_EMITTED,
    PER_CAMERA_CAL_SURFACE_IDS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE151_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PILLAR_A_SCENARIO_IDS,
    PILLAR_B_SCENARIO_IDS,
    READ_ONLY_DONOR_ACCESS,
    SECTOR0_ENTRY_COUNT,
    SECTOR0_MAGIC,
    SECTOR0_VERSION,
    SECTOR_SIZE_BYTES,
    SPACC_CIPHERTEXT_MIN_ENTROPY_BITS,
    SPI_NOR_ERASE_BLOCK_BYTES,
    SPI_NOR_ERASE_SECTOR_BYTES,
    SPI_NOR_REQUIRED_BOOT_STAGES,
    SPI_NOR_TOTAL_BYTES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_VERIFIED_PILLAR_A,
    STATUS_VERIFIED_PILLAR_B,
    STATUS_VERIFIED_SUITE,
    TIER0_16_SURFACES,
    VALID_LAYER_DOMAINS,
    VFAT_BOOT_SIG,
    DualLayerSurfaceEntry,
    audit_spi_nor_mtdro_dump,
    build_synthetic_16_surface_vault,
    build_synthetic_bk4_sample,
    build_synthetic_ext2_sample,
    build_synthetic_ext_csd_sample,
    build_synthetic_fx3_sector0_30_partitions,
    build_synthetic_high_entropy_spacc_sample,
    build_synthetic_proc_mtd_text,
    build_synthetic_spi_nor_sample,
    build_synthetic_squashfs_sample,
    build_synthetic_vfat_sample,
    build_synthetic_wbi2_sample,
    evaluate_restore_target_pairing,
    inspect_tier0_dual_layer_donors_readonly,
    parse_proc_mtd,
    run_pillar_a_8_scenario_firewall,
    run_pillar_b_6_scenario_gate,
    run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite,
    verify_dual_layer_16_surface_vault,
    verify_fx3_sector0_30_partition_geometry,
    verify_per_camera_factory_cal_vault_gate,
)
from fx3_recovery.tier0_backup_parity_and_manifest_guard import (
    encode_gf256_pq_parity,
    heal_gf256_pq_shards,
)

ROOT = Path(__file__).resolve().parents[3]


class TestRealHwPnflashaCnflashaMtdroTier0VaultVerifier(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 0: Safety Redlines, Exports, O_RDONLY Donors & Clean-Room
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_and_write_redlines(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(MTD_RW_OPENS_OR_ERASE_IOCTLS, 0)

    def test_02_package_exports_and_schema_constants(self) -> None:
        self.assertEqual(PHASE151_SCHEMA, "fx3-realhw-pnflasha-cnflasha-mtdro-tier0-vault-v1")
        for sym in (
            "realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier",
            "TIER0_16_SURFACES",
            "FX3_30_PARTITION_TABLE",
            "verify_fx3_sector0_30_partition_geometry",
            "verify_dual_layer_16_surface_vault",
            "evaluate_restore_target_pairing",
            "audit_spi_nor_mtdro_dump",
            "verify_per_camera_factory_cal_vault_gate",
            "run_pillar_a_8_scenario_firewall",
            "run_pillar_b_6_scenario_gate",
            "run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"missing export: {sym}")
            self.assertIn(sym, fx3_recovery.__all__)

    def test_03_o_rdonly_donor_inspection_and_spy_flag_enforcement(self) -> None:
        real_open = os.open
        opened: list[tuple[str, int]] = []

        def spy_open(path: str | bytes, flags: int, *args: object, **kwargs: object) -> int:
            opened.append((str(path), flags))
            return real_open(path, flags, *args, **kwargs)

        with mock.patch("os.open", side_effect=spy_open):
            snap = inspect_tier0_dual_layer_donors_readonly(force_clean_room=False)

        self.assertTrue(snap.all_passed, f"donor errors: {snap.errors}")
        for path_str, flags in opened:
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"non-O_RDONLY open on {path_str}")

        partinf_path = resolve_donor_path(P151_DONOR_FX3_PARTINF_RELPATH)
        if partinf_path is not None and partinf_path.is_file():
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(snap.donor_files_inspected, 11)
            self.assertEqual(snap.partinf_partition_count, 30)
            self.assertGreaterEqual(snap.mount_entry_count, 6)
            self.assertTrue(snap.setup_nflash_aliases_verified)
            self.assertTrue(snap.nor_loader_writer_markers_verified)
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_clean_room_fallback_parity_and_pinned_metadata(self) -> None:
        snap_cr = inspect_tier0_dual_layer_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_cr.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertTrue(snap_cr.all_passed)
        self.assertEqual(snap_cr.donor_files_inspected, 0)
        self.assertEqual(snap_cr.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(snap_cr.artifacts), 11)
        by_id = {a.artifact_id: a for a in snap_cr.artifacts}
        self.assertEqual(by_id["partinf_conf"].byte_length, P151_PINNED_FX3_PARTINF_BYTES)
        self.assertEqual(by_id["partinf_conf"].sha256_digest, P151_PINNED_FX3_PARTINF_SHA256)
        self.assertEqual(by_id["mount_conf"].byte_length, P151_PINNED_FX3_MOUNT_BYTES)
        self.assertEqual(by_id["mount_conf"].sha256_digest, P151_PINNED_FX3_MOUNT_SHA256)
        self.assertEqual(by_id["setup_nflash"].byte_length, P151_PINNED_FX3_SETUP_NFLASH_BYTES)
        self.assertEqual(by_id["setup_nflash"].sha256_digest, P151_PINNED_FX3_SETUP_NFLASH_SHA256)
        self.assertEqual(by_id["insmod_drv1"].byte_length, P151_PINNED_FX3_INSMOD_DRV1_BYTES)
        self.assertEqual(by_id["insmod_drv1"].sha256_digest, P151_PINNED_FX3_INSMOD_DRV1_SHA256)
        self.assertEqual(by_id["nor_loader_writer"].byte_length, P151_PINNED_FX3_NOR_LOADER_WRITER_BYTES)
        self.assertEqual(by_id["nor_loader_writer"].sha256_digest, P151_PINNED_FX3_NOR_LOADER_WRITER_SHA256)
        self.assertEqual(by_id["pformat_config"].byte_length, P151_PINNED_FX3_PFORMAT_CONFIG_BYTES)
        self.assertEqual(by_id["pformat_config"].sha256_digest, P151_PINNED_FX3_PFORMAT_CONFIG_SHA256)
        self.assertEqual(by_id["loader_nor_bin"].byte_length, P151_PINNED_FX3_LOADER_NOR_BIN_BYTES)
        self.assertEqual(by_id["loader_nor_bin"].sha256_digest, P151_PINNED_FX3_LOADER_NOR_BIN_SHA256)
        self.assertEqual(by_id["libsencore_so"].byte_length, P151_PINNED_FX3_LIBSENCORE_BYTES)
        self.assertEqual(by_id["libsencore_so"].sha256_digest, P151_PINNED_FX3_LIBSENCORE_SHA256)
        self.assertEqual(by_id["im_elf"].byte_length, P151_PINNED_FX3_IM_ELF_BYTES)
        self.assertEqual(by_id["im_elf"].sha256_digest, P151_PINNED_FX3_IM_ELF_SHA256)
        self.assertEqual(by_id["cpapp_b_bin"].byte_length, P151_PINNED_FX3_CPAPP_B_BYTES)
        self.assertEqual(by_id["cpapp_b_bin"].header_4k_sha256, P151_PINNED_FX3_CPAPP_B_HDR4K_SHA256)
        self.assertEqual(by_id["nflasha15_img"].byte_length, P151_PINNED_FX3_NFLASHA15_BYTES)
        self.assertEqual(by_id["nflasha15_img"].header_4k_sha256, P151_PINNED_FX3_NFLASHA15_HDR4K_SHA256)

    def test_05_env_force_clean_room_overrides_default_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=None)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_06_json_zero_raw_proprietary_firmware_bytes_and_no_nan(self) -> None:
        raw_byte_re = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
        for cr in (False, True):
            rep = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=cr)
            serialized = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
            self.assertIsNone(raw_byte_re.search(serialized), f"raw byte literal leaked in clean_room={cr}")
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_07_local_donor_script_and_elf_anchors_when_present(self) -> None:
        p_setup = resolve_donor_path(P151_DONOR_FX3_SETUP_NFLASH_RELPATH)
        if p_setup is None or not p_setup.is_file():
            self.skipTest("local FX3 donors not present")
        snap = inspect_tier0_dual_layer_donors_readonly(force_clean_room=False)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("pnflasha->nflasha", by_id["setup_nflash"].verified_markers)
        self.assertIn("cnflasha->nflasha", by_id["setup_nflash"].verified_markers)
        self.assertIn("crypt-emmc.ko", by_id["insmod_drv1"].verified_markers)
        self.assertIn("emmc.ko", by_id["insmod_drv1"].verified_markers)
        self.assertIn("loader_nor.bin", by_id["nor_loader_writer"].verified_markers)
        self.assertIn("ELF64_AArch64", by_id["libsencore_so"].verified_markers)
        self.assertIn("ELF64_AArch64_ET_EXEC", by_id["im_elf"].verified_markers)
        self.assertIn("ext2_0xEF53", by_id["nflasha15_img"].verified_markers)

    def test_08_missing_donor_fallback_still_fails_only_when_forced_local_and_absent(self) -> None:
        with mock.patch(
            "fx3_recovery.realhw_pnflasha_cnflasha_mtdro_tier0_vault_verifier.resolve_donor_path",
            return_value=None,
        ):
            snap = inspect_tier0_dual_layer_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_passed)

    # ------------------------------------------------------------------
    # Group A: Sector 0 Geometry, 16-Surface Vault & 8-Scenario Firewall
    # ------------------------------------------------------------------

    def test_09_fx3_30_partition_table_invariants(self) -> None:
        self.assertEqual(len(FX3_30_PARTITION_TABLE), SECTOR0_ENTRY_COUNT)
        indices = [r[0] for r in FX3_30_PARTITION_TABLE]
        self.assertEqual(indices, list(range(1, 31)))
        p1 = FX3_30_PARTITION_TABLE[0]
        self.assertEqual((p1[1], p1[2]), (0x80, 0xBF80))
        p15 = FX3_30_PARTITION_TABLE[14]
        self.assertEqual((p15[1], p15[2], p15[4]), (0x00222000, 0x000FA000, True))
        p18 = FX3_30_PARTITION_TABLE[17]
        self.assertEqual((p18[1], p18[2]), (0x0031C000, 0x0000A000))

    def test_10_sector0_30_partition_geometry_valid_roundtrip(self) -> None:
        sec0 = build_synthetic_fx3_sector0_30_partitions()
        self.assertEqual(len(sec0), SECTOR_SIZE_BYTES)
        self.assertEqual(sec0[0:4], SECTOR0_MAGIC)
        self.assertEqual(sec0[4:8], SECTOR0_VERSION)
        rep = verify_fx3_sector0_30_partition_geometry(sec0)
        self.assertTrue(rep.valid)
        self.assertEqual(rep.magic_ascii, "8246")
        self.assertEqual(rep.version_ascii, "2.00")
        self.assertEqual(rep.entry_count, 30)
        self.assertGreaterEqual(rep.active_partition_count, 13)
        self.assertFalse(rep.has_overlaps)
        self.assertTrue(rep.fx3_lba_geometry_ok)

    def test_11_sector0_rejects_fx6_p18_shift_0x312000(self) -> None:
        sec0 = build_synthetic_fx3_sector0_30_partitions(shift_p18_to_fx6=True)
        rep = verify_fx3_sector0_30_partition_geometry(sec0)
        self.assertFalse(rep.valid)
        self.assertFalse(rep.fx3_lba_geometry_ok)
        self.assertTrue(any("p18" in e for e in rep.errors))

    def test_12_sector0_rejects_truncated_bad_magic_and_overlaps(self) -> None:
        self.assertFalse(verify_fx3_sector0_30_partition_geometry(b"\x00" * 128).valid)
        bad_magic = bytearray(build_synthetic_fx3_sector0_30_partitions())
        bad_magic[0:4] = b"0000"
        self.assertFalse(verify_fx3_sector0_30_partition_geometry(bytes(bad_magic)).valid)

        overlap = bytearray(build_synthetic_fx3_sector0_30_partitions())
        # Shift p2 start_lba back into p1 [0x80, 0xC000)
        struct.pack_into("<I", overlap, 0x20 + 16, 0x00004000)
        rep_ov = verify_fx3_sector0_30_partition_geometry(bytes(overlap))
        self.assertFalse(rep_ov.valid)
        self.assertTrue(rep_ov.has_overlaps)

    def test_13_16_mandatory_tier0_surfaces_complete_and_domains_valid(self) -> None:
        self.assertEqual(len(TIER0_16_SURFACES), 16)
        self.assertEqual(len(MANDATORY_16_SURFACE_IDS), 16)
        for spec in TIER0_16_SURFACES:
            self.assertIn(spec.primary_layer_domain, VALID_LAYER_DOMAINS)
        by_id = {s.surface_id: s for s in TIER0_16_SURFACES}
        self.assertEqual(by_id["sector0"].primary_layer_domain, DOMAIN_RAW_PNFLASHA_ISP)
        self.assertEqual(by_id["p15"].primary_layer_domain, DOMAIN_SPACC_CNFLASHA_LOGICAL)
        self.assertEqual(by_id["spi_nor_mtd0ro"].primary_layer_domain, DOMAIN_SPI_NOR_MTDRO)
        self.assertEqual(by_id["emmc_ext_csd"].primary_layer_domain, DOMAIN_EMMC_REG_METADATA)

    def test_14_verify_dual_layer_16_surface_vault_happy_path(self) -> None:
        sec0, entries, samples = build_synthetic_16_surface_vault()
        rep = verify_dual_layer_16_surface_vault(sec0, entries, samples)
        self.assertTrue(rep.passed, f"unexpected errors: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(rep.surface_count, 16)
        self.assertTrue(rep.mandatory_16_complete)
        self.assertEqual(len(rep.surface_results), 16)
        self.assertIn("p15", rep.spacc_cnflasha_surfaces)
        self.assertIn("sector0", rep.raw_pnflasha_surfaces)
        self.assertEqual(rep.spi_nor_mtdro_surfaces, ("spi_nor_mtd0ro",))
        self.assertEqual(rep.emmc_reg_surfaces, ("emmc_ext_csd",))

    def test_15_vault_rejects_missing_mandatory_surface(self) -> None:
        sec0, entries, samples = build_synthetic_16_surface_vault()
        entries.pop("p18")
        rep = verify_dual_layer_16_surface_vault(sec0, entries, samples)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.mandatory_16_complete)
        self.assertIn("p18", rep.missing_surfaces)
        self.assertTrue(any(ERR_MISSING_TIER0_SURFACES in e for e in rep.errors))

    def test_16_vault_rejects_wrong_layer_domain_tagging(self) -> None:
        sec0, entries, samples = build_synthetic_16_surface_vault()
        e15 = entries["p15"]
        entries["p15"] = DualLayerSurfaceEntry(**{**e15.__dict__, "layer_domain": DOMAIN_RAW_PNFLASHA_ISP})
        rep = verify_dual_layer_16_surface_vault(sec0, entries, samples)
        self.assertFalse(rep.passed)
        self.assertTrue(any("DOMAIN_MISMATCH" in e for e in rep.errors))

    def test_17_vault_rejects_low_entropy_spacc_raw_ciphertext(self) -> None:
        sec0, entries, samples = build_synthetic_16_surface_vault()
        e15 = entries["p15"]
        entries["p15"] = DualLayerSurfaceEntry(**{**e15.__dict__, "raw_isp_entropy_bits": 4.2})
        rep = verify_dual_layer_16_surface_vault(sec0, entries, samples)
        self.assertFalse(rep.passed)
        self.assertTrue(any(ERR_INVALID_MAGIC_OR_LOW_ENTROPY in e for e in rep.errors))

    def test_18_vault_rejects_blank_00_or_ff_and_bad_ext2_magic(self) -> None:
        sec0, entries, samples = build_synthetic_16_surface_vault()
        samples_blank = dict(samples)
        samples_blank["p15"] = b"\xff" * 4096
        rep1 = verify_dual_layer_16_surface_vault(sec0, entries, samples_blank)
        self.assertFalse(rep1.passed)
        self.assertTrue(any("BLANK_OR_ERASED_FLASH_READ" in e for e in rep1.errors))

        samples_bad_ext2 = dict(samples)
        samples_bad_ext2["p15"] = build_synthetic_ext2_sample(valid_magic=False)
        rep2 = verify_dual_layer_16_surface_vault(sec0, entries, samples_bad_ext2)
        self.assertFalse(rep2.passed)
        self.assertTrue(any("BAD_EXT2_0XEF53_MAGIC" in e for e in rep2.errors))

    def test_19_synthetic_magic_helpers_coverage(self) -> None:
        ext2 = build_synthetic_ext2_sample()
        self.assertEqual(struct.unpack_from("<H", ext2, 1080)[0], EXT2_SUPER_MAGIC)
        sq = build_synthetic_squashfs_sample()
        self.assertEqual(sq[:4], b"hsqs")
        vf = build_synthetic_vfat_sample(marker=LENS_VX8900_MAGIC)
        self.assertEqual(vf[510:512], VFAT_BOOT_SIG)
        self.assertIn(LENS_VX8900_MAGIC, vf)
        bk4 = build_synthetic_bk4_sample()
        self.assertEqual(bk4[0x0C:0x10], b"BK4\x00")
        wbi = build_synthetic_wbi2_sample()
        self.assertEqual(wbi[:4], b"WBI2")
        csd = build_synthetic_ext_csd_sample()
        self.assertEqual(len(csd), 512)
        spacc = build_synthetic_high_entropy_spacc_sample(size=8192)
        self.assertEqual(len(spacc), 8192)

    def test_20_firewall_blocks_cnflasha_plaintext_to_pnflasha_raw(self) -> None:
        body = sha256(b"body-1").hexdigest()
        cid = sha256(b"cid-1").hexdigest()
        for dev in ("/dev/pnflasha15", "/dev/pnflasha3", "/dev/pnflasha8", "/dev/pnflasha23"):
            dec = evaluate_restore_target_pairing(
                source_layer_domain=DOMAIN_SPACC_CNFLASHA_LOGICAL,
                source_partition=15,
                source_body_serial_sha256=body,
                source_emmc_cid_sha256=cid,
                target_device_path=dev,
                target_body_serial_sha256=body,
                target_emmc_cid_sha256=cid,
            )
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.blocked_code, BLOCKED_CROSS_DOMAIN_CNFLASHA_TO_PNFLASHA)

    def test_21_firewall_blocks_pnflasha_ciphertext_to_cnflasha_or_nflasha_alias(self) -> None:
        body = sha256(b"body-1").hexdigest()
        cid = sha256(b"cid-1").hexdigest()
        for dev in ("/dev/cnflasha15", "/dev/nflasha15", "/dev/cnflasha3", "/dev/nflasha8"):
            dec = evaluate_restore_target_pairing(
                source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
                source_partition=15,
                source_body_serial_sha256=body,
                source_emmc_cid_sha256=cid,
                target_device_path=dev,
                target_body_serial_sha256=body,
                target_emmc_cid_sha256=cid,
                source_shannon_entropy_bits=7.95,
            )
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.blocked_code, BLOCKED_CROSS_DOMAIN_PNFLASHA_TO_CNFLASHA)

    def test_22_firewall_blocks_cross_camera_spacc_otp_mismatch(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        body_b = sha256(b"body-B").hexdigest()
        cid_b = sha256(b"cid-B").hexdigest()
        dec = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
            source_partition=15,
            source_body_serial_sha256=body_a,
            source_emmc_cid_sha256=cid_a,
            target_device_path="/dev/pnflasha15",
            target_body_serial_sha256=body_b,
            target_emmc_cid_sha256=cid_b,
            source_shannon_entropy_bits=7.97,
        )
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.blocked_code, BLOCKED_CROSS_CAMERA_SPACC_OTP_KEY_MISMATCH)

    def test_23_firewall_blocks_mtd_rw_and_all_forbidden_ioctls(self) -> None:
        body = sha256(b"body-1").hexdigest()
        cid = sha256(b"cid-1").hexdigest()
        dec_non_ro = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_SPI_NOR_MTDRO,
            source_partition=None,
            source_body_serial_sha256=body,
            source_emmc_cid_sha256=cid,
            target_device_path="/dev/mtd0",
            target_body_serial_sha256=body,
            target_emmc_cid_sha256=cid,
        )
        self.assertFalse(dec_non_ro.allowed)
        self.assertEqual(dec_non_ro.blocked_code, BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)

        for mode in FORBIDDEN_MTD_OPEN_MODES:
            dec_m = evaluate_restore_target_pairing(
                source_layer_domain=DOMAIN_SPI_NOR_MTDRO,
                source_partition=None,
                source_body_serial_sha256=body,
                source_emmc_cid_sha256=cid,
                target_device_path="/dev/mtd0ro",
                target_body_serial_sha256=body,
                target_emmc_cid_sha256=cid,
                open_mode=mode,
            )
            self.assertFalse(dec_m.allowed)
            self.assertEqual(dec_m.blocked_code, BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)

        for ioctl in FORBIDDEN_MTD_IOCTLS:
            dec_i = evaluate_restore_target_pairing(
                source_layer_domain=DOMAIN_SPI_NOR_MTDRO,
                source_partition=None,
                source_body_serial_sha256=body,
                source_emmc_cid_sha256=cid,
                target_device_path="/dev/mtd0ro",
                target_body_serial_sha256=body,
                target_emmc_cid_sha256=cid,
                ioctl_name=ioctl,
            )
            self.assertFalse(dec_i.allowed)
            self.assertEqual(dec_i.blocked_code, BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN)

    def test_24_firewall_allows_same_domain_readonly_and_blocks_write_open_mode(self) -> None:
        body = sha256(b"body-1").hexdigest()
        cid = sha256(b"cid-1").hexdigest()
        dec_ro = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
            source_partition=15,
            source_body_serial_sha256=body,
            source_emmc_cid_sha256=cid,
            target_device_path="/dev/pnflasha15",
            target_body_serial_sha256=body,
            target_emmc_cid_sha256=cid,
            open_mode="O_RDONLY",
            source_shannon_entropy_bits=7.96,
        )
        self.assertTrue(dec_ro.allowed)
        self.assertIsNone(dec_ro.blocked_code)

        dec_wr = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
            source_partition=15,
            source_body_serial_sha256=body,
            source_emmc_cid_sha256=cid,
            target_device_path="/dev/pnflasha15",
            target_body_serial_sha256=body,
            target_emmc_cid_sha256=cid,
            open_mode="O_RDWR",
            source_shannon_entropy_bits=7.96,
        )
        self.assertFalse(dec_wr.allowed)
        self.assertEqual(dec_wr.blocked_code, ERR_WRITE_AUTH_LOCKED)

    def test_25_firewall_rejects_low_entropy_raw_isp_and_dual_copy_bitrot(self) -> None:
        body = sha256(b"body-1").hexdigest()
        cid = sha256(b"cid-1").hexdigest()
        dec_ent = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
            source_partition=15,
            source_body_serial_sha256=body,
            source_emmc_cid_sha256=cid,
            target_device_path="/dev/pnflasha15",
            target_body_serial_sha256=body,
            target_emmc_cid_sha256=cid,
            source_shannon_entropy_bits=5.0,
        )
        self.assertFalse(dec_ent.allowed)
        self.assertEqual(dec_ent.blocked_code, ERR_INVALID_MAGIC_OR_LOW_ENTROPY)

        dec_rot = evaluate_restore_target_pairing(
            source_layer_domain=DOMAIN_RAW_PNFLASHA_ISP,
            source_partition=18,
            source_body_serial_sha256=body,
            source_emmc_cid_sha256=cid,
            target_device_path="/dev/pnflasha18",
            target_body_serial_sha256=body,
            target_emmc_cid_sha256=cid,
            sd_exfat_sha256="a" * 64,
            mac_host_vault_sha256="c" * 64,
            gf256_healed_ok=False,
        )
        self.assertFalse(dec_rot.allowed)
        self.assertEqual(dec_rot.blocked_code, BLOCKED_DUAL_COPY_BITROT_DETECTED)

    def test_26_gf256_rs_pq_healing_recovers_corrupted_p18_and_fails_quorum_loss(self) -> None:
        _sec0, _entries, samples = build_synthetic_16_surface_vault()
        shards = [samples["p18"][i * 512 : (i + 1) * 512] for i in range(4)]
        stripe = encode_gf256_pq_parity(shards, shard_names=[f"p18_s{i}" for i in range(4)])

        bad_s0 = bytearray(shards[0])
        bad_s0[5] ^= 0x55
        bad_s2 = bytearray(shards[2])
        bad_s2[99] ^= 0x33

        heal_2, _p, _q = heal_gf256_pq_shards(
            (bytes(bad_s0), shards[1], bytes(bad_s2), shards[3]),
            stripe.p_parity,
            stripe.q_parity,
            shard_sizes=stripe.shard_sizes,
            stripe_bytes=stripe.stripe_bytes,
            expected_shard_sha256s=stripe.shard_sha256s,
            expected_p_sha256=stripe.p_sha256,
            expected_q_sha256=stripe.q_sha256,
            shard_names=stripe.shard_names,
        )
        self.assertTrue(heal_2.passed)
        self.assertTrue(heal_2.bit_exact_match)
        self.assertEqual(heal_2.healed_indices, (0, 2))

        bad_s1 = bytearray(shards[1])
        bad_s1[10] ^= 0x11
        heal_3, _p3, _q3 = heal_gf256_pq_shards(
            (bytes(bad_s0), bytes(bad_s1), bytes(bad_s2), shards[3]),
            stripe.p_parity,
            stripe.q_parity,
            shard_sizes=stripe.shard_sizes,
            stripe_bytes=stripe.stripe_bytes,
            expected_shard_sha256s=stripe.shard_sha256s,
            expected_p_sha256=stripe.p_sha256,
            expected_q_sha256=stripe.q_sha256,
            shard_names=stripe.shard_names,
        )
        self.assertFalse(heal_3.passed)
        self.assertEqual(heal_3.status, "FAIL_TIER0_BACKUP")

    def test_27_pillar_a_8_scenario_firewall_all_pass(self) -> None:
        res = run_pillar_a_8_scenario_firewall()
        self.assertTrue(res.passed, f"PA failed: {res}")
        self.assertEqual(res.status, STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), PILLAR_A_SCENARIO_IDS)
        self.assertIn("GF256_RS_PQ_HEALED", res.scenarios[6].observed_code)

    def test_28_spacc_entropy_threshold_constant_is_7_9_bits(self) -> None:
        self.assertAlmostEqual(SPACC_CIPHERTEXT_MIN_ENTROPY_BITS, 7.9, places=4)

    # ------------------------------------------------------------------
    # Group B: /dev/mtd*ro SPI NOR & p12/p13/p18/p23/p30 Gate
    # ------------------------------------------------------------------

    def test_29_parse_proc_mtd_maps_to_ro_char_nodes(self) -> None:
        text = build_synthetic_proc_mtd_text()
        regions = parse_proc_mtd(text)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].mtd_name, "mtd0")
        self.assertEqual(regions[0].device_node_ro, "/dev/mtd0ro")
        self.assertEqual(regions[0].size_bytes, SPI_NOR_TOTAL_BYTES)
        self.assertEqual(regions[0].erasesize_bytes, SPI_NOR_ERASE_BLOCK_BYTES)
        self.assertEqual(regions[0].label, "spi-nor-boot")

    def test_30_audit_spi_nor_mtdro_happy_path(self) -> None:
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        rep = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        self.assertTrue(rep.valid, f"SPI NOR errors: {rep.errors}")
        self.assertTrue(rep.erase_aligned)
        self.assertEqual(rep.detected_boot_stages, SPI_NOR_REQUIRED_BOOT_STAGES)
        self.assertEqual(rep.missing_boot_stages, ())
        self.assertTrue(rep.dual_copy_parity_ok)
        self.assertEqual(rep.mtd_rw_opens_or_erase_ioctls, 0)
        self.assertFalse(rep.spi_nor_write_authorized)

    def test_31_audit_spi_nor_blocks_non_ro_path_and_rw_open_and_ioctl(self) -> None:
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        r1 = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        self.assertFalse(r1.valid)
        self.assertIn(BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN, r1.errors)

        r2 = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_WRONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
            ioctl_requested="MEMWRITEOOB",
        )
        self.assertFalse(r2.valid)
        self.assertIn(BLOCKED_MTD_RW_OR_MEMERASE_FORBIDDEN, r2.errors)

    def test_32_audit_spi_nor_blocks_unaligned_and_missing_boot_stages(self) -> None:
        bad = build_synthetic_spi_nor_sample(total_bytes=65535, include_all_stages=False)
        bad_sha = sha256(bad).hexdigest()
        rep = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=bad,
            sd_exfat_sha256=bad_sha,
            mac_host_vault_sha256=bad_sha,
        )
        self.assertFalse(rep.valid)
        self.assertFalse(rep.erase_aligned)
        self.assertGreaterEqual(len(rep.missing_boot_stages), 2)
        self.assertTrue(any(BLOCKED_SPI_NOR_ENVELOPE_OR_ALIGNMENT_INVALID in e for e in rep.errors))

    def test_33_audit_spi_nor_blocks_blank_flash_and_dual_copy_mismatch(self) -> None:
        blank = b"\xff" * SPI_NOR_ERASE_BLOCK_BYTES
        blank_sha = sha256(blank).hexdigest()
        r_blank = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=blank,
            sd_exfat_sha256=blank_sha,
            mac_host_vault_sha256=blank_sha,
        )
        self.assertFalse(r_blank.valid)

        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        r_rot = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256="0" * 64,
        )
        self.assertFalse(r_rot.valid)
        self.assertFalse(r_rot.dual_copy_parity_ok)
        self.assertIn(BLOCKED_DUAL_COPY_BITROT_DETECTED, r_rot.errors)

    def test_34_audit_spi_nor_supports_4k_sector_and_empty_proc_mtd_rejection(self) -> None:
        nor = build_synthetic_spi_nor_sample(total_bytes=128 * 1024 + SPI_NOR_ERASE_SECTOR_BYTES)
        nor_sha = sha256(nor).hexdigest()
        # With 4 KiB erase size in /proc/mtd, 132 KiB is erase-aligned
        rep_4k = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(erasesize_hex="00001000"),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        self.assertTrue(rep_4k.erase_aligned)

        rep_empty = audit_spi_nor_mtdro_dump(
            proc_mtd_text="dev:    size   erasesize  name\n",
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=build_synthetic_spi_nor_sample(),
            sd_exfat_sha256=sha256(build_synthetic_spi_nor_sample()).hexdigest(),
            mac_host_vault_sha256=sha256(build_synthetic_spi_nor_sample()).hexdigest(),
        )
        self.assertFalse(rep_empty.valid)
        self.assertIn("PROC_MTD_EMPTY_OR_UNPARSEABLE", rep_empty.errors)

    def test_35_factory_cal_gate_happy_path_unlocks_stage_b_human_review_only(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        _sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        nor_audit = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        gate = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertTrue(gate.passed)
        self.assertEqual(gate.status, STATUS_VERIFIED_PILLAR_B)
        self.assertTrue(gate.stage_b_human_review_eligible)
        self.assertEqual(tuple(c.surface_id for c in gate.factory_cal_checks), PER_CAMERA_CAL_SURFACE_IDS)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)

    def test_36_factory_cal_gate_blocks_p18_missing_vx8900(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        _sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
        samples["p18"] = build_synthetic_vfat_sample(marker=b"BADLENS")
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        nor_audit = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        gate = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(gate.passed)
        self.assertFalse(gate.stage_b_human_review_eligible)
        self.assertIn(BLOCKED_P18_LENS_VX8900_INTEGRITY_FAILURE, gate.errors)

    def test_37_factory_cal_gate_blocks_p23_p30_bk4_checksum_or_fx6_model(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        _sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        nor_audit = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )

        # Corrupt checksum on p23
        samples_chk = dict(samples)
        samples_chk["p23"] = build_synthetic_bk4_sample(corrupt_checksum=True)
        g_chk = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples_chk,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(g_chk.passed)
        self.assertIn(BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE, g_chk.errors)

        # Cross-SKU model ID on p30
        samples_sku = dict(samples)
        samples_sku["p30"] = build_synthetic_bk4_sample(model_id=0x91030070)
        g_sku = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples_sku,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(g_sku.passed)
        self.assertIn(BLOCKED_P23_P30_BK4_INTEGRITY_FAILURE, g_sku.errors)

    def test_38_factory_cal_gate_blocks_cross_camera_p12_p13_and_missing_surface(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        body_b = sha256(b"body-B").hexdigest()
        _sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        nor_audit = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        g_x = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples,
            target_body_serial_sha256=body_b,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(g_x.passed)
        self.assertTrue(any(BLOCKED_CROSS_CAMERA_FACTORY_CAL_LOCK in e for e in g_x.errors))

        entries_missing = dict(entries)
        entries_missing.pop("p12")
        g_m = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries_missing,
            samples=samples,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(g_m.passed)
        self.assertIn("MISSING_CAL_SURFACE:p12", g_m.errors)

    def test_39_factory_cal_gate_blocks_dual_copy_hash_mismatch_against_sample(self) -> None:
        body_a = sha256(b"body-A").hexdigest()
        cid_a = sha256(b"cid-A").hexdigest()
        _sec0, entries, samples = build_synthetic_16_surface_vault(body_serial_sha256=body_a, emmc_cid_sha256=cid_a)
        e13 = entries["p13"]
        entries["p13"] = DualLayerSurfaceEntry(**{**e13.__dict__, "mac_host_vault_sha256": "f" * 64})
        nor = build_synthetic_spi_nor_sample()
        nor_sha = sha256(nor).hexdigest()
        nor_audit = audit_spi_nor_mtdro_dump(
            proc_mtd_text=build_synthetic_proc_mtd_text(),
            device_path="/dev/mtd0ro",
            open_mode="O_RDONLY",
            spi_nor_bytes=nor,
            sd_exfat_sha256=nor_sha,
            mac_host_vault_sha256=nor_sha,
        )
        gate = verify_per_camera_factory_cal_vault_gate(
            spi_nor_audit=nor_audit,
            entries=entries,
            samples=samples,
            target_body_serial_sha256=body_a,
            target_emmc_cid_sha256=cid_a,
        )
        self.assertFalse(gate.passed)
        self.assertTrue(any(BLOCKED_DUAL_COPY_BITROT_DETECTED in e for e in gate.errors))

    def test_40_pillar_b_6_scenario_gate_all_pass(self) -> None:
        res = run_pillar_b_6_scenario_gate()
        self.assertTrue(res.passed, f"PB failed: {res}")
        self.assertEqual(res.status, STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), PILLAR_B_SCENARIO_IDS)
        self.assertTrue(res.scenarios[0].stage_b_human_review_eligible)
        for s in res.scenarios[1:]:
            self.assertFalse(s.stage_b_human_review_eligible)

    def test_41_spi_nor_and_cal_constants_sane(self) -> None:
        self.assertEqual(SPI_NOR_TOTAL_BYTES, 16 * 1024 * 1024)
        self.assertEqual(SPI_NOR_ERASE_BLOCK_BYTES, 65536)
        self.assertEqual(SPI_NOR_ERASE_SECTOR_BYTES, 4096)
        self.assertEqual(PER_CAMERA_CAL_SURFACE_IDS, ("p12", "p13", "p18", "p23", "p30"))

    # ------------------------------------------------------------------
    # Group C: Suite Determinism, CLI & >= 19 Pillar Integration
    # ------------------------------------------------------------------

    def test_42_suite_determinism_in_clean_room_and_local_donor_modes(self) -> None:
        r1 = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=True)
        r2 = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, STATUS_VERIFIED_SUITE)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.spi_nor_write_authorized)
        self.assertEqual(r1.mtd_rw_opens_or_erase_ioctls, 0)

        r_loc = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=False)
        self.assertTrue(r_loc.all_passed)
        self.assertEqual(r_loc.pillar_a_firewall_8_scenarios.scenarios_passed, 8)
        self.assertEqual(r_loc.pillar_b_gate_6_scenarios.scenarios_passed, 6)

    def test_43_cli_verify_tier0_dual_layer_vault_clean_room_json_and_out(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-tier0-dual-layer-vault", "--clean-room", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["pillar_a_firewall_8_scenarios"]["scenarios_passed"], 8)
        self.assertEqual(parsed["pillar_b_gate_6_scenarios"]["scenarios_passed"], 6)
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])

        scratch_root = ROOT / "work" / "_tests" / "phase151_cli_out"
        if scratch_root.exists():
            shutil.rmtree(scratch_root)
        scratch_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf_out = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-tier0-dual-layer-vault",
                        "--clean-room",
                        "--json",
                        "--out",
                        str(scratch_root),
                    ],
                ),
                redirect_stdout(buf_out),
            ):
                rc_out = fx3_cli.main()
            self.assertEqual(rc_out, 0)
            rep_file = scratch_root / "tier0-dual-layer-vault-report.json"
            self.assertTrue(rep_file.is_file())
            written = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"], PHASE151_SCHEMA)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_44_cli_verify_tier0_dual_layer_vault_text_and_nonzero_on_failure(self) -> None:
        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-tier0-dual-layer-vault", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_TIER0_DUAL_LAYER_VAULT_GATE", txt)
        self.assertIn("surfaces=16/16", txt)
        self.assertIn("pillar_a_scenarios=8/8", txt)
        self.assertIn("pillar_b_scenarios=6/6", txt)
        self.assertIn("mtd_rw_opens_or_erase_ioctls=0", txt)
        self.assertIn("spi_nor_write_authorized=False", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)

        rep = run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite(force_clean_room=True)
        failing = type(rep)(**{**rep.__dict__, "all_passed": False, "status": "REJECTED_FOR_TEST"})
        buf_fail = io.StringIO()
        with (
            mock.patch.object(fx3_cli, "run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite", return_value=failing),
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-tier0-dual-layer-vault", "--clean-room", "--json"]),
            redirect_stdout(buf_fail),
        ):
            rc_fail = fx3_cli.main()
        self.assertEqual(rc_fail, 2)
        self.assertFalse(json.loads(buf_fail.getvalue())["all_passed"])

    def test_45_cli_verify_all_recovery_with_phase151_reaches_at_least_19_pillars(self) -> None:
        argv_19 = [
            "fx3_recovery",
            "verify-all-recovery",
            "--clean-room",
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
            "--json",
        ]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv_19), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 19)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase151_pillar19_tier0_dual_layer_vault", parsed)

        buf_txt = io.StringIO()
        with mock.patch.object(sys, "argv", argv_19[:-1]), redirect_stdout(buf_txt):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillars=19/19", buf_txt.getvalue())

    def test_46_cli_verify_all_recovery_backward_compat_7_and_18(self) -> None:
        buf_def = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf_def),
        ):
            rc_def = fx3_cli.main()
        self.assertEqual(rc_def, 0)
        parsed_def = json.loads(buf_def.getvalue())
        self.assertEqual(parsed_def["pillar_count"], 7)
        self.assertNotIn("phase151_pillar19_tier0_dual_layer_vault", parsed_def)

        buf_18 = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
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
                    "--json",
                ],
            ),
            redirect_stdout(buf_18),
        ):
            rc_18 = fx3_cli.main()
        self.assertEqual(rc_18, 0)
        parsed_18 = json.loads(buf_18.getvalue())
        self.assertEqual(parsed_18["pillar_count"], 18)
        self.assertNotIn("phase151_pillar19_tier0_dual_layer_vault", parsed_18)


if __name__ == "__main__":
    unittest.main()
