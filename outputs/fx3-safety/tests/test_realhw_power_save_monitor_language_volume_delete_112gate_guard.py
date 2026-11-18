"""Phase 273 (Task H309, 112/112 Safety Gates, Wave-46) Dual-Mode Unit Tests
(76 tests, < 5.0s runtime) for
`fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard`:

- Gate `G111` (`GATE_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD`):
  - Empirical `[Power Save by Monitor]` reality split: stock `ILME-FX3 Ver. 7.02`
    (`ilc/2210`) `[Setup] -> [Power Setting Option]` exposes ONLY 2 menu items
    (`[Power Save Start Time]`, `[Auto Power OFF Temp.]`),
    `fx3_ui_exposes_power_save_by_monitor == False`, and rejects spoofed
    `"Open: On/Close: Off"` strings, while shared `BIONZ XR` `appFw.so`
    (`BKID_APP_setting_monitor_power_linkage`) + `string_english_f.uxc`
    (`0x60b9`) compile the exact 4 modes (`Both Linked` `0x6db5`,
    `Open: Return` `0x6db6`, `Close: Power Save` `0x60a8`, `Does Not Link`
    `0x6b2e`), requiring `Does Not Link` or `Open: Return` when a sibling
    exposing body runs headless HDMI with LCD closed.
  - `[Power Save Start Time]` (`BKID_APP_setting_start_power_saving`) 9 official
    Sony deactivation conditions + air-gapped battery bench guard (blocks
    zero-bypass battery runs unless `Off` or `30 Min`).
  - `[Language]` (`BK_LANG` `0x02cf019c`) FX3 34-vs-FX6 29 parity (`0x90ff0` 4B
    `0` vs `0x89242` 1B `0x00`/`0x19`), Stage-B 4-language parity, and `(Setup)`
    survival across `[Camera Settings Reset]` + `[Reset Network Set.]`.
- Gate `G112` (`GATE_G112_VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD`):
  - `[Volume Settings]` (`0..15`, factory default `7`, `resid16=0xe8c9`),
    separation from `[Audio signals]`, and `XLR-H1` MI-Shoe mic speaker
    acoustic feedback guard (`volume <= 7` or headphones).
  - `[4ch Audio Monitoring]` exact 5 routes (`CH1/CH2`, `CH3/CH4`,
    `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2`), separation from HDMI
    `[4ch Audio Output]`, and `3.5 mm` 2ch headphone boundary.
  - `[Delete confirm.]` exact 2 modes (`"Cancel" first` default vs
    `"Delete" first`) + `[Delete pressing twice]` (`Off` default), `(Playback)`
    reset survival, and hard `Slot-1` recovery vault delete/format firewall.
- Unified `112`-Gate Master Safety Preflight (`evaluate_112gate_preflight` /
  `verify-112-gates`): `109/112` offline and `112/112` in
  `--simulate-bench-dry-run` with all hardware write/live-attach redlines
  hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard import (
    ALLOWED_4CH_AUDIO_MONITORING_ROUTES_G112,
    ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G111,
    ALLOWED_DELETE_CONFIRM_MODES_G112,
    ALLOWED_DELETE_PRESSING_TWICE_MODES_G112,
    ALLOWED_MEDIA_OPS_G112,
    ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111,
    ALLOWED_POWER_SAVE_START_TIMES_G111,
    ALLOWED_RESET_ACTIONS_PHASE273,
    ALLOWED_STAGE_B_LANGUAGES_G111,
    ALLOWED_TARGET_SLOTS_G112,
    ALLOWED_VOLUME_SETTINGS_G112,
    AUDIO_MON_CH1_3_CH2_4_G112,
    AUDIO_MON_CH1_CH1_G112,
    AUDIO_MON_CH1_CH2_G112,
    AUDIO_MON_CH2_CH2_G112,
    AUDIO_MON_CH3_CH4_G112,
    AUDIO_MON_FACTORY_DEFAULT_G112,
    AUDIO_MON_ROUTE_METADATA_G112,
    AUDIO_MONITORING_4CH_MENU_PATH_G112,
    AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
    AUTO_POWER_OFF_TEMP_HIGH_G111,
    AUTO_POWER_OFF_TEMP_MENU_PATH_G111,
    AUTO_POWER_OFF_TEMP_STANDARD_G111,
    BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111,
    BK_LANG_PROPERTY_ID_G111,
    DEFAULT_REPO_ROOT,
    DELETE_CONFIRM_CANCEL_FIRST_G112,
    DELETE_CONFIRM_DELETE_FIRST_G112,
    DELETE_CONFIRM_FACTORY_DEFAULT_G112,
    DELETE_CONFIRM_MENU_PATH_G112,
    DELETE_CONFIRM_RESID16_MAP_G112,
    DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112,
    DELETE_PRESSING_TWICE_MENU_PATH_G112,
    DELETE_PRESSING_TWICE_OFF_G112,
    DELETE_PRESSING_TWICE_ON_G112,
    DELETE_PRESSING_TWICE_RESID16_G112,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE273,
    DONOR_CHECK_MAX_SECONDS_PHASE273,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE273,
    FX3_ALLLANG_BK_LANG_SEED_G111,
    FX3_BK4_LANG_OFFSET_G111,
    FX3_BK4_LANG_WIDTH_BYTES_G111,
    FX3_DEFAULT_FW_VERSION_PHASE273,
    FX3_HELP_GUIDE_CODE_PHASE273,
    FX3_LANGUAGE_COUNT_G111,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_NON_EXPOSING_BODY_MODELS_G111,
    FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111,
    FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR_G111,
    FX3A_MODEL_NAME,
    FX6_BK4_LANG_OFFSET_G111,
    FX6_BK4_LANG_WIDTH_BYTES_G111,
    FX6_CN1_BK_LANG_SEED_G111,
    FX6_DEFAULT_FW_VERSION_PHASE273,
    FX6_LANGUAGE_COUNT_G111,
    FX6_MODEL_NAME,
    FX6_NTSC_BK_LANG_SEED_G111,
    G111,
    G111_GATE_CODE,
    G111_GATE_ID,
    G112,
    G112_GATE_CODE,
    G112_GATE_ID,
    GATE_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD,
    GATE_G112_VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G112,
    HDMI_4CH_AUDIO_OUTPUT_RESID16_G112,
    HDMI_4CH_AUDIO_OUTPUT_ROUTES_G112,
    HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LANGUAGE_CODE_EN_G111,
    LANGUAGE_CODE_JAPANESE_G111,
    LANGUAGE_CODE_SCHINESE_G111,
    LANGUAGE_CODE_TCHINESE_G111,
    LANGUAGE_MENU_PATH_G111,
    LANGUAGE_OOB_PROMPT_DEFAULT_G111,
    LANGUAGE_UXC_RESID16_G111,
    MEDIA_OP_DELETE_DATE_G112,
    MEDIA_OP_DELETE_FOLDER_G112,
    MEDIA_OP_DELETE_MULTIPLE_G112,
    MEDIA_OP_DELETE_PRESSING_TWICE_G112,
    MEDIA_OP_DELETE_SINGLE_G112,
    MEDIA_OP_FORMAT_FULL_G112,
    MEDIA_OP_FORMAT_QUICK_G112,
    MEDIA_OP_NONE_G112,
    MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
    MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
    MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
    MONITOR_POWER_LINKAGE_FACTORY_DEFAULT_G111,
    MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
    MONITOR_POWER_LINKAGE_UXC_METADATA_G111,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_APPFW_FULL_SHA256_PHASE273,
    PINNED_APPFW_SLICES_PHASE273,
    PINNED_APPFW_SLICES_SHA256_PHASE273,
    PINNED_PHASE273_DONOR_SPECS,
    POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111,
    POWER_SAVE_BY_MONITOR_APPFW_TITLE_G111,
    POWER_SAVE_BY_MONITOR_RESID16_G111,
    POWER_SAVE_START_TIME_10_SEC_G111,
    POWER_SAVE_START_TIME_1_MIN_G111,
    POWER_SAVE_START_TIME_2_MIN_G111,
    POWER_SAVE_START_TIME_30_MIN_G111,
    POWER_SAVE_START_TIME_5_MIN_G111,
    POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111,
    POWER_SAVE_START_TIME_MENU_PATH_G111,
    POWER_SAVE_START_TIME_OFF_G111,
    POWER_SETTING_OPTION_MENU_PATH_G111,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_SCHEMA,
    REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE273,
    SAFE_HEADLESS_MONITOR_POWER_LINKAGE_MODES_G111,
    SIBLING_EXPOSING_BODY_MODELS_G111,
    SPI_NOR_WRITE_AUTHORIZED,
    SPOOF_FAKE_MONITOR_MODE_G111,
    STAGE_B_4_LANGUAGE_PARITY_TABLE_G111,
    STATUS_BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD,
    STATUS_BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD,
    STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION,
    STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION,
    STATUS_BLOCKED_G111_TELEMETRY_INVALID,
    STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION,
    STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION,
    STATUS_BLOCKED_G112_TELEMETRY_INVALID,
    STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION,
    STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY,
    STATUS_VERIFIED_G111,
    STATUS_VERIFIED_G112,
    TARGET_SLOT_1_G112,
    TARGET_SLOT_2_G112,
    TARGET_SLOT_NONE_G112,
    USB_PACKETS_TRANSMITTED,
    VOLUME_SETTINGS_FACTORY_DEFAULT_G112,
    VOLUME_SETTINGS_MAX_G112,
    VOLUME_SETTINGS_MENU_PATH_G112,
    VOLUME_SETTINGS_MIN_G112,
    VOLUME_SETTINGS_RESID16_G112,
    XLR_H1_INTERNAL_SPEAKER_SAFE_MAX_VOLUME_G112,
    _is_forced_clean_room,
    audit_phase273_donor_contracts,
    compute_power_save_monitor_and_language_matrix,
    compute_volume_4chmon_and_delete_confirm_matrix,
    evaluate_110gate_preflight,
    evaluate_112_master_safety_gates,
    evaluate_112gate_preflight,
    evaluate_g111_power_save_monitor_and_language_guard,
    evaluate_g112_volume_4chmon_delete_confirm_guard,
    main as module_main,
    resolve_fx3_power_save_monitor_and_language_state,
    resolve_fx3_volume_4chmon_and_delete_confirm_state,
    run_112_gate_preflight,
    verify_power_save_monitor_and_language_guard,
    verify_volume_4chmon_delete_confirm_guard,
)


def _clean_env_without_cleanroom() -> dict[str, str]:
    return {
        k: v
        for k, v in os.environ.items()
        if k not in (ENV_CLEAN_ROOM_TEST_PHASE273, "FX3_FX6_FORCE_CLEAN_ROOM")
    }


def _subprocess_timeout_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 10.0


class TestPhase273PowerSaveMonitorLanguageVolumeDelete112GateGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = audit_phase273_donor_contracts(force_clean_room=True)
        cls.clean_offline_110 = evaluate_110gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        cls.clean_dryrun_110 = evaluate_110gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )

    # ------------------------------------------------------------------
    # 1..4: Exports, schema, redlines & donor budget constants
    # ------------------------------------------------------------------

    def test_01_public_exports_and_schema_constants(self) -> None:
        self.assertEqual(
            REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_SCHEMA,
            "realhw_power_save_monitor_language_volume_delete_and_112gate_guard_v1",
        )
        self.assertEqual(
            REALHW_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_112GATE_VERSION,
            "1.0.0",
        )
        self.assertIn("evaluate_112gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "evaluate_g111_power_save_monitor_and_language_guard",
            fx3_safety.__all__,
        )
        self.assertIn(
            "evaluate_g112_volume_4chmon_delete_confirm_guard",
            fx3_safety.__all__,
        )
        self.assertIs(
            fx3_safety.evaluate_112gate_preflight,
            evaluate_112gate_preflight,
        )
        self.assertIs(
            fx3_safety.run_112_gate_preflight,
            run_112_gate_preflight,
        )
        self.assertIs(
            fx3_safety.evaluate_112_master_safety_gates,
            evaluate_112_master_safety_gates,
        )

    def test_02_gate_ids_and_codes(self) -> None:
        self.assertEqual(G111, G111_GATE_ID)
        self.assertEqual(G112, G112_GATE_ID)
        self.assertEqual(
            G111_GATE_ID,
            "G111_power_save_monitor_split_start_time_9cond_and_language_bk_lang_guard",
        )
        self.assertEqual(
            G112_GATE_ID,
            "G112_volume_settings_4ch_audio_monitoring_and_delete_confirm_slot1_vault_guard",
        )
        self.assertEqual(
            G111_GATE_CODE,
            "POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD",
        )
        self.assertEqual(
            G112_GATE_CODE,
            "VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD",
        )
        self.assertEqual(
            G111_GATE_CODE,
            GATE_G111_POWER_SAVE_MONITOR_SPLIT_START_TIME_9COND_AND_LANGUAGE_BK_LANG_GUARD,
        )
        self.assertEqual(
            G112_GATE_CODE,
            GATE_G112_VOLUME_SETTINGS_4CH_AUDIO_MONITORING_AND_DELETE_CONFIRM_SLOT1_VAULT_GUARD,
        )

    def test_03_hard_safety_redlines_locked(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_04_donor_specs_and_budget_constants(self) -> None:
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE273, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE273, 1.00)
        self.assertEqual(len(PINNED_PHASE273_DONOR_SPECS), 8)
        self.assertEqual(len(PINNED_APPFW_SLICES_PHASE273), 16)
        self.assertEqual(len(PINNED_APPFW_SLICES_SHA256_PHASE273), 64)
        self.assertEqual(len(PINNED_APPFW_FULL_SHA256_PHASE273), 64)

    # ------------------------------------------------------------------
    # 5..14: O_RDONLY Local Donor Audit & Clean-Room Fallback
    # ------------------------------------------------------------------

    def test_05_donor_audit_clean_room_explicit(self) -> None:
        res = self.clean_audit
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.within_budget_200ms)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertEqual(res.fx3_bk_lang_seed_value, 0)
        self.assertEqual(res.fx6_ntsc_bk_lang_seed_value, 0x00)
        self.assertEqual(res.fx6_cn1_bk_lang_seed_value, 0x19)
        self.assertTrue(res.spoof_open_on_close_off_absent_in_uxc)

    def test_06_donor_audit_dual_mode_env_flags(self) -> None:
        for key in (ENV_CLEAN_ROOM_TEST_PHASE273, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                res = audit_phase273_donor_contracts()
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_07_donor_audit_missing_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_phase273_donor_contracts(work_root=Path(td))
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_08_donor_audit_local_o_rdonly_if_present(self) -> None:
        with mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True):
            res = audit_phase273_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.spoof_open_on_close_off_absent_in_uxc)
        self.assertEqual(res.fx3_bk_lang_seed_value, 0)
        self.assertEqual(res.fx6_ntsc_bk_lang_seed_value, 0)
        self.assertEqual(res.fx6_cn1_bk_lang_seed_value, 0x19)
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res.access_mode, "O_RDONLY")
            self.assertEqual(res.files_inspected, 8)
            budget = (
                DONOR_CHECK_CI_MAX_SECONDS_PHASE273
                if os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
                else DONOR_CHECK_MAX_SECONDS_PHASE273
            )
            self.assertLessEqual(res.elapsed_seconds, budget)

    def test_09_donor_audit_uses_os_o_rdonly_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            synthetic_blobs: dict[str, bytes] = {}
            for key, (_body, rel, exp_size, _sha, tokens, _label) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if key == "fx3_bk4_bin":
                    buf = bytearray(b"\x00" * (FX3_BK4_LANG_OFFSET_G111 + 64))
                    buf[0:4] = b"BK4\x00"
                    buf[16:24] = b"ILME-FX3"
                    blob = bytes(buf)
                elif key == "fx6_bk4_ntsc_bin":
                    buf = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 64))
                    buf[0:4] = b"BK4\x00"
                    blob = bytes(buf)
                elif key == "fx6_bk4_cn1_bin":
                    buf = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 64))
                    buf[0:4] = b"BK4\x00"
                    buf[FX6_BK4_LANG_OFFSET_G111] = 0x19
                    blob = bytes(buf)
                else:
                    blob = b"|".join(tokens)
                p.write_bytes(blob)
                synthetic_blobs[key] = blob

            patched_specs = {
                k: (
                    v[0],
                    v[1],
                    v[2] if k == "fx3_appfw_so" else len(synthetic_blobs[k]),
                    v[3]
                    if k == "fx3_appfw_so"
                    else hashlib.sha256(synthetic_blobs[k]).hexdigest(),
                    v[4],
                    v[5],
                )
                for k, v in PINNED_PHASE273_DONOR_SPECS.items()
            }

            opened_flags: list[int] = []
            real_open = os.open

            def _tracking_open(path, flags, *a, **kw):
                if str(work_root) in str(path):
                    opened_flags.append(flags)
                return real_open(path, flags, *a, **kw)

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch.dict(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard.PINNED_PHASE273_DONOR_SPECS",
                    patched_specs,
                    clear=True,
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, PINNED_APPFW_SLICES_SHA256_PHASE273, True),
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
                mock.patch("os.open", side_effect=_tracking_open),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)

            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.files_inspected, 8)
            self.assertEqual(len(opened_flags), 7)
            for f in opened_flags:
                self.assertEqual(f & os.O_ACCMODE, os.O_RDONLY)

    def test_10_donor_audit_blocks_corrupted_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"corrupt")
            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._DONOR_BLOB_CACHE",
                    {},
                ),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)
        self.assertFalse(res.fx3_contracts_verified)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_11_donor_audit_blocks_spoofed_open_on_close_off_in_uxc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")

            def _fake_cached(path: Path):
                s = str(path)
                for key, (_body, rel, exp_sz, exp_sha, tokens, _label) in PINNED_PHASE273_DONOR_SPECS.items():
                    if s.endswith(rel):
                        if key == "fx3_string_english_f_uxc":
                            blob = b"|".join(tokens) + b"|" + SPOOF_FAKE_MONITOR_MODE_G111.encode("utf-8")
                            return exp_sz, exp_sha, blob
                        if key == "fx3_bk4_bin":
                            b_arr = bytearray(b"\x00" * (FX3_BK4_LANG_OFFSET_G111 + 8))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[10:18] = b"ILME-FX3"
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_ntsc_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_cn1_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[FX6_BK4_LANG_OFFSET_G111] = 0x19
                            return exp_sz, exp_sha, bytes(b_arr)
                        return exp_sz, exp_sha, b"|".join(tokens)
                raise AssertionError(s)

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, PINNED_APPFW_SLICES_SHA256_PHASE273, True),
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_cached_donor_o_rdonly",
                    side_effect=_fake_cached,
                ),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)

        self.assertFalse(res.valid)
        self.assertFalse(res.spoof_open_on_close_off_absent_in_uxc)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)

    def test_12_donor_audit_blocks_bk_lang_seed_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")

            def _fake_cached(path: Path):
                s = str(path)
                for key, (_body, rel, exp_sz, exp_sha, tokens, _label) in PINNED_PHASE273_DONOR_SPECS.items():
                    if s.endswith(rel):
                        if key == "fx3_bk4_bin":
                            b_arr = bytearray(b"\x00" * (FX3_BK4_LANG_OFFSET_G111 + 8))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[10:18] = b"ILME-FX3"
                            b_arr[FX3_BK4_LANG_OFFSET_G111] = 0x19  # wrong: expected 0x00
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_ntsc_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_cn1_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[FX6_BK4_LANG_OFFSET_G111] = 0x00  # wrong: expected 0x19
                            return exp_sz, exp_sha, bytes(b_arr)
                        return exp_sz, exp_sha, b"|".join(tokens)
                raise AssertionError(s)

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, PINNED_APPFW_SLICES_SHA256_PHASE273, True),
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_cached_donor_o_rdonly",
                    side_effect=_fake_cached,
                ),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)

        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)
        self.assertEqual(res.fx3_bk_lang_seed_value, 0x19)
        self.assertEqual(res.fx6_cn1_bk_lang_seed_value, 0x00)

    def test_13_donor_audit_blocks_budget_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")

            def _fake_cached(path: Path):
                s = str(path)
                for key, (_body, rel, exp_sz, exp_sha, tokens, _label) in PINNED_PHASE273_DONOR_SPECS.items():
                    if s.endswith(rel):
                        if key == "fx3_bk4_bin":
                            b_arr = bytearray(b"\x00" * (FX3_BK4_LANG_OFFSET_G111 + 8))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[10:18] = b"ILME-FX3"
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_ntsc_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            return exp_sz, exp_sha, bytes(b_arr)
                        if key == "fx6_bk4_cn1_bin":
                            b_arr = bytearray(b"\x00" * (FX6_BK4_LANG_OFFSET_G111 + 4))
                            b_arr[0:4] = b"BK4\x00"
                            b_arr[FX6_BK4_LANG_OFFSET_G111] = 0x19
                            return exp_sz, exp_sha, bytes(b_arr)
                        return exp_sz, exp_sha, b"|".join(tokens)
                raise AssertionError(s)

            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_targeted_slices_o_rdonly",
                    return_value=(79_015_712, PINNED_APPFW_SLICES_SHA256_PHASE273, True),
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_cached_donor_o_rdonly",
                    side_effect=_fake_cached,
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard.time.perf_counter",
                    side_effect=[100.0, 125.0],
                ),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)

        self.assertFalse(res.valid)
        self.assertFalse(res.within_budget_200ms)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)

    def test_14_donor_audit_handles_oserror_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _k, (_body, rel, *_rest) in PINNED_PHASE273_DONOR_SPECS.items():
                p = work_root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")
            with (
                mock.patch.dict(os.environ, _clean_env_without_cleanroom(), clear=True),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_targeted_slices_o_rdonly",
                    side_effect=OSError("EIO"),
                ),
                mock.patch(
                    "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard._read_cached_donor_o_rdonly",
                    side_effect=OSError("EIO"),
                ),
            ):
                res = audit_phase273_donor_contracts(work_root=work_root)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # 15..36: Gate G111 — Power Save by Monitor Split, Start Time, Language
    # ------------------------------------------------------------------

    def test_15_g111_baseline_defaults_pass(self) -> None:
        res = verify_power_save_monitor_and_language_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G111)
        self.assertFalse(res.fx3_ui_exposes_power_save_by_monitor)
        self.assertEqual(
            res.power_setting_option_items,
            FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111,
        )
        self.assertEqual(len(res.appfw_monitor_power_linkage_modes), 4)
        self.assertEqual(
            res.effective_post_reset_power_save_start_time,
            POWER_SAVE_START_TIME_OFF_G111,
        )
        self.assertEqual(
            res.effective_post_reset_auto_power_off_temp,
            AUTO_POWER_OFF_TEMP_STANDARD_G111,
        )
        self.assertEqual(res.effective_post_reset_language, LANGUAGE_CODE_EN_G111)
        self.assertEqual(res.bk_lang_property_id_hex, "0x02cf019c")
        self.assertEqual(res.fx3_language_count, FX3_LANGUAGE_COUNT_G111)
        self.assertEqual(res.fx6_language_count, FX6_LANGUAGE_COUNT_G111)
        self.assertEqual(res.matrix_states_checked, 192)

    def test_16_g111_constants_and_metadata_exact_values(self) -> None:
        self.assertFalse(FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR_G111)
        self.assertEqual(len(FX3_POWER_SETTING_OPTION_EXACT_2_ITEMS_G111), 2)
        self.assertEqual(
            FX3_NON_EXPOSING_BODY_MODELS_G111,
            (FX3_MODEL_NAME, FX3A_MODEL_NAME, FX6_MODEL_NAME),
        )
        self.assertEqual(
            SIBLING_EXPOSING_BODY_MODELS_G111,
            ("ILME-FX2", "ILCE-7M4", "ZV-E1", "ILCE-6700"),
        )
        self.assertEqual(SPOOF_FAKE_MONITOR_MODE_G111, "Open: On/Close: Off")
        self.assertEqual(POWER_SAVE_BY_MONITOR_APPFW_TITLE_G111, "Power Save by Monitor")
        self.assertEqual(POWER_SAVE_BY_MONITOR_RESID16_G111, 0x60B9)
        self.assertEqual(
            ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111,
            (
                MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
                MONITOR_POWER_LINKAGE_OPEN_RETURN_G111,
                MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
                MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111,
            ),
        )
        self.assertEqual(
            MONITOR_POWER_LINKAGE_FACTORY_DEFAULT_G111,
            MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
        )
        self.assertEqual(
            MONITOR_POWER_LINKAGE_UXC_METADATA_G111[MONITOR_POWER_LINKAGE_BOTH_LINKED_G111],
            (0x6DB5, "ON_ALL"),
        )
        self.assertEqual(
            MONITOR_POWER_LINKAGE_UXC_METADATA_G111[MONITOR_POWER_LINKAGE_OPEN_RETURN_G111],
            (0x6DB6, "ON_OPEN"),
        )
        self.assertEqual(
            MONITOR_POWER_LINKAGE_UXC_METADATA_G111[MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111],
            (0x60A8, "ON_CLOSE"),
        )
        self.assertEqual(
            MONITOR_POWER_LINKAGE_UXC_METADATA_G111[MONITOR_POWER_LINKAGE_DOES_NOT_LINK_G111],
            (0x6B2E, "OFF"),
        )

    def test_17_g111_power_save_start_time_and_9_conditions_constants(self) -> None:
        self.assertEqual(
            ALLOWED_POWER_SAVE_START_TIMES_G111,
            (
                POWER_SAVE_START_TIME_OFF_G111,
                POWER_SAVE_START_TIME_30_MIN_G111,
                POWER_SAVE_START_TIME_5_MIN_G111,
                POWER_SAVE_START_TIME_2_MIN_G111,
                POWER_SAVE_START_TIME_1_MIN_G111,
                POWER_SAVE_START_TIME_10_SEC_G111,
            ),
        )
        self.assertEqual(
            POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111,
            POWER_SAVE_START_TIME_5_MIN_G111,
        )
        self.assertEqual(
            BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111,
            (POWER_SAVE_START_TIME_OFF_G111, POWER_SAVE_START_TIME_30_MIN_G111),
        )
        self.assertEqual(len(POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111), 9)
        self.assertEqual(
            AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
            AUTO_POWER_OFF_TEMP_STANDARD_G111,
        )
        self.assertEqual(
            ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G111,
            (AUTO_POWER_OFF_TEMP_STANDARD_G111, AUTO_POWER_OFF_TEMP_HIGH_G111),
        )

    def test_18_g111_bk_lang_constants_and_4lang_parity(self) -> None:
        self.assertEqual(BK_LANG_PROPERTY_ID_G111, 0x02CF019C)
        self.assertEqual(LANGUAGE_UXC_RESID16_G111, 0xE397)
        self.assertEqual(FX3_LANGUAGE_COUNT_G111, 34)
        self.assertEqual(FX6_LANGUAGE_COUNT_G111, 29)
        self.assertEqual(FX3_BK4_LANG_OFFSET_G111, 0x90FF0)
        self.assertEqual(FX3_BK4_LANG_WIDTH_BYTES_G111, 4)
        self.assertEqual(FX6_BK4_LANG_OFFSET_G111, 0x89242)
        self.assertEqual(FX6_BK4_LANG_WIDTH_BYTES_G111, 1)
        self.assertEqual(FX3_ALLLANG_BK_LANG_SEED_G111, 0)
        self.assertEqual(FX6_NTSC_BK_LANG_SEED_G111, 0x00)
        self.assertEqual(FX6_CN1_BK_LANG_SEED_G111, 0x19)
        self.assertEqual(LANGUAGE_OOB_PROMPT_DEFAULT_G111, "—")
        self.assertEqual(
            STAGE_B_4_LANGUAGE_PARITY_TABLE_G111[LANGUAGE_CODE_EN_G111]["bk_lang_id"], 0x00
        )
        self.assertEqual(
            STAGE_B_4_LANGUAGE_PARITY_TABLE_G111[LANGUAGE_CODE_JAPANESE_G111]["bk_lang_id"], 0x01
        )
        self.assertEqual(
            STAGE_B_4_LANGUAGE_PARITY_TABLE_G111[LANGUAGE_CODE_TCHINESE_G111]["bk_lang_id"], 0x18
        )
        self.assertEqual(
            STAGE_B_4_LANGUAGE_PARITY_TABLE_G111[LANGUAGE_CODE_SCHINESE_G111]["bk_lang_id"], 0x19
        )

    def test_19_g111_blocks_fx3_exposing_power_save_by_monitor_ui_spoof(self) -> None:
        res = verify_power_save_monitor_and_language_guard(
            claimed_fx3_ui_exposes_power_save_by_monitor=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION)
        self.assertGreater(res.power_save_monitor_ui_spoof_events, 0)

    def test_20_g111_blocks_power_setting_option_extra_item_spoof(self) -> None:
        res = verify_power_save_monitor_and_language_guard(
            claimed_power_setting_option_items=(
                "Power Save Start Time",
                "Power Save by Monitor",
                "Auto Power OFF Temp.",
            ),
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION)

    def test_21_g111_blocks_open_on_close_off_fake_string(self) -> None:
        res = verify_power_save_monitor_and_language_guard(
            monitor_power_linkage_audit_active=True,
            audit_body_model="ILCE-7M4",
            pre_reset_monitor_power_linkage=SPOOF_FAKE_MONITOR_MODE_G111,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION)

    def test_22_g111_sibling_body_headless_closed_lcd_safe_modes_pass(self) -> None:
        for body in SIBLING_EXPOSING_BODY_MODELS_G111:
            for mode in SAFE_HEADLESS_MONITOR_POWER_LINKAGE_MODES_G111:
                res = verify_power_save_monitor_and_language_guard(
                    monitor_power_linkage_audit_active=True,
                    audit_body_model=body,
                    pre_reset_monitor_power_linkage=mode,
                    lcd_folded_inward_headless_hdmi=True,
                )
                self.assertTrue(res.valid, msg=f"{body}/{mode}: {res.errors}")
                self.assertEqual(res.headless_monitor_close_sleep_events, 0)

    def test_23_g111_sibling_body_headless_closed_lcd_blocks_close_sleep_modes(self) -> None:
        for mode in (
            MONITOR_POWER_LINKAGE_BOTH_LINKED_G111,
            MONITOR_POWER_LINKAGE_CLOSE_POWER_SAVE_G111,
        ):
            res = verify_power_save_monitor_and_language_guard(
                monitor_power_linkage_audit_active=True,
                audit_body_model="ZV-E1",
                pre_reset_monitor_power_linkage=mode,
                lcd_folded_inward_headless_hdmi=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G111_HEADLESS_MONITOR_CLOSE_SLEEP_HAZARD)
            self.assertEqual(res.headless_monitor_close_sleep_events, 1)

    def test_24_g111_sibling_body_open_lcd_allows_all_4_appfw_modes(self) -> None:
        for mode in ALLOWED_MONITOR_POWER_LINKAGE_MODES_G111:
            res = verify_power_save_monitor_and_language_guard(
                monitor_power_linkage_audit_active=True,
                audit_body_model="ILME-FX2",
                pre_reset_monitor_power_linkage=mode,
                lcd_folded_inward_headless_hdmi=False,
            )
            self.assertTrue(res.valid, msg=res.errors)

    def test_25_g111_airgapped_battery_bench_blocks_short_timeouts_without_bypass(self) -> None:
        for t in (
            POWER_SAVE_START_TIME_5_MIN_G111,
            POWER_SAVE_START_TIME_2_MIN_G111,
            POWER_SAVE_START_TIME_1_MIN_G111,
            POWER_SAVE_START_TIME_10_SEC_G111,
        ):
            res = verify_power_save_monitor_and_language_guard(
                pre_reset_power_save_start_time=t,
                active_deactivation_conditions=(),
                air_gapped_battery_bench=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G111_BATTERY_BENCH_IDLE_SLEEP_HAZARD)
            self.assertEqual(res.battery_bench_idle_sleep_events, 1)

    def test_26_g111_airgapped_battery_bench_allows_off_and_30min(self) -> None:
        for t in BATTERY_BENCH_SAFE_POWER_SAVE_TIMES_G111:
            res = verify_power_save_monitor_and_language_guard(
                pre_reset_power_save_start_time=t,
                active_deactivation_conditions=(),
                air_gapped_battery_bench=True,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.battery_bench_idle_sleep_events, 0)

    def test_27_g111_all_9_deactivation_conditions_bypass_battery_idle_sleep(self) -> None:
        for cond in POWER_SAVE_9_DEACTIVATION_CONDITIONS_G111:
            res = verify_power_save_monitor_and_language_guard(
                pre_reset_power_save_start_time=POWER_SAVE_START_TIME_10_SEC_G111,
                active_deactivation_conditions=(cond,),
                air_gapped_battery_bench=False,
            )
            self.assertTrue(res.valid, msg=f"{cond}: {res.errors}")
            self.assertTrue(res.power_save_bypass_active)
            self.assertEqual(res.battery_bench_idle_sleep_events, 0)

    def test_28_g111_stage_b_4_languages_pass(self) -> None:
        for lang in ALLOWED_STAGE_B_LANGUAGES_G111:
            res = verify_power_save_monitor_and_language_guard(
                selected_stage_b_language=lang,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_post_reset_language, lang)
            self.assertTrue(res.stage_b_4lang_parity_verified)

    def test_29_g111_setup_items_survive_camera_settings_and_network_reset(self) -> None:
        for reset_action in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE273,
        ):
            res = verify_power_save_monitor_and_language_guard(
                reset_action=reset_action,
                pre_reset_power_save_start_time=POWER_SAVE_START_TIME_30_MIN_G111,
                pre_reset_auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G111,
                selected_stage_b_language=LANGUAGE_CODE_SCHINESE_G111,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(
                res.effective_post_reset_power_save_start_time,
                POWER_SAVE_START_TIME_30_MIN_G111,
            )
            self.assertEqual(
                res.effective_post_reset_auto_power_off_temp,
                AUTO_POWER_OFF_TEMP_HIGH_G111,
            )
            self.assertEqual(res.effective_post_reset_language, LANGUAGE_CODE_SCHINESE_G111)
            self.assertTrue(res.setup_items_survive_camera_settings_and_network_reset)

    def test_30_g111_initialize_clears_setup_items_to_factory_defaults(self) -> None:
        res = verify_power_save_monitor_and_language_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_power_save_start_time=POWER_SAVE_START_TIME_30_MIN_G111,
            pre_reset_auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G111,
            selected_stage_b_language=LANGUAGE_CODE_JAPANESE_G111,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(
            res.effective_post_reset_power_save_start_time,
            POWER_SAVE_START_TIME_FACTORY_DEFAULT_G111,
        )
        self.assertEqual(
            res.effective_post_reset_auto_power_off_temp,
            AUTO_POWER_OFF_TEMP_FACTORY_DEFAULT_G111,
        )
        self.assertEqual(
            res.effective_post_reset_language,
            LANGUAGE_OOB_PROMPT_DEFAULT_G111,
        )

    def test_31_g111_blocks_language_reset_or_count_mismatch(self) -> None:
        r1 = verify_power_save_monitor_and_language_guard(fx3_language_count=29)
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)

        r2 = verify_power_save_monitor_and_language_guard(fx6_language_count=34)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)

        r3 = verify_power_save_monitor_and_language_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            selected_stage_b_language=LANGUAGE_CODE_TCHINESE_G111,
            claimed_post_reset_language=LANGUAGE_CODE_EN_G111,
        )
        self.assertFalse(r3.valid)
        self.assertEqual(r3.status, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)

        r4 = verify_power_save_monitor_and_language_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            selected_stage_b_language=LANGUAGE_CODE_SCHINESE_G111,
            claimed_post_reset_language=LANGUAGE_CODE_SCHINESE_G111,
        )
        self.assertFalse(r4.valid)
        self.assertEqual(r4.status, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)

    def test_32_g111_blocks_reported_start_time_reset_violation(self) -> None:
        res = verify_power_save_monitor_and_language_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_power_save_start_time=POWER_SAVE_START_TIME_30_MIN_G111,
            claimed_post_reset_power_save_start_time=POWER_SAVE_START_TIME_5_MIN_G111,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G111_LANGUAGE_RESET_OR_BANK_VIOLATION)

    def test_33_g111_blocks_invalid_telemetry(self) -> None:
        bad_cases = [
            dict(body_model_name="ILCE-7M4"),
            dict(body_model_id=0x12345678),
            dict(firmware_version=""),
            dict(reset_action="UNKNOWN_RESET"),
            dict(pre_reset_power_save_start_time="15 Min"),
            dict(pre_reset_auto_power_off_temp="Ultra"),
            dict(active_deactivation_conditions=("unknown_cond",)),
            dict(selected_stage_b_language="french"),
            dict(bk_lang_property_id=True),
            dict(audit_body_model=""),
            dict(pre_reset_monitor_power_linkage="INVALID_MODE"),
        ]
        for kw in bad_cases:
            res = verify_power_save_monitor_and_language_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G111_TELEMETRY_INVALID, msg=kw)

    def test_34_g111_192_state_matrix_verified(self) -> None:
        mat = compute_power_save_monitor_and_language_matrix()
        self.assertEqual(mat["states_checked"], 192)
        self.assertEqual(mat["setup_reset_corruptions"], 0)
        self.assertTrue(mat["all_invariants_hold"])
        self.assertGreater(mat["headless_unsafe_modes_detected"], 0)
        self.assertGreater(mat["battery_bench_unsafe_times_detected"], 0)

    def test_35_g111_wrapper_functions_and_donor_failure_propagation(self) -> None:
        verdict, gres = evaluate_g111_power_save_monitor_and_language_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G111_GATE_ID)
        self.assertTrue(gres.valid)
        self.assertEqual(gres.status, STATUS_VERIFIED_G111)
        self.assertFalse(gres.persistent_emmc_writes_authorized)
        self.assertEqual(gres.raw_firmware_bytes_leaked, 0)

        bad_donor = dataclasses.replace(
            self.clean_audit,
            valid=False,
            status=STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY,
            errors=("corrupt donor",),
        )
        v_bad, r_bad = evaluate_g111_power_save_monitor_and_language_guard(
            donor_audit=bad_donor,
        )
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)

    def test_36_g111_menu_paths_and_resolver_function(self) -> None:
        self.assertEqual(
            POWER_SETTING_OPTION_MENU_PATH_G111,
            "MENU -> Setup -> [Power Setting Option]",
        )
        self.assertEqual(
            POWER_SAVE_START_TIME_MENU_PATH_G111,
            "MENU -> Setup -> [Power Setting Option] -> [Power Save Start Time]",
        )
        self.assertEqual(
            AUTO_POWER_OFF_TEMP_MENU_PATH_G111,
            "MENU -> Setup -> [Power Setting Option] -> [Auto Power OFF Temp.]",
        )
        self.assertEqual(LANGUAGE_MENU_PATH_G111, "MENU -> Setup -> [Area/Date] -> [Language]")
        st = resolve_fx3_power_save_monitor_and_language_state(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_language=LANGUAGE_CODE_TCHINESE_G111,
        )
        self.assertEqual(st["effective_post_reset_language"], LANGUAGE_CODE_TCHINESE_G111)

    # ------------------------------------------------------------------
    # 37..57: Gate G112 — Volume Settings, 4ch Monitoring & Delete confirm.
    # ------------------------------------------------------------------

    def test_37_g112_baseline_defaults_pass(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G112)
        self.assertEqual(res.effective_post_reset_volume_setting, 7)
        self.assertFalse(res.audio_signals_conflated)
        self.assertEqual(res.xlr_acoustic_feedback_events, 0)
        self.assertEqual(res.effective_post_reset_4ch_audio_monitoring, AUDIO_MON_CH1_CH2_G112)
        self.assertEqual(res.headphone_35mm_output_channels, 2)
        self.assertFalse(res.discrete_4ch_35mm_claimed)
        self.assertEqual(res.effective_post_reset_delete_confirm, DELETE_CONFIRM_CANCEL_FIRST_G112)
        self.assertEqual(res.effective_post_reset_delete_pressing_twice, DELETE_PRESSING_TWICE_OFF_G112)
        self.assertTrue(res.slot1_holds_recovery_vault)
        self.assertTrue(res.slot1_format_hard_locked)
        self.assertEqual(res.slot1_vault_delete_events, 0)
        self.assertEqual(res.matrix_states_checked, 240)

    def test_38_g112_constants_and_uxc_resid16_exact_values(self) -> None:
        self.assertEqual(VOLUME_SETTINGS_RESID16_G112, 0xE8C9)
        self.assertEqual(VOLUME_SETTINGS_MIN_G112, 0)
        self.assertEqual(VOLUME_SETTINGS_MAX_G112, 15)
        self.assertEqual(VOLUME_SETTINGS_FACTORY_DEFAULT_G112, 7)
        self.assertEqual(ALLOWED_VOLUME_SETTINGS_G112, tuple(range(16)))
        self.assertEqual(XLR_H1_INTERNAL_SPEAKER_SAFE_MAX_VOLUME_G112, 7)
        self.assertEqual(HEADPHONE_35MM_MAX_DISCRETE_CHANNELS_G112, 2)
        self.assertEqual(
            ALLOWED_4CH_AUDIO_MONITORING_ROUTES_G112,
            (
                AUDIO_MON_CH1_CH2_G112,
                AUDIO_MON_CH3_CH4_G112,
                AUDIO_MON_CH1_3_CH2_4_G112,
                AUDIO_MON_CH1_CH1_G112,
                AUDIO_MON_CH2_CH2_G112,
            ),
        )
        self.assertEqual(AUDIO_MON_ROUTE_METADATA_G112[AUDIO_MON_CH1_CH2_G112][1], 0x713B)
        self.assertEqual(AUDIO_MON_ROUTE_METADATA_G112[AUDIO_MON_CH3_CH4_G112][1], 0x6BF6)
        self.assertEqual(AUDIO_MON_ROUTE_METADATA_G112[AUDIO_MON_CH1_3_CH2_4_G112][1], 0x6C2E)
        self.assertEqual(AUDIO_MON_ROUTE_METADATA_G112[AUDIO_MON_CH1_CH1_G112][1], 0x6F9C)
        self.assertEqual(AUDIO_MON_ROUTE_METADATA_G112[AUDIO_MON_CH2_CH2_G112][1], 0x7A26)
        self.assertEqual(HDMI_4CH_AUDIO_OUTPUT_RESID16_G112, 0x6AA0)
        self.assertEqual(
            HDMI_4CH_AUDIO_OUTPUT_ROUTES_G112,
            (AUDIO_MON_CH1_CH2_G112, AUDIO_MON_CH3_CH4_G112),
        )
        self.assertEqual(
            DELETE_CONFIRM_RESID16_MAP_G112[DELETE_CONFIRM_CANCEL_FIRST_G112][:2],
            (0xE724, 0x6A5E),
        )
        self.assertEqual(
            DELETE_CONFIRM_RESID16_MAP_G112[DELETE_CONFIRM_DELETE_FIRST_G112][:2],
            (0xE725, 0x6E0A),
        )
        self.assertEqual(DELETE_PRESSING_TWICE_RESID16_G112, 0x74DB)

    def test_39_g112_all_16_volume_levels_pass_with_headphones(self) -> None:
        for v in ALLOWED_VOLUME_SETTINGS_G112:
            res = verify_volume_4chmon_delete_confirm_guard(
                pre_reset_volume_setting=v,
                xlr_h1_mic_active=True,
                headphones_connected=True,
                internal_speaker_active=False,
            )
            self.assertTrue(res.valid, msg=f"vol={v}: {res.errors}")
            self.assertEqual(res.effective_post_reset_volume_setting, v)

    def test_40_g112_blocks_out_of_range_and_bool_volume_settings(self) -> None:
        for bad_vol in (-1, 16, 100):
            res = verify_volume_4chmon_delete_confirm_guard(
                pre_reset_volume_setting=bad_vol,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION,
            )
        r_bool = verify_volume_4chmon_delete_confirm_guard(
            pre_reset_volume_setting=True,  # type: ignore[arg-type]
        )
        self.assertFalse(r_bool.valid)
        self.assertIn(STATUS_BLOCKED_G112_TELEMETRY_INVALID, r_bool.violation_codes)

    def test_41_g112_blocks_audio_signals_conflation(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard(
            audio_signals_conflated=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION,
        )

    def test_42_g112_blocks_xlr_h1_speaker_feedback_above_safe_max(self) -> None:
        for v in (8, 12, 15):
            res = verify_volume_4chmon_delete_confirm_guard(
                pre_reset_volume_setting=v,
                xlr_h1_mic_active=True,
                headphones_connected=False,
                internal_speaker_active=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION,
            )
            self.assertEqual(res.xlr_acoustic_feedback_events, 1)

    def test_43_g112_allows_xlr_h1_speaker_at_safe_volume_7(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard(
            pre_reset_volume_setting=7,
            xlr_h1_mic_active=True,
            headphones_connected=False,
            internal_speaker_active=True,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.xlr_acoustic_feedback_events, 0)

    def test_44_g112_all_5_audio_monitoring_routes_pass(self) -> None:
        for route in ALLOWED_4CH_AUDIO_MONITORING_ROUTES_G112:
            res = verify_volume_4chmon_delete_confirm_guard(
                pre_reset_4ch_audio_monitoring=route,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_post_reset_4ch_audio_monitoring, route)

    def test_45_g112_blocks_discrete_4ch_35mm_or_invalid_monitor_route(self) -> None:
        r1 = verify_volume_4chmon_delete_confirm_guard(
            claimed_discrete_4ch_35mm_output=True,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)

        r2 = verify_volume_4chmon_delete_confirm_guard(
            headphone_35mm_output_channels=4,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)

        r3 = verify_volume_4chmon_delete_confirm_guard(
            pre_reset_4ch_audio_monitoring="CH1/CH2/CH3/CH4",
        )
        self.assertFalse(r3.valid)
        self.assertEqual(r3.status, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)

    def test_46_g112_blocks_invalid_hdmi_4ch_output_pair(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard(
            hdmi_4ch_audio_output=AUDIO_MON_CH1_3_CH2_4_G112,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)

    def test_47_g112_allows_both_delete_confirm_modes_and_delete_pressing_twice(self) -> None:
        for dc in ALLOWED_DELETE_CONFIRM_MODES_G112:
            for dpt in ALLOWED_DELETE_PRESSING_TWICE_MODES_G112:
                res = verify_volume_4chmon_delete_confirm_guard(
                    pre_reset_delete_confirm=dc,
                    pre_reset_delete_pressing_twice=dpt,
                )
                self.assertTrue(res.valid, msg=res.errors)
                self.assertEqual(res.effective_post_reset_delete_confirm, dc)
                self.assertEqual(res.effective_post_reset_delete_pressing_twice, dpt)

    def test_48_g112_setup_and_playback_survive_camera_settings_and_network_reset(self) -> None:
        for reset_action in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE273,
        ):
            res = verify_volume_4chmon_delete_confirm_guard(
                reset_action=reset_action,
                pre_reset_volume_setting=11,
                headphones_connected=True,
                pre_reset_4ch_audio_monitoring=AUDIO_MON_CH1_3_CH2_4_G112,
                pre_reset_delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G112,
                pre_reset_delete_pressing_twice=DELETE_PRESSING_TWICE_ON_G112,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_post_reset_volume_setting, 11)
            self.assertEqual(
                res.effective_post_reset_4ch_audio_monitoring,
                AUDIO_MON_CH1_3_CH2_4_G112,
            )
            self.assertEqual(
                res.effective_post_reset_delete_confirm,
                DELETE_CONFIRM_DELETE_FIRST_G112,
            )
            self.assertEqual(
                res.effective_post_reset_delete_pressing_twice,
                DELETE_PRESSING_TWICE_ON_G112,
            )
            self.assertTrue(res.setup_playback_reset_contract_verified)

    def test_49_g112_initialize_resets_setup_and_playback_to_factory_defaults(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_volume_setting=11,
            headphones_connected=True,
            pre_reset_4ch_audio_monitoring=AUDIO_MON_CH1_3_CH2_4_G112,
            pre_reset_delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G112,
            pre_reset_delete_pressing_twice=DELETE_PRESSING_TWICE_ON_G112,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(
            res.effective_post_reset_volume_setting,
            VOLUME_SETTINGS_FACTORY_DEFAULT_G112,
        )
        self.assertEqual(
            res.effective_post_reset_4ch_audio_monitoring,
            AUDIO_MON_FACTORY_DEFAULT_G112,
        )
        self.assertEqual(
            res.effective_post_reset_delete_confirm,
            DELETE_CONFIRM_FACTORY_DEFAULT_G112,
        )
        self.assertEqual(
            res.effective_post_reset_delete_pressing_twice,
            DELETE_PRESSING_TWICE_FACTORY_DEFAULT_G112,
        )

    def test_50_g112_blocks_all_delete_and_format_ops_on_slot1_recovery_vault(self) -> None:
        destructive_ops = (
            MEDIA_OP_DELETE_SINGLE_G112,
            MEDIA_OP_DELETE_MULTIPLE_G112,
            MEDIA_OP_DELETE_FOLDER_G112,
            MEDIA_OP_DELETE_DATE_G112,
            MEDIA_OP_DELETE_PRESSING_TWICE_G112,
            MEDIA_OP_FORMAT_QUICK_G112,
            MEDIA_OP_FORMAT_FULL_G112,
        )
        for op in destructive_ops:
            res = verify_volume_4chmon_delete_confirm_guard(
                requested_media_op=op,
                target_slot=TARGET_SLOT_1_G112,
                slot1_holds_recovery_vault=True,
            )
            self.assertFalse(res.valid, msg=op)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION,
                msg=op,
            )
            self.assertEqual(res.slot1_vault_delete_events, 1, msg=op)

    def test_51_g112_blocks_claimed_slot1_vault_delete_events(self) -> None:
        res = verify_volume_4chmon_delete_confirm_guard(
            claimed_slot1_vault_delete_events=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION,
        )

    def test_52_g112_allows_slot2_media_ops_when_slot1_vault_untouched(self) -> None:
        for op in (MEDIA_OP_DELETE_SINGLE_G112, MEDIA_OP_FORMAT_QUICK_G112):
            res = verify_volume_4chmon_delete_confirm_guard(
                requested_media_op=op,
                target_slot=TARGET_SLOT_2_G112,
                slot1_holds_recovery_vault=True,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.slot1_vault_delete_events, 0)

    def test_53_g112_blocks_reported_reset_drift_violations(self) -> None:
        r1 = verify_volume_4chmon_delete_confirm_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_volume_setting=10,
            headphones_connected=True,
            claimed_post_reset_volume_setting=7,
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status,
            STATUS_BLOCKED_G112_VOLUME_RANGE_OR_XLR_FEEDBACK_VIOLATION,
        )

        r2 = verify_volume_4chmon_delete_confirm_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_4ch_audio_monitoring=AUDIO_MON_CH3_CH4_G112,
            claimed_post_reset_4ch_audio_monitoring=AUDIO_MON_CH1_CH2_G112,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G112_4CH_MONITORING_ROUTE_VIOLATION)

        r3 = verify_volume_4chmon_delete_confirm_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G112,
            claimed_post_reset_delete_confirm=DELETE_CONFIRM_CANCEL_FIRST_G112,
        )
        self.assertFalse(r3.valid)
        self.assertEqual(
            r3.status,
            STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION,
        )

    def test_54_g112_blocks_invalid_telemetry(self) -> None:
        bad_cases = [
            dict(body_model_name="ILME-FX6"),
            dict(body_model_id=0x99999999),
            dict(firmware_version=""),
            dict(reset_action="BAD_RESET"),
            dict(pre_reset_delete_confirm="Always Confirm"),
            dict(pre_reset_delete_pressing_twice="Auto"),
            dict(requested_media_op="DROP_TABLE"),
            dict(target_slot="SLOT_99"),
        ]
        for kw in bad_cases:
            res = verify_volume_4chmon_delete_confirm_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G112_TELEMETRY_INVALID, msg=kw)

    def test_55_g112_240_state_matrix_verified(self) -> None:
        mat = compute_volume_4chmon_and_delete_confirm_matrix()
        self.assertEqual(mat["states_checked"], 240)
        self.assertEqual(mat["reset_corruptions"], 0)
        self.assertEqual(mat["slot1_vault_mutations"], 0)
        self.assertEqual(mat["discrete_4ch_35mm_breaches"], 0)
        self.assertTrue(mat["all_invariants_hold"])

    def test_56_g112_wrapper_functions_and_donor_failure_propagation(self) -> None:
        verdict, gres = evaluate_g112_volume_4chmon_delete_confirm_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G112_GATE_ID)
        self.assertTrue(gres.valid)
        self.assertEqual(gres.status, STATUS_VERIFIED_G112)
        self.assertFalse(gres.persistent_emmc_writes_authorized)
        self.assertEqual(gres.raw_firmware_bytes_leaked, 0)

        bad_donor = dataclasses.replace(
            self.clean_audit,
            valid=False,
            status=STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY,
            errors=("corrupt donor",),
        )
        v_bad, r_bad = evaluate_g112_volume_4chmon_delete_confirm_guard(
            donor_audit=bad_donor,
        )
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_PHASE273_DONOR_INTEGRITY)

    def test_57_g112_menu_paths_and_slot_metadata(self) -> None:
        self.assertEqual(
            VOLUME_SETTINGS_MENU_PATH_G112,
            "MENU -> Setup -> [Sound Option] -> [Volume Settings]",
        )
        self.assertEqual(
            AUDIO_MONITORING_4CH_MENU_PATH_G112,
            "MENU -> Setup -> [Sound Option] -> [4ch Audio Monitoring]",
        )
        self.assertEqual(
            HDMI_4CH_AUDIO_OUTPUT_MENU_PATH_G112,
            "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [4ch Audio Output]",
        )
        self.assertEqual(
            DELETE_CONFIRM_MENU_PATH_G112,
            "MENU -> Playback -> [Delete] -> [Delete confirm.]",
        )
        self.assertEqual(
            DELETE_PRESSING_TWICE_MENU_PATH_G112,
            "MENU -> Playback -> [Delete] -> [Delete pressing twice]",
        )
        self.assertEqual(len(ALLOWED_MEDIA_OPS_G112), 8)
        self.assertEqual(len(ALLOWED_TARGET_SLOTS_G112), 3)
        st = resolve_fx3_volume_4chmon_and_delete_confirm_state(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            pre_reset_volume_setting=12,
        )
        self.assertEqual(st["effective_post_reset_volume_setting"], 12)

    # ------------------------------------------------------------------
    # 58..66: Unified 112-Gate Preflight Engine
    # ------------------------------------------------------------------

    def test_58_unified_112_gates_offline_109_of_112(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_110_override=self.clean_offline_110,
        )
        self.assertEqual(rep.summary["total_gates"], 112)
        self.assertEqual(rep.summary["verified_gates"], 109)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_109_gates_verified)
        self.assertFalse(rep.all_112_gates_verified)
        self.assertTrue(rep.g111_to_g112_all_passed)
        self.assertEqual(rep.status, "VERIFIED_109_OF_112_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 112)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_59_unified_112_gates_dry_run_simulated_112_of_112(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
        )
        self.assertEqual(rep.summary["total_gates"], 112)
        self.assertEqual(rep.summary["verified_gates"], 112)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_109_gates_verified)
        self.assertTrue(rep.all_112_gates_verified)
        self.assertTrue(rep.g111_to_g112_all_passed)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.status, "VERIFIED_ALL_112_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_60_unified_112_gates_real_unmocked_delegation(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep.all_112_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 112)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_61_unified_112_gates_g111_failure_blocks_report(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
            power_save_monitor_language_kwargs={
                "claimed_fx3_ui_exposes_power_save_by_monitor": True,
            },
        )
        self.assertFalse(rep.g111_to_g112_all_passed)
        self.assertFalse(rep.all_112_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G111_POWER_SAVE_MONITOR_UI_SPOOF_VIOLATION,
        )
        self.assertEqual(rep.summary["verified_gates"], 111)

    def test_62_unified_112_gates_g112_failure_blocks_report(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
            volume_4chmon_delete_confirm_kwargs={
                "requested_media_op": MEDIA_OP_FORMAT_QUICK_G112,
                "target_slot": TARGET_SLOT_1_G112,
            },
        )
        self.assertFalse(rep.g111_to_g112_all_passed)
        self.assertFalse(rep.all_112_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G112_SLOT1_VAULT_DELETE_OR_FORMAT_VIOLATION,
        )
        self.assertEqual(rep.summary["verified_gates"], 111)

    def test_63_unified_112_gates_blocks_persistent_write_escalation(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_110_override=self.clean_dryrun_110,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.all_112_gates_verified)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_64_unified_112_gates_report_json_serializable(self) -> None:
        rep = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
        )
        raw = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(raw)
        self.assertEqual(decoded["summary"]["verified_gates"], 112)
        self.assertEqual(decoded["g111_result"]["status"], STATUS_VERIFIED_G111)
        self.assertEqual(decoded["g112_result"]["status"], STATUS_VERIFIED_G112)

    def test_65_run_112_gate_preflight_and_evaluate_112_master_aliases(self) -> None:
        rep1 = run_112_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_110_override=self.clean_offline_110,
        )
        rep2 = evaluate_112_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
        )
        self.assertEqual(rep1.summary["verified_gates"], 109)
        self.assertEqual(rep2.summary["verified_gates"], 112)

    def test_66_reset_actions_tuple_exact(self) -> None:
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE273,
            (
                RESET_ACTION_NONE,
                RESET_ACTION_CAMERA_SETTINGS_RESET,
                RESET_ACTION_RESET_NETWORK_SET_PHASE273,
                RESET_ACTION_INITIALIZE,
            ),
        )
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE273, "7.02")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE273, "6.01")

    # ------------------------------------------------------------------
    # 67..76: CLI Entrypoints, Standalone Main, Subprocess Portability & Upstream
    # ------------------------------------------------------------------

    def test_67_cli_verify_power_save_monitor_language_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-power-save-monitor-language-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G111_", buf.getvalue())
        self.assertIn("fx3_mon_ui=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g111-power-save-monitor-language", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G111)

    def test_68_cli_verify_volume_4chmon_delete_confirm_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-volume-4chmon-delete-confirm-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G112_", buf.getvalue())
        self.assertIn("slot1_fmt_lock=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g112-volume-4chmon-delete-confirm", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G112)

    def test_69_cli_verify_112_gates_offline_text_and_json(self) -> None:
        offline_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_110_override=self.clean_offline_110,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_112gate_preflight",
            return_value=offline_112,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-112-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=109/112", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-112-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 109)
            self.assertTrue(parsed["offline_109_gates_verified"])

    def test_70_cli_verify_112_gates_dry_run_text_and_json(self) -> None:
        dryrun_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_112gate_preflight",
            return_value=dryrun_112,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-112-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=112/112", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-112-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_112_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 112)

    def test_71_standalone_module_main_offline_and_dry_run(self) -> None:
        offline_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_110_override=self.clean_offline_110,
        )
        dryrun_112 = evaluate_112gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_110_override=self.clean_dryrun_110,
        )
        with mock.patch(
            "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard.evaluate_112gate_preflight",
            return_value=offline_112,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=109/112", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_power_save_monitor_language_volume_delete_and_112gate_guard.evaluate_112gate_preflight",
            return_value=dryrun_112,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(["--force-clean-room", "--simulate-bench-dry-run", "--json"])
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_112_gates_verified"])

    def test_72_subprocess_cli_verify_g111_g112_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-power-save-monitor-language-guard", STATUS_VERIFIED_G111),
            ("verify-volume-4chmon-delete-confirm-guard", STATUS_VERIFIED_G112),
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", cmd, "--force-clean-room", "--json"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["status"], expected_status)

    def test_73_subprocess_cli_verify_112_gates_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-112-gates",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_112_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 112)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_74_fx3_clean_room_test_and_force_clean_room_env_in_master_112(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE273, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_112gate_preflight(
                    master_110_override=self.clean_offline_110,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_75_argparse_help_has_no_unescaped_percent_for_python314(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-power-save-monitor-language-guard",
            "verify-volume-4chmon-delete-confirm-guard",
            "verify-112-gates",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", subcmd, "--help"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_76_upstream_verify_110_gates_remains_100pct_intact(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_110gate_preflight",
            return_value=self.clean_offline_110,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-110-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=107/110", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
