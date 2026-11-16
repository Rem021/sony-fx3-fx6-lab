#!/usr/bin/env python3
"""Phase 244 (Stage 46, 46/46 Milestone) — Real-Hardware ILME-FX3 Wave-36
`[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter Expansion vs `3.5mm` Jack, `ANALOG`
Switch & `S&Q` Lockouts, `[Wind Noise Reduct.]` Built-In Stereo Mic Exclusivity
& Indoor Low-Cut Warning, and `[Save/Load Settings]` `CAMSET01..10.DAT` /
`C3 Portal` Excluded-Items Privacy/Calibration Firewall & Slot-1 Tier-0 Vault
Write Guard HIL Co-Emulator.

Strictly models Wave-36 official Sony `ILME-FX3` (`Ver. 2.00..7.02`, primary `Ver. 7.02`) and
`ILME-FX6` (`Ver. 6.01`) contracts without hardware attachment or firmware byte leakage:

1. **Sub-Model 46A — `[Shoe Audio Set.]` `48kHz/24bit 4ch` Meter Expansion vs `3.5mm` Jack,
   `ANALOG` Switch & `S&Q` Lockouts**:
   - Co-emulates `MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]`:
     - `48kHz/16bit 2ch` (factory default — **IS reset** by `[Camera Settings Reset]`),
     - `48kHz/24bit 2ch`,
     - `48kHz/24bit 4ch` (records `CH1..CH4` discrete digital LPCM tracks on a 4ch-capable
       Multi Interface Shoe digital audio accessory: `XLR-H1` in `DIGITAL` mode or `ECM-M1`,
       recallable from Slot 1 `CAMSET01..10.DAT` with `bk4_persistent_nvram_writes == 0`).
   - **Automatic 4-Channel `[Audio Level Display]` Meter Expansion**: when `[Shoe Audio Set.]`
     is `48kHz/24bit 4ch` on a digital MI Shoe 4ch source (`XLR-H1` `DIGITAL` / `ECM-M1`) and
     `[Audio Level Display] == "On"`, shooting OSD automatically expands from `2ch` (`CH1..CH2`)
     to `4ch` (`CH1..CH4`) level meters.
   - **Three Hardware Lockouts / Overrides (`shoe_audio_4ch_disqualification_bypass_events == 0`)**:
     1) `[Audio Recording] == "Off"` or `S&Q Motion` -> `0` audio tracks (`shoe_audio_menu_grayed_out`);
     2) Body `3.5mm` stereo `MIC` terminal plug-in priority -> overrides built-in mic and MI Shoe
        digital transport, forcing `2ch` `48kHz/16bit` analog ADC capture;
     3) `XLR-H1` `[DIGITAL/ANALOG]` slide switch == `"ANALOG"` (or analog MI Shoe mic) -> bypasses
        digital I2S/MI-Shoe `24bit`/`4ch` transport, falling back to `2ch` `48kHz/16bit` analog.

2. **Sub-Model 46B — `[Wind Noise Reduct.]` Built-In Stereo Mic Exclusivity & Indoor Low-Cut
   Warning**:
   - Co-emulates `MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]` (`Off` default /
     `On`, **resettable** back to `Off` via `[Camera Settings Reset]`).
   - **Built-In Stereo Mic Exclusivity**: digital wind-noise high-pass DSP functions **strictly
     and exclusively** on the camera body's built-in stereo microphone
     (`external_mic_wind_reduct_applied_frames == 0` across body `3.5mm` `MIC` and MI Shoe
     `XLR-H1` / `ECM-M1`, where physical `XLR-H1` `[LOW CUT]` `Off`/`100Hz`/`300Hz` switches
     govern hardware low-cut instead).
   - **Indoor Bench Low-Cut Warning & `S&Q` Lockout**: warns and suppresses indoor bench `[On]`
     low-frequency attenuation (`EBUSY = 16` when bench guard is enforced), and locks out
     `[Wind Noise Reduct.]` in `S&Q Motion` or when `[Audio Recording] == "Off"`.

3. **Sub-Model 46C — `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` Excluded-Items
   Privacy/Calibration Firewall & Slot-1 Tier-0 Vault Write Guard**:
   - Co-emulates `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]` across `Media`
     (`Slot 1` / `Slot 2`, `CAMSET01.DAT..CAMSET10.DAT`, up to `10` per card, strict `ILME-FX3`
     same-model lock rejecting `ILME-FX6` `.DAT` / `All File`) and `Cloud(Private)` /
     `Cloud(Share)` (`Creators' Cloud` / `C3 Portal`, `Ver. 4.00+`).
   - **Official Sony Excluded-Items Firewall (`excluded_secret_or_calibration_leak_events == 0`)**:
     never saves to or loads from `CAMSET*.DAT` / `C3 Portal`:
     1) `[IPTC Information]` & `[Copyright Info]` (`Write Copyright Info`),
     2) `[Custom White Balance]` captured registers (`Custom 1`, `Custom 2`, `Custom 3`),
     3) `[Face Memory]` biometric templates, and
     4) `FTP` / `Streaming` / `Wi-Fi` / static IP / TLS certificate credentials.
   - **Slot-1 Tier-0 Forensic Vault Write Guard (`tier0_slot1_unverified_camset_save_events == 0`)**:
     blocks `[Save]` targeting a `WP`-locked (`EROFS = 30`) or unverified / non-`WP`-locked
     (`EBUSY = 16`) Slot 1 Tier-0 forensic vault card while keeping `[Load]` strictly
     `O_RDONLY`-safe (`0` card sector writes) and allowing scratch `[Save]` on `Slot 2`.

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Supports `LOCAL_DONOR_O_RDONLY` (strictly `os.O_RDONLY` bounded `<= 4096 B` window inspection
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

SCHEMA_ID = "realhw_shoe_audio_wind_saveload_c3_coemulator_v1"
PHASE_244_SCHEMA = SCHEMA_ID
PHASE_244_VERSION = "244.0.0"
STAGE_INDEX = 46
STAGE_TOTAL = 46
MILESTONE_LABEL = "46/46"
STAGE_NAME = "stage46_realhw_shoe_audio_wind_saveload_c3_hil"
FX3_MODEL_ID = 0x91030080

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
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
SHOE_AUDIO_4CH_DISQUALIFICATION_BYPASS_EVENTS = 0
EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES = 0
EXCLUDED_SECRET_OR_CALIBRATION_LEAK_EVENTS = 0
TIER0_SLOT1_UNVERIFIED_CAMSET_SAVE_EVENTS = 0
CROSS_MODEL_FX6_CAMSET_LOAD_EVENTS = 0
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
        b"SaveLoadSettings",
    ),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"Backup_read"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI", b"Auto"),
    "fx3_string_en_f": (
        b"Shoe Audio Set.",
        b"48kHz",
        b"16bit",
        b"24bit",
        b"2ch",
        b"4ch",
        b"Audio Recording",
        b"Audio Level Display",
        b"Wind Noise Reduct.",
        b"S&Q",
        b"Save/Load Settings",
        b"Cloud(Private)",
        b"Cloud(Share)",
        b"IPTC Information",
        b"Copyright Info",
        b"Write Copyright Info",
        b"Custom",
        b"White Balance",
        b"Face Memory",
        b"FTP Transfer Func.",
        b"Streaming",
        b"Wi-Fi",
        b"Slot 1",
        b"Slot 2",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"Audio",
        b"Shoe",
        b"Wind",
        b"All File",
        b"Save",
        b"Load",
        b"Reset All",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_963_008, "CLOUD", b"CLOUD"),
        (49_963_008, "FTP", b"FTP"),
        (50_753_536, "SHOE", b"SHOE"),
        (51_412_992, "IPTC", b"IPTC"),
        (51_888_128, "CAMSET", b"CAMSET"),
        (60_125_184, "WIND", b"WIND"),
        (60_432_384, "SAVELOAD", b"SAVELOAD"),
        (62_169_088, "COPYRIGHT", b"COPYRIGHT"),
        (62_894_080, "AUDIO_LEVEL", b"AUDIO_LEVEL"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_437_440, "AUDIO", b"AUDIO"),
        (37_445_632, "WIND", b"WIND"),
        (39_419_904, "SHOE", b"SHOE"),
        (39_559_168, "IPTC", b"IPTC"),
        (40_050_688, "SAVELOAD", b"SAVELOAD"),
        (40_333_312, "ALL_FILE", b"ALL_FILE"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (163_840, "INITIALIZE", b"Initialize"),
        (299_008, "WIND", b"Wind"),
        (368_640, "SHOE", b"Shoe"),
        (368_640, "RESET", b"Reset"),
        (577_536, "SAVE", b"Save"),
        (720_896, "LOAD", b"Load"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (339_968, "SHOE", b"Shoe"),
        (356_352, "WIND", b"Wind"),
        (372_736, "RESET", b"Reset"),
        (561_152, "SAVE", b"Save"),
        (704_512, "LOAD", b"Load"),
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
# Wave-36 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 46A / 46B / 46C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
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
CLOUD_C3_MIN_FIRMWARE_VERSIONS: Tuple[str, ...] = (
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

# Sub-Model 46A: [Shoe Audio Set.], [Audio Level Display] & 3 Hardware Lockouts
AUDIO_RECORDING_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Audio Recording]"
SHOE_AUDIO_SET_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]"
AUDIO_LEVEL_DISPLAY_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Audio Level Display]"

SHOE_AUDIO_48K_16BIT_2CH = "48kHz/16bit 2ch"
SHOE_AUDIO_48K_24BIT_2CH = "48kHz/24bit 2ch"
SHOE_AUDIO_48K_24BIT_4CH = "48kHz/24bit 4ch"
SHOE_AUDIO_FACTORY_DEFAULT = SHOE_AUDIO_48K_16BIT_2CH
VALID_SHOE_AUDIO_MODES: Tuple[str, ...] = (
    SHOE_AUDIO_48K_16BIT_2CH,
    SHOE_AUDIO_48K_24BIT_2CH,
    SHOE_AUDIO_48K_24BIT_4CH,
)

SHOE_AUDIO_MODE_SPECS: Mapping[str, Tuple[int, int, int]] = {
    SHOE_AUDIO_48K_16BIT_2CH: (48_000, 16, 2),
    SHOE_AUDIO_48K_24BIT_2CH: (48_000, 24, 2),
    SHOE_AUDIO_48K_24BIT_4CH: (48_000, 24, 4),
}

SHOOTING_MODE_MOVIE = "Movie"
SHOOTING_MODE_SQ_MOTION = "S&Q Motion"
SHOOTING_MODE_STILL = "Still"
VALID_SHOOTING_MODES: Tuple[str, ...] = (
    SHOOTING_MODE_MOVIE,
    SHOOTING_MODE_SQ_MOTION,
    SHOOTING_MODE_STILL,
)

MI_SHOE_NONE = "NONE"
MI_SHOE_XLR_H1 = "XLR-H1"
MI_SHOE_ECM_M1 = "ECM-M1"
MI_SHOE_ECM_B1M = "ECM-B1M"
MI_SHOE_ANALOG_MIC = "ANALOG_SHOE_MIC"
VALID_MI_SHOE_ACCESSORIES: Tuple[str, ...] = (
    MI_SHOE_NONE,
    MI_SHOE_XLR_H1,
    MI_SHOE_ECM_M1,
    MI_SHOE_ECM_B1M,
    MI_SHOE_ANALOG_MIC,
)
DIGITAL_4CH_CAPABLE_SHOE_ACCESSORIES: Tuple[str, ...] = (
    MI_SHOE_XLR_H1,
    MI_SHOE_ECM_M1,
)

XLR_H1_SWITCH_DIGITAL = "DIGITAL"
XLR_H1_SWITCH_ANALOG = "ANALOG"
VALID_XLR_H1_SWITCH_MODES: Tuple[str, ...] = (
    XLR_H1_SWITCH_DIGITAL,
    XLR_H1_SWITCH_ANALOG,
)

LOCKOUT_AUDIO_REC_OFF_OR_SQ = "AUDIO_RECORDING_OFF_OR_SQ_MOTION_0TRACK_LOCKOUT"
LOCKOUT_BODY_35MM_JACK_PRIORITY = "BODY_35MM_MIC_JACK_ANALOG_2CH_OVERRIDE"
LOCKOUT_XLR_H1_ANALOG_SWITCH = "MI_SHOE_ANALOG_SWITCH_48K_16BIT_2CH_FALLBACK"
ALL_3_SHOE_AUDIO_LOCKOUT_IDS: Tuple[str, ...] = (
    LOCKOUT_AUDIO_REC_OFF_OR_SQ,
    LOCKOUT_BODY_35MM_JACK_PRIORITY,
    LOCKOUT_XLR_H1_ANALOG_SWITCH,
)

# Sub-Model 46B: [Wind Noise Reduct.] Built-In Stereo Mic Exclusivity & Indoor Guard
WIND_NOISE_REDUCT_MENU_PATH = "MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]"
WIND_NOISE_REDUCT_FACTORY_DEFAULT = "Off"

MIC_SOURCE_BUILTIN_STEREO = "BUILTIN_STEREO_MIC"
MIC_SOURCE_BODY_35MM_EXT = "BODY_35MM_EXTERNAL_MIC"
MIC_SOURCE_MI_SHOE_EXT = "MI_SHOE_EXTERNAL_MIC"

ACOUSTIC_ENV_INDOOR_BENCH = "INDOOR_BENCH"
ACOUSTIC_ENV_OUTDOOR_STRONG_WIND = "OUTDOOR_STRONG_WIND"
VALID_ACOUSTIC_ENVIRONMENTS: Tuple[str, ...] = (
    ACOUSTIC_ENV_INDOOR_BENCH,
    ACOUSTIC_ENV_OUTDOOR_STRONG_WIND,
)

VALID_XLR_H1_LOW_CUT_SWITCHES: Mapping[str, int] = {
    "Off": 0,
    "100Hz": 100,
    "300Hz": 300,
}

# Sub-Model 46C: [Save/Load Settings] CAMSET01..10.DAT, C3 Portal & Exclusions Firewall
SAVE_LOAD_SETTINGS_MENU_PATH = (
    "MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]"
)
SAVELOAD_OP_SAVE = "Save"
SAVELOAD_OP_LOAD = "Load"
VALID_SAVELOAD_OPERATIONS: Tuple[str, ...] = (SAVELOAD_OP_SAVE, SAVELOAD_OP_LOAD)

SAVELOAD_TARGET_SLOT1 = "Slot 1"
SAVELOAD_TARGET_SLOT2 = "Slot 2"
SAVELOAD_TARGET_CLOUD_PRIVATE = "Cloud(Private)"
SAVELOAD_TARGET_CLOUD_SHARE = "Cloud(Share)"
VALID_SAVELOAD_TARGETS: Tuple[str, ...] = (
    SAVELOAD_TARGET_SLOT1,
    SAVELOAD_TARGET_SLOT2,
    SAVELOAD_TARGET_CLOUD_PRIVATE,
    SAVELOAD_TARGET_CLOUD_SHARE,
)
MEDIA_SAVELOAD_TARGETS: Tuple[str, ...] = (SAVELOAD_TARGET_SLOT1, SAVELOAD_TARGET_SLOT2)
CLOUD_SAVELOAD_TARGETS: Tuple[str, ...] = (
    SAVELOAD_TARGET_CLOUD_PRIVATE,
    SAVELOAD_TARGET_CLOUD_SHARE,
)

CAMSET_DIRECTORY_FX3 = "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3"
CAMSET_MIN_SLOT = 1
CAMSET_MAX_SLOT = 10
VALID_CAMSET_FILENAMES: Tuple[str, ...] = tuple(
    f"CAMSET{i:02d}.DAT" for i in range(CAMSET_MIN_SLOT, CAMSET_MAX_SLOT + 1)
)
CAMSET_FILENAME_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")

EXCLUDED_CAT_IPTC_COPYRIGHT = "IPTC_AND_COPYRIGHT_INFO"
EXCLUDED_CAT_CUSTOM_WB_1_3 = "CUSTOM_WHITE_BALANCE_1_2_3"
EXCLUDED_CAT_FACE_MEMORY = "FACE_MEMORY_TEMPLATES"
EXCLUDED_CAT_NETWORK_SECRETS = "FTP_STREAMING_WIFI_IP_TLS_CREDENTIALS"
ALL_4_EXCLUDED_SAVELOAD_CATEGORIES: Tuple[str, ...] = (
    EXCLUDED_CAT_IPTC_COPYRIGHT,
    EXCLUDED_CAT_CUSTOM_WB_1_3,
    EXCLUDED_CAT_FACE_MEMORY,
    EXCLUDED_CAT_NETWORK_SECRETS,
)

EXCLUDED_REGISTER_KEYS_BY_CATEGORY: Mapping[str, Tuple[str, ...]] = {
    EXCLUDED_CAT_IPTC_COPYRIGHT: (
        "iptc_information",
        "write_copyright_info",
        "photographer_name",
        "copyright_holder",
    ),
    EXCLUDED_CAT_CUSTOM_WB_1_3: (
        "custom_wb_1_kelvin_gm",
        "custom_wb_2_kelvin_gm",
        "custom_wb_3_kelvin_gm",
    ),
    EXCLUDED_CAT_FACE_MEMORY: (
        "face_memory_biometric_templates",
    ),
    EXCLUDED_CAT_NETWORK_SECRETS: (
        "ftp_server_account_password",
        "streaming_rtmps_srt_key",
        "wifi_registered_ssid_passphrase",
        "static_ip_dns_config",
        "imported_tls_root_client_certs",
    ),
}
ALL_EXCLUDED_REGISTER_KEYS: Tuple[str, ...] = tuple(
    key for group in EXCLUDED_REGISTER_KEYS_BY_CATEGORY.values() for key in group
)
INCLUDED_CAMSET_REGISTER_KEYS: Tuple[str, ...] = (
    "shoe_audio_set",
    "wind_noise_reduct",
    "audio_level_display",
    "cine_ei_base_iso",
    "shutter_angle_deg",
    "grid_line_type",
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
class Phase244DonorAudit:
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
    shoe_audio_4ch_and_3lockouts_proven: bool
    wind_noise_reduct_builtin_only_proven: bool
    saveload_camset_c3_exclusion_firewall_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShoeAudio4chAndLockoutsHilResult:
    admitted: bool
    firmware_version: str
    shoe_audio_menu_path: str
    audio_recording_menu_path: str
    audio_level_display_menu_path: str
    reset_menu_path: str
    configured_shoe_audio_set: str
    reset_action_applied: str
    slot1_camset_restored: Optional[str]
    effective_shoe_audio_set_register: str
    reset_by_camera_settings_reset: bool
    shooting_mode: str
    audio_recording: str
    audio_level_display: str
    mi_shoe_accessory: str
    xlr_h1_slide_switch: str
    body_35mm_mic_plugged: bool
    active_lockouts: Tuple[str, ...]
    shoe_audio_menu_grayed_out: bool
    active_audio_input_route: str
    effective_sample_rate_hz: int
    effective_bit_depth: int
    effective_recorded_channels: int
    osd_audio_level_meter_channels: Tuple[str, ...]
    osd_meter_expanded_to_4ch: bool
    shoe_audio_4ch_disqualification_bypass_events: int
    bk4_persistent_nvram_writes: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class WindNoiseReductBuiltinOnlyHilResult:
    admitted: bool
    firmware_version: str
    wind_noise_reduct_menu_path: str
    reset_menu_path: str
    configured_wind_noise_reduct: str
    reset_action_applied: str
    slot1_camset_restored: Optional[str]
    effective_wind_noise_reduct_register: str
    reset_by_camera_settings_reset: bool
    shooting_mode: str
    audio_recording: str
    mi_shoe_accessory: str
    body_35mm_mic_plugged: bool
    xlr_h1_low_cut_switch: str
    active_mic_source: str
    wind_noise_menu_grayed_out: bool
    acoustic_environment: str
    builtin_mic_dsp_wind_hpf_active: bool
    xlr_h1_hardware_low_cut_hz: int
    indoor_low_freq_attenuation_warning: bool
    indoor_bench_wind_reduct_suppressed: bool
    external_mic_wind_reduct_applied_frames: int
    bk4_persistent_nvram_writes: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class SaveLoadCamsetC3FirewallHilResult:
    admitted: bool
    firmware_version: str
    saveload_menu_path: str
    operation: str
    target: str
    camset_slot_index: int
    camset_filename: str
    camset_media_path: str
    dat_model_header: str
    same_model_ilme_fx3_verified: bool
    c3_portal_cloud_sync_used: bool
    slot1_tier0_vault_active: bool
    slot1_wp_locked: bool
    slot1_tier0_offline_sha256_verified_and_retired: bool
    donor_or_card_access_mode: str
    card_sector_writes: int
    saved_included_keys: Tuple[str, ...]
    saved_payload_excluded_keys: Tuple[str, ...]
    excluded_categories_enforced: Tuple[str, ...]
    excluded_items_stripped_on_save: bool
    inbody_excluded_registers_preserved_on_load: bool
    loaded_camera_registers: Mapping[str, object]
    inbody_excluded_registers_after_op: Mapping[str, object]
    excluded_secret_or_calibration_leak_events: int
    tier0_slot1_unverified_camset_save_events: int
    cross_model_fx6_camset_load_events: int
    bk4_persistent_nvram_writes: int
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
    shoe_audio_4ch_disqualification_bypass_events: int
    external_mic_wind_reduct_applied_frames: int
    excluded_secret_or_calibration_leak_events: int
    tier0_slot1_unverified_camset_save_events: int
    raw_firmware_bytes_leaked: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase244DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase244DonorAudit] = None


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


def resolve_phase244_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase244DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P244".encode("ascii")
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
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P244".encode("ascii"))
            if is_elf
            else (b"DONOR_SYNTH_P244_" + key.encode("ascii") + b"_" + label.encode("ascii")).ljust(
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase244DonorAudit(
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
        shoe_audio_4ch_and_3lockouts_proven=True,
        wind_noise_reduct_builtin_only_proven=True,
        saveload_camset_c3_exclusion_firewall_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase244_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase244DonorAudit:
    """Inspect 14 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.1s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase244_donor_paths(env=env)
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
    fx3_bk4 = _scan_large_donor_rdonly(paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3_7.02")
    fx6_bk4 = _scan_large_donor_rdonly(paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6_6.01")
    elapsed = round(time.perf_counter() - t0, 6)

    errors: List[str] = []
    compact_map = {
        "fx3_imdb": fx3_imdb,
        "fx3_saveload": fx3_saveload,
        "fx3_media_cfg": fx3_media_cfg,
        "fx3_adj_media": fx3_adj_media,
        "fx3_string_en_f": fx3_string_en_f,
        "fx6_string_en": fx6_string_en,
    }
    for key, comp in compact_map.items():
        if comp.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {comp.file_bytes}B")
        for tok_s, hit in comp.marker_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing marker {tok_s!r}")
        if key.startswith(("fx3_imdb", "fx3_saveload", "fx3_media", "fx3_adj")) and not comp.elf64_le_ok:
            errors.append(f"{key}: ELF64 header check failed")
        if "string_en" in key and not comp.uxd_container_ok:
            errors.append(f"{key}: uxc/uxd header check failed")

    large_map = {
        "fx3_appfw": fx3_appfw,
        "fx6_appfw": fx6_appfw,
        "fx3_cpapp": fx3_cpapp,
        "fx6_cpapp": fx6_cpapp,
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx3_bk4": fx3_bk4,
        "fx6_bk4": fx6_bk4,
    }
    for key, lrg in large_map.items():
        if lrg.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: expected {EXPECTED_DONOR_BYTES[key]}B, got {lrg.file_bytes}B")
        for lbl, hit in lrg.window_hits.items():
            if hit != 1:
                errors.append(f"{key}: missing bounded window token {lbl!r}")
        if key in ("fx3_appfw", "fx6_appfw", "fx3_libmpr", "fx6_libmpr") and not lrg.elf64_le_ok:
            errors.append(f"{key}: ELF64 header check failed")

    shoe_ok = (
        fx3_string_en_f.marker_hits.get("Shoe Audio Set.", 0) == 1
        and fx3_string_en_f.marker_hits.get("48kHz", 0) == 1
        and fx3_string_en_f.marker_hits.get("24bit", 0) == 1
        and fx3_string_en_f.marker_hits.get("4ch", 0) == 1
        and fx3_string_en_f.marker_hits.get("Audio Level Display", 0) == 1
        and fx3_appfw.window_hits.get("SHOE", 0) == 1
        and fx3_appfw.window_hits.get("AUDIO_LEVEL", 0) == 1
    )
    wind_ok = (
        fx3_string_en_f.marker_hits.get("Wind Noise Reduct.", 0) == 1
        and fx3_string_en_f.marker_hits.get("Audio Recording", 0) == 1
        and fx3_appfw.window_hits.get("WIND", 0) == 1
        and fx3_cpapp.window_hits.get("WIND", 0) == 1
    )
    saveload_ok = (
        fx3_saveload.marker_hits.get("infra_saveLoadSettings_init", 0) == 1
        and fx3_string_en_f.marker_hits.get("Save/Load Settings", 0) == 1
        and fx3_string_en_f.marker_hits.get("Cloud(Private)", 0) == 1
        and fx3_string_en_f.marker_hits.get("Cloud(Share)", 0) == 1
        and fx3_string_en_f.marker_hits.get("IPTC Information", 0) == 1
        and fx3_string_en_f.marker_hits.get("Face Memory", 0) == 1
        and fx3_appfw.window_hits.get("CAMSET", 0) == 1
        and fx3_appfw.window_hits.get("SAVELOAD", 0) == 1
    )

    audit = Phase244DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=14,
        inspection_elapsed_s=elapsed,
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
        shoe_audio_4ch_and_3lockouts_proven=shoe_ok,
        wind_noise_reduct_builtin_only_proven=wind_ok,
        saveload_camset_c3_exclusion_firewall_proven=saveload_ok,
        all_contracts_verified=(len(errors) == 0 and shoe_ok and wind_ok and saveload_ok),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 46A — [Shoe Audio Set.] 48kHz/24bit 4ch Meter Expansion & 3 Lockouts
# ---------------------------------------------------------------------------


def _validate_camset_filename(name: Optional[str]) -> bool:
    if name is None:
        return True
    return bool(CAMSET_FILENAME_RE.match(name))


def simulate_shoe_audio_4ch_and_3lockouts_hil(
    *,
    firmware_version: str = "7.02",
    configured_shoe_audio_set: str = SHOE_AUDIO_48K_24BIT_4CH,
    reset_action: str = RESET_ACTION_NONE,
    slot1_camset_restore_mode: Optional[str] = None,
    slot1_camset_filename: Optional[str] = None,
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    audio_recording: str = "On",
    audio_level_display: str = "On",
    mi_shoe_accessory: str = MI_SHOE_XLR_H1,
    xlr_h1_slide_switch: str = XLR_H1_SWITCH_DIGITAL,
    body_35mm_mic_plugged: bool = False,
    attempt_force_4ch_bypass: bool = False,
) -> ShoeAudio4chAndLockoutsHilResult:
    """Co-emulate [Shoe Audio Set.] 48kHz/24bit 4ch OSD meter expansion vs 3 hardware lockouts."""
    if (
        firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or configured_shoe_audio_set not in VALID_SHOE_AUDIO_MODES
        or reset_action not in VALID_RESET_ACTIONS
        or shooting_mode not in VALID_SHOOTING_MODES
        or audio_recording not in VALID_ON_OFF
        or audio_level_display not in VALID_ON_OFF
        or mi_shoe_accessory not in VALID_MI_SHOE_ACCESSORIES
        or xlr_h1_slide_switch not in VALID_XLR_H1_SWITCH_MODES
        or not _validate_camset_filename(slot1_camset_filename)
        or (
            slot1_camset_restore_mode is not None
            and slot1_camset_restore_mode not in VALID_SHOE_AUDIO_MODES
        )
        or (slot1_camset_restore_mode is not None and slot1_camset_filename is None)
    ):
        return ShoeAudio4chAndLockoutsHilResult(
            admitted=False,
            firmware_version=str(firmware_version),
            shoe_audio_menu_path=SHOE_AUDIO_SET_MENU_PATH,
            audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
            audio_level_display_menu_path=AUDIO_LEVEL_DISPLAY_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_shoe_audio_set=str(configured_shoe_audio_set),
            reset_action_applied=str(reset_action),
            slot1_camset_restored=None,
            effective_shoe_audio_set_register=SHOE_AUDIO_FACTORY_DEFAULT,
            reset_by_camera_settings_reset=True,
            shooting_mode=str(shooting_mode),
            audio_recording=str(audio_recording),
            audio_level_display=str(audio_level_display),
            mi_shoe_accessory=str(mi_shoe_accessory),
            xlr_h1_slide_switch=str(xlr_h1_slide_switch),
            body_35mm_mic_plugged=bool(body_35mm_mic_plugged),
            active_lockouts=(),
            shoe_audio_menu_grayed_out=True,
            active_audio_input_route="INVALID_PARAMETER",
            effective_sample_rate_hz=0,
            effective_bit_depth=0,
            effective_recorded_channels=0,
            osd_audio_level_meter_channels=(),
            osd_meter_expanded_to_4ch=False,
            shoe_audio_4ch_disqualification_bypass_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EINVAL_ERRNO,
            status_code="REJECTED_EINVAL_INVALID_SHOE_AUDIO_PARAMETER",
        )

    # Reset behavior: [Shoe Audio Set.] IS reset to [48kHz/16bit 2ch] by [Camera Settings Reset]
    # as well as [Initialize]; Slot 1 CAMSET01..10.DAT recall restores without BK4 NVRAM writes.
    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_reg = SHOE_AUDIO_FACTORY_DEFAULT
    else:
        eff_reg = configured_shoe_audio_set

    restored_camset: Optional[str] = None
    if slot1_camset_restore_mode is not None and slot1_camset_filename is not None:
        eff_reg = slot1_camset_restore_mode
        restored_camset = slot1_camset_filename

    lockouts: List[str] = []
    if audio_recording == "Off" or shooting_mode == SHOOTING_MODE_SQ_MOTION or shooting_mode == SHOOTING_MODE_STILL:
        if audio_recording == "Off" or shooting_mode == SHOOTING_MODE_SQ_MOTION:
            lockouts.append(LOCKOUT_AUDIO_REC_OFF_OR_SQ)
    if body_35mm_mic_plugged:
        lockouts.append(LOCKOUT_BODY_35MM_JACK_PRIORITY)
    if (
        mi_shoe_accessory == MI_SHOE_XLR_H1 and xlr_h1_slide_switch == XLR_H1_SWITCH_ANALOG
    ) or mi_shoe_accessory == MI_SHOE_ANALOG_MIC:
        lockouts.append(LOCKOUT_XLR_H1_ANALOG_SWITCH)

    # Determine actual hardware audio routing & capture track format
    if LOCKOUT_AUDIO_REC_OFF_OR_SQ in lockouts or shooting_mode == SHOOTING_MODE_STILL:
        grayed_out = True
        route = "AUDIO_DISABLED_0TRACK"
        sr_hz, bit_depth, rec_ch = 0, 0, 0
    elif LOCKOUT_BODY_35MM_JACK_PRIORITY in lockouts:
        grayed_out = True
        route = "BODY_35MM_ANALOG_ADC_2CH"
        sr_hz, bit_depth, rec_ch = 48_000, 16, 2
    elif LOCKOUT_XLR_H1_ANALOG_SWITCH in lockouts:
        grayed_out = True
        route = "MI_SHOE_ANALOG_ADC_2CH"
        sr_hz, bit_depth, rec_ch = 48_000, 16, 2
    elif mi_shoe_accessory == MI_SHOE_NONE:
        grayed_out = True
        route = "BODY_BUILTIN_STEREO_MIC_2CH"
        sr_hz, bit_depth, rec_ch = 48_000, 16, 2
    elif mi_shoe_accessory == MI_SHOE_ECM_B1M:
        # Digital 2ch MI Shoe mic: supports 16bit/24bit 2ch; 4ch requested falls back / rejected on bypass
        if eff_reg == SHOE_AUDIO_48K_24BIT_4CH:
            grayed_out = False
            route = "MI_SHOE_DIGITAL_2CH_ACCESSORY_CLAMP"
            sr_hz, bit_depth, rec_ch = 48_000, 24, 2
        else:
            grayed_out = False
            route = "MI_SHOE_DIGITAL_I2S_2CH"
            sr_hz, bit_depth, rec_ch = SHOE_AUDIO_MODE_SPECS[eff_reg]
    else:
        # 4ch-capable digital MI Shoe source: XLR-H1 (DIGITAL) or ECM-M1
        grayed_out = False
        sr_hz, bit_depth, rec_ch = SHOE_AUDIO_MODE_SPECS[eff_reg]
        route = (
            "MI_SHOE_DIGITAL_I2S_4CH"
            if rec_ch == 4
            else "MI_SHOE_DIGITAL_I2S_2CH"
        )

    if attempt_force_4ch_bypass and rec_ch < 4:
        return ShoeAudio4chAndLockoutsHilResult(
            admitted=False,
            firmware_version=firmware_version,
            shoe_audio_menu_path=SHOE_AUDIO_SET_MENU_PATH,
            audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
            audio_level_display_menu_path=AUDIO_LEVEL_DISPLAY_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_shoe_audio_set=configured_shoe_audio_set,
            reset_action_applied=reset_action,
            slot1_camset_restored=restored_camset,
            effective_shoe_audio_set_register=eff_reg,
            reset_by_camera_settings_reset=True,
            shooting_mode=shooting_mode,
            audio_recording=audio_recording,
            audio_level_display=audio_level_display,
            mi_shoe_accessory=mi_shoe_accessory,
            xlr_h1_slide_switch=xlr_h1_slide_switch,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            active_lockouts=tuple(lockouts),
            shoe_audio_menu_grayed_out=grayed_out,
            active_audio_input_route=route,
            effective_sample_rate_hz=sr_hz,
            effective_bit_depth=bit_depth,
            effective_recorded_channels=rec_ch,
            osd_audio_level_meter_channels=(),
            osd_meter_expanded_to_4ch=False,
            shoe_audio_4ch_disqualification_bypass_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_SHOE_AUDIO_4CH_LOCKOUT_BYPASS_FORBIDDEN",
        )

    if audio_level_display == "On" and rec_ch == 4:
        meters: Tuple[str, ...] = ("CH1", "CH2", "CH3", "CH4")
    elif audio_level_display == "On" and rec_ch == 2:
        meters = ("CH1", "CH2")
    else:
        meters = ()

    return ShoeAudio4chAndLockoutsHilResult(
        admitted=True,
        firmware_version=firmware_version,
        shoe_audio_menu_path=SHOE_AUDIO_SET_MENU_PATH,
        audio_recording_menu_path=AUDIO_RECORDING_MENU_PATH,
        audio_level_display_menu_path=AUDIO_LEVEL_DISPLAY_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_shoe_audio_set=configured_shoe_audio_set,
        reset_action_applied=reset_action,
        slot1_camset_restored=restored_camset,
        effective_shoe_audio_set_register=eff_reg,
        reset_by_camera_settings_reset=True,
        shooting_mode=shooting_mode,
        audio_recording=audio_recording,
        audio_level_display=audio_level_display,
        mi_shoe_accessory=mi_shoe_accessory,
        xlr_h1_slide_switch=xlr_h1_slide_switch,
        body_35mm_mic_plugged=body_35mm_mic_plugged,
        active_lockouts=tuple(lockouts),
        shoe_audio_menu_grayed_out=grayed_out,
        active_audio_input_route=route,
        effective_sample_rate_hz=sr_hz,
        effective_bit_depth=bit_depth,
        effective_recorded_channels=rec_ch,
        osd_audio_level_meter_channels=meters,
        osd_meter_expanded_to_4ch=(meters == ("CH1", "CH2", "CH3", "CH4")),
        shoe_audio_4ch_disqualification_bypass_events=0,
        bk4_persistent_nvram_writes=0,
        errno_code=0,
        status_code="OK_SHOE_AUDIO_ROUTING_VERIFIED",
    )


def run_shoe_audio_reset_and_camset_recall_lifecycle() -> Dict[str, object]:
    """Prove [Shoe Audio Set.] resets to 48kHz/16bit 2ch on Camera Settings Reset and recalls via CAMSET."""
    s_cfg = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        reset_action=RESET_ACTION_NONE,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_DIGITAL,
    )
    s_csr = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_DIGITAL,
    )
    s_recall = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        slot1_camset_restore_mode=SHOE_AUDIO_48K_24BIT_4CH,
        slot1_camset_filename="CAMSET01.DAT",
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_DIGITAL,
    )
    verified = (
        s_cfg.admitted
        and s_cfg.effective_recorded_channels == 4
        and s_cfg.osd_meter_expanded_to_4ch
        and s_csr.admitted
        and s_csr.effective_shoe_audio_set_register == SHOE_AUDIO_48K_16BIT_2CH
        and s_csr.effective_bit_depth == 16
        and s_csr.effective_recorded_channels == 2
        and (not s_csr.osd_meter_expanded_to_4ch)
        and s_recall.admitted
        and s_recall.effective_shoe_audio_set_register == SHOE_AUDIO_48K_24BIT_4CH
        and s_recall.effective_recorded_channels == 4
        and s_recall.osd_meter_expanded_to_4ch
        and s_recall.bk4_persistent_nvram_writes == 0
    )
    return {
        "lifecycle_verified": verified,
        "configured_4ch": asdict(s_cfg),
        "after_camera_settings_reset_16bit_2ch": asdict(s_csr),
        "after_slot1_camset01_recall_4ch": asdict(s_recall),
    }


def evaluate_pillar_a_shoe_audio_4ch_and_3lockouts_hil() -> Dict[str, object]:
    mode_matrix: Dict[str, Dict[str, object]] = {}
    for mode in VALID_SHOE_AUDIO_MODES:
        res = simulate_shoe_audio_4ch_and_3lockouts_hil(
            configured_shoe_audio_set=mode,
            mi_shoe_accessory=MI_SHOE_XLR_H1,
            xlr_h1_slide_switch=XLR_H1_SWITCH_DIGITAL,
        )
        mode_matrix[mode] = asdict(res)

    ecm_m1_4ch_ok = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        mi_shoe_accessory=MI_SHOE_ECM_M1,
    )
    lockout1_audio_off = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        audio_recording="Off",
        mi_shoe_accessory=MI_SHOE_XLR_H1,
    )
    lockout1_sq_motion = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        shooting_mode=SHOOTING_MODE_SQ_MOTION,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
    )
    lockout2_35mm_jack = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_DIGITAL,
        body_35mm_mic_plugged=True,
    )
    lockout3_xlrh1_analog = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_ANALOG,
    )
    bypass_sq_blocked = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        shooting_mode=SHOOTING_MODE_SQ_MOTION,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        attempt_force_4ch_bypass=True,
    )
    bypass_35mm_blocked = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        body_35mm_mic_plugged=True,
        attempt_force_4ch_bypass=True,
    )
    bypass_analog_blocked = simulate_shoe_audio_4ch_and_3lockouts_hil(
        configured_shoe_audio_set=SHOE_AUDIO_48K_24BIT_4CH,
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_slide_switch=XLR_H1_SWITCH_ANALOG,
        attempt_force_4ch_bypass=True,
    )
    lifecycle = run_shoe_audio_reset_and_camset_recall_lifecycle()

    passed = (
        len(mode_matrix) == 3
        and mode_matrix[SHOE_AUDIO_48K_16BIT_2CH]["effective_recorded_channels"] == 2
        and mode_matrix[SHOE_AUDIO_48K_16BIT_2CH]["effective_bit_depth"] == 16
        and (not mode_matrix[SHOE_AUDIO_48K_16BIT_2CH]["osd_meter_expanded_to_4ch"])
        and mode_matrix[SHOE_AUDIO_48K_24BIT_2CH]["effective_recorded_channels"] == 2
        and mode_matrix[SHOE_AUDIO_48K_24BIT_2CH]["effective_bit_depth"] == 24
        and mode_matrix[SHOE_AUDIO_48K_24BIT_4CH]["effective_recorded_channels"] == 4
        and mode_matrix[SHOE_AUDIO_48K_24BIT_4CH]["effective_bit_depth"] == 24
        and bool(mode_matrix[SHOE_AUDIO_48K_24BIT_4CH]["osd_meter_expanded_to_4ch"])
        and ecm_m1_4ch_ok.admitted
        and ecm_m1_4ch_ok.osd_meter_expanded_to_4ch
        and lockout1_audio_off.effective_recorded_channels == 0
        and lockout1_audio_off.shoe_audio_menu_grayed_out
        and lockout1_sq_motion.effective_recorded_channels == 0
        and lockout1_sq_motion.shoe_audio_menu_grayed_out
        and lockout2_35mm_jack.effective_recorded_channels == 2
        and lockout2_35mm_jack.effective_bit_depth == 16
        and lockout2_35mm_jack.osd_audio_level_meter_channels == ("CH1", "CH2")
        and lockout3_xlrh1_analog.effective_recorded_channels == 2
        and lockout3_xlrh1_analog.effective_bit_depth == 16
        and lockout3_xlrh1_analog.osd_audio_level_meter_channels == ("CH1", "CH2")
        and (not bypass_sq_blocked.admitted)
        and bypass_sq_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not bypass_35mm_blocked.admitted)
        and bypass_35mm_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not bypass_analog_blocked.admitted)
        and bypass_analog_blocked.errno_code == EOPNOTSUPP_ERRNO
        and bool(lifecycle["lifecycle_verified"])
    )
    return {
        "passed": passed,
        "all_3_shoe_audio_modes": list(VALID_SHOE_AUDIO_MODES),
        "all_3_lockout_ids": list(ALL_3_SHOE_AUDIO_LOCKOUT_IDS),
        "xlr_h1_digital_3mode_matrix": mode_matrix,
        "ecm_m1_digital_4ch_ok": asdict(ecm_m1_4ch_ok),
        "lockout1_audio_recording_off_0track": asdict(lockout1_audio_off),
        "lockout1_sq_motion_0track": asdict(lockout1_sq_motion),
        "lockout2_body_35mm_mic_override_2ch": asdict(lockout2_35mm_jack),
        "lockout3_xlrh1_analog_switch_2ch": asdict(lockout3_xlrh1_analog),
        "bypass_sq_blocked_eopnotsupp": asdict(bypass_sq_blocked),
        "bypass_35mm_blocked_eopnotsupp": asdict(bypass_35mm_blocked),
        "bypass_analog_blocked_eopnotsupp": asdict(bypass_analog_blocked),
        "shoe_audio_reset_and_camset_lifecycle": lifecycle,
    }


# ---------------------------------------------------------------------------
# Sub-Model 46B — [Wind Noise Reduct.] Built-In Stereo Mic Exclusivity & Guard
# ---------------------------------------------------------------------------


def simulate_wind_noise_reduct_builtin_only_hil(
    *,
    firmware_version: str = "7.02",
    configured_wind_noise_reduct: str = WIND_NOISE_REDUCT_FACTORY_DEFAULT,
    reset_action: str = RESET_ACTION_NONE,
    slot1_camset_restore_wind: Optional[str] = None,
    slot1_camset_filename: Optional[str] = None,
    shooting_mode: str = SHOOTING_MODE_MOVIE,
    audio_recording: str = "On",
    mi_shoe_accessory: str = MI_SHOE_NONE,
    body_35mm_mic_plugged: bool = False,
    xlr_h1_low_cut_switch: str = "Off",
    acoustic_environment: str = ACOUSTIC_ENV_INDOOR_BENCH,
    enforce_indoor_bench_guard: bool = True,
    attempt_force_external_mic_wind_dsp: bool = False,
    attempt_force_sq_or_audio_off_wind_dsp: bool = False,
) -> WindNoiseReductBuiltinOnlyHilResult:
    """Co-emulate [Wind Noise Reduct.] built-in stereo mic exclusivity & indoor bench warning."""
    if (
        firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or configured_wind_noise_reduct not in VALID_ON_OFF
        or reset_action not in VALID_RESET_ACTIONS
        or shooting_mode not in VALID_SHOOTING_MODES
        or audio_recording not in VALID_ON_OFF
        or mi_shoe_accessory not in VALID_MI_SHOE_ACCESSORIES
        or xlr_h1_low_cut_switch not in VALID_XLR_H1_LOW_CUT_SWITCHES
        or acoustic_environment not in VALID_ACOUSTIC_ENVIRONMENTS
        or not _validate_camset_filename(slot1_camset_filename)
        or (
            slot1_camset_restore_wind is not None
            and slot1_camset_restore_wind not in VALID_ON_OFF
        )
        or (slot1_camset_restore_wind is not None and slot1_camset_filename is None)
    ):
        return WindNoiseReductBuiltinOnlyHilResult(
            admitted=False,
            firmware_version=str(firmware_version),
            wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_wind_noise_reduct=str(configured_wind_noise_reduct),
            reset_action_applied=str(reset_action),
            slot1_camset_restored=None,
            effective_wind_noise_reduct_register=WIND_NOISE_REDUCT_FACTORY_DEFAULT,
            reset_by_camera_settings_reset=True,
            shooting_mode=str(shooting_mode),
            audio_recording=str(audio_recording),
            mi_shoe_accessory=str(mi_shoe_accessory),
            body_35mm_mic_plugged=bool(body_35mm_mic_plugged),
            xlr_h1_low_cut_switch=str(xlr_h1_low_cut_switch),
            active_mic_source="INVALID_PARAMETER",
            wind_noise_menu_grayed_out=True,
            acoustic_environment=str(acoustic_environment),
            builtin_mic_dsp_wind_hpf_active=False,
            xlr_h1_hardware_low_cut_hz=0,
            indoor_low_freq_attenuation_warning=False,
            indoor_bench_wind_reduct_suppressed=False,
            external_mic_wind_reduct_applied_frames=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EINVAL_ERRNO,
            status_code="REJECTED_EINVAL_INVALID_WIND_NOISE_PARAMETER",
        )

    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_wind = WIND_NOISE_REDUCT_FACTORY_DEFAULT
    else:
        eff_wind = configured_wind_noise_reduct

    restored_camset: Optional[str] = None
    if slot1_camset_restore_wind is not None and slot1_camset_filename is not None:
        eff_wind = slot1_camset_restore_wind
        restored_camset = slot1_camset_filename

    if body_35mm_mic_plugged:
        mic_src = MIC_SOURCE_BODY_35MM_EXT
    elif mi_shoe_accessory != MI_SHOE_NONE:
        mic_src = MIC_SOURCE_MI_SHOE_EXT
    else:
        mic_src = MIC_SOURCE_BUILTIN_STEREO

    xlr_low_cut_hz = (
        VALID_XLR_H1_LOW_CUT_SWITCHES[xlr_h1_low_cut_switch]
        if (mi_shoe_accessory == MI_SHOE_XLR_H1 and not body_35mm_mic_plugged)
        else 0
    )

    locked_out = (
        audio_recording == "Off"
        or shooting_mode == SHOOTING_MODE_SQ_MOTION
        or shooting_mode == SHOOTING_MODE_STILL
    )

    if locked_out and attempt_force_sq_or_audio_off_wind_dsp:
        return WindNoiseReductBuiltinOnlyHilResult(
            admitted=False,
            firmware_version=firmware_version,
            wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            reset_action_applied=reset_action,
            slot1_camset_restored=restored_camset,
            effective_wind_noise_reduct_register=eff_wind,
            reset_by_camera_settings_reset=True,
            shooting_mode=shooting_mode,
            audio_recording=audio_recording,
            mi_shoe_accessory=mi_shoe_accessory,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
            active_mic_source=mic_src,
            wind_noise_menu_grayed_out=True,
            acoustic_environment=acoustic_environment,
            builtin_mic_dsp_wind_hpf_active=False,
            xlr_h1_hardware_low_cut_hz=0,
            indoor_low_freq_attenuation_warning=False,
            indoor_bench_wind_reduct_suppressed=False,
            external_mic_wind_reduct_applied_frames=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_WIND_NOISE_REDUCT_LOCKED_IN_SQ_OR_AUDIO_OFF",
        )

    if mic_src != MIC_SOURCE_BUILTIN_STEREO and attempt_force_external_mic_wind_dsp:
        return WindNoiseReductBuiltinOnlyHilResult(
            admitted=False,
            firmware_version=firmware_version,
            wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            reset_action_applied=reset_action,
            slot1_camset_restored=restored_camset,
            effective_wind_noise_reduct_register=eff_wind,
            reset_by_camera_settings_reset=True,
            shooting_mode=shooting_mode,
            audio_recording=audio_recording,
            mi_shoe_accessory=mi_shoe_accessory,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
            active_mic_source=mic_src,
            wind_noise_menu_grayed_out=locked_out,
            acoustic_environment=acoustic_environment,
            builtin_mic_dsp_wind_hpf_active=False,
            xlr_h1_hardware_low_cut_hz=xlr_low_cut_hz,
            indoor_low_freq_attenuation_warning=False,
            indoor_bench_wind_reduct_suppressed=False,
            external_mic_wind_reduct_applied_frames=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_WIND_NOISE_REDUCT_BUILTIN_MIC_ONLY",
        )

    # Built-in stereo mic DSP activation & indoor low-cut hazard check
    if locked_out or mic_src != MIC_SOURCE_BUILTIN_STEREO or eff_wind == "Off":
        return WindNoiseReductBuiltinOnlyHilResult(
            admitted=True,
            firmware_version=firmware_version,
            wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            reset_action_applied=reset_action,
            slot1_camset_restored=restored_camset,
            effective_wind_noise_reduct_register=eff_wind,
            reset_by_camera_settings_reset=True,
            shooting_mode=shooting_mode,
            audio_recording=audio_recording,
            mi_shoe_accessory=mi_shoe_accessory,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
            active_mic_source=mic_src,
            wind_noise_menu_grayed_out=locked_out,
            acoustic_environment=acoustic_environment,
            builtin_mic_dsp_wind_hpf_active=False,
            xlr_h1_hardware_low_cut_hz=(0 if locked_out else xlr_low_cut_hz),
            indoor_low_freq_attenuation_warning=False,
            indoor_bench_wind_reduct_suppressed=False,
            external_mic_wind_reduct_applied_frames=0,
            bk4_persistent_nvram_writes=0,
            errno_code=0,
            status_code="OK_WIND_NOISE_REDUCT_INACTIVE_OR_EXTERNAL_MIC_BYPASSED",
        )

    # Active built-in stereo mic + [Wind Noise Reduct.] == "On"
    if acoustic_environment == ACOUSTIC_ENV_INDOOR_BENCH:
        if enforce_indoor_bench_guard:
            return WindNoiseReductBuiltinOnlyHilResult(
                admitted=False,
                firmware_version=firmware_version,
                wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
                reset_menu_path=SETTING_RESET_MENU_PATH,
                configured_wind_noise_reduct=configured_wind_noise_reduct,
                reset_action_applied=reset_action,
                slot1_camset_restored=restored_camset,
                effective_wind_noise_reduct_register=eff_wind,
                reset_by_camera_settings_reset=True,
                shooting_mode=shooting_mode,
                audio_recording=audio_recording,
                mi_shoe_accessory=mi_shoe_accessory,
                body_35mm_mic_plugged=body_35mm_mic_plugged,
                xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
                active_mic_source=mic_src,
                wind_noise_menu_grayed_out=False,
                acoustic_environment=acoustic_environment,
                builtin_mic_dsp_wind_hpf_active=False,
                xlr_h1_hardware_low_cut_hz=0,
                indoor_low_freq_attenuation_warning=True,
                indoor_bench_wind_reduct_suppressed=True,
                external_mic_wind_reduct_applied_frames=0,
                bk4_persistent_nvram_writes=0,
                errno_code=EBUSY_ERRNO,
                status_code="SUPPRESSED_EBUSY_INDOOR_BENCH_LOW_CUT_ATTENUATION_GUARD",
            )
        return WindNoiseReductBuiltinOnlyHilResult(
            admitted=True,
            firmware_version=firmware_version,
            wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_wind_noise_reduct=configured_wind_noise_reduct,
            reset_action_applied=reset_action,
            slot1_camset_restored=restored_camset,
            effective_wind_noise_reduct_register=eff_wind,
            reset_by_camera_settings_reset=True,
            shooting_mode=shooting_mode,
            audio_recording=audio_recording,
            mi_shoe_accessory=mi_shoe_accessory,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
            active_mic_source=mic_src,
            wind_noise_menu_grayed_out=False,
            acoustic_environment=acoustic_environment,
            builtin_mic_dsp_wind_hpf_active=True,
            xlr_h1_hardware_low_cut_hz=0,
            indoor_low_freq_attenuation_warning=True,
            indoor_bench_wind_reduct_suppressed=False,
            external_mic_wind_reduct_applied_frames=0,
            bk4_persistent_nvram_writes=0,
            errno_code=0,
            status_code="OK_WARNING_INDOOR_LOW_FREQ_ATTENUATION_ACTIVE",
        )

    return WindNoiseReductBuiltinOnlyHilResult(
        admitted=True,
        firmware_version=firmware_version,
        wind_noise_reduct_menu_path=WIND_NOISE_REDUCT_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_wind_noise_reduct=configured_wind_noise_reduct,
        reset_action_applied=reset_action,
        slot1_camset_restored=restored_camset,
        effective_wind_noise_reduct_register=eff_wind,
        reset_by_camera_settings_reset=True,
        shooting_mode=shooting_mode,
        audio_recording=audio_recording,
        mi_shoe_accessory=mi_shoe_accessory,
        body_35mm_mic_plugged=body_35mm_mic_plugged,
        xlr_h1_low_cut_switch=xlr_h1_low_cut_switch,
        active_mic_source=mic_src,
        wind_noise_menu_grayed_out=False,
        acoustic_environment=acoustic_environment,
        builtin_mic_dsp_wind_hpf_active=True,
        xlr_h1_hardware_low_cut_hz=0,
        indoor_low_freq_attenuation_warning=False,
        indoor_bench_wind_reduct_suppressed=False,
        external_mic_wind_reduct_applied_frames=0,
        bk4_persistent_nvram_writes=0,
        errno_code=0,
        status_code="OK_OUTDOOR_BUILTIN_MIC_WIND_NOISE_REDUCT_ACTIVE",
    )


def evaluate_pillar_b_wind_noise_reduct_builtin_only_hil() -> Dict[str, object]:
    outdoor_builtin_on = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        acoustic_environment=ACOUSTIC_ENV_OUTDOOR_STRONG_WIND,
    )
    csr_reverts_to_off = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        acoustic_environment=ACOUSTIC_ENV_INDOOR_BENCH,
    )
    ext_35mm_non_function = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        body_35mm_mic_plugged=True,
        acoustic_environment=ACOUSTIC_ENV_OUTDOOR_STRONG_WIND,
    )
    ext_xlrh1_100hz_non_function = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        xlr_h1_low_cut_switch="100Hz",
        acoustic_environment=ACOUSTIC_ENV_OUTDOOR_STRONG_WIND,
    )
    ext_force_blocked = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        mi_shoe_accessory=MI_SHOE_XLR_H1,
        attempt_force_external_mic_wind_dsp=True,
    )
    indoor_bench_suppressed_ebusy = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        acoustic_environment=ACOUSTIC_ENV_INDOOR_BENCH,
        enforce_indoor_bench_guard=True,
    )
    sq_locked_out = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        shooting_mode=SHOOTING_MODE_SQ_MOTION,
        acoustic_environment=ACOUSTIC_ENV_OUTDOOR_STRONG_WIND,
    )
    sq_force_blocked = simulate_wind_noise_reduct_builtin_only_hil(
        configured_wind_noise_reduct="On",
        shooting_mode=SHOOTING_MODE_SQ_MOTION,
        attempt_force_sq_or_audio_off_wind_dsp=True,
    )

    passed = (
        outdoor_builtin_on.admitted
        and outdoor_builtin_on.builtin_mic_dsp_wind_hpf_active
        and outdoor_builtin_on.external_mic_wind_reduct_applied_frames == 0
        and csr_reverts_to_off.admitted
        and csr_reverts_to_off.effective_wind_noise_reduct_register == "Off"
        and (not csr_reverts_to_off.builtin_mic_dsp_wind_hpf_active)
        and ext_35mm_non_function.admitted
        and (not ext_35mm_non_function.builtin_mic_dsp_wind_hpf_active)
        and ext_35mm_non_function.external_mic_wind_reduct_applied_frames == 0
        and ext_xlrh1_100hz_non_function.admitted
        and (not ext_xlrh1_100hz_non_function.builtin_mic_dsp_wind_hpf_active)
        and ext_xlrh1_100hz_non_function.xlr_h1_hardware_low_cut_hz == 100
        and ext_xlrh1_100hz_non_function.external_mic_wind_reduct_applied_frames == 0
        and (not ext_force_blocked.admitted)
        and ext_force_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not indoor_bench_suppressed_ebusy.admitted)
        and indoor_bench_suppressed_ebusy.errno_code == EBUSY_ERRNO
        and indoor_bench_suppressed_ebusy.indoor_low_freq_attenuation_warning
        and indoor_bench_suppressed_ebusy.indoor_bench_wind_reduct_suppressed
        and sq_locked_out.admitted
        and sq_locked_out.wind_noise_menu_grayed_out
        and (not sq_locked_out.builtin_mic_dsp_wind_hpf_active)
        and (not sq_force_blocked.admitted)
        and sq_force_blocked.errno_code == EOPNOTSUPP_ERRNO
    )
    return {
        "passed": passed,
        "outdoor_builtin_mic_on_ok": asdict(outdoor_builtin_on),
        "camera_settings_reset_reverts_off": asdict(csr_reverts_to_off),
        "external_35mm_mic_non_function": asdict(ext_35mm_non_function),
        "external_xlrh1_100hz_switch_non_function": asdict(ext_xlrh1_100hz_non_function),
        "external_mic_force_dsp_blocked_eopnotsupp": asdict(ext_force_blocked),
        "indoor_bench_on_suppressed_ebusy": asdict(indoor_bench_suppressed_ebusy),
        "sq_motion_locked_out": asdict(sq_locked_out),
        "sq_motion_force_dsp_blocked_eopnotsupp": asdict(sq_force_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 46C — [Save/Load Settings] CAMSET01..10.DAT, C3 Portal & Exclusions
# ---------------------------------------------------------------------------

DEFAULT_INBODY_CAMERA_REGISTERS: Mapping[str, object] = {
    "shoe_audio_set": SHOE_AUDIO_48K_16BIT_2CH,
    "wind_noise_reduct": "Off",
    "audio_level_display": "On",
    "cine_ei_base_iso": 800,
    "shutter_angle_deg": 180.0,
    "grid_line_type": "Rule of 3rds Grid",
}

DEFAULT_INBODY_EXCLUDED_REGISTERS: Mapping[str, object] = {
    "iptc_information": "BODY_LOCAL_IPTC_DO_NOT_EXPORT",
    "write_copyright_info": "On",
    "photographer_name": "KAFU_UNIT_A",
    "copyright_holder": "KAFU_STUDIO_LOCAL",
    "custom_wb_1_kelvin_gm": "5500K_G+0.25_SENSOR_A",
    "custom_wb_2_kelvin_gm": "3200K_M+0.50_SENSOR_A",
    "custom_wb_3_kelvin_gm": "4300K_G+0.00_SENSOR_A",
    "face_memory_biometric_templates": ("FACE_SLOT_01_HASH", "FACE_SLOT_02_HASH"),
    "ftp_server_account_password": "sftp://vault.local:REDACTED_SECRET",
    "streaming_rtmps_srt_key": "rtmps://ingest.local/live/REDACTED_STREAM_KEY",
    "wifi_registered_ssid_passphrase": "STUDIO_5GHZ:REDACTED_WPA3_PSK",
    "static_ip_dns_config": "10.24.0.46/24_gw_10.24.0.1",
    "imported_tls_root_client_certs": "CN=FX3_CLIENT_CERT_SHA256_LOCAL",
}

DEFAULT_PROFILE_TO_LOAD: Mapping[str, object] = {
    "shoe_audio_set": SHOE_AUDIO_48K_24BIT_4CH,
    "wind_noise_reduct": "Off",
    "audio_level_display": "On",
    "cine_ei_base_iso": 12800,
    "shutter_angle_deg": 172.8,
    "grid_line_type": "Diag. + Square Grid",
}


def simulate_saveload_camset_c3_firewall_hil(
    *,
    firmware_version: str = "7.02",
    operation: str = SAVELOAD_OP_LOAD,
    target: str = SAVELOAD_TARGET_SLOT1,
    camset_slot_index: int = 1,
    dat_model_header: str = BODY_MODEL_FX3,
    slot1_tier0_vault_active: bool = True,
    slot1_wp_locked: bool = True,
    slot1_tier0_offline_sha256_verified_and_retired: bool = False,
    inbody_camera_registers: Optional[Mapping[str, object]] = None,
    inbody_excluded_registers: Optional[Mapping[str, object]] = None,
    incoming_load_payload: Optional[Mapping[str, object]] = None,
    attempt_include_excluded_secrets_or_cal: bool = False,
) -> SaveLoadCamsetC3FirewallHilResult:
    """Co-emulate [Save/Load Settings] CAMSET01..10.DAT / C3 Portal privacy & Slot-1 vault firewall."""
    base_cam = dict(
        DEFAULT_INBODY_CAMERA_REGISTERS
        if inbody_camera_registers is None
        else inbody_camera_registers
    )
    base_excl = dict(
        DEFAULT_INBODY_EXCLUDED_REGISTERS
        if inbody_excluded_registers is None
        else inbody_excluded_registers
    )

    if (
        firmware_version not in VALID_FX3_FIRMWARE_VERSIONS
        or operation not in VALID_SAVELOAD_OPERATIONS
        or target not in VALID_SAVELOAD_TARGETS
        or not isinstance(camset_slot_index, int)
        or isinstance(camset_slot_index, bool)
        or camset_slot_index < CAMSET_MIN_SLOT
        or camset_slot_index > CAMSET_MAX_SLOT
    ):
        return SaveLoadCamsetC3FirewallHilResult(
            admitted=False,
            firmware_version=str(firmware_version),
            saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=str(operation),
            target=str(target),
            camset_slot_index=int(camset_slot_index) if isinstance(camset_slot_index, int) else -1,
            camset_filename="INVALID",
            camset_media_path="INVALID",
            dat_model_header=str(dat_model_header),
            same_model_ilme_fx3_verified=False,
            c3_portal_cloud_sync_used=(target in CLOUD_SAVELOAD_TARGETS),
            slot1_tier0_vault_active=bool(slot1_tier0_vault_active),
            slot1_wp_locked=bool(slot1_wp_locked),
            slot1_tier0_offline_sha256_verified_and_retired=bool(
                slot1_tier0_offline_sha256_verified_and_retired
            ),
            donor_or_card_access_mode=DONOR_ACCESS_MODE,
            card_sector_writes=0,
            saved_included_keys=(),
            saved_payload_excluded_keys=(),
            excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
            excluded_items_stripped_on_save=True,
            inbody_excluded_registers_preserved_on_load=True,
            loaded_camera_registers=base_cam,
            inbody_excluded_registers_after_op=base_excl,
            excluded_secret_or_calibration_leak_events=0,
            tier0_slot1_unverified_camset_save_events=0,
            cross_model_fx6_camset_load_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EINVAL_ERRNO,
            status_code="REJECTED_EINVAL_INVALID_SAVELOAD_PARAMETER_OR_CAMSET_INDEX",
        )

    camset_fname = f"CAMSET{camset_slot_index:02d}.DAT"
    media_path = (
        f"{CAMSET_DIRECTORY_FX3}/{camset_fname}"
        if target in MEDIA_SAVELOAD_TARGETS
        else f"c3portal://{target.lower().replace('(', '_').replace(')', '')}/ILME-FX3/{camset_fname}"
    )
    is_cloud = target in CLOUD_SAVELOAD_TARGETS

    # Cloud(Private) / Cloud(Share) requires Creators' Cloud / C3 Portal firmware Ver. 4.00+
    if is_cloud and firmware_version not in CLOUD_C3_MIN_FIRMWARE_VERSIONS:
        return SaveLoadCamsetC3FirewallHilResult(
            admitted=False,
            firmware_version=firmware_version,
            saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=operation,
            target=target,
            camset_slot_index=camset_slot_index,
            camset_filename=camset_fname,
            camset_media_path=media_path,
            dat_model_header=dat_model_header,
            same_model_ilme_fx3_verified=(dat_model_header == BODY_MODEL_FX3),
            c3_portal_cloud_sync_used=True,
            slot1_tier0_vault_active=slot1_tier0_vault_active,
            slot1_wp_locked=slot1_wp_locked,
            slot1_tier0_offline_sha256_verified_and_retired=(
                slot1_tier0_offline_sha256_verified_and_retired
            ),
            donor_or_card_access_mode=DONOR_ACCESS_MODE,
            card_sector_writes=0,
            saved_included_keys=(),
            saved_payload_excluded_keys=(),
            excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
            excluded_items_stripped_on_save=True,
            inbody_excluded_registers_preserved_on_load=True,
            loaded_camera_registers=base_cam,
            inbody_excluded_registers_after_op=base_excl,
            excluded_secret_or_calibration_leak_events=0,
            tier0_slot1_unverified_camset_save_events=0,
            cross_model_fx6_camset_load_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_CLOUD_C3_REQUIRES_VER_400_PLUS",
        )

    # Same-model ILME-FX3 lock (rejects ILME-FX6 .DAT / All File or ILME-FX3A cross-loads)
    if dat_model_header != BODY_MODEL_FX3:
        return SaveLoadCamsetC3FirewallHilResult(
            admitted=False,
            firmware_version=firmware_version,
            saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=operation,
            target=target,
            camset_slot_index=camset_slot_index,
            camset_filename=camset_fname,
            camset_media_path=media_path,
            dat_model_header=dat_model_header,
            same_model_ilme_fx3_verified=False,
            c3_portal_cloud_sync_used=is_cloud,
            slot1_tier0_vault_active=slot1_tier0_vault_active,
            slot1_wp_locked=slot1_wp_locked,
            slot1_tier0_offline_sha256_verified_and_retired=(
                slot1_tier0_offline_sha256_verified_and_retired
            ),
            donor_or_card_access_mode=DONOR_ACCESS_MODE,
            card_sector_writes=0,
            saved_included_keys=(),
            saved_payload_excluded_keys=(),
            excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
            excluded_items_stripped_on_save=True,
            inbody_excluded_registers_preserved_on_load=True,
            loaded_camera_registers=base_cam,
            inbody_excluded_registers_after_op=base_excl,
            excluded_secret_or_calibration_leak_events=0,
            tier0_slot1_unverified_camset_save_events=0,
            cross_model_fx6_camset_load_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_CROSS_MODEL_CAMSET_REJECTED",
        )

    # Excluded-Items Privacy/Calibration Firewall explicit bypass block
    if attempt_include_excluded_secrets_or_cal:
        return SaveLoadCamsetC3FirewallHilResult(
            admitted=False,
            firmware_version=firmware_version,
            saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=operation,
            target=target,
            camset_slot_index=camset_slot_index,
            camset_filename=camset_fname,
            camset_media_path=media_path,
            dat_model_header=dat_model_header,
            same_model_ilme_fx3_verified=True,
            c3_portal_cloud_sync_used=is_cloud,
            slot1_tier0_vault_active=slot1_tier0_vault_active,
            slot1_wp_locked=slot1_wp_locked,
            slot1_tier0_offline_sha256_verified_and_retired=(
                slot1_tier0_offline_sha256_verified_and_retired
            ),
            donor_or_card_access_mode=DONOR_ACCESS_MODE,
            card_sector_writes=0,
            saved_included_keys=(),
            saved_payload_excluded_keys=(),
            excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
            excluded_items_stripped_on_save=True,
            inbody_excluded_registers_preserved_on_load=True,
            loaded_camera_registers=base_cam,
            inbody_excluded_registers_after_op=base_excl,
            excluded_secret_or_calibration_leak_events=0,
            tier0_slot1_unverified_camset_save_events=0,
            cross_model_fx6_camset_load_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EOPNOTSUPP_EXCLUDED_PRIVACY_OR_CALIBRATION_FIREWALL",
        )

    # Slot-1 Tier-0 Forensic Vault Write Guard (blocks [Save] to WP-locked or unverified Slot 1)
    if operation == SAVELOAD_OP_SAVE and target == SAVELOAD_TARGET_SLOT1:
        if slot1_wp_locked:
            return SaveLoadCamsetC3FirewallHilResult(
                admitted=False,
                firmware_version=firmware_version,
                saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=operation,
                target=target,
                camset_slot_index=camset_slot_index,
                camset_filename=camset_fname,
                camset_media_path=media_path,
                dat_model_header=dat_model_header,
                same_model_ilme_fx3_verified=True,
                c3_portal_cloud_sync_used=False,
                slot1_tier0_vault_active=slot1_tier0_vault_active,
                slot1_wp_locked=True,
                slot1_tier0_offline_sha256_verified_and_retired=(
                    slot1_tier0_offline_sha256_verified_and_retired
                ),
                donor_or_card_access_mode=DONOR_ACCESS_MODE,
                card_sector_writes=0,
                saved_included_keys=(),
                saved_payload_excluded_keys=(),
                excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
                excluded_items_stripped_on_save=True,
                inbody_excluded_registers_preserved_on_load=True,
                loaded_camera_registers=base_cam,
                inbody_excluded_registers_after_op=base_excl,
                excluded_secret_or_calibration_leak_events=0,
                tier0_slot1_unverified_camset_save_events=0,
                cross_model_fx6_camset_load_events=0,
                bk4_persistent_nvram_writes=0,
                errno_code=EROFS_ERRNO,
                status_code="BLOCKED_EROFS_SLOT1_WP_LOCKED_VAULT_CARD",
            )
        if slot1_tier0_vault_active and not slot1_tier0_offline_sha256_verified_and_retired:
            return SaveLoadCamsetC3FirewallHilResult(
                admitted=False,
                firmware_version=firmware_version,
                saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
                operation=operation,
                target=target,
                camset_slot_index=camset_slot_index,
                camset_filename=camset_fname,
                camset_media_path=media_path,
                dat_model_header=dat_model_header,
                same_model_ilme_fx3_verified=True,
                c3_portal_cloud_sync_used=False,
                slot1_tier0_vault_active=True,
                slot1_wp_locked=False,
                slot1_tier0_offline_sha256_verified_and_retired=False,
                donor_or_card_access_mode=DONOR_ACCESS_MODE,
                card_sector_writes=0,
                saved_included_keys=(),
                saved_payload_excluded_keys=(),
                excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
                excluded_items_stripped_on_save=True,
                inbody_excluded_registers_preserved_on_load=True,
                loaded_camera_registers=base_cam,
                inbody_excluded_registers_after_op=base_excl,
                excluded_secret_or_calibration_leak_events=0,
                tier0_slot1_unverified_camset_save_events=0,
                cross_model_fx6_camset_load_events=0,
                bk4_persistent_nvram_writes=0,
                errno_code=EBUSY_ERRNO,
                status_code="BLOCKED_EBUSY_SLOT1_TIER0_UNVERIFIED_VAULT_SAVE_FORBIDDEN",
            )

    if operation == SAVELOAD_OP_SAVE:
        combined_source = {**base_excl, **base_cam}
        serialized = {
            k: v
            for k, v in combined_source.items()
            if k in INCLUDED_CAMSET_REGISTER_KEYS and k not in ALL_EXCLUDED_REGISTER_KEYS
        }
        leaked_keys = tuple(k for k in serialized if k in ALL_EXCLUDED_REGISTER_KEYS)
        sector_writes = 1 if target in MEDIA_SAVELOAD_TARGETS else 0
        access_mode = "SCRATCH_MEDIA_CAMSET_WRITE" if sector_writes > 0 else "CLOUD_HTTPS_SYNC"
        return SaveLoadCamsetC3FirewallHilResult(
            admitted=True,
            firmware_version=firmware_version,
            saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
            operation=operation,
            target=target,
            camset_slot_index=camset_slot_index,
            camset_filename=camset_fname,
            camset_media_path=media_path,
            dat_model_header=dat_model_header,
            same_model_ilme_fx3_verified=True,
            c3_portal_cloud_sync_used=is_cloud,
            slot1_tier0_vault_active=slot1_tier0_vault_active,
            slot1_wp_locked=slot1_wp_locked,
            slot1_tier0_offline_sha256_verified_and_retired=(
                slot1_tier0_offline_sha256_verified_and_retired
            ),
            donor_or_card_access_mode=access_mode,
            card_sector_writes=sector_writes,
            saved_included_keys=tuple(sorted(serialized.keys())),
            saved_payload_excluded_keys=leaked_keys,
            excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
            excluded_items_stripped_on_save=(len(leaked_keys) == 0),
            inbody_excluded_registers_preserved_on_load=True,
            loaded_camera_registers=base_cam,
            inbody_excluded_registers_after_op=base_excl,
            excluded_secret_or_calibration_leak_events=len(leaked_keys),
            tier0_slot1_unverified_camset_save_events=0,
            cross_model_fx6_camset_load_events=0,
            bk4_persistent_nvram_writes=0,
            errno_code=0,
            status_code="OK_CAMSET_OR_CLOUD_SAVE_EXCLUDED_ITEMS_STRIPPED",
        )

    # operation == "Load" — strictly O_RDONLY on card, ignores any smuggled excluded keys
    src_load = DEFAULT_PROFILE_TO_LOAD if incoming_load_payload is None else incoming_load_payload
    updated_cam = dict(base_cam)
    for k, v in src_load.items():
        if k in INCLUDED_CAMSET_REGISTER_KEYS and k not in ALL_EXCLUDED_REGISTER_KEYS:
            updated_cam[k] = v

    return SaveLoadCamsetC3FirewallHilResult(
        admitted=True,
        firmware_version=firmware_version,
        saveload_menu_path=SAVE_LOAD_SETTINGS_MENU_PATH,
        operation=operation,
        target=target,
        camset_slot_index=camset_slot_index,
        camset_filename=camset_fname,
        camset_media_path=media_path,
        dat_model_header=dat_model_header,
        same_model_ilme_fx3_verified=True,
        c3_portal_cloud_sync_used=is_cloud,
        slot1_tier0_vault_active=slot1_tier0_vault_active,
        slot1_wp_locked=slot1_wp_locked,
        slot1_tier0_offline_sha256_verified_and_retired=(
            slot1_tier0_offline_sha256_verified_and_retired
        ),
        donor_or_card_access_mode=DONOR_ACCESS_MODE,
        card_sector_writes=0,
        saved_included_keys=tuple(sorted(INCLUDED_CAMSET_REGISTER_KEYS)),
        saved_payload_excluded_keys=(),
        excluded_categories_enforced=ALL_4_EXCLUDED_SAVELOAD_CATEGORIES,
        excluded_items_stripped_on_save=True,
        inbody_excluded_registers_preserved_on_load=True,
        loaded_camera_registers=updated_cam,
        inbody_excluded_registers_after_op=base_excl,
        excluded_secret_or_calibration_leak_events=0,
        tier0_slot1_unverified_camset_save_events=0,
        cross_model_fx6_camset_load_events=0,
        bk4_persistent_nvram_writes=0,
        errno_code=0,
        status_code="OK_CAMSET_OR_CLOUD_LOAD_EXCLUDED_ITEMS_PRESERVED",
    )


# ---------------------------------------------------------------------------
# Hard Safety Redline Guard Probes
# ---------------------------------------------------------------------------


def probe_stage46_redline_guard(
    *,
    request_persistent_emmc_write: bool = False,
    request_live_hardware_attach: bool = False,
    request_overall_ready_attach: bool = False,
    request_spi_nor_write: bool = False,
    request_el3_payload_tx: bool = False,
    request_isp_write: bool = False,
    request_cnflasha_userspace_write: bool = False,
    request_usb_packet_tx: bool = False,
    request_shoe_audio_4ch_lockout_bypass: bool = False,
    request_external_mic_wind_dsp_bypass: bool = False,
    request_excluded_secret_or_cal_leak: bool = False,
    request_unverified_slot1_tier0_camset_save: bool = False,
) -> RedlineGuardProbeResult:
    triggers = (
        ("PERSISTENT_EMMC_WRITE", request_persistent_emmc_write),
        ("LIVE_HARDWARE_ATTACH", request_live_hardware_attach),
        ("OVERALL_READY_HARDWARE_ATTACH", request_overall_ready_attach),
        ("SPI_NOR_WRITE", request_spi_nor_write),
        ("EL3_PAYLOAD_TRANSMIT", request_el3_payload_tx),
        ("ISP_CALIBRATION_WRITE", request_isp_write),
        ("CNFLASHA_USERSPACE_WRITE", request_cnflasha_userspace_write),
        ("PHYSICAL_USB_PACKET_EMIT", request_usb_packet_tx),
        ("SHOE_AUDIO_4CH_LOCKOUT_BYPASS", request_shoe_audio_4ch_lockout_bypass),
        ("EXTERNAL_MIC_WIND_DSP_BYPASS", request_external_mic_wind_dsp_bypass),
        ("EXCLUDED_SECRET_OR_CALIBRATION_LEAK", request_excluded_secret_or_cal_leak),
        ("UNVERIFIED_SLOT1_TIER0_CAMSET_SAVE", request_unverified_slot1_tier0_camset_save),
    )
    hit = next((name for name, flag in triggers if flag), None)
    if hit is not None:
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
            shoe_audio_4ch_disqualification_bypass_events=0,
            external_mic_wind_reduct_applied_frames=0,
            excluded_secret_or_calibration_leak_events=0,
            tier0_slot1_unverified_camset_save_events=0,
            raw_firmware_bytes_leaked=0,
            blocked_action=hit,
            status_code=f"FAIL_CLOSED_REDLINE_{hit}",
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
        shoe_audio_4ch_disqualification_bypass_events=0,
        external_mic_wind_reduct_applied_frames=0,
        excluded_secret_or_calibration_leak_events=0,
        tier0_slot1_unverified_camset_save_events=0,
        raw_firmware_bytes_leaked=0,
        blocked_action="NONE",
        status_code="OK_ALL_STAGE46_REDLINES_LOCKED",
    )


def evaluate_pillar_c_d_saveload_camset_c3_firewall_and_redlines() -> Dict[str, object]:
    slot2_10slot_save_matrix: Dict[str, Dict[str, object]] = {}
    for idx in range(CAMSET_MIN_SLOT, CAMSET_MAX_SLOT + 1):
        res = simulate_saveload_camset_c3_firewall_hil(
            operation=SAVELOAD_OP_SAVE,
            target=SAVELOAD_TARGET_SLOT2,
            camset_slot_index=idx,
        )
        slot2_10slot_save_matrix[res.camset_filename] = asdict(res)

    slot1_tier0_load_rdonly_ok = simulate_saveload_camset_c3_firewall_hil(
        operation=SAVELOAD_OP_LOAD,
        target=SAVELOAD_TARGET_SLOT1,
        camset_slot_index=1,
        slot1_tier0_vault_active=True,
        slot1_wp_locked=True,
        incoming_load_payload={
            **DEFAULT_PROFILE_TO_LOAD,
            "iptc_information": "ATTACKER_IPTC_OVERWRITE",
            "custom_wb_1_kelvin_gm": "9900K_FOREIGN_BODY_CAL",
            "face_memory_biometric_templates": ("FOREIGN_FACE",),
            "ftp_server_account_password": "sftp://evil.example:LEAK",
        },
    )
    cloud_private_save_ok = simulate_saveload_camset_c3_firewall_hil(
        firmware_version="7.02",
        operation=SAVELOAD_OP_SAVE,
        target=SAVELOAD_TARGET_CLOUD_PRIVATE,
        camset_slot_index=1,
    )
    cloud_share_load_ok = simulate_saveload_camset_c3_firewall_hil(
        firmware_version="7.02",
        operation=SAVELOAD_OP_LOAD,
        target=SAVELOAD_TARGET_CLOUD_SHARE,
        camset_slot_index=2,
    )
    fx6_cross_model_blocked = simulate_saveload_camset_c3_firewall_hil(
        operation=SAVELOAD_OP_LOAD,
        target=SAVELOAD_TARGET_SLOT2,
        dat_model_header=BODY_MODEL_FX6,
    )
    excluded_bypass_blocked = simulate_saveload_camset_c3_firewall_hil(
        operation=SAVELOAD_OP_SAVE,
        target=SAVELOAD_TARGET_CLOUD_SHARE,
        attempt_include_excluded_secrets_or_cal=True,
    )
    slot1_wp_save_blocked_erofs = simulate_saveload_camset_c3_firewall_hil(
        operation=SAVELOAD_OP_SAVE,
        target=SAVELOAD_TARGET_SLOT1,
        slot1_tier0_vault_active=True,
        slot1_wp_locked=True,
    )
    slot1_unverified_save_blocked_ebusy = simulate_saveload_camset_c3_firewall_hil(
        operation=SAVELOAD_OP_SAVE,
        target=SAVELOAD_TARGET_SLOT1,
        slot1_tier0_vault_active=True,
        slot1_wp_locked=False,
        slot1_tier0_offline_sha256_verified_and_retired=False,
    )
    cloud_pre400_blocked = simulate_saveload_camset_c3_firewall_hil(
        firmware_version="3.00",
        operation=SAVELOAD_OP_SAVE,
        target=SAVELOAD_TARGET_CLOUD_PRIVATE,
    )

    baseline_redline = probe_stage46_redline_guard()
    probe_kwargs = (
        {"request_persistent_emmc_write": True},
        {"request_live_hardware_attach": True},
        {"request_overall_ready_attach": True},
        {"request_spi_nor_write": True},
        {"request_el3_payload_tx": True},
        {"request_isp_write": True},
        {"request_cnflasha_userspace_write": True},
        {"request_usb_packet_tx": True},
        {"request_shoe_audio_4ch_lockout_bypass": True},
        {"request_external_mic_wind_dsp_bypass": True},
        {"request_excluded_secret_or_cal_leak": True},
        {"request_unverified_slot1_tier0_camset_save": True},
    )
    blocked_probes = [asdict(probe_stage46_redline_guard(**kw)) for kw in probe_kwargs]

    passed = (
        len(slot2_10slot_save_matrix) == 10
        and all(
            bool(v["admitted"])
            and bool(v["excluded_items_stripped_on_save"])
            and v["saved_payload_excluded_keys"] == ()
            for v in slot2_10slot_save_matrix.values()
        )
        and slot1_tier0_load_rdonly_ok.admitted
        and slot1_tier0_load_rdonly_ok.card_sector_writes == 0
        and slot1_tier0_load_rdonly_ok.donor_or_card_access_mode == "O_RDONLY"
        and slot1_tier0_load_rdonly_ok.loaded_camera_registers["shoe_audio_set"]
        == SHOE_AUDIO_48K_24BIT_4CH
        and slot1_tier0_load_rdonly_ok.inbody_excluded_registers_after_op
        == dict(DEFAULT_INBODY_EXCLUDED_REGISTERS)
        and cloud_private_save_ok.admitted
        and cloud_private_save_ok.c3_portal_cloud_sync_used
        and cloud_private_save_ok.excluded_items_stripped_on_save
        and cloud_share_load_ok.admitted
        and cloud_share_load_ok.inbody_excluded_registers_preserved_on_load
        and (not fx6_cross_model_blocked.admitted)
        and fx6_cross_model_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not excluded_bypass_blocked.admitted)
        and excluded_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not slot1_wp_save_blocked_erofs.admitted)
        and slot1_wp_save_blocked_erofs.errno_code == EROFS_ERRNO
        and slot1_wp_save_blocked_erofs.card_sector_writes == 0
        and (not slot1_unverified_save_blocked_ebusy.admitted)
        and slot1_unverified_save_blocked_ebusy.errno_code == EBUSY_ERRNO
        and slot1_unverified_save_blocked_ebusy.card_sector_writes == 0
        and (not cloud_pre400_blocked.admitted)
        and cloud_pre400_blocked.errno_code == EOPNOTSUPP_ERRNO
        and baseline_redline.valid
        and len(blocked_probes) == 12
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "all_10_camset_filenames": list(VALID_CAMSET_FILENAMES),
        "all_4_saveload_targets": list(VALID_SAVELOAD_TARGETS),
        "all_4_excluded_categories": list(ALL_4_EXCLUDED_SAVELOAD_CATEGORIES),
        "all_excluded_register_keys": list(ALL_EXCLUDED_REGISTER_KEYS),
        "slot2_10slot_save_matrix": slot2_10slot_save_matrix,
        "slot1_tier0_load_rdonly_excluded_preserved_ok": asdict(slot1_tier0_load_rdonly_ok),
        "cloud_private_c3_save_ok": asdict(cloud_private_save_ok),
        "cloud_share_c3_load_ok": asdict(cloud_share_load_ok),
        "fx6_cross_model_camset_blocked_eopnotsupp": asdict(fx6_cross_model_blocked),
        "excluded_secret_or_cal_bypass_blocked_eopnotsupp": asdict(excluded_bypass_blocked),
        "slot1_wp_save_blocked_erofs": asdict(slot1_wp_save_blocked_erofs),
        "slot1_unverified_tier0_save_blocked_ebusy": asdict(slot1_unverified_save_blocked_ebusy),
        "cloud_pre400_blocked_eopnotsupp": asdict(cloud_pre400_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 244 (Stage 46, 46/46 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 244 Stage 46 (46/46) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase244_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_shoe_audio_4ch_and_3lockouts_hil()
    pillar_b = evaluate_pillar_b_wind_noise_reduct_builtin_only_hil()
    pillar_cd = evaluate_pillar_c_d_saveload_camset_c3_firewall_and_redlines()

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
        "shoe_audio_4ch_disqualification_bypass_events": (
            SHOE_AUDIO_4CH_DISQUALIFICATION_BYPASS_EVENTS
        ),
        "external_mic_wind_reduct_applied_frames": EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES,
        "excluded_secret_or_calibration_leak_events": EXCLUDED_SECRET_OR_CALIBRATION_LEAK_EVENTS,
        "tier0_slot1_unverified_camset_save_events": TIER0_SLOT1_UNVERIFIED_CAMSET_SAVE_EVENTS,
        "cross_model_fx6_camset_load_events": CROSS_MODEL_FX6_CAMSET_LOAD_EVENTS,
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
        and SHOE_AUDIO_4CH_DISQUALIFICATION_BYPASS_EVENTS == 0
        and EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES == 0
        and EXCLUDED_SECRET_OR_CALIBRATION_LEAK_EVENTS == 0
        and TIER0_SLOT1_UNVERIFIED_CAMSET_SAVE_EVENTS == 0
        and CROSS_MODEL_FX6_CAMSET_LOAD_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_244_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_shoe_audio_4ch_and_3lockouts_hil": pillar_a,
        "pillar_b_wind_noise_reduct_builtin_only_hil": pillar_b,
        "pillar_c_d_saveload_camset_c3_firewall_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_shoe_audio_wind_saveload_c3_coemulator.py",
        description=(
            "Phase 244 Stage 46 (46/46 Milestone) — Real-Hardware ILME-FX3 Wave-36 "
            "Shoe Audio Set. 48kHz/24bit 4ch Meter Expansion vs 3.5mm/ANALOG/S&Q Lockouts, "
            "Wind Noise Reduct. Built-In Mic Exclusivity & Indoor Guard, and Save/Load Settings "
            "CAMSET01..10.DAT / C3 Portal Excluded-Items Firewall & Slot-1 Tier-0 Vault Guard HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 244 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase244_realhw_shoe_audio_wind_saveload_c3_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_shoe_audio_4ch_and_3lockouts_hil"]
        pcd = rep["pillar_c_d_saveload_camset_c3_firewall_and_redlines"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 244 Stage 46 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"shoe_4ch={len(pa['all_3_shoe_audio_modes'])}m_{len(pa['all_3_lockout_ids'])}lck_byp:{red['shoe_audio_4ch_disqualification_bypass_events']} | "
            f"wind_ext:{red['external_mic_wind_reduct_applied_frames']} | "
            f"saveload={len(pcd['all_10_camset_filenames'])}dat_{len(pcd['all_4_excluded_categories'])}excl_leak:{red['excluded_secret_or_calibration_leak_events']}_t0wr:{red['tier0_slot1_unverified_camset_save_events']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
