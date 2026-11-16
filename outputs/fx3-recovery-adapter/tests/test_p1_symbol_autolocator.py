"""Tests for Phase 25 Version-Independent p1 4-Site AArch64 Autolocator.

Covers both Clean-Room synthetic ELF64/FAT12/SquashFS/Unicorn tests (always active,
including `FX3_FX6_FORCE_CLEAN_ROOM=1`) and O_RDONLY real FX3 2.04/2.05 donor
verification (exact match with 0x9fd4, 0xabf0, 0xd208, 0xd27c).
"""

from __future__ import annotations

from hashlib import md5, sha256
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fx3_recovery.fat import FatP1, MAX_P1
from fx3_recovery.files import is_clean_room_or_donor_unavailable, read_file, resolve_donor_path
from fx3_recovery.p1_symbol_autolocator import (
    AUTOLOCATOR_SCHEMA,
    LIB_SD,
    LIB_UC,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    READ_ONLY_DONOR_ACCESS,
    REFERENCE_SITE_OFFSETS,
    AutolocatorError,
    Elf64Image,
    apply_autolocated_patches,
    autolocate_4_sites,
    autolocate_sdfileinput_sites,
    autolocate_updatercorecommon_sites,
    build_synthetic_p1_elf64_libraries,
    build_synthetic_p1_fat12_squashfs_image,
    build_synthetic_squashfs,
    inspect_donor_p1_readonly,
    rebase_elf64_vma,
    rollback_autolocated_patches,
    run_autolocated_p1_roundtrip,
    verify_sites_in_unicorn,
)
from fx3_recovery.squash import SquashFS

REFERENCES = resolve_donor_path(
    "fx3-color-port-20261027/input-20261028/original-update-engine",
    sentinel_relpath="2.05/nflasha1",
    require_file=True,
)


class P1SymbolAutolocatorTests(unittest.TestCase):
    def test_01_safety_constants_hard_locked(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)

    def test_02_elf64_parser_rejects_malformed_headers(self) -> None:
        with self.assertRaises(AutolocatorError):
            Elf64Image(b"not-elf")
        # 32-bit ELF rejected
        elf32 = bytearray(128)
        elf32[:6] = b"\x7fELF\x01\x01"
        with self.assertRaises(AutolocatorError):
            Elf64Image(bytes(elf32))
        # x86_64 ELF64 rejected (expected EM_AARCH64=183)
        x86 = bytearray(128)
        x86[:7] = b"\x7fELF\x02\x01\x01"
        struct.pack_into("<HHI", x86, 16, 3, 62, 1)
        with self.assertRaises(AutolocatorError):
            Elf64Image(bytes(x86))
        # Truncated phoff rejected
        sd, _ = build_synthetic_p1_elf64_libraries()
        bad = bytearray(sd)
        struct.pack_into("<H", bad, 56, 200)
        with self.assertRaises(AutolocatorError):
            Elf64Image(bytes(bad))

    def test_03_elf64_parser_vaddr_offset_mapping_with_vma_bias(self) -> None:
        sd, _ = build_synthetic_p1_elf64_libraries(shift_sd=0x140, vma_bias=0x40000)
        elf = Elf64Image(sd)
        sym = elf.find_unique_defined_symbol(lambda s: "isVersionOK" in s.name, "isVersionOK")
        self.assertIsNotNone(sym.file_offset)
        assert sym.file_offset is not None
        self.assertEqual(sym.st_value - sym.file_offset, 0x40000)
        self.assertEqual(elf.vaddr_to_offset(sym.st_value), sym.file_offset)
        self.assertEqual(elf.offset_to_vaddr(sym.file_offset), sym.st_value)
        self.assertIsNone(elf.vaddr_to_offset(0xDEAD0000))

    def test_04_autolocator_synthetic_baseline_and_preserved_regions(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0, shift_uc=0, vma_bias=0)
        rep = autolocate_4_sites(sd, uc, require_plt_cross_check=True)
        self.assertEqual(rep.schema, AUTOLOCATOR_SCHEMA)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(len(rep.sites), 4)
        self.assertTrue(rep.preserved_checks["isModelOK_and_isRegionOK_untouched"])
        self.assertTrue(rep.sites["VerifySignature"].plt_cross_checked)
        self.assertTrue(rep.sites["chkFirmInfo_before_reject_ret"].plt_cross_checked)

    def test_05_autolocator_tracks_shifted_v702_plus_0x140_and_plus_0x280(self) -> None:
        sd0, uc0 = build_synthetic_p1_elf64_libraries(shift_sd=0, shift_uc=0, vma_bias=0x10000)
        sd1, uc1 = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280, vma_bias=0x80000)
        r0 = autolocate_4_sites(sd0, uc0, require_plt_cross_check=True)
        r1 = autolocate_4_sites(sd1, uc1, require_plt_cross_check=True)
        self.assertEqual(r1.sites["isVersionOK"].patch_offset - r0.sites["isVersionOK"].patch_offset, 0x140)
        self.assertEqual(r1.sites["VerifySignature"].patch_offset - r0.sites["VerifySignature"].patch_offset, 0x140)
        self.assertEqual(
            r1.sites["chkFirmInfo_before_reject_ret"].patch_offset
            - r0.sites["chkFirmInfo_before_reject_ret"].patch_offset,
            0x280,
        )
        self.assertEqual(
            r1.sites["chkFirmInfo_before_cmp_csinv"].patch_offset
            - r0.sites["chkFirmInfo_before_cmp_csinv"].patch_offset,
            0x280,
        )
        self.assertTrue(r1.warnings)  # Non-reference offsets noted

    def test_06_autolocator_tracks_large_shifts_and_high_vma(self) -> None:
        sd0, uc0 = build_synthetic_p1_elf64_libraries(shift_sd=0, shift_uc=0, vma_bias=0x10000)
        sd2, uc2 = build_synthetic_p1_elf64_libraries(shift_sd=0x3C0, shift_uc=0x700, vma_bias=0x200000)
        r0 = autolocate_4_sites(sd0, uc0)
        r2 = autolocate_4_sites(sd2, uc2)
        self.assertEqual(r2.sites["isVersionOK"].patch_offset - r0.sites["isVersionOK"].patch_offset, 0x3C0)
        self.assertEqual(
            r2.sites["chkFirmInfo_before_cmp_csinv"].patch_offset
            - r0.sites["chkFirmInfo_before_cmp_csinv"].patch_offset,
            0x700,
        )
        self.assertEqual(r2.sites["isVersionOK"].patch_vaddr - r2.sites["isVersionOK"].patch_offset, 0x200000)

    def test_07_rejects_missing_isVersionOK_symbol_fail_closed(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries()
        broken = sd.replace(b"isVersionOK", b"isVerXXXXXX")
        with self.assertRaises(AutolocatorError):
            autolocate_sdfileinput_sites(broken)

    def test_08_rejects_missing_VerifySignature_symbol_fail_closed(self) -> None:
        sd, _ = build_synthetic_p1_elf64_libraries()
        broken = sd.replace(b"VerifySignature", b"VerifyXXXXXXXXX")
        with self.assertRaises(AutolocatorError):
            autolocate_sdfileinput_sites(broken)

    def test_09_rejects_missing_chkFirmInfo_before_symbol_fail_closed(self) -> None:
        _, uc = build_synthetic_p1_elf64_libraries()
        broken = uc.replace(b"chkFirmInfo_before", b"chkFirmInfo_XXXXXX")
        with self.assertRaises(AutolocatorError):
            autolocate_updatercorecommon_sites(broken)

    def test_10_rejects_duplicate_dynsym_symbol_ambiguity_fail_closed(self) -> None:
        sd, _ = build_synthetic_p1_elf64_libraries()
        elf = Elf64Image(sd)
        # Rename isRegionOK's string to match isVersionOK? Instead mutate st_name in .dynsym of isRegionOK to isVersionOK's st_name!
        ver_sym = elf.find_unique_defined_symbol(lambda s: "isVersionOK" in s.name, "isVersionOK")
        reg_sym = elf.find_unique_defined_symbol(lambda s: "isRegionOK" in s.name, "isRegionOK")
        dynsym = elf.sections_by_name[".dynsym"]
        ver_st_name = struct.unpack_from("<I", sd, dynsym.sh_offset + ver_sym.index * 24)[0]
        amb = bytearray(sd)
        struct.pack_into("<I", amb, dynsym.sh_offset + reg_sym.index * 24, ver_st_name)
        with self.assertRaises(AutolocatorError):
            autolocate_sdfileinput_sites(bytes(amb))

    def test_11_rejects_ambiguous_multi_match_in_chkFirmInfo_before(self) -> None:
        _sd, uc_amb = build_synthetic_p1_elf64_libraries(duplicate_pattern_ambiguous=True)
        with self.assertRaises(AutolocatorError) as ctx:
            autolocate_updatercorecommon_sites(uc_amb)
        self.assertIn("expected 1 unique match", str(ctx.exception))

    def test_12_rejects_corrupted_prologue_fail_closed(self) -> None:
        sd_bad, uc_bad = build_synthetic_p1_elf64_libraries(corrupt_prologue=True)
        with self.assertRaises(AutolocatorError):
            autolocate_sdfileinput_sites(sd_bad)
        with self.assertRaises(AutolocatorError):
            autolocate_updatercorecommon_sites(uc_bad)

    def test_13_rejects_patch_outside_text_section(self) -> None:
        sd, _ = build_synthetic_p1_elf64_libraries()
        elf = Elf64Image(sd)
        text = elf.sections_by_name[".text"]
        # Shrink .text sh_size so VerifySignature falls outside .text
        bad = bytearray(sd)
        struct.pack_into("<Q", bad, elf.e_shoff + text.index * 64 + 32, 0x20)
        with self.assertRaises(AutolocatorError):
            autolocate_sdfileinput_sites(bytes(bad))

    def test_14_rejects_wrong_plt_target_when_cross_checked(self) -> None:
        _, uc = build_synthetic_p1_elf64_libraries()
        # Rename `remove` in dynstr to `unlink` (same length 6) -> PLT cross-check rejects mismatch
        bad = uc.replace(b"\x00remove\x00", b"\x00unlink\x00", 1)
        with self.assertRaises(AutolocatorError):
            autolocate_updatercorecommon_sites(bad, require_plt_cross_check=True)

    def test_15_apply_and_rollback_patches_byte_exact_sha256(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280)
        rep = autolocate_4_sites(sd, uc)
        sd_sites = [rep.sites["isVersionOK"], rep.sites["VerifySignature"]]
        uc_sites = [rep.sites["chkFirmInfo_before_reject_ret"], rep.sites["chkFirmInfo_before_cmp_csinv"]]

        sd_pat = apply_autolocated_patches(sd, sd_sites)
        uc_pat = apply_autolocated_patches(uc, uc_sites)
        self.assertNotEqual(sha256(sd_pat).hexdigest(), sha256(sd).hexdigest())
        self.assertNotEqual(sha256(uc_pat).hexdigest(), sha256(uc).hexdigest())

        sd_rb = rollback_autolocated_patches(sd_pat, sd_sites)
        uc_rb = rollback_autolocated_patches(uc_pat, uc_sites)
        self.assertEqual(sha256(sd_rb).hexdigest(), sha256(sd).hexdigest())
        self.assertEqual(sha256(uc_rb).hexdigest(), sha256(uc).hexdigest())

    def test_16_apply_patches_rejects_already_patched_or_tampered_bytes(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries()
        rep = autolocate_4_sites(sd, uc)
        sd_sites = [rep.sites["isVersionOK"], rep.sites["VerifySignature"]]
        sd_pat = apply_autolocated_patches(sd, sd_sites)
        with self.assertRaises(ValueError):
            apply_autolocated_patches(sd_pat, sd_sites)
        with self.assertRaises(ValueError):
            rollback_autolocated_patches(sd, sd_sites)

    def test_17_unicorn_aarch64_shifted_v702_all_4_sites_orig_patched_rollback(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280, vma_bias=0x50000)
        rep = autolocate_4_sites(sd, uc, require_plt_cross_check=True)
        u_rep = verify_sites_in_unicorn(sd, uc, rep.sites)
        self.assertTrue(u_rep.unicorn_available)
        self.assertTrue(u_rep.all_passed, u_rep.errors)
        for sid in REFERENCE_SITE_OFFSETS:
            self.assertTrue(u_rep.sites[sid].passed, u_rep.sites[sid].details)
            self.assertTrue(u_rep.sites[sid].preserved_ok)

    def test_18_unicorn_aarch64_isVersionOK_upgrade_vs_downgrade_semantics(self) -> None:
        import unicorn
        from unicorn import arm64_const

        sd, _ = build_synthetic_p1_elf64_libraries(shift_sd=0x140, vma_bias=0x20000)
        s_ver, _ = autolocate_sdfileinput_sites(sd)
        elf = Elf64Image(sd)
        mu = unicorn.Uc(unicorn.UC_ARCH_ARM64, unicorn.UC_MODE_ARM)
        for seg in elf.segments:
            start_p = (0x100000 + seg.p_vaddr) & ~0xFFF
            end_p = ((0x100000 + seg.p_vaddr + seg.p_memsz) + 0xFFF) & ~0xFFF
            mu.mem_map(start_p, end_p - start_p, unicorn.UC_PROT_ALL)
            mu.mem_write(0x100000 + seg.p_vaddr, sd[seg.p_offset : seg.p_offset + seg.p_filesz])
        mu.mem_map(0x40000000, 0x1000)
        mu.mem_map(0x50000000, 0x1000)
        mu.mem_map(0x7FFF0000, 0x2000)

        # Upgrade: current 0x0205, update 0x0702 -> original returns 1
        info = bytearray(0x40)
        struct.pack_into("<I", info, 0x04, 0x0205)
        struct.pack_into("<I", info, 0x1C, 0x0702)
        mu.mem_write(0x40000000, bytes(info))
        mu.reg_write(arm64_const.UC_ARM64_REG_SP, 0x7FFF1000)
        mu.reg_write(arm64_const.UC_ARM64_REG_X1, 0x40000000)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, 0x50000000)
        mu.emu_start(0x100000 + s_ver.patch_vaddr, 0x50000000, count=32)
        self.assertEqual(mu.reg_read(arm64_const.UC_ARM64_REG_W0), 1)

        # Downgrade: current 0x0702, update 0x0205 -> original returns 0
        struct.pack_into("<I", info, 0x04, 0x0702)
        struct.pack_into("<I", info, 0x1C, 0x0205)
        mu.mem_write(0x40000000, bytes(info))
        mu.reg_write(arm64_const.UC_ARM64_REG_X1, 0x40000000)
        mu.reg_write(arm64_const.UC_ARM64_REG_X30, 0x50000000)
        mu.emu_start(0x100000 + s_ver.patch_vaddr, 0x50000000, count=32)
        self.assertEqual(mu.reg_read(arm64_const.UC_ARM64_REG_W0), 0)

    def test_19_squashfs_z_sync_flush_builder_and_bounded_parse(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280)
        sq = build_synthetic_squashfs({LIB_SD: sd, LIB_UC: uc})
        fs = SquashFS(sq)
        rows = {r["path"]: r for r in fs.walk()}
        self.assertIn(LIB_SD, rows)
        self.assertIn(LIB_UC, rows)
        self.assertEqual(fs.contents(rows[LIB_SD]), sd)
        self.assertEqual(fs.contents(rows[LIB_UC]), uc)

    def test_20_p1_fat12_squashfs_roundtrip_shifted_v702_with_2pass_sha256_rollback(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280, vma_bias=0x30000)
        p1_raw = build_synthetic_p1_fat12_squashfs_image(sd, uc)
        fat = FatP1(p1_raw)
        self.assertIn("/boot/initrd.img", fat.files)
        rt = run_autolocated_p1_roundtrip(p1_raw)
        self.assertTrue(rt.byte_length_invariant)
        self.assertTrue(rt.squashfs_readback_ok)
        self.assertTrue(rt.rollback_verified)
        self.assertEqual(rt.pass1_rollback_sha256, rt.source_sha256)
        self.assertEqual(rt.pass2_rollback_sha256, rt.source_sha256)
        self.assertNotEqual(rt.candidate_sha256, rt.source_sha256)
        self.assertFalse(rt.persistent_emmc_writes_authorized)

    def test_21_p1_roundtrip_fails_closed_on_tampered_checksum(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries()
        p1_raw = build_synthetic_p1_fat12_squashfs_image(sd, uc)
        fat = FatP1(p1_raw)
        bad = bytearray(p1_raw)
        chk_off = fat.mapping("/p1chksum")[0][0]
        bad[chk_off] = ord("0") if bad[chk_off] != ord("0") else ord("1")
        with self.assertRaises(ValueError):
            run_autolocated_p1_roundtrip(bytes(bad))

    def test_22_autolocator_report_is_serializable_and_deterministic(self) -> None:
        sd, uc = build_synthetic_p1_elf64_libraries(shift_sd=0x140, shift_uc=0x280)
        r_a = autolocate_4_sites(sd, uc)
        r_b = autolocate_4_sites(sd, uc)
        self.assertEqual(
            {k: v.patch_offset for k, v in r_a.sites.items()},
            {k: v.patch_offset for k, v in r_b.sites.items()},
        )
        self.assertEqual(
            {k: v.original_bytes_hex for k, v in r_a.sites.items()},
            {k: v.original_bytes_hex for k, v in r_b.sites.items()},
        )

    @unittest.skipIf(
        is_clean_room_or_donor_unavailable([REFERENCES / v / "nflasha1" for v in ("2.04", "2.05")]),
        "Clean-room mode or external FX3 2.04/2.05 donor images absent",
    )
    def test_23_real_fx3_204_205_donors_readonly_exact_4_sites_unicorn_and_roundtrip(self) -> None:
        for ver in ("2.04", "2.05"):
            p1_path = REFERENCES / ver / "nflasha1"
            before_sha = sha256(read_file(p1_path, MAX_P1)).hexdigest()
            rep = inspect_donor_p1_readonly(p1_path)
            self.assertEqual(rep["p1_sha256"], before_sha)
            self.assertEqual(rep["roundtrip"]["located_offsets"], REFERENCE_SITE_OFFSETS)
            self.assertTrue(rep["autolocator"]["preserved_checks"]["isModelOK_and_isRegionOK_untouched"])
            self.assertTrue(rep["unicorn"]["all_passed"], rep["unicorn"]["errors"])
            self.assertTrue(rep["roundtrip"]["byte_length_invariant"])
            self.assertTrue(rep["roundtrip"]["squashfs_readback_ok"])
            self.assertTrue(rep["roundtrip"]["rollback_verified"])
            self.assertEqual(
                sha256(read_file(p1_path, MAX_P1)).hexdigest(),
                before_sha,
                f"Donor {ver} nflasha1 mutated!",
            )

    @unittest.skipIf(
        is_clean_room_or_donor_unavailable([REFERENCES / "2.05" / "nflasha1"]),
        "Clean-room mode or external FX3 2.05 donor image absent",
    )
    def test_24_real_fx3_205_donor_rebased_vma_autolocation_and_unicorn(self) -> None:
        raw_p1 = read_file(REFERENCES / "2.05" / "nflasha1", MAX_P1)
        fat = FatP1(raw_p1)
        fs = SquashFS(fat.contents("/boot/initrd.img"))
        rows = {r["path"]: r for r in fs.walk()}
        sd_rebased = rebase_elf64_vma(fs.contents(rows[LIB_SD]), 0x80000)
        uc_rebased = rebase_elf64_vma(fs.contents(rows[LIB_UC]), 0x120000)

        rep = autolocate_4_sites(sd_rebased, uc_rebased, require_plt_cross_check=True)
        self.assertEqual({k: v.patch_offset for k, v in rep.sites.items()}, REFERENCE_SITE_OFFSETS)
        self.assertEqual(rep.sites["isVersionOK"].patch_vaddr, 0x80000 + 0x9FD4)
        self.assertEqual(rep.sites["chkFirmInfo_before_cmp_csinv"].patch_vaddr, 0x120000 + 0xD27C)

        u_rep = verify_sites_in_unicorn(sd_rebased, uc_rebased, rep.sites)
        self.assertTrue(u_rep.all_passed, u_rep.errors)


if __name__ == "__main__":
    unittest.main()
