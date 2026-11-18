"""Phase 358 Milestone — 22nd Physical Bench Readiness Verifier (`22/22` Verifiers).

Implements `preflight-metering-pplut-ibis-customkey-diffset8-gammadisp-and-usblan-cleaning`
aligned with Global Sony Real-Hardware Empirical Intelligence Waves 75-76 across Check
Groups A-D and the mandatory `16/16 H0 == H3` dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (Wave 75: `[Metering Mode]` 6 modes [`Multi` locked under CIZ/Digital
  Zoom], `[Face Priority in Multi Metering]` [`BKID_APP_setting_face_detection_in_multi`],
  `[Spot Metering Point]`, Still-only Reset-resistant `[AEL w/ Shutter]`, and
  `[Exposure step]` `0.3EV`/`0.5EV` Reset-resistant [`Not available` under
  `[Camera Settings Reset]`, `[Initialize]`-only, `[Shutter Angle]` immune — Wave 75 erratum
  on G96] vs `ILME-FX6` `Shooting > Auto Exposure > Level` `-3.0..+3.0` in `0.25` steps
  [25 steps, disproving `-2.0..+2.0EV` rumor] + `Speed -99..+99` + `Detect Window 1..6/Custom`;
  `[Picture Profile]` index resets to `PP11` & `PPLUT1..4` [Movie-only baked LUTs forcing
  `1080p` internal-rec HDMI] reset under BOTH Reset & Initialize, whereas `PP1..11` internal
  parameters survive BOTH Reset & Initialize; `[Manage User LUTs]` `User1..16` [17/33-pt `.cube`
  `<=63` chars from `/Private/Sony/PRO/LUT` SD or `/Sony/PRO/LUT` CFexpress-A] + MP4
  `[Embed LUT File]` [no MXF on FX3, locked `Off` on SD/SDHC] vs `FX6` 16 UI `User` LUTs
  [50-slot internal buffer] & 4-channel `MLUT`).
- **Check Group B** (Wave 75: FX3 5-axis IBIS `[SteadyShot]` [`Active ~1.1x`/`Standard`/`Off`,
  disabled at `120p`, `RAW=On`, `De-Squeeze!=Off`; Catalyst Gyro requires `Off` or `Active`
  and excludes `120p`/`S&Q`] + exact 47-entry manual focal length table [`8mm..1000mm`] &
  dormant `Dynamic/Intelligent/Super Active` vs `FX6` zero physical IBIS
  [`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`, optical OSS only]; Playback 5 zero-write
  Reset-resistant items [`display_rotatiton` typo] + Movie `17-char` `Cam ID + Reel#` stem
  [`C999->D001` rollover] vs `37-char` `[Title Name Settings]` [`4..46` `Title Prefix` MXF on
  FX6], and Tier-0 `Slot 1` `EROFS (errno 30)` firewall on `[Create New Folder]` /
  `[Forced File No. Reset]` / `[Select REC Folder]` / `[Series Counter Reset]`).
- **Check Group C** (Wave 76: `XLR-H1` handle has `0` assignable custom buttons, `0` handle
  REC button, and `0` handle dials; FX3 3 custom domains: Still [`16` controls, `Follow
  Custom` except `MOVIE Button`], Movie [`16` controls, factory `C1=L.PressAv`, `C2=WB`,
  `C3=L.PressISO`, `C4=Not set`, `C5=Focus Magnifier`, `C6=Movie Shooting`, `Down=L.PressTv`],
  and Playback [`7` controls skipping `C4=Delete` and adding `Fn Button`]; dormant Alpha
  symbols [`ael_button`, `moviel_product_showcase_set_button` typo] unexposed;
  `[Different Set for Still/Mv]` exact 8 items [`Common->Separate` `Custom WB` Still-only;
  `Separate->Common` preserves Still `Aperture`/`Shutter Speed`/`Custom WB`;
  `[Picture Profile]` checkbox survives BOTH `[Camera Settings Reset]` and `[Initialize]`];
  `[Gamma Display Assist]` [dormant `S-Log2` unexposed on FX3; never applied to HDMI/TV]
  hard-locked `Off` when `[Log Shooting] != Off` [handed off to `[Display LUT]` + `[Select LUT]`,
  except Still in Log] vs `FX6` zero UI `Gamma Display Assist` & 4-way `MLUT`).
- **Check Group D** (Wave 76: `USB-LAN` [`libWiredLanResource.so`/`dhcpcd`, mutually exclusive
  with Multi/Micro USB & Wi-Fi; NOT blocked by `[Airplane Mode]=On`], `[Access Authen.
  Settings]=On` default [SSH + PTP-IP], Ver. 7.00+ disabled `[Security(IPsec)]` [and `0` FX6
  IPsec UI bindings], and `[Airplane Mode]=On` preserved across `[Reset Network Set.]` and
  reset to `Off` ONLY by `[Initialize]`; `[Sensor Cleaning]` [`>=51%` battery gate + physical
  power-switch off `_g 0x6221`] vs dormant `[Anti-dust Function]` & `[Shutter When Pwr OFF]`
  [`0` exposed UI items on FX3] + front `#5` `[IR Remote Ctrl]` + Still-only `[Auto Review]` vs
  `FX6` `APR`, `2.5mm LANC`, and `Rec Review`; plus `528 B FX3RCPT1` receipt validation &
  `16/16 H0 == H3` immutability gate).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

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

P358_VERSION = "phase358_v1"
PHASE358_VERSION = P358_VERSION
PHASE_358_VERSION = P358_VERSION

P358_SCHEMA = (
    "realhw_preflight22_metering_pplut_ibis_customkey_diffset8_gammadisp_usblan_cleaning_v1"
)
P358_SCHEMA_VERSION = P358_SCHEMA
PHASE_358_SCHEMA = P358_SCHEMA
REALHW_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_USBLAN_CLEANING_SCHEMA = P358_SCHEMA

P358_SONY_HELP_GUIDE_ID = "ilc/2210"
P358_STORAGE_SURFACE_COUNT = 16
P358_HEADER_READ_BYTES = 64

P358_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED = (
    "READONLY_PREFLIGHT22_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED"
)
P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE = (
    "BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE"
)
PHASE_358_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED,
    P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE,
)

P358_CHECK_GROUP_A_ID = "p358_ga_metering_expstep_erratum_pp11_pplut4_userlut"
P358_CHECK_GROUP_B_ID = "p358_gb_ibis_47focal_pb_readonly_camid_reel_37title_erofs"
P358_CHECK_GROUP_C_ID = "p358_gc_xlrh1_zero_keys_diffset8_gammadisp_slog2_mlut"
P358_CHECK_GROUP_D_ID = "p358_gd_usblan_auth_ipsec_airplane_cleaning_tier0"
PHASE_358_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P358_CHECK_GROUP_A_ID,
    P358_CHECK_GROUP_B_ID,
    P358_CHECK_GROUP_C_ID,
    P358_CHECK_GROUP_D_ID,
)

# Errno constants
P358_ERRNO_EPERM = 1
P358_ERRNO_EBUSY = 16
P358_ERRNO_EINVAL = 22
P358_ERRNO_EROFS = 30
P358_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE358_EMMC_WRITE_COUNT = 0
PHASE358_E_ND_ACTUATOR_TX_COUNT = 0
PHASE358_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE358_SLOT1_DATA_SECTOR_WRITES = 0
PHASE358_USB_PACKETS_TRANSMITTED = 0
PHASE358_PASSIVE_TX_BYTES_EMITTED = 0
PHASE358_RAW_FIRMWARE_BYTES_LEAKED = 0

P358_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P358_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P358_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI")
P358_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P358_VALID_DESQUEEZE_MODES: Tuple[str, ...] = ("OFF", "1.33X", "1.65X", "2.0X")
P358_VALID_MEDIA_TYPES: Tuple[str, ...] = ("CFEXPRESS_A", "SDXC", "SDHC", "SD")

# ---------------------------------------------------------------------------
# Wave 75 Group A Constants: Metering, Exp Step Erratum, PP1..11/PPLUT1..4, LUT
# ---------------------------------------------------------------------------

P358_METERING_MODES: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT_STANDARD",
    "SPOT_LARGE",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
P358_METERING_MODE_DEFAULT = "MULTI"
P358_FACE_PRIORITY_MULTI_BKID = "BKID_APP_setting_face_detection_in_multi"
P358_SPOT_METERING_POINT_MODES: Tuple[str, ...] = ("CENTER", "FOCUS_POINT_LINK")
P358_SPOT_METERING_POINT_DEFAULT = "CENTER"
P358_VALID_FOCUS_AREAS: Tuple[str, ...] = (
    "WIDE",
    "ZONE",
    "CENTER_FIX",
    "SPOT_S",
    "SPOT_M",
    "SPOT_L",
    "EXPAND_SPOT",
    "TRACKING",
)
P358_FOCUS_AREAS_FORCING_SPOT_CENTER: Tuple[str, ...] = ("WIDE", "ZONE", "CENTER_FIX")
P358_AEL_W_SHUTTER_MODES: Tuple[str, ...] = ("AUTO", "ON", "OFF")
P358_AEL_W_SHUTTER_DEFAULT = "AUTO"
P358_EXPOSURE_STEP_MODES: Tuple[str, ...] = ("0.3EV", "0.5EV")
P358_EXPOSURE_STEP_DEFAULT = "0.3EV"
P358_EXPOSURE_STEP_RESISTS_CAMERA_RESET = True
P358_EXPOSURE_STEP_AFFECTS_SHUTTER_ANGLE = False

P358_FX6_AE_MODES: Tuple[str, ...] = ("BACKLIGHT", "STANDARD", "SPOTLIGHT")
P358_FX6_AE_LEVEL_MIN = -3.0
P358_FX6_AE_LEVEL_MAX = 3.0
P358_FX6_AE_LEVEL_STEP = 0.25
P358_FX6_AE_LEVEL_STEP_COUNT = 25
P358_FX6_AE_SPEED_MIN = -99
P358_FX6_AE_SPEED_MAX = 99
P358_FX6_DETECT_WINDOW_MODES: Tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "CUSTOM")
P358_FX6_DETECT_WINDOW_WIDTH_MIN = 40
P358_FX6_DETECT_WINDOW_WIDTH_MAX = 999
P358_FX6_DETECT_WINDOW_WIDTH_DEFAULT = 500

P358_PP_BASE_PROFILES: Tuple[str, ...] = tuple(f"PP{i}" for i in range(1, 12))
P358_PPLUT_PROFILES: Tuple[str, ...] = tuple(f"PPLUT{i}" for i in range(1, 5))
P358_PICTURE_PROFILE_OPTIONS: Tuple[str, ...] = (
    ("OFF",) + P358_PP_BASE_PROFILES + P358_PPLUT_PROFILES
)
P358_PICTURE_PROFILE_DEFAULT = "PP11"
P358_PPLUT_FORCED_INTERNAL_REC_HDMI_RESOLUTION = "1080P"

P358_USER_LUT_SLOT_MAX = 16
P358_SELECT_LUT_OPTIONS: Tuple[str, ...] = (
    "S_LOG3",
    "S709",
    "709_800PCT",
) + tuple(f"USER{i}" for i in range(1, P358_USER_LUT_SLOT_MAX + 1))
P358_SELECT_LUT_DEFAULT = "S709"
P358_USER_LUT_CUBE_POINTS: Tuple[int, ...] = (17, 33)
P358_USER_LUT_MAX_FILENAME_BYTES = 63
P358_USER_LUT_SD_DIR = "/Private/Sony/PRO/LUT"
P358_USER_LUT_CFEA_DIR = "/Sony/PRO/LUT"
P358_EMBED_LUT_FILE_MENU_PATH = (
    "Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]"
)
P358_EMBED_LUT_CONTAINER = "MP4"
P358_FX3_MXF_SUPPORTED = False
P358_FX3_SIDECAR_CUBE_EMITTED = False
P358_FX6_USER_LUT_UI_SLOTS = 16
P358_FX6_USER_LUT_INTERNAL_BUFFER_SLOTS = 50
P358_FX6_MLUT_CHANNELS: Tuple[str, ...] = (
    "INTERNAL_REC",
    "MONITOR_OUT_SDI_HDMI",
    "LCD_VF",
    "PROXY_STREAM",
)

# ---------------------------------------------------------------------------
# Wave 75 Group B Constants: IBIS 47-Entry Focal Table, Playback, File/Slot1
# ---------------------------------------------------------------------------

P358_STEADYSHOT_MENU_PATH = "Shooting -> [Image Stabilization]"
P358_STEADYSHOT_MOVIE_MODES: Tuple[str, ...] = ("ACTIVE", "STANDARD", "OFF")
P358_STEADYSHOT_MOVIE_DEFAULT = "STANDARD"
P358_STEADYSHOT_ACTIVE_CROP_FACTOR = 1.1
P358_STEADYSHOT_STILL_MODES: Tuple[str, ...] = ("ON", "OFF")
P358_STEADYSHOT_STILL_DEFAULT = "ON"
P358_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = ("AUTO", "MANUAL")
P358_STEADYSHOT_ADJUST_DEFAULT = "AUTO"
P358_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM = 8
P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM: Tuple[int, ...] = (
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    24,
    25,
    28,
    30,
    32,
    35,
    40,
    45,
    50,
    55,
    60,
    70,
    75,
    80,
    85,
    90,
    100,
    105,
    120,
    135,
    150,
    180,
    200,
    210,
    250,
    300,
    350,
    400,
    450,
    500,
    600,
    800,
    1000,
)
P358_DORMANT_STEADYSHOT_MODES: Tuple[str, ...] = (
    "DYNAMIC_ACTIVE",
    "INTELLIGENT_ACTIVE",
    "SUPER_ACTIVE",
)
P358_FX6_BODY_IBIS_COUNT = 0
P358_FX6_IBIS_UNSUPPORTED_SYMBOL = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"

P358_PLAYBACK_5_READONLY_ITEMS: Tuple[str, ...] = (
    "IMAGE_INDEX",
    "DISPLAY_ROTATION",
    "FOCUS_FRAME_DISPLAY",
    "CONT_PB_FOR_INTERVAL",
    "PLAY_SPEED_FOR_INTERVAL",
)
P358_IMAGE_INDEX_OPTIONS: Tuple[str, ...] = ("9_IMAGES", "25_IMAGES")
P358_IMAGE_INDEX_DEFAULT = "9_IMAGES"
P358_DISPLAY_ROTATION_OPTIONS: Tuple[str, ...] = ("AUTO", "MANUAL", "OFF")
P358_DISPLAY_ROTATION_DEFAULT = "AUTO"
P358_DISPLAY_ROTATION_BKID_TYPO = "BKID_APP_setting_display_rotatiton"
P358_PLAY_SPEED_MIN = 1
P358_PLAY_SPEED_MAX = 9
P358_PLAY_SPEED_DEFAULT = 5

P358_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "STANDARD",
    "CAM_ID_REEL",
    "TITLE",
    "DATE_TITLE",
    "TITLE_DATE",
)
P358_FILE_NAME_FORMAT_DEFAULT = "STANDARD"
P358_MOVIE_CAMID_REEL_STEM_LEN = 17
P358_TITLE_NAME_MAX_CHARS = 37
P358_TITLE_NAME_DEFAULT = "C"
P358_FX6_TITLE_PREFIX_MIN_CHARS = 4
P358_FX6_TITLE_PREFIX_MAX_CHARS = 46
P358_FX6_CLIP_PATH_TEMPLATE = "/XDROOT/Clip/*.MXF"

# ---------------------------------------------------------------------------
# Wave 76 Group C Constants: XLR-H1, Custom Key 3 Domains, DiffSet 8, Gamma Disp
# ---------------------------------------------------------------------------

P358_XLR_H1_ASSIGNABLE_BUTTON_COUNT = 0
P358_XLR_H1_REC_BUTTON_COUNT = 0
P358_XLR_H1_DIAL_COUNT = 0

P358_STILL_CUSTOM_CONTROLS: Tuple[str, ...] = (
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "MULTI_SLC_CENTER",
    "CENTER",
    "LEFT",
    "RIGHT",
    "DOWN",
    "MOVIE_BUTTON",
    "FOCUS_HOLD",
)
P358_MOVIE_CUSTOM_FACTORY_DEFAULTS: Dict[str, str] = {
    "FRONT_DIAL": "APERTURE",
    "REAR_DIAL": "ISO_EI",
    "CONTROL_WHEEL": "SHUTTER_SPEED",
    "C1": "LPRESS_AV_AUTO_MANUAL",
    "C2": "WHITE_BALANCE",
    "C3": "LPRESS_ISO_AUTO_MANUAL",
    "C4": "NOT_SET",
    "C5": "FOCUS_MAGNIFIER",
    "C6": "MOVIE_SHOOTING",
    "MULTI_SLC_CENTER": "FOCUS_STANDARD",
    "CENTER": "NOT_SET",
    "LEFT": "ZEBRA_DISPLAY_SELECT",
    "RIGHT": "PEAKING_DISPLAY_SELECT",
    "DOWN": "LPRESS_TV_AUTO_MANUAL",
    "MOVIE_BUTTON": "MOVIE_SHOOTING",
    "FOCUS_HOLD": "FOCUS_HOLD",
}
P358_PLAYBACK_CUSTOM_CONTROLS: Tuple[str, ...] = (
    "C1",
    "C2",
    "C3",
    "C5",
    "C6",
    "MOVIE_BUTTON",
    "FN_BUTTON",
)
P358_STILL_CUSTOM_CONTROL_COUNT = len(P358_STILL_CUSTOM_CONTROLS)
P358_MOVIE_CUSTOM_CONTROL_COUNT = len(P358_MOVIE_CUSTOM_FACTORY_DEFAULTS)
P358_PLAYBACK_CUSTOM_CONTROL_COUNT = len(P358_PLAYBACK_CUSTOM_CONTROLS)
P358_DORMANT_CUSTOM_KEY_SYMBOLS: Tuple[str, ...] = (
    "ael_button",
    "af_on_button",
    "c_button",
    "rear_dial_l",
    "rear_dial_r",
    "lensring_custom",
    "moviel_product_showcase_set_button",
    "pb_fn_send_to_smartphone_button",
)

P358_DIFF_SET_EXACT_8_ITEMS: Tuple[str, ...] = (
    "APERTURE",
    "SHUTTER_SPEED",
    "ISO",
    "EXPOSURE_COMP",
    "METERING_MODE",
    "WHITE_BALANCE",
    "PICTURE_PROFILE",
    "FOCUS_MODE",
)
P358_VALID_SHUTTER_MODES: Tuple[str, ...] = ("SPEED", "ANGLE")
P358_FX6_ASSIGNABLE_BUTTON_LABELS: Tuple[str, ...] = tuple(f"<{i}>" for i in range(1, 10))
P358_FX6_STILL_MOVIE_SPLIT_SUPPORTED = False

P358_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    "AUTO",
    "SLOG3_TO_709_800",
    "HLG_BT2020",
    "HLG_709",
)
P358_GAMMA_DISP_ASSIST_TYPE_DEFAULT = "AUTO"
P358_GAMMA_DISP_ASSIST_HDMI_PIXEL_COUNT = 0
P358_FX3_GAMMA_ASSIST_SLOG2_EXPOSED = False
P358_FX6_GAMMA_DISP_ASSIST_UI_COUNT = 0

# ---------------------------------------------------------------------------
# Wave 76 Group D Constants: USB-LAN, Access Authen., IPsec, Airplane, Cleaning
# ---------------------------------------------------------------------------

P358_USB_LAN_LIBS: Tuple[str, ...] = ("libWiredLanResource.so", "libNetServiceEther.so")
P358_USB_LAN_KERNEL_MODULES: Tuple[str, ...] = (
    "usbnet.ko",
    "cdc_ncm",
    "cdc_ether",
    "r8152",
    "asix",
    "ax88179_178a",
)
P358_USB_LAN_IP_MODES: Tuple[str, ...] = ("AUTO", "MANUAL")
P358_USB_LAN_MANUAL_FIELD_MAX_CHARS = 15
P358_ACCESS_AUTHEN_DEFAULT = "ON"
P358_ACCESS_AUTHEN_PROTOCOLS = "SSH_AND_PTP_IP"
P358_ACCESS_AUTHEN_USER_MAX_CHARS = 16
P358_ACCESS_AUTHEN_PASS_MIN_CHARS = 8
P358_ACCESS_AUTHEN_PASS_MAX_CHARS = 16
P358_IPSEC_MIN_DISABLED_FW_MAJOR = 7
P358_FX6_IPSEC_UI_BINDING_COUNT = 0

P358_SENSOR_CLEANING_MIN_BATTERY_PCT = 51
P358_FX3_ANTI_DUST_UI_COUNT = 0
P358_FX3_SHUTTER_WHEN_PWR_OFF_UI_COUNT = 0
P358_AUTO_REVIEW_MODES: Tuple[str, ...] = ("OFF", "2_SEC", "5_SEC", "10_SEC")
P358_AUTO_REVIEW_DEFAULT = "OFF"
P358_FX6_BODY_IBIS_ULTRASONIC_CLEANING = False
P358_FX6_IR_REMOTE_UI_COUNT = 0
P358_FX6_STILL_AUTO_REVIEW_UI_COUNT = 0

# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Paths (Waves 75-76)
# ---------------------------------------------------------------------------

P358_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    (
        "fx3_libwiredlanresource_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libWiredLanResource.so",
    ),
    (
        "fx3_libnetserviceether_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libNetServiceEther.so",
    ),
    (
        "fx3_libinfraairplanemode_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so",
    ),
    (
        "fx3_string_english_f_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
    ),
    (
        "fx3_string_english_g_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
    ),
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx6_string_english_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P358_GA_ERR_MODEL_OR_FW_FLOOR = "P358_GA_ERR_MODEL_OR_FW_FLOOR"
P358_GA_ERR_METERING_OR_AEL_CONTRACT = "P358_GA_ERR_METERING_OR_AEL_CONTRACT"
P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE = (
    "P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE"
)
P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW = "P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW"
P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT = (
    "P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT"
)

P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE = (
    "P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE"
)
P358_GB_ERR_DORMANT_STEADYSHOT_EOPNOTSUPP = "P358_GB_ERR_DORMANT_STEADYSHOT_EOPNOTSUPP"
P358_GB_ERR_FX6_ZERO_IBIS_CONTRACT = "P358_GB_ERR_FX6_ZERO_IBIS_CONTRACT"
P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT = (
    "P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT"
)
P358_GB_ERR_SLOT1_FILE_FOLDER_EROFS30 = "P358_GB_ERR_SLOT1_FILE_FOLDER_EROFS30"

P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS = (
    "P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS"
)
P358_GC_ERR_DORMANT_CUSTOM_KEY_EOPNOTSUPP = "P358_GC_ERR_DORMANT_CUSTOM_KEY_EOPNOTSUPP"
P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY = (
    "P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY"
)
P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF = (
    "P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF"
)
P358_GC_ERR_FX6_ASSIGNABLE_OR_4WAY_MLUT = "P358_GC_ERR_FX6_ASSIGNABLE_OR_4WAY_MLUT"

P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED = (
    "P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED"
)
P358_GD_ERR_AIRPLANE_RESET_SPLIT = "P358_GD_ERR_AIRPLANE_RESET_SPLIT"
P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST = (
    "P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST"
)
P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6 = (
    "P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6"
)
P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P358_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P358_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

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


def resolve_phase358_donor_file_or_none(
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


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P358_HEADER_READ_BYTES) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase358DonorInspectionResult:
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


def inspect_phase358_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase358DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase358DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P358_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P358_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE358_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    for lbl, rel in P358_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            break
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx3_appfw_so" and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx3_libwiredlanresource_so" and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / "libWiredLanResource.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx3_libnetserviceether_so" and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / "libNetServiceEther.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl == "fx3_libinfraairplanemode_so" and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / "libInfraAirplaneMode.so"
            if p.exists() and p.is_file():
                candidate = p
        if candidate is None:
            candidate = resolve_phase358_donor_file_or_none(resolved_work_root, rel)
        if candidate is not None:
            hdr = _read_bounded_header_o_rdonly(candidate, P358_HEADER_READ_BYTES)
            present_count += 1
            bytes_read += len(hdr)
            digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]

    if present_count == 0:
        return Phase358DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P358_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P358_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE358_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    return Phase358DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        donor_tree_present=True,
        donors_checked=len(P358_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE358_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Check Group Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class P358CheckGroupAMeteringExpStepPpLutAndUserLutResult:
    group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    shoot_mode: str
    log_shooting_mode: str
    reset_action: str
    metering_mode: str
    effective_metering_mode: str
    face_priority_in_multi_metering: str
    effective_face_priority_in_multi: str
    spot_metering_point: str
    effective_spot_metering_point: str
    focus_area: str
    ciz_or_digital_zoom_active: bool
    desqueeze_display: str
    ael_w_shutter: str
    ael_w_shutter_effective: bool
    ael_w_shutter_reset_immune: bool
    exposure_step: str
    effective_exposure_step_after_reset: str
    exposure_step_reset_immune: bool
    exposure_step_affects_shutter_angle: bool
    fx6_ae_mode: str
    fx6_ae_level: float
    fx6_ae_level_steps: int
    fx6_ae_speed: int
    fx6_detect_window: str
    picture_profile: str
    effective_pp_index_after_reset: str
    pp1_to_pp11_params_survive_reset_and_init: bool
    pplut_reset_under_both_reset_and_init: bool
    pplut_forced_hdmi_resolution: Optional[str]
    select_lut: str
    user_lut_slot_count: int
    user_lut_cube_points: int
    user_lut_filename_bytes: int
    user_lut_dir: str
    media_type: str
    embed_lut_file: str
    effective_embed_lut_file: str
    embed_lut_container: str
    fx3_mxf_supported: bool
    fx3_sidecar_cube_emitted: bool
    fx6_user_lut_ui_slots: int
    fx6_user_lut_internal_buffer_slots: int
    fx6_mlut_channels: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P358CheckGroupBIbisFocalTablePlaybackAndFileSlot1Result:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    media_type: str
    steadyshot_movie: str
    effective_steadyshot_movie: str
    steadyshot_still: str
    steadyshot_adjust: str
    steadyshot_focal_length_mm: int
    focal_table_entry_count: int
    frame_rate_fps: float
    hdmi_raw_output: bool
    desqueeze_display: str
    e_mount_sony_lens: bool
    catalyst_gyro_metadata_active: bool
    dormant_steadyshot_mode_requested: Optional[str]
    fx6_body_ibis_count: int
    fx6_ibis_unsupported_symbol: str
    playback_readonly_items: Tuple[str, ...]
    image_index: str
    display_rotation: str
    focus_frame_display: str
    cont_pb_for_interval: str
    play_speed_for_interval: int
    playback_media_sector_writes: int
    file_name_format: str
    effective_file_name_format: str
    camid_reel_stem: str
    title_name: str
    fx6_title_prefix_chars: int
    slot1_contains_tier0_dump: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P358CheckGroupCXlrH1CustomKeyDiffSet8AndGammaAssistResult:
    group_id: str
    passed: bool
    shoot_mode: str
    log_shooting_mode: str
    reset_action: str
    shutter_mode: str
    xlr_h1_attached: bool
    xlr_h1_assignable_button_count: int
    xlr_h1_rec_button_count: int
    xlr_h1_dial_count: int
    still_custom_control_count: int
    movie_custom_control_count: int
    playback_custom_control_count: int
    dormant_custom_key_requested: Optional[str]
    diff_set_items: Tuple[str, ...]
    diff_set_pp_checkbox_checked: bool
    effective_pp_checkbox_after_reset: bool
    diff_set_transition: str
    custom_wb_copied_to_still_only: bool
    shutter_angle_splits_still_movie: bool
    gamma_display_assist: str
    effective_gamma_display_assist: str
    gamma_disp_assist_type: str
    display_lut: str
    select_lut: str
    shooting_still_in_log_mode: bool
    gamma_assist_hdmi_pixel_count: int
    fx3_gamma_assist_slog2_exposed: bool
    fx6_assignable_button_count: int
    fx6_still_movie_split_supported: bool
    fx6_gamma_disp_assist_ui_count: int
    fx6_mlut_channel_count: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P358CheckGroupDUsbLanAuthIpsecAirplaneCleaningAndTier0Result:
    group_id: str
    passed: bool
    body_fw: str
    reset_action: str
    usb_lan_enabled: bool
    usb_lan_ip_mode: str
    usb_lan_connect_launch: str
    usb_lan_manual_ip_valid: bool
    multi_usb_concurrent_active: bool
    wifi_concurrent_active: bool
    airplane_mode: str
    effective_airplane_mode_after_reset: str
    airplane_mode_blocks_usb_lan: bool
    access_authen: str
    access_authen_protocol: str
    ipsec_enabled: bool
    ipsec_hard_disabled_ver7_or_authen: bool
    fx6_ipsec_ui_binding_count: int
    sensor_cleaning_requested: bool
    battery_soc_pct: int
    power_switch_turned_off_for_blower: bool
    fx3_anti_dust_ui_count: int
    fx3_shutter_when_pwr_off_ui_count: int
    ir_remote_ctrl: str
    bluetooth_rmt_ctrl: str
    fx3a_body_variant: bool
    auto_review: str
    fx6_body_ibis_ultrasonic_cleaning: bool
    fx6_ir_remote_ui_count: int
    fx6_still_auto_review_ui_count: int
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
    wireless_rf_packets_emitted: int
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
class Phase358ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P358CheckGroupAMeteringExpStepPpLutAndUserLutResult
    check_group_b: P358CheckGroupBIbisFocalTablePlaybackAndFileSlot1Result
    check_group_c: P358CheckGroupCXlrH1CustomKeyDiffSet8AndGammaAssistResult
    check_group_d: P358CheckGroupDUsbLanAuthIpsecAirplaneCleaningAndTier0Result
    donor_inspection: Phase358DonorInspectionResult
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
    fx3_ibis_47_focal_table_exact: bool
    fx6_body_ibis_present: bool
    xlr_h1_assignable_keys_present: bool
    fx3_diff_set_8_items_exact: bool
    fx3_gamma_assist_slog2_exposed: bool
    fx3_ipsec_ver7_available: bool
    fx3_anti_dust_shutter_barrier_exposed: bool
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
            "fx3_ibis_47_focal_table_exact": self.fx3_ibis_47_focal_table_exact,
            "fx6_body_ibis_present": self.fx6_body_ibis_present,
            "xlr_h1_assignable_keys_present": self.xlr_h1_assignable_keys_present,
            "fx3_diff_set_8_items_exact": self.fx3_diff_set_8_items_exact,
            "fx3_gamma_assist_slog2_exposed": self.fx3_gamma_assist_slog2_exposed,
            "fx3_ipsec_ver7_available": self.fx3_ipsec_ver7_available,
            "fx3_anti_dust_shutter_barrier_exposed": self.fx3_anti_dust_shutter_barrier_exposed,
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


def build_simulated_phase358_tier0_receipts(
    *,
    body_serial: str = "FX3SIM70200358",
    emmc_cid: str = "11010030303847333000a1b2c3d49358",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE358_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE358_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
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
        "st_dev_a": 1351,
        "st_dev_b": 1352,
    }


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 75 Metering / ExpStep / PP1..11 / PPLUT / LUT)
# ---------------------------------------------------------------------------


def evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P358_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    metering_mode: str = P358_METERING_MODE_DEFAULT,
    face_priority_in_multi_metering: str = "ON",
    spot_metering_point: str = P358_SPOT_METERING_POINT_DEFAULT,
    focus_area: str = "SPOT_M",
    ciz_or_digital_zoom_active: bool = False,
    desqueeze_display: str = "OFF",
    ael_w_shutter: str = P358_AEL_W_SHUTTER_DEFAULT,
    exposure_step: str = P358_EXPOSURE_STEP_DEFAULT,
    expect_metering_not_locked_to_multi_under_zoom: bool = False,
    expect_spot_point_links_on_wide_zone_or_center_fix: bool = False,
    expect_ael_w_shutter_active_in_movie: bool = False,
    claimed_ael_w_shutter_wiped_by_camera_reset: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    expect_exposure_step_alters_shutter_angle: bool = False,
    expect_mm_meter_changes_with_ei_in_cine_ei: bool = False,
    fx6_ae_mode: str = "STANDARD",
    fx6_ae_level: float = 0.0,
    fx6_ae_speed: int = 0,
    fx6_detect_window: str = "1",
    fx6_detect_window_width: int = P358_FX6_DETECT_WINDOW_WIDTH_DEFAULT,
    claimed_fx6_ae_level_limited_to_2ev: bool = False,
    claimed_fx6_has_still_spot_or_ael_shutter: bool = False,
    picture_profile: str = P358_PICTURE_PROFILE_DEFAULT,
    internal_rec_active: bool = True,
    hdmi_only_output: bool = False,
    hdmi_raw_output: bool = False,
    select_lut: str = P358_SELECT_LUT_DEFAULT,
    user_lut_slot_count: int = P358_USER_LUT_SLOT_MAX,
    user_lut_cube_points: int = 33,
    user_lut_filename: str = "s709_custom_v1.cube",
    media_type: str = "CFEXPRESS_A",
    embed_lut_file: str = "ON",
    claimed_pp1_to_pp11_wiped_by_reset_or_init: bool = False,
    claimed_pplut_resists_reset_or_init: bool = False,
    claimed_pplut_active_in_still: bool = False,
    expect_4k_hdmi_with_pplut_internal_rec: bool = False,
    claimed_pp_active_with_log_shooting_on: bool = False,
    claimed_user_lut_wiped_by_camera_reset: bool = False,
    claimed_fx3_supports_mxf_or_sidecar_cube_embed: bool = False,
    expect_embed_lut_enabled_on_sdhc: bool = False,
    claimed_embed_lut_under_color_tone: bool = False,
    claimed_fx6_user_lut_pool_not_50: bool = False,
) -> P358CheckGroupAMeteringExpStepPpLutAndUserLutResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT or body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P358_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw {TARGET_BODY_FW}, "
            f"got 0x{body_model_id:08x} fw {body_fw!r}"
        )
    if sony_help_guide_id != P358_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P358_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P358_SONY_HELP_GUIDE_ID!r}"
        )
    if shoot_mode not in P358_VALID_SHOOT_MODES:
        errors.append(f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid shoot_mode {shoot_mode!r}")
    if log_shooting_mode not in P358_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if reset_action not in P358_VALID_RESET_ACTIONS:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid reset_action {reset_action!r}"
        )
    if desqueeze_display not in P358_VALID_DESQUEEZE_MODES:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid desqueeze_display {desqueeze_display!r}"
        )
    if media_type not in P358_VALID_MEDIA_TYPES:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: invalid media_type {media_type!r}"
        )

    # Metering 6 modes, Face Priority (BKID_APP_setting_face_detection_in_multi), Spot Point, AEL w/ Shutter
    if metering_mode not in P358_METERING_MODES:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid [Metering Mode] {metering_mode!r}; "
            f"must be one of 6 modes {P358_METERING_MODES}"
        )
    if face_priority_in_multi_metering not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid face_priority_in_multi_metering {face_priority_in_multi_metering!r}"
        )
    if spot_metering_point not in P358_SPOT_METERING_POINT_MODES:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid spot_metering_point {spot_metering_point!r}"
        )
    if focus_area not in P358_VALID_FOCUS_AREAS:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid focus_area {focus_area!r}"
        )
    if ael_w_shutter not in P358_AEL_W_SHUTTER_MODES:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: invalid ael_w_shutter {ael_w_shutter!r}"
        )

    if expect_metering_not_locked_to_multi_under_zoom and ciz_or_digital_zoom_active:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: [Metering Mode] is hard-locked to Multi under Clear Image Zoom / Digital Zoom"
        )
    if (
        expect_spot_point_links_on_wide_zone_or_center_fix
        and focus_area in P358_FOCUS_AREAS_FORCING_SPOT_CENTER
    ):
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: [Spot Metering Point] falls back to Center when [Focus Area]={focus_area!r}"
        )
    if expect_ael_w_shutter_active_in_movie:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: [AEL w/ Shutter] is strictly Still-only; Movie uses Custom Key AEL hold/toggle"
        )
    if claimed_ael_w_shutter_wiped_by_camera_reset:
        errors.append(
            f"{P358_GA_ERR_METERING_OR_AEL_CONTRACT}: [AEL w/ Shutter] is Not available under [Camera Settings Reset] (Initialize-only)"
        )

    effective_metering = (
        P358_METERING_MODE_DEFAULT
        if (ciz_or_digital_zoom_active or reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE"))
        else metering_mode
    )
    effective_face_priority = (
        "OFF"
        if (desqueeze_display != "OFF" or ciz_or_digital_zoom_active)
        else ("ON" if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else face_priority_in_multi_metering)
    )
    effective_spot_point = (
        "CENTER"
        if (
            focus_area in P358_FOCUS_AREAS_FORCING_SPOT_CENTER
            or reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        )
        else spot_metering_point
    )
    ael_w_shutter_effective = shoot_mode == "PHOTO" and (
        (P358_AEL_W_SHUTTER_DEFAULT if reset_action == "INITIALIZE" else ael_w_shutter) != "OFF"
    )

    # [Exposure step] erratum (Not available under [Camera Settings Reset], Initialize-only, Shutter Angle immune)
    if exposure_step not in P358_EXPOSURE_STEP_MODES:
        errors.append(
            f"{P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE}: invalid exposure_step {exposure_step!r}"
        )
    if claimed_exposure_step_wiped_by_camera_reset:
        errors.append(
            f"{P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE}: Wave 75 G96 erratum — [Exposure step] is Not available under [Camera Settings Reset] (Initialize-only)"
        )
    if expect_exposure_step_alters_shutter_angle:
        errors.append(
            f"{P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE}: [Shutter Angle] is immune to [Exposure step]"
        )
    if expect_mm_meter_changes_with_ei_in_cine_ei and log_shooting_mode in ("CINE_EI", "CINE_EI_QUICK"):
        errors.append(
            f"{P358_GA_ERR_EXP_STEP_ERRATUM_OR_SHUTTER_ANGLE}: in {log_shooting_mode}, M.M. metering does not change with EI switch"
        )
    effective_exposure_step = (
        P358_EXPOSURE_STEP_DEFAULT if reset_action == "INITIALIZE" else exposure_step
    )

    # FX6 Shooting > Auto Exposure (-3.0..+3.0 in 0.25 steps = 25 steps, disproving -2.0..+2.0EV rumor)
    if fx6_ae_mode not in P358_FX6_AE_MODES:
        errors.append(f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: invalid fx6_ae_mode {fx6_ae_mode!r}")
    if (
        fx6_ae_level < P358_FX6_AE_LEVEL_MIN
        or fx6_ae_level > P358_FX6_AE_LEVEL_MAX
        or abs((fx6_ae_level / P358_FX6_AE_LEVEL_STEP) - round(fx6_ae_level / P358_FX6_AE_LEVEL_STEP)) > 1e-6
    ):
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: FX6 Auto Exposure Level must be in [-3.0..+3.0] step 0.25 (25 steps), got {fx6_ae_level}"
        )
    if not (P358_FX6_AE_SPEED_MIN <= fx6_ae_speed <= P358_FX6_AE_SPEED_MAX):
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: FX6 AE Speed out of -99..+99 range: {fx6_ae_speed}"
        )
    if fx6_detect_window not in P358_FX6_DETECT_WINDOW_MODES:
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: invalid fx6_detect_window {fx6_detect_window!r}"
        )
    if not (P358_FX6_DETECT_WINDOW_WIDTH_MIN <= fx6_detect_window_width <= P358_FX6_DETECT_WINDOW_WIDTH_MAX):
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: FX6 Detect Window Width out of 40..999: {fx6_detect_window_width}"
        )
    if claimed_fx6_ae_level_limited_to_2ev:
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: -2.0..+2.0EV rumor disproved; FX6 Ver. 6.01 Auto Exposure Level spans -3.0..+3.0 in 0.25 steps (25 steps)"
        )
    if claimed_fx6_has_still_spot_or_ael_shutter:
        errors.append(
            f"{P358_GA_ERR_FX6_AE_LEVEL_RANGE_OR_WINDOW}: ILME-FX6 lacks Still [Spot Metering Point] and [AEL w/ Shutter]"
        )

    # Picture Profile PP1..11 vs PPLUT1..4, Manage User LUTs, Embed LUT File
    if picture_profile not in P358_PICTURE_PROFILE_OPTIONS:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: invalid picture_profile {picture_profile!r}"
        )
    if picture_profile in P358_PPLUT_PROFILES and shoot_mode == "PHOTO":
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: {picture_profile} is strictly Movie-only (not available in Still)"
        )
    if claimed_pplut_active_in_still:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: PPLUT1..4 are Movie-only and cannot be selected in Still mode"
        )
    if claimed_pp1_to_pp11_wiped_by_reset_or_init:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: PP1..11 internal custom parameters survive BOTH [Camera Settings Reset] and [Initialize]"
        )
    if claimed_pplut_resists_reset_or_init:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: PPLUT1..4 settings reset under BOTH [Camera Settings Reset] and [Initialize] (while PP index resets to PP11)"
        )
    if expect_4k_hdmi_with_pplut_internal_rec and (
        picture_profile in P358_PPLUT_PROFILES and internal_rec_active and not hdmi_only_output and not hdmi_raw_output
    ):
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: {picture_profile} with internal rec forces HDMI output down to 1080p unless Off(HDMI Only) or RAW Output=On"
        )
    if claimed_pp_active_with_log_shooting_on and log_shooting_mode != "OFF":
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: [Picture Profile] is forced Off when [Log Shooting]={log_shooting_mode!r}"
        )

    if select_lut not in P358_SELECT_LUT_OPTIONS:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: invalid select_lut {select_lut!r}"
        )
    if not (1 <= user_lut_slot_count <= P358_USER_LUT_SLOT_MAX):
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: user_lut_slot_count must be 1..16, got {user_lut_slot_count}"
        )
    if user_lut_cube_points not in P358_USER_LUT_CUBE_POINTS:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: .cube grid size must be 17 or 33 points, got {user_lut_cube_points}"
        )
    fname_bytes = len(user_lut_filename.encode("utf-8"))
    if (
        not user_lut_filename.lower().endswith(".cube")
        or fname_bytes > P358_USER_LUT_MAX_FILENAME_BYTES
    ):
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: User LUT .cube filename must end in .cube and be <= 63 bytes (got {fname_bytes}B)"
        )
    if claimed_user_lut_wiped_by_camera_reset:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: [Manage User LUTs] slots are Reset-immune (only Delete All or Initialize clears)"
        )
    if embed_lut_file not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: invalid embed_lut_file {embed_lut_file!r}"
        )
    if expect_embed_lut_enabled_on_sdhc and media_type in ("SDHC", "SD"):
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: [Embed LUT File] is locked Off on SD/SDHC media (_g 0x61a0)"
        )
    if claimed_fx3_supports_mxf_or_sidecar_cube_embed:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: FX3 embeds LUT into MP4 container (no MXF and no external .cube sidecar)"
        )
    if claimed_embed_lut_under_color_tone:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: [Embed LUT File] lives at {P358_EMBED_LUT_FILE_MENU_PATH!r}, NOT under [Color/Tone]"
        )
    if claimed_fx6_user_lut_pool_not_50:
        errors.append(
            f"{P358_GA_ERR_PP11_PPLUT4_OR_USER_LUT_CONTRACT}: FX6 exposes 16 UI User LUTs backed by 50-slot internal PRM_is_exist_user_lut0..49 buffer"
        )

    effective_pp = (
        P358_PICTURE_PROFILE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else ("OFF" if log_shooting_mode != "OFF" else picture_profile)
    )
    pplut_hdmi = (
        P358_PPLUT_FORCED_INTERNAL_REC_HDMI_RESOLUTION
        if (effective_pp in P358_PPLUT_PROFILES and internal_rec_active and not hdmi_only_output and not hdmi_raw_output)
        else None
    )
    user_lut_dir = (
        P358_USER_LUT_CFEA_DIR if media_type == "CFEXPRESS_A" else P358_USER_LUT_SD_DIR
    )
    effective_embed_lut = (
        "OFF"
        if media_type in ("SDHC", "SD")
        else ("ON" if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else embed_lut_file)
    )

    return P358CheckGroupAMeteringExpStepPpLutAndUserLutResult(
        group_id=P358_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        body_model_id_hex=f"0x{body_model_id:08x}",
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        metering_mode=metering_mode,
        effective_metering_mode=effective_metering,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        effective_face_priority_in_multi=effective_face_priority,
        spot_metering_point=spot_metering_point,
        effective_spot_metering_point=effective_spot_point,
        focus_area=focus_area,
        ciz_or_digital_zoom_active=ciz_or_digital_zoom_active,
        desqueeze_display=desqueeze_display,
        ael_w_shutter=ael_w_shutter,
        ael_w_shutter_effective=ael_w_shutter_effective,
        ael_w_shutter_reset_immune=True,
        exposure_step=exposure_step,
        effective_exposure_step_after_reset=effective_exposure_step,
        exposure_step_reset_immune=P358_EXPOSURE_STEP_RESISTS_CAMERA_RESET,
        exposure_step_affects_shutter_angle=P358_EXPOSURE_STEP_AFFECTS_SHUTTER_ANGLE,
        fx6_ae_mode=fx6_ae_mode,
        fx6_ae_level=fx6_ae_level,
        fx6_ae_level_steps=P358_FX6_AE_LEVEL_STEP_COUNT,
        fx6_ae_speed=fx6_ae_speed,
        fx6_detect_window=fx6_detect_window,
        picture_profile=picture_profile,
        effective_pp_index_after_reset=effective_pp,
        pp1_to_pp11_params_survive_reset_and_init=True,
        pplut_reset_under_both_reset_and_init=True,
        pplut_forced_hdmi_resolution=pplut_hdmi,
        select_lut=select_lut,
        user_lut_slot_count=user_lut_slot_count,
        user_lut_cube_points=user_lut_cube_points,
        user_lut_filename_bytes=fname_bytes,
        user_lut_dir=user_lut_dir,
        media_type=media_type,
        embed_lut_file=embed_lut_file,
        effective_embed_lut_file=effective_embed_lut,
        embed_lut_container=P358_EMBED_LUT_CONTAINER,
        fx3_mxf_supported=P358_FX3_MXF_SUPPORTED,
        fx3_sidecar_cube_emitted=P358_FX3_SIDECAR_CUBE_EMITTED,
        fx6_user_lut_ui_slots=P358_FX6_USER_LUT_UI_SLOTS,
        fx6_user_lut_internal_buffer_slots=P358_FX6_USER_LUT_INTERNAL_BUFFER_SLOTS,
        fx6_mlut_channels=P358_FX6_MLUT_CHANNELS,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 75 IBIS 47-Focal / PB ReadOnly / File & Slot1)
# ---------------------------------------------------------------------------


def evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    media_type: str = "CFEXPRESS_A",
    steadyshot_movie: str = P358_STEADYSHOT_MOVIE_DEFAULT,
    steadyshot_still: str = P358_STEADYSHOT_STILL_DEFAULT,
    steadyshot_adjust: str = P358_STEADYSHOT_ADJUST_DEFAULT,
    steadyshot_focal_length_mm: int = P358_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
    exposed_focal_lengths_mm: Tuple[int, ...] = P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    frame_rate_fps: float = 23.98,
    hdmi_raw_output: bool = False,
    desqueeze_display: str = "OFF",
    e_mount_sony_lens: bool = True,
    expect_steadyshot_active_under_lockout: bool = False,
    expect_catalyst_gyro_available: bool = False,
    dormant_steadyshot_mode_requested: Optional[str] = None,
    claimed_steadyshot_resists_camera_reset: bool = False,
    claimed_fx6_has_body_ibis: bool = False,
    exposed_playback_readonly_items: Tuple[str, ...] = P358_PLAYBACK_5_READONLY_ITEMS,
    image_index: str = P358_IMAGE_INDEX_DEFAULT,
    display_rotation: str = P358_DISPLAY_ROTATION_DEFAULT,
    focus_frame_display: str = "OFF",
    cont_pb_for_interval: str = "OFF",
    play_speed_for_interval: int = P358_PLAY_SPEED_DEFAULT,
    claimed_playback_5_wiped_by_camera_reset: bool = False,
    claimed_interval_pb_generates_video_or_writes_card: bool = False,
    file_name_format: str = P358_FILE_NAME_FORMAT_DEFAULT,
    camid_reel_stem: str = "A001C001_230101AB",
    title_name: str = P358_TITLE_NAME_DEFAULT,
    fx6_title_prefix_chars: int = 4,
    claimed_camid_reel_stem_is_37_chars: bool = False,
    expect_camid_reel_allowed_on_sdhc: bool = False,
    claimed_file_settings_wiped_by_camera_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    create_new_folder_on_slot1_requested: bool = False,
    forced_file_no_reset_on_slot1_requested: bool = False,
    select_rec_folder_write_on_slot1_requested: bool = False,
    series_counter_reset_on_slot1_requested: bool = False,
) -> P358CheckGroupBIbisFocalTablePlaybackAndFileSlot1Result:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P358_VALID_SHOOT_MODES:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid shoot_mode {shoot_mode!r}"
        )
    if reset_action not in P358_VALID_RESET_ACTIONS:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid reset_action {reset_action!r}"
        )
    if media_type not in P358_VALID_MEDIA_TYPES:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid media_type {media_type!r}"
        )
    if desqueeze_display not in P358_VALID_DESQUEEZE_MODES:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid desqueeze_display {desqueeze_display!r}"
        )

    # IBIS & 47-entry focal length table
    if steadyshot_movie not in P358_STEADYSHOT_MOVIE_MODES:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid steadyshot_movie {steadyshot_movie!r}"
        )
    if steadyshot_still not in P358_STEADYSHOT_STILL_MODES:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid steadyshot_still {steadyshot_still!r}"
        )
    if steadyshot_adjust not in P358_STEADYSHOT_ADJUST_MODES:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: invalid steadyshot_adjust {steadyshot_adjust!r}"
        )
    if tuple(exposed_focal_lengths_mm) != P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: IBIS focal table must equal exact 47 entries 8..1000mm (got {len(exposed_focal_lengths_mm)})"
        )
    if steadyshot_focal_length_mm not in P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: steadyshot_focal_length_mm {steadyshot_focal_length_mm} not in 47-entry table"
        )

    active_locked_out = frame_rate_fps >= 100.0 or hdmi_raw_output or desqueeze_display != "OFF"
    if expect_steadyshot_active_under_lockout and active_locked_out:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: SteadyShot [Active] is disabled at 120p/RAW=On/De-Squeeze!=Off"
        )

    effective_steadyshot = (
        P358_STEADYSHOT_MOVIE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else (
            "STANDARD"
            if (steadyshot_movie == "ACTIVE" and active_locked_out)
            else steadyshot_movie
        )
    )
    catalyst_gyro = (
        shoot_mode == "MOVIE"
        and e_mount_sony_lens
        and frame_rate_fps < 100.0
        and effective_steadyshot in ("OFF", "ACTIVE")
    )
    if expect_catalyst_gyro_available and not catalyst_gyro:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: Catalyst Gyro requires Movie + E-mount + fps<100 + SteadyShot in (Off, Active), got mode={shoot_mode} ss={effective_steadyshot} fps={frame_rate_fps}"
        )
    if claimed_steadyshot_resists_camera_reset:
        errors.append(
            f"{P358_GB_ERR_IBIS_STEADYSHOT_OR_47_FOCAL_TABLE}: all 4 [Image Stabilization] items are Can be reset"
        )
    if dormant_steadyshot_mode_requested is not None:
        if dormant_steadyshot_mode_requested in P358_DORMANT_STEADYSHOT_MODES or dormant_steadyshot_mode_requested:
            errors.append(
                f"{P358_GB_ERR_DORMANT_STEADYSHOT_EOPNOTSUPP}: errno={P358_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) dormant SteadyShot mode {dormant_steadyshot_mode_requested!r} inactive on FX3"
            )
    if claimed_fx6_has_body_ibis:
        errors.append(
            f"{P358_GB_ERR_FX6_ZERO_IBIS_CONTRACT}: FX6 has 0 body IBIS ({P358_FX6_IBIS_UNSUPPORTED_SYMBOL}, optical OSS only)"
        )

    # Playback 5 read-only items
    if tuple(exposed_playback_readonly_items) != P358_PLAYBACK_5_READONLY_ITEMS:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: exposed Playback read-only items must match exact 5 {P358_PLAYBACK_5_READONLY_ITEMS}"
        )
    if image_index not in P358_IMAGE_INDEX_OPTIONS:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid image_index {image_index!r}"
        )
    if display_rotation not in P358_DISPLAY_ROTATION_OPTIONS:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid display_rotation {display_rotation!r}"
        )
    if focus_frame_display not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid focus_frame_display {focus_frame_display!r}"
        )
    if cont_pb_for_interval not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid cont_pb_for_interval {cont_pb_for_interval!r}"
        )
    if not (P358_PLAY_SPEED_MIN <= play_speed_for_interval <= P358_PLAY_SPEED_MAX):
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: play_speed_for_interval must be 1..9, got {play_speed_for_interval}"
        )
    if claimed_playback_5_wiped_by_camera_reset:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: all 5 Playback items are Not available under [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_interval_pb_generates_video_or_writes_card:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: Playback read-only items execute 0 storage writes and generate no video"
        )

    # Movie Cam ID + Reel# 17-char stem vs 37-char Title Name Settings vs FX6 4..46 Title Prefix
    if file_name_format not in P358_FILE_NAME_FORMATS:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: invalid file_name_format {file_name_format!r}"
        )
    if len(camid_reel_stem) != P358_MOVIE_CAMID_REEL_STEM_LEN:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: Movie Cam ID + Reel# stem must be 17 chars, got {len(camid_reel_stem)}"
        )
    if not (1 <= len(title_name) <= P358_TITLE_NAME_MAX_CHARS):
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: [Title Name Settings] must be 1..37 chars, got {len(title_name)}"
        )
    if not (P358_FX6_TITLE_PREFIX_MIN_CHARS <= fx6_title_prefix_chars <= P358_FX6_TITLE_PREFIX_MAX_CHARS):
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: FX6 Title Prefix must be 4..46 chars, got {fx6_title_prefix_chars}"
        )
    if claimed_camid_reel_stem_is_37_chars:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: 17-char Cam ID + Reel# stem != 37-char [Title Name Settings]"
        )
    if expect_camid_reel_allowed_on_sdhc and media_type in ("SDHC", "SD"):
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: SDHC locks [File Name Format] to Standard"
        )
    if claimed_file_settings_wiped_by_camera_reset:
        errors.append(
            f"{P358_GB_ERR_PB_5_READONLY_OR_FILENAME_FORMAT}: [File] settings are Not available under [Camera Settings Reset]"
        )
    effective_format = "STANDARD" if media_type in ("SDHC", "SD") else file_name_format

    # Tier-0 Slot 1 EROFS=30 firewall
    if slot1_contains_tier0_dump:
        for req, label in (
            (create_new_folder_on_slot1_requested, "[Create New Folder]"),
            (forced_file_no_reset_on_slot1_requested, "[Forced File No. Reset]"),
            (select_rec_folder_write_on_slot1_requested, "[Select REC Folder]"),
            (series_counter_reset_on_slot1_requested, "[Series Counter Reset]"),
        ):
            if req:
                errors.append(
                    f"{P358_GB_ERR_SLOT1_FILE_FOLDER_EROFS30}: errno={P358_ERRNO_EROFS} (EROFS) {label} write blocked on protected Tier-0 Slot 1"
                )

    return P358CheckGroupBIbisFocalTablePlaybackAndFileSlot1Result(
        group_id=P358_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        media_type=media_type,
        steadyshot_movie=steadyshot_movie,
        effective_steadyshot_movie=effective_steadyshot,
        steadyshot_still=steadyshot_still,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_length_mm=steadyshot_focal_length_mm,
        focal_table_entry_count=len(exposed_focal_lengths_mm),
        frame_rate_fps=frame_rate_fps,
        hdmi_raw_output=hdmi_raw_output,
        desqueeze_display=desqueeze_display,
        e_mount_sony_lens=e_mount_sony_lens,
        catalyst_gyro_metadata_active=catalyst_gyro,
        dormant_steadyshot_mode_requested=dormant_steadyshot_mode_requested,
        fx6_body_ibis_count=P358_FX6_BODY_IBIS_COUNT,
        fx6_ibis_unsupported_symbol=P358_FX6_IBIS_UNSUPPORTED_SYMBOL,
        playback_readonly_items=tuple(exposed_playback_readonly_items),
        image_index=image_index,
        display_rotation=display_rotation,
        focus_frame_display=focus_frame_display,
        cont_pb_for_interval=cont_pb_for_interval,
        play_speed_for_interval=play_speed_for_interval,
        playback_media_sector_writes=0,
        file_name_format=file_name_format,
        effective_file_name_format=effective_format,
        camid_reel_stem=camid_reel_stem,
        title_name=title_name,
        fx6_title_prefix_chars=fx6_title_prefix_chars,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_data_sector_writes=PHASE358_SLOT1_DATA_SECTOR_WRITES,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 76 XLR-H1, Custom Key, DiffSet8, Gamma Assist)
# ---------------------------------------------------------------------------


def evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
    *,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    shutter_mode: str = "SPEED",
    xlr_h1_attached: bool = True,
    claimed_xlr_h1_has_custom_or_rec_keys: bool = False,
    still_custom_controls: Tuple[str, ...] = P358_STILL_CUSTOM_CONTROLS,
    movie_custom_factory_defaults: Mapping[str, str] = P358_MOVIE_CUSTOM_FACTORY_DEFAULTS,
    playback_custom_controls: Tuple[str, ...] = P358_PLAYBACK_CUSTOM_CONTROLS,
    claimed_fn_assignable_in_still_or_movie: bool = False,
    claimed_pb_includes_c4_delete: bool = False,
    claimed_custom_key_wiped_by_camera_reset: bool = False,
    dormant_custom_key_requested: Optional[str] = None,
    diff_set_items: Tuple[str, ...] = P358_DIFF_SET_EXACT_8_ITEMS,
    diff_set_pp_checkbox_checked: bool = True,
    diff_set_transition: str = "NONE",
    claimed_pp_checkbox_wiped_by_reset_or_init: bool = False,
    claimed_common_to_separate_copies_custom_wb_to_movie: bool = False,
    claimed_separate_to_common_discards_still_av_tv_wb: bool = False,
    claimed_shutter_angle_shared_when_diffset_unchecked: bool = False,
    claimed_diff_set_saved_in_campr: bool = False,
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = P358_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
    display_lut: str = "ON",
    select_lut: str = P358_SELECT_LUT_DEFAULT,
    shooting_still_in_log_mode: bool = False,
    dormant_gamma_assist_slog2_requested: bool = False,
    claimed_gamma_assist_active_when_log_movie_on: bool = False,
    claimed_gamma_assist_applies_to_hdmi_or_tv: bool = False,
    claimed_gamma_assist_wiped_by_camera_reset: bool = False,
    claimed_fx6_lacks_assignable_or_has_still_split: bool = False,
    claimed_fx6_has_gamma_display_assist_ui: bool = False,
) -> P358CheckGroupCXlrH1CustomKeyDiffSet8AndGammaAssistResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P358_VALID_SHOOT_MODES:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: invalid shoot_mode {shoot_mode!r}"
        )
    if log_shooting_mode not in P358_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if reset_action not in P358_VALID_RESET_ACTIONS:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: invalid reset_action {reset_action!r}"
        )
    if shutter_mode not in P358_VALID_SHUTTER_MODES:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: invalid shutter_mode {shutter_mode!r}"
        )

    # XLR-H1 zero keys & FX3 3 custom key domains
    if claimed_xlr_h1_has_custom_or_rec_keys:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: XLR-H1 handle has 0 assignable custom buttons, 0 handle REC button, and 0 handle dials"
        )
    if tuple(still_custom_controls) != P358_STILL_CUSTOM_CONTROLS:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: Still custom domain must contain exact 16 controls"
        )
    if dict(movie_custom_factory_defaults) != P358_MOVIE_CUSTOM_FACTORY_DEFAULTS:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: Movie custom factory defaults mismatch TP1000888852 (16 controls)"
        )
    if tuple(playback_custom_controls) != P358_PLAYBACK_CUSTOM_CONTROLS:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: Playback custom domain must contain exact 7 controls (skip C4, add Fn)"
        )
    if claimed_fn_assignable_in_still_or_movie:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: Fn Button is assignable in Playback ONLY (0 Still/Movie fn_button symbols)"
        )
    if claimed_pb_includes_c4_delete:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: Playback [Custom Key Setting] skips C4 (fixed Delete)"
        )
    if claimed_custom_key_wiped_by_camera_reset:
        errors.append(
            f"{P358_GC_ERR_XLR_H1_OR_CUSTOM_KEY_3_DOMAINS}: [Custom Key/Dial Set.] resists [Camera Settings Reset]"
        )
    if dormant_custom_key_requested is not None:
        errors.append(
            f"{P358_GC_ERR_DORMANT_CUSTOM_KEY_EOPNOTSUPP}: errno={P358_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) dormant Alpha key symbol {dormant_custom_key_requested!r} unexposed on FX3"
        )

    # [Different Set for Still/Mv] exact 8 items & Picture Profile Initialize immunity
    if tuple(diff_set_items) != P358_DIFF_SET_EXACT_8_ITEMS:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: [Different Set for Still/Mv] must equal exact 8 items {P358_DIFF_SET_EXACT_8_ITEMS}"
        )
    if diff_set_transition not in ("NONE", "COMMON_TO_SEPARATE", "SEPARATE_TO_COMMON"):
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: invalid diff_set_transition {diff_set_transition!r}"
        )
    if claimed_pp_checkbox_wiped_by_reset_or_init:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: [Picture Profile] checkbox in [Different Set for Still/Mv] survives BOTH [Camera Settings Reset] and [Initialize] (TP1000844002)"
        )
    if claimed_common_to_separate_copies_custom_wb_to_movie:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: Common->Separate applies Custom WB to Still ONLY"
        )
    if claimed_separate_to_common_discards_still_av_tv_wb:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: Separate->Common preserves Still Aperture, Shutter Speed, and Custom WB"
        )
    if claimed_shutter_angle_shared_when_diffset_unchecked:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: [Shutter Mode]=Angle keeps Still speed & Movie angle separate regardless of checkbox"
        )
    if claimed_diff_set_saved_in_campr:
        errors.append(
            f"{P358_GC_ERR_DIFF_SET_8_OR_PP_INIT_IMMUNITY}: [Custom Key/Dial Set.] and [Different Set] save in CAMSET01..10.DAT, excluded from CAMPR*.DAT"
        )

    # [Gamma Display Assist] vs [Display LUT] + [Select LUT] & dormant S-Log2
    if gamma_display_assist not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: invalid gamma_display_assist {gamma_display_assist!r}"
        )
    if gamma_disp_assist_type not in P358_GAMMA_DISP_ASSIST_TYPES:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: invalid gamma_disp_assist_type {gamma_disp_assist_type!r}"
        )
    if display_lut not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: invalid display_lut {display_lut!r}"
        )
    if select_lut not in P358_SELECT_LUT_OPTIONS:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: invalid select_lut {select_lut!r}"
        )
    if dormant_gamma_assist_slog2_requested:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: errno={P358_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) dormant S-Log2 (_f 0x7782) unexposed on FX3"
        )
    if claimed_gamma_assist_active_when_log_movie_on and log_shooting_mode != "OFF":
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: [Gamma Display Assist] is hard-locked Off when [Log Shooting]!=Off in Movie mode (handed off to Display LUT + Select LUT)"
        )
    if claimed_gamma_assist_applies_to_hdmi_or_tv:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: [Gamma Display Assist] is NEVER applied to HDMI/TV output (0 px)"
        )
    if claimed_gamma_assist_wiped_by_camera_reset:
        errors.append(
            f"{P358_GC_ERR_GAMMA_DISP_ASSIST_SLOG2_OR_LOG_HANDOFF}: [Gamma Display Assist] / [Display LUT] live under (Setup) and resist [Camera Settings Reset]"
        )
    if claimed_fx6_lacks_assignable_or_has_still_split or claimed_fx6_has_gamma_display_assist_ui:
        errors.append(
            f"{P358_GC_ERR_FX6_ASSIGNABLE_OR_4WAY_MLUT}: FX6 exposes Assignable <1>..<9>, Handle Rec, 3 dials, zero Still/Movie split, 0 Gamma Assist UI, and 4-way MLUT"
        )

    if log_shooting_mode != "OFF" and not shooting_still_in_log_mode:
        effective_gamma_assist = "OFF"
    elif log_shooting_mode != "OFF" and shooting_still_in_log_mode:
        effective_gamma_assist = "ON"
    elif reset_action == "INITIALIZE":
        effective_gamma_assist = "OFF"
    else:
        effective_gamma_assist = gamma_display_assist

    return P358CheckGroupCXlrH1CustomKeyDiffSet8AndGammaAssistResult(
        group_id=P358_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        shutter_mode=shutter_mode,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_assignable_button_count=P358_XLR_H1_ASSIGNABLE_BUTTON_COUNT,
        xlr_h1_rec_button_count=P358_XLR_H1_REC_BUTTON_COUNT,
        xlr_h1_dial_count=P358_XLR_H1_DIAL_COUNT,
        still_custom_control_count=len(still_custom_controls),
        movie_custom_control_count=len(movie_custom_factory_defaults),
        playback_custom_control_count=len(playback_custom_controls),
        dormant_custom_key_requested=dormant_custom_key_requested,
        diff_set_items=tuple(diff_set_items),
        diff_set_pp_checkbox_checked=diff_set_pp_checkbox_checked,
        effective_pp_checkbox_after_reset=diff_set_pp_checkbox_checked,
        diff_set_transition=diff_set_transition,
        custom_wb_copied_to_still_only=True,
        shutter_angle_splits_still_movie=shutter_mode == "ANGLE",
        gamma_display_assist=gamma_display_assist,
        effective_gamma_display_assist=effective_gamma_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        display_lut=display_lut,
        select_lut=("S709" if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else select_lut),
        shooting_still_in_log_mode=shooting_still_in_log_mode,
        gamma_assist_hdmi_pixel_count=P358_GAMMA_DISP_ASSIST_HDMI_PIXEL_COUNT,
        fx3_gamma_assist_slog2_exposed=P358_FX3_GAMMA_ASSIST_SLOG2_EXPOSED,
        fx6_assignable_button_count=len(P358_FX6_ASSIGNABLE_BUTTON_LABELS),
        fx6_still_movie_split_supported=P358_FX6_STILL_MOVIE_SPLIT_SUPPORTED,
        fx6_gamma_disp_assist_ui_count=P358_FX6_GAMMA_DISP_ASSIST_UI_COUNT,
        fx6_mlut_channel_count=len(P358_FX6_MLUT_CHANNELS),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Tier-0 Dual-Media Evidence Extraction (Shared with Phase 354)
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
    errors: List[str],
) -> Dict[str, Any]:
    t0_errors: List[str] = []
    ra: Optional[bytes] = receipt_a_bytes
    rb: Optional[bytes] = receipt_b_bytes
    dev_a: Optional[int] = st_dev_a_override
    dev_b: Optional[int] = st_dev_b_override

    if simulate_bench_dry_run:
        eff_sim_serial = body_serial or "FX3SIM70200358"
        eff_sim_cid = emmc_cid or "11010030303847333000a1b2c3d49358"
        sim = build_simulated_phase358_tier0_receipts(
            body_serial=eff_sim_serial,
            emmc_cid=eff_sim_cid,
        )
        if ra is None:
            ra = sim["receipt_a_bytes"]
        if rb is None:
            rb = sim["receipt_b_bytes"]
        if dev_a is None:
            dev_a = sim["st_dev_a"]
        if dev_b is None:
            dev_b = sim["st_dev_b"]
        h0_a: Optional[Dict[str, str]] = (
            dict(h0_baselines_a) if h0_baselines_a is not None else dict(sim["h0_baselines_a"])
        )
        h0_b: Optional[Dict[str, str]] = (
            dict(h0_baselines_b) if h0_baselines_b is not None else dict(sim["h0_baselines_b"])
        )
        h3: Optional[Dict[str, str]] = (
            dict(h3_baselines) if h3_baselines is not None else dict(sim["h3_baselines"])
        )
        receipt_mode = "SIMULATED_DRY_RUN_DUAL_MEDIA_RECEIPT"
    else:
        has_any_receipt_arg = (
            ra is not None
            or rb is not None
            or receipt_a_path is not None
            or receipt_b_path is not None
        )
        if ra is None and receipt_a_path is not None:
            p_a = Path(receipt_a_path)
            if not p_a.exists() or not p_a.is_file():
                t0_errors.append(
                    f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt A at {p_a}"
                )
            else:
                if dev_a is None:
                    dev_a = int(os.stat(p_a).st_dev)
                ra = _read_bounded_header_o_rdonly(p_a, SD_RECEIPT_BYTES + 1)
        if rb is None and receipt_b_path is not None:
            p_b = Path(receipt_b_path)
            if not p_b.exists() or not p_b.is_file():
                t0_errors.append(
                    f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt B at {p_b}"
                )
            else:
                if dev_b is None:
                    dev_b = int(os.stat(p_b).st_dev)
                rb = _read_bounded_header_o_rdonly(p_b, SD_RECEIPT_BYTES + 1)
        h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
        h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None
        h3 = dict(h3_baselines) if h3_baselines is not None else None
        if not has_any_receipt_arg:
            return {
                "tier0_receipt_verified": False,
                "receipt_mode": "NO_RECEIPT_OFFLINE",
                "h0_equals_h3_count": 0,
                "st_dev_a": None,
                "st_dev_b": None,
                "body_serial": body_serial or "",
                "emmc_cid": emmc_cid or "",
            }
        receipt_mode = (
            "PHYSICAL_DUAL_MEDIA_RECEIPT"
            if (ra is not None and rb is not None)
            else "AWAITING_PHYSICAL_TIER0_RECEIPT"
        )

    if ra is None or rb is None:
        if ra is not None or rb is not None:
            t0_errors.append(
                f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B receipts are required"
            )
        errors.extend(t0_errors)
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": (emmc_cid or "").lower(),
        }

    if len(ra) != SD_RECEIPT_BYTES or len(rb) != SD_RECEIPT_BYTES:
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt lengths ({len(ra)}, {len(rb)}) != {SD_RECEIPT_BYTES}"
        )
        errors.extend(t0_errors)
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": (emmc_cid or "").lower(),
        }

    if dev_a is None or dev_b is None or dev_a == dev_b:
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: distinct physical st_dev required for dual-media Copy A vs B ({dev_a} vs {dev_b})"
        )

    if ra != rb:
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B receipt mismatch"
        )

    parsed_a: Optional[Any] = None
    parsed_b: Optional[Any] = None
    try:
        parsed_a = parse_sd_backup_receipt_bytes(ra)
        parsed_b = parse_sd_backup_receipt_bytes(rb)
    except Exception as exc:
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid FX3RCPT1 receipt: {exc}"
        )

    if parsed_a is None or parsed_b is None:
        errors.extend(t0_errors)
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": receipt_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": dev_a,
            "st_dev_b": dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": (emmc_cid or "").lower(),
        }

    if not getattr(parsed_a, "valid", False):
        errs_a = "; ".join(getattr(parsed_a, "errors", ()))
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a invalid ({errs_a})"
        )
    if not getattr(parsed_b, "valid", False):
        errs_b = "; ".join(getattr(parsed_b, "errors", ()))
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b invalid ({errs_b})"
        )
    if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))):
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a trivial manifest_sha256"
        )
    if _is_trivial_hex64(str(getattr(parsed_b, "manifest_sha256", ""))):
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b trivial manifest_sha256"
        )

    eff_serial = body_serial if body_serial is not None else "FX3SIM70200358"
    eff_cid = (emmc_cid if emmc_cid is not None else "11010030303847333000a1b2c3d49358").lower()

    if (
        not eff_serial
        or not BODY_SERIAL_RE.match(eff_serial)
        or eff_serial.lower() in FORBIDDEN_TRIVIAL_SERIALS
        or len(set(eff_serial)) <= 1
    ):
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial body_serial {eff_serial!r}"
        )

    if (
        not eff_cid
        or not HEX32_CID_RE.match(eff_cid)
        or eff_cid in FORBIDDEN_TRIVIAL_CIDS
    ):
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial 128-bit emmc_cid {eff_cid!r}"
        )

    if body_model_id != TARGET_MODEL_ID_INT or body_fw != TARGET_BODY_FW:
        t0_errors.append(
            f"{P358_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target must match {TARGET_MODEL_ID_HEX} fw {TARGET_BODY_FW}"
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
        h0_eq_h3_count = 0
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
        h0_eq_h3_count = max(0, P358_STORAGE_SURFACE_COUNT - drifted)

    if h0_eq_h3_count != P358_STORAGE_SURFACE_COUNT:
        t0_errors.append(
            f"{P358_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity failed ({h0_eq_h3_count}/{P358_STORAGE_SURFACE_COUNT})"
        )

    errors.extend(t0_errors)
    return {
        "tier0_receipt_verified": bool(len(t0_errors) == 0 and h0_eq_h3_count == P358_STORAGE_SURFACE_COUNT),
        "receipt_mode": receipt_mode,
        "h0_equals_h3_count": h0_eq_h3_count,
        "st_dev_a": dev_a,
        "st_dev_b": dev_b,
        "body_serial": eff_serial,
        "emmc_cid": eff_cid,
    }


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 76 USB-LAN, Auth, IPsec, Airplane, Cleaning)
# ---------------------------------------------------------------------------


def _is_valid_ipv4_len15(val: str) -> bool:
    if not isinstance(val, str) or not val or len(val) > P358_USB_LAN_MANUAL_FIELD_MAX_CHARS:
        return False
    parts = val.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    usb_lan_enabled: bool = True,
    usb_lan_ip_mode: str = "AUTO",
    usb_lan_connect_launch: str = "OFF",
    usb_lan_manual_ip: str = "192.168.1.100",
    multi_usb_concurrent_active: bool = False,
    wifi_concurrent_active: bool = False,
    airplane_mode: str = "ON",
    expect_airplane_mode_blocks_usb_lan: bool = False,
    claimed_reset_network_set_wipes_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    access_authen: str = P358_ACCESS_AUTHEN_DEFAULT,
    ipsec_enabled: bool = False,
    claimed_ipsec_available_on_ver7_or_authen_on: bool = False,
    claimed_fx6_has_ipsec_menu: bool = False,
    sensor_cleaning_requested: bool = False,
    battery_soc_pct: int = 85,
    power_switch_turned_off_for_blower: bool = True,
    dormant_anti_dust_or_shutter_barrier_requested: bool = False,
    claimed_fx3_has_shutter_when_pwr_off: bool = False,
    ir_remote_ctrl: str = "OFF",
    bluetooth_rmt_ctrl: str = "OFF",
    power_save_expected_active: bool = False,
    fx3a_body_variant: bool = False,
    auto_review: str = P358_AUTO_REVIEW_DEFAULT,
    expect_auto_review_triggers_after_movie: bool = False,
    claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
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
) -> P358CheckGroupDUsbLanAuthIpsecAirplaneCleaningAndTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if reset_action not in P358_VALID_RESET_ACTIONS:
        errors.append(
            f"{P358_GD_ERR_AIRPLANE_RESET_SPLIT}: invalid reset_action {reset_action!r}"
        )
    if shoot_mode not in P358_VALID_SHOOT_MODES:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: invalid shoot_mode {shoot_mode!r}"
        )
    if usb_lan_ip_mode not in P358_USB_LAN_IP_MODES:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: invalid usb_lan_ip_mode {usb_lan_ip_mode!r}"
        )
    if usb_lan_connect_launch not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: invalid usb_lan_connect_launch {usb_lan_connect_launch!r}"
        )
    manual_ip_ok = _is_valid_ipv4_len15(usb_lan_manual_ip)
    if usb_lan_ip_mode == "MANUAL" and not manual_ip_ok:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: invalid manual IPv4 {usb_lan_manual_ip!r} (max 15 chars)"
        )
    if usb_lan_enabled and (multi_usb_concurrent_active or wifi_concurrent_active):
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: USB-LAN is mutually exclusive with concurrent Multi/Micro USB (VMC-BNCM1) and Wi-Fi"
        )

    # Airplane Mode reset split & Zero-RF USB-LAN bypass
    if airplane_mode not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GD_ERR_AIRPLANE_RESET_SPLIT}: invalid airplane_mode {airplane_mode!r}"
        )
    if expect_airplane_mode_blocks_usb_lan:
        errors.append(
            f"{P358_GD_ERR_AIRPLANE_RESET_SPLIT}: [Airplane Mode]=On only disables Wi-Fi/BT RF and does NOT block USB-LAN wired Ethernet"
        )
    if claimed_reset_network_set_wipes_airplane_mode:
        errors.append(
            f"{P358_GD_ERR_AIRPLANE_RESET_SPLIT}: [Airplane Mode]=On is preserved across [Reset Network Set.] (TP1000844002)"
        )
    if claimed_initialize_preserves_airplane_mode:
        errors.append(
            f"{P358_GD_ERR_AIRPLANE_RESET_SPLIT}: [Initialize] resets [Airplane Mode] back to Off"
        )
    if reset_action == "INITIALIZE":
        effective_airplane = "OFF"
    else:
        effective_airplane = airplane_mode

    # Access Authen & Ver. 7.00+ disabled IPsec
    if access_authen not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: invalid access_authen {access_authen!r}"
        )
    fw_major = int(body_fw.split(".")[0]) if body_fw.split(".")[0].isdigit() else 0
    ipsec_disabled = fw_major >= P358_IPSEC_MIN_DISABLED_FW_MAJOR or access_authen == "ON"
    if ipsec_enabled and ipsec_disabled:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: [Security(IPsec)] is hard-disabled in Ver. 7.00+ and when [Access Authen. Settings]=On"
        )
    if claimed_ipsec_available_on_ver7_or_authen_on:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: [Security(IPsec)] is permanently unavailable on Ver. 7.00+ / Access Authen.=On (TP1000884069)"
        )
    if claimed_fx6_has_ipsec_menu:
        errors.append(
            f"{P358_GD_ERR_USBLAN_MUTEX_AUTH_OR_IPSEC_DISABLED}: ILME-FX6 has 0 IPsec UI bindings"
        )

    # [Sensor Cleaning] >= 51% gate & dormant Anti-dust / Shutter When Pwr OFF
    if sensor_cleaning_requested and battery_soc_pct < P358_SENSOR_CLEANING_MIN_BATTERY_PCT:
        errors.append(
            f"{P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST}: [Sensor Cleaning] requires >= 51%% battery (got {battery_soc_pct}%%)"
        )
    if sensor_cleaning_requested and not power_switch_turned_off_for_blower:
        errors.append(
            f"{P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST}: [Sensor Cleaning] requires physical power-switch OFF (_g 0x6221) before manual blower"
        )
    if dormant_anti_dust_or_shutter_barrier_requested or claimed_fx3_has_shutter_when_pwr_off:
        errors.append(
            f"{P358_GD_ERR_SENSOR_CLEANING_GATE_OR_DORMANT_ANTIDUST}: errno={P358_ERRNO_EOPNOTSUPP} (EOPNOTSUPP) dormant [Anti-dust Function]/[Shutter When Pwr OFF] has 0 exposed UI items on FX3"
        )

    # [IR Remote Ctrl] & [Auto Review] vs FX6
    if ir_remote_ctrl not in P358_VALID_ON_OFF or bluetooth_rmt_ctrl not in P358_VALID_ON_OFF:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: invalid IR/Bluetooth Remote control flag"
        )
    if ir_remote_ctrl == "ON" and fx3a_body_variant:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: ILME-FX3A physically removes front #5 IR receiver"
        )
    if ir_remote_ctrl == "ON" and bluetooth_rmt_ctrl == "ON":
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: [IR Remote Ctrl] is unusable while [Bluetooth Rmt Ctrl]=On"
        )
    if ir_remote_ctrl == "ON" and power_save_expected_active:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: [IR Remote Ctrl]=On blocks [Power Save Start Time]"
        )
    if auto_review not in P358_AUTO_REVIEW_MODES:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: invalid auto_review {auto_review!r}"
        )
    if expect_auto_review_triggers_after_movie:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: [Auto Review] is strictly Still-only and never triggers after Movie/S&Q"
        )
    if claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review:
        errors.append(
            f"{P358_GD_ERR_IR_REMOTE_OR_AUTO_REVIEW_OR_FX6}: FX6 uses APR + 2.5mm LANC + Rec Review (0 body IBIS cleaning, 0 IR menu, 0 Still Auto Review)"
        )

    # Mandatory Zero-RF & Fail-Closed Redlines + Slot 1 Lock + Tier-0 Receipt Gate
    if not slot1_contains_tier0_dump:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: Slot 1 must carry protected Tier-0 vault"
        )
    if not slot1_wp_locked:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: Slot 1 physical write-protect lock must remain enabled"
        )
    if slot1_write_requested:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: errno={P358_ERRNO_EROFS} (EROFS) Slot 1 write strictly forbidden"
        )
    if airplane_mode != "ON" and reset_action != "INITIALIZE":
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: bench Zero-RF requires [Airplane Mode]=ON (even with USB-LAN enabled)"
        )
    if emmc_write_count != 0:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: emmc_write_count must remain 0 (got {emmc_write_count})"
        )
    if e_nd_actuator_tx_count != 0:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: e_nd_actuator_tx_count must remain 0 (got {e_nd_actuator_tx_count})"
        )
    if wireless_rf_packets_emitted != 0:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: wireless_rf_packets_emitted must remain 0 (got {wireless_rf_packets_emitted})"
        )
    if usb_packets_transmitted != 0:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: usb_packets_transmitted must remain 0 (got {usb_packets_transmitted})"
        )
    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: simulated_passive_tx_bytes must remain 0 (got {simulated_passive_tx_bytes})"
        )
    if claim_hardware_live_attach_authorized:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: offline verifier never authorizes hardware_live_attachment_authorized"
        )
    if claim_persistent_emmc_writes_authorized:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: offline verifier never authorizes persistent_emmc_writes_authorized"
        )
    if claim_cross_model_flash_authorized:
        errors.append(
            f"{P358_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: cross-model partition flashing is strictly BLOCKED / NO-GO"
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
        errors=errors,
    )
    if not tier0["tier0_receipt_verified"] and tier0["receipt_mode"] == "NO_RECEIPT_OFFLINE":
        warnings.append(
            "Awaiting physical dual-media 528B FX3RCPT1 Tier-0 receipts (16/16 H0 == H3)."
        )

    return P358CheckGroupDUsbLanAuthIpsecAirplaneCleaningAndTier0Result(
        group_id=P358_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        body_fw=body_fw,
        reset_action=reset_action,
        usb_lan_enabled=usb_lan_enabled,
        usb_lan_ip_mode=usb_lan_ip_mode,
        usb_lan_connect_launch=usb_lan_connect_launch,
        usb_lan_manual_ip_valid=manual_ip_ok,
        multi_usb_concurrent_active=multi_usb_concurrent_active,
        wifi_concurrent_active=wifi_concurrent_active,
        airplane_mode=airplane_mode,
        effective_airplane_mode_after_reset=effective_airplane,
        airplane_mode_blocks_usb_lan=False,
        access_authen=access_authen,
        access_authen_protocol=P358_ACCESS_AUTHEN_PROTOCOLS,
        ipsec_enabled=ipsec_enabled,
        ipsec_hard_disabled_ver7_or_authen=ipsec_disabled,
        fx6_ipsec_ui_binding_count=P358_FX6_IPSEC_UI_BINDING_COUNT,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_soc_pct=battery_soc_pct,
        power_switch_turned_off_for_blower=power_switch_turned_off_for_blower,
        fx3_anti_dust_ui_count=P358_FX3_ANTI_DUST_UI_COUNT,
        fx3_shutter_when_pwr_off_ui_count=P358_FX3_SHUTTER_WHEN_PWR_OFF_UI_COUNT,
        ir_remote_ctrl=ir_remote_ctrl,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        fx3a_body_variant=fx3a_body_variant,
        auto_review=auto_review,
        fx6_body_ibis_ultrasonic_cleaning=P358_FX6_BODY_IBIS_ULTRASONIC_CLEANING,
        fx6_ir_remote_ui_count=P358_FX6_IR_REMOTE_UI_COUNT,
        fx6_still_auto_review_ui_count=P358_FX6_STILL_AUTO_REVIEW_UI_COUNT,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_data_sector_writes=PHASE358_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        wireless_rf_packets_emitted=PHASE358_WIRELESS_RF_PACKETS_EMITTED,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P358_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 358 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P358_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    media_type: str = "CFEXPRESS_A",
    # Group A
    metering_mode: str = P358_METERING_MODE_DEFAULT,
    face_priority_in_multi_metering: str = "ON",
    spot_metering_point: str = P358_SPOT_METERING_POINT_DEFAULT,
    focus_area: str = "SPOT_M",
    ciz_or_digital_zoom_active: bool = False,
    desqueeze_display: str = "OFF",
    ael_w_shutter: str = P358_AEL_W_SHUTTER_DEFAULT,
    exposure_step: str = P358_EXPOSURE_STEP_DEFAULT,
    expect_metering_not_locked_to_multi_under_zoom: bool = False,
    expect_spot_point_links_on_wide_zone_or_center_fix: bool = False,
    expect_ael_w_shutter_active_in_movie: bool = False,
    claimed_ael_w_shutter_wiped_by_camera_reset: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    expect_exposure_step_alters_shutter_angle: bool = False,
    expect_mm_meter_changes_with_ei_in_cine_ei: bool = False,
    fx6_ae_mode: str = "STANDARD",
    fx6_ae_level: float = 0.0,
    fx6_ae_speed: int = 0,
    fx6_detect_window: str = "1",
    fx6_detect_window_width: int = P358_FX6_DETECT_WINDOW_WIDTH_DEFAULT,
    claimed_fx6_ae_level_limited_to_2ev: bool = False,
    claimed_fx6_has_still_spot_or_ael_shutter: bool = False,
    picture_profile: str = P358_PICTURE_PROFILE_DEFAULT,
    internal_rec_active: bool = True,
    hdmi_only_output: bool = False,
    hdmi_raw_output: bool = False,
    select_lut: str = P358_SELECT_LUT_DEFAULT,
    user_lut_slot_count: int = P358_USER_LUT_SLOT_MAX,
    user_lut_cube_points: int = 33,
    user_lut_filename: str = "s709_custom_v1.cube",
    embed_lut_file: str = "ON",
    claimed_pp1_to_pp11_wiped_by_reset_or_init: bool = False,
    claimed_pplut_resists_reset_or_init: bool = False,
    claimed_pplut_active_in_still: bool = False,
    expect_4k_hdmi_with_pplut_internal_rec: bool = False,
    claimed_pp_active_with_log_shooting_on: bool = False,
    claimed_user_lut_wiped_by_camera_reset: bool = False,
    claimed_fx3_supports_mxf_or_sidecar_cube_embed: bool = False,
    expect_embed_lut_enabled_on_sdhc: bool = False,
    claimed_embed_lut_under_color_tone: bool = False,
    claimed_fx6_user_lut_pool_not_50: bool = False,
    # Group B
    steadyshot_movie: str = P358_STEADYSHOT_MOVIE_DEFAULT,
    steadyshot_still: str = P358_STEADYSHOT_STILL_DEFAULT,
    steadyshot_adjust: str = P358_STEADYSHOT_ADJUST_DEFAULT,
    steadyshot_focal_length_mm: int = P358_STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM,
    exposed_focal_lengths_mm: Tuple[int, ...] = P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    frame_rate_fps: float = 23.98,
    e_mount_sony_lens: bool = True,
    expect_steadyshot_active_under_lockout: bool = False,
    expect_catalyst_gyro_available: bool = False,
    dormant_steadyshot_mode_requested: Optional[str] = None,
    claimed_steadyshot_resists_camera_reset: bool = False,
    claimed_fx6_has_body_ibis: bool = False,
    exposed_playback_readonly_items: Tuple[str, ...] = P358_PLAYBACK_5_READONLY_ITEMS,
    image_index: str = P358_IMAGE_INDEX_DEFAULT,
    display_rotation: str = P358_DISPLAY_ROTATION_DEFAULT,
    focus_frame_display: str = "OFF",
    cont_pb_for_interval: str = "OFF",
    play_speed_for_interval: int = P358_PLAY_SPEED_DEFAULT,
    claimed_playback_5_wiped_by_camera_reset: bool = False,
    claimed_interval_pb_generates_video_or_writes_card: bool = False,
    file_name_format: str = P358_FILE_NAME_FORMAT_DEFAULT,
    camid_reel_stem: str = "A001C001_230101AB",
    title_name: str = P358_TITLE_NAME_DEFAULT,
    fx6_title_prefix_chars: int = 4,
    claimed_camid_reel_stem_is_37_chars: bool = False,
    expect_camid_reel_allowed_on_sdhc: bool = False,
    claimed_file_settings_wiped_by_camera_reset: bool = False,
    create_new_folder_on_slot1_requested: bool = False,
    forced_file_no_reset_on_slot1_requested: bool = False,
    select_rec_folder_write_on_slot1_requested: bool = False,
    series_counter_reset_on_slot1_requested: bool = False,
    # Group C
    shutter_mode: str = "SPEED",
    xlr_h1_attached: bool = True,
    claimed_xlr_h1_has_custom_or_rec_keys: bool = False,
    still_custom_controls: Tuple[str, ...] = P358_STILL_CUSTOM_CONTROLS,
    movie_custom_factory_defaults: Mapping[str, str] = P358_MOVIE_CUSTOM_FACTORY_DEFAULTS,
    playback_custom_controls: Tuple[str, ...] = P358_PLAYBACK_CUSTOM_CONTROLS,
    claimed_fn_assignable_in_still_or_movie: bool = False,
    claimed_pb_includes_c4_delete: bool = False,
    claimed_custom_key_wiped_by_camera_reset: bool = False,
    dormant_custom_key_requested: Optional[str] = None,
    diff_set_items: Tuple[str, ...] = P358_DIFF_SET_EXACT_8_ITEMS,
    diff_set_pp_checkbox_checked: bool = True,
    diff_set_transition: str = "NONE",
    claimed_pp_checkbox_wiped_by_reset_or_init: bool = False,
    claimed_common_to_separate_copies_custom_wb_to_movie: bool = False,
    claimed_separate_to_common_discards_still_av_tv_wb: bool = False,
    claimed_shutter_angle_shared_when_diffset_unchecked: bool = False,
    claimed_diff_set_saved_in_campr: bool = False,
    gamma_display_assist: str = "OFF",
    gamma_disp_assist_type: str = P358_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
    display_lut: str = "ON",
    shooting_still_in_log_mode: bool = False,
    dormant_gamma_assist_slog2_requested: bool = False,
    claimed_gamma_assist_active_when_log_movie_on: bool = False,
    claimed_gamma_assist_applies_to_hdmi_or_tv: bool = False,
    claimed_gamma_assist_wiped_by_camera_reset: bool = False,
    claimed_fx6_lacks_assignable_or_has_still_split: bool = False,
    claimed_fx6_has_gamma_display_assist_ui: bool = False,
    # Group D + Tier-0
    usb_lan_enabled: bool = True,
    usb_lan_ip_mode: str = "AUTO",
    usb_lan_connect_launch: str = "OFF",
    usb_lan_manual_ip: str = "192.168.1.100",
    multi_usb_concurrent_active: bool = False,
    wifi_concurrent_active: bool = False,
    airplane_mode: str = "ON",
    expect_airplane_mode_blocks_usb_lan: bool = False,
    claimed_reset_network_set_wipes_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    access_authen: str = P358_ACCESS_AUTHEN_DEFAULT,
    ipsec_enabled: bool = False,
    claimed_ipsec_available_on_ver7_or_authen_on: bool = False,
    claimed_fx6_has_ipsec_menu: bool = False,
    sensor_cleaning_requested: bool = False,
    battery_soc_pct: int = 85,
    power_switch_turned_off_for_blower: bool = True,
    dormant_anti_dust_or_shutter_barrier_requested: bool = False,
    claimed_fx3_has_shutter_when_pwr_off: bool = False,
    ir_remote_ctrl: str = "OFF",
    bluetooth_rmt_ctrl: str = "OFF",
    power_save_expected_active: bool = False,
    fx3a_body_variant: bool = False,
    auto_review: str = P358_AUTO_REVIEW_DEFAULT,
    expect_auto_review_triggers_after_movie: bool = False,
    claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
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
) -> RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport:
    donor = inspect_phase358_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p358_check_group_a_metering_expstep_pp_and_userlut(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        metering_mode=metering_mode,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        spot_metering_point=spot_metering_point,
        focus_area=focus_area,
        ciz_or_digital_zoom_active=ciz_or_digital_zoom_active,
        desqueeze_display=desqueeze_display,
        ael_w_shutter=ael_w_shutter,
        exposure_step=exposure_step,
        expect_metering_not_locked_to_multi_under_zoom=expect_metering_not_locked_to_multi_under_zoom,
        expect_spot_point_links_on_wide_zone_or_center_fix=expect_spot_point_links_on_wide_zone_or_center_fix,
        expect_ael_w_shutter_active_in_movie=expect_ael_w_shutter_active_in_movie,
        claimed_ael_w_shutter_wiped_by_camera_reset=claimed_ael_w_shutter_wiped_by_camera_reset,
        claimed_exposure_step_wiped_by_camera_reset=claimed_exposure_step_wiped_by_camera_reset,
        expect_exposure_step_alters_shutter_angle=expect_exposure_step_alters_shutter_angle,
        expect_mm_meter_changes_with_ei_in_cine_ei=expect_mm_meter_changes_with_ei_in_cine_ei,
        fx6_ae_mode=fx6_ae_mode,
        fx6_ae_level=fx6_ae_level,
        fx6_ae_speed=fx6_ae_speed,
        fx6_detect_window=fx6_detect_window,
        fx6_detect_window_width=fx6_detect_window_width,
        claimed_fx6_ae_level_limited_to_2ev=claimed_fx6_ae_level_limited_to_2ev,
        claimed_fx6_has_still_spot_or_ael_shutter=claimed_fx6_has_still_spot_or_ael_shutter,
        picture_profile=picture_profile,
        internal_rec_active=internal_rec_active,
        hdmi_only_output=hdmi_only_output,
        hdmi_raw_output=hdmi_raw_output,
        select_lut=select_lut,
        user_lut_slot_count=user_lut_slot_count,
        user_lut_cube_points=user_lut_cube_points,
        user_lut_filename=user_lut_filename,
        media_type=media_type,
        embed_lut_file=embed_lut_file,
        claimed_pp1_to_pp11_wiped_by_reset_or_init=claimed_pp1_to_pp11_wiped_by_reset_or_init,
        claimed_pplut_resists_reset_or_init=claimed_pplut_resists_reset_or_init,
        claimed_pplut_active_in_still=claimed_pplut_active_in_still,
        expect_4k_hdmi_with_pplut_internal_rec=expect_4k_hdmi_with_pplut_internal_rec,
        claimed_pp_active_with_log_shooting_on=claimed_pp_active_with_log_shooting_on,
        claimed_user_lut_wiped_by_camera_reset=claimed_user_lut_wiped_by_camera_reset,
        claimed_fx3_supports_mxf_or_sidecar_cube_embed=claimed_fx3_supports_mxf_or_sidecar_cube_embed,
        expect_embed_lut_enabled_on_sdhc=expect_embed_lut_enabled_on_sdhc,
        claimed_embed_lut_under_color_tone=claimed_embed_lut_under_color_tone,
        claimed_fx6_user_lut_pool_not_50=claimed_fx6_user_lut_pool_not_50,
    )

    gb = evaluate_p358_check_group_b_ibis_playback_and_file_slot1(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        media_type=media_type,
        steadyshot_movie=steadyshot_movie,
        steadyshot_still=steadyshot_still,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_length_mm=steadyshot_focal_length_mm,
        exposed_focal_lengths_mm=exposed_focal_lengths_mm,
        frame_rate_fps=frame_rate_fps,
        hdmi_raw_output=hdmi_raw_output,
        desqueeze_display=desqueeze_display,
        e_mount_sony_lens=e_mount_sony_lens,
        expect_steadyshot_active_under_lockout=expect_steadyshot_active_under_lockout,
        expect_catalyst_gyro_available=expect_catalyst_gyro_available,
        dormant_steadyshot_mode_requested=dormant_steadyshot_mode_requested,
        claimed_steadyshot_resists_camera_reset=claimed_steadyshot_resists_camera_reset,
        claimed_fx6_has_body_ibis=claimed_fx6_has_body_ibis,
        exposed_playback_readonly_items=exposed_playback_readonly_items,
        image_index=image_index,
        display_rotation=display_rotation,
        focus_frame_display=focus_frame_display,
        cont_pb_for_interval=cont_pb_for_interval,
        play_speed_for_interval=play_speed_for_interval,
        claimed_playback_5_wiped_by_camera_reset=claimed_playback_5_wiped_by_camera_reset,
        claimed_interval_pb_generates_video_or_writes_card=claimed_interval_pb_generates_video_or_writes_card,
        file_name_format=file_name_format,
        camid_reel_stem=camid_reel_stem,
        title_name=title_name,
        fx6_title_prefix_chars=fx6_title_prefix_chars,
        claimed_camid_reel_stem_is_37_chars=claimed_camid_reel_stem_is_37_chars,
        expect_camid_reel_allowed_on_sdhc=expect_camid_reel_allowed_on_sdhc,
        claimed_file_settings_wiped_by_camera_reset=claimed_file_settings_wiped_by_camera_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        create_new_folder_on_slot1_requested=create_new_folder_on_slot1_requested,
        forced_file_no_reset_on_slot1_requested=forced_file_no_reset_on_slot1_requested,
        select_rec_folder_write_on_slot1_requested=select_rec_folder_write_on_slot1_requested,
        series_counter_reset_on_slot1_requested=series_counter_reset_on_slot1_requested,
    )

    gc = evaluate_p358_check_group_c_xlrh1_customkey_diffset8_and_gammadisp(
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        shutter_mode=shutter_mode,
        xlr_h1_attached=xlr_h1_attached,
        claimed_xlr_h1_has_custom_or_rec_keys=claimed_xlr_h1_has_custom_or_rec_keys,
        still_custom_controls=still_custom_controls,
        movie_custom_factory_defaults=movie_custom_factory_defaults,
        playback_custom_controls=playback_custom_controls,
        claimed_fn_assignable_in_still_or_movie=claimed_fn_assignable_in_still_or_movie,
        claimed_pb_includes_c4_delete=claimed_pb_includes_c4_delete,
        claimed_custom_key_wiped_by_camera_reset=claimed_custom_key_wiped_by_camera_reset,
        dormant_custom_key_requested=dormant_custom_key_requested,
        diff_set_items=diff_set_items,
        diff_set_pp_checkbox_checked=diff_set_pp_checkbox_checked,
        diff_set_transition=diff_set_transition,
        claimed_pp_checkbox_wiped_by_reset_or_init=claimed_pp_checkbox_wiped_by_reset_or_init,
        claimed_common_to_separate_copies_custom_wb_to_movie=claimed_common_to_separate_copies_custom_wb_to_movie,
        claimed_separate_to_common_discards_still_av_tv_wb=claimed_separate_to_common_discards_still_av_tv_wb,
        claimed_shutter_angle_shared_when_diffset_unchecked=claimed_shutter_angle_shared_when_diffset_unchecked,
        claimed_diff_set_saved_in_campr=claimed_diff_set_saved_in_campr,
        gamma_display_assist=gamma_display_assist,
        gamma_disp_assist_type=gamma_disp_assist_type,
        display_lut=display_lut,
        select_lut=select_lut,
        shooting_still_in_log_mode=shooting_still_in_log_mode,
        dormant_gamma_assist_slog2_requested=dormant_gamma_assist_slog2_requested,
        claimed_gamma_assist_active_when_log_movie_on=claimed_gamma_assist_active_when_log_movie_on,
        claimed_gamma_assist_applies_to_hdmi_or_tv=claimed_gamma_assist_applies_to_hdmi_or_tv,
        claimed_gamma_assist_wiped_by_camera_reset=claimed_gamma_assist_wiped_by_camera_reset,
        claimed_fx6_lacks_assignable_or_has_still_split=claimed_fx6_lacks_assignable_or_has_still_split,
        claimed_fx6_has_gamma_display_assist_ui=claimed_fx6_has_gamma_display_assist_ui,
    )

    gd = evaluate_p358_check_group_d_usblan_auth_ipsec_airplane_cleaning_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        body_model_id=body_model_id,
        body_fw=body_fw,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        usb_lan_enabled=usb_lan_enabled,
        usb_lan_ip_mode=usb_lan_ip_mode,
        usb_lan_connect_launch=usb_lan_connect_launch,
        usb_lan_manual_ip=usb_lan_manual_ip,
        multi_usb_concurrent_active=multi_usb_concurrent_active,
        wifi_concurrent_active=wifi_concurrent_active,
        airplane_mode=airplane_mode,
        expect_airplane_mode_blocks_usb_lan=expect_airplane_mode_blocks_usb_lan,
        claimed_reset_network_set_wipes_airplane_mode=claimed_reset_network_set_wipes_airplane_mode,
        claimed_initialize_preserves_airplane_mode=claimed_initialize_preserves_airplane_mode,
        access_authen=access_authen,
        ipsec_enabled=ipsec_enabled,
        claimed_ipsec_available_on_ver7_or_authen_on=claimed_ipsec_available_on_ver7_or_authen_on,
        claimed_fx6_has_ipsec_menu=claimed_fx6_has_ipsec_menu,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_soc_pct=battery_soc_pct,
        power_switch_turned_off_for_blower=power_switch_turned_off_for_blower,
        dormant_anti_dust_or_shutter_barrier_requested=dormant_anti_dust_or_shutter_barrier_requested,
        claimed_fx3_has_shutter_when_pwr_off=claimed_fx3_has_shutter_when_pwr_off,
        ir_remote_ctrl=ir_remote_ctrl,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        power_save_expected_active=power_save_expected_active,
        fx3a_body_variant=fx3a_body_variant,
        auto_review=auto_review,
        expect_auto_review_triggers_after_movie=expect_auto_review_triggers_after_movie,
        claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review=claimed_fx6_has_body_ibis_cleaning_or_ir_or_auto_review,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_write_requested=slot1_write_requested,
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
        go_no_go = (
            P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE
        )
        overall_status = (
            P358_GO_NO_GO_BLOCKED_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_FAILURE
        )
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P358_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = (
            P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED
        )
        overall_status = (
            P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED
        )

    report = RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport(
        schema_version=P358_SCHEMA,
        phase_version=P358_VERSION,
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
        h0_h3_surface_count=P358_STORAGE_SURFACE_COUNT,
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
        fx3_ibis_47_focal_table_exact=(
            tuple(exposed_focal_lengths_mm) == P358_IBIS_EXACT_47_FOCAL_LENGTHS_MM
        ),
        fx6_body_ibis_present=False,
        xlr_h1_assignable_keys_present=False,
        fx3_diff_set_8_items_exact=(tuple(diff_set_items) == P358_DIFF_SET_EXACT_8_ITEMS),
        fx3_gamma_assist_slog2_exposed=P358_FX3_GAMMA_ASSIST_SLOG2_EXPOSED,
        fx3_ipsec_ver7_available=False,
        fx3_anti_dust_shutter_barrier_exposed=False,
        emmc_write_count=PHASE358_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE358_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE358_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE358_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=0,
        slot1_data_sector_writes=PHASE358_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE358_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE358_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE358_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport(
        **{
            **report.to_dict(),
            "check_group_a": ga,
            "check_group_b": gb,
            "check_group_c": gc,
            "check_group_d": gd,
            "donor_inspection": donor,
            "errors": report.errors,
            "warnings": report.warnings,
            "report_sha256": digest,
        }
    )


def run_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
    **kwargs: Any,
) -> RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport:
    return evaluate_realhw_metering_pplut_ibis_customkey_diffset8_gammadisp_and_usblan_cleaning_preflight(
        **kwargs
    )


def verify_phase358_report(
    payload: Union[
        Mapping[str, Any],
        RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport,
    ],
) -> Phase358ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P358_SCHEMA:
        errors.append(
            f"schema_version mismatch: {payload.get('schema_version')!r} != {P358_SCHEMA!r}"
        )
    if payload.get("sony_help_guide_id") != P358_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_358_VALID_GO_NO_GO_VALUES:
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
        "fx6_body_ibis_present",
        "xlr_h1_assignable_keys_present",
        "fx3_gamma_assist_slog2_exposed",
        "fx3_ipsec_ver7_available",
        "fx3_anti_dust_shutter_barrier_exposed",
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
        errors.append(
            f"report_sha256 mismatch: {payload.get('report_sha256')!r} != {expected_sha!r}"
        )

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P358_GO_NO_GO_METERING_PPLUT_IBIS_CUSTOMKEY_DIFFSET8_GAMMADISP_AND_USBLAN_CLEANING_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase358ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase358_markdown(
    report: RealHwMeteringPpLutIbisCustomKeyDiffSet8GammaDispAndUsbLanCleaningReport,
) -> str:
    lines = [
        f"# Phase 358 — 22nd Physical Bench Readiness Preflight (`{report.schema_version}`)",
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
        f"metering=`{report.check_group_a.metering_mode}`, exp_step=`{report.check_group_a.exposure_step}`, "
        f"pp=`{report.check_group_a.picture_profile}`, embed_lut=`{report.check_group_a.effective_embed_lut_file}`, "
        f"fx6_ae_level=`{report.check_group_a.fx6_ae_level}` ({report.check_group_a.fx6_ae_level_steps} steps)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"steadyshot=`{report.check_group_b.effective_steadyshot_movie}`, "
        f"focal_entries={report.check_group_b.focal_table_entry_count}, "
        f"pb_readonly={len(report.check_group_b.playback_readonly_items)}, "
        f"filename=`{report.check_group_b.effective_file_name_format}`",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"xlr_h1_keys={report.check_group_c.xlr_h1_assignable_button_count}, "
        f"diff_set_items={len(report.check_group_c.diff_set_items)}, "
        f"gamma_assist=`{report.check_group_c.effective_gamma_display_assist}`",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"usb_lan=`{report.check_group_d.usb_lan_enabled}`, "
        f"access_authen=`{report.check_group_d.access_authen}`, "
        f"ipsec_disabled=`{report.check_group_d.ipsec_hard_disabled_ver7_or_authen}`, "
        f"airplane=`{report.check_group_d.effective_airplane_mode_after_reset}`, "
        f"slot1_mut=`{report.check_group_d.slot1_tier0_vault_mutated}`",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
