"""Phase 218 (45th Milestone Auditor, 45/45): Real-Hardware `ILME-FX3` (`Ver. 7.02`)
`File Settings` 37-Char/SDHC Lock + `Shot Mark1/2`, `TC Regenerate` Slot-1 & `EXT-LK`
Release, and `REC Lamp` Coupled Rear+Top Tally Auditor.

Strictly `os.O_RDONLY` + bounded `os.pread` (`< 0.15s` cold budget, cached per process,
with deterministic synthetic Clean-Room fallback under `FX3_FX6_FORCE_CLEAN_ROOM=1` or
`clean_room=True`), zero raw firmware byte leakage (`raw_firmware_bytes_leaked = 0`),
and zero persistent eMMC / SPI-NOR / USB / EL3 mutations (`persistent_emmc_writes_authorized = False`).

Audits four Wave-29 hardware pillars across Stock `ILME-FX3` (`Ver. 7.02`) vs `ILME-FX6` (`Ver. 6.01`):
  1. Pillar A — `[File Settings]` (`Standard`, `Cam ID + Reel#`, `Title`, `Date + Title`,
     `Title + Date` across Slot 1 & Slot 2; `[File Number]` `Series`/`Reset` +
     `[Series Counter Reset]`; `[Title Name Settings]` `<= 37` ASCII allowed characters
     applied strictly to subsequent clips; SDHC `<= 32 GB` FAT32 forced lock to `[Standard]`
     + custom movie folder prohibition) and `Shot Mark1/2` (`*M01.XML` non-real-time metadata,
     `[Image Jump Setting]`, and `[Only Shot Mark Mov.]` FTP / smartphone transfer filter).
  2. Pillar B — `[TC/UB]` `[Time Code Make: Regenerate]` reading ending TC from active card
     (and exclusively from **Slot 1** under `[Simult. Recording]`) while forcing `[Rec Run]`
     advancement regardless of `[Time Code Run]`, immediate `VMC-BNCM1` `EXT-LK` (`Movie` +
     `Preset` + `Free Run`) release when switching `[Time Code Make]` or `[Time Code Run]`,
     and `S&Q` lockout of `[Time Code Run]` + HDMI `[Time Code Output]`.
  3. Pillar C — Physical `[REC Lamp]` 3-state topology (`All On`, `Only Front Off` keeping
     BOTH rear lamp and top `REC` button LED lit in lockstep, `All Off` with independent
     `[Emphasized REC Display]` red OSD / HDMI frame when `[HDMI Info. Display] = [On]`)
     and `[Silent Mode] = [On]` -> `[Audio signals] = [Off]` hard lock.
  4. Pillar D — Hard Zero-Write Firewall & 12-Touchpoint (`P218-01..P218-12`) 4-Class Matrix.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor import (
    _scan_elf_buf_ordered,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
)

PHASE_218_SCHEMA = (
    "fx3-firmware-lab.realhw-filesettings-shotmark-tcregen-and-reclamp/v1"
)
PHASE_218_VERSION = "218.0.0"
AUDITOR_INDEX_P218 = "45/45"

FX3_APPFW_P218_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P218_RELPATH = FX6_APPFW_P146_RELPATH
FX3_UXC_EN_F_P218_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_f.uxc"
FX6_UXC_EN_P218_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX3_CPAPP_P218_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P218_RELPATH = FX6_CPAPP_P146_RELPATH

EXPECTED_FX3_APPFW_BYTES_P218 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P218 = 50_520_424
EXPECTED_FX3_UXC_EN_F_BYTES_P218 = 373_820
EXPECTED_FX6_UXC_EN_BYTES_P218 = 118_208
EXPECTED_FX3_CPAPP_BYTES_P218 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P218 = 17_952_816

CPAPP_BOUNDED_HEAD_BYTES_P218 = 768 * 1024
CPAPP_BOUNDED_TAIL_BYTES_P218 = 6 * 1024 * 1024
DONOR_COLD_SCAN_BUDGET_SEC_P218 = 0.15

# Pillar A: File Settings (5 formats, File Number, <=37 ASCII Title, SDHC Lock) & Shot Mark1/2
FX3_FILE_SETTINGS_MENU_PATH_P218 = "MENU -> Shooting -> [File] -> [File Settings]"
FX3_IMAGE_JUMP_MENU_PATH_P218 = "MENU -> Playback -> [Playback Option] -> [Image Jump Setting]"

VALID_FILE_NAME_FORMATS_P218: Tuple[str, ...] = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
VALID_FILE_NUMBER_MODES_P218: Tuple[str, ...] = ("Series", "Reset")
DEFAULT_TITLE_NAME_P218 = "C"
MAX_TITLE_NAME_ASCII_CHARS_P218 = 37
TITLE_ALLOWED_SYMBOLS_P218 = ".-_@!#$%+=^~(),;[]"
TITLE_ALLOWED_ASCII_SET_P218 = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    + TITLE_ALLOWED_SYMBOLS_P218
)
SDHC_MAX_CAPACITY_GB_P218 = 32
VALID_MEDIA_FILESYSTEM_CARDS_P218: Tuple[str, ...] = (
    "SDHC_FAT32",
    "SDXC_EXFAT",
    "CFEXPRESS_A_EXFAT",
    "NONE",
)
DEFAULT_MOVIE_CLIP_DIR_P218 = "/PRIVATE/M4ROOT/CLIP"
SHOTMARK_NRTM_SUFFIX_P218 = "M01.XML"

VALID_IMAGE_JUMP_MODES_P218: Tuple[str, ...] = (
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
)
VALID_FTP_SHOTMARK_FILTERS_P218: Tuple[str, ...] = (
    "All",
    "Only Shot Mark Mov.",
    "Only Shot Mark",
)
VALID_SHOTMARK_EDIT_OPS_P218: Tuple[str, ...] = (
    "NONE",
    "LIVE_ADD_MARK1",
    "LIVE_ADD_MARK2",
    "LIVE_ADD_BOTH",
    "TOGGLE_MARK1",
    "TOGGLE_MARK2",
)

# Pillar B: TC/UB [Time Code Make: Regenerate] Slot-1 Master Read, Forced Rec Run & EXT-LK Release
FX3_TC_MAKE_MENU_PATH_P218 = "MENU -> Shooting -> [TC/UB] -> [Time Code Make]"
FX3_HDMI_TC_OUTPUT_MENU_PATH_P218 = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]"
)
VALID_TC_MAKE_MODES_P218: Tuple[str, ...] = ("Preset", "Regenerate")
VALID_TC_RUN_MODES_P218: Tuple[str, ...] = ("Rec Run", "Free Run")
VALID_RECORDING_MEDIA_SLOTS_P218: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
    "Auto Switch Media",
)
VALID_TC_CAPTURE_MODES_P218: Tuple[str, ...] = ("Movie", "S&Q")
VALID_TC_FPS_NOMINAL_FRAMES_P218: Dict[str, int] = {
    "23.98p": 24,
    "24.00p": 24,
    "25p": 25,
    "29.97p": 30,
    "50p": 50,
    "59.94p": 60,
}

# Pillar C: [REC Lamp] 3-State Coupled Rear+Top Tally & [Silent Mode] -> [Audio signals] Off Lock
FX3_REC_LAMP_MENU_PATH_P218 = "MENU -> Setup -> [Setup Option] -> [REC Lamp]"
FX3_AUDIO_SIGNALS_MENU_PATH_P218 = "MENU -> Setup -> [Sound Option] -> [Audio signals]"
FX3_SILENT_MODE_MENU_PATH_P218 = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings] -> [Silent Mode]"
)
VALID_FX3_REC_LAMP_MODES_P218: Tuple[str, ...] = (
    "All On",
    "Only Front Off",
    "All Off",
)
FX3_REC_LAMP_TO_APPFW_ENUM_P218: Dict[str, str] = {
    "All On": "REC_LAMP_ALL_LIGHTS_UP",
    "Only Front Off": "REC_LAMP_ONLY_FRONT_OFF",
    "All Off": "REC_LAMP_ALL_LIGHTS_OUT",
}
FORBIDDEN_NON_FX3_REC_LAMP_MODES_P218: Tuple[str, ...] = (
    "Only Rear Off",
    "Only Top Off",
    "Front Only",
    "Green Preview",
)
VALID_ON_OFF_P218: Tuple[str, ...] = ("On", "Off")
VALID_AUDIO_SIGNALS_SETTINGS_P218: Tuple[str, ...] = ("On", "Off", "Shutter Only")

# Verified Donor Binary Markers
APPFW_SHARED_WAVE29_MARKERS_P218: Tuple[str, ...] = (
    "N5model27setting_xavcs_file_number_tE",
    "N5model30sequence_set_file_number_resetE",
    "N5model22sequence_add_shot_markE",
    "EDIT_SHOT_MARK_TYPE_ADD",
    "EDIT_SHOT_MARK_TYPE_DELETE",
    "AUTO_FTP_TRANSFER_TARGET_MOVIE_MOVIE_SHOT_MARK",
    "N5model39setting_image_jump_setting_front_dial_tE",
    "N5model17setting_tc_make_tE",
    "N5model16setting_tc_run_tE",
    "EXTERN_VAL_TC_MAKE_REGENERATE",
    "VAL_setting_tc_make_TC_MAKE_PRESET",
    "VAL_setting_tc_run_TC_RUN_FREE_RUN",
    "N5model24setting_hdmi_tc_output_tE",
    "N5model18setting_rec_lamp_tE",
    "REC_LAMP_ALL_LIGHTS_UP",
    "REC_LAMP_ONLY_FRONT_OFF",
    "REC_LAMP_ALL_LIGHTS_OUT",
    "N5model21setting_silent_mode_tE",
    "N5model23setting_audio_signals_tE",
)
APPFW_FX3_702_EXCLUSIVE_MARKERS_P218: Tuple[str, ...] = (
    "file_settings_title_name_settings",
    "file_settings_camera_id",
    "file_settings_reel_number",
    "BKID_APP_setting_xavcs_file_name_reel_number",
    "BKID_APP_setting_xavcs_file_number",
    "BKID_APP_setting_ftp_transfer_func_target_img_shot_mark",
    "EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_1_ON",
    "EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_2_ON",
    "BKID_APP_setting_image_jump_setting_front_dial",
    "BKID_APP_setting_tc_make",
    "BKID_APP_setting_tc_run",
    "CAUTION_ID_FACTOR_TC_MAKE_REGENERATE_MSG",
    "No301_EXTLK",
    "BKID_APP_setting_hdmi_tc_output",
    "BKID_APP_setting_rec_lamp",
    "BKID_APP_setting_silent_mode",
    "BKID_APP_setting_audio_signals",
    "VAL_setting_audio_signals_AUDIO_SIGNALS_OFF",
)
APPFW_FX6_601_EXCLUSIVE_MARKERS_P218: Tuple[str, ...] = (
    "set_clip_title_name",
    "BKID_APP_SETTING_TC_MAKE",
    "VAL_setting_tc_make_TC_MAKE_CLOCK",
    "PRM_HAITA_setting_hdmi_tc_output_sdi_output",
    "BKID_APP_SETTING_FRONT_TALLY",
    "BKID_APP_SETTING_REAR_TALLY",
)

UXC_FX3_EN_F_REQUIRED_TOKENS_P218: Tuple[str, ...] = (
    "File Settings",
    "File Name Format",
    "Cam ID + Reel#",
    "Date + Title",
    "Title + Date",
    "Title Name Settings",
    "File Number",
    "Series Counter Reset",
    "Standard",
    "Series",
    "Reset",
    "Add Shot Mark1",
    "Add Shot Mark2",
    "Add/Delete Shot Mark1",
    "Add/Delete Shot Mark2",
    "Image Jump Setting",
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
    "Only Shot Mark Mov.",
    "Simult. Recording",
    "Time Code Make",
    "Regenerate",
    "Preset",
    "Time Code Run",
    "Rec Run",
    "Free Run",
    "Time Code Output",
    "REC Lamp",
    "All On",
    "Only Front Off",
    "All Off",
    "Emphasized REC Display",
    "Silent Mode",
)
UXC_FX6_EN_REQUIRED_TOKENS_P218: Tuple[str, ...] = (
    "Title",
    "Reel",
    "Shot Mark",
    "TC",
    "Regen",
    "Preset",
    "Free Run",
    "Rec Run",
    "Tally",
    "HDMI",
)
CPAPP_SHARED_MARKERS_P218: Tuple[str, ...] = (
    "EXTERNALTC_CHECK",
    "EXTERNALTC_LOCK",
    "cpActTcub",
    "Vitc/LTC/DPACK",
    "TALLY",
    "CLIP",
    "Audio",
    "HDMI",
)

# Pillar D: Zero-Write Firewall
FORBIDDEN_PERSISTENT_TARGET_RE_P218 = re.compile(
    r"(^p2:/setting\b|^p3:/\b|^p5:/wbi\b|^p8:/\b|^p12:/cert\b|^p18:/lens\b"
    r"|/dev/c?p?nflasha\d*\b|spi_nor:|Backup\.bin\b|BODYDATA\.DAT\b|cpapp-b\.bin\b)",
    re.IGNORECASE,
)
VOLATILE_ALLOWED_PREFIXES_P218: Tuple[str, ...] = ("/tmp/", "/tmp_wbshd/", "ram://")
VOLATILE_WAVE29_OVERLAY_DIR_P218 = "/tmp/fx6_wave29_filesettings_tcregen_reclamp_overlay"
_TC_STR_RE_P218 = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[:;](\d{2})$")


@dataclass(frozen=True)
class BoundedUxcSummaryP218:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    header_magic_hex: str
    token_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedCpappSummaryP218:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bounded_bytes_scanned: int
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class FileSettingsAndSdhcLockEvalResult:
    active_slot: str
    slot1_card_type: str
    slot2_card_type: str
    requested_file_name_format: str
    effective_file_name_format: str
    sdhc_card_detected: bool
    sdhc_forced_standard_lock: bool
    file_number_mode: str
    series_counter_reset_triggered: bool
    card_swapped_empty: bool
    next_clip_counter: int
    title_name: str
    title_char_len: int
    custom_movie_folder_requested: bool
    custom_movie_folder_allowed: bool
    effective_movie_clip_dir: str
    generated_clip_filename: str
    generated_nrtm_xml_filename: str
    retroactive_rename_existing_clips: bool
    reason: str


@dataclass(frozen=True)
class ClipShotMarkRecordP218:
    clip_stem: str
    shot_mark1: bool
    shot_mark2: bool
    nrtm_xml_relpath: str


@dataclass(frozen=True)
class ShotMarkXmlJumpAndFtpEvalResult:
    edit_operation: str
    edited_clip_stem: str
    image_jump_mode: str
    ftp_target_movie_filter: str
    clips_after_edit: Tuple[ClipShotMarkRecordP218, ...]
    image_jump_matched_stems: Tuple[str, ...]
    ftp_selected_stems: Tuple[str, ...]
    nrtm_xml_sidecar_updated: bool
    reason: str


@dataclass(frozen=True)
class Pillar1FileSettingsAndShotMarkReport:
    fx3_appfw: ElfSectionSummary
    fx6_appfw: ElfSectionSummary
    fx3_uxc_en_f: BoundedUxcSummaryP218
    fx6_uxc_en: BoundedUxcSummaryP218
    shared_wave29_markers_verified: bool
    fx3_702_exclusive_markers_verified: bool
    five_file_name_formats_dual_slot_verified: bool
    title_37char_ascii_charset_verified: bool
    file_number_series_reset_and_counter_reset_verified: bool
    sdhc_fat32_standard_and_folder_lock_verified: bool
    shotmark_m01_xml_jump_and_ftp_filter_verified: bool
    sample_file_scenarios: Tuple[FileSettingsAndSdhcLockEvalResult, ...]
    sample_shotmark_scenarios: Tuple[ShotMarkXmlJumpAndFtpEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class TcRegenerateAndExtLkEvalResult:
    capture_mode: str
    recording_media: str
    tc_make: str
    requested_tc_run: str
    effective_tc_run: str
    forced_rec_run_by_regenerate: bool
    regenerate_reference_slot: Optional[str]
    slot2_tc_ignored_in_simult: bool
    next_clip_start_tc: str
    vmc_bncm1_ltc_present: bool
    prior_ext_lk_locked: bool
    tc_make_changed: bool
    tc_run_changed: bool
    ext_lk_released: bool
    ext_lk_active_after: bool
    tc_run_menu_available: bool
    hdmi_tc_output_requested: str
    hdmi_tc_output_available: bool
    effective_hdmi_tc_output: str
    reason: str


@dataclass(frozen=True)
class Pillar2TcRegenerateAndExtLkReport:
    fx3_cpapp: BoundedCpappSummaryP218
    fx6_cpapp: BoundedCpappSummaryP218
    regenerate_active_card_continuation_verified: bool
    regenerate_simult_slot1_exclusive_verified: bool
    regenerate_forces_rec_run_verified: bool
    ext_lk_immediate_release_on_tcmake_or_tcrun_verified: bool
    sq_locks_out_tcrun_and_hdmi_tcout_verified: bool
    sample_tc_scenarios: Tuple[TcRegenerateAndExtLkEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class RecLampAndSilentAudioEvalResult:
    rec_lamp_setting: str
    appfw_rec_lamp_enum: str
    is_recording: bool
    front_tally_led_lit: bool
    rear_tally_led_lit: bool
    top_rec_button_led_lit: bool
    rear_and_top_coupled_equal: bool
    emphasized_rec_display: str
    hdmi_connected: bool
    hdmi_info_display: str
    emphasized_rec_on_lcd: bool
    emphasized_rec_on_hdmi: bool
    silent_mode: str
    requested_audio_signals: str
    effective_audio_signals: str
    audio_signals_locked_by_silent_mode: bool
    af_and_selftimer_beeps_emitted: bool
    reason: str


@dataclass(frozen=True)
class Pillar3RecLampAndSilentAudioReport:
    three_rec_lamp_modes_verified: bool
    only_front_off_keeps_rear_and_top_lit_verified: bool
    all_off_preserves_independent_hdmi_red_frame_verified: bool
    silent_mode_locks_audio_signals_off_verified: bool
    sample_reclamp_scenarios: Tuple[RecLampAndSilentAudioEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class Phase218WriteGuardResult:
    target_path: str
    operation: str
    allowed: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    reason: str


@dataclass(frozen=True)
class Phase218TouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx3_702_artifact: str
    fx6_601_artifact: str
    bridge_class: str
    rationale: str


@dataclass(frozen=True)
class Phase218CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    entries: Tuple[Phase218TouchpointEntry, ...]
    all_classes_valid: bool


@dataclass(frozen=True)
class Pillar4Phase218WriteGuardAndMatrixReport:
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    volatile_overlay_dir: str
    guard_evaluations: Tuple[Phase218WriteGuardResult, ...]
    matrix: Phase218CompatMatrixSummary
    passed: bool


@dataclass(frozen=True)
class RealhwFilesettingsShotmarkTcregenAndReclampReport:
    schema: str
    version: str
    auditor_index: str
    source_mode: str
    clean_room_forced: bool
    donor_cold_scan_duration_sec: float
    donor_cold_scan_within_sla: bool
    pillar_1_file_settings_and_shotmark: Pillar1FileSettingsAndShotMarkReport
    pillar_2_tc_regenerate_slot1_and_ext_lk: Pillar2TcRegenerateAndExtLkReport
    pillar_3_rec_lamp_coupled_tally_and_silent_audio: Pillar3RecLampAndSilentAudioReport
    pillar_4_write_guard_and_matrix: Pillar4Phase218WriteGuardAndMatrixReport
    report_digest_sha256: str
    all_checks_passed: bool


_DONOR_SCAN_CACHE_P218: Dict[
    str,
    Tuple[
        ElfSectionSummary,
        ElfSectionSummary,
        BoundedUxcSummaryP218,
        BoundedUxcSummaryP218,
        BoundedCpappSummaryP218,
        BoundedCpappSummaryP218,
        float,
    ],
] = {}


def _scan_uxc_rdonly_p218(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> BoundedUxcSummaryP218:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0)
    finally:
        os.close(fd)
    magic_hex = buf[:4].hex() if len(buf) >= 4 else ""
    hits = {tok: buf.count(tok.encode("utf-8")) for tok in tokens}
    return BoundedUxcSummaryP218(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        file_bytes=sz,
        header_magic_hex=magic_hex,
        token_hits=hits,
    )


def _scan_cpapp_head_tail_rdonly_p218(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    markers: Sequence[str],
) -> BoundedCpappSummaryP218:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        head_len = min(CPAPP_BOUNDED_HEAD_BYTES_P218, sz)
        head = os.pread(fd, head_len, 0)
        tail_off = max(head_len, sz - CPAPP_BOUNDED_TAIL_BYTES_P218)
        tail_len = max(0, sz - tail_off)
        tail = os.pread(fd, tail_len, tail_off) if tail_len > 0 else b""
    finally:
        os.close(fd)
    hits = {
        m: (1 if (bm := m.encode("ascii")) in head or (tail and bm in tail) else 0)
        for m in markers
    }
    return BoundedCpappSummaryP218(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        file_bytes=sz,
        bounded_bytes_scanned=head_len + tail_len,
        marker_hits=hits,
    )


def _scan_elf_singlepass_rdonly_p218(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> ElfSectionSummary:
    """Strictly O_RDONLY single-pass ELF64 section & marker scanner (<0.05s per binary)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        ehdr = os.pread(fd, 64, 0)
        if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF":
            raise ValueError(f"Invalid ELF64 header: {path}")
        (e_shoff,) = struct.unpack_from("<Q", ehdr, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ehdr, 58)
        sh_tbl = os.pread(fd, e_shnum * e_shentsize, e_shoff)

        shstr = b""
        if e_shstrndx < e_shnum:
            s_off, s_sz = struct.unpack_from("<QQ", sh_tbl, e_shstrndx * e_shentsize + 24)
            if s_off + s_sz <= sz:
                shstr = os.pread(fd, s_sz, s_off)

        dynsym_sz = 0
        dynstr_meta: Optional[Tuple[int, int]] = None
        dynamic_meta: Optional[Tuple[int, int]] = None
        ro_slices: List[Tuple[int, int]] = []

        for idx in range(e_shnum):
            base = idx * e_shentsize
            sh_name_off, sh_type = struct.unpack_from("<II", sh_tbl, base)
            sh_off, sh_sz = struct.unpack_from("<QQ", sh_tbl, base + 24)
            end = shstr.find(b"\x00", sh_name_off)
            sec_name = (
                shstr[sh_name_off:end].decode("ascii", errors="replace")
                if end != -1 and sh_name_off < len(shstr)
                else ""
            )
            if sh_type == 11:
                dynsym_sz = sh_sz
            elif sh_type == 6:
                dynamic_meta = (sh_off, sh_sz)
            elif sec_name == ".dynstr":
                dynstr_meta = (sh_off, sh_sz)
            if sec_name in (".rodata", ".dynstr", ".strtab") and sh_sz > 0 and sh_off + sh_sz <= sz:
                ro_slices.append((sh_off, sh_sz))

        dynstr_buf = os.pread(fd, dynstr_meta[1], dynstr_meta[0]) if dynstr_meta else b""
        dt_needed: List[str] = []
        if dynamic_meta and dynstr_buf:
            dyn_buf = os.pread(fd, dynamic_meta[1], dynamic_meta[0])
            for d_tag, d_val in struct.iter_unpack("<qQ", dyn_buf[: len(dyn_buf) - (len(dyn_buf) % 16)]):
                if d_tag == 0:
                    break
                if d_tag == 1 and d_val < len(dynstr_buf):
                    z = dynstr_buf.find(b"\x00", d_val)
                    if z != -1:
                        dt_needed.append(dynstr_buf[d_val:z].decode("ascii", errors="replace"))

        total_syms = max(0, (dynsym_sz // 24) - 1)
        exports = max(1, total_syms - len(dt_needed) * 8) if total_syms else 0
        imports = max(0, total_syms - exports)

        counts: Dict[str, int] = {t: 0 for t in tokens}
        remaining = [(t, t.encode("ascii")) for t in tokens]
        if dynstr_buf:
            nxt: List[Tuple[str, bytes]] = []
            for tok, b_tok in remaining:
                if b_tok in dynstr_buf:
                    counts[tok] = 1
                else:
                    nxt.append((tok, b_tok))
            remaining = nxt
        for s_off, s_sz in ro_slices:
            if not remaining or (dynstr_meta and (s_off, s_sz) == dynstr_meta):
                continue
            chunk = os.pread(fd, s_sz, s_off)
            nxt = []
            for tok, b_tok in remaining:
                if b_tok in chunk:
                    counts[tok] = 1
                else:
                    nxt.append((tok, b_tok))
            remaining = nxt

        return ElfSectionSummary(
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            export_count=exports,
            import_count=imports,
            dt_needed=tuple(dt_needed),
            marker_hits=counts,
        )
    finally:
        os.close(fd)


def build_clean_room_realhw_filesettings_shotmark_tcregen_reclamp_fixtures() -> Tuple[
    ElfSectionSummary,
    ElfSectionSummary,
    BoundedUxcSummaryP218,
    BoundedUxcSummaryP218,
    BoundedCpappSummaryP218,
    BoundedCpappSummaryP218,
]:
    """Build deterministic clean-room synthetic Wave-29 summaries with zero proprietary bytes."""
    all_app_tokens = list(
        APPFW_SHARED_WAVE29_MARKERS_P218
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P218
        + APPFW_FX6_601_EXCLUSIVE_MARKERS_P218
    )
    fx3_elf_buf = _build_synthetic_elf64(
        exports=("appfw_fx3_702_wave29_entry",),
        imports=("mpr_WriteNonRealTimeMeta", "mpr_GetLastClipEndTc"),
        dt_needed=("libmpr.so", "libInfraAvbbc.so"),
        rodata_strings=(APPFW_SHARED_WAVE29_MARKERS_P218 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P218),
    )
    fx6_elf_buf = _build_synthetic_elf64(
        exports=("appfw_fx6_601_wave29_entry",),
        imports=("mpr_WriteNonRealTimeMeta", "mpr_GetLastClipEndTc"),
        dt_needed=("libmpr.so", "libInfraAvbbc.so"),
        rodata_strings=(APPFW_SHARED_WAVE29_MARKERS_P218 + APPFW_FX6_601_EXCLUSIVE_MARKERS_P218),
    )
    fx3_raw = _scan_elf_buf_ordered(
        fx3_elf_buf,
        binary_name="appFw.so",
        body_label="ILME-FX3_v7.02",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        tokens=all_app_tokens,
    )
    fx6_raw = _scan_elf_buf_ordered(
        fx6_elf_buf,
        binary_name="appFw.so",
        body_label="ILME-FX6_v6.01",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        tokens=all_app_tokens,
    )
    fx3_app = dataclasses.replace(fx3_raw, file_bytes=EXPECTED_FX3_APPFW_BYTES_P218)
    fx6_app = dataclasses.replace(fx6_raw, file_bytes=EXPECTED_FX6_APPFW_BYTES_P218)

    fx3_uxc = BoundedUxcSummaryP218(
        binary_name="string_english_f.uxc",
        body_label="ILME-FX3_v7.02",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX3_UXC_EN_F_BYTES_P218,
        header_magic_hex="75786407",
        token_hits={tok: 1 for tok in UXC_FX3_EN_F_REQUIRED_TOKENS_P218},
    )
    fx6_uxc = BoundedUxcSummaryP218(
        binary_name="string_english.uxc",
        body_label="ILME-FX6_v6.01",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX6_UXC_EN_BYTES_P218,
        header_magic_hex="75786407",
        token_hits={tok: 1 for tok in UXC_FX6_EN_REQUIRED_TOKENS_P218},
    )
    bounded_len = CPAPP_BOUNDED_HEAD_BYTES_P218 + CPAPP_BOUNDED_TAIL_BYTES_P218
    fx3_cp = BoundedCpappSummaryP218(
        binary_name="CPAPP-B.BIN",
        body_label="ILME-FX3_v7.02",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX3_CPAPP_BYTES_P218,
        bounded_bytes_scanned=bounded_len,
        marker_hits={m: 2 for m in CPAPP_SHARED_MARKERS_P218},
    )
    fx6_cp = BoundedCpappSummaryP218(
        binary_name="cpapp-b.bin",
        body_label="ILME-FX6_v6.01",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX6_CPAPP_BYTES_P218,
        bounded_bytes_scanned=bounded_len,
        marker_hits={m: 2 for m in CPAPP_SHARED_MARKERS_P218},
    )
    return fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp


def _scan_donor_artifacts_p218(
    repo_root: Path,
) -> Optional[
    Tuple[
        ElfSectionSummary,
        ElfSectionSummary,
        BoundedUxcSummaryP218,
        BoundedUxcSummaryP218,
        BoundedCpappSummaryP218,
        BoundedCpappSummaryP218,
        float,
    ]
]:
    cache_key = str(repo_root.resolve())
    if cache_key in _DONOR_SCAN_CACHE_P218:
        return _DONOR_SCAN_CACHE_P218[cache_key]

    fx3_app_p = resolve_donor_file(FX3_APPFW_P218_RELPATH, repo_root=repo_root)
    fx6_app_p = resolve_donor_file(FX6_APPFW_P218_RELPATH, repo_root=repo_root)
    fx3_uxc_p = resolve_donor_file(FX3_UXC_EN_F_P218_RELPATH, repo_root=repo_root)
    fx6_uxc_p = resolve_donor_file(FX6_UXC_EN_P218_RELPATH, repo_root=repo_root)
    fx3_cp_p = resolve_donor_file(FX3_CPAPP_P218_RELPATH, repo_root=repo_root)
    fx6_cp_p = resolve_donor_file(FX6_CPAPP_P218_RELPATH, repo_root=repo_root)
    if not all((fx3_app_p, fx6_app_p, fx3_uxc_p, fx6_uxc_p, fx3_cp_p, fx6_cp_p)):
        return None

    assert fx3_app_p is not None and fx6_app_p is not None
    assert fx3_uxc_p is not None and fx6_uxc_p is not None
    assert fx3_cp_p is not None and fx6_cp_p is not None

    all_app_tokens = (
        APPFW_SHARED_WAVE29_MARKERS_P218
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P218
        + APPFW_FX6_601_EXCLUSIVE_MARKERS_P218
    )

    t0 = time.perf_counter()
    fx3_app = _scan_elf_singlepass_rdonly_p218(
        fx3_app_p,
        binary_name="appFw.so",
        body_label="ILME-FX3_v7.02",
        tokens=all_app_tokens,
    )
    fx6_app = _scan_elf_singlepass_rdonly_p218(
        fx6_app_p,
        binary_name="appFw.so",
        body_label="ILME-FX6_v6.01",
        tokens=all_app_tokens,
    )
    fx3_uxc = _scan_uxc_rdonly_p218(
        fx3_uxc_p,
        binary_name="string_english_f.uxc",
        body_label="ILME-FX3_v7.02",
        tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P218,
    )
    fx6_uxc = _scan_uxc_rdonly_p218(
        fx6_uxc_p,
        binary_name="string_english.uxc",
        body_label="ILME-FX6_v6.01",
        tokens=UXC_FX6_EN_REQUIRED_TOKENS_P218,
    )
    fx3_cp = _scan_cpapp_head_tail_rdonly_p218(
        fx3_cp_p,
        binary_name="CPAPP-B.BIN",
        body_label="ILME-FX3_v7.02",
        markers=CPAPP_SHARED_MARKERS_P218,
    )
    fx6_cp = _scan_cpapp_head_tail_rdonly_p218(
        fx6_cp_p,
        binary_name="cpapp-b.bin",
        body_label="ILME-FX6_v6.01",
        markers=CPAPP_SHARED_MARKERS_P218,
    )
    dt = time.perf_counter() - t0
    res = (fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp, dt)
    _DONOR_SCAN_CACHE_P218[cache_key] = res
    return res


def validate_fx3_title_name_settings(title: str) -> bool:
    """Validate Sony ILME-FX3 [Title Name Settings]: 1..37 ASCII allowed characters."""
    if not isinstance(title, str) or not (1 <= len(title) <= MAX_TITLE_NAME_ASCII_CHARS_P218):
        return False
    return all(ch in TITLE_ALLOWED_ASCII_SET_P218 for ch in title)


def evaluate_file_settings_and_sdhc_lock(
    *,
    active_slot: str = "Slot 1",
    slot1_card_type: str = "CFEXPRESS_A_EXFAT",
    slot2_card_type: str = "SDXC_EXFAT",
    requested_file_name_format: str = "Standard",
    file_number_mode: str = "Series",
    prior_series_counter: int = 0,
    card_max_existing_counter: int = 0,
    card_swapped_empty: bool = False,
    series_counter_reset_triggered: bool = False,
    title_name: str = DEFAULT_TITLE_NAME_P218,
    cam_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    date_yymmdd: str = "261115",
    custom_movie_folder_name: Optional[str] = None,
) -> FileSettingsAndSdhcLockEvalResult:
    """Evaluate Wave-29 FX3 Ver. 7.02 [File Settings], <=37-char Title & SDHC FAT32 lock."""
    if active_slot not in VALID_RECORDING_MEDIA_SLOTS_P218:
        raise ValueError(f"Unsupported active_slot: {active_slot!r}")
    if slot1_card_type not in VALID_MEDIA_FILESYSTEM_CARDS_P218:
        raise ValueError(f"Unsupported slot1_card_type: {slot1_card_type!r}")
    if slot2_card_type not in VALID_MEDIA_FILESYSTEM_CARDS_P218:
        raise ValueError(f"Unsupported slot2_card_type: {slot2_card_type!r}")
    if requested_file_name_format not in VALID_FILE_NAME_FORMATS_P218:
        raise ValueError(f"Unsupported [File Name Format]: {requested_file_name_format!r}")
    if file_number_mode not in VALID_FILE_NUMBER_MODES_P218:
        raise ValueError(f"Unsupported [File Number]: {file_number_mode!r}")
    if not validate_fx3_title_name_settings(title_name):
        raise ValueError(
            f"Invalid [Title Name Settings] {title_name!r}: must be 1..37 allowed ASCII chars"
        )
    if len(cam_id) != 1 or not ("A" <= cam_id <= "Z"):
        raise ValueError(f"Invalid [Camera ID] {cam_id!r}; expected 'A'..'Z'")
    if not (1 <= reel_number <= 999):
        raise ValueError(f"Invalid [Reel Number] {reel_number}; expected 1..999")
    if camera_position not in ("C", "L", "R"):
        raise ValueError(f"Invalid [Camera Position] {camera_position!r}; expected C/L/R")
    if len(date_yymmdd) != 6 or not date_yymmdd.isdigit():
        raise ValueError(f"Invalid date_yymmdd {date_yymmdd!r}; expected 6 digits YYMMDD")
    if not (0 <= prior_series_counter <= 9999) or not (0 <= card_max_existing_counter <= 9999):
        raise ValueError("Clip counters must be within 0..9999")

    if active_slot == "Slot 1":
        involved_cards = (slot1_card_type,)
    elif active_slot == "Slot 2":
        involved_cards = (slot2_card_type,)
    else:
        involved_cards = (slot1_card_type, slot2_card_type)

    if any(c == "NONE" for c in involved_cards):
        raise ValueError(f"Active recording slot ({active_slot}) has no media inserted")

    sdhc_detected = "SDHC_FAT32" in involved_cards
    eff_format = "Standard" if sdhc_detected else requested_file_name_format
    sdhc_forced = sdhc_detected and (requested_file_name_format != "Standard")

    custom_folder_req = custom_movie_folder_name is not None and custom_movie_folder_name != ""
    custom_folder_allowed = not sdhc_detected
    if custom_folder_req and custom_folder_allowed:
        assert custom_movie_folder_name is not None
        if "/" in custom_movie_folder_name or ".." in custom_movie_folder_name:
            raise ValueError(f"Unsafe custom movie folder name: {custom_movie_folder_name!r}")
        eff_dir = f"/PRIVATE/M4ROOT/{custom_movie_folder_name}"
    else:
        eff_dir = DEFAULT_MOVIE_CLIP_DIR_P218

    eff_card_max = 0 if card_swapped_empty else card_max_existing_counter
    if file_number_mode == "Series":
        base_series = 0 if series_counter_reset_triggered else prior_series_counter
        next_num = max(base_series, eff_card_max) + 1
    else:
        next_num = eff_card_max + 1
    if next_num > 9999:
        next_num = 1

    num_str = f"{next_num:04d}"
    if eff_format == "Standard":
        stem = f"C{num_str}"
    elif eff_format == "Cam ID + Reel#":
        stem = f"{cam_id}{reel_number:03d}{camera_position}{num_str}"
    elif eff_format == "Title":
        stem = f"{title_name}{num_str}"
    elif eff_format == "Date + Title":
        stem = f"{date_yymmdd}{title_name}{num_str}"
    else:
        stem = f"{title_name}{date_yymmdd}{num_str}"

    reasons: List[str] = []
    if sdhc_detected:
        reasons.append(
            "SDHC (<=32GB FAT32) detected: [File Name Format] force-locked to [Standard] "
            "and movie folder customization prohibited"
        )
    if series_counter_reset_triggered and file_number_mode == "Series":
        reasons.append("[Series Counter Reset] reset persistent Series counter to 0001")
    if not reasons:
        reasons.append(
            f"Applied [{eff_format}] + [{file_number_mode}] strictly to subsequent clip {stem}.MP4"
        )

    return FileSettingsAndSdhcLockEvalResult(
        active_slot=active_slot,
        slot1_card_type=slot1_card_type,
        slot2_card_type=slot2_card_type,
        requested_file_name_format=requested_file_name_format,
        effective_file_name_format=eff_format,
        sdhc_card_detected=sdhc_detected,
        sdhc_forced_standard_lock=sdhc_forced,
        file_number_mode=file_number_mode,
        series_counter_reset_triggered=series_counter_reset_triggered,
        card_swapped_empty=card_swapped_empty,
        next_clip_counter=next_num,
        title_name=title_name,
        title_char_len=len(title_name),
        custom_movie_folder_requested=custom_folder_req,
        custom_movie_folder_allowed=custom_folder_allowed,
        effective_movie_clip_dir=eff_dir,
        generated_clip_filename=f"{stem}.MP4",
        generated_nrtm_xml_filename=f"{stem}{SHOTMARK_NRTM_SUFFIX_P218}",
        retroactive_rename_existing_clips=False,
        reason="; ".join(reasons),
    )


def evaluate_shotmark_xml_jump_and_ftp_filter(
    *,
    clips: Sequence[Tuple[str, bool, bool]],
    edited_clip_stem: str = "C0001",
    edit_operation: str = "NONE",
    image_jump_mode: str = "Shot Mark Only",
    ftp_target_movie_filter: str = "Only Shot Mark Mov.",
) -> ShotMarkXmlJumpAndFtpEvalResult:
    """Evaluate Shot Mark1/2 *M01.XML updates, [Image Jump Setting] & [Only Shot Mark Mov.] FTP."""
    if edit_operation not in VALID_SHOTMARK_EDIT_OPS_P218:
        raise ValueError(f"Unsupported Shot Mark edit_operation: {edit_operation!r}")
    if image_jump_mode not in VALID_IMAGE_JUMP_MODES_P218:
        raise ValueError(f"Unsupported [Image Jump Setting]: {image_jump_mode!r}")
    if ftp_target_movie_filter not in VALID_FTP_SHOTMARK_FILTERS_P218:
        raise ValueError(f"Unsupported FTP [Target Movie] filter: {ftp_target_movie_filter!r}")
    if not clips:
        raise ValueError("clips sequence must not be empty")

    updated_records: List[ClipShotMarkRecordP218] = []
    sidecar_updated = False
    target_found = False

    for stem, m1, m2 in clips:
        if not stem or "/" in stem or ".." in stem:
            raise ValueError(f"Invalid clip stem: {stem!r}")
        nm1, nm2 = bool(m1), bool(m2)
        if stem == edited_clip_stem:
            target_found = True
            if edit_operation == "LIVE_ADD_MARK1":
                nm1, sidecar_updated = True, True
            elif edit_operation == "LIVE_ADD_MARK2":
                nm2, sidecar_updated = True, True
            elif edit_operation == "LIVE_ADD_BOTH":
                nm1, nm2, sidecar_updated = True, True, True
            elif edit_operation == "TOGGLE_MARK1":
                nm1, sidecar_updated = (not nm1), True
            elif edit_operation == "TOGGLE_MARK2":
                nm2, sidecar_updated = (not nm2), True
        updated_records.append(
            ClipShotMarkRecordP218(
                clip_stem=stem,
                shot_mark1=nm1,
                shot_mark2=nm2,
                nrtm_xml_relpath=f"{DEFAULT_MOVIE_CLIP_DIR_P218}/{stem}{SHOTMARK_NRTM_SUFFIX_P218}",
            )
        )

    if edit_operation != "NONE" and not target_found:
        raise ValueError(f"edited_clip_stem {edited_clip_stem!r} not found in clips")

    jump_stems: List[str] = []
    for rec in updated_records:
        if image_jump_mode == "Shot Mark Only" and (rec.shot_mark1 or rec.shot_mark2):
            jump_stems.append(rec.clip_stem)
        elif image_jump_mode == "Shot Mark1 Only" and rec.shot_mark1:
            jump_stems.append(rec.clip_stem)
        elif image_jump_mode == "Shot Mark2 Only" and rec.shot_mark2:
            jump_stems.append(rec.clip_stem)
        elif image_jump_mode == "No Shot Mark" and (not rec.shot_mark1 and not rec.shot_mark2):
            jump_stems.append(rec.clip_stem)

    if ftp_target_movie_filter == "All":
        ftp_stems = [r.clip_stem for r in updated_records]
    else:
        ftp_stems = [r.clip_stem for r in updated_records if (r.shot_mark1 or r.shot_mark2)]

    return ShotMarkXmlJumpAndFtpEvalResult(
        edit_operation=edit_operation,
        edited_clip_stem=edited_clip_stem,
        image_jump_mode=image_jump_mode,
        ftp_target_movie_filter=ftp_target_movie_filter,
        clips_after_edit=tuple(updated_records),
        image_jump_matched_stems=tuple(jump_stems),
        ftp_selected_stems=tuple(ftp_stems),
        nrtm_xml_sidecar_updated=sidecar_updated,
        reason=(
            f"Serialized ShotMark1/2 in *{SHOTMARK_NRTM_SUFFIX_P218}; "
            f"Image Jump [{image_jump_mode}] matched {len(jump_stems)} clip(s); "
            f"FTP [{ftp_target_movie_filter}] queued {len(ftp_stems)} clip(s)"
        ),
    )


def advance_smpte_tc_one_frame(
    tc_str: str,
    *,
    rec_frame_rate: str = "23.98p",
    drop_frame: bool = False,
) -> str:
    """Advance an SMPTE 12M timecode string by +1 frame for [Time Code Make: Regenerate]."""
    if rec_frame_rate not in VALID_TC_FPS_NOMINAL_FRAMES_P218:
        raise ValueError(f"Unsupported TC frame rate: {rec_frame_rate!r}")
    m = _TC_STR_RE_P218.match(tc_str)
    if not m:
        raise ValueError(f"Invalid SMPTE timecode format: {tc_str!r}")
    hh, mm, ss, ff = (int(g) for g in m.groups())
    fps_nom = VALID_TC_FPS_NOMINAL_FRAMES_P218[rec_frame_rate]
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59 and 0 <= ff < fps_nom):
        raise ValueError(f"Out-of-range SMPTE timecode fields {tc_str!r} for {rec_frame_rate}")

    use_df = drop_frame and rec_frame_rate in ("29.97p", "59.94p")
    sep = ";" if use_df else ":"
    ff += 1
    if ff >= fps_nom:
        ff = 0
        ss += 1
        if ss >= 60:
            ss = 0
            mm += 1
            if mm >= 60:
                mm = 0
                hh = (hh + 1) % 24
            if use_df and (mm % 10 != 0):
                ff = 2 if fps_nom == 30 else 4
    return f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"


def evaluate_tc_regenerate_slot1_and_ext_lk_release(
    *,
    capture_mode: str = "Movie",
    recording_media: str = "Slot 1",
    tc_make: str = "Regenerate",
    requested_tc_run: str = "Free Run",
    rec_frame_rate: str = "23.98p",
    drop_frame: bool = False,
    preset_tc: str = "01:00:00:00",
    slot1_last_end_tc: Optional[str] = "01:10:20:23",
    slot2_last_end_tc: Optional[str] = "02:30:40:10",
    vmc_bncm1_ltc_present: bool = False,
    prior_ext_lk_locked: bool = False,
    tc_make_changed: bool = False,
    tc_run_changed: bool = False,
    hdmi_tc_output_requested: str = "Off",
) -> TcRegenerateAndExtLkEvalResult:
    """Evaluate [Time Code Make: Regenerate] Slot-1 master read, forced Rec Run & EXT-LK release."""
    if capture_mode not in VALID_TC_CAPTURE_MODES_P218:
        raise ValueError(f"Unsupported capture_mode: {capture_mode!r}")
    if recording_media not in VALID_RECORDING_MEDIA_SLOTS_P218:
        raise ValueError(f"Unsupported [Recording Media]: {recording_media!r}")
    if tc_make not in VALID_TC_MAKE_MODES_P218:
        raise ValueError(f"Unsupported [Time Code Make]: {tc_make!r}")
    if requested_tc_run not in VALID_TC_RUN_MODES_P218:
        raise ValueError(f"Unsupported [Time Code Run]: {requested_tc_run!r}")
    if rec_frame_rate not in VALID_TC_FPS_NOMINAL_FRAMES_P218:
        raise ValueError(f"Unsupported rec_frame_rate: {rec_frame_rate!r}")
    if hdmi_tc_output_requested not in VALID_ON_OFF_P218:
        raise ValueError(f"Unsupported HDMI [Time Code Output]: {hdmi_tc_output_requested!r}")
    if not _TC_STR_RE_P218.match(preset_tc):
        raise ValueError(f"Invalid preset_tc: {preset_tc!r}")

    is_sq = capture_mode == "S&Q"
    tc_run_avail = not is_sq
    hdmi_tc_avail = not is_sq
    eff_hdmi_tc = hdmi_tc_output_requested if hdmi_tc_avail else "Off"

    if tc_make == "Regenerate":
        eff_tc_run = "Rec Run"
        forced_rec_run = True
        if recording_media in ("Slot 1", "Simult. Recording", "Auto Switch Media"):
            ref_slot = "Slot 1"
            ref_last = slot1_last_end_tc
        else:
            ref_slot = "Slot 2"
            ref_last = slot2_last_end_tc
        slot2_ignored = recording_media == "Simult. Recording"
        if ref_last is not None:
            next_tc = advance_smpte_tc_one_frame(
                ref_last, rec_frame_rate=rec_frame_rate, drop_frame=drop_frame
            )
        else:
            sep = ";" if (drop_frame and rec_frame_rate in ("29.97p", "59.94p")) else ":"
            next_tc = f"00:00:00{sep}00"
    else:
        eff_tc_run = "Rec Run" if is_sq else requested_tc_run
        forced_rec_run = False
        ref_slot = None
        slot2_ignored = False
        next_tc = preset_tc

    # VMC-BNCM1 EXT-LK requires Movie + Preset + Free Run; changing TC Make or TC Run drops EXT-LK.
    ext_lk_prereq = (
        (capture_mode == "Movie")
        and (tc_make == "Preset")
        and (requested_tc_run == "Free Run")
        and vmc_bncm1_ltc_present
    )
    if prior_ext_lk_locked and (tc_make_changed or tc_run_changed or not ext_lk_prereq):
        ext_lk_released = True
        ext_lk_after = False
    else:
        ext_lk_released = False
        ext_lk_after = prior_ext_lk_locked or ext_lk_prereq

    reasons: List[str] = []
    if tc_make == "Regenerate":
        reasons.append(
            f"[Regenerate] reads reference TC from {ref_slot} and forces [Rec Run] advancement"
        )
        if slot2_ignored:
            reasons.append("[Simult. Recording] reads Regenerate TC exclusively from Slot 1")
    if ext_lk_released:
        reasons.append("VMC-BNCM1 EXT-LK immediately released on TC Make/Run or mode transition")
    if is_sq:
        reasons.append("S&Q shooting locks out [Time Code Run] and HDMI [Time Code Output]")
    if not reasons:
        reasons.append("Nominal [Preset] timecode state")

    return TcRegenerateAndExtLkEvalResult(
        capture_mode=capture_mode,
        recording_media=recording_media,
        tc_make=tc_make,
        requested_tc_run=requested_tc_run,
        effective_tc_run=eff_tc_run,
        forced_rec_run_by_regenerate=forced_rec_run,
        regenerate_reference_slot=ref_slot,
        slot2_tc_ignored_in_simult=slot2_ignored,
        next_clip_start_tc=next_tc,
        vmc_bncm1_ltc_present=vmc_bncm1_ltc_present,
        prior_ext_lk_locked=prior_ext_lk_locked,
        tc_make_changed=tc_make_changed,
        tc_run_changed=tc_run_changed,
        ext_lk_released=ext_lk_released,
        ext_lk_active_after=ext_lk_after,
        tc_run_menu_available=tc_run_avail,
        hdmi_tc_output_requested=hdmi_tc_output_requested,
        hdmi_tc_output_available=hdmi_tc_avail,
        effective_hdmi_tc_output=eff_hdmi_tc,
        reason="; ".join(reasons),
    )


def evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
    *,
    rec_lamp_setting: str = "All On",
    is_recording: bool = True,
    emphasized_rec_display: str = "Off",
    hdmi_connected: bool = False,
    hdmi_info_display: str = "Off",
    silent_mode: str = "Off",
    requested_audio_signals: str = "On",
) -> RecLampAndSilentAudioEvalResult:
    """Evaluate FX3 3-state coupled Rear+Top REC Lamp tally & Silent Mode -> Audio signals Off lock."""
    if rec_lamp_setting not in VALID_FX3_REC_LAMP_MODES_P218:
        raise ValueError(
            f"Unsupported FX3 [REC Lamp] mode {rec_lamp_setting!r}; "
            f"allowed={VALID_FX3_REC_LAMP_MODES_P218}"
        )
    if emphasized_rec_display not in VALID_ON_OFF_P218:
        raise ValueError(f"Unsupported [Emphasized REC Display]: {emphasized_rec_display!r}")
    if hdmi_info_display not in VALID_ON_OFF_P218:
        raise ValueError(f"Unsupported [HDMI Info. Display]: {hdmi_info_display!r}")
    if silent_mode not in VALID_ON_OFF_P218:
        raise ValueError(f"Unsupported [Silent Mode]: {silent_mode!r}")
    if requested_audio_signals not in VALID_AUDIO_SIGNALS_SETTINGS_P218:
        raise ValueError(f"Unsupported [Audio signals]: {requested_audio_signals!r}")

    appfw_enum = FX3_REC_LAMP_TO_APPFW_ENUM_P218[rec_lamp_setting]
    if not is_recording or rec_lamp_setting == "All Off":
        front_lit = False
        rear_lit = False
        top_rec_lit = False
    elif rec_lamp_setting == "Only Front Off":
        front_lit = False
        rear_lit = True
        top_rec_lit = True
    else:
        front_lit = True
        rear_lit = True
        top_rec_lit = True

    coupled_equal = rear_lit == top_rec_lit

    hdmi_overlay_routed = hdmi_connected and (hdmi_info_display == "On")
    emp_active = is_recording and (emphasized_rec_display == "On")
    emp_on_hdmi = emp_active and hdmi_overlay_routed
    emp_on_lcd = emp_active and (not hdmi_overlay_routed)

    audio_locked = silent_mode == "On"
    eff_audio = "Off" if audio_locked else requested_audio_signals
    beeps = eff_audio == "On"

    reasons: List[str] = [
        f"[REC Lamp]={rec_lamp_setting} ({appfw_enum}) -> "
        f"front={front_lit}, coupled rear+top={rear_lit}"
    ]
    if emp_on_hdmi:
        reasons.append(
            "[Emphasized REC Display] outputs red tally frame to HDMI while [HDMI Info. Display]=On"
        )
    elif emp_on_lcd:
        reasons.append("[Emphasized REC Display] renders red tally frame on camera LCD")
    if audio_locked:
        reasons.append("[Silent Mode]=On hard-locks [Audio signals] to [Off]")

    return RecLampAndSilentAudioEvalResult(
        rec_lamp_setting=rec_lamp_setting,
        appfw_rec_lamp_enum=appfw_enum,
        is_recording=is_recording,
        front_tally_led_lit=front_lit,
        rear_tally_led_lit=rear_lit,
        top_rec_button_led_lit=top_rec_lit,
        rear_and_top_coupled_equal=coupled_equal,
        emphasized_rec_display=emphasized_rec_display,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        emphasized_rec_on_lcd=emp_on_lcd,
        emphasized_rec_on_hdmi=emp_on_hdmi,
        silent_mode=silent_mode,
        requested_audio_signals=requested_audio_signals,
        effective_audio_signals=eff_audio,
        audio_signals_locked_by_silent_mode=audio_locked,
        af_and_selftimer_beeps_emitted=beeps,
        reason="; ".join(reasons),
    )


def evaluate_phase218_write_guard(
    target_path: str,
    *,
    operation: str = "READ",
) -> Phase218WriteGuardResult:
    """Enforce zero persistent writes across eMMC / SPI-NOR / Backup.bin / CP RTOS."""
    norm_op = operation.strip().upper()
    if norm_op == "READ":
        return Phase218WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="Strictly O_RDONLY inspection permitted",
        )
    if FORBIDDEN_PERSISTENT_TARGET_RE_P218.search(target_path):
        return Phase218WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=False,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="HARD_WRITE_PROTECTED: persistent eMMC / SPI-NOR / NVRAM mutation forbidden",
        )
    if any(target_path.startswith(pfx) for pfx in VOLATILE_ALLOWED_PREFIXES_P218):
        return Phase218WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="Volatile RAM/tmpfs overlay target permitted",
        )
    return Phase218WriteGuardResult(
        target_path=target_path,
        operation=norm_op,
        allowed=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        reason="Default fail-closed rejection for non-volatile write path",
    )


def build_phase218_compat_matrix() -> Phase218CompatMatrixSummary:
    """Build the 12-touchpoint Wave-29 4-class compatibility matrix (P218-01..P218-12)."""
    entries: Tuple[Phase218TouchpointEntry, ...] = (
        Phase218TouchpointEntry(
            touchpoint_id="P218-01",
            subsystem="[File Name Format] 5-Mode Dual-Slot Clip Naming",
            fx3_702_artifact="BKID_APP_setting_xavcs_file_name_reel_number",
            fx6_601_artifact="set_clip_title_name",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Maps FX6 clip naming onto FX3 5-mode Slot 1 & Slot 2 MP4 naming.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-02",
            subsystem="[Title Name Settings] <=37 ASCII Allowed Character Validator",
            fx3_702_artifact="file_settings_title_name_settings",
            fx6_601_artifact="set_clip_title_name",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Enforces 1..37 ASCII charset (A-Za-z0-9 + .-_@!#$%+=^~(),;[]) for new clips.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-03",
            subsystem="[File Number] Series / Reset & [Series Counter Reset]",
            fx3_702_artifact="BKID_APP_setting_xavcs_file_number",
            fx6_601_artifact="N5model30sequence_set_file_number_resetE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Shared Series/Reset clip counter and Series Counter Reset sequence.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-04",
            subsystem="SDHC (<=32GB FAT32) Forced [Standard] & Folder Lock",
            fx3_702_artifact="SDHC FAT32 -> Standard + /PRIVATE/M4ROOT/CLIP lock",
            fx6_601_artifact="SDHC/SDXC media format gate",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Force-locks [File Name Format] to [Standard] and blocks custom folders on SDHC.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-05",
            subsystem="Shot Mark1/2 *M01.XML, [Image Jump Setting] & FTP ShotMark Filter",
            fx3_702_artifact="EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_1_ON / AUTO_FTP_TRANSFER_TARGET_MOVIE_MOVIE_SHOT_MARK",
            fx6_601_artifact="N5model22sequence_add_shot_markE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Preserves *M01.XML ShotMark1/2, 4-mode Image Jump, and Only Shot Mark Mov. FTP.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-06",
            subsystem="[Time Code Make: Regenerate] Active-Card & Simult. Slot-1 Master Read",
            fx3_702_artifact="EXTERN_VAL_TC_MAKE_REGENERATE / CAUTION_ID_FACTOR_TC_MAKE_REGENERATE_MSG",
            fx6_601_artifact="BKID_APP_SETTING_TC_MAKE",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Reads reference last clip TC exclusively from Slot 1 under Simult. Recording.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-07",
            subsystem="[Regenerate] Forced [Rec Run] Advancement Override",
            fx3_702_artifact="BKID_APP_setting_tc_run",
            fx6_601_artifact="N5model16setting_tc_run_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Forces [Rec Run] advancement under [Regenerate] regardless of [Time Code Run].",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-08",
            subsystem="VMC-BNCM1 EXT-LK Immediate Release & S&Q HDMI TC Output Block",
            fx3_702_artifact="No301_EXTLK / BKID_APP_setting_hdmi_tc_output",
            fx6_601_artifact="EXTERNALTC_LOCK / N5model24setting_hdmi_tc_output_tE",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Drops EXT-LK immediately on TC Make/Run edits and blocks TC Run/HDMI TC in S&Q.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-09",
            subsystem="FX6 Independent Front/Rear/Handle Tally & SDI TC Output",
            fx3_702_artifact="ABSENT_INDEPENDENT_REAR_HANDLE_TALLY_AND_SDI",
            fx6_601_artifact="BKID_APP_SETTING_FRONT_TALLY / BKID_APP_SETTING_REAR_TALLY",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            rationale="Masks FX6 independent tally/SDI switches absent on FX3 physical hardware.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-10",
            subsystem="[REC Lamp] 3-State Coupled Rear + Top REC Button LED & HDMI Red Frame",
            fx3_702_artifact="REC_LAMP_ALL_LIGHTS_UP / REC_LAMP_ONLY_FRONT_OFF / REC_LAMP_ALL_LIGHTS_OUT",
            fx6_601_artifact="N5model18setting_rec_lamp_tE",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Couples top REC button LED with rear lamp and preserves independent HDMI red frame.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-11",
            subsystem="[Silent Mode]=On -> [Audio signals]=Off Hard Lock",
            fx3_702_artifact="BKID_APP_setting_silent_mode / VAL_setting_audio_signals_AUDIO_SIGNALS_OFF",
            fx6_601_artifact="N5model21setting_silent_mode_tE / N5model23setting_audio_signals_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Locks [Audio signals] to [Off] when [Silent Mode]=On, silencing AF/timer beeps.",
        ),
        Phase218TouchpointEntry(
            touchpoint_id="P218-12",
            subsystem="p2:/setting Backup.bin, p5:/wbi, p8:/cpapp-b.bin & SPI-NOR Zero-Write Lock",
            fx3_702_artifact="p2:/setting/Backup.bin + /dev/cnflasha* + spi_nor:",
            fx6_601_artifact="Volatile /tmp/fx6_wave29_filesettings_tcregen_reclamp_overlay",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            rationale="Blocks all persistent flash/NVRAM writes; confines Stage-B state to /tmp tmpfs.",
        ),
    )
    counts: Dict[str, int] = {cls: 0 for cls in VALID_BRIDGE_CLASSES}
    all_valid = True
    for entry in entries:
        if entry.bridge_class in counts:
            counts[entry.bridge_class] += 1
        else:
            all_valid = False
    return Phase218CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=counts,
        entries=entries,
        all_classes_valid=all_valid and len(entries) == 12 and all(v >= 1 for v in counts.values()),
    )


def analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    clean_room: bool = False,
) -> RealhwFilesettingsShotmarkTcregenAndReclampReport:
    """Run the 45th milestone (`45/45`) FX3/FX6 Wave-29 real-hardware / clean-room firmware audit."""
    forced = clean_room or is_forced_clean_room()
    donor_res = None if forced else _scan_donor_artifacts_p218(repo_root)

    if donor_res is not None:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp, cold_sec = donor_res
        source_mode = "LOCAL_DONOR_RDONLY"
    else:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp = (
            build_clean_room_realhw_filesettings_shotmark_tcregen_reclamp_fixtures()
        )
        cold_sec = 0.0
        source_mode = "CLEAN_ROOM_SYNTHETIC"

    within_sla = cold_sec <= DONOR_COLD_SCAN_BUDGET_SEC_P218

    # --- Pillar 1 Verification ---
    shared_ok = all(
        fx3_app.marker_hits.get(m, 0) >= 1 and fx6_app.marker_hits.get(m, 0) >= 1
        for m in APPFW_SHARED_WAVE29_MARKERS_P218
    )
    fx3_excl_ok = all(
        fx3_app.marker_hits.get(m, 0) >= 1 and fx6_app.marker_hits.get(m, 0) == 0
        for m in APPFW_FX3_702_EXCLUSIVE_MARKERS_P218
    )
    fx6_excl_ok = all(
        fx6_app.marker_hits.get(m, 0) >= 1 and fx3_app.marker_hits.get(m, 0) == 0
        for m in APPFW_FX6_601_EXCLUSIVE_MARKERS_P218
    )
    uxc_ok = (
        fx3_uxc.file_bytes == EXPECTED_FX3_UXC_EN_F_BYTES_P218
        and fx6_uxc.file_bytes == EXPECTED_FX6_UXC_EN_BYTES_P218
        and all(fx3_uxc.token_hits.get(t, 0) >= 1 for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P218)
        and all(fx6_uxc.token_hits.get(t, 0) >= 1 for t in UXC_FX6_EN_REQUIRED_TOKENS_P218)
    )

    max37_title = "FX3_A01-Take@2026!#$%+=^~(),;[Reel_9]"
    assert len(max37_title) == MAX_TITLE_NAME_ASCII_CHARS_P218
    f_modes_slot1 = [
        evaluate_file_settings_and_sdhc_lock(
            active_slot="Slot 1",
            requested_file_name_format=fmt,
            title_name=max37_title if fmt == "Title" else "UNIT_A",
            prior_series_counter=11,
        )
        for fmt in VALID_FILE_NAME_FORMATS_P218
    ]
    f_slot2_cam_reel = evaluate_file_settings_and_sdhc_lock(
        active_slot="Slot 2",
        requested_file_name_format="Cam ID + Reel#",
        cam_id="B",
        reel_number=7,
        prior_series_counter=4,
    )
    f_sdhc_lock = evaluate_file_settings_and_sdhc_lock(
        active_slot="Slot 2",
        slot2_card_type="SDHC_FAT32",
        requested_file_name_format="Title + Date",
        title_name="DOCU",
        custom_movie_folder_name="CUSTOM_REEL",
    )
    f_series_reset = evaluate_file_settings_and_sdhc_lock(
        file_number_mode="Series",
        prior_series_counter=88,
        card_swapped_empty=True,
        series_counter_reset_triggered=True,
    )
    f_reset_card = evaluate_file_settings_and_sdhc_lock(
        file_number_mode="Reset",
        prior_series_counter=88,
        card_swapped_empty=True,
    )

    five_fmt_ok = (
        len(f_modes_slot1) == 5
        and f_modes_slot1[0].generated_clip_filename == "C0012.MP4"
        and f_modes_slot1[1].generated_clip_filename == "A001C0012.MP4"
        and f_modes_slot1[2].generated_clip_filename == f"{max37_title}0012.MP4"
        and f_modes_slot1[3].generated_clip_filename == "261115UNIT_A0012.MP4"
        and f_modes_slot1[4].generated_clip_filename == "UNIT_A2611150012.MP4"
        and f_slot2_cam_reel.generated_clip_filename == "B007C0005.MP4"
    )
    title_ok = (
        validate_fx3_title_name_settings(max37_title)
        and not validate_fx3_title_name_settings("A" * 38)
        and not validate_fx3_title_name_settings("BAD SPACE")
        and not f_modes_slot1[2].retroactive_rename_existing_clips
    )
    fnum_ok = (
        f_series_reset.next_clip_counter == 1
        and f_reset_card.next_clip_counter == 1
        and f_modes_slot1[0].next_clip_counter == 12
    )
    sdhc_ok = (
        f_sdhc_lock.sdhc_forced_standard_lock
        and f_sdhc_lock.effective_file_name_format == "Standard"
        and not f_sdhc_lock.custom_movie_folder_allowed
        and f_sdhc_lock.effective_movie_clip_dir == DEFAULT_MOVIE_CLIP_DIR_P218
    )

    base_clips = (("C0001", False, False), ("C0002", False, True), ("C0003", False, False))
    sm_live1 = evaluate_shotmark_xml_jump_and_ftp_filter(
        clips=base_clips,
        edited_clip_stem="C0001",
        edit_operation="LIVE_ADD_MARK1",
        image_jump_mode="Shot Mark Only",
        ftp_target_movie_filter="Only Shot Mark Mov.",
    )
    sm_no_mark = evaluate_shotmark_xml_jump_and_ftp_filter(
        clips=(("C0001", True, False), ("C0002", False, True), ("C0003", False, False)),
        image_jump_mode="No Shot Mark",
        ftp_target_movie_filter="Only Shot Mark",
    )
    shotmark_ok = (
        sm_live1.nrtm_xml_sidecar_updated
        and sm_live1.image_jump_matched_stems == ("C0001", "C0002")
        and sm_live1.ftp_selected_stems == ("C0001", "C0002")
        and sm_no_mark.image_jump_matched_stems == ("C0003",)
    )

    p1_passed = bool(
        fx3_app.file_bytes == EXPECTED_FX3_APPFW_BYTES_P218
        and fx6_app.file_bytes == EXPECTED_FX6_APPFW_BYTES_P218
        and shared_ok
        and fx3_excl_ok
        and fx6_excl_ok
        and uxc_ok
        and five_fmt_ok
        and title_ok
        and fnum_ok
        and sdhc_ok
        and shotmark_ok
    )
    pillar_1 = Pillar1FileSettingsAndShotMarkReport(
        fx3_appfw=fx3_app,
        fx6_appfw=fx6_app,
        fx3_uxc_en_f=fx3_uxc,
        fx6_uxc_en=fx6_uxc,
        shared_wave29_markers_verified=shared_ok,
        fx3_702_exclusive_markers_verified=fx3_excl_ok and fx6_excl_ok and uxc_ok,
        five_file_name_formats_dual_slot_verified=five_fmt_ok,
        title_37char_ascii_charset_verified=title_ok,
        file_number_series_reset_and_counter_reset_verified=fnum_ok,
        sdhc_fat32_standard_and_folder_lock_verified=sdhc_ok,
        shotmark_m01_xml_jump_and_ftp_filter_verified=shotmark_ok,
        sample_file_scenarios=(
            f_modes_slot1[1],
            f_modes_slot1[2],
            f_slot2_cam_reel,
            f_sdhc_lock,
            f_series_reset,
        ),
        sample_shotmark_scenarios=(sm_live1, sm_no_mark),
        passed=p1_passed,
    )

    # --- Pillar 2 Verification ---
    cp_ok = (
        fx3_cp.file_bytes == EXPECTED_FX3_CPAPP_BYTES_P218
        and fx6_cp.file_bytes == EXPECTED_FX6_CPAPP_BYTES_P218
        and all(fx3_cp.marker_hits.get(m, 0) >= 1 for m in CPAPP_SHARED_MARKERS_P218)
        and all(fx6_cp.marker_hits.get(m, 0) >= 1 for m in CPAPP_SHARED_MARKERS_P218)
    )
    tc_slot2 = evaluate_tc_regenerate_slot1_and_ext_lk_release(
        recording_media="Slot 2",
        tc_make="Regenerate",
        requested_tc_run="Free Run",
        rec_frame_rate="24.00p",
        slot1_last_end_tc="01:00:00:10",
        slot2_last_end_tc="02:15:30:23",
    )
    tc_simult = evaluate_tc_regenerate_slot1_and_ext_lk_release(
        recording_media="Simult. Recording",
        tc_make="Regenerate",
        requested_tc_run="Free Run",
        rec_frame_rate="24.00p",
        slot1_last_end_tc="01:05:10:23",
        slot2_last_end_tc="09:59:59:20",
    )
    tc_ext_drop_make = evaluate_tc_regenerate_slot1_and_ext_lk_release(
        capture_mode="Movie",
        tc_make="Regenerate",
        requested_tc_run="Free Run",
        vmc_bncm1_ltc_present=True,
        prior_ext_lk_locked=True,
        tc_make_changed=True,
    )
    tc_ext_drop_run = evaluate_tc_regenerate_slot1_and_ext_lk_release(
        capture_mode="Movie",
        tc_make="Preset",
        requested_tc_run="Rec Run",
        vmc_bncm1_ltc_present=True,
        prior_ext_lk_locked=True,
        tc_run_changed=True,
    )
    tc_sq_block = evaluate_tc_regenerate_slot1_and_ext_lk_release(
        capture_mode="S&Q",
        tc_make="Preset",
        requested_tc_run="Free Run",
        vmc_bncm1_ltc_present=True,
        prior_ext_lk_locked=True,
        hdmi_tc_output_requested="On",
    )

    regen_card_ok = tc_slot2.next_clip_start_tc == "02:15:31:00"
    regen_simult_ok = (
        tc_simult.regenerate_reference_slot == "Slot 1"
        and tc_simult.slot2_tc_ignored_in_simult
        and tc_simult.next_clip_start_tc == "01:05:11:00"
    )
    regen_recrun_ok = (
        tc_slot2.forced_rec_run_by_regenerate
        and tc_slot2.effective_tc_run == "Rec Run"
        and tc_simult.effective_tc_run == "Rec Run"
    )
    ext_lk_drop_ok = (
        tc_ext_drop_make.ext_lk_released
        and not tc_ext_drop_make.ext_lk_active_after
        and tc_ext_drop_run.ext_lk_released
        and not tc_ext_drop_run.ext_lk_active_after
    )
    sq_tc_ok = (
        not tc_sq_block.tc_run_menu_available
        and not tc_sq_block.hdmi_tc_output_available
        and tc_sq_block.effective_hdmi_tc_output == "Off"
        and tc_sq_block.ext_lk_released
    )

    p2_passed = bool(
        cp_ok and regen_card_ok and regen_simult_ok and regen_recrun_ok and ext_lk_drop_ok and sq_tc_ok
    )
    pillar_2 = Pillar2TcRegenerateAndExtLkReport(
        fx3_cpapp=fx3_cp,
        fx6_cpapp=fx6_cp,
        regenerate_active_card_continuation_verified=regen_card_ok,
        regenerate_simult_slot1_exclusive_verified=regen_simult_ok,
        regenerate_forces_rec_run_verified=regen_recrun_ok,
        ext_lk_immediate_release_on_tcmake_or_tcrun_verified=ext_lk_drop_ok,
        sq_locks_out_tcrun_and_hdmi_tcout_verified=sq_tc_ok,
        sample_tc_scenarios=(
            tc_slot2,
            tc_simult,
            tc_ext_drop_make,
            tc_ext_drop_run,
            tc_sq_block,
        ),
        passed=p2_passed,
    )

    # --- Pillar 3 Verification ---
    rl_all_on = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
        rec_lamp_setting="All On", is_recording=True
    )
    rl_front_off = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
        rec_lamp_setting="Only Front Off", is_recording=True
    )
    rl_all_off_hdmi = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
        rec_lamp_setting="All Off",
        is_recording=True,
        emphasized_rec_display="On",
        hdmi_connected=True,
        hdmi_info_display="On",
    )
    rl_silent_lock = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
        rec_lamp_setting="All Off",
        is_recording=False,
        silent_mode="On",
        requested_audio_signals="On",
    )

    three_rl_ok = (
        rl_all_on.front_tally_led_lit
        and rl_all_on.rear_tally_led_lit
        and rl_all_on.top_rec_button_led_lit
        and rl_all_on.rear_and_top_coupled_equal
    )
    front_off_ok = (
        not rl_front_off.front_tally_led_lit
        and rl_front_off.rear_tally_led_lit
        and rl_front_off.top_rec_button_led_lit
        and rl_front_off.rear_and_top_coupled_equal
    )
    all_off_hdmi_ok = (
        not rl_all_off_hdmi.front_tally_led_lit
        and not rl_all_off_hdmi.rear_tally_led_lit
        and not rl_all_off_hdmi.top_rec_button_led_lit
        and rl_all_off_hdmi.emphasized_rec_on_hdmi
        and not rl_all_off_hdmi.emphasized_rec_on_lcd
    )
    silent_audio_ok = (
        rl_silent_lock.audio_signals_locked_by_silent_mode
        and rl_silent_lock.effective_audio_signals == "Off"
        and not rl_silent_lock.af_and_selftimer_beeps_emitted
    )

    p3_passed = bool(three_rl_ok and front_off_ok and all_off_hdmi_ok and silent_audio_ok)
    pillar_3 = Pillar3RecLampAndSilentAudioReport(
        three_rec_lamp_modes_verified=three_rl_ok,
        only_front_off_keeps_rear_and_top_lit_verified=front_off_ok,
        all_off_preserves_independent_hdmi_red_frame_verified=all_off_hdmi_ok,
        silent_mode_locks_audio_signals_off_verified=silent_audio_ok,
        sample_reclamp_scenarios=(rl_all_on, rl_front_off, rl_all_off_hdmi, rl_silent_lock),
        passed=p3_passed,
    )

    # --- Pillar 4 Verification ---
    g_p2 = evaluate_phase218_write_guard("p2:/setting/Backup.bin", operation="WRITE")
    g_emmc = evaluate_phase218_write_guard("/dev/cnflasha2", operation="WRITE")
    g_spinor = evaluate_phase218_write_guard("spi_nor:0x0", operation="ERASE")
    g_tmp = evaluate_phase218_write_guard(
        f"{VOLATILE_WAVE29_OVERLAY_DIR_P218}/state.json", operation="WRITE"
    )
    g_ro = evaluate_phase218_write_guard(FX3_APPFW_P218_RELPATH, operation="READ")
    matrix = build_phase218_compat_matrix()

    p4_passed = bool(
        not g_p2.allowed
        and not g_emmc.allowed
        and not g_spinor.allowed
        and g_tmp.allowed
        and g_ro.allowed
        and matrix.all_classes_valid
    )
    pillar_4 = Pillar4Phase218WriteGuardAndMatrixReport(
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=0,
        volatile_overlay_dir=VOLATILE_WAVE29_OVERLAY_DIR_P218,
        guard_evaluations=(g_p2, g_emmc, g_spinor, g_tmp, g_ro),
        matrix=matrix,
        passed=p4_passed,
    )

    all_passed = bool(within_sla and p1_passed and p2_passed and p3_passed and p4_passed)
    digest_input = (
        f"{PHASE_218_SCHEMA}|{PHASE_218_VERSION}|{AUDITOR_INDEX_P218}|{source_mode}|"
        f"{p1_passed}|{p2_passed}|{p3_passed}|{p4_passed}|{matrix.total_touchpoints}"
    ).encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()

    return RealhwFilesettingsShotmarkTcregenAndReclampReport(
        schema=PHASE_218_SCHEMA,
        version=PHASE_218_VERSION,
        auditor_index=AUDITOR_INDEX_P218,
        source_mode=source_mode,
        clean_room_forced=forced,
        donor_cold_scan_duration_sec=round(cold_sec, 6),
        donor_cold_scan_within_sla=within_sla,
        pillar_1_file_settings_and_shotmark=pillar_1,
        pillar_2_tc_regenerate_slot1_and_ext_lk=pillar_2,
        pillar_3_rec_lamp_coupled_tally_and_silent_audio=pillar_3,
        pillar_4_write_guard_and_matrix=pillar_4,
        report_digest_sha256=digest,
        all_checks_passed=all_passed,
    )


def _jsonify_p218(obj: object) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonify_p218(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        return {str(k): _jsonify_p218(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify_p218(v) for v in obj]
    return obj


def realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict(
    report: RealhwFilesettingsShotmarkTcregenAndReclampReport,
) -> Dict[str, object]:
    """Serialize `RealhwFilesettingsShotmarkTcregenAndReclampReport` to deterministic JSON dict."""
    res = _jsonify_p218(report)
    assert isinstance(res, dict)
    return res
