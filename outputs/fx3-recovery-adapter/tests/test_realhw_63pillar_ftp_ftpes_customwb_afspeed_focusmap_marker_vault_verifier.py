"""Phase 348 (Pillar 63 & 63/63 Milestone) unit tests:
Wave-61 [FTP Transfer Func.] (Server 1..9 surviving Camera Settings Reset & cleared by
Reset Network Set. / Initialize, FTP + FTPES Explicit TLS in Passive Mode ONLY, ZERO
SFTP/FTPES string/passive_mode/Transfer JPEG Size -> EOPNOTSUPP=95, Slot 1 cacert.pem
<= 1 MiB vs FX6 Server Settings1..3 + Active/Passive + Slot B certification.pem + Auto
Upload Proxy Chunk; Airplane Mode = On blocks Wi-Fi/BLE ONLY and STILL permits wired
USB-LAN USB_ETHER -> dual Zero-RF gate Airplane=On + USB-LAN=Off; Slot 1 AVF_INFO
0x0a13 / FTP_TRANS_STAT EROFS=30 firewall); White Balance (Auto, 2500K..9900K, Custom 1..3
excluded from CAMSET*.DAT & Custom WB Error hazard under Log != Off / S-Log3 / PPLUT1..4,
Cine EI / Cine EI Quick Auto lockout, Resettable Priority Set in AWB & Movie/S&Q Shockless
WB w/ direct C.Temp./tint bypass vs Still-only Reset-immune Shutter AWB Lock vs FX6 WHT
BAL PRST/A/B + Memory A..H + ATW Speed 1..5); Movie AF Transition Speed 1..7 & AF Subj.
Shift Sens. 1..5 parity across BOTH FX3 Ver. 7.02 & FX6 Ver. 6.01 (0 hits 6/7 in FX6
appFw.so!) + AF Assist w/ SELP1650/SEL18200LE gate; App-only [Focus Map] Ver. 6.00+
telemetry via Monitor & Control Ver. 2.1.0+ w/ >= 150 fps lockout vs 0 in-body UI; and
8 Reset-immune Assist items ([Marker Display] w/ Off + 15 Aspect Marker ratios = 16
states, auto-hidden in Focus Magnifier; [Peaking Display] High/Mid/Low + 4 colors) w/
0 px Clean-HDMI isolation vs FX6 User Box & B&W peaking + Tier-0 Slot 1 EROFS=30 Vault.
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
    MASTER_63_PILLAR_COUNT,
    MASTER_63_PILLAR_IDS,
    MASTER_63_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P348_AF_ASSIST_DEFAULT,
    P348_AF_ASSIST_F_RESID16,
    P348_AF_ASSIST_INCOMPATIBLE_LENSES,
    P348_AF_SUBJ_SHIFT_SENS_DEFAULT,
    P348_AF_SUBJ_SHIFT_SENS_F_RESID16,
    P348_AF_SUBJ_SHIFT_SENS_MAX,
    P348_AF_SUBJ_SHIFT_SENS_MIN,
    P348_AF_TRANSITION_SPEED_DEFAULT,
    P348_AF_TRANSITION_SPEED_F_RESID16,
    P348_AF_TRANSITION_SPEED_MAX,
    P348_AF_TRANSITION_SPEED_MIN,
    P348_AIRPLANE_MODE_FORCED_ON,
    P348_ASPECT_MARKER_F_RESID16,
    P348_BKID_AF_ASSIST,
    P348_BKID_ASPECT_MARKER,
    P348_BKID_CENTER_MARKER,
    P348_BKID_FTP_FUNCTION,
    P348_BKID_FTP_POWER_SAVE,
    P348_BKID_GUIDEFRAME,
    P348_BKID_MARKER_DISPLAY,
    P348_BKID_PEAKING_COLOR,
    P348_BKID_PEAKING_DISPLAY,
    P348_BKID_PEAKING_LEVEL,
    P348_BKID_PRIORITY_SET_AWB,
    P348_BKID_SAFETY_ZONE,
    P348_BKID_SHOCKLESS_WB,
    P348_BKID_SHUTTER_AWB_LOCK,
    P348_BKID_WB_MOVIE,
    P348_BKID_WB_STILL,
    P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT,
    P348_BLOCKED_INVALID_PILLAR63A_SPEC,
    P348_BLOCKED_INVALID_PILLAR63B_SPEC,
    P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK,
    P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF,
    P348_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P348_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P348_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT,
    P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL,
    P348_CENTER_MARKER_F_RESID16,
    P348_CINE_EI_MODES,
    P348_CONCURRENT_CEILING_SECONDS,
    P348_DONOR_INSPECT_BUDGET_SECONDS,
    P348_DORMANT_SFTP_F_RESID16S,
    P348_DORMANT_TRANSFER_HEIF_SIZE_F_RESID16,
    P348_DORMANT_TRANSFER_JPEG_SIZE_F_RESID16,
    P348_EINVAL_ERRNO,
    P348_ENV_CLEAN_ROOM_TEST,
    P348_EOPNOTSUPP_ERRNO,
    P348_EROFS_ERRNO,
    P348_FAST_CLI_BUDGET_SECONDS,
    P348_FOCUS_MAP_F_RESID16,
    P348_FTP_AVF_INFO_RESET_BASE_RESID16,
    P348_FTP_CLIP_FLAG_FILTERS,
    P348_FTP_CLIP_FLAG_F_RESID16,
    P348_FTP_DIRECTORY_HIERARCHIES,
    P348_FTP_DIRECTORY_HIERARCHY_F_RESID16,
    P348_FTP_DIR_PATH_MAX_CHARS,
    P348_FTP_FUNCTION_F_RESID16,
    P348_FTP_IMPORT_ROOT_CERT_F_RESID16,
    P348_FTP_POWER_SAVE_F_RESID16,
    P348_FTP_RAW_JH_TARGET_F_RESID16,
    P348_FTP_SAVE_TRANSFER_LIST_SYMBOL,
    P348_FTP_SECURE_PROTOCOL_F_RESID16,
    P348_FTP_SERVER_F_RESID16,
    P348_FTP_SERVER_SLOT_COUNT,
    P348_FTP_SERVER_SLOT_PREFIXES,
    P348_FTP_TRANSFERRING_SLOT_BASE_RESID16S,
    P348_FTP_TRANSFER_F_RESID16,
    P348_FTP_TRANS_STAT_EXCLUSION_PREFIX,
    P348_FTP_USB_ETHER_SYMBOL,
    P348_FX3_APPFW_FTPES_STRING_HIT_COUNT,
    P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT,
    P348_FX3_APPFW_SFTP_HIT_COUNT,
    P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT,
    P348_FX3_ASPECT_MARKER_ACTIVE_RATIOS,
    P348_FX3_ASPECT_MARKER_STATES,
    P348_FX3_FOCUS_MAP_ADDED_FW,
    P348_FX3_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD,
    P348_FX3_FOCUS_MAP_MIN_MC_APP_VER,
    P348_FX3_FOCUS_MAP_SUPPORTED_FW_VERSIONS,
    P348_FX3_FOCUS_MAP_TELEMETRY_SYMBOLS,
    P348_FX3_FTP_CERT_FILENAME,
    P348_FX3_FTP_CERT_MAX_BYTES,
    P348_FX3_FTP_CERT_SLOT,
    P348_FX3_FTP_HELPGUIDE_ID,
    P348_FX3_FTP_SUPPORTED_PROTOCOLS,
    P348_FX3_FTP_TRANSFER_MODE_ONLY,
    P348_FX3_FW_VERSION,
    P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS,
    P348_FX3_MODEL_NAME,
    P348_FX3_PEAKING_COLORS,
    P348_FX3_PEAKING_COLOR_DEFAULT,
    P348_FX3_PEAKING_LEVELS,
    P348_FX3_PEAKING_LEVEL_DEFAULT,
    P348_FX3_SAFETY_ZONE_MODES,
    P348_FX6_APPFW_AF_SUBJ_SHIFT_6_7_HITS,
    P348_FX6_ASPECT_MASK_MAX,
    P348_FX6_ATW_SPEED_MAX,
    P348_FX6_AUTO_UPLOAD_CHUNK_MODES,
    P348_FX6_DONOR_FW_VERSION,
    P348_FX6_DONOR_MODEL_NAME,
    P348_FX6_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD,
    P348_FX6_FOCUS_MAP_LOW_FPS_LOCKOUT_MAX,
    P348_FX6_FTP_CERT_FILENAME,
    P348_FX6_FTP_CERT_SLOT,
    P348_FX6_FTP_SERVER_UI_SLOTS,
    P348_FX6_PEAKING_COLORS,
    P348_FX6_SAFETY_AREA_MODES,
    P348_FX6_USER_BOX_HEIGHT_RANGE,
    P348_FX6_USER_BOX_H_POS_RANGE,
    P348_FX6_USER_BOX_V_POS_RANGE,
    P348_FX6_USER_BOX_WIDTH_RANGE,
    P348_FX6_WB_MEMORY_SLOTS,
    P348_FX6_WHT_BAL_SWITCH_POSITIONS,
    P348_GUIDEFRAME_F_RESID16,
    P348_HDMI_MARKER_PEAKING_LEAK_PIXELS,
    P348_MARKER_DISPLAY_F_RESID16,
    P348_PEAKING_COLOR_BASE_RESID16,
    P348_PEAKING_DISPLAY_F_RESID16,
    P348_PEAKING_LEVEL_BASE_RESID16,
    P348_PRIORITY_SET_AWB_DEFAULT,
    P348_PRIORITY_SET_AWB_F_RESID16,
    P348_RESET_IMMUNE_ASSIST_ITEM_COUNT,
    P348_SAFETY_ZONE_F_RESID16,
    P348_SHOCKLESS_WB_DEFAULT,
    P348_SHOCKLESS_WB_F_RESID16,
    P348_SHUTTER_AWB_LOCK_DEFAULT,
    P348_SHUTTER_AWB_LOCK_F_RESID16,
    P348_SLOT1_FORMAT_HARD_LOCKED,
    P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P348_STATUS_VERIFIED_63OF63_AGGREGATOR,
    P348_STATUS_VERIFIED_PILLAR63_SUITE,
    P348_STATUS_VERIFIED_PILLAR_63A,
    P348_STATUS_VERIFIED_PILLAR_63B,
    P348_USBLAN_BENCH_LOCKED_OFF,
    P348_WB_CUSTOM_ERROR_BASE_RESID16,
    P348_WB_CUSTOM_FAIL_F_RESID16,
    P348_WB_CUSTOM_HAZARD_PROFILES,
    P348_WB_CUSTOM_SLOTS,
    P348_WB_C_TEMP_MAX_K,
    P348_WB_C_TEMP_MIN_K,
    P348_WB_C_TEMP_STEP_K,
    P348_WB_DEFAULT,
    P348_WB_F_RESID16,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PHASE348_MASTER_SCHEMA,
    PHASE348_PHASE_NUMBER,
    PHASE348_SCHEMA,
    PHASE348_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    P348_DONOR_FX3_APPFW_702_RELPATH,
    P348_DONOR_FX6_APPFW_601_RELPATH,
    P348_WRITE_MUTATING_VAULT_ACTIONS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_ftp_ftpes_customwb_vault_spec,
    build_default_safe_movie_af_focusmap_marker_vault_spec,
    compute_expected_ftp_ftpes_customwb_state,
    compute_expected_movie_af_focusmap_marker_state,
    evaluate_63pillar_recovery_master,
    evaluate_ftp_ftpes_customwb_vault,
    evaluate_movie_af_focusmap_marker_vault,
    evaluate_realhw_63pillar_recovery_master,
    inspect_phase348_donors_readonly,
    run_pillar63_standalone_suite,
    run_pillar63a_ftp_ftpes_customwb_vault_6_scenario_suite,
    run_pillar63b_movie_af_focusmap_marker_vault_6_scenario_suite,
    verify_63pillar_recovery_suite,
    verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault,
    verify_ftp_ftpes_customwb_afspeed_focusmap_marker_vault,
)


def _fx3_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    fx3_rel = P348_DONOR_FX3_APPFW_702_RELPATH
    fx6_rel = P348_DONOR_FX6_APPFW_601_RELPATH
    fx3_ok = any((r / fx3_rel).exists() or (r.parent / fx3_rel).exists() for r in roots)
    fx6_ok = any((r / fx6_rel).exists() or (r.parent / fx6_rel).exists() for r in roots)
    return fx3_ok and fx6_ok


class Phase348Pillar63VerifierTests(unittest.TestCase):
    """Phase 348 Pillar 63 & 63/63 Master Recovery Verifier unit tests."""

    # ------------------------------------------------------------------
    # Safety Invariants, Constants & 4-Mode Bounded Donor Inspection (1..14)
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_and_budget_constants(self) -> None:
        self.assertEqual(PHASE348_PHASE_NUMBER, 348)
        self.assertEqual(
            PHASE348_SCHEMA,
            "realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier_v1",
        )
        self.assertEqual(PHASE348_MASTER_SCHEMA, "realhw_63pillar_recovery_master_v1")
        self.assertEqual(PHASE348_VERSION, "1.0.0")
        self.assertEqual(MASTER_63_PILLAR_COUNT, 63)
        self.assertEqual(len(MASTER_63_PILLAR_IDS), 63)
        self.assertEqual(len(MASTER_63_PILLAR_SPECS), 63)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P348_AIRPLANE_MODE_FORCED_ON)
        self.assertTrue(P348_USBLAN_BENCH_LOCKED_OFF)
        self.assertTrue(P348_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P348_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P348_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P348_CONCURRENT_CEILING_SECONDS, 6.00)

    def test_02_wave61_ftp_resid16_and_dormant_zero_hit_truth(self) -> None:
        self.assertEqual(P348_FTP_SERVER_SLOT_COUNT, 9)
        self.assertEqual(len(P348_FTP_SERVER_SLOT_PREFIXES), 9)
        self.assertEqual(P348_FTP_SERVER_SLOT_PREFIXES[0], "BKID_APP_ftp_server_settings_host_name0")
        self.assertEqual(P348_FTP_SERVER_SLOT_PREFIXES[8], "BKID_APP_ftp_server_settings_host_name8")
        self.assertEqual(P348_FX3_FTP_SUPPORTED_PROTOCOLS, ("FTP", "FTPES"))
        self.assertEqual(P348_FX3_FTP_TRANSFER_MODE_ONLY, "Passive")
        self.assertEqual(P348_FX3_APPFW_SFTP_HIT_COUNT, 0)
        self.assertEqual(P348_FX3_APPFW_FTPES_STRING_HIT_COUNT, 0)
        self.assertEqual(P348_FX3_APPFW_PASSIVE_MODE_HIT_COUNT, 0)
        self.assertEqual(P348_FX3_APPFW_TRANSFER_JPEG_HEIF_SIZE_HIT_COUNT, 0)
        self.assertEqual(P348_DORMANT_SFTP_F_RESID16S, (0x68D9, 0x6ED3))
        self.assertEqual(P348_DORMANT_TRANSFER_JPEG_SIZE_F_RESID16, 0x6AED)
        self.assertEqual(P348_DORMANT_TRANSFER_HEIF_SIZE_F_RESID16, 0x63DD)
        self.assertEqual(P348_FTP_TRANSFER_F_RESID16, 0x62FC)
        self.assertEqual(P348_FTP_FUNCTION_F_RESID16, (0x7287, 0x6317))
        self.assertEqual(P348_FTP_SERVER_F_RESID16, (0x6442, 0x6305, 0x72F4, 0x630D))
        self.assertEqual(P348_FTP_SECURE_PROTOCOL_F_RESID16, (0x60DD, 0x6553))
        self.assertEqual(P348_FTP_IMPORT_ROOT_CERT_F_RESID16, 0x7940)
        self.assertEqual(P348_FTP_POWER_SAVE_F_RESID16, 0x6A5F)
        self.assertEqual(P348_FTP_DIRECTORY_HIERARCHY_F_RESID16, (0x6E7E, 0x76E6))
        self.assertEqual(P348_FTP_RAW_JH_TARGET_F_RESID16, 0x6BD5)
        self.assertEqual(P348_FTP_CLIP_FLAG_F_RESID16, 0x7D31)
        self.assertEqual(P348_FTP_AVF_INFO_RESET_BASE_RESID16, 0x0A13)
        self.assertEqual(P348_FTP_SAVE_TRANSFER_LIST_SYMBOL, "save_ftp_transfer_list_to_media")
        self.assertEqual(P348_FTP_TRANS_STAT_EXCLUSION_PREFIX, "CONTENT_INFO_FTP_TRANS_STAT_")
        self.assertEqual(
            P348_FTP_USB_ETHER_SYMBOL,
            "VAL_HAITA_setting_ftp_function_setting_ftp_connect_method_FTP_CONNECT_METHOD_USB_ETHER",
        )
        self.assertEqual(P348_FX3_FTP_CERT_FILENAME, "cacert.pem")
        self.assertEqual(P348_FX3_FTP_CERT_MAX_BYTES, 1_048_576)
        self.assertEqual(P348_FX3_FTP_CERT_SLOT, 1)
        self.assertEqual(P348_FX6_FTP_CERT_FILENAME, "certification.pem")
        self.assertEqual(P348_FX6_FTP_CERT_SLOT, "Slot B")
        self.assertEqual(P348_FX6_FTP_SERVER_UI_SLOTS, 3)
        self.assertEqual(P348_FX3_FTP_HELPGUIDE_ID, "di/ftp_2210")

    def test_03_wave61_wb_movie_af_focusmap_marker_and_peaking_truth(self) -> None:
        self.assertEqual(P348_WB_CUSTOM_SLOTS, (1, 2, 3))
        self.assertEqual(P348_WB_C_TEMP_MIN_K, 2500)
        self.assertEqual(P348_WB_C_TEMP_MAX_K, 9900)
        self.assertEqual(P348_WB_C_TEMP_STEP_K, 100)
        self.assertEqual(P348_WB_F_RESID16, (0x73EE, 0x6035))
        self.assertEqual(P348_PRIORITY_SET_AWB_F_RESID16, (0x67A7, 0x749F, 0x6541))
        self.assertEqual(P348_SHUTTER_AWB_LOCK_F_RESID16, (0x66DB, 0x6373, 0x6A32))
        self.assertEqual(P348_SHOCKLESS_WB_F_RESID16, (0x62FE, 0x6649, 0x6EF1))
        self.assertEqual(P348_WB_CUSTOM_ERROR_BASE_RESID16, 0x0220)
        self.assertEqual(P348_WB_CUSTOM_FAIL_F_RESID16, 0x63AC)
        self.assertEqual(P348_AF_TRANSITION_SPEED_MIN, 1)
        self.assertEqual(P348_AF_TRANSITION_SPEED_MAX, 7)
        self.assertEqual(P348_AF_TRANSITION_SPEED_DEFAULT, 5)
        self.assertEqual(P348_AF_SUBJ_SHIFT_SENS_MIN, 1)
        self.assertEqual(P348_AF_SUBJ_SHIFT_SENS_MAX, 5)
        self.assertEqual(P348_AF_SUBJ_SHIFT_SENS_DEFAULT, 5)
        self.assertEqual(P348_FX6_APPFW_AF_SUBJ_SHIFT_6_7_HITS, 0)
        self.assertEqual(P348_AF_TRANSITION_SPEED_F_RESID16, 0x6E9D)
        self.assertEqual(P348_AF_SUBJ_SHIFT_SENS_F_RESID16, 0x79D6)
        self.assertEqual(P348_AF_ASSIST_F_RESID16, 0x64A9)
        self.assertEqual(P348_AF_ASSIST_INCOMPATIBLE_LENSES, ("SELP1650", "SEL18200LE"))
        self.assertEqual(P348_FOCUS_MAP_F_RESID16, 0x61F9)
        self.assertEqual(P348_FX3_IN_BODY_FOCUS_MAP_BKID_HITS, 0)
        self.assertEqual(P348_FX3_FOCUS_MAP_ADDED_FW, "6.00")
        self.assertEqual(P348_FX3_FOCUS_MAP_MIN_MC_APP_VER, "2.1.0")
        self.assertEqual(P348_FX3_FOCUS_MAP_HIGH_FPS_LOCKOUT_THRESHOLD, 150)
        self.assertEqual(len(P348_FX3_ASPECT_MARKER_ACTIVE_RATIOS), 15)
        self.assertEqual(len(P348_FX3_ASPECT_MARKER_STATES), 16)
        self.assertEqual(P348_FX3_PEAKING_COLORS, ("Red", "Yellow", "Blue", "White"))
        self.assertEqual(P348_FX6_PEAKING_COLORS, ("B&W", "Red", "Yellow", "Blue"))
        self.assertEqual(P348_RESET_IMMUNE_ASSIST_ITEM_COUNT, 8)
        self.assertEqual(P348_HDMI_MARKER_PEAKING_LEAK_PIXELS, 0)

    def test_04_donor_inspect_mode_1_normal_local_or_auto_cleanroom(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (P348_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, env_clean, clear=True):
            snap = inspect_phase348_donors_readonly()
            expected_mode = (
                "LOCAL_DONOR_O_RDONLY" if _fx3_donors_present() else "CLEAN_ROOM_SYNTHETIC"
            )
        self.assertEqual(snap.verification_mode, expected_mode)
        self.assertTrue(snap.all_donors_present)
        self.assertTrue(snap.under_2_0s_budget)
        self.assertLess(snap.elapsed_seconds, P348_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_05_donor_inspect_mode_2_fx3_clean_room_test_env(self) -> None:
        with patch.dict(os.environ, {P348_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase348_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertTrue(snap.under_2_0s_budget)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_06_donor_inspect_mode_3_fx3_fx6_force_clean_room_env(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase348_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_07_donor_inspect_mode_4_mocked_work_root_none_donorless(self) -> None:
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (P348_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            with patch.object(files_mod, "iter_donor_work_roots", return_value=(None,)):
                snap = inspect_phase348_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertTrue(snap.under_2_0s_budget)
                self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
                rep = evaluate_realhw_63pillar_recovery_master()
                self.assertTrue(rep.all_passed, rep.errors)
                self.assertEqual(rep.pillars_passed, 63)
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    # ------------------------------------------------------------------
    # Pillar 63A State & Evaluator Tests (8..26)
    # ------------------------------------------------------------------

    def test_08_default_safe_63a_spec_passes(self) -> None:
        rep = evaluate_ftp_ftpes_customwb_vault(build_default_safe_ftp_ftpes_customwb_vault_spec())
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P348_STATUS_VERIFIED_PILLAR_63A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.ftp_ftpes_9slots_passive_and_zero_sftp_verified)
        self.assertTrue(rep.wb_custom_cine_ei_and_shockless_verified)
        self.assertTrue(rep.zero_rf_usblan_and_slot1_avf_erofs30_verified)
        self.assertTrue(rep.overlay_and_h0_h3_verified)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.usblan_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_09_63a_sftp_active_mode_and_transfer_jpeg_size_return_eopnotsupp95(self) -> None:
        st = compute_expected_ftp_ftpes_customwb_state(
            camera_model=P348_FX3_MODEL_NAME,
            fw_version=P348_FX3_FW_VERSION,
            ftp_server_slot=9,
            ftp_protocol="SFTP",
            ftp_transfer_mode="Active",
            transfer_jpeg_heif_size_requested=True,
            ftp_directory_hierarchy="Standard",
            ftp_specify_dir_len=0,
            ftp_clip_flag_filter="Off",
            ftp_cert_filename="cacert.pem",
            ftp_cert_bytes=2048,
            ftp_cert_slot="Slot 1",
            ftp_power_save="Off",
            fx6_auto_upload_proxy_chunk="Off",
            fx6_simul_or_relay_active=False,
            airplane_mode="On",
            usb_lan_enabled=False,
            wifi_active=False,
            ble_active=False,
            ftp_function_enabled=False,
            network_transport="NONE",
            shooting_domain="Movie",
            wb_mode="C.Temp./Filter",
            wb_color_temp_k=5600,
            wb_direct_ctemp_or_tint_tweaked=False,
            custom_wb_slots_populated=3,
            custom_wb_exported_in_camset=False,
            custom_setup_triggered=False,
            log_shooting_mode="Off",
            picture_profile="Off",
            priority_set_in_awb="Standard",
            shutter_awb_lock="Off",
            shockless_wb="1",
            fx6_wht_bal_switch="PRST",
            fx6_memory_bank="A",
            fx6_atw_speed=3,
            reset_action="None",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertEqual(st["ftp_protocol_errno"], P348_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["ftp_mode_errno"], P348_EOPNOTSUPP_ERRNO)
        self.assertEqual(st["transfer_size_errno"], P348_EOPNOTSUPP_ERRNO)

        spec = build_default_safe_ftp_ftpes_customwb_vault_spec(ftp_protocol="SFTP")
        rep = evaluate_ftp_ftpes_customwb_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

    def test_10_63a_ftp_server_slot_10_invalid_and_cacert_over_1mb_rejected(self) -> None:
        rep_slot10 = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(ftp_server_slot=10)
        )
        self.assertFalse(rep_slot10.passed)
        self.assertEqual(rep_slot10.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

        rep_cert = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                ftp_cert_bytes=P348_FX3_FTP_CERT_MAX_BYTES + 1
            )
        )
        self.assertFalse(rep_cert.passed)
        self.assertEqual(rep_cert.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

    def test_11_63a_ftp_clip_flag_requires_ver7_and_specify_dir_max_256(self) -> None:
        rep_old_fw = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                fw_version="6.02", ftp_clip_flag_filter="OK"
            )
        )
        self.assertFalse(rep_old_fw.passed)
        self.assertEqual(rep_old_fw.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

        rep_dir_over = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                ftp_directory_hierarchy="Specify Directory",
                ftp_specify_dir_len=P348_FTP_DIR_PATH_MAX_CHARS + 1,
            )
        )
        self.assertFalse(rep_dir_over.passed)
        self.assertEqual(rep_dir_over.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

    def test_12_63a_fx6_active_ftp_cert_slot_b_and_auto_upload_chunk_mutex(self) -> None:
        ok_spec = build_default_safe_ftp_ftpes_customwb_vault_spec(
            camera_model=P348_FX6_DONOR_MODEL_NAME,
            fw_version=P348_FX6_DONOR_FW_VERSION,
            ftp_server_slot=3,
            ftp_protocol="FTPES",
            ftp_transfer_mode="Active",
            ftp_cert_filename=P348_FX6_FTP_CERT_FILENAME,
            ftp_cert_slot=P348_FX6_FTP_CERT_SLOT,
            fx6_auto_upload_proxy_chunk="Chunk",
            fx6_simul_or_relay_active=False,
        )
        rep_ok = evaluate_ftp_ftpes_customwb_vault(ok_spec)
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        bad_spec = build_default_safe_ftp_ftpes_customwb_vault_spec(
            camera_model=P348_FX6_DONOR_MODEL_NAME,
            fw_version=P348_FX6_DONOR_FW_VERSION,
            ftp_cert_filename=P348_FX6_FTP_CERT_FILENAME,
            ftp_cert_slot=P348_FX6_FTP_CERT_SLOT,
            fx6_auto_upload_proxy_chunk="Chunk",
            fx6_simul_or_relay_active=True,
        )
        rep_bad = evaluate_ftp_ftpes_customwb_vault(bad_spec)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P348_BLOCKED_FTP_PROTOCOL_SFTP_OR_JPEG_SIZE_DRIFT)

    def test_13_63a_ftp_survives_camera_reset_cleared_by_network_reset_and_initialize(self) -> None:
        for action, expect_cleared in (
            ("Camera Settings Reset", False),
            ("Reset Network Set.", True),
            ("Initialize", True),
        ):
            spec = build_default_safe_ftp_ftpes_customwb_vault_spec(
                reset_action=action,
                post_ftp_servers_cleared=expect_cleared,
                post_wb_mode="C.Temp./Filter" if action == "Reset Network Set." else "Auto",
                post_priority_set_in_awb="Standard",
                post_shutter_awb_lock="Off",
                post_shockless_wb="1",
                post_custom_wb_slots_cleared=(action == "Initialize"),
            )
            rep = evaluate_ftp_ftpes_customwb_vault(spec)
            self.assertTrue(rep.passed, f"{action}: {rep.errors}")

    def test_14_63a_airplane_mode_usblan_bypass_blocked(self) -> None:
        rep = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                airplane_mode="On",
                usb_lan_enabled=True,
                ftp_function_enabled=True,
                post_ftp_function_enabled=True,
                network_transport="USB-LAN",
                usblan_packets_transmitted=128,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL)

    def test_15_63a_slot1_avf_info_and_ftp_trans_stat_write_erofs30_firewall(self) -> None:
        for act in P348_WRITE_MUTATING_VAULT_ACTIONS:
            rep = evaluate_ftp_ftpes_customwb_vault(
                build_default_safe_ftp_ftpes_customwb_vault_spec(
                    requested_vault_slot=1,
                    slot1_holds_tier0_vault=True,
                    requested_vault_action=act,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                    slot1_data_sector_writes=4096,
                    slot1_avf_info_mutation_bytes=4096,
                    slot1_vault_mutation_bytes=4096,
                    slot1_vault_erofs_eopnotsupp_enforced=False,
                )
            )
            self.assertFalse(rep.passed, act)
            self.assertEqual(rep.block_code, P348_BLOCKED_ZERO_RF_USBLAN_OR_SLOT1_AVF_FIREWALL)

    def test_16_63a_wb_cine_ei_locks_out_auto_and_underwater_auto(self) -> None:
        for cine_mode in P348_CINE_EI_MODES:
            for locked_wb in ("Auto", "Underwater Auto"):
                rep = evaluate_ftp_ftpes_customwb_vault(
                    build_default_safe_ftp_ftpes_customwb_vault_spec(
                        wb_mode=locked_wb, log_shooting_mode=cine_mode
                    )
                )
                self.assertFalse(rep.passed, (cine_mode, locked_wb))
                self.assertEqual(rep.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

    def test_17_63a_custom_wb_camset_exclusion_and_log_pplut_error_hazard(self) -> None:
        rep_camset = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                wb_mode="Custom 1", custom_wb_exported_in_camset=True
            )
        )
        self.assertFalse(rep_camset.passed)
        self.assertEqual(rep_camset.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

        for profile in P348_WB_CUSTOM_HAZARD_PROFILES:
            rep_err = evaluate_ftp_ftpes_customwb_vault(
                build_default_safe_ftp_ftpes_customwb_vault_spec(
                    wb_mode="Custom 2",
                    custom_setup_triggered=True,
                    picture_profile=profile,
                )
            )
            self.assertFalse(rep_err.passed, profile)
            self.assertEqual(rep_err.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

    def test_18_63a_still_shutter_awb_lock_is_reset_immune_and_movie_eopnotsupp95(self) -> None:
        rep_still_ok = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                shooting_domain="Still",
                shutter_awb_lock="Shut. Halfway",
                reported_shockless_wb_effective="Off",
                reported_shockless_wb_bypassed=True,
                reset_action="Camera Settings Reset",
                post_wb_mode="Auto",
                post_priority_set_in_awb="Standard",
                post_shutter_awb_lock="Shut. Halfway",
                post_shockless_wb="1",
            )
        )
        self.assertTrue(rep_still_ok.passed, rep_still_ok.errors)

        rep_still_spoof_wiped = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                shooting_domain="Still",
                shutter_awb_lock="Shut. Halfway",
                reported_shockless_wb_effective="Off",
                reported_shockless_wb_bypassed=True,
                reset_action="Camera Settings Reset",
                post_wb_mode="Auto",
                post_shutter_awb_lock="Off",
            )
        )
        self.assertFalse(rep_still_spoof_wiped.passed)
        self.assertEqual(
            rep_still_spoof_wiped.block_code,
            P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT,
        )

        rep_movie_rejected = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                shooting_domain="Movie", shutter_awb_lock="Cont. Shooting"
            )
        )
        self.assertFalse(rep_movie_rejected.passed)
        self.assertEqual(rep_movie_rejected.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

    def test_19_63a_shockless_wb_bypassed_on_direct_ctemp_or_tint_tweaks(self) -> None:
        rep = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                shooting_domain="Movie",
                shockless_wb="3",
                wb_direct_ctemp_or_tint_tweaked=True,
                reported_shockless_wb_effective="Off",
                reported_shockless_wb_bypassed=True,
                post_shockless_wb="3",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_20_63a_ctemp_step_and_bounds_plus_fx6_atw_speed_rejected(self) -> None:
        rep_step = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(wb_color_temp_k=5550)
        )
        self.assertFalse(rep_step.passed)
        self.assertEqual(rep_step.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

        rep_fx6_atw = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                ftp_cert_filename=P348_FX6_FTP_CERT_FILENAME,
                ftp_cert_slot=P348_FX6_FTP_CERT_SLOT,
                fx6_atw_speed=6,
            )
        )
        self.assertFalse(rep_fx6_atw.passed)
        self.assertEqual(rep_fx6_atw.block_code, P348_BLOCKED_WB_CUSTOM_CINE_EI_OR_SHOCKLESS_DRIFT)

    def test_21_63a_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        rep_ov = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(overlay_dir="/setting/bad")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P348_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(backup_bin_h3_sha256="a" * 64)
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P348_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_22_63a_invalid_spec_field_rejected(self) -> None:
        rep = evaluate_ftp_ftpes_customwb_vault(
            build_default_safe_ftp_ftpes_customwb_vault_spec(ftp_protocol="SCP")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P348_BLOCKED_INVALID_PILLAR63A_SPEC)

    # ------------------------------------------------------------------
    # Pillar 63B State & Evaluator Tests (23..38)
    # ------------------------------------------------------------------

    def test_23_default_safe_63b_spec_passes(self) -> None:
        rep = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P348_STATUS_VERIFIED_PILLAR_63B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.movie_af_parity_and_app_only_focus_map_verified)
        self.assertTrue(rep.marker_15ratio_peaking_reset_immune_clean_hdmi_verified)
        self.assertTrue(rep.slot1_vault_firewall_and_h0_h3_verified)
        self.assertEqual(rep.hdmi_marker_peaking_pixels_emitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_24_63b_fx6_af_subj_shift_sens_6_and_7_rejected_parity_fix(self) -> None:
        for model, fw in (
            (P348_FX3_MODEL_NAME, P348_FX3_FW_VERSION),
            (P348_FX6_DONOR_MODEL_NAME, P348_FX6_DONOR_FW_VERSION),
        ):
            for bad_shift in (6, 7):
                rep = evaluate_movie_af_focusmap_marker_vault(
                    build_default_safe_movie_af_focusmap_marker_vault_spec(
                        camera_model=model,
                        fw_version=fw,
                        af_subj_shift_sens=bad_shift,
                    )
                )
                self.assertFalse(rep.passed, (model, bad_shift))
                self.assertEqual(rep.block_code, P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF)

    def test_25_63b_af_assist_incompatible_with_selp1650_and_sel18200le(self) -> None:
        for lens in P348_AF_ASSIST_INCOMPATIBLE_LENSES:
            rep = evaluate_movie_af_focusmap_marker_vault(
                build_default_safe_movie_af_focusmap_marker_vault_spec(
                    af_assist="On",
                    attached_lens_model=lens,
                    reported_af_assist_effective="On",
                )
            )
            self.assertFalse(rep.passed, lens)
            self.assertEqual(rep.block_code, P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF)

    def test_26_63b_fx3_in_body_focus_map_myth_busted_eopnotsupp95(self) -> None:
        rep = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                focus_map_in_body_requested=True,
                fx3_in_body_focus_map_bkid_hits=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF)

    def test_27_63b_fx3_remote_focus_map_fw_mc_app_and_high_fps_gates(self) -> None:
        for kw in (
            {"fw_version": "5.00"},
            {"mc_app_version": "2.0.0"},
            {"recording_fps": 200},
            {"recording_fps": 240},
            {"playback_control_active": True},
            {"auto_framing_active": True},
            {"pdaf_capable_lens_attached": False},
            {"usb_remote_or_uvc_active": True},
        ):
            rep = evaluate_movie_af_focusmap_marker_vault(
                build_default_safe_movie_af_focusmap_marker_vault_spec(**kw)
            )
            self.assertFalse(rep.passed, kw)
            self.assertEqual(rep.block_code, P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF)

    def test_28_63b_fx6_in_body_focus_map_ok_at_60fps_and_locked_at_low_or_high_fps(self) -> None:
        ok_rep = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                focus_map_in_body_requested=True,
                focus_map_remote_mc_requested=False,
                recording_fps=60,
                peaking_color="B&W",
                post_peaking_color="B&W",
            )
        )
        self.assertTrue(ok_rep.passed, ok_rep.errors)

        for bad_fps in (P348_FX6_FOCUS_MAP_LOW_FPS_LOCKOUT_MAX, 150, 240):
            bad_rep = evaluate_movie_af_focusmap_marker_vault(
                build_default_safe_movie_af_focusmap_marker_vault_spec(
                    camera_model=P348_FX6_DONOR_MODEL_NAME,
                    fw_version=P348_FX6_DONOR_FW_VERSION,
                    focus_map_in_body_requested=True,
                    focus_map_remote_mc_requested=False,
                    recording_fps=bad_fps,
                    peaking_color="B&W",
                    post_peaking_color="B&W",
                )
            )
            self.assertFalse(bad_rep.passed, bad_fps)
            self.assertEqual(bad_rep.block_code, P348_BLOCKED_MOVIE_AF_SPEED_OR_FOCUS_MAP_SPOOF)

    def test_29_63b_clean_hdmi_0px_and_marker_hidden_during_focus_magnifier(self) -> None:
        rep_mag = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                marker_display="On",
                focus_magnifier_active=True,
                reported_effective_marker_visible_on_lcd=False,
            )
        )
        self.assertTrue(rep_mag.passed, rep_mag.errors)

        rep_leak = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                hdmi_marker_peaking_pixels_emitted=640
            )
        )
        self.assertFalse(rep_leak.passed)
        self.assertEqual(rep_leak.block_code, P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK)

    def test_30_63b_all_8_marker_peaking_items_survive_camera_reset_and_wipe_on_initialize(self) -> None:
        ok_reset = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                reset_action="Camera Settings Reset"
            )
        )
        self.assertTrue(ok_reset.passed, ok_reset.errors)

        bad_reset = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                reset_action="Camera Settings Reset",
                post_aspect_marker="Off",
            )
        )
        self.assertFalse(bad_reset.passed)
        self.assertEqual(bad_reset.block_code, P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK)

        ok_init = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                reset_action="Initialize",
                post_marker_display="Off",
                post_center_marker="Off",
                post_aspect_marker="Off",
                post_safety_zone="Off",
                post_guideframe="Off",
                post_peaking_display="Off",
                post_peaking_level=P348_FX3_PEAKING_LEVEL_DEFAULT,
                post_peaking_color=P348_FX3_PEAKING_COLOR_DEFAULT,
            )
        )
        self.assertTrue(ok_init.passed, ok_init.errors)

    def test_31_63b_fx3_rejects_bw_peaking_and_92_5_safety_while_fx6_allows(self) -> None:
        bad_bw = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                peaking_color="B&W", post_peaking_color="B&W"
            )
        )
        self.assertFalse(bad_bw.passed)
        self.assertEqual(bad_bw.block_code, P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK)

        bad_925 = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                safety_zone="92.5%", post_safety_zone="92.5%"
            )
        )
        self.assertFalse(bad_925.passed)
        self.assertEqual(bad_925.block_code, P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK)

        bad_fx6_box = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                camera_model=P348_FX6_DONOR_MODEL_NAME,
                fw_version=P348_FX6_DONOR_FW_VERSION,
                focus_map_in_body_requested=True,
                focus_map_remote_mc_requested=False,
                recording_fps=60,
                fx6_user_box_width=480,
                peaking_color="B&W",
                post_peaking_color="B&W",
            )
        )
        self.assertFalse(bad_fx6_box.passed)
        self.assertEqual(bad_fx6_box.block_code, P348_BLOCKED_MARKER_15RATIO_PEAKING_HDMI_LEAK)

    def test_32_63b_slot1_vault_erofs30_overlay_h0_h3_and_invalid_spec(self) -> None:
        rep_vault = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_FULL",
                reported_vault_action_allowed=True,
                slot1_data_sector_writes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
            )
        )
        self.assertFalse(rep_vault.passed)
        self.assertEqual(rep_vault.block_code, P348_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

        rep_inv = evaluate_movie_af_focusmap_marker_vault(
            build_default_safe_movie_af_focusmap_marker_vault_spec(peaking_level="Ultra")
        )
        self.assertFalse(rep_inv.passed)
        self.assertEqual(rep_inv.block_code, P348_BLOCKED_INVALID_PILLAR63B_SPEC)

    # ------------------------------------------------------------------
    # Combined Single-Shot, 6+6 Suites, 63/63 Master, m324 & CLI (33..45)
    # ------------------------------------------------------------------

    def test_33_combined_single_shot_verifier_and_alias(self) -> None:
        rep1 = verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault(force_clean_room=True)
        rep2 = verify_ftp_ftpes_customwb_afspeed_focusmap_marker_vault(force_clean_room=True)
        for rep in (rep1, rep2):
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P348_STATUS_VERIFIED_PILLAR63_SUITE)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self.assertEqual(rep.usblan_packets_transmitted, 0)
            self.assertEqual(rep.hdmi_marker_peaking_pixels_emitted, 0)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_34_pillar63a_and_63b_6_scenario_suites(self) -> None:
        res_a = run_pillar63a_ftp_ftpes_customwb_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.status, P348_STATUS_VERIFIED_PILLAR_63A)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)

        res_b = run_pillar63b_movie_af_focusmap_marker_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.status, P348_STATUS_VERIFIED_PILLAR_63B)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)

    def test_35_pillar63_standalone_suite_normal_and_clean_room(self) -> None:
        for kw in ({}, {"force_clean_room": True}):
            rep = run_pillar63_standalone_suite(**kw)
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P348_STATUS_VERIFIED_PILLAR63_SUITE)
            self.assertEqual(rep.pillar_63a_ftp_ftpes_usblan_customwb_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_63b_movie_af_focusmap_marker_peaking_vault.scenarios_passed, 6)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self.assertEqual(rep.usblan_packets_transmitted, 0)
            self.assertEqual(rep.hdmi_marker_peaking_pixels_emitted, 0)
            self.assertEqual(rep.slot1_data_sector_writes, 0)

    def test_36_master_63pillar_recovery_clean_room_and_deterministic_sha(self) -> None:
        rep1 = evaluate_realhw_63pillar_recovery_master(force_clean_room=True)
        rep2 = evaluate_63pillar_recovery_master(force_clean_room=True)
        rep3 = verify_63pillar_recovery_suite(force_clean_room=True)
        for rep in (rep1, rep2, rep3):
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertEqual(rep.status, P348_STATUS_VERIFIED_63OF63_AGGREGATOR)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.pillar_count, 63)
            self.assertEqual(rep.pillars_passed, 63)
            self.assertEqual(rep.failed_pillars, ())
            self.assertTrue(rep.under_6s_budget)
            self.assertTrue(rep.nominal_under_4_0s)
            self.assertEqual(rep.fx3_appfw_sftp_hits, 0)
            self.assertEqual(rep.fx3_appfw_passive_mode_hits, 0)
            self.assertEqual(rep.fx3_appfw_transfer_jpeg_heif_size_hits, 0)
            self.assertEqual(rep.fx3_ftp_server_slot_count, 9)
            self.assertTrue(rep.fx3_ftp_passive_mode_only)
            self.assertTrue(rep.fx3_usblan_bypasses_airplane_mode)
            self.assertEqual(rep.fx3_wb_custom_slots, 3)
            self.assertTrue(rep.fx3_shutter_awb_lock_reset_immune)
            self.assertEqual(rep.fx3_af_transition_speed_max, 7)
            self.assertEqual(rep.fx3_af_subj_shift_sens_max, 5)
            self.assertEqual(rep.fx6_af_subj_shift_sens_max, 5)
            self.assertEqual(rep.fx3_in_body_focus_map_bkid_hits, 0)
            self.assertEqual(rep.fx3_focus_map_app_only_since_fw, "6.00")
            self.assertEqual(rep.fx3_aspect_marker_active_ratio_count, 15)
            self.assertEqual(rep.fx3_peaking_color_count, 4)
            self.assertEqual(rep.fx3_reset_immune_assist_item_count, 8)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep1.master_63pillar_sha256, rep2.master_63pillar_sha256)
        self.assertEqual(rep1.master_63pillar_sha256, rep3.master_63pillar_sha256)

    def test_37_master_63pillar_fault_injection_pillar63_and_pillar62(self) -> None:
        rep63 = evaluate_realhw_63pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar63_ftp_ftpes_customwb_afspeed_focusmap_marker_vault",
        )
        self.assertFalse(rep63.all_passed)
        self.assertEqual(rep63.pillars_passed, 62)
        self.assertIn("pillar63_ftp_ftpes_customwb_afspeed_focusmap_marker_vault", rep63.failed_pillars)

        rep62 = evaluate_realhw_63pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault",
        )
        self.assertFalse(rep62.all_passed)
        self.assertEqual(rep62.pillars_passed, 62)
        self.assertIn("pillar62_rec_media_autoswitch_proxy_cloud_mymenu_vault", rep62.failed_pillars)

        with self.assertRaises(ValueError):
            evaluate_realhw_63pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_63_plus",
            )

    def test_38_milestone311_and_324_auto_discovery_forward_compatible_ge_63(self) -> None:
        closure_root = str(REPO_ROOT / "outputs/fx6-on-fx3-closure")
        sys.path.insert(0, closure_root)
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
            from fx6_closure import realhw_milestone324_master_gate as m324
        finally:
            if closure_root in sys.path:
                sys.path.remove(closure_root)
        c311, fn311, ids311 = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(c311, 63)
        self.assertTrue(callable(fn311))
        self.assertGreaterEqual(len(ids311), 63)

        c324, fn324, ids324 = m324._discover_highest_recovery_master(fr)
        self.assertGreaterEqual(c324, 63)
        self.assertTrue(callable(fn324))
        self.assertGreaterEqual(len(ids324), 63)

    def test_39_master_63pillar_report_to_dict_roundtrip_and_package_root_exports(self) -> None:
        rep = evaluate_realhw_63pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 63)
        self.assertEqual(parsed["pillars_passed"], 63)
        for sym in (
            "MASTER_63_PILLAR_COUNT",
            "MASTER_63_PILLAR_IDS",
            "MASTER_63_PILLAR_SPECS",
            "Master63PillarRecoveryReport",
            "evaluate_realhw_63pillar_recovery_master",
            "evaluate_63pillar_recovery_master",
            "verify_63pillar_recovery_suite",
            "run_pillar63_standalone_suite",
            "verify_ftp_ftpes_customwb_afspeed_focusmap_marker_and_vault",
            "verify_ftp_ftpes_customwb_afspeed_focusmap_marker_vault",
        ):
            self.assertTrue(hasattr(fr, sym), sym)
            self.assertIn(sym, fr.__all__, sym)

    def test_40_cli_verify_63pillar_recovery_json_normal_and_clean_room(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for args in (
            ["verify-63pillar-recovery", "--json"],
            ["verify-63pillar-recovery", "--force-clean-room", "--json"],
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
            self.assertEqual(payload["pillars_passed"], 63)
            self.assertEqual(payload["pillar_count"], 63)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertLess(payload["elapsed_seconds"], P348_CONCURRENT_CEILING_SECONDS)

    def test_41_cli_verify_pillar63_aliases_text_and_out(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        for subcmd in (
            "verify-pillar63-recovery",
            "verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault",
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
            self.assertIn("VERIFIED_PILLAR63_FTP_FTPES_CUSTOMWB_AFSPEED_FOCUSMAP_MARKER_VAULT", proc_txt.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        tag = f"p348_cli_out_{os.getpid()}"
        out_master_path = work_tests / f"{tag}_master"
        out_p63_path = work_tests / f"{tag}_p63"
        try:
            proc1 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-63pillar-recovery", "--force-clean-room", "--out", str(out_master_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc1.returncode, 0, proc1.stderr or proc1.stdout)
            self.assertTrue((out_master_path / "63pillar-recovery-master-report.json").exists())

            proc2 = subprocess.run(
                [
                    "/usr/bin/python3", "-B", "-m", "fx3_recovery",
                    "verify-pillar63-recovery", "--force-clean-room", "--out", str(out_p63_path),
                ],
                cwd=str(REPO_ROOT),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr or proc2.stdout)
            self.assertTrue(
                (out_p63_path / "pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault-report.json").exists()
            )
        finally:
            for d in (out_master_path, out_p63_path):
                if d.exists():
                    for child in d.iterdir():
                        if child.is_file() or child.is_symlink():
                            child.unlink()
                    d.rmdir()

    def test_42_cli_backward_compat_verify_62pillar_recovery(self) -> None:
        env_base = os.environ.copy()
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(ADAPTER_ROOT)
        proc = subprocess.run(
            ["/usr/bin/python3", "-B", "-m", "fx3_recovery", "verify-62pillar-recovery", "--force-clean-room", "--json"],
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

    def test_43_donorless_ci_mock_master63_and_cli_subprocess_exit_zero(self) -> None:
        from fx3_recovery import __main__ as cli_main
        from fx3_recovery import files as files_mod

        clean_env = {
            k: v
            for k, v in os.environ.items()
            if k not in (P348_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            for mock_roots in ((None,), (Path("/nonexistent-donor-root"),)):
                with patch.object(files_mod, "iter_donor_work_roots", return_value=mock_roots):
                    rep = evaluate_realhw_63pillar_recovery_master()
                    self.assertTrue(rep.all_passed, rep.errors)
                    self.assertEqual(rep.pillars_passed, 63)
                    self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    buf = io.StringIO()
                    with patch.object(sys, "argv", ["fx3_recovery", "verify-63pillar-recovery", "--json"]), redirect_stdout(buf):
                        rc = cli_main.main()
                    self.assertEqual(rc, 0, buf.getvalue())
                    payload = json.loads(buf.getvalue())
                    self.assertTrue(payload["all_passed"])
                    self.assertEqual(payload["pillars_passed"], 63)
                    self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

        sub_env = {
            **clean_env,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ADAPTER_ROOT),
        }
        snippet = (
            "import sys; from unittest.mock import patch; "
            "from fx3_recovery import files as f, __main__ as m; "
            "sys.argv = ['fx3_recovery', 'verify-63pillar-recovery', '--json']; "
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
        self.assertEqual(sub_payload["pillars_passed"], 63)
        self.assertEqual(sub_payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")


# ---------------------------------------------------------------------------
# Programmatic Parametric Matrices (Tests 44..116 => Total >= 115 tests)
# ---------------------------------------------------------------------------


def _make_ftp_slot_protocol_reset_test(
    slot: int, protocol: str, reset_action: str
) -> object:
    def _test(self: Phase348Pillar63VerifierTests) -> None:
        cleared = reset_action in ("Reset Network Set.", "Initialize")
        wb_post = "Auto" if reset_action in ("Camera Settings Reset", "Initialize") else "C.Temp./Filter"
        cust_cleared = reset_action == "Initialize"
        spec = build_default_safe_ftp_ftpes_customwb_vault_spec(
            ftp_server_slot=slot,
            ftp_protocol=protocol,
            reset_action=reset_action,
            post_ftp_servers_cleared=cleared,
            post_wb_mode=wb_post,
            post_custom_wb_slots_cleared=cust_cleared,
        )
        rep = evaluate_ftp_ftpes_customwb_vault(spec)
        self.assertTrue(rep.passed, (slot, protocol, reset_action, rep.errors))
    return _test


def _make_aspect_marker_reset_matrix_test(
    aspect_ratio: str, reset_action: str
) -> object:
    def _test(self: Phase348Pillar63VerifierTests) -> None:
        is_init = reset_action == "Initialize"
        spec = build_default_safe_movie_af_focusmap_marker_vault_spec(
            aspect_marker=aspect_ratio,
            reset_action=reset_action,
            post_af_transition_speed=P348_AF_TRANSITION_SPEED_DEFAULT,
            post_af_subj_shift_sens=P348_AF_SUBJ_SHIFT_SENS_DEFAULT,
            post_af_assist="Off",
            post_marker_display="Off" if is_init else "On",
            post_center_marker="Off" if is_init else "On",
            post_aspect_marker="Off" if is_init else aspect_ratio,
            post_safety_zone="Off" if is_init else "90%",
            post_guideframe="Off" if is_init else "On",
            post_peaking_display="Off" if is_init else "On",
            post_peaking_level=P348_FX3_PEAKING_LEVEL_DEFAULT if is_init else "Mid",
            post_peaking_color=P348_FX3_PEAKING_COLOR_DEFAULT if is_init else "Red",
        )
        rep = evaluate_movie_af_focusmap_marker_vault(spec)
        self.assertTrue(rep.passed, (aspect_ratio, reset_action, rep.errors))
    return _test


def _make_peaking_color_level_matrix_test(
    color: str, level: str
) -> object:
    def _test(self: Phase348Pillar63VerifierTests) -> None:
        spec = build_default_safe_movie_af_focusmap_marker_vault_spec(
            peaking_color=color,
            peaking_level=level,
            post_peaking_color=color,
            post_peaking_level=level,
        )
        rep = evaluate_movie_af_focusmap_marker_vault(spec)
        self.assertTrue(rep.passed, (color, level, rep.errors))
    return _test


def _make_movie_af_parity_matrix_test(
    model: str, speed: int, shift: int
) -> object:
    def _test(self: Phase348Pillar63VerifierTests) -> None:
        fw = P348_FX3_FW_VERSION if model == P348_FX3_MODEL_NAME else P348_FX6_DONOR_FW_VERSION
        is_fx3 = model == P348_FX3_MODEL_NAME
        spec = build_default_safe_movie_af_focusmap_marker_vault_spec(
            camera_model=model,
            fw_version=fw,
            af_transition_speed=speed,
            af_subj_shift_sens=shift,
            focus_map_in_body_requested=not is_fx3,
            focus_map_remote_mc_requested=is_fx3,
            recording_fps=60,
            post_af_transition_speed=speed,
            post_af_subj_shift_sens=shift,
        )
        rep = evaluate_movie_af_focusmap_marker_vault(spec)
        self.assertTrue(rep.passed, (model, speed, shift, rep.errors))
    return _test


def _make_wb_custom_and_shockless_matrix_test(
    wb_slot: str, shockless: str
) -> object:
    def _test(self: Phase348Pillar63VerifierTests) -> None:
        spec = build_default_safe_ftp_ftpes_customwb_vault_spec(
            wb_mode=wb_slot,
            shockless_wb=shockless,
            reported_shockless_wb_effective=shockless,
            reported_shockless_wb_bypassed=(shockless == "Off"),
            post_wb_mode=wb_slot,
            post_shockless_wb=shockless,
        )
        rep = evaluate_ftp_ftpes_customwb_vault(spec)
        self.assertTrue(rep.passed, (wb_slot, shockless, rep.errors))
    return _test


_idx = 44
for _slot in range(1, P348_FTP_SERVER_SLOT_COUNT + 1):
    for _proto in ("FTP", "FTPES"):
        _reset = ("None", "Camera Settings Reset", "Reset Network Set.", "Initialize")[
            (_slot + (0 if _proto == "FTP" else 1)) % 4
        ]
        setattr(
            Phase348Pillar63VerifierTests,
            f"test_{_idx:03d}_ftp_slot{_slot}_{_proto}_{_reset.replace(' ', '_').replace('.', '')}",
            _make_ftp_slot_protocol_reset_test(_slot, _proto, _reset),
        )
        _idx += 1

for _ratio in P348_FX3_ASPECT_MARKER_STATES:
    for _rst in ("Camera Settings Reset", "Initialize"):
        _slug = _ratio.replace(":", "x").replace(".", "_")
        setattr(
            Phase348Pillar63VerifierTests,
            f"test_{_idx:03d}_aspect_marker_{_slug}_{_rst.replace(' ', '_')}",
            _make_aspect_marker_reset_matrix_test(_ratio, _rst),
        )
        _idx += 1

for _col in P348_FX3_PEAKING_COLORS:
    for _lvl in P348_FX3_PEAKING_LEVELS:
        setattr(
            Phase348Pillar63VerifierTests,
            f"test_{_idx:03d}_peaking_{_col}_{_lvl}",
            _make_peaking_color_level_matrix_test(_col, _lvl),
        )
        _idx += 1

for _mdl in (P348_FX3_MODEL_NAME, P348_FX6_DONOR_MODEL_NAME):
    for _spd in range(P348_AF_TRANSITION_SPEED_MIN, P348_AF_TRANSITION_SPEED_MAX + 1):
        _shf = ((_spd - 1) % P348_AF_SUBJ_SHIFT_SENS_MAX) + 1
        setattr(
            Phase348Pillar63VerifierTests,
            f"test_{_idx:03d}_af_parity_{_mdl.replace('-', '_')}_spd{_spd}_shf{_shf}",
            _make_movie_af_parity_matrix_test(_mdl, _spd, _shf),
        )
        _idx += 1

for _wbs in P348_WB_CUSTOM_SLOTS:
    _wb_mode = f"Custom {_wbs}"
    for _swb in ("Off", "1", "2", "3"):
        setattr(
            Phase348Pillar63VerifierTests,
            f"test_{_idx:03d}_wb_Custom_{_wbs}_shockless_{_swb}",
            _make_wb_custom_and_shockless_matrix_test(_wb_mode, _swb),
        )
        _idx += 1


if __name__ == "__main__":
    unittest.main()
