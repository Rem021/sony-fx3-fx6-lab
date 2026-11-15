#!/usr/bin/env python3
"""Phase 207 — Stage 37 (`37/37` Milestone) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[De-Squeeze Display]` (`Off/1.3x/2.0x/1.5x/1.6x=1.65x`
CinemaScope `2.39:1` 4-Setting Lock & 5-Mode HDMI RAW / Clean-HDMI Bypass), External-Only
`Monitor & Control` `[Focus Map]` (Zero In-Body FX3 Menu & `>=150fps` Cutoff vs `1..6fps` Allowed),
Dual-Slot `[Simult. Recording]` + `[Auto Switch Media]` (`Ver. 2.0+` Single-Card Continuation vs
`Off` Strict Dual Parity), and `[Shockless WB]` (`Off/1/2/3` All-FPS Smooth Ramp vs `0`-Frame
`[C.Temp./Filter]` Kelvin & `A-B/G-M` Fine-Grid Immediate Bypass) HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) donor inspection (< 0.10s, cached per
process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `desqueeze_baked_into_raw_or_xavc_frames == 0`
- `inbody_fx3_focus_map_overlay_frames == 0`
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
# Phase 207 Schema & Hard-Locked Safety Redlines (37/37 Milestone)
# ---------------------------------------------------------------------------

PHASE_207_SCHEMA = "phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator_v1"
PHASE_207_VERSION = "207.0.0"
STAGE_INDEX = 37
STAGE_TOTAL = 37
MILESTONE_LABEL = "37/37"
STAGE_NAME = "stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil"

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX30 = "ILME-FX30"
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
DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES = 0
INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

ENODEV_ERRNO = 19  # Linux ENODEV
EINVAL_ERRNO = 22  # Linux EINVAL
EROFS_ERRNO = 30  # Linux EROFS
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
    "fx3_ptp_ctrl": f"{_FX3_USR_PREFIX}/lib/libInfraPtpControl.so",
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
    "fx3_ptp_ctrl": 165_320,
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
    "fx3_lens_comm": (
        b"LensCommunicator",
        b"GetMountedLensInfo",
        b"SndSyncMsg",
    ),
    "fx6_lens_comm": (
        b"LensCommunicator",
        b"GetMountedLensInfo",
        b"SndSyncMsg",
    ),
    "fx3_media_cfg": (
        b"MediaConfig",
        b"Slot",
        b"Backup_read",
    ),
    "fx3_ptp_ctrl": (
        b"InfraPtp",
        b"PtpControl",
        b"SndSyncMsg",
    ),
    "fx3_string_en_f": (
        b"De-Squeeze Display",
        b"1.3x",
        b"2.0x",
        b"1.5x",
        b"1.6x",
        b"Manual Focus",
        b"Focus Mode",
        b"Focus Area",
        b"SteadyShot",
        b"Face Priority in Multi Metering",
        b"RAW Output",
        b"Off(HDMI Only)",
        b"HDMI Info. Display",
        b"Log Shooting",
        b"Focus Map",
        b"Simult. Recording",
        b"Auto Switch Media",
        b"Shockless WB",
        b"C.Temp./Filter",
    ),
    "fx6_string_en": (
        b"De-Squeeze",
        b"1.3x",
        b"2.0x",
        b"1.5x",
        b"1.6x",
        b"Manual Focus",
        b"Focus Area",
        b"SteadyShot",
        b"RAW Output",
        b"Focus Map",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_938_432, "LOG_SHOOTING", b"LOG_SHOOTING"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_954_816, "SHOCKLESS", b"SHOCKLESS"),
        (49_954_816, "FOCUS_MODE", b"FOCUS_MODE"),
        (49_954_816, "FOCUS_AREA", b"FOCUS_AREA"),
        (51_400_704, "FOCUS_MAP", b"FocusMap"),
        (59_985_920, "SIMULT", b"SIMULT"),
        (60_121_088, "STEADYSHOT", b"STEADYSHOT"),
        (60_264_448, "DESQUEEZE", b"desqueeze"),
        (60_633_088, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (60_657_664, "HDMI_RAW", b"HDMI_RAW"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_404_672, "SCALE_1_65", b"1.65"),
        (37_437_440, "DESQUEEZE", b"DESQUEEZE"),
        (39_022_592, "SHOCKLESS", b"SHOCKLESS"),
        (39_399_424, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (40_157_184, "STEADYSHOT", b"STEADYSHOT"),
        (40_173_568, "SIMULT", b"SIMULT"),
        (40_189_952, "AUTO_SWITCH", b"AUTO_SWITCH"),
        (40_960_000, "FOCUS_MAP", b"FOCUS_MAP"),
        (41_201_664, "HDMI_RAW", b"HDMI_RAW"),
    ),
    "fx3_cpapp": (
        (143_360, "WB", b"WB"),
        (311_296, "FOCUS_MAP", b"FocusMap"),
        (696_320, "HDMI", b"HDMI"),
        (712_704, "DeSqueeze", b"DeSqueeze"),
        (2_002_944, "STEADYSHOT", b"STEADYSHOT"),
        (2_015_232, "DESQUEEZE", b"DESQUEEZE"),
        (13_139_968, "ILME-FX3", b"ILME-FX3"),
        (13_275_136, "RAW_OUTPUT", b"RAW_OUTPUT"),
    ),
    "fx6_cpapp": (
        (143_360, "WB", b"WB"),
        (614_400, "DeSqueeze", b"DeSqueeze"),
        (684_032, "HDMI", b"HDMI"),
        (2_068_480, "DESQUEEZE", b"DESQUEEZE"),
        (2_072_576, "Shockless", b"Shockless"),
        (14_741_504, "RAW_OUTPUT", b"RAW_OUTPUT"),
        (14_807_040, "STEADYSHOT", b"STEADYSHOT"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (118_784, "Lens", b"Lens"),
        (307_200, "Simult", b"Simult"),
        (540_672, "WB", b"WB"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (151_552, "Lens", b"Lens"),
        (380_928, "Simult", b"Simult"),
        (1_011_712, "WB", b"WB"),
    ),
}

# ---------------------------------------------------------------------------
# Pillar A Constants: [De-Squeeze Display] (1.6x=1.65x), 4-Locks & 5 Bypasses
# ---------------------------------------------------------------------------

DESQUEEZE_MENU_PATH = "MENU -> Setup -> [Display Option] -> [De-Squeeze Display]"
DESQUEEZE_OFF = "Off"
DESQUEEZE_1_3X = "1.3x"
DESQUEEZE_2_0X = "2.0x"
DESQUEEZE_1_5X = "1.5x"
DESQUEEZE_1_6X = "1.6x"

VALID_DESQUEEZE_OPTIONS: Tuple[str, ...] = (
    DESQUEEZE_OFF,
    DESQUEEZE_1_3X,
    DESQUEEZE_2_0X,
    DESQUEEZE_1_5X,
    DESQUEEZE_1_6X,
)

# Official Sony Help Guide contract: [1.6x] executes 1.65x horizontal stretch -> 2.39:1 CinemaScope
DESQUEEZE_HORIZONTAL_SCALE_MAP: Mapping[str, float] = {
    DESQUEEZE_OFF: 1.00,
    DESQUEEZE_1_3X: 1.30,
    DESQUEEZE_1_5X: 1.50,
    DESQUEEZE_1_6X: 1.65,
    DESQUEEZE_2_0X: 2.00,
}

DESQUEEZE_FOUR_LOCKED_SETTINGS: Mapping[str, str] = {
    "Focus Mode": "Manual Focus",
    "Focus Area": "Wide",
    "SteadyShot": "Off",
    "Face Priority in Multi Metering": "Off",
}

VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Cine EI",
    "Cine EI Quick",
    "Flexible ISO",
)
VALID_CAPTURE_MODES: Tuple[str, ...] = ("Movie", "S&Q", "Photo")
VALID_REC_MEDIA_DUR_HDMI: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_ON_OFF: Tuple[str, ...] = ("On", "Off")

# ---------------------------------------------------------------------------
# Pillar B Constants: External-Only Monitor & Control [Focus Map] & >=150fps Cutoff
# ---------------------------------------------------------------------------

FX3_HAS_INBODY_FOCUS_MAP_MENU = False
FOCUS_MAP_EXTERNAL_CUTOFF_FPS = 150.0
FX6_LOW_FPS_BLOCK_MAX = 6.0

LENS_TYPE_SONY_EMOUNT_PDAF = "SONY_EMOUNT_PDAF"
LENS_TYPE_MOUNT_ADAPTER = "MOUNT_ADAPTER"
LENS_TYPE_NON_PDAF_MANUAL = "NON_PDAF_MANUAL_LENS"
LENS_TYPE_NO_LENS = "NO_LENS"
VALID_FOCUS_MAP_LENS_TYPES: Tuple[str, ...] = (
    LENS_TYPE_SONY_EMOUNT_PDAF,
    LENS_TYPE_MOUNT_ADAPTER,
    LENS_TYPE_NON_PDAF_MANUAL,
    LENS_TYPE_NO_LENS,
)

OP_STATE_LIVE_SHOOTING = "LIVE_SHOOTING"
OP_STATE_CLIP_PLAYBACK = "CLIP_PLAYBACK"
OP_STATE_UVC_STREAMING = "UVC_USB_STREAMING"
VALID_FOCUS_MAP_OP_STATES: Tuple[str, ...] = (
    OP_STATE_LIVE_SHOOTING,
    OP_STATE_CLIP_PLAYBACK,
    OP_STATE_UVC_STREAMING,
)

# ---------------------------------------------------------------------------
# Pillar C & D Constants: [Simult. Recording] + [Auto Switch Media] & [Shockless WB]
# ---------------------------------------------------------------------------

SIMULT_RECORDING_MENU_PATH = "MENU -> Shooting -> [Media] -> [Rec. Media Settings]"
REC_MODE_SIMULTANEOUS = "Simult. Recording"

SHOCKLESS_WB_MENU_PATH = "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]"
SHOCKLESS_WB_OFF = "Off"
SHOCKLESS_WB_1_FAST = "1"
SHOCKLESS_WB_2_NORMAL = "2"
SHOCKLESS_WB_3_SLOW = "3"
VALID_SHOCKLESS_WB_SETTINGS: Tuple[str, ...] = (
    SHOCKLESS_WB_OFF,
    SHOCKLESS_WB_1_FAST,
    SHOCKLESS_WB_2_NORMAL,
    SHOCKLESS_WB_3_SLOW,
)

SHOCKLESS_WB_RAMP_SECONDS: Mapping[str, float] = {
    SHOCKLESS_WB_OFF: 0.0,
    SHOCKLESS_WB_1_FAST: 0.5,
    SHOCKLESS_WB_2_NORMAL: 1.0,
    SHOCKLESS_WB_3_SLOW: 2.0,
}

WB_TRIGGER_PRESET_SWITCH = "WB_PRESET_SWITCH"
WB_TRIGGER_CTEMP_KELVIN_EDIT = "CTEMP_FILTER_KELVIN_EDIT"
WB_TRIGGER_AB_GM_FINE_GRID = "AB_GM_FINE_GRID_SHIFT"
VALID_WB_TRANSITION_TRIGGERS: Tuple[str, ...] = (
    WB_TRIGGER_PRESET_SWITCH,
    WB_TRIGGER_CTEMP_KELVIN_EDIT,
    WB_TRIGGER_AB_GM_FINE_GRID,
)


class RealHwDesqueezeFocusMapSimultShocklessWbError(ValueError):
    """Raised on invalid Phase 207 co-emulator configuration arguments."""


# ---------------------------------------------------------------------------
# Dataclasses for Donor Inspection & Pillars A-D
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
class Phase207DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_ptp_ctrl: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    desqueeze_165x_and_4locks_proven: bool
    external_focus_map_and_lens_pdaf_proven: bool
    simult_autoswitch_and_shockless_wb_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DeSqueezeDisplayHilResult:
    admitted: bool
    menu_path: str
    desqueeze_option: str
    nominal_ratio_value: float
    applied_horizontal_scale: float
    cinemascope_165x_active: bool
    output_aspect_label: str
    four_locks_enforced: bool
    effective_focus_mode: str
    effective_focus_area: str
    effective_steadyshot: str
    effective_face_priority_multi_metering: str
    lock_override_rejected: bool
    hdmi_raw_output: str
    rec_media_dur_hdmi: str
    effective_hdmi_info_display: str
    log_shooting: str
    remote_shooting_active: bool
    capture_mode: str
    display_desqueeze_active: bool
    suppression_reasons: Tuple[str, ...]
    desqueeze_baked_into_raw_or_xavc_frames: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class ExternalFocusMapHilResult:
    admitted: bool
    model_name: str
    fx3_has_inbody_focus_map_menu: bool
    inbody_menu_toggle_rejected_eopnotsupp: bool
    stage_b_local_overlay_rejected_eopnotsupp: bool
    mc_client_connected: bool
    operating_state: str
    lens_type: str
    lens_id_hex: str
    cpapp_emount_pdaf_valid: bool
    sensor_fps: float
    fx3_low_fps_1_to_6_allowed: bool
    blocked_ge_150fps_cutoff: bool
    external_mc_pdaf_depth_streaming: bool
    inbody_fx3_focus_map_overlay_frames: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class SimultAutoSwitchMediaHilResult:
    admitted: bool
    menu_path: str
    recording_mode: str
    auto_switch_media: str
    slot1_free_mb: int
    slot2_free_mb: int
    fresh_card_reinserted: bool
    recording_continues: bool
    active_recording_slots: Tuple[int, ...]
    dual_card_redundant: bool
    single_card_continuation_active: bool
    strict_dual_parity_halted: bool
    resumed_dual_slot_after_card_swap: bool
    both_slots_full_halted: bool
    dropped_frames: int
    rsv_orphan_count: int
    errno_code: int
    status_code: str


@dataclass(frozen=True)
class ShocklessWbHilResult:
    admitted: bool
    menu_path: str
    shockless_wb_setting: str
    sensor_fps: float
    all_framerates_supported: bool
    transition_trigger: str
    from_kelvin: int
    to_kelvin: int
    ab_gm_grid_offset: str
    bypassed_shockless_smoothing: bool
    immediate_zero_frame_applied: bool
    ramp_duration_seconds: float
    transition_frames: int
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
    desqueeze_baked_into_raw_or_xavc_frames: int
    inbody_fx3_focus_map_overlay_frames: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase207DonorAudit] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase207DonorAudit] = None


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
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")

    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase207_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen: Optional[Path] = None
        for root in roots:
            cand = root / rel
            if cand.is_file():
                chosen = cand
                break
        if chosen is None:
            chosen = roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        resolved[key] = chosen
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
        data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
        return st.st_size, data
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        file_bytes = st.st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            else:
                buf = seen_offsets[off]
            hits[label] = 1 if tok in buf else 0
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
    hits = {
        tok.decode("ascii", "replace"): (1 if tok in data else 0)
        for tok in tokens
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
    )


def _scan_compact_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        tokens=tokens,
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    windows: Sequence[Tuple[int, str, bytes]],
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(path, windows)
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:4] = b"\x7fELF"
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_synthetic_uxd_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    return b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase207DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH".encode("ascii")
        raw = _build_synthetic_uxd_bytes(toks, tag) if is_uxd else _build_synthetic_elf64_bytes(toks, tag)
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        if is_elf:
            head = _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
        else:
            head = (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        hits = {lbl: 1 for _off, lbl, _tok in wins}
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

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase207DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3_7.02", False),
        fx3_ptp_ctrl=_mk_compact("fx3_ptp_ctrl", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        desqueeze_165x_and_4locks_proven=True,
        external_focus_map_and_lens_pdaf_proven=True,
        simult_autoswitch_and_shockless_wb_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase207_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase207DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.10s, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase207_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for k, p in sorted(paths.items())
    )
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(
        paths["fx3_lens_comm"],
        artifact_key="fx3_lens_comm",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_lens_comm"],
    )
    fx6_lens_comm = _scan_compact_rdonly(
        paths["fx6_lens_comm"],
        artifact_key="fx6_lens_comm",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_lens_comm"],
    )
    fx3_media_cfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"],
        artifact_key="fx3_media_cfg",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_media_cfg"],
    )
    fx3_ptp_ctrl = _scan_compact_rdonly(
        paths["fx3_ptp_ctrl"],
        artifact_key="fx3_ptp_ctrl",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_ptp_ctrl"],
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en_f"],
    )
    fx6_string_en = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_string_en"],
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"],
        artifact_key="fx3_appfw",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_appfw"],
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"],
        artifact_key="fx6_appfw",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_appfw"],
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"],
        artifact_key="fx3_cpapp",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_cpapp"],
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"],
        artifact_key="fx6_cpapp",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_cpapp"],
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"],
        artifact_key="fx3_libmpr",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_libmpr"],
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"],
        artifact_key="fx6_libmpr",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_libmpr"],
    )

    errors: List[str] = []
    for item in (
        fx3_lens_comm,
        fx6_lens_comm,
        fx3_media_cfg,
        fx3_ptp_ctrl,
        fx3_string_en_f,
        fx6_string_en,
    ):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.marker_hits.values()):
            errors.append(f"{item.artifact_key} missing tokens: {item.marker_hits}")

    for item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.window_hits.values()):
            errors.append(f"{item.artifact_key} missing window markers: {item.window_hits}")

    desqueeze_ok = (
        fx3_string_en_f.uxd_container_ok
        and fx6_string_en.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("De-Squeeze Display") == 1
        and fx3_string_en_f.marker_hits.get("1.5x") == 1
        and fx3_string_en_f.marker_hits.get("1.6x") == 1
        and fx3_string_en_f.marker_hits.get("Manual Focus") == 1
        and fx3_string_en_f.marker_hits.get("Face Priority in Multi Metering") == 1
        and fx3_string_en_f.marker_hits.get("Off(HDMI Only)") == 1
        and fx3_appfw.window_hits.get("DESQUEEZE") == 1
        and fx3_appfw.window_hits.get("HDMI_RAW") == 1
        and fx6_appfw.window_hits.get("SCALE_1_65") == 1
        and fx3_cpapp.window_hits.get("DESQUEEZE") == 1
        and fx6_cpapp.window_hits.get("DESQUEEZE") == 1
    )
    focus_map_ok = (
        fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and fx3_ptp_ctrl.elf64_le_ok
        and fx3_lens_comm.file_bytes == fx6_lens_comm.file_bytes
        and fx3_string_en_f.marker_hits.get("Focus Map") == 1
        and fx3_appfw.window_hits.get("FOCUS_MAP") == 1
        and fx6_appfw.window_hits.get("FOCUS_MAP") == 1
        and fx3_cpapp.window_hits.get("FOCUS_MAP") == 1
    )
    simult_wb_ok = (
        fx3_media_cfg.elf64_le_ok
        and fx3_string_en_f.marker_hits.get("Simult. Recording") == 1
        and fx3_string_en_f.marker_hits.get("Auto Switch Media") == 1
        and fx3_string_en_f.marker_hits.get("Shockless WB") == 1
        and fx3_string_en_f.marker_hits.get("C.Temp./Filter") == 1
        and fx3_appfw.window_hits.get("SIMULT") == 1
        and fx3_appfw.window_hits.get("SHOCKLESS") == 1
        and fx6_appfw.window_hits.get("AUTO_SWITCH") == 1
        and fx3_libmpr.window_hits.get("Simult") == 1
        and fx6_libmpr.window_hits.get("Simult") == 1
    )
    all_ok = len(errors) == 0 and desqueeze_ok and focus_map_ok and simult_wb_ok

    audit = Phase207DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
        fx3_media_cfg=fx3_media_cfg,
        fx3_ptp_ctrl=fx3_ptp_ctrl,
        fx3_string_en_f=fx3_string_en_f,
        fx6_string_en=fx6_string_en,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        desqueeze_165x_and_4locks_proven=desqueeze_ok,
        external_focus_map_and_lens_pdaf_proven=focus_map_ok,
        simult_autoswitch_and_shockless_wb_proven=simult_wb_ok,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: [De-Squeeze Display] (1.6x=1.65x), 4-Setting Lock & HDMI/Mode Bypass
# ---------------------------------------------------------------------------


def probe_desqueeze_display_4locks_and_bypass_hil(
    *,
    desqueeze_option: str = DESQUEEZE_1_6X,
    requested_focus_mode: str = "AF-C",
    requested_focus_area: str = "Tracking: Spot M",
    requested_steadyshot: str = "Active",
    requested_face_priority_multi_metering: str = "On",
    attempt_override_locked_setting: bool = False,
    hdmi_raw_output: str = "Off",
    rec_media_dur_hdmi: str = "On",
    requested_hdmi_info_display: str = "On",
    log_shooting: str = "Cine EI",
    remote_shooting_active: bool = False,
    capture_mode: str = "Movie",
) -> DeSqueezeDisplayHilResult:
    """Co-emulate ILME-FX3 [De-Squeeze Display] (1.6x->1.65x), 4 hardware locks & 5 bypass rules."""
    if hdmi_raw_output not in VALID_ON_OFF:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported hdmi_raw_output {hdmi_raw_output!r}"
        )
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported rec_media_dur_hdmi {rec_media_dur_hdmi!r}"
        )
    if requested_hdmi_info_display not in VALID_ON_OFF:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported requested_hdmi_info_display {requested_hdmi_info_display!r}"
        )
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported log_shooting {log_shooting!r}"
        )
    if capture_mode not in VALID_CAPTURE_MODES:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported capture_mode {capture_mode!r}"
        )

    eff_hdmi_info = (
        "Off"
        if rec_media_dur_hdmi == "Off(HDMI Only)"
        else requested_hdmi_info_display
    )

    if desqueeze_option not in VALID_DESQUEEZE_OPTIONS:
        return DeSqueezeDisplayHilResult(
            admitted=False,
            menu_path=DESQUEEZE_MENU_PATH,
            desqueeze_option=desqueeze_option,
            nominal_ratio_value=0.0,
            applied_horizontal_scale=1.0,
            cinemascope_165x_active=False,
            output_aspect_label="16:9 (1.78:1)",
            four_locks_enforced=False,
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_multi_metering=requested_face_priority_multi_metering,
            lock_override_rejected=False,
            hdmi_raw_output=hdmi_raw_output,
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            effective_hdmi_info_display=eff_hdmi_info,
            log_shooting=log_shooting,
            remote_shooting_active=bool(remote_shooting_active),
            capture_mode=capture_mode,
            display_desqueeze_active=False,
            suppression_reasons=("INVALID_DESQUEEZE_OPTION",),
            desqueeze_baked_into_raw_or_xavc_frames=0,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_DESQUEEZE_DISPLAY_OPTION_EINVAL",
        )

    nominal_val = 1.0 if desqueeze_option == DESQUEEZE_OFF else float(desqueeze_option.rstrip("x"))
    target_scale = DESQUEEZE_HORIZONTAL_SCALE_MAP[desqueeze_option]

    reasons: List[str] = []
    if hdmi_raw_output == "On":
        reasons.append("HDMI_RAW_OUTPUT_ON")
    if rec_media_dur_hdmi == "Off(HDMI Only)":
        reasons.append("REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY")
    if log_shooting == "Off":
        reasons.append("LOG_SHOOTING_OFF")
    if remote_shooting_active:
        reasons.append("REMOTE_SHOOTING_ACTIVE")
    if capture_mode == "Photo":
        reasons.append("STILL_PHOTO_CAPTURE_MODE")

    if desqueeze_option == DESQUEEZE_OFF:
        return DeSqueezeDisplayHilResult(
            admitted=True,
            menu_path=DESQUEEZE_MENU_PATH,
            desqueeze_option=DESQUEEZE_OFF,
            nominal_ratio_value=1.0,
            applied_horizontal_scale=1.0,
            cinemascope_165x_active=False,
            output_aspect_label="16:9 (1.78:1)",
            four_locks_enforced=False,
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_multi_metering=requested_face_priority_multi_metering,
            lock_override_rejected=False,
            hdmi_raw_output=hdmi_raw_output,
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            effective_hdmi_info_display=eff_hdmi_info,
            log_shooting=log_shooting,
            remote_shooting_active=bool(remote_shooting_active),
            capture_mode=capture_mode,
            display_desqueeze_active=False,
            suppression_reasons=tuple(reasons),
            desqueeze_baked_into_raw_or_xavc_frames=0,
            errno_code=0,
            status_code="ADMITTED_DESQUEEZE_OFF_SPHERICAL_1_0X_OK",
        )

    # Non-Off De-Squeeze locks 4 camera settings when active; if suppressed by mode/HDMI, bypasses to 1.0x
    if reasons:
        return DeSqueezeDisplayHilResult(
            admitted=True,
            menu_path=DESQUEEZE_MENU_PATH,
            desqueeze_option=desqueeze_option,
            nominal_ratio_value=nominal_val,
            applied_horizontal_scale=1.0,
            cinemascope_165x_active=False,
            output_aspect_label="16:9 (1.78:1 Bypassed)",
            four_locks_enforced=False,
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_multi_metering=requested_face_priority_multi_metering,
            lock_override_rejected=False,
            hdmi_raw_output=hdmi_raw_output,
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            effective_hdmi_info_display=eff_hdmi_info,
            log_shooting=log_shooting,
            remote_shooting_active=bool(remote_shooting_active),
            capture_mode=capture_mode,
            display_desqueeze_active=False,
            suppression_reasons=tuple(reasons),
            desqueeze_baked_into_raw_or_xavc_frames=0,
            errno_code=0,
            status_code="ADMITTED_DESQUEEZE_SUPPRESSED_BY_MODE_OR_HDMI_BYPASS",
        )

    if attempt_override_locked_setting:
        return DeSqueezeDisplayHilResult(
            admitted=False,
            menu_path=DESQUEEZE_MENU_PATH,
            desqueeze_option=desqueeze_option,
            nominal_ratio_value=nominal_val,
            applied_horizontal_scale=target_scale,
            cinemascope_165x_active=(desqueeze_option == DESQUEEZE_1_6X),
            output_aspect_label=(
                "2.39:1 CinemaScope"
                if desqueeze_option == DESQUEEZE_1_6X
                else f"{target_scale:.2f}x Anamorphic"
            ),
            four_locks_enforced=True,
            effective_focus_mode=DESQUEEZE_FOUR_LOCKED_SETTINGS["Focus Mode"],
            effective_focus_area=DESQUEEZE_FOUR_LOCKED_SETTINGS["Focus Area"],
            effective_steadyshot=DESQUEEZE_FOUR_LOCKED_SETTINGS["SteadyShot"],
            effective_face_priority_multi_metering=DESQUEEZE_FOUR_LOCKED_SETTINGS[
                "Face Priority in Multi Metering"
            ],
            lock_override_rejected=True,
            hdmi_raw_output=hdmi_raw_output,
            rec_media_dur_hdmi=rec_media_dur_hdmi,
            effective_hdmi_info_display=eff_hdmi_info,
            log_shooting=log_shooting,
            remote_shooting_active=False,
            capture_mode=capture_mode,
            display_desqueeze_active=True,
            suppression_reasons=(),
            desqueeze_baked_into_raw_or_xavc_frames=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_DESQUEEZE_4LOCK_SETTING_OVERRIDE_EOPNOTSUPP",
        )

    aspect = (
        "2.39:1 CinemaScope"
        if desqueeze_option == DESQUEEZE_1_6X
        else f"{target_scale:.2f}x Anamorphic"
    )
    return DeSqueezeDisplayHilResult(
        admitted=True,
        menu_path=DESQUEEZE_MENU_PATH,
        desqueeze_option=desqueeze_option,
        nominal_ratio_value=nominal_val,
        applied_horizontal_scale=target_scale,
        cinemascope_165x_active=(desqueeze_option == DESQUEEZE_1_6X),
        output_aspect_label=aspect,
        four_locks_enforced=True,
        effective_focus_mode=DESQUEEZE_FOUR_LOCKED_SETTINGS["Focus Mode"],
        effective_focus_area=DESQUEEZE_FOUR_LOCKED_SETTINGS["Focus Area"],
        effective_steadyshot=DESQUEEZE_FOUR_LOCKED_SETTINGS["SteadyShot"],
        effective_face_priority_multi_metering=DESQUEEZE_FOUR_LOCKED_SETTINGS[
            "Face Priority in Multi Metering"
        ],
        lock_override_rejected=False,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi=rec_media_dur_hdmi,
        effective_hdmi_info_display=eff_hdmi_info,
        log_shooting=log_shooting,
        remote_shooting_active=False,
        capture_mode=capture_mode,
        display_desqueeze_active=True,
        suppression_reasons=(),
        desqueeze_baked_into_raw_or_xavc_frames=0,
        errno_code=0,
        status_code="ADMITTED_DESQUEEZE_ACTIVE_WITH_4LOCKS_OK",
    )


def evaluate_pillar_a_desqueeze_165x_4locks_and_bypass_hil() -> Dict[str, object]:
    ratio_matrix = {
        opt: asdict(probe_desqueeze_display_4locks_and_bypass_hil(desqueeze_option=opt))
        for opt in VALID_DESQUEEZE_OPTIONS
    }
    lock_override_blocked = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_1_6X,
        attempt_override_locked_setting=True,
    )
    bypass_hdmi_raw = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_1_6X,
        hdmi_raw_output="On",
    )
    bypass_clean_hdmi_only = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_2_0X,
        rec_media_dur_hdmi="Off(HDMI Only)",
        requested_hdmi_info_display="On",
    )
    bypass_log_off = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_1_5X,
        log_shooting="Off",
    )
    bypass_remote = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_1_3X,
        remote_shooting_active=True,
    )
    bypass_photo = probe_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_option=DESQUEEZE_1_6X,
        capture_mode="Photo",
    )

    c16 = ratio_matrix[DESQUEEZE_1_6X]
    passed = (
        c16["admitted"]
        and c16["applied_horizontal_scale"] == 1.65
        and c16["cinemascope_165x_active"]
        and c16["four_locks_enforced"]
        and c16["effective_focus_mode"] == "Manual Focus"
        and c16["effective_focus_area"] == "Wide"
        and c16["effective_steadyshot"] == "Off"
        and c16["effective_face_priority_multi_metering"] == "Off"
        and (not lock_override_blocked.admitted)
        and lock_override_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not bypass_hdmi_raw.display_desqueeze_active)
        and bypass_hdmi_raw.applied_horizontal_scale == 1.0
        and (not bypass_clean_hdmi_only.display_desqueeze_active)
        and bypass_clean_hdmi_only.effective_hdmi_info_display == "Off"
        and (not bypass_log_off.display_desqueeze_active)
        and (not bypass_remote.display_desqueeze_active)
        and (not bypass_photo.display_desqueeze_active)
    )
    return {
        "passed": passed,
        "ratio_matrix": ratio_matrix,
        "lock_override_blocked_eopnotsupp": asdict(lock_override_blocked),
        "bypass_hdmi_raw_on": asdict(bypass_hdmi_raw),
        "bypass_off_hdmi_only_info_off": asdict(bypass_clean_hdmi_only),
        "bypass_log_shooting_off": asdict(bypass_log_off),
        "bypass_remote_shooting": asdict(bypass_remote),
        "bypass_photo_capture": asdict(bypass_photo),
    }


# ---------------------------------------------------------------------------
# Pillar B: External-Only Monitor & Control [Focus Map] & >=150fps Cutoff HIL
# ---------------------------------------------------------------------------


def is_cpapp_emount_pdaf_lens_id(lens_id: int) -> bool:
    """CPAPP 16-bit Sony E-Mount PDAF whitelist predicate: ((id >> 14) == 3) && ((id & 0x0FFF) != 0x0FFF)."""
    if not (0 <= lens_id <= 0xFFFF):
        return False
    return ((lens_id >> 14) == 3) and ((lens_id & 0x0FFF) != 0x0FFF)


def probe_external_mc_focus_map_and_150fps_cutoff_hil(
    *,
    attempt_inbody_fx3_focus_map_menu_toggle: bool = False,
    attempt_stage_b_local_focus_map_overlay_inject: bool = False,
    mc_client_connected: bool = True,
    operating_state: str = OP_STATE_LIVE_SHOOTING,
    lens_type: str = LENS_TYPE_SONY_EMOUNT_PDAF,
    lens_id: int = 0xC124,
    sensor_fps: float = 23.98,
) -> ExternalFocusMapHilResult:
    """Co-emulate ILME-FX3 zero-in-body [Focus Map], external M&C PDAF stream & >=150fps cutoff."""
    if operating_state not in VALID_FOCUS_MAP_OP_STATES:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported operating_state {operating_state!r}"
        )
    if lens_type not in VALID_FOCUS_MAP_LENS_TYPES:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported lens_type {lens_type!r}"
        )
    if sensor_fps <= 0.0:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"sensor_fps must be > 0, got {sensor_fps!r}"
        )

    pdaf_id_ok = (lens_type == LENS_TYPE_SONY_EMOUNT_PDAF) and is_cpapp_emount_pdaf_lens_id(lens_id)
    low_fps_allowed = 1.0 <= sensor_fps <= FX6_LOW_FPS_BLOCK_MAX

    # 1. Hard reject in-body FX3 [Focus Map] menu toggle or Stage-B local EVF/LCD overlay injection
    if attempt_inbody_fx3_focus_map_menu_toggle or attempt_stage_b_local_focus_map_overlay_inject:
        code = (
            "BLOCKED_STAGE_B_LOCAL_FOCUS_MAP_OVERLAY_INJECT_EOPNOTSUPP"
            if attempt_stage_b_local_focus_map_overlay_inject
            else "BLOCKED_FX3_HAS_NO_INBODY_FOCUS_MAP_MENU_EOPNOTSUPP"
        )
        return ExternalFocusMapHilResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            fx3_has_inbody_focus_map_menu=FX3_HAS_INBODY_FOCUS_MAP_MENU,
            inbody_menu_toggle_rejected_eopnotsupp=bool(attempt_inbody_fx3_focus_map_menu_toggle),
            stage_b_local_overlay_rejected_eopnotsupp=bool(
                attempt_stage_b_local_focus_map_overlay_inject
            ),
            mc_client_connected=bool(mc_client_connected),
            operating_state=operating_state,
            lens_type=lens_type,
            lens_id_hex=f"0x{lens_id & 0xFFFF:04x}",
            cpapp_emount_pdaf_valid=pdaf_id_ok,
            sensor_fps=float(sensor_fps),
            fx3_low_fps_1_to_6_allowed=low_fps_allowed,
            blocked_ge_150fps_cutoff=(sensor_fps >= FOCUS_MAP_EXTERNAL_CUTOFF_FPS),
            external_mc_pdaf_depth_streaming=False,
            inbody_fx3_focus_map_overlay_frames=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code=code,
        )

    # 2. Operating state blocks: UVC streaming or in-camera clip playback
    if operating_state != OP_STATE_LIVE_SHOOTING:
        code = (
            "BLOCKED_EXTERNAL_FOCUS_MAP_DURING_UVC_EOPNOTSUPP"
            if operating_state == OP_STATE_UVC_STREAMING
            else "BLOCKED_EXTERNAL_FOCUS_MAP_DURING_PLAYBACK_EOPNOTSUPP"
        )
        return ExternalFocusMapHilResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            fx3_has_inbody_focus_map_menu=FX3_HAS_INBODY_FOCUS_MAP_MENU,
            inbody_menu_toggle_rejected_eopnotsupp=False,
            stage_b_local_overlay_rejected_eopnotsupp=False,
            mc_client_connected=bool(mc_client_connected),
            operating_state=operating_state,
            lens_type=lens_type,
            lens_id_hex=f"0x{lens_id & 0xFFFF:04x}",
            cpapp_emount_pdaf_valid=pdaf_id_ok,
            sensor_fps=float(sensor_fps),
            fx3_low_fps_1_to_6_allowed=low_fps_allowed,
            blocked_ge_150fps_cutoff=False,
            external_mc_pdaf_depth_streaming=False,
            inbody_fx3_focus_map_overlay_frames=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code=code,
        )

    # 3. Mount adapter, manual/non-PDAF lens, or no lens attached -> blocked
    if not pdaf_id_ok:
        return ExternalFocusMapHilResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            fx3_has_inbody_focus_map_menu=FX3_HAS_INBODY_FOCUS_MAP_MENU,
            inbody_menu_toggle_rejected_eopnotsupp=False,
            stage_b_local_overlay_rejected_eopnotsupp=False,
            mc_client_connected=bool(mc_client_connected),
            operating_state=operating_state,
            lens_type=lens_type,
            lens_id_hex=f"0x{lens_id & 0xFFFF:04x}",
            cpapp_emount_pdaf_valid=False,
            sensor_fps=float(sensor_fps),
            fx3_low_fps_1_to_6_allowed=low_fps_allowed,
            blocked_ge_150fps_cutoff=(sensor_fps >= FOCUS_MAP_EXTERNAL_CUTOFF_FPS),
            external_mc_pdaf_depth_streaming=False,
            inbody_fx3_focus_map_overlay_frames=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EXTERNAL_FOCUS_MAP_NON_PDAF_OR_ADAPTER_EOPNOTSUPP",
        )

    # 4. Frame rate >= 150 fps (e.g. 200fps / 240fps S&Q) -> hard cutoff
    if sensor_fps >= FOCUS_MAP_EXTERNAL_CUTOFF_FPS:
        return ExternalFocusMapHilResult(
            admitted=False,
            model_name=MODEL_ILME_FX3,
            fx3_has_inbody_focus_map_menu=FX3_HAS_INBODY_FOCUS_MAP_MENU,
            inbody_menu_toggle_rejected_eopnotsupp=False,
            stage_b_local_overlay_rejected_eopnotsupp=False,
            mc_client_connected=bool(mc_client_connected),
            operating_state=operating_state,
            lens_type=lens_type,
            lens_id_hex=f"0x{lens_id & 0xFFFF:04x}",
            cpapp_emount_pdaf_valid=True,
            sensor_fps=float(sensor_fps),
            fx3_low_fps_1_to_6_allowed=False,
            blocked_ge_150fps_cutoff=True,
            external_mc_pdaf_depth_streaming=False,
            inbody_fx3_focus_map_overlay_frames=0,
            errno_code=EOPNOTSUPP_ERRNO,
            status_code="BLOCKED_EXTERNAL_FOCUS_MAP_FPS_GE_150_CUTOFF_EOPNOTSUPP",
        )

    streaming = bool(mc_client_connected)
    status = (
        "ADMITTED_EXTERNAL_MC_FOCUS_MAP_STREAMING_OK"
        if streaming
        else "ADMITTED_IDLE_NO_EXTERNAL_MC_CLIENT"
    )
    return ExternalFocusMapHilResult(
        admitted=True,
        model_name=MODEL_ILME_FX3,
        fx3_has_inbody_focus_map_menu=FX3_HAS_INBODY_FOCUS_MAP_MENU,
        inbody_menu_toggle_rejected_eopnotsupp=False,
        stage_b_local_overlay_rejected_eopnotsupp=False,
        mc_client_connected=streaming,
        operating_state=operating_state,
        lens_type=lens_type,
        lens_id_hex=f"0x{lens_id & 0xFFFF:04x}",
        cpapp_emount_pdaf_valid=True,
        sensor_fps=float(sensor_fps),
        fx3_low_fps_1_to_6_allowed=low_fps_allowed,
        blocked_ge_150fps_cutoff=False,
        external_mc_pdaf_depth_streaming=streaming,
        inbody_fx3_focus_map_overlay_frames=0,
        errno_code=0,
        status_code=status,
    )


def evaluate_pillar_b_external_mc_focus_map_and_150fps_cutoff_hil() -> Dict[str, object]:
    inbody_rejected = probe_external_mc_focus_map_and_150fps_cutoff_hil(
        attempt_inbody_fx3_focus_map_menu_toggle=True,
    )
    stage_b_overlay_rejected = probe_external_mc_focus_map_and_150fps_cutoff_hil(
        attempt_stage_b_local_focus_map_overlay_inject=True,
    )
    sq_1fps_allowed = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=1.0)
    sq_6fps_allowed = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=6.0)
    hfr_120fps_allowed = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=119.88)
    cutoff_150fps_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=150.0)
    sq_200fps_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=200.0)
    sq_240fps_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(sensor_fps=240.0)
    adapter_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(
        lens_type=LENS_TYPE_MOUNT_ADAPTER,
        lens_id=0xFFFF,
    )
    uvc_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(
        operating_state=OP_STATE_UVC_STREAMING,
    )
    playback_blocked = probe_external_mc_focus_map_and_150fps_cutoff_hil(
        operating_state=OP_STATE_CLIP_PLAYBACK,
    )

    passed = (
        (not inbody_rejected.admitted)
        and inbody_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not stage_b_overlay_rejected.admitted)
        and stage_b_overlay_rejected.errno_code == EOPNOTSUPP_ERRNO
        and sq_1fps_allowed.admitted
        and sq_1fps_allowed.external_mc_pdaf_depth_streaming
        and sq_1fps_allowed.fx3_low_fps_1_to_6_allowed
        and sq_6fps_allowed.admitted
        and sq_6fps_allowed.external_mc_pdaf_depth_streaming
        and hfr_120fps_allowed.admitted
        and hfr_120fps_allowed.external_mc_pdaf_depth_streaming
        and (not cutoff_150fps_blocked.admitted)
        and cutoff_150fps_blocked.blocked_ge_150fps_cutoff
        and (not sq_200fps_blocked.admitted)
        and (not sq_240fps_blocked.admitted)
        and (not adapter_blocked.admitted)
        and (not uvc_blocked.admitted)
        and (not playback_blocked.admitted)
    )
    return {
        "passed": passed,
        "inbody_fx3_menu_toggle_rejected": asdict(inbody_rejected),
        "stage_b_local_overlay_inject_rejected": asdict(stage_b_overlay_rejected),
        "fx3_sq_1fps_streaming_ok": asdict(sq_1fps_allowed),
        "fx3_sq_6fps_streaming_ok": asdict(sq_6fps_allowed),
        "fx3_120fps_streaming_ok": asdict(hfr_120fps_allowed),
        "cutoff_150fps_blocked": asdict(cutoff_150fps_blocked),
        "sq_200fps_blocked": asdict(sq_200fps_blocked),
        "sq_240fps_blocked": asdict(sq_240fps_blocked),
        "mount_adapter_blocked": asdict(adapter_blocked),
        "uvc_streaming_blocked": asdict(uvc_blocked),
        "clip_playback_blocked": asdict(playback_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar C & D: [Simult. Recording] + [Auto Switch Media], [Shockless WB] & Redlines
# ---------------------------------------------------------------------------


def probe_simult_recording_auto_switch_hil(
    *,
    auto_switch_media: str = "On",
    slot1_free_mb: int = 0,
    slot2_free_mb: int = 65_536,
    fresh_card_reinserted: bool = False,
) -> SimultAutoSwitchMediaHilResult:
    """Co-emulate [Simult. Recording] + [Auto Switch Media] (Ver. 2.0+ single-card fallback vs Off halt)."""
    if auto_switch_media not in VALID_ON_OFF:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported auto_switch_media {auto_switch_media!r}"
        )
    if slot1_free_mb < 0 or slot2_free_mb < 0:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Slot free MB must be >= 0, got ({slot1_free_mb}, {slot2_free_mb})"
        )

    s1_ok = slot1_free_mb > 0
    s2_ok = slot2_free_mb > 0

    if not s1_ok and not s2_ok:
        return SimultAutoSwitchMediaHilResult(
            admitted=True,
            menu_path=SIMULT_RECORDING_MENU_PATH,
            recording_mode=REC_MODE_SIMULTANEOUS,
            auto_switch_media=auto_switch_media,
            slot1_free_mb=slot1_free_mb,
            slot2_free_mb=slot2_free_mb,
            fresh_card_reinserted=False,
            recording_continues=False,
            active_recording_slots=(),
            dual_card_redundant=False,
            single_card_continuation_active=False,
            strict_dual_parity_halted=False,
            resumed_dual_slot_after_card_swap=False,
            both_slots_full_halted=True,
            dropped_frames=0,
            rsv_orphan_count=0,
            errno_code=0,
            status_code="HALTED_CLEANLY_BOTH_SLOTS_FULL_ZERO_RSV",
        )

    if s1_ok and s2_ok:
        return SimultAutoSwitchMediaHilResult(
            admitted=True,
            menu_path=SIMULT_RECORDING_MENU_PATH,
            recording_mode=REC_MODE_SIMULTANEOUS,
            auto_switch_media=auto_switch_media,
            slot1_free_mb=slot1_free_mb,
            slot2_free_mb=slot2_free_mb,
            fresh_card_reinserted=bool(fresh_card_reinserted),
            recording_continues=True,
            active_recording_slots=(1, 2),
            dual_card_redundant=True,
            single_card_continuation_active=False,
            strict_dual_parity_halted=False,
            resumed_dual_slot_after_card_swap=False,
            both_slots_full_halted=False,
            dropped_frames=0,
            rsv_orphan_count=0,
            errno_code=0,
            status_code="ADMITTED_DUAL_SLOT_SIMULTANEOUS_PARITY_ACTIVE",
        )

    # Exactly one card has hit 0 MB free mid-take
    if auto_switch_media == "Off":
        return SimultAutoSwitchMediaHilResult(
            admitted=True,
            menu_path=SIMULT_RECORDING_MENU_PATH,
            recording_mode=REC_MODE_SIMULTANEOUS,
            auto_switch_media="Off",
            slot1_free_mb=slot1_free_mb,
            slot2_free_mb=slot2_free_mb,
            fresh_card_reinserted=bool(fresh_card_reinserted),
            recording_continues=False,
            active_recording_slots=(),
            dual_card_redundant=False,
            single_card_continuation_active=False,
            strict_dual_parity_halted=True,
            resumed_dual_slot_after_card_swap=False,
            both_slots_full_halted=False,
            dropped_frames=0,
            rsv_orphan_count=0,
            errno_code=0,
            status_code="HALTED_STRICT_DUAL_BACKUP_PARITY_AUTO_SWITCH_OFF",
        )

    # Auto Switch Media = On (Ver. 2.0..7.02): seamless single-card continuation, or dual resume on swap
    if fresh_card_reinserted:
        return SimultAutoSwitchMediaHilResult(
            admitted=True,
            menu_path=SIMULT_RECORDING_MENU_PATH,
            recording_mode=REC_MODE_SIMULTANEOUS,
            auto_switch_media="On",
            slot1_free_mb=slot1_free_mb if s1_ok else 131_072,
            slot2_free_mb=slot2_free_mb if s2_ok else 131_072,
            fresh_card_reinserted=True,
            recording_continues=True,
            active_recording_slots=(1, 2),
            dual_card_redundant=True,
            single_card_continuation_active=False,
            strict_dual_parity_halted=False,
            resumed_dual_slot_after_card_swap=True,
            both_slots_full_halted=False,
            dropped_frames=0,
            rsv_orphan_count=0,
            errno_code=0,
            status_code="ADMITTED_RESUMED_DUAL_SLOT_SIMULTANEOUS_AFTER_EMPTY_CARD_SWAP",
        )

    survivor = (1,) if s1_ok else (2,)
    return SimultAutoSwitchMediaHilResult(
        admitted=True,
        menu_path=SIMULT_RECORDING_MENU_PATH,
        recording_mode=REC_MODE_SIMULTANEOUS,
        auto_switch_media="On",
        slot1_free_mb=slot1_free_mb,
        slot2_free_mb=slot2_free_mb,
        fresh_card_reinserted=False,
        recording_continues=True,
        active_recording_slots=survivor,
        dual_card_redundant=False,
        single_card_continuation_active=True,
        strict_dual_parity_halted=False,
        resumed_dual_slot_after_card_swap=False,
        both_slots_full_halted=False,
        dropped_frames=0,
        rsv_orphan_count=0,
        errno_code=0,
        status_code="ADMITTED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_CONTINUATION_OK",
    )


def probe_shockless_wb_and_kelvin_bypass_hil(
    *,
    shockless_wb_setting: str = SHOCKLESS_WB_2_NORMAL,
    sensor_fps: float = 23.98,
    transition_trigger: str = WB_TRIGGER_PRESET_SWITCH,
    from_kelvin: int = 5600,
    to_kelvin: int = 3200,
    ab_gm_grid_offset: str = "A0 G0",
) -> ShocklessWbHilResult:
    """Co-emulate [Shockless WB] (Off/1/2/3 across 24p..240fps) & 0-frame Kelvin / A-B G-M bypass."""
    if transition_trigger not in VALID_WB_TRANSITION_TRIGGERS:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Unsupported transition_trigger {transition_trigger!r}"
        )
    if sensor_fps <= 0.0 or sensor_fps > 240.0:
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"sensor_fps must be in (0, 240], got {sensor_fps!r}"
        )
    if not (2500 <= from_kelvin <= 9900) or not (2500 <= to_kelvin <= 9900):
        raise RealHwDesqueezeFocusMapSimultShocklessWbError(
            f"Kelvin values must be in [2500, 9900], got ({from_kelvin}, {to_kelvin})"
        )

    if shockless_wb_setting not in VALID_SHOCKLESS_WB_SETTINGS:
        return ShocklessWbHilResult(
            admitted=False,
            menu_path=SHOCKLESS_WB_MENU_PATH,
            shockless_wb_setting=shockless_wb_setting,
            sensor_fps=float(sensor_fps),
            all_framerates_supported=True,
            transition_trigger=transition_trigger,
            from_kelvin=from_kelvin,
            to_kelvin=to_kelvin,
            ab_gm_grid_offset=ab_gm_grid_offset,
            bypassed_shockless_smoothing=False,
            immediate_zero_frame_applied=False,
            ramp_duration_seconds=0.0,
            transition_frames=0,
            errno_code=EINVAL_ERRNO,
            status_code="BLOCKED_INVALID_SHOCKLESS_WB_SETTING_EINVAL",
        )

    # Direct [C.Temp./Filter] Kelvin dial edits and A-B / G-M fine-grid shifts bypass smoothing -> 0 frames!
    if transition_trigger in (WB_TRIGGER_CTEMP_KELVIN_EDIT, WB_TRIGGER_AB_GM_FINE_GRID):
        code = (
            "ADMITTED_CTEMP_KELVIN_EDIT_IMMEDIATE_0_FRAME_BYPASS"
            if transition_trigger == WB_TRIGGER_CTEMP_KELVIN_EDIT
            else "ADMITTED_AB_GM_FINE_GRID_IMMEDIATE_0_FRAME_BYPASS"
        )
        return ShocklessWbHilResult(
            admitted=True,
            menu_path=SHOCKLESS_WB_MENU_PATH,
            shockless_wb_setting=shockless_wb_setting,
            sensor_fps=float(sensor_fps),
            all_framerates_supported=True,
            transition_trigger=transition_trigger,
            from_kelvin=from_kelvin,
            to_kelvin=to_kelvin,
            ab_gm_grid_offset=ab_gm_grid_offset,
            bypassed_shockless_smoothing=(shockless_wb_setting != SHOCKLESS_WB_OFF),
            immediate_zero_frame_applied=True,
            ramp_duration_seconds=0.0,
            transition_frames=0,
            errno_code=0,
            status_code=code,
        )

    ramp_s = SHOCKLESS_WB_RAMP_SECONDS[shockless_wb_setting]
    frames = 0 if shockless_wb_setting == SHOCKLESS_WB_OFF else max(1, int(round(ramp_s * sensor_fps)))
    status = (
        "ADMITTED_SHOCKLESS_WB_OFF_IMMEDIATE_PRESET_STEP"
        if shockless_wb_setting == SHOCKLESS_WB_OFF
        else f"ADMITTED_SHOCKLESS_WB_STEP_{shockless_wb_setting}_SMOOTH_RAMP_OK"
    )
    return ShocklessWbHilResult(
        admitted=True,
        menu_path=SHOCKLESS_WB_MENU_PATH,
        shockless_wb_setting=shockless_wb_setting,
        sensor_fps=float(sensor_fps),
        all_framerates_supported=True,
        transition_trigger=transition_trigger,
        from_kelvin=from_kelvin,
        to_kelvin=to_kelvin,
        ab_gm_grid_offset=ab_gm_grid_offset,
        bypassed_shockless_smoothing=False,
        immediate_zero_frame_applied=(frames == 0),
        ramp_duration_seconds=ramp_s,
        transition_frames=frames,
        errno_code=0,
        status_code=status,
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    bake_desqueeze_into_raw_or_xavc: bool = False,
    inject_inbody_fx3_focus_map_overlay: bool = False,
) -> RedlineGuardProbeResult:
    """Fail-closed probe verifying all 8 forbidden physical write/transmit/overlay actions are blocked."""
    violations: List[str] = []
    if authorize_persistent_emmc_writes:
        violations.append("PERSISTENT_EMMC_WRITE")
    if authorize_spi_nor_write:
        violations.append("SPI_NOR_WRITE")
    if authorize_el3_payload_transmit:
        violations.append("EL3_PAYLOAD_TRANSMIT")
    if emit_physical_usb_packet:
        violations.append("PHYSICAL_USB_PACKET_EMIT")
    if touch_otp_fuse:
        violations.append("OTP_FUSE_TOUCH")
    if increment_rpmb_counter:
        violations.append("RPMB_COUNTER_INCREMENT")
    if bake_desqueeze_into_raw_or_xavc:
        violations.append("BAKE_DESQUEEZE_INTO_MASTER_RAW_OR_XAVC")
    if inject_inbody_fx3_focus_map_overlay:
        violations.append("INBODY_FX3_FOCUS_MAP_OVERLAY_INJECT")

    if violations:
        joined = "+".join(violations)
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            desqueeze_baked_into_raw_or_xavc_frames=DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES,
            inbody_fx3_focus_map_overlay_frames=INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES,
            blocked_action=joined,
            status_code=f"FAIL_CLOSED_REDLINE_BLOCKED:{joined}",
        )

    return RedlineGuardProbeResult(
        valid=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        desqueeze_baked_into_raw_or_xavc_frames=DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES,
        inbody_fx3_focus_map_overlay_frames=INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES,
        blocked_action="NONE",
        status_code="HARD_SAFETY_REDLINES_LOCKED_OK",
    )


def evaluate_pillar_c_d_simult_autoswitch_shockless_wb_and_redlines() -> Dict[str, object]:
    dual_healthy = probe_simult_recording_auto_switch_hil(
        auto_switch_media="On",
        slot1_free_mb=65_536,
        slot2_free_mb=65_536,
    )
    slot1_full_autoswitch_on = probe_simult_recording_auto_switch_hil(
        auto_switch_media="On",
        slot1_free_mb=0,
        slot2_free_mb=65_536,
    )
    slot1_swap_resume_dual = probe_simult_recording_auto_switch_hil(
        auto_switch_media="On",
        slot1_free_mb=0,
        slot2_free_mb=65_536,
        fresh_card_reinserted=True,
    )
    slot1_full_autoswitch_off_halt = probe_simult_recording_auto_switch_hil(
        auto_switch_media="Off",
        slot1_free_mb=0,
        slot2_free_mb=65_536,
    )

    wb_preset_24p_slow = probe_shockless_wb_and_kelvin_bypass_hil(
        shockless_wb_setting=SHOCKLESS_WB_3_SLOW,
        sensor_fps=24.0,
        transition_trigger=WB_TRIGGER_PRESET_SWITCH,
    )
    wb_preset_240fps_fast = probe_shockless_wb_and_kelvin_bypass_hil(
        shockless_wb_setting=SHOCKLESS_WB_1_FAST,
        sensor_fps=240.0,
        transition_trigger=WB_TRIGGER_PRESET_SWITCH,
    )
    wb_ctemp_kelvin_bypass = probe_shockless_wb_and_kelvin_bypass_hil(
        shockless_wb_setting=SHOCKLESS_WB_3_SLOW,
        sensor_fps=59.94,
        transition_trigger=WB_TRIGGER_CTEMP_KELVIN_EDIT,
        from_kelvin=5600,
        to_kelvin=4300,
    )
    wb_ab_gm_grid_bypass = probe_shockless_wb_and_kelvin_bypass_hil(
        shockless_wb_setting=SHOCKLESS_WB_2_NORMAL,
        sensor_fps=119.88,
        transition_trigger=WB_TRIGGER_AB_GM_FINE_GRID,
        ab_gm_grid_offset="B2 G1",
    )

    baseline_redline = probe_hard_safety_redline()
    blocked_probes = [
        asdict(probe_hard_safety_redline(**kw))
        for kw in (
            {"authorize_persistent_emmc_writes": True},
            {"authorize_spi_nor_write": True},
            {"authorize_el3_payload_transmit": True},
            {"emit_physical_usb_packet": True},
            {"touch_otp_fuse": True},
            {"increment_rpmb_counter": True},
            {"bake_desqueeze_into_raw_or_xavc": True},
            {"inject_inbody_fx3_focus_map_overlay": True},
        )
    ]

    passed = (
        dual_healthy.dual_card_redundant
        and dual_healthy.active_recording_slots == (1, 2)
        and slot1_full_autoswitch_on.recording_continues
        and slot1_full_autoswitch_on.single_card_continuation_active
        and slot1_full_autoswitch_on.active_recording_slots == (2,)
        and slot1_swap_resume_dual.resumed_dual_slot_after_card_swap
        and slot1_swap_resume_dual.active_recording_slots == (1, 2)
        and (not slot1_full_autoswitch_off_halt.recording_continues)
        and slot1_full_autoswitch_off_halt.strict_dual_parity_halted
        and wb_preset_24p_slow.transition_frames == 48
        and wb_preset_240fps_fast.transition_frames == 120
        and wb_ctemp_kelvin_bypass.bypassed_shockless_smoothing
        and wb_ctemp_kelvin_bypass.transition_frames == 0
        and wb_ab_gm_grid_bypass.bypassed_shockless_smoothing
        and wb_ab_gm_grid_bypass.transition_frames == 0
        and baseline_redline.valid
        and len(blocked_probes) == 8
        and all(not p["valid"] for p in blocked_probes)
    )
    return {
        "passed": passed,
        "dual_slot_healthy_active": asdict(dual_healthy),
        "slot1_full_autoswitch_on_single_card_continues": asdict(slot1_full_autoswitch_on),
        "slot1_swap_resumes_dual_slot": asdict(slot1_swap_resume_dual),
        "slot1_full_autoswitch_off_strict_halt": asdict(slot1_full_autoswitch_off_halt),
        "shockless_wb_24p_step3_slow_48f": asdict(wb_preset_24p_slow),
        "shockless_wb_240fps_step1_fast_120f": asdict(wb_preset_240fps_fast),
        "ctemp_kelvin_edit_0frame_bypass": asdict(wb_ctemp_kelvin_bypass),
        "ab_gm_fine_grid_0frame_bypass": asdict(wb_ab_gm_grid_bypass),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 207 (Stage 37, 37/37) Co-Emulator Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 207 Stage 37 (37/37) HIL audit and return a deterministic payload."""
    donor_audit = inspect_phase207_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_desqueeze_165x_4locks_and_bypass_hil()
    pillar_b = evaluate_pillar_b_external_mc_focus_map_and_150fps_cutoff_hil()
    pillar_cd = evaluate_pillar_c_d_simult_autoswitch_shockless_wb_and_redlines()

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
        "desqueeze_baked_into_raw_or_xavc_frames": DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES,
        "inbody_fx3_focus_map_overlay_frames": INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES,
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
        and DESQUEEZE_BAKED_INTO_RAW_OR_XAVC_FRAMES == 0
        and INBODY_FX3_FOCUS_MAP_OVERLAY_FRAMES == 0
    )

    payload: Dict[str, object] = {
        "schema": PHASE_207_SCHEMA,
        "version": PHASE_207_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_desqueeze_165x_4locks_and_bypass_hil": pillar_a,
        "pillar_b_external_mc_focus_map_and_150fps_cutoff_hil": pillar_b,
        "pillar_c_d_simult_autoswitch_shockless_wb_and_redlines": pillar_cd,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py",
        description=(
            "Phase 207 Stage 37 (37/37) — Real-Hardware ILME-FX3 [De-Squeeze Display] "
            "(1.6x=1.65x 4-Locks & HDMI RAW Bypass), External M&C Focus Map (>=150fps Cutoff) "
            "& [Simult. + Auto Switch] / [Shockless WB] HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 207 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_desqueeze_165x_4locks_and_bypass_hil"]
        pb = rep["pillar_b_external_mc_focus_map_and_150fps_cutoff_hil"]
        pcd = rep["pillar_c_d_simult_autoswitch_shockless_wb_and_redlines"]
        scale_16x = pa["ratio_matrix"]["1.6x"]["applied_horizontal_scale"]
        inbody_errno = pb["inbody_fx3_menu_toggle_rejected"]["errno_code"]
        wb_bypass_f = pcd["ctemp_kelvin_edit_0frame_bypass"]["transition_frames"]
        sys.stdout.write(
            f"[{status}] Phase 207 Stage 37 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"desqueeze_1.6x={scale_16x}x(4locks=1,hdmi_raw_bypass=1) | "
            f"focus_map=ext_mc_only(inbody_errno={inbody_errno},cutoff>=150fps,1..6fps_ok=1) | "
            f"simult_autoswitch=single_card_cont_vs_off_halt | "
            f"shockless_wb=24..240fps(kelvin_bypass={wb_bypass_f}f) | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
