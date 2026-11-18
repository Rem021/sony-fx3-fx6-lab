"""Phase 336 (Pillar 60 & 60/60 Milestone) unit tests:
Wave-58 Bright Monitoring Ver.7.00+ Focus-Mag Coexistence & Monitor Brightness Manual/Sunny-Weather /
Mechanical-Only BULB & DRO vs Dormant Bulb Timer & Auto HDR / Shot Mark 1-2 & Clip Flag OK-NG-KEEP vs
Dormant Divide-Extract / Zero-BT Timecode Link vs VMC-BNCM1 EXT-LK, WPA3-SAE & USB-LAN Airplane-Mode
Isolation / Slot-1 M4ROOT-AVF_INFO-DCIM EROFS=30 Vault Firewall.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
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
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MASTER_60_PILLAR_COUNT,
    MASTER_60_PILLAR_IDS,
    MASTER_60_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P336_AIRPLANE_MODE_FORCED_ON,
    P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT,
    P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT,
    P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF,
    P336_BLOCKED_INVALID_PILLAR60A_SPEC,
    P336_BLOCKED_INVALID_PILLAR60B_SPEC,
    P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P336_BLOCKED_SAFETY_POLICY_VIOLATION,
    P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT,
    P336_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT,
    P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
    P336_BRIGHT_MONITORING_F_RESID16,
    P336_BRIGHT_MONITORING_SYMBOLS,
    P336_BT_MAX_CONCURRENT,
    P336_BT_MAX_PAIRED,
    P336_BULB_DISALLOWED_DRIVE_MODES,
    P336_BULB_FALLBACK_SHUTTER,
    P336_CAUTION_BULB_ON_MSG,
    P336_CLIP_FLAG_OPTIONS,
    P336_CONCURRENT_CEILING_SECONDS,
    P336_DORMANT_AUTO_HDR_BASE_RESID16,
    P336_DORMANT_BULB_AND_HDR_SYMBOLS,
    P336_DORMANT_BULB_TIMER_F_RESID16,
    P336_DORMANT_BULB_TIMER_SYMBOL_COUNT,
    P336_DORMANT_CLIP_EDIT_SYMBOLS,
    P336_DORMANT_CUT_15S_F_RESID16,
    P336_DORMANT_LCD_BRIGHTNESS_MODES,
    P336_DRO_BRACKET_OPTIONS,
    P336_DRO_DEFAULT,
    P336_DRO_MODES,
    P336_EINVAL_ERRNO,
    P336_EOPNOTSUPP_ERRNO,
    P336_EROFS_ERRNO,
    P336_FAST_CLI_BUDGET_SECONDS,
    P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT,
    P336_FX3_FOCUS_MAG_BRIGHT_MON_MIN_FW,
    P336_FX3_FW_VERSION,
    P336_FX3_MODEL_NAME,
    P336_FX3_PLAYBACK_EDIT_ITEMS,
    P336_FX6_AE_BACKLIGHT_SYMBOL,
    P336_FX6_DONOR_FW_VERSION,
    P336_FX6_DONOR_MODEL_NAME,
    P336_FX6_DORMANT_BACKLIGHT_SYMBOLS,
    P336_FX6_DORMANT_SHOT_MARK_SYMBOLS,
    P336_FX6_VF_BRIGHTNESS_DEFAULT,
    P336_FX6_VF_BRIGHTNESS_MAX,
    P336_FX6_VF_BRIGHTNESS_MIN,
    P336_FX6_VF_COLOR_MODES,
    P336_IMAGE_JUMP_OPTIONS,
    P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL,
    P336_MONITOR_BRIGHTNESS_DEFAULT_MODE,
    P336_MONITOR_BRIGHTNESS_MAX_LEVEL,
    P336_MONITOR_BRIGHTNESS_MENU_PATH,
    P336_MONITOR_BRIGHTNESS_MIN_LEVEL,
    P336_MONITOR_BRIGHTNESS_MODES,
    P336_NOMINAL_BUDGET_SECONDS,
    P336_PHOTO_CAPTURE_FILE_TYPES,
    P336_PILLAR_60A_SCENARIO_IDS,
    P336_PILLAR_60B_SCENARIO_IDS,
    P336_RF_PACKETS_TRANSMITTED,
    P336_SAFE_WIRED_TRANSPORT,
    P336_SHOT_MARK_TRANSFER_FILTERS,
    P336_SHUTTER_TYPES,
    P336_SLOT1_DATA_SECTOR_WRITES,
    P336_SLOT1_FORMAT_HARD_LOCKED,
    P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P336_STATUS_VERIFIED_60OF60_AGGREGATOR,
    P336_STATUS_VERIFIED_PILLAR60_SUITE,
    P336_STATUS_VERIFIED_PILLAR_60A,
    P336_STATUS_VERIFIED_PILLAR_60B,
    P336_SUNNY_WEATHER_F_RESID16,
    P336_TIER0_SURFACE_COUNT,
    P336_TIMECODE_LINK_BT_SYMBOLS,
    P336_USB_LAN_KERNEL_MODULES,
    P336_USB_LAN_SERVICE_LIBS,
    P336_VMC_BNCM1_ADAPTER_MODEL,
    P336_VMC_BNCM1_PART_NUMBER,
    P336_WIFI_COUNTRY_CODE_ENTRIES,
    P336_WIFI_REGULATORY_DFS_RULES,
    P336_WIFI_REGULATORY_REGION_COUNT,
    P336_WIFI_SECURITY_ACTIVE_MODES,
    P336_WIFI_SECURITY_REMOVED_MODES,
    P336_WIFI_SKUS,
    P336_WIFI_SKU_BANDS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PHASE336_MASTER_SCHEMA,
    PHASE336_PHASE_NUMBER,
    PHASE336_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_bright_mon_bulb_vault_spec,
    build_default_safe_shotmark_usblan_vault_spec,
    compute_expected_bright_mon_bulb_state,
    compute_expected_shotmark_tc_usblan_vault_state,
    evaluate_60pillar_recovery_master,
    evaluate_bright_mon_bulb_vault,
    evaluate_realhw_60pillar_recovery_master,
    evaluate_shotmark_tc_usblan_vault,
    inspect_phase336_donors_readonly,
    run_pillar60_standalone_suite,
    run_pillar60a_bright_mon_bulb_vault_6_scenario_suite,
    run_pillar60b_shotmark_tc_usblan_vault_6_scenario_suite,
    verify_60pillar_recovery_suite,
    verify_bright_mon_shotmark_usblan_bulb_and_vault,
    verify_bright_mon_shotmark_usblan_bulb_vault,
)
from fx3_recovery import (  # noqa: E402
    realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier as p60_mod,
)


class Phase336Pillar60VerifierTests(unittest.TestCase):
    """Comprehensive unit tests for Phase 336 Pillar 60 & 60/60 Milestone."""

    # ------------------------------------------------------------------
    # Safety Redlines, Metadata & Wave-58 Empirical Constants (01..10)
    # ------------------------------------------------------------------

    def test_01_safety_policy_flags_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P336_RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(P336_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertTrue(P336_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P336_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P336_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)

    def test_02_schema_and_60_pillar_metadata(self) -> None:
        self.assertEqual(PHASE336_PHASE_NUMBER, 336)
        self.assertEqual(
            PHASE336_SCHEMA,
            "realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier_v1",
        )
        self.assertEqual(PHASE336_MASTER_SCHEMA, "realhw_60pillar_recovery_master_v1")
        self.assertEqual(MASTER_60_PILLAR_COUNT, 60)
        self.assertEqual(len(MASTER_60_PILLAR_IDS), 60)
        self.assertEqual(len(MASTER_60_PILLAR_SPECS), 60)
        self.assertEqual(
            MASTER_60_PILLAR_IDS[-1],
            "pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault",
        )

    def test_03_bright_monitoring_and_monitor_brightness_constants(self) -> None:
        self.assertEqual(P336_FX3_BRIGHT_MONITORING_SYMBOL_COUNT, 6)
        self.assertEqual(len(P336_BRIGHT_MONITORING_SYMBOLS), 6)
        self.assertIn("FUNC_custom_bright_monitoring", P336_BRIGHT_MONITORING_SYMBOLS)
        self.assertEqual(P336_BRIGHT_MONITORING_F_RESID16, 0x701F)
        self.assertEqual(P336_FX3_FOCUS_MAG_BRIGHT_MON_MIN_FW, ("7.02", "7.01", "7.00"))
        self.assertEqual(P336_MONITOR_BRIGHTNESS_MENU_PATH, ("Setup", "Monitor", "Monitor Brightness"))
        self.assertEqual(P336_MONITOR_BRIGHTNESS_MODES, ("Manual", "Sunny Weather"))
        self.assertEqual(
            P336_DORMANT_LCD_BRIGHTNESS_MODES,
            ("LCD_BRIGHTNESS_AUTO", "LCD_BRIGHTNESS_BRIGHT", "LCD_BRIGHTNESS_NORMAL"),
        )
        self.assertEqual(P336_MONITOR_BRIGHTNESS_MIN_LEVEL, -2)
        self.assertEqual(P336_MONITOR_BRIGHTNESS_MAX_LEVEL, 2)
        self.assertEqual(P336_MONITOR_BRIGHTNESS_DEFAULT_LEVEL, 0)
        self.assertEqual(P336_MONITOR_BRIGHTNESS_DEFAULT_MODE, "Manual")
        self.assertEqual(P336_SUNNY_WEATHER_F_RESID16, 0x7A61)

    def test_04_bulb_dro_and_dormant_bulb_timer_hdr_constants(self) -> None:
        self.assertEqual(P336_SHUTTER_TYPES, ("Mechanical Shutter", "Electronic Shutter"))
        self.assertEqual(P336_BULB_FALLBACK_SHUTTER, '30"')
        self.assertEqual(P336_CAUTION_BULB_ON_MSG, "CAUTION_ID_FACTOR_CAM_SET_BULB_ON_MSG")
        self.assertEqual(len(P336_BULB_DISALLOWED_DRIVE_MODES), 4)
        self.assertEqual(P336_DRO_MODES, ("Auto", "Off", "Lv1", "Lv2", "Lv3", "Lv4", "Lv5"))
        self.assertEqual(P336_DRO_DEFAULT, "Auto")
        self.assertEqual(P336_DRO_BRACKET_OPTIONS, ("Off", "DRO Bracket: Lo", "DRO Bracket: Hi"))
        self.assertEqual(P336_DORMANT_BULB_TIMER_F_RESID16, 0x630F)
        self.assertEqual(P336_DORMANT_AUTO_HDR_BASE_RESID16, 0xE49D)
        self.assertEqual(P336_DORMANT_BULB_TIMER_SYMBOL_COUNT, 13)
        self.assertEqual(len(P336_DORMANT_BULB_AND_HDR_SYMBOLS), 7)

    def test_05_fx6_vf_setting_and_ae_backlight_constants(self) -> None:
        self.assertEqual(P336_FX6_VF_BRIGHTNESS_MIN, 1)
        self.assertEqual(P336_FX6_VF_BRIGHTNESS_MAX, 15)
        self.assertEqual(P336_FX6_VF_BRIGHTNESS_DEFAULT, 8)
        self.assertEqual(P336_FX6_VF_COLOR_MODES, ("Color", "B&W"))
        self.assertEqual(
            P336_FX6_AE_BACKLIGHT_SYMBOL,
            "VAL_setting_auto_exposure_mode_MODE_BACKLIGHT",
        )
        self.assertEqual(len(P336_FX6_DORMANT_BACKLIGHT_SYMBOLS), 4)
        self.assertEqual(len(P336_FX6_DORMANT_SHOT_MARK_SYMBOLS), 4)

    def test_06_shotmark_clipflag_edit_and_dormant_divide_constants(self) -> None:
        self.assertEqual(P336_CLIP_FLAG_OPTIONS, ("Off", "OK", "NG", "KEEP"))
        self.assertEqual(len(P336_IMAGE_JUMP_OPTIONS), 6)
        self.assertEqual(
            P336_FX3_PLAYBACK_EDIT_ITEMS,
            ("Photo Capture", "JPEG/HEIF Switch", "Copy", "Rotate"),
        )
        self.assertEqual(P336_PHOTO_CAPTURE_FILE_TYPES, ("JPEG", "HEIF_420", "HEIF_422"))
        self.assertEqual(P336_SHOT_MARK_TRANSFER_FILTERS, ("All", "Only Shot Mark", "Only Shot Mark Mov."))
        self.assertEqual(P336_DORMANT_CUT_15S_F_RESID16, 0x7005)
        self.assertEqual(len(P336_DORMANT_CLIP_EDIT_SYMBOLS), 8)

    def test_07_timecode_link_wifi_and_usblan_constants(self) -> None:
        self.assertEqual(len(P336_TIMECODE_LINK_BT_SYMBOLS), 4)
        self.assertEqual(P336_BT_MAX_PAIRED, 15)
        self.assertEqual(P336_BT_MAX_CONCURRENT, 2)
        self.assertEqual(P336_VMC_BNCM1_ADAPTER_MODEL, "VMC-BNCM1")
        self.assertEqual(P336_VMC_BNCM1_PART_NUMBER, "A-5051-506-A")
        self.assertEqual(P336_WIFI_SKUS, ("WW728473", "WW558244"))
        self.assertEqual(P336_WIFI_SKU_BANDS["WW728473"], ("2.4GHz", "5GHz"))
        self.assertEqual(P336_WIFI_SKU_BANDS["WW558244"], ("2.4GHz",))
        self.assertEqual(P336_WIFI_SECURITY_ACTIVE_MODES, ("WPA2-PSK", "WPA3-SAE"))
        self.assertEqual(P336_WIFI_SECURITY_REMOVED_MODES, ("WEP", "WPA-PSK", "Security(IPsec)"))
        self.assertEqual(P336_WIFI_COUNTRY_CODE_ENTRIES, 29)
        self.assertEqual(P336_WIFI_REGULATORY_REGION_COUNT, 21)
        self.assertEqual(P336_WIFI_REGULATORY_DFS_RULES, 59)
        self.assertEqual(len(P336_USB_LAN_KERNEL_MODULES), 8)
        self.assertIn("cdc_ncm.ko", P336_USB_LAN_KERNEL_MODULES)
        self.assertIn("r8152.ko", P336_USB_LAN_KERNEL_MODULES)
        self.assertEqual(P336_USB_LAN_SERVICE_LIBS, ("libWiredLanResource.so", "libNetServiceEther.so"))
        self.assertEqual(P336_SAFE_WIRED_TRANSPORT, "USB-LAN (CDC-NCM)")

    def test_08_errno_budget_and_scenario_id_constants(self) -> None:
        self.assertEqual(P336_EINVAL_ERRNO, 22)
        self.assertEqual(P336_EROFS_ERRNO, 30)
        self.assertEqual(P336_EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(len(P336_PILLAR_60A_SCENARIO_IDS), 6)
        self.assertEqual(len(P336_PILLAR_60B_SCENARIO_IDS), 6)
        self.assertEqual(P336_TIER0_SURFACE_COUNT, 16)
        self.assertEqual(P336_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P336_NOMINAL_BUDGET_SECONDS, 4.00)
        self.assertEqual(P336_CONCURRENT_CEILING_SECONDS, 6.00)

    def test_09_status_string_constants(self) -> None:
        self.assertEqual(
            P336_STATUS_VERIFIED_PILLAR_60A,
            "VERIFIED_PILLAR_60A_BRIGHT_MON_MONITOR_BRIGHTNESS_BULB_VAULT",
        )
        self.assertEqual(
            P336_STATUS_VERIFIED_PILLAR_60B,
            "VERIFIED_PILLAR_60B_SHOTMARK_EDIT_TCLINK_WPA3_USBLAN_VAULT",
        )
        self.assertEqual(
            P336_STATUS_VERIFIED_PILLAR60_SUITE,
            "VERIFIED_PILLAR60_BRIGHT_MON_SHOTMARK_USBLAN_BULB_VAULT",
        )
        self.assertEqual(P336_STATUS_VERIFIED_60OF60_AGGREGATOR, "VERIFIED_60OF60_PILLAR_RECOVERY_MASTER")

    def test_10_default_spec_builders_are_valid(self) -> None:
        s60a = build_default_safe_bright_mon_bulb_vault_spec()
        s60b = build_default_safe_shotmark_usblan_vault_spec()
        self.assertEqual(s60a.camera_model, P336_FX3_MODEL_NAME)
        self.assertEqual(s60b.camera_model, P336_FX3_MODEL_NAME)
        self.assertEqual(s60b.airplane_mode, "On")
        self.assertEqual(s60b.network_transport, P336_SAFE_WIRED_TRANSPORT)

    # ------------------------------------------------------------------
    # Donor Inspection & 4-Mode Clean-Room Tests (11..18)
    # ------------------------------------------------------------------

    def test_11_donor_inspection_normal_mode(self) -> None:
        snap = inspect_phase336_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(all(a.present and a.matches_pinned for a in snap.artifacts))

    def test_12_donor_inspection_force_clean_room_true(self) -> None:
        snap = inspect_phase336_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))
        self.assertTrue(snap.all_donors_present)

    def test_13_donor_inspection_env_clean_room_test(self) -> None:
        with patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            snap = inspect_phase336_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)

    def test_14_donor_inspection_env_force_clean_room(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase336_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)

    def test_15_donorless_work_root_none_and_nonexistent_guard_no_typeerror(self) -> None:
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            self.assertIsNone(p60_mod._resolve_phase336_donor_path("work/missing.bin", work_roots=(None,)))
            self.assertIsNone(
                p60_mod._resolve_phase336_donor_path("work/missing.bin", work_roots=(Path("/nonexistent-donor-root"),))
            )
            for roots in ((None,), (Path("/nonexistent-donor-root"),)):
                with patch.object(files_mod, "iter_donor_work_roots", return_value=roots):
                    self.assertFalse(p60_mod._master60_local_donors_available())
                    snap = inspect_phase336_donors_readonly(force_clean_room=False)
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(snap.donor_files_inspected, 17)
                self.assertTrue(snap.all_donors_present)

    def test_16_donor_inspection_contains_14_fx3_and_3_fx6_artifacts(self) -> None:
        snap = inspect_phase336_donors_readonly(force_clean_room=True)
        fx3_count = sum(1 for a in snap.artifacts if a.artifact_id.startswith("fx3_"))
        fx6_count = sum(1 for a in snap.artifacts if a.artifact_id.startswith("fx6_"))
        self.assertEqual(fx3_count, 14)
        self.assertEqual(fx6_count, 3)

    def test_17_donor_snapshot_to_dict_serializable(self) -> None:
        snap = inspect_phase336_donors_readonly(force_clean_room=True)
        d = snap.to_dict()
        payload = json.dumps(d)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", payload)
        self.assertEqual(d["donor_files_inspected"], 17)

    def test_18_master60_local_donors_available_ignores_none_roots(self) -> None:
        from fx3_recovery import files as files_mod

        with patch.object(files_mod, "iter_donor_work_roots", return_value=(None, None)):
            self.assertFalse(p60_mod._master60_local_donors_available())

    # ------------------------------------------------------------------
    # Pillar 60A State Helper Tests (19..35)
    # ------------------------------------------------------------------

    def _default_60a_state(self, **overrides: object) -> dict:
        kw = dict(
            camera_model=P336_FX3_MODEL_NAME,
            fw_version=P336_FX3_FW_VERSION,
            shooting_domain="Still",
            exposure_mode="M",
            focus_mode="MF",
            power_state="On",
            bright_monitoring_requested=False,
            focus_magnifier_active=False,
            requested_bright_mon_multi_gain_ext=False,
            monitor_brightness_mode="Manual",
            monitor_brightness_level=0,
            shutter_type="Mechanical Shutter",
            still_drive_mode="Single Shooting",
            bulb_requested=False,
            picture_profile="Off",
            hlg_still_image="Off",
            dro_mode="Auto",
            dro_bracket="Off",
            requested_dormant_bulb_or_hdr_symbols=(),
            reset_action="None",
        )
        kw.update(overrides)
        return compute_expected_bright_mon_bulb_state(**kw)

    def test_19_state_60a_bright_mon_active_forces_setting_effect_off_and_coexists_v702_focus_mag(self) -> None:
        st = self._default_60a_state(
            fw_version="7.02",
            bright_monitoring_requested=True,
            focus_magnifier_active=True,
        )
        self.assertTrue(st["supports_bm_focus_mag"])
        self.assertTrue(st["effective_bright_monitoring"])
        self.assertEqual(st["forced_live_view_display"], "Setting Effect OFF")
        self.assertIsNone(st["bright_monitoring_errno"])

    def test_20_state_60a_bright_mon_coexists_v700_focus_mag_but_conflicts_pre_v700(self) -> None:
        st_700 = self._default_60a_state(
            fw_version="7.00", bright_monitoring_requested=True, focus_magnifier_active=True
        )
        self.assertTrue(st_700["effective_bright_monitoring"])
        st_602 = self._default_60a_state(
            fw_version="6.02", bright_monitoring_requested=True, focus_magnifier_active=True
        )
        self.assertFalse(st_602["supports_bm_focus_mag"])
        self.assertFalse(st_602["effective_bright_monitoring"])
        self.assertEqual(st_602["bright_monitoring_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_21_state_60a_bright_mon_auto_cancels_on_power_off(self) -> None:
        st = self._default_60a_state(bright_monitoring_requested=True, power_state="Off")
        self.assertTrue(st["bm_auto_cancelled"])
        self.assertFalse(st["effective_bright_monitoring"])
        self.assertEqual(st["bright_monitoring_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_22_state_60a_bright_mon_auto_cancels_outside_pasm(self) -> None:
        st = self._default_60a_state(bright_monitoring_requested=True, exposure_mode="Intelligent Auto")
        self.assertTrue(st["bm_auto_cancelled"])
        self.assertFalse(st["effective_bright_monitoring"])
        self.assertEqual(st["bright_monitoring_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_23_state_60a_bright_mon_auto_cancels_outside_mf(self) -> None:
        for fm in ("AF-S", "AF-C", "DMF"):
            st = self._default_60a_state(bright_monitoring_requested=True, focus_mode=fm)
            self.assertTrue(st["bm_auto_cancelled"])
            self.assertFalse(st["effective_bright_monitoring"])

    def test_24_state_60a_bright_mon_multi_gain_extension_rejected_eopnotsupp(self) -> None:
        st = self._default_60a_state(
            bright_monitoring_requested=True,
            requested_bright_mon_multi_gain_ext=True,
        )
        self.assertFalse(st["effective_bright_monitoring"])
        self.assertEqual(st["bright_monitoring_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_25_state_60a_monitor_brightness_manual_and_sunny_weather_vs_dormant_auto(self) -> None:
        st_man = self._default_60a_state(monitor_brightness_mode="Manual", monitor_brightness_level=2)
        self.assertIsNone(st_man["monitor_brightness_errno"])
        st_sun = self._default_60a_state(monitor_brightness_mode="Sunny Weather", monitor_brightness_level=0)
        self.assertIsNone(st_sun["monitor_brightness_errno"])
        st_bad_lvl = self._default_60a_state(monitor_brightness_mode="Manual", monitor_brightness_level=3)
        self.assertEqual(st_bad_lvl["monitor_brightness_errno"], P336_EINVAL_ERRNO)
        st_auto = self._default_60a_state(monitor_brightness_mode="Auto")
        self.assertEqual(st_auto["monitor_brightness_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_26_state_60a_monitor_brightness_initialize_only_vs_camera_reset(self) -> None:
        st_cam = self._default_60a_state(
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_level=2,
            dro_mode="Lv5",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st_cam["post_monitor_brightness_mode"], "Sunny Weather")
        self.assertEqual(st_cam["post_monitor_brightness_level"], 2)
        self.assertEqual(st_cam["post_dro_mode"], "Auto")

        st_init = self._default_60a_state(
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_level=2,
            reset_action="Initialize",
        )
        self.assertEqual(st_init["post_monitor_brightness_mode"], "Manual")
        self.assertEqual(st_init["post_monitor_brightness_level"], 0)

    def test_27_state_60a_bulb_requires_mechanical_shutter_and_disables_antiflicker(self) -> None:
        st = self._default_60a_state(bulb_requested=True, shutter_type="Mechanical Shutter")
        self.assertTrue(st["effective_bulb_active"])
        self.assertEqual(st["effective_bulb_fallback_shutter"], "BULB")
        self.assertTrue(st["anti_flicker_disabled_by_bulb"])
        self.assertIsNone(st["bulb_errno"])

    def test_28_state_60a_bulb_falls_back_to_30s_under_electronic_shutter(self) -> None:
        st = self._default_60a_state(bulb_requested=True, shutter_type="Electronic Shutter")
        self.assertTrue(st["bulb_blocked"])
        self.assertFalse(st["effective_bulb_active"])
        self.assertEqual(st["effective_bulb_fallback_shutter"], '30"')
        self.assertEqual(st["bulb_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_29_state_60a_bulb_falls_back_to_30s_under_cont_bracket_interval(self) -> None:
        for drv in P336_BULB_DISALLOWED_DRIVE_MODES:
            st = self._default_60a_state(bulb_requested=True, still_drive_mode=drv)
            self.assertTrue(st["bulb_blocked"], drv)
            self.assertFalse(st["effective_bulb_active"], drv)
            self.assertEqual(st["effective_bulb_fallback_shutter"], '30"')
            self.assertEqual(st["bulb_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_30_state_60a_bulb_blocked_in_movie_or_non_m_mode(self) -> None:
        st_mov = self._default_60a_state(shooting_domain="Movie", bulb_requested=True)
        self.assertFalse(st_mov["effective_bulb_active"])
        self.assertEqual(st_mov["effective_bulb_fallback_shutter"], '30"')
        st_a = self._default_60a_state(exposure_mode="A", bulb_requested=True)
        self.assertFalse(st_a["effective_bulb_active"])
        self.assertEqual(st_a["effective_bulb_fallback_shutter"], '30"')

    def test_31_state_60a_dro_locked_off_when_pp_active_or_hlg_still_on(self) -> None:
        st_pp = self._default_60a_state(picture_profile="PP8", dro_mode="Lv3", dro_bracket="DRO Bracket: Lo")
        self.assertTrue(st_pp["dro_locked_off"])
        self.assertEqual(st_pp["effective_dro_mode"], "Off")
        self.assertFalse(st_pp["dro_bracket_allowed"])
        self.assertEqual(st_pp["dro_errno"], P336_EOPNOTSUPP_ERRNO)

        st_hlg = self._default_60a_state(hlg_still_image="On", dro_mode="Auto")
        self.assertTrue(st_hlg["dro_locked_off"])
        self.assertEqual(st_hlg["effective_dro_mode"], "Off")

    def test_32_state_60a_dro_bracket_allowed_when_pp_off_and_hlg_off(self) -> None:
        st = self._default_60a_state(dro_mode="Lv2", dro_bracket="DRO Bracket: Hi")
        self.assertFalse(st["dro_locked_off"])
        self.assertEqual(st["effective_dro_mode"], "Lv2")
        self.assertIsNone(st["dro_errno"])

    def test_33_state_60a_dormant_bulb_timer_and_auto_hdr_fail_closed(self) -> None:
        st = self._default_60a_state(
            requested_dormant_bulb_or_hdr_symbols=("Bulb Timer", "Auto HDR", "Exposure Time")
        )
        self.assertEqual(st["dormant_bulb_hdr_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_34_state_60a_fx6_model_disallows_fx3_bright_mon_bulb_dro(self) -> None:
        st = self._default_60a_state(
            camera_model=P336_FX6_DONOR_MODEL_NAME,
            bright_monitoring_requested=True,
            bulb_requested=True,
        )
        self.assertFalse(st["effective_bright_monitoring"])
        self.assertFalse(st["effective_bulb_active"])
        self.assertEqual(st["effective_dro_mode"], "Off")

    def test_35_state_60a_all_monitor_brightness_levels_valid(self) -> None:
        for lvl in (-2, -1, 0, 1, 2):
            st = self._default_60a_state(monitor_brightness_mode="Manual", monitor_brightness_level=lvl)
            self.assertIsNone(st["monitor_brightness_errno"])

    # ------------------------------------------------------------------
    # Pillar 60A Evaluator Tests (36..52)
    # ------------------------------------------------------------------

    def test_36_eval_60a_default_safe_spec_passes(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(build_default_safe_bright_mon_bulb_vault_spec())
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P336_STATUS_VERIFIED_PILLAR_60A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_37_eval_60a_bright_mon_v702_with_focus_mag_passes(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                fw_version="7.02",
                bright_monitoring_requested=True,
                focus_magnifier_active=True,
                reported_effective_bright_monitoring=True,
                reported_forced_live_view_display="Setting Effect OFF",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_38_eval_60a_sunny_weather_and_manual_levels_pass(self) -> None:
        for mode in P336_MONITOR_BRIGHTNESS_MODES:
            rep = evaluate_bright_mon_bulb_vault(
                build_default_safe_bright_mon_bulb_vault_spec(
                    monitor_brightness_mode=mode,
                    monitor_brightness_level=1 if mode == "Manual" else 0,
                    post_monitor_brightness_mode=mode,
                    post_monitor_brightness_level=1 if mode == "Manual" else 0,
                )
            )
            self.assertTrue(rep.passed, rep.errors)

    def test_39_eval_60a_mechanical_bulb_and_dro_pass(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                bulb_requested=True,
                shutter_type="Mechanical Shutter",
                still_drive_mode="Single Shooting",
                reported_effective_bulb_active=True,
                reported_bulb_fallback_shutter="BULB",
                reported_anti_flicker_disabled_by_bulb=True,
                post_bulb_active=True,
                dro_mode="Lv3",
                reported_effective_dro_mode="Lv3",
                post_dro_mode="Lv3",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_40_eval_60a_fx6_vf_brightness_and_ae_backlight_disambig_passes(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                camera_model=P336_FX6_DONOR_MODEL_NAME,
                fw_version=P336_FX6_DONOR_FW_VERSION,
                fx6_vf_brightness=12,
                fx6_vf_color_mode="B&W",
                reported_effective_dro_mode="Off",
                post_dro_mode="Off",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_41_eval_60a_rejects_invalid_camera_model(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(camera_model="ILCE-7RV")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_INVALID_PILLAR60A_SPEC)

    def test_42_eval_60a_rejects_bright_mon_in_shooting_menu_drift(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(bright_monitoring_in_shooting_menu=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT)

    def test_43_eval_60a_rejects_bright_mon_without_setting_effect_off(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                bright_monitoring_requested=True,
                reported_effective_bright_monitoring=True,
                reported_forced_live_view_display="Setting Effect ON",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT)

    def test_44_eval_60a_rejects_dormant_monitor_auto_spoof(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                monitor_brightness_mode="Auto",
                reported_monitor_brightness_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT)

    def test_45_eval_60a_rejects_camera_reset_wiping_monitor_brightness(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                monitor_brightness_mode="Sunny Weather",
                reset_action="Camera Settings Reset",
                post_monitor_brightness_mode="Manual",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BRIGHT_MON_OR_MONITOR_BRIGHTNESS_DRIFT)

    def test_46_eval_60a_rejects_bulb_allowed_under_electronic_shutter(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                bulb_requested=True,
                shutter_type="Electronic Shutter",
                reported_effective_bulb_active=True,
                reported_bulb_errno=None,
                post_bulb_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT)

    def test_47_eval_60a_rejects_dormant_bulb_timer_or_auto_hdr_spoof(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                requested_dormant_bulb_or_hdr_symbols=("Bulb Timer",),
                reported_dormant_bulb_hdr_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_BULB_MECH_OR_DORMANT_BULB_TIMER_HDR_DRIFT)

    def test_48_eval_60a_rejects_fx6_ae_backlight_conflation_or_still_spoof(self) -> None:
        rep1 = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                fx6_ae_backlight_is_exposure_mode=False,
            )
        )
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF)

        rep2 = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                fx6_has_bright_monitoring=True,
            )
        )
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P336_BLOCKED_FX6_VF_BACKLIGHT_OR_STILL_SPOOF)

    def test_49_eval_60a_rejects_slot1_format_full(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_FULL",
                slot1_vault_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_50_eval_60a_rejects_persistent_overlay_escape(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(overlay_dir="/setting/60a")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_51_eval_60a_rejects_backup_bin_h0_h3_mismatch(self) -> None:
        rep = evaluate_bright_mon_bulb_vault(
            build_default_safe_bright_mon_bulb_vault_spec(backup_bin_h3_sha256="a" * 64)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_52_eval_60a_rejects_safety_policy_violation(self) -> None:
        with patch.object(p60_mod, "PHYSICAL_DEVICE_WRITES", 1):
            rep = evaluate_bright_mon_bulb_vault(build_default_safe_bright_mon_bulb_vault_spec())
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_SAFETY_POLICY_VIOLATION)

    # ------------------------------------------------------------------
    # Pillar 60B State Helper Tests (53..68)
    # ------------------------------------------------------------------

    def _default_60b_state(self, **overrides: object) -> dict:
        kw = dict(
            camera_model=P336_FX3_MODEL_NAME,
            shot_mark_slot=1,
            clip_flag="Off",
            image_jump_setting="Shot Mark Only",
            photo_capture_file_type="JPEG",
            requested_dormant_clip_edit_symbols=(),
            requested_fx6_dormant_shot_mark_symbols=(),
            requested_bt_timecode_link=False,
            vmc_bncm1_connected=True,
            timecode_make="Preset",
            timecode_run="Free Run",
            hdmi_tc_output="On",
            wifi_sku="WW728473",
            wifi_band="5GHz",
            wifi_security="WPA3-SAE",
            usb_lan_active=True,
            usb_lan_cnct_launch="On",
            wifi_active=False,
            multi_micro_usb_in_use=False,
            airplane_mode="On",
            network_transport=P336_SAFE_WIRED_TRANSPORT,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
            shot_mark_or_clip_flag_targets_slot1=False,
            photo_capture_or_divider_targets_slot1=False,
        )
        kw.update(overrides)
        return compute_expected_shotmark_tc_usblan_vault_state(**kw)

    def test_53_state_60b_active_shot_mark_and_clip_flag_valid(self) -> None:
        st = self._default_60b_state(shot_mark_slot=1, clip_flag="OK", requested_vault_slot=2)
        self.assertIsNone(st["dormant_clip_edit_errno"])
        self.assertTrue(st["action_allowed"])

    def test_54_state_60b_dormant_divide_extract_cut_fail_closed_eopnotsupp(self) -> None:
        st1 = self._default_60b_state(requested_dormant_clip_edit_symbols=("Divide", "Extract"))
        self.assertEqual(st1["dormant_clip_edit_errno"], P336_EOPNOTSUPP_ERRNO)
        st2 = self._default_60b_state(requested_vault_action="DORMANT_DIVIDE_CLIP")
        self.assertEqual(st2["dormant_clip_edit_errno"], P336_EOPNOTSUPP_ERRNO)
        self.assertFalse(st2["action_allowed"])

    def test_55_state_60b_fx6_shot_mark_0_to_9_dormant_eopnotsupp(self) -> None:
        st = self._default_60b_state(requested_fx6_dormant_shot_mark_symbols=("Shot Mark 0..9", "Essence Mark"))
        self.assertEqual(st["dormant_fx6_shot_mark_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_56_state_60b_bt_timecode_link_rejected_eopnotsupp(self) -> None:
        st = self._default_60b_state(requested_bt_timecode_link=True)
        self.assertEqual(st["bt_timecode_link_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_57_state_60b_vmc_bncm1_ext_lk_requires_preset_free_run_and_no_usb_lan(self) -> None:
        st_ext = self._default_60b_state(vmc_bncm1_connected=True, usb_lan_active=False)
        self.assertTrue(st_ext["ext_tc_locked"])
        self.assertEqual(st_ext["ext_tc_status"], "EXT-LK")

        st_int = self._default_60b_state(vmc_bncm1_connected=True, timecode_make="Regenerate", usb_lan_active=False)
        self.assertFalse(st_int["ext_tc_locked"])
        self.assertEqual(st_int["ext_tc_status"], "INTERNAL")

    def test_58_state_60b_wifi_sku_ww728473_vs_ww558244(self) -> None:
        self.assertIsNone(self._default_60b_state(wifi_sku="WW728473", wifi_band="5GHz")["wifi_band_errno"])
        self.assertIsNone(self._default_60b_state(wifi_sku="WW558244", wifi_band="2.4GHz")["wifi_band_errno"])
        st_bad = self._default_60b_state(wifi_sku="WW558244", wifi_band="5GHz")
        self.assertEqual(st_bad["wifi_band_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_59_state_60b_wpa2_wpa3_active_vs_removed_wep_wpa_ipsec(self) -> None:
        for sec in P336_WIFI_SECURITY_ACTIVE_MODES:
            self.assertIsNone(self._default_60b_state(wifi_security=sec)["wifi_security_errno"])
        for old_sec in P336_WIFI_SECURITY_REMOVED_MODES:
            self.assertEqual(
                self._default_60b_state(wifi_security=old_sec)["wifi_security_errno"],
                P336_EOPNOTSUPP_ERRNO,
            )

    def test_60_state_60b_usblan_mutex_with_wifi_and_multi_micro_usb(self) -> None:
        st_wifi = self._default_60b_state(usb_lan_active=True, wifi_active=True)
        self.assertEqual(st_wifi["usb_lan_conflict_errno"], P336_EOPNOTSUPP_ERRNO)
        st_multi = self._default_60b_state(usb_lan_active=True, multi_micro_usb_in_use=True)
        self.assertEqual(st_multi["usb_lan_conflict_errno"], P336_EOPNOTSUPP_ERRNO)

    def test_61_state_60b_airplane_mode_retained_across_reset_network_and_initialize(self) -> None:
        for act in ("Reset Network Set.", "Initialize"):
            st = self._default_60b_state(usb_lan_cnct_launch="On", airplane_mode="On", reset_action=act)
            self.assertEqual(st["post_usb_lan_cnct_launch"], "Off")
            self.assertEqual(st["post_airplane_mode"], "On")
            self.assertTrue(st["rf_zero_enforced"])

    def test_62_state_60b_slot1_vault_erofs_blocks_shotmark_clipflag_photo_divider(self) -> None:
        for action in (
            "ADD_SHOT_MARK1",
            "SET_CLIP_FLAG",
            "PHOTO_CAPTURE",
            "CREATE_DIVIDER_FRAME",
            "FORMAT_QUICK",
            "FORMAT_FULL",
        ):
            st = self._default_60b_state(
                requested_vault_slot=1,
                requested_vault_action=action,
                shot_mark_or_clip_flag_targets_slot1=True,
            )
            self.assertFalse(st["action_allowed"], action)
            self.assertEqual(st["firewall_errno"], "EROFS", action)

    def test_63_state_60b_slot2_shotmark_clipflag_photo_divider_allowed(self) -> None:
        for action in (
            "ADD_SHOT_MARK1",
            "SET_CLIP_FLAG",
            "PHOTO_CAPTURE",
            "CREATE_DIVIDER_FRAME",
        ):
            st = self._default_60b_state(
                requested_vault_slot=2,
                requested_vault_action=action,
            )
            self.assertTrue(st["action_allowed"], action)
            self.assertIsNone(st["firewall_errno"], action)

    def test_64_state_60b_fx6_bnc_tc_ext_lk_without_vmc_bncm1(self) -> None:
        st = self._default_60b_state(
            camera_model=P336_FX6_DONOR_MODEL_NAME,
            vmc_bncm1_connected=False,
            usb_lan_active=False,
        )
        self.assertTrue(st["ext_tc_locked"])
        self.assertEqual(st["ext_tc_status"], "EXT-LK")

    def test_65_state_60b_slot1_target_flags_trigger_erofs_even_on_audit(self) -> None:
        st1 = self._default_60b_state(requested_vault_slot=1, shot_mark_or_clip_flag_targets_slot1=True)
        self.assertEqual(st1["firewall_errno"], "EROFS")
        st2 = self._default_60b_state(requested_vault_slot=1, photo_capture_or_divider_targets_slot1=True)
        self.assertEqual(st2["firewall_errno"], "EROFS")

    def test_66_state_60b_all_clip_flag_options_accepted_on_slot2(self) -> None:
        for flag in P336_CLIP_FLAG_OPTIONS:
            st = self._default_60b_state(
                requested_vault_slot=2,
                requested_vault_action="SET_CLIP_FLAG",
                clip_flag=flag,
            )
            self.assertTrue(st["action_allowed"])

    def test_67_state_60b_all_photo_capture_file_types_accepted_on_slot2(self) -> None:
        for ftype in P336_PHOTO_CAPTURE_FILE_TYPES:
            st = self._default_60b_state(
                requested_vault_slot=2,
                requested_vault_action="PHOTO_CAPTURE",
                photo_capture_file_type=ftype,
            )
            self.assertTrue(st["action_allowed"])

    def test_68_state_60b_usb_lan_inactive_still_enforces_rf_zero_in_airplane_mode(self) -> None:
        st = self._default_60b_state(usb_lan_active=False, wifi_active=False, airplane_mode="On")
        self.assertTrue(st["rf_zero_enforced"])

    # ------------------------------------------------------------------
    # Pillar 60B Evaluator Tests (69..86)
    # ------------------------------------------------------------------

    def test_69_eval_60b_default_safe_spec_passes(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(build_default_safe_shotmark_usblan_vault_spec())
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P336_STATUS_VERIFIED_PILLAR_60B)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_70_eval_60b_slot2_shotmark_and_clip_flag_pass(self) -> None:
        for flag in ("OK", "NG", "KEEP"):
            rep = evaluate_shotmark_tc_usblan_vault(
                build_default_safe_shotmark_usblan_vault_spec(
                    shot_mark_slot=1,
                    clip_flag=flag,
                    requested_vault_slot=2,
                    requested_vault_action="SET_CLIP_FLAG",
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                )
            )
            self.assertTrue(rep.passed, f"flag={flag}: {rep.errors}")

    def test_71_eval_60b_vmc_bncm1_ext_lk_with_usb_lan_off_passes(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                vmc_bncm1_connected=True,
                usb_lan_active=False,
                multi_micro_usb_in_use=True,
                reported_ext_tc_status="EXT-LK",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_72_eval_60b_ww558244_24ghz_wpa2_passes(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                wifi_sku="WW558244",
                wifi_band="2.4GHz",
                wifi_security="WPA2-PSK",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_73_eval_60b_rejects_invalid_camera_model(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(camera_model="PXW-FX9")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_INVALID_PILLAR60B_SPEC)

    def test_74_eval_60b_rejects_dormant_divide_extract_spoof(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                requested_dormant_clip_edit_symbols=("Divide",),
                reported_dormant_clip_edit_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_SHOTMARK_CLIPFLAG_OR_DORMANT_DIVIDE_DRIFT)

    def test_75_eval_60b_rejects_bt_timecode_link_spoof(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                requested_bt_timecode_link=True,
                reported_bt_timecode_link_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_76_eval_60b_rejects_removed_wep_wpa_ipsec_spoof(self) -> None:
        for old_sec in P336_WIFI_SECURITY_REMOVED_MODES:
            rep = evaluate_shotmark_tc_usblan_vault(
                build_default_safe_shotmark_usblan_vault_spec(
                    wifi_security=old_sec,
                    reported_wifi_security_errno=None,
                )
            )
            self.assertFalse(rep.passed, old_sec)
            self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_77_eval_60b_rejects_ww558244_5ghz_spoof(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                wifi_sku="WW558244",
                wifi_band="5GHz",
                reported_wifi_band_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_78_eval_60b_rejects_usblan_wifi_or_multi_usb_mutex_bypass(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                usb_lan_active=True,
                multi_micro_usb_in_use=True,
                reported_usb_lan_conflict_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_79_eval_60b_rejects_reset_network_or_init_clearing_airplane_mode(self) -> None:
        for act in ("Reset Network Set.", "Initialize"):
            rep = evaluate_shotmark_tc_usblan_vault(
                build_default_safe_shotmark_usblan_vault_spec(
                    reset_action=act,
                    post_airplane_mode="Off",
                )
            )
            self.assertFalse(rep.passed, act)
            self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_80_eval_60b_rejects_wifi_or_rf_packets_transmitted(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                airplane_mode="Off",
                post_airplane_mode="Off",
                network_transport="Wi-Fi",
                rf_packets_transmitted=3,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_81_eval_60b_rejects_slot1_m4root_avf_or_divider_write(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="ADD_SHOT_MARK1",
                shot_mark_or_clip_flag_targets_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=4096,
                slot1_m4root_avf_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_82_eval_60b_rejects_slot1_erofs_bypass_on_photo_capture(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="PHOTO_CAPTURE",
                photo_capture_or_divider_targets_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_dcim_divider_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_83_eval_60b_rejects_persistent_overlay_escape(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(overlay_dir="/setting/60b")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_84_eval_60b_rejects_backup_bin_h0_h3_mismatch(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_85_eval_60b_rejects_fx6_bnc_spoof_when_disabled(self) -> None:
        rep = evaluate_shotmark_tc_usblan_vault(
            build_default_safe_shotmark_usblan_vault_spec(fx6_has_physical_tc_in_out_bnc=False)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_TC_LINK_WPA3_OR_USBLAN_MUTEX_DRIFT)

    def test_86_eval_60b_rejects_safety_policy_violation(self) -> None:
        with patch.object(p60_mod, "OTP_FUSE_TOUCHES", 1):
            rep = evaluate_shotmark_tc_usblan_vault(build_default_safe_shotmark_usblan_vault_spec())
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P336_BLOCKED_SAFETY_POLICY_VIOLATION)

    # ------------------------------------------------------------------
    # Standalone Suite, 60/60 Master, CLI & Auto-Discovery Tests (87..100)
    # ------------------------------------------------------------------

    def test_87_combined_single_shot_verifier_and_alias(self) -> None:
        rep1 = verify_bright_mon_shotmark_usblan_bulb_and_vault(force_clean_room=True)
        rep2 = verify_bright_mon_shotmark_usblan_bulb_vault(force_clean_room=True)
        self.assertTrue(rep1.all_passed)
        self.assertTrue(rep2.all_passed)
        self.assertEqual(rep1.donor_snapshot.donor_files_inspected, 17)
        self.assertEqual(rep1.bright_mon_bulb_report.status, P336_STATUS_VERIFIED_PILLAR_60A)
        self.assertEqual(rep1.shotmark_usblan_report.status, P336_STATUS_VERIFIED_PILLAR_60B)

    def test_88_pillar60a_6_scenario_suite_passes(self) -> None:
        res = run_pillar60a_bright_mon_bulb_vault_6_scenario_suite()
        self.assertTrue(res.passed, res.scenarios)
        self.assertEqual(res.status, P336_STATUS_VERIFIED_PILLAR_60A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)

    def test_89_pillar60b_6_scenario_suite_passes(self) -> None:
        res = run_pillar60b_shotmark_tc_usblan_vault_6_scenario_suite()
        self.assertTrue(res.passed, res.scenarios)
        self.assertEqual(res.status, P336_STATUS_VERIFIED_PILLAR_60B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)

    def test_90_standalone_suite_normal_and_clean_room(self) -> None:
        rep_norm = run_pillar60_standalone_suite()
        self.assertTrue(rep_norm.all_passed, rep_norm.errors)
        self.assertEqual(rep_norm.status, P336_STATUS_VERIFIED_PILLAR60_SUITE)
        self.assertEqual(rep_norm.rf_packets_transmitted, 0)
        self.assertEqual(rep_norm.slot1_data_sector_writes, 0)

        rep_cr = run_pillar60_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr.all_passed, rep_cr.errors)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr.pillar_60a_bright_mon_monitor_brightness_bulb_vault.scenarios_passed, 6)
        self.assertEqual(rep_cr.pillar_60b_shotmark_edit_tclink_wpa3_usblan_vault.scenarios_passed, 6)

    def test_91_master_60pillar_recovery_normal_mode(self) -> None:
        rep = evaluate_realhw_60pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P336_STATUS_VERIFIED_60OF60_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 60)
        self.assertEqual(rep.pillars_passed, 60)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_92_master_60pillar_recovery_clean_room_and_alias(self) -> None:
        rep = evaluate_60pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillars_passed, 60)
        self.assertTrue(rep.fx3_bright_mon_v700_focus_mag_coexist)
        self.assertEqual(rep.fx3_bright_monitoring_symbol_count, 6)
        self.assertEqual(rep.fx3_monitor_brightness_level_min, -2)
        self.assertEqual(rep.fx3_monitor_brightness_level_max, 2)
        self.assertFalse(rep.fx3_has_dormant_bulb_timer)
        self.assertFalse(rep.fx3_has_dormant_auto_hdr)
        self.assertFalse(rep.fx3_has_dormant_divide_extract)
        self.assertFalse(rep.fx3_has_bt_timecode_link)
        self.assertEqual(rep.fx3_usb_lan_kmod_count, 8)
        self.assertEqual(rep.fx3_wifi_active_security_count, 2)
        self.assertEqual(rep.fx6_vf_brightness_min, 1)
        self.assertEqual(rep.fx6_vf_brightness_max, 15)
        self.assertTrue(rep.fx6_has_physical_tc_in_out_bnc)

        rep2 = verify_60pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(rep2.all_passed)
        self.assertEqual(rep2.pillars_passed, 60)

    def test_93_master_60pillar_rollup_carries_p58_p59_and_p60_metrics(self) -> None:
        rep = evaluate_realhw_60pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.fx3_dial_customize_item_count, 5)
        self.assertEqual(rep.fx3_fn_menu_still_slots, 12)
        self.assertEqual(rep.fx3_fn_menu_movie_slots, 12)
        self.assertEqual(rep.fx3_steadyshot_47_focal_count, 47)
        self.assertEqual(rep.bright_mon_or_monitor_brightness_drift_events, 0)
        self.assertEqual(rep.bulb_mech_or_dormant_bulb_timer_hdr_drift_events, 0)
        self.assertEqual(rep.fx6_vf_backlight_or_still_spoof_events, 0)
        self.assertEqual(rep.shotmark_clipflag_or_dormant_divide_drift_events, 0)
        self.assertEqual(rep.tc_link_wpa3_or_usblan_mutex_drift_events, 0)
        self.assertEqual(rep.zero_rf_or_slot1_vault_bypass_events, 0)

    def test_94_fault_inject_pillar_60_and_earlier_59_fail_closed(self) -> None:
        rep60 = evaluate_realhw_60pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault",
        )
        self.assertFalse(rep60.all_passed)
        self.assertEqual(rep60.pillars_passed, 59)
        self.assertIn("pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault", rep60.failed_pillars)

        rep59 = evaluate_realhw_60pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault",
        )
        self.assertFalse(rep59.all_passed)
        self.assertEqual(rep59.pillars_passed, 59)
        self.assertIn("pillar59_steadyshot_47focal_selftimer_zebra_streaming_vault", rep59.failed_pillars)

        with self.assertRaises(ValueError):
            evaluate_realhw_60pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_95_cli_verify_60pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-60pillar-recovery", "--json"],
            ["verify-60pillar-recovery", "--force-clean-room", "--json"],
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
            self.assertEqual(payload["pillars_passed"], 60)
            self.assertEqual(payload["pillar_count"], 60)
            self.assertLess(payload["elapsed_seconds"], P336_CONCURRENT_CEILING_SECONDS)

    def test_96_cli_verify_pillar60_aliases_text_and_out(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar60-recovery",
            "verify-pillar60-bright-mon-shotmark-usblan-bulb-vault",
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
            self.assertIn("VERIFIED_PILLAR60_BRIGHT_MON_SHOTMARK_USBLAN_BULB_VAULT", proc_txt.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p336_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p60_path = work_tests / f"{tag}_p60"
        try:
            proc1 = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-60pillar-recovery", "--force-clean-room", "--out", str(out_master_path)],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            self.assertTrue((out_master_path / "60pillar-recovery-master-report.json").exists())

            proc2 = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-pillar60-recovery", "--force-clean-room", "--out", str(out_p60_path)],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            self.assertTrue((out_p60_path / "pillar60-bright-mon-shotmark-usblan-bulb-vault-report.json").exists())
        finally:
            for d in (out_master_path, out_p60_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_97_cli_backward_compat_verify_59pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-59pillar-recovery", "--force-clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 59)

    def test_98_milestone311_and_324_auto_discovery_forward_compatible_ge_60(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        c311, fn311, ids311 = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(c311, 60)
        self.assertTrue(callable(fn311))
        self.assertGreaterEqual(len(ids311), 60)

        c324, fn324, ids324 = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(c324, 60)
        self.assertTrue(callable(fn324))
        self.assertGreaterEqual(len(ids324), 60)

    def test_99_master_60pillar_report_to_dict_roundtrip_and_package_root_exports(self) -> None:
        rep = evaluate_realhw_60pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 60)
        self.assertEqual(parsed["pillars_passed"], 60)
        for sym in (
            "MASTER_60_PILLAR_COUNT",
            "MASTER_60_PILLAR_IDS",
            "MASTER_60_PILLAR_SPECS",
            "Master60PillarRecoveryReport",
            "evaluate_realhw_60pillar_recovery_master",
            "evaluate_60pillar_recovery_master",
            "verify_60pillar_recovery_suite",
            "run_pillar60_standalone_suite",
        ):
            self.assertTrue(hasattr(fr, sym), sym)

    def test_100_donorless_ci_mock_master60_and_cli_subprocess_exit_zero(self) -> None:
        from fx3_recovery import __main__ as cli_main
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            for mock_roots in ((None,), (Path("/nonexistent-donor-root"),)):
                with patch.object(files_mod, "iter_donor_work_roots", return_value=mock_roots):
                    rep = evaluate_realhw_60pillar_recovery_master()
                    self.assertTrue(rep.all_passed, rep.errors)
                    self.assertEqual(rep.pillars_passed, 60)
                    self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    buf = io.StringIO()
                    with patch.object(sys, "argv", ["fx3_recovery", "verify-60pillar-recovery", "--json"]), redirect_stdout(buf):
                        rc = cli_main.main()
                    self.assertEqual(rc, 0, buf.getvalue())
                    payload = json.loads(buf.getvalue())
                    self.assertTrue(payload["all_passed"])
                    self.assertEqual(payload["pillars_passed"], 60)
                    self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

        # Also test true isolated subprocess invocation mocking iter_donor_work_roots to (None,)
        sub_env = {
            **clean_env,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ADAPTER_ROOT),
        }
        snippet = (
            "import sys; from unittest.mock import patch; "
            "from fx3_recovery import files as f, __main__ as m; "
            "sys.argv = ['fx3_recovery', 'verify-60pillar-recovery', '--json']; "
            "p = patch.object(f, 'iter_donor_work_roots', return_value=(None,)); "
            "p.start(); "
            "rc = m.main(); "
            "p.stop(); "
            "raise SystemExit(rc)"
        )
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-c", snippet],
            cwd=str(REPO_ROOT),
            env=sub_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        sub_payload = json.loads(proc.stdout)
        self.assertTrue(sub_payload["all_passed"])
        self.assertEqual(sub_payload["pillars_passed"], 60)
        self.assertEqual(sub_payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
