"""Phase 338: 17th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier (Waves 66-67).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Waves 66-67 before any physical bench session:

1. **Check Group A (Wave 66 §§1-2)** — Still ``[Drive Mode]`` (``Hi+ 10fps / > F11 AF lock``),
   100% Dormant ``[Focus Bracket]`` Myth-Busting, 2-Option ``[Shutter Type]`` (``NO Auto`` &
   ``1/250 s`` X-Sync), Reset-Immune ``[e-Front Curtain Shut.]`` (``front_curtaion_shutter``),
   ``[Long Exposure NR]`` (``>= 1 s``) & ``[High ISO NR]``:
   - ``Shooting -> [Drive Mode]`` (``_f 0x7228``, Still-only, ``EOPNOTSUPP=95`` in Movie/S&Q,
     **Resettable**): ``Single Shooting`` (def), ``Cont. Shooting`` (``Hi+ ~10 fps``, ``Hi ~8 fps``,
     ``Mid ~6 fps``, ``Lo ~3 fps``; ``> F11`` locks AF on 1st frame in ``Hi+/Hi/Mid``;
     ``Uncompressed RAW`` or flash reduces burst rate), ``Self-timer(Single)`` (``10/5/2 Sec``),
     ``Self-timer(Cont)`` (``10/5/2 Sec x 3/5 Img.`` = 6 combos), ``Cont. Bracket`` &
     ``Single Bracket``, ``WB bracket``, ``DRO Bracket`` (locked when ``[HLG Still Image] = On``),
     and ``[Interval Shoot Func.]`` (default ``Electronic Shutter``).
   - **100% Dormant ``[Focus Bracket]``**: ``BKID_APP_setting_focus_bracket_*`` & UXC ``0x7563/0x6915``
     exist dormantly in ``FX3 appFw.so`` (cross-verifying Wave 54), with ``0`` hits in ``ilc/2210``
     and ``0`` menu exposure on BOTH ``FX3 Ver. 7.02`` and ``FX6 Ver. 6.01`` (``EOPNOTSUPP=95``).
   - ``[Shutter Type]`` (``_f 0x63db``, Resettable): strictly 2 options (``Mechanical Shutter`` [def],
     ``Electronic Shutter``; **NO ``Auto``**; ``0x66b8`` dormant). ``Electronic Shutter`` /
     ``Silent Mode = On`` locks out Flash, ``Long Exposure NR``, ``e-Front Curtain Shut.``, ``BULB``,
     and ``Anti-flicker Shoot.``. Single ``1/250 s`` X-Sync ceiling (``0`` hits for ``1/320``).
   - ``[e-Front Curtain Shut.]`` (``_f 0x64c6``, Sony ELF typo ``BKID_APP_setting_front_curtaion_shutter``)
     is **Reset-immune** (Initialize-only). ``[Long Exposure NR]`` (``_f 0x6465``, Resettable, active
     at ``>= 1 s``) & ``[High ISO NR]`` (``_f 0x650b``, ``Normal/Low/Off``, Resettable, JPEG/HEIF only,
     never mutates ``.ARW``) vs ``FX6 Noise Suppression`` & ``Technical > APR``.

2. **Check Group B (Wave 66 §§3-4)** — ``[Creative Look]`` (10 Presets + ``Custom Look 1..6`` +
   Asymmetric ``0..9`` ``Fade/Sharpness/Clarity``), Dormant ``[Soft Skin Effect]``, Playback
   ``[Delete]``/``[Protect]`` & ``[Recover Image DB]`` ``Slot-1`` ``EROFS=30`` Firewall:
   - ``[Creative Look]`` (``_f 0x6823`` / ``_f 0x6c98``, Resettable): 10 presets (``ST..SE``) +
     ``Custom Look 1..6`` mapped to 16 ELF slots (``look0..look15``). Exact 8 parameter bounds:
     ``Contrast/Highlights/Shadows/Saturation`` in ``-9..+9``; **asymmetric ``0..9``** for
     ``Fade/Sharpness/Clarity``; ``1..5`` for ``Sharpness Range``. ``BW/SE`` locks ``Saturation``;
     Movie/S&Q locks ``Sharpness Range``; ``iAuto``, ``PP != Off``, ``Log != Off``, or
     ``HLG Still = On`` locks ``[Creative Look]`` to ``[-]``.
   - **Dormant ``[Soft Skin Effect]``** (``_f 0x76d9``, ``BKID_APP_setting_soft_skin_effect``): ``0``
     hits in ``ilc/2210`` and ``EOPNOTSUPP=95`` on BOTH ``FX3`` & ``FX6``.
   - Playback ``[Delete]`` (``0xe504``, 5 scopes, movie+Proxy co-delete, protected skipped),
     ``[Delete confirm.]`` & ``[Delete pressing twice]`` (Reset-immune), ``[Protect]`` (``0xe2c9``,
     not preserved by ``Copy``), ``[Recover Image DB]`` (``_f 0x711b``, battery-gated, resists BOTH
     Reset & Initialize, rewrites ``AVF_INFO``) -> **Tier-0 ``Slot 1`` ``EROFS=30`` firewall**, vs
     ``[Display Media Info.]`` (``0xea2a``, read-only ``40,000`` still cap, ``NOT_DISPLAYNG`` typo).

3. **Check Group C (Wave 67 §§1-2)** — ``[Auto Pixel Mapping]`` & Manual ``[Pixel Mapping]``
   (``pixel_mappinng``/``excuted``), ``Silent Mode`` Shutdown Shutter Click, Myth-Busting
   ``Setup -> [Monitor]`` (3 Reset-Immune Items & Thermal Clamp) & Dormant EVF vs ``FX6 VF Adjust``:
   - ``Setup -> [Setup Option] -> [Auto Pixel Mapping]`` (``_f 0x7734``, ``On``[def]/``Off``,
     **Reset-immune**) & manual ``[Pixel Mapping]`` (``_f 0x61f7``, lens cap + battery gate +
     mandatory reboot; Sony ELF typos ``pixel_mappinng`` & ``excuted``) + ``Silent Mode ->
     Target Function Settings -> [Auto Pixel Mapping]`` (**Resettable** ``Off`` def; ``On`` causes
     shutdown mechanical shutter click ``vdf_set_shutter_mute_by_pixel_mapping``) vs ``FX6 Technical
     > APR > Execute`` & dormant ``auto_black_balance``.
   - **Myth-Busting ``Setup -> [Monitor]`` (NOT ``[Finder/Monitor]``)**: exact 3 **Reset-immune**
     items (``Monitor Brightness`` ``Manual -2..+2 / Sunny Weather``, ``Display Quality``
     ``Standard/High`` with thermal clamp ``High -> Standard``, ``Monitor Flip Direction``);
     ``[Bright Monitoring]`` is NOT here. Dormant EVF menus (``Finder/Monitor Sel.``,
     ``Viewfinder Bright.``, ``Viewfinder Color Temp.``, ``Finder Frame Rate``) -> ``EOPNOTSUPP=95``.
     FX6 ``VF Setting`` + hardware ``MIRROR`` switch + NO 4-subitem ``VF Adjust`` menu.

4. **Check Group D (Wave 67 §§3-4 & Tier-0)** — Still ``P/A/S/M``-Only ``[Recall Custom hold 1-3]``
   (11 Hold Slots, Zero Standalone WB), ``[External Output]`` (``24.00p`` Reboot, ``REC Control <- TC``,
   ``ctrl_for_hmdi``, Dormant ``4K/2K`` & ``24p/60p``), ``Slot-1`` ``EROFS=30`` & ``16/16 H0 == H3``:
   - ``[Recall Custom hold 1-3]`` (``_f 0x60b4/0x7581/0x725b``, Reset-immune, ``CAMSET/*.DAT``):
     strictly **Still ``P/A/S/M`` only** (``EOPNOTSUPP=95`` in Movie/S&Q/iAuto), exact 11 holdable
     slots (``is_checked_recall_custom_hold0..10``), **ZERO standalone ``White Balance`` checkbox**
     (``shoot_set_registration_white_balance`` ``0`` hits), vs ``FX6 Push AF / Push AGC / Push Auto Iris``.
   - ``Setup -> [External Output]`` (Reset-immune): ``[HDMI Resolution]``, ``[HDMI Output Settings]``
     (``Rec. Media dur HDMI Output`` locked ``On`` in ``S&Q``, ``Output Resolution`` clamped to
     ``1080`` under ``Log``/``PPLUT1..4`` + ``Rec. Media=On``, ``4K Output Set.(HDMI Only)``
     ``24.00p`` mandatory reboot & playback isolation, ``RAW Output``, ``Time Code Output``,
     ``REC Control`` requiring ``Time Code Output = On``, ``4ch Audio Output``), ``[HDMI Info. Display]``,
     ``[CTRL FOR HDMI]`` (``BKID_APP_setting_ctrl_for_hmdi``), dormant ``4K/2K`` & ``24p/60p Output``
     (``EOPNOTSUPP=95``).
   - **Tier-0 ``Slot 1`` ``EROFS=30`` firewall** when ``Rec. Media dur HDMI Output = On`` targeting
     ``Slot 1`` + ``16/16 H0 == H3`` + dual-media ``528 B FX3RCPT1`` + ``emmc_write_count = 0``.
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

P338_VERSION = "phase338_v1"
PHASE_338_VERSION = P338_VERSION
P338_SCHEMA = "realhw_preflight17_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc_v1"
P338_SCHEMA_VERSION = P338_SCHEMA
PHASE_338_SCHEMA = P338_SCHEMA
REALHW_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_SCHEMA = P338_SCHEMA
P338_SONY_HELP_GUIDE_ID = "ilc/2210"

P338_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED = (
    "READONLY_PREFLIGHT17_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED"
)
P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE = (
    "BLOCKED_PREFLIGHT17_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE"
)
PHASE_338_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
    P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE,
)

# Bounded donor paths (read-only O_RDONLY)
P338_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
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
        "fx3_libusbbuspower_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so",
    ),
    (
        "fx3_upm_ko",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
    ),
)
P338_HEADER_READ_BYTES = 64

# Unconditional safety / zero-leak constants
PHASE338_RAW_FIRMWARE_BYTES_LEAKED = 0
PHASE338_PASSIVE_TX_BYTES_EMITTED = 0
PHASE338_USB_PACKETS_TRANSMITTED = 0
PHASE338_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE338_SLOT1_DATA_SECTOR_WRITES = 0
PHASE338_E_ND_ACTUATOR_TX_COUNT = 0

P338_ERRNO_EPERM = 1
P338_ERRNO_EBUSY = 16
P338_ERRNO_EINVAL = 22
P338_ERRNO_EROFS = 30
P338_ERRNO_EOPNOTSUPP = 95

# Check Group IDs
P338_CHECK_GROUP_A_ID = "check_group_a_drive_focusbracket_shutter_type_efcs_and_nr"
P338_CHECK_GROUP_B_ID = "check_group_b_creative_look_soft_skin_delete_protect_and_recoverdb"
P338_CHECK_GROUP_C_ID = "check_group_c_pixel_mapping_apr_monitor_and_evf_absence"
P338_CHECK_GROUP_D_ID = "check_group_d_recall_custom_hold_hdmi_tc_recctrl_and_tier0"
PHASE_338_CHECK_GROUP_IDS = (
    P338_CHECK_GROUP_A_ID,
    P338_CHECK_GROUP_B_ID,
    P338_CHECK_GROUP_C_ID,
    P338_CHECK_GROUP_D_ID,
)

# Common valid enums
P338_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P338_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P338_VALID_EXPOSURE_MODES = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P338_VALID_ON_OFF = ("ON", "OFF")

# ---------------------------------------------------------------------------
# Wave 66 §§1-2 Domain Constants (Group A)
# ---------------------------------------------------------------------------
P338_DRIVE_MODE_RESID16_HEX = "0x7228"
P338_VALID_DRIVE_MODES = (
    "SINGLE_SHOOTING",
    "CONT_SHOOTING",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "CONT_BRACKET",
    "SINGLE_BRACKET",
    "WB_BRACKET",
    "DRO_BRACKET",
)
P338_CONT_SPEED_EXACT_FOUR_TIERS = ("HI_PLUS", "HI", "MID", "LO")
P338_CONT_FPS_BY_TIER: Mapping[str, int] = {
    "HI_PLUS": 10,
    "HI": 8,
    "MID": 6,
    "LO": 3,
}
P338_CONT_AF_TRACK_MAX_APERTURE_F = 11.0
P338_SELF_TIMER_SECONDS = (10, 5, 2)
P338_SELF_TIMER_CONT_COUNTS = (3, 5)

P338_DORMANT_FOCUS_BRACKET_UXC_RESIDS = ("0x7563", "0x6915")
P338_DORMANT_FOCUS_BRACKET_BKIDS = (
    "BKID_APP_setting_focus_bracket_depth",
    "BKID_APP_setting_focus_bracket_exposure_lock",
    "BKID_APP_setting_focus_bracket_interval",
    "BKID_APP_setting_focus_bracket_number_of_shots",
    "BKID_APP_setting_focus_bracket_order",
    "BKID_APP_setting_focus_bracket_rec_folder",
)
P338_DORMANT_FOCUS_BRACKET_ENUM = "VAL_setting_menu_drive_mode_DRIVE_MODE_FOCUS_BRACKET"
P338_FOCUS_BRACKET_ILC2210_HITS = 0

P338_SHUTTER_TYPE_RESID16_HEX = "0x63db"
P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS = ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER")
P338_DORMANT_ANTI_DISTORTION_SHUTTER_AUTO_RESID16_HEX = "0x66b8"
P338_FLASH_XSYNC_DENOMINATOR = 250
P338_ABSENT_XSYNC_1_320_HITS = 0

P338_EFCS_RESID16_HEX = "0x64c6"
P338_EFCS_SONY_ELF_TYPO_BKID = "BKID_APP_setting_front_curtaion_shutter"
P338_LONG_EXP_NR_RESID16_HEX = "0x6465"
P338_LONG_EXP_NR_BKID = "BKID_APP_setting_still_long_exposure_nr"
P338_LONG_EXP_NR_MIN_SHUTTER_SECONDS = 1.0
P338_HIGH_ISO_NR_RESID16_HEX = "0x650b"
P338_HIGH_ISO_NR_BKID = "BKID_APP_setting_still_high_iso_nr"
P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS = ("NORMAL", "LOW", "OFF")
P338_VALID_STILL_FILE_FORMATS = ("RAW", "RAW_AND_JPEG", "RAW_AND_HEIF", "JPEG", "HEIF")
P338_VALID_RAW_FILE_TYPES = ("COMPRESSED", "UNCOMPRESSED")

# ---------------------------------------------------------------------------
# Wave 66 §§3-4 Domain Constants (Group B)
# ---------------------------------------------------------------------------
P338_CREATIVE_LOOK_RESID16_HEX = "0x6823"
P338_CREATIVE_LOOK_RESET_RESID16_HEX = "0x6c22"
P338_CREATIVE_LOOK_CUSTOM_RESID16_HEX = "0x6c98"
P338_CREATIVE_LOOK_TEN_PRESETS = ("ST", "PT", "NT", "VV", "VV2", "FL", "IN", "SH", "BW", "SE")
P338_CREATIVE_LOOK_SIX_CUSTOM_SLOTS = (
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
    "CUSTOM_4",
    "CUSTOM_5",
    "CUSTOM_6",
)
P338_CREATIVE_LOOK_SIXTEEN_ELF_SLOTS = tuple(f"look{i}" for i in range(16))
P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES: Mapping[str, Tuple[int, int]] = {
    "CONTRAST": (-9, 9),
    "HIGHLIGHTS": (-9, 9),
    "SHADOWS": (-9, 9),
    "FADE": (0, 9),
    "SATURATION": (-9, 9),
    "SHARPNESS": (0, 9),
    "SHARPNESS_RANGE": (1, 5),
    "CLARITY": (0, 9),
}
P338_DORMANT_SOFT_SKIN_RESID16_HEX = "0x76d9"
P338_DORMANT_SOFT_SKIN_BKID = "BKID_APP_setting_soft_skin_effect"

P338_DELETE_BASE_RESID16_HEX = "0xe504"
P338_PROTECT_BASE_RESID16_HEX = "0xe2c9"
P338_RECOVER_IMAGE_DB_RESID16_HEX = "0x711b"
P338_DISPLAY_MEDIA_INFO_BASE_RESID16_HEX = "0xea2a"
P338_DELETE_FIVE_SCOPES = (
    "THIS_IMAGE",
    "ALL_OTHER_IMAGES",
    "MULTIPLE_IMAGES",
    "ALL_IN_THIS_FOLDER",
    "ALL_WITH_THIS_DATE",
)
P338_DELETE_CONFIRM_OPTIONS = ("CANCEL_FIRST", "DELETE_FIRST")
P338_DISPLAY_MEDIA_INFO_STILL_CAP = 40000
P338_DISPLAY_MEDIA_INFO_TYPO_SYMBOL = "NOT_DISPLAYNG"

# ---------------------------------------------------------------------------
# Wave 67 §§1-2 Domain Constants (Group C)
# ---------------------------------------------------------------------------
P338_AUTO_PIXEL_MAPPING_RESID16_HEX = "0x7734"
P338_MANUAL_PIXEL_MAPPING_RESID16_HEX = "0x61f7"
P338_PIXEL_MAPPING_SONY_TYPO_NOTIFICATION_BKID = "BKID_APP_setting_notification_for_pixel_mappinng"
P338_PIXEL_MAPPING_SONY_TYPO_STATUS_BKID = "BKID_APP_pixel_mapping_excuted_status"
P338_SILENT_AUTO_PM_SHUTTER_MUTE_SYMBOL = "vdf_set_shutter_mute_by_pixel_mapping"
P338_PIXEL_MAPPING_BATTERY_CHECK_SYMBOL = "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING"
P338_PIXEL_MAPPING_RECOMMENDED_INTERVAL_DAYS = 3
P338_PIXEL_MAPPING_MIN_BATTERY_PCT = 20

P338_MONITOR_EXACT_THREE_ITEMS = (
    "MONITOR_BRIGHTNESS",
    "DISPLAY_QUALITY",
    "MONITOR_FLIP_DIRECTION",
)
P338_MONITOR_BRIGHTNESS_MODES = ("MANUAL", "SUNNY_WEATHER")
P338_MONITOR_BRIGHTNESS_MANUAL_RANGE = (-2, 2)
P338_DISPLAY_QUALITY_MODES = ("STANDARD", "HIGH")
P338_MONITOR_FLIP_MODES = ("AUTO", "HORIZONTAL_FLIP", "DEGREE_180_FLIP", "NO_FLIP")
P338_DORMANT_EVF_MENU_ITEMS = (
    "FINDER_MONITOR_SEL",
    "VIEWFINDER_BRIGHT",
    "VIEWFINDER_COLOR_TEMP",
    "FINDER_FRAME_RATE",
)
P338_DORMANT_FX6_VF_ADJUST_FOUR_SUBITEMS = ("BACKLIGHT", "CONTRAST", "CHROMA", "COLOR_TEMP")

# ---------------------------------------------------------------------------
# Wave 67 §§3-4 Domain Constants (Group D)
# ---------------------------------------------------------------------------
P338_RECALL_CUSTOM_HOLD_UXC_RESIDS = ("0x60b4", "0x7581", "0x725b")
P338_RECALL_CUSTOM_HOLD_STILL_EXPOSURE_MODES = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
)
P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS = (
    "shooting_mode",
    "aperture",
    "shutter_speed",
    "exposure_comp",
    "iso_sensitivity",
    "metering_mode",
    "drive_mode",
    "focus_mode",
    "focus_area",
    "af_on",
    "still_af_track_sens",
)
P338_RECALL_CUSTOM_HOLD_ELF_PREFIX = "is_checked_recall_custom_hold"
P338_RECALL_CUSTOM_HOLD_ABSENT_WB_SYMBOL = "shoot_set_registration_white_balance"
P338_RECALL_CUSTOM_HOLD_WB_HITS = 0

P338_HDMI_RESOLUTIONS = ("AUTO", "2160P", "1080P", "1080I")
P338_HDMI_4K_OUTPUT_RATES = ("59_94P", "50P", "29_97P", "25P", "23_98P", "24_00P")
P338_REC_MEDIA_DUR_HDMI_MODES = ("ON", "OFF_HDMI_ONLY")
P338_HDMI_4CH_AUDIO_MODES = ("CH1_CH2", "CH3_CH4")
P338_CTRL_FOR_HDMI_SONY_TYPO_BKID = "BKID_APP_setting_ctrl_for_hmdi"
P338_FOUR_K_OUTPUT_SET_TYPO_SYMBOL = "outpute"
P338_DORMANT_HDMI_EXTERNAL_ITEMS = ("4K_2K_OUTPUT", "24P_60P_OUTPUT")
P338_VALID_RECORDING_MEDIA_MODES = (
    "SLOT_1",
    "SLOT_2",
    "SIMULTANEOUS_RECORDING",
    "SORT_RECORDING",
)
P338_STORAGE_SURFACE_COUNT = len(SIXTEEN_STORAGE_SURFACES)

# ---------------------------------------------------------------------------
# Error Prefix Constants
# ---------------------------------------------------------------------------
P338_GA_ERR_MODEL_OR_FW_FLOOR = "P338_GA_ERR_MODEL_OR_FW_FLOOR"
P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT = "P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT"
P338_GA_ERR_DORMANT_FOCUS_BRACKET_MYTH = "P338_GA_ERR_DORMANT_FOCUS_BRACKET_MYTH"
P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE = "P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE"
P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR = "P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR"

P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS = "P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS"
P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT = "P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT"
P338_GB_ERR_DORMANT_SOFT_SKIN_EFFECT = "P338_GB_ERR_DORMANT_SOFT_SKIN_EFFECT"
P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT = "P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT"

P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING = "P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING"
P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR = "P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR"
P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP = "P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP"
P338_GC_ERR_DORMANT_EVF_OR_FX6_VF_ADJUST = "P338_GC_ERR_DORMANT_EVF_OR_FX6_VF_ADJUST"

P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS = "P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS"
P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT = "P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT"
P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS = "P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS"
P338_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P338_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = "P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Phase338DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    fx3_appfw_present: bool
    fx6_appfw_present: bool
    fx3_uxc_present: bool
    checked_paths: Tuple[str, ...]
    bytes_read_total: int
    elapsed_seconds: float
    within_budget: bool
    raw_firmware_bytes_leaked: int = PHASE338_RAW_FIRMWARE_BYTES_LEAKED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P338CheckGroupADriveFocusBracketShutterEfcsNrResult:
    group_id: str
    passed: bool
    shoot_mode: str
    drive_mode: str
    cont_speed_tier: str
    cont_max_fps: int
    aperture_f_number: float
    af_first_frame_locked_above_f11: bool
    fx3_focus_bracket_present: bool
    fx6_focus_bracket_present: bool
    shutter_type: str
    fx3_shutter_type_auto_present: bool
    flash_xsync_denominator: int
    e_front_curtain_shutter: str
    efcs_elf_typo_bkid: str
    long_exposure_nr: str
    shutter_seconds: float
    high_iso_nr: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P338CheckGroupBCreativeLookSoftSkinRecoverDbResult:
    group_id: str
    passed: bool
    creative_look_slot: str
    creative_look_locked_by_pp_log_hlg_iauto: bool
    creative_look_contrast: int
    creative_look_highlights: int
    creative_look_shadows: int
    creative_look_fade: int
    creative_look_saturation: int
    creative_look_sharpness: int
    creative_look_sharpness_range: int
    creative_look_clarity: int
    fx3_soft_skin_effect_present: bool
    fx6_soft_skin_effect_present: bool
    delete_scope: str
    delete_confirm: str
    delete_pressing_twice: str
    protect_scope: str
    recover_image_db_requested: bool
    recover_image_db_slot: int
    display_media_info_still_cap: int
    slot1_tier0_vault_mutated: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P338CheckGroupCPixelMapMonitorEvfResult:
    group_id: str
    passed: bool
    auto_pixel_mapping: str
    manual_pixel_mapping_requested: bool
    silent_mode: str
    silent_auto_pixel_mapping: str
    shutdown_shutter_click_triggered: bool
    pixel_mapping_typo_bkids: Tuple[str, ...]
    exposed_monitor_items: Tuple[str, ...]
    monitor_brightness_mode: str
    monitor_brightness_level: int
    display_quality: str
    display_quality_thermally_clamped: bool
    monitor_flip_direction: str
    fx3_builtin_evf_present: bool
    fx3_finder_monitor_menu_present: bool
    fx6_vf_adjust_four_subitems_present: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P338CheckGroupDRecallHoldHdmiTcTier0Result:
    group_id: str
    passed: bool
    shoot_mode: str
    exposure_mode: str
    recall_custom_hold_active: bool
    recall_custom_hold_slot: int
    recall_custom_hold_eleven_slots: Tuple[str, ...]
    fx3_recall_custom_hold_standalone_wb_present: bool
    hdmi_resolution: str
    rec_media_dur_hdmi_output: str
    hdmi_output_resolution: str
    hdmi_4k_output_rate: str
    hdmi_raw_output: str
    hdmi_tc_output: str
    hdmi_rec_control: str
    hdmi_4ch_audio_output: str
    hdmi_info_display: str
    ctrl_for_hdmi: str
    ctrl_for_hdmi_typo_bkid: str
    fx3_4k_2k_output_present: bool
    fx3_24p_60p_output_present: bool
    recording_media: str
    rec_target_slot: int
    slot1_tier0_vault_mutated: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    emmc_write_count: int
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase338ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport:
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
    check_group_a: P338CheckGroupADriveFocusBracketShutterEfcsNrResult
    check_group_b: P338CheckGroupBCreativeLookSoftSkinRecoverDbResult
    check_group_c: P338CheckGroupCPixelMapMonitorEvfResult
    check_group_d: P338CheckGroupDRecallHoldHdmiTcTier0Result
    donor_inspection: Phase338DonorInspectionResult
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
    fx3_focus_bracket_present: bool
    fx6_focus_bracket_present: bool
    fx3_shutter_type_auto_present: bool
    fx3_soft_skin_effect_present: bool
    fx6_soft_skin_effect_present: bool
    fx3_builtin_evf_present: bool
    fx3_finder_monitor_menu_present: bool
    fx3_recall_custom_hold_standalone_wb_present: bool
    fx3_4k_2k_output_present: bool
    fx3_24p_60p_output_present: bool
    emmc_write_count: int
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


def _bounded_read_header(path: Path, max_bytes: int = P338_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def resolve_phase338_donor_file_or_none(
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
        if any(resolve_phase338_donor_file_or_none(candidate, rel) is not None for _lbl, rel in P338_BOUNDED_DONOR_PATHS):
            return candidate
    return None


def inspect_phase338_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase338DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 0.20s) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase338DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE338_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = (
        work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    )
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase338DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE338_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P338_BOUNDED_DONOR_PATHS:
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
            resolved = resolve_phase338_donor_file_or_none(effective_work_root, rel)
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
    return Phase338DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_uxc_present=found_map.get("fx3_libusbbuspower_so", False) and found_map.get("fx3_upm_ko", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE338_RAW_FIRMWARE_BYTES_LEAKED,
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 66 §§1-2): Drive, Focus Bracket, Shutter Type, EFCS, NR
# ---------------------------------------------------------------------------
def evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P338_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Wave 66 §1: Still [Drive Mode] & Dormant [Focus Bracket]
    drive_mode: str = "SINGLE_SHOOTING",
    cont_speed_tier: str = "HI_PLUS",
    aperture_f_number: float = 2.8,
    still_file_format: str = "RAW",
    raw_file_type: str = "COMPRESSED",
    flash_enabled: bool = False,
    self_timer_sec: int = 10,
    self_timer_cont_images: int = 3,
    hlg_still_image: str = "OFF",
    picture_profile: str = "OFF",
    log_shooting_mode: str = "OFF",
    interval_shutter_type: str = "ELECTRONIC_SHUTTER",
    expect_af_tracks_all_frames_above_f11: bool = False,
    expect_full_cont_fps_with_uncompressed_raw_or_flash: bool = False,
    claimed_drive_mode_active_in_movie_or_sq: bool = False,
    claimed_drive_mode_resists_camera_reset: bool = False,
    claimed_interval_default_mech_shutter: bool = False,
    fx6_has_still_drive_mode_menu_claimed: bool = False,
    dormant_focus_bracket_requested: bool = False,
    fx3_focus_bracket_present_claimed: bool = False,
    fx6_focus_bracket_present_claimed: bool = False,
    claimed_focus_bracket_in_ilc2210: bool = False,
    # Wave 66 §2: [Shutter Type], X-Sync, [e-Front Curtain Shut.], Long Exp NR, High ISO NR
    shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    dormant_shutter_type_auto_requested: bool = False,
    fx3_shutter_type_auto_present_claimed: bool = False,
    flash_sync_denominator: int = P338_FLASH_XSYNC_DENOMINATOR,
    claimed_1_320_xsync_supported: bool = False,
    e_front_curtain_shutter: str = "ON",
    efcs_active_claimed: bool = False,
    claimed_efcs_wiped_by_camera_reset: bool = False,
    long_exposure_nr: str = "ON",
    shutter_seconds: float = 0.01,
    bulb_enabled: bool = False,
    anti_flicker_shoot: bool = False,
    claimed_long_exp_nr_active_below_1s: bool = False,
    claimed_long_exp_nr_resists_reset: bool = False,
    high_iso_nr: str = "NORMAL",
    expect_high_iso_nr_modifies_arw_raw: bool = False,
    dormant_high_iso_nr_high_option_requested: bool = False,
    claimed_high_iso_nr_resists_reset: bool = False,
    fx6_noise_suppression_uses_still_nr_menu_claimed: bool = False,
) -> P338CheckGroupADriveFocusBracketShutterEfcsNrResult:
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_id != TARGET_MODEL_ID_INT
        or body_fw != TARGET_BODY_FW
        or sony_help_guide_id != P338_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P338_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW} "
            f"help_guide={P338_SONY_HELP_GUIDE_ID}, got {hex(body_model_id)} fw={body_fw} "
            f"help_guide={sony_help_guide_id}"
        )
    if reset_action not in P338_VALID_RESET_ACTIONS:
        errors.append(f"{P338_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action}")
    if shoot_mode not in P338_VALID_SHOOT_MODES:
        errors.append(f"{P338_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode}")
    if exposure_mode not in P338_VALID_EXPOSURE_MODES:
        errors.append(f"{P338_GA_ERR_MODEL_OR_FW_FLOOR}: invalid exposure_mode={exposure_mode}")

    # [Drive Mode] (Wave 66 §1)
    if drive_mode not in P338_VALID_DRIVE_MODES:
        errors.append(f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: invalid drive_mode={drive_mode}")
    if cont_speed_tier not in P338_CONT_SPEED_EXACT_FOUR_TIERS:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: invalid cont_speed_tier={cont_speed_tier} "
            f"(exact 4 tiers: {P338_CONT_SPEED_EXACT_FOUR_TIERS})"
        )
    if still_file_format not in P338_VALID_STILL_FILE_FORMATS:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: invalid still_file_format={still_file_format}"
        )
    if raw_file_type not in P338_VALID_RAW_FILE_TYPES:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: invalid raw_file_type={raw_file_type}"
        )
    if claimed_drive_mode_active_in_movie_or_sq or (
        shoot_mode in ("MOVIE", "S_AND_Q") and drive_mode != "SINGLE_SHOOTING"
    ):
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: Still [Drive Mode] ({P338_DRIVE_MODE_RESID16_HEX}) "
            f"is disabled in Movie/S&Q (errno={P338_ERRNO_EOPNOTSUPP})"
        )
    if reset_action == "CAMERA_SETTINGS_RESET" and drive_mode != "SINGLE_SHOOTING":
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: [Drive Mode] is Resettable via "
            "[Camera Settings Reset] and must return to SINGLE_SHOOTING"
        )
    if claimed_drive_mode_resists_camera_reset or claimed_interval_default_mech_shutter:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: [Drive Mode] resets via Camera Settings Reset, "
            "and [Interval Shoot Func.] [Shutter Type in Interval] defaults to Electronic Shutter"
        )
    if interval_shutter_type not in P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: invalid interval_shutter_type={interval_shutter_type}"
        )
    if fx6_has_still_drive_mode_menu_claimed:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: ILME-FX6 does NOT expose Still [Drive Mode] "
            "or Focus Bracket (cinema body uses Picture Cache Rec / Interval Rec)"
        )

    af_first_frame_locked_above_f11 = (
        drive_mode == "CONT_SHOOTING"
        and cont_speed_tier in ("HI_PLUS", "HI", "MID")
        and aperture_f_number > P338_CONT_AF_TRACK_MAX_APERTURE_F
    )
    if expect_af_tracks_all_frames_above_f11 and aperture_f_number > P338_CONT_AF_TRACK_MAX_APERTURE_F:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: in Cont. Shooting Hi+/Hi/Mid with aperture "
            f"F{aperture_f_number} > F11, focus locks on the 1st frame (does not track all frames)"
        )
    if expect_full_cont_fps_with_uncompressed_raw_or_flash and (
        ("RAW" in still_file_format and raw_file_type == "UNCOMPRESSED") or flash_enabled
    ):
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: Uncompressed RAW or Flash firing drops "
            "Cont. Shooting burst rate below full Hi+ 10fps"
        )
    if drive_mode == "SELF_TIMER_SINGLE" and self_timer_sec not in P338_SELF_TIMER_SECONDS:
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: Self-timer(Single) requires 10/5/2 Sec "
            f"(got {self_timer_sec})"
        )
    if drive_mode == "SELF_TIMER_CONT" and (
        self_timer_sec not in P338_SELF_TIMER_SECONDS or self_timer_cont_images not in P338_SELF_TIMER_CONT_COUNTS
    ):
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: Self-timer(Cont) requires 10/5/2 Sec x 3/5 Img "
            f"(got {self_timer_sec}s x {self_timer_cont_images})"
        )
    if drive_mode in ("CONT_BRACKET", "SINGLE_BRACKET") and exposure_mode == "INTELLIGENT_AUTO":
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: Cont./Single Bracket is disabled in Intelligent Auto"
        )
    if drive_mode == "DRO_BRACKET" and (
        hlg_still_image == "ON" or picture_profile != "OFF" or log_shooting_mode != "OFF"
    ):
        errors.append(
            f"{P338_GA_ERR_DRIVE_MODE_OR_CONT_FPS_LOCKOUT}: DRO Bracket is disabled when "
            "[HLG Still Image]=ON, Picture Profile!=OFF, or Log Shooting!=OFF"
        )

    # 100% Dormant [Focus Bracket] Myth-Busting
    if (
        dormant_focus_bracket_requested
        or fx3_focus_bracket_present_claimed
        or fx6_focus_bracket_present_claimed
        or claimed_focus_bracket_in_ilc2210
    ):
        errors.append(
            f"{P338_GA_ERR_DORMANT_FOCUS_BRACKET_MYTH}: [Focus Bracket] ({P338_DORMANT_FOCUS_BRACKET_UXC_RESIDS}, "
            f"{P338_DORMANT_FOCUS_BRACKET_ENUM}) is 100% DORMANT on FX3 Ver. 7.02 (0 hits in ilc/2210) AND "
            f"FX6 Ver. 6.01 (56+ dormant symbols, 0 UI exposure) (errno={P338_ERRNO_EOPNOTSUPP})"
        )

    # [Shutter Type], X-Sync, [e-Front Curtain Shut.] (Wave 66 §2)
    if silent_mode not in P338_VALID_ON_OFF:
        errors.append(f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: invalid silent_mode={silent_mode}")
    if e_front_curtain_shutter not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: invalid e_front_curtain_shutter={e_front_curtain_shutter}"
        )
    if (
        shutter_type not in P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS
        or dormant_shutter_type_auto_requested
        or fx3_shutter_type_auto_present_claimed
    ):
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: [Shutter Type] ({P338_SHUTTER_TYPE_RESID16_HEX}) "
            f"exposes strictly 2 options {P338_SHUTTER_TYPE_EXACT_TWO_OPTIONS}; Auto ({P338_DORMANT_ANTI_DISTORTION_SHUTTER_AUTO_RESID16_HEX}) "
            f"is dormant/absent on FX3 (errno={P338_ERRNO_EOPNOTSUPP})"
        )
    if flash_sync_denominator > P338_FLASH_XSYNC_DENOMINATOR or claimed_1_320_xsync_supported:
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: FX3 single flash X-Sync ceiling is 1/250 s "
            f"(got 1/{flash_sync_denominator} s; 0 hits for 1/320 in ilc/2210)"
        )
    electronic_lockout = shutter_type == "ELECTRONIC_SHUTTER" or silent_mode == "ON"
    if electronic_lockout and (
        flash_enabled or long_exposure_nr == "ON" or bulb_enabled or anti_flicker_shoot or efcs_active_claimed
    ):
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: Electronic Shutter / Silent Mode=ON locks out "
            "all 5 items: Flash, [Long Exposure NR], [e-Front Curtain Shut.], BULB, and [Anti-flicker Shoot.]"
        )
    if claimed_efcs_wiped_by_camera_reset:
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: [e-Front Curtain Shut.] "
            f"({P338_EFCS_RESID16_HEX}, Sony typo {P338_EFCS_SONY_ELF_TYPO_BKID}) is Reset-immune (Initialize-only)"
        )
    if reset_action == "INITIALIZE" and e_front_curtain_shutter != "ON":
        errors.append(
            f"{P338_GA_ERR_SHUTTER_TYPE_XSYNC_OR_EFCS_PERSISTENCE}: [e-Front Curtain Shut.] must return to ON after INITIALIZE"
        )

    # [Long Exposure NR] & [High ISO NR]
    if long_exposure_nr not in P338_VALID_ON_OFF:
        errors.append(f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: invalid long_exposure_nr={long_exposure_nr}")
    if high_iso_nr not in P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS or dormant_high_iso_nr_high_option_requested:
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: [High ISO NR] ({P338_HIGH_ISO_NR_RESID16_HEX}) "
            f"exposes strictly {P338_HIGH_ISO_NR_EXACT_THREE_OPTIONS} (HIGH is dormant/absent)"
        )
    if long_exposure_nr == "ON" and drive_mode in ("CONT_SHOOTING", "CONT_BRACKET"):
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: [Long Exposure NR] ({P338_LONG_EXP_NR_RESID16_HEX}) "
            "is disabled during Cont. Shooting and Cont. Bracket"
        )
    if exposure_mode == "INTELLIGENT_AUTO" and (long_exposure_nr != "ON" or high_iso_nr != "NORMAL"):
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: Intelligent Auto locks Long Exposure NR=ON and High ISO NR=NORMAL"
        )
    if claimed_long_exp_nr_active_below_1s and shutter_seconds < P338_LONG_EXP_NR_MIN_SHUTTER_SECONDS:
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: [Long Exposure NR] only triggers at shutter >= 1 s "
            f"(got {shutter_seconds} s)"
        )
    if reset_action == "CAMERA_SETTINGS_RESET" and (long_exposure_nr != "ON" or high_iso_nr != "NORMAL"):
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: both [Long Exposure NR] (ON) and [High ISO NR] (NORMAL) "
            "are Resettable via [Camera Settings Reset]"
        )
    if (
        claimed_long_exp_nr_resists_reset
        or claimed_high_iso_nr_resists_reset
        or expect_high_iso_nr_modifies_arw_raw
        or fx6_noise_suppression_uses_still_nr_menu_claimed
    ):
        errors.append(
            f"{P338_GA_ERR_LONG_EXP_OR_HIGH_ISO_NR_OR_FX6_APR}: Long Exposure NR & High ISO NR are Resettable; "
            "High ISO NR applies ONLY to JPEG/HEIF (never .ARW); FX6 uses Shooting > Noise Suppression & Technical > APR"
        )

    cont_fps = P338_CONT_FPS_BY_TIER.get(cont_speed_tier, 0)
    return P338CheckGroupADriveFocusBracketShutterEfcsNrResult(
        group_id=P338_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        drive_mode=drive_mode,
        cont_speed_tier=cont_speed_tier,
        cont_max_fps=cont_fps,
        aperture_f_number=aperture_f_number,
        af_first_frame_locked_above_f11=af_first_frame_locked_above_f11,
        fx3_focus_bracket_present=False,
        fx6_focus_bracket_present=False,
        shutter_type=shutter_type,
        fx3_shutter_type_auto_present=False,
        flash_xsync_denominator=flash_sync_denominator,
        e_front_curtain_shutter=e_front_curtain_shutter,
        efcs_elf_typo_bkid=P338_EFCS_SONY_ELF_TYPO_BKID,
        long_exposure_nr=long_exposure_nr,
        shutter_seconds=shutter_seconds,
        high_iso_nr=high_iso_nr,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 66 §§3-4): Creative Look, Soft Skin, Delete/Protect/RecoverDB
# ---------------------------------------------------------------------------
def evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
    *,
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    reset_action: str = "NONE",
    # Wave 66 §3: [Creative Look] & Dormant [Soft Skin Effect]
    creative_look_slot: str = "ST",
    picture_profile: str = "OFF",
    log_shooting_mode: str = "OFF",
    hlg_still_image: str = "OFF",
    creative_look_contrast: int = 0,
    creative_look_highlights: int = 0,
    creative_look_shadows: int = 0,
    creative_look_fade: int = 0,
    creative_look_saturation: int = 0,
    creative_look_sharpness: int = 0,
    creative_look_sharpness_range: int = 3,
    creative_look_clarity: int = 0,
    creative_look_saturation_adjusted: bool = False,
    creative_look_sharpness_range_adjusted: bool = False,
    expect_creative_look_active_under_pp_log_hlg_iauto: bool = False,
    claimed_creative_look_fade_sharpness_clarity_accept_negative: bool = False,
    claimed_creative_look_resists_camera_reset: bool = False,
    dormant_soft_skin_requested: bool = False,
    fx3_soft_skin_present_claimed: bool = False,
    fx6_soft_skin_present_claimed: bool = False,
    # Wave 66 §4: [Delete], [Delete pressing twice], [Protect], [Recover Image DB], [Display Media Info.]
    delete_scope: str = "THIS_IMAGE",
    delete_confirm: str = "CANCEL_FIRST",
    delete_pressing_twice: str = "OFF",
    protect_scope: str = "THIS_IMAGE",
    delete_write_requested: bool = False,
    delete_write_slot: int = 2,
    protect_write_requested: bool = False,
    protect_write_slot: int = 2,
    protected_item_delete_attempted: bool = False,
    slot_format_executed: bool = False,
    claimed_delete_confirm_wiped_by_camera_reset: bool = False,
    claimed_delete_twice_wiped_by_camera_reset: bool = False,
    expect_copy_preserves_protect: bool = False,
    recover_image_db_requested: bool = False,
    recover_image_db_slot: int = 2,
    battery_soc_pct: int = 85,
    low_battery_warning: bool = False,
    claimed_recover_db_wiped_by_reset_or_init: bool = False,
    claimed_display_media_info_mutates_media: bool = False,
    claimed_display_media_info_cap_not_40000: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
) -> P338CheckGroupBCreativeLookSoftSkinRecoverDbResult:
    errors: List[str] = []
    warnings: List[str] = []

    valid_cl_slots = (*P338_CREATIVE_LOOK_TEN_PRESETS, *P338_CREATIVE_LOOK_SIX_CUSTOM_SLOTS)
    if creative_look_slot not in valid_cl_slots:
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS}: invalid creative_look_slot={creative_look_slot} "
            f"(valid 10 presets + 6 custom slots: {valid_cl_slots})"
        )

    param_values = {
        "CONTRAST": creative_look_contrast,
        "HIGHLIGHTS": creative_look_highlights,
        "SHADOWS": creative_look_shadows,
        "FADE": creative_look_fade,
        "SATURATION": creative_look_saturation,
        "SHARPNESS": creative_look_sharpness,
        "SHARPNESS_RANGE": creative_look_sharpness_range,
        "CLARITY": creative_look_clarity,
    }
    for pname, pval in param_values.items():
        lo, hi = P338_CREATIVE_LOOK_EIGHT_PARAM_RANGES[pname]
        if not (lo <= pval <= hi):
            errors.append(
                f"{P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS}: [Creative Look] {pname}={pval} "
                f"outside exact range [{lo}, {hi}]"
            )
    if claimed_creative_look_fade_sharpness_clarity_accept_negative:
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_PRESET_OR_PARAM_BOUNDS}: Fade, Sharpness, and Clarity use asymmetric "
            "0..9 bounds (NOT -9..+9)"
        )

    locked_by_mode = (
        picture_profile != "OFF"
        or log_shooting_mode != "OFF"
        or hlg_still_image == "ON"
        or exposure_mode == "INTELLIGENT_AUTO"
    )
    if expect_creative_look_active_under_pp_log_hlg_iauto and locked_by_mode:
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT}: [Creative Look] is locked to [-] when "
            "Picture Profile!=OFF, Log Shooting!=OFF, HLG Still=ON, or Intelligent Auto is active"
        )
    if creative_look_slot in ("BW", "SE") and (creative_look_saturation_adjusted or creative_look_saturation != 0):
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT}: [Creative Look] {creative_look_slot} locks Saturation"
        )
    if shoot_mode in ("MOVIE", "S_AND_Q") and creative_look_sharpness_range_adjusted:
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT}: [Creative Look] Sharpness Range (1..5) is locked in Movie/S&Q"
        )
    if reset_action == "CAMERA_SETTINGS_RESET" and creative_look_slot != "ST":
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT}: [Creative Look] resets to ST on [Camera Settings Reset]"
        )
    if claimed_creative_look_resists_camera_reset:
        errors.append(
            f"{P338_GB_ERR_CREATIVE_LOOK_LOCKOUT_CONFLICT}: [Creative Look] is Resettable via [Camera Settings Reset]"
        )

    # Dormant [Soft Skin Effect]
    if dormant_soft_skin_requested or fx3_soft_skin_present_claimed or fx6_soft_skin_present_claimed:
        errors.append(
            f"{P338_GB_ERR_DORMANT_SOFT_SKIN_EFFECT}: [Soft Skin Effect] ({P338_DORMANT_SOFT_SKIN_RESID16_HEX}, "
            f"{P338_DORMANT_SOFT_SKIN_BKID}) is DORMANT/UNSUPPORTED on BOTH FX3 Ver. 7.02 (0 hits in ilc/2210) "
            f"and FX6 Ver. 6.01 (errno={P338_ERRNO_EOPNOTSUPP})"
        )

    # Playback [Delete], [Delete pressing twice], [Protect], [Recover Image DB], [Display Media Info.]
    if delete_scope not in P338_DELETE_FIVE_SCOPES:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: invalid delete_scope={delete_scope}"
        )
    if delete_confirm not in P338_DELETE_CONFIRM_OPTIONS:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: invalid delete_confirm={delete_confirm}"
        )
    if delete_pressing_twice not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: invalid delete_pressing_twice={delete_pressing_twice}"
        )
    if claimed_delete_confirm_wiped_by_camera_reset or claimed_delete_twice_wiped_by_camera_reset:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: [Delete confirm.] and [Delete pressing twice] "
            "are Reset-immune (Initialize-only)"
        )
    if protected_item_delete_attempted and not slot_format_executed:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: [Delete] skips protected files "
            "(only [Format] removes protected clips)"
        )
    if expect_copy_preserves_protect:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: Playback [Copy] does NOT preserve [Protect] status"
        )
    if recover_image_db_requested and (low_battery_warning or battery_soc_pct < 20):
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: [Recover Image DB] ({P338_RECOVER_IMAGE_DB_RESID16_HEX}) "
            f"blocked by battery gate (soc={battery_soc_pct}%, low_battery_warning={low_battery_warning})"
        )
    if claimed_recover_db_wiped_by_reset_or_init or claimed_display_media_info_mutates_media or claimed_display_media_info_cap_not_40000:
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: [Recover Image DB] rewrites AVF_INFO (resists both "
            "Reset & Initialize); [Display Media Info.] (0xea2a) is read-only with 40,000 still cap"
        )

    slot1_mutated = False
    if slot1_contains_tier0_dump and (
        (recover_image_db_requested and recover_image_db_slot == 1)
        or (delete_write_requested and delete_write_slot == 1)
        or (protect_write_requested and protect_write_slot == 1)
        or slot1_data_sector_writes != 0
    ):
        slot1_mutated = True
        errors.append(
            f"{P338_GB_ERR_DELETE_PROTECT_RECOVERDB_OR_SLOT1_VAULT}: Slot-1 Tier-0 Vault write firewall triggered "
            f"(errno={P338_ERRNO_EROFS} EROFS; [Select Playback Media] defaults to Slot 1 after Reset so "
            "[Recover Image DB]/[Delete]/[Protect] must NOT touch Slot 1)"
        )

    return P338CheckGroupBCreativeLookSoftSkinRecoverDbResult(
        group_id=P338_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        creative_look_slot=creative_look_slot,
        creative_look_locked_by_pp_log_hlg_iauto=locked_by_mode,
        creative_look_contrast=creative_look_contrast,
        creative_look_highlights=creative_look_highlights,
        creative_look_shadows=creative_look_shadows,
        creative_look_fade=creative_look_fade,
        creative_look_saturation=creative_look_saturation,
        creative_look_sharpness=creative_look_sharpness,
        creative_look_sharpness_range=creative_look_sharpness_range,
        creative_look_clarity=creative_look_clarity,
        fx3_soft_skin_effect_present=False,
        fx6_soft_skin_effect_present=False,
        delete_scope=delete_scope,
        delete_confirm=delete_confirm,
        delete_pressing_twice=delete_pressing_twice,
        protect_scope=protect_scope,
        recover_image_db_requested=recover_image_db_requested,
        recover_image_db_slot=recover_image_db_slot,
        display_media_info_still_cap=P338_DISPLAY_MEDIA_INFO_STILL_CAP,
        slot1_tier0_vault_mutated=slot1_mutated,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 67 §§1-2): Pixel Mapping, Silent Click, Monitor & EVF
# ---------------------------------------------------------------------------
def evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
    *,
    reset_action: str = "NONE",
    # Wave 67 §1: [Auto Pixel Mapping], Manual [Pixel Mapping], Silent Mode, FX6 APR
    auto_pixel_mapping: str = "ON",
    days_since_pixel_mapping: int = 1,
    manual_pixel_mapping_requested: bool = False,
    lens_cap_attached: bool = True,
    battery_soc_pct: int = 85,
    low_battery_warning: bool = False,
    expect_manual_pm_without_reboot: bool = False,
    claimed_auto_pm_wiped_by_camera_reset: bool = False,
    claimed_usb_streaming_blocks_pixel_mapping_prm_haita: bool = False,
    tier0_dump_active: bool = True,
    unguarded_pm_calibration: bool = False,
    silent_mode: str = "OFF",
    silent_auto_pixel_mapping: str = "OFF",
    expect_zero_shutter_sound_with_silent_auto_pm_on: bool = False,
    claimed_silent_auto_pm_resists_camera_reset: bool = False,
    fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed: bool = False,
    fx6_auto_black_balance_menu_present_claimed: bool = False,
    # Wave 67 §2: Setup -> [Monitor] (NOT [Finder/Monitor]) & Dormant EVF vs FX6 VF
    exposed_monitor_items: Tuple[str, ...] = P338_MONITOR_EXACT_THREE_ITEMS,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_level: int = 0,
    display_quality: str = "STANDARD",
    body_temp_elevated: bool = False,
    expect_high_display_quality_unclamped_under_thermal: bool = False,
    monitor_flip_direction: str = "AUTO",
    claimed_monitor_3items_wiped_by_camera_reset: bool = False,
    claimed_bright_monitoring_in_setup_monitor: bool = False,
    fx3_finder_monitor_menu_present_claimed: bool = False,
    fx3_builtin_evf_present_claimed: bool = False,
    dormant_evf_menu_requested: str = "NONE",
    fx6_vf_adjust_four_subitems_present_claimed: bool = False,
) -> P338CheckGroupCPixelMapMonitorEvfResult:
    errors: List[str] = []
    warnings: List[str] = []

    if auto_pixel_mapping not in P338_VALID_ON_OFF:
        errors.append(f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: invalid auto_pixel_mapping={auto_pixel_mapping}")
    if silent_mode not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR}: invalid silent_mode={silent_mode}"
        )
    if silent_auto_pixel_mapping not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR}: invalid silent_auto_pixel_mapping={silent_auto_pixel_mapping}"
        )

    if auto_pixel_mapping == "OFF" and days_since_pixel_mapping > P338_PIXEL_MAPPING_RECOMMENDED_INTERVAL_DAYS:
        warnings.append(
            f"Auto Pixel Mapping is OFF and {days_since_pixel_mapping} days elapsed (>3-day manual execution advisory)"
        )
    if reset_action == "INITIALIZE" and auto_pixel_mapping != "ON":
        errors.append(
            f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: [Auto Pixel Mapping] ({P338_AUTO_PIXEL_MAPPING_RESID16_HEX}) "
            "must return to ON after INITIALIZE"
        )
    if claimed_auto_pm_wiped_by_camera_reset:
        errors.append(
            f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: Setup > [Auto Pixel Mapping] is Reset-immune (Initialize-only)"
        )
    if manual_pixel_mapping_requested:
        if not lens_cap_attached:
            errors.append(
                f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: manual [Pixel Mapping] ({P338_MANUAL_PIXEL_MAPPING_RESID16_HEX}) "
                "requires lens cap attached (light-detected guard)"
            )
        if low_battery_warning or battery_soc_pct < P338_PIXEL_MAPPING_MIN_BATTERY_PCT:
            errors.append(
                f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: manual [Pixel Mapping] blocked by "
                f"{P338_PIXEL_MAPPING_BATTERY_CHECK_SYMBOL} (soc={battery_soc_pct}%, low={low_battery_warning})"
            )
        if expect_manual_pm_without_reboot:
            errors.append(
                f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: manual [Pixel Mapping] triggers mandatory reboot"
            )
        if tier0_dump_active and unguarded_pm_calibration:
            errors.append(
                f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: unguarded Pixel Mapping calibration blocked during Tier-0 dump"
            )
    if expect_manual_pm_without_reboot and not manual_pixel_mapping_requested:
        errors.append(
            f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: manual [Pixel Mapping] ALWAYS forces post-execution reboot"
        )
    if claimed_usb_streaming_blocks_pixel_mapping_prm_haita:
        errors.append(
            f"{P338_GC_ERR_AUTO_OR_MANUAL_PIXEL_MAPPING}: no documented USB/streaming PRM_HAITA table gates [Pixel Mapping] in appFw.so"
        )

    # Silent Mode -> Target Function Settings -> [Auto Pixel Mapping] & FX6 APR
    shutdown_shutter_click_triggered = silent_mode == "ON" and silent_auto_pixel_mapping == "ON"
    if expect_zero_shutter_sound_with_silent_auto_pm_on and shutdown_shutter_click_triggered:
        errors.append(
            f"{P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR}: Silent Mode + Target [Auto Pixel Mapping]=ON "
            f"triggers mechanical shutter click at power-off ({P338_SILENT_AUTO_PM_SHUTTER_MUTE_SYMBOL})"
        )
    if reset_action == "CAMERA_SETTINGS_RESET" and silent_auto_pixel_mapping != "OFF":
        errors.append(
            f"{P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR}: Silent Mode Target [Auto Pixel Mapping] is Resettable "
            "and returns to OFF (Not Target) on [Camera Settings Reset]"
        )
    if (
        claimed_silent_auto_pm_resists_camera_reset
        or fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed
        or fx6_auto_black_balance_menu_present_claimed
    ):
        errors.append(
            f"{P338_GC_ERR_SILENT_AUTO_PM_SHUTTER_MUTE_OR_FX6_APR}: Silent Target [Auto Pixel Mapping] IS Resettable; "
            "FX6 uses Technical > APR > Execute and has NO auto_black_balance menu on CMOS"
        )

    # Setup -> [Monitor] (3 Reset-immune items, NOT [Finder/Monitor]) & Thermal Clamp
    if tuple(exposed_monitor_items) != P338_MONITOR_EXACT_THREE_ITEMS:
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: Setup -> [Monitor] must expose strictly 3 items "
            f"{P338_MONITOR_EXACT_THREE_ITEMS}, got {tuple(exposed_monitor_items)!r}"
        )
    if monitor_brightness_mode not in P338_MONITOR_BRIGHTNESS_MODES:
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: invalid monitor_brightness_mode={monitor_brightness_mode}"
        )
    b_lo, b_hi = P338_MONITOR_BRIGHTNESS_MANUAL_RANGE
    if not (b_lo <= monitor_brightness_level <= b_hi):
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: Monitor Brightness manual level {monitor_brightness_level} "
            f"outside [{b_lo}, {b_hi}]"
        )
    if display_quality not in P338_DISPLAY_QUALITY_MODES:
        errors.append(f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: invalid display_quality={display_quality}")
    if monitor_flip_direction not in P338_MONITOR_FLIP_MODES:
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: invalid monitor_flip_direction={monitor_flip_direction}"
        )
    thermally_clamped = body_temp_elevated and display_quality == "HIGH"
    if expect_high_display_quality_unclamped_under_thermal and body_temp_elevated:
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: [Display Quality]=High thermally clamps back to "
            "Standard when camera temperature rises"
        )
    if claimed_monitor_3items_wiped_by_camera_reset or claimed_bright_monitoring_in_setup_monitor:
        errors.append(
            f"{P338_GC_ERR_MONITOR_3ITEMS_OR_THERMAL_CLAMP}: Setup -> [Monitor] 3 items are Reset-immune; "
            "[Bright Monitoring] resides in Shooting -> [Shooting Display] / Custom Key, NOT Setup -> [Monitor]"
        )

    # Dormant EVF / Finder/Monitor & FX6 VF Adjust 4-subitem myth-busting
    if (
        fx3_finder_monitor_menu_present_claimed
        or fx3_builtin_evf_present_claimed
        or dormant_evf_menu_requested != "NONE"
        or fx6_vf_adjust_four_subitems_present_claimed
    ):
        errors.append(
            f"{P338_GC_ERR_DORMANT_EVF_OR_FX6_VF_ADJUST}: zero-EVF FX3 exposes Setup -> [Monitor] (NOT [Finder/Monitor]) "
            f"and rejects dormant EVF items {P338_DORMANT_EVF_MENU_ITEMS} (errno={P338_ERRNO_EOPNOTSUPP}); "
            "FX6 uses VF Setting + MIRROR switch (NO 4-subitem VF Adjust Backlight/Contrast/Chroma/Color Temp menu)"
        )

    return P338CheckGroupCPixelMapMonitorEvfResult(
        group_id=P338_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        auto_pixel_mapping=auto_pixel_mapping,
        manual_pixel_mapping_requested=manual_pixel_mapping_requested,
        silent_mode=silent_mode,
        silent_auto_pixel_mapping=silent_auto_pixel_mapping,
        shutdown_shutter_click_triggered=shutdown_shutter_click_triggered,
        pixel_mapping_typo_bkids=(
            P338_PIXEL_MAPPING_SONY_TYPO_NOTIFICATION_BKID,
            P338_PIXEL_MAPPING_SONY_TYPO_STATUS_BKID,
        ),
        exposed_monitor_items=tuple(exposed_monitor_items),
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_level=monitor_brightness_level,
        display_quality="STANDARD" if thermally_clamped else display_quality,
        display_quality_thermally_clamped=thermally_clamped,
        monitor_flip_direction=monitor_flip_direction,
        fx3_builtin_evf_present=False,
        fx3_finder_monitor_menu_present=False,
        fx6_vf_adjust_four_subitems_present=False,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D (Wave 67 §§3-4 & Tier-0): Recall Custom Hold, HDMI/TC/REC, H0==H3
# ---------------------------------------------------------------------------
def _verify_single_receipt(
    receipt_bytes: Optional[bytes],
    *,
    label: str,
) -> Tuple[Optional[Any], List[str]]:
    errors: List[str] = []
    if receipt_bytes is None:
        errors.append(f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing {label} 528B FX3RCPT1")
        return None, errors
    if len(receipt_bytes) != SD_RECEIPT_BYTES:
        errors.append(
            f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} length {len(receipt_bytes)} != {SD_RECEIPT_BYTES}"
        )
        return None, errors
    try:
        parsed = parse_sd_backup_receipt_bytes(receipt_bytes)
    except Exception as exc:
        errors.append(f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} parse failed ({exc})")
        return None, errors

    if not parsed.valid:
        errors.append(
            f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} integrity check failed ({parsed.errors})"
        )
    if parsed.entry_count != len(COLD_BACKUP_ITEMS):
        errors.append(
            f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} entry_count={parsed.entry_count} != {len(COLD_BACKUP_ITEMS)}"
        )
    if _is_trivial_hex64(parsed.manifest_sha256):
        errors.append(f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} trivial manifest_sha256")
    if _is_trivial_hex64(parsed.receipt_integrity_sha256):
        errors.append(
            f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} trivial receipt_integrity_sha256"
        )
    return parsed, errors


def build_simulated_phase338_tier0_receipts(
    *,
    body_serial: str = "FX3BENCH70200338",
    emmc_cid: str = "11010030303847333000a1b2c3d40338",
) -> Dict[str, Any]:
    """Synthesize deterministic dry-run dual-media 528B FX3RCPT1 receipts & 16/16 H0==H3 baselines."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE338_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE338_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "receipt_a_bytes": receipt,
        "receipt_b_bytes": bytes(receipt),
        "st_dev_a": 1001,
        "st_dev_b": 1002,
        "h0_baselines_a": dict(h0),
        "h0_baselines_b": dict(h0),
        "h3_baselines": dict(h0),
    }


def evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    reset_action: str = "NONE",
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Wave 67 §3: Hold custom keys & [Recall Custom hold 1-3] vs FX6 Push AF/AGC/Auto Iris
    recall_custom_hold_active: bool = False,
    recall_custom_hold_slot: int = 1,
    recall_custom_hold_eleven_slots: Tuple[str, ...] = P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS,
    recall_custom_hold_standalone_wb_requested: bool = False,
    fx3_recall_custom_hold_standalone_wb_present_claimed: bool = False,
    claimed_recall_custom_hold_wiped_by_camera_reset: bool = False,
    tracking_on_custom_key_focus_mode: str = "AF_C",
    tracking_on_custom_key_active: bool = False,
    fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed: bool = False,
    # Wave 67 §4: Setup -> [External Output] & Dormant 4K/2K / 24p/60p
    hdmi_resolution: str = "AUTO",
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_output_resolution: str = "1080P",
    hdmi_4k_output_rate: str = "23_98P",
    hdmi_raw_output: str = "OFF",
    hdmi_tc_output: str = "OFF",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "ON",
    ctrl_for_hdmi: str = "ON",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "OFF",
    expect_2400p_no_reboot_or_mixed_playback: bool = False,
    expect_hdmi_info_display_active_with_raw_or_hdmi_only: bool = False,
    claimed_external_output_wiped_by_camera_reset: bool = False,
    dormant_4k_2k_or_24p_60p_requested: bool = False,
    fx3_4k_2k_output_present_claimed: bool = False,
    fx3_24p_60p_output_present_claimed: bool = False,
    # Slot-1 EROFS=30 firewall & Tier-0 / Fail-Closed Redlines
    recording_media: str = "SLOT_2",
    rec_target_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    slot1_data_sector_writes: int = 0,
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
) -> P338CheckGroupDRecallHoldHdmiTcTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    # [Recall Custom hold 1-3] (Wave 67 §3)
    if recall_custom_hold_slot not in (1, 2, 3):
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: recall_custom_hold_slot must be 1..3 "
            f"(got {recall_custom_hold_slot})"
        )
    if tuple(recall_custom_hold_eleven_slots) != P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS:
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: [Recall Custom hold 1-3] must cover exact 11 slots "
            f"(is_checked_recall_custom_hold0..10), got {tuple(recall_custom_hold_eleven_slots)!r}"
        )
    if recall_custom_hold_active and (
        shoot_mode != "PHOTO" or exposure_mode not in P338_RECALL_CUSTOM_HOLD_STILL_EXPOSURE_MODES
    ):
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: [Recall Custom hold 1-3] ({P338_RECALL_CUSTOM_HOLD_UXC_RESIDS}) "
            f"is strictly Still P/A/S/M only; got shoot_mode={shoot_mode} exposure_mode={exposure_mode} "
            f"(errno={P338_ERRNO_EOPNOTSUPP})"
        )
    if recall_custom_hold_standalone_wb_requested or fx3_recall_custom_hold_standalone_wb_present_claimed:
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: [Recall Custom hold 1-3] has ZERO standalone "
            f"White Balance checkbox ({P338_RECALL_CUSTOM_HOLD_ABSENT_WB_SYMBOL} 0 hits; WB only via Drive Mode WB Bracket)"
        )
    if tracking_on_custom_key_active and (
        shoot_mode != "PHOTO" or tracking_on_custom_key_focus_mode != "AF_C"
    ):
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: [Tracking On] Hold Custom Key operates in "
            "Still AF-C only"
        )
    if claimed_recall_custom_hold_wiped_by_camera_reset or fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed:
        errors.append(
            f"{P338_GD_ERR_RECALL_CUSTOM_HOLD_SCOPE_OR_11SLOTS}: [Recall Custom hold 1-3] is Reset-immune "
            "(saved in CAMSET/*.DAT); FX6 Push AF/AGC is disabled in Cine EI/Quick & Bokeh Control=On"
        )

    # Setup -> [External Output] (Wave 67 §4)
    if hdmi_resolution not in P338_HDMI_RESOLUTIONS:
        errors.append(f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: invalid hdmi_resolution={hdmi_resolution}")
    if rec_media_dur_hdmi_output not in P338_REC_MEDIA_DUR_HDMI_MODES:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output}"
        )
    if hdmi_output_resolution not in P338_HDMI_RESOLUTIONS:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: invalid hdmi_output_resolution={hdmi_output_resolution}"
        )
    if hdmi_4k_output_rate not in P338_HDMI_4K_OUTPUT_RATES:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: invalid hdmi_4k_output_rate={hdmi_4k_output_rate}"
        )
    if hdmi_raw_output not in P338_VALID_ON_OFF or hdmi_tc_output not in P338_VALID_ON_OFF or hdmi_rec_control not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: RAW/TC/REC Control must be ON or OFF"
        )
    if hdmi_4ch_audio_output not in P338_HDMI_4CH_AUDIO_MODES:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: invalid hdmi_4ch_audio_output={hdmi_4ch_audio_output}"
        )
    if hdmi_info_display not in P338_VALID_ON_OFF or ctrl_for_hdmi not in P338_VALID_ON_OFF:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: HDMI Info Display / CTRL FOR HDMI must be ON or OFF"
        )

    if shoot_mode == "S_AND_Q" and (
        rec_media_dur_hdmi_output != "ON" or hdmi_raw_output == "ON" or hdmi_tc_output == "ON"
    ):
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: S&Q locks Rec. Media dur HDMI Output=ON, "
            "RAW Output=OFF, and disables Time Code Output"
        )
    if (
        rec_media_dur_hdmi_output == "ON"
        and (log_shooting_mode != "OFF" or picture_profile in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"))
        and hdmi_output_resolution == "2160P"
    ):
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: Log / PPLUT1..4 + Rec. Media dur HDMI Output=ON "
            "clamps HDMI Output Resolution to 1080p/1080i (2160p rejected)"
        )
    if hdmi_4k_output_rate == "24_00P" and expect_2400p_no_reboot_or_mixed_playback:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: 4K Output Set.(HDMI Only)=24.00p triggers "
            "mandatory camera reboot and isolates 24.00p/non-24.00p playback"
        )
    if hdmi_rec_control == "ON" and hdmi_tc_output != "ON":
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: HDMI [REC Control]=ON requires [Time Code Output]=ON"
        )
    if expect_hdmi_info_display_active_with_raw_or_hdmi_only and (
        rec_media_dur_hdmi_output == "OFF_HDMI_ONLY" or hdmi_raw_output == "ON"
    ):
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: [HDMI Info. Display] is temporarily forced OFF "
            "during Off(HDMI Only) or HDMI RAW Output=ON"
        )
    if claimed_external_output_wiped_by_camera_reset:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: Setup -> [External Output] settings are "
            f"Reset-immune (Initialize-only; {P338_CTRL_FOR_HDMI_SONY_TYPO_BKID})"
        )
    if dormant_4k_2k_or_24p_60p_requested or fx3_4k_2k_output_present_claimed or fx3_24p_60p_output_present_claimed:
        errors.append(
            f"{P338_GD_ERR_HDMI_OUTPUT_2400P_RECCTRL_OR_DORMANT}: [4K/2K Output] & [24p/60p Output] have 0 hits "
            f"in ilc/2210 and appFw.so (DORMANT/REMOVED, errno={P338_ERRNO_EOPNOTSUPP})"
        )

    # Slot-1 EROFS=30 Firewall when Rec. Media dur HDMI Output = ON
    if recording_media not in P338_VALID_RECORDING_MEDIA_MODES:
        errors.append(
            f"{P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS}: invalid recording_media={recording_media}"
        )
    slot1_targeted_hdmi_rec = (
        rec_media_dur_hdmi_output == "ON"
        and (rec_target_slot == 1 or recording_media in ("SLOT_1", "SIMULTANEOUS_RECORDING"))
        and slot1_contains_tier0_dump
    )
    slot1_mutated = bool(slot1_targeted_hdmi_rec or slot1_data_sector_writes != 0)
    if slot1_targeted_hdmi_rec:
        errors.append(
            f"{P338_GD_ERR_HDMI_REC_MEDIA_SLOT1_VAULT_EROFS}: [Rec. Media dur HDMI Output]=ON with target Slot 1 "
            f"would mutate Tier-0 Vault (M4ROOT/CLIP/*.MP4 / AVF_INFO) and is blocked (errno={P338_ERRNO_EROFS} EROFS)"
        )

    # Fail-closed redlines
    if (
        emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or wireless_rf_packets_emitted != 0
        or usb_packets_transmitted != 0
        or slot1_data_sector_writes != 0
        or simulated_passive_tx_bytes != 0
        or claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P338_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: non-zero telemetry or forbidden authorization claim "
            f"(emmc={emmc_write_count}, e_nd={e_nd_actuator_tx_count}, rf={wireless_rf_packets_emitted}, "
            f"usb={usb_packets_transmitted}, slot1={slot1_data_sector_writes}, passive={simulated_passive_tx_bytes})"
        )

    # Tier-0 Dual-Media 528B FX3RCPT1 & 16/16 H0 == H3 Gate
    tier0_verified = False
    receipt_mode = "NONE_AWAITING_PHYSICAL_RECEIPT"
    h0_eq_h3 = 0

    if simulate_bench_dry_run and receipt_a_path is None and receipt_b_path is None and receipt_a_bytes is None and receipt_b_bytes is None:
        sim = build_simulated_phase338_tier0_receipts()
        receipt_a_bytes = sim["receipt_a_bytes"]
        receipt_b_bytes = sim["receipt_b_bytes"]
        st_dev_a_override = sim["st_dev_a"]
        st_dev_b_override = sim["st_dev_b"]
        body_serial = sim["body_serial"]
        emmc_cid = sim["emmc_cid"]
        h0_baselines_a = sim["h0_baselines_a"]
        h0_baselines_b = sim["h0_baselines_b"]
        h3_baselines = sim["h3_baselines"]
        receipt_mode = "DRY_RUN_SIMULATED"
    elif receipt_a_path is not None or receipt_b_path is not None or receipt_a_bytes is not None or receipt_b_bytes is not None:
        receipt_mode = "PHYSICAL_DUAL_MEDIA_528B"

    if receipt_mode != "NONE_AWAITING_PHYSICAL_RECEIPT":
        st_dev_a = st_dev_a_override
        st_dev_b = st_dev_b_override
        raw_a = receipt_a_bytes
        raw_b = receipt_b_bytes

        if raw_a is None and receipt_a_path is not None:
            if not Path(receipt_a_path).is_file():
                errors.append(
                    f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_a file {receipt_a_path}"
                )
            else:
                raw_a = Path(receipt_a_path).read_bytes()
                if st_dev_a is None:
                    st_dev_a = Path(receipt_a_path).stat().st_dev
        if raw_b is None and receipt_b_path is not None:
            if not Path(receipt_b_path).is_file():
                errors.append(
                    f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_b file {receipt_b_path}"
                )
            else:
                raw_b = Path(receipt_b_path).read_bytes()
                if st_dev_b is None:
                    st_dev_b = Path(receipt_b_path).stat().st_dev

        if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
            errors.append(
                f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: model/fw mismatch "
                f"(model=0x{int(body_model_id):08x} != {TARGET_MODEL_ID_HEX}, fw={body_fw!r} != {TARGET_BODY_FW!r})"
            )
        if body_serial is not None and (
            not BODY_SERIAL_RE.match(body_serial) or body_serial in FORBIDDEN_TRIVIAL_SERIALS
        ):
            errors.append(
                f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial body_serial={body_serial!r}"
            )
        if emmc_cid is not None and (
            not HEX32_CID_RE.match(emmc_cid) or emmc_cid.lower() in FORBIDDEN_TRIVIAL_CIDS
        ):
            errors.append(
                f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial emmc_cid={emmc_cid!r}"
            )

        parsed_a, errs_a = _verify_single_receipt(raw_a, label="receipt_a")
        parsed_b, errs_b = _verify_single_receipt(raw_b, label="receipt_b")
        errors.extend(errs_a)
        errors.extend(errs_b)

        if raw_a is not None and raw_b is not None and raw_a != raw_b:
            errors.append(
                f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a != receipt_b byte mismatch"
            )
        if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
            errors.append(
                f"{P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media receipts must reside on "
                f"distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
            )

        # 16/16 H0 == H3 baseline parity
        if h0_baselines_a is None or h0_baselines_b is None or h3_baselines is None:
            if parsed_a is not None and parsed_b is not None and not errs_a and not errs_b:
                eff_serial = body_serial or "FX3BENCH70200338"
                eff_cid = emmc_cid or "11010030303847333000a1b2c3d40338"
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
            h0_eq_h3 = max(0, P338_STORAGE_SURFACE_COUNT - drifted)
        if h0_eq_h3 != P338_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 surface parity failed "
                f"({h0_eq_h3}/{P338_STORAGE_SURFACE_COUNT})"
            )

        if not any(
            e.startswith(P338_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            or e.startswith(P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)
            for e in errors
        ):
            tier0_verified = True
    else:
        if simulated_h0_h3_drifted_surfaces > 0:
            errors.append(
                f"{P338_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0/H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
            )

    return P338CheckGroupDRecallHoldHdmiTcTier0Result(
        group_id=P338_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        recall_custom_hold_active=recall_custom_hold_active,
        recall_custom_hold_slot=recall_custom_hold_slot,
        recall_custom_hold_eleven_slots=tuple(recall_custom_hold_eleven_slots),
        fx3_recall_custom_hold_standalone_wb_present=False,
        hdmi_resolution=hdmi_resolution,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_output_resolution=hdmi_output_resolution,
        hdmi_4k_output_rate=hdmi_4k_output_rate,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_tc_output=hdmi_tc_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        ctrl_for_hdmi=ctrl_for_hdmi,
        ctrl_for_hdmi_typo_bkid=P338_CTRL_FOR_HDMI_SONY_TYPO_BKID,
        fx3_4k_2k_output_present=False,
        fx3_24p_60p_output_present=False,
        recording_media=recording_media,
        rec_target_slot=rec_target_slot,
        slot1_tier0_vault_mutated=slot1_mutated,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3,
        h0_h3_surface_count=P338_STORAGE_SURFACE_COUNT,
        emmc_write_count=emmc_write_count,
        slot1_data_sector_writes=slot1_data_sector_writes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Master Preflight Orchestrator, Verifier & Markdown Renderer
# ---------------------------------------------------------------------------
def evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P338_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Group A
    drive_mode: str = "SINGLE_SHOOTING",
    cont_speed_tier: str = "HI_PLUS",
    aperture_f_number: float = 2.8,
    still_file_format: str = "RAW",
    raw_file_type: str = "COMPRESSED",
    flash_enabled: bool = False,
    self_timer_sec: int = 10,
    self_timer_cont_images: int = 3,
    hlg_still_image: str = "OFF",
    picture_profile: str = "OFF",
    log_shooting_mode: str = "OFF",
    interval_shutter_type: str = "ELECTRONIC_SHUTTER",
    expect_af_tracks_all_frames_above_f11: bool = False,
    expect_full_cont_fps_with_uncompressed_raw_or_flash: bool = False,
    claimed_drive_mode_active_in_movie_or_sq: bool = False,
    claimed_drive_mode_resists_camera_reset: bool = False,
    claimed_interval_default_mech_shutter: bool = False,
    fx6_has_still_drive_mode_menu_claimed: bool = False,
    dormant_focus_bracket_requested: bool = False,
    fx3_focus_bracket_present_claimed: bool = False,
    fx6_focus_bracket_present_claimed: bool = False,
    claimed_focus_bracket_in_ilc2210: bool = False,
    shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    dormant_shutter_type_auto_requested: bool = False,
    fx3_shutter_type_auto_present_claimed: bool = False,
    flash_sync_denominator: int = P338_FLASH_XSYNC_DENOMINATOR,
    claimed_1_320_xsync_supported: bool = False,
    e_front_curtain_shutter: str = "ON",
    efcs_active_claimed: bool = False,
    claimed_efcs_wiped_by_camera_reset: bool = False,
    long_exposure_nr: str = "ON",
    shutter_seconds: float = 0.01,
    bulb_enabled: bool = False,
    anti_flicker_shoot: bool = False,
    claimed_long_exp_nr_active_below_1s: bool = False,
    claimed_long_exp_nr_resists_reset: bool = False,
    high_iso_nr: str = "NORMAL",
    expect_high_iso_nr_modifies_arw_raw: bool = False,
    dormant_high_iso_nr_high_option_requested: bool = False,
    claimed_high_iso_nr_resists_reset: bool = False,
    fx6_noise_suppression_uses_still_nr_menu_claimed: bool = False,
    # Group B
    creative_look_shoot_mode: Optional[str] = None,
    creative_look_slot: str = "ST",
    creative_look_contrast: int = 0,
    creative_look_highlights: int = 0,
    creative_look_shadows: int = 0,
    creative_look_fade: int = 0,
    creative_look_saturation: int = 0,
    creative_look_sharpness: int = 0,
    creative_look_sharpness_range: int = 3,
    creative_look_clarity: int = 0,
    creative_look_saturation_adjusted: bool = False,
    creative_look_sharpness_range_adjusted: bool = False,
    expect_creative_look_active_under_pp_log_hlg_iauto: bool = False,
    claimed_creative_look_fade_sharpness_clarity_accept_negative: bool = False,
    claimed_creative_look_resists_camera_reset: bool = False,
    dormant_soft_skin_requested: bool = False,
    fx3_soft_skin_present_claimed: bool = False,
    fx6_soft_skin_present_claimed: bool = False,
    delete_scope: str = "THIS_IMAGE",
    delete_confirm: str = "CANCEL_FIRST",
    delete_pressing_twice: str = "OFF",
    protect_scope: str = "THIS_IMAGE",
    delete_write_requested: bool = False,
    delete_write_slot: int = 2,
    protect_write_requested: bool = False,
    protect_write_slot: int = 2,
    protected_item_delete_attempted: bool = False,
    slot_format_executed: bool = False,
    claimed_delete_confirm_wiped_by_camera_reset: bool = False,
    claimed_delete_twice_wiped_by_camera_reset: bool = False,
    expect_copy_preserves_protect: bool = False,
    recover_image_db_requested: bool = False,
    recover_image_db_slot: int = 2,
    battery_soc_pct: int = 85,
    low_battery_warning: bool = False,
    claimed_recover_db_wiped_by_reset_or_init: bool = False,
    claimed_display_media_info_mutates_media: bool = False,
    claimed_display_media_info_cap_not_40000: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    # Group C
    auto_pixel_mapping: str = "ON",
    days_since_pixel_mapping: int = 1,
    manual_pixel_mapping_requested: bool = False,
    lens_cap_attached: bool = True,
    expect_manual_pm_without_reboot: bool = False,
    claimed_auto_pm_wiped_by_camera_reset: bool = False,
    claimed_usb_streaming_blocks_pixel_mapping_prm_haita: bool = False,
    tier0_dump_active: bool = True,
    unguarded_pm_calibration: bool = False,
    silent_auto_pixel_mapping: str = "OFF",
    expect_zero_shutter_sound_with_silent_auto_pm_on: bool = False,
    claimed_silent_auto_pm_resists_camera_reset: bool = False,
    fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed: bool = False,
    fx6_auto_black_balance_menu_present_claimed: bool = False,
    exposed_monitor_items: Tuple[str, ...] = P338_MONITOR_EXACT_THREE_ITEMS,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_level: int = 0,
    display_quality: str = "STANDARD",
    body_temp_elevated: bool = False,
    expect_high_display_quality_unclamped_under_thermal: bool = False,
    monitor_flip_direction: str = "AUTO",
    claimed_monitor_3items_wiped_by_camera_reset: bool = False,
    claimed_bright_monitoring_in_setup_monitor: bool = False,
    fx3_finder_monitor_menu_present_claimed: bool = False,
    fx3_builtin_evf_present_claimed: bool = False,
    dormant_evf_menu_requested: str = "NONE",
    fx6_vf_adjust_four_subitems_present_claimed: bool = False,
    # Group D
    recall_custom_hold_active: bool = False,
    recall_custom_hold_slot: int = 1,
    recall_custom_hold_eleven_slots: Tuple[str, ...] = P338_RECALL_CUSTOM_HOLD_EXACT_ELEVEN_SLOTS,
    recall_custom_hold_standalone_wb_requested: bool = False,
    fx3_recall_custom_hold_standalone_wb_present_claimed: bool = False,
    claimed_recall_custom_hold_wiped_by_camera_reset: bool = False,
    tracking_on_custom_key_focus_mode: str = "AF_C",
    tracking_on_custom_key_active: bool = False,
    fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed: bool = False,
    hdmi_resolution: str = "AUTO",
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_output_resolution: str = "1080P",
    hdmi_4k_output_rate: str = "23_98P",
    hdmi_raw_output: str = "OFF",
    hdmi_tc_output: str = "OFF",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "ON",
    ctrl_for_hdmi: str = "ON",
    expect_2400p_no_reboot_or_mixed_playback: bool = False,
    expect_hdmi_info_display_active_with_raw_or_hdmi_only: bool = False,
    claimed_external_output_wiped_by_camera_reset: bool = False,
    dormant_4k_2k_or_24p_60p_requested: bool = False,
    fx3_4k_2k_output_present_claimed: bool = False,
    fx3_24p_60p_output_present_claimed: bool = False,
    recording_media: str = "SLOT_2",
    rec_target_slot: int = 2,
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
) -> RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport:
    donor = inspect_phase338_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        drive_mode=drive_mode,
        cont_speed_tier=cont_speed_tier,
        aperture_f_number=aperture_f_number,
        still_file_format=still_file_format,
        raw_file_type=raw_file_type,
        flash_enabled=flash_enabled,
        self_timer_sec=self_timer_sec,
        self_timer_cont_images=self_timer_cont_images,
        hlg_still_image=hlg_still_image,
        picture_profile=picture_profile,
        log_shooting_mode=log_shooting_mode,
        interval_shutter_type=interval_shutter_type,
        expect_af_tracks_all_frames_above_f11=expect_af_tracks_all_frames_above_f11,
        expect_full_cont_fps_with_uncompressed_raw_or_flash=expect_full_cont_fps_with_uncompressed_raw_or_flash,
        claimed_drive_mode_active_in_movie_or_sq=claimed_drive_mode_active_in_movie_or_sq,
        claimed_drive_mode_resists_camera_reset=claimed_drive_mode_resists_camera_reset,
        claimed_interval_default_mech_shutter=claimed_interval_default_mech_shutter,
        fx6_has_still_drive_mode_menu_claimed=fx6_has_still_drive_mode_menu_claimed,
        dormant_focus_bracket_requested=dormant_focus_bracket_requested,
        fx3_focus_bracket_present_claimed=fx3_focus_bracket_present_claimed,
        fx6_focus_bracket_present_claimed=fx6_focus_bracket_present_claimed,
        claimed_focus_bracket_in_ilc2210=claimed_focus_bracket_in_ilc2210,
        shutter_type=shutter_type,
        silent_mode=silent_mode,
        dormant_shutter_type_auto_requested=dormant_shutter_type_auto_requested,
        fx3_shutter_type_auto_present_claimed=fx3_shutter_type_auto_present_claimed,
        flash_sync_denominator=flash_sync_denominator,
        claimed_1_320_xsync_supported=claimed_1_320_xsync_supported,
        e_front_curtain_shutter=e_front_curtain_shutter,
        efcs_active_claimed=efcs_active_claimed,
        claimed_efcs_wiped_by_camera_reset=claimed_efcs_wiped_by_camera_reset,
        long_exposure_nr=long_exposure_nr,
        shutter_seconds=shutter_seconds,
        bulb_enabled=bulb_enabled,
        anti_flicker_shoot=anti_flicker_shoot,
        claimed_long_exp_nr_active_below_1s=claimed_long_exp_nr_active_below_1s,
        claimed_long_exp_nr_resists_reset=claimed_long_exp_nr_resists_reset,
        high_iso_nr=high_iso_nr,
        expect_high_iso_nr_modifies_arw_raw=expect_high_iso_nr_modifies_arw_raw,
        dormant_high_iso_nr_high_option_requested=dormant_high_iso_nr_high_option_requested,
        claimed_high_iso_nr_resists_reset=claimed_high_iso_nr_resists_reset,
        fx6_noise_suppression_uses_still_nr_menu_claimed=fx6_noise_suppression_uses_still_nr_menu_claimed,
    )

    gb = evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb(
        shoot_mode=creative_look_shoot_mode if creative_look_shoot_mode is not None else shoot_mode,
        exposure_mode=exposure_mode,
        reset_action=reset_action,
        creative_look_slot=creative_look_slot,
        picture_profile=picture_profile,
        log_shooting_mode=log_shooting_mode,
        hlg_still_image=hlg_still_image,
        creative_look_contrast=creative_look_contrast,
        creative_look_highlights=creative_look_highlights,
        creative_look_shadows=creative_look_shadows,
        creative_look_fade=creative_look_fade,
        creative_look_saturation=creative_look_saturation,
        creative_look_sharpness=creative_look_sharpness,
        creative_look_sharpness_range=creative_look_sharpness_range,
        creative_look_clarity=creative_look_clarity,
        creative_look_saturation_adjusted=creative_look_saturation_adjusted,
        creative_look_sharpness_range_adjusted=creative_look_sharpness_range_adjusted,
        expect_creative_look_active_under_pp_log_hlg_iauto=expect_creative_look_active_under_pp_log_hlg_iauto,
        claimed_creative_look_fade_sharpness_clarity_accept_negative=claimed_creative_look_fade_sharpness_clarity_accept_negative,
        claimed_creative_look_resists_camera_reset=claimed_creative_look_resists_camera_reset,
        dormant_soft_skin_requested=dormant_soft_skin_requested,
        fx3_soft_skin_present_claimed=fx3_soft_skin_present_claimed,
        fx6_soft_skin_present_claimed=fx6_soft_skin_present_claimed,
        delete_scope=delete_scope,
        delete_confirm=delete_confirm,
        delete_pressing_twice=delete_pressing_twice,
        protect_scope=protect_scope,
        delete_write_requested=delete_write_requested,
        delete_write_slot=delete_write_slot,
        protect_write_requested=protect_write_requested,
        protect_write_slot=protect_write_slot,
        protected_item_delete_attempted=protected_item_delete_attempted,
        slot_format_executed=slot_format_executed,
        claimed_delete_confirm_wiped_by_camera_reset=claimed_delete_confirm_wiped_by_camera_reset,
        claimed_delete_twice_wiped_by_camera_reset=claimed_delete_twice_wiped_by_camera_reset,
        expect_copy_preserves_protect=expect_copy_preserves_protect,
        recover_image_db_requested=recover_image_db_requested,
        recover_image_db_slot=recover_image_db_slot,
        battery_soc_pct=battery_soc_pct,
        low_battery_warning=low_battery_warning,
        claimed_recover_db_wiped_by_reset_or_init=claimed_recover_db_wiped_by_reset_or_init,
        claimed_display_media_info_mutates_media=claimed_display_media_info_mutates_media,
        claimed_display_media_info_cap_not_40000=claimed_display_media_info_cap_not_40000,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_data_sector_writes=slot1_data_sector_writes,
    )

    gc = evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf(
        reset_action=reset_action,
        auto_pixel_mapping=auto_pixel_mapping,
        days_since_pixel_mapping=days_since_pixel_mapping,
        manual_pixel_mapping_requested=manual_pixel_mapping_requested,
        lens_cap_attached=lens_cap_attached,
        battery_soc_pct=battery_soc_pct,
        low_battery_warning=low_battery_warning,
        expect_manual_pm_without_reboot=expect_manual_pm_without_reboot,
        claimed_auto_pm_wiped_by_camera_reset=claimed_auto_pm_wiped_by_camera_reset,
        claimed_usb_streaming_blocks_pixel_mapping_prm_haita=claimed_usb_streaming_blocks_pixel_mapping_prm_haita,
        tier0_dump_active=tier0_dump_active,
        unguarded_pm_calibration=unguarded_pm_calibration,
        silent_mode=silent_mode,
        silent_auto_pixel_mapping=silent_auto_pixel_mapping,
        expect_zero_shutter_sound_with_silent_auto_pm_on=expect_zero_shutter_sound_with_silent_auto_pm_on,
        claimed_silent_auto_pm_resists_camera_reset=claimed_silent_auto_pm_resists_camera_reset,
        fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed=fx6_uses_setup_auto_pixel_mapping_instead_of_apr_claimed,
        fx6_auto_black_balance_menu_present_claimed=fx6_auto_black_balance_menu_present_claimed,
        exposed_monitor_items=exposed_monitor_items,
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_level=monitor_brightness_level,
        display_quality=display_quality,
        body_temp_elevated=body_temp_elevated,
        expect_high_display_quality_unclamped_under_thermal=expect_high_display_quality_unclamped_under_thermal,
        monitor_flip_direction=monitor_flip_direction,
        claimed_monitor_3items_wiped_by_camera_reset=claimed_monitor_3items_wiped_by_camera_reset,
        claimed_bright_monitoring_in_setup_monitor=claimed_bright_monitoring_in_setup_monitor,
        fx3_finder_monitor_menu_present_claimed=fx3_finder_monitor_menu_present_claimed,
        fx3_builtin_evf_present_claimed=fx3_builtin_evf_present_claimed,
        dormant_evf_menu_requested=dormant_evf_menu_requested,
        fx6_vf_adjust_four_subitems_present_claimed=fx6_vf_adjust_four_subitems_present_claimed,
    )

    gd = evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        body_model_id=body_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        recall_custom_hold_active=recall_custom_hold_active,
        recall_custom_hold_slot=recall_custom_hold_slot,
        recall_custom_hold_eleven_slots=recall_custom_hold_eleven_slots,
        recall_custom_hold_standalone_wb_requested=recall_custom_hold_standalone_wb_requested,
        fx3_recall_custom_hold_standalone_wb_present_claimed=fx3_recall_custom_hold_standalone_wb_present_claimed,
        claimed_recall_custom_hold_wiped_by_camera_reset=claimed_recall_custom_hold_wiped_by_camera_reset,
        tracking_on_custom_key_focus_mode=tracking_on_custom_key_focus_mode,
        tracking_on_custom_key_active=tracking_on_custom_key_active,
        fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed=fx6_push_af_agc_allowed_in_cine_ei_or_bokeh_claimed,
        hdmi_resolution=hdmi_resolution,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_output_resolution=hdmi_output_resolution,
        hdmi_4k_output_rate=hdmi_4k_output_rate,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_tc_output=hdmi_tc_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        ctrl_for_hdmi=ctrl_for_hdmi,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        expect_2400p_no_reboot_or_mixed_playback=expect_2400p_no_reboot_or_mixed_playback,
        expect_hdmi_info_display_active_with_raw_or_hdmi_only=expect_hdmi_info_display_active_with_raw_or_hdmi_only,
        claimed_external_output_wiped_by_camera_reset=claimed_external_output_wiped_by_camera_reset,
        dormant_4k_2k_or_24p_60p_requested=dormant_4k_2k_or_24p_60p_requested,
        fx3_4k_2k_output_present_claimed=fx3_4k_2k_output_present_claimed,
        fx3_24p_60p_output_present_claimed=fx3_24p_60p_output_present_claimed,
        recording_media=recording_media,
        rec_target_slot=rec_target_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        usb_packets_transmitted=usb_packets_transmitted,
        slot1_data_sector_writes=slot1_data_sector_writes,
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
        overall_status = P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE
        go_no_go = P338_GO_NO_GO_BLOCKED_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_FAILURE
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED
        go_no_go = P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED
    else:
        overall_status = P338_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    slot1_mutated = bool(gb.slot1_tier0_vault_mutated or gd.slot1_tier0_vault_mutated)

    report = RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport(
        schema_version=P338_SCHEMA,
        phase_version=P338_VERSION,
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
        fx3_focus_bracket_present=False,
        fx6_focus_bracket_present=False,
        fx3_shutter_type_auto_present=False,
        fx3_soft_skin_effect_present=False,
        fx6_soft_skin_effect_present=False,
        fx3_builtin_evf_present=False,
        fx3_finder_monitor_menu_present=False,
        fx3_recall_custom_hold_standalone_wb_present=False,
        fx3_4k_2k_output_present=False,
        fx3_24p_60p_output_present=False,
        emmc_write_count=PHASE338_SLOT1_DATA_SECTOR_WRITES,
        e_nd_actuator_tx_count=PHASE338_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE338_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE338_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE338_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE338_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE338_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE338_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport(
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


def run_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
    **kwargs: Any,
) -> RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport:
    return evaluate_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_preflight(
        **kwargs
    )


def verify_phase338_report(
    payload: Union[
        Mapping[str, Any],
        RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport,
    ],
) -> Phase338ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P338_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P338_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P338_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_338_VALID_GO_NO_GO_VALUES:
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
        "fx3_focus_bracket_present",
        "fx6_focus_bracket_present",
        "fx3_shutter_type_auto_present",
        "fx3_soft_skin_effect_present",
        "fx6_soft_skin_effect_present",
        "fx3_builtin_evf_present",
        "fx3_finder_monitor_menu_present",
        "fx3_recall_custom_hold_standalone_wb_present",
        "fx3_4k_2k_output_present",
        "fx3_24p_60p_output_present",
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
        P338_GO_NO_GO_DRIVE_FOCUSBRACKET_EFCS_CREATIVELOOK_PIXELMAP_MONITOR_RECALLHOLD_HDMI_TC_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase338ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase338_markdown(
    report: RealHwDriveFocusBracketEfcsCreativeLookPixelMapMonitorRecallHoldHdmiTcReport,
) -> str:
    lines = [
        f"# Phase 338 — 17th Physical Bench Readiness Preflight (`{report.schema_version}`)",
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
        f"`rf_pkts={report.rf_packets_transmitted}`, `usb_pkts={report.usb_packets_transmitted}`, "
        f"`slot1_writes={report.slot1_data_sector_writes}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"drive_mode=`{report.check_group_a.drive_mode}` (Hi+ 10fps / >F11 1st-frame AF lock), "
        f"focus_bracket=`{report.check_group_a.fx3_focus_bracket_present}/{report.check_group_a.fx6_focus_bracket_present}` (100% dormant `EOPNOTSUPP=95`), "
        f"shutter_type=`{report.check_group_a.shutter_type}` (no `Auto`, `1/{report.check_group_a.flash_xsync_denominator} s` X-Sync), "
        f"efcs=`{report.check_group_a.e_front_curtain_shutter}` (`{report.check_group_a.efcs_elf_typo_bkid}`, Reset-immune), "
        f"long_exp_nr=`{report.check_group_a.long_exposure_nr}`, high_iso_nr=`{report.check_group_a.high_iso_nr}`",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"creative_look=`{report.check_group_b.creative_look_slot}` (10 presets + Custom 1..6; `Fade/Sharpness/Clarity` `0..9`), "
        f"soft_skin=`{report.check_group_b.fx3_soft_skin_effect_present}/{report.check_group_b.fx6_soft_skin_effect_present}` (dormant), "
        f"recover_image_db=`{report.check_group_b.recover_image_db_requested}` (`Slot 1 EROFS=30` firewall; `Display Media Info.` 40,000 cap)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"auto_pixel_mapping=`{report.check_group_c.auto_pixel_mapping}` (typos `{report.check_group_c.pixel_mapping_typo_bkids}`), "
        f"silent_auto_pm=`{report.check_group_c.silent_auto_pixel_mapping}`, "
        f"monitor_items=`{report.check_group_c.exposed_monitor_items}` (`Setup -> [Monitor]` 3 Reset-immune items; NOT `[Finder/Monitor]`), "
        f"evf=`{report.check_group_c.fx3_builtin_evf_present}` (dormant `EOPNOTSUPP=95`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"recall_custom_hold_wb=`{report.check_group_d.fx3_recall_custom_hold_standalone_wb_present}` (Still `P/A/S/M` 11 slots, zero WB checkbox), "
        f"rec_media_dur_hdmi=`{report.check_group_d.rec_media_dur_hdmi_output}`, "
        f"4k_rate=`{report.check_group_d.hdmi_4k_output_rate}` (`24.00p` reboot), "
        f"tc_out=`{report.check_group_d.hdmi_tc_output}`, rec_ctrl=`{report.check_group_d.hdmi_rec_control}`, "
        f"ctrl_for_hdmi=`{report.check_group_d.ctrl_for_hdmi}` (`{report.check_group_d.ctrl_for_hdmi_typo_bkid}`), "
        f"dormant_4k2k_24p60p=`{report.check_group_d.fx3_4k_2k_output_present}/{report.check_group_d.fx3_24p_60p_output_present}`",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
