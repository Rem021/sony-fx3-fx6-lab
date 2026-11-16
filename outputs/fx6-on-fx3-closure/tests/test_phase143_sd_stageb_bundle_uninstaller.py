"""Phase 143 dual-mode test suite: Reproducible BYOF SD-Card Stage-B Deployment Bundle,
`im.elf` Escape-Hatch Launcher & `H0 == H3` Factory-Byte-Identical Uninstaller Verifier.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True

import fx6_closure
from fx3_safety.runtime_antibrick_guards import audit_ld_so_preload_and_overlay
from fx6_closure.__main__ import main as cli_main
from fx6_closure.donor_paths import is_forced_clean_room
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (
    BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH,
    BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE,
    BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID,
    BLOCKED_UNVERIFIED_TIER0_RECEIPT,
    ERR_DDR_TMPFS_BUDGET_EXCEEDED,
    ERR_ORIG_SHA256_MISMATCH_ABORT,
    ESCAPE_HATCH_ABSENT_LATENCY_US,
    ESCAPE_HATCH_MAX_LATENCY_US,
    ESCAPE_HATCH_SCENARIO_IDS,
    FOUR_EPOCHS,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX6_APPFW_EXPECTED_SIZE,
    FX6_CORE_UXC_ASSETS,
    FX6_UXC_TOTAL_BYTES,
    FX6_UXC_TOTAL_COUNT,
    PHASE_143_SCHEMA,
    PHASE_143_VERSION,
    POWER_LOSS_DRILL_IDS,
    SD_BK4_SHADOW_SEED_RELPATH,
    SD_DIAG_LOG_RELPATH,
    SD_MANIFEST_RELPATH,
    SD_PHYSICAL_MEDIA_WRITTEN,
    SD_REQUIRED_TREE_PATHS,
    SD_SHIM_FBINIT9_RELPATH,
    SD_SHIM_MPR_BRIDGE_RELPATH,
    SD_STAGEB_RAM_BUDGET_LIMIT_BYTES,
    SD_STAGEB_RAM_BUDGET_LIMIT_MIB,
    SD_STOP_FLAG_RELPATH,
    SD_UNINSTALL_MANIFEST_RELPATH,
    SD_USR_OVERLAY_PREFIX,
    SIXTEEN_STORAGE_SURFACES,
    _SimulatedSixteenSurfaceCameraStorage,
    _synthetic_stock_im_elf_bytes,
    _validate_exfat_fat32_relpath,
    audit_pillar1_bundle_builder,
    audit_pillar4_no_physical_flash_guard,
    build_sd_stageb_deployment_bundle,
    default_tier0_receipt_binding,
    generate_im_elf_escape_hatch_launcher,
    inspect_phase143_donors_readonly,
    read_only_o_rdonly_bytes,
    read_only_o_rdonly_digest_and_header,
    run_4epoch_h0_to_h3_and_power_loss_drills,
    run_escape_hatch_launcher_sandbox_drills,
    run_phase143_sd_stageb_bundle_uninstaller_audit,
    validate_sd_stageb_tree,
    validate_tier0_receipt_body_binding,
    verify_phase143_report,
)


class TestPhase143SdStageBBundleUninstaller(unittest.TestCase):
    """44 dual-mode unit tests across all 4 Phase 143 pillars."""

    # ------------------------------------------------------------------
    # Package Exports, Read-Only O_RDONLY, Master Audit & Tamper (1..10)
    # ------------------------------------------------------------------

    def test_01_public_exports_present_in_package_init(self) -> None:
        for sym in (
            "PHASE_143_SCHEMA",
            "PHASE_143_VERSION",
            "SIXTEEN_STORAGE_SURFACES",
            "FOUR_EPOCHS",
            "run_phase143_sd_stageb_bundle_uninstaller_audit",
            "verify_phase143_report",
            "build_sd_stageb_deployment_bundle",
            "validate_sd_stageb_tree",
            "generate_im_elf_escape_hatch_launcher",
            "run_escape_hatch_launcher_sandbox_drills",
            "run_4epoch_h0_to_h3_and_power_loss_drills",
            "inspect_phase143_donors_readonly",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing export: {sym}")

    def test_02_master_audit_passes_current_mode(self) -> None:
        rep = run_phase143_sd_stageb_bundle_uninstaller_audit()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.schema, PHASE_143_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_143_VERSION)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.sd_physical_media_written)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_slices_emitted, 0)
        self.assertEqual(rep.errors, ())
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        v = verify_phase143_report(rep.to_dict())
        self.assertTrue(v.valid, v.errors)

    def test_03_master_audit_clean_room_deterministic_hash(self) -> None:
        r1 = run_phase143_sd_stageb_bundle_uninstaller_audit(synthetic_clean_room=True)
        r2 = run_phase143_sd_stageb_bundle_uninstaller_audit(synthetic_clean_room=True)
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertTrue(verify_phase143_report(r1.to_dict()).valid)

    def test_04_donor_inspection_readonly_covers_im_elf_appfw_and_uxc(self) -> None:
        insp = inspect_phase143_donors_readonly()
        self.assertTrue(insp.all_checks_passed, insp.errors)
        self.assertEqual(insp.fx3_im_elf_size, FX3_IM_ELF_EXPECTED_SIZE)
        self.assertEqual(insp.fx3_im_elf_sha256, FX3_IM_ELF_EXPECTED_SHA256)
        self.assertTrue(insp.fx3_im_elf_aarch64_ok)
        self.assertEqual(insp.fx6_appfw_donor_size, FX6_APPFW_EXPECTED_SIZE)
        self.assertEqual(insp.fx6_uxc_asset_count, FX6_UXC_TOTAL_COUNT)
        self.assertEqual(insp.fx6_uxc_total_bytes, FX6_UXC_TOTAL_BYTES)
        self.assertEqual(insp.fx6_core_uxc_verified_count, len(FX6_CORE_UXC_ASSETS))
        self.assertEqual(insp.stage_b_13_lock_count, 13)
        self.assertEqual(insp.raw_firmware_slices_emitted, 0)

    def test_05_read_only_o_rdonly_helpers_exact_and_reject_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "donor_ro.bin"
            payload = b"SONY_FX3_RO_TEST_" + bytes(range(64))
            p.write_bytes(payload)
            self.assertEqual(read_only_o_rdonly_bytes(p), payload)
            sz, sha, head = read_only_o_rdonly_digest_and_header(p)
            self.assertEqual(sz, len(payload))
            self.assertEqual(sha, hashlib.sha256(payload).hexdigest())
            self.assertEqual(head, payload[:64])
            sym = Path(td) / "sym.bin"
            sym.symlink_to(p)
            if hasattr(os, "O_NOFOLLOW"):
                with self.assertRaises(OSError):
                    read_only_o_rdonly_bytes(sym)

    def test_06_json_output_contains_zero_raw_bytes_repr_or_elf_header(self) -> None:
        rep = run_phase143_sd_stageb_bundle_uninstaller_audit(synthetic_clean_room=True)
        raw_json = rep.to_deterministic_json()
        self.assertNotIn("\\x7fELF", raw_json)
        self.assertNotIn("b'FX", raw_json)
        self.assertTrue(verify_phase143_report(json.loads(raw_json)).valid)

    def test_07_tamper_verifier_rejects_modified_field_and_unlocked_flags(self) -> None:
        rep = run_phase143_sd_stageb_bundle_uninstaller_audit(synthetic_clean_room=True)
        tampered = copy.deepcopy(rep.to_dict())
        tampered["pillar3_atomic_uninstaller_h0_h3"]["h0_equals_h3_count"] = 15
        res = verify_phase143_report(tampered)
        self.assertFalse(res.valid)
        self.assertTrue(any("tamper" in e for e in res.errors))

        for field in (
            "persistent_emmc_writes_authorized",
            "sd_physical_media_written",
            "persistent_write_release",
        ):
            d = copy.deepcopy(rep.to_dict())
            d[field] = True
            r = verify_phase143_report(d)
            self.assertFalse(r.valid)
            self.assertTrue(any(field in e for e in r.errors))

    def test_08_tamper_verifier_rejects_nonzero_device_writes_or_raw_slices(self) -> None:
        rep = run_phase143_sd_stageb_bundle_uninstaller_audit(synthetic_clean_room=True)
        for field in ("physical_device_writes", "raw_firmware_slices_emitted"):
            d = copy.deepcopy(rep.to_dict())
            d[field] = 1
            r = verify_phase143_report(d)
            self.assertFalse(r.valid)
            self.assertTrue(any(field in e for e in r.errors))

    def test_09_audit_pillar4_hard_lock_enforced(self) -> None:
        p4_ok = audit_pillar4_no_physical_flash_guard(raw_pnflasha_blocked=True)
        self.assertTrue(p4_ok.all_checks_passed)
        self.assertFalse(p4_ok.persistent_emmc_writes_authorized)
        self.assertFalse(p4_ok.sd_physical_media_written)
        self.assertFalse(p4_ok.persistent_write_release)
        self.assertEqual(p4_ok.physical_device_writes, 0)
        p4_bad = audit_pillar4_no_physical_flash_guard(raw_pnflasha_blocked=False)
        self.assertFalse(p4_bad.all_checks_passed)

    def test_10_all_4_languages_supported_in_bundle_builder(self) -> None:
        for lang in ("en", "schinese", "tchinese", "japanese"):
            b = build_sd_stageb_deployment_bundle(lang=lang, synthetic_clean_room=True)
            self.assertEqual(b.lang, lang)
            self.assertEqual(len(b.lock_table_13), 13)
            self.assertLess(b.ram_tmpfs_bytes, SD_STAGEB_RAM_BUDGET_LIMIT_BYTES)
        with self.assertRaises(ValueError):
            build_sd_stageb_deployment_bundle(lang="klingon", synthetic_clean_room=True)

    # ------------------------------------------------------------------
    # Pillar 1: BYOF SD-Card Stage-B Tree & Signed Manifest Builder (11..21)
    # ------------------------------------------------------------------

    def test_11_pillar1_required_sd_tree_paths_present(self) -> None:
        p1, bundle = audit_pillar1_bundle_builder()
        self.assertTrue(p1.all_checks_passed, p1.errors)
        self.assertTrue(p1.sd_tree_valid)
        self.assertTrue(p1.required_paths_present)
        for req in SD_REQUIRED_TREE_PATHS:
            self.assertIn(req, bundle.files_by_relpath)
        self.assertTrue(
            any(k.startswith(f"{SD_USR_OVERLAY_PREFIX}/lib/appFw.so") for k in bundle.files_by_relpath)
        )

    def test_12_pillar1_13_stageb_locks_verified_and_consistent(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        self.assertEqual(len(bundle.lock_table_13), 13)
        self.assertEqual(bundle.boot_manifest["lock_table_13_count"], 13)
        ok, errs = validate_sd_stageb_tree(
            bundle.files_by_relpath,
            expected_body_serial=bundle.target_body_serial,
            expected_emmc_cid=bundle.target_emmc_cid,
        )
        self.assertTrue(ok, errs)

    def test_13_pillar1_ram_tmpfs_strictly_under_64mib_ddr_budget(self) -> None:
        p1, bundle = audit_pillar1_bundle_builder(synthetic_clean_room=True)
        self.assertTrue(p1.within_64mib_ddr_budget)
        self.assertEqual(p1.ram_budget_limit_mib, SD_STAGEB_RAM_BUDGET_LIMIT_MIB)
        self.assertLess(bundle.ram_tmpfs_bytes, SD_STAGEB_RAM_BUDGET_LIMIT_BYTES)
        self.assertTrue(p1.budget_overrun_rejected)

    def test_14_pillar1_rejects_budget_overrun_ge_64mib(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_sd_stageb_deployment_bundle(
                injected_extra_tmpfs_bytes=64 * 1024 * 1024,
                synthetic_clean_room=True,
            )
        self.assertIn(ERR_DDR_TMPFS_BUDGET_EXCEEDED, str(ctx.exception))

    def test_15_pillar1_refuses_foreign_camera_serial_mismatch(self) -> None:
        foreign_receipt = default_tier0_receipt_binding(body_serial="8887776")
        with self.assertRaises(ValueError) as ctx:
            build_sd_stageb_deployment_bundle(
                tier0_receipt=foreign_receipt,
                target_body_serial="3784192",
                synthetic_clean_room=True,
            )
        self.assertIn(BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH, str(ctx.exception))

    def test_16_pillar1_refuses_foreign_emmc_cid_mismatch(self) -> None:
        foreign_cid = "220100424a54443452069a12c388591c"
        foreign_receipt = default_tier0_receipt_binding(emmc_cid=foreign_cid)
        with self.assertRaises(ValueError) as ctx:
            build_sd_stageb_deployment_bundle(
                tier0_receipt=foreign_receipt,
                synthetic_clean_room=True,
            )
        self.assertIn(BLOCKED_FOREIGN_CAMERA_TIER0_SERIAL_MISMATCH, str(ctx.exception))

    def test_17_pillar1_refuses_unverified_tier0_receipt_or_bad_magic(self) -> None:
        unverified = default_tier0_receipt_binding(readback_verified=False)
        ok, errs = validate_tier0_receipt_body_binding(
            unverified,
            target_model_id="0x91030080",
            target_body_serial=unverified.body_serial,
            target_emmc_cid=unverified.emmc_cid,
        )
        self.assertFalse(ok)
        self.assertTrue(any(BLOCKED_UNVERIFIED_TIER0_RECEIPT in e for e in errs))

        bad_magic = copy.copy(default_tier0_receipt_binding())
        bad_magic = type(bad_magic)(**{**bad_magic.__dict__, "receipt_magic": "BADMAGIC"})
        ok2, errs2 = validate_tier0_receipt_body_binding(
            bad_magic,
            target_model_id="0x91030080",
            target_body_serial=bad_magic.body_serial,
            target_emmc_cid=bad_magic.emmc_cid,
        )
        self.assertFalse(ok2)
        self.assertTrue(any(BLOCKED_UNVERIFIED_TIER0_RECEIPT in e for e in errs2))

    def test_18_pillar1_refuses_synthetic_or_trivial_serials_and_wrong_model(self) -> None:
        for bad_serial in ("00000000", "12345678"):
            rcpt = default_tier0_receipt_binding(body_serial=bad_serial)
            ok, errs = validate_tier0_receipt_body_binding(
                rcpt,
                target_model_id="0x91030080",
                target_body_serial=bad_serial,
                target_emmc_cid=rcpt.emmc_cid,
            )
            self.assertFalse(ok)
            self.assertTrue(any(BLOCKED_SYNTHETIC_OR_INVALID_BODY_ID in e for e in errs))

        fx6_model_rcpt = default_tier0_receipt_binding(model_id="0x91040086")
        ok_m, _ = validate_tier0_receipt_body_binding(
            fx6_model_rcpt,
            target_model_id="0x91030080",
            target_body_serial=fx6_model_rcpt.body_serial,
            target_emmc_cid=fx6_model_rcpt.emmc_cid,
        )
        self.assertFalse(ok_m)

    def test_19_exfat_fat32_relpath_validator_blocks_illegal_chars_and_traversal(self) -> None:
        self.assertTrue(_validate_exfat_fat32_relpath("FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST")[0])
        for bad in (
            "/leading/slash",
            "FX6_STAGEB/../etc/passwd",
            "FX6_STAGEB/bad:name.txt",
            "FX6_STAGEB/bad*glob",
            "FX6_STAGEB\\backslash",
            "FX6_STAGEB/" + "a" * 256,
        ):
            self.assertFalse(_validate_exfat_fat32_relpath(bad)[0], f"Should fail: {bad}")

    def test_20_validate_sd_stageb_tree_detects_missing_or_tampered_artifact(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        files = dict(bundle.files_by_relpath)
        files["FX6_STAGEB/usr_overlay/lib/libfan.so"] = b"CORRUPTED"
        ok, errs = validate_sd_stageb_tree(
            files,
            expected_body_serial=bundle.target_body_serial,
            expected_emmc_cid=bundle.target_emmc_cid,
        )
        self.assertFalse(ok)
        self.assertTrue(any("SHA-256 mismatch" in e for e in errs))

        files2 = dict(bundle.files_by_relpath)
        del files2[SD_UNINSTALL_MANIFEST_RELPATH]
        ok2, errs2 = validate_sd_stageb_tree(
            files2,
            expected_body_serial=bundle.target_body_serial,
            expected_emmc_cid=bundle.target_emmc_cid,
        )
        self.assertFalse(ok2)
        self.assertTrue(any("Missing required SD path" in e for e in errs2))

    def test_21_validate_sd_stageb_tree_detects_corrupt_bk4_seed(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        files = dict(bundle.files_by_relpath)
        files[SD_BK4_SHADOW_SEED_RELPATH] = b"BAD_BK4_SEED"
        ok, errs = validate_sd_stageb_tree(
            files,
            expected_body_serial=bundle.target_body_serial,
            expected_emmc_cid=bundle.target_emmc_cid,
        )
        self.assertFalse(ok)
        self.assertTrue(any("Invalid BK4" in e for e in errs))

    # ------------------------------------------------------------------
    # Pillar 2: /usr/bin/im.elf Escape-Hatch Launcher & 3 Bypasses (22..30)
    # ------------------------------------------------------------------

    def test_22_launcher_passes_runtime_antibrick_ld_so_preload_guard(self) -> None:
        script = generate_im_elf_escape_hatch_launcher()
        res = audit_ld_so_preload_and_overlay(
            script_text=script,
            require_clear_before_exec_for_ram_overlay=False,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertNotIn("/dev/pnflasha", script)

    def test_23_pillar2_all_6_escape_hatch_sandbox_scenarios_pass(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        self.assertTrue(p2.all_checks_passed, p2.errors)
        self.assertEqual(p2.scenario_count, len(ESCAPE_HATCH_SCENARIO_IDS))
        self.assertEqual(p2.passed_scenario_count, 6)
        self.assertTrue(p2.ld_so_preload_untouched)

    def test_24_escape_hatch_1_sd_absent_under_50us(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        self.assertTrue(p2.eh1_sd_absent_under_50us_ok)
        self.assertEqual(p2.eh1_observed_latency_us, ESCAPE_HATCH_ABSENT_LATENCY_US)
        self.assertLess(p2.eh1_observed_latency_us, ESCAPE_HATCH_MAX_LATENCY_US)

    def test_25_escape_hatch_2_stop_flag_and_combo_key_auto_uninstall(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        self.assertTrue(p2.eh2_combo_and_stop_flag_ok)
        self.assertTrue(p2.eh2_auto_uninstall_hook_ok)
        by_id = {s.scenario_id: s for s in p2.scenarios}
        self.assertFalse(by_id["EH2A_STOP_STAGEB_FLAG_BYPASS"].stageb_loaded)
        self.assertEqual(by_id["EH2A_STOP_STAGEB_FLAG_BYPASS"].stock_orig_exec_count, 1)
        self.assertTrue(by_id["EH2B_COMBO_KEY_BYPASS_AUTO_UNINSTALL"].auto_uninstall_triggered)

    def test_26_escape_hatch_3_tampered_artifact_writes_diag_log_and_falls_back(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        self.assertTrue(p2.eh3_fail_closed_diag_log_ok)
        by_id = {s.scenario_id: s for s in p2.scenarios}
        eh3a = by_id["EH3A_TAMPERED_ARTIFACT_SHA256_FAIL_CLOSED"]
        self.assertTrue(eh3a.diag_log_written)
        self.assertEqual(eh3a.diag_reason, "ERR_SHA256_MISMATCH")
        self.assertFalse(eh3a.stageb_loaded)
        self.assertEqual(eh3a.stock_orig_exec_count, 1)

    def test_27_escape_hatch_3_foreign_serial_manifest_rejected_fail_closed(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        by_id = {s.scenario_id: s for s in p2.scenarios}
        eh3b = by_id["EH3B_FOREIGN_SERIAL_MANIFEST_FAIL_CLOSED"]
        self.assertTrue(eh3b.passed)
        self.assertTrue(eh3b.diag_log_written)
        self.assertEqual(eh3b.diag_reason, "ERR_SERIAL_OR_MANIFEST_CORRUPT")
        self.assertFalse(eh3b.stageb_loaded)

    def test_28_nominal_stageb_authenticated_boot_succeeds_with_zero_emmc_writes(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        p2 = run_escape_hatch_launcher_sandbox_drills(bundle)
        self.assertTrue(p2.nominal_stageb_boot_ok)
        by_id = {s.scenario_id: s for s in p2.scenarios}
        nom = by_id["NOMINAL_STAGEB_AUTHENTICATED_BOOT"]
        self.assertTrue(nom.stageb_loaded)
        self.assertEqual(nom.stock_orig_exec_count, 0)
        self.assertEqual(nom.emmc_writes, 0)

    def test_29_missing_artifact_on_sd_triggers_eh3_fail_closed_diag_log(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        script = generate_im_elf_escape_hatch_launcher(expected_body_serial=bundle.target_body_serial)
        import subprocess

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "usr" / "bin").mkdir(parents=True)
            (root / "usr" / "lib").mkdir(parents=True)
            (root / "tmp").mkdir(parents=True)
            sd_dir = root / "mnt" / "sd"
            for rel_p, blob in bundle.files_by_relpath.items():
                if rel_p.endswith("libfan.so"):
                    continue  # omit artifact
                dst = sd_dir / rel_p
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(blob)
            launcher_p = root / "usr" / "bin" / "im.elf"
            launcher_p.write_text(script, encoding="utf-8")
            env = dict(os.environ)
            env["FX3_LAUNCHER_PREFIX"] = str(root)
            env["FX3_LAUNCHER_DRY_RUN"] = "1"
            proc = subprocess.run(["/bin/sh", str(launcher_p)], env=env, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0)
            diag_txt = (sd_dir / SD_DIAG_LOG_RELPATH).read_text(encoding="utf-8")
            self.assertIn("ERR_ARTIFACT_MISSING", diag_txt)
            self.assertIn("libfan.so", diag_txt)

    def test_30_launcher_script_sha256_is_deterministic(self) -> None:
        s1 = generate_im_elf_escape_hatch_launcher(expected_body_serial="3784192")
        s2 = generate_im_elf_escape_hatch_launcher(expected_body_serial="3784192")
        self.assertEqual(s1, s2)
        self.assertEqual(hashlib.sha256(s1.encode()).hexdigest(), hashlib.sha256(s2.encode()).hexdigest())

    # ------------------------------------------------------------------
    # Pillar 3: Atomic Uninstaller & H0 == H3 Across 16 Surfaces (31..40)
    # ------------------------------------------------------------------

    def test_31_pillar3_covers_exact_16_surfaces_and_4_epochs(self) -> None:
        self.assertEqual(len(SIXTEEN_STORAGE_SURFACES), 16)
        self.assertEqual(len(FOUR_EPOCHS), 4)
        script = generate_im_elf_escape_hatch_launcher()
        p3 = run_4epoch_h0_to_h3_and_power_loss_drills(launcher_script=script)
        self.assertTrue(p3.all_checks_passed, p3.errors)
        self.assertEqual(p3.surface_count, 16)
        self.assertEqual(p3.h0_equals_h3_count, 16)
        self.assertTrue(p3.h0_equals_h3_all_16)
        self.assertEqual(tuple(p.surface_id for p in p3.surface_parities), SIXTEEN_STORAGE_SURFACES)

    def test_32_pillar3_h1_modifies_only_p15_and_h2_zero_cp_wbi_cal_drift(self) -> None:
        script = generate_im_elf_escape_hatch_launcher()
        p3 = run_4epoch_h0_to_h3_and_power_loss_drills(launcher_script=script)
        self.assertTrue(p3.h1_only_p15_changed)
        self.assertTrue(p3.h2_zero_cp_wbi_cal_drift)
        for sp in p3.surface_parities:
            if sp.surface_id == "p15":
                self.assertTrue(sp.h1_changed)
            else:
                self.assertFalse(sp.h1_changed)
            self.assertTrue(sp.h0_equals_h3)

    def test_33_pillar3_zero_residual_orig_or_stageb_on_p15_and_p6(self) -> None:
        script = generate_im_elf_escape_hatch_launcher()
        p3 = run_4epoch_h0_to_h3_and_power_loss_drills(launcher_script=script)
        self.assertEqual(p3.residual_orig_files_p15, ())
        self.assertEqual(p3.residual_stageb_files_p15, ())
        self.assertEqual(p3.residual_stageb_files_p6, ())

    def test_34_pillar3_all_5_power_loss_and_security_drills_pass(self) -> None:
        script = generate_im_elf_escape_hatch_launcher()
        p3 = run_4epoch_h0_to_h3_and_power_loss_drills(launcher_script=script)
        self.assertEqual(p3.power_loss_drill_count, len(POWER_LOSS_DRILL_IDS))
        self.assertEqual(p3.power_loss_drills_passed, 5)
        for d in p3.power_loss_drills:
            self.assertTrue(d.passed, f"{d.drill_id}: {d.errors}")
            self.assertTrue(d.h0_equals_h3_after_recovery)
            self.assertEqual(d.matched_surfaces_after_recovery, 16)
            self.assertEqual(d.residual_orig_count, 0)
            self.assertEqual(d.residual_stageb_count, 0)

    def test_35_power_loss_cutpoint_before_rename_recovers_idempotently(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        h0 = cam.snapshot_16_hashes()
        cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=b"LAUNCHER")
        mid = cam.atomic_uninstall_on_cnflasha15(crash_cutpoint="AFTER_TMP_WRITE_BEFORE_RENAME")
        self.assertEqual(mid, "CRASHED_BEFORE_RENAME")
        self.assertIn("/usr/bin/im.elf.orig", cam.p15_files)
        self.assertIn("/usr/bin/im.elf.restore.tmp", cam.p15_files)
        fin = cam.atomic_uninstall_on_cnflasha15()
        self.assertEqual(fin, "CLEAN_UNINSTALLED_H0_EQ_H3")
        self.assertEqual(cam.snapshot_16_hashes(), h0)

    def test_36_power_loss_cutpoint_after_rename_before_unlink_boots_stock_and_cleans_up(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        h0 = cam.snapshot_16_hashes()
        cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=b"LAUNCHER")
        mid = cam.atomic_uninstall_on_cnflasha15(crash_cutpoint="AFTER_RENAME_BEFORE_ORIG_UNLINK")
        self.assertEqual(mid, "CRASHED_BEFORE_ORIG_UNLINK")
        # im.elf is ALREADY stock byte-identical even before retry
        self.assertEqual(cam.p15_files["/usr/bin/im.elf"], stock)
        self.assertIn("/usr/bin/im.elf.orig", cam.p15_files)
        fin = cam.atomic_uninstall_on_cnflasha15()
        self.assertEqual(fin, "CLEAN_UNINSTALLED_H0_EQ_H3")
        self.assertEqual(cam.snapshot_16_hashes(), h0)

    def test_37_corrupt_orig_aborts_fail_closed_then_recovers_from_sd_rescue(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        h0 = cam.snapshot_16_hashes()
        cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=b"LAUNCHER")
        cam.p15_files["/usr/bin/im.elf.orig"] = b"CORRUPT_ORIG"
        with self.assertRaises(ValueError) as ctx:
            cam.atomic_uninstall_on_cnflasha15()
        self.assertIn(ERR_ORIG_SHA256_MISMATCH_ABORT, str(ctx.exception))
        # Launcher still intact, not overwritten with corrupt bytes
        self.assertEqual(cam.p15_files["/usr/bin/im.elf"], b"LAUNCHER")
        fin = cam.atomic_uninstall_on_cnflasha15(sd_rescue_stock_bytes=stock)
        self.assertEqual(fin, "CLEAN_UNINSTALLED_H0_EQ_H3")
        self.assertEqual(cam.snapshot_16_hashes(), h0)

    def test_38_raw_pnflasha15_install_and_uninstall_hard_blocked(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        with self.assertRaises(PermissionError) as ctx_i:
            cam.install_stageb_on_cnflasha15(block_device="/dev/pnflasha15", launcher_bytes=b"LAUNCHER")
        self.assertIn(BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE, str(ctx_i.exception))
        with self.assertRaises(PermissionError) as ctx_u:
            cam.atomic_uninstall_on_cnflasha15(block_device="/dev/pnflasha15")
        self.assertIn(BLOCKED_RAW_PNFLASHA_PLAINTEXT_WRITE, str(ctx_u.exception))
        self.assertEqual(cam.raw_pnflasha_write_attempts, 2)

    def test_39_install_rejects_corrupted_stock_im_elf_precheck(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        cam.p15_files["/usr/bin/im.elf"] = b"MODIFIED_PRE_H1"
        with self.assertRaises(ValueError):
            cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=b"LAUNCHER")

    def test_40_uninstall_is_idempotent_when_run_twice(self) -> None:
        stock = _synthetic_stock_im_elf_bytes()
        cam = _SimulatedSixteenSurfaceCameraStorage(stock_im_elf_bytes=stock)
        h0 = cam.snapshot_16_hashes()
        cam.install_stageb_on_cnflasha15(block_device="/dev/cnflasha15", launcher_bytes=b"LAUNCHER")
        self.assertEqual(cam.atomic_uninstall_on_cnflasha15(), "CLEAN_UNINSTALLED_H0_EQ_H3")
        self.assertEqual(cam.atomic_uninstall_on_cnflasha15(), "CLEAN_UNINSTALLED_H0_EQ_H3")
        self.assertEqual(cam.snapshot_16_hashes(), h0)

    # ------------------------------------------------------------------
    # CLI Integration & Cross-Mode Parity (41..44)
    # ------------------------------------------------------------------

    def test_41_cli_verify_sd_stageb_bundle_uninstaller_summary_mode(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-sd-stageb-bundle-uninstaller", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=OK", out)
        self.assertIn(f"schema={PHASE_143_SCHEMA}", out)
        self.assertIn("h0_eq_h3=16/16", out)
        self.assertIn("emmc_writes_auth=False", out)
        self.assertIn("sd_written=False", out)

    def test_42_cli_verify_sd_stageb_bundle_uninstaller_json_and_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "phase143.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-sd-stageb-bundle-uninstaller",
                        "--clean-room",
                        "--lang",
                        "schinese",
                        "--json",
                        "--output",
                        str(out_path),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["lang"], "schinese")
            self.assertTrue(verify_phase143_report(payload).valid)
            self.assertTrue(out_path.is_file())
            self.assertEqual(json.loads(out_path.read_text(encoding="utf-8")), payload)

    def test_43_cli_honors_live_mode_when_not_forced_clean_room(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-sd-stageb-bundle-uninstaller", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(payload["verification_mode"], expected_mode)
        self.assertTrue(verify_phase143_report(payload).valid)

    def test_44_uninstall_manifest_binds_stock_im_elf_sha256_and_16_surfaces(self) -> None:
        bundle = build_sd_stageb_deployment_bundle(synthetic_clean_room=True)
        um = bundle.uninstall_manifest
        self.assertEqual(um["stock_im_elf_sha256"], FX3_IM_ELF_EXPECTED_SHA256)
        self.assertEqual(um["crypto_block_device"], "/dev/cnflasha15")
        self.assertEqual(um["forbidden_raw_block_device"], "/dev/pnflasha15")
        self.assertEqual(tuple(um["expected_clean_surfaces"]), SIXTEEN_STORAGE_SURFACES)
        self.assertFalse(um["persistent_emmc_writes_authorized"])


if __name__ == "__main__":
    unittest.main()
