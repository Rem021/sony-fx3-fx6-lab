"""Phase 323 (Task H388, Wave-62, 12^2 = 144/144 Gross Safety Gates Milestone!):
Dual-Mode Unit Tests (96 tests) for
`fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard`:

- Gate `G143` (`REALHW_SHOE_AUDIO_4CH_24BIT_OUT_TIMING_AND_FACE_EYE_SUBJECT_DORMANT_BIRD_GUARD`):
  - `Shooting -> [Audio Recording] -> [Audio Out Timing]` (`Live` default / `Lip Sync`, disabled in
    `S&Q`, **NOT** under `Setup -> [Sound Option]`), removed standalone `[Audio Level Display]`
    (`_f 0x7a36`), `[Audio Rec Level]` (`0..31`, default `26`, `Delete`-key reset, always-on
    non-disableable Limiter vs FX6 6-step Limiter), `[Shoe Audio Set.]` (`48kHz/24bit 4ch`,
    `48kHz/24bit 2ch`, `48kHz/16bit 2ch` across ALL main codecs vs `AAC-LC 2ch 128kbps` Proxy &
    `>= 100p` Proxy lockout), `3.5mm MIC` override (`EBUSY=16`), `XLR-H1` `HANDLE AUDIO=OFF`
    fallback & `ANALOG` `16bit 2ch` cap, built-in-only `[Wind Noise Reduct.]`, `5`-mode
    `[4ch Audio Monitoring]`, and `Slot 1` `EROFS=30` firewall.
  - `Focus -> [Face/Eye AF]` + Wave-42 dormant `Bird` errata: `[Face/Eye Subject]` exposes ONLY
    `Human` (default) & `Animal`, failing closed `EOPNOTSUPP=95` on ALL 5 dormant subjects
    (`Bird`, `Animal/Bird`, `Insect`, `Car/Train`, `Airplane`); `Animal` Eye AF Still-only
    (`TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`); `[Face/Eye Frame Disp.]` (`Off` default, Clean
    HDMI suppressed); `8`-face `[Face Memory]` reset-persistence & `CAMSET*.DAT` exclusion vs FX6.
- Gate `G144` (`REALHW_SILENT_TARGET_2ITEM_NO_PWR_SHUTTER_AND_SLOT1_BODYDATA_NOGO_FLASH_GUARD`):
  - `Shooting -> [Shutter/Silent] -> [Silent Mode Settings]` (`Off`/`On`) locks Electronic Shutter,
    mutes `[Audio signals]`, hard-disables exact 5 functions (`Flash`, `Long Exposure NR`,
    `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`; `[AF Illuminator]` NOT auto-disabled),
    and exposes ONLY 2 active `[Target Function Settings]` items (`[Aperture Drive in AF]` Still-only,
    `[Auto Pixel Mapping]` `Off` default).
  - Fail-closed `EOPNOTSUPP=95` on dormant `[Shutter When Pwr OFF]` (`_f 0x709f`,
    `image_sensor_barrier`) & `[Anti-dust Function]` (`0x7495`), and shutterless `ILME-FX6`
    (`Auto Pixel Restore`).
  - Zero-RF `Airplane Mode=On` silences `_g 0x6516` update badge; `BODYDATA.DAT` policy (`FX3`
    `Slot 1`, `NP-FZ100 >= 51%`, `<= Ver. 2.02` mandatory `Ver. 2.04/2.05` stepping-stone vs
    `FX6` `Slot B` + mandatory `AC Adaptor`), plus HARD `NO-GO` Physical Flash Firewall (`EROFS=30` /
    `EPERM=1`, `slot1_data_sector_writes == 0`, `emmc_writes_authorized == False`,
    `cross_model_flash_authorized == False`, `hardware_live_attachment_authorized == False`).
- Unified `144`-Gate (`12^2` Gross Milestone) Master Safety Preflight (`evaluate_144gate_preflight` /
  `verify-144-gates`): `schema_version == "realhw_144gate_preflight_v1"`, `141/144` offline,
  `144/144` `--simulate-bench-dry-run`, `raw_firmware_bytes_leaked == 0`, simulated donorless Ubuntu
  CI (`_iter_work_roots=()`) covering BOTH Phase 323 & Phase 313 `audit_phase313_donor_contracts`.
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
from fx3_safety.realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
    audit_phase313_donor_contracts,
)
from fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    ALLOWED_4CH_AUDIO_MONITORING_MODES_G143,
    ALLOWED_AUDIO_OUT_TIMING_MODES_G143,
    ALLOWED_FX3_FACE_EYE_SUBJECTS_G143,
    ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143,
    ALLOWED_MAIN_MOVIE_CODECS_G143,
    ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144,
    ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144,
    AUDIO_OUT_TIMING_DEFAULT_G143,
    AUDIO_OUT_TIMING_LIP_SYNC_G143,
    AUDIO_OUT_TIMING_LIVE_G143,
    AUDIO_OUT_TIMING_MENU_PATH_G143,
    AUDIO_REC_LEVEL_DEFAULT_G143,
    AUDIO_REC_LEVEL_MAX_G143,
    AUDIO_REC_LEVEL_MIN_G143,
    BODYDATA_FILENAME_G144,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE323,
    DONOR_CHECK_MAX_SECONDS_PHASE323,
    DORMANT_SHARED_FACE_EYE_SUBJECTS_G143,
    EBUSY_ERRNO_PHASE323,
    EINVAL_ERRNO_PHASE323,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE323,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE323,
    EPERM_ERRNO_PHASE323,
    EROFS_ERRNO_PHASE323,
    EXACT_2_TARGET_FUNCTION_ITEMS_G144,
    EXACT_5_SILENT_DISABLED_FUNCTIONS_G144,
    FACE_MEMORY_MAX_FACES_G143,
    FACE_SUBJECT_ANIMAL_G143,
    FACE_SUBJECT_HUMAN_G143,
    FX3_BODYDATA_MIN_BATTERY_BARS_G144,
    FX3_BODYDATA_MIN_BATTERY_PCT_G144,
    FX3_BODYDATA_REQUIRED_SLOT_G144,
    FX3_MODEL_ID_PHASE323,
    FX3_MODEL_NAME_PHASE323,
    FX3_UPDATE_BLINK_PROGRESS_G144,
    FX3_UPDATE_ERROR_BLINK_CODES_G144,
    FX6_BODYDATA_MIN_POWER_G144,
    FX6_BODYDATA_REQUIRED_SLOT_G144,
    FX6_MODEL_NAME_PHASE323,
    G143,
    G143_GATE_CODE,
    G144,
    G144_GATE_CODE,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MEDIA_SLOT_1_PHASE323,
    MEDIA_SLOT_2_PHASE323,
    Master144GateReport,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE323_DONOR_SPECS,
    PROXY_FORCED_AUDIO_CODEC_G143,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_144GATE_PREFLIGHT_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
    RESET_ACTION_INITIALIZE_PHASE323,
    SHOE_AUDIO_48KHZ_16BIT_2CH_G143,
    SHOE_AUDIO_48KHZ_24BIT_2CH_G143,
    SHOE_AUDIO_48KHZ_24BIT_4CH_G143,
    SHOE_AUDIO_DEFAULT_G143,
    SHOOT_MODE_MOVIE_PHASE323,
    SHOOT_MODE_SQ_PHASE323,
    SHOOT_MODE_STILL_PHASE323,
    SOUND_OPTION_MENU_PATH_G143,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION,
    STATUS_BLOCKED_G143_AUDIO_ROUTING_LEVEL_OR_CODEC_VIOLATION,
    STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
    STATUS_BLOCKED_G143_TELEMETRY_INVALID,
    STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION,
    STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION,
    STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL,
    STATUS_BLOCKED_G144_TELEMETRY_INVALID,
    STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION,
    STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_G143,
    STATUS_VERIFIED_G144,
    USB_PACKETS_TRANSMITTED,
    XLR_H1_DIGITAL_ANALOG_ANALOG_G143,
    XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
    audit_phase323_donor_contracts,
    compute_shoe_audio_4ch_subject_recog_matrix,
    compute_silent_target_bodydata_matrix,
    evaluate_144_master_safety_gates,
    evaluate_144gate_preflight,
    evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard,
    evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard,
    main as module_main,
    resolve_fx3_shoe_audio_4ch_subject_recog_state,
    resolve_fx3_silent_target_bodydata_state,
    run_144_gate_preflight,
    validate_fx3_vs_fx6_bodydata_policy,
    verify_shoe_audio_4ch_out_timing_and_subject_recog_guard,
    verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard,
)


class TestPhase323Milestone144Gates(unittest.TestCase):
    # =========================================================================
    # Section A: Exports, Redlines & Dual-Mode / Donorless CI Audit (01..18)
    # =========================================================================

    def test_01_public_exports_present_in_package_and_all(self) -> None:
        required = (
            "G143",
            "G144",
            "Master144GateReport",
            "evaluate_144gate_preflight",
            "evaluate_144_master_safety_gates",
            "run_144_gate_preflight",
            "evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard",
            "evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard",
            "verify_shoe_audio_4ch_out_timing_and_subject_recog_guard",
            "verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard",
            "audit_phase323_donor_contracts",
            "realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard",
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
        audit = audit_phase323_donor_contracts(force_clean_room=True)
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
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE323):
            with mock.patch.dict(os.environ, {env_key: "1"}, clear=False):
                audit = audit_phase323_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_local_or_clean_room_budget_and_digests(self) -> None:
        audit = audit_phase323_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid, msg=f"errors={audit.errors}")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE323)
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE323_DONOR_SPECS))
            self.assertEqual(audit.files_inspected, 15)
            self.assertTrue(audit.within_budget_200ms)
            self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE323)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")
            self.assertEqual(len(audit.file_digests), 15)

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        audit = audit_phase323_donor_contracts(
            work_root=Path("/nonexistent/phase323/donor/root"),
            force_clean_room=False,
        )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_simulated_donorless_ubuntu_ci_iter_work_roots_empty_phase323(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE323, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                audit = audit_phase323_donor_contracts(force_clean_room=False)
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

                verdict_143, res_143 = (
                    evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                        force_clean_room=False
                    )
                )
                self.assertTrue(verdict_143.passed)
                self.assertTrue(res_143.valid)
                self.assertEqual(res_143.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                verdict_144, res_144 = (
                    evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
                        force_clean_room=False
                    )
                )
                self.assertTrue(verdict_144.passed)
                self.assertTrue(res_144.valid)
                self.assertEqual(res_144.verification_mode, "CLEAN_ROOM_SYNTHETIC")

                rep = evaluate_144gate_preflight(force_clean_room=False)
                self.assertTrue(rep.offline_141_gates_verified)
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_08_simulated_donorless_ubuntu_ci_phase313_defensive_none_guard(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE323, None)
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard._iter_work_roots",
                return_value=(),
            ):
                audit_313 = audit_phase313_donor_contracts(force_clean_room=False)
                self.assertTrue(audit_313.valid)
                self.assertEqual(audit_313.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit_313.raw_firmware_bytes_leaked, 0)

    def test_09_donor_audit_override_detects_missing_file_fail_closed(self) -> None:
        bad_specs = {
            "missing_blob": (
                "fx3",
                "does/not/exist/file.bin",
                123,
                "0" * 64,
                (b"x",),
                "missing",
            )
        }
        audit = audit_phase323_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY)
        self.assertIn("missing_blob:file_missing", audit.missing_markers)

    def test_10_donor_audit_override_detects_size_and_sha_mismatch(self) -> None:
        target_rel = "outputs/fx3-safety/pyproject.toml"
        if not (DEFAULT_REPO_ROOT / target_rel).is_file():
            target_rel = "outputs/fx3-safety/README.md"
        bad_specs = {
            "tampered": (
                "fx3",
                target_rel,
                1,
                "f" * 64,
                (b"fx3-safety",),
                "tamper test",
            )
        }
        audit = audit_phase323_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY)
        self.assertTrue(any("size_mismatch" in m for m in audit.missing_markers))
        self.assertTrue(any("sha256_mismatch" in m for m in audit.missing_markers))

    def test_11_donor_audit_override_detects_missing_token(self) -> None:
        readme_path = DEFAULT_REPO_ROOT / "outputs/fx3-safety/README.md"
        raw = readme_path.read_bytes()
        import hashlib

        bad_specs = {
            "tok": (
                "fx3",
                "outputs/fx3-safety/README.md",
                len(raw),
                hashlib.sha256(raw).hexdigest(),
                (b"__NONEXISTENT_PHASE323_SENTINEL__",),
                "missing token",
            )
        }
        audit = audit_phase323_donor_contracts(
            work_root=DEFAULT_REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_specs,
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE323_DONOR_INTEGRITY)
        self.assertTrue(any("token_missing" in m for m in audit.missing_markers))

    def test_12_donor_audit_missing_directory_clean_room_fallback(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE323, None)
            audit = audit_phase323_donor_contracts(
                work_root=DEFAULT_REPO_ROOT / "nonexistent_dir_phase323"
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_13_pinned_donor_specs_include_both_fx3_and_fx6(self) -> None:
        families = {spec[0] for spec in PINNED_PHASE323_DONOR_SPECS.values()}
        self.assertEqual(families, {"FX3", "FX6"})
        self.assertIn("fx3_appfw_so", PINNED_PHASE323_DONOR_SPECS)
        self.assertIn("fx6_appfw_so", PINNED_PHASE323_DONOR_SPECS)
        self.assertIn("fx3_p1_205_nflasha1", PINNED_PHASE323_DONOR_SPECS)
        self.assertIn("fx6_avbb_scn_start_audio_so", PINNED_PHASE323_DONOR_SPECS)
        self.assertIn("fx6_libinfrahotshoe_so", PINNED_PHASE323_DONOR_SPECS)

    def test_14_g143_schema_and_gate_constants(self) -> None:
        self.assertEqual(G143, "G143")
        self.assertEqual(
            G143_GATE_CODE,
            "REALHW_SHOE_AUDIO_4CH_24BIT_OUT_TIMING_AND_FACE_EYE_SUBJECT_DORMANT_BIRD_GUARD",
        )
        self.assertEqual(AUDIO_OUT_TIMING_MENU_PATH_G143, "Shooting -> [Audio Recording] -> [Audio Out Timing]")
        self.assertEqual(SOUND_OPTION_MENU_PATH_G143, "Setup -> [Sound Option]")

    def test_15_g144_schema_and_gate_constants(self) -> None:
        self.assertEqual(G144, "G144")
        self.assertEqual(
            G144_GATE_CODE,
            "REALHW_SILENT_TARGET_2ITEM_NO_PWR_SHUTTER_AND_SLOT1_BODYDATA_NOGO_FLASH_GUARD",
        )
        self.assertEqual(REALHW_144GATE_PREFLIGHT_SCHEMA, "realhw_144gate_preflight_v1")

    def test_16_donor_audit_to_dict_serializable_no_raw_bytes(self) -> None:
        audit = audit_phase323_donor_contracts(force_clean_room=True)
        d = audit.to_dict()
        encoded = json.dumps(d)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", encoded)
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_17_evaluate_144_with_explicit_clean_room_true(self) -> None:
        rep = evaluate_144gate_preflight(force_clean_room=True, dry_run_simulated=True)
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_144_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 144)

    def test_18_strict_o_rdonly_audit_has_zero_usb_or_emmc_effects(self) -> None:
        audit = audit_phase323_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertFalse(EMMC_WRITES_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)

    # =========================================================================
    # Section B: Gate G143 — Audio Routing, 4ch 24-bit & Subject Recog (19..50)
    # =========================================================================

    def test_19_g143_default_nominal_passes(self) -> None:
        res = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G143)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.effective_audio_out_timing, AUDIO_OUT_TIMING_LIVE_G143)
        self.assertEqual(res.effective_audio_rec_level, 26)
        self.assertEqual(res.effective_shoe_audio_set, SHOE_AUDIO_48KHZ_16BIT_2CH_G143)
        self.assertTrue(res.audio_level_display_standalone_menu_removed)
        self.assertTrue(res.audio_limiter_always_on_fx3)
        self.assertEqual(res.effective_face_eye_subject, FACE_SUBJECT_HUMAN_G143)

    def test_20_g143_audio_out_timing_live_and_lip_sync_valid_and_sound_option_rejected(
        self,
    ) -> None:
        for mode in ALLOWED_AUDIO_OUT_TIMING_MODES_G143:
            res = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_audio_out_timing=mode
            )
            self.assertTrue(res.valid, msg=f"mode={mode} errors={res.errors}")
            self.assertEqual(res.effective_audio_out_timing, mode)
            self.assertEqual(res.audio_out_timing_menu_path, AUDIO_OUT_TIMING_MENU_PATH_G143)

        bad_path = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_audio_out_timing_in_sound_option=True
        )
        self.assertFalse(bad_path.valid)
        self.assertEqual(
            bad_path.status,
            STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION,
        )
        self.assertEqual(bad_path.block_errno, EINVAL_ERRNO_PHASE323)

    def test_21_g143_audio_out_timing_and_audio_recording_blocked_in_sq(self) -> None:
        sq_timing = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE323,
            requested_audio_out_timing_in_sq=True,
        )
        self.assertFalse(sq_timing.valid)
        self.assertEqual(sq_timing.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

        sq_rec = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE323,
            requested_audio_recording_in_sq=True,
        )
        self.assertFalse(sq_rec.valid)
        self.assertEqual(sq_rec.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

        sq_nominal = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE323
        )
        self.assertTrue(sq_nominal.valid)
        self.assertEqual(sq_nominal.effective_audio_recording, "Off")

    def test_22_g143_removed_standalone_audio_level_display_menu_rejected(self) -> None:
        bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_standalone_audio_level_display_menu=True
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G143_AUDIO_MENU_PATH_OR_REMOVED_DISPLAY_VIOLATION,
        )
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_23_g143_audio_rec_level_bounds_and_delete_key_reset(self) -> None:
        self.assertEqual(AUDIO_REC_LEVEL_MIN_G143, 0)
        self.assertEqual(AUDIO_REC_LEVEL_MAX_G143, 31)
        self.assertEqual(AUDIO_REC_LEVEL_DEFAULT_G143, 26)

        for lvl in (0, 15, 26, 31):
            ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_audio_rec_level=lvl
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_audio_rec_level, lvl)

        rst = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_audio_rec_level=5,
            delete_key_reset_rec_level=True,
        )
        self.assertTrue(rst.valid)
        self.assertEqual(rst.effective_audio_rec_level, 26)

        for bad_lvl in (-1, 32, True):
            bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_audio_rec_level=bad_lvl  # type: ignore[arg-type]
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_24_g143_always_on_limiter_cannot_be_disabled_and_fx6_6step_rejected(
        self,
    ) -> None:
        dis = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_fx3_disable_audio_limiter=True
        )
        self.assertFalse(dis.valid)
        self.assertEqual(dis.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

        fx6_lim = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_fx6_limiter_mode_steps=True
        )
        self.assertFalse(fx6_lim.valid)
        self.assertEqual(fx6_lim.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_25_g143_shoe_audio_all_3_formats_across_all_6_main_codecs(self) -> None:
        self.assertEqual(len(ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143), 3)
        self.assertEqual(len(ALLOWED_MAIN_MOVIE_CODECS_G143), 6)
        for codec in ALLOWED_MAIN_MOVIE_CODECS_G143:
            for fmt in ALLOWED_FX3_SHOE_AUDIO_FORMATS_G143:
                ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                    main_movie_codec=codec,
                    requested_shoe_audio_set=fmt,
                )
                self.assertTrue(ok.valid, msg=f"codec={codec} fmt={fmt} failed")
                self.assertEqual(ok.effective_shoe_audio_set, fmt)
                self.assertEqual(ok.effective_proxy_audio_codec, PROXY_FORCED_AUDIO_CODEC_G143)

    def test_26_g143_32bit_float_shoe_audio_and_invalid_codec_rejected(self) -> None:
        f32 = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_32bit_float_shoe_audio=True
        )
        self.assertFalse(f32.valid)
        self.assertEqual(f32.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

        bad_fmt = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_shoe_audio_set="48kHz/32bit 4ch"
        )
        self.assertFalse(bad_fmt.valid)
        self.assertEqual(bad_fmt.block_errno, EINVAL_ERRNO_PHASE323)

        bad_codec = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            main_movie_codec="ProRes RAW HQ"
        )
        self.assertFalse(bad_codec.valid)
        self.assertEqual(bad_codec.block_errno, EINVAL_ERRNO_PHASE323)

    def test_27_g143_proxy_aac_lc_only_and_locked_at_100p_120p(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            rec_frame_rate="59.94p",
            proxy_recording_enabled=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.proxy_allowed)
        self.assertEqual(ok.effective_proxy_audio_codec, PROXY_FORCED_AUDIO_CODEC_G143)

        lpcm_bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            proxy_recording_enabled=True,
            requested_proxy_4ch_lpcm=True,
        )
        self.assertFalse(lpcm_bad.valid)
        self.assertEqual(lpcm_bad.block_errno, EINVAL_ERRNO_PHASE323)

        for fps in ("100p", "119.88p", "120p", "240p"):
            hi_bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                rec_frame_rate=fps,
                proxy_recording_enabled=True,
            )
            self.assertFalse(hi_bad.valid)
            self.assertFalse(hi_bad.proxy_allowed)
            self.assertEqual(hi_bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_28_g143_35mm_mic_jack_overrides_digital_mi_shoe_and_blocks_4ch(self) -> None:
        ok_35 = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            mic_35mm_plugged=True,
            xlr_h1_attached=True,
            requested_shoe_audio_set=SHOE_AUDIO_48KHZ_24BIT_4CH_G143,
        )
        self.assertTrue(ok_35.valid)
        self.assertEqual(ok_35.effective_audio_source, "3.5mm MIC (2ch Analog Override)")
        self.assertEqual(ok_35.effective_shoe_audio_set, SHOE_AUDIO_48KHZ_16BIT_2CH_G143)

        bad_4ch = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            mic_35mm_plugged=True,
            requested_4ch_over_35mm_mic=True,
        )
        self.assertFalse(bad_4ch.valid)
        self.assertEqual(bad_4ch.block_errno, EBUSY_ERRNO_PHASE323)

    def test_29_g143_xlr_h1_handle_off_fallback_and_analog_16bit_cap(self) -> None:
        off_res = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="OFF",
        )
        self.assertTrue(off_res.valid)
        self.assertEqual(off_res.effective_audio_source, "Internal Stereo Mic")

        analog_ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_digital_analog=XLR_H1_DIGITAL_ANALOG_ANALOG_G143,
        )
        self.assertTrue(analog_ok.valid)
        self.assertEqual(analog_ok.effective_shoe_audio_set, SHOE_AUDIO_48KHZ_16BIT_2CH_G143)

        analog_24_bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_digital_analog=XLR_H1_DIGITAL_ANALOG_ANALOG_G143,
            requested_24bit_under_xlrh1_analog=True,
        )
        self.assertFalse(analog_24_bad.valid)
        self.assertEqual(analog_24_bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_30_g143_wind_noise_reduct_internal_mic_only(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=False,
            requested_wind_noise_reduct="On",
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_wind_noise_reduct, "On")
        self.assertEqual(ok.effective_audio_source, "Internal Stereo Mic")

        bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=True,
            requested_wind_noise_reduct="On",
            requested_wind_noise_reduct_on_external_mic=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_31_g143_4ch_audio_monitoring_5_modes(self) -> None:
        self.assertEqual(len(ALLOWED_4CH_AUDIO_MONITORING_MODES_G143), 5)
        for m in ALLOWED_4CH_AUDIO_MONITORING_MODES_G143:
            ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_4ch_audio_monitoring=m
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_4ch_audio_monitoring, m)

        bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_4ch_audio_monitoring="CH1_ONLY"
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_32_g143_slot1_tier0_audio_config_write_blocked_erofs(self) -> None:
        bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            slot_1_contains_tier0_vault=True,
            slot1_audio_config_write_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE323)
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_33_g143_face_eye_subject_only_human_and_animal(self) -> None:
        self.assertEqual(ALLOWED_FX3_FACE_EYE_SUBJECTS_G143, ("Human", "Animal"))
        ok_h = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE323,
            requested_face_eye_subject=FACE_SUBJECT_HUMAN_G143,
        )
        self.assertTrue(ok_h.valid)
        self.assertEqual(ok_h.effective_face_eye_subject, "Human")

        ok_a_still = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE323,
            requested_face_eye_subject=FACE_SUBJECT_ANIMAL_G143,
        )
        self.assertTrue(ok_a_still.valid)
        self.assertTrue(ok_a_still.animal_eye_af_active_in_mode)

    def test_34_g143_all_5_dormant_subjects_and_wave42_bird_errata_rejected_eopnotsupp(
        self,
    ) -> None:
        self.assertEqual(
            DORMANT_SHARED_FACE_EYE_SUBJECTS_G143,
            ("Bird", "Animal/Bird", "Insect", "Car/Train", "Airplane"),
        )
        for subj in DORMANT_SHARED_FACE_EYE_SUBJECTS_G143:
            bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_face_eye_subject=subj
            )
            self.assertFalse(bad.valid, msg=f"dormant subject {subj} must fail")
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
            )
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

        errata = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_wave42_bird_errata_claim=True
        )
        self.assertFalse(errata.valid)
        self.assertEqual(errata.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_35_g143_animal_eye_af_still_only_blocked_in_movie_and_sq(self) -> None:
        for mode in (SHOOT_MODE_MOVIE_PHASE323, SHOOT_MODE_SQ_PHASE323):
            bad_movie = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                shoot_mode=mode,
                requested_face_eye_subject=FACE_SUBJECT_ANIMAL_G143,
            )
            self.assertFalse(bad_movie.valid)
            self.assertFalse(bad_movie.animal_eye_af_active_in_mode)
            self.assertEqual(bad_movie.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

            bad_active = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                shoot_mode=mode,
                requested_face_eye_subject=FACE_SUBJECT_ANIMAL_G143,
                requested_animal_eye_af_in_movie=True,
            )
            self.assertFalse(bad_active.valid)
            self.assertEqual(bad_active.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_36_g143_face_eye_frame_disp_and_clean_hdmi_suppression(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_face_eye_frame_disp="On"
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_face_eye_frame_disp, "On")
        self.assertTrue(ok.clean_hdmi_face_frame_suppressed)

        bad_hdmi = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_face_frame_over_clean_hdmi=True
        )
        self.assertFalse(bad_hdmi.valid)
        self.assertEqual(bad_hdmi.block_errno, EINVAL_ERRNO_PHASE323)

    def test_37_g143_face_memory_8_faces_survives_cam_reset_wipes_on_init(self) -> None:
        self.assertEqual(FACE_MEMORY_MAX_FACES_G143, 8)
        cam_rst = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
            face_memory_count=8,
            requested_face_eye_subject=FACE_SUBJECT_ANIMAL_G143,
            requested_face_eye_frame_disp="On",
            requested_audio_rec_level=10,
            requested_shoe_audio_set=SHOE_AUDIO_48KHZ_24BIT_4CH_G143,
            requested_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G143,
        )
        self.assertTrue(cam_rst.valid)
        self.assertEqual(cam_rst.effective_face_memory_count, 8)
        self.assertTrue(cam_rst.face_memory_survived_cam_reset)
        self.assertTrue(cam_rst.face_memory_excluded_from_camset)
        self.assertEqual(cam_rst.effective_face_eye_subject, "Human")
        self.assertEqual(cam_rst.effective_face_eye_frame_disp, "Off")
        self.assertEqual(cam_rst.effective_audio_rec_level, 26)
        self.assertEqual(cam_rst.effective_shoe_audio_set, SHOE_AUDIO_48KHZ_16BIT_2CH_G143)
        self.assertEqual(cam_rst.effective_audio_out_timing, AUDIO_OUT_TIMING_LIVE_G143)

        init_rst = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE323,
            face_memory_count=8,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_face_memory_count, 0)
        self.assertFalse(init_rst.face_memory_survived_cam_reset)

    def test_38_g143_face_memory_camset_export_and_count_bounds_rejected(self) -> None:
        exp_bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            requested_camset_export_face_memory=True
        )
        self.assertFalse(exp_bad.valid)
        self.assertEqual(
            exp_bad.status, STATUS_BLOCKED_G143_FACE_MEMORY_OR_FX6_CROSSWIRE_VIOLATION
        )
        self.assertEqual(exp_bad.block_errno, EINVAL_ERRNO_PHASE323)

        for bad_cnt in (-1, 9, True):
            cnt_bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                face_memory_count=bad_cnt  # type: ignore[arg-type]
            )
            self.assertFalse(cnt_bad.valid)
            self.assertEqual(cnt_bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_39_g143_fx6_crosswire_subject_and_face_memory_rejected(self) -> None:
        for kw in (
            {"requested_fx6_non_human_subject": True},
            {"requested_fx6_persistent_face_memory": True},
        ):
            bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_40_g143_matrix_exact_792_states(self) -> None:
        mat = compute_shoe_audio_4ch_subject_recog_matrix()
        self.assertEqual(mat["audio_states_checked"], 720)
        self.assertEqual(mat["subject_states_checked"], 72)
        self.assertEqual(mat["total_matrix_states"], 792)
        self.assertEqual(mat["dormant_subjects_tested"], 5)

    def test_41_g143_invalid_identity_and_enum_telemetry_blocked(self) -> None:
        for kw in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 999999},
            {"help_guide_code": "H0000"},
            {"shoot_mode": "Timelapse"},
            {"reset_action": "Wipe"},
            {"requested_audio_recording": "Maybe"},
            {"requested_audio_out_timing": "Auto"},
            {"requested_right_left_eye_select": "Center"},
            {"requested_face_eye_subject": "Alien"},
            {"requested_wind_noise_reduct": "Max"},
        ):
            bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(**kw)
            self.assertFalse(bad.valid, msg=f"kw={kw} should fail")
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_42_g143_invalid_xlr_handle_and_digital_analog_switch(self) -> None:
        for kw in (
            {"xlr_h1_handle_audio": "AUTO"},
            {"xlr_h1_digital_analog": "OPTICAL"},
            {"requested_regist_faces_priority": "Auto"},
            {"requested_face_eye_prior_in_af": "Auto"},
            {"requested_face_eye_frame_disp": "Auto"},
        ):
            bad = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(**kw)
            self.assertFalse(bad.valid, msg=f"kw={kw} should fail")
            self.assertEqual(bad.status, STATUS_BLOCKED_G143_TELEMETRY_INVALID)

    def test_43_g143_right_left_eye_select_all_modes_valid(self) -> None:
        for mode in ("Auto", "Right Eye", "Left Eye"):
            ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
                requested_right_left_eye_select=mode
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_right_left_eye_select, mode)

    def test_44_g143_delete_all_face_memory_zeros_count(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            face_memory_count=6,
            face_memory_delete_all=True,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_face_memory_count, 0)

    def test_45_g143_resolve_helper_and_digital_24bit_4ch(self) -> None:
        st = resolve_fx3_shoe_audio_4ch_subject_recog_state(
            xlr_h1_attached=True,
            xlr_h1_handle_audio="ON",
            xlr_h1_digital_analog=XLR_H1_DIGITAL_ANALOG_DIGITAL_G143,
            requested_shoe_audio_set=SHOE_AUDIO_48KHZ_24BIT_4CH_G143,
            requested_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G143,
        )
        self.assertTrue(st["valid"])
        self.assertEqual(st["effective_shoe_audio_set"], SHOE_AUDIO_48KHZ_24BIT_4CH_G143)
        self.assertEqual(st["effective_audio_out_timing"], AUDIO_OUT_TIMING_LIP_SYNC_G143)
        self.assertEqual(st["effective_audio_source"], "Digital MI Shoe (XLR-H1)")

    def test_46_g143_evaluate_wrapper_returns_verdict_and_result(self) -> None:
        v, r = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            force_clean_room=True
        )
        self.assertEqual(v.gate_id, G143)
        self.assertEqual(v.gate_code, G143_GATE_CODE)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(r.status, STATUS_VERIFIED_G143)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_47_g143_evaluate_wrapper_propagates_fault_to_verdict(self) -> None:
        v, r = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            force_clean_room=True,
            requested_face_eye_subject="Bird",
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
        )

    def test_48_g143_proxy_codec_is_aac_lc_across_24p_59_94p_with_24bit_2ch(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            main_movie_codec="XAVC HS 4K",
            rec_frame_rate="23.98p",
            proxy_recording_enabled=True,
            requested_shoe_audio_set=SHOE_AUDIO_48KHZ_24BIT_2CH_G143,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_shoe_audio_set, SHOE_AUDIO_48KHZ_24BIT_2CH_G143)
        self.assertEqual(ok.effective_proxy_audio_codec, PROXY_FORCED_AUDIO_CODEC_G143)

    def test_49_g143_builtin_mic_when_no_xlr_no_35mm(self) -> None:
        ok = verify_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            xlr_h1_attached=False,
            mic_35mm_plugged=False,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_audio_source, "Internal Stereo Mic")

    def test_50_g143_result_dataclass_roundtrip_no_raw_bytes(self) -> None:
        _, r = evaluate_g143_shoe_audio_4ch_out_timing_and_subject_recog_guard(
            force_clean_room=True
        )
        encoded = json.dumps(r.to_dict())
        self.assertIn(G143_GATE_CODE, encoded)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.cross_model_flash_authorized)

    # =========================================================================
    # Section C: Gate G144 — Silent Mode, 2-Item Target & BODYDATA NO-GO (51..80)
    # =========================================================================

    def test_51_g144_default_nominal_passes(self) -> None:
        res = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G144)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.target_function_exact_2_items, EXACT_2_TARGET_FUNCTION_ITEMS_G144)
        self.assertEqual(len(res.target_function_exact_2_items), 2)
        self.assertTrue(res.dormant_shutter_when_pwr_off_blocked)
        self.assertFalse(res.power_off_mechanical_shutter_actuation)
        self.assertEqual(res.fx3_bodydata_required_slot, 1)
        self.assertEqual(res.fx6_bodydata_required_slot, "Slot B")
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertFalse(res.hardware_live_attachment_authorized)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_52_g144_silent_mode_on_locks_electronic_shutter_mutes_signals_disables_5(
        self,
    ) -> None:
        res = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_silent_mode="On",
            requested_shutter_type="Mechanical",
            requested_audio_signals="On",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_silent_mode, "On")
        self.assertEqual(res.effective_shutter_type, "Electronic Shutter")
        self.assertEqual(res.effective_audio_signals, "Off")
        self.assertEqual(
            res.disabled_5_functions_enforced, EXACT_5_SILENT_DISABLED_FUNCTIONS_G144
        )
        self.assertEqual(len(res.disabled_5_functions_enforced), 5)
        self.assertFalse(res.af_illuminator_auto_disabled_by_silent)

    def test_53_g144_silent_mode_override_on_each_of_5_disabled_funcs_blocked_ebusy(
        self,
    ) -> None:
        for fn in EXACT_5_SILENT_DISABLED_FUNCTIONS_G144:
            bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
                requested_silent_mode="On",
                requested_silent_disabled_func_override=fn,
            )
            self.assertFalse(bad.valid, msg=f"fn={fn} override must fail")
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G144_SILENT_MODE_OR_TARGET_2ITEM_VIOLATION
            )
            self.assertEqual(bad.block_errno, EBUSY_ERRNO_PHASE323)

    def test_54_g144_af_illuminator_not_auto_disabled_by_silent_mode(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_silent_mode="On",
            requested_af_illuminator_auto_disabled_by_silent=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_55_g144_target_function_exact_2_items_and_extra_item_rejected_eopnotsupp(
        self,
    ) -> None:
        for ap in ALLOWED_TARGET_APERTURE_DRIVE_MODES_G144:
            for pix in ALLOWED_TARGET_AUTO_PIXEL_MAPPING_MODES_G144:
                ok = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
                    shoot_mode=SHOOT_MODE_STILL_PHASE323,
                    requested_aperture_drive_in_af=ap,
                    requested_auto_pixel_mapping=pix,
                )
                self.assertTrue(ok.valid)
                self.assertEqual(ok.effective_aperture_drive_in_af, ap)
                self.assertEqual(ok.effective_auto_pixel_mapping, pix)
                self.assertEqual(
                    ok.power_off_mechanical_shutter_actuation, pix != "Off"
                )

        extra = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_target_function_extra_item="Shutter When Pwr OFF"
        )
        self.assertFalse(extra.valid)
        self.assertEqual(extra.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_56_g144_aperture_drive_still_only_annotated_in_movie_and_sq(self) -> None:
        for mode in (SHOOT_MODE_MOVIE_PHASE323, SHOOT_MODE_SQ_PHASE323):
            res = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
                shoot_mode=mode,
                requested_aperture_drive_in_af="Silent Priority",
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_aperture_drive_in_af, "Silent Priority(Still-Only)")

    def test_57_g144_dormant_shutter_when_pwr_off_and_anti_dust_rejected_eopnotsupp(
        self,
    ) -> None:
        for kw in (
            {"requested_shutter_when_pwr_off": True},
            {"requested_anti_dust_function": True},
        ):
            bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G144_DORMANT_PWR_OFF_SHUTTER_OR_FX6_VIOLATION
            )
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_58_g144_fx6_shutterless_silent_mode_or_pwr_shutter_rejected_eopnotsupp(
        self,
    ) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_fx6_silent_mode_or_pwr_shutter=True
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE323)

    def test_59_g144_airplane_mode_zero_rf_silences_update_badge(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            airplane_mode="On",
            network_update_badge_emitted=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status, STATUS_BLOCKED_G144_VERSION_STEPPING_STONE_OR_BADGE_VIOLATION
        )
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_60_g144_fx3_vs_fx6_bodydata_policy_slot1_vs_slotb_ac_adaptor(self) -> None:
        self.assertEqual(BODYDATA_FILENAME_G144, "BODYDATA.DAT")
        self.assertEqual(FX3_BODYDATA_REQUIRED_SLOT_G144, 1)
        self.assertEqual(FX3_BODYDATA_MIN_BATTERY_PCT_G144, 51)
        self.assertEqual(FX3_BODYDATA_MIN_BATTERY_BARS_G144, 3)
        self.assertEqual(FX6_BODYDATA_REQUIRED_SLOT_G144, "Slot B")
        self.assertEqual(FX6_BODYDATA_MIN_POWER_G144, "AC Adaptor")

        ok_fx3 = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX3_MODEL_NAME_PHASE323,
            current_fw_version="6.01",
            target_fw_version="7.02",
            media_slot=1,
            battery_soc_pct=51,
        )
        self.assertTrue(ok_fx3[0])

        bad_fx3_slot2 = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX3_MODEL_NAME_PHASE323,
            media_slot=2,
            battery_soc_pct=90,
        )
        self.assertFalse(bad_fx3_slot2[0])

        bad_fx3_batt = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX3_MODEL_NAME_PHASE323,
            media_slot=1,
            battery_soc_pct=50,
        )
        self.assertFalse(bad_fx3_batt[0])

        ok_fx6 = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX6_MODEL_NAME_PHASE323,
            media_slot="Slot B",
            ac_adaptor_connected=True,
        )
        self.assertTrue(ok_fx6[0])

        bad_fx6_slota = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX6_MODEL_NAME_PHASE323,
            media_slot="Slot A",
            ac_adaptor_connected=True,
        )
        self.assertFalse(bad_fx6_slota[0])

        bad_fx6_no_ac = validate_fx3_vs_fx6_bodydata_policy(
            camera_model=FX6_MODEL_NAME_PHASE323,
            media_slot="Slot B",
            ac_adaptor_connected=False,
        )
        self.assertFalse(bad_fx6_no_ac[0])

    def test_61_g144_fx3_stepping_stone_204_205_enforced_below_eq_202(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            current_fx3_fw="2.00",
            target_fx3_fw="7.02",
            stepping_stone_204_205_completed=False,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.fx3_stepping_stone_required_for_current_fw)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

        ok = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            current_fx3_fw="2.02",
            target_fx3_fw="7.02",
            stepping_stone_204_205_completed=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.fx3_stepping_stone_required_for_current_fw)

    def test_62_g144_bodydata_exact_filename_enforced(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            bodydata_filename="BODYDATA_FX6.DAT"
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_63_g144_hard_nogo_stage_bodydata_to_slot1_blocked_erofs(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            slot_1_contains_tier0_vault=True,
            stage_bodydata_to_slot1_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL)
        self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE323)
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_64_g144_hard_nogo_invoke_software_update_blocked_eperm(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            invoke_software_update_requested=True
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL)
        self.assertEqual(bad.block_errno, EPERM_ERRNO_PHASE323)
        self.assertFalse(bad.emmc_writes_authorized)

    def test_65_g144_hard_nogo_persistent_emmc_and_cnflasha_writes_blocked_eperm(
        self,
    ) -> None:
        for kw in (
            {"request_persistent_emmc_writes": True},
            {"cnflasha_write_requested": True},
        ):
            bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL
            )
            self.assertEqual(bad.block_errno, EPERM_ERRNO_PHASE323)
            self.assertFalse(bad.emmc_writes_authorized)

    def test_66_g144_hard_nogo_cross_model_flash_and_live_attach_blocked_eperm(
        self,
    ) -> None:
        for kw in (
            {"cross_model_flash_requested": True},
            {"hardware_live_attachment_requested": True},
        ):
            bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL
            )
            self.assertEqual(bad.block_errno, EPERM_ERRNO_PHASE323)
            self.assertFalse(bad.cross_model_flash_authorized)
            self.assertFalse(bad.hardware_live_attachment_authorized)
            self.assertEqual(bad.usb_packets_transmitted, 0)

    def test_67_g144_reset_behavior_silent_and_target_vs_audio_signals(self) -> None:
        cam_rst = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE323,
            requested_silent_mode="On",
            requested_aperture_drive_in_af="Silent Priority",
            requested_auto_pixel_mapping="Not Target",
            requested_audio_signals="Off",
        )
        self.assertTrue(cam_rst.valid)
        self.assertEqual(cam_rst.effective_silent_mode, "Off")
        self.assertEqual(cam_rst.effective_aperture_drive_in_af, "Standard(Still-Only)")
        self.assertEqual(cam_rst.effective_auto_pixel_mapping, "Off")
        # [Audio signals] is Initialize-only, NOT reset by Camera Settings Reset
        self.assertEqual(cam_rst.effective_audio_signals, "Off")

        init_rst = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE323,
            requested_audio_signals="Off",
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_audio_signals, "On")

    def test_68_g144_matrix_exact_204_states(self) -> None:
        mat = compute_silent_target_bodydata_matrix()
        self.assertEqual(mat["silent_states_checked"], 144)
        self.assertEqual(mat["fw_policy_states_checked"], 60)
        self.assertEqual(mat["total_matrix_states"], 204)

    def test_69_g144_blink_progress_and_error_tables_pinned(self) -> None:
        self.assertEqual(FX3_UPDATE_BLINK_PROGRESS_G144, "1 -> 3 -> 5")
        self.assertEqual(
            FX3_UPDATE_ERROR_BLINK_CODES_G144,
            ("5 long (0.5s) / 6 short (0.25s)", "7 long / 7 short"),
        )

    def test_70_g144_invalid_telemetry_rejected_einval(self) -> None:
        for kw in (
            {"body_model_name": "FX30"},
            {"body_model_id": 123},
            {"shoot_mode": "Playback"},
            {"reset_action": "Reboot"},
            {"requested_silent_mode": "Auto"},
            {"requested_audio_signals": "Mute"},
            {"airplane_mode": "Unknown"},
            {"requested_aperture_drive_in_af": "Turbo"},
            {"requested_auto_pixel_mapping": "On"},
        ):
            bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(**kw)
            self.assertFalse(bad.valid, msg=f"kw={kw} should fail")
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_71_g144_unknown_silent_override_rejected_einval(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_silent_mode="On",
            requested_silent_disabled_func_override="Focus Peaking",
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE323)

    def test_72_g144_validate_policy_unknown_model_and_bool_battery_rejected(self) -> None:
        ok, errno_v, _ = validate_fx3_vs_fx6_bodydata_policy(camera_model="ILME-A7RV")
        self.assertFalse(ok)
        self.assertEqual(errno_v, EINVAL_ERRNO_PHASE323)

        ok_b, errno_b, _ = validate_fx3_vs_fx6_bodydata_policy(
            battery_soc_pct=True  # type: ignore[arg-type]
        )
        self.assertFalse(ok_b)
        self.assertEqual(errno_b, EINVAL_ERRNO_PHASE323)

    def test_73_g144_resolve_state_helper_direct(self) -> None:
        st = resolve_fx3_silent_target_bodydata_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE323,
            requested_silent_mode="On",
            airplane_mode="On",
            current_fx3_fw="2.00",
        )
        self.assertTrue(st["valid"])
        self.assertEqual(st["effective_shutter_type"], "Electronic Shutter")
        self.assertTrue(st["update_badge_silenced"])
        self.assertTrue(st["fx3_stepping_stone_required_for_current_fw"])

    def test_74_g144_evaluate_wrapper_returns_verdict_and_result(self) -> None:
        v, r = evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            force_clean_room=True
        )
        self.assertEqual(v.gate_id, G144)
        self.assertEqual(v.gate_code, G144_GATE_CODE)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(r.status, STATUS_VERIFIED_G144)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_75_g144_evaluate_wrapper_propagates_nogo_flash_fault(self) -> None:
        v, r = evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            force_clean_room=True,
            stage_bodydata_to_slot1_requested=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL
        )

    def test_76_g144_target_auto_pixel_mapping_not_target_marks_actuation(self) -> None:
        res = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            requested_auto_pixel_mapping="Not Target"
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.power_off_mechanical_shutter_actuation)

    def test_77_g144_target_function_exact_2_items_tuple(self) -> None:
        self.assertEqual(
            EXACT_2_TARGET_FUNCTION_ITEMS_G144,
            ("Aperture Drive in AF", "Auto Pixel Mapping"),
        )

    def test_78_g144_exact_5_silent_disabled_functions_tuple(self) -> None:
        self.assertEqual(
            EXACT_5_SILENT_DISABLED_FUNCTIONS_G144,
            (
                "Flash",
                "Long Exposure NR",
                "e-Front Curtain Shut.",
                "BULB",
                "Anti-flicker Shoot.",
            ),
        )

    def test_79_g144_status_invalid_telemetry_code(self) -> None:
        bad = verify_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            body_model_id=0
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G144_TELEMETRY_INVALID)

    def test_80_g144_result_dataclass_roundtrip_zero_leak(self) -> None:
        _, r = evaluate_g144_silent_target_no_pwrshutter_and_slot1_bodydata_nogo_guard(
            force_clean_room=True
        )
        encoded = json.dumps(r.to_dict())
        self.assertIn(G144_GATE_CODE, encoded)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r.emmc_writes_authorized)
        self.assertFalse(r.cross_model_flash_authorized)

    # =========================================================================
    # Section D: Unified 144-Gate Milestone Master Preflight & CLI (81..96)
    # =========================================================================

    def test_81_master_144gate_offline_default_141_of_144(self) -> None:
        rep = evaluate_144gate_preflight(DEFAULT_REPO_ROOT)
        self.assertIsInstance(rep, Master144GateReport)
        self.assertEqual(rep.schema_version, "realhw_144gate_preflight_v1")
        self.assertEqual(rep.status, "VERIFIED_141_OF_144_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 144)
        self.assertEqual(rep.summary["verified_gates"], 141)
        self.assertEqual(len(rep.gates), 144)
        self.assertTrue(rep.offline_141_gates_verified)
        self.assertFalse(rep.all_144_gates_verified)
        self.assertTrue(rep.g13_to_g144_all_passed)
        self.assertTrue(rep.g143_to_g144_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_82_master_144gate_simulate_bench_dry_run_144_of_144(self) -> None:
        rep = evaluate_144gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_144_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 144)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_144_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_83_master_144gate_aliases_and_backup_flag(self) -> None:
        r1 = evaluate_144_master_safety_gates(force_clean_room=True, dry_run_simulated_backup=True)
        r2 = run_144_gate_preflight(force_clean_room=True, dry_run_simulated=True)
        self.assertEqual(r1.summary["verified_gates"], 144)
        self.assertEqual(r2.summary["verified_gates"], 144)
        self.assertTrue(r1.dry_run_rehearsal_only)

    def test_84_master_144gate_request_persistent_emmc_writes_blocked(self) -> None:
        rep = evaluate_144gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_144_gates_verified)
        self.assertFalse(rep.offline_141_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_85_master_144gate_g143_fault_propagation(self) -> None:
        rep = evaluate_144gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            shoe_audio_subject_recog_kwargs={"requested_face_eye_subject": "Insect"},
        )
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G143_SUBJECT_RECOG_DORMANT_OR_ANIMAL_MOVIE_VIOLATION,
        )
        self.assertFalse(rep.g143_to_g144_all_passed)
        self.assertFalse(rep.all_144_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 143)

    def test_86_master_144gate_g144_fault_propagation(self) -> None:
        rep = evaluate_144gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            silent_target_bodydata_kwargs={"cross_model_flash_requested": True},
        )
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G144_SLOT1_BODYDATA_NOGO_FLASH_FIREWALL
        )
        self.assertFalse(rep.g143_to_g144_all_passed)
        self.assertFalse(rep.all_144_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 143)

    def test_87_master_144gate_master_142_override_fault_propagation(self) -> None:
        m142 = fx3_safety.evaluate_142gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            ftp_ftpes_customwb_kwargs={"ftp_protocol": "SFTP"},
        )
        rep = evaluate_144gate_preflight(
            force_clean_room=True,
            dry_run_simulated=True,
            master_142_override=m142,
        )
        self.assertFalse(rep.g13_to_g144_all_passed)
        self.assertFalse(rep.all_144_gates_verified)
        self.assertEqual(rep.status, m142.status)

    def test_88_dynamic_discovery_pattern_finds_144_highest(self) -> None:
        pat = re.compile(r"^evaluate_(\d+)gate_preflight$")
        candidates = []
        for name in dir(fx3_safety):
            m = pat.match(name)
            if m:
                candidates.append((int(m.group(1)), name))
        candidates.sort()
        self.assertIn((142, "evaluate_142gate_preflight"), candidates)
        self.assertIn((144, "evaluate_144gate_preflight"), candidates)
        self.assertGreaterEqual(candidates[-1][0], 144)

    def test_89_cli_verify_144_gates_offline_and_dry_run_clean_room(self) -> None:
        out_off = io.StringIO()
        with contextlib.redirect_stdout(out_off):
            rc_off = cli_main(["verify-144-gates", "--clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=141/144", out_off.getvalue())
        self.assertIn("raw_firmware_bytes_leaked=0", out_off.getvalue())

        out_dry = io.StringIO()
        with contextlib.redirect_stdout(out_dry):
            rc_dry = cli_main(["verify-144-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc_dry, 0)
        self.assertIn("verified=144/144", out_dry.getvalue())
        self.assertIn("all_144_gates_verified=True", out_dry.getvalue())

    def test_90_cli_verify_144_gates_json_and_summary(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli_main(
                ["verify-144-gates", "--clean-room", "--simulate-bench-dry-run", "--json", "--summary"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["schema_version"], "realhw_144gate_preflight_v1")
        self.assertEqual(payload["summary"]["verified_gates"], 144)
        self.assertEqual(payload["g143_status"], STATUS_VERIFIED_G143)
        self.assertEqual(payload["g144_status"], STATUS_VERIFIED_G144)

    def test_91_cli_verify_g143_primary_and_aliases(self) -> None:
        for cmd in (
            "verify-shoe-audio-4ch-subject-recog-guard",
            "verify-g143-shoe-audio-subject-recog",
            "verify-g143",
        ):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["gate"], "G143")
            self.assertEqual(payload["status"], STATUS_VERIFIED_G143)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_92_cli_verify_g144_primary_and_aliases(self) -> None:
        for cmd in (
            "verify-silent-target-bodydata-nogo-guard",
            "verify-g144-silent-target-bodydata-nogo",
            "verify-g144",
        ):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["gate"], "G144")
            self.assertEqual(payload["status"], STATUS_VERIFIED_G144)
            self.assertFalse(payload["emmc_writes_authorized"])
            self.assertFalse(payload["cross_model_flash_authorized"])
            self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_93_cli_plain_stdout_for_g143_and_g144(self) -> None:
        out_143 = io.StringIO()
        with contextlib.redirect_stdout(out_143):
            rc143 = cli_main(["verify-g143", "--clean-room"])
        self.assertEqual(rc143, 0)
        self.assertIn("gate=G143", out_143.getvalue())

        out_144 = io.StringIO()
        with contextlib.redirect_stdout(out_144):
            rc144 = cli_main(["verify-g144", "--clean-room"])
        self.assertEqual(rc144, 0)
        self.assertIn("gate=G144", out_144.getvalue())

    def test_94_cli_help_renders_without_percent_formatting_error(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                cli_main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("verify-144-gates", out.getvalue())

    def test_95_standalone_module_main_all_gates(self) -> None:
        for gate in ("g143", "g144", "144"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = module_main(
                    ["--gate", gate, "--clean-room", "--simulate-bench-dry-run", "--json", "--summary"]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertTrue(payload)

    def test_96_backward_compatibility_verify_142_gates_preserved(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli_main(["verify-142-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=142/142", out.getvalue())


if __name__ == "__main__":
    unittest.main()
