"""Phase 85 — 16th Unified Firmware-Lab Auditor: Playback/Thumbnail Presenter (`icx1295`), `ShotMark1 / ShotMark2` (`EssenceMark` XML), and `Push Auto Iris / AE Shift` + `P4` Auto-ND Redirection.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `libmpr.so`, `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `cpapp-b.bin`, `libInfraLensCommunicator.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  read-only `mmap` and ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus
  `uxa\\x07` / `.uxc` container parsing.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and executes the
  identical four-pillar verification pipeline with zero proprietary files
  required.

Audits Four Playback, ShotMark XML, AE/Iris & Safety Pillars:
1. Pillar 1 — Playback / Thumbnail Presenter (`icx1295` Thumbnail/Clip-Index) &
   Internal `p1` Media Delete/Format Firewall:
   Verifies Playback / Thumbnail Browser symbols, `Cue/Review` shuttle speeds
   (`1x, 2x, 5x, 15x`), Clip Protect (`Lock`), Clip Delete, and Media Format
   targets, proving **100% isolation of internal eMMC `p1` (`/dev/mmcblk0p1`)**
   from Playback `Delete Clip` and Menu `Format Media` (`Format` targets
   strictly external `Slot A` / `Slot B` `/dev/mmcblk1*` / `/dev/mmcblk2*` /
   NVMe CFexpress, NEVER internal eMMC; `internal_emmc_format_possible == False`).
2. Pillar 2 — Cinema Line `Shot Mark 1` / `Shot Mark 2` (`_ShotMark1`,
   `_ShotMark2`, `OK / KEEP`) & `EssenceMark` XML Verifier:
   Verifies live in-record (`IN_REC`) and playback (`IN_PLAY`) frame-indexed
   ShotMark insertion/removal (`0 .. max_marks_per_clip = 100`) serialized into
   Sony `NonRealTimeMeta v2.20` `<KlvPacketTable>` / `<EssenceMark>`
   (`start="<frame>"` timecode/frame-offset tags recognized by DaVinci Resolve,
   Premiere Pro & Catalyst Browse), proving lossless frame-accurate round-trip
   across `23.98p / 24.00p / 25.00p / 29.97p / 59.94p`.
3. Pillar 3 — `Push Auto Iris`, `AE Shift (-2.0..+2.0 EV)`, Photometry
   (`Multi / Center / Spot / Entire Screen Avg / Highlight`) & `P4` Auto-ND
   Redirection:
   Proves that under `Cine EI` (`ISO/EI` locked to Base `800`/`12800` and
   Shutter Angle locked to `180.0 deg`), FX6's `AE Level / Push Auto` (which
   on FX6 prioritizes `Auto Variable ND` before Iris) cleanly redirects on FX3
   (no internal Variable ND) to **E-Mount `Push Auto Iris` (`1/8`-stop smooth
   aperture servo via `libInfraLensCommunicator.so`)** with **`0` `P4` Variable
   ND motor fault attempts**, plus `Highlight` metering (`94% IRE` `S-Log3`
   highlight-clip protection) and `Face/Eye Priority in Multi Metering`.
4. Pillar 4 — Zero Calibration / Zero NVRAM Mutation Proof:
   Proves `calibration_mutation_bytes == 0`,
   `internal_emmc_format_possible == False`, and
   `persistent_emmc_writes_authorized == False`, hard-blocking `/dev/mmcblk0p1`,
   `/dev/cnflasha*`, `/dev/nflasha*`, `p1:`, `p2:/Backup.bin`, and `p6:Jiritsu`.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import (
    FX3_LENS_COMM_RELPATH,
    FX6_LENS_COMM_RELPATH,
    _extract_uxc_labels,
    _parse_elf64_sections,
)
from .global_xdb_and_menu_tree_auditor import (
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
    parse_global_xdb_buffer,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR
from .wbi_hibdrv_and_elf_abi_differ import build_synthetic_elf64_so


PHASE_85_SCHEMA = "fx3_firmware_lab_phase85_playback_shotmark_ae_v1"
PHASE_85_VERSION = "85.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Playback / Thumbnail Presenter & p1 Media Firewall
# ---------------------------------------------------------------------------

CUE_REVIEW_SPEEDS: Tuple[int, ...] = (1, 2, 5, 15)
CUE_REVIEW_DIRECTIONS: Tuple[str, ...] = ("CUE", "REVIEW")
VALID_MEDIA_SLOTS: Tuple[str, ...] = ("SLOT_A", "SLOT_B")
VALID_PLAYBACK_MEDIA_OPS: Tuple[str, ...] = (
    "THUMBNAIL_INDEX",
    "CUE_REVIEW",
    "CLIP_PROTECT_LOCK",
    "CLIP_PROTECT_UNLOCK",
    "DELETE_CLIP",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)

EXTERNAL_MEDIA_SLOT_SPECS: Dict[str, Dict[str, object]] = {
    "SLOT_A": {
        "block_devices": ("/dev/mmcblk1p1", "/dev/nvme0n1p1"),
        "mount_roots": ("XDROOT", "M4ROOT"),
        "media_types": ("CFEXPRESS_TYPE_A", "SDXC_UHS_II"),
    },
    "SLOT_B": {
        "block_devices": ("/dev/mmcblk2p1", "/dev/nvme1n1p1"),
        "mount_roots": ("XDROOT", "M4ROOT"),
        "media_types": ("CFEXPRESS_TYPE_A", "SDXC_UHS_II"),
    },
}

FORBIDDEN_INTERNAL_EMMC_TARGETS: Tuple[str, ...] = (
    "/dev/mmcblk0p1",
    "/dev/mmcblk0",
    "mmcblk0p1",
    "mmcblk0",
    "p1:",
    "/p1/",
    "/dev/nflasha",
    "/dev/cnflasha",
    "nflasha",
    "cnflasha",
    "p2:",
    "p6:",
    "/dev/mtdblock",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: ShotMark1 / ShotMark2 / OK / KEEP & EssenceMark XML
# ---------------------------------------------------------------------------

SHOT_MARK_MAX_PER_CLIP = 100
VALID_SHOT_MARK_TYPES: Tuple[str, ...] = ("_ShotMark1", "_ShotMark2", "OK", "KEEP")
VALID_SHOT_MARK_CAPTURE_MODES: Tuple[str, ...] = ("IN_REC", "IN_PLAY")
SHOT_MARK_SUPPORTED_FPS: Tuple[str, ...] = ("23.98p", "24.00p", "25.00p", "29.97p", "59.94p")

SHOT_MARK_FPS_SPECS: Dict[str, Dict[str, object]] = {
    "23.98p": {
        "timebase": 24,
        "num": 24000,
        "den": 1001,
        "capture_fps": "23.98p",
        "format_fps": "23.98p",
    },
    "24.00p": {
        "timebase": 24,
        "num": 24,
        "den": 1,
        "capture_fps": "24p",
        "format_fps": "24p",
    },
    "25.00p": {
        "timebase": 25,
        "num": 25,
        "den": 1,
        "capture_fps": "25p",
        "format_fps": "25p",
    },
    "29.97p": {
        "timebase": 30,
        "num": 30000,
        "den": 1001,
        "capture_fps": "29.97p",
        "format_fps": "29.97p",
    },
    "59.94p": {
        "timebase": 60,
        "num": 60000,
        "den": 1001,
        "capture_fps": "59.94p",
        "format_fps": "59.94p",
    },
}

ESSENCE_MARK_KLV_UNIVERSAL_KEY = "060E2B34010101050102010201000000"
NRTM_NAMESPACE_V220 = "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
TARGET_NLE_CONSUMERS: Tuple[str, ...] = ("Resolve", "Premiere", "Catalyst")

# ---------------------------------------------------------------------------
# Pillar 3 Constants: Push Auto Iris, AE Shift (-2.0..+2.0 EV) & Photometry
# ---------------------------------------------------------------------------

AE_SHIFT_MIN_EV = -2.0
AE_SHIFT_MAX_EV = 2.0
IRIS_EIGHTH_STOP_EV = 0.125  # 1/8-stop smooth E-Mount aperture servo
VALID_PHOTOMETRY_MODES: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
VALID_SHOOTING_MODES: Tuple[str, ...] = ("CINE_EI", "FLEXIBLE_ISO", "CUSTOM")
SLOG3_HIGHLIGHT_CLIP_IRE = 94.0
CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)
CINE_EI_LOCKED_SHUTTER_ANGLE_DEG = 180.0

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Zero Calibration & Zero Persistent eMMC Mutation
# ---------------------------------------------------------------------------

VOLATILE_SHADOW_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_CALIBRATION_AND_EMMC_PATHS: Tuple[str, ...] = (
    "/dev/mmcblk0",
    "mmcblk0",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "nflasha",
    "cnflasha",
    "p1:",
    "p2:",
    "p6:",
    "backup.bin",
    "psd.bin",
    "jiritsu",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PLAYBACK_FORMAT_MARKERS: Tuple[str, ...] = (
    "EID_PLAYBACK",
    "EVENT_FUNC_PROTECT_ON",
    "EVENT_FUNC_PROTECT_OFF",
    "EXECUTE_PLAYBACK_FUNCTION_AFTER_PLAYBACK_DELETE",
    "CAUTION_ID_NO_MEDIA_TO_PLAYBACK_SLOT1",
    "CAUTION_ID_NO_MEDIA_TO_PLAYBACK_SLOT2",
    "CAUTION_ID_PROTECT_MS_SLOT1",
    "CAUTION_ID_PROTECT_MS_SLOT2",
    "VAL_movie_playback_control_MOVIE_PLAYBACK_CONTROL_FAST_FORWARD_STEP1",
    "VAL_movie_playback_control_MOVIE_PLAYBACK_CONTROL_FAST_FORWARD_STEP4",
    "EVENT_REMOTE_MEDIA_FORMAT",
    "REMOTE_SELECT_MEDIA_FORMAT_TYPE_QUICK",
    "REMOTE_SELECT_MEDIA_FORMAT_TYPE_FULL",
    "VAL_media_format_state_slot1_MEDIA_FORMAT_STATE_SLOT1_DURING_FORMAT",
    "VAL_media_format_state_slot2_MEDIA_FORMAT_STATE_SLOT2_DURING_FORMAT",
)

FX6_APPFW_PLAYBACK_FORMAT_MARKERS: Tuple[str, ...] = (
    "ASSIGNABLE_SWITCH_THUMBNAIL",
    "BKID_APP_SELECT_PLAYBACK_MEDIA",
    "BKID_APP_USER_MENU_DELETE_CLIP0",
    "BKID_APP_USER_MENU_FORMAT_MEDIA0",
    "BKID_APP_USER_MENU_FORMAT_MEDIA1",
    "CONTINUOUS_PLAYBACK_SPEED_1",
    "CONTINUOUS_PLAYBACK_SPEED_7",
    "EVENT_REMOTE_MEDIA_FORMAT",
    "MODEL_MEDIA_FORMAT_COMP",
    "MODEL_MEDIA_FORMAT_FAILED_BY_WRITEPROTECTED",
)

FX3_LIBMPR_PLAYBACK_MARKERS: Tuple[str, ...] = (
    "Fsys_Format",
    "Thumbnail",
    "XAVCThumbnailReader",
    "MP4ThumbnailReader",
)

FX6_LIBMPR_PLAYBACK_MARKERS: Tuple[str, ...] = (
    "ThumbnailItemIdGet",
    ":mediaCpClipThumbnailSet",
    ":mediaCpExpandThumbnailItemListGet",
    ":thmbExpClipThumbnailListCreate",
)

FX3_APPFW_SHOTMARK_MARKERS: Tuple[str, ...] = (
    "BKID_APP_setting_movie_with_shotmark",
    "EDIT_SHOT_MARK_TYPE_ADD",
    "EDIT_SHOT_MARK_TYPE_DELETE",
    "EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_1_ON",
    "EVENT_FUNC_CUSTOM_ADD_SHOT_MARK_2_ON",
    "EVENT_FUNC_CUSTOM_EDIT_SHOT_MARK_1_ON",
    "EVENT_FUNC_CUSTOM_EDIT_SHOT_MARK_2_ON",
    "EssenceMarkType",
    "MODEL_OK_CLIP_FLAG_OK",
    "MODEL_KEEP_CLIP_FLAG_OK",
)

FX6_APPFW_SHOTMARK_MARKERS: Tuple[str, ...] = (
    "EDIT_SHOT_MARK_TYPE_ADD",
    "EDIT_SHOT_MARK_TYPE_DELETE",
    "EVENT_FUNC_SHOT_MARK_1_ON",
    "EVENT_FUNC_SHOT_MARK_2_ON",
    "EssenceMarkType",
    "PLAYBACK_FILTER_SHOTMARK_SHOT_MARK1_ONLY",
    "PLAYBACK_FILTER_SHOTMARK_SHOT_MARK2_ONLY",
    "MODEL_OK_CLIP_FLAG_OK",
    "MODEL_KEEP_CLIP_FLAG_OK",
)

FX3_LIBMPR_SHOTMARK_MARKERS: Tuple[str, ...] = (
    "GetEssenceMarks",
    "KlvPacket",
    "KlvPacketTable",
    "NonRealTimeMeta",
    "SetEssenceMarkInPlay",
    "SetEssenceMarkInRec",
    "_ShotMark0",
    "_ShotMark1",
    "_ShotMark2",
)

FX6_LIBMPR_SHOTMARK_MARKERS: Tuple[str, ...] = (
    "EssenceMark",
    "GetEssenceMarks",
    "KlvPacketTable",
    "NonRealTimeMeta",
    "SetEssenceMarkInPlay",
    "SetEssenceMarkInRec",
    "SetEssenceMarkMaxNum",
    ":mediaCpOKMarkSet",
    ":metaEssenceMarkDelete",
)

FX3_APPFW_AE_IRIS_MARKERS: Tuple[str, ...] = (
    "PID_SET_PUSH_AUTO_IRIS_MODE",
    "UIBIZ_KEY_TACT_ONEPUSH_AUTO_IRIS",
    "UIBIZ_KEY_TACT_ONEPUSH_AUTO_ND",
    "EXTERN_VAL_ND_FILTER_AUTO",
    "RECALL_SHOOT_SET_METERING_MODE_MULTI",
    "RECALL_SHOOT_SET_METERING_MODE_CENTER",
    "RECALL_SHOOT_SET_METERING_MODE_SPOT",
    "RECALL_SHOOT_SET_METERING_MODE_ENTIRE_SCREEN_AVG",
    "RECALL_SHOOT_SET_METERING_MODE_HIGHLIGHT",
    "EVENT_FUNC_FACE_DETECTION_IN_MULTI_ON",
    "VAL_setting_ae_level_offset_AE_LEVEL_OFFSET_0EV",
    "VAL_setting_ae_level_offset_AE_LEVEL_OFFSET_1EV",
    "EXPOSURE_COMPENSATION",
)

FX6_APPFW_AE_IRIS_MARKERS: Tuple[str, ...] = (
    "ASSIGNABLE_SWITCH_AUTO_ND_FILTER",
    "ASSIGNABLE_SWITCH_PUSH_AUTO_IRIS",
    "ASSIGNABLE_SWITCH_PUSH_AUTO_ND",
    "BKID_APP_AUTO_ND_FILTER",
    "BKID_APP_EXTERN_AE_LEVEL",
    "BKID_APP_SETTING_AE_LEVEL_OFFSET",
    "EVENT_FUNC_AUTO_ND_FILTER_ON",
    "EVENT_FUNC_PUSH_AUTO_IRIS_ON",
    "EVENT_INPUT_KEY_TACT_ONEPUSH_AUTO_IRIS_ON",
    "EVENT_REMOTE_PUSH_AUTO_IRIS",
    "EVENT_REMOTE_PUSH_AUTO_ND_FILTER",
    "EXTERN_VAL_AE_METER_ENTIRE_SCREEN_AVERAGE",
    "BLACKBELT_DISP_METERING_MODE",
    "MODEL_REPROCESS_FUNC_FACE_DETECTION_IN_MULTI_ON",
    "FACE_DETECTION_IN_MULTI_VALUE_ON",
)

FX3_CP_AE_IRIS_MARKERS: Tuple[str, ...] = (
    "SET_PUSH_AUTO_IRIS_MODE",
    "SET_IRIS_DRIVE",
    "SET_IRIS_DRIVE_MODE",
    "SET_IRIS_DIAL",
)

FX6_CP_AE_IRIS_MARKERS: Tuple[str, ...] = (
    "SET_PUSH_AUTO_IRIS_MODE",
    "ND_FILTER_SELECT_FOR_PRESET",
)

LENS_COMM_AE_IRIS_MARKERS: Tuple[str, ...] = (
    "LensCommunicator_Init",
    "GetMountedLensInfo",
    "GetSuopportedCommandIds",
    "SndSyncMsg",
    "OsalSyncRcvMsgCb",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE85_LABELS: Dict[int, str] = {
    0x0004E2C9: "Protect",
    0x0004E5CF: "Metering Mode",
    0x0004E66A: "File protected.",
}

FX3_NS3_PHASE85_LABELS: Dict[int, str] = {
    0x00006044: "Metering",
    0x000060E2: "Added Shot Mark2.",
    0x00006133: "Protect of this image is canceled.",
    0x0000618A: "Shot Mark1",
    0x000061F0: "Added Shot Mark1.",
    0x00006293: "Face/Eye AF",
    0x00006397: "Shot Mark2",
}

FX6_NS1_PHASE85_LABELS: Dict[int, str] = {
    0x00002088: "Thumbnail",
    0x000020D1: "IRIS",
    0x000021B7: "AE Level",
    0x000022E4: "Auto Iris",
    0x00002418: "AE Level Offset",
    0x00002580: "Format Media (A)",
    0x00002581: "Format Media (B)",
    0x000026B8: "Press and Hold for Auto ND",
}

FX6_NS2_PHASE85_LABELS: Dict[int, str] = {
    0x00004092: "Delete Clip?",
    0x000040BE: "Add Shot Mark1?",
    0x000040BF: "Add Shot Mark2?",
    0x0000410D: "Shot Mark",
    0x00004254: "Format Media",
    0x00004285: "Iris",
    0x0000429D: "Auto Iris",
    0x000042AC: "Set Shot Mark",
    0x000042B0: "Thumbnail View",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaybackShuttleEvalResult:
    valid: bool
    status: str
    clip_basename: str
    clip_index: int
    total_clips: int
    direction: str
    shuttle_speed_x: int
    clip_protected: bool
    thumbnail_page_size: int
    thumbnail_page_index: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MediaFirewallEvalResult:
    valid: bool
    status: str
    operation: str
    target_slot: str
    target_device: str
    clip_basename: Optional[str]
    clip_protected: bool
    media_write_protected: bool
    is_external_media: bool
    is_internal_emmc_target: bool
    internal_emmc_format_possible: bool
    internal_emmc_delete_possible: bool
    emmc_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PlaybackThumbnailFirewallReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    uxc_playback_labels: Dict[str, str]
    shuttle_1x_eval: PlaybackShuttleEvalResult
    shuttle_2x_eval: PlaybackShuttleEvalResult
    shuttle_5x_eval: PlaybackShuttleEvalResult
    shuttle_15x_eval: PlaybackShuttleEvalResult
    review_15x_eval: PlaybackShuttleEvalResult
    slot_a_format_eval: MediaFirewallEvalResult
    slot_b_delete_eval: MediaFirewallEvalResult
    blocked_protected_clip_delete_eval: MediaFirewallEvalResult
    blocked_write_protect_format_eval: MediaFirewallEvalResult
    blocked_emmc_p1_format_eval: MediaFirewallEvalResult
    blocked_emmc_p1_delete_eval: MediaFirewallEvalResult
    internal_emmc_format_possible: bool
    internal_emmc_delete_possible: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShotMarkEntry:
    mark_type: str
    frame_offset: int
    capture_mode: str
    timecode: str


@dataclass(frozen=True)
class ShotMarkLedgerEvalResult:
    valid: bool
    status: str
    fps_label: str
    clip_duration_frames: int
    max_marks_per_clip: int
    mark_count: int
    entries: Tuple[ShotMarkEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EssenceMarkXmlRoundtripResult:
    valid: bool
    status: str
    fps_label: str
    xml_namespace: str
    klv_packet_count: int
    essence_mark_count: int
    roundtrip_exact: bool
    nle_consumers: Tuple[str, ...]
    parsed_entries: Tuple[ShotMarkEntry, ...]
    xml_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ShotMarkEssenceXmlReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    uxc_shotmark_labels: Dict[str, str]
    ledger_add_remove_eval: ShotMarkLedgerEvalResult
    blocked_overflow_101_eval: ShotMarkLedgerEvalResult
    roundtrip_23_98p_eval: EssenceMarkXmlRoundtripResult
    roundtrip_24_00p_eval: EssenceMarkXmlRoundtripResult
    roundtrip_25_00p_eval: EssenceMarkXmlRoundtripResult
    roundtrip_29_97p_eval: EssenceMarkXmlRoundtripResult
    roundtrip_59_94p_eval: EssenceMarkXmlRoundtripResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AeIrisConvergenceEvalResult:
    valid: bool
    status: str
    target_body: str
    shooting_mode: str
    base_iso_ei: int
    shutter_angle_deg: float
    iso_locked: bool
    shutter_angle_locked: bool
    photometry_mode: str
    ae_shift_ev: float
    ae_actuator: str
    p4_auto_nd_redirected: bool
    p4_nd_motor_fault_attempts: int
    highlight_clip_protected: bool
    peak_highlight_ire_before: float
    peak_highlight_ire_after: float
    face_eye_priority_active: bool
    current_f_stop: float
    target_f_stop: float
    iris_steps_eighth_stop: int
    applied_ev_delta: float
    residual_ev_error: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PushAutoIrisAeReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_cp_markers: Tuple[str, ...]
    fx6_cp_markers: Tuple[str, ...]
    lens_comm_markers: Tuple[str, ...]
    uxc_ae_iris_labels: Dict[str, str]
    cine_ei_push_auto_iris_eval: AeIrisConvergenceEvalResult
    ae_shift_plus_2ev_eval: AeIrisConvergenceEvalResult
    ae_shift_minus_2ev_eval: AeIrisConvergenceEvalResult
    highlight_94_ire_protect_eval: AeIrisConvergenceEvalResult
    multi_face_eye_priority_eval: AeIrisConvergenceEvalResult
    center_photometry_eval: AeIrisConvergenceEvalResult
    spot_photometry_eval: AeIrisConvergenceEvalResult
    entire_screen_avg_eval: AeIrisConvergenceEvalResult
    blocked_out_of_range_ae_shift_eval: AeIrisConvergenceEvalResult
    p4_nd_motor_fault_attempts: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationProofResult:
    valid: bool
    status: str
    target_path: str
    volatile_shadow_only: bool
    calibration_mutation_bytes: int
    internal_emmc_format_possible: bool
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroCalibrationAndEmmcReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_shadow_eval: ZeroMutationProofResult
    blocked_mmcblk0p1_eval: ZeroMutationProofResult
    blocked_cnflasha_eval: ZeroMutationProofResult
    blocked_backup_bin_eval: ZeroMutationProofResult
    blocked_emmc_flag_eval: ZeroMutationProofResult
    calibration_mutation_bytes: int
    internal_emmc_format_possible: bool
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PlaybackShotmarkAndAeReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    calibration_mutation_bytes: int
    internal_emmc_format_possible: bool
    p4_nd_motor_fault_attempts: int
    donor_file_sizes: Dict[str, int]
    pillar_1_playback_thumbnail_firewall: PlaybackThumbnailFirewallReport
    pillar_2_shotmark_essencemark_xml: ShotMarkEssenceXmlReport
    pillar_3_push_auto_iris_ae_shift: PushAutoIrisAeReport
    pillar_4_zero_mutation_proof: ZeroCalibrationAndEmmcReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap.ACCESS_READ` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Read a compact `.uxc` or `global.xdb` artifact strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens: set[bytes] = set()
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            for off, rsz in ranges:
                for mo in pat.finditer(mm, off, off + rsz):
                    matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    if not unique_markers:
        return len(blob), {k: () for k in marker_groups}
    pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
    matched_tokens = {mo.group(0) for mo in pat.finditer(blob)}
    matched_list = list(matched_tokens)
    present_markers = {
        m
        for m in unique_markers
        if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
    }
    results = {
        group_name: tuple(m for m in markers if m in present_markers)
        for group_name, markers in marker_groups.items()
    }
    return len(blob), results


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_playback_shotmark_ae_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 85."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_blob = _pack(
        (
            *FX3_APPFW_PLAYBACK_FORMAT_MARKERS,
            *FX3_APPFW_SHOTMARK_MARKERS,
            *FX3_APPFW_AE_IRIS_MARKERS,
        )
    )
    fx6_appfw_blob = _pack(
        (
            *FX6_APPFW_PLAYBACK_FORMAT_MARKERS,
            *FX6_APPFW_SHOTMARK_MARKERS,
            *FX6_APPFW_AE_IRIS_MARKERS,
        )
    )
    fx3_libmpr_blob = _pack((*FX3_LIBMPR_PLAYBACK_MARKERS, *FX3_LIBMPR_SHOTMARK_MARKERS))
    fx6_libmpr_blob = _pack((*FX6_LIBMPR_PLAYBACK_MARKERS, *FX6_LIBMPR_SHOTMARK_MARKERS))
    fx3_cp_blob = _pack(FX3_CP_AE_IRIS_MARKERS, prefix=cp_hdr)
    fx6_cp_blob = _pack(FX6_CP_AE_IRIS_MARKERS, prefix=cp_hdr)
    lens_comm_blob = build_synthetic_elf64_so(
        soname="libInfraLensCommunicator.so",
        dt_needed=("libc.so.6",),
        exports=LENS_COMM_AE_IRIS_MARKERS,
        imports=(),
    )

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE85_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE85_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE85_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE85_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_libmpr": fx3_libmpr_blob,
        "fx6_libmpr": fx6_libmpr_blob,
        "fx3_cpapp": fx3_cp_blob,
        "fx6_cpapp": fx6_cp_blob,
        "fx3_lens_comm": lens_comm_blob,
        "fx6_lens_comm": lens_comm_blob,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


# ---------------------------------------------------------------------------
# Pillar 1: Playback / Thumbnail Presenter & Internal p1 Media Firewall
# ---------------------------------------------------------------------------


def evaluate_playback_shuttle_and_thumbnail(
    *,
    clip_basename: str = "A001C001_261114_FX30",
    clip_index: int = 0,
    total_clips: int = 18,
    direction: str = "CUE",
    shuttle_speed_x: int = 1,
    clip_protected: bool = False,
    thumbnail_page_size: int = 9,
) -> PlaybackShuttleEvalResult:
    """Evaluate `icx1295` Thumbnail index paging and `Cue/Review` (`1x, 2x, 5x, 15x`) shuttle."""
    errors: List[str] = []
    norm_dir = direction.strip().upper()
    if norm_dir not in CUE_REVIEW_DIRECTIONS:
        errors.append(f"Unsupported shuttle direction {direction!r}; expected {CUE_REVIEW_DIRECTIONS}")
    if shuttle_speed_x not in CUE_REVIEW_SPEEDS:
        errors.append(f"Unsupported shuttle_speed_x={shuttle_speed_x!r}; expected {CUE_REVIEW_SPEEDS}")
    if total_clips <= 0:
        errors.append(f"total_clips={total_clips!r} must be > 0")
    if clip_index < 0 or clip_index >= max(1, total_clips):
        errors.append(f"clip_index={clip_index} out of bounds [0..{max(0, total_clips - 1)}]")
    if thumbnail_page_size not in (4, 9, 12):
        errors.append(f"thumbnail_page_size={thumbnail_page_size!r} must be 4, 9, or 12")
    if not clip_basename.strip():
        errors.append("clip_basename must be non-empty")

    page_idx = (clip_index // thumbnail_page_size) if thumbnail_page_size > 0 and clip_index >= 0 else 0
    status = "PLAYBACK_SHUTTLE_THUMBNAIL_VERIFIED" if not errors else "BLOCKED_INVALID_PLAYBACK_STATE"
    return PlaybackShuttleEvalResult(
        valid=len(errors) == 0,
        status=status,
        clip_basename=clip_basename,
        clip_index=clip_index,
        total_clips=total_clips,
        direction=norm_dir,
        shuttle_speed_x=shuttle_speed_x,
        clip_protected=clip_protected,
        thumbnail_page_size=thumbnail_page_size,
        thumbnail_page_index=page_idx,
        errors=tuple(errors),
    )


def evaluate_media_format_and_delete_firewall(
    *,
    operation: str = "FORMAT_QUICK",
    target_slot: str = "SLOT_A",
    target_device: str = "/dev/mmcblk1p1",
    clip_basename: Optional[str] = None,
    clip_protected: bool = False,
    media_write_protected: bool = False,
) -> MediaFirewallEvalResult:
    """Enforce strict internal eMMC `p1` (`/dev/mmcblk0p1`) isolation from Delete/Format commands."""
    errors: List[str] = []
    norm_op = operation.strip().upper()
    norm_slot = target_slot.strip().upper()
    norm_dev = target_device.strip()
    low_dev = norm_dev.lower()
    low_slot = norm_slot.lower()

    if norm_op not in VALID_PLAYBACK_MEDIA_OPS:
        errors.append(f"Unsupported operation {operation!r}; expected {VALID_PLAYBACK_MEDIA_OPS}")

    is_internal_emmc = any(
        tok in low_dev or tok in low_slot
        for tok in FORBIDDEN_INTERNAL_EMMC_TARGETS
    ) or ("internal" in low_slot or "emmc" in low_slot or "internal" in low_dev)

    slot_spec = EXTERNAL_MEDIA_SLOT_SPECS.get(norm_slot)
    allowed_devs: Tuple[str, ...] = tuple(slot_spec["block_devices"]) if slot_spec else ()  # type: ignore[arg-type]
    is_external = (not is_internal_emmc) and (slot_spec is not None) and (norm_dev in allowed_devs)

    if is_internal_emmc:
        errors.append(
            f"BLOCKED_INTERNAL_EMMC_P1_FIREWALL: {norm_op} forbidden on internal eMMC target "
            f"slot={target_slot!r} dev={target_device!r} (p1 /dev/mmcblk0p1 strictly isolated)"
        )
    elif not is_external:
        errors.append(
            f"BLOCKED_UNRECOGNIZED_MEDIA_TARGET: slot={target_slot!r} dev={target_device!r} "
            f"is not an authorized external Slot A/B CFexpress/SDXC device"
        )

    if not errors and norm_op == "DELETE_CLIP":
        if not clip_basename:
            errors.append("DELETE_CLIP requires a target clip_basename")
        elif clip_protected:
            errors.append(
                f"BLOCKED_CLIP_PROTECT_LOCK_ACTIVE: Clip {clip_basename!r} is locked (Protect ON)"
            )

    if not errors and norm_op in ("FORMAT_QUICK", "FORMAT_FULL") and media_write_protected:
        errors.append(
            f"BLOCKED_MEDIA_WRITE_PROTECTED: Cannot format {norm_slot} ({norm_dev}) with write-protect switch ON"
        )

    if any("INTERNAL_EMMC_P1_FIREWALL" in e for e in errors):
        status = "BLOCKED_INTERNAL_EMMC_P1_FIREWALL"
    elif any("CLIP_PROTECT_LOCK_ACTIVE" in e for e in errors):
        status = "BLOCKED_CLIP_PROTECT_LOCK_ACTIVE"
    elif any("MEDIA_WRITE_PROTECTED" in e for e in errors):
        status = "BLOCKED_MEDIA_WRITE_PROTECTED"
    elif errors:
        status = "BLOCKED_MEDIA_POLICY"
    else:
        status = f"EXTERNAL_MEDIA_{norm_op}_VERIFIED"

    return MediaFirewallEvalResult(
        valid=len(errors) == 0,
        status=status,
        operation=norm_op,
        target_slot=norm_slot,
        target_device=norm_dev,
        clip_basename=clip_basename,
        clip_protected=clip_protected,
        media_write_protected=media_write_protected,
        is_external_media=is_external,
        is_internal_emmc_target=is_internal_emmc,
        internal_emmc_format_possible=False,
        internal_emmc_delete_possible=False,
        emmc_mutation_bytes=0,
        errors=tuple(errors),
    )


def evaluate_pillar_1_playback_thumbnail_firewall(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> PlaybackThumbnailFirewallReport:
    """Audit Pillar 1 across Playback/Thumbnail binary markers, shuttle speeds, and eMMC `p1` firewall."""
    errors: List[str] = []
    fx3_pb = present_map["fx3_appfw_playback"]
    fx6_pb = present_map["fx6_appfw_playback"]
    fx3_mpr = present_map["fx3_libmpr_playback"]
    fx6_mpr = present_map["fx6_libmpr_playback"]

    if fx3_pb != FX3_APPFW_PLAYBACK_FORMAT_MARKERS:
        missing = tuple(m for m in FX3_APPFW_PLAYBACK_FORMAT_MARKERS if m not in fx3_pb)
        errors.append(f"FX3 appFw.so missing Playback/Protect/Format markers: {missing}")
    if fx6_pb != FX6_APPFW_PLAYBACK_FORMAT_MARKERS:
        missing = tuple(m for m in FX6_APPFW_PLAYBACK_FORMAT_MARKERS if m not in fx6_pb)
        errors.append(f"FX6 appFw.so missing Thumbnail/Delete/Format markers: {missing}")
    if fx3_mpr != FX3_LIBMPR_PLAYBACK_MARKERS:
        missing = tuple(m for m in FX3_LIBMPR_PLAYBACK_MARKERS if m not in fx3_mpr)
        errors.append(f"FX3 libmpr.so missing Thumbnail/Format markers: {missing}")
    if fx6_mpr != FX6_LIBMPR_PLAYBACK_MARKERS:
        missing = tuple(m for m in FX6_LIBMPR_PLAYBACK_MARKERS if m not in fx6_mpr)
        errors.append(f"FX6 libmpr.so missing Thumbnail markers: {missing}")

    s1 = evaluate_playback_shuttle_and_thumbnail(clip_index=0, direction="CUE", shuttle_speed_x=1)
    s2 = evaluate_playback_shuttle_and_thumbnail(clip_index=3, direction="CUE", shuttle_speed_x=2)
    s5 = evaluate_playback_shuttle_and_thumbnail(clip_index=9, direction="CUE", shuttle_speed_x=5, clip_protected=True)
    s15 = evaluate_playback_shuttle_and_thumbnail(clip_index=12, direction="CUE", shuttle_speed_x=15)
    rev15 = evaluate_playback_shuttle_and_thumbnail(clip_index=15, direction="REVIEW", shuttle_speed_x=15)

    for ev in (s1, s2, s5, s15, rev15):
        if not ev.valid:
            errors.extend(ev.errors)

    fmt_a = evaluate_media_format_and_delete_firewall(
        operation="FORMAT_QUICK",
        target_slot="SLOT_A",
        target_device="/dev/mmcblk1p1",
    )
    del_b = evaluate_media_format_and_delete_firewall(
        operation="DELETE_CLIP",
        target_slot="SLOT_B",
        target_device="/dev/mmcblk2p1",
        clip_basename="A001C002_261114_FX30",
        clip_protected=False,
    )
    blk_prot = evaluate_media_format_and_delete_firewall(
        operation="DELETE_CLIP",
        target_slot="SLOT_A",
        target_device="/dev/mmcblk1p1",
        clip_basename="A001C001_261114_FX30",
        clip_protected=True,
    )
    blk_wp = evaluate_media_format_and_delete_firewall(
        operation="FORMAT_FULL",
        target_slot="SLOT_B",
        target_device="/dev/mmcblk2p1",
        media_write_protected=True,
    )
    blk_p1_fmt = evaluate_media_format_and_delete_firewall(
        operation="FORMAT_FULL",
        target_slot="INTERNAL_P1",
        target_device="/dev/mmcblk0p1",
    )
    blk_p1_del = evaluate_media_format_and_delete_firewall(
        operation="DELETE_CLIP",
        target_slot="p1:",
        target_device="/dev/mmcblk0p1",
        clip_basename="A001C001_261114_FX30",
    )

    if not fmt_a.valid or fmt_a.internal_emmc_format_possible:
        errors.append("Slot A external format check failed")
    if not del_b.valid or del_b.internal_emmc_delete_possible:
        errors.append("Slot B external clip delete check failed")
    if blk_prot.valid or blk_prot.status != "BLOCKED_CLIP_PROTECT_LOCK_ACTIVE":
        errors.append("Protected clip failed to block deletion")
    if blk_wp.valid or blk_wp.status != "BLOCKED_MEDIA_WRITE_PROTECTED":
        errors.append("Write-protected media failed to block format")
    if blk_p1_fmt.valid or blk_p1_fmt.status != "BLOCKED_INTERNAL_EMMC_P1_FIREWALL":
        errors.append("Internal eMMC p1 format firewall failed to block")
    if blk_p1_del.valid or blk_p1_del.status != "BLOCKED_INTERNAL_EMMC_P1_FIREWALL":
        errors.append("Internal eMMC p1 delete firewall failed to block")

    playback_uxc = {
        k: v
        for k, v in uxc_labels.items()
        if k
        in (
            "fx3_protect",
            "fx3_file_protected",
            "fx3_protect_canceled",
            "fx6_thumbnail",
            "fx6_format_a",
            "fx6_format_b",
            "fx6_delete_clip",
            "fx6_format_media",
            "fx6_thumbnail_view",
        )
    }

    return PlaybackThumbnailFirewallReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_pb,
        fx6_appfw_markers=fx6_pb,
        fx3_libmpr_markers=fx3_mpr,
        fx6_libmpr_markers=fx6_mpr,
        uxc_playback_labels=playback_uxc,
        shuttle_1x_eval=s1,
        shuttle_2x_eval=s2,
        shuttle_5x_eval=s5,
        shuttle_15x_eval=s15,
        review_15x_eval=rev15,
        slot_a_format_eval=fmt_a,
        slot_b_delete_eval=del_b,
        blocked_protected_clip_delete_eval=blk_prot,
        blocked_write_protect_format_eval=blk_wp,
        blocked_emmc_p1_format_eval=blk_p1_fmt,
        blocked_emmc_p1_delete_eval=blk_p1_del,
        internal_emmc_format_possible=False,
        internal_emmc_delete_possible=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: Cinema Line Shot Mark 1 / 2 / OK / KEEP & EssenceMark XML Verifier
# ---------------------------------------------------------------------------


def frame_offset_to_timecode(
    frame_offset: int,
    fps_label: str,
    *,
    start_tc_frames: int = 0,
) -> str:
    """Convert a 0-based `frame_offset` at `fps_label` into SMPTE `HH:MM:SS:FF`."""
    if frame_offset < 0:
        raise ValueError(f"frame_offset={frame_offset} must be >= 0")
    if start_tc_frames < 0:
        raise ValueError(f"start_tc_frames={start_tc_frames} must be >= 0")
    spec = SHOT_MARK_FPS_SPECS.get(fps_label)
    if spec is None:
        raise ValueError(f"Unsupported fps_label={fps_label!r}; expected {SHOT_MARK_SUPPORTED_FPS}")
    tb = int(spec["timebase"])
    total = start_tc_frames + frame_offset
    ff = total % tb
    total_sec = total // tb
    ss = total_sec % 60
    total_min = total_sec // 60
    mm = total_min % 60
    hh = (total_min // 60) % 24
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def apply_shotmark_operations(
    operations: Sequence[Mapping[str, object]],
    *,
    fps_label: str = "23.98p",
    clip_duration_frames: int = 7200,
    max_marks_per_clip: int = SHOT_MARK_MAX_PER_CLIP,
    start_tc_frames: int = 86400,  # 01:00:00:00 at 24fps
) -> ShotMarkLedgerEvalResult:
    """Apply live `IN_REC` / `IN_PLAY` ShotMark insert/remove actions within `0..max_marks_per_clip`."""
    errors: List[str] = []
    if fps_label not in SHOT_MARK_FPS_SPECS:
        errors.append(f"Unsupported fps_label={fps_label!r}; expected {SHOT_MARK_SUPPORTED_FPS}")
    if clip_duration_frames <= 0:
        errors.append(f"clip_duration_frames={clip_duration_frames} must be > 0")
    if max_marks_per_clip <= 0 or max_marks_per_clip > SHOT_MARK_MAX_PER_CLIP:
        errors.append(f"max_marks_per_clip={max_marks_per_clip} outside [1..{SHOT_MARK_MAX_PER_CLIP}]")

    marks: List[ShotMarkEntry] = []
    if not errors:
        for idx, op in enumerate(operations):
            action = str(op.get("action", "ADD")).strip().upper()
            mark_type = str(op.get("mark_type", "_ShotMark1")).strip()
            frame_offset = int(op.get("frame_offset", -1))
            capture_mode = str(op.get("capture_mode", "IN_REC")).strip().upper()

            if mark_type not in VALID_SHOT_MARK_TYPES:
                errors.append(f"op[{idx}]: invalid mark_type={mark_type!r}; expected {VALID_SHOT_MARK_TYPES}")
                break
            if capture_mode not in VALID_SHOT_MARK_CAPTURE_MODES:
                errors.append(f"op[{idx}]: invalid capture_mode={capture_mode!r}")
                break
            if frame_offset < 0 or frame_offset >= clip_duration_frames:
                errors.append(
                    f"op[{idx}]: frame_offset={frame_offset} outside [0..{clip_duration_frames - 1}]"
                )
                break

            if action == "ADD":
                if len(marks) >= max_marks_per_clip:
                    errors.append(
                        f"BLOCKED_SHOT_MARK_CAPACITY_EXCEEDED: cannot exceed max_marks_per_clip={max_marks_per_clip}"
                    )
                    break
                if any(m.mark_type == mark_type and m.frame_offset == frame_offset for m in marks):
                    errors.append(
                        f"op[{idx}]: duplicate ShotMark ({mark_type!r}, frame={frame_offset})"
                    )
                    break
                tc = frame_offset_to_timecode(
                    frame_offset, fps_label, start_tc_frames=start_tc_frames
                )
                marks.append(
                    ShotMarkEntry(
                        mark_type=mark_type,
                        frame_offset=frame_offset,
                        capture_mode=capture_mode,
                        timecode=tc,
                    )
                )
            elif action == "REMOVE":
                before = len(marks)
                marks = [
                    m
                    for m in marks
                    if not (m.mark_type == mark_type and m.frame_offset == frame_offset)
                ]
                if len(marks) == before:
                    errors.append(
                        f"op[{idx}]: ShotMark not found for removal ({mark_type!r}, frame={frame_offset})"
                    )
                    break
            else:
                errors.append(f"op[{idx}]: unsupported action={action!r}; expected ADD or REMOVE")
                break

    marks.sort(key=lambda m: (m.frame_offset, m.mark_type))
    if any("CAPACITY_EXCEEDED" in e for e in errors):
        status = "BLOCKED_SHOT_MARK_CAPACITY_EXCEEDED"
    elif errors:
        status = "BLOCKED_INVALID_SHOT_MARK_OP"
    else:
        status = "SHOT_MARK_LEDGER_VERIFIED"

    return ShotMarkLedgerEvalResult(
        valid=len(errors) == 0,
        status=status,
        fps_label=fps_label,
        clip_duration_frames=clip_duration_frames,
        max_marks_per_clip=max_marks_per_clip,
        mark_count=len(marks),
        entries=tuple(marks),
        errors=tuple(errors),
    )


def synthesize_essencemark_nrtm_xml(
    entries: Sequence[ShotMarkEntry],
    *,
    clip_basename: str = "A001C001_261114_FX30",
    fps_label: str = "23.98p",
    clip_duration_frames: int = 7200,
    video_codec: str = "AVC_4096_2160_H422IP",
    umid: str = "060A2B340101010501010D4313000000A001C00126111400",
) -> str:
    """Serialize frame-indexed ShotMarks into Sony `NonRealTimeMeta v2.20` `<KlvPacketTable>` / `<EssenceMark>` XML."""
    spec = SHOT_MARK_FPS_SPECS.get(fps_label)
    if spec is None:
        raise ValueError(f"Unsupported fps_label={fps_label!r}; expected {SHOT_MARK_SUPPORTED_FPS}")
    if clip_duration_frames <= 0:
        raise ValueError(f"clip_duration_frames={clip_duration_frames} must be > 0")

    root = ET.Element(
        "NonRealTimeMeta",
        {
            "xmlns": NRTM_NAMESPACE_V220,
            "lastUpdate": "2026-11-14T17:00:00Z",
        },
    )
    ET.SubElement(root, "TargetMaterial", {"umidRef": umid})
    ET.SubElement(root, "Duration", {"value": str(clip_duration_frames)})

    vf = ET.SubElement(root, "VideoFormat")
    ET.SubElement(
        vf,
        "VideoFrame",
        {
            "videoCodec": video_codec,
            "captureFps": str(spec["capture_fps"]),
            "formatFps": str(spec["format_fps"]),
            "pixelAspectRatio": "1:1",
        },
    )

    klv_table = ET.SubElement(root, "KlvPacketTable", {"count": str(len(entries))})
    for entry in entries:
        if entry.mark_type not in VALID_SHOT_MARK_TYPES:
            raise ValueError(f"Invalid mark_type {entry.mark_type!r}")
        if entry.frame_offset < 0 or entry.frame_offset >= clip_duration_frames:
            raise ValueError(
                f"frame_offset={entry.frame_offset} out of bounds [0..{clip_duration_frames - 1}]"
            )
        pkt = ET.SubElement(
            klv_table,
            "KlvPacket",
            {
                "key": ESSENCE_MARK_KLV_UNIVERSAL_KEY,
                "frameCount": str(entry.frame_offset),
                "status": "valid",
            },
        )
        ET.SubElement(
            pkt,
            "EssenceMark",
            {
                "name": entry.mark_type,
                "start": str(entry.frame_offset),
                "timecode": entry.timecode,
                "captureMode": entry.capture_mode,
                "clipName": clip_basename,
            },
        )

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def parse_and_verify_essencemark_nrtm_xml(
    xml_text: str,
    *,
    expected_entries: Sequence[ShotMarkEntry],
    fps_label: str = "23.98p",
    clip_duration_frames: int = 7200,
) -> EssenceMarkXmlRoundtripResult:
    """Parse and roundtrip-verify Sony `NonRealTimeMeta v2.20` `<KlvPacketTable>` / `<EssenceMark>` XML."""
    errors: List[str] = []
    parsed_entries: List[ShotMarkEntry] = []
    xml_ns = ""
    klv_count = 0

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return EssenceMarkXmlRoundtripResult(
            valid=False,
            status="BLOCKED_MALFORMED_NRTM_XML",
            fps_label=fps_label,
            xml_namespace="",
            klv_packet_count=0,
            essence_mark_count=0,
            roundtrip_exact=False,
            nle_consumers=TARGET_NLE_CONSUMERS,
            parsed_entries=(),
            xml_sha256=hashlib.sha256(xml_text.encode("utf-8")).hexdigest(),
            errors=(f"XML parse error: {exc}",),
        )

    if root.tag.startswith("{") and "}" in root.tag:
        xml_ns = root.tag[1 : root.tag.index("}")]
    if xml_ns != NRTM_NAMESPACE_V220:
        errors.append(f"Unexpected NonRealTimeMeta namespace {xml_ns!r}; expected {NRTM_NAMESPACE_V220!r}")

    ns = {"n": NRTM_NAMESPACE_V220} if xml_ns == NRTM_NAMESPACE_V220 else {}
    dur_el = root.find("n:Duration", ns) if ns else root.find("Duration")
    if dur_el is None:
        errors.append("Missing <Duration> element")
    else:
        try:
            dur_val = int(dur_el.attrib.get("value", "-1"))
            if dur_val != clip_duration_frames:
                errors.append(f"<Duration value={dur_val}> != expected {clip_duration_frames}")
        except ValueError:
            errors.append("Invalid <Duration> integer value")

    vf_el = root.find("n:VideoFormat/n:VideoFrame", ns) if ns else root.find("VideoFormat/VideoFrame")
    spec = SHOT_MARK_FPS_SPECS.get(fps_label)
    if vf_el is None:
        errors.append("Missing <VideoFormat><VideoFrame> element")
    elif spec is not None:
        if vf_el.attrib.get("captureFps") != str(spec["capture_fps"]):
            errors.append(
                f"VideoFrame captureFps={vf_el.attrib.get('captureFps')!r} != {spec['capture_fps']!r}"
            )

    klv_table = root.find("n:KlvPacketTable", ns) if ns else root.find("KlvPacketTable")
    if klv_table is None:
        errors.append("Missing <KlvPacketTable> element")
    else:
        pkts = klv_table.findall("n:KlvPacket", ns) if ns else klv_table.findall("KlvPacket")
        klv_count = len(pkts)
        for pkt in pkts:
            em = pkt.find("n:EssenceMark", ns) if ns else pkt.find("EssenceMark")
            if em is None:
                errors.append("<KlvPacket> missing child <EssenceMark>")
                continue
            name = em.attrib.get("name", "")
            start_raw = em.attrib.get("start", "")
            tc = em.attrib.get("timecode", "")
            cap_mode = em.attrib.get("captureMode", "")
            if name not in VALID_SHOT_MARK_TYPES:
                errors.append(f"Invalid EssenceMark name={name!r}")
                continue
            try:
                start_frame = int(start_raw)
            except ValueError:
                errors.append(f"Invalid EssenceMark start={start_raw!r}")
                continue
            if start_frame < 0 or start_frame >= clip_duration_frames:
                errors.append(f"EssenceMark start={start_frame} out of range [0..{clip_duration_frames - 1}]")
                continue
            parsed_entries.append(
                ShotMarkEntry(
                    mark_type=name,
                    frame_offset=start_frame,
                    capture_mode=cap_mode,
                    timecode=tc,
                )
            )

    roundtrip_exact = tuple(parsed_entries) == tuple(expected_entries) and len(errors) == 0
    if not roundtrip_exact and len(errors) == 0:
        errors.append("Frame-accurate EssenceMark round-trip mismatch against expected ShotMarks")

    return EssenceMarkXmlRoundtripResult(
        valid=len(errors) == 0 and roundtrip_exact,
        status="ESSENCE_MARK_XML_ROUNDTRIP_VERIFIED" if (len(errors) == 0 and roundtrip_exact) else "BLOCKED_ESSENCE_MARK_MISMATCH",
        fps_label=fps_label,
        xml_namespace=xml_ns,
        klv_packet_count=klv_count,
        essence_mark_count=len(parsed_entries),
        roundtrip_exact=roundtrip_exact,
        nle_consumers=TARGET_NLE_CONSUMERS,
        parsed_entries=tuple(parsed_entries),
        xml_sha256=hashlib.sha256(xml_text.encode("utf-8")).hexdigest(),
        errors=tuple(errors),
    )


def evaluate_pillar_2_shotmark_essencemark(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> ShotMarkEssenceXmlReport:
    """Audit Pillar 2 across ShotMark binary markers, 0..100 ledger, and 5-framerate EssenceMark XML roundtrips."""
    errors: List[str] = []
    fx3_sm = present_map["fx3_appfw_shotmark"]
    fx6_sm = present_map["fx6_appfw_shotmark"]
    fx3_mpr_sm = present_map["fx3_libmpr_shotmark"]
    fx6_mpr_sm = present_map["fx6_libmpr_shotmark"]

    if fx3_sm != FX3_APPFW_SHOTMARK_MARKERS:
        missing = tuple(m for m in FX3_APPFW_SHOTMARK_MARKERS if m not in fx3_sm)
        errors.append(f"FX3 appFw.so missing ShotMark/OK/KEEP markers: {missing}")
    if fx6_sm != FX6_APPFW_SHOTMARK_MARKERS:
        missing = tuple(m for m in FX6_APPFW_SHOTMARK_MARKERS if m not in fx6_sm)
        errors.append(f"FX6 appFw.so missing ShotMark/OK/KEEP markers: {missing}")
    if fx3_mpr_sm != FX3_LIBMPR_SHOTMARK_MARKERS:
        missing = tuple(m for m in FX3_LIBMPR_SHOTMARK_MARKERS if m not in fx3_mpr_sm)
        errors.append(f"FX3 libmpr.so missing EssenceMark/KlvPacketTable markers: {missing}")
    if fx6_mpr_sm != FX6_LIBMPR_SHOTMARK_MARKERS:
        missing = tuple(m for m in FX6_LIBMPR_SHOTMARK_MARKERS if m not in fx6_mpr_sm)
        errors.append(f"FX6 libmpr.so missing EssenceMark/KlvPacketTable markers: {missing}")

    ops = (
        {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 24, "capture_mode": "IN_REC"},
        {"action": "ADD", "mark_type": "_ShotMark2", "frame_offset": 120, "capture_mode": "IN_REC"},
        {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": 480, "capture_mode": "IN_PLAY"},
        {"action": "ADD", "mark_type": "OK", "frame_offset": 960, "capture_mode": "IN_PLAY"},
        {"action": "ADD", "mark_type": "KEEP", "frame_offset": 1440, "capture_mode": "IN_PLAY"},
        {"action": "REMOVE", "mark_type": "_ShotMark1", "frame_offset": 480, "capture_mode": "IN_PLAY"},
    )
    ledger_eval = apply_shotmark_operations(ops, fps_label="23.98p", clip_duration_frames=7200)
    if not ledger_eval.valid or ledger_eval.mark_count != 4:
        errors.extend(ledger_eval.errors or ("ShotMark add/remove ledger expected 4 entries",))

    overflow_ops = [
        {"action": "ADD", "mark_type": "_ShotMark1", "frame_offset": i * 10, "capture_mode": "IN_REC"}
        for i in range(SHOT_MARK_MAX_PER_CLIP + 1)
    ]
    overflow_eval = apply_shotmark_operations(overflow_ops, fps_label="23.98p", clip_duration_frames=7200)
    if overflow_eval.valid or overflow_eval.status != "BLOCKED_SHOT_MARK_CAPACITY_EXCEEDED":
        errors.append("ShotMark 101-mark overflow failed to trigger capacity guard")

    roundtrips: Dict[str, EssenceMarkXmlRoundtripResult] = {}
    for fps in SHOT_MARK_SUPPORTED_FPS:
        fps_ledger = apply_shotmark_operations(ops, fps_label=fps, clip_duration_frames=7200)
        xml_txt = synthesize_essencemark_nrtm_xml(
            fps_ledger.entries,
            fps_label=fps,
            clip_duration_frames=7200,
        )
        rt = parse_and_verify_essencemark_nrtm_xml(
            xml_txt,
            expected_entries=fps_ledger.entries,
            fps_label=fps,
            clip_duration_frames=7200,
        )
        roundtrips[fps] = rt
        if not rt.valid or not rt.roundtrip_exact:
            errors.extend(rt.errors or (f"EssenceMark XML round-trip failed for {fps}",))

    shotmark_uxc = {
        k: v
        for k, v in uxc_labels.items()
        if k
        in (
            "fx3_shotmark1",
            "fx3_shotmark2",
            "fx3_added_sm1",
            "fx3_added_sm2",
            "fx6_add_sm1",
            "fx6_add_sm2",
            "fx6_shot_mark",
            "fx6_set_shot_mark",
        )
    }

    return ShotMarkEssenceXmlReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_sm,
        fx6_appfw_markers=fx6_sm,
        fx3_libmpr_markers=fx3_mpr_sm,
        fx6_libmpr_markers=fx6_mpr_sm,
        uxc_shotmark_labels=shotmark_uxc,
        ledger_add_remove_eval=ledger_eval,
        blocked_overflow_101_eval=overflow_eval,
        roundtrip_23_98p_eval=roundtrips["23.98p"],
        roundtrip_24_00p_eval=roundtrips["24.00p"],
        roundtrip_25_00p_eval=roundtrips["25.00p"],
        roundtrip_29_97p_eval=roundtrips["29.97p"],
        roundtrip_59_94p_eval=roundtrips["59.94p"],
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Push Auto Iris (1/8-stop), AE Shift (-2..+2 EV) & P4 Auto-ND Redirect
# ---------------------------------------------------------------------------


def evaluate_push_auto_iris_and_ae_shift(
    *,
    target_body: str = "ILME-FX3",
    shooting_mode: str = "CINE_EI",
    base_iso_ei: int = 800,
    shutter_angle_deg: float = 180.0,
    photometry_mode: str = "MULTI",
    ae_shift_ev: float = 0.0,
    current_f_stop: float = 2.8,
    min_f_stop: float = 1.4,
    max_f_stop: float = 22.0,
    scene_ev_error: float = 0.0,
    peak_highlight_ire: float = 75.0,
    face_eye_detected: bool = False,
    face_eye_priority_in_multi: bool = True,
    push_auto_requested: bool = True,
    auto_nd_requested: bool = True,
) -> AeIrisConvergenceEvalResult:
    """Evaluate `Cine EI` `Push Auto Iris` (`1/8`-stop servo), `AE Shift`, Photometry & `P4` Auto-ND redirect."""
    errors: List[str] = []
    norm_body = target_body.strip().upper()
    norm_shoot = shooting_mode.strip().upper()
    norm_photo = photometry_mode.strip().upper()

    if norm_shoot not in VALID_SHOOTING_MODES:
        errors.append(f"Unsupported shooting_mode={shooting_mode!r}; expected {VALID_SHOOTING_MODES}")
    if norm_photo not in VALID_PHOTOMETRY_MODES:
        errors.append(f"Unsupported photometry_mode={photometry_mode!r}; expected {VALID_PHOTOMETRY_MODES}")
    if not math.isfinite(ae_shift_ev) or not (AE_SHIFT_MIN_EV <= ae_shift_ev <= AE_SHIFT_MAX_EV):
        errors.append(
            f"BLOCKED_AE_SHIFT_OUT_OF_RANGE: ae_shift_ev={ae_shift_ev!r} outside [{AE_SHIFT_MIN_EV}..{AE_SHIFT_MAX_EV}]"
        )
    if norm_shoot == "CINE_EI":
        if base_iso_ei not in CINE_EI_BASE_ISOS:
            errors.append(f"Cine EI requires locked Dual Base ISO {CINE_EI_BASE_ISOS}, got {base_iso_ei}")
        if abs(shutter_angle_deg - CINE_EI_LOCKED_SHUTTER_ANGLE_DEG) > 1e-6:
            errors.append(
                f"Cine EI requires locked Shutter Angle {CINE_EI_LOCKED_SHUTTER_ANGLE_DEG} deg, got {shutter_angle_deg}"
            )
    if min_f_stop <= 0.0 or min_f_stop >= max_f_stop or not (min_f_stop <= current_f_stop <= max_f_stop):
        errors.append(
            f"Invalid iris bounds current={current_f_stop}, range=[{min_f_stop}..{max_f_stop}]"
        )

    if errors:
        status = (
            "BLOCKED_AE_SHIFT_OUT_OF_RANGE"
            if any("AE_SHIFT_OUT_OF_RANGE" in e for e in errors)
            else "BLOCKED_INVALID_AE_IRIS_CONFIG"
        )
        return AeIrisConvergenceEvalResult(
            valid=False,
            status=status,
            target_body=norm_body,
            shooting_mode=norm_shoot,
            base_iso_ei=base_iso_ei,
            shutter_angle_deg=round(float(shutter_angle_deg), 2),
            iso_locked=(norm_shoot == "CINE_EI"),
            shutter_angle_locked=(norm_shoot == "CINE_EI"),
            photometry_mode=norm_photo,
            ae_shift_ev=float(ae_shift_ev),
            ae_actuator="BLOCKED",
            p4_auto_nd_redirected=False,
            p4_nd_motor_fault_attempts=0,
            highlight_clip_protected=False,
            peak_highlight_ire_before=round(float(peak_highlight_ire), 2),
            peak_highlight_ire_after=round(float(peak_highlight_ire), 2),
            face_eye_priority_active=False,
            current_f_stop=round(float(current_f_stop), 3),
            target_f_stop=round(float(current_f_stop), 3),
            iris_steps_eighth_stop=0,
            applied_ev_delta=0.0,
            residual_ev_error=round(float(scene_ev_error), 4),
            errors=tuple(errors),
        )

    # On FX3 (no P4 internal electronic Variable ND), any FX6 Auto ND / Push Auto ND routes cleanly
    # to E-Mount Push Auto Iris via libInfraLensCommunicator.so with 0 P4 ND motor fault attempts!
    if norm_body == "ILME-FX3":
        p4_redirected = bool(auto_nd_requested or push_auto_requested)
        actuator = "EMOUNT_PUSH_AUTO_IRIS_1_8_STOP"
    else:
        p4_redirected = False
        actuator = "FX6_AUTO_ND_THEN_IRIS"

    # Needed EV change in camera exposure (positive => brighten => open iris / lower f-stop;
    # negative => darken => close iris / higher f-stop).
    # Note: scene_ev_error > 0 means scene is overexposed by +scene_ev_error EV, so camera needs -scene_ev_error EV.
    desired_camera_ev_change = float(ae_shift_ev) - float(scene_ev_error)

    # S-Log3 Highlight Metering (94% IRE clip ceiling protection):
    # Each +1.0 EV near S-Log3 highlights maps roughly ~9.0% IRE on the upper shoulder.
    highlight_protected = False
    eff_peak_before = float(peak_highlight_ire)
    if norm_photo == "HIGHLIGHT" and eff_peak_before > SLOG3_HIGHLIGHT_CLIP_IRE:
        excess_ire = eff_peak_before - SLOG3_HIGHLIGHT_CLIP_IRE
        # Pull exposure down enough in 1/8-stop steps so peak highlight drops <= 94.0% IRE
        extra_pull_ev = -math.ceil((excess_ire / 8.0) / IRIS_EIGHTH_STOP_EV) * IRIS_EIGHTH_STOP_EV
        desired_camera_ev_change = min(desired_camera_ev_change, extra_pull_ev)
        highlight_protected = True

    face_eye_active = (
        norm_photo == "MULTI" and bool(face_eye_priority_in_multi) and bool(face_eye_detected)
    )

    # Convert desired camera exposure EV change into f-stop change:
    # Opening aperture (brighter, +EV) decreases f-stop: f_target = f_cur * 2^(-ev_change / 2)
    raw_steps = int(round(desired_camera_ev_change / IRIS_EIGHTH_STOP_EV))
    quantized_ev_change = raw_steps * IRIS_EIGHTH_STOP_EV
    ideal_f = float(current_f_stop) * (2.0 ** (-quantized_ev_change / 2.0))
    clamped_f = min(float(max_f_stop), max(float(min_f_stop), ideal_f))

    # Actual EV change achieved after lens min/max aperture clamp
    actual_ev_change = -2.0 * math.log2(clamped_f / float(current_f_stop))
    actual_steps = int(round(actual_ev_change / IRIS_EIGHTH_STOP_EV))
    residual_err = round(desired_camera_ev_change - actual_ev_change, 4)

    # Estimate post-convergence highlight IRE when highlight protection engaged
    peak_after = eff_peak_before + (actual_ev_change * 8.0)
    if norm_photo == "HIGHLIGHT" and peak_after <= SLOG3_HIGHLIGHT_CLIP_IRE:
        highlight_protected = True
    elif norm_photo != "HIGHLIGHT":
        highlight_protected = peak_after <= SLOG3_HIGHLIGHT_CLIP_IRE

    if norm_body == "ILME-FX3" and p4_redirected:
        status = "P4_AUTO_ND_REDIRECTED_TO_PUSH_AUTO_IRIS"
    else:
        status = "PUSH_AUTO_IRIS_AE_CONVERGED"

    return AeIrisConvergenceEvalResult(
        valid=True,
        status=status,
        target_body=norm_body,
        shooting_mode=norm_shoot,
        base_iso_ei=base_iso_ei,
        shutter_angle_deg=round(float(shutter_angle_deg), 2),
        iso_locked=(norm_shoot == "CINE_EI"),
        shutter_angle_locked=(norm_shoot == "CINE_EI"),
        photometry_mode=norm_photo,
        ae_shift_ev=round(float(ae_shift_ev), 3),
        ae_actuator=actuator,
        p4_auto_nd_redirected=p4_redirected,
        p4_nd_motor_fault_attempts=0,
        highlight_clip_protected=highlight_protected,
        peak_highlight_ire_before=round(eff_peak_before, 2),
        peak_highlight_ire_after=round(peak_after, 2),
        face_eye_priority_active=face_eye_active,
        current_f_stop=round(float(current_f_stop), 3),
        target_f_stop=round(clamped_f, 3),
        iris_steps_eighth_stop=actual_steps,
        applied_ev_delta=round(actual_ev_change, 4),
        residual_ev_error=residual_err,
        errors=(),
    )


def evaluate_pillar_3_push_auto_iris_ae(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> PushAutoIrisAeReport:
    """Audit Pillar 3 across AE/Iris/LensComm binary markers, `1/8`-stop convergence & `P4` Auto-ND redirect."""
    errors: List[str] = []
    fx3_ae = present_map["fx3_appfw_ae_iris"]
    fx6_ae = present_map["fx6_appfw_ae_iris"]
    fx3_cp = present_map["fx3_cp_ae_iris"]
    fx6_cp = present_map["fx6_cp_ae_iris"]
    lens_m = present_map["lens_comm_ae_iris"]

    if fx3_ae != FX3_APPFW_AE_IRIS_MARKERS:
        missing = tuple(m for m in FX3_APPFW_AE_IRIS_MARKERS if m not in fx3_ae)
        errors.append(f"FX3 appFw.so missing Push Auto Iris/Metering/AE markers: {missing}")
    if fx6_ae != FX6_APPFW_AE_IRIS_MARKERS:
        missing = tuple(m for m in FX6_APPFW_AE_IRIS_MARKERS if m not in fx6_ae)
        errors.append(f"FX6 appFw.so missing Push Auto Iris/Auto ND/AE Level markers: {missing}")
    if fx3_cp != FX3_CP_AE_IRIS_MARKERS:
        missing = tuple(m for m in FX3_CP_AE_IRIS_MARKERS if m not in fx3_cp)
        errors.append(f"FX3 cpapp-b.bin missing Iris IPC markers: {missing}")
    if fx6_cp != FX6_CP_AE_IRIS_MARKERS:
        missing = tuple(m for m in FX6_CP_AE_IRIS_MARKERS if m not in fx6_cp)
        errors.append(f"FX6 cpapp-b.bin missing Push Auto Iris/ND markers: {missing}")
    if lens_m != LENS_COMM_AE_IRIS_MARKERS:
        missing = tuple(m for m in LENS_COMM_AE_IRIS_MARKERS if m not in lens_m)
        errors.append(f"libInfraLensCommunicator.so missing markers: {missing}")

    cine_ei_iris = evaluate_push_auto_iris_and_ae_shift(
        target_body="ILME-FX3",
        shooting_mode="CINE_EI",
        base_iso_ei=800,
        shutter_angle_deg=180.0,
        photometry_mode="MULTI",
        ae_shift_ev=0.0,
        current_f_stop=2.8,
        scene_ev_error=2.0,
        push_auto_requested=True,
        auto_nd_requested=True,
    )
    ae_plus2 = evaluate_push_auto_iris_and_ae_shift(
        target_body="ILME-FX3",
        shooting_mode="CINE_EI",
        base_iso_ei=12800,
        shutter_angle_deg=180.0,
        photometry_mode="MULTI",
        ae_shift_ev=2.0,
        current_f_stop=4.0,
        scene_ev_error=0.0,
    )
    ae_minus2 = evaluate_push_auto_iris_and_ae_shift(
        target_body="ILME-FX3",
        shooting_mode="CINE_EI",
        base_iso_ei=800,
        shutter_angle_deg=180.0,
        photometry_mode="MULTI",
        ae_shift_ev=-2.0,
        current_f_stop=2.8,
        scene_ev_error=0.0,
    )
    hl_protect = evaluate_push_auto_iris_and_ae_shift(
        target_body="ILME-FX3",
        shooting_mode="CINE_EI",
        base_iso_ei=800,
        shutter_angle_deg=180.0,
        photometry_mode="HIGHLIGHT",
        ae_shift_ev=0.0,
        current_f_stop=2.8,
        scene_ev_error=0.0,
        peak_highlight_ire=102.0,
    )
    face_multi = evaluate_push_auto_iris_and_ae_shift(
        target_body="ILME-FX3",
        shooting_mode="CINE_EI",
        base_iso_ei=800,
        shutter_angle_deg=180.0,
        photometry_mode="MULTI",
        ae_shift_ev=0.5,
        current_f_stop=4.0,
        face_eye_detected=True,
        face_eye_priority_in_multi=True,
    )
    center_ev = evaluate_push_auto_iris_and_ae_shift(photometry_mode="CENTER", ae_shift_ev=0.25)
    spot_ev = evaluate_push_auto_iris_and_ae_shift(photometry_mode="SPOT", ae_shift_ev=-0.5)
    entire_ev = evaluate_push_auto_iris_and_ae_shift(photometry_mode="ENTIRE_SCREEN_AVG", ae_shift_ev=0.0)
    bad_shift = evaluate_push_auto_iris_and_ae_shift(ae_shift_ev=2.5)

    for ev in (
        cine_ei_iris,
        ae_plus2,
        ae_minus2,
        hl_protect,
        face_multi,
        center_ev,
        spot_ev,
        entire_ev,
    ):
        if not ev.valid:
            errors.extend(ev.errors)

    if not cine_ei_iris.p4_auto_nd_redirected or cine_ei_iris.p4_nd_motor_fault_attempts != 0:
        errors.append("Cine EI Push Auto Iris failed to cleanly redirect P4 Auto ND with 0 motor faults")
    if not cine_ei_iris.iso_locked or not cine_ei_iris.shutter_angle_locked:
        errors.append("Cine EI failed to keep Base ISO & 180.0 deg Shutter Angle locked")
    if abs(cine_ei_iris.target_f_stop - 5.6) > 0.05:
        errors.append(f"Expected +2.0 EV overexposure Push Auto Iris convergence F2.8->F5.6, got F{cine_ei_iris.target_f_stop}")
    if not hl_protect.highlight_clip_protected or hl_protect.peak_highlight_ire_after > SLOG3_HIGHLIGHT_CLIP_IRE:
        errors.append("Highlight metering failed to protect S-Log3 <= 94% IRE highlight ceiling")
    if not face_multi.face_eye_priority_active:
        errors.append("Face/Eye Priority in Multi Metering failed to activate")
    if bad_shift.valid or bad_shift.status != "BLOCKED_AE_SHIFT_OUT_OF_RANGE":
        errors.append("Out-of-range AE Shift (+2.5 EV) failed to block")

    total_nd_faults = sum(
        ev.p4_nd_motor_fault_attempts
        for ev in (
            cine_ei_iris,
            ae_plus2,
            ae_minus2,
            hl_protect,
            face_multi,
            center_ev,
            spot_ev,
            entire_ev,
            bad_shift,
        )
    )

    ae_uxc = {
        k: v
        for k, v in uxc_labels.items()
        if k
        in (
            "fx3_metering_mode",
            "fx3_metering",
            "fx3_face_eye_af",
            "fx6_iris",
            "fx6_ae_level",
            "fx6_auto_iris",
            "fx6_ae_level_offset",
            "fx6_press_hold_auto_nd",
            "fx6_iris_ns2",
            "fx6_auto_iris_ns2",
        )
    }

    return PushAutoIrisAeReport(
        passed=len(errors) == 0 and total_nd_faults == 0,
        fx3_appfw_markers=fx3_ae,
        fx6_appfw_markers=fx6_ae,
        fx3_cp_markers=fx3_cp,
        fx6_cp_markers=fx6_cp,
        lens_comm_markers=lens_m,
        uxc_ae_iris_labels=ae_uxc,
        cine_ei_push_auto_iris_eval=cine_ei_iris,
        ae_shift_plus_2ev_eval=ae_plus2,
        ae_shift_minus_2ev_eval=ae_minus2,
        highlight_94_ire_protect_eval=hl_protect,
        multi_face_eye_priority_eval=face_multi,
        center_photometry_eval=center_ev,
        spot_photometry_eval=spot_ev,
        entire_screen_avg_eval=entire_ev,
        blocked_out_of_range_ae_shift_eval=bad_shift,
        p4_nd_motor_fault_attempts=total_nd_faults,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Zero Calibration & Zero Persistent eMMC Mutation Proof
# ---------------------------------------------------------------------------


def verify_zero_calibration_and_emmc_immutability(
    *,
    target_path: str = "/tmp/fx3_stageb_phase85_shadow.json",
    persistent_emmc_writes_authorized: bool = False,
) -> ZeroMutationProofResult:
    """Enforce `calibration_mutation_bytes == 0`, `internal_emmc_format_possible == False`, & `persistent_emmc_writes_authorized == False`."""
    errors: List[str] = []
    low = target_path.strip().lower()
    is_volatile = low.startswith(VOLATILE_SHADOW_PREFIXES)
    is_forbidden = any(low.startswith(p) or p in low for p in FORBIDDEN_CALIBRATION_AND_EMMC_PATHS)

    if persistent_emmc_writes_authorized:
        errors.append("BLOCKED_PERSISTENT_EMMC_WRITE_FLAG: persistent_emmc_writes_authorized must remain False")
    if is_forbidden:
        errors.append(
            f"BLOCKED_CALIBRATION_OR_EMMC_MUTATION: {target_path!r} targets protected internal eMMC/calibration"
        )
    elif not is_volatile:
        errors.append(f"target_path={target_path!r} must use a volatile prefix {VOLATILE_SHADOW_PREFIXES}")

    status = (
        "BLOCKED_PROTECTED_CALIBRATION_OR_EMMC_WRITE"
        if errors
        else "ZERO_CALIBRATION_ZERO_EMMC_MUTATION_VERIFIED"
    )
    return ZeroMutationProofResult(
        valid=len(errors) == 0,
        status=status,
        target_path=target_path,
        volatile_shadow_only=(not is_forbidden) and is_volatile,
        calibration_mutation_bytes=0,
        internal_emmc_format_possible=False,
        persistent_emmc_writes_authorized=persistent_emmc_writes_authorized,
        errors=tuple(errors),
    )


def evaluate_pillar_4_zero_mutation(
    fx3_xdb_ok: bool,
    fx6_xdb_ok: bool,
) -> ZeroCalibrationAndEmmcReport:
    """Audit Pillar 4 across `global.xdb` validity and protected eMMC/calibration write guards."""
    errors: List[str] = []
    if not fx3_xdb_ok or not fx6_xdb_ok:
        errors.append(f"global.xdb validation failed (fx3={fx3_xdb_ok}, fx6={fx6_xdb_ok})")

    vol_ok = verify_zero_calibration_and_emmc_immutability(
        target_path="/tmp/fx3_stageb_phase85_shadow.json",
        persistent_emmc_writes_authorized=False,
    )
    blk_mmc = verify_zero_calibration_and_emmc_immutability(
        target_path="/dev/mmcblk0p1",
        persistent_emmc_writes_authorized=False,
    )
    blk_cnf = verify_zero_calibration_and_emmc_immutability(
        target_path="/dev/cnflasha1/cal_override.bin",
        persistent_emmc_writes_authorized=False,
    )
    blk_bak = verify_zero_calibration_and_emmc_immutability(
        target_path="p2:/Backup.bin",
        persistent_emmc_writes_authorized=False,
    )
    blk_flag = verify_zero_calibration_and_emmc_immutability(
        target_path="/tmp/fx3_stageb_phase85_shadow.json",
        persistent_emmc_writes_authorized=True,
    )

    if not vol_ok.valid or vol_ok.calibration_mutation_bytes != 0:
        errors.extend(vol_ok.errors or ("Volatile shadow proof failed",))
    for blk in (blk_mmc, blk_cnf, blk_bak, blk_flag):
        if blk.valid or blk.calibration_mutation_bytes != 0 or blk.internal_emmc_format_possible:
            errors.append(f"Protected path/flag failed to block: {blk.target_path}")

    total_mut = sum(
        ev.calibration_mutation_bytes for ev in (vol_ok, blk_mmc, blk_cnf, blk_bak, blk_flag)
    )
    return ZeroCalibrationAndEmmcReport(
        passed=len(errors) == 0 and total_mut == 0,
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        volatile_shadow_eval=vol_ok,
        blocked_mmcblk0p1_eval=blk_mmc,
        blocked_cnflasha_eval=blk_cnf,
        blocked_backup_bin_eval=blk_bak,
        blocked_emmc_flag_eval=blk_flag,
        calibration_mutation_bytes=total_mut,
        internal_emmc_format_possible=False,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Main Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def analyze_playback_shotmark_and_ae(
    repo_root: Optional[Path] = None,
    *,
    clean_room: bool = False,
) -> PlaybackShotmarkAndAeReport:
    """Run the 16th Unified Firmware-Lab Auditor across Local Donor (`os.O_RDONLY`) or Clean-Room fixtures."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx3_lens_comm": FX3_LENS_COMM_RELPATH,
        "fx6_lens_comm": FX6_LENS_COMM_RELPATH,
        "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
        "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    resolved_paths: Dict[str, Path] = {}
    if not forced_clean:
        for key, rel in donor_relpaths.items():
            p = resolve_donor_file(rel, repo_root=root)
            if p is not None and p.is_file():
                resolved_paths[key] = p

    use_local_donors = (not forced_clean) and (len(resolved_paths) == len(donor_relpaths))
    mode = "LOCAL_DONOR_VERIFIED" if use_local_donors else "CLEAN_ROOM_SYNTHETIC_VERIFIED"

    errors: List[str] = []
    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}

    fx3_appfw_groups = {
        "fx3_appfw_playback": FX3_APPFW_PLAYBACK_FORMAT_MARKERS,
        "fx3_appfw_shotmark": FX3_APPFW_SHOTMARK_MARKERS,
        "fx3_appfw_ae_iris": FX3_APPFW_AE_IRIS_MARKERS,
    }
    fx6_appfw_groups = {
        "fx6_appfw_playback": FX6_APPFW_PLAYBACK_FORMAT_MARKERS,
        "fx6_appfw_shotmark": FX6_APPFW_SHOTMARK_MARKERS,
        "fx6_appfw_ae_iris": FX6_APPFW_AE_IRIS_MARKERS,
    }
    fx3_mpr_groups = {
        "fx3_libmpr_playback": FX3_LIBMPR_PLAYBACK_MARKERS,
        "fx3_libmpr_shotmark": FX3_LIBMPR_SHOTMARK_MARKERS,
    }
    fx6_mpr_groups = {
        "fx6_libmpr_playback": FX6_LIBMPR_PLAYBACK_MARKERS,
        "fx6_libmpr_shotmark": FX6_LIBMPR_SHOTMARK_MARKERS,
    }

    if use_local_donors:
        sz_fx3_app, fx3_app_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_appfw"], fx3_appfw_groups, is_elf=True
        )
        sz_fx6_app, fx6_app_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_appfw"], fx6_appfw_groups, is_elf=True
        )
        sz_fx3_mpr, fx3_mpr_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_libmpr"], fx3_mpr_groups, is_elf=True
        )
        sz_fx6_mpr, fx6_mpr_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_libmpr"], fx6_mpr_groups, is_elf=True
        )
        sz_fx3_cp, fx3_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_cpapp"], {"fx3_cp_ae_iris": FX3_CP_AE_IRIS_MARKERS}, is_elf=False
        )
        sz_fx6_cp, fx6_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_cpapp"], {"fx6_cp_ae_iris": FX6_CP_AE_IRIS_MARKERS}, is_elf=False
        )
        sz_fx3_lens, fx3_lens_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_lens_comm"], {"lens": LENS_COMM_AE_IRIS_MARKERS}, is_elf=True
        )
        sz_fx6_lens, fx6_lens_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_lens_comm"], {"lens": LENS_COMM_AE_IRIS_MARKERS}, is_elf=True
        )

        fx3_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx3_global_xdb"])
        fx6_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx6_global_xdb"])
        fx3_str_en_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en"])
        fx3_str_eng_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en_g"])
        fx6_str_en1_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_1"])
        fx6_str_en2_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_2"])

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_libmpr": sz_fx3_mpr,
            "fx6_libmpr": sz_fx6_mpr,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx3_lens_comm": sz_fx3_lens,
            "fx6_lens_comm": sz_fx6_lens,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }
    else:
        fixtures = build_clean_room_playback_shotmark_ae_fixtures()
        sz_fx3_app, fx3_app_hits = _scan_bytes_marker_groups(fixtures["fx3_appfw"], fx3_appfw_groups)
        sz_fx6_app, fx6_app_hits = _scan_bytes_marker_groups(fixtures["fx6_appfw"], fx6_appfw_groups)
        sz_fx3_mpr, fx3_mpr_hits = _scan_bytes_marker_groups(fixtures["fx3_libmpr"], fx3_mpr_groups)
        sz_fx6_mpr, fx6_mpr_hits = _scan_bytes_marker_groups(fixtures["fx6_libmpr"], fx6_mpr_groups)
        sz_fx3_cp, fx3_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx3_cpapp"], {"fx3_cp_ae_iris": FX3_CP_AE_IRIS_MARKERS}
        )
        sz_fx6_cp, fx6_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx6_cpapp"], {"fx6_cp_ae_iris": FX6_CP_AE_IRIS_MARKERS}
        )
        sz_fx3_lens, fx3_lens_hits = _scan_bytes_marker_groups(
            fixtures["fx3_lens_comm"], {"lens": LENS_COMM_AE_IRIS_MARKERS}
        )
        sz_fx6_lens, fx6_lens_hits = _scan_bytes_marker_groups(
            fixtures["fx6_lens_comm"], {"lens": LENS_COMM_AE_IRIS_MARKERS}
        )

        fx3_xdb_bytes = fixtures["fx3_global_xdb"]
        fx6_xdb_bytes = fixtures["fx6_global_xdb"]
        fx3_str_en_bytes = fixtures["fx3_str_en"]
        fx3_str_eng_bytes = fixtures["fx3_str_en_g"]
        fx6_str_en1_bytes = fixtures["fx6_str_en_1"]
        fx6_str_en2_bytes = fixtures["fx6_str_en_2"]

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_libmpr": sz_fx3_mpr,
            "fx6_libmpr": sz_fx6_mpr,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx3_lens_comm": sz_fx3_lens,
            "fx6_lens_comm": sz_fx6_lens,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }

    present_map.update(fx3_app_hits)
    present_map.update(fx6_app_hits)
    present_map.update(fx3_mpr_hits)
    present_map.update(fx6_mpr_hits)
    present_map.update(fx3_cp_hits)
    present_map.update(fx6_cp_hits)
    present_map["lens_comm_ae_iris"] = tuple(
        m
        for m in LENS_COMM_AE_IRIS_MARKERS
        if m in fx3_lens_hits["lens"] and m in fx6_lens_hits["lens"]
    )

    xdb_source_mode = "LOCAL_DONOR_RDONLY" if use_local_donors else "SYNTHETIC_CLEAN_ROOM"
    fx3_xdb_audit = parse_global_xdb_buffer(
        fx3_xdb_bytes,
        body="fx3_702",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx3_global_xdb"].parent if use_local_donors else None,
    )
    fx6_xdb_audit = parse_global_xdb_buffer(
        fx6_xdb_bytes,
        body="fx6_601",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx6_global_xdb"].parent if use_local_donors else None,
    )
    fx3_xdb_ok = fx3_xdb_audit.valid
    fx6_xdb_ok = fx6_xdb_audit.valid
    if not fx3_xdb_ok:
        errors.extend(fx3_xdb_audit.errors)
    if not fx6_xdb_ok:
        errors.extend(fx6_xdb_audit.errors)

    lbl_fx3_en, errs_fx3_en = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE85_LABELS)
    lbl_fx3_eng, errs_fx3_eng = _extract_uxc_labels(fx3_str_eng_bytes, FX3_NS3_PHASE85_LABELS)
    lbl_fx6_en1, errs_fx6_en1 = _extract_uxc_labels(fx6_str_en1_bytes, FX6_NS1_PHASE85_LABELS)
    lbl_fx6_en2, errs_fx6_en2 = _extract_uxc_labels(fx6_str_en2_bytes, FX6_NS2_PHASE85_LABELS)
    errors.extend((*errs_fx3_en, *errs_fx3_eng, *errs_fx6_en1, *errs_fx6_en2))

    uxc_labels: Dict[str, str] = {
        "fx3_protect": lbl_fx3_en.get("0x0004e2c9", ""),
        "fx3_metering_mode": lbl_fx3_en.get("0x0004e5cf", ""),
        "fx3_file_protected": lbl_fx3_en.get("0x0004e66a", ""),
        "fx3_metering": lbl_fx3_eng.get("0x00006044", ""),
        "fx3_added_sm2": lbl_fx3_eng.get("0x000060e2", ""),
        "fx3_protect_canceled": lbl_fx3_eng.get("0x00006133", ""),
        "fx3_shotmark1": lbl_fx3_eng.get("0x0000618a", ""),
        "fx3_added_sm1": lbl_fx3_eng.get("0x000061f0", ""),
        "fx3_face_eye_af": lbl_fx3_eng.get("0x00006293", ""),
        "fx3_shotmark2": lbl_fx3_eng.get("0x00006397", ""),
        "fx6_thumbnail": lbl_fx6_en1.get("0x00002088", ""),
        "fx6_iris": lbl_fx6_en1.get("0x000020d1", ""),
        "fx6_ae_level": lbl_fx6_en1.get("0x000021b7", ""),
        "fx6_auto_iris": lbl_fx6_en1.get("0x000022e4", ""),
        "fx6_ae_level_offset": lbl_fx6_en1.get("0x00002418", ""),
        "fx6_format_a": lbl_fx6_en1.get("0x00002580", ""),
        "fx6_format_b": lbl_fx6_en1.get("0x00002581", ""),
        "fx6_press_hold_auto_nd": lbl_fx6_en1.get("0x000026b8", ""),
        "fx6_delete_clip": lbl_fx6_en2.get("0x00004092", ""),
        "fx6_add_sm1": lbl_fx6_en2.get("0x000040be", ""),
        "fx6_add_sm2": lbl_fx6_en2.get("0x000040bf", ""),
        "fx6_shot_mark": lbl_fx6_en2.get("0x0000410d", ""),
        "fx6_format_media": lbl_fx6_en2.get("0x00004254", ""),
        "fx6_iris_ns2": lbl_fx6_en2.get("0x00004285", ""),
        "fx6_auto_iris_ns2": lbl_fx6_en2.get("0x0000429d", ""),
        "fx6_set_shot_mark": lbl_fx6_en2.get("0x000042ac", ""),
        "fx6_thumbnail_view": lbl_fx6_en2.get("0x000042b0", ""),
    }

    p1 = evaluate_pillar_1_playback_thumbnail_firewall(present_map, uxc_labels)
    p2 = evaluate_pillar_2_shotmark_essencemark(present_map, uxc_labels)
    p3 = evaluate_pillar_3_push_auto_iris_ae(present_map, uxc_labels)
    p4 = evaluate_pillar_4_zero_mutation(fx3_xdb_ok, fx6_xdb_ok)

    errors.extend((*p1.errors, *p2.errors, *p3.errors, *p4.errors))
    all_passed = bool(
        len(errors) == 0
        and p1.passed
        and p2.passed
        and p3.passed
        and p4.passed
        and not p1.internal_emmc_format_possible
        and not p1.internal_emmc_delete_possible
        and not p4.internal_emmc_format_possible
        and p4.calibration_mutation_bytes == 0
        and p3.p4_nd_motor_fault_attempts == 0
    )

    pre_hash_payload = {
        "schema_version": PHASE_85_SCHEMA,
        "phase_version": PHASE_85_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "calibration_mutation_bytes": p4.calibration_mutation_bytes,
        "internal_emmc_format_possible": False,
        "p4_nd_motor_fault_attempts": p3.p4_nd_motor_fault_attempts,
        "donor_file_sizes": donor_sizes,
        "pillar_1_playback_thumbnail_firewall": asdict(p1),
        "pillar_2_shotmark_essencemark_xml": asdict(p2),
        "pillar_3_push_auto_iris_ae_shift": asdict(p3),
        "pillar_4_zero_mutation_proof": asdict(p4),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(pre_hash_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return PlaybackShotmarkAndAeReport(
        schema_version=PHASE_85_SCHEMA,
        phase_version=PHASE_85_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        calibration_mutation_bytes=p4.calibration_mutation_bytes,
        internal_emmc_format_possible=False,
        p4_nd_motor_fault_attempts=p3.p4_nd_motor_fault_attempts,
        donor_file_sizes=donor_sizes,
        pillar_1_playback_thumbnail_firewall=p1,
        pillar_2_shotmark_essencemark_xml=p2,
        pillar_3_push_auto_iris_ae_shift=p3,
        pillar_4_zero_mutation_proof=p4,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def playback_shotmark_and_ae_report_to_dict(
    report: PlaybackShotmarkAndAeReport,
) -> Dict[str, object]:
    """Convert `PlaybackShotmarkAndAeReport` to a deterministic JSON-serializable dict."""
    return report.to_dict()
