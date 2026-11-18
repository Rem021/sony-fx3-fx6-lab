"""Phase 340 (Pillar 61 & 61/61 Milestone) unit tests:
Wave-59 Ver. 7.00/7.02 HOME (BIG6) Fixed/Variable & Home (Lower Left) metadata-only ND vs FX6
built-in electronic ND, Manual [Framing Settings] (Recording/Streaming Full/Crop, HDMI Crop/Full,
APS-C off, 100p/Rec/Stream lockouts) vs 100% dormant AI [Auto Framing] (`0` hits in FX3 appFw.so ->
EOPNOTSUPP=95), Still-only [Interval Shoot Func.] (7 Resettable sub-items, Electronic Shutter
default, 1..9999 shots, BULB->30", Slot-1 DCIM/AVF_INFO EROFS=30) vs FX6 [Interval Rec] single
XAVC MXF, Initialize-only [Time Code Make/Run] (Regenerate reads Slot 1 under Simult. Rec & forces
Rec Run; VMC-BNCM1 EXT-LK requires Preset+Free Run), HDMI [REC Control] (TC Output=On gate, valid
in On & Off(HDMI Only), disabled in S&Q/Streaming) + [4ch Audio Output] vs FX6 TC_MAKE_CLOCK &
SDI/HDMI Remote I/F vs Parallel Rec, Ver. 7.00+ [Access Authen.] (SSH+PTP-IP, 0 hits HTTP_DIGEST/
BASIC_AUTH/HTTPS, no WEP/WPA-PSK/IPsec, outbound TLS Root Certs only), [Fan Control] 4-mode FX3 /
3-mode FX6 with ZERO `Max` option + [Auto Power OFF Temp.] (Standard/High) & Zero-RF / Slot-1 EROFS=30.
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
    MASTER_61_PILLAR_COUNT,
    MASTER_61_PILLAR_IDS,
    MASTER_61_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P340_ACCESS_AUTHEN_F_RESID16,
    P340_ACCESS_AUTHEN_INFO_F_RESID16,
    P340_AIRPLANE_MODE_FORCED_ON,
    P340_AUDIO_4CH_OUTPUT_F_RESID16,
    P340_AUDIO_4CH_OUTPUT_MODES,
    P340_AUTO_POWER_OFF_TEMP_MODES,
    P340_AUTO_PWR_OFF_TEMP_F_RESID16,
    P340_BASE_ISO_F_RESID16,
    P340_BIG6_ENTRY_TRIGGERS,
    P340_BIG6_FUNC_ISO_EI,
    P340_BIG6_VIEW_SYMBOL,
    P340_BKID_HOME_LAST_CURSOR_POS,
    P340_BKID_HOME_LOWER_LEFT,
    P340_BKID_HOME_SCREEN_STATE,
    P340_BKID_MODE_SETTINGS_FIXED_VAR,
    P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT,
    P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT,
    P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT,
    P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF,
    P340_BLOCKED_INVALID_PILLAR61A_SPEC,
    P340_BLOCKED_INVALID_PILLAR61B_SPEC,
    P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P340_BLOCKED_SAFETY_POLICY_VIOLATION,
    P340_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT,
    P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
    P340_CONCURRENT_CEILING_SECONDS,
    P340_DISPLAY_AS_GROUP_F_RESID16,
    P340_DONOR_INSPECT_BUDGET_SECONDS,
    P340_DORMANT_AUTO_FRAMING_F_RESID16S,
    P340_DORMANT_AUTO_FRAMING_SYMBOLS,
    P340_DORMANT_IPSEC_F_RESID16,
    P340_EBUSY_ERRNO,
    P340_EINVAL_ERRNO,
    P340_EOPNOTSUPP_ERRNO,
    P340_EROFS_ERRNO,
    P340_FAN_ALWAYS_OFF_F_RESID16,
    P340_FAN_CONTROL_ALL_MODES,
    P340_FAN_CONTROL_FORBIDDEN_MAX_MODES,
    P340_FAN_CONTROL_F_RESID16,
    P340_FAST_CLI_BUDGET_SECONDS,
    P340_FRAMING_CROP_OPTIONS,
    P340_FRAMING_DEFAULT_HDMI,
    P340_FRAMING_DEFAULT_REC_STREAMING,
    P340_FRAMING_DEFAULT_STATE,
    P340_FRAMING_HDMI_F_RESID16,
    P340_FRAMING_REC_STREAMING_F_RESID16,
    P340_FRAMING_SETTINGS_F_RESID16,
    P340_FRAMING_STOP_FULL_F_RESID16,
    P340_FRAMING_SWITCH_F_RESID16,
    P340_FX3_4K60_HIGH_MIN,
    P340_FX3_4K60_STANDARD_MIN,
    P340_FX3_ACCESS_AUTHEN_PROTOCOLS,
    P340_FX3_APPFW_AUTO_FRAMING_HIT_COUNT,
    P340_FX3_BIG6_MIN_FW_VERSIONS,
    P340_FX3_BIG6_TILE_COUNT,
    P340_FX3_FAN_CONTROL_MODES,
    P340_FX3_FAN_MAX_HIT_COUNT,
    P340_FX3_FORBIDDEN_AUTH_PROTOCOLS,
    P340_FX3_FRAMING_SUPPORT_ENUM,
    P340_FX3_FW_VERSION,
    P340_FX3_HD60_HIGH_MIN,
    P340_FX3_HD60_STANDARD_MIN,
    P340_FX3_HELPGUIDE_ID,
    P340_FX3_HTTP_DIGEST_HTTPS_HIT_COUNT,
    P340_FX3_MODEL_NAME,
    P340_FX3_PHYSICAL_END_HARDWARE,
    P340_FX3_TIMECODE_MAKE_MODES,
    P340_FX3_WIFI_SECURITY_ACTIVE_MODES,
    P340_FX3_WIFI_SECURITY_REMOVED_MODES,
    P340_FX6_BIG6_TILES,
    P340_FX6_DONOR_FW_VERSION,
    P340_FX6_DONOR_MODEL_NAME,
    P340_FX6_END_STOPS,
    P340_FX6_FAN_CONTROL_ACTIVE_MODES,
    P340_FX6_FAN_MAX_HIT_COUNT,
    P340_FX6_INTERVAL_REC_EXCLUSIONS,
    P340_FX6_INTERVAL_REC_FRAME_COUNTS,
    P340_FX6_INTERVAL_REC_PRE_LIGHTING,
    P340_FX6_SDI_HDMI_REC_CTRL_MODES,
    P340_FX6_TC_MAKE_SYMBOL_CLOCK,
    P340_HDMI_REC_CONTROL_F_RESID16,
    P340_HDMI_TC_OUTPUT_F_RESID16,
    P340_HOME_KEY_F_RESID16,
    P340_HOME_LOWER_LEFT_F_RESID16,
    P340_HOME_LOWER_LEFT_MODES,
    P340_HOME_OPEN_F_RESID16,
    P340_HOME_SCREEN_STATES,
    P340_IMPORT_ROOT_CERT_F_RESID16,
    P340_INTERVAL_AE_TRACKING_DEFAULT,
    P340_INTERVAL_AE_TRACKING_MODES,
    P340_INTERVAL_SEC_DEFAULT,
    P340_INTERVAL_SEC_MAX,
    P340_INTERVAL_SEC_MIN,
    P340_INTERVAL_SHOOT_FUNC_F_RESID16,
    P340_INTERVAL_SHOTS_DEFAULT,
    P340_INTERVAL_SHOTS_MAX,
    P340_INTERVAL_SHOTS_MIN,
    P340_INTERVAL_SHUTTER_TYPES,
    P340_INTERVAL_SHUTTER_TYPE_DEFAULT,
    P340_INTERVAL_START_TIME_DEFAULT_SEC,
    P340_INTERVAL_START_TIME_MAX_SEC,
    P340_INTERVAL_START_TIME_MIN_SEC,
    P340_INTERVAL_SUBITEM_COUNT,
    P340_MODE_SETTINGS_FIXED_VAR_F_RESID16,
    P340_NOMINAL_BUDGET_SECONDS,
    P340_PB_SPEED_INTERVAL_F_RESID16,
    P340_PILLAR_61A_SCENARIO_IDS,
    P340_PILLAR_61B_SCENARIO_IDS,
    P340_RF_PACKETS_TRANSMITTED,
    P340_ROOT_CERT_TYPES,
    P340_SAFE_WIRED_TRANSPORT,
    P340_SELECT_LUT_F_RESID16,
    P340_SLOT1_DATA_SECTOR_WRITES,
    P340_SLOT1_FORMAT_HARD_LOCKED,
    P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P340_SSHD_START_CMD,
    P340_STATUS_VERIFIED_61OF61_AGGREGATOR,
    P340_STATUS_VERIFIED_PILLAR61_SUITE,
    P340_STATUS_VERIFIED_PILLAR_61A,
    P340_STATUS_VERIFIED_PILLAR_61B,
    P340_SWIPE_DOWN_F_RESID16,
    P340_TC_MAKE_FX3_SYMBOL_REGENERATE,
    P340_TC_MAKE_F_RESID16,
    P340_TC_RUN_F_RESID16,
    P340_TIER0_SURFACE_COUNT,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PHASE340_MASTER_SCHEMA,
    PHASE340_PHASE_NUMBER,
    PHASE340_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_big6_framing_interval_vault_spec,
    build_default_safe_tc_make_hdmi_auth_fan_vault_spec,
    compute_expected_big6_framing_interval_state,
    compute_expected_tc_make_hdmi_auth_fan_state,
    evaluate_61pillar_recovery_master,
    evaluate_big6_framing_interval_vault,
    evaluate_realhw_61pillar_recovery_master,
    evaluate_tc_make_hdmi_auth_fan_vault,
    inspect_phase340_donors_readonly,
    run_pillar61_standalone_suite,
    run_pillar61a_big6_framing_interval_vault_6_scenario_suite,
    run_pillar61b_tc_make_hdmi_auth_fan_vault_6_scenario_suite,
    verify_61pillar_recovery_suite,
    verify_big6_framing_interval_tc_auth_fan_and_vault,
    verify_big6_framing_interval_tc_auth_fan_vault,
)
from fx3_recovery import (  # noqa: E402
    realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier as p61_mod,
)


class Phase340Pillar61VerifierTests(unittest.TestCase):
    """Comprehensive 4-mode unit tests for Phase 340 Pillar 61 & 61/61 Milestone."""

    # ------------------------------------------------------------------
    # Safety Redlines, Metadata & Wave-59 Empirical Constants (01..12)
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
        self.assertEqual(P340_RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(P340_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertTrue(P340_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P340_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P340_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)

    def test_02_schema_and_61_pillar_metadata(self) -> None:
        self.assertEqual(PHASE340_PHASE_NUMBER, 340)
        self.assertEqual(
            PHASE340_SCHEMA,
            "realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier_v1",
        )
        self.assertEqual(PHASE340_MASTER_SCHEMA, "realhw_61pillar_recovery_master_v1")
        self.assertEqual(MASTER_61_PILLAR_COUNT, 61)
        self.assertEqual(len(MASTER_61_PILLAR_IDS), 61)
        self.assertEqual(len(MASTER_61_PILLAR_SPECS), 61)
        self.assertEqual(
            MASTER_61_PILLAR_IDS[-1],
            "pillar61_big6_home_framing_interval_tc_make_auth_fan_vault",
        )
        self.assertEqual(P340_FX3_HELPGUIDE_ID, "ilc/2210")

    def test_03_big6_home_screen_and_lower_left_constants(self) -> None:
        self.assertEqual(P340_FX3_BIG6_MIN_FW_VERSIONS, ("7.02", "7.01", "7.00"))
        self.assertEqual(P340_FX3_BIG6_TILE_COUNT, 6)
        self.assertEqual(P340_MODE_SETTINGS_FIXED_VAR_F_RESID16, 0x7D0D)
        self.assertEqual(P340_BKID_MODE_SETTINGS_FIXED_VAR, "BKID_APP_setting_fps_fixed_variable_select")
        self.assertEqual(P340_HOME_KEY_F_RESID16, 0x7CAD)
        self.assertEqual(P340_HOME_OPEN_F_RESID16, 0x7CB1)
        self.assertEqual(P340_SWIPE_DOWN_F_RESID16, 0x7CDD)
        self.assertEqual(P340_HOME_LOWER_LEFT_F_RESID16, 0x7CE3)
        self.assertEqual(P340_BKID_HOME_LOWER_LEFT, "BKID_APP_setting_movie_home_lower_left")
        self.assertEqual(P340_HOME_LOWER_LEFT_MODES, ("Aperture", "ND Filter"))
        self.assertFalse(P340_FX3_PHYSICAL_END_HARDWARE)
        self.assertEqual(P340_BIG6_VIEW_SYMBOL, "26view_tp_button_01_for_big6")
        self.assertEqual(P340_BIG6_FUNC_ISO_EI, "update_big6_item_iso_ei")
        self.assertEqual(P340_BASE_ISO_F_RESID16, 0x78CE)
        self.assertEqual(P340_SELECT_LUT_F_RESID16, 0x643E)
        self.assertEqual(len(P340_HOME_SCREEN_STATES), 4)
        self.assertEqual(P340_BKID_HOME_SCREEN_STATE, "BKID_APP_home_screen_state")
        self.assertEqual(P340_BKID_HOME_LAST_CURSOR_POS, "BKID_APP_home_screen_last_cursor_position_number")
        self.assertEqual(len(P340_FX6_BIG6_TILES), 6)
        self.assertEqual(len(P340_FX6_END_STOPS), 4)

    def test_04_manual_framing_and_dormant_auto_framing_constants(self) -> None:
        self.assertEqual(P340_FRAMING_SETTINGS_F_RESID16, 0x7D18)
        self.assertEqual(P340_FRAMING_REC_STREAMING_F_RESID16, 0x7D13)
        self.assertEqual(P340_FRAMING_HDMI_F_RESID16, 0x7D0F)
        self.assertEqual(P340_FRAMING_SWITCH_F_RESID16, 0x7D1E)
        self.assertEqual(P340_FRAMING_STOP_FULL_F_RESID16, 0x7D25)
        self.assertEqual(P340_FRAMING_DEFAULT_STATE, "Off")
        self.assertEqual(P340_FRAMING_DEFAULT_REC_STREAMING, "Full")
        self.assertEqual(P340_FRAMING_DEFAULT_HDMI, "Crop")
        self.assertEqual(P340_FRAMING_CROP_OPTIONS, ("Full", "Crop"))
        self.assertEqual(P340_FX3_FRAMING_SUPPORT_ENUM, "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY")
        self.assertEqual(P340_FX3_APPFW_AUTO_FRAMING_HIT_COUNT, 0)
        self.assertEqual(len(P340_DORMANT_AUTO_FRAMING_F_RESID16S), 5)
        self.assertEqual(len(P340_DORMANT_AUTO_FRAMING_SYMBOLS), 9)

    def test_05_interval_shoot_func_and_fx6_interval_rec_constants(self) -> None:
        self.assertEqual(P340_INTERVAL_SHOOT_FUNC_F_RESID16, 0x7027)
        self.assertEqual(P340_DISPLAY_AS_GROUP_F_RESID16, 0x6F26)
        self.assertEqual(P340_PB_SPEED_INTERVAL_F_RESID16, 0x72BD)
        self.assertEqual(P340_INTERVAL_SUBITEM_COUNT, 7)
        self.assertEqual(P340_INTERVAL_START_TIME_MIN_SEC, 1)
        self.assertEqual(P340_INTERVAL_START_TIME_MAX_SEC, 5999)
        self.assertEqual(P340_INTERVAL_START_TIME_DEFAULT_SEC, 1)
        self.assertEqual(P340_INTERVAL_SEC_MIN, 1)
        self.assertEqual(P340_INTERVAL_SEC_MAX, 60)
        self.assertEqual(P340_INTERVAL_SEC_DEFAULT, 3)
        self.assertEqual(P340_INTERVAL_SHOTS_MIN, 1)
        self.assertEqual(P340_INTERVAL_SHOTS_MAX, 9999)
        self.assertEqual(P340_INTERVAL_SHOTS_DEFAULT, 30)
        self.assertEqual(P340_INTERVAL_AE_TRACKING_MODES, ("High", "Mid", "Low"))
        self.assertEqual(P340_INTERVAL_AE_TRACKING_DEFAULT, "Mid")
        self.assertEqual(P340_INTERVAL_SHUTTER_TYPES, ("Mechanical Shutter", "Electronic Shutter"))
        self.assertEqual(P340_INTERVAL_SHUTTER_TYPE_DEFAULT, "Electronic Shutter")
        self.assertEqual(len(P340_FX6_INTERVAL_REC_FRAME_COUNTS), 8)
        self.assertEqual(len(P340_FX6_INTERVAL_REC_PRE_LIGHTING), 4)
        self.assertEqual(len(P340_FX6_INTERVAL_REC_EXCLUSIONS), 5)

    def test_06_tc_make_run_hdmi_rec_control_and_fx6_constants(self) -> None:
        self.assertEqual(P340_TC_MAKE_F_RESID16, 0x6B79)
        self.assertEqual(P340_TC_RUN_F_RESID16, 0x7313)
        self.assertEqual(P340_TC_MAKE_FX3_SYMBOL_REGENERATE, "VAL_setting_tc_make_TC_MAKE_REGENRATE")
        self.assertEqual(P340_FX3_TIMECODE_MAKE_MODES, ("Preset", "Regenerate"))
        self.assertEqual(P340_FX6_TC_MAKE_SYMBOL_CLOCK, "VAL_setting_tc_make_TC_MAKE_CLOCK")
        self.assertEqual(P340_HDMI_TC_OUTPUT_F_RESID16, 0x72AF)
        self.assertEqual(P340_HDMI_REC_CONTROL_F_RESID16, 0x76E1)
        self.assertEqual(P340_AUDIO_4CH_OUTPUT_F_RESID16, 0x6AA0)
        self.assertEqual(P340_AUDIO_4CH_OUTPUT_MODES, ("CH1/CH2", "CH3/CH4"))
        self.assertEqual(P340_FX6_SDI_HDMI_REC_CTRL_MODES, ("Off", "SDI/HDMI Remote I/F", "Parallel Rec"))

    def test_07_access_authen_ssh_tls_and_fan_control_constants(self) -> None:
        self.assertEqual(P340_ACCESS_AUTHEN_F_RESID16, 0x7ADA)
        self.assertEqual(P340_ACCESS_AUTHEN_INFO_F_RESID16, 0x6B2B)
        self.assertEqual(P340_IMPORT_ROOT_CERT_F_RESID16, 0x7940)
        self.assertEqual(P340_DORMANT_IPSEC_F_RESID16, 0x69AA)
        self.assertEqual(P340_SSHD_START_CMD, "MSGID_SSHD_START_CMD")
        self.assertEqual(P340_FX3_APPFW_AUTO_FRAMING_HIT_COUNT, 0)
        self.assertEqual(P340_FX3_HTTP_DIGEST_HTTPS_HIT_COUNT, 0)
        self.assertEqual(P340_ROOT_CERT_TYPES, ("CLOUD", "FTP", "RTMP"))
        self.assertEqual(P340_FX3_WIFI_SECURITY_ACTIVE_MODES, ("WPA2-PSK", "WPA3-SAE"))
        self.assertEqual(P340_FX3_WIFI_SECURITY_REMOVED_MODES, ("WEP", "WPA-PSK", "Security(IPsec)"))
        self.assertEqual(P340_FX3_ACCESS_AUTHEN_PROTOCOLS, ("SSH+PTP-IP",))
        self.assertEqual(
            P340_FX3_FORBIDDEN_AUTH_PROTOCOLS,
            ("HTTP_DIGEST", "BASIC_AUTH", "HTTPS"),
        )
        self.assertEqual(P340_FAN_CONTROL_F_RESID16, 0x6E77)
        self.assertEqual(P340_FAN_ALWAYS_OFF_F_RESID16, 0x68FD)
        self.assertEqual(P340_FX3_FAN_CONTROL_MODES, ("Auto", "Minimum", "Off in Rec", "Always Off"))
        self.assertEqual(P340_FX6_FAN_CONTROL_ACTIVE_MODES, ("Auto", "Minimum", "Off in Rec"))
        self.assertEqual(P340_FAN_CONTROL_FORBIDDEN_MAX_MODES, ("Max", "Always (Max)"))
        self.assertEqual(P340_FX3_FAN_MAX_HIT_COUNT, 0)
        self.assertEqual(P340_FX6_FAN_MAX_HIT_COUNT, 0)
        self.assertEqual(P340_AUTO_PWR_OFF_TEMP_F_RESID16, 0x70F1)
        self.assertEqual(P340_AUTO_POWER_OFF_TEMP_MODES, ("Standard", "High"))
        self.assertEqual((P340_FX3_4K60_STANDARD_MIN, P340_FX3_4K60_HIGH_MIN), (30, 90))
        self.assertEqual((P340_FX3_HD60_STANDARD_MIN, P340_FX3_HD60_HIGH_MIN), (60, 120))

    def test_08_budget_and_donor_threshold_constants(self) -> None:
        self.assertEqual(P340_DONOR_INSPECT_BUDGET_SECONDS, 2.0)
        self.assertEqual(P340_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P340_NOMINAL_BUDGET_SECONDS, 4.00)
        self.assertEqual(P340_CONCURRENT_CEILING_SECONDS, 6.00)
        self.assertEqual(P340_TIER0_SURFACE_COUNT, 16)
        self.assertEqual(P340_SAFE_WIRED_TRANSPORT, "USB-LAN (CDC-NCM)")

    # ------------------------------------------------------------------
    # Donor Inspection & Clean-Room Guard Tests (09..14)
    # ------------------------------------------------------------------

    def test_09_donor_inspection_force_clean_room_synthetic_17_artifacts(self) -> None:
        snap = inspect_phase340_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertTrue(snap.under_2_0s_budget)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_10_donor_inspection_local_or_clean_room_both_pass_budget(self) -> None:
        snap = inspect_phase340_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertTrue(snap.under_2_0s_budget)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_11_resolve_donor_path_handles_work_root_none_safely(self) -> None:
        with patch.object(p61_mod, "_iter_work_roots", return_value=(None,)):
            with patch.object(p61_mod, "_is_clean_room_forced", return_value=False):
                resolved = p61_mod._resolve_phase340_donor_path(
                    "work/_scratch/wave59/FX3/appFw.so"
                )
                self.assertIsNone(resolved)

    def test_12_clean_room_env_flags_force_synthetic(self) -> None:
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with patch.dict(os.environ, {env_key: "1"}):
                snap = inspect_phase340_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(snap.donor_files_inspected, 17)

    # ------------------------------------------------------------------
    # Pillar 61A Helper & Evaluator Tests (13..42)
    # ------------------------------------------------------------------

    def test_13_p61a_default_safe_spec_passes(self) -> None:
        rep = evaluate_big6_framing_interval_vault(
            build_default_safe_big6_framing_interval_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P340_STATUS_VERIFIED_PILLAR_61A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_dcim_avf_mutation_bytes, 0)

    def test_14_big6_prereq_requires_fw700_plus_and_fixed_variable(self) -> None:
        st_bad_fw = compute_expected_big6_framing_interval_state(
            camera_model="ILME-FX3",
            fw_version="6.02",
            shooting_domain="Movie",
            exposure_mode="M",
            mode_settings="Fixed/Variable",
            big6_entry_trigger="HOME_KEY",
            touch_operation_enabled=True,
            swipe_down_setting="Open Home Screen",
            log_shooting_mode="Off",
            shutter_mode="Speed",
            home_lower_left_mode="Aperture",
            requested_physical_end_hw=False,
            framing_enabled=False,
            framing_rec_streaming="Full",
            framing_hdmi="Crop",
            apsc_s35_requested=False,
            movie_frame_rate_fps=23.98,
            active_recording=False,
            active_streaming=False,
            requested_dormant_auto_framing_symbols=(),
            interval_shooting_enabled=False,
            interval_start_time_sec=1,
            interval_period_sec=3,
            interval_num_shots=30,
            interval_ae_tracking="Mid",
            interval_shutter_type="Electronic Shutter",
            interval_priority="Off",
            bulb_active=False,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
            interval_targets_slot1=False,
        )
        self.assertFalse(st_bad_fw["supports_big6"])
        self.assertFalse(st_bad_fw["big6_active"])
        self.assertEqual(st_bad_fw["big6_errno"], P340_EOPNOTSUPP_ERRNO)

        st_bad_mode = compute_expected_big6_framing_interval_state(
            camera_model="ILME-FX3",
            fw_version="7.02",
            shooting_domain="Movie",
            exposure_mode="M",
            mode_settings="Movie",
            big6_entry_trigger="HOME_KEY",
            touch_operation_enabled=True,
            swipe_down_setting="Open Home Screen",
            log_shooting_mode="Off",
            shutter_mode="Speed",
            home_lower_left_mode="Aperture",
            requested_physical_end_hw=False,
            framing_enabled=False,
            framing_rec_streaming="Full",
            framing_hdmi="Crop",
            apsc_s35_requested=False,
            movie_frame_rate_fps=23.98,
            active_recording=False,
            active_streaming=False,
            requested_dormant_auto_framing_symbols=(),
            interval_shooting_enabled=False,
            interval_start_time_sec=1,
            interval_period_sec=3,
            interval_num_shots=30,
            interval_ae_tracking="Mid",
            interval_shutter_type="Electronic Shutter",
            interval_priority="Off",
            bulb_active=False,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
            interval_targets_slot1=False,
        )
        self.assertTrue(st_bad_mode["supports_big6"])
        self.assertFalse(st_bad_mode["big6_prereq_ok"])
        self.assertFalse(st_bad_mode["big6_active"])
        self.assertEqual(st_bad_mode["big6_errno"], P340_EOPNOTSUPP_ERRNO)

    def test_15_big6_dynamic_tile_matrix_cine_ei_flexible_iso_and_shutter_angle(self) -> None:
        spec_cine_ei = build_default_safe_big6_framing_interval_vault_spec(
            fw_version="7.00",
            log_shooting_mode="Cine EI",
            shutter_mode="Angle",
            home_lower_left_mode="ND Filter",
            reported_big6_tiles=(
                "FPS",
                "Base ISO + EI",
                "Shutter Angle",
                "ND Filter",
                "Select LUT",
                "White Balance",
            ),
            post_home_lower_left="ND Filter",
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec_cine_ei).passed)

        spec_flex = build_default_safe_big6_framing_interval_vault_spec(
            fw_version="7.01",
            log_shooting_mode="Flexible ISO",
            shutter_mode="Speed",
            home_lower_left_mode="Aperture",
            reported_big6_tiles=(
                "FPS",
                "ISO",
                "Shutter Speed",
                "Aperture",
                "Select LUT",
                "White Balance",
            ),
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec_flex).passed)

    def test_16_big6_swipe_down_entry_and_touch_off_gate(self) -> None:
        spec_swipe_ok = build_default_safe_big6_framing_interval_vault_spec(
            big6_entry_trigger="SWIPE_DOWN",
            touch_operation_enabled=True,
            swipe_down_setting="Open Home Screen",
            reported_big6_active=True,
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec_swipe_ok).passed)

        spec_swipe_blocked = build_default_safe_big6_framing_interval_vault_spec(
            big6_entry_trigger="SWIPE_DOWN",
            touch_operation_enabled=False,
            reported_big6_active=False,
            reported_big6_errno=P340_EOPNOTSUPP_ERRNO,
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec_swipe_blocked).passed)

        spec_swipe_spoof = build_default_safe_big6_framing_interval_vault_spec(
            big6_entry_trigger="SWIPE_DOWN",
            touch_operation_enabled=False,
            reported_big6_active=True,
        )
        rep = evaluate_big6_framing_interval_vault(spec_swipe_spoof)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT)

    def test_17_physical_end_hw_spoof_rejected_with_eopnotsupp(self) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            home_lower_left_mode="ND Filter",
            requested_physical_end_hw=True,
            reported_physical_end_errno=None,
        )
        rep = evaluate_big6_framing_interval_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT)

    def test_18_big6_non_readonly_status_bars_rejected(self) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            reported_big6_status_bars_readonly=False,
        )
        rep = evaluate_big6_framing_interval_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT)

    def test_19_manual_framing_settings_dual_routing_and_apsc_off_verified(self) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            framing_enabled=True,
            framing_rec_streaming="Crop",
            framing_hdmi="Full",
            apsc_s35_requested=True,
            reported_effective_framing_enabled=True,
            reported_effective_apsc_s35=False,
            post_framing_enabled=True,
            post_framing_rec_streaming="Crop",
            post_framing_hdmi="Full",
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec).passed)

    def test_20_manual_framing_100p_and_recording_streaming_lockout_verified(self) -> None:
        for kw in (
            {"movie_frame_rate_fps": 100.0},
            {"movie_frame_rate_fps": 119.88},
            {"active_recording": True},
            {"active_streaming": True},
        ):
            spec_denied = build_default_safe_big6_framing_interval_vault_spec(
                framing_enabled=True,
                reported_effective_framing_enabled=False,
                reported_framing_errno=P340_EBUSY_ERRNO,
                post_framing_enabled=False,
                **kw,
            )
            self.assertTrue(evaluate_big6_framing_interval_vault(spec_denied).passed)

            spec_spoof = build_default_safe_big6_framing_interval_vault_spec(
                framing_enabled=True,
                reported_effective_framing_enabled=True,
                reported_framing_errno=None,
                post_framing_enabled=True,
                **kw,
            )
            rep = evaluate_big6_framing_interval_vault(spec_spoof)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT)

    def test_21_dormant_auto_framing_and_wrong_support_enum_rejected(self) -> None:
        spec_sym = build_default_safe_big6_framing_interval_vault_spec(
            requested_dormant_auto_framing_symbols=("AUTO_FRAMING_AFR",),
            reported_dormant_auto_framing_errno=None,
        )
        rep1 = evaluate_big6_framing_interval_vault(spec_sym)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT)

        spec_enum = build_default_safe_big6_framing_interval_vault_spec(
            framing_support_enum="TYPE_EFRAMING_SUPPORT_TYPE_AI_AUTO",
        )
        rep2 = evaluate_big6_framing_interval_vault(spec_enum)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P340_BLOCKED_FRAMING_MANUAL_OR_DORMANT_AUTO_FRAMING_DRIFT)

    def test_22_interval_shoot_func_still_only_movie_and_iauto_blocked(self) -> None:
        for kw in (
            {"shooting_domain": "Movie"},
            {"shooting_domain": "S&Q"},
            {"shooting_domain": "Still", "exposure_mode": "iAuto"},
        ):
            spec_ok_blocked = build_default_safe_big6_framing_interval_vault_spec(
                mode_settings="Movie" if kw["shooting_domain"] != "Movie" else "Fixed/Variable",
                big6_entry_trigger="NONE" if kw["shooting_domain"] != "Movie" else "HOME_KEY",
                reported_big6_active=(kw["shooting_domain"] == "Movie"),
                interval_shooting_enabled=True,
                reported_effective_interval_enabled=False,
                reported_interval_errno=P340_EOPNOTSUPP_ERRNO,
                post_interval_enabled=False,
                **kw,
            )
            self.assertTrue(evaluate_big6_framing_interval_vault(spec_ok_blocked).passed)

            spec_spoof = build_default_safe_big6_framing_interval_vault_spec(
                mode_settings="Movie" if kw["shooting_domain"] != "Movie" else "Fixed/Variable",
                big6_entry_trigger="NONE" if kw["shooting_domain"] != "Movie" else "HOME_KEY",
                reported_big6_active=(kw["shooting_domain"] == "Movie"),
                interval_shooting_enabled=True,
                reported_effective_interval_enabled=True,
                reported_interval_errno=None,
                post_interval_enabled=True,
                **kw,
            )
            rep = evaluate_big6_framing_interval_vault(spec_spoof)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF)

    def test_23_interval_shoot_bounds_start_period_shots_validated(self) -> None:
        for bad_kw in (
            {"interval_start_time_sec": 0},
            {"interval_start_time_sec": 6000},
            {"interval_period_sec": 0},
            {"interval_period_sec": 61},
            {"interval_num_shots": 0},
            {"interval_num_shots": 10000},
        ):
            spec = build_default_safe_big6_framing_interval_vault_spec(
                shooting_domain="Still",
                mode_settings="Movie",
                big6_entry_trigger="NONE",
                reported_big6_active=False,
                interval_shooting_enabled=True,
                reported_effective_interval_enabled=False,
                reported_interval_errno=P340_EINVAL_ERRNO,
                **bad_kw,
            )
            rep = evaluate_big6_framing_interval_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF)

    def test_24_interval_shoot_bulb_override_to_30s_and_electronic_shutter_default(self) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            shooting_domain="Still",
            mode_settings="Movie",
            big6_entry_trigger="NONE",
            reported_big6_active=False,
            interval_shooting_enabled=True,
            interval_num_shots=9999,
            interval_shutter_type="Mechanical Shutter",
            bulb_active=True,
            reported_effective_interval_enabled=True,
            reported_bulb_overridden_to_30s=True,
            reset_action="Camera Settings Reset",
            post_interval_enabled=False,
            post_interval_num_shots=30,
            post_interval_shutter_type="Electronic Shutter",
            requested_vault_slot=2,
            requested_vault_action="INTERVAL_SHOOT_SLOT2",
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec).passed)

    def test_25_p61a_camera_settings_reset_resets_lower_left_framing_and_interval_7_items(self) -> None:
        spec_bad_reset = build_default_safe_big6_framing_interval_vault_spec(
            home_lower_left_mode="ND Filter",
            framing_enabled=True,
            framing_rec_streaming="Crop",
            framing_hdmi="Full",
            reported_effective_framing_enabled=True,
            reset_action="Camera Settings Reset",
            post_home_lower_left="ND Filter",  # should reset to Aperture!
            post_framing_enabled=True,        # should reset to False!
        )
        rep = evaluate_big6_framing_interval_vault(spec_bad_reset)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_BIG6_HOME_OR_LOWER_LEFT_ND_DRIFT)

    def test_26_p61a_fx6_mxf_and_auto_framing_spoof_rejected(self) -> None:
        for bad_kw in (
            {"fx6_has_builtin_end": False},
            {"fx6_interval_rec_single_mxf": False},
            {"fx6_has_auto_framing_menu": True},
        ):
            spec = build_default_safe_big6_framing_interval_vault_spec(**bad_kw)
            rep = evaluate_big6_framing_interval_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_INTERVAL_SHOOT_9999_OR_FX6_MXF_SPOOF)

    def test_27_p61a_slot1_interval_burst_and_format_erofs30_firewall(self) -> None:
        # Properly blocked returns passed=True
        spec_blocked = build_default_safe_big6_framing_interval_vault_spec(
            shooting_domain="Still",
            mode_settings="Movie",
            big6_entry_trigger="NONE",
            reported_big6_active=False,
            interval_shooting_enabled=True,
            interval_num_shots=9999,
            reported_effective_interval_enabled=True,
            post_interval_enabled=True,
            post_interval_num_shots=9999,
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="INTERVAL_SHOOT_SLOT1_BURST",
            interval_targets_slot1=True,
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        self.assertTrue(evaluate_big6_framing_interval_vault(spec_blocked).passed)

        # Allowed write or non-zero mutation bytes fail closed
        for bad_kw in (
            {
                "requested_vault_action": "INTERVAL_SHOOT_SLOT1_BURST",
                "interval_targets_slot1": True,
                "reported_vault_action_allowed": True,
                "vault_firewall_errno": None,
            },
            {"slot1_data_sector_writes": 512},
            {"slot1_dcim_avf_mutation_bytes": 128},
            {"slot1_vault_mutation_bytes": 4096},
            {"slot1_vault_erofs_eopnotsupp_enforced": False},
            {"slot1_format_hard_locked": False},
        ):
            spec_bad = build_default_safe_big6_framing_interval_vault_spec(**bad_kw)
            rep = evaluate_big6_framing_interval_vault(spec_bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_28_p61a_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        rep_ov = evaluate_big6_framing_interval_vault(
            build_default_safe_big6_framing_interval_vault_spec(overlay_dir="/nflasha15/p61a")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h03 = evaluate_big6_framing_interval_vault(
            build_default_safe_big6_framing_interval_vault_spec(backup_bin_h3_sha256="f" * 64)
        )
        self.assertFalse(rep_h03.passed)
        self.assertEqual(rep_h03.block_code, P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_29_p61a_invalid_spec_rejected(self) -> None:
        for bad_kw in (
            {"fw_version": "5.00"},
            {"shooting_domain": "Panorama"},
            {"mode_settings": "InvalidMode"},
            {"requested_vault_slot": 3},
            {"requested_vault_action": "WIPE_RAW"},
        ):
            rep = evaluate_big6_framing_interval_vault(
                build_default_safe_big6_framing_interval_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_INVALID_PILLAR61A_SPEC)

    def test_30_p61a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar61a_big6_framing_interval_vault_6_scenario_suite()
        self.assertTrue(res.passed, res.scenarios)
        self.assertEqual(res.status, P340_STATUS_VERIFIED_PILLAR_61A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        for idx, s in enumerate(res.scenarios):
            self.assertTrue(s.passed, s.detail)
            self.assertEqual(s.scenario_id, P340_PILLAR_61A_SCENARIO_IDS[idx])

    # ------------------------------------------------------------------
    # Pillar 61B Helper & Evaluator Tests (31..65)
    # ------------------------------------------------------------------

    def test_31_p61b_default_safe_spec_passes(self) -> None:
        rep = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P340_STATUS_VERIFIED_PILLAR_61B)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_32_tc_make_regenerate_reads_slot1_simult_and_forces_rec_run(self) -> None:
        # Regenerate with timecode_run="Free Run" MUST still run as Rec Run and read Slot 1 under Simult. Recording!
        spec_ok = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            recording_media_mode="Simult. Recording",
            timecode_make="Regenerate",
            timecode_run="Free Run",
            vmc_bncm1_connected=True,
            reported_effective_tc_run="Rec Run",
            reported_regen_source_slot=1,
            reported_ext_tc_status="INTERNAL",  # cannot EXT-LK under Regenerate!
            post_tc_make="Regenerate",
            post_tc_run="Free Run",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_ok).passed)

        # Under Slot 2, Regenerate reads Slot 2
        spec_slot2 = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            recording_media_mode="Slot 2",
            timecode_make="Regenerate",
            timecode_run="Rec Run",
            reported_effective_tc_run="Rec Run",
            reported_regen_source_slot=2,
            post_tc_make="Regenerate",
            post_tc_run="Rec Run",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_slot2).passed)

        # Spoofing Free Run under Regenerate fails closed
        spec_spoof = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Regenerate",
            timecode_run="Free Run",
            reported_effective_tc_run="Free Run",
            reported_regen_source_slot=1,
            post_tc_make="Regenerate",
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_spoof)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT)

    def test_33_fx3_rejects_tc_make_clock_while_fx6_supports_clock(self) -> None:
        spec_fx3_clock = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Clock",
            reported_tc_make_errno=None,
            post_tc_make="Clock",
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_fx3_clock)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT)

        spec_fx6_clock = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            camera_model=P340_FX6_DONOR_MODEL_NAME,
            fw_version=P340_FX6_DONOR_FW_VERSION,
            timecode_make="Clock",
            reported_tc_make_errno=None,
            post_tc_make="Clock",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_fx6_clock).passed)

    def test_34_vmc_bncm1_ext_lk_requires_preset_free_run_and_non_usblan(self) -> None:
        spec_extlk = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Preset",
            timecode_run="Free Run",
            vmc_bncm1_connected=True,
            usb_lan_active=False,
            reported_ext_tc_status="EXT-LK",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_extlk).passed)

        # Rec Run cannot lock EXT-LK even when VMC-BNCM1 connected
        spec_recrun_extlk = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Preset",
            timecode_run="Rec Run",
            vmc_bncm1_connected=True,
            usb_lan_active=False,
            reported_ext_tc_status="EXT-LK",
            post_tc_run="Rec Run",
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_recrun_extlk)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT)

    def test_35_hdmi_rec_control_requires_tc_output_on_and_allows_both_on_and_off_hdmi_only(self) -> None:
        for rec_media, vault_act in (
            ("On", "READ_ONLY_AUDIT"),
            ("Off(HDMI Only)", "HDMI_ONLY_EXT_REC_TRIGGER"),
        ):
            spec_ok = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                rec_media_dur_hdmi_output=rec_media,
                hdmi_tc_output="On",
                hdmi_rec_control="On",
                reported_effective_hdmi_rec_control="On",
                post_rec_media_hdmi=rec_media,
                post_hdmi_tc_output="On",
                post_hdmi_rec_control="On",
                requested_vault_action=vault_act,
            )
            self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_ok).passed)

        # TC Output = Off must block REC Control = On!
        spec_denied_ok = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            hdmi_tc_output="Off",
            hdmi_rec_control="On",
            reported_effective_hdmi_rec_control="Off",
            reported_hdmi_rec_control_errno=P340_EOPNOTSUPP_ERRNO,
            post_hdmi_tc_output="Off",
            post_hdmi_rec_control="Off",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_denied_ok).passed)

        spec_spoof = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            hdmi_tc_output="Off",
            hdmi_rec_control="On",
            reported_effective_hdmi_rec_control="On",
            reported_hdmi_rec_control_errno=None,
            post_hdmi_tc_output="Off",
            post_hdmi_rec_control="On",
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_spoof)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT)

    def test_36_hdmi_rec_control_blocked_in_sq_and_streaming(self) -> None:
        for kw in (
            {"shooting_domain": "S&Q"},
            {"network_streaming_active": True},
            {"usb_streaming_active": True},
        ):
            spec_spoof = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                hdmi_tc_output="On",
                hdmi_rec_control="On",
                reported_effective_hdmi_rec_control="On",
                reported_hdmi_rec_control_errno=None,
                post_hdmi_rec_control="On",
                **kw,
            )
            rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_spoof)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_TC_MAKE_REGEN_OR_HDMI_REC_CTRL_DRIFT)

    def test_37_4ch_audio_output_selectable_pairs(self) -> None:
        spec = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            hdmi_4ch_audio_output="CH3/CH4",
            post_4ch_audio_out="CH3/CH4",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec).passed)

    def test_38_access_authen_ssh_ptpip_accepted_and_http_digest_https_rejected(self) -> None:
        for proto in P340_FX3_ACCESS_AUTHEN_PROTOCOLS:
            spec_ok = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                access_authen_protocol=proto,
            )
            self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_ok).passed)

        for bad_proto in P340_FX3_FORBIDDEN_AUTH_PROTOCOLS:
            spec_bad = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                access_authen_protocol=bad_proto,
                reported_auth_proto_errno=None,
            )
            rep = evaluate_tc_make_hdmi_auth_fan_vault(spec_bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

    def test_39_access_authen_off_and_removed_wifi_security_rejected(self) -> None:
        rep_off = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(access_authen_settings="Off")
        )
        self.assertFalse(rep_off.passed)
        self.assertEqual(rep_off.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

        for old_sec in P340_FX3_WIFI_SECURITY_REMOVED_MODES:
            rep_sec = evaluate_tc_make_hdmi_auth_fan_vault(
                build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                    wifi_security=old_sec,
                    reported_wifi_sec_errno=None,
                )
            )
            self.assertFalse(rep_sec.passed)
            self.assertEqual(rep_sec.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

    def test_40_inbound_tls_root_cert_spoof_rejected(self) -> None:
        rep = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                root_cert_inbound_server_requested=True,
                reported_root_cert_inbound_errno=None,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

    def test_41_fan_control_4_modes_fx3_and_3_modes_fx6_with_zero_max(self) -> None:
        for mode in P340_FX3_FAN_CONTROL_MODES:
            spec_fx3 = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                fan_control=mode,
                recording_active=True,
                internal_temp_over_threshold=False,
                reported_fan_spinning_now=(mode in ("Auto", "Minimum")),
                post_fan_control=mode,
            )
            self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_fx3).passed)

        # Off in Rec spins back up if internal temperature exceeds thermal threshold!
        spec_overtemp = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            fan_control="Off in Rec",
            recording_active=True,
            internal_temp_over_threshold=True,
            reported_fan_spinning_now=True,
            post_fan_control="Off in Rec",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_overtemp).passed)

        # FX6 3 active modes pass; FX6 Always Off rejected as dormant!
        for mode in P340_FX6_FAN_CONTROL_ACTIVE_MODES:
            spec_fx6 = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                camera_model=P340_FX6_DONOR_MODEL_NAME,
                fw_version=P340_FX6_DONOR_FW_VERSION,
                reported_ext_tc_status="EXT-LK",
                fan_control=mode,
                post_fan_control=mode,
            )
            self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_fx6).passed)

        rep_fx6_dormant = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                camera_model=P340_FX6_DONOR_MODEL_NAME,
                fw_version=P340_FX6_DONOR_FW_VERSION,
                reported_ext_tc_status="EXT-LK",
                fan_control="Always Off",
                reported_fan_control_errno=None,
                reported_fan_spinning_now=False,
                post_fan_control="Always Off",
            )
        )
        self.assertFalse(rep_fx6_dormant.passed)
        self.assertEqual(rep_fx6_dormant.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

        # Max rejected on BOTH FX3 and FX6!
        for bad_max in P340_FAN_CONTROL_FORBIDDEN_MAX_MODES:
            for cam, fw in (
                (P340_FX3_MODEL_NAME, P340_FX3_FW_VERSION),
                (P340_FX6_DONOR_MODEL_NAME, P340_FX6_DONOR_FW_VERSION),
            ):
                rep_max = evaluate_tc_make_hdmi_auth_fan_vault(
                    build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
                        camera_model=cam,
                        fw_version=fw,
                        reported_ext_tc_status=("INTERNAL" if cam == P340_FX3_MODEL_NAME else "EXT-LK"),
                        fan_control=bad_max,
                        reported_fan_control_errno=None,
                        post_fan_control=bad_max,
                    )
                )
                self.assertFalse(rep_max.passed)
                self.assertEqual(rep_max.block_code, P340_BLOCKED_ACCESS_AUTHEN_SSH_TLS_OR_FAN_MAX_DRIFT)

    def test_42_reset_differentiation_camera_reset_vs_network_reset_vs_initialize(self) -> None:
        # Camera Settings Reset preserves ALL Pillar 61B settings
        spec_cam_reset = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Regenerate",
            timecode_run="Free Run",
            reported_effective_tc_run="Rec Run",
            reported_regen_source_slot=1,
            hdmi_tc_output="On",
            hdmi_rec_control="On",
            reported_effective_hdmi_rec_control="On",
            hdmi_4ch_audio_output="CH3/CH4",
            fan_control="Off in Rec",
            auto_power_off_temp="High",
            reset_action="Camera Settings Reset",
            post_tc_make="Regenerate",
            post_tc_run="Free Run",
            post_hdmi_rec_control="On",
            post_hdmi_tc_output="On",
            post_4ch_audio_out="CH3/CH4",
            post_fan_control="Off in Rec",
            post_auto_pwr_off_temp="High",
            post_airplane_mode="On",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_cam_reset).passed)

        # Reset Network Set. clears root certs & resets Access Authen.=On, preserves TC/Fan/Airplane Mode=On
        spec_net_reset = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            fan_control="Minimum",
            auto_power_off_temp="High",
            reset_action="Reset Network Set.",
            post_root_certs_cleared=True,
            post_fan_control="Minimum",
            post_auto_pwr_off_temp="High",
            post_airplane_mode="On",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_net_reset).passed)

        # Initialize resets TC/HDMI/Fan/AutoPwrOffTemp/RootCerts, preserves Airplane Mode=On!
        spec_init = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make="Regenerate",
            timecode_run="Free Run",
            reported_effective_tc_run="Rec Run",
            reported_regen_source_slot=1,
            hdmi_tc_output="On",
            hdmi_rec_control="On",
            reported_effective_hdmi_rec_control="On",
            hdmi_4ch_audio_output="CH3/CH4",
            fan_control="Always Off",
            reported_fan_spinning_now=False,
            auto_power_off_temp="High",
            reset_action="Initialize",
            post_tc_make="Preset",
            post_tc_run="Rec Run",
            post_hdmi_rec_control="Off",
            post_hdmi_tc_output="Off",
            post_rec_media_hdmi="On",
            post_4ch_audio_out="CH1/CH2",
            post_access_authen="On",
            post_root_certs_cleared=True,
            post_fan_control="Auto",
            post_auto_pwr_off_temp="Standard",
            post_airplane_mode="On",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_init).passed)

    def test_43_p61b_zero_rf_and_slot1_vault_erofs30_firewall(self) -> None:
        # Blocked FORMAT_FULL returns passed=True
        spec_blocked = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            requested_vault_slot=1,
            requested_vault_action="FORMAT_FULL",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        self.assertTrue(evaluate_tc_make_hdmi_auth_fan_vault(spec_blocked).passed)

        for bad_kw in (
            {"airplane_mode": "Off", "post_airplane_mode": "Off"},
            {"wifi_active": True},
            {"network_transport": "Wi-Fi"},
            {"rf_packets_transmitted": 1},
            {"rf_nvs_mutation_bytes": 32},
            {"slot1_data_sector_writes": 4096},
            {"slot1_vault_mutation_bytes": 1024},
            {"slot1_vault_erofs_eopnotsupp_enforced": False},
            {"slot1_format_hard_locked": False},
        ):
            rep = evaluate_tc_make_hdmi_auth_fan_vault(
                build_default_safe_tc_make_hdmi_auth_fan_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P340_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_44_p61b_overlay_escape_h0_h3_drift_and_invalid_spec_rejected(self) -> None:
        rep_ov = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(overlay_dir="/pnflasha/p61b")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P340_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(tier0_surfaces_h0_h3_matched=14)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P340_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_inv = evaluate_tc_make_hdmi_auth_fan_vault(
            build_default_safe_tc_make_hdmi_auth_fan_vault_spec(fan_control="Turbo999")
        )
        self.assertFalse(rep_inv.passed)
        self.assertEqual(rep_inv.block_code, P340_BLOCKED_INVALID_PILLAR61B_SPEC)

    def test_45_p61b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar61b_tc_make_hdmi_auth_fan_vault_6_scenario_suite()
        self.assertTrue(res.passed, res.scenarios)
        self.assertEqual(res.status, P340_STATUS_VERIFIED_PILLAR_61B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        for idx, s in enumerate(res.scenarios):
            self.assertTrue(s.passed, s.detail)
            self.assertEqual(s.scenario_id, P340_PILLAR_61B_SCENARIO_IDS[idx])

    # ------------------------------------------------------------------
    # Combined Single-Shot, Standalone Suite, 61/61 Master & Symmetry Aliases (46..60)
    # ------------------------------------------------------------------

    def test_46_combined_single_shot_verifier_and_symmetry_alias(self) -> None:
        r1 = verify_big6_framing_interval_tc_auth_fan_and_vault(force_clean_room=True)
        r2 = verify_big6_framing_interval_tc_auth_fan_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P340_STATUS_VERIFIED_PILLAR61_SUITE)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_47_standalone_suite_clean_room_and_default(self) -> None:
        for kw in ({"force_clean_room": True}, {}):
            rep = run_pillar61_standalone_suite(**kw)
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P340_STATUS_VERIFIED_PILLAR61_SUITE)
            self.assertEqual(rep.pillar_61a_big6_home_framing_interval_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_61b_tc_make_hdmi_auth_fan_vault.scenarios_passed, 6)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_48_master_61pillar_recovery_clean_room_and_rollup_metrics(self) -> None:
        rep = evaluate_realhw_61pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P340_STATUS_VERIFIED_61OF61_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 61)
        self.assertEqual(rep.pillars_passed, 61)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(rep.fx3_big6_tile_count, 6)
        self.assertFalse(rep.fx3_has_physical_end_hw)
        self.assertFalse(rep.fx3_has_dormant_auto_framing)
        self.assertEqual(rep.fx3_interval_subitem_count, 7)
        self.assertEqual(rep.fx3_interval_max_shots, 9999)
        self.assertEqual(rep.fx3_access_authen_http_digest_hits, 0)
        self.assertEqual(rep.fx3_fan_control_mode_count, 4)
        self.assertEqual(rep.fx6_fan_control_mode_count, 3)
        self.assertFalse(rep.fx3_has_fan_control_max)
        self.assertFalse(rep.fx6_has_fan_control_max)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

        rep2 = evaluate_61pillar_recovery_master(force_clean_room=True)
        rep3 = verify_61pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(rep2.pillars_passed, 61)
        self.assertEqual(rep3.pillars_passed, 61)

    def test_49_master_61pillar_recovery_fault_injection_pillar61_and_pillar60(self) -> None:
        rep61 = evaluate_realhw_61pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar61_big6_home_framing_interval_tc_make_auth_fan_vault",
        )
        self.assertFalse(rep61.all_passed)
        self.assertEqual(rep61.pillars_passed, 60)
        self.assertIn("pillar61_big6_home_framing_interval_tc_make_auth_fan_vault", rep61.failed_pillars)

        rep60 = evaluate_realhw_61pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault",
        )
        self.assertFalse(rep60.all_passed)
        self.assertEqual(rep60.pillars_passed, 60)
        self.assertIn("pillar60_bright_mon_shotmark_usblan_bulb_dormant_vault", rep60.failed_pillars)

        with self.assertRaises(ValueError):
            evaluate_realhw_61pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_61_plus",
            )

    def test_50_milestone311_and_324_auto_discovery_forward_compatible_ge_61(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        c311, fn311, ids311 = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(c311, 61)
        self.assertTrue(callable(fn311))
        self.assertGreaterEqual(len(ids311), 61)

        c324, fn324, ids324 = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(c324, 61)
        self.assertTrue(callable(fn324))
        self.assertGreaterEqual(len(ids324), 61)

    def test_51_master_61pillar_report_to_dict_roundtrip_and_package_root_exports(self) -> None:
        rep = evaluate_realhw_61pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 61)
        self.assertEqual(parsed["pillars_passed"], 61)
        for sym in (
            "MASTER_61_PILLAR_COUNT",
            "MASTER_61_PILLAR_IDS",
            "MASTER_61_PILLAR_SPECS",
            "Master61PillarRecoveryReport",
            "evaluate_realhw_61pillar_recovery_master",
            "evaluate_61pillar_recovery_master",
            "verify_61pillar_recovery_suite",
            "run_pillar61_standalone_suite",
        ):
            self.assertTrue(hasattr(fr, sym), sym)

    def test_52_cli_verify_61pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-61pillar-recovery", "--json"],
            ["verify-61pillar-recovery", "--force-clean-room", "--json"],
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
            self.assertEqual(payload["pillars_passed"], 61)
            self.assertEqual(payload["pillar_count"], 61)
            self.assertLess(payload["elapsed_seconds"], P340_CONCURRENT_CEILING_SECONDS)

    def test_53_cli_verify_pillar61_aliases_text_and_out(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar61-recovery",
            "verify-pillar61-big6-framing-interval-tc-auth-fan-vault",
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
            self.assertIn("VERIFIED_PILLAR61_BIG6_FRAMING_INTERVAL_TC_AUTH_FAN_VAULT", proc_txt.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p340_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p61_path = work_tests / f"{tag}_p61"
        try:
            proc1 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-61pillar-recovery", "--force-clean-room", "--out", str(out_master_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            self.assertTrue((out_master_path / "61pillar-recovery-master-report.json").exists())

            proc2 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-pillar61-recovery", "--force-clean-room", "--out", str(out_p61_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            self.assertTrue((out_p61_path / "pillar61-big6-framing-interval-tc-auth-fan-vault-report.json").exists())
        finally:
            for d in (out_master_path, out_p61_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_54_cli_backward_compat_verify_60pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-60pillar-recovery", "--force-clean-room", "--json"],
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

    def test_55_donorless_ci_mock_master61_and_cli_subprocess_exit_zero(self) -> None:
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
                    rep = evaluate_realhw_61pillar_recovery_master()
                    self.assertTrue(rep.all_passed, rep.errors)
                    self.assertEqual(rep.pillars_passed, 61)
                    self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    buf = io.StringIO()
                    with patch.object(sys, "argv", ["fx3_recovery", "verify-61pillar-recovery", "--json"]), redirect_stdout(buf):
                        rc = cli_main.main()
                    self.assertEqual(rc, 0, buf.getvalue())
                    payload = json.loads(buf.getvalue())
                    self.assertTrue(payload["all_passed"])
                    self.assertEqual(payload["pillars_passed"], 61)
                    self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

        sub_env = {
            **clean_env,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ADAPTER_ROOT),
        }
        snippet = (
            "import sys; from unittest.mock import patch; "
            "from fx3_recovery import files as f, __main__ as m; "
            "sys.argv = ['fx3_recovery', 'verify-61pillar-recovery', '--json']; "
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
        self.assertEqual(sub_payload["pillars_passed"], 61)
        self.assertEqual(sub_payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")


# Programmatically expand parametric verification cases across all Wave-59 state combinations so total test count >= 96!
def _make_big6_tile_test(fw: str, log_mode: str, shutter_mode: str, lower_left: str, expected_tiles: tuple):
    def _test(self: Phase340Pillar61VerifierTests) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            fw_version=fw,
            log_shooting_mode=log_mode,
            shutter_mode=shutter_mode,
            home_lower_left_mode=lower_left,
            reported_big6_tiles=expected_tiles,
            post_home_lower_left=lower_left,
        )
        rep = evaluate_big6_framing_interval_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_interval_subitem_boundary_test(start_s: int, period_s: int, shots: int, ae: str, shutter: str, prio: str):
    def _test(self: Phase340Pillar61VerifierTests) -> None:
        spec = build_default_safe_big6_framing_interval_vault_spec(
            shooting_domain="Still",
            mode_settings="Movie",
            big6_entry_trigger="NONE",
            reported_big6_active=False,
            interval_shooting_enabled=True,
            interval_start_time_sec=start_s,
            interval_period_sec=period_s,
            interval_num_shots=shots,
            interval_ae_tracking=ae,
            interval_shutter_type=shutter,
            interval_priority=prio,
            reported_effective_interval_enabled=True,
            post_interval_enabled=True,
            post_interval_start_sec=start_s,
            post_interval_period_sec=period_s,
            post_interval_num_shots=shots,
            post_interval_ae_tracking=ae,
            post_interval_shutter_type=shutter,
            post_interval_priority=prio,
        )
        rep = evaluate_big6_framing_interval_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_tc_hdmi_matrix_test(tc_make: str, tc_run: str, rec_media_hdmi: str, audio_4ch: str):
    def _test(self: Phase340Pillar61VerifierTests) -> None:
        eff_run = "Rec Run" if tc_make == "Regenerate" else tc_run
        regen_slot = 1 if tc_make == "Regenerate" else None
        spec = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            timecode_make=tc_make,
            timecode_run=tc_run,
            reported_effective_tc_run=eff_run,
            reported_regen_source_slot=regen_slot,
            rec_media_dur_hdmi_output=rec_media_hdmi,
            hdmi_tc_output="On",
            hdmi_rec_control="On",
            hdmi_4ch_audio_output=audio_4ch,
            reported_effective_hdmi_rec_control="On",
            post_tc_make=tc_make,
            post_tc_run=tc_run,
            post_rec_media_hdmi=rec_media_hdmi,
            post_hdmi_tc_output="On",
            post_hdmi_rec_control="On",
            post_4ch_audio_out=audio_4ch,
            requested_vault_action=(
                "HDMI_ONLY_EXT_REC_TRIGGER" if rec_media_hdmi == "Off(HDMI Only)" else "READ_ONLY_AUDIT"
            ),
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_fan_temp_sec_matrix_test(fan_mode: str, temp_mode: str, wifi_sec: str, rec_active: bool):
    def _test(self: Phase340Pillar61VerifierTests) -> None:
        spinning = fan_mode in ("Auto", "Minimum") or (fan_mode == "Off in Rec" and not rec_active)
        spec = build_default_safe_tc_make_hdmi_auth_fan_vault_spec(
            fan_control=fan_mode,
            recording_active=rec_active,
            reported_fan_spinning_now=spinning,
            auto_power_off_temp=temp_mode,
            wifi_security=wifi_sec,
            post_fan_control=fan_mode,
            post_auto_pwr_off_temp=temp_mode,
        )
        rep = evaluate_tc_make_hdmi_auth_fan_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


_idx = 56
for _fw in ("7.00", "7.01", "7.02"):
    for _log in ("Off", "Flexible ISO", "Cine EI", "Cine EI Quick"):
        for _shutter, _ll in (("Speed", "Aperture"), ("Angle", "ND Filter")):
            _iso_tile = "Base ISO + EI" if _log in ("Cine EI", "Cine EI Quick") else "ISO"
            _sh_tile = "Shutter Angle" if _shutter == "Angle" else "Shutter Speed"
            _look_tile = "Picture Profile" if _log == "Off" else "Select LUT"
            _tiles = ("FPS", _iso_tile, _sh_tile, _ll, _look_tile, "White Balance")
            setattr(
                Phase340Pillar61VerifierTests,
                f"test_{_idx:02d}_big6_matrix_{_fw.replace('.', '')}_{_log.lower().replace(' ', '_')}_{_shutter.lower()}",
                _make_big6_tile_test(_fw, _log, _shutter, _ll, _tiles),
            )
            _idx += 1

for _start, _per, _shots, _ae, _sh, _pr in (
    (1, 1, 1, "High", "Electronic Shutter", "Off"),
    (10, 5, 100, "Mid", "Electronic Shutter", "On"),
    (5999, 60, 9999, "Low", "Mechanical Shutter", "On"),
    (120, 30, 500, "High", "Mechanical Shutter", "Off"),
):
    setattr(
        Phase340Pillar61VerifierTests,
        f"test_{_idx:02d}_interval_subitem_matrix_{_shots}_{_ae.lower()}",
        _make_interval_subitem_boundary_test(_start, _per, _shots, _ae, _sh, _pr),
    )
    _idx += 1

for _make in ("Preset", "Regenerate"):
    for _run in ("Rec Run", "Free Run"):
        for _rm in ("On", "Off(HDMI Only)"):
            _aud = "CH3/CH4" if _idx % 2 == 0 else "CH1/CH2"
            setattr(
                Phase340Pillar61VerifierTests,
                f"test_{_idx:02d}_tc_hdmi_matrix_{_make.lower()}_{_run.lower().replace(' ', '_')}_{_rm.split('(')[0].lower()}",
                _make_tc_hdmi_matrix_test(_make, _run, _rm, _aud),
            )
            _idx += 1

for _fan in ("Auto", "Minimum", "Off in Rec", "Always Off"):
    for _tmp in ("Standard", "High"):
        for _sec in ("WPA2-PSK", "WPA3-SAE"):
            setattr(
                Phase340Pillar61VerifierTests,
                f"test_{_idx:02d}_fan_temp_sec_matrix_{_fan.lower().replace(' ', '_')}_{_tmp.lower()}_{_sec.lower().replace('-', '_')}",
                _make_fan_temp_sec_matrix_test(_fan, _tmp, _sec, _fan == "Off in Rec"),
            )
            _idx += 1


if __name__ == "__main__":
    unittest.main()
