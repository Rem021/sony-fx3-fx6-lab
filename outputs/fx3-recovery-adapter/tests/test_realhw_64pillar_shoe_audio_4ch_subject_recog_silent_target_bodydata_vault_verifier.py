"""Phase 352 (Pillar 64 & 64/64 Milestone) unit tests:
Wave-62 Digital MI Shoe `[Shoe Audio Set.]` (`48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch` def),
`[Audio Recording]` (`On` def/`Off`, disabled in `S&Q`), `[Audio Rec Level]` (`0..31` def `26`,
always-on body Limiter), `[Wind Noise Reduct.]` (internal mic only), `[Audio Out Timing]`
(`Live` def/`Lip Sync` under `Shooting -> [Audio Recording]`, NOT `Setup -> [Sound Option]`),
removal of standalone `[Audio Level Display]` in Ver. 2.00..7.02 (`EOPNOTSUPP=95`),
`[4ch Audio Monitoring]` 5 mixes, all main codecs `24-bit 4ch LPCM` vs Proxy forced
`MPEG-4 AAC-LC 2ch 128 kbps` & disabled `>= 100p`, hardware preemption (`3.5mm MIC` > MI Shoe,
`XLR-H1 HANDLE AUDIO=OFF` -> internal mic, `ANALOG` -> `48kHz/16bit 2ch`, `INPUT1->CH1`,
`INPUT2->CH2`, `INPUT3->CH3/CH4`) vs FX6 native `4ch 24-bit 48kHz`, physical `CH1..CH4`,
6-step `Limiter Mode`, dormant `32bit float` (`0x3215`); `[Face/Eye Subject]` strictly
`Human`/`Animal` (`Animal` Still-only Eye AF via `TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` ->
Movie/S&Q `EOPNOTSUPP=95`), ZERO `Bird`/`Insect`/`Car/Train`/`Airplane` (`bkid_app_airplane_hits == 0`),
active `[Face Memory]` (`<= 8` faces, Reset-immune, NOT in `CAMSET*.DAT`, cleared by
`Delete All`/`Initialize`), `0 px` Clean-HDMI Face/Eye frame isolation vs FX6 `Human`-only &
`Saved Tracking Face`; `[Silent Mode Settings]` (`On` -> Electronic Shutter + `Audio signals=Off` +
5 locked features `[Flash, Long Exposure NR, e-Front Curtain Shut., BULB, Anti-flicker Shoot.]`,
`[AF Illuminator]` NOT auto-disabled) + `[Target Function Settings]` strictly `2` items
(`[Aperture Drive in AF]` Still-only, `[Auto Pixel Mapping]` `Off` def/`Not Target`), ZERO exposed
`[Shutter When Pwr OFF]` (`EOPNOTSUPP=95`) vs FX6 zero mechanical shutter; `[Version]` &
`[Software Update]` (`BODYDATA.DAT` strictly `Slot 1` root vs FX6 `Slot B` root + AC Adaptor,
`NP-FZ100 >= 51%`, mandatory `Ver. 2.04/2.05` stepping-stone gate from `<= Ver. 2.02`,
Zero-RF update badge suppression, and Tier-0 `Slot 1` `EROFS=30` & `NO-GO` Flash Firewall).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_ROOT = Path(__file__).resolve().parents[1]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

import fx3_recovery as fr  # noqa: E402
from fx3_recovery import (  # noqa: E402
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_64_PILLAR_COUNT,
    MASTER_64_PILLAR_IDS,
    MASTER_64_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P352_4CH_AUDIO_MONITORING_MIXES,
    P352_4CH_AUDIO_OUTPUT_CHANNELS,
    P352_ALL_SUBJECT_TOKENS,
    P352_ANIMAL_EYE_MOVIE_NOT_SUPPORT_SYMBOL,
    P352_APERTURE_DRIVE_DEFAULT,
    P352_APERTURE_DRIVE_MODES,
    P352_AUDIO_OUT_TIMINGS,
    P352_AUDIO_OUT_TIMING_DEFAULT,
    P352_AUDIO_OUT_TIMING_MENU_PATH,
    P352_AUDIO_REC_LEVEL_DEFAULT,
    P352_AUDIO_REC_LEVEL_MAX,
    P352_AUDIO_REC_LEVEL_MIN,
    P352_AUTO_PIXEL_MAPPING_DEFAULT,
    P352_AUTO_PIXEL_MAPPING_MODES,
    P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT,
    P352_BLOCKED_INVALID_PILLAR64A_SPEC,
    P352_BLOCKED_INVALID_PILLAR64B_SPEC,
    P352_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT,
    P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT,
    P352_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT,
    P352_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P352_BODYDATA_FILENAME,
    P352_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P352_CONCURRENT_CEILING_SECONDS,
    P352_CROSS_MODEL_FLASH_AUTHORIZED,
    P352_DONOR_FX3_702_BODYDATA_RELPATH,
    P352_DONOR_FX3_APPFW_702_RELPATH,
    P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH,
    P352_DONOR_FX6_APPFW_601_RELPATH,
    P352_DONOR_FX6_AVBB_AUDIO_RELPATH,
    P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH,
    P352_DONOR_INSPECT_BUDGET_SECONDS,
    P352_DORMANT_SUBJECT_F_RESID16S,
    P352_EMMC_WRITES_AUTHORIZED,
    P352_ENOENT_ERRNO,
    P352_ENV_CLEAN_ROOM_TEST,
    P352_EOPNOTSUPP_ERRNO,
    P352_EROFS_ERRNO,
    P352_FAST_CLI_BUDGET_SECONDS,
    P352_FX3_BKID_APP_AIRPLANE_HITS,
    P352_FX3_DORMANT_SUBJECTS,
    P352_FX3_EXPOSED_SUBJECTS,
    P352_FX3_FACE_FRAME_DISP_DEFAULT,
    P352_FX3_FACE_MEMORY_IN_CAMSET,
    P352_FX3_FACE_MEMORY_MAX_FACES,
    P352_FX3_FW_VERSION,
    P352_FX3_LEGACY_PRE_STEPPING_VERSIONS,
    P352_FX3_LIMITER_CONFIGURABLE,
    P352_FX3_MAIN_VIDEO_CODECS,
    P352_FX3_MIN_BATTERY_BARS,
    P352_FX3_MIN_BATTERY_PCT,
    P352_FX3_MODEL_ID,
    P352_FX3_MODEL_NAME,
    P352_FX3_PROXY_AUDIO_SPEC,
    P352_FX3_PROXY_DISABLED_MIN_FPS,
    P352_FX3_SHUTTER_WHEN_PWR_OFF_EXPOSED,
    P352_FX3_STEPPING_STONE_VERSIONS,
    P352_FX3_SUBJECT_DEFAULT,
    P352_FX3_UI_EXPOSES_AUDIO_LEVEL_DISPLAY,
    P352_FX3_UPDATE_SLOT,
    P352_FX6_32BIT_FLOAT_ACTIVE,
    P352_FX6_DONOR_FW_VERSION,
    P352_FX6_DONOR_MODEL_NAME,
    P352_FX6_FACE_EYE_MODES,
    P352_FX6_HAS_MECHANICAL_SHUTTER,
    P352_FX6_LIMITER_MODES,
    P352_FX6_UPDATE_SLOT,
    P352_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P352_PILLAR_64A_SCENARIO_IDS,
    P352_PILLAR_64B_SCENARIO_IDS,
    P352_PINNED_FX3_BACKUP_BIN_SHA256,
    P352_SHOE_AUDIO_FORMATS,
    P352_SHOE_AUDIO_FORMAT_DEFAULT,
    P352_SILENT_MODE_AF_ILLUMINATOR_AUTO_DISABLED,
    P352_SILENT_MODE_LOCKED_FEATURES,
    P352_SILENT_TARGET_EXPOSED_ITEMS,
    P352_SOUND_OPTION_MENU_PATH,
    P352_STAGE_B_VOLATILE_OVERLAY_DIR,
    P352_STATUS_VERIFIED_64OF64_AGGREGATOR,
    P352_STATUS_VERIFIED_PILLAR64_SUITE,
    P352_STATUS_VERIFIED_PILLAR_64A,
    P352_STATUS_VERIFIED_PILLAR_64B,
    P352_TIER0_SURFACE_COUNT,
    P352_WRITE_MUTATING_VAULT_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE352_MASTER_SCHEMA,
    PHASE352_PHASE_NUMBER,
    PHASE352_SCHEMA,
    PHASE352_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_shoe_audio_subject_recog_vault_spec,
    build_default_safe_silent_target_bodydata_vault_spec,
    compute_expected_shoe_audio_subject_recog_state,
    compute_expected_silent_target_version_bodydata_state,
    evaluate_64pillar_recovery_master,
    evaluate_realhw_64pillar_recovery_master,
    evaluate_shoe_audio_subject_recog_vault,
    evaluate_silent_target_bodydata_vault,
    inspect_phase352_donors_readonly,
    run_pillar64_standalone_suite,
    run_pillar64a_shoe_audio_subject_recog_vault_6_scenario_suite,
    run_pillar64b_silent_target_bodydata_vault_6_scenario_suite,
    verify_64pillar_recovery,
    verify_64pillar_recovery_suite,
    verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault,
    verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault,
)


def _wave62_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P352_DONOR_FX3_APPFW_702_RELPATH,
        P352_DONOR_FX6_APPFW_601_RELPATH,
        P352_DONOR_FX3_LIBSDFILEUPDATER_RELPATH,
        P352_DONOR_FX3_702_BODYDATA_RELPATH,
        P352_DONOR_FX6_AVBB_AUDIO_RELPATH,
        P352_DONOR_FX6_LIBINFRAHOTSHOE_RELPATH,
    )
    for rel in required:
        rel_n = rel[5:] if rel.startswith("work/") else rel
        if not any(
            r is not None and ((r / rel_n).exists() or (r.parent / rel).exists())
            for r in roots
        ):
            return False
    return True


class Phase352Pillar64VerifierTests(unittest.TestCase):
    """Phase 352 Pillar 64 & 64/64 Master Recovery Verifier unit tests."""

    # ------------------------------------------------------------------
    # Safety Invariants, Constants & 4-Mode Bounded Donor Inspection (01..12)
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_and_budget_constants(self) -> None:
        self.assertEqual(PHASE352_PHASE_NUMBER, 352)
        self.assertEqual(
            PHASE352_SCHEMA,
            "realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier_v1",
        )
        self.assertEqual(PHASE352_MASTER_SCHEMA, "realhw_64pillar_recovery_master_v1")
        self.assertEqual(PHASE352_VERSION, "1.0.0")
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(P352_EMMC_WRITES_AUTHORIZED)
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
        self.assertFalse(P352_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(P352_CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED)
        self.assertFalse(P352_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertLessEqual(P352_DONOR_INSPECT_BUDGET_SECONDS, 2.0)
        self.assertEqual(P352_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P352_EROFS_ERRNO, 30)
        self.assertEqual(P352_EOPNOTSUPP_ERRNO, 95)

    def test_02_wave62_empirical_constants_and_pillar_specs(self) -> None:
        self.assertEqual(P352_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P352_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P352_FX3_FW_VERSION, "7.02")
        self.assertEqual(P352_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P352_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P352_AUDIO_REC_LEVEL_MIN, 0)
        self.assertEqual(P352_AUDIO_REC_LEVEL_MAX, 31)
        self.assertEqual(P352_AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertFalse(P352_FX3_LIMITER_CONFIGURABLE)
        self.assertFalse(P352_FX3_UI_EXPOSES_AUDIO_LEVEL_DISPLAY)
        self.assertFalse(P352_FX6_32BIT_FLOAT_ACTIVE)
        self.assertEqual(P352_AUDIO_OUT_TIMING_MENU_PATH, "Shooting -> [Audio Recording]")
        self.assertEqual(P352_SOUND_OPTION_MENU_PATH, "Setup -> [Sound Option]")
        self.assertEqual(len(P352_4CH_AUDIO_MONITORING_MIXES), 5)
        self.assertEqual(len(P352_FX3_MAIN_VIDEO_CODECS), 6)
        self.assertEqual(P352_FX3_PROXY_AUDIO_SPEC, "MPEG-4 AAC-LC 2ch 128 kbps")
        self.assertEqual(P352_FX3_EXPOSED_SUBJECTS, ("Human", "Animal"))
        self.assertEqual(len(P352_FX3_DORMANT_SUBJECTS), 5)
        self.assertEqual(P352_FX3_BKID_APP_AIRPLANE_HITS, 0)
        self.assertEqual(P352_FX3_FACE_MEMORY_MAX_FACES, 8)
        self.assertFalse(P352_FX3_FACE_MEMORY_IN_CAMSET)
        self.assertEqual(P352_FX3_FACE_FRAME_DISP_DEFAULT, "Off")
        self.assertEqual(P352_SILENT_TARGET_EXPOSED_ITEMS, ("Aperture Drive in AF", "Auto Pixel Mapping"))
        self.assertEqual(len(P352_SILENT_MODE_LOCKED_FEATURES), 5)
        self.assertFalse(P352_SILENT_MODE_AF_ILLUMINATOR_AUTO_DISABLED)
        self.assertFalse(P352_FX3_SHUTTER_WHEN_PWR_OFF_EXPOSED)
        self.assertFalse(P352_FX6_HAS_MECHANICAL_SHUTTER)
        self.assertEqual(P352_BODYDATA_FILENAME, "BODYDATA.DAT")
        self.assertEqual(P352_FX3_UPDATE_SLOT, "Slot 1")
        self.assertEqual(P352_FX6_UPDATE_SLOT, "Slot B")
        self.assertEqual(P352_FX3_MIN_BATTERY_PCT, 51)
        self.assertEqual(P352_FX3_MIN_BATTERY_BARS, 3)
        self.assertEqual(MASTER_64_PILLAR_COUNT, 64)
        self.assertEqual(len(MASTER_64_PILLAR_IDS), 64)
        self.assertEqual(len(MASTER_64_PILLAR_SPECS), 64)
        nums = [spec[0] for spec in MASTER_64_PILLAR_SPECS]
        self.assertIn(64, nums)
        self.assertGreaterEqual(max(nums), 64)

    def test_03_donor_inspect_mode_1_local_o_rdonly_if_present(self) -> None:
        snap = inspect_phase352_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 21)
        self.assertTrue(snap.under_2_0s_budget)
        self.assertLessEqual(snap.elapsed_seconds, P352_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if (
            _wave62_donors_present()
            and not fr.files.is_forced_clean_room()
            and os.environ.get(P352_ENV_CLEAN_ROOM_TEST) != "1"
        ):
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            for art in snap.artifacts:
                self.assertEqual(art.read_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(art.matches_pinned, art.artifact_id)
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_inspect_mode_2_fx3_clean_room_test_env(self) -> None:
        with patch.dict(os.environ, {P352_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase352_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 21)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_05_donor_inspect_mode_3_fx3_fx6_force_clean_room_env(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase352_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 21)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_06_donor_inspect_mode_4_work_root_none_and_nonexistent_fallback(self) -> None:
        with patch.object(
            fr.files,
            "iter_donor_work_roots",
            return_value=(None, Path("/nonexistent/phase352_wave62_donor_root")),
        ):
            snap = inspect_phase352_donors_readonly(force_clean_room=False)
            master = evaluate_realhw_64pillar_recovery_master(force_clean_room=None)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 21)
        self.assertTrue(master.all_passed)
        self.assertEqual(master.pillars_passed, 64)
        self.assertEqual(master.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    # ------------------------------------------------------------------
    # Pillar 64A: Digital MI Shoe `[Shoe Audio Set.]`, Preemption & `[Face/Eye Subject]` (07..22)
    # ------------------------------------------------------------------

    def test_07_pillar64a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec()
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P352_STATUS_VERIFIED_PILLAR_64A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.shoe_audio_4ch_preemption_and_timing_verified)
        self.assertTrue(rep.subject_recog_human_animal_and_face_memory_verified)
        self.assertTrue(rep.slot1_vault_and_h0_h3_verified)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.hdmi_face_frame_pixels_emitted, 0)

    def test_08_pillar64a_audio_recording_disabled_in_sq_rejected(self) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            shooting_domain="S&Q",
            audio_recording_enabled=True,
            reported_sq_audio_errno=None,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

    def test_09_pillar64a_audio_rec_level_bounds_and_nonconfigurable_limiter(self) -> None:
        for bad_lvl in (-1, 32):
            spec_lvl = build_default_safe_shoe_audio_subject_recog_vault_spec(
                audio_rec_level=bad_lvl,
                post_audio_rec_level=bad_lvl,
            )
            rep = evaluate_shoe_audio_subject_recog_vault(spec_lvl)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

        spec_lim = build_default_safe_shoe_audio_subject_recog_vault_spec(
            fx3_limiter_configurable_requested=True,
            reported_limiter_errno=None,
        )
        rep_lim = evaluate_shoe_audio_subject_recog_vault(spec_lim)
        self.assertFalse(rep_lim.passed)
        self.assertEqual(rep_lim.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

    def test_10_pillar64a_audio_out_timing_menu_path_and_removed_audio_level_disp(self) -> None:
        spec_wrong_path = build_default_safe_shoe_audio_subject_recog_vault_spec(
            audio_out_timing="Lip Sync",
            audio_out_timing_menu_location=P352_SOUND_OPTION_MENU_PATH,
            post_audio_out_timing="Lip Sync",
        )
        rep_path = evaluate_shoe_audio_subject_recog_vault(spec_wrong_path)
        self.assertFalse(rep_path.passed)
        self.assertEqual(rep_path.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

        spec_disp = build_default_safe_shoe_audio_subject_recog_vault_spec(
            audio_level_display_menu_requested=True,
            reported_audio_level_display_errno=None,
        )
        rep_disp = evaluate_shoe_audio_subject_recog_vault(spec_disp)
        self.assertFalse(rep_disp.passed)
        self.assertEqual(rep_disp.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

    def test_11_pillar64a_35mm_preempts_mi_shoe_and_grays_shoe_audio_set(self) -> None:
        st_35 = compute_expected_shoe_audio_subject_recog_state(
            camera_model=P352_FX3_MODEL_NAME,
            fw_version=P352_FX3_FW_VERSION,
            shooting_domain="Movie",
            audio_recording_enabled=True,
            audio_rec_level=26,
            shoe_audio_set="48kHz/24bit 4ch",
            wind_noise_reduct="On",
            audio_out_timing="Live",
            audio_out_timing_menu_location=P352_AUDIO_OUT_TIMING_MENU_PATH,
            audio_level_display_menu_requested=False,
            monitoring_4ch_mix="CH1/CH2",
            hdmi_4ch_audio_out="CH1/CH2",
            video_codec="XAVC S 4K",
            recording_fps=24,
            proxy_recording_enabled=True,
            jack_35mm_mic_inserted=True,
            mi_shoe_device="XLR-H1",
            xlr_h1_handle_audio_on=True,
            xlr_h1_digital_analog_switch="DIGITAL",
            xlr_h1_input_select="IN1_IN2",
            fx3_limiter_configurable_requested=False,
            fx6_limiter_mode="Off",
            fx6_32bit_float_requested=False,
            face_eye_prior_in_af="On",
            face_eye_subject="Human",
            right_left_eye_select="Auto",
            face_eye_frame_disp="Off",
            face_memory_count=0,
            face_memory_exported_in_camset=False,
            regist_faces_priority="On",
            hdmi_info_display="Off",
            fx6_face_eye_detection_mode="Face/Eye Priority AF",
            fx6_saved_tracking_face_active=False,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertEqual(st_35["effective_audio_source"], "3.5mm_MIC_2CH_ANALOG")
        self.assertTrue(st_35["shoe_audio_set_grayed"])
        self.assertEqual(st_35["effective_shoe_audio_format"], "48kHz/16bit 2ch")
        self.assertEqual(st_35["wind_noise_effective"], "Off")
        self.assertEqual(st_35["shoe_format_errno"], P352_EOPNOTSUPP_ERRNO)

    def test_12_pillar64a_xlr_h1_handle_off_fallback_analog_cap_and_proxy_100p_lockout(self) -> None:
        spec_off = build_default_safe_shoe_audio_subject_recog_vault_spec(
            mi_shoe_device="XLR-H1",
            xlr_h1_handle_audio_on=False,
            shoe_audio_set="48kHz/16bit 2ch",
            wind_noise_reduct="On",
            recording_fps=120,
            proxy_recording_enabled=True,
            reported_effective_audio_source="INTERNAL_MIC",
            reported_shoe_audio_set_grayed=True,
            reported_effective_shoe_audio_format="48kHz/16bit 2ch",
            reported_wind_noise_effective="On",
            reported_effective_proxy_audio_spec="DISABLED",
            post_shoe_audio_set="48kHz/16bit 2ch",
            post_wind_noise_reduct="On",
        )
        rep_off = evaluate_shoe_audio_subject_recog_vault(spec_off)
        self.assertTrue(rep_off.passed, rep_off.errors)

        spec_analog_bad = build_default_safe_shoe_audio_subject_recog_vault_spec(
            mi_shoe_device="XLR-H1",
            xlr_h1_handle_audio_on=True,
            xlr_h1_digital_analog_switch="ANALOG",
            shoe_audio_set="48kHz/24bit 4ch",
            reported_effective_audio_source="MI_SHOE_XLR-H1_ANALOG",
            reported_effective_shoe_audio_format="48kHz/24bit 4ch",
            reported_shoe_format_errno=None,
        )
        rep_analog = evaluate_shoe_audio_subject_recog_vault(spec_analog_bad)
        self.assertFalse(rep_analog.passed)

    def test_13_pillar64a_fx6_32bit_float_dormant_rejected(self) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            camera_model=P352_FX6_DONOR_MODEL_NAME,
            fw_version=P352_FX6_DONOR_FW_VERSION,
            fx6_32bit_float_requested=True,
            reported_fx6_32bit_float_errno=None,
            reported_effective_audio_source="FX6_NATIVE_4CH_24BIT",
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P352_BLOCKED_SHOE_AUDIO_PREEMPTION_OR_LIMITER_DRIFT)

    def test_14_pillar64a_animal_eye_af_still_only_vs_movie_not_support(self) -> None:
        self.assertIn("TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT", P352_ANIMAL_EYE_MOVIE_NOT_SUPPORT_SYMBOL)
        spec_still = build_default_safe_shoe_audio_subject_recog_vault_spec(
            shooting_domain="Still",
            proxy_recording_enabled=False,
            reported_effective_proxy_audio_spec="DISABLED",
            face_eye_subject="Animal",
            reported_animal_eye_af_effective=True,
            reported_animal_movie_errno=None,
            reported_regist_faces_priority_enabled=False,
            post_face_eye_subject="Animal",
        )
        rep_still = evaluate_shoe_audio_subject_recog_vault(spec_still)
        self.assertTrue(rep_still.passed, rep_still.errors)

        spec_movie = build_default_safe_shoe_audio_subject_recog_vault_spec(
            shooting_domain="Movie",
            face_eye_subject="Animal",
            reported_animal_eye_af_effective=True,
            reported_animal_movie_errno=None,
            reported_regist_faces_priority_enabled=False,
            post_face_eye_subject="Animal",
        )
        rep_movie = evaluate_shoe_audio_subject_recog_vault(spec_movie)
        self.assertFalse(rep_movie.passed)
        self.assertEqual(rep_movie.block_code, P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT)

    def test_15_pillar64a_dormant_subjects_and_bkid_app_airplane_myth_rejected(self) -> None:
        for sub in P352_FX3_DORMANT_SUBJECTS:
            self.assertIn(sub, P352_DORMANT_SUBJECT_F_RESID16S)
            spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
                shooting_domain="Still",
                proxy_recording_enabled=False,
                reported_effective_proxy_audio_spec="DISABLED",
                face_eye_subject=sub,
                reported_subject_errno=None,
                reported_regist_faces_priority_enabled=False,
                post_face_eye_subject=sub,
            )
            rep = evaluate_shoe_audio_subject_recog_vault(spec)
            self.assertFalse(rep.passed, sub)
            self.assertEqual(rep.block_code, P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT)

        spec_bkid = build_default_safe_shoe_audio_subject_recog_vault_spec(fx3_bkid_app_airplane_hits=1)
        rep_bkid = evaluate_shoe_audio_subject_recog_vault(spec_bkid)
        self.assertFalse(rep_bkid.passed)
        self.assertEqual(rep_bkid.block_code, P352_BLOCKED_SUBJECT_RECOG_MYTH_OR_FACE_MEMORY_DRIFT)

    def test_16_pillar64a_face_memory_8_max_camset_exclusion_reset_and_clean_hdmi(self) -> None:
        spec_over = build_default_safe_shoe_audio_subject_recog_vault_spec(
            face_memory_count=9,
            post_face_memory_count=9,
        )
        self.assertFalse(evaluate_shoe_audio_subject_recog_vault(spec_over).passed)

        spec_camset = build_default_safe_shoe_audio_subject_recog_vault_spec(
            face_memory_exported_in_camset=True,
        )
        self.assertFalse(evaluate_shoe_audio_subject_recog_vault(spec_camset).passed)

        spec_hdmi = build_default_safe_shoe_audio_subject_recog_vault_spec(
            face_eye_frame_disp="On",
            hdmi_face_frame_pixels_emitted=512,
            post_face_eye_frame_disp="On",
        )
        self.assertFalse(evaluate_shoe_audio_subject_recog_vault(spec_hdmi).passed)

    def test_17_pillar64a_slot1_vault_overlay_escape_and_h0_h3_drift(self) -> None:
        for bad_act in P352_WRITE_MUTATING_VAULT_ACTIONS:
            spec_v = build_default_safe_shoe_audio_subject_recog_vault_spec(
                requested_vault_action=bad_act,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
            rep_v = evaluate_shoe_audio_subject_recog_vault(spec_v)
            self.assertFalse(rep_v.passed, bad_act)
            self.assertEqual(rep_v.block_code, P352_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

        spec_ov = build_default_safe_shoe_audio_subject_recog_vault_spec(overlay_dir="/setting/bad64a")
        rep_ov = evaluate_shoe_audio_subject_recog_vault(spec_ov)
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P352_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        spec_h3 = build_default_safe_shoe_audio_subject_recog_vault_spec(backup_bin_h3_sha256="f" * 64)
        rep_h3 = evaluate_shoe_audio_subject_recog_vault(spec_h3)
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P352_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    # ------------------------------------------------------------------
    # Pillar 64B: `[Silent Mode Settings]`, `[Version]` & `BODYDATA.DAT` Vault (18..30)
    # ------------------------------------------------------------------

    def test_18_pillar64b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_silent_target_bodydata_vault_spec()
        rep = evaluate_silent_target_bodydata_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P352_STATUS_VERIFIED_PILLAR_64B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.silent_mode_2item_target_and_zero_barrier_verified)
        self.assertTrue(rep.version_bodydata_slot1_nogo_and_vault_verified)
        self.assertTrue(rep.overlay_and_h0_h3_verified)
        self.assertFalse(rep.bodydata_placement_or_flash_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertFalse(rep.hardware_live_attachment_authorized)

    def test_19_pillar64b_silent_mode_on_forces_eshutter_audio_off_and_leaves_af_illum_intact(self) -> None:
        spec = build_default_safe_silent_target_bodydata_vault_spec(
            silent_mode="On",
            af_illuminator_setting="Auto",
            audio_signals_setting="On",
            shutter_type_setting="Mechanical Shutter",
            reported_effective_shutter_type="Electronic Shutter",
            reported_effective_audio_signals="Off",
            reported_effective_af_illuminator="Auto",
            post_silent_mode="On",
        )
        rep = evaluate_silent_target_bodydata_vault(spec)
        self.assertTrue(rep.passed, rep.errors)

    def test_20_pillar64b_silent_mode_5_locked_features_reject_when_unblocked(self) -> None:
        for flag in (
            "flash_requested",
            "long_exposure_nr_requested",
            "efcs_requested",
            "bulb_requested",
            "anti_flicker_requested",
        ):
            spec = build_default_safe_silent_target_bodydata_vault_spec(
                silent_mode="On",
                reported_effective_shutter_type="Electronic Shutter",
                reported_effective_audio_signals="Off",
                reported_silent_feature_errno=None,
                post_silent_mode="On",
                **{flag: True},
            )
            rep = evaluate_silent_target_bodydata_vault(spec)
            self.assertFalse(rep.passed, flag)
            self.assertEqual(rep.block_code, P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT)

    def test_21_pillar64b_strict_2item_target_and_dormant_shutter_when_pwr_off_rejected(self) -> None:
        spec_3rd = build_default_safe_silent_target_bodydata_vault_spec(
            requested_silent_target_extra_items=("Touch Operation",),
            reported_extra_target_item_errno=None,
        )
        rep_3rd = evaluate_silent_target_bodydata_vault(spec_3rd)
        self.assertFalse(rep_3rd.passed)
        self.assertEqual(rep_3rd.block_code, P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT)

        spec_pwr = build_default_safe_silent_target_bodydata_vault_spec(
            shutter_when_pwr_off_exposed_requested=True,
            reported_shutter_when_pwr_off_errno=None,
            dormant_shutter_when_pwr_off_exposed_events=1,
        )
        rep_pwr = evaluate_silent_target_bodydata_vault(spec_pwr)
        self.assertFalse(rep_pwr.passed)
        self.assertEqual(rep_pwr.block_code, P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT)

    def test_22_pillar64b_auto_pixel_mapping_not_target_or_cnflasha_write_blocked(self) -> None:
        spec_map = build_default_safe_silent_target_bodydata_vault_spec(
            target_auto_pixel_mapping="Not Target",
            cnflasha_pixel_map_mutation_bytes=4096,
            post_auto_pixel_mapping="Not Target",
        )
        rep = evaluate_silent_target_bodydata_vault(spec_map)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P352_BLOCKED_SILENT_TARGET_OR_SHUTTER_BARRIER_DRIFT)

    def test_23_pillar64b_bodydata_slot1_vs_slot2_and_battery_51pct_gate(self) -> None:
        spec_s2 = build_default_safe_silent_target_bodydata_vault_spec(
            bodydata_target_slot="Slot 2",
            reported_bodydata_action_allowed=True,
            reported_bodydata_errno=None,
        )
        rep_s2 = evaluate_silent_target_bodydata_vault(spec_s2)
        self.assertFalse(rep_s2.passed)
        self.assertEqual(rep_s2.block_code, P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT)

        spec_bat = build_default_safe_silent_target_bodydata_vault_spec(
            battery_percent=50,
            reported_bodydata_action_allowed=True,
            reported_bodydata_errno=None,
        )
        rep_bat = evaluate_silent_target_bodydata_vault(spec_bat)
        self.assertFalse(rep_bat.passed)
        self.assertEqual(rep_bat.block_code, P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT)

    def test_24_pillar64b_fx3_stepping_stone_ver204_205_gate_vs_legacy_202(self) -> None:
        for pre_ver in P352_FX3_LEGACY_PRE_STEPPING_VERSIONS:
            st = compute_expected_silent_target_version_bodydata_state(
                camera_model=P352_FX3_MODEL_NAME,
                fw_version=P352_FX3_FW_VERSION,
                shooting_domain="Still",
                silent_mode="Off",
                target_aperture_drive_in_af="Standard",
                target_auto_pixel_mapping="Off",
                requested_silent_target_extra_items=(),
                shutter_when_pwr_off_exposed_requested=False,
                af_illuminator_setting="Auto",
                audio_signals_setting="On",
                shutter_type_setting="Auto",
                flash_requested=False,
                long_exposure_nr_requested=False,
                efcs_requested=False,
                bulb_requested=False,
                anti_flicker_requested=False,
                lens_mounted_supports_fw_update=True,
                airplane_mode="On",
                battery_percent=80,
                ac_adaptor_connected=False,
                current_body_fw_version=pre_ver,
                target_body_fw_version="7.02",
                bodydata_filename="BODYDATA.DAT",
                bodydata_target_slot="Slot 1",
                bodydata_stage_or_flash_requested=False,
                cross_model_flash_requested=False,
                reset_action="None",
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="READ_ONLY_AUDIT",
            )
            self.assertTrue(st["stepping_stone_needed"], pre_ver)
            self.assertFalse(st["bodydata_action_allowed"], pre_ver)
            self.assertIn("MISSING_VER_204_205_STEPPING_STONE_5LONG_6SHORT", st["flash_blocked_reasons"])

        for step_ver in P352_FX3_STEPPING_STONE_VERSIONS:
            spec_ok = build_default_safe_silent_target_bodydata_vault_spec(
                current_body_fw_version=step_ver,
                target_body_fw_version="7.02",
            )
            self.assertTrue(evaluate_silent_target_bodydata_vault(spec_ok).passed, step_ver)

    def test_25_pillar64b_fx6_slot_b_and_mandatory_ac_adaptor_contrast(self) -> None:
        spec_fx6_ok = build_default_safe_silent_target_bodydata_vault_spec(
            camera_model=P352_FX6_DONOR_MODEL_NAME,
            fw_version=P352_FX6_DONOR_FW_VERSION,
            reported_effective_shutter_type="Electronic Shutter",
            bodydata_target_slot=P352_FX6_UPDATE_SLOT,
            ac_adaptor_connected=True,
            current_body_fw_version="6.01",
            target_body_fw_version="6.02",
        )
        rep_ok = evaluate_silent_target_bodydata_vault(spec_fx6_ok)
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        spec_fx6_no_ac = build_default_safe_silent_target_bodydata_vault_spec(
            camera_model=P352_FX6_DONOR_MODEL_NAME,
            fw_version=P352_FX6_DONOR_FW_VERSION,
            bodydata_target_slot=P352_FX6_UPDATE_SLOT,
            ac_adaptor_connected=False,
        )
        self.assertFalse(evaluate_silent_target_bodydata_vault(spec_fx6_no_ac).passed)

    def test_26_pillar64b_nogo_bodydata_flash_and_cross_model_flash_fail_closed_erofs30(self) -> None:
        spec_flash = build_default_safe_silent_target_bodydata_vault_spec(
            bodydata_stage_or_flash_requested=True,
            requested_vault_action="STAGE_BODYDATA_SLOT1",
            reported_bodydata_action_allowed=True,
            reported_bodydata_errno=None,
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
            slot1_bodydata_mutation_bytes=4096,
            slot1_data_sector_writes=4096,
        )
        rep = evaluate_silent_target_bodydata_vault(spec_flash)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT)

        spec_xmodel = build_default_safe_silent_target_bodydata_vault_spec(
            cross_model_flash_requested=True,
            requested_vault_action="CROSS_MODEL_FLASH_FX6_TO_FX3",
            reported_bodydata_action_allowed=True,
            reported_bodydata_errno=None,
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
        )
        rep_xm = evaluate_silent_target_bodydata_vault(spec_xmodel)
        self.assertFalse(rep_xm.passed)
        self.assertEqual(rep_xm.block_code, P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT)

    def test_27_pillar64b_zero_rf_airplane_mode_required_for_red_dot_suppression(self) -> None:
        spec_rf = build_default_safe_silent_target_bodydata_vault_spec(
            airplane_mode="Off",
            rf_packets_transmitted=64,
            reported_update_red_dot_suppressed=False,
        )
        rep = evaluate_silent_target_bodydata_vault(spec_rf)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P352_BLOCKED_BODYDATA_VERSION_FLASH_OR_SLOT1_VAULT)

    def test_28_pillar64b_invalid_enum_spec_fields_rejected(self) -> None:
        spec_a = build_default_safe_shoe_audio_subject_recog_vault_spec(shoe_audio_set="96kHz/32bit")
        rep_a = evaluate_shoe_audio_subject_recog_vault(spec_a)
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P352_BLOCKED_INVALID_PILLAR64A_SPEC)

        spec_b = build_default_safe_silent_target_bodydata_vault_spec(
            target_aperture_drive_in_af="InvalidMode"
        )
        rep_b = evaluate_silent_target_bodydata_vault(spec_b)
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P352_BLOCKED_INVALID_PILLAR64B_SPEC)

    # ------------------------------------------------------------------
    # Suites, Symmetry Aliases, Concurrent 64/64 Aggregator & CLI (29..42)
    # ------------------------------------------------------------------

    def test_29_pillar64a_and_64b_6_scenario_suites_2_allow_4_reject(self) -> None:
        res_a = run_pillar64a_shoe_audio_subject_recog_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)
        self.assertEqual(sum(1 for s in res_a.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res_a.scenarios if not s.expected_allowed), 4)
        self.assertEqual([s.scenario_id for s in res_a.scenarios], list(P352_PILLAR_64A_SCENARIO_IDS))

        res_b = run_pillar64b_silent_target_bodydata_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)
        self.assertEqual(sum(1 for s in res_b.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res_b.scenarios if not s.expected_allowed), 4)
        self.assertEqual([s.scenario_id for s in res_b.scenarios], list(P352_PILLAR_64B_SCENARIO_IDS))

    def test_30_standalone_suite_and_symmetry_aliases(self) -> None:
        r1 = run_pillar64_standalone_suite(force_clean_room=True)
        r2 = run_pillar64_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, P352_STATUS_VERIFIED_PILLAR64_SUITE)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(r1.slot1_data_sector_writes, 0)
        self.assertFalse(r1.bodydata_placement_or_flash_authorized)

        c1 = verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault(force_clean_room=True)
        c2 = verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault(force_clean_room=True)
        self.assertTrue(c1.all_passed)
        self.assertTrue(c2.all_passed)
        self.assertEqual(c1.shoe_audio_subject_report.digest_sha256, c2.shoe_audio_subject_report.digest_sha256)
        self.assertEqual(c1.silent_target_bodydata_report.digest_sha256, c2.silent_target_bodydata_report.digest_sha256)

    def test_31_concurrent_64pillar_master_all_64_pillars_pass_and_deterministic_sha(self) -> None:
        rep1 = evaluate_realhw_64pillar_recovery_master(force_clean_room=True)
        rep2 = evaluate_64pillar_recovery_master(force_clean_room=True)
        rep3 = verify_64pillar_recovery_suite(force_clean_room=True)
        rep4 = verify_64pillar_recovery(force_clean_room=True)
        for rep in (rep1, rep2, rep3, rep4):
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P352_STATUS_VERIFIED_64OF64_AGGREGATOR)
            self.assertEqual(rep.pillar_count, 64)
            self.assertEqual(rep.pillars_passed, 64)
            self.assertEqual(rep.failed_pillars, ())
            self.assertTrue(rep.under_6s_budget)
            self.assertTrue(rep.nominal_under_4_0s)
            self.assertEqual(rep.fx3_audio_rec_level_default, 26)
            self.assertEqual(rep.fx3_audio_rec_level_max, 31)
            self.assertFalse(rep.fx3_ui_exposes_audio_level_display)
            self.assertFalse(rep.fx3_limiter_configurable)
            self.assertFalse(rep.fx6_32bit_float_active)
            self.assertEqual(rep.fx3_exposed_subject_count, 2)
            self.assertEqual(rep.fx3_bkid_app_airplane_hits, 0)
            self.assertEqual(rep.fx3_face_memory_max_faces, 8)
            self.assertEqual(rep.fx3_silent_target_item_count, 2)
            self.assertEqual(rep.fx3_silent_mode_locked_feature_count, 5)
            self.assertFalse(rep.fx3_shutter_when_pwr_off_exposed)
            self.assertFalse(rep.fx6_mechanical_shutter_present)
            self.assertEqual(rep.fx3_bodydata_slot, "Slot 1")
            self.assertEqual(rep.fx6_bodydata_slot, "Slot B")
            self.assertEqual(rep.fx3_min_battery_percent_for_update, 51)
            self.assertFalse(rep.bodydata_placement_or_flash_authorized)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep1.master_64pillar_sha256, rep2.master_64pillar_sha256)
        self.assertEqual(rep1.master_64pillar_sha256, rep3.master_64pillar_sha256)
        self.assertEqual(rep1.master_64pillar_sha256, rep4.master_64pillar_sha256)

    def test_32_master_64pillar_fast_budget_under_1_5s_clean_room(self) -> None:
        rep = evaluate_realhw_64pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.under_1_5s_fast_cli_budget, f"elapsed={rep.elapsed_seconds}s")
        self.assertLess(rep.elapsed_seconds, P352_FAST_CLI_BUDGET_SECONDS)

    def test_33_master_64pillar_fault_injection_pillar64_and_pillar63(self) -> None:
        rep64 = evaluate_realhw_64pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar64_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault",
        )
        self.assertFalse(rep64.all_passed)
        self.assertEqual(rep64.pillars_passed, 63)
        self.assertIn(
            "pillar64_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault",
            rep64.failed_pillars,
        )

        rep63 = evaluate_realhw_64pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar63_ftp_ftpes_customwb_afspeed_focusmap_marker_vault",
        )
        self.assertFalse(rep63.all_passed)
        self.assertEqual(rep63.pillars_passed, 63)
        self.assertIn(
            "pillar63_ftp_ftpes_customwb_afspeed_focusmap_marker_vault",
            rep63.failed_pillars,
        )

        with self.assertRaises(ValueError):
            evaluate_realhw_64pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_64_plus",
            )

    def test_34_milestone311_and_324_auto_discovery_forward_compatible_ge_64(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)

        c311, fn311, ids311 = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(c311, 64)
        self.assertTrue(callable(fn311))
        self.assertGreaterEqual(len(ids311), 64)

        c324, fn324, ids324 = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(c324, 64)
        self.assertTrue(callable(fn324))
        self.assertGreaterEqual(len(ids324), 64)

        nums_from_adapter = [
            int(name[len("verify_") : -len("pillar_recovery")])
            for name in dir(fr)
            if name.startswith("verify_") and name.endswith("pillar_recovery")
            and name[len("verify_") : -len("pillar_recovery")].isdigit()
        ]
        self.assertIn(64, nums_from_adapter)
        self.assertGreaterEqual(max(nums_from_adapter), 64)

    def test_35_master_64pillar_report_to_dict_roundtrip_and_package_root_exports(self) -> None:
        rep = evaluate_realhw_64pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 64)
        self.assertEqual(parsed["pillars_passed"], 64)
        for sym in (
            "MASTER_64_PILLAR_COUNT",
            "MASTER_64_PILLAR_IDS",
            "MASTER_64_PILLAR_SPECS",
            "Master64PillarRecoveryReport",
            "evaluate_realhw_64pillar_recovery_master",
            "evaluate_64pillar_recovery_master",
            "verify_64pillar_recovery_suite",
            "verify_64pillar_recovery",
            "run_pillar64_standalone_suite",
            "verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_and_vault",
            "verify_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault",
        ):
            self.assertTrue(hasattr(fr, sym), sym)
            self.assertIn(sym, fr.__all__, sym)

    def test_36_cli_verify_64pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-64pillar-recovery", "--json"],
            ["verify-64pillar-recovery", "--force-clean-room", "--json"],
        ):
            proc = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", *args],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], 64)
            self.assertEqual(payload["pillar_count"], 64)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertLess(payload["elapsed_seconds"], P352_CONCURRENT_CEILING_SECONDS)

    def test_37_cli_verify_pillar64_aliases_text_and_out(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar64-recovery",
            "verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault",
        ):
            proc_txt = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", subcmd, "--force-clean-room"],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_txt.returncode, 0, proc_txt.stderr or proc_txt.stdout)
            self.assertIn(
                "VERIFIED_PILLAR64_SHOE_AUDIO_4CH_SUBJECT_RECOG_SILENT_TARGET_BODYDATA_VAULT",
                proc_txt.stdout,
            )

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p352_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p64_path = work_tests / f"{tag}_p64"
        try:
            proc1 = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-64pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_master_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            self.assertTrue((out_master_path / "64pillar-recovery-master-report.json").exists())

            proc2 = subprocess.run(
                [
                    "/usr/bin/python3",
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-pillar64-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_p64_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            self.assertTrue(
                (
                    out_p64_path
                    / "pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault-report.json"
                ).exists()
            )
        finally:
            for d in (out_master_path, out_p64_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_38_cli_backward_compat_verify_63pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                "-m",
                "fx3_recovery",
                "verify-63pillar-recovery",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 63)

    def test_39_cli_help_percent_escaping_no_argparse_crash(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in ("--help", "verify-64pillar-recovery", "verify-pillar64-recovery"):
            args = [subcmd] if subcmd == "--help" else [subcmd, "--help"]
            proc = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", *args],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)


# ---------------------------------------------------------------------------
# Programmatic Exhaustive Matrix Tests (>= 128 total unit tests across all 4 modes)
# ---------------------------------------------------------------------------


def _make_codec_shoe_format_test(codec: str, shoe_fmt: str) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            video_codec=codec,
            shoe_audio_set=shoe_fmt,
            reported_effective_shoe_audio_format=shoe_fmt,
            post_shoe_audio_set=shoe_fmt,
            proxy_recording_enabled=True,
            recording_fps=24,
            reported_effective_proxy_audio_spec=P352_FX3_PROXY_AUDIO_SPEC,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, (codec, shoe_fmt, rep.errors))

    return _test


def _make_preemption_matrix_test(
    jack_35mm: bool,
    mi_dev: str,
    handle_on: bool,
    dig_ana: str,
    inp_sel: str,
) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        st = compute_expected_shoe_audio_subject_recog_state(
            camera_model=P352_FX3_MODEL_NAME,
            fw_version=P352_FX3_FW_VERSION,
            shooting_domain="Movie",
            audio_recording_enabled=True,
            audio_rec_level=26,
            shoe_audio_set="48kHz/16bit 2ch",
            wind_noise_reduct="On",
            audio_out_timing="Live",
            audio_out_timing_menu_location=P352_AUDIO_OUT_TIMING_MENU_PATH,
            audio_level_display_menu_requested=False,
            monitoring_4ch_mix="CH1/CH2",
            hdmi_4ch_audio_out="CH1/CH2",
            video_codec="XAVC S 4K",
            recording_fps=24,
            proxy_recording_enabled=True,
            jack_35mm_mic_inserted=jack_35mm,
            mi_shoe_device=mi_dev,
            xlr_h1_handle_audio_on=handle_on,
            xlr_h1_digital_analog_switch=dig_ana,
            xlr_h1_input_select=inp_sel,
            fx3_limiter_configurable_requested=False,
            fx6_limiter_mode="Off",
            fx6_32bit_float_requested=False,
            face_eye_prior_in_af="On",
            face_eye_subject="Human",
            right_left_eye_select="Auto",
            face_eye_frame_disp="Off",
            face_memory_count=2,
            face_memory_exported_in_camset=False,
            regist_faces_priority="On",
            hdmi_info_display="Off",
            fx6_face_eye_detection_mode="Face/Eye Priority AF",
            fx6_saved_tracking_face_active=False,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            shoe_audio_set="48kHz/16bit 2ch",
            wind_noise_reduct="On",
            jack_35mm_mic_inserted=jack_35mm,
            mi_shoe_device=mi_dev,
            xlr_h1_handle_audio_on=handle_on,
            xlr_h1_digital_analog_switch=dig_ana,
            xlr_h1_input_select=inp_sel,
            reported_effective_audio_source=st["effective_audio_source"],
            reported_shoe_audio_set_grayed=st["shoe_audio_set_grayed"],
            reported_effective_shoe_audio_format=st["effective_shoe_audio_format"],
            reported_wind_noise_effective=st["wind_noise_effective"],
            face_memory_count=2,
            post_shoe_audio_set="48kHz/16bit 2ch",
            post_wind_noise_reduct="On",
            post_face_memory_count=2,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, (jack_35mm, mi_dev, handle_on, dig_ana, rep.errors))

    return _test


def _make_audio_rec_level_step_test(level: int) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            audio_rec_level=level,
            post_audio_rec_level=level,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, (level, rep.errors))

    return _test


def _make_4ch_monitoring_and_timing_test(mix: str, timing: str, hdmi_ch: str) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            monitoring_4ch_mix=mix,
            audio_out_timing=timing,
            hdmi_4ch_audio_out=hdmi_ch,
            post_monitoring_4ch_mix=mix,
            post_audio_out_timing=timing,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, (mix, timing, hdmi_ch, rep.errors))

    return _test


def _make_subject_domain_test(subject: str, domain: str) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        is_exposed = subject in P352_FX3_EXPOSED_SUBJECTS
        animal_movie_conflict = subject == "Animal" and domain != "Still"
        should_pass = is_exposed and not animal_movie_conflict
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            shooting_domain=domain,
            audio_recording_enabled=(domain != "S&Q"),
            proxy_recording_enabled=(domain == "Movie"),
            reported_effective_proxy_audio_spec=(
                P352_FX3_PROXY_AUDIO_SPEC if domain == "Movie" else "DISABLED"
            ),
            face_eye_subject=subject,
            reported_animal_eye_af_effective=(subject == "Animal" and domain == "Still"),
            reported_regist_faces_priority_enabled=(subject == "Human"),
            post_audio_recording_enabled=(domain != "S&Q"),
            post_face_eye_subject=subject,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertEqual(rep.passed, should_pass, (subject, domain, rep.errors))

    return _test


def _make_silent_target_reset_matrix_test(
    silent_mode: str,
    ap_drive: str,
    reset_action: str,
) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        is_reset = reset_action in ("Camera Settings Reset", "Initialize")
        eff_shutter = "Electronic Shutter" if silent_mode == "On" else "Auto"
        eff_sig = "Off" if silent_mode == "On" else "On"
        spec = build_default_safe_silent_target_bodydata_vault_spec(
            silent_mode=silent_mode,
            target_aperture_drive_in_af=ap_drive,
            target_auto_pixel_mapping="Off",
            reported_effective_shutter_type=eff_shutter,
            reported_effective_audio_signals=eff_sig,
            reset_action=reset_action,
            post_silent_mode="Off" if is_reset else silent_mode,
            post_aperture_drive_in_af=P352_APERTURE_DRIVE_DEFAULT if is_reset else ap_drive,
            post_auto_pixel_mapping=P352_AUTO_PIXEL_MAPPING_DEFAULT,
        )
        rep = evaluate_silent_target_bodydata_vault(spec)
        self.assertTrue(rep.passed, (silent_mode, ap_drive, reset_action, rep.errors))

    return _test


def _make_fx3_fw_and_battery_gate_test(cur_ver: str, battery: int, slot: str) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        needs_step = cur_ver in P352_FX3_LEGACY_PRE_STEPPING_VERSIONS
        should_pass = (not needs_step) and (battery >= P352_FX3_MIN_BATTERY_PCT) and (slot == "Slot 1")
        spec = build_default_safe_silent_target_bodydata_vault_spec(
            current_body_fw_version=cur_ver,
            target_body_fw_version="7.02",
            battery_percent=battery,
            bodydata_target_slot=slot,
        )
        rep = evaluate_silent_target_bodydata_vault(spec)
        self.assertEqual(rep.passed, should_pass, (cur_ver, battery, slot, rep.errors))

    return _test


def _make_fx6_limiter_mode_test(lim_mode: str) -> object:
    def _test(self: Phase352Pillar64VerifierTests) -> None:
        spec = build_default_safe_shoe_audio_subject_recog_vault_spec(
            camera_model=P352_FX6_DONOR_MODEL_NAME,
            fw_version=P352_FX6_DONOR_FW_VERSION,
            fx6_limiter_mode=lim_mode,
            reported_effective_audio_source="FX6_NATIVE_4CH_24BIT",
            reported_effective_shoe_audio_format="48kHz/24bit 4ch",
            reported_regist_faces_priority_enabled=False,
        )
        rep = evaluate_shoe_audio_subject_recog_vault(spec)
        self.assertTrue(rep.passed, (lim_mode, rep.errors))

    return _test


_idx = 40
for _codec in P352_FX3_MAIN_VIDEO_CODECS:
    for _sfmt in P352_SHOE_AUDIO_FORMATS:
        _cslug = _codec.replace(" ", "_").replace("-", "_")
        _fslug = _sfmt.replace("/", "_").replace(" ", "_")
        setattr(
            Phase352Pillar64VerifierTests,
            f"test_{_idx:03d}_codec_{_cslug}_shoe_{_fslug}",
            _make_codec_shoe_format_test(_codec, _sfmt),
        )
        _idx += 1

for _j35 in (False, True):
    for _dev in ("NONE", "XLR-H1", "ECM-B1M", "ECM-B10", "LEGACY_ANALOG_SHOE"):
        for _hon in (True, False):
            _sw = "ANALOG" if _dev == "XLR-H1" and _hon else "DIGITAL"
            setattr(
                Phase352Pillar64VerifierTests,
                f"test_{_idx:03d}_preempt_35mm_{int(_j35)}_{_dev.replace('-', '_')}_hon{int(_hon)}",
                _make_preemption_matrix_test(_j35, _dev, _hon, _sw, "IN1_IN2"),
            )
            _idx += 1

for _lvl in (0, 1, 5, 10, 15, 20, 26, 28, 30, 31):
    setattr(
        Phase352Pillar64VerifierTests,
        f"test_{_idx:03d}_audio_rec_level_{_lvl:02d}",
        _make_audio_rec_level_step_test(_lvl),
    )
    _idx += 1

for _mix in P352_4CH_AUDIO_MONITORING_MIXES:
    for _tmg in P352_AUDIO_OUT_TIMINGS:
        for _hch in P352_4CH_AUDIO_OUTPUT_CHANNELS:
            _mslug = _mix.replace("/", "_").replace("+", "p")
            _tslug = _tmg.replace(" ", "_")
            _hslug = _hch.replace("/", "_")
            setattr(
                Phase352Pillar64VerifierTests,
                f"test_{_idx:03d}_mon_{_mslug}_{_tslug}_hdmi_{_hslug}",
                _make_4ch_monitoring_and_timing_test(_mix, _tmg, _hch),
            )
            _idx += 1

for _sub in P352_ALL_SUBJECT_TOKENS:
    for _dom in ("Still", "Movie", "S&Q"):
        _sslug = _sub.replace("/", "_")
        _dslug = _dom.replace("&", "_")
        setattr(
            Phase352Pillar64VerifierTests,
            f"test_{_idx:03d}_subject_{_sslug}_domain_{_dslug}",
            _make_subject_domain_test(_sub, _dom),
        )
        _idx += 1

for _sm in ("Off", "On"):
    for _ap in P352_APERTURE_DRIVE_MODES:
        for _rst in ("None", "Camera Settings Reset", "Initialize"):
            _aslug = _ap.replace(" ", "_")
            _rslug = _rst.replace(" ", "_")
            setattr(
                Phase352Pillar64VerifierTests,
                f"test_{_idx:03d}_silent_{_sm}_ap_{_aslug}_rst_{_rslug}",
                _make_silent_target_reset_matrix_test(_sm, _ap, _rst),
            )
            _idx += 1

for _ver in ("1.01", "2.00", "2.02", "2.04", "2.05", "5.00", "6.02"):
    for _bat in (30, 50, 51, 80):
        _slt = "Slot 1" if _bat >= 50 else "Slot 2"
        setattr(
            Phase352Pillar64VerifierTests,
            f"test_{_idx:03d}_fw_gate_v{_ver.replace('.', '_')}_bat{_bat}_{_slt.replace(' ', '')}",
            _make_fx3_fw_and_battery_gate_test(_ver, _bat, _slt),
        )
        _idx += 1

for _lm in P352_FX6_LIMITER_MODES:
    setattr(
        Phase352Pillar64VerifierTests,
        f"test_{_idx:03d}_fx6_limiter_{_lm.replace(' ', '_').replace('-', 'neg')}",
        _make_fx6_limiter_mode_test(_lm),
    )
    _idx += 1


if __name__ == "__main__":
    unittest.main()
