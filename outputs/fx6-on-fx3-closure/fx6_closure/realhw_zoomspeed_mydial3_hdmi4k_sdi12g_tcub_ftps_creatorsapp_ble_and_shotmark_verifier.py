"""Phase 371 Milestone — 24th Physical Bench Readiness Verifier (`24/24` Verifiers).

Implements `preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark`
(short CLI alias `preflight-phase371`) aligned with Global Sony Real-Hardware Empirical
Intelligence Waves 79-80 across Check Groups A-D and the mandatory `16/16 H0 == H3`
dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (Wave 79 Zoom Speed Split & Dial Customize 5-Item / Zero-EVF Operation):
  - `[Zoom Range]` (`Optical`/`CIZ` `4K 1.5x, HD 2.0x`/`Digital 4.0x`; `Smart Zoom` Still
    M/S only; resists Reset) & `[Zoom Ring Rotate]` (resists Reset) vs Resettable speed trio:
    `[Zoom Lever Speed]` (`1st=3, 2nd=8` Stby/REC), `[Custom Key Z. Speed]` (Fixed `1..8`
    only, ZERO `Variable` mode), and `[Remote Zoom Speed]` (`Variable`/`Fix` via
    `BKID_APP_setting_fixed_zoom_speed_type` + `1..8`), plus CIZ/Digital lockouts (`RAW`,
    `100/120p`, `S&Q>=100fps`, HDMI `RAW`, Focus Area/Tracking/Face AF/Metering=Multi
    lockouts) vs FX6 `Zoom Type` (no Digital Zoom) & `Handle Zoom` (`0..99` is HUD position
    display only).
  - `[Dial Customize]` strictly 5 Initialize-only items (`Custom Key/Dial Set.`, `My Dial
    Settings` temporary unlock of `Lock Operation Parts`, `Av/Tv Rotate`, `Function
    Ring(Lens)` `Power Focus` vs `APS-C/FF`, `Lock Operation Parts`; dormant `Dial Setup` /
    `Dial/Wheel Lock` / `Rear Dial L/R` rejected). `[Different Set for Still/Mv]` 8-bit
    mask (`Picture Profile` resists BOTH Reset & Initialize) vs `12+12` `Fn` slots, 4 Monitor
    `[DISP]` pages (`Graphic Display` & entire `[Finder/Monitor]` dormant on EVF-less FX3),
    and `[Select LUT]`/`[Display LUT]` vs `[Gamma Display Assist]` (inactive when `Log
    Shooting != Off`).
- **Check Group B** (Wave 79 External Output HDMI 4K 10-bit/RAW vs FX6 12G-SDI Dual-Pipeline):
  - FX3 `[HDMI Resolution]` strictly 4 options (`Auto`/`2160p`/`1080p`/`1080i`, no `720p`),
    `[4K Output Set.(HDMI Only)]` strictly 6 `10bit 4:2:2` modes (no `4:2:0`, dormant
    `24.00p 8bit` & `24p/60p Output` rejected, `24.00p` reboot gate), `[HDMI Info. Display]
    = On` LCD blanking strictly when `Rec. Media = On & RAW = Off` (auto-Clean HDMI + active
    LCD under `Off(HDMI Only)` or `RAW = On`), and Sony ELF typos
    (`BKID_APP_setting_ctrl_for_hmdi`, `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`,
    `BKID_APP_setting_4ch_output_ch`) vs FX6 25-combo `12G/6G/3G-SDI + HDMI` matrix
    (`SDI/HDMI Remote I/F` vs `Parallel Rec`).
- **Check Group C** (Wave 80 `[TC/UB]` `VMC-BNCM1` TC-IN-Only & `[FTP Transfer Func.]`):
  - All 7 FX3 `[TC/UB]` + `[TC/UB Disp. Setting]` items resist `[Camera Settings Reset]`
    (`Initialize`/Delete/FW update clear `Preset`; Sony typo `TC_MAKE_REGENRATE`);
    `DF`/`NDF` selectable strictly on NTSC `29.97p`/`59.94p`/`119.88p` (`23.98p`/`24.00p`/PAL
    locked `NDF`); `VMC-BNCM1` unidirectional `TC-IN-Only` via body Multi/Micro USB
    (`Preset` + `Free Run` -> `EXT-LK`, forbidden on `XLR-H1` handle port) vs FX6 physical
    BNC `TC IN/OUT` switch + `Clock` mode + hex-only `Users Bit` (`Title1(ASCII)` is Clip
    Title).
  - FX3 `[FTP Transfer Func.]` (`Server 1..9`, plaintext `FTP` & Explicit `AUTH TLS`
    `FTPES` via OpenSSL 3.0 `libInfraFtpClient.so` Passive-only; zero SSH-SFTP / Implicit
    FTPS; `Slot 1` `cacert.pem` & `SONY/SETTING/<Model>/FTPSET/FTPSET01..10.DAT`
    password-encrypted + mandatory reboot -> blocked `EROFS=30` on Tier-0 `Slot 1`) vs FX6
    `File Transfer` (`Slot B` `certification.pem`, Active/Passive, Chunk Proxy upload).
- **Check Group D** (Wave 80 `Creators' App` 5-GATT BLE / `G114` `[Airplane Mode]` Erratum &
  Playback Write Matrix `Slot 1 EROFS=30` + Tier-0 Receipt Gate):
  - `Creators' App` 5 BLE GATT tables (`8000CC00/DD00/EE00/FF00/BB00`), Ver. 3.00+ migration
    of `[Location Info. Link Set.]` to smartphone app (`8000DD00`), `bt_stack.conf`
    `LMP_WAKEUP_CONFIG` `[Cnct. while Power OFF]`, BLE pairing wiped by `[Reset Network
    Set.]` & `[Initialize]`, and **Wave 80 `G114` erratum**: `[Airplane Mode] = On` is NOT
    cleared by `[Reset Network Set.]` (`Initialize`-only) + mandatory electrical isolation of
    `USB-LAN` (`rf_tx_packets == 0`).
  - Playback write matrix (`libmpr.so` / `libInfraFsys.so`): `[Add/Delete Shot Mark 1/2]`
    (`*M01.XML` + `AVF_INFO`), `[Rating]` (`<xmp:Rating>`), `[Protect]` (`Fsys_Chmod`),
    `[Delete]`, and asymmetric `[Copy]` (`Slot 1 -> Slot 2` read-only safe on `Slot 1` vs
    `Slot 2 -> Slot 1` blocked `EROFS=30`, `slot1_sector_writes == 0`) vs FX6 `Clip Flag`
    (`OK`/`NG`/`KEEP`).
  - **Tier-0 Receipt Gate**: Dual-media `528 B FX3RCPT1` Copy A & Copy B with distinct
    `st_dev`, `16/16 H0 == H3`, non-trivial serial/CID, `0x91030080` + fw `7.02`.
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

P371_VERSION = "phase371_v1"
PHASE371_VERSION = P371_VERSION
PHASE_371_VERSION = P371_VERSION

P371_SCHEMA = (
    "realhw_preflight24_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_shotmark_v1"
)
P371_SCHEMA_VERSION = P371_SCHEMA
PHASE_371_SCHEMA = P371_SCHEMA
REALHW_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_SHOTMARK_SCHEMA = (
    P371_SCHEMA
)

P371_SONY_HELP_GUIDE_ID = "ilc/2210"
P371_STORAGE_SURFACE_COUNT = 16
P371_HEADER_READ_BYTES = 64

P371_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED = (
    "READONLY_PREFLIGHT24_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED"
)
P371_GO_NO_GO_BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE = (
    "BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE"
)
PHASE_371_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED,
    P371_GO_NO_GO_BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE,
)

P371_CHECK_GROUP_A_ID = "p371_ga_zoomspeed_mydial3_diffset8_zeroevf_lut_fx6_handle"
P371_CHECK_GROUP_B_ID = "p371_gb_hdmi4k_10bit_raw_blank_typos_fx6_sdi12g_matrix"
P371_CHECK_GROUP_C_ID = "p371_gc_tcub_vmc_bncm1_extlk_ftpes_explicit_slot1_dat"
P371_CHECK_GROUP_D_ID = "p371_gd_creatorsapp_ble_g114_airplane_playback_shotmark_tier0"
PHASE_371_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P371_CHECK_GROUP_A_ID,
    P371_CHECK_GROUP_B_ID,
    P371_CHECK_GROUP_C_ID,
    P371_CHECK_GROUP_D_ID,
)

# Errno constants
P371_ERRNO_EPERM = 1
P371_ERRNO_EBUSY = 16
P371_ERRNO_EINVAL = 22
P371_ERRNO_EROFS = 30
P371_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE371_EMMC_WRITE_COUNT = 0
PHASE371_E_ND_ACTUATOR_TX_COUNT = 0
PHASE371_E_ND_I2C_TX_BYTES = 0
PHASE371_RF_TX_PACKETS = 0
PHASE371_RF_PACKETS_TRANSMITTED = 0
PHASE371_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE371_RF_NVS_MUTATION_BYTES = 0
PHASE371_SLOT1_SECTOR_WRITES = 0
PHASE371_SLOT1_DATA_SECTOR_WRITES = 0
PHASE371_USB_PACKETS_TRANSMITTED = 0
PHASE371_PASSIVE_TX_BYTES_EMITTED = 0
PHASE371_RAW_FIRMWARE_BYTES_LEAKED = 0

P371_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P371_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P371_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P371_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")

# ---------------------------------------------------------------------------
# Wave 79 Group A Constants: Zoom Speed, Dial Customize 5-Item, DiffSet-8, Zero-EVF, LUT
# ---------------------------------------------------------------------------

P371_ZOOM_RANGE_MODES: Tuple[str, ...] = (
    "OPTICAL_ONLY",
    "CLEAR_IMAGE_ZOOM",
    "DIGITAL_ZOOM",
)
P371_ZOOM_RANGE_DEFAULT = "OPTICAL_ONLY"
P371_ZOOM_CIZ_MAX_4K = 1.5
P371_ZOOM_CIZ_MAX_HD = 2.0
P371_ZOOM_DIGITAL_MAX = 4.0
P371_SMART_ZOOM_STILL_M_MAX = 1.5
P371_SMART_ZOOM_STILL_S_MAX = 2.0
P371_ZOOM_RING_ROTATE_MODES: Tuple[str, ...] = ("LEFT_W_RIGHT_T", "RIGHT_W_LEFT_T")
P371_ZOOM_RING_ROTATE_DEFAULT = "LEFT_W_RIGHT_T"
P371_ZOOM_SPEED_MIN = 1
P371_ZOOM_SPEED_MAX = 8
P371_ZOOM_LEVER_1ST_DEFAULT = 3
P371_ZOOM_LEVER_2ND_DEFAULT = 8
P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT = 3
P371_CUSTOM_KEY_ZOOM_MODES: Tuple[str, ...] = ("FIXED",)
P371_REMOTE_ZOOM_SPEED_TYPES: Tuple[str, ...] = ("VARIABLE", "FIX")
P371_REMOTE_ZOOM_SPEED_TYPE_BKID = "BKID_APP_setting_fixed_zoom_speed_type"
P371_RAW_STILL_FORMATS: Tuple[str, ...] = ("RAW", "RAW_AND_JPEG", "RAW_AND_HEIF")
P371_CIZ_DIGITAL_LOCKED_FOCUS_AREAS: Tuple[str, ...] = ("CENTER_PRIORITY_AF",)
P371_FX6_ZOOM_TYPES: Tuple[str, ...] = ("OPTICAL_ONLY", "CLEAR_IMAGE_ZOOM")
P371_FX6_HANDLE_ZOOM_MODES: Tuple[str, ...] = ("OFF", "LOW", "HIGH", "VARIABLE")
P371_FX6_HANDLE_ZOOM_HUD_RANGE: Tuple[int, int] = (0, 99)

P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS: Tuple[str, ...] = (
    "Custom Key/Dial Set.",
    "My Dial Settings",
    "Av/Tv Rotate",
    "Function Ring(Lens)",
    "Lock Operation Parts",
)
P371_DIAL_CUSTOMIZE_DORMANT_ITEMS: Tuple[str, ...] = (
    "Dial Setup",
    "Dial/Wheel Lock",
    "Rear Dial L/R",
)
P371_FUNCTION_RING_MODES: Tuple[str, ...] = ("POWER_FOCUS", "APSC_S35_FF")
P371_FUNCTION_RING_DEFAULT = "POWER_FOCUS"
P371_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    "OFF",
    "MULTI_SELECTOR_ONLY",
    "DIAL_AND_WHEEL",
    "ALL",
)
P371_MY_DIAL_SLOTS: Tuple[int, ...] = (1, 2, 3)
P371_DIFF_SET_EXACT_8_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "ISO",
    "Exposure Comp.",
    "Metering Mode",
    "White Balance",
    "Picture Profile",
    "Focus Mode",
)
P371_FN_MENU_STILL_SLOTS = 12
P371_FN_MENU_MOVIE_SLOTS = 12
P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES: Tuple[str, ...] = (
    "Display All Info.",
    "No Disp. Info.",
    "Histogram",
    "Level",
)
P371_DORMANT_EVF_DISP_ITEMS: Tuple[str, ...] = (
    "Graphic Display",
    "For viewfinder",
    "Monitor Off",
    "Finder/Monitor",
)
P371_SELECT_LUT_PRESETS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
P371_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    "AUTO",
    "SLOG3_TO_709_800",
    "HLG_BT2020",
    "HLG_709",
)

# ---------------------------------------------------------------------------
# Wave 79 Group B Constants: External Output HDMI 4K 10-bit/RAW vs FX6 12G-SDI
# ---------------------------------------------------------------------------

P371_HDMI_RESOLUTIONS_EXACT_4: Tuple[str, ...] = ("AUTO", "2160P", "1080P", "1080I")
P371_HDMI_RESOLUTION_DORMANT: Tuple[str, ...] = ("720P",)
P371_HDMI_4K_OUTPUT_EXACT_6_MODES: Tuple[str, ...] = (
    "59_94P_10BIT_422",
    "50P_10BIT_422",
    "29_97P_10BIT_422",
    "25P_10BIT_422",
    "23_98P_10BIT_422",
    "24_00P_10BIT_422",
)
P371_HDMI_4K_DORMANT_MODES: Tuple[str, ...] = (
    "24_00P_8BIT",
    "24P_60P_OUTPUT",
    "4K_420_8BIT",
)
P371_REBOOT_2400P_EVENT = "MODEL_EVENT_REBOOT_BY_CROSS_2400P"
P371_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF_HDMI_ONLY")
P371_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("AUTO", "2160P", "1080P", "1080I")
P371_RAW_OUTPUT_SETTINGS: Tuple[str, ...] = ("59_94P", "50P", "29_97P", "25P", "23_98P", "24_00P")
P371_RAW_OUTPUT_RES_STR = "4264x2408_16BIT"
P371_4CH_AUDIO_OUTPUT_MODES: Tuple[str, ...] = ("CH1_CH2", "CH3_CH4")
P371_PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P371_SONY_ELF_TYPOS: Tuple[str, ...] = (
    "BKID_APP_setting_ctrl_for_hmdi",
    "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
    "BKID_APP_setting_4ch_output_ch",
)
P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT = 25
P371_FX6_SDI_MODES: Tuple[str, ...] = ("12G_SDI", "6G_SDI", "3G_SDI", "OFF")
P371_FX6_HDMI_RAW_RES_STR = "4240x2392"
P371_FX6_REC_SYNC_MODES: Tuple[str, ...] = ("OFF", "SDI_HDMI_REMOTE_IF", "PARALLEL_REC")

# ---------------------------------------------------------------------------
# Wave 80 Group C Constants: [TC/UB] VMC-BNCM1 TC-IN-Only & [FTP Transfer Func.]
# ---------------------------------------------------------------------------

P371_TCUB_EXACT_7_ITEMS: Tuple[str, ...] = (
    "Time Code Preset",
    "User Bit Preset",
    "Time Code Format",
    "Time Code Run",
    "Time Code Make",
    "User Bit Time Rec",
    "TC/UB Disp. Setting",
)
P371_TC_FORMAT_MODES: Tuple[str, ...] = ("DF", "NDF")
P371_TC_FORMAT_DEFAULT = "DF"
P371_TC_RUN_MODES: Tuple[str, ...] = ("REC_RUN", "FREE_RUN")
P371_TC_MAKE_MODES: Tuple[str, ...] = ("PRESET", "REGENERATE")
P371_TC_MAKE_TYPO_SYMBOL = "VAL_setting_tc_make_TC_MAKE_REGENRATE"
P371_TCUB_DISP_MODES: Tuple[str, ...] = ("COUNTER", "TC", "U_BIT")
P371_NTSC_DF_CAPABLE_FPS: Tuple[float, ...] = (29.97, 59.94, 119.88)
P371_VMC_BNCM1_PART = "VMC-BNCM1"
P371_VMC_PORT_MODES: Tuple[str, ...] = ("DISCONNECTED", "BODY_MULTI_MICRO_USB", "XLR_H1_HANDLE_PORT")
P371_VMC_DIRECTIONS: Tuple[str, ...] = ("NONE", "TC_IN_ONLY", "TC_OUT")
P371_FX6_BNC_TC_SWITCH_MODES: Tuple[str, ...] = ("TC_IN", "TC_OUT")
P371_FX6_TC_MAKE_MODES: Tuple[str, ...] = ("PRESET", "REGENERATE", "CLOCK")

P371_FTP_SERVER_SLOTS_MAX = 9
P371_FTP_PROTOCOLS: Tuple[str, ...] = ("NONE", "FTP", "FTPES_EXPLICIT_AUTH_TLS")
P371_FTP_FORBIDDEN_PROTOCOLS: Tuple[str, ...] = ("SSH_SFTP", "IMPLICIT_FTPS")
P371_FTP_TRANSFER_MODES: Tuple[str, ...] = ("PASSIVE",)
P371_FTP_CACERT_FILENAME = "cacert.pem"
P371_FTP_CACERT_MAX_BYTES = 1024 * 1024
P371_FTPSET_TEMPLATE = "SONY/SETTING/<Model>/FTPSET/FTPSET%02d.DAT"
P371_FTPSET_SLOTS_MAX = 10
P371_FX6_CACERT_FILENAME = "certification.pem"
P371_FX6_CACERT_SLOT = "SLOT_B"

# ---------------------------------------------------------------------------
# Wave 80 Group D Constants: Creators' App 5-GATT BLE, G114 Airplane, Playback Shot Mark
# ---------------------------------------------------------------------------

P371_BLE_EXACT_5_GATT_TABLES: Tuple[str, ...] = (
    "8000CC00",
    "8000DD00",
    "8000EE00",
    "8000FF00",
    "8000BB00",
)
P371_BLE_MAX_PAIRED_DEVICES = 15
P371_BLE_MAX_CONCURRENT_LINKS = 2
P371_BT_STACK_WAKEUP_KEY = "LMP_WAKEUP_CONFIG"
P371_PLAYBACK_WRITE_OPS: Tuple[str, ...] = (
    "NONE",
    "ADD_SHOT_MARK_1",
    "ADD_SHOT_MARK_2",
    "DELETE_SHOT_MARK_1",
    "DELETE_SHOT_MARK_2",
    "RATING",
    "PROTECT",
    "DELETE",
    "COPY",
)
P371_COPY_DIRECTIONS: Tuple[str, ...] = ("NONE", "SLOT_1_TO_SLOT_2", "SLOT_2_TO_SLOT_1")
P371_FX6_CLIP_FLAGS: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP")

# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Paths (Waves 79-80)
# ---------------------------------------------------------------------------

P371_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    (
        "fx3_libinfraftpclient_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFtpClient.so",
    ),
    (
        "fx3_libinfrable_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothLowEnergy.so",
    ),
    (
        "fx3_bt_stack_conf",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/bin/bt_stack.conf",
    ),
    (
        "fx3_libmpr_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
    ),
    (
        "fx3_libinfrafsys_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so",
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
        "fx6_string_english_2_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P371_GA_ERR_MODEL_OR_FW_FLOOR = "P371_GA_ERR_MODEL_OR_FW_FLOOR"
P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED = (
    "P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED"
)
P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD = (
    "P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD"
)
P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK = (
    "P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK"
)
P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT = (
    "P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT"
)

P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT = "P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT"
P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP = (
    "P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP"
)
P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE = "P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE"
P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC = "P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC"

P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE = "P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE"
P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB = "P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB"
P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT = (
    "P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT"
)
P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30 = (
    "P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30"
)

P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET = (
    "P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET"
)
P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION = (
    "P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION"
)
P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30 = (
    "P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30"
)
P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

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


def resolve_phase371_donor_file_or_none(
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


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P371_HEADER_READ_BYTES) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase371DonorInspectionResult:
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


def inspect_phase371_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase371DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase371DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P371_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P371_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE371_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    fx3_override_names = {
        "fx3_appfw_so": "appFw.so",
        "fx3_libinfraftpclient_so": "libInfraFtpClient.so",
        "fx3_libinfrable_so": "libInfraBluetoothLowEnergy.so",
        "fx3_bt_stack_conf": "bt_stack.conf",
        "fx3_libmpr_so": "libmpr.so",
        "fx3_libinfrafsys_so": "libInfraFsys.so",
    }
    for lbl, rel in P371_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            break
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl in fx3_override_names and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / fx3_override_names[lbl]
            if p.exists() and p.is_file():
                candidate = p
        if candidate is None:
            candidate = resolve_phase371_donor_file_or_none(resolved_work_root, rel)

        if candidate is not None:
            hdr = _read_bounded_header_o_rdonly(candidate, P371_HEADER_READ_BYTES)
            present_count += 1
            bytes_read += len(hdr)
            digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]
        else:
            digests[lbl] = hashlib.sha256(f"missing:{lbl}".encode("utf-8")).hexdigest()[:16]

    mode = "LOCAL_DONOR_O_RDONLY" if present_count > 0 else "CLEAN_ROOM_SYNTHETIC"
    return Phase371DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=present_count > 0,
        donors_checked=len(P371_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE371_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Simulated Dual-Media Tier-0 Receipt Helper (Dry-Run Only)
# ---------------------------------------------------------------------------


def build_simulated_phase371_tier0_receipts(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: str = "FX3SIM70200371",
    emmc_cid: str = "11010030303847333000a1b2c3d49371",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE371_TIER0:{hex(body_model_id)}:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE371_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_a_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    receipt_b_bytes = bytes(receipt_a_bytes)
    h0_a = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    h0_b = dict(h0_a)
    h3 = dict(h0_a)
    return {
        "receipt_a_bytes": receipt_a_bytes,
        "receipt_b_bytes": receipt_b_bytes,
        "st_dev_a": 0x1001,
        "st_dev_b": 0x2002,
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "h0_baselines_a": h0_a,
        "h0_baselines_b": h0_b,
        "h3_baselines": h3,
    }


def _extract_tier0_evidence(
    *,
    simulate_bench_dry_run: bool,
    receipt_a_bytes: Optional[bytes],
    receipt_b_bytes: Optional[bytes],
    receipt_a_path: Optional[Path],
    receipt_b_path: Optional[Path],
    st_dev_a_override: Optional[int],
    st_dev_b_override: Optional[int],
    body_serial: Optional[str],
    emmc_cid: Optional[str],
    h0_baselines_a: Optional[Mapping[str, str]],
    h0_baselines_b: Optional[Mapping[str, str]],
    h3_baselines: Optional[Mapping[str, str]],
    simulated_h0_h3_drifted_surfaces: int,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    st_dev_a = st_dev_a_override
    st_dev_b = st_dev_b_override

    if receipt_a_path is not None:
        if not receipt_a_path.exists() or not receipt_a_path.is_file():
            errors.append(
                f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a path missing: {receipt_a_path}"
            )
        else:
            st_dev_a = st_dev_a if st_dev_a is not None else int(os.stat(receipt_a_path).st_dev)
            fd = os.open(str(receipt_a_path), os.O_RDONLY)
            try:
                raw_a = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if receipt_b_path is not None:
        if not receipt_b_path.exists() or not receipt_b_path.is_file():
            errors.append(
                f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b path missing: {receipt_b_path}"
            )
        else:
            st_dev_b = st_dev_b if st_dev_b is not None else int(os.stat(receipt_b_path).st_dev)
            fd = os.open(str(receipt_b_path), os.O_RDONLY)
            try:
                raw_b = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if simulated_h0_h3_drifted_surfaces != 0:
        errors.append(
            f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0 != H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
        )

    if raw_a is None and raw_b is None:
        if simulate_bench_dry_run:
            sim = build_simulated_phase371_tier0_receipts(
                body_serial=body_serial or "FX3SIM70200371",
                emmc_cid=emmc_cid or "11010030303847333000a1b2c3d49371",
            )
            raw_a = sim["receipt_a_bytes"]
            raw_b = sim["receipt_b_bytes"]
            st_dev_a = st_dev_a if st_dev_a is not None else sim["st_dev_a"]
            st_dev_b = st_dev_b if st_dev_b is not None else sim["st_dev_b"]
            h0_baselines_a = h0_baselines_a or sim["h0_baselines_a"]
            h0_baselines_b = h0_baselines_b or sim["h0_baselines_b"]
            h3_baselines = h3_baselines or sim["h3_baselines"]
            body_serial = body_serial or sim["body_serial"]
            emmc_cid = emmc_cid or sim["emmc_cid"]
            receipt_mode = "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH"
        else:
            warnings.append(
                "Offline preflight mode: dual-media 528 B FX3RCPT1 receipts not supplied; "
                "physical hardware attachment remains BLOCKED (`rc=2`)."
            )
            return {
                "tier0_receipt_verified": False,
                "receipt_mode": "AWAITING_PHYSICAL_RECEIPTS",
                "h0_equals_h3_count": 0,
                "st_dev_a": st_dev_a,
                "st_dev_b": st_dev_b,
                "body_serial": body_serial or "",
                "emmc_cid": emmc_cid or "",
                "errors": errors,
                "warnings": warnings,
            }
    else:
        receipt_mode = (
            "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH"
            if simulate_bench_dry_run
            else "PHYSICAL_TIER0_DUAL_MEDIA_VERIFIED"
        )

    if raw_a is None or raw_b is None:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528-byte FX3RCPT1 receipts are required"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "INVALID_OR_SINGLE_COPY",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt size must be {SD_RECEIPT_BYTES} B (got A={len(raw_a)}, B={len(raw_b)})"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "INVALID_SIZE",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if raw_a != raw_b:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B FX3RCPT1 payloads differ"
        )

    if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B must reside on distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
        )

    try:
        parsed_a = parse_sd_backup_receipt_bytes(raw_a)
        parsed_b = parse_sd_backup_receipt_bytes(raw_b)
    except Exception as exc:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
        )
        return {
            "tier0_receipt_verified": False,
            "receipt_mode": "CORRUPT_FX3RCPT1",
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": body_serial or "",
            "emmc_cid": emmc_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if not getattr(parsed_a, "valid", False) or not getattr(parsed_b, "valid", False):
        errs_ab = list(getattr(parsed_a, "errors", ())) + list(getattr(parsed_b, "errors", ()))
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 integrity failure ({'; '.join(errs_ab)})"
        )
    if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))) or _is_trivial_hex64(
        str(getattr(parsed_b, "manifest_sha256", ""))
    ):
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: trivial manifest_sha256 in FX3RCPT1"
        )
    if getattr(parsed_a, "entry_count", 0) != len(COLD_BACKUP_ITEMS) or getattr(
        parsed_b, "entry_count", 0
    ) != len(COLD_BACKUP_ITEMS):
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: cold backup item count mismatch ({getattr(parsed_a, 'entry_count', 0)} != {len(COLD_BACKUP_ITEMS)})"
        )

    eff_serial = body_serial if body_serial is not None else ""
    eff_cid = emmc_cid if emmc_cid is not None else ""
    if eff_serial:
        if eff_serial.upper() in FORBIDDEN_TRIVIAL_SERIALS or not BODY_SERIAL_RE.match(eff_serial):
            errors.append(
                f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial body_serial {eff_serial!r}"
            )
    else:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial body_serial required for receipt binding"
        )

    if eff_cid:
        if eff_cid.lower() in FORBIDDEN_TRIVIAL_CIDS or not HEX32_CID_RE.match(eff_cid):
            errors.append(
                f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial emmc_cid {eff_cid!r}"
            )
    else:
        errors.append(
            f"{P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial 32-hex emmc_cid required for receipt binding"
        )

    h0_match = 0
    if not errors and eff_serial and eff_cid:
        h0_a_map = (
            dict(h0_baselines_a)
            if h0_baselines_a is not None
            else build_default_h0_baselines(body_serial=eff_serial, emmc_cid=eff_cid)
        )
        h0_b_map = dict(h0_baselines_b) if h0_baselines_b is not None else dict(h0_a_map)
        h3_map = dict(h3_baselines) if h3_baselines is not None else dict(h0_a_map)
        if set(h0_a_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_a keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h0_b_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_b keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h3_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h3_baselines keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif len(SIXTEEN_STORAGE_SURFACES) != P371_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: expected 16 storage surfaces, got {len(SIXTEEN_STORAGE_SURFACES)}"
            )
        else:
            key_mismatches = sum(
                1
                for key in REQUIRED_H0_BASELINE_KEYS
                if _is_trivial_hex64(str(h0_a_map.get(key, "")))
                or _is_trivial_hex64(str(h3_map.get(key, "")))
                or str(h0_a_map.get(key, "")).lower() != str(h0_b_map.get(key, "")).lower()
                or str(h0_a_map.get(key, "")).lower() != str(h3_map.get(key, "")).lower()
            )
            surface_mismatches = sum(
                1
                for surf in SIXTEEN_STORAGE_SURFACES
                if h0_a_map.get(surf) != h0_b_map.get(surf) or h0_a_map.get(surf) != h3_map.get(surf)
            )
            drifted = max(0, int(simulated_h0_h3_drifted_surfaces), key_mismatches, surface_mismatches)
            if drifted > 0:
                errors.append(
                    f"{P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 != H3 or trivial digest detected ({drifted} drifted)"
                )
            h0_match = max(0, P371_STORAGE_SURFACE_COUNT - drifted)

    verified = (
        len(errors) == 0
        and h0_match == P371_STORAGE_SURFACE_COUNT
        and simulated_h0_h3_drifted_surfaces == 0
    )
    return {
        "tier0_receipt_verified": verified,
        "receipt_mode": receipt_mode if verified else "BLOCKED_INVALID_RECEIPT",
        "h0_equals_h3_count": h0_match if verified else 0,
        "st_dev_a": st_dev_a,
        "st_dev_b": st_dev_b,
        "body_serial": eff_serial,
        "emmc_cid": eff_cid,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Result Dataclasses (Check Groups A-D & Top-Level Report)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class P371CheckGroupAZoomSpeedDialCustomizeAndZeroEvfResult:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    zoom_range: str
    effective_zoom_range_after_reset: str
    zoom_ring_rotate: str
    effective_zoom_ring_rotate_after_reset: str
    zoom_lever_stby_1st: int
    zoom_lever_stby_2nd: int
    zoom_lever_rec_1st: int
    zoom_lever_rec_2nd: int
    effective_zoom_lever_stby_1st_after_reset: int
    custom_key_zoom_mode: str
    custom_key_zoom_stby_speed: int
    custom_key_zoom_rec_speed: int
    effective_custom_key_zoom_stby_after_reset: int
    remote_zoom_speed_type: str
    remote_zoom_fixed_stby_speed: int
    remote_zoom_fixed_rec_speed: int
    effective_remote_zoom_type_after_reset: str
    ciz_digital_locked_out: bool
    ciz_digital_af_metering_locked: bool
    fx6_zoom_type: str
    fx6_handle_zoom_mode: str
    fx6_handle_zoom_hud_position: int
    dial_customize_items: Tuple[str, ...]
    my_dial_slot: int
    my_dial_temporarily_unlocks_lock_op: bool
    av_tv_rotate: str
    function_ring_lens: str
    lock_operation_parts: str
    diff_set_items: Tuple[str, ...]
    diff_set_pp_checked: bool
    effective_diff_set_pp_after_reset: bool
    fn_menu_still_slots: int
    fn_menu_movie_slots: int
    monitor_disp_pages: Tuple[str, ...]
    fx3_builtin_evf_present: bool
    select_lut: str
    display_lut: str
    gamma_display_assist: str
    gamma_display_assist_active_in_movie: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P371CheckGroupBHdmi4k10BitRawAndFx6Sdi12gResult:
    group_id: str
    passed: bool
    reset_action: str
    hdmi_resolution: str
    hdmi_resolution_options_exposed: Tuple[str, ...]
    hdmi_4k_output_set: str
    hdmi_4k_output_options_exposed: Tuple[str, ...]
    rec_media_dur_hdmi_output: str
    output_resolution: str
    effective_output_resolution: str
    hdmi_raw_output: bool
    raw_output_setting: str
    hdmi_time_code_output: str
    hdmi_rec_control: str
    hdmi_4ch_audio_output: str
    hdmi_info_display: str
    effective_hdmi_info_display: str
    fx3_lcd_blanked_for_hdmi_info: bool
    reboot_2400p_gate_triggered: bool
    sony_elf_typos_verified: Tuple[str, ...]
    fx6_sdi_mode: str
    fx6_hdmi_mode: str
    fx6_sdi_hdmi_combo_count: int
    fx6_rec_sync_mode: str
    fx6_raw_pipeline: str
    fx6_builtin_vf_active: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P371CheckGroupCTcUbVmcBncm1AndFtpesSlot1Result:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    tcub_items_exposed: Tuple[str, ...]
    video_system: str
    rec_fps: float
    tc_format: str
    tc_run: str
    tc_make: str
    tcub_disp_setting: str
    effective_tc_make_after_reset: str
    tc_preset_cleared_on_reset: bool
    vmc_bncm1_port: str
    vmc_bncm1_direction: str
    ext_lk_status: str
    fx6_bnc_tc_switch: str
    fx6_tc_make: str
    fx6_users_bit_hex: str
    ftp_transfer_func: str
    ftp_server_slot: int
    ftp_protocol: str
    ftp_transfer_mode: str
    ftp_cacert_slot: int
    ftp_cacert_size_bytes: int
    ftpset_slot: int
    ftpset_action: str
    ftpset_target_slot: int
    ftpset_encrypted_with_password: bool
    ftpset_load_reboot_acknowledged: bool
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_sector_writes: int
    fx6_file_transfer_cacert: str
    fx6_chunk_proxy_upload_enabled: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P371CheckGroupDCreatorsAppBleG114AirplaneAndShotMarkTier0Result:
    group_id: str
    passed: bool
    reset_action: str
    ble_gatt_tables_exposed: Tuple[str, ...]
    creators_app_paired_count: int
    location_info_migrated_to_app_ver3: bool
    cnct_while_power_off: str
    effective_ble_paired_after_reset: int
    airplane_mode: str
    effective_airplane_mode_after_reset: str
    usb_lan_electrically_isolated: bool
    rf_tx_packets: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    playback_write_op: str
    playback_target_slot: int
    playback_copy_direction: str
    rating_stars: int
    shot_mark_slot1_blocked_erofs30: bool
    copy_slot1_to_slot2_readonly_safe: bool
    copy_slot2_to_slot1_blocked_erofs30: bool
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_sector_writes: int
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
    fx6_clip_flag: str
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
class Phase371ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P371CheckGroupAZoomSpeedDialCustomizeAndZeroEvfResult
    check_group_b: P371CheckGroupBHdmi4k10BitRawAndFx6Sdi12gResult
    check_group_c: P371CheckGroupCTcUbVmcBncm1AndFtpesSlot1Result
    check_group_d: P371CheckGroupDCreatorsAppBleG114AirplaneAndShotMarkTier0Result
    donor_inspection: Phase371DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    slot1_tier0_vault_mutated: bool
    ready_for_live_camera_attach: bool
    overall_ready_for_hardware_attach: bool
    live_attach_authorized: bool
    hardware_live_attachment_authorized: bool
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_builtin_evf_present: bool
    fx3_custom_key_zoom_variable_supported: bool
    fx3_hdmi_720p_supported: bool
    fx3_sftp_supported: bool
    fx3_implicit_ftps_supported: bool
    emmc_write_count: int
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_tx_packets: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    rf_nvs_mutation_bytes: int
    slot1_sector_writes: int
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
            "ready_for_live_camera_attach": self.ready_for_live_camera_attach,
            "overall_ready_for_hardware_attach": self.overall_ready_for_hardware_attach,
            "live_attach_authorized": self.live_attach_authorized,
            "hardware_live_attachment_authorized": self.hardware_live_attachment_authorized,
            "emmc_writes_authorized": self.emmc_writes_authorized,
            "persistent_emmc_writes_authorized": self.persistent_emmc_writes_authorized,
            "persistent_write_release": self.persistent_write_release,
            "spi_nor_write_authorized": self.spi_nor_write_authorized,
            "el3_payload_transmit_authorized": self.el3_payload_transmit_authorized,
            "sd_physical_media_written": self.sd_physical_media_written,
            "cross_model_flash_authorized": self.cross_model_flash_authorized,
            "rf_nvs_p12_p13_writes_authorized": self.rf_nvs_p12_p13_writes_authorized,
            "fx3_builtin_evf_present": self.fx3_builtin_evf_present,
            "fx3_custom_key_zoom_variable_supported": self.fx3_custom_key_zoom_variable_supported,
            "fx3_hdmi_720p_supported": self.fx3_hdmi_720p_supported,
            "fx3_sftp_supported": self.fx3_sftp_supported,
            "fx3_implicit_ftps_supported": self.fx3_implicit_ftps_supported,
            "emmc_write_count": self.emmc_write_count,
            "e_nd_actuator_tx_count": self.e_nd_actuator_tx_count,
            "e_nd_i2c_tx_bytes": self.e_nd_i2c_tx_bytes,
            "rf_tx_packets": self.rf_tx_packets,
            "rf_packets_transmitted": self.rf_packets_transmitted,
            "wireless_rf_packets_emitted": self.wireless_rf_packets_emitted,
            "rf_nvs_mutation_bytes": self.rf_nvs_mutation_bytes,
            "slot1_sector_writes": self.slot1_sector_writes,
            "slot1_data_sector_writes": self.slot1_data_sector_writes,
            "usb_packets_transmitted": self.usb_packets_transmitted,
            "passive_tx_bytes_emitted": self.passive_tx_bytes_emitted,
            "raw_firmware_bytes_leaked": self.raw_firmware_bytes_leaked,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "report_sha256": self.report_sha256,
        }

    def to_deterministic_json(self, indent: int = 2) -> str:
        payload = _strip_timing_fields(self.to_dict())
        return json.dumps(payload, indent=indent, sort_keys=True, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 79 Zoom Speed Split & Dial Customize 5-Item / Zero-EVF)
# ---------------------------------------------------------------------------


def _parse_fw_tuple(fw: str) -> Optional[Tuple[int, int]]:
    parts = fw.strip().split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


def evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P371_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    # Zoom Range & Ring Rotate (Initialize-only) vs Speed Trio (Resettable)
    zoom_range: str = P371_ZOOM_RANGE_DEFAULT,
    zoom_ring_rotate: str = P371_ZOOM_RING_ROTATE_DEFAULT,
    zoom_lever_stby_1st: int = P371_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_stby_2nd: int = P371_ZOOM_LEVER_2ND_DEFAULT,
    zoom_lever_rec_1st: int = P371_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_rec_2nd: int = P371_ZOOM_LEVER_2ND_DEFAULT,
    custom_key_zoom_mode: str = "FIXED",
    custom_key_zoom_stby_speed: int = P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_zoom_rec_speed: int = P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = 3,
    remote_zoom_fixed_rec_speed: int = 3,
    smart_zoom_requested: bool = False,
    still_file_format: str = "JPEG",
    still_image_size: str = "M",
    rec_frame_rate_fps: float = 59.94,
    sq_frame_rate_fps: int = 24,
    hdmi_raw_output: bool = False,
    focus_area: str = "WIDE",
    metering_mode: str = "MULTI",
    face_eye_prior_in_af: str = "ON",
    face_priority_in_multi_metering: str = "ON",
    tracking_af_active: bool = False,
    claimed_zoom_range_wiped_by_camera_reset: bool = False,
    claimed_zoom_ring_rotate_wiped_by_camera_reset: bool = False,
    claimed_zoom_speeds_resist_camera_reset: bool = False,
    claimed_custom_key_zoom_has_variable_mode: bool = False,
    expect_ciz_active_under_lockout: bool = False,
    expect_focus_area_or_tracking_under_ciz: bool = False,
    # FX6 zoom & handle zoom contrast
    fx6_zoom_type: str = "CLEAR_IMAGE_ZOOM",
    fx6_handle_zoom_mode: str = "VARIABLE",
    fx6_handle_zoom_hud_position: int = 50,
    claimed_fx6_has_digital_zoom: bool = False,
    claimed_fx6_0_99_is_speed_scale: bool = False,
    # Dial Customize 5-Item + DiffSet 8 + Fn 12+12 + Zero-EVF + LUT vs Gamma Assist
    dial_customize_items: Tuple[str, ...] = P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS,
    dormant_dial_customize_item_requested: Optional[str] = None,
    my_dial_slot: int = 1,
    my_dial_active: bool = False,
    av_tv_rotate: str = "NORMAL",
    function_ring_lens: str = P371_FUNCTION_RING_DEFAULT,
    lock_operation_parts: str = "OFF",
    claimed_dial_customize_wiped_by_camera_reset: bool = False,
    expect_lock_op_blocks_my_dial: bool = False,
    diff_set_items: Tuple[str, ...] = P371_DIFF_SET_EXACT_8_ITEMS,
    diff_set_pp_checked: bool = True,
    claimed_pp_diffset_wiped_by_reset_or_init: bool = False,
    shutter_mode: str = "SPEED",
    expect_shutter_angle_shares_still_movie: bool = False,
    fn_menu_still_slots: int = P371_FN_MENU_STILL_SLOTS,
    fn_menu_movie_slots: int = P371_FN_MENU_MOVIE_SLOTS,
    fn_menu_all_not_set_requested: bool = False,
    monitor_disp_pages: Tuple[str, ...] = P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES,
    dormant_evf_disp_requested: Optional[str] = None,
    claimed_fx3_has_builtin_evf: bool = False,
    select_lut: str = "s709",
    display_lut: str = "OFF",
    gamma_display_assist: str = "OFF",
    expect_gamma_assist_active_in_log_movie: bool = False,
) -> P371CheckGroupAZoomSpeedDialCustomizeAndZeroEvfResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX}, got 0x{body_model_id:08x}"
        )
    fw_t = _parse_fw_tuple(body_fw)
    if fw_t is None or fw_t < (7, 2):
        errors.append(
            f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: body_fw must be >= {TARGET_BODY_FW}, got {body_fw!r}"
        )
    if sony_help_guide_id != P371_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P371_SONY_HELP_GUIDE_ID}, got {sony_help_guide_id!r}"
        )
    if shoot_mode not in P371_VALID_SHOOT_MODES:
        errors.append(f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode {shoot_mode!r}")
    if log_shooting_mode not in P371_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if reset_action not in P371_VALID_RESET_ACTIONS:
        errors.append(f"{P371_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action {reset_action!r}")

    # Zoom Range, Ring Rotate, and Resettable 3-Trio Speeds
    if zoom_range not in P371_ZOOM_RANGE_MODES:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: invalid zoom_range {zoom_range!r}"
        )
    if zoom_ring_rotate not in P371_ZOOM_RING_ROTATE_MODES:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: invalid zoom_ring_rotate {zoom_ring_rotate!r}"
        )
    for name, val in (
        ("zoom_lever_stby_1st", zoom_lever_stby_1st),
        ("zoom_lever_stby_2nd", zoom_lever_stby_2nd),
        ("zoom_lever_rec_1st", zoom_lever_rec_1st),
        ("zoom_lever_rec_2nd", zoom_lever_rec_2nd),
        ("custom_key_zoom_stby_speed", custom_key_zoom_stby_speed),
        ("custom_key_zoom_rec_speed", custom_key_zoom_rec_speed),
        ("remote_zoom_fixed_stby_speed", remote_zoom_fixed_stby_speed),
        ("remote_zoom_fixed_rec_speed", remote_zoom_fixed_rec_speed),
    ):
        if not (P371_ZOOM_SPEED_MIN <= val <= P371_ZOOM_SPEED_MAX):
            errors.append(
                f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: {name}={val} must be in 1..8"
            )
    if custom_key_zoom_mode != "FIXED" or claimed_custom_key_zoom_has_variable_mode:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: [Custom Key Z. Speed] supports Fixed 1..8 ONLY (zero Variable mode)"
        )
    if remote_zoom_speed_type not in P371_REMOTE_ZOOM_SPEED_TYPES:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: invalid remote_zoom_speed_type {remote_zoom_speed_type!r} ({P371_REMOTE_ZOOM_SPEED_TYPE_BKID})"
        )
    if claimed_zoom_range_wiped_by_camera_reset:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: [Zoom Range] resists [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_zoom_ring_rotate_wiped_by_camera_reset:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: [Zoom Ring Rotate] resists [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_zoom_speeds_resist_camera_reset:
        errors.append(
            f"{P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED}: all 3 zoom speed items ([Zoom Lever Speed], [Custom Key Z. Speed], [Remote Zoom Speed]) are Resettable"
        )

    # Smart Zoom & CIZ/Digital Lockouts
    if smart_zoom_requested and (
        shoot_mode != "PHOTO"
        or still_file_format in P371_RAW_STILL_FORMATS
        or still_image_size not in ("M", "S")
    ):
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: Smart Zoom is strictly Still non-RAW size M (1.5x) / S (2.0x) only"
        )

    ciz_lockout = (
        (shoot_mode == "PHOTO" and still_file_format in P371_RAW_STILL_FORMATS)
        or (shoot_mode == "MOVIE" and rec_frame_rate_fps >= 100.0)
        or (shoot_mode == "S_AND_Q" and sq_frame_rate_fps >= 100)
        or hdmi_raw_output
    )
    if expect_ciz_active_under_lockout and ciz_lockout:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: Clear Image Zoom / Digital Zoom locked out under RAW / 100-120p / S&Q>=100fps / HDMI RAW"
        )
    if zoom_range in ("CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM") and ciz_lockout:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: zoom_range={zoom_range} cannot run under active lockout condition"
        )
    ciz_af_metering_locked = zoom_range in ("CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM")
    if expect_focus_area_or_tracking_under_ciz and ciz_af_metering_locked:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: CIZ/Digital Zoom locks Metering=Multi and disables Focus Area, Tracking, Face/Eye Prior. in AF, and Face Priority in Multi Metering"
        )
    if ciz_af_metering_locked and (
        metering_mode != "MULTI"
        or face_eye_prior_in_af != "OFF"
        or face_priority_in_multi_metering != "OFF"
        or tracking_af_active
        or focus_area not in ("CENTER_FIX", "CENTER_PRIORITY_AF", "WIDE")
    ):
        # Under CIZ/Digital Zoom, Multi Metering + disabled face/tracking must hold if claimed active
        if metering_mode != "MULTI" or tracking_af_active or face_eye_prior_in_af == "ON":
            errors.append(
                f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: CIZ/Digital Zoom requires Metering=MULTI, Tracking=False, Face/Eye AF=OFF"
            )

    # FX6 Zoom Type & Handle Zoom 0..99 HUD
    if fx6_zoom_type not in P371_FX6_ZOOM_TYPES or claimed_fx6_has_digital_zoom:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: FX6 Zoom Type supports Optical / Clear Image Zoom only (zero Digital Zoom)"
        )
    if fx6_handle_zoom_mode not in P371_FX6_HANDLE_ZOOM_MODES:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: invalid fx6_handle_zoom_mode {fx6_handle_zoom_mode!r}"
        )
    if not (0 <= fx6_handle_zoom_hud_position <= 99) or claimed_fx6_0_99_is_speed_scale:
        errors.append(
            f"{P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD}: FX6 0..99 is Zoom Position Display HUD readout only (NOT a speed scale)"
        )

    # Dial Customize 5-Item Initialize-Only & My Dial 1..3 Unlock
    if tuple(dial_customize_items) != P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: [Dial Customize] must expose exact 5 items {P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS}"
        )
    if dormant_dial_customize_item_requested is not None:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: dormant [Dial Customize] item {dormant_dial_customize_item_requested!r} rejected (EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP})"
        )
    if my_dial_slot not in P371_MY_DIAL_SLOTS:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: my_dial_slot must be 1..3, got {my_dial_slot}"
        )
    if av_tv_rotate not in ("NORMAL", "REVERSE"):
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: invalid av_tv_rotate {av_tv_rotate!r}"
        )
    if function_ring_lens not in P371_FUNCTION_RING_MODES:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: invalid function_ring_lens {function_ring_lens!r}"
        )
    if lock_operation_parts not in P371_LOCK_OPERATION_PARTS_MODES:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: invalid lock_operation_parts {lock_operation_parts!r}"
        )
    if claimed_dial_customize_wiped_by_camera_reset:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: all 5 [Dial Customize] items resist [Camera Settings Reset] (Initialize-only)"
        )
    if expect_lock_op_blocks_my_dial:
        errors.append(
            f"{P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK}: active My Dial 1..3 temporarily unlocks [Lock Operation Parts]"
        )

    # Different Set for Still/Mv 8-bit Mask, Fn 12+12, Zero-EVF 4 DISP Pages, Select LUT vs Gamma Assist
    if tuple(diff_set_items) != P371_DIFF_SET_EXACT_8_ITEMS:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: [Different Set for Still/Mv] must expose exact 8 items"
        )
    if claimed_pp_diffset_wiped_by_reset_or_init:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: Picture Profile checkmark in [Different Set for Still/Mv] resists BOTH [Camera Settings Reset] and [Initialize]"
        )
    if expect_shutter_angle_shares_still_movie and shutter_mode == "ANGLE":
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: [Shutter Mode]=Angle forces Still/Movie shutter separation"
        )
    if fn_menu_still_slots != P371_FN_MENU_STILL_SLOTS or fn_menu_movie_slots != P371_FN_MENU_MOVIE_SLOTS or fn_menu_all_not_set_requested:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: Fn Menu requires 12 Still + 12 Movie slots and forbids all-Not-set"
        )
    if tuple(monitor_disp_pages) != P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: FX3 Monitor [DISP] exposes exact 4 shooting pages"
        )
    if dormant_evf_disp_requested is not None or claimed_fx3_has_builtin_evf:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: FX3 is EVF-less; dormant EVF/Finder/Graphic Display rejected (EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP})"
        )
    valid_user_luts = tuple(f"User{i}" for i in range(1, 17))
    if select_lut not in (P371_SELECT_LUT_PRESETS + valid_user_luts):
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: invalid select_lut {select_lut!r}"
        )
    if display_lut not in P371_VALID_ON_OFF or gamma_display_assist not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: display_lut and gamma_display_assist must be ON/OFF"
        )
    gamma_assist_active_in_movie = (
        shoot_mode in ("MOVIE", "S_AND_Q")
        and log_shooting_mode == "OFF"
        and gamma_display_assist == "ON"
    )
    if expect_gamma_assist_active_in_log_movie and log_shooting_mode != "OFF":
        errors.append(
            f"{P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT}: [Gamma Display Assist] is inactive in Movie when [Log Shooting] != Off (use [Select LUT]/[Display LUT])"
        )

    eff_zoom_range = P371_ZOOM_RANGE_DEFAULT if reset_action == "INITIALIZE" else zoom_range
    eff_ring_rotate = (
        P371_ZOOM_RING_ROTATE_DEFAULT if reset_action == "INITIALIZE" else zoom_ring_rotate
    )
    eff_lever_stby_1st = (
        P371_ZOOM_LEVER_1ST_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else zoom_lever_stby_1st
    )
    eff_custom_key_stby = (
        P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else custom_key_zoom_stby_speed
    )
    eff_remote_type = (
        "VARIABLE"
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else remote_zoom_speed_type
    )
    # Picture Profile diffset resists BOTH Camera Settings Reset and Initialize
    eff_diff_set_pp = diff_set_pp_checked

    return P371CheckGroupAZoomSpeedDialCustomizeAndZeroEvfResult(
        group_id=P371_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        zoom_range=zoom_range,
        effective_zoom_range_after_reset=eff_zoom_range,
        zoom_ring_rotate=zoom_ring_rotate,
        effective_zoom_ring_rotate_after_reset=eff_ring_rotate,
        zoom_lever_stby_1st=zoom_lever_stby_1st,
        zoom_lever_stby_2nd=zoom_lever_stby_2nd,
        zoom_lever_rec_1st=zoom_lever_rec_1st,
        zoom_lever_rec_2nd=zoom_lever_rec_2nd,
        effective_zoom_lever_stby_1st_after_reset=eff_lever_stby_1st,
        custom_key_zoom_mode=custom_key_zoom_mode,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        effective_custom_key_zoom_stby_after_reset=eff_custom_key_stby,
        remote_zoom_speed_type=remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        effective_remote_zoom_type_after_reset=eff_remote_type,
        ciz_digital_locked_out=ciz_lockout,
        ciz_digital_af_metering_locked=ciz_af_metering_locked,
        fx6_zoom_type=fx6_zoom_type,
        fx6_handle_zoom_mode=fx6_handle_zoom_mode,
        fx6_handle_zoom_hud_position=fx6_handle_zoom_hud_position,
        dial_customize_items=tuple(dial_customize_items),
        my_dial_slot=my_dial_slot,
        my_dial_temporarily_unlocks_lock_op=True,
        av_tv_rotate=av_tv_rotate,
        function_ring_lens=function_ring_lens,
        lock_operation_parts=lock_operation_parts,
        diff_set_items=tuple(diff_set_items),
        diff_set_pp_checked=diff_set_pp_checked,
        effective_diff_set_pp_after_reset=eff_diff_set_pp,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        monitor_disp_pages=tuple(monitor_disp_pages),
        fx3_builtin_evf_present=False,
        select_lut=select_lut,
        display_lut=display_lut,
        gamma_display_assist=gamma_display_assist,
        gamma_display_assist_active_in_movie=gamma_assist_active_in_movie,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 79 External Output HDMI 4K 10-bit/RAW vs FX6 12G-SDI)
# ---------------------------------------------------------------------------


def evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
    *,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "PP11",
    apsc_s35_shooting: str = "OFF",
    reset_action: str = "NONE",
    hdmi_resolution: str = "AUTO",
    hdmi_resolution_options_exposed: Tuple[str, ...] = P371_HDMI_RESOLUTIONS_EXACT_4,
    hdmi_4k_output_set: str = "23_98P_10BIT_422",
    prev_hdmi_4k_output_set: str = "23_98P_10BIT_422",
    hdmi_4k_output_options_exposed: Tuple[str, ...] = P371_HDMI_4K_OUTPUT_EXACT_6_MODES,
    dormant_hdmi_4k_mode_requested: Optional[str] = None,
    reboot_2400p_acknowledged: bool = True,
    rec_media_dur_hdmi_output: str = "ON",
    output_resolution: str = "AUTO",
    hdmi_raw_output: bool = False,
    raw_output_setting: str = "23_98P",
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "OFF",
    sony_elf_typos_verified: Tuple[str, ...] = P371_SONY_ELF_TYPOS,
    claimed_external_output_wiped_by_camera_reset: bool = False,
    claimed_hdmi_has_720p_or_420: bool = False,
    claimed_color_gamut_for_raw_output_present: bool = False,
    expect_fx3_lcd_active_when_rec_on_info_on_raw_off: bool = False,
    expect_4k_internal_hdmi_when_log_or_pplut: bool = False,
    expect_rec_ctrl_without_tc_output_or_in_sq: bool = False,
    # FX6 12G/6G/3G-SDI + HDMI Dual-Pipeline
    fx6_sdi_mode: str = "12G_SDI",
    fx6_hdmi_mode: str = "3840x2160_59_94P",
    fx6_sdi_hdmi_combo_count: int = P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT,
    fx6_rec_sync_mode: str = "SDI_HDMI_REMOTE_IF",
    fx6_raw_pipeline: str = "NONE",
    fx6_sq_fps: int = 24,
    claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi: bool = False,
    claimed_fx6_builtin_vf_blanks_like_fx3_lcd: bool = False,
    claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on: bool = False,
) -> P371CheckGroupBHdmi4k10BitRawAndFx6Sdi12gResult:
    errors: List[str] = []
    warnings: List[str] = []

    if tuple(hdmi_resolution_options_exposed) != P371_HDMI_RESOLUTIONS_EXACT_4 or claimed_hdmi_has_720p_or_420:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: [HDMI Resolution] exposes strictly 4 options (Auto/2160p/1080p/1080i; zero 720p)"
        )
    if hdmi_resolution not in P371_HDMI_RESOLUTIONS_EXACT_4:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: invalid hdmi_resolution {hdmi_resolution!r}"
        )
    if tuple(hdmi_4k_output_options_exposed) != P371_HDMI_4K_OUTPUT_EXACT_6_MODES:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: [4K Output Set.(HDMI Only)] must expose strictly 6 10bit 4:2:2 modes"
        )
    if hdmi_4k_output_set not in P371_HDMI_4K_OUTPUT_EXACT_6_MODES:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: invalid hdmi_4k_output_set {hdmi_4k_output_set!r}"
        )
    if dormant_hdmi_4k_mode_requested is not None:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: dormant HDMI 4K mode {dormant_hdmi_4k_mode_requested!r} rejected (EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP})"
        )
    if claimed_external_output_wiped_by_camera_reset:
        errors.append(
            f"{P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT}: all [External Output] settings resist [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_color_gamut_for_raw_output_present:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: [Color Gamut for RAW Output] was removed in Ver. 2.00+"
        )

    # 24.00p reboot gate & APS-C restriction
    crossing_2400p = (hdmi_4k_output_set == "24_00P_10BIT_422") != (
        prev_hdmi_4k_output_set == "24_00P_10BIT_422"
    )
    if crossing_2400p and not reboot_2400p_acknowledged:
        errors.append(
            f"{P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE}: crossing 24.00p triggers {P371_REBOOT_2400P_EVENT} reboot gate"
        )
    if hdmi_4k_output_set == "24_00P_10BIT_422" and apsc_s35_shooting == "ON":
        errors.append(
            f"{P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE}: 4K 24.00p HDMI Only output blocked when [APS-C S35 Shooting] = ON ({P371_SONY_ELF_TYPOS[1]})"
        )

    if rec_media_dur_hdmi_output not in P371_REC_MEDIA_DUR_HDMI_MODES:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: invalid rec_media_dur_hdmi_output {rec_media_dur_hdmi_output!r}"
        )
    if shoot_mode == "S_AND_Q" and rec_media_dur_hdmi_output != "ON":
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: S&Q mode locks [Rec. Media dur HDMI Output] = ON"
        )
    if output_resolution not in P371_OUTPUT_RESOLUTIONS:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: invalid output_resolution {output_resolution!r}"
        )

    is_1080_clamped = (
        rec_media_dur_hdmi_output == "ON"
        and not hdmi_raw_output
        and (log_shooting_mode != "OFF" or picture_profile in P371_PPLUT_PROFILES)
    )
    eff_output_res = "1080P" if is_1080_clamped else output_resolution
    if expect_4k_internal_hdmi_when_log_or_pplut and is_1080_clamped:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: internal Log / PPLUT1..4 with Rec. Media = ON clamps HDMI output to 1080p"
        )

    if hdmi_raw_output:
        if raw_output_setting not in P371_RAW_OUTPUT_SETTINGS:
            errors.append(
                f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: invalid raw_output_setting {raw_output_setting!r}"
            )
        if shoot_mode == "PHOTO" or log_shooting_mode == "OFF":
            errors.append(
                f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: 16-bit 4264x2408 [RAW Output]=ON requires Movie/S&Q with Log Shooting != OFF"
            )

    if hdmi_time_code_output not in P371_VALID_ON_OFF or hdmi_rec_control not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: hdmi_time_code_output and hdmi_rec_control must be ON/OFF"
        )
    if expect_rec_ctrl_without_tc_output_or_in_sq:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: [REC Control] requires [Time Code Output]=ON and is disabled in S&Q"
        )
    if hdmi_rec_control == "ON" and (hdmi_time_code_output != "ON" or shoot_mode == "S_AND_Q"):
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: [REC Control]=ON requires Time Code Output=ON and non-S&Q mode"
        )
    if hdmi_4ch_audio_output not in P371_4CH_AUDIO_OUTPUT_MODES:
        errors.append(
            f"{P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE}: invalid hdmi_4ch_audio_output {hdmi_4ch_audio_output!r}"
        )

    # HDMI Info. Display LCD Blanking vs Auto Clean HDMI
    if hdmi_info_display not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: hdmi_info_display must be ON/OFF"
        )
    auto_clean_hdmi = (rec_media_dur_hdmi_output == "OFF_HDMI_ONLY") or hdmi_raw_output
    eff_hdmi_info = "OFF" if auto_clean_hdmi else hdmi_info_display
    lcd_blanked = (rec_media_dur_hdmi_output == "ON") and (not hdmi_raw_output) and (eff_hdmi_info == "ON")
    if expect_fx3_lcd_active_when_rec_on_info_on_raw_off and lcd_blanked:
        errors.append(
            f"{P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP}: [HDMI Info. Display]=ON blanks built-in FX3 LCD when Rec. Media=ON and RAW=OFF"
        )

    if tuple(sony_elf_typos_verified) != P371_SONY_ELF_TYPOS:
        errors.append(
            f"{P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE}: expected exact Sony ELF typos {P371_SONY_ELF_TYPOS}"
        )

    # FX6 12G-SDI + HDMI Dual-Pipeline Matrix
    if fx6_sdi_hdmi_combo_count != P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT:
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: FX6 VAL_setting_output_format_sdi_hdmi_* matrix has 25 combos"
        )
    if fx6_sdi_mode not in P371_FX6_SDI_MODES:
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: invalid fx6_sdi_mode {fx6_sdi_mode!r}"
        )
    if fx6_rec_sync_mode not in P371_FX6_REC_SYNC_MODES:
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: invalid fx6_rec_sync_mode {fx6_rec_sync_mode!r}"
        )
    if claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi:
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: FX6 RAW(HDMI) 4240x2392 has NO 24.00Hz and clamps SDI OUT to 1080P/i"
        )
    if claimed_fx6_builtin_vf_blanks_like_fx3_lcd:
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: FX6 built-in VF stays active during HDMI/SDI OSD output"
        )
    if claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on or (
        fx6_sq_fps > 60 and fx6_sdi_mode != "OFF" and "2160" in fx6_hdmi_mode
    ):
        errors.append(
            f"{P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC}: FX6 S&Q > 60fps with SDI ON or RAW clamps HDMI <= 1080p"
        )

    return P371CheckGroupBHdmi4k10BitRawAndFx6Sdi12gResult(
        group_id=P371_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        reset_action=reset_action,
        hdmi_resolution=hdmi_resolution,
        hdmi_resolution_options_exposed=tuple(hdmi_resolution_options_exposed),
        hdmi_4k_output_set=hdmi_4k_output_set,
        hdmi_4k_output_options_exposed=tuple(hdmi_4k_output_options_exposed),
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        output_resolution=output_resolution,
        effective_output_resolution=eff_output_res,
        hdmi_raw_output=hdmi_raw_output,
        raw_output_setting=raw_output_setting,
        hdmi_time_code_output=hdmi_time_code_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        effective_hdmi_info_display=eff_hdmi_info,
        fx3_lcd_blanked_for_hdmi_info=lcd_blanked,
        reboot_2400p_gate_triggered=crossing_2400p,
        sony_elf_typos_verified=tuple(sony_elf_typos_verified),
        fx6_sdi_mode=fx6_sdi_mode,
        fx6_hdmi_mode=fx6_hdmi_mode,
        fx6_sdi_hdmi_combo_count=fx6_sdi_hdmi_combo_count,
        fx6_rec_sync_mode=fx6_rec_sync_mode,
        fx6_raw_pipeline=fx6_raw_pipeline,
        fx6_builtin_vf_active=True,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 80 [TC/UB] VMC-BNCM1 TC-IN-Only & [FTP Transfer Func.])
# ---------------------------------------------------------------------------


def evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    # [TC/UB] 7 items + VMC-BNCM1
    tcub_items_exposed: Tuple[str, ...] = P371_TCUB_EXACT_7_ITEMS,
    video_system: str = "NTSC",
    rec_fps: float = 29.97,
    tc_format: str = P371_TC_FORMAT_DEFAULT,
    tc_run: str = "FREE_RUN",
    tc_make: str = "PRESET",
    tcub_disp_setting: str = "TC",
    tc_preset_delete_or_fw_update: bool = False,
    tc_make_typo_symbol: str = P371_TC_MAKE_TYPO_SYMBOL,
    vmc_bncm1_port: str = "BODY_MULTI_MICRO_USB",
    vmc_bncm1_direction: str = "TC_IN_ONLY",
    ext_lk_freewheel_after_unplug: bool = True,
    claimed_tcub_wiped_by_camera_reset: bool = False,
    expect_df_selectable_on_2398_2400_or_pal: bool = False,
    expect_tc_run_active_in_sq: bool = False,
    claimed_fx3_has_bnc_tc_out_or_clock_mode: bool = False,
    # FX6 TC/UB contrast
    fx6_bnc_tc_switch: str = "TC_IN",
    fx6_tc_make: str = "CLOCK",
    fx6_users_bit_hex: str = "A1B2C3D4",
    claimed_fx6_users_bit_ascii_title1: bool = False,
    # [FTP Transfer Func.] Explicit FTPES & Slot 1 .DAT
    ftp_transfer_func: str = "OFF",
    cloud_connection: str = "OFF",
    ftp_server_slot: int = 1,
    ftp_protocol: str = "FTPES_EXPLICIT_AUTH_TLS",
    ftp_transfer_mode: str = "PASSIVE",
    ftp_cacert_import_requested: bool = False,
    ftp_cacert_slot: int = 1,
    ftp_cacert_size_bytes: int = 2048,
    ftpset_slot: int = 1,
    ftpset_action: str = "NONE",
    ftpset_target_slot: int = 1,
    ftpset_encrypted_with_password: bool = True,
    ftpset_load_reboot_acknowledged: bool = True,
    ftpset_cross_model_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    claimed_fx3_supports_sftp_or_implicit_ftps_or_active: bool = False,
    fx6_file_transfer_cacert: str = P371_FX6_CACERT_FILENAME,
    fx6_chunk_proxy_upload_enabled: bool = True,
) -> P371CheckGroupCTcUbVmcBncm1AndFtpesSlot1Result:
    errors: List[str] = []
    warnings: List[str] = []

    if tuple(tcub_items_exposed) != P371_TCUB_EXACT_7_ITEMS:
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: [TC/UB] + [TC/UB Disp. Setting] must expose exact 7 items"
        )
    if claimed_tcub_wiped_by_camera_reset:
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: all 7 [TC/UB] + [TC/UB Disp. Setting] items resist [Camera Settings Reset]"
        )
    if tc_make_typo_symbol != P371_TC_MAKE_TYPO_SYMBOL:
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: expected Sony ELF typo {P371_TC_MAKE_TYPO_SYMBOL}"
        )
    if tc_format not in P371_TC_FORMAT_MODES:
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: invalid tc_format {tc_format!r}"
        )
    if tc_run not in P371_TC_RUN_MODES:
        errors.append(f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: invalid tc_run {tc_run!r}")
    if tc_make not in P371_TC_MAKE_MODES:
        errors.append(f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: invalid tc_make {tc_make!r}")
    if tcub_disp_setting not in P371_TCUB_DISP_MODES:
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: invalid tcub_disp_setting {tcub_disp_setting!r}"
        )

    df_allowed = (video_system == "NTSC") and (rec_fps in P371_NTSC_DF_CAPABLE_FPS)
    if expect_df_selectable_on_2398_2400_or_pal or (tc_format == "DF" and not df_allowed):
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: DF/NDF selectable strictly on NTSC 29.97p/59.94p/119.88p (23.98p/24.00p/PAL locked NDF)"
        )
    if expect_tc_run_active_in_sq and shoot_mode == "S_AND_Q":
        errors.append(
            f"{P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE}: S&Q mode disables [Time Code Run] and [Time Code Output]"
        )

    # VMC-BNCM1 TC-IN-Only via Body Multi/Micro USB
    if vmc_bncm1_port not in P371_VMC_PORT_MODES:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: invalid vmc_bncm1_port {vmc_bncm1_port!r}"
        )
    if vmc_bncm1_port == "XLR_H1_HANDLE_PORT":
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: VMC-BNCM1 is forbidden on XLR-H1 handle port (body Multi/Micro USB ONLY)"
        )
    if vmc_bncm1_direction not in P371_VMC_DIRECTIONS or vmc_bncm1_direction == "TC_OUT":
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: VMC-BNCM1 is unidirectional TC-IN-Only (TC_OUT forbidden)"
        )
    if claimed_fx3_has_bnc_tc_out_or_clock_mode:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: FX3 has zero BNC TC-OUT and zero Clock TC mode"
        )

    ext_lk_ready = (
        vmc_bncm1_port == "BODY_MULTI_MICRO_USB"
        and vmc_bncm1_direction == "TC_IN_ONLY"
        and shoot_mode == "MOVIE"
        and tc_make == "PRESET"
        and tc_run == "FREE_RUN"
    )
    if vmc_bncm1_port == "BODY_MULTI_MICRO_USB" and not ext_lk_ready:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: VMC-BNCM1 EXT-LK requires Movie + Preset + Free Run"
        )
    ext_lk_status = "EXT-LK" if ext_lk_ready else "INTERNAL_UNJAMMED"
    if not ext_lk_freewheel_after_unplug:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: EXT-LK free-wheels after VMC-BNCM1 unplug"
        )

    # FX6 BNC & Hex-only Users Bit
    if fx6_bnc_tc_switch not in P371_FX6_BNC_TC_SWITCH_MODES:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: invalid fx6_bnc_tc_switch {fx6_bnc_tc_switch!r}"
        )
    if fx6_tc_make not in P371_FX6_TC_MAKE_MODES:
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: invalid fx6_tc_make {fx6_tc_make!r}"
        )
    if claimed_fx6_users_bit_ascii_title1 or len(fx6_users_bit_hex) != 8 or any(
        c not in "0123456789ABCDEFabcdef" for c in fx6_users_bit_hex
    ):
        errors.append(
            f"{P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB}: FX6 Users Bit is 8-hex-digit only (Title1(ASCII) is Clip Title)"
        )

    # FTP Transfer Func. Explicit FTPES Passive-only & Slot 1 .DAT EROFS=30
    if ftp_transfer_func not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT}: ftp_transfer_func must be ON/OFF"
        )
    if ftp_transfer_func == "ON" and cloud_connection == "ON":
        errors.append(
            f"{P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT}: CLOUD_CONNECTION_ON_FTP_OFF mutual exclusion"
        )
    if not (1 <= ftp_server_slot <= P371_FTP_SERVER_SLOTS_MAX):
        errors.append(
            f"{P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT}: ftp_server_slot must be 1..9, got {ftp_server_slot}"
        )
    if ftp_protocol in P371_FTP_FORBIDDEN_PROTOCOLS or ftp_protocol not in P371_FTP_PROTOCOLS:
        errors.append(
            f"{P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT}: FX3 supports FTP or Explicit AUTH TLS FTPES only (zero SSH-SFTP / Implicit FTPS), got {ftp_protocol!r}"
        )
    if ftp_transfer_mode not in P371_FTP_TRANSFER_MODES or claimed_fx3_supports_sftp_or_implicit_ftps_or_active:
        errors.append(
            f"{P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT}: FX3 FTP client is Passive-only with zero SSH-SFTP / Implicit FTPS"
        )

    if ftp_cacert_slot != 1 or ftp_cacert_size_bytes <= 0 or ftp_cacert_size_bytes > P371_FTP_CACERT_MAX_BYTES:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: cacert.pem must reside on Slot 1 root and <= 1 MiB"
        )
    if not (1 <= ftpset_slot <= P371_FTPSET_SLOTS_MAX):
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: ftpset_slot must be 1..10, got {ftpset_slot}"
        )
    if not ftpset_encrypted_with_password:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: FTPSET01..10.DAT requires password encryption"
        )
    if ftpset_cross_model_requested:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: cross-model FTPSET*.DAT loading forbidden"
        )
    if ftpset_action == "LOAD" and not ftpset_load_reboot_acknowledged:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: loading FTPSET*.DAT requires mandatory reboot acknowledgment"
        )
    if (
        (ftp_cacert_import_requested and ftp_cacert_slot == 1)
        or (ftpset_action in ("SAVE", "DELETE") and ftpset_target_slot == 1)
    ) and (slot1_contains_tier0_dump or slot1_wp_locked):
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: Slot 1 Tier-0 Vault write/modify ({ftpset_action or 'cacert.pem'}) blocked with EROFS={P371_ERRNO_EROFS}"
        )
    if slot1_sector_writes != 0:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: slot1_sector_writes must remain 0"
        )
    if fx6_file_transfer_cacert != P371_FX6_CACERT_FILENAME:
        errors.append(
            f"{P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30}: FX6 uses Slot B {P371_FX6_CACERT_FILENAME}"
        )

    eff_tc_make = "PRESET" if reset_action == "INITIALIZE" else tc_make
    tc_preset_cleared = reset_action == "INITIALIZE" or tc_preset_delete_or_fw_update

    return P371CheckGroupCTcUbVmcBncm1AndFtpesSlot1Result(
        group_id=P371_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        tcub_items_exposed=tuple(tcub_items_exposed),
        video_system=video_system,
        rec_fps=rec_fps,
        tc_format=tc_format,
        tc_run=tc_run,
        tc_make=tc_make,
        tcub_disp_setting=tcub_disp_setting,
        effective_tc_make_after_reset=eff_tc_make,
        tc_preset_cleared_on_reset=tc_preset_cleared,
        vmc_bncm1_port=vmc_bncm1_port,
        vmc_bncm1_direction=vmc_bncm1_direction,
        ext_lk_status=ext_lk_status,
        fx6_bnc_tc_switch=fx6_bnc_tc_switch,
        fx6_tc_make=fx6_tc_make,
        fx6_users_bit_hex=fx6_users_bit_hex,
        ftp_transfer_func=ftp_transfer_func,
        ftp_server_slot=ftp_server_slot,
        ftp_protocol=ftp_protocol,
        ftp_transfer_mode=ftp_transfer_mode,
        ftp_cacert_slot=ftp_cacert_slot,
        ftp_cacert_size_bytes=ftp_cacert_size_bytes,
        ftpset_slot=ftpset_slot,
        ftpset_action=ftpset_action,
        ftpset_target_slot=ftpset_target_slot,
        ftpset_encrypted_with_password=ftpset_encrypted_with_password,
        ftpset_load_reboot_acknowledged=ftpset_load_reboot_acknowledged,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=PHASE371_SLOT1_SECTOR_WRITES,
        fx6_file_transfer_cacert=fx6_file_transfer_cacert,
        fx6_chunk_proxy_upload_enabled=fx6_chunk_proxy_upload_enabled,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 80 Creators' App 5-GATT BLE, G114 Airplane, Playback Shot Mark & Tier-0)
# ---------------------------------------------------------------------------


def evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    reset_action: str = "NONE",
    # Creators' App 5-GATT BLE & G114 Airplane Erratum
    ble_gatt_tables_exposed: Tuple[str, ...] = P371_BLE_EXACT_5_GATT_TABLES,
    creators_app_paired_count: int = 1,
    location_info_migrated_to_app_ver3: bool = True,
    cnct_while_power_off: str = "OFF",
    claimed_ble_survives_reset_network_set: bool = False,
    claimed_ble_wiped_by_camera_settings_reset: bool = False,
    claimed_fx6_has_creators_app_ble_or_airplane_mode: bool = False,
    airplane_mode: str = "ON",
    claimed_reset_network_set_clears_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    usb_lan_electrically_isolated: bool = True,
    expect_airplane_mode_isolates_usb_lan: bool = False,
    # Playback Write Matrix (*M01.XML, Rating, Protect, Delete, Asymmetric Copy)
    playback_write_op: str = "NONE",
    playback_target_slot: int = 2,
    playback_copy_direction: str = "NONE",
    rating_stars: int = 0,
    fx6_clip_flag: str = "OK",
    claimed_copy_slot2_to_slot1_safe: bool = False,
    claimed_fx6_supports_shotmark0_9_or_in_camera_copy: bool = False,
    # Tier-0 Vault & Zero-Telemetry Redlines
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    rf_tx_packets: int = 0,
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
) -> P371CheckGroupDCreatorsAppBleG114AirplaneAndShotMarkTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if tuple(ble_gatt_tables_exposed) != P371_BLE_EXACT_5_GATT_TABLES:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: libInfraBluetoothLowEnergy.so must expose exact 5 GATT tables {P371_BLE_EXACT_5_GATT_TABLES}"
        )
    if not (0 <= creators_app_paired_count <= P371_BLE_MAX_PAIRED_DEVICES):
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: BLE paired count max 15, got {creators_app_paired_count}"
        )
    if not location_info_migrated_to_app_ver3:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: [Location Info. Link Set.] migrated to Creators' App (8000DD00) in Ver. 3.00+"
        )
    if cnct_while_power_off not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: cnct_while_power_off must be ON/OFF"
        )
    if cnct_while_power_off == "ON" and airplane_mode == "ON":
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: Zero-RF bench requires [Cnct. while Power OFF]=OFF under Airplane Mode=ON"
        )
    if claimed_ble_survives_reset_network_set:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: BLE pairing is wiped by BOTH [Reset Network Set.] and [Initialize]"
        )
    if claimed_ble_wiped_by_camera_settings_reset:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: BLE pairing resists [Camera Settings Reset]"
        )
    if claimed_fx6_has_creators_app_ble_or_airplane_mode:
        errors.append(
            f"{P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET}: FX6 lacks Creators' App BLE GATT and Airplane Mode"
        )

    # Wave 80 G114 Airplane Mode Erratum & USB-LAN Isolation
    if airplane_mode not in P371_VALID_ON_OFF:
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: airplane_mode must be ON/OFF"
        )
    if airplane_mode != "ON":
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: Zero-RF bench requires [Airplane Mode]=ON"
        )
    if claimed_reset_network_set_clears_airplane_mode:
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: Wave 80 G114 erratum — [Airplane Mode]=On is NOT cleared by [Reset Network Set.] (Initialize-only)"
        )
    if claimed_initialize_preserves_airplane_mode:
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: [Initialize] resets [Airplane Mode] to Off"
        )
    if expect_airplane_mode_isolates_usb_lan or not usb_lan_electrically_isolated:
        errors.append(
            f"{P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION}: [Airplane Mode]=On does NOT block wired USB-LAN; physical USB-LAN isolation is mandatory"
        )

    # Playback Write Matrix & Asymmetric Copy
    if playback_write_op not in P371_PLAYBACK_WRITE_OPS:
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: invalid playback_write_op {playback_write_op!r}"
        )
    if playback_copy_direction not in P371_COPY_DIRECTIONS:
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: invalid playback_copy_direction {playback_copy_direction!r}"
        )
    if not (0 <= rating_stars <= 5):
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: rating_stars must be 0..5"
        )
    if fx6_clip_flag not in P371_FX6_CLIP_FLAGS:
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: invalid fx6_clip_flag {fx6_clip_flag!r}"
        )
    if claimed_fx6_supports_shotmark0_9_or_in_camera_copy:
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: FX6 uses Clip Flag (OK/NG/KEEP), not Shot Mark 0..9"
        )
    if claimed_copy_slot2_to_slot1_safe:
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: Copy Slot 2 -> Slot 1 mutates Slot 1 and is blocked EROFS={P371_ERRNO_EROFS}"
        )

    shotmark_or_mutating_op = playback_write_op in (
        "ADD_SHOT_MARK_1",
        "ADD_SHOT_MARK_2",
        "DELETE_SHOT_MARK_1",
        "DELETE_SHOT_MARK_2",
        "RATING",
        "PROTECT",
        "DELETE",
    )
    if (
        (shotmark_or_mutating_op and playback_target_slot == 1)
        or (playback_write_op == "COPY" and playback_copy_direction == "SLOT_2_TO_SLOT_1")
    ) and (slot1_contains_tier0_dump or slot1_wp_locked):
        errors.append(
            f"{P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30}: Playback write ({playback_write_op}/{playback_copy_direction}) on Slot 1 Tier-0 Vault blocked EROFS={P371_ERRNO_EROFS}"
        )

    # Zero-Telemetry & Fail-Closed Redlines
    if (
        slot1_sector_writes != 0
        or emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or rf_tx_packets != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
    ):
        errors.append(
            f"{P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: telemetry counters must remain 0 (slot1={slot1_sector_writes}, emmc={emmc_write_count}, e_nd={e_nd_actuator_tx_count}, rf={rf_tx_packets}, usb={usb_packets_transmitted}, passive={simulated_passive_tx_bytes})"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: live attach, persistent eMMC writes, and cross-model flash remain hard-locked False"
        )

    tier0 = _extract_tier0_evidence(
        simulate_bench_dry_run=simulate_bench_dry_run,
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
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
    )
    errors.extend(tier0["errors"])
    warnings.extend(tier0["warnings"])

    eff_ble_paired = (
        0
        if reset_action in ("RESET_NETWORK_SET", "INITIALIZE")
        else creators_app_paired_count
    )
    # G114 erratum: RESET_NETWORK_SET preserves Airplane Mode; INITIALIZE clears it
    eff_airplane = "OFF" if reset_action == "INITIALIZE" else airplane_mode

    return P371CheckGroupDCreatorsAppBleG114AirplaneAndShotMarkTier0Result(
        group_id=P371_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        reset_action=reset_action,
        ble_gatt_tables_exposed=tuple(ble_gatt_tables_exposed),
        creators_app_paired_count=creators_app_paired_count,
        location_info_migrated_to_app_ver3=location_info_migrated_to_app_ver3,
        cnct_while_power_off=cnct_while_power_off,
        effective_ble_paired_after_reset=eff_ble_paired,
        airplane_mode=airplane_mode,
        effective_airplane_mode_after_reset=eff_airplane,
        usb_lan_electrically_isolated=usb_lan_electrically_isolated,
        rf_tx_packets=PHASE371_RF_TX_PACKETS,
        rf_packets_transmitted=PHASE371_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE371_WIRELESS_RF_PACKETS_EMITTED,
        playback_write_op=playback_write_op,
        playback_target_slot=playback_target_slot,
        playback_copy_direction=playback_copy_direction,
        rating_stars=rating_stars,
        shot_mark_slot1_blocked_erofs30=True,
        copy_slot1_to_slot2_readonly_safe=True,
        copy_slot2_to_slot1_blocked_erofs30=True,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=PHASE371_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE371_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        fx6_clip_flag=fx6_clip_flag,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P371_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 371 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P371_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    # Group A
    zoom_range: str = P371_ZOOM_RANGE_DEFAULT,
    zoom_ring_rotate: str = P371_ZOOM_RING_ROTATE_DEFAULT,
    zoom_lever_stby_1st: int = P371_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_stby_2nd: int = P371_ZOOM_LEVER_2ND_DEFAULT,
    zoom_lever_rec_1st: int = P371_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_rec_2nd: int = P371_ZOOM_LEVER_2ND_DEFAULT,
    custom_key_zoom_mode: str = "FIXED",
    custom_key_zoom_stby_speed: int = P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_zoom_rec_speed: int = P371_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = 3,
    remote_zoom_fixed_rec_speed: int = 3,
    smart_zoom_requested: bool = False,
    still_file_format: str = "JPEG",
    still_image_size: str = "M",
    rec_frame_rate_fps: float = 59.94,
    sq_frame_rate_fps: int = 24,
    hdmi_raw_output: bool = False,
    focus_area: str = "WIDE",
    metering_mode: str = "MULTI",
    face_eye_prior_in_af: str = "ON",
    face_priority_in_multi_metering: str = "ON",
    tracking_af_active: bool = False,
    claimed_zoom_range_wiped_by_camera_reset: bool = False,
    claimed_zoom_ring_rotate_wiped_by_camera_reset: bool = False,
    claimed_zoom_speeds_resist_camera_reset: bool = False,
    claimed_custom_key_zoom_has_variable_mode: bool = False,
    expect_ciz_active_under_lockout: bool = False,
    expect_focus_area_or_tracking_under_ciz: bool = False,
    fx6_zoom_type: str = "CLEAR_IMAGE_ZOOM",
    fx6_handle_zoom_mode: str = "VARIABLE",
    fx6_handle_zoom_hud_position: int = 50,
    claimed_fx6_has_digital_zoom: bool = False,
    claimed_fx6_0_99_is_speed_scale: bool = False,
    dial_customize_items: Tuple[str, ...] = P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS,
    dormant_dial_customize_item_requested: Optional[str] = None,
    my_dial_slot: int = 1,
    my_dial_active: bool = False,
    av_tv_rotate: str = "NORMAL",
    function_ring_lens: str = P371_FUNCTION_RING_DEFAULT,
    lock_operation_parts: str = "OFF",
    claimed_dial_customize_wiped_by_camera_reset: bool = False,
    expect_lock_op_blocks_my_dial: bool = False,
    diff_set_items: Tuple[str, ...] = P371_DIFF_SET_EXACT_8_ITEMS,
    diff_set_pp_checked: bool = True,
    claimed_pp_diffset_wiped_by_reset_or_init: bool = False,
    shutter_mode: str = "SPEED",
    expect_shutter_angle_shares_still_movie: bool = False,
    fn_menu_still_slots: int = P371_FN_MENU_STILL_SLOTS,
    fn_menu_movie_slots: int = P371_FN_MENU_MOVIE_SLOTS,
    fn_menu_all_not_set_requested: bool = False,
    monitor_disp_pages: Tuple[str, ...] = P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES,
    dormant_evf_disp_requested: Optional[str] = None,
    claimed_fx3_has_builtin_evf: bool = False,
    select_lut: str = "s709",
    display_lut: str = "OFF",
    gamma_display_assist: str = "OFF",
    expect_gamma_assist_active_in_log_movie: bool = False,
    # Group B
    picture_profile: str = "PP11",
    apsc_s35_shooting: str = "OFF",
    hdmi_resolution: str = "AUTO",
    hdmi_resolution_options_exposed: Tuple[str, ...] = P371_HDMI_RESOLUTIONS_EXACT_4,
    hdmi_4k_output_set: str = "23_98P_10BIT_422",
    prev_hdmi_4k_output_set: str = "23_98P_10BIT_422",
    hdmi_4k_output_options_exposed: Tuple[str, ...] = P371_HDMI_4K_OUTPUT_EXACT_6_MODES,
    dormant_hdmi_4k_mode_requested: Optional[str] = None,
    reboot_2400p_acknowledged: bool = True,
    rec_media_dur_hdmi_output: str = "ON",
    output_resolution: str = "AUTO",
    raw_output_setting: str = "23_98P",
    hdmi_time_code_output: str = "ON",
    hdmi_rec_control: str = "OFF",
    hdmi_4ch_audio_output: str = "CH1_CH2",
    hdmi_info_display: str = "OFF",
    sony_elf_typos_verified: Tuple[str, ...] = P371_SONY_ELF_TYPOS,
    claimed_external_output_wiped_by_camera_reset: bool = False,
    claimed_hdmi_has_720p_or_420: bool = False,
    claimed_color_gamut_for_raw_output_present: bool = False,
    expect_fx3_lcd_active_when_rec_on_info_on_raw_off: bool = False,
    expect_4k_internal_hdmi_when_log_or_pplut: bool = False,
    expect_rec_ctrl_without_tc_output_or_in_sq: bool = False,
    fx6_sdi_mode: str = "12G_SDI",
    fx6_hdmi_mode: str = "3840x2160_59_94P",
    fx6_sdi_hdmi_combo_count: int = P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT,
    fx6_rec_sync_mode: str = "SDI_HDMI_REMOTE_IF",
    fx6_raw_pipeline: str = "NONE",
    fx6_sq_fps: int = 24,
    claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi: bool = False,
    claimed_fx6_builtin_vf_blanks_like_fx3_lcd: bool = False,
    claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on: bool = False,
    # Group C
    tcub_items_exposed: Tuple[str, ...] = P371_TCUB_EXACT_7_ITEMS,
    video_system: str = "NTSC",
    tc_format: str = P371_TC_FORMAT_DEFAULT,
    tc_run: str = "FREE_RUN",
    tc_make: str = "PRESET",
    tcub_disp_setting: str = "TC",
    tc_preset_delete_or_fw_update: bool = False,
    tc_make_typo_symbol: str = P371_TC_MAKE_TYPO_SYMBOL,
    vmc_bncm1_port: str = "BODY_MULTI_MICRO_USB",
    vmc_bncm1_direction: str = "TC_IN_ONLY",
    ext_lk_freewheel_after_unplug: bool = True,
    claimed_tcub_wiped_by_camera_reset: bool = False,
    expect_df_selectable_on_2398_2400_or_pal: bool = False,
    expect_tc_run_active_in_sq: bool = False,
    claimed_fx3_has_bnc_tc_out_or_clock_mode: bool = False,
    fx6_bnc_tc_switch: str = "TC_IN",
    fx6_tc_make: str = "CLOCK",
    fx6_users_bit_hex: str = "A1B2C3D4",
    claimed_fx6_users_bit_ascii_title1: bool = False,
    ftp_transfer_func: str = "OFF",
    cloud_connection: str = "OFF",
    ftp_server_slot: int = 1,
    ftp_protocol: str = "FTPES_EXPLICIT_AUTH_TLS",
    ftp_transfer_mode: str = "PASSIVE",
    ftp_cacert_import_requested: bool = False,
    ftp_cacert_slot: int = 1,
    ftp_cacert_size_bytes: int = 2048,
    ftpset_slot: int = 1,
    ftpset_action: str = "NONE",
    ftpset_target_slot: int = 1,
    ftpset_encrypted_with_password: bool = True,
    ftpset_load_reboot_acknowledged: bool = True,
    ftpset_cross_model_requested: bool = False,
    claimed_fx3_supports_sftp_or_implicit_ftps_or_active: bool = False,
    fx6_file_transfer_cacert: str = P371_FX6_CACERT_FILENAME,
    fx6_chunk_proxy_upload_enabled: bool = True,
    # Group D + Tier-0
    ble_gatt_tables_exposed: Tuple[str, ...] = P371_BLE_EXACT_5_GATT_TABLES,
    creators_app_paired_count: int = 1,
    location_info_migrated_to_app_ver3: bool = True,
    cnct_while_power_off: str = "OFF",
    claimed_ble_survives_reset_network_set: bool = False,
    claimed_ble_wiped_by_camera_settings_reset: bool = False,
    claimed_fx6_has_creators_app_ble_or_airplane_mode: bool = False,
    airplane_mode: str = "ON",
    claimed_reset_network_set_clears_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    usb_lan_electrically_isolated: bool = True,
    expect_airplane_mode_isolates_usb_lan: bool = False,
    playback_write_op: str = "NONE",
    playback_target_slot: int = 2,
    playback_copy_direction: str = "NONE",
    rating_stars: int = 0,
    fx6_clip_flag: str = "OK",
    claimed_copy_slot2_to_slot1_safe: bool = False,
    claimed_fx6_supports_shotmark0_9_or_in_camera_copy: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    rf_tx_packets: int = 0,
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
) -> RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport:
    donor = inspect_phase371_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        zoom_range=zoom_range,
        zoom_ring_rotate=zoom_ring_rotate,
        zoom_lever_stby_1st=zoom_lever_stby_1st,
        zoom_lever_stby_2nd=zoom_lever_stby_2nd,
        zoom_lever_rec_1st=zoom_lever_rec_1st,
        zoom_lever_rec_2nd=zoom_lever_rec_2nd,
        custom_key_zoom_mode=custom_key_zoom_mode,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        remote_zoom_speed_type=remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        smart_zoom_requested=smart_zoom_requested,
        still_file_format=still_file_format,
        still_image_size=still_image_size,
        rec_frame_rate_fps=rec_frame_rate_fps,
        sq_frame_rate_fps=sq_frame_rate_fps,
        hdmi_raw_output=hdmi_raw_output,
        focus_area=focus_area,
        metering_mode=metering_mode,
        face_eye_prior_in_af=face_eye_prior_in_af,
        face_priority_in_multi_metering=face_priority_in_multi_metering,
        tracking_af_active=tracking_af_active,
        claimed_zoom_range_wiped_by_camera_reset=claimed_zoom_range_wiped_by_camera_reset,
        claimed_zoom_ring_rotate_wiped_by_camera_reset=claimed_zoom_ring_rotate_wiped_by_camera_reset,
        claimed_zoom_speeds_resist_camera_reset=claimed_zoom_speeds_resist_camera_reset,
        claimed_custom_key_zoom_has_variable_mode=claimed_custom_key_zoom_has_variable_mode,
        expect_ciz_active_under_lockout=expect_ciz_active_under_lockout,
        expect_focus_area_or_tracking_under_ciz=expect_focus_area_or_tracking_under_ciz,
        fx6_zoom_type=fx6_zoom_type,
        fx6_handle_zoom_mode=fx6_handle_zoom_mode,
        fx6_handle_zoom_hud_position=fx6_handle_zoom_hud_position,
        claimed_fx6_has_digital_zoom=claimed_fx6_has_digital_zoom,
        claimed_fx6_0_99_is_speed_scale=claimed_fx6_0_99_is_speed_scale,
        dial_customize_items=dial_customize_items,
        dormant_dial_customize_item_requested=dormant_dial_customize_item_requested,
        my_dial_slot=my_dial_slot,
        my_dial_active=my_dial_active,
        av_tv_rotate=av_tv_rotate,
        function_ring_lens=function_ring_lens,
        lock_operation_parts=lock_operation_parts,
        claimed_dial_customize_wiped_by_camera_reset=claimed_dial_customize_wiped_by_camera_reset,
        expect_lock_op_blocks_my_dial=expect_lock_op_blocks_my_dial,
        diff_set_items=diff_set_items,
        diff_set_pp_checked=diff_set_pp_checked,
        claimed_pp_diffset_wiped_by_reset_or_init=claimed_pp_diffset_wiped_by_reset_or_init,
        shutter_mode=shutter_mode,
        expect_shutter_angle_shares_still_movie=expect_shutter_angle_shares_still_movie,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        fn_menu_all_not_set_requested=fn_menu_all_not_set_requested,
        monitor_disp_pages=monitor_disp_pages,
        dormant_evf_disp_requested=dormant_evf_disp_requested,
        claimed_fx3_has_builtin_evf=claimed_fx3_has_builtin_evf,
        select_lut=select_lut,
        display_lut=display_lut,
        gamma_display_assist=gamma_display_assist,
        expect_gamma_assist_active_in_log_movie=expect_gamma_assist_active_in_log_movie,
    )

    gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        apsc_s35_shooting=apsc_s35_shooting,
        reset_action=reset_action,
        hdmi_resolution=hdmi_resolution,
        hdmi_resolution_options_exposed=hdmi_resolution_options_exposed,
        hdmi_4k_output_set=hdmi_4k_output_set,
        prev_hdmi_4k_output_set=prev_hdmi_4k_output_set,
        hdmi_4k_output_options_exposed=hdmi_4k_output_options_exposed,
        dormant_hdmi_4k_mode_requested=dormant_hdmi_4k_mode_requested,
        reboot_2400p_acknowledged=reboot_2400p_acknowledged,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        output_resolution=output_resolution,
        hdmi_raw_output=hdmi_raw_output,
        raw_output_setting=raw_output_setting,
        hdmi_time_code_output=hdmi_time_code_output,
        hdmi_rec_control=hdmi_rec_control,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        hdmi_info_display=hdmi_info_display,
        sony_elf_typos_verified=sony_elf_typos_verified,
        claimed_external_output_wiped_by_camera_reset=claimed_external_output_wiped_by_camera_reset,
        claimed_hdmi_has_720p_or_420=claimed_hdmi_has_720p_or_420,
        claimed_color_gamut_for_raw_output_present=claimed_color_gamut_for_raw_output_present,
        expect_fx3_lcd_active_when_rec_on_info_on_raw_off=expect_fx3_lcd_active_when_rec_on_info_on_raw_off,
        expect_4k_internal_hdmi_when_log_or_pplut=expect_4k_internal_hdmi_when_log_or_pplut,
        expect_rec_ctrl_without_tc_output_or_in_sq=expect_rec_ctrl_without_tc_output_or_in_sq,
        fx6_sdi_mode=fx6_sdi_mode,
        fx6_hdmi_mode=fx6_hdmi_mode,
        fx6_sdi_hdmi_combo_count=fx6_sdi_hdmi_combo_count,
        fx6_rec_sync_mode=fx6_rec_sync_mode,
        fx6_raw_pipeline=fx6_raw_pipeline,
        fx6_sq_fps=fx6_sq_fps,
        claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi=claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi,
        claimed_fx6_builtin_vf_blanks_like_fx3_lcd=claimed_fx6_builtin_vf_blanks_like_fx3_lcd,
        claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on=claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on,
    )

    gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        tcub_items_exposed=tcub_items_exposed,
        video_system=video_system,
        rec_fps=rec_frame_rate_fps,
        tc_format=tc_format,
        tc_run=tc_run,
        tc_make=tc_make,
        tcub_disp_setting=tcub_disp_setting,
        tc_preset_delete_or_fw_update=tc_preset_delete_or_fw_update,
        tc_make_typo_symbol=tc_make_typo_symbol,
        vmc_bncm1_port=vmc_bncm1_port,
        vmc_bncm1_direction=vmc_bncm1_direction,
        ext_lk_freewheel_after_unplug=ext_lk_freewheel_after_unplug,
        claimed_tcub_wiped_by_camera_reset=claimed_tcub_wiped_by_camera_reset,
        expect_df_selectable_on_2398_2400_or_pal=expect_df_selectable_on_2398_2400_or_pal,
        expect_tc_run_active_in_sq=expect_tc_run_active_in_sq,
        claimed_fx3_has_bnc_tc_out_or_clock_mode=claimed_fx3_has_bnc_tc_out_or_clock_mode,
        fx6_bnc_tc_switch=fx6_bnc_tc_switch,
        fx6_tc_make=fx6_tc_make,
        fx6_users_bit_hex=fx6_users_bit_hex,
        claimed_fx6_users_bit_ascii_title1=claimed_fx6_users_bit_ascii_title1,
        ftp_transfer_func=ftp_transfer_func,
        cloud_connection=cloud_connection,
        ftp_server_slot=ftp_server_slot,
        ftp_protocol=ftp_protocol,
        ftp_transfer_mode=ftp_transfer_mode,
        ftp_cacert_import_requested=ftp_cacert_import_requested,
        ftp_cacert_slot=ftp_cacert_slot,
        ftp_cacert_size_bytes=ftp_cacert_size_bytes,
        ftpset_slot=ftpset_slot,
        ftpset_action=ftpset_action,
        ftpset_target_slot=ftpset_target_slot,
        ftpset_encrypted_with_password=ftpset_encrypted_with_password,
        ftpset_load_reboot_acknowledged=ftpset_load_reboot_acknowledged,
        ftpset_cross_model_requested=ftpset_cross_model_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=slot1_sector_writes,
        claimed_fx3_supports_sftp_or_implicit_ftps_or_active=claimed_fx3_supports_sftp_or_implicit_ftps_or_active,
        fx6_file_transfer_cacert=fx6_file_transfer_cacert,
        fx6_chunk_proxy_upload_enabled=fx6_chunk_proxy_upload_enabled,
    )

    gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        reset_action=reset_action,
        ble_gatt_tables_exposed=ble_gatt_tables_exposed,
        creators_app_paired_count=creators_app_paired_count,
        location_info_migrated_to_app_ver3=location_info_migrated_to_app_ver3,
        cnct_while_power_off=cnct_while_power_off,
        claimed_ble_survives_reset_network_set=claimed_ble_survives_reset_network_set,
        claimed_ble_wiped_by_camera_settings_reset=claimed_ble_wiped_by_camera_settings_reset,
        claimed_fx6_has_creators_app_ble_or_airplane_mode=claimed_fx6_has_creators_app_ble_or_airplane_mode,
        airplane_mode=airplane_mode,
        claimed_reset_network_set_clears_airplane_mode=claimed_reset_network_set_clears_airplane_mode,
        claimed_initialize_preserves_airplane_mode=claimed_initialize_preserves_airplane_mode,
        usb_lan_electrically_isolated=usb_lan_electrically_isolated,
        expect_airplane_mode_isolates_usb_lan=expect_airplane_mode_isolates_usb_lan,
        playback_write_op=playback_write_op,
        playback_target_slot=playback_target_slot,
        playback_copy_direction=playback_copy_direction,
        rating_stars=rating_stars,
        fx6_clip_flag=fx6_clip_flag,
        claimed_copy_slot2_to_slot1_safe=claimed_copy_slot2_to_slot1_safe,
        claimed_fx6_supports_shotmark0_9_or_in_camera_copy=claimed_fx6_supports_shotmark0_9_or_in_camera_copy,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=slot1_sector_writes,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        rf_tx_packets=rf_tx_packets,
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
            P371_GO_NO_GO_BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE
        )
        overall_status = go_no_go
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P371_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = (
            P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED
        )
        overall_status = go_no_go

    report = RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport(
        schema_version=P371_SCHEMA,
        phase_version=P371_VERSION,
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
        h0_h3_surface_count=P371_STORAGE_SURFACE_COUNT,
        slot1_tier0_vault_mutated=False,
        ready_for_live_camera_attach=False,
        overall_ready_for_hardware_attach=False,
        live_attach_authorized=False,
        hardware_live_attachment_authorized=False,
        emmc_writes_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_builtin_evf_present=False,
        fx3_custom_key_zoom_variable_supported=False,
        fx3_hdmi_720p_supported=False,
        fx3_sftp_supported=False,
        fx3_implicit_ftps_supported=False,
        emmc_write_count=PHASE371_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE371_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=PHASE371_E_ND_I2C_TX_BYTES,
        rf_tx_packets=PHASE371_RF_TX_PACKETS,
        rf_packets_transmitted=PHASE371_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE371_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=PHASE371_RF_NVS_MUTATION_BYTES,
        slot1_sector_writes=PHASE371_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE371_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE371_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE371_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE371_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport(
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


def run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
    **kwargs: Any,
) -> RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport:
    return evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
        **kwargs
    )


def verify_phase371_report(
    payload: Union[
        Mapping[str, Any],
        RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport,
    ],
) -> Phase371ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P371_SCHEMA:
        errors.append(
            f"schema_version mismatch: {payload.get('schema_version')!r} != {P371_SCHEMA!r}"
        )
    if payload.get("sony_help_guide_id") != P371_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_371_VALID_GO_NO_GO_VALUES:
        errors.append(f"invalid go_no_go: {payload.get('go_no_go')!r}")

    locked_false_fields = (
        "ready_for_live_camera_attach",
        "overall_ready_for_hardware_attach",
        "live_attach_authorized",
        "hardware_live_attachment_authorized",
        "emmc_writes_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_builtin_evf_present",
        "fx3_custom_key_zoom_variable_supported",
        "fx3_hdmi_720p_supported",
        "fx3_sftp_supported",
        "fx3_implicit_ftps_supported",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "emmc_write_count",
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_tx_packets",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "rf_nvs_mutation_bytes",
        "slot1_sector_writes",
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
        P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase371ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase371_markdown(
    report: RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport,
) -> str:
    lines = [
        f"# Phase 371 — 24th Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}`, "
        f"`live_attach_authorized={report.live_attach_authorized}`, "
        f"`emmc_writes_authorized={report.emmc_writes_authorized}`, "
        f"`rf_tx_packets={report.rf_tx_packets}`, `slot1_sector_writes={report.slot1_sector_writes}`, "
        f"`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"zoom_range=`{report.check_group_a.zoom_range}`, custom_key_zoom=`{report.check_group_a.custom_key_zoom_mode}`, "
        f"dial_customize={len(report.check_group_a.dial_customize_items)}, diff_set={len(report.check_group_a.diff_set_items)}, "
        f"evf={report.check_group_a.fx3_builtin_evf_present}",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"hdmi_res=`{report.check_group_b.hdmi_resolution}`, hdmi_4k=`{report.check_group_b.hdmi_4k_output_set}`, "
        f"lcd_blanked=`{report.check_group_b.fx3_lcd_blanked_for_hdmi_info}`, fx6_sdi=`{report.check_group_b.fx6_sdi_mode}` "
        f"({report.check_group_b.fx6_sdi_hdmi_combo_count} combos)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"tcub_items={len(report.check_group_c.tcub_items_exposed)}, ext_lk=`{report.check_group_c.ext_lk_status}`, "
        f"ftp_protocol=`{report.check_group_c.ftp_protocol}`, slot1_writes={report.check_group_c.slot1_sector_writes}",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"ble_tables={len(report.check_group_d.ble_gatt_tables_exposed)}, airplane=`{report.check_group_d.effective_airplane_mode_after_reset}`, "
        f"playback_op=`{report.check_group_d.playback_write_op}`, copy_dir=`{report.check_group_d.playback_copy_direction}`, "
        f"slot1_mut={report.check_group_d.slot1_tier0_vault_mutated}",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
