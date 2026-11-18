"""Phase 344 (Pillar 62 & 62/62 Milestone) unit tests:
Wave-60 [Rec. Media Settings] architectural evolution from dormant Alpha
[Prioritize Rec. Media] (_f 0x719e, 0 hits in FX3 appFw.so) to split Reset-immune
Still/Movie [Recording Media] (ZERO Movie Sort Recording, Simult. Recording same-FS
gate) + Reset-immune [Auto Switch Media] (BKID_APP_setting_relay_rec) & Tier-0 Slot-1
spillover guard (EROFS=30) vs FX6 Project > Simul Rec + Rec Button Set + hard exclusions;
SDXC V60/V90 vs CFexpress Type A VPG200 (0xe228) / VPG400 (0xe224/0xe93f/0xe9aa) card
speed-gate matrix; [Proxy Settings] (sq_proxy, 0 PRM_HAITA_*proxy* strings, XAVC S HD 6M
8bit & XAVC HS HD 9M/16M 10bit, XAVC S-I DCI 4K allowed vs 119.88p/100p & S&Q 120/100fps
lockout, M4ROOT/SUB/*S03.MP4 coupled Delete/Protect & Slot-1 EROFS=30); [Creators' Cloud] /
[C3 Portal] (* survives BOTH Camera Settings Reset AND Initialize, FTP mutex, Ver. 7.00+
Clip Flag filter), [Cnct. while Power OFF] (BKID_APP_extern_menu_cnct_while_power_off,
_f 0x6ab3, BLE energized while physical POWER switch OFF -> dual Zero-RF lock Airplane=On
+ Off vs Bluetooth-less FX6), and [My Menu] 6x7=42 NVRAM slots (NOT 30/36, Playback
disallowed) vs FX6 20-item User Menu with Lock (Multi-selector + MENU, 4-digit PIN,
excluded from All File & Scene File) + Tier-0 Slot-1 EROFS=30 Vault Firewall.
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
    MASTER_62_PILLAR_COUNT,
    MASTER_62_PILLAR_IDS,
    MASTER_62_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P344_AIRPLANE_MODE_FORCED_ON,
    P344_ALWAYS_CONNECTED_F_RESID16,
    P344_AUTO_SWITCH_MEDIA_DEFAULT,
    P344_AUTO_SWITCH_MEDIA_F_RESID16,
    P344_AUTO_SWITCH_MEDIA_MODES,
    P344_BASE_CFEXPRESS_VPG200_RESID16,
    P344_BASE_CFEXPRESS_VPG400_RESID16S,
    P344_BKID_ALWAYS_CONNECTED,
    P344_BKID_AUTO_SWITCH_MEDIA,
    P344_BKID_CLOUD_CONNECTION,
    P344_BKID_CNCT_WHILE_POWER_OFF,
    P344_BKID_DISPLAY_FROM_MYMENU,
    P344_BKID_MOVIE_RECORDING_MEDIA,
    P344_BKID_SQ_PROXY_FILE_FORMAT,
    P344_BKID_SQ_PROXY_RECORDING,
    P344_BKID_SQ_PROXY_RECORD_SETTING,
    P344_BKID_STILL_RECORDING_MEDIA,
    P344_BLOCKED_CARD_SPEED_VPG200_VPG400_GATE_DRIFT,
    P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF,
    P344_BLOCKED_INVALID_PILLAR62A_SPEC,
    P344_BLOCKED_INVALID_PILLAR62B_SPEC,
    P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF,
    P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT,
    P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT,
    P344_BLOCKED_SAFETY_POLICY_VIOLATION,
    P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL,
    P344_C3_PORTAL_PRIVATE_F_RESID16,
    P344_C3_PORTAL_SHARE_F_RESID16,
    P344_CARD_MEDIA_TYPES,
    P344_CLIP_FLAG_FILTERS,
    P344_CLOUD_BT_AIRPLANE_L10N_DEFECT_G_RESID16,
    P344_CLOUD_CONNECTION_F_RESID16,
    P344_CLOUD_INFORMATION_F_RESID16,
    P344_CNCT_WHILE_POWER_OFF_F_RESID16,
    P344_CONCURRENT_CEILING_SECONDS,
    P344_CREATORS_CLOUD_G_RESID16,
    P344_DISPLAY_FROM_MYMENU_F_RESID16,
    P344_DONOR_INSPECT_BUDGET_SECONDS,
    P344_DORMANT_PRIORITIZE_REC_MEDIA_F_RESID16,
    P344_DORMANT_PRIORITIZE_SYMBOLS,
    P344_DORMANT_PROXY_16M_8BIT_F_RESID16,
    P344_DORMANT_SORT_JPEG_RAW_F_RESID16,
    P344_DORMANT_SORT_RAW_JPEG_F_RESID16,
    P344_EBUSY_ERRNO,
    P344_EINVAL_ERRNO,
    P344_ENV_CLEAN_ROOM_TEST,
    P344_EOPNOTSUPP_ERRNO,
    P344_EROFS_ERRNO,
    P344_FAST_CLI_BUDGET_SECONDS,
    P344_FILESYSTEM_TYPES,
    P344_FX3_APPFW_PRIORITIZE_HIT_COUNT,
    P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT,
    P344_FX3_FW_VERSION,
    P344_FX3_HELPGUIDE_ID,
    P344_FX3_MODEL_ID,
    P344_FX3_MODEL_NAME,
    P344_FX3_MYMENU_ALLOWED_DOMAINS,
    P344_FX3_MYMENU_DORMANT_BOUNDARY_HITS,
    P344_FX3_MYMENU_ITEMS_PER_PAGE,
    P344_FX3_MYMENU_PAGES,
    P344_FX3_MYMENU_SLOT_SYMBOLS,
    P344_FX3_MYMENU_SUBITEMS,
    P344_FX3_MYMENU_TOTAL_SLOTS,
    P344_FX6_BKID_PROXY_LUT,
    P344_FX6_BKID_SIMUL_REC,
    P344_FX6_BKID_USER_MENU_ONLY,
    P344_FX6_DONOR_FW_VERSION,
    P344_FX6_DONOR_MODEL_NAME,
    P344_FX6_HAS_BLUETOOTH_HARDWARE,
    P344_FX6_PROXY_BITRATE_MBPS,
    P344_FX6_PROXY_CHUNK_DURATIONS,
    P344_FX6_PROXY_EXCLUSIONS,
    P344_FX6_PROXY_RESOLUTION,
    P344_FX6_REC_BUTTON_CONTROLS,
    P344_FX6_SIMUL_REC_EXCLUSIONS,
    P344_FX6_USER_MENU_LOCK_CHORD,
    P344_FX6_USER_MENU_LOCK_DEFAULT_PIN,
    P344_FX6_USER_MENU_LOCK_PIN_DIGITS,
    P344_FX6_USER_MENU_MAX_ITEMS,
    P344_MOVIE_FILE_FORMATS,
    P344_MOVIE_RECORDING_MEDIA_MODES,
    P344_MYMENU_ADD_ITEM_F_RESID16,
    P344_MYMENU_DELETE_ALL_F_RESID16,
    P344_MYMENU_DELETE_ITEM_F_RESID16,
    P344_MYMENU_DELETE_PAGE_F_RESID16,
    P344_MYMENU_G_RESID16,
    P344_MYMENU_SORT_ITEM_F_RESID16,
    P344_NOMINAL_BUDGET_SECONDS,
    P344_PILLAR_62A_SCENARIO_IDS,
    P344_PILLAR_62B_SCENARIO_IDS,
    P344_POWER_OFF_BLE_FORCED_OFF,
    P344_PRM_HAITA_CLOUD_FTP_SYMBOL,
    P344_PRM_HAITA_RELAY_REC_SLOT1_LOCKED_SYMBOL,
    P344_PRM_HAITA_RELAY_REC_SLOT1_RO_SYMBOL,
    P344_PROXY_16M_10BIT_F_RESID16,
    P344_PROXY_6M_8BIT_F_RESID16,
    P344_PROXY_9M_10BIT_F_RESID16,
    P344_PROXY_CFE_SUBDIR,
    P344_PROXY_DISALLOWED_MOVIE_FPS,
    P344_PROXY_DISALLOWED_SQ_SENSOR_FPS,
    P344_PROXY_DORMANT_REC_SETTINGS,
    P344_PROXY_FILE_FORMATS,
    P344_PROXY_FILE_FORMAT_DEFAULT,
    P344_PROXY_FILE_FORMAT_F_RESID16,
    P344_PROXY_FILE_SUFFIX,
    P344_PROXY_RECORDING_DEFAULT,
    P344_PROXY_RECORDING_F_RESID16,
    P344_PROXY_REC_SETTINGS_F_RESID16,
    P344_PROXY_REC_SETTINGS_XAVC_HS_HD,
    P344_PROXY_REC_SETTINGS_XAVC_S_HD,
    P344_PROXY_SD_SUBDIR,
    P344_PROXY_SETTINGS_F_RESID16,
    P344_RECORDING_MEDIA_DEFAULT,
    P344_RECORDING_MEDIA_F_RESID16,
    P344_REC_MEDIA_SETTINGS_F_RESID16,
    P344_RF_PACKETS_TRANSMITTED,
    P344_SAFE_WIRED_TRANSPORT,
    P344_SIMULT_RECORDING_F_RESID16,
    P344_SLOT1_DATA_SECTOR_WRITES,
    P344_SLOT1_FORMAT_HARD_LOCKED,
    P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P344_SORT_RECORDING_F_RESID16,
    P344_STATUS_VERIFIED_62OF62_AGGREGATOR,
    P344_STATUS_VERIFIED_PILLAR62_SUITE,
    P344_STATUS_VERIFIED_PILLAR_62A,
    P344_STATUS_VERIFIED_PILLAR_62B,
    P344_STILL_RECORDING_MEDIA_MODES,
    P344_SUPPORTED_CARD_MEDIA_TYPES,
    P344_TIER0_SURFACE_COUNT,
    P344_UIBIZ_BLE_POWER_SYMBOL,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PHASE344_MASTER_SCHEMA,
    PHASE344_PHASE_NUMBER,
    PHASE344_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_cloud_poweroff_ble_mymenu_vault_spec,
    build_default_safe_rec_media_autoswitch_proxy_vault_spec,
    compute_expected_cloud_poweroff_ble_mymenu_state,
    compute_expected_rec_media_autoswitch_proxy_state,
    evaluate_62pillar_recovery_master,
    evaluate_cloud_poweroff_ble_mymenu_vault,
    evaluate_realhw_62pillar_recovery_master,
    evaluate_rec_media_autoswitch_proxy_vault,
    inspect_phase344_donors_readonly,
    run_pillar62_standalone_suite,
    run_pillar62a_rec_media_autoswitch_proxy_vault_6_scenario_suite,
    run_pillar62b_cloud_poweroff_ble_mymenu_vault_6_scenario_suite,
    verify_62pillar_recovery_suite,
    verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault,
    verify_rec_media_autoswitch_proxy_cloud_mymenu_vault,
)
from fx3_recovery import (  # noqa: E402
    realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier as p62_mod,
)


class Phase344Pillar62VerifierTests(unittest.TestCase):
    """Comprehensive 4-mode unit tests for Phase 344 Pillar 62 & 62/62 Milestone."""

    # ------------------------------------------------------------------
    # Safety Redlines, Metadata & Wave-60 Empirical Constants (01..08)
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
        self.assertEqual(P344_RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(P344_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertTrue(P344_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P344_POWER_OFF_BLE_FORCED_OFF)
        self.assertTrue(P344_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P344_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)

    def test_02_schema_and_62_pillar_metadata(self) -> None:
        self.assertEqual(PHASE344_PHASE_NUMBER, 344)
        self.assertEqual(
            PHASE344_SCHEMA,
            "realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier_v1",
        )
        self.assertEqual(PHASE344_MASTER_SCHEMA, "realhw_62pillar_recovery_master_v1")
        self.assertEqual(MASTER_62_PILLAR_COUNT, 62)
        self.assertEqual(len(MASTER_62_PILLAR_IDS), 62)
        self.assertEqual(len(MASTER_62_PILLAR_SPECS), 62)
        self.assertEqual(
            MASTER_62_PILLAR_IDS[-1],
            "pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault",
        )
        self.assertEqual(P344_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P344_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P344_FX3_FW_VERSION, "7.02")
        self.assertEqual(P344_FX3_HELPGUIDE_ID, "ilc/2210")

    def test_03_rec_media_and_dormant_prioritize_constants(self) -> None:
        self.assertEqual(P344_REC_MEDIA_SETTINGS_F_RESID16, (0x734D, 0x794A))
        self.assertEqual(P344_RECORDING_MEDIA_F_RESID16, (0x749D, 0x78BE))
        self.assertEqual(P344_SIMULT_RECORDING_F_RESID16, 0x7505)
        self.assertEqual(P344_SORT_RECORDING_F_RESID16, 0x7916)
        self.assertEqual(P344_AUTO_SWITCH_MEDIA_F_RESID16, 0x6DD9)
        self.assertEqual(P344_DORMANT_PRIORITIZE_REC_MEDIA_F_RESID16, 0x719E)
        self.assertEqual(P344_DORMANT_SORT_RAW_JPEG_F_RESID16, 0x710D)
        self.assertEqual(P344_DORMANT_SORT_JPEG_RAW_F_RESID16, 0x765B)
        self.assertEqual(P344_FX3_APPFW_PRIORITIZE_HIT_COUNT, 0)
        self.assertEqual(P344_BKID_STILL_RECORDING_MEDIA, "BKID_APP_setting_still_recording_media")
        self.assertEqual(P344_BKID_MOVIE_RECORDING_MEDIA, "BKID_APP_setting_movie_recording_media")
        self.assertEqual(P344_BKID_AUTO_SWITCH_MEDIA, "BKID_APP_setting_relay_rec")
        self.assertIn("media_read_only_state_slot1", P344_PRM_HAITA_RELAY_REC_SLOT1_RO_SYMBOL)
        self.assertIn("media_locked_state_slot1", P344_PRM_HAITA_RELAY_REC_SLOT1_LOCKED_SYMBOL)
        self.assertIn("Sort Recording", P344_STILL_RECORDING_MEDIA_MODES)
        self.assertNotIn("Sort Recording", P344_MOVIE_RECORDING_MEDIA_MODES)
        self.assertEqual(P344_RECORDING_MEDIA_DEFAULT, "Slot 1")
        self.assertEqual(P344_AUTO_SWITCH_MEDIA_DEFAULT, "Off")

    def test_04_card_speed_vpg200_vpg400_and_fx6_simul_constants(self) -> None:
        self.assertEqual(P344_BASE_CFEXPRESS_VPG200_RESID16, 0xE228)
        self.assertEqual(P344_BASE_CFEXPRESS_VPG400_RESID16S, (0xE224, 0xE93F, 0xE9AA, 0xEA64, 0xEA78))
        self.assertIn("CFexpress Type A VPG400", P344_SUPPORTED_CARD_MEDIA_TYPES)
        self.assertIn("CFexpress Type A VPG200", P344_SUPPORTED_CARD_MEDIA_TYPES)
        self.assertIn("CFexpress Type B", P344_CARD_MEDIA_TYPES)
        self.assertNotIn("CFexpress Type B", P344_SUPPORTED_CARD_MEDIA_TYPES)
        self.assertEqual(P344_FX6_BKID_SIMUL_REC, "BKID_APP_SETTING_SIMUL_REC")
        self.assertEqual(P344_FX6_REC_BUTTON_CONTROLS, ("Slot A", "Slot B"))
        self.assertEqual(len(P344_FX6_SIMUL_REC_EXCLUSIONS), 6)

    def test_05_proxy_sq_constants_and_dormant_8bit(self) -> None:
        self.assertEqual(P344_PROXY_SETTINGS_F_RESID16, 0x6E3F)
        self.assertEqual(P344_PROXY_RECORDING_F_RESID16, 0x6F19)
        self.assertEqual(P344_PROXY_FILE_FORMAT_F_RESID16, 0x6662)
        self.assertEqual(P344_PROXY_REC_SETTINGS_F_RESID16, 0x6AAD)
        self.assertEqual(P344_PROXY_9M_10BIT_F_RESID16, 0x611C)
        self.assertEqual(P344_PROXY_16M_10BIT_F_RESID16, 0x62A6)
        self.assertEqual(P344_PROXY_6M_8BIT_F_RESID16, 0x764C)
        self.assertEqual(P344_DORMANT_PROXY_16M_8BIT_F_RESID16, 0x6B8F)
        self.assertEqual(P344_BKID_SQ_PROXY_RECORDING, "BKID_APP_setting_sq_proxy_recording")
        self.assertEqual(P344_BKID_SQ_PROXY_FILE_FORMAT, "BKID_APP_setting_sq_proxy_file_format")
        self.assertEqual(P344_BKID_SQ_PROXY_RECORD_SETTING, "BKID_APP_setting_sq_proxy_record_setting")
        self.assertEqual(P344_FX3_APPFW_PRM_HAITA_PROXY_HIT_COUNT, 0)
        self.assertEqual(P344_PROXY_SD_SUBDIR, "/PRIVATE/M4ROOT/SUB")
        self.assertEqual(P344_PROXY_CFE_SUBDIR, "/M4ROOT/SUB")
        self.assertEqual(P344_PROXY_FILE_SUFFIX, "S03.MP4")
        self.assertEqual(P344_FX6_PROXY_RESOLUTION, "1920x1080")
        self.assertEqual(P344_FX6_PROXY_BITRATE_MBPS, 9)
        self.assertEqual(P344_FX6_PROXY_CHUNK_DURATIONS, ("Off", "30s", "1min", "2min"))

    def test_06_creators_cloud_and_poweroff_ble_constants(self) -> None:
        self.assertEqual(P344_CLOUD_CONNECTION_F_RESID16, 0x6E63)
        self.assertEqual(P344_CLOUD_INFORMATION_F_RESID16, 0x773E)
        self.assertEqual(P344_CREATORS_CLOUD_G_RESID16, 0x62B5)
        self.assertEqual(P344_C3_PORTAL_PRIVATE_F_RESID16, 0x7C55)
        self.assertEqual(P344_C3_PORTAL_SHARE_F_RESID16, 0x7C52)
        self.assertEqual(P344_CNCT_WHILE_POWER_OFF_F_RESID16, 0x6AB3)
        self.assertEqual(P344_ALWAYS_CONNECTED_F_RESID16, 0x6833)
        self.assertEqual(P344_CLOUD_BT_AIRPLANE_L10N_DEFECT_G_RESID16, 0x6476)
        self.assertEqual(P344_BKID_CLOUD_CONNECTION, "BKID_APP_setting_cloud_connection")
        self.assertEqual(P344_PRM_HAITA_CLOUD_FTP_SYMBOL, "PRM_HAITA_confirm_change_cloud_connection")
        self.assertEqual(P344_BKID_CNCT_WHILE_POWER_OFF, "BKID_APP_extern_menu_cnct_while_power_off")
        self.assertEqual(P344_BKID_ALWAYS_CONNECTED, "BKID_APP_setting_always_connected")
        self.assertEqual(P344_UIBIZ_BLE_POWER_SYMBOL, "UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER")
        self.assertEqual(P344_CLIP_FLAG_FILTERS, ("Off", "OK", "NG", "KEEP", "All"))
        self.assertFalse(P344_FX6_HAS_BLUETOOTH_HARDWARE)

    def test_07_mymenu_6x7_42_slots_and_fx6_user_menu_lock_constants(self) -> None:
        self.assertEqual(P344_MYMENU_G_RESID16, 0x6232)
        self.assertEqual(P344_DISPLAY_FROM_MYMENU_F_RESID16, 0x64F6)
        self.assertEqual(P344_MYMENU_ADD_ITEM_F_RESID16, 0x7122)
        self.assertEqual(P344_MYMENU_SORT_ITEM_F_RESID16, 0x7A11)
        self.assertEqual(P344_MYMENU_DELETE_ITEM_F_RESID16, 0x698D)
        self.assertEqual(P344_MYMENU_DELETE_PAGE_F_RESID16, 0x6B7C)
        self.assertEqual(P344_MYMENU_DELETE_ALL_F_RESID16, 0x6226)
        self.assertEqual(P344_BKID_DISPLAY_FROM_MYMENU, "BKID_APP_setting_display_from_mymenu")
        self.assertEqual(P344_FX3_MYMENU_PAGES, 6)
        self.assertEqual(P344_FX3_MYMENU_ITEMS_PER_PAGE, 7)
        self.assertEqual(P344_FX3_MYMENU_TOTAL_SLOTS, 42)
        self.assertEqual(P344_FX3_MYMENU_DORMANT_BOUNDARY_HITS, 0)
        self.assertEqual(len(P344_FX3_MYMENU_SLOT_SYMBOLS), 42)
        self.assertEqual(P344_FX3_MYMENU_SLOT_SYMBOLS[0], "BKID_APP_mymenu_group1_setting_list0")
        self.assertEqual(P344_FX3_MYMENU_SLOT_SYMBOLS[-1], "BKID_APP_mymenu_group6_setting_list6")
        self.assertNotIn("Playback", P344_FX3_MYMENU_ALLOWED_DOMAINS)
        self.assertEqual(len(P344_FX3_MYMENU_SUBITEMS), 6)
        self.assertEqual(P344_FX6_USER_MENU_MAX_ITEMS, 20)
        self.assertEqual(P344_FX6_BKID_USER_MENU_ONLY, "BKID_APP_SETTING_USER_MENU_ONLY")
        self.assertEqual(P344_FX6_USER_MENU_LOCK_CHORD, "Multi-selector + MENU")
        self.assertEqual(P344_FX6_USER_MENU_LOCK_PIN_DIGITS, 4)
        self.assertEqual(P344_FX6_USER_MENU_LOCK_DEFAULT_PIN, "0000")

    def test_08_errno_and_scenario_id_constants(self) -> None:
        self.assertEqual(P344_EBUSY_ERRNO, 16)
        self.assertEqual(P344_EINVAL_ERRNO, 22)
        self.assertEqual(P344_EROFS_ERRNO, 30)
        self.assertEqual(P344_EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(len(P344_PILLAR_62A_SCENARIO_IDS), 6)
        self.assertEqual(len(P344_PILLAR_62B_SCENARIO_IDS), 6)
        self.assertEqual(P344_SAFE_WIRED_TRANSPORT, "USB_LAN_CDC_NCM")
        self.assertEqual(P344_TIER0_SURFACE_COUNT, 16)

    # ------------------------------------------------------------------
    # 4-Mode Donor Inspection & work_root=None Guards (09..14)
    # ------------------------------------------------------------------

    def test_09_donor_inspection_4_modes_bounded_o_rdonly(self) -> None:
        # Mode 1: Clean-room via explicit arg
        snap_cr = inspect_phase344_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_cr.all_donors_present)
        self.assertEqual(snap_cr.donor_files_inspected, 17)
        self.assertTrue(snap_cr.under_2_0s_budget)
        self.assertEqual(snap_cr.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.matches_pinned for a in snap_cr.artifacts))

        # Mode 2: FX3_CLEAN_ROOM_TEST=1
        with patch.dict(os.environ, {P344_ENV_CLEAN_ROOM_TEST: "1"}):
            snap_env = inspect_phase344_donors_readonly()
            self.assertEqual(snap_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_env.donor_files_inspected, 17)

        # Mode 3: FX3_FX6_FORCE_CLEAN_ROOM=1
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap_force = inspect_phase344_donors_readonly()
            self.assertEqual(snap_force.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_force.donor_files_inspected, 17)

        # Mode 4: Auto mode (local donor or clean-room fallback)
        snap_auto = inspect_phase344_donors_readonly()
        self.assertIn(snap_auto.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap_auto.all_donors_present)
        self.assertEqual(snap_auto.donor_files_inspected, 17)
        self.assertTrue(snap_auto.under_2_0s_budget)
        self.assertLess(snap_auto.elapsed_seconds, P344_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertEqual(snap_auto.raw_firmware_bytes_leaked, 0)

    def test_10_work_root_none_guard_never_raises_typeerror(self) -> None:
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (P344_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(files_mod, "iter_donor_work_roots", return_value=(None,)):
                self.assertIsNone(p62_mod._resolve_phase344_donor_path(p62_mod.P344_DONOR_FX3_APPFW_702_RELPATH))
                self.assertFalse(p62_mod._master62_local_donors_available())
                snap = inspect_phase344_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 17)

    def test_11_donor_inspection_o_rdonly_local_sha_parity_when_present(self) -> None:
        if not p62_mod._master62_local_donors_available():
            self.skipTest("Local Wave-60 donors absent in this environment")
        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (P344_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            snap = inspect_phase344_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(all(a.read_mode == "LOCAL_DONOR_O_RDONLY" and a.matches_pinned for a in snap.artifacts))
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_12_donor_snapshot_to_dict_serializable(self) -> None:
        snap = inspect_phase344_donors_readonly(force_clean_room=True)
        raw = json.dumps(snap.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["donor_files_inspected"], 17)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_13_read_donor_bounded_nonexistent_path_safe(self) -> None:
        present, total_b, hdr_b, dkind, dsha, data = p62_mod._read_donor_readonly_bounded(
            "nonexistent/wave60/missing.bin"
        )
        self.assertFalse(present)
        self.assertEqual(total_b, 0)
        self.assertEqual(hdr_b, 0)
        self.assertEqual(dkind, "MISSING")
        self.assertEqual(dsha, "")
        self.assertEqual(data, b"")

    def test_14_safety_invariant_helper_returns_empty_by_default(self) -> None:
        self.assertEqual(p62_mod._safety_invariant_errors(), [])

    # ------------------------------------------------------------------
    # Pillar 62A: [Rec. Media Settings], VPG200/400, [Proxy Settings], Vault (15..30)
    # ------------------------------------------------------------------

    def test_15_pillar62a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec()
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P344_STATUS_VERIFIED_PILLAR_62A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.rec_media_split_and_autoswitch_guard_verified)
        self.assertTrue(rep.card_speed_vpg200_vpg400_gate_verified)
        self.assertTrue(rep.proxy_sq_dci4k_and_m4root_sub_verified)
        self.assertTrue(rep.slot1_vault_firewall_and_h0_h3_verified)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_16_pillar62a_dormant_prioritize_rec_media_zero_hits_and_eopnotsupp(self) -> None:
        # Correctly blocked with EOPNOTSUPP=95 -> passes guardrail check
        spec_ok = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            prioritize_rec_media_requested=True,
            reported_prioritize_errno=P344_EOPNOTSUPP_ERRNO,
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_ok).passed)

        # Spoofing prioritize_hits != 0 or accepting Prioritize Rec. Media without EOPNOTSUPP -> rejected
        spec_bad = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            prioritize_rec_media_requested=True,
            reported_prioritize_errno=None,
        )
        rep_bad = evaluate_rec_media_autoswitch_proxy_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT)

        spec_hits = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            fx3_appfw_prioritize_hits=1,
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_hits).passed)

    def test_17_pillar62a_movie_sort_recording_forbidden_still_sort_shared_required(self) -> None:
        # Movie Sort Recording properly returns EOPNOTSUPP=95
        spec_ok = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Sort Recording",
            reported_movie_sort_errno=P344_EOPNOTSUPP_ERRNO,
            post_movie_rec_media="Sort Recording",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_ok).passed)

        # Movie Sort Recording accepted without EOPNOTSUPP -> rejected
        spec_bad = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Sort Recording",
            reported_movie_sort_errno=None,
            post_movie_rec_media="Sort Recording",
        )
        rep_bad = evaluate_rec_media_autoswitch_proxy_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT)

        # Still Sort Recording requires shared JPEG/RAW quality/size settings
        spec_unshared = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain="Still",
            still_recording_media="Sort Recording",
            still_jpeg_raw_settings_shared=False,
            post_still_rec_media="Sort Recording",
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_unshared).passed)

    def test_18_pillar62a_simult_recording_requires_identical_filesystem_and_vault_lock(self) -> None:
        # Different FS (exFAT vs FAT32) properly returns EINVAL=22 and Slot 1 vault still blocks
        spec_mismatch_blocked = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Simult. Recording",
            slot1_filesystem="exFAT",
            slot2_filesystem="FAT32",
            reported_simult_fs_errno=P344_EINVAL_ERRNO,
            requested_vault_slot=1,
            requested_vault_action="SIMULT_REC_SLOT1_SLOT2",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
            post_movie_rec_media="Simult. Recording",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_mismatch_blocked).passed)

        # Different FS accepted without EINVAL -> rejected
        spec_bad = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Simult. Recording",
            slot1_filesystem="exFAT",
            slot2_filesystem="FAT32",
            reported_simult_fs_errno=None,
            requested_vault_slot=1,
            requested_vault_action="SIMULT_REC_SLOT1_SLOT2",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
            post_movie_rec_media="Simult. Recording",
        )
        rep_bad = evaluate_rec_media_autoswitch_proxy_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT)

    def test_19_pillar62a_auto_switch_media_reset_immune_and_slot1_spillover_guard(self) -> None:
        # Camera Settings Reset does NOT reset Recording Media or Auto Switch Media; Initialize DOES
        spec_reset = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            still_recording_media="Sort Recording",
            movie_recording_media="Slot 2",
            auto_switch_media="Off",
            reset_action="Camera Settings Reset",
            post_still_rec_media="Sort Recording",
            post_movie_rec_media="Slot 2",
            post_auto_switch_media="Off",
            post_proxy_recording="Off",
            post_proxy_file_format="XAVC S HD",
            post_proxy_rec_setting="6M 4:2:0 8bit",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_reset).passed)

        # Tier-0 Slot-1 Spillover properly blocked with EROFS=30 -> passed=True
        spec_spill_blocked = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Slot 2",
            auto_switch_media="On",
            slot2_full_or_missing=True,
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="AUTO_SWITCH_SPILLOVER_SLOT1",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
            post_auto_switch_media="On",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_spill_blocked).passed)

        # Spillover allowed onto Slot 1 -> REJECTED with SLOT1_VAULT_WRITE_FIREWALL
        spec_spill_breach = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_recording_media="Slot 2",
            auto_switch_media="On",
            slot2_full_or_missing=True,
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="AUTO_SWITCH_SPILLOVER_SLOT1",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
            slot1_data_sector_writes=4096,
            post_auto_switch_media="On",
        )
        rep_breach = evaluate_rec_media_autoswitch_proxy_vault(spec_spill_breach)
        self.assertFalse(rep_breach.passed)
        self.assertEqual(rep_breach.block_code, P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_20_pillar62a_fx6_simul_rec_and_chunk_mutual_exclusions(self) -> None:
        spec_fx6_ok = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_simul_rec_enabled=True,
            fx6_simul_exclusions_active=(),
            fx6_proxy_chunk_mode="Off",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_fx6_ok).passed)

        for excl in P344_FX6_SIMUL_REC_EXCLUSIONS:
            spec_excl = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                camera_model=P344_FX6_DONOR_MODEL_NAME,
                fw_version=P344_FX6_DONOR_FW_VERSION,
                fx6_simul_rec_enabled=True,
                fx6_simul_exclusions_active=(excl,),
            )
            rep_excl = evaluate_rec_media_autoswitch_proxy_vault(spec_excl)
            self.assertFalse(rep_excl.passed, excl)
            self.assertEqual(rep_excl.block_code, P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT)

        # Chunk active during Simul Rec -> blocked
        spec_chunk = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_simul_rec_enabled=True,
            fx6_proxy_chunk_mode="30s",
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_chunk).passed)

    def test_21_pillar62a_card_speed_sq_1200mbps_and_vpg200_vpg400_gates(self) -> None:
        # S&Q XAVC S-I 4K 1200Mbps on SDXC V90 MUST fail with EINVAL=22
        spec_sdxc_blocked = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain="S&Q",
            movie_file_format="XAVC S-I 4K",
            movie_bitrate_mbps=1200,
            sq_sensor_fps=120,
            rec_frame_rate_p=23.98,
            media_card_slot2_type="SDXC V90",
            reported_card_gate_errno=P344_EINVAL_ERRNO,
            proxy_recording="Off",
            proxy_file_format="XAVC S HD",
            proxy_rec_setting="6M 4:2:0 8bit",
            reported_effective_proxy_recording="Off",
            reported_proxy_errno=None,
            reported_proxy_subdir=P344_PROXY_SD_SUBDIR,
            reported_proxy_example_path=f"{P344_PROXY_SD_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
            post_proxy_recording="Off",
            post_proxy_file_format="XAVC S HD",
            post_proxy_rec_setting="6M 4:2:0 8bit",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_sdxc_blocked).passed)

        # S&Q XAVC S-I 4K 1200Mbps on VPG200 with Proxy=On emits VPG400_RECOMMENDED_DISABLE_PROXY
        spec_vpg200 = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain="S&Q",
            movie_file_format="XAVC S-I 4K",
            movie_bitrate_mbps=1200,
            sq_sensor_fps=60,
            rec_frame_rate_p=23.98,
            media_card_slot2_type="CFexpress Type A VPG200",
            reported_card_gate_errno=None,
            reported_card_gate_warning="VPG400_RECOMMENDED_DISABLE_PROXY",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_vpg200).passed)

        # CFexpress Type B is unsupported -> EOPNOTSUPP=95
        spec_type_b = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            media_card_slot2_type="CFexpress Type B",
            reported_card_gate_errno=P344_EOPNOTSUPP_ERRNO,
            reported_proxy_subdir=P344_PROXY_SD_SUBDIR,
            reported_proxy_example_path=f"{P344_PROXY_SD_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_type_b).passed)

        # Spoof missing warning on Movie XAVC S-I DCI 4K + Proxy + SDXC V90 -> rejected
        spec_bad_warn = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            media_card_slot2_type="SDXC V90",
            reported_card_gate_warning=None,
            reported_proxy_subdir=P344_PROXY_SD_SUBDIR,
            reported_proxy_example_path=f"{P344_PROXY_SD_SUBDIR}/C0001{P344_PROXY_FILE_SUFFIX}",
        )
        rep_bad_warn = evaluate_rec_media_autoswitch_proxy_vault(spec_bad_warn)
        self.assertFalse(rep_bad_warn.passed)
        self.assertEqual(rep_bad_warn.block_code, P344_BLOCKED_CARD_SPEED_VPG200_VPG400_GATE_DRIFT)

    def test_22_pillar62a_proxy_xavc_si_dci4k_allowed_vs_120p_100p_lockout(self) -> None:
        # XAVC S-I DCI 4K at 59.94p IS allowed for Proxy with CFexpress VPG400
        spec_dci4k = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            movie_file_format="XAVC S-I DCI 4K",
            movie_bitrate_mbps=600,
            rec_frame_rate_p=59.94,
            media_card_slot2_type="CFexpress Type A VPG400",
            proxy_recording="On",
            proxy_file_format="XAVC HS HD",
            proxy_rec_setting="16M 4:2:0 10bit",
            reported_effective_proxy_recording="On",
            post_proxy_recording="On",
            post_proxy_file_format="XAVC HS HD",
            post_proxy_rec_setting="16M 4:2:0 10bit",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_dci4k).passed)

        # Movie 119.88p / 100p locks out Proxy -> forced Off + EOPNOTSUPP=95
        for fps in (119.88, 100.0):
            spec_120_blocked = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="Movie",
                movie_file_format="XAVC S 4K",
                movie_bitrate_mbps=280,
                rec_frame_rate_p=fps,
                proxy_recording="On",
                reported_effective_proxy_recording="Off",
                reported_proxy_errno=P344_EOPNOTSUPP_ERRNO,
                post_proxy_recording="Off",
            )
            self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_120_blocked).passed, fps)

            # Spoofing Proxy On at 119.88p -> rejected
            spec_120_spoof = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                shooting_domain="Movie",
                movie_file_format="XAVC S 4K",
                movie_bitrate_mbps=280,
                rec_frame_rate_p=fps,
                proxy_recording="On",
                reported_effective_proxy_recording="On",
                reported_proxy_errno=None,
            )
            rep_spoof = evaluate_rec_media_autoswitch_proxy_vault(spec_120_spoof)
            self.assertFalse(rep_spoof.passed)
            self.assertEqual(rep_spoof.block_code, P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT)

    def test_23_pillar62a_proxy_sq_120_100fps_lockout_and_dormant_8bit_rejected(self) -> None:
        # S&Q 120fps locks out Proxy
        spec_sq = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain="S&Q",
            movie_file_format="XAVC S 4K",
            movie_bitrate_mbps=280,
            sq_sensor_fps=120,
            rec_frame_rate_p=23.98,
            proxy_recording="On",
            reported_effective_proxy_recording="Off",
            reported_proxy_errno=P344_EOPNOTSUPP_ERRNO,
            post_proxy_recording="Off",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_sq).passed)

        # Dormant 16M 4:2:0 8bit / 9M 4:2:0 8bit rejected with EOPNOTSUPP=95
        for dormant_setting in P344_PROXY_DORMANT_REC_SETTINGS:
            spec_dorm = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
                proxy_recording="On",
                proxy_file_format="XAVC HS HD",
                proxy_rec_setting=dormant_setting,
                reported_effective_proxy_recording="On",
                reported_proxy_errno=None,
            )
            rep_dorm = evaluate_rec_media_autoswitch_proxy_vault(spec_dorm)
            self.assertFalse(rep_dorm.passed)
            self.assertEqual(rep_dorm.block_code, P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT)

    def test_24_pillar62a_m4root_sub_lifecycle_coupled_delete_protect_and_erofs30(self) -> None:
        # In-camera playback of Proxy -> rejected
        spec_play = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            proxy_playable_in_camera=True,
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_play).passed)

        # Uncoupled delete/protect -> rejected
        spec_uncoupled = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            proxy_coupled_delete_protect=False,
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_uncoupled).passed)

        # Coupled Delete/Protect targeting Slot 1 Proxy -> properly blocked EROFS=30
        spec_del_blocked = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            requested_vault_slot=1,
            requested_vault_action="COUPLED_DELETE_PROTECT_SLOT1_PROXY",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_del_blocked).passed)

        # Coupled Delete/Protect bypassing Slot-1 firewall -> rejected
        spec_del_breach = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            requested_vault_slot=1,
            requested_vault_action="COUPLED_DELETE_PROTECT_SLOT1_PROXY",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
            slot1_dcim_m4root_avf_mutation_bytes=4096,
        )
        rep_breach = evaluate_rec_media_autoswitch_proxy_vault(spec_del_breach)
        self.assertFalse(rep_breach.passed)
        self.assertEqual(rep_breach.block_code, P344_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_25_pillar62a_prm_haita_proxy_hits_must_be_zero(self) -> None:
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            fx3_appfw_prm_haita_proxy_hits=1,
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_REC_MEDIA_PRIORITIZE_OR_AUTOSWITCH_DRIFT)

    def test_26_pillar62a_proxy_resets_under_camera_settings_reset(self) -> None:
        # Claiming Proxy survives Camera Settings Reset -> rejected
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            proxy_recording="On",
            reset_action="Camera Settings Reset",
            post_proxy_recording="On",
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_PROXY_SQ_DCI4K_OR_120P_LOCKOUT_DRIFT)

    def test_27_pillar62a_overlay_escape_rejected(self) -> None:
        for bad_dir in ("/setting/62a", "/dev/cnflasha/sub", "/mnt/emmc/test", "/nflasha/x"):
            spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(overlay_dir=bad_dir)
            rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_28_pillar62a_backup_bin_h0_h3_drift_rejected(self) -> None:
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            backup_bin_h3_sha256="f" * 64,
            tier0_surfaces_h0_h3_matched=15,
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_29_pillar62a_invalid_spec_rejected(self) -> None:
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            camera_model="ILCE-7M3",
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_INVALID_PILLAR62A_SPEC)

    def test_30_pillar62a_sd_vs_cfe_proxy_subdir_truth(self) -> None:
        spec_sd = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            media_card_slot2_type="SDXC V90",
            movie_file_format="XAVC S 4K",
            movie_bitrate_mbps=200,
            reported_proxy_subdir="/PRIVATE/M4ROOT/SUB",
            reported_proxy_example_path="/PRIVATE/M4ROOT/SUB/C0001S03.MP4",
        )
        self.assertTrue(evaluate_rec_media_autoswitch_proxy_vault(spec_sd).passed)

        spec_wrong = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            media_card_slot2_type="SDXC V90",
            movie_file_format="XAVC S 4K",
            movie_bitrate_mbps=200,
            reported_proxy_subdir="/M4ROOT/SUB",
            reported_proxy_example_path="/M4ROOT/SUB/C0001S03.MP4",
        )
        self.assertFalse(evaluate_rec_media_autoswitch_proxy_vault(spec_wrong).passed)

    # ------------------------------------------------------------------
    # Pillar 62B: [Creators' Cloud], [Cnct. while Power OFF], [My Menu] 42 vs FX6 20 Lock (31..44)
    # ------------------------------------------------------------------

    def test_31_pillar62b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec()
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P344_STATUS_VERIFIED_PILLAR_62B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.cloud_star_init_persist_and_poweroff_ble_verified)
        self.assertTrue(rep.mymenu_42slot_and_fx6_pin_lock_verified)
        self.assertTrue(rep.zero_rf_and_slot1_erofs30_vault_verified)
        self.assertTrue(rep.overlay_and_h0_h3_verified)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_32_pillar62b_creators_cloud_star_survives_initialize_unless_explicit_delete(self) -> None:
        # Cloud Connection * survives Initialize
        spec_init = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cloud_account_bound_star=True,
            reset_action="Initialize",
            post_cloud_account_bound_star=True,
            post_mymenu_count=0,
            post_display_from_mymenu="Off",
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_init).passed)

        # Falsely assuming Initialize wipes Cloud * -> rejected
        spec_wiped = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cloud_account_bound_star=True,
            reset_action="Initialize",
            post_cloud_account_bound_star=False,
            post_mymenu_count=0,
        )
        rep_wiped = evaluate_cloud_poweroff_ble_mymenu_vault(spec_wiped)
        self.assertFalse(rep_wiped.passed)
        self.assertEqual(rep_wiped.block_code, P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF)

        # Explicit deletion in Cloud Information DOES clear Cloud *
        spec_del = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cloud_account_bound_star=True,
            explicit_cloud_account_deleted=True,
            reset_action="Initialize",
            post_cloud_account_bound_star=False,
            post_mymenu_count=0,
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_del).passed)

    def test_33_pillar62b_cloud_ftp_mutex_and_clip_flag_ver_7_gate(self) -> None:
        # Simultaneous Cloud Connection + FTP -> blocked
        spec_ftp = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cloud_connection_enabled=True,
            ftp_transfer_enabled=True,
            reported_cloud_ftp_errno=P344_EBUSY_ERRNO,
        )
        rep_ftp = evaluate_cloud_poweroff_ble_mymenu_vault(spec_ftp)
        self.assertFalse(rep_ftp.passed)
        self.assertEqual(rep_ftp.block_code, P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF)

        # Clip Flag filter on FW 6.02 (< 7.00) -> blocked
        spec_old_fw = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            fw_version="6.02",
            cloud_clip_flag_filter="KEEP",
            reported_clip_flag_errno=P344_EOPNOTSUPP_ERRNO,
        )
        self.assertFalse(evaluate_cloud_poweroff_ble_mymenu_vault(spec_old_fw).passed)

    def test_34_pillar62b_cnct_while_power_off_ble_rf_hazard_rejected(self) -> None:
        # Physical switch OFF does NOT prevent BLE TX when Cnct. while Power OFF = On!
        spec_ble_leak = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            bluetooth_paired=True,
            cnct_while_power_off="On",
            power_switch_state="OFF",
            airplane_mode="Off",
            post_airplane_mode="Off",
            post_cnct_while_power_off="On",
            reported_ble_energized_while_power_off=True,
            network_transport="BLE",
            rf_packets_transmitted=8,
        )
        rep_leak = evaluate_cloud_poweroff_ble_mymenu_vault(spec_ble_leak)
        self.assertFalse(rep_leak.passed)
        self.assertEqual(rep_leak.block_code, P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF)

        # Even if Airplane Mode = On, Cnct. while Power OFF = On violates dual Zero-RF bench policy
        spec_half_lock = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cnct_while_power_off="On",
            post_cnct_while_power_off="On",
            airplane_mode="On",
            post_airplane_mode="On",
        )
        rep_half = evaluate_cloud_poweroff_ble_mymenu_vault(spec_half_lock)
        self.assertFalse(rep_half.passed)
        self.assertEqual(rep_half.block_code, P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_35_pillar62b_cnct_while_power_off_resets_only_on_network_reset_or_init(self) -> None:
        # Reset Network Set. clears Cnct. while Power OFF -> Off, preserves Airplane Mode = On and My Menu
        spec_net_reset = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            cnct_while_power_off="On",
            post_cnct_while_power_off="Off",
            reset_action="Reset Network Set.",
            airplane_mode="On",
            post_airplane_mode="On",
            mymenu_registered_count=42,
            post_mymenu_count=42,
        )
        # Note: spec has cnct_while_power_off="On" initially, so Zero-RF guard flags pre-reset state!
        self.assertFalse(evaluate_cloud_poweroff_ble_mymenu_vault(spec_net_reset).passed)

        # Using state calculator directly verifies Reset Network Set. clears Cnct. while Power OFF
        st_net = compute_expected_cloud_poweroff_ble_mymenu_state(
            camera_model="ILME-FX3",
            fw_version="7.02",
            cloud_connection_enabled=True,
            cloud_account_bound_star=True,
            cloud_clip_flag_filter="OK",
            ftp_transfer_enabled=False,
            explicit_cloud_account_deleted=False,
            bluetooth_paired=True,
            cnct_while_power_off="On",
            power_switch_state="OFF",
            airplane_mode="On",
            wifi_active=False,
            cloud_upload_active=False,
            network_transport="USB_LAN_CDC_NCM",
            mymenu_page=6,
            mymenu_slot_index=6,
            mymenu_registered_count=42,
            mymenu_includes_playback_item=False,
            mymenu_display_from_mymenu="On",
            mymenu_delete_all_requested=False,
            fx6_user_menu_item_count=20,
            fx6_user_menu_only=False,
            fx6_user_menu_with_lock=False,
            fx6_lock_chord_used=P344_FX6_USER_MENU_LOCK_CHORD,
            fx6_lock_pin="0000",
            fx6_save_target="All File",
            reset_action="Reset Network Set.",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertEqual(st_net["post_cnct_while_power_off"], "Off")
        self.assertEqual(st_net["post_airplane_mode"], "On")
        self.assertEqual(st_net["post_mymenu_count"], 42)
        self.assertTrue(st_net["post_cloud_account_bound_star"])

        # Camera Settings Reset preserves Cnct. while Power OFF = On
        st_cam = compute_expected_cloud_poweroff_ble_mymenu_state(
            camera_model="ILME-FX3",
            fw_version="7.02",
            cloud_connection_enabled=False,
            cloud_account_bound_star=True,
            cloud_clip_flag_filter="OK",
            ftp_transfer_enabled=False,
            explicit_cloud_account_deleted=False,
            bluetooth_paired=False,
            cnct_while_power_off="On",
            power_switch_state="OFF",
            airplane_mode="On",
            wifi_active=False,
            cloud_upload_active=False,
            network_transport="USB_LAN_CDC_NCM",
            mymenu_page=6,
            mymenu_slot_index=6,
            mymenu_registered_count=42,
            mymenu_includes_playback_item=False,
            mymenu_display_from_mymenu="Off",
            mymenu_delete_all_requested=False,
            fx6_user_menu_item_count=20,
            fx6_user_menu_only=False,
            fx6_user_menu_with_lock=False,
            fx6_lock_chord_used=P344_FX6_USER_MENU_LOCK_CHORD,
            fx6_lock_pin="0000",
            fx6_save_target="All File",
            reset_action="Camera Settings Reset",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertEqual(st_cam["post_cnct_while_power_off"], "On")
        self.assertEqual(st_cam["post_mymenu_count"], 42)

    def test_36_pillar62b_fx6_bluetooth_less_hardware_contrast(self) -> None:
        spec_fx6 = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_has_bluetooth_hardware=False,
            fx6_user_menu_item_count=20,
            fx6_user_menu_only=True,
            fx6_user_menu_with_lock=True,
            fx6_lock_pin="1234",
            fx6_save_target="All File",
            reported_fx6_menu_exported=True,
            reported_fx6_lock_exported=False,
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_fx6).passed)

        # Spoofing Bluetooth hardware on FX6 -> rejected
        spec_spoof_bt = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_has_bluetooth_hardware=True,
        )
        rep_bt = evaluate_cloud_poweroff_ble_mymenu_vault(spec_spoof_bt)
        self.assertFalse(rep_bt.passed)
        self.assertEqual(rep_bt.block_code, P344_BLOCKED_CLOUD_INIT_PERSIST_OR_POWEROFF_BLE_RF)

    def test_37_pillar62b_mymenu_42_slots_vs_30_or_36_myth_bust(self) -> None:
        # Page 6 slot 6 (42nd slot) allowed
        spec_42 = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            mymenu_page=6,
            mymenu_slot_index=6,
            mymenu_registered_count=42,
            fx3_mymenu_slot_capacity=42,
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_42).passed)

        # Spoofing 30 or 36 capacity -> rejected
        for bad_cap in (30, 36):
            spec_bad_cap = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                fx3_mymenu_slot_capacity=bad_cap,
            )
            rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec_bad_cap)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF)

        # Boundary page 7 or slot 7 -> EINVAL=22 -> rejected
        spec_oob = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            mymenu_page=7,
            mymenu_slot_index=0,
            reported_mymenu_errno=None,
        )
        self.assertFalse(evaluate_cloud_poweroff_ble_mymenu_vault(spec_oob).passed)

    def test_38_pillar62b_mymenu_playback_disallowed_and_reset_immunity(self) -> None:
        spec_pb = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            mymenu_includes_playback_item=True,
            reported_mymenu_errno=P344_EOPNOTSUPP_ERRNO,
        )
        rep_pb = evaluate_cloud_poweroff_ble_mymenu_vault(spec_pb)
        self.assertFalse(rep_pb.passed)
        self.assertEqual(rep_pb.block_code, P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF)

        # Reset-immune across Camera Settings Reset and Reset Network Set.
        for ra in ("Camera Settings Reset", "Reset Network Set."):
            spec_ra = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
                reset_action=ra,
                mymenu_registered_count=42,
                mymenu_display_from_mymenu="On",
                post_mymenu_count=42,
                post_display_from_mymenu="On",
            )
            self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_ra).passed, ra)

    def test_39_pillar62b_fx6_user_menu_lock_pin_and_allfile_exclusion(self) -> None:
        # 21 items exceeds FX6 20-item cap -> rejected
        spec_21 = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_user_menu_item_count=21,
        )
        self.assertFalse(evaluate_cloud_poweroff_ble_mymenu_vault(spec_21).passed)

        # Invalid chord or non-4-digit PIN -> rejected
        spec_bad_pin = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_user_menu_with_lock=True,
            fx6_lock_pin="12A4",
        )
        self.assertFalse(evaluate_cloud_poweroff_ble_mymenu_vault(spec_bad_pin).passed)

        # Claiming User Menu with Lock exports into All File -> rejected
        spec_leak_lock = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_user_menu_with_lock=True,
            fx6_save_target="All File",
            reported_fx6_menu_exported=True,
            reported_fx6_lock_exported=True,
        )
        rep_leak = evaluate_cloud_poweroff_ble_mymenu_vault(spec_leak_lock)
        self.assertFalse(rep_leak.passed)
        self.assertEqual(rep_leak.block_code, P344_BLOCKED_MYMENU_42SLOT_OR_FX6_LOCK_SPOOF)

        # Scene File excludes BOTH User Menu and Lock
        spec_scene = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            camera_model=P344_FX6_DONOR_MODEL_NAME,
            fw_version=P344_FX6_DONOR_FW_VERSION,
            fx6_user_menu_with_lock=True,
            fx6_save_target="Scene File",
            reported_fx6_menu_exported=False,
            reported_fx6_lock_exported=False,
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_scene).passed)

    def test_40_pillar62b_slot1_format_full_erofs30_firewall(self) -> None:
        spec_blocked = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            requested_vault_slot=1,
            requested_vault_action="FORMAT_FULL",
            reported_vault_action_allowed=False,
            vault_firewall_errno="EROFS",
        )
        self.assertTrue(evaluate_cloud_poweroff_ble_mymenu_vault(spec_blocked).passed)

        spec_breach = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            requested_vault_slot=1,
            requested_vault_action="FORMAT_FULL",
            reported_vault_action_allowed=True,
            vault_firewall_errno=None,
            slot1_data_sector_writes=4096,
            slot1_vault_mutation_bytes=4096,
            slot1_vault_erofs_eopnotsupp_enforced=False,
        )
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec_breach)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_41_pillar62b_zero_rf_wifi_or_cloud_upload_rejected(self) -> None:
        spec_wifi = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            wifi_active=True,
            network_transport="Wi-Fi",
            rf_packets_transmitted=5,
        )
        rep_wifi = evaluate_cloud_poweroff_ble_mymenu_vault(spec_wifi)
        self.assertFalse(rep_wifi.passed)
        self.assertEqual(rep_wifi.block_code, P344_BLOCKED_ZERO_RF_OR_SLOT1_VAULT_WRITE_FIREWALL)

    def test_42_pillar62b_overlay_escape_rejected(self) -> None:
        spec = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(overlay_dir="/nflasha/62b")
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_43_pillar62b_h0_h3_drift_rejected(self) -> None:
        spec = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            backup_bin_h3_sha256="a" * 64,
        )
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_44_pillar62b_invalid_spec_rejected(self) -> None:
        spec = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            power_switch_state="SLEEP",
        )
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P344_BLOCKED_INVALID_PILLAR62B_SPEC)

    # ------------------------------------------------------------------
    # Combined Single-Shot, 6+6 Suites, 62/62 Master & CLI (45..55)
    # ------------------------------------------------------------------

    def test_45_combined_single_shot_verifier_and_alias(self) -> None:
        rep1 = verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault(force_clean_room=True)
        rep2 = verify_rec_media_autoswitch_proxy_cloud_mymenu_vault(force_clean_room=True)
        for rep in (rep1, rep2):
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P344_STATUS_VERIFIED_PILLAR62_SUITE)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_46_pillar62a_and_62b_6_scenario_suites(self) -> None:
        res_a = run_pillar62a_rec_media_autoswitch_proxy_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.status, P344_STATUS_VERIFIED_PILLAR_62A)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)

        res_b = run_pillar62b_cloud_poweroff_ble_mymenu_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.status, P344_STATUS_VERIFIED_PILLAR_62B)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)

    def test_47_pillar62_standalone_suite_normal_and_clean_room(self) -> None:
        for kw in ({}, {"force_clean_room": True}):
            rep = run_pillar62_standalone_suite(**kw)
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P344_STATUS_VERIFIED_PILLAR62_SUITE)
            self.assertEqual(rep.pillar_62a_rec_media_autoswitch_proxy_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_62b_cloud_poweroff_ble_mymenu_vault.scenarios_passed, 6)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_48_master_62pillar_recovery_clean_room_and_deterministic_sha(self) -> None:
        rep1 = evaluate_realhw_62pillar_recovery_master(force_clean_room=True)
        rep2 = evaluate_62pillar_recovery_master(force_clean_room=True)
        rep3 = verify_62pillar_recovery_suite(force_clean_room=True)
        for rep in (rep1, rep2, rep3):
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P344_STATUS_VERIFIED_62OF62_AGGREGATOR)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.pillar_count, 62)
            self.assertEqual(rep.pillars_passed, 62)
            self.assertEqual(rep.failed_pillars, ())
            self.assertTrue(rep.under_6s_budget)
            self.assertTrue(rep.nominal_under_4_0s)
            self.assertEqual(rep.fx3_appfw_prioritize_hits, 0)
            self.assertEqual(rep.fx3_appfw_prm_haita_proxy_hits, 0)
            self.assertFalse(rep.fx3_has_movie_sort_recording)
            self.assertTrue(rep.fx3_proxy_dci4k_allowed)
            self.assertTrue(rep.fx3_cloud_star_survives_initialize)
            self.assertTrue(rep.fx3_power_off_ble_forced_off)
            self.assertEqual(rep.fx3_mymenu_slot_capacity, 42)
            self.assertEqual(rep.fx3_mymenu_pages, 6)
            self.assertEqual(rep.fx3_mymenu_items_per_page, 7)
            self.assertEqual(rep.fx6_user_menu_max_items, 20)
            self.assertFalse(rep.fx6_has_bluetooth_hardware)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep1.master_62pillar_sha256, rep2.master_62pillar_sha256)
        self.assertEqual(rep1.master_62pillar_sha256, rep3.master_62pillar_sha256)

    def test_49_master_62pillar_recovery_fault_injection_pillar62_and_pillar61(self) -> None:
        rep62 = evaluate_realhw_62pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault",
        )
        self.assertFalse(rep62.all_passed)
        self.assertEqual(rep62.pillars_passed, 61)
        self.assertIn("pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault", rep62.failed_pillars)

        rep61 = evaluate_realhw_62pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar61_big6_home_framing_interval_tc_make_auth_fan_vault",
        )
        self.assertFalse(rep61.all_passed)
        self.assertEqual(rep61.pillars_passed, 61)
        self.assertIn("pillar61_big6_home_framing_interval_tc_make_auth_fan_vault", rep61.failed_pillars)

        with self.assertRaises(ValueError):
            evaluate_realhw_62pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_62_plus",
            )

    def test_50_milestone311_and_324_auto_discovery_forward_compatible_ge_62(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        c311, fn311, ids311 = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(c311, 62)
        self.assertTrue(callable(fn311))
        self.assertGreaterEqual(len(ids311), 62)

        c324, fn324, ids324 = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(c324, 62)
        self.assertTrue(callable(fn324))
        self.assertGreaterEqual(len(ids324), 62)

    def test_51_master_62pillar_report_to_dict_roundtrip_and_package_root_exports(self) -> None:
        rep = evaluate_realhw_62pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 62)
        self.assertEqual(parsed["pillars_passed"], 62)
        for sym in (
            "MASTER_62_PILLAR_COUNT",
            "MASTER_62_PILLAR_IDS",
            "MASTER_62_PILLAR_SPECS",
            "Master62PillarRecoveryReport",
            "evaluate_realhw_62pillar_recovery_master",
            "evaluate_62pillar_recovery_master",
            "verify_62pillar_recovery_suite",
            "run_pillar62_standalone_suite",
            "verify_rec_media_autoswitch_proxy_cloud_mymenu_and_vault",
            "verify_rec_media_autoswitch_proxy_cloud_mymenu_vault",
        ):
            self.assertTrue(hasattr(fr, sym), sym)
            self.assertIn(sym, fr.__all__, sym)

    def test_52_cli_verify_62pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-62pillar-recovery", "--json"],
            ["verify-62pillar-recovery", "--force-clean-room", "--json"],
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
            self.assertEqual(payload["pillars_passed"], 62)
            self.assertEqual(payload["pillar_count"], 62)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertLess(payload["elapsed_seconds"], P344_CONCURRENT_CEILING_SECONDS)

    def test_53_cli_verify_pillar62_aliases_text_and_out(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar62-recovery",
            "verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault",
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
            self.assertIn("VERIFIED_PILLAR62_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_VAULT", proc_txt.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p344_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p62_path = work_tests / f"{tag}_p62"
        try:
            proc1 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-62pillar-recovery", "--force-clean-room", "--out", str(out_master_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            self.assertTrue((out_master_path / "62pillar-recovery-master-report.json").exists())

            proc2 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-pillar62-recovery", "--force-clean-room", "--out", str(out_p62_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            self.assertTrue((out_p62_path / "pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault-report.json").exists())
        finally:
            for d in (out_master_path, out_p62_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_54_cli_backward_compat_verify_61pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-61pillar-recovery", "--force-clean-room", "--json"],
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

    def test_55_donorless_ci_mock_master62_and_cli_subprocess_exit_zero(self) -> None:
        from fx3_recovery import __main__ as cli_main
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (P344_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            for mock_roots in ((None,), (Path("/nonexistent-donor-root"),)):
                with patch.object(files_mod, "iter_donor_work_roots", return_value=mock_roots):
                    rep = evaluate_realhw_62pillar_recovery_master()
                    self.assertTrue(rep.all_passed, rep.errors)
                    self.assertEqual(rep.pillars_passed, 62)
                    self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    buf = io.StringIO()
                    with patch.object(sys, "argv", ["fx3_recovery", "verify-62pillar-recovery", "--json"]), redirect_stdout(buf):
                        rc = cli_main.main()
                    self.assertEqual(rc, 0, buf.getvalue())
                    payload = json.loads(buf.getvalue())
                    self.assertTrue(payload["all_passed"])
                    self.assertEqual(payload["pillars_passed"], 62)
                    self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

        sub_env = {
            **clean_env,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ADAPTER_ROOT),
        }
        snippet = (
            "import sys; from unittest.mock import patch; "
            "from fx3_recovery import files as f, __main__ as m; "
            "sys.argv = ['fx3_recovery', 'verify-62pillar-recovery', '--json']; "
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
        self.assertEqual(sub_payload["pillars_passed"], 62)
        self.assertEqual(sub_payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")


# ---------------------------------------------------------------------------
# Programmatic Parametric Matrices (Tests 56..112 => Total >= 112 tests)
# ---------------------------------------------------------------------------

def _make_rec_media_reset_matrix_test(
    still_media: str,
    movie_media: str,
    reset_action: str,
) -> object:
    def _test(self: Phase344Pillar62VerifierTests) -> None:
        is_init = reset_action == "Initialize"
        is_still_domain = still_media == "Sort Recording"
        active_media = still_media if is_still_domain else movie_media
        slot1_active = active_media == "Slot 1"
        vault_act = "READ_ONLY_AUDIT" if "Slot 1" in (still_media, movie_media) or "Simult" in (still_media, movie_media) else "PROXY_TO_SLOT2"
        vault_slot = 1 if vault_act == "READ_ONLY_AUDIT" else 2
        proxy_on = "Off" if is_still_domain else "On"
        proxy_fmt = "XAVC S HD" if is_still_domain else "XAVC HS HD"
        proxy_set = "6M 4:2:0 8bit" if is_still_domain else "9M 4:2:0 10bit"
        post_proxy_on = "Off" if (is_still_domain or reset_action in ("Camera Settings Reset", "Initialize")) else "On"
        post_proxy_fmt = "XAVC S HD" if (is_still_domain or reset_action in ("Camera Settings Reset", "Initialize")) else "XAVC HS HD"
        post_proxy_set = "6M 4:2:0 8bit" if (is_still_domain or reset_action in ("Camera Settings Reset", "Initialize")) else "9M 4:2:0 10bit"
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain="Still" if is_still_domain else "Movie",
            still_recording_media=still_media,
            movie_recording_media=movie_media,
            auto_switch_media="Off",
            proxy_recording=proxy_on,
            proxy_file_format=proxy_fmt,
            proxy_rec_setting=proxy_set,
            reported_effective_proxy_recording=proxy_on,
            reset_action=reset_action,
            post_still_rec_media="Slot 1" if is_init else still_media,
            post_movie_rec_media="Slot 1" if is_init else movie_media,
            post_auto_switch_media="Off",
            post_proxy_recording=post_proxy_on,
            post_proxy_file_format=post_proxy_fmt,
            post_proxy_rec_setting=post_proxy_set,
            requested_vault_slot=vault_slot,
            requested_vault_action=vault_act,
            reported_vault_action_allowed=not slot1_active,
            vault_firewall_errno="EROFS" if slot1_active else None,
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_card_speed_matrix_test(
    domain: str,
    fmt: str,
    bitrate: int,
    sq_fps: int,
    card: str,
    exp_errno: object,
    exp_warn: object,
) -> object:
    def _test(self: Phase344Pillar62VerifierTests) -> None:
        is_cfe = card.startswith("CFexpress Type A")
        subdir = P344_PROXY_CFE_SUBDIR if is_cfe else P344_PROXY_SD_SUBDIR
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain=domain,
            movie_file_format=fmt,
            movie_bitrate_mbps=bitrate,
            rec_frame_rate_p=23.98,
            sq_sensor_fps=sq_fps,
            media_card_slot2_type=card,
            reported_card_gate_errno=exp_errno,
            reported_card_gate_warning=exp_warn,
            proxy_recording="Off",
            proxy_file_format="XAVC S HD",
            proxy_rec_setting="6M 4:2:0 8bit",
            reported_effective_proxy_recording="Off",
            reported_proxy_subdir=subdir,
            reported_proxy_example_path=f"{subdir}/C0001{P344_PROXY_FILE_SUFFIX}",
            post_proxy_recording="Off",
            post_proxy_file_format="XAVC S HD",
            post_proxy_rec_setting="6M 4:2:0 8bit",
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_proxy_matrix_test(
    domain: str,
    fmt: str,
    rec_fps: float,
    sq_fps: int,
    proxy_fmt: str,
    proxy_set: str,
    expect_lockout: bool,
) -> object:
    def _test(self: Phase344Pillar62VerifierTests) -> None:
        eff_proxy = "Off" if expect_lockout else "On"
        p_errno = P344_EOPNOTSUPP_ERRNO if expect_lockout else None
        spec = build_default_safe_rec_media_autoswitch_proxy_vault_spec(
            shooting_domain=domain,
            movie_file_format=fmt,
            movie_bitrate_mbps=600 if "S-I" in fmt else 200,
            rec_frame_rate_p=rec_fps,
            sq_sensor_fps=sq_fps,
            media_card_slot2_type="CFexpress Type A VPG400",
            proxy_recording="On",
            proxy_file_format=proxy_fmt,
            proxy_rec_setting=proxy_set,
            reported_effective_proxy_recording=eff_proxy,
            reported_proxy_errno=p_errno,
            post_proxy_recording=eff_proxy,
            post_proxy_file_format=proxy_fmt,
            post_proxy_rec_setting=proxy_set,
        )
        rep = evaluate_rec_media_autoswitch_proxy_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


def _make_cloud_mymenu_reset_matrix_test(
    fw: str,
    clip_flag: str,
    page: int,
    slot_idx: int,
    disp_from_mymenu: str,
    reset_action: str,
) -> object:
    def _test(self: Phase344Pillar62VerifierTests) -> None:
        is_init = reset_action == "Initialize"
        reg_cnt = (page - 1) * 7 + slot_idx + 1
        spec = build_default_safe_cloud_poweroff_ble_mymenu_vault_spec(
            fw_version=fw,
            cloud_clip_flag_filter=clip_flag,
            mymenu_page=page,
            mymenu_slot_index=slot_idx,
            mymenu_registered_count=reg_cnt,
            mymenu_display_from_mymenu=disp_from_mymenu,
            reset_action=reset_action,
            post_cloud_account_bound_star=True,
            post_cloud_connection_enabled=False,
            post_cnct_while_power_off="Off",
            post_airplane_mode="On",
            post_mymenu_count=0 if is_init else reg_cnt,
            post_display_from_mymenu="Off" if is_init else disp_from_mymenu,
        )
        rep = evaluate_cloud_poweroff_ble_mymenu_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
    return _test


_idx = 56
for _still in ("Slot 1", "Slot 2", "Sort Recording"):
    for _movie in ("Slot 1", "Slot 2"):
        for _ra in ("None", "Camera Settings Reset", "Initialize"):
            setattr(
                Phase344Pillar62VerifierTests,
                f"test_{_idx:03d}_rec_media_reset_{_still.lower().replace(' ', '_').replace('.', '')}_{_movie.lower().replace(' ', '_')}_{_ra.lower().replace(' ', '_')}",
                _make_rec_media_reset_matrix_test(_still, _movie, _ra),
            )
            _idx += 1

for _domain, _fmt, _br, _sq, _card, _errno, _warn in (
    ("Movie", "XAVC S HD", 100, 24, "SDXC U3/V30", None, None),
    ("Movie", "XAVC S 4K", 200, 24, "SDXC U3/V30", None, None),
    ("Movie", "XAVC S 4K", 280, 24, "SDXC U3/V30", P344_EINVAL_ERRNO, None),
    ("Movie", "XAVC S 4K", 280, 24, "SDXC V60", None, None),
    ("Movie", "XAVC HS 4K", 280, 24, "SDXC V60", None, None),
    ("Movie", "XAVC S-I 4K", 600, 24, "SDXC V60", P344_EINVAL_ERRNO, None),
    ("Movie", "XAVC S-I 4K", 600, 24, "SDXC V90", None, None),
    ("Movie", "XAVC S-I DCI 4K", 600, 24, "SDXC V90", None, None),
    ("Movie", "XAVC S-I DCI 4K", 600, 24, "CFexpress Type A VPG200", None, None),
    ("Movie", "XAVC S-I DCI 4K", 600, 24, "CFexpress Type A VPG400", None, None),
    ("S&Q", "XAVC S-I 4K", 1200, 120, "SDXC V90", P344_EINVAL_ERRNO, None),
    ("S&Q", "XAVC S-I 4K", 1200, 120, "CFexpress Type A VPG200", None, "VPG200_VPG400_GATE"),
    ("S&Q", "XAVC S-I 4K", 1200, 120, "CFexpress Type A VPG400", None, None),
    ("S&Q", "XAVC S-I HD", 890, 240, "SDXC V90", P344_EINVAL_ERRNO, None),
    ("S&Q", "XAVC S-I HD", 890, 240, "CFexpress Type A VPG400", None, None),
    ("S&Q", "XAVC S-I DCI 4K", 600, 60, "CFexpress Type A VPG400", None, None),
):
    setattr(
        Phase344Pillar62VerifierTests,
        f"test_{_idx:03d}_card_gate_{_domain.lower().replace('&', '')}_{_fmt.lower().replace(' ', '_').replace('-', '_')}_{_card.lower().replace(' ', '_').replace('/', '_')}",
        _make_card_speed_matrix_test(_domain, _fmt, _br, _sq, _card, _errno, _warn),
    )
    _idx += 1

for _domain, _fmt, _rfps, _sqfps, _pfmt, _pset, _lock in (
    ("Movie", "XAVC S-I DCI 4K", 23.98, 24, "XAVC S HD", "6M 4:2:0 8bit", False),
    ("Movie", "XAVC S-I DCI 4K", 59.94, 24, "XAVC HS HD", "9M 4:2:0 10bit", False),
    ("Movie", "XAVC S-I DCI 4K", 50.0, 24, "XAVC HS HD", "16M 4:2:0 10bit", False),
    ("Movie", "XAVC S 4K", 59.94, 24, "XAVC HS HD", "16M 4:2:0 10bit", False),
    ("Movie", "XAVC S 4K", 119.88, 24, "XAVC HS HD", "9M 4:2:0 10bit", True),
    ("Movie", "XAVC HS 4K", 100.0, 24, "XAVC S HD", "6M 4:2:0 8bit", True),
    ("S&Q", "XAVC S-I 4K", 23.98, 60, "XAVC HS HD", "9M 4:2:0 10bit", False),
    ("S&Q", "XAVC S 4K", 23.98, 120, "XAVC HS HD", "9M 4:2:0 10bit", True),
    ("S&Q", "XAVC S HD", 25.0, 100, "XAVC S HD", "6M 4:2:0 8bit", True),
):
    setattr(
        Phase344Pillar62VerifierTests,
        f"test_{_idx:03d}_proxy_matrix_{_domain.lower().replace('&', '')}_{_fmt.lower().replace(' ', '_').replace('-', '_')}_{int(_rfps)}_{_sqfps}",
        _make_proxy_matrix_test(_domain, _fmt, _rfps, _sqfps, _pfmt, _pset, _lock),
    )
    _idx += 1

for _fw in ("7.00", "7.01", "7.02"):
    for _cf in ("Off", "OK", "NG", "KEEP"):
        for _ra in ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize"):
            _pg = 1 + (_idx % 6)
            _si = _idx % 7
            _dfm = "On" if _idx % 2 == 0 else "Off"
            setattr(
                Phase344Pillar62VerifierTests,
                f"test_{_idx:03d}_cloud_mymenu_{_fw.replace('.', '')}_{_cf.lower()}_{_ra.lower().replace(' ', '_').replace('.', '')}",
                _make_cloud_mymenu_reset_matrix_test(_fw, _cf, _pg, _si, _dfm, _ra),
            )
            _idx += 1


if __name__ == "__main__":
    unittest.main()
