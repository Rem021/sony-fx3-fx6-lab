#!/usr/bin/env python3
"""Phase 167 Test Suite — Stage 29 (`29/29`) Real-Hardware Main Track Part 12:
`CXD90057` (`Mira`) + `CXD90058` (`Cetus`) Dual-BIONZ-XR Inter-SoC IPC, `sabin` SA-DSP,
`XAVC-I / XAVC S-I / XAVC HS (HEVC)` Codec Bridge & `H0 == H3` Factory Seal HIL Co-Emulator.

Exercises 46 fast dual-mode unit, integration, Pillar A-D HIL, GF(256) RAID-6 math,
16/16 H0==H3 factory seal, Stage 29 suite orchestration (`29/29` stages), CLI, runtime-budget,
and clean-room hygiene checks.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_cxd90058_sabin_codec_and_seal_coemulator as p167  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_default_audit() -> dict:
    key = ("default", p167.is_forced_clean_room())
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p167.run_phase167_realhw_cxd90058_sabin_seal_hil(env=os.environ)
    return _AUDIT_CACHE[key]


def _get_clean_room_audit() -> dict:
    key = ("clean_room", True)
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p167.run_phase167_realhw_cxd90058_sabin_seal_hil(
            force_clean_room=True,
            env=os.environ,
        )
    return _AUDIT_CACHE[key]


class TestStage29DualModeDonorsAndRedlines(unittest.TestCase):
    """Dual-mode O_RDONLY donor inspection, parity contracts & hard-locked safety redlines."""

    def test_01_donor_path_resolution_honors_clean_room_toggle(self) -> None:
        self.assertTrue(p167.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p167.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "0"}))
        paths_clean = p167.resolve_phase167_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 10)
        for p in paths_clean.values():
            self.assertIn(p167.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_02_clean_room_synthetic_fixtures_valid_cpapp_elf_and_bk4(self) -> None:
        fx = p167.build_clean_room_phase167_fixtures()
        self.assertEqual(len(fx), 10)
        for k in ("fx3_libmpr", "fx6_libmpr", "fx3_sencore", "fx6_sencore", "fx3_im_elf", "fx6_im_elf"):
            self.assertEqual(fx[k][:4], b"\x7fELF")
        self.assertEqual(fx["fx3_backup"][12:16], b"BK4\x00")
        self.assertEqual(fx["fx6_backup"][12:16], b"BK4\x00")
        self.assertIn(b"/usr/sabin/aed_dic1.bin", fx["fx3_cpapp"])
        self.assertNotIn(b"MoniFpga_StartStopSDI", fx["fx3_cpapp"])
        self.assertIn(b"MoniFpga_StartStopSDI", fx["fx6_cpapp"])

    def test_03_clean_room_donor_audit_verifies_all_10_donors(self) -> None:
        da = p167.inspect_phase167_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da.access_mode, "O_RDONLY")
        self.assertEqual(da.donor_files_inspected, 10)
        self.assertTrue(da.all_contracts_verified, msg=str(da.errors))
        self.assertEqual(da.errors, ())

    def test_04_default_mode_donor_audit_passes_in_current_env(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        da = rep["donor_audit"]
        self.assertTrue(da["all_contracts_verified"], msg=str(da["errors"]))
        self.assertEqual(da["donor_files_inspected"], 10)
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_05_cpapp_arm32_entry_and_fx6_exclusive_mew_absent_in_fx3(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertTrue(da["fx3_cpapp"]["arm32_entry_ok"])
        self.assertTrue(da["fx6_cpapp"]["arm32_entry_ok"])
        self.assertEqual(da["fx3_cpapp"]["load_base_hex"], "0x00108000")
        self.assertEqual(da["fx6_cpapp"]["load_base_hex"], "0x00108000")
        self.assertTrue(da["fx6_exclusive_mew_absent_in_fx3_cp"])
        self.assertEqual(da["fx3_cpapp"]["fx6_exclusive_hits"]["Mew"], 0)
        self.assertEqual(da["fx6_cpapp"]["fx6_exclusive_hits"]["Mew"], 1)

    def test_06_elf_parity_libmpr_libsencore_im_elf_and_backup_bk4(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertEqual(da["fx3_libmpr"]["export_count"], p167.EXPECTED_FX3_LIBMPR_EXPORTS)
        self.assertEqual(da["fx6_libmpr"]["export_count"], p167.EXPECTED_FX6_LIBMPR_EXPORTS)
        self.assertTrue(da["sencore_symbol_parity"])
        self.assertEqual(da["fx3_sencore"]["export_count"], 355)
        self.assertEqual(da["fx3_sencore"]["import_count"], 130)
        self.assertTrue(da["im_elf_abi_zero_diff"])
        self.assertEqual(da["fx3_im_elf"]["export_count"], 11)
        self.assertEqual(da["fx3_im_elf"]["import_count"], 85)
        self.assertEqual(da["fx3_backup"]["magic_ascii"], "BK4")
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

    def test_07_hard_locked_safety_redlines_enforced(self) -> None:
        for rep in (_get_clean_room_audit(), _get_default_audit()):
            red = rep["redlines"]
            self.assertTrue(red["p8_cp_mutation_forbidden"])
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["cp_mutation_bytes"], 0)
            self.assertEqual(red["cxd90058_mutation_bytes"], 0)
            self.assertEqual(red["wbi_mutation_bytes"], 0)
            self.assertEqual(red["calibration_mutation_bytes"], 0)
            self.assertEqual(red["nvram_persistent_writes"], 0)
            self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertEqual(red["emmc_nflasha_write_count"], 0)
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertEqual(red["otp_write_count"], 0)
            self.assertEqual(red["rpmb_write_count"], 0)
            self.assertEqual(red["orig_residual_count"], 0)
            self.assertEqual(red["tmp_jiritsu_residual_count"], 0)
            self.assertEqual(red["p6_chunk_residual_count"], 0)
            self.assertEqual(red["ipc_deadlocks"], 0)
            self.assertEqual(red["appfw_crashes"], 0)
            self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_08_donor_cache_returns_identical_audit_object(self) -> None:
        a1 = p167.inspect_phase167_donors(force_clean_room=True)
        a2 = p167.inspect_phase167_donors(force_clean_room=True)
        self.assertIs(a1, a2)


class TestStage29PillarACxd90058DualSocIpcAndMemcfg(unittest.TestCase):
    """Pillar A — CXD90057 <-> CXD90058 Dual-SoC IPC & 1,724.00 MiB memcfg= pool."""

    def test_09_memcfg_pool_validates_exact_1724_mib_non_overlapping(self) -> None:
        res = p167.verify_memcfg_pool_layout(p167.EXPECTED_RUNTIME_MEMCFG_SPEC)
        self.assertTrue(res.valid)
        self.assertEqual(res.region_count, 4)
        self.assertEqual(res.total_bytes, p167.EXPECTED_MEMCFG_TOTAL_BYTES)
        self.assertEqual(res.total_mib, 1724.0)
        self.assertTrue(res.pairwise_non_overlapping)
        self.assertTrue(res.exact_1724_mib_match)
        self.assertEqual(res.status_code, "MEMCFG_1724MIB_NON_OVERLAPPING_OK")

    def test_10_memcfg_rejects_empty_overlap_wrong_cache_and_size_mismatch(self) -> None:
        self.assertFalse(p167.verify_memcfg_pool_layout(()).valid)
        self.assertEqual(p167.verify_memcfg_pool_layout(()).status_code, "MEMCFG_EMPTY_POOL_REJECTED")
        non_uc = (
            (0x04C00000, 0x00400000, "wb"),
            (0x09000000, 0x07000000, "uc"),
            (0x1B800000, 0x24800000, "uc"),
            (0x80000000, 0x40000000, "uc"),
        )
        self.assertFalse(p167.verify_memcfg_pool_layout(non_uc).valid)
        overlap = (
            (0x04C00000, 0x00500000, "uc"),
            (0x05000000, 0x00400000, "uc"),
            (0x1B800000, 0x24800000, "uc"),
            (0x80000000, 0x40000000, "uc"),
        )
        ov_res = p167.verify_memcfg_pool_layout(overlap)
        self.assertFalse(ov_res.valid)
        self.assertFalse(ov_res.pairwise_non_overlapping)
        self.assertEqual(ov_res.status_code, "MEMCFG_OVERLAP_DETECTED")
        mismatch = (
            (0x04C00000, 0x00200000, "uc"),
            (0x09000000, 0x07000000, "uc"),
            (0x1B800000, 0x24800000, "uc"),
            (0x80000000, 0x40000000, "uc"),
        )
        self.assertFalse(p167.verify_memcfg_pool_layout(mismatch).valid)

    def test_11_sustained_4k120_ipc_link_zero_deadlock_and_cp_immutable(self) -> None:
        ipc = p167.simulate_cxd90057_cxd90058_4k120_ipc_link()
        self.assertTrue(ipc.valid)
        self.assertEqual(ipc.frames_executed, 240)
        self.assertEqual(ipc.tx_packets, 480)
        self.assertEqual(ipc.rx_completions, 480)
        self.assertEqual(ipc.ipc_deadlocks, 0)
        self.assertEqual(ipc.mailbox_stalls, 0)
        self.assertEqual(ipc.cxd90058_mutation_bytes, 0)
        self.assertEqual(ipc.cp_mutation_bytes, 0)
        self.assertEqual(ipc.cp_sha256_before, ipc.cp_sha256_after)
        self.assertTrue(ipc.cp_immutability_verified)
        self.assertEqual(ipc.status_code, "DUAL_SOC_4K120P_IPC_LOCKFREE_OK")

    def test_12_ipc_doorbell_stall_fails_closed_and_bad_args_raise(self) -> None:
        stalled = p167.simulate_cxd90057_cxd90058_4k120_ipc_link(inject_doorbell_stall=True)
        self.assertFalse(stalled.valid)
        self.assertGreater(stalled.ipc_deadlocks, 0)
        self.assertGreater(stalled.mailbox_stalls, 0)
        self.assertEqual(stalled.status_code, "IPC_DEADLOCK_OR_STALL")
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.simulate_cxd90057_cxd90058_4k120_ipc_link(frames_to_run=0)
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.simulate_cxd90057_cxd90058_4k120_ipc_link(ring_capacity=0)

    def test_13_cxd90058_mutation_guard_blocks_all_forbidden_cp_targets(self) -> None:
        for target in p167.FORBIDDEN_CP_MUTATION_TARGETS:
            g = p167.evaluate_cxd90058_mutation_guard(target)
            self.assertTrue(g.blocked, msg=f"Expected block for {target}")
            self.assertEqual(g.cxd90058_mutation_bytes, 0)
            self.assertEqual(g.cp_mutation_bytes, 0)
            self.assertEqual(g.status_code, "BLOCKED_P8_CXD90058_CP_READONLY")
        non_cp = p167.evaluate_cxd90058_mutation_guard("/tmp/vm_scratch/frame.bin")
        self.assertFalse(non_cp.blocked)
        self.assertEqual(non_cp.status_code, "NON_CP_TARGET")

    def test_14_pillar_a_integrated_evaluation_passes(self) -> None:
        pa = _get_clean_room_audit()["pillar_a_cxd90058_memcfg_4k120_ipc"]
        self.assertTrue(pa["passed"])
        self.assertTrue(pa["memcfg_pool_1724mib"]["exact_1724_mib_match"])
        self.assertFalse(pa["memcfg_overlap_rejected"]["valid"])
        self.assertTrue(pa["dual_soc_4k120p_ipc_run"]["valid"])
        self.assertFalse(pa["doorbell_stall_fault_detected"]["valid"])
        self.assertTrue(pa["cxd90058_mutation_guard"]["blocked"])


class TestStage29PillarBSabinSadspAndCodecBridge(unittest.TestCase):
    """Pillar B — sabin 32-bit SA-DSP & XAVC-I / XAVC S-I / XAVC HS / 16-bit SDI RAW gate."""

    def test_15_sabin_sadsp_window_verified_inside_memcfg_no_cpimg_overlap(self) -> None:
        res = p167.audit_sabin_sadsp_microcode()
        self.assertTrue(res.valid)
        self.assertEqual(res.bank1_window_start_hex, "0x809139000")
        self.assertEqual(res.bank1_window_end_hex, "0x809178fff")
        self.assertEqual(res.window_bytes, 0x40000)
        self.assertTrue(res.within_memcfg_pool)
        self.assertTrue(res.non_overlapping_with_cpimg)
        self.assertEqual(res.dictionaries_verified, len(p167.SABIN_ACTIVE_DICTIONARY_PATHS))
        self.assertEqual(res.status_code, "SABIN_32BIT_SADSP_WINDOW_VERIFIED")

    def test_16_sabin_sadsp_rejects_cpimg_overlap_and_out_of_memcfg_bounds(self) -> None:
        ov = p167.audit_sabin_sadsp_microcode(bank1_base_addr=p167.CPIMG_BANK1_WINDOW_BASE_32)
        self.assertFalse(ov.valid)
        self.assertFalse(ov.non_overlapping_with_cpimg)
        self.assertEqual(ov.status_code, "SABIN_WINDOW_CONFLICT")
        oob = p167.audit_sabin_sadsp_microcode(bank1_base_addr=0x04000000)
        self.assertFalse(oob.valid)
        self.assertFalse(oob.within_memcfg_pool)

    def test_17_codec_bridge_admits_xavc_i_xavc_si_and_xavc_hs_presets(self) -> None:
        admitted_ids = (
            "XAVC_I_MXF_4K_59P",
            "XAVC_I_MXF_4K_24P",
            "XAVC_SI_MP4_4K_120P",
            "XAVC_HS_HEVC_4K_60P",
            "XAVC_HS_HEVC_4K_120P",
        )
        for pid in admitted_ids:
            r = p167.evaluate_codec_preset_bridge(pid)
            self.assertTrue(r.valid)
            self.assertTrue(r.request_admitted, msg=f"Expected admit for {pid}")
            self.assertFalse(r.request_blocked_fail_closed)
            self.assertEqual(r.appfw_crashes, 0)
            self.assertEqual(r.sdi_raw_fpga_faults, 0)
            self.assertTrue(r.status_code.startswith("LIBMPR_BRIDGE_ADMITTED_"))

    def test_18_codec_bridge_fail_closes_fx6_16bit_sdi_raw_without_appfw_crash(self) -> None:
        sdi = p167.evaluate_codec_preset_bridge("FX6_SDI_RAW_16BIT_MEW")
        self.assertTrue(sdi.valid)
        self.assertFalse(sdi.request_admitted)
        self.assertTrue(sdi.request_blocked_fail_closed)
        self.assertEqual(sdi.sdi_raw_fpga_faults, 0)
        self.assertEqual(sdi.appfw_crashes, 0)
        self.assertEqual(sdi.bit_depth, 16)
        self.assertEqual(sdi.status_code, "FX6_EXCLUSIVE_MEW_SDI_RAW_BLOCKED_SAFE")

    def test_19_codec_bridge_unknown_preset_raises_explicit_error(self) -> None:
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.evaluate_codec_preset_bridge("NONEXISTENT_CODEC_PRESET")

    def test_20_pillar_b_integrated_evaluation_passes(self) -> None:
        pb = _get_clean_room_audit()["pillar_b_sabin_sadsp_and_xavc_codec_bridge"]
        self.assertTrue(pb["passed"])
        self.assertTrue(pb["sabin_sadsp_audit"]["valid"])
        self.assertFalse(pb["sabin_cpimg_overlap_rejected"]["valid"])
        self.assertTrue(pb["xavc_i_mxf_4k_59p"]["request_admitted"])
        self.assertTrue(pb["xavc_hs_hevc_4k_120p"]["request_admitted"])
        self.assertTrue(pb["fx6_sdi_raw_16bit_mew_fail_closed"]["request_blocked_fail_closed"])


class TestStage29PillarCRaid6Gf256SelfHeal(unittest.TestCase):
    """Pillar C — Dual-Media Tier-0 Cold-Backup RAID-6 GF(256) bit-rot self-heal."""

    def test_21_gf256_primitive_poly_0x11d_field_axioms(self) -> None:
        self.assertEqual(p167.gf256_mul(0, 0xAB), 0)
        self.assertEqual(p167.gf256_mul(0xAB, 0), 0)
        self.assertEqual(p167.gf256_mul(0x57, 0x83), p167.gf256_mul(0x83, 0x57))
        for a in range(1, 256):
            inv = p167.GF256_INV[a]
            self.assertEqual(p167.gf256_mul(a, inv), 1)
            self.assertEqual(p167.gf256_div(a, a), 1)
            self.assertEqual(p167.gf256_div(0, a), 0)
        with self.assertRaises(ZeroDivisionError):
            p167.gf256_div(1, 0)

    def test_22_raid6_encode_validates_non_empty_and_equal_lengths(self) -> None:
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.encode_raid6_gf256_pq(())
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.encode_raid6_gf256_pq((b"aaaa", b"bb"))

    def test_23_raid6_healthy_fast_path_requires_no_heal(self) -> None:
        shards = p167._build_tier0_cold_backup_shards()
        shas = tuple(hashlib.sha256(s).hexdigest() for s in shards)
        p_par, q_par = p167.encode_raid6_gf256_pq(shards)
        ok, healed, bad_idx, status = p167.reconstruct_raid6_gf256_in_ram(shards, p_par, q_par, shas)
        self.assertTrue(ok)
        self.assertEqual(bad_idx, ())
        self.assertEqual(status, "RAID6_HEALTHY_NO_HEAL_NEEDED")
        self.assertEqual(healed, shards)

    def test_24_raid6_heals_single_data_or_data_plus_parity_corruption(self) -> None:
        shards = p167._build_tier0_cold_backup_shards()
        shas = tuple(hashlib.sha256(s).hexdigest() for s in shards)
        p_par, q_par = p167.encode_raid6_gf256_pq(shards)

        corrupted = list(shards)
        corrupted[4] = bytes(b ^ 0x5A for b in corrupted[4])

        for p_bad, q_bad in ((False, False), (True, False), (False, True)):
            ok, healed, bad_idx, status = p167.reconstruct_raid6_gf256_in_ram(
                corrupted, p_par, q_par, shas, p_corrupted=p_bad, q_corrupted=q_bad
            )
            self.assertTrue(ok)
            self.assertEqual(bad_idx, (4,))
            self.assertEqual(status, "RAID6_GF256_BIT_EXACT_HEALED_IN_RAM")
            self.assertEqual(healed[4], shards[4])

    def test_25_raid6_heals_every_pair_of_corrupted_tier0_shards_bit_exact(self) -> None:
        shards = p167._build_tier0_cold_backup_shards(shard_bytes=256)
        shas = tuple(hashlib.sha256(s).hexdigest() for s in shards)
        p_par, q_par = p167.encode_raid6_gf256_pq(shards)
        n = len(shards)
        for i in range(n):
            for j in range(i + 1, n):
                corrupted = list(shards)
                corrupted[i] = b"\x00" * len(shards[i])
                corrupted[j] = b"\xFF" * len(shards[j])
                ok, healed, bad_idx, status = p167.reconstruct_raid6_gf256_in_ram(
                    corrupted, p_par, q_par, shas
                )
                self.assertTrue(ok, msg=f"Pair ({i},{j}) failed")
                self.assertEqual(bad_idx, (i, j))
                self.assertEqual(status, "RAID6_GF256_BIT_EXACT_HEALED_IN_RAM")
                self.assertEqual(healed, shards)

    def test_26_raid6_drill_blocks_stage_a_before_heal_then_heals_11_of_11(self) -> None:
        res = p167.run_raid6_two_chunk_bitrot_self_heal_drill((5, 9))
        self.assertTrue(res.valid)
        self.assertEqual(res.total_data_shards, 11)
        self.assertEqual(res.corrupted_shard_indices, (5, 9))
        self.assertEqual(res.corrupted_shard_names, ("boot_b", "cnflasha_spacc"))
        self.assertFalse(res.stage_a_staging_authorized_before_heal)
        self.assertTrue(res.heal_succeeded)
        self.assertEqual(res.shards_bit_exact_matched, 11)
        self.assertTrue(res.stage_a_staging_authorized_after_heal)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(res.status_code, "RAID6_GF256_BIT_EXACT_HEALED_IN_RAM")

    def test_27_raid6_three_chunk_quorum_loss_fails_closed_and_bad_index_raises(self) -> None:
        loss3 = p167.run_raid6_two_chunk_bitrot_self_heal_drill((1, 5, 9))
        self.assertTrue(loss3.valid)
        self.assertFalse(loss3.heal_succeeded)
        self.assertFalse(loss3.stage_a_staging_authorized_before_heal)
        self.assertFalse(loss3.stage_a_staging_authorized_after_heal)
        self.assertEqual(loss3.status_code, "UNRECOVERABLE_QUORUM_LOSS_GE_3")
        with self.assertRaises(p167.RealHwCxd90058SabinSealError):
            p167.run_raid6_two_chunk_bitrot_self_heal_drill((99,))

    def test_28_pillar_c_integrated_evaluation_passes(self) -> None:
        pc = _get_clean_room_audit()["pillar_c_raid6_gf256_cold_backup_self_heal"]
        self.assertTrue(pc["passed"])
        self.assertTrue(pc["two_chunk_bitrot_healed"]["heal_succeeded"])
        self.assertTrue(pc["edge_pair_bitrot_healed"]["heal_succeeded"])
        self.assertFalse(pc["three_chunk_quorum_loss_fail_closed"]["heal_succeeded"])


class TestStage29PillarDH0ToH3FactorySealAndWarranty(unittest.TestCase):
    """Pillar D — End-to-end H0 -> H1 -> H2 -> H3 16/16 Factory Seal & Zero-Residual Audit."""

    def test_29_clean_16_of_16_factory_seal_and_zero_residuals(self) -> None:
        seal = p167.audit_h0_to_h3_factory_seal()
        self.assertTrue(seal.valid)
        self.assertEqual(seal.epochs_verified, p167.FOUR_EPOCHS)
        self.assertEqual(seal.surfaces_total, 16)
        self.assertEqual(seal.surfaces_matched, 16)
        self.assertTrue(seal.h0_equals_h3)
        self.assertEqual(seal.orig_residual_count, 0)
        self.assertEqual(seal.tmp_jiritsu_residual_count, 0)
        self.assertEqual(seal.p6_chunk_residual_count, 0)
        self.assertEqual(seal.otp_write_count, 0)
        self.assertEqual(seal.rpmb_write_count, 0)
        self.assertFalse(seal.persistent_emmc_writes_authorized)
        self.assertEqual(seal.emmc_nflasha_write_count, 0)
        self.assertTrue(seal.warranty_clean)
        self.assertEqual(seal.status_code, "SEAL_VERIFIED_16_OF_16_H0_EQ_H3_ZERO_RESIDUAL")

    def test_30_any_surface_h0_neq_h3_fails_seal_audit(self) -> None:
        for surf in ("sector0", "p8", "p15", "spi_nor", "otp", "rpmb"):
            res = p167.audit_h0_to_h3_factory_seal(corrupt_surface=surf)
            self.assertFalse(res.valid)
            self.assertFalse(res.h0_equals_h3)
            self.assertFalse(res.warranty_clean)
            self.assertEqual(res.surfaces_matched, 15)
            self.assertEqual(res.status_code, "SEAL_FAILED_H0_NEQ_H3:15/16")

    def test_31_residual_orig_jiritsu_or_p6_chunk_fails_seal_audit(self) -> None:
        for kwargs in (
            {"orig_residual_count": 1},
            {"tmp_jiritsu_residual_count": 1},
            {"p6_chunk_residual_count": 1},
        ):
            res = p167.audit_h0_to_h3_factory_seal(**kwargs)
            self.assertFalse(res.valid)
            self.assertFalse(res.warranty_clean)
            self.assertEqual(res.status_code, "SEAL_FAILED_RESIDUAL_FILES_DETECTED")

    def test_32_otp_or_rpmb_nonzero_write_fails_seal_audit(self) -> None:
        for kwargs in ({"otp_write_count": 1}, {"rpmb_write_count": 1}):
            res = p167.audit_h0_to_h3_factory_seal(**kwargs)
            self.assertFalse(res.valid)
            self.assertFalse(res.warranty_clean)
            self.assertEqual(res.status_code, "SEAL_FAILED_OTP_OR_RPMB_MUTATION")

    def test_33_persistent_emmc_write_authorization_blocked_fail_closed(self) -> None:
        res = p167.audit_h0_to_h3_factory_seal(authorize_persistent_emmc_writes=True)
        self.assertFalse(res.valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertFalse(res.warranty_clean)
        self.assertEqual(res.status_code, "BLOCKED_PERSISTENT_EMMC_WRITE_REQUEST")

    def test_34_pillar_d_integrated_evaluation_passes(self) -> None:
        pd = _get_clean_room_audit()["pillar_d_h0_h3_16_of_16_factory_seal_audit"]
        self.assertTrue(pd["passed"])
        self.assertTrue(pd["clean_16_of_16_factory_seal"]["warranty_clean"])
        self.assertFalse(pd["fault_orig_residual_rejected"]["valid"])
        self.assertFalse(pd["fault_jiritsu_p6_residual_rejected"]["valid"])
        self.assertFalse(pd["fault_p15_h0_neq_h3_rejected"]["valid"])
        self.assertFalse(pd["fault_otp_rpmb_nonzero_rejected"]["valid"])
        self.assertFalse(pd["fault_emmc_write_request_blocked"]["valid"])


class TestStage29CliSuiteAndHygiene(unittest.TestCase):
    """CLI self-test, 29/29 full suite orchestration, runtime budget & BYOF hygiene."""

    def test_35_module_cli_summary_json_and_clean_room_in_process(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p167.main(["--self-test", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 167 Stage 29 Real-HW CXD90058/sabin/Seal HIL", buf_sum.getvalue())
        self.assertIn("h0_eq_h3=16/16", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p167.main(["--clean-room", "--self-test", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["stage_index"], 29)

    def test_36_module_cli_subprocess_and_invalid_flag_nonzero(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_cxd90058_sabin_codec_and_seal_coemulator.py"),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                p167.main(["--no-such-phase167-flag"])
            self.assertNotEqual(ctx.exception.code, 0)

    def test_37_suite_in_process_29_stages_and_skip_phase167_config(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage29_realhw_cxd90058_sabin_seal_hil", rep_on)
        s29 = rep_on["stage29_realhw_cxd90058_sabin_seal_hil"]
        self.assertTrue(s29["all_checks_passed"])
        self.assertEqual(s29["cxd90058_mutation_bytes"], 0)
        self.assertEqual(s29["cp_mutation_bytes"], 0)
        self.assertEqual(s29["otp_write_count"], 0)
        self.assertEqual(s29["rpmb_write_count"], 0)
        self.assertEqual(s29["emmc_nflasha_write_count"], 0)
        self.assertFalse(s29["persistent_emmc_writes_authorized"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 29)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase167_realhw_cxd90058_sabin_seal_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage29_realhw_cxd90058_sabin_seal_hil", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_38_suite_subprocess_summary_and_skip_phase167_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("realhw_cxd90058_sabin_seal_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase167",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_cxd90058_sabin_seal_hil=", proc_skip.stdout)

    def test_39_suite_29_stages_clean_room_lt_1p2s_and_local_lt_2p6s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 29)
        self.assertLess(dt_clean, 1.20)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 29)
        self.assertLess(dt_mode, 2.60)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_clean.returncode, 0, msg=p_clean.stderr)
        d_clean = json.loads(p_clean.stdout)
        self.assertTrue(d_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 29)

    def test_40_all_29_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 30):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_41_stage29_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_42_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_cxd90058_sabin_codec_and_seal_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_43_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p167.run_phase167_realhw_cxd90058_sabin_seal_hil(force_clean_room=True)
        r2 = p167.run_phase167_realhw_cxd90058_sabin_seal_hil(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_44_suite_phase167_digest_propagated_and_nonzero_stage_count(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        s29 = rep["stage29_realhw_cxd90058_sabin_seal_hil"]
        self.assertEqual(
            s29["phase167_audit_digest_sha256"],
            _get_clean_room_audit()["audit_digest_sha256"],
        )
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_45_sabin_and_codec_constants_match_fx3_702_hardware_contracts(self) -> None:
        self.assertEqual(p167.SABIN_IDT_CAM_BANK1_START, 0x809139000)
        self.assertEqual(p167.SABIN_IDT_CAM_BANK1_END_INCL, 0x809178FFF)
        self.assertEqual(p167.SABIN_IDT_CAM_BANK1_SIZE, 0x40000)
        self.assertEqual(len(p167.SIXTEEN_STORAGE_SURFACES), 16)
        self.assertEqual(len(p167.TIER0_SHARD_NAMES), 11)

    def test_46_clean_room_vs_default_audit_redlines_identical_zero_mutation(self) -> None:
        r_clean = _get_clean_room_audit()
        r_def = _get_default_audit()
        self.assertEqual(r_clean["redlines"], r_def["redlines"])
        self.assertEqual(
            r_clean["pillar_d_h0_h3_16_of_16_factory_seal_audit"]["clean_16_of_16_factory_seal"]["surfaces_matched"],
            16,
        )
        self.assertEqual(
            r_def["pillar_d_h0_h3_16_of_16_factory_seal_audit"]["clean_16_of_16_factory_seal"]["surfaces_matched"],
            16,
        )


if __name__ == "__main__":
    unittest.main()
