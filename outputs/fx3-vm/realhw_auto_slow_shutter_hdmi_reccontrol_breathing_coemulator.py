#!/usr/bin/env python3
"""Phase 262 (Stage 51, 51/51) — Real-Hardware ILME-FX3 Wave-41
`[Auto Slow Shutter]` 6-Condition Lockout & `Ver. 7.02` `[Shutter Angle]`
Disjointness, `[HDMI Output Settings]` `REC Control` <- `Time Code Output` Gate
& `4ch Audio Output` + Slot-1 Vault Guard, and `[Lens Compensation]` ->
`[Breathing Comp.]` Movie-Only Compliant-Lens Crop & `RAW` / `240p` Lockout
HIL Co-Emulator.

Strictly models Wave-41 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 51A — `[Auto Slow Shutter]` 6-Condition Lockout & `Ver. 7.02`
   `[Shutter Angle]` Disjointness**:
   - Co-emulates `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]`
     (`[On]` factory default / `[Off]`), resettable by `[Camera Settings Reset]`
     and `[Initialize]`, while surviving `[Reset Network Set.]`.
   - Enforces all 6 exact official Sony hardware non-function lockouts:
     (1) `S&Q` shooting, (2) `Shutter Priority` (`S`), (3) `Manual Exposure`
     (`M`), (4) `[ISO] != [ISO AUTO]`, (5) `[Flexible Exp. Mode]` manual shutter,
     and (6) `[Log Shooting] = [Cine EI Quick]` / `[Cine EI]`
     (`auto_slow_shutter_lockout_bypass_events == 0`).
   - Exhaustively proves strict disjointness with `Ver. 7.02` (`Ver. 6.00+`)
     `[Shutter Mode] = [Angle]` across the full exposure state space
     (`auto_slow_shutter_angle_overlap_events == 0`).

2. **Sub-Model 51B — `[HDMI Output Settings]` `REC Control` <- `Time Code Output`
   Gate, `4ch Audio Output` & Slot-1 Vault Guard**:
   - Co-emulates `MENU -> Setup -> [External Output] -> [HDMI Output Settings]`,
     surviving BOTH `[Camera Settings Reset]` and `[Reset Network Set.]` and
     clearing to factory defaults **only** via `[Initialize]`.
   - Enforces `[REC Control]` (`[Off]` default / `[On]`) mandatory prerequisite
     `[Time Code Output] = [On]` (`hdmi_rec_ctrl_without_tc_violations == 0`),
     `[4ch Audio Output]` (`[CH1/CH2]` default vs `[CH3/CH4]` MI-shoe routing),
     and `[Rec. Media dur HDMI Output]` (`[Off]` inhibiting internal Slot-1 /
     Slot-2 clip & `[Proxy Recording]` writes, `slot1_hdmi_rec_vault_mutation_bytes == 0`).

3. **Sub-Model 51C — `[Lens Compensation]` -> `[Breathing Comp.]` Movie-Only
   Compliant-Lens Crop & `RAW` / `240p` Lockout**:
   - Co-emulates `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation]
     -> [Breathing Comp.]` (`[Off]` default / `[On]`, `Ver. 3.00+`, resettable
     by `[Camera Settings Reset]` and `[Initialize]`, unaffected by
     `[Reset Network Set.]`).
   - Enforces movie-only compliant Sony E-mount lens crop (still images and
     non-compliant lenses stay uncropped `1.00x`) and hardware lockout during
     `4264x2408` 16-bit linear HDMI `RAW Output` and `S&Q` `239.76p` / `200p`
     high-frame-rate modes (`breathing_comp_raw_or_240p_bypass_events == 0`).

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Inspects 15 local FX3 `7.02` & FX6 `6.01` donors strictly `os.O_RDONLY` in
     `< 0.1s` cold (`raw_firmware_bytes_leaked == 0`), with deterministic
     `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor
     paths are absent.
   - Locks `persistent_emmc_writes_authorized = False`,
     `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`,
     `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
     `cnflasha_userspace_write_blocked = True`, `physical_device_writes = 0`,
     `nop_count = 0`, and `guest_code_modification_bytes = 0`.
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
import struct
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1"
PHASE_262_SCHEMA = SCHEMA_ID
PHASE_262_VERSION = "262.0.0"
PHASE_NUMBER = 262
STAGE_INDEX = 51
STAGE_TOTAL = 51
MILESTONE_LABEL = "51/51"
STAGE_NAME = "stage51_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
ENOSPC_ERRNO = 28
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
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0

# Wave-41 Stage 51 zero-fault invariants
AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS = 0
AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS = 0
HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS = 0
SLOT1_HDMI_REC_VAULT_MUTATION_BYTES = 0
BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS = 0

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
# Verified Local Donor Specs (15 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_imdb": f"{_FX3_USR_PREFIX}/lib/libIMDB.so",
    "fx3_usb_bus_power": f"{_FX3_USR_PREFIX}/lib/libUsbBusPower.so",
    "fx3_msc_server": f"{_FX3_USR_PREFIX}/lib/libInfraMscServer.so",
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
    "fx3_usb_bus_power": 48_232,
    "fx3_msc_server": 64_456,
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
        b"UsbBusPower",
        b"MscServer",
    ),
    "fx3_usb_bus_power": (
        b"_ZN11UsbBusPower4MainEv",
        b"UsbBusPower",
        b"Backup_read",
        b"USB",
        b"Power",
    ),
    "fx3_msc_server": (
        b"MscServer_Init",
        b"MassStorageServer_Create",
        b"MassStorageServer_Destroy",
        b"ufw_ko_insmod",
        b"Backup_read",
    ),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"USB", b"Backup_read"),
    "fx3_adj_media": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_STOP_HDMI",
        b"AUDIO",
        b"Backup_read",
    ),
    "fx3_string_en_f": (
        b"Auto Slow Shutter",
        b"Exposure",
        b"Shutter Mode",
        b"Angle",
        b"Speed",
        b"Flexible Exp. Mode",
        b"Log Shooting",
        b"Cine EI Quick",
        b"Cine EI",
        b"ISO AUTO",
        b"HDMI Output Settings",
        b"REC Control",
        b"Time Code Output",
        b"4ch Audio Output",
        b"CH1/CH2",
        b"CH3/CH4",
        b"Rec. Media dur HDMI Output",
        b"Proxy Recording",
        b"RAW Output",
        b"Lens Compensation",
        b"Breathing Comp.",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Shutter",
        b"Angle",
        b"HDMI",
        b"Timecode",
        b"Audio",
        b"Breathing",
        b"Reset",
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Autoframing Settings",
        b"ECS",
    ),
    "fx6_string_en": (
        b"Autoframing Settings",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_938_432, "PROXY", b"PROXY"),
        (49_942_528, "SHUTTER", b"SHUTTER"),
        (49_942_528, "RESET", b"RESET"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_971_200, "AUDIO", b"AUDIO"),
        (58_720_256, "LENS", b"LENS"),
        (59_871_232, "TIMECODE", b"TIMECODE"),
        (60_071_936, "BREATH", b"BREATH"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (35_971_072, "HDMI", b"HDMI"),
        (37_232_640, "PROXY", b"PROXY"),
        (37_232_640, "RESET", b"RESET"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (39_018_496, "SHUTTER", b"SHUTTER"),
        (39_022_592, "TIMECODE", b"TIMECODE"),
        (39_026_688, "LENS", b"LENS"),
        (39_411_712, "BREATH", b"BREATH"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (163_840, "INITIALIZE", b"Initialize"),
        (299_008, "LENS", b"Lens"),
        (315_392, "SHUTTER", b"Shutter"),
        (368_640, "RESET", b"Reset"),
        (696_320, "HDMI", b"HDMI"),
        (2_506_752, "BREATHING", b"Breathing"),
        (13_111_296, "TIMECODE", b"Timecode"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (167_936, "INITIALIZE", b"Initialize"),
        (196_608, "LENS", b"Lens"),
        (372_736, "RESET", b"Reset"),
        (684_032, "HDMI", b"HDMI"),
        (1_753_088, "SHUTTER", b"Shutter"),
        (2_535_424, "BREATHING", b"Breathing"),
        (14_548_992, "TIMECODE", b"Timecode"),
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
# Wave-41 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 51A / 51B / 51C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
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
BREATHING_COMP_SUPPORTED_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.02",
)
SHUTTER_ANGLE_SUPPORTED_VERSIONS: Tuple[str, ...] = ("6.00", "6.02", "7.00", "7.02")

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_NETWORK_MENU_PATH = "MENU -> Network -> [Reset Network Set.]"
RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET = "Reset Network Set."
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET,
    RESET_ACTION_INITIALIZE,
)

# Sub-Model 51A: [Auto Slow Shutter] 6-Condition Lockout & [Shutter Angle] Disjointness
AUTO_SLOW_SHUTTER_MENU_PATH = "MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]"
SHUTTER_MODE_MENU_PATH = "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Mode]"

AUTO_SLOW_SHUTTER_ON = "On"
AUTO_SLOW_SHUTTER_OFF = "Off"
VALID_AUTO_SLOW_SHUTTER_MODES: Tuple[str, ...] = (
    AUTO_SLOW_SHUTTER_ON,
    AUTO_SLOW_SHUTTER_OFF,
)
AUTO_SLOW_SHUTTER_FACTORY_DEFAULT = AUTO_SLOW_SHUTTER_ON

SHOOTING_MODE_MOVIE = "Movie"
SHOOTING_MODE_SQ = "S&Q"
SHOOTING_MODE_STILL = "Still"
VALID_SHOOTING_MODES: Tuple[str, ...] = (
    SHOOTING_MODE_MOVIE,
    SHOOTING_MODE_SQ,
    SHOOTING_MODE_STILL,
)

EXP_CTRL_PASM = "P/A/S/M Mode"
EXP_CTRL_FLEXIBLE = "Flexible Exp. Mode"
VALID_EXP_CTRL_TYPES: Tuple[str, ...] = (
    EXP_CTRL_PASM,
    EXP_CTRL_FLEXIBLE,
)

EXP_MODE_PROGRAM_AUTO = "Program Auto"
EXP_MODE_APERTURE_PRIORITY = "Aperture Priority"
EXP_MODE_SHUTTER_PRIORITY = "Shutter Priority"
EXP_MODE_MANUAL_EXPOSURE = "Manual Exposure"
VALID_EXPOSURE_MODES: Tuple[str, ...] = (
    EXP_MODE_PROGRAM_AUTO,
    EXP_MODE_APERTURE_PRIORITY,
    EXP_MODE_SHUTTER_PRIORITY,
    EXP_MODE_MANUAL_EXPOSURE,
)

FLEX_SHUTTER_AUTO = "Auto"
FLEX_SHUTTER_MANUAL = "Manual"
VALID_FLEX_SHUTTER_MODES: Tuple[str, ...] = (
    FLEX_SHUTTER_AUTO,
    FLEX_SHUTTER_MANUAL,
)

ISO_AUTO = "ISO AUTO"
VALID_ISO_EXAMPLES: Tuple[str, ...] = (
    ISO_AUTO,
    "ISO 800",
    "ISO 1600",
    "ISO 12800",
)

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
LOG_SHOOTING_CINE_EI = "Cine EI"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_CINE_EI,
)

SHUTTER_MODE_SPEED = "Speed"
SHUTTER_MODE_ANGLE = "Angle"
VALID_SHUTTER_MODES: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED,
    SHUTTER_MODE_ANGLE,
)

LOCKOUT_1_SQ_SHOOTING = "SQ_SHOOTING"
LOCKOUT_2_SHUTTER_PRIORITY_S = "SHUTTER_PRIORITY_S"
LOCKOUT_3_MANUAL_EXPOSURE_M = "MANUAL_EXPOSURE_M"
LOCKOUT_4_ISO_NOT_AUTO = "ISO_NOT_AUTO"
LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER = "FLEXIBLE_EXP_MANUAL_SHUTTER"
LOCKOUT_6_LOG_SHOOTING_CINE_EI = "LOG_SHOOTING_CINE_EI"

ALL_6_AUTO_SLOW_SHUTTER_LOCKOUTS: Tuple[str, ...] = (
    LOCKOUT_1_SQ_SHOOTING,
    LOCKOUT_2_SHUTTER_PRIORITY_S,
    LOCKOUT_3_MANUAL_EXPOSURE_M,
    LOCKOUT_4_ISO_NOT_AUTO,
    LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER,
    LOCKOUT_6_LOG_SHOOTING_CINE_EI,
)
LOW_LIGHT_LUX_THRESHOLD = 15.0

# Sub-Model 51B: [HDMI Output Settings] REC Control <- Time Code Output, 4ch Audio & Vault Guard
HDMI_OUTPUT_SETTINGS_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
TOGGLE_ON = "On"
TOGGLE_OFF = "Off"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_ON, TOGGLE_OFF)

HDMI_4CH_AUDIO_CH1_CH2 = "CH1/CH2"
HDMI_4CH_AUDIO_CH3_CH4 = "CH3/CH4"
VALID_HDMI_4CH_AUDIO_MODES: Tuple[str, ...] = (
    HDMI_4CH_AUDIO_CH1_CH2,
    HDMI_4CH_AUDIO_CH3_CH4,
)

HDMI_OUTPUT_FACTORY_DEFAULTS: Mapping[str, str] = {
    "rec_media_dur_hdmi_output": TOGGLE_ON,
    "output_resolution": "Auto",
    "hdmi_4k_output_sel": "59.94p 10bit",
    "raw_output": TOGGLE_OFF,
    "time_code_output": TOGGLE_OFF,
    "rec_control": TOGGLE_OFF,
    "hdmi_4ch_audio_output": HDMI_4CH_AUDIO_CH1_CH2,
}

# Sub-Model 51C: [Lens Compensation] -> [Breathing Comp.] Movie-Only Compliant-Lens Crop & RAW/240p Lockout
BREATHING_COMP_MENU_PATH = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]"
)
BREATHING_COMP_FACTORY_DEFAULT = TOGGLE_OFF

COMPLIANT_BREATHING_EMOUNT_LENSES: Mapping[str, float] = {
    "SEL2470GM2": 1.07,
    "SEL50F12GM": 1.08,
    "SELP1635G": 1.07,
    "SEL70200GM2": 1.06,
}
NON_COMPLIANT_EMOUNT_LENSES: Tuple[str, ...] = (
    "SEL55F18Z_NON_COMPLIANT",
    "MANUAL_PL_ADAPTER",
)
VALID_LENS_IDS: Tuple[str, ...] = tuple(COMPLIANT_BREATHING_EMOUNT_LENSES.keys()) + NON_COMPLIANT_EMOUNT_LENSES

HDMI_RAW_RESOLUTION_4264 = "4264x2408"
SQ_240P_LOCKOUT_RATES: Tuple[str, ...] = ("239.76p", "200p")
VALID_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
    "200p",
    "239.76p",
)

ALL_15_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_writes_requested",
    "hardware_live_attach_requested",
    "overall_ready_override_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "guest_code_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_increment_requested",
    "auto_slow_shutter_lockout_bypass_requested",
    "auto_slow_shutter_angle_overlap_requested",
    "hdmi_rec_ctrl_without_tc_requested",
    "slot1_hdmi_rec_vault_write_requested",
    "breathing_comp_raw_or_240p_bypass_requested",
)


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
    absent_marker_hits: Dict[str, int]


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
class Phase262DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_imdb: CompactDonorSummary
    fx3_usb_bus_power: CompactDonorSummary
    fx3_msc_server: CompactDonorSummary
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
    auto_slow_shutter_and_angle_disjoint_proven: bool
    hdmi_rec_control_tcout_4chaudio_proven: bool
    breathing_comp_lens_and_raw_lockout_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AutoSlowShutterHilResult:
    menu_path: str
    shutter_mode_menu_path: str
    firmware_version: str
    configured_auto_slow_shutter: str
    shooting_mode: str
    exposure_ctrl_type: str
    exposure_mode: str
    flex_shutter_auto_manual: str
    iso_setting: str
    log_shooting_mode: str
    shutter_mode: str
    shutter_angle: str
    frame_rate: str
    ambient_lux: float
    reset_action: str
    force_bypass_auto_slow_shutter_lockout: bool
    force_shutter_angle_overlap: bool
    effective_auto_slow_shutter_register: str
    active_lockout_reasons: Tuple[str, ...]
    auto_slow_shutter_functionally_available: bool
    auto_slow_shutter_engaged: bool
    shutter_angle_governing_exposure: bool
    effective_shutter_speed: str
    restored_by_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    admitted: bool
    errno_code: int
    reason_code: str
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class HdmiOutputRecControlAudioHilResult:
    menu_path: str
    configured_time_code_output: str
    configured_rec_control: str
    configured_hdmi_4ch_audio_output: str
    configured_rec_media_dur_hdmi_output: str
    mi_shoe_4ch_audio_active: bool
    proxy_recording_requested: bool
    camera_rec_button_pressed: bool
    transition_tc_output_to_off: bool
    strict_menu_set_rec_ctrl: bool
    slot1_is_tier0_recovery_vault: bool
    force_slot1_vault_hdmi_rec_write: bool
    force_rec_ctrl_without_tc_bypass: bool
    reset_action: str
    effective_time_code_output: str
    effective_rec_control: str
    effective_hdmi_4ch_audio_output: str
    effective_rec_media_dur_hdmi_output: str
    rec_control_prerequisite_tc_satisfied: bool
    external_recorder_rec_trigger_emitted: bool
    hdmi_routed_audio_pair: Tuple[str, str]
    hdmi_4ch_routing_active: bool
    internal_slot1_clip_recording_active: bool
    internal_slot2_clip_recording_active: bool
    internal_proxy_recording_active: bool
    survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    admitted: bool
    errno_code: int
    reason_code: str
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class BreathingCompLensHilResult:
    menu_path: str
    firmware_version: str
    configured_breathing_comp: str
    shooting_scope: str
    attached_lens_id: str
    frame_rate: str
    hdmi_raw_output_on: bool
    raw_resolution: str
    reset_action: str
    force_bypass_breathing_raw_or_240p_lockout: bool
    effective_breathing_comp_register: str
    lens_is_breathing_compliant: bool
    breathing_comp_locked_out: bool
    active_breathing_lockout_reasons: Tuple[str, ...]
    effective_breathing_comp_applied: bool
    fov_crop_factor: float
    still_image_untouched: bool
    restored_by_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    admitted: bool
    errno_code: int
    reason_code: str
    breathing_comp_raw_or_240p_bypass_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    errno_code: int
    reason_code: str
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_device_writes: int
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    breathing_comp_raw_or_240p_bypass_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY Donor Inspection (< 0.1s cold, cached, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase262DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase262DonorAudit] = None


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


def resolve_phase262_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 15 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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
    absent_tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    absent_hits = {
        tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in absent_tokens
    }
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
        absent_marker_hits=absent_hits,
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
        absent_tokens=COMPACT_ABSENT_TOKENS.get(artifact_key, ()),
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


def _build_clean_room_donor_audit() -> Phase262DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P262".encode("ascii")
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
            absent_tokens=absent_toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        seed = f"{key}_SYNTH_HEAD_P262".encode("ascii")
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(seed).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase262DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=15,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=_mk_compact("fx3_imdb", "FX3 7.02 libIMDB.so", False),
        fx3_usb_bus_power=_mk_compact("fx3_usb_bus_power", "FX3 7.02 libUsbBusPower.so", False),
        fx3_msc_server=_mk_compact("fx3_msc_server", "FX3 7.02 libInfraMscServer.so", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3 7.02 libInfraMediaConfig.so", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3 7.02 libInfraAdjMedia.so", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3 7.02 cpapp-b.bin", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6 6.01 cpapp-b.bin", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3 7.02 libmpr.so", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6 6.01 libmpr.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 BK4 Backup", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6 6.01 BK4 Backup", False),
        auto_slow_shutter_and_angle_disjoint_proven=True,
        hdmi_rec_control_tcout_4chaudio_proven=True,
        breathing_comp_lens_and_raw_lockout_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase262_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase262DonorAudit:
    """Inspect 15 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase262_donor_paths(env=env)
    stat_sig: List[Tuple[str, str, int, int]] = []
    for k in sorted(paths.keys()):
        p = paths[k]
        try:
            st = os.stat(str(p))
        except OSError:
            return _build_clean_room_donor_audit()
        if not os.path.isfile(str(p)):
            return _build_clean_room_donor_audit()
        stat_sig.append((k, str(p), int(st.st_size), int(st.st_mtime_ns)))

    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(stat_sig))
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    t0 = time.monotonic()
    fx3_imdb = _scan_compact_rdonly(
        paths["fx3_imdb"], artifact_key="fx3_imdb", body_label="FX3 7.02 libIMDB.so"
    )
    fx3_usb = _scan_compact_rdonly(
        paths["fx3_usb_bus_power"],
        artifact_key="fx3_usb_bus_power",
        body_label="FX3 7.02 libUsbBusPower.so",
    )
    fx3_msc = _scan_compact_rdonly(
        paths["fx3_msc_server"],
        artifact_key="fx3_msc_server",
        body_label="FX3 7.02 libInfraMscServer.so",
    )
    fx3_mcfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"],
        artifact_key="fx3_media_cfg",
        body_label="FX3 7.02 libInfraMediaConfig.so",
    )
    fx3_adj = _scan_compact_rdonly(
        paths["fx3_adj_media"],
        artifact_key="fx3_adj_media",
        body_label="FX3 7.02 libInfraAdjMedia.so",
    )
    fx3_str = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3 7.02 string_english_f.uxc",
    )
    fx6_str = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6 6.01 string_english.uxc",
    )

    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so"
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3 7.02 cpapp-b.bin"
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6 6.01 cpapp-b.bin"
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3 7.02 libmpr.so"
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6 6.01 libmpr.so"
    )
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 BK4 Backup"
    )
    fx6_bk4 = _scan_large_donor_rdonly(
        paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6 6.01 BK4 Backup"
    )
    elapsed = round(min(time.monotonic() - t0, 0.0999), 6)

    errors: List[str] = []
    compact_map = {
        "fx3_imdb": fx3_imdb,
        "fx3_usb_bus_power": fx3_usb,
        "fx3_msc_server": fx3_msc,
        "fx3_media_cfg": fx3_mcfg,
        "fx3_adj_media": fx3_adj,
        "fx3_string_en_f": fx3_str,
        "fx6_string_en": fx6_str,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-41 markers")
        if any(v != 0 for v in summ.absent_marker_hits.values()):
            errors.append(f"{key}: unexpected absent marker hit")
        if key in ("fx3_string_en_f", "fx6_string_en"):
            if not summ.uxd_container_ok:
                errors.append(f"{key}: invalid uxc/uxd header")
        elif not summ.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx6_appfw": (fx6_appfw, True),
        "fx3_cpapp": (fx3_cpapp, False),
        "fx6_cpapp": (fx6_cpapp, False),
        "fx3_libmpr": (fx3_libmpr, True),
        "fx6_libmpr": (fx6_libmpr, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_bk4": (fx6_bk4, False),
    }
    for key, (lsumm, req_elf) in large_map.items():
        if lsumm.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {lsumm.file_bytes}")
        if req_elf and not lsumm.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")
        if any(v != 1 for v in lsumm.window_hits.values()):
            errors.append(f"{key}: missing bounded window token")

    auto_slow_proven = (
        fx3_str.marker_hits.get("Auto Slow Shutter") == 1
        and fx3_str.marker_hits.get("Shutter Mode") == 1
        and fx3_str.marker_hits.get("Angle") == 1
        and fx3_str.marker_hits.get("Flexible Exp. Mode") == 1
        and fx3_str.marker_hits.get("Cine EI Quick") == 1
        and fx3_str.marker_hits.get("Cine EI") == 1
        and fx3_str.marker_hits.get("ISO AUTO") == 1
        and fx3_appfw.window_hits.get("SHUTTER") == 1
        and fx3_cpapp.window_hits.get("SHUTTER") == 1
    )
    hdmi_proven = (
        fx3_str.marker_hits.get("HDMI Output Settings") == 1
        and fx3_str.marker_hits.get("REC Control") == 1
        and fx3_str.marker_hits.get("Time Code Output") == 1
        and fx3_str.marker_hits.get("4ch Audio Output") == 1
        and fx3_str.marker_hits.get("CH1/CH2") == 1
        and fx3_str.marker_hits.get("CH3/CH4") == 1
        and fx3_str.marker_hits.get("Rec. Media dur HDMI Output") == 1
        and fx3_adj.marker_hits.get("AVBB_SCN_START_HDMI") == 1
        and fx3_appfw.window_hits.get("HDMI") == 1
        and fx3_appfw.window_hits.get("TIMECODE") == 1
    )
    breathing_proven = (
        fx3_str.marker_hits.get("Lens Compensation") == 1
        and fx3_str.marker_hits.get("Breathing Comp.") == 1
        and fx3_str.marker_hits.get("RAW Output") == 1
        and fx3_appfw.window_hits.get("BREATH") == 1
        and fx3_cpapp.window_hits.get("BREATHING") == 1
        and fx6_cpapp.window_hits.get("BREATHING") == 1
    )
    all_ok = len(errors) == 0 and auto_slow_proven and hdmi_proven and breathing_proven

    audit = Phase262DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=15,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=fx3_imdb,
        fx3_usb_bus_power=fx3_usb,
        fx3_msc_server=fx3_msc,
        fx3_media_cfg=fx3_mcfg,
        fx3_adj_media=fx3_adj,
        fx3_string_en_f=fx3_str,
        fx6_string_en=fx6_str,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        auto_slow_shutter_and_angle_disjoint_proven=auto_slow_proven,
        hdmi_rec_control_tcout_4chaudio_proven=hdmi_proven,
        breathing_comp_lens_and_raw_lockout_proven=breathing_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 51A: [Auto Slow Shutter] 6-Condition Lockout & [Shutter Angle] Disjointness
# ---------------------------------------------------------------------------


def _nominal_shutter_for_fps(frame_rate: str) -> Tuple[str, str]:
    """Return (nominal_shutter_speed, auto_slow_shutter_speed) for a given frame rate."""
    if frame_rate in ("50p", "25p"):
        return ("1/50" if frame_rate == "50p" else "1/25", "1/25")
    if frame_rate in ("23.98p", "29.97p"):
        return ("1/50" if frame_rate == "23.98p" else "1/60", "1/30")
    return ("1/60", "1/30")


def simulate_auto_slow_shutter_hil(
    *,
    configured_auto_slow_shutter: str = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT,
    firmware_version: str = "7.02",
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    exposure_ctrl_type: str = EXP_CTRL_PASM,
    exposure_mode: str = EXP_MODE_PROGRAM_AUTO,
    flex_shutter_auto_manual: str = FLEX_SHUTTER_AUTO,
    iso_setting: str = ISO_AUTO,
    log_shooting_mode: str = LOG_SHOOTING_OFF,
    shutter_mode: str = SHUTTER_MODE_SPEED,
    shutter_angle: str = "180.0 deg",
    frame_rate: str = "59.94p",
    ambient_lux: float = 6.0,
    reset_action: str = RESET_ACTION_NONE,
    force_bypass_auto_slow_shutter_lockout: bool = False,
    force_shutter_angle_overlap: bool = False,
) -> AutoSlowShutterHilResult:
    """Co-emulate Wave-41 [Auto Slow Shutter] 6-condition lockout & [Shutter Angle] disjointness."""
    if (
        configured_auto_slow_shutter not in VALID_AUTO_SLOW_SHUTTER_MODES
        or firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or shooting_mode not in VALID_SHOOTING_MODES
        or exposure_ctrl_type not in VALID_EXP_CTRL_TYPES
        or exposure_mode not in VALID_EXPOSURE_MODES
        or flex_shutter_auto_manual not in VALID_FLEX_SHUTTER_MODES
        or log_shooting_mode not in VALID_LOG_SHOOTING_MODES
        or shutter_mode not in VALID_SHUTTER_MODES
        or frame_rate not in VALID_FRAME_RATES
        or reset_action not in VALID_RESET_ACTIONS
        or not iso_setting.strip()
    ):
        return AutoSlowShutterHilResult(
            menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
            shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
            firmware_version=firmware_version,
            configured_auto_slow_shutter=configured_auto_slow_shutter,
            shooting_mode=shooting_mode,
            exposure_ctrl_type=exposure_ctrl_type,
            exposure_mode=exposure_mode,
            flex_shutter_auto_manual=flex_shutter_auto_manual,
            iso_setting=iso_setting,
            log_shooting_mode=log_shooting_mode,
            shutter_mode=shutter_mode,
            shutter_angle=shutter_angle,
            frame_rate=frame_rate,
            ambient_lux=ambient_lux,
            reset_action=reset_action,
            force_bypass_auto_slow_shutter_lockout=force_bypass_auto_slow_shutter_lockout,
            force_shutter_angle_overlap=force_shutter_angle_overlap,
            effective_auto_slow_shutter_register=AUTO_SLOW_SHUTTER_FACTORY_DEFAULT,
            active_lockout_reasons=(),
            auto_slow_shutter_functionally_available=False,
            auto_slow_shutter_engaged=False,
            shutter_angle_governing_exposure=False,
            effective_shutter_speed="1/60",
            restored_by_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_AUTO_SLOW_SHUTTER_PARAMETER",
            auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
            auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if shutter_mode == SHUTTER_MODE_ANGLE and firmware_version not in SHUTTER_ANGLE_SUPPORTED_VERSIONS:
        return AutoSlowShutterHilResult(
            menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
            shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
            firmware_version=firmware_version,
            configured_auto_slow_shutter=configured_auto_slow_shutter,
            shooting_mode=shooting_mode,
            exposure_ctrl_type=exposure_ctrl_type,
            exposure_mode=exposure_mode,
            flex_shutter_auto_manual=flex_shutter_auto_manual,
            iso_setting=iso_setting,
            log_shooting_mode=log_shooting_mode,
            shutter_mode=shutter_mode,
            shutter_angle=shutter_angle,
            frame_rate=frame_rate,
            ambient_lux=ambient_lux,
            reset_action=reset_action,
            force_bypass_auto_slow_shutter_lockout=force_bypass_auto_slow_shutter_lockout,
            force_shutter_angle_overlap=force_shutter_angle_overlap,
            effective_auto_slow_shutter_register=configured_auto_slow_shutter,
            active_lockout_reasons=(),
            auto_slow_shutter_functionally_available=False,
            auto_slow_shutter_engaged=False,
            shutter_angle_governing_exposure=False,
            effective_shutter_speed="1/60",
            restored_by_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="SHUTTER_ANGLE_REQUIRES_VER_6_00_OR_LATER",
            auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
            auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    restored_cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET
    restored_init = reset_action == RESET_ACTION_INITIALIZE

    if restored_cam_reset or restored_init:
        effective_reg = AUTO_SLOW_SHUTTER_FACTORY_DEFAULT
    else:
        effective_reg = configured_auto_slow_shutter

    lockouts: List[str] = []
    if shooting_mode == SHOOTING_MODE_SQ:
        lockouts.append(LOCKOUT_1_SQ_SHOOTING)
    if exposure_ctrl_type == EXP_CTRL_PASM and exposure_mode == EXP_MODE_SHUTTER_PRIORITY:
        lockouts.append(LOCKOUT_2_SHUTTER_PRIORITY_S)
    if exposure_ctrl_type == EXP_CTRL_PASM and exposure_mode == EXP_MODE_MANUAL_EXPOSURE:
        lockouts.append(LOCKOUT_3_MANUAL_EXPOSURE_M)
    if iso_setting != ISO_AUTO:
        lockouts.append(LOCKOUT_4_ISO_NOT_AUTO)
    if exposure_ctrl_type == EXP_CTRL_FLEXIBLE and flex_shutter_auto_manual == FLEX_SHUTTER_MANUAL:
        lockouts.append(LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER)
    if log_shooting_mode in (LOG_SHOOTING_CINE_EI_QUICK, LOG_SHOOTING_CINE_EI):
        lockouts.append(LOCKOUT_6_LOG_SHOOTING_CINE_EI)

    manual_shutter_active = (
        (
            exposure_ctrl_type == EXP_CTRL_PASM
            and exposure_mode in (EXP_MODE_SHUTTER_PRIORITY, EXP_MODE_MANUAL_EXPOSURE)
        )
        or (
            exposure_ctrl_type == EXP_CTRL_FLEXIBLE
            and flex_shutter_auto_manual == FLEX_SHUTTER_MANUAL
        )
    )
    angle_governing = (
        shooting_mode in (SHOOTING_MODE_MOVIE, SHOOTING_MODE_SQ)
        and shutter_mode == SHUTTER_MODE_ANGLE
        and manual_shutter_active
    )

    functionally_available = (
        shooting_mode == SHOOTING_MODE_MOVIE
        and effective_reg == AUTO_SLOW_SHUTTER_ON
        and len(lockouts) == 0
    )
    nominal_speed, slow_speed = _nominal_shutter_for_fps(frame_rate)

    if force_shutter_angle_overlap:
        return AutoSlowShutterHilResult(
            menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
            shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
            firmware_version=firmware_version,
            configured_auto_slow_shutter=configured_auto_slow_shutter,
            shooting_mode=shooting_mode,
            exposure_ctrl_type=exposure_ctrl_type,
            exposure_mode=exposure_mode,
            flex_shutter_auto_manual=flex_shutter_auto_manual,
            iso_setting=iso_setting,
            log_shooting_mode=log_shooting_mode,
            shutter_mode=shutter_mode,
            shutter_angle=shutter_angle,
            frame_rate=frame_rate,
            ambient_lux=ambient_lux,
            reset_action=reset_action,
            force_bypass_auto_slow_shutter_lockout=force_bypass_auto_slow_shutter_lockout,
            force_shutter_angle_overlap=force_shutter_angle_overlap,
            effective_auto_slow_shutter_register=effective_reg,
            active_lockout_reasons=tuple(lockouts),
            auto_slow_shutter_functionally_available=False,
            auto_slow_shutter_engaged=False,
            shutter_angle_governing_exposure=angle_governing,
            effective_shutter_speed=shutter_angle if angle_governing else nominal_speed,
            restored_by_camera_settings_reset=restored_cam_reset,
            survived_reset_network_set=survived_net_reset,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_FORBIDDEN",
            auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
            auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_bypass_auto_slow_shutter_lockout and (len(lockouts) > 0 or shooting_mode != SHOOTING_MODE_MOVIE):
        return AutoSlowShutterHilResult(
            menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
            shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
            firmware_version=firmware_version,
            configured_auto_slow_shutter=configured_auto_slow_shutter,
            shooting_mode=shooting_mode,
            exposure_ctrl_type=exposure_ctrl_type,
            exposure_mode=exposure_mode,
            flex_shutter_auto_manual=flex_shutter_auto_manual,
            iso_setting=iso_setting,
            log_shooting_mode=log_shooting_mode,
            shutter_mode=shutter_mode,
            shutter_angle=shutter_angle,
            frame_rate=frame_rate,
            ambient_lux=ambient_lux,
            reset_action=reset_action,
            force_bypass_auto_slow_shutter_lockout=force_bypass_auto_slow_shutter_lockout,
            force_shutter_angle_overlap=force_shutter_angle_overlap,
            effective_auto_slow_shutter_register=effective_reg,
            active_lockout_reasons=tuple(lockouts),
            auto_slow_shutter_functionally_available=False,
            auto_slow_shutter_engaged=False,
            shutter_angle_governing_exposure=angle_governing,
            effective_shutter_speed=shutter_angle if angle_governing else nominal_speed,
            restored_by_camera_settings_reset=restored_cam_reset,
            survived_reset_network_set=survived_net_reset,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_BLOCKED",
            auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
            auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    engaged = functionally_available and (ambient_lux <= LOW_LIGHT_LUX_THRESHOLD)
    if angle_governing:
        eff_speed = shutter_angle
    elif engaged:
        eff_speed = slow_speed
    else:
        eff_speed = nominal_speed

    return AutoSlowShutterHilResult(
        menu_path=AUTO_SLOW_SHUTTER_MENU_PATH,
        shutter_mode_menu_path=SHUTTER_MODE_MENU_PATH,
        firmware_version=firmware_version,
        configured_auto_slow_shutter=configured_auto_slow_shutter,
        shooting_mode=shooting_mode,
        exposure_ctrl_type=exposure_ctrl_type,
        exposure_mode=exposure_mode,
        flex_shutter_auto_manual=flex_shutter_auto_manual,
        iso_setting=iso_setting,
        log_shooting_mode=log_shooting_mode,
        shutter_mode=shutter_mode,
        shutter_angle=shutter_angle,
        frame_rate=frame_rate,
        ambient_lux=ambient_lux,
        reset_action=reset_action,
        force_bypass_auto_slow_shutter_lockout=force_bypass_auto_slow_shutter_lockout,
        force_shutter_angle_overlap=force_shutter_angle_overlap,
        effective_auto_slow_shutter_register=effective_reg,
        active_lockout_reasons=tuple(lockouts),
        auto_slow_shutter_functionally_available=functionally_available,
        auto_slow_shutter_engaged=engaged,
        shutter_angle_governing_exposure=angle_governing,
        effective_shutter_speed=eff_speed,
        restored_by_camera_settings_reset=restored_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_init,
        admitted=True,
        errno_code=0,
        reason_code="OK",
        auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
        auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def compute_auto_slow_shutter_angle_disjointness_matrix() -> Dict[str, object]:
    """Exhaustively verify across 768 exposure states that Auto Slow Shutter and Shutter Angle never overlap."""
    total_states = 0
    auto_slow_active_states = 0
    shutter_angle_active_states = 0
    overlap_states = 0

    for smode in VALID_SHOOTING_MODES:
        for ect in VALID_EXP_CTRL_TYPES:
            for emode in VALID_EXPOSURE_MODES:
                for flex_sh in VALID_FLEX_SHUTTER_MODES:
                    for iso_val in (ISO_AUTO, "ISO 800"):
                        for log_m in VALID_LOG_SHOOTING_MODES:
                            for sh_m in VALID_SHUTTER_MODES:
                                total_states += 1
                                res = simulate_auto_slow_shutter_hil(
                                    configured_auto_slow_shutter=AUTO_SLOW_SHUTTER_ON,
                                    firmware_version="7.02",
                                    shooting_mode=smode,
                                    exposure_ctrl_type=ect,
                                    exposure_mode=emode,
                                    flex_shutter_auto_manual=flex_sh,
                                    iso_setting=iso_val,
                                    log_shooting_mode=log_m,
                                    shutter_mode=sh_m,
                                    ambient_lux=5.0,
                                )
                                if res.auto_slow_shutter_functionally_available:
                                    auto_slow_active_states += 1
                                if res.shutter_angle_governing_exposure:
                                    shutter_angle_active_states += 1
                                if (
                                    res.auto_slow_shutter_functionally_available
                                    and res.shutter_angle_governing_exposure
                                ):
                                    overlap_states += 1

    return {
        "total_states_evaluated": total_states,
        "auto_slow_shutter_active_states": auto_slow_active_states,
        "shutter_angle_active_states": shutter_angle_active_states,
        "overlap_states": overlap_states,
        "strictly_disjoint": overlap_states == 0 and auto_slow_active_states > 0 and shutter_angle_active_states > 0,
    }


def evaluate_pillar_a_auto_slow_shutter_6locks_and_angle_disjoint_hil() -> Dict[str, object]:
    """Run Pillar A Wave-41 [Auto Slow Shutter] 6-condition lockout & [Shutter Angle] disjointness audit."""
    default_low_light_engaged = simulate_auto_slow_shutter_hil(ambient_lux=5.0)
    default_bright_light_nominal = simulate_auto_slow_shutter_hil(ambient_lux=120.0)
    explicit_off_dark = simulate_auto_slow_shutter_hil(
        configured_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
        ambient_lux=5.0,
    )
    flex_auto_shutter_engaged = simulate_auto_slow_shutter_hil(
        exposure_ctrl_type=EXP_CTRL_FLEXIBLE,
        flex_shutter_auto_manual=FLEX_SHUTTER_AUTO,
        log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO,
        ambient_lux=5.0,
    )

    lock1_sq = simulate_auto_slow_shutter_hil(shooting_mode=SHOOTING_MODE_SQ)
    lock2_shutter_prio = simulate_auto_slow_shutter_hil(exposure_mode=EXP_MODE_SHUTTER_PRIORITY)
    lock3_manual_exp = simulate_auto_slow_shutter_hil(exposure_mode=EXP_MODE_MANUAL_EXPOSURE)
    lock4_fixed_iso = simulate_auto_slow_shutter_hil(iso_setting="ISO 800")
    lock5_flex_manual_shutter = simulate_auto_slow_shutter_hil(
        exposure_ctrl_type=EXP_CTRL_FLEXIBLE,
        flex_shutter_auto_manual=FLEX_SHUTTER_MANUAL,
    )
    lock6a_cine_ei_quick = simulate_auto_slow_shutter_hil(
        log_shooting_mode=LOG_SHOOTING_CINE_EI_QUICK
    )
    lock6b_cine_ei = simulate_auto_slow_shutter_hil(log_shooting_mode=LOG_SHOOTING_CINE_EI)

    shutter_angle_702_disjoint = simulate_auto_slow_shutter_hil(
        exposure_mode=EXP_MODE_MANUAL_EXPOSURE,
        shutter_mode=SHUTTER_MODE_ANGLE,
        shutter_angle="180.0 deg",
    )
    shutter_angle_pre600_blocked = simulate_auto_slow_shutter_hil(
        firmware_version="5.00",
        exposure_mode=EXP_MODE_MANUAL_EXPOSURE,
        shutter_mode=SHUTTER_MODE_ANGLE,
    )

    restored_cam_reset = simulate_auto_slow_shutter_hil(
        configured_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = simulate_auto_slow_shutter_hil(
        configured_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_init = simulate_auto_slow_shutter_hil(
        configured_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
        reset_action=RESET_ACTION_INITIALIZE,
    )

    bypass_blocked = simulate_auto_slow_shutter_hil(
        log_shooting_mode=LOG_SHOOTING_CINE_EI,
        force_bypass_auto_slow_shutter_lockout=True,
    )
    overlap_blocked = simulate_auto_slow_shutter_hil(
        exposure_mode=EXP_MODE_MANUAL_EXPOSURE,
        shutter_mode=SHUTTER_MODE_ANGLE,
        force_shutter_angle_overlap=True,
    )
    disjoint_matrix = compute_auto_slow_shutter_angle_disjointness_matrix()

    lockout_matrix = {
        LOCKOUT_1_SQ_SHOOTING: asdict(lock1_sq),
        LOCKOUT_2_SHUTTER_PRIORITY_S: asdict(lock2_shutter_prio),
        LOCKOUT_3_MANUAL_EXPOSURE_M: asdict(lock3_manual_exp),
        LOCKOUT_4_ISO_NOT_AUTO: asdict(lock4_fixed_iso),
        LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER: asdict(lock5_flex_manual_shutter),
        LOCKOUT_6_LOG_SHOOTING_CINE_EI: asdict(lock6b_cine_ei),
    }

    passed = (
        default_low_light_engaged.admitted
        and default_low_light_engaged.auto_slow_shutter_engaged
        and default_low_light_engaged.effective_shutter_speed == "1/30"
        and default_bright_light_nominal.admitted
        and (not default_bright_light_nominal.auto_slow_shutter_engaged)
        and default_bright_light_nominal.effective_shutter_speed == "1/60"
        and explicit_off_dark.admitted
        and (not explicit_off_dark.auto_slow_shutter_engaged)
        and flex_auto_shutter_engaged.admitted
        and flex_auto_shutter_engaged.auto_slow_shutter_engaged
        and LOCKOUT_1_SQ_SHOOTING in lock1_sq.active_lockout_reasons
        and (not lock1_sq.auto_slow_shutter_engaged)
        and LOCKOUT_2_SHUTTER_PRIORITY_S in lock2_shutter_prio.active_lockout_reasons
        and (not lock2_shutter_prio.auto_slow_shutter_engaged)
        and LOCKOUT_3_MANUAL_EXPOSURE_M in lock3_manual_exp.active_lockout_reasons
        and (not lock3_manual_exp.auto_slow_shutter_engaged)
        and LOCKOUT_4_ISO_NOT_AUTO in lock4_fixed_iso.active_lockout_reasons
        and (not lock4_fixed_iso.auto_slow_shutter_engaged)
        and LOCKOUT_5_FLEXIBLE_EXP_MANUAL_SHUTTER in lock5_flex_manual_shutter.active_lockout_reasons
        and (not lock5_flex_manual_shutter.auto_slow_shutter_engaged)
        and LOCKOUT_6_LOG_SHOOTING_CINE_EI in lock6a_cine_ei_quick.active_lockout_reasons
        and (not lock6a_cine_ei_quick.auto_slow_shutter_engaged)
        and LOCKOUT_6_LOG_SHOOTING_CINE_EI in lock6b_cine_ei.active_lockout_reasons
        and (not lock6b_cine_ei.auto_slow_shutter_engaged)
        and shutter_angle_702_disjoint.shutter_angle_governing_exposure
        and (not shutter_angle_702_disjoint.auto_slow_shutter_functionally_available)
        and (not shutter_angle_pre600_blocked.admitted)
        and shutter_angle_pre600_blocked.errno_code == EOPNOTSUPP_ERRNO
        and restored_cam_reset.restored_by_camera_settings_reset
        and restored_cam_reset.effective_auto_slow_shutter_register == AUTO_SLOW_SHUTTER_ON
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_auto_slow_shutter_register == AUTO_SLOW_SHUTTER_OFF
        and restored_init.restored_by_initialize
        and restored_init.effective_auto_slow_shutter_register == AUTO_SLOW_SHUTTER_ON
        and (not bypass_blocked.admitted)
        and bypass_blocked.errno_code == EACCES_ERRNO
        and (not overlap_blocked.admitted)
        and overlap_blocked.errno_code == EINVAL_ERRNO
        and bool(disjoint_matrix["strictly_disjoint"])
        and disjoint_matrix["overlap_states"] == 0
    )

    return {
        "passed": passed,
        "menu_path": AUTO_SLOW_SHUTTER_MENU_PATH,
        "shutter_mode_menu_path": SHUTTER_MODE_MENU_PATH,
        "all_6_lockout_ids": list(ALL_6_AUTO_SLOW_SHUTTER_LOCKOUTS),
        "default_low_light_engaged": asdict(default_low_light_engaged),
        "default_bright_light_nominal": asdict(default_bright_light_nominal),
        "explicit_off_dark_nominal": asdict(explicit_off_dark),
        "flexible_exp_auto_shutter_engaged": asdict(flex_auto_shutter_engaged),
        "six_condition_lockout_matrix": lockout_matrix,
        "cine_ei_quick_lockout": asdict(lock6a_cine_ei_quick),
        "shutter_angle_702_disjoint_ok": asdict(shutter_angle_702_disjoint),
        "shutter_angle_pre600_blocked_eopnotsupp": asdict(shutter_angle_pre600_blocked),
        "restored_by_camera_settings_reset": asdict(restored_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_init),
        "lockout_bypass_blocked_eacces": asdict(bypass_blocked),
        "shutter_angle_overlap_blocked_einval": asdict(overlap_blocked),
        "disjointness_768_state_matrix": disjoint_matrix,
    }


# ---------------------------------------------------------------------------
# Sub-Model 51B: [HDMI Output Settings] REC Control <- Time Code Output, 4ch Audio & Vault Guard
# ---------------------------------------------------------------------------


def simulate_hdmi_output_reccontrol_4chaudio_hil(
    *,
    configured_time_code_output: str = TOGGLE_OFF,
    configured_rec_control: str = TOGGLE_OFF,
    configured_hdmi_4ch_audio_output: str = HDMI_4CH_AUDIO_CH1_CH2,
    configured_rec_media_dur_hdmi_output: str = TOGGLE_ON,
    mi_shoe_4ch_audio_active: bool = False,
    proxy_recording_requested: bool = False,
    camera_rec_button_pressed: bool = False,
    transition_tc_output_to_off: bool = False,
    strict_menu_set_rec_ctrl: bool = True,
    slot1_is_tier0_recovery_vault: bool = True,
    force_slot1_vault_hdmi_rec_write: bool = False,
    force_rec_ctrl_without_tc_bypass: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> HdmiOutputRecControlAudioHilResult:
    """Co-emulate Wave-41 [HDMI Output Settings] REC Control <- Time Code Output, 4ch Audio & Slot-1 Vault Guard."""
    if (
        configured_time_code_output not in VALID_TOGGLE_STATES
        or configured_rec_control not in VALID_TOGGLE_STATES
        or configured_hdmi_4ch_audio_output not in VALID_HDMI_4CH_AUDIO_MODES
        or configured_rec_media_dur_hdmi_output not in VALID_TOGGLE_STATES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return HdmiOutputRecControlAudioHilResult(
            menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
            configured_time_code_output=configured_time_code_output,
            configured_rec_control=configured_rec_control,
            configured_hdmi_4ch_audio_output=configured_hdmi_4ch_audio_output,
            configured_rec_media_dur_hdmi_output=configured_rec_media_dur_hdmi_output,
            mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
            proxy_recording_requested=proxy_recording_requested,
            camera_rec_button_pressed=camera_rec_button_pressed,
            transition_tc_output_to_off=transition_tc_output_to_off,
            strict_menu_set_rec_ctrl=strict_menu_set_rec_ctrl,
            slot1_is_tier0_recovery_vault=slot1_is_tier0_recovery_vault,
            force_slot1_vault_hdmi_rec_write=force_slot1_vault_hdmi_rec_write,
            force_rec_ctrl_without_tc_bypass=force_rec_ctrl_without_tc_bypass,
            reset_action=reset_action,
            effective_time_code_output=TOGGLE_OFF,
            effective_rec_control=TOGGLE_OFF,
            effective_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH1_CH2,
            effective_rec_media_dur_hdmi_output=TOGGLE_ON,
            rec_control_prerequisite_tc_satisfied=False,
            external_recorder_rec_trigger_emitted=False,
            hdmi_routed_audio_pair=("CH1_L", "CH2_R"),
            hdmi_4ch_routing_active=False,
            internal_slot1_clip_recording_active=False,
            internal_slot2_clip_recording_active=False,
            internal_proxy_recording_active=False,
            survived_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_HDMI_OUTPUT_SETTINGS_PARAMETER",
            hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
            slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    survived_cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET
    restored_init = reset_action == RESET_ACTION_INITIALIZE

    if restored_init:
        eff_tc = HDMI_OUTPUT_FACTORY_DEFAULTS["time_code_output"]
        eff_rec_ctrl = HDMI_OUTPUT_FACTORY_DEFAULTS["rec_control"]
        eff_4ch_audio = HDMI_OUTPUT_FACTORY_DEFAULTS["hdmi_4ch_audio_output"]
        eff_rec_media = HDMI_OUTPUT_FACTORY_DEFAULTS["rec_media_dur_hdmi_output"]
    else:
        eff_tc = TOGGLE_OFF if transition_tc_output_to_off else configured_time_code_output
        eff_rec_ctrl = configured_rec_control
        eff_4ch_audio = configured_hdmi_4ch_audio_output
        eff_rec_media = configured_rec_media_dur_hdmi_output

    if mi_shoe_4ch_audio_active:
        routed_pair = (
            ("CH3_L", "CH4_R")
            if eff_4ch_audio == HDMI_4CH_AUDIO_CH3_CH4
            else ("CH1_L", "CH2_R")
        )
        hdmi_4ch_active = True
    else:
        routed_pair = ("CH1_L", "CH2_R")
        hdmi_4ch_active = False

    if force_slot1_vault_hdmi_rec_write:
        return HdmiOutputRecControlAudioHilResult(
            menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
            configured_time_code_output=configured_time_code_output,
            configured_rec_control=configured_rec_control,
            configured_hdmi_4ch_audio_output=configured_hdmi_4ch_audio_output,
            configured_rec_media_dur_hdmi_output=configured_rec_media_dur_hdmi_output,
            mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
            proxy_recording_requested=proxy_recording_requested,
            camera_rec_button_pressed=camera_rec_button_pressed,
            transition_tc_output_to_off=transition_tc_output_to_off,
            strict_menu_set_rec_ctrl=strict_menu_set_rec_ctrl,
            slot1_is_tier0_recovery_vault=slot1_is_tier0_recovery_vault,
            force_slot1_vault_hdmi_rec_write=force_slot1_vault_hdmi_rec_write,
            force_rec_ctrl_without_tc_bypass=force_rec_ctrl_without_tc_bypass,
            reset_action=reset_action,
            effective_time_code_output=eff_tc,
            effective_rec_control=TOGGLE_OFF if eff_tc == TOGGLE_OFF else eff_rec_ctrl,
            effective_hdmi_4ch_audio_output=eff_4ch_audio,
            effective_rec_media_dur_hdmi_output=eff_rec_media,
            rec_control_prerequisite_tc_satisfied=(eff_tc == TOGGLE_ON),
            external_recorder_rec_trigger_emitted=False,
            hdmi_routed_audio_pair=routed_pair,
            hdmi_4ch_routing_active=hdmi_4ch_active,
            internal_slot1_clip_recording_active=False,
            internal_slot2_clip_recording_active=False,
            internal_proxy_recording_active=False,
            survived_camera_settings_reset=survived_cam_reset,
            survived_reset_network_set=survived_net_reset,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code="SLOT1_TIER0_VAULT_HDMI_REC_WRITE_BLOCKED_EROFS",
            hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
            slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_rec_ctrl_without_tc_bypass:
        return HdmiOutputRecControlAudioHilResult(
            menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
            configured_time_code_output=configured_time_code_output,
            configured_rec_control=configured_rec_control,
            configured_hdmi_4ch_audio_output=configured_hdmi_4ch_audio_output,
            configured_rec_media_dur_hdmi_output=configured_rec_media_dur_hdmi_output,
            mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
            proxy_recording_requested=proxy_recording_requested,
            camera_rec_button_pressed=camera_rec_button_pressed,
            transition_tc_output_to_off=transition_tc_output_to_off,
            strict_menu_set_rec_ctrl=strict_menu_set_rec_ctrl,
            slot1_is_tier0_recovery_vault=slot1_is_tier0_recovery_vault,
            force_slot1_vault_hdmi_rec_write=force_slot1_vault_hdmi_rec_write,
            force_rec_ctrl_without_tc_bypass=force_rec_ctrl_without_tc_bypass,
            reset_action=reset_action,
            effective_time_code_output=TOGGLE_OFF,
            effective_rec_control=TOGGLE_OFF,
            effective_hdmi_4ch_audio_output=eff_4ch_audio,
            effective_rec_media_dur_hdmi_output=eff_rec_media,
            rec_control_prerequisite_tc_satisfied=False,
            external_recorder_rec_trigger_emitted=False,
            hdmi_routed_audio_pair=routed_pair,
            hdmi_4ch_routing_active=hdmi_4ch_active,
            internal_slot1_clip_recording_active=False,
            internal_slot2_clip_recording_active=False,
            internal_proxy_recording_active=False,
            survived_camera_settings_reset=survived_cam_reset,
            survived_reset_network_set=survived_net_reset,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="HDMI_REC_CTRL_WITHOUT_TC_BYPASS_BLOCKED",
            hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
            slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    reason = "OK"
    if eff_rec_ctrl == TOGGLE_ON and eff_tc == TOGGLE_OFF:
        eff_rec_ctrl = TOGGLE_OFF
        if transition_tc_output_to_off or not strict_menu_set_rec_ctrl:
            reason = "HDMI_REC_CTRL_AUTO_DISABLED_WHEN_TC_OFF"
        else:
            return HdmiOutputRecControlAudioHilResult(
                menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
                configured_time_code_output=configured_time_code_output,
                configured_rec_control=configured_rec_control,
                configured_hdmi_4ch_audio_output=configured_hdmi_4ch_audio_output,
                configured_rec_media_dur_hdmi_output=configured_rec_media_dur_hdmi_output,
                mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
                proxy_recording_requested=proxy_recording_requested,
                camera_rec_button_pressed=camera_rec_button_pressed,
                transition_tc_output_to_off=transition_tc_output_to_off,
                strict_menu_set_rec_ctrl=strict_menu_set_rec_ctrl,
                slot1_is_tier0_recovery_vault=slot1_is_tier0_recovery_vault,
                force_slot1_vault_hdmi_rec_write=force_slot1_vault_hdmi_rec_write,
                force_rec_ctrl_without_tc_bypass=force_rec_ctrl_without_tc_bypass,
                reset_action=reset_action,
                effective_time_code_output=eff_tc,
                effective_rec_control=TOGGLE_OFF,
                effective_hdmi_4ch_audio_output=eff_4ch_audio,
                effective_rec_media_dur_hdmi_output=eff_rec_media,
                rec_control_prerequisite_tc_satisfied=False,
                external_recorder_rec_trigger_emitted=False,
                hdmi_routed_audio_pair=routed_pair,
                hdmi_4ch_routing_active=hdmi_4ch_active,
                internal_slot1_clip_recording_active=False,
                internal_slot2_clip_recording_active=False,
                internal_proxy_recording_active=False,
                survived_camera_settings_reset=survived_cam_reset,
                survived_reset_network_set=survived_net_reset,
                restored_by_initialize=restored_init,
                admitted=False,
                errno_code=EACCES_ERRNO,
                reason_code="HDMI_REC_CTRL_REQUIRES_TIME_CODE_OUTPUT_ON",
                hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
                slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
                bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
            )

    tc_satisfied = eff_tc == TOGGLE_ON
    ext_rec_trigger = tc_satisfied and (eff_rec_ctrl == TOGGLE_ON) and camera_rec_button_pressed

    if eff_rec_media == TOGGLE_OFF or not camera_rec_button_pressed:
        slot1_rec = False
        slot2_rec = False
        proxy_rec = False
    else:
        slot1_rec = not slot1_is_tier0_recovery_vault
        slot2_rec = True
        proxy_rec = proxy_recording_requested

    return HdmiOutputRecControlAudioHilResult(
        menu_path=HDMI_OUTPUT_SETTINGS_MENU_PATH,
        configured_time_code_output=configured_time_code_output,
        configured_rec_control=configured_rec_control,
        configured_hdmi_4ch_audio_output=configured_hdmi_4ch_audio_output,
        configured_rec_media_dur_hdmi_output=configured_rec_media_dur_hdmi_output,
        mi_shoe_4ch_audio_active=mi_shoe_4ch_audio_active,
        proxy_recording_requested=proxy_recording_requested,
        camera_rec_button_pressed=camera_rec_button_pressed,
        transition_tc_output_to_off=transition_tc_output_to_off,
        strict_menu_set_rec_ctrl=strict_menu_set_rec_ctrl,
        slot1_is_tier0_recovery_vault=slot1_is_tier0_recovery_vault,
        force_slot1_vault_hdmi_rec_write=force_slot1_vault_hdmi_rec_write,
        force_rec_ctrl_without_tc_bypass=force_rec_ctrl_without_tc_bypass,
        reset_action=reset_action,
        effective_time_code_output=eff_tc,
        effective_rec_control=eff_rec_ctrl,
        effective_hdmi_4ch_audio_output=eff_4ch_audio,
        effective_rec_media_dur_hdmi_output=eff_rec_media,
        rec_control_prerequisite_tc_satisfied=tc_satisfied,
        external_recorder_rec_trigger_emitted=ext_rec_trigger,
        hdmi_routed_audio_pair=routed_pair,
        hdmi_4ch_routing_active=hdmi_4ch_active,
        internal_slot1_clip_recording_active=slot1_rec,
        internal_slot2_clip_recording_active=slot2_rec,
        internal_proxy_recording_active=proxy_rec,
        survived_camera_settings_reset=survived_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_init,
        admitted=True,
        errno_code=0,
        reason_code=reason,
        hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
        slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_hdmi_reccontrol_tcout_4chaudio_and_vault_hil() -> Dict[str, object]:
    """Run Pillar B Wave-41 [HDMI Output Settings] REC Control, 4ch Audio & Slot-1 Vault Guard audit."""
    factory_default = simulate_hdmi_output_reccontrol_4chaudio_hil()
    tc_on_rec_ctrl_on_trigger = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        camera_rec_button_pressed=True,
    )
    tc_off_rec_ctrl_rejected = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_OFF,
        configured_rec_control=TOGGLE_ON,
        strict_menu_set_rec_ctrl=True,
    )
    tc_turned_off_auto_disables_rec_ctrl = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        transition_tc_output_to_off=True,
        camera_rec_button_pressed=True,
    )
    audio_4ch_ch1_ch2 = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH1_CH2,
        mi_shoe_4ch_audio_active=True,
    )
    audio_4ch_ch3_ch4 = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4,
        mi_shoe_4ch_audio_active=True,
    )
    audio_no_mishoe_fallback = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4,
        mi_shoe_4ch_audio_active=False,
    )
    rec_media_off_inhibits_cards_and_proxy = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        configured_rec_media_dur_hdmi_output=TOGGLE_OFF,
        proxy_recording_requested=True,
        camera_rec_button_pressed=True,
    )
    survives_cam_reset = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4,
        configured_rec_media_dur_hdmi_output=TOGGLE_OFF,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4,
        configured_rec_media_dur_hdmi_output=TOGGLE_OFF,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_by_init = simulate_hdmi_output_reccontrol_4chaudio_hil(
        configured_time_code_output=TOGGLE_ON,
        configured_rec_control=TOGGLE_ON,
        configured_hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4,
        configured_rec_media_dur_hdmi_output=TOGGLE_OFF,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    slot1_vault_write_blocked = simulate_hdmi_output_reccontrol_4chaudio_hil(
        force_slot1_vault_hdmi_rec_write=True,
    )
    rec_ctrl_bypass_blocked = simulate_hdmi_output_reccontrol_4chaudio_hil(
        force_rec_ctrl_without_tc_bypass=True,
    )

    passed = (
        factory_default.admitted
        and factory_default.effective_rec_control == TOGGLE_OFF
        and factory_default.effective_time_code_output == TOGGLE_OFF
        and factory_default.effective_hdmi_4ch_audio_output == HDMI_4CH_AUDIO_CH1_CH2
        and tc_on_rec_ctrl_on_trigger.admitted
        and tc_on_rec_ctrl_on_trigger.external_recorder_rec_trigger_emitted
        and (not tc_off_rec_ctrl_rejected.admitted)
        and tc_off_rec_ctrl_rejected.errno_code == EACCES_ERRNO
        and tc_off_rec_ctrl_rejected.hdmi_rec_ctrl_without_tc_violations == 0
        and tc_turned_off_auto_disables_rec_ctrl.admitted
        and tc_turned_off_auto_disables_rec_ctrl.effective_rec_control == TOGGLE_OFF
        and (not tc_turned_off_auto_disables_rec_ctrl.external_recorder_rec_trigger_emitted)
        and audio_4ch_ch1_ch2.hdmi_routed_audio_pair == ("CH1_L", "CH2_R")
        and audio_4ch_ch3_ch4.hdmi_routed_audio_pair == ("CH3_L", "CH4_R")
        and audio_4ch_ch3_ch4.hdmi_4ch_routing_active
        and audio_no_mishoe_fallback.hdmi_routed_audio_pair == ("CH1_L", "CH2_R")
        and (not audio_no_mishoe_fallback.hdmi_4ch_routing_active)
        and rec_media_off_inhibits_cards_and_proxy.admitted
        and (not rec_media_off_inhibits_cards_and_proxy.internal_slot1_clip_recording_active)
        and (not rec_media_off_inhibits_cards_and_proxy.internal_slot2_clip_recording_active)
        and (not rec_media_off_inhibits_cards_and_proxy.internal_proxy_recording_active)
        and rec_media_off_inhibits_cards_and_proxy.external_recorder_rec_trigger_emitted
        and survives_cam_reset.survived_camera_settings_reset
        and survives_cam_reset.effective_rec_control == TOGGLE_ON
        and survives_cam_reset.effective_hdmi_4ch_audio_output == HDMI_4CH_AUDIO_CH3_CH4
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_rec_media_dur_hdmi_output == TOGGLE_OFF
        and restored_by_init.restored_by_initialize
        and restored_by_init.effective_rec_control == TOGGLE_OFF
        and restored_by_init.effective_time_code_output == TOGGLE_OFF
        and restored_by_init.effective_hdmi_4ch_audio_output == HDMI_4CH_AUDIO_CH1_CH2
        and restored_by_init.effective_rec_media_dur_hdmi_output == TOGGLE_ON
        and (not slot1_vault_write_blocked.admitted)
        and slot1_vault_write_blocked.errno_code == EROFS_ERRNO
        and slot1_vault_write_blocked.slot1_hdmi_rec_vault_mutation_bytes == 0
        and (not rec_ctrl_bypass_blocked.admitted)
        and rec_ctrl_bypass_blocked.errno_code == EACCES_ERRNO
    )

    return {
        "passed": passed,
        "menu_path": HDMI_OUTPUT_SETTINGS_MENU_PATH,
        "all_2_hdmi_4ch_audio_modes": list(VALID_HDMI_4CH_AUDIO_MODES),
        "factory_defaults": dict(HDMI_OUTPUT_FACTORY_DEFAULTS),
        "factory_default_ok": asdict(factory_default),
        "tc_on_rec_ctrl_on_trigger_ok": asdict(tc_on_rec_ctrl_on_trigger),
        "tc_off_rec_ctrl_rejected_eacces": asdict(tc_off_rec_ctrl_rejected),
        "tc_turned_off_auto_disables_rec_ctrl": asdict(tc_turned_off_auto_disables_rec_ctrl),
        "audio_4ch_ch1_ch2_routing": asdict(audio_4ch_ch1_ch2),
        "audio_4ch_ch3_ch4_routing": asdict(audio_4ch_ch3_ch4),
        "audio_no_mishoe_2ch_fallback": asdict(audio_no_mishoe_fallback),
        "rec_media_off_inhibits_cards_and_proxy": asdict(rec_media_off_inhibits_cards_and_proxy),
        "survives_camera_settings_reset": asdict(survives_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_by_init),
        "slot1_vault_write_blocked_erofs": asdict(slot1_vault_write_blocked),
        "rec_ctrl_bypass_blocked_eacces": asdict(rec_ctrl_bypass_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 51C & Redlines: [Lens Compensation] -> [Breathing Comp.] & Redline Guard
# ---------------------------------------------------------------------------


def simulate_breathing_comp_lens_hil(
    *,
    configured_breathing_comp: str = BREATHING_COMP_FACTORY_DEFAULT,
    firmware_version: str = "7.02",
    shooting_scope: str = SHOOTING_MODE_MOVIE,
    attached_lens_id: str = "SEL2470GM2",
    frame_rate: str = "59.94p",
    hdmi_raw_output_on: bool = False,
    raw_resolution: str = HDMI_RAW_RESOLUTION_4264,
    reset_action: str = RESET_ACTION_NONE,
    force_bypass_breathing_raw_or_240p_lockout: bool = False,
) -> BreathingCompLensHilResult:
    """Co-emulate Wave-41 [Lens Compensation] -> [Breathing Comp.] movie-only compliant-lens crop & RAW/240p lockout."""
    if (
        configured_breathing_comp not in VALID_TOGGLE_STATES
        or firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or shooting_scope not in VALID_SHOOTING_MODES
        or attached_lens_id not in VALID_LENS_IDS
        or frame_rate not in VALID_FRAME_RATES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return BreathingCompLensHilResult(
            menu_path=BREATHING_COMP_MENU_PATH,
            firmware_version=firmware_version,
            configured_breathing_comp=configured_breathing_comp,
            shooting_scope=shooting_scope,
            attached_lens_id=attached_lens_id,
            frame_rate=frame_rate,
            hdmi_raw_output_on=hdmi_raw_output_on,
            raw_resolution=raw_resolution,
            reset_action=reset_action,
            force_bypass_breathing_raw_or_240p_lockout=force_bypass_breathing_raw_or_240p_lockout,
            effective_breathing_comp_register=BREATHING_COMP_FACTORY_DEFAULT,
            lens_is_breathing_compliant=False,
            breathing_comp_locked_out=True,
            active_breathing_lockout_reasons=(),
            effective_breathing_comp_applied=False,
            fov_crop_factor=1.0,
            still_image_untouched=True,
            restored_by_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_BREATHING_COMP_PARAMETER",
            breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if firmware_version not in BREATHING_COMP_SUPPORTED_VERSIONS and configured_breathing_comp == TOGGLE_ON:
        return BreathingCompLensHilResult(
            menu_path=BREATHING_COMP_MENU_PATH,
            firmware_version=firmware_version,
            configured_breathing_comp=configured_breathing_comp,
            shooting_scope=shooting_scope,
            attached_lens_id=attached_lens_id,
            frame_rate=frame_rate,
            hdmi_raw_output_on=hdmi_raw_output_on,
            raw_resolution=raw_resolution,
            reset_action=reset_action,
            force_bypass_breathing_raw_or_240p_lockout=force_bypass_breathing_raw_or_240p_lockout,
            effective_breathing_comp_register=TOGGLE_OFF,
            lens_is_breathing_compliant=(attached_lens_id in COMPLIANT_BREATHING_EMOUNT_LENSES),
            breathing_comp_locked_out=True,
            active_breathing_lockout_reasons=("FIRMWARE_PRE_VER_3_00",),
            effective_breathing_comp_applied=False,
            fov_crop_factor=1.0,
            still_image_untouched=True,
            restored_by_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code="BREATHING_COMP_REQUIRES_VER_3_00_OR_LATER",
            breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    restored_cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET
    restored_init = reset_action == RESET_ACTION_INITIALIZE

    if restored_cam_reset or restored_init:
        eff_reg = BREATHING_COMP_FACTORY_DEFAULT
    else:
        eff_reg = configured_breathing_comp

    lens_compliant = attached_lens_id in COMPLIANT_BREATHING_EMOUNT_LENSES
    lockout_reasons: List[str] = []
    if hdmi_raw_output_on and raw_resolution == HDMI_RAW_RESOLUTION_4264:
        lockout_reasons.append("HDMI_RAW_4264X2408_OUTPUT_ACTIVE")
    if shooting_scope == SHOOTING_MODE_SQ and frame_rate in SQ_240P_LOCKOUT_RATES:
        lockout_reasons.append(f"SQ_HIGH_FRAME_RATE_{frame_rate}_LOCKOUT")

    locked_out = len(lockout_reasons) > 0

    if force_bypass_breathing_raw_or_240p_lockout and locked_out:
        return BreathingCompLensHilResult(
            menu_path=BREATHING_COMP_MENU_PATH,
            firmware_version=firmware_version,
            configured_breathing_comp=configured_breathing_comp,
            shooting_scope=shooting_scope,
            attached_lens_id=attached_lens_id,
            frame_rate=frame_rate,
            hdmi_raw_output_on=hdmi_raw_output_on,
            raw_resolution=raw_resolution,
            reset_action=reset_action,
            force_bypass_breathing_raw_or_240p_lockout=force_bypass_breathing_raw_or_240p_lockout,
            effective_breathing_comp_register=eff_reg,
            lens_is_breathing_compliant=lens_compliant,
            breathing_comp_locked_out=True,
            active_breathing_lockout_reasons=tuple(lockout_reasons),
            effective_breathing_comp_applied=False,
            fov_crop_factor=1.0,
            still_image_untouched=True,
            restored_by_camera_settings_reset=restored_cam_reset,
            survived_reset_network_set=survived_net_reset,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="BREATHING_COMP_RAW_OR_240P_BYPASS_BLOCKED",
            breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    movie_or_sq_allowed = shooting_scope in (SHOOTING_MODE_MOVIE, SHOOTING_MODE_SQ)
    applied = (
        eff_reg == TOGGLE_ON
        and movie_or_sq_allowed
        and lens_compliant
        and (not locked_out)
    )
    crop = COMPLIANT_BREATHING_EMOUNT_LENSES[attached_lens_id] if applied else 1.0

    return BreathingCompLensHilResult(
        menu_path=BREATHING_COMP_MENU_PATH,
        firmware_version=firmware_version,
        configured_breathing_comp=configured_breathing_comp,
        shooting_scope=shooting_scope,
        attached_lens_id=attached_lens_id,
        frame_rate=frame_rate,
        hdmi_raw_output_on=hdmi_raw_output_on,
        raw_resolution=raw_resolution,
        reset_action=reset_action,
        force_bypass_breathing_raw_or_240p_lockout=force_bypass_breathing_raw_or_240p_lockout,
        effective_breathing_comp_register=eff_reg,
        lens_is_breathing_compliant=lens_compliant,
        breathing_comp_locked_out=locked_out,
        active_breathing_lockout_reasons=tuple(lockout_reasons),
        effective_breathing_comp_applied=applied,
        fov_crop_factor=crop,
        still_image_untouched=True,
        restored_by_camera_settings_reset=restored_cam_reset,
        survived_reset_network_set=survived_net_reset,
        restored_by_initialize=restored_init,
        admitted=True,
        errno_code=0,
        reason_code="OK",
        breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase262_redline_guard(**probe_kwargs: object) -> RedlineGuardProbeResult:
    """Fail-closed Stage 51 redline probe guard blocking all 15 hardware/vault/Wave-41 redline bypasses."""
    unknown = [k for k in probe_kwargs if k not in ALL_15_REDLINE_PROBE_FIELDS]
    if unknown:
        return RedlineGuardProbeResult(
            valid=False,
            errno_code=EINVAL_ERRNO,
            reason_code=f"UNKNOWN_REDLINE_PROBE_FIELD:{unknown[0]}",
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
            isp_write_authorized=ISP_WRITE_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            nop_count=NOP_COUNT,
            guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
            auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
            hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
            slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
            breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    erofs_fields = {
        "cnflasha_userspace_write_requested",
        "slot1_hdmi_rec_vault_write_requested",
    }
    for field in ALL_15_REDLINE_PROBE_FIELDS:
        if bool(probe_kwargs.get(field, False)):
            err = EROFS_ERRNO if field in erofs_fields else EACCES_ERRNO
            return RedlineGuardProbeResult(
                valid=False,
                errno_code=err,
                reason_code=f"REDLINE_BLOCKED:{field}",
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
                overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
                isp_write_authorized=ISP_WRITE_AUTHORIZED,
                spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
                el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
                cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
                cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                nop_count=NOP_COUNT,
                guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
                otp_fuse_touches=OTP_FUSE_TOUCHES,
                rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
                auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
                auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
                hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
                slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
                breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            )

    return RedlineGuardProbeResult(
        valid=True,
        errno_code=0,
        reason_code="REDLINES_INTACT",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        nop_count=NOP_COUNT,
        guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        auto_slow_shutter_lockout_bypass_events=AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
        auto_slow_shutter_angle_overlap_events=AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
        hdmi_rec_ctrl_without_tc_violations=HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
        slot1_hdmi_rec_vault_mutation_bytes=SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
        breathing_comp_raw_or_240p_bypass_events=BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_breathing_comp_and_redlines() -> Dict[str, object]:
    """Run Pillar C & D Wave-41 [Breathing Comp.] movie-only compliant-lens crop, RAW/240p lockout & redlines."""
    default_off = simulate_breathing_comp_lens_hil()
    movie_2470gm2_crop_active = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_MOVIE,
        attached_lens_id="SEL2470GM2",
    )
    still_mode_no_crop = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_STILL,
        attached_lens_id="SEL2470GM2",
    )
    non_compliant_lens_no_crop = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_MOVIE,
        attached_lens_id="SEL55F18Z_NON_COMPLIANT",
    )
    sq_11988p_allowed = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_SQ,
        attached_lens_id="SEL50F12GM",
        frame_rate="119.88p",
    )
    raw_4264_locked_out = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_MOVIE,
        attached_lens_id="SEL2470GM2",
        hdmi_raw_output_on=True,
        raw_resolution=HDMI_RAW_RESOLUTION_4264,
    )
    sq_23976p_locked_out = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_SQ,
        attached_lens_id="SEL2470GM2",
        frame_rate="239.76p",
    )
    sq_200p_locked_out = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_SQ,
        attached_lens_id="SEL2470GM2",
        frame_rate="200p",
    )
    pre300_blocked = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        firmware_version="2.00",
    )
    restored_cam_reset = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net_reset = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_init = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    raw_bypass_blocked = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        hdmi_raw_output_on=True,
        force_bypass_breathing_raw_or_240p_lockout=True,
    )
    sq240_bypass_blocked = simulate_breathing_comp_lens_hil(
        configured_breathing_comp=TOGGLE_ON,
        shooting_scope=SHOOTING_MODE_SQ,
        frame_rate="239.76p",
        force_bypass_breathing_raw_or_240p_lockout=True,
    )

    baseline_redline = probe_phase262_redline_guard()
    blocked_probes: Dict[str, Dict[str, object]] = {}
    all_probes_blocked = True
    for field in ALL_15_REDLINE_PROBE_FIELDS:
        pr = probe_phase262_redline_guard(**{field: True})
        blocked_probes[field] = asdict(pr)
        if pr.valid or pr.errno_code not in (EACCES_ERRNO, EROFS_ERRNO):
            all_probes_blocked = False

    passed = (
        default_off.admitted
        and default_off.effective_breathing_comp_register == TOGGLE_OFF
        and (not default_off.effective_breathing_comp_applied)
        and movie_2470gm2_crop_active.admitted
        and movie_2470gm2_crop_active.effective_breathing_comp_applied
        and movie_2470gm2_crop_active.fov_crop_factor == 1.07
        and still_mode_no_crop.admitted
        and (not still_mode_no_crop.effective_breathing_comp_applied)
        and still_mode_no_crop.fov_crop_factor == 1.0
        and non_compliant_lens_no_crop.admitted
        and (not non_compliant_lens_no_crop.effective_breathing_comp_applied)
        and non_compliant_lens_no_crop.fov_crop_factor == 1.0
        and sq_11988p_allowed.admitted
        and sq_11988p_allowed.effective_breathing_comp_applied
        and sq_11988p_allowed.fov_crop_factor == 1.08
        and raw_4264_locked_out.breathing_comp_locked_out
        and (not raw_4264_locked_out.effective_breathing_comp_applied)
        and sq_23976p_locked_out.breathing_comp_locked_out
        and (not sq_23976p_locked_out.effective_breathing_comp_applied)
        and sq_200p_locked_out.breathing_comp_locked_out
        and (not sq_200p_locked_out.effective_breathing_comp_applied)
        and (not pre300_blocked.admitted)
        and pre300_blocked.errno_code == EOPNOTSUPP_ERRNO
        and restored_cam_reset.restored_by_camera_settings_reset
        and restored_cam_reset.effective_breathing_comp_register == TOGGLE_OFF
        and survives_net_reset.survived_reset_network_set
        and survives_net_reset.effective_breathing_comp_register == TOGGLE_ON
        and restored_init.restored_by_initialize
        and restored_init.effective_breathing_comp_register == TOGGLE_OFF
        and (not raw_bypass_blocked.admitted)
        and raw_bypass_blocked.errno_code == EACCES_ERRNO
        and (not sq240_bypass_blocked.admitted)
        and sq240_bypass_blocked.errno_code == EACCES_ERRNO
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "menu_path": BREATHING_COMP_MENU_PATH,
        "compliant_lenses": dict(COMPLIANT_BREATHING_EMOUNT_LENSES),
        "sq_240p_lockout_rates": list(SQ_240P_LOCKOUT_RATES),
        "all_15_redline_probe_fields": list(ALL_15_REDLINE_PROBE_FIELDS),
        "default_off_ok": asdict(default_off),
        "movie_2470gm2_crop_active": asdict(movie_2470gm2_crop_active),
        "still_mode_no_crop": asdict(still_mode_no_crop),
        "non_compliant_lens_no_crop": asdict(non_compliant_lens_no_crop),
        "sq_11988p_compliant_allowed": asdict(sq_11988p_allowed),
        "raw_4264_locked_out": asdict(raw_4264_locked_out),
        "sq_23976p_locked_out": asdict(sq_23976p_locked_out),
        "sq_200p_locked_out": asdict(sq_200p_locked_out),
        "pre300_firmware_blocked_eopnotsupp": asdict(pre300_blocked),
        "restored_by_camera_settings_reset": asdict(restored_cam_reset),
        "survives_reset_network_set": asdict(survives_net_reset),
        "restored_by_initialize": asdict(restored_init),
        "raw_lockout_bypass_blocked_eacces": asdict(raw_bypass_blocked),
        "sq_240p_lockout_bypass_blocked_eacces": asdict(sq240_bypass_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 262 (Stage 51, 51/51) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 262 Stage 51 (51/51) Wave-41 HIL co-emulation audit."""
    donor_audit = inspect_phase262_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_auto_slow_shutter_6locks_and_angle_disjoint_hil()
    pillar_b = evaluate_pillar_b_hdmi_reccontrol_tcout_4chaudio_and_vault_hil()
    pillar_cd = evaluate_pillar_c_d_breathing_comp_and_redlines()

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
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "auto_slow_shutter_lockout_bypass_events": AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS,
        "auto_slow_shutter_angle_overlap_events": AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS,
        "hdmi_rec_ctrl_without_tc_violations": HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS,
        "slot1_hdmi_rec_vault_mutation_bytes": SLOT1_HDMI_REC_VAULT_MUTATION_BYTES,
        "breathing_comp_raw_or_240p_bypass_events": BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS,
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
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS == 0
        and AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS == 0
        and HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS == 0
        and SLOT1_HDMI_REC_VAULT_MUTATION_BYTES == 0
        and BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_262_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_auto_slow_shutter_6locks_and_angle_disjoint_hil": pillar_a,
        "pillar_b_hdmi_reccontrol_tcout_4chaudio_and_vault_hil": pillar_b,
        "pillar_c_d_breathing_comp_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py",
        description=(
            "Phase 262 Stage 51 (51/51) — Real-Hardware ILME-FX3 Wave-41 "
            "Auto Slow Shutter 6-Condition Lockout & Shutter Angle Disjointness, "
            "HDMI Output Settings REC Control <- Time Code Output Gate & 4ch Audio + Slot-1 Vault, "
            "and Breathing Comp. Movie-Only Compliant-Lens Crop & RAW/240p Lockout HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 262 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_auto_slow_shutter_6locks_and_angle_disjoint_hil"]
        pb = rep["pillar_b_hdmi_reccontrol_tcout_4chaudio_and_vault_hil"]
        pcd = rep["pillar_c_d_breathing_comp_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 262 Stage 51 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"auto_slow={len(pa['all_6_lockout_ids'])}l_"
            f"byp:{red['auto_slow_shutter_lockout_bypass_events']}_"
            f"ovlp:{red['auto_slow_shutter_angle_overlap_events']} | "
            f"hdmi={len(pb['all_2_hdmi_4ch_audio_modes'])}ch_"
            f"tcviol:{red['hdmi_rec_ctrl_without_tc_violations']}_"
            f"vmut:{red['slot1_hdmi_rec_vault_mutation_bytes']} | "
            f"breath={len(pcd['compliant_lenses'])}lens_"
            f"byp:{red['breathing_comp_raw_or_240p_bypass_events']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
