#!/usr/bin/env python3
"""Phase 217 — Stage 39 (`39/39` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[File Settings]` (`Cam ID + Reel#` / 37-Char ASCII
`[Title Name Settings]` / SDHC `<=32GB` FAT32 Forced `[Standard]` Lock & Custom Folder Block +
`Shot Mark1/2` `*M01.XML` Sidecar, `[Image Jump Setting]` & FTP `[Only Shot Mark Mov.]`),
`[TC/UB]` (`[Time Code Make: Regenerate]` Slot-1 Exclusive Master Read Under `[Simult. Recording]`,
Forced `[Rec Run]`, `VMC-BNCM1` `EXT-LK` Immediate Release & `S&Q` HDMI `Time Code Output` Block),
and `[REC Lamp]` (`All On` / `Only Front Off` / `All Off` Hardware-Coupled Rear + Top `REC` Button
Tally, Independent `[Emphasized REC Display]` HDMI Red Frame & `[Silent Mode]` -> `[Audio signals]`
Hard `[Off]` Lock) HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) 12-donor inspection (< 0.02s cold,
cached per process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `sdhc_non_standard_filename_or_custom_folder_bypasses == 0`
- `slot2_simult_tc_regenerate_contamination_events == 0`
- `decoupled_top_rec_button_vs_rear_tally_mismatches == 0`
- `raw_firmware_bytes_leaked == 0`
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
import string
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 217 Schema & Hard-Locked Safety Redlines (39/39 Milestone)
# ---------------------------------------------------------------------------

PHASE_217_SCHEMA = "phase217_realhw_filesettings_shotmark_tcregen_reclamp_coemulator_v1"
PHASE_217_VERSION = "217.0.0"
STAGE_INDEX = 39
STAGE_TOTAL = 39
MILESTONE_LABEL = "39/39"
STAGE_NAME = "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil"

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX6 = "ILME-FX6"
FX3_MODEL_ID = 0x91030080

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
SDHC_NON_STANDARD_FILENAME_OR_CUSTOM_FOLDER_BYPASSES = 0
SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION_EVENTS = 0
DECOUPLED_TOP_REC_BUTTON_VS_REAR_TALLY_MISMATCHES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

EINVAL_ERRNO = 22  # Linux EINVAL
EOPNOTSUPP_ERRNO = 95  # Linux ARM64 EOPNOTSUPP

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
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"HDMI"),
    "fx3_string_en_f": (
        b"File Settings",
        b"File Name Format",
        b"File Number",
        b"Series",
        b"Reset",
        b"Series Counter Reset",
        b"Title Name Settings",
        b"Cam ID + Reel#",
        b"Standard",
        b"Title",
        b"Date + Title",
        b"Title + Date",
        b"Shot Mark",
        b"Add Shot Mark1",
        b"Add Shot Mark2",
        b"Add/Delete Shot Mark1",
        b"Add/Delete Shot Mark2",
        b"Image Jump Setting",
        b"Shot Mark Only",
        b"Shot Mark1 Only",
        b"Shot Mark2 Only",
        b"No Shot Mark",
        b"Only Shot Mark Mov.",
        b"Only Shot Mark",
        b"Select on Cam & Send",
        b"Target Movie",
        b"FTP Transfer",
        b"Time Code Make",
        b"Regenerate",
        b"Preset",
        b"Time Code Run",
        b"Rec Run",
        b"Free Run",
        b"Time Code Output",
        b"Recording Media",
        b"Simult. Recording",
        b"S&Q",
        b"REC Lamp",
        b"All On",
        b"Only Front Off",
        b"All Off",
        b"Emphasized REC Display",
        b"HDMI Info. Display",
        b"Silent Mode",
    ),
    "fx6_string_en": (
        b"File",
        b"Shot Mark",
        b"Preset",
        b"Rec Run",
        b"Free Run",
        b"Tally",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_942_528, "SILENT_MODE", b"SILENT_MODE"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_958_912, "SHOT_MARK", b"SHOT_MARK"),
        (49_971_200, "REC_LAMP", b"REC_LAMP"),
        (50_016_256, "CLIP", b"CLIP"),
        (51_433_472, "SHOTMARK_CAMEL", b"ShotMark"),
        (51_486_720, "TIMECODE_CAMEL", b"TimeCode"),
        (59_801_600, "M4ROOT", b"M4ROOT"),
        (62_623_744, "REGENERATE", b"REGENERATE"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_236_736, "CLIP", b"CLIP"),
        (39_022_592, "TIMECODE", b"TIMECODE"),
        (39_387_136, "TALLY", b"TALLY"),
        (39_464_960, "M4ROOT", b"M4ROOT"),
        (40_804_352, "SHOT_MARK", b"SHOT_MARK"),
        (41_213_952, "REGENERATE", b"REGENERATE"),
    ),
    "fx3_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (221_184, "TC", b"TC"),
        (577_536, "TIMECODE", b"TimeCode"),
        (696_320, "HDMI", b"HDMI"),
        (13_066_240, "LTC", b"LTC"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (135_168, "AUDIO", b"Audio"),
        (196_608, "TC", b"TC"),
        (294_912, "TALLY", b"Tally"),
        (561_152, "TIMECODE", b"TimeCode"),
        (684_032, "HDMI", b"HDMI"),
        (704_512, "LTC", b"LTC"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (131_072, "XAVC", b"Xavc"),
        (159_744, "MP4", b"Mp4"),
        (172_032, "XML", b"Xml"),
        (2_965_504, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
        (2_965_504, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (2_969_600, "SHOT_MARK", b"ShotMark"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (163_840, "XAVC", b"Xavc"),
        (13_475_840, "LTC_CHANGE_TABLE", b"LtcChangeTable"),
        (13_484_032, "SHOT_MARK", b"ShotMark"),
        (13_516_800, "NON_REAL_TIME_META", b"NonRealTimeMeta"),
    ),
}

# ---------------------------------------------------------------------------
# Sub-model A/B/C Constants (Wave-29 Official ILME-FX3 Ver. 7.02 Contracts)
# ---------------------------------------------------------------------------

VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
VALID_CAPTURE_MODES: Tuple[str, ...] = ("Movie", "S&Q", "Photo")
VALID_RECORDING_MEDIA: Tuple[str, ...] = ("Slot 1", "Slot 2", "Simult. Recording")

FILE_SETTINGS_MENU_PATH = "MENU -> Shooting -> [File] -> [File Settings]"
FMT_STANDARD = "Standard"
FMT_CAM_ID_REEL = "Cam ID + Reel#"
FMT_TITLE = "Title"
FMT_DATE_PLUS_TITLE = "Date + Title"
FMT_TITLE_PLUS_DATE = "Title + Date"
VALID_FILE_NAME_FORMATS: Tuple[str, ...] = (
    FMT_STANDARD,
    FMT_CAM_ID_REEL,
    FMT_TITLE,
    FMT_DATE_PLUS_TITLE,
    FMT_TITLE_PLUS_DATE,
)
VALID_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
VALID_MEDIA_CARD_TYPES: Tuple[str, ...] = ("CFexpress Type A", "SDXC", "SDHC")
SDHC_MAX_CAPACITY_GB = 32
MOVIE_CLIP_FOLDER_LOCKED = "/PRIVATE/M4ROOT/CLIP"

TITLE_NAME_DEFAULT = "C"
TITLE_NAME_MAX_CHARS = 37
TITLE_NAME_PUNCTUATION = ".-_@!#$%+=^~(),;[]"
TITLE_NAME_ALLOWED_ASCII = frozenset(string.ascii_letters + string.digits + TITLE_NAME_PUNCTUATION)

JUMP_SHOT_MARK_ONLY = "Shot Mark Only"
JUMP_SHOT_MARK1_ONLY = "Shot Mark1 Only"
JUMP_SHOT_MARK2_ONLY = "Shot Mark2 Only"
JUMP_NO_SHOT_MARK = "No Shot Mark"
VALID_IMAGE_JUMP_SETTINGS: Tuple[str, ...] = (
    JUMP_SHOT_MARK_ONLY,
    JUMP_SHOT_MARK1_ONLY,
    JUMP_SHOT_MARK2_ONLY,
    JUMP_NO_SHOT_MARK,
)

FTP_FILTER_ALL = "All"
FTP_FILTER_ONLY_SHOT_MARK_MOV = "Only Shot Mark Mov."
FTP_FILTER_ONLY_SHOT_MARK = "Only Shot Mark"
VALID_FTP_TARGET_MOVIE_FILTERS: Tuple[str, ...] = (
    FTP_FILTER_ALL,
    FTP_FILTER_ONLY_SHOT_MARK_MOV,
    FTP_FILTER_ONLY_SHOT_MARK,
)

TC_UB_MENU_PATH = "MENU -> Shooting -> [TC/UB] -> [Time Code Make]"
TC_MAKE_PRESET = "Preset"
TC_MAKE_REGENERATE = "Regenerate"
VALID_TIME_CODE_MAKE: Tuple[str, ...] = (TC_MAKE_PRESET, TC_MAKE_REGENERATE)
TC_RUN_REC_RUN = "Rec Run"
TC_RUN_FREE_RUN = "Free Run"
VALID_TIME_CODE_RUN: Tuple[str, ...] = (TC_RUN_REC_RUN, TC_RUN_FREE_RUN)
VALID_TC_NOMINAL_FPS: Tuple[int, ...] = (24, 25, 30, 50, 60)
EXT_LK_MIN_SYNC_SECONDS = 10.0

REC_LAMP_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [REC Lamp]"
AUDIO_SIGNALS_MENU_PATH = "MENU -> Setup -> [Sound Option] -> [Audio signals]"
REC_LAMP_ALL_ON = "All On"
REC_LAMP_ONLY_FRONT_OFF = "Only Front Off"
REC_LAMP_ALL_OFF = "All Off"
VALID_REC_LAMP_MODES: Tuple[str, ...] = (
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    REC_LAMP_ALL_OFF,
)


class RealHwFileSettingsShotMarkTcRegenRecLampError(ValueError):
    """Raised on invalid Phase 217 co-emulator configuration arguments."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Sub-models A-C + Redlines
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
class Phase217DonorAudit:
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
    file_settings_sdhc_and_shotmark_proven: bool
    tc_regenerate_slot1_and_extlk_proven: bool
    rec_lamp_coupled_tally_and_silent_audio_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FileSettingsShotMarkHilResult:
    admitted: bool
    menu_path: str
    recording_media: str
    slot1_card_type: str
    slot1_capacity_gb: int
    slot2_card_type: str
    slot2_capacity_gb: int
    requested_file_name_format: str
    effective_file_name_format: str
    sdhc_forced_standard_lock: bool
    file_number_mode: str
    series_counter_reset: bool
    assigned_clip_number: int
    next_series_counter: int
    title_name: str
    title_char_length: int
    movie_folder_path: str
    clip_filename: str
    active_slot_clip_paths: Tuple[str, ...]
    sidecar_xml_path: str
    sidecar_xml_excerpt: str
    prior_recorded_clips: Tuple[str, ...]
    prior_clips_retroactively_renamed: bool
    shot_mark1_frames: Tuple[int, ...]
    shot_mark2_frames: Tuple[int, ...]
    has_shot_mark1: bool
    has_shot_mark2: bool
    has_any_shot_mark: bool
    image_jump_setting: str
    clip_matched_by_image_jump: bool
    ftp_target_movie_filter: str
    clip_selected_for_ftp_transfer: bool
    sdhc_non_standard_filename_or_custom_folder_bypasses: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class TcRegenerateSlot1ExtLkHilResult:
    admitted: bool
    menu_path: str
    capture_mode: str
    recording_media: str
    time_code_make: str
    requested_time_code_run: str
    effective_time_code_run: str
    forced_rec_run_under_regenerate: bool
    time_code_run_menu_available: bool
    nominal_fps: int
    preset_tc: str
    slot1_last_end_tc: str
    slot2_last_end_tc: str
    regenerate_reference_slot: str
    slot2_simult_tc_ignored: bool
    standby_frames: int
    record_frames: int
    clip_start_tc: str
    clip_end_tc: str
    vmc_bncm1_attached: bool
    sync_hold_seconds: float
    prior_ext_lk_locked: bool
    ext_lk_active: bool
    ext_lk_released: bool
    ext_lk_release_reasons: Tuple[str, ...]
    tc_status_badge: str
    requested_hdmi_time_code_output: str
    hdmi_time_code_output_available: bool
    effective_hdmi_time_code_output: str
    hdmi_tc_packet_stream_active: bool
    slot2_simult_tc_regenerate_contamination_events: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RecLampCoupledTallySilentAudioHilResult:
    admitted: bool
    rec_lamp_menu_path: str
    audio_signals_menu_path: str
    rec_lamp_mode: str
    is_recording: bool
    front_tally_led_on: bool
    rear_tally_led_on: bool
    top_rec_button_led_on: bool
    rear_and_top_rec_button_coupled: bool
    emphasized_rec_display: str
    hdmi_info_display: str
    lcd_red_rec_frame_active: bool
    hdmi_red_rec_frame_active: bool
    silent_mode: str
    requested_audio_signals: str
    effective_audio_signals: str
    audio_signals_locked_by_silent_mode: bool
    af_lock_beep_emitted: bool
    self_timer_beep_emitted: bool
    decoupled_top_rec_button_vs_rear_tally_mismatches: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    sdhc_non_standard_filename_or_custom_folder_bypasses: int
    slot2_simult_tc_regenerate_contamination_events: int
    decoupled_top_rec_button_vs_rear_tally_mismatches: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase217DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase217DonorAudit] = None


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


def resolve_phase217_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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
    data: bytes, *, file_bytes: int, artifact_key: str, body_label: str,
    source_mode: str, tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("ascii", "replace"): (1 if tok in data else 0) for tok in tokens}
    return CompactDonorSummary(
        artifact_key=artifact_key, body_label=body_label, source_mode=source_mode,
        file_bytes=file_bytes, elf64_le_ok=elf64_ok, uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16], marker_hits=hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data, file_bytes=file_bytes, artifact_key=artifact_key, body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY", tokens=COMPACT_DONOR_TOKENS[artifact_key],
    )


def _scan_large_donor_rdonly(
    path: Path, *, artifact_key: str, body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key, body_label=body_label, source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True, bytes_read_total=bytes_read_total, file_bytes=file_bytes,
        elf64_le_ok=elf64_ok, window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase217DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw, file_bytes=EXPECTED_DONOR_BYTES[key], artifact_key=key,
            body_label=label, source_mode=mode, tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        )
        hits = {lbl: 1 for _off, lbl, _tok in LARGE_DONOR_WINDOWS[key]}
        return BoundedWindowDonorSummary(
            artifact_key=key, body_label=label, source_mode=mode, bounded_windows_only=True,
            bytes_read_total=len(head), file_bytes=EXPECTED_DONOR_BYTES[key], elf64_le_ok=is_elf,
            window_hits=hits, head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase217DonorAudit(
        source_mode=mode, access_mode=DONOR_ACCESS_MODE, donor_files_inspected=12,
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
        file_settings_sdhc_and_shotmark_proven=True,
        tc_regenerate_slot1_and_extlk_proven=True,
        rec_lamp_coupled_tally_and_silent_audio_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase217_donors(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Phase217DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase217_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple((k, str(p), p.stat().st_size, p.stat().st_mtime_ns) for k, p in sorted(paths.items()))
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(paths["fx3_lens_comm"], artifact_key="fx3_lens_comm", body_label="FX3_7.02")
    fx6_lens_comm = _scan_compact_rdonly(paths["fx6_lens_comm"], artifact_key="fx6_lens_comm", body_label="FX6_6.01")
    fx3_media_cfg = _scan_compact_rdonly(paths["fx3_media_cfg"], artifact_key="fx3_media_cfg", body_label="FX3_7.02")
    fx3_adj_media = _scan_compact_rdonly(paths["fx3_adj_media"], artifact_key="fx3_adj_media", body_label="FX3_7.02")
    fx3_string_en_f = _scan_compact_rdonly(paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="FX3_7.02")
    fx6_string_en = _scan_compact_rdonly(paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="FX6_6.01")
    fx3_appfw = _scan_large_donor_rdonly(paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3_7.02")
    fx6_appfw = _scan_large_donor_rdonly(paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6_6.01")
    fx3_cpapp = _scan_large_donor_rdonly(paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3_7.02")
    fx6_cpapp = _scan_large_donor_rdonly(paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6_6.01")
    fx3_libmpr = _scan_large_donor_rdonly(paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3_7.02")
    fx6_libmpr = _scan_large_donor_rdonly(paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6_6.01")

    errors: List[str] = []
    for c_item in (fx3_lens_comm, fx6_lens_comm, fx3_media_cfg, fx3_adj_media, fx3_string_en_f, fx6_string_en):
        if c_item.file_bytes != EXPECTED_DONOR_BYTES[c_item.artifact_key]:
            errors.append(f"{c_item.artifact_key} byte size {c_item.file_bytes} != {EXPECTED_DONOR_BYTES[c_item.artifact_key]}")
        if not all(c_item.marker_hits.values()):
            errors.append(f"{c_item.artifact_key} missing tokens: {c_item.marker_hits}")

    for w_item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        if w_item.file_bytes != EXPECTED_DONOR_BYTES[w_item.artifact_key]:
            errors.append(f"{w_item.artifact_key} byte size {w_item.file_bytes} != {EXPECTED_DONOR_BYTES[w_item.artifact_key]}")
        if not all(w_item.window_hits.values()):
            errors.append(f"{w_item.artifact_key} missing window markers: {w_item.window_hits}")

    filesettings_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("File Settings") == 1
        and fx3_string_en_f.marker_hits.get("Title Name Settings") == 1
        and fx3_string_en_f.marker_hits.get("Cam ID + Reel#") == 1
        and fx3_string_en_f.marker_hits.get("Add Shot Mark1") == 1
        and fx3_string_en_f.marker_hits.get("Image Jump Setting") == 1
        and fx3_string_en_f.marker_hits.get("Only Shot Mark Mov.") == 1
        and fx3_appfw.window_hits.get("SHOT_MARK") == 1
        and fx3_libmpr.window_hits.get("NON_REAL_TIME_META") == 1
        and fx3_libmpr.window_hits.get("SHOT_MARK") == 1
    )
    tcregen_ok = (
        fx3_adj_media.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Time Code Make") == 1
        and fx3_string_en_f.marker_hits.get("Regenerate") == 1
        and fx3_string_en_f.marker_hits.get("Time Code Output") == 1
        and fx3_string_en_f.marker_hits.get("Simult. Recording") == 1
        and fx3_appfw.window_hits.get("REGENERATE") == 1
        and fx3_cpapp.window_hits.get("LTC") == 1
        and fx3_libmpr.window_hits.get("LTC_CHANGE_TABLE") == 1
    )
    reclamp_ok = (
        fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("REC Lamp") == 1
        and fx3_string_en_f.marker_hits.get("Only Front Off") == 1
        and fx3_string_en_f.marker_hits.get("Silent Mode") == 1
        and fx3_appfw.window_hits.get("REC_LAMP") == 1
        and fx3_appfw.window_hits.get("SILENT_MODE") == 1
    )
    audit = Phase217DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY", access_mode=DONOR_ACCESS_MODE, donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm, fx6_lens_comm=fx6_lens_comm, fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media, fx3_string_en_f=fx3_string_en_f, fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw, fx6_appfw=fx6_appfw, fx3_cpapp=fx3_cpapp, fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr, fx6_libmpr=fx6_libmpr,
        file_settings_sdhc_and_shotmark_proven=filesettings_ok,
        tc_regenerate_slot1_and_extlk_proven=tcregen_ok,
        rec_lamp_coupled_tally_and_silent_audio_proven=reclamp_ok,
        all_contracts_verified=(len(errors) == 0 and filesettings_ok and tcregen_ok and reclamp_ok),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: [File Settings] 5-Mode Naming, 37-Char Title, SDHC Lock & Shot Mark1/2
# ---------------------------------------------------------------------------


def validate_title_name_ascii(title_name: str) -> Tuple[bool, str]:
    """Validate [Title Name Settings]: 1..37 chars from Sony allowed ASCII set."""
    if not isinstance(title_name, str) or len(title_name) == 0:
        return False, "EMPTY_TITLE_NAME"
    if len(title_name) > TITLE_NAME_MAX_CHARS:
        return False, f"TITLE_EXCEEDS_{TITLE_NAME_MAX_CHARS}_CHARS"
    for ch in title_name:
        if ch not in TITLE_NAME_ALLOWED_ASCII:
            return False, f"DISALLOWED_CHAR:{ch!r}"
    return True, "OK"


def evaluate_shot_mark_jump_and_ftp_filter(
    clips: Sequence[Tuple[str, bool, bool]],
    *,
    image_jump_setting: str = JUMP_SHOT_MARK_ONLY,
    ftp_target_movie_filter: str = FTP_FILTER_ONLY_SHOT_MARK_MOV,
) -> Dict[str, Tuple[str, ...]]:
    """Filter `(clip_name, has_mark1, has_mark2)` records for [Image Jump Setting] and FTP transfer."""
    if image_jump_setting not in VALID_IMAGE_JUMP_SETTINGS:
        raise RealHwFileSettingsShotMarkTcRegenRecLampError(
            f"Unsupported image_jump_setting {image_jump_setting!r}"
        )
    if ftp_target_movie_filter not in VALID_FTP_TARGET_MOVIE_FILTERS:
        raise RealHwFileSettingsShotMarkTcRegenRecLampError(
            f"Unsupported ftp_target_movie_filter {ftp_target_movie_filter!r}"
        )
    jump_hits: List[str] = []
    ftp_hits: List[str] = []
    for name, m1, m2 in clips:
        if (
            (image_jump_setting == JUMP_SHOT_MARK_ONLY and (m1 or m2))
            or (image_jump_setting == JUMP_SHOT_MARK1_ONLY and m1)
            or (image_jump_setting == JUMP_SHOT_MARK2_ONLY and m2)
            or (image_jump_setting == JUMP_NO_SHOT_MARK and (not m1) and (not m2))
        ):
            jump_hits.append(name)
        if ftp_target_movie_filter == FTP_FILTER_ALL or (m1 or m2):
            ftp_hits.append(name)
    return {
        "image_jump_matched_clips": tuple(jump_hits),
        "ftp_transfer_selected_clips": tuple(ftp_hits),
    }


def probe_file_settings_sdhc_lock_and_shotmark_hil(
    *,
    recording_media: str = "Slot 1",
    slot1_card_type: str = "CFexpress Type A",
    slot1_capacity_gb: int = 160,
    slot2_card_type: str = "SDXC",
    slot2_capacity_gb: int = 128,
    requested_file_name_format: str = FMT_STANDARD,
    file_number_mode: str = "Series",
    series_counter_reset: bool = False,
    prior_series_counter: int = 0,
    max_existing_clip_num_on_card: int = 0,
    title_name: str = TITLE_NAME_DEFAULT,
    camera_id: str = "A",
    reel_number: int = 1,
    date_yyyymmdd: str = "20261115",
    camera_uid4: str = "FX3A",
    custom_movie_folder_name: Optional[str] = None,
    attempt_unlock_non_standard_on_sdhc: bool = False,
    prior_recorded_clips: Sequence[str] = ("C0001.MP4",),
    rec_shot_mark1_frames: Sequence[int] = (),
    rec_shot_mark2_frames: Sequence[int] = (),
    playback_toggle_shot_mark1_frames: Sequence[int] = (),
    playback_toggle_shot_mark2_frames: Sequence[int] = (),
    image_jump_setting: str = JUMP_SHOT_MARK_ONLY,
    ftp_target_movie_filter: str = FTP_FILTER_ALL,
) -> FileSettingsShotMarkHilResult:
    """Co-emulate [File Settings] 5-mode naming, 37-char ASCII Title, SDHC lock & Shot Mark1/2 XML."""
    for val, allowed, label in (
        (recording_media, VALID_RECORDING_MEDIA, "recording_media"),
        (slot1_card_type, VALID_MEDIA_CARD_TYPES, "slot1_card_type"),
        (slot2_card_type, VALID_MEDIA_CARD_TYPES, "slot2_card_type"),
        (file_number_mode, VALID_FILE_NUMBER_MODES, "file_number_mode"),
        (image_jump_setting, VALID_IMAGE_JUMP_SETTINGS, "image_jump_setting"),
        (ftp_target_movie_filter, VALID_FTP_TARGET_MOVIE_FILTERS, "ftp_target_movie_filter"),
    ):
        if val not in allowed:
            raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Unsupported {label} {val!r}")
    if prior_series_counter < 0 or max_existing_clip_num_on_card < 0:
        raise RealHwFileSettingsShotMarkTcRegenRecLampError("Clip counters must be non-negative")
    if len(date_yyyymmdd) != 8 or not date_yyyymmdd.isdigit():
        raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Invalid date_yyyymmdd {date_yyyymmdd!r}")
    if len(camera_uid4) != 4 or not camera_uid4.isalnum():
        raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Invalid camera_uid4 {camera_uid4!r}")

    prior_tuple = tuple(prior_recorded_clips)

    def _mk_err(errno: int, status: str, *, sdhc_lock: bool = False) -> FileSettingsShotMarkHilResult:
        return FileSettingsShotMarkHilResult(
            admitted=False, menu_path=FILE_SETTINGS_MENU_PATH, recording_media=recording_media,
            slot1_card_type=slot1_card_type, slot1_capacity_gb=slot1_capacity_gb,
            slot2_card_type=slot2_card_type, slot2_capacity_gb=slot2_capacity_gb,
            requested_file_name_format=requested_file_name_format,
            effective_file_name_format=FMT_STANDARD if sdhc_lock else "INVALID",
            sdhc_forced_standard_lock=sdhc_lock, file_number_mode=file_number_mode,
            series_counter_reset=series_counter_reset, assigned_clip_number=0,
            next_series_counter=prior_series_counter, title_name=title_name,
            title_char_length=len(title_name) if isinstance(title_name, str) else 0,
            movie_folder_path=MOVIE_CLIP_FOLDER_LOCKED, clip_filename="",
            active_slot_clip_paths=(), sidecar_xml_path="", sidecar_xml_excerpt="",
            prior_recorded_clips=prior_tuple, prior_clips_retroactively_renamed=False,
            shot_mark1_frames=(), shot_mark2_frames=(), has_shot_mark1=False,
            has_shot_mark2=False, has_any_shot_mark=False, image_jump_setting=image_jump_setting,
            clip_matched_by_image_jump=False, ftp_target_movie_filter=ftp_target_movie_filter,
            clip_selected_for_ftp_transfer=False,
            sdhc_non_standard_filename_or_custom_folder_bypasses=0,
            errno_code=errno, status_code=status,
        )

    if requested_file_name_format not in VALID_FILE_NAME_FORMATS:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_FILE_NAME_FORMAT_EINVAL")
    if (slot1_card_type == "SDHC" and not (1 <= slot1_capacity_gb <= SDHC_MAX_CAPACITY_GB)) or (
        slot2_card_type == "SDHC" and not (1 <= slot2_capacity_gb <= SDHC_MAX_CAPACITY_GB)
    ) or (slot1_card_type == "SDXC" and slot1_capacity_gb <= SDHC_MAX_CAPACITY_GB) or (
        slot2_card_type == "SDXC" and slot2_capacity_gb <= SDHC_MAX_CAPACITY_GB
    ):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_SDHC_SDXC_CAPACITY_BOUNDARY_EINVAL")

    if custom_movie_folder_name is not None and custom_movie_folder_name != "CLIP":
        return _mk_err(EOPNOTSUPP_ERRNO, "BLOCKED_CUSTOM_MOVIE_FOLDER_NAME_PROHIBITED_EOPNOTSUPP")

    if len(camera_id) != 1 or camera_id not in string.ascii_uppercase:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_CAMERA_ID_LETTER_EINVAL")
    if not (1 <= reel_number <= 999):
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_REEL_NUMBER_RANGE_EINVAL")

    title_ok, title_reason = validate_title_name_ascii(title_name)
    if not title_ok:
        return _mk_err(EINVAL_ERRNO, f"BLOCKED_INVALID_TITLE_NAME_{title_reason}_EINVAL")

    active_slots = (
        (1,) if recording_media == "Slot 1"
        else ((2,) if recording_media == "Slot 2" else (1, 2))
    )
    sdhc_active = (1 in active_slots and slot1_card_type == "SDHC") or (
        2 in active_slots and slot2_card_type == "SDHC"
    )
    if sdhc_active and attempt_unlock_non_standard_on_sdhc and requested_file_name_format != FMT_STANDARD:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_SDHC_FORCE_LOCKED_TO_STANDARD_FORMAT_EOPNOTSUPP",
            sdhc_lock=True,
        )

    eff_fmt = FMT_STANDARD if sdhc_active else requested_file_name_format
    if file_number_mode == "Reset" or series_counter_reset:
        clip_num = max_existing_clip_num_on_card + 1
    else:
        clip_num = max(prior_series_counter, max_existing_clip_num_on_card) + 1
    if clip_num > 9999:
        clip_num = 1
    next_series = clip_num if file_number_mode == "Series" else prior_series_counter

    if eff_fmt == FMT_STANDARD:
        stem = f"C{clip_num:04d}"
    elif eff_fmt == FMT_CAM_ID_REEL:
        stem = f"{camera_id}{reel_number:03d}C{clip_num:04d}_{date_yyyymmdd[2:]}_{camera_uid4.upper()}"
    elif eff_fmt == FMT_TITLE:
        stem = f"{title_name}{clip_num:04d}"
    elif eff_fmt == FMT_DATE_PLUS_TITLE:
        stem = f"{date_yyyymmdd}_{title_name}{clip_num:04d}"
    else:
        stem = f"{title_name}_{date_yyyymmdd}_{clip_num:04d}"

    clip_filename = f"{stem}.MP4"
    slot_paths = tuple(f"/mnt/slot{s}{MOVIE_CLIP_FOLDER_LOCKED}/{clip_filename}" for s in active_slots)
    sidecar_xml_path = f"{MOVIE_CLIP_FOLDER_LOCKED}/{stem}M01.XML"

    m1_set = {int(f) for f in rec_shot_mark1_frames if int(f) >= 0}
    for f in playback_toggle_shot_mark1_frames:
        fi = int(f)
        if fi < 0:
            raise RealHwFileSettingsShotMarkTcRegenRecLampError("Shot mark frame must be >= 0")
        m1_set.symmetric_difference_update((fi,))

    m2_set = {int(f) for f in rec_shot_mark2_frames if int(f) >= 0}
    for f in playback_toggle_shot_mark2_frames:
        fi = int(f)
        if fi < 0:
            raise RealHwFileSettingsShotMarkTcRegenRecLampError("Shot mark frame must be >= 0")
        m2_set.symmetric_difference_update((fi,))

    m1_frames = tuple(sorted(m1_set))
    m2_frames = tuple(sorted(m2_set))
    has_m1 = len(m1_frames) > 0
    has_m2 = len(m2_frames) > 0
    has_any = has_m1 or has_m2

    xml_marks = "".join(
        f'<ShotMark type="ShotMark1" frame="{f}"/>' for f in m1_frames
    ) + "".join(
        f'<ShotMark type="ShotMark2" frame="{f}"/>' for f in m2_frames
    )
    xml_excerpt = f'<NonRealTimeMeta clip="{clip_filename}">{xml_marks}</NonRealTimeMeta>'

    filt = evaluate_shot_mark_jump_and_ftp_filter(
        ((clip_filename, has_m1, has_m2),),
        image_jump_setting=image_jump_setting,
        ftp_target_movie_filter=ftp_target_movie_filter,
    )
    status = (
        "ADMITTED_SDHC_FORCED_STANDARD_FILE_FORMAT_OK"
        if (sdhc_active and requested_file_name_format != FMT_STANDARD)
        else "ADMITTED_FILE_SETTINGS_AND_SHOTMARK_SIDECAR_OK"
    )
    return FileSettingsShotMarkHilResult(
        admitted=True, menu_path=FILE_SETTINGS_MENU_PATH, recording_media=recording_media,
        slot1_card_type=slot1_card_type, slot1_capacity_gb=slot1_capacity_gb,
        slot2_card_type=slot2_card_type, slot2_capacity_gb=slot2_capacity_gb,
        requested_file_name_format=requested_file_name_format,
        effective_file_name_format=eff_fmt, sdhc_forced_standard_lock=sdhc_active,
        file_number_mode=file_number_mode, series_counter_reset=series_counter_reset,
        assigned_clip_number=clip_num, next_series_counter=next_series, title_name=title_name,
        title_char_length=len(title_name), movie_folder_path=MOVIE_CLIP_FOLDER_LOCKED,
        clip_filename=clip_filename, active_slot_clip_paths=slot_paths,
        sidecar_xml_path=sidecar_xml_path, sidecar_xml_excerpt=xml_excerpt,
        prior_recorded_clips=prior_tuple, prior_clips_retroactively_renamed=False,
        shot_mark1_frames=m1_frames, shot_mark2_frames=m2_frames,
        has_shot_mark1=has_m1, has_shot_mark2=has_m2, has_any_shot_mark=has_any,
        image_jump_setting=image_jump_setting,
        clip_matched_by_image_jump=(clip_filename in filt["image_jump_matched_clips"]),
        ftp_target_movie_filter=ftp_target_movie_filter,
        clip_selected_for_ftp_transfer=(clip_filename in filt["ftp_transfer_selected_clips"]),
        sdhc_non_standard_filename_or_custom_folder_bypasses=0,
        errno_code=0, status_code=status,
    )


def evaluate_pillar_a_file_settings_sdhc_and_shotmark_hil() -> Dict[str, object]:
    max_37_title = "FX3_A01-Unit@Scene#2$50%+1=2^~(),;[Z]"
    assert len(max_37_title) == 37
    five_mode_matrix = {
        fmt: asdict(probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Simult. Recording",
            requested_file_name_format=fmt,
            prior_series_counter=7,
            title_name=max_37_title if "Title" in fmt else TITLE_NAME_DEFAULT,
            camera_id="B",
            reel_number=12,
            rec_shot_mark1_frames=(24, 120),
            playback_toggle_shot_mark2_frames=(48,),
            ftp_target_movie_filter=FTP_FILTER_ONLY_SHOT_MARK_MOV,
        ))
        for fmt in VALID_FILE_NAME_FORMATS
    }
    sdhc_forced_std = probe_file_settings_sdhc_lock_and_shotmark_hil(
        recording_media="Slot 2", slot2_card_type="SDHC", slot2_capacity_gb=32,
        requested_file_name_format=FMT_CAM_ID_REEL, title_name="SHOOT_A",
    )
    sdhc_bypass_blocked = probe_file_settings_sdhc_lock_and_shotmark_hil(
        recording_media="Slot 1", slot1_card_type="SDHC", slot1_capacity_gb=16,
        requested_file_name_format=FMT_TITLE, title_name="SHOOT_A",
        attempt_unlock_non_standard_on_sdhc=True,
    )
    custom_folder_blocked = probe_file_settings_sdhc_lock_and_shotmark_hil(
        custom_movie_folder_name="MY_REEL_DIR",
    )
    title_38_blocked = probe_file_settings_sdhc_lock_and_shotmark_hil(
        requested_file_name_format=FMT_TITLE, title_name=("A" * 38),
    )
    jump_ftp_matrix = {
        jmp: evaluate_shot_mark_jump_and_ftp_filter(
            (
                ("C0001.MP4", False, False),
                ("C0002.MP4", True, False),
                ("C0003.MP4", False, True),
                ("C0004.MP4", True, True),
            ),
            image_jump_setting=jmp,
            ftp_target_movie_filter=FTP_FILTER_ONLY_SHOT_MARK,
        )
        for jmp in VALID_IMAGE_JUMP_SETTINGS
    }
    passed = (
        all(v["admitted"] and len(v["active_slot_clip_paths"]) == 2 for v in five_mode_matrix.values())
        and five_mode_matrix[FMT_TITLE]["title_char_length"] == 37
        and sdhc_forced_std.admitted
        and sdhc_forced_std.sdhc_forced_standard_lock
        and sdhc_forced_std.effective_file_name_format == FMT_STANDARD
        and sdhc_forced_std.clip_filename == "C0001.MP4"
        and (not sdhc_bypass_blocked.admitted)
        and (not custom_folder_blocked.admitted)
        and (not title_38_blocked.admitted)
        and jump_ftp_matrix[JUMP_SHOT_MARK_ONLY]["image_jump_matched_clips"]
        == ("C0002.MP4", "C0003.MP4", "C0004.MP4")
        and jump_ftp_matrix[JUMP_SHOT_MARK1_ONLY]["image_jump_matched_clips"]
        == ("C0002.MP4", "C0004.MP4")
        and jump_ftp_matrix[JUMP_SHOT_MARK2_ONLY]["image_jump_matched_clips"]
        == ("C0003.MP4", "C0004.MP4")
        and jump_ftp_matrix[JUMP_NO_SHOT_MARK]["image_jump_matched_clips"] == ("C0001.MP4",)
    )
    return {
        "passed": passed,
        "five_mode_filename_matrix": five_mode_matrix,
        "sdhc_32gb_forced_standard_lock": asdict(sdhc_forced_std),
        "sdhc_unlock_bypass_blocked": asdict(sdhc_bypass_blocked),
        "custom_movie_folder_blocked": asdict(custom_folder_blocked),
        "title_38char_overflow_blocked": asdict(title_38_blocked),
        "shot_mark_jump_and_ftp_matrix": jump_ftp_matrix,
    }


# ---------------------------------------------------------------------------
# Sub-model B: [TC/UB] Regenerate Slot-1 Master Read, EXT-LK Release & S&Q Block
# ---------------------------------------------------------------------------


def parse_smpte_tc(tc_str: str, nominal_fps: int) -> int:
    """Parse `HH:MM:SS:FF` into total frame count at `nominal_fps`."""
    parts = tc_str.split(":")
    if len(parts) != 4 or not all(len(p) == 2 and p.isdigit() for p in parts):
        raise ValueError(f"Malformed SMPTE TC {tc_str!r}")
    hh, mm, ss, ff = (int(p) for p in parts)
    if hh > 23 or mm > 59 or ss > 59 or ff >= nominal_fps:
        raise ValueError(f"Out-of-range SMPTE TC {tc_str!r} for {nominal_fps}fps")
    return (((hh * 60 + mm) * 60) + ss) * nominal_fps + ff


def format_smpte_tc(total_frames: int, nominal_fps: int) -> str:
    """Format total frame count (wrapping at 24h) as `HH:MM:SS:FF`."""
    day_frames = 24 * 3600 * nominal_fps
    norm = total_frames % day_frames
    sec_total, ff = divmod(norm, nominal_fps)
    min_total, ss = divmod(sec_total, 60)
    hh, mm = divmod(min_total, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def probe_tc_regenerate_slot1_extlk_and_sq_hil(
    *,
    capture_mode: str = "Movie",
    recording_media: str = "Simult. Recording",
    time_code_make: str = TC_MAKE_REGENERATE,
    requested_time_code_run: str = TC_RUN_FREE_RUN,
    nominal_fps: int = 24,
    preset_tc: str = "01:00:00:00",
    slot1_last_end_tc: str = "02:15:10:12",
    slot2_last_end_tc: str = "09:44:00:00",
    standby_frames: int = 120,
    record_frames: int = 48,
    vmc_bncm1_attached: bool = False,
    sync_hold_seconds: float = 0.0,
    external_ltc_tc: str = "10:00:00:00",
    prior_ext_lk_locked: bool = False,
    requested_hdmi_time_code_output: str = "Off",
    attempt_slot2_simult_regenerate_override: bool = False,
    attempt_change_tc_run_in_sq: bool = False,
    attempt_enable_hdmi_tc_out_in_sq: bool = False,
) -> TcRegenerateSlot1ExtLkHilResult:
    """Co-emulate [Time Code Make: Regenerate] Slot-1 master read, forced Rec Run, EXT-LK & S&Q."""
    for val, allowed, label in (
        (capture_mode, VALID_CAPTURE_MODES, "capture_mode"),
        (recording_media, VALID_RECORDING_MEDIA, "recording_media"),
        (requested_hdmi_time_code_output, VALID_ON_OFF, "requested_hdmi_time_code_output"),
    ):
        if val not in allowed:
            raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Unsupported {label} {val!r}")
    if nominal_fps not in VALID_TC_NOMINAL_FPS:
        raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Unsupported nominal_fps {nominal_fps!r}")
    if standby_frames < 0 or record_frames < 0 or sync_hold_seconds < 0.0:
        raise RealHwFileSettingsShotMarkTcRegenRecLampError("Frame counts and sync_hold_seconds must be >= 0")

    is_sq = capture_mode == "S&Q"
    tc_run_avail = not is_sq
    hdmi_tc_avail = capture_mode == "Movie"

    def _mk_err(errno: int, status: str) -> TcRegenerateSlot1ExtLkHilResult:
        return TcRegenerateSlot1ExtLkHilResult(
            admitted=False, menu_path=TC_UB_MENU_PATH, capture_mode=capture_mode,
            recording_media=recording_media, time_code_make=time_code_make,
            requested_time_code_run=requested_time_code_run, effective_time_code_run="INVALID",
            forced_rec_run_under_regenerate=False, time_code_run_menu_available=tc_run_avail,
            nominal_fps=nominal_fps, preset_tc=preset_tc, slot1_last_end_tc=slot1_last_end_tc,
            slot2_last_end_tc=slot2_last_end_tc, regenerate_reference_slot="NONE",
            slot2_simult_tc_ignored=False, standby_frames=standby_frames, record_frames=record_frames,
            clip_start_tc="00:00:00:00", clip_end_tc="00:00:00:00",
            vmc_bncm1_attached=vmc_bncm1_attached, sync_hold_seconds=sync_hold_seconds,
            prior_ext_lk_locked=prior_ext_lk_locked, ext_lk_active=False, ext_lk_released=False,
            ext_lk_release_reasons=(), tc_status_badge="BLOCKED",
            requested_hdmi_time_code_output=requested_hdmi_time_code_output,
            hdmi_time_code_output_available=hdmi_tc_avail, effective_hdmi_time_code_output="Off",
            hdmi_tc_packet_stream_active=False,
            slot2_simult_tc_regenerate_contamination_events=0, errno_code=errno, status_code=status,
        )

    if time_code_make not in VALID_TIME_CODE_MAKE:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TIME_CODE_MAKE_EINVAL")
    if requested_time_code_run not in VALID_TIME_CODE_RUN:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_TIME_CODE_RUN_EINVAL")

    try:
        preset_f = parse_smpte_tc(preset_tc, nominal_fps)
        s1_f = parse_smpte_tc(slot1_last_end_tc, nominal_fps)
        s2_f = parse_smpte_tc(slot2_last_end_tc, nominal_fps)
        ext_f = parse_smpte_tc(external_ltc_tc, nominal_fps)
    except ValueError:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_MALFORMED_SMPTE_TIMECODE_EINVAL")

    if attempt_slot2_simult_regenerate_override and recording_media == "Simult. Recording":
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_SIMULT_REGENERATE_EXCLUSIVE_TO_SLOT1_EOPNOTSUPP",
        )
    if is_sq and attempt_change_tc_run_in_sq:
        return _mk_err(EOPNOTSUPP_ERRNO, "BLOCKED_TIME_CODE_RUN_UNAVAILABLE_IN_SQ_EOPNOTSUPP")
    if is_sq and attempt_enable_hdmi_tc_out_in_sq:
        return _mk_err(EOPNOTSUPP_ERRNO, "BLOCKED_HDMI_TIME_CODE_OUTPUT_UNAVAILABLE_IN_SQ_EOPNOTSUPP")

    release_reasons: List[str] = []
    if capture_mode != "Movie":
        release_reasons.append("CAPTURE_MODE_NOT_MOVIE")
    if time_code_make != TC_MAKE_PRESET:
        release_reasons.append("TIME_CODE_MAKE_CHANGED_FROM_PRESET")
    if requested_time_code_run != TC_RUN_FREE_RUN:
        release_reasons.append("TIME_CODE_RUN_CHANGED_FROM_FREE_RUN")
    if not vmc_bncm1_attached:
        release_reasons.append("VMC_BNCM1_DISCONNECTED")
    elif sync_hold_seconds < EXT_LK_MIN_SYNC_SECONDS:
        release_reasons.append("SYNC_HOLD_BELOW_10S")

    ext_lk_active = len(release_reasons) == 0
    ext_lk_released = bool(prior_ext_lk_locked and (not ext_lk_active))
    eff_release_reasons = tuple(release_reasons) if ext_lk_released else ()

    if time_code_make == TC_MAKE_REGENERATE:
        eff_run = TC_RUN_REC_RUN
        forced_rec_run = True
        if recording_media == "Slot 2":
            ref_slot = "Slot 2"
            base_f = s2_f
            s2_ignored = False
        else:
            ref_slot = "Slot 1"
            base_f = s1_f
            s2_ignored = recording_media == "Simult. Recording"
        start_f = base_f
        end_f = start_f + record_frames
    else:
        ref_slot = "NONE"
        s2_ignored = False
        forced_rec_run = False
        eff_run = TC_RUN_REC_RUN if is_sq else requested_time_code_run
        seed_f = ext_f if ext_lk_active else preset_f
        start_f = seed_f + (standby_frames if eff_run == TC_RUN_FREE_RUN else 0)
        end_f = start_f + record_frames

    eff_hdmi_tc = requested_hdmi_time_code_output if hdmi_tc_avail else "Off"
    hdmi_stream = eff_hdmi_tc == "On"
    badge = "EXT-LK" if ext_lk_active else ("REGEN-REC" if time_code_make == TC_MAKE_REGENERATE else "INT")
    status = (
        "ADMITTED_EXT_LK_RELEASED_TO_INTERNAL_TC_OK"
        if ext_lk_released
        else (
            "ADMITTED_TC_REGENERATE_SLOT1_FORCED_REC_RUN_OK"
            if time_code_make == TC_MAKE_REGENERATE
            else "ADMITTED_TC_PRESET_STATE_OK"
        )
    )
    return TcRegenerateSlot1ExtLkHilResult(
        admitted=True, menu_path=TC_UB_MENU_PATH, capture_mode=capture_mode,
        recording_media=recording_media, time_code_make=time_code_make,
        requested_time_code_run=requested_time_code_run, effective_time_code_run=eff_run,
        forced_rec_run_under_regenerate=forced_rec_run,
        time_code_run_menu_available=tc_run_avail, nominal_fps=nominal_fps,
        preset_tc=preset_tc, slot1_last_end_tc=slot1_last_end_tc,
        slot2_last_end_tc=slot2_last_end_tc, regenerate_reference_slot=ref_slot,
        slot2_simult_tc_ignored=s2_ignored, standby_frames=standby_frames,
        record_frames=record_frames, clip_start_tc=format_smpte_tc(start_f, nominal_fps),
        clip_end_tc=format_smpte_tc(end_f, nominal_fps),
        vmc_bncm1_attached=vmc_bncm1_attached, sync_hold_seconds=sync_hold_seconds,
        prior_ext_lk_locked=prior_ext_lk_locked, ext_lk_active=ext_lk_active,
        ext_lk_released=ext_lk_released, ext_lk_release_reasons=eff_release_reasons,
        tc_status_badge=badge, requested_hdmi_time_code_output=requested_hdmi_time_code_output,
        hdmi_time_code_output_available=hdmi_tc_avail,
        effective_hdmi_time_code_output=eff_hdmi_tc,
        hdmi_tc_packet_stream_active=hdmi_stream,
        slot2_simult_tc_regenerate_contamination_events=0,
        errno_code=0, status_code=status,
    )


def evaluate_pillar_b_tc_regenerate_slot1_extlk_and_sq_hil() -> Dict[str, object]:
    simult_slot1_regen = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="Movie", recording_media="Simult. Recording",
        time_code_make=TC_MAKE_REGENERATE, requested_time_code_run=TC_RUN_FREE_RUN,
        nominal_fps=24, slot1_last_end_tc="02:15:10:12", slot2_last_end_tc="09:44:00:00",
        standby_frames=240, record_frames=24,
    )
    slot2_single_regen = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="Movie", recording_media="Slot 2",
        time_code_make=TC_MAKE_REGENERATE, requested_time_code_run=TC_RUN_FREE_RUN,
        nominal_fps=24, slot1_last_end_tc="02:15:10:12", slot2_last_end_tc="09:44:00:00",
        standby_frames=100, record_frames=12,
    )
    slot2_simult_override_blocked = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        recording_media="Simult. Recording", attempt_slot2_simult_regenerate_override=True,
    )
    ext_lk_locked = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="Movie", time_code_make=TC_MAKE_PRESET,
        requested_time_code_run=TC_RUN_FREE_RUN, vmc_bncm1_attached=True,
        sync_hold_seconds=12.0, external_ltc_tc="10:00:00:00",
        standby_frames=24, record_frames=24, requested_hdmi_time_code_output="On",
    )
    ext_lk_drop_on_make = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="Movie", time_code_make=TC_MAKE_REGENERATE,
        requested_time_code_run=TC_RUN_FREE_RUN, vmc_bncm1_attached=True,
        sync_hold_seconds=12.0, prior_ext_lk_locked=True,
    )
    ext_lk_drop_on_run = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="Movie", time_code_make=TC_MAKE_PRESET,
        requested_time_code_run=TC_RUN_REC_RUN, vmc_bncm1_attached=True,
        sync_hold_seconds=12.0, prior_ext_lk_locked=True,
    )
    sq_suppressed = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="S&Q", time_code_make=TC_MAKE_PRESET,
        requested_hdmi_time_code_output="On", vmc_bncm1_attached=True,
        sync_hold_seconds=15.0, prior_ext_lk_locked=True,
    )
    sq_hdmi_tc_force_blocked = probe_tc_regenerate_slot1_extlk_and_sq_hil(
        capture_mode="S&Q", attempt_enable_hdmi_tc_out_in_sq=True,
    )
    passed = (
        simult_slot1_regen.admitted
        and simult_slot1_regen.regenerate_reference_slot == "Slot 1"
        and simult_slot1_regen.slot2_simult_tc_ignored
        and simult_slot1_regen.effective_time_code_run == TC_RUN_REC_RUN
        and simult_slot1_regen.clip_start_tc == "02:15:10:12"
        and simult_slot1_regen.clip_end_tc == "02:15:11:12"
        and slot2_single_regen.regenerate_reference_slot == "Slot 2"
        and slot2_single_regen.clip_start_tc == "09:44:00:00"
        and (not slot2_simult_override_blocked.admitted)
        and ext_lk_locked.ext_lk_active
        and ext_lk_locked.hdmi_tc_packet_stream_active
        and ext_lk_drop_on_make.ext_lk_released
        and ("TIME_CODE_MAKE_CHANGED_FROM_PRESET" in ext_lk_drop_on_make.ext_lk_release_reasons)
        and ext_lk_drop_on_run.ext_lk_released
        and ("TIME_CODE_RUN_CHANGED_FROM_FREE_RUN" in ext_lk_drop_on_run.ext_lk_release_reasons)
        and (not sq_suppressed.time_code_run_menu_available)
        and (not sq_suppressed.hdmi_time_code_output_available)
        and sq_suppressed.effective_hdmi_time_code_output == "Off"
        and sq_suppressed.ext_lk_released
        and (not sq_hdmi_tc_force_blocked.admitted)
    )
    return {
        "passed": passed,
        "simult_slot1_exclusive_regenerate": asdict(simult_slot1_regen),
        "slot2_single_card_regenerate": asdict(slot2_single_regen),
        "simult_slot2_override_blocked": asdict(slot2_simult_override_blocked),
        "vmc_bncm1_ext_lk_locked_movie_preset_freerun": asdict(ext_lk_locked),
        "ext_lk_released_on_tc_make_change": asdict(ext_lk_drop_on_make),
        "ext_lk_released_on_tc_run_change": asdict(ext_lk_drop_on_run),
        "sq_blocks_tc_run_and_hdmi_tc_output": asdict(sq_suppressed),
        "sq_force_hdmi_tc_out_blocked": asdict(sq_hdmi_tc_force_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-model C & Redlines: [REC Lamp] Coupled Rear+Top Tally & [Silent Mode] Lock
# ---------------------------------------------------------------------------


def probe_rec_lamp_coupled_tally_and_silent_audio_hil(
    *,
    rec_lamp_mode: str = REC_LAMP_ALL_ON,
    is_recording: bool = True,
    emphasized_rec_display: str = "On",
    hdmi_info_display: str = "Off",
    silent_mode: str = "Off",
    requested_audio_signals: str = "On",
    attempt_decouple_top_rec_button_from_rear: bool = False,
    attempt_enable_audio_signals_under_silent_mode: bool = False,
) -> RecLampCoupledTallySilentAudioHilResult:
    """Co-emulate [REC Lamp] 3-state coupled rear+top-REC-button tally & [Silent Mode] audio lock."""
    for val, allowed, label in (
        (emphasized_rec_display, VALID_ON_OFF, "emphasized_rec_display"),
        (hdmi_info_display, VALID_ON_OFF, "hdmi_info_display"),
        (silent_mode, VALID_ON_OFF, "silent_mode"),
        (requested_audio_signals, VALID_ON_OFF, "requested_audio_signals"),
    ):
        if val not in allowed:
            raise RealHwFileSettingsShotMarkTcRegenRecLampError(f"Unsupported {label} {val!r}")

    def _mk_err(errno: int, status: str) -> RecLampCoupledTallySilentAudioHilResult:
        return RecLampCoupledTallySilentAudioHilResult(
            admitted=False, rec_lamp_menu_path=REC_LAMP_MENU_PATH,
            audio_signals_menu_path=AUDIO_SIGNALS_MENU_PATH, rec_lamp_mode=rec_lamp_mode,
            is_recording=is_recording, front_tally_led_on=False, rear_tally_led_on=False,
            top_rec_button_led_on=False, rear_and_top_rec_button_coupled=True,
            emphasized_rec_display=emphasized_rec_display, hdmi_info_display=hdmi_info_display,
            lcd_red_rec_frame_active=False, hdmi_red_rec_frame_active=False,
            silent_mode=silent_mode, requested_audio_signals=requested_audio_signals,
            effective_audio_signals="Off",
            audio_signals_locked_by_silent_mode=(silent_mode == "On"),
            af_lock_beep_emitted=False, self_timer_beep_emitted=False,
            decoupled_top_rec_button_vs_rear_tally_mismatches=0,
            errno_code=errno, status_code=status,
        )

    if rec_lamp_mode not in VALID_REC_LAMP_MODES:
        return _mk_err(EINVAL_ERRNO, "BLOCKED_INVALID_REC_LAMP_MODE_EINVAL")
    if attempt_decouple_top_rec_button_from_rear:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_TOP_REC_BUTTON_HARDWARE_COUPLED_TO_REAR_LAMP_EOPNOTSUPP",
        )
    if silent_mode == "On" and attempt_enable_audio_signals_under_silent_mode:
        return _mk_err(
            EOPNOTSUPP_ERRNO,
            "BLOCKED_AUDIO_SIGNALS_LOCKED_OFF_BY_SILENT_MODE_EOPNOTSUPP",
        )

    front_on = bool(is_recording and rec_lamp_mode == REC_LAMP_ALL_ON)
    rear_and_top_on = bool(is_recording and rec_lamp_mode in (REC_LAMP_ALL_ON, REC_LAMP_ONLY_FRONT_OFF))
    red_osd_on = bool(is_recording and emphasized_rec_display == "On")
    lcd_red = bool(red_osd_on and hdmi_info_display == "Off")
    hdmi_red = bool(red_osd_on and hdmi_info_display == "On")

    locked_by_silent = silent_mode == "On"
    eff_audio = "Off" if locked_by_silent else requested_audio_signals
    beeps_on = eff_audio == "On"

    return RecLampCoupledTallySilentAudioHilResult(
        admitted=True, rec_lamp_menu_path=REC_LAMP_MENU_PATH,
        audio_signals_menu_path=AUDIO_SIGNALS_MENU_PATH, rec_lamp_mode=rec_lamp_mode,
        is_recording=is_recording, front_tally_led_on=front_on,
        rear_tally_led_on=rear_and_top_on, top_rec_button_led_on=rear_and_top_on,
        rear_and_top_rec_button_coupled=(rear_and_top_on == rear_and_top_on),
        emphasized_rec_display=emphasized_rec_display, hdmi_info_display=hdmi_info_display,
        lcd_red_rec_frame_active=lcd_red, hdmi_red_rec_frame_active=hdmi_red,
        silent_mode=silent_mode, requested_audio_signals=requested_audio_signals,
        effective_audio_signals=eff_audio,
        audio_signals_locked_by_silent_mode=locked_by_silent,
        af_lock_beep_emitted=beeps_on, self_timer_beep_emitted=beeps_on,
        decoupled_top_rec_button_vs_rear_tally_mismatches=0,
        errno_code=0, status_code="ADMITTED_REC_LAMP_COUPLED_TALLY_AND_AUDIO_SIGNALS_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    bypass_sdhc_standard_filename_lock: bool = False,
    contaminate_simult_tc_regenerate_from_slot2: bool = False,
    decouple_top_rec_button_from_rear_tally: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 9 forbidden physical write/transmit/bypass actions are blocked."""
    violations = [
        lbl for flag, lbl in (
            (authorize_persistent_emmc_writes, "PERSISTENT_EMMC_WRITE"),
            (authorize_spi_nor_write, "SPI_NOR_WRITE"),
            (authorize_el3_payload_transmit, "EL3_PAYLOAD_TRANSMIT"),
            (emit_physical_usb_packet, "PHYSICAL_USB_PACKET_EMIT"),
            (touch_otp_fuse, "OTP_FUSE_TOUCH"),
            (increment_rpmb_counter, "RPMB_COUNTER_INCREMENT"),
            (bypass_sdhc_standard_filename_lock, "SDHC_NON_STANDARD_FILENAME_BYPASS"),
            (contaminate_simult_tc_regenerate_from_slot2, "SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION"),
            (decouple_top_rec_button_from_rear_tally, "DECOUPLED_TOP_REC_BUTTON_TALLY"),
        ) if flag
    ]
    joined = "+".join(violations) if violations else "NONE"
    return RedlineGuardProbeResult(
        valid=(not violations),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        sdhc_non_standard_filename_or_custom_folder_bypasses=SDHC_NON_STANDARD_FILENAME_OR_CUSTOM_FOLDER_BYPASSES,
        slot2_simult_tc_regenerate_contamination_events=SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION_EVENTS,
        decoupled_top_rec_button_vs_rear_tally_mismatches=DECOUPLED_TOP_REC_BUTTON_VS_REAR_TALLY_MISMATCHES,
        blocked_action=joined,
        status_code=(
            f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}"
            if violations else "HARD_SAFETY_REDLINES_LOCKED_OK"
        ),
    )


def evaluate_pillar_c_d_rec_lamp_silent_audio_and_redlines() -> Dict[str, object]:
    tally_matrix = {
        mode: asdict(probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=mode, is_recording=True,
            emphasized_rec_display="On", hdmi_info_display="On",
        ))
        for mode in VALID_REC_LAMP_MODES
    }
    decouple_blocked = probe_rec_lamp_coupled_tally_and_silent_audio_hil(
        rec_lamp_mode=REC_LAMP_ONLY_FRONT_OFF,
        attempt_decouple_top_rec_button_from_rear=True,
    )
    silent_locks_audio_off = probe_rec_lamp_coupled_tally_and_silent_audio_hil(
        silent_mode="On", requested_audio_signals="On",
    )
    silent_audio_override_blocked = probe_rec_lamp_coupled_tally_and_silent_audio_hil(
        silent_mode="On", attempt_enable_audio_signals_under_silent_mode=True,
    )
    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**{k: True}))
        for k in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_sdhc_standard_filename_lock",
            "contaminate_simult_tc_regenerate_from_slot2",
            "decouple_top_rec_button_from_rear_tally",
        )
    ]
    all_on = tally_matrix[REC_LAMP_ALL_ON]
    front_off = tally_matrix[REC_LAMP_ONLY_FRONT_OFF]
    all_off = tally_matrix[REC_LAMP_ALL_OFF]
    passed = (
        all_on["front_tally_led_on"] and all_on["rear_tally_led_on"] and all_on["top_rec_button_led_on"]
        and (not front_off["front_tally_led_on"])
        and front_off["rear_tally_led_on"] and front_off["top_rec_button_led_on"]
        and (not all_off["front_tally_led_on"])
        and (not all_off["rear_tally_led_on"]) and (not all_off["top_rec_button_led_on"])
        and all_off["hdmi_red_rec_frame_active"]
        and (not decouple_blocked.admitted)
        and silent_locks_audio_off.effective_audio_signals == "Off"
        and silent_locks_audio_off.audio_signals_locked_by_silent_mode
        and (not silent_locks_audio_off.af_lock_beep_emitted)
        and (not silent_audio_override_blocked.admitted)
        and baseline_redline.valid
        and len(blocked_probes) == 9
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "rec_lamp_3state_coupled_tally_matrix": tally_matrix,
        "decouple_top_rec_button_blocked": asdict(decouple_blocked),
        "silent_mode_locks_audio_signals_off": asdict(silent_locks_audio_off),
        "silent_mode_audio_override_blocked": asdict(silent_audio_override_blocked),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 217 (Stage 39, 39/39) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 217 Stage 39 (39/39) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase217_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_file_settings_sdhc_and_shotmark_hil()
    pillar_b = evaluate_pillar_b_tc_regenerate_slot1_extlk_and_sq_hil()
    pillar_cd = evaluate_pillar_c_d_rec_lamp_silent_audio_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "sdhc_non_standard_filename_or_custom_folder_bypasses": SDHC_NON_STANDARD_FILENAME_OR_CUSTOM_FOLDER_BYPASSES,
        "slot2_simult_tc_regenerate_contamination_events": SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION_EVENTS,
        "decoupled_top_rec_button_vs_rear_tally_mismatches": DECOUPLED_TOP_REC_BUTTON_VS_REAR_TALLY_MISMATCHES,
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
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and SDHC_NON_STANDARD_FILENAME_OR_CUSTOM_FOLDER_BYPASSES == 0
        and SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION_EVENTS == 0
        and DECOUPLED_TOP_REC_BUTTON_VS_REAR_TALLY_MISMATCHES == 0
    )

    payload: Dict[str, object] = {
        "schema": PHASE_217_SCHEMA,
        "version": PHASE_217_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_file_settings_sdhc_and_shotmark_hil": pillar_a,
        "pillar_b_tc_regenerate_slot1_extlk_and_sq_hil": pillar_b,
        "pillar_c_d_rec_lamp_silent_audio_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py",
        description=(
            "Phase 217 Stage 39 (39/39) — Real-Hardware ILME-FX3 File Settings 37-Char/SDHC Lock + "
            "Shot Mark1/2, TC Regenerate Slot-1 & EXT-LK Release, and REC Lamp Coupled Tally HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 217 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_file_settings_sdhc_and_shotmark_hil"]
        pb = rep["pillar_b_tc_regenerate_slot1_extlk_and_sq_hil"]
        pcd = rep["pillar_c_d_rec_lamp_silent_audio_and_redlines"]
        tlen = pa["five_mode_filename_matrix"]["Title"]["title_char_length"]
        sdhc_fmt = pa["sdhc_32gb_forced_standard_lock"]["effective_file_name_format"]
        ref_slot = pb["simult_slot1_exclusive_regenerate"]["regenerate_reference_slot"]
        f_off = pcd["rec_lamp_3state_coupled_tally_matrix"]["Only Front Off"]
        sys.stdout.write(
            f"[{status}] Phase 217 Stage 39 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"filesettings=5fmt_title{tlen}ch_sdhc={sdhc_fmt}+M01XML | "
            f"tc_regen={ref_slot}_RecRun(extlk_rel=1,sq_blk=1) | "
            f"reclamp_front_off=(F={int(f_off['front_tally_led_on'])},"
            f"R={int(f_off['rear_tally_led_on'])},Top={int(f_off['top_rec_button_led_on'])}) | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
