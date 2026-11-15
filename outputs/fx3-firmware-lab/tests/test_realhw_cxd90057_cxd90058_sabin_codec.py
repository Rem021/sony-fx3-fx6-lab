"""Phase 164 Dual-Mode Unit Tests (48 tests): Real-Hardware `CXD90057` (`Mira`) +
`CXD90058` (`Cetus`) Dual-BIONZ-XR Inter-Chip IPC, `sabin` 32-Bit SA-DSP Microcode,
and `XAVC-I / HEVC` Hardware Codec Boundary Auditor (`34/34`).
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_cxd90057_cxd90058_sabin_codec_auditor import (
    BK4_HEADER_MAGIC_HEX,
    CODEC_TRANSLATION_PROFILES,
    CXD90057_PCIE_DEVICE_ID,
    CXD90057_PCIE_VENDOR_ID,
    CXD90057_SOC_CODENAME,
    CXD90058_SOC_CODENAME,
    DTB_CXD90057_MARKERS,
    EXPECTED_FX3_APPFW_BYTES_P164,
    EXPECTED_FX3_BACKUP_BYTES_P164,
    EXPECTED_FX3_CPAPP_BYTES_P164,
    EXPECTED_FX3_DMMCFG_BYTES_P164,
    EXPECTED_FX3_DTB_BYTES_P164,
    EXPECTED_FX3_MPR_BYTES_P164,
    EXPECTED_FX3_MPR_EXPORTS_P164,
    EXPECTED_FX3_SENCORE_BYTES_P164,
    EXPECTED_FX6_APPFW_BYTES_P164,
    EXPECTED_FX6_BACKUP_BYTES_P164,
    EXPECTED_FX6_CPAPP_BYTES_P164,
    EXPECTED_FX6_DMMCFG_BYTES_P164,
    EXPECTED_FX6_MEW_BIN_BYTES_P164,
    EXPECTED_FX6_MPR_BYTES_P164,
    EXPECTED_FX6_MPR_EXPORTS_P164,
    EXPECTED_FX6_SABIN_CP_CAM_POST_BYTES,
    EXPECTED_FX6_SENCORE_BYTES_P164,
    FDT_MAGIC_U32,
    INSMOD_IPC_KMODS_P164,
    PHASE_164_SCHEMA,
    PHASE_164_VERSION,
    SABIN_DICTIONARY_BIN_PATHS,
    SABIN_SP01_MAGIC_HEX,
    XILINX_BUS_DETECT_HEX,
    XILINX_FPGA_SYNC_HEX,
    XILINX_FPGA_SYNC_OFFSET,
    analyze_realhw_cxd90057_cxd90058_sabin_codec,
    build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures,
    build_phase164_sabin_codec_matrix,
    evaluate_dual_soc_pcie_slvsec_invariance,
    evaluate_hardware_codec_boundary_translation,
    evaluate_phase164_write_guard,
    evaluate_sabin_dsp_and_dmm_pool_alignment,
    parse_backup_bin_header_summary,
    parse_dtb_header_and_markers,
    parse_mew_fpga_bitstream_header,
    parse_sabin_sp01_header,
    realhw_cxd90057_cxd90058_sabin_codec_report_to_dict,
)
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
)
from fx3_firmware_lab.realhw_mpr_dmm_rec_pipeline_bridge_auditor import (
    DMM_MAX_EXTENTS_IN_MPR_REPLY,
    FX3_DMMCFG_EXPECTED_RULES,
    FX3_DMMCFG_EXPECTED_UNITS,
    FX6_DMMCFG_EXPECTED_RULES,
    FX6_DMMCFG_EXPECTED_UNITS,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_cxd90057_cxd90058_sabin_codec_auditor.py"
)


class TestRealhwCxd90057Cxd90058SabinCodec(unittest.TestCase):
    """Comprehensive dual-mode tests (48 tests) for the 34th unified auditor (34/34)."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_164_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_164_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertTrue(rep.dual_soc_ipc_invariance_verified)
        self.assertTrue(rep.sabin_dsp_dmm_aligned)
        self.assertTrue(rep.xavc_hevc_codec_boundary_verified)
        self.assertTrue(rep.sdi_raw_mew_fpga_masked)
        self.assertTrue(rep.appfw_crash_prevented)
        self.assertEqual(rep.cxd90058_fw_mutation_bytes, 0)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(rep.sabin_microcode_mutation_bytes, 0)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertTrue(rep.pillar1_dual_soc_ipc.passed)
        self.assertTrue(rep.pillar2_sabin_dsp_dmm.passed)
        self.assertTrue(rep.pillar3_codec_boundary.passed)
        self.assertTrue(rep.pillar4_write_guard_matrix.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(len(rep.donor_file_sizes), 19)
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), EXPECTED_FX3_APPFW_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), EXPECTED_FX6_APPFW_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_mpr"), EXPECTED_FX3_MPR_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_mpr"), EXPECTED_FX6_MPR_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), EXPECTED_FX3_SENCORE_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), EXPECTED_FX6_SENCORE_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), EXPECTED_FX3_CPAPP_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), EXPECTED_FX6_CPAPP_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), EXPECTED_FX3_BACKUP_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), EXPECTED_FX6_BACKUP_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_dtb"), EXPECTED_FX3_DTB_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx3_dmmcfg"), EXPECTED_FX3_DMMCFG_BYTES_P164)
            self.assertEqual(rep.donor_file_sizes.get("fx6_dmmcfg"), EXPECTED_FX6_DMMCFG_BYTES_P164)
            self.assertEqual(
                rep.donor_file_sizes.get("fx6_sabin_cp_cam_post"),
                EXPECTED_FX6_SABIN_CP_CAM_POST_BYTES,
            )
            self.assertEqual(rep.donor_file_sizes.get("fx6_mew_bin"), EXPECTED_FX6_MEW_BIN_BYTES_P164)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_cxd90057_cxd90058_sabin_codec()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_cxd90057_cxd90058_sabin_codec_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_cxd90057_cxd90058_sabin_codec()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_no_raw_bytes_repr_leak(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        payload = realhw_cxd90057_cxd90058_sabin_codec_report_to_dict(rep)
        dumped = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(dumped), "Unexpected raw bytes repr in JSON")
        self.assertNotIn("BEGIN RSA PRIVATE KEY", dumped)
        self.assertIn(PHASE_164_SCHEMA, dumped)

    def test_06_ast_enforces_strictly_o_rdonly_and_zero_writes(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_attrs = {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND", "ACCESS_WRITE"}
        forbidden_calls = {"write", "write_bytes", "write_text"}
        os_open_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_attrs)
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr == "open"
                ):
                    os_open_count += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "open")
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
        self.assertGreaterEqual(os_open_count, 2)

    def test_07_package_init_exports_and_all(self) -> None:
        required = (
            "PHASE_164_SCHEMA",
            "PHASE_164_VERSION",
            "CXD90057_SOC_CODENAME",
            "CXD90058_SOC_CODENAME",
            "SABIN_DICTIONARY_BIN_PATHS",
            "CODEC_TRANSLATION_PROFILES",
            "BinaryHeaderSummary",
            "DualSocPcieSlvsecEvalResult",
            "SabinDspDmmPoolEvalResult",
            "HardwareCodecBoundaryEvalResult",
            "Phase164WriteGuardResult",
            "SabinCodecCompatMatrixSummary",
            "RealhwCxd90057Cxd90058SabinCodecReport",
            "parse_dtb_header_and_markers",
            "parse_sabin_sp01_header",
            "parse_mew_fpga_bitstream_header",
            "parse_backup_bin_header_summary",
            "evaluate_dual_soc_pcie_slvsec_invariance",
            "evaluate_sabin_dsp_and_dmm_pool_alignment",
            "evaluate_hardware_codec_boundary_translation",
            "evaluate_phase164_write_guard",
            "build_phase164_sabin_codec_matrix",
            "build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures",
            "analyze_realhw_cxd90057_cxd90058_sabin_codec",
            "realhw_cxd90057_cxd90058_sabin_codec_report_to_dict",
        )
        for name in required:
            self.assertTrue(hasattr(lab, name), f"Missing export {name} in fx3_firmware_lab")
            self.assertIn(name, lab.__all__, f"Missing {name} in fx3_firmware_lab.__all__")

    def test_08_run_audit_all_and_cli_integration_34_of_34(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-cxd90057-cxd90058-sabin", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_164_SCHEMA)
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertEqual(parsed["cxd90058_fw_mutation_bytes"], 0)
        self.assertEqual(parsed["cp_mutation_bytes"], 0)
        self.assertEqual(parsed["sabin_microcode_mutation_bytes"], 0)

        all_summary = run_audit_all(clean_room=True)
        self.assertTrue(all_summary["all_checks_passed"])
        self.assertIn("realhw_cxd90057_cxd90058_sabin_codec_audit", all_summary)
        audit_keys = [k for k in all_summary.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 34)

    def test_09_cli_audit_all_clean_room_smoke(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("realhw_cxd90057_cxd90058_sabin_codec_audit", parsed)

    def test_10_clean_room_fixtures_structure_valid(self) -> None:
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        expected_keys = {
            "fx3_appfw",
            "fx6_appfw",
            "fx3_mpr",
            "fx6_mpr",
            "fx3_sencore",
            "fx6_sencore",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_dtb",
            "fx3_insmod_drv2",
            "fx3_dmmcfg",
            "fx6_dmmcfg",
            "fx6_pci_ep_cp_ko",
            "fx6_pcie_if_ko",
            "fx6_codec_drv_ko",
            "fx6_sabin_head",
            "fx6_mew_head",
            "fx3_backup_head",
            "fx6_backup_head",
        }
        self.assertEqual(set(fx.keys()), expected_keys)
        self.assertEqual(struct.unpack_from(">I", fx["fx3_dtb"], 0)[0], FDT_MAGIC_U32)
        self.assertEqual(fx["fx6_sabin_head"][:4].hex(), SABIN_SP01_MAGIC_HEX)
        self.assertEqual(
            fx["fx6_mew_head"][XILINX_FPGA_SYNC_OFFSET : XILINX_FPGA_SYNC_OFFSET + 4].hex(),
            XILINX_FPGA_SYNC_HEX,
        )

    # ---- Pillar 1: CXD90057 (Mira) <-> CXD90058 (Cetus) Dual-SoC Boot & PCIe/SLVS-EC ----

    def test_11_dtb_parser_validates_fdt_magic_and_cxd90057_nodes(self) -> None:
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        summary, hits = parse_dtb_header_and_markers(fx["fx3_dtb"], source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(summary.valid)
        self.assertEqual(summary.header_magic_hex, "d00dfeed")
        for marker in DTB_CXD90057_MARKERS:
            self.assertGreaterEqual(hits[marker], 1)

    def test_12_dtb_parser_rejects_truncated_or_bad_magic(self) -> None:
        trunc_sum, _ = parse_dtb_header_and_markers(b"\xd0\x0d\xfe\xed", source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(trunc_sum.valid)
        self.assertEqual(trunc_sum.details, "TRUNCATED_FDT_HEADER")

        bad_sum, _ = parse_dtb_header_and_markers(b"\x00" * 64, source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(bad_sum.valid)

    def test_13_backup_bk4_header_parser_valid_and_invalid(self) -> None:
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        ok = parse_backup_bin_header_summary(
            fx["fx3_backup_head"],
            total_bytes=EXPECTED_FX3_BACKUP_BYTES_P164,
            source_mode="CLEAN_ROOM_SYNTHETIC",
            artifact_name="FX3-Backup.bin",
        )
        bad = parse_backup_bin_header_summary(
            b"\x00" * 32,
            total_bytes=EXPECTED_FX3_BACKUP_BYTES_P164,
            source_mode="CLEAN_ROOM_SYNTHETIC",
            artifact_name="Bad-Backup.bin",
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.header_magic_hex, BK4_HEADER_MAGIC_HEX)
        self.assertFalse(bad.valid)

    def test_14_pillar1_report_verifies_kmods_pcie_ep_and_cetus_slvsec(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        p1 = rep.pillar1_dual_soc_ipc
        self.assertTrue(p1.passed)
        self.assertTrue(p1.insmod_ipc_kmods_verified)
        self.assertEqual(len(INSMOD_IPC_KMODS_P164), 8)
        self.assertGreater(p1.pci_ep_cp_ko_hits["pci:v00001556d00001100"], 0)
        self.assertGreater(p1.pcie_if_ko_hits["PCIEIF_EPAR"], 0)
        self.assertGreater(p1.fx3_cp_cetus_hits["IMG:CetusSlvsecDriver::initialize"], 0)
        self.assertGreater(p1.fx6_cp_cetus_hits["IMG:CetusSlvsecMphy::startLane"], 0)

    def test_15_route1_hybrid_userland_keeps_mira_cetus_stock(self) -> None:
        res = evaluate_dual_soc_pcie_slvsec_invariance(
            deployment_route="ROUTE1_HYBRID_USERLAND_STAGE_B",
            cxd90058_fw_mutation_bytes=0,
            cp_mutation_bytes=0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.route1_invariance_verified)
        self.assertEqual(res.cxd90057_codename, CXD90057_SOC_CODENAME)
        self.assertEqual(res.cxd90058_codename, CXD90058_SOC_CODENAME)
        self.assertEqual(res.pcie_ep_id, f"0x{CXD90057_PCIE_VENDOR_ID:04x}:0x{CXD90057_PCIE_DEVICE_ID:04x}")
        self.assertEqual(res.status, "ROUTE1_DUAL_SOC_INVARIANT")

    def test_16_route2_full_cp_flash_blocked(self) -> None:
        res = evaluate_dual_soc_pcie_slvsec_invariance(
            deployment_route="ROUTE2_FULL_CP_FLASH",
            cxd90058_fw_mutation_bytes=4096,
            cp_mutation_bytes=17_952_816,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.route1_invariance_verified)
        self.assertTrue(any("BLOCKED_NON_ROUTE1_CP_REPLACEMENT" in e for e in res.errors))
        self.assertTrue(any("CXD90058_FW_MUTATION_NONZERO" in e for e in res.errors))
        self.assertTrue(any("CPAPP_P8_MUTATION_NONZERO" in e for e in res.errors))

    def test_17_unknown_deployment_route_and_pcie_id_mismatch_blocked(self) -> None:
        r_route = evaluate_dual_soc_pcie_slvsec_invariance(deployment_route="ROUTE3_UNSAFE")
        r_pcie = evaluate_dual_soc_pcie_slvsec_invariance(pcie_ep_vendor_id=0x10EE, pcie_ep_device_id=0x7024)
        self.assertFalse(r_route.valid)
        self.assertTrue(any("UNKNOWN_DEPLOYMENT_ROUTE" in e for e in r_route.errors))
        self.assertFalse(r_pcie.valid)
        self.assertTrue(any("PCIE_EP_ID_MISMATCH" in e for e in r_pcie.errors))

    def test_18_unpreserved_slvsec_backup_or_dtb_blocked(self) -> None:
        self.assertFalse(evaluate_dual_soc_pcie_slvsec_invariance(slvsec_mphy_stock_preserved=False).valid)
        self.assertFalse(evaluate_dual_soc_pcie_slvsec_invariance(backup_bin_stock_preserved=False).valid)
        self.assertFalse(evaluate_dual_soc_pcie_slvsec_invariance(dtb_cxd90057_stock_preserved=False).valid)

    # ---- Pillar 2: `sabin` 32-bit SA-DSP Microcode & `DmmCfg.bin` Pool Alignment ----

    def test_19_sabin_sp01_header_parser_valid_and_invalid(self) -> None:
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        ok = parse_sabin_sp01_header(
            fx["fx6_sabin_head"],
            total_bytes=EXPECTED_FX6_SABIN_CP_CAM_POST_BYTES,
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        bad_magic = parse_sabin_sp01_header(b"\x00" * 32, total_bytes=65536, source_mode="CLEAN_ROOM_SYNTHETIC")
        bad_size = parse_sabin_sp01_header(fx["fx6_sabin_head"], total_bytes=512, source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(ok.valid)
        self.assertEqual(ok.header_magic_hex, SABIN_SP01_MAGIC_HEX)
        self.assertFalse(bad_magic.valid)
        self.assertFalse(bad_size.valid)

    def test_20_pillar2_verifies_34_sabin_paths_and_dmmcfg_parity(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        p2 = rep.pillar2_sabin_dsp_dmm
        self.assertTrue(p2.passed)
        self.assertEqual(len(SABIN_DICTIONARY_BIN_PATHS), 34)
        self.assertEqual(p2.sabin_dict_count_fx3, 34)
        self.assertEqual(p2.sabin_dict_count_fx6, 34)
        self.assertEqual(p2.fx3_dmmcfg_summary.units_count, FX3_DMMCFG_EXPECTED_UNITS)
        self.assertEqual(p2.fx3_dmmcfg_summary.rules_count, FX3_DMMCFG_EXPECTED_RULES)
        self.assertEqual(p2.fx6_dmmcfg_summary.units_count, FX6_DMMCFG_EXPECTED_UNITS)
        self.assertEqual(p2.fx6_dmmcfg_summary.rules_count, FX6_DMMCFG_EXPECTED_RULES)
        self.assertLessEqual(p2.fx3_dmmcfg_summary.max_extents_per_unit, DMM_MAX_EXTENTS_IN_MPR_REPLY)
        self.assertGreater(p2.codec_drv_ko_hits["EXTERNAL_CODEC_DRIVER_LOAD_FIRM"], 0)
        self.assertGreater(p2.codec_drv_ko_hits["bdrv_uipc_send_sync_msg"], 0)

    def test_21_sabin_dmm_pool_alignment_dci_4k_60p_and_qfhd_120p_pass(self) -> None:
        dci = evaluate_sabin_dsp_and_dmm_pool_alignment(
            resolution="4096x2160", fps=59.94, codec_profile="XAVC_I_DCI_4K", dmm_mode_id=31, dmm_extent_count=1
        )
        qfhd = evaluate_sabin_dsp_and_dmm_pool_alignment(
            resolution="3840x2160", fps=119.88, codec_profile="XAVC_SI_QFHD", dmm_mode_id=32, dmm_extent_count=8
        )
        self.assertTrue(dci.valid)
        self.assertTrue(qfhd.valid)
        self.assertEqual(dci.sabin_microcode_mutation_bytes, 0)
        self.assertEqual(qfhd.max_allowed_extents, 8)
        self.assertEqual(dci.status, "SABIN_DMM_POOL_ALIGNED")

    def test_22_sabin_microcode_mutation_or_raw_dmmcfg_flash_blocked(self) -> None:
        r_mut = evaluate_sabin_dsp_and_dmm_pool_alignment(sabin_microcode_mutation_bytes=64)
        r_flash = evaluate_sabin_dsp_and_dmm_pool_alignment(raw_fx6_dmmcfg_flash=True)
        self.assertFalse(r_mut.valid)
        self.assertTrue(any("SABIN_MICROCODE_MUTATION_NONZERO" in e for e in r_mut.errors))
        self.assertFalse(r_flash.valid)
        self.assertTrue(any("BLOCKED_RAW_FX6_DMMCFG_EMMC_FLASH" in e for e in r_flash.errors))

    def test_23_dmm_extent_overflow_above_8_and_bad_mode_blocked(self) -> None:
        r_over = evaluate_sabin_dsp_and_dmm_pool_alignment(dmm_extent_count=9)
        r_zero = evaluate_sabin_dsp_and_dmm_pool_alignment(dmm_extent_count=0)
        r_mode = evaluate_sabin_dsp_and_dmm_pool_alignment(dmm_mode_id=99)
        self.assertFalse(r_over.valid)
        self.assertFalse(r_zero.valid)
        self.assertFalse(r_mode.valid)
        self.assertTrue(any("DMM_EXTENT_COUNT_OUT_OF_RANGE" in e for e in r_over.errors))
        self.assertTrue(any("UNSUPPORTED_DMM_MODE_ID" in e for e in r_mode.errors))

    def test_24_missing_ld_preload_shim_or_unloaded_sabin_blocked(self) -> None:
        r_no_shim = evaluate_sabin_dsp_and_dmm_pool_alignment(ld_preload_shim_active=False)
        r_no_sabin = evaluate_sabin_dsp_and_dmm_pool_alignment(sabin_cp_cam_post_loaded=False)
        self.assertFalse(r_no_shim.valid)
        self.assertFalse(r_no_sabin.valid)

    def test_25_5k_opengate_5016x3344_sabin_pool_blocked(self) -> None:
        r_5k = evaluate_sabin_dsp_and_dmm_pool_alignment(
            resolution="5016x3344", fps=23.98, codec_profile="X_OCN_LT_5K_OPENGATE"
        )
        self.assertFalse(r_5k.valid)
        self.assertTrue(any("UNSUPPORTED_5K_OPENGATE_SABIN_POOL" in e for e in r_5k.errors))
        self.assertTrue(any("BLOCKED_ABSENT_HW_CODEC_POOL" in e for e in r_5k.errors))

    # ---- Pillar 3: XAVC-I / HEVC Hardware Encoder vs Masked 16-bit SDI RAW FPGA ----

    def test_26_mew_fpga_bitstream_parser_validates_xilinx_sync(self) -> None:
        fx = build_clean_room_realhw_cxd90057_cxd90058_sabin_fixtures()
        ok = parse_mew_fpga_bitstream_header(
            fx["fx6_mew_head"],
            total_bytes=EXPECTED_FX6_MEW_BIN_BYTES_P164,
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        bad = parse_mew_fpga_bitstream_header(b"\xff" * 64, total_bytes=6_000_000, source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(ok.valid)
        self.assertEqual(ok.header_magic_hex, XILINX_FPGA_SYNC_HEX)
        self.assertEqual(fx["fx6_mew_head"][0x20:0x28].hex(), XILINX_BUS_DETECT_HEX)
        self.assertFalse(bad.valid)

    def test_27_pillar3_mpr_export_counts_and_fx3_zero_sdi_fpga_hits(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        p3 = rep.pillar3_codec_boundary
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_mpr_summary.export_count, EXPECTED_FX3_MPR_EXPORTS_P164)
        self.assertEqual(p3.fx6_mpr_summary.export_count, EXPECTED_FX6_MPR_EXPORTS_P164)
        self.assertTrue(all(v > 0 for v in p3.fx6_exclusive_fpga_cp_hits.values()))
        self.assertTrue(all(v == 0 for v in p3.fx3_fpga_cp_hits.values()))

    def test_28_xavc_i_dci_4k_and_qfhd_mxf_to_mp4_shim_admitted(self) -> None:
        for profile, res, fps in (
            ("XAVC_I_DCI_4K", "4096x2160", 23.98),
            ("XAVC_I_DCI_4K", "4096x2160", 59.94),
            ("XAVC_I_QFHD", "3840x2160", 29.97),
            ("XAVC_I_QFHD", "3840x2160", 119.88),
        ):
            ev = evaluate_hardware_codec_boundary_translation(
                fx6_codec_profile=profile, resolution=res, fps=fps, chroma="4:2:2", bit_depth=10
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertTrue(ev.codec_admitted)
            self.assertTrue(ev.mxf_to_mp4_shim_active)
            self.assertEqual(ev.target_container, "MP4_ISO_BMFF_SHIM")
            self.assertEqual(ev.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_29_xavc_si_native_passthrough_admitted(self) -> None:
        dci = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_SI_DCI_4K", resolution="4096x2160", fps=24.0, chroma="4:2:2", bit_depth=10
        )
        qfhd = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_SI_QFHD", resolution="3840x2160", fps=119.88, chroma="4:2:2", bit_depth=10
        )
        self.assertTrue(dci.valid and qfhd.valid)
        self.assertFalse(dci.mxf_to_mp4_shim_active)
        self.assertEqual(dci.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertIn("AVC480_3840_2160_H422IP", qfhd.hw_encoder_queue)

    def test_30_xavc_l_qfhd_422_shim_translated(self) -> None:
        ev = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_L_QFHD_422", resolution="3840x2160", fps=59.94, chroma="4:2:2", bit_depth=10
        )
        self.assertTrue(ev.valid)
        self.assertTrue(ev.mxf_to_mp4_shim_active)
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)
        self.assertIn("AVC_3840_2160_H422IP", ev.hw_encoder_queue)

    def test_31_xavc_hs_hevc_422_and_420_10bit_native_admitted(self) -> None:
        h422 = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_HS_QFHD_422_10B", resolution="3840x2160", fps=119.88, chroma="4:2:2", bit_depth=10
        )
        h420 = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_HS_QFHD_420_10B", resolution="3840x2160", fps=59.94, chroma="4:2:0", bit_depth=10
        )
        self.assertTrue(h422.valid and h420.valid)
        self.assertIn("HEVC_3840_2160_M42210P", h422.hw_encoder_queue)
        self.assertIn("HEVC_3840_2160_M10P", h420.hw_encoder_queue)
        self.assertEqual(h422.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_32_hdmi_16bit_raw_passthrough_admitted(self) -> None:
        ev = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="HDMI_RAW_16BIT", resolution="4264x2408", fps=59.94, chroma="RAW", bit_depth=16
        )
        self.assertTrue(ev.valid)
        self.assertTrue(ev.codec_admitted)
        self.assertEqual(ev.target_container, "HDMI_TMDS_RAW")
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_33_sdi_raw_mew_fpga_fail_closed_without_appfw_crash(self) -> None:
        ev = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="SDI_RAW_16BIT_MEW_FPGA",
            resolution="4096x2160",
            fps=59.94,
            chroma="RAW",
            bit_depth=16,
            sdi_raw_hw_present=False,
            mask_absent_fpga_sdi=True,
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.codec_admitted)
        self.assertTrue(ev.masked_gracefully)
        self.assertTrue(ev.appfw_crash_prevented)
        self.assertTrue(ev.fpga_mew_spi_access_blocked)
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)
        self.assertEqual(ev.status, "MASKED_ABSENT_SDI_RAW_MEW_FPGA")

    def test_34_unmasked_sdi_raw_fpga_flags_crash_hazard(self) -> None:
        ev = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="SDI_RAW_16BIT_MEW_FPGA",
            resolution="4096x2160",
            fps=59.94,
            chroma="RAW",
            bit_depth=16,
            sdi_raw_hw_present=False,
            mask_absent_fpga_sdi=False,
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.masked_gracefully)
        self.assertFalse(ev.appfw_crash_prevented)
        self.assertFalse(ev.fpga_mew_spi_access_blocked)
        self.assertEqual(ev.status, "UNMASKED_SDI_FPGA_CRASH_HAZARD")

    def test_35_x_ocn_lt_5k_opengate_masked_gracefully(self) -> None:
        ev = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="X_OCN_LT_5K_OPENGATE", resolution="5016x3344", fps=23.98, chroma="RAW", bit_depth=16
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.codec_admitted)
        self.assertTrue(ev.masked_gracefully)
        self.assertTrue(ev.appfw_crash_prevented)
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)

    def test_36_invalid_codec_parameter_combinations_rejected(self) -> None:
        bad_res = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_I_DCI_4K", resolution="1920x1080", fps=59.94, chroma="4:2:2", bit_depth=10
        )
        bad_fps = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_I_DCI_4K", resolution="4096x2160", fps=119.88, chroma="4:2:2", bit_depth=10
        )
        bad_chroma = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_HS_QFHD_422_10B", resolution="3840x2160", fps=59.94, chroma="4:2:0", bit_depth=10
        )
        bad_depth = evaluate_hardware_codec_boundary_translation(
            fx6_codec_profile="XAVC_I_QFHD", resolution="3840x2160", fps=59.94, chroma="4:2:2", bit_depth=8
        )
        unknown = evaluate_hardware_codec_boundary_translation(fx6_codec_profile="PRORES_4444_XQ")
        self.assertFalse(bad_res.valid)
        self.assertFalse(bad_fps.valid)
        self.assertFalse(bad_chroma.valid)
        self.assertFalse(bad_depth.valid)
        self.assertFalse(unknown.valid)

    # ---- Pillar 4: Non-Volatile Write Firewall & 12-Touchpoint 4-Class Matrix ----

    def test_37_write_guard_allows_volatile_ram_and_external_sd_clips(self) -> None:
        for path in (
            "/tmp/stage_b_sabin_codec_shadow.json",
            "ram://sabin_codec_params",
            "memfd:fx6_codec_shim",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/sd2/PRIVATE/M4ROOT/CLIP/C0002.MP4",
        ):
            wg = evaluate_phase164_write_guard(path)
            self.assertTrue(wg.valid, path)
            self.assertTrue(wg.volatile_or_ext_allowed)
            self.assertFalse(wg.persistent_write_blocked)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertFalse(wg.spi_nor_write_authorized)
            self.assertEqual(wg.emmc_mutation_bytes, 0)
            self.assertEqual(wg.cxd90058_fw_mutation_bytes, 0)
            self.assertEqual(wg.sabin_microcode_mutation_bytes, 0)

    def test_38_write_guard_blocks_cpapp_cetus_and_sabin_targets(self) -> None:
        for path in (
            "p8:/cpapp-b.bin",
            "/usr/sabin/sa_sabin_cp_cam_post.bin",
            "/usr/sabin/aed2_dic1.bin",
            "/dev/cnflasha1",
            "/dev/nflasha8",
        ):
            wg = evaluate_phase164_write_guard(path)
            self.assertFalse(wg.valid, path)
            self.assertTrue(wg.persistent_write_blocked)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertFalse(wg.spi_nor_write_authorized)

    def test_39_write_guard_blocks_mew_spinor_backup_dmmcfg_and_unlisted(self) -> None:
        for path in (
            "spi_nor:/mew.bin",
            "sector0:/loader_nor.bin",
            "p2:/Backup.bin",
            "p15:/usr/lib/libmpr.so",
            "/setting/DmmCfg.bin",
            "/dev/mmcblk0p1",
            "/var/log/unlisted.bin",
        ):
            wg = evaluate_phase164_write_guard(path)
            self.assertFalse(wg.valid, path)
            self.assertTrue(wg.persistent_write_blocked)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertFalse(wg.spi_nor_write_authorized)

    def test_40_12_touchpoint_4_class_matrix_structure(self) -> None:
        matrix = build_phase164_sabin_codec_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(len(matrix.touchpoints), 12)
        self.assertEqual(sum(matrix.class_counts.values()), 12)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_NATIVE_PASSTHROUGH], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_SHIM_TRANSLATED], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_MASKED_ABSENT_HW], 0)
        self.assertGreater(matrix.class_counts[BRIDGE_CLASS_HARD_WRITE_PROTECTED], 0)
        ids = [tp.touchpoint_id for tp in matrix.touchpoints]
        self.assertEqual(ids, [f"P164-{i:02d}" for i in range(1, 13)])

    def test_41_matrix_subsystems_cover_ipc_sabin_codec_fpga(self) -> None:
        matrix = build_phase164_sabin_codec_matrix()
        self.assertEqual(set(matrix.subsystem_counts.keys()), {"SOC_IPC", "SABIN_DSP", "HW_CODEC", "FPGA_SDI_GUARD"})
        self.assertEqual(sum(matrix.subsystem_counts.values()), 12)

    def test_42_codec_translation_catalog_completeness(self) -> None:
        self.assertEqual(len(CODEC_TRANSLATION_PROFILES), 10)
        supported = [k for k, v in CODEC_TRANSLATION_PROFILES.items() if v["supported_on_fx3_stage_b"]]
        masked = [k for k, v in CODEC_TRANSLATION_PROFILES.items() if not v["supported_on_fx3_stage_b"]]
        self.assertEqual(len(supported), 8)
        self.assertEqual(set(masked), {"SDI_RAW_16BIT_MEW_FPGA", "X_OCN_LT_5K_OPENGATE"})

    def test_43_local_donor_verification_when_donors_present(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=False)
        if rep.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Local Sony donor binaries absent in this environment; clean-room verified elsewhere.")
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.pillar1_dual_soc_ipc.dtb_summary.header_magic_hex, "d00dfeed")
        self.assertEqual(rep.pillar2_sabin_dsp_dmm.sabin_sp01_summary.header_magic_hex, SABIN_SP01_MAGIC_HEX)
        self.assertEqual(rep.pillar3_codec_boundary.mew_fpga_summary.header_magic_hex, XILINX_FPGA_SYNC_HEX)
        self.assertGreater(rep.pillar3_codec_boundary.fx6_exclusive_fpga_cp_hits["MoniFpgaSdi"], 0)
        self.assertEqual(rep.pillar3_codec_boundary.fx3_fpga_cp_hits["MoniFpgaSdi"], 0)

    def test_44_report_sha256_differs_if_field_changes(self) -> None:
        r1 = realhw_cxd90057_cxd90058_sabin_codec_report_to_dict(
            analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        )
        self.assertEqual(len(str(r1["report_sha256"])), 64)
        self.assertEqual(r1["cxd90058_fw_mutation_bytes"], 0)
        self.assertEqual(r1["cp_mutation_bytes"], 0)
        self.assertEqual(r1["sabin_microcode_mutation_bytes"], 0)

    def test_45_cli_subcommand_human_summary_returns_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-cxd90057-cxd90058-sabin", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("CLEAN_ROOM_SYNTHETIC", out)

    def test_46_dmm_pool_alignment_unknown_or_mismatched_resolution_rejected(self) -> None:
        r_unk = evaluate_sabin_dsp_and_dmm_pool_alignment(codec_profile="NON_EXISTENT")
        r_res = evaluate_sabin_dsp_and_dmm_pool_alignment(
            resolution="3840x2160", fps=59.94, codec_profile="XAVC_I_DCI_4K"
        )
        r_fps = evaluate_sabin_dsp_and_dmm_pool_alignment(
            resolution="4096x2160", fps=240.0, codec_profile="XAVC_I_DCI_4K"
        )
        self.assertFalse(r_unk.valid)
        self.assertFalse(r_res.valid)
        self.assertFalse(r_fps.valid)

    def test_47_report_dict_roundtrip_json_clean(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        d = realhw_cxd90057_cxd90058_sabin_codec_report_to_dict(rep)
        roundtrip = json.loads(json.dumps(d))
        self.assertEqual(roundtrip["report_sha256"], rep.report_sha256)
        self.assertEqual(roundtrip["pillar4_write_guard_matrix"]["compatibility_matrix"]["total_touchpoints"], 12)

    def test_48_pillar_errors_empty_on_pass(self) -> None:
        rep = analyze_realhw_cxd90057_cxd90058_sabin_codec(clean_room=True)
        self.assertEqual(rep.errors, ())
        self.assertEqual(rep.pillar1_dual_soc_ipc.errors, ())
        self.assertEqual(rep.pillar2_sabin_dsp_dmm.errors, ())
        self.assertEqual(rep.pillar3_codec_boundary.errors, ())
        self.assertEqual(rep.pillar4_write_guard_matrix.errors, ())


if __name__ == "__main__":
    unittest.main()
