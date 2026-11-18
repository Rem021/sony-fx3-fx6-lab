"""Phase 366 (Pillar 67 & 67/67 Milestone) unit tests:
Wave-65 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` empirical telemetry across 4 sub-pillars:
- Pillar 67A (`[Zoom Range]` `Optical zoom only` / `ClearImage Zoom` 1.5x 4K & 2.0x HD / `Digital Zoom`
  4.0x Movie & up to 8.0x Still S; Reset-resistant `Zoom Range` + `Zoom Ring Rotate` vs Resettable
  `Zoom Lever Speed` `1st=3`/`2nd=8` `Standby/Movie Rec` + `Custom Key Z. Speed` `1..8` def `3` +
  `Remote Zoom Speed` `Variable`/`Fixed 1..8` def `3`; CIZ/Digital lockouts on RAW / 120p / S&Q>=100 /
  HDMI RAW / Breathing Comp + forced Center AF / `[Multi]` Metering vs FX6 2-option `Zoom Type` +
  `Handle Zoom`; `[Auto Slow Shutter]` Movie-only `On` def `Can be reset` with 6+ lockouts, Reset-resistant
  `[ISO Range Limit]`, Still-only `[ISO AUTO Min. SS]` + 1/250s flash override, and Dual Base ISO
  curve table `800/12800`, `640/12800`, `100/2000`, `80/1600`, `64/1280`, `50/1000`).
- Pillar 67B (Dormant `Lossless Comp` `.ARW` (`L/M/S`) rejection `EOPNOTSUPP=95` leaving only
  `Compressed` / `Uncompressed` 14-bit; `[HLG Still Image]` `BT.2100` ISO floor 100/125; `Sort Recording`
  + `[Auto Switch Media]` spillover blocked by Tier-0 `Slot 1 EROFS=30`; Reset-resistant `Setup -> USB`
  4-mode `[USB Connection Mode]` + `[USB LUN Setting] = Single` (`Slot 1`-ONLY!) macOS MSC hazard guard;
  `NP-FZ100` mandatory even on `9V/3A` USB-C PD + `DC-C1` `>=65W` + `5A e-Marked` cable vs FX6 `19.5V DC IN`;
  and Dual FX3/FX6 Dormant `UVC USB Streaming` (`usb_f_uvc.ko` / `g_webcam.ko`) firewall `EOPNOTSUPP=95`
  with `raw_firmware_bytes_leaked == 0` and `overall_ready_for_hardware_attach == False`).
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
    MASTER_67_PILLAR_COUNT,
    MASTER_67_PILLAR_IDS,
    MASTER_67_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P366_AIRPLANE_MODE_FORCED_ON,
    P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT,
    P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT,
    P366_BLOCKED_INVALID_PILLAR67A_SPEC,
    P366_BLOCKED_INVALID_PILLAR67B_SPEC,
    P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT,
    P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT,
    P366_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P366_CONCURRENT_CEILING_SECONDS,
    P366_CROSS_MODEL_FLASH_AUTHORIZED,
    P366_DONOR_FX3_APPFW_702_RELPATH,
    P366_DONOR_FX3_BACKUP_BIN_RELPATH,
    P366_DONOR_FX3_G_WEBCAM_KO_RELPATH,
    P366_DONOR_FX3_USB_F_UVC_KO_RELPATH,
    P366_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH,
    P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH,
    P366_DONOR_FX6_APPFW_601_RELPATH,
    P366_DONOR_FX6_G_WEBCAM_KO_RELPATH,
    P366_DONOR_FX6_USB_F_UVC_KO_RELPATH,
    P366_DONOR_FX6_USBG_STILLIMAGE_KO_RELPATH,
    P366_DONOR_FX6_USBG_STORAGE_KO_RELPATH,
    P366_DONOR_FX6_UXC_EN_RELPATH,
    P366_DONOR_INSPECT_BUDGET_SECONDS,
    P366_EMMC_WRITES_AUTHORIZED,
    P366_ENV_CLEAN_ROOM_TEST,
    P366_EOPNOTSUPP_ERRNO,
    P366_FAST_CLI_BUDGET_SECONDS,
    P366_FX3_ACTIVE_RAW_FILE_TYPES,
    P366_FX3_ACTIVE_USB_CONNECTION_MODES,
    P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT,
    P366_FX3_AUTO_SLOW_SHUTTER_RESETTABLE,
    P366_FX3_DORMANT_RAW_FILE_TYPES,
    P366_FX3_DUAL_BASE_ISO_CURVES,
    P366_FX3_FW_VERSION,
    P366_FX3_HAS_DORMANT_LOSSLESS_ARW_EXPOSED,
    P366_FX3_HAS_NATIVE_UVC_STREAMING,
    P366_FX3_HELPGUIDE_ID,
    P366_FX3_ISO_AUTO_MIN_SS_DEFAULT,
    P366_FX3_ISO_RANGE_LIMIT_RESETTABLE,
    P366_FX3_MODEL_ID,
    P366_FX3_MODEL_NAME,
    P366_FX3_ZOOM_LEVER_1ST_DEFAULT,
    P366_FX3_ZOOM_LEVER_2ND_DEFAULT,
    P366_FX3_ZOOM_RANGE_DEFAULT,
    P366_FX3_ZOOM_RANGE_RESETTABLE,
    P366_FX3_ZOOM_RING_ROTATE_DEFAULT,
    P366_FX3_ZOOM_RING_ROTATE_RESETTABLE,
    P366_FX3_ZOOM_SPEED_RESETTABLE,
    P366_FX6_DONOR_FW_VERSION,
    P366_FX6_DONOR_MODEL_NAME,
    P366_FX6_HAS_DIGITAL_ZOOM,
    P366_FX6_HAS_ISO_AUTO_MIN_SS,
    P366_FX6_HAS_NATIVE_UVC_STREAMING,
    P366_FX6_HAS_STILL_ARW_HLG_PIPELINE,
    P366_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P366_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P366_PILLAR_67A_SCENARIO_IDS,
    P366_PILLAR_67B_SCENARIO_IDS,
    P366_PINNED_FX3_BACKUP_BIN_SHA256,
    P366_PINNED_FX3_G_WEBCAM_KO_SHA256,
    P366_PINNED_FX3_USB_F_UVC_KO_SHA256,
    P366_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256,
    P366_PINNED_FX3_USBG_STORAGE_KO_SHA256,
    P366_PINNED_FX6_G_WEBCAM_KO_SHA256,
    P366_PINNED_FX6_USB_F_UVC_KO_SHA256,
    P366_PINNED_FX6_USBG_STILLIMAGE_KO_SHA256,
    P366_PINNED_FX6_USBG_STORAGE_KO_SHA256,
    P366_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P366_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P366_STATUS_FAIL_67OF67_AGGREGATOR,
    P366_STATUS_VERIFIED_67OF67_AGGREGATOR,
    P366_STATUS_VERIFIED_PILLAR67_SUITE,
    P366_STATUS_VERIFIED_PILLAR_67A,
    P366_STATUS_VERIFIED_PILLAR_67B,
    P366_WRITE_MUTATING_VAULT_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE366_MASTER_SCHEMA,
    PHASE366_PHASE_NUMBER,
    PHASE366_SCHEMA,
    PHASE366_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec,
    build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec,
    compute_expected_arw_hlg_sort_usblun_uvc_state,
    compute_expected_zoom_ciz_autoslow_baseiso_state,
    evaluate_67pillar_recovery_master,
    evaluate_arw_hlg_sort_usblun_uvc_vault,
    evaluate_realhw_67pillar_recovery_master,
    evaluate_zoom_ciz_autoslow_baseiso_vault,
    inspect_phase366_donors_readonly,
    run_pillar67_standalone_suite,
    run_pillar67a_zoom_ciz_autoslow_baseiso_vault_6_scenario_suite,
    run_pillar67b_arw_hlg_sort_usblun_uvc_vault_6_scenario_suite,
    verify_67pillar_recovery,
    verify_67pillar_recovery_suite,
    verify_all_67_recovery_pillars,
    verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault,
    verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault,
)

CI_RELAXED_CLEAN_ROOM_BUDGET_S = 5.0


def _wave65_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P366_DONOR_FX3_APPFW_702_RELPATH,
        P366_DONOR_FX3_BACKUP_BIN_RELPATH,
        P366_DONOR_FX3_USBG_STORAGE_KO_RELPATH,
        P366_DONOR_FX3_USB_F_UVC_KO_RELPATH,
        P366_DONOR_FX6_APPFW_601_RELPATH,
        P366_DONOR_FX6_USB_F_UVC_KO_RELPATH,
        P366_DONOR_FX6_UXC_EN_RELPATH,
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


def _compute_67a_from_spec(spec: fr.ZoomCizAutoSlowBaseIsoVaultSpec) -> dict[str, object]:
    return compute_expected_zoom_ciz_autoslow_baseiso_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        recording_fps=spec.recording_fps,
        movie_resolution=spec.movie_resolution,
        still_file_format=spec.still_file_format,
        still_image_size=spec.still_image_size,
        apsc_s35_on=spec.apsc_s35_on,
        raw_output=spec.raw_output,
        breathing_comp=spec.breathing_comp,
        zoom_range=spec.zoom_range,
        zoom_ring_rotate=spec.zoom_ring_rotate,
        zoom_lever_1st_stby=spec.zoom_lever_1st_stby,
        zoom_lever_1st_rec=spec.zoom_lever_1st_rec,
        zoom_lever_2nd_stby=spec.zoom_lever_2nd_stby,
        zoom_lever_2nd_rec=spec.zoom_lever_2nd_rec,
        custom_key_zoom_speed_stby=spec.custom_key_zoom_speed_stby,
        custom_key_zoom_speed_rec=spec.custom_key_zoom_speed_rec,
        remote_zoom_speed_type=spec.remote_zoom_speed_type,
        remote_zoom_fixed_stby=spec.remote_zoom_fixed_stby,
        remote_zoom_fixed_rec=spec.remote_zoom_fixed_rec,
        fx6_sq_motion=spec.fx6_sq_motion,
        fx6_codec=spec.fx6_codec,
        fx6_handle_zoom_mode=spec.fx6_handle_zoom_mode,
        exposure_mode=spec.exposure_mode,
        iso_setting=spec.iso_setting,
        flexible_exp_manual_shutter=spec.flexible_exp_manual_shutter,
        log_shooting_mode=spec.log_shooting_mode,
        shutter_mode=spec.shutter_mode,
        auto_slow_shutter=spec.auto_slow_shutter,
        iso_auto_min_ss=spec.iso_auto_min_ss,
        flash_active=spec.flash_active,
        gamma_curve_key=spec.gamma_curve_key,
        hlg_still_image=spec.hlg_still_image,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_67b_from_spec(spec: fr.ArwHlgSortUsbLunUvcVaultSpec) -> dict[str, object]:
    return compute_expected_arw_hlg_sort_usblun_uvc_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        dro_bracket_active=spec.dro_bracket_active,
        still_file_format=spec.still_file_format,
        raw_file_type=spec.raw_file_type,
        jpeg_heif_switch=spec.jpeg_heif_switch,
        hlg_still_image=spec.hlg_still_image,
        rec_media_mode=spec.rec_media_mode,
        auto_switch_media=spec.auto_switch_media,
        slot2_full_or_unready=spec.slot2_full_or_unready,
        usb_connection_mode=spec.usb_connection_mode,
        usb_lun_setting=spec.usb_lun_setting,
        host_os_is_macos=spec.host_os_is_macos,
        usb_power_supply=spec.usb_power_supply,
        npfz100_present_with_charge=spec.npfz100_present_with_charge,
        usb_pd_watts=spec.usb_pd_watts,
        dc_coupler_model=spec.dc_coupler_model,
        cable_emarked_amps=spec.cable_emarked_amps,
        fx6_dc_in_volts=spec.fx6_dc_in_volts,
        uvc_streaming_requested=spec.uvc_streaming_requested,
        network_streaming_active=spec.network_streaming_active,
        streaming_transport=spec.streaming_transport,
        movie_rec_during_streaming=spec.movie_rec_during_streaming,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _run_cli(*args: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = (
        f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs/fx3-safety'}:"
        f"{REPO_ROOT / 'outputs/fx3-firmware-lab'}:{REPO_ROOT / 'outputs/fx3-vm'}"
    )
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


class Phase366Pillar67VerifierTests(unittest.TestCase):
    """Comprehensive Phase 366 Pillar 67 (`67A`/`67B`) & `67/67` Master Recovery tests."""

    # ------------------------------------------------------------------
    # 1. Safety Redlines, Metadata & 67-Pillar Spec Sanity
    # ------------------------------------------------------------------

    def test_001_phase366_metadata_and_67pillar_inventory(self) -> None:
        self.assertEqual(PHASE366_PHASE_NUMBER, 366)
        self.assertEqual(PHASE366_VERSION, "1.0.0")
        self.assertTrue(PHASE366_SCHEMA.startswith("realhw_67pillar_"))
        self.assertEqual(PHASE366_MASTER_SCHEMA, "realhw_67pillar_recovery_master_v1")
        self.assertEqual(MASTER_67_PILLAR_COUNT, 67)
        self.assertEqual(len(MASTER_67_PILLAR_SPECS), 67)
        self.assertEqual(len(MASTER_67_PILLAR_IDS), 67)
        self.assertEqual(
            MASTER_67_PILLAR_IDS[-1],
            "pillar67_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault",
        )
        self.assertEqual(P366_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P366_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P366_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P366_FX3_FW_VERSION, "7.02")
        self.assertEqual(P366_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P366_FX6_DONOR_FW_VERSION, "6.01")

    def test_002_hard_locked_safety_flags_and_zero_tx_redlines(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P366_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P366_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P366_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        for false_flag in (
            PERSISTENT_EMMC_WRITES_AUTHORIZED,
            SPI_NOR_WRITE_AUTHORIZED,
            EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            ISP_WRITE_AUTHORIZED,
            PERSISTENT_WRITE_RELEASE,
            ALLOW_BOOT_PARTITION_TARGETING,
            ALLOW_DESTRUCTIVE_FASTBOOT,
            ALLOW_PERSISTENT_JIRITSU_WRITES,
            ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
            LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            OVERALL_READY_FOR_HARDWARE_ATTACH,
            CROSS_MODEL_FLASH_AUTHORIZED,
            BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
            P366_EMMC_WRITES_AUTHORIZED,
            P366_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            P366_OVERALL_READY_FOR_HARDWARE_ATTACH,
            P366_CROSS_MODEL_FLASH_AUTHORIZED,
            P366_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
        ):
            self.assertFalse(false_flag)
        for zero_cnt in (
            OTP_FUSE_TOUCHES,
            OTP_FUSE_WRITES,
            RPMB_COUNTER_INCREMENTS,
            PASSIVE_TX_BYTES_EMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_cnt, 0)

    def test_003_public_package_exports_complete_and_no_shadowing(self) -> None:
        for sym in (
            "evaluate_realhw_67pillar_recovery_master",
            "evaluate_67pillar_recovery_master",
            "verify_67pillar_recovery_suite",
            "verify_67pillar_recovery",
            "verify_all_67_recovery_pillars",
            "verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault",
            "verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault",
            "run_pillar67_standalone_suite",
            "inspect_phase366_donors_readonly",
            "evaluate_realhw_66pillar_recovery_master",
            "verify_66pillar_recovery",
        ):
            self.assertTrue(hasattr(fr, sym), f"Missing export: {sym}")
        self.assertEqual(fr.MASTER_66_PILLAR_COUNT, 66)
        self.assertEqual(fr.MASTER_67_PILLAR_COUNT, 67)

    # ------------------------------------------------------------------
    # 2. 25 Bounded O_RDONLY Donors, Synthetic Fallback & work_root=None
    # ------------------------------------------------------------------

    def test_004_donor_inspection_clean_room_25_donors_under_budget(self) -> None:
        snap = inspect_phase366_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 25)
        self.assertEqual(len(snap.artifacts), 25)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P366_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(by_id["fx3_usbg_storage_ko"].digest_sha256, P366_PINNED_FX3_USBG_STORAGE_KO_SHA256)
        self.assertEqual(by_id["fx3_usbg_stillimage_ko"].digest_sha256, P366_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256)
        self.assertEqual(by_id["fx3_usb_f_uvc_ko"].digest_sha256, P366_PINNED_FX3_USB_F_UVC_KO_SHA256)
        self.assertEqual(by_id["fx3_g_webcam_ko"].digest_sha256, P366_PINNED_FX3_G_WEBCAM_KO_SHA256)
        self.assertEqual(by_id["fx6_usbg_storage_ko"].digest_sha256, P366_PINNED_FX6_USBG_STORAGE_KO_SHA256)
        self.assertEqual(by_id["fx6_usbg_stillimage_ko"].digest_sha256, P366_PINNED_FX6_USBG_STILLIMAGE_KO_SHA256)
        self.assertEqual(by_id["fx6_usb_f_uvc_ko"].digest_sha256, P366_PINNED_FX6_USB_F_UVC_KO_SHA256)
        self.assertEqual(by_id["fx6_g_webcam_ko"].digest_sha256, P366_PINNED_FX6_G_WEBCAM_KO_SHA256)

    def test_005_donor_inspection_normal_mode_uses_local_o_rdonly_when_present(self) -> None:
        snap = inspect_phase366_donors_readonly()
        if _wave65_donors_present() and not os.environ.get(P366_ENV_CLEAN_ROOM_TEST) and not os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM"):
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 25)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned, f"Donor digest mismatch: {art.artifact_id}")

    def test_006_donor_inspection_donorless_work_root_none_falls_back_cleanly(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P366_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                snap = inspect_phase366_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 25)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_007_donor_inspection_respects_both_clean_room_env_vars(self) -> None:
        for env_key in (P366_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with patch.dict(os.environ, {env_key: "1"}, clear=False):
                snap = inspect_phase366_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 25)

    # ------------------------------------------------------------------
    # 3. Pillar 67A: Zoom Range, 8-Speed Split, Auto Slow Shutter,
    #    ISO Range Limit, Still ISO AUTO Min. SS & Dual Base ISO Curves
    # ------------------------------------------------------------------

    def test_008_pillar67a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec()
        report = evaluate_zoom_ciz_autoslow_baseiso_vault(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P366_STATUS_VERIFIED_PILLAR_67A)
        self.assertIsNone(report.block_code)
        self.assertTrue(report.zoom_ciz_8speed_reset_verified)
        self.assertTrue(report.autoslow_minss_dual_base_iso_verified)
        self.assertTrue(report.slot1_vault_and_h0_h3_verified)
        self.assertEqual(report.slot1_data_sector_writes, 0)
        self.assertEqual(report.physical_device_writes, 0)

    def test_009_pillar67a_reset_split_zoom_range_ring_vs_speeds_verified(self) -> None:
        self.assertFalse(P366_FX3_ZOOM_RANGE_RESETTABLE)
        self.assertFalse(P366_FX3_ZOOM_RING_ROTATE_RESETTABLE)
        self.assertTrue(P366_FX3_ZOOM_SPEED_RESETTABLE)
        self.assertEqual(P366_FX3_ZOOM_RANGE_DEFAULT, "Optical zoom only")
        self.assertEqual(P366_FX3_ZOOM_RING_ROTATE_DEFAULT, "Left(W)/Right(T)")
        self.assertEqual(P366_FX3_ZOOM_LEVER_1ST_DEFAULT, 3)
        self.assertEqual(P366_FX3_ZOOM_LEVER_2ND_DEFAULT, 8)

        # Spoofing Camera Settings Reset wiping Zoom Range to Optical fails
        bad_wipe_range = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            zoom_range="ClearImage Zoom",
            reset_action="Camera Settings Reset",
            post_zoom_range="Optical zoom only",
        )
        rep1 = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_wipe_range)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT)

        # Spoofing Camera Settings Reset NOT resetting Zoom Lever Speed 2nd back to 8 fails
        bad_keep_spd = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            zoom_lever_2nd_stby=5,
            reset_action="Camera Settings Reset",
            post_zoom_lever_2nd_stby=5,
        )
        rep2 = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_keep_spd)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P366_BLOCKED_ZOOM_CIZ_OR_8SPEED_RESET_DRIFT)

    def test_010_pillar67a_ciz_digital_forces_center_af_multi_metering_no_tracking(self) -> None:
        for zr, expected_af in (("Optical zoom only", False), ("ClearImage Zoom", True), ("Digital Zoom", True)):
            scale = 1.0 if zr == "Optical zoom only" else (1.5 if zr == "ClearImage Zoom" else 4.0)
            ok = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                zoom_range=zr,
                reported_effective_zoom_range=zr,
                reported_max_zoom_scale=scale,
                reported_focus_area_locked_center=expected_af,
                reported_metering_locked_multi=expected_af,
                reported_face_eye_tracking_disabled=expected_af,
                post_zoom_range=zr,
            )
            self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(ok).passed)

        spoof = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            zoom_range="ClearImage Zoom",
            reported_effective_zoom_range="ClearImage Zoom",
            reported_max_zoom_scale=1.5,
            reported_focus_area_locked_center=False,
            reported_face_eye_tracking_disabled=False,
        )
        self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(spoof).passed)

    def test_011_pillar67a_ciz_lockouts_raw_120p_sq100_hdmi_raw_breathing_smart_l(self) -> None:
        lockout_cases = (
            {"shooting_domain": "Still", "still_file_format": "RAW", "zoom_range": "ClearImage Zoom"},
            {"shooting_domain": "Still", "still_file_format": "RAW & HEIF", "zoom_range": "Digital Zoom"},
            {"shooting_domain": "Movie", "recording_fps": 120, "zoom_range": "ClearImage Zoom"},
            {"shooting_domain": "S&Q", "recording_fps": 100, "zoom_range": "Digital Zoom"},
            {"shooting_domain": "Movie", "raw_output": "On", "zoom_range": "ClearImage Zoom"},
            {"shooting_domain": "Movie", "breathing_comp": "On", "zoom_range": "ClearImage Zoom"},
            {"shooting_domain": "Movie", "recording_fps": 24, "zoom_range": "Smart Zoom"},
            {"shooting_domain": "Still", "still_image_size": "L", "zoom_range": "Smart Zoom"},
        )
        for kw in lockout_cases:
            spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(**kw)
            st = _compute_67a_from_spec(spec)
            self.assertEqual(st["zoom_errno"], P366_EOPNOTSUPP_ERRNO, f"Expected lockout for {kw}")
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)

    def test_012_pillar67a_fx6_2option_zoom_zero_digital_and_handle_zoom_contrast(self) -> None:
        self.assertFalse(P366_FX6_HAS_DIGITAL_ZOOM)
        ok_fx6 = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            camera_model=P366_FX6_DONOR_MODEL_NAME,
            fw_version=P366_FX6_DONOR_FW_VERSION,
            zoom_range="ClearImage Zoom",
            fx6_handle_zoom_mode="High",
            reported_effective_zoom_range="ClearImage Zoom",
            reported_max_zoom_scale=1.5,
            reported_focus_area_locked_center=False,
            reported_metering_locked_multi=False,
            reported_face_eye_tracking_disabled=False,
            auto_slow_shutter="Off",
            reported_effective_auto_slow_shutter="Off",
            log_shooting_mode="Cine EI",
            gamma_curve_key="Cine EI",
            reported_base_iso_low=800,
            reported_base_iso_high=12800,
            reported_base_iso_menu_exposed=True,
            reset_action="None",
            post_zoom_range="ClearImage Zoom",
            post_auto_slow_shutter="Off",
        )
        self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(ok_fx6).passed)

        # FX6 rejects Digital Zoom + S&Q > 60fps CIZ + RAW codec CIZ
        for kw in (
            {"zoom_range": "Digital Zoom"},
            {"fx6_sq_motion": "On", "recording_fps": 120, "zoom_range": "ClearImage Zoom"},
            {"fx6_codec": "RAW", "zoom_range": "ClearImage Zoom"},
        ):
            bad_fx6 = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                camera_model=P366_FX6_DONOR_MODEL_NAME,
                fw_version=P366_FX6_DONOR_FW_VERSION,
                reset_action="None",
                **kw,
            )
            self.assertEqual(_compute_67a_from_spec(bad_fx6)["zoom_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(bad_fx6).passed)

    def test_013_pillar67a_autoslow_shutter_6plus_lockouts_enforced(self) -> None:
        self.assertTrue(P366_FX3_AUTO_SLOW_SHUTTER_RESETTABLE)
        self.assertEqual(P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT, "On")
        lockouts = (
            {"shooting_domain": "S&Q"},
            {"shooting_domain": "Still"},
            {"exposure_mode": "S"},
            {"exposure_mode": "M"},
            {"iso_setting": "ISO 800"},
            {"exposure_mode": "Flexible Exp.", "flexible_exp_manual_shutter": True},
            {"log_shooting_mode": "Cine EI"},
            {"log_shooting_mode": "Cine EI Quick"},
            {"shutter_mode": "Angle"},
        )
        for kw in lockouts:
            bad = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                zoom_range="Optical zoom only",
                reported_effective_zoom_range="Optical zoom only",
                reported_max_zoom_scale=1.0,
                reported_focus_area_locked_center=False,
                reported_metering_locked_multi=False,
                reported_face_eye_tracking_disabled=False,
                post_zoom_range="Optical zoom only",
                auto_slow_shutter="On",
                reported_auto_slow_errno=None,
                **kw,
            )
            st = _compute_67a_from_spec(bad)
            self.assertEqual(st["auto_slow_errno"], P366_EOPNOTSUPP_ERRNO, f"Expected lock for {kw}")
            rep = evaluate_zoom_ciz_autoslow_baseiso_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT)

    def test_014_pillar67a_still_iso_auto_min_ss_and_flash_override(self) -> None:
        self.assertFalse(P366_FX6_HAS_ISO_AUTO_MIN_SS)
        self.assertEqual(P366_FX3_ISO_AUTO_MIN_SS_DEFAULT, "STD")
        self.assertFalse(P366_FX3_ISO_RANGE_LIMIT_RESETTABLE)
        # Still A + ISO AUTO + Flash -> flash override True
        ok_still = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            shooting_domain="Still",
            exposure_mode="A",
            iso_setting="ISO AUTO",
            zoom_range="Optical zoom only",
            reported_effective_zoom_range="Optical zoom only",
            reported_max_zoom_scale=1.0,
            reported_focus_area_locked_center=False,
            reported_metering_locked_multi=False,
            reported_face_eye_tracking_disabled=False,
            post_zoom_range="Optical zoom only",
            auto_slow_shutter="Off",
            iso_auto_min_ss="FASTER",
            flash_active=True,
            reported_effective_auto_slow_shutter="Off",
            reported_min_ss_flash_override=True,
            reset_action="None",
            post_auto_slow_shutter="Off",
            post_iso_auto_min_ss="FASTER",
        )
        self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(ok_still).passed)

        # Movie or S&Q setting non-STD ISO AUTO Min. SS must reject
        for dom in ("Movie", "S&Q"):
            bad = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
                shooting_domain=dom,
                exposure_mode="P",
                iso_setting="ISO AUTO",
                auto_slow_shutter="Off",
                iso_auto_min_ss="1/500",
                reported_iso_auto_min_ss_errno=None,
            )
            self.assertEqual(_compute_67a_from_spec(bad)["iso_auto_min_ss_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(bad).passed)

    def test_015_pillar67a_dual_base_iso_curve_matrix_and_hlg_still_floor(self) -> None:
        # HLG Still forces low floor to at least 100
        ok_hlg_floor = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            shooting_domain="Still",
            zoom_range="Optical zoom only",
            reported_effective_zoom_range="Optical zoom only",
            reported_max_zoom_scale=1.0,
            reported_focus_area_locked_center=False,
            reported_metering_locked_multi=False,
            reported_face_eye_tracking_disabled=False,
            post_zoom_range="Optical zoom only",
            auto_slow_shutter="Off",
            reported_effective_auto_slow_shutter="Off",
            gamma_curve_key="PP HLG1",
            hlg_still_image="On",
            reported_base_iso_low=100,
            reported_base_iso_high=2000,
            reported_base_iso_menu_exposed=False,
            reset_action="None",
            post_auto_slow_shutter="Off",
        )
        self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(ok_hlg_floor).passed)

        # Spoofing Flexible ISO base low=800 instead of 640 fails
        bad_flex = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            log_shooting_mode="Flexible ISO",
            gamma_curve_key="Flexible ISO (S-Log3)",
            reported_base_iso_low=800,
            reported_base_iso_high=12800,
            reported_base_iso_menu_exposed=False,
        )
        rep = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_flex)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P366_BLOCKED_AUTOSLOW_MINSS_OR_DUAL_BASE_ISO_DRIFT)

    def test_016_pillar67a_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        bad_ovl = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(overlay_dir="/nflasha/67a")
        r1 = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_ovl)
        self.assertFalse(r1.passed)
        self.assertEqual(r1.block_code, P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(backup_bin_h3_sha256="f" * 64)
        r2 = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_h3)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.block_code, P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    # ------------------------------------------------------------------
    # 4. Pillar 67B: Dormant Lossless ARW, HLG Still, Sort Rec Spillover,
    #    USB LUN Single (Slot 1-Only!) macOS MSC Hazard, NP-FZ100 PD & UVC
    # ------------------------------------------------------------------

    def test_017_pillar67b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec()
        report = evaluate_arw_hlg_sort_usblun_uvc_vault(spec)
        self.assertTrue(report.passed)
        self.assertEqual(report.status, P366_STATUS_VERIFIED_PILLAR_67B)
        self.assertIsNone(report.block_code)
        self.assertTrue(report.arw_hlg_sort_spillover_verified)
        self.assertTrue(report.usblun_single_npfz100_uvc_firewall_verified)
        self.assertTrue(report.overlay_and_h0_h3_verified)
        self.assertEqual(report.slot1_data_sector_writes, 0)

    def test_018_pillar67b_active_arw_compressed_uncompressed_vs_dormant_lossless_rejected(self) -> None:
        self.assertFalse(P366_FX3_HAS_DORMANT_LOSSLESS_ARW_EXPOSED)
        self.assertEqual(P366_FX3_ACTIVE_RAW_FILE_TYPES, ("Compressed", "Uncompressed"))
        for active_raw in P366_FX3_ACTIVE_RAW_FILE_TYPES:
            ok = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                raw_file_type=active_raw,
                reset_action="Camera Settings Reset",
                post_raw_file_type="Compressed",
            )
            self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(ok).passed)

        for dormant_raw in P366_FX3_DORMANT_RAW_FILE_TYPES:
            bad = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                raw_file_type=dormant_raw,
                reported_raw_file_type_errno=None,
            )
            st = _compute_67b_from_spec(bad)
            self.assertEqual(st["raw_file_type_errno"], P366_EOPNOTSUPP_ERRNO)
            rep = evaluate_arw_hlg_sort_usblun_uvc_vault(bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT)

    def test_019_pillar67b_hlg_still_requires_heif_pure_and_pasm_no_dro(self) -> None:
        for heif_mode in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
            ok_hlg = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                still_file_format="HEIF",
                jpeg_heif_switch=heif_mode,
                exposure_mode="A",
                dro_bracket_active=False,
                hlg_still_image="On",
                reported_effective_hlg_still="On",
                reported_hlg_bt2100_active=True,
                reported_hlg_pp_dro_disabled=True,
                reset_action="None",
                post_jpeg_heif_switch=heif_mode,
                post_hlg_still_image="On",
            )
            self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(ok_hlg).passed)

        bad_cases = (
            {"still_file_format": "JPEG", "jpeg_heif_switch": "JPEG"},
            {"still_file_format": "RAW & HEIF", "jpeg_heif_switch": "HEIF(4:2:0)"},
            {"still_file_format": "HEIF", "jpeg_heif_switch": "HEIF(4:2:0)", "exposure_mode": "iAuto"},
            {"still_file_format": "HEIF", "jpeg_heif_switch": "HEIF(4:2:0)", "dro_bracket_active": True},
        )
        for kw in bad_cases:
            bad = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                hlg_still_image="On",
                reported_hlg_still_errno=None,
                **kw,
            )
            self.assertEqual(_compute_67b_from_spec(bad)["hlg_still_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_arw_hlg_sort_usblun_uvc_vault(bad).passed)

    def test_020_pillar67b_sort_recording_auto_switch_spillover_slot1_blocked_erofs(self) -> None:
        # Read-only audit detects spillover target without mutation -> passes
        audit = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            rec_media_mode="Sort Recording",
            auto_switch_media="On",
            slot2_full_or_unready=True,
            reported_sort_spillover_targets_slot1=True,
            requested_vault_action="READ_ONLY_AUDIT",
            reported_vault_action_allowed=True,
            reset_action="None",
            post_rec_media_mode="Sort Recording",
        )
        self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(audit).passed)

        # Attempting physical Slot 1 write via Sort spillover fails with SLOT1_VAULT_WRITE_FIREWALL
        write_try = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            rec_media_mode="Sort Recording",
            auto_switch_media="On",
            slot2_full_or_unready=True,
            reported_sort_spillover_targets_slot1=True,
            requested_vault_slot=1,
            requested_vault_action="CARD_WRITE_STILL_ARW_HIF_SORT_SPILLOVER",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
            slot1_data_sector_writes=4096,
            reset_action="None",
            post_rec_media_mode="Sort Recording",
        )
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(write_try)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P366_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_021_pillar67b_usb_lun_single_exposes_slot1_only_not_hiding_slot1(self) -> None:
        # Truth table: MSC + Single -> slot1=True, slot2=False; MSC + Multi -> slot1=True, slot2=True; MTP -> slot1=True, slot2=False
        for mode, lun, exp_s1, exp_s2 in (
            ("MassStorage(MSC)", "Single", True, False),
            ("MassStorage(MSC)", "Multi", True, True),
            ("MTP", "Multi", True, False),
            ("Remote Shooting", "Single", False, False),
            ("Sel. When Connect", "Single", False, False),
        ):
            st = compute_expected_arw_hlg_sort_usblun_uvc_state(
                camera_model=P366_FX3_MODEL_NAME,
                fw_version=P366_FX3_FW_VERSION,
                shooting_domain="Still",
                exposure_mode="A",
                dro_bracket_active=False,
                still_file_format="JPEG",
                raw_file_type="Compressed",
                jpeg_heif_switch="JPEG",
                hlg_still_image="Off",
                rec_media_mode="Slot 1",
                auto_switch_media="Off",
                slot2_full_or_unready=False,
                usb_connection_mode=mode,
                usb_lun_setting=lun,
                host_os_is_macos=True,
                usb_power_supply="On",
                npfz100_present_with_charge=True,
                usb_pd_watts=27,
                dc_coupler_model="",
                cable_emarked_amps=3,
                fx6_dc_in_volts=19.5,
                uvc_streaming_requested=False,
                network_streaming_active=False,
                streaming_transport="USB-LAN",
                movie_rec_during_streaming="Disable",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                reset_action="None",
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="READ_ONLY_AUDIT",
            )
            self.assertEqual(st["slot1_exposed_to_host"], exp_s1)
            self.assertEqual(st["slot2_exposed_to_host"], exp_s2)
            self.assertEqual(st["macos_msc_host_blocked"], exp_s1)

        # Live macOS MSC Single mount MUST fail closed
        bad_msc = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Single",
            host_os_is_macos=True,
            reported_slot1_exposed_to_host=True,
            reported_slot2_exposed_to_host=False,
            reported_macos_msc_host_blocked=True,
            reset_action="None",
            post_usb_connection_mode="MassStorage(MSC)",
            post_usb_lun_setting="Single",
        )
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_msc)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT)

    def test_022_pillar67b_setup_usb_4mode_and_reset_resistance(self) -> None:
        self.assertEqual(
            P366_FX3_ACTIVE_USB_CONNECTION_MODES,
            ("Sel. When Connect", "MassStorage(MSC)", "MTP", "Remote Shooting"),
        )
        # Camera Settings Reset does NOT wipe Remote Shooting or Single LUN or USB Power Supply=Off
        ok_rst = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            usb_connection_mode="Remote Shooting",
            usb_lun_setting="Single",
            usb_power_supply="Off",
            reset_action="Camera Settings Reset",
            post_usb_connection_mode="Remote Shooting",
            post_usb_lun_setting="Single",
            post_usb_power_supply="Off",
        )
        self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(ok_rst).passed)

        # Spoofing USB Connection Mode wiped by Camera Settings Reset fails
        bad_rst = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            usb_connection_mode="Remote Shooting",
            reset_action="Camera Settings Reset",
            post_usb_connection_mode="Sel. When Connect",
        )
        self.assertFalse(evaluate_arw_hlg_sort_usblun_uvc_vault(bad_rst).passed)

    def test_023_pillar67b_npfz100_mandatory_on_pd_and_dcc1_65w_5a_gate(self) -> None:
        # Standard 9V/3A 27W USB-C PD WITHOUT NP-FZ100 -> rejected!
        bad_no_bat = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            npfz100_present_with_charge=False,
            usb_pd_watts=27,
            dc_coupler_model="",
            cable_emarked_amps=3,
            reported_power_boot_allowed=True,
        )
        st1 = _compute_67b_from_spec(bad_no_bat)
        self.assertFalse(st1["power_boot_allowed"])
        self.assertTrue(st1["power_brownout_risk"])
        self.assertFalse(evaluate_arw_hlg_sort_usblun_uvc_vault(bad_no_bat).passed)

        # DC-C1 with <65W or <5A cable -> rejected!
        for w, a in ((45, 5), (65, 3)):
            bad_dcc1 = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                npfz100_present_with_charge=False,
                dc_coupler_model="DC-C1",
                usb_pd_watts=w,
                cable_emarked_amps=a,
                reported_power_boot_allowed=True,
            )
            self.assertFalse(_compute_67b_from_spec(bad_dcc1)["power_boot_allowed"])
            self.assertFalse(evaluate_arw_hlg_sort_usblun_uvc_vault(bad_dcc1).passed)

        # DC-C1 + >=65W PD + 5A e-Marked cable -> allowed!
        ok_dcc1 = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            npfz100_present_with_charge=False,
            dc_coupler_model="DC-C1",
            usb_pd_watts=65,
            cable_emarked_amps=5,
            reported_power_boot_allowed=True,
            reported_power_brownout_risk=False,
        )
        self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(ok_dcc1).passed)

    def test_024_pillar67b_dual_fx3_fx6_dormant_uvc_streaming_firewall(self) -> None:
        self.assertFalse(P366_FX3_HAS_NATIVE_UVC_STREAMING)
        self.assertFalse(P366_FX6_HAS_NATIVE_UVC_STREAMING)
        for model, fw, raw_t in (
            (P366_FX3_MODEL_NAME, P366_FX3_FW_VERSION, "Compressed"),
            (P366_FX6_DONOR_MODEL_NAME, P366_FX6_DONOR_FW_VERSION, "None"),
        ):
            bad_uvc = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
                camera_model=model,
                fw_version=fw,
                raw_file_type=raw_t,
                reset_action="None",
                post_raw_file_type=raw_t,
                uvc_streaming_requested=True,
                reported_dormant_uvc_errno=None,
                reported_usb_mode_errno=None,
            )
            st = _compute_67b_from_spec(bad_uvc)
            self.assertEqual(st["dormant_uvc_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertEqual(st["usb_mode_errno"], P366_EOPNOTSUPP_ERRNO)
            rep = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_uvc)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P366_BLOCKED_USBLUN_SINGLE_PD_OR_DORMANT_UVC_DRIFT)

    def test_025_pillar67b_fx6_zero_still_pipeline_and_dc_in_brownout_gate(self) -> None:
        self.assertFalse(P366_FX6_HAS_STILL_ARW_HLG_PIPELINE)
        bad_fx6_still = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            camera_model=P366_FX6_DONOR_MODEL_NAME,
            fw_version=P366_FX6_DONOR_FW_VERSION,
            raw_file_type="Compressed",
            hlg_still_image="On",
            reset_action="None",
            post_raw_file_type="Compressed",
        )
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_fx6_still)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT)

        bad_fx6_dc = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            camera_model=P366_FX6_DONOR_MODEL_NAME,
            fw_version=P366_FX6_DONOR_FW_VERSION,
            raw_file_type="None",
            reset_action="None",
            post_raw_file_type="None",
            npfz100_present_with_charge=False,
            fx6_dc_in_volts=15.5,
            reported_power_boot_allowed=True,
        )
        self.assertTrue(_compute_67b_from_spec(bad_fx6_dc)["power_brownout_risk"])
        self.assertFalse(evaluate_arw_hlg_sort_usblun_uvc_vault(bad_fx6_dc).passed)

    def test_026_pillar67b_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        bad_ovl = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(overlay_dir="/setting/67b")
        r1 = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_ovl)
        self.assertFalse(r1.passed)
        self.assertEqual(r1.block_code, P366_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(backup_bin_h3_sha256="a" * 64)
        r2 = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_h3)
        self.assertFalse(r2.passed)
        self.assertEqual(r2.block_code, P366_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    # ------------------------------------------------------------------
    # 5. Standalone Suites, Master 67/67 Aggregator, Fault Injection & CLI
    # ------------------------------------------------------------------

    def test_027_single_shot_combined_verifier_both_variants_pass(self) -> None:
        r1 = verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_and_vault(force_clean_room=True)
        r2 = verify_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P366_STATUS_VERIFIED_PILLAR67_SUITE)
        self.assertEqual(r2.status, P366_STATUS_VERIFIED_PILLAR67_SUITE)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_028_pillar67a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar67a_zoom_ciz_autoslow_baseiso_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P366_PILLAR_67A_SCENARIO_IDS,
        )

    def test_029_pillar67b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar67b_arw_hlg_sort_usblun_uvc_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(
            tuple(s.scenario_id for s in res.scenarios),
            P366_PILLAR_67B_SCENARIO_IDS,
        )

    def test_030_standalone_suite_all_4_modes_pass(self) -> None:
        r_normal = run_pillar67_standalone_suite()
        r_cr = run_pillar67_standalone_suite(force_clean_room=True)
        with patch.dict(os.environ, {P366_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            r_env1 = run_pillar67_standalone_suite()
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r_env2 = run_pillar67_standalone_suite()
        clean_env = os.environ.copy()
        clean_env.pop(P366_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                r_nomock = run_pillar67_standalone_suite()
        for r in (r_normal, r_cr, r_env1, r_env2, r_nomock):
            self.assertTrue(r.all_passed)
            self.assertEqual(r.status, P366_STATUS_VERIFIED_PILLAR67_SUITE)
            self.assertEqual(r.pillar_67a_zoom_ciz_autoslow_baseiso_vault.scenarios_passed, 6)
            self.assertEqual(r.pillar_67b_arw_hlg_sort_usblun_uvc_vault.scenarios_passed, 6)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)
            self.assertLess(r.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_031_master_67_recovery_clean_room_mode_passes_under_budget(self) -> None:
        m = verify_all_67_recovery_pillars(force_clean_room=True)
        self.assertTrue(m.all_passed)
        self.assertEqual(m.status, P366_STATUS_VERIFIED_67OF67_AGGREGATOR)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillar_count, 67)
        self.assertEqual(m.pillars_passed, 67)
        self.assertEqual(m.failed_pillars, ())
        self.assertTrue(m.under_6s_budget)
        self.assertLess(m.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_032_master_67_recovery_normal_mode_and_aliases_match(self) -> None:
        m1 = evaluate_realhw_67pillar_recovery_master()
        m2 = evaluate_67pillar_recovery_master()
        m3 = verify_67pillar_recovery_suite()
        m4 = verify_67pillar_recovery()
        for m in (m1, m2, m3, m4):
            self.assertTrue(m.all_passed)
            self.assertEqual(m.pillars_passed, 67)
            self.assertEqual(m.pillar_count, 67)
            self.assertEqual(m.master_67pillar_sha256, m1.master_67pillar_sha256)
            self.assertFalse(m.fx3_zoom_range_resettable)
            self.assertTrue(m.fx3_zoom_speed_resettable)
            self.assertFalse(m.fx3_has_dormant_lossless_arw_exposed)
            self.assertFalse(m.fx3_has_native_uvc_streaming)
            self.assertFalse(m.fx6_has_native_uvc_streaming)
            self.assertFalse(m.fx6_has_digital_zoom)
            self.assertFalse(m.fx6_has_still_arw_hlg_pipeline)
            self.assertFalse(m.fx6_has_iso_auto_min_ss)
            self.assertEqual(m.raw_firmware_bytes_leaked, 0)
            self.assertFalse(m.overall_ready_for_hardware_attach)
            self.assertTrue(m.under_6s_budget)

    def test_033_master_67_recovery_donorless_work_root_none_passes(self) -> None:
        clean_env = os.environ.copy()
        clean_env.pop(P366_ENV_CLEAN_ROOM_TEST, None)
        clean_env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
                m = verify_all_67_recovery_pillars()
        self.assertTrue(m.all_passed)
        self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m.pillars_passed, 67)
        self.assertEqual(m.pillar_count, 67)
        self.assertLess(m.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_034_master_67_recovery_env_clean_room_modes_pass(self) -> None:
        for env_key in (P366_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with patch.dict(os.environ, {env_key: "1"}, clear=False):
                m = verify_all_67_recovery_pillars()
                self.assertTrue(m.all_passed)
                self.assertEqual(m.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(m.pillars_passed, 67)
                self.assertLess(m.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_035_master_67_fault_injection_fail_closed(self) -> None:
        target = MASTER_67_PILLAR_IDS[-1]
        rep = evaluate_realhw_67pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=target,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P366_STATUS_FAIL_67OF67_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 66)
        self.assertEqual(rep.failed_pillars, (target,))

    def test_036_recursive_strip_elapsed_seconds_deterministic_digest(self) -> None:
        m1 = verify_all_67_recovery_pillars(force_clean_room=True)
        m2 = verify_all_67_recovery_pillars(force_clean_room=True)
        d1 = _strip_elapsed_seconds(m1.to_dict())
        d2 = _strip_elapsed_seconds(m2.to_dict())
        self.assertEqual(d1, d2)
        self.assertEqual(m1.master_67pillar_sha256, m2.master_67pillar_sha256)
        self.assertEqual(len(m1.master_67pillar_sha256), 64)

    def test_037_cli_help_percent_escape_and_subcommands(self) -> None:
        res_top = _run_cli("--help")
        self.assertEqual(res_top.returncode, 0, res_top.stderr)
        for cmd in (
            "verify-pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault",
            "verify-pillar67-recovery",
            "verify-67pillar-recovery",
        ):
            self.assertIn(cmd, res_top.stdout)
            res_sub = _run_cli(cmd, "--help")
            self.assertEqual(res_sub.returncode, 0, f"{cmd} --help failed: {res_sub.stderr}")

    def test_038_cli_json_and_out_execution_clean_room_and_normal(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests) as td:
            out_p67 = Path(td) / "out_p67"
            out_m67 = Path(td) / "out_m67"
            res_p67 = _run_cli(
                "verify-pillar67-recovery", "--force-clean-room", "--json", "--out", str(out_p67)
            )
            self.assertEqual(res_p67.returncode, 0, res_p67.stderr)
            p67_data = json.loads(res_p67.stdout)
            self.assertTrue(p67_data["all_passed"])
            self.assertEqual(p67_data["status"], P366_STATUS_VERIFIED_PILLAR67_SUITE)
            self.assertEqual(p67_data["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(
                (out_p67 / "pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault-report.json").exists()
            )

            res_m67 = _run_cli(
                "verify-67pillar-recovery", "--force-clean-room", "--json", "--out", str(out_m67)
            )
            self.assertEqual(res_m67.returncode, 0, res_m67.stderr)
            m67_data = json.loads(res_m67.stdout)
            self.assertTrue(m67_data["all_passed"])
            self.assertEqual(m67_data["pillar_count"], 67)
            self.assertEqual(m67_data["pillars_passed"], 67)
            self.assertEqual(m67_data["raw_firmware_bytes_leaked"], 0)
            self.assertTrue((out_m67 / "67pillar-recovery-master-report.json").exists())

            # Also verify normal mode text CLI
            res_norm = _run_cli("verify-67pillar-recovery")
            self.assertEqual(res_norm.returncode, 0, res_norm.stderr)
            self.assertIn("pillars=67/67", res_norm.stdout)

    def test_039_invalid_specs_fail_closed_with_explicit_block_codes(self) -> None:
        bad_a = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(zoom_lever_1st_stby=9)
        ra = evaluate_zoom_ciz_autoslow_baseiso_vault(bad_a)
        self.assertFalse(ra.passed)
        self.assertEqual(ra.block_code, P366_BLOCKED_INVALID_PILLAR67A_SPEC)

        bad_b = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(usb_lun_setting="Triple")
        rb = evaluate_arw_hlg_sort_usblun_uvc_vault(bad_b)
        self.assertFalse(rb.passed)
        self.assertEqual(rb.block_code, P366_BLOCKED_INVALID_PILLAR67B_SPEC)

    def test_040_master_67_zero_violation_counters_and_no_drift(self) -> None:
        m = verify_67pillar_recovery(force_clean_room=True)
        for zero_field in (
            "zoom_ciz_lockout_or_8speed_reset_drift_events",
            "autoslow_6lockout_or_minss_still_drift_events",
            "dual_base_iso_curve_matrix_drift_events",
            "dormant_lossless_arw_exposed_events",
            "hlg_still_or_sort_rec_spillover_drift_events",
            "usb_lun_single_slot1_msc_hazard_events",
            "npfz100_pd_interlock_or_dcc1_drift_events",
            "dormant_uvc_streaming_exposed_events",
            "slot1_data_sector_writes",
            "slot1_vault_mutation_bytes",
            "rf_packets_transmitted",
            "rf_nvs_mutation_bytes",
            "otp_fuse_touches",
            "otp_fuse_writes",
            "rpmb_counter_increments",
            "passive_tx_bytes_emitted",
            "physical_usb_packets_emitted",
            "physical_device_writes",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(getattr(m, zero_field), 0, f"Expected 0 for {zero_field}")
        self.assertTrue(m.slot1_format_hard_locked)
        self.assertTrue(m.slot1_vault_erofs_eopnotsupp_enforced)
        self.assertTrue(m.slot1_vault_erofs_ebusy_enforced)


# ---------------------------------------------------------------------------
# Parameterized Matrix Tests (bringing suite well past 130+ tests)
# ---------------------------------------------------------------------------


def _make_dual_base_iso_curve_test(
    curve_key: str,
    exp_low: int,
    exp_high: int,
    exp_menu: bool,
):
    def _test(self: unittest.TestCase) -> None:
        log_mode = curve_key if curve_key in ("Cine EI", "Cine EI Quick") else "Off"
        autoslow = "Off" if exp_menu else "On"
        spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            gamma_curve_key=curve_key,
            log_shooting_mode=log_mode,
            auto_slow_shutter=autoslow,
            reported_effective_auto_slow_shutter=autoslow,
            reported_base_iso_low=exp_low,
            reported_base_iso_high=exp_high,
            reported_base_iso_menu_exposed=exp_menu,
            reset_action="None",
            post_auto_slow_shutter=autoslow,
        )
        st = _compute_67a_from_spec(spec)
        self.assertEqual(st["base_iso_low"], exp_low)
        self.assertEqual(st["base_iso_high"], exp_high)
        self.assertEqual(st["base_iso_menu_exposed"], exp_menu)
        self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
    return _test


def _make_zoom_scale_lockout_test(
    camera_model: str,
    domain: str,
    apsc_s35: bool,
    size_or_res: str,
    zoom_range: str,
    still_fmt: str,
    fps: int,
    raw_out: str,
    breath: str,
    fx6_sq: str,
    fx6_codec: str,
    expect_errno: bool,
    expect_scale: float,
):
    def _test(self: unittest.TestCase) -> None:
        is_still = domain == "Still"
        eff_zoom = "Optical zoom only" if expect_errno else zoom_range
        non_opt = eff_zoom != "Optical zoom only" and camera_model == P366_FX3_MODEL_NAME
        spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            camera_model=camera_model,
            fw_version=P366_FX6_DONOR_FW_VERSION if camera_model == P366_FX6_DONOR_MODEL_NAME else P366_FX3_FW_VERSION,
            shooting_domain=domain,
            apsc_s35_on=apsc_s35,
            still_image_size=size_or_res if is_still else "L",
            movie_resolution=size_or_res if not is_still else "4K",
            still_file_format=still_fmt,
            recording_fps=fps,
            raw_output=raw_out,
            breathing_comp=breath,
            fx6_sq_motion=fx6_sq,
            fx6_codec=fx6_codec,
            zoom_range=zoom_range,
            auto_slow_shutter="Off",
            reported_effective_auto_slow_shutter="Off",
            reported_zoom_errno=None,
            reported_effective_zoom_range=eff_zoom,
            reported_max_zoom_scale=expect_scale,
            reported_focus_area_locked_center=non_opt,
            reported_metering_locked_multi=non_opt,
            reported_face_eye_tracking_disabled=non_opt,
            reset_action="None",
            post_zoom_range=eff_zoom,
            post_auto_slow_shutter="Off",
        )
        st = _compute_67a_from_spec(spec)
        if expect_errno:
            self.assertEqual(st["zoom_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertEqual(st["effective_zoom_range"], "Optical zoom only")
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
        else:
            self.assertIsNone(st["zoom_errno"])
            self.assertAlmostEqual(st["max_zoom_scale"], expect_scale, places=2)
            self.assertEqual(st["focus_area_locked_center"], non_opt)
            self.assertEqual(st["metering_locked_multi"], non_opt)
            self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
    return _test


def _make_autoslow_gate_test(
    domain: str,
    exp_mode: str,
    iso_set: str,
    flex_man: bool,
    log_mode: str,
    shut_mode: str,
    expect_locked: bool,
):
    def _test(self: unittest.TestCase) -> None:
        is_cei = log_mode in ("Cine EI", "Cine EI Quick")
        spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            shooting_domain=domain,
            exposure_mode=exp_mode,
            iso_setting=iso_set,
            flexible_exp_manual_shutter=flex_man,
            log_shooting_mode=log_mode,
            shutter_mode=shut_mode,
            auto_slow_shutter="On",
            zoom_range="Optical zoom only",
            reported_effective_zoom_range="Optical zoom only",
            reported_max_zoom_scale=1.0,
            reported_focus_area_locked_center=False,
            reported_metering_locked_multi=False,
            reported_face_eye_tracking_disabled=False,
            gamma_curve_key="Cine EI" if is_cei else "PP11 S-Cinetone",
            reported_base_iso_low=800 if is_cei else 100,
            reported_base_iso_high=12800 if is_cei else 2000,
            reported_base_iso_menu_exposed=is_cei,
            reported_auto_slow_errno=None,
            reported_effective_auto_slow_shutter="On",
            reset_action="None",
            post_zoom_range="Optical zoom only",
            post_auto_slow_shutter="On",
        )
        st = _compute_67a_from_spec(spec)
        if expect_locked:
            self.assertEqual(st["auto_slow_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertEqual(st["effective_auto_slow_shutter"], "Off")
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
        else:
            self.assertIsNone(st["auto_slow_errno"])
            self.assertEqual(st["effective_auto_slow_shutter"], "On")
            self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
    return _test


def _make_min_ss_preset_test(
    preset: str,
    domain: str,
    exp_mode: str,
    expect_allowed: bool,
):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            shooting_domain=domain,
            exposure_mode=exp_mode,
            iso_setting="ISO AUTO",
            auto_slow_shutter="Off",
            reported_effective_auto_slow_shutter="Off",
            iso_auto_min_ss=preset,
            reported_iso_auto_min_ss_errno=None,
            zoom_range="Optical zoom only",
            reported_effective_zoom_range="Optical zoom only",
            reported_max_zoom_scale=1.0,
            reported_focus_area_locked_center=False,
            reported_metering_locked_multi=False,
            reported_face_eye_tracking_disabled=False,
            reset_action="None",
            post_zoom_range="Optical zoom only",
            post_auto_slow_shutter="Off",
            post_iso_auto_min_ss=preset,
        )
        st = _compute_67a_from_spec(spec)
        if expect_allowed:
            self.assertIsNone(st["iso_auto_min_ss_errno"])
            self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
        else:
            self.assertEqual(st["iso_auto_min_ss_errno"], P366_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_zoom_ciz_autoslow_baseiso_vault(spec).passed)
    return _test


def _make_dormant_lossless_arw_test(raw_type: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            raw_file_type=raw_type,
            reported_raw_file_type_errno=None,
            reset_action="None",
            post_raw_file_type=raw_type,
        )
        st = _compute_67b_from_spec(spec)
        self.assertEqual(st["raw_file_type_errno"], P366_EOPNOTSUPP_ERRNO)
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P366_BLOCKED_DORMANT_ARW_HLG_OR_SORT_SPILLOVER_DRIFT)
    return _test


def _make_usb_lun_mode_test(
    usb_mode: str,
    lun: str,
    host_mac: bool,
    exp_s1: bool,
    exp_s2: bool,
    exp_mac_block: bool,
):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            usb_connection_mode=usb_mode,
            usb_lun_setting=lun,
            host_os_is_macos=host_mac,
            reported_slot1_exposed_to_host=exp_s1,
            reported_slot2_exposed_to_host=exp_s2,
            reported_macos_msc_host_blocked=exp_mac_block,
            reset_action="None",
            post_usb_connection_mode=usb_mode,
            post_usb_lun_setting=lun,
        )
        st = _compute_67b_from_spec(spec)
        self.assertEqual(st["slot1_exposed_to_host"], exp_s1)
        self.assertEqual(st["slot2_exposed_to_host"], exp_s2)
        self.assertEqual(st["macos_msc_host_blocked"], exp_mac_block)
        rep = evaluate_arw_hlg_sort_usblun_uvc_vault(spec)
        self.assertEqual(rep.passed, not exp_mac_block)
    return _test


def _make_power_gate_test(
    camera_model: str,
    npf: bool,
    coupler: str,
    watts: int,
    amps: int,
    fx6_v: float,
    exp_boot: bool,
    exp_risk: bool,
):
    def _test(self: unittest.TestCase) -> None:
        raw_t = "None" if camera_model == P366_FX6_DONOR_MODEL_NAME else "Compressed"
        spec = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            camera_model=camera_model,
            fw_version=P366_FX6_DONOR_FW_VERSION if camera_model == P366_FX6_DONOR_MODEL_NAME else P366_FX3_FW_VERSION,
            raw_file_type=raw_t,
            npfz100_present_with_charge=npf,
            dc_coupler_model=coupler,
            usb_pd_watts=watts,
            cable_emarked_amps=amps,
            fx6_dc_in_volts=fx6_v,
            reported_power_boot_allowed=exp_boot,
            reported_power_brownout_risk=exp_risk,
            reset_action="None",
            post_raw_file_type=raw_t,
        )
        st = _compute_67b_from_spec(spec)
        self.assertEqual(st["power_boot_allowed"], exp_boot)
        self.assertEqual(st["power_brownout_risk"], exp_risk)
        self.assertEqual(evaluate_arw_hlg_sort_usblun_uvc_vault(spec).passed, exp_boot)
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        sa = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_zoom_ciz_autoslow_baseiso_vault(sa).passed, expect_pass)

        sb = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_arw_hlg_sort_usblun_uvc_vault(sb).passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        keep = reset_action == "None"
        sa = build_default_safe_zoom_ciz_autoslow_baseiso_vault_spec(
            zoom_range="Digital Zoom",
            zoom_ring_rotate="Right(W)/Left(T)",
            zoom_lever_1st_stby=5,
            zoom_lever_1st_rec=2,
            zoom_lever_2nd_stby=7,
            zoom_lever_2nd_rec=6,
            custom_key_zoom_speed_stby=4,
            custom_key_zoom_speed_rec=1,
            remote_zoom_speed_type="Fixed",
            remote_zoom_fixed_stby=6,
            remote_zoom_fixed_rec=2,
            reported_effective_zoom_range="Digital Zoom",
            reported_max_zoom_scale=4.0,
            auto_slow_shutter="Off",
            reported_effective_auto_slow_shutter="Off",
            shooting_domain="Still",
            exposure_mode="A",
            iso_auto_min_ss="1/125",
            reset_action=reset_action,
            post_zoom_range=P366_FX3_ZOOM_RANGE_DEFAULT if init else "Digital Zoom",
            post_zoom_ring_rotate=P366_FX3_ZOOM_RING_ROTATE_DEFAULT if init else "Right(W)/Left(T)",
            post_zoom_lever_1st_stby=5 if keep else P366_FX3_ZOOM_LEVER_1ST_DEFAULT,
            post_zoom_lever_1st_rec=2 if keep else P366_FX3_ZOOM_LEVER_1ST_DEFAULT,
            post_zoom_lever_2nd_stby=7 if keep else P366_FX3_ZOOM_LEVER_2ND_DEFAULT,
            post_zoom_lever_2nd_rec=6 if keep else P366_FX3_ZOOM_LEVER_2ND_DEFAULT,
            post_custom_key_zoom_speed_stby=4 if keep else fr.P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
            post_custom_key_zoom_speed_rec=1 if keep else fr.P366_FX3_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
            post_remote_zoom_speed_type="Fixed" if keep else fr.P366_FX3_REMOTE_ZOOM_SPEED_TYPE_DEFAULT,
            post_remote_zoom_fixed_stby=6 if keep else fr.P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
            post_remote_zoom_fixed_rec=2 if keep else fr.P366_FX3_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
            post_auto_slow_shutter="Off" if keep else P366_FX3_AUTO_SLOW_SHUTTER_DEFAULT,
            post_iso_auto_min_ss="1/125" if keep else P366_FX3_ISO_AUTO_MIN_SS_DEFAULT,
            post_iso_range_limit_persisted=not init,
        )
        self.assertTrue(evaluate_zoom_ciz_autoslow_baseiso_vault(sa).passed)

        sb = build_default_safe_arw_hlg_sort_usblun_uvc_vault_spec(
            still_file_format="HEIF",
            raw_file_type="Uncompressed",
            jpeg_heif_switch="HEIF(4:2:2)",
            hlg_still_image="On",
            reported_effective_hlg_still="On",
            reported_hlg_bt2100_active=True,
            reported_hlg_pp_dro_disabled=True,
            rec_media_mode="Sort Recording",
            usb_connection_mode="Remote Shooting",
            usb_lun_setting="Single",
            usb_power_supply="Off",
            reset_action=reset_action,
            post_raw_file_type="Uncompressed" if keep else fr.P366_FX3_RAW_FILE_TYPE_DEFAULT,
            post_jpeg_heif_switch="HEIF(4:2:2)" if keep else "JPEG",
            post_hlg_still_image="On" if keep else "Off",
            post_usb_connection_mode=fr.P366_FX3_USB_CONNECTION_DEFAULT if init else "Remote Shooting",
            post_usb_lun_setting=fr.P366_FX3_USB_LUN_DEFAULT if init else "Single",
            post_usb_power_supply="On" if init else "Off",
            post_rec_media_mode="Slot 1" if init else "Sort Recording",
        )
        self.assertTrue(evaluate_arw_hlg_sort_usblun_uvc_vault(sb).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase366_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_67_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_67_PILLAR_IDS[idx])
    return _test


def _make_fault_inject_pillar_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        pid = MASTER_67_PILLAR_IDS[idx]
        m = evaluate_realhw_67pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid,
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, 66)
        self.assertEqual(m.failed_pillars, (pid,))
    return _test


def _install_parameterized_tests() -> None:
    idx = 41

    # 1. All 19 Dual Base ISO Curves (19 tests)
    for curve_key, (exp_low, exp_high, exp_menu) in P366_FX3_DUAL_BASE_ISO_CURVES.items():
        clean = (
            curve_key.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("%", "pct")
            .replace("-", "_")
        )
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_dual_base_iso_curve_{clean}",
            _make_dual_base_iso_curve_test(curve_key, exp_low, exp_high, exp_menu),
        )
        idx += 1

    # 2. Zoom Scale & Lockout Matrix (14 tests)
    zoom_cases = (
        ("fx3_movie_4k_ciz_1_5x", P366_FX3_MODEL_NAME, "Movie", False, "4K", "ClearImage Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 1.5),
        ("fx3_movie_hd_ciz_2_0x", P366_FX3_MODEL_NAME, "Movie", False, "HD", "ClearImage Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 2.0),
        ("fx3_movie_4k_digital_4_0x", P366_FX3_MODEL_NAME, "Movie", False, "4K", "Digital Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 4.0),
        ("fx3_still_ff_l_ciz_2_0x", P366_FX3_MODEL_NAME, "Still", False, "L", "ClearImage Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 2.0),
        ("fx3_still_ff_m_smart_1_5x", P366_FX3_MODEL_NAME, "Still", False, "M", "Smart Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 1.5),
        ("fx3_still_ff_m_ciz_3_1x", P366_FX3_MODEL_NAME, "Still", False, "M", "ClearImage Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 3.1),
        ("fx3_still_ff_s_digital_8_0x", P366_FX3_MODEL_NAME, "Still", False, "S", "Digital Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 8.0),
        ("fx3_still_apsc_m_ciz_2_6x", P366_FX3_MODEL_NAME, "Still", True, "M", "ClearImage Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 2.6),
        ("fx3_still_apsc_s_smart_2_0x", P366_FX3_MODEL_NAME, "Still", True, "S", "Smart Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", False, 2.0),
        ("fx3_raw_heif_ciz_lock", P366_FX3_MODEL_NAME, "Still", False, "L", "ClearImage Zoom", "RAW & HEIF", 24, "Off", "Off", "Off", "XAVC-I", True, 1.0),
        ("fx3_movie_120p_ciz_lock", P366_FX3_MODEL_NAME, "Movie", False, "4K", "ClearImage Zoom", "JPEG", 120, "Off", "Off", "Off", "XAVC-I", True, 1.0),
        ("fx3_hdmi_raw_ciz_lock", P366_FX3_MODEL_NAME, "Movie", False, "4K", "ClearImage Zoom", "JPEG", 24, "On", "Off", "Off", "XAVC-I", True, 1.0),
        ("fx6_digital_zoom_lock", P366_FX6_DONOR_MODEL_NAME, "Movie", False, "4K", "Digital Zoom", "JPEG", 24, "Off", "Off", "Off", "XAVC-I", True, 1.0),
        ("fx6_sq_gt60_ciz_lock", P366_FX6_DONOR_MODEL_NAME, "Movie", False, "4K", "ClearImage Zoom", "JPEG", 120, "Off", "Off", "On", "XAVC-I", True, 1.0),
    )
    for label, mod, dom, apsc, sz, zrng, fmt, fps, ro, br, fsq, fcod, ee, es in zoom_cases:
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_zoom_{label}",
            _make_zoom_scale_lockout_test(mod, dom, apsc, sz, zrng, fmt, fps, ro, br, fsq, fcod, ee, es),
        )
        idx += 1

    # 3. Auto Slow Shutter Valid & Lockout Modes (10 tests)
    autoslow_cases = (
        ("movie_p_auto_ok", "Movie", "P", "ISO AUTO", False, "Off", "Speed", False),
        ("movie_a_auto_ok", "Movie", "A", "ISO AUTO", False, "Off", "Speed", False),
        ("movie_flex_auto_ok", "Movie", "Flexible Exp.", "ISO AUTO", False, "Flexible ISO", "Speed", False),
        ("sq_lock", "S&Q", "P", "ISO AUTO", False, "Off", "Speed", True),
        ("still_lock", "Still", "P", "ISO AUTO", False, "Off", "Speed", True),
        ("shutter_s_lock", "Movie", "S", "ISO AUTO", False, "Off", "Speed", True),
        ("manual_m_lock", "Movie", "M", "ISO AUTO", False, "Off", "Speed", True),
        ("fixed_iso_lock", "Movie", "P", "800", False, "Off", "Speed", True),
        ("flex_manual_shutter_lock", "Movie", "Flexible Exp.", "ISO AUTO", True, "Off", "Speed", True),
        ("cine_ei_quick_and_angle_lock", "Movie", "M", "800", False, "Cine EI Quick", "Angle", True),
    )
    for label, dom, expm, isos, fman, lmode, smode, elock in autoslow_cases:
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_autoslow_{label}",
            _make_autoslow_gate_test(dom, expm, isos, fman, lmode, smode, elock),
        )
        idx += 1

    # 4. Still-Only ISO AUTO Min. SS Presets & Lockouts (6 tests)
    min_ss_cases = (
        ("still_p_slower", "SLOWER", "Still", "P", True),
        ("still_a_faster", "FASTER", "Still", "A", True),
        ("still_p_1_8000", "1/8000", "Still", "P", True),
        ("still_a_30s", '30"', "Still", "A", True),
        ("movie_p_1_125_lock", "1/125", "Movie", "P", False),
        ("sq_a_fast_lock", "FAST", "S&Q", "A", False),
    )
    for label, preset, dom, expm, eok in min_ss_cases:
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_min_ss_{label}",
            _make_min_ss_preset_test(preset, dom, expm, eok),
        )
        idx += 1

    # 5. Dormant Lossless Comp ARW Variants Rejected (8 tests)
    for d_raw in P366_FX3_DORMANT_RAW_FILE_TYPES:
        clean = (
            d_raw.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
        )
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_dormant_arw_{clean}",
            _make_dormant_lossless_arw_test(d_raw),
        )
        idx += 1

    # 6. USB Connection Mode x USB LUN Setting Matrix (6 tests)
    usb_cases = (
        ("msc_single_macos_blocked", "MassStorage(MSC)", "Single", True, True, False, True),
        ("msc_multi_macos_blocked", "MassStorage(MSC)", "Multi", True, True, True, True),
        ("mtp_multi_macos_blocked", "MTP", "Multi", True, True, False, True),
        ("remote_single_ok", "Remote Shooting", "Single", True, False, False, False),
        ("sel_single_ok", "Sel. When Connect", "Single", True, False, False, False),
        ("msc_single_nonmac_audit_ok", "MassStorage(MSC)", "Single", False, True, False, False),
    )
    for label, umode, lun, mac, s1, s2, mblk in usb_cases:
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_usb_{label}",
            _make_usb_lun_mode_test(umode, lun, mac, s1, s2, mblk),
        )
        idx += 1

    # 7. NP-FZ100 USB-C PD / DC-C1 / FX6 19.5V DC IN Power Gates (5 tests)
    pwr_cases = (
        ("fx3_npfz100_pd27w_ok", P366_FX3_MODEL_NAME, True, "", 27, 3, 19.5, True, False),
        ("fx3_batteryless_pd27w_fail", P366_FX3_MODEL_NAME, False, "", 27, 3, 19.5, False, True),
        ("fx3_dcc1_65w_5a_ok", P366_FX3_MODEL_NAME, False, "DC-C1", 65, 5, 19.5, True, False),
        ("fx3_dcc1_45w_3a_fail", P366_FX3_MODEL_NAME, False, "DC-C1", 45, 3, 19.5, False, True),
        ("fx6_19_5v_dc_in_batteryless_ok", P366_FX6_DONOR_MODEL_NAME, False, "", 0, 0, 19.5, True, False),
    )
    for label, mod, npf, cpl, w, a, fv, eb, er in pwr_cases:
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_power_{label}",
            _make_power_gate_test(mod, npf, cpl, w, a, fv, eb, er),
        )
        idx += 1

    # 8. Slot-1 Write Firewall actions x errno pairs (6 actions x 3 errnos = 18 tests)
    for action in sorted(P366_WRITE_MUTATING_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP", "EBUSY"):
            setattr(
                Phase366Pillar67VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 9. Reset Action Matrices (3 tests)
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 10. Individual Donor Checks (25 Wave-65 donors)
    for d_i in range(25):
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # 11. Selected key pillars + final 67th pillar across MASTER_67_PILLAR_IDS (17 tests)
    for p_i in (*range(0, 67, 5), 64, 65, 66):
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1

    # 12. Fault injection across 5 key pillars incl. 65, 66 & 67 (5 tests)
    for p_i in (0, 21, 64, 65, 66):
        setattr(
            Phase366Pillar67VerifierTests,
            f"test_{idx:03d}_fault_inject_pillar_{p_i+1:02d}",
            _make_fault_inject_pillar_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
