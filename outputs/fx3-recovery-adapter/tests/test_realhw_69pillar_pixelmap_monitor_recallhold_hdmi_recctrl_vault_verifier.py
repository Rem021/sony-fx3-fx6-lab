"""Phase 377 (Pillar 69 & 69/69 Milestone) unit tests:
Wave-67 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` empirical telemetry across Pillars 69A & 69B:
- Pillar 69A (`[Pixel Mapping]` / `[Auto Pixel Mapping]` Silent Target + Battery Check + Lens Cap + ELF typos
  vs FX6 `APR` & Zero `ABB`; `Setup -> [Monitor]` 3-item group + thermal lock + dormant 4 EVF items debunk
  vs FX6 `VF Setting`/`VF Adjust`/`MIRROR`; Hold custom keys + Still-only `P/A/S/M` `[Recall Custom hold 1-3]`
  exact 11 bits + zero independent WB + `CAMSET` vs `CAMPR` vs FX6 `Push AF/AGC/Iris` & dormant `High/Low Key`).
- Pillar 69B (`Setup -> [External Output]` reset-resistant HDMI matrix, `[Rec. Media dur HDMI Output]` `S&Q`
  lock & `HDMI Info. Display` override, `Log`/`PPLUT1..4` 1080 downscale, `24.00p` reboot & playback isolation,
  `[Time Code Output]` -> `[REC Control]` hard precondition, `[4ch Audio Output]` 2ch pair, `[CTRL FOR HDMI]`
  typo, dormant `4K/2K` & `24p/60p` debunk, FX6 `12G/6G/3G-SDI + HDMI` dual-output matrix, and Tier-0 `Slot 1`
  `EROFS=30` Recovery Vault Firewall).
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
    MASTER_69_PILLAR_COUNT,
    MASTER_69_PILLAR_IDS,
    MASTER_69_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P377_AIRPLANE_MODE_FORCED_ON,
    P377_BKID_CTRL_FOR_HDMI_SONY_TYPO,
    P377_BKID_PIXEL_MAP_EXECUTED_STATUS_SONY_TYPO,
    P377_BKID_PIXEL_MAP_NOTIFICATION_SONY_TYPO,
    P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT,
    P377_BLOCKED_INVALID_PILLAR69A_SPEC,
    P377_BLOCKED_INVALID_PILLAR69B_SPEC,
    P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT,
    P377_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P377_BLOCKED_PIXELMAP_APR_OR_ZERO_ABB_DRIFT,
    P377_BLOCKED_RECALL_HOLD_11BIT_OR_PUSH_KEY_DRIFT,
    P377_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P377_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P377_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P377_CONCURRENT_CEILING_SECONDS,
    P377_CROSS_MODEL_FLASH_AUTHORIZED,
    P377_DONOR_FX3_APPFW_702_RELPATH,
    P377_DONOR_FX3_BACKUP_BIN_RELPATH,
    P377_DONOR_FX3_UXC_EN_RELPATH,
    P377_DONOR_FX6_APPFW_601_RELPATH,
    P377_DONOR_FX6_UXC_EN_2_RELPATH,
    P377_DONOR_FX6_UXC_EN_RELPATH,
    P377_DONOR_INSPECT_BUDGET_SECONDS,
    P377_EBUSY_ERRNO,
    P377_EINVAL_ERRNO,
    P377_ELF_BATTERY_CHECK_PIXEL_MAP_SYMBOL,
    P377_ELF_SHUTTER_MUTE_PIXEL_MAP_SYMBOL,
    P377_EMMC_WRITES_AUTHORIZED,
    P377_ENOENT_ERRNO,
    P377_ENV_CLEAN_ROOM_TEST,
    P377_EOPNOTSUPP_ERRNO,
    P377_EROFS_ERRNO,
    P377_FAST_CLI_BUDGET_SECONDS,
    P377_FX3_4K_OUTPUT_HDMI_ONLY_RATES,
    P377_FX3_AUTO_PIXEL_MAP_DEFAULT,
    P377_FX3_AUTO_PIXEL_MAP_RESETTABLE,
    P377_FX3_CTRL_FOR_HDMI_DEFAULT,
    P377_FX3_DISPLAY_QUALITY_DEFAULT,
    P377_FX3_DORMANT_EVF_ITEMS,
    P377_FX3_EXTERNAL_OUTPUT_RESETTABLE,
    P377_FX3_FW_VERSION,
    P377_FX3_HAS_DORMANT_24P_60P_OUTPUT,
    P377_FX3_HAS_DORMANT_4K_2K_OUTPUT,
    P377_FX3_HAS_DORMANT_EVF_ITEMS_EXPOSED,
    P377_FX3_HAS_FINDER_MONITOR_GROUP,
    P377_FX3_HAS_PIXEL_MAP_NOTIFICATION_EXPOSED,
    P377_FX3_HDMI_4CH_AUDIO_DEFAULT,
    P377_FX3_HDMI_4CH_AUDIO_MODES,
    P377_FX3_HDMI_INFO_DISPLAY_DEFAULT,
    P377_FX3_HDMI_REC_CONTROL_DEFAULT,
    P377_FX3_HDMI_RESOLUTION_MODES,
    P377_FX3_HDMI_TC_OUTPUT_DEFAULT,
    P377_FX3_HELPGUIDE_ID,
    P377_FX3_MODEL_ID,
    P377_FX3_MODEL_NAME,
    P377_FX3_MONITOR_BRIGHTNESS_DEFAULT,
    P377_FX3_MONITOR_EXPOSED_ITEMS,
    P377_FX3_MONITOR_FLIP_DEFAULT,
    P377_FX3_MONITOR_FLIP_DIRECTIONS,
    P377_FX3_MONITOR_GROUP_NAME,
    P377_FX3_MONITOR_GROUP_RESETTABLE,
    P377_FX3_OUTPUT_RESOLUTION_DEFAULT,
    P377_FX3_PPLUT_SLOTS,
    P377_FX3_RECALL_CUSTOM_HOLD_11_BITS,
    P377_FX3_RECALL_CUSTOM_HOLD_ALLOWED_MODES,
    P377_FX3_RECALL_CUSTOM_HOLD_BIT_COUNT,
    P377_FX3_RECALL_CUSTOM_HOLD_HAS_INDEPENDENT_WB,
    P377_FX3_RECALL_CUSTOM_HOLD_SLOTS,
    P377_FX3_RECALL_CUSTOM_HOLD_WB_HITS,
    P377_FX3_REC_MEDIA_DUR_HDMI_DEFAULT,
    P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMPR,
    P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMSET,
    P377_FX3_REG_CUSTOM_SHOOT_SET_RESETTABLE,
    P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT,
    P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_RESETTABLE,
    P377_FX6_CODEC_MODES,
    P377_FX6_DONOR_FW_VERSION,
    P377_FX6_DONOR_MODEL_NAME,
    P377_FX6_HAS_HIGH_LOW_KEY_EXPOSED,
    P377_FX6_HAS_MECHANICAL_SHUTTER,
    P377_FX6_HAS_RECALL_CUSTOM_HOLD,
    P377_FX6_HAS_USER_EXPOSED_ABB,
    P377_FX6_HAS_VF_4ITEM_SUBMENU,
    P377_FX6_MIRROR_SWITCH_POSITIONS,
    P377_FX6_SDI_HDMI_REC_CONTROL_MODES,
    P377_FX6_VF_BRIGHTNESS_DEFAULT,
    P377_FX6_VF_BRIGHTNESS_RANGE,
    P377_FX6_VF_COLOR_MODES,
    P377_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P377_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P377_PILLAR_69A_SCENARIO_IDS,
    P377_PILLAR_69B_SCENARIO_IDS,
    P377_PINNED_FX3_BACKUP_BIN_SHA256,
    P377_PRM_HAITA_HDMI_4K_OUTPUTE_SONY_TYPO,
    P377_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P377_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P377_STATUS_FAIL_69OF69_AGGREGATOR,
    P377_STATUS_VERIFIED_69OF69_AGGREGATOR,
    P377_STATUS_VERIFIED_PILLAR69_SUITE,
    P377_STATUS_VERIFIED_PILLAR_69A,
    P377_STATUS_VERIFIED_PILLAR_69B,
    P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE377_MASTER_SCHEMA,
    PHASE377_PHASE_NUMBER,
    PHASE377_SCHEMA,
    PHASE377_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec,
    build_default_safe_pixelmap_monitor_recallhold_vault_spec,
    compute_expected_hdmi_recctrl_24p_sdi_slot1_vault_state,
    compute_expected_pixelmap_monitor_recallhold_vault_state,
    evaluate_69pillar_recovery_master,
    evaluate_hdmi_recctrl_24p_sdi_slot1_vault,
    evaluate_pixelmap_monitor_recallhold_vault,
    evaluate_realhw_69pillar_recovery_master,
    inspect_phase377_donors_readonly,
    run_pillar69_standalone_suite,
    run_pillar69a_pixelmap_monitor_recallhold_vault_6_scenario_suite,
    run_pillar69b_hdmi_recctrl_24p_sdi_slot1_vault_6_scenario_suite,
    verify_69pillar_recovery,
    verify_69pillar_recovery_master,
    verify_69pillar_recovery_suite,
    verify_all_69_recovery_pillars,
    verify_pixelmap_monitor_recallhold_hdmi_recctrl_and_vault,
    verify_pixelmap_monitor_recallhold_hdmi_recctrl_vault,
)


def _wave67_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P377_DONOR_FX3_APPFW_702_RELPATH,
        P377_DONOR_FX3_BACKUP_BIN_RELPATH,
        P377_DONOR_FX3_UXC_EN_RELPATH,
        P377_DONOR_FX6_APPFW_601_RELPATH,
        P377_DONOR_FX6_UXC_EN_RELPATH,
        P377_DONOR_FX6_UXC_EN_2_RELPATH,
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


def _compute_69a_from_spec(spec: fr.PixelMapMonitorRecallHoldVaultSpec) -> dict[str, Any]:
    return compute_expected_pixelmap_monitor_recallhold_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        focus_mode=spec.focus_mode,
        setup_auto_pixel_mapping=spec.setup_auto_pixel_mapping,
        silent_mode=spec.silent_mode,
        silent_target_auto_pixel_mapping=spec.silent_target_auto_pixel_mapping,
        manual_pixel_mapping_requested=spec.manual_pixel_mapping_requested,
        manual_pixel_map_lens_cap_attached=spec.manual_pixel_map_lens_cap_attached,
        manual_pixel_map_battery_ok=spec.manual_pixel_map_battery_ok,
        pixel_map_notification_requested=spec.pixel_map_notification_requested,
        fx6_apr_requested=spec.fx6_apr_requested,
        fx6_apr_lens_cap_and_black_cloth=spec.fx6_apr_lens_cap_and_black_cloth,
        fx6_apr_temperature_valid=spec.fx6_apr_temperature_valid,
        fx6_abb_requested=spec.fx6_abb_requested,
        monitor_group_name=spec.monitor_group_name,
        monitor_brightness_mode=spec.monitor_brightness_mode,
        monitor_brightness_manual_level=spec.monitor_brightness_manual_level,
        display_quality=spec.display_quality,
        thermal_elevated=spec.thermal_elevated,
        monitor_flip_direction=spec.monitor_flip_direction,
        dormant_evf_item_requested=spec.dormant_evf_item_requested,
        fx6_vf_connected=spec.fx6_vf_connected,
        fx6_vf_brightness=spec.fx6_vf_brightness,
        fx6_vf_color_mode=spec.fx6_vf_color_mode,
        fx6_vf_adjust_pressed=spec.fx6_vf_adjust_pressed,
        fx6_mirror_switch=spec.fx6_mirror_switch,
        fx6_vf_4item_submenu_requested=spec.fx6_vf_4item_submenu_requested,
        hold_custom_key=spec.hold_custom_key,
        recall_selected_bits=spec.recall_selected_bits,
        recall_independent_wb_requested=spec.recall_independent_wb_requested,
        recall_drive_mode_selftimer_requested=spec.recall_drive_mode_selftimer_requested,
        recall_persists_in_camset=spec.recall_persists_in_camset,
        recall_persists_in_campr=spec.recall_persists_in_campr,
        fx6_push_key=spec.fx6_push_key,
        fx6_lens_manual_mode=spec.fx6_lens_manual_mode,
        fx6_bokeh_control_on=spec.fx6_bokeh_control_on,
        fx6_desqueeze_active=spec.fx6_desqueeze_active,
        fx6_high_low_key_requested=spec.fx6_high_low_key_requested,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_69b_from_spec(spec: fr.HdmiRecCtrl24pSdiSlot1VaultSpec) -> dict[str, Any]:
    return compute_expected_hdmi_recctrl_24p_sdi_slot1_vault_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        log_shooting_mode=spec.log_shooting_mode,
        picture_profile=spec.picture_profile,
        hdmi_resolution=spec.hdmi_resolution,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
        output_resolution=spec.output_resolution,
        hdmi_4k_output_rate_prev=spec.hdmi_4k_output_rate_prev,
        hdmi_4k_output_rate_new=spec.hdmi_4k_output_rate_new,
        raw_output_enabled=spec.raw_output_enabled,
        time_code_output=spec.time_code_output,
        rec_control=spec.rec_control,
        compatible_external_recorder_connected=spec.compatible_external_recorder_connected,
        usb_streaming_active=spec.usb_streaming_active,
        hdmi_4ch_audio_output=spec.hdmi_4ch_audio_output,
        four_discrete_hdmi_audio_requested=spec.four_discrete_hdmi_audio_requested,
        hdmi_info_display=spec.hdmi_info_display,
        ctrl_for_hdmi=spec.ctrl_for_hdmi,
        dormant_4k_2k_output_requested=spec.dormant_4k_2k_output_requested,
        dormant_24p_60p_output_requested=spec.dormant_24p_60p_output_requested,
        fx6_sdi_output_on=spec.fx6_sdi_output_on,
        fx6_hdmi_output_on=spec.fx6_hdmi_output_on,
        fx6_codec_mode=spec.fx6_codec_mode,
        fx6_sq_fps=spec.fx6_sq_fps,
        fx6_hdmi_tc_out=spec.fx6_hdmi_tc_out,
        fx6_sdi_hdmi_rec_control=spec.fx6_sdi_hdmi_rec_control,
        fx6_card_inserted=spec.fx6_card_inserted,
        reset_action=spec.reset_action,
        recording_target_slot=spec.recording_target_slot,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


class Phase377Pillar69VerifierTests(unittest.TestCase):
    """Core & parameterized four-mode unit tests for Phase 377 (Pillar 69A + 69B + 69/69 Master)."""

    def test_001_safety_redlines_and_pinned_metadata(self) -> None:
        self.assertEqual(
            PHASE377_SCHEMA,
            "realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier_v1",
        )
        self.assertEqual(PHASE377_MASTER_SCHEMA, "realhw_69pillar_recovery_master_v1")
        self.assertEqual(PHASE377_VERSION, "1.0.0")
        self.assertEqual(PHASE377_PHASE_NUMBER, 377)
        self.assertEqual(MASTER_69_PILLAR_COUNT, 69)
        self.assertEqual(len(MASTER_69_PILLAR_SPECS), 69)
        self.assertEqual(len(MASTER_69_PILLAR_IDS), 69)
        self.assertEqual(P377_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P377_CONCURRENT_CEILING_SECONDS, 6.00)
        self.assertEqual(P377_DONOR_INSPECT_BUDGET_SECONDS, 2.0)

        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P377_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P377_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertTrue(P377_AIRPLANE_MODE_FORCED_ON)

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
            P377_EMMC_WRITES_AUTHORIZED,
            P377_CROSS_MODEL_FLASH_AUTHORIZED,
            P377_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            P377_OVERALL_READY_FOR_HARDWARE_ATTACH,
            P377_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
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
        self.assertTrue(hasattr(fr, "verify_67pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_68pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_69pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_69pillar_recovery_master"))
        self.assertTrue(callable(verify_69pillar_recovery))
        self.assertTrue(callable(verify_69pillar_recovery_master))
        self.assertTrue(callable(verify_all_69_recovery_pillars))
        self.assertTrue(callable(evaluate_69pillar_recovery_master))
        self.assertIs(
            fr.realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier,
            sys.modules[
                "fx3_recovery.realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier"
            ],
        )

    def test_003_wave67_empirical_constants_and_sony_elf_typos(self) -> None:
        self.assertEqual(P377_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P377_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P377_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P377_FX3_FW_VERSION, "7.02")
        self.assertEqual(P377_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P377_FX6_DONOR_FW_VERSION, "6.01")

        # Exact Sony ELF typos
        self.assertEqual(
            P377_BKID_PIXEL_MAP_NOTIFICATION_SONY_TYPO,
            "BKID_APP_setting_notification_for_pixel_mappinng",
        )
        self.assertEqual(
            P377_BKID_PIXEL_MAP_EXECUTED_STATUS_SONY_TYPO,
            "BKID_APP_pixel_mapping_excuted_status",
        )
        self.assertEqual(
            P377_PRM_HAITA_HDMI_4K_OUTPUTE_SONY_TYPO,
            "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
        )
        self.assertEqual(
            P377_BKID_CTRL_FOR_HDMI_SONY_TYPO,
            "BKID_APP_setting_ctrl_for_hmdi",
        )
        self.assertEqual(
            P377_ELF_BATTERY_CHECK_PIXEL_MAP_SYMBOL,
            "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
        )
        self.assertEqual(
            P377_ELF_SHUTTER_MUTE_PIXEL_MAP_SYMBOL,
            "vdf_set_shutter_mute_by_pixel_mapping",
        )

        # Debunks & counts
        self.assertEqual(P377_FX3_MONITOR_GROUP_NAME, "Monitor")
        self.assertFalse(P377_FX3_HAS_FINDER_MONITOR_GROUP)
        self.assertEqual(len(P377_FX3_MONITOR_EXPOSED_ITEMS), 3)
        self.assertEqual(len(P377_FX3_DORMANT_EVF_ITEMS), 4)
        self.assertFalse(P377_FX3_HAS_DORMANT_EVF_ITEMS_EXPOSED)
        self.assertFalse(P377_FX3_MONITOR_GROUP_RESETTABLE)

        self.assertEqual(len(P377_FX3_RECALL_CUSTOM_HOLD_11_BITS), 11)
        self.assertEqual(P377_FX3_RECALL_CUSTOM_HOLD_BIT_COUNT, 11)
        self.assertEqual(P377_FX3_RECALL_CUSTOM_HOLD_WB_HITS, 0)
        self.assertFalse(P377_FX3_RECALL_CUSTOM_HOLD_HAS_INDEPENDENT_WB)
        self.assertNotIn("white_balance", P377_FX3_RECALL_CUSTOM_HOLD_11_BITS)
        self.assertFalse(P377_FX3_REG_CUSTOM_SHOOT_SET_RESETTABLE)
        self.assertTrue(P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMSET)
        self.assertFalse(P377_FX3_REG_CUSTOM_SHOOT_SET_IN_CAMPR)

        self.assertFalse(P377_FX3_AUTO_PIXEL_MAP_RESETTABLE)
        self.assertTrue(P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_RESETTABLE)
        self.assertFalse(P377_FX3_HAS_PIXEL_MAP_NOTIFICATION_EXPOSED)
        self.assertFalse(P377_FX3_EXTERNAL_OUTPUT_RESETTABLE)
        self.assertFalse(P377_FX3_HAS_DORMANT_4K_2K_OUTPUT)
        self.assertFalse(P377_FX3_HAS_DORMANT_24P_60P_OUTPUT)
        self.assertFalse(P377_FX6_HAS_MECHANICAL_SHUTTER)
        self.assertFalse(P377_FX6_HAS_USER_EXPOSED_ABB)
        self.assertFalse(P377_FX6_HAS_VF_4ITEM_SUBMENU)
        self.assertFalse(P377_FX6_HAS_RECALL_CUSTOM_HOLD)
        self.assertFalse(P377_FX6_HAS_HIGH_LOW_KEY_EXPOSED)

    def test_004_donor_inspect_clean_room_and_local_o_rdonly(self) -> None:
        snap_clean = inspect_phase377_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_clean.donor_files_inspected, 17)
        self.assertTrue(snap_clean.all_donors_present)
        self.assertEqual(snap_clean.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap_clean.under_2_0s_budget)

        snap_auto = inspect_phase377_donors_readonly()
        self.assertEqual(snap_auto.donor_files_inspected, 17)
        self.assertTrue(snap_auto.all_donors_present)
        self.assertEqual(snap_auto.raw_firmware_bytes_leaked, 0)
        if _wave67_donors_present() and not (
            os.environ.get(P377_ENV_CLEAN_ROOM_TEST) == "1"
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        ):
            self.assertEqual(snap_auto.verification_mode, "LOCAL_DONOR_O_RDONLY")

    def test_005_donor_inspect_all_four_modes_including_work_root_none(self) -> None:
        with patch.dict(os.environ, {P377_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase377_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 17)
            self.assertTrue(snap.all_donors_present)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap2 = inspect_phase377_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap2.donor_files_inspected, 17)

        with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
            snap_none = inspect_phase377_donors_readonly(force_clean_room=False)
            self.assertEqual(snap_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_none.donor_files_inspected, 17)
            self.assertTrue(snap_none.all_donors_present)

            m_none = verify_69pillar_recovery_suite()
            self.assertTrue(m_none.all_passed)
            self.assertEqual(m_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(m_none.pillars_passed, m_none.pillar_count)
            self.assertEqual(m_none.pillar_count, 69)

    def test_006_donor_inspect_bad_marker_rejection_helpers(self) -> None:
        mod = fr.realhw_69pillar_pixelmap_monitor_recallhold_hdmi_recctrl_vault_verifier
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
        rep_a = evaluate_pixelmap_monitor_recallhold_vault(
            build_default_safe_pixelmap_monitor_recallhold_vault_spec()
        )
        self.assertTrue(rep_a.passed)
        self.assertEqual(rep_a.status, P377_STATUS_VERIFIED_PILLAR_69A)
        self.assertIsNone(rep_a.block_code)

        rep_b = evaluate_hdmi_recctrl_24p_sdi_slot1_vault(
            build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec()
        )
        self.assertTrue(rep_b.passed)
        self.assertEqual(rep_b.status, P377_STATUS_VERIFIED_PILLAR_69B)
        self.assertIsNone(rep_b.block_code)

        comb1 = verify_pixelmap_monitor_recallhold_hdmi_recctrl_and_vault(force_clean_room=True)
        comb2 = verify_pixelmap_monitor_recallhold_hdmi_recctrl_vault(force_clean_room=True)
        self.assertTrue(comb1.all_passed)
        self.assertTrue(comb2.all_passed)
        self.assertEqual(comb1.status, P377_STATUS_VERIFIED_PILLAR69_SUITE)
        self.assertEqual(comb1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(comb1.slot1_writes, 0)
        self.assertEqual(_strip_volatile_timing(comb1.to_dict()), _strip_volatile_timing(comb2.to_dict()))

    def test_008_pillar69a_auto_pixel_mapping_silent_target_and_manual_gates(self) -> None:
        # Setup=On + SilentMode=On + SilentTarget=On -> mutes shutdown mechanical shutter sound
        spec_muted = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            setup_auto_pixel_mapping="On",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
            reported_effective_silent_target_auto_pixel_mapping="On",
            reported_shutdown_shutter_sound_emitted=False,
            reset_action="Camera Settings Reset",
            post_auto_pixel_mapping="On",  # Resists Reset!
            post_silent_target_auto_pixel_mapping="Off",  # Can be reset!
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec_muted).passed)

        # Manual Pixel Mapping with lens cap + battery ok -> triggers auto reboot
        spec_man = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            manual_pixel_mapping_requested=True,
            manual_pixel_map_lens_cap_attached=True,
            manual_pixel_map_battery_ok=True,
            reported_manual_pixel_map_auto_reboot=True,
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec_man).passed)

        # Low battery -> EBUSY(16)
        spec_low_bat = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            manual_pixel_mapping_requested=True,
            manual_pixel_map_battery_ok=False,
        )
        self.assertEqual(_compute_69a_from_spec(spec_low_bat)["pixelmap_errno"], P377_EBUSY_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_low_bat).passed)

        # Lens cap missing -> EINVAL(22)
        spec_no_cap = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            manual_pixel_mapping_requested=True,
            manual_pixel_map_lens_cap_attached=False,
        )
        self.assertEqual(_compute_69a_from_spec(spec_no_cap)["pixelmap_errno"], P377_EINVAL_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_no_cap).passed)

    def test_009_pillar69a_fx6_apr_light_temp_and_zero_abb_debunk(self) -> None:
        # FX6 APR missing lens cap + black cloth -> EINVAL (LIGHT_DETECTED)
        spec_light = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_apr_requested=True,
            fx6_apr_lens_cap_and_black_cloth=False,
        )
        self.assertEqual(_compute_69a_from_spec(spec_light)["pixelmap_errno"], P377_EINVAL_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_light).passed)

        # FX6 APR invalid temperature -> EBUSY (INVALID_TEMPERATURE)
        spec_temp = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_apr_requested=True,
            fx6_apr_lens_cap_and_black_cloth=True,
            fx6_apr_temperature_valid=False,
        )
        self.assertEqual(_compute_69a_from_spec(spec_temp)["pixelmap_errno"], P377_EBUSY_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_temp).passed)

        # FX6 dormant ABB requested -> EOPNOTSUPP(95)
        spec_abb = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_abb_requested=True,
        )
        self.assertEqual(_compute_69a_from_spec(spec_abb)["pixelmap_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_abb).passed)

    def test_010_pillar69a_monitor_group_debunk_thermal_lock_and_fx6_vf(self) -> None:
        # Finder/Monitor group name rejected on EVF-less FX3
        spec_fm = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            monitor_group_name="Finder/Monitor",
        )
        self.assertEqual(_compute_69a_from_spec(spec_fm)["monitor_errno"], P377_EOPNOTSUPP_ERRNO)
        rep_fm = evaluate_pixelmap_monitor_recallhold_vault(spec_fm)
        self.assertFalse(rep_fm.passed)
        self.assertEqual(rep_fm.block_code, P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT)

        # Thermal elevated locks Display Quality back to Standard
        spec_th = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            display_quality="High",
            thermal_elevated=True,
            reported_effective_display_quality="Standard",
            reported_thermal_display_quality_locked=True,
            post_display_quality="High",
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec_th).passed)

        # FX6 VF Adjust without viewfinder connected -> ENOENT(2)
        spec_vf_disc = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_vf_connected=False,
            fx6_vf_adjust_pressed=True,
        )
        self.assertEqual(_compute_69a_from_spec(spec_vf_disc)["monitor_errno"], P377_ENOENT_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_vf_disc).passed)

        # FX6 4-item VF submenu debunk -> EOPNOTSUPP(95)
        spec_vf4 = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_vf_4item_submenu_requested=True,
        )
        self.assertEqual(_compute_69a_from_spec(spec_vf4)["dormant_evf_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_vf4).passed)

    def test_011_pillar69a_recall_custom_hold_still_pasm_only_zero_wb_and_camset(self) -> None:
        # Independent White Balance rejected EOPNOTSUPP(95)
        spec_wb = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            recall_independent_wb_requested=True,
        )
        self.assertEqual(_compute_69a_from_spec(spec_wb)["recall_wb_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_wb).passed)

        # Putting "white_balance" into recall_selected_bits rejected
        spec_wb_bit = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            recall_selected_bits=P377_FX3_RECALL_CUSTOM_HOLD_11_BITS + ("white_balance",),
        )
        self.assertEqual(_compute_69a_from_spec(spec_wb_bit)["recall_wb_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(_compute_69a_from_spec(spec_wb_bit)["recall_bits_valid"])
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_wb_bit).passed)

        # Self-timer in drive_mode rejected
        spec_st = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            recall_drive_mode_selftimer_requested=True,
        )
        self.assertEqual(_compute_69a_from_spec(spec_st)["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_st).passed)

        # Serialized in CAMSET*.DAT, excluded from CAMPR*.DAT
        spec_campr = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            recall_persists_in_campr=True,
        )
        self.assertFalse(_compute_69a_from_spec(spec_campr)["recall_serialization_valid"])
        self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec_campr).passed)

    def test_012_pillar69a_fx6_push_af_agc_iris_lockouts_and_dormant_high_low_key(self) -> None:
        # Push AGC blocked in Cine EI / Cine EI Quick / Bokeh Control = On
        for exp_m, bokeh in (("Cine EI", False), ("Cine EI Quick", False), ("M", True)):
            s = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                camera_model=P377_FX6_DONOR_MODEL_NAME,
                fw_version=P377_FX6_DONOR_FW_VERSION,
                exposure_mode=exp_m,
                hold_custom_key="None",
                fx6_push_key="Push AGC",
                fx6_bokeh_control_on=bokeh,
            )
            self.assertEqual(_compute_69a_from_spec(s)["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)

        # Push Auto Iris blocked on lens MANUAL or Bokeh Control = On
        for man_l, bokeh in ((True, False), (False, True)):
            s = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
                camera_model=P377_FX6_DONOR_MODEL_NAME,
                fw_version=P377_FX6_DONOR_FW_VERSION,
                hold_custom_key="None",
                fx6_push_key="Push Auto Iris",
                fx6_lens_manual_mode=man_l,
                fx6_bokeh_control_on=bokeh,
            )
            self.assertEqual(_compute_69a_from_spec(s)["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)

        # Dormant High/Low Key blocked on FX6
        s_hl = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            hold_custom_key="None",
            fx6_high_low_key_requested=True,
        )
        self.assertEqual(_compute_69a_from_spec(s_hl)["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)

    def test_013_pillar69b_hdmi_tc_rec_control_gate_and_sq_lockouts(self) -> None:
        # REC Control = On without Time Code Output = On -> EOPNOTSUPP(95)
        s_no_tc = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            time_code_output="Off",
            rec_control="On",
        )
        self.assertEqual(_compute_69b_from_spec(s_no_tc)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(s_no_tc).passed)

        # REC Control = On without compatible external recorder -> EOPNOTSUPP(95)
        s_no_rec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            time_code_output="On",
            rec_control="On",
            compatible_external_recorder_connected=False,
        )
        self.assertEqual(_compute_69b_from_spec(s_no_rec)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)

        # S&Q locks Rec. Media dur HDMI Output = On and blocks Time Code Output = On
        s_sq_off = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            shooting_domain="S&Q",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            time_code_output="Off",
            rec_control="Off",
        )
        self.assertEqual(_compute_69b_from_spec(s_sq_off)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)

        s_sq_tc = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            shooting_domain="S&Q",
            rec_media_dur_hdmi_output="On",
            time_code_output="On",
            rec_control="Off",
        )
        self.assertEqual(_compute_69b_from_spec(s_sq_tc)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)

    def test_014_pillar69b_24_00p_reboot_chain_and_log_pplut_1080_downscale(self) -> None:
        # Switching 23.98p -> 24.00p forces reboot + playback isolation
        s_24 = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            hdmi_4k_output_rate_prev="23.98p 10bit",
            hdmi_4k_output_rate_new="24.00p 10bit",
            reported_reboot_required_for_24_00p_switch=True,
            reported_cross_24_00p_playback_isolated=True,
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(s_24).passed)

        # Log Shooting != Off with Rec. Media = On & RAW = Off forces 1080 downscale
        s_log = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            rec_media_dur_hdmi_output="On",
            log_shooting_mode="Cine EI",
            output_resolution="2160p",
            raw_output_enabled="Off",
            reported_effective_rec_media_dur_hdmi="On",
            reported_effective_output_resolution="1080p",
            reported_output_forced_1080_downscale=True,
            reported_effective_hdmi_info_display="On",
            reported_internal_media_write_attempted=True,
            post_rec_media_dur_hdmi="On",
            post_output_resolution="2160p",
            recording_target_slot=2,
            requested_vault_slot=2,
            requested_vault_action="WRITE_M4ROOT_CLIP_SLOT2",
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(s_log).passed)

    def test_015_pillar69b_dormant_4k2k_24p60p_and_4ch_discrete_debunk(self) -> None:
        for kw in (
            {"dormant_4k_2k_output_requested": True},
            {"dormant_24p_60p_output_requested": True},
            {"four_discrete_hdmi_audio_requested": True},
        ):
            s = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(**kw)
            self.assertEqual(_compute_69b_from_spec(s)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)
            rep = evaluate_hdmi_recctrl_24p_sdi_slot1_vault(s)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P377_BLOCKED_HDMI_RECCTRL_24P_OR_DORMANT_OUTPUT_DRIFT)

    def test_016_pillar69b_fx6_raw_hdmi_sdi_1080_and_sq_gt60_hdmi_1080(self) -> None:
        # FX6 RAW(HDMI) 4240x2392 forces SDI to 1080
        s_rawh = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            shooting_domain="Movie",
            fx6_codec_mode="RAW(HDMI)",
            fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
            fx6_hdmi_tc_out="On",
            fx6_card_inserted=False,
        )
        st = _compute_69b_from_spec(s_rawh)
        self.assertIsNone(st["hdmi_matrix_errno"])
        self.assertTrue(st["fx6_sdi_forced_1080"])
        self.assertFalse(st["fx6_hdmi_forced_1080"])

        # FX6 Parallel Rec without card inserted -> EOPNOTSUPP(95)
        s_nocard = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_sdi_hdmi_rec_control="Parallel Rec",
            fx6_card_inserted=False,
        )
        self.assertEqual(_compute_69b_from_spec(s_nocard)["hdmi_matrix_errno"], P377_EOPNOTSUPP_ERRNO)

    def test_017_pillar69_slot1_vault_erofs30_overlay_escape_and_h0_h3_drift(self) -> None:
        # Overlay escape -> BLOCKED_P377_PERSISTENT_OVERLAY_ESCAPE
        s_esc = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            overlay_dir="/dev/cnflasha/69b",
        )
        rep_esc = evaluate_hdmi_recctrl_24p_sdi_slot1_vault(s_esc)
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P377_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        # Backup.bin H0 != H3 -> BLOCKED_P377_TIER0_BACKUP_BIN_H0_H3_DRIFT
        s_h3 = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            backup_bin_h3_sha256="f" * 64,
        )
        rep_h3 = evaluate_pixelmap_monitor_recallhold_vault(s_h3)
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P377_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_018_standalone_69a_69b_12_scenario_suites(self) -> None:
        res_a = run_pillar69a_pixelmap_monitor_recallhold_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)
        self.assertEqual(res_a.status, P377_STATUS_VERIFIED_PILLAR_69A)

        res_b = run_pillar69b_hdmi_recctrl_24p_sdi_slot1_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)
        self.assertEqual(res_b.status, P377_STATUS_VERIFIED_PILLAR_69B)

        st1 = run_pillar69_standalone_suite(force_clean_room=True)
        st2 = run_pillar69_standalone_suite(force_clean_room=True)
        self.assertTrue(st1.all_passed)
        self.assertEqual(st1.suite_sha256, st2.suite_sha256)
        self.assertEqual(st1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st1.slot1_writes, 0)

    def test_019_master_69pillar_clean_room_and_determinism(self) -> None:
        m1 = evaluate_realhw_69pillar_recovery_master(force_clean_room=True)
        m2 = verify_69pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(m1.all_passed)
        self.assertTrue(m2.all_passed)
        self.assertEqual(m1.status, P377_STATUS_VERIFIED_69OF69_AGGREGATOR)
        self.assertEqual(m1.pillar_count, 69)
        self.assertEqual(m1.pillars_passed, 69)
        self.assertEqual(m1.failed_pillars, ())
        self.assertEqual(m1.master_69pillar_sha256, m2.master_69pillar_sha256)
        self.assertEqual(m1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m1.slot1_writes, 0)
        self.assertTrue(m1.under_1_5s_fast_cli_budget or m1.under_6s_budget)

    def test_020_master_69pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_69pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_021_cli_verify_pillar69_recovery_normal_and_clean_room(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs' / 'fx3-safety'}"
        for cmd in (
            "verify-pillar69-pixelmap-monitor-recallhold-hdmi-recctrl-vault",
            "verify-pillar69-recovery",
            "verify-69pillar-recovery",
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
        with tempfile.TemporaryDirectory(dir=work_tests, prefix="p377_cli_p69_") as td:
            out_dir = Path(td) / "p69_out"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-pillar69-recovery",
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
            self.assertEqual(payload["status"], P377_STATUS_VERIFIED_PILLAR69_SUITE)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(payload["slot1_writes"], 0)
            self.assertTrue(
                (out_dir / "pillar69-pixelmap-monitor-recallhold-hdmi-recctrl-vault-report.json").is_file()
            )

    def test_022_cli_verify_69pillar_recovery_json_and_out(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs' / 'fx3-safety'}"
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests, prefix="p377_cli_m69_") as td:
            out_dir = Path(td) / "m69_out"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-69pillar-recovery",
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
            self.assertEqual(payload["status"], P377_STATUS_VERIFIED_69OF69_AGGREGATOR)
            self.assertGreaterEqual(payload["pillar_count"], 69)
            self.assertEqual(payload["pillars_passed"], 69)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(payload["slot1_writes"], 0)
            self.assertTrue((out_dir / "69pillar-recovery-master-report.json").is_file())

    def test_023_cli_verify_69pillar_recovery_human_readable_summary(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-69pillar-recovery",
                "--force-clean-room",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("pillars=69/69", proc.stdout)
        self.assertIn("raw_firmware_bytes_leaked=0", proc.stdout)
        self.assertIn("slot1_writes=0", proc.stdout)


# ---------------------------------------------------------------------------
# Parameterized Test Factories (>= 180 Total Tests)
# ---------------------------------------------------------------------------


def _make_autopixelmap_silent_sound_test(
    setup_apm: str, silent_m: str, silent_tgt: str, expect_sound: bool
):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            setup_auto_pixel_mapping=setup_apm,
            silent_mode=silent_m,
            silent_target_auto_pixel_mapping=silent_tgt,
            reported_effective_auto_pixel_mapping=setup_apm,
            reported_effective_silent_target_auto_pixel_mapping=silent_tgt,
            reported_shutdown_shutter_sound_emitted=expect_sound,
            reset_action="Camera Settings Reset",
            post_auto_pixel_mapping=setup_apm,
            post_silent_target_auto_pixel_mapping="Off",
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_dormant_evf_item_test(evf_item: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            dormant_evf_item_requested=evf_item,
        )
        st = _compute_69a_from_spec(spec)
        self.assertEqual(st["dormant_evf_errno"], P377_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["monitor_errno"], P377_EOPNOTSUPP_ERRNO)
        rep = evaluate_pixelmap_monitor_recallhold_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P377_BLOCKED_MONITOR_3ITEM_OR_DORMANT_EVF_DRIFT)
    return _test


def _make_monitor_brightness_level_test(level: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            monitor_brightness_mode="Manual",
            monitor_brightness_manual_level=level,
        )
        st = _compute_69a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["monitor_errno"])
            self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
        else:
            self.assertEqual(st["monitor_errno"], P377_EINVAL_ERRNO)
            self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_monitor_flip_test(direction: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            monitor_flip_direction=direction,
            reset_action="Camera Settings Reset",
            post_monitor_flip_direction=direction,  # Resists Reset!
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_fx6_vf_brightness_test(level: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_vf_brightness=level,
        )
        st = _compute_69a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["monitor_errno"])
        else:
            self.assertEqual(st["monitor_errno"], P377_EINVAL_ERRNO)
    return _test


def _make_fx6_mirror_color_test(mirror: str, color: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            fx6_mirror_switch=mirror,
            fx6_vf_color_mode=color,
        )
        self.assertIsNone(_compute_69a_from_spec(spec)["monitor_errno"])
    return _test


def _make_recall_bit_test(bit_name: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            recall_selected_bits=(bit_name,),
        )
        st = _compute_69a_from_spec(spec)
        self.assertEqual(st["recall_bits_valid"], expect_ok)
        if expect_ok:
            self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
        else:
            self.assertEqual(st["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_recall_slot_mode_test(slot: str, domain: str, exp_mode: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            shooting_domain=domain,
            exposure_mode=exp_mode,
            hold_custom_key=slot,
        )
        st = _compute_69a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["hold_key_errno"])
            self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
        else:
            self.assertEqual(st["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_hold_focus_key_test(key: str, domain: str, focus_mode: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            shooting_domain=domain,
            focus_mode=focus_mode,
            hold_custom_key=key,
        )
        st = _compute_69a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["hold_key_errno"])
            self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
        else:
            self.assertEqual(st["hold_key_errno"], P377_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_pixelmap_monitor_recallhold_vault(spec).passed)
    return _test


def _make_hdmi_4k_rate_transition_test(prev_r: str, new_r: str, expect_reboot: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            hdmi_4k_output_rate_prev=prev_r,
            hdmi_4k_output_rate_new=new_r,
            reported_reboot_required_for_24_00p_switch=expect_reboot,
            reported_cross_24_00p_playback_isolated=(new_r == "24.00p 10bit" or expect_reboot),
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(spec).passed)
    return _test


def _make_pplut_downscale_test(pp: str, rec_media: str, raw_out: str, expect_1080: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            picture_profile=pp,
            rec_media_dur_hdmi_output=rec_media,
            raw_output_enabled=raw_out,
            output_resolution="2160p",
            reported_effective_rec_media_dur_hdmi=rec_media,
            reported_effective_output_resolution="1080p" if expect_1080 else "2160p",
            reported_output_forced_1080_downscale=expect_1080,
            reported_effective_hdmi_info_display=(
                "Off" if (rec_media == "Off(HDMI Only)" or raw_out == "On") else "On"
            ),
            reported_internal_media_write_attempted=(rec_media == "On"),
            post_rec_media_dur_hdmi=rec_media,
            post_output_resolution="2160p",
            recording_target_slot=2,
            requested_vault_slot=2,
            requested_vault_action=(
                "HDMI_ONLY_ZERO_MEDIA_WRITE" if rec_media == "Off(HDMI Only)" else "WRITE_M4ROOT_CLIP_SLOT2"
            ),
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(spec).passed)
    return _test


def _make_hdmi_4ch_audio_test(pair: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            hdmi_4ch_audio_output=pair,
            post_hdmi_4ch_audio=pair,
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(spec).passed)
    return _test


def _make_hdmi_resolution_test(res: str):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            hdmi_resolution=res,
            output_resolution=res,
            reported_effective_output_resolution=res,
            post_output_resolution=res,
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(spec).passed)
    return _test


def _make_fx6_codec_sdi_hdmi_test(codec: str, domain: str, sq_fps: int, sdi_on: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            camera_model=P377_FX6_DONOR_MODEL_NAME,
            fw_version=P377_FX6_DONOR_FW_VERSION,
            shooting_domain=domain,
            fx6_codec_mode=codec,
            fx6_sq_fps=sq_fps,
            fx6_sdi_output_on=sdi_on,
            fx6_hdmi_output_on=True,
            fx6_hdmi_tc_out="On",
            fx6_sdi_hdmi_rec_control="Off",
        )
        st = _compute_69b_from_spec(spec)
        self.assertIsNone(st["hdmi_matrix_errno"])
        self.assertEqual(st["fx6_sdi_forced_1080"], codec in ("RAW(HDMI)", "RAW(HDMI) & XAVC-I"))
        self.assertEqual(
            st["fx6_hdmi_forced_1080"],
            domain == "S&Q" and sq_fps > 60 and (sdi_on or codec in ("RAW", "RAW & XAVC-I")),
        )
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        sa = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_pixelmap_monitor_recallhold_vault(sa).passed, expect_pass)

        sb = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(sb).passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        keep = reset_action == "None"
        sa = build_default_safe_pixelmap_monitor_recallhold_vault_spec(
            setup_auto_pixel_mapping="Off",
            silent_target_auto_pixel_mapping="On",
            reported_effective_auto_pixel_mapping="Off",
            reported_effective_silent_target_auto_pixel_mapping="On",
            reported_shutdown_shutter_sound_emitted=False,
            monitor_brightness_mode="Sunny Weather",
            display_quality="High",
            monitor_flip_direction="Horizontal Flip",
            reported_effective_display_quality="High",
            reset_action=reset_action,
            post_auto_pixel_mapping=P377_FX3_AUTO_PIXEL_MAP_DEFAULT if init else "Off",
            post_silent_target_auto_pixel_mapping="On" if keep else P377_FX3_SILENT_TARGET_AUTO_PIXEL_MAP_DEFAULT,
            post_monitor_brightness_mode=P377_FX3_MONITOR_BRIGHTNESS_DEFAULT if init else "Sunny Weather",
            post_display_quality=P377_FX3_DISPLAY_QUALITY_DEFAULT if init else "High",
            post_monitor_flip_direction=P377_FX3_MONITOR_FLIP_DEFAULT if init else "Horizontal Flip",
            post_reg_custom_shoot_set_retained=(not init),
        )
        self.assertTrue(evaluate_pixelmap_monitor_recallhold_vault(sa).passed)

        sb = build_default_safe_hdmi_recctrl_24p_sdi_slot1_vault_spec(
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            output_resolution="2160p",
            time_code_output="On",
            rec_control="On",
            hdmi_4ch_audio_output="CH3/CH4",
            hdmi_info_display="Off",
            ctrl_for_hdmi="Off",
            reported_effective_output_resolution="2160p",
            reported_effective_hdmi_info_display="Off",
            reset_action=reset_action,
            post_rec_media_dur_hdmi=P377_FX3_REC_MEDIA_DUR_HDMI_DEFAULT if init else "Off(HDMI Only)",
            post_output_resolution=P377_FX3_OUTPUT_RESOLUTION_DEFAULT if init else "2160p",
            post_time_code_output=P377_FX3_HDMI_TC_OUTPUT_DEFAULT if init else "On",
            post_rec_control=P377_FX3_HDMI_REC_CONTROL_DEFAULT if init else "On",
            post_hdmi_4ch_audio=P377_FX3_HDMI_4CH_AUDIO_DEFAULT if init else "CH3/CH4",
            post_hdmi_info_display=P377_FX3_HDMI_INFO_DISPLAY_DEFAULT if init else "Off",
            post_ctrl_for_hdmi=P377_FX3_CTRL_FOR_HDMI_DEFAULT if init else "Off",
        )
        self.assertTrue(evaluate_hdmi_recctrl_24p_sdi_slot1_vault(sb).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase377_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_69_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_69_PILLAR_IDS[idx])
    return _test


def _make_fault_inject_pillar_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        pid = MASTER_69_PILLAR_IDS[idx]
        m = evaluate_realhw_69pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid,
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, 68)
        self.assertEqual(m.failed_pillars, (pid,))
    return _test


def _install_parameterized_tests() -> None:
    idx = 24

    # 1. Auto Pixel Mapping x Silent Mode x Silent Target matrix (8 tests)
    for setup_apm in ("On", "Off"):
        for sil_m in ("On", "Off"):
            for sil_t in ("On", "Off"):
                expect_snd = setup_apm == "On" and not (sil_m == "On" and sil_t == "On")
                setattr(
                    Phase377Pillar69VerifierTests,
                    f"test_{idx:03d}_autopixelmap_{setup_apm.lower()}_sil_{sil_m.lower()}_tgt_{sil_t.lower()}",
                    _make_autopixelmap_silent_sound_test(setup_apm, sil_m, sil_t, expect_snd),
                )
                idx += 1

    # 2. All 4 dormant EVF items strictly blocked EOPNOTSUPP=95 (4 tests)
    for evf_item in P377_FX3_DORMANT_EVF_ITEMS:
        clean = evf_item.lower().replace("/", "_").replace(".", "").replace(" ", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_dormant_evf_reject_{clean}",
            _make_dormant_evf_item_test(evf_item),
        )
        idx += 1

    # 3. Monitor Brightness manual levels -3..+3 (7 tests)
    for lvl in range(-3, 4):
        tag = f"m{abs(lvl)}" if lvl < 0 else f"p{lvl}"
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_monitor_brightness_manual_{tag}",
            _make_monitor_brightness_level_test(lvl, -2 <= lvl <= 2),
        )
        idx += 1

    # 4. Monitor Flip Direction all 4 active modes (4 tests)
    for flip in P377_FX3_MONITOR_FLIP_DIRECTIONS:
        clean = flip.lower().replace(" ", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_monitor_flip_{clean}",
            _make_monitor_flip_test(flip),
        )
        idx += 1

    # 5. FX6 VF Brightness 0..16 (17 tests)
    for lvl in range(0, 17):
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_fx6_vf_brightness_{lvl:02d}",
            _make_fx6_vf_brightness_test(lvl, 1 <= lvl <= 15),
        )
        idx += 1

    # 6. FX6 MIRROR switch x Color Mode matrix (6 tests)
    for mir in P377_FX6_MIRROR_SWITCH_POSITIONS:
        for col in P377_FX6_VF_COLOR_MODES:
            clean_m = mir.lower().replace("-", "_")
            clean_c = col.lower().replace("&", "_")
            setattr(
                Phase377Pillar69VerifierTests,
                f"test_{idx:03d}_fx6_mirror_{clean_m}_color_{clean_c}",
                _make_fx6_mirror_color_test(mir, col),
            )
            idx += 1

    # 7. All 11 valid Recall Custom hold bits + 3 invalid bits (incl. white_balance) (14 tests)
    for bit in P377_FX3_RECALL_CUSTOM_HOLD_11_BITS:
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_recall_hold_valid_bit_{bit}",
            _make_recall_bit_test(bit, True),
        )
        idx += 1
    for bad_bit in ("white_balance", "creative_look", "picture_profile"):
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_recall_hold_reject_bit_{bad_bit}",
            _make_recall_bit_test(bad_bit, False),
        )
        idx += 1

    # 8. Recall Custom hold 1..3 across Still P/A/S/M vs Movie/S&Q/iAuto/Flexible Exp. (24 tests)
    mode_cases = (
        ("Still", "P", True),
        ("Still", "A", True),
        ("Still", "S", True),
        ("Still", "M", True),
        ("Still", "iAuto", False),
        ("Still", "Flexible Exp.", False),
        ("Movie", "M", False),
        ("S&Q", "M", False),
    )
    for slot in P377_FX3_RECALL_CUSTOM_HOLD_SLOTS:
        slot_tag = slot.lower().replace(" ", "_")
        for dom, exp_m, eok in mode_cases:
            exp_tag = exp_m.lower().replace(" ", "_").replace(".", "")
            dom_tag = dom.lower().replace("&", "_")
            setattr(
                Phase377Pillar69VerifierTests,
                f"test_{idx:03d}_{slot_tag}_{dom_tag}_{exp_tag}",
                _make_recall_slot_mode_test(slot, dom, exp_m, eok),
            )
            idx += 1

    # 9. Hold Focus Custom Keys (AF On, Eye AF, Tracking On/Toggle/+AF On) matrix (12 tests)
    focus_key_cases = (
        ("AF On", "Still", "AF-S", True),
        ("AF On", "Movie", "MF", True),
        ("AF On", "S&Q", "AF-C", True),
        ("Eye AF", "Still", "AF-C", True),
        ("Eye AF", "Movie", "AF-C", True),
        ("Eye AF", "S&Q", "AF-C", False),
        ("Tracking On", "Still", "AF-C", True),
        ("Tracking On", "Still", "AF-S", False),
        ("Tracking On", "Movie", "AF-C", False),
        ("Tracking on Toggle", "Still", "AF-C", True),
        ("Tracking On + AF On", "Still", "AF-C", True),
        ("Tracking On + AF On", "S&Q", "AF-C", False),
    )
    for key, dom, fm, eok in focus_key_cases:
        clean_k = key.lower().replace(" ", "_").replace("+", "plus")
        clean_d = dom.lower().replace("&", "_")
        clean_f = fm.lower().replace("-", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_holdkey_{clean_k}_{clean_d}_{clean_f}",
            _make_hold_focus_key_test(key, dom, fm, eok),
        )
        idx += 1

    # 10. 4K Output Set.(HDMI Only) 24.00p reboot matrix (12 tests)
    for rate in P377_FX3_4K_OUTPUT_HDMI_ONLY_RATES:
        r_tag = rate.lower().replace(" ", "_").replace(".", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_4k_hdmi_to_24_00p_from_{r_tag}",
            _make_hdmi_4k_rate_transition_test(rate, "24.00p 10bit", rate != "24.00p 10bit"),
        )
        idx += 1
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_4k_hdmi_from_24_00p_to_{r_tag}",
            _make_hdmi_4k_rate_transition_test("24.00p 10bit", rate, rate != "24.00p 10bit"),
        )
        idx += 1

    # 11. PPLUT1..4 + Rec. Media On/Off + RAW On/Off 1080 downscale matrix (12 tests)
    for pp in P377_FX3_PPLUT_SLOTS:
        for rec_m, raw_o, exp_1080 in (
            ("On", "Off", True),
            ("Off(HDMI Only)", "Off", False),
            ("On", "On", False),
        ):
            rm_tag = "on" if rec_m == "On" else "hdmi_only"
            setattr(
                Phase377Pillar69VerifierTests,
                f"test_{idx:03d}_{pp.lower()}_rec_{rm_tag}_raw_{raw_o.lower()}",
                _make_pplut_downscale_test(pp, rec_m, raw_o, exp_1080),
            )
            idx += 1

    # 12. HDMI 4ch Audio & Resolution options (6 tests)
    for pair in P377_FX3_HDMI_4CH_AUDIO_MODES:
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_hdmi_audio_{pair.lower().replace('/', '_')}",
            _make_hdmi_4ch_audio_test(pair),
        )
        idx += 1
    for res in P377_FX3_HDMI_RESOLUTION_MODES:
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_hdmi_res_{res.lower()}",
            _make_hdmi_resolution_test(res),
        )
        idx += 1

    # 13. FX6 Dual-Output SDI + HDMI Matrix (12 tests)
    for codec in P377_FX6_CODEC_MODES:
        c_tag = codec.lower().replace(" ", "_").replace("&", "and").replace("(", "_").replace(")", "").replace("-", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_fx6_movie_{c_tag}",
            _make_fx6_codec_sdi_hdmi_test(codec, "Movie", 24, True),
        )
        idx += 1
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_fx6_sq120_{c_tag}",
            _make_fx6_codec_sdi_hdmi_test(codec, "S&Q", 120, True),
        )
        idx += 1

    # 14. Slot-1 Tier-0 EROFS=30 Write Firewall actions x errnos (4 actions x 3 errnos = 12 tests)
    for action in sorted(P377_WRITE_MUTATING_SLOT1_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP", "EBUSY"):
            setattr(
                Phase377Pillar69VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 15. Reset Action Matrices (3 tests)
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 16. Individual Donor Checks (17 Wave-67 donors)
    for d_i in range(17):
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # 17. Key & final pillars across MASTER_69_PILLAR_IDS (16 tests)
    for p_i in (*range(0, 65, 5), 66, 67, 68):
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1

    # 18. Fault injection across 5 key pillars incl. 67, 68 & 69 (5 tests)
    for p_i in (0, 21, 66, 67, 68):
        setattr(
            Phase377Pillar69VerifierTests,
            f"test_{idx:03d}_fault_inject_pillar_{p_i+1:02d}",
            _make_fault_inject_pillar_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
