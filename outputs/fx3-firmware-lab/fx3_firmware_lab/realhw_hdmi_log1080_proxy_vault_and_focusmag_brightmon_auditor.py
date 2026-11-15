"""Phase 211 (44th Auditor, 44/44): Real-Hardware `ILME-FX3` (`Ver. 7.02`) HDMI Log `1080p` vs
`Off(HDMI Only)` `4K 10-bit`, `Px` Proxy Coupled Vault & `Focus Magnifier` / `Bright Monitoring` Auditor.

Strictly `os.O_RDONLY` + bounded `os.pread` (`< 0.15s` cold budget, cached per process,
with deterministic synthetic Clean-Room fallback under `FX3_FX6_FORCE_CLEAN_ROOM=1` or
`clean_room=True`), zero raw firmware byte leakage (`raw_firmware_bytes_leaked = 0`),
and zero persistent eMMC / SPI-NOR / USB / EL3 mutations (`persistent_emmc_writes_authorized = False`).

Audits four Wave-28 hardware pillars across Stock `ILME-FX3` (`Ver. 7.02`) vs `ILME-FX6` (`Ver. 6.01`):
  1. Pillar A — `[HDMI Output Settings]` (`[Rec. Media dur HDMI Output]`: `[On]` vs `[Off(HDMI Only)]`)
     + `[4K Output Set.(HDMI Only)]` (`59.94p/50p/29.97p/25p/23.98p/24.00p 10bit`), `[Log Shooting]`
     (`Cine EI` / `Cine EI Quick` / `Flexible ISO`) & `[Picture Profile]` `PPLUT1..PPLUT4` forced
     `1080p` (`1920x1080`) HDMI downshift when internal card recording is `[On]` and `[RAW Output] = [Off]`,
     `[HDMI Info. Display]` forced `[Off]` (and HDMI `[De-Squeeze Display]` disabled) under
     `[Off(HDMI Only)]` / `[RAW Output] = [On]`, and built-in camera LCD blanking when
     `[HDMI Info. Display] = [On]` (with `[Emphasized REC Display]` red tally border on external HDMI).
  2. Pillar B — `[Proxy Settings]` exact 2-format / 3-bitrate schema (`[XAVC HS HD]` `1920x1080`
     10-bit 4:2:0 HEVC `16M` / `9M` [format default] max `59.94p/50p`; `[XAVC S HD]` [overall default]
     `1280x720` 8-bit 4:2:0 AVC `6M` max `59.94p/50p`), hard cutoffs at `[Rec Frame Rate] = 119.88p/100p`,
     `S&Q` sensor `[Frame Rate] >= 120fps/100fps` (`100/120/200/240fps`), and `[Off(HDMI Only)]`,
     zero on-camera proxy playback (`(Px)` badge only on `M4ROOT/CLIP/`), and atomic coupled
     `M4ROOT/CLIP/` + `M4ROOT/SUB/` in-camera Delete/Protect vault integrity + orphan detection.
  3. Pillar C — `[Initial Focus Mag.]` movie (`x1.0` [default] / `x4.0`; `Focus Magnif. Time`:
     `2 Sec` / `5 Sec` / `No Limit` [default]) vs still (`x1.0`/`x2.1` Full-Frame; `x1.0`/`x1.5`
     APS-C/S35), `[Auto Magnifier in MF]` movie block, `[Marker Display]` suppression while magnified,
     and `[Bright Monitoring]` custom-key toggle lockout during `[Focus Magnifier]` /
     `[Auto Magnifier in MF]` plus `[Setting Effect OFF]` live-view lock and auto-cancel on
     power-off, leaving `P/A/S/M`, or leaving `Manual Focus (MF)`.
  4. Pillar D — Hard Zero-Write Firewall & 12-Touchpoint (`P211-01..P211-12`) 4-Class Matrix.
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

PHASE_211_SCHEMA = (
    "fx3-firmware-lab.realhw-hdmi-log1080-proxy-vault-and-focusmag-brightmon/v1"
)
PHASE_211_VERSION = "211.0.0"
AUDITOR_INDEX_P211 = "44/44"

FX3_APPFW_P211_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P211_RELPATH = FX6_APPFW_P146_RELPATH
FX3_UXC_EN_F_P211_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_f.uxc"
FX6_UXC_EN_P211_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX3_CPAPP_P211_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P211_RELPATH = FX6_CPAPP_P146_RELPATH

EXPECTED_FX3_APPFW_BYTES_P211 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P211 = 50_520_424
EXPECTED_FX3_UXC_EN_F_BYTES_P211 = 373_820
EXPECTED_FX6_UXC_EN_BYTES_P211 = 118_208
EXPECTED_FX3_CPAPP_BYTES_P211 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P211 = 17_952_816

CPAPP_BOUNDED_HEAD_BYTES_P211 = 768 * 1024
CPAPP_BOUNDED_TAIL_BYTES_P211 = 6 * 1024 * 1024
DONOR_COLD_SCAN_BUDGET_SEC_P211 = 0.15

# Pillar A: HDMI Output Settings, Log/PPLUT 1080p Downshift, Off(HDMI Only) 4K & LCD Blanking
FX3_HDMI_OUTPUT_SETTINGS_MENU_PATH_P211 = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
)
FX3_HDMI_INFO_DISPLAY_MENU_PATH_P211 = (
    "MENU -> Setup -> [External Output] -> [HDMI Info. Display]"
)
FX3_HDMI_RESOLUTION_MENU_PATH_P211 = (
    "MENU -> Setup -> [External Output] -> [HDMI Resolution]"
)

VALID_REC_MEDIA_DUR_HDMI_MODES_P211: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
VALID_HDMI_RESOLUTIONS_P211: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
VALID_LOG_SHOOTING_MODES_P211: Tuple[str, ...] = (
    "Off",
    "Cine EI",
    "Cine EI Quick",
    "Flexible ISO",
)
PPLUT_PICTURE_PROFILES_P211: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
VALID_PICTURE_PROFILES_P211: Tuple[str, ...] = (
    "Off",
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "PP6",
    "PP7",
    "PP8",
    "PP9",
    "PP10",
    "PP11",
    "PPLUT1",
    "PPLUT2",
    "PPLUT3",
    "PPLUT4",
)
VALID_ON_OFF_P211: Tuple[str, ...] = ("On", "Off")
VALID_DESQUEEZE_STATES_P211: Tuple[str, ...] = ("Off", "1.3x", "1.5x", "1.6x", "2.0x")
VALID_INTERNAL_REC_RESOLUTIONS_P211: Tuple[str, ...] = ("4K_DCI", "4K", "HD")

HDMI_RAW_SENSOR_RESOLUTION_P211: Tuple[int, int] = (4264, 2408)
HDMI_4K_DCI_RESOLUTION_P211: Tuple[int, int] = (4096, 2160)
HDMI_4K_UHD_RESOLUTION_P211: Tuple[int, int] = (3840, 2160)
HDMI_FHD_1080P_RESOLUTION_P211: Tuple[int, int] = (1920, 1080)

# Pillar B: Proxy Settings (2 formats / 3 bitrates), Cutoffs & Coupled CLIP/ + SUB/ Vault
FX3_PROXY_SETTINGS_MENU_PATH_P211 = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]"
)
DEFAULT_PROXY_FILE_FORMAT_P211 = "XAVC S HD"
PROXY_MAIN_CLIP_DIR_P211 = "/PRIVATE/M4ROOT/CLIP"
PROXY_SUB_DIR_P211 = "/PRIVATE/M4ROOT/SUB"
PROXY_SUB_SUFFIX_P211 = "S03.MP4"

FX3_PROXY_FORMAT_SPECS_P211: Dict[str, Dict[str, object]] = {
    "XAVC HS HD": {
        "resolution": (1920, 1080),
        "codec": "MPEG-H HEVC/H.265 Long GOP",
        "chroma_bit_depth": "4:2:0 10-bit",
        "audio": "LPCM 2ch 48kHz 16-bit",
        "bitrates": ("16M", "9M"),
        "default_bitrate": "9M",
        "max_ntsc_fps": "59.94p",
        "max_pal_fps": "50p",
        "appfw_enums": {
            "16M": "PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
            "9M": "PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD",
        },
    },
    "XAVC S HD": {
        "resolution": (1280, 720),
        "codec": "MPEG-4 AVC/H.264 Long GOP",
        "chroma_bit_depth": "4:2:0 8-bit",
        "audio": "LPCM 2ch 48kHz 16-bit",
        "bitrates": ("6M",),
        "default_bitrate": "6M",
        "max_ntsc_fps": "59.94p",
        "max_pal_fps": "50p",
        "appfw_enums": {
            "6M": "PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD",
        },
    },
}
FORBIDDEN_NON_FX3_PROXY_FORMATS_P211: Tuple[str, ...] = (
    "XAVC S-I",
    "ProRes Proxy",
    "XAVC Proxy MXF",
    "DNxHR LB",
)
VALID_REC_FRAME_RATES_P211: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
PROXY_CUTOFF_REC_FRAME_RATES_P211: Tuple[str, ...] = ("100p", "119.88p")
VALID_SQ_SENSOR_FPS_P211: Tuple[int, ...] = (
    1, 2, 3, 4, 6, 8, 12, 15, 24, 25, 30, 50, 60, 100, 120, 200, 240,
)
PROXY_CUTOFF_SQ_MIN_PAL_FPS_P211 = 100
PROXY_CUTOFF_SQ_MIN_NTSC_FPS_P211 = 120

VALID_VAULT_ACTIONS_P211: Tuple[str, ...] = ("DELETE", "PROTECT", "UNPROTECT", "VERIFY_ONLY")
VALID_VAULT_SCOPES_P211: Tuple[str, ...] = ("COUPLED_PAIR", "CLIP_ONLY", "SUB_ONLY")

# Pillar C: Focus Magnifier (Movie x1.0/x4.0 vs Still FF x1.0/x2.1 & APS-C x1.0/x1.5) & Bright Monitoring
FX3_INITIAL_FOCUS_MAG_MENU_PATH_P211 = (
    "MENU -> Focus -> [Focus Assistant] -> [Initial Focus Mag.]"
)
VALID_MOVIE_INITIAL_FOCUS_MAG_P211: Tuple[str, ...] = ("x1.0", "x4.0")
VALID_STILL_FF_INITIAL_FOCUS_MAG_P211: Tuple[str, ...] = ("x1.0", "x2.1")
VALID_STILL_APSC_INITIAL_FOCUS_MAG_P211: Tuple[str, ...] = ("x1.0", "x1.5")
VALID_FOCUS_MAGNIF_TIMES_P211: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
VALID_CAPTURE_MODES_P211: Tuple[str, ...] = ("Movie", "S&Q", "Still")
VALID_SENSOR_CROP_MODES_P211: Tuple[str, ...] = ("Full-Frame", "APS-C_S35")
PASM_EXPOSURE_MODES_P211: Tuple[str, ...] = ("P", "A", "S", "M")
VALID_EXPOSURE_MODES_P211: Tuple[str, ...] = (
    "P",
    "A",
    "S",
    "M",
    "Flexible Exp.",
    "Auto",
    "Scene",
)
VALID_FOCUS_MODES_P211: Tuple[str, ...] = ("AF-S", "AF-C", "DMF", "MF")

# Verified Donor Binary Markers
APPFW_SHARED_WAVE28_MARKERS_P211: Tuple[str, ...] = (
    "N5model38setting_rec_media_during_hdmi_output_tE",
    "N5model32setting_hdmi_4k_output_setting_tE",
    "N5model27setting_hdmi_info_display_tE",
    "N5model28setting_sq_proxy_recording_tE",
    "N5model30setting_sq_proxy_file_format_tE",
    "N5model37setting_mov_init_ratio_focus_magnif_tE",
    "N5model19setting_mf_assist_tE",
    "N5model24setting_marker_display_tE",
    "N5model33setting_bright_monitoring_state_tE",
    "HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_10BIT",
    "MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0",
    "FOCUS_MAGNIFICATION_TIME_NO_LIMIT",
)
APPFW_FX3_702_EXCLUSIVE_MARKERS_P211: Tuple[str, ...] = (
    "PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
    "PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD",
    "PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD",
    "BKID_APP_setting_rec_media_during_hdmi_output",
    "BKID_APP_setting_hdmi_4k_output_setting",
    "BKID_APP_setting_hdmi_info_display",
    "BKID_APP_setting_raw_output",
    "CAUTION_ID_FACTOR_PICTURE_PROFILE_PPLUT_MSG",
    "EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
    "CAUTION_ID_FACTOR_REC_MEDIA_DUR_HDMI_OUTPUT_OFF_MSG",
)
APPFW_FX6_601_EXCLUSIVE_MARKERS_P211: Tuple[str, ...] = (
    "BKID_APP_EXTERN_SQ_PROXY_RECORDING_PROCAM",
    "BKID_APP_EXTERN_PROXY_REC_BITRATE_PROCAM",
    "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6",
    "BKID_APP_SETTING_HDMI_INFO_DISPLAY",
)

UXC_FX3_EN_F_REQUIRED_TOKENS_P211: Tuple[str, ...] = (
    "HDMI Output Settings",
    "Rec. Media dur HDMI Output",
    "Off(HDMI Only)",
    "4K Output Set.(HDMI Only)",
    "HDMI Info. Display",
    "Emphasized REC Display",
    "RAW Output",
    "Log Shooting",
    "Proxy Settings",
    "Proxy Recording",
    "Proxy File Format",
    "XAVC HS HD",
    "XAVC S HD",
    "Initial Focus Mag.",
    "Focus Magnif. Time",
    "Auto Magnifier in MF",
    "Marker Display",
    "Bright Monitoring",
    "Setting Effect OFF",
)
UXC_FX6_EN_REQUIRED_TOKENS_P211: Tuple[str, ...] = (
    "HDMI",
    "RAW Output",
    "Proxy",
    "Focus Magnifier",
    "Marker",
    "Protect",
    "Delete",
    "XAVC",
)

CPAPP_SHARED_MARKERS_P211: Tuple[str, ...] = (
    "HDMI",
    "Proxy",
    "SUB",
    "CLIP",
    "Magnif",
    "Marker",
    "Bright",
    "1080",
    "RAW",
)

# Pillar D: Zero-Write Firewall
FORBIDDEN_PERSISTENT_TARGET_RE_P211 = re.compile(
    r"(^p2:/setting\b|^p3:/\b|^p5:/wbi\b|^p8:/\b|^p12:/cert\b|^p18:/lens\b"
    r"|/dev/c?p?nflasha\d*\b|spi_nor:|Backup\.bin\b|BODYDATA\.DAT\b|cpapp-b\.bin\b)",
    re.IGNORECASE,
)
VOLATILE_ALLOWED_PREFIXES_P211: Tuple[str, ...] = (
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
)
VOLATILE_WAVE28_OVERLAY_DIR_P211 = "/tmp/fx6_wave28_hdmi_proxy_focusmag_overlay"


@dataclass(frozen=True)
class BoundedUxcSummaryP211:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    header_magic_hex: str
    token_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedCpappSummaryP211:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bounded_bytes_scanned: int
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class HdmiLog1080pVsHdmiOnly4kEvalResult:
    rec_media_dur_hdmi: str
    raw_output: str
    hdmi_4k_output_set: str
    hdmi_resolution_menu: str
    log_shooting: str
    picture_profile: str
    log_or_pplut_active: bool
    internal_card_recording_permitted: bool
    proxy_recording_permitted_by_hdmi: bool
    forced_1080p_downshift_by_log_or_pplut: bool
    effective_hdmi_signal_class: str
    effective_hdmi_resolution: Tuple[int, int]
    effective_hdmi_bit_depth: int
    effective_hdmi_info_display: str
    hdmi_info_display_forced_off: bool
    camera_lcd_live_view_blanked: bool
    hdmi_emphasized_rec_border_visible: bool
    hdmi_desqueeze_applied: bool
    reason: str


@dataclass(frozen=True)
class Pillar1HdmiLog1080pAndHdmiOnly4kReport:
    fx3_appfw: ElfSectionSummary
    fx6_appfw: ElfSectionSummary
    fx3_uxc_en_f: BoundedUxcSummaryP211
    fx6_uxc_en: BoundedUxcSummaryP211
    shared_hdmi_markers_verified: bool
    fx3_702_hdmi_pplut_markers_verified: bool
    log_cine_ei_rec_on_downshifts_1080p: bool
    pplut1_to_4_rec_on_downshifts_1080p: bool
    hdmionly_unlocks_4k_10bit_all_six_rates: bool
    raw_output_delivers_4264x2408_16bit: bool
    hdmionly_and_raw_force_hdmi_info_off: bool
    hdmi_info_on_blanks_builtin_lcd: bool
    sample_scenarios: Tuple[HdmiLog1080pVsHdmiOnly4kEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class ProxyCodecAndCutoffEvalResult:
    proxy_recording_setting: str
    proxy_file_format: str
    proxy_bitrate: str
    capture_mode: str
    rec_frame_rate: str
    sq_sensor_fps: Optional[int]
    rec_media_dur_hdmi: str
    proxy_active: bool
    cutoff_reason: str
    proxy_resolution: Optional[Tuple[int, int]]
    proxy_codec: Optional[str]
    proxy_chroma_bit_depth: Optional[str]
    appfw_record_setting_enum: Optional[str]
    main_clip_dir: str
    proxy_sub_dir: str
    on_camera_proxy_playback_supported: bool
    playback_thumbnail_px_badge_shown: bool


@dataclass(frozen=True)
class CoupledClipSubVaultEvalResult:
    clip_stem: str
    action: str
    scope: str
    in_camera: bool
    allowed: bool
    single_sided_incamera_op_rejected: bool
    resulting_clip_present: bool
    resulting_sub_present: bool
    resulting_protected: bool
    integrity_status: str
    orphan_anomaly: Optional[str]
    reason: str


@dataclass(frozen=True)
class Pillar2ProxyMatrixAndCoupledVaultReport:
    fx3_cpapp: BoundedCpappSummaryP211
    fx6_cpapp: BoundedCpappSummaryP211
    exact_two_formats_three_bitrates_verified: bool
    fx3_appfw_three_proxy_enums_verified: bool
    hfr_120p_100p_cutoff_verified: bool
    sq_120fps_100fps_cutoff_verified: bool
    hdmionly_zero_card_proxy_verified: bool
    zero_oncamera_proxy_playback_verified: bool
    atomic_coupled_delete_protect_verified: bool
    orphan_detection_verified: bool
    sample_proxy_scenarios: Tuple[ProxyCodecAndCutoffEvalResult, ...]
    sample_vault_scenarios: Tuple[CoupledClipSubVaultEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class FocusMagAndBrightMonitoringEvalResult:
    capture_mode: str
    sensor_crop_mode: str
    exposure_mode: str
    focus_mode: str
    initial_focus_mag: str
    focus_magnif_time: str
    auto_magnifier_in_mf_setting: str
    focus_magnifier_active: bool
    auto_magnifier_triggered_active: bool
    marker_display_setting: str
    bright_monitoring_prior_active: bool
    bright_monitoring_key_pressed: bool
    power_off_event: bool
    auto_magnifier_in_mf_effective: bool
    auto_magnifier_blocked_in_movie: bool
    marker_display_visible: bool
    marker_display_suppressed_by_magnifier: bool
    bright_monitoring_key_locked_out: bool
    bright_monitoring_active_after: bool
    bright_monitoring_auto_canceled: bool
    effective_live_view_display: str
    reason: str


@dataclass(frozen=True)
class Pillar3FocusMagAndBrightMonReport:
    movie_x10_x40_scales_verified: bool
    still_ff_x21_and_apsc_x15_verified: bool
    auto_magnifier_blocked_in_movie_verified: bool
    marker_suppressed_during_magnifier_verified: bool
    bright_mon_custom_key_lockout_verified: bool
    bright_mon_pasm_mf_autocancel_and_liveview_off_verified: bool
    sample_interlock_scenarios: Tuple[FocusMagAndBrightMonitoringEvalResult, ...]
    passed: bool


@dataclass(frozen=True)
class Phase211WriteGuardResult:
    target_path: str
    operation: str
    allowed: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    reason: str


@dataclass(frozen=True)
class Phase211TouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx3_702_artifact: str
    fx6_601_artifact: str
    bridge_class: str
    rationale: str


@dataclass(frozen=True)
class Phase211CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    entries: Tuple[Phase211TouchpointEntry, ...]
    all_classes_valid: bool


@dataclass(frozen=True)
class Pillar4Phase211WriteGuardAndMatrixReport:
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    volatile_overlay_dir: str
    guard_evaluations: Tuple[Phase211WriteGuardResult, ...]
    matrix: Phase211CompatMatrixSummary
    passed: bool


@dataclass(frozen=True)
class RealhwHdmiLog1080ProxyVaultAndFocusmagBrightmonReport:
    schema: str
    version: str
    auditor_index: str
    source_mode: str
    clean_room_forced: bool
    donor_cold_scan_duration_sec: float
    donor_cold_scan_within_sla: bool
    pillar_1_hdmi_log_1080p_and_hdmionly_4k: Pillar1HdmiLog1080pAndHdmiOnly4kReport
    pillar_2_proxy_matrix_and_coupled_vault: Pillar2ProxyMatrixAndCoupledVaultReport
    pillar_3_focusmag_and_bright_monitoring: Pillar3FocusMagAndBrightMonReport
    pillar_4_write_guard_and_matrix: Pillar4Phase211WriteGuardAndMatrixReport
    report_digest_sha256: str
    all_checks_passed: bool


_DONOR_SCAN_CACHE_P211: Dict[
    str,
    Tuple[
        ElfSectionSummary,
        ElfSectionSummary,
        BoundedUxcSummaryP211,
        BoundedUxcSummaryP211,
        BoundedCpappSummaryP211,
        BoundedCpappSummaryP211,
        float,
    ],
] = {}


def _scan_uxc_rdonly_p211(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> BoundedUxcSummaryP211:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0)
    finally:
        os.close(fd)
    magic_hex = buf[:4].hex() if len(buf) >= 4 else ""
    hits = {tok: buf.count(tok.encode("utf-8")) for tok in tokens}
    return BoundedUxcSummaryP211(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        file_bytes=sz,
        header_magic_hex=magic_hex,
        token_hits=hits,
    )


def _scan_cpapp_head_tail_rdonly_p211(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    markers: Sequence[str],
) -> BoundedCpappSummaryP211:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        head_len = min(CPAPP_BOUNDED_HEAD_BYTES_P211, sz)
        head = os.pread(fd, head_len, 0)
        tail_off = max(head_len, sz - CPAPP_BOUNDED_TAIL_BYTES_P211)
        tail_len = max(0, sz - tail_off)
        tail = os.pread(fd, tail_len, tail_off) if tail_len > 0 else b""
    finally:
        os.close(fd)
    hits = {
        m: (1 if (bm := m.encode("ascii")) in head or (tail and bm in tail) else 0)
        for m in markers
    }
    return BoundedCpappSummaryP211(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        file_bytes=sz,
        bounded_bytes_scanned=head_len + tail_len,
        marker_hits=hits,
    )


def build_clean_room_realhw_hdmi_log1080_proxy_focusmag_brightmon_fixtures() -> Tuple[
    ElfSectionSummary,
    ElfSectionSummary,
    BoundedUxcSummaryP211,
    BoundedUxcSummaryP211,
    BoundedCpappSummaryP211,
    BoundedCpappSummaryP211,
]:
    """Build deterministic clean-room synthetic Wave-28 summaries with zero proprietary bytes."""
    all_app_tokens = list(
        APPFW_SHARED_WAVE28_MARKERS_P211
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P211
        + APPFW_FX6_601_EXCLUSIVE_MARKERS_P211
    )
    fx3_elf_buf = _build_synthetic_elf64(
        exports=("appfw_fx3_702_wave28_entry",),
        imports=("mpr_Delete", "mpr_Protect"),
        dt_needed=("libmpr.so", "libInfraAvbbc.so"),
        rodata_strings=(APPFW_SHARED_WAVE28_MARKERS_P211 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P211),
    )
    fx6_elf_buf = _build_synthetic_elf64(
        exports=("appfw_fx6_601_wave28_entry",),
        imports=("mpr_Delete", "mpr_Protect"),
        dt_needed=("libmpr.so", "libInfraAvbbc.so"),
        rodata_strings=(APPFW_SHARED_WAVE28_MARKERS_P211 + APPFW_FX6_601_EXCLUSIVE_MARKERS_P211),
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
    fx3_app = dataclasses.replace(fx3_raw, file_bytes=EXPECTED_FX3_APPFW_BYTES_P211)
    fx6_app = dataclasses.replace(fx6_raw, file_bytes=EXPECTED_FX6_APPFW_BYTES_P211)

    fx3_uxc = BoundedUxcSummaryP211(
        binary_name="string_english_f.uxc",
        body_label="ILME-FX3_v7.02",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX3_UXC_EN_F_BYTES_P211,
        header_magic_hex="75786407",
        token_hits={tok: 1 for tok in UXC_FX3_EN_F_REQUIRED_TOKENS_P211},
    )
    fx6_uxc = BoundedUxcSummaryP211(
        binary_name="string_english.uxc",
        body_label="ILME-FX6_v6.01",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX6_UXC_EN_BYTES_P211,
        header_magic_hex="75786407",
        token_hits={tok: 1 for tok in UXC_FX6_EN_REQUIRED_TOKENS_P211},
    )
    bounded_len = CPAPP_BOUNDED_HEAD_BYTES_P211 + CPAPP_BOUNDED_TAIL_BYTES_P211
    fx3_cp = BoundedCpappSummaryP211(
        binary_name="CPAPP-B.BIN",
        body_label="ILME-FX3_v7.02",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX3_CPAPP_BYTES_P211,
        bounded_bytes_scanned=bounded_len,
        marker_hits={m: 2 for m in CPAPP_SHARED_MARKERS_P211},
    )
    fx6_cp = BoundedCpappSummaryP211(
        binary_name="cpapp-b.bin",
        body_label="ILME-FX6_v6.01",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=EXPECTED_FX6_CPAPP_BYTES_P211,
        bounded_bytes_scanned=bounded_len,
        marker_hits={m: 2 for m in CPAPP_SHARED_MARKERS_P211},
    )
    return fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp


def _scan_elf_singlepass_rdonly_p211(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> ElfSectionSummary:
    """Strictly O_RDONLY SIMD ELF64 section & marker scanner (<0.05s per binary)."""
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


def _scan_donor_artifacts_p211(
    repo_root: Path,
) -> Optional[
    Tuple[
        ElfSectionSummary,
        ElfSectionSummary,
        BoundedUxcSummaryP211,
        BoundedUxcSummaryP211,
        BoundedCpappSummaryP211,
        BoundedCpappSummaryP211,
        float,
    ]
]:
    cache_key = str(repo_root.resolve())
    if cache_key in _DONOR_SCAN_CACHE_P211:
        return _DONOR_SCAN_CACHE_P211[cache_key]

    fx3_app_p = resolve_donor_file(FX3_APPFW_P211_RELPATH, repo_root=repo_root)
    fx6_app_p = resolve_donor_file(FX6_APPFW_P211_RELPATH, repo_root=repo_root)
    fx3_uxc_p = resolve_donor_file(FX3_UXC_EN_F_P211_RELPATH, repo_root=repo_root)
    fx6_uxc_p = resolve_donor_file(FX6_UXC_EN_P211_RELPATH, repo_root=repo_root)
    fx3_cp_p = resolve_donor_file(FX3_CPAPP_P211_RELPATH, repo_root=repo_root)
    fx6_cp_p = resolve_donor_file(FX6_CPAPP_P211_RELPATH, repo_root=repo_root)
    if not all((fx3_app_p, fx6_app_p, fx3_uxc_p, fx6_uxc_p, fx3_cp_p, fx6_cp_p)):
        return None

    assert fx3_app_p is not None and fx6_app_p is not None
    assert fx3_uxc_p is not None and fx6_uxc_p is not None
    assert fx3_cp_p is not None and fx6_cp_p is not None

    all_app_tokens = (
        APPFW_SHARED_WAVE28_MARKERS_P211
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P211
        + APPFW_FX6_601_EXCLUSIVE_MARKERS_P211
    )

    t0 = time.perf_counter()
    fx3_app = _scan_elf_singlepass_rdonly_p211(
        fx3_app_p,
        binary_name="appFw.so",
        body_label="ILME-FX3_v7.02",
        tokens=all_app_tokens,
    )
    fx6_app = _scan_elf_singlepass_rdonly_p211(
        fx6_app_p,
        binary_name="appFw.so",
        body_label="ILME-FX6_v6.01",
        tokens=all_app_tokens,
    )
    fx3_uxc = _scan_uxc_rdonly_p211(
        fx3_uxc_p,
        binary_name="string_english_f.uxc",
        body_label="ILME-FX3_v7.02",
        tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P211,
    )
    fx6_uxc = _scan_uxc_rdonly_p211(
        fx6_uxc_p,
        binary_name="string_english.uxc",
        body_label="ILME-FX6_v6.01",
        tokens=UXC_FX6_EN_REQUIRED_TOKENS_P211,
    )
    fx3_cp = _scan_cpapp_head_tail_rdonly_p211(
        fx3_cp_p,
        binary_name="CPAPP-B.BIN",
        body_label="ILME-FX3_v7.02",
        markers=CPAPP_SHARED_MARKERS_P211,
    )
    fx6_cp = _scan_cpapp_head_tail_rdonly_p211(
        fx6_cp_p,
        binary_name="cpapp-b.bin",
        body_label="ILME-FX6_v6.01",
        markers=CPAPP_SHARED_MARKERS_P211,
    )
    dt = time.perf_counter() - t0
    res = (fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp, dt)
    _DONOR_SCAN_CACHE_P211[cache_key] = res
    return res


def evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
    *,
    rec_media_dur_hdmi: str = "On",
    raw_output: str = "Off",
    hdmi_4k_output_set: str = "23.98p 10bit",
    hdmi_resolution_menu: str = "Auto",
    log_shooting: str = "Off",
    picture_profile: str = "Off",
    hdmi_info_display_requested: str = "Off",
    emphasized_rec_display: str = "Off",
    desqueeze_display: str = "Off",
    hdmi_cable_connected: bool = True,
    internal_rec_resolution: str = "4K",
    rec_frame_rate: str = "23.98p",
    dci_4k_24_00p_enabled: bool = False,
) -> HdmiLog1080pVsHdmiOnly4kEvalResult:
    """Evaluate Wave-28 FX3 Ver. 7.02 HDMI output resolution, Log/PPLUT 1080p clamp & LCD blanking."""
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI_MODES_P211:
        raise ValueError(f"Unsupported [Rec. Media dur HDMI Output]: {rec_media_dur_hdmi!r}")
    if raw_output not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [RAW Output]: {raw_output!r}")
    if hdmi_4k_output_set not in VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211:
        raise ValueError(f"Unsupported [4K Output Set.(HDMI Only)]: {hdmi_4k_output_set!r}")
    if hdmi_resolution_menu not in VALID_HDMI_RESOLUTIONS_P211:
        raise ValueError(f"Unsupported [HDMI Resolution]: {hdmi_resolution_menu!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES_P211:
        raise ValueError(f"Unsupported [Log Shooting]: {log_shooting!r}")
    if picture_profile not in VALID_PICTURE_PROFILES_P211:
        raise ValueError(f"Unsupported [Picture Profile]: {picture_profile!r}")
    if hdmi_info_display_requested not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [HDMI Info. Display]: {hdmi_info_display_requested!r}")
    if emphasized_rec_display not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [Emphasized REC Display]: {emphasized_rec_display!r}")
    if desqueeze_display not in VALID_DESQUEEZE_STATES_P211:
        raise ValueError(f"Unsupported [De-Squeeze Display]: {desqueeze_display!r}")
    if internal_rec_resolution not in VALID_INTERNAL_REC_RESOLUTIONS_P211:
        raise ValueError(f"Unsupported internal_rec_resolution: {internal_rec_resolution!r}")
    if rec_frame_rate not in VALID_REC_FRAME_RATES_P211:
        raise ValueError(f"Unsupported [Rec Frame Rate]: {rec_frame_rate!r}")

    pplut_selected = (log_shooting == "Off") and (picture_profile in PPLUT_PICTURE_PROFILES_P211)
    log_or_pplut_active = (log_shooting != "Off") or pplut_selected

    if raw_output == "On":
        rec_permitted = rec_media_dur_hdmi == "On"
        return HdmiLog1080pVsHdmiOnly4kEvalResult(
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            raw_output=raw_output,
            hdmi_4k_output_set=hdmi_4k_output_set,
            hdmi_resolution_menu=hdmi_resolution_menu,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            log_or_pplut_active=log_or_pplut_active,
            internal_card_recording_permitted=rec_permitted,
            proxy_recording_permitted_by_hdmi=rec_permitted,
            forced_1080p_downshift_by_log_or_pplut=False,
            effective_hdmi_signal_class="RAW_16BIT_LINEAR_4264x2408",
            effective_hdmi_resolution=HDMI_RAW_SENSOR_RESOLUTION_P211,
            effective_hdmi_bit_depth=16,
            effective_hdmi_info_display="Off",
            hdmi_info_display_forced_off=True,
            camera_lcd_live_view_blanked=False,
            hdmi_emphasized_rec_border_visible=False,
            hdmi_desqueeze_applied=False,
            reason="RAW Output=On emits 4264x2408 16-bit linear RAW and forces HDMI Info. Display=Off",
        )

    if rec_media_dur_hdmi == "Off(HDMI Only)":
        out_res = (
            HDMI_4K_DCI_RESOLUTION_P211
            if (hdmi_4k_output_set == "24.00p 10bit" and dci_4k_24_00p_enabled)
            else HDMI_4K_UHD_RESOLUTION_P211
        )
        return HdmiLog1080pVsHdmiOnly4kEvalResult(
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            raw_output=raw_output,
            hdmi_4k_output_set=hdmi_4k_output_set,
            hdmi_resolution_menu=hdmi_resolution_menu,
            log_shooting=log_shooting,
            picture_profile=picture_profile,
            log_or_pplut_active=log_or_pplut_active,
            internal_card_recording_permitted=False,
            proxy_recording_permitted_by_hdmi=False,
            forced_1080p_downshift_by_log_or_pplut=False,
            effective_hdmi_signal_class="YCBCR_422_10BIT_4K_HDMI_ONLY",
            effective_hdmi_resolution=out_res,
            effective_hdmi_bit_depth=10,
            effective_hdmi_info_display="Off",
            hdmi_info_display_forced_off=True,
            camera_lcd_live_view_blanked=False,
            hdmi_emphasized_rec_border_visible=False,
            hdmi_desqueeze_applied=False,
            reason=(
                f"Off(HDMI Only) disables internal card/proxy recording, unlocks 4K 10-bit "
                f"({hdmi_4k_output_set}), and forces HDMI Info. Display=Off"
            ),
        )

    # rec_media_dur_hdmi == "On" and raw_output == "Off"
    forced_downshift = log_or_pplut_active
    if forced_downshift:
        out_res = HDMI_FHD_1080P_RESOLUTION_P211
        sig_class = "YCBCR_1080P_CLAMPED_BY_LOG_OR_PPLUT"
    elif (
        hdmi_resolution_menu in ("Auto", "2160p")
        and internal_rec_resolution in ("4K", "4K_DCI")
        and rec_frame_rate not in PROXY_CUTOFF_REC_FRAME_RATES_P211
    ):
        out_res = (
            HDMI_4K_DCI_RESOLUTION_P211
            if internal_rec_resolution == "4K_DCI"
            else HDMI_4K_UHD_RESOLUTION_P211
        )
        sig_class = "YCBCR_4K_WITH_CARD_REC"
    else:
        out_res = HDMI_FHD_1080P_RESOLUTION_P211
        sig_class = "YCBCR_1080_STANDARD"

    eff_info = "On" if (hdmi_cable_connected and hdmi_info_display_requested == "On") else "Off"
    lcd_blanked = eff_info == "On"
    red_border_hdmi = lcd_blanked and (emphasized_rec_display == "On")
    hdmi_desqueeze = (
        hdmi_cable_connected
        and desqueeze_display != "Off"
        and log_shooting != "Off"
        and eff_info == "Off"
    )
    reason = (
        "Log Shooting or PPLUT1..4 with Rec. Media=On & RAW=Off forces HDMI down to 1080p"
        if forced_downshift
        else "Standard HDMI output with internal card recording On"
    )
    if lcd_blanked:
        reason += "; HDMI Info. Display=On renders overlays on HDMI and blanks built-in LCD"

    return HdmiLog1080pVsHdmiOnly4kEvalResult(
        rec_media_dur_hdmi=rec_media_dur_hdmi,
        raw_output=raw_output,
        hdmi_4k_output_set=hdmi_4k_output_set,
        hdmi_resolution_menu=hdmi_resolution_menu,
        log_shooting=log_shooting,
        picture_profile=picture_profile,
        log_or_pplut_active=log_or_pplut_active,
        internal_card_recording_permitted=True,
        proxy_recording_permitted_by_hdmi=True,
        forced_1080p_downshift_by_log_or_pplut=forced_downshift,
        effective_hdmi_signal_class=sig_class,
        effective_hdmi_resolution=out_res,
        effective_hdmi_bit_depth=10,
        effective_hdmi_info_display=eff_info,
        hdmi_info_display_forced_off=False,
        camera_lcd_live_view_blanked=lcd_blanked,
        hdmi_emphasized_rec_border_visible=red_border_hdmi,
        hdmi_desqueeze_applied=hdmi_desqueeze,
        reason=reason,
    )


def evaluate_proxy_codec_matrix_and_hfr_cutoffs(
    *,
    proxy_recording_setting: str = "On",
    proxy_file_format: str = DEFAULT_PROXY_FILE_FORMAT_P211,
    proxy_bitrate: Optional[str] = None,
    capture_mode: str = "Movie",
    rec_frame_rate: str = "23.98p",
    sq_sensor_fps: Optional[int] = None,
    ntsc_pal_region: str = "NTSC",
    rec_media_dur_hdmi: str = "On",
) -> ProxyCodecAndCutoffEvalResult:
    """Evaluate FX3 Ver. 7.02 2-format/3-bitrate Proxy schema, HFR/S&Q/HDMI cutoffs & zero playback."""
    if proxy_recording_setting not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [Proxy Recording]: {proxy_recording_setting!r}")
    if proxy_file_format not in FX3_PROXY_FORMAT_SPECS_P211:
        raise ValueError(f"Unsupported FX3 [Proxy File Format]: {proxy_file_format!r}")
    if capture_mode not in ("Movie", "S&Q"):
        raise ValueError(f"Unsupported capture_mode for proxy check: {capture_mode!r}")
    if rec_frame_rate not in VALID_REC_FRAME_RATES_P211:
        raise ValueError(f"Unsupported [Rec Frame Rate]: {rec_frame_rate!r}")
    if ntsc_pal_region not in ("NTSC", "PAL"):
        raise ValueError(f"Unsupported ntsc_pal_region: {ntsc_pal_region!r}")
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI_MODES_P211:
        raise ValueError(f"Unsupported [Rec. Media dur HDMI Output]: {rec_media_dur_hdmi!r}")

    spec = FX3_PROXY_FORMAT_SPECS_P211[proxy_file_format]
    valid_bitrates = spec["bitrates"]
    assert isinstance(valid_bitrates, tuple)
    chosen_bitrate = str(spec["default_bitrate"]) if proxy_bitrate is None else proxy_bitrate
    if chosen_bitrate not in valid_bitrates:
        raise ValueError(
            f"Bitrate {chosen_bitrate!r} invalid for {proxy_file_format!r}; allowed={valid_bitrates}"
        )

    if capture_mode == "S&Q":
        eff_sq = 60 if sq_sensor_fps is None else sq_sensor_fps
        if eff_sq not in VALID_SQ_SENSOR_FPS_P211:
            raise ValueError(f"Unsupported S&Q sensor frame rate: {eff_sq}")
    else:
        eff_sq = sq_sensor_fps

    cutoff = "NONE"
    if proxy_recording_setting == "Off":
        cutoff = "PROXY_RECORDING_SWITCHED_OFF"
    elif rec_media_dur_hdmi == "Off(HDMI Only)":
        cutoff = "REC_MEDIA_OFF_HDMI_ONLY"
    elif rec_frame_rate in PROXY_CUTOFF_REC_FRAME_RATES_P211:
        cutoff = "REC_FRAME_RATE_119_88P_OR_100P"
    elif capture_mode == "S&Q" and eff_sq is not None:
        sq_limit = (
            PROXY_CUTOFF_SQ_MIN_NTSC_FPS_P211
            if ntsc_pal_region == "NTSC"
            else PROXY_CUTOFF_SQ_MIN_PAL_FPS_P211
        )
        if eff_sq >= sq_limit:
            cutoff = f"SQ_SENSOR_FPS_GE_{sq_limit}"

    active = cutoff == "NONE"
    enums = spec["appfw_enums"]
    assert isinstance(enums, dict)
    res_tuple = spec["resolution"]
    assert isinstance(res_tuple, tuple)

    return ProxyCodecAndCutoffEvalResult(
        proxy_recording_setting=proxy_recording_setting,
        proxy_file_format=proxy_file_format,
        proxy_bitrate=chosen_bitrate,
        capture_mode=capture_mode,
        rec_frame_rate=rec_frame_rate,
        sq_sensor_fps=eff_sq,
        rec_media_dur_hdmi=rec_media_dur_hdmi,
        proxy_active=active,
        cutoff_reason=cutoff,
        proxy_resolution=res_tuple if active else None,
        proxy_codec=str(spec["codec"]) if active else None,
        proxy_chroma_bit_depth=str(spec["chroma_bit_depth"]) if active else None,
        appfw_record_setting_enum=str(enums[chosen_bitrate]) if active else None,
        main_clip_dir=PROXY_MAIN_CLIP_DIR_P211,
        proxy_sub_dir=PROXY_SUB_DIR_P211,
        on_camera_proxy_playback_supported=False,
        playback_thumbnail_px_badge_shown=active,
    )


def evaluate_coupled_clip_sub_vault_integrity(
    *,
    clip_stem: str = "C0001",
    clip_present: bool = True,
    sub_present: bool = True,
    expect_proxy_pair: bool = True,
    clip_protected: bool = False,
    sub_protected: bool = False,
    action: str = "VERIFY_ONLY",
    scope: str = "COUPLED_PAIR",
    in_camera: bool = True,
) -> CoupledClipSubVaultEvalResult:
    """Evaluate atomic coupled M4ROOT/CLIP/ + M4ROOT/SUB/ Delete/Protect & recovery orphan audit."""
    if not clip_stem or "/" in clip_stem or ".." in clip_stem:
        raise ValueError(f"Invalid clip_stem: {clip_stem!r}")
    if action not in VALID_VAULT_ACTIONS_P211:
        raise ValueError(f"Unsupported vault action: {action!r}")
    if scope not in VALID_VAULT_SCOPES_P211:
        raise ValueError(f"Unsupported vault scope: {scope!r}")

    # Pre-check external orphan / split-protection anomalies
    orphan: Optional[str] = None
    if sub_present and not clip_present:
        orphan = "ORPHAN_SUB_WITHOUT_CLIP"
    elif expect_proxy_pair and clip_present and not sub_present:
        orphan = "MISSING_SUB_FOR_PX_CLIP"
    elif clip_present and sub_present and (clip_protected != sub_protected):
        orphan = "DESYNCED_CLIP_SUB_PROTECT_FLAGS"

    if in_camera and action in ("DELETE", "PROTECT", "UNPROTECT") and scope != "COUPLED_PAIR":
        return CoupledClipSubVaultEvalResult(
            clip_stem=clip_stem,
            action=action,
            scope=scope,
            in_camera=in_camera,
            allowed=False,
            single_sided_incamera_op_rejected=True,
            resulting_clip_present=clip_present,
            resulting_sub_present=sub_present,
            resulting_protected=(clip_protected or sub_protected),
            integrity_status="REJECTED_SINGLE_SIDED_INCAMERA_OP",
            orphan_anomaly=orphan,
            reason=(
                "FX3 in-camera Delete/Protect on (Px) clips operates atomically on BOTH "
                "M4ROOT/CLIP/ and M4ROOT/SUB/; single-sided operation is impossible"
            ),
        )

    if action == "VERIFY_ONLY":
        ok = orphan is None
        return CoupledClipSubVaultEvalResult(
            clip_stem=clip_stem,
            action=action,
            scope=scope,
            in_camera=in_camera,
            allowed=ok,
            single_sided_incamera_op_rejected=False,
            resulting_clip_present=clip_present,
            resulting_sub_present=sub_present,
            resulting_protected=(clip_protected and (sub_protected or not sub_present)),
            integrity_status="COUPLED_VAULT_HEALTHY" if ok else "VAULT_ANOMALY_DETECTED",
            orphan_anomaly=orphan,
            reason="Vault pair healthy" if ok else f"Detected vault anomaly: {orphan}",
        )

    if action == "DELETE":
        if clip_protected or sub_protected:
            return CoupledClipSubVaultEvalResult(
                clip_stem=clip_stem,
                action=action,
                scope=scope,
                in_camera=in_camera,
                allowed=False,
                single_sided_incamera_op_rejected=False,
                resulting_clip_present=clip_present,
                resulting_sub_present=sub_present,
                resulting_protected=True,
                integrity_status="BLOCKED_BY_PROTECT_LOCK",
                orphan_anomaly=orphan,
                reason="Protected (Px) clip pair cannot be deleted (mpr_Delete Protect NG)",
            )
        if scope == "COUPLED_PAIR":
            return CoupledClipSubVaultEvalResult(
                clip_stem=clip_stem,
                action=action,
                scope=scope,
                in_camera=in_camera,
                allowed=True,
                single_sided_incamera_op_rejected=False,
                resulting_clip_present=False,
                resulting_sub_present=False,
                resulting_protected=False,
                integrity_status="ATOMIC_COUPLED_DELETED",
                orphan_anomaly=None,
                reason=f"Atomically deleted {clip_stem}.MP4 and {clip_stem}{PROXY_SUB_SUFFIX_P211}",
            )
        # External host single-sided mutation creates an orphan hazard
        res_clip = False if scope == "CLIP_ONLY" else clip_present
        res_sub = False if scope == "SUB_ONLY" else sub_present
        new_orphan = (
            "ORPHAN_SUB_WITHOUT_CLIP"
            if (res_sub and not res_clip)
            else ("MISSING_SUB_FOR_PX_CLIP" if (expect_proxy_pair and res_clip and not res_sub) else None)
        )
        return CoupledClipSubVaultEvalResult(
            clip_stem=clip_stem,
            action=action,
            scope=scope,
            in_camera=in_camera,
            allowed=False,
            single_sided_incamera_op_rejected=False,
            resulting_clip_present=res_clip,
            resulting_sub_present=res_sub,
            resulting_protected=False,
            integrity_status="VAULT_ANOMALY_DETECTED",
            orphan_anomaly=new_orphan,
            reason=f"External single-sided delete broke coupled vault integrity ({new_orphan})",
        )

    # PROTECT or UNPROTECT
    target_prot = action == "PROTECT"
    return CoupledClipSubVaultEvalResult(
        clip_stem=clip_stem,
        action=action,
        scope=scope,
        in_camera=in_camera,
        allowed=orphan is None,
        single_sided_incamera_op_rejected=False,
        resulting_clip_present=clip_present,
        resulting_sub_present=sub_present,
        resulting_protected=target_prot,
        integrity_status="ATOMIC_COUPLED_PROTECT_UPDATED" if orphan is None else "VAULT_ANOMALY_DETECTED",
        orphan_anomaly=orphan,
        reason=f"Atomically set Protect={target_prot} across coupled CLIP + SUB pair",
    )


def evaluate_focus_magnifier_and_bright_monitoring_interlocks(
    *,
    capture_mode: str = "Movie",
    sensor_crop_mode: str = "Full-Frame",
    exposure_mode: str = "M",
    focus_mode: str = "MF",
    initial_focus_mag: str = "x1.0",
    focus_magnif_time: str = "No Limit",
    auto_magnifier_in_mf_setting: str = "On",
    focus_magnifier_custom_active: bool = False,
    focus_ring_rotated: bool = False,
    marker_display_setting: str = "On",
    live_view_display_setting: str = "Setting Effect ON",
    bright_monitoring_prior_active: bool = False,
    bright_monitoring_key_pressed: bool = False,
    power_off_event: bool = False,
) -> FocusMagAndBrightMonitoringEvalResult:
    """Evaluate FX3 Ver. 7.02 Focus Magnifier scales, Auto Magnifier movie block & Bright Monitoring."""
    if capture_mode not in VALID_CAPTURE_MODES_P211:
        raise ValueError(f"Unsupported capture_mode: {capture_mode!r}")
    if sensor_crop_mode not in VALID_SENSOR_CROP_MODES_P211:
        raise ValueError(f"Unsupported sensor_crop_mode: {sensor_crop_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES_P211:
        raise ValueError(f"Unsupported exposure_mode: {exposure_mode!r}")
    if focus_mode not in VALID_FOCUS_MODES_P211:
        raise ValueError(f"Unsupported focus_mode: {focus_mode!r}")
    if focus_magnif_time not in VALID_FOCUS_MAGNIF_TIMES_P211:
        raise ValueError(f"Unsupported [Focus Magnif. Time]: {focus_magnif_time!r}")
    if auto_magnifier_in_mf_setting not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [Auto Magnifier in MF]: {auto_magnifier_in_mf_setting!r}")
    if marker_display_setting not in VALID_ON_OFF_P211:
        raise ValueError(f"Unsupported [Marker Display]: {marker_display_setting!r}")
    if live_view_display_setting not in ("Setting Effect ON", "Setting Effect OFF"):
        raise ValueError(f"Unsupported [Live View Display]: {live_view_display_setting!r}")

    if capture_mode in ("Movie", "S&Q"):
        allowed_scales = VALID_MOVIE_INITIAL_FOCUS_MAG_P211
    elif sensor_crop_mode == "Full-Frame":
        allowed_scales = VALID_STILL_FF_INITIAL_FOCUS_MAG_P211
    else:
        allowed_scales = VALID_STILL_APSC_INITIAL_FOCUS_MAG_P211

    if initial_focus_mag not in allowed_scales:
        raise ValueError(
            f"[Initial Focus Mag.]={initial_focus_mag!r} invalid for {capture_mode}/{sensor_crop_mode}; "
            f"allowed={allowed_scales}"
        )

    is_movie_like = capture_mode in ("Movie", "S&Q")
    auto_mag_blocked_movie = is_movie_like and (auto_magnifier_in_mf_setting == "On")
    auto_mag_effective = (
        (not is_movie_like)
        and (auto_magnifier_in_mf_setting == "On")
        and (focus_mode in ("MF", "DMF"))
    )
    auto_mag_triggered = auto_mag_effective and focus_ring_rotated
    any_magnifier_active = focus_magnifier_custom_active or auto_mag_triggered

    marker_suppressed = any_magnifier_active and (marker_display_setting == "On")
    marker_visible = (marker_display_setting == "On") and (not any_magnifier_active)

    # Bright Monitoring prerequisites & auto-cancellation:
    # Automatically canceled on power-off, leaving P/A/S/M exposure modes, or leaving MF.
    pasm_and_mf_ok = (exposure_mode in PASM_EXPOSURE_MODES_P211) and (focus_mode == "MF")
    auto_canceled = False
    bm_state = bright_monitoring_prior_active
    if bm_state and (power_off_event or not pasm_and_mf_ok):
        bm_state = False
        auto_canceled = True

    # While Focus Magnifier or Auto Magnifier in MF is active, Bright Monitoring custom key is locked out
    bm_key_locked = False
    if bright_monitoring_key_pressed:
        if any_magnifier_active:
            bm_key_locked = True
        elif power_off_event or not pasm_and_mf_ok:
            bm_key_locked = True
        else:
            bm_state = not bm_state

    eff_live_view = "Setting Effect OFF" if bm_state else live_view_display_setting

    reasons: List[str] = []
    if auto_mag_blocked_movie:
        reasons.append("Auto Magnifier in MF disabled during movie shooting")
    if marker_suppressed:
        reasons.append("Marker Display suppressed while Focus Magnifier is active")
    if bm_key_locked:
        reasons.append("Bright Monitoring custom key locked out")
    if auto_canceled:
        reasons.append("Bright Monitoring auto-canceled (power-off or left P/A/S/M + MF)")
    if bm_state:
        reasons.append("Bright Monitoring active -> Live View Display forced to Setting Effect OFF")
    if not reasons:
        reasons.append("Nominal Focus Magnifier / Bright Monitoring state")

    return FocusMagAndBrightMonitoringEvalResult(
        capture_mode=capture_mode,
        sensor_crop_mode=sensor_crop_mode,
        exposure_mode=exposure_mode,
        focus_mode=focus_mode,
        initial_focus_mag=initial_focus_mag,
        focus_magnif_time=focus_magnif_time,
        auto_magnifier_in_mf_setting=auto_magnifier_in_mf_setting,
        focus_magnifier_active=focus_magnifier_custom_active,
        auto_magnifier_triggered_active=auto_mag_triggered,
        marker_display_setting=marker_display_setting,
        bright_monitoring_prior_active=bright_monitoring_prior_active,
        bright_monitoring_key_pressed=bright_monitoring_key_pressed,
        power_off_event=power_off_event,
        auto_magnifier_in_mf_effective=auto_mag_effective,
        auto_magnifier_blocked_in_movie=auto_mag_blocked_movie,
        marker_display_visible=marker_visible,
        marker_display_suppressed_by_magnifier=marker_suppressed,
        bright_monitoring_key_locked_out=bm_key_locked,
        bright_monitoring_active_after=bm_state,
        bright_monitoring_auto_canceled=auto_canceled,
        effective_live_view_display=eff_live_view,
        reason="; ".join(reasons),
    )


def evaluate_phase211_write_guard(
    target_path: str,
    *,
    operation: str = "READ",
) -> Phase211WriteGuardResult:
    """Enforce zero persistent writes across eMMC / SPI-NOR / Backup.bin / CP RTOS."""
    norm_op = operation.strip().upper()
    if norm_op == "READ":
        return Phase211WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="Strictly O_RDONLY inspection permitted",
        )

    if FORBIDDEN_PERSISTENT_TARGET_RE_P211.search(target_path):
        return Phase211WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=False,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="HARD_WRITE_PROTECTED: persistent eMMC / SPI-NOR / NVRAM mutation forbidden",
        )

    if any(target_path.startswith(pfx) for pfx in VOLATILE_ALLOWED_PREFIXES_P211):
        return Phase211WriteGuardResult(
            target_path=target_path,
            operation=norm_op,
            allowed=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            reason="Volatile RAM/tmpfs overlay target permitted",
        )

    return Phase211WriteGuardResult(
        target_path=target_path,
        operation=norm_op,
        allowed=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        reason="Default fail-closed rejection for non-volatile write path",
    )


def build_phase211_compat_matrix() -> Phase211CompatMatrixSummary:
    """Build the 12-touchpoint Wave-28 4-class compatibility matrix (P211-01..P211-12)."""
    entries: Tuple[Phase211TouchpointEntry, ...] = (
        Phase211TouchpointEntry(
            touchpoint_id="P211-01",
            subsystem="Rec. Media dur HDMI Output (On vs Off(HDMI Only))",
            fx3_702_artifact="BKID_APP_setting_rec_media_during_hdmi_output",
            fx6_601_artifact="N5model38setting_rec_media_during_hdmi_output_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Shared model state gating internal card recording vs clean HDMI-only feed.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-02",
            subsystem="4K Output Set.(HDMI Only) 6x 10-bit Rates (incl. 24.00p)",
            fx3_702_artifact="HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_10BIT",
            fx6_601_artifact="N5model32setting_hdmi_4k_output_setting_tE",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Translates FX6 4K output selector onto FX3 Type-A HDMI 10-bit 4:2:2 modes.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-03",
            subsystem="Log Shooting & PPLUT1..4 HDMI 1080p Downshift Clamp",
            fx3_702_artifact="CAUTION_ID_FACTOR_PICTURE_PROFILE_PPLUT_MSG",
            fx6_601_artifact="common_set_hdmi_resolution_4k_rec",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Models mandatory 1080p HDMI clamp when Rec. Media=On & RAW=Off under Log/PPLUT.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-04",
            subsystem="HDMI Info. Display Built-in LCD Blank & HDMI-Only Force-Off",
            fx3_702_artifact="CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON",
            fx6_601_artifact="BKID_APP_SETTING_HDMI_INFO_DISPLAY",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Forces HDMI Info. Display=Off in HDMI-Only/RAW and models LCD blanking when On.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-05",
            subsystem="FX6 12G-SDI Output & Dual-Link ProCam Proxy Routing",
            fx3_702_artifact="ABSENT_ON_ILME_FX3_BODY",
            fx6_601_artifact="BKID_APP_EXTERN_SQ_PROXY_RECORDING_PROCAM",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            rationale="Masks FX6-only SDI/ProCam MXF proxy switches cleanly on Type-A-only FX3.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-06",
            subsystem="Proxy 2-Format / 3-Bitrate Schema (XAVC HS HD 16M/9M, XAVC S HD 6M)",
            fx3_702_artifact="PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
            fx6_601_artifact="N5model33setting_sq_proxy_record_setting_tE",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Maps Stage-B proxy bitrate controls strictly onto FX3's 3 hardware proxy enums.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-07",
            subsystem="Proxy HFR (119.88p/100p) & S&Q (>=120fps/100fps) Cutoffs",
            fx3_702_artifact="BKID_APP_setting_sq_proxy_recording",
            fx6_601_artifact="N5model28setting_sq_proxy_recording_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Enforces identical BIONZ XR sub-encoder HFR/S&Q proxy cutoffs.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-08",
            subsystem="Coupled M4ROOT/CLIP/ + M4ROOT/SUB/ Atomic Delete & Protect",
            fx3_702_artifact="mpr_Delete / mpr_Protect (CLIP + S03.MP4)",
            fx6_601_artifact="mpr_Delete / mpr_Protect",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Preserves atomic main+proxy Delete/Protect coupling and zero on-camera SUB playback.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-09",
            subsystem="Initial Focus Mag. Movie (x1.0/x4.0) vs FX6 x3/x6 Switch",
            fx3_702_artifact="MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0",
            fx6_601_artifact="ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            rationale="Translates FX6 x3/x6 assignable magnifier requests to FX3 movie x1.0/x4.0.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-10",
            subsystem="Auto Magnifier in MF Movie Block & Marker Display Suppression",
            fx3_702_artifact="BKID_APP_setting_mf_assist / BKID_APP_setting_marker_display",
            fx6_601_artifact="N5model19setting_mf_assist_tE / N5model24setting_marker_display_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Blocks focus-ring auto-magnify in Movie and hides Marker Display while magnified.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-11",
            subsystem="Bright Monitoring Custom-Key Lockout & P/A/S/M + MF Auto-Cancel",
            fx3_702_artifact="EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
            fx6_601_artifact="N5model33setting_bright_monitoring_state_tE",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            rationale="Locks out Bright Monitoring key during magnification and forces Setting Effect OFF.",
        ),
        Phase211TouchpointEntry(
            touchpoint_id="P211-12",
            subsystem="p2:/setting Backup.bin, p5:/wbi, p8:/cpapp-b.bin & SPI-NOR Zero-Write Lock",
            fx3_702_artifact="p2:/setting/Backup.bin + /dev/cnflasha* + spi_nor:",
            fx6_601_artifact="Volatile /tmp/fx6_wave28_hdmi_proxy_focusmag_overlay",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            rationale="Blocks all persistent flash/NVRAM writes; redirects Stage-B state to /tmp tmpfs.",
        ),
    )
    counts: Dict[str, int] = {cls: 0 for cls in VALID_BRIDGE_CLASSES}
    all_valid = True
    for entry in entries:
        if entry.bridge_class in counts:
            counts[entry.bridge_class] += 1
        else:
            all_valid = False
    return Phase211CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=counts,
        entries=entries,
        all_classes_valid=all_valid and len(entries) == 12 and all(v >= 1 for v in counts.values()),
    )


def analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    clean_room: bool = False,
) -> RealhwHdmiLog1080ProxyVaultAndFocusmagBrightmonReport:
    """Run the 44th (`44/44`) FX3/FX6 Wave-28 real-hardware / clean-room firmware audit."""
    forced = clean_room or is_forced_clean_room()
    donor_res = None if forced else _scan_donor_artifacts_p211(repo_root)

    if donor_res is not None:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp, cold_sec = donor_res
        source_mode = "LOCAL_DONOR_RDONLY"
    else:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp = (
            build_clean_room_realhw_hdmi_log1080_proxy_focusmag_brightmon_fixtures()
        )
        cold_sec = 0.0
        source_mode = "CLEAN_ROOM_SYNTHETIC"

    within_sla = cold_sec <= DONOR_COLD_SCAN_BUDGET_SEC_P211

    # --- Pillar 1 Verification ---
    shared_ok = all(
        fx3_app.marker_hits.get(m, 0) >= 1 and fx6_app.marker_hits.get(m, 0) >= 1
        for m in APPFW_SHARED_WAVE28_MARKERS_P211
    )
    fx3_excl_ok = all(
        fx3_app.marker_hits.get(m, 0) >= 1 and fx6_app.marker_hits.get(m, 0) == 0
        for m in APPFW_FX3_702_EXCLUSIVE_MARKERS_P211
    )
    fx6_excl_ok = all(
        fx6_app.marker_hits.get(m, 0) >= 1 and fx3_app.marker_hits.get(m, 0) == 0
        for m in APPFW_FX6_601_EXCLUSIVE_MARKERS_P211
    )
    uxc_ok = (
        fx3_uxc.file_bytes == EXPECTED_FX3_UXC_EN_F_BYTES_P211
        and fx6_uxc.file_bytes == EXPECTED_FX6_UXC_EN_BYTES_P211
        and all(fx3_uxc.token_hits.get(t, 0) >= 1 for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P211)
        and all(fx6_uxc.token_hits.get(t, 0) >= 1 for t in UXC_FX6_EN_REQUIRED_TOKENS_P211)
    )

    s_log_rec_on = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
        rec_media_dur_hdmi="On",
        raw_output="Off",
        hdmi_resolution_menu="2160p",
        log_shooting="Cine EI",
    )
    s_pplut_rec_on = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
        rec_media_dur_hdmi="On",
        raw_output="Off",
        hdmi_resolution_menu="Auto",
        log_shooting="Off",
        picture_profile="PPLUT1",
    )
    s_hdmionly_all = [
        evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="Off(HDMI Only)",
            raw_output="Off",
            hdmi_4k_output_set=rate,
            log_shooting="Cine EI",
            hdmi_info_display_requested="On",
            desqueeze_display="1.6x",
            dci_4k_24_00p_enabled=(rate == "24.00p 10bit"),
        )
        for rate in VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211
    ]
    s_raw = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
        rec_media_dur_hdmi="On",
        raw_output="On",
        log_shooting="Cine EI",
        hdmi_info_display_requested="On",
        desqueeze_display="1.6x",
    )
    s_info_on = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
        rec_media_dur_hdmi="On",
        raw_output="Off",
        log_shooting="Off",
        hdmi_info_display_requested="On",
        emphasized_rec_display="On",
        desqueeze_display="1.5x",
    )

    log_downshift_ok = all(
        evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            hdmi_resolution_menu="2160p",
            log_shooting=m,
        ).effective_hdmi_resolution
        == HDMI_FHD_1080P_RESOLUTION_P211
        for m in ("Cine EI", "Cine EI Quick", "Flexible ISO")
    )
    pplut_downshift_ok = all(
        evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            hdmi_resolution_menu="2160p",
            log_shooting="Off",
            picture_profile=pp,
        ).effective_hdmi_resolution
        == HDMI_FHD_1080P_RESOLUTION_P211
        for pp in PPLUT_PICTURE_PROFILES_P211
    )
    hdmionly_6rates_ok = all(
        r.effective_hdmi_resolution in (HDMI_4K_UHD_RESOLUTION_P211, HDMI_4K_DCI_RESOLUTION_P211)
        and r.effective_hdmi_bit_depth == 10
        and not r.internal_card_recording_permitted
        and r.effective_hdmi_info_display == "Off"
        and not r.hdmi_desqueeze_applied
        for r in s_hdmionly_all
    )
    raw_ok = (
        s_raw.effective_hdmi_resolution == HDMI_RAW_SENSOR_RESOLUTION_P211
        and s_raw.effective_hdmi_bit_depth == 16
        and s_raw.effective_hdmi_info_display == "Off"
        and not s_raw.hdmi_desqueeze_applied
    )
    info_blank_ok = (
        s_info_on.camera_lcd_live_view_blanked
        and s_info_on.hdmi_emphasized_rec_border_visible
        and not s_info_on.hdmi_desqueeze_applied
    )

    p1_passed = bool(
        fx3_app.file_bytes == EXPECTED_FX3_APPFW_BYTES_P211
        and fx6_app.file_bytes == EXPECTED_FX6_APPFW_BYTES_P211
        and shared_ok
        and fx3_excl_ok
        and fx6_excl_ok
        and uxc_ok
        and log_downshift_ok
        and pplut_downshift_ok
        and hdmionly_6rates_ok
        and raw_ok
        and info_blank_ok
    )
    pillar_1 = Pillar1HdmiLog1080pAndHdmiOnly4kReport(
        fx3_appfw=fx3_app,
        fx6_appfw=fx6_app,
        fx3_uxc_en_f=fx3_uxc,
        fx6_uxc_en=fx6_uxc,
        shared_hdmi_markers_verified=shared_ok,
        fx3_702_hdmi_pplut_markers_verified=fx3_excl_ok and fx6_excl_ok and uxc_ok,
        log_cine_ei_rec_on_downshifts_1080p=log_downshift_ok,
        pplut1_to_4_rec_on_downshifts_1080p=pplut_downshift_ok,
        hdmionly_unlocks_4k_10bit_all_six_rates=hdmionly_6rates_ok,
        raw_output_delivers_4264x2408_16bit=raw_ok,
        hdmionly_and_raw_force_hdmi_info_off=hdmionly_6rates_ok and raw_ok,
        hdmi_info_on_blanks_builtin_lcd=info_blank_ok,
        sample_scenarios=(s_log_rec_on, s_pplut_rec_on, s_hdmionly_all[0], s_raw, s_info_on),
        passed=p1_passed,
    )

    # --- Pillar 2 Verification ---
    cp_ok = (
        fx3_cp.file_bytes == EXPECTED_FX3_CPAPP_BYTES_P211
        and fx6_cp.file_bytes == EXPECTED_FX6_CPAPP_BYTES_P211
        and all(fx3_cp.marker_hits.get(m, 0) >= 1 for m in CPAPP_SHARED_MARKERS_P211)
        and all(fx6_cp.marker_hits.get(m, 0) >= 1 for m in CPAPP_SHARED_MARKERS_P211)
    )
    px_hs_16 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        proxy_file_format="XAVC HS HD", proxy_bitrate="16M", rec_frame_rate="59.94p"
    )
    px_hs_9 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        proxy_file_format="XAVC HS HD", proxy_bitrate=None, rec_frame_rate="23.98p"
    )
    px_s_6 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        proxy_file_format="XAVC S HD", proxy_bitrate=None, rec_frame_rate="50p"
    )
    px_cut_120p = evaluate_proxy_codec_matrix_and_hfr_cutoffs(rec_frame_rate="119.88p")
    px_cut_100p = evaluate_proxy_codec_matrix_and_hfr_cutoffs(rec_frame_rate="100p")
    px_cut_sq120 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        capture_mode="S&Q", rec_frame_rate="23.98p", sq_sensor_fps=120, ntsc_pal_region="NTSC"
    )
    px_cut_sq100 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        capture_mode="S&Q", rec_frame_rate="25p", sq_sensor_fps=100, ntsc_pal_region="PAL"
    )
    px_cut_hdmionly = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
        rec_media_dur_hdmi="Off(HDMI Only)"
    )

    v_del_pair = evaluate_coupled_clip_sub_vault_integrity(
        clip_stem="C0001", action="DELETE", scope="COUPLED_PAIR", in_camera=True
    )
    v_del_single_reject = evaluate_coupled_clip_sub_vault_integrity(
        clip_stem="C0001", action="DELETE", scope="SUB_ONLY", in_camera=True
    )
    v_prot_pair = evaluate_coupled_clip_sub_vault_integrity(
        clip_stem="C0002", action="PROTECT", scope="COUPLED_PAIR", in_camera=True
    )
    v_del_blocked_prot = evaluate_coupled_clip_sub_vault_integrity(
        clip_stem="C0002", clip_protected=True, sub_protected=True, action="DELETE"
    )
    v_orphan_sub = evaluate_coupled_clip_sub_vault_integrity(
        clip_stem="C0003", clip_present=False, sub_present=True, action="VERIFY_ONLY", in_camera=False
    )

    two_fmt_ok = (
        px_hs_16.proxy_active
        and px_hs_16.proxy_resolution == (1920, 1080)
        and px_hs_9.proxy_bitrate == "9M"
        and px_s_6.proxy_resolution == (1280, 720)
        and px_s_6.proxy_bitrate == "6M"
    )
    three_enums_ok = all(
        fx3_app.marker_hits.get(e, 0) >= 1
        for e in (
            "PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
            "PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD",
            "PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD",
        )
    )
    hfr_cut_ok = (not px_cut_120p.proxy_active) and (not px_cut_100p.proxy_active)
    sq_cut_ok = (not px_cut_sq120.proxy_active) and (not px_cut_sq100.proxy_active)
    hdmionly_px_ok = not px_cut_hdmionly.proxy_active
    zero_pb_ok = (
        not px_hs_16.on_camera_proxy_playback_supported
        and px_hs_16.playback_thumbnail_px_badge_shown
    )
    atomic_vault_ok = (
        v_del_pair.allowed
        and not v_del_pair.resulting_clip_present
        and not v_del_pair.resulting_sub_present
        and v_del_single_reject.single_sided_incamera_op_rejected
        and v_prot_pair.resulting_protected
        and not v_del_blocked_prot.allowed
    )
    orphan_ok = v_orphan_sub.orphan_anomaly == "ORPHAN_SUB_WITHOUT_CLIP"

    p2_passed = bool(
        cp_ok
        and two_fmt_ok
        and three_enums_ok
        and hfr_cut_ok
        and sq_cut_ok
        and hdmionly_px_ok
        and zero_pb_ok
        and atomic_vault_ok
        and orphan_ok
    )
    pillar_2 = Pillar2ProxyMatrixAndCoupledVaultReport(
        fx3_cpapp=fx3_cp,
        fx6_cpapp=fx6_cp,
        exact_two_formats_three_bitrates_verified=two_fmt_ok,
        fx3_appfw_three_proxy_enums_verified=three_enums_ok,
        hfr_120p_100p_cutoff_verified=hfr_cut_ok,
        sq_120fps_100fps_cutoff_verified=sq_cut_ok,
        hdmionly_zero_card_proxy_verified=hdmionly_px_ok,
        zero_oncamera_proxy_playback_verified=zero_pb_ok,
        atomic_coupled_delete_protect_verified=atomic_vault_ok,
        orphan_detection_verified=orphan_ok,
        sample_proxy_scenarios=(
            px_hs_16,
            px_hs_9,
            px_s_6,
            px_cut_120p,
            px_cut_sq120,
            px_cut_hdmionly,
        ),
        sample_vault_scenarios=(
            v_del_pair,
            v_del_single_reject,
            v_prot_pair,
            v_del_blocked_prot,
            v_orphan_sub,
        ),
        passed=p2_passed,
    )

    # --- Pillar 3 Verification ---
    fm_mov = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
        capture_mode="Movie",
        initial_focus_mag="x4.0",
        auto_magnifier_in_mf_setting="On",
        focus_ring_rotated=True,
        focus_magnifier_custom_active=True,
        marker_display_setting="On",
        bright_monitoring_key_pressed=True,
    )
    fm_still_ff = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
        capture_mode="Still",
        sensor_crop_mode="Full-Frame",
        initial_focus_mag="x2.1",
        auto_magnifier_in_mf_setting="On",
        focus_ring_rotated=True,
        bright_monitoring_key_pressed=True,
    )
    fm_still_apsc = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
        capture_mode="Still",
        sensor_crop_mode="APS-C_S35",
        initial_focus_mag="x1.5",
        exposure_mode="M",
        focus_mode="MF",
        bright_monitoring_key_pressed=True,
    )
    fm_bm_cancel_af = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
        capture_mode="Still",
        exposure_mode="M",
        focus_mode="AF-C",
        bright_monitoring_prior_active=True,
    )
    fm_bm_cancel_exp = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
        capture_mode="Movie",
        exposure_mode="Flexible Exp.",
        focus_mode="MF",
        bright_monitoring_prior_active=True,
    )

    mov_scales_ok = fm_mov.initial_focus_mag == "x4.0" and fm_mov.auto_magnifier_blocked_in_movie
    still_scales_ok = (
        fm_still_ff.initial_focus_mag == "x2.1"
        and fm_still_ff.auto_magnifier_triggered_active
        and fm_still_apsc.initial_focus_mag == "x1.5"
    )
    marker_supp_ok = fm_mov.marker_display_suppressed_by_magnifier and not fm_mov.marker_display_visible
    bm_lockout_ok = (
        fm_mov.bright_monitoring_key_locked_out
        and fm_still_ff.bright_monitoring_key_locked_out
        and fm_still_apsc.bright_monitoring_active_after
        and fm_still_apsc.effective_live_view_display == "Setting Effect OFF"
    )
    bm_cancel_ok = (
        fm_bm_cancel_af.bright_monitoring_auto_canceled
        and not fm_bm_cancel_af.bright_monitoring_active_after
        and fm_bm_cancel_exp.bright_monitoring_auto_canceled
        and not fm_bm_cancel_exp.bright_monitoring_active_after
    )

    p3_passed = bool(
        mov_scales_ok and still_scales_ok and marker_supp_ok and bm_lockout_ok and bm_cancel_ok
    )
    pillar_3 = Pillar3FocusMagAndBrightMonReport(
        movie_x10_x40_scales_verified=mov_scales_ok,
        still_ff_x21_and_apsc_x15_verified=still_scales_ok,
        auto_magnifier_blocked_in_movie_verified=fm_mov.auto_magnifier_blocked_in_movie,
        marker_suppressed_during_magnifier_verified=marker_supp_ok,
        bright_mon_custom_key_lockout_verified=bm_lockout_ok,
        bright_mon_pasm_mf_autocancel_and_liveview_off_verified=bm_cancel_ok,
        sample_interlock_scenarios=(
            fm_mov,
            fm_still_ff,
            fm_still_apsc,
            fm_bm_cancel_af,
            fm_bm_cancel_exp,
        ),
        passed=p3_passed,
    )

    # --- Pillar 4 Verification ---
    g_p2 = evaluate_phase211_write_guard("p2:/setting/Backup.bin", operation="WRITE")
    g_emmc = evaluate_phase211_write_guard("/dev/cnflasha2", operation="WRITE")
    g_spinor = evaluate_phase211_write_guard("spi_nor:0x0", operation="ERASE")
    g_tmp = evaluate_phase211_write_guard(
        f"{VOLATILE_WAVE28_OVERLAY_DIR_P211}/state.json", operation="WRITE"
    )
    g_ro = evaluate_phase211_write_guard(FX3_APPFW_P211_RELPATH, operation="READ")
    matrix = build_phase211_compat_matrix()

    p4_passed = bool(
        not g_p2.allowed
        and not g_emmc.allowed
        and not g_spinor.allowed
        and g_tmp.allowed
        and g_ro.allowed
        and matrix.all_classes_valid
    )
    pillar_4 = Pillar4Phase211WriteGuardAndMatrixReport(
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=0,
        volatile_overlay_dir=VOLATILE_WAVE28_OVERLAY_DIR_P211,
        guard_evaluations=(g_p2, g_emmc, g_spinor, g_tmp, g_ro),
        matrix=matrix,
        passed=p4_passed,
    )

    all_passed = bool(within_sla and p1_passed and p2_passed and p3_passed and p4_passed)
    digest_input = (
        f"{PHASE_211_SCHEMA}|{PHASE_211_VERSION}|{AUDITOR_INDEX_P211}|{source_mode}|"
        f"{p1_passed}|{p2_passed}|{p3_passed}|{p4_passed}|{matrix.total_touchpoints}"
    ).encode("utf-8")
    digest = hashlib.sha256(digest_input).hexdigest()

    return RealhwHdmiLog1080ProxyVaultAndFocusmagBrightmonReport(
        schema=PHASE_211_SCHEMA,
        version=PHASE_211_VERSION,
        auditor_index=AUDITOR_INDEX_P211,
        source_mode=source_mode,
        clean_room_forced=forced,
        donor_cold_scan_duration_sec=round(cold_sec, 6),
        donor_cold_scan_within_sla=within_sla,
        pillar_1_hdmi_log_1080p_and_hdmionly_4k=pillar_1,
        pillar_2_proxy_matrix_and_coupled_vault=pillar_2,
        pillar_3_focusmag_and_bright_monitoring=pillar_3,
        pillar_4_write_guard_and_matrix=pillar_4,
        report_digest_sha256=digest,
        all_checks_passed=all_passed,
    )


def _jsonify_p211(obj: object) -> object:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonify_p211(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Mapping):
        return {str(k): _jsonify_p211(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify_p211(v) for v in obj]
    return obj


def realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict(
    report: RealhwHdmiLog1080ProxyVaultAndFocusmagBrightmonReport,
) -> Dict[str, object]:
    """Serialize `RealhwHdmiLog1080ProxyVaultAndFocusmagBrightmonReport` to deterministic JSON dict."""
    res = _jsonify_p211(report)
    assert isinstance(res, dict)
    return res
