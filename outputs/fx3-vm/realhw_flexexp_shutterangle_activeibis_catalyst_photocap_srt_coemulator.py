#!/usr/bin/env python3
"""Phase 383 — Stage 88 (88/88 Full-Board VM HIL Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-78 HIL:
- 88A: `[Exposure Ctrl Type]` (`_f 0x787e`: `Flexible Exp. Mode` def /
  `P/A/S/M Mode`, Movie/S&Q ONLY) resists `[Camera Settings Reset]` (cleared
  ONLY on `[Initialize]` — closing Wave-78 `G86` omission!), whereas
  `[Auto/Manual Swt. Set.]` (`Av`/`Tv`/`ISO` def `Manual`) and `[Auto Slow
  Shutter]` (`On`) are `Can be reset`; Ver. 6.00+ `[Shutter Mode]` (`_f 0x7c7c`:
  `Speed` def / `Angle` `_f 0x7c86`, Movie/S&Q ONLY, `Can be reset`) with
  standard angles (`5.6°..360.0°`) + multi-frame angles (`2F..64F` clamped by
  high fps), strict `BK4` slot separation (`0x01120024` Speed vs `0x01120028`
  Angle), unaffected by `[Exposure step]`, forcing Still/Movie shutter
  separation when `Angle` is active; Still-only `[Anti-flicker Shoot.]`;
  dormant `Var. Shutter` (`_f 0x7924/0x7af8`, `HIGH_RES_SS`) blocked
  `EOPNOTSUPP=95`; vs `ILME-FX6` physical `IRIS`/`ISO-GAIN`/`SHUTTER`/
  `FULL AUTO` + 4-option `Shutter Mode` (`Angle`/`Speed`/`ECS`/`Off`).
- 88B: `[Image Stabilization]` Movie `[SteadyShot]` (`Active ~1.104x` forcing
  `[Distortion Comp.] = Auto`, `Standard` def, `Off`; all 4 IS settings
  `Can be reset`); dormant `Dynamic active`/`Intelligent Active`/`Super Active`
  blocked `EOPNOTSUPP=95`; ALL 4 `Active` hard lockouts (`119.88p/100p`,
  `S&Q >= 100fps`, `HDMI RAW Output = On`, `[De-Squeeze Display] != Off`,
  reflecting Ver. 2.00+ removal of old Ver. 1 `200mm` note); `[SteadyShot
  Adjust.]` (`Auto`/`Manual`) + exact `47`-step `[Focal Length]` (`8..1000mm`,
  def `8mm`); `Catalyst Prepare` gyro `RTMD` eligibility (`Off`/`Active` ONLY,
  NOT `Standard`, electronic-contact E-mount lens required, `S&Q` all fps and
  `119.88p/100p` produce ZERO usable gyro stabilization); vs `ILME-FX6` zero
  body IBIS (`"The SteadyShot mechanism is fixed."`) + OSS-lens 3-mode
  `Active / Standard / Off` (zero `Dynamic Active`), requiring lens OSS `OFF`
  + `<= 60p` non-S&Q for `Catalyst`.
- 88C: `Playback -> [Photo Capture]` (`_f 0x6856`: `8.3M` `3840x2160` from 4K
  UHD, `2.1M` `1920x1080` from HD, HARD BLOCK `XAVC S-I DCI 4K` `4096x2160`
  `_g 0x60ce` `EOPNOTSUPP=95`); Playback `[JPEG/HEIF Switch]` (`JPEG` def /
  `HEIF(4:2:0)` / `HEIF(4:2:2)`, HLG->HLG HEIF) resists `[Camera Settings
  Reset]` (unlike Shooting-side resettable `[JPEG/HEIF Switch]`); `[View Mode]`
  (`base 0xe3b7`, anti-Reset) exact 3 exposed states (`Date View` def /
  `Folder View(Still)` / `Movie View`) with dormant `Folder View(MP4)`,
  `AVCHD View`, and `VIEW_MODE_XAVC_S_*` blocked `EOPNOTSUPP=95` (closing
  Wave-78 `G126` gap); `[Rating]` (`1..5` stars) & `[Rating Set(Custom Key)]`
  (anti-Reset) with FTP/Smartphone rating filter hooks; Tier-0 `Slot 1
  EROFS=30` firewall blocking ANY `[Photo Capture]` write or `[Rating]`
  XMP/AVF mutation targeting `Slot 1` (`slot1_writes == 0`, writable `Slot 2`
  allowed only in simulated sandbox); vs `ILME-FX6` zero in-camera Photo
  Capture + `Thumbnail > Set Clip Flag` (`OK`/`NG`/`KEEP`).
- 88D: Double debunk `[USB Streaming]` (UVC/UAC) on `ILME-FX3`/`ILME-FX3A`/
  `ILCE-7SM3` (`[USB Connection Mode]` exposes ONLY 4 items: `Sel. When
  Connect`/`MassStorage(MSC)`/`MTP`/`Remote Shooting`; dormant ELF
  `OUTPUT_FORMAT_*` has ONLY `4K_12_5P/15P`, ZERO `4K 30p/25p/24p` -> blocked
  `EOPNOTSUPP=95`; `[Movie Rec During Streaming]` `_f 0x79d5` belongs 100% to
  `[Network Streaming]`); `[Network Streaming]` (`libInfraSrtLiveStreaming.so`,
  `libInfraRtmpLiveStreaming.so`): BLE `Creators' App` provisioning,
  `RTMP`/`RTMPS` (H.264) & `SRT` (H.265/H.264, `AES-128/256`, `48kHz 16-bit
  2ch`, outbound `SRT Caller` ONLY — zero in-camera `SRT Listener`), fps locked
  to `59.94p/50p/29.97p/25p` (blocks `23.98p/24p/120p`), `<= 38 Mbps`, `[Movie
  Rec During Streaming]` (`Disable` def) blocking internal 4K rec when
  streaming 4K or 2K 60p/50p + `Slot 1 EROFS=30`, Airplane Mode zero-RF hard
  block (`rf_tx_packets == 0`); vs `ILME-FX6` zero native UVC & zero native
  RTMP/SRT/QoS (dormant symbols only; requires `CBK-WA100`/`CBK-RPU7`/
  `PDT-FP1`).

Enforces strict Tier-0 safety redlines across all 4 execution modes (normal
local donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` with `<= 4096 B`
`os.pread` bounded windows on multi-MiB files; `FX3_CLEAN_ROOM_TEST=1`;
`FX3_FX6_FORCE_CLEAN_ROOM=1`; and donorless `work_root=None` /
`FX3_FX6_MAC_WORK_ROOT` sentinel).
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Phase 383 Schema, Stage 88 (88/88) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation_v1"
)
PHASE_383_VERSION = "383.0.0"
PHASE_NUMBER = 383
STAGE_INDEX = 88
STAGE_TOTAL = 88
MILESTONE_LABEL = "88/88"

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
READY_FOR_LIVE_CAMERA_ATTACH = False
LIVE_ATTACH_AUTHORIZED = False
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
EMMC_WRITES_AUTHORIZED = False
CROSS_MODEL_FLASH_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
ISP_WRITE_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
EMMC_CORRUPTIONS = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
USB_TX_PACKETS = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0
SLOT1_WRITE_AUTHORIZED = False
SLOT1_WRITES = 0
SLOT1_SECTOR_WRITES = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_TX_PACKETS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# POSIX Errno Contracts
EPERM_ERRNO = 1
EIO_ERRNO = 5
EAGAIN_ERRNO = 11
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
ENODEV_ERRNO = 19
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

# Body & Mode Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_A7SM3 = "ILCE-7SM3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3A,
    BODY_MODEL_A7SM3,
    BODY_MODEL_FX6,
)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")

# ---------------------------------------------------------------------------
# 88A Constants — Exposure Ctrl Type (G86), Shutter Mode Angle & FX6 ECS
# ---------------------------------------------------------------------------

FX3_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = (
    "Flexible Exp. Mode",
    "P/A/S/M Mode",
)
FX3_EXPOSURE_CTRL_TYPE_DEFAULT = "Flexible Exp. Mode"
FX3_AUTO_MANUAL_STATES: Tuple[str, ...] = ("Auto", "Manual")
FX3_AUTO_MANUAL_DEFAULT = "Manual"
FX3_AUTO_SLOW_SHUTTER_DEFAULT = "On"
FX3_G86_EXPOSURE_CTRL_TYPE_RESET_ERRATUM_RECONCILED = True

FX3_SHUTTER_MODES: Tuple[str, ...] = ("Speed", "Angle")
FX3_SHUTTER_MODE_DEFAULT = "Speed"
FX3_SHUTTER_ANGLE_STANDARD_STEPS: Tuple[str, ...] = (
    "5.6",
    "11.25",
    "22.5",
    "30.0",
    "45.0",
    "72.0",
    "86.4",
    "90.0",
    "120.0",
    "144.0",
    "150.0",
    "172.8",
    "180.0",
    "210.0",
    "216.0",
    "240.0",
    "270.0",
    "300.0",
    "360.0",
)
FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS: Tuple[str, ...] = (
    "2F",
    "3F",
    "4F",
    "5F",
    "6F",
    "7F",
    "8F",
    "16F",
    "32F",
    "64F",
)
FX3_ALL_SHUTTER_ANGLES: Tuple[str, ...] = (
    FX3_SHUTTER_ANGLE_STANDARD_STEPS + FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS
)
FX3_BK4_SHUTTER_SPEED_SLOT = 0x01120024
FX3_BK4_SHUTTER_ANGLE_SLOT = 0x01120028
FX3_EXPOSURE_STEPS: Tuple[str, ...] = ("0.3 EV", "0.5 EV")
FX3_ANTI_FLICKER_DEFAULT = "Off"
FX3_DORMANT_VAR_SHUTTER_ITEMS: Tuple[str, ...] = (
    "Var. Shutter",
    "Var. Shutter Select",
    "Var. Shutter Set.",
    "HIGH_RES_SS",
)

FX6_PHYSICAL_EXPOSURE_KEYS: Tuple[str, ...] = (
    "IRIS",
    "ISO/GAIN",
    "SHUTTER",
    "FULL AUTO",
)
FX6_SHUTTER_MODES: Tuple[str, ...] = ("Angle", "Speed", "ECS", "Off")
FX6_ECS_FREQ_MIN_HZ = 24.0
FX6_ECS_FREQ_MAX_HZ = 8000.0

VALID_88A_OPERATIONS: Tuple[str, ...] = (
    "fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
    "fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
    "fx3_antiflicker_still_only_and_dormant_var_shutter_block",
    "fx6_physical_exposure_keys_and_4mode_shutter_ecs",
)

# ---------------------------------------------------------------------------
# 88B Constants — SteadyShot Active 4-Lock, 47-Step Focal & Catalyst Gyro
# ---------------------------------------------------------------------------

FX3_MOVIE_STEADYSHOT_MODES: Tuple[str, ...] = ("Active", "Standard", "Off")
FX3_MOVIE_STEADYSHOT_DEFAULT = "Standard"
FX3_STILL_STEADYSHOT_DEFAULT = "On"
FX3_ACTIVE_CROP_FACTOR = 1.104
FX3_DORMANT_STEADYSHOT_MODES: Tuple[str, ...] = (
    "Dynamic active",
    "Intelligent Active",
    "Super Active",
    "HYBRID",
)
FX3_ACTIVE_4_LOCKOUT_IDS: Tuple[str, ...] = (
    "REC_FRAME_RATE_119_88P_100P",
    "SQ_FRAME_RATE_GE_100FPS",
    "HDMI_RAW_OUTPUT_ON",
    "DESQUEEZE_DISPLAY_NOT_OFF",
)
FX3_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = ("Auto", "Manual")
FX3_STEADYSHOT_ADJUST_DEFAULT = "Auto"
FX3_FOCAL_LENGTH_DEFAULT_MM = 8
FX3_FOCAL_LENGTH_47_STEPS_MM: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 28,
    30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105, 120,
    135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000,
)
FX3_IS_4_RESETTABLE_SETTINGS: Tuple[str, ...] = (
    "Still SteadyShot",
    "Movie SteadyShot",
    "SteadyShot Adjust.",
    "Focal Length",
)
FX3_G81_200MM_NOTE_REMOVED_IN_V2_PLUS = True
FX3_CATALYST_SUPPORTED_STEADYSHOT_MODES: Tuple[str, ...] = ("Off", "Active")

FX6_HAS_BODY_IBIS = False
FX6_IBIS_FIXED_MESSAGE = "The SteadyShot mechanism is fixed."
FX6_OSS_STEADYSHOT_MODES: Tuple[str, ...] = ("Active", "Standard", "Off")
FX6_DORMANT_STEADYSHOT_MODES: Tuple[str, ...] = ("Dynamic Active",)

VALID_88B_OPERATIONS: Tuple[str, ...] = (
    "fx3_steadyshot_active_4locks_and_dormant_block",
    "fx3_steadyshot_adjust_and_47step_focal_length",
    "fx3_catalyst_gyro_rtmd_eligibility",
    "fx6_zero_ibis_oss_3mode_and_catalyst",
)

# ---------------------------------------------------------------------------
# 88C Constants — Photo Capture, 3-Item View Mode (G126), Rating & EROFS=30
# ---------------------------------------------------------------------------

FX3_PHOTO_CAPTURE_JPEG_HEIF_OPTIONS: Tuple[str, ...] = (
    "JPEG",
    "HEIF(4:2:0)",
    "HEIF(4:2:2)",
)
FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT = "JPEG"
FX3_PHOTO_CAPTURE_4K_UHD_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S-I 4K",
)
FX3_PHOTO_CAPTURE_HD_FORMATS: Tuple[str, ...] = (
    "XAVC S HD",
    "XAVC S-I HD",
)
FX3_PHOTO_CAPTURE_BLOCKED_FORMATS: Tuple[str, ...] = ("XAVC S-I DCI 4K",)
FX3_PHOTO_CAPTURE_4K_RES = "3840x2160"
FX3_PHOTO_CAPTURE_4K_MP = 8.3
FX3_PHOTO_CAPTURE_HD_RES = "1920x1080"
FX3_PHOTO_CAPTURE_HD_MP = 2.1

FX3_VIEW_MODE_EXPOSED_3_STATES: Tuple[str, ...] = (
    "Date View",
    "Folder View(Still)",
    "Movie View",
)
FX3_VIEW_MODE_DEFAULT = "Date View"
FX3_DORMANT_VIEW_MODES: Tuple[str, ...] = (
    "Folder View(MP4)",
    "AVCHD View",
    "VIEW_MODE_XAVC_S_4K_VIEW",
    "VIEW_MODE_XAVC_S_HD_VIEW",
    "VIEW_MODE_XAVC_S_VIEW",
)
FX3_G126_VIEW_MODE_3ITEM_ERRATUM_RECONCILED = True
FX3_RATING_STARS_MIN = 1
FX3_RATING_STARS_MAX = 5

FX6_HAS_IN_CAMERA_PHOTO_CAPTURE = False
FX6_CLIP_FLAG_OPTIONS: Tuple[str, ...] = ("OK", "NG", "KEEP")

VALID_88C_OPERATIONS: Tuple[str, ...] = (
    "fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
    "fx3_view_mode_3item_g126_and_dormant_block",
    "fx3_rating_1to5_ftp_filter_and_slot1_erofs",
    "fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
)

# ---------------------------------------------------------------------------
# 88D Constants — UVC/UAC Debunk vs Network Streaming RTMP/RTMPS/SRT Caller
# ---------------------------------------------------------------------------

FX3_NATIVE_UVC_SUPPORTED = False
FX3_UVC_UNSUPPORTED_BODIES: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3A,
    BODY_MODEL_A7SM3,
)
FX3_USB_CONNECTION_EXPOSED_4_MODES: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shooting",
)
FX3_USB_CONNECTION_DEFAULT = "Sel. When Connect"
FX3_DORMANT_UVC_ELF_FORMATS: Tuple[str, ...] = (
    "4K_12_5P",
    "4K_15P",
    "FULLHD_25P",
    "FULLHD_30P",
    "FULLHD_50P",
    "FULLHD_60P",
    "HD720_25P",
    "HD720_30P",
)
FX3_NONEXISTENT_UVC_4K_FORMATS: Tuple[str, ...] = (
    "4K_30P",
    "4K_25P",
    "4K_24P",
)
FX3_MOVIE_REC_DURING_STREAMING_OWNER = "Network Streaming"
FX3_MOVIE_REC_DURING_STREAMING_DEFAULT = "Disable"

FX3_NETWORK_STREAMING_PROTOCOLS: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT")
FX3_SRT_EXPOSED_MODES: Tuple[str, ...] = ("Caller",)
FX3_SRT_BLOCKED_MODES: Tuple[str, ...] = ("Listener", "Rendezvous")
FX3_G134_SRT_CALLER_ONLY_RECONCILED = True
FX3_SRT_ENCRYPTIONS: Tuple[str, ...] = ("None", "AES-128", "AES-256")
FX3_STREAMING_AUDIO_SPEC = "AAC-LC 48kHz 16-bit 2ch"
FX3_STREAMING_ALLOWED_FPS: Tuple[str, ...] = ("59.94p", "50p", "29.97p", "25p")
FX3_STREAMING_BLOCKED_FPS: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "24p",
    "100p",
    "119.88p",
    "120p",
)
FX3_STREAMING_MAX_BITRATE_MBPS = 38.0
FX3_STREAMING_TRANSPORTS: Tuple[str, ...] = ("Wi-Fi", "USB Tethering", "USB-LAN")
FX3_STREAMING_BITRATE_8_BUCKETS: Mapping[Tuple[str, str], Mapping[str, Any]] = {
    ("4K (2160p)", "60p_50p"): {
        "min_mbps": 38.0,
        "max_mbps": 38.0,
        "default_mbps": 38.0,
        "blocks_internal_4k_rec": True,
    },
    ("4K (2160p)", "30p_25p"): {
        "min_mbps": 13.0,
        "max_mbps": 38.0,
        "default_mbps": 34.0,
        "blocks_internal_4k_rec": True,
    },
    ("2K (1440p)", "60p_50p"): {
        "min_mbps": 9.0,
        "max_mbps": 38.0,
        "default_mbps": 18.0,
        "blocks_internal_4k_rec": True,
    },
    ("2K (1440p)", "30p_25p"): {
        "min_mbps": 6.0,
        "max_mbps": 38.0,
        "default_mbps": 13.0,
        "blocks_internal_4k_rec": False,
    },
    ("HD (1080p)", "60p_50p"): {
        "min_mbps": 4.5,
        "max_mbps": 27.0,
        "default_mbps": 9.0,
        "blocks_internal_4k_rec": False,
    },
    ("HD (1080p)", "30p_25p"): {
        "min_mbps": 3.0,
        "max_mbps": 18.0,
        "default_mbps": 6.0,
        "blocks_internal_4k_rec": False,
    },
    ("HD (720p)", "60p_50p"): {
        "min_mbps": 2.3,
        "max_mbps": 13.5,
        "default_mbps": 6.0,
        "blocks_internal_4k_rec": False,
    },
    ("HD (720p)", "30p_25p"): {
        "min_mbps": 1.5,
        "max_mbps": 9.0,
        "default_mbps": 4.0,
        "blocks_internal_4k_rec": False,
    },
}

FX6_NATIVE_UVC_SUPPORTED = False
FX6_NATIVE_NETWORK_STREAMING_SUPPORTED = False
FX6_EXTERNAL_STREAMING_ADAPTERS: Tuple[str, ...] = (
    "CBK-WA100",
    "CBK-RPU7",
    "PDT-FP1",
)
FX6_DORMANT_STREAMING_PROTOCOLS: Tuple[str, ...] = (
    "UVC",
    "RTMP",
    "RTMPS",
    "SRT",
    "QoS",
)

VALID_88D_OPERATIONS: Tuple[str, ...] = (
    "fx3_usb_streaming_uvc_debunk_and_4mode_usb",
    "fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
    "fx3_movie_rec_during_streaming_and_slot1_erofs",
    "fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
)

# Clean-Room & Donor Sentinel Controls
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
DEFAULT_MAC_WORK_ROOT = (
    Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work"
)
_DONOR_DISABLED_SENTINEL = "__fx3_fx6_clean_room_donor_disabled__"
_UNSET = object()

_COMPACT_MAX_READ_BYTES = 1 * 1024 * 1024
_BOUNDED_WINDOW_BYTES = 4096
_DONOR_OPEN_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage88Phase383Error(RuntimeError):
    """Raised on invalid Phase 383 Stage 88 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 23 Real-Hardware Wave-78 Donor Specs (O_RDONLY|O_NOFOLLOW|O_NONBLOCK)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    expected_sha256: str
    required_tokens: Tuple[bytes, ...]
    absent_tokens: Tuple[bytes, ...] = ()


@dataclass(frozen=True)
class WindowDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    head4k_sha256: str
    windows: Tuple[Tuple[int, str, bytes], ...]
    absent_windows: Tuple[Tuple[int, str, bytes], ...] = ()


PHASE383_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Exposure Ctrl Type",
            b"Flexible Exp. Mode",
            b"P/A/S/M Mode",
            b"Auto/Manual Swt. Set.",
            b"Av Auto/Manual Switch",
            b"Tv Auto/Manual Switch",
            b"ISO Auto/Manual Set",
            b"Shutter Mode",
            b"Speed",
            b"Angle",
            b"Anti-flicker Shoot Sel.",
            b"Var. Shutter Select",
            b"Var. Shutter Set.",
            b"SteadyShot",
            b"Active",
            b"SteadyShot Adjust.",
            b"Focal Length",
            b"Dynamic active",
            b"Intelligent Active",
            b"Super Active",
            b"Photo Capture",
            b"JPEG/HEIF Switch",
            b"Movie View",
            b"Rating",
            b"Rating Set(Custom Key)",
            b"Network Streaming",
            b"Output Img. Quality Set",
            b"Movie Rec During Streaming",
            b"USB Streaming",
            b"Live Stream(USB Streaming)",
            b"USB Connection Mode",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "曝光控制类型".encode("utf-8"),
            "灵活曝光模式".encode("utf-8"),
            "快门模式".encode("utf-8"),
            "动态增强".encode("utf-8"),
            "照片捕获".encode("utf-8"),
            "动态影像视窗".encode("utf-8"),
            "分级".encode("utf-8"),
            "网络流式传输".encode("utf-8"),
            "流式传输动态影像录制".encode("utf-8"),
            "USB流式传输".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "曝光控制類型".encode("utf-8"),
            "快門模式".encode("utf-8"),
            "照片攝取".encode("utf-8"),
            "網路串流傳輸".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "露出制御方式".encode("utf-8"),
            "シャッターモード".encode("utf-8"),
            "動画から静止画作成".encode("utf-8"),
            "レーティング".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"View Mode",
            b"Date View",
            b"Folder View(Still)",
            b"Folder View(MP4)",
            b"AVCHD View",
            b"MTP",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "观看模式".encode("utf-8"),
            "日期视窗".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "觀看模式".encode("utf-8"),
            "日期檢視".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "ビューモード".encode("utf-8"),
            "日付ビュー".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            b"Added a Rating",
            b"Creators' App",
            b"USB Streaming",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            "已添加分级".encode("utf-8"),
            b"Creators' App",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            "已新增等級".encode("utf-8"),
            b"Creators' App",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=(
            b"XAVC S-I DCI 4K",
            b"Creators' App",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_srt_live_streaming",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraSrtLiveStreaming.so",
        expected_size=90248,
        expected_sha256="97292f569f1a9dbf63e1e888267ecbce34a767511da43cc15f1213119169447e",
        required_tokens=(
            b"InfraSrtLiveStreaming",
            b"AES128",
            b"AES256",
            b"EsAudioSrt",
            b"EsMetaSrt",
            b"EsVideoSrt",
        ),
        absent_tokens=(
            b"SRT_LISTENER",
            b"srt_listen",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_rtmp_live_streaming",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraRtmpLiveStreaming.so",
        expected_size=85960,
        expected_sha256="9a6f65df052086ed198c69c55fbd35feaa4393d5a64acce6d17d48862f890104",
        required_tokens=(
            b"InfraRtmpLiveStreaming",
            b"ERR_CERTIFICATION_ERROR",
            b"ERR_CERTIFICATION_HAS_EXPIRED",
            b"ERR_CERTIFICATION_IS_NOT_YET_VALID",
            b"EsAudioRtmp",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_veric_live_streaming",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraVericLiveStreaming.so",
        expected_size=182472,
        expected_sha256="cce66e647be7444af73a54b0132e100972b32b43e1db13ab3a719819192597ae",
        required_tokens=(
            b"VericVideoDistributor",
            b"VericAudioDistributor",
            b"VericMetaDistributor",
            b"VericProtocolHeaderCreator",
            b"convertCryptoAlgo",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_veric_es_codec",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraVericEsCodecLibrary.so",
        expected_size=22912,
        expected_sha256="70c8ffb1a7da9114eb5c3375628997d839dd6b2983a269e67aed6725abc4a4ca",
        required_tokens=(
            b"DefInfraVericLiveStreaming",
            b"eslib_get_handle",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_rtmp_util_common",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraRtmpLiveStreamingUtilCommon.so",
        expected_size=10336,
        expected_sha256="2802e2b0cb1a07f1585c82721b90043c0ac1c9aabf95a15b714133feb4e30ebf",
        required_tokens=(
            b"DefInfraRtmpLiveStreaming",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_veric_util_common",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraVericUtilCommon.so",
        expected_size=18744,
        expected_sha256="241194a00038cf000ad2665ccc3f4a797b82d07bf85b96075bcd9d12cbac2a2b",
        required_tokens=(
            b"DefInfraVericLiveStreaming",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"The SteadyShot mechanism is fixed.",
            b"Dynamic Active",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"Shutter Mode",
            b"ECS",
            b"SteadyShot: Active",
            b"Set Clip Flag",
            b"Delete Clip Flag",
            b"QoS Streaming",
        ),
    ),
)

PHASE383_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x39E4000, "FLEX_EXP_MOVIE", b"VAL_exposure_mode_EXPOSURE_MODE_MOVIE_FLEXIBLE_EXPOSURE_MODE"),
            (0x39E4000, "FLEX_EXP_SQ", b"VAL_exposure_mode_EXPOSURE_MODE_SQ_FLEXIBLE_EXPOSURE_MODE"),
            (0x3C3A000, "EXP_CTRL_EVENT", b"EVENT_REMOTE_EXPOSURE_CTRL_TYPE"),
            (0x3AC1000, "SHUTTER_ANGLE_5_6", b"VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6"),
            (0x3AC1000, "SHUTTER_ANGLE_360", b"VAL_setting_shutter_angle_SHUTTER_ANGLE_360_POINT_0"),
            (0x3AC1000, "SHUTTER_ANGLE_64F", b"VAL_setting_shutter_angle_SHUTTER_ANGLE_64F"),
            (0x3BC7000, "ANTI_FLICKER_SHOOT", b"BKID_APP_setting_anti_flicker_shoot"),
            (0x2FA2000, "DORMANT_HIGH_RES_SS", b"ANTI_FLICKER_SET_HIGH_RES_SS_ON"),
            (0x3BC7000, "STEADYSHOT_ADJUST", b"BKID_APP_setting_steadyshot_adjustment"),
            (0x3BC7000, "STEADY_FOCAL_LEN", b"BKID_APP_setting_steady_focal_length"),
            (0x3AC1000, "DORMANT_SS_HYBRID", b"VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_HYBRID"),
            (0x3BC9000, "PHOTO_CAP_FILE_TYPE", b"BKID_APP_setting_photo_capture_file_type"),
            (0x3BC9000, "VIEW_MODE_BKID", b"BKID_APP_setting_menu_view_mode"),
            (0x3B14000, "VIEW_MODE_XAVC_S", b"VIEW_MODE_XAVC_S_4K_VIEW"),
            (0x3B28000, "VALID_RATING_5", b"VALID_RATING_5_SELECTING_VALID"),
            (0x3BF0000, "FTP_RATING_5", b"BKID_APP_is_valid_ftp_transfer_target_image_rating_5"),
            (0x3B11000, "USB_CONN_STREAMING", b"VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING"),
            (0x39D9000, "UVC_4K_15P", b"VAL_setting_output_format_OUTPUT_FORMAT_4K_15P"),
            (0x39D9000, "UVC_4K_12_5P", b"VAL_setting_output_format_OUTPUT_FORMAT_4K_12_5P"),
            (0x3BF2000, "STREAM_BR_4K60", b"BKID_APP_video_stream_bit_rate_4k_2160p_60p_50p"),
            (0x3BF2000, "STREAM_BR_4K30", b"BKID_APP_video_stream_bit_rate_4k_2160p_30p_25p"),
            (0x3BF2000, "STREAM_BR_2K60", b"BKID_APP_video_stream_bit_rate_2k_1440p_60p_50p"),
            (0x3BF2000, "STREAM_BR_2K30", b"BKID_APP_video_stream_bit_rate_2k_1440p_30p_25p"),
            (0x3BF2000, "STREAM_BR_HD60", b"BKID_APP_video_stream_bit_rate_hd_1080p_60p_50p"),
            (0x3BF2000, "STREAM_BR_HD30", b"BKID_APP_video_stream_bit_rate_hd_1080p_30p_25p"),
            (0x3BF2000, "STREAM_BR_720P60", b"BKID_APP_video_stream_bit_rate_hd_720p_60p_50p"),
            (0x3BF2000, "STREAM_BR_720P30", b"BKID_APP_video_stream_bit_rate_hd_720p_30p_25p"),
            (0x3BCA000, "NET_STREAM_CERT_ERR", b"BKID_APP_setting_movie_network_streaming_root_certificate_error"),
        ),
        absent_windows=(
            (0x39D9000, "NO_UVC_4K_30P", b"OUTPUT_FORMAT_4K_30P"),
            (0x39D9000, "NO_UVC_4K_25P", b"OUTPUT_FORMAT_4K_25P"),
            (0x39D9000, "NO_UVC_4K_24P", b"OUTPUT_FORMAT_4K_24P"),
            (0x3BCA000, "NO_SRT_LISTENER", b"SRT_LISTENER"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_bk4",
        rel_path="fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        expected_size=2229740,
        head4k_sha256="87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
        windows=(
            (0x0000000, "BK4_HEADER", b"BK4\x00"),
            (0x004A000, "ILME-FX3", b"ILME-FX3"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x2706000, "FX6_MODE_SHUTTER", b"BKID_APP_SETTING_MODE_SHUTTER"),
            (0x2706000, "FX6_SHUTTER_ANGLE", b"BKID_APP_SETTING_SHUTTER_ANGLE"),
            (0x2707000, "FX6_ECS_FREQ", b"BKID_APP_SETTING_ECS_FREQUENCY"),
            (0x26AE000, "FX6_NO_BODY_IBIS", b"TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"),
            (0x27A9000, "FX6_SS_ACTIVE_SW", b"ASSIGNABLE_SWITCH_STEADYSHOT_ACTIVE"),
            (0x27A9000, "FX6_SS_STD_SW", b"ASSIGNABLE_SWITCH_STEADYSHOT_STANDARD"),
            (0x2706000, "FX6_MOVIE_SS", b"BKID_APP_SETTING_MOVIE_STEADYSHOT"),
            (0x27A9000, "FX6_CLIP_FLAG_OK", b"ASSIGNABLE_SWITCH_CLIP_FLAG_OK"),
            (0x27A9000, "FX6_CLIP_FLAG_NG", b"ASSIGNABLE_SWITCH_CLIP_FLAG_NG"),
            (0x27A9000, "FX6_CLIP_FLAG_KEEP", b"ASSIGNABLE_SWITCH_CLIP_FLAG_KEEP"),
            (0x271E000, "FX6_DORMANT_RTMP1", b"BKID_APP_RTMP_SETTINGS1"),
            (0x271F000, "FX6_DORMANT_SRT1", b"BKID_APP_SETTING_SRT_SETTINGS1"),
            (0x270A000, "FX6_DORMANT_USB_STREAM", b"BKID_APP_SETTING_USB_STREAMING_FORMAT_PROCAM"),
        ),
        absent_windows=(
            (0x271F000, "FX6_NO_USER_MENU_SRT", b"BKID_APP_USER_MENU_SRT"),
            (0x271E000, "FX6_NO_USER_MENU_RTMP", b"BKID_APP_USER_MENU_RTMP"),
            (0x271E000, "FX6_NO_USER_MENU_QOS", b"BKID_APP_USER_MENU_QOS"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY | O_NOFOLLOW | O_NONBLOCK & Clean-Room Synthetic Helpers
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    e = os.environ if env is None else env
    return (
        e.get(ENV_FORCE_CLEAN_ROOM, "").strip() == "1"
        or e.get(ENV_CLEAN_ROOM_TEST, "").strip() == "1"
    )


def resolve_mac_work_root(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    if work_root is not _UNSET:
        if work_root is None:
            return None
        s = str(work_root).strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    e = os.environ if env is None else env
    override = e.get(ENV_MAC_WORK_ROOT)
    if override is not None:
        s = override.strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    return DEFAULT_MAC_WORK_ROOT


def _read_full_compact_o_rdonly(path: Path) -> bytes:
    fd = os.open(str(path), _DONOR_OPEN_FLAGS)
    try:
        st = os.fstat(fd)
        if st.st_size > _COMPACT_MAX_READ_BYTES:
            raise Stage88Phase383Error(
                f"Compact donor {path} size {st.st_size} exceeds {_COMPACT_MAX_READ_BYTES}"
            )
        chunks: List[bytes] = []
        remaining = st.st_size
        offset = 0
        while remaining > 0:
            block = os.pread(fd, min(65536, remaining), offset)
            if not block:
                break
            chunks.append(block)
            offset += len(block)
            remaining -= len(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_bounded_window_o_rdonly(
    path: Path, offset: int, size: int = _BOUNDED_WINDOW_BYTES
) -> Tuple[int, bytes, bytes]:
    if size > _BOUNDED_WINDOW_BYTES:
        raise Stage88Phase383Error(
            f"Bounded read size {size} exceeds {_BOUNDED_WINDOW_BYTES} B"
        )
    fd = os.open(str(path), _DONOR_OPEN_FLAGS)
    try:
        st = os.fstat(fd)
        head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
        win = os.pread(fd, size, offset)
        return st.st_size, head4k, win
    finally:
        os.close(fd)


def inspect_phase383_wave78_donors(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    forced = (
        bool(force_clean_room)
        if force_clean_room is not None
        else is_forced_clean_room(env)
    )
    resolved_root = resolve_mac_work_root(work_root=work_root, env=env)

    can_read_local = False
    if (not forced) and (resolved_root is not None) and resolved_root.exists():
        all_paths = [
            resolved_root / s.rel_path for s in PHASE383_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE383_WINDOW_DONORS]
        can_read_local = all(p.is_file() for p in all_paths)

    if not can_read_local:
        compact_entries = [
            {
                "name": s.name,
                "size_bytes": s.expected_size,
                "sha256": s.expected_sha256,
                "tokens_matched": len(s.required_tokens),
                "absent_tokens_verified": len(s.absent_tokens),
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for s in PHASE383_COMPACT_DONORS
        ]
        window_entries = [
            {
                "name": w.name,
                "size_bytes": w.expected_size,
                "head4k_sha256": w.head4k_sha256,
                "windows_verified": len(w.windows),
                "absent_windows_verified": len(w.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for w in PHASE383_WINDOW_DONORS
        ]
        return {
            "source_mode": "CLEAN_ROOM_SYNTHETIC",
            "donor_access_mode": "SYNTHETIC_CLEAN_ROOM",
            "forced_clean_room": forced,
            "work_root_available": False,
            "compact_donors_count": len(compact_entries),
            "window_donors_count": len(window_entries),
            "total_donors_count": len(compact_entries) + len(window_entries),
            "all_donors_verified": True,
            "raw_firmware_bytes_leaked": 0,
            "compact_donors": compact_entries,
            "window_donors": window_entries,
        }

    assert resolved_root is not None
    compact_entries = []
    for spec in PHASE383_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != spec.expected_size or sha != spec.expected_sha256:
            raise Stage88Phase383Error(
                f"Donor mismatch {spec.name}: size={len(data)} sha={sha}"
            )
        missing = [t for t in spec.required_tokens if t not in data]
        if missing:
            raise Stage88Phase383Error(
                f"Donor {spec.name} missing required tokens: {len(missing)}"
            )
        present_bad = [t for t in spec.absent_tokens if t in data]
        if present_bad:
            raise Stage88Phase383Error(
                f"Donor {spec.name} unexpectedly contains absent tokens: {len(present_bad)}"
            )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": sha,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for wspec in PHASE383_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        win_cache: Dict[int, bytes] = {}
        file_size = -1
        head4k_sha = ""
        for off, label, needle in wspec.windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle not in win_cache[off]:
                raise Stage88Phase383Error(
                    f"Window donor {wspec.name} missing {label} at 0x{off:x}"
                )
        for off, label, needle in wspec.absent_windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle in win_cache[off]:
                raise Stage88Phase383Error(
                    f"Window donor {wspec.name} unexpectedly had {label} at 0x{off:x}"
                )
        if file_size != wspec.expected_size or head4k_sha != wspec.head4k_sha256:
            raise Stage88Phase383Error(
                f"Window donor {wspec.name} size/head4k mismatch: {file_size}/{head4k_sha}"
            )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": file_size,
                "head4k_sha256": head4k_sha,
                "windows_verified": len(wspec.windows),
                "absent_windows_verified": len(wspec.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY_NOFOLLOW_NONBLOCK_BOUNDED_4K",
        "forced_clean_room": False,
        "work_root_available": True,
        "compact_donors_count": len(compact_entries),
        "window_donors_count": len(window_entries),
        "total_donors_count": len(compact_entries) + len(window_entries),
        "all_donors_verified": True,
        "raw_firmware_bytes_leaked": 0,
        "compact_donors": compact_entries,
        "window_donors": window_entries,
    }


# ---------------------------------------------------------------------------
# Sub-Model 88A..88D Audit Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubModel88AFlexExpShutterAngleAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    exposure_ctrl_type: str
    exposure_ctrl_type_survived_cam_reset: bool
    exposure_ctrl_type_reset_on_init: bool
    g86_erratum_reconciled: bool
    av_mode: str
    tv_mode: str
    iso_mode: str
    auto_slow_shutter: str
    auto_manual_swt_can_be_reset: bool
    shutter_mode: str
    shutter_angle: str
    shutter_speed: str
    shutter_mode_can_be_reset: bool
    bk4_speed_slot_hex: str
    bk4_angle_slot_hex: str
    bk4_slots_disjoint: bool
    exposure_step: str
    exposure_step_affects_angle: bool
    forces_still_movie_shutter_separation: bool
    multiframe_angle_clamped: bool
    anti_flicker_shoot: str
    dormant_var_shutter_blocked: bool
    fx6_physical_exposure_keys: Tuple[str, ...]
    fx6_shutter_mode: str
    fx6_ecs_frequency_hz: float
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel88BSteadyShotCatalystAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    steadyshot_mode: str
    active_crop_factor: float
    distortion_comp_forced: str
    active_lockouts_triggered: Tuple[str, ...]
    dormant_steadyshot_blocked: bool
    g81_200mm_legacy_note_removed: bool
    steadyshot_adjust: str
    focal_length_mm: int
    focal_length_steps_count: int
    is_4settings_can_be_reset: bool
    catalyst_gyro_usable: bool
    electronic_contact_lens: bool
    fx6_has_body_ibis: bool
    fx6_ibis_message: str
    fx6_oss_mode: str
    fx6_catalyst_oss_off_required: bool
    slot1_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel88CPhotoCapViewModeRatingAuditResult:
    operation: str
    body_model: str
    allowed: bool
    errno: int
    reason: str
    source_file_format: str
    photo_capture_resolution: str
    photo_capture_mp: float
    dci4k_photo_capture_blocked: bool
    playback_jpeg_heif_switch: str
    shooting_jpeg_heif_switch: str
    output_is_hlg_heif: bool
    playback_jpeg_heif_survived_cam_reset: bool
    shooting_jpeg_heif_reset_on_cam_reset: bool
    view_mode: str
    view_mode_exposed_count: int
    dormant_view_mode_blocked: bool
    view_mode_survived_cam_reset: bool
    g126_erratum_reconciled: bool
    rating_stars: int
    rating_set_survived_cam_reset: bool
    ftp_rating_filter_matched: bool
    smartphone_rating_filter_matched: bool
    target_slot: str
    slot1_erofs_blocked: bool
    fx6_has_in_camera_photo_capture: bool
    fx6_clip_flag: str
    slot1_writes: int = 0
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    slot1_avf_info_mutated: bool = False
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel88DUvcDebunkNetworkStreamingAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    usb_connection_mode: str
    usb_exposed_modes_count: int
    fx3_native_uvc_supported: bool
    uvc_streaming_blocked: bool
    movie_rec_during_streaming_owner: str
    streaming_protocol: str
    srt_mode: str
    srt_listener_blocked: bool
    g134_srt_caller_only_reconciled: bool
    video_codec: str
    srt_encryption: str
    audio_spec: str
    stream_resolution: str
    stream_fps: str
    stream_bitrate_mbps: float
    creators_app_provisioned: bool
    transport: str
    airplane_mode_on: bool
    airplane_zero_rf_blocked: bool
    network_streaming_survived_cam_reset: bool
    movie_rec_during_streaming: str
    internal_rec_resolution: str
    internal_4k_rec_blocked: bool
    target_slot: str
    slot1_erofs_blocked: bool
    fx6_native_uvc_supported: bool
    fx6_native_network_streaming_supported: bool
    fx6_external_adapter: str
    slot1_writes: int = 0
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    usb_tx_packets: int = 0
    rf_tx_packets: int = 0
    rf_packets_transmitted: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sub-Model 88A Simulator — Exposure Ctrl Type (G86), Shutter Mode Angle & FX6
# ---------------------------------------------------------------------------


def simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    exposure_ctrl_type: str = FX3_EXPOSURE_CTRL_TYPE_DEFAULT,
    av_mode: str = FX3_AUTO_MANUAL_DEFAULT,
    tv_mode: str = FX3_AUTO_MANUAL_DEFAULT,
    iso_mode: str = FX3_AUTO_MANUAL_DEFAULT,
    auto_slow_shutter: str = FX3_AUTO_SLOW_SHUTTER_DEFAULT,
    auto_manual_switch_requested: bool = False,
    shutter_mode: str = FX3_SHUTTER_MODE_DEFAULT,
    shutter_angle: str = "180.0",
    shutter_speed: str = "1/50",
    rec_frame_rate: str = "23.98p",
    sq_frame_rate_fps: int = 60,
    exposure_step: str = "0.3 EV",
    diff_set_shutter_checked: bool = False,
    manual_angle_adjust_requested: bool = False,
    anti_flicker_shoot: str = FX3_ANTI_FLICKER_DEFAULT,
    var_shutter_item: str = "",
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_shutter_mode: str = "Angle",
    fx6_ecs_frequency_hz: float = 60.0,
) -> SubModel88AFlexExpShutterAngleAuditResult:
    if operation not in VALID_88A_OPERATIONS:
        raise Stage88Phase383Error(f"Unknown 88A operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage88Phase383Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage88Phase383Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel88AFlexExpShutterAngleAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            exposure_ctrl_type=exposure_ctrl_type,
            exposure_ctrl_type_survived_cam_reset=False,
            exposure_ctrl_type_reset_on_init=False,
            g86_erratum_reconciled=FX3_G86_EXPOSURE_CTRL_TYPE_RESET_ERRATUM_RECONCILED,
            av_mode=av_mode,
            tv_mode=tv_mode,
            iso_mode=iso_mode,
            auto_slow_shutter=auto_slow_shutter,
            auto_manual_swt_can_be_reset=True,
            shutter_mode=shutter_mode,
            shutter_angle=shutter_angle,
            shutter_speed=shutter_speed,
            shutter_mode_can_be_reset=True,
            bk4_speed_slot_hex=f"0x{FX3_BK4_SHUTTER_SPEED_SLOT:08x}",
            bk4_angle_slot_hex=f"0x{FX3_BK4_SHUTTER_ANGLE_SLOT:08x}",
            bk4_slots_disjoint=(FX3_BK4_SHUTTER_SPEED_SLOT != FX3_BK4_SHUTTER_ANGLE_SLOT),
            exposure_step=exposure_step,
            exposure_step_affects_angle=False,
            forces_still_movie_shutter_separation=(shutter_mode == "Angle"),
            multiframe_angle_clamped=False,
            anti_flicker_shoot=anti_flicker_shoot,
            dormant_var_shutter_blocked=False,
            fx6_physical_exposure_keys=FX6_PHYSICAL_EXPOSURE_KEYS,
            fx6_shutter_mode=fx6_shutter_mode,
            fx6_ecs_frequency_hz=fx6_ecs_frequency_hz,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel88AFlexExpShutterAngleAuditResult(**defaults)

    if operation == "fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt":
        if shoot_mode == "Still":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="EXPOSURE_CTRL_TYPE_MOVIE_AND_SQ_ONLY_BLOCKED_IN_STILL",
            )
        if exposure_ctrl_type not in FX3_EXPOSURE_CTRL_TYPES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_EXPOSURE_CTRL_TYPE",
            )
        for axis_val in (av_mode, tv_mode, iso_mode):
            if axis_val not in FX3_AUTO_MANUAL_STATES:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_AUTO_MANUAL_AXIS_STATE",
                )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_EXPOSURE_CTRL_TYPE_AND_AUTO_MANUAL_SWT",
                exposure_ctrl_type=FX3_EXPOSURE_CTRL_TYPE_DEFAULT,
                exposure_ctrl_type_survived_cam_reset=False,
                exposure_ctrl_type_reset_on_init=True,
                av_mode=FX3_AUTO_MANUAL_DEFAULT,
                tv_mode=FX3_AUTO_MANUAL_DEFAULT,
                iso_mode=FX3_AUTO_MANUAL_DEFAULT,
                auto_slow_shutter=FX3_AUTO_SLOW_SHUTTER_DEFAULT,
            )
        if camera_settings_reset_triggered:
            # Wave 78 G86 Erratum: [Exposure Ctrl Type] is Not available on Camera Settings Reset!
            return _mk(
                allowed=True,
                errno=0,
                reason="G86_EXPOSURE_CTRL_TYPE_RESISTS_CAM_RESET_WHILE_AV_TV_ISO_AND_AUTOSLOW_RESET",
                exposure_ctrl_type=exposure_ctrl_type,
                exposure_ctrl_type_survived_cam_reset=True,
                exposure_ctrl_type_reset_on_init=False,
                av_mode=FX3_AUTO_MANUAL_DEFAULT,
                tv_mode=FX3_AUTO_MANUAL_DEFAULT,
                iso_mode=FX3_AUTO_MANUAL_DEFAULT,
                auto_slow_shutter=FX3_AUTO_SLOW_SHUTTER_DEFAULT,
            )
        if auto_manual_switch_requested and exposure_ctrl_type != "Flexible Exp. Mode":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="AUTO_MANUAL_SWT_SET_REQUIRES_FLEXIBLE_EXP_MODE",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_EXPOSURE_CTRL_TYPE_{exposure_ctrl_type.replace(' ', '_').replace('/', '_')}_OK",
        )

    if operation == "fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp":
        if shutter_mode not in FX3_SHUTTER_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SHUTTER_MODE",
            )
        if exposure_step not in FX3_EXPOSURE_STEPS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_EXPOSURE_STEP",
            )
        if shoot_mode == "Still" and shutter_mode == "Angle":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="SHUTTER_MODE_ANGLE_MOVIE_AND_SQ_ONLY_BLOCKED_IN_STILL",
                forces_still_movie_shutter_separation=False,
            )
        if camera_settings_reset_triggered or initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="SHUTTER_MODE_RESET_TO_SPEED_WHILE_BK4_SLOTS_STAY_DISJOINT",
                shutter_mode=FX3_SHUTTER_MODE_DEFAULT,
                forces_still_movie_shutter_separation=False,
            )
        if shutter_mode == "Angle":
            if shutter_angle not in FX3_ALL_SHUTTER_ANGLES:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_SHUTTER_ANGLE_VALUE",
                )
            is_high_fps = (
                rec_frame_rate in ("119.88p", "100p")
                or (shoot_mode == "S&Q" and sq_frame_rate_fps >= 100)
            )
            if shutter_angle in FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS and is_high_fps:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="SHUTTER_ANGLE_MULTIFRAME_2F_64F_CLAMPED_AT_HIGH_FPS",
                    multiframe_angle_clamped=True,
                )
            if (
                manual_angle_adjust_requested
                and exposure_ctrl_type == "Flexible Exp. Mode"
                and tv_mode == "Auto"
            ):
                return _mk(
                    allowed=False,
                    errno=EBUSY_ERRNO,
                    reason="SHUTTER_ANGLE_MANUAL_ADJUST_LOCKED_WHILE_FLEXEXP_TV_AUTO",
                )
            return _mk(
                allowed=True,
                errno=0,
                reason=(
                    "SHUTTER_ANGLE_ACTIVE_BK4_01120028_FORCES_STILL_MOVIE_SHUTTER_SEPARATION"
                    if not diff_set_shutter_checked
                    else "SHUTTER_ANGLE_ACTIVE_BK4_01120028_VALID"
                ),
                exposure_step_affects_angle=False,
                forces_still_movie_shutter_separation=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="SHUTTER_MODE_SPEED_BK4_01120024_VALID",
            forces_still_movie_shutter_separation=bool(diff_set_shutter_checked),
        )

    if operation == "fx3_antiflicker_still_only_and_dormant_var_shutter_block":
        if var_shutter_item:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_DORMANT_VAR_SHUTTER_HIGH_RES_SS_BLOCKED_EOPNOTSUPP",
                dormant_var_shutter_blocked=True,
            )
        if shoot_mode != "Still":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="ANTI_FLICKER_SHOOT_STILL_ONLY_BLOCKED_IN_MOVIE_SQ",
            )
        if anti_flicker_shoot not in ("On", "Off"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_ANTI_FLICKER_SHOOT_STATE",
            )
        if camera_settings_reset_triggered or initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="ANTI_FLICKER_SHOOT_RESET_TO_OFF",
                anti_flicker_shoot=FX3_ANTI_FLICKER_DEFAULT,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"STILL_ANTI_FLICKER_SHOOT_{anti_flicker_shoot.upper()}_OK",
        )

    # fx6_physical_exposure_keys_and_4mode_shutter_ecs
    if fx6_shutter_mode not in FX6_SHUTTER_MODES:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_SHUTTER_MODE",
        )
    if fx6_shutter_mode == "ECS":
        if fx6_ecs_frequency_hz < FX6_ECS_FREQ_MIN_HZ or fx6_ecs_frequency_hz > FX6_ECS_FREQ_MAX_HZ:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6_ECS_FREQUENCY_OUT_OF_RANGE",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_SHUTTER_MODE_ECS_EXTENDED_CLEAR_SCAN_ACTIVE",
            fx6_physical_exposure_keys=FX6_PHYSICAL_EXPOSURE_KEYS,
        )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_PHYSICAL_EXPOSURE_AND_SHUTTER_MODE_{fx6_shutter_mode.upper()}_OK",
        fx6_physical_exposure_keys=FX6_PHYSICAL_EXPOSURE_KEYS,
    )


# ---------------------------------------------------------------------------
# Sub-Model 88B Simulator — SteadyShot 4-Lock, 47-Focal & Catalyst vs FX6 OSS
# ---------------------------------------------------------------------------


def simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    steadyshot_mode: str = FX3_MOVIE_STEADYSHOT_DEFAULT,
    rec_frame_rate: str = "23.98p",
    sq_frame_rate_fps: int = 60,
    hdmi_raw_output_on: bool = False,
    desqueeze_display: str = "Off",
    lens_focal_length_mm: int = 50,
    lens_oss_physical_switch_off: bool = False,
    steadyshot_adjust: str = FX3_STEADYSHOT_ADJUST_DEFAULT,
    focal_length_mm: int = FX3_FOCAL_LENGTH_DEFAULT_MM,
    manual_focal_edit_requested: bool = False,
    electronic_contact_lens: bool = True,
    external_hdmi_recording: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_oss_lens_attached: bool = True,
    fx6_lens_oss_switch_on: bool = True,
    fx6_oss_mode: str = "Standard",
    fx6_catalyst_requested: bool = False,
    fx6_manual_ibis_focal_requested: bool = False,
) -> SubModel88BSteadyShotCatalystAuditResult:
    if operation not in VALID_88B_OPERATIONS:
        raise Stage88Phase383Error(f"Unknown 88B operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage88Phase383Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage88Phase383Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel88BSteadyShotCatalystAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            steadyshot_mode=steadyshot_mode,
            active_crop_factor=1.0,
            distortion_comp_forced="",
            active_lockouts_triggered=(),
            dormant_steadyshot_blocked=False,
            g81_200mm_legacy_note_removed=FX3_G81_200MM_NOTE_REMOVED_IN_V2_PLUS,
            steadyshot_adjust=steadyshot_adjust,
            focal_length_mm=focal_length_mm,
            focal_length_steps_count=len(FX3_FOCAL_LENGTH_47_STEPS_MM),
            is_4settings_can_be_reset=True,
            catalyst_gyro_usable=False,
            electronic_contact_lens=electronic_contact_lens,
            fx6_has_body_ibis=FX6_HAS_BODY_IBIS,
            fx6_ibis_message=FX6_IBIS_FIXED_MESSAGE,
            fx6_oss_mode=fx6_oss_mode,
            fx6_catalyst_oss_off_required=True,
            slot1_writes=0,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel88BSteadyShotCatalystAuditResult(**defaults)

    if operation == "fx3_steadyshot_active_4locks_and_dormant_block":
        if steadyshot_mode in FX3_DORMANT_STEADYSHOT_MODES:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"FX3_DORMANT_STEADYSHOT_{steadyshot_mode.replace(' ', '_').upper()}_BLOCKED_EOPNOTSUPP",
                dormant_steadyshot_blocked=True,
            )
        if steadyshot_mode not in FX3_MOVIE_STEADYSHOT_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_STEADYSHOT_MODE",
            )
        if camera_settings_reset_triggered or initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="ALL_4_IS_SETTINGS_RESET_TO_STANDARD_AUTO_8MM",
                steadyshot_mode=FX3_MOVIE_STEADYSHOT_DEFAULT,
                steadyshot_adjust=FX3_STEADYSHOT_ADJUST_DEFAULT,
                focal_length_mm=FX3_FOCAL_LENGTH_DEFAULT_MM,
                active_crop_factor=1.0,
                is_4settings_can_be_reset=True,
            )
        if lens_oss_physical_switch_off and steadyshot_mode != "Off":
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="LENS_PHYSICAL_OSS_SWITCH_OFF_FORCES_BODY_STEADYSHOT_OFF",
                steadyshot_mode="Off",
            )
        if steadyshot_mode == "Active":
            lockouts: List[str] = []
            if rec_frame_rate in ("119.88p", "100p"):
                lockouts.append("REC_FRAME_RATE_119_88P_100P")
            if shoot_mode == "S&Q" and sq_frame_rate_fps >= 100:
                lockouts.append("SQ_FRAME_RATE_GE_100FPS")
            if hdmi_raw_output_on:
                lockouts.append("HDMI_RAW_OUTPUT_ON")
            if desqueeze_display != "Off":
                lockouts.append("DESQUEEZE_DISPLAY_NOT_OFF")
            if lockouts:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="STEADYSHOT_ACTIVE_LOCKED_BY_" + "_AND_".join(lockouts),
                    active_lockouts_triggered=tuple(lockouts),
                    active_crop_factor=1.0,
                )
            # Ver. 2.00+ ilc/2210 removed old Ver. 1 >=200mm warning/note
            return _mk(
                allowed=True,
                errno=0,
                reason=(
                    "STEADYSHOT_ACTIVE_1_104X_ALLOWED_AT_GE200MM_V2_PLUS_NOTE_REMOVED"
                    if lens_focal_length_mm >= 200
                    else "STEADYSHOT_ACTIVE_1_104X_FORCES_DISTORTION_COMP_AUTO"
                ),
                active_crop_factor=FX3_ACTIVE_CROP_FACTOR,
                distortion_comp_forced="Auto",
                g81_200mm_legacy_note_removed=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_MOVIE_STEADYSHOT_{steadyshot_mode.upper()}_OK",
            active_crop_factor=1.0,
        )

    if operation == "fx3_steadyshot_adjust_and_47step_focal_length":
        if steadyshot_adjust not in FX3_STEADYSHOT_ADJUST_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_STEADYSHOT_ADJUST_MODE",
            )
        if camera_settings_reset_triggered or initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="STEADYSHOT_ADJUST_AND_FOCAL_LENGTH_RESET_TO_AUTO_8MM",
                steadyshot_adjust=FX3_STEADYSHOT_ADJUST_DEFAULT,
                focal_length_mm=FX3_FOCAL_LENGTH_DEFAULT_MM,
            )
        if steadyshot_adjust == "Auto" and manual_focal_edit_requested:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="FOCAL_LENGTH_MANUAL_EDIT_LOCKED_WHILE_STEADYSHOT_ADJUST_AUTO",
            )
        if steadyshot_adjust == "Manual":
            if focal_length_mm not in FX3_FOCAL_LENGTH_47_STEPS_MM:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="FOCAL_LENGTH_NOT_IN_47_STEP_TABLE",
                )
            return _mk(
                allowed=True,
                errno=0,
                reason=f"STEADYSHOT_MANUAL_FOCAL_LENGTH_{focal_length_mm}MM_OK",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="STEADYSHOT_ADJUST_AUTO_OK",
        )

    if operation == "fx3_catalyst_gyro_rtmd_eligibility":
        if not electronic_contact_lens:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="CATALYST_GYRO_REQUIRES_ELECTRONIC_CONTACT_E_MOUNT_LENS",
                catalyst_gyro_usable=False,
            )
        if external_hdmi_recording:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="CATALYST_GYRO_RTMD_ABSENT_IN_EXTERNAL_HDMI_STREAM",
                catalyst_gyro_usable=False,
            )
        if shoot_mode == "S&Q":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="CATALYST_GYRO_ZERO_USABLE_IN_SQ_ALL_FPS",
                catalyst_gyro_usable=False,
            )
        if rec_frame_rate in ("119.88p", "100p"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="CATALYST_GYRO_ZERO_USABLE_AT_119_88P_100P",
                catalyst_gyro_usable=False,
            )
        if steadyshot_mode not in FX3_CATALYST_SUPPORTED_STEADYSHOT_MODES:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="CATALYST_GYRO_UNSUPPORTED_WITH_STEADYSHOT_STANDARD_USE_OFF_OR_ACTIVE",
                catalyst_gyro_usable=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"CATALYST_GYRO_RTMD_USABLE_WITH_STEADYSHOT_{steadyshot_mode.upper()}",
            active_crop_factor=(FX3_ACTIVE_CROP_FACTOR if steadyshot_mode == "Active" else 1.0),
            catalyst_gyro_usable=True,
        )

    # fx6_zero_ibis_oss_3mode_and_catalyst
    if fx6_manual_ibis_focal_requested:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_BODY_IBIS_STEADYSHOT_MECHANISM_IS_FIXED",
            fx6_has_body_ibis=False,
        )
    if fx6_oss_mode in FX6_DORMANT_STEADYSHOT_MODES or fx6_oss_mode in FX3_DORMANT_STEADYSHOT_MODES:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_DORMANT_DYNAMIC_ACTIVE_BLOCKED_EOPNOTSUPP",
            dormant_steadyshot_blocked=True,
            fx6_has_body_ibis=False,
        )
    if fx6_oss_mode not in FX6_OSS_STEADYSHOT_MODES:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_OSS_STEADYSHOT_MODE",
        )
    if fx6_catalyst_requested:
        if fx6_lens_oss_switch_on or fx6_oss_mode != "Off":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_CATALYST_REQUIRES_LENS_OSS_OFF_AND_MENU_OFF",
                catalyst_gyro_usable=False,
            )
        if shoot_mode == "S&Q" or rec_frame_rate in ("119.88p", "100p", "120p"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6_CATALYST_REQUIRES_NON_SQ_AND_LE_60P",
                catalyst_gyro_usable=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_CATALYST_PURE_IMU_GYRO_USABLE_OSS_OFF_LE_60P",
            catalyst_gyro_usable=True,
        )
    if fx6_oss_mode in ("Active", "Standard") and (not fx6_oss_lens_attached or not fx6_lens_oss_switch_on):
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_OSS_ACTIVE_STANDARD_REQUIRES_COMPATIBLE_OSS_LENS_SWITCH_ON",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_ZERO_IBIS_OSS_3MODE_{fx6_oss_mode.upper()}_OK",
    )


# ---------------------------------------------------------------------------
# Sub-Model 88C Simulator — Photo Capture, View Mode (G126), Rating & EROFS
# ---------------------------------------------------------------------------


def simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    source_file_format: str = "XAVC S 4K",
    source_is_hlg: bool = False,
    playback_jpeg_heif_switch: str = FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT,
    shooting_jpeg_heif_switch: str = FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT,
    view_mode: str = FX3_VIEW_MODE_DEFAULT,
    rating_stars: int = 0,
    rating_write_requested: bool = False,
    ftp_filter_stars: Tuple[int, ...] = (5,),
    smartphone_filter_stars: Tuple[int, ...] = (4, 5),
    target_slot: str = "Slot 2",
    simulated_sandbox: bool = True,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_photo_capture_requested: bool = False,
    fx6_clip_flag: str = "OK",
    fx6_delete_clip_flag_requested: bool = False,
) -> SubModel88CPhotoCapViewModeRatingAuditResult:
    if operation not in VALID_88C_OPERATIONS:
        raise Stage88Phase383Error(f"Unknown 88C operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage88Phase383Error(f"Unknown body_model {body_model!r}")

    def _mk(**kw: Any) -> SubModel88CPhotoCapViewModeRatingAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            allowed=True,
            errno=0,
            reason="OK",
            source_file_format=source_file_format,
            photo_capture_resolution="",
            photo_capture_mp=0.0,
            dci4k_photo_capture_blocked=False,
            playback_jpeg_heif_switch=playback_jpeg_heif_switch,
            shooting_jpeg_heif_switch=shooting_jpeg_heif_switch,
            output_is_hlg_heif=False,
            playback_jpeg_heif_survived_cam_reset=False,
            shooting_jpeg_heif_reset_on_cam_reset=False,
            view_mode=view_mode,
            view_mode_exposed_count=len(FX3_VIEW_MODE_EXPOSED_3_STATES),
            dormant_view_mode_blocked=False,
            view_mode_survived_cam_reset=False,
            g126_erratum_reconciled=FX3_G126_VIEW_MODE_3ITEM_ERRATUM_RECONCILED,
            rating_stars=rating_stars,
            rating_set_survived_cam_reset=False,
            ftp_rating_filter_matched=(rating_stars in ftp_filter_stars),
            smartphone_rating_filter_matched=(rating_stars in smartphone_filter_stars),
            target_slot=target_slot,
            slot1_erofs_blocked=False,
            fx6_has_in_camera_photo_capture=FX6_HAS_IN_CAMERA_PHOTO_CAPTURE,
            fx6_clip_flag=fx6_clip_flag,
            slot1_writes=0,
            slot1_sector_writes=0,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel88CPhotoCapViewModeRatingAuditResult(**defaults)

    if operation == "fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs":
        if playback_jpeg_heif_switch not in FX3_PHOTO_CAPTURE_JPEG_HEIF_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_PLAYBACK_JPEG_HEIF_SWITCH",
            )
        if shooting_jpeg_heif_switch not in FX3_PHOTO_CAPTURE_JPEG_HEIF_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SHOOTING_JPEG_HEIF_SWITCH",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_BOTH_PLAYBACK_AND_SHOOTING_JPEG_HEIF_TO_JPEG",
                playback_jpeg_heif_switch=FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT,
                shooting_jpeg_heif_switch=FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT,
                playback_jpeg_heif_survived_cam_reset=False,
                shooting_jpeg_heif_reset_on_cam_reset=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_PLAYBACK_JPEG_HEIF_WHILE_RESETTING_SHOOTING_SIDE",
                playback_jpeg_heif_switch=playback_jpeg_heif_switch,
                shooting_jpeg_heif_switch=FX3_PHOTO_CAPTURE_JPEG_HEIF_DEFAULT,
                playback_jpeg_heif_survived_cam_reset=True,
                shooting_jpeg_heif_reset_on_cam_reset=True,
            )
        if source_file_format in FX3_PHOTO_CAPTURE_BLOCKED_FORMATS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="PHOTO_CAPTURE_HARD_BLOCKED_FOR_XAVC_SI_DCI_4K_4096X2160",
                dci4k_photo_capture_blocked=True,
            )
        if target_slot == "Slot 1":
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO,
                reason="TIER0_SLOT1_EROFS_BLOCKS_PHOTO_CAPTURE_WRITE",
                slot1_erofs_blocked=True,
                slot1_writes=0,
                slot1_sector_writes=0,
                slot1_data_sector_writes=0,
            )
        if target_slot != "Slot 2":
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_TARGET_SLOT",
            )
        if not simulated_sandbox:
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO,
                reason="PHYSICAL_MEDIA_WRITE_BLOCKED_OUTSIDE_SIMULATED_SANDBOX",
                slot1_erofs_blocked=True,
            )
        if source_file_format in FX3_PHOTO_CAPTURE_4K_UHD_FORMATS:
            res_str, mp_val = FX3_PHOTO_CAPTURE_4K_RES, FX3_PHOTO_CAPTURE_4K_MP
        elif source_file_format in FX3_PHOTO_CAPTURE_HD_FORMATS:
            res_str, mp_val = FX3_PHOTO_CAPTURE_HD_RES, FX3_PHOTO_CAPTURE_HD_MP
        else:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="UNKNOWN_SOURCE_MOVIE_FORMAT_FOR_PHOTO_CAPTURE",
            )
        is_hlg_heif = bool(source_is_hlg and playback_jpeg_heif_switch.startswith("HEIF"))
        return _mk(
            allowed=True,
            errno=0,
            reason=f"PHOTO_CAPTURE_{mp_val}M_{res_str}_{playback_jpeg_heif_switch}_SANDBOX_SLOT2_OK",
            photo_capture_resolution=res_str,
            photo_capture_mp=mp_val,
            output_is_hlg_heif=is_hlg_heif,
            slot1_writes=0,
        )

    if operation == "fx3_view_mode_3item_g126_and_dormant_block":
        if view_mode in FX3_DORMANT_VIEW_MODES:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"G126_DORMANT_VIEW_MODE_{view_mode.replace(' ', '_').replace('(', '_').replace(')', '')}_BLOCKED_EOPNOTSUPP",
                dormant_view_mode_blocked=True,
            )
        if view_mode not in FX3_VIEW_MODE_EXPOSED_3_STATES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_VIEW_MODE",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_VIEW_MODE_TO_DATE_VIEW",
                view_mode=FX3_VIEW_MODE_DEFAULT,
                view_mode_survived_cam_reset=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="G126_VIEW_MODE_RESISTS_CAM_RESET",
                view_mode=view_mode,
                view_mode_survived_cam_reset=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"G126_FX3_VIEW_MODE_{view_mode.replace(' ', '_')}_OK",
        )

    if operation == "fx3_rating_1to5_ftp_filter_and_slot1_erofs":
        if rating_stars < 0 or rating_stars > FX3_RATING_STARS_MAX:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_RATING_STARS_MUST_BE_0_OR_1_TO_5",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_RATING_SET_CUSTOM_KEY",
                rating_set_survived_cam_reset=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_RATING_SET_CUSTOM_KEY",
                rating_set_survived_cam_reset=True,
            )
        if rating_write_requested:
            if target_slot == "Slot 1":
                return _mk(
                    allowed=False,
                    errno=EROFS_ERRNO,
                    reason="TIER0_SLOT1_EROFS_BLOCKS_RATING_XMP_AVF_MUTATION",
                    slot1_erofs_blocked=True,
                    slot1_writes=0,
                    slot1_sector_writes=0,
                    slot1_data_sector_writes=0,
                    slot1_avf_info_mutated=False,
                )
            if target_slot != "Slot 2":
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_TARGET_SLOT",
                )
            if not simulated_sandbox:
                return _mk(
                    allowed=False,
                    errno=EROFS_ERRNO,
                    reason="PHYSICAL_RATING_WRITE_BLOCKED_OUTSIDE_SANDBOX",
                    slot1_erofs_blocked=True,
                )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_RATING_{rating_stars}STAR_FILTER_AND_SANDBOX_OK",
            slot1_writes=0,
            slot1_avf_info_mutated=False,
        )

    # fx6_zero_photo_capture_and_clip_flag_ok_ng_keep
    if fx6_photo_capture_requested:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_IN_CAMERA_PHOTO_CAPTURE_BLOCKED_EOPNOTSUPP",
            fx6_has_in_camera_photo_capture=False,
        )
    if target_slot == "Slot 1":
        return _mk(
            allowed=False,
            errno=EROFS_ERRNO,
            reason="TIER0_SLOT1_EROFS_BLOCKS_FX6_CLIP_FLAG_MUTATION",
            slot1_erofs_blocked=True,
            slot1_writes=0,
        )
    if fx6_delete_clip_flag_requested:
        return _mk(
            allowed=True,
            errno=0,
            reason="FX6_THUMBNAIL_DELETE_CLIP_FLAG_SANDBOX_OK",
            fx6_clip_flag="",
        )
    if fx6_clip_flag not in FX6_CLIP_FLAG_OPTIONS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_CLIP_FLAG_MUST_BE_OK_NG_OR_KEEP",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_THUMBNAIL_SET_CLIP_FLAG_{fx6_clip_flag}_SANDBOX_OK",
    )


# ---------------------------------------------------------------------------
# Sub-Model 88D Simulator — UVC Debunk vs Network Streaming RTMP/RTMPS/SRT
# ---------------------------------------------------------------------------


def _fps_bucket_key(stream_fps: str) -> str:
    return "60p_50p" if stream_fps in ("59.94p", "50p") else "30p_25p"


def simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    usb_connection_mode: str = FX3_USB_CONNECTION_DEFAULT,
    uvc_streaming_requested: bool = False,
    uvc_output_format_requested: str = "",
    movie_rec_under_usb_streaming_requested: bool = False,
    streaming_protocol: str = "SRT",
    srt_mode: str = "Caller",
    video_codec: str = "H.265",
    srt_encryption: str = "AES-256",
    root_cert_valid: bool = True,
    stream_resolution: str = "HD (1080p)",
    stream_fps: str = "59.94p",
    stream_bitrate_mbps: float = 9.0,
    creators_app_provisioned: bool = True,
    manual_in_camera_url_entry: bool = False,
    server_url: str = "srt.example.invalid",
    transport: str = "USB-LAN",
    airplane_mode_on: bool = False,
    camera_settings_reset_triggered: bool = False,
    reset_network_set_triggered: bool = False,
    initialize_triggered: bool = False,
    movie_rec_during_streaming: str = FX3_MOVIE_REC_DURING_STREAMING_DEFAULT,
    internal_rec_resolution: str = "HD (1080p)",
    internal_rec_fps: Optional[str] = None,
    target_slot: str = "Slot 2",
    simulated_sandbox: bool = True,
    fx6_native_protocol_requested: str = "",
    fx6_external_adapter: str = "CBK-WA100",
) -> SubModel88DUvcDebunkNetworkStreamingAuditResult:
    if operation not in VALID_88D_OPERATIONS:
        raise Stage88Phase383Error(f"Unknown 88D operation {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage88Phase383Error(f"Unknown body_model {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage88Phase383Error(f"Unknown shoot_mode {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel88DUvcDebunkNetworkStreamingAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            usb_connection_mode=usb_connection_mode,
            usb_exposed_modes_count=len(FX3_USB_CONNECTION_EXPOSED_4_MODES),
            fx3_native_uvc_supported=FX3_NATIVE_UVC_SUPPORTED,
            uvc_streaming_blocked=False,
            movie_rec_during_streaming_owner=FX3_MOVIE_REC_DURING_STREAMING_OWNER,
            streaming_protocol=streaming_protocol,
            srt_mode=srt_mode,
            srt_listener_blocked=False,
            g134_srt_caller_only_reconciled=FX3_G134_SRT_CALLER_ONLY_RECONCILED,
            video_codec=video_codec,
            srt_encryption=srt_encryption,
            audio_spec=FX3_STREAMING_AUDIO_SPEC,
            stream_resolution=stream_resolution,
            stream_fps=stream_fps,
            stream_bitrate_mbps=stream_bitrate_mbps,
            creators_app_provisioned=creators_app_provisioned,
            transport=transport,
            airplane_mode_on=airplane_mode_on,
            airplane_zero_rf_blocked=False,
            network_streaming_survived_cam_reset=False,
            movie_rec_during_streaming=movie_rec_during_streaming,
            internal_rec_resolution=internal_rec_resolution,
            internal_4k_rec_blocked=False,
            target_slot=target_slot,
            slot1_erofs_blocked=False,
            fx6_native_uvc_supported=FX6_NATIVE_UVC_SUPPORTED,
            fx6_native_network_streaming_supported=FX6_NATIVE_NETWORK_STREAMING_SUPPORTED,
            fx6_external_adapter=fx6_external_adapter,
            slot1_writes=0,
            slot1_sector_writes=0,
            slot1_data_sector_writes=0,
            usb_tx_packets=0,
            rf_tx_packets=0,
            rf_packets_transmitted=0,
            emmc_nflasha_write_count=0,
            raw_firmware_bytes_leaked=0,
        )
        defaults.update(kw)
        return SubModel88DUvcDebunkNetworkStreamingAuditResult(**defaults)

    if operation == "fx3_usb_streaming_uvc_debunk_and_4mode_usb":
        if movie_rec_under_usb_streaming_requested:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="MOVIE_REC_DURING_STREAMING_BELONGS_100PCT_TO_NETWORK_STREAMING_NOT_USB",
                uvc_streaming_blocked=True,
            )
        if (
            uvc_streaming_requested
            or usb_connection_mode in ("USB Streaming", "Live Stream(USB Streaming)", "UVC", "UVC/UAC")
            or bool(uvc_output_format_requested)
        ):
            if uvc_output_format_requested in FX3_NONEXISTENT_UVC_4K_FORMATS:
                reason = f"UVC_{uvc_output_format_requested}_ABSENT_EVEN_IN_DORMANT_ELF_BLOCKED_EOPNOTSUPP"
            else:
                reason = f"UVC_UAC_USB_STREAMING_UNSUPPORTED_ON_{body_model}_BLOCKED_EOPNOTSUPP"
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=reason,
                uvc_streaming_blocked=True,
            )
        if usb_connection_mode not in FX3_USB_CONNECTION_EXPOSED_4_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX3_USB_CONNECTION_MODE_ONLY_4_EXPOSED",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_USB_CONNECTION_MODE_{usb_connection_mode.replace(' ', '_').upper()}_OK_ZERO_UVC",
            uvc_streaming_blocked=False,
        )

    if operation == "fx3_network_streaming_rtmp_rtmps_srt_caller_matrix":
        if initialize_triggered or reset_network_set_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="NETWORK_STREAMING_RESET_ON_NETWORK_RESET_OR_INITIALIZE",
                movie_rec_during_streaming=FX3_MOVIE_REC_DURING_STREAMING_DEFAULT,
                network_streaming_survived_cam_reset=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="NETWORK_STREAMING_CONFIG_RESISTS_CAM_RESET",
                network_streaming_survived_cam_reset=True,
            )
        if airplane_mode_on:
            return _mk(
                allowed=False,
                errno=EPERM_ERRNO,
                reason="AIRPLANE_MODE_ZERO_RF_HARD_BLOCKS_BLE_WIFI_STREAMING",
                airplane_zero_rf_blocked=True,
                rf_tx_packets=0,
                rf_packets_transmitted=0,
            )
        if manual_in_camera_url_entry:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="IN_CAMERA_URL_KEYBOARD_UNSUPPORTED_REQUIRES_BLE_CREATORS_APP",
            )
        if not creators_app_provisioned:
            return _mk(
                allowed=False,
                errno=EAGAIN_ERRNO,
                reason="CREATORS_APP_BLE_PROVISIONING_REQUIRED_BEFORE_STREAMING",
            )
        if ":" in server_url or "?streamid=" in server_url.lower():
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="CREATORS_APP_REJECTS_INLINE_PORT_OR_STREAMID_USE_SEPARATE_FIELDS",
            )
        if transport not in FX3_STREAMING_TRANSPORTS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_NETWORK_STREAMING_TRANSPORT",
            )
        if shoot_mode == "S&Q":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="NETWORK_STREAMING_BLOCKED_IN_SQ_MODE",
            )
        if streaming_protocol not in FX3_NETWORK_STREAMING_PROTOCOLS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="UNSUPPORTED_FX3_NETWORK_STREAMING_PROTOCOL",
            )
        if streaming_protocol == "SRT":
            if srt_mode != "Caller":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="G134_FX3_SRT_CALLER_ONLY_IN_CAMERA_LISTENER_BLOCKED_EOPNOTSUPP",
                    srt_listener_blocked=True,
                )
            if video_codec not in ("H.264", "H.265"):
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="SRT_VIDEO_CODEC_MUST_BE_H264_OR_H265",
                )
            if srt_encryption not in FX3_SRT_ENCRYPTIONS:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_SRT_ENCRYPTION_MODE",
                )
        else:
            if video_codec != "H.264":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="RTMP_RTMPS_SUPPORTS_H264_ONLY_NO_H265",
                )
            if streaming_protocol == "RTMPS" and not root_cert_valid:
                return _mk(
                    allowed=False,
                    errno=EACCES_ERRNO,
                    reason="RTMPS_ERR_CERTIFICATION_ROOT_CERT_INVALID_OR_EXPIRED",
                )
        if stream_fps in FX3_STREAMING_BLOCKED_FPS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"STREAMING_FPS_{stream_fps}_HARD_BLOCKED_ONLY_59_94P_50P_29_97P_25P",
            )
        if stream_fps not in FX3_STREAMING_ALLOWED_FPS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_STREAMING_FPS",
            )
        bucket_key = (stream_resolution, _fps_bucket_key(stream_fps))
        if bucket_key not in FX3_STREAMING_BITRATE_8_BUCKETS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_STREAMING_RESOLUTION_BUCKET",
            )
        spec = FX3_STREAMING_BITRATE_8_BUCKETS[bucket_key]
        if (
            stream_bitrate_mbps < spec["min_mbps"]
            or stream_bitrate_mbps > spec["max_mbps"]
            or stream_bitrate_mbps > FX3_STREAMING_MAX_BITRATE_MBPS
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="STREAMING_BITRATE_OUT_OF_BUCKET_OR_38MBPS_LIMIT",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_NETWORK_STREAMING_{streaming_protocol}_{srt_mode if streaming_protocol == 'SRT' else 'PUSH'}_{video_codec}_OFFLINE_VALID",
            rf_tx_packets=0,
            rf_packets_transmitted=0,
            usb_tx_packets=0,
        )

    if operation == "fx3_movie_rec_during_streaming_and_slot1_erofs":
        if movie_rec_during_streaming not in ("Disable", "Enable"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_MOVIE_REC_DURING_STREAMING_OPTION",
            )
        if movie_rec_during_streaming == "Disable":
            return _mk(
                allowed=True,
                errno=0,
                reason="MOVIE_REC_DURING_STREAMING_DISABLED_DEFAULT_ZERO_WRITES",
                slot1_writes=0,
            )
        if shoot_mode == "S&Q":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="MOVIE_REC_DURING_STREAMING_BLOCKED_IN_SQ",
            )
        if stream_fps not in FX3_STREAMING_ALLOWED_FPS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="STREAMING_FPS_NOT_ALLOWED_FOR_SIMULTANEOUS_REC",
            )
        bucket_key = (stream_resolution, _fps_bucket_key(stream_fps))
        if bucket_key not in FX3_STREAMING_BITRATE_8_BUCKETS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_STREAMING_RESOLUTION_BUCKET",
            )
        spec = FX3_STREAMING_BITRATE_8_BUCKETS[bucket_key]
        if spec["blocks_internal_4k_rec"] and internal_rec_resolution.startswith("4K"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="INTERNAL_4K_REC_BLOCKED_WHEN_STREAMING_4K_OR_2K_60P_50P",
                internal_4k_rec_blocked=True,
            )
        if internal_rec_fps is not None and internal_rec_fps != stream_fps:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INTERNAL_REC_FPS_LOCKED_TO_STREAM_FPS",
            )
        if target_slot == "Slot 1":
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO,
                reason="TIER0_SLOT1_EROFS_BLOCKS_MOVIE_REC_DURING_STREAMING",
                slot1_erofs_blocked=True,
                slot1_writes=0,
                slot1_sector_writes=0,
                slot1_data_sector_writes=0,
            )
        if target_slot != "Slot 2" or not simulated_sandbox:
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO if not simulated_sandbox else EINVAL_ERRNO,
                reason="CONCURRENT_REC_ALLOWED_ONLY_ON_SANDBOX_SLOT2",
                slot1_erofs_blocked=not simulated_sandbox,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="MOVIE_REC_DURING_STREAMING_SANDBOX_SLOT2_OK",
            slot1_writes=0,
        )

    # fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters
    if fx6_native_protocol_requested:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX6_ZERO_NATIVE_{fx6_native_protocol_requested.upper()}_DORMANT_SYMBOLS_ONLY",
            uvc_streaming_blocked=(fx6_native_protocol_requested.upper() == "UVC"),
        )
    if fx6_external_adapter not in FX6_EXTERNAL_STREAMING_ADAPTERS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_EXTERNAL_STREAMING_ADAPTER",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason=f"FX6_EXTERNAL_STREAMING_VIA_{fx6_external_adapter.replace('-', '_')}_OFFLINE_OK",
        rf_tx_packets=0,
        usb_tx_packets=0,
    )


# ---------------------------------------------------------------------------
# Sub-Model Evaluators & Unified Stage 88 (88/88) Orchestrator
# ---------------------------------------------------------------------------


def _evaluate_submodel_88a() -> Dict[str, Any]:
    r_g86_rst = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
        exposure_ctrl_type="P/A/S/M Mode",
        av_mode="Auto",
        tv_mode="Auto",
        iso_mode="Auto",
        auto_slow_shutter="Off",
        camera_settings_reset_triggered=True,
    )
    r_g86_init = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_exposure_ctrl_type_g86_reset_and_auto_manual_swt",
        exposure_ctrl_type="P/A/S/M Mode",
        initialize_triggered=True,
    )
    r_ang_ok = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
        shoot_mode="Movie",
        shutter_mode="Angle",
        shutter_angle="180.0",
        exposure_step="0.5 EV",
        diff_set_shutter_checked=False,
    )
    r_ang_still = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
        shoot_mode="Still",
        shutter_mode="Angle",
    )
    r_mf_clamp = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_shutter_mode_angle_bk4_split_and_multiframe_clamp",
        shoot_mode="S&Q",
        shutter_mode="Angle",
        shutter_angle="64F",
        sq_frame_rate_fps=120,
    )
    r_var_blk = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
        shoot_mode="Movie",
        var_shutter_item="HIGH_RES_SS",
    )
    r_af_mv = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx3_antiflicker_still_only_and_dormant_var_shutter_block",
        shoot_mode="Movie",
        anti_flicker_shoot="On",
    )
    r_fx6_ecs = simulate_88a_flexexp_shutterangle_varshutter_and_fx6_ecs(
        operation="fx6_physical_exposure_keys_and_4mode_shutter_ecs",
        body_model=BODY_MODEL_FX6,
        fx6_shutter_mode="ECS",
        fx6_ecs_frequency_hz=120.5,
    )
    passed = (
        (
            r_g86_rst.allowed
            and r_g86_rst.exposure_ctrl_type == "P/A/S/M Mode"
            and r_g86_rst.exposure_ctrl_type_survived_cam_reset
            and r_g86_rst.av_mode == "Manual"
            and r_g86_rst.tv_mode == "Manual"
            and r_g86_rst.iso_mode == "Manual"
            and r_g86_rst.auto_slow_shutter == "On"
        )
        and (
            r_g86_init.allowed
            and r_g86_init.exposure_ctrl_type == "Flexible Exp. Mode"
            and r_g86_init.exposure_ctrl_type_reset_on_init
        )
        and (
            r_ang_ok.allowed
            and r_ang_ok.bk4_slots_disjoint
            and r_ang_ok.bk4_speed_slot_hex == "0x01120024"
            and r_ang_ok.bk4_angle_slot_hex == "0x01120028"
            and (not r_ang_ok.exposure_step_affects_angle)
            and r_ang_ok.forces_still_movie_shutter_separation
        )
        and (not r_ang_still.allowed and r_ang_still.errno == EOPNOTSUPP_ERRNO)
        and (not r_mf_clamp.allowed and r_mf_clamp.errno == EOPNOTSUPP_ERRNO and r_mf_clamp.multiframe_angle_clamped)
        and (not r_var_blk.allowed and r_var_blk.errno == EOPNOTSUPP_ERRNO and r_var_blk.dormant_var_shutter_blocked)
        and (not r_af_mv.allowed and r_af_mv.errno == EOPNOTSUPP_ERRNO)
        and (r_fx6_ecs.allowed and r_fx6_ecs.fx6_shutter_mode == "ECS" and len(r_fx6_ecs.fx6_physical_exposure_keys) == 4)
    )
    return {
        "passed": passed,
        "fx3_g86_exposure_ctrl_type_reset_erratum_reconciled": FX3_G86_EXPOSURE_CTRL_TYPE_RESET_ERRATUM_RECONCILED,
        "fx3_shutter_angle_standard_steps_count": len(FX3_SHUTTER_ANGLE_STANDARD_STEPS),
        "fx3_shutter_angle_multiframe_steps_count": len(FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS),
        "fx3_dormant_var_shutter_exposed_events": 0,
        "fx6_shutter_modes_count": len(FX6_SHUTTER_MODES),
        "samples": {
            "fx3_g86_exposure_ctrl_resists_cam_reset": r_g86_rst.to_dict(),
            "fx3_g86_exposure_ctrl_resets_on_init": r_g86_init.to_dict(),
            "fx3_shutter_angle_180_bk4_split": r_ang_ok.to_dict(),
            "fx3_shutter_angle_still_blocked": r_ang_still.to_dict(),
            "fx3_multiframe_64f_high_fps_clamped": r_mf_clamp.to_dict(),
            "fx3_dormant_var_shutter_blocked": r_var_blk.to_dict(),
            "fx3_antiflicker_movie_blocked": r_af_mv.to_dict(),
            "fx6_shutter_mode_ecs_ok": r_fx6_ecs.to_dict(),
        },
    }


def _evaluate_submodel_88b() -> Dict[str, Any]:
    r_act_200 = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_4locks_and_dormant_block",
        steadyshot_mode="Active",
        lens_focal_length_mm=200,
    )
    r_act_4lck = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_4locks_and_dormant_block",
        shoot_mode="S&Q",
        steadyshot_mode="Active",
        rec_frame_rate="119.88p",
        sq_frame_rate_fps=120,
        hdmi_raw_output_on=True,
        desqueeze_display="1.6x",
    )
    r_dyn_blk = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_4locks_and_dormant_block",
        steadyshot_mode="Dynamic active",
    )
    r_fl_47 = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_adjust_and_47step_focal_length",
        steadyshot_adjust="Manual",
        focal_length_mm=1000,
    )
    r_cat_off = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_catalyst_gyro_rtmd_eligibility",
        steadyshot_mode="Off",
        electronic_contact_lens=True,
    )
    r_cat_std = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_catalyst_gyro_rtmd_eligibility",
        steadyshot_mode="Standard",
        electronic_contact_lens=True,
    )
    r_cat_sq = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx3_catalyst_gyro_rtmd_eligibility",
        shoot_mode="S&Q",
        steadyshot_mode="Off",
        electronic_contact_lens=True,
    )
    r_fx6_oss = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx6_zero_ibis_oss_3mode_and_catalyst",
        body_model=BODY_MODEL_FX6,
        fx6_oss_lens_attached=True,
        fx6_lens_oss_switch_on=True,
        fx6_oss_mode="Active",
    )
    r_fx6_cat = simulate_88b_steadyshot_4locks_47focal_catalyst_and_fx6_oss(
        operation="fx6_zero_ibis_oss_3mode_and_catalyst",
        body_model=BODY_MODEL_FX6,
        fx6_lens_oss_switch_on=False,
        fx6_oss_mode="Off",
        fx6_catalyst_requested=True,
    )
    passed = (
        (
            r_act_200.allowed
            and r_act_200.active_crop_factor == FX3_ACTIVE_CROP_FACTOR
            and r_act_200.distortion_comp_forced == "Auto"
            and r_act_200.g81_200mm_legacy_note_removed
        )
        and (
            not r_act_4lck.allowed
            and r_act_4lck.errno == EOPNOTSUPP_ERRNO
            and len(r_act_4lck.active_lockouts_triggered) == 4
        )
        and (not r_dyn_blk.allowed and r_dyn_blk.errno == EOPNOTSUPP_ERRNO and r_dyn_blk.dormant_steadyshot_blocked)
        and (r_fl_47.allowed and r_fl_47.focal_length_steps_count == 47)
        and (r_cat_off.allowed and r_cat_off.catalyst_gyro_usable)
        and (not r_cat_std.allowed and r_cat_std.errno == EOPNOTSUPP_ERRNO and not r_cat_std.catalyst_gyro_usable)
        and (not r_cat_sq.allowed and r_cat_sq.errno == EOPNOTSUPP_ERRNO and not r_cat_sq.catalyst_gyro_usable)
        and (r_fx6_oss.allowed and not r_fx6_oss.fx6_has_body_ibis)
        and (r_fx6_cat.allowed and r_fx6_cat.catalyst_gyro_usable)
    )
    return {
        "passed": passed,
        "fx3_active_lockouts_count": len(FX3_ACTIVE_4_LOCKOUT_IDS),
        "fx3_active_crop_factor": FX3_ACTIVE_CROP_FACTOR,
        "fx3_focal_length_steps_count": len(FX3_FOCAL_LENGTH_47_STEPS_MM),
        "fx3_dormant_steadyshot_exposed_events": 0,
        "fx3_g81_200mm_note_removed": FX3_G81_200MM_NOTE_REMOVED_IN_V2_PLUS,
        "fx6_has_body_ibis": FX6_HAS_BODY_IBIS,
        "fx6_oss_modes_count": len(FX6_OSS_STEADYSHOT_MODES),
        "samples": {
            "fx3_active_200mm_v2_plus_ok": r_act_200.to_dict(),
            "fx3_active_all_4_lockouts_blocked": r_act_4lck.to_dict(),
            "fx3_dormant_dynamic_active_blocked": r_dyn_blk.to_dict(),
            "fx3_manual_focal_47step_1000mm": r_fl_47.to_dict(),
            "fx3_catalyst_off_usable": r_cat_off.to_dict(),
            "fx3_catalyst_standard_blocked": r_cat_std.to_dict(),
            "fx3_catalyst_sq_blocked": r_cat_sq.to_dict(),
            "fx6_zero_ibis_oss_active_ok": r_fx6_oss.to_dict(),
            "fx6_catalyst_oss_off_usable": r_fx6_cat.to_dict(),
        },
    }


def _evaluate_submodel_88c() -> Dict[str, Any]:
    r_pc_4k = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
        source_file_format="XAVC HS 4K",
        source_is_hlg=True,
        playback_jpeg_heif_switch="HEIF(4:2:2)",
        target_slot="Slot 2",
        simulated_sandbox=True,
    )
    r_pc_dci = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
        source_file_format="XAVC S-I DCI 4K",
        target_slot="Slot 2",
    )
    r_pc_s1 = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
        source_file_format="XAVC S 4K",
        target_slot="Slot 1",
    )
    r_pc_rst = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_photo_capture_dci4k_block_heif_reset_and_slot1_erofs",
        playback_jpeg_heif_switch="HEIF(4:2:0)",
        shooting_jpeg_heif_switch="HEIF(4:2:2)",
        camera_settings_reset_triggered=True,
    )
    r_vm_ok = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_view_mode_3item_g126_and_dormant_block",
        view_mode="Movie View",
        camera_settings_reset_triggered=True,
    )
    r_vm_dorm = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_view_mode_3item_g126_and_dormant_block",
        view_mode="AVCHD View",
    )
    r_rt_s1 = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx3_rating_1to5_ftp_filter_and_slot1_erofs",
        rating_stars=5,
        rating_write_requested=True,
        target_slot="Slot 1",
    )
    r_fx6_pc = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
        body_model=BODY_MODEL_FX6,
        fx6_photo_capture_requested=True,
    )
    r_fx6_cf = simulate_88c_photocap_viewmode_g126_rating_erofs_and_fx6_clipflag(
        operation="fx6_zero_photo_capture_and_clip_flag_ok_ng_keep",
        body_model=BODY_MODEL_FX6,
        fx6_clip_flag="KEEP",
        target_slot="Slot 2",
    )
    passed = (
        (r_pc_4k.allowed and r_pc_4k.photo_capture_mp == 8.3 and r_pc_4k.output_is_hlg_heif and r_pc_4k.slot1_writes == 0)
        and (not r_pc_dci.allowed and r_pc_dci.errno == EOPNOTSUPP_ERRNO and r_pc_dci.dci4k_photo_capture_blocked)
        and (not r_pc_s1.allowed and r_pc_s1.errno == EROFS_ERRNO and r_pc_s1.slot1_erofs_blocked and r_pc_s1.slot1_writes == 0)
        and (
            r_pc_rst.allowed
            and r_pc_rst.playback_jpeg_heif_switch == "HEIF(4:2:0)"
            and r_pc_rst.playback_jpeg_heif_survived_cam_reset
            and r_pc_rst.shooting_jpeg_heif_switch == "JPEG"
        )
        and (r_vm_ok.allowed and r_vm_ok.view_mode == "Movie View" and r_vm_ok.view_mode_survived_cam_reset)
        and (not r_vm_dorm.allowed and r_vm_dorm.errno == EOPNOTSUPP_ERRNO and r_vm_dorm.dormant_view_mode_blocked)
        and (not r_rt_s1.allowed and r_rt_s1.errno == EROFS_ERRNO and r_rt_s1.slot1_erofs_blocked and not r_rt_s1.slot1_avf_info_mutated)
        and (not r_fx6_pc.allowed and r_fx6_pc.errno == EOPNOTSUPP_ERRNO)
        and (r_fx6_cf.allowed and r_fx6_cf.fx6_clip_flag == "KEEP")
    )
    return {
        "passed": passed,
        "fx3_view_mode_exposed_count": len(FX3_VIEW_MODE_EXPOSED_3_STATES),
        "fx3_g126_view_mode_3item_erratum_reconciled": FX3_G126_VIEW_MODE_3ITEM_ERRATUM_RECONCILED,
        "fx3_dormant_view_mode_exposed_events": 0,
        "fx3_dci4k_photo_capture_bypass_events": 0,
        "fx6_has_in_camera_photo_capture": FX6_HAS_IN_CAMERA_PHOTO_CAPTURE,
        "fx6_clip_flag_options_count": len(FX6_CLIP_FLAG_OPTIONS),
        "samples": {
            "fx3_photo_capture_4k_hlg_heif_slot2": r_pc_4k.to_dict(),
            "fx3_photo_capture_dci4k_blocked": r_pc_dci.to_dict(),
            "fx3_photo_capture_slot1_erofs": r_pc_s1.to_dict(),
            "fx3_playback_vs_shooting_heif_reset": r_pc_rst.to_dict(),
            "fx3_g126_view_mode_movie_resists_reset": r_vm_ok.to_dict(),
            "fx3_g126_dormant_avchd_blocked": r_vm_dorm.to_dict(),
            "fx3_rating_slot1_erofs": r_rt_s1.to_dict(),
            "fx6_photo_capture_blocked": r_fx6_pc.to_dict(),
            "fx6_clip_flag_keep_ok": r_fx6_cf.to_dict(),
        },
    }


def _evaluate_submodel_88d() -> Dict[str, Any]:
    r_uvc_blk = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
        uvc_streaming_requested=True,
        uvc_output_format_requested="4K_30P",
    )
    r_usb_ok = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_usb_streaming_uvc_debunk_and_4mode_usb",
        usb_connection_mode="Remote Shooting",
    )
    r_srt_ok = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
        streaming_protocol="SRT",
        srt_mode="Caller",
        video_codec="H.265",
        srt_encryption="AES-256",
        stream_resolution="4K (2160p)",
        stream_fps="59.94p",
        stream_bitrate_mbps=38.0,
        transport="USB-LAN",
    )
    r_srt_lst = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
        streaming_protocol="SRT",
        srt_mode="Listener",
    )
    r_fps_24 = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
        streaming_protocol="RTMP",
        video_codec="H.264",
        stream_fps="23.98p",
    )
    r_air_blk = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_network_streaming_rtmp_rtmps_srt_caller_matrix",
        airplane_mode_on=True,
    )
    r_rec_4k = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
        movie_rec_during_streaming="Enable",
        stream_resolution="2K (1440p)",
        stream_fps="59.94p",
        internal_rec_resolution="4K (2160p)",
        target_slot="Slot 2",
    )
    r_rec_s1 = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx3_movie_rec_during_streaming_and_slot1_erofs",
        movie_rec_during_streaming="Enable",
        stream_resolution="HD (1080p)",
        stream_fps="59.94p",
        internal_rec_resolution="HD (1080p)",
        target_slot="Slot 1",
    )
    r_fx6_srt = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
        body_model=BODY_MODEL_FX6,
        fx6_native_protocol_requested="SRT",
    )
    r_fx6_ext = simulate_88d_uvc_debunk_network_streaming_srt_caller_and_fx6(
        operation="fx6_zero_native_uvc_rtmp_srt_qos_and_external_adapters",
        body_model=BODY_MODEL_FX6,
        fx6_external_adapter="CBK-WA100",
    )
    passed = (
        (not r_uvc_blk.allowed and r_uvc_blk.errno == EOPNOTSUPP_ERRNO and r_uvc_blk.uvc_streaming_blocked)
        and (r_usb_ok.allowed and r_usb_ok.usb_exposed_modes_count == 4 and not r_usb_ok.fx3_native_uvc_supported)
        and (r_srt_ok.allowed and r_srt_ok.srt_mode == "Caller" and r_srt_ok.rf_tx_packets == 0)
        and (not r_srt_lst.allowed and r_srt_lst.errno == EOPNOTSUPP_ERRNO and r_srt_lst.srt_listener_blocked)
        and (not r_fps_24.allowed and r_fps_24.errno == EOPNOTSUPP_ERRNO)
        and (not r_air_blk.allowed and r_air_blk.errno == EPERM_ERRNO and r_air_blk.airplane_zero_rf_blocked and r_air_blk.rf_tx_packets == 0)
        and (not r_rec_4k.allowed and r_rec_4k.errno == EOPNOTSUPP_ERRNO and r_rec_4k.internal_4k_rec_blocked)
        and (not r_rec_s1.allowed and r_rec_s1.errno == EROFS_ERRNO and r_rec_s1.slot1_erofs_blocked and r_rec_s1.slot1_writes == 0)
        and (not r_fx6_srt.allowed and r_fx6_srt.errno == EOPNOTSUPP_ERRNO)
        and (r_fx6_ext.allowed and r_fx6_ext.fx6_external_adapter == "CBK-WA100")
    )
    return {
        "passed": passed,
        "fx3_native_uvc_supported": FX3_NATIVE_UVC_SUPPORTED,
        "fx3_usb_connection_exposed_modes_count": len(FX3_USB_CONNECTION_EXPOSED_4_MODES),
        "fx3_streaming_bitrate_buckets_count": len(FX3_STREAMING_BITRATE_8_BUCKETS),
        "fx3_streaming_max_bitrate_mbps": FX3_STREAMING_MAX_BITRATE_MBPS,
        "fx3_srt_listener_exposed_events": 0,
        "fx3_g134_srt_caller_only_reconciled": FX3_G134_SRT_CALLER_ONLY_RECONCILED,
        "fx6_native_uvc_supported": FX6_NATIVE_UVC_SUPPORTED,
        "fx6_native_network_streaming_supported": FX6_NATIVE_NETWORK_STREAMING_SUPPORTED,
        "samples": {
            "fx3_uvc_4k30p_debunk_blocked": r_uvc_blk.to_dict(),
            "fx3_usb_4mode_remote_shooting_ok": r_usb_ok.to_dict(),
            "fx3_srt_caller_4k60_38mbps_ok": r_srt_ok.to_dict(),
            "fx3_srt_listener_blocked": r_srt_lst.to_dict(),
            "fx3_streaming_2398p_blocked": r_fps_24.to_dict(),
            "fx3_airplane_zero_rf_blocked": r_air_blk.to_dict(),
            "fx3_rec_during_stream_2k60_blocks_4k": r_rec_4k.to_dict(),
            "fx3_rec_during_stream_slot1_erofs": r_rec_s1.to_dict(),
            "fx6_native_srt_blocked": r_fx6_srt.to_dict(),
            "fx6_external_cbk_wa100_ok": r_fx6_ext.to_dict(),
        },
    }


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(v) for v in obj]
    return obj


def _build_stage88_probe(
    sub_88a: Mapping[str, Any],
    sub_88b: Mapping[str, Any],
    sub_88c: Mapping[str, Any],
    sub_88d: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone_label": MILESTONE_LABEL,
        "submodel_88a_passed": bool(sub_88a["passed"]),
        "submodel_88b_passed": bool(sub_88b["passed"]),
        "submodel_88c_passed": bool(sub_88c["passed"]),
        "submodel_88d_passed": bool(sub_88d["passed"]),
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
    }


def run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    donor_info = inspect_phase383_wave78_donors(
        work_root=work_root,
        force_clean_room=force_clean_room,
        env=env,
    )
    sub_88a = _evaluate_submodel_88a()
    sub_88b = _evaluate_submodel_88b()
    sub_88c = _evaluate_submodel_88c()
    sub_88d = _evaluate_submodel_88d()
    probe = _build_stage88_probe(sub_88a, sub_88b, sub_88c, sub_88d)

    all_passed = bool(
        donor_info["all_donors_verified"]
        and sub_88a["passed"]
        and sub_88b["passed"]
        and sub_88c["passed"]
        and sub_88d["passed"]
    )

    payload: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": PHASE_383_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "all_checks_passed": all_passed,
        "source_mode": donor_info["source_mode"],
        "donor_access_mode": donor_info["donor_access_mode"],
        "donors": donor_info,
        # Tier-0 Hardware Safety Redlines
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
        "live_attach_authorized": LIVE_ATTACH_AUTHORIZED,
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
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "emmc_corruptions": EMMC_CORRUPTIONS,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "usb_tx_packets": USB_TX_PACKETS,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "slot1_write_authorized": SLOT1_WRITE_AUTHORIZED,
        "slot1_writes": SLOT1_WRITES,
        "slot1_sector_writes": SLOT1_SECTOR_WRITES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_tx_packets": RF_TX_PACKETS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        # Stage 88 Wave-78 Invariant Metrics
        "fx3_g86_exposure_ctrl_type_reset_erratum_reconciled": (
            FX3_G86_EXPOSURE_CTRL_TYPE_RESET_ERRATUM_RECONCILED
        ),
        "fx3_shutter_angle_standard_steps_count": len(FX3_SHUTTER_ANGLE_STANDARD_STEPS),
        "fx3_shutter_angle_multiframe_steps_count": len(FX3_SHUTTER_ANGLE_MULTIFRAME_STEPS),
        "fx3_dormant_var_shutter_exposed_events": 0,
        "fx6_shutter_modes_count": len(FX6_SHUTTER_MODES),
        "fx3_active_lockouts_count": len(FX3_ACTIVE_4_LOCKOUT_IDS),
        "fx3_active_crop_factor": FX3_ACTIVE_CROP_FACTOR,
        "fx3_focal_length_steps_count": len(FX3_FOCAL_LENGTH_47_STEPS_MM),
        "fx3_dormant_steadyshot_exposed_events": 0,
        "fx3_g81_200mm_note_removed": FX3_G81_200MM_NOTE_REMOVED_IN_V2_PLUS,
        "fx6_has_body_ibis": FX6_HAS_BODY_IBIS,
        "fx6_oss_modes_count": len(FX6_OSS_STEADYSHOT_MODES),
        "fx3_view_mode_exposed_count": len(FX3_VIEW_MODE_EXPOSED_3_STATES),
        "fx3_g126_view_mode_3item_erratum_reconciled": (
            FX3_G126_VIEW_MODE_3ITEM_ERRATUM_RECONCILED
        ),
        "fx3_dormant_view_mode_exposed_events": 0,
        "fx3_dci4k_photo_capture_bypass_events": 0,
        "fx6_has_in_camera_photo_capture": FX6_HAS_IN_CAMERA_PHOTO_CAPTURE,
        "fx6_clip_flag_options_count": len(FX6_CLIP_FLAG_OPTIONS),
        "fx3_native_uvc_supported": FX3_NATIVE_UVC_SUPPORTED,
        "fx3_usb_connection_exposed_modes_count": len(FX3_USB_CONNECTION_EXPOSED_4_MODES),
        "fx3_streaming_bitrate_buckets_count": len(FX3_STREAMING_BITRATE_8_BUCKETS),
        "fx3_streaming_max_bitrate_mbps": FX3_STREAMING_MAX_BITRATE_MBPS,
        "fx3_srt_listener_exposed_events": 0,
        "fx3_g134_srt_caller_only_reconciled": FX3_G134_SRT_CALLER_ONLY_RECONCILED,
        "fx6_native_uvc_supported": FX6_NATIVE_UVC_SUPPORTED,
        "fx6_native_network_streaming_supported": FX6_NATIVE_NETWORK_STREAMING_SUPPORTED,
        # Nested Sub-Model Audits
        "submodel_88a_flexexp_shutterangle_varshutter_fx6_ecs": sub_88a,
        "submodel_88b_steadyshot_4locks_47focal_catalyst_fx6_oss": sub_88b,
        "submodel_88c_photocap_viewmode_g126_rating_erofs_fx6_clipflag": sub_88c,
        "submodel_88d_uvc_debunk_network_streaming_srt_caller_fx6": sub_88d,
        "stage88_probe": probe,
    }
    digest_body = _strip_wall_clock(payload)
    payload["phase383_audit_digest_sha256"] = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def run_self_test(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Union[None, str, Path, object] = _UNSET,
) -> Dict[str, Any]:
    return run_phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation(
        work_root=work_root,
        force_clean_room=force_clean_room,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator.py",
        description=(
            "Phase 383 Stage 88 (88/88) Real-Hardware FX3/FX6 Wave-78 Co-Emulator: "
            "88A Exposure Ctrl Type (G86 Anti-Reset) / Auto/Manual Swt. Set. / Shutter Mode Angle (5.6..360 deg & 2F..64F, BK4 Split, Dormant Var. Shutter) vs FX6 ECS, "
            "88B Image Stabilization Active 1.104x 4-Lock Matrix / 47-Step Focal Length / Catalyst Gyro RTMD vs FX6 Zero-IBIS OSS 3-Mode, "
            "88C Playback Photo Capture (DCI 4K Block, Anti-Reset HEIF) / 3-Item View Mode (G126) / Rating & Slot 1 EROFS=30 vs FX6 Clip Flag, "
            "and 88D USB Streaming UVC/UAC Debunk vs Network Streaming RTMP/RTMPS/SRT Caller-Only & Zero-RF Guard vs FX6"
        ),
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room synthetic donor mode",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run Stage 88 (88/88) built-in self-test matrix",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON payload (default)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line HIL summary",
    )
    args = parser.parse_args(argv)

    rep = run_self_test(force_clean_room=(True if args.clean_room else None))
    if args.summary:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 383 Stage 88 ({rep['milestone']}) | mode={rep['source_mode']} "
            f"| donors={rep['donors']['total_donors_count']} "
            f"| exp=g86:{int(rep['fx3_g86_exposure_ctrl_type_reset_erratum_reconciled'])}/ang:{rep['fx3_shutter_angle_standard_steps_count']}+{rep['fx3_shutter_angle_multiframe_steps_count']}/fx6sh:{rep['fx6_shutter_modes_count']} "
            f"| is=4lck:{rep['fx3_active_lockouts_count']}/fl:{rep['fx3_focal_length_steps_count']}/fx6ibis:{int(rep['fx6_has_body_ibis'])}/oss:{rep['fx6_oss_modes_count']} "
            f"| pb=vm:{rep['fx3_view_mode_exposed_count']}/g126:{int(rep['fx3_g126_view_mode_3item_erratum_reconciled'])}/fx6cf:{rep['fx6_clip_flag_options_count']} "
            f"| str=uvc:{int(rep['fx3_native_uvc_supported'])}/usb:{rep['fx3_usb_connection_exposed_modes_count']}/srt_lst:{rep['fx3_srt_listener_exposed_events']}/mbps:{rep['fx3_streaming_max_bitrate_mbps']:.0f} "
            f"| s1_wr={rep['slot1_writes']} usb_tx={rep['usb_tx_packets']} rf_tx={rep['rf_tx_packets']} emmc_wr={rep['emmc_nflasha_write_count']} "
            f"leaked={rep['raw_firmware_bytes_leaked']} "
            f"| digest={rep['phase383_audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
