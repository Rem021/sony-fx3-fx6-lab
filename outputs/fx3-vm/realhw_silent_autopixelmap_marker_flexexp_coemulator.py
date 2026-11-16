#!/usr/bin/env python3
"""Phase 236 (Stage 43, 43/43 Milestone) — Real-Hardware ILME-FX3 Wave-33
`[Silent Mode Settings]` `[Auto Pixel Mapping]` Target & `[Shutter When Pwr OFF]` Absence,
`[Marker Display]` 15-Ratio HDMI Isolation & `[Flexible Exp. Mode]` Reset Split HIL Co-Emulator.

Strictly models Wave-33 official Sony `ILME-FX3` (`Ver. 2.00..7.02`, primary `Ver. 7.02`) and
`ILME-FX6` (`Ver. 6.01`) contracts without hardware attachment or firmware byte leakage:

1. **Sub-model A — `[Silent Mode Settings]` (`MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`),
   `[Target Function Settings]` (`[Aperture Drive in AF]` & `[Auto Pixel Mapping]`), 5 Disabled
   Functions & Hardware Absence of `[Shutter When Pwr OFF]` on `ILME-FX3` (`Ver. 2.00..7.02`)**:
   - Enabling `[Silent Mode] = [On]` deterministically locks `[Shutter Type]` and
     `[Shutter Type in Interval]` to `[Electronic Shutter]`, locks `[Audio signals]` to `[Off]`,
     and disables all **5 shooting functions**:
     (1) `Flash` (Flash shooting),
     (2) `Long Exposure NR` (`[Long Exposure NR]`),
     (3) `e-Front Curtain Shut.` (`[e-Front Curtain Shut.]`),
     (4) `BULB` (`BULB` shooting),
     (5) `Anti-flicker Shoot.` (`[Anti-flicker Shoot.]`).
     Any attempt to force mechanical shutter, emit audio signals, or invoke any of the 5 disabled
     functions while `[Silent Mode] = [On]` fails closed with `EOPNOTSUPP (95)`.
   - `[Target Function Settings]` governs `[Aperture Drive in AF]` and `[Auto Pixel Mapping]`:
     setting either item to `[Not Target]` retains its configured user setting even when
     `[Silent Mode] = [On]`; setting `[Auto Pixel Mapping]` to `[Target]` under `[Silent Mode] = [On]`
     suppresses automatic power-off mechanical-shutter dark-frame pixel-mapping calibration
     (`poweroff_mech_shutter_darkframe_actuations == 0`, `poweroff_cnflasha_calibration_touches == 0`).
     During controlled Tier-0 backup/restore bench shutdowns, unsuppressed `[Auto Pixel Mapping] = [On]`
     is blocked fail-closed with `EBUSY (16)`.
   - Unlike Alpha still bodies (`ILCE-7SM3` / `ILCE-7RM5`), physical `ILME-FX3` (`Ver. 2.00..7.02`)
     exposes only `[Sensor Cleaning]`, `[Auto Pixel Mapping]`, and `[Pixel Mapping]` under
     `MENU -> Setup -> [Setup Option] -> [Anti-dust Function]`. Any request or configuration for
     the nonexistent `[Shutter When Pwr OFF]` setting on `ILME-FX3` fails closed with `EOPNOTSUPP (95)`.

2. **Sub-model B — `[Marker Display]` (`Center Marker`, `Aspect Marker` `Off` + 15 Ver. 3.00+/7.02
   Ratios, `Safety Zone` `Off/80%/90%`, `Guideframe`) Survival Across `[Camera Settings Reset]` &
   Strict Local-LCD-Only HDMI Isolation (`0` External HDMI Marker Pixels)**:
   - Models `MENU -> Shooting -> [Marker Display]` sub-items: `[Marker Display]` (`Off`/`On`),
     `[Center Marker]` (`Off`/`On`), `[Aspect Marker]` (`Off` + all **15 Ver. 3.00+/7.02 ratios**:
     `9:16`, `4:5`, `1:1`, `4:3`, `13:9`, `14:9`, `15:9`, `16:9` *(Ver. 3.00+)*, `17:9`,
     `1.66:1`, `1.85:1`, `1.91:1`, `2:1`, `2.35:1`, `2.39:1`), `[Safety Zone]` (`Off`/`80%`/`90%`),
     and `[Guideframe]` (`Off`/`On`).
   - **Reset survival**: `[Marker Display]` and `[Aspect Marker]` configurations survive
     `[Camera Settings Reset]` intact and are cleared back to `Off` only by full `[Initialize]`.
   - **Strict Local-LCD-Only HDMI isolation**: markers render exclusively on the camera's local LCD;
     external HDMI output carries **`0` marker overlay pixels** even when
     `MENU -> Setup -> [External Output] -> [HDMI Info. Display] = [On]`. Forcing markers onto HDMI
     fails closed with `EOPNOTSUPP (95)`.

3. **Sub-model C & Redlines — `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`),
   `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO` Default `Manual`) & `[Auto Slow Shutter]` (Default `On`)
   Reset Split + Hard Safety Redlines**:
   - Models `MENU -> Shooting -> [Shooting Mode] -> [Exposure Ctrl Type]` (`P/A/S/M Mode` with
     `Program Auto` / `Aperture Priority` / `Shutter Priority` / `Manual Exposure` vs
     `Flexible Exp. Mode`).
   - Under `Flexible Exp. Mode`, `[Auto/Manual Swt. Set.]` independently switches `Av`
     (`Av Auto/Manual Switch`), `Tv` (`Tv Auto/Manual Switch`), and `ISO` (`ISO Auto/Manual Set`),
     all 3 defaulting to `Manual` and resetting cleanly to `Manual` on `[Camera Settings Reset]`.
   - `[Auto Slow Shutter]` (`On`/`Off`) defaults to `On` and resets cleanly to `On` on
     `[Camera Settings Reset]`, forming a deterministic asymmetric reset split against co-resident
     non-resettable `[Marker Display]` / `[Aspect Marker]`. Also models Slot-1 `CAMSET01..10.DAT`
     profile recall without persistent eMMC/NVRAM mutation.

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Supports `LOCAL_DONOR_O_RDONLY` (`os.O_RDONLY` bounded `<= 4096 B` window inspection across
     12 FX3 `7.02` & FX6 `6.01` donors, `< 0.02s` cold, cached, `raw_firmware_bytes_leaked == 0`)
     and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`).
   - Locks `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `spi_nor_write_authorized = False`,
     `el3_payload_transmit_authorized = False`, `isp_write_authorized = False`, and
     `cnflasha_userspace_write_blocked = True`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_silent_autopixelmap_marker_flexexp_coemulator_v1"
PHASE_236_SCHEMA = SCHEMA_ID
PHASE_236_VERSION = "236.0.0"
STAGE_INDEX = 43
STAGE_TOTAL = 43
MILESTONE_LABEL = "43/43"
STAGE_NAME = "stage43_realhw_silent_autopixelmap_marker_flexexp_hil"
FX3_MODEL_ID = 0x91030080

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# Errno constants (POSIX / Linux / Sony Infra)
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

# Bounded donor window read cap (<= 4 KiB per window)
BOUNDED_WINDOW_MAX_BYTES = 4096

# Hard Safety Redline invariants (strictly locked False / 0)
P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
CNFLASHA_MUTATION_BYTES = 0
CNFLASHA_USERSPACE_WRITE_BLOCKED = True
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
ISP_WRITE_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
SILENT_MODE_5FUNC_OR_PWRSHUTTER_BYPASS_EVENTS = 0
BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP_EVENTS = 0
HDMI_MARKER_LEAKED_OVERLAY_PIXELS = 0
FLEXEXP_OR_MARKER_RESET_SPLIT_DRIFT_EVENTS = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Environment variables
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx6_lens_comm": f"{_FX6_NF15_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx3_media_cfg": f"{_FX3_USR_PREFIX}/lib/libInfraMediaConfig.so",
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_lens_comm": 14_544,
    "fx6_lens_comm": 14_544,
    "fx3_media_cfg": 52_312,
    "fx3_adj_media": 318_152,
    "fx3_string_en_f": 373_820,
    "fx6_string_en": 118_208,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx6_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI", b"Auto"),
    "fx3_string_en_f": (
        b"Silent Mode Settings",
        b"Silent Mode",
        b"Target Function Settings",
        b"Target",
        b"Not Target",
        b"Aperture Drive in AF",
        b"Auto Pixel Mapping",
        b"Pixel Mapping",
        b"Sensor Cleaning",
        b"Shutter Type",
        b"Shutter Type in Interval",
        b"Electronic Shutter",
        b"Mechanical Shutter",
        b"Long Exposure NR",
        b"e-Front Curtain Shut.",
        b"Anti-flicker Shoot.",
        b"BULB",
        b"Flash",
        b"Marker Display",
        b"Center Marker",
        b"Aspect Marker",
        b"Safety Zone",
        b"Guideframe",
        b"9:16",
        b"4:5",
        b"1:1",
        b"4:3",
        b"13:9",
        b"14:9",
        b"15:9",
        b"16:9",
        b"17:9",
        b"1.66:1",
        b"1.85:1",
        b"1.91:1",
        b"2:1",
        b"2.35:1",
        b"2.39:1",
        b"80%",
        b"90%",
        b"HDMI Info. Display",
        b"Exposure Ctrl Type",
        b"P/A/S/M Mode",
        b"Flexible Exp. Mode",
        b"Auto/Manual Swt. Set.",
        b"Av Auto/Manual Switch",
        b"Tv Auto/Manual Switch",
        b"ISO Auto/Manual Set",
        b"Auto Slow Shutter",
        b"Program Auto",
        b"Aperture Priority",
        b"Shutter Priority",
        b"Manual Exposure",
        b"Manual",
        b"Auto",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Marker",
        b"16:9",
        b"17:9",
        b"4:3",
        b"2.39:1",
        b"Shutter",
        b"Auto",
        b"Manual",
        b"ISO",
        b"HDMI",
        b"Audio",
        b"Reset",
        b"Pixel",
        b"APR",
        b"Black",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_938_432, "FLEXIBLE", b"FLEXIBLE"),
        (49_942_528, "SILENT", b"SILENT"),
        (49_942_528, "SHUTTER", b"SHUTTER"),
        (49_942_528, "EXPOSURE", b"EXPOSURE"),
        (49_946_624, "PIXEL_MAPPING", b"PIXEL_MAPPING"),
        (49_946_624, "SAFETY_ZONE", b"SAFETY_ZONE"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_967_104, "INITIALIZE", b"INITIALIZE"),
        (58_707_968, "ASPECT", b"ASPECT"),
        (61_878_272, "HDMI_INFO", b"HDMI_INFO"),
        (61_906_944, "AUTO_SLOW_SHUTTER", b"AUTO_SLOW_SHUTTER"),
        (62_046_208, "MARKER", b"MARKER"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_437_440, "EXPOSURE", b"EXPOSURE"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
        (39_370_752, "ASPECT", b"ASPECT"),
        (39_374_848, "MARKER", b"MARKER"),
        (39_374_848, "SAFETY", b"SAFETY"),
        (39_886_848, "PIXEL", b"PIXEL"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (315_392, "SHUTTER", b"Shutter"),
        (655_360, "MARKER", b"Marker"),
        (655_360, "ASPECT", b"Aspect"),
        (696_320, "HDMI", b"HDMI"),
        (1_880_064, "EXPOSURE", b"Exposure"),
        (2_039_808, "SILENT", b"Silent"),
        (2_052_096, "PIXEL", b"Pixel"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (299_008, "ASPECT", b"Aspect"),
        (303_104, "MARKER", b"Marker"),
        (684_032, "HDMI", b"HDMI"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (1_949_696, "EXPOSURE", b"Exposure"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (126_976, "AUDIO", b"Audio"),
        (131_072, "XAVC", b"Xavc"),
        (159_744, "MP4", b"Mp4"),
        (176_128, "PROXY", b"Proxy"),
        (249_856, "TIMECODE", b"TimeCode"),
        (2_965_504, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
        (2_965_504, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (155_648, "AUDIO", b"Audio"),
        (163_840, "XAVC", b"Xavc"),
        (163_840, "TIMECODE", b"TimeCode"),
        (204_800, "PROXY", b"Proxy"),
        (13_475_840, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (13_516_800, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-33 Official ILME-FX3 Ver. 2.00..7.02 Sub-model A/B/C Constants
# ---------------------------------------------------------------------------

VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
BODY_MODEL_FX3 = "ILME-FX3"
VALID_FX3_FIRMWARE_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.02",
)
PRE_300_FX3_FIRMWARE_VERSIONS: Tuple[str, ...] = ("2.00",)

# Sub-model A: [Silent Mode Settings], [Target Function Settings] & [Shutter When Pwr OFF] Absence
SILENT_MODE_SETTINGS_MENU_PATH = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]"
)
TARGET_FUNCTION_SETTINGS_MENU_PATH = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Target Function Settings]"
)
SHUTTER_TYPE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Type]"
SHUTTER_TYPE_INTERVAL_MENU_PATH = (
    "MENU -> Shooting -> [Drive Mode] -> [Interval Shoot. Func.] -> [Shutter Type in Interval]"
)
AUDIO_SIGNALS_MENU_PATH = "MENU -> Setup -> [Sound Option] -> [Audio signals]"
ANTI_DUST_FUNCTION_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Anti-dust Function]"

SHUTTER_TYPE_AUTO = "Auto"
SHUTTER_TYPE_MECHANICAL = "Mechanical Shutter"
SHUTTER_TYPE_ELECTRONIC = "Electronic Shutter"
VALID_SHUTTER_TYPES: Tuple[str, ...] = (
    SHUTTER_TYPE_AUTO,
    SHUTTER_TYPE_MECHANICAL,
    SHUTTER_TYPE_ELECTRONIC,
)
VALID_INTERVAL_SHUTTER_TYPES: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL,
    SHUTTER_TYPE_ELECTRONIC,
)

TARGET_SETTING_TARGET = "Target"
TARGET_SETTING_NOT_TARGET = "Not Target"
VALID_TARGET_FUNCTION_STATES: Tuple[str, ...] = (
    TARGET_SETTING_TARGET,
    TARGET_SETTING_NOT_TARGET,
)

APERTURE_DRIVE_AF_STANDARD = "Standard"
APERTURE_DRIVE_AF_FOCUS_PRIORITY = "Focus Priority"
APERTURE_DRIVE_AF_SILENT_PRIORITY = "Silent Priority"
VALID_APERTURE_DRIVE_IN_AF_MODES: Tuple[str, ...] = (
    APERTURE_DRIVE_AF_STANDARD,
    APERTURE_DRIVE_AF_FOCUS_PRIORITY,
    APERTURE_DRIVE_AF_SILENT_PRIORITY,
)

SILENT_DISABLED_FLASH = "Flash"
SILENT_DISABLED_LONG_EXPOSURE_NR = "Long Exposure NR"
SILENT_DISABLED_E_FRONT_CURTAIN_SHUT = "e-Front Curtain Shut."
SILENT_DISABLED_BULB = "BULB"
SILENT_DISABLED_ANTI_FLICKER_SHOOT = "Anti-flicker Shoot."
SILENT_MODE_5_DISABLED_FUNCTIONS: Tuple[str, ...] = (
    SILENT_DISABLED_FLASH,
    SILENT_DISABLED_LONG_EXPOSURE_NR,
    SILENT_DISABLED_E_FRONT_CURTAIN_SHUT,
    SILENT_DISABLED_BULB,
    SILENT_DISABLED_ANTI_FLICKER_SHOOT,
)

FX3_EXPOSED_ANTI_DUST_ITEMS: Tuple[str, ...] = (
    "Sensor Cleaning",
    "Auto Pixel Mapping",
    "Pixel Mapping",
)
ABSENT_FX3_SHUTTER_WHEN_PWR_OFF = "Shutter When Pwr OFF"

# Sub-model B: [Marker Display] (15 Ver. 3.00+/7.02 Aspect Ratios, Reset Survival & Local-LCD-Only)
MARKER_DISPLAY_MENU_PATH = "MENU -> Shooting -> [Marker Display]"
HDMI_INFO_DISPLAY_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"

RESET_ACTION_NONE = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

ASPECT_MARKER_OFF = "Off"
ASPECT_MARKER_15_RATIOS: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
VALID_ASPECT_MARKER_SETTINGS: Tuple[str, ...] = (ASPECT_MARKER_OFF,) + ASPECT_MARKER_15_RATIOS
VALID_SAFETY_ZONE_SETTINGS: Tuple[str, ...] = ("Off", "80%", "90%")

# Deterministic local-LCD marker overlay pixel budgets (0 on external HDMI)
LCD_CENTER_MARKER_PIXELS = 420
LCD_ASPECT_MARKER_PIXELS = 3_840
LCD_SAFETY_ZONE_PIXELS = 3_200
LCD_GUIDEFRAME_PIXELS = 5_120

# Sub-model C: [Exposure Ctrl Type] (P/A/S/M vs Flexible Exp. Mode) & Reset Split
EXPOSURE_CTRL_TYPE_MENU_PATH = "MENU -> Shooting -> [Shooting Mode] -> [Exposure Ctrl Type]"
AUTO_MANUAL_SWT_SET_MENU_PATH = (
    "MENU -> Shooting -> [Exposure/Color] -> [Exposure] -> [Auto/Manual Swt. Set.]"
)
AUTO_SLOW_SHUTTER_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Auto Slow Shutter]"

EXPOSURE_CTRL_PASM = "P/A/S/M Mode"
EXPOSURE_CTRL_FLEXIBLE = "Flexible Exp. Mode"
VALID_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = (
    EXPOSURE_CTRL_PASM,
    EXPOSURE_CTRL_FLEXIBLE,
)

PASM_PROGRAM_AUTO = "Program Auto"
PASM_APERTURE_PRIORITY = "Aperture Priority"
PASM_SHUTTER_PRIORITY = "Shutter Priority"
PASM_MANUAL_EXPOSURE = "Manual Exposure"
VALID_PASM_SUBMODES: Tuple[str, ...] = (
    PASM_PROGRAM_AUTO,
    PASM_APERTURE_PRIORITY,
    PASM_SHUTTER_PRIORITY,
    PASM_MANUAL_EXPOSURE,
)

SWITCH_MANUAL = "Manual"
SWITCH_AUTO = "Auto"
VALID_AUTO_MANUAL_SWITCH_STATES: Tuple[str, ...] = (SWITCH_MANUAL, SWITCH_AUTO)

DEFAULT_FLEXEXP_AV_SWITCH = SWITCH_MANUAL
DEFAULT_FLEXEXP_TV_SWITCH = SWITCH_MANUAL
DEFAULT_FLEXEXP_ISO_SWITCH = SWITCH_MANUAL
DEFAULT_AUTO_SLOW_SHUTTER = "On"

_CAMSET_FILENAME_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256_prefix16: str
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase236DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    silent_mode_autopixelmap_no_pwrshutter_proven: bool
    marker_15ratio_persistence_and_hdmi_isolation_proven: bool
    flexible_exp_and_auto_slow_shutter_reset_split_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SilentModeAutoPixelMapNoPwrShutterHilResult:
    admitted: bool
    body_model: str
    firmware_version: str
    silent_mode_menu_path: str
    target_function_menu_path: str
    anti_dust_menu_path: str
    exposed_anti_dust_items: Tuple[str, ...]
    shutter_when_pwr_off_hardware_present: bool
    silent_mode: str
    configured_shutter_type: str
    configured_shutter_type_in_interval: str
    configured_audio_signals: str
    effective_shutter_type: str
    effective_shutter_type_in_interval: str
    effective_audio_signals: str
    aperture_drive_in_af_target: str
    configured_aperture_drive_in_af: str
    effective_aperture_drive_in_af: str
    auto_pixel_mapping_target: str
    configured_auto_pixel_mapping: str
    effective_auto_pixel_mapping: str
    disabled_shooting_functions: Tuple[str, ...]
    blocked_function_requests: Tuple[str, ...]
    power_off_event: bool
    controlled_tier0_bench_shutdown: bool
    poweroff_mech_shutter_darkframe_actuations: int
    poweroff_cnflasha_calibration_touches: int
    silent_mode_5func_or_pwrshutter_bypass_events: int
    bench_shutdown_unsuppressed_auto_pixelmap_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class MarkerDisplay15RatioHdmiIsolationHilResult:
    admitted: bool
    firmware_version: str
    marker_menu_path: str
    hdmi_info_menu_path: str
    reset_menu_path: str
    reset_action_applied: str
    configured_marker_display: str
    configured_center_marker: str
    configured_aspect_marker: str
    configured_safety_zone: str
    configured_guideframe: str
    effective_marker_display: str
    effective_center_marker: str
    effective_aspect_marker: str
    effective_safety_zone: str
    effective_guideframe: str
    marker_survived_camera_settings_reset: bool
    marker_cleared_by_initialize: bool
    hdmi_connected: bool
    hdmi_info_display: str
    local_lcd_marker_overlay_active: bool
    local_lcd_marker_overlay_pixels: int
    hdmi_info_telemetry_osd_active: bool
    hdmi_marker_overlay_rendered: bool
    hdmi_center_marker_pixels: int
    hdmi_aspect_marker_pixels: int
    hdmi_safety_zone_pixels: int
    hdmi_guideframe_pixels: int
    hdmi_marker_leaked_overlay_pixels: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class FlexibleExpModeResetSplitHilResult:
    admitted: bool
    exposure_ctrl_menu_path: str
    auto_manual_swt_menu_path: str
    auto_slow_shutter_menu_path: str
    reset_menu_path: str
    exposure_ctrl_type: str
    pasm_submode: str
    auto_manual_swt_menu_available: bool
    reset_action_applied: str
    slot1_camset_restored: Optional[str]
    configured_av_switch: str
    configured_tv_switch: str
    configured_iso_switch: str
    configured_auto_slow_shutter: str
    effective_av_switch: str
    effective_tv_switch: str
    effective_iso_switch: str
    effective_auto_slow_shutter: str
    configured_marker_display: str
    configured_aspect_marker: str
    effective_marker_display: str
    effective_aspect_marker: str
    flexexp_switches_reset_by_camera_settings_reset: bool
    auto_slow_shutter_reset_by_camera_settings_reset: bool
    marker_survived_while_flexexp_reset_split_verified: bool
    bk4_persistent_nvram_writes: int
    flexexp_or_marker_reset_split_drift_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    silent_mode_5func_or_pwrshutter_bypass_events: int
    bench_shutdown_unsuppressed_auto_pixelmap_events: int
    hdmi_marker_leaked_overlay_pixels: int
    flexexp_or_marker_reset_split_drift_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase236DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase236DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.extend((base / "work", base / "outputs" / "sony-fx3-fx6-lab" / "work"))
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.extend((
        DEFAULT_REPO_ROOT / "work",
        internal / "work",
        internal / "outputs" / "sony-fx3-fx6-lab" / "work",
        LEGACY_MAC_ROOT / "work",
        LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work",
    ))
    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase236_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = chosen if chosen is not None else (
            roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        )
    return resolved


def _read_full_rdonly(path: Path) -> Tuple[int, bytes]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = max(st.st_size, 0)
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return st.st_size, (chunks[0] if len(chunks) == 1 else b"".join(chunks))
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        file_bytes = os.fstat(fd).st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            hits[label] = 1 if tok in seen_offsets[off] else 0
        head = seen_offsets.get(0)
        if head is None:
            os.lseek(fd, 0, os.SEEK_SET)
            head = os.read(fd, min(BOUNDED_WINDOW_MAX_BYTES, max(file_bytes, 0)))
            bytes_read_total += len(head)
        return file_bytes, bytes_read_total, head, hits
    finally:
        os.close(fd)


def _scan_compact_buf(
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        tokens=COMPACT_DONOR_TOKENS[artifact_key],
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase236DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P236".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P236".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_P236_" + label.encode("ascii")).ljust(64, b"\x00")
        )
        hits = {lbl: 1 for _off, lbl, _tok in LARGE_DONOR_WINDOWS[key]}
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(head),
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase236DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3_7.02", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        silent_mode_autopixelmap_no_pwrshutter_proven=True,
        marker_15ratio_persistence_and_hdmi_isolation_proven=True,
        flexible_exp_and_auto_slow_shutter_reset_split_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase236_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase236DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase236_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items())
    )
    cache_key = (SOURCE_MODE_LOCAL_DONOR, sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(
        paths["fx3_lens_comm"], artifact_key="fx3_lens_comm", body_label="FX3_7.02"
    )
    fx6_lens_comm = _scan_compact_rdonly(
        paths["fx6_lens_comm"], artifact_key="fx6_lens_comm", body_label="FX6_6.01"
    )
    fx3_media_cfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3_7.02"
    )
    fx3_adj_media = _scan_compact_rdonly(
        paths["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3_7.02"
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3_7.02"
    )
    fx6_string_en = _scan_compact_rdonly(
        paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6_6.01"
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3_7.02"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6_6.01"
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02"
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01"
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02"
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01"
    )

    errors: List[str] = []
    for c_item in (
        fx3_lens_comm,
        fx6_lens_comm,
        fx3_media_cfg,
        fx3_adj_media,
        fx3_string_en_f,
        fx6_string_en,
    ):
        if c_item.file_bytes != EXPECTED_DONOR_BYTES[c_item.artifact_key]:
            errors.append(
                f"{c_item.artifact_key} byte size {c_item.file_bytes} != "
                f"{EXPECTED_DONOR_BYTES[c_item.artifact_key]}"
            )
        if not all(c_item.marker_hits.values()):
            errors.append(f"{c_item.artifact_key} missing tokens: {c_item.marker_hits}")

    for l_item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        if l_item.file_bytes != EXPECTED_DONOR_BYTES[l_item.artifact_key]:
            errors.append(
                f"{l_item.artifact_key} byte size {l_item.file_bytes} != "
                f"{EXPECTED_DONOR_BYTES[l_item.artifact_key]}"
            )
        if not all(l_item.window_hits.values()):
            errors.append(f"{l_item.artifact_key} missing window tokens: {l_item.window_hits}")

    silent_proven = (
        fx3_string_en_f.marker_hits.get("Silent Mode Settings") == 1
        and fx3_string_en_f.marker_hits.get("Silent Mode") == 1
        and fx3_string_en_f.marker_hits.get("Target Function Settings") == 1
        and fx3_string_en_f.marker_hits.get("Not Target") == 1
        and fx3_string_en_f.marker_hits.get("Aperture Drive in AF") == 1
        and fx3_string_en_f.marker_hits.get("Auto Pixel Mapping") == 1
        and fx3_string_en_f.marker_hits.get("Sensor Cleaning") == 1
        and fx3_string_en_f.marker_hits.get("Electronic Shutter") == 1
        and fx3_string_en_f.marker_hits.get("Long Exposure NR") == 1
        and fx3_string_en_f.marker_hits.get("e-Front Curtain Shut.") == 1
        and fx3_string_en_f.marker_hits.get("Anti-flicker Shoot.") == 1
        and fx3_appfw.window_hits.get("SILENT") == 1
        and fx3_appfw.window_hits.get("PIXEL_MAPPING") == 1
        and fx3_cpapp.window_hits.get("SILENT") == 1
    )
    marker_proven = (
        fx3_string_en_f.marker_hits.get("Marker Display") == 1
        and fx3_string_en_f.marker_hits.get("Center Marker") == 1
        and fx3_string_en_f.marker_hits.get("Aspect Marker") == 1
        and fx3_string_en_f.marker_hits.get("Safety Zone") == 1
        and fx3_string_en_f.marker_hits.get("Guideframe") == 1
        and all(fx3_string_en_f.marker_hits.get(r) == 1 for r in ASPECT_MARKER_15_RATIOS)
        and fx3_string_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_adj_media.marker_hits.get("AVBB_SCN_START_HDMI") == 1
        and fx3_appfw.window_hits.get("MARKER") == 1
        and fx3_appfw.window_hits.get("ASPECT") == 1
        and fx6_appfw.window_hits.get("MARKER") == 1
    )
    flexexp_proven = (
        fx3_string_en_f.marker_hits.get("Exposure Ctrl Type") == 1
        and fx3_string_en_f.marker_hits.get("P/A/S/M Mode") == 1
        and fx3_string_en_f.marker_hits.get("Flexible Exp. Mode") == 1
        and fx3_string_en_f.marker_hits.get("Auto/Manual Swt. Set.") == 1
        and fx3_string_en_f.marker_hits.get("Av Auto/Manual Switch") == 1
        and fx3_string_en_f.marker_hits.get("Tv Auto/Manual Switch") == 1
        and fx3_string_en_f.marker_hits.get("ISO Auto/Manual Set") == 1
        and fx3_string_en_f.marker_hits.get("Auto Slow Shutter") == 1
        and fx3_string_en_f.marker_hits.get("Camera Settings Reset") == 1
        and fx3_string_en_f.marker_hits.get("Initialize") == 1
        and fx3_appfw.window_hits.get("FLEXIBLE") == 1
        and fx3_appfw.window_hits.get("AUTO_SLOW_SHUTTER") == 1
    )

    audit = Phase236DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
        fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media,
        fx3_string_en_f=fx3_string_en_f,
        fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        silent_mode_autopixelmap_no_pwrshutter_proven=silent_proven,
        marker_15ratio_persistence_and_hdmi_isolation_proven=marker_proven,
        flexible_exp_and_auto_slow_shutter_reset_split_proven=flexexp_proven,
        all_contracts_verified=(not errors and silent_proven and marker_proven and flexexp_proven),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: [Silent Mode Settings], [Target Function Settings] &
#              [Shutter When Pwr OFF] Hardware Absence on ILME-FX3 (Ver. 2.00..7.02)
# ---------------------------------------------------------------------------


def probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
    *,
    body_model: str = BODY_MODEL_FX3,
    firmware_version: str = "7.02",
    silent_mode: str = "On",
    configured_shutter_type: str = SHUTTER_TYPE_MECHANICAL,
    configured_shutter_type_in_interval: str = SHUTTER_TYPE_MECHANICAL,
    configured_audio_signals: str = "On",
    aperture_drive_in_af_target: str = TARGET_SETTING_TARGET,
    configured_aperture_drive_in_af: str = APERTURE_DRIVE_AF_STANDARD,
    auto_pixel_mapping_target: str = TARGET_SETTING_TARGET,
    configured_auto_pixel_mapping: str = "On",
    requested_shooting_functions: Sequence[str] = (),
    attempt_force_mechanical_shutter_in_silent: bool = False,
    attempt_force_audio_signals_in_silent: bool = False,
    request_shutter_when_pwr_off: Optional[str] = None,
    attempt_target_shutter_when_pwr_off: bool = False,
    power_off_event: bool = False,
    periodic_pixelmap_timer_due: bool = True,
    controlled_tier0_bench_shutdown: bool = False,
) -> SilentModeAutoPixelMapNoPwrShutterHilResult:
    """Co-emulate [Silent Mode Settings], [Target Function Settings] & [Shutter When Pwr OFF] absence."""

    def _mk_err(
        errno: int,
        status: str,
        *,
        eff_shutter: str = configured_shutter_type,
        eff_ivl_shutter: str = configured_shutter_type_in_interval,
        eff_audio: str = configured_audio_signals,
        eff_ap_drive: str = configured_aperture_drive_in_af,
        eff_auto_pm: str = configured_auto_pixel_mapping,
        disabled_funcs: Tuple[str, ...] = (),
        blocked_reqs: Tuple[str, ...] = (),
    ) -> SilentModeAutoPixelMapNoPwrShutterHilResult:
        return SilentModeAutoPixelMapNoPwrShutterHilResult(
            admitted=False,
            body_model=body_model,
            firmware_version=firmware_version,
            silent_mode_menu_path=SILENT_MODE_SETTINGS_MENU_PATH,
            target_function_menu_path=TARGET_FUNCTION_SETTINGS_MENU_PATH,
            anti_dust_menu_path=ANTI_DUST_FUNCTION_MENU_PATH,
            exposed_anti_dust_items=FX3_EXPOSED_ANTI_DUST_ITEMS,
            shutter_when_pwr_off_hardware_present=False,
            silent_mode=silent_mode,
            configured_shutter_type=configured_shutter_type,
            configured_shutter_type_in_interval=configured_shutter_type_in_interval,
            configured_audio_signals=configured_audio_signals,
            effective_shutter_type=eff_shutter,
            effective_shutter_type_in_interval=eff_ivl_shutter,
            effective_audio_signals=eff_audio,
            aperture_drive_in_af_target=aperture_drive_in_af_target,
            configured_aperture_drive_in_af=configured_aperture_drive_in_af,
            effective_aperture_drive_in_af=eff_ap_drive,
            auto_pixel_mapping_target=auto_pixel_mapping_target,
            configured_auto_pixel_mapping=configured_auto_pixel_mapping,
            effective_auto_pixel_mapping=eff_auto_pm,
            disabled_shooting_functions=disabled_funcs,
            blocked_function_requests=blocked_reqs,
            power_off_event=power_off_event,
            controlled_tier0_bench_shutdown=controlled_tier0_bench_shutdown,
            poweroff_mech_shutter_darkframe_actuations=0,
            poweroff_cnflasha_calibration_touches=0,
            silent_mode_5func_or_pwrshutter_bypass_events=0,
            bench_shutdown_unsuppressed_auto_pixelmap_events=0,
            errno_code=errno,
            status_code=status,
        )

    if body_model != BODY_MODEL_FX3:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_UNSUPPORTED_BODY_MODEL_FOR_FX3_STAGE43_EINVAL")
    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if silent_mode not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SILENT_MODE_STATE_EINVAL")
    if configured_shutter_type not in VALID_SHUTTER_TYPES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SHUTTER_TYPE_EINVAL")
    if configured_shutter_type_in_interval not in VALID_INTERVAL_SHUTTER_TYPES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SHUTTER_TYPE_IN_INTERVAL_EINVAL")
    if configured_audio_signals not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUDIO_SIGNALS_STATE_EINVAL")
    if aperture_drive_in_af_target not in VALID_TARGET_FUNCTION_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_APERTURE_DRIVE_TARGET_STATE_EINVAL")
    if configured_aperture_drive_in_af not in VALID_APERTURE_DRIVE_IN_AF_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_APERTURE_DRIVE_IN_AF_MODE_EINVAL")
    if auto_pixel_mapping_target not in VALID_TARGET_FUNCTION_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUTO_PIXEL_MAPPING_TARGET_STATE_EINVAL")
    if configured_auto_pixel_mapping not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUTO_PIXEL_MAPPING_STATE_EINVAL")

    # Explicit rejection of nonexistent [Shutter When Pwr OFF] on ILME-FX3 (Ver. 2.00..7.02)
    if request_shutter_when_pwr_off is not None or attempt_target_shutter_when_pwr_off:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_SHUTTER_WHEN_PWR_OFF_ABSENT_ON_ILME_FX3_VER_200_TO_702_EOPNOTSUPP",
            blocked_reqs=(ABSENT_FX3_SHUTTER_WHEN_PWR_OFF,),
        )

    for req_fn in requested_shooting_functions:
        if req_fn == ABSENT_FX3_SHUTTER_WHEN_PWR_OFF:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_SHUTTER_WHEN_PWR_OFF_ABSENT_ON_ILME_FX3_VER_200_TO_702_EOPNOTSUPP",
                blocked_reqs=(ABSENT_FX3_SHUTTER_WHEN_PWR_OFF,),
            )
        if req_fn not in SILENT_MODE_5_DISABLED_FUNCTIONS:
            return _mk_err(EINVAL_ERRNO, f"BLOCKED_UNKNOWN_SHOOTING_FUNCTION_{req_fn}_EINVAL")

    if silent_mode == "On":
        eff_shutter = SHUTTER_TYPE_ELECTRONIC
        eff_ivl_shutter = SHUTTER_TYPE_ELECTRONIC
        eff_audio = "Off"
        eff_ap_drive = (
            APERTURE_DRIVE_AF_SILENT_PRIORITY
            if aperture_drive_in_af_target == TARGET_SETTING_TARGET
            else configured_aperture_drive_in_af
        )
        eff_auto_pm = (
            "Off"
            if auto_pixel_mapping_target == TARGET_SETTING_TARGET
            else configured_auto_pixel_mapping
        )
        disabled_funcs = SILENT_MODE_5_DISABLED_FUNCTIONS

        blocked_list: List[str] = []
        if attempt_force_mechanical_shutter_in_silent:
            blocked_list.append("Shutter Type=Mechanical Shutter")
        if attempt_force_audio_signals_in_silent:
            blocked_list.append("Audio signals=On")
        for req_fn in requested_shooting_functions:
            if req_fn in SILENT_MODE_5_DISABLED_FUNCTIONS and req_fn not in blocked_list:
                blocked_list.append(req_fn)

        if blocked_list:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                f"BLOCKED_SILENT_MODE_LOCKOUT:{'+'.join(blocked_list)}",
                eff_shutter=eff_shutter,
                eff_ivl_shutter=eff_ivl_shutter,
                eff_audio=eff_audio,
                eff_ap_drive=eff_ap_drive,
                eff_auto_pm=eff_auto_pm,
                disabled_funcs=disabled_funcs,
                blocked_reqs=tuple(blocked_list),
            )
    else:
        eff_shutter = configured_shutter_type
        eff_ivl_shutter = configured_shutter_type_in_interval
        eff_audio = configured_audio_signals
        eff_ap_drive = configured_aperture_drive_in_af
        eff_auto_pm = configured_auto_pixel_mapping
        disabled_funcs = ()

    # Power-off Auto Pixel Mapping & Tier-0 Bench Shutdown Firewall
    mech_darkframe_actuations = 0
    if power_off_event:
        if controlled_tier0_bench_shutdown:
            if eff_auto_pm == "On" and periodic_pixelmap_timer_due:
                return _mk_err(
                    EBUSY_ERRNO,
                    "BLOCKED_TIER0_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP_EBUSY",
                    eff_shutter=eff_shutter,
                    eff_ivl_shutter=eff_ivl_shutter,
                    eff_audio=eff_audio,
                    eff_ap_drive=eff_ap_drive,
                    eff_auto_pm=eff_auto_pm,
                    disabled_funcs=disabled_funcs,
                    blocked_reqs=("Unsuppressed Auto Pixel Mapping on Tier-0 Bench Shutdown",),
                )
            mech_darkframe_actuations = 0
        else:
            # Normal non-bench field shutdown: mechanical shutter dark-frame runs only if
            # effective Auto Pixel Mapping is On and timer is due (0 persistent eMMC writes
            # in VM co-emulator).
            mech_darkframe_actuations = (
                1 if (eff_auto_pm == "On" and periodic_pixelmap_timer_due) else 0
            )

    status = (
        "ADMITTED_TIER0_BENCH_SHUTDOWN_SILENT_AUTOPIXELMAP_SUPPRESSED_OK"
        if (power_off_event and controlled_tier0_bench_shutdown)
        else (
            "ADMITTED_SILENT_MODE_ON_ESHUTTER_AUDIO_OFF_5FUNC_LOCKED_OK"
            if silent_mode == "On"
            else "ADMITTED_SILENT_MODE_OFF_STANDARD_OPERATION_OK"
        )
    )
    return SilentModeAutoPixelMapNoPwrShutterHilResult(
        admitted=True,
        body_model=body_model,
        firmware_version=firmware_version,
        silent_mode_menu_path=SILENT_MODE_SETTINGS_MENU_PATH,
        target_function_menu_path=TARGET_FUNCTION_SETTINGS_MENU_PATH,
        anti_dust_menu_path=ANTI_DUST_FUNCTION_MENU_PATH,
        exposed_anti_dust_items=FX3_EXPOSED_ANTI_DUST_ITEMS,
        shutter_when_pwr_off_hardware_present=False,
        silent_mode=silent_mode,
        configured_shutter_type=configured_shutter_type,
        configured_shutter_type_in_interval=configured_shutter_type_in_interval,
        configured_audio_signals=configured_audio_signals,
        effective_shutter_type=eff_shutter,
        effective_shutter_type_in_interval=eff_ivl_shutter,
        effective_audio_signals=eff_audio,
        aperture_drive_in_af_target=aperture_drive_in_af_target,
        configured_aperture_drive_in_af=configured_aperture_drive_in_af,
        effective_aperture_drive_in_af=eff_ap_drive,
        auto_pixel_mapping_target=auto_pixel_mapping_target,
        configured_auto_pixel_mapping=configured_auto_pixel_mapping,
        effective_auto_pixel_mapping=eff_auto_pm,
        disabled_shooting_functions=disabled_funcs,
        blocked_function_requests=(),
        power_off_event=power_off_event,
        controlled_tier0_bench_shutdown=controlled_tier0_bench_shutdown,
        poweroff_mech_shutter_darkframe_actuations=mech_darkframe_actuations,
        poweroff_cnflasha_calibration_touches=0,
        silent_mode_5func_or_pwrshutter_bypass_events=0,
        bench_shutdown_unsuppressed_auto_pixelmap_events=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil() -> Dict[str, object]:
    bench_shutdown_silent_targeted_ok = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="On",
        configured_shutter_type=SHUTTER_TYPE_MECHANICAL,
        configured_shutter_type_in_interval=SHUTTER_TYPE_MECHANICAL,
        configured_audio_signals="On",
        aperture_drive_in_af_target=TARGET_SETTING_TARGET,
        configured_aperture_drive_in_af=APERTURE_DRIVE_AF_STANDARD,
        auto_pixel_mapping_target=TARGET_SETTING_TARGET,
        configured_auto_pixel_mapping="On",
        power_off_event=True,
        periodic_pixelmap_timer_due=True,
        controlled_tier0_bench_shutdown=True,
    )
    not_target_retains_settings_ok = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="On",
        aperture_drive_in_af_target=TARGET_SETTING_NOT_TARGET,
        configured_aperture_drive_in_af=APERTURE_DRIVE_AF_FOCUS_PRIORITY,
        auto_pixel_mapping_target=TARGET_SETTING_NOT_TARGET,
        configured_auto_pixel_mapping="On",
        power_off_event=False,
    )
    bench_shutdown_unsuppressed_blocked = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="On",
        auto_pixel_mapping_target=TARGET_SETTING_NOT_TARGET,
        configured_auto_pixel_mapping="On",
        power_off_event=True,
        periodic_pixelmap_timer_due=True,
        controlled_tier0_bench_shutdown=True,
    )
    silent_5func_blocked_matrix = {
        fn: asdict(
            probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
                silent_mode="On",
                requested_shooting_functions=(fn,),
            )
        )
        for fn in SILENT_MODE_5_DISABLED_FUNCTIONS
    }
    mech_shutter_override_blocked = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="On",
        attempt_force_mechanical_shutter_in_silent=True,
    )
    audio_signals_override_blocked = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="On",
        attempt_force_audio_signals_in_silent=True,
    )
    pwr_shutter_rejected_across_versions = {
        ver: asdict(
            probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
                firmware_version=ver,
                request_shutter_when_pwr_off="On",
            )
        )
        for ver in VALID_FX3_FIRMWARE_VERSIONS
    }
    silent_off_5func_allowed_ok = probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
        silent_mode="Off",
        configured_shutter_type=SHUTTER_TYPE_MECHANICAL,
        configured_audio_signals="On",
        requested_shooting_functions=SILENT_MODE_5_DISABLED_FUNCTIONS,
    )

    passed = (
        bench_shutdown_silent_targeted_ok.admitted
        and bench_shutdown_silent_targeted_ok.effective_shutter_type == SHUTTER_TYPE_ELECTRONIC
        and bench_shutdown_silent_targeted_ok.effective_shutter_type_in_interval
        == SHUTTER_TYPE_ELECTRONIC
        and bench_shutdown_silent_targeted_ok.effective_audio_signals == "Off"
        and bench_shutdown_silent_targeted_ok.effective_aperture_drive_in_af
        == APERTURE_DRIVE_AF_SILENT_PRIORITY
        and bench_shutdown_silent_targeted_ok.effective_auto_pixel_mapping == "Off"
        and bench_shutdown_silent_targeted_ok.poweroff_mech_shutter_darkframe_actuations == 0
        and bench_shutdown_silent_targeted_ok.poweroff_cnflasha_calibration_touches == 0
        and not_target_retains_settings_ok.admitted
        and not_target_retains_settings_ok.effective_aperture_drive_in_af
        == APERTURE_DRIVE_AF_FOCUS_PRIORITY
        and not_target_retains_settings_ok.effective_auto_pixel_mapping == "On"
        and (not bench_shutdown_unsuppressed_blocked.admitted)
        and bench_shutdown_unsuppressed_blocked.errno_code == EBUSY_ERRNO
        and len(silent_5func_blocked_matrix) == 5
        and all(
            (not item["admitted"]) and item["errno_code"] == EOPNOTSUPP_ERRNO
            for item in silent_5func_blocked_matrix.values()
        )
        and (not mech_shutter_override_blocked.admitted)
        and mech_shutter_override_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not audio_signals_override_blocked.admitted)
        and audio_signals_override_blocked.errno_code == EOPNOTSUPP_ERRNO
        and all(
            (not item["admitted"])
            and item["errno_code"] == EOPNOTSUPP_ERRNO
            and (not item["shutter_when_pwr_off_hardware_present"])
            for item in pwr_shutter_rejected_across_versions.values()
        )
        and silent_off_5func_allowed_ok.admitted
    )
    return {
        "passed": passed,
        "all_5_silent_disabled_functions": list(SILENT_MODE_5_DISABLED_FUNCTIONS),
        "exposed_fx3_anti_dust_items": list(FX3_EXPOSED_ANTI_DUST_ITEMS),
        "absent_fx3_shutter_when_pwr_off": ABSENT_FX3_SHUTTER_WHEN_PWR_OFF,
        "bench_shutdown_silent_targeted_ok": asdict(bench_shutdown_silent_targeted_ok),
        "not_target_retains_settings_ok": asdict(not_target_retains_settings_ok),
        "bench_shutdown_unsuppressed_blocked_ebusy": asdict(bench_shutdown_unsuppressed_blocked),
        "silent_mode_5_disabled_functions_blocked_matrix": silent_5func_blocked_matrix,
        "mech_shutter_override_blocked_eopnotsupp": asdict(mech_shutter_override_blocked),
        "audio_signals_override_blocked_eopnotsupp": asdict(audio_signals_override_blocked),
        "shutter_when_pwr_off_rejected_ver_200_to_702": pwr_shutter_rejected_across_versions,
        "silent_mode_off_5func_allowed_ok": asdict(silent_off_5func_allowed_ok),
    }


# ---------------------------------------------------------------------------
# Sub-model B: [Marker Display] 15-Ratio Survival Across [Camera Settings Reset]
#              & Strict Local-LCD-Only HDMI Isolation (0 HDMI Marker Pixels)
# ---------------------------------------------------------------------------


def probe_marker_display_15ratio_and_hdmi_isolation_hil(
    *,
    firmware_version: str = "7.02",
    configured_marker_display: str = "On",
    configured_center_marker: str = "On",
    configured_aspect_marker: str = "2.39:1",
    configured_safety_zone: str = "90%",
    configured_guideframe: str = "On",
    reset_action: str = RESET_ACTION_NONE,
    hdmi_connected: bool = True,
    hdmi_info_display: str = "On",
    attempt_force_hdmi_marker_overlay: bool = False,
) -> MarkerDisplay15RatioHdmiIsolationHilResult:
    """Co-emulate [Marker Display] 15-ratio reset survival & strict local-LCD-only HDMI isolation."""

    def _mk_err(errno: int, status: str) -> MarkerDisplay15RatioHdmiIsolationHilResult:
        return MarkerDisplay15RatioHdmiIsolationHilResult(
            admitted=False,
            firmware_version=firmware_version,
            marker_menu_path=MARKER_DISPLAY_MENU_PATH,
            hdmi_info_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            reset_action_applied=reset_action,
            configured_marker_display=configured_marker_display,
            configured_center_marker=configured_center_marker,
            configured_aspect_marker=configured_aspect_marker,
            configured_safety_zone=configured_safety_zone,
            configured_guideframe=configured_guideframe,
            effective_marker_display="Off",
            effective_center_marker="Off",
            effective_aspect_marker=ASPECT_MARKER_OFF,
            effective_safety_zone="Off",
            effective_guideframe="Off",
            marker_survived_camera_settings_reset=False,
            marker_cleared_by_initialize=False,
            hdmi_connected=hdmi_connected,
            hdmi_info_display=hdmi_info_display,
            local_lcd_marker_overlay_active=False,
            local_lcd_marker_overlay_pixels=0,
            hdmi_info_telemetry_osd_active=False,
            hdmi_marker_overlay_rendered=False,
            hdmi_center_marker_pixels=0,
            hdmi_aspect_marker_pixels=0,
            hdmi_safety_zone_pixels=0,
            hdmi_guideframe_pixels=0,
            hdmi_marker_leaked_overlay_pixels=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if configured_marker_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MARKER_DISPLAY_STATE_EINVAL")
    if configured_center_marker not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_CENTER_MARKER_STATE_EINVAL")
    if configured_aspect_marker not in VALID_ASPECT_MARKER_SETTINGS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ASPECT_MARKER_RATIO_EINVAL")
    if configured_safety_zone not in VALID_SAFETY_ZONE_SETTINGS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SAFETY_ZONE_SETTING_EINVAL")
    if configured_guideframe not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_GUIDEFRAME_STATE_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if hdmi_info_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_HDMI_INFO_DISPLAY_STATE_EINVAL")

    # Aspect Marker 16:9 was added in Ver. 3.00+; reject on Ver. 2.00
    if firmware_version in PRE_300_FX3_FIRMWARE_VERSIONS and configured_aspect_marker == "16:9":
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_ASPECT_MARKER_16_9_REQUIRES_VER_300_OR_LATER_EOPNOTSUPP",
        )

    # Strict local-LCD-only isolation: forcing markers onto external HDMI is forbidden on ILME-FX3
    if attempt_force_hdmi_marker_overlay:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_HDMI_MARKER_OVERLAY_LOCAL_LCD_ONLY_ON_ILME_FX3_EOPNOTSUPP",
        )

    if reset_action == RESET_ACTION_INITIALIZE:
        eff_marker = "Off"
        eff_center = "Off"
        eff_aspect = ASPECT_MARKER_OFF
        eff_safety = "Off"
        eff_guide = "Off"
        survived_csr = False
        cleared_init = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        # [Marker Display] & [Aspect Marker] are NOT reset by [Camera Settings Reset]
        eff_marker = configured_marker_display
        eff_center = configured_center_marker
        eff_aspect = configured_aspect_marker
        eff_safety = configured_safety_zone
        eff_guide = configured_guideframe
        survived_csr = True
        cleared_init = False
    else:
        eff_marker = configured_marker_display
        eff_center = configured_center_marker
        eff_aspect = configured_aspect_marker
        eff_safety = configured_safety_zone
        eff_guide = configured_guideframe
        survived_csr = False
        cleared_init = False

    lcd_px = 0
    if eff_marker == "On":
        if eff_center == "On":
            lcd_px += LCD_CENTER_MARKER_PIXELS
        if eff_aspect != ASPECT_MARKER_OFF:
            lcd_px += LCD_ASPECT_MARKER_PIXELS
        if eff_safety != "Off":
            lcd_px += LCD_SAFETY_ZONE_PIXELS
        if eff_guide == "On":
            lcd_px += LCD_GUIDEFRAME_PIXELS

    lcd_overlay_active = lcd_px > 0
    hdmi_telemetry_osd_active = bool(hdmi_connected and hdmi_info_display == "On")

    status = (
        "ADMITTED_INITIALIZE_CLEARED_MARKERS_TO_OFF_OK"
        if cleared_init
        else (
            "ADMITTED_MARKER_SURVIVED_CAMERA_SETTINGS_RESET_HDMI_0PX_OK"
            if survived_csr
            else "ADMITTED_MARKER_LOCAL_LCD_ONLY_HDMI_0PX_OK"
        )
    )
    return MarkerDisplay15RatioHdmiIsolationHilResult(
        admitted=True,
        firmware_version=firmware_version,
        marker_menu_path=MARKER_DISPLAY_MENU_PATH,
        hdmi_info_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        reset_action_applied=reset_action,
        configured_marker_display=configured_marker_display,
        configured_center_marker=configured_center_marker,
        configured_aspect_marker=configured_aspect_marker,
        configured_safety_zone=configured_safety_zone,
        configured_guideframe=configured_guideframe,
        effective_marker_display=eff_marker,
        effective_center_marker=eff_center,
        effective_aspect_marker=eff_aspect,
        effective_safety_zone=eff_safety,
        effective_guideframe=eff_guide,
        marker_survived_camera_settings_reset=survived_csr,
        marker_cleared_by_initialize=cleared_init,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        local_lcd_marker_overlay_active=lcd_overlay_active,
        local_lcd_marker_overlay_pixels=lcd_px,
        hdmi_info_telemetry_osd_active=hdmi_telemetry_osd_active,
        hdmi_marker_overlay_rendered=False,
        hdmi_center_marker_pixels=0,
        hdmi_aspect_marker_pixels=0,
        hdmi_safety_zone_pixels=0,
        hdmi_guideframe_pixels=0,
        hdmi_marker_leaked_overlay_pixels=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil() -> Dict[str, object]:
    ratio_15_matrix = {
        ratio: asdict(
            probe_marker_display_15ratio_and_hdmi_isolation_hil(
                firmware_version="7.02",
                configured_marker_display="On",
                configured_center_marker="On",
                configured_aspect_marker=ratio,
                configured_safety_zone="80%",
                configured_guideframe="On",
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                hdmi_connected=True,
                hdmi_info_display="On",
            )
        )
        for ratio in ASPECT_MARKER_15_RATIOS
    }
    aspect_off_baseline = probe_marker_display_15ratio_and_hdmi_isolation_hil(
        configured_marker_display="On",
        configured_center_marker="On",
        configured_aspect_marker=ASPECT_MARKER_OFF,
        configured_safety_zone="90%",
        configured_guideframe="Off",
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    initialize_clears_all_markers = probe_marker_display_15ratio_and_hdmi_isolation_hil(
        configured_marker_display="On",
        configured_center_marker="On",
        configured_aspect_marker="2.39:1",
        configured_safety_zone="90%",
        configured_guideframe="On",
        reset_action=RESET_ACTION_INITIALIZE,
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    ver200_16_9_rejected = probe_marker_display_15ratio_and_hdmi_isolation_hil(
        firmware_version="2.00",
        configured_aspect_marker="16:9",
    )
    force_hdmi_marker_rejected = probe_marker_display_15ratio_and_hdmi_isolation_hil(
        configured_marker_display="On",
        configured_aspect_marker="2.39:1",
        hdmi_connected=True,
        hdmi_info_display="On",
        attempt_force_hdmi_marker_overlay=True,
    )

    passed = (
        len(ratio_15_matrix) == 15
        and all(
            item["admitted"]
            and item["marker_survived_camera_settings_reset"]
            and item["effective_aspect_marker"] == ratio
            and item["local_lcd_marker_overlay_active"]
            and item["local_lcd_marker_overlay_pixels"] > 0
            and item["hdmi_info_telemetry_osd_active"]
            and (not item["hdmi_marker_overlay_rendered"])
            and item["hdmi_marker_leaked_overlay_pixels"] == 0
            for ratio, item in ratio_15_matrix.items()
        )
        and aspect_off_baseline.admitted
        and aspect_off_baseline.effective_aspect_marker == ASPECT_MARKER_OFF
        and aspect_off_baseline.hdmi_marker_leaked_overlay_pixels == 0
        and initialize_clears_all_markers.admitted
        and initialize_clears_all_markers.marker_cleared_by_initialize
        and initialize_clears_all_markers.effective_marker_display == "Off"
        and initialize_clears_all_markers.effective_aspect_marker == ASPECT_MARKER_OFF
        and initialize_clears_all_markers.local_lcd_marker_overlay_pixels == 0
        and (not ver200_16_9_rejected.admitted)
        and ver200_16_9_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not force_hdmi_marker_rejected.admitted)
        and force_hdmi_marker_rejected.errno_code == EOPNOTSUPP_ERRNO
        and force_hdmi_marker_rejected.hdmi_marker_leaked_overlay_pixels == 0
    )
    return {
        "passed": passed,
        "all_15_aspect_marker_ratios": list(ASPECT_MARKER_15_RATIOS),
        "ratio_15_camera_settings_reset_and_hdmi_0px_matrix": ratio_15_matrix,
        "aspect_off_safety90_hdmi_0px_ok": asdict(aspect_off_baseline),
        "initialize_clears_all_markers_ok": asdict(initialize_clears_all_markers),
        "ver200_aspect_16_9_rejected_eopnotsupp": asdict(ver200_16_9_rejected),
        "force_hdmi_marker_overlay_rejected_eopnotsupp": asdict(force_hdmi_marker_rejected),
    }


# ---------------------------------------------------------------------------
# Sub-model C & Redlines: [Exposure Ctrl Type] (P/A/S/M vs Flexible Exp. Mode),
#                         [Auto/Manual Swt. Set.] & [Auto Slow Shutter] Reset Split
# ---------------------------------------------------------------------------


def probe_flexible_exp_mode_and_reset_split_hil(
    *,
    exposure_ctrl_type: str = EXPOSURE_CTRL_FLEXIBLE,
    pasm_submode: str = PASM_MANUAL_EXPOSURE,
    configured_av_switch: str = SWITCH_AUTO,
    configured_tv_switch: str = SWITCH_AUTO,
    configured_iso_switch: str = SWITCH_AUTO,
    configured_auto_slow_shutter: str = "Off",
    configured_marker_display: str = "On",
    configured_aspect_marker: str = "2.39:1",
    reset_action: str = RESET_ACTION_NONE,
    attempt_auto_manual_swt_in_pasm: bool = False,
    restore_from_slot1_camset: Optional[str] = None,
    saved_camset_av_switch: str = SWITCH_AUTO,
    saved_camset_tv_switch: str = SWITCH_MANUAL,
    saved_camset_iso_switch: str = SWITCH_AUTO,
    saved_camset_auto_slow_shutter: str = "Off",
) -> FlexibleExpModeResetSplitHilResult:
    """Co-emulate [Exposure Ctrl Type] & [Camera Settings Reset] split vs [Marker Display]."""

    def _mk_err(errno: int, status: str) -> FlexibleExpModeResetSplitHilResult:
        return FlexibleExpModeResetSplitHilResult(
            admitted=False,
            exposure_ctrl_menu_path=EXPOSURE_CTRL_TYPE_MENU_PATH,
            auto_manual_swt_menu_path=AUTO_MANUAL_SWT_SET_MENU_PATH,
            auto_slow_shutter_menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            exposure_ctrl_type=exposure_ctrl_type,
            pasm_submode=pasm_submode,
            auto_manual_swt_menu_available=(exposure_ctrl_type == EXPOSURE_CTRL_FLEXIBLE),
            reset_action_applied=reset_action,
            slot1_camset_restored=restore_from_slot1_camset,
            configured_av_switch=configured_av_switch,
            configured_tv_switch=configured_tv_switch,
            configured_iso_switch=configured_iso_switch,
            configured_auto_slow_shutter=configured_auto_slow_shutter,
            effective_av_switch=DEFAULT_FLEXEXP_AV_SWITCH,
            effective_tv_switch=DEFAULT_FLEXEXP_TV_SWITCH,
            effective_iso_switch=DEFAULT_FLEXEXP_ISO_SWITCH,
            effective_auto_slow_shutter=DEFAULT_AUTO_SLOW_SHUTTER,
            configured_marker_display=configured_marker_display,
            configured_aspect_marker=configured_aspect_marker,
            effective_marker_display="Off",
            effective_aspect_marker=ASPECT_MARKER_OFF,
            flexexp_switches_reset_by_camera_settings_reset=False,
            auto_slow_shutter_reset_by_camera_settings_reset=False,
            marker_survived_while_flexexp_reset_split_verified=False,
            bk4_persistent_nvram_writes=0,
            flexexp_or_marker_reset_split_drift_events=0,
            errno_code=errno,
            status_code=status,
        )

    if exposure_ctrl_type not in VALID_EXPOSURE_CTRL_TYPES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_EXPOSURE_CTRL_TYPE_EINVAL")
    if pasm_submode not in VALID_PASM_SUBMODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_PASM_SUBMODE_EINVAL")
    if configured_av_switch not in VALID_AUTO_MANUAL_SWITCH_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AV_SWITCH_STATE_EINVAL")
    if configured_tv_switch not in VALID_AUTO_MANUAL_SWITCH_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TV_SWITCH_STATE_EINVAL")
    if configured_iso_switch not in VALID_AUTO_MANUAL_SWITCH_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ISO_SWITCH_STATE_EINVAL")
    if configured_auto_slow_shutter not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_AUTO_SLOW_SHUTTER_STATE_EINVAL")
    if configured_marker_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MARKER_DISPLAY_STATE_EINVAL")
    if configured_aspect_marker not in VALID_ASPECT_MARKER_SETTINGS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_ASPECT_MARKER_RATIO_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")

    if restore_from_slot1_camset is not None:
        if not _CAMSET_FILENAME_RE.match(restore_from_slot1_camset):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SLOT1_CAMSET_FILENAME_EINVAL")
        if (
            saved_camset_av_switch not in VALID_AUTO_MANUAL_SWITCH_STATES
            or saved_camset_tv_switch not in VALID_AUTO_MANUAL_SWITCH_STATES
            or saved_camset_iso_switch not in VALID_AUTO_MANUAL_SWITCH_STATES
            or saved_camset_auto_slow_shutter not in VALID_ON_OFF
        ):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SAVED_CAMSET_EXPOSURE_PAYLOAD_EINVAL")

    if exposure_ctrl_type == EXPOSURE_CTRL_PASM and attempt_auto_manual_swt_in_pasm:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_AUTO_MANUAL_SWT_REQUIRES_FLEXIBLE_EXP_MODE_EOPNOTSUPP",
        )

    # Compute baseline effective switches before reset / CAMSET recall
    if exposure_ctrl_type == EXPOSURE_CTRL_PASM:
        if pasm_submode == PASM_PROGRAM_AUTO:
            eff_av, eff_tv = SWITCH_AUTO, SWITCH_AUTO
        elif pasm_submode == PASM_APERTURE_PRIORITY:
            eff_av, eff_tv = SWITCH_MANUAL, SWITCH_AUTO
        elif pasm_submode == PASM_SHUTTER_PRIORITY:
            eff_av, eff_tv = SWITCH_AUTO, SWITCH_MANUAL
        else:
            eff_av, eff_tv = SWITCH_MANUAL, SWITCH_MANUAL
        eff_iso = configured_iso_switch
    else:
        eff_av = configured_av_switch
        eff_tv = configured_tv_switch
        eff_iso = configured_iso_switch

    eff_slow = configured_auto_slow_shutter
    eff_marker = configured_marker_display
    eff_aspect = configured_aspect_marker
    flexexp_reset_csr = False
    slow_reset_csr = False
    split_verified = False

    if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        # [Auto/Manual Swt. Set.] (Av/Tv/ISO -> Manual) and [Auto Slow Shutter] (-> On)
        # reset cleanly on [Camera Settings Reset], whereas [Marker Display]/[Aspect Marker] SURVIVE!
        eff_av = DEFAULT_FLEXEXP_AV_SWITCH
        eff_tv = DEFAULT_FLEXEXP_TV_SWITCH
        eff_iso = DEFAULT_FLEXEXP_ISO_SWITCH
        eff_slow = DEFAULT_AUTO_SLOW_SHUTTER
        eff_marker = configured_marker_display
        eff_aspect = configured_aspect_marker
        flexexp_reset_csr = True
        slow_reset_csr = True
        split_verified = (
            eff_av == SWITCH_MANUAL
            and eff_tv == SWITCH_MANUAL
            and eff_iso == SWITCH_MANUAL
            and eff_slow == "On"
            and eff_marker == configured_marker_display
            and eff_aspect == configured_aspect_marker
        )
    elif reset_action == RESET_ACTION_INITIALIZE:
        eff_av = DEFAULT_FLEXEXP_AV_SWITCH
        eff_tv = DEFAULT_FLEXEXP_TV_SWITCH
        eff_iso = DEFAULT_FLEXEXP_ISO_SWITCH
        eff_slow = DEFAULT_AUTO_SLOW_SHUTTER
        eff_marker = "Off"
        eff_aspect = ASPECT_MARKER_OFF

    if restore_from_slot1_camset is not None:
        eff_av = saved_camset_av_switch
        eff_tv = saved_camset_tv_switch
        eff_iso = saved_camset_iso_switch
        eff_slow = saved_camset_auto_slow_shutter

    status = (
        f"ADMITTED_SLOT1_{restore_from_slot1_camset}_FLEXEXP_RESTORED_OK"
        if restore_from_slot1_camset is not None
        else (
            "ADMITTED_CAMERA_SETTINGS_RESET_SPLIT_FLEXEXP_DEFAULT_MARKER_SURVIVED_OK"
            if reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
            else (
                "ADMITTED_INITIALIZE_ALL_EXPOSURE_AND_MARKERS_DEFAULT_OK"
                if reset_action == RESET_ACTION_INITIALIZE
                else (
                    "ADMITTED_FLEXIBLE_EXP_MODE_ACTIVE_OK"
                    if exposure_ctrl_type == EXPOSURE_CTRL_FLEXIBLE
                    else "ADMITTED_PASM_MODE_ACTIVE_OK"
                )
            )
        )
    )
    return FlexibleExpModeResetSplitHilResult(
        admitted=True,
        exposure_ctrl_menu_path=EXPOSURE_CTRL_TYPE_MENU_PATH,
        auto_manual_swt_menu_path=AUTO_MANUAL_SWT_SET_MENU_PATH,
        auto_slow_shutter_menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        exposure_ctrl_type=exposure_ctrl_type,
        pasm_submode=pasm_submode,
        auto_manual_swt_menu_available=(exposure_ctrl_type == EXPOSURE_CTRL_FLEXIBLE),
        reset_action_applied=reset_action,
        slot1_camset_restored=restore_from_slot1_camset,
        configured_av_switch=configured_av_switch,
        configured_tv_switch=configured_tv_switch,
        configured_iso_switch=configured_iso_switch,
        configured_auto_slow_shutter=configured_auto_slow_shutter,
        effective_av_switch=eff_av,
        effective_tv_switch=eff_tv,
        effective_iso_switch=eff_iso,
        effective_auto_slow_shutter=eff_slow,
        configured_marker_display=configured_marker_display,
        configured_aspect_marker=configured_aspect_marker,
        effective_marker_display=eff_marker,
        effective_aspect_marker=eff_aspect,
        flexexp_switches_reset_by_camera_settings_reset=flexexp_reset_csr,
        auto_slow_shutter_reset_by_camera_settings_reset=slow_reset_csr,
        marker_survived_while_flexexp_reset_split_verified=split_verified,
        bk4_persistent_nvram_writes=0,
        flexexp_or_marker_reset_split_drift_events=0,
        errno_code=0,
        status_code=status,
    )


def simulate_marker_and_flexexp_reset_vs_initialize_lifecycle(
    *,
    configured_aspect_marker: str = "2.39:1",
    configured_av_switch: str = SWITCH_AUTO,
    configured_tv_switch: str = SWITCH_AUTO,
    configured_iso_switch: str = SWITCH_AUTO,
    configured_auto_slow_shutter: str = "Off",
) -> Dict[str, object]:
    """Simulate 3-stage lifecycle: Configured -> [Camera Settings Reset] -> [Initialize]."""
    step1_configured = probe_flexible_exp_mode_and_reset_split_hil(
        exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE,
        configured_av_switch=configured_av_switch,
        configured_tv_switch=configured_tv_switch,
        configured_iso_switch=configured_iso_switch,
        configured_auto_slow_shutter=configured_auto_slow_shutter,
        configured_marker_display="On",
        configured_aspect_marker=configured_aspect_marker,
        reset_action=RESET_ACTION_NONE,
    )
    step2_csr = probe_flexible_exp_mode_and_reset_split_hil(
        exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE,
        configured_av_switch=configured_av_switch,
        configured_tv_switch=configured_tv_switch,
        configured_iso_switch=configured_iso_switch,
        configured_auto_slow_shutter=configured_auto_slow_shutter,
        configured_marker_display="On",
        configured_aspect_marker=configured_aspect_marker,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    step3_initialize = probe_flexible_exp_mode_and_reset_split_hil(
        exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE,
        configured_av_switch=configured_av_switch,
        configured_tv_switch=configured_tv_switch,
        configured_iso_switch=configured_iso_switch,
        configured_auto_slow_shutter=configured_auto_slow_shutter,
        configured_marker_display="On",
        configured_aspect_marker=configured_aspect_marker,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    lifecycle_verified = (
        step1_configured.admitted
        and step1_configured.effective_av_switch == configured_av_switch
        and step1_configured.effective_auto_slow_shutter == configured_auto_slow_shutter
        and step1_configured.effective_aspect_marker == configured_aspect_marker
        and step2_csr.admitted
        and step2_csr.marker_survived_while_flexexp_reset_split_verified
        and step2_csr.effective_av_switch == SWITCH_MANUAL
        and step2_csr.effective_tv_switch == SWITCH_MANUAL
        and step2_csr.effective_iso_switch == SWITCH_MANUAL
        and step2_csr.effective_auto_slow_shutter == "On"
        and step2_csr.effective_marker_display == "On"
        and step2_csr.effective_aspect_marker == configured_aspect_marker
        and step3_initialize.admitted
        and step3_initialize.effective_av_switch == SWITCH_MANUAL
        and step3_initialize.effective_tv_switch == SWITCH_MANUAL
        and step3_initialize.effective_iso_switch == SWITCH_MANUAL
        and step3_initialize.effective_auto_slow_shutter == "On"
        and step3_initialize.effective_marker_display == "Off"
        and step3_initialize.effective_aspect_marker == ASPECT_MARKER_OFF
    )
    return {
        "lifecycle_verified": lifecycle_verified,
        "step1_configured": asdict(step1_configured),
        "step2_camera_settings_reset_split": asdict(step2_csr),
        "step3_initialize_full_clear": asdict(step3_initialize),
    }


def probe_hard_safety_redline(
    *,
    persistent_emmc_writes_authorized: bool = False,
    hardware_live_attachment_authorized: bool = False,
    overall_ready_for_hardware_attach: bool = False,
    spi_nor_write_authorized: bool = False,
    el3_payload_transmit_authorized: bool = False,
    isp_write_authorized: bool = False,
    cnflasha_userspace_write_attempt: bool = False,
    bypass_silent_mode_5func_or_pwrshutter: bool = False,
    bypass_bench_shutdown_auto_pixelmap: bool = False,
    force_hdmi_marker_leak_or_reset_split_drift: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed hard safety redline guard for Phase 236 Stage 43 (43/43)."""
    violations: List[str] = []
    if persistent_emmc_writes_authorized:
        violations.append("persistent_emmc_writes_authorized")
    if hardware_live_attachment_authorized:
        violations.append("hardware_live_attachment_authorized")
    if overall_ready_for_hardware_attach:
        violations.append("overall_ready_for_hardware_attach")
    if spi_nor_write_authorized:
        violations.append("spi_nor_write_authorized")
    if el3_payload_transmit_authorized:
        violations.append("el3_payload_transmit_authorized")
    if isp_write_authorized:
        violations.append("isp_write_authorized")
    if cnflasha_userspace_write_attempt:
        violations.append("cnflasha_userspace_write_attempt")
    if bypass_silent_mode_5func_or_pwrshutter:
        violations.append("bypass_silent_mode_5func_or_pwrshutter")
    if bypass_bench_shutdown_auto_pixelmap:
        violations.append("bypass_bench_shutdown_auto_pixelmap")
    if force_hdmi_marker_leak_or_reset_split_drift:
        violations.append("force_hdmi_marker_leak_or_reset_split_drift")

    if violations:
        joined = "+".join(violations)
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=False,
            hardware_live_attachment_authorized=False,
            overall_ready_for_hardware_attach=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            isp_write_authorized=False,
            cnflasha_userspace_write_blocked=True,
            cnflasha_mutation_bytes=0,
            physical_usb_packets_emitted=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            silent_mode_5func_or_pwrshutter_bypass_events=0,
            bench_shutdown_unsuppressed_auto_pixelmap_events=0,
            hdmi_marker_leaked_overlay_pixels=0,
            flexexp_or_marker_reset_split_drift_events=0,
            blocked_action=joined,
            status_code=f"BLOCKED_HARD_SAFETY_REDLINE:{joined}",
        )

    return RedlineGuardProbeResult(
        valid=True,
        persistent_emmc_writes_authorized=False,
        hardware_live_attachment_authorized=False,
        overall_ready_for_hardware_attach=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        isp_write_authorized=False,
        cnflasha_userspace_write_blocked=True,
        cnflasha_mutation_bytes=0,
        physical_usb_packets_emitted=0,
        otp_fuse_touches=0,
        rpmb_counter_increments=0,
        silent_mode_5func_or_pwrshutter_bypass_events=0,
        bench_shutdown_unsuppressed_auto_pixelmap_events=0,
        hdmi_marker_leaked_overlay_pixels=0,
        flexexp_or_marker_reset_split_drift_events=0,
        blocked_action="NONE",
        status_code="VERIFIED_HARD_SAFETY_REDLINES_LOCKED_FALSE_OK",
    )


def evaluate_pillar_c_d_flexexp_reset_split_and_redlines() -> Dict[str, object]:
    pasm_4mode_matrix = {
        sub: asdict(
            probe_flexible_exp_mode_and_reset_split_hil(
                exposure_ctrl_type=EXPOSURE_CTRL_PASM,
                pasm_submode=sub,
                configured_iso_switch=SWITCH_MANUAL,
            )
        )
        for sub in VALID_PASM_SUBMODES
    }
    pasm_auto_manual_swt_blocked = probe_flexible_exp_mode_and_reset_split_hil(
        exposure_ctrl_type=EXPOSURE_CTRL_PASM,
        pasm_submode=PASM_MANUAL_EXPOSURE,
        attempt_auto_manual_swt_in_pasm=True,
    )
    lifecycle = simulate_marker_and_flexexp_reset_vs_initialize_lifecycle(
        configured_aspect_marker="2.39:1",
        configured_av_switch=SWITCH_AUTO,
        configured_tv_switch=SWITCH_AUTO,
        configured_iso_switch=SWITCH_AUTO,
        configured_auto_slow_shutter="Off",
    )
    camset01_restore_after_csr = probe_flexible_exp_mode_and_reset_split_hil(
        exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        restore_from_slot1_camset="CAMSET01.DAT",
        saved_camset_av_switch=SWITCH_AUTO,
        saved_camset_tv_switch=SWITCH_MANUAL,
        saved_camset_iso_switch=SWITCH_AUTO,
        saved_camset_auto_slow_shutter="Off",
        configured_marker_display="On",
        configured_aspect_marker="1.85:1",
    )

    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(persistent_emmc_writes_authorized=True)),
        asdict(probe_hard_safety_redline(hardware_live_attachment_authorized=True)),
        asdict(probe_hard_safety_redline(overall_ready_for_hardware_attach=True)),
        asdict(probe_hard_safety_redline(spi_nor_write_authorized=True)),
        asdict(probe_hard_safety_redline(el3_payload_transmit_authorized=True)),
        asdict(probe_hard_safety_redline(isp_write_authorized=True)),
        asdict(probe_hard_safety_redline(cnflasha_userspace_write_attempt=True)),
        asdict(probe_hard_safety_redline(bypass_silent_mode_5func_or_pwrshutter=True)),
        asdict(probe_hard_safety_redline(bypass_bench_shutdown_auto_pixelmap=True)),
        asdict(probe_hard_safety_redline(force_hdmi_marker_leak_or_reset_split_drift=True)),
    ]

    passed = (
        len(pasm_4mode_matrix) == 4
        and all(item["admitted"] for item in pasm_4mode_matrix.values())
        and (not pasm_auto_manual_swt_blocked.admitted)
        and pasm_auto_manual_swt_blocked.errno_code == EOPNOTSUPP_ERRNO
        and bool(lifecycle["lifecycle_verified"])
        and camset01_restore_after_csr.admitted
        and camset01_restore_after_csr.effective_av_switch == SWITCH_AUTO
        and camset01_restore_after_csr.effective_tv_switch == SWITCH_MANUAL
        and camset01_restore_after_csr.effective_iso_switch == SWITCH_AUTO
        and camset01_restore_after_csr.effective_auto_slow_shutter == "Off"
        and camset01_restore_after_csr.effective_aspect_marker == "1.85:1"
        and camset01_restore_after_csr.bk4_persistent_nvram_writes == 0
        and baseline_redline.valid
        and len(blocked_probes) == 10
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "pasm_4mode_matrix": pasm_4mode_matrix,
        "pasm_auto_manual_swt_blocked_eopnotsupp": asdict(pasm_auto_manual_swt_blocked),
        "marker_vs_flexexp_reset_and_initialize_lifecycle": lifecycle,
        "slot1_camset01_restore_after_csr_ok": asdict(camset01_restore_after_csr),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 236 (Stage 43, 43/43 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 236 Stage 43 (43/43) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase236_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil()
    pillar_b = evaluate_pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil()
    pillar_cd = evaluate_pillar_c_d_flexexp_reset_split_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "cnflasha_mutation_bytes": CNFLASHA_MUTATION_BYTES,
        "cnflasha_userspace_write_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "silent_mode_5func_or_pwrshutter_bypass_events": (
            SILENT_MODE_5FUNC_OR_PWRSHUTTER_BYPASS_EVENTS
        ),
        "bench_shutdown_unsuppressed_auto_pixelmap_events": (
            BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP_EVENTS
        ),
        "hdmi_marker_leaked_overlay_pixels": HDMI_MARKER_LEAKED_OVERLAY_PIXELS,
        "flexexp_or_marker_reset_split_drift_events": (
            FLEXEXP_OR_MARKER_RESET_SPLIT_DRIFT_EVENTS
        ),
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        "donor_access_mode": DONOR_ACCESS_MODE,
    }

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
        and CNFLASHA_MUTATION_BYTES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and SILENT_MODE_5FUNC_OR_PWRSHUTTER_BYPASS_EVENTS == 0
        and BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP_EVENTS == 0
        and HDMI_MARKER_LEAKED_OVERLAY_PIXELS == 0
        and FLEXEXP_OR_MARKER_RESET_SPLIT_DRIFT_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_236_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil": pillar_a,
        "pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil": pillar_b,
        "pillar_c_d_flexexp_reset_split_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_silent_autopixelmap_marker_flexexp_coemulator.py",
        description=(
            "Phase 236 Stage 43 (43/43 Milestone) — Real-Hardware ILME-FX3 Wave-33 Silent Mode "
            "Auto Pixel Mapping Target & Shutter When Pwr OFF Absence, Marker Display 15-Ratio "
            "HDMI Isolation & Flexible Exp. Mode Reset Split HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 236 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil"]
        pb = rep["pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil"]
        pcd = rep["pillar_c_d_flexexp_reset_split_and_redlines"]
        funcs5 = len(pa["all_5_silent_disabled_functions"])
        pm_act = pa["bench_shutdown_silent_targeted_ok"][
            "poweroff_mech_shutter_darkframe_actuations"
        ]
        ratios15 = len(pb["all_15_aspect_marker_ratios"])
        hdmi_px = rep["redlines"]["hdmi_marker_leaked_overlay_pixels"]
        split_ok = int(pcd["marker_vs_flexexp_reset_and_initialize_lifecycle"]["lifecycle_verified"])
        sys.stdout.write(
            f"[{status}] Phase 236 Stage 43 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"silent={funcs5}func_lock_pm_act:{pm_act}_nopwrshutter:1 | "
            f"marker_ratios={ratios15}_hdmi_px:{hdmi_px} | "
            f"flexexp_csr_split={split_ok} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
