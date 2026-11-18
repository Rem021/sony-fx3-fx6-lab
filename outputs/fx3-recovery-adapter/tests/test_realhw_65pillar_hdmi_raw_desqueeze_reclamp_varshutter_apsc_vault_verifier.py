"""Phase 355 (Pillar 65 & 65/65 Milestone) unit tests:
Wave-63 `Setup -> [External Output] -> [HDMI Output Settings]` 8 active Reset-resistant items
(with `[Color Gamut for RAW Output]` `_f 0x6bdc` removed since Ver. 2.00..7.02 and unified into
`[Log Shooting Setting] -> [Color Gamut]`): `[Rec. Media dur HDMI Output]` (`On` default vs
`Off(HDMI Only)` zero card writes, locked `On` in `S&Q`), `[Output Resolution]`,
`[4K Output Set.(HDMI Only)]` (10-bit only, dormant `24.00p 8bit`, `24.00p` mandatory reboot),
`[RAW Output]` (`4264x2408` 16-bit linear over HDMI Type-A, requires Movie + `Log != Off`,
`S&Q` locked `Off`), `[RAW Output Setting]` (`59.94p/50p/29.97p/25p/23.98p/24.00p`),
`[Time Code Output]` (hard gate for `[REC Control]`), `[REC Control]`, and `[4ch Audio Output]`
(`CH1/CH2` or `CH3/CH4`); Vault Firewall when `RAW=On` & `Rec. Media=On` (`Slot 1 EROFS`
card-write lockout, `S-Log3` lock, `Active` IBIS off, `HDMI Info. Display=Off`) vs FX6 dual
`12G-SDI RAW` (`4096x2160` / `3840x2160 "C"` capping HDMI `<= 1080p`) + `RAW(HDMI)` (`4240x2392`,
zero `24Hz`); `De-Squeeze Display` Ver. 7.00/7.02 (`Off/1.3x/1.5x/1.6x[1.65x]/2.0x` with ZERO
`1.8x` hits, 4 hard locks, 6 bypasses, `Focus Magnifier` & `Bright Monitoring` still allowed,
never touches recorded media vs FX6 SDI never desqueezed); `[REC Lamp]` 3-LED rear+top coupled
(`All On / Only Front Off / All Off`, ZERO `[Tally Light]`, Reset-resistant, `[Silent Mode]`
decoupled), `[Emphasized REC Display]` (Resettable, `0 px` clean-HDMI), `[Remain Shoot Display]`
(Reset-resistant), `[Auto Review]` (Still-only, Interval disabled, Reset-resistant), dormant
`[Var. Shutter]` (`0` `TYPE_MENU_ITEM_*HIGH_RES*` hits, `EOPNOTSUPP=95`) vs FX6 `ECS`
(`23.99..8000 Hz`), and `[APS-C S35 Shooting]` Reset-resistant erratum + 4K/DCI 4K lockout +
Still `5.1M` (`2768x1848`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
    MASTER_65_PILLAR_COUNT,
    MASTER_65_PILLAR_IDS,
    MASTER_65_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P355_AIRPLANE_MODE_FORCED_ON,
    P355_APSC_S35_ALLOWED_VIDEO_FORMATS,
    P355_APSC_S35_DEFAULT,
    P355_APSC_S35_LOCKED_OUT_VIDEO_FORMATS,
    P355_APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET,
    P355_APSC_S35_STILL_CROP_SIZE_16_9,
    P355_APSC_S35_STILL_CROP_SIZE_3_2,
    P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT,
    P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT,
    P355_BLOCKED_INVALID_PILLAR65A_SPEC,
    P355_BLOCKED_INVALID_PILLAR65B_SPEC,
    P355_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P355_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT,
    P355_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P355_CROSS_MODEL_FLASH_AUTHORIZED,
    P355_DESQUEEZE_1_65X_ENUM_SYMBOL,
    P355_DESQUEEZE_1_8X_HITS,
    P355_DONOR_FX3_APPFW_702_RELPATH,
    P355_DONOR_FX3_BACKUP_BIN_RELPATH,
    P355_DONOR_FX6_APPFW_601_RELPATH,
    P355_DONOR_FX6_UXC_EN_RELPATH,
    P355_DONOR_INSPECT_BUDGET_SECONDS,
    P355_EMMC_WRITES_AUTHORIZED,
    P355_ENV_CLEAN_ROOM_TEST,
    P355_EOPNOTSUPP_ERRNO,
    P355_FAST_CLI_BUDGET_SECONDS,
    P355_FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR,
    P355_FX3_DESQUEEZE_4_HARD_LOCKS,
    P355_FX3_DESQUEEZE_6_BYPASS_CONDITIONS,
    P355_FX3_DESQUEEZE_DISABLES_BRIGHT_MONITORING,
    P355_FX3_DESQUEEZE_DISABLES_FOCUS_MAGNIFIER,
    P355_FX3_FW_VERSION,
    P355_FX3_HAS_VAR_SHUTTER,
    P355_FX3_HDMI_4K_DORMANT_8BIT_MODE,
    P355_FX3_HDMI_4K_ONLY_10BIT_MODES,
    P355_FX3_HELPGUIDE_ID,
    P355_FX3_MODEL_ID,
    P355_FX3_MODEL_NAME,
    P355_FX3_RAW_BIT_DEPTH,
    P355_FX3_RAW_FPS_MODES,
    P355_FX3_RAW_RESOLUTION,
    P355_FX3_REAR_TOP_LED_COUPLED,
    P355_FX3_REC_LAMP_PHYSICAL_LEDS,
    P355_FX3_TALLY_LIGHT_MENU_COUNT,
    P355_FX3_TYPE_MENU_ITEM_HIGH_RES_HITS,
    P355_FX3_VER3_DESQUEEZE_MODES,
    P355_FX6_DONOR_FW_VERSION,
    P355_FX6_DONOR_MODEL_NAME,
    P355_FX6_ECS_FREQ_MAX_HZ,
    P355_FX6_ECS_FREQ_MIN_HZ,
    P355_FX6_HDMI_RAW_RESOLUTION,
    P355_FX6_HDMI_RAW_SUPPORTS_24HZ,
    P355_FX6_SDI_DESQUEEZE_PIXELS,
    P355_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P355_HDMI_OUTPUT_8_ACTIVE_ITEMS,
    P355_HDMI_OUTPUT_RESET_RESISTANT,
    P355_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P355_PILLAR_65A_SCENARIO_IDS,
    P355_PILLAR_65B_SCENARIO_IDS,
    P355_PINNED_FX3_BACKUP_BIN_SHA256,
    P355_RECORDED_MEDIA_DESQUEEZE_PIXELS,
    P355_REC_LAMP_DEFAULT,
    P355_SILENT_MODE_DISABLES_REC_LAMP,
    P355_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P355_STATUS_VERIFIED_65OF65_AGGREGATOR,
    P355_STATUS_VERIFIED_PILLAR65_SUITE,
    P355_STATUS_VERIFIED_PILLAR_65A,
    P355_STATUS_VERIFIED_PILLAR_65B,
    P355_WRITE_MUTATING_VAULT_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE355_MASTER_SCHEMA,
    PHASE355_PHASE_NUMBER,
    PHASE355_SCHEMA,
    PHASE355_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec,
    build_default_safe_hdmi_raw_media_vault_spec,
    compute_expected_desqueeze_reclamp_varshutter_apsc_vault_state,
    compute_expected_hdmi_raw_media_vault_state,
    evaluate_65pillar_recovery_master,
    evaluate_desqueeze_reclamp_varshutter_apsc_vault,
    evaluate_hdmi_raw_media_vault,
    evaluate_realhw_65pillar_recovery_master,
    inspect_phase355_donors_readonly,
    run_pillar65_standalone_suite,
    run_pillar65a_hdmi_raw_media_vault_6_scenario_suite,
    run_pillar65b_desqueeze_reclamp_varshutter_apsc_vault_6_scenario_suite,
    verify_65pillar_recovery,
    verify_65pillar_recovery_suite,
    verify_all_65_recovery_pillars,
    verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault,
    verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_vault,
)


def _wave63_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P355_DONOR_FX3_APPFW_702_RELPATH,
        P355_DONOR_FX6_APPFW_601_RELPATH,
        P355_DONOR_FX3_BACKUP_BIN_RELPATH,
        P355_DONOR_FX6_UXC_EN_RELPATH,
    )
    for rel in required:
        rel_n = rel[5:] if rel.startswith("work/") else rel
        if not any(
            r is not None and ((r / rel_n).exists() or (r.parent / rel).exists())
            for r in roots
        ):
            return False
    return True


def _compute_65a_from_spec(spec: fr.HdmiRawOutputMediaVaultSpec) -> dict[str, object]:
    return compute_expected_hdmi_raw_media_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        log_shooting=spec.log_shooting,
        pplut_active=spec.pplut_active,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        output_resolution=spec.output_resolution,
        hdmi_4k_output_setting=spec.hdmi_4k_output_setting,
        raw_output=spec.raw_output,
        raw_output_setting=spec.raw_output_setting,
        color_gamut_for_raw_out_requested=spec.color_gamut_for_raw_out_requested,
        time_code_output=spec.time_code_output,
        rec_control=spec.rec_control,
        audio_4ch_output=spec.audio_4ch_output,
        hdmi_info_display=spec.hdmi_info_display,
        steadyshot_mode=spec.steadyshot_mode,
        gamma_curve=spec.gamma_curve,
        fx6_raw_interface=spec.fx6_raw_interface,
        fx6_sdi_hdmi_rec_control=spec.fx6_sdi_hdmi_rec_control,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_65b_from_spec(spec: fr.DeSqueezeRecLampVarShutterApscVaultSpec) -> dict[str, object]:
    return compute_expected_desqueeze_reclamp_varshutter_apsc_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        de_squeeze_display=spec.de_squeeze_display,
        focus_mode=spec.focus_mode,
        focus_area=spec.focus_area,
        steadyshot_mode=spec.steadyshot_mode,
        face_priority_in_multi_metering=spec.face_priority_in_multi_metering,
        log_shooting=spec.log_shooting,
        raw_output=spec.raw_output,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        still_movie_key_recording=spec.still_movie_key_recording,
        remote_shooting_active=spec.remote_shooting_active,
        photo_capture_active=spec.photo_capture_active,
        focus_magnifier_requested=spec.focus_magnifier_requested,
        bright_monitoring_requested=spec.bright_monitoring_requested,
        rec_lamp=spec.rec_lamp,
        tally_light_menu_requested=spec.tally_light_menu_requested,
        rec_lamp_only_one_requested=spec.rec_lamp_only_one_requested,
        silent_mode=spec.silent_mode,
        emphasized_rec_display=spec.emphasized_rec_display,
        hdmi_info_display=spec.hdmi_info_display,
        remain_shoot_display=spec.remain_shoot_display,
        auto_review=spec.auto_review,
        interval_shooting_active=spec.interval_shooting_active,
        var_shutter_requested=spec.var_shutter_requested,
        anti_flicker_shoot=spec.anti_flicker_shoot,
        shutter_type=spec.shutter_type,
        bulb_active=spec.bulb_active,
        fx6_shutter_mode=spec.fx6_shutter_mode,
        fx6_ecs_frequency_hz=spec.fx6_ecs_frequency_hz,
        apsc_s35_shooting=spec.apsc_s35_shooting,
        video_codec=spec.video_codec,
        recording_fps=spec.recording_fps,
        still_aspect_ratio=spec.still_aspect_ratio,
        still_image_size_requested=spec.still_image_size_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _run_cli(*args: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ADAPTER_ROOT)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-B", "-m", "fx3_recovery", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class Phase355Pillar65VerifierTests(unittest.TestCase):
    """Phase 355 Pillar 65 & 65/65 Master Recovery Verifier unit tests."""

    # ------------------------------------------------------------------
    # 1. Constants, Safety Redlines, Package Exports & Non-Shadowing
    # ------------------------------------------------------------------

    def test_001_phase355_metadata_and_schema_constants(self) -> None:
        self.assertEqual(PHASE355_PHASE_NUMBER, 355)
        self.assertEqual(PHASE355_VERSION, "1.0.0")
        self.assertIn("65pillar", PHASE355_SCHEMA)
        self.assertIn("65pillar", PHASE355_MASTER_SCHEMA)
        self.assertEqual(MASTER_65_PILLAR_COUNT, 65)
        self.assertEqual(len(MASTER_65_PILLAR_SPECS), 65)
        self.assertEqual(len(MASTER_65_PILLAR_IDS), 65)
        self.assertEqual(
            MASTER_65_PILLAR_IDS[-1],
            "pillar65_hdmi_raw_desqueeze_reclamp_varshutter_apsc_vault",
        )

    def test_002_safety_flags_and_no_hardware_attach_invariants(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
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
        self.assertFalse(BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertFalse(P355_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED)
        self.assertFalse(P355_CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(P355_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(P355_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P355_OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertTrue(P355_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P355_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P355_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)

    def test_003_package_exports_do_not_shadow_pillar64_symbols(self) -> None:
        self.assertEqual(fr.MASTER_64_PILLAR_COUNT, 64)
        self.assertEqual(fr.MASTER_65_PILLAR_COUNT, 65)
        self.assertTrue(hasattr(fr, "verify_64pillar_recovery"))
        self.assertTrue(hasattr(fr, "verify_65pillar_recovery"))
        self.assertTrue(hasattr(fr, "evaluate_realhw_64pillar_recovery_master"))
        self.assertTrue(hasattr(fr, "evaluate_realhw_65pillar_recovery_master"))
        self.assertTrue(hasattr(fr, "verify_all_65_recovery_pillars"))
        self.assertEqual(len(fr.MASTER_64_PILLAR_IDS), 64)
        self.assertEqual(len(fr.MASTER_65_PILLAR_IDS), 65)
        self.assertEqual(fr.MASTER_65_PILLAR_IDS[:64], fr.MASTER_64_PILLAR_IDS)
        self.assertIn("verify_65pillar_recovery", fr.__all__)
        self.assertIn("verify_64pillar_recovery", fr.__all__)
        self.assertIn("verify_all_65_recovery_pillars", fr.__all__)

    def test_004_wave63_empirical_constants_grounding(self) -> None:
        self.assertEqual(P355_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P355_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P355_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P355_FX3_FW_VERSION, "7.02")
        self.assertEqual(P355_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P355_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(len(P355_HDMI_OUTPUT_8_ACTIVE_ITEMS), 8)
        self.assertTrue(P355_HDMI_OUTPUT_RESET_RESISTANT)
        self.assertEqual(P355_FX3_RAW_RESOLUTION, "4264x2408")
        self.assertEqual(P355_FX3_RAW_BIT_DEPTH, 16)
        self.assertEqual(len(P355_FX3_RAW_FPS_MODES), 6)
        self.assertEqual(P355_FX3_HDMI_4K_DORMANT_8BIT_MODE, "24.00p 8bit")
        self.assertEqual(P355_FX6_HDMI_RAW_RESOLUTION, "4240x2392")
        self.assertFalse(P355_FX6_HDMI_RAW_SUPPORTS_24HZ)
        self.assertEqual(P355_FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR, 1.65)
        self.assertEqual(P355_DESQUEEZE_1_65X_ENUM_SYMBOL, "VAL_DE_SQUEEZE_DISP_1_65X")
        self.assertEqual(P355_DESQUEEZE_1_8X_HITS, 0)
        self.assertEqual(len(P355_FX3_DESQUEEZE_4_HARD_LOCKS), 4)
        self.assertEqual(len(P355_FX3_DESQUEEZE_6_BYPASS_CONDITIONS), 6)
        self.assertFalse(P355_FX3_DESQUEEZE_DISABLES_FOCUS_MAGNIFIER)
        self.assertFalse(P355_FX3_DESQUEEZE_DISABLES_BRIGHT_MONITORING)
        self.assertEqual(P355_FX6_SDI_DESQUEEZE_PIXELS, 0)
        self.assertEqual(P355_RECORDED_MEDIA_DESQUEEZE_PIXELS, 0)
        self.assertEqual(P355_FX3_REC_LAMP_PHYSICAL_LEDS, 3)
        self.assertTrue(P355_FX3_REAR_TOP_LED_COUPLED)
        self.assertEqual(P355_FX3_TALLY_LIGHT_MENU_COUNT, 0)
        self.assertFalse(P355_SILENT_MODE_DISABLES_REC_LAMP)
        self.assertFalse(P355_FX3_HAS_VAR_SHUTTER)
        self.assertEqual(P355_FX3_TYPE_MENU_ITEM_HIGH_RES_HITS, 0)
        self.assertEqual(P355_FX6_ECS_FREQ_MIN_HZ, 23.99)
        self.assertEqual(P355_FX6_ECS_FREQ_MAX_HZ, 8000.0)
        self.assertFalse(P355_APSC_S35_RESETTABLE_BY_CAMERA_SETTINGS_RESET)
        self.assertEqual(P355_APSC_S35_STILL_CROP_SIZE_3_2, "M: 5.1M (2768x1848)")
        self.assertEqual(P355_APSC_S35_STILL_CROP_SIZE_16_9, "M: 4.3M (2768x1560)")

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY 17-Donor Inspection & All 4 Execution Modes
    # ------------------------------------------------------------------

    def test_005_donor_inspection_force_clean_room_argument(self) -> None:
        snap = inspect_phase355_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, P355_DONOR_INSPECT_BUDGET_SECONDS)

    def test_006_donor_inspection_env_fx3_clean_room_test_mode(self) -> None:
        with patch.dict(os.environ, {P355_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase355_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)

    def test_007_donor_inspection_env_fx3_fx6_force_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase355_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)

    def test_008_donor_inspection_mocked_donorless_work_root_none(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P355_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                snap = inspect_phase355_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)

    def test_009_donor_inspection_normal_mode_matches_environment(self) -> None:
        snap = inspect_phase355_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        if (
            not os.environ.get(P355_ENV_CLEAN_ROOM_TEST)
            and not os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
            and _wave63_donors_present()
        ):
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        fx3_bk = [a for a in snap.artifacts if a.artifact_id == "fx3_backup_bin"][0]
        self.assertEqual(fx3_bk.digest_sha256, P355_PINNED_FX3_BACKUP_BIN_SHA256)

    def test_010_donor_inspection_strictly_pins_17_artifacts_and_zero_raw_leak(self) -> None:
        snap = inspect_phase355_donors_readonly(force_clean_room=True)
        self.assertEqual(len(snap.artifacts), 17)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)
            self.assertGreater(art.total_bytes, 0)

    # ------------------------------------------------------------------
    # 3. Pillar 65A: HDMI Output 8 Active Items, 4264x2408 RAW & Slot 1 Vault
    # ------------------------------------------------------------------

    def test_011_pillar65a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec()
        report = evaluate_hdmi_raw_media_vault(spec)
        st = _compute_65a_from_spec(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P355_STATUS_VERIFIED_PILLAR_65A)
        self.assertIsNone(report.block_code)
        self.assertFalse(st["card_write_pathway_active"])
        self.assertTrue(report.hdmi_8_items_raw_16bit_and_coupling_verified)
        self.assertTrue(report.hdmi_4k_10bit_gamut_removal_and_reset_verified)

    def test_012_pillar65a_rec_media_on_with_raw_on_keeps_card_write_pathway_active(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            hdmi_info_display="Off",
            steadyshot_mode="Standard",
            gamma_curve="S-Log3",
            reported_effective_rec_media="On",
            reported_effective_raw_output="On",
            reported_effective_gamma="S-Log3",
            reported_effective_steadyshot="Standard",
            reported_effective_hdmi_info_display="Off",
            reported_card_write_pathway_active=True,
            post_rec_media_dur_hdmi_output="On",
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertTrue(report.passed)
        self.assertTrue(_compute_65a_from_spec(spec)["card_write_pathway_active"])

    def test_013_pillar65a_raw_on_rec_media_on_rejects_false_zero_card_write_claim(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            reported_effective_rec_media="On",
            reported_card_write_pathway_active=False,
            post_rec_media_dur_hdmi_output="On",
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_014_pillar65a_raw_on_rec_media_on_blocks_slot1_card_write_with_erofs(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            reported_effective_rec_media="On",
            reported_card_write_pathway_active=True,
            post_rec_media_dur_hdmi_output="On",
            requested_vault_slot=1,
            requested_vault_action="CARD_WRITE_XAVC_REC",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertTrue(report.passed)

    def test_015_pillar65a_mutating_action_blocked_readonly_even_when_slot2_requested(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            reported_effective_rec_media="On",
            reported_card_write_pathway_active=True,
            post_rec_media_dur_hdmi_output="On",
            requested_vault_slot=2,
            slot1_holds_tier0_vault=True,
            requested_vault_action="CARD_WRITE_XAVC_REC",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertTrue(report.passed)

    def test_016_pillar65a_rejects_unblocked_slot1_write_under_raw_rec_media_on(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            reported_effective_rec_media="On",
            reported_card_write_pathway_active=True,
            post_rec_media_dur_hdmi_output="On",
            requested_vault_slot=1,
            requested_vault_action="CARD_WRITE_XAVC_REC",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_017_pillar65a_off_hdmi_only_zero_card_writes_succeeds(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_4k_output_setting="23.98p 10bit",
            raw_output="On",
            hdmi_info_display="On",
            steadyshot_mode="Active",
            gamma_curve="S-Log2",
            reported_effective_steadyshot="Off",
            post_hdmi_4k_output_setting="23.98p 10bit",
        )
        expected = _compute_65a_from_spec(spec)
        self.assertFalse(expected["card_write_pathway_active"])
        self.assertEqual(expected["effective_gamma"], "S-Log3")
        self.assertEqual(expected["effective_steadyshot"], "Off")
        self.assertEqual(expected["effective_hdmi_info_display"], "Off")
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertTrue(report.passed)

    def test_018_pillar65a_rejects_active_ibis_or_non_slog3_under_raw_output(self) -> None:
        bad_ibis = build_default_safe_hdmi_raw_media_vault_spec(
            steadyshot_mode="Active",
            reported_effective_steadyshot="Active",
        )
        r1 = evaluate_hdmi_raw_media_vault(bad_ibis)
        self.assertFalse(r1.passed)
        self.assertEqual(r1.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

        bad_gamma = build_default_safe_hdmi_raw_media_vault_spec(
            gamma_curve="Still",
            reported_effective_gamma="Still",
        )
        r2 = evaluate_hdmi_raw_media_vault(bad_gamma)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_019_pillar65a_rejects_hdmi_info_display_on_leaking_under_raw(self) -> None:
        bad_osd = build_default_safe_hdmi_raw_media_vault_spec(
            hdmi_info_display="On",
            reported_effective_hdmi_info_display="On",
        )
        report = evaluate_hdmi_raw_media_vault(bad_osd)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_020_pillar65a_snq_locks_rec_media_on_and_raw_off_with_eopnotsupp(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            shooting_domain="S&Q",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            raw_output="On",
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["sq_rec_media_errno"], P355_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["sq_raw_errno"], P355_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["effective_rec_media"], "On")
        self.assertEqual(st["effective_raw_output"], "Off")
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(r.passed)
        self.assertEqual(r.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_021_pillar65a_snq_without_eopnotsupp_fails_closed(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            shooting_domain="S&Q",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            raw_output="On",
            reported_sq_rec_media_errno=None,
            reported_sq_raw_errno=None,
            reported_effective_rec_media="Off(HDMI Only)",
            reported_effective_raw_output="On",
        )
        report = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_022_pillar65a_raw_output_requires_movie_and_log_not_off(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            log_shooting="Off",
            raw_output="On",
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["raw_prereq_errno"], P355_EOPNOTSUPP_ERRNO)
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(r.passed)
        self.assertEqual(r.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_023_pillar65a_removed_color_gamut_for_raw_output_must_reject(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            color_gamut_for_raw_out_requested=True,
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["removed_raw_gamut_errno"], P355_EOPNOTSUPP_ERRNO)
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(r.passed)
        self.assertEqual(r.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_024_pillar65a_dormant_2400p_8bit_4k_hdmi_only_must_reject(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            hdmi_4k_output_setting=P355_FX3_HDMI_4K_DORMANT_8BIT_MODE,
            post_hdmi_4k_output_setting=P355_FX3_HDMI_4K_DORMANT_8BIT_MODE,
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["dormant_4k_8bit_errno"], P355_EOPNOTSUPP_ERRNO)
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(r.passed)
        self.assertEqual(r.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_025_pillar65a_timecode_output_gates_rec_control(self) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            time_code_output="Off",
            rec_control="On",
            post_time_code_output="Off",
            post_rec_control="On",
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["rec_control_errno"], P355_EOPNOTSUPP_ERRNO)
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertFalse(r.passed)
        self.assertEqual(r.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_026_pillar65a_hdmi_output_settings_resist_camera_settings_reset_but_clear_on_init(self) -> None:
        spec_keep = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            output_resolution="1080p",
            hdmi_4k_output_setting="23.98p 10bit",
            raw_output="On",
            time_code_output="On",
            rec_control="On",
            reset_action="Camera Settings Reset",
        )
        res_keep = _compute_65a_from_spec(spec_keep)
        self.assertEqual(res_keep["post_rec_media_dur_hdmi_output"], "Off(HDMI Only)")
        self.assertEqual(res_keep["post_raw_output"], "On")
        self.assertEqual(res_keep["post_rec_control"], "On")

        spec_init = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            output_resolution="1080p",
            hdmi_4k_output_setting="23.98p 10bit",
            raw_output="On",
            time_code_output="On",
            rec_control="On",
            reset_action="Initialize",
        )
        res_init = _compute_65a_from_spec(spec_init)
        self.assertEqual(res_init["post_rec_media_dur_hdmi_output"], "On")
        self.assertEqual(res_init["post_raw_output"], "Off")
        self.assertEqual(res_init["post_rec_control"], "Off")

    def test_027_pillar65a_rejects_post_reset_hdmi_drift(self) -> None:
        bad = build_default_safe_hdmi_raw_media_vault_spec(
            reset_action="Camera Settings Reset",
            post_raw_output="Off",
            post_rec_media_dur_hdmi_output="On",
        )
        report = evaluate_hdmi_raw_media_vault(bad)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_028_pillar65a_fx6_12g_sdi_raw_caps_hdmi_1080p_and_raw_hdmi_rejects_24hz(self) -> None:
        fx6_sdi = build_default_safe_hdmi_raw_media_vault_spec(
            camera_model=P355_FX6_DONOR_MODEL_NAME,
            fw_version=P355_FX6_DONOR_FW_VERSION,
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            fx6_raw_interface="12G-SDI_RAW",
            fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
            reported_effective_rec_media="On",
            reported_effective_raw_output="On",
            reported_card_write_pathway_active=False,
            reported_fx6_hdmi_capped_1080p=True,
            reported_fx6_hdmi_raw_res="N/A",
            reported_fx6_hdmi_raw_24hz_supported=False,
            post_rec_media_dur_hdmi_output="On",
        )
        self.assertTrue(evaluate_hdmi_raw_media_vault(fx6_sdi).passed)

        fx6_hdmi_raw = build_default_safe_hdmi_raw_media_vault_spec(
            camera_model=P355_FX6_DONOR_MODEL_NAME,
            fw_version=P355_FX6_DONOR_FW_VERSION,
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            fx6_raw_interface="RAW_HDMI",
            fx6_sdi_hdmi_rec_control="Parallel Rec",
            reported_effective_rec_media="On",
            reported_effective_raw_output="On",
            reported_card_write_pathway_active=True,
            reported_fx6_hdmi_capped_1080p=False,
            reported_fx6_hdmi_raw_res=P355_FX6_HDMI_RAW_RESOLUTION,
            reported_fx6_hdmi_raw_24hz_supported=False,
            post_rec_media_dur_hdmi_output="On",
        )
        self.assertTrue(evaluate_hdmi_raw_media_vault(fx6_hdmi_raw).passed)

        fx6_hdmi_bad_24 = build_default_safe_hdmi_raw_media_vault_spec(
            camera_model=P355_FX6_DONOR_MODEL_NAME,
            fw_version=P355_FX6_DONOR_FW_VERSION,
            rec_media_dur_hdmi_output="On",
            raw_output="On",
            fx6_raw_interface="RAW_HDMI",
            reported_fx6_hdmi_raw_res=P355_FX6_HDMI_RAW_RESOLUTION,
            reported_fx6_hdmi_raw_24hz_supported=True,
            post_rec_media_dur_hdmi_output="On",
        )
        r_bad = evaluate_hdmi_raw_media_vault(fx6_hdmi_bad_24)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_HDMI_RAW_OR_MEDIA_VAULT_DRIFT)

    def test_029_pillar65a_rejects_persistent_overlay_or_backup_h0_h3_mismatch(self) -> None:
        bad_overlay = build_default_safe_hdmi_raw_media_vault_spec(overlay_dir="/nflasha/p1")
        r1 = evaluate_hdmi_raw_media_vault(bad_overlay)
        self.assertFalse(r1.passed)
        self.assertEqual(r1.block_code, P355_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = build_default_safe_hdmi_raw_media_vault_spec(backup_bin_h3_sha256="0" * 64)
        r2 = evaluate_hdmi_raw_media_vault(bad_h3)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.block_code, P355_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_030_pillar65a_rejects_slot1_write_mutation_when_unblocked(self) -> None:
        for action in P355_WRITE_MUTATING_VAULT_ACTIONS:
            spec = build_default_safe_hdmi_raw_media_vault_spec(
                requested_vault_slot=1,
                requested_vault_action=action,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
            r = evaluate_hdmi_raw_media_vault(spec)
            self.assertFalse(r.passed, f"action={action} should fail if allowed")
            self.assertEqual(r.block_code, P355_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    # ------------------------------------------------------------------
    # 4. Pillar 65B: De-Squeeze 1.6x[1.65x], REC Lamp, Dormant Var. Shutter & APS-C
    # ------------------------------------------------------------------

    def test_031_pillar65b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec()
        report = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        st = _compute_65b_from_spec(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P355_STATUS_VERIFIED_PILLAR_65B)
        self.assertIsNone(report.block_code)
        self.assertEqual(st["effective_stretch_factor"], 1.65)
        self.assertTrue(st["effective_hdmi_desqueezed"])
        self.assertEqual(report.recorded_media_desqueeze_pixels, 0)
        self.assertEqual(report.fx6_sdi_desqueeze_pixels, 0)

    def test_032_pillar65b_rejects_1_8x_desqueeze_spoofing(self) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display="1.8x",
            post_de_squeeze_display="1.8x",
        )
        st = _compute_65b_from_spec(spec)
        self.assertEqual(st["desqueeze_errno"], P355_EOPNOTSUPP_ERRNO)
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT)

    def test_033_pillar65b_rejects_1_6x_factor_drift_away_from_1_65x(self) -> None:
        bad = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display="1.6x",
            reported_stretch_factor=1.60,
        )
        report = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad)
        self.assertFalse(report.passed)
        self.assertEqual(report.block_code, P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT)

    def test_034_pillar65b_enforces_4_hard_locks_when_desqueeze_active(self) -> None:
        for field_name, bad_val in (
            ("reported_effective_focus_mode", "AF-C"),
            ("reported_effective_focus_area", "Spot"),
            ("reported_effective_steadyshot", "Standard"),
            ("reported_effective_face_priority", "On"),
        ):
            spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(**{field_name: bad_val})
            r = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
            self.assertFalse(r.passed, f"{field_name}={bad_val} should fail")
            self.assertEqual(r.block_code, P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT)

    def test_035_pillar65b_focus_magnifier_and_bright_monitoring_remain_allowed(self) -> None:
        bad_fm = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            focus_magnifier_requested=True,
            reported_focus_magnifier_allowed=False,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_fm).passed)

        bad_bm = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            bright_monitoring_requested=True,
            focus_magnifier_requested=False,
            reported_bright_monitoring_allowed=False,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_bm).passed)

    def test_036_pillar65b_ver3_firmware_lacks_1_5x_and_1_6x_modes(self) -> None:
        self.assertNotIn("1.5x", P355_FX3_VER3_DESQUEEZE_MODES)
        self.assertNotIn("1.6x", P355_FX3_VER3_DESQUEEZE_MODES)
        spec_v3 = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            fw_version="3.00",
            de_squeeze_display="1.3x",
            reported_stretch_factor=1.3,
            post_de_squeeze_display="1.3x",
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec_v3).passed)

    def test_037_pillar65b_zero_recorded_media_and_fx6_sdi_desqueeze_pixels(self) -> None:
        bad_media = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            recorded_media_desqueeze_pixels=1024,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_media).passed)

        bad_sdi = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            fx6_sdi_desqueeze_pixels=1920,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_sdi).passed)

    def test_038_pillar65b_rec_lamp_coupling_and_silent_mode_decoupling(self) -> None:
        all_on = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            rec_lamp="All On",
            silent_mode="On",
            reported_front_led_on=True,
            reported_rear_led_on=True,
            reported_top_rec_ring_on=True,
            post_rec_lamp="All On",
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(all_on).passed)

        bad_silent = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            rec_lamp="All On",
            silent_mode="On",
            reported_front_led_on=False,
            reported_rear_led_on=False,
            reported_top_rec_ring_on=False,
            post_rec_lamp="All On",
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_silent)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT)

    def test_039_pillar65b_rec_lamp_rear_top_hardware_coupling_invariant(self) -> None:
        decoupled_leds = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            rec_lamp="Only Front Off",
            reported_front_led_on=False,
            reported_rear_led_on=True,
            reported_top_rec_ring_on=False,
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(decoupled_leds)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_DESQUEEZE_OR_REC_LAMP_DRIFT)

    def test_040_pillar65b_zero_tally_light_and_dormant_only_one_rejects_without_errno(self) -> None:
        bad_tally = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            tally_light_menu_requested=True,
            reported_tally_menu_errno=None,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_tally).passed)

        bad_only_one = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            rec_lamp_only_one_requested=True,
            reported_only_one_led_errno=None,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_only_one).passed)

    def test_041_pillar65b_emphasized_rec_clean_hdmi_and_auto_review_interval_disabled(self) -> None:
        bad_border = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            hdmi_red_border_clean_feed_leak_pixels=48,
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_border).passed)

        bad_auto_rev = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            interval_shooting_active=True,
            auto_review="5 Sec",
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_auto_review="5 Sec",
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_auto_rev)
        self.assertFalse(r_bad.passed)

    def test_042_pillar65b_dormant_var_shutter_enforces_eopnotsupp_vs_fx6_ecs(self) -> None:
        spec_dormant = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            var_shutter_requested=True,
        )
        st = _compute_65b_from_spec(spec_dormant)
        self.assertEqual(st["var_shutter_errno"], P355_EOPNOTSUPP_ERRNO)
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec_dormant)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT)

    def test_043_pillar65b_anti_flicker_shoot_mechanical_shutter_still_only_gate(self) -> None:
        ok_still_mech = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            silent_mode="Off",
            anti_flicker_shoot="On",
            shutter_type="Mechanical Shutter",
            bulb_active=False,
            reported_anti_flicker_effective=True,
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_anti_flicker_shoot="On",
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(ok_still_mech).passed)

        bad_elec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            silent_mode="Off",
            anti_flicker_shoot="On",
            shutter_type="Electronic Shutter",
            bulb_active=False,
            reported_anti_flicker_effective=True,
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_anti_flicker_shoot="On",
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_elec)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT)

    def test_044_pillar65b_apsc_s35_reset_resistant_erratum_and_4k_lockout_5_1mp_still(self) -> None:
        ok_apsc = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            apsc_s35_shooting="On",
            video_codec="XAVC S-I HD",
            recording_fps=60,
            reset_action="Camera Settings Reset",
            post_de_squeeze_display="1.6x",
            post_rec_lamp="Only Front Off",
            post_emphasized_rec_display="On",
            post_remain_shoot_display="Always Display",
            post_auto_review="2 Sec",
            post_anti_flicker_shoot="Off",
            post_apsc_s35_shooting="On",
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(ok_apsc).passed)

        # Spoofing Wave 42 erratum: resetting APS-C S35 to Off under Camera Settings Reset must FAIL!
        bad_reset = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            apsc_s35_shooting="On",
            video_codec="XAVC S HD",
            reset_action="Camera Settings Reset",
            post_apsc_s35_shooting="Off",
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_reset)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT)

    def test_045_pillar65b_apsc_s35_still_5_1mp_size_validation(self) -> None:
        bad_still = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            apsc_s35_shooting="On",
            still_aspect_ratio="3:2",
            still_image_size_requested="L: 12M (4240x2832)",
            reported_still_size_errno=None,
            reported_effective_still_size="L: 12M (4240x2832)",
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_apsc_s35_shooting="On",
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_still)
        self.assertFalse(r_bad.passed)
        self.assertEqual(r_bad.block_code, P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT)

    # ------------------------------------------------------------------
    # 5. Standalone Suites, Master 65/65 Aggregator & Determinism
    # ------------------------------------------------------------------

    def test_046_single_shot_combined_verifier_both_variants_pass(self) -> None:
        r1 = verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_and_vault(force_clean_room=True)
        r2 = verify_hdmi_raw_desqueeze_rec_lamp_varshutter_apsc_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P355_STATUS_VERIFIED_PILLAR65_SUITE)
        self.assertEqual(r2.status, P355_STATUS_VERIFIED_PILLAR65_SUITE)

    def test_047_pillar65a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar65a_hdmi_raw_media_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P355_PILLAR_65A_SCENARIO_IDS,
        )

    def test_048_pillar65b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar65b_desqueeze_reclamp_varshutter_apsc_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P355_PILLAR_65B_SCENARIO_IDS,
        )

    def test_049_standalone_suite_all_4_modes_pass(self) -> None:
        r_normal = run_pillar65_standalone_suite()
        r_cr = run_pillar65_standalone_suite(force_clean_room=True)
        with patch.dict(os.environ, {P355_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            r_env1 = run_pillar65_standalone_suite()
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r_env2 = run_pillar65_standalone_suite()
        with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
            clean_env = os.environ.copy()
            clean_env.pop(P355_ENV_CLEAN_ROOM_TEST, None)
            clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            with patch.dict(os.environ, clean_env, clear=True):
                r_nomock = run_pillar65_standalone_suite()
        for r in (r_normal, r_cr, r_env1, r_env2, r_nomock):
            self.assertTrue(r.all_passed)
            self.assertEqual(r.status, P355_STATUS_VERIFIED_PILLAR65_SUITE)
            self.assertEqual(r.pillar_65a_hdmi_raw_16bit_rec_media_vault.scenarios_passed, 6)
            self.assertEqual(r.pillar_65b_desqueeze_reclamp_varshutter_apsc_vault.scenarios_passed, 6)
            self.assertLess(r.elapsed_seconds, P355_FAST_CLI_BUDGET_SECONDS)

    def test_050_master_65_recovery_clean_room_mode_passes_under_budget(self) -> None:
        m = verify_all_65_recovery_pillars(force_clean_room=True)
        self.assertTrue(m.all_passed)
        self.assertEqual(m.status, P355_STATUS_VERIFIED_65OF65_AGGREGATOR)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillar_count, 65)
        self.assertEqual(m.pillars_passed, 65)
        self.assertEqual(m.failed_pillars, ())
        self.assertTrue(m.under_6s_budget)
        self.assertTrue(m.under_2_5s_fast_cli_budget)
        self.assertLess(m.elapsed_seconds, P355_FAST_CLI_BUDGET_SECONDS)

    def test_051_master_65_recovery_normal_mode_and_aliases_match(self) -> None:
        m1 = evaluate_realhw_65pillar_recovery_master()
        m2 = evaluate_65pillar_recovery_master()
        m3 = verify_65pillar_recovery_suite()
        m4 = verify_65pillar_recovery()
        for m in (m1, m2, m3, m4):
            self.assertTrue(m.all_passed)
            self.assertEqual(m.pillars_passed, 65)
            self.assertEqual(m.pillar_count, 65)
            self.assertEqual(m.master_65pillar_sha256, m1.master_65pillar_sha256)
            self.assertEqual(m.fx3_desqueeze_1_8x_hits, 0)
            self.assertEqual(m.fx3_type_menu_item_high_res_hits, 0)
            self.assertFalse(m.apsc_s35_resettable_by_camera_settings_reset)
            self.assertFalse(m.fx3_has_var_shutter)
            self.assertFalse(m.fx3_has_builtin_evf)
            self.assertFalse(m.overall_ready_for_hardware_attach)

    def test_052_master_65_recovery_donorless_work_root_none_passes(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P355_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                m = verify_all_65_recovery_pillars()
        self.assertTrue(m.all_passed)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillars_passed, 65)
        self.assertEqual(m.pillar_count, 65)

    def test_053_master_65_recovery_env_clean_room_modes_pass(self) -> None:
        for env_key in (P355_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with patch.dict(os.environ, {env_key: "1"}, clear=False):
                m = verify_all_65_recovery_pillars()
                self.assertTrue(m.all_passed)
                self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(m.pillars_passed, 65)

    def test_054_cli_help_percent_escape_and_subcommands(self) -> None:
        res_top = _run_cli("--help")
        self.assertEqual(res_top.returncode, 0, res_top.stderr)
        for cmd in (
            "verify-pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault",
            "verify-pillar65-recovery",
            "verify-65pillar-recovery",
        ):
            self.assertIn(cmd, res_top.stdout)
            res_sub = _run_cli(cmd, "--help")
            self.assertEqual(res_sub.returncode, 0, f"{cmd} --help failed: {res_sub.stderr}")

    def test_055_cli_json_and_out_execution_both_modes(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests) as td:
            out_p65 = Path(td) / "out_p65"
            out_m65 = Path(td) / "out_m65"
            res_p65 = _run_cli("verify-pillar65-recovery", "--force-clean-room", "--json", "--out", str(out_p65))
            self.assertEqual(res_p65.returncode, 0, res_p65.stderr)
            p65_data = json.loads(res_p65.stdout)
            self.assertTrue(p65_data["all_passed"])
            self.assertEqual(p65_data["status"], P355_STATUS_VERIFIED_PILLAR65_SUITE)
            self.assertTrue(
                (out_p65 / "pillar65-hdmi-raw-desqueeze-reclamp-varshutter-apsc-vault-report.json").exists()
            )

            res_m65 = _run_cli("verify-65pillar-recovery", "--force-clean-room", "--json", "--out", str(out_m65))
            self.assertEqual(res_m65.returncode, 0, res_m65.stderr)
            m65_data = json.loads(res_m65.stdout)
            self.assertTrue(m65_data["all_passed"])
            self.assertEqual(m65_data["pillar_count"], 65)
            self.assertEqual(m65_data["pillars_passed"], 65)
            self.assertTrue((out_m65 / "65pillar-recovery-master-report.json").exists())

    def test_056_master_65_pillar_sha256_matches_clean_room_deterministic_value(self) -> None:
        m1 = verify_all_65_recovery_pillars(force_clean_room=True)
        m2 = verify_all_65_recovery_pillars(force_clean_room=True)
        self.assertEqual(m1.master_65pillar_sha256, m2.master_65pillar_sha256)
        self.assertEqual(len(m1.master_65pillar_sha256), 64)


def _make_desqueeze_mode_test(mode: str, expected_factor: float):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display=mode,
            reported_stretch_factor=expected_factor,
            reported_effective_hdmi_desqueezed=(mode != "Off"),
            post_de_squeeze_display=mode,
        )
        expected = _compute_65b_from_spec(spec)
        self.assertEqual(expected["effective_stretch_factor"], expected_factor)
        is_active = mode != "Off"
        self.assertEqual(expected["effective_hdmi_desqueezed"], is_active)
        self.assertFalse(expected["recorded_media_desqueezed"])
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec).passed)
    return _test


def _make_desqueeze_bypass_test(bypass_name: str, overrides: dict[str, object]):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display="1.6x",
            reported_stretch_factor=1.65,
            reported_effective_hdmi_desqueezed=False,
            **overrides,
        )
        r_ok = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        self.assertTrue(r_ok.passed, f"bypass {bypass_name} failed: {r_ok.errors}")

        bad_spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display="1.6x",
            reported_stretch_factor=1.65,
            reported_effective_hdmi_desqueezed=True,
            **overrides,
        )
        r_bad = evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad_spec)
        self.assertFalse(r_bad.passed, f"spoofed desqueeze under {bypass_name} must fail")
    return _test


def _make_raw_fps_test(fps: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            raw_output="On",
            raw_output_setting=fps,
            post_raw_output_setting=fps,
        )
        r = evaluate_hdmi_raw_media_vault(spec)
        self.assertTrue(r.passed)
        self.assertEqual(P355_FX3_RAW_RESOLUTION, "4264x2408")
        self.assertEqual(P355_FX3_RAW_BIT_DEPTH, 16)
    return _test


def _make_4k_hdmi_10bit_test(mode: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_raw_media_vault_spec(
            raw_output="Off",
            rec_control="Off",
            time_code_output="Off",
            hdmi_4k_output_setting=mode,
            reported_effective_raw_output="Off",
            reported_effective_gamma="S-Log3",
            reported_effective_output_resolution="Auto",
            reported_card_write_pathway_active=False,
            post_raw_output="Off",
            post_rec_control="Off",
            post_time_code_output="Off",
            post_hdmi_4k_output_setting=mode,
        )
        st = _compute_65a_from_spec(spec)
        self.assertEqual(st["is_2400p"], mode.startswith("24.00p"))
        self.assertTrue(evaluate_hdmi_raw_media_vault(spec).passed)
    return _test


def _make_apsc_lockout_codec_test(codec: str, locked_out: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            apsc_s35_shooting="On",
            video_codec=codec,
            reported_apsc_4k_lockout_errno=P355_EOPNOTSUPP_ERRNO if locked_out else None,
            post_apsc_s35_shooting="On",
        )
        r = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        self.assertEqual(r.passed, not locked_out, f"codec={codec} unexpected result: {r.errors}")
        if locked_out:
            self.assertEqual(r.block_code, P355_BLOCKED_VAR_SHUTTER_OR_APSC_RESET_DRIFT)
    return _test


def _make_rec_lamp_state_test(rec_lamp_mode: str, silent_mode: str, exp_leds: tuple[bool, bool, bool]):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            rec_lamp=rec_lamp_mode,
            silent_mode=silent_mode,
            reported_front_led_on=exp_leds[0],
            reported_rear_led_on=exp_leds[1],
            reported_top_rec_ring_on=exp_leds[2],
            post_rec_lamp=rec_lamp_mode,
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec).passed)
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        spec_a = build_default_safe_hdmi_raw_media_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        ra = evaluate_hdmi_raw_media_vault(spec_a)
        self.assertEqual(ra.passed, expect_pass)

        spec_b = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        rb = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec_b)
        self.assertEqual(rb.passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        spec_a = build_default_safe_hdmi_raw_media_vault_spec(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            output_resolution="1080p",
            hdmi_4k_output_setting="23.98p 10bit",
            raw_output="On",
            raw_output_setting="23.98p",
            time_code_output="On",
            rec_control="On",
            audio_4ch_output="CH3/CH4",
            reported_effective_output_resolution="1080p",
            reset_action=reset_action,
            post_rec_media_dur_hdmi_output="On" if init else "Off(HDMI Only)",
            post_output_resolution="Auto" if init else "1080p",
            post_hdmi_4k_output_setting="59.94p 10bit" if init else "23.98p 10bit",
            post_raw_output="Off" if init else "On",
            post_raw_output_setting="59.94p" if init else "23.98p",
            post_time_code_output="Off" if init else "On",
            post_rec_control="Off" if init else "On",
            post_audio_4ch_output="CH1/CH2" if init else "CH3/CH4",
        )
        self.assertTrue(evaluate_hdmi_raw_media_vault(spec_a).passed)

        spec_b = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            de_squeeze_display="1.6x",
            rec_lamp="Only Front Off",
            emphasized_rec_display="Off",
            remain_shoot_display="Always Display",
            auto_review="5 Sec",
            anti_flicker_shoot="Off",
            apsc_s35_shooting="On",
            video_codec="XAVC S HD",
            reset_action=reset_action,
            post_de_squeeze_display="Off" if init else "1.6x",
            post_rec_lamp=P355_REC_LAMP_DEFAULT if init else "Only Front Off",
            post_emphasized_rec_display="On" if reset_action in ("Camera Settings Reset", "Initialize") else "Off",
            post_remain_shoot_display="Not Displayed" if init else "Always Display",
            post_auto_review="Off" if init else "5 Sec",
            post_anti_flicker_shoot="Off",
            post_apsc_s35_shooting=P355_APSC_S35_DEFAULT if init else "On",
        )
        self.assertTrue(evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec_b).passed)
    return _test


def _make_fx6_ecs_range_test(hz: float, expect_valid: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            camera_model=P355_FX6_DONOR_MODEL_NAME,
            fw_version=P355_FX6_DONOR_FW_VERSION,
            de_squeeze_display="1.5x",
            reported_stretch_factor=1.5,
            post_de_squeeze_display="1.5x",
            fx6_shutter_mode="ECS",
            fx6_ecs_frequency_hz=hz,
        )
        r = evaluate_desqueeze_reclamp_varshutter_apsc_vault(spec)
        self.assertEqual(r.passed, expect_valid, f"hz={hz} errors={r.errors}")
    return _test


def _make_still_crop_size_test(aspect: str, valid_size: str, invalid_size: str):
    def _test(self: unittest.TestCase) -> None:
        ok = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            apsc_s35_shooting="On",
            video_codec="XAVC S-I HD",
            still_aspect_ratio=aspect,
            still_image_size_requested=valid_size,
            reported_still_size_errno=None,
            reported_effective_still_size=valid_size,
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_apsc_s35_shooting="On",
        )
        rok = evaluate_desqueeze_reclamp_varshutter_apsc_vault(ok)
        self.assertTrue(rok.passed, f"still crop {aspect} failed: {rok.errors}")

        bad = build_default_safe_desqueeze_reclamp_varshutter_apsc_vault_spec(
            shooting_domain="Still",
            de_squeeze_display="Off",
            reported_stretch_factor=1.0,
            reported_effective_hdmi_desqueezed=False,
            apsc_s35_shooting="On",
            video_codec="XAVC S-I HD",
            still_aspect_ratio=aspect,
            still_image_size_requested=invalid_size,
            reported_still_size_errno=None,
            reported_effective_still_size=invalid_size,
            reported_auto_review_active=True,
            post_de_squeeze_display="Off",
            post_apsc_s35_shooting="On",
        )
        self.assertFalse(evaluate_desqueeze_reclamp_varshutter_apsc_vault(bad).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase355_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_65_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_65_PILLAR_IDS[idx])
    return _test


def _install_parameterized_tests() -> None:
    idx = 57

    # 5 De-Squeeze modes
    for mode, factor in (("Off", 1.0), ("1.3x", 1.3), ("1.5x", 1.5), ("1.6x", 1.65), ("2.0x", 2.0)):
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_desqueeze_mode_{mode.replace('.', '_')}",
            _make_desqueeze_mode_test(mode, factor),
        )
        idx += 1

    # 6 De-Squeeze bypasses
    bypasses = (
        ("log_off", {"log_shooting": "Off"}),
        ("raw_on", {"raw_output": "On"}),
        ("hdmi_only", {"rec_media_dur_hdmi_output": "Off(HDMI Only)"}),
        ("still_movie_key", {"shooting_domain": "Still", "still_movie_key_recording": True, "reported_auto_review_active": True}),
        ("remote_shooting", {"remote_shooting_active": True}),
        ("photo_capture", {"photo_capture_active": True}),
    )
    for b_name, ov in bypasses:
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_desqueeze_bypass_{b_name}",
            _make_desqueeze_bypass_test(b_name, ov),
        )
        idx += 1

    # 6 RAW fps modes
    for fps in P355_FX3_RAW_FPS_MODES:
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_raw_fps_{fps.replace('.', '_')}",
            _make_raw_fps_test(fps),
        )
        idx += 1

    # 6 4K Output Set (HDMI Only) 10-bit modes
    for mode in P355_FX3_HDMI_4K_ONLY_10BIT_MODES:
        clean = mode.replace(" ", "_").replace(".", "_")
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_hdmi_4k_10bit_{clean}",
            _make_4k_hdmi_10bit_test(mode),
        )
        idx += 1

    # 7 APS-C codec gates (5 locked out + 2 allowed)
    for codec in P355_APSC_S35_LOCKED_OUT_VIDEO_FORMATS:
        clean = codec.replace(" ", "_").replace("-", "_").replace("&", "n")
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_apsc_locked_codec_{clean}",
            _make_apsc_lockout_codec_test(codec, True),
        )
        idx += 1
    for codec in P355_APSC_S35_ALLOWED_VIDEO_FORMATS:
        clean = codec.replace(" ", "_").replace("-", "_")
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_apsc_allowed_codec_{clean}",
            _make_apsc_lockout_codec_test(codec, False),
        )
        idx += 1

    # 6 REC Lamp x Silent Mode combinations
    rec_lamp_cases = (
        ("All On", "Off", (True, True, True)),
        ("All On", "On", (True, True, True)),
        ("Only Front Off", "Off", (False, True, True)),
        ("Only Front Off", "On", (False, True, True)),
        ("All Off", "Off", (False, False, False)),
        ("All Off", "On", (False, False, False)),
    )
    for m_name, s_name, leds in rec_lamp_cases:
        clean = f"{m_name}_{s_name}".lower().replace(" ", "_")
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_rec_lamp_{clean}",
            _make_rec_lamp_state_test(m_name, s_name, leds),
        )
        idx += 1

    # 12 Slot-1 Write Firewall actions x errno pairs
    for action in sorted(P355_WRITE_MUTATING_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP", "EBUSY"):
            setattr(
                Phase355Pillar65VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 3 Reset action matrices (None / Camera Settings Reset / Initialize)
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 6 FX6 ECS boundary checks
    for hz, valid in ((23.98, False), (23.99, True), (50.10, True), (60.00, True), (8000.0, True), (8000.1, False)):
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_fx6_ecs_hz_{str(hz).replace('.', '_')}",
            _make_fx6_ecs_range_test(hz, valid),
        )
        idx += 1

    # 2 APS-C Still Crop size checks (3:2 5.1M & 16:9 4.3M)
    for aspect, valid_sz, invalid_sz in (
        ("3:2", P355_APSC_S35_STILL_CROP_SIZE_3_2, "L: 12M (4240x2832)"),
        ("16:9", P355_APSC_S35_STILL_CROP_SIZE_16_9, "L: 10M (4240x2384)"),
    ):
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_apsc_still_crop_{aspect.replace(':', '_')}",
            _make_still_crop_size_test(aspect, valid_sz, invalid_sz),
        )
        idx += 1

    # 17 Individual donor checks
    for d_i in range(17):
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # Selected key pillars + final 65th pillar across MASTER_65_PILLAR_IDS (16 tests -> total 148 tests)
    for p_i in (*range(0, 65, 5), 62, 63, 64):
        setattr(
            Phase355Pillar65VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
