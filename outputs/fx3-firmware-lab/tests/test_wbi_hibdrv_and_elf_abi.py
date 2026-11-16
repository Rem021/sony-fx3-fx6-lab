"""Unit tests for Phase 43 WBI2 Hibernation Snapshot, hibdrv Mismatch Detector & Pure-Python ELF64 ABI Differ.

Runs in BOTH Local Donor mode (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1`
mode in under 0.5 seconds, keeping the combined `fx3-firmware-lab` test suite
(>= 127 tests) fast and deterministic.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.wbi_hibdrv_and_elf_abi_differ import (
    CORE_SHARED_OBJECTS,
    DIVERGENT_FEATURE_FAMILIES,
    EM_AARCH64,
    ET_DYN,
    FX3_WBI2_PINNED_SPEC,
    FX6_WBI2_PINNED_SPEC,
    PHASE_43_SCHEMA,
    WBI_SECTOR_SIZE,
    Elf64ParseError,
    WbiHibdrvAndElfAbiReport,
    analyze_wbi_hibdrv_and_elf_abi,
    audit_elf64_file_rdonly,
    audit_wbi2_file_rdonly,
    build_clean_room_elf64_fixtures,
    build_synthetic_elf64_so,
    build_synthetic_kernel_for_wbi,
    build_synthetic_wbi2_image,
    classify_symbol_family,
    cross_validate_p_closure_matrix,
    diff_library_abi,
    parse_elf64_dynamic_abi,
    parse_wbi2_buffer,
    verify_hibdrv_cross_kernel_rejection,
    wbi_hibdrv_and_elf_abi_report_to_dict,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveWbiHibdrvAndElfAbiAudit(unittest.TestCase):
    _active_report: Optional[WbiHibdrvAndElfAbiReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_wbi_hibdrv_and_elf_abi()

    def test_01_active_mode_passes_with_deterministic_sha256(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_43_SCHEMA)
        self.assertEqual(rep.wbi_mutation_bytes, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertGreaterEqual(rep.libraries_both_compared, 4)
        self.assertEqual(len(rep.library_diffs), len(CORE_SHARED_OBJECTS))
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.fx3_wbi2.section_count, 1399)
            self.assertEqual(rep.fx3_wbi2.zero_fill_section_count, 82)
            self.assertEqual(rep.fx6_wbi2.section_count, 1197)
            self.assertEqual(rep.fx6_wbi2.zero_fill_section_count, 54)
            self.assertTrue(rep.fx3_wbi2.resume_64b_kernel_match)
            self.assertTrue(rep.fx6_wbi2.resume_64b_kernel_match)

    def test_02_clean_room_and_active_reports_have_full_p_closure(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertEqual(len(rep.feature_closure_checks), len(DIVERGENT_FEATURE_FAMILIES))
        for chk in rep.feature_closure_checks:
            self.assertTrue(chk.closed, msg=f"Unclosed family: {chk.family}")
            self.assertGreater(chk.observed_symbol_hits, 0, msg=f"Zero hits for {chk.family}")

    def test_03_report_to_dict_is_json_serializable(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = wbi_hibdrv_and_elf_abi_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertEqual(decoded["wbi_mutation_bytes"], 0)


class TestWbi2ParserAndHibdrvMismatch(unittest.TestCase):
    def test_04_synthetic_fx3_wbi2_header_sections_and_kernel_coupling(self) -> None:
        wbi = build_synthetic_wbi2_image("fx3_702")
        kern = build_synthetic_kernel_for_wbi("fx3_702")
        audit = parse_wbi2_buffer(wbi, body_label="fx3_702", kernel_buf=kern)
        self.assertTrue(audit.valid, msg=f"Errors: {audit.errors}")
        self.assertEqual(audit.magic, "WBI2")
        self.assertEqual(audit.sector_size, WBI_SECTOR_SIZE)
        self.assertEqual(audit.section_count, 4)
        self.assertEqual(audit.stored_section_count, 3)
        self.assertEqual(audit.zero_fill_section_count, 1)
        self.assertEqual(audit.metadata_xor_verified_count, 4)
        self.assertEqual(audit.linear_alias_verified_count, 4)
        self.assertEqual(audit.sorted_physical_overlaps, 0)
        self.assertTrue(audit.resume_64b_kernel_match)
        self.assertTrue(audit.kernel_build_coupled)
        self.assertTrue(audit.trailer_rbuf_found)
        self.assertTrue(audit.trailer_subs_found)
        self.assertIn("dic-build-scm-u20-028", audit.kernel_banner)

    def test_05_synthetic_fx6_wbi2_distinct_rv_and_dram_span(self) -> None:
        wbi = build_synthetic_wbi2_image("fx6_601")
        kern = build_synthetic_kernel_for_wbi("fx6_601")
        audit = parse_wbi2_buffer(wbi, body_label="fx6_601", kernel_buf=kern)
        self.assertTrue(audit.valid, msg=f"Errors: {audit.errors}")
        self.assertEqual(audit.resume_vector_hex, hex(int(FX6_WBI2_PINNED_SPEC["resume_vector"])))
        self.assertEqual(audit.phys_max_hex, hex(int(FX6_WBI2_PINNED_SPEC["phys_max"])))
        self.assertTrue(audit.resume_64b_kernel_match)
        self.assertIn("dic-build-scm-u24-002", audit.kernel_banner)

    def test_06_wbi2_rejects_bad_magic_and_truncated_buffer(self) -> None:
        short = parse_wbi2_buffer(b"WBI2\x00\x00")
        self.assertFalse(short.valid)
        self.assertTrue(any("smaller than 512B" in e for e in short.errors))

        bad_magic = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702", corrupt_magic=True))
        self.assertFalse(bad_magic.valid)
        self.assertTrue(any("Invalid WBI2 magic" in e for e in bad_magic.errors))

    def test_07_wbi2_rejects_corrupt_xor_checksum(self) -> None:
        bad_xor = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702", corrupt_xor_index=1))
        self.assertFalse(bad_xor.valid)
        self.assertEqual(bad_xor.metadata_xor_verified_count, 3)
        self.assertTrue(any("metadata XOR mismatch" in e for e in bad_xor.errors))

    def test_08_wbi2_rejects_corrupt_ttbr1_el1_linear_alias(self) -> None:
        bad_alias = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702", corrupt_linear_alias_index=2))
        self.assertFalse(bad_alias.valid)
        self.assertEqual(bad_alias.linear_alias_verified_count, 3)
        self.assertTrue(any("TTBR1_EL1 linear alias mismatch" in e for e in bad_alias.errors))

    def test_09_wbi2_rejects_overlapping_physical_sections(self) -> None:
        overlap = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702", corrupt_overlap=True))
        self.assertFalse(overlap.valid)
        self.assertGreater(overlap.sorted_physical_overlaps, 0)
        self.assertTrue(any("overlapping physical" in e for e in overlap.errors))

    def test_10_wbi2_detects_missing_kernel_banner_and_mismatched_kernel(self) -> None:
        no_banner = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702", include_kernel_banner=False))
        self.assertFalse(no_banner.valid)
        self.assertFalse(no_banner.kernel_build_coupled)

        # FX6 WBI2 paired against FX3 vmlinux.bin must fail resume 64B kernel match
        fx6_wbi = build_synthetic_wbi2_image("fx6_601")
        fx3_kern = build_synthetic_kernel_for_wbi("fx3_702")
        mismatch = parse_wbi2_buffer(fx6_wbi, body_label="fx6_601", kernel_buf=fx3_kern)
        self.assertFalse(mismatch.valid)
        self.assertFalse(mismatch.resume_64b_kernel_match)

    def test_11_wbi2_audit_rdonly_via_temp_file(self) -> None:
        blob = build_synthetic_wbi2_image("fx3_702")
        kblob = build_synthetic_kernel_for_wbi("fx3_702")
        with tempfile.TemporaryDirectory() as tmp:
            wp = Path(tmp) / "wbi.img"
            kp = Path(tmp) / "vmlinux.bin"
            wp.write_bytes(blob)
            kp.write_bytes(kblob)
            audit = audit_wbi2_file_rdonly(wp, body_label="fx3_702", kernel_path=kp, p11_path=wp)
            self.assertTrue(audit.valid, msg=f"Errors: {audit.errors}")
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertTrue(audit.p11_companion_present)

    def test_12_hibdrv_rejects_fx6_wbi2_on_fx3_kernel_fail_closed(self) -> None:
        fx3_audit = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702"), body_label="fx3_702")
        fx6_audit = parse_wbi2_buffer(build_synthetic_wbi2_image("fx6_601"), body_label="fx6_601")
        verdict = verify_hibdrv_cross_kernel_rejection(
            fx3_audit,
            fx6_audit,
            requested_warm_mode=2,
            allow_p5_write=True,
            allow_p11_bis_format=True,
        )
        self.assertTrue(verdict.rejected_fail_closed)
        self.assertEqual(verdict.verdict_code, "BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH")
        self.assertEqual(verdict.wbi_mutation_bytes, 0)
        self.assertTrue(verdict.p5_wbi_write_forbidden)
        self.assertTrue(verdict.p11_bis_format_forbidden)
        self.assertTrue(verdict.warm_mode_2_forbidden)
        self.assertFalse(verdict.kernel_banner_match)
        self.assertEqual(verdict.resume_vector_delta_bytes, 0x2000)
        self.assertEqual(verdict.phys_span_delta_bytes, 0x04000000)
        self.assertGreater(verdict.wbimem_delta_bytes, 14_000_000)
        self.assertTrue(any("EL1_TTBR1_PAGE_TABLE_DRAM_SPAN_HAZARD" in h for h in verdict.el1_hazards))

    def test_13_hibdrv_locks_warm_mode_2_even_on_identical_wbi2(self) -> None:
        fx3_a = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702"), body_label="fx3_702")
        fx3_b = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702"), body_label="fx3_702")
        verdict = verify_hibdrv_cross_kernel_rejection(fx3_a, fx3_b, requested_warm_mode=2)
        self.assertTrue(verdict.rejected_fail_closed)
        self.assertEqual(verdict.verdict_code, "BLOCKED_WBI_MUTATION_AND_WARM_MODE_LOCKED")
        self.assertEqual(verdict.wbi_mutation_bytes, 0)

    def test_14_hibdrv_flags_invalid_wbi2_fail_closed(self) -> None:
        fx3_ok = parse_wbi2_buffer(build_synthetic_wbi2_image("fx3_702"), body_label="fx3_702")
        bad = parse_wbi2_buffer(build_synthetic_wbi2_image("fx6_601", corrupt_xor_index=0), body_label="fx6_601")
        verdict = verify_hibdrv_cross_kernel_rejection(fx3_ok, bad)
        self.assertTrue(verdict.rejected_fail_closed)
        self.assertEqual(verdict.verdict_code, "BLOCKED_INVALID_WBI2_OR_KERNEL")
        self.assertEqual(verdict.wbi_mutation_bytes, 0)


class TestPurePythonElf64AbiDiffer(unittest.TestCase):
    def test_15_parse_synthetic_elf64_via_section_headers(self) -> None:
        so_bytes = build_synthetic_elf64_so(
            soname="libWlanResource.so",
            dt_needed=("libbackup.so", "libc.so.6"),
            exports=("_Z16handleFatalErrorv", "_Z19loadWlanHostDriversb"),
            imports=("osal_snd_sync_direct",),
            include_section_headers=True,
        )
        info = parse_elf64_dynamic_abi(so_bytes, library_name="libWlanResource.so", body_label="fx6_601")
        self.assertEqual(info.e_type, ET_DYN)
        self.assertEqual(info.e_machine, EM_AARCH64)
        self.assertEqual(info.soname, "libWlanResource.so")
        self.assertEqual(info.dt_needed, ("libbackup.so", "libc.so.6"))
        self.assertEqual(info.parse_path, "SECTION_HEADERS")
        self.assertEqual(info.export_count, 2)
        self.assertEqual(info.import_count, 1)
        self.assertIn("_Z16handleFatalErrorv", info.exports)
        self.assertIn("osal_snd_sync_direct", info.imports)

    def test_16_parse_stripped_elf64_via_pt_dynamic_vaddr_fallback(self) -> None:
        so_bytes = build_synthetic_elf64_so(
            soname="libmpr.so",
            dt_needed=("libexpat.so.1", "libc.so.6"),
            exports=("_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",),
            imports=("osal_snd_sync_msg",),
            include_section_headers=False,
        )
        info = parse_elf64_dynamic_abi(so_bytes, library_name="libmpr.so", body_label="fx6_601")
        self.assertEqual(info.parse_path, "PT_DYNAMIC_VADDR")
        self.assertEqual(info.soname, "libmpr.so")
        self.assertEqual(info.dt_needed, ("libexpat.so.1", "libc.so.6"))
        self.assertIn("_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE", info.exports)

    def test_17_parse_elf64_rejects_invalid_headers(self) -> None:
        with self.assertRaises(Elf64ParseError):
            parse_elf64_dynamic_abi(b"NOTELF", library_name="bad.so", body_label="fx3_702")

        # Valid ELF64 magic but x86_64 machine (62) instead of AArch64 (183)
        bad_arch = bytearray(build_synthetic_elf64_so(soname="x.so", dt_needed=(), exports=("f",), imports=()))
        struct.pack_into("<H", bad_arch, 18, 62)
        with self.assertRaises(Elf64ParseError):
            parse_elf64_dynamic_abi(bytes(bad_arch), library_name="x.so", body_label="fx3_702")

    def test_18_audit_elf64_file_rdonly_via_temp_file(self) -> None:
        so_bytes = build_synthetic_elf64_so(
            soname="libgemini-grm.so",
            dt_needed=("libc.so.6",),
            exports=("GRM_gpermRectblit",),
            imports=("pthread_mutex_lock",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "libgemini-grm.so"
            p.write_bytes(so_bytes)
            info = audit_elf64_file_rdonly(p, library_name="libgemini-grm.so", body_label="fx6_601")
            self.assertEqual(info.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(info.soname, "libgemini-grm.so")
            self.assertEqual(info.export_count, 1)

    def test_19_symbol_family_classifier_precision(self) -> None:
        self.assertEqual(classify_symbol_family("GRM_gpermRectblit"), "Big6")
        self.assertEqual(classify_symbol_family("_ZN8UXEngine6resmgrEv"), "Big6")
        self.assertEqual(classify_symbol_family("_ZN3mpr12KlvConverter18Rdd18KeyCameraUnitE"), "CineEI")
        self.assertEqual(classify_symbol_family("_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE"), "Lut3D")
        self.assertEqual(classify_symbol_family("_ZN3mpr12KlvConverter46ManuallyEnteredMeta2rdd_ExternalNdFilterFactorERKtPhRjb"), "VariableND")
        self.assertEqual(classify_symbol_family("MuxMxfFnlzPrm_GetVideoCompression"), "SdiOut")
        self.assertEqual(classify_symbol_family("_ZN12InfraBTCore_7CBTWoLE9startWoLEEv"), "SmartHandle")
        self.assertEqual(classify_symbol_family("_Z16handleFatalErrorv"), "WlanFatal")
        # Ensure 'nd' inside 'send' or 'bind' does NOT misclassify as VariableND!
        self.assertEqual(classify_symbol_family("osal_snd_sync_msg"), "SharedBionzXrBaseABI")
        self.assertEqual(classify_symbol_family("send"), "SharedBionzXrBaseABI")
        self.assertEqual(classify_symbol_family("pthread_mutex_lock"), "SharedBionzXrBaseABI")

    def test_20_clean_room_elf64_fixtures_cover_all_6_core_libraries(self) -> None:
        fixtures = build_clean_room_elf64_fixtures()
        self.assertEqual(set(fixtures["fx3_702"].keys()), set(CORE_SHARED_OBJECTS))
        self.assertEqual(set(fixtures["fx6_601"].keys()), set(CORE_SHARED_OBJECTS))
        diffs = []
        for lib in CORE_SHARED_OBJECTS:
            i3 = parse_elf64_dynamic_abi(fixtures["fx3_702"][lib], library_name=lib, body_label="fx3_702")
            i6 = parse_elf64_dynamic_abi(fixtures["fx6_601"][lib], library_name=lib, body_label="fx6_601")
            diffs.append(diff_library_abi(lib, i3, i6))
        appfw_diff = next(d for d in diffs if d.library_name == "appFw.so")
        self.assertIn("libInfraSKD.so", appfw_diff.fx3_only_dt_needed)
        self.assertIn("libopus.so.0", appfw_diff.fx6_only_dt_needed)
        mpr_diff = next(d for d in diffs if d.library_name == "libmpr.so")
        self.assertIn("libsecvlt.so", mpr_diff.fx3_only_dt_needed)
        self.assertIn("libexpat.so.1", mpr_diff.shared_dt_needed)

    def test_21_diff_handles_partial_on_disk_subset_gracefully(self) -> None:
        fixtures = build_clean_room_elf64_fixtures()
        fx6_ux = parse_elf64_dynamic_abi(
            fixtures["fx6_601"]["libuxengine.so"],
            library_name="libuxengine.so",
            body_label="fx6_601",
        )
        d_fx6_only = diff_library_abi("libuxengine.so", None, fx6_ux)
        self.assertEqual(d_fx6_only.comparison_status, "FX6_ONLY_ON_DISK")
        self.assertFalse(d_fx6_only.fx3_present)
        self.assertTrue(d_fx6_only.fx6_present)
        self.assertGreater(d_fx6_only.fx6_only_export_count, 0)

        d_missing = diff_library_abi("libuxengine.so", None, None)
        self.assertEqual(d_missing.comparison_status, "MISSING_BOTH")

    def test_22_p_closure_cross_validation_closes_all_7_families(self) -> None:
        fixtures = build_clean_room_elf64_fixtures()
        diffs = [
            diff_library_abi(
                lib,
                parse_elf64_dynamic_abi(fixtures["fx3_702"][lib], library_name=lib, body_label="fx3_702"),
                parse_elf64_dynamic_abi(fixtures["fx6_601"][lib], library_name=lib, body_label="fx6_601"),
            )
            for lib in CORE_SHARED_OBJECTS
        ]
        checks = cross_validate_p_closure_matrix(diffs)
        self.assertEqual({c.family for c in checks}, set(DIVERGENT_FEATURE_FAMILIES))
        self.assertTrue(all(c.closed and c.observed_symbol_hits > 0 for c in checks))


class TestCliAndAuditAllIntegration(unittest.TestCase):
    def test_23_forced_clean_room_env_returns_synthetic_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_wbi_hibdrv_and_elf_abi()
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(rep.libraries_both_compared, len(CORE_SHARED_OBJECTS))
        self.assertEqual(rep.wbi_mutation_bytes, 0)

    def test_24_cli_audit_wbi_elf_clean_room_in_process(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-wbi-elf", "--clean-room"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(data["schema_version"], PHASE_43_SCHEMA)

    def test_25_run_audit_all_includes_all_7_auditors(self) -> None:
        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        self.assertIn("wbi_hibdrv_and_elf_abi_audit", all_res)
        self.assertTrue(all_res["wbi_hibdrv_and_elf_abi_audit"]["all_checks_passed"])
        self.assertEqual(all_res["wbi_hibdrv_and_elf_abi_audit"]["wbi_mutation_bytes"], 0)

    def test_26_cli_audit_wbi_elf_clean_room_subprocess_deterministic(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-wbi-elf", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        p2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-wbi-elf", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(p1.stdout, p2.stdout)
        parsed = json.loads(p1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("b'", p1.stdout)

    def test_27_strict_o_rdonly_and_zero_raw_bytes_repr_in_module(self) -> None:
        mod_path = PKG_ROOT / "fx3_firmware_lab" / "wbi_hibdrv_and_elf_abi_differ.py"
        src = mod_path.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess.", src)


if __name__ == "__main__":
    unittest.main()
