"""Phase 26 Dual-Mode Integration Test Suite: Stage-B P12 (`libWlanResource.so` `0x70d4` Infinite-`usleep` Guard + `BK4\\0` Cold-Boot Airplane-Mode RAM Shadow).

Verifies end-to-end Phase 26 wiring into `fx6_closure`:
- `patcher.py`: `P12_WLAN_FATAL_GUARD_SPEC`, `FX6_WLAN_RSRC_DONOR_SHA256`, `FX6_WLAN_RSRC_P12_SHA256`,
  `STAGE_B_WITH_P12_PATCH_SPECS`, `build_stage_b_wlan_rsrc_image`, zero-overlap & bit-exact rollback,
  and 100% backward compatibility with `STAGE_A_PATCH_SPECS` & `STAGE_B_PATCH_SPECS`.
- `candidate_builder.py`: `CandidateDryRunReport` P12 fields, `run_offline_candidate_dry_run`
  (`include_p12_wireless_guard`, `precomputed_wireless_fault_isolation`, `corrupt_wireless_guard` -> Gate `G12` block).
- `hardware_readiness_packet.py`: `Phase_22_p12_wf12_wireless_fault_isolation` entry & offline completion gate.
- `__main__.py`: `verify-wireless-guard [--clean-room] [--output PATH]` and `dry-run-candidate` P12 JSON fields.
- Dual-mode execution: 21 Clean-Room/Synthetic/Unit tests always pass under `FX3_FX6_FORCE_CLEAN_ROOM=1`,
  and all 26 tests pass when read-only local Sony donor binaries are present.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

import fx6_closure
from fx6_closure.__main__ import main as cli_main
from fx6_closure.candidate_builder import (
    CandidateDryRunReport,
    run_offline_candidate_dry_run,
)
from fx6_closure.donor_paths import (
    is_forced_clean_room,
    resolve_fx3_modules_dir,
    resolve_fx6_donor_lib_dir,
)
from fx6_closure.hardware_readiness_packet import (
    READINESS_PACKET_SCHEMA,
    build_stage_a_hardware_readiness_packet,
    populate_tier0_capture_bundle_fixture,
)
from fx6_closure.patcher import (
    ALL_PHASE2_TARGET_SPECS,
    FX6_APPFW_STAGE_A_SHA256,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    P12_WLAN_FATAL_GUARD_SPEC,
    P12_WLAN_FATAL_GUARD_VMA,
    STAGE_A_PATCH_SPECS,
    STAGE_B_PATCH_SPECS,
    STAGE_B_WITH_P12_PATCH_SPECS,
    PatchVerificationError,
    apply_patch_spec,
    build_stage_b_wlan_rsrc_image,
    get_target_patch_specs,
    rollback_patch_spec,
    verify_patch_sites_non_overlapping,
)
from fx6_closure.tier0_unicorn_verifier import (
    Tier0UnicornRunResult,
    compile_tier0_worker_shared_object,
    run_tier0_worker_in_unicorn,
)
from fx6_closure.wireless_fault_isolation_verifier import (
    APPLICATION_SYSTEM_INIT_BUDGET_MS,
    FX6_WLAN_RSRC_SHA256,
    P12_WLAN_FATAL_GUARD_SPEC as VERIFIER_P12_SPEC,
    PHASE_22_SCHEMA,
    SONY_NOTICE_00342260_ID,
    Phase22WirelessFaultIsolationReport,
    build_clean_room_phase22_fixtures,
    run_phase22_wireless_fault_isolation_verification,
)


_CLEAN_ROOM_SKIP_REASON = "FX3_FX6_FORCE_CLEAN_ROOM=1 or read-only local donor binaries absent"


def _is_clean_room_or_donor_missing() -> bool:
    if is_forced_clean_room():
        return True
    fx6_dir = resolve_fx6_donor_lib_dir()
    fx3_dir = resolve_fx3_modules_dir()
    required = (
        fx6_dir / "appFw.so",
        fx6_dir / "libInfraSetupFile.so",
        fx6_dir / "libInfraMediaCommon.so",
        fx6_dir / "libInfraMediaConfig.so",
        fx6_dir / "libInfraAppRemoteBoard.so",
        fx6_dir / "libWlanResource.so",
        fx6_dir / "libfan.so",
        fx3_dir / "upm.ko",
    )
    return any(not p.is_file() for p in required)


class TestPhase26StageBP12Integration(unittest.TestCase):
    """Dual-mode tests for Phase 26 Stage-B P12 integration."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_room_p22 = run_phase22_wireless_fault_isolation_verification(synthetic_mode=True)
        cls.clean_room_pkt = build_stage_a_hardware_readiness_packet(synthetic_clean_room=True)
        cls.local_donor_dry_run: CandidateDryRunReport | None = None
        cls.local_donor_tier0: Tier0UnicornRunResult | None = None
        if not _is_clean_room_or_donor_missing():
            compiled_worker = compile_tier0_worker_shared_object()
            cls.local_donor_tier0 = run_tier0_worker_in_unicorn(compiled_worker=compiled_worker)
            cls.local_donor_dry_run = run_offline_candidate_dry_run(
                compiled_worker=compiled_worker,
                precomputed_tier0_result=cls.local_donor_tier0,
            )

    def test_01_p12_spec_matches_phase22_canonical_definition(self) -> None:
        self.assertEqual(P12_WLAN_FATAL_GUARD_SPEC, VERIFIER_P12_SPEC)
        self.assertEqual(P12_WLAN_FATAL_GUARD_SPEC.spec_id, "P12_libWlanResource_fatal_guard")
        self.assertEqual(P12_WLAN_FATAL_GUARD_SPEC.library_name, "libWlanResource.so")
        self.assertEqual(P12_WLAN_FATAL_GUARD_SPEC.expected_size, 56464)
        self.assertEqual(FX6_WLAN_RSRC_DONOR_SHA256, FX6_WLAN_RSRC_SHA256)
        self.assertEqual(P12_WLAN_FATAL_GUARD_SPEC.donor_sha256, FX6_WLAN_RSRC_DONOR_SHA256)
        self.assertEqual(P12_WLAN_FATAL_GUARD_VMA, 0x70D4)
        self.assertEqual(len(P12_WLAN_FATAL_GUARD_SPEC.sites), 1)
        site = P12_WLAN_FATAL_GUARD_SPEC.sites[0]
        self.assertEqual(site.patch_group, "P12")
        self.assertEqual(site.vma, 0x70D4)
        self.assertEqual(site.expected_file_offset, 0x70D4)
        self.assertEqual(len(site.patched_bytes), 8)

    def test_02_stage_a_and_stage_b_p10_backward_compatibility(self) -> None:
        self.assertEqual(STAGE_A_PATCH_SPECS, ALL_PHASE2_TARGET_SPECS)
        self.assertEqual(len(STAGE_A_PATCH_SPECS), 7)
        self.assertEqual(len(STAGE_B_PATCH_SPECS), 7)
        self.assertEqual(get_target_patch_specs(include_p10_keymap=False), STAGE_A_PATCH_SPECS)
        self.assertEqual(get_target_patch_specs(include_p10_keymap=True), STAGE_B_PATCH_SPECS)
        self.assertEqual(
            get_target_patch_specs(include_p10_keymap=True, include_p12_wireless_guard=True),
            STAGE_B_WITH_P12_PATCH_SPECS,
        )
        self.assertEqual(
            get_target_patch_specs(include_p10_keymap=False, include_p12_wireless_guard=True),
            (*STAGE_A_PATCH_SPECS, P12_WLAN_FATAL_GUARD_SPEC),
        )

    def test_03_stage_b_with_p12_non_overlapping_and_unique_libraries(self) -> None:
        self.assertEqual(len(STAGE_B_WITH_P12_PATCH_SPECS), 8)
        lib_names = [s.library_name for s in STAGE_B_WITH_P12_PATCH_SPECS]
        self.assertEqual(len(set(lib_names)), 8)
        self.assertIn("libWlanResource.so", lib_names)
        self.assertEqual(STAGE_B_WITH_P12_PATCH_SPECS[-1], P12_WLAN_FATAL_GUARD_SPEC)

        intervals = verify_patch_sites_non_overlapping(P12_WLAN_FATAL_GUARD_SPEC)
        self.assertEqual(
            intervals,
            (("P12", "P12_wlan_resource_handleFatalError_nonblocking", 0x70D4, 0x70DC),),
        )

    def test_04_build_stage_b_wlan_rsrc_image_synthetic_apply_and_rollback(self) -> None:
        fixtures = build_clean_room_phase22_fixtures()
        raw_wlan = fixtures["fx6_wlan_rsrc"]
        donor_sha = hashlib.sha256(raw_wlan).hexdigest()

        patched, p_rec = build_stage_b_wlan_rsrc_image(raw_wlan, verify_donor_sha256=False)
        self.assertEqual(p_rec.spec_id, P12_WLAN_FATAL_GUARD_SPEC.spec_id)
        self.assertEqual(p_rec.library_name, "libWlanResource.so")
        self.assertEqual(p_rec.before_sha256, donor_sha)
        self.assertNotEqual(p_rec.after_sha256, donor_sha)
        self.assertEqual(p_rec.changed_byte_count, 8)
        self.assertEqual(len(patched), len(raw_wlan))

        diff_count = sum(1 for a, b in zip(raw_wlan, patched) if a != b)
        self.assertEqual(diff_count, 7)

        restored, rb_rec = rollback_patch_spec(
            patched,
            P12_WLAN_FATAL_GUARD_SPEC,
            expected_original_sha256=donor_sha,
            enforce_size=True,
        )
        self.assertTrue(rb_rec.donor_sha256_matched)
        self.assertEqual(rb_rec.restored_sha256, donor_sha)
        self.assertEqual(restored, raw_wlan)

    def test_05_build_stage_b_wlan_rsrc_rejects_wrong_sha_corrupted_context_and_double_apply(self) -> None:
        fixtures = build_clean_room_phase22_fixtures()
        raw_wlan = fixtures["fx6_wlan_rsrc"]

        with self.assertRaises(PatchVerificationError):
            build_stage_b_wlan_rsrc_image(raw_wlan, verify_donor_sha256=True)

        tampered = bytearray(raw_wlan)
        tampered[0x70D4:0x70D8] = b"\x00\x00\x00\x00"
        with self.assertRaises(PatchVerificationError):
            build_stage_b_wlan_rsrc_image(bytes(tampered), verify_donor_sha256=False)

        patched, _ = build_stage_b_wlan_rsrc_image(raw_wlan, verify_donor_sha256=False)
        with self.assertRaises(PatchVerificationError):
            apply_patch_spec(patched, P12_WLAN_FATAL_GUARD_SPEC, verify_donor_sha256=False)

    def test_06_candidate_dry_run_report_dataclass_and_signature(self) -> None:
        field_names = {f.name for f in CandidateDryRunReport.__dataclass_fields__.values()}
        self.assertTrue(
            {
                "stage_b_p12_wireless_guard_enabled",
                "stage_b_wlan_rsrc_sha256",
                "wireless_fault_isolation_ok",
                "wireless_fault_isolation_audit",
            }.issubset(field_names)
        )

        sig = inspect.signature(run_offline_candidate_dry_run)
        self.assertIn("include_p12_wireless_guard", sig.parameters)
        self.assertEqual(sig.parameters["include_p12_wireless_guard"].default, True)
        self.assertIn("precomputed_wireless_fault_isolation", sig.parameters)
        self.assertIsNone(sig.parameters["precomputed_wireless_fault_isolation"].default)
        self.assertIn("corrupt_wireless_guard", sig.parameters)
        self.assertEqual(sig.parameters["corrupt_wireless_guard"].default, False)

    def test_07_top_level_package_exports_p12_symbols(self) -> None:
        expected_exports = (
            "FX6_WLAN_RSRC_DONOR_SHA256",
            "FX6_WLAN_RSRC_P12_SHA256",
            "P12_WLAN_FATAL_GUARD_SPEC",
            "STAGE_B_WITH_P12_PATCH_SPECS",
            "Phase22WirelessFaultIsolationReport",
            "build_stage_b_wlan_rsrc_image",
            "run_phase22_wireless_fault_isolation_verification",
        )
        for name in expected_exports:
            self.assertIn(name, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, name), f"Missing export {name}")
        self.assertIs(fx6_closure.P12_WLAN_FATAL_GUARD_SPEC, P12_WLAN_FATAL_GUARD_SPEC)

    def test_08_phase22_clean_room_verification_and_redline_locks(self) -> None:
        rep = self.clean_room_p22
        self.assertEqual(rep.schema, PHASE_22_SCHEMA)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(rep.passed, rep.errors)
        self.assertFalse(rep.corrupt_wireless_guard_injected)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(rep.p8_cp_mutation_forbidden)
        self.assertEqual(rep.wbi_mutation_bytes, 0)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(rep.kmod_mutation_count, 0)
        self.assertEqual(rep.nvram_persistent_writes, 0)
        self.assertEqual(rep.sony_notice_id, SONY_NOTICE_00342260_ID)
        self.assertTrue(rep.p12_wlan_fatal_guard.unpatched_hang_proven)
        self.assertEqual(rep.p12_wlan_fatal_guard.patched_rc, 0)
        self.assertTrue(rep.p12_wlan_fatal_guard.sp_preserved)
        self.assertTrue(rep.p12_wlan_fatal_guard.rollback_sha256_matched)
        self.assertEqual(rep.p12_wlan_fatal_guard.changed_bytes, 7)
        self.assertEqual(len(rep.fault_scenarios), 5)
        self.assertTrue(all(s.passed for s in rep.fault_scenarios))

    def test_09_phase22_corrupt_wireless_guard_fails_closed(self) -> None:
        bad = run_phase22_wireless_fault_isolation_verification(
            synthetic_mode=True,
            corrupt_wireless_guard=True,
        )
        self.assertFalse(bad.passed)
        self.assertTrue(bad.corrupt_wireless_guard_injected)
        self.assertGreater(len(bad.errors), 0)

    def test_10_readiness_packet_clean_room_includes_phase22_p12_closure(self) -> None:
        pkt1 = self.clean_room_pkt
        self.assertEqual(pkt1.schema, READINESS_PACKET_SCHEMA)
        self.assertTrue(pkt1.offline_engineering_complete, pkt1.errors)
        self.assertEqual(len(pkt1.packet_sha256), 64)

        p22 = pkt1.u1_to_u5_and_abi_redlines["Phase_22_p12_wf12_wireless_fault_isolation"]
        self.assertIsInstance(p22, dict)
        self.assertTrue(p22["closed"])
        self.assertTrue(p22["stage_b_p12_wireless_guard_enabled"])
        self.assertTrue(p22["p12_rollback_verified"])
        self.assertTrue(p22["airplane_ram_shadow_bk4_valid"])
        self.assertEqual(p22["sony_notice_id"], "00342260")
        self.assertEqual(p22["wbi_mutation_bytes"], 0)
        self.assertEqual(p22["cp_mutation_bytes"], 0)
        self.assertEqual(p22["kmod_mutation_count"], 0)
        self.assertEqual(p22["nvram_persistent_writes"], 0)
        self.assertEqual(len(str(p22["stage_b_wlan_rsrc_sha256"])), 64)

    def test_11_cli_verify_wireless_guard_clean_room_stdout_and_output_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p26_cli_wg_") as tmp_s:
            out_path = Path(tmp_s) / "nested" / "wireless_guard.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(["verify-wireless-guard", "--clean-room", "--output", str(out_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.is_file())
            disk_text = out_path.read_text(encoding="utf-8")
            self.assertEqual(buf.getvalue(), disk_text)
            payload = json.loads(disk_text)
            self.assertEqual(payload["schema"], PHASE_22_SCHEMA)
            self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertTrue(payload["passed"])
            self.assertEqual(payload["cp_mutation_bytes"], 0)
            self.assertEqual(payload["wbi_mutation_bytes"], 0)

    def test_12_cli_verify_wireless_guard_listed_in_help(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["verify-wireless-guard", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        help_text = buf.getvalue()
        self.assertIn("verify-wireless-guard", help_text)
        self.assertIn("--clean-room", help_text)
        self.assertIn("--output", help_text)

    def test_13_bk4_airplane_ram_shadow_keys_and_cold_boot_safety(self) -> None:
        shadow = self.clean_room_p22.airplane_ram_shadow_bk4
        self.assertTrue(shadow.valid_bk4_header)
        self.assertTrue(shadow.checksum_ok)
        self.assertTrue(shadow.airplane_mode_shadow_default)
        self.assertEqual(shadow.bkid_0x019e0012_shadow_hex, "00")
        self.assertEqual(shadow.bkid_0x0051000f_shadow_hex, "00")
        self.assertEqual(shadow.bkid_0x01a20002_shadow_hex, "00")
        self.assertTrue(shadow.unicorn_bt_init_bypassed)
        self.assertTrue(shadow.unicorn_rsrc_bt_bypassed)
        self.assertEqual(shadow.nvram_persistent_writes, 0)
        self.assertEqual(shadow.wbi_mutation_bytes, 0)
        self.assertEqual(shadow.cp_mutation_bytes, 0)

    def test_14_p12_read_donor_bytes_uses_o_rdonly_exclusively(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p26_rdonly_") as tmp_s:
            lib_dir = Path(tmp_s)
            raw_wlan = build_clean_room_phase22_fixtures()["fx6_wlan_rsrc"]
            (lib_dir / "libWlanResource.so").write_bytes(raw_wlan)

            observed_flags = []
            orig_open = os.open

            def spy_open(path, flags, *args, **kwargs):
                observed_flags.append((str(path), flags))
                return orig_open(path, flags, *args, **kwargs)

            with mock.patch("fx6_closure.patcher.os.open", side_effect=spy_open):
                patched, rec = build_stage_b_wlan_rsrc_image(
                    fx6_lib_dir=lib_dir,
                    verify_donor_sha256=False,
                )
            self.assertEqual(rec.changed_byte_count, 8)
            self.assertNotEqual(patched, raw_wlan)
            self.assertEqual(len(observed_flags), 1)
            opened_path, flags = observed_flags[0]
            self.assertTrue(opened_path.endswith("libWlanResource.so"))
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)

    def test_15_build_stage_b_wlan_rsrc_missing_donor_file_raises(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p26_missing_") as tmp_s:
            with self.assertRaises(FileNotFoundError):
                build_stage_b_wlan_rsrc_image(fx6_lib_dir=Path(tmp_s), verify_donor_sha256=False)

    def test_16_dry_run_cli_emits_p12_fields_from_report(self) -> None:
        mock_rep = mock.MagicMock()
        mock_rep.candidate_ready = True
        mock_rep.all_12_gates_verified = True
        mock_rep.verified_gate_count = 12
        mock_rep.blocked_gate_ids = ()
        mock_rep.verified_matrix_items = ("P1",)
        mock_rep.temp_dir_cleaned = True
        mock_rep.patch_receipts = ()
        mock_rep.p5_p6_uipc_unicorn = mock.MagicMock(all_positive_passed=True, all_negative_captured=True)
        mock_rep.p7_backup_bridge = mock.MagicMock(all_checks_passed=True)
        mock_rep.feature_routing_audit = mock.MagicMock(all_checks_passed=True)
        mock_rep.backup_mount_tolerance_ok = True
        mock_rep.backup_mount_tolerance_audit = mock.MagicMock(
            dimension_a_mount_tolerance=mock.MagicMock(u4_closed=True),
            dimension_b_backup_contracts=mock.MagicMock(ram_shadow_bundle_sha256="a" * 64),
        )
        mock_rep.boot_selector_and_banks_ok = True
        mock_rep.boot_selector_and_bank_audit = mock.MagicMock(
            dimension_a_boot_selector=mock.MagicMock(u5_closed=True),
            dimension_b_bank_maps=mock.MagicMock(u3_advanced=True),
        )
        mock_rep.kernel_dtb_ok = True
        mock_rep.kernel_dtb_audit = mock.MagicMock(
            dimension_a_dtb=mock.MagicMock(dtb_byte_identical=True),
            dimension_b_ko=mock.MagicMock(p9_upm_integrity=mock.MagicMock(valid=True)),
        )
        mock_rep.storage_and_ram_budget_ok = True
        mock_rep.storage_and_ram_budget_audit = mock.MagicMock(
            edisx_repartition_forbidden=True,
            sector0_mutation_bytes=0,
            p15_fits_stock_fx3=True,
            ram_budget_within_safe_bounds=True,
        )
        mock_rep.cp_rtos_ok = True
        mock_rep.cp_rtos_audit = mock.MagicMock(
            u2_closed=True,
            p8_cp_mutation_forbidden=True,
            cp_mutation_bytes=0,
        )
        mock_rep.p1_recovery_bridge_ok = True
        mock_rep.stage_a_orchestrator_ok = True
        mock_rep.stage_a_orchestrator_audit = mock.MagicMock(
            wbi_p5_write_and_hibernation_forbidden=True,
            wbi_mutation_bytes=0,
            scenario_count=6,
        )
        mock_rep.kmod_userland_abi_ok = True
        mock_rep.kmod_userland_abi_audit = mock.MagicMock(
            kmod_mutation_count=0,
            fx6_kmod_loaded_count=0,
            unaccounted_dev_node_count=0,
            unresolved_required_symbols=0,
            unsatisfied_verneed_count=0,
        )
        mock_rep.peripheral_ux_ok = True
        mock_rep.peripheral_ux_audit = mock.MagicMock(
            input_audit=mock.MagicMock(p10_rollback_receipt=mock.MagicMock(donor_sha256_matched=True))
        )
        mock_rep.ap_cp_imaging_ok = True
        mock_rep.ap_cp_imaging_audit = mock.MagicMock(
            uipc_queue_scan=mock.MagicMock(total_0x92840747_opcodes_matched_in_fx3_cp=2),
            ibis_safety=mock.MagicMock(center_lock_mechanism_verified=True),
        )
        mock_rep.stage_b_p10_keymap_enabled = True
        mock_rep.stage_b_appfw_sha256 = "b" * 64
        mock_rep.stage_b_combined_appfw_verified = True
        mock_rep.uipc_cp_shim_ok = True
        mock_rep.stage_b_p12_wireless_guard_enabled = True
        mock_rep.stage_b_wlan_rsrc_sha256 = FX6_WLAN_RSRC_P12_SHA256
        mock_rep.wireless_fault_isolation_ok = True
        mock_rep.stage_a_overlay_cpio_sha256 = "c" * 64
        mock_rep.stage_a_overlay_cpio_size = 30956
        mock_rep.stage_a_cpio_audit = mock.MagicMock(valid=True)
        mock_rep.rollback_drill = mock.MagicMock(all_scenarios_passed=True, total_emmc_writes=0)
        from fx6_closure.vfat_builder import build_opelog_vfat_image

        _, mock_rep.vfat_receipt = build_opelog_vfat_image("8m_ram")
        mock_rep.tier0_manifest_audit = mock.MagicMock(valid=True)
        mock_rep.tier0_syscall_audit = mock.MagicMock(valid=True)
        mock_rep.safety_gates_report = {"summary": {"verified_gates": 12}}

        buf = io.StringIO()
        with mock.patch("fx6_closure.__main__.run_offline_candidate_dry_run", return_value=mock_rep):
            with redirect_stdout(buf):
                rc = cli_main(["dry-run-candidate"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["stage_b_p12_wireless_guard_enabled"])
        self.assertEqual(payload["stage_b_wlan_rsrc_sha256"], FX6_WLAN_RSRC_P12_SHA256)
        self.assertTrue(payload["wireless_fault_isolation_ok"])

    def test_17_p12_instruction_encoding_mov_w0_0_ret_a64(self) -> None:
        site = P12_WLAN_FATAL_GUARD_SPEC.sites[0]
        w0, w1 = struct.unpack("<II", site.patched_bytes)
        self.assertEqual(w0, 0x52800000)  # mov w0, #0
        self.assertEqual(w1, 0xD65F03C0)  # ret
        diff_bytes = sum(
            1 for a, b in zip(site.original_bytes, site.patched_bytes) if a != b
        )
        self.assertEqual(diff_bytes, 7)

    def test_18_phase22_scenario_3_notice_00342260_nonblocking(self) -> None:
        s3 = next(s for s in self.clean_room_p22.fault_scenarios if "00342260" in s.scenario_id)
        self.assertTrue(s3.passed)
        self.assertFalse(s3.hang_or_loop_detected)
        self.assertFalse(s3.system_error_abort)
        self.assertEqual(s3.wdt_resets, 0)
        self.assertTrue(s3.shooting_unaffected)
        self.assertTrue(s3.recording_unaffected)
        self.assertEqual(s3.nvram_writes, 0)

    def test_19_phase22_scenario_4_seq_queue_network_drain_budget(self) -> None:
        s4 = next(s for s in self.clean_room_p22.fault_scenarios if "SEQ_QUEUE_NETWORK" in s.scenario_id)
        self.assertTrue(s4.passed)
        self.assertTrue(s4.unicorn_executed)
        self.assertLess(s4.simulated_elapsed_ms, APPLICATION_SYSTEM_INIT_BUDGET_MS)
        self.assertFalse(s4.hang_or_loop_detected)
        self.assertEqual(s4.wdt_resets, 0)

    def test_20_readiness_packet_clean_room_cli_and_file_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p26_pkt_cli_") as tmp_s:
            out_json = Path(tmp_s) / "readiness.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(["build-readiness-packet", "--clean-room", "--output", str(out_json)])
            self.assertEqual(rc, 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(buf.getvalue(), out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["packet_sha256"], self.clean_room_pkt.packet_sha256)
            self.assertTrue(payload["offline_engineering_complete"])
            p22 = payload["u1_to_u5_and_abi_redlines"]["Phase_22_p12_wf12_wireless_fault_isolation"]
            self.assertTrue(p22["closed"])
            self.assertEqual(p22["sony_notice_id"], "00342260")

    def test_21_clean_room_readiness_packet_tier0_go_keeps_p12_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p26_tier0_go_") as tmp_s:
            bdir = Path(tmp_s) / "tier0"
            populate_tier0_capture_bundle_fixture(bdir)
            pkt = build_stage_a_hardware_readiness_packet(
                tier0_bundle_dir=bdir,
                synthetic_clean_room=True,
            )
            self.assertTrue(pkt.offline_engineering_complete)
            self.assertTrue(pkt.real_tier0_hardware_backup_verified)
            self.assertTrue(pkt.stage_a_ram_trial_hardware_go)
            self.assertFalse(pkt.persistent_emmc_writes_authorized)
            p22 = pkt.u1_to_u5_and_abi_redlines["Phase_22_p12_wf12_wireless_fault_isolation"]
            self.assertTrue(p22["closed"])
            self.assertTrue(p22["stage_b_p12_wireless_guard_enabled"])
            self.assertTrue(p22["p12_rollback_verified"])

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_22_local_donor_p12_wlan_rsrc_sha256_and_rollback(self) -> None:
        fx6_dir = resolve_fx6_donor_lib_dir()
        patched, p_rec = build_stage_b_wlan_rsrc_image(fx6_lib_dir=fx6_dir, verify_donor_sha256=True)
        self.assertEqual(p_rec.before_sha256, FX6_WLAN_RSRC_DONOR_SHA256)
        self.assertEqual(p_rec.after_sha256, FX6_WLAN_RSRC_P12_SHA256)
        self.assertEqual(p_rec.changed_byte_count, 8)
        self.assertEqual(hashlib.sha256(patched).hexdigest(), FX6_WLAN_RSRC_P12_SHA256)

        donor_raw = (fx6_dir / "libWlanResource.so").read_bytes()
        self.assertEqual(sum(1 for a, b in zip(donor_raw, patched) if a != b), 7)

        restored, rb_rec = rollback_patch_spec(patched, P12_WLAN_FATAL_GUARD_SPEC)
        self.assertTrue(rb_rec.donor_sha256_matched)
        self.assertEqual(rb_rec.restored_sha256, FX6_WLAN_RSRC_DONOR_SHA256)
        self.assertEqual(restored, donor_raw)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_23_local_donor_cli_verify_wireless_guard(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["verify-wireless-guard"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["verification_mode"], "LOCAL_DONOR_VERIFIED")
        self.assertEqual(payload["p12_wlan_fatal_guard"]["before_sha256"], FX6_WLAN_RSRC_DONOR_SHA256)
        self.assertEqual(payload["p12_wlan_fatal_guard"]["after_sha256"], FX6_WLAN_RSRC_P12_SHA256)
        self.assertTrue(payload["p12_wlan_fatal_guard"]["rollback_sha256_matched"])

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_24_local_donor_dry_run_stage_b_p12_default_passes(self) -> None:
        rep = self.local_donor_dry_run
        assert rep is not None
        self.assertTrue(rep.candidate_ready)
        self.assertTrue(rep.all_12_gates_verified)
        self.assertEqual(rep.blocked_gate_ids, ())
        self.assertTrue(rep.stage_b_p12_wireless_guard_enabled)
        self.assertEqual(rep.stage_b_wlan_rsrc_sha256, FX6_WLAN_RSRC_P12_SHA256)
        self.assertTrue(rep.wireless_fault_isolation_ok)
        assert rep.wireless_fault_isolation_audit is not None
        self.assertTrue(rep.wireless_fault_isolation_audit.passed)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_25_local_donor_corrupt_wireless_guard_blocks_g12_and_backward_compat(self) -> None:
        rep_ok = self.local_donor_dry_run
        assert rep_ok is not None
        precomp = dict(
            precomputed_tier0_result=self.local_donor_tier0,
            precomputed_rollback_drill=rep_ok.rollback_drill,
            precomputed_feature_routing=rep_ok.feature_routing_audit,
            precomputed_backup_mount_tolerance=rep_ok.backup_mount_tolerance_audit,
            precomputed_boot_selector_and_banks=rep_ok.boot_selector_and_bank_audit,
            precomputed_kernel_dtb=rep_ok.kernel_dtb_audit,
            precomputed_storage_and_ram_budget=rep_ok.storage_and_ram_budget_audit,
            precomputed_cp_rtos=rep_ok.cp_rtos_audit,
            precomputed_p1_recovery_bridge=rep_ok.p1_recovery_bridge_audit,
            precomputed_stage_a_orchestrator=rep_ok.stage_a_orchestrator_audit,
            precomputed_kmod_userland_abi=rep_ok.kmod_userland_abi_audit,
            precomputed_peripheral_ux=rep_ok.peripheral_ux_audit,
            precomputed_ap_cp_imaging=rep_ok.ap_cp_imaging_audit,
            precomputed_stage_b_appfw=rep_ok.stage_b_p10_summary,
            precomputed_uipc_cp_shim=rep_ok.uipc_cp_shim_audit,
            precomputed_wireless_fault_isolation=rep_ok.wireless_fault_isolation_audit,
        )

        rep_bad = run_offline_candidate_dry_run(**precomp, corrupt_wireless_guard=True)
        self.assertFalse(rep_bad.candidate_ready)
        self.assertFalse(rep_bad.all_12_gates_verified)
        self.assertFalse(rep_bad.wireless_fault_isolation_ok)
        self.assertIn("G12_persistent_flash_write_authorization", rep_bad.blocked_gate_ids)

        rep_a = run_offline_candidate_dry_run(
            **precomp,
            include_p10_keymap=False,
            include_p12_wireless_guard=False,
        )
        self.assertTrue(rep_a.candidate_ready)
        self.assertEqual(rep_a.stage_b_appfw_sha256, FX6_APPFW_STAGE_A_SHA256)
        self.assertFalse(rep_a.stage_b_p12_wireless_guard_enabled)
        self.assertEqual(rep_a.stage_b_wlan_rsrc_sha256, "")
        self.assertTrue(rep_a.wireless_fault_isolation_ok)

    @unittest.skipIf(_is_clean_room_or_donor_missing(), _CLEAN_ROOM_SKIP_REASON)
    def test_26_local_donor_readiness_packet_includes_p12_sha(self) -> None:
        rep_ok = self.local_donor_dry_run
        assert rep_ok is not None
        pkt = build_stage_a_hardware_readiness_packet(precomputed_dry_run=rep_ok)
        self.assertTrue(pkt.offline_engineering_complete, pkt.errors)
        p22 = pkt.u1_to_u5_and_abi_redlines["Phase_22_p12_wf12_wireless_fault_isolation"]
        self.assertTrue(p22["closed"])
        self.assertTrue(p22["stage_b_p12_wireless_guard_enabled"])
        self.assertEqual(p22["stage_b_wlan_rsrc_sha256"], FX6_WLAN_RSRC_P12_SHA256)
        self.assertTrue(p22["p12_rollback_verified"])
        self.assertTrue(p22["airplane_ram_shadow_bk4_valid"])


if __name__ == "__main__":
    unittest.main()
