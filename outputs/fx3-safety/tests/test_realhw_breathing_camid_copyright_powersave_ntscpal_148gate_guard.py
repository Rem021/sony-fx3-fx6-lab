"""Phase 331 (Task H400 — 400th Task Milestone!, Wave-64, 148/148 Safety Gates):
Four-Mode Unit Tests (96 tests) for
`fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard`:

- Gate `G147` (`REALHW_BREATHING_COMP_120P_CATALYST_AND_CAMID_REEL_SDHC_VAULT_GUARD`):
  - `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`
    (`Off` default / `On`, **Resettable** via `[Camera Settings Reset]` unlike
    `Initialize`-only `Shading`/`Chromatic Aberration`/`Distortion Comp.`): Wave-41
    errata enforcing unavailability at **regular Movie `119.88p / 100p` (`120p`)**
    AND `S&Q` `100/120/200/240fps` (while `< 100fps` `S&Q` stays available on FX3),
    Still-mode lockout, incompatible lenses / `SEL100F28GM` `0.57-1.0m` macro ring /
    `SEL14TC` / `SEL20TC` teleconverters (`EOPNOTSUPP=95`), external `4264x2408`
    16-bit HDMI RAW bypass, paid **`Catalyst Prepare` / `Catalyst Prepare Plugin`** +
    `[Distortion Comp.] = [Auto]` vs free `Catalyst Browse` (`EOPNOTSUPP=95`), and
    `ILME-FX6` (`Technical > Lens > Breathing Compensation` locked `Off` on
    `Distortion=Off`, ALL `S&Q=On`, or any `RAW` codec).
  - `Shooting -> [File] -> [File Settings]` (`Initialize`-only): `[File Number]`
    (`Series`/`Reset` + `[Series Counter Reset]` `max + 1`), `[File Name Format]`
    (`Standard`/`Cam ID + Reel#`/`Title`/`Date + Title`/`Title + Date`; **`SDHC`
    `FAT32 <= 32 GB`** locking `[Standard]`, `4 GB` XAVC S split, blocking
    `Simult. Recording` with `exFAT`), `[Cam ID + Reel#]` (`A..Z` ID change resets
    `Reel#` `001..999` while `File Number = Reset` preserves `Reel#`, `C999 -> D001`
    rollover without mutating menu setting, `6`-digit `YYMMDD` vs `8`-digit
    `YYYYMMDD`), **`37`-char `[Title Name Settings]`** (default `"C"`), fixed
    `PRIVATE/M4ROOT/CLIP` vs FX6 `4..46`-char `nnn_` + `/XDROOT/Clip/*.MXF`, and
    `Slot-1` Tier-0 Vault `EROFS=30` firewall (`slot1_data_sector_writes == 0`).
- Gate `G148` (`REALHW_COPYRIGHT_46CH_SERIAL_ERRATA_AND_POWERSAVE_NTSCPAL_VAULT_GUARD`):
  - **Round-57 Reset Errata**: `Shooting -> [File] -> [Copyright Info]` (4 items,
    `<= 46` printable ASCII chars) AND active Still+Movie `[Write Serial Number]`
    (`BKID_APP_setting_write_serial_number_still_movie`) are **ALL `Initialize`-only**
    (`Not available` under `[Camera Settings Reset]`); `[Copyright Info]` excluded
    from `CAMSET*.DAT` (blocking PII leak) while `[Write Serial Number]` boolean
    toggle is allowed, vs `ILME-FX6` (no EXIF copyright, lens serial `0..5` + 3-digit
    body serial `nnn_`).
  - `Setup -> [Power Setting Option]` exact `2` active `Initialize`-only items
    (`[Power Save Start Time]` `Off/30/5[def]/2/1 Min/10 Sec`, dormant
    `20SEC`/`NO_LIMIT`/`30 sec`/`60 min`/`240 min` -> `EOPNOTSUPP=95`, exact `9`
    official auto-bypass conditions, `[Auto Power OFF Temp.]` `Standard`/`High`) vs
    dormant `[Power Save by Monitor]` (`EOPNOTSUPP=95`); AND `[NTSC/PAL Selector]`
    (`Initialize`-only, mandatory reboot, `Running on NTSC./PAL.`, cross-system
    playback block, **HARD `EROFS=30` `Slot-1` Format/SD-Erase/TRIM Firewall**).
- Unified `148`-Gate Master Preflight (`evaluate_148gate_preflight` / `verify-148-gates`):
  `145/148` offline, `148/148` `--simulate-bench-dry-run`, backward-compatible across
  `verify-58-gates` .. `verify-146-gates`, auto-discovered by `milestone324` & `311`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    evaluate_146gate_preflight,
)
from fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    evaluate_144gate_preflight,
)
from fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard import (
    ALLOWED_AUTO_POWER_OFF_TEMP_MODES_G148,
    ALLOWED_BREATHING_COMP_MODES_G147,
    ALLOWED_FILE_NAME_FORMATS_G147,
    ALLOWED_FILE_NUMBER_MODES_G147,
    ALLOWED_POWER_SAVE_START_TIMES_G148,
    ALLOWED_VIDEO_SYSTEMS_G148,
    AUTO_POWER_OFF_TEMP_DEFAULT_G148,
    AUTO_POWER_OFF_TEMP_F_RESID16_G148,
    AUTO_POWER_OFF_TEMP_HIGH_G148,
    AUTO_POWER_OFF_TEMP_STANDARD_G148,
    BREATHING_COMP_DEFAULT_G147,
    BREATHING_COMP_F_RESID16_G147,
    BREATHING_COMP_MIN_FW_G147,
    BREATHING_COMP_OFF_G147,
    BREATHING_COMP_ON_G147,
    BREATHING_COMP_RESETTABLE_BY_CAMSET_RESET_G147,
    CAMERA_POS_C_G147,
    CAMERA_POS_L_G147,
    CARD_TYPE_CFEXPRESS_TYPE_A_G147,
    CARD_TYPE_SDHC_G147,
    CARD_TYPE_SDXC_G147,
    CATALYST_BROWSE_FREE_TOOL_G147,
    CATALYST_PREPARE_PAID_TOOLS_G147,
    COPYRIGHT_INFO_EXCLUDED_FROM_CAMSET_DAT_G148,
    COPYRIGHT_INFO_F_RESID16_G148,
    COPYRIGHT_INFO_RESETTABLE_BY_CAMSET_RESET_G148,
    COPYRIGHT_MAX_CHARS_G148,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE331,
    DONOR_CHECK_MAX_SECONDS_PHASE331,
    DORMANT_POWER_SAVE_BY_MONITOR_BKID_G148,
    DORMANT_POWER_SAVE_VALUES_G148,
    EINVAL_ERRNO_PHASE331,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE331,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE331,
    EROFS_ERRNO_PHASE331,
    EXACT_2_POWER_SETTING_OPTION_ITEMS_G148,
    EXACT_4_COPYRIGHT_INFO_ITEMS_G148,
    EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148,
    FILE_NAME_FORMAT_CAM_ID_REEL_G147,
    FILE_NAME_FORMAT_DATE_TITLE_G147,
    FILE_NAME_FORMAT_STANDARD_G147,
    FILE_NAME_FORMAT_TITLE_DATE_G147,
    FILE_NAME_FORMAT_TITLE_G147,
    FILE_NUMBER_RESET_G147,
    FILE_NUMBER_SERIES_G147,
    FILE_SETTINGS_F_RESID16_G147,
    FILE_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G147,
    FX3_DEFAULT_FW_VERSION_PHASE331,
    FX3_HELP_GUIDE_CODE_PHASE331,
    FX3_MODEL_ID_PHASE331,
    FX3_MODEL_NAME_PHASE331,
    FX3_MOVIE_CLIP_FOLDER_PATH_G147,
    FX6_CFEXPRESS_CLIP_FOLDER_PATH_G147,
    FX6_MODEL_NAME_PHASE331,
    G147,
    G147_GATE_CODE,
    G148,
    G148_GATE_CODE,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LENS_BREATHING_NA_G147,
    LENS_BREATHING_NOT_SUPPORT_G147,
    LENS_BREATHING_SUPPORT_G147,
    LENS_COMP_INITIALIZE_ONLY_ITEMS_G147,
    MACRO_RING_RESTRICTED_LENS_G147,
    MEDIA_SLOT_1_PHASE331,
    MEDIA_SLOT_2_PHASE331,
    MEDIA_SLOT_NONE_PHASE331,
    Master148GateReport,
    NTSC_PAL_RESETTABLE_BY_CAMSET_RESET_G148,
    NTSC_PAL_SELECTOR_F_RESID16_G148,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE331,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE331,
    PINNED_PHASE331_DONOR_SPECS,
    POWER_SAVE_10_SEC_G148,
    POWER_SAVE_5_MIN_G148,
    POWER_SAVE_OFF_G148,
    POWER_SAVE_START_TIME_F_RESID16_G148,
    POWER_SETTING_OPTION_RESETTABLE_BY_CAMSET_RESET_G148,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_148GATE_PREFLIGHT_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
    RESET_ACTION_INITIALIZE_PHASE331,
    RESET_ACTION_NONE_PHASE331,
    SHOOT_MODE_MOVIE_PHASE331,
    SHOOT_MODE_SQ_PHASE331,
    SHOOT_MODE_STILL_PHASE331,
    SPI_NOR_WRITE_AUTHORIZED,
    STARTUP_BANNER_NONE_G148,
    STARTUP_BANNER_NTSC_G148,
    STARTUP_BANNER_PAL_G148,
    STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP,
    STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION,
    STATUS_BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS,
    STATUS_BLOCKED_G147_TELEMETRY_INVALID,
    STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION,
    STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP,
    STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
    STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS,
    STATUS_BLOCKED_G148_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY,
    STATUS_VERIFIED_G147,
    STATUS_VERIFIED_G148,
    TELECONVERTER_MODELS_G147,
    TITLE_NAME_DEFAULT_G147,
    TITLE_NAME_MAX_CHARS_G147,
    USB_PACKETS_TRANSMITTED,
    VIDEO_SYSTEM_NTSC_G148,
    VIDEO_SYSTEM_PAL_G148,
    WRITE_SERIAL_NUMBER_EXCLUDED_FROM_CAMSET_DAT_G148,
    WRITE_SERIAL_NUMBER_RESETTABLE_BY_CAMSET_RESET_G148,
    WRITE_SERIAL_NUMBER_SYMBOL_STILL_MOVIE_G148,
    audit_phase331_donor_contracts,
    compute_breathing_camid_reel_matrix,
    compute_copyright_powersave_ntscpal_matrix,
    evaluate_148_master_safety_gates,
    evaluate_148gate_preflight,
    evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard,
    evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard,
    main as module_main,
    resolve_fx3_breathing_and_file_settings_state,
    resolve_fx3_copyright_powersave_ntscpal_state,
    run_148_gate_preflight,
    verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard,
    verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard_with_audit,
    verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard,
    verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard_with_audit,
)
from fx3_safety.thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths


def _donors_available_here() -> bool:
    if os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    if os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE331, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    wr = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    if wr is None:
        return False
    return all((wr / spec[1]).is_file() for spec in PINNED_PHASE331_DONOR_SPECS.values())


class TestPhase331Milestone148Gates(unittest.TestCase):
    # =========================================================================
    # Section A: Exports, Redlines & 4-Mode / Donorless CI Audit (01..12)
    # =========================================================================

    def test_01_public_exports_present_in_package_and_all(self) -> None:
        required = (
            "G147",
            "G148",
            "Master148GateReport",
            "evaluate_148gate_preflight",
            "evaluate_148_master_safety_gates",
            "run_148_gate_preflight",
            "evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard",
            "evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard",
            "verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard",
            "verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard",
            "audit_phase331_donor_contracts",
            "realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard",
        )
        for name in required:
            self.assertTrue(hasattr(fx3_safety, name), msg=f"missing fx3_safety.{name}")
            self.assertIn(name, fx3_safety.__all__, msg=f"missing {name} in __all__")

    def test_02_immutable_safety_redlines_hard_locked_false_and_zero(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_donor_audit_clean_room_forced_kwarg(self) -> None:
        audit = audit_phase331_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.zero_forbidden_myths_verified)

    def test_04_donor_audit_clean_room_via_env_vars(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE331):
            with mock.patch.dict(os.environ, {env_key: "1"}, clear=False):
                audit = audit_phase331_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_local_or_clean_room_budget_and_digests(self) -> None:
        audit = audit_phase331_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid, msg=f"errors={audit.errors}")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE331)
        if _donors_available_here():
            self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE331_DONOR_SPECS))
            self.assertEqual(audit.files_inspected, 12)
            self.assertTrue(audit.within_budget_200ms)
            self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE331)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")
            self.assertEqual(
                audit.file_digests["fx3_appfw_so"],
                PINNED_FX3_APPFW_SLICES_SHA256_PHASE331,
            )
            self.assertEqual(
                audit.file_digests["fx6_appfw_so"],
                PINNED_FX6_APPFW_SLICES_SHA256_PHASE331,
            )

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        audit = audit_phase331_donor_contracts(
            work_root=Path("/nonexistent/phase331/donor/root"),
            force_clean_room=False,
        )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_simulated_donorless_ubuntu_ci_iter_work_roots_empty_phase331(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE331, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                audit = audit_phase331_donor_contracts(force_clean_room=False)
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

                v147, r147 = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                    force_clean_room=False
                )
                self.assertTrue(v147.passed)
                self.assertTrue(r147.valid)
                self.assertEqual(r147.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                v148, r148 = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                    force_clean_room=False
                )
                self.assertTrue(v148.passed)
                self.assertTrue(r148.valid)
                self.assertEqual(r148.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                rep = evaluate_148gate_preflight(force_clean_room=False)
                self.assertTrue(rep.offline_145_gates_verified)
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_blocks_on_size_mismatch_or_bad_token_via_override(self) -> None:
        if not _donors_available_here():
            self.skipTest("local donor artifacts absent in clean-room environment")
        bad_specs = dict(PINNED_PHASE331_DONOR_SPECS)
        family, rel, _size, sha, toks, desc = bad_specs["fx3_lib_saveload_settings_so"]
        bad_specs["fx3_lib_saveload_settings_so"] = (
            family,
            rel,
            999999999,
            sha,
            toks + (b"__NONEXISTENT_PHASE331_TOKEN__",),
            desc,
        )
        audit = audit_phase331_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_09_donor_audit_blocks_on_bad_pinned_slice_sha256(self) -> None:
        if not _donors_available_here():
            self.skipTest("local donor artifacts absent in clean-room environment")
        bad_specs = dict(PINNED_PHASE331_DONOR_SPECS)
        family, rel, size, _sha, toks, desc = bad_specs["fx3_lib_saveload_settings_so"]
        bad_specs["fx3_lib_saveload_settings_so"] = (
            family,
            rel,
            size,
            "0" * 64,
            toks,
            desc,
        )
        audit = audit_phase331_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY)

    def test_10_donor_audit_inspects_lib_saveload_and_four_lang_packs(self) -> None:
        if not _donors_available_here():
            self.skipTest("local donor artifacts absent in clean-room environment")
        audit = audit_phase331_donor_contracts(repo_root=DEFAULT_REPO_ROOT, force_clean_room=False)
        for key in (
            "fx3_lib_saveload_settings_so",
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        ):
            self.assertIn(key, audit.file_digests)
            self.assertEqual(len(audit.file_digests[key]), 64)

    def test_11_strict_o_rdonly_donor_helpers_never_open_write_flags(self) -> None:
        mod_path = Path(fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.__file__)
        src = mod_path.read_text(encoding="utf-8")
        self.assertIn("os.open(path, os.O_RDONLY)", src)
        self.assertIn("os.pread", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn('open(path, "w', src)

    def test_12_g147_and_g148_identity_constants_pinned(self) -> None:
        self.assertEqual(G147, "G147")
        self.assertEqual(G148, "G148")
        self.assertEqual(BREATHING_COMP_F_RESID16_G147, 0x73EA)
        self.assertEqual(FILE_SETTINGS_F_RESID16_G147, 0x61BC)
        self.assertEqual(COPYRIGHT_INFO_F_RESID16_G148, 0x6D53)
        self.assertEqual(POWER_SAVE_START_TIME_F_RESID16_G148, 0x69B0)
        self.assertEqual(AUTO_POWER_OFF_TEMP_F_RESID16_G148, 0x70F1)
        self.assertEqual(NTSC_PAL_SELECTOR_F_RESID16_G148, 0x6B6F)

    # =========================================================================
    # Section B: Gate G147 — [Breathing Comp.] 120p/S&Q/Catalyst & [File Settings] (13..46)
    # =========================================================================

    def test_13_g147_defaults_pass_direct_and_audit_wrapper(self) -> None:
        res = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G147)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.effective_breathing_comp, BREATHING_COMP_DEFAULT_G147)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        v, wrapped = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            force_clean_room=True
        )
        self.assertTrue(v.passed)
        self.assertTrue(wrapped.valid)
        self.assertEqual(wrapped.gate_id, G147)
        self.assertEqual(wrapped.gate_code, G147_GATE_CODE)

    def test_14_g147_breathing_comp_resettable_unlike_initialize_only_shading_ca_distortion(self) -> None:
        self.assertTrue(BREATHING_COMP_RESETTABLE_BY_CAMSET_RESET_G147)
        self.assertEqual(
            LENS_COMP_INITIALIZE_ONLY_ITEMS_G147,
            ("Shading Comp.", "Chromatic Aberration Comp.", "Distortion Comp."),
        )
        st = resolve_fx3_breathing_and_file_settings_state(
            breathing_comp=BREATHING_COMP_ON_G147,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
        )
        self.assertEqual(st["effective_breathing_comp"], BREATHING_COMP_DEFAULT_G147)
        self.assertEqual(st["effective_breathing_comp"], BREATHING_COMP_OFF_G147)

    def test_15_g147_claiming_camset_reset_retains_breathing_comp_blocked_einval(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            breathing_comp=BREATHING_COMP_ON_G147,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
            claimed_camset_reset_preserves_breathing=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION)

    def test_16_g147_wave41_errata_regular_movie_119_88p_and_100p_blocks_breathing_comp(self) -> None:
        for fps in (100.0, 119.88, 120.0):
            st = resolve_fx3_breathing_and_file_settings_state(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE331,
                fps=fps,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertEqual(st["effective_breathing_comp"], BREATHING_COMP_OFF_G147)
            self.assertFalse(st["breathing_comp_available"])

            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE331,
                fps=fps,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertFalse(bad.valid, msg=f"fps={fps}")
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION)

    def test_17_g147_wave41_errata_sq_100_120_200_240fps_blocks_breathing_comp(self) -> None:
        for sq_fps in (100, 120, 200, 240):
            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE331,
                fps=sq_fps,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertFalse(bad.valid, msg=f"sq_fps={sq_fps}")
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION)

    def test_18_g147_fx3_sq_below_100fps_allows_breathing_comp(self) -> None:
        for sq_fps in (1, 2, 4, 8, 15, 30, 60):
            ok = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE331,
                fps=sq_fps,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertTrue(ok.valid, msg=f"sq_fps={sq_fps} errors={ok.errors}")
            self.assertEqual(ok.effective_breathing_comp, BREATHING_COMP_ON_G147)

    def test_19_g147_still_mode_locks_breathing_comp_off(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE331,
            breathing_comp=BREATHING_COMP_ON_G147,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION)

    def test_20_g147_incompatible_lens_not_support_or_na_rejected_eopnotsupp_95(self) -> None:
        for state in (LENS_BREATHING_NOT_SUPPORT_G147, LENS_BREATHING_NA_G147):
            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                lens_breathing_support=state,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)

    def test_21_g147_sel100f28gm_macro_ring_0_57_1_0m_rejected_eopnotsupp_95(self) -> None:
        ok_normal = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            lens_model=MACRO_RING_RESTRICTED_LENS_G147,
            macro_ring_057_10m_active=False,
            breathing_comp=BREATHING_COMP_ON_G147,
        )
        self.assertTrue(ok_normal.valid)
        bad_macro = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            lens_model=MACRO_RING_RESTRICTED_LENS_G147,
            macro_ring_057_10m_active=True,
            breathing_comp=BREATHING_COMP_ON_G147,
        )
        self.assertFalse(bad_macro.valid)
        self.assertEqual(bad_macro.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(bad_macro.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)

    def test_22_g147_sel14tc_and_sel20tc_teleconverters_rejected_eopnotsupp_95(self) -> None:
        for tc in TELECONVERTER_MODELS_G147:
            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                teleconverter_model=tc,
                breathing_comp=BREATHING_COMP_ON_G147,
            )
            self.assertFalse(bad.valid, msg=tc)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)

    def test_23_g147_external_hdmi_raw_4264x2408_16bit_bypasses_breathing_comp(self) -> None:
        ok = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            breathing_comp=BREATHING_COMP_ON_G147,
            raw_output="On",
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.breathing_bypassed_on_hdmi_raw)

        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            breathing_comp=BREATHING_COMP_ON_G147,
            raw_output="On",
            claimed_breathing_applied_to_hdmi_raw=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_BREATHING_120P_SQ_RAW_OR_RESET_VIOLATION)

    def test_24_g147_catalyst_prepare_and_plugin_with_distortion_auto_allowed(self) -> None:
        for tool in CATALYST_PREPARE_PAID_TOOLS_G147:
            ok = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                catalyst_tool=tool,
                catalyst_breathing_comp_requested=True,
                distortion_comp="Auto",
            )
            self.assertTrue(ok.valid, msg=f"{tool}: {ok.errors}")

    def test_25_g147_free_catalyst_browse_rejected_eopnotsupp_95(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            catalyst_tool=CATALYST_BROWSE_FREE_TOOL_G147,
            catalyst_breathing_comp_requested=True,
            distortion_comp="Auto",
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)

    def test_26_g147_catalyst_prepare_requires_distortion_comp_auto_not_off(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            catalyst_tool="Catalyst Prepare",
            catalyst_breathing_comp_requested=True,
            distortion_comp="Off",
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)

    def test_27_g147_fx6_breathing_rules_sq_on_any_raw_or_distortion_off_rejected_eopnotsupp_95(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            fx6_breathing_under_sq_or_raw_or_distortion_off_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)
        self.assertTrue(bad.fx6_cross_model_spoof_rejected)

    def test_28_g147_file_settings_all_initialize_only_claiming_camset_reset_fails(self) -> None:
        self.assertFalse(FILE_SETTINGS_RESETTABLE_BY_CAMSET_RESET_G147)
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_TITLE_G147,
            title_name="SCENE_A",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
            claimed_camset_reset_clears_file_settings_or_lens_comp=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION)

        st = resolve_fx3_breathing_and_file_settings_state(
            file_name_format=FILE_NAME_FORMAT_TITLE_G147,
            title_name="SCENE_A",
            reset_action=RESET_ACTION_INITIALIZE_PHASE331,
        )
        self.assertEqual(st["effective_file_name_format"], FILE_NAME_FORMAT_STANDARD_G147)
        self.assertEqual(st["effective_title_name"], TITLE_NAME_DEFAULT_G147)

    def test_29_g147_file_number_series_vs_reset_and_series_counter_reset_max_plus_1(self) -> None:
        ok_reset_counter = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_number_mode=FILE_NUMBER_SERIES_G147,
            series_counter_reset_triggered=True,
            existing_dir_max_file_number=42,
        )
        self.assertTrue(ok_reset_counter.valid)
        self.assertEqual(ok_reset_counter.sample_output_clip_stem, "C0043")

        ok_file_reset = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_number_mode=FILE_NUMBER_RESET_G147,
        )
        self.assertTrue(ok_file_reset.valid)
        self.assertEqual(ok_file_reset.sample_output_clip_stem, "C0001")

    def test_30_g147_file_name_format_5_modes_and_sdhc_fat32_hard_lock_standard(self) -> None:
        self.assertEqual(len(ALLOWED_FILE_NAME_FORMATS_G147), 5)
        ok_sdhc = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            card_type=CARD_TYPE_SDHC_G147,
            sdhc_capacity_gb=32,
            file_name_format=FILE_NAME_FORMAT_STANDARD_G147,
        )
        self.assertTrue(ok_sdhc.valid)
        self.assertTrue(ok_sdhc.sdhc_standard_format_locked)
        self.assertTrue(ok_sdhc.sdhc_4gb_split_enforced)

    def test_31_g147_sdhc_non_standard_format_blocked_einval(self) -> None:
        for fmt in (
            FILE_NAME_FORMAT_CAM_ID_REEL_G147,
            FILE_NAME_FORMAT_TITLE_G147,
            FILE_NAME_FORMAT_DATE_TITLE_G147,
            FILE_NAME_FORMAT_TITLE_DATE_G147,
        ):
            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                card_type=CARD_TYPE_SDHC_G147,
                sdhc_capacity_gb=32,
                file_name_format=fmt,
            )
            self.assertFalse(bad.valid, msg=fmt)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION)

    def test_32_g147_sdhc_xavcs_4gb_split_and_simult_rec_with_exfat_blocked(self) -> None:
        bad_bypass_split = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            card_type=CARD_TYPE_SDHC_G147,
            sdhc_capacity_gb=16,
            file_name_format=FILE_NAME_FORMAT_STANDARD_G147,
            sdhc_4gb_split_bypass_requested=True,
        )
        self.assertFalse(bad_bypass_split.valid)

        bad_simult = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            card_type=CARD_TYPE_SDHC_G147,
            sdhc_capacity_gb=32,
            file_name_format=FILE_NAME_FORMAT_STANDARD_G147,
            simult_recording_active=True,
            secondary_card_type=CARD_TYPE_SDXC_G147,
        )
        self.assertFalse(bad_simult.valid)
        self.assertEqual(bad_simult.status, STATUS_BLOCKED_G147_SDHC_FILESETTINGS_CAMID_TITLE_VIOLATION)
        self.assertTrue(bad_simult.simult_recording_mixed_fs_blocked)

        bad_cap = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            card_type=CARD_TYPE_SDHC_G147,
            sdhc_capacity_gb=64,
        )
        self.assertFalse(bad_cap.valid)

    def test_33_g147_cam_id_change_resets_reel_while_file_number_reset_preserves_reel(self) -> None:
        st_changed = resolve_fx3_breathing_and_file_settings_state(
            file_name_format=FILE_NAME_FORMAT_CAM_ID_REEL_G147,
            camera_id="B",
            previous_camera_id="A",
            reel_number=17,
            camera_position=CAMERA_POS_C_G147,
            file_seq_number=1,
        )
        self.assertEqual(st_changed["effective_reel_number"], 1)
        self.assertEqual(st_changed["sample_output_clip_stem"], "B001C001_261117AB")

        st_reset = resolve_fx3_breathing_and_file_settings_state(
            file_name_format=FILE_NAME_FORMAT_CAM_ID_REEL_G147,
            file_number_mode=FILE_NUMBER_RESET_G147,
            camera_id="A",
            previous_camera_id="A",
            reel_number=17,
            camera_position=CAMERA_POS_L_G147,
            file_seq_number=1,
        )
        self.assertEqual(st_reset["effective_reel_number"], 17)
        self.assertEqual(st_reset["sample_output_clip_stem"], "A017L001_261117AB")

        bad_claim = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_number_mode=FILE_NUMBER_RESET_G147,
            claimed_file_number_reset_clears_reel=True,
        )
        self.assertFalse(bad_claim.valid)

    def test_34_g147_cam_id_reel_c999_rolls_to_d001_without_mutating_menu_setting(self) -> None:
        ok = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_CAM_ID_REEL_G147,
            camera_id="A",
            previous_camera_id="A",
            reel_number=1,
            camera_position=CAMERA_POS_C_G147,
            file_seq_number=999,
            rollover_from_999=True,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_camera_position_menu, CAMERA_POS_C_G147)
        self.assertEqual(ok.effective_filename_position_char, "D")
        self.assertEqual(ok.sample_output_clip_stem, "A001D001_261117AB")

        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            rollover_from_999=True,
            claimed_999_overflow_mutates_menu_position=True,
        )
        self.assertFalse(bad.valid)

    def test_35_g147_camid_6digit_yymmdd_vs_date_title_8digit_yyyymmdd(self) -> None:
        ok_camid = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_CAM_ID_REEL_G147,
            camera_id="A",
            reel_number=1,
            file_seq_number=7,
        )
        self.assertTrue(ok_camid.valid)
        self.assertIn("_261117", ok_camid.sample_output_clip_stem)

        ok_dt = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_DATE_TITLE_G147,
            title_name="CAM_A",
            file_seq_number=7,
        )
        self.assertTrue(ok_dt.valid)
        self.assertEqual(ok_dt.sample_output_clip_stem, "20261117_CAM_A_0007")

    def test_36_g147_title_name_settings_default_c_and_37_char_limit_and_invalid_chars(self) -> None:
        self.assertEqual(TITLE_NAME_DEFAULT_G147, "C")
        self.assertEqual(TITLE_NAME_MAX_CHARS_G147, 37)
        ok_37 = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_TITLE_G147,
            title_name="A" * 37,
        )
        self.assertTrue(ok_37.valid)

        bad_38 = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_TITLE_G147,
            title_name="A" * 38,
        )
        self.assertFalse(bad_38.valid)

        bad_char = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            file_name_format=FILE_NAME_FORMAT_TITLE_G147,
            title_name="BAD TITLE!",
        )
        self.assertFalse(bad_char.valid)

    def test_37_g147_fx3_fixed_private_m4root_clip_vs_fx6_clip_name_format_and_xdroot_spoof(self) -> None:
        ok = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard()
        self.assertEqual(ok.fx3_movie_clip_folder_path, FX3_MOVIE_CLIP_FOLDER_PATH_G147)

        bad_xdroot = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            requested_custom_movie_folder_path=FX6_CFEXPRESS_CLIP_FOLDER_PATH_G147,
        )
        self.assertFalse(bad_xdroot.valid)

        bad_fx6_prefix = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            fx6_46char_title_prefix_or_xdroot_spoof_requested=True,
        )
        self.assertFalse(bad_fx6_prefix.valid)
        self.assertEqual(bad_fx6_prefix.block_errno, EOPNOTSUPP_ERRNO_PHASE331)

    def test_38_g147_slot1_tier0_vault_write_blocked_erofs_30_zero_sector_writes(self) -> None:
        bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            target_media_slot=MEDIA_SLOT_1_PHASE331,
            requested_write_operation=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G147_SLOT1_TIER0_VAULT_EROFS)
        self.assertTrue(bad.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_39_g147_slot2_write_ok_and_invalid_telemetry_blocked(self) -> None:
        ok_s2 = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            target_media_slot=MEDIA_SLOT_2_PHASE331,
            requested_write_operation=True,
        )
        self.assertTrue(ok_s2.valid)
        self.assertEqual(ok_s2.slot1_data_sector_writes, 0)

        for bad_kw in (
            {"breathing_comp": "Auto"},
            {"file_number_mode": "Continuous"},
            {"file_name_format": "Custom"},
            {"card_type": "SD"},
            {"target_media_slot": True},
        ):
            bad = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(**bad_kw)
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G147_TELEMETRY_INVALID)

    def test_40_g147_matrix_864_states_exact_counts(self) -> None:
        mat = compute_breathing_camid_reel_matrix()
        self.assertEqual(mat["total_matrix_states"], 864)
        self.assertGreater(mat["breathing_active_count"], 0)
        self.assertGreater(mat["breathing_blocked_hfr_count"], 0)
        self.assertGreater(mat["sdhc_standard_locked_count"], 0)
        self.assertGreater(mat["camset_preserved_camid_reel_count"], 0)
        self.assertGreater(mat["camset_reset_breathing_count"], 0)

    def test_41_g147_verdict_evidence_and_json_roundtrip(self) -> None:
        v, wrapped = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            force_clean_room=True
        )
        self.assertIn("s1_writes=0", v.evidence)
        encoded = json.dumps(wrapped.to_dict(), ensure_ascii=False)
        self.assertIn(G147_GATE_CODE, encoded)

    def test_42_g147_body_identity_validation_rejects_fx6_or_bad_id(self) -> None:
        bad_model = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            body_model_name=FX6_MODEL_NAME_PHASE331,
        )
        self.assertFalse(bad_model.valid)
        self.assertEqual(bad_model.status, STATUS_BLOCKED_G147_TELEMETRY_INVALID)

    def test_43_g147_breathing_min_fw_3_00_enforced_eopnotsupp_95(self) -> None:
        self.assertEqual(BREATHING_COMP_MIN_FW_G147, "3.00")
        bad_fw = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            firmware_version="1.01",
            breathing_comp=BREATHING_COMP_ON_G147,
        )
        self.assertFalse(bad_fw.valid)
        self.assertEqual(bad_fw.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(bad_fw.status, STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP)

    def test_44_g147_resolve_state_title_date_stem_formatting(self) -> None:
        st_td = resolve_fx3_breathing_and_file_settings_state(
            file_name_format=FILE_NAME_FORMAT_TITLE_DATE_G147,
            title_name="MY_FILM",
            file_seq_number=12,
        )
        self.assertEqual(st_td["sample_output_clip_stem"], "MY_FILM_20261117_0012")

    def test_45_g147_resolve_state_cam_id_lower_or_bad_rejected(self) -> None:
        bad_cam = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            camera_id="a",
        )
        self.assertFalse(bad_cam.valid)
        bad_reel = verify_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
            reel_number=1000,
        )
        self.assertFalse(bad_reel.valid)

    def test_46_g147_evaluate_wrapper_propagates_donor_audit_failure(self) -> None:
        if not _donors_available_here():
            self.skipTest("local donor artifacts absent in clean-room environment")
        bad_specs = dict(PINNED_PHASE331_DONOR_SPECS)
        family, rel, _s, sha, toks, desc = bad_specs["fx3_bk4_bin"]
        bad_specs["fx3_bk4_bin"] = (family, rel, 1, sha, toks, desc)
        with mock.patch.dict(
            fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.PINNED_PHASE331_DONOR_SPECS,
            bad_specs,
        ):
            v, w = evaluate_g147_breathing_comp_120p_catalyst_and_camid_reel_sdhc_vault_guard(
                force_clean_room=False
            )
            self.assertFalse(v.passed)
            self.assertFalse(w.valid)
            self.assertEqual(w.status, STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY)

    # =========================================================================
    # Section C: Gate G148 — Round-57 [Copyright Info] + [Write Serial], 2-Item [Power Setting], [NTSC/PAL] Vault (47..78)
    # =========================================================================

    def test_47_g148_defaults_pass_direct_and_audit_wrapper(self) -> None:
        res = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G148)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        v, wrapped = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            force_clean_room=True
        )
        self.assertTrue(v.passed)
        self.assertTrue(wrapped.valid)
        self.assertEqual(wrapped.gate_id, G148)
        self.assertEqual(wrapped.gate_code, G148_GATE_CODE)

    def test_48_g148_round57_reset_errata_copyright_4_items_and_write_serial_all_initialize_only(self) -> None:
        self.assertFalse(COPYRIGHT_INFO_RESETTABLE_BY_CAMSET_RESET_G148)
        self.assertFalse(WRITE_SERIAL_NUMBER_RESETTABLE_BY_CAMSET_RESET_G148)
        self.assertEqual(
            EXACT_4_COPYRIGHT_INFO_ITEMS_G148,
            ("Write Copyright Info", "Set Photographer", "Set Copyright", "Disp. Copyright Info"),
        )
        st = resolve_fx3_copyright_powersave_ntscpal_state(
            write_copyright_info="On",
            photographer_name="Alice Photographer",
            copyright_name="Alice Studio",
            write_serial_number="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
        )
        self.assertEqual(st["effective_write_copyright_info"], "On")
        self.assertEqual(st["effective_photographer"], "Alice Photographer")
        self.assertEqual(st["effective_copyright"], "Alice Studio")
        self.assertEqual(st["effective_write_serial_number"], "On")

    def test_49_g148_claiming_camset_reset_clears_copyright_or_serial_blocked_einval(self) -> None:
        for kw in (
            {"claimed_camset_reset_clears_write_copyright_info": True},
            {"claimed_camset_reset_clears_copyright_strings": True},
            {"claimed_camset_reset_clears_write_serial_number": True},
        ):
            bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION,
            )

    def test_50_g148_write_serial_number_is_active_still_and_movie_not_still_only(self) -> None:
        self.assertEqual(
            WRITE_SERIAL_NUMBER_SYMBOL_STILL_MOVIE_G148,
            "BKID_APP_setting_write_serial_number_still_movie",
        )
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            claimed_write_serial_number_still_only=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION,
        )

    def test_51_g148_photographer_and_copyright_exact_46_printable_ascii_limit(self) -> None:
        self.assertEqual(COPYRIGHT_MAX_CHARS_G148, 46)
        ok = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            write_copyright_info="On",
            photographer_name="P" * 46,
            copyright_name="C" * 46,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(len(ok.effective_photographer), 46)
        self.assertEqual(len(ok.effective_copyright), 46)

    def test_52_g148_photographer_or_copyright_47_chars_or_non_ascii_blocked(self) -> None:
        for bad_str in ("P" * 47, "摄影师", "Line1\nLine2"):
            bad_p = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                photographer_name=bad_str,
            )
            self.assertFalse(bad_p.valid)
            self.assertEqual(
                bad_p.status,
                STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION,
            )
            bad_c = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                copyright_name=bad_str,
            )
            self.assertFalse(bad_c.valid)

    def test_53_g148_camset_dat_excludes_copyright_info_blocks_pii_export(self) -> None:
        self.assertTrue(COPYRIGHT_INFO_EXCLUDED_FROM_CAMSET_DAT_G148)
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            claimed_copyright_info_exported_to_camset=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_COPYRIGHT_46CH_SERIAL_RESET_OR_CAMSET_PII_VIOLATION,
        )

    def test_54_g148_camset_dat_allows_write_serial_number_boolean_toggle(self) -> None:
        self.assertFalse(WRITE_SERIAL_NUMBER_EXCLUDED_FROM_CAMSET_DAT_G148)
        ok = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            write_serial_number="On",
        )
        self.assertTrue(ok.write_serial_number_toggle_camset_permitted)
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            claimed_write_serial_toggle_excluded_from_camset=True,
        )
        self.assertFalse(bad.valid)

    def test_55_g148_fx6_no_consumer_exif_copyright_spoof_rejected(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            fx6_consumer_exif_copyright_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP,
        )

    def test_56_g148_power_setting_option_exact_2_active_items_only(self) -> None:
        self.assertEqual(
            EXACT_2_POWER_SETTING_OPTION_ITEMS_G148,
            ("Power Save Start Time", "Auto Power OFF Temp."),
        )
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            power_setting_option_items=("Power Save Start Time",),
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
        )

    def test_57_g148_power_save_start_time_6_values_and_default_5_min(self) -> None:
        self.assertEqual(len(ALLOWED_POWER_SAVE_START_TIMES_G148), 6)
        for val in ALLOWED_POWER_SAVE_START_TIMES_G148:
            ok = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                power_save_start_time=val,
            )
            self.assertTrue(ok.valid, msg=val)

    def test_58_g148_dormant_power_save_values_rejected_eopnotsupp_95(self) -> None:
        for dormant_val in DORMANT_POWER_SAVE_VALUES_G148:
            bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                power_save_start_time=dormant_val,
            )
            self.assertFalse(bad.valid, msg=dormant_val)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP,
            )
            self.assertTrue(bad.dormant_power_save_value_rejected)

    def test_59_g148_dormant_power_save_by_monitor_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(
            DORMANT_POWER_SAVE_BY_MONITOR_BKID_G148,
            "BKID_APP_setting_monitor_power_linkage",
        )
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            requested_dormant_power_save_by_monitor=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP,
        )
        self.assertTrue(bad.dormant_monitor_power_saving_rejected)

    def test_60_g148_exact_9_official_power_save_auto_bypass_conditions_all_verified(self) -> None:
        self.assertEqual(len(EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148), 9)
        for cond in EXACT_9_POWER_SAVE_BYPASS_CONDITIONS_G148:
            ok = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                power_save_start_time=POWER_SAVE_10_SEC_G148,
                active_bypass_conditions=(cond,),
            )
            self.assertTrue(ok.valid, msg=cond)
            self.assertTrue(ok.effective_power_save_bypassed, msg=cond)
            self.assertIn(cond, ok.active_power_save_bypass_conditions)

    def test_61_g148_claiming_sleep_during_active_bypass_condition_blocked_einval(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            power_save_start_time=POWER_SAVE_10_SEC_G148,
            active_bypass_conditions=("recording_movies",),
            claimed_power_save_sleeps_during_bypass=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
        )

    def test_62_g148_unknown_power_save_bypass_condition_blocked_telemetry_invalid(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            active_bypass_conditions=("imaginary_bypass",),
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G148_TELEMETRY_INVALID)

    def test_63_g148_auto_power_off_temp_standard_vs_high_tripod_burn_hazard_handheld(self) -> None:
        ok_tripod = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G148,
            handheld_sustained_shooting_without_tripod=False,
        )
        self.assertTrue(ok_tripod.valid)

        bad_handheld = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G148,
            handheld_sustained_shooting_without_tripod=True,
        )
        self.assertFalse(bad_handheld.valid)
        self.assertEqual(bad_handheld.block_errno, EINVAL_ERRNO_PHASE331)
        self.assertEqual(
            bad_handheld.status,
            STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
        )

    def test_64_g148_power_setting_option_initialize_only_camset_reset_persists(self) -> None:
        self.assertFalse(POWER_SETTING_OPTION_RESETTABLE_BY_CAMSET_RESET_G148)
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE331,
            claimed_camset_reset_clears_powersave_or_ntscpal=True,
        )
        self.assertFalse(bad.valid)

    def test_65_g148_ntsc_pal_selector_initialize_only_and_mandatory_reboot_gate(self) -> None:
        self.assertFalse(NTSC_PAL_RESETTABLE_BY_CAMSET_RESET_G148)
        bad_no_reboot = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            video_system=VIDEO_SYSTEM_PAL_G148,
            previous_video_system=VIDEO_SYSTEM_NTSC_G148,
            reboot_confirmed=False,
        )
        self.assertFalse(bad_no_reboot.valid)
        self.assertEqual(
            bad_no_reboot.status,
            STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
        )

        ok_reboot = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            video_system=VIDEO_SYSTEM_PAL_G148,
            previous_video_system=VIDEO_SYSTEM_NTSC_G148,
            factory_video_system=VIDEO_SYSTEM_NTSC_G148,
            reboot_confirmed=True,
        )
        self.assertTrue(ok_reboot.valid)
        self.assertEqual(ok_reboot.effective_startup_banner, STARTUP_BANNER_PAL_G148)

    def test_66_g148_ntsc_pal_startup_banners_running_on_ntsc_pal_and_factory_none(self) -> None:
        st_pal = resolve_fx3_copyright_powersave_ntscpal_state(
            video_system=VIDEO_SYSTEM_PAL_G148,
            factory_video_system=VIDEO_SYSTEM_NTSC_G148,
        )
        self.assertEqual(st_pal["effective_startup_banner"], STARTUP_BANNER_PAL_G148)
        st_ntsc = resolve_fx3_copyright_powersave_ntscpal_state(
            video_system=VIDEO_SYSTEM_NTSC_G148,
            factory_video_system=VIDEO_SYSTEM_PAL_G148,
        )
        self.assertEqual(st_ntsc["effective_startup_banner"], STARTUP_BANNER_NTSC_G148)
        st_match = resolve_fx3_copyright_powersave_ntscpal_state(
            video_system=VIDEO_SYSTEM_NTSC_G148,
            factory_video_system=VIDEO_SYSTEM_NTSC_G148,
        )
        self.assertEqual(st_match["effective_startup_banner"], STARTUP_BANNER_NONE_G148)

    def test_67_g148_cross_system_ntsc_pal_movie_playback_blocked(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            video_system=VIDEO_SYSTEM_PAL_G148,
            playback_clip_video_system=VIDEO_SYSTEM_NTSC_G148,
            claimed_cross_system_playback_allowed=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_POWERSAVE_9COND_TEMP_HIGH_OR_NTSCPAL_VIOLATION,
        )

    def test_68_g148_slot1_tier0_vault_ntsc_pal_format_prompt_blocked_erofs_30(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            target_media_slot=MEDIA_SLOT_1_PHASE331,
            ntsc_pal_format_prompt_confirm_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS)
        self.assertTrue(bad.slot1_tier0_vault_format_firewall_blocked)
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_69_g148_slot1_tier0_vault_sd_erase_trim_blocked_erofs_30(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            target_media_slot=MEDIA_SLOT_1_PHASE331,
            sd_erase_trim_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE331)
        self.assertEqual(bad.status, STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS)
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_70_g148_slot2_ntsc_pal_format_prompt_allowed_without_slot1_violation(self) -> None:
        ok = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            target_media_slot=MEDIA_SLOT_2_PHASE331,
            ntsc_pal_format_prompt_confirm_requested=True,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.slot1_tier0_vault_format_firewall_blocked)
        self.assertEqual(ok.slot1_data_sector_writes, 0)

    def test_71_g148_fx6_project_rec_format_frequency_spoof_rejected_eopnotsupp_95(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            fx6_frequency_rec_format_spoof_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE331)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G148_DORMANT_MONITOR_POWER_SAVING_OR_FX6_EOPNOTSUPP,
        )

    def test_72_g148_matrix_288_states_exact_counts(self) -> None:
        mat = compute_copyright_powersave_ntscpal_matrix()
        self.assertEqual(mat["total_matrix_states"], 288)
        self.assertGreater(mat["camset_preserved_copyright_count"], 0)
        self.assertGreater(mat["camset_preserved_serial_count"], 0)
        self.assertGreater(mat["power_save_bypassed_count"], 0)
        self.assertGreater(mat["pal_banner_count"], 0)
        self.assertGreater(mat["temp_high_count"], 0)

    def test_73_g148_resid16_constants_pinned(self) -> None:
        self.assertEqual(COPYRIGHT_INFO_F_RESID16_G148, 0x6D53)
        self.assertEqual(POWER_SAVE_START_TIME_F_RESID16_G148, 0x69B0)
        self.assertEqual(AUTO_POWER_OFF_TEMP_F_RESID16_G148, 0x70F1)
        self.assertEqual(NTSC_PAL_SELECTOR_F_RESID16_G148, 0x6B6F)

    def test_74_g148_invalid_telemetry_paths_blocked(self) -> None:
        for bad_kw in (
            {"write_copyright_info": "Always"},
            {"write_serial_number": "Auto"},
            {"auto_power_off_temp": "Extreme"},
            {"video_system": "SECAM"},
            {"target_media_slot": True},
        ):
            bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(**bad_kw)
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G148_TELEMETRY_INVALID)

    def test_75_g148_body_identity_validation_rejects_fx6_or_bad_fw(self) -> None:
        bad = verify_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            body_model_id=0,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G148_TELEMETRY_INVALID)

    def test_76_g148_verdict_evidence_and_json_roundtrip(self) -> None:
        v, wrapped = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
            force_clean_room=True
        )
        self.assertIn("s1_writes=0", v.evidence)
        encoded = json.dumps(wrapped.to_dict(), ensure_ascii=False)
        self.assertIn(G148_GATE_CODE, encoded)

    def test_77_g148_evaluate_wrapper_propagates_donor_audit_failure(self) -> None:
        if not _donors_available_here():
            self.skipTest("local donor artifacts absent in clean-room environment")
        bad_specs = dict(PINNED_PHASE331_DONOR_SPECS)
        family, rel, _s, sha, toks, desc = bad_specs["fx3_string_english_g_uxc"]
        bad_specs["fx3_string_english_g_uxc"] = (family, rel, 1, sha, toks, desc)
        with mock.patch.dict(
            fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard.PINNED_PHASE331_DONOR_SPECS,
            bad_specs,
        ):
            v, w = evaluate_g148_copyright_46ch_serial_errata_and_powersave_ntscpal_vault_guard(
                force_clean_room=False
            )
            self.assertFalse(v.passed)
            self.assertFalse(w.valid)
            self.assertEqual(w.status, STATUS_BLOCKED_PHASE331_DONOR_INTEGRITY)

    def test_78_g148_resolve_state_initialize_clears_copyright_and_restores_defaults(self) -> None:
        st = resolve_fx3_copyright_powersave_ntscpal_state(
            write_copyright_info="On",
            photographer_name="User",
            copyright_name="Corp",
            write_serial_number="On",
            power_save_start_time=POWER_SAVE_10_SEC_G148,
            auto_power_off_temp=AUTO_POWER_OFF_TEMP_HIGH_G148,
            video_system=VIDEO_SYSTEM_PAL_G148,
            factory_video_system=VIDEO_SYSTEM_NTSC_G148,
            reset_action=RESET_ACTION_INITIALIZE_PHASE331,
        )
        self.assertEqual(st["effective_write_copyright_info"], "Off")
        self.assertEqual(st["effective_photographer"], "")
        self.assertEqual(st["effective_write_serial_number"], "Off")
        self.assertEqual(st["effective_power_save_start_time"], POWER_SAVE_5_MIN_G148)
        self.assertEqual(st["effective_auto_power_off_temp"], AUTO_POWER_OFF_TEMP_DEFAULT_G148)
        self.assertEqual(st["effective_video_system"], VIDEO_SYSTEM_NTSC_G148)

    # =========================================================================
    # Section D: Unified 148-Gate Master Preflight, Discovery & CLI (79..96)
    # =========================================================================

    def test_79_evaluate_148gate_preflight_offline_145_of_148(self) -> None:
        rep = evaluate_148gate_preflight(DEFAULT_REPO_ROOT)
        self.assertIsInstance(rep, Master148GateReport)
        self.assertEqual(rep.schema, REALHW_148GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.summary["total_gates"], 148)
        self.assertEqual(rep.summary["verified_gates"], 145)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_145_gates_verified)
        self.assertFalse(rep.all_148_gates_verified)
        self.assertTrue(rep.g13_to_g148_all_passed)
        self.assertTrue(rep.g147_to_g148_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(rep.gates), 148)

    def test_80_evaluate_148gate_preflight_dry_run_148_of_148(self) -> None:
        rep = evaluate_148gate_preflight(DEFAULT_REPO_ROOT, simulate_bench_dry_run=True)
        self.assertEqual(rep.status, "VERIFIED_ALL_148_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 148)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_148_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_81_backward_compat_evaluate_146gate_preflight_unchanged(self) -> None:
        r146 = evaluate_146gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(r146.summary["total_gates"], 146)
        self.assertEqual(r146.summary["verified_gates"], 143)
        self.assertTrue(r146.offline_143_gates_verified)

    def test_82_backward_compat_evaluate_144gate_unchanged(self) -> None:
        r144 = evaluate_144gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(r144.summary["total_gates"], 144)
        self.assertEqual(r144.summary["verified_gates"], 141)
        self.assertTrue(r144.offline_141_gates_verified)

    def test_83_highest_gate_discovery_hook_finds_148(self) -> None:
        pat = re.compile(r"^evaluate_(\d+)gate_preflight$")
        nums = [
            int(m.group(1))
            for attr in dir(fx3_safety)
            for m in [pat.match(attr)]
            if m and callable(getattr(fx3_safety, attr))
        ]
        self.assertIn(148, nums)
        self.assertGreaterEqual(max(nums), 148)

    def test_84_aliases_evaluate_148_master_safety_gates_and_run_148_gate_preflight(self) -> None:
        r1 = evaluate_148_master_safety_gates(DEFAULT_REPO_ROOT, force_clean_room=True)
        r2 = run_148_gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True)
        self.assertTrue(r1.offline_145_gates_verified)
        self.assertTrue(r2.all_148_gates_verified)

    def test_85_request_persistent_emmc_writes_fails_closed(self) -> None:
        rep = evaluate_148gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep.all_148_gates_verified)
        self.assertFalse(rep.offline_145_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_86_fault_injection_in_g147_blocks_148gate_preflight(self) -> None:
        rep = evaluate_148gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            breathing_camid_reel_kwargs={
                "catalyst_tool": CATALYST_BROWSE_FREE_TOOL_G147,
                "catalyst_breathing_comp_requested": True,
            },
        )
        self.assertFalse(rep.g147_to_g148_all_passed)
        self.assertFalse(rep.all_148_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G147_LENS_CATALYST_BROWSE_OR_FX6_EOPNOTSUPP,
        )

    def test_87_fault_injection_in_g148_blocks_148gate_preflight(self) -> None:
        rep = evaluate_148gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            copyright_powersave_ntscpal_kwargs={
                "target_media_slot": MEDIA_SLOT_1_PHASE331,
                "ntsc_pal_format_prompt_confirm_requested": True,
            },
        )
        self.assertFalse(rep.g147_to_g148_all_passed)
        self.assertFalse(rep.all_148_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G148_SLOT1_FORMAT_SD_ERASE_TRIM_VAULT_EROFS,
        )

    def test_88_fault_injection_in_master146_blocks_148gate_preflight(self) -> None:
        bad_m146 = evaluate_146gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            reclamp_varshutter_apsc_kwargs={"claimed_camset_reset_resets_apsc": True},
        )
        rep = evaluate_148gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_146_override=bad_m146,
        )
        self.assertFalse(rep.g13_to_g148_all_passed)
        self.assertFalse(rep.all_148_gates_verified)
        self.assertEqual(rep.status, bad_m146.status)

    def test_89_cli_main_verify_g147_and_g148_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-breathing-camid-reel-sdhc-guard",
            "verify-g147",
            "verify-copyright-powersave-ntscpal-guard",
            "verify-g148",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, msg=cmd)
            data = json.loads(buf.getvalue())
            self.assertTrue(data["valid"], msg=cmd)
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_90_cli_main_help_argparse_no_percent_formatting_crash(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        for subcmd in (
            "verify-breathing-camid-reel-sdhc-guard",
            "verify-copyright-powersave-ntscpal-guard",
            "verify-148-gates",
        ):
            with self.assertRaises(SystemExit) as sctx:
                with contextlib.redirect_stdout(io.StringIO()):
                    cli_main([subcmd, "--help"])
            self.assertEqual(sctx.exception.code, 0, msg=subcmd)

    def test_91_cli_main_verify_148_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = cli_main(["verify-148-gates", "--clean-room", "--summary", "--json"])
        self.assertEqual(rc_off, 0)
        d_off = json.loads(buf_off.getvalue())
        self.assertEqual(d_off["summary"]["verified_gates"], 145)
        self.assertEqual(d_off["summary"]["total_gates"], 148)

        buf_sim = io.StringIO()
        with contextlib.redirect_stdout(buf_sim):
            rc_sim = cli_main(
                ["verify-148-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
            )
        self.assertEqual(rc_sim, 0)
        d_sim = json.loads(buf_sim.getvalue())
        self.assertEqual(d_sim["summary"]["verified_gates"], 148)
        self.assertTrue(d_sim["summary"]["all_148_gates_verified"])

    def test_92_cli_main_verify_148_gates_text_mode_exit_codes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-148-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=148/148", buf.getvalue())
        self.assertIn("all_148_gates_verified=True", buf.getvalue())

    def test_93_module_main_entrypoint_g147_g148_148(self) -> None:
        for gate_arg in ("g147", "g148", "148"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", gate_arg, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, msg=gate_arg)
            parsed = json.loads(buf.getvalue())
            self.assertIsInstance(parsed, dict)

    def test_94_donorless_ubuntu_ci_cli_verify_148_gates_passes(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE331, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = cli_main(["verify-148-gates", "--summary", "--json"])
                self.assertEqual(rc, 0)
                d = json.loads(buf.getvalue())
                self.assertEqual(d["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(d["summary"]["verified_gates"], 145)

    def test_95_milestone_324_master_gate_auto_discovers_148_gates(self) -> None:
        extra_paths = [
            str(DEFAULT_REPO_ROOT / "outputs" / p)
            for p in (
                "fx6-on-fx3-closure",
                "fx3-safety",
                "fx3-recovery-adapter",
                "fx3-firmware-lab",
                "fx3-vm",
            )
        ]
        with mock.patch.object(sys, "path", extra_paths + sys.path):
            from fx6_closure.realhw_milestone324_master_gate import (
                evaluate_milestone_324_master_gate,
            )

            rep = evaluate_milestone_324_master_gate(
                repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
            )
            self.assertEqual(rep.gate142_total_gates, 148)
            self.assertEqual(rep.gate142_offline_verified, 145)
            self.assertEqual(rep.gate142_simulated_verified, 148)
            self.assertTrue(rep.gate142_all_verified)

    def test_96_milestone_311_master_gate_auto_discovers_148_gates(self) -> None:
        extra_paths = [
            str(DEFAULT_REPO_ROOT / "outputs" / p)
            for p in (
                "fx6-on-fx3-closure",
                "fx3-safety",
                "fx3-recovery-adapter",
                "fx3-firmware-lab",
                "fx3-vm",
            )
        ]
        with mock.patch.object(sys, "path", extra_paths + sys.path):
            from fx6_closure.realhw_milestone311_master_gate import (
                evaluate_milestone_311_master_gate,
            )

            rep = evaluate_milestone_311_master_gate(
                repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
            )
            self.assertEqual(rep.gate134_total_gates, 148)
            self.assertEqual(rep.gate134_offline_verified, 145)
            self.assertEqual(rep.gate134_simulated_verified, 148)
            self.assertTrue(rep.gate134_all_verified)


if __name__ == "__main__":
    unittest.main()
