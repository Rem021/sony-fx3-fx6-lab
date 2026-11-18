"""Phase 308 — Dual-mode unit tests for Recovery Pillar 55 & Unified 55/55 Recovery Master.

Covers:
1. Sub-Pillar 55A:
   - `[Lens Comp.]` `[Shading Comp.]` Auto/Off ONLY vs dormant `LENS_COMP_SHADING_AUTO_LOW`
     (`_f.uxc 0x6c9c`, `Auto: Low`) rejected with `EOPNOTSUPP=95`; `[Chromatic Aberration Comp.]`
     Auto/Off; `[Distortion Comp.]` Auto/Off with lens-forced Auto lock & Movie SteadyShot Active
     Auto lock, `.ARW` no distortion bake, Movie-only `[Breathing Comp.]` (HDMI RAW / unsupported
     lens lockout), unchipped manual lens gray-out, and `ILME-FX6` `Technical > Lens` / `All File` /
     RAW+S&Q Distortion-Off lockout contrast.
   - Movie AF (`[AF Transition Speed]` 1..7, `[AF Subj. Shift Sens.]` 1..5, `[AF Assist]`, all reset
     on `[Camera Settings Reset]`).
   - FX3 front built-in AF illuminator LED `#8` (`0.3..3.0 m`) + MI-Shoe external flash illuminator
     active ONLY in Still `AF-S` (locked out in Movie, `S&Q`, `AF-C`, `MF`, Silent Mode On, Focus
     Magnifier, Mount Adaptor), contrasted with `ILME-FX6` (`0` built-in AF illuminator).
2. Sub-Pillar 55B:
   - `[Aperture Drive in AF]` (`Focus Priority` / `Standard` / `Silent Priority`), Still-only
     `[AF w/ Shutter]` & `[Pre-AF]`, `[Circ. of Focus Point]` (orthogonal wrap only, never
     diagonal), and `[Focus Area Color]` (`White` / `Red`) — surviving `[Camera Settings Reset]`
     and resetting ONLY via `[Initialize]`.
   - `[File/Folder Settings]` (`Standard`/`Date Form`, `Series`/`Reset`, 3-char prefix without
     leading `_`, 4000-still folder cap) & Playback `[Rating]` (`1..5` stars + custom-key `Rating Set`),
     with CRITICAL `Slot-1` Tier-0 Recovery Vault Firewall failing closed (`EROFS=30`/`EBUSY=16`,
     `slot1_data_sector_writes == 0`) on `[Create New Folder]`, `[Rating]`, `[Add Rating]`,
     and Slot-1 formats.
3. Unified `55/55` Recovery Master (`evaluate_realhw_55pillar_recovery_master` / CLI).
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier as p308,
)
from fx3_recovery.realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier import (
    evaluate_realhw_54pillar_recovery_master,
)
from fx3_recovery.realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_55_PILLAR_COUNT,
    MASTER_55_PILLAR_IDS,
    MASTER_55_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P308_AF_SUBJ_SHIFT_SENS_MAX,
    P308_AF_SUBJ_SHIFT_SENS_MIN,
    P308_AF_TRANSITION_SPEED_MAX,
    P308_AF_TRANSITION_SPEED_MIN,
    P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF,
    P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT,
    P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
    P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT,
    P308_BLOCKED_INVALID_PILLAR55A_SPEC,
    P308_BLOCKED_INVALID_PILLAR55B_SPEC,
    P308_BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT,
    P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P308_BLOCKED_SAFETY_POLICY_VIOLATION,
    P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P308_DONOR_INSPECT_BUDGET_SECONDS,
    P308_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P308_DORMANT_SHADING_AUTO_LOW_F_RESID16,
    P308_ENV_CLEAN_ROOM_TEST,
    P308_EOPNOTSUPP_ERRNO,
    P308_FAST_CLI_BUDGET_SECONDS,
    P308_FOLDER_MAX_STILLS,
    P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO,
    P308_FX3_AF_ILLUMINATOR_RANGE_M,
    P308_FX3_FW_VERSION,
    P308_FX3_HELPGUIDE_ID,
    P308_FX3_MODEL_ID,
    P308_FX3_MODEL_NAME,
    P308_FX6_DONOR_FW_VERSION,
    P308_FX6_DONOR_MODEL_NAME,
    P308_FX6_LENS_COMP_MENU_PATH,
    P308_PINNED_FX3_APPFW_702_BYTES,
    P308_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P308_PINNED_FX3_BACKUP_BIN_BYTES,
    P308_PINNED_FX3_BACKUP_BIN_SHA256,
    P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES,
    P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256,
    P308_PINNED_FX6_APPFW_601_BYTES,
    P308_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P308_STAGE_B_VOLATILE_OVERLAY_DIR,
    P308_STATUS_VERIFIED_55OF55_AGGREGATOR,
    P308_STATUS_VERIFIED_PILLAR55_SUITE,
    P308_STATUS_VERIFIED_PILLAR_55A,
    P308_STATUS_VERIFIED_PILLAR_55B,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE308_PHASE_NUMBER,
    PHASE308_SCHEMA,
    PHASE308_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_aperture_drive_folder_rating_vault_spec,
    build_default_safe_lens_comp_af_illuminator_vault_spec,
    compute_expected_af_illuminator_state,
    compute_expected_aperture_drive_and_focus_ui_state,
    compute_expected_folder_and_rating_vault_state,
    compute_expected_lens_comp_and_movie_af_state,
    evaluate_55pillar_recovery_master,
    evaluate_aperture_drive_folder_rating_vault,
    evaluate_lens_comp_af_illuminator_vault,
    evaluate_realhw_55pillar_recovery_master,
    inspect_phase308_donors_readonly,
    is_valid_fx3_file_prefix,
    run_pillar55_standalone_suite,
    run_pillar55a_lens_comp_af_illuminator_6_scenario_suite,
    run_pillar55b_aperture_drive_folder_rating_6_scenario_suite,
    verify_55pillar_recovery_suite,
    verify_lens_comp_af_illuminator_folder_rating_and_vault,
    verify_lens_comp_af_illuminator_folder_rating_vault,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _ci_headroom() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 0.0


def _clean_env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{ADAPTER_ROOT}{os.pathsep}{existing_pp}" if existing_pp else str(ADAPTER_ROOT)
    )
    env.update(extra)
    return env


class TestPhase308SafetyDonorsAndExports(unittest.TestCase):
    """Tests 01-12: Safety locks, package exports, donor inspection, and pure prefix helper."""

    def test_01_hard_locked_module_safety_invariants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(p308.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_camera_identity_constants(self) -> None:
        self.assertEqual(
            PHASE308_SCHEMA,
            "realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier_v1",
        )
        self.assertEqual(PHASE308_VERSION, "1.0.0")
        self.assertEqual(PHASE308_PHASE_NUMBER, 308)
        self.assertEqual(P308_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P308_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P308_FX3_FW_VERSION, "7.02")
        self.assertEqual(P308_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO, 8)
        self.assertEqual(P308_FX3_AF_ILLUMINATOR_RANGE_M, (0.3, 3.0))
        self.assertEqual(P308_DORMANT_SHADING_AUTO_LOW_F_RESID16, 0x6C9C)
        self.assertEqual(P308_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P308_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P308_FX6_LENS_COMP_MENU_PATH, "Technical > Lens")

    def test_03_init_exports_and_non_overlapping_master_55_registry(self) -> None:
        self.assertIs(
            fx3_recovery.evaluate_realhw_55pillar_recovery_master,
            evaluate_realhw_55pillar_recovery_master,
        )
        self.assertIs(fx3_recovery.evaluate_55pillar_recovery_master, evaluate_55pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_55pillar_recovery_suite, verify_55pillar_recovery_suite)
        self.assertIs(fx3_recovery.run_pillar55_standalone_suite, run_pillar55_standalone_suite)
        self.assertIs(fx3_recovery.CROSS_MODEL_FLASH_AUTHORIZED, CROSS_MODEL_FLASH_AUTHORIZED)
        p55_specific = [
            sym
            for sym in p308.__all__
            if sym.startswith(
                (
                    "P308_",
                    "PHASE308_",
                    "MASTER_55",
                    "Pillar55",
                    "Master55",
                    "evaluate_realhw_55",
                    "evaluate_55",
                    "verify_55",
                    "verify_lens_comp_af",
                    "run_pillar55",
                )
            )
        ]
        self.assertGreaterEqual(len(p55_specific), 200)
        for sym in p55_specific:
            self.assertEqual(fx3_recovery.__all__.count(sym), 1, sym)
        self.assertEqual(MASTER_55_PILLAR_COUNT, 55)
        self.assertEqual(len(MASTER_55_PILLAR_SPECS), 55)
        self.assertEqual(len(MASTER_55_PILLAR_IDS), 55)
        self.assertEqual(len(set(MASTER_55_PILLAR_IDS)), 55)
        self.assertEqual(MASTER_55_PILLAR_SPECS[54][0], 55)
        self.assertEqual(
            MASTER_55_PILLAR_SPECS[54][1],
            "pillar_55_lens_comp_af_illuminator_folder_rating_vault",
        )

    def test_04_safety_invariant_tamper_rejected_in_55a_and_55b(self) -> None:
        with mock.patch.object(p308, "CROSS_MODEL_FLASH_AUTHORIZED", True):
            rep_a = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec()
            )
            rep_b = evaluate_aperture_drive_folder_rating_vault(
                build_default_safe_aperture_drive_folder_rating_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P308_BLOCKED_SAFETY_POLICY_VIOLATION)
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P308_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_05_inspect_donors_clean_room_forced_returns_18_pinned_artifacts(self) -> None:
        snap = inspect_phase308_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertLess(snap.elapsed_seconds, P308_DONOR_INSPECT_CI_BUDGET_SECONDS + _ci_headroom())
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P308_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(
            by_id["fx3_appfw_702_so"].digest_sha256, P308_PINNED_FX3_APPFW_702_HDR4K_SHA256
        )
        self.assertEqual(
            by_id["fx3_lib_infra_lens_comm_so"].total_bytes,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES,
        )
        self.assertEqual(
            by_id["fx3_lib_infra_lens_comm_so"].digest_sha256,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256,
        )
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P308_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(
            by_id["fx6_appfw_601_so"].digest_sha256, P308_PINNED_FX6_APPFW_601_HDR4K_SHA256
        )
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P308_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P308_PINNED_FX3_BACKUP_BIN_SHA256)

    def test_06_inspect_donors_honors_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {P308_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase308_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 18)

    def test_07_inspect_donors_honors_fx3_fx6_force_clean_room_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase308_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 18)

    def test_08_inspect_donors_auto_fallback_when_donor_missing(self) -> None:
        with mock.patch.object(p308, "resolve_donor_path", return_value=None):
            with mock.patch.dict(
                os.environ,
                {P308_ENV_CLEAN_ROOM_TEST: "0", "FX3_FX6_FORCE_CLEAN_ROOM": "0"},
                clear=False,
            ):
                snap = inspect_phase308_donors_readonly(force_clean_room=None)
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 18)

    def test_09_inspect_donors_local_o_rdonly_uses_bounded_header_and_o_rdonly_flags(self) -> None:
        clean_flag = (
            os.environ.get(P308_ENV_CLEAN_ROOM_TEST, "") == "1"
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "") == "1"
        )
        snap = inspect_phase308_donors_readonly(force_clean_room=None)
        if clean_flag or snap.verification_mode == "CLEAN_ROOM_SYNTHETIC":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 18)
            self.assertLess(snap.elapsed_seconds, P308_DONOR_INSPECT_BUDGET_SECONDS + _ci_headroom())
            for art in snap.artifacts:
                self.assertEqual(art.read_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(art.matches_pinned, art.artifact_id)
                if art.artifact_id.endswith("_so") and art.artifact_id != "fx3_lib_infra_lens_comm_so":
                    self.assertEqual(art.digest_kind, "HEADER4K_SHA256")
                    self.assertEqual(art.header_bytes_read, 4096)

    def test_10_read_donor_readonly_bounded_rejects_symlink_and_missing(self) -> None:
        self.assertEqual(p308._read_donor_readonly_bounded("definitely/missing/file.bin")[:3], (False, 0, 0))
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(tempfile.mkdtemp(prefix="p308_sym_", dir=str(work_tests)))
        try:
            target = tmp_dir / "real.bin"
            target.write_bytes(b"FX3_DONOR_OK")
            link = tmp_dir / "sym.bin"
            link.symlink_to(target)
            with mock.patch.object(p308, "resolve_donor_path", return_value=target):
                ok_real, sz_real, read_real = p308._read_donor_readonly_bounded("real.bin")[:3]
                self.assertTrue(ok_real)
                self.assertEqual((sz_real, read_real), (12, 12))
            with mock.patch.object(p308, "resolve_donor_path", return_value=link):
                ok_sym = p308._read_donor_readonly_bounded("sym.bin")[0]
                self.assertFalse(ok_sym)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_11_is_valid_fx3_file_prefix_enforces_3_alnum_no_leading_underscore(self) -> None:
        for good in ("DSC", "A01", "FX3", "A_1", "B9_"):
            self.assertTrue(is_valid_fx3_file_prefix(good), good)
        for bad in ("_DSC", "__A", "DS", "DSC1", "DS-"):
            self.assertFalse(is_valid_fx3_file_prefix(bad), bad)

    def test_12_donor_snapshot_uses_expected_o_rdonly_and_nofollow_flags(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(tempfile.mkdtemp(prefix="p308_flags_", dir=str(work_tests)))
        captured_flags: list[int] = []
        orig_open = os.open

        def _spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            captured_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        try:
            sample = tmp_dir / "sample.bin"
            sample.write_bytes(b"UXC7TEST")
            with mock.patch.object(p308, "resolve_donor_path", return_value=sample), mock.patch(
                "os.open", side_effect=_spy_open
            ):
                p308._read_donor_readonly_bounded("sample.bin")
            self.assertTrue(captured_flags)
            self.assertEqual(captured_flags[0] & os.O_RDONLY, os.O_RDONLY)
            if hasattr(os, "O_NOFOLLOW"):
                self.assertEqual(captured_flags[0] & os.O_NOFOLLOW, os.O_NOFOLLOW)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestPhase308SubPillar55ALensCompAndAfIlluminator(unittest.TestCase):
    """Tests 13-36: Sub-Pillar 55A Lens Comp., Movie AF, AF Illuminator, and Vault Firewall."""

    def test_13_default_safe_spec_passes_pillar55a(self) -> None:
        spec = build_default_safe_lens_comp_af_illuminator_vault_spec()
        rep = evaluate_lens_comp_af_illuminator_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P308_STATUS_VERIFIED_PILLAR_55A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_14_shading_comp_auto_and_off_allowed(self) -> None:
        for mode in ("Auto", "Off"):
            rep = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(
                    requested_shading_comp=mode,
                    post_shading_comp=mode,
                )
            )
            self.assertTrue(rep.passed, rep.errors)

    def test_15_dormant_shading_auto_low_rejected_with_eopnotsupp95(self) -> None:
        st_dormant = compute_expected_lens_comp_and_movie_af_state(
            camera_model="ILME-FX3",
            lens_id="SEL2470GM2",
            unchipped_manual_lens=False,
            lens_requires_distortion_comp=False,
            lens_supports_breathing_comp=True,
            shooting_domain="Still",
            steadyshot_mode="Standard",
            hdmi_external_raw=False,
            requested_shading_comp="Auto: Low",
            requested_chroma_aber_comp="Auto",
            requested_distortion_comp="Off",
            requested_breathing_comp="Off",
            requested_af_transition_speed=5,
            requested_af_subj_shift_sens=5,
            requested_af_assist="Off",
            focus_mode="AF-S",
            fx6_sq_motion_on=False,
            fx6_rec_codec="XAVC-I",
            reset_action="None",
        )
        self.assertEqual(st_dormant["shading_rejected_errno"], P308_EOPNOTSUPP_ERRNO)
        self.assertEqual(st_dormant["post_shading"], "Auto")

        rep_leaked = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                requested_shading_comp="Auto: Low",
                shading_comp_rejected_errno=0,
                dormant_shading_auto_low_exposed=True,
                post_shading_comp="Auto: Low",
            )
        )
        self.assertFalse(rep_leaked.passed)
        self.assertEqual(rep_leaked.block_code, P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT)

    def test_16_distortion_comp_lens_forced_auto_and_steadyshot_active_lock(self) -> None:
        rep_lens_lock = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                lens_requires_distortion_comp=True,
                requested_distortion_comp="Off",
                reported_distortion_forced_auto=True,
                post_distortion_comp="Auto",
            )
        )
        self.assertTrue(rep_lens_lock.passed, rep_lens_lock.errors)

        rep_ss_active = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                steadyshot_mode="Active",
                requested_distortion_comp="Off",
                reported_distortion_forced_auto=True,
                post_distortion_comp="Auto",
                post_af_illuminator="Auto",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_ss_active.passed, rep_ss_active.errors)

        rep_bypass = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                steadyshot_mode="Active",
                requested_distortion_comp="Off",
                reported_distortion_forced_auto=False,
                post_distortion_comp="Off",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertFalse(rep_bypass.passed)
        self.assertEqual(rep_bypass.block_code, P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT)

    def test_17_arw_does_not_bake_distortion_comp_but_applies_shading_gain(self) -> None:
        rep_bad = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                arw_distortion_baked=True,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT)

        rep_good = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                requested_shading_comp="Auto",
                arw_distortion_baked=False,
                arw_shading_gain_applied_on_auto=True,
            )
        )
        self.assertTrue(rep_good.passed, rep_good.errors)

    def test_18_breathing_comp_movie_only_and_hdmi_raw_lockout(self) -> None:
        rep_movie = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                requested_breathing_comp="On",
                post_breathing_comp="On",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_movie.passed, rep_movie.errors)

        rep_raw_locked = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                hdmi_external_raw=True,
                requested_breathing_comp="On",
                post_breathing_comp="Off",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_raw_locked.passed, rep_raw_locked.errors)

        rep_still_breathe_fail = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Still",
                requested_breathing_comp="On",
                post_breathing_comp="On",
            )
        )
        self.assertFalse(rep_still_breathe_fail.passed)
        self.assertEqual(
            rep_still_breathe_fail.block_code,
            P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
        )

    def test_19_unchipped_manual_lens_grays_out_breathing_and_comp_controls(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                unchipped_manual_lens=True,
                lens_supports_breathing_comp=False,
                requested_chroma_aber_comp="Off",
                requested_distortion_comp="Off",
                requested_breathing_comp="Off",
                post_chroma_aber_comp="Off",
                post_distortion_comp="Off",
                post_breathing_comp="Off",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

        rep_blocked = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                unchipped_manual_lens=True,
                shooting_domain="Movie",
                requested_breathing_comp="On",
                post_breathing_comp="On",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertFalse(rep_blocked.passed)
        self.assertEqual(
            rep_blocked.block_code, P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT
        )

    def test_20_fx6_lens_comp_menu_path_and_all_file_isolation(self) -> None:
        rep_fx6_ok = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                fx6_lens_menu_path=P308_FX6_LENS_COMP_MENU_PATH,
                fx6_saved_in_all_file=True,
                mishoe_external_flash_attached=False,
                reported_has_builtin_af_illuminator=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
                post_af_illuminator="Off",
            )
        )
        self.assertTrue(rep_fx6_ok.passed, rep_fx6_ok.errors)

        rep_fx6_allfile_fail = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                fx6_lens_menu_path=P308_FX6_LENS_COMP_MENU_PATH,
                fx6_saved_in_all_file=False,
                mishoe_external_flash_attached=False,
                reported_has_builtin_af_illuminator=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
                post_af_illuminator="Off",
            )
        )
        self.assertFalse(rep_fx6_allfile_fail.passed)
        self.assertEqual(
            rep_fx6_allfile_fail.block_code,
            P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
        )

    def test_21_fx6_raw_and_sq_lock_out_breathing_comp_to_off(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                fx6_lens_menu_path=P308_FX6_LENS_COMP_MENU_PATH,
                fx6_saved_in_all_file=True,
                fx6_sq_motion_on=True,
                fx6_rec_codec="XAVC-I RAW",
                requested_distortion_comp="Auto",
                post_distortion_comp="Auto",
                requested_breathing_comp="On",
                post_breathing_comp="Off",
                mishoe_external_flash_attached=False,
                reported_has_builtin_af_illuminator=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
                post_af_illuminator="Off",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_22_movie_af_transition_speed_subj_shift_sens_and_af_assist(self) -> None:
        rep_ok = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                focus_mode="AF-C",
                requested_af_transition_speed=P308_AF_TRANSITION_SPEED_MIN,
                requested_af_subj_shift_sens=P308_AF_SUBJ_SHIFT_SENS_MIN,
                requested_af_assist="On",
                post_af_transition_speed=P308_AF_TRANSITION_SPEED_MIN,
                post_af_subj_shift_sens=P308_AF_SUBJ_SHIFT_SENS_MIN,
                post_af_assist="On",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_reset = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                focus_mode="AF-C",
                requested_af_transition_speed=P308_AF_TRANSITION_SPEED_MAX,
                requested_af_subj_shift_sens=P308_AF_SUBJ_SHIFT_SENS_MIN,
                requested_af_assist="On",
                reset_action="Camera Settings Reset",
                post_af_transition_speed=5,
                post_af_subj_shift_sens=5,
                post_af_assist="Off",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_reset.passed, rep_reset.errors)

    def test_23_movie_af_transition_out_of_range_or_drift_rejected(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                requested_af_transition_speed=5,
                post_af_transition_speed=7,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT)

    def test_24_af_illuminator_active_in_still_af_s_including_mishoe_flash(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Still",
                focus_mode="AF-S",
                configured_af_illuminator="Auto",
                mishoe_external_flash_attached=True,
                reported_builtin_af_illuminator_active=True,
                reported_mishoe_af_illuminator_active=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_25_af_illuminator_locked_out_in_movie_sq_afc_mf_and_silent(self) -> None:
        for kw in (
            {"shooting_domain": "Movie", "focus_mode": "AF-C"},
            {"shooting_domain": "S&Q", "focus_mode": "AF-C"},
            {"shooting_domain": "Still", "focus_mode": "AF-C"},
            {"shooting_domain": "Still", "focus_mode": "MF"},
            {"shooting_domain": "Still", "focus_mode": "AF-S", "silent_mode_on": True},
            {"shooting_domain": "Still", "focus_mode": "AF-S", "focus_magnifier_active": True},
            {"shooting_domain": "Still", "focus_mode": "AF-S", "mount_adaptor_attached": True},
        ):
            rep_safe = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(
                    mishoe_external_flash_attached=False,
                    reported_builtin_af_illuminator_active=False,
                    reported_mishoe_af_illuminator_active=False,
                    **kw,
                )
            )
            self.assertTrue(rep_safe.passed, (kw, rep_safe.errors))

            rep_spoof = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(
                    reported_builtin_af_illuminator_active=True,
                    **kw,
                )
            )
            self.assertFalse(rep_spoof.passed, kw)
            self.assertEqual(rep_spoof.block_code, P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF)

    def test_26_fx6_builtin_af_illuminator_spoof_rejected(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                fx6_lens_menu_path=P308_FX6_LENS_COMP_MENU_PATH,
                reported_has_builtin_af_illuminator=True,
                reported_builtin_af_illuminator_active=True,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF)

    def test_27_af_illuminator_afa_moving_subject_locks_out_led(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Still",
                focus_mode="AF-A",
                subject_moving_in_afa=True,
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_28_pillar55a_slot1_vault_mutation_and_format_blocked(self) -> None:
        for kw in (
            {"requested_vault_slot": 1, "requested_vault_action": "FORMAT_QUICK"},
            {"requested_vault_slot": 1, "requested_vault_action": "PLAYBACK_RATING_SET"},
            {"slot1_vault_mutation_bytes": 4096},
            {"slot1_vault_erofs_ebusy_enforced": False},
            {"slot1_format_hard_locked": False},
        ):
            rep = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(**kw)
            )
            self.assertFalse(rep.passed, kw)
            self.assertEqual(rep.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_29_pillar55a_persistent_overlay_escape_rejected(self) -> None:
        for bad_ov in ("/setting/p55", "p2:/setting", "/dev/mmcblk0"):
            rep = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(overlay_dir=bad_ov)
            )
            self.assertFalse(rep.passed, bad_ov)
            self.assertEqual(rep.block_code, P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_30_pillar55a_tier0_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_31_pillar55a_invalid_spec_rejected(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX9"},
            {"shooting_domain": "Burst"},
            {"steadyshot_mode": "HyperSmooth"},
            {"requested_shading_comp": "High"},
            {"requested_af_transition_speed": 9},
            {"requested_af_subj_shift_sens": 0},
            {"requested_af_assist": "Auto"},
            {"configured_af_illuminator": "Strobe"},
            {"reset_action": "WipeAll"},
            {"requested_vault_slot": 3},
        ):
            rep = evaluate_lens_comp_af_illuminator_vault(
                build_default_safe_lens_comp_af_illuminator_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed, bad_kw)
            self.assertEqual(rep.block_code, P308_BLOCKED_INVALID_PILLAR55A_SPEC)

    def test_32_pillar55a_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        res = run_pillar55a_lens_comp_af_illuminator_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P308_STATUS_VERIFIED_PILLAR_55A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        allow_cnt = sum(1 for s in res.scenarios if s.expected_allowed)
        reject_cnt = sum(1 for s in res.scenarios if not s.expected_allowed)
        self.assertEqual((allow_cnt, reject_cnt), (2, 4))

    def test_33_compute_expected_lens_comp_and_movie_af_state_reset_semantics(self) -> None:
        st_cam = compute_expected_lens_comp_and_movie_af_state(
            camera_model="ILME-FX3",
            lens_id="SEL2470GM2",
            unchipped_manual_lens=False,
            lens_requires_distortion_comp=False,
            lens_supports_breathing_comp=True,
            shooting_domain="Movie",
            steadyshot_mode="Standard",
            hdmi_external_raw=False,
            requested_shading_comp="Off",
            requested_chroma_aber_comp="Off",
            requested_distortion_comp="Off",
            requested_breathing_comp="On",
            requested_af_transition_speed=7,
            requested_af_subj_shift_sens=2,
            requested_af_assist="On",
            focus_mode="AF-C",
            fx6_sq_motion_on=False,
            fx6_rec_codec="XAVC-I",
            reset_action="Camera Settings Reset",
        )
        # Camera Settings Reset preserves Shading/CA/Distortion while resetting Movie AF & Breathing Comp
        self.assertEqual(st_cam["post_shading"], "Off")
        self.assertEqual(st_cam["post_breathing"], "Off")
        self.assertEqual(st_cam["post_af_transition_speed"], 5)
        self.assertEqual(st_cam["post_af_subj_shift_sens"], 5)
        self.assertEqual(st_cam["post_af_assist"], "Off")

        st_init = compute_expected_lens_comp_and_movie_af_state(
            camera_model="ILME-FX3",
            lens_id="SEL2470GM2",
            unchipped_manual_lens=False,
            lens_requires_distortion_comp=False,
            lens_supports_breathing_comp=True,
            shooting_domain="Movie",
            steadyshot_mode="Standard",
            hdmi_external_raw=False,
            requested_shading_comp="Off",
            requested_chroma_aber_comp="Off",
            requested_distortion_comp="Auto",
            requested_breathing_comp="On",
            requested_af_transition_speed=7,
            requested_af_subj_shift_sens=2,
            requested_af_assist="On",
            focus_mode="AF-C",
            fx6_sq_motion_on=False,
            fx6_rec_codec="XAVC-I",
            reset_action="Initialize",
        )
        self.assertEqual(st_init["post_shading"], "Auto")
        self.assertEqual(st_init["post_chroma"], "Auto")
        self.assertEqual(st_init["post_distortion"], "Off")

    def test_34_compute_expected_af_illuminator_state_contract(self) -> None:
        builtin, mishoe, post_cfg, has_led = compute_expected_af_illuminator_state(
            camera_model="ILME-FX3",
            shooting_domain="Still",
            focus_mode="AF-S",
            configured_af_illuminator="Auto",
            silent_mode_on=False,
            focus_magnifier_active=False,
            mount_adaptor_attached=False,
            subject_moving_in_afa=False,
            mishoe_external_flash_attached=True,
            reset_action="Camera Settings Reset",
        )
        self.assertTrue((builtin, mishoe, has_led) == (True, True, True))
        self.assertEqual(post_cfg, "Auto")

        b6, m6, p6, h6 = compute_expected_af_illuminator_state(
            camera_model="ILME-FX6",
            shooting_domain="Movie",
            focus_mode="AF-C",
            configured_af_illuminator="Auto",
            silent_mode_on=False,
            focus_magnifier_active=False,
            mount_adaptor_attached=False,
            subject_moving_in_afa=False,
            mishoe_external_flash_attached=False,
            reset_action="None",
        )
        self.assertEqual((b6, m6, p6, h6), (False, False, "Off", False))

    def test_35_pillar55a_deterministic_sha256_digest(self) -> None:
        spec = build_default_safe_lens_comp_af_illuminator_vault_spec()
        r1 = evaluate_lens_comp_af_illuminator_vault(spec)
        r2 = evaluate_lens_comp_af_illuminator_vault(spec)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        self.assertEqual(len(r1.digest_sha256), 64)

    def test_36_pillar55a_matrix_states_and_to_dict(self) -> None:
        d = evaluate_lens_comp_af_illuminator_vault(
            build_default_safe_lens_comp_af_illuminator_vault_spec()
        ).to_dict()
        self.assertEqual(d["matrix_states_checked"], 18)
        self.assertEqual(d["physical_device_writes"], 0)
        self.assertFalse(d["persistent_emmc_writes_authorized"])
        self.assertEqual(d["slot1_vault_mutation_bytes"], 0)


class TestPhase308SubPillar55BApertureDriveFolderRatingVault(unittest.TestCase):
    """Tests 37-64: Sub-Pillar 55B Aperture Drive/Pre-AF/Circ/Color Initialize-Only & Folder/Rating Firewall."""

    def test_37_default_safe_spec_passes_pillar55b(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P308_STATUS_VERIFIED_PILLAR_55B)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_38_five_initialize_only_items_survive_camera_settings_reset(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Silent Priority",
                configured_af_w_shutter="Off",
                configured_pre_af="Off",
                configured_circ_of_focus_point="Circulate",
                configured_focus_area_color="Red",
                reset_action="Camera Settings Reset",
                post_aperture_drive_in_af="Silent Priority",
                post_af_w_shutter="Off",
                post_pre_af="Off",
                post_circ_of_focus_point="Circulate",
                post_focus_area_color="Red",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_39_camera_settings_reset_wiped_init_only_drift_rejected(self) -> None:
        rep_ap = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Silent Priority",
                reset_action="Camera Settings Reset",
                post_aperture_drive_in_af="Standard",
            )
        )
        self.assertFalse(rep_ap.passed)
        self.assertEqual(
            rep_ap.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT
        )

        rep_col = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_focus_area_color="Red",
                reset_action="Camera Settings Reset",
                post_focus_area_color="White",
            )
        )
        self.assertFalse(rep_col.passed)
        self.assertEqual(
            rep_col.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT
        )

    def test_40_initialize_resets_all_5_items_to_factory_defaults(self) -> None:
        rep_ok = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Focus Priority",
                aperture_drive_burst_warn_acknowledged=True,
                configured_af_w_shutter="Off",
                configured_pre_af="On",
                configured_circ_of_focus_point="Circulate",
                configured_focus_area_color="Red",
                reset_action="Initialize",
                post_aperture_drive_in_af="Standard",
                post_af_w_shutter="On",
                post_pre_af="Off",
                post_circ_of_focus_point="Does Not Circulate",
                post_focus_area_color="White",
                post_folder_name_form="Standard Form",
                post_file_number_mode="Series",
                post_file_prefix="DSC",
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

    def test_41_focus_priority_requires_burst_rate_warning_ack(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Focus Priority",
                aperture_drive_burst_warn_acknowledged=False,
                post_aperture_drive_in_af="Focus Priority",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT)

    def test_42_pre_af_lens_incompatibility_forces_off(self) -> None:
        rep_ok = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_pre_af="On",
                lens_supports_pre_af=False,
                post_pre_af="Off",
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_pre_af="On",
                lens_supports_pre_af=False,
                post_pre_af="On",
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT)

    def test_43_circ_of_focus_point_orthogonal_only_never_diagonal(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_circ_of_focus_point="Circulate",
                circ_wrap_axis="Diagonal",
                post_circ_of_focus_point="Circulate",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT)

    def test_44_fx6_iris_and_msdcf_rating_spoof_rejected(self) -> None:
        rep_iris = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                fx6_exposes_aperture_drive_or_circ_color=True,
            )
        )
        self.assertFalse(rep_iris.passed)
        self.assertEqual(rep_iris.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT)

        rep_msdcf = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                fx6_exposes_msdcf_or_star_rating=True,
            )
        )
        self.assertFalse(rep_msdcf.passed)
        self.assertEqual(rep_msdcf.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT)

    def test_45_folder_settings_prefix_cap_and_rating_1_to_5_on_slot2_allowed(self) -> None:
        rep_slot2_folder = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                folder_name_form="Date Form",
                select_rec_folder_enabled=False,
                file_number_mode="Reset",
                file_prefix="FX3",
                post_folder_name_form="Date Form",
                post_file_number_mode="Reset",
                post_file_prefix="FX3",
                target_media_slot=2,
                requested_vault_action="CREATE_NEW_FOLDER",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertTrue(rep_slot2_folder.passed, rep_slot2_folder.errors)

        rep_slot2_rate = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=2,
                requested_rating_stars=5,
                rating_set_custom_key_mask=(1, 3, 5),
                requested_vault_action="PLAYBACK_RATING_SET",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertTrue(rep_slot2_rate.passed, rep_slot2_rate.errors)

    def test_46_leading_underscore_file_prefix_or_folder_cap_overflow_rejected(self) -> None:
        rep_prefix = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                file_prefix="_FX",
                post_file_prefix="_FX",
            )
        )
        self.assertFalse(rep_prefix.passed)
        self.assertEqual(rep_prefix.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT)

        rep_cap = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                current_folder_still_count=P308_FOLDER_MAX_STILLS + 1,
                target_media_slot=2,
                requested_vault_action="CREATE_NEW_FOLDER",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertFalse(rep_cap.passed)
        self.assertEqual(rep_cap.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT)

        st_max = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Standard Form",
            file_number_mode="Series",
            file_prefix="DSC",
            current_folder_still_count=P308_FOLDER_MAX_STILLS,
            target_slot=2,
            dual_slot_simult_rec=False,
            slot1_holds_tier0_vault=True,
            requested_vault_action="CREATE_NEW_FOLDER",
            requested_rating_stars=0,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=False,
            reset_action="None",
        )
        self.assertTrue(st_max["folder_max_reached"])
        self.assertTrue(st_max["action_allowed"])

    def test_47_slot1_tier0_vault_firewall_blocks_create_new_folder(self) -> None:
        st = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Standard Form",
            file_number_mode="Series",
            file_prefix="DSC",
            current_folder_still_count=42,
            target_slot=1,
            dual_slot_simult_rec=False,
            slot1_holds_tier0_vault=True,
            requested_vault_action="CREATE_NEW_FOLDER",
            requested_rating_stars=0,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=False,
            reset_action="None",
        )
        self.assertFalse(st["action_allowed"])
        self.assertEqual(st["firewall_errno"], "EROFS")
        self.assertEqual(st["firewall_errno_num"], 30)

        for allowed_flag, errno_val in ((False, "EROFS"), (True, None)):
            rep = evaluate_aperture_drive_folder_rating_vault(
                build_default_safe_aperture_drive_folder_rating_vault_spec(
                    target_media_slot=1,
                    slot1_holds_tier0_vault=True,
                    requested_vault_action="CREATE_NEW_FOLDER",
                    reported_vault_action_allowed=allowed_flag,
                    vault_firewall_errno=errno_val,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_48_slot1_tier0_vault_firewall_blocks_playback_rating_and_add_rating(self) -> None:
        for act in ("PLAYBACK_RATING_SET", "SHOOT_ADD_RATING", "FORCED_FILE_NUMBER_RESET"):
            st = compute_expected_folder_and_rating_vault_state(
                folder_name_form="Standard Form",
                file_number_mode="Series",
                file_prefix="DSC",
                current_folder_still_count=42,
                target_slot=1,
                dual_slot_simult_rec=False,
                slot1_holds_tier0_vault=True,
                requested_vault_action=act,
                requested_rating_stars=4,
                image_already_rated=False,
                shooting_domain="Still",
                background_transfer_active=False,
                reset_action="None",
            )
            self.assertFalse(st["action_allowed"], act)
            self.assertEqual(st["firewall_errno"], "EROFS", act)
            self.assertEqual(st["firewall_errno_num"], 30, act)

            for allowed_flag, errno_val in ((False, "EROFS"), (True, None)):
                rep = evaluate_aperture_drive_folder_rating_vault(
                    build_default_safe_aperture_drive_folder_rating_vault_spec(
                        target_media_slot=1,
                        slot1_holds_tier0_vault=True,
                        requested_rating_stars=4,
                        requested_vault_action=act,
                        reported_vault_action_allowed=allowed_flag,
                        vault_firewall_errno=errno_val,
                    )
                )
                self.assertFalse(rep.passed, (act, allowed_flag))
                self.assertEqual(rep.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)
                self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_49_dual_slot_simult_rec_and_add_rating_no_overwrite_and_bg_transfer_ebusy(self) -> None:
        st_simult = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Standard Form",
            file_number_mode="Series",
            file_prefix="DSC",
            current_folder_still_count=42,
            target_slot=2,
            dual_slot_simult_rec=True,
            slot1_holds_tier0_vault=True,
            requested_vault_action="SELECT_REC_FOLDER_SIMULT_SHOOT",
            requested_rating_stars=0,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=False,
            reset_action="None",
        )
        self.assertFalse(st_simult["action_allowed"])
        self.assertEqual(st_simult["firewall_errno"], "EROFS")

        rep_simult = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=2,
                dual_slot_simult_rec=True,
                slot1_holds_tier0_vault=True,
                requested_vault_action="SELECT_REC_FOLDER_SIMULT_SHOOT",
                reported_vault_action_allowed=False,
                vault_firewall_errno="EROFS",
            )
        )
        self.assertFalse(rep_simult.passed)
        self.assertEqual(rep_simult.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

        rep_already_rated = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=2,
                image_already_rated=True,
                requested_vault_action="SHOOT_ADD_RATING",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertFalse(rep_already_rated.passed)
        self.assertEqual(
            rep_already_rated.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT
        )

        st_bg = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Standard Form",
            file_number_mode="Series",
            file_prefix="DSC",
            current_folder_still_count=42,
            target_slot=2,
            dual_slot_simult_rec=False,
            slot1_holds_tier0_vault=True,
            requested_vault_action="PLAYBACK_RATING_SET",
            requested_rating_stars=3,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=True,
            reset_action="None",
        )
        self.assertFalse(st_bg["action_allowed"])
        self.assertEqual(st_bg["firewall_errno"], "EBUSY")
        self.assertEqual(st_bg["firewall_errno_num"], 16)

        rep_bg = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=2,
                background_transfer_active=True,
                requested_vault_action="PLAYBACK_RATING_SET",
                reported_vault_action_allowed=False,
                vault_firewall_errno="EBUSY",
            )
        )
        self.assertFalse(rep_bg.passed)
        self.assertEqual(rep_bg.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_50_slot1_mutation_byte_counters_and_format_always_fail_closed(self) -> None:
        for bad_kw in (
            {"slot1_data_sector_writes": 1},
            {"slot1_folder_dir_mutation_bytes": 512},
            {"slot1_rating_avf_info_mutation_bytes": 256},
            {"slot1_vault_mutation_bytes": 4096},
            {"slot1_vault_erofs_ebusy_enforced": False},
            {"slot1_format_hard_locked": False},
            {
                "target_media_slot": 1,
                "requested_vault_action": "FORMAT_QUICK",
                "reported_vault_action_allowed": True,
                "vault_firewall_errno": None,
            },
            {
                "target_media_slot": 1,
                "requested_vault_action": "FORMAT_FULL",
                "reported_vault_action_allowed": True,
                "vault_firewall_errno": None,
            },
        ):
            rep = evaluate_aperture_drive_folder_rating_vault(
                build_default_safe_aperture_drive_folder_rating_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed, bad_kw)
            self.assertEqual(rep.block_code, P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_51_pillar55b_persistent_overlay_escape_rejected(self) -> None:
        for bad_ov in ("/setting/55b", "p2:/setting", "/dev/mmcblk0"):
            rep = evaluate_aperture_drive_folder_rating_vault(
                build_default_safe_aperture_drive_folder_rating_vault_spec(overlay_dir=bad_ov)
            )
            self.assertFalse(rep.passed, bad_ov)
            self.assertEqual(rep.block_code, P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_52_pillar55b_tier0_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_53_pillar55b_invalid_spec_parameters_rejected(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX6"},
            {"shooting_domain": "Burst"},
            {"configured_aperture_drive_in_af": "Turbo"},
            {"configured_af_w_shutter": "Auto"},
            {"configured_pre_af": "Auto"},
            {"configured_circ_of_focus_point": "Spiral"},
            {"circ_wrap_axis": "Hex"},
            {"configured_focus_area_color": "Green"},
            {"reset_action": "WipeAll"},
            {"folder_name_form": "ISO8601"},
            {"file_number_mode": "Random"},
            {"requested_rating_stars": 7},
            {"target_media_slot": 3},
            {"requested_vault_action": "FLASH_BOOT"},
            {"vault_firewall_errno": "EINVAL"},
        ):
            rep = evaluate_aperture_drive_folder_rating_vault(
                build_default_safe_aperture_drive_folder_rating_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed, bad_kw)
            self.assertEqual(rep.block_code, P308_BLOCKED_INVALID_PILLAR55B_SPEC)

    def test_54_rating_zero_clears_or_movie_rating_rejected_when_set(self) -> None:
        rep_movie_rate = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                shooting_domain="Movie",
                requested_rating_stars=3,
                target_media_slot=2,
                requested_vault_action="SHOOT_ADD_RATING",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertFalse(rep_movie_rate.passed)
        self.assertEqual(
            rep_movie_rate.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT
        )

    def test_55_select_rec_folder_date_form_lockout_enforced(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                folder_name_form="Date Form",
                post_folder_name_form="Date Form",
                select_rec_folder_enabled=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT)

    def test_56_pillar55b_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        res = run_pillar55b_aperture_drive_folder_rating_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P308_STATUS_VERIFIED_PILLAR_55B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        allow_cnt = sum(1 for s in res.scenarios if s.expected_allowed)
        reject_cnt = sum(1 for s in res.scenarios if not s.expected_allowed)
        self.assertEqual((allow_cnt, reject_cnt), (2, 4))

    def test_57_compute_expected_aperture_drive_and_focus_ui_state_init_resets(self) -> None:
        st = compute_expected_aperture_drive_and_focus_ui_state(
            camera_model="ILME-FX3",
            configured_aperture_drive_in_af="Silent Priority",
            configured_af_w_shutter="Off",
            configured_pre_af="On",
            lens_supports_pre_af=True,
            configured_circ_of_focus_point="Circulate",
            circ_wrap_axis="Horizontal",
            configured_focus_area_color="Red",
            reset_action="Initialize",
        )
        self.assertFalse(st["circ_diagonal_rejected"])
        self.assertEqual(st["post_aperture_drive"], "Standard")
        self.assertEqual(st["post_af_w_shutter"], "On")
        self.assertEqual(st["post_pre_af"], "Off")
        self.assertEqual(st["post_circ_focus_point"], "Does Not Circulate")
        self.assertEqual(st["post_focus_area_color"], "White")

    def test_58_compute_expected_aperture_drive_ui_state_rejects_diagonal(self) -> None:
        st = compute_expected_aperture_drive_and_focus_ui_state(
            camera_model="ILME-FX3",
            configured_aperture_drive_in_af="Standard",
            configured_af_w_shutter="On",
            configured_pre_af="Off",
            lens_supports_pre_af=True,
            configured_circ_of_focus_point="Circulate",
            circ_wrap_axis="Diagonal",
            configured_focus_area_color="White",
            reset_action="None",
        )
        self.assertTrue(st["circ_diagonal_rejected"])

    def test_59_compute_expected_folder_and_rating_vault_state_firewall(self) -> None:
        st = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Date Form",
            file_number_mode="Reset",
            file_prefix="FX3",
            current_folder_still_count=100,
            target_slot=1,
            dual_slot_simult_rec=False,
            slot1_holds_tier0_vault=True,
            requested_vault_action="CREATE_NEW_FOLDER",
            requested_rating_stars=5,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=False,
            reset_action="Camera Settings Reset",
        )
        self.assertFalse(st["action_allowed"])
        self.assertEqual(st["firewall_errno"], "EROFS")
        self.assertEqual(st["firewall_errno_num"], 30)
        self.assertFalse(st["select_rec_folder_enabled"])
        # Folder Name/File Number/Prefix survive Camera Settings Reset
        self.assertEqual(st["post_folder_name_form"], "Date Form")
        self.assertEqual(st["post_file_number_mode"], "Reset")
        self.assertEqual(st["post_file_prefix"], "FX3")

    def test_60_compute_expected_folder_and_rating_initialize_resets_folder_prefs(self) -> None:
        st = compute_expected_folder_and_rating_vault_state(
            folder_name_form="Date Form",
            file_number_mode="Reset",
            file_prefix="FX3",
            current_folder_still_count=10,
            target_slot=2,
            dual_slot_simult_rec=False,
            slot1_holds_tier0_vault=True,
            requested_vault_action="CREATE_NEW_FOLDER",
            requested_rating_stars=0,
            image_already_rated=False,
            shooting_domain="Still",
            background_transfer_active=False,
            reset_action="Initialize",
        )
        self.assertTrue(st["action_allowed"])
        self.assertEqual(st["post_folder_name_form"], "Standard Form")
        self.assertEqual(st["post_file_number_mode"], "Series")
        self.assertEqual(st["post_file_prefix"], "DSC")

    def test_61_pillar55b_deterministic_sha256_digest(self) -> None:
        spec = build_default_safe_aperture_drive_folder_rating_vault_spec()
        r1 = evaluate_aperture_drive_folder_rating_vault(spec)
        r2 = evaluate_aperture_drive_folder_rating_vault(spec)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        self.assertEqual(len(r1.digest_sha256), 64)

    def test_62_pillar55b_matrix_states_and_to_dict_zero_device_writes(self) -> None:
        d = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec()
        ).to_dict()
        self.assertEqual(d["matrix_states_checked"], 18)
        self.assertEqual(d["physical_device_writes"], 0)
        self.assertFalse(d["persistent_emmc_writes_authorized"])
        self.assertEqual(d["slot1_data_sector_writes"], 0)
        self.assertEqual(d["slot1_folder_dir_mutation_bytes"], 0)
        self.assertEqual(d["slot1_rating_avf_info_mutation_bytes"], 0)

    def test_63_pillar55b_negative_counter_injected_still_blocks(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                aperture_drive_pre_af_shutter_reset_drift_events=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(
            rep.block_code, P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT
        )

    def test_64_rating_custom_key_mask_invalid_stars_rejected(self) -> None:
        rep = evaluate_aperture_drive_folder_rating_vault(
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                rating_set_custom_key_mask=(1, 6),
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT)


class TestPhase308Master55Of55AndCli(unittest.TestCase):
    """Tests 65-85: Combined verifier, Standalone Pillar 55, 55/55 Recovery Master, and CLI."""

    def test_65_combined_verifier_default_and_symmetry_alias_pass(self) -> None:
        rep1 = verify_lens_comp_af_illuminator_folder_rating_and_vault(force_clean_room=True)
        rep2 = verify_lens_comp_af_illuminator_folder_rating_vault(force_clean_room=True)
        self.assertTrue(rep1.all_passed)
        self.assertTrue(rep1.passed)
        self.assertEqual(rep1.status, P308_STATUS_VERIFIED_PILLAR55_SUITE)
        self.assertEqual(rep1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep2.status, rep1.status)
        self.assertFalse(rep1.overall_ready_for_hardware_attach)
        self.assertFalse(rep1.cross_model_flash_authorized)
        self.assertEqual(rep1.raw_firmware_bytes_leaked, 0)

    def test_66_combined_verifier_propagates_55a_and_55b_spec_failures(self) -> None:
        bad_55a = build_default_safe_lens_comp_af_illuminator_vault_spec(
            requested_shading_comp="Auto: Low",
            shading_comp_rejected_errno=0,
            dormant_shading_auto_low_exposed=True,
            post_shading_comp="Auto: Low",
        )
        rep_a = verify_lens_comp_af_illuminator_folder_rating_and_vault(
            force_clean_room=True, spec_55a=bad_55a
        )
        self.assertFalse(rep_a.all_passed)
        self.assertFalse(rep_a.lens_comp_af_illuminator_report.passed)

        bad_55b = build_default_safe_aperture_drive_folder_rating_vault_spec(
            target_media_slot=1,
            requested_vault_action="CREATE_NEW_FOLDER",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
        )
        rep_b = verify_lens_comp_af_illuminator_folder_rating_and_vault(
            force_clean_room=True, spec_55b=bad_55b
        )
        self.assertFalse(rep_b.all_passed)
        self.assertFalse(rep_b.aperture_drive_folder_rating_report.passed)

    def test_67_combined_verifier_donor_failure_propagates_to_errors(self) -> None:
        base_snap = inspect_phase308_donors_readonly(force_clean_room=True)
        bad_snap = p308.Phase308DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=False,
            donor_files_inspected=0,
            elapsed_seconds=0.01,
            under_0_20s_budget=True,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=base_snap.artifacts,
        )
        with mock.patch.object(p308, "inspect_phase308_donors_readonly", return_value=bad_snap):
            rep = verify_lens_comp_af_illuminator_folder_rating_and_vault()
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("donor artifact parity" in e for e in rep.errors))

    def test_68_standalone_pillar55_suite_passes_default_mode(self) -> None:
        rep = run_pillar55_standalone_suite()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P308_STATUS_VERIFIED_PILLAR55_SUITE)
        self.assertEqual(rep.pillar_55a_lens_comp_af_illuminator_vault.scenarios_passed, 6)
        self.assertEqual(rep.pillar_55b_aperture_drive_folder_rating_vault.scenarios_passed, 6)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_folder_dir_mutation_bytes, 0)
        self.assertEqual(rep.slot1_rating_avf_info_mutation_bytes, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertLess(rep.elapsed_seconds, P308_FAST_CLI_BUDGET_SECONDS + _ci_headroom())

    def test_69_standalone_pillar55_suite_clean_room_deterministic_sha256(self) -> None:
        r1 = run_pillar55_standalone_suite(force_clean_room=True)
        r2 = run_pillar55_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(len(r1.suite_sha256), 64)

    def test_70_standalone_pillar55_suite_propagates_55a_failure(self) -> None:
        bad_res = p308.Pillar55ASuiteResult(
            passed=False, status="FAIL", scenarios_passed=5, scenarios_total=6, scenarios=()
        )
        with mock.patch.object(
            p308, "run_pillar55a_lens_comp_af_illuminator_6_scenario_suite", return_value=bad_res
        ):
            rep = run_pillar55_standalone_suite(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.dormant_shading_auto_low_exposure_events, 1)

    def test_71_standalone_pillar55_suite_propagates_donor_budget_failure(self) -> None:
        base_snap = inspect_phase308_donors_readonly(force_clean_room=True)
        slow_snap = p308.Phase308DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=18,
            elapsed_seconds=9.9,
            under_0_20s_budget=False,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=base_snap.artifacts,
        )
        with mock.patch.object(p308, "inspect_phase308_donors_readonly", return_value=slow_snap):
            rep = run_pillar55_standalone_suite()
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("budget" in e for e in rep.errors))

    def test_72_master_55_of_55_passes_in_clean_room_under_fast_budget(self) -> None:
        rep = evaluate_realhw_55pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P308_STATUS_VERIFIED_55OF55_AGGREGATOR)
        self.assertGreaterEqual(rep.pillar_count, 55)
        self.assertGreaterEqual(rep.pillars_passed, 55)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertLess(rep.elapsed_seconds, P308_FAST_CLI_BUDGET_SECONDS + _ci_headroom())
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_73_master_55_of_55_passes_default_mode_and_aliases_match(self) -> None:
        rep = evaluate_realhw_55pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertGreaterEqual(rep.pillar_count, 55)
        self.assertGreaterEqual(rep.pillars_passed, 55)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_folder_dir_mutation_bytes, 0)
        self.assertEqual(rep.slot1_rating_avf_info_mutation_bytes, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertFalse(rep.fx3_exposes_shading_auto_low)
        self.assertTrue(rep.fx3_has_builtin_af_illuminator)
        self.assertTrue(p308.P308_FX3_SUPPORTS_MISHOE_FLASH_ILLUMINATOR)
        self.assertFalse(rep.fx6_has_builtin_af_illuminator)
        self.assertFalse(rep.fx6_has_aperture_drive_pre_af_circ_color)
        self.assertFalse(rep.fx6_has_msdcf_or_star_rating)

        alias1 = evaluate_55pillar_recovery_master(force_clean_room=True)
        alias2 = verify_55pillar_recovery_suite(force_clean_room=True)
        self.assertGreaterEqual(alias1.pillar_count, 55)
        self.assertGreaterEqual(alias2.pillar_count, 55)
        self.assertEqual(alias1.master_55pillar_sha256, alias2.master_55pillar_sha256)

    def test_74_master_55_inherits_54_pillars_plus_pillar_55_lineage(self) -> None:
        m54 = evaluate_realhw_54pillar_recovery_master(force_clean_room=True)
        m55 = evaluate_realhw_55pillar_recovery_master(force_clean_room=True)
        self.assertGreaterEqual(m55.pillar_count, 55)
        self.assertEqual(m55.pillar_count, m54.pillar_count + 1)
        self.assertEqual(
            [p.pillar_id for p in m55.pillars[:54]],
            [p.pillar_id for p in m54.pillars],
        )
        self.assertEqual(
            m55.pillars[54].pillar_id,
            "pillar_55_lens_comp_af_illuminator_folder_rating_vault",
        )
        self.assertEqual(m55.pillars[54].phase_label, "Phase 308 (Wave-53)")

    def test_75_master_55_fault_injection_on_pillar_55_and_pillar_1_fails_closed(self) -> None:
        rep55 = evaluate_realhw_55pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_55_lens_comp_af_illuminator_folder_rating_vault",
        )
        self.assertFalse(rep55.all_passed)
        self.assertEqual(rep55.pillars_passed, 54)
        self.assertEqual(
            rep55.failed_pillars,
            ("pillar_55_lens_comp_af_illuminator_folder_rating_vault",),
        )
        self.assertFalse(rep55.overall_ready_for_hardware_attach)

        rep1 = evaluate_realhw_55pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_55_PILLAR_IDS[0],
        )
        self.assertFalse(rep1.all_passed)
        self.assertEqual(rep1.pillars_passed, 54)
        self.assertEqual(rep1.failed_pillars, (MASTER_55_PILLAR_IDS[0],))

    def test_76_master_55_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_55pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_77_master_55_milestone_295_negative_safety_bool_audit(self) -> None:
        d = evaluate_realhw_55pillar_recovery_master(force_clean_room=True).to_dict()
        negative_keys = (
            "overall_ready_for_hardware_attach",
            "cross_model_flash_authorized",
            "hardware_live_attachment_authorized",
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "allow_boot_partition_targeting",
            "allow_destructive_fastboot",
            "live_usb_iokit_transmit_enabled",
            "fx3_exposes_shading_auto_low",
            "fx6_has_builtin_af_illuminator",
            "fx6_has_aperture_drive_pre_af_circ_color",
            "fx6_has_msdcf_or_star_rating",
        )
        for key in negative_keys:
            self.assertFalse(d[key], f"Expected False for {key}")
        self.assertTrue(d["cnflasha_userspace_write_blocked"])
        self.assertTrue(d["slot1_format_hard_locked"])
        self.assertTrue(d["slot1_vault_erofs_ebusy_enforced"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(d["physical_device_writes"], 0)

    def test_78_master_55_detects_cross_model_flash_tamper(self) -> None:
        m54 = evaluate_realhw_54pillar_recovery_master(force_clean_room=True)
        p55 = run_pillar55_standalone_suite(force_clean_room=True)
        bad_p55 = p308.Pillar55StandaloneReport(
            **{**p55.__dict__, "cross_model_flash_authorized": True}
        )
        with mock.patch.object(
            p308, "evaluate_realhw_54pillar_recovery_master", return_value=m54
        ), mock.patch.object(p308, "run_pillar55_standalone_suite", return_value=bad_p55):
            rep = evaluate_realhw_55pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("cross_model_flash_authorized" in e for e in rep.errors))

    def test_79_cli_inprocess_help_and_pillar55_json(self) -> None:
        buf_help = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "--help"]):
            with self.assertRaises(SystemExit) as ctx, redirect_stdout(buf_help):
                cli_main.main()
        self.assertEqual(ctx.exception.code, 0)
        help_txt = buf_help.getvalue()
        self.assertIn("verify-55pillar-recovery", help_txt)
        self.assertIn("verify-pillar55-lens-comp-af-illuminator-folder-rating-vault", help_txt)

        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar55-lens-comp-af-illuminator-folder-rating-vault",
                "--force-clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_80_cli_inprocess_verify_55pillar_recovery_json_and_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p308_m55_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-55pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            payload = json.loads(buf.getvalue())
            report_file = out_dir / "55pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            file_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(payload, file_payload)
            self.assertTrue(payload["all_passed"])
            self.assertGreaterEqual(payload["pillar_count"], 55)
            self.assertGreaterEqual(payload["pillars_passed"], 55)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_81_cli_inprocess_human_readable_summary_exits_zero(self) -> None:
        buf55 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar55-lens-comp-af-illuminator-folder-rating-vault",
                "--force-clean-room",
            ],
        ):
            with redirect_stdout(buf55):
                rc55 = cli_main.main()
        self.assertEqual(rc55, 0)
        self.assertIn("pillar_55a=6/6 pillar_55b=6/6", buf55.getvalue())

        bufm = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-55pillar-recovery", "--force-clean-room"],
        ):
            with redirect_stdout(bufm):
                rcm = cli_main.main()
        self.assertEqual(rcm, 0)
        self.assertIn("pillars=55/55", bufm.getvalue())

    def test_82_cli_subprocess_help_uses_sys_executable(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "--help"],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("verify-55pillar-recovery", proc.stdout)

    def test_83_cli_subprocess_verify_55pillar_recovery_clean_room_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-55pillar-recovery",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 55)
        self.assertGreaterEqual(payload["pillars_passed"], 55)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertLess(payload["elapsed_seconds"], P308_FAST_CLI_BUDGET_SECONDS + _ci_headroom())
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["cross_model_flash_authorized"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_84_cli_subprocess_pillar55_fx3_clean_room_test_env_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar55-lens-comp-af-illuminator-folder-rating-vault",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(**{P308_ENV_CLEAN_ROOM_TEST: "1"}),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["donor_snapshot"]["donor_files_inspected"], 18)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_85_cli_subprocess_fx3_fx6_force_clean_room_env_55pillar(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-55pillar-recovery",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(FX3_FX6_FORCE_CLEAN_ROOM="1"),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 55)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)


if __name__ == "__main__":
    unittest.main()
