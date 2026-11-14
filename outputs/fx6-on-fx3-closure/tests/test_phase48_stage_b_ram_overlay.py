"""Phase 48 unit tests for Stage-B (`P1..P12+Fan`, 13/13) RAM-Overlay Packager v2 & Atomic `init2` Guard."""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx6_closure
from fx6_closure import __main__ as cli_main
from fx6_closure.backup_mount_tolerance_verifier import (
    audit_ram_shadow_bk4,
    read_bk4_property_bytes,
)
from fx6_closure.patcher import (
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    read_donor_bytes_readonly,
)
from fx6_closure.ram_overlay_packager import (
    CPIO_NEWC_MAGIC,
    S_IFDIR,
    S_IFREG,
    CpioEntrySpec,
    CpioFormatError,
)
from fx6_closure.stage_b_ram_overlay_packager import (
    BK_KEY_LANG,
    FX3_PRODUCT_MODEL_HEX,
    FX3_PRODUCT_MODEL_U32,
    PHASE_48_SCHEMA,
    PHASE_48_VERSION,
    STAGE_B_AIRPLANE_KEYS,
    STAGE_B_BK_LANG_SPECS,
    STAGE_B_DETERMINISTIC_GID,
    STAGE_B_DETERMINISTIC_MTIME,
    STAGE_B_DETERMINISTIC_UID,
    STAGE_B_FX3_DDR_TOTAL_BYTES,
    STAGE_B_INIT2_SANDBOX_SCENARIOS,
    STAGE_B_LOCK_TABLE_13_ARTIFACTS,
    STAGE_B_SUPPORTED_LANGS,
    STAGE_B_TMPFS_BUDGET_LIMIT_BYTES,
    STAGE_B_TMPFS_BUDGET_LIMIT_MIB,
    STAGE_B_V2_REQUIRED_CPIO_PATHS,
    audit_stage_b_bk4_shadow,
    build_stage_b_cpio_newc_archive,
    build_stage_b_ram_overlay_v2_package,
    generate_stage_b_init2_guard_script,
    parse_and_audit_stage_b_cpio_newc,
    synthesize_stage_b_bk4_shadow,
    verify_stage_b_ram_overlay_v2,
    verify_stage_b_tmpfs_ddr_budget,
)
from fx3_safety.boot_contracts import parse_bk4_record
from fx3_safety.preflight import verify_failsafe_hook_script
from fx3_safety.runtime_antibrick_guards import audit_ld_so_preload_and_overlay


class TestPhase48StageBRamOverlayPackagerV2(unittest.TestCase):
    """Fast (<5s) dual-mode Stage-B RAM-overlay v2 packager, BK4 shadow, and init2 guard tests."""

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls.bundle = build_stage_b_ram_overlay_v2_package(lang="en")
        cls.report = verify_stage_b_ram_overlay_v2(lang="en", prebuilt_bundle=cls.bundle)
        cls.elapsed_s = time.monotonic() - t0
        cls.report_json_str = cls.report.to_deterministic_json()
        cls.report_json = json.loads(cls.report_json_str)
        cls.scenario_map = {s.scenario_id: s for s in cls.report.sandbox_drill.scenarios}

    def test_01_public_exports_and_constants(self) -> None:
        expected = {
            "BK_KEY_LANG",
            "FX3_PRODUCT_MODEL_HEX",
            "FX3_PRODUCT_MODEL_U32",
            "PHASE_48_SCHEMA",
            "PHASE_48_VERSION",
            "STAGE_B_AIRPLANE_KEYS",
            "STAGE_B_BK_LANG_SPECS",
            "STAGE_B_DETERMINISTIC_GID",
            "STAGE_B_DETERMINISTIC_MTIME",
            "STAGE_B_DETERMINISTIC_UID",
            "STAGE_B_FX3_DDR_TOTAL_BYTES",
            "STAGE_B_INIT2_SANDBOX_SCENARIOS",
            "STAGE_B_LOCK_TABLE_13_ARTIFACTS",
            "STAGE_B_SUPPORTED_LANGS",
            "STAGE_B_TMPFS_BUDGET_LIMIT_BYTES",
            "STAGE_B_V2_REQUIRED_CPIO_PATHS",
            "StageBBkLangSpec",
            "StageBInit2SandboxDrillReport",
            "StageBInit2SandboxScenarioResult",
            "StageBLockTableEntry",
            "StageBRamOverlayV2Bundle",
            "StageBRamOverlayV2Report",
            "StageBTmpfsBudgetAudit",
            "audit_stage_b_bk4_shadow",
            "build_stage_b_cpio_newc_archive",
            "build_stage_b_ram_overlay_v2_package",
            "generate_stage_b_init2_guard_script",
            "parse_and_audit_stage_b_cpio_newc",
            "run_stage_b_init2_sandbox_drill",
            "synthesize_stage_b_bk4_shadow",
            "verify_stage_b_ram_overlay_v2",
            "verify_stage_b_tmpfs_ddr_budget",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        self.assertEqual(PHASE_48_SCHEMA, "stage_b_ram_overlay_v2")
        self.assertEqual(PHASE_48_VERSION, "48.0.0")
        self.assertEqual(FX3_PRODUCT_MODEL_U32, 0x91030080)
        self.assertEqual(FX3_PRODUCT_MODEL_HEX, "0x91030080")
        self.assertEqual(STAGE_B_DETERMINISTIC_MTIME, 0)
        self.assertEqual(STAGE_B_DETERMINISTIC_UID, 0)
        self.assertEqual(STAGE_B_DETERMINISTIC_GID, 0)

    def test_02_fast_execution_and_overall_pass(self) -> None:
        self.assertLess(self.elapsed_s, 5.0)
        self.assertTrue(self.report.all_checks_passed, msg=f"errors={self.report.errors}")
        self.assertEqual(self.report.errors, ())
        self.assertIn(
            self.report.verification_mode,
            ("LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED", "CLEAN_ROOM_SYNTHETIC_VERIFIED"),
        )
        self.assertEqual(len(self.report.report_sha256), 64)
        self.assertNotIn("b'", self.report_json_str)
        self.assertIsNone(re.search(r'(?<![0-9A-Za-z_])b["\']', self.report_json_str))

    def test_03_hard_locked_zero_write_redlines(self) -> None:
        self.assertFalse(self.report.persistent_emmc_writes_authorized)
        self.assertFalse(self.report.persistent_write_release)
        self.assertTrue(self.report.p8_cp_mutation_forbidden)
        self.assertEqual(self.report.cp_mutation_bytes, 0)
        self.assertTrue(self.report.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(self.report.wbi_mutation_bytes, 0)
        self.assertEqual(self.report.usb_or_camera_operations, 0)

    def test_04_read_donor_bytes_readonly_strictly_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sample = Path(td) / "donor.bin"
            sample.write_bytes(b"\x7fELF\x02\x01\x01\x00")
            seen_flags = []
            real_open = os.open

            def _spy_open(path: str, flags: int, *args: object) -> int:
                seen_flags.append(flags)
                return real_open(path, flags, *args)

            with mock.patch("fx6_closure.patcher.os.open", side_effect=_spy_open):
                blob = read_donor_bytes_readonly(sample)

            self.assertEqual(blob.hex(), "7f454c4602010100")
            self.assertEqual(seen_flags, [os.O_RDONLY])

    def test_05_cpio_newc_header_metadata_mtime_uid_gid_sorted(self) -> None:
        audit = parse_and_audit_stage_b_cpio_newc(self.bundle.cpio_bytes)
        self.assertTrue(audit.valid, msg=f"cpio errors={audit.errors}")
        self.assertTrue(audit.trailer_found)
        self.assertEqual(self.bundle.cpio_bytes[:6], CPIO_NEWC_MAGIC)
        self.assertEqual(self.bundle.cpio_size % 4, 0)
        names = [e.name for e in audit.entries]
        self.assertEqual(names, sorted(names))
        for req in STAGE_B_V2_REQUIRED_CPIO_PATHS:
            self.assertIn(req, names)
        for ent in audit.entries:
            self.assertEqual(ent.mtime, 0)
            self.assertEqual(ent.uid, 0)
            self.assertEqual(ent.gid, 0)

    def test_06_cpio_determinism_identical_sha256_regardless_of_input_order(self) -> None:
        e_a = CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755, mtime=123, uid=10, gid=10)
        e_b = CpioEntrySpec(name="etc/fx6_overlay", mode=S_IFDIR | 0o755, mtime=456, uid=99, gid=99)
        e_c = CpioEntrySpec(
            name="etc/fx6_overlay/stage_b_init2_guard.sh",
            mode=S_IFREG | 0o755,
            data=b"#!/bin/sh\necho ok\n",
            mtime=999,
            uid=1000,
            gid=1000,
        )
        e_d = CpioEntrySpec(name="tmp", mode=S_IFDIR | 0o755, mtime=77)
        e_e = CpioEntrySpec(name="tmp/bk4_shadow", mode=S_IFREG | 0o644, data=b"BK4TEST", mtime=88)
        e_f = CpioEntrySpec(name="etc/fx6_overlay/bk4_shadow_meta.json", mode=S_IFREG | 0o644, data=b"{}\n")
        e_g = CpioEntrySpec(name="etc/fx6_overlay/p11_uipc_cp_shim.json", mode=S_IFREG | 0o644, data=b"{}\n")
        e_h = CpioEntrySpec(name="etc/fx6_overlay/stage_b_overlay_manifest.json", mode=S_IFREG | 0o644, data=b"{}\n")

        arch1 = build_stage_b_cpio_newc_archive([e_a, e_b, e_c, e_d, e_e, e_f, e_g, e_h])
        arch2 = build_stage_b_cpio_newc_archive([e_h, e_e, e_g, e_c, e_f, e_d, e_b, e_a])
        self.assertEqual(arch1, arch2)
        audit = parse_and_audit_stage_b_cpio_newc(arch1)
        self.assertTrue(audit.valid)

        b1 = build_stage_b_ram_overlay_v2_package(lang="en", synthetic_clean_room=True)
        b2 = build_stage_b_ram_overlay_v2_package(lang="en", synthetic_clean_room=True)
        self.assertEqual(b1.cpio_sha256, b2.cpio_sha256)
        self.assertEqual(b1.bk4_shadow_sha256, b2.bk4_shadow_sha256)

    def test_07_cpio_parser_rejects_bad_magic_and_missing_trailer(self) -> None:
        bad_magic = b"070702" + self.bundle.cpio_bytes[6:]
        self.assertFalse(parse_and_audit_stage_b_cpio_newc(bad_magic).valid)
        truncated = self.bundle.cpio_bytes[:-40]
        self.assertFalse(parse_and_audit_stage_b_cpio_newc(truncated).valid)

    def test_08_cpio_parser_rejects_nonzero_mtime_uid_gid(self) -> None:
        bad_hdr = bytearray(self.bundle.cpio_bytes)
        # mtime field is header index 5 -> offset 6 + 5*8 = 46..54
        bad_hdr[46:54] = b"00000001"
        audit_mtime = parse_and_audit_stage_b_cpio_newc(bytes(bad_hdr))
        self.assertFalse(audit_mtime.valid)
        self.assertTrue(any("non-zero mtime=1" in e for e in audit_mtime.errors))

        bad_uid = bytearray(self.bundle.cpio_bytes)
        bad_uid[22:30] = b"00000064"
        audit_uid = parse_and_audit_stage_b_cpio_newc(bytes(bad_uid))
        self.assertFalse(audit_uid.valid)
        self.assertTrue(any("non-zero uid=100" in e for e in audit_uid.errors))

    def test_09_cpio_builder_blocks_traversal_duplicates_and_nonempty_dir(self) -> None:
        with self.assertRaises(CpioFormatError):
            build_stage_b_cpio_newc_archive([CpioEntrySpec(name="../etc/shadow", mode=S_IFREG | 0o644)])
        with self.assertRaises(CpioFormatError):
            build_stage_b_cpio_newc_archive([CpioEntrySpec(name="/abs/path", mode=S_IFREG | 0o644)])
        with self.assertRaises(CpioFormatError):
            build_stage_b_cpio_newc_archive([
                CpioEntrySpec(name="a", mode=S_IFREG | 0o644),
                CpioEntrySpec(name="a", mode=S_IFREG | 0o644),
            ])
        with self.assertRaises(CpioFormatError):
            build_stage_b_cpio_newc_archive([CpioEntrySpec(name="dir", mode=S_IFDIR | 0o755, data=b"x")])

    def test_10_13_of_13_lock_table_and_manifest_parity(self) -> None:
        self.assertEqual(self.report.lock_table_count, 13)
        self.assertEqual(len(self.bundle.lock_table_13), 13)
        manifest_raw = [
            e.data for e in self.bundle.cpio_audit.entries
            if e.name == "etc/fx6_overlay/stage_b_overlay_manifest.json"
        ][0]
        manifest = json.loads(manifest_raw.decode("utf-8"))
        self.assertEqual(manifest["lock_table_count"], 13)
        self.assertEqual(len(manifest["sha256_lock_table"]), 13)
        paths = [ent.rel_path for ent in self.bundle.lock_table_13]
        self.assertEqual(paths, [p for _, p in STAGE_B_LOCK_TABLE_13_ARTIFACTS])
        self.assertTrue(self.bundle.rollback_all_matched)

        p11_raw = [
            e.data for e in self.bundle.cpio_audit.entries
            if e.name == "etc/fx6_overlay/p11_uipc_cp_shim.json"
        ][0]
        p11 = json.loads(p11_raw.decode("utf-8"))
        self.assertEqual(p11["handle_queue_id"], "0x91db059b")
        self.assertEqual(p11["rtc_queue_id"], "0x92d2091c")
        self.assertEqual(p11["rtc_mapping"], "/dev/rtc0->udate")
        self.assertEqual(p11["xlr_h1_hotshoe_vma"], "0x5d90")

    def test_11_p10_and_p12_hashes_verified(self) -> None:
        by_path = {ent.rel_path: ent for ent in self.bundle.lock_table_13}
        self.assertIn("lib/appFw.so", by_path)
        self.assertIn("lib/libWlanResource.so", by_path)
        if self.bundle.verification_mode == "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED":
            self.assertEqual(by_path["lib/appFw.so"].sha256, FX6_APPFW_STAGE_B_SHA256)
            self.assertEqual(by_path["lib/libWlanResource.so"].sha256, FX6_WLAN_RSRC_P12_SHA256)
            self.assertTrue(by_path["lib/libWlanResource.so"].sha256.startswith("47fec188"))
        else:
            self.assertEqual(len(by_path["lib/appFw.so"].sha256), 64)
            self.assertEqual(len(by_path["lib/libWlanResource.so"].sha256), 64)

    def test_12_bk4_shadow_binary_valid_and_flash_prohibited(self) -> None:
        rec, errs = parse_bk4_record(self.bundle.bk4_shadow_bytes, offset=0, record_index=0)
        self.assertIsNotNone(rec)
        self.assertEqual(errs, [])
        assert rec is not None
        self.assertTrue(rec.magic_ok)
        self.assertTrue(rec.checksum_ok)
        self.assertEqual(rec.active_byte8, 0x00)
        self.assertFalse(rec.strict_loader_selectable)
        self.assertEqual(self.bundle.bk4_shadow_bytes[0x0C:0x10], b"BK4\x00")

        u4_audit = audit_ram_shadow_bk4(self.bundle.bk4_shadow_bytes, flash_write_allowed=False)
        self.assertTrue(u4_audit.valid, msg=f"u4 audit errors={u4_audit.errors}")
        with self.assertRaises(ValueError):
            synthesize_stage_b_bk4_shadow(flash_write_allowed=True, use_clean_room=True)

    def test_13_bk4_shadow_airplane_mode_keys(self) -> None:
        for key_id, exp_byte in STAGE_B_AIRPLANE_KEYS.items():
            val = read_bk4_property_bytes(self.bundle.bk4_shadow_bytes, key_id, offset=0)
            self.assertEqual(val, bytes([exp_byte]), msg=f"key={hex(key_id)}")

    def test_14_bk4_shadow_all_four_langs_en_schinese_tchinese_japanese(self) -> None:
        expected_vals = {"en": 0x00, "japanese": 0x01, "tchinese": 0x18, "schinese": 0x19}
        seen_shas = set()
        for lang in STAGE_B_SUPPORTED_LANGS:
            raw, audit = synthesize_stage_b_bk4_shadow(lang=lang, use_clean_room=True)
            self.assertTrue(audit["valid"], msg=f"lang={lang} errors={audit['errors']}")
            prop = read_bk4_property_bytes(raw, BK_KEY_LANG, offset=0)
            self.assertEqual(prop, bytes([expected_vals[lang]]))
            self.assertEqual(STAGE_B_BK_LANG_SPECS[lang].bk_lang_value, expected_vals[lang])
            seen_shas.add(audit["sha256"])
        self.assertEqual(len(seen_shas), 4)

    def test_15_bk4_shadow_tamper_fails_closed(self) -> None:
        raw, _ = synthesize_stage_b_bk4_shadow(lang="schinese", use_clean_room=True)
        # Wrong expected lang triggers fail-closed
        wrong_lang = audit_stage_b_bk4_shadow(raw, expected_lang="en")
        self.assertFalse(wrong_lang["valid"])
        self.assertFalse(wrong_lang["bk_lang_ok"])

        # Magic tamper triggers fail-closed
        bad_magic = bytearray(raw)
        bad_magic[0x0C:0x10] = b"BAD0"
        res_magic = audit_stage_b_bk4_shadow(bytes(bad_magic), expected_lang="schinese")
        self.assertFalse(res_magic["valid"])
        self.assertFalse(res_magic["magic_ok"])

    def test_16_bk4_shadow_rejects_unsupported_lang(self) -> None:
        with self.assertRaises(ValueError):
            synthesize_stage_b_bk4_shadow(lang="klingon", use_clean_room=True)

    def test_17_tmpfs_ddr_budget_under_48mib_in_2048mib_ddr(self) -> None:
        bud = self.report.tmpfs_budget_audit
        self.assertTrue(bud.within_budget, msg=f"budget errors={bud.errors}")
        self.assertEqual(bud.fx3_ddr_total_bytes, STAGE_B_FX3_DDR_TOTAL_BYTES)
        self.assertEqual(bud.tmpfs_budget_limit_bytes, STAGE_B_TMPFS_BUDGET_LIMIT_BYTES)
        self.assertLess(bud.volatile_tmpfs_overlay_bytes, STAGE_B_TMPFS_BUDGET_LIMIT_BYTES)
        self.assertLess(bud.volatile_tmpfs_overlay_mib, STAGE_B_TMPFS_BUDGET_LIMIT_MIB)
        self.assertLess(bud.cpio_archive_bytes, STAGE_B_TMPFS_BUDGET_LIMIT_BYTES)
        self.assertGreater(bud.tmpfs_headroom_bytes, 0)
        self.assertEqual(bud.appfw_staging_mode, "ro_sd_loop_bind")

    def test_18_tmpfs_ddr_budget_rejects_over_budget_and_wrong_staging(self) -> None:
        over = verify_stage_b_tmpfs_ddr_budget(
            tmpfs_payload_sizes={"lib/appFw.so": 50 * 1024 * 1024},
            cpio_archive_bytes=40000,
            appfw_size_bytes=50 * 1024 * 1024,
            appfw_staging_mode="tmpfs_copy",
        )
        self.assertFalse(over.within_budget)
        self.assertLess(over.tmpfs_headroom_bytes, 0)
        self.assertGreaterEqual(len(over.errors), 2)

    def test_19_init2_guard_passes_failsafe_and_ld_so_preload_audits(self) -> None:
        script = generate_stage_b_init2_guard_script()
        fs_audit = verify_failsafe_hook_script(script)
        ld_audit = audit_ld_so_preload_and_overlay(script_text=script)
        self.assertTrue(fs_audit.valid, msg=f"failsafe errors={fs_audit.errors}")
        self.assertTrue(ld_audit.valid, msg=f"ld preload errors={ld_audit.errors}")
        self.assertIn("boot_attempts", script)
        self.assertIn("0x91030080", script)
        self.assertIn("export LD_LIBRARY_PATH=", script)

    def test_20_sandbox_s01_clean_stage_b_mount(self) -> None:
        sc = self.scenario_map["S01_CLEAN_STAGE_B_MOUNT"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "ADAPTED_FX6_STAGE_B")
        self.assertEqual(sc.observed_diag_code, "OK_STAGE_B_MOUNTED")
        self.assertEqual(sc.mount_count, 8)
        self.assertEqual(sc.boot_attempts_before, 0)
        self.assertEqual(sc.boot_attempts_after, 1)
        self.assertTrue(sc.ld_so_preload_untouched)
        self.assertEqual(sc.emmc_mutation_bytes, 0)
        self.assertEqual(sc.cp_mutation_bytes, 0)
        self.assertEqual(sc.wbi_mutation_bytes, 0)

    def test_21_sandbox_s02_p12_sha_mismatch(self) -> None:
        sc = self.scenario_map["S02_FAULT_P12_SHA_MISMATCH"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so")
        self.assertEqual(sc.mount_count, 0)

    def test_22_sandbox_s03_p10_missing_blob(self) -> None:
        sc = self.scenario_map["S03_FAULT_P10_MISSING_BLOB"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_VERIFY_MISSING:lib/appFw.so")
        self.assertEqual(sc.mount_count, 0)

    def test_23_sandbox_s04_boot_attempts_prelatched(self) -> None:
        sc = self.scenario_map["S04_FAULT_BOOT_ATTEMPTS_PRELATCHED"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_BOOT_ATTEMPTS_LATCHED")
        self.assertEqual(sc.boot_attempts_before, 1)
        self.assertEqual(sc.mount_count, 0)

    def test_24_sandbox_s05_bk4_magic_corruption(self) -> None:
        sc = self.scenario_map["S05_FAULT_BK4_MAGIC_CORRUPTION"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertTrue(sc.observed_diag_code.startswith("ERR_BK4_MAGIC_INVALID:"))
        self.assertEqual(sc.mount_count, 0)

    def test_25_sandbox_s06_product_model_tamper(self) -> None:
        sc = self.scenario_map["S06_FAULT_PRODUCT_MODEL_TAMPER"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_PRODUCT_MODEL_MISMATCH:0x91030099")
        self.assertEqual(sc.mount_count, 0)

    def test_26_sandbox_s07_ld_so_preload_hazard(self) -> None:
        sc = self.scenario_map["S07_FAULT_LD_SO_PRELOAD_HAZARD"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_LD_SO_PRELOAD_HAZARD")
        self.assertEqual(sc.mount_count, 0)

    def test_27_sandbox_s08_thermal_battery_reject(self) -> None:
        sc = self.scenario_map["S08_FAULT_THERMAL_BATTERY_REJECT"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_THERMAL_OR_BATTERY_PREFLIGHT_REJECT")
        self.assertEqual(sc.mount_count, 0)

    def test_28_sandbox_s09_missing_tmpfs_headroom(self) -> None:
        sc = self.scenario_map["S09_FAULT_MISSING_TMPFS_HEADROOM"]
        self.assertTrue(sc.passed, msg=f"errors={sc.errors}")
        self.assertEqual(sc.observed_branch, "STOCK_FX3_FALLBACK")
        self.assertEqual(sc.observed_diag_code, "ERR_TMPFS_HEADROOM_EXHAUSTED")
        self.assertEqual(sc.mount_count, 0)

    def test_29_all_9_scenarios_and_tempdir_clean_no_repo_artifacts(self) -> None:
        drill = self.report.sandbox_drill
        self.assertEqual(drill.scenario_count, 9)
        self.assertEqual(drill.passed_count, 9)
        self.assertEqual(
            tuple(s.scenario_id for s in drill.scenarios),
            STAGE_B_INIT2_SANDBOX_SCENARIOS,
        )
        self.assertTrue(drill.clean_mount_verified)
        self.assertTrue(drill.all_faults_fail_closed)
        self.assertTrue(drill.temp_dir_cleaned)
        closure_dir = Path(__file__).resolve().parents[1]
        for ext in (".cpio", ".bin", ".vfat", ".pyc"):
            hits = list(closure_dir.rglob(f"*{ext}"))
            self.assertEqual(hits, [], msg=f"Found forbidden files with ext {ext}: {hits}")

    def test_30_cli_verify_stage_b_ram_overlay_clean_room_lang_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main.main(
                ["verify-stage-b-ram-overlay", "--clean-room", "--lang", "tchinese", "--json"]
            )
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotIn("b'", rendered)
        payload = json.loads(rendered)
        self.assertEqual(payload["schema"], PHASE_48_SCHEMA)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["lang"], "tchinese")
        self.assertEqual(payload["bk_lang_spec"]["bk_lang_value"], 0x18)
        self.assertEqual(payload["lock_table_count"], 13)
        self.assertEqual(payload["sandbox_drill"]["passed_count"], 9)
        self.assertLess(payload["tmpfs_budget_audit"]["volatile_tmpfs_overlay_mib"], 48.0)


if __name__ == "__main__":
    unittest.main()
