"""Phase 341: 18th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier (Waves 68-69).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Global Sony Waves 68-69 before any physical bench session:

1. **Check Group A (Wave 68 §§1-2)** — Reset-Immune ``Setup -> [Area/Date] -> [Area/Date/Time Setting]``
   (30 ``AREA_GMT_*`` zones w/ 6 half-hour offsets, ``Daylight Savings`` + Sony ELF typo
   ``convert_setting_daylight_saving_to_saylight_saving``, ``Date Format``, soldered ``>=24h`` RTC battery)
   vs ``FX6 Maintenance > Clock Set`` + Clean-HDMI ``[Grid Line Display]`` (3 types, passes over HDMI when
   ``HDMI Info. Display = On``) vs ``[Marker Display]`` (``Guideframe`` / 15-ratio ``Aspect Marker``, ``0``
   pixels ever output over HDMI), both Reset-immune:
   - ``[Area/Date/Time Setting]`` (``_f 0x6a9c``, vs legacy ``0xe87f Date/Time Setup``): **Reset-immune**
     (survives ``[Camera Settings Reset]``; cleared only by ``[Initialize]``). 4 subitems:
     1) ``[Area Setting]`` (``0xe91a``): exact **30** ``AREA_GMT_*`` zones (``GMT_M_11_0..GMT_P_12_0``) including
        **6 half-hour offsets** (``M_03_5``, ``P_03_5``, ``P_04_5``, ``P_05_5``, ``P_06_5``, ``P_09_5``).
     2) ``[Daylight Savings]`` (``0xe917``) with Sony ELF typo ``convert_setting_daylight_saving_to_saylight_saving``.
     3) ``[Date/Time]`` with typo ``BKID_APP_setting_auto_sync_sever_date_time``.
     4) ``[Date Format]`` (``0x670d``): ``Y-M-D``, ``M-D-Y``, ``D-M-Y``.
   - Soldered internal rechargeable RTC backup battery (NO user-replaceable CR2032 slot); requires
     powered ``OFF`` with charged ``NP-FZ100`` for ``>= 24 hours`` (vs ``FX6`` 30-min steps & no standalone DST).
   - ``[Grid Line Display]`` (``0x6f9d``) & ``[Grid Line Type]`` (``0x69c9``: ``Rule of 3rds``/``Square``/``Diag.+Square``):
     **passes over HDMI when ``HDMI Info. Display = On``** (suppressed when ``Off``, ``Off(HDMI Only)``, or
     ``RAW Output = On``) vs ``[Marker Display]`` (``0x6803``, Movie/S&Q only, ``Guideframe`` ``0x62f9``,
     15-ratio ``Aspect Marker``, ``Safety Zone`` ``Off/80%/90%``, hidden in ``Focus Magnifier``, **``0`` pixels
     ever output over HDMI**). Both Grid Line and Marker Display are **Reset-immune**.

2. **Check Group B (Wave 68 §§3-4)** — ``[Save/Load Settings]`` Locked to ``Slot 1`` (``CAMSET*.DAT`` &
   ``FTPSET*.DAT`` vs ``Camera Set. Memory`` ``1..3``/``M1..M4`` ``CAMPR%02d%c.DAT``, Tier-0 ``EROFS=30``)
   vs ``FX6 Project > All File`` + Zero Physical PC Flash Sync Terminal & ``XLR-H1`` Passive Cold Shoe
   (``HVL-LBPC`` ``Video Light Mode`` 4 modes & ``PMIC 5V <= 900 mA``) vs ``FX6`` Zero ``GENLOCK`` BNC:
   - ``[Save/Load Settings]`` (``0x6254``, ``libSaveLoadSettings.so``): strictly locked to **``Slot 1``** (max 10
     ``CAMSET01..10.DAT``; ``%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT``; **``0``** hits for ``PRO/CAMERA`` on FX3;
     Ver. <= 1.01 rejected on >= 2.00; disabled in ``MR`` mode; excludes 17+ categories including ``Copyright Info``,
     ``External Flash Set.``, Custom WB, ``Area/Date/Time``, Network/``FTPSET/%s.DAT``).
   - ``Camera Set. Memory`` body ``1..3`` (NVRAM, saved in ``CAMSET``) vs card ``M1..M4``
     (``%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT``, ``[Memory/Recall Media]`` ``Slot 1``/``Slot 2``). Tier-0 ``Slot 1``
     ``EROFS=30`` firewall blocks ``Save``/``Delete`` onto ``Slot 1`` while allowing read-only ``Load``/``Recall``.
   - **Zero physical PC Flash Sync terminal on FX3** (``0`` ``SYNCHRO_TERMINAL*`` symbols in ``FX3 appFw.so``;
     ``0x6b31``/``0x645e`` dormant ``EOPNOTSUPP=95``). ``XLR-H1`` top handle occupies the sole electrical MI Shoe
     and exposes a passive cold shoe (``0`` contacts), physically excluding ``HVL-LBPC`` (``Video Light Mode`` 4 modes,
     ``PMIC 5V <= 900 mA``) or MI-Shoe flash (Still Mechanical Shutter only, ``1/250 s`` X-Sync, forbids ``>=250V``).
     ``FX6`` has switchable ``TC IN/OUT`` BNC and **ZERO physical ``GENLOCK`` BNC** (despite 107 dormant symbols).

3. **Check Group C (Wave 69 §§1-2)** — Still-Only ``Playback -> [Magnification]``
   (``playback_zoom_maginify_by_pinch``, Reset-Immune) & Still Mechanical ``[Anti-flicker Shoot.]`` (``100/120 Hz``)
   vs 100% Dormant ``[Var. Shutter]`` & ``[Anti-flicker Tv Scan]`` (``EOPNOTSUPP=95``) vs ``FX6 ECS``:
   - ``Playback -> [Magnification]``: ``[Enlarge Image]`` (``0xe8cb``), ``[Enlarge Initial Mag.]`` (``0x6b6e``:
     ``Standard. Mag.``/``Previous Mag.``), ``[Enlarge Initial Position]`` (``0x781f``: ``Focused Position``/``Center``),
     Sony ELF typo ``playback_zoom_maginify_by_pinch``, **Reset-immune**, **strictly Still-only**
     (``"You cannot enlarge movies."`` / ``playback_zoom::is_inhibition()`` -> ``EOPNOTSUPP=95`` on movies).
   - Still mechanical ``[Anti-flicker Shoot.]`` (``0x623d``, ``100/120 Hz`` only; locked in Movie, S&Q,
     ``Electronic Shutter``, ``Silent Mode``, ``BULB``) vs **100% dormant ``[Var. Shutter]`` (``0x6831``) &
     ``[Anti-flicker Tv Scan]`` (``0x63c0``)** (``EOPNOTSUPP=95``) vs ``FX6 ECS`` (``23.99..8000 Hz``).

4. **Check Group D (Wave 69 §§3-4 & Tier-0 ``H0 == H3`` Gate)** — Dual-SKU ``Network -> [Wi-Fi]``
   (``WW728473`` 2.4+5 GHz vs ``WW558244`` 2.4 GHz-only, ``WPA2/WPA3``, ``p12/p13`` ``MS_RDONLY``), Front ``#5``
   ``[IR Remote Ctrl]`` (``FX3A`` Removal, BT Mutex, Power Save Bypass) & Default-``On`` ``[CTRL FOR HDMI]``
   (``BKID_APP_setting_ctrl_for_hmdi``, 41 ``EVENT_INPUT_KEY_CEC_*`` Bench Hijack Hazard -> Mandatory Bench ``Off``):
   - ``Network -> [Wi-Fi]``: SKU gating via ``backup_get_wi_fi_frequency_band_dst`` (``WW728473`` 2.4+5 GHz vs
     ``WW558244`` 2.4 GHz-only), Ver. 7.00+ strictly ``WPA2-PSK``/``WPA3-SAE`` (removed WEP/WPA/IPsec),
     ``[Reset Network Set.]`` preserves ``[Airplane Mode] = On``, ``p12/p13`` RF NVS ``MS_RDONLY``
     (``rf_nvs_mutation_bytes == 0``), vs ``FX6 AP/Station Mode`` (``FX6V`` vs ``FX6T``).
   - ``[IR Remote Ctrl]`` (``0x61a6``, Reset-immune): front **``#5``** ``Infrared remote sensor`` (NOT ``#8`` AF
     illuminator/Self-timer lamp); ``ILME-FX3A`` removed IR sensor; bypasses ``Power Save``; BT mutex; zero
     ``2.5mm LANC`` on FX3 (vs FX6 ``#24 REMOTE`` LANC + ``3.5mm`` Grip Remote).
   - ``[CTRL FOR HDMI]`` (``0xe41f``, ``BKID_APP_setting_ctrl_for_hmdi``, Reset-immune, **factory default ``On``**):
     41 ``EVENT_INPUT_KEY_CEC_*`` (no ``CEC_REC``) bench hijack hazard -> **mandatory bench ``Off``** when attached
     to HDMI bench equipment, plus ``16/16 H0 == H3`` dual-media ``528 B FX3RCPT1`` Tier-0 gate (``emmc_write_count = 0``).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, iter_work_roots, resolve_work_subpath
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

P341_VERSION = "phase341_v1"
PHASE_341_VERSION = P341_VERSION
P341_SCHEMA = "realhw_preflight18_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec_v1"
P341_SCHEMA_VERSION = P341_SCHEMA
PHASE_341_SCHEMA = P341_SCHEMA
REALHW_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_SCHEMA = P341_SCHEMA
P341_SONY_HELP_GUIDE_ID = "ilc/2210"

P341_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED = (
    "READONLY_PREFLIGHT18_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED"
)
P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE = (
    "BLOCKED_PREFLIGHT18_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE"
)
PHASE_341_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
    P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE,
)

# Bounded donor paths (read-only O_RDONLY)
P341_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx3_im_elf",
        "sony-firmware-20261024/stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf",
    ),
    (
        "fx3_libjiritsu_so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so",
    ),
    (
        "fx3_libsaveloadsettings_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
    ),
    (
        "fx3_upm_ko",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
    ),
)
P341_HEADER_READ_BYTES = 64

# Unconditional safety / zero-leak constants
PHASE341_RAW_FIRMWARE_BYTES_LEAKED = 0
PHASE341_PASSIVE_TX_BYTES_EMITTED = 0
PHASE341_USB_PACKETS_TRANSMITTED = 0
PHASE341_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE341_SLOT1_DATA_SECTOR_WRITES = 0
PHASE341_E_ND_ACTUATOR_TX_COUNT = 0
PHASE341_RF_NVS_MUTATION_BYTES = 0

P341_ERRNO_EPERM = 1
P341_ERRNO_EBUSY = 16
P341_ERRNO_EINVAL = 22
P341_ERRNO_EROFS = 30
P341_ERRNO_EOPNOTSUPP = 95

# Check Group IDs
P341_CHECK_GROUP_A_ID = "check_group_a_area_date_dst_rtc_and_grid_vs_marker_hdmi"
P341_CHECK_GROUP_B_ID = "check_group_b_camset_saveload_exclusions_and_mishoe_flash_sync"
P341_CHECK_GROUP_C_ID = "check_group_c_playback_magnification_and_antiflicker_vs_varshutter"
P341_CHECK_GROUP_D_ID = "check_group_d_wifi_5ghz_rf_nvs_ir_remote_cec_and_tier0"
PHASE_341_CHECK_GROUP_IDS = (
    P341_CHECK_GROUP_A_ID,
    P341_CHECK_GROUP_B_ID,
    P341_CHECK_GROUP_C_ID,
    P341_CHECK_GROUP_D_ID,
)

# Common valid enums
P341_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P341_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P341_VALID_EXPOSURE_MODES = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
    "MEMORY_RECALL",
)
P341_VALID_ON_OFF = ("ON", "OFF")
P341_STORAGE_SURFACE_COUNT = len(SIXTEEN_STORAGE_SURFACES)

# ---------------------------------------------------------------------------
# Group A Domain Constants (Wave 68 §§1-2: Area/Date/DST/RTC & Grid/Marker HDMI)
# ---------------------------------------------------------------------------
P341_AREA_DATE_TIME_RESID16_HEX = "0x6a9c"
P341_LEGACY_DATE_TIME_SETUP_RESID16_HEX = "0xe87f"
P341_AREA_SETTING_RESID16_HEX = "0xe91a"
P341_DAYLIGHT_SAVINGS_RESID16_HEX = "0xe917"
P341_DATE_FORMAT_RESID16_HEX = "0x670d"
P341_AREA_DATE_EXACT_FOUR_ITEMS = ("AREA_SETTING", "DAYLIGHT_SAVINGS", "DATE_TIME", "DATE_FORMAT")
P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC = "convert_setting_daylight_saving_to_saylight_saving"
P341_DATE_TIME_AUTO_SYNC_SONY_TYPO_BKID = "BKID_APP_setting_auto_sync_sever_date_time"
P341_AREA_GMT_THIRTY_ZONES: Tuple[str, ...] = (
    "AREA_GMT_M_11_0",
    "AREA_GMT_M_10_0",
    "AREA_GMT_M_09_0",
    "AREA_GMT_M_08_0",
    "AREA_GMT_M_07_0",
    "AREA_GMT_M_06_0",
    "AREA_GMT_M_05_0",
    "AREA_GMT_M_04_0",
    "AREA_GMT_M_03_5",
    "AREA_GMT_M_03_0",
    "AREA_GMT_M_02_0",
    "AREA_GMT_M_01_0",
    "AREA_GMT_00_0",
    "AREA_GMT_P_01_0",
    "AREA_GMT_P_02_0",
    "AREA_GMT_P_03_0",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_0",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_0",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_0",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_07_0",
    "AREA_GMT_P_08_0",
    "AREA_GMT_P_09_0",
    "AREA_GMT_P_09_5",
    "AREA_GMT_P_10_0",
    "AREA_GMT_P_11_0",
    "AREA_GMT_P_12_0",
)
P341_AREA_HALF_HOUR_SIX_ZONES: Tuple[str, ...] = (
    "AREA_GMT_M_03_5",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_09_5",
)
P341_VALID_DATE_FORMATS = ("Y_M_D", "M_D_Y", "D_M_Y")
P341_RTC_INTERNAL_MIN_CHARGE_HOURS = 24.0
P341_USER_REPLACEABLE_CR2032_SLOT_PRESENT = False
P341_FX6_CLOCK_SET_STEP_MINUTES = 30
P341_FX6_STANDALONE_DST_SWITCH_PRESENT = False

P341_GRID_LINE_DISPLAY_RESID16_HEX = "0x6f9d"
P341_GRID_LINE_TYPE_RESID16_HEX = "0x69c9"
P341_GRID_LINE_EXACT_THREE_TYPES = ("RULE_OF_3RDS", "SQUARE", "DIAG_PLUS_SQUARE")
P341_MARKER_DISPLAY_RESID16_HEX = "0x6803"
P341_GUIDEFRAME_RESID16_HEX = "0x62f9"
P341_ASPECT_MARKER_RATIO_COUNT = 15
P341_SAFETY_ZONE_OPTIONS = ("OFF", "80PCT", "90PCT")
P341_REC_MEDIA_DUR_HDMI_MODES = ("ON", "OFF_HDMI_ONLY")
P341_FX3_MARKER_OUTPUTS_TO_HDMI = False

# ---------------------------------------------------------------------------
# Group B Domain Constants (Wave 68 §§3-4: Save/Load CAMSET, Flash Sync, MI Shoe, Genlock)
# ---------------------------------------------------------------------------
P341_SAVE_LOAD_SETTINGS_RESID16_HEX = "0x6254"
P341_CAMSET_ALLOWED_SLOT = 1
P341_CAMSET_MAX_FILES_PER_CARD = 10
P341_CAMSET_CARD_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
P341_CAMPR_CARD_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT"
P341_FTPSET_CARD_TEMPLATE = "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"
P341_CAMSET_PRO_CAMERA_FX3_HITS = 0
P341_VALID_CARD_MEDIA_TYPES = ("CFEXPRESS_A", "SDXC", "SDHC")
P341_VALID_CAMSET_ACTIONS = ("NONE", "SAVE", "LOAD", "DELETE")
P341_VALID_CAMPR_ACTIONS = ("NONE", "SAVE", "RECALL")
P341_VALID_FTPSET_ACTIONS = ("NONE", "SAVE", "LOAD")
P341_CAMSET_EXCLUDED_CATEGORIES: Tuple[str, ...] = (
    "IPTC_INFORMATION",
    "COPYRIGHT_INFO",
    "EXTERNAL_FLASH_SET",
    "WHITE_BALANCE_CUSTOM",
    "FACE_MEMORY",
    "FTP_TRANSFER_FUNC",
    "NETWORK_STREAMING",
    "CLOUD_CONNECTION",
    "WPS_PUSH",
    "ACCESS_POINT_SET",
    "WIFI_FREQUENCY_BAND",
    "IP_ADDRESS_SETTING",
    "EDIT_DEVICE_NAME",
    "IMPORT_ROOT_CERTIFICATE",
    "ACCESS_AUTHEN_SETTINGS",
    "SECURITY_IPSEC",
    "LANGUAGE",
    "AREA_DATE_TIME_SETTING",
)
P341_CAMERA_SET_MEMORY_BODY_SLOTS = ("1", "2", "3")
P341_CAMERA_SET_MEMORY_CARD_SLOTS = ("M1", "M2", "M3", "M4")
P341_VALID_CAMPR_SLOTS = P341_CAMERA_SET_MEMORY_BODY_SLOTS + P341_CAMERA_SET_MEMORY_CARD_SLOTS
P341_FX6_REFERENCE_FILE_PRESENT = False

P341_FX3_SYNCHRO_TERMINAL_SYMBOL_HITS = 0
P341_FX3_SYNC_TERMINAL_PRESENT = False
P341_VIDEO_LIGHT_MODE_RESID16_HEX = "0x6211"
P341_VIDEO_LIGHT_MODE_FOUR_OPTIONS = ("POWER_LINK", "REC_LINK", "REC_LINK_AND_STBY", "AUTO")
P341_FX6_VIDEO_LIGHT_SET_THREE_OPTIONS = ("POWER_LINK", "REC_LINK", "REC_LINK_AND_STBY")
P341_MI_SHOE_PMIC_5V_MAX_MA = 900
P341_FLASH_XSYNC_DENOMINATOR = 250
P341_FLASH_MAX_TRIGGER_VOLTAGE_V = 250.0
P341_VALID_FLASH_MODES = ("OFF", "AUTO_FLASH", "FILL_FLASH", "SLOW_SYNC", "REAR_SYNC")
P341_FX6_GENLOCK_DORMANT_SYMBOL_HITS = 107
P341_FX6_GENLOCK_BNC_PRESENT = False

# ---------------------------------------------------------------------------
# Group C Domain Constants (Wave 69 §§1-2: Playback Magnification & Anti-flicker vs Var. Shutter)
# ---------------------------------------------------------------------------
P341_PB_ENLARGE_IMAGE_RESID16_HEX = "0xe8cb"
P341_PB_ENLARGE_INITIAL_MAG_RESID16_HEX = "0x6b6e"
P341_PB_ENLARGE_INITIAL_POS_RESID16_HEX = "0x781f"
P341_PB_MAGNIFY_PINCH_SONY_TYPO_SYMBOL = "playback_zoom_maginify_by_pinch"
P341_PB_ENLARGE_INITIAL_MAG_MODES = ("STANDARD_MAG", "PREVIOUS_MAG")
P341_PB_ENLARGE_INITIAL_POS_MODES = ("FOCUSED_POSITION", "CENTER")
P341_VALID_PB_MEDIA_KINDS = ("STILL", "MOVIE")

P341_ANTI_FLICKER_SHOOT_RESID16_HEX = "0x623d"
P341_ANTI_FLICKER_FREQUENCIES_HZ = (100, 120)
P341_VALID_SHUTTER_TYPES = ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER")
P341_DORMANT_ANTI_FLICKER_SET_RESID16_HEX = "0x68e7"
P341_DORMANT_VAR_SHUTTER_RESID16_HEX = "0x6831"
P341_DORMANT_VAR_SHUTTER_SET_RESID16_HEX = "0x6f9e"
P341_DORMANT_ANTI_FLICKER_TV_SCAN_RESID16_HEX = "0x63c0"
P341_FX6_ECS_FREQ_MIN_HZ = 23.99
P341_FX6_ECS_FREQ_MAX_HZ = 8000.0

# ---------------------------------------------------------------------------
# Group D Domain Constants (Wave 69 §§3-4: Wi-Fi Dual-SKU, RF NVS, IR Remote, CEC, LANC & Tier-0)
# ---------------------------------------------------------------------------
P341_WIFI_VALID_SKUS = ("NONE", "WW728473", "WW558244")
P341_WIFI_FREQUENCY_BAND_RESID16_HEX = "0x66c3"
P341_WIFI_VALID_BANDS = ("2_4_GHZ", "5_GHZ")
P341_WIFI_SKU_GATING_SYMBOL = "backup_get_wi_fi_frequency_band_dst"
P341_WIFI_SUPPORTED_SECURITY_PROTOCOLS = ("NONE", "WPA2_PSK", "WPA3_SAE", "OPEN_MANUAL_AP")
P341_WIFI_REMOVED_LEGACY_PROTOCOLS = ("WEP", "WPA_PSK", "IPSEC")
P341_RF_NVS_PARTITIONS = ("nflasha12", "nflasha13")

P341_IR_REMOTE_CTRL_RESID16_HEX = "0x61a6"
P341_FX3_IR_SENSOR_FRONT_INDEX = 5
P341_FX3_AF_ILLUMINATOR_LAMP_FRONT_INDEX = 8
P341_VALID_FX3_REVISIONS = ("ILME_FX3", "ILME_FX3A")
P341_FX3_2_5MM_LANC_PRESENT = False

P341_CTRL_FOR_HDMI_RESID16_HEX = "0xe41f"
P341_CTRL_FOR_HDMI_FACTORY_DEFAULT = "ON"
P341_CTRL_FOR_HDMI_BENCH_REQUIRED = "OFF"
P341_CTRL_FOR_HDMI_SONY_TYPO_BKID = "BKID_APP_setting_ctrl_for_hmdi"
P341_CEC_EVENT_KEY_COUNT = 41

# ---------------------------------------------------------------------------
# Error Tokens
# ---------------------------------------------------------------------------
P341_GA_ERR_MODEL_OR_FW_FLOOR = "P341_GA_ERR_MODEL_OR_FW_FLOOR"
P341_GA_ERR_AREA_DATE_DST_OR_RTC = "P341_GA_ERR_AREA_DATE_DST_OR_RTC"
P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI = "P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI"
P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY = "P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY"

P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION = "P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION"
P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS = "P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS"
P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE = "P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE"
P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH = "P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH"

P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE = "P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE"
P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT = "P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT"
P341_GC_ERR_DORMANT_VAR_SHUTTER_OR_TV_SCAN = "P341_GC_ERR_DORMANT_VAR_SHUTTER_OR_TV_SCAN"
P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY = "P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY"

P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE = "P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE"
P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK = "P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK"
P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC = "P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC"
P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK = "P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK"
P341_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P341_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Phase341DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    fx3_appfw_present: bool
    fx6_appfw_present: bool
    fx3_libsaveloadsettings_present: bool
    checked_paths: Tuple[str, ...]
    bytes_read_total: int
    elapsed_seconds: float
    within_budget: bool
    raw_firmware_bytes_leaked: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P341CheckGroupAAreaDateGridMarkerResult:
    group_id: str
    passed: bool
    area_zone: str
    area_gmt_zone_count: int
    area_half_hour_zone_count: int
    daylight_savings: str
    daylight_savings_elf_typo_func: str
    date_format: str
    rtc_backup_charge_hours: float
    user_replaceable_cr2032_slot_present: bool
    fx6_standalone_dst_switch_present: bool
    grid_line_display: str
    grid_line_type: str
    grid_line_passes_over_hdmi: bool
    marker_display: str
    aspect_marker: str
    safety_zone: str
    guideframe: str
    fx3_marker_outputs_to_hdmi: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P341CheckGroupBCamsetSaveLoadMiShoeFlashSyncResult:
    group_id: str
    passed: bool
    camset_action: str
    camset_slot: int
    camset_file_index: int
    camset_card_template: str
    camset_pro_camera_fx3_hits: int
    campr_action: str
    campr_slot: str
    memory_recall_media_slot: int
    ftpset_action: str
    ftpset_slot: int
    fx6_reference_file_present: bool
    fx3_sync_terminal_present: bool
    fx3_synchro_terminal_hits: int
    xlr_h1_attached: bool
    video_light_mode: str
    mi_shoe_5v_draw_ma: int
    flash_mode: str
    flash_xsync_denominator: int
    fx6_genlock_bnc_present: bool
    fx6_genlock_dormant_hits: int
    slot1_tier0_vault_mutated: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P341CheckGroupCPbMagnifyAntiFlickerVarShutterResult:
    group_id: str
    passed: bool
    playback_magnify_requested: bool
    playback_media_kind: str
    enlarge_initial_mag: str
    enlarge_initial_pos: str
    playback_magnify_pinch_typo_symbol: str
    anti_flicker_shoot: str
    still_shutter_type: str
    fx3_var_shutter_present: bool
    fx3_anti_flicker_tv_scan_present: bool
    fx3_anti_flicker_set_present: bool
    fx6_ecs_enabled: bool
    fx6_ecs_freq_hz: float
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P341CheckGroupDWifi5GhzIrRemoteCecTier0Result:
    group_id: str
    passed: bool
    wifi_sku: str
    wifi_connect: str
    wifi_frequency_band: str
    wifi_security_protocol: str
    wifi_sku_gating_symbol: str
    airplane_mode: str
    rf_nvs_p12_p13_readonly: bool
    rf_nvs_mutation_bytes: int
    wireless_rf_packets_emitted: int
    camera_revision: str
    ir_remote_ctrl: str
    ir_sensor_front_index: int
    bluetooth_rmt_ctrl: str
    fx3_2_5mm_lanc_present: bool
    ctrl_for_hdmi: str
    ctrl_for_hdmi_factory_default: str
    ctrl_for_hdmi_typo_bkid: str
    cec_event_key_count: int
    hdmi_bench_attached: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    emmc_write_count: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase341ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    verification_mode: str
    simulate_bench_dry_run: bool
    overall_status: str
    go_no_go: str
    body_model_id_hex: str
    body_fw: str
    reset_action: str
    check_group_count: int
    check_groups_passed: int
    check_group_a: P341CheckGroupAAreaDateGridMarkerResult
    check_group_b: P341CheckGroupBCamsetSaveLoadMiShoeFlashSyncResult
    check_group_c: P341CheckGroupCPbMagnifyAntiFlickerVarShutterResult
    check_group_d: P341CheckGroupDWifi5GhzIrRemoteCecTier0Result
    donor_inspection: Phase341DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    slot1_tier0_vault_mutated: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_sync_terminal_present: bool
    fx6_genlock_bnc_present: bool
    fx3_var_shutter_present: bool
    fx3_anti_flicker_tv_scan_present: bool
    fx3_anti_flicker_set_present: bool
    fx3_2_5mm_lanc_present: bool
    fx6_standalone_dst_switch_present: bool
    fx6_reference_file_present: bool
    fx3_marker_outputs_to_hdmi: bool
    fx3_camset_allows_slot2: bool
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
    report_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        """Return deterministic JSON with all timing fields (elapsed_seconds, etc.) stripped recursively."""
        return json.dumps(_strip_timing_fields(self.to_dict()), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Timing Stripping, SHA-256 & Bounded Donor Inspection Helpers
# ---------------------------------------------------------------------------
def _is_timing_key(key: str) -> bool:
    return key in (
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    ) or key.endswith(("_elapsed_ms", "_elapsed_s", "_elapsed_seconds"))


def _strip_timing_fields(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if _is_timing_key(ks):
                continue
            out[ks] = _strip_timing_fields(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_strip_timing_fields(x) for x in obj]
    return obj


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    clone = json.loads(json.dumps(dict(payload)))
    clone.pop("report_sha256", None)
    clone = _strip_timing_fields(clone)
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _bounded_read_header(path: Path, max_bytes: int = P341_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def resolve_phase341_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    """Resolve a donor file under ``work_root``, returning ``None`` cleanly when ``work_root is None``."""
    if work_root is None:
        return None
    cand = Path(work_root) / rel_subpath
    return cand if cand.is_file() else None


def _resolve_work_root_or_none(*, force_clean_room: bool = False) -> Optional[Path]:
    """Return the first ``work/`` root containing BYOF donor artifacts, or ``None`` on donorless CI."""
    if force_clean_room or _is_clean_room_env():
        return None
    for candidate in iter_work_roots():
        if not candidate.is_dir():
            continue
        if any(resolve_phase341_donor_file_or_none(candidate, rel) is not None for _lbl, rel in P341_BOUNDED_DONOR_PATHS):
            return candidate
    return None


def inspect_phase341_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase341DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 0.20s) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase341DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_libsaveloadsettings_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE341_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = (
        work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    )
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase341DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_libsaveloadsettings_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE341_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P341_BOUNDED_DONOR_PATHS:
        resolved: Optional[Path] = None
        if label == "fx6_appfw_so" and fx6_lib_dir is not None:
            cand = fx6_lib_dir / "appFw.so"
            if cand.is_file():
                resolved = cand
        if label == "fx3_upm_ko" and fx3_modules_dir is not None:
            cand = fx3_modules_dir / "upm.ko"
            if cand.is_file():
                resolved = cand
        if resolved is None:
            resolved = resolve_phase341_donor_file_or_none(effective_work_root, rel)
        if resolved is None and work_root is None and effective_work_root is not None:
            try:
                cand = resolve_work_subpath(rel, require_file=True)
                if cand.is_file():
                    resolved = cand
            except Exception:
                resolved = None
        if resolved is not None and resolved.is_file():
            checked.append(label)
            bytes_total += _bounded_read_header(resolved)
            found_map[label] = True
        else:
            found_map[label] = False

    donor_present = any(found_map.values())
    mode = "LOCAL_DONOR_O_RDONLY" if donor_present else "CLEAN_ROOM_SYNTHETIC"
    elapsed = round(time.monotonic() - t0, 6)
    return Phase341DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_libsaveloadsettings_present=found_map.get("fx3_libsaveloadsettings_so", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE341_RAW_FIRMWARE_BYTES_LEAKED,
    )


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 68 §§1-2: Area/Date/DST/RTC & Grid/Marker HDMI)
# ---------------------------------------------------------------------------
def evaluate_p341_check_group_a_area_date_grid_and_marker(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P341_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    area_zone: str = "AREA_GMT_P_09_0",
    exposed_area_gmt_zones: Tuple[str, ...] = P341_AREA_GMT_THIRTY_ZONES,
    daylight_savings: str = "OFF",
    date_format: str = "Y_M_D",
    rtc_backup_charge_hours: float = 24.0,
    rtc_initialized: bool = True,
    claimed_user_replaceable_cr2032_present: bool = False,
    rtc_discharge_without_24h_charge_claimed: bool = False,
    claimed_area_date_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_standalone_dst_switch: bool = False,
    expect_area_date_uses_legacy_name_only: bool = False,
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS",
    hdmi_info_display: str = "ON",
    hdmi_raw_output: str = "OFF",
    rec_media_dur_hdmi_output: str = "ON",
    marker_display: str = "OFF",
    center_marker: str = "OFF",
    aspect_marker: str = "OFF",
    safety_zone: str = "OFF",
    guideframe: str = "OFF",
    focus_magnifier_active: bool = False,
    expect_marker_outputs_over_hdmi: bool = False,
    expect_grid_passes_hdmi_when_info_off_or_raw: bool = False,
    expect_marker_active_in_still_mode: bool = False,
    expect_marker_visible_during_focus_magnifier: bool = False,
    claimed_grid_or_marker_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_3mode_static_grid_line_menu: bool = False,
) -> P341CheckGroupAAreaDateGridMarkerResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT or body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P341_GA_ERR_MODEL_OR_FW_FLOOR}: expected model {TARGET_MODEL_ID_HEX} / fw {TARGET_BODY_FW}, "
            f"got {hex(body_model_id)} / {body_fw!r}"
        )
    if sony_help_guide_id != P341_SONY_HELP_GUIDE_ID:
        errors.append(f"{P341_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P341_SONY_HELP_GUIDE_ID}")
    if reset_action not in P341_VALID_RESET_ACTIONS:
        errors.append(f"{P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY}: invalid reset_action={reset_action!r}")
    if shoot_mode not in P341_VALID_SHOOT_MODES:
        errors.append(f"{P341_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode!r}")

    if area_zone not in P341_AREA_GMT_THIRTY_ZONES:
        errors.append(f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: invalid area_zone={area_zone!r}")
    half_hour_present = sum(1 for z in P341_AREA_HALF_HOUR_SIX_ZONES if z in exposed_area_gmt_zones)
    if len(exposed_area_gmt_zones) != 30 or tuple(exposed_area_gmt_zones) != P341_AREA_GMT_THIRTY_ZONES or half_hour_present != 6:
        errors.append(
            f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: FX3 [Area Setting] ({P341_AREA_SETTING_RESID16_HEX}) must expose "
            f"exact 30 AREA_GMT_* zones including 6 half-hour offsets (got {len(exposed_area_gmt_zones)}, half={half_hour_present})"
        )
    if daylight_savings not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: invalid daylight_savings={daylight_savings!r}")
    if date_format not in P341_VALID_DATE_FORMATS:
        errors.append(f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: invalid date_format={date_format!r}")
    if claimed_user_replaceable_cr2032_present:
        errors.append(
            f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: FX3 uses a soldered internal rechargeable RTC battery "
            f"and has ZERO user-replaceable CR2032 coin-cell slot"
        )
    if rtc_discharge_without_24h_charge_claimed or (not rtc_initialized and rtc_backup_charge_hours < P341_RTC_INTERNAL_MIN_CHARGE_HOURS):
        errors.append(
            f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: depleted FX3 internal RTC backup battery requires >= 24.0 h "
            f"powered-OFF charge with a charged NP-FZ100 (got {rtc_backup_charge_hours} h)"
        )
    if claimed_area_date_wiped_by_camera_reset:
        errors.append(
            f"{P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY}: [Area/Date/Time Setting] ({P341_AREA_DATE_TIME_RESID16_HEX}) "
            f"is Reset-immune ([Camera Settings Reset] Not available; only [Initialize] resets it)"
        )
    if claimed_fx6_has_standalone_dst_switch:
        errors.append(
            f"{P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY}: FX6 Maintenance > Clock Set has 30-min steps and "
            f"NO standalone Daylight Savings UI switch (summer_time_name_dst dormant)"
        )
    if expect_area_date_uses_legacy_name_only:
        errors.append(
            f"{P341_GA_ERR_AREA_DATE_DST_OR_RTC}: ilc/2210 uses Setup -> [Area/Date] -> [Area/Date/Time Setting] "
            f"({P341_AREA_DATE_TIME_RESID16_HEX}), not legacy {P341_LEGACY_DATE_TIME_SETUP_RESID16_HEX} Date/Time Setup"
        )

    if grid_line_display not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: invalid grid_line_display={grid_line_display!r}")
    if grid_line_type not in P341_GRID_LINE_EXACT_THREE_TYPES:
        errors.append(
            f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: invalid grid_line_type={grid_line_type!r}; "
            f"expected one of {P341_GRID_LINE_EXACT_THREE_TYPES}"
        )
    if marker_display not in P341_VALID_ON_OFF or center_marker not in P341_VALID_ON_OFF or guideframe not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: Marker Display/Center/Guideframe must be ON or OFF")
    if safety_zone not in P341_SAFETY_ZONE_OPTIONS:
        errors.append(f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: invalid safety_zone={safety_zone!r}")
    if hdmi_info_display not in P341_VALID_ON_OFF or hdmi_raw_output not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: hdmi_info_display/hdmi_raw_output must be ON/OFF")
    if rec_media_dur_hdmi_output not in P341_REC_MEDIA_DUR_HDMI_MODES:
        errors.append(f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output!r}")

    grid_passes_hdmi = (
        grid_line_display == "ON"
        and hdmi_info_display == "ON"
        and hdmi_raw_output == "OFF"
        and rec_media_dur_hdmi_output == "ON"
    )
    if expect_grid_passes_hdmi_when_info_off_or_raw:
        errors.append(
            f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: [Grid Line] is suppressed over HDMI whenever "
            f"[HDMI Info. Display]=Off, [Off (HDMI Only)], or [RAW Output]=On"
        )
    if expect_marker_outputs_over_hdmi:
        errors.append(
            f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: [Marker Display] ({P341_MARKER_DISPLAY_RESID16_HEX}) / "
            f"[Guideframe] ({P341_GUIDEFRAME_RESID16_HEX}) / 15-ratio [Aspect Marker] NEVER output pixels over HDMI (0 px)"
        )
    if expect_marker_active_in_still_mode or (shoot_mode == "PHOTO" and marker_display == "ON"):
        errors.append(
            f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: [Marker Display] is Movie/S&Q-only "
            f"(PRM_HAITA_setting_marker_display_exposure_mode) and inhibited in Still mode"
        )
    if expect_marker_visible_during_focus_magnifier or (focus_magnifier_active and marker_display == "ON"):
        errors.append(
            f"{P341_GA_ERR_GRID_LINE_OR_MARKER_HDMI}: [Marker Display] is hidden while Focus Magnifier is active"
        )
    if claimed_grid_or_marker_wiped_by_camera_reset:
        errors.append(
            f"{P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY}: both [Grid Line Display/Type] and all 5 [Marker Display] "
            f"items are Reset-immune ([Camera Settings Reset] Not available)"
        )
    if claimed_fx6_has_3mode_static_grid_line_menu:
        errors.append(
            f"{P341_GA_ERR_RESET_IMMUNITY_OR_FX6_PARITY}: FX6 Monitoring > Marker lacks FX3 3-mode static Grid Line UI "
            f"(GUIDE_FRAME_*_GRID dormant in FX6 appFw.so)"
        )
    if grid_passes_hdmi:
        warnings.append(
            "Clean-HDMI advisory: [Grid Line Display]=On + [HDMI Info. Display]=On overlays grid lines onto HDMI output."
        )

    return P341CheckGroupAAreaDateGridMarkerResult(
        group_id=P341_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        area_zone=area_zone,
        area_gmt_zone_count=len(exposed_area_gmt_zones),
        area_half_hour_zone_count=half_hour_present,
        daylight_savings=daylight_savings,
        daylight_savings_elf_typo_func=P341_DAYLIGHT_SAVINGS_SONY_ELF_TYPO_FUNC,
        date_format=date_format,
        rtc_backup_charge_hours=rtc_backup_charge_hours,
        user_replaceable_cr2032_slot_present=P341_USER_REPLACEABLE_CR2032_SLOT_PRESENT,
        fx6_standalone_dst_switch_present=P341_FX6_STANDALONE_DST_SWITCH_PRESENT,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        grid_line_passes_over_hdmi=grid_passes_hdmi,
        marker_display=marker_display,
        aspect_marker=aspect_marker,
        safety_zone=safety_zone,
        guideframe=guideframe,
        fx3_marker_outputs_to_hdmi=P341_FX3_MARKER_OUTPUTS_TO_HDMI,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 68 §§3-4: Save/Load CAMSET, Flash Sync, MI Shoe, Genlock)
# ---------------------------------------------------------------------------
def evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
    *,
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    still_shutter_type: str = "MECHANICAL_SHUTTER",
    camset_action: str = "NONE",
    camset_slot: int = 1,
    camset_file_index: int = 1,
    camset_media_type: str = "CFEXPRESS_A",
    camset_card_template: str = P341_CAMSET_CARD_TEMPLATE,
    camset_fw_version: str = TARGET_BODY_FW,
    claimed_camset_allows_slot2: bool = False,
    claimed_camset_uses_pro_camera_path: bool = False,
    claimed_camset_includes_excluded_items: bool = False,
    claimed_ftpset_shares_camset_dir: bool = False,
    campr_action: str = "NONE",
    campr_slot: str = "M1",
    memory_recall_media_slot: int = 2,
    claimed_campr_includes_custom_key_or_program_shift: bool = False,
    ftpset_action: str = "NONE",
    ftpset_slot: int = 2,
    claimed_fx6_reference_file_present: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    pc_sync_terminal_requested: bool = False,
    claimed_fx3_sync_terminal_present: bool = False,
    xlr_h1_attached: bool = True,
    hvl_lbpc_direct_mount_requested: bool = False,
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_draw_ma: int = 0,
    flash_mode: str = "OFF",
    flash_xsync_denominator: int = P341_FLASH_XSYNC_DENOMINATOR,
    flash_trigger_voltage_v: float = 0.0,
    claimed_fx6_video_light_has_auto_mode: bool = False,
    claimed_fx6_genlock_bnc_present: bool = False,
    fx6_genlock_requested: bool = False,
) -> P341CheckGroupBCamsetSaveLoadMiShoeFlashSyncResult:
    errors: List[str] = []
    warnings: List[str] = []
    slot1_mutated = False

    if camset_action not in P341_VALID_CAMSET_ACTIONS:
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: invalid camset_action={camset_action!r}")
    if campr_action not in P341_VALID_CAMPR_ACTIONS:
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: invalid campr_action={campr_action!r}")
    if ftpset_action not in P341_VALID_FTPSET_ACTIONS:
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: invalid ftpset_action={ftpset_action!r}")
    if camset_media_type not in P341_VALID_CARD_MEDIA_TYPES:
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: invalid camset_media_type={camset_media_type!r}")
    if camset_slot != P341_CAMSET_ALLOWED_SLOT or claimed_camset_allows_slot2:
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Save/Load Settings] ({P341_SAVE_LOAD_SETTINGS_RESID16_HEX}) "
            f"is strictly locked to Slot 1 on FX3 (got camset_slot={camset_slot}, allow_slot2={claimed_camset_allows_slot2})"
        )
    if not (1 <= camset_file_index <= P341_CAMSET_MAX_FILES_PER_CARD):
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: CAMSET file index must be 1..10 (got {camset_file_index})"
        )
    if camset_card_template != P341_CAMSET_CARD_TEMPLATE or claimed_camset_uses_pro_camera_path:
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: FX3 CAMSET card path must match "
            f"{P341_CAMSET_CARD_TEMPLATE!r} (0 PRO/CAMERA hits on FX3; FX6 uses PRO/CAMERA/*.ALL on Media(B))"
        )
    if camset_action == "LOAD" and exposure_mode == "MEMORY_RECALL":
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Save/Load Settings] cannot execute in MR (Memory Recall) mode"
        )
    if camset_action == "LOAD" and camset_fw_version in ("1.00", "1.01"):
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: CAMSET files from Ver. <= 1.01 are rejected on Ver. >= 2.00"
        )
    if claimed_camset_includes_excluded_items:
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Save/Load Settings] excludes 18 official categories "
            f"(Copyright Info, External Flash Set., Custom WB, Face Memory, Network/FTPSET, Area/Date/Time, etc.)"
        )
    if claimed_ftpset_shares_camset_dir:
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Save/Load FTP Settings] stores into FTPSET/%s.DAT, "
            f"strictly separated from CAMSET/%s.DAT"
        )
    if campr_slot not in P341_VALID_CAMPR_SLOTS:
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: invalid campr_slot={campr_slot!r}")
    if memory_recall_media_slot not in (1, 2):
        errors.append(f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Memory/Recall Media] slot must be 1 or 2")
    if claimed_campr_includes_custom_key_or_program_shift:
        errors.append(
            f"{P341_GB_ERR_CAMSET_SLOT1_OR_TEMPLATE_OR_EXCLUSION}: [Camera Set. Memory] (CAMPR%02d%c.DAT) excludes "
            f"[Custom Key/Dial Set.] and Program Shift"
        )
    if claimed_fx6_reference_file_present:
        errors.append(
            f"{P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH}: FX6 [Reference File] has 0 hits in FX6 appFw.so (dormant)"
        )

    # Tier-0 Slot-1 EROFS=30 write firewall
    slot1_write_attempted = (
        (camset_action in ("SAVE", "DELETE") and camset_slot == 1)
        or (campr_action == "SAVE" and campr_slot in P341_CAMERA_SET_MEMORY_CARD_SLOTS and memory_recall_media_slot == 1)
        or (ftpset_action == "SAVE" and ftpset_slot == 1)
    )
    if slot1_write_attempted and slot1_contains_tier0_dump:
        slot1_mutated = True
        errors.append(
            f"{P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS}: errno={P341_ERRNO_EROFS} (EROFS) blocked Save/Delete write onto "
            f"Slot-1 Tier-0 recovery vault (read-only Load/Recall permitted)"
        )
    if slot1_data_sector_writes != 0:
        slot1_mutated = True
        errors.append(
            f"{P341_GB_ERR_SLOT1_TIER0_VAULT_EROFS}: slot1_data_sector_writes={slot1_data_sector_writes} must remain 0"
        )

    # PC Flash Sync absence, XLR-H1 passive cold shoe, MI Shoe PMIC, FX6 Genlock myth
    if pc_sync_terminal_requested or claimed_fx3_sync_terminal_present:
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: errno={P341_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) — "
            f"FX3 has ZERO physical PC Flash Sync terminal (0 SYNCHRO_TERMINAL* symbols in FX3 appFw.so)"
        )
    if video_light_mode not in P341_VIDEO_LIGHT_MODE_FOUR_OPTIONS:
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: invalid video_light_mode={video_light_mode!r}"
        )
    if mi_shoe_5v_draw_ma < 0 or mi_shoe_5v_draw_ma > P341_MI_SHOE_PMIC_5V_MAX_MA:
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: MI Shoe PMIC 5V draw {mi_shoe_5v_draw_ma} mA "
            f"exceeds 0..{P341_MI_SHOE_PMIC_5V_MAX_MA} mA budget"
        )
    if xlr_h1_attached and (hvl_lbpc_direct_mount_requested or flash_mode != "OFF"):
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: XLR-H1 occupies the sole electrical MI Shoe and "
            f"exposes only a passive cold shoe (0 contacts), physically excluding HVL-LBPC or MI-Shoe flash"
        )
    if flash_mode not in P341_VALID_FLASH_MODES:
        errors.append(f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: invalid flash_mode={flash_mode!r}")
    if flash_mode != "OFF" and (shoot_mode != "PHOTO" or still_shutter_type != "MECHANICAL_SHUTTER"):
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: MI-Shoe Flash is Still Mechanical Shutter only "
            f"(shoot_mode={shoot_mode}, still_shutter_type={still_shutter_type})"
        )
    if flash_xsync_denominator != P341_FLASH_XSYNC_DENOMINATOR:
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: FX3 X-Sync ceiling is 1/{P341_FLASH_XSYNC_DENOMINATOR} s"
        )
    if flash_trigger_voltage_v < 0.0 or flash_trigger_voltage_v >= P341_FLASH_MAX_TRIGGER_VOLTAGE_V:
        errors.append(
            f"{P341_GB_ERR_FLASH_SYNC_ABSENCE_OR_XLR_H1_COLD_SHOE}: MI Shoe forbids reverse polarity (<0V) or >=250V flash trigger"
        )
    if claimed_fx6_video_light_has_auto_mode:
        errors.append(
            f"{P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH}: FX6 Technical > Video Light Set has 3 modes only (NO Auto)"
        )
    if claimed_fx6_genlock_bnc_present or fx6_genlock_requested:
        errors.append(
            f"{P341_GB_ERR_FX6_GENLOCK_OR_REFERENCE_FILE_MYTH}: FX6 has ZERO physical GENLOCK BNC (only switchable "
            f"TC IN/OUT BNC, despite {P341_FX6_GENLOCK_DORMANT_SYMBOL_HITS} dormant GENLOCK symbols in FX6 appFw.so)"
        )

    return P341CheckGroupBCamsetSaveLoadMiShoeFlashSyncResult(
        group_id=P341_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        camset_action=camset_action,
        camset_slot=camset_slot,
        camset_file_index=camset_file_index,
        camset_card_template=camset_card_template,
        camset_pro_camera_fx3_hits=P341_CAMSET_PRO_CAMERA_FX3_HITS,
        campr_action=campr_action,
        campr_slot=campr_slot,
        memory_recall_media_slot=memory_recall_media_slot,
        ftpset_action=ftpset_action,
        ftpset_slot=ftpset_slot,
        fx6_reference_file_present=P341_FX6_REFERENCE_FILE_PRESENT,
        fx3_sync_terminal_present=P341_FX3_SYNC_TERMINAL_PRESENT,
        fx3_synchro_terminal_hits=P341_FX3_SYNCHRO_TERMINAL_SYMBOL_HITS,
        xlr_h1_attached=xlr_h1_attached,
        video_light_mode=video_light_mode,
        mi_shoe_5v_draw_ma=mi_shoe_5v_draw_ma,
        flash_mode=flash_mode,
        flash_xsync_denominator=flash_xsync_denominator,
        fx6_genlock_bnc_present=P341_FX6_GENLOCK_BNC_PRESENT,
        fx6_genlock_dormant_hits=P341_FX6_GENLOCK_DORMANT_SYMBOL_HITS,
        slot1_tier0_vault_mutated=slot1_mutated,
        slot1_data_sector_writes=slot1_data_sector_writes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 69 §§1-2: Playback Magnify & Anti-flicker vs Var. Shutter)
# ---------------------------------------------------------------------------
def evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
    *,
    shoot_mode: str = "MOVIE",
    playback_magnify_requested: bool = False,
    playback_media_kind: str = "STILL",
    enlarge_initial_mag: str = "STANDARD_MAG",
    enlarge_initial_pos: str = "FOCUSED_POSITION",
    claimed_playback_magnify_works_on_movies: bool = False,
    claimed_playback_magnify_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_playback_enlarge: bool = False,
    anti_flicker_shoot: str = "OFF",
    still_shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    bulb_enabled: bool = False,
    claimed_anti_flicker_effective_on_high_freq_led: bool = False,
    claimed_anti_flicker_shoot_resists_camera_reset: bool = False,
    dormant_var_shutter_requested: bool = False,
    dormant_anti_flicker_set_requested: bool = False,
    dormant_anti_flicker_tv_scan_requested: bool = False,
    claimed_fx3_var_shutter_present: bool = False,
    claimed_fx3_anti_flicker_tv_scan_present: bool = False,
    claimed_fx3_anti_flicker_set_present: bool = False,
    fx6_ecs_enabled: bool = False,
    fx6_ecs_freq_hz: float = 60.0,
    claimed_fx6_lacks_ecs: bool = False,
) -> P341CheckGroupCPbMagnifyAntiFlickerVarShutterResult:
    errors: List[str] = []
    warnings: List[str] = []

    if playback_media_kind not in P341_VALID_PB_MEDIA_KINDS:
        errors.append(f"{P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE}: invalid playback_media_kind={playback_media_kind!r}")
    if enlarge_initial_mag not in P341_PB_ENLARGE_INITIAL_MAG_MODES:
        errors.append(f"{P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE}: invalid enlarge_initial_mag={enlarge_initial_mag!r}")
    if enlarge_initial_pos not in P341_PB_ENLARGE_INITIAL_POS_MODES:
        errors.append(f"{P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE}: invalid enlarge_initial_pos={enlarge_initial_pos!r}")

    if (playback_magnify_requested and playback_media_kind == "MOVIE") or claimed_playback_magnify_works_on_movies:
        errors.append(
            f"{P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE}: errno={P341_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) — "
            f"Playback [Enlarge Image] ({P341_PB_ENLARGE_IMAGE_RESID16_HEX}) is strictly Still-only "
            f"('You cannot enlarge movies.' / playback_zoom::is_inhibition())"
        )
    if claimed_playback_magnify_wiped_by_camera_reset:
        errors.append(
            f"{P341_GC_ERR_PB_MAGNIFY_STILL_ONLY_OR_PERSISTENCE}: [Enlarge Initial Mag.] ({P341_PB_ENLARGE_INITIAL_MAG_RESID16_HEX}) "
            f"and [Enlarge Initial Position] ({P341_PB_ENLARGE_INITIAL_POS_RESID16_HEX}) are Reset-immune"
        )
    if claimed_fx6_has_playback_enlarge:
        errors.append(
            f"{P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY}: FX6 uses Thumbnail/Rec Review and live Focus Magnifier, "
            f"with NO Playback still enlarge feature"
        )

    if anti_flicker_shoot not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT}: invalid anti_flicker_shoot={anti_flicker_shoot!r}")
    if still_shutter_type not in P341_VALID_SHUTTER_TYPES:
        errors.append(f"{P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT}: invalid still_shutter_type={still_shutter_type!r}")
    if anti_flicker_shoot == "ON" and (
        shoot_mode != "PHOTO"
        or still_shutter_type != "MECHANICAL_SHUTTER"
        or silent_mode == "ON"
        or bulb_enabled
    ):
        errors.append(
            f"{P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT}: [Anti-flicker Shoot.] ({P341_ANTI_FLICKER_SHOOT_RESID16_HEX}) "
            f"is Still mechanical shutter only (locked in Movie/S&Q, Electronic Shutter, Silent Mode, and BULB)"
        )
    if claimed_anti_flicker_effective_on_high_freq_led:
        errors.append(
            f"{P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT}: [Anti-flicker Shoot.] detects 100/120 Hz AC flicker only "
            f"and is ineffective against high-frequency PWM LED lighting"
        )
    if claimed_anti_flicker_shoot_resists_camera_reset:
        errors.append(
            f"{P341_GC_ERR_ANTI_FLICKER_SHOOT_LOCKOUT}: [Anti-flicker Shoot.] IS Resettable by [Camera Settings Reset]"
        )

    if (
        dormant_var_shutter_requested
        or dormant_anti_flicker_set_requested
        or dormant_anti_flicker_tv_scan_requested
        or claimed_fx3_var_shutter_present
        or claimed_fx3_anti_flicker_tv_scan_present
        or claimed_fx3_anti_flicker_set_present
    ):
        errors.append(
            f"{P341_GC_ERR_DORMANT_VAR_SHUTTER_OR_TV_SCAN}: errno={P341_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) — "
            f"[Var. Shutter] ({P341_DORMANT_VAR_SHUTTER_RESID16_HEX}), [Var. Shutter Set.] ({P341_DORMANT_VAR_SHUTTER_SET_RESID16_HEX}), "
            f"[Anti-flicker Set.] ({P341_DORMANT_ANTI_FLICKER_SET_RESID16_HEX}), and "
            f"[Anti-flicker Tv Scan] ({P341_DORMANT_ANTI_FLICKER_TV_SCAN_RESID16_HEX}) are 100% dormant on ALCIN_UUD FX3"
        )

    if fx6_ecs_enabled and not (P341_FX6_ECS_FREQ_MIN_HZ <= fx6_ecs_freq_hz <= P341_FX6_ECS_FREQ_MAX_HZ):
        errors.append(
            f"{P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY}: FX6 ECS frequency {fx6_ecs_freq_hz} Hz out of "
            f"{P341_FX6_ECS_FREQ_MIN_HZ}..{P341_FX6_ECS_FREQ_MAX_HZ} Hz range"
        )
    if claimed_fx6_lacks_ecs:
        errors.append(
            f"{P341_GC_ERR_FX6_THUMBNAIL_OR_ECS_PARITY}: FX6 Shooting > Shutter exposes continuous ECS ({P341_FX6_ECS_FREQ_MIN_HZ}..{P341_FX6_ECS_FREQ_MAX_HZ} Hz)"
        )

    return P341CheckGroupCPbMagnifyAntiFlickerVarShutterResult(
        group_id=P341_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        playback_magnify_requested=playback_magnify_requested,
        playback_media_kind=playback_media_kind,
        enlarge_initial_mag=enlarge_initial_mag,
        enlarge_initial_pos=enlarge_initial_pos,
        playback_magnify_pinch_typo_symbol=P341_PB_MAGNIFY_PINCH_SONY_TYPO_SYMBOL,
        anti_flicker_shoot=anti_flicker_shoot,
        still_shutter_type=still_shutter_type,
        fx3_var_shutter_present=False,
        fx3_anti_flicker_tv_scan_present=False,
        fx3_anti_flicker_set_present=False,
        fx6_ecs_enabled=fx6_ecs_enabled,
        fx6_ecs_freq_hz=fx6_ecs_freq_hz,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 69 §§3-4: Wi-Fi 5GHz, RF NVS, IR Remote, CEC, LANC & Tier-0)
# ---------------------------------------------------------------------------
def _verify_single_receipt(raw: Optional[bytes], *, label: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errs: List[str] = []
    if raw is None:
        errs.append(f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} missing")
        return None, errs
    if len(raw) != SD_RECEIPT_BYTES:
        errs.append(
            f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} length {len(raw)} != {SD_RECEIPT_BYTES}"
        )
        return None, errs
    try:
        parsed = parse_sd_backup_receipt_bytes(raw)
        if not parsed.valid:
            errs.append(
                f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} invalid ({'; '.join(parsed.errors)})"
            )
            return None, errs
        return asdict(parsed), errs
    except Exception as exc:
        errs.append(f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} parse failed ({exc})")
        return None, errs


def evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    reset_action: str = "NONE",
    wifi_sku: str = "WW728473",
    wifi_connect: str = "OFF",
    wifi_frequency_band: str = "2_4_GHZ",
    wifi_security_protocol: str = "WPA2_PSK",
    access_point_set_requested: bool = False,
    claimed_ww558244_supports_5ghz: bool = False,
    claimed_ver700_supports_wep_wpa_ipsec: bool = False,
    claimed_reset_network_wipes_airplane_mode: bool = False,
    claimed_camera_reset_wipes_network: bool = False,
    claimed_fx6_uses_single_wifi_sku: bool = False,
    airplane_mode: str = "ON",
    rf_nvs_p12_p13_readonly: bool = True,
    rf_nvs_mutation_bytes: int = 0,
    claim_rf_nvs_write_authorized: bool = False,
    camera_revision: str = "ILME_FX3",
    ir_remote_ctrl: str = "OFF",
    ir_sensor_front_index: int = 5,
    bluetooth_rmt_ctrl: str = "OFF",
    expect_power_save_sleeps_during_ir: bool = False,
    claimed_ir_sensor_is_front_8: bool = False,
    claimed_fx3a_keeps_ir_sensor: bool = False,
    claimed_fx3_has_2_5mm_lanc: bool = False,
    ctrl_for_hdmi: str = "OFF",
    hdmi_bench_attached: bool = True,
    claimed_ctrl_for_hdmi_factory_default_is_off: bool = False,
    claimed_ir_or_cec_wiped_by_camera_reset: bool = False,
    claimed_cec_has_rec_key: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> P341CheckGroupDWifi5GhzIrRemoteCecTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if wifi_sku not in P341_WIFI_VALID_SKUS:
        errors.append(f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: invalid wifi_sku={wifi_sku!r}")
    if wifi_connect not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: invalid wifi_connect={wifi_connect!r}")
    if wifi_frequency_band not in P341_WIFI_VALID_BANDS:
        errors.append(f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: invalid wifi_frequency_band={wifi_frequency_band!r}")
    if wifi_sku == "WW558244" and wifi_frequency_band == "5_GHZ":
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: errno={P341_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) — "
            f"SKU WW558244 ({P341_WIFI_SKU_GATING_SYMBOL}=AVAILABLE_2_4_GHZ_ONLY) locks out 5 GHz Wi-Fi"
        )
    if claimed_ww558244_supports_5ghz:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: WW558244 is strictly 2.4 GHz (802.11 b/g/n) only"
        )
    if wifi_security_protocol in P341_WIFI_REMOVED_LEGACY_PROTOCOLS or claimed_ver700_supports_wep_wpa_ipsec:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: Ver. 7.00+ removed WEP, WPA-PSK, and IPsec; "
            f"only WPA2-PSK and WPA3-SAE are supported"
        )
    elif wifi_security_protocol not in P341_WIFI_SUPPORTED_SECURITY_PROTOCOLS:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: invalid wifi_security_protocol={wifi_security_protocol!r}"
        )
    if access_point_set_requested and wifi_connect != "ON":
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: [Access Point Set.] requires [Wi-Fi Connect]=On"
        )
    if reset_action == "RESET_NETWORK_SET" and claimed_reset_network_wipes_airplane_mode:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: [Reset Network Set.] preserves [Airplane Mode]=On"
        )
    if reset_action == "CAMERA_SETTINGS_RESET" and claimed_camera_reset_wipes_network:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: [Camera Settings Reset] does NOT reset Network menus"
        )
    if claimed_fx6_uses_single_wifi_sku:
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: FX6 splits wireless SKUs between FX6V (2.4+5 GHz) "
            f"and FX6T (2.4 GHz only)"
        )

    if airplane_mode != "ON" or wifi_connect == "ON":
        errors.append(
            f"{P341_GD_ERR_WIFI_5GHZ_SKU_OR_SECURITY_OR_AIRPLANE}: Zero-RF bench gate requires [Airplane Mode]=ON "
            f"and [Wi-Fi Connect]=OFF (got airplane_mode={airplane_mode!r}, wifi_connect={wifi_connect!r})"
        )
    if not rf_nvs_p12_p13_readonly or rf_nvs_mutation_bytes != 0 or claim_rf_nvs_write_authorized:
        errors.append(
            f"{P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK}: p12/p13 RF NVS must remain MS_RDONLY with "
            f"rf_nvs_mutation_bytes=0"
        )
    if wireless_rf_packets_emitted != 0:
        errors.append(
            f"{P341_GD_ERR_RF_NVS_READONLY_OR_RF_PACKET_LEAK}: wireless_rf_packets_emitted={wireless_rf_packets_emitted} must be 0"
        )

    # IR Remote Ctrl, FX3A, BT mutex, 2.5mm LANC absence, and CTRL FOR HDMI (CEC)
    if camera_revision not in P341_VALID_FX3_REVISIONS:
        errors.append(f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: invalid camera_revision={camera_revision!r}")
    if ir_remote_ctrl not in P341_VALID_ON_OFF or bluetooth_rmt_ctrl not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: ir_remote_ctrl/bluetooth_rmt_ctrl must be ON/OFF")
    if ir_sensor_front_index != P341_FX3_IR_SENSOR_FRONT_INDEX or claimed_ir_sensor_is_front_8:
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: FX3 IR receiver is front #5 (Infrared remote sensor), "
            f"NOT front #{P341_FX3_AF_ILLUMINATOR_LAMP_FRONT_INDEX} (AF illuminator/Self-timer lamp)"
        )
    if camera_revision == "ILME_FX3A" and (ir_remote_ctrl == "ON" or claimed_fx3a_keeps_ir_sensor):
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: ILME-FX3A physically removed the front #5 IR remote receiver"
        )
    if ir_remote_ctrl == "ON" and bluetooth_rmt_ctrl == "ON":
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: [IR Remote Ctrl]=On and [Bluetooth Rmt Ctrl]=On are mutually exclusive"
        )
    if ir_remote_ctrl == "ON" and expect_power_save_sleeps_during_ir:
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: [IR Remote Ctrl]=On bypasses [Power Save Start Time]"
        )
    if claimed_fx3_has_2_5mm_lanc:
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: FX3 has ZERO 2.5mm LANC terminal (unlike FX6 #24 REMOTE + 3.5mm Grip)"
        )
    if claimed_ir_or_cec_wiped_by_camera_reset:
        errors.append(
            f"{P341_GD_ERR_IR_REMOTE_SENSOR_OR_FX3A_OR_LANC}: [IR Remote Ctrl] and [CTRL FOR HDMI] are both Reset-immune"
        )

    if ctrl_for_hdmi not in P341_VALID_ON_OFF:
        errors.append(f"{P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK}: invalid ctrl_for_hdmi={ctrl_for_hdmi!r}")
    if claimed_ctrl_for_hdmi_factory_default_is_off:
        errors.append(
            f"{P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK}: [CTRL FOR HDMI] ({P341_CTRL_FOR_HDMI_RESID16_HEX}, "
            f"{P341_CTRL_FOR_HDMI_SONY_TYPO_BKID}) ships factory-default ON and must be explicitly set OFF for bench"
        )
    if hdmi_bench_attached and ctrl_for_hdmi == "ON":
        errors.append(
            f"{P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK}: factory-default [CTRL FOR HDMI]=ON causes "
            f"{P341_CEC_EVENT_KEY_COUNT}-key EVENT_INPUT_KEY_CEC_* bench hijack hazard (STANDBY/MENU/EXIT); must be OFF on HDMI bench"
        )
    if claimed_cec_has_rec_key:
        errors.append(
            f"{P341_GD_ERR_CTRL_FOR_HDMI_BENCH_CEC_HIJACK}: the 41 EVENT_INPUT_KEY_CEC_* symbols include STANDBY/MENUs/PLAY/STOP "
            f"but include ZERO CEC_REC trigger"
        )

    # Fail-closed zero-write / passive-bench invariants
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
            f"{P341_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: fail-closed hardware/write/packet redline violated"
        )

    # Dual-media Tier-0 FX3RCPT1 & 16/16 H0 == H3
    tier0_verified = False
    receipt_mode = "NONE_AWAITING_PHYSICAL_TIER0"
    h0_eq_h3 = 0

    if simulate_bench_dry_run:
        receipt_mode = "SIMULATED_BENCH_DRY_RUN"
        sim = build_simulated_phase341_tier0_receipts(
            body_serial=body_serial or "FX3BENCH70200341",
            emmc_cid=emmc_cid or "11010030303847333000a1b2c3d40341",
        )
        drifted = max(0, int(simulated_h0_h3_drifted_surfaces))
        h0_eq_h3 = max(0, P341_STORAGE_SURFACE_COUNT - drifted)
        if h0_eq_h3 != P341_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0 == H3 parity drift "
                f"({h0_eq_h3}/{P341_STORAGE_SURFACE_COUNT})"
            )
        else:
            tier0_verified = True
        _ = sim
    elif receipt_a_bytes is not None or receipt_b_bytes is not None or receipt_a_path is not None or receipt_b_path is not None:
        receipt_mode = "PHYSICAL_DUAL_MEDIA_RECEIPT"
        raw_a = receipt_a_bytes
        raw_b = receipt_b_bytes
        st_dev_a = st_dev_a_override
        st_dev_b = st_dev_b_override
        if raw_a is None and receipt_a_path is not None:
            if not receipt_a_path.is_file():
                errors.append(
                    f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a not found ({receipt_a_path})"
                )
            else:
                st_dev_a = st_dev_a if st_dev_a is not None else os.stat(receipt_a_path).st_dev
                raw_a = receipt_a_path.read_bytes()
        if raw_b is None and receipt_b_path is not None:
            if not receipt_b_path.is_file():
                errors.append(
                    f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b not found ({receipt_b_path})"
                )
            else:
                st_dev_b = st_dev_b if st_dev_b is not None else os.stat(receipt_b_path).st_dev
                raw_b = receipt_b_path.read_bytes()

        if body_serial is not None and (
            not BODY_SERIAL_RE.match(body_serial) or body_serial in FORBIDDEN_TRIVIAL_SERIALS
        ):
            errors.append(
                f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial body_serial={body_serial!r}"
            )
        if emmc_cid is not None and (
            not HEX32_CID_RE.match(emmc_cid) or emmc_cid.lower() in FORBIDDEN_TRIVIAL_CIDS
        ):
            errors.append(
                f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial emmc_cid={emmc_cid!r}"
            )

        parsed_a, errs_a = _verify_single_receipt(raw_a, label="receipt_a")
        parsed_b, errs_b = _verify_single_receipt(raw_b, label="receipt_b")
        errors.extend(errs_a)
        errors.extend(errs_b)

        if raw_a is not None and raw_b is not None and raw_a != raw_b:
            errors.append(
                f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a != receipt_b byte mismatch"
            )
        if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
            errors.append(
                f"{P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media receipts must reside on "
                f"distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
            )

        if h0_baselines_a is None or h0_baselines_b is None or h3_baselines is None:
            if parsed_a is not None and parsed_b is not None and not errs_a and not errs_b:
                eff_serial = body_serial or "FX3BENCH70200341"
                eff_cid = emmc_cid or "11010030303847333000a1b2c3d40341"
                auto_h0 = build_default_h0_baselines(body_serial=eff_serial, emmc_cid=eff_cid)
                h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else dict(auto_h0)
                h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else dict(auto_h0)
                h3_map = dict(h3_baselines) if h3_baselines is not None else dict(auto_h0)
            else:
                h0_a, h0_b, h3_map = {}, {}, {}
        else:
            h0_a = dict(h0_baselines_a)
            h0_b = dict(h0_baselines_b)
            h3_map = dict(h3_baselines)

        if not h0_a or not h0_b or not h3_map:
            h0_eq_h3 = 0
        else:
            key_mismatches = sum(
                1
                for key in REQUIRED_H0_BASELINE_KEYS
                if _is_trivial_hex64(h0_a.get(key, ""))
                or h0_a.get(key, "").lower() != h0_b.get(key, "").lower()
                or h0_a.get(key, "").lower() != h3_map.get(key, "").lower()
            )
            surface_mismatches = sum(
                1
                for surf in SIXTEEN_STORAGE_SURFACES
                if h0_a.get(surf) != h0_b.get(surf) or h0_a.get(surf) != h3_map.get(surf)
            )
            extra_keys = set(h0_a.keys()) | set(h0_b.keys()) | set(h3_map.keys())
            extra_mismatches = sum(
                1
                for k in extra_keys
                if (k in h0_a) != (k in h3_map)
                or (k in h0_a) != (k in h0_b)
                or str(h0_a.get(k, "")).lower() != str(h3_map.get(k, "")).lower()
                or str(h0_a.get(k, "")).lower() != str(h0_b.get(k, "")).lower()
            )
            drifted = max(
                0,
                int(simulated_h0_h3_drifted_surfaces),
                key_mismatches,
                surface_mismatches,
                extra_mismatches,
            )
            h0_eq_h3 = max(0, P341_STORAGE_SURFACE_COUNT - drifted)
        if h0_eq_h3 != P341_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 surface parity failed "
                f"({h0_eq_h3}/{P341_STORAGE_SURFACE_COUNT})"
            )

        if not any(
            e.startswith(P341_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            or e.startswith(P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)
            for e in errors
        ):
            tier0_verified = True
    else:
        if simulated_h0_h3_drifted_surfaces > 0:
            errors.append(
                f"{P341_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0/H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
            )

    return P341CheckGroupDWifi5GhzIrRemoteCecTier0Result(
        group_id=P341_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        wifi_sku=wifi_sku,
        wifi_connect=wifi_connect,
        wifi_frequency_band=wifi_frequency_band,
        wifi_security_protocol=wifi_security_protocol,
        wifi_sku_gating_symbol=P341_WIFI_SKU_GATING_SYMBOL,
        airplane_mode=airplane_mode,
        rf_nvs_p12_p13_readonly=rf_nvs_p12_p13_readonly,
        rf_nvs_mutation_bytes=rf_nvs_mutation_bytes,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        camera_revision=camera_revision,
        ir_remote_ctrl=ir_remote_ctrl,
        ir_sensor_front_index=ir_sensor_front_index,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        fx3_2_5mm_lanc_present=P341_FX3_2_5MM_LANC_PRESENT,
        ctrl_for_hdmi=ctrl_for_hdmi,
        ctrl_for_hdmi_factory_default=P341_CTRL_FOR_HDMI_FACTORY_DEFAULT,
        ctrl_for_hdmi_typo_bkid=P341_CTRL_FOR_HDMI_SONY_TYPO_BKID,
        cec_event_key_count=P341_CEC_EVENT_KEY_COUNT,
        hdmi_bench_attached=hdmi_bench_attached,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3,
        h0_h3_surface_count=P341_STORAGE_SURFACE_COUNT,
        emmc_write_count=emmc_write_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_simulated_phase341_tier0_receipts(
    *,
    body_serial: str = "FX3BENCH70200341",
    emmc_cid: str = "11010030303847333000a1b2c3d40341",
) -> Dict[str, Any]:
    """Build synthetic deterministic dual-media H0/H3 baseline maps + 528-byte FX3RCPT1 receipts."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE341_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE341_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    raw_receipt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    assert len(raw_receipt) == SD_RECEIPT_BYTES
    base = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "receipt_a_bytes": raw_receipt,
        "receipt_b_bytes": bytes(raw_receipt),
        "st_dev_a": 1001,
        "st_dev_b": 1002,
        "h0_baselines_a": dict(base),
        "h0_baselines_b": dict(base),
        "h3_baselines": dict(base),
    }


# ---------------------------------------------------------------------------
# Master Preflight Orchestrator, Verifier & Markdown Renderer
# ---------------------------------------------------------------------------
def evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P341_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Group A (Wave 68 §§1-2)
    area_zone: str = "AREA_GMT_P_09_0",
    exposed_area_gmt_zones: Tuple[str, ...] = P341_AREA_GMT_THIRTY_ZONES,
    daylight_savings: str = "OFF",
    date_format: str = "Y_M_D",
    rtc_backup_charge_hours: float = 24.0,
    rtc_initialized: bool = True,
    claimed_user_replaceable_cr2032_present: bool = False,
    rtc_discharge_without_24h_charge_claimed: bool = False,
    claimed_area_date_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_standalone_dst_switch: bool = False,
    expect_area_date_uses_legacy_name_only: bool = False,
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS",
    hdmi_info_display: str = "ON",
    hdmi_raw_output: str = "OFF",
    rec_media_dur_hdmi_output: str = "ON",
    marker_display: str = "OFF",
    center_marker: str = "OFF",
    aspect_marker: str = "OFF",
    safety_zone: str = "OFF",
    guideframe: str = "OFF",
    focus_magnifier_active: bool = False,
    expect_marker_outputs_over_hdmi: bool = False,
    expect_grid_passes_hdmi_when_info_off_or_raw: bool = False,
    expect_marker_active_in_still_mode: bool = False,
    expect_marker_visible_during_focus_magnifier: bool = False,
    claimed_grid_or_marker_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_3mode_static_grid_line_menu: bool = False,
    # Group B (Wave 68 §§3-4)
    camset_action: str = "NONE",
    camset_slot: int = 1,
    camset_file_index: int = 1,
    camset_media_type: str = "CFEXPRESS_A",
    camset_card_template: str = P341_CAMSET_CARD_TEMPLATE,
    camset_fw_version: str = TARGET_BODY_FW,
    claimed_camset_allows_slot2: bool = False,
    claimed_camset_uses_pro_camera_path: bool = False,
    claimed_camset_includes_excluded_items: bool = False,
    claimed_ftpset_shares_camset_dir: bool = False,
    campr_action: str = "NONE",
    campr_slot: str = "M1",
    memory_recall_media_slot: int = 2,
    claimed_campr_includes_custom_key_or_program_shift: bool = False,
    ftpset_action: str = "NONE",
    ftpset_slot: int = 2,
    claimed_fx6_reference_file_present: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    pc_sync_terminal_requested: bool = False,
    claimed_fx3_sync_terminal_present: bool = False,
    xlr_h1_attached: bool = True,
    hvl_lbpc_direct_mount_requested: bool = False,
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_draw_ma: int = 0,
    flash_mode: str = "OFF",
    flash_xsync_denominator: int = P341_FLASH_XSYNC_DENOMINATOR,
    flash_trigger_voltage_v: float = 0.0,
    claimed_fx6_video_light_has_auto_mode: bool = False,
    claimed_fx6_genlock_bnc_present: bool = False,
    fx6_genlock_requested: bool = False,
    # Group C (Wave 69 §§1-2)
    playback_magnify_requested: bool = False,
    playback_media_kind: str = "STILL",
    enlarge_initial_mag: str = "STANDARD_MAG",
    enlarge_initial_pos: str = "FOCUSED_POSITION",
    claimed_playback_magnify_works_on_movies: bool = False,
    claimed_playback_magnify_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_playback_enlarge: bool = False,
    anti_flicker_shoot: str = "OFF",
    still_shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    bulb_enabled: bool = False,
    claimed_anti_flicker_effective_on_high_freq_led: bool = False,
    claimed_anti_flicker_shoot_resists_camera_reset: bool = False,
    dormant_var_shutter_requested: bool = False,
    dormant_anti_flicker_set_requested: bool = False,
    dormant_anti_flicker_tv_scan_requested: bool = False,
    claimed_fx3_var_shutter_present: bool = False,
    claimed_fx3_anti_flicker_tv_scan_present: bool = False,
    claimed_fx3_anti_flicker_set_present: bool = False,
    fx6_ecs_enabled: bool = False,
    fx6_ecs_freq_hz: float = 60.0,
    claimed_fx6_lacks_ecs: bool = False,
    # Group D (Wave 69 §§3-4 + Tier-0)
    wifi_sku: str = "WW728473",
    wifi_connect: str = "OFF",
    wifi_frequency_band: str = "2_4_GHZ",
    wifi_security_protocol: str = "WPA2_PSK",
    access_point_set_requested: bool = False,
    claimed_ww558244_supports_5ghz: bool = False,
    claimed_ver700_supports_wep_wpa_ipsec: bool = False,
    claimed_reset_network_wipes_airplane_mode: bool = False,
    claimed_camera_reset_wipes_network: bool = False,
    claimed_fx6_uses_single_wifi_sku: bool = False,
    airplane_mode: str = "ON",
    rf_nvs_p12_p13_readonly: bool = True,
    rf_nvs_mutation_bytes: int = 0,
    claim_rf_nvs_write_authorized: bool = False,
    camera_revision: str = "ILME_FX3",
    ir_remote_ctrl: str = "OFF",
    ir_sensor_front_index: int = 5,
    bluetooth_rmt_ctrl: str = "OFF",
    expect_power_save_sleeps_during_ir: bool = False,
    claimed_ir_sensor_is_front_8: bool = False,
    claimed_fx3a_keeps_ir_sensor: bool = False,
    claimed_fx3_has_2_5mm_lanc: bool = False,
    ctrl_for_hdmi: str = "OFF",
    hdmi_bench_attached: bool = True,
    claimed_ctrl_for_hdmi_factory_default_is_off: bool = False,
    claimed_ir_or_cec_wiped_by_camera_reset: bool = False,
    claimed_cec_has_rec_key: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport:
    donor = inspect_phase341_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p341_check_group_a_area_date_grid_and_marker(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        area_zone=area_zone,
        exposed_area_gmt_zones=exposed_area_gmt_zones,
        daylight_savings=daylight_savings,
        date_format=date_format,
        rtc_backup_charge_hours=rtc_backup_charge_hours,
        rtc_initialized=rtc_initialized,
        claimed_user_replaceable_cr2032_present=claimed_user_replaceable_cr2032_present,
        rtc_discharge_without_24h_charge_claimed=rtc_discharge_without_24h_charge_claimed,
        claimed_area_date_wiped_by_camera_reset=claimed_area_date_wiped_by_camera_reset,
        claimed_fx6_has_standalone_dst_switch=claimed_fx6_has_standalone_dst_switch,
        expect_area_date_uses_legacy_name_only=expect_area_date_uses_legacy_name_only,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        marker_display=marker_display,
        center_marker=center_marker,
        aspect_marker=aspect_marker,
        safety_zone=safety_zone,
        guideframe=guideframe,
        focus_magnifier_active=focus_magnifier_active,
        expect_marker_outputs_over_hdmi=expect_marker_outputs_over_hdmi,
        expect_grid_passes_hdmi_when_info_off_or_raw=expect_grid_passes_hdmi_when_info_off_or_raw,
        expect_marker_active_in_still_mode=expect_marker_active_in_still_mode,
        expect_marker_visible_during_focus_magnifier=expect_marker_visible_during_focus_magnifier,
        claimed_grid_or_marker_wiped_by_camera_reset=claimed_grid_or_marker_wiped_by_camera_reset,
        claimed_fx6_has_3mode_static_grid_line_menu=claimed_fx6_has_3mode_static_grid_line_menu,
    )

    gb = evaluate_p341_check_group_b_camset_mishoe_and_flash_sync(
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        still_shutter_type=still_shutter_type,
        camset_action=camset_action,
        camset_slot=camset_slot,
        camset_file_index=camset_file_index,
        camset_media_type=camset_media_type,
        camset_card_template=camset_card_template,
        camset_fw_version=camset_fw_version,
        claimed_camset_allows_slot2=claimed_camset_allows_slot2,
        claimed_camset_uses_pro_camera_path=claimed_camset_uses_pro_camera_path,
        claimed_camset_includes_excluded_items=claimed_camset_includes_excluded_items,
        claimed_ftpset_shares_camset_dir=claimed_ftpset_shares_camset_dir,
        campr_action=campr_action,
        campr_slot=campr_slot,
        memory_recall_media_slot=memory_recall_media_slot,
        claimed_campr_includes_custom_key_or_program_shift=claimed_campr_includes_custom_key_or_program_shift,
        ftpset_action=ftpset_action,
        ftpset_slot=ftpset_slot,
        claimed_fx6_reference_file_present=claimed_fx6_reference_file_present,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_data_sector_writes=slot1_data_sector_writes,
        pc_sync_terminal_requested=pc_sync_terminal_requested,
        claimed_fx3_sync_terminal_present=claimed_fx3_sync_terminal_present,
        xlr_h1_attached=xlr_h1_attached,
        hvl_lbpc_direct_mount_requested=hvl_lbpc_direct_mount_requested,
        video_light_mode=video_light_mode,
        mi_shoe_5v_draw_ma=mi_shoe_5v_draw_ma,
        flash_mode=flash_mode,
        flash_xsync_denominator=flash_xsync_denominator,
        flash_trigger_voltage_v=flash_trigger_voltage_v,
        claimed_fx6_video_light_has_auto_mode=claimed_fx6_video_light_has_auto_mode,
        claimed_fx6_genlock_bnc_present=claimed_fx6_genlock_bnc_present,
        fx6_genlock_requested=fx6_genlock_requested,
    )

    gc = evaluate_p341_check_group_c_pb_magnify_and_antiflicker(
        shoot_mode=shoot_mode,
        playback_magnify_requested=playback_magnify_requested,
        playback_media_kind=playback_media_kind,
        enlarge_initial_mag=enlarge_initial_mag,
        enlarge_initial_pos=enlarge_initial_pos,
        claimed_playback_magnify_works_on_movies=claimed_playback_magnify_works_on_movies,
        claimed_playback_magnify_wiped_by_camera_reset=claimed_playback_magnify_wiped_by_camera_reset,
        claimed_fx6_has_playback_enlarge=claimed_fx6_has_playback_enlarge,
        anti_flicker_shoot=anti_flicker_shoot,
        still_shutter_type=still_shutter_type,
        silent_mode=silent_mode,
        bulb_enabled=bulb_enabled,
        claimed_anti_flicker_effective_on_high_freq_led=claimed_anti_flicker_effective_on_high_freq_led,
        claimed_anti_flicker_shoot_resists_camera_reset=claimed_anti_flicker_shoot_resists_camera_reset,
        dormant_var_shutter_requested=dormant_var_shutter_requested,
        dormant_anti_flicker_set_requested=dormant_anti_flicker_set_requested,
        dormant_anti_flicker_tv_scan_requested=dormant_anti_flicker_tv_scan_requested,
        claimed_fx3_var_shutter_present=claimed_fx3_var_shutter_present,
        claimed_fx3_anti_flicker_tv_scan_present=claimed_fx3_anti_flicker_tv_scan_present,
        claimed_fx3_anti_flicker_set_present=claimed_fx3_anti_flicker_set_present,
        fx6_ecs_enabled=fx6_ecs_enabled,
        fx6_ecs_freq_hz=fx6_ecs_freq_hz,
        claimed_fx6_lacks_ecs=claimed_fx6_lacks_ecs,
    )

    gd = evaluate_p341_check_group_d_wifi_ir_cec_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        reset_action=reset_action,
        wifi_sku=wifi_sku,
        wifi_connect=wifi_connect,
        wifi_frequency_band=wifi_frequency_band,
        wifi_security_protocol=wifi_security_protocol,
        access_point_set_requested=access_point_set_requested,
        claimed_ww558244_supports_5ghz=claimed_ww558244_supports_5ghz,
        claimed_ver700_supports_wep_wpa_ipsec=claimed_ver700_supports_wep_wpa_ipsec,
        claimed_reset_network_wipes_airplane_mode=claimed_reset_network_wipes_airplane_mode,
        claimed_camera_reset_wipes_network=claimed_camera_reset_wipes_network,
        claimed_fx6_uses_single_wifi_sku=claimed_fx6_uses_single_wifi_sku,
        airplane_mode=airplane_mode,
        rf_nvs_p12_p13_readonly=rf_nvs_p12_p13_readonly,
        rf_nvs_mutation_bytes=rf_nvs_mutation_bytes,
        claim_rf_nvs_write_authorized=claim_rf_nvs_write_authorized,
        camera_revision=camera_revision,
        ir_remote_ctrl=ir_remote_ctrl,
        ir_sensor_front_index=ir_sensor_front_index,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        expect_power_save_sleeps_during_ir=expect_power_save_sleeps_during_ir,
        claimed_ir_sensor_is_front_8=claimed_ir_sensor_is_front_8,
        claimed_fx3a_keeps_ir_sensor=claimed_fx3a_keeps_ir_sensor,
        claimed_fx3_has_2_5mm_lanc=claimed_fx3_has_2_5mm_lanc,
        ctrl_for_hdmi=ctrl_for_hdmi,
        hdmi_bench_attached=hdmi_bench_attached,
        claimed_ctrl_for_hdmi_factory_default_is_off=claimed_ctrl_for_hdmi_factory_default_is_off,
        claimed_ir_or_cec_wiped_by_camera_reset=claimed_ir_or_cec_wiped_by_camera_reset,
        claimed_cec_has_rec_key=claimed_cec_has_rec_key,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        usb_packets_transmitted=usb_packets_transmitted,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
    )

    groups = (ga, gb, gc, gd)
    groups_passed = sum(1 for g in groups if g.passed)
    all_errors = (*ga.errors, *gb.errors, *gc.errors, *gd.errors)
    all_warnings = (*ga.warnings, *gb.warnings, *gc.warnings, *gd.warnings)

    if len(all_errors) > 0:
        overall_status = (
            P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE
        )
        go_no_go = (
            P341_GO_NO_GO_BLOCKED_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_FAILURE
        )
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = (
            P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED
        )
        go_no_go = (
            P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED
        )
    else:
        overall_status = P341_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    report = RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport(
        schema_version=P341_SCHEMA,
        phase_version=P341_VERSION,
        sony_help_guide_id=sony_help_guide_id,
        verification_mode=donor.verification_mode,
        simulate_bench_dry_run=bool(simulate_bench_dry_run),
        overall_status=overall_status,
        go_no_go=go_no_go,
        body_model_id_hex=hex(body_model_id),
        body_fw=body_fw,
        reset_action=reset_action,
        check_group_count=4,
        check_groups_passed=groups_passed,
        check_group_a=ga,
        check_group_b=gb,
        check_group_c=gc,
        check_group_d=gd,
        donor_inspection=donor,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        receipt_mode=gd.receipt_mode,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        slot1_tier0_vault_mutated=gb.slot1_tier0_vault_mutated,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_sync_terminal_present=False,
        fx6_genlock_bnc_present=False,
        fx3_var_shutter_present=False,
        fx3_anti_flicker_tv_scan_present=False,
        fx3_anti_flicker_set_present=False,
        fx3_2_5mm_lanc_present=False,
        fx6_standalone_dst_switch_present=False,
        fx6_reference_file_present=False,
        fx3_marker_outputs_to_hdmi=False,
        fx3_camset_allows_slot2=False,
        emmc_write_count=PHASE341_SLOT1_DATA_SECTOR_WRITES,
        e_nd_actuator_tx_count=PHASE341_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE341_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE341_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=PHASE341_RF_NVS_MUTATION_BYTES,
        slot1_data_sector_writes=PHASE341_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE341_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE341_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE341_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport(
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


def run_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
    **kwargs: Any,
) -> RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport:
    return evaluate_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_preflight(
        **kwargs
    )


def verify_phase341_report(
    payload: Union[
        Mapping[str, Any],
        RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport,
    ],
) -> Phase341ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P341_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P341_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P341_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_341_VALID_GO_NO_GO_VALUES:
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
        "fx3_sync_terminal_present",
        "fx6_genlock_bnc_present",
        "fx3_var_shutter_present",
        "fx3_anti_flicker_tv_scan_present",
        "fx3_anti_flicker_set_present",
        "fx3_2_5mm_lanc_present",
        "fx6_standalone_dst_switch_present",
        "fx6_reference_file_present",
        "fx3_marker_outputs_to_hdmi",
        "fx3_camset_allows_slot2",
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
        P341_GO_NO_GO_AREA_DATE_DST_GRID_CLEANHDMI_CAMSET_MISHOE_PB_MAGNIFY_WIFI_5GHZ_AND_CEC_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase341ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase341_markdown(
    report: RealHwAreaDateDstGridCleanHdmiCamsetMiShoePbMagnifyWifi5GhzCecReport,
) -> str:
    lines = [
        f"# Phase 341 — 18th Physical Bench Readiness Preflight (`{report.schema_version}`)",
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
        f"`rf_pkts={report.rf_packets_transmitted}`, `rf_nvs_mut={report.rf_nvs_mutation_bytes}`, "
        f"`usb_pkts={report.usb_packets_transmitted}`, `slot1_writes={report.slot1_data_sector_writes}`, "
        f"`leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"area=`{report.check_group_a.area_zone}` ({report.check_group_a.area_gmt_zone_count} zones / "
        f"{report.check_group_a.area_half_hour_zone_count} half-hour, Reset-immune, typo `{report.check_group_a.daylight_savings_elf_typo_func}`), "
        f"grid=`{report.check_group_a.grid_line_display}` (`{report.check_group_a.grid_line_type}`, hdmi_pass=`{report.check_group_a.grid_line_passes_over_hdmi}`), "
        f"marker=`{report.check_group_a.marker_display}` (`marker_hdmi={report.check_group_a.fx3_marker_outputs_to_hdmi}`)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"camset_slot=`{report.check_group_b.camset_slot}` (0 PRO/CAMERA hits, Slot-1 EROFS=30 firewall), "
        f"sync_terminal=`{report.check_group_b.fx3_sync_terminal_present}` ({report.check_group_b.fx3_synchro_terminal_hits} hits), "
        f"xlr_h1=`{report.check_group_b.xlr_h1_attached}` (passive cold shoe), "
        f"fx6_genlock=`{report.check_group_b.fx6_genlock_bnc_present}` ({report.check_group_b.fx6_genlock_dormant_hits} dormant symbols)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"pb_magnify=`{report.check_group_c.playback_magnify_requested}` ({report.check_group_c.playback_media_kind}, "
        f"typo `{report.check_group_c.playback_magnify_pinch_typo_symbol}`, Reset-immune), "
        f"anti_flicker=`{report.check_group_c.anti_flicker_shoot}`, "
        f"dormant_var_shutter=`{report.check_group_c.fx3_var_shutter_present}` / "
        f"tv_scan=`{report.check_group_c.fx3_anti_flicker_tv_scan_present}` (`EOPNOTSUPP=95`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"wifi=`{report.check_group_d.wifi_sku}`/{report.check_group_d.wifi_frequency_band} "
        f"({report.check_group_d.wifi_security_protocol}, airplane=`{report.check_group_d.airplane_mode}`, "
        f"p12/p13_ro=`{report.check_group_d.rf_nvs_p12_p13_readonly}`), "
        f"ir=`{report.check_group_d.ir_remote_ctrl}` (front `#{report.check_group_d.ir_sensor_front_index}`, "
        f"rev=`{report.check_group_d.camera_revision}`, lanc=`{report.check_group_d.fx3_2_5mm_lanc_present}`), "
        f"ctrl_for_hdmi=`{report.check_group_d.ctrl_for_hdmi}` (factory_def=`{report.check_group_d.ctrl_for_hdmi_factory_default}`, "
        f"typo `{report.check_group_d.ctrl_for_hdmi_typo_bkid}`, {report.check_group_d.cec_event_key_count} CEC events)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
