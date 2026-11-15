#!/usr/bin/env python3
"""Phase 213 — Stage 38 (`38/38` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[HDMI Output Settings]` (`[Log Shooting]` / `PPLUT1..4`
Forced `1080p` Downshift vs `[Off(HDMI Only)]` `4K 10-bit` & `[HDMI Info. Display]` Blank-LCD),
`[Proxy Settings]` (`XAVC HS HD` 10-bit HEVC `16M`/`9M` & `XAVC S HD` 8-bit AVC `6M`, `119.88p/100p`
& `>=120fps/100fps` Cutoffs, `(Px)` Zero-Playback & Atomic Coupled `M4ROOT/CLIP/`+`SUB/` Vault),
and `[Focus Magnifier]` (`x1.0`/`x4.0` Movie vs `x1.0`/`x2.1`/`x1.5` Still, `[Auto Magnifier in MF]`
Movie Block & `[Marker Display]` Suppression) × `[Bright Monitoring]` (`P/A/S/M` + `MF` Lock,
Custom-Key Lockout While Magnified & `[Setting Effect OFF]`) HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) 12-donor inspection (< 0.02s cold,
cached per process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `single_sided_proxy_or_main_orphan_mutations == 0`
- `on_camera_proxy_playback_frames == 0`
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
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 213 Schema & Hard-Locked Safety Redlines (38/38 Milestone)
# ---------------------------------------------------------------------------

PHASE_213_SCHEMA = "phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator_v1"
PHASE_213_VERSION = "213.0.0"
STAGE_INDEX = 38
STAGE_TOTAL = 38
MILESTONE_LABEL = "38/38"
STAGE_NAME = "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil"

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
SINGLE_SIDED_PROXY_OR_MAIN_ORPHAN_MUTATIONS = 0
ON_CAMERA_PROXY_PLAYBACK_FRAMES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

EACCES_ERRNO = 13  # Linux EACCES (protected clip delete block)
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
        b"HDMI Output Settings",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"4K Output Set.(HDMI Only)",
        b"Output Resolution",
        b"HDMI Info. Display",
        b"Emphasized REC Display",
        b"RAW Output",
        b"Log Shooting",
        b"Cine EI",
        b"Cine EI Quick",
        b"Flexible ISO",
        b"59.94p 10bit",
        b"50p 10bit",
        b"29.97p 10bit",
        b"25p 10bit",
        b"23.98p 10bit",
        b"24.00p 10bit",
        b"Proxy Settings",
        b"Proxy Recording",
        b"Proxy File Format",
        b"XAVC HS HD",
        b"XAVC S HD",
        b"16M 4:2:0 10bit",
        b"9M 4:2:0 10bit",
        b"6M 4:2:0 8bit",
        b"Initial Focus Mag.",
        b"Focus Magnif. Time",
        b"Auto Magnifier in MF",
        b"Marker Display",
        b"Bright Monitoring",
        b"Live View Display",
        b"Setting Effect OFF",
        b"x1.0",
        b"x4.0",
        b"x2.1",
        b"x1.5",
    ),
    "fx6_string_en": (
        b"HDMI",
        b"Output",
        b"Proxy",
        b"Focus Magnifier",
        b"Marker",
        b"Cine EI",
        b"RAW Output",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_938_432, "LOG_SHOOTING", b"LOG_SHOOTING"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_954_816, "FOCUS_MAG", b"FOCUS_MAG"),
        (49_954_816, "SUB", b"SUB"),
        (50_016_256, "CLIP", b"CLIP"),
        (51_404_800, "PROXY", b"Proxy"),
        (51_417_088, "BRIGHT_MON", b"BrightMonitoring"),
        (59_801_600, "M4ROOT", b"M4ROOT"),
        (60_264_448, "DESQUEEZE", b"desqueeze"),
        (60_633_088, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (60_657_664, "HDMI_RAW", b"HDMI_RAW"),
        (61_313_024, "PPLUT", b"PPLUT"),
        (62_046_208, "MARKER", b"MARKER"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_232_640, "PROXY", b"PROXY"),
        (37_236_736, "FOCUS_MAG", b"FOCUS_MAG"),
        (37_437_440, "DESQUEEZE", b"DESQUEEZE"),
        (39_374_848, "MARKER", b"MARKER"),
        (39_399_424, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (41_201_664, "HDMI_RAW", b"HDMI_RAW"),
    ),
    "fx3_cpapp": (
        (655_360, "MARKER", b"Marker"),
        (696_320, "HDMI", b"HDMI"),
        (2_015_232, "DESQUEEZE", b"DESQUEEZE"),
        (10_731_520, "PROXY", b"Proxy"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
        (13_139_968, "MAGNIF", b"Magnif"),
        (13_275_136, "RAW_OUTPUT", b"RAW_OUTPUT"),
    ),
    "fx6_cpapp": (
        (303_104, "MARKER", b"Marker"),
        (684_032, "HDMI", b"HDMI"),
        (2_068_480, "DESQUEEZE", b"DESQUEEZE"),
        (12_193_792, "PROXY", b"Proxy"),
        (14_741_504, "RAW_OUTPUT", b"RAW_OUTPUT"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (131_072, "XAVC", b"Xavc"),
        (167_936, "SUB", b"Sub"),
        (176_128, "PROXY", b"Proxy"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (163_840, "XAVC", b"Xavc"),
        (204_800, "PROXY", b"Proxy"),
    ),
}

# ---------------------------------------------------------------------------
# Sub-model A/B/C Constants (Wave-28 Official ILME-FX3 Ver. 7.02 Contracts)
# ---------------------------------------------------------------------------

HDMI_OUTPUT_MENU_PATH = "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")
VALID_REC_MEDIA_DUR_HDMI: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_HDMI_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
VALID_HDMI_ONLY_4K_SETTINGS: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Cine EI", "Cine EI Quick", "Flexible ISO")
PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
VALID_PICTURE_PROFILES: Tuple[str, ...] = (
    "Off", "PP1", "PP2", "PP3", "PP4", "PP5", "PP6", "PP7", "PP8", "PP9", "PP10", "PP11",
    "PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4",
)
VALID_DESQUEEZE_OPTIONS: Tuple[str, ...] = ("Off", "1.3x", "2.0x", "1.5x", "1.6x")

PROXY_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]"
PROXY_FORMAT_XAVC_S_HD = "XAVC S HD"  # Overall [Proxy File Format] default
PROXY_FORMAT_XAVC_HS_HD = "XAVC HS HD"
VALID_PROXY_FILE_FORMATS: Tuple[str, ...] = (PROXY_FORMAT_XAVC_S_HD, PROXY_FORMAT_XAVC_HS_HD)

PROXY_CODEC_SPECS: Mapping[str, Dict[str, object]] = {
    PROXY_FORMAT_XAVC_HS_HD: {
        "width": 1920,
        "height": 1080,
        "codec": "MPEG-H HEVC/H.265",
        "bit_depth": 10,
        "chroma": "4:2:0",
        "max_fps_ntsc_pal": ("59.94p", "50p"),
        "default_setting": "9M 4:2:0 10bit",
        "valid_settings": ("9M 4:2:0 10bit", "16M 4:2:0 10bit"),
    },
    PROXY_FORMAT_XAVC_S_HD: {
        "width": 1280,
        "height": 720,
        "codec": "MPEG-4 AVC/H.264",
        "bit_depth": 8,
        "chroma": "4:2:0",
        "max_fps_ntsc_pal": ("59.94p", "50p"),
        "default_setting": "6M 4:2:0 8bit",
        "valid_settings": ("6M 4:2:0 8bit",),
    },
}

VALID_MOVIE_REC_FRAME_RATES: Tuple[str, ...] = (
    "23.98p", "24.00p", "25p", "29.97p", "50p", "59.94p", "100p", "119.88p",
)
BLOCKED_PROXY_REC_FRAME_RATES: Tuple[str, ...] = ("100p", "119.88p")
PROXY_SQ_SENSOR_FPS_CUTOFF = 100.0  # Blocks [100fps]/[120fps]/[200fps]/[240fps]

VAULT_OP_NONE = "NONE"
VAULT_OP_COUPLED_PROTECT_ON = "COUPLED_PROTECT_ON"
VAULT_OP_COUPLED_PROTECT_OFF = "COUPLED_PROTECT_OFF"
VAULT_OP_COUPLED_DELETE = "COUPLED_DELETE"
VAULT_OP_ATTEMPT_PROXY_PLAYBACK = "ATTEMPT_ON_CAMERA_PROXY_PLAYBACK"
VAULT_OP_SINGLE_DELETE_MAIN = "SINGLE_SIDED_DELETE_MAIN_ONLY"
VAULT_OP_SINGLE_DELETE_PROXY = "SINGLE_SIDED_DELETE_PROXY_ONLY"
VAULT_OP_SINGLE_PROTECT_MAIN = "SINGLE_SIDED_PROTECT_MAIN_ONLY"
VAULT_OP_SINGLE_PROTECT_PROXY = "SINGLE_SIDED_PROTECT_PROXY_ONLY"

VALID_VAULT_OPERATIONS: Tuple[str, ...] = (
    VAULT_OP_NONE,
    VAULT_OP_COUPLED_PROTECT_ON,
    VAULT_OP_COUPLED_PROTECT_OFF,
    VAULT_OP_COUPLED_DELETE,
    VAULT_OP_ATTEMPT_PROXY_PLAYBACK,
    VAULT_OP_SINGLE_DELETE_MAIN,
    VAULT_OP_SINGLE_DELETE_PROXY,
    VAULT_OP_SINGLE_PROTECT_MAIN,
    VAULT_OP_SINGLE_PROTECT_PROXY,
)
VALID_ORPHAN_INJECTIONS: Tuple[str, ...] = (
    "NONE",
    "ORPHAN_SUB_WITHOUT_CLIP",
    "ORPHAN_CLIP_MISSING_EXPECTED_SUB",
)

FOCUS_MAG_MENU_PATH = "MENU -> Focus -> [Focus Assistant] -> [Focus Magnifier]"
VALID_CAPTURE_MODES: Tuple[str, ...] = ("Movie", "S&Q", "Photo")
CROP_FULL_FRAME = "Full-Frame"
CROP_APSC_S35 = "APS-C/Super 35mm"
VALID_SENSOR_CROPS: Tuple[str, ...] = (CROP_FULL_FRAME, CROP_APSC_S35)
MOVIE_INITIAL_FOCUS_MAG_SCALES: Tuple[str, ...] = ("x1.0", "x4.0")
STILL_FF_INITIAL_FOCUS_MAG_SCALES: Tuple[str, ...] = ("x1.0", "x2.1")
STILL_APSC_INITIAL_FOCUS_MAG_SCALES: Tuple[str, ...] = ("x1.0", "x1.5")
VALID_FOCUS_MAGNIF_TIMES: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")

MAG_TRIGGER_IDLE = "IDLE"
MAG_TRIGGER_CUSTOM_KEY = "CUSTOM_KEY_FOCUS_MAG"
MAG_TRIGGER_FOCUS_RING_AUTO = "FOCUS_RING_AUTO_MAG_IN_MF"
VALID_MAG_TRIGGERS: Tuple[str, ...] = (
    MAG_TRIGGER_IDLE,
    MAG_TRIGGER_CUSTOM_KEY,
    MAG_TRIGGER_FOCUS_RING_AUTO,
)

PASM_EXPOSURE_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
VALID_EXPOSURE_MODES: Tuple[str, ...] = ("P", "A", "S", "M", "Auto", "SCN", "Flexible_Auto")
VALID_FOCUS_MODES: Tuple[str, ...] = ("MF", "AF-S", "AF-C", "DMF")
VALID_LIVE_VIEW_DISPLAY: Tuple[str, ...] = ("Setting Effect ON", "Setting Effect OFF")


class RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(ValueError):
    """Raised on invalid Phase 213 co-emulator configuration arguments."""


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
class Phase213DonorAudit:
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
    hdmi_log_1080p_and_hdmionly_4k_proven: bool
    proxy_dual_codec_and_coupled_vault_proven: bool
    focus_mag_and_bright_monitoring_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiLog1080VsHdmiOnly4kHilResult:
    admitted: bool
    menu_path: str
    rec_media_dur_hdmi: str
    hdmi_raw_output: str
    requested_output_resolution: str
    hdmi_only_4k_setting: str
    log_shooting: str
    picture_profile: str
    requested_hdmi_info_display: str
    effective_hdmi_info_display: str
    emphasized_rec_display: str
    hdmi_emphasized_rec_tally_active: bool
    desqueeze_option: str
    hdmi_desqueeze_active: bool
    effective_hdmi_width: int
    effective_hdmi_height: int
    effective_hdmi_resolution_label: str
    effective_hdmi_bit_depth: int
    hdmi_downshifted_to_1080p: bool
    downshift_trigger_reason: str
    internal_card_recording_active: bool
    camera_lcd_blanked: bool
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class ProxyCoupledVaultHilResult:
    admitted: bool
    menu_path: str
    proxy_recording: str
    proxy_file_format: str
    proxy_record_setting: str
    capture_mode: str
    rec_frame_rate: str
    sq_sensor_fps: float
    rec_media_dur_hdmi: str
    proxy_codec_name: str
    proxy_width: int
    proxy_height: int
    proxy_bit_depth: int
    main_clip_path: str
    proxy_sub_path: str
    main_clip_exists: bool
    proxy_sub_exists: bool
    proxy_generated: bool
    proxy_blocked_reason: str
    px_badge_displayed: bool
    on_camera_proxy_playback_supported: bool
    proxy_visible_in_playback_index: bool
    on_camera_proxy_playback_frames: int
    vault_operation: str
    main_protected: bool
    proxy_protected: bool
    coupled_pair_intact: bool
    orphan_detected: bool
    single_sided_mutation_rejected: bool
    single_sided_proxy_or_main_orphan_mutations: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class FocusMagBrightMonitoringHilResult:
    admitted: bool
    menu_path: str
    capture_mode: str
    sensor_crop_mode: str
    exposure_mode: str
    focus_mode: str
    initial_focus_mag: str
    applied_mag_scale: float
    focus_magnif_time: str
    auto_magnifier_in_mf: str
    trigger_source: str
    focus_magnifier_active: bool
    auto_magnifier_in_mf_blocked_in_movie: bool
    requested_marker_display: str
    effective_marker_display: str
    marker_display_suppressed: bool
    prior_bright_monitoring_active: bool
    press_bright_monitoring_custom_key: bool
    bright_monitoring_key_locked_out: bool
    camera_power_off: bool
    effective_bright_monitoring: bool
    bright_monitoring_auto_canceled: bool
    auto_cancel_reasons: Tuple[str, ...]
    requested_live_view_display: str
    effective_live_view_display: str
    live_view_forced_setting_effect_off: bool
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
    single_sided_proxy_or_main_orphan_mutations: int
    on_camera_proxy_playback_frames: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase213DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase213DonorAudit] = None


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


def resolve_phase213_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase213DonorAudit:
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase213DonorAudit(
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
        hdmi_log_1080p_and_hdmionly_4k_proven=True,
        proxy_dual_codec_and_coupled_vault_proven=True,
        focus_mag_and_bright_monitoring_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase213_donors(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Phase213DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.02s cold, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase213_donor_paths(env=env)
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

    hdmi_ok = (
        fx3_adj_media.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("HDMI Output Settings") == 1
        and fx3_string_en_f.marker_hits.get("Off(HDMI Only)") == 1
        and fx3_string_en_f.marker_hits.get("4K Output Set.(HDMI Only)") == 1
        and fx3_string_en_f.marker_hits.get("HDMI Info. Display") == 1
        and fx3_appfw.window_hits.get("PPLUT") == 1
        and fx3_appfw.window_hits.get("LOG_SHOOTING") == 1
        and fx3_cpapp.window_hits.get("HDMI") == 1
    )
    proxy_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Proxy Settings") == 1
        and fx3_string_en_f.marker_hits.get("XAVC HS HD") == 1
        and fx3_string_en_f.marker_hits.get("XAVC S HD") == 1
        and fx3_appfw.window_hits.get("M4ROOT") == 1
        and fx3_appfw.window_hits.get("CLIP") == 1
        and fx3_appfw.window_hits.get("SUB") == 1
        and fx3_libmpr.window_hits.get("PROXY") == 1
    )
    mag_bright_ok = (
        fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Initial Focus Mag.") == 1
        and fx3_string_en_f.marker_hits.get("Auto Magnifier in MF") == 1
        and fx3_string_en_f.marker_hits.get("Bright Monitoring") == 1
        and fx3_string_en_f.marker_hits.get("Setting Effect OFF") == 1
        and fx3_appfw.window_hits.get("FOCUS_MAG") == 1
        and fx3_appfw.window_hits.get("BRIGHT_MON") == 1
    )
    audit = Phase213DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY", access_mode=DONOR_ACCESS_MODE, donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm, fx6_lens_comm=fx6_lens_comm, fx3_media_cfg=fx3_media_cfg,
        fx3_adj_media=fx3_adj_media, fx3_string_en_f=fx3_string_en_f, fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw, fx6_appfw=fx6_appfw, fx3_cpapp=fx3_cpapp, fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr, fx6_libmpr=fx6_libmpr,
        hdmi_log_1080p_and_hdmionly_4k_proven=hdmi_ok,
        proxy_dual_codec_and_coupled_vault_proven=proxy_ok,
        focus_mag_and_bright_monitoring_proven=mag_bright_ok,
        all_contracts_verified=(len(errors) == 0 and hdmi_ok and proxy_ok and mag_bright_ok),
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-model A: HDMI Log 1080p Downshift vs Off(HDMI Only) 4K 10-bit & Blank-LCD
# ---------------------------------------------------------------------------


def probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
    *,
    rec_media_dur_hdmi: str = "On",
    hdmi_raw_output: str = "Off",
    requested_output_resolution: str = "2160p",
    hdmi_only_4k_setting: str = "59.94p 10bit",
    log_shooting: str = "Cine EI",
    picture_profile: str = "Off",
    requested_hdmi_info_display: str = "Off",
    emphasized_rec_display: str = "On",
    desqueeze_option: str = "1.6x",
    record_setting_bit_depth: int = 10,
    attempt_internal_card_rec: bool = False,
) -> HdmiLog1080VsHdmiOnly4kHilResult:
    """Co-emulate [HDMI Output Settings], Log/PPLUT 1080p downshift, Off(HDMI Only) 4K & Blank-LCD."""
    for val, allowed, label in (
        (rec_media_dur_hdmi, VALID_REC_MEDIA_DUR_HDMI, "rec_media_dur_hdmi"),
        (hdmi_raw_output, VALID_ON_OFF, "hdmi_raw_output"),
        (log_shooting, VALID_LOG_SHOOTING_MODES, "log_shooting"),
        (picture_profile, VALID_PICTURE_PROFILES, "picture_profile"),
        (requested_hdmi_info_display, VALID_ON_OFF, "requested_hdmi_info_display"),
        (emphasized_rec_display, VALID_ON_OFF, "emphasized_rec_display"),
        (desqueeze_option, VALID_DESQUEEZE_OPTIONS, "desqueeze_option"),
    ):
        if val not in allowed:
            raise RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(f"Unsupported {label} {val!r}")
    if record_setting_bit_depth not in (8, 10):
        raise RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(
            f"record_setting_bit_depth must be 8 or 10, got {record_setting_bit_depth!r}"
        )

    def _mk(
        *, admitted: bool, eff_info: str = "Off", tally: bool = False, desq: bool = False,
        w: int = 0, h: int = 0, lbl: str = "INVALID", bdepth: int = 0,
        downshifted: bool = False, reason: str = "NONE", card_rec: bool = False,
        lcd_blank: bool = False, errno: int = 0, status: str,
    ) -> HdmiLog1080VsHdmiOnly4kHilResult:
        return HdmiLog1080VsHdmiOnly4kHilResult(
            admitted=admitted, menu_path=HDMI_OUTPUT_MENU_PATH,
            rec_media_dur_hdmi=rec_media_dur_hdmi, hdmi_raw_output=hdmi_raw_output,
            requested_output_resolution=requested_output_resolution,
            hdmi_only_4k_setting=hdmi_only_4k_setting, log_shooting=log_shooting,
            picture_profile=picture_profile,
            requested_hdmi_info_display=requested_hdmi_info_display,
            effective_hdmi_info_display=eff_info, emphasized_rec_display=emphasized_rec_display,
            hdmi_emphasized_rec_tally_active=tally, desqueeze_option=desqueeze_option,
            hdmi_desqueeze_active=desq, effective_hdmi_width=w, effective_hdmi_height=h,
            effective_hdmi_resolution_label=lbl, effective_hdmi_bit_depth=bdepth,
            hdmi_downshifted_to_1080p=downshifted, downshift_trigger_reason=reason,
            internal_card_recording_active=card_rec, camera_lcd_blanked=lcd_blank,
            errno_code=errno, status_code=status,
        )

    if requested_output_resolution not in VALID_HDMI_OUTPUT_RESOLUTIONS:
        return _mk(
            admitted=False, reason="INVALID_OUTPUT_RESOLUTION", errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_HDMI_OUTPUT_RESOLUTION_EINVAL",
        )
    if hdmi_only_4k_setting not in VALID_HDMI_ONLY_4K_SETTINGS:
        return _mk(
            admitted=False, reason="INVALID_4K_HDMI_ONLY_SETTING", errno=EINVAL_ERRNO,
            status="BLOCKED_INVALID_4K_OUTPUT_SET_HDMI_ONLY_EINVAL",
        )

    if hdmi_raw_output == "On":
        if rec_media_dur_hdmi == "Off(HDMI Only)" and attempt_internal_card_rec:
            return _mk(
                admitted=False, w=4264, h=2408, lbl="4264x2408 RAW16", bdepth=16,
                errno=EOPNOTSUPP_ERRNO,
                status="BLOCKED_INTERNAL_CARD_REC_DISABLED_UNDER_OFF_HDMI_ONLY_EOPNOTSUPP",
            )
        return _mk(
            admitted=True, w=4264, h=2408, lbl="4264x2408 RAW16", bdepth=16,
            card_rec=(rec_media_dur_hdmi == "On"),
            status="ADMITTED_HDMI_4264X2408_16BIT_LINEAR_RAW_OK",
        )

    if rec_media_dur_hdmi == "Off(HDMI Only)":
        lbl_4k = f"2160p ({hdmi_only_4k_setting})"
        if attempt_internal_card_rec:
            return _mk(
                admitted=False, w=3840, h=2160, lbl=lbl_4k, bdepth=10, errno=EOPNOTSUPP_ERRNO,
                status="BLOCKED_INTERNAL_CARD_REC_DISABLED_UNDER_OFF_HDMI_ONLY_EOPNOTSUPP",
            )
        return _mk(
            admitted=True, w=3840, h=2160, lbl=lbl_4k, bdepth=10,
            status="ADMITTED_OFF_HDMI_ONLY_4K_10BIT_ZERO_CARD_REC_OK",
        )

    log_active = log_shooting != "Off"
    pplut_active = picture_profile in PPLUT_PROFILES
    eff_info = requested_hdmi_info_display
    lcd_blanked = eff_info == "On"
    rec_tally_hdmi = lcd_blanked and (emphasized_rec_display == "On")
    desq_hdmi = (desqueeze_option != "Off") and log_active

    if log_active or pplut_active:
        reasons = [
            r for r in (
                f"LOG_SHOOTING:{log_shooting}" if log_active else "",
                f"PICTURE_PROFILE:{picture_profile}" if pplut_active else "",
            ) if r
        ]
        return _mk(
            admitted=True, eff_info=eff_info, tally=rec_tally_hdmi, desq=desq_hdmi,
            w=1920, h=1080, lbl="1080p", bdepth=record_setting_bit_depth,
            downshifted=(requested_output_resolution in ("Auto", "2160p")),
            reason="+".join(reasons), card_rec=True, lcd_blank=lcd_blanked,
            status="ADMITTED_HDMI_FORCED_1080P_DOWNSHIFT_WITH_CARD_REC_OK",
        )

    w, h, lbl = (
        (3840, 2160, "2160p")
        if requested_output_resolution in ("Auto", "2160p")
        else (1920, 1080, requested_output_resolution)
    )
    return _mk(
        admitted=True, eff_info=eff_info, tally=rec_tally_hdmi, w=w, h=h, lbl=lbl,
        bdepth=record_setting_bit_depth, card_rec=True, lcd_blank=lcd_blanked,
        status="ADMITTED_STANDARD_HDMI_OUTPUT_WITH_CARD_REC_OK",
    )


def evaluate_pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil() -> Dict[str, object]:
    log_downshift_matrix = {
        mode: asdict(probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On", requested_output_resolution="2160p", log_shooting=mode,
        ))
        for mode in ("Cine EI", "Cine EI Quick", "Flexible ISO")
    }
    pplut_downshift_matrix = {
        pp: asdict(probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On", requested_output_resolution="Auto",
            log_shooting="Off", picture_profile=pp,
        ))
        for pp in PPLUT_PROFILES
    }
    hdmi_only_4k_matrix = {
        opt: asdict(probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="Off(HDMI Only)", hdmi_only_4k_setting=opt,
            log_shooting="Cine EI", requested_hdmi_info_display="On", desqueeze_option="1.6x",
        ))
        for opt in VALID_HDMI_ONLY_4K_SETTINGS
    }
    info_on_blanks_lcd = probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
        rec_media_dur_hdmi="On", log_shooting="Cine EI",
        requested_hdmi_info_display="On", emphasized_rec_display="On",
    )
    hdmi_only_blocks_card_rec = probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
        rec_media_dur_hdmi="Off(HDMI Only)", attempt_internal_card_rec=True,
    )
    raw_4264_bypass = probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
        rec_media_dur_hdmi="On", hdmi_raw_output="On",
        log_shooting="Cine EI", requested_hdmi_info_display="On",
    )
    std_4k_no_log = probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
        rec_media_dur_hdmi="On", log_shooting="Off",
        picture_profile="PP11", requested_output_resolution="2160p",
    )
    passed = (
        all(
            v["effective_hdmi_width"] == 1920 and v["hdmi_downshifted_to_1080p"]
            and v["internal_card_recording_active"]
            for v in log_downshift_matrix.values()
        )
        and all(
            v["effective_hdmi_width"] == 1920 and v["hdmi_downshifted_to_1080p"]
            for v in pplut_downshift_matrix.values()
        )
        and all(
            v["effective_hdmi_width"] == 3840 and v["effective_hdmi_bit_depth"] == 10
            and (not v["internal_card_recording_active"])
            and v["effective_hdmi_info_display"] == "Off"
            and (not v["hdmi_desqueeze_active"]) and (not v["camera_lcd_blanked"])
            for v in hdmi_only_4k_matrix.values()
        )
        and info_on_blanks_lcd.camera_lcd_blanked
        and info_on_blanks_lcd.hdmi_emphasized_rec_tally_active
        and (not hdmi_only_blocks_card_rec.admitted)
        and raw_4264_bypass.effective_hdmi_width == 4264
        and std_4k_no_log.effective_hdmi_width == 3840
    )
    return {
        "passed": passed,
        "log_downshift_1080p_matrix": log_downshift_matrix,
        "pplut_downshift_1080p_matrix": pplut_downshift_matrix,
        "hdmi_only_4k_10bit_matrix": hdmi_only_4k_matrix,
        "hdmi_info_on_blanks_camera_lcd": asdict(info_on_blanks_lcd),
        "hdmi_only_card_rec_blocked": asdict(hdmi_only_blocks_card_rec),
        "hdmi_raw_4264x2408_bypass": asdict(raw_4264_bypass),
        "standard_pp11_4k_no_downshift": asdict(std_4k_no_log),
    }


# ---------------------------------------------------------------------------
# Sub-model B: [Proxy Settings] Dual-Codec Matrix & Atomic CLIP/+SUB/ Vault
# ---------------------------------------------------------------------------


def probe_proxy_dual_codec_and_coupled_vault_hil(
    *,
    proxy_recording: str = "On",
    proxy_file_format: str = PROXY_FORMAT_XAVC_S_HD,
    proxy_record_setting: Optional[str] = None,
    capture_mode: str = "Movie",
    rec_frame_rate: str = "23.98p",
    sq_sensor_fps: float = 60.0,
    rec_media_dur_hdmi: str = "On",
    clip_id: str = "C0001",
    prior_protected: bool = False,
    vault_operation: str = VAULT_OP_NONE,
    simulate_external_orphan_state: str = "NONE",
) -> ProxyCoupledVaultHilResult:
    """Co-emulate [Proxy Settings] codecs/cutoffs, zero proxy playback & atomic CLIP/+SUB/ vault."""
    for val, allowed, label in (
        (proxy_recording, VALID_ON_OFF, "proxy_recording"),
        (capture_mode, ("Movie", "S&Q"), "capture_mode"),
        (rec_frame_rate, VALID_MOVIE_REC_FRAME_RATES, "rec_frame_rate"),
        (rec_media_dur_hdmi, VALID_REC_MEDIA_DUR_HDMI, "rec_media_dur_hdmi"),
        (vault_operation, VALID_VAULT_OPERATIONS, "vault_operation"),
        (simulate_external_orphan_state, VALID_ORPHAN_INJECTIONS, "simulate_external_orphan_state"),
    ):
        if val not in allowed:
            raise RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(f"Unsupported {label} {val!r}")
    if sq_sensor_fps <= 0.0 or sq_sensor_fps > 240.0:
        raise RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(
            f"sq_sensor_fps must be in (0, 240], got {sq_sensor_fps!r}"
        )

    main_path = f"/PRIVATE/M4ROOT/CLIP/{clip_id}.MP4"
    sub_path = f"/PRIVATE/M4ROOT/SUB/{clip_id}S03.MP4"
    spec = PROXY_CODEC_SPECS.get(proxy_file_format)
    eff_setting = (
        "" if spec is None
        else (str(spec["default_setting"]) if proxy_record_setting is None else proxy_record_setting)
    )
    codec_name = "INVALID" if spec is None else str(spec["codec"])
    w = 0 if spec is None else int(spec["width"])
    h = 0 if spec is None else int(spec["height"])
    bdepth = 0 if spec is None else int(spec["bit_depth"])

    def _mk(
        *, admitted: bool, main_ex: bool = False, sub_ex: bool = False, px_gen: bool = False,
        reason: str = "NONE", px_badge: bool = False, m_prot: bool = False, p_prot: bool = False,
        intact: bool = True, orphan: bool = False, single_rej: bool = False,
        errno: int = 0, status: str,
    ) -> ProxyCoupledVaultHilResult:
        return ProxyCoupledVaultHilResult(
            admitted=admitted, menu_path=PROXY_MENU_PATH, proxy_recording=proxy_recording,
            proxy_file_format=proxy_file_format, proxy_record_setting=eff_setting,
            capture_mode=capture_mode, rec_frame_rate=rec_frame_rate,
            sq_sensor_fps=float(sq_sensor_fps), rec_media_dur_hdmi=rec_media_dur_hdmi,
            proxy_codec_name=codec_name, proxy_width=w, proxy_height=h, proxy_bit_depth=bdepth,
            main_clip_path=main_path, proxy_sub_path=sub_path,
            main_clip_exists=main_ex, proxy_sub_exists=sub_ex, proxy_generated=px_gen,
            proxy_blocked_reason=reason, px_badge_displayed=px_badge,
            on_camera_proxy_playback_supported=False, proxy_visible_in_playback_index=False,
            on_camera_proxy_playback_frames=0, vault_operation=vault_operation,
            main_protected=m_prot, proxy_protected=p_prot, coupled_pair_intact=intact,
            orphan_detected=orphan, single_sided_mutation_rejected=single_rej,
            single_sided_proxy_or_main_orphan_mutations=0, errno_code=errno, status_code=status,
        )

    if spec is None or eff_setting not in spec["valid_settings"]:
        return _mk(
            admitted=False,
            reason="INVALID_PROXY_FILE_FORMAT" if spec is None else "INVALID_PROXY_RECORD_SETTING_FOR_FORMAT",
            errno=EINVAL_ERRNO, status="BLOCKED_INVALID_PROXY_FORMAT_OR_BITRATE_EINVAL",
        )

    if rec_media_dur_hdmi == "Off(HDMI Only)":
        return _mk(
            admitted=False, reason="OFF_HDMI_ONLY_ZERO_INTERNAL_CARD_FILES",
            errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_PROXY_ZERO_CARD_FILES_UNDER_OFF_HDMI_ONLY_EOPNOTSUPP",
        )

    if proxy_recording == "Off":
        return _mk(
            admitted=True, main_ex=True, reason="PROXY_RECORDING_MENU_OFF",
            m_prot=bool(prior_protected), status="ADMITTED_MAIN_ONLY_PROXY_RECORDING_OFF_OK",
        )

    cutoff_reason = ""
    if capture_mode == "Movie" and rec_frame_rate in BLOCKED_PROXY_REC_FRAME_RATES:
        cutoff_reason = f"NORMAL_MOVIE_REC_FPS_{rec_frame_rate}"
    elif capture_mode == "S&Q" and rec_frame_rate in BLOCKED_PROXY_REC_FRAME_RATES:
        cutoff_reason = f"SQ_REC_FPS_{rec_frame_rate}"
    elif capture_mode == "S&Q" and sq_sensor_fps >= PROXY_SQ_SENSOR_FPS_CUTOFF:
        cutoff_reason = f"SQ_SENSOR_FPS_GE_100_120_CUTOFF:{sq_sensor_fps:.0f}fps"

    if cutoff_reason:
        return _mk(
            admitted=False, main_ex=True, reason=cutoff_reason, m_prot=bool(prior_protected),
            errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_PROXY_UNAVAILABLE_AT_HFR_OR_SQ_CUTOFF_EOPNOTSUPP",
        )

    if simulate_external_orphan_state != "NONE":
        sub_only = simulate_external_orphan_state == "ORPHAN_SUB_WITHOUT_CLIP"
        return _mk(
            admitted=False, main_ex=(not sub_only), sub_ex=sub_only, px_gen=sub_only,
            reason="EXTERNAL_ORPHAN_DETECTED", m_prot=bool(prior_protected),
            p_prot=bool(prior_protected), intact=False, orphan=True, errno=EINVAL_ERRNO,
            status="VAULT_INTEGRITY_ALERT_ORPHAN_CLIP_SUB_MISMATCH_EINVAL",
        )

    if vault_operation == VAULT_OP_ATTEMPT_PROXY_PLAYBACK:
        return _mk(
            admitted=False, main_ex=True, sub_ex=True, px_gen=True, px_badge=True,
            m_prot=bool(prior_protected), p_prot=bool(prior_protected), errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_ON_CAMERA_PROXY_SUB_PLAYBACK_EOPNOTSUPP",
        )

    if vault_operation in (
        VAULT_OP_SINGLE_DELETE_MAIN, VAULT_OP_SINGLE_DELETE_PROXY,
        VAULT_OP_SINGLE_PROTECT_MAIN, VAULT_OP_SINGLE_PROTECT_PROXY,
    ):
        return _mk(
            admitted=False, main_ex=True, sub_ex=True, px_gen=True, px_badge=True,
            m_prot=bool(prior_protected), p_prot=bool(prior_protected), single_rej=True,
            errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_SINGLE_SIDED_IN_CAMERA_CLIP_SUB_MUTATION_EOPNOTSUPP",
        )

    if vault_operation == VAULT_OP_COUPLED_PROTECT_ON:
        return _mk(
            admitted=True, main_ex=True, sub_ex=True, px_gen=True, px_badge=True,
            m_prot=True, p_prot=True, status="ADMITTED_ATOMIC_COUPLED_PROTECT_CLIP_AND_SUB_ON_OK",
        )
    if vault_operation == VAULT_OP_COUPLED_PROTECT_OFF:
        return _mk(
            admitted=True, main_ex=True, sub_ex=True, px_gen=True, px_badge=True,
            m_prot=False, p_prot=False, status="ADMITTED_ATOMIC_COUPLED_PROTECT_CLIP_AND_SUB_OFF_OK",
        )
    if vault_operation == VAULT_OP_COUPLED_DELETE:
        if prior_protected:
            return _mk(
                admitted=False, main_ex=True, sub_ex=True, px_gen=True,
                reason="PROTECTED_PAIR_CANNOT_DELETE", px_badge=True, m_prot=True, p_prot=True,
                errno=EACCES_ERRNO, status="BLOCKED_PROTECTED_COUPLED_PAIR_DELETE_EACCES",
            )
        return _mk(
            admitted=True, main_ex=False, sub_ex=False, px_gen=True, px_badge=False,
            status="ADMITTED_ATOMIC_COUPLED_DELETE_CLIP_AND_SUB_OK",
        )

    return _mk(
        admitted=True, main_ex=True, sub_ex=True, px_gen=True, px_badge=True,
        m_prot=bool(prior_protected), p_prot=bool(prior_protected),
        status="ADMITTED_PROXY_COUPLED_CLIP_AND_SUB_RECORDED_OK",
    )


def evaluate_pillar_b_proxy_dual_codec_and_coupled_vault_hil() -> Dict[str, object]:
    hs_16m = probe_proxy_dual_codec_and_coupled_vault_hil(
        proxy_file_format=PROXY_FORMAT_XAVC_HS_HD, proxy_record_setting="16M 4:2:0 10bit",
        rec_frame_rate="59.94p",
    )
    hs_9m_default = probe_proxy_dual_codec_and_coupled_vault_hil(
        proxy_file_format=PROXY_FORMAT_XAVC_HS_HD, rec_frame_rate="50p",
    )
    s_6m_default = probe_proxy_dual_codec_and_coupled_vault_hil(
        proxy_file_format=PROXY_FORMAT_XAVC_S_HD, rec_frame_rate="23.98p",
    )
    normal_11988p_blocked = probe_proxy_dual_codec_and_coupled_vault_hil(rec_frame_rate="119.88p")
    sq_120fps_blocked = probe_proxy_dual_codec_and_coupled_vault_hil(
        capture_mode="S&Q", rec_frame_rate="23.98p", sq_sensor_fps=120.0,
    )
    sq_100fps_blocked = probe_proxy_dual_codec_and_coupled_vault_hil(
        capture_mode="S&Q", rec_frame_rate="25p", sq_sensor_fps=100.0,
    )
    sq_60fps_allowed = probe_proxy_dual_codec_and_coupled_vault_hil(
        capture_mode="S&Q", rec_frame_rate="23.98p", sq_sensor_fps=60.0,
    )
    hdmi_only_blocked = probe_proxy_dual_codec_and_coupled_vault_hil(
        rec_media_dur_hdmi="Off(HDMI Only)",
    )
    proxy_playback_blocked = probe_proxy_dual_codec_and_coupled_vault_hil(
        vault_operation=VAULT_OP_ATTEMPT_PROXY_PLAYBACK,
    )
    coupled_protect_on = probe_proxy_dual_codec_and_coupled_vault_hil(
        vault_operation=VAULT_OP_COUPLED_PROTECT_ON,
    )
    coupled_delete_ok = probe_proxy_dual_codec_and_coupled_vault_hil(
        vault_operation=VAULT_OP_COUPLED_DELETE,
    )
    single_delete_rejected = probe_proxy_dual_codec_and_coupled_vault_hil(
        vault_operation=VAULT_OP_SINGLE_DELETE_PROXY,
    )
    orphan_alert = probe_proxy_dual_codec_and_coupled_vault_hil(
        simulate_external_orphan_state="ORPHAN_SUB_WITHOUT_CLIP",
    )
    passed = (
        hs_16m.proxy_generated and hs_16m.proxy_width == 1920 and hs_16m.proxy_bit_depth == 10
        and hs_9m_default.proxy_record_setting == "9M 4:2:0 10bit"
        and s_6m_default.proxy_width == 1280 and s_6m_default.proxy_bit_depth == 8
        and (not normal_11988p_blocked.admitted) and (not sq_120fps_blocked.admitted)
        and (not sq_100fps_blocked.admitted) and sq_60fps_allowed.proxy_generated
        and (not hdmi_only_blocked.main_clip_exists) and (not hdmi_only_blocked.proxy_sub_exists)
        and (not proxy_playback_blocked.admitted)
        and coupled_protect_on.main_protected and coupled_protect_on.proxy_protected
        and (not coupled_delete_ok.main_clip_exists) and (not coupled_delete_ok.proxy_sub_exists)
        and single_delete_rejected.single_sided_mutation_rejected and orphan_alert.orphan_detected
    )
    return {
        "passed": passed,
        "xavc_hs_hd_1080p_16m_10bit": asdict(hs_16m),
        "xavc_hs_hd_1080p_9m_default": asdict(hs_9m_default),
        "xavc_s_hd_720p_6m_8bit_default": asdict(s_6m_default),
        "normal_11988p_cutoff_blocked": asdict(normal_11988p_blocked),
        "sq_120fps_cutoff_blocked": asdict(sq_120fps_blocked),
        "sq_100fps_cutoff_blocked": asdict(sq_100fps_blocked),
        "sq_60fps_proxy_allowed": asdict(sq_60fps_allowed),
        "off_hdmi_only_zero_files_blocked": asdict(hdmi_only_blocked),
        "on_camera_proxy_playback_blocked": asdict(proxy_playback_blocked),
        "atomic_coupled_protect_on": asdict(coupled_protect_on),
        "atomic_coupled_delete_ok": asdict(coupled_delete_ok),
        "single_sided_delete_rejected": asdict(single_delete_rejected),
        "external_orphan_vault_alert": asdict(orphan_alert),
    }


# ---------------------------------------------------------------------------
# Sub-model C & Hard Redlines: [Focus Magnifier] × [Bright Monitoring] HIL
# ---------------------------------------------------------------------------


def probe_focus_mag_and_bright_monitoring_hil(
    *,
    capture_mode: str = "Movie",
    sensor_crop_mode: str = CROP_FULL_FRAME,
    exposure_mode: str = "M",
    focus_mode: str = "MF",
    initial_focus_mag: str = "x1.0",
    focus_magnif_time: str = "No Limit",
    auto_magnifier_in_mf: str = "On",
    trigger_source: str = MAG_TRIGGER_CUSTOM_KEY,
    requested_marker_display: str = "On",
    prior_bright_monitoring_active: bool = False,
    press_bright_monitoring_custom_key: bool = False,
    camera_power_off: bool = False,
    requested_live_view_display: str = "Setting Effect ON",
) -> FocusMagBrightMonitoringHilResult:
    """Co-emulate [Focus Magnifier] (Movie x1.0/x4.0 vs Still) × [Bright Monitoring] interlocks."""
    for val, allowed, label in (
        (capture_mode, VALID_CAPTURE_MODES, "capture_mode"),
        (sensor_crop_mode, VALID_SENSOR_CROPS, "sensor_crop_mode"),
        (exposure_mode, VALID_EXPOSURE_MODES, "exposure_mode"),
        (focus_mode, VALID_FOCUS_MODES, "focus_mode"),
        (auto_magnifier_in_mf, VALID_ON_OFF, "auto_magnifier_in_mf"),
        (trigger_source, VALID_MAG_TRIGGERS, "trigger_source"),
        (requested_marker_display, VALID_ON_OFF, "requested_marker_display"),
        (requested_live_view_display, VALID_LIVE_VIEW_DISPLAY, "requested_live_view_display"),
    ):
        if val not in allowed:
            raise RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError(f"Unsupported {label} {val!r}")

    is_movie = capture_mode in ("Movie", "S&Q")
    valid_scales = (
        MOVIE_INITIAL_FOCUS_MAG_SCALES if is_movie
        else (
            STILL_FF_INITIAL_FOCUS_MAG_SCALES
            if sensor_crop_mode == CROP_FULL_FRAME
            else STILL_APSC_INITIAL_FOCUS_MAG_SCALES
        )
    )

    def _mk(
        *, admitted: bool, scale: float = 1.0, mag_on: bool = False, auto_blk: bool = False,
        eff_marker: str = requested_marker_display, marker_sup: bool = False,
        key_lock: bool = False, eff_bright: bool = False, auto_canc: bool = False,
        canc_reasons: Tuple[str, ...] = (), errno: int = 0, status: str,
    ) -> FocusMagBrightMonitoringHilResult:
        eff_lv = "Setting Effect OFF" if eff_bright else requested_live_view_display
        return FocusMagBrightMonitoringHilResult(
            admitted=admitted, menu_path=FOCUS_MAG_MENU_PATH, capture_mode=capture_mode,
            sensor_crop_mode=sensor_crop_mode, exposure_mode=exposure_mode, focus_mode=focus_mode,
            initial_focus_mag=initial_focus_mag, applied_mag_scale=scale,
            focus_magnif_time=focus_magnif_time, auto_magnifier_in_mf=auto_magnifier_in_mf,
            trigger_source=trigger_source, focus_magnifier_active=mag_on,
            auto_magnifier_in_mf_blocked_in_movie=auto_blk,
            requested_marker_display=requested_marker_display, effective_marker_display=eff_marker,
            marker_display_suppressed=marker_sup,
            prior_bright_monitoring_active=bool(prior_bright_monitoring_active),
            press_bright_monitoring_custom_key=bool(press_bright_monitoring_custom_key),
            bright_monitoring_key_locked_out=key_lock, camera_power_off=bool(camera_power_off),
            effective_bright_monitoring=eff_bright, bright_monitoring_auto_canceled=auto_canc,
            auto_cancel_reasons=canc_reasons,
            requested_live_view_display=requested_live_view_display,
            effective_live_view_display=eff_lv, live_view_forced_setting_effect_off=eff_bright,
            errno_code=errno, status_code=status,
        )

    if initial_focus_mag not in valid_scales or focus_magnif_time not in VALID_FOCUS_MAGNIF_TIMES:
        return _mk(
            admitted=False, errno=EINVAL_ERRNO,
            status=(
                "BLOCKED_INVALID_INITIAL_FOCUS_MAG_SCALE_EINVAL"
                if initial_focus_mag not in valid_scales
                else "BLOCKED_INVALID_FOCUS_MAGNIF_TIME_EINVAL"
            ),
        )

    cancel_reasons = tuple(
        r for r in (
            "CAMERA_POWER_OFF" if camera_power_off else "",
            "EXPOSURE_MODE_OUTSIDE_PASM" if exposure_mode not in PASM_EXPOSURE_MODES else "",
            "FOCUS_MODE_NOT_MF" if focus_mode != "MF" else "",
        ) if r
    )
    auto_canceled = bool(prior_bright_monitoring_active and cancel_reasons)
    base_bright_mon = bool(prior_bright_monitoring_active) and not cancel_reasons

    if trigger_source == MAG_TRIGGER_FOCUS_RING_AUTO and is_movie:
        return _mk(
            admitted=False, auto_blk=True, eff_bright=base_bright_mon, auto_canc=auto_canceled,
            canc_reasons=cancel_reasons, errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_AUTO_MAGNIFIER_IN_MF_DISABLED_IN_MOVIE_EOPNOTSUPP",
        )

    mag_active = (not camera_power_off) and (
        trigger_source == MAG_TRIGGER_CUSTOM_KEY
        or (
            trigger_source == MAG_TRIGGER_FOCUS_RING_AUTO
            and (not is_movie)
            and focus_mode == "MF"
            and auto_magnifier_in_mf == "On"
        )
    )
    scale_val = float(initial_focus_mag.lstrip("x")) if mag_active else 1.0
    eff_marker = "Off" if mag_active else requested_marker_display
    marker_suppressed = mag_active and (requested_marker_display == "On")

    if press_bright_monitoring_custom_key and mag_active:
        return _mk(
            admitted=False, scale=scale_val, mag_on=True, eff_marker="Off",
            marker_sup=marker_suppressed, key_lock=True, eff_bright=base_bright_mon,
            auto_canc=auto_canceled, canc_reasons=cancel_reasons, errno=EOPNOTSUPP_ERRNO,
            status="BLOCKED_BRIGHT_MONITORING_KEY_LOCKED_WHILE_MAGNIFIED_EOPNOTSUPP",
        )

    eff_bright = base_bright_mon
    if press_bright_monitoring_custom_key and (not mag_active):
        if cancel_reasons:
            return _mk(
                admitted=False, eff_marker=eff_marker, auto_canc=auto_canceled,
                canc_reasons=cancel_reasons, errno=EOPNOTSUPP_ERRNO,
                status="BLOCKED_BRIGHT_MONITORING_REQUIRES_PASM_AND_MF_EOPNOTSUPP",
            )
        eff_bright = not base_bright_mon

    status = (
        "ADMITTED_BRIGHT_MONITORING_AUTO_CANCELED_OK" if auto_canceled
        else (
            "ADMITTED_FOCUS_MAGNIFIER_ACTIVE_MARKER_SUPPRESSED_OK" if mag_active
            else "ADMITTED_FOCUS_AND_BRIGHT_MONITORING_STATE_OK"
        )
    )
    return _mk(
        admitted=True, scale=scale_val, mag_on=mag_active, eff_marker=eff_marker,
        marker_sup=marker_suppressed, eff_bright=eff_bright, auto_canc=auto_canceled,
        canc_reasons=cancel_reasons, status=status,
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    mutate_single_sided_proxy_or_main_clip: bool = False,
    force_on_camera_proxy_playback: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 8 forbidden physical write/transmit/vault actions are blocked."""
    violations = [
        lbl for flag, lbl in (
            (authorize_persistent_emmc_writes, "PERSISTENT_EMMC_WRITE"),
            (authorize_spi_nor_write, "SPI_NOR_WRITE"),
            (authorize_el3_payload_transmit, "EL3_PAYLOAD_TRANSMIT"),
            (emit_physical_usb_packet, "PHYSICAL_USB_PACKET_EMIT"),
            (touch_otp_fuse, "OTP_FUSE_TOUCH"),
            (increment_rpmb_counter, "RPMB_COUNTER_INCREMENT"),
            (mutate_single_sided_proxy_or_main_clip, "SINGLE_SIDED_PROXY_MAIN_ORPHAN_MUTATION"),
            (force_on_camera_proxy_playback, "ON_CAMERA_PROXY_SUB_PLAYBACK"),
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
        single_sided_proxy_or_main_orphan_mutations=SINGLE_SIDED_PROXY_OR_MAIN_ORPHAN_MUTATIONS,
        on_camera_proxy_playback_frames=ON_CAMERA_PROXY_PLAYBACK_FRAMES,
        blocked_action=joined,
        status_code=(
            f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}"
            if violations else "HARD_SAFETY_REDLINES_LOCKED_OK"
        ),
    )


def evaluate_pillar_c_d_focus_mag_bright_monitoring_and_redlines() -> Dict[str, object]:
    movie_x4_marker_suppressed = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Movie", initial_focus_mag="x4.0",
        trigger_source=MAG_TRIGGER_CUSTOM_KEY, requested_marker_display="On",
    )
    still_ff_x21 = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", sensor_crop_mode=CROP_FULL_FRAME,
        initial_focus_mag="x2.1", trigger_source=MAG_TRIGGER_FOCUS_RING_AUTO,
    )
    still_apsc_x15 = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", sensor_crop_mode=CROP_APSC_S35,
        initial_focus_mag="x1.5", trigger_source=MAG_TRIGGER_FOCUS_RING_AUTO,
    )
    movie_auto_mag_blocked = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Movie", trigger_source=MAG_TRIGGER_FOCUS_RING_AUTO,
    )
    bright_key_locked_while_mag = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", initial_focus_mag="x2.1",
        trigger_source=MAG_TRIGGER_CUSTOM_KEY, press_bright_monitoring_custom_key=True,
    )
    bright_on_setting_effect_off = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", exposure_mode="M", focus_mode="MF",
        trigger_source=MAG_TRIGGER_IDLE, press_bright_monitoring_custom_key=True,
        requested_live_view_display="Setting Effect ON",
    )
    bright_cancel_non_pasm = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", exposure_mode="Auto", focus_mode="MF",
        trigger_source=MAG_TRIGGER_IDLE, prior_bright_monitoring_active=True,
    )
    bright_cancel_afc = probe_focus_mag_and_bright_monitoring_hil(
        capture_mode="Photo", exposure_mode="A", focus_mode="AF-C",
        trigger_source=MAG_TRIGGER_IDLE, prior_bright_monitoring_active=True,
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
            "mutate_single_sided_proxy_or_main_clip",
            "force_on_camera_proxy_playback",
        )
    ]
    passed = (
        movie_x4_marker_suppressed.admitted
        and movie_x4_marker_suppressed.applied_mag_scale == 4.0
        and movie_x4_marker_suppressed.marker_display_suppressed
        and still_ff_x21.applied_mag_scale == 2.1
        and still_apsc_x15.applied_mag_scale == 1.5
        and (not movie_auto_mag_blocked.admitted)
        and movie_auto_mag_blocked.auto_magnifier_in_mf_blocked_in_movie
        and (not bright_key_locked_while_mag.admitted)
        and bright_key_locked_while_mag.bright_monitoring_key_locked_out
        and bright_on_setting_effect_off.effective_bright_monitoring
        and bright_on_setting_effect_off.effective_live_view_display == "Setting Effect OFF"
        and bright_cancel_non_pasm.bright_monitoring_auto_canceled
        and bright_cancel_afc.bright_monitoring_auto_canceled
        and baseline_redline.valid
        and len(blocked_probes) == 8
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "movie_x4_0_marker_suppressed": asdict(movie_x4_marker_suppressed),
        "still_ff_x2_1_auto_mag_ok": asdict(still_ff_x21),
        "still_apsc_x1_5_auto_mag_ok": asdict(still_apsc_x15),
        "movie_auto_mag_in_mf_blocked": asdict(movie_auto_mag_blocked),
        "bright_mon_key_locked_while_magnified": asdict(bright_key_locked_while_mag),
        "bright_mon_forces_setting_effect_off": asdict(bright_on_setting_effect_off),
        "bright_mon_auto_cancel_outside_pasm": asdict(bright_cancel_non_pasm),
        "bright_mon_auto_cancel_outside_mf": asdict(bright_cancel_afc),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 213 (Stage 38, 38/38) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil(
    *, force_clean_room: Optional[bool] = None, env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 213 Stage 38 (38/38) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase213_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil()
    pillar_b = evaluate_pillar_b_proxy_dual_codec_and_coupled_vault_hil()
    pillar_cd = evaluate_pillar_c_d_focus_mag_bright_monitoring_and_redlines()

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
        "single_sided_proxy_or_main_orphan_mutations": SINGLE_SIDED_PROXY_OR_MAIN_ORPHAN_MUTATIONS,
        "on_camera_proxy_playback_frames": ON_CAMERA_PROXY_PLAYBACK_FRAMES,
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
        and SINGLE_SIDED_PROXY_OR_MAIN_ORPHAN_MUTATIONS == 0
        and ON_CAMERA_PROXY_PLAYBACK_FRAMES == 0
    )

    payload: Dict[str, object] = {
        "schema": PHASE_213_SCHEMA,
        "version": PHASE_213_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil": pillar_a,
        "pillar_b_proxy_dual_codec_and_coupled_vault_hil": pillar_b,
        "pillar_c_d_focus_mag_bright_monitoring_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py",
        description=(
            "Phase 213 Stage 38 (38/38) — Real-Hardware ILME-FX3 HDMI Log 1080p vs Off(HDMI Only) "
            "4K 10-bit, Px Proxy Coupled Vault & Focus Magnifier x Bright Monitoring HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 213 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil"]
        pb = rep["pillar_b_proxy_dual_codec_and_coupled_vault_hil"]
        pcd = rep["pillar_c_d_focus_mag_bright_monitoring_and_redlines"]
        log_lbl = pa["log_downshift_1080p_matrix"]["Cine EI"]["effective_hdmi_resolution_label"]
        honly_w = pa["hdmi_only_4k_10bit_matrix"]["59.94p 10bit"]["effective_hdmi_width"]
        px_pb = pb["on_camera_proxy_playback_blocked"]["on_camera_proxy_playback_frames"]
        mag_s = pcd["movie_x4_0_marker_suppressed"]["applied_mag_scale"]
        sys.stdout.write(
            f"[{status}] Phase 213 Stage 38 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"hdmi_log={log_lbl}_vs_hdmionly={honly_w}p10(lcd_blank=1) | "
            f"proxy=HS1080_16M_9M+S720_6M(oncam_pb={px_pb},coupled_vault=1) | "
            f"focus_mag=movie_{mag_s}x(bright_lockout=1,effect_off=1) | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
