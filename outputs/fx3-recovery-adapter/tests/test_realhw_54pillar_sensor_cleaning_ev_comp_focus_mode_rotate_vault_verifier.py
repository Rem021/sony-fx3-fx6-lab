"""Phase 304 — Dual-mode unit tests for Recovery Pillar 54 & Unified 54/54 Recovery Master.

Covers:
1. Sub-Pillar 54A:
   - `[Sensor Cleaning]` (`>= 51%` NP-FZ100 battery gate `.uxc 0xe574` vs pre-V2 `>= 3` bars +
     mandatory physical power-switch `OFF` `_g.uxc 0x6221` before lens removal vs IBIS-less
     `ILME-FX6` Electronic Variable ND `1/4..1/128` + `CLEAR` + `Technical > APR`).
   - `[Exposure Comp.]` (`+-5.0 EV` Still / `+-2.0 EV` Movie & `S&Q`, `M + ISO AUTO` only,
     `[Exposure step]` `0.3EV`/`0.5EV` `Initialize`-only, dormant `[Reset EV Comp.]` `0x7853` /
     `[Dial Ev Comp]` `0xe4d9` omitted, 100% `[Cine EI]` / `[Cine EI Quick]` lockout).
2. Sub-Pillar 54B:
   - `[Focus Mode]` (5 Still modes vs Movie/`S&Q` 2-mode `AF-C` / `MF` clamp `EOPNOTSUPP=95`
     / `EINVAL=22`, `[Priority Set in AF-S/AF-C]` `Initialize`-only, Still-only `[AF Illuminator]`).
   - `[Playback]` (`[View Mode]`, exact `9 Images` / `25 Images` `[Image Index]`,
     `[Display as Group]`, `[Display Rotation]`, and CRITICAL `Slot-1` Tier-0 Recovery Vault
     Firewall failing closed on `[Rotate]` EXIF / `AVF_INFO` mutations with `EROFS=30`/`EBUSY=16`).
3. Unified `54/54` Recovery Master (`evaluate_realhw_54pillar_recovery_master` / CLI).
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier as p304,
)
from fx3_recovery.realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier import (
    evaluate_realhw_53pillar_recovery_master,
)
from fx3_recovery.realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_54_PILLAR_COUNT,
    MASTER_54_PILLAR_IDS,
    MASTER_54_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT,
    P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT,
    P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT,
    P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION,
    P304_BLOCKED_INVALID_PILLAR54A_SPEC,
    P304_BLOCKED_INVALID_PILLAR54B_SPEC,
    P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT,
    P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT,
    P304_BLOCKED_SAFETY_POLICY_VIOLATION,
    P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION,
    P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P304_CINE_EI_BASE_ISOS,
    P304_CINE_EI_LOCKED_LOG_MODES,
    P304_DONOR_INSPECT_BUDGET_SECONDS,
    P304_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P304_DORMANT_FOCUS_MODES,
    P304_DORMANT_IMAGE_INDEX_MODES,
    P304_ENV_CLEAN_ROOM_TEST,
    P304_EV_COMP_MOVIE_MAX_EV,
    P304_EV_COMP_MOVIE_MIN_EV,
    P304_EV_COMP_STILL_MAX_EV,
    P304_EV_COMP_STILL_MIN_EV,
    P304_EXPOSURE_STEPS,
    P304_FAST_CLI_BUDGET_SECONDS,
    P304_FX3_FW_VERSION,
    P304_FX3_HELPGUIDE_ID,
    P304_FX3_MODEL_ID,
    P304_FX3_MODEL_NAME,
    P304_FX3_PRE_V2_FW_VERSIONS,
    P304_FX3_SUPPORTED_FW_VERSIONS,
    P304_FX6_DONOR_FW_VERSION,
    P304_FX6_DONOR_MODEL_NAME,
    P304_FX6_VARIABLE_ND_VALUES,
    P304_IMAGE_INDEX_MODES,
    P304_MANDATORY_POWER_OFF_G_RESID16,
    P304_MOVIE_SQ_FOCUS_MODES,
    P304_MOVIE_SQ_LOCKED_OUT_FOCUS_MODES,
    P304_NP_FZ100_MIN_CLEANING_PCT,
    P304_PINNED_FX3_APPFW_702_BYTES,
    P304_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P304_PINNED_FX3_BACKUP_BIN_BYTES,
    P304_PINNED_FX3_BACKUP_BIN_SHA256,
    P304_PINNED_FX6_APPFW_601_BYTES,
    P304_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P304_POWER_INSUFFICIENT_RESID16,
    P304_STAGE_B_VOLATILE_OVERLAY_DIR,
    P304_STATUS_VERIFIED_54OF54_AGGREGATOR,
    P304_STATUS_VERIFIED_PILLAR54_SUITE,
    P304_STATUS_VERIFIED_PILLAR_54A,
    P304_STATUS_VERIFIED_PILLAR_54B,
    P304_STILL_FOCUS_MODES,
    P304_VIEW_MODE_SUPPORTED,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE304_PHASE_NUMBER,
    PHASE304_SCHEMA,
    PHASE304_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_focus_mode_playback_rotate_vault_spec,
    build_default_safe_sensor_cleaning_ev_comp_vault_spec,
    compute_expected_exposure_comp_state,
    compute_expected_focus_mode_state,
    compute_expected_playback_rotate_state,
    compute_expected_sensor_cleaning_state,
    evaluate_54pillar_recovery_master,
    evaluate_focus_mode_playback_rotate_vault,
    evaluate_realhw_54pillar_recovery_master,
    evaluate_sensor_cleaning_ev_comp_vault,
    inspect_phase304_donors_readonly,
    run_pillar54_standalone_suite,
    run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite,
    run_pillar54b_focus_mode_playback_rotate_6_scenario_suite,
    verify_54pillar_recovery_suite,
    verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault,
    verify_sensor_cleaning_ev_comp_focus_mode_rotate_vault,
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


class TestPhase304SafetyDonorsAndExports(unittest.TestCase):
    """Tests 01-12: Safety locks, package exports, donor inspection, and mode switches."""

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
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_camera_identity_constants(self) -> None:
        self.assertEqual(
            PHASE304_SCHEMA,
            "realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier_v1",
        )
        self.assertEqual(PHASE304_VERSION, "1.0.0")
        self.assertEqual(PHASE304_PHASE_NUMBER, 304)
        self.assertEqual(P304_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P304_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P304_FX3_FW_VERSION, "7.02")
        self.assertEqual(P304_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P304_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P304_FX6_DONOR_FW_VERSION, "6.01")

    def test_03_init_exports_and_non_overlapping_master_54_registry(self) -> None:
        self.assertIs(
            fx3_recovery.evaluate_realhw_54pillar_recovery_master,
            evaluate_realhw_54pillar_recovery_master,
        )
        self.assertIs(fx3_recovery.evaluate_54pillar_recovery_master, evaluate_54pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_54pillar_recovery_suite, verify_54pillar_recovery_suite)
        self.assertIs(fx3_recovery.run_pillar54_standalone_suite, run_pillar54_standalone_suite)
        self.assertIs(fx3_recovery.CROSS_MODEL_FLASH_AUTHORIZED, CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(MASTER_54_PILLAR_COUNT, 54)
        self.assertEqual(len(MASTER_54_PILLAR_SPECS), 54)
        self.assertEqual(len(MASTER_54_PILLAR_IDS), 54)
        self.assertEqual(len(set(MASTER_54_PILLAR_IDS)), 54)
        self.assertEqual(MASTER_54_PILLAR_SPECS[53][0], 54)
        self.assertEqual(
            MASTER_54_PILLAR_SPECS[53][1],
            "pillar_54_sensor_cleaning_ev_comp_focus_mode_rotate_vault",
        )

    def test_04_safety_invariant_tamper_rejected_in_54a_and_54b(self) -> None:
        with mock.patch.object(p304, "CROSS_MODEL_FLASH_AUTHORIZED", True):
            rep_a = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec()
            )
            rep_b = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P304_BLOCKED_SAFETY_POLICY_VIOLATION)
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P304_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_05_inspect_donors_clean_room_forced_returns_17_pinned_artifacts(self) -> None:
        snap = inspect_phase304_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertLess(snap.elapsed_seconds, P304_DONOR_INSPECT_CI_BUDGET_SECONDS + _ci_headroom())
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P304_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(
            by_id["fx3_appfw_702_so"].digest_sha256, P304_PINNED_FX3_APPFW_702_HDR4K_SHA256
        )
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P304_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(
            by_id["fx6_appfw_601_so"].digest_sha256, P304_PINNED_FX6_APPFW_601_HDR4K_SHA256
        )
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P304_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P304_PINNED_FX3_BACKUP_BIN_SHA256)

    def test_06_inspect_donors_honors_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {P304_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase304_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 17)

    def test_07_inspect_donors_honors_fx3_fx6_force_clean_room_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase304_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)
            self.assertEqual(snap.donor_files_inspected, 17)

    def test_08_inspect_donors_auto_fallback_when_donor_missing(self) -> None:
        with mock.patch.object(p304, "resolve_donor_path", return_value=None):
            with mock.patch.dict(
                os.environ,
                {P304_ENV_CLEAN_ROOM_TEST: "0", "FX3_FX6_FORCE_CLEAN_ROOM": "0"},
                clear=False,
            ):
                snap = inspect_phase304_donors_readonly(force_clean_room=None)
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 17)

    def test_09_inspect_donors_local_o_rdonly_uses_bounded_header_and_o_rdonly_flags(self) -> None:
        clean_flag = (
            os.environ.get(P304_ENV_CLEAN_ROOM_TEST, "") == "1"
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "") == "1"
        )
        snap = inspect_phase304_donors_readonly(force_clean_room=None)
        if clean_flag or snap.verification_mode == "CLEAN_ROOM_SYNTHETIC":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(snap.all_donors_present)
            for art in snap.artifacts:
                self.assertEqual(art.read_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(art.matches_pinned, art.artifact_id)
                if art.artifact_id.endswith("_so"):
                    self.assertEqual(art.digest_kind, "HEADER4K_SHA256")
                    self.assertEqual(art.header_bytes_read, 4096)

    def test_10_read_donor_readonly_bounded_rejects_symlink_and_missing(self) -> None:
        self.assertEqual(p304._read_donor_readonly_bounded("definitely/missing/file.bin")[:3], (False, 0, 0))
        with tempfile.TemporaryDirectory() as td:
            real_f = Path(td) / "real.bin"
            real_f.write_bytes(b"uxc\x07" + b"\x00" * 32)
            link_f = Path(td) / "link.bin"
            link_f.symlink_to(real_f)
            with mock.patch.object(p304, "resolve_donor_path", return_value=link_f):
                present, _, _, mode, _, _ = p304._read_donor_readonly_bounded("link.bin")
                if hasattr(os, "O_NOFOLLOW"):
                    self.assertFalse(present)
                    self.assertEqual(mode, "OPEN_ERROR")

    def test_11_binary_header_validators_reject_malformed_inputs(self) -> None:
        self.assertFalse(p304._check_elf64_aarch64(b"BAD", "x")[0])
        self.assertFalse(p304._check_uxc7_pack(b"NOPE", "x")[0])
        self.assertFalse(p304._check_bk4_backup(b"NOPE", "x")[0])

    def test_12_donor_snapshot_to_dict_serializable_zero_leaked_bytes(self) -> None:
        payload = inspect_phase304_donors_readonly(force_clean_room=True).to_dict()
        encoded = json.dumps(payload, sort_keys=True)
        self.assertIn("fx3_appfw_702_so", encoded)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertLessEqual(
            payload["budget_seconds_applied"],
            max(P304_DONOR_INSPECT_BUDGET_SECONDS, P304_DONOR_INSPECT_CI_BUDGET_SECONDS),
        )


class TestPhase304Pillar54ASensorCleaningEvCompVault(unittest.TestCase):
    """Tests 13-38: Pillar 54A (Sensor Cleaning >= 51% + Power-OFF vs FX6 e-ND/APR, Exposure Comp)."""

    def test_13_default_safe_54a_spec_passes(self) -> None:
        rep = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P304_STATUS_VERIFIED_PILLAR_54A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.sensor_cleaning_51pct_poweroff_verified)
        self.assertTrue(rep.fx6_end_apr_contrast_verified)
        self.assertTrue(rep.ev_comp_range_iso_auto_and_cine_ei_lockout_verified)
        self.assertTrue(rep.slot1_vault_firewall_and_h0_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_14_sensor_cleaning_exact_51pct_boundary_passes_across_v2_to_v702(self) -> None:
        for fw in P304_FX3_SUPPORTED_FW_VERSIONS:
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    fw_version=fw,
                    battery_pct=P304_NP_FZ100_MIN_CLEANING_PCT,
                    cleaning_mode_entered=True,
                    power_switch_off_after_shake=True,
                    lens_removed_before_power_off=False,
                )
            )
            self.assertTrue(rep.passed, f"fw={fw}: {rep.errors}")

    def test_15_sensor_cleaning_below_51pct_aborts_0xe574_and_rejects_bypass(self) -> None:
        for pct in (0, 25, 49, 50):
            allowed, _, resid, path_tag = compute_expected_sensor_cleaning_state(
                camera_model=P304_FX3_MODEL_NAME,
                fw_version="7.02",
                battery_pct=pct,
                battery_bars=2,
                power_switch_off_after_shake=True,
                lens_removed_before_power_off=False,
            )
            self.assertFalse(allowed, pct)
            self.assertEqual(resid, P304_POWER_INSUFFICIENT_RESID16)
            self.assertEqual(path_tag, "V2_PLUS_BELOW_51PCT")

            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    fw_version="7.02",
                    battery_pct=pct,
                    cleaning_mode_entered=True,
                    sensor_cleaning_low_battery_bypass_events=1,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(
                rep.block_code, P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION
            )

    def test_16_sensor_cleaning_pre_v2_firmware_uses_3_bars_gate(self) -> None:
        for fw in P304_FX3_PRE_V2_FW_VERSIONS:
            ok_bars, _, _, _ = compute_expected_sensor_cleaning_state(
                camera_model=P304_FX3_MODEL_NAME,
                fw_version=fw,
                battery_pct=48,
                battery_bars=3,
                power_switch_off_after_shake=True,
                lens_removed_before_power_off=False,
            )
            self.assertTrue(ok_bars, fw)
            rep_ok = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    fw_version=fw,
                    battery_pct=48,
                    battery_bars=3,
                )
            )
            self.assertTrue(rep_ok.passed, f"{fw}: {rep_ok.errors}")

            low_bars, _, resid, tag = compute_expected_sensor_cleaning_state(
                camera_model=P304_FX3_MODEL_NAME,
                fw_version=fw,
                battery_pct=48,
                battery_bars=2,
                power_switch_off_after_shake=True,
                lens_removed_before_power_off=False,
            )
            self.assertFalse(low_bars)
            self.assertEqual(resid, P304_POWER_INSUFFICIENT_RESID16)
            self.assertEqual(tag, "PRE_V2_LOW_BARS")

    def test_17_sensor_cleaning_mandatory_power_switch_off_and_lens_order_enforced(self) -> None:
        for bad in (
            {"power_switch_off_after_shake": False},
            {"lens_removed_before_power_off": True},
            {"mandatory_power_off_msg_resid16": None},
            {"power_insufficient_msg_resid16": P304_POWER_INSUFFICIENT_RESID16},
            {"sensor_cleaning_no_power_off_violations": 1},
        ):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(**bad)
            )
            self.assertFalse(rep.passed, bad)
            self.assertEqual(
                rep.block_code, P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION
            )

    def test_18_fx6_variable_nd_all_steps_and_technical_apr_positive_contrast(self) -> None:
        for nd_val in P304_FX6_VARIABLE_ND_VALUES:
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    camera_model=P304_FX6_DONOR_MODEL_NAME,
                    fw_version=P304_FX6_DONOR_FW_VERSION,
                    cleaning_mode_entered=False,
                    power_switch_off_after_shake=False,
                    mandatory_power_off_msg_resid16=None,
                    fx6_variable_nd_step=nd_val,
                    fx6_apr_supported=True,
                    fx6_ultrasonic_ibis_shake_attempted=False,
                    fx6_cr_sensor_cleaning_supported=False,
                )
            )
            self.assertTrue(rep.passed, f"nd={nd_val}: {rep.errors}")

    def test_19_fx6_ultrasonic_ibis_shake_or_cr320_spoof_rejected(self) -> None:
        for bad_fx6 in (
            {"fx6_ultrasonic_ibis_shake_attempted": True},
            {"fx6_cr_sensor_cleaning_supported": True},
            {"fx6_apr_supported": False},
            {"fx6_ibis_shake_conflation_events": 1},
            {
                "camera_model": P304_FX6_DONOR_MODEL_NAME,
                "fw_version": P304_FX6_DONOR_FW_VERSION,
                "cleaning_mode_entered": True,
                "power_switch_off_after_shake": True,
            },
        ):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(**bad_fx6)
            )
            self.assertFalse(rep.passed, bad_fx6)
            self.assertEqual(rep.block_code, P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION)

    def test_20_ev_comp_still_5_0_ev_and_movie_sq_2_0_ev_ranges_pass(self) -> None:
        for ev in (P304_EV_COMP_STILL_MIN_EV, -1.7, 0.0, 2.3, P304_EV_COMP_STILL_MAX_EV):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    shooting_domain="Still",
                    exposure_mode="P",
                    requested_ev_comp_ev=ev,
                    reported_ev_comp_active=True,
                    reported_ev_comp_min_ev=-5.0,
                    reported_ev_comp_max_ev=5.0,
                    post_reset_ev_comp_ev=ev,
                )
            )
            self.assertTrue(rep.passed, f"still ev={ev}: {rep.errors}")

        for domain in ("Movie", "S&Q"):
            for ev in (P304_EV_COMP_MOVIE_MIN_EV, -0.7, 0.0, 1.3, P304_EV_COMP_MOVIE_MAX_EV):
                rep = evaluate_sensor_cleaning_ev_comp_vault(
                    build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                        shooting_domain=domain,
                        exposure_mode="A",
                        requested_ev_comp_ev=ev,
                        reported_ev_comp_active=True,
                        reported_ev_comp_min_ev=-2.0,
                        reported_ev_comp_max_ev=2.0,
                        post_reset_ev_comp_ev=ev,
                    )
                )
                self.assertTrue(rep.passed, f"{domain} ev={ev}: {rep.errors}")

    def test_21_ev_comp_out_of_range_rejected_for_still_and_movie_sq(self) -> None:
        rep_still = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Still",
                requested_ev_comp_ev=5.3,
                post_reset_ev_comp_ev=5.3,
            )
        )
        self.assertFalse(rep_still.passed)
        self.assertEqual(rep_still.block_code, P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT)

        for domain in ("Movie", "S&Q"):
            rep_mv = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    shooting_domain=domain,
                    requested_ev_comp_ev=2.3,
                    reported_ev_comp_min_ev=-2.0,
                    reported_ev_comp_max_ev=2.0,
                    post_reset_ev_comp_ev=2.3,
                )
            )
            self.assertFalse(rep_mv.passed, domain)
            self.assertEqual(
                rep_mv.block_code, P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT
            )

    def test_22_ev_comp_manual_m_iso_auto_allowed_vs_fixed_iso_locked_out(self) -> None:
        rep_auto = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                iso_mode="ISO AUTO",
                requested_ev_comp_ev=-1.7,
                reported_ev_comp_active=True,
                reported_ev_comp_min_ev=-2.0,
                reported_ev_comp_max_ev=2.0,
                post_reset_ev_comp_ev=-1.7,
            )
        )
        self.assertTrue(rep_auto.passed, rep_auto.errors)

        rep_fixed_ok = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                iso_mode="ISO 800",
                requested_ev_comp_ev=0.0,
                reported_ev_comp_active=False,
                reported_ev_comp_min_ev=-2.0,
                reported_ev_comp_max_ev=2.0,
                post_reset_ev_comp_ev=0.0,
            )
        )
        self.assertTrue(rep_fixed_ok.passed, rep_fixed_ok.errors)

        rep_fixed_spoof = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                iso_mode="ISO 800",
                requested_ev_comp_ev=1.0,
                reported_ev_comp_active=True,
                reported_ev_comp_min_ev=-2.0,
                reported_ev_comp_max_ev=2.0,
                post_reset_ev_comp_ev=1.0,
            )
        )
        self.assertFalse(rep_fixed_spoof.passed)
        self.assertEqual(
            rep_fixed_spoof.block_code, P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT
        )

    def test_23_ev_comp_disabled_in_intelligent_auto(self) -> None:
        rep_ia = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Still",
                exposure_mode="Intelligent Auto",
                reported_ev_comp_active=False,
                post_reset_ev_comp_ev=0.0,
            )
        )
        self.assertTrue(rep_ia.passed, rep_ia.errors)

        rep_ia_spoof = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Still",
                exposure_mode="Intelligent Auto",
                reported_ev_comp_active=True,
            )
        )
        self.assertFalse(rep_ia_spoof.passed)
        self.assertEqual(
            rep_ia_spoof.block_code, P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT
        )

    def test_24_cine_ei_and_cine_ei_quick_100pct_lockout_on_ev_comp(self) -> None:
        for log_mode in P304_CINE_EI_LOCKED_LOG_MODES:
            for base_iso in P304_CINE_EI_BASE_ISOS:
                rep_locked = evaluate_sensor_cleaning_ev_comp_vault(
                    build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                        shooting_domain="Movie",
                        exposure_mode="M",
                        iso_mode="ISO AUTO",
                        log_shooting_mode=log_mode,
                        cine_ei_base_iso=base_iso,
                        cine_ei_exposure_index_ev=-1.0,
                        display_lut_enabled=True,
                        requested_ev_comp_ev=0.0,
                        reported_ev_comp_active=False,
                        reported_ev_comp_min_ev=-2.0,
                        reported_ev_comp_max_ev=2.0,
                        post_reset_ev_comp_ev=0.0,
                    )
                )
                self.assertTrue(rep_locked.passed, f"{log_mode}/{base_iso}: {rep_locked.errors}")

                rep_bypass = evaluate_sensor_cleaning_ev_comp_vault(
                    build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                        shooting_domain="Movie",
                        exposure_mode="A",
                        iso_mode="ISO AUTO",
                        log_shooting_mode=log_mode,
                        cine_ei_base_iso=base_iso,
                        requested_ev_comp_ev=1.0,
                        reported_ev_comp_active=True,
                        reported_ev_comp_min_ev=-2.0,
                        reported_ev_comp_max_ev=2.0,
                        post_reset_ev_comp_ev=1.0,
                    )
                )
                self.assertFalse(rep_bypass.passed, f"{log_mode}/{base_iso}")
                self.assertEqual(
                    rep_bypass.block_code,
                    P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT,
                )

    def test_25_flexible_iso_keeps_ev_comp_active_with_iso_auto(self) -> None:
        rep = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                iso_mode="ISO AUTO",
                log_shooting_mode="Flexible ISO",
                requested_ev_comp_ev=1.0,
                reported_ev_comp_active=True,
                reported_ev_comp_min_ev=-2.0,
                reported_ev_comp_max_ev=2.0,
                post_reset_ev_comp_ev=1.0,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_26_camera_settings_reset_clears_ev_comp_but_exposure_step_survives_until_initialize(
        self,
    ) -> None:
        for step in P304_EXPOSURE_STEPS:
            rep_cam_rst = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    requested_ev_comp_ev=2.0,
                    exposure_step=step,
                    reset_action="Camera Settings Reset",
                    post_reset_ev_comp_ev=0.0,
                    post_reset_exposure_step=step,
                )
            )
            self.assertTrue(rep_cam_rst.passed, f"{step}: {rep_cam_rst.errors}")

        rep_wipe_step = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_ev_comp_ev=0.0,
                post_reset_exposure_step="0.3EV",
            )
        )
        self.assertFalse(rep_wipe_step.passed)
        self.assertEqual(
            rep_wipe_step.block_code, P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT
        )

        rep_init = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                exposure_step="0.5EV",
                reset_action="Initialize",
                post_reset_ev_comp_ev=0.0,
                post_reset_exposure_step="0.3EV",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_27_dormant_reset_ev_comp_and_dial_ev_comp_omitted_in_ilc2210(self) -> None:
        for bad in (
            {"dormant_reset_ev_comp_exposed": True},
            {"dormant_dial_ev_comp_exposed": True},
            {"exposure_step_or_dormant_reset_ev_drift_events": 1},
        ):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(**bad)
            )
            self.assertFalse(rep.passed, bad)
            self.assertEqual(
                rep.block_code, P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT
            )

    def test_28_pillar54a_slot1_vault_destructive_actions_blocked(self) -> None:
        for action in ("ROTATE_EXIF_ORIENTATION", "AVF_INFO_DB_MUTATE", "FORMAT_QUICK", "FORMAT_FULL", "DELETE_SINGLE"):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                )
            )
            self.assertFalse(rep.passed, action)
            self.assertEqual(rep.block_code, P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_29_pillar54a_persistent_overlay_escape_and_h0_h3_drift_blocked(self) -> None:
        rep_ov = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(overlay_dir="/setting/fx3")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                backup_bin_h3_sha256="a" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_30_pillar54a_invalid_spec_parameters_rejected(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX9"},
            {"fw_version": "9.99"},
            {"shooting_domain": "TimeLapse"},
            {"exposure_mode": "Scene"},
            {"log_shooting_mode": "RawLog"},
            {"exposure_step": "0.1EV"},
            {"cine_ei_base_iso": 1600},
            {"cine_ei_exposure_index_ev": 4.0},
            {"fx6_variable_nd_step": "1/256"},
            {"exposure_std_adjust_ev": 2.0},
        ):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed, bad_kw)
            self.assertEqual(rep.block_code, P304_BLOCKED_INVALID_PILLAR54A_SPEC)

    def test_31_pillar54a_deterministic_sha256_digest(self) -> None:
        spec = build_default_safe_sensor_cleaning_ev_comp_vault_spec()
        r1 = evaluate_sensor_cleaning_ev_comp_vault(spec)
        r2 = evaluate_sensor_cleaning_ev_comp_vault(spec)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        self.assertEqual(len(r1.digest_sha256), 64)

    def test_32_pillar54a_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        res = run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P304_STATUS_VERIFIED_PILLAR_54A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        allow_cnt = sum(1 for s in res.scenarios if s.expected_allowed)
        reject_cnt = sum(1 for s in res.scenarios if not s.expected_allowed)
        self.assertEqual((allow_cnt, reject_cnt), (2, 4))

    def test_33_compute_expected_sensor_cleaning_state_matrix(self) -> None:
        ok, pwr_req, resid, path = compute_expected_sensor_cleaning_state(
            camera_model="ILME-FX3",
            fw_version="7.02",
            battery_pct=51,
            battery_bars=2,
            power_switch_off_after_shake=True,
            lens_removed_before_power_off=False,
        )
        self.assertTrue(ok)
        self.assertTrue(pwr_req)
        self.assertEqual(resid, P304_MANDATORY_POWER_OFF_G_RESID16)
        self.assertEqual(path, "FX3_IBIS_SHAKE_AND_POWER_OFF")

        fx6_ok, fx6_pwr, fx6_resid, fx6_path = compute_expected_sensor_cleaning_state(
            camera_model="ILME-FX6",
            fw_version="6.01",
            battery_pct=100,
            battery_bars=4,
            power_switch_off_after_shake=False,
            lens_removed_before_power_off=False,
        )
        self.assertFalse(fx6_ok)
        self.assertFalse(fx6_pwr)
        self.assertIsNone(fx6_resid)
        self.assertEqual(fx6_path, "Technical > APR")

    def test_34_compute_expected_exposure_comp_state_matrix(self) -> None:
        ev_ok, mn, mx, post_ev, post_step, ei = compute_expected_exposure_comp_state(
            shooting_domain="Movie",
            exposure_mode="M",
            iso_mode="ISO AUTO",
            log_shooting_mode="Cine EI",
            configured_ev_comp=1.3,
            configured_exposure_step="0.5EV",
            reset_action="Camera Settings Reset",
        )
        self.assertFalse(ev_ok)
        self.assertEqual((mn, mx), (-2.0, 2.0))
        self.assertEqual(post_ev, 0.0)
        self.assertEqual(post_step, "0.5EV")
        self.assertTrue(ei)

    def test_35_pillar54a_matrix_states_and_to_dict_keys(self) -> None:
        d = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec()
        ).to_dict()
        self.assertEqual(d["matrix_states_checked"], 16)
        self.assertEqual(d["slot1_vault_mutation_bytes"], 0)
        self.assertTrue(d["slot1_vault_erofs_ebusy_enforced"])
        self.assertTrue(d["slot1_format_hard_locked"])

    def test_36_pillar54a_non_volatile_dev_paths_rejected_as_overlay(self) -> None:
        for bad_ov in ("/setting", "p2:/setting", "/dev/nflasha", "/dev/mmcblk0/p2"):
            rep = evaluate_sensor_cleaning_ev_comp_vault(
                build_default_safe_sensor_cleaning_ev_comp_vault_spec(overlay_dir=bad_ov)
            )
            self.assertFalse(rep.passed, bad_ov)
            self.assertEqual(rep.block_code, P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_37_pillar54a_run_tmpfs_overlay_allowed(self) -> None:
        rep = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                overlay_dir="/run/fx3_stageb_p304_test"
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_38_pillar54a_reset_network_set_preserves_ev_comp_and_exposure_step(self) -> None:
        rep = evaluate_sensor_cleaning_ev_comp_vault(
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                requested_ev_comp_ev=-2.3,
                exposure_step="0.5EV",
                reset_action="Reset Network Set.",
                post_reset_ev_comp_ev=-2.3,
                post_reset_exposure_step="0.5EV",
            )
        )
        self.assertTrue(rep.passed, rep.errors)


class TestPhase304Pillar54BFocusModePlaybackRotateVault(unittest.TestCase):
    """Tests 39-64: Pillar 54B (Focus Mode 5-Still/2-Movie Clamp & Playback Rotate Slot-1 Vault)."""

    def test_39_default_safe_54b_spec_passes(self) -> None:
        rep = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P304_STATUS_VERIFIED_PILLAR_54B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.focus_mode_5still_2movie_clamp_verified)
        self.assertTrue(rep.priority_set_init_and_illuminator_gate_verified)
        self.assertTrue(rep.playback_view_9_25_index_group_rotation_verified)
        self.assertTrue(rep.slot1_rotate_exif_erofs_ebusy_firewall_verified)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_rotate_exif_mutation_bytes, 0)

    def test_40_focus_mode_all_5_still_modes_pass(self) -> None:
        self.assertEqual(P304_STILL_FOCUS_MODES, ("AF-S", "AF-A", "AF-C", "DMF", "MF"))
        for fmode in P304_STILL_FOCUS_MODES:
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(
                    shooting_domain="Still",
                    requested_focus_mode=fmode,
                    reported_focus_mode_allowed=True,
                    movie_clamp_errno=None,
                    reported_af_illuminator_active=(fmode != "AF-C"),
                )
            )
            self.assertTrue(rep.passed, f"{fmode}: {rep.errors}")

    def test_41_focus_mode_movie_and_sq_strictly_allow_only_af_c_and_mf(self) -> None:
        self.assertEqual(P304_MOVIE_SQ_FOCUS_MODES, ("AF-C", "MF"))
        for domain in ("Movie", "S&Q"):
            for fmode in P304_MOVIE_SQ_FOCUS_MODES:
                rep = evaluate_focus_mode_playback_rotate_vault(
                    build_default_safe_focus_mode_playback_rotate_vault_spec(
                        shooting_domain=domain,
                        requested_focus_mode=fmode,
                        reported_focus_mode_allowed=True,
                        movie_clamp_errno=None,
                        reported_af_illuminator_active=False,
                    )
                )
                self.assertTrue(rep.passed, f"{domain}/{fmode}: {rep.errors}")

    def test_42_focus_mode_movie_and_sq_clamp_af_s_af_a_dmf_eopnotsupp_95(self) -> None:
        self.assertEqual(P304_MOVIE_SQ_LOCKED_OUT_FOCUS_MODES, ("AF-S", "AF-A", "DMF"))
        for domain in ("Movie", "S&Q"):
            for fmode in P304_MOVIE_SQ_LOCKED_OUT_FOCUS_MODES:
                allowed, errno_no, _, _, illum_active, _ = compute_expected_focus_mode_state(
                    shooting_domain=domain,
                    requested_focus_mode=fmode,
                    configured_priority_afs="Balanced Emphasis",
                    configured_priority_afc="Balanced Emphasis",
                    configured_af_illuminator="Auto",
                    reset_action="None",
                )
                self.assertFalse(allowed, f"{domain}/{fmode}")
                self.assertEqual(errno_no, 95)
                self.assertFalse(illum_active)

                rep = evaluate_focus_mode_playback_rotate_vault(
                    build_default_safe_focus_mode_playback_rotate_vault_spec(
                        shooting_domain=domain,
                        requested_focus_mode=fmode,
                        reported_focus_mode_allowed=True,
                        movie_clamp_errno=None,
                        reported_af_illuminator_active=False,
                    )
                )
                self.assertFalse(rep.passed, f"{domain}/{fmode}")
                self.assertEqual(
                    rep.block_code, P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT
                )

    def test_43_dormant_focus_modes_pf_and_semi_manual_rejected_einval_22(self) -> None:
        for dormant in P304_DORMANT_FOCUS_MODES:
            for domain in ("Still", "Movie", "S&Q"):
                allowed, errno_no, _, _, _, _ = compute_expected_focus_mode_state(
                    shooting_domain=domain,
                    requested_focus_mode=dormant,
                    configured_priority_afs="Balanced Emphasis",
                    configured_priority_afc="Balanced Emphasis",
                    configured_af_illuminator="Auto",
                    reset_action="None",
                )
                self.assertFalse(allowed)
                self.assertEqual(errno_no, 22)

                rep = evaluate_focus_mode_playback_rotate_vault(
                    build_default_safe_focus_mode_playback_rotate_vault_spec(
                        shooting_domain=domain,
                        requested_focus_mode=dormant,
                        reported_focus_mode_allowed=False,
                        movie_clamp_errno=22,
                        reported_af_illuminator_active=(domain == "Still"),
                    )
                )
                self.assertFalse(rep.passed, f"{domain}/{dormant}")
                self.assertEqual(
                    rep.block_code, P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT
                )

    def test_44_priority_set_afs_afc_survives_camera_reset_and_resets_only_on_initialize(
        self,
    ) -> None:
        rep_survive = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Still",
                requested_focus_mode="AF-S",
                configured_priority_afs="AF",
                configured_priority_afc="Release",
                configured_af_illuminator="Off",
                reported_af_illuminator_active=True,
                reset_action="Camera Settings Reset",
                post_priority_afs="AF",
                post_priority_afc="Release",
                post_af_illuminator="Auto",
            )
        )
        self.assertTrue(rep_survive.passed, rep_survive.errors)

        rep_init = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Still",
                requested_focus_mode="AF-S",
                configured_priority_afs="AF",
                configured_priority_afc="Release",
                configured_af_illuminator="Off",
                reported_af_illuminator_active=True,
                reset_action="Initialize",
                post_priority_afs="Balanced Emphasis",
                post_priority_afc="Balanced Emphasis",
                post_af_illuminator="Auto",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_45_priority_set_wipe_or_movie_af_illuminator_fire_rejected(self) -> None:
        rep_wipe = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Still",
                requested_focus_mode="AF-S",
                configured_priority_afs="AF",
                reported_af_illuminator_active=True,
                reset_action="Camera Settings Reset",
                post_priority_afs="Balanced Emphasis",
                post_af_illuminator="Auto",
            )
        )
        self.assertFalse(rep_wipe.passed)
        self.assertEqual(rep_wipe.block_code, P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT)

        for domain in ("Movie", "S&Q"):
            rep_mv_illum = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(
                    shooting_domain=domain,
                    requested_focus_mode="AF-C",
                    reported_af_illuminator_active=True,
                )
            )
            self.assertFalse(rep_mv_illum.passed, domain)
            self.assertEqual(
                rep_mv_illum.block_code, P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT
            )

    def test_46_playback_all_5_view_modes_and_exact_9_25_image_index_pass(self) -> None:
        self.assertEqual(P304_IMAGE_INDEX_MODES, ("9 Images", "25 Images"))
        for vmode in P304_VIEW_MODE_SUPPORTED:
            for idx in P304_IMAGE_INDEX_MODES:
                rep = evaluate_focus_mode_playback_rotate_vault(
                    build_default_safe_focus_mode_playback_rotate_vault_spec(
                        view_mode=vmode,
                        image_index=idx,
                        post_view_mode=vmode,
                        post_image_index=idx,
                    )
                )
                self.assertTrue(rep.passed, f"{vmode}/{idx}: {rep.errors}")

    def test_47_playback_dormant_12_30_image_index_rejected(self) -> None:
        self.assertEqual(
            P304_DORMANT_IMAGE_INDEX_MODES,
            ("12 Images", "30 Images", "12_IMAGES", "30_IMAGES"),
        )
        for bad_idx in P304_DORMANT_IMAGE_INDEX_MODES:
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(
                    image_index=bad_idx,
                    post_image_index=bad_idx,
                )
            )
            self.assertFalse(rep.passed, bad_idx)
            self.assertEqual(
                rep.block_code, P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT
            )

    def test_48_playback_display_group_and_display_rotation_modes_pass(self) -> None:
        for grp in ("Off", "On"):
            for rot in ("Auto", "Manual", "Off"):
                rep = evaluate_focus_mode_playback_rotate_vault(
                    build_default_safe_focus_mode_playback_rotate_vault_spec(
                        display_as_group=grp,
                        display_rotation=rot,
                        post_display_as_group=grp,
                        post_display_rotation=rot,
                    )
                )
                self.assertTrue(rep.passed, f"{grp}/{rot}: {rep.errors}")

    def test_49_playback_settings_survive_camera_reset_and_clear_on_initialize(self) -> None:
        rep_cam = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                view_mode="Folder View(Still)",
                image_index="25 Images",
                display_as_group="On",
                display_rotation="Manual",
                reset_action="Camera Settings Reset",
                post_view_mode="Folder View(Still)",
                post_image_index="25 Images",
                post_display_as_group="On",
                post_display_rotation="Manual",
                reported_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_cam.passed, rep_cam.errors)

        rep_init = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                view_mode="Folder View(Still)",
                image_index="25 Images",
                display_as_group="On",
                display_rotation="Manual",
                reset_action="Initialize",
                post_view_mode="Date View",
                post_image_index="9 Images",
                post_display_as_group="Off",
                post_display_rotation="Auto",
                reported_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_50_playback_fx6_still_image_index_or_exif_rotate_conflation_rejected(self) -> None:
        rep = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                fx6_exposes_still_image_index_or_exif_rotate=True,
                image_index_dormant_or_view_mode_drift_events=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT)

    def test_51_slot1_tier0_vault_blocks_playback_rotate_exif_and_avf_info_erofs(self) -> None:
        for action in ("ROTATE_EXIF_ORIENTATION", "AVF_INFO_DB_MUTATE", "FORMAT_QUICK", "FORMAT_FULL", "DELETE_SINGLE"):
            _, rot_ok, fw_errno, _, _, _, _ = compute_expected_playback_rotate_state(
                view_mode="Date View",
                image_index="9 Images",
                display_as_group="Off",
                display_rotation="Auto",
                playback_slot=1,
                slot1_holds_tier0_vault=True,
                requested_action=action,
                background_transfer_active=False,
                reset_action="None",
            )
            self.assertFalse(rot_ok, action)
            if action in ("ROTATE_EXIF_ORIENTATION", "AVF_INFO_DB_MUTATE"):
                self.assertEqual(fw_errno, "EROFS")

            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(
                    select_playback_media_slot=1,
                    slot1_holds_tier0_vault=True,
                    requested_vault_action=action,
                    reported_rotate_allowed=True,
                    rotate_firewall_errno=None,
                    slot1_data_sector_writes=1,
                    slot1_rotate_exif_mutation_bytes=512,
                    slot1_vault_mutation_bytes=512,
                )
            )
            self.assertFalse(rep.passed, action)
            self.assertEqual(rep.block_code, P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_52_slot1_readonly_playback_browse_with_erofs_blocked_rotate_is_allowed(self) -> None:
        for action in ("READ_ONLY_AUDIT", "VIEW_MODE_BROWSE", "IMAGE_INDEX_BROWSE"):
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(
                    select_playback_media_slot=1,
                    slot1_holds_tier0_vault=True,
                    requested_vault_action=action,
                    reported_rotate_allowed=False,
                    rotate_firewall_errno=None,
                    slot1_data_sector_writes=0,
                    slot1_rotate_exif_mutation_bytes=0,
                    slot1_vault_mutation_bytes=0,
                )
            )
            self.assertTrue(rep.passed, f"{action}: {rep.errors}")

    def test_53_slot2_playback_rotate_allowed_when_idle_and_ebusy_during_bg_transfer(self) -> None:
        rep_s2_idle = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                select_playback_media_slot=2,
                slot1_holds_tier0_vault=True,
                requested_vault_action="ROTATE_EXIF_ORIENTATION",
                background_transfer_active=False,
                reported_rotate_allowed=True,
                rotate_firewall_errno=None,
                slot1_data_sector_writes=0,
                slot1_rotate_exif_mutation_bytes=0,
            )
        )
        self.assertTrue(rep_s2_idle.passed, rep_s2_idle.errors)

        _, bg_rot_ok, bg_errno, _, _, _, _ = compute_expected_playback_rotate_state(
            view_mode="Date View",
            image_index="9 Images",
            display_as_group="Off",
            display_rotation="Auto",
            playback_slot=2,
            slot1_holds_tier0_vault=True,
            requested_action="ROTATE_EXIF_ORIENTATION",
            background_transfer_active=True,
            reset_action="None",
        )
        self.assertFalse(bg_rot_ok)
        self.assertEqual(bg_errno, "EBUSY")

        rep_s2_bg_spoof = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                select_playback_media_slot=2,
                requested_vault_action="ROTATE_EXIF_ORIENTATION",
                background_transfer_active=True,
                reported_rotate_allowed=True,
                rotate_firewall_errno=None,
            )
        )
        self.assertFalse(rep_s2_bg_spoof.passed)
        self.assertEqual(rep_s2_bg_spoof.block_code, P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_54_pillar54b_slot1_nonzero_sector_or_exif_bytes_fail_firewall(self) -> None:
        for bad in (
            {"slot1_data_sector_writes": 1},
            {"slot1_rotate_exif_mutation_bytes": 128},
            {"slot1_vault_mutation_bytes": 4096},
            {"slot1_vault_erofs_ebusy_enforced": False},
            {"slot1_format_hard_locked": False},
        ):
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(**bad)
            )
            self.assertFalse(rep.passed, bad)
            self.assertEqual(rep.block_code, P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_55_pillar54b_persistent_overlay_escape_rejected(self) -> None:
        for bad_ov in ("/setting/54b", "p2:/setting", "/dev/mmcblk0", "/var/tmp/persist"):
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(overlay_dir=bad_ov)
            )
            self.assertFalse(rep.passed, bad_ov)
            self.assertEqual(rep.block_code, P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_56_pillar54b_tier0_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_57_pillar54b_invalid_spec_parameters_rejected(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX6"},
            {"shooting_domain": "Burst"},
            {"configured_priority_afs": "Instant"},
            {"configured_priority_afc": "Instant"},
            {"configured_af_illuminator": "Strobe"},
            {"display_as_group": "Always"},
            {"display_rotation": "Flip180"},
            {"reset_action": "WipeAll"},
            {"requested_vault_action": "FLASH_BOOT"},
        ):
            rep = evaluate_focus_mode_playback_rotate_vault(
                build_default_safe_focus_mode_playback_rotate_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed, bad_kw)
            self.assertEqual(rep.block_code, P304_BLOCKED_INVALID_PILLAR54B_SPEC)

    def test_58_pillar54b_af_assist_enabled_with_movie_af_c_safe_pass(self) -> None:
        rep = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Movie",
                requested_focus_mode="AF-C",
                af_assist_enabled=True,
                reported_af_illuminator_active=False,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_59_pillar54b_deterministic_sha256_digest(self) -> None:
        spec = build_default_safe_focus_mode_playback_rotate_vault_spec()
        r1 = evaluate_focus_mode_playback_rotate_vault(spec)
        r2 = evaluate_focus_mode_playback_rotate_vault(spec)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        self.assertEqual(len(r1.digest_sha256), 64)

    def test_60_pillar54b_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        res = run_pillar54b_focus_mode_playback_rotate_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P304_STATUS_VERIFIED_PILLAR_54B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        allow_cnt = sum(1 for s in res.scenarios if s.expected_allowed)
        reject_cnt = sum(1 for s in res.scenarios if not s.expected_allowed)
        self.assertEqual((allow_cnt, reject_cnt), (2, 4))

    def test_61_compute_expected_playback_rotate_state_initialize_resets_fields(self) -> None:
        ok, rot_ok, errno_s, vw, idx, grp, rot = compute_expected_playback_rotate_state(
            view_mode="XAVC S View",
            image_index="25 Images",
            display_as_group="On",
            display_rotation="Off",
            playback_slot=1,
            slot1_holds_tier0_vault=True,
            requested_action="AVF_INFO_DB_MUTATE",
            background_transfer_active=False,
            reset_action="Initialize",
        )
        self.assertTrue(ok)
        self.assertFalse(rot_ok)
        self.assertEqual(errno_s, "EROFS")
        self.assertEqual((vw, idx, grp, rot), ("Date View", "9 Images", "Off", "Auto"))

    def test_62_compute_expected_focus_mode_state_still_afc_disables_af_illuminator(self) -> None:
        ok, err, pafs, pafc, illum, post_i = compute_expected_focus_mode_state(
            shooting_domain="Still",
            requested_focus_mode="AF-C",
            configured_priority_afs="AF",
            configured_priority_afc="Release",
            configured_af_illuminator="Off",
            reset_action="None",
        )
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual((pafs, pafc), ("AF", "Release"))
        self.assertFalse(illum)
        self.assertEqual(post_i, "Off")

    def test_63_pillar54b_matrix_states_and_to_dict_zero_device_writes(self) -> None:
        d = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec()
        ).to_dict()
        self.assertEqual(d["matrix_states_checked"], 16)
        self.assertEqual(d["physical_device_writes"], 0)
        self.assertFalse(d["persistent_emmc_writes_authorized"])
        self.assertEqual(d["slot1_data_sector_writes"], 0)
        self.assertEqual(d["slot1_rotate_exif_mutation_bytes"], 0)

    def test_64_pillar54b_post_reset_drift_without_negative_counter_still_blocks(self) -> None:
        rep = evaluate_focus_mode_playback_rotate_vault(
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                view_mode="XAVC S View",
                reset_action="Camera Settings Reset",
                post_view_mode="Date View",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT)


class TestPhase304Master54Of54AndCli(unittest.TestCase):
    """Tests 65-84: Combined verifier, Standalone Pillar 54, 54/54 Recovery Master, and CLI."""

    def test_65_combined_verifier_default_and_symmetry_alias_pass(self) -> None:
        rep1 = verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault(force_clean_room=True)
        rep2 = verify_sensor_cleaning_ev_comp_focus_mode_rotate_vault(force_clean_room=True)
        self.assertTrue(rep1.all_passed)
        self.assertTrue(rep1.passed)
        self.assertEqual(rep1.status, P304_STATUS_VERIFIED_PILLAR54_SUITE)
        self.assertEqual(rep1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep2.status, rep1.status)
        self.assertFalse(rep1.overall_ready_for_hardware_attach)
        self.assertFalse(rep1.cross_model_flash_authorized)
        self.assertEqual(rep1.raw_firmware_bytes_leaked, 0)

    def test_66_combined_verifier_propagates_54a_and_54b_spec_failures(self) -> None:
        bad_54a = build_default_safe_sensor_cleaning_ev_comp_vault_spec(battery_pct=15)
        rep_a = verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault(
            force_clean_room=True, spec_54a=bad_54a
        )
        self.assertFalse(rep_a.all_passed)
        self.assertFalse(rep_a.sensor_cleaning_ev_comp_report.passed)

        bad_54b = build_default_safe_focus_mode_playback_rotate_vault_spec(
            select_playback_media_slot=1,
            requested_vault_action="ROTATE_EXIF_ORIENTATION",
        )
        rep_b = verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault(
            force_clean_room=True, spec_54b=bad_54b
        )
        self.assertFalse(rep_b.all_passed)
        self.assertFalse(rep_b.focus_mode_playback_rotate_report.passed)

    def test_67_combined_verifier_donor_failure_propagates_to_errors(self) -> None:
        bad_snap = inspect_phase304_donors_readonly(force_clean_room=True)
        bad_snap = p304.Phase304DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=False,
            donor_files_inspected=0,
            elapsed_seconds=0.01,
            under_0_20s_budget=True,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=bad_snap.artifacts,
        )
        with mock.patch.object(p304, "inspect_phase304_donors_readonly", return_value=bad_snap):
            rep = verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault()
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("donor artifact parity" in e for e in rep.errors))

    def test_68_standalone_pillar54_suite_passes_default_mode(self) -> None:
        rep = run_pillar54_standalone_suite()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P304_STATUS_VERIFIED_PILLAR54_SUITE)
        self.assertEqual(rep.pillar_54a_sensor_cleaning_ev_comp_vault.scenarios_passed, 6)
        self.assertEqual(rep.pillar_54b_focus_mode_playback_rotate_vault.scenarios_passed, 6)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_rotate_exif_mutation_bytes, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertLess(rep.elapsed_seconds, P304_FAST_CLI_BUDGET_SECONDS + _ci_headroom())

    def test_69_standalone_pillar54_suite_clean_room_deterministic_sha256(self) -> None:
        r1 = run_pillar54_standalone_suite(force_clean_room=True)
        r2 = run_pillar54_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(len(r1.suite_sha256), 64)

    def test_70_standalone_pillar54_suite_propagates_54a_failure(self) -> None:
        bad_res = p304.Pillar54ASuiteResult(
            passed=False, status="FAIL", scenarios_passed=5, scenarios_total=6, scenarios=()
        )
        with mock.patch.object(
            p304, "run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite", return_value=bad_res
        ):
            rep = run_pillar54_standalone_suite(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.sensor_cleaning_low_battery_bypass_events, 1)

    def test_71_standalone_pillar54_suite_propagates_donor_budget_failure(self) -> None:
        base_snap = inspect_phase304_donors_readonly(force_clean_room=True)
        slow_snap = p304.Phase304DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=17,
            elapsed_seconds=9.9,
            under_0_20s_budget=False,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=base_snap.artifacts,
        )
        with mock.patch.object(p304, "inspect_phase304_donors_readonly", return_value=slow_snap):
            rep = run_pillar54_standalone_suite()
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("budget" in e for e in rep.errors))

    def test_72_master_54_of_54_passes_in_clean_room_under_fast_budget(self) -> None:
        rep = evaluate_realhw_54pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P304_STATUS_VERIFIED_54OF54_AGGREGATOR)
        self.assertGreaterEqual(rep.pillar_count, 54)
        self.assertGreaterEqual(rep.pillars_passed, 54)
        self.assertEqual(rep.pillar_count, 54)
        self.assertEqual(rep.pillars_passed, 54)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertLess(rep.elapsed_seconds, P304_FAST_CLI_BUDGET_SECONDS + _ci_headroom())
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_73_master_54_of_54_passes_default_mode_and_aliases_match(self) -> None:
        rep = evaluate_realhw_54pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertGreaterEqual(rep.pillar_count, 54)
        self.assertGreaterEqual(rep.pillars_passed, 54)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_rotate_exif_mutation_bytes, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.fx3_has_sensor_cleaning_ibis)
        self.assertTrue(rep.fx3_has_exposure_comp)
        self.assertFalse(rep.fx3_has_physical_ev_reset_dial)
        self.assertFalse(rep.fx6_has_ultrasonic_ibis_cleaning)
        self.assertTrue(rep.fx6_has_variable_end_optical_block)
        self.assertTrue(rep.fx6_has_technical_apr)
        self.assertFalse(rep.fx6_has_still_exposure_comp)
        self.assertFalse(rep.fx6_has_still_image_index_rotate)

        alias1 = evaluate_54pillar_recovery_master(force_clean_room=True)
        alias2 = verify_54pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(alias1.pillar_count, 54)
        self.assertEqual(alias2.pillar_count, 54)
        self.assertEqual(alias1.master_54pillar_sha256, alias2.master_54pillar_sha256)

    def test_74_master_54_inherits_53_pillars_plus_pillar_54_lineage(self) -> None:
        m53 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        m54 = evaluate_realhw_54pillar_recovery_master(force_clean_room=True)
        self.assertGreaterEqual(m54.pillar_count, 54)
        self.assertEqual(m54.pillar_count, m53.pillar_count + 1)
        self.assertEqual(
            [p.pillar_id for p in m54.pillars[:53]],
            [p.pillar_id for p in m53.pillars],
        )
        self.assertEqual(
            m54.pillars[53].pillar_id,
            "pillar_54_sensor_cleaning_ev_comp_focus_mode_rotate_vault",
        )
        self.assertEqual(m54.pillars[53].phase_label, "Phase 304 (Wave-52)")

    def test_75_master_54_fault_injection_on_pillar_54_and_pillar_1_fails_closed(self) -> None:
        rep54 = evaluate_realhw_54pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_54_sensor_cleaning_ev_comp_focus_mode_rotate_vault",
        )
        self.assertFalse(rep54.all_passed)
        self.assertEqual(rep54.pillars_passed, 53)
        self.assertEqual(
            rep54.failed_pillars,
            ("pillar_54_sensor_cleaning_ev_comp_focus_mode_rotate_vault",),
        )
        self.assertFalse(rep54.overall_ready_for_hardware_attach)

        rep1 = evaluate_realhw_54pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_54_PILLAR_IDS[0],
        )
        self.assertFalse(rep1.all_passed)
        self.assertEqual(rep1.pillars_passed, 53)
        self.assertEqual(rep1.failed_pillars, (MASTER_54_PILLAR_IDS[0],))

    def test_76_master_54_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_54pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_77_master_54_milestone_295_negative_safety_bool_audit(self) -> None:
        d = evaluate_realhw_54pillar_recovery_master(force_clean_room=True).to_dict()
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
            "fx3_has_physical_ev_reset_dial",
            "fx6_has_ultrasonic_ibis_cleaning",
            "fx6_has_still_exposure_comp",
            "fx6_has_still_image_index_rotate",
        )
        for key in negative_keys:
            self.assertFalse(d[key], f"Expected False for {key}")
        self.assertTrue(d["cnflasha_userspace_write_blocked"])
        self.assertTrue(d["slot1_format_hard_locked"])
        self.assertTrue(d["slot1_vault_erofs_ebusy_enforced"])
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(d["physical_device_writes"], 0)

    def test_78_master_54_detects_cross_model_flash_tamper(self) -> None:
        m53 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        p54 = run_pillar54_standalone_suite(force_clean_room=True)
        bad_p54 = p304.Pillar54StandaloneReport(
            **{**p54.__dict__, "cross_model_flash_authorized": True}
        )
        with mock.patch.object(
            p304, "evaluate_realhw_53pillar_recovery_master", return_value=m53
        ), mock.patch.object(p304, "run_pillar54_standalone_suite", return_value=bad_p54):
            rep = evaluate_realhw_54pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("cross_model_flash_authorized" in e for e in rep.errors))

    def test_79_cli_inprocess_help_and_pillar54_json(self) -> None:
        buf_help = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "--help"]):
            with self.assertRaises(SystemExit) as ctx, redirect_stdout(buf_help):
                cli_main.main()
        self.assertEqual(ctx.exception.code, 0)
        help_txt = buf_help.getvalue()
        self.assertIn("verify-54pillar-recovery", help_txt)
        self.assertIn("verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault", help_txt)
        self.assertIn(">= 51%", help_txt)

        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault",
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

    def test_80_cli_inprocess_verify_54pillar_recovery_json_and_out_file(self) -> None:
        import shutil

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p304_m54_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-54pillar-recovery",
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
            report_file = out_dir / "54pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            file_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(payload, file_payload)
            self.assertTrue(payload["all_passed"])
            self.assertGreaterEqual(payload["pillar_count"], 54)
            self.assertGreaterEqual(payload["pillars_passed"], 54)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_81_cli_inprocess_human_readable_summary_exits_zero(self) -> None:
        buf54 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault",
                "--force-clean-room",
            ],
        ):
            with redirect_stdout(buf54):
                rc54 = cli_main.main()
        self.assertEqual(rc54, 0)
        self.assertIn("pillar_54a=6/6 pillar_54b=6/6", buf54.getvalue())

        bufm = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-54pillar-recovery", "--force-clean-room"],
        ):
            with redirect_stdout(bufm):
                rcm = cli_main.main()
        self.assertEqual(rcm, 0)
        self.assertIn("pillars=54/54", bufm.getvalue())

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
        self.assertIn("verify-54pillar-recovery", proc.stdout)

    def test_83_cli_subprocess_verify_54pillar_recovery_clean_room_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-54pillar-recovery",
                "--force-clean-room",
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
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertGreaterEqual(data["pillar_count"], 54)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(data["overall_ready_for_hardware_attach"])
        self.assertFalse(data["cross_model_flash_authorized"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)
        self.assertLess(data["elapsed_seconds"], P304_FAST_CLI_BUDGET_SECONDS + _ci_headroom())

    def test_84_cli_subprocess_verify_54pillar_recovery_default_donor_or_clean(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-54pillar-recovery",
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
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertGreaterEqual(data["pillar_count"], 54)
        self.assertGreaterEqual(data["pillars_passed"], 54)
        self.assertIn(data["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(data["slot1_data_sector_writes"], 0)
        self.assertEqual(data["slot1_rotate_exif_mutation_bytes"], 0)
        self.assertLess(data["elapsed_seconds"], P304_FAST_CLI_BUDGET_SECONDS + _ci_headroom())


if __name__ == "__main__":
    unittest.main()
