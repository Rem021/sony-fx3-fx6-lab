"""Fast dual-mode unit tests for Phase 165 — Real-Hardware Main Track Part 14:
Gate G53 (`CXD90057` *Mira* + `CXD90058` *Cetus* Dual-BIONZ-XR Inter-SoC Link,
`sabin` 32-bit SA-DSP Microcode Immutability, FX6 `16-bit SDI RAW` / `mew.bin`
FPGA Output Mask & FX3 `1,724.00 MiB` `memcfg=` XAVC Encoder Pool Guard),
Gate G54 (Post-Bench `16/16 H0 == H3` Bit-Identical Factory Seal, Zero
`/usr/bin/im.elf.orig`, `/etc/ld.so.preload`, `/tmp/jiritsu/*`, `p6` Residual,
`OTP == 0`, `RPMB == 0` & `mode* == 0` Official Update Readiness Guard), and
Unified 54-Gate Master Safety Preflight (`G01..G54` / `verify-54-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
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
from fx3_safety.realhw_cfexpress_ufu_el3_and_52gate_guard import (
    MEDIA_TYPE_SDXC_V90,
    REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA,
    STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT,
    STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH,
    evaluate_52gate_preflight,
)
from fx3_safety.realhw_cxd90058_sabin_seal_and_54gate_guard import (
    AP_SOC_MIRA_CODENAME,
    AP_SOC_MIRA_NAME,
    CANONICAL_16_STORAGE_SURFACES,
    CANONICAL_16_SURFACE_COUNT,
    CP_SOC_CETUS_CODENAME,
    CP_SOC_CETUS_NAME,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FORBIDDEN_BENCH_RESIDUAL_PATHS,
    FX3_ALLOWED_OUTPUT_PATHS,
    FX3_ENCODER_POOL_ALIGN_BYTES,
    FX3_MEMCFG_BUDGET_BYTES,
    FX3_MEMCFG_BUDGET_MIB,
    FX3_VALID_XAVC_CODEC_POOLS,
    FX6_FORBIDDEN_SDI_RAW_MODES,
    FX6_MEW_FPGA_BINARY,
    G53_GATE_CODE,
    G53_GATE_ID,
    G54_GATE_CODE,
    G54_GATE_ID,
    INTERSOC_VALID_LINK_PROTOCOLS,
    P8_CPAPP_PARTITION_PATH,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_FX3_CPAPP_SHA256,
    PINNED_PHASE165_DONOR_SPECS,
    REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA,
    REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION,
    SABIN_DSP_ARCH_NAME,
    SABIN_DSP_MICROCODE_PREFIX,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION,
    STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED,
    STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION,
    STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW,
    STATUS_BLOCKED_G53_TELEMETRY_INVALID,
    STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH,
    STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY,
    STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT,
    STATUS_BLOCKED_G54_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G53,
    STATUS_VERIFIED_G54,
    STATUS_VERIFIED_SAFE,
    audit_phase165_donor_contracts,
    default_verified_16_surface_seal_hashes,
    evaluate_54_master_safety_gates,
    evaluate_54gate_preflight,
    evaluate_g53_cxd90058_sabin,
    evaluate_g54_factory_seal,
    find_h0_h3_surface_mismatches,
    main as module_cli_main,
    validate_16_surface_h0_h3_seal,
    validate_cxd90058_and_sabin_immutability,
    validate_memcfg_xavc_encoder_pool,
    validate_mira_cetus_intersoc_link,
    validate_otp_rpmb_and_updater_flags,
    validate_sdi_raw_mew_mask,
    validate_zero_bench_residuals,
    verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard,
    verify_post_bench_factory_seal_and_official_readiness_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwCxd90058SabinSealAnd54GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA,
            "fx3-realhw-cxd90058-sabin-seal-54gate-preflight-v1",
        )
        self.assertEqual(REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION, "1.0.0")
        self.assertEqual(AP_SOC_MIRA_NAME, "CXD90057")
        self.assertEqual(AP_SOC_MIRA_CODENAME, "Mira")
        self.assertEqual(CP_SOC_CETUS_NAME, "CXD90058")
        self.assertEqual(CP_SOC_CETUS_CODENAME, "Cetus")
        self.assertEqual(CANONICAL_16_SURFACE_COUNT, 16)
        self.assertEqual(len(CANONICAL_16_STORAGE_SURFACES), 16)
        self.assertEqual(FX3_MEMCFG_BUDGET_MIB, 1724.0)
        self.assertEqual(FX3_MEMCFG_BUDGET_BYTES, 1724 * 1024 * 1024)
        self.assertEqual(FX6_MEW_FPGA_BINARY, "mew.bin")

        for sym in (
            "AP_SOC_MIRA_CODENAME",
            "AP_SOC_MIRA_NAME",
            "CANONICAL_16_STORAGE_SURFACES",
            "CANONICAL_16_SURFACE_COUNT",
            "CP_SOC_CETUS_CODENAME",
            "CP_SOC_CETUS_NAME",
            "FORBIDDEN_BENCH_RESIDUAL_PATHS",
            "FX3_ALLOWED_OUTPUT_PATHS",
            "FX3_ENCODER_POOL_ALIGN_BYTES",
            "FX3_MEMCFG_BUDGET_BYTES",
            "FX3_MEMCFG_BUDGET_MIB",
            "FX3_VALID_XAVC_CODEC_POOLS",
            "FX6_FORBIDDEN_SDI_RAW_MODES",
            "FX6_MEW_FPGA_BINARY",
            "G53_GATE_CODE",
            "G53_GATE_ID",
            "G54_GATE_CODE",
            "G54_GATE_ID",
            "INTERSOC_VALID_LINK_PROTOCOLS",
            "P8_CPAPP_PARTITION_PATH",
            "PINNED_FX3_CPAPP_SHA256",
            "PINNED_PHASE165_DONOR_SPECS",
            "REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA",
            "REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION",
            "SABIN_DSP_ARCH_NAME",
            "SABIN_DSP_MICROCODE_PREFIX",
            "STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION",
            "STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED",
            "STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION",
            "STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW",
            "STATUS_BLOCKED_G53_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH",
            "STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY",
            "STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT",
            "STATUS_BLOCKED_G54_TELEMETRY_INVALID",
            "STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY",
            "STATUS_VERIFIED_G53",
            "STATUS_VERIFIED_G54",
            "Cxd90058SabinSdiGuardResult",
            "G53Cxd90058SabinResult",
            "G54FactorySealResult",
            "Master54GateReport",
            "Phase165DonorAuditResult",
            "PostBenchFactorySealGuardResult",
            "audit_phase165_donor_contracts",
            "default_verified_16_surface_seal_hashes",
            "evaluate_54_master_safety_gates",
            "evaluate_54gate_preflight",
            "evaluate_g53_cxd90058_sabin",
            "evaluate_g54_factory_seal",
            "find_h0_h3_surface_mismatches",
            "realhw_cxd90058_sabin_seal_and_54gate_guard",
            "validate_16_surface_h0_h3_seal",
            "validate_cxd90058_and_sabin_immutability",
            "validate_memcfg_xavc_encoder_pool",
            "validate_mira_cetus_intersoc_link",
            "validate_otp_rpmb_and_updater_flags",
            "validate_sdi_raw_mew_mask",
            "validate_zero_bench_residuals",
            "verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard",
            "verify_post_bench_factory_seal_and_official_readiness_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing package export: {sym}")

        # Prior colliding constants must remain untouched
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.MEDIA_TYPE_CFEXPRESS_A, "CFEXPRESS_TYPE_A")

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        clean_res = audit_phase165_donor_contracts(force_clean_room=True)
        self.assertTrue(clean_res.valid)
        self.assertEqual(clean_res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(clean_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_res.access_mode, "O_RDONLY")
        self.assertEqual(clean_res.files_inspected, 0)
        self.assertEqual(len(clean_res.checked_markers), len(PINNED_PHASE165_DONOR_SPECS))
        self.assertEqual(clean_res.missing_markers, ())
        self.assertTrue(clean_res.fx3_contracts_verified)

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_res = audit_phase165_donor_contracts(
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
            "fx3_safety.realhw_cxd90058_sabin_seal_and_54gate_guard.os.open",
            side_effect=spy_open,
        ):
            auto_res = audit_phase165_donor_contracts(repo_root=DEFAULT_REPO_ROOT)

        self.assertTrue(auto_res.valid)
        self.assertEqual(auto_res.access_mode, "O_RDONLY")
        if auto_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(auto_res.files_inspected, len(PINNED_PHASE165_DONOR_SPECS))
            self.assertEqual(len(seen_flags), len(PINNED_PHASE165_DONOR_SPECS))
            for fl in seen_flags:
                self.assertEqual(fl & 3, os.O_RDONLY)

        dumped = json.dumps(auto_res.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)
        self.assertNotIn("b'BK4", dumped)

    def test_03_donor_audit_fails_closed_on_tampered_sha_or_missing_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for _k, (_body, rel, size, _sha, toks, _lbl) in PINNED_PHASE165_DONOR_SPECS.items():
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                payload = b"".join(t + b"\x00" for t in toks)
                if len(payload) < size:
                    payload = payload + b"\x00" * min(64, size - len(payload))
                p.write_bytes(payload)

            tampered = audit_phase165_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(tampered.valid)
            self.assertEqual(tampered.status, STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY)
            self.assertEqual(tampered.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertFalse(tampered.fx3_contracts_verified)
            self.assertGreaterEqual(len(tampered.errors), len(PINNED_PHASE165_DONOR_SPECS))

            v53, r53 = evaluate_g53_cxd90058_sabin(donor_audit=tampered)
            self.assertFalse(v53.passed)
            self.assertFalse(r53.valid)
            self.assertIn(STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY, v53.violation_codes)

            v54, r54 = evaluate_g54_factory_seal(donor_audit=tampered)
            self.assertFalse(v54.passed)
            self.assertFalse(r54.valid)
            self.assertIn(STATUS_BLOCKED_PHASE165_DONOR_INTEGRITY, v54.violation_codes)

    def test_04_donor_audit_fails_closed_on_missing_token_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            for key, (_body, rel, _sz, _sha, toks, _lbl) in PINNED_PHASE165_DONOR_SPECS.items():
                p = work / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if key == "fx3_cpapp_b":
                    # Omit Cetus and sabin tokens intentionally
                    p.write_bytes(b"ILME-FX3\x00memcfg\x00")
                else:
                    p.write_bytes(b"".join(t + b"\x00" for t in toks))

            tampered = audit_phase165_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(tampered.valid)
            self.assertTrue(any("cpapp-b.bin" in m for m in tampered.missing_markers))

    # --- 2. Pure Helper Function Unit Tests (G53 & G54) ---

    def test_05_helper_validate_cxd90058_and_sabin_immutability(self) -> None:
        self.assertTrue(validate_cxd90058_and_sabin_immutability())
        self.assertFalse(validate_cxd90058_and_sabin_immutability(p8_cpapp_ro_locked=False))
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(p8_cpapp_mutation_bytes=4)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(cxd90058_mutation_bytes=16)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(sabin_dsp_mutation_bytes=32)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(cxd90058_boot_blobs_untouched=False)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(sabin_microcode_untouched=False)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(cxd90058_write_requested=True)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(sabin_dsp_patch_requested=True)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(p8_cpapp_sha256="0" * 64)
        )
        self.assertFalse(
            validate_cxd90058_and_sabin_immutability(sabin_dsp_arch="UNKNOWN_DSP")
        )

    def test_06_helper_validate_mira_cetus_intersoc_link(self) -> None:
        for proto in INTERSOC_VALID_LINK_PROTOCOLS:
            self.assertTrue(
                validate_mira_cetus_intersoc_link(intersoc_link_protocol=proto)
            )
        self.assertFalse(
            validate_mira_cetus_intersoc_link(intersoc_link_healthy=False)
        )
        self.assertFalse(validate_mira_cetus_intersoc_link(ap_soc_name="CXD90056"))
        self.assertFalse(validate_mira_cetus_intersoc_link(cp_soc_name="CXD90059"))
        self.assertFalse(
            validate_mira_cetus_intersoc_link(intersoc_link_protocol="SPI_RAW")
        )
        self.assertFalse(
            validate_mira_cetus_intersoc_link(p8_cpapp_partition="p3:/system")
        )

    def test_07_helper_validate_sdi_raw_mew_mask(self) -> None:
        for allowed in FX3_ALLOWED_OUTPUT_PATHS:
            self.assertTrue(validate_sdi_raw_mew_mask(output_path=allowed))
        self.assertFalse(validate_sdi_raw_mew_mask(fx6_sdi_raw_masked=False))
        self.assertFalse(validate_sdi_raw_mew_mask(mew_bin_fpga_probe_masked=False))
        self.assertFalse(validate_sdi_raw_mew_mask(sdi_raw_16bit_requested=True))
        self.assertFalse(validate_sdi_raw_mew_mask(mew_bin_load_requested=True))
        for bad_mode in FX6_FORBIDDEN_SDI_RAW_MODES:
            self.assertFalse(validate_sdi_raw_mew_mask(output_path=bad_mode))
        self.assertFalse(validate_sdi_raw_mew_mask(output_path="MEW_FPGA_OUT"))
        self.assertFalse(validate_sdi_raw_mew_mask(output_path="12G_SDI_PORT"))

    def test_08_helper_validate_memcfg_xavc_encoder_pool(self) -> None:
        for codec in FX3_VALID_XAVC_CODEC_POOLS:
            self.assertTrue(
                validate_memcfg_xavc_encoder_pool(encoder_codec_family=codec)
            )
        # Wrong FX3 memcfg ceiling (e.g. FX6 2048 MiB) must fail
        self.assertFalse(validate_memcfg_xavc_encoder_pool(memcfg_total_mib=2048.0))
        self.assertFalse(validate_memcfg_xavc_encoder_pool(allocated_memcfg_mib=1800.0))
        self.assertFalse(validate_memcfg_xavc_encoder_pool(allocated_memcfg_mib=0.0))
        self.assertFalse(validate_memcfg_xavc_encoder_pool(memcfg_overflow_bytes=4096))
        self.assertFalse(validate_memcfg_xavc_encoder_pool(encoder_codec_family="SDI_RAW"))
        self.assertFalse(
            validate_memcfg_xavc_encoder_pool(
                encoder_pool_bytes=268_435_456 + 128  # unaligned
            )
        )
        self.assertFalse(
            validate_memcfg_xavc_encoder_pool(encoder_pool_align_bytes=1024)
        )
        self.assertFalse(
            validate_memcfg_xavc_encoder_pool(encoder_pool_align_bytes=6144)  # not pow2
        )

    def test_09_helper_16_surface_h0_h3_seal_and_mismatches(self) -> None:
        h0, h3 = default_verified_16_surface_seal_hashes()
        self.assertEqual(len(h0), 16)
        self.assertEqual(len(h3), 16)
        self.assertEqual(find_h0_h3_surface_mismatches(h0, h3), ())
        self.assertTrue(validate_16_surface_h0_h3_seal(h0, h3))

        h3_bad = dict(h3)
        h3_bad["p15_usr"] = "f" * 64
        self.assertEqual(find_h0_h3_surface_mismatches(h0, h3_bad), ("p15_usr",))
        self.assertFalse(validate_16_surface_h0_h3_seal(h0, h3_bad))

        h3_short = dict(h3)
        del h3_short["spi_nor_ro"]
        self.assertFalse(validate_16_surface_h0_h3_seal(h0, h3_short))

    def test_10_helper_validate_zero_bench_residuals_and_otp_flags(self) -> None:
        self.assertTrue(validate_zero_bench_residuals())
        self.assertFalse(validate_zero_bench_residuals(im_elf_orig_present=True))
        self.assertFalse(validate_zero_bench_residuals(ld_so_preload_present=True))
        self.assertFalse(validate_zero_bench_residuals(tmp_jiritsu_file_count=1))
        self.assertFalse(validate_zero_bench_residuals(p6_residual_file_count=1))
        self.assertFalse(validate_zero_bench_residuals(p6_chunk_residual_bytes=512))
        self.assertFalse(validate_zero_bench_residuals(residual_artifact_count=1))
        self.assertFalse(
            validate_zero_bench_residuals(leftover_paths=("/tmp/jiritsu/payload.bin",))
        )

        self.assertTrue(validate_otp_rpmb_and_updater_flags())
        self.assertFalse(validate_otp_rpmb_and_updater_flags(otp_write_count=1))
        self.assertFalse(validate_otp_rpmb_and_updater_flags(rpmb_write_count=1))
        self.assertFalse(validate_otp_rpmb_and_updater_flags(updater_mode_flag_count=1))
        self.assertFalse(
            validate_otp_rpmb_and_updater_flags(
                updater_mode_paths_present=("/setting/updater/mode5",)
            )
        )
        self.assertFalse(validate_otp_rpmb_and_updater_flags(official_update_ready=False))

    # --- 3. Gate G53 Guard & Evaluator Tests ---

    def test_11_g53_baseline_safe_state(self) -> None:
        res = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G53)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.cxd90058_sabin_immutability_safe)
        self.assertTrue(res.intersoc_link_safe)
        self.assertTrue(res.sdi_raw_mask_safe)
        self.assertTrue(res.memcfg_encoder_pool_safe)
        self.assertEqual(res.cxd90058_mutation_bytes, 0)
        self.assertEqual(res.sabin_dsp_mutation_bytes, 0)
        self.assertEqual(res.p8_cpapp_mutation_bytes, 0)
        self.assertFalse(res.el3_payload_transmit_authorized)
        self.assertFalse(res.spi_nor_write_authorized)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_12_g53_blocks_cxd90058_mutation_and_write_request(self) -> None:
        r_mut = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            cxd90058_mutation_bytes=64
        )
        self.assertFalse(r_mut.valid)
        self.assertIn(STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r_mut.violation_codes)
        self.assertFalse(r_mut.cxd90058_sabin_immutability_safe)

        r_req = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            cxd90058_write_requested=True
        )
        self.assertFalse(r_req.valid)
        self.assertIn(STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r_req.violation_codes)

    def test_13_g53_blocks_p8_cpapp_mutation_and_sha_mismatch(self) -> None:
        r_unlock = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            p8_cpapp_ro_locked=False,
            p8_cpapp_mutation_bytes=128,
        )
        self.assertFalse(r_unlock.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r_unlock.violation_codes
        )

        r_sha = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            p8_cpapp_sha256="b" * 64
        )
        self.assertFalse(r_sha.valid)
        self.assertIn(STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r_sha.violation_codes)

    def test_14_g53_blocks_sabin_dsp_microcode_patch(self) -> None:
        r1 = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            sabin_dsp_mutation_bytes=4,
            sabin_microcode_untouched=False,
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r1.violation_codes)

        r2 = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            sabin_dsp_patch_requested=True
        )
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION, r2.violation_codes)

    def test_15_g53_blocks_intersoc_link_fault_and_wrong_partition(self) -> None:
        r_link = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            intersoc_link_healthy=False
        )
        self.assertFalse(r_link.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION, r_link.violation_codes
        )
        self.assertFalse(r_link.intersoc_link_safe)

        r_proto = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            intersoc_link_protocol="RAW_PCIe_DMA"
        )
        self.assertFalse(r_proto.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION, r_proto.violation_codes
        )

        r_part = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            p8_cpapp_partition="p3:/cpapp-b.bin"
        )
        self.assertFalse(r_part.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_INTERSOC_LINK_OR_CPAPP_VIOLATION, r_part.violation_codes
        )

    def test_16_g53_blocks_fx6_16bit_sdi_raw_and_mew_bin_paths(self) -> None:
        r_sdi = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            fx6_sdi_raw_masked=False,
            sdi_raw_16bit_requested=True,
        )
        self.assertFalse(r_sdi.valid)
        self.assertIn(STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED, r_sdi.violation_codes)
        self.assertFalse(r_sdi.sdi_raw_mask_safe)

        r_mew = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            mew_bin_fpga_probe_masked=False,
            mew_bin_load_requested=True,
        )
        self.assertFalse(r_mew.valid)
        self.assertIn(STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED, r_mew.violation_codes)

        r_out = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            output_path="16BIT_SDI_RAW"
        )
        self.assertFalse(r_out.valid)
        self.assertIn(STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED, r_out.violation_codes)

    def test_17_g53_blocks_memcfg_overflow_and_misaligned_xavc_pool(self) -> None:
        r_budget = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            allocated_memcfg_mib=1725.0,
        )
        self.assertFalse(r_budget.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW, r_budget.violation_codes
        )
        self.assertFalse(r_budget.memcfg_encoder_pool_safe)

        r_over = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            memcfg_overflow_bytes=65536
        )
        self.assertFalse(r_over.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW, r_over.violation_codes
        )

        r_align = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            encoder_pool_bytes=268_435_456 + 512
        )
        self.assertFalse(r_align.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW, r_align.violation_codes
        )

    def test_18_g53_accepts_all_valid_xavc_pools_within_1724mib(self) -> None:
        for codec in FX3_VALID_XAVC_CODEC_POOLS:
            res = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
                encoder_codec_family=codec,
                allocated_memcfg_mib=1724.0,
                encoder_pool_bytes=536_870_912,  # 512 MiB
                encoder_pool_align_bytes=65_536,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.status, STATUS_VERIFIED_G53)

    def test_19_g53_blocks_invalid_telemetry_and_bool_injection(self) -> None:
        bad_nan = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            memcfg_total_mib=float("nan")
        )
        self.assertFalse(bad_nan.valid)
        self.assertIn(STATUS_BLOCKED_G53_TELEMETRY_INVALID, bad_nan.violation_codes)

        bad_bool = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            cxd90058_mutation_bytes=True,  # type: ignore[arg-type]
        )
        self.assertFalse(bad_bool.valid)
        self.assertIn(STATUS_BLOCKED_G53_TELEMETRY_INVALID, bad_bool.violation_codes)

        bad_sha = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            p8_cpapp_sha256="not-a-sha256"
        )
        self.assertFalse(bad_sha.valid)
        self.assertIn(STATUS_BLOCKED_G53_TELEMETRY_INVALID, bad_sha.violation_codes)

    def test_20_evaluate_g53_verdict_and_persistent_write_block(self) -> None:
        v, r = evaluate_g53_cxd90058_sabin(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertEqual(v.gate_id, G53_GATE_ID)
        self.assertEqual(v.gate_code, G53_GATE_CODE)
        self.assertTrue(r.valid)

        v_blk, r_blk = evaluate_g53_cxd90058_sabin(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v_blk.violation_codes)
        self.assertFalse(r_blk.persistent_emmc_writes_authorized)

    # --- 4. Gate G54 Guard & Evaluator Tests ---

    def test_21_g54_baseline_16_of_16_factory_seal_clean(self) -> None:
        res = verify_post_bench_factory_seal_and_official_readiness_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G54)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.expected_surface_count, 16)
        self.assertEqual(res.verified_surface_count, 16)
        self.assertEqual(res.mismatched_surfaces, ())
        self.assertTrue(res.h0_equals_h3_16_of_16)
        self.assertTrue(res.zero_residual_safe)
        self.assertTrue(res.otp_rpmb_updater_clean_safe)
        self.assertFalse(res.im_elf_orig_present)
        self.assertFalse(res.ld_so_preload_present)
        self.assertEqual(res.residual_artifact_count, 0)
        self.assertEqual(res.otp_write_count, 0)
        self.assertEqual(res.rpmb_write_count, 0)
        self.assertEqual(res.updater_mode_flag_count, 0)
        self.assertTrue(res.official_update_ready)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_22_g54_blocks_single_and_multiple_h0_h3_surface_mismatches(self) -> None:
        h0, h3 = default_verified_16_surface_seal_hashes()
        for surface in ("sector0", "p6_jiritsu", "p8_cpapp", "p15_usr", "spi_nor_ro"):
            bad_h3 = dict(h3)
            bad_h3[surface] = "0" * 64
            res = verify_post_bench_factory_seal_and_official_readiness_guard(
                h0_surface_sha256s=h0,
                h3_surface_sha256s=bad_h3,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.h0_equals_h3_16_of_16)
            self.assertEqual(res.verified_surface_count, 15)
            self.assertEqual(res.mismatched_surfaces, (surface,))
            self.assertIn(
                STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH, res.violation_codes
            )

        bad_multi = dict(h3)
        bad_multi["p1_updater"] = "1" * 64
        bad_multi["p18_lens"] = "2" * 64
        res_m = verify_post_bench_factory_seal_and_official_readiness_guard(
            h0_surface_sha256s=h0,
            h3_surface_sha256s=bad_multi,
        )
        self.assertFalse(res_m.valid)
        self.assertEqual(res_m.verified_surface_count, 14)
        self.assertEqual(res_m.mismatched_surfaces, ("p1_updater", "p18_lens"))

    def test_23_g54_blocks_missing_surface_from_16_seal_map(self) -> None:
        h0, h3 = default_verified_16_surface_seal_hashes()
        h3_partial = dict(h3)
        del h3_partial["p12_cert"]
        res = verify_post_bench_factory_seal_and_official_readiness_guard(
            h0_surface_sha256s=h0,
            h3_surface_sha256s=h3_partial,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.h0_equals_h3_16_of_16)
        self.assertIn("p12_cert", res.mismatched_surfaces)
        self.assertIn(STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH, res.violation_codes)

    def test_24_g54_blocks_im_elf_orig_and_ld_so_preload(self) -> None:
        r_orig = verify_post_bench_factory_seal_and_official_readiness_guard(
            im_elf_orig_present=True
        )
        self.assertFalse(r_orig.valid)
        self.assertFalse(r_orig.zero_residual_safe)
        self.assertIn(STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT, r_orig.violation_codes)

        r_preload = verify_post_bench_factory_seal_and_official_readiness_guard(
            ld_so_preload_present=True
        )
        self.assertFalse(r_preload.valid)
        self.assertIn(
            STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT, r_preload.violation_codes
        )

    def test_25_g54_blocks_tmp_jiritsu_and_p6_chunk_residuals(self) -> None:
        r_tmp = verify_post_bench_factory_seal_and_official_readiness_guard(
            tmp_jiritsu_file_count=2,
            leftover_paths=("/tmp/jiritsu/stageb.so", "/tmp/jiritsu/canary.bin"),
        )
        self.assertFalse(r_tmp.valid)
        self.assertIn(STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT, r_tmp.violation_codes)

        r_p6 = verify_post_bench_factory_seal_and_official_readiness_guard(
            p6_residual_file_count=1,
            p6_chunk_residual_bytes=65536,
            residual_artifact_count=1,
        )
        self.assertFalse(r_p6.valid)
        self.assertIn(STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT, r_p6.violation_codes)

    def test_26_g54_blocks_otp_rpmb_and_updater_mode_flags(self) -> None:
        r_otp = verify_post_bench_factory_seal_and_official_readiness_guard(
            otp_write_count=1
        )
        self.assertFalse(r_otp.valid)
        self.assertIn(STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY, r_otp.violation_codes)

        r_rpmb = verify_post_bench_factory_seal_and_official_readiness_guard(
            rpmb_write_count=1
        )
        self.assertFalse(r_rpmb.valid)
        self.assertIn(STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY, r_rpmb.violation_codes)

        r_mode = verify_post_bench_factory_seal_and_official_readiness_guard(
            updater_mode_flag_count=1,
            updater_mode_paths_present=("/setting/updater/mode",),
        )
        self.assertFalse(r_mode.valid)
        self.assertIn(STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY, r_mode.violation_codes)

        r_not_ready = verify_post_bench_factory_seal_and_official_readiness_guard(
            official_update_ready=False
        )
        self.assertFalse(r_not_ready.valid)
        self.assertIn(
            STATUS_BLOCKED_G54_OTP_RPMB_OR_UPDATER_DIRTY, r_not_ready.violation_codes
        )

    def test_27_g54_blocks_invalid_telemetry_and_bool_injection(self) -> None:
        r1 = verify_post_bench_factory_seal_and_official_readiness_guard(
            otp_write_count=True,  # type: ignore[arg-type]
        )
        self.assertFalse(r1.valid)
        self.assertIn(STATUS_BLOCKED_G54_TELEMETRY_INVALID, r1.violation_codes)

        r2 = verify_post_bench_factory_seal_and_official_readiness_guard(
            residual_artifact_count=False,  # type: ignore[arg-type]
        )
        self.assertFalse(r2.valid)
        self.assertIn(STATUS_BLOCKED_G54_TELEMETRY_INVALID, r2.violation_codes)

        r3 = verify_post_bench_factory_seal_and_official_readiness_guard(
            guard_profile="   ",
        )
        self.assertFalse(r3.valid)
        self.assertIn(STATUS_BLOCKED_G54_TELEMETRY_INVALID, r3.violation_codes)

    def test_28_evaluate_g54_verdict_and_persistent_write_block(self) -> None:
        v, r = evaluate_g54_factory_seal(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertEqual(v.gate_id, G54_GATE_ID)
        self.assertEqual(v.gate_code, G54_GATE_CODE)
        self.assertTrue(r.valid)

        v_blk, r_blk = evaluate_g54_factory_seal(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_blk.passed)
        self.assertFalse(r_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, v_blk.violation_codes)
        self.assertFalse(r_blk.persistent_emmc_writes_authorized)

    def test_29_g54_constants_cover_canonical_surfaces_and_forbidden_paths(self) -> None:
        for required_surface in (
            "sector0",
            "emmc_boot0",
            "emmc_boot1",
            "p1_updater",
            "p6_jiritsu",
            "p8_cpapp",
            "p15_usr",
            "p18_lens",
            "spi_nor_ro",
        ):
            self.assertIn(required_surface, CANONICAL_16_STORAGE_SURFACES)
        self.assertIn("/usr/bin/im.elf.orig", FORBIDDEN_BENCH_RESIDUAL_PATHS)
        self.assertIn("/etc/ld.so.preload", FORBIDDEN_BENCH_RESIDUAL_PATHS)
        self.assertIn("/tmp/jiritsu", FORBIDDEN_BENCH_RESIDUAL_PATHS)
        self.assertEqual(SABIN_DSP_ARCH_NAME, "SA_DSP_32BIT")
        self.assertEqual(SABIN_DSP_MICROCODE_PREFIX, "sabin/")

    # --- 5. Unified 54-Gate Master Safety Preflight Tests ---

    def test_30_54gate_offline_default_reports_51_of_54_and_locks_writes(self) -> None:
        report = evaluate_54gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(report.schema, REALHW_CXD90058_SABIN_SEAL_54GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_CXD90058_SABIN_SEAL_54GATE_VERSION)
        self.assertEqual(len(report.gates), 54)
        self.assertEqual(report.summary["total_gates"], 54)
        self.assertEqual(report.summary["verified_gates"], 51)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g01_to_g12_verified"], 9)
        self.assertEqual(report.summary["g13_to_g52_verified"], 40)
        self.assertEqual(report.summary["g53_to_g54_verified"], 2)
        self.assertTrue(report.offline_51_gates_verified)
        self.assertFalse(report.all_54_gates_verified)
        self.assertTrue(report.g13_to_g54_all_passed)
        self.assertTrue(report.g53_to_g54_all_passed)
        self.assertFalse(report.dry_run_rehearsal_only)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.status, "VERIFIED_51_OF_54_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(report.gates[idx]["passed"])
            self.assertEqual(
                report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_31_54gate_dry_run_simulated_backup_54_of_54_keeps_redlines_locked(
        self,
    ) -> None:
        report = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertEqual(len(report.gates), 54)
        self.assertEqual(report.summary["verified_gates"], 54)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(report.all_54_gates_verified)
        self.assertTrue(report.offline_51_gates_verified)
        self.assertTrue(report.g13_to_g54_all_passed)
        self.assertTrue(report.g53_to_g54_all_passed)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(
            report.status, "VERIFIED_ALL_54_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        # Hard-locked even in dry-run green
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)

    def test_32_54gate_clean_room_and_alias_parity(self) -> None:
        r1 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r2 = evaluate_54_master_safety_gates(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r1.clean_room_forced)
        self.assertTrue(r1.all_54_gates_verified)
        self.assertEqual(r1.summary, r2.summary)
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(
            r1.master_52_report["schema"], REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA
        )

    def test_33_54gate_propagates_g53_and_g54_failures_and_blocks_h0_h1(self) -> None:
        fail_g53 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cxd90058_sabin_kwargs={"sabin_dsp_mutation_bytes": 16},
        )
        self.assertFalse(fail_g53.all_54_gates_verified)
        self.assertFalse(fail_g53.offline_51_gates_verified)
        self.assertFalse(fail_g53.g53_to_g54_all_passed)
        self.assertFalse(fail_g53.h0_h1_trial_entry_allowed)
        self.assertEqual(
            fail_g53.status, STATUS_BLOCKED_G53_CXD90058_OR_SABIN_MUTATION
        )

        fail_sdi = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cxd90058_sabin_kwargs={"sdi_raw_16bit_requested": True},
        )
        self.assertFalse(fail_sdi.all_54_gates_verified)
        self.assertEqual(fail_sdi.status, STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED)

        h0, h3 = default_verified_16_surface_seal_hashes()
        h3_bad = dict(h3)
        h3_bad["p8_cpapp"] = "c" * 64
        fail_g54 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            factory_seal_kwargs={
                "h0_surface_sha256s": h0,
                "h3_surface_sha256s": h3_bad,
            },
        )
        self.assertFalse(fail_g54.all_54_gates_verified)
        self.assertFalse(fail_g54.offline_51_gates_verified)
        self.assertFalse(fail_g54.g53_to_g54_all_passed)
        self.assertFalse(fail_g54.h0_h1_trial_entry_allowed)
        self.assertEqual(fail_g54.status, STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH)

    def test_34_54gate_propagates_g51_g52_failures_and_persistent_write_redline(
        self,
    ) -> None:
        fail_g51 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            cfexpress_ufu_kwargs={
                "slot_a_media_type": MEDIA_TYPE_SDXC_V90,
                "slot_a_speed_class": "V90",
                "slot_a_sustained_write_mb_s": 90.0,
            },
        )
        self.assertFalse(fail_g51.all_54_gates_verified)
        self.assertEqual(
            fail_g51.status, STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT
        )

        fail_g52 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            five_tier_el3_kwargs={
                "target_model_id": 0x91020080,
                "target_model_name": "ILME-FX6",
            },
        )
        self.assertFalse(fail_g52.all_54_gates_verified)
        self.assertEqual(
            fail_g52.status, STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH
        )

        fail_emmc = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(fail_emmc.all_54_gates_verified)
        self.assertEqual(fail_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(fail_emmc.persistent_emmc_writes_authorized)

    def test_35_54gate_unique_gate_ids_and_52gate_unchanged(self) -> None:
        m52 = evaluate_52gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        m54 = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(len(m52.gates), 52)
        self.assertEqual(len(m54.gates), 54)
        gate_ids = [g["gate_id"] for g in m54.gates]
        self.assertEqual(len(set(gate_ids)), 54)
        self.assertEqual(gate_ids[52], G53_GATE_ID)
        self.assertEqual(gate_ids[53], G54_GATE_ID)

    def test_36_json_serializable_without_raw_binary_leakage(self) -> None:
        report = evaluate_54gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        dumped = json.dumps(report.to_dict(), ensure_ascii=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["summary"]["verified_gates"], 54)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("b'\\x89UFU", dumped)
        self.assertNotIn("b'BK4", dumped)

    # --- 6. CLI Tests (fx3_safety.__main__ & module main) ---

    def test_37_cli_verify_g53_cxd90058_sabin_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-g53-cxd90058-sabin", "--clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G53)
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_38_cli_verify_g54_factory_seal_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-g54-factory-seal", "--clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G54)
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_39_cli_verify_54_gates_offline_and_dry_run(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-54-gates", "--clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=51/54", buf_off.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf_off.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf_off.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_off.getvalue())

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-54-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        data = json.loads(buf_dry.getvalue())
        self.assertTrue(data["all_54_gates_verified"])
        self.assertEqual(data["summary"]["verified_gates"], 54)
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertFalse(data["el3_payload_transmit_authorized"])
        self.assertFalse(data["spi_nor_write_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertFalse(data["persistent_write_release"])

    def test_40_module_cli_main_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--clean-room", "--dry-run-simulated-backup"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=54/54", out)
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
        self.assertTrue(parsed["all_54_gates_verified"])

    # --- 7. Additional Boundary & Edge-Case Coverage Tests (48 Total) ---

    def test_41_g53_allows_alternate_valid_intersoc_protocols(self) -> None:
        for proto in ("SLVS-EC", "ivshmem", "UIPC_CP_IPC"):
            res = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
                intersoc_link_protocol=proto
            )
            self.assertTrue(res.valid)

    def test_42_g53_blocks_mew_or_sdi_substring_in_output_path(self) -> None:
        for bad_out in ("SDI_DIRECT", "MEW_BYPASS", "EXTERNAL_SDI_16B", "HDMI_PLUS_MEW"):
            res = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
                output_path=bad_out
            )
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G53_FX6_SDI_RAW_MEW_UNMASKED, res.violation_codes)

    def test_43_g53_blocks_non_exact_fx3_memcfg_ceiling_and_zero_pool(self) -> None:
        r_low = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            memcfg_total_mib=1024.0
        )
        self.assertFalse(r_low.valid)
        self.assertIn(STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW, r_low.violation_codes)

        r_pool_gt_alloc = verify_cxd90058_sabin_dsp_and_sdi_raw_mask_guard(
            allocated_memcfg_mib=128.0,
            encoder_pool_bytes=268_435_456,  # 256 MiB > 128 MiB allocated
        )
        self.assertFalse(r_pool_gt_alloc.valid)
        self.assertIn(
            STATUS_BLOCKED_G53_MEMCFG_ENCODER_POOL_OVERFLOW,
            r_pool_gt_alloc.violation_codes,
        )

    def test_44_g54_blocks_extra_unexpected_surface_key(self) -> None:
        h0, h3 = default_verified_16_surface_seal_hashes()
        h3_extra = dict(h3)
        h3_extra["unexpected_p99"] = "d" * 64
        res = verify_post_bench_factory_seal_and_official_readiness_guard(
            h0_surface_sha256s=h0,
            h3_surface_sha256s=h3_extra,
        )
        self.assertFalse(res.valid)
        self.assertIn("unexpected_p99", res.mismatched_surfaces)
        self.assertIn(STATUS_BLOCKED_G54_H0_H3_SURFACE_SEAL_MISMATCH, res.violation_codes)

    def test_45_g54_blocks_uppercase_invalid_sha_format(self) -> None:
        h0, h3 = default_verified_16_surface_seal_hashes()
        h3_bad = dict(h3)
        h3_bad["p2_setting"] = "not-64-hex"
        res = verify_post_bench_factory_seal_and_official_readiness_guard(
            h0_surface_sha256s=h0,
            h3_surface_sha256s=h3_bad,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.mismatched_surfaces, ("p2_setting",))

    def test_46_g54_blocks_residual_count_even_if_specific_flags_false(self) -> None:
        res = verify_post_bench_factory_seal_and_official_readiness_guard(
            residual_artifact_count=3
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G54_RESIDUAL_ARTIFACT_PRESENT, res.violation_codes)

    def test_47_clean_room_env_var_overrides_local_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            report = evaluate_54gate_preflight(
                DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
            )
            self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(report.clean_room_forced)
            self.assertTrue(report.all_54_gates_verified)
            self.assertEqual(report.summary["verified_gates"], 54)
            self.assertFalse(report.overall_ready_for_hardware_attach)
            self.assertFalse(report.el3_payload_transmit_authorized)
            self.assertFalse(report.spi_nor_write_authorized)
            self.assertFalse(report.persistent_emmc_writes_authorized)
            self.assertFalse(report.persistent_write_release)

    def test_48_text_cli_output_for_g53_and_g54(self) -> None:
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = package_cli_main(["verify-g53-cxd90058-sabin", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn(STATUS_VERIFIED_G53, buf1.getvalue())
        self.assertIn("el3_payload_transmit_authorized=False", buf1.getvalue())
        self.assertIn("spi_nor_write_authorized=False", buf1.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf1.getvalue())

        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = package_cli_main(["verify-g54-factory-seal", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn(STATUS_VERIFIED_G54, buf2.getvalue())
        self.assertIn("h0_eq_h3=16/16", buf2.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf2.getvalue())


if __name__ == "__main__":
    unittest.main()
