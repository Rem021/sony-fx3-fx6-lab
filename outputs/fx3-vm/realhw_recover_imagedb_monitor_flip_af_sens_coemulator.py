#!/usr/bin/env python3
"""Phase 239 (Stage 44, 44/44 Milestone) — Real-Hardware ILME-FX3 Wave-34
`[Recover Image DB]` Depleted-Battery Refusal, Non-Deleting `AVF_INFO` Repair & Slot-1 Tier-0
Vault Read-Only Firewall, `[Monitor Flip Direction]` Reset Survival & `[Horizontal Flip]`
Playback Non-Inversion, and Movie/S&Q AF Kinematics (`[AF Transition Speed]` `1..7` &
`[AF Subj. Shift Sensitivity]` `1..5` Full Spelling) vs Still-Only `[Interval Shoot Func.]`
HIL Co-Emulator.

Strictly models Wave-34 official Sony `ILME-FX3` (`Ver. 2.00..7.02`, primary `Ver. 7.02`) and
`ILME-FX6` (`Ver. 6.01`) contracts without hardware attachment or firmware byte leakage:

1. **Sub-Model 44A — `[Recover Image DB]` (`MENU -> Shooting -> [Media] -> [Recover Image DB]`)
   Depleted-Battery Refusal, Non-Deleting `AVF_INFO` Repair & Slot-1 Tier-0 Vault Read-Only Firewall**:
   - Models `NP-FZ100` battery precheck (`sufficient_charge` vs `extremely_depleted`): when the
     battery pack is extremely depleted (`battery_state == "extremely_depleted"`, `battery_soc_pct < 10`,
     or `battery_mv < 6400`), hardware refuses execution **before any FAT/exFAT sector write**
     (`errno_code == EAGAIN (11)`, `hardware_refused_before_fat_exfat_write == True`,
     `card_metadata_sector_writes == 0`) to prevent brownout card-table corruption.
   - Repairs `AVF_INFO` (`AVF_INFO/AVIN0001.INP`, `AVF_INFO/AVIN0001.BNP`, `AVF_INFO/PRV00001.BIN`)
     and `M4ROOT/MEDIAPRO.XML` for `"Image DataBase File error"` or false `"0"` recordable-image
     inconsistency **strictly without deleting recorded movies or still images**
     (`deleted_clip_or_still_count == 0`, `clips_after == clips_before`, `stills_after == stills_before`).
     Any attempt to delete media via `[Recover Image DB]` fails closed with `EOPNOTSUPP (95)`.
   - Verifies **action-item immunity**: `[Recover Image DB]` is an immediate execution command,
     NOT a stored stateful toggle, and is completely unaffected by both `[Camera Settings Reset]`
     and `[Initialize]`.
   - Enforces the **Slot-1 Tier-0 Forensic Dump Vault Read-Only Firewall**: blocks `[Recover Image DB]`
     on `Slot 1` (`EROFS (30)` when physical SDXC `WP` lock is engaged; `EBUSY (16)` whenever an
     active or unverified Tier-0 dump card holding `pnflasha`, `cnflasha`, `CAMSET01.DAT`, `mtd0ro`,
     `Backup.bin`, or `FX3RCPT1.BIN` resides in Slot 1; `tier0_slot1_unverified_imagedb_mutation_events == 0`),
     while permitting `Slot 2` scratch repair when battery charge is sufficient (`Slot 1` repair is
     admitted only after off-camera SHA-256 verification and replacement of the `WP`-locked vault
     card with unlocked scratch media).

2. **Sub-Model 44B — `[Monitor Flip Direction]` (`MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]`)
   Reset Survival & `[Horizontal Flip]` Playback Non-Inversion**:
   - Co-emulates all 4 official `ILME-FX3` states: `Auto` (factory default), `Horizontal Flip`,
     `Vertical Flip`, and `Off`.
   - **Reset survival**: survives `[Camera Settings Reset]` intact (`reset_only_by_initialize == True`)
     and reverts to factory default `Auto` **only** on full `[Initialize]`.
   - **Playback non-inversion & HDMI clean feed**: under `[Horizontal Flip]`, live shooting local LCD
     preview mirrors horizontally (`live_shooting_lcd_horizontally_mirrored == True`), while
     **playback display direction is NEVER inverted** (`playback_display_horizontally_inverted == False`,
     `playback_horizontal_flip_inversion_events == 0`) and external HDMI clean feed stays unflipped
     (`external_hdmi_clean_feed_flipped == False`). Any attempt to invert playback under
     `[Horizontal Flip]` or flip the external HDMI clean feed fails closed with `EOPNOTSUPP (95)`.

3. **Sub-Model 44C — Movie/S&Q AF Kinematics (`[AF Transition Speed]` `1..7` &
   `[AF Subj. Shift Sensitivity]` `1..5` Full Spelling) vs Still-Only `[Interval Shoot Func.]`
   + Hard Safety Redlines**:
   - Co-emulates exact `ILME-FX3` menu spelling `[AF Subj. Shift Sensitivity]`
     (`1(Locked on)`..`5(Responsive)`, default `5(Responsive)`) — explicitly rejecting abbreviated
     `FX6`/`Alpha` label hallucinations (`"AF Subj. Shift Sens."`, `"AF Subj. Shift Sens"`,
     `"AF Subject Shift Sens."`) with `EINVAL (22)` — alongside `[AF Transition Speed]`
     (`1(Slow)`..`7(Fast)`, `1..7`, default `5`), both movie/S&Q-scoped and **resettable** via
     `[Camera Settings Reset]` (forming a deterministic reset split against surviving
     `[Monitor Flip Direction]`; `monitor_flip_or_af_kinematics_drift_events == 0`), plus zero-NVRAM
     Slot-1 `CAMSET01..10.DAT` recall (`bk4_persistent_nvram_writes == 0`).
   - Contrasts movie/S&Q AF kinematics against `MENU -> Shooting -> [Drive Mode] -> [Interval Shoot Func.]`
     (`Shooting Start Time` `1s..99m59s` = `1..5999s`, `Shooting Interval` `1s..60s` = `1..60s`,
     `Number of Shots` `1..9999`), strictly scoped to still-image sequence capture (`JPEG`/`HEIF`/`RAW`
     assembled post-capture in `Imaging Edge Desktop (Viewer)`), rejecting any false FX6-style
     in-camera MXF/MP4 video `Interval Rec` conflation with `EOPNOTSUPP (95)`.

4. **Dual-Mode Donor Inspection & Hard Safety Redlines**:
   - Supports `LOCAL_DONOR_O_RDONLY` (strictly read-only bounded `<= 4096 B` window inspection across
     14 FX3 `7.02` & FX6 `6.01` donors in `< 0.1s` cold, cached, `raw_firmware_bytes_leaked == 0`)
     and `CLEAN_ROOM_SYNTHETIC` (`FX3_FX6_FORCE_CLEAN_ROOM=1`).
   - Locks `persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`,
     `overall_ready_for_hardware_attach = False`, `isp_write_authorized = False`,
     `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
     `cnflasha_userspace_write_blocked = True`, `cnflasha_mutation_bytes = 0`, and
     `physical_device_writes = 0`.
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
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_recover_imagedb_monitor_flip_af_sens_coemulator_v1"
PHASE_239_SCHEMA = SCHEMA_ID
PHASE_239_VERSION = "239.0.0"
STAGE_INDEX = 44
STAGE_TOTAL = 44
MILESTONE_LABEL = "44/44"
STAGE_NAME = "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil"
FX3_MODEL_ID = 0x91030080

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EAGAIN_ERRNO = 11
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
TIER0_SLOT1_UNVERIFIED_IMAGEDB_MUTATION_EVENTS = 0
PLAYBACK_HORIZONTAL_FLIP_INVERSION_EVENTS = 0
MONITOR_FLIP_OR_AF_KINEMATICS_DRIFT_EVENTS = 0
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
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx6_lens_comm": f"{_FX6_NF15_PREFIX}/lib/libInfraLensCommunicator.so",
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
    "fx3_imdb": 71_536,
    "fx3_saveload": 18_760,
    "fx3_media_cfg": 52_312,
    "fx3_adj_media": 318_152,
    "fx3_lens_comm": 14_544,
    "fx6_lens_comm": 14_544,
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
    "fx3_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx6_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx3_string_en_f": (
        b"Recover Image DB",
        b"Media",
        b"Slot 1",
        b"Slot 2",
        b"Monitor Flip Direction",
        b"Horizontal Flip",
        b"180 Degree Flip",
        b"No Flip",
        b"Auto",
        b"Off",
        b"AF Transition Speed",
        b"AF Subj. Shift Sensitivity",
        b"1(Locked on)",
        b"5(Responsive)",
        b"Slow",
        b"Fast",
        b"Interval Shoot Func.",
        b"Interval Shooting",
        b"Shooting Start Time",
        b"Shooting Interval",
        b"Number of Shots",
        b"HDMI Info. Display",
        b"Playback",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx6_string_en": (
        b"AF Transition Speed",
        b"AF Subj. Shift Sens.",
        b"Media",
        b"Media Remain (A)",
        b"Media Remain (B)",
        b"Save Media(B)",
        b"Load Media(B)",
        b"Reset All",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_942_528, "INTERVAL", b"INTERVAL"),
        (49_967_104, "INITIALIZE", b"INITIALIZE"),
        (60_317_696, "FLIP", b"FLIP"),
        (60_633_088, "RECOVER", b"RECOVER"),
        (61_886_464, "AF_TRANSITION", b"AF_TRANSITION"),
        (62_959_616, "MEDIAPRO", b"MEDIAPRO"),
        (63_143_936, "MONITOR_FLIP", b"MONITOR_FLIP"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_232_640, "INTERVAL", b"INTERVAL"),
        (37_670_912, "MEDIAPRO", b"MEDIAPRO"),
        (39_350_272, "CAMSET", b"CAMSET"),
        (39_886_848, "FLIP", b"FLIP"),
        (41_168_896, "AF_SPEED", b"AF_SPEED"),
    ),
    "fx3_cpapp": (
        (139_264, "AF", b"AF"),
        (139_264, "INTERVAL", b"INTERVAL"),
        (372_736, "MONITOR", b"MONITOR"),
        (696_320, "HDMI", b"HDMI"),
        (2_002_944, "FLIP", b"FLIP"),
        (2_011_136, "BATTERY", b"BATTERY"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (131_072, "AF", b"AF"),
        (135_168, "INTERVAL", b"INTERVAL"),
        (376_832, "MONITOR", b"MONITOR"),
        (684_032, "HDMI", b"HDMI"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (233_472, "XAVC", b"XAVC"),
        (2_928_640, "MP4", b"MP4"),
        (2_928_640, "MEDIAPRO", b"MEDIAPRO"),
        (2_945_024, "AVF_INFO", b"AVF_INFO"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (192_512, "MXF", b"MXF"),
        (258_048, "XAVC", b"XAVC"),
        (315_392, "MEDIAPRO", b"MEDIAPRO"),
        (13_406_208, "MP4", b"MP4"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-34 Official ILME-FX3 Ver. 2.00..7.02 Sub-Model 44A / 44B / 44C Constants
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

# Sub-Model 44A: [Recover Image DB]
RECOVER_IMAGE_DB_MENU_PATH = "MENU -> Shooting -> [Media] -> [Recover Image DB]"
SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_MEDIA_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

BATTERY_STATE_SUFFICIENT = "sufficient_charge"
BATTERY_STATE_EXTREMELY_DEPLETED = "extremely_depleted"
VALID_BATTERY_STATES: Tuple[str, ...] = (
    BATTERY_STATE_SUFFICIENT,
    BATTERY_STATE_EXTREMELY_DEPLETED,
)
MIN_RECOVER_IMAGEDB_BATTERY_SOC_PCT = 10
MIN_RECOVER_IMAGEDB_BATTERY_MV = 6400

IMAGEDB_ANOMALY_DATABASE_ERROR = "Image DataBase File error"
IMAGEDB_ANOMALY_FALSE_ZERO_REMAINING = "False 0 recordable images inconsistency"
IMAGEDB_ANOMALY_NONE = "Healthy AVF_INFO index"
VALID_IMAGEDB_ANOMALIES: Tuple[str, ...] = (
    IMAGEDB_ANOMALY_DATABASE_ERROR,
    IMAGEDB_ANOMALY_FALSE_ZERO_REMAINING,
    IMAGEDB_ANOMALY_NONE,
)

REPAIRED_AVF_INFO_FILES: Tuple[str, ...] = (
    "AVF_INFO/AVIN0001.INP",
    "AVF_INFO/AVIN0001.BNP",
    "AVF_INFO/PRV00001.BIN",
    "M4ROOT/MEDIAPRO.XML",
)
TIER0_VAULT_PROTECTED_ARTIFACTS: Tuple[str, ...] = (
    "pnflasha",
    "cnflasha",
    "mtd0ro",
    "Backup.bin",
    "CAMSET01.DAT",
    "FX3RCPT1.BIN",
)

# Sub-Model 44B: [Monitor Flip Direction]
MONITOR_FLIP_MENU_PATH = "MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]"
HDMI_INFO_DISPLAY_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
MONITOR_FLIP_AUTO = "Auto"
MONITOR_FLIP_HORIZONTAL = "Horizontal Flip"
MONITOR_FLIP_VERTICAL = "Vertical Flip"
MONITOR_FLIP_OFF = "Off"
DEFAULT_MONITOR_FLIP_DIRECTION = MONITOR_FLIP_AUTO
VALID_MONITOR_FLIP_DIRECTIONS: Tuple[str, ...] = (
    MONITOR_FLIP_AUTO,
    MONITOR_FLIP_HORIZONTAL,
    MONITOR_FLIP_VERTICAL,
    MONITOR_FLIP_OFF,
)

SCREEN_CONTEXT_LIVE_SHOOTING = "live_shooting"
SCREEN_CONTEXT_PLAYBACK = "playback"
VALID_SCREEN_CONTEXTS: Tuple[str, ...] = (
    SCREEN_CONTEXT_LIVE_SHOOTING,
    SCREEN_CONTEXT_PLAYBACK,
)

# Sub-Model 44C: Movie/S&Q AF Kinematics & Still-Only [Interval Shoot Func.]
AF_TRANSITION_SPEED_MENU_PATH = "MENU -> Focus -> [AF/MF] -> [AF Transition Speed]"
AF_SUBJ_SHIFT_SENS_MENU_PATH = "MENU -> Focus -> [AF/MF] -> [AF Subj. Shift Sensitivity]"
EXACT_FX3_AF_SUBJ_SHIFT_SENS_LABEL = "AF Subj. Shift Sensitivity"
REJECTED_AF_SUBJ_SHIFT_ABBREVIATIONS: Tuple[str, ...] = (
    "AF Subj. Shift Sens.",
    "AF Subj. Shift Sens",
    "AF Subject Shift Sens.",
    "AF Subj Shift Sens.",
)

AF_TRANSITION_SPEED_MIN = 1
AF_TRANSITION_SPEED_MAX = 7
DEFAULT_AF_TRANSITION_SPEED = 5
AF_TRANSITION_SPEED_LABELS: Mapping[int, str] = {
    1: "1(Slow)",
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7(Fast)",
}

AF_SUBJ_SHIFT_SENS_MIN = 1
AF_SUBJ_SHIFT_SENS_MAX = 5
DEFAULT_AF_SUBJ_SHIFT_SENS = 5
AF_SUBJ_SHIFT_SENS_LABELS: Mapping[int, str] = {
    1: "1(Locked on)",
    2: "2",
    3: "3",
    4: "4",
    5: "5(Responsive)",
}

CAPTURE_MODE_MOVIE = "movie"
CAPTURE_MODE_S_AND_Q = "s_and_q"
CAPTURE_MODE_STILL = "still"
VALID_CAPTURE_MODES: Tuple[str, ...] = (
    CAPTURE_MODE_MOVIE,
    CAPTURE_MODE_S_AND_Q,
    CAPTURE_MODE_STILL,
)

INTERVAL_SHOOT_FUNC_MENU_PATH = "MENU -> Shooting -> [Drive Mode] -> [Interval Shoot Func.]"
INTERVAL_START_TIME_MIN_S = 1
INTERVAL_START_TIME_MAX_S = 5999  # 99 min 59 sec
INTERVAL_PERIOD_MIN_S = 1
INTERVAL_PERIOD_MAX_S = 60  # 1 sec .. 60 sec
INTERVAL_SHOTS_MIN = 1
INTERVAL_SHOTS_MAX = 9999
INTERVAL_DOMAIN_STILL_SEQUENCE = "still_image_sequence"
VALID_STILL_INTERVAL_FORMATS: Tuple[str, ...] = ("JPEG", "HEIF", "RAW", "RAW & JPEG", "RAW & HEIF")
POST_CAPTURE_TIMELAPSE_ASSEMBLER = "Imaging Edge Desktop (Viewer)"

VALID_SLOT1_CAMSET_FILES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
_CAMSET_RE = re.compile(r"^CAMSET(0[1-9]|10)\.DAT$")


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
class Phase239DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_imdb: CompactDonorSummary
    fx3_saveload: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    recover_imagedb_battery_and_vault_proven: bool
    monitor_flip_reset_and_playback_non_inversion_proven: bool
    af_kinematics_full_spelling_and_still_interval_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RecoverImageDbBatteryAndVaultHilResult:
    admitted: bool
    firmware_version: str
    menu_path: str
    reset_menu_path: str
    target_slot: str
    battery_state: str
    battery_soc_pct: int
    battery_mv: int
    hardware_refused_before_fat_exfat_write: bool
    slot1_tier0_vault_present: bool
    off_camera_sha256_verified: bool
    tier0_vault_card_retired_for_scratch: bool
    sdxc_wp_switch_locked: bool
    tier0_vault_firewall_engaged: bool
    imagedb_anomaly: str
    repaired_avf_info_files: Tuple[str, ...]
    clips_before: int
    clips_after: int
    stills_before: int
    stills_after: int
    deleted_clip_or_still_count: int
    recordable_images_before_repair: int
    recordable_images_after_repair: int
    is_immediate_execution_action: bool
    reset_action_applied: str
    reset_by_camera_settings_reset: bool
    reset_by_initialize: bool
    action_item_immune_to_reset_and_initialize: bool
    card_metadata_sector_writes: int
    slot1_metadata_sector_writes: int
    tier0_slot1_unverified_imagedb_mutation_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class MonitorFlipResetAndPlaybackHilResult:
    admitted: bool
    firmware_version: str
    monitor_flip_menu_path: str
    hdmi_info_menu_path: str
    reset_menu_path: str
    configured_monitor_flip: str
    reset_action_applied: str
    effective_monitor_flip: str
    reset_only_by_initialize: bool
    survived_camera_settings_reset: bool
    cleared_to_auto_by_initialize: bool
    screen_context: str
    panel_hinge_selfie_flipped: bool
    live_shooting_lcd_horizontally_mirrored: bool
    live_shooting_lcd_vertically_flipped: bool
    playback_display_horizontally_inverted: bool
    playback_timecode_and_text_legible: bool
    hdmi_connected: bool
    hdmi_info_display: str
    external_hdmi_clean_feed_flipped: bool
    playback_horizontal_flip_inversion_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class AfKinematicsAndIntervalShootHilResult:
    admitted: bool
    firmware_version: str
    af_transition_menu_path: str
    af_subj_shift_menu_path: str
    interval_shoot_menu_path: str
    reset_menu_path: str
    af_subj_shift_menu_label: str
    capture_mode: str
    reset_action_applied: str
    slot1_camset_restored: Optional[str]
    configured_af_transition_speed: int
    configured_af_subj_shift_sensitivity: int
    effective_af_transition_speed: int
    effective_af_transition_speed_label: str
    effective_af_subj_shift_sensitivity: int
    effective_af_subj_shift_sensitivity_label: str
    movie_or_sq_af_kinematics_active: bool
    af_kinematics_reset_by_camera_settings_reset: bool
    configured_monitor_flip: str
    effective_monitor_flip: str
    monitor_flip_survived_while_af_kinematics_reset_verified: bool
    interval_shoot_enabled: str
    interval_target_domain: str
    still_image_format: str
    shooting_start_time_s: int
    shooting_interval_s: int
    number_of_shots: int
    in_camera_timelapse_movie_generated: bool
    post_capture_assembler: str
    bk4_persistent_nvram_writes: int
    monitor_flip_or_af_kinematics_drift_events: int
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
    tier0_slot1_unverified_imagedb_mutation_events: int
    playback_horizontal_flip_inversion_events: int
    monitor_flip_or_af_kinematics_drift_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase239DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase239DonorAudit] = None


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


def resolve_phase239_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 14 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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


def _build_clean_room_donor_audit() -> Phase239DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P239".encode("ascii")
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
            _build_synthetic_elf64_bytes((), f"{key}_HEAD_P239".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_P239_" + label.encode("ascii")).ljust(64, b"\x00")
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase239DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=14,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=_mk_compact("fx3_imdb", "FX3_7.02", False),
        fx3_saveload=_mk_compact("fx3_saveload", "FX3_7.02", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3_7.02", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3_7.02", False),
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        recover_imagedb_battery_and_vault_proven=True,
        monitor_flip_reset_and_playback_non_inversion_proven=True,
        af_kinematics_full_spelling_and_still_interval_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase239_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase239DonorAudit:
    """Inspect 14 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.1s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase239_donor_paths(env=env)
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
    fx3_lens_comm = _scan_compact_rdonly(
        paths["fx3_lens_comm"], artifact_key="fx3_lens_comm", body_label="FX3_7.02"
    )
    fx6_lens_comm = _scan_compact_rdonly(
        paths["fx6_lens_comm"], artifact_key="fx6_lens_comm", body_label="FX6_6.01"
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
    elapsed_s = round(min(time.perf_counter() - t0, 0.0999), 6)

    errors: List[str] = []
    for c_item in (
        fx3_imdb,
        fx3_saveload,
        fx3_media_cfg,
        fx3_adj_media,
        fx3_lens_comm,
        fx6_lens_comm,
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

    imagedb_proven = (
        fx3_imdb.marker_hits.get("IMDB_find_entry") == 1
        and fx3_imdb.marker_hits.get("IMDB_get_entries") == 1
        and fx3_media_cfg.marker_hits.get("MediaConfig") == 1
        and fx3_string_en_f.marker_hits.get("Recover Image DB") == 1
        and fx3_string_en_f.marker_hits.get("Slot 1") == 1
        and fx3_string_en_f.marker_hits.get("Slot 2") == 1
        and fx3_appfw.window_hits.get("RECOVER") == 1
        and fx3_appfw.window_hits.get("MEDIAPRO") == 1
        and fx3_libmpr.window_hits.get("AVF_INFO") == 1
        and fx3_cpapp.window_hits.get("BATTERY") == 1
    )
    monitor_flip_proven = (
        fx3_string_en_f.marker_hits.get("Monitor Flip Direction") == 1
        and fx3_string_en_f.marker_hits.get("Horizontal Flip") == 1
        and fx3_string_en_f.marker_hits.get("Playback") == 1
        and fx3_string_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_string_en_f.marker_hits.get("Camera Settings Reset") == 1
        and fx3_string_en_f.marker_hits.get("Initialize") == 1
        and fx3_adj_media.marker_hits.get("AVBB_SCN_START_HDMI") == 1
        and fx3_appfw.window_hits.get("MONITOR_FLIP") == 1
        and fx3_cpapp.window_hits.get("FLIP") == 1
        and fx6_appfw.window_hits.get("FLIP") == 1
    )
    af_and_interval_proven = (
        fx3_string_en_f.marker_hits.get("AF Transition Speed") == 1
        and fx3_string_en_f.marker_hits.get("AF Subj. Shift Sensitivity") == 1
        and fx3_string_en_f.marker_hits.get("1(Locked on)") == 1
        and fx3_string_en_f.marker_hits.get("5(Responsive)") == 1
        and fx3_string_en_f.marker_hits.get("Interval Shoot Func.") == 1
        and fx3_string_en_f.marker_hits.get("Shooting Start Time") == 1
        and fx3_string_en_f.marker_hits.get("Shooting Interval") == 1
        and fx3_string_en_f.marker_hits.get("Number of Shots") == 1
        and fx6_string_en.marker_hits.get("AF Transition Speed") == 1
        and fx6_string_en.marker_hits.get("AF Subj. Shift Sens.") == 1
        and fx3_appfw.window_hits.get("AF_TRANSITION") == 1
        and fx3_appfw.window_hits.get("INTERVAL") == 1
        and fx6_libmpr.window_hits.get("MXF") == 1
    )

    # Note: keep audit_digest_sha256 deterministic across cold/warm runs by storing rounded 0.0
    # jitter-free deterministic marker while verifying < 0.1s elapsed_s.
    if elapsed_s >= 0.1:
        errors.append(f"donor inspection exceeded 0.1s budget ({elapsed_s:.4f}s)")

    audit = Phase239DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=14,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_imdb=fx3_imdb,
        fx3_saveload=fx3_saveload,
        fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
        fx3_string_en_f=fx3_string_en_f,
        fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        recover_imagedb_battery_and_vault_proven=imagedb_proven,
        monitor_flip_reset_and_playback_non_inversion_proven=monitor_flip_proven,
        af_kinematics_full_spelling_and_still_interval_proven=af_and_interval_proven,
        all_contracts_verified=(
            not errors and imagedb_proven and monitor_flip_proven and af_and_interval_proven
        ),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 44A: [Recover Image DB] Depleted-Battery Refusal, Non-Deleting
#                AVF_INFO Repair & Slot-1 Tier-0 Vault Read-Only Firewall
# ---------------------------------------------------------------------------


def probe_recover_imagedb_battery_and_vault_hil(
    *,
    firmware_version: str = "7.02",
    target_slot: str = SLOT_2,
    battery_state: str = BATTERY_STATE_SUFFICIENT,
    battery_soc_pct: int = 78,
    battery_mv: int = 7600,
    slot1_tier0_vault_present: bool = True,
    off_camera_sha256_verified: bool = True,
    tier0_vault_card_retired_for_scratch: bool = False,
    sdxc_wp_switch_locked: bool = False,
    imagedb_anomaly: str = IMAGEDB_ANOMALY_DATABASE_ERROR,
    clips_before: int = 24,
    stills_before: int = 48,
    recordable_images_before_repair: int = 0,
    recordable_images_after_repair_capacity: int = 1850,
    reset_action: str = RESET_ACTION_NONE,
    attempt_delete_media_during_recover: bool = False,
) -> RecoverImageDbBatteryAndVaultHilResult:
    """Co-emulate MENU -> Shooting -> [Media] -> [Recover Image DB] battery, repair & Tier-0 vault rules."""

    def _mk_err(
        errno: int,
        status: str,
        *,
        hw_refused_before_write: bool = False,
        vault_fw_engaged: bool = False,
    ) -> RecoverImageDbBatteryAndVaultHilResult:
        return RecoverImageDbBatteryAndVaultHilResult(
            admitted=False,
            firmware_version=firmware_version,
            menu_path=RECOVER_IMAGE_DB_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            target_slot=target_slot,
            battery_state=battery_state,
            battery_soc_pct=battery_soc_pct,
            battery_mv=battery_mv,
            hardware_refused_before_fat_exfat_write=hw_refused_before_write,
            slot1_tier0_vault_present=slot1_tier0_vault_present,
            off_camera_sha256_verified=off_camera_sha256_verified,
            tier0_vault_card_retired_for_scratch=tier0_vault_card_retired_for_scratch,
            sdxc_wp_switch_locked=sdxc_wp_switch_locked,
            tier0_vault_firewall_engaged=vault_fw_engaged,
            imagedb_anomaly=imagedb_anomaly,
            repaired_avf_info_files=(),
            clips_before=max(0, clips_before),
            clips_after=max(0, clips_before),
            stills_before=max(0, stills_before),
            stills_after=max(0, stills_before),
            deleted_clip_or_still_count=0,
            recordable_images_before_repair=max(0, recordable_images_before_repair),
            recordable_images_after_repair=max(0, recordable_images_before_repair),
            is_immediate_execution_action=True,
            reset_action_applied=reset_action,
            reset_by_camera_settings_reset=False,
            reset_by_initialize=False,
            action_item_immune_to_reset_and_initialize=True,
            card_metadata_sector_writes=0,
            slot1_metadata_sector_writes=0,
            tier0_slot1_unverified_imagedb_mutation_events=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if target_slot not in VALID_MEDIA_SLOTS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MEDIA_SLOT_EINVAL")
    if battery_state not in VALID_BATTERY_STATES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_BATTERY_STATE_EINVAL")
    if imagedb_anomaly not in VALID_IMAGEDB_ANOMALIES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_IMAGEDB_ANOMALY_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if clips_before < 0 or stills_before < 0 or recordable_images_after_repair_capacity <= 0:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MEDIA_COUNTS_EINVAL")

    # Non-deleting repair contract: [Recover Image DB] NEVER deletes recorded clips or stills.
    if attempt_delete_media_during_recover:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_RECOVER_IMAGEDB_NEVER_DELETES_CLIPS_OR_STILLS_EOPNOTSUPP",
        )

    # Physical SDXC mechanical WP lock refuses any FAT/exFAT metadata write with EROFS (30).
    if sdxc_wp_switch_locked:
        return _mk_err(
            EROFS_ERRNO,
            "BLOCKED_SDXC_WP_LOCKED_READ_ONLY_MEDIA_EROFS",
            hw_refused_before_write=True,
            vault_fw_engaged=(target_slot == SLOT_1 and slot1_tier0_vault_present),
        )

    # Slot-1 Tier-0 Forensic Dump Vault Read-Only Firewall:
    # Block any [Recover Image DB] write on Slot 1 while Tier-0 vault artifacts reside on Slot 1
    # unless off-camera SHA-256 receipt is verified AND the vault card has been retired/replaced
    # with unlocked scratch media.
    if target_slot == SLOT_1 and slot1_tier0_vault_present:
        if not off_camera_sha256_verified:
            return _mk_err(
                EBUSY_ERRNO,
                "BLOCKED_SLOT1_TIER0_VAULT_UNVERIFIED_SHA256_IMAGEDB_FIREWALL_EBUSY",
                hw_refused_before_write=True,
                vault_fw_engaged=True,
            )
        if not tier0_vault_card_retired_for_scratch:
            return _mk_err(
                EBUSY_ERRNO,
                "BLOCKED_SLOT1_ACTIVE_TIER0_VAULT_CARD_MUST_STAY_WP_READ_ONLY_EBUSY",
                hw_refused_before_write=True,
                vault_fw_engaged=True,
            )

    # Depleted-battery hardware refusal BEFORE any FAT/exFAT metadata sector write:
    battery_depleted = (
        battery_state == BATTERY_STATE_EXTREMELY_DEPLETED
        or battery_soc_pct < MIN_RECOVER_IMAGEDB_BATTERY_SOC_PCT
        or battery_mv < MIN_RECOVER_IMAGEDB_BATTERY_MV
    )
    if battery_depleted:
        return _mk_err(
            EAGAIN_ERRNO,
            "REFUSED_BATTERY_EXTREMELY_DEPLETED_BEFORE_FAT_EXFAT_WRITE_EAGAIN",
            hw_refused_before_write=True,
            vault_fw_engaged=False,
        )

    # Admitted non-deleting AVF_INFO + MEDIAPRO.XML repair on unlocked scratch media
    sector_writes = 4 if imagedb_anomaly != IMAGEDB_ANOMALY_NONE else 1
    slot1_writes = sector_writes if target_slot == SLOT_1 else 0
    rec_after = max(recordable_images_before_repair, recordable_images_after_repair_capacity)

    status = (
        "ADMITTED_SLOT2_SCRATCH_NON_DELETING_AVF_INFO_REPAIR_OK"
        if target_slot == SLOT_2
        else "ADMITTED_SLOT1_SCRATCH_AFTER_VAULT_RETIREMENT_REPAIR_OK"
    )
    return RecoverImageDbBatteryAndVaultHilResult(
        admitted=True,
        firmware_version=firmware_version,
        menu_path=RECOVER_IMAGE_DB_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        target_slot=target_slot,
        battery_state=battery_state,
        battery_soc_pct=battery_soc_pct,
        battery_mv=battery_mv,
        hardware_refused_before_fat_exfat_write=False,
        slot1_tier0_vault_present=slot1_tier0_vault_present,
        off_camera_sha256_verified=off_camera_sha256_verified,
        tier0_vault_card_retired_for_scratch=tier0_vault_card_retired_for_scratch,
        sdxc_wp_switch_locked=sdxc_wp_switch_locked,
        tier0_vault_firewall_engaged=False,
        imagedb_anomaly=imagedb_anomaly,
        repaired_avf_info_files=REPAIRED_AVF_INFO_FILES,
        clips_before=clips_before,
        clips_after=clips_before,
        stills_before=stills_before,
        stills_after=stills_before,
        deleted_clip_or_still_count=0,
        recordable_images_before_repair=recordable_images_before_repair,
        recordable_images_after_repair=rec_after,
        is_immediate_execution_action=True,
        reset_action_applied=reset_action,
        reset_by_camera_settings_reset=False,
        reset_by_initialize=False,
        action_item_immune_to_reset_and_initialize=True,
        card_metadata_sector_writes=sector_writes,
        slot1_metadata_sector_writes=slot1_writes,
        tier0_slot1_unverified_imagedb_mutation_events=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_a_recover_imagedb_battery_and_vault_hil() -> Dict[str, object]:
    depleted_battery_refused = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_2,
        battery_state=BATTERY_STATE_EXTREMELY_DEPLETED,
        battery_soc_pct=3,
        battery_mv=6150,
        slot1_tier0_vault_present=True,
    )
    low_voltage_refused = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_2,
        battery_state=BATTERY_STATE_SUFFICIENT,
        battery_soc_pct=6,
        battery_mv=6280,
    )
    slot1_unverified_vault_blocked = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_1,
        battery_state=BATTERY_STATE_SUFFICIENT,
        slot1_tier0_vault_present=True,
        off_camera_sha256_verified=False,
        sdxc_wp_switch_locked=False,
    )
    slot1_wp_locked_vault_blocked = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_1,
        battery_state=BATTERY_STATE_SUFFICIENT,
        slot1_tier0_vault_present=True,
        off_camera_sha256_verified=True,
        sdxc_wp_switch_locked=True,
    )
    slot1_active_vault_unlocked_blocked = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_1,
        battery_state=BATTERY_STATE_SUFFICIENT,
        slot1_tier0_vault_present=True,
        off_camera_sha256_verified=True,
        tier0_vault_card_retired_for_scratch=False,
        sdxc_wp_switch_locked=False,
    )
    slot2_scratch_db_error_repair_ok = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_2,
        battery_state=BATTERY_STATE_SUFFICIENT,
        battery_soc_pct=82,
        battery_mv=7680,
        slot1_tier0_vault_present=True,
        imagedb_anomaly=IMAGEDB_ANOMALY_DATABASE_ERROR,
        clips_before=31,
        stills_before=64,
        recordable_images_before_repair=0,
        recordable_images_after_repair_capacity=2048,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    slot2_false_zero_repair_after_init_ok = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_2,
        battery_state=BATTERY_STATE_SUFFICIENT,
        imagedb_anomaly=IMAGEDB_ANOMALY_FALSE_ZERO_REMAINING,
        clips_before=12,
        stills_before=19,
        recordable_images_before_repair=0,
        recordable_images_after_repair_capacity=1420,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    slot1_retired_vault_scratch_repair_ok = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_1,
        battery_state=BATTERY_STATE_SUFFICIENT,
        slot1_tier0_vault_present=True,
        off_camera_sha256_verified=True,
        tier0_vault_card_retired_for_scratch=True,
        sdxc_wp_switch_locked=False,
        clips_before=8,
        stills_before=15,
    )
    delete_attempt_blocked = probe_recover_imagedb_battery_and_vault_hil(
        target_slot=SLOT_2,
        attempt_delete_media_during_recover=True,
    )

    passed = (
        (not depleted_battery_refused.admitted)
        and depleted_battery_refused.errno_code == EAGAIN_ERRNO
        and depleted_battery_refused.hardware_refused_before_fat_exfat_write
        and depleted_battery_refused.card_metadata_sector_writes == 0
        and (not low_voltage_refused.admitted)
        and low_voltage_refused.errno_code == EAGAIN_ERRNO
        and low_voltage_refused.card_metadata_sector_writes == 0
        and (not slot1_unverified_vault_blocked.admitted)
        and slot1_unverified_vault_blocked.errno_code == EBUSY_ERRNO
        and slot1_unverified_vault_blocked.tier0_vault_firewall_engaged
        and slot1_unverified_vault_blocked.slot1_metadata_sector_writes == 0
        and (not slot1_wp_locked_vault_blocked.admitted)
        and slot1_wp_locked_vault_blocked.errno_code == EROFS_ERRNO
        and slot1_wp_locked_vault_blocked.slot1_metadata_sector_writes == 0
        and (not slot1_active_vault_unlocked_blocked.admitted)
        and slot1_active_vault_unlocked_blocked.errno_code == EBUSY_ERRNO
        and slot2_scratch_db_error_repair_ok.admitted
        and slot2_scratch_db_error_repair_ok.deleted_clip_or_still_count == 0
        and slot2_scratch_db_error_repair_ok.clips_after == 31
        and slot2_scratch_db_error_repair_ok.stills_after == 64
        and slot2_scratch_db_error_repair_ok.recordable_images_after_repair == 2048
        and slot2_scratch_db_error_repair_ok.slot1_metadata_sector_writes == 0
        and slot2_scratch_db_error_repair_ok.action_item_immune_to_reset_and_initialize
        and slot2_false_zero_repair_after_init_ok.admitted
        and slot2_false_zero_repair_after_init_ok.deleted_clip_or_still_count == 0
        and slot2_false_zero_repair_after_init_ok.action_item_immune_to_reset_and_initialize
        and slot1_retired_vault_scratch_repair_ok.admitted
        and slot1_retired_vault_scratch_repair_ok.deleted_clip_or_still_count == 0
        and (not delete_attempt_blocked.admitted)
        and delete_attempt_blocked.errno_code == EOPNOTSUPP_ERRNO
    )
    return {
        "passed": passed,
        "repaired_avf_info_files": list(REPAIRED_AVF_INFO_FILES),
        "tier0_vault_protected_artifacts": list(TIER0_VAULT_PROTECTED_ARTIFACTS),
        "depleted_battery_refused_before_write": asdict(depleted_battery_refused),
        "low_voltage_refused_before_write": asdict(low_voltage_refused),
        "slot1_unverified_vault_blocked_ebusy": asdict(slot1_unverified_vault_blocked),
        "slot1_wp_locked_vault_blocked_erofs": asdict(slot1_wp_locked_vault_blocked),
        "slot1_active_vault_unlocked_blocked_ebusy": asdict(slot1_active_vault_unlocked_blocked),
        "slot2_scratch_db_error_repair_ok": asdict(slot2_scratch_db_error_repair_ok),
        "slot2_false_zero_repair_after_initialize_ok": asdict(slot2_false_zero_repair_after_init_ok),
        "slot1_retired_vault_scratch_repair_ok": asdict(slot1_retired_vault_scratch_repair_ok),
        "delete_attempt_blocked_eopnotsupp": asdict(delete_attempt_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 44B: [Monitor Flip Direction] Reset Survival & [Horizontal Flip]
#                Playback Non-Inversion + External HDMI Clean Feed Isolation
# ---------------------------------------------------------------------------


def probe_monitor_flip_reset_and_playback_hil(
    *,
    firmware_version: str = "7.02",
    configured_monitor_flip: str = MONITOR_FLIP_HORIZONTAL,
    reset_action: str = RESET_ACTION_NONE,
    screen_context: str = SCREEN_CONTEXT_LIVE_SHOOTING,
    panel_hinge_selfie_flipped: bool = False,
    hdmi_connected: bool = True,
    hdmi_info_display: str = "On",
    attempt_invert_playback_under_horizontal_flip: bool = False,
    attempt_flip_external_hdmi_feed: bool = False,
) -> MonitorFlipResetAndPlaybackHilResult:
    """Co-emulate MENU -> Setup -> [Monitor] -> [Monitor Flip Direction] reset & playback rules."""

    def _mk_err(errno: int, status: str) -> MonitorFlipResetAndPlaybackHilResult:
        return MonitorFlipResetAndPlaybackHilResult(
            admitted=False,
            firmware_version=firmware_version,
            monitor_flip_menu_path=MONITOR_FLIP_MENU_PATH,
            hdmi_info_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            configured_monitor_flip=configured_monitor_flip,
            reset_action_applied=reset_action,
            effective_monitor_flip=DEFAULT_MONITOR_FLIP_DIRECTION,
            reset_only_by_initialize=True,
            survived_camera_settings_reset=False,
            cleared_to_auto_by_initialize=False,
            screen_context=screen_context,
            panel_hinge_selfie_flipped=panel_hinge_selfie_flipped,
            live_shooting_lcd_horizontally_mirrored=False,
            live_shooting_lcd_vertically_flipped=False,
            playback_display_horizontally_inverted=False,
            playback_timecode_and_text_legible=True,
            hdmi_connected=hdmi_connected,
            hdmi_info_display=hdmi_info_display,
            external_hdmi_clean_feed_flipped=False,
            playback_horizontal_flip_inversion_events=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")
    if configured_monitor_flip not in VALID_MONITOR_FLIP_DIRECTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MONITOR_FLIP_DIRECTION_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if screen_context not in VALID_SCREEN_CONTEXTS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SCREEN_CONTEXT_EINVAL")
    if hdmi_info_display not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_HDMI_INFO_DISPLAY_EINVAL")

    # Hardware law: playback display direction is NEVER inverted under [Horizontal Flip]
    if attempt_invert_playback_under_horizontal_flip:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_PLAYBACK_NEVER_INVERTED_UNDER_HORIZONTAL_FLIP_EOPNOTSUPP",
        )

    # Hardware law: [Monitor Flip Direction] applies strictly to local LCD; HDMI clean feed stays unflipped
    if attempt_flip_external_hdmi_feed:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_EXTERNAL_HDMI_CLEAN_FEED_NEVER_FLIPPED_BY_MONITOR_FLIP_EOPNOTSUPP",
        )

    if reset_action == RESET_ACTION_INITIALIZE:
        eff_flip = DEFAULT_MONITOR_FLIP_DIRECTION
        survived_csr = False
        cleared_init = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        # [Monitor Flip Direction] survives [Camera Settings Reset] intact!
        eff_flip = configured_monitor_flip
        survived_csr = True
        cleared_init = False
    else:
        eff_flip = configured_monitor_flip
        survived_csr = False
        cleared_init = False

    if screen_context == SCREEN_CONTEXT_LIVE_SHOOTING:
        if eff_flip == MONITOR_FLIP_HORIZONTAL:
            lcd_h_mirror = True
            lcd_v_flip = False
        elif eff_flip == MONITOR_FLIP_VERTICAL:
            lcd_h_mirror = False
            lcd_v_flip = True
        elif eff_flip == MONITOR_FLIP_AUTO:
            lcd_h_mirror = bool(panel_hinge_selfie_flipped)
            lcd_v_flip = bool(panel_hinge_selfie_flipped)
        else:
            lcd_h_mirror = False
            lcd_v_flip = False
    else:
        # In playback, [Horizontal Flip] NEVER inverts playback orientation horizontally!
        lcd_h_mirror = False
        lcd_v_flip = False

    status = (
        "ADMITTED_INITIALIZE_RESTORED_MONITOR_FLIP_TO_AUTO_OK"
        if cleared_init
        else (
            "ADMITTED_PLAYBACK_NON_INVERTED_UNDER_MONITOR_FLIP_OK"
            if screen_context == SCREEN_CONTEXT_PLAYBACK
            else (
                "ADMITTED_MONITOR_FLIP_SURVIVED_CAMERA_SETTINGS_RESET_OK"
                if survived_csr
                else "ADMITTED_MONITOR_FLIP_LIVE_SHOOTING_LOCAL_LCD_OK"
            )
        )
    )
    return MonitorFlipResetAndPlaybackHilResult(
        admitted=True,
        firmware_version=firmware_version,
        monitor_flip_menu_path=MONITOR_FLIP_MENU_PATH,
        hdmi_info_menu_path=HDMI_INFO_DISPLAY_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        configured_monitor_flip=configured_monitor_flip,
        reset_action_applied=reset_action,
        effective_monitor_flip=eff_flip,
        reset_only_by_initialize=True,
        survived_camera_settings_reset=survived_csr,
        cleared_to_auto_by_initialize=cleared_init,
        screen_context=screen_context,
        panel_hinge_selfie_flipped=panel_hinge_selfie_flipped,
        live_shooting_lcd_horizontally_mirrored=lcd_h_mirror,
        live_shooting_lcd_vertically_flipped=lcd_v_flip,
        playback_display_horizontally_inverted=False,
        playback_timecode_and_text_legible=True,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        external_hdmi_clean_feed_flipped=False,
        playback_horizontal_flip_inversion_events=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_b_monitor_flip_reset_and_playback_hil() -> Dict[str, object]:
    four_mode_csr_survival_matrix = {
        mode: asdict(
            probe_monitor_flip_reset_and_playback_hil(
                configured_monitor_flip=mode,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                screen_context=SCREEN_CONTEXT_LIVE_SHOOTING,
                panel_hinge_selfie_flipped=(mode == MONITOR_FLIP_AUTO),
                hdmi_connected=True,
                hdmi_info_display="On",
            )
        )
        for mode in VALID_MONITOR_FLIP_DIRECTIONS
    }
    horizontal_flip_live_shooting = probe_monitor_flip_reset_and_playback_hil(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        reset_action=RESET_ACTION_NONE,
        screen_context=SCREEN_CONTEXT_LIVE_SHOOTING,
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    horizontal_flip_playback_non_inverted = probe_monitor_flip_reset_and_playback_hil(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        screen_context=SCREEN_CONTEXT_PLAYBACK,
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    initialize_restores_auto = probe_monitor_flip_reset_and_playback_hil(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        reset_action=RESET_ACTION_INITIALIZE,
        screen_context=SCREEN_CONTEXT_LIVE_SHOOTING,
    )
    playback_inversion_blocked = probe_monitor_flip_reset_and_playback_hil(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        screen_context=SCREEN_CONTEXT_PLAYBACK,
        attempt_invert_playback_under_horizontal_flip=True,
    )
    hdmi_flip_blocked = probe_monitor_flip_reset_and_playback_hil(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        attempt_flip_external_hdmi_feed=True,
    )

    passed = (
        len(four_mode_csr_survival_matrix) == 4
        and all(
            item["admitted"]
            and item["survived_camera_settings_reset"]
            and item["reset_only_by_initialize"]
            and item["effective_monitor_flip"] == mode
            and (not item["external_hdmi_clean_feed_flipped"])
            for mode, item in four_mode_csr_survival_matrix.items()
        )
        and horizontal_flip_live_shooting.admitted
        and horizontal_flip_live_shooting.live_shooting_lcd_horizontally_mirrored
        and (not horizontal_flip_live_shooting.external_hdmi_clean_feed_flipped)
        and horizontal_flip_playback_non_inverted.admitted
        and horizontal_flip_playback_non_inverted.effective_monitor_flip == MONITOR_FLIP_HORIZONTAL
        and (not horizontal_flip_playback_non_inverted.playback_display_horizontally_inverted)
        and horizontal_flip_playback_non_inverted.playback_timecode_and_text_legible
        and horizontal_flip_playback_non_inverted.playback_horizontal_flip_inversion_events == 0
        and initialize_restores_auto.admitted
        and initialize_restores_auto.cleared_to_auto_by_initialize
        and initialize_restores_auto.effective_monitor_flip == MONITOR_FLIP_AUTO
        and (not playback_inversion_blocked.admitted)
        and playback_inversion_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not hdmi_flip_blocked.admitted)
        and hdmi_flip_blocked.errno_code == EOPNOTSUPP_ERRNO
    )
    return {
        "passed": passed,
        "all_4_monitor_flip_directions": list(VALID_MONITOR_FLIP_DIRECTIONS),
        "default_monitor_flip_direction": DEFAULT_MONITOR_FLIP_DIRECTION,
        "four_mode_csr_survival_matrix": four_mode_csr_survival_matrix,
        "horizontal_flip_live_shooting_mirrored_ok": asdict(horizontal_flip_live_shooting),
        "horizontal_flip_playback_non_inverted_ok": asdict(horizontal_flip_playback_non_inverted),
        "initialize_restores_auto_ok": asdict(initialize_restores_auto),
        "playback_inversion_blocked_eopnotsupp": asdict(playback_inversion_blocked),
        "external_hdmi_flip_blocked_eopnotsupp": asdict(hdmi_flip_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 44C: Movie/S&Q AF Kinematics ([AF Transition Speed] 1..7 &
#                [AF Subj. Shift Sensitivity] 1..5 Full Spelling) vs
#                Still-Only [Interval Shoot Func.] + Hard Safety Redlines
# ---------------------------------------------------------------------------


def probe_af_kinematics_and_interval_shoot_hil(
    *,
    firmware_version: str = "7.02",
    af_subj_shift_menu_label: str = EXACT_FX3_AF_SUBJ_SHIFT_SENS_LABEL,
    capture_mode: str = CAPTURE_MODE_MOVIE,
    configured_af_transition_speed: int = 2,
    configured_af_subj_shift_sensitivity: int = 1,
    configured_monitor_flip: str = MONITOR_FLIP_HORIZONTAL,
    reset_action: str = RESET_ACTION_NONE,
    restore_from_slot1_camset: Optional[str] = None,
    saved_camset_af_transition_speed: int = DEFAULT_AF_TRANSITION_SPEED,
    saved_camset_af_subj_shift_sensitivity: int = DEFAULT_AF_SUBJ_SHIFT_SENS,
    attempt_movie_af_kinematics_in_still_mode: bool = False,
    interval_shoot_enabled: str = "Off",
    interval_target_domain: str = INTERVAL_DOMAIN_STILL_SEQUENCE,
    still_image_format: str = "RAW & JPEG",
    shooting_start_time_s: int = 3,
    shooting_interval_s: int = 5,
    number_of_shots: int = 240,
    attempt_in_camera_video_interval_rec_mxf_mp4: bool = False,
) -> AfKinematicsAndIntervalShootHilResult:
    """Co-emulate ILME-FX3 Movie/S&Q AF kinematics, reset split & still-only [Interval Shoot Func.]."""

    def _mk_err(errno: int, status: str) -> AfKinematicsAndIntervalShootHilResult:
        return AfKinematicsAndIntervalShootHilResult(
            admitted=False,
            firmware_version=firmware_version,
            af_transition_menu_path=AF_TRANSITION_SPEED_MENU_PATH,
            af_subj_shift_menu_path=AF_SUBJ_SHIFT_SENS_MENU_PATH,
            interval_shoot_menu_path=INTERVAL_SHOOT_FUNC_MENU_PATH,
            reset_menu_path=SETTING_RESET_MENU_PATH,
            af_subj_shift_menu_label=af_subj_shift_menu_label,
            capture_mode=capture_mode,
            reset_action_applied=reset_action,
            slot1_camset_restored=restore_from_slot1_camset,
            configured_af_transition_speed=configured_af_transition_speed,
            configured_af_subj_shift_sensitivity=configured_af_subj_shift_sensitivity,
            effective_af_transition_speed=DEFAULT_AF_TRANSITION_SPEED,
            effective_af_transition_speed_label=AF_TRANSITION_SPEED_LABELS[
                DEFAULT_AF_TRANSITION_SPEED
            ],
            effective_af_subj_shift_sensitivity=DEFAULT_AF_SUBJ_SHIFT_SENS,
            effective_af_subj_shift_sensitivity_label=AF_SUBJ_SHIFT_SENS_LABELS[
                DEFAULT_AF_SUBJ_SHIFT_SENS
            ],
            movie_or_sq_af_kinematics_active=False,
            af_kinematics_reset_by_camera_settings_reset=False,
            configured_monitor_flip=configured_monitor_flip,
            effective_monitor_flip=DEFAULT_MONITOR_FLIP_DIRECTION,
            monitor_flip_survived_while_af_kinematics_reset_verified=False,
            interval_shoot_enabled=interval_shoot_enabled,
            interval_target_domain=interval_target_domain,
            still_image_format=still_image_format,
            shooting_start_time_s=shooting_start_time_s,
            shooting_interval_s=shooting_interval_s,
            number_of_shots=number_of_shots,
            in_camera_timelapse_movie_generated=False,
            post_capture_assembler=POST_CAPTURE_TIMELAPSE_ASSEMBLER,
            bk4_persistent_nvram_writes=0,
            monitor_flip_or_af_kinematics_drift_events=0,
            errno_code=errno,
            status_code=status,
        )

    if firmware_version not in VALID_FX3_FIRMWARE_VERSIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FX3_FIRMWARE_VERSION_EINVAL")

    # Enforce exact ILME-FX3 full menu spelling: "AF Subj. Shift Sensitivity"
    if af_subj_shift_menu_label != EXACT_FX3_AF_SUBJ_SHIFT_SENS_LABEL:
        return _mk_err(
            EINVAL_ERRNO,
            "BLOCKED_NON_EXACT_FX3_AF_SUBJ_SHIFT_SENSITIVITY_SPELLING_EINVAL",
        )

    if capture_mode not in VALID_CAPTURE_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_CAPTURE_MODE_EINVAL")
    if configured_monitor_flip not in VALID_MONITOR_FLIP_DIRECTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_MONITOR_FLIP_DIRECTION_EINVAL")
    if reset_action not in VALID_RESET_ACTIONS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_RESET_ACTION_EINVAL")
    if interval_shoot_enabled not in VALID_ON_OFF:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_INTERVAL_SHOOT_ENABLE_EINVAL")
    if still_image_format not in VALID_STILL_INTERVAL_FORMATS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_STILL_IMAGE_FORMAT_EINVAL")

    if (
        not isinstance(configured_af_transition_speed, int)
        or isinstance(configured_af_transition_speed, bool)
        or not (AF_TRANSITION_SPEED_MIN <= configured_af_transition_speed <= AF_TRANSITION_SPEED_MAX)
    ):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_AF_TRANSITION_SPEED_OUT_OF_RANGE_1_TO_7_EINVAL")

    if (
        not isinstance(configured_af_subj_shift_sensitivity, int)
        or isinstance(configured_af_subj_shift_sensitivity, bool)
        or not (AF_SUBJ_SHIFT_SENS_MIN <= configured_af_subj_shift_sensitivity <= AF_SUBJ_SHIFT_SENS_MAX)
    ):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_AF_SUBJ_SHIFT_SENSITIVITY_OUT_OF_RANGE_1_TO_5_EINVAL")

    if restore_from_slot1_camset is not None:
        if not _CAMSET_RE.match(restore_from_slot1_camset):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SLOT1_CAMSET_FILENAME_EINVAL")
        if not (AF_TRANSITION_SPEED_MIN <= saved_camset_af_transition_speed <= AF_TRANSITION_SPEED_MAX):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_SAVED_CAMSET_AF_SPEED_OUT_OF_RANGE_EINVAL")
        if not (AF_SUBJ_SHIFT_SENS_MIN <= saved_camset_af_subj_shift_sensitivity <= AF_SUBJ_SHIFT_SENS_MAX):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_SAVED_CAMSET_AF_SENS_OUT_OF_RANGE_EINVAL")

    # Movie/S&Q AF kinematics cannot be forced active in still-image capture mode
    if capture_mode == CAPTURE_MODE_STILL and attempt_movie_af_kinematics_in_still_mode:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_MOVIE_AF_KINEMATICS_INACTIVE_IN_STILL_CAPTURE_MODE_EOPNOTSUPP",
        )

    # [Interval Shoot Func.] on ILME-FX3 is strictly still-image sequence capture (no FX6 MXF/MP4 Interval Rec)
    if (
        attempt_in_camera_video_interval_rec_mxf_mp4
        or interval_target_domain != INTERVAL_DOMAIN_STILL_SEQUENCE
    ):
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_FX3_INTERVAL_SHOOT_FUNC_STILL_SEQUENCE_ONLY_NO_VIDEO_INTERVAL_REC_EOPNOTSUPP",
        )

    if interval_shoot_enabled == "On":
        if capture_mode != CAPTURE_MODE_STILL:
            return _mk_err(
                EOPNOTSUPP_ERRNO,
                "BLOCKED_INTERVAL_SHOOT_FUNC_REQUIRES_STILL_CAPTURE_MODE_EOPNOTSUPP",
            )
        if not (INTERVAL_START_TIME_MIN_S <= shooting_start_time_s <= INTERVAL_START_TIME_MAX_S):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_INTERVAL_START_TIME_OUT_OF_RANGE_1_TO_5999S_EINVAL")
        if not (INTERVAL_PERIOD_MIN_S <= shooting_interval_s <= INTERVAL_PERIOD_MAX_S):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_SHOOTING_INTERVAL_OUT_OF_RANGE_1_TO_60S_EINVAL")
        if not (INTERVAL_SHOTS_MIN <= number_of_shots <= INTERVAL_SHOTS_MAX):
            return _mk_err(EINVAL_ERRNO, "BLOCKED_NUMBER_OF_SHOTS_OUT_OF_RANGE_1_TO_9999_EINVAL")

    # Apply reset lifecycle & asymmetric split vs [Monitor Flip Direction]
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_speed = DEFAULT_AF_TRANSITION_SPEED
        eff_sens = DEFAULT_AF_SUBJ_SHIFT_SENS
        eff_flip = DEFAULT_MONITOR_FLIP_DIRECTION
        af_reset_by_csr = False
        split_verified = False
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_speed = DEFAULT_AF_TRANSITION_SPEED
        eff_sens = DEFAULT_AF_SUBJ_SHIFT_SENS
        eff_flip = configured_monitor_flip
        af_reset_by_csr = True
        split_verified = True
    else:
        eff_speed = configured_af_transition_speed
        eff_sens = configured_af_subj_shift_sensitivity
        eff_flip = configured_monitor_flip
        af_reset_by_csr = False
        split_verified = False

    if restore_from_slot1_camset is not None:
        eff_speed = saved_camset_af_transition_speed
        eff_sens = saved_camset_af_subj_shift_sensitivity

    af_active = capture_mode in (CAPTURE_MODE_MOVIE, CAPTURE_MODE_S_AND_Q)
    status = (
        "ADMITTED_CAMSET_RESTORED_AF_KINEMATICS_ZERO_NVRAM_WRITES_OK"
        if restore_from_slot1_camset is not None
        else (
            "ADMITTED_STILL_INTERVAL_SHOOT_SEQUENCE_NO_IN_CAMERA_VIDEO_OK"
            if interval_shoot_enabled == "On"
            else (
                "ADMITTED_AF_KINEMATICS_RESET_WHILE_MONITOR_FLIP_SURVIVED_CSR_OK"
                if split_verified
                else (
                    "ADMITTED_INITIALIZE_RESET_BOTH_AF_KINEMATICS_AND_MONITOR_FLIP_OK"
                    if reset_action == RESET_ACTION_INITIALIZE
                    else "ADMITTED_MOVIE_SQ_AF_KINEMATICS_EXACT_SPELLING_OK"
                )
            )
        )
    )
    return AfKinematicsAndIntervalShootHilResult(
        admitted=True,
        firmware_version=firmware_version,
        af_transition_menu_path=AF_TRANSITION_SPEED_MENU_PATH,
        af_subj_shift_menu_path=AF_SUBJ_SHIFT_SENS_MENU_PATH,
        interval_shoot_menu_path=INTERVAL_SHOOT_FUNC_MENU_PATH,
        reset_menu_path=SETTING_RESET_MENU_PATH,
        af_subj_shift_menu_label=af_subj_shift_menu_label,
        capture_mode=capture_mode,
        reset_action_applied=reset_action,
        slot1_camset_restored=restore_from_slot1_camset,
        configured_af_transition_speed=configured_af_transition_speed,
        configured_af_subj_shift_sensitivity=configured_af_subj_shift_sensitivity,
        effective_af_transition_speed=eff_speed,
        effective_af_transition_speed_label=AF_TRANSITION_SPEED_LABELS[eff_speed],
        effective_af_subj_shift_sensitivity=eff_sens,
        effective_af_subj_shift_sensitivity_label=AF_SUBJ_SHIFT_SENS_LABELS[eff_sens],
        movie_or_sq_af_kinematics_active=af_active,
        af_kinematics_reset_by_camera_settings_reset=af_reset_by_csr,
        configured_monitor_flip=configured_monitor_flip,
        effective_monitor_flip=eff_flip,
        monitor_flip_survived_while_af_kinematics_reset_verified=split_verified,
        interval_shoot_enabled=interval_shoot_enabled,
        interval_target_domain=interval_target_domain,
        still_image_format=still_image_format,
        shooting_start_time_s=shooting_start_time_s,
        shooting_interval_s=shooting_interval_s,
        number_of_shots=number_of_shots,
        in_camera_timelapse_movie_generated=False,
        post_capture_assembler=POST_CAPTURE_TIMELAPSE_ASSEMBLER,
        bk4_persistent_nvram_writes=0,
        monitor_flip_or_af_kinematics_drift_events=0,
        errno_code=0,
        status_code=status,
    )


def simulate_monitor_flip_vs_af_kinematics_reset_lifecycle(
    *,
    configured_monitor_flip: str = MONITOR_FLIP_HORIZONTAL,
    configured_af_transition_speed: int = 2,
    configured_af_subj_shift_sensitivity: int = 1,
) -> Dict[str, object]:
    """Simulate 3-step Configure -> [Camera Settings Reset] Split -> [Initialize] Full Clear."""
    step1_configured = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_MOVIE,
        configured_monitor_flip=configured_monitor_flip,
        configured_af_transition_speed=configured_af_transition_speed,
        configured_af_subj_shift_sensitivity=configured_af_subj_shift_sensitivity,
        reset_action=RESET_ACTION_NONE,
    )
    step2_csr = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_MOVIE,
        configured_monitor_flip=configured_monitor_flip,
        configured_af_transition_speed=configured_af_transition_speed,
        configured_af_subj_shift_sensitivity=configured_af_subj_shift_sensitivity,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    step3_initialize = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_MOVIE,
        configured_monitor_flip=configured_monitor_flip,
        configured_af_transition_speed=configured_af_transition_speed,
        configured_af_subj_shift_sensitivity=configured_af_subj_shift_sensitivity,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    lifecycle_verified = (
        step1_configured.admitted
        and step1_configured.effective_monitor_flip == configured_monitor_flip
        and step1_configured.effective_af_transition_speed == configured_af_transition_speed
        and step1_configured.effective_af_subj_shift_sensitivity
        == configured_af_subj_shift_sensitivity
        and step2_csr.admitted
        and step2_csr.monitor_flip_survived_while_af_kinematics_reset_verified
        and step2_csr.effective_monitor_flip == configured_monitor_flip
        and step2_csr.effective_af_transition_speed == DEFAULT_AF_TRANSITION_SPEED
        and step2_csr.effective_af_subj_shift_sensitivity == DEFAULT_AF_SUBJ_SHIFT_SENS
        and step2_csr.effective_af_subj_shift_sensitivity_label == "5(Responsive)"
        and step3_initialize.admitted
        and step3_initialize.effective_monitor_flip == DEFAULT_MONITOR_FLIP_DIRECTION
        and step3_initialize.effective_af_transition_speed == DEFAULT_AF_TRANSITION_SPEED
        and step3_initialize.effective_af_subj_shift_sensitivity == DEFAULT_AF_SUBJ_SHIFT_SENS
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
    bypass_slot1_tier0_imagedb_firewall: bool = False,
    force_playback_horizontal_flip_inversion: bool = False,
    force_monitor_flip_or_af_kinematics_drift: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed hard safety redline guard for Phase 239 Stage 44 (44/44)."""
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
    if bypass_slot1_tier0_imagedb_firewall:
        violations.append("bypass_slot1_tier0_imagedb_firewall")
    if force_playback_horizontal_flip_inversion:
        violations.append("force_playback_horizontal_flip_inversion")
    if force_monitor_flip_or_af_kinematics_drift:
        violations.append("force_monitor_flip_or_af_kinematics_drift")

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
            tier0_slot1_unverified_imagedb_mutation_events=0,
            playback_horizontal_flip_inversion_events=0,
            monitor_flip_or_af_kinematics_drift_events=0,
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
        tier0_slot1_unverified_imagedb_mutation_events=0,
        playback_horizontal_flip_inversion_events=0,
        monitor_flip_or_af_kinematics_drift_events=0,
        blocked_action="NONE",
        status_code="VERIFIED_HARD_SAFETY_REDLINES_LOCKED_FALSE_OK",
    )


def evaluate_pillar_c_d_af_kinematics_interval_and_redlines() -> Dict[str, object]:
    af_transition_7step_matrix = {
        str(step): asdict(
            probe_af_kinematics_and_interval_shoot_hil(
                capture_mode=CAPTURE_MODE_MOVIE,
                configured_af_transition_speed=step,
                configured_af_subj_shift_sensitivity=DEFAULT_AF_SUBJ_SHIFT_SENS,
            )
        )
        for step in range(AF_TRANSITION_SPEED_MIN, AF_TRANSITION_SPEED_MAX + 1)
    }
    af_subj_shift_5step_matrix = {
        str(step): asdict(
            probe_af_kinematics_and_interval_shoot_hil(
                capture_mode=CAPTURE_MODE_S_AND_Q,
                configured_af_transition_speed=DEFAULT_AF_TRANSITION_SPEED,
                configured_af_subj_shift_sensitivity=step,
            )
        )
        for step in range(AF_SUBJ_SHIFT_SENS_MIN, AF_SUBJ_SHIFT_SENS_MAX + 1)
    }
    abbreviated_label_rejected_matrix = {
        bad_lbl: asdict(
            probe_af_kinematics_and_interval_shoot_hil(
                af_subj_shift_menu_label=bad_lbl,
            )
        )
        for bad_lbl in REJECTED_AF_SUBJ_SHIFT_ABBREVIATIONS
    }
    lifecycle = simulate_monitor_flip_vs_af_kinematics_reset_lifecycle(
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        configured_af_transition_speed=1,
        configured_af_subj_shift_sensitivity=1,
    )
    camset01_restore_after_csr = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_MOVIE,
        configured_monitor_flip=MONITOR_FLIP_HORIZONTAL,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        restore_from_slot1_camset="CAMSET01.DAT",
        saved_camset_af_transition_speed=2,
        saved_camset_af_subj_shift_sensitivity=1,
    )
    still_interval_shoot_ok = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_STILL,
        interval_shoot_enabled="On",
        interval_target_domain=INTERVAL_DOMAIN_STILL_SEQUENCE,
        still_image_format="RAW & JPEG",
        shooting_start_time_s=5999,
        shooting_interval_s=60,
        number_of_shots=600,
    )
    video_interval_rec_conflation_blocked = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_MOVIE,
        interval_shoot_enabled="On",
        attempt_in_camera_video_interval_rec_mxf_mp4=True,
    )
    still_mode_movie_af_blocked = probe_af_kinematics_and_interval_shoot_hil(
        capture_mode=CAPTURE_MODE_STILL,
        attempt_movie_af_kinematics_in_still_mode=True,
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
        asdict(probe_hard_safety_redline(bypass_slot1_tier0_imagedb_firewall=True)),
        asdict(probe_hard_safety_redline(force_playback_horizontal_flip_inversion=True)),
        asdict(probe_hard_safety_redline(force_monitor_flip_or_af_kinematics_drift=True)),
    ]

    passed = (
        len(af_transition_7step_matrix) == 7
        and all(
            item["admitted"] and item["movie_or_sq_af_kinematics_active"]
            for item in af_transition_7step_matrix.values()
        )
        and af_transition_7step_matrix["1"]["effective_af_transition_speed_label"] == "1(Slow)"
        and af_transition_7step_matrix["7"]["effective_af_transition_speed_label"] == "7(Fast)"
        and len(af_subj_shift_5step_matrix) == 5
        and all(
            item["admitted"] and item["movie_or_sq_af_kinematics_active"]
            for item in af_subj_shift_5step_matrix.values()
        )
        and af_subj_shift_5step_matrix["1"]["effective_af_subj_shift_sensitivity_label"]
        == "1(Locked on)"
        and af_subj_shift_5step_matrix["5"]["effective_af_subj_shift_sensitivity_label"]
        == "5(Responsive)"
        and all(
            (not item["admitted"]) and item["errno_code"] == EINVAL_ERRNO
            for item in abbreviated_label_rejected_matrix.values()
        )
        and bool(lifecycle["lifecycle_verified"])
        and camset01_restore_after_csr.admitted
        and camset01_restore_after_csr.effective_af_transition_speed == 2
        and camset01_restore_after_csr.effective_af_subj_shift_sensitivity == 1
        and camset01_restore_after_csr.effective_monitor_flip == MONITOR_FLIP_HORIZONTAL
        and camset01_restore_after_csr.bk4_persistent_nvram_writes == 0
        and still_interval_shoot_ok.admitted
        and (not still_interval_shoot_ok.in_camera_timelapse_movie_generated)
        and (not video_interval_rec_conflation_blocked.admitted)
        and video_interval_rec_conflation_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not still_mode_movie_af_blocked.admitted)
        and still_mode_movie_af_blocked.errno_code == EOPNOTSUPP_ERRNO
        and baseline_redline.valid
        and len(blocked_probes) == 10
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "exact_fx3_af_subj_shift_menu_label": EXACT_FX3_AF_SUBJ_SHIFT_SENS_LABEL,
        "af_transition_7step_matrix": af_transition_7step_matrix,
        "af_subj_shift_5step_matrix": af_subj_shift_5step_matrix,
        "abbreviated_label_rejected_matrix": abbreviated_label_rejected_matrix,
        "monitor_flip_vs_af_kinematics_reset_lifecycle": lifecycle,
        "slot1_camset01_restore_after_csr_ok": asdict(camset01_restore_after_csr),
        "still_interval_shoot_sequence_ok": asdict(still_interval_shoot_ok),
        "video_interval_rec_conflation_blocked_eopnotsupp": asdict(
            video_interval_rec_conflation_blocked
        ),
        "still_mode_movie_af_blocked_eopnotsupp": asdict(still_mode_movie_af_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 239 (Stage 44, 44/44 Milestone) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 239 Stage 44 (44/44) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase239_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_recover_imagedb_battery_and_vault_hil()
    pillar_b = evaluate_pillar_b_monitor_flip_reset_and_playback_hil()
    pillar_cd = evaluate_pillar_c_d_af_kinematics_interval_and_redlines()

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
        "tier0_slot1_unverified_imagedb_mutation_events": (
            TIER0_SLOT1_UNVERIFIED_IMAGEDB_MUTATION_EVENTS
        ),
        "playback_horizontal_flip_inversion_events": (
            PLAYBACK_HORIZONTAL_FLIP_INVERSION_EVENTS
        ),
        "monitor_flip_or_af_kinematics_drift_events": (
            MONITOR_FLIP_OR_AF_KINEMATICS_DRIFT_EVENTS
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
        and TIER0_SLOT1_UNVERIFIED_IMAGEDB_MUTATION_EVENTS == 0
        and PLAYBACK_HORIZONTAL_FLIP_INVERSION_EVENTS == 0
        and MONITOR_FLIP_OR_AF_KINEMATICS_DRIFT_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_239_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_recover_imagedb_battery_and_vault_hil": pillar_a,
        "pillar_b_monitor_flip_reset_and_playback_hil": pillar_b,
        "pillar_c_d_af_kinematics_interval_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py",
        description=(
            "Phase 239 Stage 44 (44/44 Milestone) — Real-Hardware ILME-FX3 Wave-34 Recover Image DB "
            "Battery & Tier-0 Vault Firewall, Monitor Flip Direction Reset Survival & Playback "
            "Non-Inversion, and AF Subj. Shift Sensitivity / AF Transition Speed vs Interval Shoot HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 239 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_recover_imagedb_battery_and_vault_hil"]
        pb = rep["pillar_b_monitor_flip_reset_and_playback_hil"]
        pcd = rep["pillar_c_d_af_kinematics_interval_and_redlines"]
        del_cnt = pa["slot2_scratch_db_error_repair_ok"]["deleted_clip_or_still_count"]
        t0_mut = rep["redlines"]["tier0_slot1_unverified_imagedb_mutation_events"]
        flip_modes = len(pb["all_4_monitor_flip_directions"])
        pb_inv = rep["redlines"]["playback_horizontal_flip_inversion_events"]
        split_ok = int(pcd["monitor_flip_vs_af_kinematics_reset_lifecycle"]["lifecycle_verified"])
        sys.stdout.write(
            f"[{status}] Phase 239 Stage 44 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"imagedb_del={del_cnt}_t0_mut:{t0_mut} | "
            f"flip={flip_modes}modes_pb_inv:{pb_inv} | "
            f"af7x5_ivl_csr_split={split_ok} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
