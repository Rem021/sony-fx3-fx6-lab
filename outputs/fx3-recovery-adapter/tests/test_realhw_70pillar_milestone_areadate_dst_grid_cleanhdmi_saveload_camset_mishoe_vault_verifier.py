"""Phase 380 Milestone (Pillar 70 & 70/70 Milestone) unit tests:
Wave-68 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` empirical telemetry across Pillars 70A & 70B:
- Pillar 70A (`Setup -> [Area/Date] -> [Area/Date/Time Setting]` 4 items, 30 `AREA_GMT_*` zones incl.
  6 half-hour zones, `Daylight Savings` + Sony ELF typo `convert_setting_daylight_saving_to_saylight_saving`,
  `Date/Time` + ELF typo `BKID_APP_setting_auto_sync_sever_date_time`, `Date Format` `Y-M-D/M-D-Y/D-M-Y`,
  anti-Reset / `Initialize` wizard trigger, internal rechargeable RTC backup `>= 24h` OFF, no CR2032 / no
  3-month claim vs FX6 `Maintenance > Clock Set` `UTC -12..+14` 30-min, zero UI DST, `Backup Battery End`;
  `[Grid Line Display]` / `[Grid Line Type]` all-mode, deleted `_movie` keys, HDMI passthrough unless Clean-Feed
  vs `[Marker Display] -> [Guideframe]` Movie/S&Q-only, all-5 anti-Reset, Focus Magnifier hidden, 0px Clean-HDMI
  vs FX6 `Monitoring > Marker` & zero 3-mode composition grid UI).
- Pillar 70B (`[Save/Load Settings]` Slot-1 hard lock, max 10 `CAMSET01..10.DAT` / 60 Cloud, exact path
  `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`, SD `/PRIVATE` vs CFexpress `""`, zero `PRO/CAMERA` hits,
  `libSaveLoadSettings.so` `18,760 B` SHA-256 `07819f42...`, same-model / `1.01 -> 2.00+` / `MR` mode / reboot,
  complete official excluded items list, `FTPSET%02d.DAT`, `Camera Set. Memory` `1..3` vs `M1..M4` `CAMPR`,
  Tier-0 `Slot 1` `EROFS=30` firewall & RO host-buffer Load vs FX6 `All File` / `User File` / `Scene File` /
  `User 3D LUT` / dormant `Reference File`; Sync Terminal debunk `0` hits / dormant `_f 0x6b31` & `_g 0x645e`,
  MI-Shoe Still mechanical `1/250s` `< 250V` Flash, `[Video Light Mode]` 4 modes `HVL-LBPC` vs `XLR-H1`
  electrical preemption & Stage-B `PMIC 5V <= 900 mA`, vs FX6 3-mode Video Light zero Auto, zero Still Flash,
  `TC IN/OUT` BNC `EXT-LK`, and zero physical `GENLOCK` BNC despite `107` dormant symbols).
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
    MASTER_70_PILLAR_COUNT,
    MASTER_70_PILLAR_IDS,
    MASTER_70_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P380_AIRPLANE_MODE_FORCED_ON,
    P380_BKID_DELETED_GRID_LINE_MOVIE_SYMBOLS,
    P380_BLOCKED_AREADATE_DST_OR_RTC_BACKUP_DRIFT,
    P380_BLOCKED_GRID_VS_MARKER_CLEANHDMI_DRIFT,
    P380_BLOCKED_INVALID_PILLAR70A_SPEC,
    P380_BLOCKED_INVALID_PILLAR70B_SPEC,
    P380_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT,
    P380_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P380_BLOCKED_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT,
    P380_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P380_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P380_CONCURRENT_CEILING_SECONDS,
    P380_CROSS_MODEL_FLASH_AUTHORIZED,
    P380_DONOR_FX3_APPFW_702_RELPATH,
    P380_DONOR_FX3_BACKUP_BIN_RELPATH,
    P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
    P380_DONOR_FX3_UXC_EN_RELPATH,
    P380_DONOR_FX6_APPFW_601_RELPATH,
    P380_DONOR_FX6_UXC_EN_2_RELPATH,
    P380_DONOR_FX6_UXC_EN_RELPATH,
    P380_DONOR_INSPECT_BUDGET_SECONDS,
    P380_EBUSY_ERRNO,
    P380_EINVAL_ERRNO,
    P380_ELF_AUTO_SYNC_SERVER_SONY_TYPO,
    P380_ELF_DAYLIGHT_SAVING_SONY_TYPO,
    P380_ELF_INITIAL_SETTING_CONTROLLER,
    P380_EMMC_WRITES_AUTHORIZED,
    P380_ENOENT_ERRNO,
    P380_ENV_CLEAN_ROOM_TEST,
    P380_EOPNOTSUPP_ERRNO,
    P380_EROFS_ERRNO,
    P380_FAST_CLI_BUDGET_SECONDS,
    P380_FX3_AREA_DATE_TIME_4_ITEMS,
    P380_FX3_AREA_DATE_TIME_RESETTABLE,
    P380_FX3_AREA_GMT_30_ZONES,
    P380_FX3_AREA_GMT_HALF_HOUR_ZONES,
    P380_FX3_AREA_GMT_ZONE_COUNT,
    P380_FX3_CAMERA_SET_MEMORY_BODY_RESETTABLE,
    P380_FX3_CAMERA_SET_MEMORY_BODY_SLOTS,
    P380_FX3_CAMERA_SET_MEMORY_CARD_SLOTS,
    P380_FX3_CAMPR_PATH_TEMPLATE,
    P380_FX3_CAMSET_CORE_EXCLUDED_COUNT,
    P380_FX3_CAMSET_LOCKED_SLOT,
    P380_FX3_CAMSET_MAX_CARD_SLOTS,
    P380_FX3_CAMSET_MAX_CLOUD_SLOTS,
    P380_FX3_CAMSET_NETWORK_11_EXCLUDED_ITEMS,
    P380_FX3_CAMSET_OFFICIAL_EXCLUDED_ITEMS,
    P380_FX3_CAMSET_PATH_TEMPLATE,
    P380_FX3_CFEXPRESS_MEDIA_PREFIX,
    P380_FX3_DATE_FORMATS,
    P380_FX3_DAYLIGHT_SAVINGS_DEFAULT,
    P380_FX3_EXTERNAL_FLASH_SET_IN_CAMSET,
    P380_FX3_EXTERNAL_FLASH_SET_RESETTABLE,
    P380_FX3_FLASH_MAX_SYNC_RECIPROCAL,
    P380_FX3_FLASH_MODES,
    P380_FX3_FLASH_TRIGGER_VOLTAGE_LIMIT_V,
    P380_FX3_FTPSET_PATH_TEMPLATE,
    P380_FX3_FW_VERSION,
    P380_FX3_GRID_LINE_ALLOWED_DOMAINS,
    P380_FX3_GRID_LINE_DISPLAY_DEFAULT,
    P380_FX3_GRID_LINE_RESETTABLE,
    P380_FX3_GRID_LINE_TYPES,
    P380_FX3_GRID_LINE_TYPE_DEFAULT,
    P380_FX3_HAS_PHYSICAL_SYNC_TERMINAL,
    P380_FX3_HAS_TC_BNC,
    P380_FX3_HAS_USER_CR2032_SLOT,
    P380_FX3_HELPGUIDE_CLAIMS_3_MONTHS_RETENTION,
    P380_FX3_HELPGUIDE_ID,
    P380_FX3_LIBSAVELOADSETTINGS_EXPORTS,
    P380_FX3_MARKER_DISPLAY_4_SUBITEMS,
    P380_FX3_MARKER_DISPLAY_ALL_5_RESETTABLE,
    P380_FX3_MARKER_DISPLAY_DEFAULT,
    P380_FX3_MARKER_DISPLAY_HDMI_PIXELS_EMITTED,
    P380_FX3_MODEL_ID,
    P380_FX3_MODEL_NAME,
    P380_FX3_PRO_CAMERA_PATH_HITS,
    P380_FX3_RTC_BACKUP_CHARGE_MIN_HOURS_OFF,
    P380_FX3_SD_MEDIA_PREFIX,
    P380_FX3_SYNCHRO_TERMINAL_APPFW_HITS,
    P380_FX3_SYNC_TERMINAL_HELPGUIDE_PAGES,
    P380_FX3_VIDEO_LIGHT_MODEL,
    P380_FX3_VIDEO_LIGHT_MODES,
    P380_FX3_VIDEO_LIGHT_MODE_DEFAULT,
    P380_FX6_ALL_FILE_MAX_SLOTS,
    P380_FX6_ALL_FILE_PATH_TEMPLATE,
    P380_FX6_CENTER_MARKER_MODES,
    P380_FX6_DATE_MODES,
    P380_FX6_DONOR_FW_VERSION,
    P380_FX6_DONOR_MODEL_NAME,
    P380_FX6_DORMANT_GENLOCK_SYMBOL_COUNT,
    P380_FX6_ELF_DORMANT_SUMMER_TIME_SYMBOL,
    P380_FX6_HAS_3MODE_COMPOSITION_GRID_UI,
    P380_FX6_HAS_PHYSICAL_GENLOCK_BNC,
    P380_FX6_HAS_STILL_FLASH_UI,
    P380_FX6_HAS_TC_IN_OUT_BNC,
    P380_FX6_HAS_UI_DST_SWITCH,
    P380_FX6_HAS_USER_EXPOSED_REFERENCE_FILE,
    P380_FX6_HAS_VIDEO_LIGHT_AUTO,
    P380_FX6_MARKER_OSD_GATES,
    P380_FX6_MARKER_SUBITEMS,
    P380_FX6_REFERENCE_FILE_APPFW_HITS,
    P380_FX6_SAFETY_AREA_PERCENTAGES,
    P380_FX6_TIME_FORMAT_MODES,
    P380_FX6_USER_3D_LUT_MAX_SLOTS,
    P380_FX6_VIDEO_LIGHT_MODES,
    P380_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P380_MISHOE_PMIC_5V_MAX_MA,
    P380_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P380_PILLAR_70A_SCENARIO_IDS,
    P380_PILLAR_70B_SCENARIO_IDS,
    P380_PINNED_FX3_BACKUP_BIN_SHA256,
    P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
    P380_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P380_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P380_STATUS_FAIL_70OF70_AGGREGATOR,
    P380_STATUS_VERIFIED_70OF70_AGGREGATOR,
    P380_STATUS_VERIFIED_PILLAR70_SUITE,
    P380_STATUS_VERIFIED_PILLAR_70A,
    P380_STATUS_VERIFIED_PILLAR_70B,
    P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS,
    P380_XLR_H1_ACCESSORY_SHOE_IS_PASSIVE_COLD_SHOE,
    P380_XLR_H1_PREEMPTS_ELECTRICAL_MI_SHOE,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE380_MASTER_SCHEMA,
    PHASE380_PHASE_NUMBER,
    PHASE380_SCHEMA,
    PHASE380_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec,
    build_default_safe_saveload_camset_mishoe_sync_vault_spec,
    compute_expected_areadate_dst_grid_cleanhdmi_state,
    compute_expected_saveload_camset_mishoe_sync_state,
    evaluate_70pillar_recovery_master,
    evaluate_areadate_dst_grid_cleanhdmi_vault,
    evaluate_realhw_70pillar_recovery_master,
    evaluate_saveload_camset_mishoe_sync_vault,
    inspect_phase380_donors_readonly,
    run_pillar70_standalone_suite,
    run_pillar70a_areadate_dst_grid_cleanhdmi_vault_6_scenario_suite,
    run_pillar70b_saveload_camset_mishoe_sync_vault_6_scenario_suite,
    verify_70pillar_recovery,
    verify_70pillar_recovery_master,
    verify_70pillar_recovery_suite,
    verify_all_70_recovery_pillars,
    verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_vault,
    verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault,
)


def _wave68_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P380_DONOR_FX3_APPFW_702_RELPATH,
        P380_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
        P380_DONOR_FX3_BACKUP_BIN_RELPATH,
        P380_DONOR_FX3_UXC_EN_RELPATH,
        P380_DONOR_FX6_APPFW_601_RELPATH,
        P380_DONOR_FX6_UXC_EN_RELPATH,
        P380_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for rel in required:
        rel_n = rel[5:] if rel.startswith("work/") else rel
        if not any(
            r is not None and ((r / rel_n).exists() or (r.parent / rel).exists())
            for r in roots
        ):
            return False
    return True


def _strip_volatile_timing(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` and `elapsed_ms` keys."""
    if isinstance(obj, dict):
        return {
            k: _strip_volatile_timing(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [_strip_volatile_timing(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_strip_volatile_timing(v) for v in obj)
    return obj


def _compute_70a_from_spec(spec: fr.AreaDateDstGridCleanHdmiVaultSpec) -> dict[str, Any]:
    return compute_expected_areadate_dst_grid_cleanhdmi_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        area_gmt_zone=spec.area_gmt_zone,
        daylight_savings=spec.daylight_savings,
        date_format=spec.date_format,
        rtc_backup_depleted=spec.rtc_backup_depleted,
        rtc_charge_hours_off_with_full_npfz100=spec.rtc_charge_hours_off_with_full_npfz100,
        claim_user_cr2032_slot=spec.claim_user_cr2032_slot,
        claim_3month_retention_in_ilc2210=spec.claim_3month_retention_in_ilc2210,
        fx6_utc_offset_minutes=spec.fx6_utc_offset_minutes,
        fx6_date_mode=spec.fx6_date_mode,
        fx6_time_format=spec.fx6_time_format,
        fx6_ui_dst_switch_requested=spec.fx6_ui_dst_switch_requested,
        fx6_backup_battery_end_alert=spec.fx6_backup_battery_end_alert,
        grid_line_display=spec.grid_line_display,
        grid_line_type=spec.grid_line_type,
        hdmi_info_display=spec.hdmi_info_display,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        raw_output_enabled=spec.raw_output_enabled,
        marker_display=spec.marker_display,
        marker_guideframe=spec.marker_guideframe,
        focus_magnifier_active=spec.focus_magnifier_active,
        fx6_marker_setting=spec.fx6_marker_setting,
        fx6_center_marker=spec.fx6_center_marker,
        fx6_safety_area=spec.fx6_safety_area,
        fx6_guide_frame=spec.fx6_guide_frame,
        fx6_vf_marker_osd=spec.fx6_vf_marker_osd,
        fx6_sdi_marker_osd=spec.fx6_sdi_marker_osd,
        fx6_hdmi_marker_osd=spec.fx6_hdmi_marker_osd,
        fx6_3mode_composition_grid_requested=spec.fx6_3mode_composition_grid_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_70b_from_spec(spec: fr.SaveLoadCamsetMiShoeSyncVaultSpec) -> dict[str, Any]:
    return compute_expected_saveload_camset_mishoe_sync_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        shutter_type=spec.shutter_type,
        silent_mode=spec.silent_mode,
        saveload_operation=spec.saveload_operation,
        saveload_target_slot=spec.saveload_target_slot,
        camset_slot_index=spec.camset_slot_index,
        cloud_slot_count=spec.cloud_slot_count,
        media_card_type=spec.media_card_type,
        camset_path_uses_pro_camera=spec.camset_path_uses_pro_camera,
        camset_source_model=spec.camset_source_model,
        camset_source_fw_version=spec.camset_source_fw_version,
        in_mr_recall_mode=spec.in_mr_recall_mode,
        camset_excluded_item_requested=spec.camset_excluded_item_requested,
        load_into_simulated_host_buffer_only=spec.load_into_simulated_host_buffer_only,
        cam_memory_slot=spec.cam_memory_slot,
        memory_recall_media_slot=spec.memory_recall_media_slot,
        cam_memory_includes_custom_key_or_pshift=spec.cam_memory_includes_custom_key_or_pshift,
        fx6_all_file_slot_count=spec.fx6_all_file_slot_count,
        fx6_all_file_load_network_data=spec.fx6_all_file_load_network_data,
        fx6_user_3d_lut_count=spec.fx6_user_3d_lut_count,
        fx6_reference_file_requested=spec.fx6_reference_file_requested,
        sync_terminal_requested=spec.sync_terminal_requested,
        flash_sync_spd_prty_requested=spec.flash_sync_spd_prty_requested,
        flash_mode=spec.flash_mode,
        flash_shutter_reciprocal=spec.flash_shutter_reciprocal,
        flash_trigger_voltage_v=spec.flash_trigger_voltage_v,
        flash_reverse_polarity=spec.flash_reverse_polarity,
        video_light_mode=spec.video_light_mode,
        xlr_h1_attached=spec.xlr_h1_attached,
        mishoe_electrical_device_attached=spec.mishoe_electrical_device_attached,
        mishoe_current_ma=spec.mishoe_current_ma,
        fx6_video_light_mode=spec.fx6_video_light_mode,
        fx6_still_flash_requested=spec.fx6_still_flash_requested,
        fx6_tc_bnc_mode=spec.fx6_tc_bnc_mode,
        fx6_genlock_bnc_requested=spec.fx6_genlock_bnc_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


class Phase380MilestonePillar70VerifierTests(unittest.TestCase):
    """Core & parameterized four-mode unit tests for Phase 380 Milestone (Pillar 70A + 70B + 70/70 Master)."""

    def test_001_safety_redlines_and_pinned_metadata(self) -> None:
        self.assertEqual(
            PHASE380_SCHEMA,
            "realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier_v1",
        )
        self.assertEqual(PHASE380_MASTER_SCHEMA, "realhw_70pillar_recovery_master_v1")
        self.assertEqual(PHASE380_VERSION, "1.0.0")
        self.assertEqual(PHASE380_PHASE_NUMBER, 380)
        self.assertEqual(MASTER_70_PILLAR_COUNT, 70)
        self.assertEqual(len(MASTER_70_PILLAR_SPECS), 70)
        self.assertEqual(len(MASTER_70_PILLAR_IDS), 70)
        self.assertEqual(P380_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P380_CONCURRENT_CEILING_SECONDS, 6.00)
        self.assertEqual(P380_DONOR_INSPECT_BUDGET_SECONDS, 2.0)

        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P380_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P380_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertTrue(P380_AIRPLANE_MODE_FORCED_ON)

        for flag in (
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
            P380_EMMC_WRITES_AUTHORIZED,
            P380_CROSS_MODEL_FLASH_AUTHORIZED,
            P380_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            P380_OVERALL_READY_FOR_HARDWARE_ATTACH,
            P380_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
        ):
            self.assertFalse(flag)

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

    def test_002_non_shadowing_package_exports_and_aliases(self) -> None:
        self.assertTrue(hasattr(fr, "verify_68pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_69pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_70pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_70pillar_recovery_master"))
        self.assertTrue(callable(verify_70pillar_recovery))
        self.assertTrue(callable(verify_70pillar_recovery_master))
        self.assertTrue(callable(verify_all_70_recovery_pillars))
        self.assertTrue(callable(evaluate_70pillar_recovery_master))
        self.assertIs(
            fr.realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier,
            sys.modules[
                "fx3_recovery.realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier"
            ],
        )

    def test_003_wave68_empirical_constants_typos_and_debunks(self) -> None:
        self.assertEqual(P380_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P380_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P380_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P380_FX3_FW_VERSION, "7.02")
        self.assertEqual(P380_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P380_FX6_DONOR_FW_VERSION, "6.01")

        # Exact Sony ELF typos
        self.assertEqual(
            P380_ELF_DAYLIGHT_SAVING_SONY_TYPO,
            "convert_setting_daylight_saving_to_saylight_saving",
        )
        self.assertEqual(
            P380_ELF_AUTO_SYNC_SERVER_SONY_TYPO,
            "BKID_APP_setting_auto_sync_sever_date_time",
        )
        self.assertEqual(
            P380_ELF_INITIAL_SETTING_CONTROLLER,
            "37dlg_rec203_initial_setting_controller",
        )
        self.assertEqual(len(P380_BKID_DELETED_GRID_LINE_MOVIE_SYMBOLS), 2)

        # Area/Date & RTC
        self.assertEqual(len(P380_FX3_AREA_DATE_TIME_4_ITEMS), 4)
        self.assertEqual(len(P380_FX3_AREA_GMT_30_ZONES), 30)
        self.assertEqual(P380_FX3_AREA_GMT_ZONE_COUNT, 30)
        self.assertEqual(len(P380_FX3_AREA_GMT_HALF_HOUR_ZONES), 6)
        for hz in P380_FX3_AREA_GMT_HALF_HOUR_ZONES:
            self.assertIn(hz, P380_FX3_AREA_GMT_30_ZONES)
        self.assertFalse(P380_FX3_AREA_DATE_TIME_RESETTABLE)
        self.assertFalse(P380_FX3_HAS_USER_CR2032_SLOT)
        self.assertEqual(P380_FX3_RTC_BACKUP_CHARGE_MIN_HOURS_OFF, 24)
        self.assertFalse(P380_FX3_HELPGUIDE_CLAIMS_3_MONTHS_RETENTION)
        self.assertFalse(P380_FX6_HAS_UI_DST_SWITCH)
        self.assertEqual(P380_FX6_ELF_DORMANT_SUMMER_TIME_SYMBOL, "summer_time_name_dst")

        # Grid Line vs Marker Display
        self.assertFalse(P380_FX3_GRID_LINE_RESETTABLE)
        self.assertFalse(P380_FX3_MARKER_DISPLAY_ALL_5_RESETTABLE)
        self.assertEqual(P380_FX3_MARKER_DISPLAY_HDMI_PIXELS_EMITTED, 0)
        self.assertEqual(len(P380_FX3_MARKER_DISPLAY_4_SUBITEMS), 4)
        self.assertFalse(P380_FX6_HAS_3MODE_COMPOSITION_GRID_UI)
        self.assertEqual(len(P380_FX6_MARKER_SUBITEMS), 6)
        self.assertEqual(len(P380_FX6_MARKER_OSD_GATES), 3)

        # Save/Load Settings & libSaveLoadSettings.so
        self.assertEqual(P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, 18760)
        self.assertEqual(
            P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        )
        self.assertEqual(len(P380_FX3_LIBSAVELOADSETTINGS_EXPORTS), 11)
        self.assertEqual(P380_FX3_CAMSET_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT")
        self.assertEqual(P380_FX3_CAMPR_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT")
        self.assertEqual(P380_FX3_FTPSET_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT")
        self.assertEqual(P380_FX3_PRO_CAMERA_PATH_HITS, 0)
        self.assertEqual(P380_FX3_CAMSET_LOCKED_SLOT, 1)
        self.assertEqual(P380_FX3_CAMSET_MAX_CARD_SLOTS, 10)
        self.assertEqual(P380_FX3_CAMSET_MAX_CLOUD_SLOTS, 60)
        self.assertEqual(P380_FX3_CAMSET_CORE_EXCLUDED_COUNT, 16)
        self.assertEqual(len(P380_FX3_CAMSET_NETWORK_11_EXCLUDED_ITEMS), 11)
        self.assertGreaterEqual(len(P380_FX3_CAMSET_OFFICIAL_EXCLUDED_ITEMS), 16)
        self.assertFalse(P380_FX3_CAMERA_SET_MEMORY_BODY_RESETTABLE)
        self.assertEqual(P380_FX6_ALL_FILE_MAX_SLOTS, 64)
        self.assertEqual(P380_FX6_USER_3D_LUT_MAX_SLOTS, 16)
        self.assertEqual(P380_FX6_REFERENCE_FILE_APPFW_HITS, 0)
        self.assertFalse(P380_FX6_HAS_USER_EXPOSED_REFERENCE_FILE)

        # Sync Terminal Debunk, MI-Shoe Video Light vs XLR-H1, FX6 TC/Genlock
        self.assertFalse(P380_FX3_HAS_PHYSICAL_SYNC_TERMINAL)
        self.assertEqual(P380_FX3_SYNCHRO_TERMINAL_APPFW_HITS, 0)
        self.assertEqual(P380_FX3_SYNC_TERMINAL_HELPGUIDE_PAGES, 0)
        self.assertEqual(P380_FX3_FLASH_MAX_SYNC_RECIPROCAL, 250)
        self.assertEqual(P380_FX3_FLASH_TRIGGER_VOLTAGE_LIMIT_V, 250)
        self.assertFalse(P380_FX3_EXTERNAL_FLASH_SET_RESETTABLE)
        self.assertFalse(P380_FX3_EXTERNAL_FLASH_SET_IN_CAMSET)
        self.assertEqual(P380_FX3_VIDEO_LIGHT_MODEL, "HVL-LBPC")
        self.assertEqual(len(P380_FX3_VIDEO_LIGHT_MODES), 4)
        self.assertTrue(P380_XLR_H1_ACCESSORY_SHOE_IS_PASSIVE_COLD_SHOE)
        self.assertTrue(P380_XLR_H1_PREEMPTS_ELECTRICAL_MI_SHOE)
        self.assertEqual(P380_MISHOE_PMIC_5V_MAX_MA, 900)
        self.assertEqual(len(P380_FX6_VIDEO_LIGHT_MODES), 3)
        self.assertFalse(P380_FX6_HAS_VIDEO_LIGHT_AUTO)
        self.assertFalse(P380_FX6_HAS_STILL_FLASH_UI)
        self.assertFalse(P380_FX3_HAS_TC_BNC)
        self.assertTrue(P380_FX6_HAS_TC_IN_OUT_BNC)
        self.assertFalse(P380_FX6_HAS_PHYSICAL_GENLOCK_BNC)
        self.assertEqual(P380_FX6_DORMANT_GENLOCK_SYMBOL_COUNT, 107)

    def test_004_donor_inspect_clean_room_and_local_o_rdonly_18_donors(self) -> None:
        snap_clean = inspect_phase380_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_clean.donor_files_inspected, 18)
        self.assertTrue(snap_clean.all_donors_present)
        self.assertEqual(snap_clean.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap_clean.under_2_0s_budget)

        snap_auto = inspect_phase380_donors_readonly()
        self.assertEqual(snap_auto.donor_files_inspected, 18)
        self.assertTrue(snap_auto.all_donors_present)
        self.assertEqual(snap_auto.raw_firmware_bytes_leaked, 0)
        if _wave68_donors_present() and not (
            os.environ.get(P380_ENV_CLEAN_ROOM_TEST) == "1"
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        ):
            self.assertEqual(snap_auto.verification_mode, "LOCAL_DONOR_O_RDONLY")
            sl_art = [a for a in snap_auto.artifacts if a.artifact_id == "fx3_libsaveloadsettings_so"][0]
            self.assertEqual(sl_art.total_bytes, 18760)
            self.assertEqual(sl_art.digest_sha256, P380_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256)
            self.assertTrue(sl_art.matches_pinned)

    def test_005_donor_inspect_all_four_modes_including_work_root_none(self) -> None:
        with patch.dict(os.environ, {P380_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase380_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 18)
            self.assertTrue(snap.all_donors_present)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap2 = inspect_phase380_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap2.donor_files_inspected, 18)

        with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
            snap_none = inspect_phase380_donors_readonly(force_clean_room=False)
            self.assertEqual(snap_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_none.donor_files_inspected, 18)
            self.assertTrue(snap_none.all_donors_present)

            m_none = verify_70pillar_recovery_suite()
            self.assertTrue(m_none.all_passed)
            self.assertEqual(m_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(m_none.pillars_passed, m_none.pillar_count)
            self.assertGreaterEqual(m_none.pillar_count, 70)

    def test_006_donor_inspect_bad_marker_rejection_helpers(self) -> None:
        mod = fr.realhw_70pillar_milestone_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault_verifier
        ok_elf, msg_elf = mod._check_elf64_aarch64(b"NOT_ELF", "X")
        self.assertFalse(ok_elf)
        self.assertIn("NOT_ELF", msg_elf)

        ok_uxc, msg_uxc = mod._check_uxc7_pack(b"BAD_UXC0000000000", "X")
        self.assertFalse(ok_uxc)
        self.assertIn("BAD_UXC7_MAGIC", msg_uxc)

        ok_bk4, msg_bk4 = mod._check_bk4_backup(b"BAD_BK4" + b"\x00" * 32, "X")
        self.assertFalse(ok_bk4)
        self.assertIn("BAD_BK4_MAGIC", msg_bk4)

    def test_007_default_safe_specs_evaluate_and_verify_combined_deterministic(self) -> None:
        rep_a = evaluate_areadate_dst_grid_cleanhdmi_vault(
            build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec()
        )
        self.assertTrue(rep_a.passed)
        self.assertEqual(rep_a.status, P380_STATUS_VERIFIED_PILLAR_70A)
        self.assertIsNone(rep_a.block_code)

        rep_b = evaluate_saveload_camset_mishoe_sync_vault(
            build_default_safe_saveload_camset_mishoe_sync_vault_spec()
        )
        self.assertTrue(rep_b.passed)
        self.assertEqual(rep_b.status, P380_STATUS_VERIFIED_PILLAR_70B)
        self.assertIsNone(rep_b.block_code)

        comb1 = verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_and_vault(force_clean_room=True)
        comb2 = verify_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_vault(force_clean_room=True)
        self.assertTrue(comb1.all_passed)
        self.assertTrue(comb2.all_passed)
        self.assertEqual(comb1.status, P380_STATUS_VERIFIED_PILLAR70_SUITE)
        self.assertEqual(comb1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(comb1.slot1_writes, 0)
        self.assertEqual(_strip_volatile_timing(comb1.to_dict()), _strip_volatile_timing(comb2.to_dict()))

    def test_008_pillar70a_areadate_dst_rtc_cr2032_and_3month_debunk(self) -> None:
        # Depleted RTC with <24h OFF triggers Initial Setting wizard
        s_dep = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            rtc_backup_depleted=True,
            rtc_charge_hours_off_with_full_npfz100=12,
            reported_initial_setting_wizard_triggered=True,
            reported_rtc_backup_charged_sufficiently=False,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(s_dep).passed)

        # Claim user CR2032 slot -> EOPNOTSUPP(95)
        s_cr = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            claim_user_cr2032_slot=True,
        )
        self.assertEqual(_compute_70a_from_spec(s_cr)["areadate_errno"], P380_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(s_cr).passed)

        # Claim 3 months in ilc/2210 -> EOPNOTSUPP(95)
        s_3m = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            claim_3month_retention_in_ilc2210=True,
        )
        self.assertEqual(_compute_70a_from_spec(s_3m)["areadate_errno"], P380_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(s_3m).passed)

    def test_009_pillar70a_fx6_clock_set_zero_dst_and_backup_battery_end(self) -> None:
        # FX6 dormant UI DST switch -> EOPNOTSUPP(95)
        s_dst = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            fx6_ui_dst_switch_requested=True,
        )
        self.assertEqual(_compute_70a_from_spec(s_dst)["areadate_errno"], P380_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(s_dst).passed)

        # FX6 Backup Battery End alert forces Clock Set lock
        s_end = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            fx6_backup_battery_end_alert=True,
            reported_initial_setting_wizard_triggered=True,
            reported_rtc_backup_charged_sufficiently=False,
            reported_grid_line_hdmi_passthrough=False,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(s_end).passed)

    def test_010_pillar70a_grid_line_hdmi_passthrough_vs_cleanfeed(self) -> None:
        # HDMI Info=On + Rec. Media=On + RAW=Off -> Grid Line passes through to HDMI
        s_pass = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            grid_line_display="On",
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            raw_output_enabled="Off",
            reported_grid_line_hdmi_passthrough=True,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(s_pass).passed)

        # Forced Clean-Feed via Off(HDMI Only) or RAW Output=On strips Grid Line from HDMI
        for kw in (
            {"rec_media_dur_hdmi_output": "Off(HDMI Only)"},
            {"raw_output_enabled": "On"},
            {"hdmi_info_display": "Off"},
        ):
            s_cf = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
                grid_line_display="On",
                reported_grid_line_hdmi_passthrough=False,
                **kw,
            )
            self.assertFalse(_compute_70a_from_spec(s_cf)["grid_line_hdmi_passthrough"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(s_cf).passed)

    def test_011_pillar70a_marker_display_movie_only_focus_mag_and_0px_cleanhdmi(self) -> None:
        # Still mode blocks Marker Display / Guideframe -> EOPNOTSUPP(95)
        s_still = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            shooting_domain="Still",
            marker_display="On",
            marker_guideframe="On",
        )
        self.assertEqual(_compute_70a_from_spec(s_still)["grid_marker_errno"], P380_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(s_still).passed)

        # Focus Magnifier hides Marker Display on LCD while keeping 0 HDMI pixels
        s_fm = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            shooting_domain="Movie",
            marker_display="On",
            marker_guideframe="On",
            focus_magnifier_active=True,
            reported_marker_visible_on_lcd=False,
            reported_marker_hdmi_pixels_emitted=0,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(s_fm).passed)

        # Any leaked Marker HDMI pixel rejected
        s_leak = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            reported_marker_hdmi_pixels_emitted=12,
        )
        rep_leak = evaluate_areadate_dst_grid_cleanhdmi_vault(s_leak)
        self.assertFalse(rep_leak.passed)
        self.assertEqual(rep_leak.block_code, P380_BLOCKED_GRID_VS_MARKER_CLEANHDMI_DRIFT)

    def test_012_pillar70b_saveload_slot1_lock_model_fw_mr_and_pro_camera_debunk(self) -> None:
        # Slot 2 rejected on Save/Load Settings -> EOPNOTSUPP(95)
        s_s2 = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            saveload_target_slot=2,
        )
        self.assertEqual(_compute_70b_from_spec(s_s2)["saveload_errno"], P380_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(s_s2).passed)

        # Cross-model rejected -> EOPNOTSUPP(95)
        s_cm = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_source_model="ILCE-7SM3",
        )
        self.assertEqual(_compute_70b_from_spec(s_cm)["saveload_errno"], P380_EOPNOTSUPP_ERRNO)

        # Ver. 1.01 -> 2.00+ rejected -> EINVAL(22)
        s_v1 = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_source_fw_version="1.01",
            fw_version="7.02",
        )
        self.assertEqual(_compute_70b_from_spec(s_v1)["saveload_errno"], P380_EINVAL_ERRNO)

        # MR mode blocks Save/Load Settings -> EBUSY(16)
        s_mr = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            in_mr_recall_mode=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_mr)["saveload_errno"], P380_EBUSY_ERRNO)

        # PRO/CAMERA path spoof on FX3 -> EOPNOTSUPP(95)
        s_pc = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_path_uses_pro_camera=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_pc)["saveload_errno"], P380_EOPNOTSUPP_ERRNO)

    def test_013_pillar70b_campr_memory_slot2_and_fx6_allfile_reference_file(self) -> None:
        # Save CAMPR M2 to Slot 2 allowed without reboot and without touching Slot 1
        s_m2 = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            saveload_operation="SAVE_CAMPR",
            cam_memory_slot="M2",
            memory_recall_media_slot=2,
            reported_saveload_reboot_required=False,
            requested_vault_slot=2,
            requested_vault_action="SAVE_CAMPR_DAT_SLOT2",
        )
        self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(s_m2).passed)

        # Custom Key/Dial Set. or Program Shift in Camera Set. Memory rejected -> EOPNOTSUPP(95)
        s_ck = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            cam_memory_includes_custom_key_or_pshift=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_ck)["saveload_errno"], P380_EOPNOTSUPP_ERRNO)

        # FX6 dormant Reference File rejected -> EOPNOTSUPP(95)
        s_ref = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            saveload_operation="FX6_LOAD_ALL_FILE",
            fx6_reference_file_requested=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_ref)["saveload_errno"], P380_EOPNOTSUPP_ERRNO)

    def test_014_pillar70b_sync_terminal_debunk_and_still_mechanical_flash(self) -> None:
        # Sync Terminal & dormant Flash Sync Spd. Prty. -> EOPNOTSUPP(95)
        for kw in ({"sync_terminal_requested": True}, {"flash_sync_spd_prty_requested": True}):
            s = build_default_safe_saveload_camset_mishoe_sync_vault_spec(**kw)
            self.assertEqual(_compute_70b_from_spec(s)["mishoe_sync_errno"], P380_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(s).passed)

        # Valid Still Mechanical Shutter Flash (1/250s, 12V positive, no XLR-H1) -> PASS
        s_fl = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            shooting_domain="Still",
            shutter_type="Mechanical Shutter",
            silent_mode="Off",
            flash_mode="Fill-flash",
            flash_shutter_reciprocal=250,
            flash_trigger_voltage_v=12,
            flash_reverse_polarity=False,
            xlr_h1_attached=False,
            mishoe_electrical_device_attached=True,
        )
        self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(s_fl).passed)

        # Electronic shutter or Silent mode blocks flash -> EOPNOTSUPP(95)
        for kw in ({"shutter_type": "Electronic Shutter"}, {"silent_mode": "On"}, {"shooting_domain": "Movie"}):
            base_kw = {
                "shooting_domain": "Still",
                "shutter_type": "Mechanical Shutter",
                "silent_mode": "Off",
                "flash_mode": "Fill-flash",
            }
            base_kw.update(kw)
            s_bad = build_default_safe_saveload_camset_mishoe_sync_vault_spec(**base_kw)
            self.assertEqual(_compute_70b_from_spec(s_bad)["mishoe_sync_errno"], P380_EOPNOTSUPP_ERRNO)

        # Reverse polarity -> EINVAL(22)
        s_rev = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            shooting_domain="Still",
            flash_mode="Fill-flash",
            flash_reverse_polarity=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_rev)["mishoe_sync_errno"], P380_EINVAL_ERRNO)

    def test_015_pillar70b_xlrh1_mishoe_preemption_pmic_and_fx6_tc_genlock(self) -> None:
        # XLR-H1 + electrical MI-Shoe HVL-LBPC simultaneously -> EBUSY(16)
        s_xlr = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            xlr_h1_attached=True,
            mishoe_electrical_device_attached=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_xlr)["mishoe_sync_errno"], P380_EBUSY_ERRNO)
        rep_xlr = evaluate_saveload_camset_mishoe_sync_vault(s_xlr)
        self.assertFalse(rep_xlr.passed)
        self.assertEqual(rep_xlr.block_code, P380_BLOCKED_SYNC_TERMINAL_MISHOE_OR_GENLOCK_DRIFT)

        # FX6 Genlock BNC request -> EOPNOTSUPP(95)
        s_gl = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            saveload_operation="FX6_LOAD_ALL_FILE",
            fx6_genlock_bnc_requested=True,
        )
        self.assertEqual(_compute_70b_from_spec(s_gl)["mishoe_sync_errno"], P380_EOPNOTSUPP_ERRNO)

        # FX6 TC BNC IN activates EXT-LK, OUT does not
        for tc_m, exp_ext in (("IN", True), ("OUT", False), ("OFF", False)):
            s_tc = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                saveload_operation="FX6_LOAD_ALL_FILE",
                fx6_tc_bnc_mode=tc_m,
                reported_fx6_tc_ext_lk_active=exp_ext,
                requested_vault_slot=2,
                requested_vault_action="FX6_ALL_FILE_MEDIA_B",
            )
            self.assertEqual(_compute_70b_from_spec(s_tc)["fx6_tc_ext_lk_active"], exp_ext)
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(s_tc).passed)

    def test_016_pillar70_slot1_vault_erofs30_emmc_load_overlay_and_h0_h3(self) -> None:
        # Load CAMSET without host-buffer-only flag -> EROFS(30) (never writes physical eMMC!)
        s_emmc = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            load_into_simulated_host_buffer_only=False,
        )
        self.assertEqual(_compute_70b_from_spec(s_emmc)["saveload_errno"], P380_EROFS_ERRNO)
        self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(s_emmc).passed)

        # Overlay escape -> BLOCKED_P380_PERSISTENT_OVERLAY_ESCAPE
        s_esc = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            overlay_dir="/dev/cnflasha/70b",
        )
        rep_esc = evaluate_saveload_camset_mishoe_sync_vault(s_esc)
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P380_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        # Backup.bin H0 != H3 -> BLOCKED_P380_TIER0_BACKUP_BIN_H0_H3_DRIFT
        s_h3 = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            backup_bin_h3_sha256="f" * 64,
        )
        rep_h3 = evaluate_areadate_dst_grid_cleanhdmi_vault(s_h3)
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P380_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_017_standalone_70a_70b_12_scenario_suites(self) -> None:
        res_a = run_pillar70a_areadate_dst_grid_cleanhdmi_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)
        self.assertEqual(res_a.status, P380_STATUS_VERIFIED_PILLAR_70A)

        res_b = run_pillar70b_saveload_camset_mishoe_sync_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)
        self.assertEqual(res_b.status, P380_STATUS_VERIFIED_PILLAR_70B)

        st1 = run_pillar70_standalone_suite(force_clean_room=True)
        st2 = run_pillar70_standalone_suite(force_clean_room=True)
        self.assertTrue(st1.all_passed)
        self.assertEqual(st1.suite_sha256, st2.suite_sha256)
        self.assertEqual(st1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st1.slot1_writes, 0)

    def test_018_master_70pillar_clean_room_and_determinism(self) -> None:
        m1 = evaluate_realhw_70pillar_recovery_master(force_clean_room=True)
        m2 = verify_70pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(m1.all_passed)
        self.assertTrue(m2.all_passed)
        self.assertEqual(m1.status, P380_STATUS_VERIFIED_70OF70_AGGREGATOR)
        self.assertGreaterEqual(m1.pillar_count, 70)
        self.assertEqual(m1.pillars_passed, m1.pillar_count)
        self.assertEqual(m1.failed_pillars, ())
        self.assertEqual(m1.master_70pillar_sha256, m2.master_70pillar_sha256)
        self.assertEqual(m1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m1.slot1_writes, 0)
        self.assertTrue(m1.under_1_5s_fast_cli_budget or m1.under_6s_budget)
        self.assertEqual(_strip_volatile_timing(m1.to_dict()), _strip_volatile_timing(m2.to_dict()))

    def test_019_master_70pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_70pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_020_cli_help_and_verify_pillar70_recovery_json_out(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs' / 'fx3-safety'}"
        for cmd in (
            "verify-pillar70-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-vault",
            "verify-pillar70-recovery",
            "verify-70pillar-recovery",
        ):
            help_proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", cmd, "--help"],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(help_proc.returncode, 0, f"{cmd} --help: {help_proc.stderr}")
            self.assertIn(cmd, help_proc.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests, prefix="p380_cli_p70_") as td:
            out_dir = Path(td) / "p70_out"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-pillar70-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout or proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["status"], P380_STATUS_VERIFIED_PILLAR70_SUITE)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(payload["slot1_writes"], 0)
            self.assertTrue(
                (out_dir / "pillar70-areadate-dst-grid-cleanhdmi-saveload-camset-mishoe-vault-report.json").is_file()
            )

    def test_021_cli_verify_70pillar_recovery_json_and_out(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs' / 'fx3-safety'}"
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests, prefix="p380_cli_m70_") as td:
            out_dir = Path(td) / "m70_out"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-70pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout or proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["status"], P380_STATUS_VERIFIED_70OF70_AGGREGATOR)
            self.assertGreaterEqual(payload["pillar_count"], 70)
            self.assertEqual(payload["pillars_passed"], payload["pillar_count"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(payload["slot1_writes"], 0)
            self.assertTrue((out_dir / "70pillar-recovery-master-report.json").is_file())

    def test_022_cli_verify_70pillar_recovery_human_readable_summary(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-70pillar-recovery",
                "--force-clean-room",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("pillars=70/70", proc.stdout)
        self.assertIn("raw_firmware_bytes_leaked=0", proc.stdout)
        self.assertIn("slot1_writes=0", proc.stdout)

    def test_023_cli_verify_70pillar_and_pillar70_auto_mode(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        for cmd in ("verify-pillar70-recovery", "verify-70pillar-recovery"):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", cmd, "--json"],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"{cmd}: {proc.stderr}")
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(payload["slot1_writes"], 0)


# ---------------------------------------------------------------------------
# Parameterized Test Factories (>= 180 Total Tests)
# ---------------------------------------------------------------------------


def _make_area_gmt_zone_test(zone: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(area_gmt_zone=zone)
        st = _compute_70a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["areadate_errno"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
        else:
            self.assertEqual(st["areadate_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_date_format_test(fmt: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(date_format=fmt)
        st = _compute_70a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["areadate_errno"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
        else:
            self.assertEqual(st["areadate_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_rtc_charge_hours_test(hours: int):
    def _test(self: unittest.TestCase) -> None:
        charged = hours >= P380_FX3_RTC_BACKUP_CHARGE_MIN_HOURS_OFF
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            rtc_backup_depleted=True,
            rtc_charge_hours_off_with_full_npfz100=hours,
            reported_rtc_backup_charged_sufficiently=charged,
            reported_initial_setting_wizard_triggered=(not charged),
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_fx6_utc_offset_test(offset_min: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            fx6_utc_offset_minutes=offset_min,
            reported_grid_line_hdmi_passthrough=False,
        )
        st = _compute_70a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["areadate_errno"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
        else:
            self.assertEqual(st["areadate_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_fx6_date_time_fmt_test(date_mode: str, time_fmt: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            fx6_date_mode=date_mode,
            fx6_time_format=time_fmt,
            reported_grid_line_hdmi_passthrough=False,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_grid_type_test(gtype: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            grid_line_type=gtype,
            post_grid_line_type=gtype,
        )
        st = _compute_70a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["grid_marker_errno"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
        else:
            self.assertEqual(st["grid_marker_errno"], P380_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_grid_domain_test(domain: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            shooting_domain=domain,
            grid_line_display="On",
            marker_display="Off",
            marker_guideframe="Off",
            reported_marker_visible_on_lcd=False,
            post_marker_display="Off",
            post_marker_guideframe="Off",
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_grid_hdmi_truth_test(grid_d: str, hdmi_i: str, rec_m: str, raw_o: str):
    def _test(self: unittest.TestCase) -> None:
        forced_cf = hdmi_i == "Off" or rec_m == "Off(HDMI Only)" or raw_o == "On"
        expect_pt = (grid_d == "On") and (not forced_cf)
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            grid_line_display=grid_d,
            hdmi_info_display=hdmi_i,
            rec_media_dur_hdmi_output=rec_m,
            raw_output_enabled=raw_o,
            reported_grid_line_hdmi_passthrough=expect_pt,
            post_grid_line_display=grid_d,
        )
        st = _compute_70a_from_spec(spec)
        self.assertEqual(st["grid_line_hdmi_passthrough"], expect_pt)
        self.assertEqual(st["marker_hdmi_pixels_emitted"], 0)
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_marker_domain_focus_mag_test(domain: str, fmag: bool):
    def _test(self: unittest.TestCase) -> None:
        expect_ok = domain in ("Movie", "S&Q")
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            shooting_domain=domain,
            marker_display="On",
            marker_guideframe="On",
            focus_magnifier_active=fmag,
            reported_marker_visible_on_lcd=(expect_ok and not fmag),
            reported_marker_hdmi_pixels_emitted=0,
        )
        st = _compute_70a_from_spec(spec)
        self.assertEqual(st["marker_hdmi_pixels_emitted"], 0)
        if expect_ok:
            self.assertIsNone(st["grid_marker_errno"])
            self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
        else:
            self.assertEqual(st["grid_marker_errno"], P380_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_fx6_marker_option_test(center_m: str, safety_a: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            camera_model=P380_FX6_DONOR_MODEL_NAME,
            fw_version=P380_FX6_DONOR_FW_VERSION,
            fx6_center_marker=center_m,
            fx6_safety_area=safety_a,
            reported_grid_line_hdmi_passthrough=False,
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(spec).passed)
    return _test


def _make_camset_slot_index_test(slot_idx: int):
    def _test(self: unittest.TestCase) -> None:
        expect_ok = 1 <= slot_idx <= P380_FX3_CAMSET_MAX_CARD_SLOTS
        spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_slot_index=slot_idx,
        )
        st = _compute_70b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["saveload_errno"])
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            self.assertEqual(st["saveload_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_camset_excluded_item_test(item_name: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_excluded_item_requested=item_name,
        )
        st = _compute_70b_from_spec(spec)
        self.assertEqual(st["saveload_errno"], P380_EOPNOTSUPP_ERRNO)
        rep = evaluate_saveload_camset_mishoe_sync_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P380_BLOCKED_SAVELOAD_CAMSET_OR_CAMPR_DRIFT)
    return _test


def _make_camset_version_compat_test(src_ver: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            camset_source_fw_version=src_ver,
            fw_version="7.02",
        )
        st = _compute_70b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["saveload_errno"])
            self.assertTrue(st["saveload_reboot_required"])
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            self.assertEqual(st["saveload_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_campr_memory_slot_test(mslot: str, media_slot: int):
    def _test(self: unittest.TestCase) -> None:
        if media_slot == 1:
            # Recall from Slot 1 RO allowed; Save to Slot 1 blocked EROFS!
            spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                saveload_operation="RECALL_CAMPR",
                cam_memory_slot=mslot,
                memory_recall_media_slot=1,
                reported_saveload_reboot_required=False,
                requested_vault_slot=1,
                requested_vault_action="RECALL_CAMPR_SLOT1_RO",
            )
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                saveload_operation="SAVE_CAMPR",
                cam_memory_slot=mslot,
                memory_recall_media_slot=2,
                reported_saveload_reboot_required=False,
                requested_vault_slot=2,
                requested_vault_action="SAVE_CAMPR_DAT_SLOT2",
            )
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_video_light_mode_test(model: str, mode: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        if model == P380_FX6_DONOR_MODEL_NAME:
            spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                camera_model=P380_FX6_DONOR_MODEL_NAME,
                fw_version=P380_FX6_DONOR_FW_VERSION,
                saveload_operation="FX6_LOAD_ALL_FILE",
                fx6_video_light_mode=mode,
                fx6_tc_bnc_mode="OUT",
                reported_fx6_tc_ext_lk_active=False,
                requested_vault_slot=2,
                requested_vault_action="FX6_ALL_FILE_MEDIA_B",
            )
        else:
            spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
                video_light_mode=mode,
            )
        st = _compute_70b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["mishoe_sync_errno"])
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            self.assertIsNotNone(st["mishoe_sync_errno"])
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_pmic_current_test(ma: int):
    def _test(self: unittest.TestCase) -> None:
        expect_ok = 0 <= ma <= P380_MISHOE_PMIC_5V_MAX_MA
        spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            mishoe_current_ma=ma,
        )
        st = _compute_70b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["mishoe_sync_errno"])
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            self.assertEqual(st["mishoe_sync_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_flash_sync_voltage_test(shutter_rec: int, voltage_v: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            shooting_domain="Still",
            shutter_type="Mechanical Shutter",
            silent_mode="Off",
            flash_mode="Fill-flash",
            flash_shutter_reciprocal=shutter_rec,
            flash_trigger_voltage_v=voltage_v,
        )
        st = _compute_70b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["mishoe_sync_errno"])
            self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
        else:
            self.assertEqual(st["mishoe_sync_errno"], P380_EINVAL_ERRNO)
            self.assertFalse(evaluate_saveload_camset_mishoe_sync_vault(spec).passed)
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        sa = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_areadate_dst_grid_cleanhdmi_vault(sa).passed, expect_pass)

        sb = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_saveload_camset_mishoe_sync_vault(sb).passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        sa = build_default_safe_areadate_dst_grid_cleanhdmi_vault_spec(
            daylight_savings="On",
            grid_line_display="On",
            grid_line_type="Square Grid",
            marker_display="On",
            marker_guideframe="On",
            reset_action=reset_action,
            reported_initial_setting_wizard_triggered=init,
            post_daylight_savings=P380_FX3_DAYLIGHT_SAVINGS_DEFAULT if init else "On",
            post_area_date_retained=(not init),
            post_grid_line_display=P380_FX3_GRID_LINE_DISPLAY_DEFAULT if init else "On",
            post_grid_line_type=P380_FX3_GRID_LINE_TYPE_DEFAULT if init else "Square Grid",
            post_marker_display=P380_FX3_MARKER_DISPLAY_DEFAULT if init else "On",
            post_marker_guideframe=P380_FX3_MARKER_DISPLAY_DEFAULT if init else "On",
        )
        self.assertTrue(evaluate_areadate_dst_grid_cleanhdmi_vault(sa).passed)

        sb = build_default_safe_saveload_camset_mishoe_sync_vault_spec(
            reset_action=reset_action,
            post_body_cam_memory_retained=(not init),
            post_external_flash_set_retained=(not init),
        )
        self.assertTrue(evaluate_saveload_camset_mishoe_sync_vault(sb).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase380_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_70_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_70_PILLAR_IDS[idx])
    return _test


def _make_fault_inject_pillar_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        pid = MASTER_70_PILLAR_IDS[idx]
        m = evaluate_realhw_70pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid,
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, 69)
        self.assertEqual(m.failed_pillars, (pid,))
    return _test


def _install_parameterized_tests() -> None:
    idx = 24

    # 1. All 30 AREA_GMT_* zones + 2 invalid zones (32 tests)
    for z in P380_FX3_AREA_GMT_30_ZONES:
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_area_zone_valid_{z.lower()}",
            _make_area_gmt_zone_test(z, True),
        )
        idx += 1
    for bad_z in ("AREA_GMT_P_13_0", "AREA_GMT_M_12_0"):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_area_zone_reject_{bad_z.lower()}",
            _make_area_gmt_zone_test(bad_z, False),
        )
        idx += 1

    # 2. Date Formats (3 valid + 2 invalid = 5 tests)
    for fmt, ok in (("Y-M-D", True), ("M-D-Y", True), ("D-M-Y", True), ("YYYY-MM-DD", False), ("YYMMDD", False)):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_date_format_{fmt.lower().replace('-', '_')}",
            _make_date_format_test(fmt, ok),
        )
        idx += 1

    # 3. RTC Backup charge hours sweep (5 tests)
    for hrs in (0, 12, 23, 24, 36):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_rtc_charge_hours_{hrs:02d}",
            _make_rtc_charge_hours_test(hrs),
        )
        idx += 1

    # 4. FX6 UTC offset boundary sweep (8 tests)
    for off, ok in ((-750, False), (-720, True), (-30, True), (0, True), (15, False), (330, True), (840, True), (870, False)):
        tag = f"m{abs(off)}" if off < 0 else f"p{off}"
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx6_utc_offset_{tag}",
            _make_fx6_utc_offset_test(off, ok),
        )
        idx += 1

    # 5. FX6 Date Mode x 12h/24h (6 tests)
    for dm in P380_FX6_DATE_MODES:
        for tf in P380_FX6_TIME_FORMAT_MODES:
            setattr(
                Phase380MilestonePillar70VerifierTests,
                f"test_{idx:03d}_fx6_clock_{dm.lower()}_{tf.lower()}",
                _make_fx6_date_time_fmt_test(dm, tf),
            )
            idx += 1

    # 6. Grid Line Types (3 valid + Golden Ratio rejected) & 3 Shooting Domains (7 tests)
    for gt in P380_FX3_GRID_LINE_TYPES:
        clean = gt.lower().replace(" ", "_").replace(".", "").replace("+", "plus")
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_grid_type_valid_{clean}",
            _make_grid_type_test(gt, True),
        )
        idx += 1
    setattr(
        Phase380MilestonePillar70VerifierTests,
        f"test_{idx:03d}_fx3_grid_type_reject_golden_ratio",
        _make_grid_type_test("Golden Ratio Grid", False),
    )
    idx += 1
    for dom in P380_FX3_GRID_LINE_ALLOWED_DOMAINS:
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_grid_allmode_{dom.lower().replace('&', '_')}",
            _make_grid_domain_test(dom),
        )
        idx += 1

    # 7. Grid Line HDMI passthrough truth table (16 tests)
    for gd in ("Off", "On"):
        for hi in ("Off", "On"):
            for rm in ("On", "Off(HDMI Only)"):
                for rw in ("Off", "On"):
                    rm_tag = "on" if rm == "On" else "hdmionly"
                    setattr(
                        Phase380MilestonePillar70VerifierTests,
                        f"test_{idx:03d}_grid_hdmi_g{gd.lower()}_i{hi.lower()}_r{rm_tag}_w{rw.lower()}",
                        _make_grid_hdmi_truth_test(gd, hi, rm, rw),
                    )
                    idx += 1

    # 8. Marker Display across Still/Movie/S&Q x Focus Magnifier (6 tests)
    for dom in ("Still", "Movie", "S&Q"):
        for fmag in (False, True):
            setattr(
                Phase380MilestonePillar70VerifierTests,
                f"test_{idx:03d}_marker_{dom.lower().replace('&', '_')}_fmag_{int(fmag)}",
                _make_marker_domain_focus_mag_test(dom, fmag),
            )
            idx += 1

    # 9. FX6 Center Marker & Safety Area options (9 tests)
    for cm in P380_FX6_CENTER_MARKER_MODES:
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx6_center_marker_{cm.lower()}",
            _make_fx6_marker_option_test(cm, "90%"),
        )
        idx += 1
    for sa in P380_FX6_SAFETY_AREA_PERCENTAGES:
        clean_sa = sa.replace("%", "pct").replace(".", "_")
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx6_safety_area_{clean_sa}",
            _make_fx6_marker_option_test("1", sa),
        )
        idx += 1

    # 10. CAMSET01..10.DAT slot index 0..11 (12 tests)
    for si in range(0, 12):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_camset_slot_index_{si:02d}",
            _make_camset_slot_index_test(si),
        )
        idx += 1

    # 11. All 18 official CAMSET excluded items individually blocked (18 tests)
    for ex_i, item in enumerate(P380_FX3_CAMSET_OFFICIAL_EXCLUDED_ITEMS):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_camset_exclude_item_{ex_i:02d}",
            _make_camset_excluded_item_test(item),
        )
        idx += 1

    # 12. CAMSET cross-version compatibility matrix (6 tests)
    for sv, ok in (("1.00", False), ("1.01", False), ("2.00", True), ("2.05", True), ("4.00", True), ("7.02", True)):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_camset_fw_compat_{sv.replace('.', '_')}",
            _make_camset_version_compat_test(sv, ok),
        )
        idx += 1

    # 13. Camera Set. Memory M1..M4 x Slot 1/2 (8 tests)
    for ms in P380_FX3_CAMERA_SET_MEMORY_CARD_SLOTS:
        for sl in (1, 2):
            setattr(
                Phase380MilestonePillar70VerifierTests,
                f"test_{idx:03d}_campr_{ms.lower()}_slot{sl}",
                _make_campr_memory_slot_test(ms, sl),
            )
            idx += 1

    # 14. Video Light Modes FX3 (4) & FX6 (3 + Auto rejected) (8 tests)
    for vm in P380_FX3_VIDEO_LIGHT_MODES:
        clean = vm.lower().replace(" ", "_").replace("&", "_and_")
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx3_videolight_{clean}",
            _make_video_light_mode_test(P380_FX3_MODEL_NAME, vm, True),
        )
        idx += 1
    for vm in P380_FX6_VIDEO_LIGHT_MODES:
        clean = vm.lower().replace(" ", "_").replace("+", "plus")
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fx6_videolight_{clean}",
            _make_video_light_mode_test(P380_FX6_DONOR_MODEL_NAME, vm, True),
        )
        idx += 1
    setattr(
        Phase380MilestonePillar70VerifierTests,
        f"test_{idx:03d}_fx6_videolight_reject_auto",
        _make_video_light_mode_test(P380_FX6_DONOR_MODEL_NAME, "Auto", False),
    )
    idx += 1

    # 15. MI-Shoe PMIC 5V current budget sweep (5 tests)
    for ma in (0, 450, 900, 901, 1200):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_mishoe_pmic_5v_{ma:04d}ma",
            _make_pmic_current_test(ma),
        )
        idx += 1

    # 16. Flash sync & trigger voltage limits (7 tests)
    for sr, vv, ok in (
        (125, 12, True),
        (250, 12, True),
        (320, 12, False),
        (250, 249, True),
        (250, 250, False),
        (250, 300, False),
        (500, 12, False),
    ):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_flash_sync_1_{sr}_v{vv}",
            _make_flash_sync_voltage_test(sr, vv, ok),
        )
        idx += 1

    # 17. Slot-1 Tier-0 EROFS=30 write-mutating actions x 2 errnos (12 tests)
    for action in sorted(P380_WRITE_MUTATING_SLOT1_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP"):
            setattr(
                Phase380MilestonePillar70VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 18. Reset Action Matrices (3 tests)
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 19. All 18 Wave-68 donor artifacts individually verified (18 tests)
    for d_i in range(18):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # 20. Key & final pillars across MASTER_70_PILLAR_IDS (16 tests)
    for p_i in (*range(0, 65, 5), 67, 68, 69):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1

    # 21. Fault injection across 5 key pillars incl. 68, 69 & 70 (5 tests)
    for p_i in (0, 21, 67, 68, 69):
        setattr(
            Phase380MilestonePillar70VerifierTests,
            f"test_{idx:03d}_fault_inject_pillar_{p_i+1:02d}",
            _make_fault_inject_pillar_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
