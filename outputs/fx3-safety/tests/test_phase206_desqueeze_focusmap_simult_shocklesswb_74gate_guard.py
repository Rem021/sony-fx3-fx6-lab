"""Fast dual-mode unit tests for Phase 206 — Real-Hardware Main Track Part 24:
Gate G73 (`ILME-FX3` `Ver. 7.02` `[De-Squeeze Display]` `Off / 1.3x / 2.0x / 1.5x / 1.6x=1.65x`
4-Setting Lock `[Focus Mode]=Manual Focus` + `[Focus Area]=Wide` + `[SteadyShot]=Off` +
`[Face Priority in Multi Metering]=Off`, Auto-Suppression under `HDMI RAW` / `Off(HDMI Only)` /
`Log Off` / `Remote Shooting` / `Still`, Zero In-Body FX3 `[Focus Map]` Block, and External
`M&C Focus Map` `< 150fps` Cutoff Guard),
Gate G74 (Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]` Strict Dual-Vault Parity vs
`Ver. 2.00+` Single-Card Fallback & `[Shockless WB]` `Off/1/2/3` + Immediate `0`-Frame Bypass
for `[C.Temp./Filter]` Kelvin and `A-B / G-M` Fine-Grid Shifts),
and 74-Gate Master Safety Preflight (`G01..G74` / `verify-74-gates` / `run_74_gate_preflight`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    evaluate_58gate_preflight,
)
from fx3_safety.realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    evaluate_60gate_preflight,
)
from fx3_safety.realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    evaluate_62gate_preflight,
)
from fx3_safety.realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    evaluate_64gate_preflight,
)
from fx3_safety.realhw_nouvc_dcc1_pd_lut_path_and_66gate_guard import (
    evaluate_66gate_preflight,
)
from fx3_safety.realhw_usblan_rtmp_clipflag_anamorphic_and_68gate_guard import (
    evaluate_68gate_preflight,
)
from fx3_safety.realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard import (
    evaluate_70gate_preflight,
)
from fx3_safety.realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard import (
    Master72GateReport,
    evaluate_72gate_preflight,
)
from fx3_safety.realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard import (
    ALLOWED_DESQUEEZE_MENU_OPTIONS,
    ALLOWED_FOCUS_MAP_RENDER_TARGETS_G73,
    ALLOWED_REC_MEDIA_MODES_G74,
    ALLOWED_SHOCKLESS_WB_LEVELS,
    ALLOWED_WB_OPERATION_TYPES,
    CTEMP_KELVIN_MAX,
    CTEMP_KELVIN_MIN,
    DESQUEEZE_15X_16X_MIN_FW_VERSION,
    DESQUEEZE_16X_ACTUAL_STRETCH_FACTOR,
    DESQUEEZE_16X_TARGET_ASPECT,
    DESQUEEZE_MENU_PATH,
    DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR,
    DESQUEEZE_REQUIRED_4_LOCKS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FOCUS_MAP_CUTOFF_MIN_FPS,
    G73,
    G73_GATE_CODE,
    G73_GATE_ID,
    G74,
    G74_GATE_CODE,
    G74_GATE_ID,
    GATE_G73_FX3_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUSMAP_GUARD,
    GATE_G74_SIMULT_AUTOSWITCH_DUAL_VAULT_PARITY_AND_SHOCKLESS_WB_GUARD,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE206_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_SCHEMA,
    REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_VERSION,
    REC_MEDIA_MODE_SIMULTANEOUS,
    SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS,
    SHOCKLESS_WB_NOMINAL_RAMP_FRAMES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION,
    STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH,
    STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION,
    STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION,
    STATUS_BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN,
    STATUS_BLOCKED_G73_TELEMETRY_INVALID,
    STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH,
    STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD,
    STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION,
    STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID,
    STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF,
    STATUS_BLOCKED_G74_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY,
    STATUS_VERIFIED_G73,
    STATUS_VERIFIED_G74,
    WB_OP_AB_GM_GRID_SHIFT,
    WB_OP_CTEMP_KELVIN_EDIT,
    WB_OP_PRESET_SWITCH,
    audit_phase206_donor_contracts,
    compute_desqueeze_auto_suppression_reasons,
    evaluate_74_master_safety_gates,
    evaluate_74gate_preflight,
    evaluate_g73_desqueeze_focusmap_guard,
    evaluate_g74_simult_autoswitch_shocklesswb_guard,
    main as module_cli_main,
    resolve_desqueeze_horizontal_factor,
    run_74_gate_preflight,
    validate_fx3_desqueeze_4locks_and_suppression,
    validate_fx3_external_only_mc_focus_map_cutoff,
    validate_shockless_wb_and_immediate_kelvin_grid_bypass,
    validate_simult_recording_autoswitch_parity,
    verify_fx3_desqueeze_4locks_and_external_focusmap_guard,
    verify_simult_autoswitch_parity_and_shockless_wb_guard,
)


class TestPhase206DeSqueezeFocusMapSimultShocklessWb74GateGuard(unittest.TestCase):
    """56 dual-mode unit tests for Phase 206 Gates G73, G74, and `verify-74-gates`."""

    suite_start_monotonic: float
    cached_m74_offline: fx3_safety.Master74GateReport
    cached_m72_clean: Master72GateReport
    cached_m72_dry: Master72GateReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_start_monotonic = time.monotonic()
        cls.cached_m74_offline = evaluate_74gate_preflight(DEFAULT_REPO_ROOT)
        cls.cached_m72_clean = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True
        )
        cls.cached_m72_dry = evaluate_72gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )

    # ------------------------------------------------------------------
    # 1. Hard-Locked Safety Redlines, Exports & Donor Audit (Tests 01-08)
    # ------------------------------------------------------------------

    def test_01_hard_locked_redline_constants_and_gate_codes(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(G73, GATE_G73_FX3_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUSMAP_GUARD)
        self.assertEqual(G74, GATE_G74_SIMULT_AUTOSWITCH_DUAL_VAULT_PARITY_AND_SHOCKLESS_WB_GUARD)
        self.assertEqual(DESQUEEZE_16X_ACTUAL_STRETCH_FACTOR, 1.65)
        self.assertEqual(DESQUEEZE_16X_TARGET_ASPECT, "2.39:1_CINEMASCOPE")

    def test_02_package_top_level_exports_complete(self) -> None:
        expected_symbols = (
            "G73",
            "G73_GATE_ID",
            "G73_GATE_CODE",
            "G74",
            "G74_GATE_ID",
            "G74_GATE_CODE",
            "Master74GateReport",
            "evaluate_g73_desqueeze_focusmap_guard",
            "evaluate_g74_simult_autoswitch_shocklesswb_guard",
            "evaluate_74gate_preflight",
            "evaluate_74_master_safety_gates",
            "run_74_gate_preflight",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    def test_03_donor_audit_default_mode_strictly_o_rdonly(self) -> None:
        res = audit_phase206_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes", "on"):
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)
        else:
            self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_04_donor_audit_forced_clean_room_and_env_override(self) -> None:
        res_arg = audit_phase206_donor_contracts(force_clean_room=True)
        self.assertTrue(res_arg.valid)
        self.assertEqual(res_arg.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_arg.files_inspected, 0)
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res_env = audit_phase206_donor_contracts()
            self.assertTrue(res_env.valid)
            self.assertEqual(res_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_missing_work_root_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase206_donor_contracts(work_root=Path(tmp))
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_corrupted_synthetic_tree_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, toks, _lbl) in PINNED_PHASE206_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"CORRUPT_" + b"_".join(toks))
            res = audit_phase206_donor_contracts(work_root=root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE206_DONOR_INTEGRITY)
            self.assertGreater(len(res.errors), 0)

    def test_07_donor_audit_missing_marker_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, _toks, _lbl) in PINNED_PHASE206_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"EMPTY_NO_MARKERS")
            res = audit_phase206_donor_contracts(work_root=root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(len(res.missing_markers), len(PINNED_PHASE206_DONOR_SPECS))

    def test_08_donor_audit_json_never_leaks_raw_bytes(self) -> None:
        res = audit_phase206_donor_contracts(force_clean_room=True)
        serialized = json.dumps(res.to_dict())
        self.assertNotIn("b'", serialized)
        self.assertNotIn("\\x7fELF", serialized)

    # ------------------------------------------------------------------
    # 2. Gate G73 — [De-Squeeze Display] & External M&C Focus Map (Tests 09-26)
    # ------------------------------------------------------------------

    def test_09_g73_resolve_desqueeze_horizontal_factors_exact(self) -> None:
        self.assertEqual(resolve_desqueeze_horizontal_factor("Off"), 1.0)
        self.assertEqual(resolve_desqueeze_horizontal_factor("1.3x"), 1.3)
        self.assertEqual(resolve_desqueeze_horizontal_factor("2.0x"), 2.0)
        self.assertEqual(resolve_desqueeze_horizontal_factor("1.5x"), 1.5)
        self.assertEqual(resolve_desqueeze_horizontal_factor("1.6x"), 1.65)
        self.assertIsNone(resolve_desqueeze_horizontal_factor("1.8x"))
        self.assertEqual(len(ALLOWED_DESQUEEZE_MENU_OPTIONS), 5)

    def test_10_g73_default_16x_maps_to_165x_with_4_locks_verified(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G73)
        self.assertEqual(res.desqueeze_menu_path, DESQUEEZE_MENU_PATH)
        self.assertEqual(res.canonical_desqueeze_option, "1.6X")
        self.assertEqual(res.nominal_horizontal_factor, 1.65)
        self.assertEqual(res.effective_horizontal_factor, 1.65)
        self.assertTrue(res.four_locks_enforced)
        self.assertTrue(res.desqueeze_display_engaged)
        self.assertFalse(res.desqueeze_auto_suppressed)

    def test_11_g73_16x_claiming_160_instead_of_165_fails_closed(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.6x",
            effective_horizontal_factor=1.60,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH)

    def test_12_g73_all_five_desqueeze_options_and_fw_floors(self) -> None:
        for opt, factor in DESQUEEZE_OPTION_TO_HORIZONTAL_FACTOR.items():
            res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
                desqueeze_menu_option=opt,
                firmware_version="7.02",
            )
            self.assertTrue(res.valid, msg=f"Failed for {opt}")
            expected_eff = 1.0 if opt == "OFF" else factor
            self.assertEqual(res.effective_horizontal_factor, expected_eff)

        # 1.5x and 1.6x require Ver. >= 7.00, while 1.3x/2.0x pass on Ver. 6.01
        res_601_13x = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.3x", firmware_version="6.01"
        )
        self.assertTrue(res_601_13x.valid)
        for v7_only in ("1.5x", "1.6x"):
            res_old = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
                desqueeze_menu_option=v7_only, firmware_version="6.01"
            )
            self.assertFalse(res_old.valid)
            self.assertEqual(res_old.status, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH)
        self.assertEqual(DESQUEEZE_15X_16X_MIN_FW_VERSION, "7.00")

    def test_13_g73_unsupported_desqueeze_option_and_non_fx3_body_blocked(self) -> None:
        res_opt = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.8x"
        )
        self.assertFalse(res_opt.valid)
        self.assertEqual(res_opt.status, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH)

        res_body = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            body_model_name=FX3A_MODEL_NAME
        )
        self.assertFalse(res_body.valid)
        self.assertEqual(res_body.status, STATUS_BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH)

    def test_14_g73_lock1_focus_mode_non_mf_blocked(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.5x", focus_mode="AF-C"
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION)
        self.assertEqual(DESQUEEZE_REQUIRED_4_LOCKS["focus_mode"], "MANUAL_FOCUS")

    def test_15_g73_lock2_focus_area_non_wide_blocked(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="2.0x", focus_area="Tracking: Spot M"
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION)

    def test_16_g73_lock3_steadyshot_active_or_standard_blocked(self) -> None:
        for ss_mode in ("Active", "Standard"):
            res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
                desqueeze_menu_option="1.6x", steadyshot=ss_mode
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION)

    def test_17_g73_lock4_face_priority_in_multi_metering_on_blocked(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.3x", face_priority_in_multi_metering="On"
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION)

    def test_18_g73_desqueeze_off_unlocks_afc_steadyshot_and_face_priority(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="Off",
            focus_mode="AF-C",
            focus_area="Zone",
            steadyshot="Active",
            face_priority_in_multi_metering="On",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.desqueeze_display_engaged)
        self.assertEqual(res.effective_horizontal_factor, 1.0)

    def test_19_g73_auto_suppression_under_hdmi_raw_log_off_remote_still(self) -> None:
        reasons = compute_desqueeze_auto_suppression_reasons(
            hdmi_raw_output_on=True,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            log_shooting_on=False,
            remote_shooting_active=True,
            shooting_mode="Still",
        )
        self.assertEqual(len(reasons), 5)

        # Valid auto-suppression under HDMI RAW Output = On (forces 1.0x unscaled)
        res_raw = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.6x",
            hdmi_raw_output_on=True,
        )
        self.assertTrue(res_raw.valid)
        self.assertTrue(res_raw.desqueeze_auto_suppressed)
        self.assertFalse(res_raw.desqueeze_display_engaged)
        self.assertEqual(res_raw.effective_horizontal_factor, 1.0)

        # Claiming desqueeze remains engaged while HDMI RAW is On -> fail closed!
        res_bad = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.6x",
            hdmi_raw_output_on=True,
            desqueeze_display_engaged=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION
        )

    def test_20_g73_off_hdmi_only_enforces_hdmi_info_display_off_and_no_pixel_stretch(self) -> None:
        res_ok = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.5x",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_info_display_on=False,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.desqueeze_auto_suppressed)

        res_info_on = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="1.5x",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_info_display_on=True,
        )
        self.assertFalse(res_info_on.valid)
        self.assertEqual(
            res_info_on.status, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION
        )

        res_essence = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            recorded_essence_desqueezed=True
        )
        self.assertFalse(res_essence.valid)
        self.assertEqual(
            res_essence.status, STATUS_BLOCKED_G73_DESQUEEZE_SUPPRESSION_OR_ESSENCE_MUTATION
        )

    def test_21_g73_in_body_fx3_focus_map_menu_or_stageb_overlay_blocked(self) -> None:
        self.assertEqual(ALLOWED_FOCUS_MAP_RENDER_TARGETS_G73, ("EXTERNAL_MC_APP", "DISABLED"))
        for kwargs in (
            {"in_body_fx3_focus_map_menu_claimed": True},
            {"stageb_local_focus_map_overlay_injected": True},
            {"focus_map_render_target": "IN_BODY_LCD"},
            {"focus_map_render_target": "LOCAL_HDMI_OSD"},
        ):
            res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(**kwargs)
            self.assertFalse(res.valid, msg=f"Should fail for {kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN)

    def test_22_g73_external_mc_focus_map_150fps_200fps_240fps_cutoff_blocked(self) -> None:
        self.assertEqual(FOCUS_MAP_CUTOFF_MIN_FPS, 150.0)
        # 1fps, 6fps, 23.98p, 59.94p, 119.88p, 120fps all pass on ILME-FX3 (<=6fps floor is FX6-only)
        for valid_fps in (1.0, 6.0, 23.98, 59.94, 119.88, 120.0):
            ok, _c, _e = validate_fx3_external_only_mc_focus_map_cutoff(frame_rate_fps=valid_fps)
            self.assertTrue(ok, msg=f"Valid FX3 fps={valid_fps} should pass")

        # >= 150fps hard-disabled
        for high_fps in (150.0, 200.0, 240.0):
            res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
                frame_rate_fps=high_fps, external_mc_focus_map_active=True
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION)

    def test_23_g73_external_mc_focus_map_adapter_non_pdaf_and_playback_blocked(self) -> None:
        for bad_kwargs in (
            {"lens_attached": False},
            {"mount_adapter_attached": True},
            {"pdaf_capable_lens": False},
            {"camera_playback_mode": True},
            {"shooting_mode": "Playback"},
            {"firmware_version": "5.00", "desqueeze_menu_option": "1.3x"},
            {"monitor_control_app_version": "1.2.0"},
        ):
            res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
                external_mc_focus_map_active=True, **bad_kwargs
            )
            self.assertFalse(res.valid, msg=f"Expected cutoff block for {bad_kwargs}")
            self.assertEqual(res.status, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION)

    def test_24_g73_high_fps_allowed_when_external_focus_map_disabled(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            frame_rate_fps=240.0,
            external_mc_focus_map_active=False,
            focus_map_render_target="DISABLED",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G73)

    def test_25_g73_invalid_telemetry_fails_closed(self) -> None:
        res = verify_fx3_desqueeze_4locks_and_external_focusmap_guard(
            desqueeze_menu_option="",  # empty string
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G73_TELEMETRY_INVALID)

        ok, _c, _e = validate_fx3_desqueeze_4locks_and_suppression(
            desqueeze_menu_option="1.6x", effective_horizontal_factor=1.65
        )
        self.assertTrue(ok)

    def test_26_g73_evaluator_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g73_desqueeze_focusmap_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.gate_id, G73_GATE_ID)
        self.assertEqual(verdict.gate_code, G73_GATE_CODE)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # 3. Gate G74 — [Simult. + Auto Switch] & [Shockless WB] (Tests 27-44)
    # ------------------------------------------------------------------

    def test_27_g74_default_strict_dual_vault_parity_verified(self) -> None:
        res = verify_simult_autoswitch_parity_and_shockless_wb_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G74)
        self.assertEqual(res.canonical_rec_media_mode, REC_MEDIA_MODE_SIMULTANEOUS)
        self.assertFalse(res.auto_switch_media_enabled)
        self.assertTrue(res.strict_dual_vault_parity_required)
        self.assertEqual(res.modeled_dual_slot_state, "STRICT_DUAL_SLOT_PARITY_LOCKED")
        self.assertEqual(res.active_recording_slot_count, 2)
        self.assertIn(REC_MEDIA_MODE_SIMULTANEOUS, ALLOWED_REC_MEDIA_MODES_G74)

    def test_28_g74_strict_dual_vault_blocks_auto_switch_media_on(self) -> None:
        res = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
            strict_dual_vault_parity_required=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF
        )

    def test_29_g74_strict_dual_vault_blocks_single_slot_prioritize_mode(self) -> None:
        res = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            rec_media_mode="Prioritize Slot 1",
            auto_switch_media="Off",
            strict_dual_vault_parity_required=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF
        )

    def test_30_g74_strict_dual_vault_blocks_slot_full_or_missing_card(self) -> None:
        for degraded_kwargs in (
            {"slot1_full": True, "active_recording_slot_count": 1, "single_card_fallback_active": True},
            {"slot2_full": True},
            {"slot2_card_present_writable": False},
            {"active_recording_slot_count": 1},
            {"single_card_fallback_active": True},
        ):
            res = verify_simult_autoswitch_parity_and_shockless_wb_guard(
                strict_dual_vault_parity_required=True,
                auto_switch_media="Off",
                **degraded_kwargs,
            )
            self.assertFalse(res.valid, msg=f"Should block degraded parity: {degraded_kwargs}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD
            )

    def test_31_g74_non_strict_marathon_autoswitch_on_warns_on_single_card_fallback(self) -> None:
        # Both cards healthy: 2 slots active, zero warnings
        res_dual = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            strict_dual_vault_parity_required=False,
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_full=False,
            slot2_full=False,
            active_recording_slot_count=2,
            single_card_fallback_active=False,
        )
        self.assertTrue(res_dual.valid)
        self.assertEqual(res_dual.modeled_dual_slot_state, "DUAL_SLOT_MARATHON_ACTIVE")
        self.assertEqual(len(res_dual.warnings), 0)

        # Slot 1 full -> Ver. 2.00+ degrades to single-card recording on Slot 2 with warning
        res_fb = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            strict_dual_vault_parity_required=False,
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_full=True,
            slot2_full=False,
            active_recording_slot_count=1,
            single_card_fallback_active=True,
        )
        self.assertTrue(res_fb.valid)
        self.assertEqual(res_fb.modeled_dual_slot_state, "SINGLE_CARD_FALLBACK_ACTIVE")
        self.assertEqual(len(res_fb.warnings), 1)
        self.assertIn("SINGLE-CARD", res_fb.warnings[0])

    def test_32_g74_non_strict_autoswitch_both_slots_full_or_pre_v200_blocked(self) -> None:
        res_both_full = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            strict_dual_vault_parity_required=False,
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_full=True,
            slot2_full=True,
            active_recording_slot_count=0,
            single_card_fallback_active=False,
        )
        self.assertFalse(res_both_full.valid)
        self.assertEqual(
            res_both_full.status, STATUS_BLOCKED_G74_DUAL_SLOT_PARITY_DEGRADED_SINGLE_CARD
        )

        res_old_fw = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            firmware_version="1.01",
            strict_dual_vault_parity_required=False,
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
        )
        self.assertFalse(res_old_fw.valid)
        self.assertEqual(
            res_old_fw.status, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH
        )

    def test_33_g74_non_strict_autoswitch_slot_count_mismatch_blocked(self) -> None:
        ok, code, _st, _e, _w = validate_simult_recording_autoswitch_parity(
            strict_dual_vault_parity_required=False,
            rec_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_full=True,
            slot2_full=False,
            active_recording_slot_count=2,  # impossible when Slot 1 is full!
            single_card_fallback_active=False,
        )
        self.assertFalse(ok)
        self.assertEqual(code, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH)

    def test_34_g74_shockless_wb_all_levels_across_24p_to_240fps(self) -> None:
        self.assertEqual(ALLOWED_SHOCKLESS_WB_LEVELS, ("OFF", "1", "2", "3"))
        for lvl in ("Off", "1", "2", "3"):
            for fps in (1.0, 23.98, 24.0, 29.97, 59.94, 119.88, 200.0, 240.0):
                res = verify_simult_autoswitch_parity_and_shockless_wb_guard(
                    shockless_wb_setting=lvl,
                    frame_rate_fps=fps,
                    wb_operation_type=WB_OP_PRESET_SWITCH,
                )
                self.assertTrue(res.valid, msg=f"Failed for level={lvl}, fps={fps}")
                canon = "OFF" if lvl == "Off" else lvl
                self.assertEqual(
                    res.observed_wb_ramp_frames, SHOCKLESS_WB_NOMINAL_RAMP_FRAMES[canon]
                )

    def test_35_g74_shockless_wb_ctemp_kelvin_edit_enforces_zero_frame_bypass(self) -> None:
        self.assertIn(WB_OP_CTEMP_KELVIN_EDIT, SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS)
        self.assertEqual(CTEMP_KELVIN_MIN, 2500)
        self.assertEqual(CTEMP_KELVIN_MAX, 9900)
        # Valid 0-frame immediate bypass even when Shockless WB = 3 (Slow)
        res_ok = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="3 (Slow)",
            wb_operation_type="CTEMP_KELVIN_EDIT",
            ctemp_kelvin=4300,
            observed_wb_ramp_frames=0,
            immediate_zero_frame_bypass_observed=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.immediate_zero_frame_bypass_required)
        self.assertTrue(res_ok.immediate_zero_frame_bypass_observed)
        self.assertEqual(res_ok.observed_wb_ramp_frames, 0)

        # Claiming smoothed non-zero ramp frames on C.Temp./Filter Kelvin edit -> fail closed!
        res_bad = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="3",
            wb_operation_type="CTEMP_KELVIN_EDIT",
            ctemp_kelvin=4300,
            observed_wb_ramp_frames=48,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION
        )

    def test_36_g74_shockless_wb_ab_gm_grid_shift_enforces_zero_frame_bypass(self) -> None:
        self.assertIn(WB_OP_AB_GM_GRID_SHIFT, SHOCKLESS_WB_IMMEDIATE_BYPASS_OPS)
        res_ok = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="2",
            wb_operation_type="AB_GM_GRID_SHIFT",
            ab_fine_shift=-3,
            gm_fine_shift=2,
            observed_wb_ramp_frames=0,
        )
        self.assertTrue(res_ok.valid)

        res_bad = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="2",
            wb_operation_type="AB_GM_GRID_SHIFT",
            ab_fine_shift=-3,
            gm_fine_shift=2,
            observed_wb_ramp_frames=12,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION
        )

    def test_37_g74_preset_switch_ramp_consistency_enforced(self) -> None:
        # Shockless WB = 1/2/3 with 0 ramp frames on preset switch -> fail closed
        res_zero = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="1",
            wb_operation_type=WB_OP_PRESET_SWITCH,
            observed_wb_ramp_frames=0,
        )
        self.assertFalse(res_zero.valid)
        self.assertEqual(
            res_zero.status, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION
        )

        # Shockless WB = Off with non-zero ramp frames -> fail closed
        res_off_nonzero = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting="Off",
            wb_operation_type=WB_OP_PRESET_SWITCH,
            observed_wb_ramp_frames=15,
        )
        self.assertFalse(res_off_nonzero.valid)
        self.assertEqual(
            res_off_nonzero.status, STATUS_BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION
        )

    def test_38_g74_invalid_shockless_wb_level_fps_kelvin_or_grid_blocked(self) -> None:
        self.assertEqual(len(ALLOWED_WB_OPERATION_TYPES), 3)
        for bad_kwargs in (
            {"shockless_wb_setting": "4"},
            {"shockless_wb_setting": "Auto"},
            {"frame_rate_fps": 0.0},
            {"frame_rate_fps": 300.0},
            {"ctemp_kelvin": 2000},
            {"ctemp_kelvin": 10500},
            {"ab_fine_shift": 12},
            {"gm_fine_shift": -10},
            {"wb_operation_type": "UNKNOWN_WB_OP"},
        ):
            ok, code, _e = validate_shockless_wb_and_immediate_kelvin_grid_bypass(**bad_kwargs)
            self.assertFalse(ok, msg=f"Expected invalid setting block for {bad_kwargs}")
            self.assertEqual(code, STATUS_BLOCKED_G74_SHOCKLESS_WB_SETTING_OR_FPS_INVALID)

    def test_39_g74_non_fx3_body_and_invalid_rec_mode_blocked(self) -> None:
        res_body = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            body_model_name=FX3A_MODEL_NAME
        )
        self.assertFalse(res_body.valid)
        self.assertEqual(
            res_body.status, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH
        )

        res_mode = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            rec_media_mode="RAID0_STRIPE"
        )
        self.assertFalse(res_mode.valid)
        self.assertEqual(
            res_mode.status, STATUS_BLOCKED_G74_AUTOSWITCH_FIRMWARE_OR_STATE_MISMATCH
        )

    def test_40_g74_invalid_telemetry_fails_closed(self) -> None:
        res = verify_simult_autoswitch_parity_and_shockless_wb_guard(
            shockless_wb_setting=True,  # type: ignore[arg-type]
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G74_TELEMETRY_INVALID)

    def test_41_g74_evaluator_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g74_simult_autoswitch_shocklesswb_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.gate_id, G74_GATE_ID)
        self.assertEqual(verdict.gate_code, G74_GATE_CODE)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # 4. Master 74-Gate Preflight, CLI & Backward Compat (Tests 42-56)
    # ------------------------------------------------------------------

    def test_42_master_74gate_offline_default_71_of_74(self) -> None:
        rep = self.cached_m74_offline
        self.assertEqual(rep.schema, REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_SCHEMA)
        self.assertEqual(rep.version, REALHW_DESQUEEZE_FOCUSMAP_SIMULT_SHOCKLESSWB_74GATE_VERSION)
        self.assertEqual(rep.summary["total_gates"], 74)
        self.assertEqual(rep.summary["verified_gates"], 71)
        self.assertEqual(rep.technical_gates_passed, 71)
        self.assertTrue(rep.offline_71_gates_verified)
        self.assertFalse(rep.all_74_gates_verified)
        self.assertTrue(rep.g13_to_g74_all_passed)
        self.assertTrue(rep.g73_to_g74_all_passed)
        self.assertEqual(rep.status, "VERIFIED_71_OF_74_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(rep.gates), 74)

    def test_43_master_74gate_forced_clean_room_71_of_74(self) -> None:
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            master_72_override=self.cached_m72_clean,
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_71_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 71)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_44_master_74gate_dry_run_simulated_74_of_74_still_locks_attach_false(self) -> None:
        rep = run_74_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_72_override=self.cached_m72_dry,
        )
        self.assertTrue(rep.all_74_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 74)
        self.assertEqual(rep.status, "VERIFIED_ALL_74_GATES_DRY_RUN_SIMULATED_BACKUP")
        # Physical hardware attach MUST remain hard-locked False!
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertTrue(rep.agent_auto_flash_blocked)

    def test_45_master_74gate_aliases_and_dry_run_backup_flag(self) -> None:
        self.assertIs(evaluate_74_master_safety_gates, evaluate_74gate_preflight)
        self.assertIs(run_74_gate_preflight, evaluate_74gate_preflight)
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_72_override=self.cached_m72_dry,
        )
        self.assertTrue(rep.all_74_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)

    def test_46_master_74gate_propagates_g73_failure(self) -> None:
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            desqueeze_focusmap_kwargs={"frame_rate_fps": 240.0, "external_mc_focus_map_active": True},
            master_72_override=self.cached_m72_clean,
        )
        self.assertFalse(rep.offline_71_gates_verified)
        self.assertFalse(rep.g73_to_g74_all_passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION)

    def test_47_master_74gate_propagates_g74_failure(self) -> None:
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simult_autoswitch_shocklesswb_kwargs={
                "strict_dual_vault_parity_required": True,
                "auto_switch_media": "On",
            },
            master_72_override=self.cached_m72_clean,
        )
        self.assertFalse(rep.offline_71_gates_verified)
        self.assertFalse(rep.g73_to_g74_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF
        )

    def test_48_master_74gate_blocks_persistent_emmc_write_redline(self) -> None:
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_72_override=self.cached_m72_clean,
        )
        self.assertFalse(rep.offline_71_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_49_cli_verify_g73_desqueeze_focusmap_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g73-desqueeze-focusmap", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("desqueeze=1.6X->1.65x", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = package_cli_main(["verify-g73-desqueeze-focusmap", "--force-clean-room", "--json"])
        self.assertEqual(rc_j, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["desqueeze_focusmap_guard"]["effective_horizontal_factor"], 1.65)

    def test_50_cli_verify_g74_simult_autoswitch_shocklesswb_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-g74-simult-autoswitch-shocklesswb", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("STRICT_DUAL_SLOT_PARITY_LOCKED", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = package_cli_main(
                ["verify-g74-simult-autoswitch-shocklesswb", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])

    def test_51_cli_verify_74_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-74-gates", "--force-clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=71/74", buf_off.getvalue())

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-74-gates", "--force-clean-room", "--dry-run-simulated", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        payload = json.loads(buf_dry.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 74)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_52_module_cli_main_entrypoint(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=74/74", buf.getvalue())

    def test_53_backward_compatibility_58_to_72_gates_intact(self) -> None:
        checks = (
            (evaluate_58gate_preflight, 58, 55, "offline_55_gates_verified"),
            (evaluate_60gate_preflight, 60, 57, "offline_57_gates_verified"),
            (evaluate_62gate_preflight, 62, 59, "offline_59_gates_verified"),
            (evaluate_64gate_preflight, 64, 61, "offline_61_gates_verified"),
            (evaluate_66gate_preflight, 66, 63, "offline_63_gates_verified"),
            (evaluate_68gate_preflight, 68, 65, "offline_65_gates_verified"),
            (evaluate_70gate_preflight, 70, 67, "offline_67_gates_verified"),
            (evaluate_72gate_preflight, 72, 69, "offline_69_gates_verified"),
        )
        for fn, total, expected_off, attr_name in checks:
            rep = fn(DEFAULT_REPO_ROOT, force_clean_room=True)
            self.assertEqual(rep.summary["total_gates"], total)
            self.assertEqual(rep.summary["verified_gates"], expected_off)
            self.assertTrue(getattr(rep, attr_name))
            self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_54_backward_compatibility_cli_verify_72_gates(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-72-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=69/72", buf.getvalue())

    def test_55_json_serialization_zero_raw_firmware_bytes(self) -> None:
        rep = evaluate_74gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            master_72_override=self.cached_m72_clean,
        )
        raw_json = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'", raw_json)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)

    def test_56_suite_wall_clock_ceiling_under_6_seconds(self) -> None:
        elapsed = time.monotonic() - self.suite_start_monotonic
        self.assertLess(
            elapsed,
            6.0,
            msg=f"Phase 206 test suite exceeded 6.0s wall-clock ceiling: {elapsed:.3f}s",
        )


if __name__ == "__main__":
    unittest.main()
