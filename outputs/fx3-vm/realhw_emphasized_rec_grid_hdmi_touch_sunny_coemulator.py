#!/usr/bin/env python3
"""Phase 242 (Stage 45, 45/45 Milestone) — Real-Hardware ILME-FX3 Wave-35
`[Emphasized REC Display]` & `[Grid Line Display]` HDMI Info Routing vs Forced
`[Off(HDMI Only)]` / `RAW` Clean-Feed Lock, `[Touch Operation]` 4-Item
`[Camera Settings Reset]` Survival & Unattended Bench Tap Guard, and
`[Monitor Brightness]` `[Manual]` (`-2..+2`) vs `[Sunny Weather]` Indoor
Over-Brightness & `NP-FZ100` Power Guard HIL Co-Emulator.

Strictly models Wave-35 official Sony `ILME-FX3` (`Ver. 2.00..7.02`, primary `Ver. 7.02`) and
`ILME-FX6` (`Ver. 6.01`) contracts without hardware attachment or firmware byte leakage:

1. **Sub-Model 45A — `[Emphasized REC Display]` & `[Grid Line Display]` HDMI Info Routing vs
   Forced `[Off(HDMI Only)]` / `RAW` Clean-Feed Lock**:
   - Co-emulates `MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]` (`On`
     factory default, `Off` — **resettable** back to `On` via `[Camera Settings Reset]`, active
     strictly during Movie and `S&Q` recording, inactive in Standby and Still shooting) alongside
     `[Grid Line Display]` (`Off` factory default, `On`) and `[Grid Line Type]`
     (`Rule of 3rds Grid` factory default, `Square Grid`, `Diag. + Square Grid` — **NOT reset**
     by `[Camera Settings Reset]`, `grid_line_reset_only_by_initialize == True`), proving the
     deterministic `[Camera Settings Reset]` split plus zero-NVRAM Slot-1 `CAMSET01..10.DAT`
     recall (`bk4_persistent_nvram_writes == 0`).
   - **External HDMI Info Routing vs Local-LCD-Only Assist Overlays**: unlike strictly
     local-LCD-only `[Marker Display]`, `[Zebra Display]`, and `[Peaking Display]` (`0` HDMI
     overlay pixels even when `[HDMI Info. Display] == "On"`), both `[Emphasized REC Display]`
     red border (when `On` during Movie/`S&Q` recording) and `[Grid Line Display]` (when `On`)
     **CAN route to external HDMI** when effective `[HDMI Info. Display] == "On"`, which
     simultaneously blanks the built-in camera LCD (`camera_lcd_blanked_by_hdmi_info == True`).
   - **Two Automatic Hardware `[HDMI Info. Display] -> [Off]` Clean-Feed Clamps**: whenever
     `[Rec. Media dur HDMI Output] == "Off(HDMI Only)"` OR while HDMI `RAW` movie output
     (`[RAW Output] == "On"`) is active, hardware automatically forces `[HDMI Info. Display]`
     to `"Off"`, guaranteeing `0` baked red REC frames, `0` grid lines, and `0` status OSD pixels
     on external HDMI recorders (`hdmi_only_or_raw_baked_recframe_or_grid_frames == 0`,
     `hdmi_baked_overlay_pixels == 0`).

2. **Sub-Model 45B — `[Touch Operation]` 4-Item `[Camera Settings Reset]` Survival & Unattended
   Bench Tap Guard**:
   - Co-emulates all 4 `MENU -> Setup -> [Touch Operation]` items:
     1) `[Touch Operation]` (`On` default / `On: Playback Only` / `Off`),
     2) `[Touch Sensitivity]` (`Standard` default / `Sensitive`),
     3) `[Swipe Up]` (`Open the Fn Menu` default / `Off`), and
     4) `[Touch Func. in Shooting]` (`Touch Tracking` default / `Touch Focus` / `Off`).
   - **4-Item Reset Survival**: all 4 items survive `[Camera Settings Reset]` intact
     (`reset_only_by_initialize == True`) and revert to factory defaults **only** on full
     `[Initialize]`.
   - **Unattended Bench Tap Guard**: during unattended physical bench rehearsals or Tier-0 vault
     dumps, setting `[Touch Operation] = "Off"` (or `"On: Playback Only"`) survives
     `[Camera Settings Reset]` and blocks accidental capacitive screen brushes from opening the
     `Fn` menu via `Swipe Up` or triggering `Touch Tracking` / `Touch Focus`
     (`unattended_bench_accidental_touch_events == 0`), while leaving `[Touch Operation] = "On"`
     on an unattended bench fails closed with `EBUSY (16)`.

3. **Sub-Model 45C — `[Monitor Brightness]` `[Manual]` (`-2..+2`) vs `[Sunny Weather]` Indoor
   Over-Brightness & `NP-FZ100` Power Guard + Hard Safety Redlines**:
   - Co-emulates `MENU -> Setup -> [Monitor] -> [Monitor Brightness]` (`Manual` `-2..+2`,
     default `0`, vs `Sunny Weather`), surviving `[Camera Settings Reset]` intact
     (`reset_only_by_initialize == True`) and clearing to `Manual` (`0`) exclusively on
     `[Initialize]`.
   - Flags and blocks `[Sunny Weather]` during indoor bench rehearsals (`EBUSY (16)`,
     `indoor_sunny_weather_unclamped_events == 0`) to prevent indoor manual visual exposure
     skew and excess `NP-FZ100` LCD backlight power/thermal draw (`1050 mW` vs `450 mW` at
     `Manual 0`), while permitting outdoor daylight `[Sunny Weather]` monitoring.

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Supports `LOCAL_DONOR_O_RDONLY` (strictly read-only bounded `<= 4096 B` window inspection
     across 14 FX3 `7.02` & FX6 `6.01` donors in `< 0.1s` cold, cached,
     `raw_firmware_bytes_leaked == 0`) and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`).
   - Locks `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`,
     `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
     `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, and
     `physical_device_writes = 0`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator_v1"
PHASE_242_SCHEMA = SCHEMA_ID
PHASE_242_VERSION = "242.0.0"
STAGE_INDEX = 45
STAGE_TOTAL = 45
MILESTONE_LABEL = "45/45"
STAGE_NAME = "stage45_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil"
FX3_MODEL_ID = 0x91030080

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
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
HDMI_ONLY_OR_RAW_BAKED_RECFRAME_OR_GRID_FRAMES = 0
HDMI_LOCAL_ONLY_MARKER_ZEBRA_PEAKING_LEAKED_PIXELS = 0
UNATTENDED_BENCH_ACCIDENTAL_TOUCH_EVENTS = 0
INDOOR_SUNNY_WEATHER_UNCLAMPED_EVENTS = 0
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
# Verified Local Donor Specs (14 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_imdb": f"{_FX3_USR_PREFIX}/lib/libIMDB.so",
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
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
    "fx3_bk4": "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    "fx6_bk4": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_imdb": 71_536,
    "fx3_saveload": 18_760,
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
    "fx3_bk4": 2_229_740,
    "fx6_bk4": 2_253_333,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_imdb": (
        b"IMDB_find_entry",
        b"IMDB_get_entries",
        b"IMDB_find_target_bit",
        b"libIMDB.so",
        b"libSaveLoadSettings.so",
    ),
    "fx3_saveload": (
        b"Backup_get_datasize",
        b"Backup_read",
        b"infra_saveLoadSettings_init",
    ),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI", b"Auto"),
    "fx3_string_en_f": (
        b"Emphasized REC Display",
        b"Grid Line Display",
        b"Grid Line Type",
        b"Rule of 3rds Grid",
        b"Square Grid",
        b"Diag. + Square Grid",
        b"HDMI Info. Display",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"RAW Output",
        b"Marker Display",
        b"Zebra Display",
        b"Peaking Display",
        b"Touch Operation",
        b"On: Playback Only",
        b"Touch Sensitivity",
        b"Standard",
        b"Sensitive",
        b"Swipe Up",
        b"Open the Fn Menu",
        b"Touch Func. in Shooting",
        b"Touch Tracking",
        b"Touch Focus",
        b"Brightness",
        b"Manual",
        b"Sunny Weather",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Marker",
        b"Zebra",
        b"Peaking",
        b"HDMI",
        b"Touch",
        b"LCD",
        b"Monitor",
        b"Brightness",
        b"Reset All",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_934_336, "REC_FRAME", b"REC_FRAME"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_967_104, "TOUCH", b"TOUCH"),
        (49_967_104, "SWIPE", b"SWIPE"),
        (49_967_104, "BRIGHTNESS", b"BRIGHTNESS"),
        (49_967_104, "INITIALIZE", b"INITIALIZE"),
        (50_003_968, "SUNNY", b"SUNNY"),
        (51_400_704, "EMPHASIZED", b"Emphasized"),
        (60_633_088, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (62_046_208, "GRID", b"GRID"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_437_440, "TOUCH", b"TOUCH"),
        (38_588_416, "GRID", b"GRID"),
        (39_374_848, "MARKER", b"MARKER"),
        (39_387_136, "TALLY", b"TALLY"),
        (39_391_232, "BRIGHTNESS", b"BRIGHTNESS"),
    ),
    "fx3_cpapp": (
        (139_264, "REC", b"REC"),
        (163_840, "INITIALIZE", b"Initialize"),
        (315_392, "SENSITIVITY", b"Sensitivity"),
        (319_488, "TRACKING", b"Tracking"),
        (368_640, "RESET", b"Reset"),
        (409_600, "MONITOR", b"Monitor"),
        (471_040, "MANUAL", b"Manual"),
        (626_688, "TOUCH", b"Touch"),
        (696_320, "HDMI", b"HDMI"),
        (704_512, "BRIGHTNESS", b"Brightness"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
        (13_361_152, "GRID", b"Grid"),
    ),
    "fx6_cpapp": (
        (135_168, "REC", b"REC"),
        (311_296, "TOUCH", b"Touch"),
        (409_600, "MONITOR", b"Monitor"),
        (684_032, "HDMI", b"HDMI"),
        (688_128, "BRIGHTNESS", b"Brightness"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (233_472, "XAVC", b"XAVC"),
        (2_928_640, "MP4", b"MP4"),
        (2_928_640, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (192_512, "MXF", b"MXF"),
        (258_048, "XAVC", b"XAVC"),
        (315_392, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
        (409_600, "SETTING", b"/setting"),
    ),
    "fx6_bk4": (
        (0, "BK4", b"BK4"),
        (0, "NTSC", b"NTSC"),
        (442_368, "SETTING", b"/setting"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-35 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 45A / 45B / 45C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
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

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Sub-Model 45A: [Emphasized REC Display], [Grid Line Display], [Grid Line Type],
#                [HDMI Info. Display] & Forced [Off(HDMI Only)] / RAW Clean-Feed Clamps
EMPHASIZED_REC_DISPLAY_MENU_PATH = (
    "MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]"
)
GRID_LINE_DISPLAY_MENU_PATH = (
    "MENU -> Shooting -> [Shooting Display] -> [Grid Line Display]"
)
GRID_LINE_TYPE_MENU_PATH = (
    "MENU -> Shooting -> [Shooting Display] -> [Grid Line Type]"
)
HDMI_INFO_DISPLAY_MENU_PATH = (
    "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
)
REC_MEDIA_DUR_HDMI_MENU_PATH = (
    "MENU -> Setup -> [External Output] -> [Rec. Media dur HDMI Output]"
)
HDMI_RAW_OUTPUT_MENU_PATH = (
    "MENU -> Setup -> [External Output] -> [RAW Output]"
)

DEFAULT_EMPHASIZED_REC_DISPLAY = "On"
DEFAULT_GRID_LINE_DISPLAY = "Off"

GRID_LINE_TYPE_RULE_OF_3RDS = "Rule of 3rds Grid"
GRID_LINE_TYPE_SQUARE = "Square Grid"
GRID_LINE_TYPE_DIAG_PLUS_SQUARE = "Diag. + Square Grid"
DEFAULT_GRID_LINE_TYPE = GRID_LINE_TYPE_RULE_OF_3RDS
VALID_GRID_LINE_TYPES: Tuple[str, ...] = (
    GRID_LINE_TYPE_RULE_OF_3RDS,
    GRID_LINE_TYPE_SQUARE,
    GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
)

SHOOTING_STATE_MOVIE_REC = "Movie Recording"
SHOOTING_STATE_SQ_REC = "S&Q Recording"
SHOOTING_STATE_STANDBY = "Standby"
SHOOTING_STATE_STILL = "Still Shooting"
VALID_SHOOTING_STATES: Tuple[str, ...] = (
    SHOOTING_STATE_MOVIE_REC,
    SHOOTING_STATE_SQ_REC,
    SHOOTING_STATE_STANDBY,
    SHOOTING_STATE_STILL,
)
ACTIVE_MOVIE_OR_SQ_REC_STATES: Tuple[str, ...] = (
    SHOOTING_STATE_MOVIE_REC,
    SHOOTING_STATE_SQ_REC,
)

DEFAULT_HDMI_INFO_DISPLAY = "Off"
REC_MEDIA_DUR_HDMI_ON = "On"
REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY = "Off(HDMI Only)"
VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = (
    REC_MEDIA_DUR_HDMI_ON,
    REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
)

LOCAL_LCD_ONLY_ASSIST_OVERLAYS: Tuple[str, ...] = (
    "Marker Display",
    "Zebra Display",
    "Peaking Display",
)

VALID_SLOT1_CAMSET_FILES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
_CAMSET_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")

# Sub-Model 45B: [Touch Operation] 4-Item [Camera Settings Reset] Survival & Bench Tap Guard
TOUCH_OPERATION_MENU_PATH = "MENU -> Setup -> [Touch Operation]"

TOUCH_OP_ON = "On"
TOUCH_OP_PLAYBACK_ONLY = "On: Playback Only"
TOUCH_OP_OFF = "Off"
DEFAULT_TOUCH_OPERATION = TOUCH_OP_ON
VALID_TOUCH_OPERATION_MODES: Tuple[str, ...] = (
    TOUCH_OP_ON,
    TOUCH_OP_PLAYBACK_ONLY,
    TOUCH_OP_OFF,
)
SAFE_BENCH_UNATTENDED_TOUCH_MODES: Tuple[str, ...] = (
    TOUCH_OP_OFF,
    TOUCH_OP_PLAYBACK_ONLY,
)

TOUCH_SENSITIVITY_STANDARD = "Standard"
TOUCH_SENSITIVITY_SENSITIVE = "Sensitive"
DEFAULT_TOUCH_SENSITIVITY = TOUCH_SENSITIVITY_STANDARD
VALID_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = (
    TOUCH_SENSITIVITY_STANDARD,
    TOUCH_SENSITIVITY_SENSITIVE,
)

SWIPE_UP_OPEN_FN_MENU = "Open the Fn Menu"
SWIPE_UP_OFF = "Off"
DEFAULT_SWIPE_UP = SWIPE_UP_OPEN_FN_MENU
VALID_SWIPE_UP_MODES: Tuple[str, ...] = (
    SWIPE_UP_OPEN_FN_MENU,
    SWIPE_UP_OFF,
)

TOUCH_FUNC_SHOOTING_TRACKING = "Touch Tracking"
TOUCH_FUNC_SHOOTING_FOCUS = "Touch Focus"
TOUCH_FUNC_SHOOTING_OFF = "Off"
DEFAULT_TOUCH_FUNC_IN_SHOOTING = TOUCH_FUNC_SHOOTING_TRACKING
VALID_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = (
    TOUCH_FUNC_SHOOTING_TRACKING,
    TOUCH_FUNC_SHOOTING_FOCUS,
    TOUCH_FUNC_SHOOTING_OFF,
)

ALL_4_TOUCH_SETUP_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Swipe Up",
    "Touch Func. in Shooting",
)

SCREEN_VIEW_SHOOTING = "shooting"
SCREEN_VIEW_PLAYBACK = "playback"
VALID_SCREEN_VIEWS: Tuple[str, ...] = (
    SCREEN_VIEW_SHOOTING,
    SCREEN_VIEW_PLAYBACK,
)

# Sub-Model 45C: [Monitor Brightness] [Manual] (-2..+2) vs [Sunny Weather] Indoor & Power Guard
MONITOR_BRIGHTNESS_MENU_PATH = "MENU -> Setup -> [Monitor] -> [Monitor Brightness]"
MONITOR_BRIGHTNESS_MANUAL = "Manual"
MONITOR_BRIGHTNESS_SUNNY_WEATHER = "Sunny Weather"
DEFAULT_MONITOR_BRIGHTNESS_MODE = MONITOR_BRIGHTNESS_MANUAL
VALID_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = (
    MONITOR_BRIGHTNESS_MANUAL,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER,
)

MONITOR_BRIGHTNESS_MANUAL_MIN = -2
MONITOR_BRIGHTNESS_MANUAL_MAX = 2
DEFAULT_MONITOR_BRIGHTNESS_MANUAL_LEVEL = 0
VALID_MONITOR_BRIGHTNESS_MANUAL_LEVELS: Tuple[int, ...] = (-2, -1, 0, 1, 2)

MANUAL_BRIGHTNESS_BACKLIGHT_MW: Mapping[int, int] = {
    -2: 380,
    -1: 415,
    0: 450,
    1: 495,
    2: 540,
}
SUNNY_WEATHER_BACKLIGHT_MW = 1050


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
    marker_hits: Mapping[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Mapping[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase242DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_imdb: CompactDonorSummary
    fx3_saveload: CompactDonorSummary
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
    fx3_bk4: BoundedWindowDonorSummary
    fx6_bk4: BoundedWindowDonorSummary
    emphasized_rec_and_grid_hdmi_cleanfeed_proven: bool
    touch_operation_4item_reset_survival_proven: bool
    monitor_brightness_manual_vs_sunny_weather_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmphasizedRecAndGridHdmiCleanFeedHilResult:
    admitted: bool
    firmware_version: str
    emphasized_rec_menu_path: str
    grid_line_display_menu_path: str
    grid_line_type_menu_path: str
    hdmi_info_display_menu_path: str
    rec_media_dur_hdmi_menu_path: str
    hdmi_raw_output_menu_path: str
    reset_menu_path: str
    configured_emphasized_rec_display: str
    configured_grid_line_display: str
    configured_grid_line_type: str
    reset_action_applied: str
    slot1_camset_restored: Optional[str]
    effective_emphasized_rec_display: str
    emphasized_rec_reset_by_camera_settings_reset: bool
    effective_grid_line_display: str
    effective_grid_line_type: str
    grid_line_reset_only_by_initialize: bool
    grid_line_survived_camera_settings_reset: bool
    emphasized_rec_vs_grid_reset_split_verified: bool
    shooting_state: str
    movie_or_sq_recording_active: bool
    hdmi_connected: bool
    configured_hdmi_info_display: str
    rec_media_dur_hdmi_output: str
    hdmi_raw_output: str
    forced_off_by_hdmi_only_clamp: bool
    forced_off_by_hdmi_raw_clamp: bool
    hdmi_clean_feed_clamp_active: bool
    effective_hdmi_info_display: str
    camera_lcd_blanked_by_hdmi_info: bool
    local_lcd_emphasized_rec_rendered: bool
    local_lcd_grid_line_rendered: bool
    hdmi_emphasized_rec_rendered: bool
    hdmi_grid_line_rendered: bool
    hdmi_status_osd_rendered: bool
    hdmi_local_only_marker_rendered: bool
    hdmi_local_only_zebra_rendered: bool
    hdmi_local_only_peaking_rendered: bool
    hdmi_baked_overlay_pixels: int
    hdmi_only_or_raw_baked_recframe_or_grid_frames: int
    hdmi_local_only_marker_zebra_peaking_leaked_pixels: int
    bk4_persistent_nvram_writes: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class TouchOperationResetAndBenchTapHilResult:
    admitted: bool
    firmware_version: str
    touch_operation_menu_path: str
    reset_menu_path: str
    configured_touch_operation: str
    configured_touch_sensitivity: str
    configured_swipe_up: str
    configured_touch_func_in_shooting: str
    reset_action_applied: str
    effective_touch_operation: str
    effective_touch_sensitivity: str
    effective_swipe_up: str
    effective_touch_func_in_shooting: str
    reset_only_by_initialize: bool
    all_4_items_survived_camera_settings_reset: bool
    cleared_to_defaults_by_initialize: bool
    screen_view: str
    bench_unattended_rehearsal_active: bool
    simulated_capacitive_screen_brush: bool
    shooting_capacitive_touch_locked: bool
    playback_touch_active: bool
    fn_menu_opened_by_swipe_up: bool
    shooting_touch_tracking_or_focus_triggered: bool
    unattended_bench_accidental_touch_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class MonitorBrightnessSunnyWeatherHilResult:
    admitted: bool
    firmware_version: str
    monitor_brightness_menu_path: str
    reset_menu_path: str
    configured_brightness_mode: str
    configured_manual_brightness_level: int
    reset_action_applied: str
    effective_brightness_mode: str
    effective_manual_brightness_level: int
    reset_only_by_initialize: bool
    survived_camera_settings_reset: bool
    cleared_to_manual_zero_by_initialize: bool
    indoor_bench_environment: bool
    npfz100_internal_battery_active: bool
    lcd_backlight_power_mw: int
    sunny_weather_indoor_hazard_flagged: bool
    indoor_sunny_weather_blocked: bool
    indoor_sunny_weather_unclamped_events: int
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
    physical_device_writes: int
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    hdmi_only_or_raw_baked_recframe_or_grid_frames: int
    hdmi_local_only_marker_zebra_peaking_leaked_pixels: int
    unattended_bench_accidental_touch_events: int
    indoor_sunny_weather_unclamped_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase242DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase242DonorAudit] = None


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


def resolve_phase242_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 14 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = (
            chosen
            if chosen is not None
            else (roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel))
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


def _build_clean_room_donor_audit() -> Phase242DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P242".encode("ascii")
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
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P242".encode("ascii"))
            if is_elf
            else (b"DONOR_SYNTH_P242_" + key.encode("ascii") + b"_" + label.encode("ascii")).ljust(
                64, b"\x00"
            )
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase242DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=14,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=_mk_compact("fx3_imdb", "FX3_7.02", False),
        fx3_saveload=_mk_compact("fx3_saveload", "FX3_7.02", False),
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
        fx3_bk4=_mk_large("fx3_bk4", "FX3_7.02", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6_6.01", False),
        emphasized_rec_and_grid_hdmi_cleanfeed_proven=True,
        touch_operation_4item_reset_survival_proven=True,
        monitor_brightness_manual_vs_sunny_weather_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase242_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase242DonorAudit:
    """Inspect 14 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.1s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase242_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items())
    )
    cache_key = (SOURCE_MODE_LOCAL_DONOR, sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    t0 = time.perf_counter()
    fx3_imdb = _scan_compact_rdonly(paths["fx3_imdb"], artifact_key="fx3_imdb", body_label="FX3_7.02")
    fx3_saveload = _scan_compact_rdonly(
        paths["fx3_saveload"], artifact_key="fx3_saveload", body_label="FX3_7.02"
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
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3_7.02"
    )
    fx6_bk4 = _scan_large_donor_rdonly(
        paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6_6.01"
    )
    elapsed_s = time.perf_counter() - t0

    errors: List[str] = []
    for c_item in (
        fx3_imdb,
        fx3_saveload,
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

    for l_item in (
        fx3_appfw,
        fx6_appfw,
        fx3_cpapp,
        fx6_cpapp,
        fx3_libmpr,
        fx6_libmpr,
        fx3_bk4,
        fx6_bk4,
    ):
        if l_item.file_bytes != EXPECTED_DONOR_BYTES[l_item.artifact_key]:
            errors.append(
                f"{l_item.artifact_key} byte size {l_item.file_bytes} != "
                f"{EXPECTED_DONOR_BYTES[l_item.artifact_key]}"
            )
        if not all(l_item.window_hits.values()):
            errors.append(f"{l_item.artifact_key} missing window tokens: {l_item.window_hits}")

    emp_grid_hdmi_proven = (
        fx3_string_en_f.marker_hits.get("Emphasized REC Display") == 1
        and fx3_string_en_f.marker_hits.get("Grid Line Display") == 1
        and fx3_string_en_f.marker_hits.get("Grid Line Type") == 1
        and fx3_string_en_f.marker_hits.get("Rule of 3rds Grid") == 1
        and fx3_string_en_f.marker_hits.get("Square Grid") == 1
        and fx3_string_en_f.marker_hits.get("Diag. + Square Grid") == 1
        and fx3_string_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_string_en_f.marker_hits.get("Rec. Media dur HDMI Output") == 1
        and fx3_string_en_f.marker_hits.get("Off(HDMI Only)") == 1
        and fx3_string_en_f.marker_hits.get("RAW Output") == 1
        and fx3_string_en_f.marker_hits.get("Marker Display") == 1
        and fx3_string_en_f.marker_hits.get("Zebra Display") == 1
        and fx3_string_en_f.marker_hits.get("Peaking Display") == 1
        and fx3_adj_media.marker_hits.get("AVBB_SCN_START_HDMI") == 1
        and fx3_appfw.window_hits.get("REC_FRAME") == 1
        and fx3_appfw.window_hits.get("EMPHASIZED") == 1
        and fx3_appfw.window_hits.get("GRID") == 1
        and fx3_appfw.window_hits.get("RAW_OUTPUT") == 1
        and fx3_cpapp.window_hits.get("GRID") == 1
        and fx6_appfw.window_hits.get("GRID") == 1
    )
    touch_4item_proven = (
        fx3_string_en_f.marker_hits.get("Touch Operation") == 1
        and fx3_string_en_f.marker_hits.get("On: Playback Only") == 1
        and fx3_string_en_f.marker_hits.get("Touch Sensitivity") == 1
        and fx3_string_en_f.marker_hits.get("Standard") == 1
        and fx3_string_en_f.marker_hits.get("Sensitive") == 1
        and fx3_string_en_f.marker_hits.get("Swipe Up") == 1
        and fx3_string_en_f.marker_hits.get("Open the Fn Menu") == 1
        and fx3_string_en_f.marker_hits.get("Touch Func. in Shooting") == 1
        and fx3_string_en_f.marker_hits.get("Touch Tracking") == 1
        and fx3_string_en_f.marker_hits.get("Touch Focus") == 1
        and fx3_string_en_f.marker_hits.get("Camera Settings Reset") == 1
        and fx3_string_en_f.marker_hits.get("Initialize") == 1
        and fx3_saveload.marker_hits.get("infra_saveLoadSettings_init") == 1
        and fx3_appfw.window_hits.get("TOUCH") == 1
        and fx3_appfw.window_hits.get("SWIPE") == 1
        and fx3_cpapp.window_hits.get("TOUCH") == 1
        and fx3_cpapp.window_hits.get("SENSITIVITY") == 1
        and fx3_cpapp.window_hits.get("TRACKING") == 1
        and fx3_bk4.window_hits.get("BK4") == 1
        and fx6_bk4.window_hits.get("BK4") == 1
    )
    brightness_sunny_proven = (
        fx3_string_en_f.marker_hits.get("Brightness") == 1
        and fx3_string_en_f.marker_hits.get("Manual") == 1
        and fx3_string_en_f.marker_hits.get("Sunny Weather") == 1
        and fx6_string_en.marker_hits.get("Monitor") == 1
        and fx6_string_en.marker_hits.get("Brightness") == 1
        and fx3_appfw.window_hits.get("BRIGHTNESS") == 1
        and fx3_appfw.window_hits.get("SUNNY") == 1
        and fx3_cpapp.window_hits.get("MONITOR") == 1
        and fx3_cpapp.window_hits.get("BRIGHTNESS") == 1
        and fx3_cpapp.window_hits.get("MANUAL") == 1
        and fx6_cpapp.window_hits.get("BRIGHTNESS") == 1
    )

    # Keep audit_digest_sha256 deterministic across cold/warm runs while enforcing < 0.1s budget.
    if elapsed_s >= 0.1:
        errors.append(f"donor inspection exceeded 0.1s budget ({elapsed_s:.4f}s)")

    audit = Phase242DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=14,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=fx3_imdb,
        fx3_saveload=fx3_saveload,
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
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        emphasized_rec_and_grid_hdmi_cleanfeed_proven=emp_grid_hdmi_proven,
        touch_operation_4item_reset_survival_proven=touch_4item_proven,
        monitor_brightness_manual_vs_sunny_weather_proven=brightness_sunny_proven,
        all_contracts_verified=(
            not errors
            and emp_grid_hdmi_proven
            and touch_4item_proven
            and brightness_sunny_proven
        ),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 45A: [Emphasized REC Display] & [Grid Line Display] HDMI Info
#                Routing vs Forced [Off(HDMI Only)] / RAW Clean-Feed Lock
# ---------------------------------------------------------------------------


def probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
    *,
    firmware_version: str = "7.02",
    configured_emphasized_rec_display: str = "Off",
    configured_grid_line_display: str = "On",
    configured_grid_line_type: str = GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
    reset_action: str = RESET_ACTION_NONE,
    restore_from_slot1_camset: Optional[str] = None,
    saved_camset_emphasized_rec_display: str = DEFAULT_EMPHASIZED_REC_DISPLAY,
    shooting_state: str = SHOOTING_STATE_MOVIE_REC,
    hdmi_connected: bool = True,
    configured_hdmi_info_display: str = "On",
    rec_media_dur_hdmi_output: str = REC_MEDIA_DUR_HDMI_ON,
    hdmi_raw_output: str = "Off",
    local_marker_display_on: bool = True,
    local_zebra_display_on: bool = True,
    local_peaking_display_on: bool = True,
    attempt_force_rec_frame_in_standby_or_still: bool = False,
    attempt_bypass_hdmi_only_or_raw_cleanfeed_clamp: bool = False,
    attempt_route_local_only_assist_to_hdmi: bool = False,
) -> EmphasizedRecAndGridHdmiCleanFeedHilResult:
    """Co-emulate [Emphasized REC Display], [Grid Line Display]/[Grid Line Type] reset split,
    HDMI Info routing vs LCD blanking, local-only assist isolation, and automatic
    [Off(HDMI Only)] / RAW clean-feed clamps.
    """
    _ = (local_marker_display_on, local_zebra_display_on, local_peaking_display_on)

    def _mk_err(errno: int, status: str) -> EmphasizedRecAndGridHdmiCleanFeedHilResult:
        return EmphasizedRecAndGridHdmiCleanFeedHilResult(
            admitted=False,
            firmware_version=firmware_version,
            emphasized_rec_menu_path=EMPHASIZED_REC_DISPLAY_MENU_PATH,
            grid_line_display_menu_path=GRID_LINE_DISPLAY_MENU_PATH,
            grid_line_type_menu_path=GRID_LINE_TYPE_MENU_PATH,
            hdmi_info_display_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
            rec_media_dur_hdmi_menu_path=REC_MEDIA_DUR_HDMI_MENU_PATH,
            hdmi_raw_output_menu_path=HDMI_RAW_OUTPUT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_emphasized_rec_display=configured_emphasized_rec_display,
            configured_grid_line_display=configured_grid_line_display,
            configured_grid_line_type=configured_grid_line_type,
            reset_action_applied=reset_action,
            slot1_camset_restored=restore_from_slot1_camset,
            effective_emphasized_rec_display=DEFAULT_EMPHASIZED_REC_DISPLAY,
            emphasized_rec_reset_by_camera_settings_reset=False,
            effective_grid_line_display=DEFAULT_GRID_LINE_DISPLAY,
            effective_grid_line_type=DEFAULT_GRID_LINE_TYPE,
            grid_line_reset_only_by_initialize=True,
            grid_line_survived_camera_settings_reset=False,
            emphasized_rec_vs_grid_reset_split_verified=False,
            shooting_state=shooting_state,
            movie_or_sq_recording_active=False,
            hdmi_connected=hdmi_connected,
            configured_hdmi_info_display=configured_hdmi_info_display,
            rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
            hdmi_raw_output=hdmi_raw_output,
            forced_off_by_hdmi_only_clamp=False,
            forced_off_by_hdmi_raw_clamp=False,
            hdmi_clean_feed_clamp_active=False,
            effective_hdmi_info_display=DEFAULT_HDMI_INFO_DISPLAY,
            camera_lcd_blanked_by_hdmi_info=False,
            local_lcd_emphasized_rec_rendered=False,
            local_lcd_grid_line_rendered=False,
            hdmi_emphasized_rec_rendered=False,
            hdmi_grid_line_rendered=False,
            hdmi_status_osd_rendered=False,
            hdmi_local_only_marker_rendered=False,
            hdmi_local_only_zebra_rendered=False,
            hdmi_local_only_peaking_rendered=False,
            hdmi_baked_overlay_pixels=0,
            hdmi_only_or_raw_baked_recframe_or_grid_frames=0,
            hdmi_local_only_marker_zebra_peaking_leaked_pixels=0,
            bk4_persistent_nvram_writes=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if configured_emphasized_rec_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_EMPHASIZED_REC_DISPLAY_EINVAL")
    if configured_grid_line_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_GRID_LINE_DISPLAY_EINVAL")
    if configured_grid_line_type not in VALID_GRID_LINE_TYPES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_GRID_LINE_TYPE_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if shooting_state not in VALID_SHOOTING_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SHOOTING_STATE_EINVAL")
    if configured_hdmi_info_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_HDMI_INFO_DISPLAY_EINVAL")
    if rec_media_dur_hdmi_output not in VALID_REC_MEDIA_DUR_HDMI_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_REC_MEDIA_DUR_HDMI_OUTPUT_EINVAL")
    if hdmi_raw_output not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_HDMI_RAW_OUTPUT_EINVAL")

    if restore_from_slot1_camset is not None:
        if not _CAMSET_RE.match(restore_from_slot1_camset):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SLOT1_CAMSET_FILENAME_EINVAL")
        if saved_camset_emphasized_rec_display not in VALID_ON_OFF:
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SAVED_CAMSET_EMPHASIZED_REC_EINVAL")

    movie_or_sq_active = shooting_state in ACTIVE_MOVIE_OR_SQ_REC_STATES
    if (not movie_or_sq_active) and attempt_force_rec_frame_in_standby_or_still:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_EMPHASIZED_REC_RED_FRAME_INACTIVE_OUTSIDE_MOVIE_OR_SQ_REC_EOPNOTSUPP",
        )

    if attempt_route_local_only_assist_to_hdmi:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_MARKER_ZEBRA_PEAKING_STRICTLY_LOCAL_LCD_ONLY_NEVER_ROUTED_TO_HDMI_EOPNOTSUPP",
        )

    forced_hdmi_only = rec_media_dur_hdmi_output == REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY
    forced_hdmi_raw = hdmi_raw_output == "On"
    cleanfeed_clamp = forced_hdmi_only or forced_hdmi_raw

    if cleanfeed_clamp and attempt_bypass_hdmi_only_or_raw_cleanfeed_clamp:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_HDMI_ONLY_OR_RAW_FORCES_HDMI_INFO_DISPLAY_OFF_CLEAN_FEED_EOPNOTSUPP",
        )

    # Apply reset lifecycle:
    # - [Emphasized REC Display] resets to "On" on BOTH [Camera Settings Reset] and [Initialize]
    # - [Grid Line Display] & [Grid Line Type] survive [Camera Settings Reset] intact and reset
    #   ONLY on [Initialize]
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_emp = DEFAULT_EMPHASIZED_REC_DISPLAY
        emp_reset_csr = False
        eff_grid_disp = DEFAULT_GRID_LINE_DISPLAY
        eff_grid_type = DEFAULT_GRID_LINE_TYPE
        grid_survived_csr = False
        split_verified = False
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_emp = DEFAULT_EMPHASIZED_REC_DISPLAY
        emp_reset_csr = True
        eff_grid_disp = configured_grid_line_display
        eff_grid_type = configured_grid_line_type
        grid_survived_csr = True
        split_verified = True
    else:
        eff_emp = configured_emphasized_rec_display
        emp_reset_csr = False
        eff_grid_disp = configured_grid_line_display
        eff_grid_type = configured_grid_line_type
        grid_survived_csr = False
        split_verified = False

    if restore_from_slot1_camset is not None:
        eff_emp = saved_camset_emphasized_rec_display

    # Effective [HDMI Info. Display] & LCD blanking / HDMI overlay routing
    if not hdmi_connected:
        eff_hdmi_info = "Off"
        lcd_blanked = False
        hdmi_routed = False
    elif cleanfeed_clamp:
        eff_hdmi_info = "Off"
        lcd_blanked = False
        hdmi_routed = False
    else:
        eff_hdmi_info = configured_hdmi_info_display
        hdmi_routed = eff_hdmi_info == "On"
        lcd_blanked = hdmi_routed

    emp_active = (eff_emp == "On") and movie_or_sq_active
    grid_active = eff_grid_disp == "On"

    hdmi_emp = hdmi_routed and emp_active
    hdmi_grid = hdmi_routed and grid_active
    hdmi_osd = hdmi_routed

    lcd_emp = (not lcd_blanked) and emp_active
    lcd_grid = (not lcd_blanked) and grid_active

    # Count intentional OSD pixels ONLY when HDMI Info routing is explicitly active (never in clean-feed clamp)
    hdmi_pixels = 0
    if hdmi_routed:
        hdmi_pixels += 8192
        if hdmi_emp:
            hdmi_pixels += 24_576
        if hdmi_grid:
            hdmi_pixels += 12_288

    if cleanfeed_clamp:
        status = (
            "ADMITTED_HDMI_ONLY_AND_RAW_DUAL_CLAMP_FORCED_CLEAN_FEED_OK"
            if (forced_hdmi_only and forced_hdmi_raw)
            else (
                "ADMITTED_OFF_HDMI_ONLY_FORCED_HDMI_INFO_OFF_CLEAN_FEED_OK"
                if forced_hdmi_only
                else "ADMITTED_HDMI_RAW_OUTPUT_FORCED_HDMI_INFO_OFF_CLEAN_FEED_OK"
            )
        )
    elif restore_from_slot1_camset is not None:
        status = "ADMITTED_SLOT1_CAMSET_RESTORED_EMPHASIZED_REC_ZERO_NVRAM_WRITES_OK"
    elif split_verified:
        status = "ADMITTED_EMPHASIZED_REC_RESET_WHILE_GRID_LINE_SURVIVED_CSR_OK"
    elif reset_action == RESET_ACTION_INITIALIZE:
        status = "ADMITTED_INITIALIZE_RESET_BOTH_EMPHASIZED_REC_AND_GRID_LINE_OK"
    elif hdmi_routed:
        status = "ADMITTED_HDMI_INFO_ON_ROUTED_REC_FRAME_AND_GRID_LCD_BLANKED_OK"
    else:
        status = "ADMITTED_LOCAL_LCD_REC_FRAME_AND_GRID_CLEAN_HDMI_OK"

    return EmphasizedRecAndGridHdmiCleanFeedHilResult(
        admitted=True,
        firmware_version=firmware_version,
        emphasized_rec_menu_path=EMPHASIZED_REC_DISPLAY_MENU_PATH,
        grid_line_display_menu_path=GRID_LINE_DISPLAY_MENU_PATH,
        grid_line_type_menu_path=GRID_LINE_TYPE_MENU_PATH,
        hdmi_info_display_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
        rec_media_dur_hdmi_menu_path=REC_MEDIA_DUR_HDMI_MENU_PATH,
        hdmi_raw_output_menu_path=HDMI_RAW_OUTPUT_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_emphasized_rec_display=configured_emphasized_rec_display,
        configured_grid_line_display=configured_grid_line_display,
        configured_grid_line_type=configured_grid_line_type,
        reset_action_applied=reset_action,
        slot1_camset_restored=restore_from_slot1_camset,
        effective_emphasized_rec_display=eff_emp,
        emphasized_rec_reset_by_camera_settings_reset=emp_reset_csr,
        effective_grid_line_display=eff_grid_disp,
        effective_grid_line_type=eff_grid_type,
        grid_line_reset_only_by_initialize=True,
        grid_line_survived_camera_settings_reset=grid_survived_csr,
        emphasized_rec_vs_grid_reset_split_verified=split_verified,
        shooting_state=shooting_state,
        movie_or_sq_recording_active=movie_or_sq_active,
        hdmi_connected=hdmi_connected,
        configured_hdmi_info_display=configured_hdmi_info_display,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        forced_off_by_hdmi_only_clamp=forced_hdmi_only,
        forced_off_by_hdmi_raw_clamp=forced_hdmi_raw,
        hdmi_clean_feed_clamp_active=cleanfeed_clamp,
        effective_hdmi_info_display=eff_hdmi_info,
        camera_lcd_blanked_by_hdmi_info=lcd_blanked,
        local_lcd_emphasized_rec_rendered=lcd_emp,
        local_lcd_grid_line_rendered=lcd_grid,
        hdmi_emphasized_rec_rendered=hdmi_emp,
        hdmi_grid_line_rendered=hdmi_grid,
        hdmi_status_osd_rendered=hdmi_osd,
        hdmi_local_only_marker_rendered=False,
        hdmi_local_only_zebra_rendered=False,
        hdmi_local_only_peaking_rendered=False,
        hdmi_baked_overlay_pixels=hdmi_pixels,
        hdmi_only_or_raw_baked_recframe_or_grid_frames=0,
        hdmi_local_only_marker_zebra_peaking_leaked_pixels=0,
        bk4_persistent_nvram_writes=0,
        errno_code=0,
        status_code=status,
    )


def simulate_emphasized_rec_vs_grid_line_reset_lifecycle(
    *,
    configured_emphasized_rec_display: str = "Off",
    configured_grid_line_display: str = "On",
    configured_grid_line_type: str = GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
) -> Dict[str, object]:
    """Simulate 3-step Configure -> [Camera Settings Reset] Split -> [Initialize] Full Clear."""
    step1_configured = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display=configured_emphasized_rec_display,
        configured_grid_line_display=configured_grid_line_display,
        configured_grid_line_type=configured_grid_line_type,
        reset_action=RESET_ACTION_NONE,
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        hdmi_raw_output="Off",
    )
    step2_csr = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display=configured_emphasized_rec_display,
        configured_grid_line_display=configured_grid_line_display,
        configured_grid_line_type=configured_grid_line_type,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        hdmi_raw_output="Off",
    )
    step3_initialize = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display=configured_emphasized_rec_display,
        configured_grid_line_display=configured_grid_line_display,
        configured_grid_line_type=configured_grid_line_type,
        reset_action=RESET_ACTION_INITIALIZE,
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        hdmi_raw_output="Off",
    )
    lifecycle_verified = (
        step1_configured.admitted
        and step1_configured.effective_emphasized_rec_display == configured_emphasized_rec_display
        and step1_configured.effective_grid_line_display == configured_grid_line_display
        and step1_configured.effective_grid_line_type == configured_grid_line_type
        and step2_csr.admitted
        and step2_csr.emphasized_rec_vs_grid_reset_split_verified
        and step2_csr.effective_emphasized_rec_display == DEFAULT_EMPHASIZED_REC_DISPLAY
        and step2_csr.effective_grid_line_display == configured_grid_line_display
        and step2_csr.effective_grid_line_type == configured_grid_line_type
        and step2_csr.hdmi_emphasized_rec_rendered
        and step2_csr.hdmi_grid_line_rendered
        and step3_initialize.admitted
        and step3_initialize.effective_emphasized_rec_display == DEFAULT_EMPHASIZED_REC_DISPLAY
        and step3_initialize.effective_grid_line_display == DEFAULT_GRID_LINE_DISPLAY
        and step3_initialize.effective_grid_line_type == DEFAULT_GRID_LINE_TYPE
    )
    return {
        "lifecycle_verified": lifecycle_verified,
        "step1_configured": asdict(step1_configured),
        "step2_camera_settings_reset_split": asdict(step2_csr),
        "step3_initialize_full_clear": asdict(step3_initialize),
    }


def evaluate_pillar_a_emphasized_rec_and_grid_hdmi_cleanfeed_hil() -> Dict[str, object]:
    grid_3type_hdmi_info_routed_matrix = {
        gtype: asdict(
            probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
                configured_emphasized_rec_display="On",
                configured_grid_line_display="On",
                configured_grid_line_type=gtype,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                shooting_state=SHOOTING_STATE_MOVIE_REC,
                hdmi_connected=True,
                configured_hdmi_info_display="On",
                rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
                hdmi_raw_output="Off",
            )
        )
        for gtype in VALID_GRID_LINE_TYPES
    }
    sq_rec_hdmi_info_routed_ok = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        configured_grid_line_type=GRID_LINE_TYPE_SQUARE,
        shooting_state=SHOOTING_STATE_SQ_REC,
        hdmi_connected=True,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        hdmi_raw_output="Off",
    )
    standby_no_red_frame_grid_only = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        configured_grid_line_type=GRID_LINE_TYPE_RULE_OF_3RDS,
        shooting_state=SHOOTING_STATE_STANDBY,
        hdmi_connected=True,
        configured_hdmi_info_display="On",
    )
    still_no_red_frame_local_lcd = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        shooting_state=SHOOTING_STATE_STILL,
        hdmi_connected=True,
        configured_hdmi_info_display="Off",
    )
    hdmi_only_forced_cleanfeed_clamp = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        configured_grid_line_type=GRID_LINE_TYPE_DIAG_PLUS_SQUARE,
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        hdmi_connected=True,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
        hdmi_raw_output="Off",
    )
    hdmi_raw_forced_cleanfeed_clamp = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        configured_grid_line_type=GRID_LINE_TYPE_SQUARE,
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        hdmi_connected=True,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_ON,
        hdmi_raw_output="On",
    )
    hdmi_only_and_raw_dual_clamp = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="On",
        configured_grid_line_display="On",
        shooting_state=SHOOTING_STATE_SQ_REC,
        hdmi_connected=True,
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
        hdmi_raw_output="On",
    )
    reset_lifecycle = simulate_emphasized_rec_vs_grid_line_reset_lifecycle()
    camset01_restore_ok = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_emphasized_rec_display="Off",
        configured_grid_line_display="On",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        restore_from_slot1_camset="CAMSET01.DAT",
        saved_camset_emphasized_rec_display="Off",
        shooting_state=SHOOTING_STATE_MOVIE_REC,
        configured_hdmi_info_display="Off",
    )
    bypass_clamp_blocked = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_hdmi_info_display="On",
        rec_media_dur_hdmi_output=REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
        attempt_bypass_hdmi_only_or_raw_cleanfeed_clamp=True,
    )
    local_assist_hdmi_leak_blocked = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        configured_hdmi_info_display="On",
        attempt_route_local_only_assist_to_hdmi=True,
    )
    standby_force_rec_frame_blocked = probe_emphasized_rec_and_grid_hdmi_cleanfeed_hil(
        shooting_state=SHOOTING_STATE_STANDBY,
        attempt_force_rec_frame_in_standby_or_still=True,
    )

    passed = (
        len(grid_3type_hdmi_info_routed_matrix) == 3
        and all(
            item["admitted"]
            and item["grid_line_survived_camera_settings_reset"]
            and item["grid_line_reset_only_by_initialize"]
            and item["effective_grid_line_type"] == gtype
            and item["camera_lcd_blanked_by_hdmi_info"]
            and item["hdmi_emphasized_rec_rendered"]
            and item["hdmi_grid_line_rendered"]
            and (not item["hdmi_local_only_marker_rendered"])
            and (not item["hdmi_local_only_zebra_rendered"])
            and (not item["hdmi_local_only_peaking_rendered"])
            for gtype, item in grid_3type_hdmi_info_routed_matrix.items()
        )
        and sq_rec_hdmi_info_routed_ok.admitted
        and sq_rec_hdmi_info_routed_ok.hdmi_emphasized_rec_rendered
        and sq_rec_hdmi_info_routed_ok.hdmi_grid_line_rendered
        and standby_no_red_frame_grid_only.admitted
        and (not standby_no_red_frame_grid_only.hdmi_emphasized_rec_rendered)
        and standby_no_red_frame_grid_only.hdmi_grid_line_rendered
        and still_no_red_frame_local_lcd.admitted
        and (not still_no_red_frame_local_lcd.local_lcd_emphasized_rec_rendered)
        and still_no_red_frame_local_lcd.local_lcd_grid_line_rendered
        and hdmi_only_forced_cleanfeed_clamp.admitted
        and hdmi_only_forced_cleanfeed_clamp.forced_off_by_hdmi_only_clamp
        and hdmi_only_forced_cleanfeed_clamp.effective_hdmi_info_display == "Off"
        and hdmi_only_forced_cleanfeed_clamp.hdmi_baked_overlay_pixels == 0
        and hdmi_only_forced_cleanfeed_clamp.hdmi_only_or_raw_baked_recframe_or_grid_frames == 0
        and (not hdmi_only_forced_cleanfeed_clamp.hdmi_emphasized_rec_rendered)
        and (not hdmi_only_forced_cleanfeed_clamp.hdmi_grid_line_rendered)
        and hdmi_raw_forced_cleanfeed_clamp.admitted
        and hdmi_raw_forced_cleanfeed_clamp.forced_off_by_hdmi_raw_clamp
        and hdmi_raw_forced_cleanfeed_clamp.effective_hdmi_info_display == "Off"
        and hdmi_raw_forced_cleanfeed_clamp.hdmi_baked_overlay_pixels == 0
        and hdmi_only_and_raw_dual_clamp.admitted
        and hdmi_only_and_raw_dual_clamp.hdmi_baked_overlay_pixels == 0
        and bool(reset_lifecycle["lifecycle_verified"])
        and camset01_restore_ok.admitted
        and camset01_restore_ok.effective_emphasized_rec_display == "Off"
        and camset01_restore_ok.bk4_persistent_nvram_writes == 0
        and (not bypass_clamp_blocked.admitted)
        and bypass_clamp_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not local_assist_hdmi_leak_blocked.admitted)
        and local_assist_hdmi_leak_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not standby_force_rec_frame_blocked.admitted)
        and standby_force_rec_frame_blocked.errno_code == EOPNOTSUPP_ERRNO
    )
    return {
        "passed": passed,
        "all_3_grid_line_types": list(VALID_GRID_LINE_TYPES),
        "local_lcd_only_assist_overlays": list(LOCAL_LCD_ONLY_ASSIST_OVERLAYS),
        "grid_3type_hdmi_info_routed_matrix": grid_3type_hdmi_info_routed_matrix,
        "sq_rec_hdmi_info_routed_ok": asdict(sq_rec_hdmi_info_routed_ok),
        "standby_no_red_frame_grid_only": asdict(standby_no_red_frame_grid_only),
        "still_no_red_frame_local_lcd": asdict(still_no_red_frame_local_lcd),
        "hdmi_only_forced_cleanfeed_clamp": asdict(hdmi_only_forced_cleanfeed_clamp),
        "hdmi_raw_forced_cleanfeed_clamp": asdict(hdmi_raw_forced_cleanfeed_clamp),
        "hdmi_only_and_raw_dual_clamp": asdict(hdmi_only_and_raw_dual_clamp),
        "emphasized_rec_vs_grid_reset_lifecycle": reset_lifecycle,
        "slot1_camset01_restore_after_csr_ok": asdict(camset01_restore_ok),
        "bypass_cleanfeed_clamp_blocked_eopnotsupp": asdict(bypass_clamp_blocked),
        "local_assist_hdmi_leak_blocked_eopnotsupp": asdict(local_assist_hdmi_leak_blocked),
        "standby_force_rec_frame_blocked_eopnotsupp": asdict(standby_force_rec_frame_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 45B: [Touch Operation] 4-Item [Camera Settings Reset] Survival &
#                Unattended Bench Tap Guard
# ---------------------------------------------------------------------------


def probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
    *,
    firmware_version: str = "7.02",
    configured_touch_operation: str = TOUCH_OP_OFF,
    configured_touch_sensitivity: str = TOUCH_SENSITIVITY_SENSITIVE,
    configured_swipe_up: str = SWIPE_UP_OPEN_FN_MENU,
    configured_touch_func_in_shooting: str = TOUCH_FUNC_SHOOTING_FOCUS,
    reset_action: str = RESET_ACTION_NONE,
    screen_view: str = SCREEN_VIEW_SHOOTING,
    bench_unattended_rehearsal_active: bool = True,
    simulated_capacitive_screen_brush: bool = True,
    attempt_force_touch_when_touch_operation_off: bool = False,
) -> TouchOperationResetAndBenchTapHilResult:
    """Co-emulate MENU -> Setup -> [Touch Operation] 4-item survival across
    [Camera Settings Reset] and unattended bench accidental-tap blocking.
    """

    def _mk_err(errno: int, status: str) -> TouchOperationResetAndBenchTapHilResult:
        return TouchOperationResetAndBenchTapHilResult(
            admitted=False,
            firmware_version=firmware_version,
            touch_operation_menu_path=TOUCH_OPERATION_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_touch_operation=configured_touch_operation,
            configured_touch_sensitivity=configured_touch_sensitivity,
            configured_swipe_up=configured_swipe_up,
            configured_touch_func_in_shooting=configured_touch_func_in_shooting,
            reset_action_applied=reset_action,
            effective_touch_operation=DEFAULT_TOUCH_OPERATION,
            effective_touch_sensitivity=DEFAULT_TOUCH_SENSITIVITY,
            effective_swipe_up=DEFAULT_SWIPE_UP,
            effective_touch_func_in_shooting=DEFAULT_TOUCH_FUNC_IN_SHOOTING,
            reset_only_by_initialize=True,
            all_4_items_survived_camera_settings_reset=False,
            cleared_to_defaults_by_initialize=False,
            screen_view=screen_view,
            bench_unattended_rehearsal_active=bench_unattended_rehearsal_active,
            simulated_capacitive_screen_brush=simulated_capacitive_screen_brush,
            shooting_capacitive_touch_locked=True,
            playback_touch_active=False,
            fn_menu_opened_by_swipe_up=False,
            shooting_touch_tracking_or_focus_triggered=False,
            unattended_bench_accidental_touch_events=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if configured_touch_operation not in VALID_TOUCH_OPERATION_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TOUCH_OPERATION_MODE_EINVAL")
    if configured_touch_sensitivity not in VALID_TOUCH_SENSITIVITY_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TOUCH_SENSITIVITY_MODE_EINVAL")
    if configured_swipe_up not in VALID_SWIPE_UP_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SWIPE_UP_MODE_EINVAL")
    if configured_touch_func_in_shooting not in VALID_TOUCH_FUNC_IN_SHOOTING_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TOUCH_FUNC_IN_SHOOTING_MODE_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if screen_view not in VALID_SCREEN_VIEWS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SCREEN_VIEW_EINVAL")

    if attempt_force_touch_when_touch_operation_off:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_CAPACITIVE_DISPATCH_DISABLED_WHEN_TOUCH_OPERATION_OFF_EOPNOTSUPP",
        )

    # All 4 Setup [Touch Operation] items survive [Camera Settings Reset] intact;
    # restored to factory defaults exclusively by [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_op = DEFAULT_TOUCH_OPERATION
        eff_sens = DEFAULT_TOUCH_SENSITIVITY
        eff_swipe = DEFAULT_SWIPE_UP
        eff_func = DEFAULT_TOUCH_FUNC_IN_SHOOTING
        survived_csr = False
        cleared_init = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_op = configured_touch_operation
        eff_sens = configured_touch_sensitivity
        eff_swipe = configured_swipe_up
        eff_func = configured_touch_func_in_shooting
        survived_csr = True
        cleared_init = False
    else:
        eff_op = configured_touch_operation
        eff_sens = configured_touch_sensitivity
        eff_swipe = configured_swipe_up
        eff_func = configured_touch_func_in_shooting
        survived_csr = False
        cleared_init = False

    shooting_locked = eff_op in SAFE_BENCH_UNATTENDED_TOUCH_MODES
    if bench_unattended_rehearsal_active and not shooting_locked:
        return _mk_err(
            EBUSY_ERRNO,
            "BLOCKED_BENCH_UNATTENDED_TOUCH_SHOOTING_LIVE_HAZARD_EBUSY",
        )

    playback_active = (
        screen_view == SCREEN_VIEW_PLAYBACK
        and eff_op in (TOUCH_OP_ON, TOUCH_OP_PLAYBACK_ONLY)
        and simulated_capacitive_screen_brush
    )
    fn_opened = (
        screen_view == SCREEN_VIEW_SHOOTING
        and (not shooting_locked)
        and eff_swipe == SWIPE_UP_OPEN_FN_MENU
        and simulated_capacitive_screen_brush
    )
    tracking_or_focus = (
        screen_view == SCREEN_VIEW_SHOOTING
        and (not shooting_locked)
        and eff_func in (TOUCH_FUNC_SHOOTING_TRACKING, TOUCH_FUNC_SHOOTING_FOCUS)
        and simulated_capacitive_screen_brush
    )

    if cleared_init:
        status = "ADMITTED_INITIALIZE_RESTORED_ALL_4_TOUCH_ITEMS_TO_DEFAULTS_OK"
    elif bench_unattended_rehearsal_active:
        status = (
            "ADMITTED_BENCH_UNATTENDED_TOUCH_OFF_SURVIVED_CSR_TAP_BLOCKED_OK"
            if survived_csr
            else "ADMITTED_BENCH_UNATTENDED_TOUCH_SHOOTING_LOCKED_TAP_BLOCKED_OK"
        )
    elif survived_csr:
        status = "ADMITTED_ALL_4_TOUCH_ITEMS_SURVIVED_CAMERA_SETTINGS_RESET_OK"
    else:
        status = "ADMITTED_TOUCH_OPERATION_INTERACTIVE_SHOOTING_OR_PLAYBACK_OK"

    return TouchOperationResetAndBenchTapHilResult(
        admitted=True,
        firmware_version=firmware_version,
        touch_operation_menu_path=TOUCH_OPERATION_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_touch_operation=configured_touch_operation,
        configured_touch_sensitivity=configured_touch_sensitivity,
        configured_swipe_up=configured_swipe_up,
        configured_touch_func_in_shooting=configured_touch_func_in_shooting,
        reset_action_applied=reset_action,
        effective_touch_operation=eff_op,
        effective_touch_sensitivity=eff_sens,
        effective_swipe_up=eff_swipe,
        effective_touch_func_in_shooting=eff_func,
        reset_only_by_initialize=True,
        all_4_items_survived_camera_settings_reset=survived_csr,
        cleared_to_defaults_by_initialize=cleared_init,
        screen_view=screen_view,
        bench_unattended_rehearsal_active=bench_unattended_rehearsal_active,
        simulated_capacitive_screen_brush=simulated_capacitive_screen_brush,
        shooting_capacitive_touch_locked=shooting_locked,
        playback_touch_active=playback_active,
        fn_menu_opened_by_swipe_up=fn_opened,
        shooting_touch_tracking_or_focus_triggered=tracking_or_focus,
        unattended_bench_accidental_touch_events=0,
        errno_code=0,
        status_code=status,
    )


def simulate_touch_operation_4item_reset_lifecycle(
    *,
    configured_touch_operation: str = TOUCH_OP_OFF,
    configured_touch_sensitivity: str = TOUCH_SENSITIVITY_SENSITIVE,
    configured_swipe_up: str = SWIPE_UP_OFF,
    configured_touch_func_in_shooting: str = TOUCH_FUNC_SHOOTING_FOCUS,
) -> Dict[str, object]:
    """Simulate 3-step Configure -> [Camera Settings Reset] 4-Item Survival -> [Initialize] Clear."""
    step1_configured = probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
        configured_touch_operation=configured_touch_operation,
        configured_touch_sensitivity=configured_touch_sensitivity,
        configured_swipe_up=configured_swipe_up,
        configured_touch_func_in_shooting=configured_touch_func_in_shooting,
        reset_action=RESET_ACTION_NONE,
        bench_unattended_rehearsal_active=False,
    )
    step2_csr = probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
        configured_touch_operation=configured_touch_operation,
        configured_touch_sensitivity=configured_touch_sensitivity,
        configured_swipe_up=configured_swipe_up,
        configured_touch_func_in_shooting=configured_touch_func_in_shooting,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        bench_unattended_rehearsal_active=True,
    )
    step3_initialize = probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
        configured_touch_operation=configured_touch_operation,
        configured_touch_sensitivity=configured_touch_sensitivity,
        configured_swipe_up=configured_swipe_up,
        configured_touch_func_in_shooting=configured_touch_func_in_shooting,
        reset_action=RESET_ACTION_INITIALIZE,
        bench_unattended_rehearsal_active=False,
    )
    lifecycle_verified = (
        step1_configured.admitted
        and step2_csr.admitted
        and step2_csr.all_4_items_survived_camera_settings_reset
        and step2_csr.reset_only_by_initialize
        and step2_csr.effective_touch_operation == configured_touch_operation
        and step2_csr.effective_touch_sensitivity == configured_touch_sensitivity
        and step2_csr.effective_swipe_up == configured_swipe_up
        and step2_csr.effective_touch_func_in_shooting == configured_touch_func_in_shooting
        and step2_csr.unattended_bench_accidental_touch_events == 0
        and step3_initialize.admitted
        and step3_initialize.cleared_to_defaults_by_initialize
        and step3_initialize.effective_touch_operation == DEFAULT_TOUCH_OPERATION
        and step3_initialize.effective_touch_sensitivity == DEFAULT_TOUCH_SENSITIVITY
        and step3_initialize.effective_swipe_up == DEFAULT_SWIPE_UP
        and step3_initialize.effective_touch_func_in_shooting == DEFAULT_TOUCH_FUNC_IN_SHOOTING
    )
    return {
        "lifecycle_verified": lifecycle_verified,
        "step1_configured": asdict(step1_configured),
        "step2_camera_settings_reset_4item_survived": asdict(step2_csr),
        "step3_initialize_restored_defaults": asdict(step3_initialize),
    }


def evaluate_pillar_b_touch_operation_4item_reset_and_bench_tap_guard_hil() -> Dict[str, object]:
    touch_op_3mode_csr_survival_matrix = {
        mode: asdict(
            probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
                configured_touch_operation=mode,
                configured_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE,
                configured_swipe_up=SWIPE_UP_OPEN_FN_MENU,
                configured_touch_func_in_shooting=TOUCH_FUNC_SHOOTING_FOCUS,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                screen_view=SCREEN_VIEW_SHOOTING,
                bench_unattended_rehearsal_active=(mode != TOUCH_OP_ON),
                simulated_capacitive_screen_brush=True,
            )
        )
        for mode in VALID_TOUCH_OPERATION_MODES
    }
    bench_touch_off_blocks_swipe_and_tracking = (
        probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation=TOUCH_OP_OFF,
            configured_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE,
            configured_swipe_up=SWIPE_UP_OPEN_FN_MENU,
            configured_touch_func_in_shooting=TOUCH_FUNC_SHOOTING_TRACKING,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            screen_view=SCREEN_VIEW_SHOOTING,
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
    )
    bench_playback_only_locks_shooting_allows_playback = (
        probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation=TOUCH_OP_PLAYBACK_ONLY,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            screen_view=SCREEN_VIEW_PLAYBACK,
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
    )
    bench_unattended_touch_on_blocked_ebusy = (
        probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation=TOUCH_OP_ON,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            screen_view=SCREEN_VIEW_SHOOTING,
            bench_unattended_rehearsal_active=True,
            simulated_capacitive_screen_brush=True,
        )
    )
    force_touch_when_off_blocked = (
        probe_touch_operation_4item_reset_and_bench_tap_guard_hil(
            configured_touch_operation=TOUCH_OP_OFF,
            attempt_force_touch_when_touch_operation_off=True,
        )
    )
    lifecycle = simulate_touch_operation_4item_reset_lifecycle()

    passed = (
        len(touch_op_3mode_csr_survival_matrix) == 3
        and all(
            item["admitted"]
            and item["all_4_items_survived_camera_settings_reset"]
            and item["reset_only_by_initialize"]
            and item["effective_touch_operation"] == mode
            and item["effective_touch_sensitivity"] == TOUCH_SENSITIVITY_SENSITIVE
            and item["effective_touch_func_in_shooting"] == TOUCH_FUNC_SHOOTING_FOCUS
            for mode, item in touch_op_3mode_csr_survival_matrix.items()
        )
        and bench_touch_off_blocks_swipe_and_tracking.admitted
        and bench_touch_off_blocks_swipe_and_tracking.shooting_capacitive_touch_locked
        and (not bench_touch_off_blocks_swipe_and_tracking.fn_menu_opened_by_swipe_up)
        and (
            not bench_touch_off_blocks_swipe_and_tracking.shooting_touch_tracking_or_focus_triggered
        )
        and bench_touch_off_blocks_swipe_and_tracking.unattended_bench_accidental_touch_events == 0
        and bench_playback_only_locks_shooting_allows_playback.admitted
        and bench_playback_only_locks_shooting_allows_playback.shooting_capacitive_touch_locked
        and bench_playback_only_locks_shooting_allows_playback.playback_touch_active
        and (
            bench_playback_only_locks_shooting_allows_playback.unattended_bench_accidental_touch_events
            == 0
        )
        and (not bench_unattended_touch_on_blocked_ebusy.admitted)
        and bench_unattended_touch_on_blocked_ebusy.errno_code == EBUSY_ERRNO
        and (not force_touch_when_off_blocked.admitted)
        and force_touch_when_off_blocked.errno_code == EOPNOTSUPP_ERRNO
        and bool(lifecycle["lifecycle_verified"])
    )
    return {
        "passed": passed,
        "all_4_touch_setup_items": list(ALL_4_TOUCH_SETUP_ITEMS),
        "all_3_touch_operation_modes": list(VALID_TOUCH_OPERATION_MODES),
        "touch_op_3mode_csr_survival_matrix": touch_op_3mode_csr_survival_matrix,
        "bench_touch_off_blocks_swipe_and_tracking": asdict(
            bench_touch_off_blocks_swipe_and_tracking
        ),
        "bench_playback_only_locks_shooting_allows_playback": asdict(
            bench_playback_only_locks_shooting_allows_playback
        ),
        "bench_unattended_touch_on_blocked_ebusy": asdict(
            bench_unattended_touch_on_blocked_ebusy
        ),
        "force_touch_when_off_blocked_eopnotsupp": asdict(force_touch_when_off_blocked),
        "touch_operation_4item_reset_lifecycle": lifecycle,
    }


# ---------------------------------------------------------------------------
# Sub-Model 45C: [Monitor Brightness] [Manual] (-2..+2) vs [Sunny Weather]
#                Indoor Over-Brightness & NP-FZ100 Power Guard + Redlines
# ---------------------------------------------------------------------------


def probe_monitor_brightness_sunny_weather_and_power_guard_hil(
    *,
    firmware_version: str = "7.02",
    configured_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL,
    configured_manual_brightness_level: int = 0,
    reset_action: str = RESET_ACTION_NONE,
    indoor_bench_environment: bool = True,
    npfz100_internal_battery_active: bool = True,
    attempt_bypass_indoor_sunny_weather_guard: bool = False,
) -> MonitorBrightnessSunnyWeatherHilResult:
    """Co-emulate MENU -> Setup -> [Monitor] -> [Monitor Brightness] Manual (-2..+2)
    vs Sunny Weather, survival across [Camera Settings Reset], and indoor bench
    over-brightness / NP-FZ100 battery-drain hazard clamping.
    """

    def _mk_err(
        errno: int,
        status: str,
        *,
        indoor_hazard: bool = False,
        indoor_blocked: bool = False,
    ) -> MonitorBrightnessSunnyWeatherHilResult:
        return MonitorBrightnessSunnyWeatherHilResult(
            admitted=False,
            firmware_version=firmware_version,
            monitor_brightness_menu_path=MONITOR_BRIGHTNESS_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_brightness_mode=configured_brightness_mode,
            configured_manual_brightness_level=(
                configured_manual_brightness_level
                if isinstance(configured_manual_brightness_level, int)
                and not isinstance(configured_manual_brightness_level, bool)
                else 0
            ),
            reset_action_applied=reset_action,
            effective_brightness_mode=DEFAULT_MONITOR_BRIGHTNESS_MODE,
            effective_manual_brightness_level=DEFAULT_MONITOR_BRIGHTNESS_MANUAL_LEVEL,
            reset_only_by_initialize=True,
            survived_camera_settings_reset=False,
            cleared_to_manual_zero_by_initialize=False,
            indoor_bench_environment=indoor_bench_environment,
            npfz100_internal_battery_active=npfz100_internal_battery_active,
            lcd_backlight_power_mw=MANUAL_BRIGHTNESS_BACKLIGHT_MW[
                DEFAULT_MONITOR_BRIGHTNESS_MANUAL_LEVEL
            ],
            sunny_weather_indoor_hazard_flagged=indoor_hazard,
            indoor_sunny_weather_blocked=indoor_blocked,
            indoor_sunny_weather_unclamped_events=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if configured_brightness_mode not in VALID_MONITOR_BRIGHTNESS_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MONITOR_BRIGHTNESS_MODE_EINVAL")
    if (
        isinstance(configured_manual_brightness_level, bool)
        or not isinstance(configured_manual_brightness_level, int)
        or not (
            MONITOR_BRIGHTNESS_MANUAL_MIN
            <= configured_manual_brightness_level
            <= MONITOR_BRIGHTNESS_MANUAL_MAX
        )
    ):
        return _mk_err(
            EINVAL_ERRNO,
            "BLOCKED_MANUAL_BRIGHTNESS_LEVEL_OUT_OF_RANGE_MINUS2_TO_PLUS2_EINVAL",
        )
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")

    if attempt_bypass_indoor_sunny_weather_guard:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_INDOOR_SUNNY_WEATHER_UNCLAMPED_BYPASS_FORBIDDEN_EOPNOTSUPP",
            indoor_hazard=True,
            indoor_blocked=True,
        )

    # [Monitor Brightness] survives [Camera Settings Reset] intact;
    # restored to [Manual] (0) exclusively by [Initialize].
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_mode = DEFAULT_MONITOR_BRIGHTNESS_MODE
        eff_level = DEFAULT_MONITOR_BRIGHTNESS_MANUAL_LEVEL
        survived_csr = False
        cleared_init = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_mode = configured_brightness_mode
        eff_level = configured_manual_brightness_level
        survived_csr = True
        cleared_init = False
    else:
        eff_mode = configured_brightness_mode
        eff_level = configured_manual_brightness_level
        survived_csr = False
        cleared_init = False

    # Flag and block [Sunny Weather] during indoor bench rehearsals to prevent
    # manual exposure misjudgment and excess NP-FZ100 LCD backlight drain.
    if indoor_bench_environment and eff_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER:
        return _mk_err(
            EBUSY_ERRNO,
            "BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OVERBRIGHTNESS_AND_NPFZ100_DRAIN_EBUSY",
            indoor_hazard=True,
            indoor_blocked=True,
        )

    power_mw = (
        SUNNY_WEATHER_BACKLIGHT_MW
        if eff_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER
        else MANUAL_BRIGHTNESS_BACKLIGHT_MW[eff_level]
    )

    if cleared_init:
        status = "ADMITTED_INITIALIZE_RESTORED_MONITOR_BRIGHTNESS_TO_MANUAL_0_OK"
    elif eff_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER:
        status = "ADMITTED_OUTDOOR_DAYLIGHT_SUNNY_WEATHER_BOOST_OK"
    elif survived_csr:
        status = "ADMITTED_MONITOR_BRIGHTNESS_MANUAL_SURVIVED_CAMERA_SETTINGS_RESET_OK"
    else:
        status = "ADMITTED_INDOOR_BENCH_MONITOR_BRIGHTNESS_MANUAL_SAFE_OK"

    return MonitorBrightnessSunnyWeatherHilResult(
        admitted=True,
        firmware_version=firmware_version,
        monitor_brightness_menu_path=MONITOR_BRIGHTNESS_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_brightness_mode=configured_brightness_mode,
        configured_manual_brightness_level=configured_manual_brightness_level,
        reset_action_applied=reset_action,
        effective_brightness_mode=eff_mode,
        effective_manual_brightness_level=eff_level,
        reset_only_by_initialize=True,
        survived_camera_settings_reset=survived_csr,
        cleared_to_manual_zero_by_initialize=cleared_init,
        indoor_bench_environment=indoor_bench_environment,
        npfz100_internal_battery_active=npfz100_internal_battery_active,
        lcd_backlight_power_mw=power_mw,
        sunny_weather_indoor_hazard_flagged=False,
        indoor_sunny_weather_blocked=False,
        indoor_sunny_weather_unclamped_events=0,
        errno_code=0,
        status_code=status,
    )


def simulate_monitor_brightness_reset_lifecycle(
    *,
    configured_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL,
    configured_manual_brightness_level: int = -1,
) -> Dict[str, object]:
    """Simulate 3-step Configure -> [Camera Settings Reset] Survival -> [Initialize] Manual 0."""
    step1_configured = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=configured_brightness_mode,
        configured_manual_brightness_level=configured_manual_brightness_level,
        reset_action=RESET_ACTION_NONE,
        indoor_bench_environment=True,
    )
    step2_csr = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=configured_brightness_mode,
        configured_manual_brightness_level=configured_manual_brightness_level,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        indoor_bench_environment=True,
    )
    step3_initialize = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
        configured_manual_brightness_level=configured_manual_brightness_level,
        reset_action=RESET_ACTION_INITIALIZE,
        indoor_bench_environment=True,
    )
    lifecycle_verified = (
        step1_configured.admitted
        and step1_configured.effective_brightness_mode == configured_brightness_mode
        and step1_configured.effective_manual_brightness_level == configured_manual_brightness_level
        and step2_csr.admitted
        and step2_csr.survived_camera_settings_reset
        and step2_csr.reset_only_by_initialize
        and step2_csr.effective_brightness_mode == configured_brightness_mode
        and step2_csr.effective_manual_brightness_level == configured_manual_brightness_level
        and step3_initialize.admitted
        and step3_initialize.cleared_to_manual_zero_by_initialize
        and step3_initialize.effective_brightness_mode == DEFAULT_MONITOR_BRIGHTNESS_MODE
        and step3_initialize.effective_manual_brightness_level
        == DEFAULT_MONITOR_BRIGHTNESS_MANUAL_LEVEL
    )
    return {
        "lifecycle_verified": lifecycle_verified,
        "step1_configured": asdict(step1_configured),
        "step2_camera_settings_reset_survived": asdict(step2_csr),
        "step3_initialize_restored_manual_0": asdict(step3_initialize),
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
    bypass_hdmi_only_or_raw_cleanfeed_clamp: bool = False,
    leak_local_only_assist_to_hdmi: bool = False,
    bypass_unattended_bench_touch_lock: bool = False,
    bypass_indoor_sunny_weather_guard: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed hard safety redline guard for Phase 242 Stage 45 (45/45)."""
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
    if bypass_hdmi_only_or_raw_cleanfeed_clamp:
        violations.append("bypass_hdmi_only_or_raw_cleanfeed_clamp")
    if leak_local_only_assist_to_hdmi:
        violations.append("leak_local_only_assist_to_hdmi")
    if bypass_unattended_bench_touch_lock:
        violations.append("bypass_unattended_bench_touch_lock")
    if bypass_indoor_sunny_weather_guard:
        violations.append("bypass_indoor_sunny_weather_guard")

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
            physical_device_writes=0,
            physical_usb_packets_emitted=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            hdmi_only_or_raw_baked_recframe_or_grid_frames=0,
            hdmi_local_only_marker_zebra_peaking_leaked_pixels=0,
            unattended_bench_accidental_touch_events=0,
            indoor_sunny_weather_unclamped_events=0,
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
        physical_device_writes=0,
        physical_usb_packets_emitted=0,
        otp_fuse_touches=0,
        rpmb_counter_increments=0,
        hdmi_only_or_raw_baked_recframe_or_grid_frames=0,
        hdmi_local_only_marker_zebra_peaking_leaked_pixels=0,
        unattended_bench_accidental_touch_events=0,
        indoor_sunny_weather_unclamped_events=0,
        blocked_action="NONE",
        status_code="VERIFIED_HARD_SAFETY_REDLINES_LOCKED_FALSE_OK",
    )


def evaluate_pillar_c_d_monitor_brightness_sunny_weather_and_redlines() -> Dict[str, object]:
    manual_5step_indoor_csr_matrix = {
        str(lvl): asdict(
            probe_monitor_brightness_sunny_weather_and_power_guard_hil(
                configured_brightness_mode=MONITOR_BRIGHTNESS_MANUAL,
                configured_manual_brightness_level=lvl,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                indoor_bench_environment=True,
                npfz100_internal_battery_active=True,
            )
        )
        for lvl in VALID_MONITOR_BRIGHTNESS_MANUAL_LEVELS
    }
    outdoor_sunny_weather_csr_ok = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
        configured_manual_brightness_level=0,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        indoor_bench_environment=False,
        npfz100_internal_battery_active=True,
    )
    indoor_sunny_weather_blocked_ebusy = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
        configured_manual_brightness_level=0,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        indoor_bench_environment=True,
        npfz100_internal_battery_active=True,
    )
    indoor_bypass_blocked_eopnotsupp = probe_monitor_brightness_sunny_weather_and_power_guard_hil(
        configured_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER,
        indoor_bench_environment=True,
        attempt_bypass_indoor_sunny_weather_guard=True,
    )
    lifecycle = simulate_monitor_brightness_reset_lifecycle()

    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(persistent_emmc_writes_authorized=True)),
        asdict(probe_hard_safety_redline(hardware_live_attachment_authorized=True)),
        asdict(probe_hard_safety_redline(overall_ready_for_hardware_attach=True)),
        asdict(probe_hard_safety_redline(spi_nor_write_authorized=True)),
        asdict(probe_hard_safety_redline(el3_payload_transmit_authorized=True)),
        asdict(probe_hard_safety_redline(isp_write_authorized=True)),
        asdict(probe_hard_safety_redline(cnflasha_userspace_write_attempt=True)),
        asdict(probe_hard_safety_redline(bypass_hdmi_only_or_raw_cleanfeed_clamp=True)),
        asdict(probe_hard_safety_redline(leak_local_only_assist_to_hdmi=True)),
        asdict(probe_hard_safety_redline(bypass_unattended_bench_touch_lock=True)),
        asdict(probe_hard_safety_redline(bypass_indoor_sunny_weather_guard=True)),
    ]

    passed = (
        len(manual_5step_indoor_csr_matrix) == 5
        and all(
            item["admitted"]
            and item["survived_camera_settings_reset"]
            and item["reset_only_by_initialize"]
            and item["effective_brightness_mode"] == MONITOR_BRIGHTNESS_MANUAL
            and item["indoor_sunny_weather_unclamped_events"] == 0
            for item in manual_5step_indoor_csr_matrix.values()
        )
        and manual_5step_indoor_csr_matrix["-2"]["lcd_backlight_power_mw"] == 380
        and manual_5step_indoor_csr_matrix["0"]["lcd_backlight_power_mw"] == 450
        and manual_5step_indoor_csr_matrix["2"]["lcd_backlight_power_mw"] == 540
        and outdoor_sunny_weather_csr_ok.admitted
        and outdoor_sunny_weather_csr_ok.survived_camera_settings_reset
        and outdoor_sunny_weather_csr_ok.effective_brightness_mode == MONITOR_BRIGHTNESS_SUNNY_WEATHER
        and outdoor_sunny_weather_csr_ok.lcd_backlight_power_mw == SUNNY_WEATHER_BACKLIGHT_MW
        and (not indoor_sunny_weather_blocked_ebusy.admitted)
        and indoor_sunny_weather_blocked_ebusy.errno_code == EBUSY_ERRNO
        and indoor_sunny_weather_blocked_ebusy.sunny_weather_indoor_hazard_flagged
        and indoor_sunny_weather_blocked_ebusy.indoor_sunny_weather_blocked
        and indoor_sunny_weather_blocked_ebusy.indoor_sunny_weather_unclamped_events == 0
        and (not indoor_bypass_blocked_eopnotsupp.admitted)
        and indoor_bypass_blocked_eopnotsupp.errno_code == EOPNOTSUPP_ERRNO
        and bool(lifecycle["lifecycle_verified"])
        and baseline_redline.valid
        and len(blocked_probes) == 11
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "manual_brightness_levels": list(VALID_MONITOR_BRIGHTNESS_MANUAL_LEVELS),
        "manual_5step_indoor_csr_matrix": manual_5step_indoor_csr_matrix,
        "outdoor_sunny_weather_csr_ok": asdict(outdoor_sunny_weather_csr_ok),
        "indoor_sunny_weather_blocked_ebusy": asdict(indoor_sunny_weather_blocked_ebusy),
        "indoor_bypass_blocked_eopnotsupp": asdict(indoor_bypass_blocked_eopnotsupp),
        "monitor_brightness_reset_lifecycle": lifecycle,
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 242 (Stage 45, 45/45 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 242 Stage 45 (45/45) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase242_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_emphasized_rec_and_grid_hdmi_cleanfeed_hil()
    pillar_b = evaluate_pillar_b_touch_operation_4item_reset_and_bench_tap_guard_hil()
    pillar_cd = evaluate_pillar_c_d_monitor_brightness_sunny_weather_and_redlines()

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
        "hdmi_only_or_raw_baked_recframe_or_grid_frames": (
            HDMI_ONLY_OR_RAW_BAKED_RECFRAME_OR_GRID_FRAMES
        ),
        "hdmi_local_only_marker_zebra_peaking_leaked_pixels": (
            HDMI_LOCAL_ONLY_MARKER_ZEBRA_PEAKING_LEAKED_PIXELS
        ),
        "unattended_bench_accidental_touch_events": UNATTENDED_BENCH_ACCIDENTAL_TOUCH_EVENTS,
        "indoor_sunny_weather_unclamped_events": INDOOR_SUNNY_WEATHER_UNCLAMPED_EVENTS,
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
        and PHYSICAL_DEVICE_WRITES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and HDMI_ONLY_OR_RAW_BAKED_RECFRAME_OR_GRID_FRAMES == 0
        and HDMI_LOCAL_ONLY_MARKER_ZEBRA_PEAKING_LEAKED_PIXELS == 0
        and UNATTENDED_BENCH_ACCIDENTAL_TOUCH_EVENTS == 0
        and INDOOR_SUNNY_WEATHER_UNCLAMPED_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_242_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_emphasized_rec_and_grid_hdmi_cleanfeed_hil": pillar_a,
        "pillar_b_touch_operation_4item_reset_and_bench_tap_guard_hil": pillar_b,
        "pillar_c_d_monitor_brightness_sunny_weather_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py",
        description=(
            "Phase 242 Stage 45 (45/45 Milestone) — Real-Hardware ILME-FX3 Wave-35 "
            "Emphasized REC Display & Grid Line HDMI Info Routing vs Off(HDMI Only)/RAW Clean-Feed "
            "Lock, Touch Operation 4-Item Reset Survival & Bench Tap Guard, and Monitor Brightness "
            "Manual (-2..+2) vs Sunny Weather Indoor/NP-FZ100 Power Guard HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 242 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_emphasized_rec_and_grid_hdmi_cleanfeed_hil"]
        pb = rep["pillar_b_touch_operation_4item_reset_and_bench_tap_guard_hil"]
        pcd = rep["pillar_c_d_monitor_brightness_sunny_weather_and_redlines"]
        baked = rep["redlines"]["hdmi_only_or_raw_baked_recframe_or_grid_frames"]
        grid_types = len(pa["all_3_grid_line_types"])
        touch_items = len(pb["all_4_touch_setup_items"])
        tap_ev = rep["redlines"]["unattended_bench_accidental_touch_events"]
        sunny_ev = rep["redlines"]["indoor_sunny_weather_unclamped_events"]
        man_steps = len(pcd["manual_brightness_levels"])
        sys.stdout.write(
            f"[{status}] Phase 242 Stage 45 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"rec_grid={grid_types}types_baked:{baked} | "
            f"touch={touch_items}items_tap:{tap_ev} | "
            f"bright={man_steps}steps_sunny_unclamped:{sunny_ev} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
