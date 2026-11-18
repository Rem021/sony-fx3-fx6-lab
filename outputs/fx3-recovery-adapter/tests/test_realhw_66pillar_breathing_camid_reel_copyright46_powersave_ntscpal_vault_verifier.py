"""Phase 361 (Pillar 66 & 66/66 Milestone) unit tests:
Wave-64 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` empirical telemetry across 4 pillars:
- Pillar 66A (`[Breathing Comp.]` optical crop / regular Movie 119.88p/100p + S&Q >=100fps +
  HDMI 16-bit RAW + `SEL100F28GM` macro `0.57m..1.0m` + `SEL14TC/SEL20TC` lockouts, resettable
  via `[Camera Settings Reset]` vs non-resettable `Shading/CA/Distortion`, paid `Catalyst Prepare`
  + `[Distortion Comp.]=Auto` vs unsupported `Catalyst Browse`, contrasted against FX6 3-lock:
  `Distortion Comp.=Off`, ALL `S&Q=On`, ALL `RAW` codecs; AND Movie `[File Settings]` Reset-resistant
  tree: `[File Number]` Series/Reset + `Series Counter Reset -> max+1`, 5 `[File Name Format]` modes,
  `SDHC <=32GB FAT32` forced `[Standard]` + `4 GB` XAVC S split + no `FAT32+exFAT` `[Simult. Recording]`,
  `[Cam ID + Reel# Settings]` `Cam ID` change resets `Reel#` while `File Number=Reset` does NOT,
  `C999 -> D001` filename-only overflow leaving menu pos `"C"`, `YYMMDD` vs `YYYYMMDD`, `<=37`-char
  Title default `"C"`, `PRIVATE/M4ROOT/CLIP`, Slot 1 `EROFS=30` vs FX6 `4..46`-char `Title Prefix`
  default `"nnn_"`, `DIADEM_PRO` hand-over, `/XDROOT/Clip`).
- Pillar 66B (`[Copyright Info]` 46-char ASCII `[Set Photographer]`/`[Set Copyright]` + Round 57
  Erratum correction proving ALL 4 `[Copyright Info]` items incl. `[Write Copyright Info]` AND
  `[Write Serial Number]` are Reset-resistant [`Not available` under `Camera Settings Reset`],
  cleared ONLY by `[Initialize]`; active Still+Movie `[Write Serial Number]` in Ver. 2.00..7.02;
  `CAMSET*.DAT` PII exclusion vs FX6 zero EXIF Copyright menu + `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`;
  `[Power Setting Option]` 2 active Reset-resistant items, `[Power Save Start Time]` exact 9 bypass
  conditions & dormant tiers, `[Auto Power OFF Temp.]` `Standard`/`High` tripod warning, dormant
  `[Power Save by Monitor]` `EOPNOTSUPP=95`; `[NTSC/PAL Selector]` `base 0xe5c1` reboot, `Running
  on NTSC./PAL.`, PAL `23.98p`/`DF` lockouts, cross-region playback block, & legacy `base 0xe595`
  `"Format? Slot 1"` intercepted fail-closed `EROFS=30` with `raw_firmware_bytes_leaked == 0`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
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
    MASTER_66_PILLAR_COUNT,
    MASTER_66_PILLAR_IDS,
    MASTER_66_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P361_AIRPLANE_MODE_FORCED_ON,
    P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT,
    P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT,
    P361_BLOCKED_FILE_SETTINGS_CAMID_OR_SDHC_DRIFT,
    P361_BLOCKED_INVALID_PILLAR66A_SPEC,
    P361_BLOCKED_INVALID_PILLAR66B_SPEC,
    P361_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT,
    P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P361_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P361_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P361_CATALYST_BROWSE_BREATHING_SUPPORTED,
    P361_CATALYST_PREPARE_BREATHING_SUPPORTED,
    P361_CATALYST_PREPARE_REQUIRES_DISTORTION_AUTO,
    P361_CONCURRENT_CEILING_SECONDS,
    P361_COPYRIGHT_INFO_MAX_LEN,
    P361_CROSS_MODEL_FLASH_AUTHORIZED,
    P361_DONOR_FX3_APPFW_702_RELPATH,
    P361_DONOR_FX3_BACKUP_BIN_RELPATH,
    P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
    P361_DONOR_FX6_APPFW_601_RELPATH,
    P361_DONOR_FX6_UXC_EN_RELPATH,
    P361_DONOR_INSPECT_BUDGET_SECONDS,
    P361_EINVAL_ERRNO,
    P361_EMMC_WRITES_AUTHORIZED,
    P361_ENV_CLEAN_ROOM_TEST,
    P361_EOPNOTSUPP_ERRNO,
    P361_FAST_CLI_BUDGET_SECONDS,
    P361_FX3_BREATHING_DEFAULT,
    P361_FX3_BREATHING_EXCLUDED_LENSES,
    P361_FX3_BREATHING_RESETTABLE_BY_CAMERA_SETTINGS_RESET,
    P361_FX3_CAMID_DATE_DIGITS,
    P361_FX3_FILE_NAME_FORMATS,
    P361_FX3_FILE_SETTINGS_RESETTABLE,
    P361_FX3_FW_VERSION,
    P361_FX3_HAS_POWER_SAVE_BY_MONITOR,
    P361_FX3_HELPGUIDE_ID,
    P361_FX3_MODEL_ID,
    P361_FX3_MODEL_NAME,
    P361_FX3_MOVIE_STORAGE_DIR,
    P361_FX3_OTHER_LENS_COMP_RESETTABLE,
    P361_FX3_POWER_SAVE_9_BYPASS_CONDITIONS,
    P361_FX3_POWER_SAVE_DEFAULT,
    P361_FX3_POWER_SAVE_DORMANT_TIERS,
    P361_FX3_POWER_SAVE_MODES,
    P361_FX3_POWER_SETTING_RESETTABLE,
    P361_FX3_TITLE_DATE_DIGITS,
    P361_FX3_TITLE_DEFAULT,
    P361_FX3_TITLE_MAX_LEN,
    P361_FX6_CARD_HANDOVER_ENABLED,
    P361_FX6_DONOR_FW_VERSION,
    P361_FX6_DONOR_MODEL_NAME,
    P361_FX6_HAS_CONSUMER_POWER_SAVE_OR_NTSC_FORMAT_POPUP,
    P361_FX6_HAS_EXIF_COPYRIGHT_MENU,
    P361_FX6_LENS_SERIAL_SLOTS,
    P361_FX6_TITLE_PREFIX_DEFAULT,
    P361_FX6_TITLE_PREFIX_MAX_LEN,
    P361_FX6_TITLE_PREFIX_MIN_LEN,
    P361_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P361_NTSC_PAL_RESETTABLE,
    P361_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P361_PILLAR_66A_SCENARIO_IDS,
    P361_PILLAR_66B_SCENARIO_IDS,
    P361_PINNED_FX3_BACKUP_BIN_SHA256,
    P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
    P361_ROUND57_ERRATUM_ALL_COPYRIGHT_RESETTABLE,
    P361_SDHC_FAT32_SPLIT_GB,
    P361_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P361_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P361_STATUS_FAIL_66OF66_AGGREGATOR,
    P361_STATUS_VERIFIED_66OF66_AGGREGATOR,
    P361_STATUS_VERIFIED_PILLAR66_SUITE,
    P361_STATUS_VERIFIED_PILLAR_66A,
    P361_STATUS_VERIFIED_PILLAR_66B,
    P361_WRITE_COPYRIGHT_RESETTABLE,
    P361_WRITE_MUTATING_VAULT_ACTIONS,
    P361_WRITE_SERIAL_RESETTABLE,
    P361_WRITE_SERIAL_STILL_AND_MOVIE_ACTIVE,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE361_MASTER_SCHEMA,
    PHASE361_PHASE_NUMBER,
    PHASE361_SCHEMA,
    PHASE361_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_breathing_camid_reel_sdhc_vault_spec,
    build_default_safe_copyright46_powersave_ntscpal_vault_spec,
    compute_expected_breathing_camid_reel_sdhc_vault_state,
    compute_expected_copyright46_powersave_ntscpal_vault_state,
    evaluate_66pillar_recovery_master,
    evaluate_breathing_camid_reel_sdhc_vault,
    evaluate_copyright46_powersave_ntscpal_vault,
    evaluate_realhw_66pillar_recovery_master,
    inspect_phase361_donors_readonly,
    run_pillar66_standalone_suite,
    run_pillar66a_breathing_camid_reel_sdhc_vault_6_scenario_suite,
    run_pillar66b_copyright46_powersave_ntscpal_vault_6_scenario_suite,
    verify_66pillar_recovery,
    verify_66pillar_recovery_suite,
    verify_all_66_recovery_pillars,
    verify_breathing_camid_reel_copyright46_powersave_ntscpal_and_vault,
    verify_breathing_camid_reel_copyright46_powersave_ntscpal_vault,
)


def _wave64_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P361_DONOR_FX3_APPFW_702_RELPATH,
        P361_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
        P361_DONOR_FX6_APPFW_601_RELPATH,
        P361_DONOR_FX3_BACKUP_BIN_RELPATH,
        P361_DONOR_FX6_UXC_EN_RELPATH,
    )
    for rel in required:
        rel_n = rel[5:] if rel.startswith("work/") else rel
        if not any(
            r is not None and ((r / rel_n).exists() or (r.parent / rel).exists())
            for r in roots
        ):
            return False
    return True


def _strip_elapsed_seconds(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys prior to digest checks."""
    if isinstance(obj, dict):
        return {
            k: _strip_elapsed_seconds(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_elapsed_seconds(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_strip_elapsed_seconds(v) for v in obj)
    return obj


def _compute_66a_from_spec(spec: fr.BreathingCamIdReelSdhcVaultSpec) -> dict[str, object]:
    return compute_expected_breathing_camid_reel_sdhc_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        recording_fps=spec.recording_fps,
        raw_output=spec.raw_output,
        breathing_comp=spec.breathing_comp,
        lens_info_status=spec.lens_info_status,
        lens_id=spec.lens_id,
        distortion_comp=spec.distortion_comp,
        clear_image_zoom_scale=spec.clear_image_zoom_scale,
        auto_framing_active=spec.auto_framing_active,
        framing_stabilizer_active=spec.framing_stabilizer_active,
        catalyst_product=spec.catalyst_product,
        fx6_sq_motion=spec.fx6_sq_motion,
        fx6_codec=spec.fx6_codec,
        file_number_mode=spec.file_number_mode,
        series_counter_reset_requested=spec.series_counter_reset_requested,
        existing_max_clip_number=spec.existing_max_clip_number,
        file_name_format=spec.file_name_format,
        card_type=spec.card_type,
        card_filesystem=spec.card_filesystem,
        simult_recording_enabled=spec.simult_recording_enabled,
        secondary_card_filesystem=spec.secondary_card_filesystem,
        recorded_clip_size_gb=spec.recorded_clip_size_gb,
        camera_id=spec.camera_id,
        prev_camera_id=spec.prev_camera_id,
        reel_number=spec.reel_number,
        camera_position=spec.camera_position,
        clip_number=spec.clip_number,
        title_name=spec.title_name,
        capture_date_yyyymmdd=spec.capture_date_yyyymmdd,
        random_2char=spec.random_2char,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_66b_from_spec(spec: fr.Copyright46PowerSaveNtscPalVaultSpec) -> dict[str, object]:
    return compute_expected_copyright46_powersave_ntscpal_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        write_copyright_info=spec.write_copyright_info,
        photographer_name=spec.photographer_name,
        copyright_holder=spec.copyright_holder,
        write_serial_number=spec.write_serial_number,
        camset_export_requested=spec.camset_export_requested,
        camset_target_slot=spec.camset_target_slot,
        camset_files_existing=spec.camset_files_existing,
        exif_copyright_menu_requested=spec.exif_copyright_menu_requested,
        power_save_start_time=spec.power_save_start_time,
        auto_power_off_temp=spec.auto_power_off_temp,
        power_save_by_monitor_requested=spec.power_save_by_monitor_requested,
        usb_power_supply=spec.usb_power_supply,
        slideshow_playing=spec.slideshow_playing,
        ftp_transfer_active=spec.ftp_transfer_active,
        movie_recording_active=spec.movie_recording_active,
        pc_connected=spec.pc_connected,
        tv_hdmi_connected=spec.tv_hdmi_connected,
        ir_remote_ctrl_on=spec.ir_remote_ctrl_on,
        bluetooth_rmt_ctrl_on=spec.bluetooth_rmt_ctrl_on,
        streaming_or_creators_cloud_active=spec.streaming_or_creators_cloud_active,
        factory_tv_system=spec.factory_tv_system,
        ntsc_pal_selector=spec.ntsc_pal_selector,
        target_ntsc_pal_selector=spec.target_ntsc_pal_selector,
        requested_movie_fps=spec.requested_movie_fps,
        requested_tc_format=spec.requested_tc_format,
        playback_clip_system=spec.playback_clip_system,
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


class Phase361Pillar66VerifierTests(unittest.TestCase):
    """Phase 361 Pillar 66 & 66/66 Master Recovery Verifier unit tests."""

    # ------------------------------------------------------------------
    # 1. Constants, Safety Redlines, Package Exports & Non-Shadowing
    # ------------------------------------------------------------------

    def test_001_phase361_metadata_and_schema_constants(self) -> None:
        self.assertEqual(PHASE361_PHASE_NUMBER, 361)
        self.assertEqual(PHASE361_VERSION, "1.0.0")
        self.assertIn("66pillar", PHASE361_SCHEMA)
        self.assertIn("66pillar", PHASE361_MASTER_SCHEMA)
        self.assertEqual(MASTER_66_PILLAR_COUNT, 66)
        self.assertEqual(len(MASTER_66_PILLAR_SPECS), 66)
        self.assertEqual(len(MASTER_66_PILLAR_IDS), 66)
        self.assertEqual(
            MASTER_66_PILLAR_IDS[-1],
            "pillar66_breathing_camid_reel_copyright46_powersave_ntscpal_vault",
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
        self.assertFalse(P361_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED)
        self.assertFalse(P361_CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(P361_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(P361_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P361_OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertTrue(P361_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P361_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P361_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)

    def test_003_package_exports_do_not_shadow_pillar65_symbols(self) -> None:
        self.assertEqual(fr.MASTER_65_PILLAR_COUNT, 65)
        self.assertEqual(fr.MASTER_66_PILLAR_COUNT, 66)
        self.assertTrue(hasattr(fr, "verify_65pillar_recovery"))
        self.assertTrue(hasattr(fr, "verify_66pillar_recovery"))
        self.assertTrue(hasattr(fr, "evaluate_realhw_65pillar_recovery_master"))
        self.assertTrue(hasattr(fr, "evaluate_realhw_66pillar_recovery_master"))
        self.assertTrue(hasattr(fr, "verify_all_66_recovery_pillars"))
        self.assertEqual(len(fr.MASTER_65_PILLAR_IDS), 65)
        self.assertEqual(len(fr.MASTER_66_PILLAR_IDS), 66)
        self.assertEqual(fr.MASTER_66_PILLAR_IDS[:65], fr.MASTER_65_PILLAR_IDS)
        self.assertIn("verify_66pillar_recovery", fr.__all__)
        self.assertIn("verify_65pillar_recovery", fr.__all__)
        self.assertIn("verify_all_66_recovery_pillars", fr.__all__)

    def test_004_wave64_empirical_constants_grounding(self) -> None:
        self.assertEqual(P361_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P361_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P361_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P361_FX3_FW_VERSION, "7.02")
        self.assertEqual(P361_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P361_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P361_FX3_BREATHING_DEFAULT, "Off")
        self.assertTrue(P361_FX3_BREATHING_RESETTABLE_BY_CAMERA_SETTINGS_RESET)
        self.assertFalse(P361_FX3_OTHER_LENS_COMP_RESETTABLE)
        self.assertFalse(P361_CATALYST_BROWSE_BREATHING_SUPPORTED)
        self.assertTrue(P361_CATALYST_PREPARE_BREATHING_SUPPORTED)
        self.assertTrue(P361_CATALYST_PREPARE_REQUIRES_DISTORTION_AUTO)
        self.assertFalse(P361_FX3_FILE_SETTINGS_RESETTABLE)
        self.assertEqual(P361_FX3_TITLE_MAX_LEN, 37)
        self.assertEqual(P361_FX3_TITLE_DEFAULT, "C")
        self.assertEqual(P361_SDHC_FAT32_SPLIT_GB, 4)
        self.assertEqual(P361_FX3_CAMID_DATE_DIGITS, 6)
        self.assertEqual(P361_FX3_TITLE_DATE_DIGITS, 8)
        self.assertEqual(P361_FX3_MOVIE_STORAGE_DIR, "PRIVATE/M4ROOT/CLIP")
        self.assertEqual(P361_FX6_TITLE_PREFIX_MIN_LEN, 4)
        self.assertEqual(P361_FX6_TITLE_PREFIX_MAX_LEN, 46)
        self.assertEqual(P361_FX6_TITLE_PREFIX_DEFAULT, "nnn_")
        self.assertTrue(P361_FX6_CARD_HANDOVER_ENABLED)
        self.assertEqual(P361_COPYRIGHT_INFO_MAX_LEN, 46)
        self.assertFalse(P361_ROUND57_ERRATUM_ALL_COPYRIGHT_RESETTABLE)
        self.assertFalse(P361_WRITE_COPYRIGHT_RESETTABLE)
        self.assertFalse(P361_WRITE_SERIAL_RESETTABLE)
        self.assertTrue(P361_WRITE_SERIAL_STILL_AND_MOVIE_ACTIVE)
        self.assertFalse(P361_FX6_HAS_EXIF_COPYRIGHT_MENU)
        self.assertEqual(P361_FX6_LENS_SERIAL_SLOTS, 6)
        self.assertEqual(len(P361_FX3_POWER_SAVE_9_BYPASS_CONDITIONS), 9)
        self.assertEqual(P361_FX3_POWER_SAVE_DEFAULT, "5 Min")
        self.assertFalse(P361_FX3_POWER_SETTING_RESETTABLE)
        self.assertFalse(P361_FX3_HAS_POWER_SAVE_BY_MONITOR)
        self.assertFalse(P361_NTSC_PAL_RESETTABLE)
        self.assertFalse(P361_FX6_HAS_CONSUMER_POWER_SAVE_OR_NTSC_FORMAT_POPUP)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY 18-Donor Inspection & All 4 Execution Modes
    # ------------------------------------------------------------------

    def test_005_donor_inspection_force_clean_room_argument(self) -> None:
        snap = inspect_phase361_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, P361_DONOR_INSPECT_BUDGET_SECONDS)

    def test_006_donor_inspection_env_fx3_clean_room_test_mode(self) -> None:
        with patch.dict(os.environ, {P361_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase361_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)

    def test_007_donor_inspection_env_fx3_fx6_force_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase361_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)

    def test_008_donor_inspection_mocked_donorless_work_root_none(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P361_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                snap = inspect_phase361_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)

    def test_009_donor_inspection_normal_mode_matches_environment(self) -> None:
        snap = inspect_phase361_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)
        if (
            not os.environ.get(P361_ENV_CLEAN_ROOM_TEST)
            and not os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
            and _wave64_donors_present()
        ):
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        fx3_bk = [a for a in snap.artifacts if a.artifact_id == "fx3_backup_bin"][0]
        self.assertEqual(fx3_bk.digest_sha256, P361_PINNED_FX3_BACKUP_BIN_SHA256)
        libsl = [a for a in snap.artifacts if a.artifact_id == "fx3_libsaveloadsettings_so"][0]
        self.assertEqual(libsl.digest_sha256, P361_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256)

    def test_010_donor_inspection_strictly_pins_18_artifacts_and_zero_raw_leak(self) -> None:
        snap = inspect_phase361_donors_readonly(force_clean_room=True)
        self.assertEqual(len(snap.artifacts), 18)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned, f"{art.artifact_id} failed pinned check")
            self.assertEqual(len(art.digest_sha256), 64)
            self.assertGreater(art.total_bytes, 0)

    # ------------------------------------------------------------------
    # 3. Pillar 66A: Breathing Comp., Catalyst Prepare, File Settings, Cam ID + Reel# & SDHC
    # ------------------------------------------------------------------

    def test_011_pillar66a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec()
        report = evaluate_breathing_camid_reel_sdhc_vault(spec)
        st = _compute_66a_from_spec(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P361_STATUS_VERIFIED_PILLAR_66A)
        self.assertIsNone(report.block_code)
        self.assertTrue(st["optical_crop_active"])
        self.assertTrue(report.breathing_comp_120p_sq_raw_catalyst_verified)
        self.assertTrue(report.file_settings_camid_reel_sdhc_reset_verified)
        self.assertTrue(report.slot1_vault_and_h0_h3_verified)

    def test_012_pillar66a_breathing_comp_movie_120p_100p_lockout_enforced(self) -> None:
        for fps in (100, 120):
            spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                shooting_domain="Movie",
                recording_fps=fps,
                breathing_comp="On",
                reported_breathing_errno=None,
            )
            st = _compute_66a_from_spec(spec)
            self.assertEqual(st["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
            self.assertEqual(st["effective_breathing"], "Off")
            rep = evaluate_breathing_camid_reel_sdhc_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT)

    def test_013_pillar66a_breathing_comp_sq_lt_100fps_allowed_ge_100fps_locked(self) -> None:
        ok_sq = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            shooting_domain="S&Q",
            recording_fps=60,
            breathing_comp="On",
            reported_effective_breathing="On",
            reported_optical_crop_active=True,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_sq).passed)

        bad_sq = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            shooting_domain="S&Q",
            recording_fps=120,
            breathing_comp="On",
            reported_breathing_errno=None,
        )
        st = _compute_66a_from_spec(bad_sq)
        self.assertEqual(st["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_sq).passed)

    def test_014_pillar66a_breathing_comp_hdmi_raw_bypass_and_still_lockout(self) -> None:
        bad_raw = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            raw_output="On",
            breathing_comp="On",
            reported_optical_crop_active=True,
        )
        st_raw = _compute_66a_from_spec(bad_raw)
        self.assertIsNone(st_raw["breathing_errno"])
        self.assertEqual(st_raw["effective_breathing"], "Off")
        self.assertFalse(st_raw["optical_crop_active"])
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_raw).passed)

        ok_raw_bypass = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            raw_output="On",
            breathing_comp="On",
            reported_breathing_errno=None,
            reported_effective_breathing="Off",
            reported_optical_crop_active=False,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_raw_bypass).passed)

        bad_still = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            shooting_domain="Still",
            breathing_comp="On",
            reported_breathing_errno=None,
        )
        st_still = _compute_66a_from_spec(bad_still)
        self.assertEqual(st_still["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_still).passed)

    def test_015_pillar66a_breathing_lens_exclusions_sel100_macro_teleconverters(self) -> None:
        for lens_id in P361_FX3_BREATHING_EXCLUDED_LENSES:
            spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                lens_id=lens_id,
                breathing_comp="On",
                reported_breathing_errno=None,
            )
            st = _compute_66a_from_spec(spec)
            self.assertEqual(st["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(spec).passed)

    def test_016_pillar66a_ciz_autoframing_stabilizer_allow_breathing_and_bypass_post_crop(self) -> None:
        for flag_kw in (
            {"clear_image_zoom_scale": 1.5},
            {"auto_framing_active": True},
            {"framing_stabilizer_active": True},
        ):
            spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                breathing_comp="On",
                reported_breathing_errno=None,
                reported_effective_breathing="On",
                reported_optical_crop_active=False,
                **flag_kw,
            )
            st = _compute_66a_from_spec(spec)
            self.assertIsNone(st["breathing_errno"])
            self.assertFalse(st["optical_crop_active"])
            rep = evaluate_breathing_camid_reel_sdhc_vault(spec)
            self.assertTrue(rep.passed, f"flag_kw={flag_kw} failed: {rep.errors}")

    def test_017_pillar66a_catalyst_prepare_vs_browse_and_distortion_auto_gate(self) -> None:
        ok_prep = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            breathing_comp="Off",
            distortion_comp="Auto",
            catalyst_product="Catalyst Prepare",
            reported_effective_breathing="Off",
            reported_optical_crop_active=False,
            reported_catalyst_metadata_supported=True,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_prep).passed)

        bad_dist_off = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            breathing_comp="Off",
            distortion_comp="Off",
            catalyst_product="Catalyst Prepare",
            reported_effective_breathing="Off",
            reported_optical_crop_active=False,
            reported_catalyst_metadata_supported=True,
        )
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_dist_off).passed)

        bad_browse = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            breathing_comp="Off",
            distortion_comp="Auto",
            catalyst_product="Catalyst Browse",
            reported_effective_breathing="Off",
            reported_optical_crop_active=False,
            reported_catalyst_metadata_supported=True,
        )
        rep = evaluate_breathing_camid_reel_sdhc_vault(bad_browse)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P361_BLOCKED_BREATHING_COMP_OR_CATALYST_DRIFT)

    def test_018_pillar66a_fx6_breathing_3_lock_matrix(self) -> None:
        for lock_kw in (
            {"distortion_comp": "Off"},
            {"fx6_sq_motion": "On"},
            {"fx6_codec": "RAW"},
            {"fx6_codec": "RAW & XAVC-I"},
        ):
            bad_fx6 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                camera_model=P361_FX6_DONOR_MODEL_NAME,
                fw_version=P361_FX6_DONOR_FW_VERSION,
                breathing_comp="Auto",
                title_name=P361_FX6_TITLE_PREFIX_DEFAULT,
                reported_storage_dir="/XDROOT/Clip",
                fx6_card_handover_expected=True,
                post_title_name=P361_FX6_TITLE_PREFIX_DEFAULT,
                **lock_kw,
            )
            st = _compute_66a_from_spec(bad_fx6)
            self.assertEqual(st["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
            self.assertTrue(st["fx6_hard_locked_off"])
            self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_fx6).passed)

    def test_019_pillar66a_series_counter_reset_sets_max_plus_1(self) -> None:
        ok = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_number_mode="Series",
            series_counter_reset_requested=True,
            existing_max_clip_number=44,
            reported_next_series_clip=45,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok).passed)

        spoof = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_number_mode="Series",
            series_counter_reset_requested=True,
            existing_max_clip_number=44,
            reported_next_series_clip=1,
        )
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(spoof).passed)

    def test_020_pillar66a_sdhc_fat32_forces_standard_splits_4gb_forbids_mixed_simult(self) -> None:
        ok_sdhc = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            card_type="SDHC_FAT32",
            card_filesystem="FAT32",
            file_name_format="Standard",
            simult_recording_enabled=False,
            recorded_clip_size_gb=7.2,
            reported_sdhc_split_required=True,
            clip_number=12,
            reported_next_series_clip=12,
            reported_output_clip_number=12,
            reported_clip_basename="C0012",
            post_file_name_format="Standard",
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_sdhc).passed)

        bad_nonstd = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            card_type="SDHC_FAT32",
            card_filesystem="FAT32",
            file_name_format="Cam ID + Reel#",
        )
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_nonstd).passed)

        bad_simult = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            card_type="SDXC_exFAT",
            card_filesystem="exFAT",
            file_name_format="Standard",
            simult_recording_enabled=True,
            secondary_card_filesystem="FAT32",
            reported_clip_basename="C0001",
            post_file_name_format="Standard",
        )
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_simult).passed)

    def test_021_pillar66a_camid_change_resets_reel_while_file_number_reset_does_not(self) -> None:
        ok_id_chg = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            camera_id="B",
            prev_camera_id="A",
            reel_number=19,
            reported_effective_reel_number=1,
            reported_clip_basename="B001C001_230101AB",
            post_camera_id="B",
            post_reel_number=1,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_id_chg).passed)

        ok_file_rst = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_number_mode="Reset",
            camera_id="B",
            prev_camera_id="B",
            reel_number=19,
            reported_effective_reel_number=19,
            reported_clip_basename="B019C001_230101AB",
            post_file_number_mode="Reset",
            post_camera_id="B",
            post_reel_number=19,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_file_rst).passed)

    def test_022_pillar66a_c999_to_d001_filename_overflow_leaves_menu_position_unchanged(self) -> None:
        ok_ovf = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            camera_id="A",
            prev_camera_id="A",
            reel_number=1,
            camera_position="C",
            clip_number=1000,
            reported_next_series_clip=1000,
            reported_output_position="D",
            reported_output_clip_number=1,
            reported_menu_position_unchanged="C",
            reported_clip_basename="A001D001_230101AB",
            post_camera_position="C",
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_ovf).passed)

        bad_mut_menu = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            camera_position="C",
            clip_number=1000,
            reported_next_series_clip=1000,
            reported_output_position="D",
            reported_output_clip_number=1,
            reported_menu_position_unchanged="D",
            reported_clip_basename="A001D001_230101AB",
            post_camera_position="D",
        )
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_mut_menu).passed)

    def test_023_pillar66a_yymmdd_vs_yyyymmdd_and_37_char_title_boundary(self) -> None:
        title_37 = "T" * 37
        ok_37 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_name_format="Title + Date",
            title_name=title_37,
            capture_date_yyyymmdd="20261118",
            clip_number=9,
            reported_next_series_clip=9,
            reported_output_clip_number=9,
            reported_clip_basename=f"{title_37}_20261118_0009",
            post_file_name_format="Title + Date",
            post_title_name=title_37,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_37).passed)

        bad_38 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_name_format="Title",
            title_name="T" * 38,
        )
        st = _compute_66a_from_spec(bad_38)
        self.assertEqual(st["title_errno"], P361_EINVAL_ERRNO)
        self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_38).passed)

    def test_024_pillar66a_fx6_4_to_46_title_prefix_bounds(self) -> None:
        title_46 = "F" * 46
        ok_fx6 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            camera_model=P361_FX6_DONOR_MODEL_NAME,
            fw_version=P361_FX6_DONOR_FW_VERSION,
            breathing_comp="Off",
            reported_effective_breathing="Off",
            reported_optical_crop_active=False,
            file_name_format="Title",
            title_name=title_46,
            reported_storage_dir="/XDROOT/Clip",
            reported_clip_basename=f"{title_46}_0001",
            fx6_card_handover_expected=True,
            post_breathing_comp="Off",
            post_file_name_format="Title",
            post_title_name=title_46,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(ok_fx6).passed)

        for bad_len in (3, 47):
            bad_fx6 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
                camera_model=P361_FX6_DONOR_MODEL_NAME,
                fw_version=P361_FX6_DONOR_FW_VERSION,
                breathing_comp="Off",
                reported_effective_breathing="Off",
                reported_optical_crop_active=False,
                file_name_format="Title",
                title_name="F" * bad_len,
                reported_storage_dir="/XDROOT/Clip",
                fx6_card_handover_expected=True,
                post_breathing_comp="Off",
                post_file_name_format="Title",
                post_title_name="F" * bad_len,
            )
            self.assertEqual(_compute_66a_from_spec(bad_fx6)["title_errno"], P361_EINVAL_ERRNO)
            self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(bad_fx6).passed)

    def test_025_pillar66a_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        bad_ovl = build_default_safe_breathing_camid_reel_sdhc_vault_spec(overlay_dir="/nflasha/66a")
        r1 = evaluate_breathing_camid_reel_sdhc_vault(bad_ovl)
        self.assertFalse(r1.passed)
        self.assertEqual(r1.block_code, P361_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = build_default_safe_breathing_camid_reel_sdhc_vault_spec(backup_bin_h3_sha256="f" * 64)
        r2 = evaluate_breathing_camid_reel_sdhc_vault(bad_h3)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.block_code, P361_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    # ------------------------------------------------------------------
    # 4. Pillar 66B: Copyright 46-Char (Round 57 Erratum), Write Serial,
    #    CAMSET Shield, Power Save 9-Bypass, Dormant Monitor & NTSC/PAL Vault
    # ------------------------------------------------------------------

    def test_026_pillar66b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_copyright46_powersave_ntscpal_vault_spec()
        report = evaluate_copyright46_powersave_ntscpal_vault(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P361_STATUS_VERIFIED_PILLAR_66B)
        self.assertIsNone(report.block_code)
        self.assertTrue(report.copyright46_round57_reset_serial_and_camset_verified)
        self.assertTrue(report.powersave_9cond_dormant_monitor_and_ntscpal_verified)
        self.assertTrue(report.overlay_and_h0_h3_verified)

    def test_027_pillar66b_round57_erratum_all_4_copyright_and_serial_survive_camera_reset(self) -> None:
        p46 = "P" * 46
        c46 = "C" * 46
        ok = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            shooting_domain="Still",
            write_copyright_info="On",
            photographer_name=p46,
            copyright_holder=c46,
            write_serial_number="On",
            reported_still_copyright_written=True,
            reported_movie_copyright_written=False,
            reported_serial_written_on_capture=True,
            reset_action="Camera Settings Reset",
            post_write_copyright_info="On",
            post_photographer_name=p46,
            post_copyright_holder=c46,
            post_write_serial_number="On",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok).passed)

        # Spoofing Round 57 erratum (claiming Write Copyright Info flips Off on Camera Settings Reset)
        bad_erratum = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            shooting_domain="Still",
            write_copyright_info="On",
            photographer_name=p46,
            copyright_holder=c46,
            write_serial_number="On",
            reported_still_copyright_written=True,
            reported_serial_written_on_capture=True,
            reset_action="Camera Settings Reset",
            post_write_copyright_info="Off",
            post_photographer_name=p46,
            post_copyright_holder=c46,
            post_write_serial_number="On",
        )
        rep = evaluate_copyright46_powersave_ntscpal_vault(bad_erratum)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P361_BLOCKED_COPYRIGHT46_RESET_OR_CAMSET_DRIFT)

    def test_028_pillar66b_initialize_clears_all_copyright_serial_powersave_and_ntscpal(self) -> None:
        ok_init = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            shooting_domain="Still",
            write_copyright_info="On",
            photographer_name="PhotoUser",
            copyright_holder="CopyrightCorp",
            write_serial_number="On",
            reported_still_copyright_written=True,
            reported_serial_written_on_capture=True,
            power_save_start_time="10 Sec",
            auto_power_off_temp="High",
            reported_tripod_warning_active=True,
            factory_tv_system="NTSC",
            ntsc_pal_selector="PAL",
            target_ntsc_pal_selector="PAL",
            requested_movie_fps="25p",
            requested_tc_format="NDF",
            playback_clip_system="PAL",
            reported_effective_tv_system="PAL",
            reported_non_factory_banner="Running on PAL.",
            reset_action="Initialize",
            post_write_copyright_info="Off",
            post_photographer_name="",
            post_copyright_holder="",
            post_write_serial_number="Off",
            post_power_save_start_time="5 Min",
            post_auto_power_off_temp="Standard",
            post_ntsc_pal_selector="NTSC",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok_init).passed)

    def test_029_pillar66b_copyright_47char_and_non_ascii_rejected(self) -> None:
        for bad_kw in (
            {"photographer_name": "A" * 47},
            {"copyright_holder": "B" * 47},
            {"photographer_name": "摄影师FX3"},
            {"copyright_holder": "著作権2026"},
        ):
            spec = build_default_safe_copyright46_powersave_ntscpal_vault_spec(**bad_kw)
            self.assertEqual(_compute_66b_from_spec(spec)["copyright_str_errno"], P361_EINVAL_ERRNO)
            self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(spec).passed)

    def test_030_pillar66b_write_serial_active_across_still_movie_and_sq(self) -> None:
        for dom in ("Still", "Movie", "S&Q"):
            spec = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                shooting_domain=dom,
                write_serial_number="On",
                reported_serial_written_on_capture=True,
                post_write_serial_number="On",
            )
            self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(spec).passed)

            spoof = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                shooting_domain=dom,
                write_serial_number="On",
                reported_serial_written_on_capture=False,
                post_write_serial_number="On",
            )
            self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(spoof).passed)

    def test_031_pillar66b_camset_pii_exclusion_and_slot1_10file_limit(self) -> None:
        bad_pii = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            camset_copyright_pii_leaked_bytes=46,
        )
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_pii).passed)

        bad_limit = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            camset_export_requested=True,
            camset_target_slot=1,
            camset_files_existing=10,
            reported_camset_slot_limit_ok=False,
        )
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_limit).passed)

    def test_032_pillar66b_fx6_zero_exif_copyright_menu_enforced(self) -> None:
        bad_fx6 = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            camera_model=P361_FX6_DONOR_MODEL_NAME,
            fw_version=P361_FX6_DONOR_FW_VERSION,
            exif_copyright_menu_requested=True,
            reported_exif_menu_errno=None,
        )
        self.assertEqual(_compute_66b_from_spec(bad_fx6)["exif_menu_errno"], P361_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_fx6).passed)

    def test_033_pillar66b_auto_pwr_off_temp_high_tripod_warning_and_reset_resistance(self) -> None:
        ok_high = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            auto_power_off_temp="High",
            reported_tripod_warning_active=True,
            reset_action="Camera Settings Reset",
            post_auto_power_off_temp="High",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok_high).passed)

        bad_reset = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            auto_power_off_temp="High",
            reported_tripod_warning_active=True,
            reset_action="Camera Settings Reset",
            post_auto_power_off_temp="Standard",
        )
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_reset).passed)

    def test_034_pillar66b_dormant_power_save_by_monitor_enforces_eopnotsupp(self) -> None:
        bad = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            power_save_by_monitor_requested=True,
            dormant_power_save_by_monitor_exposed_events=1,
            reported_monitor_linkage_errno=None,
        )
        self.assertEqual(_compute_66b_from_spec(bad)["monitor_linkage_errno"], P361_EOPNOTSUPP_ERRNO)
        rep = evaluate_copyright46_powersave_ntscpal_vault(bad)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT)

    def test_035_pillar66b_ntsc_pal_reboot_and_pal_2398p_df_tc_lockout(self) -> None:
        ok_pal = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            factory_tv_system="NTSC",
            ntsc_pal_selector="NTSC",
            target_ntsc_pal_selector="PAL",
            requested_movie_fps="50p",
            requested_tc_format="NDF",
            playback_clip_system="PAL",
            reported_ntsc_pal_reboot_triggered=True,
            reported_effective_tv_system="PAL",
            reported_non_factory_banner="Running on PAL.",
            reported_playback_allowed=True,
            post_ntsc_pal_selector="PAL",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok_pal).passed)

        for bad_kw in (
            {"requested_movie_fps": "23.98p", "requested_tc_format": "NDF"},
            {"requested_movie_fps": "29.97p", "requested_tc_format": "NDF"},
            {"requested_movie_fps": "59.94p", "requested_tc_format": "NDF"},
            {"requested_movie_fps": "119.88p", "requested_tc_format": "NDF"},
            {"requested_movie_fps": "25p", "requested_tc_format": "DF"},
        ):
            bad_pal = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
                factory_tv_system="NTSC",
                ntsc_pal_selector="PAL",
                target_ntsc_pal_selector="PAL",
                playback_clip_system="PAL",
                reported_effective_tv_system="PAL",
                reported_non_factory_banner="Running on PAL.",
                post_ntsc_pal_selector="PAL",
                **bad_kw,
            )
            self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_pal).passed)

    def test_036_pillar66b_cross_region_playback_block(self) -> None:
        ok_blocked = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            factory_tv_system="NTSC",
            ntsc_pal_selector="PAL",
            target_ntsc_pal_selector="PAL",
            requested_movie_fps="25p",
            requested_tc_format="NDF",
            playback_clip_system="NTSC",
            reported_effective_tv_system="PAL",
            reported_non_factory_banner="Running on PAL.",
            reported_playback_allowed=False,
            post_ntsc_pal_selector="PAL",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok_blocked).passed)

        bad_allow = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            factory_tv_system="NTSC",
            ntsc_pal_selector="PAL",
            target_ntsc_pal_selector="PAL",
            requested_movie_fps="25p",
            requested_tc_format="NDF",
            playback_clip_system="NTSC",
            reported_effective_tv_system="PAL",
            reported_non_factory_banner="Running on PAL.",
            reported_playback_allowed=True,
            post_ntsc_pal_selector="PAL",
        )
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(bad_allow).passed)

    def test_037_pillar66b_legacy_ntsc_pal_format_prompt_slot1_blocked_erofs(self) -> None:
        ok_shielded = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="FORMAT_NTSC_PAL_PROMPT",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok_shielded).passed)

        breached = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="FORMAT_NTSC_PAL_PROMPT",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
        )
        rep = evaluate_copyright46_powersave_ntscpal_vault(breached)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P361_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    # ------------------------------------------------------------------
    # 5. Standalone Suites, Master 66/66 Aggregator, Fault Injection & CLI
    # ------------------------------------------------------------------

    def test_038_single_shot_combined_verifier_both_variants_pass(self) -> None:
        r1 = verify_breathing_camid_reel_copyright46_powersave_ntscpal_and_vault(force_clean_room=True)
        r2 = verify_breathing_camid_reel_copyright46_powersave_ntscpal_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P361_STATUS_VERIFIED_PILLAR66_SUITE)
        self.assertEqual(r2.status, P361_STATUS_VERIFIED_PILLAR66_SUITE)

    def test_039_pillar66a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar66a_breathing_camid_reel_sdhc_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P361_PILLAR_66A_SCENARIO_IDS,
        )

    def test_040_pillar66b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar66b_copyright46_powersave_ntscpal_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P361_PILLAR_66B_SCENARIO_IDS,
        )

    def test_041_standalone_suite_all_4_modes_pass(self) -> None:
        r_normal = run_pillar66_standalone_suite()
        r_cr = run_pillar66_standalone_suite(force_clean_room=True)
        with patch.dict(os.environ, {P361_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            r_env1 = run_pillar66_standalone_suite()
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r_env2 = run_pillar66_standalone_suite()
        with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
            clean_env = os.environ.copy()
            clean_env.pop(P361_ENV_CLEAN_ROOM_TEST, None)
            clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            with patch.dict(os.environ, clean_env, clear=True):
                r_nomock = run_pillar66_standalone_suite()
        for r in (r_normal, r_cr, r_env1, r_env2, r_nomock):
            self.assertTrue(r.all_passed)
            self.assertEqual(r.status, P361_STATUS_VERIFIED_PILLAR66_SUITE)
            self.assertEqual(r.pillar_66a_breathing_camid_reel_sdhc_vault.scenarios_passed, 6)
            self.assertEqual(r.pillar_66b_copyright46_powersave_ntscpal_vault.scenarios_passed, 6)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)
            self.assertLess(r.elapsed_seconds, P361_FAST_CLI_BUDGET_SECONDS)

    def test_042_master_66_recovery_clean_room_mode_passes_under_budget(self) -> None:
        m = verify_all_66_recovery_pillars(force_clean_room=True)
        self.assertTrue(m.all_passed)
        self.assertEqual(m.status, P361_STATUS_VERIFIED_66OF66_AGGREGATOR)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillar_count, 66)
        self.assertEqual(m.pillars_passed, 66)
        self.assertEqual(m.failed_pillars, ())
        self.assertTrue(m.under_6s_budget)
        self.assertTrue(m.under_2_5s_fast_cli_budget)
        self.assertLess(m.elapsed_seconds, P361_FAST_CLI_BUDGET_SECONDS)

    def test_043_master_66_recovery_normal_mode_and_aliases_match(self) -> None:
        m1 = evaluate_realhw_66pillar_recovery_master()
        m2 = evaluate_66pillar_recovery_master()
        m3 = verify_66pillar_recovery_suite()
        m4 = verify_66pillar_recovery()
        for m in (m1, m2, m3, m4):
            self.assertTrue(m.all_passed)
            self.assertEqual(m.pillars_passed, 66)
            self.assertEqual(m.pillar_count, 66)
            self.assertEqual(m.master_66pillar_sha256, m1.master_66pillar_sha256)
            self.assertTrue(m.breathing_comp_resettable_by_camera_settings_reset)
            self.assertFalse(m.catalyst_browse_breathing_supported)
            self.assertTrue(m.catalyst_prepare_breathing_supported)
            self.assertFalse(m.round57_erratum_copyright_resettable)
            self.assertTrue(m.write_serial_still_and_movie_active)
            self.assertFalse(m.fx6_has_exif_copyright_menu)
            self.assertFalse(m.fx3_has_power_save_by_monitor)
            self.assertEqual(m.raw_firmware_bytes_leaked, 0)
            self.assertFalse(m.overall_ready_for_hardware_attach)
            self.assertTrue(m.under_6s_budget)

    def test_044_master_66_recovery_donorless_work_root_none_passes(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P361_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                m = verify_all_66_recovery_pillars()
        self.assertTrue(m.all_passed)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillars_passed, 66)
        self.assertEqual(m.pillar_count, 66)

    def test_045_master_66_recovery_env_clean_room_modes_pass(self) -> None:
        for env_key in (P361_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with patch.dict(os.environ, {env_key: "1"}, clear=False):
                m = verify_all_66_recovery_pillars()
                self.assertTrue(m.all_passed)
                self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(m.pillars_passed, 66)

    def test_046_master_66_fault_injection_fail_closed(self) -> None:
        target = MASTER_66_PILLAR_IDS[-1]
        rep = evaluate_realhw_66pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=target,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P361_STATUS_FAIL_66OF66_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 65)
        self.assertEqual(rep.failed_pillars, (target,))

    def test_047_recursive_strip_elapsed_seconds_deterministic_digest(self) -> None:
        m1 = verify_all_66_recovery_pillars(force_clean_room=True)
        m2 = verify_all_66_recovery_pillars(force_clean_room=True)
        d1 = _strip_elapsed_seconds(m1.to_dict())
        d2 = _strip_elapsed_seconds(m2.to_dict())
        self.assertEqual(d1, d2)
        self.assertEqual(m1.master_66pillar_sha256, m2.master_66pillar_sha256)
        self.assertEqual(len(m1.master_66pillar_sha256), 64)

    def test_048_cli_help_percent_escape_and_subcommands(self) -> None:
        res_top = _run_cli("--help")
        self.assertEqual(res_top.returncode, 0, res_top.stderr)
        for cmd in (
            "verify-pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault",
            "verify-pillar66-recovery",
            "verify-66pillar-recovery",
        ):
            self.assertIn(cmd, res_top.stdout)
            res_sub = _run_cli(cmd, "--help")
            self.assertEqual(res_sub.returncode, 0, f"{cmd} --help failed: {res_sub.stderr}")

    def test_049_cli_json_and_out_execution_clean_room_and_normal(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests) as td:
            out_p66 = Path(td) / "out_p66"
            out_m66 = Path(td) / "out_m66"
            res_p66 = _run_cli("verify-pillar66-recovery", "--force-clean-room", "--json", "--out", str(out_p66))
            self.assertEqual(res_p66.returncode, 0, res_p66.stderr)
            p66_data = json.loads(res_p66.stdout)
            self.assertTrue(p66_data["all_passed"])
            self.assertEqual(p66_data["status"], P361_STATUS_VERIFIED_PILLAR66_SUITE)
            self.assertEqual(p66_data["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(
                (out_p66 / "pillar66-breathing-camid-reel-copyright46-powersave-ntscpal-vault-report.json").exists()
            )

            res_m66 = _run_cli("verify-66pillar-recovery", "--force-clean-room", "--json", "--out", str(out_m66))
            self.assertEqual(res_m66.returncode, 0, res_m66.stderr)
            m66_data = json.loads(res_m66.stdout)
            self.assertTrue(m66_data["all_passed"])
            self.assertEqual(m66_data["pillar_count"], 66)
            self.assertEqual(m66_data["pillars_passed"], 66)
            self.assertEqual(m66_data["raw_firmware_bytes_leaked"], 0)
            self.assertTrue((out_m66 / "66pillar-recovery-master-report.json").exists())

    def test_050_invalid_specs_fail_closed_with_explicit_block_codes(self) -> None:
        bad_a = build_default_safe_breathing_camid_reel_sdhc_vault_spec(camera_id="?")
        ra = evaluate_breathing_camid_reel_sdhc_vault(bad_a)
        self.assertFalse(ra.passed)
        self.assertEqual(ra.block_code, P361_BLOCKED_INVALID_PILLAR66A_SPEC)

        bad_b = build_default_safe_copyright46_powersave_ntscpal_vault_spec(ntsc_pal_selector="SECAM")
        rb = evaluate_copyright46_powersave_ntscpal_vault(bad_b)
        self.assertFalse(rb.passed)
        self.assertEqual(rb.block_code, P361_BLOCKED_INVALID_PILLAR66B_SPEC)


# ---------------------------------------------------------------------------
# Parameterized Matrix Tests (bringing suite well past 130+ tests)
# ---------------------------------------------------------------------------


def _make_breathing_gate_test(
    domain: str,
    fps: int,
    raw_out: str,
    lens_info: str,
    lens_id: str,
    expect_allowed: bool,
):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            shooting_domain=domain,
            recording_fps=fps,
            raw_output=raw_out,
            breathing_comp="On",
            lens_info_status=lens_info,
            lens_id=lens_id,
            reported_breathing_errno=None if expect_allowed else P361_EOPNOTSUPP_ERRNO,
            reported_effective_breathing="On" if expect_allowed else "Off",
            reported_optical_crop_active=expect_allowed,
        )
        st = _compute_66a_from_spec(spec)
        if expect_allowed:
            self.assertIsNone(st["breathing_errno"])
            self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(spec).passed)
        elif raw_out == "On":
            self.assertIsNone(st["breathing_errno"])
            self.assertEqual(st["effective_breathing"], "Off")
            self.assertFalse(st["optical_crop_active"])
            self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(spec).passed)
        else:
            self.assertEqual(st["breathing_errno"], P361_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_breathing_camid_reel_sdhc_vault(spec).passed)
    return _test


def _make_file_name_format_test(fmt: str, exp_basename: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            file_name_format=fmt,
            camera_id="A",
            prev_camera_id="A",
            reel_number=1,
            camera_position="C",
            clip_number=1,
            title_name="C",
            capture_date_yyyymmdd="20230101",
            random_2char="AB",
            reported_clip_basename=exp_basename,
            post_file_name_format=fmt,
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(spec).passed)
    return _test


def _make_9_bypass_test(field_name: str):
    def _test(self: unittest.TestCase) -> None:
        ok = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            power_save_start_time="5 Min",
            reported_power_save_bypassed=True,
            reported_power_save_timer_effective=False,
            **{field_name: True},
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(ok).passed)

        spoof = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            power_save_start_time="5 Min",
            reported_power_save_bypassed=False,
            reported_power_save_timer_effective=True,
            **{field_name: True},
        )
        rep = evaluate_copyright46_powersave_ntscpal_vault(spoof)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P361_BLOCKED_POWERSAVE_OR_NTSCPAL_DRIFT)
    return _test


def _make_active_powersave_mode_test(mode: str):
    def _test(self: unittest.TestCase) -> None:
        timer_eff = mode != "Off"
        spec = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            power_save_start_time=mode,
            reported_power_save_timer_effective=timer_eff,
            post_power_save_start_time=mode,
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(spec).passed)
    return _test


def _make_dormant_powersave_tier_test(tier: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            power_save_start_time=tier,
            reported_power_save_errno=None,
        )
        st = _compute_66b_from_spec(spec)
        self.assertEqual(st["power_save_errno"], P361_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_copyright46_powersave_ntscpal_vault(spec).passed)
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        sa = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_breathing_camid_reel_sdhc_vault(sa).passed, expect_pass)

        sb = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_copyright46_powersave_ntscpal_vault(sb).passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        sa = build_default_safe_breathing_camid_reel_sdhc_vault_spec(
            breathing_comp="On",
            file_number_mode="Reset",
            file_name_format="Title + Date",
            camera_id="C",
            prev_camera_id="C",
            reel_number=9,
            camera_position="R",
            reported_effective_reel_number=9,
            reported_output_position="R",
            reported_menu_position_unchanged="R",
            title_name="Scene37",
            capture_date_yyyymmdd="20261118",
            reported_clip_basename="Scene37_20261118_0001",
            reset_action=reset_action,
            post_breathing_comp="On" if reset_action == "None" else P361_FX3_BREATHING_DEFAULT,
            post_file_number_mode="Series" if init else "Reset",
            post_file_name_format="Standard" if init else "Title + Date",
            post_camera_id="A" if init else "C",
            post_reel_number=1 if init else 9,
            post_camera_position="C" if init else "R",
            post_title_name=P361_FX3_TITLE_DEFAULT if init else "Scene37",
        )
        self.assertTrue(evaluate_breathing_camid_reel_sdhc_vault(sa).passed)

        sb = build_default_safe_copyright46_powersave_ntscpal_vault_spec(
            shooting_domain="Still",
            write_copyright_info="On",
            photographer_name="P" * 46,
            copyright_holder="C" * 46,
            write_serial_number="On",
            reported_still_copyright_written=True,
            reported_serial_written_on_capture=True,
            power_save_start_time="10 Sec",
            auto_power_off_temp="High",
            reported_tripod_warning_active=True,
            factory_tv_system="NTSC",
            ntsc_pal_selector="PAL",
            target_ntsc_pal_selector="PAL",
            requested_movie_fps="25p",
            requested_tc_format="NDF",
            playback_clip_system="PAL",
            reported_effective_tv_system="PAL",
            reported_non_factory_banner="Running on PAL.",
            reset_action=reset_action,
            post_write_copyright_info="Off" if init else "On",
            post_photographer_name="" if init else "P" * 46,
            post_copyright_holder="" if init else "C" * 46,
            post_write_serial_number="Off" if init else "On",
            post_power_save_start_time=P361_FX3_POWER_SAVE_DEFAULT if init else "10 Sec",
            post_auto_power_off_temp="Standard" if init else "High",
            post_ntsc_pal_selector="NTSC" if init else "PAL",
        )
        self.assertTrue(evaluate_copyright46_powersave_ntscpal_vault(sb).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase361_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_66_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_66_PILLAR_IDS[idx])
    return _test


def _make_fault_inject_pillar_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        pid = MASTER_66_PILLAR_IDS[idx]
        m = evaluate_realhw_66pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid,
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, 65)
        self.assertEqual(m.failed_pillars, (pid,))
    return _test


def _install_parameterized_tests() -> None:
    idx = 51

    # 10 Breathing Comp domain/fps/raw/lens gate cases
    breathing_cases = (
        ("Movie_24p_ok", "Movie", 24, "Off", "SUPPORT", "SEL24F14GM", True),
        ("Movie_60p_ok", "Movie", 60, "Off", "SUPPORT", "SEL24F14GM", True),
        ("Movie_100p_lock", "Movie", 100, "Off", "SUPPORT", "SEL24F14GM", False),
        ("Movie_120p_lock", "Movie", 120, "Off", "SUPPORT", "SEL24F14GM", False),
        ("SQ_60fps_ok", "S&Q", 60, "Off", "SUPPORT", "SEL24F14GM", True),
        ("SQ_100fps_lock", "S&Q", 100, "Off", "SUPPORT", "SEL24F14GM", False),
        ("SQ_120fps_lock", "S&Q", 120, "Off", "SUPPORT", "SEL24F14GM", False),
        ("Still_lock", "Still", 24, "Off", "SUPPORT", "SEL24F14GM", False),
        ("RAW_lock", "Movie", 24, "On", "SUPPORT", "SEL24F14GM", False),
        ("Lens_NOT_SUPPORT_lock", "Movie", 24, "Off", "NOT_SUPPORT", "SEL100F28GM_MACRO_0.57M_1.0M", False),
    )
    for label, dom, fps, raw_o, linfo, lid, exp in breathing_cases:
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_breathing_{label}",
            _make_breathing_gate_test(dom, fps, raw_o, linfo, lid, exp),
        )
        idx += 1

    # 5 File Name Format modes
    fmt_cases = (
        ("Standard", "C0001"),
        ("Cam ID + Reel#", "A001C001_230101AB"),
        ("Title", "C_0001"),
        ("Date + Title", "20230101_C_0001"),
        ("Title + Date", "C_20230101_0001"),
    )
    for fmt, base in fmt_cases:
        clean = fmt.lower().replace(" ", "_").replace("+", "plus").replace("#", "num")
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_file_name_format_{clean}",
            _make_file_name_format_test(fmt, base),
        )
        idx += 1

    # 9 Power Save bypass conditions
    for cond in P361_FX3_POWER_SAVE_9_BYPASS_CONDITIONS:
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_powersave_bypass_{cond}",
            _make_9_bypass_test(cond),
        )
        idx += 1

    # 6 Active Power Save Start Time modes
    for mode in P361_FX3_POWER_SAVE_MODES:
        clean = mode.lower().replace(" ", "_")
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_powersave_active_mode_{clean}",
            _make_active_powersave_mode_test(mode),
        )
        idx += 1

    # 5 Dormant Power Save tiers
    for tier in P361_FX3_POWER_SAVE_DORMANT_TIERS:
        clean = tier.lower().replace(" ", "_")
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_powersave_dormant_tier_{clean}",
            _make_dormant_powersave_tier_test(tier),
        )
        idx += 1

    # 18 Slot-1 Write Firewall actions x errno pairs (6 actions x 3 errnos)
    for action in sorted(P361_WRITE_MUTATING_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP", "EBUSY"):
            setattr(
                Phase361Pillar66VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 3 Reset Action matrices
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 18 Individual Donor checks
    for d_i in range(18):
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # Selected key pillars + final 66th pillar across MASTER_66_PILLAR_IDS (17 tests)
    for p_i in (*range(0, 66, 5), 63, 64, 65):
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1

    # Fault injection across 5 key pillars incl. 65 & 66
    for p_i in (0, 21, 63, 64, 65):
        setattr(
            Phase361Pillar66VerifierTests,
            f"test_{idx:03d}_fault_inject_pillar_{p_i+1:02d}",
            _make_fault_inject_pillar_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
