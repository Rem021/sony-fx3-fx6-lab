"""Phase 345 Milestone — 20th Physical Bench Readiness Verifier (`20/20` Milestone!).

Implements `preflight-audio-reclevel-outtiming-4ch-mon-touch-dormant-and-remote-shoot`
aligned with Global Sony Real-Hardware Empirical Intelligence Wave 72 across Check Groups
A–D and the mandatory `16/16 H0 == H3` dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (`Shooting -> [Audio Recording] -> [Audio Rec Level]` `0..31` def `26`
  `adj_audio_rec_level_defult`, `Delete` resets to `26`, `Can be reset`, built-in stereo mic
  & `3.5mm MIC` only with `3.5mm` preempting MI shoe, permanently active non-disableable body
  limiter, `XLR-H1 HANDLE AUDIO = ON` hardware override (`LINE +4 dBu`, `MIC/MIC+48V ATT
  0/10/20 dB = -60/-50/-40 dBu`, `AUTO/MAN(/LINK)`, `0..10` dials), `S&Q` `0ch` 4-item lockout,
  vs `ILME-FX6 Ver. 6.01` `CH1..CH4 Input Select` matrix, 3-tier Reference incl. 5-option
  `Reference Level`, and **6-mode** `Limiter Mode` `Off / -6dB / -9dB / -12dB / -15dB / -17dB`).
- **Check Group B** (`Shooting -> [Audio Recording] -> [Audio Out Timing]` `Live` def / `Lip Sync`,
  `Can be reset`, disabled in `S&Q`; Reset-immune `Setup -> [Sound Option] -> [Volume Settings]`
  `0..15` def `7` + acoustic feedback hazard near `XLR-H1` & `[4ch Audio Monitoring]` exact **5**
  options `CH1/CH2` [def], `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2` debunking `"mono mix"` /
  `CH1+2/CH3+4` / `All` myths; vs `ILME-FX6` `Monitor CH` `7` options incl. `MIX ALL`,
  `Headphone Out` `Stereo/Mono`, `Volume 0..50` menu/status/ASSIGN debunking `"MONITOR VOL +/-"`
  side buttons (`0` hits in `5-024-458-18`), and `SDI OUT` 4ch vs `HDMI` 2ch pair).
- **Check Group C** (`Setup -> [Touch Operation]` strictly **4** Reset-immune items
  `[Touch Operation]`, `[Touch Sensitivity]`, `[Touch Func. in Shooting]` identical across
  Still/Movie/`S&Q`, and `[Swipe Up]`; reject 100% dormant EVF/Alpha symbols `[Touch Panel/Pad]`,
  `[Touch Pad (vertical)]`, `[Touch Shutter]`, `[Touch AE]` (`0` hits in `ilc/2210` on EVF-less
  `ALCIN_UUD`) with `EOPNOTSUPP=95`; verify `[Spot Metering Point]` does not move dynamically
  with tracking box; vs `ILME-FX6` `Touch Function in MF` (`Spot Focus`/`Tracking AF`) +
  Ver. 6.00+ `BIG6` & full-menu touch).
- **Check Group D** (`Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]` Ver. 2.00..7.02
  rename of `PC Remote Function`, Reset-immune / restored only by `Reset Network Set.` or
  `Initialize`: `[Still Img. Save Dest.]` `Destination Only` / `Dest.+Camera` [factory default!] /
  `Camera Only`, `[Save Image Size]`, `[RAW+J Save Image]`, `[RAW+H Save Image]`; PTP USB
  `/dev/usb/sicd_*` & PTP-IP `TCP 15740`; ONLY `Destination Only` streams from RAM with zero card
  writes; factory-default `Dest.+Camera` & `Camera Only` write to `Slot 1` and are firewalled at
  Tier-0 `Slot 1` with `EROFS=30` + Zero-RF `Airplane Mode = On`, vs `ILME-FX6` zero
  `Still Img. Save Dest.` UI; plus `16/16 H0 == H3` dual-media `528 B FX3RCPT1` receipt gate).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import dataclasses
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import (
    is_forced_clean_room,
    iter_work_roots,
    resolve_work_subpath,
)
from .realhw_card_insert_readiness_verifier import (
    BODY_SERIAL_RE,
    DONOR_INSPECTION_MAX_SECONDS,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    HEX32_CID_RE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _is_trivial_hex64,
    build_default_h0_baselines,
)
from .realhw_sd_stageb_bundle_and_uninstaller import SIXTEEN_STORAGE_SURFACES

# ---------------------------------------------------------------------------
# Version / Schema / Go-No-Go / Locked Zero-Telemetry Constants
# ---------------------------------------------------------------------------

P345_VERSION = "phase345_v1"
PHASE_345_VERSION = P345_VERSION

P345_SCHEMA = "realhw_preflight20_audio_reclevel_outtiming_4ch_touch_remoteshoot_v1"
P345_SCHEMA_VERSION = P345_SCHEMA
PHASE_345_SCHEMA = P345_SCHEMA
REALHW_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_SCHEMA = P345_SCHEMA

P345_SONY_HELP_GUIDE_ID = "ilc/2210"
P345_STORAGE_SURFACE_COUNT = 16
P345_HEADER_READ_BYTES = 64

P345_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED = (
    "READONLY_PREFLIGHT20_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED"
)
P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE = (
    "BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE"
)
PHASE_345_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED,
    P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE,
)

P345_CHECK_GROUP_A_ID = "p345_ga_audio_reclevel_xlr_h1_limiter_fx6_ref"
P345_CHECK_GROUP_B_ID = "p345_gb_audio_out_timing_volume_4ch_mon_fx6_monitor"
P345_CHECK_GROUP_C_ID = "p345_gc_touch_operation_dormant_evf_spot_link_fx6"
P345_CHECK_GROUP_D_ID = "p345_gd_remote_shoot_ptp_slot1_erofs_and_tier0"
PHASE_345_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P345_CHECK_GROUP_A_ID,
    P345_CHECK_GROUP_B_ID,
    P345_CHECK_GROUP_C_ID,
    P345_CHECK_GROUP_D_ID,
)

# Errno constants
P345_ERRNO_EPERM = 1
P345_ERRNO_EBUSY = 16
P345_ERRNO_EINVAL = 22
P345_ERRNO_EROFS = 30
P345_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE345_EMMC_WRITE_COUNT = 0
PHASE345_E_ND_ACTUATOR_TX_COUNT = 0
PHASE345_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE345_SLOT1_DATA_SECTOR_WRITES = 0
PHASE345_USB_PACKETS_TRANSMITTED = 0
PHASE345_PASSIVE_TX_BYTES_EMITTED = 0
PHASE345_RAW_FIRMWARE_BYTES_LEAKED = 0

P345_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P345_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P345_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_C", "DMF", "MF")
P345_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")

# ---------------------------------------------------------------------------
# Wave 72 Group A Constants: [Audio Rec Level], Always-On Limiter, XLR-H1 & FX6
# ---------------------------------------------------------------------------

P345_AUDIO_REC_LEVEL_MENU_PATH = "Shooting -> [Audio Recording] -> [Audio Rec Level]"
P345_AUDIO_REC_LEVEL_UXC_RESIDS: Tuple[str, ...] = ("0x63b9", "0x6f0a")
P345_AUDIO_REC_LEVEL_MIN = 0
P345_AUDIO_REC_LEVEL_MAX = 31
P345_AUDIO_REC_LEVEL_STEP_COUNT = 32
P345_AUDIO_REC_LEVEL_DEFAULT = 26
P345_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL = "adj_audio_rec_level_defult"
P345_AUDIO_REC_LEVEL_VAL_PREFIX = "VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_"
P345_AUDIO_RECORDING_FOUR_CONTROL_ITEMS: Tuple[str, ...] = (
    "AUDIO_RECORDING",
    "AUDIO_REC_LEVEL",
    "AUDIO_OUT_TIMING",
    "WIND_NOISE_REDUCT",
)
P345_FX3_BUILTIN_LIMITER_ALWAYS_ON = True
P345_FX3_BUILTIN_LIMITER_DISABLEABLE = False

P345_XLR_H1_UIBIZ_SYMBOL = "UIBIZ_INP_HOTSHOE_XLRMIC"
P345_XLR_H1_INPUT_MODES: Tuple[str, ...] = ("LINE", "MIC", "MIC_PLUS_48V")
P345_XLR_H1_LINE_LEVEL_DBU = 4
P345_XLR_H1_ATT_TO_DBU: Dict[int, int] = {
    0: -60,
    10: -50,
    20: -40,
}
P345_XLR_H1_GAIN_MODES: Tuple[str, ...] = ("AUTO", "MAN", "LINK")
P345_XLR_H1_DIAL_MIN = 0
P345_XLR_H1_DIAL_MAX = 10

P345_FX6_CH1_INPUT_SELECT: Tuple[str, ...] = ("INPUT1", "INTERNAL_MIC", "SHOE_CH1")
P345_FX6_CH2_INPUT_SELECT: Tuple[str, ...] = ("INPUT1", "INPUT2", "INTERNAL_MIC", "SHOE_CH2")
P345_FX6_CH3_INPUT_SELECT: Tuple[str, ...] = ("OFF", "INPUT1", "INTERNAL_MIC", "SHOE_CH1")
P345_FX6_CH4_INPUT_SELECT: Tuple[str, ...] = ("OFF", "INPUT1", "INPUT2", "INTERNAL_MIC", "SHOE_CH2")
P345_FX6_INPUT_MIC_REFERENCE_STEPS: Tuple[str, ...] = (
    "-80dB",
    "-70dB",
    "-60dB",
    "-50dB",
    "-40dB",
    "-30dB",
)
P345_FX6_LINE_INPUT_REFERENCE_STEPS: Tuple[str, ...] = ("+4dB", "0dB", "-3dB", "EBUL")
P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS: Tuple[str, ...] = (
    "-20dB",
    "-18dB",
    "-16dB",
    "-12dB",
    "EBUL",
)
P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS: Tuple[str, ...] = (
    "OFF",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-17dB",
)
P345_FX6_LIMITER_ELF_SYMBOLS: Tuple[str, ...] = (
    "EXTERN_LIMITER_MODE_OFF",
    "EXTERN_LIMITER_MODE_NEGATIVE_6_DB",
    "EXTERN_LIMITER_MODE_NEGATIVE_9_DB",
    "EXTERN_LIMITER_MODE_NEGATIVE_12_DB",
    "EXTERN_LIMITER_MODE_NEGATIVE_15_DB",
    "EXTERN_LIMITER_MODE_NEGATIVE_17_DB",
)

# ---------------------------------------------------------------------------
# Wave 72 Group B Constants: [Audio Out Timing], [Volume Settings], [4ch Audio Monitoring] & FX6
# ---------------------------------------------------------------------------

P345_AUDIO_OUT_TIMING_MENU_PATH = "Shooting -> [Audio Recording] -> [Audio Out Timing]"
P345_AUDIO_OUT_TIMING_UXC_RESIDS: Tuple[str, ...] = ("0x6bc2", "0x62d8")
P345_AUDIO_OUT_TIMING_BKID = "BKID_APP_setting_audio_output_timing"
P345_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("LIVE", "LIP_SYNC")
P345_AUDIO_OUT_TIMING_DEFAULT = "LIVE"

P345_SOUND_OPTION_MENU_PATH = "Setup -> [Sound Option]"
P345_VOLUME_SETTINGS_BASE_RESID16 = "0xe8c9"
P345_VOLUME_SETTINGS_MIN = 0
P345_VOLUME_SETTINGS_MAX = 15
P345_VOLUME_SETTINGS_DEFAULT = 7
P345_VOLUME_SETTINGS_ACOUSTIC_HAZARD_THRESHOLD = 13

P345_4CH_MON_UXC_RESID16 = "0x70dd"
P345_4CH_MON_BKID = "BKID_APP_setting_audio_monitoring_ch"
P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
P345_FX3_4CH_MON_RESIDS: Dict[str, str] = {
    "CH1/CH2": "0x713b",
    "CH3/CH4": "0x6bf6",
    "CH1+3/CH2+4": "0x6c2e",
    "CH1/CH1": "0x6f9c",
    "CH2/CH2": "0x7a26",
}
P345_FX3_4CH_MON_ELF_SYMBOLS: Tuple[str, ...] = (
    "AUDIO_MONITORING_CH_1CH_2CH",
    "AUDIO_MONITORING_CH_3CH_4CH",
    "AUDIO_MONITORING_CH_MIX_ALL",
    "AUDIO_MONITORING_CH_1CH",
    "AUDIO_MONITORING_CH_2CH",
)
P345_FX3_4CH_MON_MYTH_LABELS: Tuple[str, ...] = (
    "CH1/CH2 mono mix",
    "CH1+2/CH3+4",
    "All",
)

P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS: Tuple[str, ...] = (
    "CH1",
    "CH2",
    "CH3",
    "CH4",
    "CH1/CH2",
    "CH3/CH4",
    "MIX_ALL",
)
P345_FX6_HEADPHONE_OUT_MODES: Tuple[str, ...] = ("STEREO", "MONO")
P345_FX6_VOLUME_MIN = 0
P345_FX6_VOLUME_MAX = 50
P345_FX6_SIDE_MONITOR_VOL_BUTTONS_PRESENT = False
P345_FX6_MANUAL_MONITOR_VOL_HITS = 0
P345_FX6_HDMI_AUDIO_CHANNELS = 2
P345_FX6_SDI_AUDIO_CHANNELS = 4

# ---------------------------------------------------------------------------
# Wave 72 Group C Constants: [Touch Operation] 4 Items vs 100% Dormant EVF/Alpha
# ---------------------------------------------------------------------------

P345_TOUCH_OPERATION_MENU_PATH = "Setup -> [Touch Operation]"
P345_TOUCH_OPERATION_RESIDS: Tuple[str, ...] = ("0x6345", "0xe8e3")
P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS: Tuple[str, ...] = (
    "TOUCH_OPERATION",
    "TOUCH_SENSITIVITY",
    "TOUCH_FUNC_IN_SHOOTING",
    "SWIPE_UP",
)
P345_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("ON", "ON_PLAYBACK_ONLY", "OFF")
P345_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("STANDARD", "SENSITIVE")
P345_TOUCH_FUNC_IN_SHOOTING_THREE_OPTIONS: Tuple[str, ...] = (
    "TOUCH_FOCUS",
    "TOUCH_TRACKING",
    "OFF",
)
P345_SWIPE_UP_MODES: Tuple[str, ...] = ("OPEN_THE_FN_MENU", "OFF")

P345_FX3_BUILTIN_EVF_PRESENT = False
P345_DORMANT_TOUCH_SYMBOLS: Dict[str, Tuple[str, str, int]] = {
    "TOUCH_PANEL_PAD": ("0x76ec", "BKID_APP_setting_touch_panel_pad", 0),
    "TOUCH_PAD_VERTICAL": ("0x7312", "BKID_APP_setting_touch_pad_vertical", 0),
    "TOUCH_SHUTTER": (
        "0x6a80",
        "VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER",
        0,
    ),
    "TOUCH_AE": ("0x702a", "PID_SET_TOUCH_SPOT_METER", 0),
}
P345_FX3_TOUCH_SHUTTER_PRESENT = False
P345_FX3_TOUCH_AE_PRESENT = False
P345_FX3_TOUCH_PANEL_PAD_PRESENT = False

P345_SPOT_METERING_POINT_MODES: Tuple[str, ...] = ("CENTER", "FOCUS_POINT_LINK")
P345_SPOT_METERING_FOLLOWS_TRACKING_BOX = False

P345_FX6_TOUCH_FUNCTION_IN_MF_MODES: Tuple[str, ...] = ("SPOT_FOCUS", "TRACKING_AF")
P345_FX6_BIG6_HOME_BKID = "BKID_APP_HOME_SCREEN_STATE"

# ---------------------------------------------------------------------------
# Wave 72 Group D Constants: [Remote Shoot Setting], PTP/PTP-IP & Slot-1 EROFS=30
# ---------------------------------------------------------------------------

P345_REMOTE_SHOOT_MENU_PATH = "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]"
P345_REMOTE_SHOOT_LEGACY_VER1_PATH = "Transfer/Remote -> [PC Remote Function]"
P345_REMOTE_SHOOT_EXACT_FOUR_ITEMS: Tuple[str, ...] = (
    "STILL_IMG_SAVE_DEST",
    "SAVE_IMAGE_SIZE",
    "RAW_J_SAVE_IMAGE",
    "RAW_H_SAVE_IMAGE",
)
P345_STILL_IMG_SAVE_DEST_MODES: Tuple[str, ...] = (
    "DESTINATION_ONLY",
    "DEST_PLUS_CAMERA",
    "CAMERA_ONLY",
)
P345_STILL_IMG_SAVE_DEST_FACTORY_DEFAULT = "DEST_PLUS_CAMERA"
P345_SAVE_IMAGE_SIZE_MODES: Tuple[str, ...] = ("ORIGINAL", "2M")
P345_RAW_J_SAVE_IMAGE_MODES: Tuple[str, ...] = ("RAW_AND_JPEG", "JPEG_ONLY", "RAW_ONLY")
P345_RAW_H_SAVE_IMAGE_MODES: Tuple[str, ...] = ("RAW_AND_HEIF", "HEIF_ONLY", "RAW_ONLY")

P345_PTP_USB_DEV_NODES: Tuple[str, ...] = (
    "/dev/usb/sicd_core",
    "/dev/usb/sicd_data",
    "/dev/usb/sicd_event",
)
P345_PTPIP_TCP_PORT = 15740
P345_PTP_NO_PSEUDO_REC_SYMBOL = "N5model37stillrec_running_without_pseudo_rec_tE"
P345_PTP_MUTEX_SYMBOL = (
    "PRM_HAITA_setting_remote_settings_still_img_save_dest_pc_remote_connection_state"
)
P345_VALID_REMOTE_TRANSPORTS: Tuple[str, ...] = ("NONE", "PTP_USB", "PTP_IP_USBLAN", "WIRELESS_RF")
P345_FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED = False

# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Paths (Wave 72 §5.1)
# ---------------------------------------------------------------------------

P345_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    (
        "fx3_libptp_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libptp.so",
    ),
    (
        "fx3_libinfraptpcontrol_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraPtpControl.so",
    ),
    (
        "fx3_libinfraptpextcmd_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraPtpExtCmd.so",
    ),
    (
        "fx3_libinfraremote_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRemote.so",
    ),
    (
        "fx3_libinframtpserver_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMtpServer.so",
    ),
    (
        "fx3_string_english_f_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
    ),
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx6_libinfraptpcontrol_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraPtpControl.so",
    ),
    (
        "fx6_libinfraremote_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraRemote.so",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P345_GA_ERR_MODEL_OR_FW_FLOOR = "P345_GA_ERR_MODEL_OR_FW_FLOOR"
P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET = "P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET"
P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK = "P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK"
P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH = "P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH"
P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER = (
    "P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER"
)

P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ = "P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ"
P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK = (
    "P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK"
)
P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH = (
    "P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH"
)
P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL = "P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL"

P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY = "P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY"
P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP = (
    "P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP"
)
P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6 = "P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6"

P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE = "P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE"
P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30 = "P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30"
P345_GD_ERR_ZERO_RF_AIRPLANE_MODE_VIOLATION = "P345_GD_ERR_ZERO_RF_AIRPLANE_MODE_VIOLATION"
P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY = "P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY"
P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P345_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P345_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

# ---------------------------------------------------------------------------
# Timing-Stripping & Deterministic Hashing Helpers
# ---------------------------------------------------------------------------

_TIMING_STRIP_EXACT_KEYS = frozenset(
    {
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    }
)


def _strip_timing_fields(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            if k in _TIMING_STRIP_EXACT_KEYS or (
                isinstance(k, str)
                and (
                    k.endswith("_elapsed_ms")
                    or k.endswith("_elapsed_s")
                    or k.endswith("_elapsed_seconds")
                )
            ):
                continue
            cleaned[k] = _strip_timing_fields(v)
        return cleaned
    if isinstance(value, list):
        return [_strip_timing_fields(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_timing_fields(item) for item in value]
    return value


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("report_sha256", None)
    stripped = _strip_timing_fields(body)
    raw = json.dumps(stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _resolve_work_root_or_none() -> Optional[Path]:
    if _is_clean_room_env():
        return None
    for root in iter_work_roots():
        if root.exists():
            return root
    return None


def resolve_phase345_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    if work_root is None:
        return None
    try:
        candidate = resolve_work_subpath(rel_subpath, work_root=work_root)
    except Exception:
        candidate = Path(work_root) / rel_subpath
    return candidate if candidate.exists() and candidate.is_file() else None


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P345_HEADER_READ_BYTES) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase345DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    donors_checked: int
    donors_present: int
    bytes_read_total: int
    header_digests: Dict[str, str]
    raw_firmware_bytes_leaked: int
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_phase345_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase345DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase345DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P345_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P345_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE345_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    for lbl, rel in P345_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            break
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx6_libinfraptpcontrol_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "libInfraPtpControl.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx6_libinfraremote_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "libInfraRemote.so"
            if p.exists() and p.is_file():
                candidate = p
        if candidate is None:
            candidate = resolve_phase345_donor_file_or_none(resolved_work_root, rel)
        if candidate is not None:
            hdr = _read_bounded_header_o_rdonly(candidate, P345_HEADER_READ_BYTES)
            present_count += 1
            bytes_read += len(hdr)
            digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]

    if present_count == 0:
        return Phase345DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P345_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P345_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE345_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    return Phase345DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        donor_tree_present=True,
        donors_checked=len(P345_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE345_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Check Group Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class P345CheckGroupAAudioRecLevelXlrLimiterResult:
    group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    shoot_mode: str
    reset_action: str
    audio_rec_level_menu_path: str
    audio_rec_level: int
    effective_audio_rec_level_after_reset: int
    audio_rec_level_default: int
    delete_key_resets_to_26: bool
    audio_rec_level_resettable: bool
    active_audio_source: str
    audio_rec_level_active: bool
    audio_channels: int
    shoe_audio_grayed_out: bool
    mic_35mm_inserted: bool
    xlr_h1_attached: bool
    xlr_h1_handle_audio: str
    xlr_h1_input_mode: str
    xlr_h1_att_db: int
    xlr_h1_gain_mode: str
    xlr_h1_audio_level: int
    xlr_h1_reference_level_dbu: int
    fx3_builtin_limiter_always_on: bool
    fx3_builtin_limiter_disableable: bool
    fx6_limiter_mode: str
    fx6_limiter_mode_six_options: Tuple[str, ...]
    fx6_reference_level: str
    fx6_reference_level_five_options: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P345CheckGroupBAudioOutTimingVolume4ChMonResult:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    audio_out_timing: str
    effective_audio_out_timing_after_reset: str
    audio_out_timing_active: bool
    audio_out_timing_resettable: bool
    volume_settings: int
    effective_volume_settings_after_reset: int
    volume_settings_reset_immune: bool
    four_ch_audio_monitoring: str
    effective_4ch_monitoring_after_reset: str
    four_ch_monitoring_reset_immune: bool
    exposed_4ch_monitoring_options: Tuple[str, ...]
    acoustic_feedback_hazard_detected: bool
    fx6_monitor_ch: str
    fx6_monitor_ch_seven_options: Tuple[str, ...]
    fx6_headphone_out: str
    fx6_volume: int
    fx6_side_monitor_vol_buttons_present: bool
    fx6_manual_monitor_vol_hits: int
    fx6_sdi_audio_channels: int
    fx6_hdmi_audio_channels: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P345CheckGroupCTouchOperationDormantEvfSpotLinkResult:
    group_id: str
    passed: bool
    shoot_mode: str
    focus_mode: str
    reset_action: str
    exposed_touch_operation_items: Tuple[str, ...]
    touch_operation: str
    touch_sensitivity: str
    touch_func_in_shooting: str
    effective_touch_func_in_shooting: str
    swipe_up: str
    touch_operation_reset_immune: bool
    fx3_builtin_evf_present: bool
    fx3_touch_panel_pad_present: bool
    fx3_touch_shutter_present: bool
    fx3_touch_ae_present: bool
    spot_metering_point: str
    spot_metering_follows_tracking_box: bool
    fx6_touch_operation: str
    fx6_touch_function_in_mf: str
    fx6_spot_focus_in_mf_disabled: bool
    fx6_big6_home_touch_enabled: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P345CheckGroupDRemoteShootPtpSlot1Tier0Result:
    group_id: str
    passed: bool
    reset_action: str
    remote_shoot_menu_path: str
    still_img_save_dest: str
    effective_still_img_save_dest_after_reset: str
    save_image_size: str
    raw_j_save_image: str
    raw_h_save_image: str
    remote_shoot_reset_immune: bool
    restored_by_network_reset_or_init: bool
    usb_connection_mode: str
    remote_transport: str
    airplane_mode: str
    wireless_rf_packets_emitted: int
    pc_remote_connected: bool
    release_wo_card: str
    card_inserted: bool
    recording_media_slot: int
    zero_card_ram_streaming_active: bool
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
    fx6_still_img_save_dest_ui_exposed: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    st_dev_a: Optional[int]
    st_dev_b: Optional[int]
    receipt_body_serial: str
    receipt_emmc_cid: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase345ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P345CheckGroupAAudioRecLevelXlrLimiterResult
    check_group_b: P345CheckGroupBAudioOutTimingVolume4ChMonResult
    check_group_c: P345CheckGroupCTouchOperationDormantEvfSpotLinkResult
    check_group_d: P345CheckGroupDRemoteShootPtpSlot1Tier0Result
    donor_inspection: Phase345DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    slot1_tier0_vault_mutated: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_builtin_limiter_disableable: bool
    fx3_4ch_mon_five_options_exact: bool
    fx6_side_monitor_vol_buttons_present: bool
    fx3_builtin_evf_present: bool
    fx3_touch_panel_pad_present: bool
    fx3_touch_shutter_present: bool
    fx3_touch_ae_present: bool
    fx3_spot_metering_follows_tracking_box: bool
    fx6_still_img_save_dest_ui_exposed: bool
    emmc_write_count: int
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase_version": self.phase_version,
            "sony_help_guide_id": self.sony_help_guide_id,
            "overall_status": self.overall_status,
            "go_no_go": self.go_no_go,
            "verification_mode": self.verification_mode,
            "simulate_bench_dry_run": self.simulate_bench_dry_run,
            "check_group_count": self.check_group_count,
            "check_groups_passed": self.check_groups_passed,
            "check_group_a": self.check_group_a.to_dict(),
            "check_group_b": self.check_group_b.to_dict(),
            "check_group_c": self.check_group_c.to_dict(),
            "check_group_d": self.check_group_d.to_dict(),
            "donor_inspection": self.donor_inspection.to_dict(),
            "tier0_receipt_verified": self.tier0_receipt_verified,
            "receipt_mode": self.receipt_mode,
            "h0_equals_h3_count": self.h0_equals_h3_count,
            "h0_h3_surface_count": self.h0_h3_surface_count,
            "slot1_tier0_vault_mutated": self.slot1_tier0_vault_mutated,
            "overall_ready_for_hardware_attach": self.overall_ready_for_hardware_attach,
            "hardware_live_attachment_authorized": self.hardware_live_attachment_authorized,
            "persistent_emmc_writes_authorized": self.persistent_emmc_writes_authorized,
            "persistent_write_release": self.persistent_write_release,
            "spi_nor_write_authorized": self.spi_nor_write_authorized,
            "el3_payload_transmit_authorized": self.el3_payload_transmit_authorized,
            "sd_physical_media_written": self.sd_physical_media_written,
            "cross_model_flash_authorized": self.cross_model_flash_authorized,
            "rf_nvs_p12_p13_writes_authorized": self.rf_nvs_p12_p13_writes_authorized,
            "fx3_builtin_limiter_disableable": self.fx3_builtin_limiter_disableable,
            "fx3_4ch_mon_five_options_exact": self.fx3_4ch_mon_five_options_exact,
            "fx6_side_monitor_vol_buttons_present": self.fx6_side_monitor_vol_buttons_present,
            "fx3_builtin_evf_present": self.fx3_builtin_evf_present,
            "fx3_touch_panel_pad_present": self.fx3_touch_panel_pad_present,
            "fx3_touch_shutter_present": self.fx3_touch_shutter_present,
            "fx3_touch_ae_present": self.fx3_touch_ae_present,
            "fx3_spot_metering_follows_tracking_box": self.fx3_spot_metering_follows_tracking_box,
            "fx6_still_img_save_dest_ui_exposed": self.fx6_still_img_save_dest_ui_exposed,
            "emmc_write_count": self.emmc_write_count,
            "e_nd_actuator_tx_count": self.e_nd_actuator_tx_count,
            "e_nd_i2c_tx_bytes": self.e_nd_i2c_tx_bytes,
            "rf_packets_transmitted": self.rf_packets_transmitted,
            "wireless_rf_packets_emitted": self.wireless_rf_packets_emitted,
            "rf_nvs_mutation_bytes": self.rf_nvs_mutation_bytes,
            "slot1_data_sector_writes": self.slot1_data_sector_writes,
            "usb_packets_transmitted": self.usb_packets_transmitted,
            "passive_tx_bytes_emitted": self.passive_tx_bytes_emitted,
            "raw_firmware_bytes_leaked": self.raw_firmware_bytes_leaked,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "report_sha256": self.report_sha256,
        }

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        cleaned = _strip_timing_fields(self.to_dict())
        return json.dumps(cleaned, indent=indent, sort_keys=True, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------
# Simulated Tier-0 Dual-Media Receipt Builder
# ---------------------------------------------------------------------------


def build_simulated_phase345_tier0_receipts(
    *,
    body_serial: str = "FX3SIM70200345",
    emmc_cid: str = "11010030303847333000a1b2c3d49345",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE345_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE345_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_a = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    receipt_b = bytes(receipt_a)
    if len(receipt_a) != SD_RECEIPT_BYTES:
        raise AssertionError(f"Expected {SD_RECEIPT_BYTES}B receipt, got {len(receipt_a)}")
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "h0_baselines_a": dict(h0),
        "h0_baselines_b": dict(h0),
        "h3_baselines": dict(h0),
        "receipt_a_bytes": receipt_a,
        "receipt_b_bytes": receipt_b,
        "st_dev_a": 1201,
        "st_dev_b": 1202,
    }


# ---------------------------------------------------------------------------
# Check Group A Evaluator
# ---------------------------------------------------------------------------


def evaluate_p345_check_group_a_audio_reclevel_and_limiter(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P345_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    audio_rec_level: int = P345_AUDIO_REC_LEVEL_DEFAULT,
    delete_key_resets_to_26: bool = True,
    claimed_menu_path_is_shooting_audio: bool = False,
    claimed_audio_rec_level_resists_camera_reset: bool = False,
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "OFF",
    xlr_h1_input_mode: str = "MIC",
    xlr_h1_att_db: int = 10,
    xlr_h1_gain_mode: str = "MAN",
    xlr_h1_audio_level: int = 5,
    expect_xlr_h1_active_over_35mm_mic: bool = False,
    expect_audio_rec_level_controls_xlr_h1: bool = False,
    expect_audio_active_in_sq: bool = False,
    fx3_disable_builtin_limiter_requested: bool = False,
    claimed_fx3_builtin_limiter_has_menu_off: bool = False,
    fx6_ch1_input: str = "INPUT1",
    fx6_ch2_input: str = "INPUT2",
    fx6_ch3_input: str = "OFF",
    fx6_ch4_input: str = "OFF",
    fx6_input_mic_reference: str = "-50dB",
    fx6_line_input_reference: str = "+4dB",
    fx6_reference_level: str = "-20dB",
    fx6_limiter_mode: str = "-6dB",
    claimed_fx6_reference_level_only_3_options: bool = False,
    claimed_fx6_limiter_mode_only_4_options: bool = False,
) -> P345CheckGroupAAudioRecLevelXlrLimiterResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT or body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P345_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw {TARGET_BODY_FW}, "
            f"got 0x{body_model_id:08x} fw {body_fw!r}"
        )
    if sony_help_guide_id != P345_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P345_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P345_SONY_HELP_GUIDE_ID!r}"
        )
    if reset_action not in P345_VALID_RESET_ACTIONS:
        errors.append(f"{P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET}: invalid reset_action {reset_action!r}")
    if shoot_mode not in P345_VALID_SHOOT_MODES:
        errors.append(f"{P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK}: invalid shoot_mode {shoot_mode!r}")

    if not (P345_AUDIO_REC_LEVEL_MIN <= audio_rec_level <= P345_AUDIO_REC_LEVEL_MAX):
        errors.append(
            f"{P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET}: audio_rec_level={audio_rec_level} "
            f"out of range {P345_AUDIO_REC_LEVEL_MIN}..{P345_AUDIO_REC_LEVEL_MAX}"
        )
    if not delete_key_resets_to_26:
        errors.append(
            f"{P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET}: Delete key must reset [Audio Rec Level] to 26"
        )
    if claimed_menu_path_is_shooting_audio:
        errors.append(
            f"{P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET}: exact path is '{P345_AUDIO_REC_LEVEL_MENU_PATH}', NOT 'Shooting -> [Audio]'"
        )
    if claimed_audio_rec_level_resists_camera_reset:
        errors.append(
            f"{P345_GA_ERR_AUDIO_REC_LEVEL_RANGE_PATH_OR_RESET}: [Audio Rec Level] is 'Can be reset' under Camera Settings Reset"
        )

    effective_audio_rec_level = (
        P345_AUDIO_REC_LEVEL_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else audio_rec_level
    )

    if xlr_h1_handle_audio not in P345_VALID_ON_OFF:
        errors.append(f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: invalid xlr_h1_handle_audio {xlr_h1_handle_audio!r}")
    if xlr_h1_input_mode not in P345_XLR_H1_INPUT_MODES:
        errors.append(f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: invalid xlr_h1_input_mode {xlr_h1_input_mode!r}")
    if xlr_h1_att_db not in P345_XLR_H1_ATT_TO_DBU:
        errors.append(f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: invalid xlr_h1_att_db={xlr_h1_att_db} (must be 0, 10, 20)")
    if xlr_h1_gain_mode not in P345_XLR_H1_GAIN_MODES:
        errors.append(f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: invalid xlr_h1_gain_mode {xlr_h1_gain_mode!r}")
    if not (P345_XLR_H1_DIAL_MIN <= xlr_h1_audio_level <= P345_XLR_H1_DIAL_MAX):
        errors.append(f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: xlr_h1_audio_level={xlr_h1_audio_level} out of 0..10")

    xlr_ref_dbu = (
        P345_XLR_H1_LINE_LEVEL_DBU
        if xlr_h1_input_mode == "LINE"
        else P345_XLR_H1_ATT_TO_DBU.get(xlr_h1_att_db, -60)
    )

    if shoot_mode == "S_AND_Q":
        active_source = "SQ_0CH_LOCKED"
        audio_rec_level_active = False
        audio_channels = 0
        shoe_audio_grayed_out = True
    elif mic_35mm_inserted:
        active_source = "BODY_3_5MM_MIC"
        audio_rec_level_active = True
        audio_channels = 2
        shoe_audio_grayed_out = True
    elif xlr_h1_attached and xlr_h1_handle_audio == "ON":
        active_source = "XLR_H1_MI_SHOE"
        audio_rec_level_active = False
        audio_channels = 4 if xlr_h1_input_mode != "LINE" or xlr_h1_gain_mode != "LINK" else 4
        shoe_audio_grayed_out = False
    else:
        active_source = "INTERNAL_STEREO_MIC"
        audio_rec_level_active = True
        audio_channels = 2
        shoe_audio_grayed_out = False

    if expect_xlr_h1_active_over_35mm_mic:
        errors.append(
            f"{P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK}: 3.5mm MIC preempts XLR-H1 / MI shoe"
        )
    if expect_audio_rec_level_controls_xlr_h1:
        errors.append(
            f"{P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK}: [Audio Rec Level] is grayed out when XLR-H1 HANDLE AUDIO=ON governs"
        )
    if expect_audio_active_in_sq:
        errors.append(
            f"{P345_GA_ERR_AUDIO_SOURCE_PREEMPTION_OR_SQ_LOCK}: S&Q mode forces 0ch and locks all 4 audio items"
        )

    if fx3_disable_builtin_limiter_requested or claimed_fx3_builtin_limiter_has_menu_off:
        errors.append(
            f"{P345_GA_ERR_BUILTIN_LIMITER_OR_XLR_H1_SWITCH}: FX3 body limiter always operates with zero menu Off switch"
        )

    if (
        fx6_ch1_input not in P345_FX6_CH1_INPUT_SELECT
        or fx6_ch2_input not in P345_FX6_CH2_INPUT_SELECT
        or fx6_ch3_input not in P345_FX6_CH3_INPUT_SELECT
        or fx6_ch4_input not in P345_FX6_CH4_INPUT_SELECT
    ):
        errors.append(f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: invalid FX6 CH1..CH4 Input Select")
    if fx6_input_mic_reference not in P345_FX6_INPUT_MIC_REFERENCE_STEPS:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: invalid FX6 INPUT1/2 MIC Reference {fx6_input_mic_reference!r}"
        )
    if fx6_line_input_reference not in P345_FX6_LINE_INPUT_REFERENCE_STEPS:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: invalid FX6 Line Input Reference {fx6_line_input_reference!r}"
        )
    if fx6_reference_level not in P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: invalid FX6 Reference Level {fx6_reference_level!r}"
        )
    if claimed_fx6_reference_level_only_3_options:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: FX6 Reference Level has 5 options (-20/-18/-16/-12dB/EBUL), NOT 3"
        )
    if fx6_limiter_mode not in P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: invalid FX6 Limiter Mode {fx6_limiter_mode!r}"
        )
    if claimed_fx6_limiter_mode_only_4_options:
        errors.append(
            f"{P345_GA_ERR_FX6_MATRIX_REFERENCE_OR_6MODE_LIMITER}: FX6 Limiter Mode has 6 modes (Off/-6/-9/-12/-15/-17dB), NOT 4"
        )

    if shoot_mode == "S_AND_Q":
        warnings.append("S&Q Motion forces 0ch silent capture and grays out all 4 audio items.")

    return P345CheckGroupAAudioRecLevelXlrLimiterResult(
        group_id=P345_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        body_model_id_hex=f"0x{body_model_id:08x}",
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        audio_rec_level_menu_path=P345_AUDIO_REC_LEVEL_MENU_PATH,
        audio_rec_level=audio_rec_level,
        effective_audio_rec_level_after_reset=effective_audio_rec_level,
        audio_rec_level_default=P345_AUDIO_REC_LEVEL_DEFAULT,
        delete_key_resets_to_26=delete_key_resets_to_26,
        audio_rec_level_resettable=True,
        active_audio_source=active_source,
        audio_rec_level_active=audio_rec_level_active,
        audio_channels=audio_channels,
        shoe_audio_grayed_out=shoe_audio_grayed_out,
        mic_35mm_inserted=mic_35mm_inserted,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        xlr_h1_input_mode=xlr_h1_input_mode,
        xlr_h1_att_db=xlr_h1_att_db,
        xlr_h1_gain_mode=xlr_h1_gain_mode,
        xlr_h1_audio_level=xlr_h1_audio_level,
        xlr_h1_reference_level_dbu=xlr_ref_dbu,
        fx3_builtin_limiter_always_on=P345_FX3_BUILTIN_LIMITER_ALWAYS_ON,
        fx3_builtin_limiter_disableable=P345_FX3_BUILTIN_LIMITER_DISABLEABLE,
        fx6_limiter_mode=fx6_limiter_mode,
        fx6_limiter_mode_six_options=P345_FX6_LIMITER_MODE_EXACT_SIX_OPTIONS,
        fx6_reference_level=fx6_reference_level,
        fx6_reference_level_five_options=P345_FX6_REFERENCE_LEVEL_FIVE_OPTIONS,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator
# ---------------------------------------------------------------------------


def evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    audio_out_timing: str = P345_AUDIO_OUT_TIMING_DEFAULT,
    claimed_audio_out_timing_under_setup: bool = False,
    claimed_audio_out_timing_resists_camera_reset: bool = False,
    expect_audio_out_timing_active_in_sq: bool = False,
    volume_settings: int = P345_VOLUME_SETTINGS_DEFAULT,
    claimed_volume_settings_wiped_by_camera_reset: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "OFF",
    speaker_monitor_unmuted_near_mic: bool = False,
    four_ch_audio_monitoring: str = "CH1/CH2",
    exposed_4ch_monitoring_options: Tuple[str, ...] = P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS,
    claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all: bool = False,
    claimed_4ch_monitoring_wiped_by_camera_reset: bool = False,
    fx6_monitor_ch: str = "CH1/CH2",
    fx6_headphone_out: str = "STEREO",
    fx6_volume: int = 25,
    claimed_fx6_has_side_monitor_vol_buttons: bool = False,
    claimed_fx6_hdmi_carries_4ch_audio: bool = False,
    claimed_fx6_sdi_limited_to_2ch_audio: bool = False,
) -> P345CheckGroupBAudioOutTimingVolume4ChMonResult:
    errors: List[str] = []
    warnings: List[str] = []

    if audio_out_timing not in P345_AUDIO_OUT_TIMING_MODES:
        errors.append(
            f"{P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ}: invalid audio_out_timing {audio_out_timing!r}"
        )
    if claimed_audio_out_timing_under_setup:
        errors.append(
            f"{P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ}: [Audio Out Timing] lives under '{P345_AUDIO_OUT_TIMING_MENU_PATH}', NOT Setup"
        )
    if claimed_audio_out_timing_resists_camera_reset:
        errors.append(
            f"{P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ}: [Audio Out Timing] is 'Can be reset' under Camera Settings Reset"
        )
    if expect_audio_out_timing_active_in_sq:
        errors.append(
            f"{P345_GB_ERR_AUDIO_OUT_TIMING_PATH_RESET_OR_SQ}: [Audio Out Timing] is disabled in S&Q mode"
        )

    audio_out_timing_active = shoot_mode != "S_AND_Q"
    effective_audio_out_timing = (
        P345_AUDIO_OUT_TIMING_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else audio_out_timing
    )

    if not (P345_VOLUME_SETTINGS_MIN <= volume_settings <= P345_VOLUME_SETTINGS_MAX):
        errors.append(
            f"{P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK}: volume_settings={volume_settings} out of 0..15"
        )
    if claimed_volume_settings_wiped_by_camera_reset:
        errors.append(
            f"{P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK}: Setup -> [Sound Option] -> [Volume Settings] is Reset-immune (Initialize only)"
        )
    effective_volume = (
        P345_VOLUME_SETTINGS_DEFAULT if reset_action == "INITIALIZE" else volume_settings
    )

    acoustic_feedback_hazard = (
        speaker_monitor_unmuted_near_mic
        and volume_settings >= P345_VOLUME_SETTINGS_ACOUSTIC_HAZARD_THRESHOLD
        and xlr_h1_attached
        and xlr_h1_handle_audio == "ON"
    )
    if acoustic_feedback_hazard:
        errors.append(
            f"{P345_GB_ERR_VOLUME_SETTINGS_OR_ACOUSTIC_FEEDBACK}: high speaker volume={volume_settings} near active XLR-H1 risks acoustic feedback howl"
        )

    if tuple(exposed_4ch_monitoring_options) != P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS:
        errors.append(
            f"{P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH}: exposed options {exposed_4ch_monitoring_options!r} != exact 5 {P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS!r}"
        )
    if four_ch_audio_monitoring not in P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS:
        errors.append(
            f"{P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH}: invalid [4ch Audio Monitoring] {four_ch_audio_monitoring!r}"
        )
    if claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all:
        errors.append(
            f"{P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH}: 'CH1/CH2 mono mix', 'CH1+2/CH3+4', and 'All' are debunked myths"
        )
    if claimed_4ch_monitoring_wiped_by_camera_reset:
        errors.append(
            f"{P345_GB_ERR_4CH_MONITORING_FIVE_OPTIONS_OR_MYTH}: Setup -> [Sound Option] -> [4ch Audio Monitoring] is Reset-immune (Initialize only)"
        )
    effective_4ch_mon = "CH1/CH2" if reset_action == "INITIALIZE" else four_ch_audio_monitoring

    if fx6_monitor_ch not in P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS:
        errors.append(
            f"{P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL}: invalid FX6 Monitor CH {fx6_monitor_ch!r} (must be in 7 options)"
        )
    if fx6_headphone_out not in P345_FX6_HEADPHONE_OUT_MODES:
        errors.append(
            f"{P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL}: invalid FX6 Headphone Out {fx6_headphone_out!r}"
        )
    if not (P345_FX6_VOLUME_MIN <= fx6_volume <= P345_FX6_VOLUME_MAX):
        errors.append(
            f"{P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL}: fx6_volume={fx6_volume} out of 0..50"
        )
    if claimed_fx6_has_side_monitor_vol_buttons:
        errors.append(
            f"{P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL}: FX6 has ZERO 'MONITOR VOL +/-' side buttons (0 hits in 5-024-458-18)"
        )
    if claimed_fx6_hdmi_carries_4ch_audio or claimed_fx6_sdi_limited_to_2ch_audio:
        errors.append(
            f"{P345_GB_ERR_FX6_MONITOR_CH_7_OR_NO_SIDE_VOL}: FX6 SDI OUT carries 4ch while HDMI carries 2ch pair"
        )

    if audio_out_timing == "LIP_SYNC":
        warnings.append("Audio Out Timing=Lip Sync adds video buffer latency; may cause speech echo in headphones.")

    return P345CheckGroupBAudioOutTimingVolume4ChMonResult(
        group_id=P345_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        audio_out_timing=audio_out_timing,
        effective_audio_out_timing_after_reset=effective_audio_out_timing,
        audio_out_timing_active=audio_out_timing_active,
        audio_out_timing_resettable=True,
        volume_settings=volume_settings,
        effective_volume_settings_after_reset=effective_volume,
        volume_settings_reset_immune=True,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        effective_4ch_monitoring_after_reset=effective_4ch_mon,
        four_ch_monitoring_reset_immune=True,
        exposed_4ch_monitoring_options=tuple(exposed_4ch_monitoring_options),
        acoustic_feedback_hazard_detected=acoustic_feedback_hazard,
        fx6_monitor_ch=fx6_monitor_ch,
        fx6_monitor_ch_seven_options=P345_FX6_MONITOR_CH_EXACT_SEVEN_OPTIONS,
        fx6_headphone_out=fx6_headphone_out,
        fx6_volume=fx6_volume,
        fx6_side_monitor_vol_buttons_present=P345_FX6_SIDE_MONITOR_VOL_BUTTONS_PRESENT,
        fx6_manual_monitor_vol_hits=P345_FX6_MANUAL_MONITOR_VOL_HITS,
        fx6_sdi_audio_channels=P345_FX6_SDI_AUDIO_CHANNELS,
        fx6_hdmi_audio_channels=P345_FX6_HDMI_AUDIO_CHANNELS,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator
# ---------------------------------------------------------------------------


def evaluate_p345_check_group_c_touch_dormant_and_spot_link(
    *,
    shoot_mode: str = "MOVIE",
    focus_mode: str = "AF_C",
    reset_action: str = "NONE",
    exposed_touch_operation_items: Tuple[str, ...] = P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS,
    touch_operation: str = "ON",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    swipe_up: str = "OPEN_THE_FN_MENU",
    claimed_touch_operation_wiped_by_camera_reset: bool = False,
    claimed_touch_func_differs_in_movie_or_sq: bool = False,
    dormant_touch_panel_pad_requested: bool = False,
    dormant_touch_pad_vertical_requested: bool = False,
    dormant_touch_shutter_requested: bool = False,
    dormant_touch_ae_requested: bool = False,
    claimed_fx3_touch_panel_pad_present: bool = False,
    claimed_fx3_touch_shutter_present: bool = False,
    claimed_fx3_touch_ae_present: bool = False,
    claimed_fx3_has_builtin_evf: bool = False,
    spot_metering_point: str = "CENTER",
    expect_spot_metering_follows_tracking_box: bool = False,
    fx6_touch_operation: str = "ON",
    fx6_touch_function_in_mf: str = "SPOT_FOCUS",
    fx6_manual_lens: bool = False,
    fx6_desqueeze_not_off: bool = False,
    fx6_focus_magnifier_active: bool = False,
    expect_fx6_spot_focus_in_mf_during_lockout: bool = False,
    claimed_fx6_lacks_big6_or_mf_touch: bool = False,
) -> P345CheckGroupCTouchOperationDormantEvfSpotLinkResult:
    errors: List[str] = []
    warnings: List[str] = []

    if tuple(exposed_touch_operation_items) != P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: expected exact 4 items {P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS!r}, "
            f"got {exposed_touch_operation_items!r}"
        )
    if touch_operation not in P345_TOUCH_OPERATION_MODES:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: invalid touch_operation {touch_operation!r}"
        )
    if touch_sensitivity not in P345_TOUCH_SENSITIVITY_MODES:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: invalid touch_sensitivity {touch_sensitivity!r}"
        )
    if touch_func_in_shooting not in P345_TOUCH_FUNC_IN_SHOOTING_THREE_OPTIONS:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: invalid touch_func_in_shooting {touch_func_in_shooting!r}"
        )
    if swipe_up not in P345_SWIPE_UP_MODES:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: invalid swipe_up {swipe_up!r}"
        )
    if claimed_touch_operation_wiped_by_camera_reset:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: all 4 Setup -> [Touch Operation] items are Reset-immune"
        )
    if claimed_touch_func_differs_in_movie_or_sq:
        errors.append(
            f"{P345_GC_ERR_TOUCH_FOUR_ITEMS_OR_RESET_IMMUNITY}: [Touch Func. in Shooting] has identical 3 options across Still, Movie, and S&Q"
        )

    effective_touch_func = (
        "TOUCH_FOCUS"
        if focus_mode == "MF" and touch_func_in_shooting == "TOUCH_TRACKING"
        else touch_func_in_shooting
    )
    if reset_action == "INITIALIZE":
        effective_touch_func = "TOUCH_TRACKING" if focus_mode != "MF" else "TOUCH_FOCUS"

    if (
        dormant_touch_panel_pad_requested
        or dormant_touch_pad_vertical_requested
        or dormant_touch_shutter_requested
        or dormant_touch_ae_requested
    ):
        errors.append(
            f"{P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP}: errno={P345_ERRNO_EOPNOTSUPP} "
            "(EOPNOTSUPP): dormant Touch Panel/Pad, Touch Shutter, and Touch AE are 100% disabled on ALCIN_UUD (0 ilc/2210 hits)"
        )
    if (
        claimed_fx3_touch_panel_pad_present
        or claimed_fx3_touch_shutter_present
        or claimed_fx3_touch_ae_present
        or claimed_fx3_has_builtin_evf
    ):
        errors.append(
            f"{P345_GC_ERR_DORMANT_TOUCH_SHUTTER_AE_PAD_EOPNOTSUPP}: EVF-less FX3 Ver. 7.02 exposes zero Touch Panel/Pad, Touch Shutter, or Touch AE"
        )

    if spot_metering_point not in P345_SPOT_METERING_POINT_MODES:
        errors.append(
            f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: invalid spot_metering_point {spot_metering_point!r}"
        )
    if expect_spot_metering_follows_tracking_box:
        errors.append(
            f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: [Spot Metering Point] does NOT move dynamically with a tracking box"
        )

    if fx6_touch_operation not in P345_VALID_ON_OFF:
        errors.append(f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: invalid fx6_touch_operation {fx6_touch_operation!r}")
    if fx6_touch_function_in_mf not in P345_FX6_TOUCH_FUNCTION_IN_MF_MODES:
        errors.append(
            f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: invalid fx6_touch_function_in_mf {fx6_touch_function_in_mf!r}"
        )
    fx6_spot_focus_in_mf_disabled = (
        fx6_manual_lens or fx6_desqueeze_not_off or fx6_focus_magnifier_active
    )
    if expect_fx6_spot_focus_in_mf_during_lockout and fx6_spot_focus_in_mf_disabled:
        errors.append(
            f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: FX6 Spot Focus in MF is disabled under manual lens, De-Squeeze!=Off, or Focus Magnifier"
        )
    if claimed_fx6_lacks_big6_or_mf_touch:
        errors.append(
            f"{P345_GC_ERR_SPOT_METERING_TRACKING_BOX_OR_FX6}: FX6 Ver. 6.00+ supports BIG6 & full-menu touch plus Touch Function in MF"
        )

    return P345CheckGroupCTouchOperationDormantEvfSpotLinkResult(
        group_id=P345_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        reset_action=reset_action,
        exposed_touch_operation_items=tuple(exposed_touch_operation_items),
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        effective_touch_func_in_shooting=effective_touch_func,
        swipe_up=swipe_up,
        touch_operation_reset_immune=True,
        fx3_builtin_evf_present=P345_FX3_BUILTIN_EVF_PRESENT,
        fx3_touch_panel_pad_present=P345_FX3_TOUCH_PANEL_PAD_PRESENT,
        fx3_touch_shutter_present=P345_FX3_TOUCH_SHUTTER_PRESENT,
        fx3_touch_ae_present=P345_FX3_TOUCH_AE_PRESENT,
        spot_metering_point=spot_metering_point,
        spot_metering_follows_tracking_box=P345_SPOT_METERING_FOLLOWS_TRACKING_BOX,
        fx6_touch_operation=fx6_touch_operation,
        fx6_touch_function_in_mf=fx6_touch_function_in_mf,
        fx6_spot_focus_in_mf_disabled=fx6_spot_focus_in_mf_disabled,
        fx6_big6_home_touch_enabled=True,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D + Dual-Media Tier-0 Receipt Gate Evaluator
# ---------------------------------------------------------------------------


def _extract_tier0_evidence(
    *,
    simulate_bench_dry_run: bool,
    receipt_a_bytes: Optional[bytes],
    receipt_b_bytes: Optional[bytes],
    receipt_a_path: Optional[Path],
    receipt_b_path: Optional[Path],
    st_dev_a_override: Optional[int],
    st_dev_b_override: Optional[int],
    body_model_id: int,
    body_fw: str,
    body_serial: Optional[str],
    emmc_cid: Optional[str],
    h0_baselines_a: Optional[Mapping[str, str]],
    h0_baselines_b: Optional[Mapping[str, str]],
    h3_baselines: Optional[Mapping[str, str]],
    simulated_h0_h3_drifted_surfaces: int,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if simulated_h0_h3_drifted_surfaces != 0:
        errors.append(
            f"{P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated_h0_h3_drifted_surfaces={simulated_h0_h3_drifted_surfaces} != 0"
        )

    if simulate_bench_dry_run:
        sim = build_simulated_phase345_tier0_receipts(
            body_serial=body_serial or "FX3SIM70200345",
            emmc_cid=emmc_cid or "11010030303847333000a1b2c3d49345",
        )
        ra = receipt_a_bytes if receipt_a_bytes is not None else sim["receipt_a_bytes"]
        rb = receipt_b_bytes if receipt_b_bytes is not None else sim["receipt_b_bytes"]
        dev_a = st_dev_a_override if st_dev_a_override is not None else sim["st_dev_a"]
        dev_b = st_dev_b_override if st_dev_b_override is not None else sim["st_dev_b"]
        h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else sim["h0_baselines_a"]
        h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else sim["h0_baselines_b"]
        h3 = dict(h3_baselines) if h3_baselines is not None else sim["h3_baselines"]
        receipt_mode = "DRY_RUN_SIMULATED_RECEIPT"
    else:
        ra = receipt_a_bytes
        rb = receipt_b_bytes
        dev_a = st_dev_a_override
        dev_b = st_dev_b_override
        if ra is None and receipt_a_path is not None:
            p_a = Path(receipt_a_path)
            if not p_a.exists() or not p_a.is_file():
                errors.append(f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_a {p_a}")
            else:
                if dev_a is None:
                    dev_a = int(os.stat(p_a).st_dev)
                ra = _read_bounded_header_o_rdonly(p_a, SD_RECEIPT_BYTES + 1)
        if rb is None and receipt_b_path is not None:
            p_b = Path(receipt_b_path)
            if not p_b.exists() or not p_b.is_file():
                errors.append(f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_b {p_b}")
            else:
                if dev_b is None:
                    dev_b = int(os.stat(p_b).st_dev)
                rb = _read_bounded_header_o_rdonly(p_b, SD_RECEIPT_BYTES + 1)
        h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
        h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None
        h3 = dict(h3_baselines) if h3_baselines is not None else None
        receipt_mode = (
            "PHYSICAL_DUAL_MEDIA_RECEIPT"
            if (ra is not None and rb is not None)
            else "AWAITING_PHYSICAL_TIER0_RECEIPT"
        )

    if ra is None or rb is None:
        if ra is not None or rb is not None:
            errors.append(
                f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media requires BOTH receipt_a and receipt_b"
            )
        else:
            warnings.append("Awaiting physical dual-media 528-byte FX3RCPT1 Tier-0 receipts (rc=2).")
        return {
            "receipt_provided": False,
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": "",
            "emmc_cid": "",
            "errors": tuple(errors),
            "warnings": tuple(warnings),
        }

    if len(ra) != SD_RECEIPT_BYTES or len(rb) != SD_RECEIPT_BYTES:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt lengths ({len(ra)}, {len(rb)}) != {SD_RECEIPT_BYTES}"
        )
        return {
            "receipt_provided": True,
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": "",
            "emmc_cid": "",
            "errors": tuple(errors),
            "warnings": tuple(warnings),
        }

    if dev_a is None or dev_b is None or dev_a == dev_b:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media requires distinct st_dev ({dev_a} vs {dev_b})"
        )

    if ra != rb:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a != receipt_b byte parity failure"
        )

    parsed_a: Optional[Any] = None
    parsed_b: Optional[Any] = None
    try:
        parsed_a = parse_sd_backup_receipt_bytes(ra)
        parsed_b = parse_sd_backup_receipt_bytes(rb)
    except Exception as exc:
        errors.append(f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: parse error {exc}")

    if parsed_a is None or parsed_b is None:
        return {
            "receipt_provided": True,
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": (emmc_cid or "").lower(),
            "errors": tuple(errors),
            "warnings": tuple(warnings),
        }

    if not getattr(parsed_a, "valid", False):
        errs_a = "; ".join(getattr(parsed_a, "errors", ()))
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a invalid ({errs_a})"
        )
    if not getattr(parsed_b, "valid", False):
        errs_b = "; ".join(getattr(parsed_b, "errors", ()))
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b invalid ({errs_b})"
        )
    if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))):
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a trivial manifest_sha256"
        )
    if _is_trivial_hex64(str(getattr(parsed_b, "manifest_sha256", ""))):
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b trivial manifest_sha256"
        )

    eff_serial = body_serial if body_serial is not None else "FX3SIM70200345"
    eff_cid = (emmc_cid if emmc_cid is not None else "11010030303847333000a1b2c3d49345").lower()

    if (
        not BODY_SERIAL_RE.match(eff_serial)
        or eff_serial.lower() in FORBIDDEN_TRIVIAL_SERIALS
        or len(set(eff_serial)) <= 1
    ):
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: trivial or invalid body_serial={eff_serial!r}"
        )
    if not HEX32_CID_RE.match(eff_cid) or eff_cid in FORBIDDEN_TRIVIAL_CIDS:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: trivial or invalid emmc_cid={eff_cid!r}"
        )
    if body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: firmware {body_fw!r} != {TARGET_BODY_FW!r}"
        )
    if body_model_id != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P345_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: model_id 0x{body_model_id:08x} != {TARGET_MODEL_ID_HEX}"
        )

    auto_h0 = build_default_h0_baselines(body_serial=eff_serial, emmc_cid=eff_cid)
    if h0_a is None:
        h0_a = dict(auto_h0)
    if h0_b is None:
        h0_b = dict(auto_h0)
    if h3 is None:
        h3 = dict(h0_a)

    receipt_ok_so_far = (
        getattr(parsed_a, "valid", False)
        and getattr(parsed_b, "valid", False)
        and ra == rb
        and not _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", "")))
    )
    if not receipt_ok_so_far or not h0_a or not h0_b or not h3:
        h0_eq_h3 = 0
    else:
        key_mismatches = sum(
            1
            for key in REQUIRED_H0_BASELINE_KEYS
            if _is_trivial_hex64(str(h0_a.get(key, "")))
            or str(h0_a.get(key, "")).lower() != str(h0_b.get(key, "")).lower()
            or str(h0_a.get(key, "")).lower() != str(h3.get(key, "")).lower()
        )
        surface_mismatches = sum(
            1
            for surf in SIXTEEN_STORAGE_SURFACES
            if h0_a.get(surf) != h0_b.get(surf) or h0_a.get(surf) != h3.get(surf)
        )
        extra_keys = set(h0_a.keys()) | set(h0_b.keys()) | set(h3.keys())
        extra_mismatches = sum(
            1
            for k in extra_keys
            if (k in h0_a) != (k in h3)
            or (k in h0_a) != (k in h0_b)
            or str(h0_a.get(k, "")).lower() != str(h3.get(k, "")).lower()
            or str(h0_a.get(k, "")).lower() != str(h0_b.get(k, "")).lower()
        )
        drifted = max(
            0,
            int(simulated_h0_h3_drifted_surfaces),
            key_mismatches,
            surface_mismatches,
            extra_mismatches,
        )
        h0_eq_h3 = max(0, P345_STORAGE_SURFACE_COUNT - drifted)

    if h0_eq_h3 != P345_STORAGE_SURFACE_COUNT:
        errors.append(
            f"{P345_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity failed ({h0_eq_h3}/{P345_STORAGE_SURFACE_COUNT})"
        )

    return {
        "receipt_provided": True,
        "tier0_receipt_verified": len(errors) == 0 and h0_eq_h3 == P345_STORAGE_SURFACE_COUNT,
        "receipt_mode": receipt_mode,
        "h0_equals_h3_count": h0_eq_h3,
        "st_dev_a": dev_a,
        "st_dev_b": dev_b,
        "body_serial": eff_serial,
        "emmc_cid": eff_cid,
        "errors": tuple(errors),
        "warnings": tuple(warnings),
    }


def evaluate_p345_check_group_d_remote_shoot_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    reset_action: str = "NONE",
    still_img_save_dest: str = "DESTINATION_ONLY",
    save_image_size: str = "2M",
    raw_j_save_image: str = "JPEG_ONLY",
    raw_h_save_image: str = "HEIF_ONLY",
    claimed_still_img_save_dest_default_is_destination_only: bool = False,
    claimed_remote_shoot_wiped_by_camera_reset: bool = False,
    claimed_remote_shoot_retains_ver1_pc_remote_menu: bool = False,
    usb_connection_mode: str = "REMOTE_SHOOTING",
    remote_transport: str = "PTP_USB",
    airplane_mode: str = "ON",
    pc_remote_connected: bool = False,
    change_save_dest_while_connected_requested: bool = False,
    release_wo_card: str = "ENABLE",
    card_inserted: bool = False,
    recording_media_slot: int = 1,
    remote_shoot_capture_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
    expect_dest_plus_camera_zero_card_write: bool = False,
    expect_camera_only_shoots_without_card: bool = False,
    claimed_fx6_exposes_still_img_save_dest_ui: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> P345CheckGroupDRemoteShootPtpSlot1Tier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if still_img_save_dest not in P345_STILL_IMG_SAVE_DEST_MODES:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: invalid still_img_save_dest {still_img_save_dest!r}"
        )
    if save_image_size not in P345_SAVE_IMAGE_SIZE_MODES:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: invalid save_image_size {save_image_size!r}"
        )
    if raw_j_save_image not in P345_RAW_J_SAVE_IMAGE_MODES:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: invalid raw_j_save_image {raw_j_save_image!r}"
        )
    if raw_h_save_image not in P345_RAW_H_SAVE_IMAGE_MODES:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: invalid raw_h_save_image {raw_h_save_image!r}"
        )
    if claimed_still_img_save_dest_default_is_destination_only:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: factory default is 'Dest.+Camera', NOT 'Destination Only'!"
        )
    if claimed_remote_shoot_wiped_by_camera_reset:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: [Remote Shoot Setting] resists Camera Settings Reset (Network Reset/Initialize only)"
        )
    if claimed_remote_shoot_retains_ver1_pc_remote_menu:
        errors.append(
            f"{P345_GD_ERR_REMOTE_SHOOT_RENAME_OR_PERSISTENCE}: Ver. 2.00..7.02 renamed 'PC Remote Function' to '{P345_REMOTE_SHOOT_MENU_PATH}'"
        )

    restored_by_net_or_init = reset_action in ("RESET_NETWORK_SET", "INITIALIZE")
    effective_save_dest = (
        P345_STILL_IMG_SAVE_DEST_FACTORY_DEFAULT
        if restored_by_net_or_init
        else still_img_save_dest
    )

    if remote_transport not in P345_VALID_REMOTE_TRANSPORTS:
        errors.append(f"{P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY}: invalid remote_transport {remote_transport!r}")
    if remote_transport == "PTP_USB" and usb_connection_mode != "REMOTE_SHOOTING":
        errors.append(
            f"{P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY}: PTP USB requires [USB Connection Mode]=REMOTE_SHOOTING"
        )
    if airplane_mode != "ON" or remote_transport == "WIRELESS_RF" or wireless_rf_packets_emitted != 0:
        errors.append(
            f"{P345_GD_ERR_ZERO_RF_AIRPLANE_MODE_VIOLATION}: Zero-RF bench requires Airplane Mode=ON, zero WIRELESS_RF transport, and rf_packets=0"
        )

    if change_save_dest_while_connected_requested and pc_remote_connected:
        errors.append(
            f"{P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY}: errno={P345_ERRNO_EBUSY} (EBUSY) {P345_PTP_MUTEX_SYMBOL} blocks changing [Still Img. Save Dest.] while connected"
        )
    if claimed_fx6_exposes_still_img_save_dest_ui:
        errors.append(
            f"{P345_GD_ERR_PTP_MUTEX_OR_FX6_PARITY}: ILME-FX6 exposes 0 [Still Img. Save Dest.] UI items (Monitor & Control / Camera Remote Control)"
        )

    zero_card_ram_streaming_active = effective_save_dest == "DESTINATION_ONLY"

    if expect_dest_plus_camera_zero_card_write:
        errors.append(
            f"{P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30}: factory-default Dest.+Camera writes to [Recording Media] (Slot 1), NOT zero-card RAM"
        )
    if expect_camera_only_shoots_without_card:
        errors.append(
            f"{P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30}: Camera Only rejects shutter without a card even if [Release w/o Card]=Enable"
        )

    slot1_writes_blocked = (
        slot1_contains_tier0_dump
        and (
            slot1_write_requested
            or (
                remote_shoot_capture_requested
                and not zero_card_ram_streaming_active
                and recording_media_slot == 1
            )
            or (
                restored_by_net_or_init
                and remote_shoot_capture_requested
                and recording_media_slot == 1
            )
        )
    )
    if slot1_writes_blocked:
        errors.append(
            f"{P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30}: errno={P345_ERRNO_EROFS} (EROFS) Tier-0 Slot 1 firewall blocked "
            f"remote shoot card write under {effective_save_dest!r}"
        )

    if remote_shoot_capture_requested and not zero_card_ram_streaming_active and not card_inserted:
        errors.append(
            f"{P345_GD_ERR_SLOT1_REMOTE_SHOOT_EROFS30}: {effective_save_dest!r} refuses shutter with no card inserted"
        )

    if not zero_card_ram_streaming_active and slot1_contains_tier0_dump and recording_media_slot == 1:
        warnings.append(
            f"Warning: effective Still Img. Save Dest. is {effective_save_dest!r}; Slot 1 Tier-0 EROFS=30 firewall armed."
        )

    if (
        emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
        or claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P345_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: fail-closed hardware redline violated"
        )

    tier0 = _extract_tier0_evidence(
        simulate_bench_dry_run=simulate_bench_dry_run,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
    )
    errors.extend(tier0["errors"])
    warnings.extend(tier0["warnings"])

    return P345CheckGroupDRemoteShootPtpSlot1Tier0Result(
        group_id=P345_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        reset_action=reset_action,
        remote_shoot_menu_path=P345_REMOTE_SHOOT_MENU_PATH,
        still_img_save_dest=still_img_save_dest,
        effective_still_img_save_dest_after_reset=effective_save_dest,
        save_image_size=save_image_size,
        raw_j_save_image=raw_j_save_image,
        raw_h_save_image=raw_h_save_image,
        remote_shoot_reset_immune=True,
        restored_by_network_reset_or_init=restored_by_net_or_init,
        usb_connection_mode=usb_connection_mode,
        remote_transport=remote_transport,
        airplane_mode=airplane_mode,
        wireless_rf_packets_emitted=PHASE345_WIRELESS_RF_PACKETS_EMITTED,
        pc_remote_connected=pc_remote_connected,
        release_wo_card=release_wo_card,
        card_inserted=card_inserted,
        recording_media_slot=recording_media_slot,
        zero_card_ram_streaming_active=zero_card_ram_streaming_active,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_data_sector_writes=PHASE345_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        fx6_still_img_save_dest_ui_exposed=P345_FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P345_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 345 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P345_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "AF_C",
    # Group A
    audio_rec_level: int = P345_AUDIO_REC_LEVEL_DEFAULT,
    delete_key_resets_to_26: bool = True,
    claimed_menu_path_is_shooting_audio: bool = False,
    claimed_audio_rec_level_resists_camera_reset: bool = False,
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "OFF",
    xlr_h1_input_mode: str = "MIC",
    xlr_h1_att_db: int = 10,
    xlr_h1_gain_mode: str = "MAN",
    xlr_h1_audio_level: int = 5,
    expect_xlr_h1_active_over_35mm_mic: bool = False,
    expect_audio_rec_level_controls_xlr_h1: bool = False,
    expect_audio_active_in_sq: bool = False,
    fx3_disable_builtin_limiter_requested: bool = False,
    claimed_fx3_builtin_limiter_has_menu_off: bool = False,
    fx6_ch1_input: str = "INPUT1",
    fx6_ch2_input: str = "INPUT2",
    fx6_ch3_input: str = "OFF",
    fx6_ch4_input: str = "OFF",
    fx6_input_mic_reference: str = "-50dB",
    fx6_line_input_reference: str = "+4dB",
    fx6_reference_level: str = "-20dB",
    fx6_limiter_mode: str = "-6dB",
    claimed_fx6_reference_level_only_3_options: bool = False,
    claimed_fx6_limiter_mode_only_4_options: bool = False,
    # Group B
    audio_out_timing: str = P345_AUDIO_OUT_TIMING_DEFAULT,
    claimed_audio_out_timing_under_setup: bool = False,
    claimed_audio_out_timing_resists_camera_reset: bool = False,
    expect_audio_out_timing_active_in_sq: bool = False,
    volume_settings: int = P345_VOLUME_SETTINGS_DEFAULT,
    claimed_volume_settings_wiped_by_camera_reset: bool = False,
    speaker_monitor_unmuted_near_mic: bool = False,
    four_ch_audio_monitoring: str = "CH1/CH2",
    exposed_4ch_monitoring_options: Tuple[str, ...] = P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS,
    claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all: bool = False,
    claimed_4ch_monitoring_wiped_by_camera_reset: bool = False,
    fx6_monitor_ch: str = "CH1/CH2",
    fx6_headphone_out: str = "STEREO",
    fx6_volume: int = 25,
    claimed_fx6_has_side_monitor_vol_buttons: bool = False,
    claimed_fx6_hdmi_carries_4ch_audio: bool = False,
    claimed_fx6_sdi_limited_to_2ch_audio: bool = False,
    # Group C
    exposed_touch_operation_items: Tuple[str, ...] = P345_FX3_TOUCH_OPERATION_EXACT_FOUR_ITEMS,
    touch_operation: str = "ON",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    swipe_up: str = "OPEN_THE_FN_MENU",
    claimed_touch_operation_wiped_by_camera_reset: bool = False,
    claimed_touch_func_differs_in_movie_or_sq: bool = False,
    dormant_touch_panel_pad_requested: bool = False,
    dormant_touch_pad_vertical_requested: bool = False,
    dormant_touch_shutter_requested: bool = False,
    dormant_touch_ae_requested: bool = False,
    claimed_fx3_touch_panel_pad_present: bool = False,
    claimed_fx3_touch_shutter_present: bool = False,
    claimed_fx3_touch_ae_present: bool = False,
    claimed_fx3_has_builtin_evf: bool = False,
    spot_metering_point: str = "CENTER",
    expect_spot_metering_follows_tracking_box: bool = False,
    fx6_touch_operation: str = "ON",
    fx6_touch_function_in_mf: str = "SPOT_FOCUS",
    fx6_manual_lens: bool = False,
    fx6_desqueeze_not_off: bool = False,
    fx6_focus_magnifier_active: bool = False,
    expect_fx6_spot_focus_in_mf_during_lockout: bool = False,
    claimed_fx6_lacks_big6_or_mf_touch: bool = False,
    # Group D + Tier-0
    still_img_save_dest: str = "DESTINATION_ONLY",
    save_image_size: str = "2M",
    raw_j_save_image: str = "JPEG_ONLY",
    raw_h_save_image: str = "HEIF_ONLY",
    claimed_still_img_save_dest_default_is_destination_only: bool = False,
    claimed_remote_shoot_wiped_by_camera_reset: bool = False,
    claimed_remote_shoot_retains_ver1_pc_remote_menu: bool = False,
    usb_connection_mode: str = "REMOTE_SHOOTING",
    remote_transport: str = "PTP_USB",
    airplane_mode: str = "ON",
    pc_remote_connected: bool = False,
    change_save_dest_while_connected_requested: bool = False,
    release_wo_card: str = "ENABLE",
    card_inserted: bool = False,
    recording_media_slot: int = 1,
    remote_shoot_capture_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
    expect_dest_plus_camera_zero_card_write: bool = False,
    expect_camera_only_shoots_without_card: bool = False,
    claimed_fx6_exposes_still_img_save_dest_ui: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport:
    donor = inspect_phase345_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p345_check_group_a_audio_reclevel_and_limiter(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        audio_rec_level=audio_rec_level,
        delete_key_resets_to_26=delete_key_resets_to_26,
        claimed_menu_path_is_shooting_audio=claimed_menu_path_is_shooting_audio,
        claimed_audio_rec_level_resists_camera_reset=claimed_audio_rec_level_resists_camera_reset,
        mic_35mm_inserted=mic_35mm_inserted,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        xlr_h1_input_mode=xlr_h1_input_mode,
        xlr_h1_att_db=xlr_h1_att_db,
        xlr_h1_gain_mode=xlr_h1_gain_mode,
        xlr_h1_audio_level=xlr_h1_audio_level,
        expect_xlr_h1_active_over_35mm_mic=expect_xlr_h1_active_over_35mm_mic,
        expect_audio_rec_level_controls_xlr_h1=expect_audio_rec_level_controls_xlr_h1,
        expect_audio_active_in_sq=expect_audio_active_in_sq,
        fx3_disable_builtin_limiter_requested=fx3_disable_builtin_limiter_requested,
        claimed_fx3_builtin_limiter_has_menu_off=claimed_fx3_builtin_limiter_has_menu_off,
        fx6_ch1_input=fx6_ch1_input,
        fx6_ch2_input=fx6_ch2_input,
        fx6_ch3_input=fx6_ch3_input,
        fx6_ch4_input=fx6_ch4_input,
        fx6_input_mic_reference=fx6_input_mic_reference,
        fx6_line_input_reference=fx6_line_input_reference,
        fx6_reference_level=fx6_reference_level,
        fx6_limiter_mode=fx6_limiter_mode,
        claimed_fx6_reference_level_only_3_options=claimed_fx6_reference_level_only_3_options,
        claimed_fx6_limiter_mode_only_4_options=claimed_fx6_limiter_mode_only_4_options,
    )

    gb = evaluate_p345_check_group_b_outtiming_volume_and_4ch_mon(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        audio_out_timing=audio_out_timing,
        claimed_audio_out_timing_under_setup=claimed_audio_out_timing_under_setup,
        claimed_audio_out_timing_resists_camera_reset=claimed_audio_out_timing_resists_camera_reset,
        expect_audio_out_timing_active_in_sq=expect_audio_out_timing_active_in_sq,
        volume_settings=volume_settings,
        claimed_volume_settings_wiped_by_camera_reset=claimed_volume_settings_wiped_by_camera_reset,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        speaker_monitor_unmuted_near_mic=speaker_monitor_unmuted_near_mic,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        exposed_4ch_monitoring_options=exposed_4ch_monitoring_options,
        claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all=claimed_4ch_monitoring_has_mono_mix_or_ch1_2_ch3_4_or_all,
        claimed_4ch_monitoring_wiped_by_camera_reset=claimed_4ch_monitoring_wiped_by_camera_reset,
        fx6_monitor_ch=fx6_monitor_ch,
        fx6_headphone_out=fx6_headphone_out,
        fx6_volume=fx6_volume,
        claimed_fx6_has_side_monitor_vol_buttons=claimed_fx6_has_side_monitor_vol_buttons,
        claimed_fx6_hdmi_carries_4ch_audio=claimed_fx6_hdmi_carries_4ch_audio,
        claimed_fx6_sdi_limited_to_2ch_audio=claimed_fx6_sdi_limited_to_2ch_audio,
    )

    gc = evaluate_p345_check_group_c_touch_dormant_and_spot_link(
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        reset_action=reset_action,
        exposed_touch_operation_items=exposed_touch_operation_items,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        swipe_up=swipe_up,
        claimed_touch_operation_wiped_by_camera_reset=claimed_touch_operation_wiped_by_camera_reset,
        claimed_touch_func_differs_in_movie_or_sq=claimed_touch_func_differs_in_movie_or_sq,
        dormant_touch_panel_pad_requested=dormant_touch_panel_pad_requested,
        dormant_touch_pad_vertical_requested=dormant_touch_pad_vertical_requested,
        dormant_touch_shutter_requested=dormant_touch_shutter_requested,
        dormant_touch_ae_requested=dormant_touch_ae_requested,
        claimed_fx3_touch_panel_pad_present=claimed_fx3_touch_panel_pad_present,
        claimed_fx3_touch_shutter_present=claimed_fx3_touch_shutter_present,
        claimed_fx3_touch_ae_present=claimed_fx3_touch_ae_present,
        claimed_fx3_has_builtin_evf=claimed_fx3_has_builtin_evf,
        spot_metering_point=spot_metering_point,
        expect_spot_metering_follows_tracking_box=expect_spot_metering_follows_tracking_box,
        fx6_touch_operation=fx6_touch_operation,
        fx6_touch_function_in_mf=fx6_touch_function_in_mf,
        fx6_manual_lens=fx6_manual_lens,
        fx6_desqueeze_not_off=fx6_desqueeze_not_off,
        fx6_focus_magnifier_active=fx6_focus_magnifier_active,
        expect_fx6_spot_focus_in_mf_during_lockout=expect_fx6_spot_focus_in_mf_during_lockout,
        claimed_fx6_lacks_big6_or_mf_touch=claimed_fx6_lacks_big6_or_mf_touch,
    )

    gd = evaluate_p345_check_group_d_remote_shoot_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        reset_action=reset_action,
        still_img_save_dest=still_img_save_dest,
        save_image_size=save_image_size,
        raw_j_save_image=raw_j_save_image,
        raw_h_save_image=raw_h_save_image,
        claimed_still_img_save_dest_default_is_destination_only=claimed_still_img_save_dest_default_is_destination_only,
        claimed_remote_shoot_wiped_by_camera_reset=claimed_remote_shoot_wiped_by_camera_reset,
        claimed_remote_shoot_retains_ver1_pc_remote_menu=claimed_remote_shoot_retains_ver1_pc_remote_menu,
        usb_connection_mode=usb_connection_mode,
        remote_transport=remote_transport,
        airplane_mode=airplane_mode,
        pc_remote_connected=pc_remote_connected,
        change_save_dest_while_connected_requested=change_save_dest_while_connected_requested,
        release_wo_card=release_wo_card,
        card_inserted=card_inserted,
        recording_media_slot=recording_media_slot,
        remote_shoot_capture_requested=remote_shoot_capture_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_write_requested=slot1_write_requested,
        expect_dest_plus_camera_zero_card_write=expect_dest_plus_camera_zero_card_write,
        expect_camera_only_shoots_without_card=expect_camera_only_shoots_without_card,
        claimed_fx6_exposes_still_img_save_dest_ui=claimed_fx6_exposes_still_img_save_dest_ui,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        usb_packets_transmitted=usb_packets_transmitted,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
    )

    groups = (ga, gb, gc, gd)
    groups_passed = sum(1 for g in groups if g.passed)
    all_errors = ga.errors + gb.errors + gc.errors + gd.errors
    all_warnings = ga.warnings + gb.warnings + gc.warnings + gd.warnings

    if all_errors:
        go_no_go = P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE
        overall_status = P345_GO_NO_GO_BLOCKED_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_FAILURE
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P345_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED
        overall_status = P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED

    report = RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport(
        schema_version=P345_SCHEMA,
        phase_version=P345_VERSION,
        sony_help_guide_id=sony_help_guide_id,
        overall_status=overall_status,
        go_no_go=go_no_go,
        verification_mode=donor.verification_mode,
        simulate_bench_dry_run=bool(simulate_bench_dry_run),
        check_group_count=len(groups),
        check_groups_passed=groups_passed,
        check_group_a=ga,
        check_group_b=gb,
        check_group_c=gc,
        check_group_d=gd,
        donor_inspection=donor,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        receipt_mode=gd.receipt_mode,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        h0_h3_surface_count=P345_STORAGE_SURFACE_COUNT,
        slot1_tier0_vault_mutated=False,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_builtin_limiter_disableable=P345_FX3_BUILTIN_LIMITER_DISABLEABLE,
        fx3_4ch_mon_five_options_exact=tuple(exposed_4ch_monitoring_options)
        == P345_FX3_4CH_AUDIO_MONITORING_EXACT_FIVE_OPTIONS,
        fx6_side_monitor_vol_buttons_present=P345_FX6_SIDE_MONITOR_VOL_BUTTONS_PRESENT,
        fx3_builtin_evf_present=P345_FX3_BUILTIN_EVF_PRESENT,
        fx3_touch_panel_pad_present=P345_FX3_TOUCH_PANEL_PAD_PRESENT,
        fx3_touch_shutter_present=P345_FX3_TOUCH_SHUTTER_PRESENT,
        fx3_touch_ae_present=P345_FX3_TOUCH_AE_PRESENT,
        fx3_spot_metering_follows_tracking_box=P345_SPOT_METERING_FOLLOWS_TRACKING_BOX,
        fx6_still_img_save_dest_ui_exposed=P345_FX6_STILL_IMG_SAVE_DEST_UI_EXPOSED,
        emmc_write_count=PHASE345_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE345_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE345_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE345_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=0,
        slot1_data_sector_writes=PHASE345_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE345_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE345_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE345_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport(
        **{
            **report.to_dict(),
            "check_group_a": ga,
            "check_group_b": gb,
            "check_group_c": gc,
            "check_group_d": gd,
            "donor_inspection": donor,
            "report_sha256": digest,
        }
    )


def run_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
    **kwargs: Any,
) -> RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport:
    return evaluate_realhw_audio_reclevel_outtiming_4ch_mon_touch_dormant_and_remote_shoot_preflight(
        **kwargs
    )


def verify_phase345_report(
    payload: Union[
        Mapping[str, Any],
        RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport,
    ],
) -> Phase345ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P345_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P345_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P345_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_345_VALID_GO_NO_GO_VALUES:
        errors.append(f"invalid go_no_go: {payload.get('go_no_go')!r}")

    locked_false_fields = (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_builtin_limiter_disableable",
        "fx6_side_monitor_vol_buttons_present",
        "fx3_builtin_evf_present",
        "fx3_touch_panel_pad_present",
        "fx3_touch_shutter_present",
        "fx3_touch_ae_present",
        "fx3_spot_metering_follows_tracking_box",
        "fx6_still_img_save_dest_ui_exposed",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "emmc_write_count",
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "rf_nvs_mutation_bytes",
        "slot1_data_sector_writes",
        "usb_packets_transmitted",
        "passive_tx_bytes_emitted",
        "raw_firmware_bytes_leaked",
    )
    for field in locked_zero_fields:
        if payload.get(field) != 0:
            errors.append(f"hard-locked zero telemetry {field} must be 0")

    expected_sha = _canonical_sha256_dict(payload)
    if payload.get("report_sha256") != expected_sha:
        errors.append(f"report_sha256 mismatch: {payload.get('report_sha256')!r} != {expected_sha!r}")

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P345_GO_NO_GO_AUDIO_RECLEVEL_OUTTIMING_4CH_MON_TOUCH_DORMANT_AND_REMOTE_SHOOT_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase345ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase345_markdown(
    report: RealHwAudioRecLevelOutTiming4ChMonTouchDormantAndRemoteShootReport,
) -> str:
    lines = [
        f"# Phase 345 — 20th Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `ready_attach={report.overall_ready_for_hardware_attach}`, "
        f"`emmc_writes={report.persistent_emmc_writes_authorized}`, "
        f"`emmc_write_count={report.emmc_write_count}`, "
        f"`cross_model_flash={report.cross_model_flash_authorized}`, "
        f"`rf_pkts={report.rf_packets_transmitted}`, `slot1_writes={report.slot1_data_sector_writes}`, "
        f"`usb_pkts={report.usb_packets_transmitted}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"rec_level=`{report.check_group_a.audio_rec_level}` (default=`{report.check_group_a.audio_rec_level_default}`, "
        f"source=`{report.check_group_a.active_audio_source}`, limiter_always_on=`{report.check_group_a.fx3_builtin_limiter_always_on}`, "
        f"fx6_limiter=`{report.check_group_a.fx6_limiter_mode}` in {len(report.check_group_a.fx6_limiter_mode_six_options)} modes)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"out_timing=`{report.check_group_b.audio_out_timing}`, volume=`{report.check_group_b.volume_settings}` "
        f"(reset_immune=`{report.check_group_b.volume_settings_reset_immune}`), "
        f"4ch_mon=`{report.check_group_b.four_ch_audio_monitoring}` "
        f"({len(report.check_group_b.exposed_4ch_monitoring_options)} options), "
        f"fx6_side_vol=`{report.check_group_b.fx6_side_monitor_vol_buttons_present}`",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"items={len(report.check_group_c.exposed_touch_operation_items)}, "
        f"touch_func=`{report.check_group_c.touch_func_in_shooting}`, "
        f"dormant=(pad:`{report.check_group_c.fx3_touch_panel_pad_present}`, "
        f"shutter:`{report.check_group_c.fx3_touch_shutter_present}`, "
        f"ae:`{report.check_group_c.fx3_touch_ae_present}`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"save_dest=`{report.check_group_d.still_img_save_dest}` (effective=`{report.check_group_d.effective_still_img_save_dest_after_reset}`, "
        f"ram_streaming=`{report.check_group_d.zero_card_ram_streaming_active}`, "
        f"airplane=`{report.check_group_d.airplane_mode}`, slot1_mut=`{report.check_group_d.slot1_tier0_vault_mutated}`)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
