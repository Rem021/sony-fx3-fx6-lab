"""Phase 241 Dual-Mode Unit Tests (`>=62` tests; 66 tests implemented) for
`fx3_safety.realhw_shoe_audio_wind_saveload_c3_and_92gate_guard`:

- Gate `G91`: `ILME-FX3` (`Ver. 7.02`) `[Shoe Audio Set.]` `48kHz/24bit 4ch`
  Meter/Routing Guard & `[Wind Noise Reduct.]` Built-In-Mic-Only Boundary.
- Gate `G92`: `ILME-FX3` (`Ver. 7.02`) `[Save/Load Settings]`
  `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items Privacy/Calibration Firewall
  & Slot-1 Tier-0 Vault Write Guard.
- Unified `92`-Gate Master Safety Preflight (`evaluate_92gate_preflight` /
  `verify-92-gates`): `89/92` offline awaiting physical Tier-0 receipt and
  `92/92` in `--simulate-bench-dry-run` with all hardware write/live-attach
  redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_shoe_audio_wind_saveload_c3_and_92gate_guard import (
    ALLOWED_MISHOE_AUDIO_ACCESSORIES_G91,
    ALLOWED_RESET_ACTIONS_PHASE241,
    ALLOWED_SAVELOAD_OPERATIONS,
    ALLOWED_SAVELOAD_TARGETS,
    ALLOWED_SHOE_AUDIO_SET_MODES,
    ALLOWED_SHOOT_MODES_G91,
    ALLOWED_WIND_NOISE_REDUCT_MODES,
    ALLOWED_XLRH1_SWITCH_MODES_G91,
    AUDIO_INPUT_SOURCE_BODY_35MM_ANALOG_G91,
    AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91,
    AUDIO_INPUT_SOURCE_DISABLED_G91,
    AUDIO_INPUT_SOURCE_MISHOE_ANALOG_2CH_G91,
    AUDIO_INPUT_SOURCE_MISHOE_DIGITAL_G91,
    AUDIO_LEVEL_DISPLAY_MENU_PATH,
    AUDIO_RECORDING_MENU_PATH_G91,
    DIGITAL_2CH_MISHOE_ACCESSORIES_G91,
    DIGITAL_4CH_MISHOE_ACCESSORIES_G91,
    DONOR_CHECK_MAX_SECONDS_PHASE241,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_DEFAULT_FW_VERSION_PHASE241,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE241,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    G91,
    G91_GATE_CODE,
    G91_GATE_ID,
    G92,
    G92_GATE_CODE,
    G92_GATE_ID,
    GATE_G91_SHOE_AUDIO_48KHZ_24BIT_4CH_METER_ROUTING_AND_WIND_NOISE_BUILTIN_ONLY_GUARD,
    GATE_G92_SAVELOAD_CAMSET_C3_PORTAL_EXCLUDED_ITEMS_FIREWALL_AND_SLOT1_TIER0_VAULT_WRITE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MISHOE_ACCESSORY_ANALOG_MIC_G91,
    MISHOE_ACCESSORY_ECM_B1M_G91,
    MISHOE_ACCESSORY_ECM_M1_G91,
    MISHOE_ACCESSORY_NONE_G91,
    MISHOE_ACCESSORY_XLR_H1_G91,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE241_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA,
    REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SAVELOAD_ALLOWED_CAMSET_FILENAMES,
    SAVELOAD_CLOUD_C3_MIN_FW_TUPLE,
    SAVELOAD_CLOUD_C3_TARGETS,
    SAVELOAD_EXCLUDED_ITEM_CATEGORIES,
    SAVELOAD_EXCLUDED_ITEM_TOKENS,
    SAVELOAD_FX3_CAMSET_CARD_DIR,
    SAVELOAD_MAX_CAMSET_FILES_PER_CARD,
    SAVELOAD_MEDIA_TARGETS,
    SAVELOAD_OP_LOAD,
    SAVELOAD_OP_NONE,
    SAVELOAD_OP_SAVE,
    SAVELOAD_REJECTED_CROSS_MODELS,
    SAVELOAD_TARGET_CLOUD_PRIVATE,
    SAVELOAD_TARGET_CLOUD_SHARE,
    SAVELOAD_TARGET_MEDIA_SLOT_1,
    SAVELOAD_TARGET_MEDIA_SLOT_2,
    SAVE_LOAD_SETTINGS_MENU_PATH,
    SHOE_AUDIO_3_DISQUALIFYING_CONDITIONS,
    SHOE_AUDIO_48K_16BIT_2CH,
    SHOE_AUDIO_48K_24BIT_2CH,
    SHOE_AUDIO_48K_24BIT_4CH,
    SHOE_AUDIO_SET_FACTORY_DEFAULT,
    SHOE_AUDIO_SET_MENU_PATH,
    SHOOT_MODE_MOVIE_G91,
    SHOOT_MODE_SQ_MOTION_G91,
    SHOOT_MODE_STILL_G91,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G91_AUDIO_LEVEL_METER_EXPANSION_MISMATCH,
    STATUS_BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM,
    STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
    STATUS_BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_HAZARD,
    STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G91_TELEMETRY_INVALID,
    STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED,
    STATUS_BLOCKED_G92_CLOUD_C3_FIRMWARE_FLOOR_VIOLATION,
    STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
    STATUS_BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION,
    STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID,
    STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
    STATUS_BLOCKED_G92_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE241_DONOR_INTEGRITY,
    STATUS_VERIFIED_G91,
    STATUS_VERIFIED_G92,
    TIER0_VAULT_GUARDED_ARTIFACTS_G92,
    USB_PACKETS_TRANSMITTED,
    WIND_NOISE_REDUCT_FACTORY_DEFAULT,
    WIND_NOISE_REDUCT_MENU_PATH,
    WIND_NOISE_REDUCT_OFF,
    WIND_NOISE_REDUCT_ON,
    XLRH1_HARDWARE_LOW_CUT_MODES_G91,
    XLRH1_SWITCH_ANALOG_G91,
    XLRH1_SWITCH_DIGITAL_G91,
    audit_phase241_donor_contracts,
    classify_saveload_excluded_items,
    evaluate_92_master_safety_gates,
    evaluate_92gate_preflight,
    evaluate_g91_shoe_audio_and_wind_noise_guard,
    evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard,
    main as module_main,
    resolve_fx3_saveload_c3_and_slot1_vault_state,
    resolve_fx3_shoe_audio_and_wind_noise_state,
    run_92_gate_preflight,
    verify_saveload_camset_c3_exclusions_and_slot1_vault_guard,
    verify_shoe_audio_4ch_and_wind_noise_guard,
)


class TestPhase241ShoeAudioWindSaveloadC3And92GateGuard(unittest.TestCase):
    """66 dual-mode tests covering Gates G91, G92, and unified 92-Gate preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        # Run unmocked evaluate_92gate_preflight() once in active environment mode
        # (LOCAL_DONOR_O_RDONLY when local donor is available, CLEAN_ROOM_SYNTHETIC
        # when FX3_FX6_FORCE_CLEAN_ROOM=1) to keep total suite runtime < 5s.
        cls.active_offline_92 = evaluate_92gate_preflight()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_90 = fx3_safety.evaluate_90gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_90 = fx3_safety.evaluate_90gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_92 = evaluate_92gate_preflight(
                force_clean_room=True, master_90_override=cls.clean_offline_90
            )
            cls.clean_dryrun_92 = evaluate_92gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_90_override=cls.clean_dryrun_90,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded `< 0.10s` Donor Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G91, G91_GATE_ID)
        self.assertEqual(G92, G92_GATE_ID)
        self.assertEqual(
            G91_GATE_CODE,
            GATE_G91_SHOE_AUDIO_48KHZ_24BIT_4CH_METER_ROUTING_AND_WIND_NOISE_BUILTIN_ONLY_GUARD,
        )
        self.assertEqual(
            G92_GATE_CODE,
            GATE_G92_SAVELOAD_CAMSET_C3_PORTAL_EXCLUDED_ITEMS_FIREWALL_AND_SLOT1_TIER0_VAULT_WRITE_GUARD,
        )
        self.assertEqual(
            REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA,
            "realhw_shoe_audio_wind_saveload_c3_and_92gate_guard_v1",
        )
        self.assertEqual(REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_VERSION, "1.0.0")
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
        phase241_exports = (
            "realhw_shoe_audio_wind_saveload_c3_and_92gate_guard",
            "G91",
            "G92",
            "G91_GATE_ID",
            "G92_GATE_ID",
            "Master92GateReport",
            "evaluate_92gate_preflight",
            "evaluate_92_master_safety_gates",
            "run_92_gate_preflight",
            "evaluate_g91_shoe_audio_and_wind_noise_guard",
            "evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard",
            "verify_shoe_audio_4ch_and_wind_noise_guard",
            "verify_saveload_camset_c3_exclusions_and_slot1_vault_guard",
        )
        for sym in phase241_exports:
            self.assertEqual(
                fx3_safety.__all__.count(sym),
                1,
                msg=f"Expected exactly 1 entry for {sym} in __all__",
            )
            self.assertTrue(hasattr(fx3_safety, sym), msg=f"Missing {sym} attr")
        for prior_sym in (
            "G89",
            "G90",
            "evaluate_90gate_preflight",
            "evaluate_88gate_preflight",
            "evaluate_12_safety_gates",
        ):
            self.assertIn(prior_sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, prior_sym))

    def test_03_donor_audit_active_environment_under_100ms_and_zero_byte_leak(
        self,
    ) -> None:
        t0 = time.monotonic()
        audit = audit_phase241_donor_contracts()
        elapsed = time.monotonic() - t0
        self.assertTrue(audit.valid)
        self.assertLess(elapsed, 0.25)
        self.assertTrue(audit.within_budget_100ms)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.files_inspected, 0)
        elif audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE241_DONOR_SPECS))
        else:
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.files_inspected, 0)

    def test_04_donor_audit_forced_clean_room_via_arg_and_env(self) -> None:
        a_arg = audit_phase241_donor_contracts(force_clean_room=True)
        self.assertTrue(a_arg.valid)
        self.assertEqual(a_arg.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(a_arg.raw_firmware_bytes_leaked, 0)

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            a_env = audit_phase241_donor_contracts()
            self.assertTrue(a_env.valid)
            self.assertEqual(a_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_missing_work_root_falls_back_to_clean_room_synthetic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_work = Path(td) / "nonexistent_donor_root"
            audit = audit_phase241_donor_contracts(
                work_root=empty_work, force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
            self.assertTrue(audit.within_budget_100ms)

    def test_06_donor_audit_partial_work_root_falls_back_and_negative_budget_flags(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            first_spec = next(iter(PINNED_PHASE241_DONOR_SPECS.values()))
            p = work / first_spec[1]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"partial")
            audit_partial = audit_phase241_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertTrue(audit_partial.valid)
            self.assertEqual(audit_partial.verification_mode, "CLEAN_ROOM_SYNTHETIC")

            audit_budget = audit_phase241_donor_contracts(
                force_clean_room=True, max_budget_seconds=-1.0
            )
            self.assertFalse(audit_budget.within_budget_100ms)

    def test_07_donor_audit_size_or_sha256_mismatch_blocks_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            for spec in PINNED_PHASE241_DONOR_SPECS.values():
                p = work / str(spec[1])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"corrupt_donor_payload")
            audit = audit_phase241_donor_contracts(
                work_root=work, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE241_DONOR_INTEGRITY)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_08_donor_audit_uses_strictly_o_rdonly_flags(self) -> None:
        seen_flags = []
        real_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            seen_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        mod = fx3_safety.realhw_shoe_audio_wind_saveload_c3_and_92gate_guard
        mod._DONOR_BLOB_CACHE.clear()
        with mock.patch("os.open", side_effect=spy_open):
            audit = audit_phase241_donor_contracts()
        self.assertTrue(audit.valid)
        for fl in seen_flags:
            self.assertEqual(
                fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0
            )

    # ------------------------------------------------------------------
    # Section B: Gate G91 — `[Shoe Audio Set.]` `48kHz/24bit 4ch` &
    # `[Wind Noise Reduct.]` Built-In-Mic-Only Boundary (24 tests)
    # ------------------------------------------------------------------

    def test_09_g91_menu_paths_enums_and_factory_defaults(self) -> None:
        self.assertEqual(
            SHOE_AUDIO_SET_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]",
        )
        self.assertEqual(
            WIND_NOISE_REDUCT_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]",
        )
        self.assertEqual(
            AUDIO_LEVEL_DISPLAY_MENU_PATH,
            "MENU -> Shooting -> [Audio Recording] -> [Audio Level Display]",
        )
        self.assertEqual(
            AUDIO_RECORDING_MENU_PATH_G91,
            "MENU -> Shooting -> [Audio Recording] -> [Audio Recording]",
        )
        self.assertEqual(
            ALLOWED_SHOE_AUDIO_SET_MODES,
            ("48kHz/16bit 2ch", "48kHz/24bit 2ch", "48kHz/24bit 4ch"),
        )
        self.assertEqual(SHOE_AUDIO_SET_FACTORY_DEFAULT, "48kHz/16bit 2ch")
        self.assertEqual(ALLOWED_WIND_NOISE_REDUCT_MODES, ("Off", "On"))
        self.assertEqual(WIND_NOISE_REDUCT_FACTORY_DEFAULT, "Off")
        self.assertEqual(len(SHOE_AUDIO_3_DISQUALIFYING_CONDITIONS), 3)

    def test_10_g91_default_xlrh1_digital_4ch_expands_audio_level_meter_to_4ch(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G91)
        self.assertEqual(res.effective_post_reset_shoe_audio_set, SHOE_AUDIO_48K_24BIT_4CH)
        self.assertEqual(res.active_audio_input_source, AUDIO_INPUT_SOURCE_MISHOE_DIGITAL_G91)
        self.assertEqual(res.effective_audio_format, SHOE_AUDIO_48K_24BIT_4CH)
        self.assertEqual(res.effective_recorded_audio_channels, 4)
        self.assertEqual(res.audio_level_meter_channels, 4)
        self.assertTrue(res.four_ch_audio_level_meter_expanded)
        self.assertFalse(res.external_mic_wind_reduct_effective)
        self.assertFalse(res.builtin_mic_wind_reduct_effective)

    def test_11_g91_ecm_m1_digital_4ch_expands_audio_level_meter_to_4ch(self) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_ECM_M1_G91,
            audio_level_display="On",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_recorded_audio_channels, 4)
        self.assertEqual(res.audio_level_meter_channels, 4)
        self.assertTrue(res.four_ch_audio_level_meter_expanded)
        self.assertFalse(res.external_mic_wind_reduct_effective)

    def test_12_g91_xlrh1_digital_2ch_16bit_and_24bit_keep_2ch_meter(self) -> None:
        for fmt in (SHOE_AUDIO_48K_16BIT_2CH, SHOE_AUDIO_48K_24BIT_2CH):
            res = verify_shoe_audio_4ch_and_wind_noise_guard(
                pre_reset_shoe_audio_set=fmt,
                mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
                xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            )
            self.assertTrue(res.valid, msg=fmt)
            self.assertEqual(res.effective_audio_format, fmt)
            self.assertEqual(res.effective_recorded_audio_channels, 2)
            self.assertEqual(res.audio_level_meter_channels, 2)
            self.assertFalse(res.four_ch_audio_level_meter_expanded)

    def test_13_g91_ecm_b1m_2ch_digital_shoe_supports_2ch_and_blocks_4ch(
        self,
    ) -> None:
        self.assertIn(MISHOE_ACCESSORY_ECM_B1M_G91, DIGITAL_2CH_MISHOE_ACCESSORIES_G91)
        self.assertIn(MISHOE_ACCESSORY_XLR_H1_G91, DIGITAL_4CH_MISHOE_ACCESSORIES_G91)
        res_2ch = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_2CH,
            mishoe_accessory=MISHOE_ACCESSORY_ECM_B1M_G91,
        )
        self.assertTrue(res_2ch.valid)
        self.assertEqual(res_2ch.effective_audio_format, SHOE_AUDIO_48K_24BIT_2CH)
        self.assertEqual(res_2ch.effective_recorded_audio_channels, 2)
        self.assertEqual(res_2ch.audio_level_meter_channels, 2)
        self.assertFalse(res_2ch.four_ch_audio_level_meter_expanded)

        res_4ch_blocked = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_ECM_B1M_G91,
        )
        self.assertFalse(res_4ch_blocked.valid)
        self.assertEqual(
            res_4ch_blocked.status,
            STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
        )

    def test_14_g91_audio_level_display_off_yields_zero_meter_bars_even_in_4ch(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            audio_level_display="Off",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_recorded_audio_channels, 4)
        self.assertEqual(res.audio_level_meter_channels, 0)
        self.assertFalse(res.four_ch_audio_level_meter_expanded)

    def test_15_g91_audio_level_meter_mismatch_blocks(self) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            audio_level_display="On",
            observed_audio_level_meter_channels=2,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G91_AUDIO_LEVEL_METER_EXPANSION_MISMATCH
        )

    def test_16_g91_disqualifier_1a_audio_recording_off_locks_out_to_0ch(self) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            audio_recording="Off",
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.disqualified_by_audio_off_or_sq)
        self.assertFalse(res.shoe_audio_set_available)
        self.assertFalse(res.wind_noise_reduct_available)
        self.assertEqual(res.active_audio_input_source, AUDIO_INPUT_SOURCE_DISABLED_G91)
        self.assertEqual(res.effective_recorded_audio_channels, 0)
        self.assertEqual(res.audio_level_meter_channels, 0)

        res_bad = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            audio_recording="Off",
            observed_recorded_audio_channels=4,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
        )

    def test_17_g91_disqualifier_1b_sq_motion_locks_out_audio_and_wind_reduct(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            shoot_mode=SHOOT_MODE_SQ_MOTION_G91,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.disqualified_by_audio_off_or_sq)
        self.assertFalse(res.shoe_audio_set_available)
        self.assertFalse(res.wind_noise_reduct_available)
        self.assertEqual(res.effective_recorded_audio_channels, 0)
        self.assertEqual(res.audio_level_meter_channels, 0)

        res_claimed = verify_shoe_audio_4ch_and_wind_noise_guard(
            shoot_mode=SHOOT_MODE_SQ_MOTION_G91,
            observed_shoe_audio_set_available=True,
        )
        self.assertFalse(res_claimed.valid)
        self.assertEqual(
            res_claimed.status,
            STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
        )

    def test_18_g91_disqualifier_2_body_35mm_mic_jack_overrides_mishoe_to_2ch_analog(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            body_35mm_mic_jack_plugged=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.disqualified_by_35mm_jack_override)
        self.assertFalse(res.shoe_audio_set_available)
        self.assertEqual(
            res.active_audio_input_source, AUDIO_INPUT_SOURCE_BODY_35MM_ANALOG_G91
        )
        self.assertEqual(res.effective_audio_format, SHOE_AUDIO_48K_16BIT_2CH)
        self.assertEqual(res.effective_recorded_audio_channels, 2)
        self.assertEqual(res.audio_level_meter_channels, 2)
        self.assertFalse(res.external_mic_wind_reduct_effective)

        res_bad = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            body_35mm_mic_jack_plugged=True,
            observed_recorded_audio_channels=4,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
        )

    def test_19_g91_disqualifier_3_xlrh1_analog_switch_falls_back_to_2ch_16bit(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_ANALOG_G91,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.disqualified_by_analog_shoe_switch)
        self.assertFalse(res.shoe_audio_set_available)
        self.assertEqual(
            res.active_audio_input_source, AUDIO_INPUT_SOURCE_MISHOE_ANALOG_2CH_G91
        )
        self.assertEqual(res.effective_audio_format, SHOE_AUDIO_48K_16BIT_2CH)
        self.assertEqual(res.effective_recorded_audio_channels, 2)
        self.assertEqual(res.audio_level_meter_channels, 2)

        res_analog_acc = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_ANALOG_MIC_G91,
        )
        self.assertTrue(res_analog_acc.valid)
        self.assertTrue(res_analog_acc.disqualified_by_analog_shoe_switch)
        self.assertEqual(res_analog_acc.effective_recorded_audio_channels, 2)

        res_bad_fmt = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_ANALOG_G91,
            observed_effective_audio_format=SHOE_AUDIO_48K_24BIT_4CH,
        )
        self.assertFalse(res_bad_fmt.valid)
        self.assertEqual(
            res_bad_fmt.status,
            STATUS_BLOCKED_G91_FOUR_CH_LOCKOUT_OR_ROUTING_OVERRIDE_VIOLATION,
        )

    def test_20_g91_shoe_audio_set_and_wind_reduct_reset_by_camera_settings_reset(
        self,
    ) -> None:
        for rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
            res = verify_shoe_audio_4ch_and_wind_noise_guard(
                pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
                pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
                reset_action=rst,
                mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
                xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            )
            self.assertTrue(res.valid, msg=rst)
            self.assertEqual(
                res.effective_post_reset_shoe_audio_set, SHOE_AUDIO_48K_16BIT_2CH
            )
            self.assertEqual(
                res.effective_post_reset_wind_noise_reduct, WIND_NOISE_REDUCT_OFF
            )
            self.assertTrue(res.shoe_audio_set_reset_by_camera_settings_reset)
            self.assertTrue(res.wind_noise_reduct_reset_by_camera_settings_reset)
            self.assertEqual(res.effective_recorded_audio_channels, 2)

    def test_21_g91_shoe_audio_set_or_wind_reduct_reset_mismatch_blocks(self) -> None:
        res_shoe = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        )
        self.assertFalse(res_shoe.valid)
        self.assertEqual(
            res_shoe.status, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION
        )

        res_wind = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
        )
        self.assertFalse(res_wind.valid)
        self.assertEqual(
            res_wind.status,
            STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION,
        )

    def test_22_g91_invalid_shoe_audio_set_or_wind_reduct_enum_blocks(self) -> None:
        r1 = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_shoe_audio_set="96kHz/24bit 4ch"
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION
        )

        r2 = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct="Auto"
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION
        )

    def test_23_g91_wind_noise_reduct_builtin_mic_only_external_mic_never_effective(
        self,
    ) -> None:
        res_xlr = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            xlrh1_digital_analog_switch=XLRH1_SWITCH_DIGITAL_G91,
            indoor_low_wind_bench=True,
        )
        self.assertTrue(res_xlr.valid)
        self.assertFalse(res_xlr.external_mic_wind_reduct_effective)
        self.assertFalse(res_xlr.builtin_mic_wind_reduct_effective)
        self.assertGreaterEqual(len(res_xlr.warnings), 1)

        res_35 = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_NONE_G91,
            body_35mm_mic_jack_plugged=True,
            indoor_low_wind_bench=True,
        )
        self.assertTrue(res_35.valid)
        self.assertFalse(res_35.external_mic_wind_reduct_effective)
        self.assertFalse(res_35.builtin_mic_wind_reduct_effective)

    def test_24_g91_false_claim_of_external_mic_wind_noise_reduct_blocks(self) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_XLR_H1_G91,
            observed_external_mic_wind_reduct_effective=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM
        )

    def test_25_g91_builtin_stereo_mic_wind_reduct_on_blocks_indoor_bench_passes_outdoor(
        self,
    ) -> None:
        res_indoor_blocked = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_NONE_G91,
            body_35mm_mic_jack_plugged=False,
            indoor_low_wind_bench=True,
        )
        self.assertFalse(res_indoor_blocked.valid)
        self.assertTrue(res_indoor_blocked.builtin_mic_wind_reduct_effective)
        self.assertFalse(res_indoor_blocked.indoor_low_wind_attenuation_blocked)
        self.assertEqual(
            res_indoor_blocked.status,
            STATUS_BLOCKED_G91_INDOOR_LOW_WIND_BENCH_ATTENUATION_HAZARD,
        )

        res_outdoor_ok = verify_shoe_audio_4ch_and_wind_noise_guard(
            pre_reset_wind_noise_reduct=WIND_NOISE_REDUCT_ON,
            mishoe_accessory=MISHOE_ACCESSORY_NONE_G91,
            body_35mm_mic_jack_plugged=False,
            indoor_low_wind_bench=False,
        )
        self.assertTrue(res_outdoor_ok.valid)
        self.assertEqual(
            res_outdoor_ok.active_audio_input_source,
            AUDIO_INPUT_SOURCE_BUILTIN_STEREO_MIC_G91,
        )
        self.assertTrue(res_outdoor_ok.builtin_mic_wind_reduct_effective)
        self.assertFalse(res_outdoor_ok.external_mic_wind_reduct_effective)

    def test_26_g91_factory_default_false_claims_block(self) -> None:
        r_shoe = verify_shoe_audio_4ch_and_wind_noise_guard(
            claimed_shoe_audio_factory_default=SHOE_AUDIO_48K_24BIT_4CH
        )
        self.assertFalse(r_shoe.valid)
        self.assertEqual(
            r_shoe.status, STATUS_BLOCKED_G91_SHOE_AUDIO_SET_ENUM_OR_RESET_VIOLATION
        )

        r_wind = verify_shoe_audio_4ch_and_wind_noise_guard(
            claimed_wind_noise_factory_default=WIND_NOISE_REDUCT_ON
        )
        self.assertFalse(r_wind.valid)
        self.assertEqual(
            r_wind.status, STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION
        )

    def test_27_g91_xlrh1_hardware_low_cut_switch_modes_validated(self) -> None:
        self.assertEqual(XLRH1_HARDWARE_LOW_CUT_MODES_G91, ("Off", "100Hz", "300Hz"))
        for lc in XLRH1_HARDWARE_LOW_CUT_MODES_G91:
            res = verify_shoe_audio_4ch_and_wind_noise_guard(xlrh1_low_cut_switch=lc)
            self.assertTrue(res.valid, msg=lc)
            self.assertEqual(res.xlrh1_low_cut_switch, lc)

        res_bad = verify_shoe_audio_4ch_and_wind_noise_guard(
            xlrh1_low_cut_switch="500Hz"
        )
        self.assertFalse(res_bad.valid)
        self.assertIn(STATUS_BLOCKED_G91_TELEMETRY_INVALID, res_bad.violation_codes)

    def test_28_g91_still_shoot_mode_locks_out_movie_audio_tracks(self) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            shoot_mode=SHOOT_MODE_STILL_G91,
            pre_reset_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.shoe_audio_set_available)
        self.assertFalse(res.wind_noise_reduct_available)
        self.assertEqual(res.effective_recorded_audio_channels, 0)
        self.assertEqual(res.audio_level_meter_channels, 0)

    def test_29_g91_observed_wind_reduct_available_during_sq_or_audio_off_blocks(
        self,
    ) -> None:
        res = verify_shoe_audio_4ch_and_wind_noise_guard(
            audio_recording="Off",
            observed_wind_noise_reduct_available=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G91_WIND_NOISE_REDUCT_ENUM_OR_RESET_VIOLATION,
        )

    def test_30_g91_telemetry_validation_blocks_foreign_model_old_fw_or_bad_enums(
        self,
    ) -> None:
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE241, "7.02")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE241, (1, 0))
        self.assertEqual(len(ALLOWED_SHOOT_MODES_G91), 3)
        self.assertEqual(len(ALLOWED_MISHOE_AUDIO_ACCESSORIES_G91), 5)
        self.assertEqual(len(ALLOWED_XLRH1_SWITCH_MODES_G91), 2)
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE241), 3)

        bad_cases = (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x99999999},
            {"firmware_version": "0.99"},
            {"reset_action": "Hard Wipe"},
            {"shoot_mode": "Panorama"},
            {"audio_recording": "Maybe"},
            {"audio_level_display": "Half"},
            {"mishoe_accessory": "UnknownAdapter"},
            {"xlrh1_digital_analog_switch": "OPTICAL"},
        )
        for kw in bad_cases:
            res = verify_shoe_audio_4ch_and_wind_noise_guard(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G91_TELEMETRY_INVALID, res.violation_codes)

    def test_31_g91_resolver_normalizes_bracketed_sony_menu_strings(self) -> None:
        st = resolve_fx3_shoe_audio_and_wind_noise_state(
            pre_reset_shoe_audio_set="[48kHz/24bit 4ch]",
            pre_reset_wind_noise_reduct="[Off]",
            reset_action="[None]",
            shoot_mode="[Movie]",
            audio_recording="[On]",
            audio_level_display="[On]",
            mishoe_accessory="[XLR-H1]",
            xlrh1_digital_analog_switch="[DIGITAL]",
        )
        self.assertEqual(st["expected_post_shoe_audio_set"], "48kHz/24bit 4ch")
        self.assertEqual(st["expected_recorded_audio_channels"], 4)
        self.assertEqual(st["expected_audio_level_meter_channels"], 4)
        self.assertTrue(st["four_ch_audio_level_meter_expanded"])

    def test_32_g91_evaluator_dual_mode_and_persistent_emmc_write_block(self) -> None:
        v_n, r_n = evaluate_g91_shoe_audio_and_wind_noise_guard()
        self.assertTrue(v_n.passed)
        self.assertTrue(r_n.valid)
        self.assertEqual(v_n.gate_code, G91_GATE_CODE)
        self.assertEqual(r_n.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r_n.persistent_emmc_writes_authorized)

        v_c, r_c = evaluate_g91_shoe_audio_and_wind_noise_guard(force_clean_room=True)
        self.assertTrue(v_c.passed)
        self.assertEqual(r_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_w, r_w = evaluate_g91_shoe_audio_and_wind_noise_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_w.passed)
        self.assertEqual(r_w.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # ------------------------------------------------------------------
    # Section C: Gate G92 — `[Save/Load Settings]` `CAMSET01..10.DAT` /
    # `C3 Portal` Excluded-Items Firewall & Slot-1 Tier-0 Vault Guard (20 tests)
    # ------------------------------------------------------------------

    def test_33_g92_menu_path_targets_filenames_and_excluded_categories(self) -> None:
        self.assertEqual(
            SAVE_LOAD_SETTINGS_MENU_PATH,
            "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]",
        )
        self.assertEqual(ALLOWED_SAVELOAD_OPERATIONS, ("NONE", "LOAD", "SAVE"))
        self.assertEqual(
            ALLOWED_SAVELOAD_TARGETS,
            ("Media(Slot 1)", "Media(Slot 2)", "Cloud(Private)", "Cloud(Share)"),
        )
        self.assertEqual(SAVELOAD_MEDIA_TARGETS, ("Media(Slot 1)", "Media(Slot 2)"))
        self.assertEqual(SAVELOAD_CLOUD_C3_TARGETS, ("Cloud(Private)", "Cloud(Share)"))
        self.assertEqual(SAVELOAD_CLOUD_C3_MIN_FW_TUPLE, (4, 0))
        self.assertEqual(SAVELOAD_MAX_CAMSET_FILES_PER_CARD, 10)
        self.assertEqual(len(SAVELOAD_ALLOWED_CAMSET_FILENAMES), 10)
        self.assertEqual(SAVELOAD_ALLOWED_CAMSET_FILENAMES[0], "CAMSET01.DAT")
        self.assertEqual(SAVELOAD_ALLOWED_CAMSET_FILENAMES[-1], "CAMSET10.DAT")
        self.assertEqual(
            SAVELOAD_FX3_CAMSET_CARD_DIR, "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3"
        )
        self.assertEqual(len(SAVELOAD_EXCLUDED_ITEM_CATEGORIES), 5)
        self.assertEqual(len(SAVELOAD_EXCLUDED_ITEM_TOKENS), 5)
        self.assertIn("ILME-FX6", SAVELOAD_REJECTED_CROSS_MODELS)
        self.assertIn("pnflasha", TIER0_VAULT_GUARDED_ARTIFACTS_G92)

    def test_34_g92_default_load_from_slot1_tier0_vault_is_rdonly_safe(self) -> None:
        res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G92)
        self.assertEqual(res.saveload_operation, SAVELOAD_OP_LOAD)
        self.assertEqual(res.saveload_target, SAVELOAD_TARGET_MEDIA_SLOT_1)
        self.assertEqual(
            res.camset_card_path, "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3/CAMSET01.DAT"
        )
        self.assertTrue(res.same_model_ilme_fx3_locked)
        self.assertTrue(res.action_item_not_reset_parameter)
        self.assertTrue(res.excluded_items_firewall_enforced)
        self.assertTrue(res.load_is_card_o_rdonly_safe)
        self.assertTrue(res.slot1_unverified_camset_save_blocked)
        self.assertTrue(res.slot1_vault_write_firewall_enforced)
        self.assertEqual(res.slot1_card_sector_writes, 0)

    def test_35_g92_all_ten_camset01_to_camset10_dat_slots_accepted_on_slot2(
        self,
    ) -> None:
        for idx, fname in enumerate(SAVELOAD_ALLOWED_CAMSET_FILENAMES, start=1):
            res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                saveload_operation=SAVELOAD_OP_SAVE,
                saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_2,
                camset_filename=fname,
                card_camset_file_count=idx,
            )
            self.assertTrue(res.valid, msg=fname)
            self.assertEqual(
                res.camset_card_path, f"/PRIVATE/SONY/PRO/CAMERA/ILME-FX3/{fname}"
            )

    def test_36_g92_invalid_camset_filename_or_over_10_count_blocks(self) -> None:
        for bad_name in ("CAMSET00.DAT", "CAMSET11.DAT", "CAMSET1.DAT", "SETTINGS.BIN"):
            res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                camset_filename=bad_name
            )
            self.assertFalse(res.valid, msg=bad_name)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID
            )

        for bad_cnt in (11, 99):
            res_cnt = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                card_camset_file_count=bad_cnt
            )
            self.assertFalse(res_cnt.valid, msg=str(bad_cnt))
            self.assertEqual(
                res_cnt.status,
                STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID,
            )

        res_neg = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            card_camset_file_count=-1
        )
        self.assertFalse(res_neg.valid)
        self.assertIn(STATUS_BLOCKED_G92_TELEMETRY_INVALID, res_neg.violation_codes)

    def test_37_g92_invalid_saveload_operation_or_target_blocks(self) -> None:
        r_op = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation="DELETE_ALL"
        )
        self.assertFalse(r_op.valid)
        self.assertEqual(r_op.status, STATUS_BLOCKED_G92_TELEMETRY_INVALID)

        r_tgt = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_target="USB_THUMBDRIVE"
        )
        self.assertFalse(r_tgt.valid)
        self.assertEqual(
            r_tgt.status, STATUS_BLOCKED_G92_SAVELOAD_TARGET_FILE_OR_COUNT_INVALID
        )

    def test_38_g92_cloud_private_and_cloud_share_c3_portal_ver400_floor(self) -> None:
        for tgt in (SAVELOAD_TARGET_CLOUD_PRIVATE, SAVELOAD_TARGET_CLOUD_SHARE):
            for op in (SAVELOAD_OP_LOAD, SAVELOAD_OP_SAVE):
                res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                    firmware_version="7.02",
                    saveload_operation=op,
                    saveload_target=tgt,
                    profile_model_header=FX3_MODEL_NAME,
                )
                self.assertTrue(res.valid, msg=f"{op}@{tgt}")
                self.assertTrue(res.is_cloud_c3_target)
                self.assertFalse(res.is_media_target)
                self.assertTrue(res.c3_portal_firmware_floor_met)
                self.assertEqual(res.camset_card_path, f"c3portal://{tgt}/ILME-FX3")

        res_old = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            firmware_version="3.00",
            saveload_operation=SAVELOAD_OP_LOAD,
            saveload_target=SAVELOAD_TARGET_CLOUD_PRIVATE,
        )
        self.assertFalse(res_old.valid)
        self.assertFalse(res_old.c3_portal_firmware_floor_met)
        self.assertEqual(
            res_old.status, STATUS_BLOCKED_G92_CLOUD_C3_FIRMWARE_FLOOR_VIOLATION
        )

    def test_39_g92_cross_model_ilme_fx6_or_fx3a_dat_and_cloud_rejected(self) -> None:
        for foreign in ("ILME-FX6", "ILME-FX30", "ILME-FX3A", "ILCE-7SM3", "FX6"):
            res_m = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                saveload_operation=SAVELOAD_OP_LOAD,
                saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_1,
                profile_model_header=foreign,
            )
            self.assertFalse(res_m.valid, msg=foreign)
            self.assertFalse(res_m.same_model_ilme_fx3_locked)
            self.assertEqual(
                res_m.status, STATUS_BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED
            )

            res_c = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                saveload_operation=SAVELOAD_OP_LOAD,
                saveload_target=SAVELOAD_TARGET_CLOUD_SHARE,
                profile_model_header=foreign,
            )
            self.assertFalse(res_c.valid, msg=foreign)
            self.assertEqual(
                res_c.status, STATUS_BLOCKED_G92_CAMSET_OR_CLOUD_CROSS_MODEL_REJECTED
            )

    def test_40_g92_excluded_items_classifier_detects_all_five_sony_categories(
        self,
    ) -> None:
        leaked = classify_saveload_excluded_items(
            [
                "[IPTC Information]",
                "Copyright Photographer Name",
                "Custom WB 2",
                "Registered Faces / Face Memory",
                "RTMP Stream Key",
            ]
        )
        self.assertEqual(len(leaked), 5)
        for cat in SAVELOAD_EXCLUDED_ITEM_CATEGORIES:
            self.assertIn(cat, leaked)

    def test_41_g92_excluded_item_iptc_information_blocks(self) -> None:
        r1 = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            iptc_info_exported_or_overwritten=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r1.iptc_info_excluded)
        self.assertEqual(
            r1.status,
            STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
        )

        r2 = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            exported_or_overwritten_items=("IPTC Metadata Slot 1",)
        )
        self.assertFalse(r2.valid)
        self.assertFalse(r2.iptc_info_excluded)

    def test_42_g92_excluded_item_copyright_info_blocks(self) -> None:
        r1 = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            copyright_info_exported_or_overwritten=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r1.copyright_info_excluded)
        self.assertEqual(
            r1.status,
            STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
        )

    def test_43_g92_excluded_item_custom_white_balance_1_to_3_blocks(self) -> None:
        for tok in ("Custom 1", "Custom 2", "Custom 3", "Custom White Balance"):
            r = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
                exported_or_overwritten_items=(tok,)
            )
            self.assertFalse(r.valid, msg=tok)
            self.assertFalse(r.custom_wb_1_to_3_excluded)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
            )

        r_flag = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            custom_wb_1_to_3_exported_or_overwritten=True
        )
        self.assertFalse(r_flag.valid)
        self.assertFalse(r_flag.custom_wb_1_to_3_excluded)

    def test_44_g92_excluded_item_face_memory_blocks(self) -> None:
        r1 = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            face_memory_exported_or_overwritten=True
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r1.face_memory_excluded)
        self.assertEqual(
            r1.status,
            STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
        )

    def test_45_g92_excluded_item_network_credentials_ftp_rtmp_srt_wifi_tls_blocks(
        self,
    ) -> None:
        net_flags = (
            {"ftp_credentials_exported_or_overwritten": True},
            {"streaming_rtmp_srt_keys_exported_or_overwritten": True},
            {"wifi_ssid_passphrase_exported_or_overwritten": True},
            {"static_ip_or_tls_cert_exported_or_overwritten": True},
            {"exported_or_overwritten_items": ("FTP Server Password",)},
            {"exported_or_overwritten_items": ("SRT Passphrase",)},
            {"exported_or_overwritten_items": ("WPA2 Passphrase",)},
            {"exported_or_overwritten_items": ("Root Certificate PEM",)},
        )
        for kw in net_flags:
            r = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(**kw)
            self.assertFalse(r.valid, msg=str(kw))
            self.assertFalse(r.network_credentials_excluded)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
            )

    def test_46_g92_load_non_rdonly_or_card_sector_write_blocks(self) -> None:
        r_mode = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_LOAD,
            observed_load_card_access_mode="O_RDWR",
        )
        self.assertFalse(r_mode.valid)
        self.assertFalse(r_mode.load_is_card_o_rdonly_safe)
        self.assertEqual(
            r_mode.status, STATUS_BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION
        )

        r_wr = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_LOAD,
            slot1_card_sector_writes=1,
        )
        self.assertFalse(r_wr.valid)
        self.assertIn(
            STATUS_BLOCKED_G92_LOAD_CARD_NON_RDONLY_MUTATION, r_wr.violation_codes
        )

    def test_47_g92_slot1_tier0_vault_blocks_save_when_unverified_or_not_wp_locked(
        self,
    ) -> None:
        # Unverified + non-WP-locked Slot 1 Tier-0 vault card -> SAVE blocked!
        r_unverified = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_SAVE,
            saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_1,
            slot1_tier0_vault_active=True,
            slot1_present_artifacts=("pnflasha", "cnflasha", "CAMSET01.DAT"),
            slot1_off_camera_sha256_verified=False,
            slot1_sdxc_wp_locked=False,
        )
        self.assertFalse(r_unverified.valid)
        self.assertTrue(r_unverified.slot1_unverified_camset_save_blocked)
        self.assertFalse(r_unverified.slot1_vault_write_firewall_enforced)
        self.assertEqual(
            r_unverified.status,
            STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
        )

        # Even if SHA-256 verified, non-WP-locked Slot 1 vault card still blocks SAVE!
        r_no_wp = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_SAVE,
            saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_1,
            slot1_tier0_vault_active=True,
            slot1_off_camera_sha256_verified=True,
            slot1_sdxc_wp_locked=False,
        )
        self.assertFalse(r_no_wp.valid)
        self.assertEqual(
            r_no_wp.status,
            STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
        )

    def test_48_g92_slot1_wp_locked_blocks_attempted_save_write_execution(self) -> None:
        r_wp_exec = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_SAVE,
            saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_1,
            slot1_tier0_vault_active=True,
            slot1_off_camera_sha256_verified=True,
            slot1_sdxc_wp_locked=True,
            observed_slot1_save_executed=True,
        )
        self.assertFalse(r_wp_exec.valid)
        self.assertEqual(
            r_wp_exec.status,
            STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
        )

    def test_49_g92_dedicated_non_vault_slot1_card_permits_clean_save(self) -> None:
        res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            saveload_operation=SAVELOAD_OP_SAVE,
            saveload_target=SAVELOAD_TARGET_MEDIA_SLOT_1,
            camset_filename="CAMSET03.DAT",
            slot1_tier0_vault_active=False,
            slot1_present_artifacts=(),
            slot1_off_camera_sha256_verified=True,
            slot1_sdxc_wp_locked=False,
            slot1_card_sector_writes=4,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_unverified_camset_save_blocked)
        self.assertTrue(res.slot1_vault_write_firewall_enforced)

    def test_50_g92_action_item_claimed_as_stateful_reset_parameter_blocks(
        self,
    ) -> None:
        res = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(
            claimed_saveload_is_stateful_reset_parameter=True
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.action_item_not_reset_parameter)
        self.assertIn(STATUS_BLOCKED_G92_TELEMETRY_INVALID, res.violation_codes)

    def test_51_g92_telemetry_and_resolver_normalization(self) -> None:
        st = resolve_fx3_saveload_c3_and_slot1_vault_state(
            saveload_operation="[Load]",
            saveload_target="[Slot 2]",
            camset_filename="  camset10.dat  ",
            profile_model_header="  ilme-fx3  ",
            slot1_tier0_vault_active=True,
            slot1_present_artifacts=("pnflasha",),
            slot1_off_camera_sha256_verified=False,
            slot1_sdxc_wp_locked=False,
        )
        self.assertEqual(st["canonical_op"], SAVELOAD_OP_LOAD)
        self.assertEqual(st["canonical_target"], SAVELOAD_TARGET_MEDIA_SLOT_2)
        self.assertEqual(st["canonical_camset_filename"], "CAMSET10.DAT")
        self.assertTrue(st["slot1_unverified_camset_save_blocked"])

        for kw in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x12345678},
            {"firmware_version": "0.99"},
        ):
            r = verify_saveload_camset_c3_exclusions_and_slot1_vault_guard(**kw)
            self.assertFalse(r.valid, msg=str(kw))
            self.assertIn(STATUS_BLOCKED_G92_TELEMETRY_INVALID, r.violation_codes)

    def test_52_g92_evaluator_dual_mode_and_persistent_emmc_write_block(self) -> None:
        v_n, r_n = evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard()
        self.assertTrue(v_n.passed)
        self.assertTrue(r_n.valid)
        self.assertEqual(v_n.gate_code, G92_GATE_CODE)
        self.assertEqual(r_n.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r_n.persistent_emmc_writes_authorized)

        v_c, r_c = evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard(
            force_clean_room=True
        )
        self.assertTrue(v_c.passed)
        self.assertEqual(r_c.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_w, r_w = evaluate_g92_saveload_c3_exclusions_and_slot1_vault_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_w.passed)
        self.assertEqual(r_w.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # ------------------------------------------------------------------
    # Section D: Unified `92`-Gate Master Preflight & CLI (14 tests)
    # ------------------------------------------------------------------

    def test_53_92gate_offline_active_environment_89_of_92_verified(self) -> None:
        r = self.active_offline_92
        self.assertEqual(r.schema, REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA)
        self.assertEqual(r.summary["total_gates"], 92)
        self.assertEqual(r.summary["verified_gates"], 89)
        self.assertEqual(r.technical_gates_passed, 89)
        self.assertEqual(r.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r.summary["g13_to_g90_verified"], 78)
        self.assertEqual(r.summary["g91_to_g92_verified"], 2)
        self.assertTrue(r.offline_89_gates_verified)
        self.assertFalse(r.all_92_gates_verified)
        self.assertTrue(r.g13_to_g92_all_passed)
        self.assertTrue(r.g91_to_g92_all_passed)
        self.assertEqual(r.status, "VERIFIED_89_OF_92_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 92)
        self.assertEqual(r.gates[-2]["gate_id"], G91_GATE_ID)
        self.assertEqual(r.gates[-1]["gate_id"], G92_GATE_ID)

    def test_54_92gate_clean_room_offline_and_dry_run_92_of_92_verified(self) -> None:
        ro = self.clean_offline_92
        self.assertEqual(ro.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(ro.clean_room_forced)
        self.assertEqual(ro.summary["verified_gates"], 89)
        self.assertTrue(ro.offline_89_gates_verified)
        self.assertFalse(ro.all_92_gates_verified)

        rd = self.clean_dryrun_92
        self.assertEqual(rd.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rd.summary["verified_gates"], 92)
        self.assertEqual(rd.technical_gates_passed, 92)
        self.assertTrue(rd.all_92_gates_verified)
        self.assertTrue(rd.dry_run_rehearsal_only)
        self.assertEqual(
            rd.status, "VERIFIED_ALL_92_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_55_92gate_hard_redlines_remain_false_in_both_offline_and_dryrun(
        self,
    ) -> None:
        for r in (self.active_offline_92, self.clean_offline_92, self.clean_dryrun_92):
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertTrue(r.agent_auto_flash_blocked)
            self.assertFalse(r.human_hardware_attach_token)
            self.assertFalse(r.physical_flash_auto_exec_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.persistent_write_release)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)
            d = r.to_dict()
            self.assertEqual(d["summary"]["total_gates"], 92)
            self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_56_92gate_aliases_and_dry_run_simulated_backup_kwarg(self) -> None:
        self.assertIs(evaluate_92_master_safety_gates, evaluate_92gate_preflight)
        self.assertIs(run_92_gate_preflight, evaluate_92gate_preflight)
        r = run_92_gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_90_override=self.clean_dryrun_90,
        )
        self.assertTrue(r.all_92_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)

    def test_57_92gate_blocks_when_g91_fault_injected(self) -> None:
        r = evaluate_92gate_preflight(
            force_clean_room=True,
            master_90_override=self.clean_dryrun_90,
            simulate_bench_dry_run=True,
            shoe_audio_wind_kwargs={
                "observed_external_mic_wind_reduct_effective": True,
            },
        )
        self.assertFalse(r.g91_to_g92_all_passed)
        self.assertFalse(r.all_92_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G91_EXTERNAL_MIC_WIND_NOISE_REDUCT_FALSE_CLAIM
        )

    def test_58_92gate_blocks_when_g92_excluded_item_or_slot1_save_fault_injected(
        self,
    ) -> None:
        r_exc = evaluate_92gate_preflight(
            force_clean_room=True,
            master_90_override=self.clean_dryrun_90,
            simulate_bench_dry_run=True,
            saveload_c3_exclusions_kwargs={
                "iptc_info_exported_or_overwritten": True,
            },
        )
        self.assertFalse(r_exc.g91_to_g92_all_passed)
        self.assertEqual(
            r_exc.status,
            STATUS_BLOCKED_G92_EXCLUDED_PRIVACY_CALIBRATION_OR_CREDENTIAL_LEAK,
        )

        r_s1 = evaluate_92gate_preflight(
            force_clean_room=True,
            master_90_override=self.clean_dryrun_90,
            simulate_bench_dry_run=True,
            saveload_c3_exclusions_kwargs={
                "saveload_operation": SAVELOAD_OP_SAVE,
                "saveload_target": SAVELOAD_TARGET_MEDIA_SLOT_1,
            },
        )
        self.assertFalse(r_s1.g91_to_g92_all_passed)
        self.assertEqual(
            r_s1.status,
            STATUS_BLOCKED_G92_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
        )

    def test_59_92gate_blocks_when_persistent_emmc_writes_requested(self) -> None:
        r = evaluate_92gate_preflight(
            force_clean_room=True,
            master_90_override=self.clean_dryrun_90,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r.all_92_gates_verified)
        self.assertFalse(r.offline_89_gates_verified)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_60_92gate_propagates_upstream_g13_to_g90_failure(self) -> None:
        bad_90 = fx3_safety.evaluate_90gate_preflight(
            force_clean_room=True,
            master_88_override=self.clean_offline_90.master_88_report
            if hasattr(self.clean_offline_90, "master_88_report")
            and not isinstance(self.clean_offline_90.master_88_report, dict)
            else fx3_safety.evaluate_88gate_preflight(force_clean_room=True),
            touch_op_sunny_weather_kwargs={
                "pre_reset_monitor_brightness_mode": "Sunny Weather",
                "indoor_bench_environment": True,
            },
        )
        r = evaluate_92gate_preflight(
            force_clean_room=True, master_90_override=bad_90
        )
        self.assertFalse(r.g13_to_g92_all_passed)
        self.assertEqual(r.status, bad_90.status)

    def test_61_cli_verify_shoe_audio_wind_guard_text_and_json_and_alias(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-shoe-audio-wind-guard"])
        self.assertEqual(rc, 0)
        self.assertIn(G91_GATE_ID, buf.getvalue())
        self.assertIn("meter_4ch_expanded=True", buf.getvalue())

        buf_j = io.StringIO()
        with contextlib.redirect_stdout(buf_j):
            rc_j = cli_main(
                ["verify-g91-shoe-audio-wind", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_j.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_62_cli_verify_saveload_c3_exclusions_guard_text_and_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-saveload-c3-exclusions-guard"])
        self.assertEqual(rc, 0)
        self.assertIn(G92_GATE_ID, buf.getvalue())
        self.assertIn("exclusions_ok=True", buf.getvalue())
        self.assertIn("slot1_save_blocked=True", buf.getvalue())

        buf_j = io.StringIO()
        with contextlib.redirect_stdout(buf_j):
            rc_j = cli_main(
                ["verify-g92-saveload-c3-exclusions", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_j.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_63_cli_verify_92_gates_offline_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-92-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=89/92", buf.getvalue())
        self.assertIn("VERIFIED_89_OF_92_AWAITING_PHYSICAL_TIER0", buf.getvalue())

        with mock.patch(
            "fx3_safety.__main__.evaluate_92gate_preflight",
            return_value=self.clean_offline_92,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(["verify-92-gates", "--force-clean-room", "--json"])
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_j.getvalue())
        self.assertEqual(
            payload["schema"], REALHW_SHOE_AUDIO_WIND_SAVELOAD_C3_92GATE_SCHEMA
        )
        self.assertEqual(payload["summary"]["verified_gates"], 89)

    def test_64_cli_verify_92_gates_simulate_bench_dry_run_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-92-gates",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn("verified=92/92", buf.getvalue())
        self.assertIn("all_92_gates_verified=True", buf.getvalue())

        with mock.patch(
            "fx3_safety.__main__.evaluate_92gate_preflight",
            return_value=self.clean_dryrun_92,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(
                    [
                        "verify-92-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_j.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 92)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_65_standalone_module_main_text_and_json_modes(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.evaluate_92gate_preflight",
            return_value=self.clean_offline_92,
        ):
            buf_t = io.StringIO()
            with contextlib.redirect_stdout(buf_t):
                rc_t = module_main(["--force-clean-room"])
            self.assertEqual(rc_t, 0)
            self.assertIn("verified=89/92", buf_t.getvalue())

        with mock.patch(
            "fx3_safety.realhw_shoe_audio_wind_saveload_c3_and_92gate_guard.evaluate_92gate_preflight",
            return_value=self.clean_dryrun_92,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            data = json.loads(buf_j.getvalue())
            self.assertEqual(data["summary"]["verified_gates"], 92)

    def test_66_donor_check_budget_constant_is_100ms(self) -> None:
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE241, 0.10)
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(SHOOT_MODE_MOVIE_G91, "Movie")
        self.assertEqual(SAVELOAD_OP_NONE, "NONE")
        self.assertEqual(RESET_ACTION_NONE, "NONE")


if __name__ == "__main__":
    unittest.main()
