"""Phase 329: 15th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier (Waves 62-63).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Waves 62-63 before any physical bench session:

1. **Check Group A (Wave 62 §§1-2)** — ``[Audio Recording]`` / ``[Shoe Audio Set.]`` 4ch 24-bit Routing &
   ``[Face/Eye AF]`` Subject Recognition (``Human``/``Animal`` ONLY + Wave-42 Bird Errata):
   - ``Shooting -> [Audio Recording] -> [Audio Out Timing]`` (``_f 0x6bc2``, ``Live``/``Lip Sync``; NOT under
     ``Setup -> [Sound Option]``; disabled in ``S&Q``).
   - Ver. 2.00+ removal of standalone ``[Audio Level Display]`` (``_f 0x7a36``, ``EOPNOTSUPP=95``; DISP meter).
   - ``[Audio Rec Level]`` (``0..31``, default ``26``, non-disableable Limiter vs FX6 6-step ``Limiter Mode``
     and dormant FX6 ``ns1 0x3215`` ``32bit float``).
   - ``[Shoe Audio Set.]`` (``_f 0x77f6``): ``48kHz/24bit 4ch`` across ALL 6 main XAVC codecs vs Proxy forced
     ``MPEG-4 AAC-LC 2ch 128kbps`` and disabled ``>= 100p``, ``3.5mm MIC`` hardware override graying out
     ``[Shoe Audio Set.]``, ``XLR-H1 HANDLE AUDIO=OFF`` internal mic fallback, ``ANALOG`` ``16bit 2ch`` cap,
     and built-in-only ``[Wind Noise Reduct.]``.
   - ``[Face/Eye Subject]`` (``_f 0x70fa``): **ONLY ``Human`` and ``Animal``**! Explicitly corrects Wave-42
     Bird errata: dormant ``Bird`` (``0x6cb1``), ``Animal/Bird`` (``0x6957``), ``Insect`` (``0x6996``),
     ``Car/Train`` (``0x674e``), ``Airplane`` (``0x7440``, 0 hits in ``BKID_APP_*``) -> ``EOPNOTSUPP=95``.
   - ``Animal`` Eye AF is Still-only (``TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`` -> ``EOPNOTSUPP=95`` in
     Movie/S&Q); ``8``-face ``[Face Memory]`` survives Reset & is excluded from ``CAMSET*.DAT``; Clean HDMI
     never outputs ``[Face/Eye Frame Disp.]``.

2. **Check Group B (Wave 62 §§3-4)** — ``[Silent Mode Settings]`` 5-Lockout, 2-Item ``[Target Function Settings]``,
   Dormant ``[Shutter When Pwr OFF]``, Zero-RF ``[Version]`` & HARD ``NO-GO / BLOCKED`` ``BODYDATA.DAT`` Firewall:
   - ``[Silent Mode Settings]`` (``_f 0x655f``) 2-level submenu forcing electronic shutter + ``Audio signals=Off``
     and hard-disabling 5 functions (Flash, ``Long Exposure NR``, ``e-Front Curtain Shut.``, ``BULB``,
     ``Anti-flicker Shoot.``; does NOT auto-disable ``AF Illuminator``).
   - Exact **2-item** ``[Target Function Settings]`` (``_f 0x79c0``): ``[Aperture Drive in AF]`` (Still-only) &
     ``[Auto Pixel Mapping]`` (``Off`` prevents power-off mechanical curtain & ``cnflasha`` writes).
   - Dormant ``[Shutter When Pwr OFF]`` (``_f 0x709f`` / ``image_sensor_barrier`` -> ``EOPNOTSUPP=95``).
   - Zero-RF ``Airplane Mode = On`` silencing ``Ver. 6.00+`` ``_g 0x6516`` update badge.
   - **HARD ``NO-GO / BLOCKED`` ``Slot-1 BODYDATA.DAT`` / FX6 ``Slot B AC Adaptor`` Flash Firewall**
     (``EROFS=30`` / ``EPERM=1``; ``<= Ver. 2.02`` mandatory ``Ver. 2.04/2.05`` stepping-stone audit).

3. **Check Group C (Wave 63 §§1-2)** — ``[HDMI Output Settings]`` 8-Item Tree, 16-bit ``4264x2408`` RAW Co-Rec
   Vault Firewall & Ver. 7.00+ 4-Ratio ``[De-Squeeze Display]`` (``1.3x``/``1.5x``/``1.6x[1.65x]``/``2.0x``):
   - ``Setup -> [External Output] -> [HDMI Output Settings]`` 8 Initialize-only items; Ver. 2.00+ removal of
     ``[Color Gamut for RAW Output]`` (``_f 0x6bdc`` -> ``EOPNOTSUPP=95``).
   - ``4264x2408`` 16-bit ``[RAW Output] = On`` + ``[Rec. Media dur HDMI Output] = On`` co-records internal
     XAVC+Proxy (``EROFS=30`` on Slot-1 Tier-0 Vault) vs zero card writes under ``Off(HDMI Only)``.
   - 10-bit-only ``[4K Output Set.(HDMI Only)]`` (dormant ``24.00p 8bit`` ``_f 0x748a`` -> ``EOPNOTSUPP=95``);
     ``[HDMI Info. Display] = On`` blanks FX3 LCD; vs FX6 ``12G-SDI RAW`` / ``4240x2392`` ``RAW(HDMI)``
     excluding ``24Hz`` / ``SDI/HDMI Remote I/F`` vs ``Parallel Rec``.
   - Initialize-only ``[De-Squeeze Display]`` (``Off``, ``1.3x``, ``1.5x``, ``1.6x`` [``1.65x``], ``2.0x``;
     absent ``1.8x`` -> ``EOPNOTSUPP=95``), 4 lockouts + 6 auto-bypass conditions + ``Focus Magnifier``/
     ``Bright Monitoring`` coexistence vs FX6 VF/HDMI-only ``1.3x/1.5x/2.0x``.

4. **Check Group D (Wave 63 §§3-4 & Tier-0)** — 3-Lamp ``[REC Lamp]``, ``[Emphasized REC Display]``,
   ``[Remain Shoot Display]``, Still ``[Auto Review]``, Dormant ``[Var. Shutter]`` vs FX6 ``ECS``, Wave-42
   Reset Errata on ``[APS-C S35 Shooting]`` & ``16/16 H0 == H3`` Dual-Media ``528 B FX3RCPT1`` Gate:
   - Initialize-only 3-lamp ``[REC Lamp]`` (``All On``/``Only Front Off``/``All Off``, dormant ``[Tally Light]``
     & ``_f 0x743e`` -> ``EOPNOTSUPP=95``, independent of ``[Silent Mode]``).
   - Resettable ``[Emphasized REC Display]``, active Initialize-only ``[Remain Shoot Display]`` & Still ``[Auto Review]``.
   - Dormant ``[Var. Shutter]`` (``high_res_ss`` ``_f 0x6831`` -> ``EOPNOTSUPP=95``) vs Still mech-shutter
     ``[Anti-flicker Shoot.]`` vs FX6 ``23.99..8000 Hz`` ``ECS``.
   - **Wave-42 Reset Errata on ``[APS-C S35 Shooting]``**: Initialize-only (NOT resettable by
     ``[Camera Settings Reset]``); ``On`` locks out ALL 4K/DCI 4K/RAW formats to ``HD 1920x1080 <= 120p`` and
     drops Still ``L: 12M`` to ``M: 5.1M`` (``2768x1848``, NOT ``4.2M``).
   - ``16/16 H0 == H3`` + dual-media ``528 B FX3RCPT1`` Tier-0 receipt gate.
"""

from __future__ import annotations

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

P329_VERSION = "phase329_v1"
PHASE_329_VERSION = P329_VERSION
P329_SCHEMA = "realhw_preflight15_shoe_audio_subject_hdmi_raw_desqueeze_varshutter_v1"
P329_SCHEMA_VERSION = P329_SCHEMA
PHASE_329_SCHEMA = P329_SCHEMA
REALHW_SHOE_AUDIO_4CH_SUBJECT_RECOG_HDMI_RAW_DESQUEEZE_VARSHUTTER_SCHEMA = P329_SCHEMA
P329_SONY_HELP_GUIDE_ID = "ilc/2210"

P329_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED = (
    "READONLY_PREFLIGHT15_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED"
)
P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE = (
    "BLOCKED_PREFLIGHT15_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE"
)
PHASE_329_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED,
    P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE,
)

# Bounded donor paths (read-only O_RDONLY)
P329_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx6_appfw_so", "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"),
    ("fx3_im_elf", "sony-firmware-20261024/stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf"),
    ("fx3_libjiritsu_so", "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"),
    ("fx3_libusbbuspower_so", "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"),
    ("fx3_upm_ko", "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko"),
)
P329_HEADER_READ_BYTES = 64

# Unconditional safety / zero-leak constants
PHASE329_RAW_FIRMWARE_BYTES_LEAKED = 0
PHASE329_PASSIVE_TX_BYTES_EMITTED = 0
PHASE329_USB_PACKETS_TRANSMITTED = 0
PHASE329_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE329_SLOT1_DATA_SECTOR_WRITES = 0
PHASE329_E_ND_ACTUATOR_TX_COUNT = 0

P329_ERRNO_EPERM = 1
P329_ERRNO_EBUSY = 16
P329_ERRNO_EINVAL = 22
P329_ERRNO_EROFS = 30
P329_ERRNO_EOPNOTSUPP = 95

# Check Group IDs
P329_CHECK_GROUP_A_ID = "GROUP_A_SHOE_AUDIO_4CH_AUDIO_OUT_TIMING_AND_SUBJECT_RECOG_HUMAN_ANIMAL"
P329_CHECK_GROUP_B_ID = "GROUP_B_SILENT_TARGET_2ITEM_NO_PWR_OFF_SHUTTER_AND_BODYDATA_NO_GO_FIREWALL"
P329_CHECK_GROUP_C_ID = "GROUP_C_HDMI_16BIT_RAW_COREC_VAULT_AND_V7_DESQUEEZE_4RATIOS_NO_1_8X"
P329_CHECK_GROUP_D_ID = "GROUP_D_REC_LAMP_EMPH_REC_DORMANT_VAR_SHUTTER_APSC_RESET_ERRATA_AND_TIER0"
PHASE_329_CHECK_GROUP_IDS = (
    P329_CHECK_GROUP_A_ID,
    P329_CHECK_GROUP_B_ID,
    P329_CHECK_GROUP_C_ID,
    P329_CHECK_GROUP_D_ID,
)

# Common enums
P329_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P329_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P329_VALID_ON_OFF = ("ON", "OFF")
P329_VALID_EXPOSURE_MODES = (
    "MANUAL_EXPOSURE",
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P329_VALID_LOG_SHOOTING_MODES = ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI")

# Wave 62 Group A constants
P329_AUDIO_OUT_TIMING_RESID16_HEX = "0x6bc2"
P329_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX = "0x7a36"
P329_SHOE_AUDIO_SET_RESID16_HEX = "0x77f6"
P329_AUDIO_REC_LEVEL_MIN = 0
P329_AUDIO_REC_LEVEL_MAX = 31
P329_AUDIO_REC_LEVEL_DEFAULT = 26
P329_VALID_AUDIO_OUT_TIMINGS = ("LIVE", "LIP_SYNC")
P329_VALID_SHOE_AUDIO_MODES = ("48KHZ_24BIT_4CH", "48KHZ_24BIT_2CH", "48KHZ_16BIT_2CH")
P329_VALID_AUDIO_MON_ROUTES = ("CH1_CH2", "CH3_CH4", "CH1_3_CH2_4", "CH1_CH1", "CH2_CH2")
P329_VALID_AUDIO_SIGNAL_MODES = ("ON", "OFF_SHUTTER_ONLY", "OFF")
P329_VALID_XLR_DIG_ANALOG_MODES = ("DIGITAL", "ANALOG")
P329_VALID_XLR_INPUT_SELECTS = ("IN1_IN2", "IN1")
P329_VALID_MAIN_XAVC_CODECS = (
    "XAVC_HS_4K",
    "XAVC_S_4K",
    "XAVC_S_HD",
    "XAVC_S_I_4K",
    "XAVC_S_I_HD",
    "XAVC_S_I_DCI_4K",
)
P329_PROXY_AUDIO_CODEC = "MPEG4_AAC_LC_2CH_128KBPS"
P329_PROXY_CUTOFF_FPS = 100.0

P329_FACE_EYE_SUBJECT_RESID16_HEX = "0x70fa"
P329_FACE_EYE_SUBJECT_VALID_TWO = ("HUMAN", "ANIMAL")
P329_DORMANT_AI_SUBJECTS = ("BIRD", "ANIMAL_BIRD", "INSECT", "CAR_TRAIN", "AIRPLANE")
P329_DORMANT_SUBJECT_RESIDS = {
    "BIRD": "0x6cb1",
    "ANIMAL_BIRD": "0x6957",
    "INSECT": "0x6996",
    "CAR_TRAIN": "0x674e",
    "AIRPLANE": "0x7440",
}
P329_VALID_EYE_SELECTS = ("AUTO", "RIGHT_EYE", "LEFT_EYE")
P329_FACE_MEMORY_MAX_SLOTS = 8

# Wave 62 Group B constants
P329_SILENT_MODE_SETTINGS_RESID16_HEX = "0x655f"
P329_TARGET_FUNCTION_SETTINGS_RESID16_HEX = "0x79c0"
P329_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX = "0x709f"
P329_DORMANT_ANTI_DUST_FUNCTION_RESID16_HEX = "0x7495"
P329_SOFTWARE_UPDATE_RESID16_HEX = "0x6fd6"
P329_VERSION_BADGE_RESID16_HEX = "0x6516"
P329_LENS_VERSION_RESID16_HEX = "0x6517"
P329_SILENT_MODE_FIVE_DISABLED_FUNCTIONS = (
    "FLASH_SHOOTING",
    "LONG_EXPOSURE_NR",
    "E_FRONT_CURTAIN_SHUT",
    "BULB_SHOOTING",
    "ANTI_FLICKER_SHOOT",
)
P329_TARGET_FUNCTION_EXACT_TWO_ITEMS = ("APERTURE_DRIVE_IN_AF", "AUTO_PIXEL_MAPPING")
P329_VALID_APERTURE_DRIVE_TARGET_MODES = ("STANDARD", "SILENT_PRIORITY", "NOT_TARGET")
P329_VALID_AUTO_PIXEL_MAPPING_TARGET_MODES = ("OFF", "NOT_TARGET")
P329_VALID_SHUTTER_TYPES = ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER")
P329_STEPPING_STONE_FWS = ("2.04", "2.05")
P329_BODYDATA_FILENAME = "BODYDATA.DAT"
P329_BODYDATA_MIN_BATTERY_SOC_PCT = 51.0
P329_FX3_FLASH_ERROR_LED_BLINK_PATTERN = "5_LONG_6_SHORT"

# Wave 63 Group C constants
P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS = (
    "REC_MEDIA_DUR_HDMI_OUTPUT",
    "OUTPUT_RESOLUTION",
    "4K_OUTPUT_SET_HDMI_ONLY",
    "RAW_OUTPUT",
    "RAW_OUTPUT_SETTING",
    "TIME_CODE_OUTPUT",
    "REC_CONTROL",
    "4CH_AUDIO_OUTPUT",
)
P329_REMOVED_COLOR_GAMUT_FOR_RAW_RESID16_HEX = "0x6bdc"
P329_DORMANT_4K_24P_8BIT_RESID16_HEX = "0x748a"
P329_HDMI_RAW_RESOLUTION_WH = "4264x2408"
P329_HDMI_RAW_BIT_DEPTH = 16
P329_FX6_HDMI_RAW_RESOLUTION_WH = "4240x2392"
P329_VALID_REC_MEDIA_DUR_HDMI = ("ON", "OFF_HDMI_ONLY")
P329_VALID_RECORDING_MEDIA_MODES = ("SLOT_1", "SLOT_2", "SIMULTANEOUS_RECORDING", "SORT_RECORDING")
P329_VALID_OUTPUT_RESOLUTIONS = ("AUTO", "2160P", "1080P", "1080I")
P329_VALID_4K_10BIT_SETTINGS = (
    "59.94P_10BIT",
    "50P_10BIT",
    "29.97P_10BIT",
    "25P_10BIT",
    "23.98P_10BIT",
    "24.00P_10BIT",
)
P329_VALID_RAW_OUTPUT_SETTINGS = ("59.94P", "50P", "29.97P", "25P", "23.98P", "24.00P")
P329_VALID_HDMI_4CH_OUTPUT_ROUTES = ("CH1_CH2", "CH3_CH4")
P329_VALID_STEADYSHOT_MODES = ("OFF", "STANDARD", "ACTIVE")
P329_VALID_FOCUS_MODES = ("MF", "AF_C", "AF_S", "AF_A", "DMF")
P329_VALID_FOCUS_AREAS = ("WIDE", "ZONE", "CENTER_FIX", "SPOT_S", "SPOT_M", "SPOT_L", "EXPAND_SPOT")

P329_DESQUEEZE_EXACT_FIVE_STATES = ("OFF", "1.3X", "1.5X", "1.6X", "2.0X")
P329_DESQUEEZE_1_6X_EXECUTED_FACTOR = 1.65
P329_DESQUEEZE_1_6X_RESID16_HEX = "0x7d09"
P329_DESQUEEZE_1_65X_DESC_RESID16_HEX = "0x7d0c"
P329_DESQUEEZE_FOUR_LOCKOUTS = (
    "FOCUS_MODE_MANUAL",
    "FOCUS_AREA_WIDE",
    "STEADYSHOT_OFF",
    "FACE_PRIORITY_MULTI_METERING_OFF",
)
P329_DESQUEEZE_SIX_BYPASS_CONDITIONS = (
    "LOG_SHOOTING_OFF",
    "RAW_OUTPUT_ON_HDMI",
    "REC_MEDIA_OFF_HDMI_ONLY_HDMI",
    "STILL_MOVIE_BUTTON",
    "REMOTE_SHOOTING",
    "PHOTO_CAPTURE",
)
P329_FX6_DESQUEEZE_RATIOS = ("OFF_1.0X", "1.3X", "1.5X", "2.0X")

# Wave 63 Group D constants
P329_REC_LAMP_THREE_STATES = ("ALL_ON", "ONLY_FRONT_OFF", "ALL_OFF")
P329_REC_LAMP_RESID16_HEX = "0x6e62"
P329_DORMANT_REC_LAMP_ONLY_ONE_RESID16_HEX = "0x743e"
P329_EMPH_REC_DISP_RESID16_HEX = "0x68cf"
P329_REMAIN_SHOOT_DISP_RESID16_HEX = "0x604d"
P329_VALID_REMAIN_SHOOT_MODES = ("NOT_DISPLAYED", "ALWAYS_DISPLAY", "SHOOT_ONLY_DISPLAY")
P329_VALID_AUTO_REVIEW_MODES = ("OFF", "2_SEC", "5_SEC", "10_SEC")
P329_DORMANT_VAR_SHUTTER_RESIDS = ("0x6831", "0x6f9e", "0x6399", "0x68e7", "0x60a8")
P329_ANTI_FLICKER_SHOOT_RESID16_HEX = "0x623d"
P329_VALID_APSC_S35_MODES = ("AUTO", "ON", "OFF")
P329_APSC_LOCKED_OUT_4K_FORMATS = ("XAVC_HS_4K", "XAVC_S_4K", "XAVC_S_I_4K", "XAVC_S_I_DCI_4K")
P329_APSC_STILL_MAX_SIZE_LABEL = "M_5_1M_2768x1848"
P329_VALID_STILL_IMAGE_SIZES = ("L_12M", "M_5_1M", "S_3_0M", "M_4_2M")
P329_FX6_ECS_MIN_HZ = 23.99
P329_FX6_ECS_MAX_HZ = 8000.0

# Error code constants
P329_GA_ERR_MODEL_OR_FW_FLOOR = "P329_GA_ERR_MODEL_OR_FW_FLOOR"
P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY = (
    "P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY"
)
P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF = (
    "P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF"
)
P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL = (
    "P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL"
)
P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME = (
    "P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME"
)

P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH = (
    "P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH"
)
P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE = (
    "P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE"
)
P329_GB_ERR_DORMANT_SHUTTER_WHEN_PWR_OFF = "P329_GB_ERR_DORMANT_SHUTTER_WHEN_PWR_OFF"
P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION = "P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION"
P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE = (
    "P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE"
)

P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT = (
    "P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT"
)
P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP = (
    "P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP"
)
P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION = (
    "P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION"
)
P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS = (
    "P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS"
)
P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION = (
    "P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION"
)

P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT = (
    "P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT"
)
P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW = (
    "P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW"
)
P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT = (
    "P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT"
)
P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA = (
    "P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA"
)
P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"


@dataclass(frozen=True)
class Phase329DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    fx3_appfw_present: bool
    fx6_appfw_present: bool
    fx3_uxc_present: bool
    checked_paths: Tuple[str, ...]
    bytes_read_total: int
    elapsed_seconds: float
    within_budget: bool
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class P329CheckGroupAShoeAudioAndSubjectRecogResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    audio_out_timing: str
    audio_rec_level: int
    shoe_audio_set: str
    four_ch_audio_monitoring: str
    wind_noise_reduct: str
    fx3_audio_level_display_menu_present: bool
    proxy_audio_codec: str
    face_eye_subject: str
    right_left_eye_select: str
    face_eye_frame_disp: str
    face_memory_count: int
    fx3_bird_insect_car_airplane_present: bool
    fx3_animal_eye_af_in_movie_present: bool


@dataclass(frozen=True)
class P329CheckGroupBSilentTargetAndBodydataFirewallResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    silent_mode: str
    audio_signals: str
    shutter_type: str
    target_aperture_drive_in_af: str
    target_auto_pixel_mapping: str
    exposed_target_function_items: Tuple[str, ...]
    fx3_shutter_when_pwr_off_present: bool
    airplane_mode: str
    bodydata_flash_policy: str
    stepping_stone_fw_required: bool
    rf_packets_transmitted: int
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool


@dataclass(frozen=True)
class P329CheckGroupCHdmiRawAndDesqueezeResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    exposed_hdmi_settings_items: Tuple[str, ...]
    rec_media_dur_hdmi_output: str
    hdmi_raw_output: str
    hdmi_raw_resolution_wh: str
    hdmi_raw_bit_depth: int
    hdmi_output_resolution: str
    hdmi_4k_setting: str
    hdmi_info_display: str
    fx3_color_gamut_for_raw_output_menu_present: bool
    fx3_4k_24p_8bit_present: bool
    slot1_tier0_vault_mutated: bool
    desqueeze_display: str
    desqueeze_executed_factor: float
    fx3_desqueeze_1_8x_present: bool
    desqueeze_four_lockouts_enforced: bool


@dataclass(frozen=True)
class P329CheckGroupDRecLampVarShutterApscAndTier0Result:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    rec_lamp_mode: str
    fx3_tally_light_menu_present: bool
    emphasized_rec_display: str
    remain_shoot_display: str
    auto_review: str
    anti_flicker_shoot: str
    fx3_var_shutter_present: bool
    fx6_ecs_freq_hz: float
    apsc_s35_shooting: str
    fx3_apsc_resets_via_camera_settings_reset: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    e_nd_actuator_tx_count: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class Phase329ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport:
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
    check_group_a: P329CheckGroupAShoeAudioAndSubjectRecogResult
    check_group_b: P329CheckGroupBSilentTargetAndBodydataFirewallResult
    check_group_c: P329CheckGroupCHdmiRawAndDesqueezeResult
    check_group_d: P329CheckGroupDRecLampVarShutterApscAndTier0Result
    donor_inspection: Phase329DonorInspectionResult
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
    fx3_audio_level_display_menu_present: bool
    fx3_bird_insect_car_airplane_present: bool
    fx3_animal_eye_af_in_movie_present: bool
    fx3_shutter_when_pwr_off_present: bool
    fx3_color_gamut_for_raw_output_menu_present: bool
    fx3_4k_24p_8bit_present: bool
    fx3_desqueeze_1_8x_present: bool
    fx3_tally_light_menu_present: bool
    fx3_var_shutter_present: bool
    fx3_apsc_resets_via_camera_settings_reset: bool
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
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
        return json.dumps(_zero_timing_fields(self.to_dict()), indent=indent, sort_keys=True) + "\n"


def _is_timing_key(key: str) -> bool:
    return key in (
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    ) or key.endswith(("_elapsed_ms", "_elapsed_s", "_elapsed_seconds"))


def _zero_timing_fields(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if _is_timing_key(ks) and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[ks] = 0.0
            else:
                out[ks] = _zero_timing_fields(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_zero_timing_fields(x) for x in obj]
    return obj


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


def _bounded_read_header(path: Path, max_bytes: int = P329_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def _resolve_work_root_or_none(
    *,
    force_clean_room: bool = False,
) -> Optional[Path]:
    """Return the first ``work/`` root containing BYOF donor artifacts, or ``None`` on donorless CI."""
    if force_clean_room or _is_clean_room_env():
        return None
    for candidate in iter_work_roots():
        if not candidate.is_dir():
            continue
        if any((candidate / rel).is_file() for _lbl, rel in P329_BOUNDED_DONOR_PATHS):
            return candidate
    return None


def inspect_phase329_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase329DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 0.20s) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase329DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = (
        work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    )
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase329DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P329_BOUNDED_DONOR_PATHS:
        resolved: Optional[Path] = None
        if label == "fx6_appfw_so" and fx6_lib_dir is not None:
            cand = fx6_lib_dir / "appFw.so"
            if cand.is_file():
                resolved = cand
        if label == "fx3_upm_ko" and fx3_modules_dir is not None:
            cand = fx3_modules_dir / "upm.ko"
            if cand.is_file():
                resolved = cand
        if resolved is None and effective_work_root is not None:
            cand = effective_work_root / rel
            if cand.is_file():
                resolved = cand
        if resolved is None and effective_work_root is not None:
            cand = resolve_work_subpath(rel, require_file=True)
            if cand.is_file():
                resolved = cand
        if resolved is not None and resolved.is_file():
            checked.append(label)
            bytes_total += _bounded_read_header(resolved)
            found_map[label] = True
        else:
            found_map[label] = False

    donor_present = any(found_map.values())
    mode = "LOCAL_DONOR_O_RDONLY" if donor_present else "CLEAN_ROOM_SYNTHETIC"
    elapsed = round(time.monotonic() - t0, 6)
    return Phase329DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_uxc_present=found_map.get("fx3_libusbbuspower_so", False) and found_map.get("fx3_upm_ko", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P329_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Wave 62 §1 Audio
    audio_recording: str = "ON",
    audio_out_timing: str = "LIVE",
    claimed_audio_out_timing_under_setup_sound_option: bool = False,
    audio_out_timing_active_in_sq_claimed: bool = False,
    audio_recording_in_sq_claimed: bool = False,
    claimed_audio_out_timing_resists_reset: bool = False,
    dormant_audio_level_display_requested: bool = False,
    fx3_audio_level_display_menu_present_claimed: bool = False,
    audio_rec_level: int = P329_AUDIO_REC_LEVEL_DEFAULT,
    fx3_disable_builtin_limiter_requested: bool = False,
    fx3_limiter_6step_present_claimed: bool = False,
    fx3_32bit_float_audio_claimed: bool = False,
    four_ch_audio_monitoring: str = "CH1_CH2",
    shoe_audio_set: str = "48KHZ_24BIT_4CH",
    movie_file_format: str = "XAVC_S_I_4K",
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    proxy_recording: str = "OFF",
    claimed_shoe_4ch_unsupported_on_xavc_codec: bool = False,
    expect_proxy_4ch_24bit_audio: bool = False,
    expect_proxy_active_at_100p_plus: bool = False,
    mic_35mm_inserted: bool = False,
    expect_shoe_audio_active_with_35mm_mic: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "ON",
    xlr_h1_dig_analog: str = "DIGITAL",
    xlr_h1_input_select: str = "IN1_IN2",
    expect_xlr_h1_audio_active_when_handle_off: bool = False,
    wind_noise_reduct: str = "OFF",
    expect_wind_noise_applies_to_xlr_or_35mm: bool = False,
    # Wave 62 §2 Subject Recognition + Wave-42 Bird Errata
    face_eye_prior_in_af: str = "ON",
    face_eye_subject: str = "HUMAN",
    dormant_subject_requested: str = "NONE",
    fx3_bird_insect_car_airplane_present_claimed: bool = False,
    fx3_animal_eye_af_in_movie_present_claimed: bool = False,
    expect_animal_eye_af_in_movie: bool = False,
    right_left_eye_select: str = "AUTO",
    face_eye_frame_disp: str = "OFF",
    expect_face_eye_frame_on_clean_hdmi: bool = False,
    face_memory_count: int = 0,
    regist_faces_priority: str = "ON",
    claimed_face_memory_wiped_by_camera_reset: bool = False,
    claimed_face_memory_exported_in_camset: bool = False,
    expect_regist_faces_priority_active_in_animal: bool = False,
    fx6_has_animal_or_bird_subject_claimed: bool = False,
    fx6_has_persistent_face_memory_claimed: bool = False,
) -> P329CheckGroupAShoeAudioAndSubjectRecogResult:
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_id != TARGET_MODEL_ID_INT
        or body_fw != TARGET_BODY_FW
        or sony_help_guide_id != P329_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P329_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW} "
            f"help_guide={P329_SONY_HELP_GUIDE_ID}, got {hex(body_model_id)} fw={body_fw} "
            f"help_guide={sony_help_guide_id}"
        )
    if reset_action not in P329_VALID_RESET_ACTIONS:
        errors.append(f"{P329_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action}")
    if shoot_mode not in P329_VALID_SHOOT_MODES:
        errors.append(f"{P329_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode}")
    if exposure_mode not in P329_VALID_EXPOSURE_MODES:
        errors.append(f"{P329_GA_ERR_MODEL_OR_FW_FLOOR}: invalid exposure_mode={exposure_mode}")

    # Audio Recording & Audio Out Timing
    if audio_recording not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: invalid audio_recording={audio_recording}"
        )
    if audio_out_timing not in P329_VALID_AUDIO_OUT_TIMINGS:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: invalid audio_out_timing={audio_out_timing}"
        )
    if claimed_audio_out_timing_under_setup_sound_option:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            f"[Audio Out Timing] ({P329_AUDIO_OUT_TIMING_RESID16_HEX}) resides under Shooting -> [Audio Recording], "
            "NOT Setup -> [Sound Option]"
        )
    if audio_out_timing_active_in_sq_claimed or audio_recording_in_sq_claimed:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            "[Audio Recording] & [Audio Out Timing] are disabled in S&Q mode"
        )
    if claimed_audio_out_timing_resists_reset:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            "[Audio Out Timing] IS resettable via [Camera Settings Reset]"
        )
    if dormant_audio_level_display_requested or fx3_audio_level_display_menu_present_claimed:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            f"standalone [Audio Level Display] ({P329_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX}) was removed in "
            f"Ver. 2.00+ (errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if not (P329_AUDIO_REC_LEVEL_MIN <= audio_rec_level <= P329_AUDIO_REC_LEVEL_MAX):
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            f"[Audio Rec Level] {audio_rec_level} out of range 0..31 (default 26)"
        )
    if fx3_disable_builtin_limiter_requested or fx3_limiter_6step_present_claimed or fx3_32bit_float_audio_claimed:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            "FX3 built-in Limiter is non-disableable (FX6 6-step Limiter Mode / dormant 32-bit float rejected, "
            f"errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if four_ch_audio_monitoring not in P329_VALID_AUDIO_MON_ROUTES:
        errors.append(
            f"{P329_GA_ERR_AUDIO_OUT_TIMING_OR_REMOVED_LEVEL_DISPLAY}: "
            f"invalid [4ch Audio Monitoring]={four_ch_audio_monitoring}"
        )

    # [Shoe Audio Set.] 4ch 24-bit matrix & hardware overrides
    if shoe_audio_set not in P329_VALID_SHOE_AUDIO_MODES:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid shoe_audio_set={shoe_audio_set}"
        )
    if movie_file_format not in P329_VALID_MAIN_XAVC_CODECS:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid movie_file_format={movie_file_format}"
        )
    if claimed_shoe_4ch_unsupported_on_xavc_codec:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            f"48kHz/24bit 4ch is supported across ALL 6 main XAVC codecs ({P329_SHOE_AUDIO_SET_RESID16_HEX})"
        )
    if proxy_recording not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid proxy_recording={proxy_recording}"
        )
    if expect_proxy_4ch_24bit_audio:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            f"Proxy files always use {P329_PROXY_AUDIO_CODEC}, never 4ch 24-bit LPCM"
        )
    eff_fps = sq_fps if (shoot_mode == "S_AND_Q" or sq_enabled) else rec_fps
    if expect_proxy_active_at_100p_plus or (proxy_recording == "ON" and eff_fps >= P329_PROXY_CUTOFF_FPS):
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            f"Proxy recording is cut off >= {P329_PROXY_CUTOFF_FPS}p (effective_fps={eff_fps})"
        )

    if xlr_h1_handle_audio not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid xlr_h1_handle_audio={xlr_h1_handle_audio}"
        )
    if xlr_h1_dig_analog not in P329_VALID_XLR_DIG_ANALOG_MODES:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid xlr_h1_dig_analog={xlr_h1_dig_analog}"
        )
    if xlr_h1_input_select not in P329_VALID_XLR_INPUT_SELECTS:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid xlr_h1_input_select={xlr_h1_input_select}"
        )
    if mic_35mm_inserted and expect_shoe_audio_active_with_35mm_mic:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            "3.5mm MIC insertion overrides MI shoe, forcing 2ch analog and graying out [Shoe Audio Set.]"
        )
    if xlr_h1_attached and xlr_h1_handle_audio == "OFF" and expect_xlr_h1_audio_active_when_handle_off:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            "XLR-H1 HANDLE AUDIO=OFF falls back to built-in stereo microphone"
        )
    if (
        xlr_h1_attached
        and xlr_h1_handle_audio == "ON"
        and xlr_h1_dig_analog == "ANALOG"
        and not mic_35mm_inserted
        and shoe_audio_set != "48KHZ_16BIT_2CH"
    ):
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            f"DIGITAL/ANALOG=ANALOG caps [Shoe Audio Set.] at 48KHZ_16BIT_2CH (got {shoe_audio_set})"
        )
    if wind_noise_reduct not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: invalid wind_noise_reduct={wind_noise_reduct}"
        )
    if expect_wind_noise_applies_to_xlr_or_35mm:
        errors.append(
            f"{P329_GA_ERR_SHOE_AUDIO_4CH_ROUTING_OR_PROXY_CUTOFF}: "
            "[Wind Noise Reduct.] applies ONLY to the built-in internal stereo mic, never XLR-H1 or 3.5mm"
        )

    # [Face/Eye AF] Subject Recognition (Human/Animal ONLY + Wave-42 Bird Errata)
    if face_eye_prior_in_af not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            f"invalid face_eye_prior_in_af={face_eye_prior_in_af}"
        )
    if exposure_mode == "INTELLIGENT_AUTO" and face_eye_prior_in_af != "ON":
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            "[Face/Eye Prior. in AF] is locked ON in Intelligent Auto"
        )
    if (
        face_eye_subject not in P329_FACE_EYE_SUBJECT_VALID_TWO
        or dormant_subject_requested in P329_DORMANT_AI_SUBJECTS
        or fx3_bird_insect_car_airplane_present_claimed
    ):
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            f"FX3 Ver. 7.02 [Face/Eye Subject] ({P329_FACE_EYE_SUBJECT_RESID16_HEX}) supports ONLY Human/Animal "
            f"(Wave-42 Bird errata: dormant Bird/Animal_Bird/Insect/Car_Train/Airplane -> errno={P329_ERRNO_EOPNOTSUPP})"
        )
    elif dormant_subject_requested != "NONE":
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            f"invalid dormant_subject_requested={dormant_subject_requested}"
        )
    if (
        (face_eye_subject == "ANIMAL" and shoot_mode in ("MOVIE", "S_AND_Q") and expect_animal_eye_af_in_movie)
        or fx3_animal_eye_af_in_movie_present_claimed
    ):
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            "TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT — Animal Eye AF is Still-only "
            f"(errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if fx6_has_animal_or_bird_subject_claimed or fx6_has_persistent_face_memory_claimed:
        errors.append(
            f"{P329_GA_ERR_SUBJECT_RECOG_HUMAN_ANIMAL_ONLY_OR_STILL_ANIMAL}: "
            "ILME-FX6 Ver. 6.01 supports Human-only AF and session-based Saved Tracking Face (no Face Memory)"
        )
    if right_left_eye_select not in P329_VALID_EYE_SELECTS:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: invalid right_left_eye_select={right_left_eye_select}"
        )
    if face_eye_frame_disp not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: invalid face_eye_frame_disp={face_eye_frame_disp}"
        )
    if expect_face_eye_frame_on_clean_hdmi:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: "
            "[Face/Eye Frame Disp.] is suppressed on Clean HDMI / HDMI RAW"
        )
    if not (0 <= face_memory_count <= P329_FACE_MEMORY_MAX_SLOTS):
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: "
            f"[Face Memory] count {face_memory_count} exceeds max {P329_FACE_MEMORY_MAX_SLOTS} faces"
        )
    if regist_faces_priority not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: invalid regist_faces_priority={regist_faces_priority}"
        )
    if claimed_face_memory_wiped_by_camera_reset or claimed_face_memory_exported_in_camset:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: "
            "8-face [Face Memory] survives [Camera Settings Reset] and is excluded from CAMSET*.DAT"
        )
    if expect_regist_faces_priority_active_in_animal:
        errors.append(
            f"{P329_GA_ERR_FACE_MEMORY_8SLOT_OR_CLEAN_HDMI_FRAME}: "
            "[Regist. Faces Priority] is grayed out when [Face/Eye Subject]=Animal"
        )

    return P329CheckGroupAShoeAudioAndSubjectRecogResult(
        group_id=P329_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        audio_out_timing=audio_out_timing,
        audio_rec_level=audio_rec_level,
        shoe_audio_set=shoe_audio_set,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        wind_noise_reduct=wind_noise_reduct,
        fx3_audio_level_display_menu_present=False,
        proxy_audio_codec=P329_PROXY_AUDIO_CODEC,
        face_eye_subject=face_eye_subject,
        right_left_eye_select=right_left_eye_select,
        face_eye_frame_disp=face_eye_frame_disp,
        face_memory_count=face_memory_count,
        fx3_bird_insect_car_airplane_present=False,
        fx3_animal_eye_af_in_movie_present=False,
    )


def _is_fw_le_2_02(fw: str) -> bool:
    parts = fw.strip().lstrip("vV").split(".")
    if len(parts) != 2:
        return False
    try:
        major = int(parts[0])
        minor = int(parts[1])
    except ValueError:
        return False
    return (major, minor) <= (2, 2)


def evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    shutter_type: str = "MECHANICAL_SHUTTER",
    flash_enabled: bool = False,
    long_exposure_nr: str = "OFF",
    e_front_curtain_shut: str = "OFF",
    bulb_enabled: bool = False,
    anti_flicker_shoot: str = "OFF",
    claimed_silent_mode_auto_disables_af_illuminator: bool = False,
    claimed_silent_mode_is_single_bool_toggle: bool = False,
    exposed_target_function_items: Tuple[str, ...] = P329_TARGET_FUNCTION_EXACT_TWO_ITEMS,
    target_aperture_drive_in_af: str = "STANDARD",
    target_auto_pixel_mapping: str = "OFF",
    expect_aperture_drive_silent_in_movie: bool = False,
    cnflasha_write_on_poweroff_allowed: bool = False,
    dormant_shutter_when_pwr_off_requested: bool = False,
    fx3_shutter_when_pwr_off_present_claimed: bool = False,
    fx6_shutter_when_pwr_off_present_claimed: bool = False,
    airplane_mode: str = "ON",
    wifi_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    version_update_badge_active: bool = False,
    # BODYDATA.DAT NO-GO Firewall
    slot1_contains_tier0_dump: bool = True,
    slot1_bodydata_stage_requested: bool = False,
    software_update_trigger_requested: bool = False,
    slot1_bodydata_writes: int = 0,
    cross_model_flash_requested: bool = False,
    bodydata_in_slot2_claimed: bool = False,
    source_fw_for_update_audit: str = "7.02",
    stepping_stone_v204_v205_completed: bool = True,
    direct_v202_to_v702_flash_claimed: bool = False,
    battery_soc_pct: float = 88.0,
    fx6_update_slot_claimed: str = "SLOT_B",
    fx6_battery_only_update_claimed: bool = False,
) -> P329CheckGroupBSilentTargetAndBodydataFirewallResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P329_VALID_SHOOT_MODES:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid shoot_mode={shoot_mode}")
    if reset_action not in P329_VALID_RESET_ACTIONS:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid reset_action={reset_action}")
    if silent_mode not in P329_VALID_ON_OFF:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid silent_mode={silent_mode}")
    if audio_signals not in P329_VALID_AUDIO_SIGNAL_MODES:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid audio_signals={audio_signals}")
    if shutter_type not in P329_VALID_SHUTTER_TYPES:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid shutter_type={shutter_type}")
    if long_exposure_nr not in P329_VALID_ON_OFF or e_front_curtain_shut not in P329_VALID_ON_OFF:
        errors.append(f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid NR/e-front state")
    if anti_flicker_shoot not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: invalid anti_flicker_shoot={anti_flicker_shoot}"
        )

    if silent_mode == "ON":
        if shutter_type != "ELECTRONIC_SHUTTER":
            errors.append(
                f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: "
                "[Silent Mode]=On locks electronic shutter"
            )
        if audio_signals != "OFF":
            errors.append(
                f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: "
                "[Silent Mode]=On forces [Audio signals]=OFF"
            )
        if (
            flash_enabled
            or long_exposure_nr == "ON"
            or e_front_curtain_shut == "ON"
            or bulb_enabled
            or anti_flicker_shoot == "ON"
        ):
            errors.append(
                f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: "
                "[Silent Mode]=On hard-disables 5 functions (Flash/LongExpNR/e-Front/BULB/Anti-flicker)"
            )
    if claimed_silent_mode_auto_disables_af_illuminator or claimed_silent_mode_is_single_bool_toggle:
        errors.append(
            f"{P329_GB_ERR_SILENT_MODE_5LOCK_OR_SIGNAL_MISMATCH}: "
            f"[Silent Mode Settings] ({P329_SILENT_MODE_SETTINGS_RESID16_HEX}) is a 2-level submenu and does NOT "
            "auto-disable [AF Illuminator]"
        )

    # Exact 2-item [Target Function Settings]
    if tuple(exposed_target_function_items) != P329_TARGET_FUNCTION_EXACT_TWO_ITEMS:
        errors.append(
            f"{P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE}: "
            f"[Target Function Settings] ({P329_TARGET_FUNCTION_SETTINGS_RESID16_HEX}) has exact 2 items "
            f"{P329_TARGET_FUNCTION_EXACT_TWO_ITEMS}, got {tuple(exposed_target_function_items)}"
        )
    if target_aperture_drive_in_af not in P329_VALID_APERTURE_DRIVE_TARGET_MODES:
        errors.append(
            f"{P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE}: "
            f"invalid target_aperture_drive_in_af={target_aperture_drive_in_af}"
        )
    if target_auto_pixel_mapping not in P329_VALID_AUTO_PIXEL_MAPPING_TARGET_MODES:
        errors.append(
            f"{P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE}: "
            f"invalid target_auto_pixel_mapping={target_auto_pixel_mapping}"
        )
    if expect_aperture_drive_silent_in_movie:
        errors.append(
            f"{P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE}: "
            "[Aperture Drive in AF] -> Silent Priority applies to Still AF only"
        )
    if cnflasha_write_on_poweroff_allowed or target_auto_pixel_mapping != "OFF":
        errors.append(
            f"{P329_GB_ERR_TARGET_FUNC_NOT_2ITEMS_OR_CNFLASHA_WRITE}: "
            "[Auto Pixel Mapping] must remain OFF to block power-off curtain actuation & cnflasha writes "
            f"(errno={P329_ERRNO_EROFS})"
        )

    # Dormant [Shutter When Pwr OFF]
    if (
        dormant_shutter_when_pwr_off_requested
        or fx3_shutter_when_pwr_off_present_claimed
        or fx6_shutter_when_pwr_off_present_claimed
    ):
        errors.append(
            f"{P329_GB_ERR_DORMANT_SHUTTER_WHEN_PWR_OFF}: "
            f"[Shutter When Pwr OFF] ({P329_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX}, image_sensor_barrier) is "
            f"dormant on ILME-FX3 Ver. 7.02 and absent on shutterless ILME-FX6 (errno={P329_ERRNO_EOPNOTSUPP})"
        )

    # [Version] Zero-RF badge silencing
    if airplane_mode not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION}: invalid airplane_mode={airplane_mode}"
        )
    if airplane_mode != "ON" or wifi_enabled or wireless_rf_packets_emitted != 0 or version_update_badge_active:
        errors.append(
            f"{P329_GB_ERR_VERSION_ZERO_RF_BADGE_VIOLATION}: "
            f"Zero-RF bench requires Airplane Mode=ON, Wi-Fi=False, 0 RF packets, and silent {P329_VERSION_BADGE_RESID16_HEX} badge"
        )

    # HARD NO-GO / BLOCKED Slot-1 BODYDATA.DAT & FX6 Slot-B AC Adaptor Flash Firewall
    if (
        slot1_bodydata_stage_requested
        or software_update_trigger_requested
        or slot1_bodydata_writes > 0
        or cross_model_flash_requested
        or bodydata_in_slot2_claimed
    ):
        errors.append(
            f"{P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE}: "
            f"HARD NO-GO / BLOCKED physical {P329_BODYDATA_FILENAME} flash firewall "
            f"(errno={P329_ERRNO_EROFS}/EPERM={P329_ERRNO_EPERM}; slot1_stage={slot1_bodydata_stage_requested}, "
            f"trigger={software_update_trigger_requested}, cross_model={cross_model_flash_requested})"
        )
    stepping_required = _is_fw_le_2_02(source_fw_for_update_audit)
    if direct_v202_to_v702_flash_claimed or (stepping_required and not stepping_stone_v204_v205_completed):
        errors.append(
            f"{P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE}: "
            f"<= Ver. 2.02 bodies MUST use Ver. {P329_STEPPING_STONE_FWS} stepping-stone audit; skipping triggers "
            f"{P329_FX3_FLASH_ERROR_LED_BLINK_PATTERN} LED blink lock"
        )
    if battery_soc_pct < P329_BODYDATA_MIN_BATTERY_SOC_PCT:
        errors.append(
            f"{P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE}: "
            f"NP-FZ100 battery_soc_pct={battery_soc_pct:.1f}% < {P329_BODYDATA_MIN_BATTERY_SOC_PCT:.0f}% (3 bars) floor"
        )
    if fx6_update_slot_claimed != "SLOT_B" or fx6_battery_only_update_claimed:
        errors.append(
            f"{P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE}: "
            "ILME-FX6 Version Up mandates Slot B + AC Adaptor (never Slot A or battery-only)"
        )
    if slot1_contains_tier0_dump and slot1_bodydata_writes != 0:
        errors.append(
            f"{P329_GB_ERR_BODYDATA_FLASH_NO_GO_OR_STEPPING_STONE}: "
            "Slot-1 Tier-0 recovery vault mutated by BODYDATA write"
        )

    return P329CheckGroupBSilentTargetAndBodydataFirewallResult(
        group_id=P329_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        shutter_type=shutter_type,
        target_aperture_drive_in_af=target_aperture_drive_in_af,
        target_auto_pixel_mapping=target_auto_pixel_mapping,
        exposed_target_function_items=tuple(exposed_target_function_items),
        fx3_shutter_when_pwr_off_present=False,
        airplane_mode=airplane_mode,
        bodydata_flash_policy="HARD_NO_GO_BLOCKED_EROFS_EPERM",
        stepping_stone_fw_required=stepping_required,
        rf_packets_transmitted=PHASE329_WIRELESS_RF_PACKETS_EMITTED,
        emmc_writes_authorized=False,
        cross_model_flash_authorized=False,
    )


def evaluate_p329_check_group_c_hdmi_raw_desqueeze(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    exposed_hdmi_settings_items: Tuple[str, ...] = P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS,
    dormant_color_gamut_for_raw_requested: bool = False,
    fx3_color_gamut_for_raw_present_claimed: bool = False,
    claimed_hdmi_settings_wiped_by_camera_reset: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    recording_media: str = "SLOT_2",
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_data_sector_writes: int = 0,
    internal_co_rec_write_to_slot1_requested: bool = False,
    expect_internal_writes_during_hdmi_only: bool = False,
    hdmi_output_resolution: str = "AUTO",
    expect_4k_hdmi_with_rec_on_during_log_or_pplut: bool = False,
    hdmi_4k_setting: str = "59.94P_10BIT",
    dormant_4k_24p_8bit_requested: bool = False,
    fx3_4k_24p_8bit_present_claimed: bool = False,
    expect_24p_no_reboot: bool = False,
    hdmi_raw_output: str = "OFF",
    raw_output_setting: str = "59.94P",
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "OFF",
    allow_lcd_blanking_for_hdmi_info: bool = False,
    expect_fx3_lcd_stays_on_when_hdmi_info_on: bool = False,
    fx6_sdi_raw_allows_4k_hdmi_claimed: bool = False,
    fx6_hdmi_raw_supports_24_00p_claimed: bool = False,
    fx6_remote_if_syncs_internal_card_claimed: bool = False,
    # [De-Squeeze Display]
    desqueeze_display: str = "OFF",
    dormant_desqueeze_1_8x_requested: bool = False,
    fx3_desqueeze_1_8x_present_claimed: bool = False,
    claimed_desqueeze_wiped_by_camera_reset: bool = False,
    desqueeze_1_6x_executed_factor: float = P329_DESQUEEZE_1_6X_EXECUTED_FACTOR,
    focus_mode: str = "MF",
    focus_area: str = "WIDE",
    steadyshot_mode: str = "OFF",
    face_priority_in_multi_metering: str = "OFF",
    expect_desqueeze_active_in_still: bool = False,
    expect_desqueeze_bakes_internal_file: bool = False,
    expect_desqueeze_applied_during_bypass: bool = False,
    claimed_desqueeze_locks_out_focus_mag_or_bright_mon: bool = False,
    fx6_desqueeze_has_1_6x_or_sdi_claimed: bool = False,
) -> P329CheckGroupCHdmiRawAndDesqueezeResult:
    errors: List[str] = []
    warnings: List[str] = []

    if reset_action not in P329_VALID_RESET_ACTIONS:
        errors.append(
            f"{P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT}: invalid reset_action={reset_action}"
        )
    if tuple(exposed_hdmi_settings_items) != P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS:
        errors.append(
            f"{P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT}: "
            f"[HDMI Output Settings] must expose exact 8 items, got {tuple(exposed_hdmi_settings_items)}"
        )
    if dormant_color_gamut_for_raw_requested or fx3_color_gamut_for_raw_present_claimed:
        errors.append(
            f"{P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT}: "
            f"[Color Gamut for RAW Output] ({P329_REMOVED_COLOR_GAMUT_FOR_RAW_RESID16_HEX}) was removed in "
            f"Ver. 2.00+ (errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if claimed_hdmi_settings_wiped_by_camera_reset:
        errors.append(
            f"{P329_GC_ERR_HDMI_8ITEM_OR_REMOVED_COLOR_GAMUT}: "
            "[HDMI Output Settings] resists [Camera Settings Reset] (Initialize-only)"
        )

    if rec_media_dur_hdmi_output not in P329_VALID_REC_MEDIA_DUR_HDMI:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            f"invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output}"
        )
    if recording_media not in P329_VALID_RECORDING_MEDIA_MODES:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            f"invalid recording_media={recording_media}"
        )
    if hdmi_output_resolution not in P329_VALID_OUTPUT_RESOLUTIONS:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            f"invalid hdmi_output_resolution={hdmi_output_resolution}"
        )
    if hdmi_4k_setting not in P329_VALID_4K_10BIT_SETTINGS:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            f"invalid 10-bit hdmi_4k_setting={hdmi_4k_setting}"
        )
    if dormant_4k_24p_8bit_requested or fx3_4k_24p_8bit_present_claimed:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            f"24.00p 8bit ({P329_DORMANT_4K_24P_8BIT_RESID16_HEX}) is dormant on FX3 (10-bit only, "
            f"errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if expect_24p_no_reboot:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            "entering/exiting 24.00p triggers a mandatory camera reboot"
        )
    if hdmi_raw_output not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: invalid hdmi_raw_output={hdmi_raw_output}"
        )
    if raw_output_setting not in P329_VALID_RAW_OUTPUT_SETTINGS:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: invalid raw_output_setting={raw_output_setting}"
        )
    if hdmi_time_code_output not in P329_VALID_ON_OFF or hdmi_rec_control not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: invalid TC Output/REC Control mode"
        )
    if hdmi_4ch_audio_output not in P329_VALID_HDMI_4CH_OUTPUT_ROUTES:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: invalid hdmi_4ch_audio_output={hdmi_4ch_audio_output}"
        )
    if hdmi_info_display not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION}: invalid hdmi_info_display={hdmi_info_display}"
        )

    if shoot_mode == "S_AND_Q":
        if rec_media_dur_hdmi_output == "OFF_HDMI_ONLY" or hdmi_raw_output == "ON":
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                "S&Q mode locks [Rec. Media dur HDMI Output]=On and [RAW Output]=Off"
            )
        if hdmi_time_code_output == "ON" and hdmi_rec_control == "ON":
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                "HDMI [Time Code Output] / [REC Control] disabled in S&Q"
            )

    if hdmi_raw_output == "ON":
        if shoot_mode != "MOVIE" or log_shooting_mode == "OFF":
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                f"16-bit {P329_HDMI_RAW_RESOLUTION_WH} [RAW Output]=On requires Movie mode + [Log Shooting] != Off"
            )
        if steadyshot_mode == "ACTIVE":
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                "[RAW Output]=On disables [SteadyShot]=Active"
            )
        if hdmi_info_display == "ON":
            errors.append(
                f"{P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION}: "
                "[RAW Output]=On temporarily forces [HDMI Info. Display]=Off"
            )

    if hdmi_rec_control == "ON" and hdmi_time_code_output != "ON":
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            "[REC Control]=On requires [Time Code Output]=On"
        )

    is_pplut = picture_profile in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
    if (
        rec_media_dur_hdmi_output == "ON"
        and hdmi_raw_output == "OFF"
        and (log_shooting_mode != "OFF" or is_pplut)
        and (expect_4k_hdmi_with_rec_on_during_log_or_pplut or hdmi_output_resolution == "2160P")
    ):
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            "Log/PPLUT1..4 with [Rec. Media dur HDMI Output]=On clamps [Output Resolution] to 1080p"
        )

    # Co-recording Slot-1 Tier-0 Vault protection
    slot1_mutated = False
    if slot1_contains_tier0_dump:
        if slot1_data_sector_writes != 0 or internal_co_rec_write_to_slot1_requested:
            slot1_mutated = True
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                f"RAW/XAVC co-recording must NOT touch Slot-1 Tier-0 Vault (errno={P329_ERRNO_EROFS})"
            )
        if rec_media_dur_hdmi_output == "ON" and (
            recording_media != "SLOT_2" or not slot1_wp_locked
        ):
            errors.append(
                f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
                f"[Rec. Media dur HDMI Output]=On co-records internal XAVC+Proxy -> requires Recording Media=SLOT_2 "
                f"and Slot-1 WP lock (errno={P329_ERRNO_EROFS})"
            )
    if rec_media_dur_hdmi_output == "OFF_HDMI_ONLY" and expect_internal_writes_during_hdmi_only:
        errors.append(
            f"{P329_GC_ERR_HDMI_RAW_16BIT_COREC_SLOT1_VAULT_OR_10BIT_CLAMP}: "
            "[Rec. Media dur HDMI Output]=Off(HDMI Only) yields 0 internal card writes"
        )

    if hdmi_info_display == "ON":
        if expect_fx3_lcd_stays_on_when_hdmi_info_on:
            errors.append(
                f"{P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION}: "
                "[HDMI Info. Display]=On blanks FX3 built-in LCD"
            )
        if not allow_lcd_blanking_for_hdmi_info:
            errors.append(
                f"{P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION}: "
                "[HDMI Info. Display]=On blanks FX3 LCD; pass allow_lcd_blanking_for_hdmi_info=True if intentional"
            )

    if (
        fx6_sdi_raw_allows_4k_hdmi_claimed
        or fx6_hdmi_raw_supports_24_00p_claimed
        or fx6_remote_if_syncs_internal_card_claimed
    ):
        errors.append(
            f"{P329_GC_ERR_HDMI_INFO_LCD_BLANK_OR_FX6_SDI_RAW_CONFUSION}: "
            f"ILME-FX6 12G-SDI RAW caps HDMI <= 1080p, RAW(HDMI) {P329_FX6_HDMI_RAW_RESOLUTION_WH} excludes 24Hz, "
            "and SDI/HDMI Remote I/F is cardless vs Parallel Rec"
        )

    # [De-Squeeze Display]
    if (
        desqueeze_display == "1.8X"
        or dormant_desqueeze_1_8x_requested
        or fx3_desqueeze_1_8x_present_claimed
    ):
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS}: "
            f"1.8x De-Squeeze is absent on ILME-FX3 Ver. 7.02 (only {P329_DESQUEEZE_EXACT_FIVE_STATES}, "
            f"errno={P329_ERRNO_EOPNOTSUPP})"
        )
    elif desqueeze_display not in P329_DESQUEEZE_EXACT_FIVE_STATES:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS}: "
            f"invalid desqueeze_display={desqueeze_display}"
        )
    if claimed_desqueeze_wiped_by_camera_reset:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS}: "
            "[De-Squeeze Display] resists [Camera Settings Reset] (Initialize-only)"
        )
    if desqueeze_display == "1.6X" and abs(desqueeze_1_6x_executed_factor - P329_DESQUEEZE_1_6X_EXECUTED_FACTOR) > 1e-6:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS}: "
            f"[De-Squeeze Display]=1.6x executes 1.65x (_f {P329_DESQUEEZE_1_65X_DESC_RESID16_HEX}), "
            f"got {desqueeze_1_6x_executed_factor}"
        )

    if focus_mode not in P329_VALID_FOCUS_MODES or focus_area not in P329_VALID_FOCUS_AREAS:
        errors.append(f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: invalid focus_mode/focus_area")
    if steadyshot_mode not in P329_VALID_STEADYSHOT_MODES:
        errors.append(f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: invalid steadyshot_mode={steadyshot_mode}")
    if face_priority_in_multi_metering not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: invalid face_priority_in_multi_metering"
        )

    four_locks_ok = True
    if expect_desqueeze_active_in_still or (shoot_mode == "PHOTO" and desqueeze_display != "OFF"):
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: "
            "[De-Squeeze Display] is Movie/S&Q only (grayed in Still)"
        )
    if desqueeze_display != "OFF" and desqueeze_display in P329_DESQUEEZE_EXACT_FIVE_STATES:
        if (
            focus_mode != "MF"
            or focus_area != "WIDE"
            or steadyshot_mode != "OFF"
            or face_priority_in_multi_metering != "OFF"
        ):
            four_locks_ok = False
            errors.append(
                f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: "
                "[De-Squeeze Display] != Off requires 4 lockouts: "
                f"{P329_DESQUEEZE_FOUR_LOCKOUTS}"
            )
    if expect_desqueeze_bakes_internal_file or expect_desqueeze_applied_during_bypass:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: "
            "[De-Squeeze Display] never alters internal files and auto-bypasses across all 6 documented conditions"
        )
    if claimed_desqueeze_locks_out_focus_mag_or_bright_mon:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_4LOCKS_OR_6BYPASS_VIOLATION}: "
            "[De-Squeeze Display] coexists with [Focus Magnifier] and [Bright Monitoring]"
        )
    if fx6_desqueeze_has_1_6x_or_sdi_claimed:
        errors.append(
            f"{P329_GC_ERR_DESQUEEZE_RATIO_NO_1_8X_OR_1_65X_SEMANTICS}: "
            "ILME-FX6 De-Squeeze is VF/HDMI-only (never SDI) with 1.3x/1.5x/2.0x only (no 1.6x)"
        )

    exec_factor = (
        P329_DESQUEEZE_1_6X_EXECUTED_FACTOR
        if desqueeze_display == "1.6X"
        else (1.3 if desqueeze_display == "1.3X" else (1.5 if desqueeze_display == "1.5X" else (2.0 if desqueeze_display == "2.0X" else 1.0)))
    )

    return P329CheckGroupCHdmiRawAndDesqueezeResult(
        group_id=P329_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        exposed_hdmi_settings_items=tuple(exposed_hdmi_settings_items),
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_raw_resolution_wh=P329_HDMI_RAW_RESOLUTION_WH,
        hdmi_raw_bit_depth=P329_HDMI_RAW_BIT_DEPTH,
        hdmi_output_resolution=hdmi_output_resolution,
        hdmi_4k_setting=hdmi_4k_setting,
        hdmi_info_display=hdmi_info_display,
        fx3_color_gamut_for_raw_output_menu_present=False,
        fx3_4k_24p_8bit_present=False,
        slot1_tier0_vault_mutated=slot1_mutated,
        desqueeze_display=desqueeze_display,
        desqueeze_executed_factor=exec_factor,
        fx3_desqueeze_1_8x_present=False,
        desqueeze_four_lockouts_enforced=four_locks_ok,
    )


def _read_single_tier0_receipt_file(path: Path) -> Tuple[Optional[Tuple[bytes, int]], List[str]]:
    errors: List[str] = []
    if path.is_symlink():
        errors.append(f"Tier-0 receipt path is a symlink (forbidden): {path}")
        return None, errors
    if not path.is_file():
        errors.append(f"Tier-0 receipt file missing: {path}")
        return None, errors
    st = os.lstat(path)
    fd = os.open(str(path), os.O_RDONLY)
    try:
        raw = os.read(fd, SD_RECEIPT_BYTES + 64)
    finally:
        os.close(fd)
    if len(raw) != SD_RECEIPT_BYTES:
        errors.append(f"Tier-0 receipt {path} length {len(raw)} != {SD_RECEIPT_BYTES} bytes")
        return None, errors
    return (raw, int(st.st_dev)), errors


def evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    shoot_mode: str = "MOVIE",
    silent_mode: str = "OFF",
    shutter_type: str = "MECHANICAL_SHUTTER",
    bulb_enabled: bool = False,
    # Wave 63 §§3-4
    rec_lamp_mode: str = "ONLY_FRONT_OFF",
    dormant_tally_light_menu_requested: bool = False,
    fx3_tally_light_menu_present_claimed: bool = False,
    dormant_rec_lamp_only_one_requested: bool = False,
    claimed_rec_lamp_wiped_by_camera_reset: bool = False,
    expect_top_rec_ring_off_with_rear_on: bool = False,
    claimed_silent_mode_turns_off_rec_lamp: bool = False,
    emphasized_rec_display: str = "ON",
    claimed_emph_rec_resists_camera_reset: bool = False,
    expect_emph_rec_on_clean_hdmi: bool = False,
    remain_shoot_display: str = "NOT_DISPLAYED",
    claimed_remain_shoot_wiped_by_camera_reset: bool = False,
    expect_remain_shoot_shows_movie_time: bool = False,
    auto_review: str = "OFF",
    interval_shooting_active: bool = False,
    expect_auto_review_in_interval: bool = False,
    claimed_auto_review_wiped_by_camera_reset: bool = False,
    anti_flicker_shoot: str = "OFF",
    dormant_var_shutter_requested: bool = False,
    fx3_var_shutter_present_claimed: bool = False,
    fx6_ecs_freq_hz: float = 23.99,
    fx3_has_ecs_mode_claimed: bool = False,
    apsc_s35_shooting: str = "AUTO",
    movie_file_format: str = "XAVC_S_I_4K",
    hdmi_raw_output: str = "OFF",
    hdmi_4k_only_active: bool = False,
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    still_image_size: str = "L_12M",
    expect_apsc_4k_or_raw: bool = False,
    claimed_apsc_wiped_by_camera_reset: bool = False,
    claimed_apsc_still_size_4_2m: bool = False,
    # Hardware & Tier-0 Gate
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    slot1_data_sector_writes: int = 0,
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
) -> P329CheckGroupDRecLampVarShutterApscAndTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    # [REC Lamp] & dormant [Tally Light]
    if rec_lamp_mode not in P329_REC_LAMP_THREE_STATES:
        errors.append(
            f"{P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT}: invalid rec_lamp_mode={rec_lamp_mode}"
        )
    if (
        dormant_tally_light_menu_requested
        or fx3_tally_light_menu_present_claimed
        or dormant_rec_lamp_only_one_requested
    ):
        errors.append(
            f"{P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT}: "
            f"[Tally Light] and dormant _f {P329_DORMANT_REC_LAMP_ONLY_ONE_RESID16_HEX} are absent on FX3 Ver. 7.02 "
            f"(use [REC Lamp] {P329_REC_LAMP_RESID16_HEX}, errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if claimed_rec_lamp_wiped_by_camera_reset:
        errors.append(
            f"{P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT}: "
            "[REC Lamp] resists [Camera Settings Reset] (Initialize-only)"
        )
    if expect_top_rec_ring_off_with_rear_on:
        errors.append(
            f"{P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT}: "
            "FX3 rear LED and top REC key ring are hardware-coupled (cannot turn off top ring alone)"
        )
    if claimed_silent_mode_turns_off_rec_lamp:
        errors.append(
            f"{P329_GD_ERR_REC_LAMP_OR_DORMANT_TALLY_LIGHT}: "
            "[REC Lamp] is independent of [Silent Mode]"
        )

    # [Emphasized REC Display], [Remain Shoot Display], [Auto Review]
    if emphasized_rec_display not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: invalid emphasized_rec_display={emphasized_rec_display}"
        )
    if claimed_emph_rec_resists_camera_reset or expect_emph_rec_on_clean_hdmi:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: "
            f"[Emphasized REC Display] ({P329_EMPH_REC_DISP_RESID16_HEX}) IS resettable and never output on Clean HDMI"
        )
    if remain_shoot_display not in P329_VALID_REMAIN_SHOOT_MODES:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: invalid remain_shoot_display={remain_shoot_display}"
        )
    if claimed_remain_shoot_wiped_by_camera_reset or expect_remain_shoot_shows_movie_time:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: "
            f"[Remain Shoot Display] ({P329_REMAIN_SHOOT_DISP_RESID16_HEX}) is active (Still buffer) and Initialize-only"
        )
    if auto_review not in P329_VALID_AUTO_REVIEW_MODES:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: invalid auto_review={auto_review}"
        )
    if claimed_auto_review_wiped_by_camera_reset or expect_auto_review_in_interval:
        errors.append(
            f"{P329_GD_ERR_EMPH_REC_REMAIN_SHOOT_OR_AUTO_REVIEW}: "
            "[Auto Review] is Still-only, disabled in Interval Shooting, and Initialize-only"
        )

    # Dormant [Var. Shutter] vs Still mech [Anti-flicker Shoot.] vs FX6 ECS
    if dormant_var_shutter_requested or fx3_var_shutter_present_claimed or fx3_has_ecs_mode_claimed:
        errors.append(
            f"{P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT}: "
            f"[Var. Shutter] (high_res_ss, {P329_DORMANT_VAR_SHUTTER_RESIDS}) is dormant on ILME-FX3 Ver. 7.02 "
            f"(errno={P329_ERRNO_EOPNOTSUPP})"
        )
    if anti_flicker_shoot not in P329_VALID_ON_OFF:
        errors.append(
            f"{P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT}: invalid anti_flicker_shoot={anti_flicker_shoot}"
        )
    if anti_flicker_shoot == "ON" and (
        shoot_mode != "PHOTO"
        or shutter_type == "ELECTRONIC_SHUTTER"
        or bulb_enabled
        or silent_mode == "ON"
    ):
        errors.append(
            f"{P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT}: "
            f"[Anti-flicker Shoot.] ({P329_ANTI_FLICKER_SHOOT_RESID16_HEX}) is Still mechanical-shutter 100/120Hz only"
        )
    if not (P329_FX6_ECS_MIN_HZ <= fx6_ecs_freq_hz <= P329_FX6_ECS_MAX_HZ):
        errors.append(
            f"{P329_GD_ERR_DORMANT_VAR_SHUTTER_OR_ANTIFLICKER_LOCKOUT}: "
            f"FX6 ECS frequency {fx6_ecs_freq_hz} Hz out of range {P329_FX6_ECS_MIN_HZ}..{P329_FX6_ECS_MAX_HZ} Hz"
        )

    # Wave-42 Reset Errata on [APS-C S35 Shooting]
    if apsc_s35_shooting not in P329_VALID_APSC_S35_MODES:
        errors.append(
            f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: invalid apsc_s35_shooting={apsc_s35_shooting}"
        )
    if claimed_apsc_wiped_by_camera_reset:
        errors.append(
            f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
            "Wave-42 errata: [APS-C S35 Shooting] is Initialize-only (NOT resettable by [Camera Settings Reset])"
        )
    if claimed_apsc_still_size_4_2m or still_image_size == "M_4_2M":
        errors.append(
            f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
            "APS-C Still size drops from L:12M to M:5.1M (2768x1848 3:2 / 4.3M 16:9, NOT 4.2M)"
        )
    if expect_apsc_4k_or_raw:
        errors.append(
            f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
            "APS-C S35 locks out ALL 4K/DCI 4K/HDMI 4K/RAW formats"
        )
    if apsc_s35_shooting == "ON":
        if (
            movie_file_format in P329_APSC_LOCKED_OUT_4K_FORMATS
            or hdmi_raw_output == "ON"
            or hdmi_4k_only_active
        ):
            errors.append(
                f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
                f"APS-C S35=ON locks out 4K/RAW ({movie_file_format}, raw={hdmi_raw_output}, "
                f"hdmi_4k_only={hdmi_4k_only_active}, errno={P329_ERRNO_EOPNOTSUPP})"
            )
        eff_fps = sq_fps if (shoot_mode == "S_AND_Q" or sq_enabled) else rec_fps
        if eff_fps > 120.0:
            errors.append(
                f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
                f"APS-C S35=ON HD format capped at <= 120p (200/240fps gated, got {eff_fps}p)"
            )
        if shoot_mode == "PHOTO" and still_image_size == "L_12M":
            errors.append(
                f"{P329_GD_ERR_APSC_S35_4K_LOCKOUT_5_1M_OR_RESET_ERRATA}: "
                f"APS-C S35=ON disables Still L:12M and drops to {P329_APSC_STILL_MAX_SIZE_LABEL} (not 4.2M)"
            )

    # Zero-emission hardware redlines
    if (
        e_nd_actuator_tx_count != 0
        or wireless_rf_packets_emitted != 0
        or slot1_data_sector_writes != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
        or claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P329_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: "
            "Hardware safety redline violated (live_attach/emmc_writes/cross_model_flash must be False, "
            "all TX/write counters must be 0)"
        )

    # 16/16 H0 == H3 Surface Invariant
    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = h0_baselines_a
    eff_h0_b = h0_baselines_b
    eff_h3 = h3_baselines

    sim_bundle: Optional[Dict[str, Any]] = None
    if (
        simulate_bench_dry_run
        and receipt_a_path is None
        and receipt_b_path is None
        and receipt_a_bytes is None
        and receipt_b_bytes is None
    ):
        sim_bundle = build_simulated_phase329_tier0_receipts()
        if eff_serial is None:
            eff_serial = sim_bundle["body_serial"]
        if eff_cid is None:
            eff_cid = sim_bundle["emmc_cid"]
        if eff_h0_a is None:
            eff_h0_a = sim_bundle["h0_baselines_a"]
        if eff_h0_b is None:
            eff_h0_b = sim_bundle["h0_baselines_b"]
        if eff_h3 is None:
            eff_h3 = sim_bundle["h3_baselines"]

    drifted = max(0, int(simulated_h0_h3_drifted_surfaces))
    if eff_h0_a is not None and eff_h3 is not None:
        key_mismatches = sum(
            1
            for key in REQUIRED_H0_BASELINE_KEYS
            if _is_trivial_hex64(eff_h0_a.get(key, ""))
            or eff_h0_a.get(key, "").lower() != eff_h3.get(key, "").lower()
        )
        surface_mismatches = sum(
            1
            for surf in SIXTEEN_STORAGE_SURFACES
            if eff_h0_a.get(surf) != eff_h3.get(surf)
        )
        extra_keys = set(eff_h0_a.keys()) | set(eff_h3.keys())
        extra_mismatches = sum(
            1
            for k in extra_keys
            if (k in eff_h0_a) != (k in eff_h3)
            or str(eff_h0_a.get(k, "")).lower() != str(eff_h3.get(k, "")).lower()
        )
        drifted = max(drifted, key_mismatches, surface_mismatches, extra_mismatches)
    h0_eq_h3_count = max(0, surface_count - drifted)

    if drifted != 0 or h0_eq_h3_count != surface_count:
        errors.append(
            f"{P329_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: "
            f"16/16 H0 == H3 invariant broken ({h0_eq_h3_count}/{surface_count})"
        )

    # Tier-0 Dual-Media 528B FX3RCPT1 Verification
    tier0_verified = False
    receipt_mode = "AWAITING_PHYSICAL_TIER0_RECEIPTS"

    if sim_bundle is not None:
        tier0_verified = True
        receipt_mode = "DRY_RUN_SIMULATED"
    elif (
        receipt_a_path is not None
        or receipt_b_path is not None
        or receipt_a_bytes is not None
        or receipt_b_bytes is not None
    ):
        raw_a = receipt_a_bytes
        raw_b = receipt_b_bytes
        dev_a = st_dev_a_override
        dev_b = st_dev_b_override
        read_errs: List[str] = []

        if raw_a is None and receipt_a_path is not None:
            res_a, err_a = _read_single_tier0_receipt_file(Path(receipt_a_path))
            if err_a or res_a is None:
                read_errs.extend(err_a)
            else:
                raw_a, st_a = res_a
                if dev_a is None:
                    dev_a = st_a
        if raw_b is None and receipt_b_path is not None:
            res_b, err_b = _read_single_tier0_receipt_file(Path(receipt_b_path))
            if err_b or res_b is None:
                read_errs.extend(err_b)
            else:
                raw_b, st_b = res_b
                if dev_b is None:
                    dev_b = st_b

        if read_errs:
            errors.extend(
                f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {msg}"
                for msg in read_errs
            )
            receipt_mode = "INVALID_RECEIPT_PARSE_OR_IDENTITY"
        elif raw_a is None or raw_b is None:
            errors.append(
                f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                "both Copy A and Copy B 528B FX3RCPT1 receipts are required"
            )
            receipt_mode = "INVALID_RECEIPT_SINGLE_COPY"
        else:
            if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "dual 528B FX3RCPT1 size/byte mismatch"
                )
            if dev_a is None or dev_b is None or int(dev_a) == int(dev_b):
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"dual-media receipts must reside on distinct physical devices (st_dev {dev_a} vs {dev_b})"
                )
            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid 128-bit emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"receipt target model/fw mismatch ({hex(body_model_id)} / {body_fw})"
                )
            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    errors.append(
                        f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                        f"FX3RCPT1 integrity/header check failed ({parsed_a.errors or parsed_b.errors})"
                    )
            except Exception as exc:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
                )
            if eff_h0_a is None or eff_h0_b is None:
                errors.append(
                    f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "h0_baselines_a and h0_baselines_b required with physical receipts"
                )
            else:
                for key in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(key, "")
                    vb = eff_h0_b.get(key, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        errors.append(
                            f"{P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                            f"H0 baseline invalid or mismatched for {key}"
                        )
                        break
            if not any(e.startswith(P329_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID) for e in errors):
                tier0_verified = True
                receipt_mode = "PHYSICAL_DUAL_MEDIA_528B"
            else:
                receipt_mode = "INVALID_RECEIPT_REJECTED"
    else:
        warnings.append("No physical 528B FX3RCPT1 Tier-0 receipts provided; status fail-closed offline")

    return P329CheckGroupDRecLampVarShutterApscAndTier0Result(
        group_id=P329_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        rec_lamp_mode=rec_lamp_mode,
        fx3_tally_light_menu_present=False,
        emphasized_rec_display=emphasized_rec_display,
        remain_shoot_display=remain_shoot_display,
        auto_review=auto_review,
        anti_flicker_shoot=anti_flicker_shoot,
        fx3_var_shutter_present=False,
        fx6_ecs_freq_hz=fx6_ecs_freq_hz,
        apsc_s35_shooting=apsc_s35_shooting,
        fx3_apsc_resets_via_camera_settings_reset=False,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3_count,
        h0_h3_surface_count=surface_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        usb_packets_transmitted=usb_packets_transmitted,
        passive_tx_bytes_emitted=simulated_passive_tx_bytes,
        raw_firmware_bytes_leaked=PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
    )


def build_simulated_phase329_tier0_receipts(
    *,
    body_serial: str = "FX3702SIM329",
    emmc_cid: str = "150100424a4e42345201020304050607",
) -> Dict[str, Any]:
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE329_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE329_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "receipt_a_bytes": receipt_bytes,
        "receipt_b_bytes": bytes(receipt_bytes),
        "st_dev_a_override": 101,
        "st_dev_b_override": 202,
        "h0_baselines_a": dict(h0),
        "h0_baselines_b": dict(h0),
        "h3_baselines": dict(h0),
    }


def evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P329_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Group A
    audio_recording: str = "ON",
    audio_out_timing: str = "LIVE",
    claimed_audio_out_timing_under_setup_sound_option: bool = False,
    audio_out_timing_active_in_sq_claimed: bool = False,
    audio_recording_in_sq_claimed: bool = False,
    claimed_audio_out_timing_resists_reset: bool = False,
    dormant_audio_level_display_requested: bool = False,
    fx3_audio_level_display_menu_present_claimed: bool = False,
    audio_rec_level: int = P329_AUDIO_REC_LEVEL_DEFAULT,
    fx3_disable_builtin_limiter_requested: bool = False,
    fx3_limiter_6step_present_claimed: bool = False,
    fx3_32bit_float_audio_claimed: bool = False,
    four_ch_audio_monitoring: str = "CH1_CH2",
    shoe_audio_set: str = "48KHZ_24BIT_4CH",
    movie_file_format: str = "XAVC_S_I_4K",
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    proxy_recording: str = "OFF",
    claimed_shoe_4ch_unsupported_on_xavc_codec: bool = False,
    expect_proxy_4ch_24bit_audio: bool = False,
    expect_proxy_active_at_100p_plus: bool = False,
    mic_35mm_inserted: bool = False,
    expect_shoe_audio_active_with_35mm_mic: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "ON",
    xlr_h1_dig_analog: str = "DIGITAL",
    xlr_h1_input_select: str = "IN1_IN2",
    expect_xlr_h1_audio_active_when_handle_off: bool = False,
    wind_noise_reduct: str = "OFF",
    expect_wind_noise_applies_to_xlr_or_35mm: bool = False,
    face_eye_prior_in_af: str = "ON",
    face_eye_subject: str = "HUMAN",
    dormant_subject_requested: str = "NONE",
    fx3_bird_insect_car_airplane_present_claimed: bool = False,
    fx3_animal_eye_af_in_movie_present_claimed: bool = False,
    expect_animal_eye_af_in_movie: bool = False,
    right_left_eye_select: str = "AUTO",
    face_eye_frame_disp: str = "OFF",
    expect_face_eye_frame_on_clean_hdmi: bool = False,
    face_memory_count: int = 0,
    regist_faces_priority: str = "ON",
    claimed_face_memory_wiped_by_camera_reset: bool = False,
    claimed_face_memory_exported_in_camset: bool = False,
    expect_regist_faces_priority_active_in_animal: bool = False,
    fx6_has_animal_or_bird_subject_claimed: bool = False,
    fx6_has_persistent_face_memory_claimed: bool = False,
    # Group B
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    shutter_type: str = "MECHANICAL_SHUTTER",
    flash_enabled: bool = False,
    long_exposure_nr: str = "OFF",
    e_front_curtain_shut: str = "OFF",
    bulb_enabled: bool = False,
    anti_flicker_shoot: str = "OFF",
    claimed_silent_mode_auto_disables_af_illuminator: bool = False,
    claimed_silent_mode_is_single_bool_toggle: bool = False,
    exposed_target_function_items: Tuple[str, ...] = P329_TARGET_FUNCTION_EXACT_TWO_ITEMS,
    target_aperture_drive_in_af: str = "STANDARD",
    target_auto_pixel_mapping: str = "OFF",
    expect_aperture_drive_silent_in_movie: bool = False,
    cnflasha_write_on_poweroff_allowed: bool = False,
    dormant_shutter_when_pwr_off_requested: bool = False,
    fx3_shutter_when_pwr_off_present_claimed: bool = False,
    fx6_shutter_when_pwr_off_present_claimed: bool = False,
    airplane_mode: str = "ON",
    wifi_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    version_update_badge_active: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_bodydata_stage_requested: bool = False,
    software_update_trigger_requested: bool = False,
    slot1_bodydata_writes: int = 0,
    cross_model_flash_requested: bool = False,
    bodydata_in_slot2_claimed: bool = False,
    source_fw_for_update_audit: str = "7.02",
    stepping_stone_v204_v205_completed: bool = True,
    direct_v202_to_v702_flash_claimed: bool = False,
    battery_soc_pct: float = 88.0,
    fx6_update_slot_claimed: str = "SLOT_B",
    fx6_battery_only_update_claimed: bool = False,
    # Group C
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    exposed_hdmi_settings_items: Tuple[str, ...] = P329_HDMI_SETTINGS_EXACT_EIGHT_ITEMS,
    dormant_color_gamut_for_raw_requested: bool = False,
    fx3_color_gamut_for_raw_present_claimed: bool = False,
    claimed_hdmi_settings_wiped_by_camera_reset: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    recording_media: str = "SLOT_2",
    slot1_wp_locked: bool = True,
    slot1_data_sector_writes: int = 0,
    internal_co_rec_write_to_slot1_requested: bool = False,
    expect_internal_writes_during_hdmi_only: bool = False,
    hdmi_output_resolution: str = "AUTO",
    expect_4k_hdmi_with_rec_on_during_log_or_pplut: bool = False,
    hdmi_4k_setting: str = "59.94P_10BIT",
    dormant_4k_24p_8bit_requested: bool = False,
    fx3_4k_24p_8bit_present_claimed: bool = False,
    expect_24p_no_reboot: bool = False,
    hdmi_raw_output: str = "OFF",
    raw_output_setting: str = "59.94P",
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "OFF",
    allow_lcd_blanking_for_hdmi_info: bool = False,
    expect_fx3_lcd_stays_on_when_hdmi_info_on: bool = False,
    fx6_sdi_raw_allows_4k_hdmi_claimed: bool = False,
    fx6_hdmi_raw_supports_24_00p_claimed: bool = False,
    fx6_remote_if_syncs_internal_card_claimed: bool = False,
    desqueeze_display: str = "OFF",
    dormant_desqueeze_1_8x_requested: bool = False,
    fx3_desqueeze_1_8x_present_claimed: bool = False,
    claimed_desqueeze_wiped_by_camera_reset: bool = False,
    desqueeze_1_6x_executed_factor: float = P329_DESQUEEZE_1_6X_EXECUTED_FACTOR,
    focus_mode: str = "MF",
    focus_area: str = "WIDE",
    steadyshot_mode: str = "OFF",
    face_priority_in_multi_metering: str = "OFF",
    expect_desqueeze_active_in_still: bool = False,
    expect_desqueeze_bakes_internal_file: bool = False,
    expect_desqueeze_applied_during_bypass: bool = False,
    claimed_desqueeze_locks_out_focus_mag_or_bright_mon: bool = False,
    fx6_desqueeze_has_1_6x_or_sdi_claimed: bool = False,
    # Group D
    rec_lamp_mode: str = "ONLY_FRONT_OFF",
    dormant_tally_light_menu_requested: bool = False,
    fx3_tally_light_menu_present_claimed: bool = False,
    dormant_rec_lamp_only_one_requested: bool = False,
    claimed_rec_lamp_wiped_by_camera_reset: bool = False,
    expect_top_rec_ring_off_with_rear_on: bool = False,
    claimed_silent_mode_turns_off_rec_lamp: bool = False,
    emphasized_rec_display: str = "ON",
    claimed_emph_rec_resists_camera_reset: bool = False,
    expect_emph_rec_on_clean_hdmi: bool = False,
    remain_shoot_display: str = "NOT_DISPLAYED",
    claimed_remain_shoot_wiped_by_camera_reset: bool = False,
    expect_remain_shoot_shows_movie_time: bool = False,
    auto_review: str = "OFF",
    interval_shooting_active: bool = False,
    expect_auto_review_in_interval: bool = False,
    claimed_auto_review_wiped_by_camera_reset: bool = False,
    dormant_var_shutter_requested: bool = False,
    fx3_var_shutter_present_claimed: bool = False,
    fx6_ecs_freq_hz: float = 23.99,
    fx3_has_ecs_mode_claimed: bool = False,
    apsc_s35_shooting: str = "AUTO",
    hdmi_4k_only_active: bool = False,
    still_image_size: str = "L_12M",
    expect_apsc_4k_or_raw: bool = False,
    claimed_apsc_wiped_by_camera_reset: bool = False,
    claimed_apsc_still_size_4_2m: bool = False,
    e_nd_actuator_tx_count: int = 0,
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
) -> RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport:
    donor = inspect_phase329_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p329_check_group_a_shoe_audio_and_subject_recog(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        audio_recording=audio_recording,
        audio_out_timing=audio_out_timing,
        claimed_audio_out_timing_under_setup_sound_option=claimed_audio_out_timing_under_setup_sound_option,
        audio_out_timing_active_in_sq_claimed=audio_out_timing_active_in_sq_claimed,
        audio_recording_in_sq_claimed=audio_recording_in_sq_claimed,
        claimed_audio_out_timing_resists_reset=claimed_audio_out_timing_resists_reset,
        dormant_audio_level_display_requested=dormant_audio_level_display_requested,
        fx3_audio_level_display_menu_present_claimed=fx3_audio_level_display_menu_present_claimed,
        audio_rec_level=audio_rec_level,
        fx3_disable_builtin_limiter_requested=fx3_disable_builtin_limiter_requested,
        fx3_limiter_6step_present_claimed=fx3_limiter_6step_present_claimed,
        fx3_32bit_float_audio_claimed=fx3_32bit_float_audio_claimed,
        four_ch_audio_monitoring=four_ch_audio_monitoring,
        shoe_audio_set=shoe_audio_set,
        movie_file_format=movie_file_format,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        proxy_recording=proxy_recording,
        claimed_shoe_4ch_unsupported_on_xavc_codec=claimed_shoe_4ch_unsupported_on_xavc_codec,
        expect_proxy_4ch_24bit_audio=expect_proxy_4ch_24bit_audio,
        expect_proxy_active_at_100p_plus=expect_proxy_active_at_100p_plus,
        mic_35mm_inserted=mic_35mm_inserted,
        expect_shoe_audio_active_with_35mm_mic=expect_shoe_audio_active_with_35mm_mic,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        xlr_h1_dig_analog=xlr_h1_dig_analog,
        xlr_h1_input_select=xlr_h1_input_select,
        expect_xlr_h1_audio_active_when_handle_off=expect_xlr_h1_audio_active_when_handle_off,
        wind_noise_reduct=wind_noise_reduct,
        expect_wind_noise_applies_to_xlr_or_35mm=expect_wind_noise_applies_to_xlr_or_35mm,
        face_eye_prior_in_af=face_eye_prior_in_af,
        face_eye_subject=face_eye_subject,
        dormant_subject_requested=dormant_subject_requested,
        fx3_bird_insect_car_airplane_present_claimed=fx3_bird_insect_car_airplane_present_claimed,
        fx3_animal_eye_af_in_movie_present_claimed=fx3_animal_eye_af_in_movie_present_claimed,
        expect_animal_eye_af_in_movie=expect_animal_eye_af_in_movie,
        right_left_eye_select=right_left_eye_select,
        face_eye_frame_disp=face_eye_frame_disp,
        expect_face_eye_frame_on_clean_hdmi=expect_face_eye_frame_on_clean_hdmi,
        face_memory_count=face_memory_count,
        regist_faces_priority=regist_faces_priority,
        claimed_face_memory_wiped_by_camera_reset=claimed_face_memory_wiped_by_camera_reset,
        claimed_face_memory_exported_in_camset=claimed_face_memory_exported_in_camset,
        expect_regist_faces_priority_active_in_animal=expect_regist_faces_priority_active_in_animal,
        fx6_has_animal_or_bird_subject_claimed=fx6_has_animal_or_bird_subject_claimed,
        fx6_has_persistent_face_memory_claimed=fx6_has_persistent_face_memory_claimed,
    )
    gb = evaluate_p329_check_group_b_silent_target_and_bodydata_firewall(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        shutter_type=shutter_type,
        flash_enabled=flash_enabled,
        long_exposure_nr=long_exposure_nr,
        e_front_curtain_shut=e_front_curtain_shut,
        bulb_enabled=bulb_enabled,
        anti_flicker_shoot=anti_flicker_shoot,
        claimed_silent_mode_auto_disables_af_illuminator=claimed_silent_mode_auto_disables_af_illuminator,
        claimed_silent_mode_is_single_bool_toggle=claimed_silent_mode_is_single_bool_toggle,
        exposed_target_function_items=exposed_target_function_items,
        target_aperture_drive_in_af=target_aperture_drive_in_af,
        target_auto_pixel_mapping=target_auto_pixel_mapping,
        expect_aperture_drive_silent_in_movie=expect_aperture_drive_silent_in_movie,
        cnflasha_write_on_poweroff_allowed=cnflasha_write_on_poweroff_allowed,
        dormant_shutter_when_pwr_off_requested=dormant_shutter_when_pwr_off_requested,
        fx3_shutter_when_pwr_off_present_claimed=fx3_shutter_when_pwr_off_present_claimed,
        fx6_shutter_when_pwr_off_present_claimed=fx6_shutter_when_pwr_off_present_claimed,
        airplane_mode=airplane_mode,
        wifi_enabled=wifi_enabled,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        version_update_badge_active=version_update_badge_active,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_bodydata_stage_requested=slot1_bodydata_stage_requested,
        software_update_trigger_requested=software_update_trigger_requested,
        slot1_bodydata_writes=slot1_bodydata_writes,
        cross_model_flash_requested=cross_model_flash_requested,
        bodydata_in_slot2_claimed=bodydata_in_slot2_claimed,
        source_fw_for_update_audit=source_fw_for_update_audit,
        stepping_stone_v204_v205_completed=stepping_stone_v204_v205_completed,
        direct_v202_to_v702_flash_claimed=direct_v202_to_v702_flash_claimed,
        battery_soc_pct=battery_soc_pct,
        fx6_update_slot_claimed=fx6_update_slot_claimed,
        fx6_battery_only_update_claimed=fx6_battery_only_update_claimed,
    )
    gc = evaluate_p329_check_group_c_hdmi_raw_desqueeze(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        exposed_hdmi_settings_items=exposed_hdmi_settings_items,
        dormant_color_gamut_for_raw_requested=dormant_color_gamut_for_raw_requested,
        fx3_color_gamut_for_raw_present_claimed=fx3_color_gamut_for_raw_present_claimed,
        claimed_hdmi_settings_wiped_by_camera_reset=claimed_hdmi_settings_wiped_by_camera_reset,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        recording_media=recording_media,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_data_sector_writes=slot1_data_sector_writes,
        internal_co_rec_write_to_slot1_requested=internal_co_rec_write_to_slot1_requested,
        expect_internal_writes_during_hdmi_only=expect_internal_writes_during_hdmi_only,
        hdmi_output_resolution=hdmi_output_resolution,
        expect_4k_hdmi_with_rec_on_during_log_or_pplut=expect_4k_hdmi_with_rec_on_during_log_or_pplut,
        hdmi_4k_setting=hdmi_4k_setting,
        dormant_4k_24p_8bit_requested=dormant_4k_24p_8bit_requested,
        fx3_4k_24p_8bit_present_claimed=fx3_4k_24p_8bit_present_claimed,
        expect_24p_no_reboot=expect_24p_no_reboot,
        hdmi_raw_output=hdmi_raw_output,
        raw_output_setting=raw_output_setting,
        hdmi_time_code_output=hdmi_time_code_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        allow_lcd_blanking_for_hdmi_info=allow_lcd_blanking_for_hdmi_info,
        expect_fx3_lcd_stays_on_when_hdmi_info_on=expect_fx3_lcd_stays_on_when_hdmi_info_on,
        fx6_sdi_raw_allows_4k_hdmi_claimed=fx6_sdi_raw_allows_4k_hdmi_claimed,
        fx6_hdmi_raw_supports_24_00p_claimed=fx6_hdmi_raw_supports_24_00p_claimed,
        fx6_remote_if_syncs_internal_card_claimed=fx6_remote_if_syncs_internal_card_claimed,
        desqueeze_display=desqueeze_display,
        dormant_desqueeze_1_8x_requested=dormant_desqueeze_1_8x_requested,
        fx3_desqueeze_1_8x_present_claimed=fx3_desqueeze_1_8x_present_claimed,
        claimed_desqueeze_wiped_by_camera_reset=claimed_desqueeze_wiped_by_camera_reset,
        desqueeze_1_6x_executed_factor=desqueeze_1_6x_executed_factor,
        focus_mode=focus_mode,
        focus_area=focus_area,
        steadyshot_mode=steadyshot_mode,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        expect_desqueeze_active_in_still=expect_desqueeze_active_in_still,
        expect_desqueeze_bakes_internal_file=expect_desqueeze_bakes_internal_file,
        expect_desqueeze_applied_during_bypass=expect_desqueeze_applied_during_bypass,
        claimed_desqueeze_locks_out_focus_mag_or_bright_mon=claimed_desqueeze_locks_out_focus_mag_or_bright_mon,
        fx6_desqueeze_has_1_6x_or_sdi_claimed=fx6_desqueeze_has_1_6x_or_sdi_claimed,
    )
    gd = evaluate_p329_check_group_d_reclamp_varshutter_apsc_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        body_model_id=body_model_id,
        body_fw=body_fw,
        shoot_mode=shoot_mode,
        silent_mode=silent_mode,
        shutter_type=shutter_type,
        bulb_enabled=bulb_enabled,
        rec_lamp_mode=rec_lamp_mode,
        dormant_tally_light_menu_requested=dormant_tally_light_menu_requested,
        fx3_tally_light_menu_present_claimed=fx3_tally_light_menu_present_claimed,
        dormant_rec_lamp_only_one_requested=dormant_rec_lamp_only_one_requested,
        claimed_rec_lamp_wiped_by_camera_reset=claimed_rec_lamp_wiped_by_camera_reset,
        expect_top_rec_ring_off_with_rear_on=expect_top_rec_ring_off_with_rear_on,
        claimed_silent_mode_turns_off_rec_lamp=claimed_silent_mode_turns_off_rec_lamp,
        emphasized_rec_display=emphasized_rec_display,
        claimed_emph_rec_resists_camera_reset=claimed_emph_rec_resists_camera_reset,
        expect_emph_rec_on_clean_hdmi=expect_emph_rec_on_clean_hdmi,
        remain_shoot_display=remain_shoot_display,
        claimed_remain_shoot_wiped_by_camera_reset=claimed_remain_shoot_wiped_by_camera_reset,
        expect_remain_shoot_shows_movie_time=expect_remain_shoot_shows_movie_time,
        auto_review=auto_review,
        interval_shooting_active=interval_shooting_active,
        expect_auto_review_in_interval=expect_auto_review_in_interval,
        claimed_auto_review_wiped_by_camera_reset=claimed_auto_review_wiped_by_camera_reset,
        anti_flicker_shoot=anti_flicker_shoot,
        dormant_var_shutter_requested=dormant_var_shutter_requested,
        fx3_var_shutter_present_claimed=fx3_var_shutter_present_claimed,
        fx6_ecs_freq_hz=fx6_ecs_freq_hz,
        fx3_has_ecs_mode_claimed=fx3_has_ecs_mode_claimed,
        apsc_s35_shooting=apsc_s35_shooting,
        movie_file_format=movie_file_format,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_4k_only_active=hdmi_4k_only_active,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        still_image_size=still_image_size,
        expect_apsc_4k_or_raw=expect_apsc_4k_or_raw,
        claimed_apsc_wiped_by_camera_reset=claimed_apsc_wiped_by_camera_reset,
        claimed_apsc_still_size_4_2m=claimed_apsc_still_size_4_2m,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        slot1_data_sector_writes=slot1_data_sector_writes,
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
        overall_status = P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE
        go_no_go = P329_GO_NO_GO_BLOCKED_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_FAILURE
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED
        go_no_go = P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED
    else:
        overall_status = P329_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    slot1_mutated = bool(gc.slot1_tier0_vault_mutated or slot1_bodydata_writes != 0)

    report = RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport(
        schema_version=P329_SCHEMA,
        phase_version=P329_VERSION,
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
        slot1_tier0_vault_mutated=slot1_mutated,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_audio_level_display_menu_present=False,
        fx3_bird_insect_car_airplane_present=False,
        fx3_animal_eye_af_in_movie_present=False,
        fx3_shutter_when_pwr_off_present=False,
        fx3_color_gamut_for_raw_output_menu_present=False,
        fx3_4k_24p_8bit_present=False,
        fx3_desqueeze_1_8x_present=False,
        fx3_tally_light_menu_present=False,
        fx3_var_shutter_present=False,
        fx3_apsc_resets_via_camera_settings_reset=False,
        e_nd_actuator_tx_count=PHASE329_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE329_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE329_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE329_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE329_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE329_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE329_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport(
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


def run_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(
    **kwargs: Any,
) -> RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport:
    return evaluate_realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_preflight(**kwargs)


def verify_phase329_report(
    payload: Union[Mapping[str, Any], RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport],
) -> Phase329ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P329_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P329_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P329_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_329_VALID_GO_NO_GO_VALUES:
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
        "fx3_audio_level_display_menu_present",
        "fx3_bird_insect_car_airplane_present",
        "fx3_animal_eye_af_in_movie_present",
        "fx3_shutter_when_pwr_off_present",
        "fx3_color_gamut_for_raw_output_menu_present",
        "fx3_4k_24p_8bit_present",
        "fx3_desqueeze_1_8x_present",
        "fx3_tally_light_menu_present",
        "fx3_var_shutter_present",
        "fx3_apsc_resets_via_camera_settings_reset",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
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
        P329_GO_NO_GO_SHOE_AUDIO_SUBJECT_HDMI_RAW_DESQUEEZE_VARSHUTTER_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase329ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase329_markdown(
    report: RealHwShoeAudio4chSubjectRecogHdmiRawDesqueezeVarShutterReport,
) -> str:
    lines = [
        f"# Phase 329 — 15th Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `ready_attach={report.overall_ready_for_hardware_attach}`, "
        f"`emmc_writes={report.persistent_emmc_writes_authorized}`, "
        f"`cross_model_flash={report.cross_model_flash_authorized}`, "
        f"`rf_pkts={report.rf_packets_transmitted}`, `usb_pkts={report.usb_packets_transmitted}`, "
        f"`slot1_writes={report.slot1_data_sector_writes}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"shoe_audio=`{report.check_group_a.shoe_audio_set}` (`48kHz / 24-bit 4ch` across all 6 main XAVC codecs; "
        f"Proxy `{report.check_group_a.proxy_audio_codec}` cutoff `>= 100p`), "
        f"timing=`{report.check_group_a.audio_out_timing}`, "
        f"subject=`{report.check_group_a.face_eye_subject}` (`Human` / `Animal` only, Still-only Animal Eye AF, "
        f"8-face Memory)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"silent=`{report.check_group_b.silent_mode}` (5 lockouts), "
        f"target_2items=`{report.check_group_b.exposed_target_function_items}`, "
        f"bodydata_policy=`{report.check_group_b.bodydata_flash_policy}` (`BODYDATA.DAT` Slot-1 NO-GO)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"hdmi_raw=`{report.check_group_c.hdmi_raw_output}` (`{report.check_group_c.hdmi_raw_resolution_wh}` 16-bit), "
        f"desqueeze=`{report.check_group_c.desqueeze_display}` (`{report.check_group_c.desqueeze_executed_factor}x`, "
        f"`1.6x` = `1.65x`, no `1.8x`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"rec_lamp=`{report.check_group_d.rec_lamp_mode}`, "
        f"var_shutter=`{report.check_group_d.fx3_var_shutter_present}` (dormant `0x6831` `EOPNOTSUPP=95`), "
        f"apsc=`{report.check_group_d.apsc_s35_shooting}` (`Initialize`-only, `HD <= 120p` / Still `M: 5.1M`)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
