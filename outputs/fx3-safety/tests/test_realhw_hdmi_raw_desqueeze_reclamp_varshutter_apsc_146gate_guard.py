"""Phase 327 (Task H394, Wave-63, 146/146 Safety Gates):
Dual-Mode Unit Tests (96 tests) for
`fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard`:

- Gate `G145` (`REALHW_HDMI_RAW_CO_REC_VAULT_AND_DESQUEEZE_4RATIO_GUARD`):
  - `Setup -> [External Output] -> [HDMI Output Settings]` exact 8 Initialize-only items
    (`[Rec. Media dur HDMI Output]` `On`/`Off(HDMI Only)` locked `On` in `S&Q`,
    `[Output Resolution]` forced `1080p` under Log/PPLUT when `Rec. Media = On` &
    `RAW = Off`, `[4K Output Set.(HDMI Only)]` 10-bit-only + `24.00p` reboot gate &
    dormant `24.00p 8bit` `EOPNOTSUPP=95`, `[RAW Output]` `4264x2408` 16-bit linear
    requiring Movie + `Log != Off`, `[RAW Output Setting]`, `[Time Code Output]`,
    `[REC Control]` requiring `Time Code Output = On`, `[4ch Audio Output]` `CH1/CH2`
    or `CH3/CH4`); removed standalone `[Color Gamut for RAW Output]` (`EOPNOTSUPP=95`);
    `RAW + Rec. Media = On` internal XAVC+Proxy co-recording `Slot-1` Tier-0 Vault
    `EROFS=30` vs `Off(HDMI Only)` zero-card-write bypass; `HDMI Info. Display = On`
    LCD blanking; vs `ILME-FX6` (`12G-SDI RAW`, `Parallel Rec`, SDI De-Squeeze).
  - `Setup -> [Display Option] -> [De-Squeeze Display]` Initialize-only Ver. 7.00/7.02
    5-state set (`Off`, `1.3x`, `1.5x`, `1.6x` [executing `1.65x`], `2.0x`), absent
    `1.8x` (`EOPNOTSUPP=95`), 4 forced lockouts, 6 auto-bypass conditions, coexistence
    with `Focus Magnifier` / `Bright Monitoring`, and zero internal file baking.
- Gate `G146` (`REALHW_RECLAMP_EMPH_REMAIN_AUTOREVIEW_DORMANT_VARSHUTTER_APSC_GUARD`):
  - `Setup -> [Setup Option] -> [REC Lamp]` Initialize-only 3 physical lamps (`All On`,
    `Only Front Off`, `All Off`), independent of `[Silent Mode]`, dormant `[Tally Light]`
    & `REC_LAMP_LIGHT_UP_ONLY_ONE` (`EOPNOTSUPP=95`), resettable `[Emphasized REC Display]`
    (Clean HDMI suppressed), Initialize-only `[Remain Shoot Display]`, Still-only
    Initialize-only `[Auto Review]` (disabled in Interval Shoot).
  - Dormant `[Var. Shutter]` (`high_res_ss` / `Anti-flicker Tv Scan` `EOPNOTSUPP=95`) vs
    Still mechanical-shutter-only resettable `[Anti-flicker Shoot.]` vs `FX6` `ECS`.
  - **Wave-42 Reset Errata**: `[APS-C S35 Shooting]` (`Auto`/`On`/`Off`) is
    **Initialize-only / NOT resettable by `[Camera Settings Reset]`**, clamping ALL
    4K/DCI 4K/S&Q 4K/4K HDMI Only/RAW Output formats to `HD 1920x1080 <= 120p` and
    Still `L: 12M` -> `M: 5.1M (2768x1848)`.
- Unified 146-Gate Master Safety Preflight (`evaluate_146gate_preflight` /
  `verify-146-gates`): `143/146` offline, `146/146` `--simulate-bench-dry-run`,
  `raw_firmware_bytes_leaked == 0`, donorless Ubuntu CI (`_iter_work_roots=()`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import re
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    audit_phase323_donor_contracts,
    evaluate_144gate_preflight,
)
from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    ALLOWED_APSC_S35_MODES_G146,
    ALLOWED_AUTO_REVIEW_MODES_G146,
    ALLOWED_FX3_DESQUEEZE_MODES_G145,
    ALLOWED_HDMI_4CH_AUDIO_MODES_G145,
    ALLOWED_HDMI_4K_10BIT_SETTINGS_G145,
    ALLOWED_HDMI_OUT_RESOLUTIONS_G145,
    ALLOWED_REC_LAMP_MODES_G146,
    ALLOWED_REC_MEDIA_HDMI_MODES_G145,
    ALLOWED_REMAIN_SHOOT_MODES_G146,
    APSC_S35_AUTO_G146,
    APSC_S35_OFF_G146,
    APSC_S35_ON_G146,
    APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET_G146,
    APSC_S35_STILL_ASPECT_DIMENSIONS_G146,
    AUTO_REVIEW_10_SEC_G146,
    AUTO_REVIEW_2_SEC_G146,
    AUTO_REVIEW_5_SEC_G146,
    AUTO_REVIEW_OFF_G146,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DESQUEEZE_1_3X_G145,
    DESQUEEZE_1_5X_G145,
    DESQUEEZE_1_65X_EXEC_G145,
    DESQUEEZE_1_6X_G145,
    DESQUEEZE_2_0X_G145,
    DESQUEEZE_OFF_G145,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE327,
    DONOR_CHECK_MAX_SECONDS_PHASE327,
    DORMANT_DESQUEEZE_1_8X_G145,
    DORMANT_HDMI_4K_24_00P_8BIT_G145,
    EBUSY_ERRNO_PHASE327,
    EINVAL_ERRNO_PHASE327,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE327,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE327,
    EROFS_ERRNO_PHASE327,
    EXACT_4_DESQUEEZE_LOCKOUTS_G145,
    EXACT_6_DESQUEEZE_AUTO_BYPASS_CONDITIONS_G145,
    EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145,
    FX3_DEFAULT_FW_VERSION_PHASE327,
    FX3_HDMI_RAW_BIT_DEPTH_G145,
    FX3_HDMI_RAW_DIMENSIONS_G145,
    FX3_HELP_GUIDE_CODE_PHASE327,
    FX3_MODEL_ID_PHASE327,
    FX3_MODEL_NAME_PHASE327,
    FX3_PHYSICAL_REC_LAMPS_G146,
    FX6_DESQUEEZE_MODES_G145,
    FX6_ECS_MAX_HZ_G146,
    FX6_ECS_MIN_HZ_G146,
    FX6_HDMI_RAW_DIMENSIONS_G145,
    FX6_SDI_RAW_DIMENSIONS_G145,
    G145,
    G145_GATE_CODE,
    G146,
    G146_GATE_CODE,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_4CH_AUDIO_CH1_CH2_G145,
    HDMI_4CH_AUDIO_CH3_CH4_G145,
    HDMI_4K_23_98P_10BIT_G145,
    HDMI_4K_24_00P_10BIT_G145,
    HDMI_4K_59_94P_10BIT_G145,
    HDMI_OUT_RES_1080P_G145,
    HDMI_OUT_RES_2160P_G145,
    HDMI_OUT_RES_AUTO_G145,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOG_SHOOTING_CINE_EI_G145,
    LOG_SHOOTING_CINE_EI_QUICK_G145,
    LOG_SHOOTING_FLEXIBLE_ISO_G145,
    LOG_SHOOTING_OFF_G145,
    MEDIA_SLOT_1_PHASE327,
    MEDIA_SLOT_2_PHASE327,
    MEDIA_SLOT_NONE_PHASE327,
    MOVIE_RES_4K_UHD_G146,
    MOVIE_RES_DCI_4K_G146,
    MOVIE_RES_FHD_1080P_G146,
    Master146GateReport,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE327,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE327,
    PINNED_PHASE327_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_146GATE_PREFLIGHT_SCHEMA,
    REC_LAMP_ALL_OFF_G146,
    REC_LAMP_ALL_ON_G146,
    REC_LAMP_ONLY_FRONT_OFF_G146,
    REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
    REC_MEDIA_HDMI_ON_G145,
    REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
    REMAIN_SHOOT_NOT_DISPLAYED_G146,
    REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
    RESET_ACTION_INITIALIZE_PHASE327,
    RESET_ACTION_RESET_NETWORK_SET_PHASE327,
    SHOOT_MODE_MOVIE_PHASE327,
    SHOOT_MODE_SQ_PHASE327,
    SHOOT_MODE_STILL_PHASE327,
    SHUTTER_TYPE_ELECTRONIC_G146,
    SHUTTER_TYPE_MECHANICAL_G146,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION,
    STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION,
    STATUS_BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION,
    STATUS_BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION,
    STATUS_BLOCKED_G145_TELEMETRY_INVALID,
    STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION,
    STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION,
    STATUS_BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION,
    STATUS_BLOCKED_G146_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY,
    STATUS_VERIFIED_G145,
    STATUS_VERIFIED_G146,
    STILL_SIZE_L_12M_G146,
    STILL_SIZE_M_5_1M_G146,
    USB_PACKETS_TRANSMITTED,
    audit_phase327_donor_contracts,
    compute_hdmi_raw_desqueeze_matrix,
    compute_reclamp_varshutter_apsc_matrix,
    evaluate_146_master_safety_gates,
    evaluate_146gate_preflight,
    evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard,
    evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard,
    main as module_main,
    resolve_fx3_hdmi_raw_desqueeze_state,
    resolve_fx3_reclamp_varshutter_apsc_state,
    run_146_gate_preflight,
    verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard,
    verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard,
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
    if os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE327, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return False
    wr = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    if wr is None:
        return False
    return all((wr / spec[1]).is_file() for spec in PINNED_PHASE327_DONOR_SPECS.values())


class TestPhase327Milestone146Gates(unittest.TestCase):
    # =========================================================================
    # Section A: Exports, Redlines & Dual-Mode / Donorless CI Audit (01..18)
    # =========================================================================

    def test_01_public_exports_present_in_package_and_all(self) -> None:
        required = (
            "G145",
            "G146",
            "Master146GateReport",
            "evaluate_146gate_preflight",
            "evaluate_146_master_safety_gates",
            "run_146_gate_preflight",
            "evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard",
            "evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard",
            "verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard",
            "verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard",
            "audit_phase327_donor_contracts",
            "realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard",
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
        audit = audit_phase327_donor_contracts(force_clean_room=True)
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
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE327):
            with mock.patch.dict(os.environ, {env_key: "1"}, clear=False):
                audit = audit_phase327_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_local_or_clean_room_budget_and_digests(self) -> None:
        audit = audit_phase327_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid, msg=f"errors={audit.errors}")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE327)
        if _donors_available_here():
            self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE327_DONOR_SPECS))
            self.assertEqual(audit.files_inspected, 11)
            self.assertTrue(audit.within_budget_200ms)
            self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE327)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")
            self.assertEqual(
                audit.file_digests["fx3_appfw_so"],
                PINNED_FX3_APPFW_SLICES_SHA256_PHASE327,
            )
            self.assertEqual(
                audit.file_digests["fx6_appfw_so"],
                PINNED_FX6_APPFW_SLICES_SHA256_PHASE327,
            )

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        audit = audit_phase327_donor_contracts(
            work_root=Path("/nonexistent/phase327/donor/root"),
            force_clean_room=False,
        )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_simulated_donorless_ubuntu_ci_iter_work_roots_empty_phase327(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE327, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                audit = audit_phase327_donor_contracts(force_clean_room=False)
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

                v145, r145 = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                    force_clean_room=False
                )
                self.assertTrue(v145.passed)
                self.assertTrue(r145.valid)
                self.assertEqual(r145.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                v146, r146 = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                    force_clean_room=False
                )
                self.assertTrue(v146.passed)
                self.assertTrue(r146.valid)
                self.assertEqual(r146.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                rep = evaluate_146gate_preflight(force_clean_room=False)
                self.assertTrue(rep.offline_143_gates_verified)
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_08_simulated_donorless_ubuntu_ci_phase323_compatibility(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE327, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                audit_323 = audit_phase323_donor_contracts(force_clean_room=False)
                self.assertTrue(audit_323.valid)
                self.assertEqual(audit_323.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_09_donor_audit_override_missing_file_fails_closed(self) -> None:
        bad_specs = {
            "missing_blob": (
                "FX3",
                "does/not/exist/file.bin",
                123,
                "0" * 64,
                (b"x",),
                "missing",
            )
        }
        audit = audit_phase327_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY)
        self.assertIn("missing_blob:file_missing", audit.missing_markers)

    def test_10_donor_audit_override_work_root_none_guarded(self) -> None:
        bad_specs = {
            "blob": (
                "FX3",
                "outputs/fx3-safety/README.md",
                1,
                "0" * 64,
                (b"x",),
                "work_root_none",
            )
        }
        with mock.patch(
            "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
            return_value=(),
        ):
            audit = audit_phase327_donor_contracts(
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY)
            self.assertIn("blob:work_root_none", audit.missing_markers)

    def test_11_donor_audit_override_size_and_sha_mismatch(self) -> None:
        target_rel = "outputs/fx3-safety/README.md"
        bad_specs = {
            "tampered": (
                "FX3",
                target_rel,
                1,
                "f" * 64,
                (b"FX3",),
                "tampered",
            )
        }
        audit = audit_phase327_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY)
        self.assertTrue(any("size_mismatch" in m for m in audit.missing_markers))
        self.assertTrue(any("sha256_mismatch" in m for m in audit.missing_markers))

    def test_12_donor_audit_override_token_missing(self) -> None:
        target_rel = "outputs/fx3-safety/README.md"
        full = (DEFAULT_REPO_ROOT / target_rel).read_bytes()
        import hashlib

        sha = hashlib.sha256(full).hexdigest()
        bad_specs = {
            "missing_tok": (
                "FX3",
                target_rel,
                len(full),
                sha,
                (b"NONEXISTENT_PHASE327_MARKER_XYZ_9999",),
                "missing_tok",
            )
        }
        audit = audit_phase327_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertTrue(any("token_missing" in m for m in audit.missing_markers))

    def test_13_pinned_donor_specs_exact_11_artifacts_and_4lang_uxc(self) -> None:
        self.assertEqual(len(PINNED_PHASE327_DONOR_SPECS), 11)
        for key in (
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
            "fx3_string_english_uxc",
            "fx3_string_english_g_uxc",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        ):
            self.assertIn(key, PINNED_PHASE327_DONOR_SPECS)

    def test_14_g145_rejects_wrong_body_identity(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            body_model_name="ILME-FX3A",
            body_model_id=0x9999,
            help_guide_code="ilc/9999",
            firmware_version="bad",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G145_TELEMETRY_INVALID)

    def test_15_g146_rejects_wrong_body_identity(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            body_model_name="ILME-FX6",
            body_model_id=0x0000,
            help_guide_code="ilc/9999",
            firmware_version="",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G146_TELEMETRY_INVALID)

    def test_16_g145_evaluators_propagate_donor_integrity_failure(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.audit_phase327_donor_contracts"
        ) as m_audit:
            from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
                Phase327DonorAuditResult,
            )

            m_audit.return_value = Phase327DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="STRICT_OS_O_RDONLY_PREAD",
                files_inspected=0,
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                zero_forbidden_myths_verified=False,
                elapsed_seconds=0.001,
                within_budget_200ms=True,
                raw_firmware_bytes_leaked=0,
                file_digests={},
                missing_markers=("tampered",),
                errors=("tampered",),
                warnings=(),
            )
            v, r = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard()
            self.assertFalse(v.passed)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY)

    def test_17_g146_evaluators_propagate_donor_integrity_failure(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.audit_phase327_donor_contracts"
        ) as m_audit:
            from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
                Phase327DonorAuditResult,
            )

            m_audit.return_value = Phase327DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="STRICT_OS_O_RDONLY_PREAD",
                files_inspected=0,
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                zero_forbidden_myths_verified=False,
                elapsed_seconds=0.001,
                within_budget_200ms=True,
                raw_firmware_bytes_leaked=0,
                file_digests={},
                missing_markers=("tampered",),
                errors=("tampered",),
                warnings=(),
            )
            v, r = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard()
            self.assertFalse(v.passed)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_PHASE327_DONOR_INTEGRITY)

    def test_18_g145_and_g146_gate_constants_and_versions(self) -> None:
        self.assertEqual(G145, "G145")
        self.assertEqual(G146, "G146")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE327, "7.02")
        self.assertEqual(FX3_MODEL_NAME_PHASE327, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE327, 0x0502)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE327, "ilc/2210")

    # =========================================================================
    # Section B: Gate G145 — HDMI 8-Item, RAW Co-Rec Vault & De-Squeeze (19..52)
    # =========================================================================

    def test_19_g145_baseline_valid(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G145)
        self.assertEqual(res.block_errno, 0)
        self.assertTrue(res.exact_8_hdmi_items_verified)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)

    def test_20_g145_exact_8_hdmi_items_required(self) -> None:
        self.assertEqual(len(EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145), 8)
        bad_7 = EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145[:-1]
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            hdmi_output_setting_items=bad_7
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G145_HDMI_8ITEM_RAW_REBOOT_OR_TC_VIOLATION)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE327)

    def test_21_g145_rejects_9th_removed_color_gamut_in_hdmi_menu(self) -> None:
        bad_9 = EXACT_8_HDMI_OUTPUT_SETTING_ITEMS_G145 + ("Color Gamut for RAW Output",)
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            hdmi_output_setting_items=bad_9,
            requested_standalone_color_gamut_for_raw_output=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION,
        )
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
        self.assertTrue(res.removed_color_gamut_for_raw_out_rejected)

    def test_22_g145_output_resolution_clamped_1080p_under_all_log_modes(self) -> None:
        for log_mode in (
            LOG_SHOOTING_FLEXIBLE_ISO_G145,
            LOG_SHOOTING_CINE_EI_G145,
            LOG_SHOOTING_CINE_EI_QUICK_G145,
        ):
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                log_shooting=log_mode,
                rec_media_dur_hdmi=REC_MEDIA_HDMI_ON_G145,
                hdmi_output_resolution=HDMI_OUT_RES_AUTO_G145,
                raw_output="Off",
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_OUT_RES_1080P_G145)

    def test_23_g145_output_resolution_clamped_1080p_under_pplut1_to_4(self) -> None:
        for pp in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                log_shooting=LOG_SHOOTING_OFF_G145,
                picture_profile=pp,
                rec_media_dur_hdmi=REC_MEDIA_HDMI_ON_G145,
                hdmi_output_resolution=HDMI_OUT_RES_2160P_G145,
                raw_output="Off",
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_OUT_RES_1080P_G145)

    def test_24_g145_off_hdmi_only_bypasses_1080p_clamp_and_zero_card_writes(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            log_shooting=LOG_SHOOTING_CINE_EI_G145,
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
            hdmi_output_resolution=HDMI_OUT_RES_2160P_G145,
            raw_output="Off",
            target_media_slot=MEDIA_SLOT_NONE_PHASE327,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_hdmi_output_resolution, HDMI_OUT_RES_2160P_G145)
        self.assertTrue(res.off_hdmi_only_zero_card_writes)
        self.assertFalse(res.internal_xavc_proxy_co_recording_active)

    def test_25_g145_sq_locks_rec_media_on_and_disables_tc_and_raw(self) -> None:
        st = resolve_fx3_hdmi_raw_desqueeze_state(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
            time_code_output="On",
            rec_control="On",
            raw_output="On",
        )
        self.assertEqual(st["effective_rec_media_dur_hdmi"], REC_MEDIA_HDMI_ON_G145)
        self.assertEqual(st["effective_time_code_output"], "Off")
        self.assertEqual(st["effective_rec_control"], "Off")
        self.assertEqual(st["effective_raw_output"], "Off")

        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE327)

    def test_26_g145_4k_output_set_all_6_10bit_modes_valid_and_reboot_gate(self) -> None:
        self.assertEqual(len(ALLOWED_HDMI_4K_10BIT_SETTINGS_G145), 6)
        for mode in ALLOWED_HDMI_4K_10BIT_SETTINGS_G145:
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                hdmi_4k_output_setting=mode,
                previous_hdmi_4k_output_setting=mode,
                reboot_confirmed=True,
            )
            self.assertTrue(res.valid, msg=mode)

    def test_27_g145_24_00p_10bit_without_reboot_blocked_both_directions(self) -> None:
        res_enter = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            hdmi_4k_output_setting=HDMI_4K_24_00P_10BIT_G145,
            previous_hdmi_4k_output_setting=HDMI_4K_23_98P_10BIT_G145,
            reboot_confirmed=False,
        )
        self.assertFalse(res_enter.valid)
        self.assertEqual(res_enter.block_errno, EINVAL_ERRNO_PHASE327)

        res_exit = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            hdmi_4k_output_setting=HDMI_4K_59_94P_10BIT_G145,
            previous_hdmi_4k_output_setting=HDMI_4K_24_00P_10BIT_G145,
            reboot_confirmed=False,
        )
        self.assertFalse(res_exit.valid)
        self.assertEqual(res_exit.block_errno, EINVAL_ERRNO_PHASE327)

    def test_28_g145_dormant_24_00p_8bit_rejected_eopnotsupp_95(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            hdmi_4k_output_setting=DORMANT_HDMI_4K_24_00P_8BIT_G145,
            requested_4k_hdmi_8bit_24p=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
        self.assertTrue(res.dormant_24p_8bit_rejected)

    def test_29_g145_raw_output_requires_movie_and_log_on(self) -> None:
        res_nolog = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            log_shooting=LOG_SHOOTING_OFF_G145,
            raw_output="On",
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertFalse(res_nolog.valid)
        self.assertEqual(res_nolog.block_errno, EINVAL_ERRNO_PHASE327)

        res_still = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            log_shooting=LOG_SHOOTING_CINE_EI_G145,
            raw_output="On",
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertFalse(res_still.valid)

    def test_30_g145_raw_output_4264x2408_16bit_locks_slog3_blocks_active_ss(self) -> None:
        res_ok = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G145,
            raw_output="On",
            raw_output_dimensions=FX3_HDMI_RAW_DIMENSIONS_G145,
            raw_output_bit_depth=FX3_HDMI_RAW_BIT_DEPTH_G145,
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.internal_xavc_proxy_co_recording_active)
        self.assertEqual(res_ok.effective_hdmi_info_display, "Off")

        res_bad_dim = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="On",
            raw_output_dimensions=FX6_HDMI_RAW_DIMENSIONS_G145,
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertFalse(res_bad_dim.valid)

        res_active_ss = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="On",
            raw_active_steadyshot_requested=True,
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertFalse(res_active_ss.valid)

        res_noslog3 = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="On",
            slog3_locked_when_raw_on=False,
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertFalse(res_noslog3.valid)

    def test_31_g145_raw_co_rec_slot1_tier0_vault_erofs_30_vs_off_hdmi_only_bypass(self) -> None:
        res_slot1 = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="On",
            rec_media_dur_hdmi=REC_MEDIA_HDMI_ON_G145,
            target_media_slot=MEDIA_SLOT_1_PHASE327,
        )
        self.assertFalse(res_slot1.valid)
        self.assertEqual(res_slot1.status, STATUS_BLOCKED_G145_SLOT1_CO_REC_VAULT_OR_LOG_CLAMP_VIOLATION)
        self.assertEqual(res_slot1.block_errno, EROFS_ERRNO_PHASE327)
        self.assertTrue(res_slot1.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(res_slot1.slot1_data_sector_writes, 0)

        # Cardless Off(HDMI Only) bypasses Slot-1 writes even with RAW Output = On
        res_cardless = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="On",
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
            target_media_slot=MEDIA_SLOT_1_PHASE327,
        )
        self.assertTrue(res_cardless.valid)
        self.assertFalse(res_cardless.internal_xavc_proxy_co_recording_active)
        self.assertTrue(res_cardless.off_hdmi_only_zero_card_writes)
        self.assertEqual(res_cardless.slot1_data_sector_writes, 0)

    def test_32_g145_rec_control_requires_time_code_output_on(self) -> None:
        res_bad = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            time_code_output="Off",
            rec_control="On",
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE327)

        res_ok = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            time_code_output="On",
            rec_control="On",
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.effective_rec_control, "On")

    def test_33_g145_4ch_audio_output_modes(self) -> None:
        self.assertEqual(
            ALLOWED_HDMI_4CH_AUDIO_MODES_G145,
            (HDMI_4CH_AUDIO_CH1_CH2_G145, HDMI_4CH_AUDIO_CH3_CH4_G145),
        )
        for ch_pair in ALLOWED_HDMI_4CH_AUDIO_MODES_G145:
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                hdmi_4ch_audio_output=ch_pair
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_4ch_audio_output, ch_pair)

    def test_34_g145_hdmi_info_display_on_blanks_built_in_lcd(self) -> None:
        res_blank = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            raw_output="Off",
            rec_media_dur_hdmi=REC_MEDIA_HDMI_ON_G145,
            hdmi_info_display="On",
        )
        self.assertTrue(res_blank.valid)
        self.assertTrue(res_blank.lcd_blanked_by_hdmi_info_display)

        res_raw = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            raw_output="On",
            rec_media_dur_hdmi=REC_MEDIA_HDMI_ON_G145,
            hdmi_info_display="On",
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertTrue(res_raw.valid)
        self.assertFalse(res_raw.lcd_blanked_by_hdmi_info_display)
        self.assertEqual(res_raw.effective_hdmi_info_display, "Off")

    def test_35_g145_initialize_only_persists_across_camset_and_network_reset(self) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
            RESET_ACTION_RESET_NETWORK_SET_PHASE327,
        ):
            st = resolve_fx3_hdmi_raw_desqueeze_state(
                rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
                desqueeze_display=DESQUEEZE_1_6X_G145,
                reset_action=rst,
            )
            self.assertEqual(st["effective_rec_media_dur_hdmi"], REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145)
            self.assertEqual(st["effective_desqueeze_display"], DESQUEEZE_1_6X_G145)
            self.assertEqual(st["effective_desqueeze_exec_ratio"], "1.0x")  # auto-bypassed by Off(HDMI Only)

        st_init = resolve_fx3_hdmi_raw_desqueeze_state(
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
            desqueeze_display=DESQUEEZE_1_6X_G145,
            reset_action=RESET_ACTION_INITIALIZE_PHASE327,
        )
        self.assertEqual(st_init["effective_rec_media_dur_hdmi"], REC_MEDIA_HDMI_ON_G145)
        self.assertEqual(st_init["effective_desqueeze_display"], DESQUEEZE_OFF_G145)

        res_bad = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
            claimed_camset_reset_clears_hdmi_or_desqueeze=True,
        )
        self.assertFalse(res_bad.valid)

    def test_36_g145_fx6_cross_model_spoofs_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(FX6_SDI_RAW_DIMENSIONS_G145, ("4096x2160", "3840x2160 C"))
        for kw in (
            {"fx6_12g_sdi_raw_requested": True},
            {"fx6_parallel_rec_requested": True},
            {"fx6_sdi_desqueeze_requested": True},
        ):
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
            self.assertTrue(res.fx6_cross_model_spoof_rejected)

    def test_37_g145_desqueeze_5_state_set_and_1_6x_executes_1_65x(self) -> None:
        self.assertEqual(
            ALLOWED_FX3_DESQUEEZE_MODES_G145,
            (
                DESQUEEZE_OFF_G145,
                DESQUEEZE_1_3X_G145,
                DESQUEEZE_1_5X_G145,
                DESQUEEZE_1_6X_G145,
                DESQUEEZE_2_0X_G145,
            ),
        )
        for ratio in ALLOWED_FX3_DESQUEEZE_MODES_G145:
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                desqueeze_display=ratio
            )
            self.assertTrue(res.valid, msg=ratio)
            if ratio == DESQUEEZE_1_6X_G145:
                self.assertEqual(res.effective_desqueeze_exec_ratio, DESQUEEZE_1_65X_EXEC_G145)
            elif ratio == DESQUEEZE_OFF_G145:
                self.assertEqual(res.effective_desqueeze_exec_ratio, "1.0x")
            else:
                self.assertEqual(res.effective_desqueeze_exec_ratio, ratio)

    def test_38_g145_desqueeze_absent_1_8x_rejected_eopnotsupp_95(self) -> None:
        self.assertNotIn(DORMANT_DESQUEEZE_1_8X_G145, ALLOWED_FX3_DESQUEEZE_MODES_G145)
        self.assertNotIn(DESQUEEZE_1_6X_G145, FX6_DESQUEEZE_MODES_G145)
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            desqueeze_display=DORMANT_DESQUEEZE_1_8X_G145,
            requested_desqueeze_1_8x=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
        self.assertTrue(res.dormant_desqueeze_1_8x_rejected)

    def test_39_g145_desqueeze_4_forced_lockouts_enforced(self) -> None:
        self.assertEqual(len(EXACT_4_DESQUEEZE_LOCKOUTS_G145), 4)
        res_ok = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            desqueeze_display=DESQUEEZE_1_5X_G145
        )
        self.assertEqual(res_ok.desqueeze_active_lockouts, EXACT_4_DESQUEEZE_LOCKOUTS_G145)

        for bad_kw in (
            {"focus_mode_during_desqueeze": "AF-C"},
            {"focus_area_during_desqueeze": "Spot: M"},
            {"steadyshot_during_desqueeze": "Standard"},
            {"face_priority_multi_metering_during_desqueeze": "On"},
        ):
            res_bad = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                desqueeze_display=DESQUEEZE_1_5X_G145,
                **bad_kw,
            )
            self.assertFalse(res_bad.valid, msg=bad_kw)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G145_DESQUEEZE_5STATE_LOCKOUT_OR_BYPASS_VIOLATION,
            )

    def test_40_g145_desqueeze_6_auto_bypass_conditions(self) -> None:
        self.assertEqual(len(EXACT_6_DESQUEEZE_AUTO_BYPASS_CONDITIONS_G145), 6)
        scenarios = [
            {"log_shooting": LOG_SHOOTING_OFF_G145},
            {"raw_output": "On", "target_media_slot": MEDIA_SLOT_2_PHASE327},
            {"rec_media_dur_hdmi": REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145},
            {"shoot_mode": SHOOT_MODE_STILL_PHASE327, "still_movie_rec_button_pressed": True},
            {"remote_shooting": True},
            {"photo_capture_active": True},
        ]
        for kw in scenarios:
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                desqueeze_display=DESQUEEZE_2_0X_G145,
                **kw,
            )
            self.assertTrue(res.valid, msg=kw)
            self.assertTrue(res.desqueeze_auto_bypassed, msg=kw)
            self.assertEqual(res.effective_desqueeze_exec_ratio, "1.0x", msg=kw)
            self.assertEqual(res.desqueeze_active_lockouts, (), msg=kw)

    def test_41_g145_desqueeze_coexists_with_magnifier_and_bright_monitoring(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            desqueeze_display=DESQUEEZE_1_3X_G145,
            focus_magnifier_active=True,
            bright_monitoring_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.desqueeze_coexists_with_magnifier_and_brightmon)
        self.assertFalse(res.desqueeze_baked_into_file)

    def test_42_g145_desqueeze_rejects_still_mode_without_movie_rec_and_rejects_baking(self) -> None:
        res_still = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            desqueeze_display=DESQUEEZE_1_3X_G145,
            still_movie_rec_button_pressed=False,
        )
        self.assertFalse(res_still.valid)

        res_bake = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            desqueeze_display=DESQUEEZE_1_3X_G145,
            desqueeze_baked_into_file_requested=True,
        )
        self.assertFalse(res_bake.valid)
        self.assertEqual(res_bake.block_errno, EINVAL_ERRNO_PHASE327)

    def test_43_g145_matrix_576_states(self) -> None:
        mat = compute_hdmi_raw_desqueeze_matrix()
        self.assertEqual(mat["total_matrix_states"], 576)
        self.assertGreater(mat["clamped_1080p_count"], 0)
        self.assertGreater(mat["co_rec_count"], 0)
        self.assertGreater(mat["desqueeze_165_exec_count"], 0)
        self.assertGreater(mat["desqueeze_bypass_count"], 0)
        self.assertGreater(mat["lcd_blanked_count"], 0)

    def test_44_g145_invalid_telemetry_enums_fail_closed(self) -> None:
        for bad_kw in (
            {"shoot_mode": "Timelapse"},
            {"log_shooting": "S-Log2"},
            {"rec_media_dur_hdmi": "Dual"},
            {"hdmi_output_resolution": "4320p"},
            {"raw_output_setting": "120p"},
            {"hdmi_4ch_audio_output": "CH1/CH4"},
            {"target_media_slot": 99},
        ):
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G145_TELEMETRY_INVALID)

    def test_45_g145_evaluates_with_slot2_raw_co_rec_valid(self) -> None:
        v, r = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            force_clean_room=True,
            raw_output="On",
            target_media_slot=MEDIA_SLOT_2_PHASE327,
        )
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G145)
        self.assertEqual(v.gate_code, G145_GATE_CODE)

    def test_46_g145_raw_output_setting_all_6_rates(self) -> None:
        from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
            ALLOWED_RAW_OUTPUT_SETTINGS_G145,
        )

        self.assertEqual(len(ALLOWED_RAW_OUTPUT_SETTINGS_G145), 6)
        for rate in ALLOWED_RAW_OUTPUT_SETTINGS_G145:
            res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
                raw_output="On",
                raw_output_setting=rate,
                target_media_slot=MEDIA_SLOT_2_PHASE327,
            )
            self.assertTrue(res.valid, msg=rate)
            self.assertEqual(res.effective_raw_output_setting, rate)

    def test_47_g145_hdmi_4k_output_setting_preserves_under_off_hdmi_only(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            rec_media_dur_hdmi=REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145,
            hdmi_4k_output_setting=HDMI_4K_23_98P_10BIT_G145,
            previous_hdmi_4k_output_setting=HDMI_4K_23_98P_10BIT_G145,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_hdmi_4k_output_setting, HDMI_4K_23_98P_10BIT_G145)

    def test_48_g145_rec_media_hdmi_modes_exact_2(self) -> None:
        self.assertEqual(
            ALLOWED_REC_MEDIA_HDMI_MODES_G145,
            (REC_MEDIA_HDMI_ON_G145, REC_MEDIA_HDMI_OFF_HDMI_ONLY_G145),
        )

    def test_49_g145_hdmi_output_resolutions_exact_4(self) -> None:
        self.assertEqual(
            ALLOWED_HDMI_OUT_RESOLUTIONS_G145,
            ("Auto", "2160p", "1080p", "1080i"),
        )

    def test_50_g145_explicit_write_request_on_slot1_blocked_erofs_30(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            raw_output="Off",
            target_media_slot=MEDIA_SLOT_1_PHASE327,
            requested_write_operation=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE327)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_51_g145_result_to_dict_serializable(self) -> None:
        _, r = evaluate_g145_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            force_clean_room=True
        )
        payload = json.dumps(r.to_dict())
        self.assertIn("VERIFIED_G145", payload)

    def test_52_g145_desqueeze_1_6x_in_sq_mode_executes_1_65x(self) -> None:
        res = verify_hdmi_raw_co_rec_vault_and_desqueeze_4ratio_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G145,
            time_code_output="Off",
            desqueeze_display=DESQUEEZE_1_6X_G145,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_desqueeze_exec_ratio, DESQUEEZE_1_65X_EXEC_G145)

    # =========================================================================
    # Section C: Gate G146 — REC Lamp, Emph, Remain, Auto Review, Var. Shutter,
    #            and Wave-42 APS-C S35 Reset Errata (53..84)
    # =========================================================================

    def test_53_g146_baseline_valid(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G146)
        self.assertEqual(res.physical_rec_lamps_count, FX3_PHYSICAL_REC_LAMPS_G146)
        self.assertEqual(res.physical_rec_lamps_count, 3)
        self.assertFalse(res.apsc_s35_resettable_by_camset_reset)

    def test_54_g146_rec_lamp_3_modes_and_independent_of_silent_mode(self) -> None:
        self.assertEqual(
            ALLOWED_REC_LAMP_MODES_G146,
            (REC_LAMP_ALL_ON_G146, REC_LAMP_ONLY_FRONT_OFF_G146, REC_LAMP_ALL_OFF_G146),
        )
        for mode in ALLOWED_REC_LAMP_MODES_G146:
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                rec_lamp=mode,
                silent_mode="On",
            )
            self.assertTrue(res.valid, msg=mode)
            self.assertEqual(res.effective_rec_lamp, mode)
            self.assertTrue(res.rec_lamp_independent_of_silent_mode)

        res_bad = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            silent_mode="On",
            rec_lamp_turned_off_by_silent_mode=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G146_REC_LAMP_EMPH_REMAIN_OR_AUTO_REVIEW_VIOLATION,
        )

    def test_55_g146_dormant_tally_light_and_only_one_rejected_eopnotsupp_95(self) -> None:
        for kw in (
            {"requested_tally_light_menu": True},
            {"requested_rec_lamp_light_up_only_one": True},
            {"fx6_independent_tally_or_gy_requested": True},
        ):
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                **kw
            )
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)

    def test_56_g146_emphasized_rec_display_resettable_and_clean_hdmi_suppressed(self) -> None:
        st_rst = resolve_fx3_reclamp_varshutter_apsc_state(
            emphasized_rec_display="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
        )
        self.assertEqual(st_rst["effective_emphasized_rec_display"], "On")

        res_bad = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            emphasized_rec_output_on_clean_hdmi=True
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE327)

    def test_57_g146_remain_shoot_display_3_modes_and_initialize_only(self) -> None:
        self.assertEqual(
            ALLOWED_REMAIN_SHOOT_MODES_G146,
            (
                REMAIN_SHOOT_NOT_DISPLAYED_G146,
                REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
                REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146,
            ),
        )
        for mode in ALLOWED_REMAIN_SHOOT_MODES_G146:
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE327,
                remain_shoot_display=mode,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_remain_shoot_display, mode)

        st = resolve_fx3_reclamp_varshutter_apsc_state(
            remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
        )
        self.assertEqual(st["effective_remain_shoot_display"], REMAIN_SHOOT_ALWAYS_DISPLAY_G146)

    def test_58_g146_auto_review_still_only_4_modes_and_interval_shoot_lockout(self) -> None:
        self.assertEqual(
            ALLOWED_AUTO_REVIEW_MODES_G146,
            (
                AUTO_REVIEW_OFF_G146,
                AUTO_REVIEW_2_SEC_G146,
                AUTO_REVIEW_5_SEC_G146,
                AUTO_REVIEW_10_SEC_G146,
            ),
        )
        for mode in ALLOWED_AUTO_REVIEW_MODES_G146:
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE327,
                auto_review=mode,
            )
            self.assertTrue(res.valid, msg=mode)
            self.assertEqual(res.effective_auto_review, mode)

        res_iv = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            auto_review=AUTO_REVIEW_2_SEC_G146,
            interval_shoot_active=True,
        )
        self.assertFalse(res_iv.valid)

        res_mv = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            auto_review=AUTO_REVIEW_5_SEC_G146,
        )
        self.assertFalse(res_mv.valid)

    def test_59_g146_dormant_var_shutter_and_fx6_ecs_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(FX6_ECS_MIN_HZ_G146, 23.99)
        self.assertEqual(FX6_ECS_MAX_HZ_G146, 8000.0)
        for kw in (
            {"requested_dormant_var_shutter": True},
            {"requested_dormant_anti_flicker_tv_scan": True},
            {"fx6_ecs_requested": True},
        ):
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                **kw
            )
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G146_DORMANT_VAR_SHUTTER_OR_ANTI_FLICKER_VIOLATION,
            )

    def test_60_g146_anti_flicker_shoot_valid_only_in_still_mechanical_shutter(self) -> None:
        res_ok = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            shutter_type=SHUTTER_TYPE_MECHANICAL_G146,
            silent_mode="Off",
            anti_flicker_shoot="On",
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.effective_anti_flicker_shoot, "On")

        for bad_kw in (
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE327, "anti_flicker_shoot": "On"},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE327, "anti_flicker_shoot": "On"},
            {
                "shoot_mode": SHOOT_MODE_STILL_PHASE327,
                "shutter_type": SHUTTER_TYPE_ELECTRONIC_G146,
                "anti_flicker_shoot": "On",
            },
            {
                "shoot_mode": SHOOT_MODE_STILL_PHASE327,
                "silent_mode": "On",
                "anti_flicker_shoot": "On",
            },
            {
                "shoot_mode": SHOOT_MODE_STILL_PHASE327,
                "bulb_active": True,
                "anti_flicker_shoot": "On",
            },
        ):
            res_bad = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                **bad_kw
            )
            self.assertFalse(res_bad.valid, msg=bad_kw)
            self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE327)

    def test_61_g146_wave42_reset_errata_apsc_s35_initialize_only(self) -> None:
        self.assertFalse(APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET_G146)
        st_camset = resolve_fx3_reclamp_varshutter_apsc_state(
            apsc_s35_shooting=APSC_S35_ON_G146,
            anti_flicker_shoot="On",
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
        )
        # Camera Settings Reset resets Anti-flicker & Emph REC, but MUST preserve APS-C S35!
        self.assertEqual(st_camset["effective_apsc_s35_shooting"], APSC_S35_ON_G146)
        self.assertTrue(st_camset["apsc_s35_active"])
        self.assertEqual(st_camset["effective_anti_flicker_shoot"], "Off")

        st_init = resolve_fx3_reclamp_varshutter_apsc_state(
            apsc_s35_shooting=APSC_S35_ON_G146,
            reset_action=RESET_ACTION_INITIALIZE_PHASE327,
        )
        self.assertEqual(st_init["effective_apsc_s35_shooting"], APSC_S35_AUTO_G146)

    def test_62_g146_rejects_false_claim_that_camset_resets_apsc_or_rec_lamp(self) -> None:
        res_apsc = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
            claimed_camset_reset_resets_apsc=True,
        )
        self.assertFalse(res_apsc.valid)
        self.assertEqual(
            res_apsc.status,
            STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION,
        )

        res_lamp = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
            claimed_camset_reset_resets_rec_lamp_or_autoreview=True,
        )
        self.assertFalse(res_lamp.valid)

    def test_63_g146_apsc_on_locks_out_all_4k_dci4k_sq4k_hdmi_raw_to_fhd_120p(self) -> None:
        for bad_res in (MOVIE_RES_4K_UHD_G146, MOVIE_RES_DCI_4K_G146):
            res_bad = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
                apsc_s35_shooting=APSC_S35_ON_G146,
                movie_resolution=bad_res,
                movie_fps=24,
            )
            self.assertFalse(res_bad.valid, msg=bad_res)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION,
            )

        res_hfr = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            movie_resolution=MOVIE_RES_FHD_1080P_G146,
            movie_fps=240,
        )
        self.assertFalse(res_hfr.valid)

        res_hdmi = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            movie_resolution=MOVIE_RES_FHD_1080P_G146,
            movie_fps=60,
            requested_4k_hdmi_raw_under_apsc=True,
        )
        self.assertFalse(res_hdmi.valid)

        res_ok = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            movie_resolution=MOVIE_RES_FHD_1080P_G146,
            movie_fps=120,
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.effective_movie_max_resolution, MOVIE_RES_FHD_1080P_G146)
        self.assertEqual(res_ok.effective_movie_max_fps, 120)

    def test_64_g146_apsc_auto_plus_apsc_lens_triggers_crop_lockout_vs_off(self) -> None:
        res_auto_crop = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            apsc_s35_shooting=APSC_S35_AUTO_G146,
            apsc_lens_attached=True,
            movie_resolution=MOVIE_RES_4K_UHD_G146,
        )
        self.assertFalse(res_auto_crop.valid)

        res_off_override = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            apsc_s35_shooting=APSC_S35_OFF_G146,
            apsc_lens_attached=True,
            movie_resolution=MOVIE_RES_4K_UHD_G146,
        )
        self.assertTrue(res_off_override.valid)

    def test_65_g146_apsc_clamps_still_l_12m_to_m_5_1m_2768x1848(self) -> None:
        self.assertEqual(APSC_S35_STILL_ASPECT_DIMENSIONS_G146["3:2"], "2768x1848 (5.1M)")
        res_l = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            still_image_size=STILL_SIZE_L_12M_G146,
        )
        self.assertFalse(res_l.valid)

        res_m = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            still_image_size=STILL_SIZE_M_5_1M_G146,
        )
        self.assertTrue(res_m.valid)
        self.assertEqual(res_m.effective_still_max_size, STILL_SIZE_M_5_1M_G146)

    def test_66_g146_fx6_clear_image_zoom_4k_rejected_eopnotsupp_95(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            fx6_clear_image_zoom_4k_requested=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE327)
        self.assertTrue(res.fx6_tally_ecs_or_ciz4k_spoof_rejected)

    def test_67_g146_matrix_648_states(self) -> None:
        mat = compute_reclamp_varshutter_apsc_matrix()
        self.assertEqual(mat["total_matrix_states"], 648)
        self.assertGreater(mat["apsc_fhd_clamped_count"], 0)
        self.assertGreater(mat["apsc_still_5_1m_count"], 0)
        self.assertGreater(mat["camset_preserved_apsc_on_count"], 0)
        self.assertGreater(mat["anti_flicker_active_count"], 0)

    def test_68_g146_invalid_telemetry_enums_fail_closed(self) -> None:
        for bad_kw in (
            {"shoot_mode": "Panorama"},
            {"silent_mode": "Auto"},
            {"shutter_type": "Leaf"},
            {"rec_lamp": "Only One"},
            {"emphasized_rec_display": "Blinking"},
            {"remain_shoot_display": "Never"},
            {"auto_review": "30 Sec"},
            {"anti_flicker_shoot": "Auto"},
            {"apsc_s35_shooting": "S16"},
            {"movie_resolution": "8K"},
            {"movie_fps": 0},
            {"still_image_size": "XL: 61M"},
            {"reset_action": "Factory Wipe"},
        ):
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                **bad_kw
            )
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G146_TELEMETRY_INVALID)

    def test_69_g146_evaluates_with_clean_room_still_auto_review_and_antiflicker(self) -> None:
        v, r = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            force_clean_room=True,
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            auto_review=AUTO_REVIEW_5_SEC_G146,
            anti_flicker_shoot="On",
            remain_shoot_display=REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G146,
        )
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(v.gate_id, G146)
        self.assertEqual(v.gate_code, G146_GATE_CODE)

    def test_70_g146_rec_lamp_preserved_across_camset_reset(self) -> None:
        st = resolve_fx3_reclamp_varshutter_apsc_state(
            rec_lamp=REC_LAMP_ONLY_FRONT_OFF_G146,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
        )
        self.assertEqual(st["effective_rec_lamp"], REC_LAMP_ONLY_FRONT_OFF_G146)

    def test_71_g146_auto_review_preserved_across_camset_reset(self) -> None:
        st = resolve_fx3_reclamp_varshutter_apsc_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            auto_review=AUTO_REVIEW_10_SEC_G146,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE327,
        )
        self.assertEqual(st["effective_auto_review"], AUTO_REVIEW_10_SEC_G146)

    def test_72_g146_initialize_resets_all_g146_menus_to_defaults(self) -> None:
        st = resolve_fx3_reclamp_varshutter_apsc_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            rec_lamp=REC_LAMP_ALL_OFF_G146,
            emphasized_rec_display="Off",
            remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
            auto_review=AUTO_REVIEW_10_SEC_G146,
            anti_flicker_shoot="On",
            apsc_s35_shooting=APSC_S35_ON_G146,
            reset_action=RESET_ACTION_INITIALIZE_PHASE327,
        )
        self.assertEqual(st["effective_rec_lamp"], REC_LAMP_ALL_ON_G146)
        self.assertEqual(st["effective_emphasized_rec_display"], "On")
        self.assertEqual(st["effective_remain_shoot_display"], REMAIN_SHOOT_NOT_DISPLAYED_G146)
        self.assertEqual(st["effective_auto_review"], AUTO_REVIEW_OFF_G146)
        self.assertEqual(st["effective_anti_flicker_shoot"], "Off")
        self.assertEqual(st["effective_apsc_s35_shooting"], APSC_S35_AUTO_G146)

    def test_73_g146_apsc_still_aspects_all_4_ratios_present(self) -> None:
        self.assertEqual(set(APSC_S35_STILL_ASPECT_DIMENSIONS_G146.keys()), {"3:2", "16:9", "4:3", "1:1"})

    def test_74_g146_apsc_modes_exact_3(self) -> None:
        self.assertEqual(ALLOWED_APSC_S35_MODES_G146, (APSC_S35_AUTO_G146, APSC_S35_ON_G146, APSC_S35_OFF_G146))

    def test_75_g146_interval_shoot_still_with_auto_review_off_passes(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            interval_shoot_active=True,
            auto_review=AUTO_REVIEW_OFF_G146,
        )
        self.assertTrue(res.valid)

    def test_76_g146_anti_flicker_frequencies_100_120hz(self) -> None:
        from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
            ANTI_FLICKER_FREQUENCIES_HZ_G146,
        )

        self.assertEqual(ANTI_FLICKER_FREQUENCIES_HZ_G146, (100, 120))

    def test_77_g146_result_to_dict_serializable(self) -> None:
        _, r = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            force_clean_room=True
        )
        payload = json.dumps(r.to_dict())
        self.assertIn("VERIFIED_G146", payload)

    def test_78_g146_remain_shoot_in_movie_persists_still_config_without_error(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
            remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G146,
        )
        self.assertTrue(res.valid)

    def test_79_g146_apsc_on_sq_120fps_fhd_valid(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            movie_resolution=MOVIE_RES_FHD_1080P_G146,
            movie_fps=120,
        )
        self.assertTrue(res.valid)

    def test_80_g146_apsc_on_sq_200fps_fhd_blocked(self) -> None:
        res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE327,
            apsc_s35_shooting=APSC_S35_ON_G146,
            movie_resolution=MOVIE_RES_FHD_1080P_G146,
            movie_fps=200,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE327)

    def test_81_g146_full_frame_4k_and_dci_4k_valid_when_apsc_off_or_auto_ff_lens(self) -> None:
        for res_fmt in (MOVIE_RES_4K_UHD_G146, MOVIE_RES_DCI_4K_G146):
            res = verify_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE327,
                apsc_s35_shooting=APSC_S35_AUTO_G146,
                apsc_lens_attached=False,
                movie_resolution=res_fmt,
                movie_fps=60,
            )
            self.assertTrue(res.valid, msg=res_fmt)

    def test_82_g146_silent_mode_locks_electronic_shutter_in_state_resolver(self) -> None:
        st = resolve_fx3_reclamp_varshutter_apsc_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE327,
            silent_mode="On",
            shutter_type=SHUTTER_TYPE_MECHANICAL_G146,
            anti_flicker_shoot="On",
        )
        self.assertEqual(st["effective_shutter_type"], SHUTTER_TYPE_ELECTRONIC_G146)
        self.assertEqual(st["effective_anti_flicker_shoot"], "Off")

    def test_83_g146_g145_resid16_constants_pinned(self) -> None:
        from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
            APSC_S35_F_RESID16_G146,
            DESQUEEZE_DISPLAY_F_RESID16_G145,
            DORMANT_VAR_SHUTTER_F_RESID16_G146,
            REC_LAMP_F_RESID16_G146,
            REMOVED_COLOR_GAMUT_RAW_OUT_F_RESID16_G145,
        )

        self.assertEqual(DESQUEEZE_DISPLAY_F_RESID16_G145, 0x7ABA)
        self.assertEqual(REMOVED_COLOR_GAMUT_RAW_OUT_F_RESID16_G145, 0x6BDC)
        self.assertEqual(REC_LAMP_F_RESID16_G146, 0x6E62)
        self.assertEqual(DORMANT_VAR_SHUTTER_F_RESID16_G146, 0x6831)
        self.assertEqual(APSC_S35_F_RESID16_G146, 0x6EBA)

    def test_84_g146_gate_verdict_evidence_contains_status_and_apsc_resettable_false(self) -> None:
        v, _ = evaluate_g146_reclamp_emph_remain_autoreview_and_dormant_varshutter_apsc_guard(
            force_clean_room=True
        )
        self.assertIn("apsc_resettable=False", v.evidence)

    # =========================================================================
    # Section D: Unified 146-Gate Master Preflight, Discovery & CLI (85..96)
    # =========================================================================

    def test_85_evaluate_146gate_preflight_offline_143_of_146(self) -> None:
        rep = evaluate_146gate_preflight(DEFAULT_REPO_ROOT)
        self.assertIsInstance(rep, Master146GateReport)
        self.assertEqual(rep.schema, REALHW_146GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.summary["total_gates"], 146)
        self.assertEqual(rep.summary["verified_gates"], 143)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_143_gates_verified)
        self.assertFalse(rep.all_146_gates_verified)
        self.assertTrue(rep.g13_to_g146_all_passed)
        self.assertTrue(rep.g145_to_g146_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(rep.gates), 146)

    def test_86_evaluate_146gate_preflight_dry_run_146_of_146(self) -> None:
        rep = evaluate_146gate_preflight(DEFAULT_REPO_ROOT, simulate_bench_dry_run=True)
        self.assertEqual(rep.status, "VERIFIED_ALL_146_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 146)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_146_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_87_backward_compat_evaluate_144gate_preflight_unchanged(self) -> None:
        r144 = evaluate_144gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(r144.summary["total_gates"], 144)
        self.assertEqual(r144.summary["verified_gates"], 141)
        self.assertTrue(r144.offline_141_gates_verified)

    def test_88_highest_gate_discovery_hook_finds_146(self) -> None:
        pat = re.compile(r"^evaluate_(\d+)gate_preflight$")
        nums = [
            int(m.group(1))
            for attr in dir(fx3_safety)
            for m in [pat.match(attr)]
            if m and callable(getattr(fx3_safety, attr))
        ]
        self.assertEqual(max(nums), 146)

    def test_89_aliases_evaluate_146_master_safety_gates_and_run_146_gate_preflight(self) -> None:
        r1 = evaluate_146_master_safety_gates(DEFAULT_REPO_ROOT, force_clean_room=True)
        r2 = run_146_gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True)
        self.assertTrue(r1.offline_143_gates_verified)
        self.assertTrue(r2.all_146_gates_verified)

    def test_90_request_persistent_emmc_writes_fails_closed(self) -> None:
        rep = evaluate_146gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep.all_146_gates_verified)
        self.assertFalse(rep.offline_143_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_91_fault_injection_in_g145_blocks_146gate_preflight(self) -> None:
        rep = evaluate_146gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            hdmi_raw_desqueeze_kwargs={"requested_desqueeze_1_8x": True},
        )
        self.assertFalse(rep.g145_to_g146_all_passed)
        self.assertFalse(rep.all_146_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G145_DORMANT_8BIT_24P_RAW_GAMUT_18X_OR_FX6_VIOLATION,
        )

    def test_92_fault_injection_in_g146_blocks_146gate_preflight(self) -> None:
        rep = evaluate_146gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            reclamp_varshutter_apsc_kwargs={"claimed_camset_reset_resets_apsc": True},
        )
        self.assertFalse(rep.g145_to_g146_all_passed)
        self.assertFalse(rep.all_146_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G146_APSC_RESET_ERRATA_OR_4K_STILL_CLAMP_VIOLATION,
        )

    def test_93_cli_main_verify_g145_and_g146_summary_json(self) -> None:
        for cmd in (
            "verify-hdmi-raw-desqueeze-guard",
            "verify-g145",
            "verify-reclamp-varshutter-apsc-guard",
            "verify-g146",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, msg=cmd)
            data = json.loads(buf.getvalue())
            self.assertTrue(data["valid"], msg=cmd)
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_94_cli_main_help_argparse_no_percent_formatting_crash(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        for subcmd in (
            "verify-hdmi-raw-desqueeze-guard",
            "verify-reclamp-varshutter-apsc-guard",
            "verify-146-gates",
        ):
            with self.assertRaises(SystemExit) as sctx:
                with contextlib.redirect_stdout(io.StringIO()):
                    cli_main([subcmd, "--help"])
            self.assertEqual(sctx.exception.code, 0, msg=subcmd)

    def test_95_cli_main_verify_146_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = cli_main(["verify-146-gates", "--clean-room", "--summary", "--json"])
        self.assertEqual(rc_off, 0)
        d_off = json.loads(buf_off.getvalue())
        self.assertEqual(d_off["summary"]["verified_gates"], 143)
        self.assertEqual(d_off["summary"]["total_gates"], 146)

        buf_sim = io.StringIO()
        with contextlib.redirect_stdout(buf_sim):
            rc_sim = cli_main(
                ["verify-146-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
            )
        self.assertEqual(rc_sim, 0)
        d_sim = json.loads(buf_sim.getvalue())
        self.assertEqual(d_sim["summary"]["verified_gates"], 146)
        self.assertTrue(d_sim["summary"]["all_146_gates_verified"])

    def test_96_module_main_entrypoint_g145_g146_146(self) -> None:
        for gate_arg in ("g145", "g146", "146"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", gate_arg, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, msg=gate_arg)
            parsed = json.loads(buf.getvalue())
            self.assertIsInstance(parsed, dict)


if __name__ == "__main__":
    unittest.main()
