"""Phase 246 Dual-Mode Unit Tests (`>=62` tests; 66 tests implemented) for
`fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard`:

- Gate `G93`: `ILME-FX3` (`Ver. 7.02`) `[Framing Settings]` Asymmetric `Full`/`Crop`
  Stream Guard & `[Anti-flicker Shoot.]` Mechanical-Still-Only / No-`Var. Shutter`
  Firewall.
- Gate `G94`: `ILME-FX3` (`Ver. 7.02`) `[USB Power Supply]` Mandatory `NP-FZ100`
  Insertion + `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single`
  Setup Persistence Guard.
- Unified `94`-Gate Master Safety Preflight (`evaluate_94gate_preflight` /
  `verify-94-gates`): `91/94` offline awaiting physical Tier-0 receipt and
  `94/94` in `--simulate-bench-dry-run` with all hardware write/live-attach
  redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard import (
    ALLOWED_ANTI_FLICKER_SHOOT_MODES,
    ALLOWED_BATTERY_BAY_SOURCES_G94,
    ALLOWED_FRAMING_MODES,
    ALLOWED_FRAMING_STREAM_OUTPUTS,
    ALLOWED_RESET_ACTIONS_PHASE246,
    ALLOWED_SHOOT_MODES_G93,
    ALLOWED_SHUTTER_TYPES_G93,
    ALLOWED_USB_CONNECTION_MODES_G94,
    ALLOWED_USB_LUN_SETTINGS_G94,
    ALLOWED_USB_POWER_PORTS_G94,
    ALLOWED_USB_POWER_SUPPLY_MODES_G94,
    ANTI_FLICKER_DETECTED_MAINS_HZ,
    ANTI_FLICKER_SHOOT_FACTORY_DEFAULT,
    ANTI_FLICKER_SHOOT_MENU_PATH,
    ANTI_FLICKER_SHOOT_OFF,
    ANTI_FLICKER_SHOOT_ON,
    BATTERY_BAY_DC_C1_COUPLER_G94,
    BATTERY_BAY_EMPTY_G94,
    BATTERY_BAY_NP_FZ100_G94,
    DONOR_CHECK_MAX_SECONDS_PHASE246,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FRAMING_FACTORY_DEFAULT,
    FRAMING_HDMI_FACTORY_DEFAULT,
    FRAMING_MODE_OFF,
    FRAMING_MODE_ON,
    FRAMING_OUTPUT_CROP,
    FRAMING_OUTPUT_FULL,
    FRAMING_REC_STREAMING_FACTORY_DEFAULT,
    FRAMING_SETTINGS_MENU_PATH,
    FX30_HELP_GUIDE_CODE_G93,
    FX3_DEFAULT_FW_VERSION_PHASE246,
    FX3_HAS_FX6_ECS_MENU,
    FX3_HAS_VAR_SHUTTER,
    FX3_HELP_GUIDE_CODE_G93,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE246,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    G93,
    G93_GATE_CODE,
    G93_GATE_ID,
    G94,
    G94_GATE_CODE,
    G94_GATE_ID,
    GATE_G93_FRAMING_ASYMMETRIC_CROP_FULL_AND_ANTIFLICKER_NO_VARSHUTTER_GUARD,
    GATE_G94_USB_POWER_NPFZ100_TYPEC_INTERLOCK_AND_USB_LUN_SETUP_PERSISTENCE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE246_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA,
    REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_VERSION,
    REJECTED_VAR_SHUTTER_AND_ECS_MODELS_G93,
    REJECTED_ZVE1_AUTOFRAMING_LABELS,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SHOOT_MODE_MOVIE_G93,
    SHOOT_MODE_SQ_MOTION_G93,
    SHOOT_MODE_STILL_G93,
    SHUTTER_TYPE_ELECTRONIC_G93,
    SHUTTER_TYPE_MECHANICAL_G93,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
    STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION,
    STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT,
    STATUS_BLOCKED_G93_TELEMETRY_INVALID,
    STATUS_BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION,
    STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN,
    STATUS_BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF,
    STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED,
    STATUS_BLOCKED_G94_TELEMETRY_INVALID,
    STATUS_BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH,
    STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE,
    STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY,
    STATUS_VERIFIED_G93,
    STATUS_VERIFIED_G94,
    USB_CONNECTION_MODE_FACTORY_DEFAULT_G94,
    USB_CONNECTION_MODE_MENU_PATH_G94,
    USB_CONN_LAN_WIRED_G94,
    USB_CONN_MASS_STORAGE_MSC_G94,
    USB_CONN_MTP_G94,
    USB_CONN_PC_REMOTE_G94,
    USB_CONN_SEL_WHEN_CONNECT_G94,
    USB_LUN_MULTI_G94,
    USB_LUN_SETTING_FACTORY_DEFAULT_G94,
    USB_LUN_SETTING_MENU_PATH_G94,
    USB_LUN_SINGLE_G94,
    USB_PACKETS_TRANSMITTED,
    USB_PORT_MULTI_MICRO_G94,
    USB_PORT_NONE_G94,
    USB_PORT_TYPE_C_G94,
    USB_POWER_SUPPLY_FACTORY_DEFAULT_G94,
    USB_POWER_SUPPLY_MENU_PATH_G94,
    USB_POWER_SUPPLY_OFF_G94,
    USB_POWER_SUPPLY_ON_G94,
    USB_SETUP_MENU_PATH_G94,
    ZVE1_HELP_GUIDE_CODE_G93,
    audit_phase246_donor_contracts,
    evaluate_94_master_safety_gates,
    evaluate_94gate_preflight,
    evaluate_g93_framing_and_antiflicker_guard,
    evaluate_g94_usb_power_and_lun_persistence_guard,
    main as module_main,
    resolve_fx3_framing_and_antiflicker_state,
    resolve_fx3_usb_power_interlock_and_lun_persistence_state,
    run_94_gate_preflight,
    verify_framing_asymmetric_and_antiflicker_no_varshutter_guard,
    verify_usb_power_npfz100_typec_and_lun_persistence_guard,
)


class TestPhase246FramingUsbPowerLunAntiflickerAnd94GateGuard(unittest.TestCase):
    """66 fast dual-mode tests covering Gates G93, G94, and unified 94-Gate preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        # Run unmocked evaluate_94gate_preflight() once in active environment mode
        # (LOCAL_DONOR_O_RDONLY when local donor is available, CLEAN_ROOM_SYNTHETIC
        # when FX3_FX6_FORCE_CLEAN_ROOM=1) and cache upstream 92-gate evaluations
        # so all 66 tests complete well under < 5s.
        cls.active_offline_94 = evaluate_94gate_preflight()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_92 = fx3_safety.evaluate_92gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_92 = fx3_safety.evaluate_92gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_94 = evaluate_94gate_preflight(
                force_clean_room=True, master_92_override=cls.clean_offline_92
            )
            cls.clean_dryrun_94 = evaluate_94gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_92_override=cls.clean_dryrun_92,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded `< 0.10s` Donor Audit (10 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G93, G93_GATE_ID)
        self.assertEqual(G94, G94_GATE_ID)
        self.assertEqual(
            G93_GATE_CODE,
            GATE_G93_FRAMING_ASYMMETRIC_CROP_FULL_AND_ANTIFLICKER_NO_VARSHUTTER_GUARD,
        )
        self.assertEqual(
            G94_GATE_CODE,
            GATE_G94_USB_POWER_NPFZ100_TYPEC_INTERLOCK_AND_USB_LUN_SETUP_PERSISTENCE_GUARD,
        )
        self.assertEqual(
            REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA,
            "realhw_framing_usbpower_lun_antiflicker_and_94gate_guard_v1",
        )
        self.assertEqual(
            REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_VERSION, "1.0.0"
        )
        self.assertFalse(FX3_HAS_VAR_SHUTTER)
        self.assertFalse(FX3_HAS_FX6_ECS_MENU)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_fx3_safety_init_exports_do_not_shadow_prior_phases(self) -> None:
        phase246_exports = (
            "realhw_framing_usbpower_lun_antiflicker_and_94gate_guard",
            "G93",
            "G94",
            "G93_GATE_ID",
            "G94_GATE_ID",
            "Master94GateReport",
            "evaluate_94gate_preflight",
            "evaluate_94_master_safety_gates",
            "run_94_gate_preflight",
            "evaluate_g93_framing_and_antiflicker_guard",
            "evaluate_g94_usb_power_and_lun_persistence_guard",
            "verify_framing_asymmetric_and_antiflicker_no_varshutter_guard",
            "verify_usb_power_npfz100_typec_and_lun_persistence_guard",
        )
        for sym in phase246_exports:
            self.assertEqual(
                fx3_safety.__all__.count(sym),
                1,
                msg=f"Expected exactly 1 entry for {sym} in __all__",
            )
            self.assertTrue(hasattr(fx3_safety, sym), msg=f"Missing {sym} attr")
        for prior_sym in (
            "G91",
            "G92",
            "evaluate_92gate_preflight",
            "G89",
            "G90",
            "evaluate_90gate_preflight",
        ):
            self.assertTrue(hasattr(fx3_safety, prior_sym))

    def test_03_pinned_donor_specs_structure_and_five_artifacts(self) -> None:
        self.assertEqual(len(PINNED_PHASE246_DONOR_SPECS), 5)
        self.assertIn("fx3_cpapp_bin", PINNED_PHASE246_DONOR_SPECS)
        self.assertIn("fx3_usb_buspower_so", PINNED_PHASE246_DONOR_SPECS)
        self.assertIn("fx3_msc_server_so", PINNED_PHASE246_DONOR_SPECS)
        self.assertIn("fx3_bk4_bin", PINNED_PHASE246_DONOR_SPECS)
        self.assertIn("fx6_bk4_bin", PINNED_PHASE246_DONOR_SPECS)
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE246, 0.10)

    def test_04_donor_audit_active_environment_o_rdonly_or_clean_room(self) -> None:
        res = audit_phase246_donor_contracts()
        self.assertTrue(res.valid)
        self.assertTrue(res.within_budget_100ms)
        self.assertLess(res.elapsed_seconds, 0.10)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() in ("1", "true", "TRUE"):
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)
        else:
            self.assertIn(
                res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
            )
            if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
                self.assertEqual(res.access_mode, "O_RDONLY")
                self.assertEqual(res.files_inspected, 5)

    def test_05_donor_audit_explicit_force_clean_room_parity(self) -> None:
        res = audit_phase246_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), 5)
        self.assertEqual(res.missing_markers, ())
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_env_var_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase246_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase246_donor_contracts(
                work_root=Path(tmp) / "nonexistent_donor_dir",
                force_clean_room=False,
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_08_donor_audit_corrupted_local_donor_blob_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, _markers, _lbl) in PINNED_PHASE246_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"corrupted_stub_without_valid_markers_or_sha")
            res = audit_phase246_donor_contracts(
                work_root=root, force_clean_room=False
            )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreater(len(res.errors), 0)

    def test_09_donor_audit_budget_exceeded_fails_closed(self) -> None:
        res = audit_phase246_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_100ms)

    def test_10_donor_audit_to_dict_serializable_without_raw_bytes(self) -> None:
        d = audit_phase246_donor_contracts(force_clean_room=True).to_dict()
        encoded = json.dumps(d)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", encoded)
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # Section B: Gate `G93` Framing Asymmetric Routing & Anti-flicker /
    #            No-Var. Shutter Firewall (18 tests: 11..28)
    # ------------------------------------------------------------------

    def test_11_g93_factory_defaults_and_menu_paths(self) -> None:
        self.assertEqual(FRAMING_FACTORY_DEFAULT, "Off")
        self.assertEqual(FRAMING_REC_STREAMING_FACTORY_DEFAULT, "Full")
        self.assertEqual(FRAMING_HDMI_FACTORY_DEFAULT, "Crop")
        self.assertEqual(ANTI_FLICKER_SHOOT_FACTORY_DEFAULT, "Off")
        self.assertEqual(ALLOWED_FRAMING_MODES, ("Off", "On"))
        self.assertEqual(ALLOWED_FRAMING_STREAM_OUTPUTS, ("Full", "Crop"))
        self.assertEqual(ALLOWED_ANTI_FLICKER_SHOOT_MODES, ("Off", "On"))
        self.assertEqual(ALLOWED_SHOOT_MODES_G93, ("Still", "Movie", "S&Q Motion"))
        self.assertEqual(ALLOWED_SHUTTER_TYPES_G93, ("Mechanical", "Electronic"))
        self.assertEqual(ALLOWED_RESET_ACTIONS_PHASE246[1], RESET_ACTION_CAMERA_SETTINGS_RESET)
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G93)
        self.assertEqual(res.framing_settings_menu_path, FRAMING_SETTINGS_MENU_PATH)
        self.assertEqual(res.anti_flicker_shoot_menu_path, ANTI_FLICKER_SHOOT_MENU_PATH)
        self.assertTrue(res.framing_asymmetric_factory_default_preserved)
        self.assertFalse(res.fx3_has_var_shutter)
        self.assertFalse(res.fx3_has_fx6_ecs_menu)

    def test_12_g93_framing_on_preserves_asymmetric_rec_full_hdmi_crop_routing(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing=FRAMING_MODE_ON,
            pre_reset_recording_streaming=FRAMING_OUTPUT_FULL,
            pre_reset_hdmi=FRAMING_OUTPUT_CROP,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_recording_streaming_routing, "Full")
        self.assertEqual(res.active_hdmi_routing, "Crop")

    def test_13_g93_framing_off_forces_uncropped_full_on_both_streams(self) -> None:
        state = resolve_fx3_framing_and_antiflicker_state(
            pre_reset_framing=FRAMING_MODE_OFF,
            pre_reset_recording_streaming=FRAMING_OUTPUT_CROP,
            pre_reset_hdmi=FRAMING_OUTPUT_CROP,
        )
        self.assertEqual(state["active_recording_streaming_routing"], "Full")
        self.assertEqual(state["active_hdmi_routing"], "Full")

    def test_14_g93_camera_settings_reset_restores_framing_and_antiflicker_defaults(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing="On",
            pre_reset_recording_streaming="Crop",
            pre_reset_hdmi="Full",
            pre_reset_anti_flicker_shoot="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_framing, "Off")
        self.assertEqual(res.effective_post_reset_recording_streaming, "Full")
        self.assertEqual(res.effective_post_reset_hdmi, "Crop")
        self.assertEqual(res.effective_post_reset_anti_flicker_shoot, "Off")

    def test_15_g93_initialize_restores_framing_and_antiflicker_defaults(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing="On",
            pre_reset_recording_streaming="Crop",
            pre_reset_hdmi="Full",
            pre_reset_anti_flicker_shoot="On",
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_framing, "Off")
        self.assertEqual(res.effective_post_reset_recording_streaming, "Full")
        self.assertEqual(res.effective_post_reset_hdmi, "Crop")
        self.assertEqual(res.effective_post_reset_anti_flicker_shoot, "Off")

    def test_16_g93_rejects_false_symmetric_factory_default_assumption(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            claimed_factory_recording_streaming_default="Full",
            claimed_factory_hdmi_default="Full",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION,
            res.violation_codes,
        )

    def test_17_g93_rejects_false_framing_survival_across_camera_settings_reset(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_framing="On",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION,
            res.violation_codes,
        )

    def test_18_g93_blocks_hdmi_raw_output_when_framing_on_with_hdmi_crop(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing="On",
            pre_reset_recording_streaming="Full",
            pre_reset_hdmi="Crop",
            hdmi_raw_output_enabled=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.hdmi_raw_framing_conflict_blocked)
        self.assertIn(
            STATUS_BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT,
            res.violation_codes,
        )

    def test_19_g93_allows_hdmi_raw_output_when_framing_is_off(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_framing="Off",
            hdmi_raw_output_enabled=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.hdmi_raw_framing_conflict_blocked)

    def test_20_g93_rejects_zve1_autoframing_settings_label_and_model_conflation(self) -> None:
        self.assertGreaterEqual(len(REJECTED_ZVE1_AUTOFRAMING_LABELS), 4)
        for bad_label in ("[Autoframing Settings]", "Autoframing Settings"):
            res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
                framing_menu_node_label=bad_label
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.zve1_autoframing_conflation_rejected)
            self.assertIn(
                STATUS_BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION,
                res.violation_codes,
            )
        res_guide = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            help_guide_code=ZVE1_HELP_GUIDE_CODE_G93
        )
        self.assertFalse(res_guide.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION,
            res_guide.violation_codes,
        )

    def test_21_g93_antiflicker_functions_strictly_in_mechanical_still_mode(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_anti_flicker_shoot=ANTI_FLICKER_SHOOT_ON,
            shoot_mode=SHOOT_MODE_STILL_G93,
            silent_mode="Off",
            shutter_type=SHUTTER_TYPE_MECHANICAL_G93,
            claimed_anti_flicker_functional=True,
            require_active_anti_flicker_mitigation=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.anti_flicker_mechanical_still_only_eligible)
        self.assertTrue(res.anti_flicker_functional)
        self.assertEqual(res.detected_mains_flicker_hz, (100, 120))
        self.assertEqual(ANTI_FLICKER_DETECTED_MAINS_HZ, (100, 120))

    def test_22_g93_antiflicker_non_functional_in_movie_and_sq_modes(self) -> None:
        for mode in (SHOOT_MODE_MOVIE_G93, SHOOT_MODE_SQ_MOTION_G93):
            res_dormant = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
                pre_reset_anti_flicker_shoot="On",
                shoot_mode=mode,
                silent_mode="Off",
                shutter_type="Mechanical",
            )
            self.assertTrue(res_dormant.valid)
            self.assertFalse(res_dormant.anti_flicker_functional)
            self.assertGreater(len(res_dormant.warnings), 0)

            res_bad = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
                pre_reset_anti_flicker_shoot="On",
                shoot_mode=mode,
                claimed_anti_flicker_functional=True,
            )
            self.assertFalse(res_bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
                res_bad.violation_codes,
            )

    def test_23_g93_antiflicker_non_functional_in_silent_mode_or_electronic_shutter(self) -> None:
        res_silent = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_anti_flicker_shoot="On",
            shoot_mode=SHOOT_MODE_STILL_G93,
            silent_mode="On",
            shutter_type=SHUTTER_TYPE_MECHANICAL_G93,
            require_active_anti_flicker_mitigation=True,
        )
        self.assertFalse(res_silent.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
            res_silent.violation_codes,
        )
        res_elec = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_anti_flicker_shoot="On",
            shoot_mode=SHOOT_MODE_STILL_G93,
            silent_mode="Off",
            shutter_type=SHUTTER_TYPE_ELECTRONIC_G93,
            require_active_anti_flicker_mitigation=True,
        )
        self.assertFalse(res_elec.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
            res_elec.violation_codes,
        )

    def test_24_g93_blocks_false_fx30_var_shutter_assumption_on_ilme_fx3(self) -> None:
        self.assertGreaterEqual(len(REJECTED_VAR_SHUTTER_AND_ECS_MODELS_G93), 3)
        res1 = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            claimed_fx3_var_shutter_supported=True
        )
        self.assertFalse(res1.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION,
            res1.violation_codes,
        )
        res2 = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            requested_var_shutter_mode="1/48.0"
        )
        self.assertFalse(res2.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION,
            res2.violation_codes,
        )
        res3 = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            help_guide_code=FX30_HELP_GUIDE_CODE_G93
        )
        self.assertFalse(res3.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION,
            res3.violation_codes,
        )

    def test_25_g93_blocks_false_fx6_ecs_menu_assumption_on_ilme_fx3(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            claimed_fx3_ecs_supported=True
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.var_shutter_or_ecs_false_assumption_blocked)
        self.assertIn(
            STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION,
            res.violation_codes,
        )

    def test_26_g93_rejects_invalid_antiflicker_enum_and_post_reset_mismatch(self) -> None:
        res_enum = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_anti_flicker_shoot="AutoVar"
        )
        self.assertFalse(res_enum.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION,
            res_enum.violation_codes,
        )
        res_rst = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            pre_reset_anti_flicker_shoot="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_anti_flicker_shoot="On",
        )
        self.assertFalse(res_rst.valid)
        self.assertIn(
            STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION,
            res_rst.violation_codes,
        )

    def test_27_g93_rejects_invalid_body_or_firmware_telemetry(self) -> None:
        res = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
            body_model_name=FX3_MODEL_NAME,
            body_model_id=0xDEADBEEF,
            firmware_version="not_a_version",
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G93_TELEMETRY_INVALID, res.violation_codes)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE246, "7.02")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE246, (1, 0))
        self.assertEqual(FX3_HELP_GUIDE_CODE_G93, "ilc/2210")

    def test_28_evaluate_g93_clean_room_and_persistent_emmc_write_block(self) -> None:
        verdict_ok, res_ok = evaluate_g93_framing_and_antiflicker_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict_ok.passed)
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res_ok.persistent_emmc_writes_authorized)

        verdict_blk, res_blk = evaluate_g93_framing_and_antiflicker_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict_blk.passed)
        self.assertFalse(res_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res_blk.violation_codes)

    # ------------------------------------------------------------------
    # Section C: Gate `G94` USB Power Supply Battery/Type-C Interlocks &
    #            USB LUN Setup Persistence Guard (18 tests: 29..46)
    # ------------------------------------------------------------------

    def test_29_g94_factory_defaults_and_usb_setup_menu_paths(self) -> None:
        self.assertEqual(USB_CONNECTION_MODE_FACTORY_DEFAULT_G94, "Sel. When Connect")
        self.assertEqual(USB_LUN_SETTING_FACTORY_DEFAULT_G94, "Multi")
        self.assertEqual(USB_POWER_SUPPLY_FACTORY_DEFAULT_G94, "On")
        self.assertEqual(len(ALLOWED_USB_CONNECTION_MODES_G94), 5)
        self.assertEqual(ALLOWED_USB_LUN_SETTINGS_G94, ("Multi", "Single"))
        self.assertEqual(ALLOWED_USB_POWER_SUPPLY_MODES_G94, ("On", "Off"))
        self.assertEqual(
            ALLOWED_USB_POWER_PORTS_G94,
            ("USB Type-C", "Multi/Micro USB", "Disconnected"),
        )
        self.assertEqual(
            ALLOWED_BATTERY_BAY_SOURCES_G94, ("NP-FZ100", "DC-C1", "Empty")
        )
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G94)
        self.assertEqual(res.usb_setup_menu_path, USB_SETUP_MENU_PATH_G94)
        self.assertEqual(
            res.usb_connection_mode_menu_path, USB_CONNECTION_MODE_MENU_PATH_G94
        )
        self.assertEqual(res.usb_lun_setting_menu_path, USB_LUN_SETTING_MENU_PATH_G94)
        self.assertEqual(res.usb_power_supply_menu_path, USB_POWER_SUPPLY_MENU_PATH_G94)
        self.assertTrue(res.effective_usb_bus_power_active)
        self.assertEqual(res.usb_packets_transmitted, 0)

    def test_30_g94_all_five_usb_connection_modes_accepted_offline(self) -> None:
        for conn_mode in (
            USB_CONN_SEL_WHEN_CONNECT_G94,
            USB_CONN_MASS_STORAGE_MSC_G94,
            USB_CONN_MTP_G94,
            USB_CONN_PC_REMOTE_G94,
            USB_CONN_LAN_WIRED_G94,
        ):
            res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
                pre_reset_usb_connection_mode=conn_mode
            )
            self.assertTrue(res.valid, msg=f"Failed for {conn_mode}")
            self.assertEqual(res.effective_post_reset_usb_connection_mode, conn_mode)

    def test_31_g94_usb_setup_items_survive_camera_settings_reset(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_connection_mode=USB_CONN_MASS_STORAGE_MSC_G94,
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G94,
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G94,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.usb_setup_survives_camera_settings_reset)
        self.assertEqual(
            res.effective_post_reset_usb_connection_mode, USB_CONN_MASS_STORAGE_MSC_G94
        )
        self.assertEqual(res.effective_post_reset_usb_lun_setting, USB_LUN_SINGLE_G94)
        self.assertEqual(
            res.effective_post_reset_usb_power_supply, USB_POWER_SUPPLY_OFF_G94
        )
        self.assertFalse(res.effective_usb_bus_power_active)

    def test_32_g94_usb_setup_items_reset_to_defaults_only_on_initialize(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_connection_mode=USB_CONN_LAN_WIRED_G94,
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G94,
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G94,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.usb_setup_reset_only_by_initialize)
        self.assertEqual(
            res.effective_post_reset_usb_connection_mode,
            USB_CONN_SEL_WHEN_CONNECT_G94,
        )
        self.assertEqual(res.effective_post_reset_usb_lun_setting, USB_LUN_MULTI_G94)
        self.assertEqual(
            res.effective_post_reset_usb_power_supply, USB_POWER_SUPPLY_ON_G94
        )

    def test_33_g94_rejects_false_claim_that_camera_settings_reset_wipes_usb_lun_or_power(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G94,
            pre_reset_usb_power_supply=USB_POWER_SUPPLY_OFF_G94,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_usb_lun_setting=USB_LUN_MULTI_G94,
            claimed_post_reset_usb_power_supply=USB_POWER_SUPPLY_ON_G94,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            res.violation_codes,
        )

    def test_34_g94_blocks_powering_on_via_usb_without_inserted_npfz100_battery(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            battery_bay_source=BATTERY_BAY_EMPTY_G94,
            usb_power_port=USB_PORT_TYPE_C_G94,
            usb_wall_adapter_connected=True,
            power_on_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.power_on_available)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE,
            res.violation_codes,
        )

    def test_35_g94_blocks_false_claim_that_battery_free_usb_poweron_is_allowed(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            battery_bay_source=BATTERY_BAY_NP_FZ100_G94,
            claimed_power_on_without_battery_allowed=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE,
            res.violation_codes,
        )

    def test_36_g94_allows_dc_c1_coupler_occupying_battery_bay(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            battery_bay_source=BATTERY_BAY_DC_C1_COUPLER_G94,
            usb_power_port=USB_PORT_TYPE_C_G94,
            usb_wall_adapter_connected=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.np_fz100_or_dc_c1_present)
        self.assertTrue(res.power_on_available)

    def test_37_g94_blocks_mid_session_npfz100_battery_removal_under_usb_wall_power(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            battery_bay_source=BATTERY_BAY_NP_FZ100_G94,
            usb_power_port=USB_PORT_TYPE_C_G94,
            usb_wall_adapter_connected=True,
            mid_session_battery_removed=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.mid_session_unbuffered_power_off_triggered)
        self.assertFalse(res.effective_usb_bus_power_active)
        self.assertIn(
            STATUS_BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF,
            res.violation_codes,
        )

    def test_38_g94_blocks_multi_micro_usb_power_supply_or_charging(self) -> None:
        res_port = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            usb_power_port=USB_PORT_MULTI_MICRO_G94,
            usb_wall_adapter_connected=True,
        )
        self.assertFalse(res_port.valid)
        self.assertFalse(res_port.multi_micro_usb_power_or_charge_supported)
        self.assertTrue(res_port.usb_power_type_c_exclusive)
        self.assertIn(
            STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED,
            res_port.violation_codes,
        )
        res_claim = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            usb_power_port=USB_PORT_TYPE_C_G94,
            claimed_multi_micro_usb_power_supported=True,
        )
        self.assertFalse(res_claim.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED,
            res_claim.violation_codes,
        )

    def test_39_g94_disconnected_usb_port_runs_on_inserted_npfz100_battery(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            battery_bay_source=BATTERY_BAY_NP_FZ100_G94,
            usb_power_port=USB_PORT_NONE_G94,
            usb_wall_adapter_connected=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.effective_usb_bus_power_active)
        self.assertTrue(res.power_on_available)

    def test_40_g94_usb_lun_multi_exposes_two_slots_and_single_exposes_one_slot(self) -> None:
        res_multi = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_lun_setting=USB_LUN_MULTI_G94,
            claimed_msc_exposed_lun_count=2,
        )
        self.assertTrue(res_multi.valid)
        self.assertEqual(res_multi.effective_msc_exposed_lun_count, 2)
        self.assertEqual(res_multi.exposed_msc_slots, ("Slot 1", "Slot 2"))

        res_single = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G94,
            claimed_msc_exposed_lun_count=1,
        )
        self.assertTrue(res_single.valid)
        self.assertEqual(res_single.effective_msc_exposed_lun_count, 1)
        self.assertEqual(res_single.exposed_msc_slots, ("Primary Recording Slot",))
        self.assertGreater(len(res_single.warnings), 0)

    def test_41_g94_blocks_usb_lun_slot_visibility_count_mismatch(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_lun_setting=USB_LUN_SINGLE_G94,
            claimed_msc_exposed_lun_count=2,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH,
            res.violation_codes,
        )

    def test_42_g94_blocks_live_host_usb_attachment_and_packet_transmission(self) -> None:
        res_live = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            live_host_usb_attach_requested=True
        )
        self.assertFalse(res_live.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN,
            res_live.violation_codes,
        )
        res_pkts = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            simulated_usb_packets_transmitted=4
        )
        self.assertFalse(res_pkts.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN,
            res_pkts.violation_codes,
        )

    def test_43_g94_blocks_unlocked_tier0_sdxc_reader_without_wp_switch(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            off_camera_wp_locked_sdxc_reader_used=False
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN,
            res.violation_codes,
        )

    def test_44_g94_rejects_invalid_usb_conn_or_lun_enums(self) -> None:
        res_uvc = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_connection_mode="UVC/UAC Streaming"
        )
        self.assertFalse(res_uvc.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            res_uvc.violation_codes,
        )
        res_lun = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            pre_reset_usb_lun_setting="QuadSlot"
        )
        self.assertFalse(res_lun.valid)
        self.assertIn(
            STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            res_lun.violation_codes,
        )

    def test_45_g94_rejects_invalid_body_or_port_telemetry(self) -> None:
        res = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
            body_model_name="ILME-FX6",
            usb_power_port="FireWire400",
        )
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_G94_TELEMETRY_INVALID, res.violation_codes)

    def test_46_evaluate_g94_clean_room_and_persistent_emmc_write_block(self) -> None:
        state = resolve_fx3_usb_power_interlock_and_lun_persistence_state()
        self.assertTrue(state["effective_usb_bus_power_active"])
        verdict_ok, res_ok = evaluate_g94_usb_power_and_lun_persistence_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict_ok.passed)
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.usb_packets_transmitted, 0)
        self.assertFalse(res_ok.hardware_live_attachment_authorized)

        verdict_blk, res_blk = evaluate_g94_usb_power_and_lun_persistence_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict_blk.passed)
        self.assertFalse(res_blk.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res_blk.violation_codes)

    # ------------------------------------------------------------------
    # Section D: Unified `94`-Gate Master Safety Preflight (12 tests: 47..58)
    # ------------------------------------------------------------------

    def test_47_active_environment_94gate_offline_verifies_91_of_94(self) -> None:
        r = self.active_offline_94
        self.assertEqual(
            r.schema, REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA
        )
        self.assertEqual(
            r.version, REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_VERSION
        )
        self.assertEqual(len(r.gates), 94)
        self.assertEqual(r.summary["total_gates"], 94)
        self.assertEqual(r.summary["verified_gates"], 91)
        self.assertEqual(r.technical_gates_passed, 91)
        self.assertEqual(r.status, "VERIFIED_91_OF_94_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(r.offline_91_gates_verified)
        self.assertFalse(r.all_94_gates_verified)
        self.assertTrue(r.g13_to_g94_all_passed)
        self.assertTrue(r.g93_to_g94_all_passed)

    def test_48_clean_room_offline_91_of_94_and_gate_ordering(self) -> None:
        r = self.clean_offline_94
        self.assertEqual(r.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r.clean_room_forced)
        self.assertEqual(r.summary["verified_gates"], 91)
        self.assertEqual(r.gates[-2]["gate_id"], G93_GATE_ID)
        self.assertEqual(r.gates[-1]["gate_id"], G94_GATE_ID)
        self.assertTrue(r.gates[-2]["passed"])
        self.assertTrue(r.gates[-1]["passed"])

    def test_49_simulate_bench_dry_run_verifies_all_94_of_94_gates(self) -> None:
        r = self.clean_dryrun_94
        self.assertEqual(r.summary["verified_gates"], 94)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(r.all_94_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertEqual(
            r.status, "VERIFIED_ALL_94_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_50_all_hardware_redlines_remain_false_in_offline_and_dry_run(self) -> None:
        for r in (self.active_offline_94, self.clean_offline_94, self.clean_dryrun_94):
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.human_hardware_attach_token)
            self.assertFalse(r.physical_flash_auto_exec_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.persistent_write_release)
            self.assertTrue(r.agent_auto_flash_blocked)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_51_aliases_evaluate_94_master_safety_gates_and_run_94_gate_preflight(self) -> None:
        self.assertIs(evaluate_94_master_safety_gates, evaluate_94gate_preflight)
        self.assertIs(run_94_gate_preflight, evaluate_94gate_preflight)

    def test_52_94gate_propagates_g93_hdmi_raw_framing_conflict_failure(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            master_92_override=self.clean_offline_92,
            framing_antiflicker_kwargs={
                "pre_reset_framing": "On",
                "hdmi_raw_output_enabled": True,
            },
        )
        self.assertFalse(r.g93_to_g94_all_passed)
        self.assertFalse(r.g13_to_g94_all_passed)
        self.assertFalse(r.offline_91_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT
        )
        self.assertEqual(r.summary["verified_gates"], 90)

    def test_53_94gate_propagates_g93_false_var_shutter_assumption_failure(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            master_92_override=self.clean_offline_92,
            framing_antiflicker_kwargs={"claimed_fx3_var_shutter_supported": True},
        )
        self.assertFalse(r.g93_to_g94_all_passed)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION
        )

    def test_54_94gate_propagates_g94_missing_npfz100_battery_failure(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            master_92_override=self.clean_offline_92,
            usb_power_lun_kwargs={"battery_bay_source": "Empty"},
        )
        self.assertFalse(r.g93_to_g94_all_passed)
        self.assertFalse(r.offline_91_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE
        )
        self.assertEqual(r.summary["verified_gates"], 90)

    def test_55_94gate_propagates_g94_multi_micro_usb_power_failure(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            master_92_override=self.clean_offline_92,
            usb_power_lun_kwargs={"usb_power_port": "Multi/Micro USB"},
        )
        self.assertFalse(r.g93_to_g94_all_passed)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED
        )

    def test_56_94gate_blocks_persistent_emmc_write_request(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            master_92_override=self.clean_dryrun_92,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r.offline_91_gates_verified)
        self.assertFalse(r.all_94_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)

    def test_57_94gate_dry_run_simulated_backup_kwarg_alias(self) -> None:
        r = evaluate_94gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_92_override=self.clean_dryrun_92,
        )
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertTrue(r.all_94_gates_verified)

    def test_58_94gate_report_to_dict_json_roundtrip(self) -> None:
        payload = json.loads(json.dumps(self.clean_offline_94.to_dict()))
        self.assertEqual(
            payload["schema"], REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA
        )
        self.assertEqual(payload["summary"]["total_gates"], 94)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["usb_packets_transmitted"], 0)

    # ------------------------------------------------------------------
    # Section E: CLI Subcommands & Standalone Module Entrypoint (8 tests: 59..66)
    # ------------------------------------------------------------------

    def test_59_cli_verify_framing_antiflicker_guard_text_and_alias(self) -> None:
        for subcmd in (
            "verify-framing-antiflicker-guard",
            "verify-g93-framing-antiflicker",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn(f"gate={G93_GATE_ID}", out)
            self.assertIn("valid=True", out)
            self.assertIn("has_var_shutter=False", out)

    def test_60_cli_verify_framing_antiflicker_guard_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-framing-antiflicker-guard", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G93)
        self.assertFalse(data["framing_antiflicker_guard"]["fx3_has_var_shutter"])

    def test_61_cli_verify_usbpower_lun_guard_text_and_alias(self) -> None:
        for subcmd in ("verify-usbpower-lun-guard", "verify-g94-usbpower-lun"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([subcmd, "--force-clean-room"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            self.assertIn(f"gate={G94_GATE_ID}", out)
            self.assertIn("valid=True", out)
            self.assertIn("usb_packets_transmitted=0", out)

    def test_62_cli_verify_usbpower_lun_guard_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-usbpower-lun-guard", "--force-clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G94)
        self.assertEqual(data["usb_packets_transmitted"], 0)

    def test_63_cli_verify_94_gates_offline_text_output(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard,
            "evaluate_92gate_preflight",
            return_value=self.clean_offline_92,
        ), contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-94-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=91/94", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_64_cli_verify_94_gates_simulate_bench_dry_run_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard,
            "evaluate_92gate_preflight",
            return_value=self.clean_dryrun_92,
        ), contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-94-gates",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["summary"]["verified_gates"], 94)
        self.assertTrue(data["all_94_gates_verified"])
        self.assertFalse(data["overall_ready_for_hardware_attach"])

    def test_65_standalone_module_main_text_and_json_modes(self) -> None:
        buf_txt = io.StringIO()
        with mock.patch.object(
            fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard,
            "evaluate_92gate_preflight",
            return_value=self.clean_offline_92,
        ), contextlib.redirect_stdout(buf_txt):
            rc_txt = module_main(["--force-clean-room"])
        self.assertEqual(rc_txt, 0)
        self.assertIn("verified=91/94", buf_txt.getvalue())

        buf_json = io.StringIO()
        with mock.patch.object(
            fx3_safety.realhw_framing_usbpower_lun_antiflicker_and_94gate_guard,
            "evaluate_92gate_preflight",
            return_value=self.clean_dryrun_92,
        ), contextlib.redirect_stdout(buf_json):
            rc_json = module_main(
                ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 94)

    def test_66_backward_compatibility_with_92gate_report_structure(self) -> None:
        m92 = self.active_offline_94.master_92_report
        self.assertEqual(m92["summary"]["total_gates"], 92)
        self.assertEqual(m92["summary"]["verified_gates"], 89)
        self.assertTrue(m92["g91_to_g92_all_passed"])


if __name__ == "__main__":
    unittest.main()
