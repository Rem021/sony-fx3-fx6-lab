"""Fast dual-mode unit tests for Phase 57 — exFAT BootChecksum, Sony Media Tree & Dual CFexpress Firewall."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.exfat_media_integrity_guard import (
    EXFAT_BOOT_CHECKSUM_SKIP_OFFSETS,
    EXFAT_FLAG_ACTIVE_FAT,
    EXFAT_FLAG_MEDIA_FAILURE,
    EXFAT_FLAG_VOLUME_DIRTY,
    EXFAT_FS_NAME,
    EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA,
    EXFAT_MEDIA_INTEGRITY_GUARD_VERSION,
    EXFAT_PERCENT_IN_USE_OFFSET,
    EXFAT_VOLUME_FLAGS_OFFSET,
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SDXC,
    MediaSlotConfig,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SLOT_A,
    SLOT_B,
    STATUS_BLOCKED_CHKDSK_FOUND_CHK_PRESENT,
    STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH,
    STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM,
    STATUS_BLOCKED_EXFAT_MEDIA_FAILURE,
    STATUS_BLOCKED_EXFAT_VBR_INVALID,
    STATUS_BLOCKED_EXFAT_VOLUME_DIRTY,
    STATUS_BLOCKED_FILESYSTEM_SEPARATION,
    STATUS_BLOCKED_NO_LAB_MEDIA_CARD,
    STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT,
    STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT,
    STATUS_VERIFIED_SAFE,
    build_synthetic_exfat_boot_region,
    build_synthetic_p1_fat12_vbr,
    compute_exfat_boot_checksum,
    evaluate_exfat_media_integrity_guard,
    inspect_sony_media_tree,
    main as module_cli_main,
    parse_exfat_vbr,
    parse_p1_fat12_fat16_vbr,
    verify_dual_slot_media_firewall,
    verify_exfat_boot_region,
    verify_exfat_image_file,
    verify_p1_vs_exfat_filesystem_separation,
)


class ExfatMediaIntegrityGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines & Package Exports ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA, "fx3-exfat-media-integrity-guard-v1")
        self.assertEqual(EXFAT_MEDIA_INTEGRITY_GUARD_VERSION, "1.0.0")
        self.assertEqual(EXFAT_BOOT_CHECKSUM_SKIP_OFFSETS, (106, 107, 112))
        for sym in (
            "EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA",
            "MediaSlotConfig",
            "compute_exfat_boot_checksum",
            "build_synthetic_exfat_boot_region",
            "parse_exfat_vbr",
            "verify_exfat_boot_region",
            "verify_exfat_image_file",
            "inspect_sony_media_tree",
            "verify_dual_slot_media_firewall",
            "parse_p1_fat12_fat16_vbr",
            "verify_p1_vs_exfat_filesystem_separation",
            "evaluate_exfat_media_integrity_guard",
            "exfat_media_integrity_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    # --- 2. Pure-Python exFAT VBR & 12-Sector BootChecksum Verifier ---

    def test_02_exfat_vbr_valid_512b_and_4096b_sectors(self) -> None:
        for bps_shift, expected_bps in ((9, 512), (12, 4096)):
            blob = build_synthetic_exfat_boot_region(
                bytes_per_sector_shift=bps_shift,
                sectors_per_cluster_shift=4,
            )
            self.assertEqual(len(blob), 24 * expected_bps)
            vbr = parse_exfat_vbr(blob[:expected_bps])
            self.assertTrue(vbr.valid)
            self.assertEqual(vbr.bytes_per_sector, expected_bps)
            self.assertEqual(vbr.sectors_per_cluster, 16)
            self.assertEqual(vbr.bytes_per_cluster, expected_bps * 16)
            self.assertTrue(vbr.sector_shift_power_of_two_ok)
            self.assertTrue(vbr.cluster_shift_power_of_two_ok)
            self.assertTrue(vbr.file_system_name_ok)
            self.assertTrue(vbr.must_be_zero_ok)
            self.assertTrue(vbr.boot_signature_ok)
            self.assertFalse(vbr.volume_dirty)
            self.assertFalse(vbr.media_failure)

            res = verify_exfat_boot_region(blob)
            self.assertTrue(res.valid)
            self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
            self.assertTrue(res.main_checksum_ok)
            self.assertTrue(res.backup_checksum_ok)
            self.assertTrue(res.main_vs_backup_consistent)

    def test_03_exfat_vbr_rejects_bad_filesystem_name_and_fat32_spoof(self) -> None:
        for bad_name in (b"FAT32   ", b"NTFS    ", b"exfat   "):
            blob = bytearray(build_synthetic_exfat_boot_region())
            blob[3:11] = bad_name
            vbr = parse_exfat_vbr(bytes(blob[:512]))
            self.assertFalse(vbr.valid)
            self.assertFalse(vbr.file_system_name_ok)
            self.assertEqual(vbr.status, STATUS_BLOCKED_EXFAT_VBR_INVALID)

    def test_04_exfat_vbr_rejects_nonzero_must_be_zero_and_bad_boot_sig(self) -> None:
        blob_mbz = bytearray(build_synthetic_exfat_boot_region())
        blob_mbz[20] = 0x01
        vbr_mbz = parse_exfat_vbr(bytes(blob_mbz[:512]))
        self.assertFalse(vbr_mbz.valid)
        self.assertFalse(vbr_mbz.must_be_zero_ok)
        self.assertEqual(vbr_mbz.status, STATUS_BLOCKED_EXFAT_VBR_INVALID)

        blob_sig = bytearray(build_synthetic_exfat_boot_region())
        blob_sig[510:512] = b"\x00\x00"
        vbr_sig = parse_exfat_vbr(bytes(blob_sig[:512]))
        self.assertFalse(vbr_sig.valid)
        self.assertFalse(vbr_sig.boot_signature_ok)
        self.assertEqual(vbr_sig.status, STATUS_BLOCKED_EXFAT_VBR_INVALID)

    def test_05_exfat_vbr_rejects_invalid_sector_and_cluster_shifts(self) -> None:
        for bad_bps_shift in (8, 13, 255):
            blob = bytearray(build_synthetic_exfat_boot_region())
            blob[108] = bad_bps_shift
            vbr = parse_exfat_vbr(bytes(blob[:512]))
            self.assertFalse(vbr.valid)
            self.assertFalse(vbr.sector_shift_power_of_two_ok)
            self.assertEqual(vbr.status, STATUS_BLOCKED_EXFAT_VBR_INVALID)

        # Cluster size > 32 MiB (shift 9 + 17 = 26 > 25)
        blob_spc = bytearray(build_synthetic_exfat_boot_region())
        blob_spc[109] = 17
        vbr_spc = parse_exfat_vbr(bytes(blob_spc[:512]))
        self.assertFalse(vbr_spc.valid)
        self.assertFalse(vbr_spc.cluster_shift_power_of_two_ok)

    def test_06_exfat_vbr_rejects_invalid_geometry_and_fat_count(self) -> None:
        # FatOffset < 24 overlaps boot area
        b1 = bytearray(build_synthetic_exfat_boot_region())
        struct.pack_into("<I", b1, 80, 12)
        self.assertFalse(parse_exfat_vbr(bytes(b1[:512])).geometry_ok)

        # ClusterHeapOffset overlaps FAT
        b2 = bytearray(build_synthetic_exfat_boot_region())
        struct.pack_into("<I", b2, 88, 30)  # fat_offset=24, fat_length=16 -> min 40
        self.assertFalse(parse_exfat_vbr(bytes(b2[:512])).geometry_ok)

        # ActiveFat=1 with NumberOfFats=1
        b3 = bytearray(build_synthetic_exfat_boot_region())
        struct.pack_into("<H", b3, EXFAT_VOLUME_FLAGS_OFFSET, EXFAT_FLAG_ACTIVE_FAT)
        self.assertFalse(parse_exfat_vbr(bytes(b3[:512])).valid)

        # NumberOfFats=3
        b4 = bytearray(build_synthetic_exfat_boot_region())
        b4[110] = 3
        self.assertFalse(parse_exfat_vbr(bytes(b4[:512])).valid)

    def test_07_boot_checksum_skips_volumeflags_106_107_and_percent_in_use_112(self) -> None:
        clean = build_synthetic_exfat_boot_region()
        chk_clean = compute_exfat_boot_checksum(clean[: 11 * 512], 512)

        mutated = bytearray(clean[: 11 * 512])
        mutated[106] = 0x03  # VolumeFlags low byte (ActiveFat + VolumeDirty)
        mutated[107] = 0x80  # VolumeFlags high byte
        mutated[112] = 73    # PercentInUse
        chk_mutated = compute_exfat_boot_checksum(bytes(mutated), 512)
        self.assertEqual(chk_clean, chk_mutated)

        # Verify verify_exfat_boot_region confirms checksum_ok even when VolumeDirty=1
        dirty_24 = bytearray(clean)
        struct.pack_into("<H", dirty_24, EXFAT_VOLUME_FLAGS_OFFSET, EXFAT_FLAG_VOLUME_DIRTY)
        dirty_24[EXFAT_PERCENT_IN_USE_OFFSET] = 42
        res_allow = verify_exfat_boot_region(bytes(dirty_24), allow_volume_dirty=True)
        self.assertTrue(res_allow.main_checksum_ok)
        self.assertTrue(res_allow.backup_checksum_ok)
        self.assertTrue(res_allow.volume_dirty)

    def test_08_boot_checksum_detects_single_bit_flip_in_sectors_0_to_10(self) -> None:
        base = build_synthetic_exfat_boot_region()
        for offset in (100, 512 * 5 + 16, 512 * 9 + 4, 512 * 10 + 128):
            corrupted = bytearray(base)
            corrupted[offset] ^= 0x01
            res = verify_exfat_boot_region(bytes(corrupted))
            self.assertFalse(res.valid, f"Expected failure at offset {offset}")
            self.assertFalse(res.main_checksum_ok)
            self.assertIn(STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM, res.violation_codes)

    def test_09_boot_checksum_detects_non_uniform_sector11_checksum_slot(self) -> None:
        corrupted = bytearray(build_synthetic_exfat_boot_region())
        # Flip last 32-bit word of Sector 11
        corrupted[12 * 512 - 4] ^= 0xFF
        res = verify_exfat_boot_region(bytes(corrupted))
        self.assertFalse(res.valid)
        self.assertFalse(res.main_checksum_sector_uniform)
        self.assertFalse(res.main_checksum_ok)
        self.assertIn(STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM, res.violation_codes)

    def test_10_backup_boot_region_checksum_and_consistency_check(self) -> None:
        # 12-sector-only fails when require_backup_region=True, passes when False
        only_12 = build_synthetic_exfat_boot_region(include_backup_region=False)
        res_req = verify_exfat_boot_region(only_12, require_backup_region=True)
        self.assertFalse(res_req.valid)
        self.assertIn(STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH, res_req.violation_codes)

        res_opt = verify_exfat_boot_region(only_12, require_backup_region=False)
        self.assertTrue(res_opt.valid)

        # Corrupt Backup Sector 23 checksum
        corrupt_bkp = bytearray(build_synthetic_exfat_boot_region())
        corrupt_bkp[23 * 512] ^= 0x10
        res_bkp_chk = verify_exfat_boot_region(bytes(corrupt_bkp))
        self.assertFalse(res_bkp_chk.valid)
        self.assertFalse(res_bkp_chk.backup_checksum_ok)
        self.assertIn(STATUS_BLOCKED_EXFAT_BOOT_CHECKSUM, res_bkp_chk.violation_codes)

        # Backup VBR valid checksum on its own, but diverges from Main VBR serial
        diverged = bytearray(build_synthetic_exfat_boot_region())
        bkp_start = 12 * 512
        struct.pack_into("<I", diverged, bkp_start + 100, 0xDEADBEEF)
        new_bkp_chk = compute_exfat_boot_checksum(
            bytes(diverged[bkp_start : bkp_start + 11 * 512]), 512
        )
        diverged[bkp_start + 11 * 512 : bkp_start + 12 * 512] = struct.pack("<I", new_bkp_chk) * 128
        res_div = verify_exfat_boot_region(bytes(diverged))
        self.assertFalse(res_div.valid)
        self.assertFalse(res_div.main_vs_backup_consistent)
        self.assertIn(STATUS_BLOCKED_EXFAT_BACKUP_MISMATCH, res_div.violation_codes)

    def test_11_exfat_extended_boot_signatures_check(self) -> None:
        no_ext = build_synthetic_exfat_boot_region(extended_boot_signatures=False)
        res_warn = verify_exfat_boot_region(no_ext, require_extended_boot_signatures=False)
        self.assertTrue(res_warn.valid)
        self.assertFalse(res_warn.main_extended_signatures_ok)
        self.assertTrue(len(res_warn.warnings) >= 1)

        res_strict = verify_exfat_boot_region(no_ext, require_extended_boot_signatures=True)
        self.assertFalse(res_strict.valid)
        self.assertIn(STATUS_BLOCKED_EXFAT_VBR_INVALID, res_strict.violation_codes)

    def test_12_volume_dirty_and_media_failure_block_even_with_valid_checksum(self) -> None:
        dirty_main = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_VOLUME_DIRTY)
        res_dm = verify_exfat_boot_region(dirty_main)
        self.assertFalse(res_dm.valid)
        self.assertTrue(res_dm.volume_dirty)
        self.assertTrue(res_dm.main_checksum_ok)
        self.assertEqual(res_dm.status, STATUS_BLOCKED_EXFAT_VOLUME_DIRTY)

        dirty_bkp = build_synthetic_exfat_boot_region(
            volume_flags=0,
            backup_volume_flags=EXFAT_FLAG_VOLUME_DIRTY,
        )
        res_db = verify_exfat_boot_region(dirty_bkp)
        self.assertFalse(res_db.valid)
        self.assertTrue(res_db.volume_dirty)
        self.assertEqual(res_db.status, STATUS_BLOCKED_EXFAT_VOLUME_DIRTY)

        media_fail = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_MEDIA_FAILURE)
        res_mf = verify_exfat_boot_region(media_fail)
        self.assertFalse(res_mf.valid)
        self.assertTrue(res_mf.media_failure)
        self.assertEqual(res_mf.status, STATUS_BLOCKED_EXFAT_MEDIA_FAILURE)

    def test_13_o_rdonly_image_file_audit_uses_strict_os_open(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            img_path = Path(td) / "clean_exfat.img"
            img_path.write_bytes(build_synthetic_exfat_boot_region())
            observed_flags = []
            orig_open = os.open

            def spy_open(path, flags, *args, **kwargs):
                observed_flags.append((str(path), flags))
                return orig_open(path, flags, *args, **kwargs)

            with patch("os.open", side_effect=spy_open):
                res = verify_exfat_image_file(img_path)

            self.assertTrue(res.valid)
            self.assertGreaterEqual(len(observed_flags), 1)
            for p, fl in observed_flags:
                if "clean_exfat.img" in p:
                    self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)

    # --- 3. Sony Media Tree (`XDROOT` vs `M4ROOT` + `.RSV`) & Production Card Firewall ---

    def test_14_sony_media_tree_detects_fx6_xdroot_mxf_clips(self) -> None:
        res = inspect_sony_media_tree(
            entries=[
                ("XDROOT/MEDIAPRO.XML", 2048),
                ("XDROOT/Clip/A001C001_261114.MXF", 524288000),
                ("XDROOT/Sub/A001C001S01.MXF", 10485760),
            ]
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.is_clean_lab_media)
        self.assertEqual(res.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)
        self.assertIn("FX6_XDROOT", res.detected_trees)
        self.assertEqual(len(res.fx6_xdroot_mxf_clips), 2)
        self.assertEqual(res.total_production_bytes, 524288000 + 10485760)

    def test_15_sony_media_tree_detects_fx3_private_m4root_and_cfex_m4root_mp4_clips(self) -> None:
        # SDXC layout: PRIVATE/M4ROOT/CLIP/*.MP4
        res_sd = inspect_sony_media_tree(
            entries=[
                ("PRIVATE/M4ROOT/MEDIAPRO.XML", 1024),
                ("PRIVATE/M4ROOT/CLIP/C0001.MP4", 134217728),
                ("PRIVATE/M4ROOT/SUB/C0001S01.MP4", 4194304),
            ]
        )
        self.assertFalse(res_sd.valid)
        self.assertEqual(res_sd.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)
        self.assertIn("FX3_PRIVATE_M4ROOT", res_sd.detected_trees)
        self.assertEqual(len(res_sd.fx3_m4root_mp4_clips), 2)

        # CFexpress Type A layout: M4ROOT/CLIP/*.MP4
        res_cf = inspect_sony_media_tree(
            entries=[("M4ROOT/CLIP/C0042.MP4", 67108864)]
        )
        self.assertFalse(res_cf.valid)
        self.assertEqual(res_cf.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)
        self.assertIn("FX3_M4ROOT", res_cf.detected_trees)

    def test_16_sony_media_tree_detects_unfinalized_rsv_power_loss_clips(self) -> None:
        for rsv_path, rsv_size in (
            ("PRIVATE/M4ROOT/CLIP/C0009.RSV", 209715200),
            ("M4ROOT/CLIP/C0010.rsv", 1024),
            ("XDROOT/Clip/A002C001.RSV", 0),
        ):
            res = inspect_sony_media_tree(entries=[(rsv_path, rsv_size)])
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT)
            self.assertIn(rsv_path, res.unfinalized_rsv_files)

    def test_17_sony_media_tree_detects_chkdsk_found000_and_dcim_media(self) -> None:
        res_chk = inspect_sony_media_tree(
            entries=[("FOUND.000/FILE0000.CHK", 16384)]
        )
        self.assertFalse(res_chk.valid)
        self.assertEqual(res_chk.status, STATUS_BLOCKED_CHKDSK_FOUND_CHK_PRESENT)

        res_dcim = inspect_sony_media_tree(
            entries=[("DCIM/100MSDCF/DSC00001.ARW", 52428800)]
        )
        self.assertFalse(res_dcim.valid)
        self.assertEqual(res_dcim.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)

    def test_18_sony_media_tree_allows_blank_and_fresh_empty_camera_tree_and_lab_markers(self) -> None:
        # Blank card
        res_blank = inspect_sony_media_tree(entries=())
        self.assertTrue(res_blank.valid)
        self.assertTrue(res_blank.is_clean_lab_media)

        # Freshly camera-formatted empty M4ROOT + lab BODYDATA.DAT + 0-byte stub warning only
        res_fresh = inspect_sony_media_tree(
            entries=[
                ("BODYDATA.DAT", 4096),
                ("PRIVATE/M4ROOT/MEDIAPRO.XML", 512),
                ("PRIVATE/M4ROOT/CLIP/EMPTY_STUB.MP4", 0),
            ]
        )
        self.assertTrue(res_fresh.valid)
        self.assertTrue(res_fresh.is_clean_lab_media)
        self.assertEqual(res_fresh.zero_byte_clip_stubs, ("PRIVATE/M4ROOT/CLIP/EMPTY_STUB.MP4",))
        self.assertTrue(len(res_fresh.warnings) >= 1)

    def test_19_sony_media_tree_real_directory_walk_in_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            clip_dir = root / "XDROOT" / "Clip"
            clip_dir.mkdir(parents=True)
            (clip_dir / "A001C001.MXF").write_bytes(b"\x06\x0e\x2b\x34" * 16)
            res = inspect_sony_media_tree(card_root=root)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT)
            self.assertEqual(res.fx6_xdroot_mxf_clips, ("XDROOT/Clip/A001C001.MXF",))

        with tempfile.TemporaryDirectory() as td_clean:
            res_clean = inspect_sony_media_tree(card_root=Path(td_clean))
            self.assertTrue(res_clean.valid)
            self.assertTrue(res_clean.is_clean_lab_media)

    def test_20_dual_slot_firewall_blocks_production_card_in_slot_b_while_slot_a_clean(self) -> None:
        clean_boot = build_synthetic_exfat_boot_region()
        slot_a = MediaSlotConfig(
            slot_id=SLOT_A,
            inserted=True,
            media_type=MEDIA_TYPE_CFEXPRESS_A,
            exfat_boot_bytes=clean_boot,
            card_entries=(),
            dedicated_lab_card=True,
        )
        for bad_entries, expected_code in (
            ([("XDROOT/Clip/A001C001.MXF", 4096)], STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT),
            ([("PRIVATE/M4ROOT/CLIP/C0001.MP4", 4096)], STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT),
            ([("PRIVATE/M4ROOT/CLIP/C0002.RSV", 4096)], STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT),
        ):
            slot_b = MediaSlotConfig(
                slot_id=SLOT_B,
                inserted=True,
                media_type=MEDIA_TYPE_SDXC,
                device_node="/dev/mmcblk2p1",
                mount_point="/mnt/slot_b",
                exfat_boot_bytes=clean_boot,
                card_entries=bad_entries,
                dedicated_lab_card=True,
            )
            fw = verify_dual_slot_media_firewall(slot_a=slot_a, slot_b=slot_b)
            self.assertFalse(fw.valid)
            self.assertFalse(fw.h0_h1_trial_entry_allowed)
            self.assertIn(expected_code, fw.violation_codes)

    def test_21_dual_slot_firewall_blocks_dirty_or_corrupt_exfat_in_either_slot(self) -> None:
        clean_boot = build_synthetic_exfat_boot_region()
        dirty_boot = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_VOLUME_DIRTY)
        fw = verify_dual_slot_media_firewall(
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=True, exfat_boot_bytes=clean_boot),
            slot_b=MediaSlotConfig(
                slot_id=SLOT_B,
                inserted=True,
                device_node="/dev/mmcblk2p1",
                mount_point="/mnt/slot_b",
                exfat_boot_bytes=dirty_boot,
            ),
        )
        self.assertFalse(fw.valid)
        self.assertFalse(fw.h0_h1_trial_entry_allowed)
        self.assertIn(STATUS_BLOCKED_EXFAT_VOLUME_DIRTY, fw.violation_codes)

    def test_22_dual_slot_firewall_requires_dedicated_lab_card_and_allows_dual_clean(self) -> None:
        clean_boot = build_synthetic_exfat_boot_region()

        # Unconfirmed card -> blocked
        fw_unconf = verify_dual_slot_media_firewall(
            slot_a=MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                exfat_boot_bytes=clean_boot,
                dedicated_lab_card=False,
            ),
            slot_b=MediaSlotConfig(slot_id=SLOT_B, inserted=False),
        )
        self.assertFalse(fw_unconf.valid)
        self.assertIn(STATUS_BLOCKED_NO_LAB_MEDIA_CARD, fw_unconf.violation_codes)

        # Both empty when lab card required -> blocked
        fw_empty = verify_dual_slot_media_firewall(
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=False),
            slot_b=MediaSlotConfig(slot_id=SLOT_B, inserted=False),
            require_at_least_one_lab_card=True,
        )
        self.assertFalse(fw_empty.valid)
        self.assertIn(STATUS_BLOCKED_NO_LAB_MEDIA_CARD, fw_empty.violation_codes)

        # Both slots clean dedicated lab cards -> allowed
        fw_both = verify_dual_slot_media_firewall(
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=True, exfat_boot_bytes=clean_boot),
            slot_b=MediaSlotConfig(
                slot_id=SLOT_B,
                inserted=True,
                media_type=MEDIA_TYPE_SDXC,
                device_node="/dev/mmcblk2p1",
                mount_point="/mnt/slot_b",
                exfat_boot_bytes=clean_boot,
            ),
        )
        self.assertTrue(fw_both.valid)
        self.assertTrue(fw_both.h0_h1_trial_entry_allowed)
        self.assertEqual(fw_both.inserted_lab_slots, (SLOT_A, SLOT_B))

    # --- 4. Internal `p1` (`FAT12`/`FAT16`) vs External `exFAT` Separation ---

    def test_23_p1_vbr_validates_fat12_and_fat16_and_rejects_exfat_or_fat32(self) -> None:
        for ft in ("FAT12", "FAT16"):
            res = parse_p1_fat12_fat16_vbr(build_synthetic_p1_fat12_vbr(fat_type=ft))
            self.assertTrue(res.valid)
            self.assertEqual(res.fat_type, ft)
            self.assertFalse(res.is_exfat_spoofed)

        # Spoof EXFAT onto p1 -> blocked
        exfat_spoof = build_synthetic_exfat_boot_region()[:512]
        res_ex = parse_p1_fat12_fat16_vbr(exfat_spoof)
        self.assertFalse(res_ex.valid)
        self.assertTrue(res_ex.is_exfat_spoofed)
        self.assertIn(STATUS_BLOCKED_FILESYSTEM_SEPARATION, res_ex.violation_codes)

        # Invalid BootSignature -> blocked
        bad_sig = bytearray(build_synthetic_p1_fat12_vbr())
        bad_sig[510:512] = b"\x00\x00"
        res_bad = parse_p1_fat12_fat16_vbr(bytes(bad_sig))
        self.assertFalse(res_bad.valid)
        self.assertIn(STATUS_BLOCKED_P1_FAILSAFE_VBR_INVALID, res_bad.violation_codes)

    def test_24_filesystem_separation_donor_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_cur = verify_p1_vs_exfat_filesystem_separation()
        self.assertTrue(res_cur.valid)
        self.assertEqual(res_cur.p1_filesystem, "FAT12")
        self.assertIn(res_cur.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        for p, fl in observed_flags:
            if "nflasha1" in p:
                self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)

        res_clean = verify_p1_vs_exfat_filesystem_separation(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.p1_filesystem, "FAT12")

    def test_25_filesystem_separation_blocks_emmc_overlap_and_cross_domain_writes(self) -> None:
        # Slot A pointing at /dev/nflasha1
        r1 = verify_p1_vs_exfat_filesystem_separation(
            force_clean_room=True,
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=True, device_node="/dev/nflasha1"),
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_FILESYSTEM_SEPARATION, r1.violation_codes)

        # Planned write targeting p1 /setting or cross-domain exfat mount on nflasha1
        r2 = verify_p1_vs_exfat_filesystem_separation(
            force_clean_room=True,
            planned_mounts=["mount -t exfat /dev/nflasha1 /mnt/slot_a"],
            planned_writes=["/dev/nflasha1"],
        )
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_FILESYSTEM_SEPARATION, r2.violation_codes)
        self.assertGreaterEqual(len(r2.blocked_cross_domain_targets), 2)

        # Slot A & Slot B sharing device_node
        r3 = verify_p1_vs_exfat_filesystem_separation(
            force_clean_room=True,
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=True, device_node="/dev/mmcblk1p1"),
            slot_b=MediaSlotConfig(slot_id=SLOT_B, inserted=True, device_node="/dev/mmcblk1p1", mount_point="/mnt/slot_b"),
        )
        self.assertFalse(r3.valid)
        self.assertIn(STATUS_BLOCKED_FILESYSTEM_SEPARATION, r3.violation_codes)

    def test_26_persistent_emmc_write_redline_always_blocked(self) -> None:
        res = evaluate_exfat_media_integrity_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(res.all_passed)
        self.assertFalse(res.h0_h1_trial_entry_allowed)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # --- 5. Unified Evaluator & Dual-Mode CLI ---

    def test_27_unified_evaluator_passes_in_local_and_clean_room_modes(self) -> None:
        rep_cur = evaluate_exfat_media_integrity_guard()
        self.assertTrue(rep_cur.all_passed)
        self.assertTrue(rep_cur.h0_h1_trial_entry_allowed)
        self.assertEqual(rep_cur.status, STATUS_VERIFIED_SAFE)
        self.assertFalse(rep_cur.persistent_emmc_writes_authorized)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep_cr = evaluate_exfat_media_integrity_guard()
        self.assertTrue(rep_cr.all_passed)
        self.assertTrue(rep_cr.clean_room_forced)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep_cr.h0_h1_trial_entry_allowed)

    def test_28_unified_evaluator_blocks_h0_h1_on_media_or_separation_fault(self) -> None:
        dirty_boot = build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_VOLUME_DIRTY)
        rep_dirty = evaluate_exfat_media_integrity_guard(
            force_clean_room=True,
            slot_a=MediaSlotConfig(slot_id=SLOT_A, inserted=True, exfat_boot_bytes=dirty_boot),
        )
        self.assertFalse(rep_dirty.all_passed)
        self.assertFalse(rep_dirty.h0_h1_trial_entry_allowed)
        self.assertEqual(rep_dirty.status, STATUS_BLOCKED_EXFAT_VOLUME_DIRTY)

        rep_rsv = evaluate_exfat_media_integrity_guard(
            force_clean_room=True,
            slot_a=MediaSlotConfig(
                slot_id=SLOT_A,
                inserted=True,
                exfat_boot_bytes=build_synthetic_exfat_boot_region(),
                card_entries=[("M4ROOT/CLIP/C0005.RSV", 8192)],
            ),
        )
        self.assertFalse(rep_rsv.all_passed)
        self.assertFalse(rep_rsv.h0_h1_trial_entry_allowed)
        self.assertEqual(rep_rsv.status, STATUS_BLOCKED_UNFINALIZED_RSV_PRESENT)

    def test_29_package_cli_verify_media_guard_json_and_clean_room(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-media-guard", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], EXFAT_MEDIA_INTEGRITY_GUARD_SCHEMA)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_passed"])
        self.assertTrue(payload["h0_h1_trial_entry_allowed"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertNotIn("b'", buf.getvalue())

    def test_30_cli_fail_closed_on_dirty_image_and_production_card_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dirty_img = root / "slot_a_dirty.img"
            dirty_img.write_bytes(build_synthetic_exfat_boot_region(volume_flags=EXFAT_FLAG_VOLUME_DIRTY))
            card_dir = root / "card_a"
            (card_dir / "XDROOT" / "Clip").mkdir(parents=True)
            (card_dir / "XDROOT" / "Clip" / "A001C001.MXF").write_bytes(b"\x00" * 64)

            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    [
                        "verify-media-guard",
                        "--clean-room",
                        "--slot-a-image",
                        str(dirty_img),
                        "--slot-a-root",
                        str(card_dir),
                        "--json",
                    ]
                )
            self.assertEqual(rc_fail, 1)
            fail_json = json.loads(buf_fail.getvalue())
            self.assertFalse(fail_json["all_passed"])
            self.assertFalse(fail_json["h0_h1_trial_entry_allowed"])
            self.assertIn(STATUS_BLOCKED_EXFAT_VOLUME_DIRTY, fail_json["violation_codes"])
            self.assertIn(STATUS_BLOCKED_PRODUCTION_CLIP_PRESENT, fail_json["violation_codes"])

        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        self.assertIn("status=VERIFIED_SAFE", buf_mod.getvalue())
        self.assertIn("h0_h1_trial_entry_allowed=True", buf_mod.getvalue())


if __name__ == "__main__":
    unittest.main()
