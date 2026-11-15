"""Fast dual-mode unit tests for Phase 199 — Real-Hardware Main Track Part 22:
Gate G69 (`ILME-FX3` `Ver. 7.02` Exact 4-Mode `[Fan Control]` `Auto` / `Minimum` /
`Off in Rec` / `Always Off` — Rejecting Non-FX3 `Auto1`/`Auto2` Tokens, Modeling
`Off in Rec` `0%` Recording PWM + Thermal Emergency Override & `100% MAX PWM`
Standby Active Purge, and Blocking Pre-Backup / High-Load Rehearsal When
`[Fan Control] == Always Off` with `[Auto Power OFF Temp.] = Standard / High`
`CXD90057 / CXD90058` Protection),
Gate G70 (`FX6 Ver. 6.01` `<= 6.01` Legacy LUT Slot Format vs `Stock FX3 Ver. 7.00/7.02`
`7.00+` Optimized `p2:/setting` `User1..User16` LUT Binary Format Split Firewall
Requiring Volatile `/tmp/fx6_lut_overlay` Redirection with `H0 == H3` Invariance,
plus Independent `[Shutter Mode]` `Speed` vs `Angle` `Backup.bin` Slot Storage &
`5.6°..64F` Normal vs `5.6°..360°` `119.88p/100p` / `S&Q` Angle Bounds Immune to
`0.3EV / 0.5EV` Exposure Step),
and 70-Gate Master Preflight (`G01..G70` / `verify-70-gates` / `run_70_gate_preflight`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Dict, Tuple
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
    evaluate_58gate_preflight,
)
from fx3_safety.realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
    STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
    evaluate_60gate_preflight,
)
from fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    STATUS_BLOCKED_G61_LENS_ID_BREATHING_02CF0232_UNSUPPORTED,
    STATUS_BLOCKED_G62_FX6_12GSDI_MMIO_PROBE_UNMASKED,
    evaluate_62gate_preflight,
)
from fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE,
    STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE,
    evaluate_64gate_preflight,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    STATUS_BLOCKED_G65_UVC_UAC_GADGET_FORBIDDEN,
    STATUS_BLOCKED_G66_MEDIA_LUT_PATH_ASYMMETRY_OR_P2_WRITE,
    evaluate_66gate_preflight,
)
from fx3_safety.realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE,
    STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR,
    evaluate_68gate_preflight,
)
from fx3_safety.realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard import (
    ALLOWED_AUTO_POWER_OFF_TEMP_MODES,
    ALLOWED_EXPOSURE_STEPS_EV,
    ALLOWED_G69_BODY_MODELS,
    ALLOWED_PREBACKUP_CONTEXTS,
    ALLOWED_SHOOTING_MODES_G70,
    ALLOWED_SHUTTER_MODES,
    AUTO_MODE_BASE_PWM_PCT,
    AUTO_POWER_OFF_HIGH_MAX_TEMP_C,
    AUTO_POWER_OFF_STANDARD_MAX_TEMP_C,
    CXD90057_CXD90058_CRITICAL_SHUTDOWN_TEMP_C,
    CXD90057_PRIMARY_SOC,
    CXD90058_COMPANION_SOC,
    DEFAULT_H0_P2_SETTING_SHA256,
    DEFAULT_SHUTTER_ANGLE_BK4_SLOT_ID,
    DEFAULT_SHUTTER_SPEED_BK4_SLOT_ID,
    DONOR_FX6_FW_VERSION,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FORBIDDEN_PERSISTENT_LUT_SETTING_PATHS,
    FX3_DEFAULT_FW_VERSION_G69,
    FX3_EXACT_4_FAN_MENU_LABELS,
    FX3_EXACT_4_FAN_MODES,
    FX3_FAN_CONTROL_MENU_PATH,
    FX3_FAN_MIN_FW_VERSION,
    FX3_FAN_MODE_ALWAYS_OFF,
    FX3_FAN_MODE_AUTO,
    FX3_FAN_MODE_MINIMUM,
    FX3_FAN_MODE_OFF_IN_REC,
    G69,
    G69_GATE_CODE,
    G69_GATE_ID,
    G70,
    G70_GATE_CODE,
    G70_GATE_ID,
    GATE_G69_FX3_4MODE_FAN_PWM_AND_PREBACKUP_THERMAL_GUARD,
    GATE_G70_LUT_601_702_BINARY_SPLIT_AND_SHUTTER_SPEED_ANGLE_GUARD,
    HIGH_FPS_ANGLE_CLAMP_RATES,
    HOST_STOCK_FX3_FW_VERSION,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LUT_BINARY_SPLIT_BOUNDARY_FW,
    LUT_SLOT_FORMAT_LEGACY_LE_601,
    LUT_SLOT_FORMAT_OPTIMIZED_GE_700,
    MINIMUM_MODE_QUIET_PWM_PCT,
    MIN_SHUTTER_ANGLE_FW_VERSION,
    OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C,
    OFF_IN_REC_RECORDING_NORMAL_PWM_PCT,
    OFF_IN_REC_STANDBY_MAX_PWM_PCT,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE199_DONOR_SPECS,
    PREBACKUP_SOC_MAX_START_TEMP_C,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_SCHEMA,
    REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_VERSION,
    REJECTED_NON_FX3_FAN_MODES,
    REQUIRED_VOLATILE_LUT_OVERLAY_DIR,
    SHUTTER_ANGLE_MAX_FRAMES_NORMAL,
    SHUTTER_ANGLE_MIN_DEG,
    SHUTTER_ANGLE_NORMAL_MAX_EQUIV_DEG,
    SHUTTER_ANGLE_STD_MAX_DEG,
    SPI_NOR_WRITE_AUTHORIZED,
    STANDARD_MOVIE_FRAME_RATES,
    STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED,
    STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT,
    STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2,
    STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION,
    STATUS_BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO,
    STATUS_BLOCKED_G69_TELEMETRY_INVALID,
    STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT,
    STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS,
    STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION,
    STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE,
    STATUS_BLOCKED_G70_TELEMETRY_INVALID,
    STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G69,
    STATUS_VERIFIED_G70,
    STATUS_VERIFIED_SAFE,
    USER_LUT_SLOT_MAX,
    USER_LUT_SLOT_MIN,
    VALID_USER_LUT_SLOTS,
    Master70GateReport,
    audit_phase199_donor_contracts,
    classify_user_lut_slot_binary_format,
    compute_fx3_702_fan_pwm_duty_pct,
    evaluate_70_master_safety_gates,
    evaluate_70gate_preflight,
    evaluate_g69_fan_pwm_thermal_guard,
    evaluate_g70_lut_split_shutter_angle_guard,
    main as module_cli_main,
    run_70_gate_preflight,
    validate_fx3_4mode_fan_enum_and_off_in_rec_pwm,
    validate_independent_shutter_speed_angle_bounds,
    validate_lut_601_vs_702_p2_setting_split_firewall,
    validate_prebackup_fan_and_auto_power_off_temp,
    verify_fx3_4mode_fan_pwm_and_prebackup_guard,
    verify_lut_601_702_split_and_shutter_angle_guard,
)


def _create_synthetic_donor_tree(
    base: Path,
    *,
    corrupt_fan: bool = False,
) -> Tuple[Path, Dict[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]]:
    patched_specs: Dict[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {}
    for key, (body, rel_path, exp_size, _sha, markers, lbl) in PINNED_PHASE199_DONOR_SPECS.items():
        p = base / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray(exp_size)
        cursor = 0
        for tok in markers:
            if corrupt_fan and key == "fx3_libfan_so" and tok == b"fan":
                tok = b"COR"
            payload[cursor : cursor + len(tok)] = tok
            cursor += len(tok) + 16
        raw = bytes(payload)
        p.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        patched_specs[key] = (body, rel_path, exp_size, sha, markers, lbl)
    return base, patched_specs


class Phase199FanPwmShutterAngleLutSplit70GateGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_dry_68 = evaluate_68gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        t0 = time.monotonic()
        cls.default_dry_70 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        cls.default_dry_elapsed = time.monotonic() - t0

    # --- 1. Hard-Locked Safety Redlines & Public Package Exports ---

    def test_01_hard_locked_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(G69, GATE_G69_FX3_4MODE_FAN_PWM_AND_PREBACKUP_THERMAL_GUARD)
        self.assertEqual(
            G70, GATE_G70_LUT_601_702_BINARY_SPLIT_AND_SHUTTER_SPEED_ANGLE_GUARD
        )
        self.assertIs(run_70_gate_preflight, evaluate_70gate_preflight)
        self.assertIs(evaluate_70_master_safety_gates, evaluate_70gate_preflight)
        for name in (
            "G69",
            "G70",
            "Master70GateReport",
            "run_70_gate_preflight",
            "evaluate_70gate_preflight",
            "evaluate_70_master_safety_gates",
            "evaluate_g69_fan_pwm_thermal_guard",
            "evaluate_g70_lut_split_shutter_angle_guard",
            "realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, name), f"missing fx3_safety.{name}")
            self.assertIn(name, fx3_safety.__all__)

    def test_02_schema_version_and_wave25_phase199_constants(self) -> None:
        self.assertEqual(
            REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_SCHEMA,
            "fx3-realhw-fan-pwm-shutter-angle-lut-split-70gate-preflight-v1",
        )
        self.assertEqual(REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_VERSION, "1.0.0")
        self.assertEqual(
            FX3_EXACT_4_FAN_MENU_LABELS,
            ("Auto", "Minimum", "Off in Rec", "Always Off"),
        )
        self.assertEqual(
            FX3_EXACT_4_FAN_MODES,
            ("AUTO", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF"),
        )
        self.assertIn("AUTO1", REJECTED_NON_FX3_FAN_MODES)
        self.assertIn("AUTO2", REJECTED_NON_FX3_FAN_MODES)
        self.assertEqual(OFF_IN_REC_RECORDING_NORMAL_PWM_PCT, 0)
        self.assertEqual(OFF_IN_REC_STANDBY_MAX_PWM_PCT, 100)
        self.assertEqual(OFF_IN_REC_EMERGENCY_OVERRIDE_TEMP_C, 78.0)
        self.assertEqual(CXD90057_PRIMARY_SOC, "CXD90057")
        self.assertEqual(CXD90058_COMPANION_SOC, "CXD90058")
        self.assertEqual(DONOR_FX6_FW_VERSION, "6.01")
        self.assertEqual(HOST_STOCK_FX3_FW_VERSION, "7.02")
        self.assertEqual(LUT_BINARY_SPLIT_BOUNDARY_FW, "7.00")
        self.assertEqual(REQUIRED_VOLATILE_LUT_OVERLAY_DIR, "/tmp/fx6_lut_overlay")
        self.assertEqual(len(VALID_USER_LUT_SLOTS), 16)
        self.assertEqual(VALID_USER_LUT_SLOTS[0], "User1")
        self.assertEqual(VALID_USER_LUT_SLOTS[-1], "User16")
        self.assertEqual(SHUTTER_ANGLE_MIN_DEG, 5.6)
        self.assertEqual(SHUTTER_ANGLE_STD_MAX_DEG, 360.0)
        self.assertEqual(SHUTTER_ANGLE_MAX_FRAMES_NORMAL, 64)
        self.assertEqual(SHUTTER_ANGLE_NORMAL_MAX_EQUIV_DEG, 23040.0)
        self.assertEqual(ALLOWED_EXPOSURE_STEPS_EV, (0.3, 0.5))

    # --- 2. Strictly Read-Only (O_RDONLY) Donor Contract Audit ---

    def test_03_donor_audit_default_mode_respects_environment(self) -> None:
        audit = audit_phase199_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid, audit.errors)
        self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 4)
        self.assertEqual(audit.missing_markers, ())
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if env_clean:
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.files_inspected, 0)
        else:
            self.assertIn(
                audit.verification_mode,
                ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
            )

    def test_04_donor_audit_forced_clean_room_and_missing_work_root_fallback(self) -> None:
        clean = audit_phase199_donor_contracts(force_clean_room=True)
        self.assertTrue(clean.valid)
        self.assertEqual(clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean.files_inspected, 0)
        self.assertEqual(len(clean.sha256_by_artifact), 4)

        with tempfile.TemporaryDirectory() as tmp:
            missing_work = audit_phase199_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
            )
            self.assertTrue(missing_work.valid)
            self.assertEqual(missing_work.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(missing_work.files_inspected, 0)

    def test_05_donor_audit_synthetic_tree_valid_vs_corrupted_marker_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, patched_specs = _create_synthetic_donor_tree(Path(tmp), corrupt_fan=False)
            with patch(
                "fx3_safety.realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.PINNED_PHASE199_DONOR_SPECS",
                patched_specs,
            ):
                ok_audit = audit_phase199_donor_contracts(
                    work_root=work,
                    force_clean_room=False,
                )
            self.assertTrue(ok_audit.valid, ok_audit.errors)
            self.assertEqual(ok_audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(ok_audit.files_inspected, 4)

            # Without patching SHA-256, synthetic zeros fail integrity check
            bad_hash_audit = audit_phase199_donor_contracts(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(bad_hash_audit.valid)
            self.assertEqual(bad_hash_audit.status, STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY)

        with tempfile.TemporaryDirectory() as tmp2:
            work2, patched_corrupt = _create_synthetic_donor_tree(Path(tmp2), corrupt_fan=True)
            with patch(
                "fx3_safety.realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard.PINNED_PHASE199_DONOR_SPECS",
                patched_corrupt,
            ):
                bad_marker = audit_phase199_donor_contracts(
                    work2 if False else None,
                    work_root=work2,
                    force_clean_room=False,
                )
            self.assertFalse(bad_marker.valid)
            self.assertEqual(bad_marker.status, STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY)
            self.assertEqual(len(bad_marker.missing_markers), 1)

    # --- 3. Gate G69: ILME-FX3 Exact 4-Mode [Fan Control] & Pre-Backup Thermal Guard ---

    def test_06_g69_default_prebackup_auto_high_passes_safely(self) -> None:
        res = verify_fx3_4mode_fan_pwm_and_prebackup_guard()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G69)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.menu_path, FX3_FAN_CONTROL_MENU_PATH)
        self.assertEqual(res.canonical_fan_mode, FX3_FAN_MODE_AUTO)
        self.assertTrue(res.exact_4mode_enum_valid)
        self.assertTrue(res.off_in_rec_pwm_contract_valid)
        self.assertTrue(res.prebackup_thermal_guard_valid)
        self.assertFalse(res.always_off_prebackup_blocked)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_07_g69_accepts_all_4_canonical_fx3_fan_modes_in_normal_camera_operation(self) -> None:
        for label, expected_canon in (
            ("Auto", FX3_FAN_MODE_AUTO),
            ("Minimum", FX3_FAN_MODE_MINIMUM),
            ("Off in Rec", FX3_FAN_MODE_OFF_IN_REC),
            ("Always Off", FX3_FAN_MODE_ALWAYS_OFF),
        ):
            res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                fan_mode=label,
                operation_context="NORMAL_CAMERA_OPERATION",
                pre_backup_or_high_load=False,
                require_auto_for_prebackup=False,
            )
            self.assertTrue(res.valid, f"failed for {label}: {res.errors}")
            self.assertEqual(res.canonical_fan_mode, expected_canon)

    def test_08_g69_rejects_auto1_auto2_and_non_fx3_studio_lumix_fan_tokens(self) -> None:
        for bad_mode in (
            "Auto1",
            "Auto2",
            "AUTO_1",
            "AUTO_2",
            "LUMIX_AUTO1",
            "LUMIX_AUTO2",
            "STUDIO_AUTO1",
            "STUDIO_AUTO2",
            "Normal",
            "High",
            "Turbo",
        ):
            res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                fan_mode=bad_mode,
                operation_context="NORMAL_CAMERA_OPERATION",
                pre_backup_or_high_load=False,
                require_auto_for_prebackup=False,
            )
            self.assertFalse(res.valid, f"expected rejection for {bad_mode}")
            self.assertEqual(res.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)
            self.assertFalse(res.exact_4mode_enum_valid)

        with self.assertRaises(ValueError):
            compute_fx3_702_fan_pwm_duty_pct(fan_mode="Auto1")

    def test_09_g69_rejects_mutated_menu_options_list_or_wrong_body_fw(self) -> None:
        r_menu = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            menu_options=("Auto1", "Auto2", "Off in Rec", "Always Off"),
        )
        self.assertFalse(r_menu.valid)
        self.assertEqual(r_menu.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)

        r_fw = verify_fx3_4mode_fan_pwm_and_prebackup_guard(firmware_version="5.00")
        self.assertFalse(r_fw.valid)
        self.assertEqual(r_fw.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)

        r_body = verify_fx3_4mode_fan_pwm_and_prebackup_guard(body_model_name="ILME-FX30")
        self.assertFalse(r_body.valid)
        self.assertEqual(r_body.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)

    def test_10_g69_models_off_in_rec_zero_pwm_in_rec_and_100_max_pwm_in_standby(self) -> None:
        # Normal recording (< 78C) -> 0% PWM
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Off in Rec",
                recording_active=True,
                cxd90057_temp_c=52.0,
                cxd90058_temp_c=50.0,
            ),
            0,
        )
        # Standby -> 100% MAX PWM active purge
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Off in Rec",
                recording_active=False,
                cxd90057_temp_c=40.0,
                cxd90058_temp_c=39.0,
            ),
            100,
        )
        # Thermal emergency (>= 78C) during recording -> 100% override
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Off in Rec",
                recording_active=True,
                cxd90057_temp_c=78.5,
                cxd90058_temp_c=74.0,
            ),
            100,
        )

        r_rec = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Off in Rec",
            recording_active=True,
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            require_auto_for_prebackup=False,
            cxd90057_temp_c=50.0,
            cxd90058_temp_c=48.0,
        )
        self.assertTrue(r_rec.valid, r_rec.errors)
        self.assertEqual(r_rec.modeled_pwm_duty_pct, 0)
        self.assertEqual(r_rec.observed_pwm_duty_pct, 0)

        r_stby = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Off in Rec",
            recording_active=False,
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            require_auto_for_prebackup=False,
            cxd90057_temp_c=45.0,
            cxd90058_temp_c=43.0,
        )
        self.assertTrue(r_stby.valid, r_stby.errors)
        self.assertEqual(r_stby.modeled_pwm_duty_pct, 100)
        self.assertEqual(r_stby.observed_pwm_duty_pct, 100)

    def test_11_g69_blocks_off_in_rec_pwm_contract_violations_and_emergency_override_disable(
        self,
    ) -> None:
        # Non-zero PWM during normal Off-in-Rec recording
        r1 = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Off in Rec",
            recording_active=True,
            observed_pwm_duty_pct=50,
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            require_auto_for_prebackup=False,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION)

        # Standby not running 100% MAX PWM purge in Off in Rec
        r2 = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Off in Rec",
            recording_active=False,
            observed_pwm_duty_pct=35,
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            require_auto_for_prebackup=False,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION)

        # Emergency thermal override disabled or suppressed at >= 78C
        r3 = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Off in Rec",
            recording_active=True,
            cxd90057_temp_c=79.0,
            cxd90058_temp_c=75.0,
            observed_pwm_duty_pct=0,
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            require_auto_for_prebackup=False,
            auto_power_off_temp="High",
        )
        self.assertFalse(r3.valid)
        self.assertEqual(r3.status, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION)

        r4 = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            off_in_rec_emergency_override_enabled=False,
        )
        self.assertFalse(r4.valid)
        self.assertEqual(r4.status, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION)

    def test_12_g69_fail_closes_prebackup_and_rehearsal_when_always_off_or_non_auto(self) -> None:
        for ctx in (
            "PRE_BACKUP_ADJUST_CONTROL_0X40_P3_75MIB",
            "HIGH_LOAD_DUAL_SYSTEM_REHEARSAL",
            "STAGE_B_REHEARSAL",
        ):
            r_always_off = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                fan_mode="Always Off",
                operation_context=ctx,
                pre_backup_or_high_load=True,
            )
            self.assertFalse(r_always_off.valid)
            self.assertEqual(
                r_always_off.status, STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED
            )
            self.assertTrue(r_always_off.always_off_prebackup_blocked)

        for non_auto in ("Minimum", "Off in Rec"):
            r_non_auto = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                fan_mode=non_auto,
                operation_context="PRE_BACKUP_ADJUST_CONTROL_0X40_P3_75MIB",
                pre_backup_or_high_load=True,
                require_auto_for_prebackup=True,
            )
            self.assertFalse(r_non_auto.valid)
            self.assertEqual(
                r_non_auto.status, STATUS_BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO
            )

    def test_13_g69_auto_power_off_temp_standard_vs_high_and_cxd90057_cxd90058_ceilings(
        self,
    ) -> None:
        # Standard in pre-backup passes when cool (< 62C) and emits advisory warning
        r_std = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Auto",
            auto_power_off_temp="Standard",
            cxd90057_temp_c=50.0,
            cxd90058_temp_c=48.0,
        )
        self.assertTrue(r_std.valid, r_std.errors)
        self.assertEqual(len(r_std.warnings), 1)

        # Pre-backup start temp > 62.0C blocked
        r_hot_pre = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Auto",
            auto_power_off_temp="High",
            cxd90057_temp_c=63.5,
            cxd90058_temp_c=60.0,
        )
        self.assertFalse(r_hot_pre.valid)
        self.assertEqual(
            r_hot_pre.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

        # Normal operation: 74C fails Standard (68C) but passes High (82C)
        r_norm_std = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Auto",
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            auto_power_off_temp="Standard",
            cxd90057_temp_c=74.0,
            cxd90058_temp_c=70.0,
        )
        self.assertFalse(r_norm_std.valid)
        self.assertEqual(
            r_norm_std.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

        r_norm_high = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Auto",
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            auto_power_off_temp="High",
            cxd90057_temp_c=74.0,
            cxd90058_temp_c=70.0,
        )
        self.assertTrue(r_norm_high.valid, r_norm_high.errors)

        # Companion CXD90058 exceeding High ceiling (83.0C) blocked
        r_58_over = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Auto",
            operation_context="NORMAL_CAMERA_OPERATION",
            pre_backup_or_high_load=False,
            auto_power_off_temp="High",
            cxd90057_temp_c=65.0,
            cxd90058_temp_c=83.0,
        )
        self.assertFalse(r_58_over.valid)
        self.assertEqual(
            r_58_over.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

    def test_14_g69_rejects_malformed_telemetry_and_persistent_emmc_write_requests(self) -> None:
        for bad_tel in (
            {"fan_mode": ""},
            {"menu_options": ()},
            {"recording_active": 1},
            {"observed_pwm_duty_pct": 105},
            {"cxd90057_temp_c": True},
            {"body_model_id": -5},
        ):
            res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(**bad_tel)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"expected fail for {bad_tel}")
            self.assertEqual(res.status, STATUS_BLOCKED_G69_TELEMETRY_INVALID)

        verdict, r_pw = evaluate_g69_fan_pwm_thermal_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(r_pw.valid)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 4. Gate G70: 6.01 vs 7.00/7.02 p2:/setting User LUT Binary Split & Shutter Speed/Angle ---

    def test_15_g70_default_601_to_702_volatile_lut_overlay_and_shutter_angle_passes(self) -> None:
        res = verify_lut_601_702_split_and_shutter_angle_guard()
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G70)
        self.assertEqual(res.donor_lut_slot_format, LUT_SLOT_FORMAT_LEGACY_LE_601)
        self.assertEqual(res.host_lut_slot_format, LUT_SLOT_FORMAT_OPTIMIZED_GE_700)
        self.assertTrue(res.generation_format_split_detected)
        self.assertTrue(res.volatile_lut_overlay_redirected)
        self.assertTrue(res.h0_equals_h3_p2_setting)
        self.assertTrue(res.lut_binary_split_firewall_valid)
        self.assertTrue(res.speed_and_angle_slots_independent)
        self.assertTrue(res.shutter_speed_angle_valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_16_g70_classifies_601_legacy_vs_700_702_optimized_lut_binary_formats(self) -> None:
        for leg_ver in ("2.00", "5.00", "6.00", "6.01", "Ver. 6.01"):
            self.assertEqual(
                classify_user_lut_slot_binary_format(leg_ver),
                LUT_SLOT_FORMAT_LEGACY_LE_601,
            )
        for opt_ver in ("7.00", "7.01", "7.02", "v7.02", "Ver. 8.00"):
            self.assertEqual(
                classify_user_lut_slot_binary_format(opt_ver),
                LUT_SLOT_FORMAT_OPTIMIZED_GE_700,
            )
        self.assertEqual(classify_user_lut_slot_binary_format("invalid"), "INVALID_FW_VERSION")

    def test_17_g70_validates_user1_through_user16_slots_and_rejects_out_of_range(self) -> None:
        for idx in range(USER_LUT_SLOT_MIN, USER_LUT_SLOT_MAX + 1):
            r_str = verify_lut_601_702_split_and_shutter_angle_guard(
                lut_slot=f"User{idx}",
                stageb_lut_registry_path=f"/tmp/fx6_lut_overlay/User{idx}.lutbin",
            )
            self.assertTrue(r_str.valid, r_str.errors)
            self.assertEqual(r_str.lut_slot_name, f"User{idx}")
            self.assertEqual(r_str.lut_slot_index, idx)

            r_int = verify_lut_601_702_split_and_shutter_angle_guard(lut_slot=idx)
            self.assertTrue(r_int.valid, r_int.errors)
            self.assertEqual(r_int.lut_slot_index, idx)

        for bad_slot in ("User0", "User17", "User99", 0, 17, "BaseLUT"):
            r_bad = verify_lut_601_702_split_and_shutter_angle_guard(lut_slot=bad_slot)
            self.assertFalse(r_bad.valid, f"expected fail for slot={bad_slot}")
            self.assertEqual(r_bad.status, STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID)

    def test_18_g70_blocks_stageb_601_writes_into_702_p2_setting_and_non_tmp_paths(self) -> None:
        for bad_path in (
            "p2:/setting/lut/User1.bin",
            "/setting/lut/User1.bin",
            "/dev/nflasha2",
            "/dev/cnflasha2",
            "/var/tmp/User1.bin",
        ):
            r = verify_lut_601_702_split_and_shutter_angle_guard(
                stageb_lut_registry_path=bad_path,
            )
            self.assertFalse(r.valid, f"expected block for path={bad_path}")
            self.assertEqual(
                r.status, STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE
            )

        for bad_write_kw in (
            {"stageb_p2_setting_lut_write_attempted": True},
            {"cross_generation_raw_slot_inject": True},
            {"p2_setting_lut_mutation_bytes": 64},
            {"p2_setting_mount_ro": False},
        ):
            r = verify_lut_601_702_split_and_shutter_angle_guard(**bad_write_kw)
            self.assertFalse(r.valid, f"expected block for {bad_write_kw}")
            self.assertEqual(
                r.status, STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE
            )

    def test_19_g70_blocks_h0_h3_p2_setting_hash_drift_and_stale_601_lut_state(self) -> None:
        r_drift = verify_lut_601_702_split_and_shutter_angle_guard(
            h0_p2_setting_sha256="a" * 64,
            h3_p2_setting_sha256="c" * 64,
        )
        self.assertFalse(r_drift.valid)
        self.assertFalse(r_drift.h0_equals_h3_p2_setting)
        self.assertEqual(r_drift.status, STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT)

        r_stale = verify_lut_601_702_split_and_shutter_angle_guard(
            upgraded_from_le_601_stale_lut_unreregistered=True,
        )
        self.assertFalse(r_stale.valid)
        self.assertEqual(r_stale.status, STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID)

    def test_20_g70_validates_independent_speed_vs_angle_slots_and_03_05_ev_immunity(self) -> None:
        for sm in ("Speed", "Angle", "SPEED", "ANGLE"):
            for step in (0.3, 0.5, "0.3EV", "0.5EV", "1/3", "1/2"):
                r = verify_lut_601_702_split_and_shutter_angle_guard(
                    shutter_mode=sm,
                    exposure_step_ev=step,
                )
                self.assertTrue(r.valid, f"failed for sm={sm}, step={step}: {r.errors}")

        for bad_slot_kw in (
            {
                "shutter_speed_bk4_slot_id": 0x01120024,
                "shutter_angle_bk4_slot_id": 0x01120024,
            },
            {"speed_and_angle_slots_independent": False},
            {"mode_toggle_mutated_inactive_slot": True},
            {"exposure_step_ev": 1.0},
            {"exposure_step_altered_shutter_angle": True},
            {"shutter_mode": "SYNCHRO_SCAN_ONLY"},
            {"shooting_mode": "STILL_PHOTO"},
        ):
            r = verify_lut_601_702_split_and_shutter_angle_guard(**bad_slot_kw)
            self.assertFalse(r.valid, f"expected block for {bad_slot_kw}")
            self.assertEqual(
                r.status, STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION
            )

    def test_21_g70_enforces_normal_5_6_to_64f_vs_119_88p_100p_and_sq_5_6_to_360_bounds(
        self,
    ) -> None:
        # Normal Movie (23.98p / 59.94p): 5.6 deg .. 64F allowed
        for fps in ("23.98p", "24.00p", "25p", "29.97p", "50p", "59.94p"):
            r_min = verify_lut_601_702_split_and_shutter_angle_guard(
                rec_frame_rate=fps,
                shutter_angle_deg=5.6,
                shutter_frames_count=1,
            )
            self.assertTrue(r_min.valid, r_min.errors)

            r_64f = verify_lut_601_702_split_and_shutter_angle_guard(
                rec_frame_rate=fps,
                shutter_angle_deg=360.0,
                shutter_frames_count=64,
            )
            self.assertTrue(r_64f.valid, r_64f.errors)

        # Normal Movie > 64F or < 5.6 deg blocked
        for bad_norm in (
            {"rec_frame_rate": "23.98p", "shutter_angle_deg": 5.5, "shutter_frames_count": 1},
            {"rec_frame_rate": "23.98p", "shutter_angle_deg": 360.0, "shutter_frames_count": 65},
            {"rec_frame_rate": "23.98p", "shutter_angle_deg": 25000.0, "shutter_frames_count": 1},
        ):
            r_bn = verify_lut_601_702_split_and_shutter_angle_guard(**bad_norm)
            self.assertFalse(r_bn.valid)
            self.assertEqual(r_bn.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS)

        # High-FPS (119.88p / 100p / 240p) and S&Q clamped to 5.6 .. 360.0 deg (1F only!)
        for clamp_case in (
            {"rec_frame_rate": "119.88p", "sq_mode_active": False},
            {"rec_frame_rate": "100p", "sq_mode_active": False},
            {"rec_frame_rate": "23.98p", "sq_mode_active": True},
            {"rec_frame_rate": "25p", "shooting_mode": "S&Q"},
        ):
            r_360_ok = verify_lut_601_702_split_and_shutter_angle_guard(
                shutter_angle_deg=360.0,
                shutter_frames_count=1,
                **clamp_case,
            )
            self.assertTrue(r_360_ok.valid, r_360_ok.errors)
            self.assertTrue(r_360_ok.high_fps_or_sq_360_clamp_active)

            r_2f_fail = verify_lut_601_702_split_and_shutter_angle_guard(
                shutter_angle_deg=360.0,
                shutter_frames_count=2,
                **clamp_case,
            )
            self.assertFalse(r_2f_fail.valid)
            self.assertEqual(
                r_2f_fail.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS
            )

            r_720_fail = verify_lut_601_702_split_and_shutter_angle_guard(
                shutter_angle_deg=720.0,
                shutter_frames_count=1,
                **clamp_case,
            )
            self.assertFalse(r_720_fail.valid)
            self.assertEqual(
                r_720_fail.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS
            )

    def test_22_g70_rejects_malformed_telemetry_and_persistent_emmc_write_requests(self) -> None:
        for bad_tel in (
            {"lut_slot": True},
            {"p2_setting_lut_mutation_bytes": -1},
            {"shutter_angle_deg": True},
            {"shutter_frames_count": True},
            {"shutter_speed_bk4_slot_id": "not_an_int"},
            {"stageb_lut_registry_path": ""},
        ):
            res = verify_lut_601_702_split_and_shutter_angle_guard(**bad_tel)  # type: ignore[arg-type]
            self.assertFalse(res.valid, f"expected fail for {bad_tel}")
            self.assertEqual(res.status, STATUS_BLOCKED_G70_TELEMETRY_INVALID)

        verdict, r_pw = evaluate_g70_lut_split_shutter_angle_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(r_pw.valid)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 5. Pure Validator Direct Invocations & Donor Fault Propagation ---

    def test_23_pure_validators_direct_invocations(self) -> None:
        ok1, code1, _ = validate_fx3_4mode_fan_enum_and_off_in_rec_pwm(
            fan_mode="Minimum",
            recording_active=True,
        )
        self.assertTrue(ok1)
        self.assertEqual(code1, "")

        ok2, code2, _ = validate_prebackup_fan_and_auto_power_off_temp(
            fan_mode="Auto",
            auto_power_off_temp="High",
            cxd90057_temp_c=45.0,
            cxd90058_temp_c=43.0,
        )
        self.assertTrue(ok2)
        self.assertEqual(code2, "")

        ok3, code3, _ = validate_lut_601_vs_702_p2_setting_split_firewall(
            donor_stageb_fw_version="6.01",
            host_stock_fx3_fw_version="7.00",
            lut_slot="User16",
            stageb_lut_registry_path="/tmp/fx6_lut_overlay/User16.lutbin",
        )
        self.assertTrue(ok3)
        self.assertEqual(code3, "")

        ok4, code4, _ = validate_independent_shutter_speed_angle_bounds(
            shutter_mode="Angle",
            shooting_mode="BIG6_MOVIE",
            rec_frame_rate="24.00p",
            shutter_angle_deg=172.8,
        )
        self.assertTrue(ok4)
        self.assertEqual(code4, "")

    def test_24_g69_and_g70_evaluators_propagate_corrupted_donor_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, _ = _create_synthetic_donor_tree(Path(tmp), corrupt_fan=True)
            v69, r69 = evaluate_g69_fan_pwm_thermal_guard(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(v69.passed)
            self.assertFalse(r69.valid)
            self.assertIn(STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY, r69.violation_codes)

            v70, r70 = evaluate_g70_lut_split_shutter_angle_guard(
                work_root=work,
                force_clean_room=False,
            )
            self.assertFalse(v70.passed)
            self.assertFalse(r70.valid)
            self.assertIn(STATUS_BLOCKED_PHASE199_DONOR_INTEGRITY, r70.violation_codes)

    # --- 6. Unified 70-Gate Master Safety Preflight (`evaluate_70gate_preflight`) ---

    def test_25_preflight_default_offline_verifies_67_of_70_and_hard_locks_redlines(self) -> None:
        report = evaluate_70gate_preflight(DEFAULT_REPO_ROOT)
        self.assertIsInstance(report, Master70GateReport)
        self.assertEqual(report.schema, REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_SCHEMA)
        self.assertEqual(report.version, REALHW_FAN_PWM_SHUTTER_ANGLE_LUT_SPLIT_70GATE_VERSION)
        self.assertEqual(len(report.gates), 70)
        self.assertTrue(report.offline_67_gates_verified, report.errors)
        self.assertFalse(report.all_70_gates_verified)
        self.assertTrue(report.g13_to_g70_all_passed)
        self.assertTrue(report.g69_to_g70_all_passed)
        self.assertEqual(report.summary["verified_gates"], 67)
        self.assertEqual(report.summary["technical_gates_passed"], 67)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(report.summary["g69_to_g70_verified"], 2)
        self.assertEqual(report.status, "VERIFIED_67_OF_70_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(report.agent_auto_flash_blocked)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_26_preflight_dry_run_simulated_verifies_70_of_70_still_locks_attach(self) -> None:
        report = self.default_dry_70
        self.assertEqual(len(report.gates), 70)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.all_70_gates_verified)
        self.assertEqual(report.summary["verified_gates"], 70)
        self.assertEqual(report.summary["technical_gates_passed"], 70)
        self.assertEqual(report.status, "VERIFIED_ALL_70_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(report.agent_auto_flash_blocked)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.human_hardware_attach_token)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertFalse(report.physical_flash_auto_exec_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_27_preflight_clean_room_mode_verifies_67_offline_and_70_dry_run(self) -> None:
        r_off = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(r_off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_off.offline_67_gates_verified)
        self.assertEqual(r_off.summary["verified_gates"], 67)

        r_dry = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(r_dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r_dry.all_70_gates_verified)
        self.assertEqual(r_dry.summary["verified_gates"], 70)

    def test_28_preflight_gate_order_places_g69_and_g70_at_indices_68_and_69(self) -> None:
        report = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_68_override=self.clean_dry_68,
        )
        self.assertEqual(report.gates[68]["gate_id"], G69_GATE_ID)
        self.assertEqual(report.gates[68]["gate_code"], G69_GATE_CODE)
        self.assertEqual(report.gates[69]["gate_id"], G70_GATE_ID)
        self.assertEqual(report.gates[69]["gate_code"], G70_GATE_CODE)

    def test_29_preflight_propagates_g69_fan_enum_pwm_and_always_off_faults(self) -> None:
        # Full end-to-end uncached propagation check
        r_auto1 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fan_pwm_thermal_kwargs={"fan_mode": "Auto1"},
        )
        self.assertFalse(r_auto1.all_70_gates_verified)
        self.assertFalse(r_auto1.g69_to_g70_all_passed)
        self.assertEqual(r_auto1.status, STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2)
        self.assertEqual(r_auto1.summary["verified_gates"], 69)

        r_always_off = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fan_pwm_thermal_kwargs={"fan_mode": "Always Off"},
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_always_off.all_70_gates_verified)
        self.assertEqual(
            r_always_off.status, STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED
        )

        r_pwm = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fan_pwm_thermal_kwargs={"off_in_rec_standby_pwm_pct": 40},
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_pwm.all_70_gates_verified)
        self.assertEqual(
            r_pwm.status, STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION
        )

        r_hot = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            fan_pwm_thermal_kwargs={"cxd90057_temp_c": 88.0},
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_hot.all_70_gates_verified)
        self.assertEqual(
            r_hot.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

    def test_30_preflight_propagates_g70_lut_split_and_shutter_angle_faults(self) -> None:
        # Full end-to-end uncached propagation check
        r_lut_p2 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_split_shutter_angle_kwargs={
                "stageb_lut_registry_path": "p2:/setting/lut/User1.bin"
            },
        )
        self.assertFalse(r_lut_p2.all_70_gates_verified)
        self.assertFalse(r_lut_p2.g69_to_g70_all_passed)
        self.assertEqual(
            r_lut_p2.status, STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE
        )
        self.assertEqual(r_lut_p2.summary["verified_gates"], 69)

        r_h0h3 = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_split_shutter_angle_kwargs={"h3_p2_setting_sha256": "0" * 64},
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_h0h3.all_70_gates_verified)
        self.assertEqual(r_h0h3.status, STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT)

        r_collision = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_split_shutter_angle_kwargs={"mode_toggle_mutated_inactive_slot": True},
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_collision.all_70_gates_verified)
        self.assertEqual(
            r_collision.status, STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION
        )

        r_angle = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            lut_split_shutter_angle_kwargs={
                "rec_frame_rate": "119.88p",
                "shutter_frames_count": 4,
            },
            master_68_override=self.clean_dry_68,
        )
        self.assertFalse(r_angle.all_70_gates_verified)
        self.assertEqual(r_angle.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS)

    def test_31_preflight_propagates_g58_to_g68_faults_and_persistent_write_block(self) -> None:
        for kwargs, expected_status in (
            (
                {"bench_interlock_kwargs": {"auto_flash_requested": True}},
                STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
            ),
            (
                {"usblan_rtmp_kwargs": {"adapter_chipset": "AX88179A"}},
                STATUS_BLOCKED_G67_USBLAN_ADAPTER_OR_POWER_UNSAFE,
            ),
            (
                {"clipflag_anamorphic_kwargs": {"video_essence_modified": True}},
                STATUS_BLOCKED_G68_CLIP_FLAG_ESSENCE_MUTATION_OR_APP_FLOOR,
            ),
        ):
            r = evaluate_70gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated=True,
                **kwargs,
            )
            self.assertFalse(r.all_70_gates_verified)
            self.assertEqual(r.status, expected_status)

        r_pw = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r_pw.all_70_gates_verified)
        self.assertEqual(r_pw.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_32_dry_run_simulated_backup_alias_flag_works(self) -> None:
        report = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_68_override=self.clean_dry_68,
        )
        self.assertTrue(report.all_70_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 70)

    # --- 7. Backward Compatibility: 58/60/62/64/66/68-Gate Preflights & CLIs Intact ---

    def test_33_backward_compatibility_58_60_62_64_66_68_preflights_intact(self) -> None:
        self.assertEqual(self.clean_dry_68.summary["verified_gates"], 68)
        self.assertTrue(self.clean_dry_68.all_68_gates_verified)

        for cmd, expected in (
            (["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"], 58),
            (["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 60),
            (["verify-62-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 62),
            (["verify-64-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 64),
            (["verify-66-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 66),
            (["verify-68-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 68),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(cmd)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["verified_gates"], expected)

    # --- 8. Edge-Case Coverage Matrix for G69 & G70 ---

    def test_34_g69_pwm_duty_ramp_across_auto_minimum_always_off(self) -> None:
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Auto", cxd90057_temp_c=35.0, cxd90058_temp_c=34.0
            ),
            AUTO_MODE_BASE_PWM_PCT,
        )
        mid_pwm = compute_fx3_702_fan_pwm_duty_pct(
            fan_mode="Auto", cxd90057_temp_c=59.0, cxd90058_temp_c=55.0
        )
        self.assertGreater(mid_pwm, AUTO_MODE_BASE_PWM_PCT)
        self.assertLess(mid_pwm, 100)
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Auto", cxd90057_temp_c=80.0, cxd90058_temp_c=79.0
            ),
            100,
        )
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Minimum", cxd90057_temp_c=45.0, cxd90058_temp_c=42.0
            ),
            MINIMUM_MODE_QUIET_PWM_PCT,
        )
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Minimum", cxd90057_temp_c=65.0, cxd90058_temp_c=60.0
            ),
            50,
        )
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Minimum", cxd90057_temp_c=79.0, cxd90058_temp_c=75.0
            ),
            100,
        )
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Always Off", cxd90057_temp_c=50.0, cxd90058_temp_c=48.0
            ),
            0,
        )
        self.assertEqual(
            compute_fx3_702_fan_pwm_duty_pct(
                fan_mode="Always Off", cxd90057_temp_c=78.0, cxd90058_temp_c=70.0
            ),
            100,
        )

    def test_35_g69_body_model_id_hex_string_and_fx3a_supported(self) -> None:
        r_fx3 = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            body_model_name=FX3_MODEL_NAME,
            body_model_id="0x91030080",
        )
        self.assertTrue(r_fx3.valid, r_fx3.errors)
        self.assertEqual(r_fx3.body_model_id, FX3_MODEL_ID)
        self.assertEqual(r_fx3.body_model_id_hex, "0x91030080")

        r_fx3a = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            body_model_name=FX3A_MODEL_NAME,
            body_model_id=FX3_MODEL_ID,
        )
        self.assertTrue(r_fx3a.valid, r_fx3a.errors)

    def test_36_g69_rejects_invalid_auto_power_off_temp_and_unknown_context(self) -> None:
        r_apo = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            auto_power_off_temp="UltraHigh",
        )
        self.assertFalse(r_apo.valid)
        self.assertEqual(
            r_apo.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

        r_ctx = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            operation_context="UNKNOWN_OPERATION_MODE",
        )
        self.assertFalse(r_ctx.valid)
        self.assertEqual(
            r_ctx.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
        )

    def test_37_g69_critical_90c_shutdown_and_implausible_sensor_temperatures(self) -> None:
        for bad_t in (-35.0, 90.0, 95.0, 140.0):
            res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                operation_context="NORMAL_CAMERA_OPERATION",
                pre_backup_or_high_load=False,
                auto_power_off_temp="High",
                cxd90057_temp_c=bad_t,
            )
            self.assertFalse(res.valid, f"expected thermal block for {bad_t}C")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT
            )

    def test_38_g69_minimum_allowed_in_prebackup_only_when_require_auto_disabled(self) -> None:
        res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Minimum",
            operation_context="STAGE_B_REHEARSAL",
            pre_backup_or_high_load=True,
            require_auto_for_prebackup=False,
        )
        self.assertTrue(res.valid, res.errors)

        # Even with require_auto_for_prebackup=False, Always Off MUST still block!
        res_ao = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
            fan_mode="Always Off",
            operation_context="STAGE_B_REHEARSAL",
            pre_backup_or_high_load=True,
            require_auto_for_prebackup=False,
        )
        self.assertFalse(res_ao.valid)
        self.assertEqual(res_ao.status, STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED)

    def test_39_g70_rejects_same_generation_or_inverted_lut_split_versions(self) -> None:
        # Host below 7.00
        r_host_old = verify_lut_601_702_split_and_shutter_angle_guard(
            donor_stageb_fw_version="6.01",
            host_stock_fx3_fw_version="6.00",
        )
        self.assertFalse(r_host_old.valid)
        self.assertEqual(
            r_host_old.status, STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID
        )

        # Donor >= 7.00 (not FX6 6.01 legacy donor)
        r_donor_700 = verify_lut_601_702_split_and_shutter_angle_guard(
            donor_stageb_fw_version="7.00",
            host_stock_fx3_fw_version="7.02",
        )
        self.assertFalse(r_donor_700.valid)
        self.assertEqual(
            r_donor_700.status, STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID
        )

    def test_40_g70_accepts_root_volatile_overlay_dir_and_hex_bk4_slot_ids(self) -> None:
        res = verify_lut_601_702_split_and_shutter_angle_guard(
            stageb_lut_registry_path=REQUIRED_VOLATILE_LUT_OVERLAY_DIR,
            shutter_speed_bk4_slot_id="0x01120024",
            shutter_angle_bk4_slot_id="0x01120028",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.shutter_speed_bk4_slot_hex, "0x01120024")
        self.assertEqual(res.shutter_angle_bk4_slot_hex, "0x01120028")

    def test_41_g70_multi_frame_shutter_angle_equivalent_degrees_and_mismatch(self) -> None:
        # 2F == 720.0 deg equivalent allowed in normal Movie
        r_ok = verify_lut_601_702_split_and_shutter_angle_guard(
            rec_frame_rate="24.00p",
            shutter_frames_count=2,
            shutter_angle_deg=720.0,
        )
        self.assertTrue(r_ok.valid, r_ok.errors)

        # 64F == 23040.0 deg equivalent allowed in normal Movie
        r_64 = verify_lut_601_702_split_and_shutter_angle_guard(
            rec_frame_rate="24.00p",
            shutter_frames_count=64,
            shutter_angle_deg=23040.0,
        )
        self.assertTrue(r_64.valid, r_64.errors)

        # Mismatched multi-frame angle (e.g. frames=4 but deg=180.0)
        r_mismatch = verify_lut_601_702_split_and_shutter_angle_guard(
            rec_frame_rate="24.00p",
            shutter_frames_count=4,
            shutter_angle_deg=180.0,
        )
        self.assertFalse(r_mismatch.valid)
        self.assertEqual(
            r_mismatch.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS
        )

    def test_42_g70_rejects_invalid_rec_frame_rate_tokens(self) -> None:
        for bad_fps in ("0p", "2000p", "NTSC_BAD", "-24p"):
            res = verify_lut_601_702_split_and_shutter_angle_guard(
                rec_frame_rate=bad_fps,
            )
            self.assertFalse(res.valid, f"expected fail for fps={bad_fps}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS
            )

    def test_43_g70_slot_parser_supports_whitespace_and_underscore_variants(self) -> None:
        for token, idx in (("user 1", 1), ("USER_8", 8), ("User16", 16), ("12", 12)):
            res = verify_lut_601_702_split_and_shutter_angle_guard(lut_slot=token)
            self.assertTrue(res.valid, f"failed for token={token}: {res.errors}")
            self.assertEqual(res.lut_slot_index, idx)
            self.assertEqual(res.lut_slot_name, f"User{idx}")

    # --- 9. CLI Subcommands, Zero Raw Firmware Leakage & Runtime Budget ---

    def test_44_cli_verify_g69_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g69-fan-pwm-thermal", "--force-clean-room", "--json"],
            ["verify-g69-fan-pwm-thermal", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G69)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(data["fan_pwm_thermal_guard"]["exact_4mode_enum_valid"])
                self.assertTrue(
                    data["fan_pwm_thermal_guard"]["off_in_rec_pwm_contract_valid"]
                )
                self.assertTrue(
                    data["fan_pwm_thermal_guard"]["prebackup_thermal_guard_valid"]
                )
            else:
                self.assertIn(f"gate={G69_GATE_ID}", buf.getvalue())

    def test_45_cli_verify_g70_subcommand_json_and_text(self) -> None:
        for subcmd in (
            ["verify-g70-lut-601-702-shutter-angle", "--force-clean-room", "--json"],
            ["verify-g70-lut-601-702-shutter-angle", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, buf.getvalue())
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertEqual(data["status"], STATUS_VERIFIED_G70)
                self.assertFalse(data["persistent_emmc_writes_authorized"])
                self.assertTrue(
                    data["lut_split_shutter_angle_guard"][
                        "lut_binary_split_firewall_valid"
                    ]
                )
                self.assertTrue(
                    data["lut_split_shutter_angle_guard"]["shutter_speed_angle_valid"]
                )
            else:
                self.assertIn(f"gate={G70_GATE_ID}", buf.getvalue())

    def test_46_cli_verify_70_gates_offline_and_dry_run_modes(self) -> None:
        for subcmd, expected_count in (
            (["verify-70-gates", "--force-clean-room", "--json"], 67),
            (["verify-70-gates", "--force-clean-room", "--dry-run-simulated", "--json"], 70),
            (["verify-70-gates", "--force-clean-room"], None),
            (["verify-70-gates", "--force-clean-room", "--dry-run-simulated"], None),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if expected_count is not None:
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload["summary"]["verified_gates"], expected_count)
                self.assertFalse(payload["overall_ready_for_hardware_attach"])
                self.assertTrue(payload["agent_auto_flash_blocked"])

    def test_47_cli_supports_clean_room_and_dry_run_simulated_backup_aliases(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(
                ["verify-70-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_70_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 70)

    def test_48_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 70)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["human_hardware_attach_token"])
        self.assertFalse(payload["el3_payload_transmit_authorized"])
        self.assertFalse(payload["spi_nor_write_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_49_module_cli_text_output_offline_and_dry_run_smoke(self) -> None:
        for args, exp_tok in (
            (["--force-clean-room"], "verified=67/70"),
            (["--force-clean-room", "--dry-run-simulated"], "verified=70/70"),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_cli_main(args)
            self.assertEqual(rc, 0)
            self.assertIn(exp_tok, buf.getvalue())

    def test_50_to_dict_roundtrip_on_all_phase199_dataclasses(self) -> None:
        audit = audit_phase199_donor_contracts(force_clean_room=True)
        self.assertEqual(json.loads(json.dumps(audit.to_dict()))["status"], STATUS_VERIFIED_SAFE)

        g69_guard = verify_fx3_4mode_fan_pwm_and_prebackup_guard()
        self.assertEqual(json.loads(json.dumps(g69_guard.to_dict()))["status"], STATUS_VERIFIED_G69)

        g70_guard = verify_lut_601_702_split_and_shutter_angle_guard()
        self.assertEqual(json.loads(json.dumps(g70_guard.to_dict()))["status"], STATUS_VERIFIED_G70)

        _, r69 = evaluate_g69_fan_pwm_thermal_guard(force_clean_room=True)
        self.assertEqual(json.loads(json.dumps(r69.to_dict()))["status"], STATUS_VERIFIED_G69)

        _, r70 = evaluate_g70_lut_split_shutter_angle_guard(force_clean_room=True)
        self.assertEqual(json.loads(json.dumps(r70.to_dict()))["status"], STATUS_VERIFIED_G70)

    def test_51_preflight_summary_counts_match_gate_list_breakdown(self) -> None:
        r_off = evaluate_70gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(r_off.summary["total_gates"], 70)
        self.assertEqual(r_off.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r_off.summary["g13_to_g68_verified"], 56)
        self.assertEqual(r_off.summary["g69_to_g70_verified"], 2)
        self.assertEqual(
            r_off.summary["g01_to_g12_verified"]
            + r_off.summary["g13_to_g68_verified"]
            + r_off.summary["g69_to_g70_verified"],
            67,
        )
        locked_ids = [g["gate_id"] for g in r_off.gates if not g["passed"]]
        self.assertEqual(len(locked_ids), 3)
        for gid in locked_ids:
            self.assertTrue(
                gid.startswith(("G10_", "G11_", "G12_")),
                f"unexpected offline failed gate: {gid}",
            )

    def test_52_preflight_blocks_corrupted_phase199_donor_in_70gate_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work, _ = _create_synthetic_donor_tree(Path(tmp), corrupt_fan=True)
            rep = evaluate_70gate_preflight(
                DEFAULT_REPO_ROOT,
                work_root=work,
                force_clean_room=False,
                dry_run_simulated=True,
            )
            self.assertFalse(rep.all_70_gates_verified)
            self.assertFalse(rep.g69_to_g70_all_passed)

    def test_53_g69_fan_mode_case_and_whitespace_normalization(self) -> None:
        for alias, expected in (
            ("  auto ", FX3_FAN_MODE_AUTO),
            ("minimum", FX3_FAN_MODE_MINIMUM),
            ("MIN", FX3_FAN_MODE_MINIMUM),
            ("Off In Rec", FX3_FAN_MODE_OFF_IN_REC),
            ("OFF_IN_REC", FX3_FAN_MODE_OFF_IN_REC),
            ("always_off", FX3_FAN_MODE_ALWAYS_OFF),
        ):
            res = verify_fx3_4mode_fan_pwm_and_prebackup_guard(
                fan_mode=alias,
                operation_context="NORMAL_CAMERA_OPERATION",
                pre_backup_or_high_load=False,
                require_auto_for_prebackup=False,
            )
            self.assertTrue(res.valid, f"failed for alias={alias!r}: {res.errors}")
            self.assertEqual(res.canonical_fan_mode, expected)

    def test_54_g70_version_boundary_700_exact_accepted_as_optimized_host(self) -> None:
        res = verify_lut_601_702_split_and_shutter_angle_guard(
            donor_stageb_fw_version="6.01",
            host_stock_fx3_fw_version="7.00",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.host_lut_slot_format, LUT_SLOT_FORMAT_OPTIMIZED_GE_700)

    def test_55_status_safe_constants_non_empty_and_distinct(self) -> None:
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(STATUS_VERIFIED_SAFE, "VERIFIED_SAFE")
        distinct_codes = {
            STATUS_BLOCKED_G69_NON_FX3_FAN_ENUM_AUTO1_AUTO2,
            STATUS_BLOCKED_G69_OFF_IN_REC_PWM_CONTRACT_VIOLATION,
            STATUS_BLOCKED_G69_ALWAYS_OFF_PREBACKUP_BLOCKED,
            STATUS_BLOCKED_G69_PREBACKUP_REQUIRES_FAN_AUTO,
            STATUS_BLOCKED_G69_AUTO_POWER_OFF_TEMP_OR_THERMAL_OVERLIMIT,
            STATUS_BLOCKED_G69_TELEMETRY_INVALID,
            STATUS_BLOCKED_G70_STAGEB_601_TO_702_P2_SETTING_LUT_WRITE,
            STATUS_BLOCKED_G70_USER_LUT_SLOT_OR_FORMAT_INVALID,
            STATUS_BLOCKED_G70_H0_H3_P2_SETTING_HASH_DRIFT,
            STATUS_BLOCKED_G70_SHUTTER_SPEED_ANGLE_SLOT_COLLISION,
            STATUS_BLOCKED_G70_SHUTTER_ANGLE_OUT_OF_BOUNDS,
            STATUS_BLOCKED_G70_TELEMETRY_INVALID,
        }
        self.assertEqual(len(distinct_codes), 12)

    def test_56_wall_clock_ceiling_under_6_seconds(self) -> None:
        self.assertTrue(self.default_dry_70.all_70_gates_verified)
        self.assertLess(
            self.default_dry_elapsed,
            6.0,
            f"evaluate_70gate_preflight exceeded 6.0s wall-clock ceiling ({self.default_dry_elapsed:.2f}s)",
        )
        t0 = time.monotonic()
        rep_clean = evaluate_70gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        clean_elapsed = time.monotonic() - t0
        self.assertTrue(rep_clean.all_70_gates_verified)
        self.assertLess(clean_elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
