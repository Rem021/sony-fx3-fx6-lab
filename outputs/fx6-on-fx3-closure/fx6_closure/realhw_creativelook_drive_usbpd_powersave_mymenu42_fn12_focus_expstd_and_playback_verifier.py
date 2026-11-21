"""Phase 381 — 26th Physical Bench Readiness Verifier (`26/26`, Waves 83-84).

Implements `preflight-creativelook-drive-usbpd-powersave-mymenu42-fn12-focus-expstd-and-playback`
(short CLI alias `preflight-phase381`) aligned with Global Sony Real-Hardware Empirical
Intelligence Waves 83-84 across Check Groups A-D and the mandatory `16/16 H0 == H3`
dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (Wave 83.1-83.2: `[Creative Look]` 10+6 / `354` NVRAM Keys & Dormant
  `[Soft Skin Effect]` + Still `[Drive Mode]` / `> F11` AF Lock / 16 EV Brackets / Dormant
  `[Focus Bracket]` & Ver. 7.02 `[Shutter Type in Interval]`):
  - `[Creative Look]` (`ST` default, `Can be reset`): 10 presets (`ST..SE`) + 6 `Custom Look`
    (`Custom Look 1..6`), `354` NVRAM keys (`2` main + `352` `11 x 16 x 2` incl. 3-track split
    `look`/`look_still`/`look_movie`). Asymmetric 8-parameter bounds: `Contrast/Highlights/
    Shadows/Saturation` `-9..+9`, `Fade/Sharpness/Clarity` `0..9` (non-negative), `Sharpness
    Range` (`fineness`) `1..5` (locked in Movie/S&Q), `Saturation` locked in `BW`/`SE`. 4 hard
    lockouts (`PP11` out-of-box, `Log != Off`, `HLG Still = On`, `iAuto`). `[Soft Skin Effect]`
    100% dormant on FX3/FX3A/FX6 (`EOPNOTSUPP=95`). Contrast FX6 `Paint/Look > Base Look` +
    `User 1..16`.
  - Still `[Drive Mode]` (exact 8 modes, `Single Shooting` default, `Can be reset`): `Hi+`
    `10 fps` (no live-view, post-view only), `Hi` `8 fps`, `Mid` `6 fps`, `Lo` `3 fps`; AF
    locks on frame 1 at `> F11` (NOT `F8`!) in `Hi+/Hi/Mid`; CFexpress Type A `CEA-G160T`
    `~1,000+` buffer (`NVMe` vs `MMCB`). Exact `16` EV bracket combos (`0.3/0.5/0.7/1.0 EV` x
    `3/5/9` + `2.0/3.0 EV` x `3/5`, zero `9 Image` for `2.0/3.0 EV`). `[Focus Bracket]` 100%
    dormant (`EOPNOTSUPP=95`, `129` FX3 / `98` FX6 dormant symbols — recording Wave 83 `G151`
    erratum `56` vs `98`). `[Interval Shoot Func.]` exact 7 items ALL `Can be reset`, Ver. 7.02
    name `[Shutter Type in Interval]` (default `Electronic Shutter`, replacing legacy `[Silent
    Shoot. in Interval]`), zero in-camera movie synthesis. Contrast FX6 `S&Q Motion` / `Interval
    Rec` / `Picture Cache Rec` & ZERO `Frame Rec` (`0` hits).
- **Check Group B** (Wave 83.3-83.4: `[USB Power Supply]` / `libUsbBusPower.so` 11 PMIC Drivers /
  `NP-FZ100` Handshake / `DC-C1` + `[Power Setting Option]` FX3 9-Item vs `ILME-FX3A` 8-Item
  Bypass & IR/NFC Removal):
  - `libUsbBusPower.so` (`48,232 B`, 11 PMIC/charger `.ko` modules incl. `usb_bd91407gw.ko`,
    `usb_smb232.ko`, `usb_max*`, `GetCurrentBattState`/`IsSinkReady`), mandatory in-slot
    `NP-FZ100` (`7.2 V`), USB-PD `9V/3A` `HIGH` recommended (zero ON-state charging, `CHARGE`
    LED off; OFF-state `10°C-30°C` `9V/2A+`), `5V/1.5A` `LOW` drains, `Sony DC-C1` requires
    `>= 65 W + 5A` cable; hot-pulling `NP-FZ100` cuts `SYS` rail bypassing `cpapp-b.bin`
    `SequenceAsync_PowerOff` & `libInfraMediaCommon.so` `mcmn_drv_writeandflush`/`fsync`
    (Tier-0 power-loss redline). Contrast FX6 `19.5V` EIAJ `DC IN` (`18.0-20.5V`, battery-less
    boot, seamless `BP-U` fallback, hot-replug reboot trap).
  - `[Power Setting Option]` exact 2 anti-Reset items: `[Power Save Start Time]` (`Off`/`30 Min`/
    `5 Min` def/`2 Min`/`1 Min`/`10 Sec`; FX3 `9` bypasses vs 2025 `ILME-FX3A` `8` bypasses
    after IR removal) & `[Auto Power OFF Temp.]` (`Standard` def/`High` tripod-only). `[Power
    Save by Monitor]` 100% dormant (`EOPNOTSUPP=95`). `ILME-FX3A` (`ilc/2510`, `2.36M`-dot LCD)
    physically removed IR remote receiver & NFC; original FX3 IR & BLE remote mutually exclusive;
    Ver. 7.00+ `[USB-LAN Cnct. Launch]`. Contrast FX6 `2.5 mm` LANC + `3.5 mm` grip remote (zero
    BLE/IR).
- **Check Group C** (Wave 84.1-84.2: `[My Menu]` 42 Slots / `12+12` `[Fn Menu Settings]` +
  `[Focus Mode]` Still 5 vs Movie 2 / Movie `[AF Subj. Shift Sensitivity]` Default
  `5(Responsive)` / `14`-Item `[Focus Area Limit]`):
  - `[My Menu]`: exact `6 x 7 = 42` slots (`BKID_APP_mymenu_group1..6_setting_list0..6`,
    debunking `30`/`36` & recording Wave 84 `G98` erratum), Playback blacklist, all 6 management
    ops + `[Display From My Menu]` (`Off` def) anti-Reset, persisted in Slot 1 `CAMSET01..10.DAT`
    (Slot 1 Save/Delete `EROFS=30`). `[Fn Menu Settings]`: strict `12` Still + `12` Movie
    independent slots, ZERO `Follow Custom` switch, all-`Not set` blocked (`_f 0x6220`), `XLR-H1`
    zero `Fn`/`MENU`/REC keys. Contrast FX6 `User Menu` (20 items, `User Menu Only` + 4-digit
    `User Menu with Lock` excluded from `All File`).
  - `[Focus Mode]`: Still 5 (`AF-S`/`AF-A` def/`AF-C`/`DMF`/`MF`) vs Movie/`S&Q` locked 2
    (`AF-C` [`MOVIE_AUTO`]/`MF`). Still `[AF w/ Shutter]` (`On` def, anti-Reset), `[Pre-AF]`
    (`Off` def, anti-Reset, E-mount only), `[AF Tracking Sensitivity]` (`3(Standard)` def,
    resettable). Movie `[AF Transition Speed]` (`1..7`, def `5`), `[AF Subj. Shift Sensitivity]`
    (`1..5`, def `5(Responsive)` NOT `3`!, ELF `RESPONSICE`). `[Focus Area Limit]` exact 14
    checkboxes (min 2 to switch `.uxc 0xea28`); `[Circ. of Focus Point]` (`Does Not Circulate`
    def, anti-Reset, orthogonal only across 8 movable areas). Contrast FX6 `Face/Eye Only AF` /
    `Face/Eye Priority AF` / `Off`.
- **Check Group D + Tier-0** (Wave 84.3-84.4 + `16/16 H0 == H3` Dual-Media `528 B FX3RCPT1`):
  - `[Exposure Comp.]` (Still `±5.0 EV` / Movie `±2.0 EV`, locked in `iAuto`/`M+fixed ISO`/
    `Cine EI`/`Cine EI Quick`), `[Exposure step]` (`0.3EV` def/`0.5EV`, anti-Reset, independent
    of `Shutter Angle`), `[Exposure Std. Adjust]` ALL 5 metering modes (`Multi`/`Center`/`Spot`/
    `Entire Screen Average`/`Highlight`, `±1 EV @ 1/6 EV` 13 steps, anti-Reset), `[AEL w/ Shutter]`
    (Still-only `Auto` def, anti-Reset), `[Spot Metering Point]` exact 8 focus-point-linked
    (initial point only in Tracking) / 6 center-locked (incl. `Tracking: Wide/Zone/Center Fix` —
    Wave 84 `G116` erratum). Contrast FX6 `Auto Exposure Level` (`±3.0 EV @ 0.25 EV` 25 steps,
    ZERO `AE Shift`) + `AGC Limit` (`3..36 dB` / 12 ISO groups).
  - `[View Mode]` exact 3 states (`Date View` def/`Folder View(Still)`/`Movie View`, zero
    codec-split XAVC views), `[Display Rotation]` default `Auto` (NOT `Off`!, ELF `rotatiton`),
    `[Image Index]` (`9`/`25`), `[Display as Group]` (`Off` def), `[Enlarge Initial Mag./Position]`
    — all anti-Reset. `[Protect]` (7 menu items, ZERO `"Single"` — Wave 84 `G114` erratum; syncs
    `M4ROOT/SUB/*S03.MP4`) & `[Rating]` (`0..5` XMP write) targeting `Slot 1` MUST fail-closed
    with `EROFS=30` (`slot1_data_sector_writes == 0`). `[Select on Cam & Send]` hard-blocked when
    `[Airplane Mode] = On` (zero-RF redline). Contrast FX6 `Thumbnail` / `OK-NG-KEEP` / `Shot Mark
    1/2` / `Lock/Unlock Clip`.
  - Tier-0 Receipt Gate: Dual-media `528 B FX3RCPT1` Copy A & Copy B with distinct `st_dev`,
    `16/16 H0 == H3`, non-trivial serial/CID, `0x91030080` + fw `7.02`.
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

P381_VERSION = "phase381_v1"
PHASE381_VERSION = P381_VERSION
PHASE_381_VERSION = P381_VERSION

P381_SCHEMA = (
    "realhw_preflight26_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_playback_v1"
)
P381_SCHEMA_VERSION = P381_SCHEMA
PHASE_381_SCHEMA = P381_SCHEMA
REALHW_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_PLAYBACK_SCHEMA = P381_SCHEMA

P381_SONY_HELP_GUIDE_ID = "ilc/2210"
P381_SONY_FX3A_HELP_GUIDE_ID = "ilc/2510"
P381_STORAGE_SURFACE_COUNT = 16
P381_HEADER_READ_BYTES = 64

P381_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED = (
    "READONLY_PREFLIGHT26_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED"
)
P381_GO_NO_GO_BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE = (
    "BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE"
)
PHASE_381_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED,
    P381_GO_NO_GO_BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE,
)

P381_CHECK_GROUP_A_ID = "p381_ga_creativelook_354nvram_softskin_drive_f11_focusbracket_interval"
P381_CHECK_GROUP_B_ID = "p381_gb_usbpd_11pmic_npfz100_dcc1_powersave_fx3_9_vs_fx3a_8_ir_lanc"
P381_CHECK_GROUP_C_ID = "p381_gc_mymenu42_fn12_focusmode_5vs2_subjshift5_focuslimit14_circ"
P381_CHECK_GROUP_D_ID = "p381_gd_expcomp_expstd5_spot8vs6_playback_slot1_erofs30_zerorf_tier0"
PHASE_381_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P381_CHECK_GROUP_A_ID,
    P381_CHECK_GROUP_B_ID,
    P381_CHECK_GROUP_C_ID,
    P381_CHECK_GROUP_D_ID,
)

# Errno constants
P381_ERRNO_EPERM = 1
P381_ERRNO_EBUSY = 16
P381_ERRNO_EINVAL = 22
P381_ERRNO_EROFS = 30
P381_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE381_EMMC_WRITE_COUNT = 0
PHASE381_E_ND_ACTUATOR_TX_COUNT = 0
PHASE381_E_ND_I2C_TX_BYTES = 0
PHASE381_RF_TX_PACKETS = 0
PHASE381_RF_PACKETS_TRANSMITTED = 0
PHASE381_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE381_RF_NVS_MUTATION_BYTES = 0
PHASE381_SLOT1_SECTOR_WRITES = 0
PHASE381_SLOT1_DATA_SECTOR_WRITES = 0
PHASE381_USB_PACKETS_TRANSMITTED = 0
PHASE381_PASSIVE_TX_BYTES_EMITTED = 0
PHASE381_RAW_FIRMWARE_BYTES_LEAKED = 0

P381_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P381_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P381_VALID_EXPOSURE_MODES: Tuple[str, ...] = (
    "MANUAL_EXPOSURE",
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P381_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P381_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P381_VALID_ISO_MODES: Tuple[str, ...] = ("ISO_AUTO", "MANUAL_ISO", "CINE_EI_BASE")

# ---------------------------------------------------------------------------
# Wave 83 Group A Constants: Creative Look 10+6 / 354 NVRAM / Drive Mode / Interval
# ---------------------------------------------------------------------------

P381_CREATIVE_LOOK_10_PRESETS: Tuple[str, ...] = (
    "ST",
    "PT",
    "NT",
    "VV",
    "VV2",
    "FL",
    "IN",
    "SH",
    "BW",
    "SE",
)
P381_CREATIVE_LOOK_6_CUSTOM_SLOTS: Tuple[str, ...] = (
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
    "CUSTOM_4",
    "CUSTOM_5",
    "CUSTOM_6",
)
P381_CREATIVE_LOOK_ALL_16_SLOTS: Tuple[str, ...] = (
    P381_CREATIVE_LOOK_10_PRESETS + P381_CREATIVE_LOOK_6_CUSTOM_SLOTS
)
P381_CREATIVE_LOOK_DEFAULT = "ST"
P381_CREATIVE_LOOK_MAIN_NVRAM_KEYS = 2
P381_CREATIVE_LOOK_OPTION_NVRAM_KEYS = 352
P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS = 354
P381_CREATIVE_LOOK_3_TRACKS: Tuple[str, ...] = ("look", "look_still", "look_movie")
P381_CREATIVE_LOOK_SYMMETRIC_MIN = -9
P381_CREATIVE_LOOK_SYMMETRIC_MAX = 9
P381_CREATIVE_LOOK_NONNEG_MIN = 0
P381_CREATIVE_LOOK_NONNEG_MAX = 9
P381_CREATIVE_LOOK_SHARPNESS_RANGE_MIN = 1
P381_CREATIVE_LOOK_SHARPNESS_RANGE_MAX = 5
P381_CREATIVE_LOOK_SATURATION_LOCKED_LOOKS: Tuple[str, ...] = ("BW", "SE")
P381_SOFT_SKIN_FX3_DORMANT_SYMBOLS = 32
P381_FX6_BASE_LOOK_USER_LUT_SLOTS = 16
P381_FX6_BASE_LOOK_CUSTOM_DEFAULT = "S_CINETONE"

P381_STILL_DRIVE_EXACT_8_MODES: Tuple[str, ...] = (
    "SINGLE_SHOOTING",
    "CONT_SHOOTING",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "CONT_BRACKET",
    "SINGLE_BRACKET",
    "WB_BRACKET",
    "DRO_BRACKET",
)
P381_STILL_DRIVE_DEFAULT = "SINGLE_SHOOTING"
P381_CONT_SPEED_TIERS: Tuple[str, ...] = ("HI_PLUS", "HI", "MID", "LO")
P381_CONT_SPEED_FPS_MAP: Mapping[str, int] = {
    "HI_PLUS": 10,
    "HI": 8,
    "MID": 6,
    "LO": 3,
}
P381_CONT_AF_LOCK_F_NUMBER_THRESHOLD = 11.0
P381_CONT_AF_LOCK_TIERS: Tuple[str, ...] = ("HI_PLUS", "HI", "MID")
P381_CFEXPRESS_CEA_G160T_BUFFER_MIN = 1000
P381_DRIVE_MEDIA_BUSES: Tuple[str, ...] = ("CFEXPRESS_TYPE_A_NVME", "SDXC_UHS_II_MMCB")

P381_EV_BRACKET_EXACT_16_COMBOS: Tuple[Tuple[float, int], ...] = (
    (0.3, 3),
    (0.3, 5),
    (0.3, 9),
    (0.5, 3),
    (0.5, 5),
    (0.5, 9),
    (0.7, 3),
    (0.7, 5),
    (0.7, 9),
    (1.0, 3),
    (1.0, 5),
    (1.0, 9),
    (2.0, 3),
    (2.0, 5),
    (3.0, 3),
    (3.0, 5),
)
P381_FX3_DORMANT_FOCUS_BRACKET_SYMBOLS = 129
P381_FX6_DORMANT_FOCUS_BRACKET_SYMBOLS_G151_FULL = 98
P381_INTERVAL_EXACT_7_ITEMS: Tuple[str, ...] = (
    "Interval Shooting",
    "Shooting Start Time",
    "Shooting Interval",
    "Number of Shots",
    "AE Tracking Sensitivity",
    "Shutter Type in Interval",
    "Shoot Interval Priority",
)
P381_INTERVAL_SHUTTER_V702_NAME = "Shutter Type in Interval"
P381_INTERVAL_SHUTTER_TYPES: Tuple[str, ...] = ("ELECTRONIC_SHUTTER", "MECHANICAL_SHUTTER")
P381_INTERVAL_SHUTTER_DEFAULT = "ELECTRONIC_SHUTTER"
P381_FX6_SPECIAL_REC_EXACT_3: Tuple[str, ...] = (
    "S&Q Motion",
    "Interval Rec",
    "Picture Cache Rec",
)

# ---------------------------------------------------------------------------
# Wave 83 Group B Constants: USB-PD 11 PMIC / NP-FZ100 / DC-C1 / Power Save FX3 vs FX3A
# ---------------------------------------------------------------------------

P381_LIBUSBBUSPOWER_EXPECTED_BYTES = 48232
P381_LIBUSBBUSPOWER_EXACT_11_KMODS: Tuple[str, ...] = (
    "usb_bd91407gw.ko",
    "usb_smb232.ko",
    "usb_max14646.ko",
    "usb_max8934.ko",
    "usb_max8976.ko",
    "usb_max16648.ko",
    "usb_max14648.ko",
    "usb_darwin.ko",
    "usb_beets.ko",
    "usbg_buspower.ko",
    "usb_buspwr.ko",
)
P381_NP_FZ100_NOMINAL_VOLTAGE_V = 7.2
P381_USB_POWER_PROFILES: Tuple[str, ...] = (
    "USB_PD_9V_3A_HIGH",
    "USB_PD_9V_2A_MIN",
    "USB_5V_1_5A_LOW",
    "SONY_DC_C1_COUPLER",
    "INTERNAL_NP_FZ100_ONLY",
)
P381_USB_POWER_TERMINALS: Tuple[str, ...] = ("USB_TYPE_C", "MULTI_MICRO_USB")
P381_USB_PD_OFF_CHARGE_TEMP_MIN_C = 10.0
P381_USB_PD_OFF_CHARGE_TEMP_MAX_C = 30.0
P381_USB_PD_OFF_CHARGE_MIN_WATTS = 18.0
P381_DC_C1_MIN_PD_WATTS = 65
P381_DC_C1_MIN_CABLE_AMPS = 5
P381_CPAPP_POWEROFF_SYMBOL = "SequenceAsync_PowerOff"
P381_MEDIA_FLUSH_SYMBOL = "mcmn_drv_writeandflush"
P381_FX6_DC_IN_NOMINAL_V = 19.5
P381_FX6_DC_IN_MIN_V = 18.0
P381_FX6_DC_IN_MAX_V = 20.5

P381_CAMERA_REVISIONS: Tuple[str, ...] = ("ILME_FX3", "ILME_FX3A")
P381_FX3_LCD_DOTS = 1440000
P381_FX3A_LCD_DOTS = 2359296
P381_POWER_SETTING_OPTION_EXACT_2_ITEMS: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
P381_POWER_SAVE_START_TIME_EXACT_6_OPTIONS: Tuple[str, ...] = (
    "OFF",
    "30_MIN",
    "5_MIN",
    "2_MIN",
    "1_MIN",
    "10_SEC",
)
P381_POWER_SAVE_START_TIME_DEFAULT = "5_MIN"
P381_POWER_SAVE_DORMANT_OPTIONS: Tuple[str, ...] = ("20_SEC", "NO_LIMIT")
P381_AUTO_POWER_OFF_TEMP_OPTIONS: Tuple[str, ...] = ("STANDARD", "HIGH")
P381_AUTO_POWER_OFF_TEMP_DEFAULT = "STANDARD"
P381_FX3_POWER_SAVE_EXACT_9_BYPASSES: Tuple[str, ...] = (
    "USB_POWER_FROM_COMPUTER_OR_DEVICE",
    "SLIDESHOW_PLAYBACK",
    "FTP_TRANSFER",
    "MOVIE_RECORDING",
    "CONNECTED_TO_COMPUTER_OR_TV",
    "IR_REMOTE_CTRL_ON",
    "BLUETOOTH_RMT_CTRL_ON",
    "NETWORK_STREAMING",
    "CREATORS_CLOUD_UPLOAD",
)
P381_FX3A_POWER_SAVE_EXACT_8_BYPASSES: Tuple[str, ...] = tuple(
    item for item in P381_FX3_POWER_SAVE_EXACT_9_BYPASSES if item != "IR_REMOTE_CTRL_ON"
)
P381_FX6_WIRED_REMOTE_PORTS: Tuple[str, ...] = ("LANC_2_5MM_3POLE", "GRIP_REMOTE_3_5MM_4POLE")

# ---------------------------------------------------------------------------
# Wave 84 Group C Constants: My Menu 42 / Fn 12+12 / Focus Mode 5-vs-2 / Subj Shift 5
# ---------------------------------------------------------------------------

P381_MY_MENU_EXACT_PAGES = 6
P381_MY_MENU_EXACT_ITEMS_PER_PAGE = 7
P381_MY_MENU_EXACT_TOTAL_SLOTS = 42
P381_MY_MENU_EXACT_6_OPS: Tuple[str, ...] = (
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
P381_DISPLAY_FROM_MY_MENU_DEFAULT = "OFF"
P381_CAMSET_MAX_SLOTS = 10
P381_CAMSET_PATH_TEMPLATE = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
P381_CAMSET_OPERATIONS: Tuple[str, ...] = ("NONE", "LOAD_READONLY", "SAVE", "DELETE")
P381_FN_MENU_STILL_EXACT_SLOTS = 12
P381_FN_MENU_MOVIE_EXACT_SLOTS = 12
P381_FX6_USER_MENU_MAX_ITEMS = 20

P381_STILL_FOCUS_EXACT_5_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")
P381_STILL_FOCUS_DEFAULT = "AF_A"
P381_MOVIE_FOCUS_EXACT_2_MODES: Tuple[str, ...] = ("AF_C", "MF")
P381_MOVIE_FOCUS_DEFAULT = "AF_C"
P381_STILL_AF_TRACK_SENS_MIN = 1
P381_STILL_AF_TRACK_SENS_MAX = 5
P381_STILL_AF_TRACK_SENS_DEFAULT = 3
P381_MOVIE_AF_TRANSITION_SPEED_MIN = 1
P381_MOVIE_AF_TRANSITION_SPEED_MAX = 7
P381_MOVIE_AF_TRANSITION_SPEED_DEFAULT = 5
P381_MOVIE_AF_SUBJ_SHIFT_SENS_MIN = 1
P381_MOVIE_AF_SUBJ_SHIFT_SENS_MAX = 5
P381_MOVIE_AF_SUBJ_SHIFT_SENS_DEFAULT = 5
P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL = "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE"
P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
P381_FOCUS_AREA_LIMIT_MIN_CHECKED_TO_SWITCH = 2
P381_CIRC_OF_FOCUS_POINT_OPTIONS: Tuple[str, ...] = ("DOES_NOT_CIRCULATE", "CIRCULATE")
P381_CIRC_OF_FOCUS_POINT_DEFAULT = "DOES_NOT_CIRCULATE"
P381_CIRC_MOVABLE_AREAS_COUNT = 8
P381_FX6_FACE_EYE_AF_EXACT_3_MODES: Tuple[str, ...] = (
    "FACE_EYE_ONLY_AF",
    "FACE_EYE_PRIORITY_AF",
    "OFF",
)

# ---------------------------------------------------------------------------
# Wave 84 Group D Constants: Exposure Comp / Std Adjust 5 / Spot 8-vs-6 / Playback / Slot 1
# ---------------------------------------------------------------------------

P381_EXP_COMP_STILL_MAX_ABS_EV = 5.0
P381_EXP_COMP_MOVIE_MAX_ABS_EV = 2.0
P381_EXP_STEP_OPTIONS: Tuple[str, ...] = ("0.3EV", "0.5EV")
P381_EXP_STEP_DEFAULT = "0.3EV"
P381_SHUTTER_MODES: Tuple[str, ...] = ("SPEED", "ANGLE")
P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
P381_EXPOSURE_STD_ADJUST_MIN_SIXTHS = -6
P381_EXPOSURE_STD_ADJUST_MAX_SIXTHS = 6
P381_EXPOSURE_STD_ADJUST_EXACT_STEPS = 13
P381_AEL_W_SHUTTER_OPTIONS: Tuple[str, ...] = ("AUTO", "ON", "OFF")
P381_AEL_W_SHUTTER_DEFAULT = "AUTO"
P381_SPOT_METERING_POINT_OPTIONS: Tuple[str, ...] = ("CENTER", "FOCUS_POINT_LINK")
P381_SPOT_METERING_POINT_DEFAULT = "CENTER"
P381_SPOT_METERING_LINKED_EXACT_8_AREAS: Tuple[str, ...] = (
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
)
P381_FX6_AE_LEVEL_MIN_EV = -3.0
P381_FX6_AE_LEVEL_MAX_EV = 3.0
P381_FX6_AE_LEVEL_STEP_EV = 0.25
P381_FX6_AE_LEVEL_EXACT_STEPS = 25
P381_FX6_AGC_LIMIT_MIN_DB = 3
P381_FX6_AGC_LIMIT_MAX_DB = 36
P381_FX6_AGC_LIMIT_STEP_DB = 3
P381_FX6_AGC_ISO_GROUP_COUNT = 12

P381_VIEW_MODE_EXACT_3_STATES: Tuple[str, ...] = (
    "DATE_VIEW",
    "FOLDER_VIEW_STILL",
    "MOVIE_VIEW",
)
P381_VIEW_MODE_DEFAULT = "DATE_VIEW"
P381_DISPLAY_ROTATION_OPTIONS: Tuple[str, ...] = ("AUTO", "MANUAL", "OFF")
P381_DISPLAY_ROTATION_DEFAULT = "AUTO"
P381_DISPLAY_ROTATION_BKID_TYPO = "BKID_APP_setting_display_rotatiton"
P381_IMAGE_INDEX_EXACT_2_OPTIONS: Tuple[str, ...] = ("9_IMAGES", "25_IMAGES")
P381_IMAGE_INDEX_DEFAULT = "9_IMAGES"
P381_DISPLAY_AS_GROUP_DEFAULT = "OFF"
P381_ENLARGE_INITIAL_MAG_OPTIONS: Tuple[str, ...] = ("STANDARD_MAG", "PREVIOUS_MAG")
P381_ENLARGE_INITIAL_MAG_DEFAULT = "STANDARD_MAG"
P381_ENLARGE_INITIAL_POS_OPTIONS: Tuple[str, ...] = ("FOCUSED_POSITION", "CENTER")
P381_ENLARGE_INITIAL_POS_DEFAULT = "FOCUSED_POSITION"
P381_PROTECT_MENU_EXACT_7_ITEMS: Tuple[str, ...] = (
    "Multiple Img.",
    "All in this Folder",
    "Cancel All in this Folder",
    "All with this date",
    "Cancel All with this date",
    "All Images in This Group",
    "Cancel All in This Group",
)
P381_PROTECT_PROXY_SUB_PATTERN = "M4ROOT/SUB/*S03.MP4"
P381_RATING_MIN_STARS = 0
P381_RATING_MAX_STARS = 5
P381_FX6_CLIP_FLAGS: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP")

# ---------------------------------------------------------------------------
# Bounded O_RDONLY | O_NOFOLLOW | O_NONBLOCK Donor Paths (Waves 83-84)
# ---------------------------------------------------------------------------

P381_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    ("fx3_cpapp_b_bin", "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"),
    (
        "fx3_libusbbuspower_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so",
    ),
    (
        "fx3_libinframediacommon_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so",
    ),
    (
        "fx3_seed_bk4_bin",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    ),
    (
        "fx3_string_english_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
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
        "fx6_cpapp_b_bin",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    ),
    (
        "fx6_string_english_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
    ),
    (
        "fx6_string_english_2_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P381_GA_ERR_MODEL_OR_FW_FLOOR = "P381_GA_ERR_MODEL_OR_FW_FLOOR"
P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT = (
    "P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT"
)
P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK = "P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK"
P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16 = "P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16"
P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM = (
    "P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM"
)
P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC = (
    "P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC"
)

P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION = (
    "P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION"
)
P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP = (
    "P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP"
)
P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR = (
    "P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR"
)
P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC = (
    "P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC"
)

P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30 = (
    "P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30"
)
P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU = (
    "P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU"
)
P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE = (
    "P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE"
)
P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF = (
    "P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF"
)

P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116 = (
    "P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116"
)
P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12 = (
    "P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12"
)
P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET = (
    "P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET"
)
P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30 = (
    "P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30"
)
P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL = (
    "P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL"
)
P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

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
# Bounded O_RDONLY | O_NOFOLLOW | O_NONBLOCK Donor Inspection
# ---------------------------------------------------------------------------


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _resolve_work_root_or_none() -> Optional[Path]:
    if _is_clean_room_env():
        return None
    explicit_env = os.environ.get("FX3_FX6_MAC_WORK_ROOT", "").strip()
    if explicit_env:
        cand = Path(os.path.expanduser(explicit_env))
        return cand if cand.exists() else None
    for root in iter_work_roots():
        if root.exists() and (
            (root / "fx3-vm-20261101").exists()
            or (root / "fx3-color-port-20261027").exists()
            or (root / "sony-firmware-20261024").exists()
        ):
            return root
    return None


def resolve_phase381_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    if work_root is None:
        return None
    candidate = Path(work_root) / rel_subpath
    if candidate.exists() and candidate.is_file() and not candidate.is_symlink():
        return candidate
    return None


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P381_HEADER_READ_BYTES) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    fd = os.open(str(path), flags)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase381DonorInspectionResult:
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


def inspect_phase381_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase381DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase381DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P381_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P381_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE381_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    fx3_override_names = {
        "fx3_appfw_so": "appFw.so",
        "fx3_cpapp_b_bin": "cpapp-b.bin",
        "fx3_libusbbuspower_so": "libUsbBusPower.so",
        "fx3_libinframediacommon_so": "libInfraMediaCommon.so",
    }
    for lbl, rel in P381_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            digests[lbl] = hashlib.sha256(f"timeout:{lbl}".encode("utf-8")).hexdigest()[:16]
            continue
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file() and not p.is_symlink():
                candidate = p
        elif lbl in fx3_override_names and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / fx3_override_names[lbl]
            if p.exists() and p.is_file() and not p.is_symlink():
                candidate = p
        if candidate is None:
            candidate = resolve_phase381_donor_file_or_none(resolved_work_root, rel)

        if candidate is not None:
            try:
                hdr = _read_bounded_header_o_rdonly(candidate, P381_HEADER_READ_BYTES)
                present_count += 1
                bytes_read += len(hdr)
                digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]
            except OSError:
                digests[lbl] = hashlib.sha256(f"unreadable:{lbl}".encode("utf-8")).hexdigest()[:16]
        else:
            digests[lbl] = hashlib.sha256(f"missing:{lbl}".encode("utf-8")).hexdigest()[:16]

    mode = "LOCAL_DONOR_O_RDONLY" if present_count > 0 else "CLEAN_ROOM_SYNTHETIC"
    return Phase381DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=present_count > 0,
        donors_checked=len(P381_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE381_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Simulated Dual-Media Tier-0 Receipt Helper (Dry-Run Only)
# ---------------------------------------------------------------------------


def build_simulated_phase381_tier0_receipts(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: str = "FX3SIM70200381",
    emmc_cid: str = "11010030303847333000a1b2c3d49381",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE381_TIER0:{hex(body_model_id)}:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE381_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
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
    open_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)

    if receipt_a_path is not None:
        if not receipt_a_path.exists() or not receipt_a_path.is_file():
            errors.append(
                f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a path missing: {receipt_a_path}"
            )
        else:
            st_dev_a = st_dev_a if st_dev_a is not None else int(os.stat(receipt_a_path).st_dev)
            fd = os.open(str(receipt_a_path), open_flags)
            try:
                raw_a = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if receipt_b_path is not None:
        if not receipt_b_path.exists() or not receipt_b_path.is_file():
            errors.append(
                f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b path missing: {receipt_b_path}"
            )
        else:
            st_dev_b = st_dev_b if st_dev_b is not None else int(os.stat(receipt_b_path).st_dev)
            fd = os.open(str(receipt_b_path), open_flags)
            try:
                raw_b = os.read(fd, SD_RECEIPT_BYTES + 64)
            finally:
                os.close(fd)

    if simulated_h0_h3_drifted_surfaces != 0:
        errors.append(
            f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0 != H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
        )

    if raw_a is None and raw_b is None:
        if simulate_bench_dry_run:
            sim = build_simulated_phase381_tier0_receipts(
                body_serial=body_serial or "FX3SIM70200381",
                emmc_cid=emmc_cid or "11010030303847333000a1b2c3d49381",
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
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528-byte FX3RCPT1 receipts are required"
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
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt size must be {SD_RECEIPT_BYTES} B (got A={len(raw_a)}, B={len(raw_b)})"
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
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B FX3RCPT1 payloads differ"
        )

    if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B must reside on distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
        )

    try:
        parsed_a = parse_sd_backup_receipt_bytes(raw_a)
        parsed_b = parse_sd_backup_receipt_bytes(raw_b)
    except Exception as exc:
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
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
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 integrity failure ({'; '.join(errs_ab)})"
        )
    if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))) or _is_trivial_hex64(
        str(getattr(parsed_b, "manifest_sha256", ""))
    ):
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: trivial manifest_sha256 in FX3RCPT1"
        )
    if getattr(parsed_a, "entry_count", 0) != len(COLD_BACKUP_ITEMS) or getattr(
        parsed_b, "entry_count", 0
    ) != len(COLD_BACKUP_ITEMS):
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: cold backup item count mismatch ({getattr(parsed_a, 'entry_count', 0)} != {len(COLD_BACKUP_ITEMS)})"
        )

    eff_serial = body_serial if body_serial is not None else ""
    eff_cid = emmc_cid if emmc_cid is not None else ""
    if eff_serial:
        if (
            eff_serial.upper() in FORBIDDEN_TRIVIAL_SERIALS
            or len(set(eff_serial.upper())) == 1
            or not BODY_SERIAL_RE.match(eff_serial)
        ):
            errors.append(
                f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial body_serial {eff_serial!r}"
            )
    else:
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial body_serial required for receipt binding"
        )

    if eff_cid:
        if eff_cid.lower() in FORBIDDEN_TRIVIAL_CIDS or not HEX32_CID_RE.match(eff_cid):
            errors.append(
                f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial emmc_cid {eff_cid!r}"
            )
    else:
        errors.append(
            f"{P381_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: non-trivial 32-hex emmc_cid required for receipt binding"
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
                f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_a keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h0_b_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h0_baselines_b keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif set(h3_map.keys()) != set(REQUIRED_H0_BASELINE_KEYS):
            errors.append(
                f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: h3_baselines keys must match {len(REQUIRED_H0_BASELINE_KEYS)} REQUIRED_H0_BASELINE_KEYS"
            )
        elif len(SIXTEEN_STORAGE_SURFACES) != P381_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: expected 16 storage surfaces, got {len(SIXTEEN_STORAGE_SURFACES)}"
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
                    f"{P381_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 != H3 or trivial digest detected ({drifted} drifted)"
                )
            h0_match = max(0, P381_STORAGE_SURFACE_COUNT - drifted)

    verified = (
        len(errors) == 0
        and h0_match == P381_STORAGE_SURFACE_COUNT
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
class P381CheckGroupACreativeLookSoftSkinDriveF11FocusBracketIntervalResult:
    group_id: str
    passed: bool
    shoot_mode: str
    exposure_mode: str
    log_shooting_mode: str
    picture_profile: str
    hlg_still_image: str
    reset_action: str
    creative_look_slot: str
    creative_look_nvram_total_keys: int
    creative_look_locked_to_dash: bool
    effective_creative_look: str
    effective_creative_look_after_reset: str
    creative_look_contrast: int
    creative_look_highlights: int
    creative_look_shadows: int
    creative_look_fade: int
    creative_look_saturation: int
    creative_look_sharpness: int
    creative_look_sharpness_range: int
    creative_look_clarity: int
    fx3_soft_skin_effect_supported: bool
    fx6_base_look_user_lut_slots: int
    still_drive_mode: str
    effective_still_drive_mode_after_reset: str
    cont_speed_tier: str
    cont_speed_max_fps: int
    cont_live_view_active: bool
    aperture_f_number: float
    cont_af_locked_first_frame: bool
    drive_media_bus: str
    cfexpress_buffer_min_images: int
    ev_bracket_step_ev: float
    ev_bracket_shot_count: int
    ev_bracket_combo_count: int
    fx3_focus_bracket_supported: bool
    fx3_dormant_focus_bracket_symbols: int
    fx6_dormant_focus_bracket_symbols_g151_full: int
    interval_items_exposed: Tuple[str, ...]
    interval_shutter_type: str
    effective_interval_shutter_after_reset: str
    interval_in_camera_movie_synthesis: bool
    fx6_special_rec_modes: Tuple[str, ...]
    fx6_frame_rec_supported: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P381CheckGroupBUsbPdPmicPowerSaveFx3VsFx3aRemotesResult:
    group_id: str
    passed: bool
    camera_revision: str
    reset_action: str
    libusbbuspower_bytes: int
    pmic_kmods_exposed: Tuple[str, ...]
    usb_power_supply: str
    effective_usb_power_supply_after_reset: str
    usb_power_profile: str
    usb_power_terminal: str
    np_fz100_inserted: bool
    dc_c1_pd_watts: int
    dc_c1_cable_amps: int
    on_state_charging_possible: bool
    off_state_charging_active: bool
    ambient_temp_c: float
    power_loss_hotpull_blocked: bool
    fx6_dc_in_voltage_v: float
    fx6_batteryless_boot_supported: bool
    fx6_usbc_power_supply_supported: bool
    power_setting_option_items: Tuple[str, ...]
    power_save_start_time: str
    effective_power_save_start_time_after_reset: str
    auto_power_off_temp: str
    effective_auto_power_off_temp_after_reset: str
    power_save_bypass_count: int
    fx3_power_save_by_monitor_supported: bool
    ir_receiver_present: bool
    nfc_present: bool
    ir_remote_ctrl: str
    bluetooth_rmt_ctrl: str
    usb_lan_cnct_launch: str
    effective_usb_lan_cnct_launch_after_reset: str
    fx6_wired_remote_ports: Tuple[str, ...]
    fx6_ble_or_ir_remote_supported: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P381CheckGroupCMyMenu42Fn12FocusModeSubjShift5FocusLimit14Result:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    my_menu_pages: int
    my_menu_items_per_page: int
    my_menu_total_slots: int
    my_menu_ops_exposed: Tuple[str, ...]
    display_from_my_menu: str
    effective_display_from_my_menu_after_reset: str
    camset_operation: str
    camset_target_slot: int
    camset_slot1_write_blocked_erofs30: bool
    fn_menu_still_slots: int
    fn_menu_movie_slots: int
    fn_menu_active_slots: int
    fx3_fn_menu_follow_custom_supported: bool
    xlr_h1_has_fn_menu_or_rec_keys: bool
    fx6_user_menu_max_items: int
    fx6_user_menu_lock_excluded_from_all_file: bool
    focus_mode: str
    effective_focus_mode_after_reset: str
    af_w_shutter: str
    effective_af_w_shutter_after_reset: str
    pre_af: str
    effective_pre_af_after_reset: str
    still_af_tracking_sensitivity: int
    effective_still_af_tracking_sens_after_reset: int
    movie_af_transition_speed: int
    effective_movie_af_transition_speed_after_reset: int
    movie_af_subj_shift_sensitivity: int
    effective_movie_af_subj_shift_sens_after_reset: int
    movie_af_subj_shift_responsice_symbol: str
    focus_area_limit_items_exposed: Tuple[str, ...]
    focus_area_limit_checked_count: int
    circ_of_focus_point: str
    effective_circ_of_focus_point_after_reset: str
    circ_movable_areas_count: int
    fx6_face_eye_af_mode: str
    slot1_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P381CheckGroupDExpCompExpStd5Spot8Vs6PlaybackSlot1ZeroRfTier0Result:
    group_id: str
    passed: bool
    shoot_mode: str
    exposure_mode: str
    iso_mode: str
    log_shooting_mode: str
    reset_action: str
    exposure_comp_ev: float
    exposure_comp_locked: bool
    effective_exposure_comp_after_reset: float
    exposure_step: str
    effective_exposure_step_after_reset: str
    shutter_mode: str
    exposure_std_adjust_modes_exposed: Tuple[str, ...]
    exposure_std_adjust_mode: str
    exposure_std_adjust_sixths: int
    effective_exposure_std_adjust_sixths_after_reset: int
    ael_w_shutter: str
    effective_ael_w_shutter_after_reset: str
    spot_metering_point: str
    spot_metering_focus_area: str
    spot_metering_linked_areas: Tuple[str, ...]
    spot_metering_center_locked_areas: Tuple[str, ...]
    spot_metering_linked_active: bool
    fx6_ae_level_ev: float
    fx6_ae_shift_menu_supported: bool
    fx6_agc_limit_db: int
    fx6_agc_iso_groups: int
    view_mode: str
    view_mode_options_exposed: Tuple[str, ...]
    effective_view_mode_after_reset: str
    display_rotation: str
    effective_display_rotation_after_reset: str
    display_rotation_bkid_typo: str
    image_index: str
    effective_image_index_after_reset: str
    display_as_group: str
    effective_display_as_group_after_reset: str
    enlarge_initial_mag: str
    effective_enlarge_initial_mag_after_reset: str
    enlarge_initial_position: str
    effective_enlarge_initial_position_after_reset: str
    protect_menu_items_exposed: Tuple[str, ...]
    protect_write_requested: bool
    protect_syncs_proxy_pattern: str
    rating_write_requested: bool
    rating_stars: int
    playback_target_slot: int
    slot1_playback_write_blocked_erofs30: bool
    airplane_mode: str
    cnct_while_power_off: str
    select_on_cam_and_send_requested: bool
    select_on_cam_and_send_blocked_zero_rf: bool
    fx6_clip_flag: str
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_sector_writes: int
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
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
class Phase381ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P381CheckGroupACreativeLookSoftSkinDriveF11FocusBracketIntervalResult
    check_group_b: P381CheckGroupBUsbPdPmicPowerSaveFx3VsFx3aRemotesResult
    check_group_c: P381CheckGroupCMyMenu42Fn12FocusModeSubjShift5FocusLimit14Result
    check_group_d: P381CheckGroupDExpCompExpStd5Spot8Vs6PlaybackSlot1ZeroRfTier0Result
    donor_inspection: Phase381DonorInspectionResult
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
    fx3_soft_skin_effect_supported: bool
    fx3_focus_bracket_supported: bool
    fx6_frame_rec_supported: bool
    fx3_power_save_by_monitor_supported: bool
    fx3a_ir_or_nfc_supported: bool
    fx3_fn_menu_follow_custom_supported: bool
    fx6_ae_shift_menu_supported: bool
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
            "fx3_soft_skin_effect_supported": self.fx3_soft_skin_effect_supported,
            "fx3_focus_bracket_supported": self.fx3_focus_bracket_supported,
            "fx6_frame_rec_supported": self.fx6_frame_rec_supported,
            "fx3_power_save_by_monitor_supported": self.fx3_power_save_by_monitor_supported,
            "fx3a_ir_or_nfc_supported": self.fx3a_ir_or_nfc_supported,
            "fx3_fn_menu_follow_custom_supported": self.fx3_fn_menu_follow_custom_supported,
            "fx6_ae_shift_menu_supported": self.fx6_ae_shift_menu_supported,
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
# Helpers
# ---------------------------------------------------------------------------


def _parse_fw_tuple(fw: str) -> Optional[Tuple[int, int]]:
    parts = fw.strip().split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 83.1-83.2)
# ---------------------------------------------------------------------------


def evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P381_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "MANUAL_EXPOSURE",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "PP11",
    hlg_still_image: str = "OFF",
    reset_action: str = "NONE",
    # Creative Look 10+6 / 354 NVRAM / Asymmetric 8 Params / Dormant Soft Skin
    creative_look_slot: str = P381_CREATIVE_LOOK_DEFAULT,
    creative_look_nvram_total_keys: int = P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS,
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
    expect_creative_look_active_under_lockout: bool = False,
    claimed_creative_look_fade_sharpness_clarity_accept_negative: bool = False,
    claimed_creative_look_resists_camera_reset: bool = False,
    dormant_soft_skin_effect_requested: bool = False,
    claimed_fx3_or_fx6_has_soft_skin_effect: bool = False,
    fx6_base_look_user_lut_slots: int = P381_FX6_BASE_LOOK_USER_LUT_SLOTS,
    claimed_fx6_has_creative_look_menu: bool = False,
    # Still Drive Mode / > F11 AF Lock / 16 EV Brackets / Dormant Focus Bracket / Interval
    still_drive_mode: str = P381_STILL_DRIVE_DEFAULT,
    still_drive_modes_exposed: Tuple[str, ...] = P381_STILL_DRIVE_EXACT_8_MODES,
    cont_speed_tier: str = "HI_PLUS",
    aperture_f_number: float = 2.8,
    expect_hi_plus_live_view: bool = False,
    expect_af_tracks_all_frames_above_f11: bool = False,
    claimed_af_lock_threshold_is_f8: bool = False,
    claimed_drive_mode_resists_camera_reset: bool = False,
    drive_media_bus: str = "CFEXPRESS_TYPE_A_NVME",
    cfexpress_buffer_min_images: int = P381_CFEXPRESS_CEA_G160T_BUFFER_MIN,
    ev_bracket_step_ev: float = 0.7,
    ev_bracket_shot_count: int = 3,
    ev_bracket_combos_exposed: Tuple[Tuple[float, int], ...] = P381_EV_BRACKET_EXACT_16_COMBOS,
    dormant_focus_bracket_requested: bool = False,
    claimed_fx3_or_fx6_exposes_focus_bracket: bool = False,
    claimed_g151_fx6_focus_bracket_full_scan_is_56: bool = False,
    interval_items_exposed: Tuple[str, ...] = P381_INTERVAL_EXACT_7_ITEMS,
    interval_shutter_type: str = P381_INTERVAL_SHUTTER_DEFAULT,
    claimed_interval_shutter_name_is_legacy_silent_shoot: bool = False,
    claimed_interval_resists_camera_reset: bool = False,
    claimed_interval_in_camera_movie_synthesis: bool = False,
    fx6_special_rec_modes: Tuple[str, ...] = P381_FX6_SPECIAL_REC_EXACT_3,
    dormant_fx6_frame_rec_requested: bool = False,
    claimed_fx6_has_frame_rec: bool = False,
) -> P381CheckGroupACreativeLookSoftSkinDriveF11FocusBracketIntervalResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX}, got 0x{body_model_id:08x}"
        )
    fw_t = _parse_fw_tuple(body_fw)
    if fw_t is None or fw_t < (7, 2):
        errors.append(
            f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: body_fw must be >= {TARGET_BODY_FW}, got {body_fw!r}"
        )
    if sony_help_guide_id != P381_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P381_SONY_HELP_GUIDE_ID}, got {sony_help_guide_id!r}"
        )
    if shoot_mode not in P381_VALID_SHOOT_MODES:
        errors.append(f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode {shoot_mode!r}")
    if exposure_mode not in P381_VALID_EXPOSURE_MODES:
        errors.append(f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: invalid exposure_mode {exposure_mode!r}")
    if log_shooting_mode not in P381_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if hlg_still_image not in P381_VALID_ON_OFF:
        errors.append(f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: invalid hlg_still_image {hlg_still_image!r}")
    if reset_action not in P381_VALID_RESET_ACTIONS:
        errors.append(f"{P381_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action {reset_action!r}")

    # Creative Look 10+6 / 354 NVRAM / Asymmetric 8 Params / 4 Hard Lockouts
    if creative_look_slot not in P381_CREATIVE_LOOK_ALL_16_SLOTS:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: invalid creative_look_slot {creative_look_slot!r}"
        )
    if creative_look_nvram_total_keys != P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: [Creative Look] NVRAM layout is exact {P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS} keys (2 main + 352 option keys), got {creative_look_nvram_total_keys}"
        )
    for name, val in (
        ("Contrast", creative_look_contrast),
        ("Highlights", creative_look_highlights),
        ("Shadows", creative_look_shadows),
        ("Saturation", creative_look_saturation),
    ):
        if not (P381_CREATIVE_LOOK_SYMMETRIC_MIN <= val <= P381_CREATIVE_LOOK_SYMMETRIC_MAX):
            errors.append(
                f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: {name} must be -9..+9, got {val}"
            )
    for name, val in (
        ("Fade", creative_look_fade),
        ("Sharpness", creative_look_sharpness),
        ("Clarity", creative_look_clarity),
    ):
        if not (P381_CREATIVE_LOOK_NONNEG_MIN <= val <= P381_CREATIVE_LOOK_NONNEG_MAX):
            errors.append(
                f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: {name} is asymmetric non-negative 0..9 (no negative values), got {val}"
            )
    if not (
        P381_CREATIVE_LOOK_SHARPNESS_RANGE_MIN
        <= creative_look_sharpness_range
        <= P381_CREATIVE_LOOK_SHARPNESS_RANGE_MAX
    ):
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: Sharpness Range (fineness) must be 1..5, got {creative_look_sharpness_range}"
        )
    if claimed_creative_look_fade_sharpness_clarity_accept_negative:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: Fade/Sharpness/Clarity are strictly 0..9 (non-negative)"
        )
    if creative_look_slot in P381_CREATIVE_LOOK_SATURATION_LOCKED_LOOKS and (
        creative_look_saturation_adjusted or creative_look_saturation != 0
    ):
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: Saturation is locked in {creative_look_slot}"
        )
    if shoot_mode in ("MOVIE", "S_AND_Q") and creative_look_sharpness_range_adjusted:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: Sharpness Range (fineness) is locked in Movie and S&Q modes"
        )
    cl_locked = (
        picture_profile != "OFF"
        or log_shooting_mode != "OFF"
        or hlg_still_image == "ON"
        or exposure_mode == "INTELLIGENT_AUTO"
    )
    if cl_locked and expect_creative_look_active_under_lockout:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: [Creative Look] is hard-locked to [-] under PP!=Off (stock PP11), Log!=Off, HLG Still=On, or Intelligent Auto"
        )
    if claimed_creative_look_resists_camera_reset:
        errors.append(
            f"{P381_GA_ERR_CREATIVE_LOOK_354NVRAM_BOUNDS_OR_LOCKOUT}: [Creative Look] is Can be reset under [Camera Settings Reset] (resets to ST)"
        )

    # Dormant [Soft Skin Effect] & FX6 Base Look Contrast
    if dormant_soft_skin_effect_requested or claimed_fx3_or_fx6_has_soft_skin_effect:
        errors.append(
            f"{P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK}: [Soft Skin Effect] is 100%% dormant on FX3/FX3A/FX6 (0 Help Guide hits, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )
    if fx6_base_look_user_lut_slots != P381_FX6_BASE_LOOK_USER_LUT_SLOTS or claimed_fx6_has_creative_look_menu:
        errors.append(
            f"{P381_GA_ERR_SOFT_SKIN_DORMANT_OR_FX6_BASE_LOOK}: FX6 has zero [Creative Look]; uses Paint/Look > Base Look + User 1..{P381_FX6_BASE_LOOK_USER_LUT_SLOTS}"
        )

    # Still [Drive Mode], > F11 AF Lock, CFexpress Buffer, 16 EV Brackets
    if tuple(still_drive_modes_exposed) != P381_STILL_DRIVE_EXACT_8_MODES:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: Still [Drive Mode] must expose exact 8 modes {P381_STILL_DRIVE_EXACT_8_MODES}"
        )
    if still_drive_mode not in P381_STILL_DRIVE_EXACT_8_MODES:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: invalid still_drive_mode {still_drive_mode!r}"
        )
    if cont_speed_tier not in P381_CONT_SPEED_TIERS:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: invalid cont_speed_tier {cont_speed_tier!r}"
        )
    cont_max_fps = P381_CONT_SPEED_FPS_MAP.get(cont_speed_tier, 0)
    cont_live_view_active = cont_speed_tier != "HI_PLUS"
    if cont_speed_tier == "HI_PLUS" and expect_hi_plus_live_view:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: Cont. Shooting Hi+ (10 fps) has zero live-view (post-view only)"
        )
    if aperture_f_number <= 0.0:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: invalid aperture_f_number {aperture_f_number}"
        )
    af_locked_first_frame = (
        cont_speed_tier in P381_CONT_AF_LOCK_TIERS
        and aperture_f_number > P381_CONT_AF_LOCK_F_NUMBER_THRESHOLD
    )
    if af_locked_first_frame and expect_af_tracks_all_frames_above_f11:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: AF locks on frame 1 at > F11 in Hi+/Hi/Mid (got F{aperture_f_number} in {cont_speed_tier})"
        )
    if claimed_af_lock_threshold_is_f8:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: Cont. Shooting AF lock threshold is > F11 (NOT F8!) per ilc/2210 TP1000867608"
        )
    if claimed_drive_mode_resists_camera_reset:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: [Drive Mode] is Can be reset under [Camera Settings Reset] (resets to Single Shooting)"
        )
    if drive_media_bus not in P381_DRIVE_MEDIA_BUSES:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: invalid drive_media_bus {drive_media_bus!r}"
        )
    if drive_media_bus == "CFEXPRESS_TYPE_A_NVME" and cfexpress_buffer_min_images < P381_CFEXPRESS_CEA_G160T_BUFFER_MIN:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: CFexpress Type A CEA-G160T buffer rating is >= {P381_CFEXPRESS_CEA_G160T_BUFFER_MIN} images"
        )
    if tuple(ev_bracket_combos_exposed) != P381_EV_BRACKET_EXACT_16_COMBOS:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: EV bracket table must expose exact 16 combos (zero 9 Image for 2.0/3.0 EV)"
        )
    if (round(float(ev_bracket_step_ev), 1), int(ev_bracket_shot_count)) not in P381_EV_BRACKET_EXACT_16_COMBOS:
        errors.append(
            f"{P381_GA_ERR_DRIVE_MODE_F11_OR_EV_BRACKET_16}: invalid EV bracket combo ({ev_bracket_step_ev} EV, {ev_bracket_shot_count} shots); 2.0/3.0 EV only allow 3/5 shots"
        )

    # Dormant [Focus Bracket] & Wave 83 G151 Erratum (56 vs 98)
    if dormant_focus_bracket_requested or claimed_fx3_or_fx6_exposes_focus_bracket:
        errors.append(
            f"{P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM}: [Focus Bracket] is 100%% dormant on FX3/FX6 (0 ilc/2210 hits, 129 FX3 / 98 FX6 dormant symbols, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )
    if claimed_g151_fx6_focus_bracket_full_scan_is_56:
        errors.append(
            f"{P381_GA_ERR_FOCUS_BRACKET_DORMANT_OR_G151_ERRATUM}: Wave 83 G151 erratum: full case-insensitive scan of FX6 appFw.so yields {P381_FX6_DORMANT_FOCUS_BRACKET_SYMBOLS_G151_FULL} dormant focus_bracket symbols (not 56)"
        )

    # [Interval Shoot Func.] 7 Items + Ver. 7.02 Name + FX6 Zero Frame Rec
    if tuple(interval_items_exposed) != P381_INTERVAL_EXACT_7_ITEMS:
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: [Interval Shoot Func.] must expose exact 7 items {P381_INTERVAL_EXACT_7_ITEMS}"
        )
    if interval_shutter_type not in P381_INTERVAL_SHUTTER_TYPES:
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: invalid interval_shutter_type {interval_shutter_type!r}"
        )
    if claimed_interval_shutter_name_is_legacy_silent_shoot:
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: Ver. 7.02 renamed [Silent Shoot. in Interval] to [{P381_INTERVAL_SHUTTER_V702_NAME}] (default Electronic Shutter)"
        )
    if claimed_interval_resists_camera_reset:
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: ALL 7 [Interval Shoot Func.] items are Can be reset under [Camera Settings Reset]"
        )
    if claimed_interval_in_camera_movie_synthesis:
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: FX3 [Interval Shoot Func.] outputs still sequences only (zero in-camera movie synthesis)"
        )
    if (
        tuple(fx6_special_rec_modes) != P381_FX6_SPECIAL_REC_EXACT_3
        or dormant_fx6_frame_rec_requested
        or claimed_fx6_has_frame_rec
    ):
        errors.append(
            f"{P381_GA_ERR_INTERVAL_7ITEM_V702_OR_FX6_ZERO_FRAME_REC}: FX6 Ver. 6.01 supports only {P381_FX6_SPECIAL_REC_EXACT_3} and has ZERO Frame Rec (0 ELF/UXC hits, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )

    eff_cl = "-" if cl_locked else creative_look_slot
    eff_cl_after_reset = (
        P381_CREATIVE_LOOK_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else eff_cl
    )
    eff_drive_after_reset = (
        P381_STILL_DRIVE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else still_drive_mode
    )
    eff_interval_shutter_after_reset = (
        P381_INTERVAL_SHUTTER_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else interval_shutter_type
    )

    return P381CheckGroupACreativeLookSoftSkinDriveF11FocusBracketIntervalResult(
        group_id=P381_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hlg_still_image=hlg_still_image,
        reset_action=reset_action,
        creative_look_slot=creative_look_slot,
        creative_look_nvram_total_keys=creative_look_nvram_total_keys,
        creative_look_locked_to_dash=cl_locked,
        effective_creative_look=eff_cl,
        effective_creative_look_after_reset=eff_cl_after_reset,
        creative_look_contrast=creative_look_contrast,
        creative_look_highlights=creative_look_highlights,
        creative_look_shadows=creative_look_shadows,
        creative_look_fade=creative_look_fade,
        creative_look_saturation=creative_look_saturation,
        creative_look_sharpness=creative_look_sharpness,
        creative_look_sharpness_range=creative_look_sharpness_range,
        creative_look_clarity=creative_look_clarity,
        fx3_soft_skin_effect_supported=False,
        fx6_base_look_user_lut_slots=fx6_base_look_user_lut_slots,
        still_drive_mode=still_drive_mode,
        effective_still_drive_mode_after_reset=eff_drive_after_reset,
        cont_speed_tier=cont_speed_tier,
        cont_speed_max_fps=cont_max_fps,
        cont_live_view_active=cont_live_view_active,
        aperture_f_number=aperture_f_number,
        cont_af_locked_first_frame=af_locked_first_frame,
        drive_media_bus=drive_media_bus,
        cfexpress_buffer_min_images=cfexpress_buffer_min_images,
        ev_bracket_step_ev=ev_bracket_step_ev,
        ev_bracket_shot_count=ev_bracket_shot_count,
        ev_bracket_combo_count=len(ev_bracket_combos_exposed),
        fx3_focus_bracket_supported=False,
        fx3_dormant_focus_bracket_symbols=P381_FX3_DORMANT_FOCUS_BRACKET_SYMBOLS,
        fx6_dormant_focus_bracket_symbols_g151_full=P381_FX6_DORMANT_FOCUS_BRACKET_SYMBOLS_G151_FULL,
        interval_items_exposed=tuple(interval_items_exposed),
        interval_shutter_type=interval_shutter_type,
        effective_interval_shutter_after_reset=eff_interval_shutter_after_reset,
        interval_in_camera_movie_synthesis=False,
        fx6_special_rec_modes=tuple(fx6_special_rec_modes),
        fx6_frame_rec_supported=False,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 83.3-83.4)
# ---------------------------------------------------------------------------


def evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
    *,
    camera_revision: str = "ILME_FX3",
    reset_action: str = "NONE",
    # USB Power Supply / libUsbBusPower.so 11 PMIC / NP-FZ100 / DC-C1 / Power-Loss Redline
    libusbbuspower_bytes: int = P381_LIBUSBBUSPOWER_EXPECTED_BYTES,
    pmic_kmods_exposed: Tuple[str, ...] = P381_LIBUSBBUSPOWER_EXACT_11_KMODS,
    usb_power_supply: str = "ON",
    usb_power_profile: str = "USB_PD_9V_3A_HIGH",
    usb_power_terminal: str = "USB_TYPE_C",
    np_fz100_inserted: bool = True,
    dc_c1_pd_watts: int = 65,
    dc_c1_cable_amps: int = 5,
    expect_on_state_battery_charging: bool = False,
    off_state_charging_active: bool = False,
    off_charge_pd_watts: float = 18.0,
    ambient_temp_c: float = 22.0,
    expect_5v_1_5a_sustains_4k_recording: bool = False,
    hot_pull_np_fz100_requested: bool = False,
    claimed_hot_pull_runs_poweroff_and_fsync: bool = False,
    claimed_usb_power_supply_wiped_by_camera_reset: bool = False,
    fx6_dc_in_voltage_v: float = P381_FX6_DC_IN_NOMINAL_V,
    fx6_hot_replug_dc_in_during_rec: bool = False,
    claimed_fx6_supports_usbc_power_supply: bool = False,
    # Power Setting Option Exact 2 Items / FX3 9 vs FX3A 8 Bypasses / IR & NFC Removal / FX6 LANC
    power_setting_option_items: Tuple[str, ...] = P381_POWER_SETTING_OPTION_EXACT_2_ITEMS,
    power_save_start_time: str = P381_POWER_SAVE_START_TIME_DEFAULT,
    dormant_power_save_time_requested: Optional[str] = None,
    auto_power_off_temp: str = P381_AUTO_POWER_OFF_TEMP_DEFAULT,
    handheld_bare_skin_operation: bool = False,
    expect_high_temp_safe_handheld: bool = False,
    power_save_bypasses_exposed: Optional[Tuple[str, ...]] = None,
    claimed_power_setting_option_wiped_by_camera_reset: bool = False,
    dormant_power_save_by_monitor_requested: bool = False,
    ir_remote_ctrl: str = "OFF",
    bluetooth_rmt_ctrl: str = "OFF",
    nfc_requested: bool = False,
    claimed_fx3a_has_ir_or_nfc: bool = False,
    usb_lan_cnct_launch: str = "OFF",
    fx6_wired_remote_ports: Tuple[str, ...] = P381_FX6_WIRED_REMOTE_PORTS,
    claimed_fx6_has_ble_or_ir_remote: bool = False,
) -> P381CheckGroupBUsbPdPmicPowerSaveFx3VsFx3aRemotesResult:
    errors: List[str] = []
    warnings: List[str] = []

    if camera_revision not in P381_CAMERA_REVISIONS:
        errors.append(
            f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: invalid camera_revision {camera_revision!r}"
        )
    if reset_action not in P381_VALID_RESET_ACTIONS:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: invalid reset_action {reset_action!r}"
        )

    # libUsbBusPower.so 11 PMIC / NP-FZ100 / USB-PD / DC-C1
    if libusbbuspower_bytes != P381_LIBUSBBUSPOWER_EXPECTED_BYTES:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: libUsbBusPower.so expected {P381_LIBUSBBUSPOWER_EXPECTED_BYTES} B, got {libusbbuspower_bytes} B"
        )
    if tuple(pmic_kmods_exposed) != P381_LIBUSBBUSPOWER_EXACT_11_KMODS:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: libUsbBusPower.so must declare exact 11 PMIC/charger .ko drivers"
        )
    if usb_power_supply not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: invalid usb_power_supply {usb_power_supply!r}"
        )
    if usb_power_profile not in P381_USB_POWER_PROFILES:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: invalid usb_power_profile {usb_power_profile!r}"
        )
    if usb_power_terminal != "USB_TYPE_C":
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: USB Power Supply is USB Type-C only (Multi/Micro USB forbidden: {usb_power_terminal!r})"
        )
    if usb_power_profile != "SONY_DC_C1_COUPLER" and not np_fz100_inserted:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: mandatory in-slot NP-FZ100 (7.2 V) required by libUsbBusPower.so GetCurrentBattState/IsSinkReady"
        )
    if usb_power_profile == "SONY_DC_C1_COUPLER":
        if dc_c1_pd_watts < P381_DC_C1_MIN_PD_WATTS or dc_c1_cable_amps < P381_DC_C1_MIN_CABLE_AMPS:
            errors.append(
                f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: Sony DC-C1 requires >= {P381_DC_C1_MIN_PD_WATTS} W USB-PD and >= {P381_DC_C1_MIN_CABLE_AMPS}A cable (got {dc_c1_pd_watts}W / {dc_c1_cable_amps}A)"
            )
    if usb_power_profile == "USB_5V_1_5A_LOW":
        warnings.append(
            "USB 5V/1.5A (7.5 W, LOW) drains NP-FZ100 during 4K recording (>7.3 W); use USB-PD 9V/3A HIGH."
        )
        if expect_5v_1_5a_sustains_4k_recording:
            errors.append(
                f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: 5V/1.5A LOW cannot sustain 4K recording without battery drain"
            )
    if expect_on_state_battery_charging:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: FX3 performs zero ON-state battery charging (CHARGE LED off; SetChargingDisable)"
        )
    if off_state_charging_active:
        if not (P381_USB_PD_OFF_CHARGE_TEMP_MIN_C <= ambient_temp_c <= P381_USB_PD_OFF_CHARGE_TEMP_MAX_C):
            errors.append(
                f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: OFF-state charging requires 10-30 C window, got {ambient_temp_c} C"
            )
        if off_charge_pd_watts < P381_USB_PD_OFF_CHARGE_MIN_WATTS:
            errors.append(
                f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: OFF-state fast charging requires >= 9V/2A (18 W) USB-PD, got {off_charge_pd_watts} W"
            )
    if claimed_usb_power_supply_wiped_by_camera_reset:
        errors.append(
            f"{P381_GB_ERR_USBPD_11PMIC_NPFZ100_OR_DCC1_VIOLATION}: [USB Power Supply] resists [Camera Settings Reset] (Initialize-only)"
        )

    # Power-Loss Hot-Pull Redline & FX6 19.5V DC IN Contrast
    if hot_pull_np_fz100_requested or claimed_hot_pull_runs_poweroff_and_fsync:
        errors.append(
            f"{P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP}: hot-pulling NP-FZ100 cuts SYS rail bypassing cpapp-b.bin {P381_CPAPP_POWEROFF_SYMBOL} and libInfraMediaCommon.so {P381_MEDIA_FLUSH_SYMBOL}/fsync (Tier-0 power-loss redline)"
        )
    if not (P381_FX6_DC_IN_MIN_V <= fx6_dc_in_voltage_v <= P381_FX6_DC_IN_MAX_V):
        errors.append(
            f"{P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP}: FX6 19.5V EIAJ DC IN operating window is 18.0-20.5 V, got {fx6_dc_in_voltage_v} V"
        )
    if fx6_hot_replug_dc_in_during_rec:
        errors.append(
            f"{P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP}: FX6 hot-replugging DC IN during live recording risks transient voltage-drop reboot trap"
        )
    if claimed_fx6_supports_usbc_power_supply:
        errors.append(
            f"{P381_GB_ERR_POWER_LOSS_HOTPULL_OR_FX6_DCIN_TRAP}: FX6 USB-C has zero power supply support (sequence_set_usb_power_supply dormant, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )

    # [Power Setting Option] Exact 2 Items, FX3 9 vs FX3A 8 Bypasses & Dormant Power Save by Monitor
    if tuple(power_setting_option_items) != P381_POWER_SETTING_OPTION_EXACT_2_ITEMS:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: [Power Setting Option] must expose exact 2 items {P381_POWER_SETTING_OPTION_EXACT_2_ITEMS}"
        )
    if power_save_start_time not in P381_POWER_SAVE_START_TIME_EXACT_6_OPTIONS:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: invalid power_save_start_time {power_save_start_time!r}"
        )
    if dormant_power_save_time_requested is not None:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: dormant Power Save Start Time {dormant_power_save_time_requested!r} (20SEC/NO_LIMIT) blocked EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP}"
        )
    if auto_power_off_temp not in P381_AUTO_POWER_OFF_TEMP_OPTIONS:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: invalid auto_power_off_temp {auto_power_off_temp!r}"
        )
    if auto_power_off_temp == "HIGH" and handheld_bare_skin_operation:
        warnings.append(
            "[Auto Power OFF Temp.]=High is tripod-only; sustained handheld operation risks low-temperature burns."
        )
        if expect_high_temp_safe_handheld:
            errors.append(
                f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: [Auto Power OFF Temp.]=High is tripod-only (handheld burn hazard)"
            )
    if claimed_power_setting_option_wiped_by_camera_reset:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: [Power Save Start Time] and [Auto Power OFF Temp.] resist [Camera Settings Reset]"
        )
    if dormant_power_save_by_monitor_requested:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: [Power Save by Monitor] (BKID_APP_setting_monitor_power_linkage) is 100%% dormant on FX3/FX3A (EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )

    expected_bypasses = (
        P381_FX3_POWER_SAVE_EXACT_9_BYPASSES
        if camera_revision == "ILME_FX3"
        else P381_FX3A_POWER_SAVE_EXACT_8_BYPASSES
    )
    actual_bypasses = (
        expected_bypasses if power_save_bypasses_exposed is None else tuple(power_save_bypasses_exposed)
    )
    if actual_bypasses != expected_bypasses:
        errors.append(
            f"{P381_GB_ERR_POWER_SAVE_2ITEM_BYPASS_9VS8_OR_DORMANT_MONITOR}: {camera_revision} requires exact {len(expected_bypasses)} Power Save bypasses (FX3=9 vs FX3A=8 after IR removal), got {len(actual_bypasses)}"
        )

    # IR/NFC Removal on ILME-FX3A, IR/BLE Mutex, USB-LAN Cnct. Launch & FX6 LANC
    if ir_remote_ctrl not in P381_VALID_ON_OFF or bluetooth_rmt_ctrl not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: ir_remote_ctrl and bluetooth_rmt_ctrl must be ON/OFF"
        )
    if usb_lan_cnct_launch not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: invalid usb_lan_cnct_launch {usb_lan_cnct_launch!r}"
        )
    ir_present = camera_revision == "ILME_FX3"
    nfc_present = camera_revision == "ILME_FX3"
    if camera_revision == "ILME_FX3A":
        if ir_remote_ctrl == "ON" or nfc_requested or claimed_fx3a_has_ir_or_nfc:
            errors.append(
                f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: 2025 ILME-FX3A (ilc/2510, 2.36M-dot LCD) physically removed IR remote receiver and NFC (EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
            )
    else:
        if claimed_fx3a_has_ir_or_nfc:
            errors.append(
                f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: 2025 ILME-FX3A physically removed IR remote receiver and NFC (EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
            )
        if ir_remote_ctrl == "ON" and bluetooth_rmt_ctrl == "ON":
            errors.append(
                f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: original ILME-FX3 [IR Remote Ctrl]=On and [Bluetooth Rmt Ctrl]=On are mutually exclusive (EINVAL={P381_ERRNO_EINVAL})"
            )
    if tuple(fx6_wired_remote_ports) != P381_FX6_WIRED_REMOTE_PORTS or claimed_fx6_has_ble_or_ir_remote:
        errors.append(
            f"{P381_GB_ERR_FX3A_IR_NFC_REMOVAL_BT_MUTEX_OR_FX6_LANC}: FX6 uses 2.5mm LANC + 3.5mm grip remote with ZERO BLE remote and ZERO physical IR receiver"
        )

    eff_usb_pwr = "ON" if reset_action == "INITIALIZE" else usb_power_supply
    eff_ps_time = (
        P381_POWER_SAVE_START_TIME_DEFAULT if reset_action == "INITIALIZE" else power_save_start_time
    )
    eff_auto_temp = (
        P381_AUTO_POWER_OFF_TEMP_DEFAULT if reset_action == "INITIALIZE" else auto_power_off_temp
    )
    eff_usblan_launch = (
        "OFF" if reset_action in ("RESET_NETWORK_SET", "INITIALIZE") else usb_lan_cnct_launch
    )

    return P381CheckGroupBUsbPdPmicPowerSaveFx3VsFx3aRemotesResult(
        group_id=P381_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        camera_revision=camera_revision,
        reset_action=reset_action,
        libusbbuspower_bytes=libusbbuspower_bytes,
        pmic_kmods_exposed=tuple(pmic_kmods_exposed),
        usb_power_supply=usb_power_supply,
        effective_usb_power_supply_after_reset=eff_usb_pwr,
        usb_power_profile=usb_power_profile,
        usb_power_terminal=usb_power_terminal,
        np_fz100_inserted=np_fz100_inserted,
        dc_c1_pd_watts=dc_c1_pd_watts,
        dc_c1_cable_amps=dc_c1_cable_amps,
        on_state_charging_possible=False,
        off_state_charging_active=off_state_charging_active,
        ambient_temp_c=ambient_temp_c,
        power_loss_hotpull_blocked=True,
        fx6_dc_in_voltage_v=fx6_dc_in_voltage_v,
        fx6_batteryless_boot_supported=True,
        fx6_usbc_power_supply_supported=False,
        power_setting_option_items=tuple(power_setting_option_items),
        power_save_start_time=power_save_start_time,
        effective_power_save_start_time_after_reset=eff_ps_time,
        auto_power_off_temp=auto_power_off_temp,
        effective_auto_power_off_temp_after_reset=eff_auto_temp,
        power_save_bypass_count=len(actual_bypasses),
        fx3_power_save_by_monitor_supported=False,
        ir_receiver_present=ir_present,
        nfc_present=nfc_present,
        ir_remote_ctrl=ir_remote_ctrl,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        effective_usb_lan_cnct_launch_after_reset=eff_usblan_launch,
        fx6_wired_remote_ports=tuple(fx6_wired_remote_ports),
        fx6_ble_or_ir_remote_supported=False,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 84.1-84.2)
# ---------------------------------------------------------------------------


def evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
    *,
    shoot_mode: str = "PHOTO",
    reset_action: str = "NONE",
    # My Menu 42 Slots (G98 Erratum) & CAMSET Slot 1 EROFS=30
    my_menu_pages: int = P381_MY_MENU_EXACT_PAGES,
    my_menu_items_per_page: int = P381_MY_MENU_EXACT_ITEMS_PER_PAGE,
    my_menu_total_slots: int = P381_MY_MENU_EXACT_TOTAL_SLOTS,
    my_menu_ops_exposed: Tuple[str, ...] = P381_MY_MENU_EXACT_6_OPS,
    display_from_my_menu: str = P381_DISPLAY_FROM_MY_MENU_DEFAULT,
    claimed_mymenu_capacity_30_or_36_g98: bool = False,
    mymenu_add_playback_item_requested: bool = False,
    claimed_mymenu_wiped_by_camera_reset: bool = False,
    camset_operation: str = "NONE",
    camset_target_slot: int = 1,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    # Fn Menu Settings 12+12 / Zero Follow Custom / XLR-H1 / FX6 User Menu
    fn_menu_still_slots: int = P381_FN_MENU_STILL_EXACT_SLOTS,
    fn_menu_movie_slots: int = P381_FN_MENU_MOVIE_EXACT_SLOTS,
    fn_menu_active_slots: int = 12,
    fn_menu_all_not_set_requested: bool = False,
    claimed_fn_menu_has_follow_custom: bool = False,
    claimed_fn_menu_wiped_by_camera_reset: bool = False,
    claimed_xlr_h1_has_fn_menu_or_rec_keys: bool = False,
    fx6_user_menu_max_items: int = P381_FX6_USER_MENU_MAX_ITEMS,
    claimed_fx6_user_menu_lock_in_all_file_or_fn12: bool = False,
    # Focus Mode Still 5 vs Movie 2 / Still AF vs Movie AF Subj. Shift Sens. 5(Responsive)
    focus_mode: str = P381_STILL_FOCUS_DEFAULT,
    lens_pdaf_supported: bool = True,
    lens_is_e_mount: bool = True,
    af_w_shutter: str = "ON",
    pre_af: str = "OFF",
    still_af_tracking_sensitivity: int = P381_STILL_AF_TRACK_SENS_DEFAULT,
    movie_af_transition_speed: int = P381_MOVIE_AF_TRANSITION_SPEED_DEFAULT,
    movie_af_subj_shift_sensitivity: int = P381_MOVIE_AF_SUBJ_SHIFT_SENS_DEFAULT,
    movie_af_subj_shift_responsice_symbol: str = P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL,
    claimed_movie_af_subj_shift_default_is_3: bool = False,
    claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset: bool = False,
    # Focus Area Limit 14 & Circ. of Focus Point
    focus_area_limit_items_exposed: Tuple[str, ...] = P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS,
    focus_area_limit_checked_count: int = 14,
    circ_of_focus_point: str = P381_CIRC_OF_FOCUS_POINT_DEFAULT,
    expect_diagonal_focus_circulation: bool = False,
    claimed_circ_wiped_by_camera_reset: bool = False,
    fx6_face_eye_af_mode: str = "FACE_EYE_PRIORITY_AF",
    claimed_fx6_has_still_af_s_afa_dmf_or_pre_af: bool = False,
) -> P381CheckGroupCMyMenu42Fn12FocusModeSubjShift5FocusLimit14Result:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P381_VALID_SHOOT_MODES:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: invalid shoot_mode {shoot_mode!r}"
        )
    if reset_action not in P381_VALID_RESET_ACTIONS:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: invalid reset_action {reset_action!r}"
        )

    # [My Menu] Exact 6 x 7 = 42 Slots (Wave 84 G98 Erratum) & CAMSET Slot 1 EROFS=30
    if (
        my_menu_pages != P381_MY_MENU_EXACT_PAGES
        or my_menu_items_per_page != P381_MY_MENU_EXACT_ITEMS_PER_PAGE
        or my_menu_total_slots != P381_MY_MENU_EXACT_TOTAL_SLOTS
        or claimed_mymenu_capacity_30_or_36_g98
    ):
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: [My Menu] exact capacity is 6 x 7 = 42 slots (BKID_APP_mymenu_group1..6_setting_list0..6; Wave 84 G98 erratum debunks 30/36), got {my_menu_pages}x{my_menu_items_per_page}={my_menu_total_slots}"
        )
    if tuple(my_menu_ops_exposed) != P381_MY_MENU_EXACT_6_OPS:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: [My Menu Setting] must expose exact 6 ops {P381_MY_MENU_EXACT_6_OPS}"
        )
    if display_from_my_menu not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: invalid display_from_my_menu {display_from_my_menu!r}"
        )
    if mymenu_add_playback_item_requested:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: (Playback) menu items are blacklisted from [My Menu] (EINVAL={P381_ERRNO_EINVAL})"
        )
    if claimed_mymenu_wiped_by_camera_reset:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: all 6 [My Menu] ops and [Display From My Menu] resist [Camera Settings Reset] (Initialize-only)"
        )
    if camset_operation not in P381_CAMSET_OPERATIONS:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: invalid camset_operation {camset_operation!r}"
        )
    if camset_operation != "NONE" and camset_target_slot != 1:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: [Save/Load Settings] CAMSET01..10.DAT is Slot 1 exclusive (got slot {camset_target_slot})"
        )
    if (
        camset_operation in ("SAVE", "DELETE")
        and camset_target_slot == 1
        and (slot1_contains_tier0_dump or slot1_wp_locked)
    ):
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: CAMSET {camset_operation} on Slot 1 Tier-0 Vault blocked EROFS={P381_ERRNO_EROFS}"
        )
    if slot1_sector_writes != 0:
        errors.append(
            f"{P381_GC_ERR_MYMENU_42_G98_PLAYBACK_BLACKLIST_OR_CAMSET_EROFS30}: Slot 1 sector writes must remain 0 (EROFS={P381_ERRNO_EROFS})"
        )

    # [Fn Menu Settings] 12+12 Split / Zero Follow Custom / XLR-H1 / FX6 User Menu
    if (
        fn_menu_still_slots != P381_FN_MENU_STILL_EXACT_SLOTS
        or fn_menu_movie_slots != P381_FN_MENU_MOVIE_EXACT_SLOTS
    ):
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: [Fn Menu Settings] must expose exact 12 Still + 12 Movie slots (got {fn_menu_still_slots}+{fn_menu_movie_slots})"
        )
    if fn_menu_all_not_set_requested or fn_menu_active_slots < 1 or fn_menu_active_slots > 12:
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: Fn Menu all-'Not set' is blocked by _f 0x6220 (requires 1..12 assigned slots, got {fn_menu_active_slots})"
        )
    if claimed_fn_menu_has_follow_custom:
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: [Fn Menu Settings] has ZERO Follow Custom switch (0 hits in ilc/2210 and appFw.so)"
        )
    if claimed_fn_menu_wiped_by_camera_reset:
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: [Fn Menu Settings] resists [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_xlr_h1_has_fn_menu_or_rec_keys:
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: XLR-H1 handle has ZERO Fn, MENU, or REC buttons"
        )
    if fx6_user_menu_max_items != P381_FX6_USER_MENU_MAX_ITEMS or claimed_fx6_user_menu_lock_in_all_file_or_fn12:
        errors.append(
            f"{P381_GC_ERR_FN12_NO_FOLLOW_CUSTOM_XLRH1_OR_FX6_USER_MENU}: FX6 User Menu holds max {P381_FX6_USER_MENU_MAX_ITEMS} items, excludes 4-digit User Menu with Lock from All File, and has zero 12+12 Fn grid"
        )

    # [Focus Mode] Still 5 vs Movie 2 & AF Kinematics (Subj. Shift Sens. default 5 RESPONSICE)
    if focus_mode not in P381_STILL_FOCUS_EXACT_5_MODES:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: invalid focus_mode {focus_mode!r}"
        )
    if shoot_mode in ("MOVIE", "S_AND_Q") and focus_mode not in P381_MOVIE_FOCUS_EXACT_2_MODES:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Movie/S&Q [Focus Mode] is hard-locked to {P381_MOVIE_FOCUS_EXACT_2_MODES} (got {focus_mode!r}, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )
    if shoot_mode == "PHOTO" and focus_mode == "AF_A" and not lens_pdaf_supported:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Still AF-A requires a phase-detection AF compatible lens"
        )
    if af_w_shutter not in P381_VALID_ON_OFF or pre_af not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: af_w_shutter and pre_af must be ON/OFF"
        )
    if pre_af == "ON" and not lens_is_e_mount:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: [Pre-AF]=ON is E-mount lens only"
        )
    if claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: [AF w/ Shutter] and [Pre-AF] resist [Camera Settings Reset] (Initialize-only)"
        )
    if not (P381_STILL_AF_TRACK_SENS_MIN <= still_af_tracking_sensitivity <= P381_STILL_AF_TRACK_SENS_MAX):
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Still [AF Tracking Sensitivity] must be 1..5, got {still_af_tracking_sensitivity}"
        )
    if not (P381_MOVIE_AF_TRANSITION_SPEED_MIN <= movie_af_transition_speed <= P381_MOVIE_AF_TRANSITION_SPEED_MAX):
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Movie [AF Transition Speed] must be 1..7, got {movie_af_transition_speed}"
        )
    if not (P381_MOVIE_AF_SUBJ_SHIFT_SENS_MIN <= movie_af_subj_shift_sensitivity <= P381_MOVIE_AF_SUBJ_SHIFT_SENS_MAX):
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Movie [AF Subj. Shift Sensitivity] must be 1..5, got {movie_af_subj_shift_sensitivity}"
        )
    if movie_af_subj_shift_responsice_symbol != P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: ELF symbol must match {P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL!r}"
        )
    if claimed_movie_af_subj_shift_default_is_3:
        errors.append(
            f"{P381_GC_ERR_FOCUS_MODE_5VS2_OR_AF_SENS_DEFAULT5_RESPONSICE}: Movie [AF Subj. Shift Sensitivity] factory default is 5(Responsive) (NOT 3!)"
        )

    # [Focus Area Limit] Exact 14 & [Circ. of Focus Point] & FX6 AF Contrast
    if tuple(focus_area_limit_items_exposed) != P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS:
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: [Focus Area Limit] must expose exact 14 checkboxes"
        )
    if not (P381_FOCUS_AREA_LIMIT_MIN_CHECKED_TO_SWITCH <= focus_area_limit_checked_count <= len(P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS)):
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: [Focus Area Limit] requires >= 2..14 checked areas to switch (.uxc 0xea28), got {focus_area_limit_checked_count}"
        )
    if circ_of_focus_point not in P381_CIRC_OF_FOCUS_POINT_OPTIONS:
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: invalid circ_of_focus_point {circ_of_focus_point!r}"
        )
    if expect_diagonal_focus_circulation:
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: [Circ. of Focus Point] wraps orthogonally only (zero diagonal circulation across 8 movable areas)"
        )
    if claimed_circ_wiped_by_camera_reset:
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: [Circ. of Focus Point] resists [Camera Settings Reset] (Initialize-only)"
        )
    if fx6_face_eye_af_mode not in P381_FX6_FACE_EYE_AF_EXACT_3_MODES or claimed_fx6_has_still_af_s_afa_dmf_or_pre_af:
        errors.append(
            f"{P381_GC_ERR_FOCUS_AREA_LIMIT_14_CIRC_ORTHO_OR_FX6_AF}: FX6 exposes Face/Eye Detection AF {P381_FX6_FACE_EYE_AF_EXACT_3_MODES} with zero Still AF-S/AF-A/DMF/Pre-AF"
        )

    eff_disp_mymenu = P381_DISPLAY_FROM_MY_MENU_DEFAULT if reset_action == "INITIALIZE" else display_from_my_menu
    default_focus_for_mode = P381_STILL_FOCUS_DEFAULT if shoot_mode == "PHOTO" else P381_MOVIE_FOCUS_DEFAULT
    eff_focus = (
        default_focus_for_mode
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else focus_mode
    )
    eff_af_w_shutter = "ON" if reset_action == "INITIALIZE" else af_w_shutter
    eff_pre_af = "OFF" if reset_action == "INITIALIZE" else pre_af
    eff_still_track = (
        P381_STILL_AF_TRACK_SENS_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else still_af_tracking_sensitivity
    )
    eff_movie_trans = (
        P381_MOVIE_AF_TRANSITION_SPEED_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else movie_af_transition_speed
    )
    eff_movie_shift = (
        P381_MOVIE_AF_SUBJ_SHIFT_SENS_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else movie_af_subj_shift_sensitivity
    )
    eff_circ = (
        P381_CIRC_OF_FOCUS_POINT_DEFAULT if reset_action == "INITIALIZE" else circ_of_focus_point
    )

    return P381CheckGroupCMyMenu42Fn12FocusModeSubjShift5FocusLimit14Result(
        group_id=P381_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        my_menu_pages=my_menu_pages,
        my_menu_items_per_page=my_menu_items_per_page,
        my_menu_total_slots=my_menu_total_slots,
        my_menu_ops_exposed=tuple(my_menu_ops_exposed),
        display_from_my_menu=display_from_my_menu,
        effective_display_from_my_menu_after_reset=eff_disp_mymenu,
        camset_operation=camset_operation,
        camset_target_slot=camset_target_slot,
        camset_slot1_write_blocked_erofs30=True,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        fn_menu_active_slots=fn_menu_active_slots,
        fx3_fn_menu_follow_custom_supported=False,
        xlr_h1_has_fn_menu_or_rec_keys=False,
        fx6_user_menu_max_items=fx6_user_menu_max_items,
        fx6_user_menu_lock_excluded_from_all_file=True,
        focus_mode=focus_mode,
        effective_focus_mode_after_reset=eff_focus,
        af_w_shutter=af_w_shutter,
        effective_af_w_shutter_after_reset=eff_af_w_shutter,
        pre_af=pre_af,
        effective_pre_af_after_reset=eff_pre_af,
        still_af_tracking_sensitivity=still_af_tracking_sensitivity,
        effective_still_af_tracking_sens_after_reset=eff_still_track,
        movie_af_transition_speed=movie_af_transition_speed,
        effective_movie_af_transition_speed_after_reset=eff_movie_trans,
        movie_af_subj_shift_sensitivity=movie_af_subj_shift_sensitivity,
        effective_movie_af_subj_shift_sens_after_reset=eff_movie_shift,
        movie_af_subj_shift_responsice_symbol=movie_af_subj_shift_responsice_symbol,
        focus_area_limit_items_exposed=tuple(focus_area_limit_items_exposed),
        focus_area_limit_checked_count=focus_area_limit_checked_count,
        circ_of_focus_point=circ_of_focus_point,
        effective_circ_of_focus_point_after_reset=eff_circ,
        circ_movable_areas_count=P381_CIRC_MOVABLE_AREAS_COUNT,
        fx6_face_eye_af_mode=fx6_face_eye_af_mode,
        slot1_sector_writes=PHASE381_SLOT1_SECTOR_WRITES,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 84.3-84.4 + Mandatory Tier-0 Receipt Gate)
# ---------------------------------------------------------------------------


def evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "APERTURE_PRIORITY",
    iso_mode: str = "ISO_AUTO",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    # Exposure Comp / Exposure Step / Exposure Std Adjust 5 / AEL / Spot 8-vs-6 (G116)
    exposure_comp_ev: float = 0.0,
    expect_exposure_comp_active_under_lockout: bool = False,
    exposure_step: str = P381_EXP_STEP_DEFAULT,
    shutter_mode: str = "SPEED",
    expect_exposure_step_alters_shutter_angle: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    exposure_std_adjust_modes_exposed: Tuple[str, ...] = P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES,
    exposure_std_adjust_mode: str = "MULTI",
    exposure_std_adjust_sixths: int = 0,
    claimed_exp_std_adjust_only_4_modes_missing_highlight: bool = False,
    claimed_exp_std_adjust_wiped_by_camera_reset: bool = False,
    ael_w_shutter: str = P381_AEL_W_SHUTTER_DEFAULT,
    expect_ael_w_shutter_in_movie_or_sq: bool = False,
    claimed_ael_w_shutter_wiped_by_camera_reset: bool = False,
    spot_metering_point: str = P381_SPOT_METERING_POINT_DEFAULT,
    spot_metering_focus_area: str = "Spot: M",
    spot_metering_linked_areas_exposed: Tuple[str, ...] = P381_SPOT_METERING_LINKED_EXACT_8_AREAS,
    spot_metering_center_locked_areas_exposed: Tuple[str, ...] = P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS,
    expect_spot_metering_follows_moving_tracking_subject: bool = False,
    claimed_g116_center_locked_only_3_omitting_tracking: bool = False,
    # FX6 Auto Exposure Level (25 steps, ZERO AE Shift) & AGC Limit
    fx6_ae_level_ev: float = 0.0,
    claimed_fx6_has_ae_shift_menu: bool = False,
    fx6_agc_limit_db: int = 18,
    fx6_agc_iso_groups: int = P381_FX6_AGC_ISO_GROUP_COUNT,
    # Playback (View Mode 3, Display Rotation Auto + rotatiton, Image Index, Protect 7 G114, Rating, Slot 1 EROFS=30, Zero-RF Send)
    view_mode: str = P381_VIEW_MODE_DEFAULT,
    view_mode_options_exposed: Tuple[str, ...] = P381_VIEW_MODE_EXACT_3_STATES,
    dormant_xavc_codec_view_mode_requested: bool = False,
    display_rotation: str = P381_DISPLAY_ROTATION_DEFAULT,
    display_rotation_bkid_typo: str = P381_DISPLAY_ROTATION_BKID_TYPO,
    claimed_display_rotation_default_is_off: bool = False,
    image_index: str = P381_IMAGE_INDEX_DEFAULT,
    dormant_image_index_12_or_30_requested: bool = False,
    display_as_group: str = P381_DISPLAY_AS_GROUP_DEFAULT,
    enlarge_initial_mag: str = P381_ENLARGE_INITIAL_MAG_DEFAULT,
    enlarge_initial_position: str = P381_ENLARGE_INITIAL_POS_DEFAULT,
    claimed_playback_display_options_wiped_by_camera_reset: bool = False,
    protect_menu_items_exposed: Tuple[str, ...] = P381_PROTECT_MENU_EXACT_7_ITEMS,
    claimed_protect_menu_has_single_g114: bool = False,
    protect_write_requested: bool = False,
    rating_write_requested: bool = False,
    rating_stars: int = 0,
    rating_movie_during_recording_requested: bool = False,
    playback_target_slot: int = 2,
    airplane_mode: str = "ON",
    cnct_while_power_off: str = "OFF",
    select_on_cam_and_send_requested: bool = False,
    fx6_clip_flag: str = "OK",
    claimed_fx6_has_5star_rating_or_display_as_group: bool = False,
    # Tier-0 Vault & Zero-Telemetry Redlines
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    slot1_data_sector_writes: int = 0,
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
) -> P381CheckGroupDExpCompExpStd5Spot8Vs6PlaybackSlot1ZeroRfTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P381_VALID_SHOOT_MODES:
        errors.append(f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid shoot_mode {shoot_mode!r}")
    if exposure_mode not in P381_VALID_EXPOSURE_MODES:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid exposure_mode {exposure_mode!r}"
        )
    if iso_mode not in P381_VALID_ISO_MODES:
        errors.append(f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid iso_mode {iso_mode!r}")
    if log_shooting_mode not in P381_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid log_shooting_mode {log_shooting_mode!r}"
        )

    # [Exposure Comp.], [Exposure step], 5-Mode [Exposure Std. Adjust], [AEL w/ Shutter], [Spot Metering Point]
    max_abs_ev = (
        P381_EXP_COMP_STILL_MAX_ABS_EV if shoot_mode == "PHOTO" else P381_EXP_COMP_MOVIE_MAX_ABS_EV
    )
    if abs(exposure_comp_ev) > max_abs_ev + 1e-9:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure Comp.] in {shoot_mode} must be within +/-{max_abs_ev} EV, got {exposure_comp_ev}"
        )
    exp_comp_locked = (
        exposure_mode == "INTELLIGENT_AUTO"
        or (exposure_mode == "MANUAL_EXPOSURE" and iso_mode == "MANUAL_ISO")
        or log_shooting_mode in ("CINE_EI", "CINE_EI_QUICK")
    )
    if exp_comp_locked and (abs(exposure_comp_ev) > 1e-9 or expect_exposure_comp_active_under_lockout):
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure Comp.] is locked in iAuto, M+fixed ISO, Cine EI, and Cine EI Quick"
        )
    if exposure_step not in P381_EXP_STEP_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid exposure_step {exposure_step!r}"
        )
    if shutter_mode not in P381_SHUTTER_MODES:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid shutter_mode {shutter_mode!r}"
        )
    if expect_exposure_step_alters_shutter_angle:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure step] (0.3EV/0.5EV) is independent of [Shutter Mode]=Angle"
        )
    if claimed_exposure_step_wiped_by_camera_reset:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure step] resists [Camera Settings Reset] (Initialize-only)"
        )
    if (
        tuple(exposure_std_adjust_modes_exposed) != P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES
        or claimed_exp_std_adjust_only_4_modes_missing_highlight
    ):
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure Std. Adjust] covers ALL 5 metering modes {P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES} (incl. Highlight)"
        )
    if exposure_std_adjust_mode not in P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid exposure_std_adjust_mode {exposure_std_adjust_mode!r}"
        )
    if not (
        P381_EXPOSURE_STD_ADJUST_MIN_SIXTHS
        <= exposure_std_adjust_sixths
        <= P381_EXPOSURE_STD_ADJUST_MAX_SIXTHS
    ):
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure Std. Adjust] must be -6..+6 sixths (+/-1 EV in 1/6 EV, 13 steps), got {exposure_std_adjust_sixths}"
        )
    if claimed_exp_std_adjust_wiped_by_camera_reset:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Exposure Std. Adjust] resists [Camera Settings Reset] (Initialize-only)"
        )
    if ael_w_shutter not in P381_AEL_W_SHUTTER_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid ael_w_shutter {ael_w_shutter!r}"
        )
    if expect_ael_w_shutter_in_movie_or_sq and shoot_mode != "PHOTO":
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [AEL w/ Shutter] is strictly Still-only"
        )
    if claimed_ael_w_shutter_wiped_by_camera_reset:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [AEL w/ Shutter] resists [Camera Settings Reset] (Initialize-only)"
        )
    if spot_metering_point not in P381_SPOT_METERING_POINT_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid spot_metering_point {spot_metering_point!r}"
        )
    if tuple(spot_metering_linked_areas_exposed) != P381_SPOT_METERING_LINKED_EXACT_8_AREAS:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: [Spot Metering Point] Focus Point Link applies to exact 8 focus areas"
        )
    if (
        tuple(spot_metering_center_locked_areas_exposed)
        != P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS
        or claimed_g116_center_locked_only_3_omitting_tracking
    ):
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: Wave 84 G116 erratum: [Spot Metering Point] center-locks exact 6 focus areas (incl. Tracking: Wide/Zone/Center Fix)"
        )
    if spot_metering_focus_area not in P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: invalid spot_metering_focus_area {spot_metering_focus_area!r}"
        )
    if expect_spot_metering_follows_moving_tracking_subject:
        errors.append(
            f"{P381_GD_ERR_EXP_COMP_STEP_STD5_AEL_OR_SPOT_G116}: in Tracking: Spot/Expand Spot, [Spot Metering Point] links ONLY to the initial focus point (never follows moving subject)"
        )
    spot_linked_active = (
        spot_metering_point == "FOCUS_POINT_LINK"
        and spot_metering_focus_area in P381_SPOT_METERING_LINKED_EXACT_8_AREAS
    )

    # FX6 Auto Exposure Level (25 steps, ZERO AE Shift) & AGC Limit
    fx6_ae_quarters = round(fx6_ae_level_ev / P381_FX6_AE_LEVEL_STEP_EV)
    if (
        not (P381_FX6_AE_LEVEL_MIN_EV <= fx6_ae_level_ev <= P381_FX6_AE_LEVEL_MAX_EV)
        or abs(fx6_ae_level_ev - fx6_ae_quarters * P381_FX6_AE_LEVEL_STEP_EV) > 1e-6
    ):
        errors.append(
            f"{P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12}: FX6 Auto Exposure Level must be -3.0..+3.0 EV in 0.25 EV steps (25 steps), got {fx6_ae_level_ev}"
        )
    if claimed_fx6_has_ae_shift_menu:
        errors.append(
            f"{P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12}: FX6 has ZERO 'AE Shift' menu item (uses Auto Exposure Level, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )
    if (
        not (P381_FX6_AGC_LIMIT_MIN_DB <= fx6_agc_limit_db <= P381_FX6_AGC_LIMIT_MAX_DB)
        or (fx6_agc_limit_db % P381_FX6_AGC_LIMIT_STEP_DB) != 0
        or fx6_agc_iso_groups != P381_FX6_AGC_ISO_GROUP_COUNT
    ):
        errors.append(
            f"{P381_GD_ERR_FX6_AE_LEVEL_25STEP_ZERO_AESHIFT_OR_AGC12}: FX6 AGC Limit must be 3..36 dB (3 dB step) with 12 ISO groups (got {fx6_agc_limit_db} dB, {fx6_agc_iso_groups} groups)"
        )

    # Playback Display Options (View Mode 3, Display Rotation Auto + rotatiton, Index, Group, Enlarge)
    if tuple(view_mode_options_exposed) != P381_VIEW_MODE_EXACT_3_STATES:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: [View Mode] exposes exact 3 states {P381_VIEW_MODE_EXACT_3_STATES} (zero codec-split XAVC views)"
        )
    if view_mode not in P381_VIEW_MODE_EXACT_3_STATES or dormant_xavc_codec_view_mode_requested:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: invalid or dormant codec-split View Mode ({view_mode!r}, EOPNOTSUPP={P381_ERRNO_EOPNOTSUPP})"
        )
    if display_rotation not in P381_DISPLAY_ROTATION_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: invalid display_rotation {display_rotation!r}"
        )
    if display_rotation_bkid_typo != P381_DISPLAY_ROTATION_BKID_TYPO:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: Sony ELF BKID typo must match {P381_DISPLAY_ROTATION_BKID_TYPO!r}"
        )
    if claimed_display_rotation_default_is_off:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: [Display Rotation] factory default is Auto (NOT Off!)"
        )
    if image_index not in P381_IMAGE_INDEX_EXACT_2_OPTIONS or dormant_image_index_12_or_30_requested:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: [Image Index] exposes only 9_IMAGES / 25_IMAGES (12/30 dormant, got {image_index!r})"
        )
    if display_as_group not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: invalid display_as_group {display_as_group!r}"
        )
    if enlarge_initial_mag not in P381_ENLARGE_INITIAL_MAG_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: invalid enlarge_initial_mag {enlarge_initial_mag!r}"
        )
    if enlarge_initial_position not in P381_ENLARGE_INITIAL_POS_OPTIONS:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: invalid enlarge_initial_position {enlarge_initial_position!r}"
        )
    if claimed_playback_display_options_wiped_by_camera_reset:
        errors.append(
            f"{P381_GD_ERR_PLAYBACK_VIEW3_ROTATITON_AUTO_OR_ANTIRESET}: Playback View Mode, Display Rotation, Image Index, Display as Group, and Enlarge Initial Mag./Position all resist [Camera Settings Reset]"
        )

    # [Protect] 7 Menu Items (Wave 84 G114 Erratum), [Rating] 0..5, Slot 1 EROFS=30 Firewall
    if (
        tuple(protect_menu_items_exposed) != P381_PROTECT_MENU_EXACT_7_ITEMS
        or claimed_protect_menu_has_single_g114
    ):
        errors.append(
            f"{P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30}: Wave 84 G114 erratum: [Protect] menu exposes exact 7 items with ZERO 'Single' (single toggle is Custom Key only)"
        )
    if not (P381_RATING_MIN_STARS <= rating_stars <= P381_RATING_MAX_STARS):
        errors.append(
            f"{P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30}: [Rating] stars must be 0..5 (Off + 1..5), got {rating_stars}"
        )
    if rating_movie_during_recording_requested:
        errors.append(
            f"{P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30}: [Rating] cannot be applied to movies during shooting (TP1000882823)"
        )
    if playback_target_slot not in (1, 2):
        errors.append(
            f"{P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30}: playback_target_slot must be 1 or 2, got {playback_target_slot}"
        )
    if (
        (protect_write_requested or rating_write_requested)
        and playback_target_slot == 1
        and (slot1_contains_tier0_dump or slot1_wp_locked)
    ):
        errors.append(
            f"{P381_GD_ERR_PROTECT_7MENU_G114_RATING_SLOT1_EROFS30}: [Protect] (syncs {P381_PROTECT_PROXY_SUB_PATTERN}) / [Rating] (XMP write) targeting Slot 1 Tier-0 Vault blocked EROFS={P381_ERRNO_EROFS}"
        )

    # [Select on Cam & Send] Zero-RF Airplane Mode Block & FX6 Thumbnail Contrast
    if airplane_mode not in P381_VALID_ON_OFF or cnct_while_power_off not in P381_VALID_ON_OFF:
        errors.append(
            f"{P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL}: airplane_mode and cnct_while_power_off must be ON/OFF"
        )
    if airplane_mode != "ON" or cnct_while_power_off != "OFF":
        errors.append(
            f"{P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL}: Zero-RF bench requires [Airplane Mode]=ON and [Cnct. while Power OFF]=OFF"
        )
    if select_on_cam_and_send_requested:
        errors.append(
            f"{P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL}: [Select on Cam & Send] is hard-blocked when [Airplane Mode]=On (zero-RF redline, EPERM={P381_ERRNO_EPERM})"
        )
    if fx6_clip_flag not in P381_FX6_CLIP_FLAGS or claimed_fx6_has_5star_rating_or_display_as_group:
        errors.append(
            f"{P381_GD_ERR_SELECT_SEND_AIRPLANE_ZERORF_OR_FX6_THUMBNAIL}: FX6 uses Thumbnail / Clip Flag {P381_FX6_CLIP_FLAGS} / Shot Mark 1-2 / Lock-Unlock Clip (zero 1..5 star Rating or Display as Group)"
        )

    # Zero-Telemetry & Fail-Closed Redlines
    if (
        slot1_sector_writes != 0
        or slot1_data_sector_writes != 0
        or emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or rf_tx_packets != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
    ):
        errors.append(
            f"{P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: telemetry counters must remain 0 "
            f"(slot1={slot1_sector_writes}, slot1_data={slot1_data_sector_writes}, emmc={emmc_write_count}, "
            f"e_nd={e_nd_actuator_tx_count}, rf={rf_tx_packets}, usb={usb_packets_transmitted}, passive={simulated_passive_tx_bytes})"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P381_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: live attach, persistent eMMC writes, and cross-model flash remain hard-locked False"
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

    eff_exp_comp = (
        0.0 if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE") else exposure_comp_ev
    )
    eff_exp_step = P381_EXP_STEP_DEFAULT if reset_action == "INITIALIZE" else exposure_step
    eff_std_sixths = 0 if reset_action == "INITIALIZE" else exposure_std_adjust_sixths
    eff_ael = P381_AEL_W_SHUTTER_DEFAULT if reset_action == "INITIALIZE" else ael_w_shutter
    eff_view = P381_VIEW_MODE_DEFAULT if reset_action == "INITIALIZE" else view_mode
    eff_rot = P381_DISPLAY_ROTATION_DEFAULT if reset_action == "INITIALIZE" else display_rotation
    eff_idx = P381_IMAGE_INDEX_DEFAULT if reset_action == "INITIALIZE" else image_index
    eff_grp = P381_DISPLAY_AS_GROUP_DEFAULT if reset_action == "INITIALIZE" else display_as_group
    eff_mag = P381_ENLARGE_INITIAL_MAG_DEFAULT if reset_action == "INITIALIZE" else enlarge_initial_mag
    eff_pos = P381_ENLARGE_INITIAL_POS_DEFAULT if reset_action == "INITIALIZE" else enlarge_initial_position

    return P381CheckGroupDExpCompExpStd5Spot8Vs6PlaybackSlot1ZeroRfTier0Result(
        group_id=P381_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        exposure_comp_ev=exposure_comp_ev,
        exposure_comp_locked=exp_comp_locked,
        effective_exposure_comp_after_reset=eff_exp_comp,
        exposure_step=exposure_step,
        effective_exposure_step_after_reset=eff_exp_step,
        shutter_mode=shutter_mode,
        exposure_std_adjust_modes_exposed=tuple(exposure_std_adjust_modes_exposed),
        exposure_std_adjust_mode=exposure_std_adjust_mode,
        exposure_std_adjust_sixths=exposure_std_adjust_sixths,
        effective_exposure_std_adjust_sixths_after_reset=eff_std_sixths,
        ael_w_shutter=ael_w_shutter,
        effective_ael_w_shutter_after_reset=eff_ael,
        spot_metering_point=spot_metering_point,
        spot_metering_focus_area=spot_metering_focus_area,
        spot_metering_linked_areas=tuple(spot_metering_linked_areas_exposed),
        spot_metering_center_locked_areas=tuple(spot_metering_center_locked_areas_exposed),
        spot_metering_linked_active=spot_linked_active,
        fx6_ae_level_ev=fx6_ae_level_ev,
        fx6_ae_shift_menu_supported=False,
        fx6_agc_limit_db=fx6_agc_limit_db,
        fx6_agc_iso_groups=fx6_agc_iso_groups,
        view_mode=view_mode,
        view_mode_options_exposed=tuple(view_mode_options_exposed),
        effective_view_mode_after_reset=eff_view,
        display_rotation=display_rotation,
        effective_display_rotation_after_reset=eff_rot,
        display_rotation_bkid_typo=display_rotation_bkid_typo,
        image_index=image_index,
        effective_image_index_after_reset=eff_idx,
        display_as_group=display_as_group,
        effective_display_as_group_after_reset=eff_grp,
        enlarge_initial_mag=enlarge_initial_mag,
        effective_enlarge_initial_mag_after_reset=eff_mag,
        enlarge_initial_position=enlarge_initial_position,
        effective_enlarge_initial_position_after_reset=eff_pos,
        protect_menu_items_exposed=tuple(protect_menu_items_exposed),
        protect_write_requested=protect_write_requested,
        protect_syncs_proxy_pattern=P381_PROTECT_PROXY_SUB_PATTERN,
        rating_write_requested=rating_write_requested,
        rating_stars=rating_stars,
        playback_target_slot=playback_target_slot,
        slot1_playback_write_blocked_erofs30=True,
        airplane_mode=airplane_mode,
        cnct_while_power_off=cnct_while_power_off,
        select_on_cam_and_send_requested=select_on_cam_and_send_requested,
        select_on_cam_and_send_blocked_zero_rf=True,
        fx6_clip_flag=fx6_clip_flag,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=PHASE381_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE381_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P381_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 381 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P381_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "PHOTO",
    exposure_mode: str = "APERTURE_PRIORITY",
    iso_mode: str = "ISO_AUTO",
    log_shooting_mode: str = "OFF",
    picture_profile: str = "PP11",
    hlg_still_image: str = "OFF",
    reset_action: str = "NONE",
    # Group A
    creative_look_slot: str = P381_CREATIVE_LOOK_DEFAULT,
    creative_look_nvram_total_keys: int = P381_CREATIVE_LOOK_TOTAL_NVRAM_KEYS,
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
    expect_creative_look_active_under_lockout: bool = False,
    claimed_creative_look_fade_sharpness_clarity_accept_negative: bool = False,
    claimed_creative_look_resists_camera_reset: bool = False,
    dormant_soft_skin_effect_requested: bool = False,
    claimed_fx3_or_fx6_has_soft_skin_effect: bool = False,
    fx6_base_look_user_lut_slots: int = P381_FX6_BASE_LOOK_USER_LUT_SLOTS,
    claimed_fx6_has_creative_look_menu: bool = False,
    still_drive_mode: str = P381_STILL_DRIVE_DEFAULT,
    still_drive_modes_exposed: Tuple[str, ...] = P381_STILL_DRIVE_EXACT_8_MODES,
    cont_speed_tier: str = "HI_PLUS",
    aperture_f_number: float = 2.8,
    expect_hi_plus_live_view: bool = False,
    expect_af_tracks_all_frames_above_f11: bool = False,
    claimed_af_lock_threshold_is_f8: bool = False,
    claimed_drive_mode_resists_camera_reset: bool = False,
    drive_media_bus: str = "CFEXPRESS_TYPE_A_NVME",
    cfexpress_buffer_min_images: int = P381_CFEXPRESS_CEA_G160T_BUFFER_MIN,
    ev_bracket_step_ev: float = 0.7,
    ev_bracket_shot_count: int = 3,
    ev_bracket_combos_exposed: Tuple[Tuple[float, int], ...] = P381_EV_BRACKET_EXACT_16_COMBOS,
    dormant_focus_bracket_requested: bool = False,
    claimed_fx3_or_fx6_exposes_focus_bracket: bool = False,
    claimed_g151_fx6_focus_bracket_full_scan_is_56: bool = False,
    interval_items_exposed: Tuple[str, ...] = P381_INTERVAL_EXACT_7_ITEMS,
    interval_shutter_type: str = P381_INTERVAL_SHUTTER_DEFAULT,
    claimed_interval_shutter_name_is_legacy_silent_shoot: bool = False,
    claimed_interval_resists_camera_reset: bool = False,
    claimed_interval_in_camera_movie_synthesis: bool = False,
    fx6_special_rec_modes: Tuple[str, ...] = P381_FX6_SPECIAL_REC_EXACT_3,
    dormant_fx6_frame_rec_requested: bool = False,
    claimed_fx6_has_frame_rec: bool = False,
    # Group B
    camera_revision: str = "ILME_FX3",
    libusbbuspower_bytes: int = P381_LIBUSBBUSPOWER_EXPECTED_BYTES,
    pmic_kmods_exposed: Tuple[str, ...] = P381_LIBUSBBUSPOWER_EXACT_11_KMODS,
    usb_power_supply: str = "ON",
    usb_power_profile: str = "USB_PD_9V_3A_HIGH",
    usb_power_terminal: str = "USB_TYPE_C",
    np_fz100_inserted: bool = True,
    dc_c1_pd_watts: int = 65,
    dc_c1_cable_amps: int = 5,
    expect_on_state_battery_charging: bool = False,
    off_state_charging_active: bool = False,
    off_charge_pd_watts: float = 18.0,
    ambient_temp_c: float = 22.0,
    expect_5v_1_5a_sustains_4k_recording: bool = False,
    hot_pull_np_fz100_requested: bool = False,
    claimed_hot_pull_runs_poweroff_and_fsync: bool = False,
    claimed_usb_power_supply_wiped_by_camera_reset: bool = False,
    fx6_dc_in_voltage_v: float = P381_FX6_DC_IN_NOMINAL_V,
    fx6_hot_replug_dc_in_during_rec: bool = False,
    claimed_fx6_supports_usbc_power_supply: bool = False,
    power_setting_option_items: Tuple[str, ...] = P381_POWER_SETTING_OPTION_EXACT_2_ITEMS,
    power_save_start_time: str = P381_POWER_SAVE_START_TIME_DEFAULT,
    dormant_power_save_time_requested: Optional[str] = None,
    auto_power_off_temp: str = P381_AUTO_POWER_OFF_TEMP_DEFAULT,
    handheld_bare_skin_operation: bool = False,
    expect_high_temp_safe_handheld: bool = False,
    power_save_bypasses_exposed: Optional[Tuple[str, ...]] = None,
    claimed_power_setting_option_wiped_by_camera_reset: bool = False,
    dormant_power_save_by_monitor_requested: bool = False,
    ir_remote_ctrl: str = "OFF",
    bluetooth_rmt_ctrl: str = "OFF",
    nfc_requested: bool = False,
    claimed_fx3a_has_ir_or_nfc: bool = False,
    usb_lan_cnct_launch: str = "OFF",
    fx6_wired_remote_ports: Tuple[str, ...] = P381_FX6_WIRED_REMOTE_PORTS,
    claimed_fx6_has_ble_or_ir_remote: bool = False,
    # Group C
    my_menu_pages: int = P381_MY_MENU_EXACT_PAGES,
    my_menu_items_per_page: int = P381_MY_MENU_EXACT_ITEMS_PER_PAGE,
    my_menu_total_slots: int = P381_MY_MENU_EXACT_TOTAL_SLOTS,
    my_menu_ops_exposed: Tuple[str, ...] = P381_MY_MENU_EXACT_6_OPS,
    display_from_my_menu: str = P381_DISPLAY_FROM_MY_MENU_DEFAULT,
    claimed_mymenu_capacity_30_or_36_g98: bool = False,
    mymenu_add_playback_item_requested: bool = False,
    claimed_mymenu_wiped_by_camera_reset: bool = False,
    camset_operation: str = "NONE",
    camset_target_slot: int = 1,
    fn_menu_still_slots: int = P381_FN_MENU_STILL_EXACT_SLOTS,
    fn_menu_movie_slots: int = P381_FN_MENU_MOVIE_EXACT_SLOTS,
    fn_menu_active_slots: int = 12,
    fn_menu_all_not_set_requested: bool = False,
    claimed_fn_menu_has_follow_custom: bool = False,
    claimed_fn_menu_wiped_by_camera_reset: bool = False,
    claimed_xlr_h1_has_fn_menu_or_rec_keys: bool = False,
    fx6_user_menu_max_items: int = P381_FX6_USER_MENU_MAX_ITEMS,
    claimed_fx6_user_menu_lock_in_all_file_or_fn12: bool = False,
    focus_mode: str = P381_STILL_FOCUS_DEFAULT,
    lens_pdaf_supported: bool = True,
    lens_is_e_mount: bool = True,
    af_w_shutter: str = "ON",
    pre_af: str = "OFF",
    still_af_tracking_sensitivity: int = P381_STILL_AF_TRACK_SENS_DEFAULT,
    movie_af_transition_speed: int = P381_MOVIE_AF_TRANSITION_SPEED_DEFAULT,
    movie_af_subj_shift_sensitivity: int = P381_MOVIE_AF_SUBJ_SHIFT_SENS_DEFAULT,
    movie_af_subj_shift_responsice_symbol: str = P381_MOVIE_AF_SUBJ_SHIFT_RESPONSICE_SYMBOL,
    claimed_movie_af_subj_shift_default_is_3: bool = False,
    claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset: bool = False,
    focus_area_limit_items_exposed: Tuple[str, ...] = P381_FOCUS_AREA_LIMIT_EXACT_14_ITEMS,
    focus_area_limit_checked_count: int = 14,
    circ_of_focus_point: str = P381_CIRC_OF_FOCUS_POINT_DEFAULT,
    expect_diagonal_focus_circulation: bool = False,
    claimed_circ_wiped_by_camera_reset: bool = False,
    fx6_face_eye_af_mode: str = "FACE_EYE_PRIORITY_AF",
    claimed_fx6_has_still_af_s_afa_dmf_or_pre_af: bool = False,
    # Group D + Tier-0
    exposure_comp_ev: float = 0.0,
    expect_exposure_comp_active_under_lockout: bool = False,
    exposure_step: str = P381_EXP_STEP_DEFAULT,
    shutter_mode: str = "SPEED",
    expect_exposure_step_alters_shutter_angle: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    exposure_std_adjust_modes_exposed: Tuple[str, ...] = P381_EXPOSURE_STD_ADJUST_EXACT_5_MODES,
    exposure_std_adjust_mode: str = "MULTI",
    exposure_std_adjust_sixths: int = 0,
    claimed_exp_std_adjust_only_4_modes_missing_highlight: bool = False,
    claimed_exp_std_adjust_wiped_by_camera_reset: bool = False,
    ael_w_shutter: str = P381_AEL_W_SHUTTER_DEFAULT,
    expect_ael_w_shutter_in_movie_or_sq: bool = False,
    claimed_ael_w_shutter_wiped_by_camera_reset: bool = False,
    spot_metering_point: str = P381_SPOT_METERING_POINT_DEFAULT,
    spot_metering_focus_area: str = "Spot: M",
    spot_metering_linked_areas_exposed: Tuple[str, ...] = P381_SPOT_METERING_LINKED_EXACT_8_AREAS,
    spot_metering_center_locked_areas_exposed: Tuple[str, ...] = P381_SPOT_METERING_CENTER_LOCKED_EXACT_6_AREAS,
    expect_spot_metering_follows_moving_tracking_subject: bool = False,
    claimed_g116_center_locked_only_3_omitting_tracking: bool = False,
    fx6_ae_level_ev: float = 0.0,
    claimed_fx6_has_ae_shift_menu: bool = False,
    fx6_agc_limit_db: int = 18,
    fx6_agc_iso_groups: int = P381_FX6_AGC_ISO_GROUP_COUNT,
    view_mode: str = P381_VIEW_MODE_DEFAULT,
    view_mode_options_exposed: Tuple[str, ...] = P381_VIEW_MODE_EXACT_3_STATES,
    dormant_xavc_codec_view_mode_requested: bool = False,
    display_rotation: str = P381_DISPLAY_ROTATION_DEFAULT,
    display_rotation_bkid_typo: str = P381_DISPLAY_ROTATION_BKID_TYPO,
    claimed_display_rotation_default_is_off: bool = False,
    image_index: str = P381_IMAGE_INDEX_DEFAULT,
    dormant_image_index_12_or_30_requested: bool = False,
    display_as_group: str = P381_DISPLAY_AS_GROUP_DEFAULT,
    enlarge_initial_mag: str = P381_ENLARGE_INITIAL_MAG_DEFAULT,
    enlarge_initial_position: str = P381_ENLARGE_INITIAL_POS_DEFAULT,
    claimed_playback_display_options_wiped_by_camera_reset: bool = False,
    protect_menu_items_exposed: Tuple[str, ...] = P381_PROTECT_MENU_EXACT_7_ITEMS,
    claimed_protect_menu_has_single_g114: bool = False,
    protect_write_requested: bool = False,
    rating_write_requested: bool = False,
    rating_stars: int = 0,
    rating_movie_during_recording_requested: bool = False,
    playback_target_slot: int = 2,
    airplane_mode: str = "ON",
    cnct_while_power_off: str = "OFF",
    select_on_cam_and_send_requested: bool = False,
    fx6_clip_flag: str = "OK",
    claimed_fx6_has_5star_rating_or_display_as_group: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_sector_writes: int = 0,
    slot1_data_sector_writes: int = 0,
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
) -> RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport:
    donor = inspect_phase381_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p381_check_group_a_creativelook_softskin_drive_f11_focusbracket_and_interval(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hlg_still_image=hlg_still_image,
        reset_action=reset_action,
        creative_look_slot=creative_look_slot,
        creative_look_nvram_total_keys=creative_look_nvram_total_keys,
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
        expect_creative_look_active_under_lockout=expect_creative_look_active_under_lockout,
        claimed_creative_look_fade_sharpness_clarity_accept_negative=claimed_creative_look_fade_sharpness_clarity_accept_negative,
        claimed_creative_look_resists_camera_reset=claimed_creative_look_resists_camera_reset,
        dormant_soft_skin_effect_requested=dormant_soft_skin_effect_requested,
        claimed_fx3_or_fx6_has_soft_skin_effect=claimed_fx3_or_fx6_has_soft_skin_effect,
        fx6_base_look_user_lut_slots=fx6_base_look_user_lut_slots,
        claimed_fx6_has_creative_look_menu=claimed_fx6_has_creative_look_menu,
        still_drive_mode=still_drive_mode,
        still_drive_modes_exposed=still_drive_modes_exposed,
        cont_speed_tier=cont_speed_tier,
        aperture_f_number=aperture_f_number,
        expect_hi_plus_live_view=expect_hi_plus_live_view,
        expect_af_tracks_all_frames_above_f11=expect_af_tracks_all_frames_above_f11,
        claimed_af_lock_threshold_is_f8=claimed_af_lock_threshold_is_f8,
        claimed_drive_mode_resists_camera_reset=claimed_drive_mode_resists_camera_reset,
        drive_media_bus=drive_media_bus,
        cfexpress_buffer_min_images=cfexpress_buffer_min_images,
        ev_bracket_step_ev=ev_bracket_step_ev,
        ev_bracket_shot_count=ev_bracket_shot_count,
        ev_bracket_combos_exposed=ev_bracket_combos_exposed,
        dormant_focus_bracket_requested=dormant_focus_bracket_requested,
        claimed_fx3_or_fx6_exposes_focus_bracket=claimed_fx3_or_fx6_exposes_focus_bracket,
        claimed_g151_fx6_focus_bracket_full_scan_is_56=claimed_g151_fx6_focus_bracket_full_scan_is_56,
        interval_items_exposed=interval_items_exposed,
        interval_shutter_type=interval_shutter_type,
        claimed_interval_shutter_name_is_legacy_silent_shoot=claimed_interval_shutter_name_is_legacy_silent_shoot,
        claimed_interval_resists_camera_reset=claimed_interval_resists_camera_reset,
        claimed_interval_in_camera_movie_synthesis=claimed_interval_in_camera_movie_synthesis,
        fx6_special_rec_modes=fx6_special_rec_modes,
        dormant_fx6_frame_rec_requested=dormant_fx6_frame_rec_requested,
        claimed_fx6_has_frame_rec=claimed_fx6_has_frame_rec,
    )

    gb = evaluate_p381_check_group_b_usbpd_11pmic_dcc1_powersave_fx3_vs_fx3a_and_remotes(
        camera_revision=camera_revision,
        reset_action=reset_action,
        libusbbuspower_bytes=libusbbuspower_bytes,
        pmic_kmods_exposed=pmic_kmods_exposed,
        usb_power_supply=usb_power_supply,
        usb_power_profile=usb_power_profile,
        usb_power_terminal=usb_power_terminal,
        np_fz100_inserted=np_fz100_inserted,
        dc_c1_pd_watts=dc_c1_pd_watts,
        dc_c1_cable_amps=dc_c1_cable_amps,
        expect_on_state_battery_charging=expect_on_state_battery_charging,
        off_state_charging_active=off_state_charging_active,
        off_charge_pd_watts=off_charge_pd_watts,
        ambient_temp_c=ambient_temp_c,
        expect_5v_1_5a_sustains_4k_recording=expect_5v_1_5a_sustains_4k_recording,
        hot_pull_np_fz100_requested=hot_pull_np_fz100_requested,
        claimed_hot_pull_runs_poweroff_and_fsync=claimed_hot_pull_runs_poweroff_and_fsync,
        claimed_usb_power_supply_wiped_by_camera_reset=claimed_usb_power_supply_wiped_by_camera_reset,
        fx6_dc_in_voltage_v=fx6_dc_in_voltage_v,
        fx6_hot_replug_dc_in_during_rec=fx6_hot_replug_dc_in_during_rec,
        claimed_fx6_supports_usbc_power_supply=claimed_fx6_supports_usbc_power_supply,
        power_setting_option_items=power_setting_option_items,
        power_save_start_time=power_save_start_time,
        dormant_power_save_time_requested=dormant_power_save_time_requested,
        auto_power_off_temp=auto_power_off_temp,
        handheld_bare_skin_operation=handheld_bare_skin_operation,
        expect_high_temp_safe_handheld=expect_high_temp_safe_handheld,
        power_save_bypasses_exposed=power_save_bypasses_exposed,
        claimed_power_setting_option_wiped_by_camera_reset=claimed_power_setting_option_wiped_by_camera_reset,
        dormant_power_save_by_monitor_requested=dormant_power_save_by_monitor_requested,
        ir_remote_ctrl=ir_remote_ctrl,
        bluetooth_rmt_ctrl=bluetooth_rmt_ctrl,
        nfc_requested=nfc_requested,
        claimed_fx3a_has_ir_or_nfc=claimed_fx3a_has_ir_or_nfc,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        fx6_wired_remote_ports=fx6_wired_remote_ports,
        claimed_fx6_has_ble_or_ir_remote=claimed_fx6_has_ble_or_ir_remote,
    )

    gc = evaluate_p381_check_group_c_mymenu42_fn12_focusmode_5vs2_subjshift5_and_focuslimit14(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        my_menu_pages=my_menu_pages,
        my_menu_items_per_page=my_menu_items_per_page,
        my_menu_total_slots=my_menu_total_slots,
        my_menu_ops_exposed=my_menu_ops_exposed,
        display_from_my_menu=display_from_my_menu,
        claimed_mymenu_capacity_30_or_36_g98=claimed_mymenu_capacity_30_or_36_g98,
        mymenu_add_playback_item_requested=mymenu_add_playback_item_requested,
        claimed_mymenu_wiped_by_camera_reset=claimed_mymenu_wiped_by_camera_reset,
        camset_operation=camset_operation,
        camset_target_slot=camset_target_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=slot1_sector_writes,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        fn_menu_active_slots=fn_menu_active_slots,
        fn_menu_all_not_set_requested=fn_menu_all_not_set_requested,
        claimed_fn_menu_has_follow_custom=claimed_fn_menu_has_follow_custom,
        claimed_fn_menu_wiped_by_camera_reset=claimed_fn_menu_wiped_by_camera_reset,
        claimed_xlr_h1_has_fn_menu_or_rec_keys=claimed_xlr_h1_has_fn_menu_or_rec_keys,
        fx6_user_menu_max_items=fx6_user_menu_max_items,
        claimed_fx6_user_menu_lock_in_all_file_or_fn12=claimed_fx6_user_menu_lock_in_all_file_or_fn12,
        focus_mode=focus_mode,
        lens_pdaf_supported=lens_pdaf_supported,
        lens_is_e_mount=lens_is_e_mount,
        af_w_shutter=af_w_shutter,
        pre_af=pre_af,
        still_af_tracking_sensitivity=still_af_tracking_sensitivity,
        movie_af_transition_speed=movie_af_transition_speed,
        movie_af_subj_shift_sensitivity=movie_af_subj_shift_sensitivity,
        movie_af_subj_shift_responsice_symbol=movie_af_subj_shift_responsice_symbol,
        claimed_movie_af_subj_shift_default_is_3=claimed_movie_af_subj_shift_default_is_3,
        claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset=claimed_af_w_shutter_or_pre_af_wiped_by_camera_reset,
        focus_area_limit_items_exposed=focus_area_limit_items_exposed,
        focus_area_limit_checked_count=focus_area_limit_checked_count,
        circ_of_focus_point=circ_of_focus_point,
        expect_diagonal_focus_circulation=expect_diagonal_focus_circulation,
        claimed_circ_wiped_by_camera_reset=claimed_circ_wiped_by_camera_reset,
        fx6_face_eye_af_mode=fx6_face_eye_af_mode,
        claimed_fx6_has_still_af_s_afa_dmf_or_pre_af=claimed_fx6_has_still_af_s_afa_dmf_or_pre_af,
    )

    gd = evaluate_p381_check_group_d_expcomp_expstd5_spot8vs6_playback_slot1_zerorf_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        exposure_comp_ev=exposure_comp_ev,
        expect_exposure_comp_active_under_lockout=expect_exposure_comp_active_under_lockout,
        exposure_step=exposure_step,
        shutter_mode=shutter_mode,
        expect_exposure_step_alters_shutter_angle=expect_exposure_step_alters_shutter_angle,
        claimed_exposure_step_wiped_by_camera_reset=claimed_exposure_step_wiped_by_camera_reset,
        exposure_std_adjust_modes_exposed=exposure_std_adjust_modes_exposed,
        exposure_std_adjust_mode=exposure_std_adjust_mode,
        exposure_std_adjust_sixths=exposure_std_adjust_sixths,
        claimed_exp_std_adjust_only_4_modes_missing_highlight=claimed_exp_std_adjust_only_4_modes_missing_highlight,
        claimed_exp_std_adjust_wiped_by_camera_reset=claimed_exp_std_adjust_wiped_by_camera_reset,
        ael_w_shutter=ael_w_shutter,
        expect_ael_w_shutter_in_movie_or_sq=expect_ael_w_shutter_in_movie_or_sq,
        claimed_ael_w_shutter_wiped_by_camera_reset=claimed_ael_w_shutter_wiped_by_camera_reset,
        spot_metering_point=spot_metering_point,
        spot_metering_focus_area=spot_metering_focus_area,
        spot_metering_linked_areas_exposed=spot_metering_linked_areas_exposed,
        spot_metering_center_locked_areas_exposed=spot_metering_center_locked_areas_exposed,
        expect_spot_metering_follows_moving_tracking_subject=expect_spot_metering_follows_moving_tracking_subject,
        claimed_g116_center_locked_only_3_omitting_tracking=claimed_g116_center_locked_only_3_omitting_tracking,
        fx6_ae_level_ev=fx6_ae_level_ev,
        claimed_fx6_has_ae_shift_menu=claimed_fx6_has_ae_shift_menu,
        fx6_agc_limit_db=fx6_agc_limit_db,
        fx6_agc_iso_groups=fx6_agc_iso_groups,
        view_mode=view_mode,
        view_mode_options_exposed=view_mode_options_exposed,
        dormant_xavc_codec_view_mode_requested=dormant_xavc_codec_view_mode_requested,
        display_rotation=display_rotation,
        display_rotation_bkid_typo=display_rotation_bkid_typo,
        claimed_display_rotation_default_is_off=claimed_display_rotation_default_is_off,
        image_index=image_index,
        dormant_image_index_12_or_30_requested=dormant_image_index_12_or_30_requested,
        display_as_group=display_as_group,
        enlarge_initial_mag=enlarge_initial_mag,
        enlarge_initial_position=enlarge_initial_position,
        claimed_playback_display_options_wiped_by_camera_reset=claimed_playback_display_options_wiped_by_camera_reset,
        protect_menu_items_exposed=protect_menu_items_exposed,
        claimed_protect_menu_has_single_g114=claimed_protect_menu_has_single_g114,
        protect_write_requested=protect_write_requested,
        rating_write_requested=rating_write_requested,
        rating_stars=rating_stars,
        rating_movie_during_recording_requested=rating_movie_during_recording_requested,
        playback_target_slot=playback_target_slot,
        airplane_mode=airplane_mode,
        cnct_while_power_off=cnct_while_power_off,
        select_on_cam_and_send_requested=select_on_cam_and_send_requested,
        fx6_clip_flag=fx6_clip_flag,
        claimed_fx6_has_5star_rating_or_display_as_group=claimed_fx6_has_5star_rating_or_display_as_group,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_sector_writes=slot1_sector_writes,
        slot1_data_sector_writes=slot1_data_sector_writes,
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
            P381_GO_NO_GO_BLOCKED_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_FAILURE
        )
        overall_status = go_no_go
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P381_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = (
            P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED
        )
        overall_status = go_no_go

    report = RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport(
        schema_version=P381_SCHEMA,
        phase_version=P381_VERSION,
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
        h0_h3_surface_count=P381_STORAGE_SURFACE_COUNT,
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
        fx3_soft_skin_effect_supported=False,
        fx3_focus_bracket_supported=False,
        fx6_frame_rec_supported=False,
        fx3_power_save_by_monitor_supported=False,
        fx3a_ir_or_nfc_supported=False,
        fx3_fn_menu_follow_custom_supported=False,
        fx6_ae_shift_menu_supported=False,
        emmc_write_count=PHASE381_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE381_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=PHASE381_E_ND_I2C_TX_BYTES,
        rf_tx_packets=PHASE381_RF_TX_PACKETS,
        rf_packets_transmitted=PHASE381_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE381_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=PHASE381_RF_NVS_MUTATION_BYTES,
        slot1_sector_writes=PHASE381_SLOT1_SECTOR_WRITES,
        slot1_data_sector_writes=PHASE381_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE381_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE381_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE381_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport(
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


def run_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
    **kwargs: Any,
) -> RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport:
    return evaluate_realhw_creativelook_drive_usbpd_powersave_mymenu42_fn12_focus_expstd_and_playback_preflight(
        **kwargs
    )


def verify_phase381_report(
    payload: Union[
        Mapping[str, Any],
        RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport,
    ],
) -> Phase381ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P381_SCHEMA:
        errors.append(
            f"schema_version mismatch: {payload.get('schema_version')!r} != {P381_SCHEMA!r}"
        )
    if payload.get("sony_help_guide_id") != P381_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_381_VALID_GO_NO_GO_VALUES:
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
        "fx3_soft_skin_effect_supported",
        "fx3_focus_bracket_supported",
        "fx6_frame_rec_supported",
        "fx3_power_save_by_monitor_supported",
        "fx3a_ir_or_nfc_supported",
        "fx3_fn_menu_follow_custom_supported",
        "fx6_ae_shift_menu_supported",
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
        P381_GO_NO_GO_CREATIVELOOK_DRIVE_USBPD_POWERSAVE_MYMENU42_FN12_FOCUS_EXPSTD_AND_PLAYBACK_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase381ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase381_markdown(
    report: RealHwCreativeLookDriveUsbPdPowerSaveMyMenu42Fn12FocusExpStdAndPlaybackReport,
) -> str:
    lines = [
        f"# Phase 381 — 26th Physical Bench Readiness Preflight (`26/26`, Waves 83-84, `{report.schema_version}`)",
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
        f"`slot1_data_sector_writes={report.slot1_data_sector_writes}`, "
        f"`raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"creative_look=`{report.check_group_a.effective_creative_look}` ({report.check_group_a.creative_look_nvram_total_keys} NVRAM keys), "
        f"drive=`{report.check_group_a.still_drive_mode}` (hi+={report.check_group_a.cont_speed_max_fps}fps, af_lock_f11={report.check_group_a.cont_af_locked_first_frame}), "
        f"ev_combos={report.check_group_a.ev_bracket_combo_count}, focus_bracket={report.check_group_a.fx3_focus_bracket_supported}, "
        f"fx6_frame_rec={report.check_group_a.fx6_frame_rec_supported}",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"rev=`{report.check_group_b.camera_revision}`, pmic_kmods={len(report.check_group_b.pmic_kmods_exposed)}, "
        f"usb_profile=`{report.check_group_b.usb_power_profile}`, "
        f"power_save_bypasses={report.check_group_b.power_save_bypass_count}, "
        f"ir_present={report.check_group_b.ir_receiver_present}",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"mymenu={report.check_group_c.my_menu_pages}x{report.check_group_c.my_menu_items_per_page}={report.check_group_c.my_menu_total_slots}, "
        f"fn={report.check_group_c.fn_menu_still_slots}+{report.check_group_c.fn_menu_movie_slots}, "
        f"focus_mode=`{report.check_group_c.focus_mode}`, "
        f"subj_shift=`{report.check_group_c.movie_af_subj_shift_sensitivity}`, "
        f"focus_limit={report.check_group_c.focus_area_limit_checked_count}/14",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"exp_step=`{report.check_group_d.exposure_step}`, "
        f"exp_std_modes={len(report.check_group_d.exposure_std_adjust_modes_exposed)}, "
        f"spot_8v6={len(report.check_group_d.spot_metering_linked_areas)}/{len(report.check_group_d.spot_metering_center_locked_areas)}, "
        f"view_mode=`{report.check_group_d.view_mode}`, "
        f"rot=`{report.check_group_d.display_rotation}`, "
        f"protect_items={len(report.check_group_d.protect_menu_items_exposed)}, "
        f"airplane=`{report.check_group_d.airplane_mode}`, "
        f"slot1_mut={report.check_group_d.slot1_tier0_vault_mutated}",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
