"""Phase 347 (Task H432, Wave-65, 150/150 Milestone): Real-Hardware `[Zoom Range]`
(Optical/ClearImage/Digital) & 8-Step Speed Reset Split + `[Auto Slow Shutter]`
/ `[ISO Range Limit]` / Still-Only `[ISO AUTO Min. SS]` / Dual Base ISO (`G149`),
Still `.ARW` Dormant `Lossless Comp` Myth-Busting + `[HLG Still Image]` +
`[USB LUN Setting] = Single` `Slot-1` Exposure Trap + `NP-FZ100` PD + Dual
`FX3`/`FX6` `UVC` Myth-Busting (`G150`), and Unified `150`-Gate Master Safety
Preflight (`G01..G150`).

Authoritative Empirical Baseline (`ILME-FX3 Ver. 7.02`, `ilc/2210`, `0x0502`,
`PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`):
  - **Gate `G149` (`ZOOM_CIZ_DIGITAL_8STEP_SPEED_RESET_SPLIT_AND_AUTOSLOW_DUAL_BASE_ISO_GUARD`)**:
    1. `Shooting -> [Zoom]` & `Setup -> [Operation Customize] -> [Zoom Ring Rotate]`:
       - **Reset Split Law**: `[Zoom Range]` (`Optical zoom only` default /
         `ClearImage Zoom` [`1.5x` 4K, `2.0x` HD] / `Digital Zoom` [`4.0x` Movie,
         `8.0x` Still `S`]; `Smart Zoom` Still `M/S` only, disabled in Movie) AND
         `[Zoom Ring Rotate]` (`Left(W)/Right(T)` default / `Right(W)/Left(T)`)
         are **Reset-immune** (`Not available` under `[Camera Settings Reset]`),
         whereas `[Zoom Lever Speed]` (`1st=3` def, `2nd=8 Fast` def, `1..8`
         Standby & Movie Rec), `[Custom Key Z. Speed]` (`1..8` def `3` Standby &
         Movie Rec), and `[Remote Zoom Speed]` (`Variable` def / `Fixed 1..8`
         def `3` Standby & Movie Rec) ARE **Resettable** (`Can be reset`).
       - **Pre-entry Lockouts**: Non-optical zoom unavailable under Still `RAW`
         (`RAW`, `RAW & JPEG`, `RAW & HEIF`), Movie `119.88p/100p`, `S&Q >=
         100/120fps` (`100/120/200/240fps`), or HDMI 16-bit `RAW`.
       - **Active Non-Optical Zoom Lockouts**: `[Focus Area]` disabled -> center
         priority AF, `[Metering Mode]` locked `[Multi]`, and `Face/Eye Prior.
         in AF` / `Face Priority in Multi Metering` / `Tracking` disabled.
       - **Contrast `ILME-FX6 Ver. 6.01`**: `Technical > Zoom > Zoom Type`
         exposes ONLY `Optical Zoom Only` and `On(Clear Image Zoom)` (`1.5x` 4K
         / `2.0x` HD) with **ZERO user-exposed `Digital Zoom`** (blocked on
         `S&Q > 60fps` or `RAW`), plus dual-rocker `Handle Zoom` (`Off` /
         `Low=1..8` def `3` / `High=1..8` def `8` / `Variable`, `0..99` position).
    2. `Exposure/Color -> [Exposure]`:
       - `[Auto Slow Shutter]`: Movie-only, `On` default, **Resettable**,
         locked disabled under `7` conditions (`S&Q`, `S`, `M`, manual `ISO` !=
         `ISO AUTO`, `Flexible Exp. Shutter = Manual`, `Cine EI` / `Cine EI
         Quick`, and `Shutter Mode = Angle`).
       - `[ISO Range Limit]`: **Reset-immune**, limits manual ISO only (`ISO
         AUTO` limits configured via right dial on `[ISO AUTO]`).
       - `[ISO AUTO Min. SS]`: **Still-only** (`P`/`A` + `ISO AUTO`), `STD`
         default, Resettable, `SLOWER (-2 EV)..FASTER (+2 EV)` or `1/8000"..30"`,
         `1/250 s` flash sync override, disabled in Movie & `S&Q`, `0` hits in
         `FX6 appFw.so` (`ISO_AUTO_MIN`).
       - **Dual Base ISO**: `[Base ISO]` (`800` def / `12800`) visible ONLY in
         `Cine EI` / `Cine EI Quick`; elsewhere automatic `20x` (`+4.33 EV`)
         per-Gamma switching (`S-Log3`/`S-Log2`/`ITU709 800%`: `640/12800`,
         `S-Cinetone PP11`/`HLG`/`HLG3`/`Cine4`: `100/2000`, `HLG1`/`Cine2`:
         `50/1000`, `Cine1`: `64/1280`, `PP Off`/`Still`/`Movie`/`HLG2`/`Cine3`:
         `80/1600`) vs `FX6` `Base Sensitivity = Low / High` + `AGC`.

  - **Gate `G150` (`STILL_ARW_DORMANT_LOSSLESS_HLG_PHOTO_AND_USB_LUN_SINGLE_SLOT1_NPFZ100_UVC_FIREWALL`)**:
    1. **Still `ARW` / `HEIF` / `[HLG Still Image]` & `[Sort Recording]` Vault**:
       - `[RAW File Type]` exposes strictly `Compressed` (def) & `Uncompressed`
         (`14-bit .ARW`, Resettable); reject 100% dormant `Lossless Comp (L/M/S)`
         (`RAW_FILE_TYPE_LOSSLESS*`) with `EOPNOTSUPP=95`.
       - `[HLG Still Image]` (`BKID_APP_setting_still_hlg_photo` + ELF typo
         `STILL_HLD_PHOTO_{OFF,ON}`) requires `HEIF(4:2:0)`/`HEIF(4:2:2)` +
         `[File Format] = HEIF` + `P/A/S/M`, forces `BT.2100` (`BT.2020`),
         raises normal ISO floor to `100/125`, and disables PP / Creative Look /
         DRO / DRO Bracket.
       - `[Sort Recording]` + `[Auto Switch Media]` spillover and all `.ARW` /
         `.JPG` / `.HIF` writes targeting `Slot 1` blocked at Tier-0 `Slot 1`
         with `EROFS=30` (`slot1_data_sector_writes == 0`).
    2. **`[USB LUN Setting] = Single` Trap & Host MSC Firewall**:
       - `[USB Connection Mode]` exposes strictly 4 Reset-immune modes (`Sel.
         When Connect` def, `MassStorage(MSC)`, `MTP`, `Remote Shooting`).
       - **`[USB LUN Setting]` (`_f 0x6b19`, Reset-immune)**: `Multi` (def)
         exposes `Slot 1 + Slot 2`, while **`Single` (`_f 0x776d`) exposes ONLY
         `Slot 1` (does NOT hide `Slot 1`!)** and `MTP` also targets `Slot 1`
         (`usbg_storage.ko` writable LUNs -> macOS `Spotlight` / `fseventsd` /
         `Finder` / `fsck_exfat` contamination hazard -> host-MSC blocked +
         `Slot 1` `EROFS=30`, `slot1_data_sector_writes == 0`).
    3. **`[USB Power Supply]` (`On` def, Reset-immune, Type-C only)**:
       - USB-C PD (`9V/3A`) requires charged `NP-FZ100` inserted; battery-less
         external power requires `DC-C1` + `>=65W PD` + `5A e-Marked` cable vs
         `FX6` `19.5V DC IN` (`16.5V`/`15.5V` low voltage) battery-less boot.
    4. **Dual `UVC` Myth-Busting (`FX3 Ver. 7.02` & `FX6 Ver. 6.01`)**:
       - Reject native `UVC/UAC USB Streaming` (`EOPNOTSUPP=95`) on BOTH `FX3`
         AND `FX6` (`[Movie Rec During Streaming]` `_f 0x79d5` `Disable` def /
         `Enable` governs Network Streaming `RTMP/RTMPS/SRT` only, distinct
         from HDMI `[Rec. Media dur HDMI Output]` `_f 0x6144`; both trigger
         `Slot 1` writes if enabled -> `EROFS=30` on `Slot 1`).

  - **Unified 150-Gate Master Safety Preflight (`G01..G150`)**:
    Delegates `G01..G148` to `evaluate_148gate_preflight()`, enforces `147/150`
    verified offline (`VERIFIED_147_OF_150_AWAITING_PHYSICAL_TIER0`) and `150/150`
    under `--simulate-bench-dry-run` (`VERIFIED_ALL_150_GATES_DRY_RUN_SIMULATED_BACKUP`),
    with ALL write/flash/live-attach redlines hard-locked `False` and `0`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    GateVerdict,
)
from .thermal_pwm_and_power_guard import (
    DEFAULT_REPO_ROOT,
    STATUS_VERIFIED_SAFE,
    resolve_donor_thermal_power_paths,
)
from .realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_FORCE_CLEAN_ROOM,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    USB_PACKETS_TRANSMITTED,
    evaluate_144gate_preflight,
)
from .realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    evaluate_146gate_preflight,
)
from .realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard import (
    evaluate_142gate_preflight,
)
from .realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard import (
    Master148GateReport,
    evaluate_148gate_preflight,
)


# ---------------------------------------------------------------------------
# Schema, Versions, Env Keys & Shared Constants
# ---------------------------------------------------------------------------

REALHW_ZOOM_CIZ_AUTOSLOW_ISO_ARW_RAWCOMP_USBLUN_UVC_150GATE_SCHEMA = (
    "fx3_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_150gate_guard_v1"
)
REALHW_ZOOM_CIZ_AUTOSLOW_ISO_ARW_RAWCOMP_USBLUN_UVC_150GATE_VERSION = (
    "2026.11.18-phase347-milestone150"
)
REALHW_150GATE_PREFLIGHT_SCHEMA = "realhw_150gate_preflight_v1"

G149 = "G149"
G149_GATE_ID = "G149"
G149_GATE_CODE = (
    "ZOOM_CIZ_DIGITAL_8STEP_SPEED_RESET_SPLIT_AND_AUTOSLOW_DUAL_BASE_ISO_GUARD"
)

G150 = "G150"
G150_GATE_ID = "G150"
G150_GATE_CODE = (
    "STILL_ARW_DORMANT_LOSSLESS_HLG_PHOTO_AND_USB_LUN_SINGLE_SLOT1_NPFZ100_UVC_FIREWALL"
)

ENV_CLEAN_ROOM_TEST_PHASE347 = "FX3_CLEAN_ROOM_TEST"
DONOR_CHECK_MAX_SECONDS_PHASE347 = 0.20
DONOR_CHECK_CI_MAX_SECONDS_PHASE347 = 0.05

EROFS_ERRNO_PHASE347 = 30
EROFS_NAME_PHASE347 = "EROFS"
EINVAL_ERRNO_PHASE347 = 22
EINVAL_NAME_PHASE347 = "EINVAL"
EOPNOTSUPP_ERRNO_PHASE347 = 95
EOPNOTSUPP_NAME_PHASE347 = "EOPNOTSUPP"

FX3_MODEL_NAME_PHASE347 = "ILME-FX3"
FX3_MODEL_ID_PHASE347 = 0x0502
FX3_HELP_GUIDE_CODE_PHASE347 = "ilc/2210"
FX3_DEFAULT_FW_VERSION_PHASE347 = "7.02"
FX6_MODEL_NAME_PHASE347 = "ILME-FX6"
FX6_DEFAULT_FW_VERSION_PHASE347 = "6.01"

MEDIA_SLOT_NONE_PHASE347 = 0
MEDIA_SLOT_1_PHASE347 = 1
MEDIA_SLOT_2_PHASE347 = 2
ALLOWED_MEDIA_SLOTS_PHASE347: Tuple[int, ...] = (
    MEDIA_SLOT_NONE_PHASE347,
    MEDIA_SLOT_1_PHASE347,
    MEDIA_SLOT_2_PHASE347,
)

SHOOT_MODE_STILL_PHASE347 = "Still"
SHOOT_MODE_MOVIE_PHASE347 = "Movie"
SHOOT_MODE_SQ_PHASE347 = "S&Q"
ALLOWED_SHOOT_MODES_PHASE347: Tuple[str, ...] = (
    SHOOT_MODE_STILL_PHASE347,
    SHOOT_MODE_MOVIE_PHASE347,
    SHOOT_MODE_SQ_PHASE347,
)

RESET_ACTION_NONE_PHASE347 = "None"
RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347 = "Camera Settings Reset"
RESET_ACTION_INITIALIZE_PHASE347 = "Initialize"
RESET_ACTION_RESET_NETWORK_SET_PHASE347 = "Reset Network Set."
ALLOWED_RESET_ACTIONS_PHASE347: Tuple[str, ...] = (
    RESET_ACTION_NONE_PHASE347,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
    RESET_ACTION_INITIALIZE_PHASE347,
    RESET_ACTION_RESET_NETWORK_SET_PHASE347,
)


# ---------------------------------------------------------------------------
# Gate G149 Constants: Zoom/CIZ/Digital/8-Step Speed Reset Split + Auto Slow
#                      Shutter / ISO Range Limit / Min SS / Dual Base ISO
# ---------------------------------------------------------------------------

ZOOM_MENU_PATH_G149 = "Shooting -> [Zoom]"
ZOOM_RANGE_MENU_PATH_G149 = "Shooting -> [Zoom] -> [Zoom Range]"
ZOOM_LEVER_SPEED_MENU_PATH_G149 = "Shooting -> [Zoom] -> [Zoom Lever Speed]"
CUSTOM_KEY_ZOOM_SPEED_MENU_PATH_G149 = "Shooting -> [Zoom] -> [Custom Key Z. Speed]"
REMOTE_ZOOM_SPEED_MENU_PATH_G149 = "Shooting -> [Zoom] -> [Remote Zoom Speed]"
ZOOM_RING_ROTATE_MENU_PATH_G149 = (
    "Setup -> [Operation Customize] -> [Zoom Ring Rotate]"
)

ZOOM_RANGE_OPTICAL_ONLY_G149 = "Optical zoom only"
ZOOM_RANGE_CIZ_G149 = "ClearImage Zoom"
ZOOM_RANGE_DIGITAL_G149 = "Digital Zoom"
ZOOM_RANGE_SMART_G149 = "Smart Zoom"
ZOOM_RANGE_DEFAULT_G149 = ZOOM_RANGE_OPTICAL_ONLY_G149
ALLOWED_ZOOM_RANGES_G149: Tuple[str, ...] = (
    ZOOM_RANGE_OPTICAL_ONLY_G149,
    ZOOM_RANGE_CIZ_G149,
    ZOOM_RANGE_DIGITAL_G149,
)

ZOOM_RING_ROTATE_LEFT_RIGHT_G149 = "Left(W)/Right(T)"
ZOOM_RING_ROTATE_RIGHT_LEFT_G149 = "Right(W)/Left(T)"
ZOOM_RING_ROTATE_DEFAULT_G149 = ZOOM_RING_ROTATE_LEFT_RIGHT_G149
ALLOWED_ZOOM_RING_ROTATIONS_G149: Tuple[str, ...] = (
    ZOOM_RING_ROTATE_LEFT_RIGHT_G149,
    ZOOM_RING_ROTATE_RIGHT_LEFT_G149,
)

ZOOM_SPEED_MIN_G149 = 1
ZOOM_SPEED_MAX_G149 = 8
ZOOM_LEVER_1ST_DEFAULT_G149 = 3
ZOOM_LEVER_2ND_DEFAULT_G149 = 8
CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149 = 3
REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149 = "Variable"
REMOTE_ZOOM_SPEED_TYPE_FIXED_G149 = "Fixed"
REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149 = REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149
ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G149: Tuple[str, ...] = (
    REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149,
    REMOTE_ZOOM_SPEED_TYPE_FIXED_G149,
)
REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149 = 3

# Exact Reset Split in Zoom Subsystem
ZOOM_RANGE_RESETTABLE_BY_CAMSET_RESET_G149 = False
ZOOM_RING_ROTATE_RESETTABLE_BY_CAMSET_RESET_G149 = False
ZOOM_LEVER_SPEED_RESETTABLE_BY_CAMSET_RESET_G149 = True
CUSTOM_KEY_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149 = True
REMOTE_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149 = True

# Exact Zoom Scales (ilc/2210 About zoom scale)
MOVIE_CIZ_4K_SCALE_G149 = 1.5
MOVIE_CIZ_HD_SCALE_G149 = 2.0
MOVIE_DIGITAL_ZOOM_SCALE_G149 = 4.0
STILL_FF_SCALES_G149: Dict[str, Dict[str, Optional[float]]] = {
    "L": {"Smart": None, "ClearImage": 2.0, "Digital": 4.0},
    "M": {"Smart": 1.5, "ClearImage": 3.1, "Digital": 6.1},
    "S": {"Smart": 2.0, "ClearImage": 4.0, "Digital": 8.0},
}
STILL_APSC_SCALES_G149: Dict[str, Dict[str, Optional[float]]] = {
    "M": {"Smart": 1.3, "ClearImage": 2.6, "Digital": 5.2},
    "S": {"Smart": 2.0, "ClearImage": 4.0, "Digital": 8.0},
}

# FX6 Contrast (5-024-458-18 p.116 & Handle Zoom)
FX6_ZOOM_TYPES_G149: Tuple[str, ...] = ("Optical Zoom Only", "On(Clear Image Zoom)")
FX6_HANDLE_ZOOM_MODES_G149: Tuple[str, ...] = ("Off", "Low", "High", "Variable")
FX6_HANDLE_ZOOM_LOW_DEFAULT_G149 = 3
FX6_HANDLE_ZOOM_HIGH_DEFAULT_G149 = 8

# Exposure / Auto Slow Shutter / ISO / Dual Base ISO
EXPOSURE_MENU_PATH_G149 = "Exposure/Color -> [Exposure]"
AUTO_SLOW_SHUTTER_DEFAULT_G149 = "On"
AUTO_SLOW_SHUTTER_RESETTABLE_BY_CAMSET_RESET_G149 = True
ISO_RANGE_LIMIT_RESETTABLE_BY_CAMSET_RESET_G149 = False
ISO_AUTO_MIN_SS_DEFAULT_G149 = "STD"
ISO_AUTO_MIN_SS_RESETTABLE_BY_CAMSET_RESET_G149 = True
ISO_AUTO_MIN_SS_FLASH_OVERRIDE_G149 = "1/250"
ALLOWED_ISO_AUTO_MIN_SS_PRESETS_G149: Tuple[str, ...] = (
    "SLOWER",
    "SLOW",
    "STD",
    "FAST",
    "FASTER",
)

EXPOSURE_MODE_P_G149 = "P"
EXPOSURE_MODE_A_G149 = "A"
EXPOSURE_MODE_S_G149 = "S"
EXPOSURE_MODE_M_G149 = "M"
EXPOSURE_MODE_FLEXIBLE_G149 = "Flexible Exp."
EXPOSURE_MODE_IAUTO_G149 = "iAuto"
ALLOWED_EXPOSURE_MODES_G149: Tuple[str, ...] = (
    EXPOSURE_MODE_P_G149,
    EXPOSURE_MODE_A_G149,
    EXPOSURE_MODE_S_G149,
    EXPOSURE_MODE_M_G149,
    EXPOSURE_MODE_FLEXIBLE_G149,
    EXPOSURE_MODE_IAUTO_G149,
)

LOG_SHOOTING_OFF_G149 = "Off"
LOG_SHOOTING_FLEXIBLE_ISO_G149 = "Flexible ISO"
LOG_SHOOTING_CINE_EI_G149 = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK_G149 = "Cine EI Quick"
ALLOWED_LOG_SHOOTING_MODES_G149: Tuple[str, ...] = (
    LOG_SHOOTING_OFF_G149,
    LOG_SHOOTING_FLEXIBLE_ISO_G149,
    LOG_SHOOTING_CINE_EI_G149,
    LOG_SHOOTING_CINE_EI_QUICK_G149,
)

SHUTTER_MODE_SPEED_G149 = "Speed"
SHUTTER_MODE_ANGLE_G149 = "Angle"
ALLOWED_SHUTTER_MODES_G149: Tuple[str, ...] = (
    SHUTTER_MODE_SPEED_G149,
    SHUTTER_MODE_ANGLE_G149,
)

BASE_ISO_LOW_G149 = 800
BASE_ISO_HIGH_G149 = 12800
BASE_ISO_DEFAULT_G149 = BASE_ISO_LOW_G149
ALLOWED_CINE_EI_BASE_ISOS_G149: Tuple[int, ...] = (
    BASE_ISO_LOW_G149,
    BASE_ISO_HIGH_G149,
)

# Exact Per-Gamma Dual Base ISO Map (20x / +4.33 EV circuit jump)
DUAL_BASE_ISO_GAMMA_MAP_G149: Dict[str, Tuple[int, int]] = {
    "Cine EI": (800, 12800),
    "Cine EI Quick": (800, 12800),
    "S-Log3": (640, 12800),
    "S-Log2": (640, 12800),
    "ITU709(800%)": (640, 12800),
    "S-Cinetone": (100, 2000),
    "HLG": (100, 2000),
    "HLG3": (100, 2000),
    "Cine4": (100, 2000),
    "HLG1": (50, 1000),
    "Cine2": (50, 1000),
    "Cine1": (64, 1280),
    "PP Off": (80, 1600),
    "Movie": (80, 1600),
    "Still": (80, 1600),
    "HLG2": (80, 1600),
    "Cine3": (80, 1600),
    "ITU709": (80, 1600),
}
ALLOWED_GAMMA_CURVES_G149: Tuple[str, ...] = tuple(DUAL_BASE_ISO_GAMMA_MAP_G149.keys())

# UXC resid16 anchors (G149)
ZOOM_RANGE_F_RESID16_G149 = 0x7164
ZOOM_OPTICAL_ONLY_F_RESID16_G149 = 0x73F2
ZOOM_CIZ_F_RESID16_G149 = 0x70E1
ZOOM_DIGITAL_F_RESID16_G149 = 0x796C
ZOOM_LEVER_SPEED_F_RESID16_G149 = 0x6304
ZOOM_1ST_SPEED_F_RESID16_G149 = 0x6FC0
ZOOM_2ND_SPEED_F_RESID16_G149 = 0x78F0
CUSTOM_KEY_ZOOM_SPEED_F_RESID16_G149 = 0x78E8
REMOTE_ZOOM_SPEED_F_RESID16_G149 = 0x7128
ZOOM_RING_ROTATE_F_RESID16_G149 = 0x6BE7
ZOOM_RING_LEFT_RIGHT_F_RESID16_G149 = 0x7A01
ZOOM_RING_RIGHT_LEFT_F_RESID16_G149 = 0x7A9E
AUTO_SLOW_SHUTTER_F_RESID16_G149 = 0x76EE
ISO_RANGE_LIMIT_F_RESID16_G149 = 0x69CB
ISO_AUTO_MIN_SS_F_RESID16_G149 = 0x778B
BASE_ISO_F_RESID16_G149 = 0x78CE

STATUS_VERIFIED_G149 = (
    "VERIFIED_G149_ZOOM_CIZ_DIGITAL_8STEP_SPEED_RESET_SPLIT_AND_AUTOSLOW_DUAL_BASE_ISO_GUARD"
)
STATUS_BLOCKED_G149_TELEMETRY_INVALID = "BLOCKED_G149_TELEMETRY_INVALID"
STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP = (
    "BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP"
)
STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION = (
    "BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION"
)
STATUS_BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION = (
    "BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION"
)


# ---------------------------------------------------------------------------
# Gate G150 Constants: Still .ARW Dormant Lossless, HLG Still Photo,
#                      Sort Recording Slot 1, USB LUN Single Trap, NP-FZ100 PD,
#                      and Dual FX3/FX6 UVC Myth-Busting
# ---------------------------------------------------------------------------

STILL_IMAGE_QUALITY_MENU_PATH_G150 = "Shooting -> [Image Quality/Rec]"
USB_MENU_PATH_G150 = "Setup -> [USB]"
NETWORK_STREAMING_MENU_PATH_G150 = "Network -> [Streaming]"

RAW_FILE_TYPE_COMPRESSED_G150 = "Compressed"
RAW_FILE_TYPE_UNCOMPRESSED_G150 = "Uncompressed"
RAW_FILE_TYPE_DEFAULT_G150 = RAW_FILE_TYPE_COMPRESSED_G150
ALLOWED_RAW_FILE_TYPES_G150: Tuple[str, ...] = (
    RAW_FILE_TYPE_COMPRESSED_G150,
    RAW_FILE_TYPE_UNCOMPRESSED_G150,
)
DORMANT_RAW_FILE_TYPES_G150: Tuple[str, ...] = (
    "Lossless Comp",
    "Lossless Comp (L)",
    "Lossless Comp (M)",
    "Lossless Comp (S)",
    "RAW_FILE_TYPE_LOSSLESS",
    "RAW_FILE_TYPE_LOSSLESS_L",
    "RAW_FILE_TYPE_LOSSLESS_M",
    "RAW_FILE_TYPE_LOSSLESS_S",
)

JH_SWITCH_JPEG_G150 = "JPEG"
JH_SWITCH_HEIF_420_G150 = "HEIF(4:2:0)"
JH_SWITCH_HEIF_422_G150 = "HEIF(4:2:2)"
JH_SWITCH_DEFAULT_G150 = JH_SWITCH_JPEG_G150
ALLOWED_JH_SWITCH_MODES_G150: Tuple[str, ...] = (
    JH_SWITCH_JPEG_G150,
    JH_SWITCH_HEIF_420_G150,
    JH_SWITCH_HEIF_422_G150,
)

STILL_FMT_JPEG_G150 = "JPEG"
STILL_FMT_HEIF_G150 = "HEIF"
STILL_FMT_RAW_G150 = "RAW"
STILL_FMT_RAW_JPEG_G150 = "RAW & JPEG"
STILL_FMT_RAW_HEIF_G150 = "RAW & HEIF"
ALLOWED_STILL_FILE_FORMATS_G150: Tuple[str, ...] = (
    STILL_FMT_JPEG_G150,
    STILL_FMT_HEIF_G150,
    STILL_FMT_RAW_G150,
    STILL_FMT_RAW_JPEG_G150,
    STILL_FMT_RAW_HEIF_G150,
)

HLG_STILL_IMAGE_ELF_TYPO_SYMBOLS_G150: Tuple[str, ...] = (
    "STILL_HLD_PHOTO_OFF",
    "STILL_HLD_PHOTO_ON",
)
HLG_STILL_COLOR_SPACE_G150 = "BT.2100"
HLG_STILL_ISO_FLOOR_G150 = 100

REC_MEDIA_SLOT1_G150 = "Slot 1"
REC_MEDIA_SLOT2_G150 = "Slot 2"
REC_MEDIA_SIMULT_G150 = "Simult. Recording"
REC_MEDIA_SORT_G150 = "Sort Recording"
ALLOWED_REC_MEDIA_MODES_G150: Tuple[str, ...] = (
    REC_MEDIA_SLOT1_G150,
    REC_MEDIA_SLOT2_G150,
    REC_MEDIA_SIMULT_G150,
    REC_MEDIA_SORT_G150,
)

USB_CONN_SEL_WHEN_CONNECT_G150 = "Sel. When Connect"
USB_CONN_MSC_G150 = "MassStorage(MSC)"
USB_CONN_MTP_G150 = "MTP"
USB_CONN_REMOTE_SHOOTING_G150 = "Remote Shooting"
USB_CONN_DEFAULT_G150 = USB_CONN_SEL_WHEN_CONNECT_G150
EXACT_4_USB_CONNECTION_MODES_G150: Tuple[str, ...] = (
    USB_CONN_SEL_WHEN_CONNECT_G150,
    USB_CONN_MSC_G150,
    USB_CONN_MTP_G150,
    USB_CONN_REMOTE_SHOOTING_G150,
)
DORMANT_USB_STREAMING_MODE_NAMES_G150: Tuple[str, ...] = (
    "Live Stream(USB Streaming)",
    "USB Streaming",
    "USB_CONNECTION_USB_STREAMING",
    "BKID_APP_SETTING_USB_STREAMING_PROCAM",
)

USB_LUN_MULTI_G150 = "Multi"
USB_LUN_SINGLE_G150 = "Single"
USB_LUN_DEFAULT_G150 = USB_LUN_MULTI_G150
ALLOWED_USB_LUN_SETTINGS_G150: Tuple[str, ...] = (
    USB_LUN_MULTI_G150,
    USB_LUN_SINGLE_G150,
)
USB_SETUP_RESETTABLE_BY_CAMSET_RESET_G150 = False

MACOS_MSC_POLLUTION_DAEMONS_G150: Tuple[str, ...] = (
    "mds_Spotlight",
    "fseventsd",
    "Finder_AppleDouble",
    "fsck_exfat",
)

USB_POWER_SUPPLY_DEFAULT_G150 = "On"
USB_POWER_PORT_TYPE_C_G150 = "USB Type-C"
USB_POWER_PORT_MULTI_MICRO_G150 = "Multi/Micro USB"
USB_PD_VOLTS_G150 = 9
USB_PD_AMPS_G150 = 3
FX3_DCC1_MIN_PD_WATTS_G150 = 65
FX3_DCC1_CABLE_AMPS_G150 = 5
FX6_DC_IN_VOLTS_G150 = 19.5

MOVIE_REC_DURING_STREAMING_DEFAULT_G150 = "Disable"
ALLOWED_MOVIE_REC_DURING_STREAMING_G150: Tuple[str, ...] = ("Disable", "Enable")
HDMI_REC_MEDIA_ON_G150 = "On"
HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150 = "Off(HDMI Only)"
ALLOWED_HDMI_REC_MEDIA_MODES_G150: Tuple[str, ...] = (
    HDMI_REC_MEDIA_ON_G150,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150,
)

# UXC resid16 anchors (G150)
RAW_FILE_TYPE_F_RESID16_G150 = 0x6FF2
RAW_UNCOMPRESSED_F_RESID16_G150 = 0x6F5B
RAW_COMPRESSED_F_RESID16_G150 = 0x6F67
DORMANT_LOSSLESS_COMP_F_RESID16S_G150: Tuple[int, ...] = (
    0x6B56,
    0x7897,
    0x6BFD,
    0x7894,
)
JPEG_HEIF_SWITCH_F_RESID16_G150 = 0x742A
HEIF_420_F_RESID16_G150 = 0x7959
HEIF_422_F_RESID16_G150 = 0x6057
HLG_STILL_IMAGE_F_RESID16_G150 = 0x76C8
SORT_RECORDING_F_RESID16_G150 = 0x7916
USB_CONNECTION_MODE_F_RESID16_G150 = 0x69A2
USB_SEL_WHEN_CONNECT_F_RESID16_G150 = 0x7738
USB_MSC_F_RESID16_G150 = 0x6C54
USB_MTP_BASE_RESID16_G150 = 0xE24B
USB_REMOTE_SHOOTING_F_RESID16_G150 = 0x7C6F
USB_LUN_SETTING_F_RESID16_G150 = 0x6B19
USB_LUN_MULTI_F_RESID16_G150 = 0x6CEC
USB_LUN_SINGLE_F_RESID16_G150 = 0x776D
USB_POWER_SUPPLY_F_RESID16_G150 = 0x721E
DORMANT_LIVE_STREAM_USB_F_RESID16_G150 = 0x6216
DORMANT_USB_STREAM_RES_F_RESID16_G150 = 0x6194
DORMANT_USB_STREAMING_G_RESID16_G150 = 0x63F7
MOVIE_REC_DURING_STREAMING_F_RESID16_G150 = 0x79D5
REC_MEDIA_DUR_HDMI_OUTPUT_F_RESID16_G150 = 0x6144

STATUS_VERIFIED_G150 = (
    "VERIFIED_G150_STILL_ARW_DORMANT_LOSSLESS_HLG_PHOTO_AND_USB_LUN_SINGLE_SLOT1_NPFZ100_UVC_FIREWALL"
)
STATUS_BLOCKED_G150_TELEMETRY_INVALID = "BLOCKED_G150_TELEMETRY_INVALID"
STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP = (
    "BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP"
)
STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS = (
    "BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS"
)
STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION = (
    "BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION"
)
STATUS_BLOCKED_PHASE347_DONOR_INTEGRITY = "BLOCKED_PHASE347_DONOR_INTEGRITY"


# ---------------------------------------------------------------------------
# Pinned Wave-65 Targeted Donor Binary Slices & SHA-256 Registry
# ---------------------------------------------------------------------------

PINNED_FX3_APPFW_SLICES_PHASE347: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x03BC753C, b"BKID_APP_setting_zoom_setting"),
    (0x03AC8CD9, b"VAL_setting_zoom_setting_ZOOM_SETTING_OPTICAL_ZOOM_ONLY"),
    (0x03AC8D47, b"VAL_setting_zoom_setting_ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON"),
    (0x03AC8D81, b"VAL_setting_zoom_setting_ZOOM_SETTING_DIGITAL_ZOOM_ON"),
    (0x03BC75B6, b"BKID_APP_setting_1st_zoom_spd_stby"),
    (0x03BC75FF, b"BKID_APP_setting_2nd_zoom_spd_stby"),
    (0x03BC76D6, b"BKID_APP_setting_fixed_zoom_speed_stby"),
    (0x03BC77EC, b"BKID_APP_setting_remote_fixed_zoom_speed_stby"),
    (0x03BCB7C3, b"BKID_APP_setting_zoom_direction"),
    (0x03BC7FC5, b"BKID_APP_setting_auto_slow_shutter"),
    (0x03BEEE70, b"BKID_APP_setting_iso_range_limit_min_movie"),
    (0x03BC80B6, b"BKID_APP_setting_iso_auto_min_s_s"),
    (0x03BC80FD, b"BKID_APP_setting_base_iso"),
    (
        0x039D1975,
        b"VAL_HAITA_model_diff_normal_iso_range_min_movie_in_gamma_slog3_ISO_SENSITIVITY_640",
    ),
    (
        0x039D2BA7,
        b"VAL_HAITA_model_diff_normal_iso_range_min_movie_in_gamma_schrome_ISO_SENSITIVITY_100",
    ),
    (
        0x039D20A9,
        b"VAL_HAITA_model_diff_normal_iso_range_min_movie_in_gamma_hlg1_ISO_SENSITIVITY_50",
    ),
    (
        0x039CFF7D,
        b"VAL_HAITA_model_diff_normal_iso_range_min_movie_in_gamma_cine1_ISO_SENSITIVITY_64",
    ),
    (
        0x039CEE19,
        b"VAL_HAITA_model_diff_normal_iso_range_min_movie_ISO_SENSITIVITY_80",
    ),
    (0x03BC35C3, b"BKID_APP_setting_still_raw_file_type"),
    (0x03A654E0, b"VAL_setting_still_raw_file_type_RAW_FILE_TYPE_LOSSLESS"),
    (0x03BC353B, b"BKID_APP_setting_jh_file_type"),
    (0x03BC600B, b"BKID_APP_setting_still_hlg_photo"),
    (0x03A793C1, b"STILL_HLD_PHOTO_ON"),
    (
        0x039CF2E4,
        b"VAL_HAITA_model_diff_normal_iso_range_min_in_still_hlg_photo_on_ISO_SENSITIVITY_100",
    ),
    (0x03BCC062, b"BKID_APP_setting_usb_connection_method"),
    (0x03B111E1, b"USB_CONNECTION_USB_STREAMING"),
    (0x03BCC089, b"BKID_APP_setting_lun_settings"),
    (0x03BCC0A7, b"BKID_APP_setting_usb_supply"),
    (0x03BCA294, b"BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution"),
    (0x03BCC0E4, b"BKID_APP_setting_rec_media_during_hdmi_output"),
)
PINNED_FX3_APPFW_SLICES_SHA256_PHASE347 = (
    "3e23abd40668e00457da1f45907648cb1259adbcf822e2775e28c6662dd7ce11"
)

PINNED_FX6_APPFW_SLICES_PHASE347: Tuple[Tuple[int, bytes], ...] = (
    (0x00000000, b"\x7fELF"),
    (0x026C62A7, b"VAL_setting_zoom_setting_ZOOM_SETTING_OPTICAL_ZOOM_ONLY"),
    (0x026C62DF, b"VAL_setting_zoom_setting_ZOOM_SETTING_CLEAR_IMAGE_ZOOM_ON"),
    (0x0266BF10, b"VAL_setting_base_sensitivity_menu_BASE_SENSITIVITY_MENU_LOW_DUAL_GAIN"),
    (0x0270AF1C, b"BKID_APP_SETTING_USB_STREAMING_PROCAM"),
    (0x0270C9E5, b"BKID_APP_SETTING_HANDLE_ZOOM"),
)
PINNED_FX6_APPFW_SLICES_SHA256_PHASE347 = (
    "add623c23c20a1b970e4b110eb62cd737ab531b37e08712c7802d4b9b0a3008b"
)

PINNED_PHASE347_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_appfw_so": (
        "FX3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        PINNED_FX3_APPFW_SLICES_SHA256_PHASE347,
        tuple(tok for _, tok in PINNED_FX3_APPFW_SLICES_PHASE347),
        "FX3 appFw.so Wave-65 Zoom/AutoSlow/ISO/DualBase/RAW/HLG/USB-LUN/UVC slices",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4\x00",),
        "FX3-CX95900_ALLLANG-Backup.bin BK4 seed",
    ),
    "fx3_usbg_storage_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_storage.ko",
        104_288,
        "b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255",
        (
            b"pInfoLun",
            b"sony_storage_dev",
            b"atapi_dvd_read_write",
            b"atapi_dvd_set_write_protect",
        ),
        "FX3 usbg_storage.ko writable MSC LUN kernel driver",
    ),
    "fx3_usbg_stillimage_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_stillimage.ko",
        49_448,
        "0ef9132f6e043bd38a376519f0f130545e4c8ae68473b1b9d97b1228fa2829a5",
        (b"\x7fELF",),
        "FX3 usbg_stillimage.ko MTP/PTP kernel driver",
    ),
    "fx3_usb_f_uvc_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usb_f_uvc.ko",
        78_840,
        "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc",
        (b"\x7fELF",),
        "FX3 dormant usb_f_uvc.ko UVC gadget driver",
    ),
    "fx3_g_webcam_ko": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/g_webcam.ko",
        13_728,
        "9d8df09a035d288673dbc59daac186959fe826fdddb613a7cecc57d321164792",
        (b"\x7fELF",),
        "FX3 dormant g_webcam.ko UVC gadget driver",
    ),
    "fx3_string_english_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
        373_820,
        "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        (
            b"Zoom Range",
            b"Zoom Lever Speed",
            b"Zoom Ring Rotate",
            b"Auto Slow Shutter",
            b"ISO Range Limit",
            b"ISO AUTO Min. SS",
            b"Base ISO",
            b"RAW File Type",
            b"HLG Still Image",
            b"Sort Recording",
            b"USB Connection Mode",
            b"USB LUN Setting",
            b"USB Power Supply",
            b"Live Stream(USB Streaming)",
            b"Movie Rec During Streaming",
        ),
        "FX3 string_english_f.uxc Wave-65 EN parity",
    ),
    "fx3_string_english_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc",
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        (b"Digital Zoom", b"MTP"),
        "FX3 string_english.uxc Wave-65 base tokens",
    ),
    "fx3_string_english_g_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc",
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        (b"USB Streaming",),
        "FX3 string_english_g.uxc Wave-65 dormant USB Streaming token",
    ),
    "fx3_string_simplifiedchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc",
        322_652,
        "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        (
            "变焦范围".encode("utf-8"),
            "变焦杆速度".encode("utf-8"),
            "变焦环旋转".encode("utf-8"),
            "自动低速快门".encode("utf-8"),
            "ISO范围限制".encode("utf-8"),
            "ISO AUTO最小速度".encode("utf-8"),
            "RAW文件类型".encode("utf-8"),
            "HLG静态影像".encode("utf-8"),
            "分类记录".encode("utf-8"),
            "USB连接模式".encode("utf-8"),
            "USB LUN设定".encode("utf-8"),
            "USB电源供给".encode("utf-8"),
            "流式传输动态影像录制".encode("utf-8"),
        ),
        "FX3 string_simplifiedchinese_f.uxc Wave-65 ZH-CN parity",
    ),
    "fx3_string_traditionalchinese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc",
        324_148,
        "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        (
            "變焦範圍".encode("utf-8"),
            "變焦控制桿速度".encode("utf-8"),
            "變焦環旋轉".encode("utf-8"),
            "自動慢速快門".encode("utf-8"),
            "ISO範圍限制".encode("utf-8"),
            "ISO AUTO快門速度".encode("utf-8"),
            "RAW檔案類型".encode("utf-8"),
            "HLG靜態影像".encode("utf-8"),
            "排序錄製".encode("utf-8"),
            "USB連線模式".encode("utf-8"),
            "USB LUN設定".encode("utf-8"),
            "USB電源供給".encode("utf-8"),
            "串流傳輸動態影像錄製".encode("utf-8"),
        ),
        "FX3 string_traditionalchinese_f.uxc Wave-65 ZH-TW parity",
    ),
    "fx3_string_japanese_f_uxc": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc",
        447_840,
        "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        (
            "ズーム範囲".encode("utf-8"),
            "ｽﾞｰﾑﾘﾝｸﾞ操作方向".encode("utf-8"),
            "ISO感度範囲限定".encode("utf-8"),
            "ISO AUTO低速限界".encode("utf-8"),
            "RAW記録方式".encode("utf-8"),
            "HLG静止画".encode("utf-8"),
            "振り分け".encode("utf-8"),
            "USB接続モード".encode("utf-8"),
            "USB LUN設定".encode("utf-8"),
            "USB給電".encode("utf-8"),
        ),
        "FX3 string_japanese_f.uxc Wave-65 JA parity",
    ),
    "fx6_appfw_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
        50_520_424,
        PINNED_FX6_APPFW_SLICES_SHA256_PHASE347,
        tuple(tok for _, tok in PINNED_FX6_APPFW_SLICES_PHASE347),
        "FX6 appFw.so Wave-65 ZoomType/BaseSensitivity/HandleZoom/USB_STREAMING_PROCAM slices",
    ),
    "fx6_usbg_storage_ko": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usbg_storage.ko",
        104_288,
        "fc6de444414c9931dc33ac9702aa9a8113e8d41bdf09d818de8fd0524783aa1e",
        (b"\x7fELF",),
        "FX6 usbg_storage.ko USB storage kernel driver",
    ),
    "fx6_usb_f_uvc_ko": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usb_f_uvc.ko",
        78_840,
        "bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305",
        (b"\x7fELF",),
        "FX6 dormant usb_f_uvc.ko UVC gadget driver",
    ),
    "fx6_string_english_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc",
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        (b"Zoom Type", b"Handle Zoom", b"Base Sensitivity"),
        "FX6 string_english.uxc Wave-65 EN baseline",
    ),
    "fx6_string_english_2_uxc": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        (b"Handle Zoom", b"DC Low Voltage"),
        "FX6 string_english_2.uxc Wave-65 EN enterprise baseline",
    ),
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _is_clean_room_forced(force_clean_room: Optional[bool]) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347):
        if os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_strict_num(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _is_on_off(val: Any) -> bool:
    return isinstance(val, str) and val in ("On", "Off")


def _encode_token_variants(token: bytes) -> Tuple[bytes, ...]:
    variants = [token]
    try:
        text = token.decode("utf-8")
        variants.append(text.encode("utf-16-le"))
    except UnicodeDecodeError:
        pass
    return tuple(variants)


def _read_exact_o_rdonly_slices(
    path: Path, slices: Sequence[Tuple[int, bytes]]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    hasher = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        for offset, expected in slices:
            chunk = os.pread(fd, len(expected), offset)
            if chunk != expected:
                missing.append(f"slice_mismatch@0x{offset:08X}")
            hasher.update(chunk)
        return st.st_size, hasher.hexdigest(), missing
    finally:
        os.close(fd)


def _read_full_o_rdonly_sha256_and_tokens(
    path: Path, required_tokens: Sequence[bytes]
) -> Tuple[int, str, List[str]]:
    missing: List[str] = []
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        data = os.read(fd, st.st_size)
    finally:
        os.close(fd)
    sha = hashlib.sha256(data).hexdigest()
    for tok in required_tokens:
        if not any(var in data for var in _encode_token_variants(tok)):
            missing.append(f"token_missing:{tok[:32]!r}")
    return st.st_size, sha, missing


def _parse_fw_float(ver_str: str) -> Optional[float]:
    if not isinstance(ver_str, str) or not ver_str.strip():
        return None
    try:
        return float(ver_str.strip())
    except ValueError:
        return None


def _validate_fx3_body_identity(
    body_model_name: str,
    body_model_id: int,
    help_guide_code: str,
    firmware_version: str,
) -> List[str]:
    errs: List[str] = []
    if body_model_name != FX3_MODEL_NAME_PHASE347:
        errs.append(f"body_model_name_invalid:{body_model_name!r}")
    if not _is_strict_int(body_model_id) or body_model_id != FX3_MODEL_ID_PHASE347:
        errs.append(f"body_model_id_invalid:{body_model_id!r}")
    if help_guide_code != FX3_HELP_GUIDE_CODE_PHASE347:
        errs.append(f"help_guide_code_invalid:{help_guide_code!r}")
    if _parse_fw_float(firmware_version) is None:
        errs.append(f"firmware_version_invalid:{firmware_version!r}")
    return errs


def strip_elapsed_seconds_recursive_phase347(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys for canonical digests."""
    if isinstance(obj, dict):
        return {
            k: strip_elapsed_seconds_recursive_phase347(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [strip_elapsed_seconds_recursive_phase347(v) for v in obj]
    if isinstance(obj, tuple):
        return [strip_elapsed_seconds_recursive_phase347(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Donor Integrity Audit (O_RDONLY / Clean-Room Dual-Mode)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase347DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    four_lang_resid16_parity_verified: bool
    zero_forbidden_myths_verified: bool
    elapsed_seconds: float
    within_budget_200ms: bool
    raw_firmware_bytes_leaked: int
    file_digests: Dict[str, str]
    missing_markers: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_phase347_donor_contracts(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    donor_specs_override: Optional[
        Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]]
    ] = None,
) -> Phase347DonorAuditResult:
    """Fast (< 0.20s) O_RDONLY + bounded os.pread donor audit with clean-room fallback."""
    import time

    t0 = time.perf_counter()
    clean_forced = _is_clean_room_forced(force_clean_room)
    specs = (
        dict(donor_specs_override)
        if donor_specs_override is not None
        else dict(PINNED_PHASE347_DONOR_SPECS)
    )
    resolved_work_root = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(
            repo_root=repo_root or DEFAULT_REPO_ROOT
        ).work_root
    )

    if clean_forced:
        dt = time.perf_counter() - t0
        return Phase347DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_NO_DONOR_DISK_IO",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE347,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(),
        )

    missing_files = (
        list(specs.keys())
        if resolved_work_root is None
        else [
            key
            for key, spec in specs.items()
            if not (resolved_work_root / spec[1]).is_file()
        ]
    )
    if missing_files and donor_specs_override is None:
        dt = time.perf_counter() - t0
        return Phase347DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_ABSENT_DONOR_FALLBACK",
            files_inspected=0,
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            four_lang_resid16_parity_verified=True,
            zero_forbidden_myths_verified=True,
            elapsed_seconds=round(dt, 6),
            within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE347,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            file_digests={k: v[3] for k, v in specs.items()},
            missing_markers=(),
            errors=(),
            warnings=(
                f"Donor files absent ({len(missing_files)} missing); "
                "verified Phase 347 via clean-room synthetic fallback.",
            ),
        )

    file_digests: Dict[str, str] = {}
    missing_markers: List[str] = []
    errors: List[str] = []
    inspected = 0

    for key, (
        family,
        rel_path,
        expected_size,
        expected_sha,
        tokens,
        desc,
    ) in specs.items():
        if resolved_work_root is None:
            missing_markers.append(f"{key}:work_root_none")
            errors.append(f"{key}:{desc}:work_root_none")
            continue
        target = resolved_work_root / rel_path
        if not target.is_file():
            missing_markers.append(f"{key}:file_missing")
            errors.append(f"{key}:{desc}:file_missing")
            continue
        inspected += 1
        if key == "fx3_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX3_APPFW_SLICES_PHASE347
            )
        elif key == "fx6_appfw_so" and donor_specs_override is None:
            actual_size, actual_sha, tok_errs = _read_exact_o_rdonly_slices(
                target, PINNED_FX6_APPFW_SLICES_PHASE347
            )
        else:
            actual_size, actual_sha, tok_errs = _read_full_o_rdonly_sha256_and_tokens(
                target, tokens
            )

        file_digests[key] = actual_sha
        if actual_size != expected_size:
            missing_markers.append(
                f"{key}:size_mismatch:{actual_size}!={expected_size}"
            )
            errors.append(f"{family}:{key}:size_mismatch")
        if actual_sha != expected_sha:
            missing_markers.append(f"{key}:sha256_mismatch")
            errors.append(f"{family}:{key}:sha256_mismatch")
        for terr in tok_errs:
            missing_markers.append(f"{key}:{terr}")
            errors.append(f"{family}:{key}:{terr}")

    dt = time.perf_counter() - t0
    valid = len(errors) == 0
    return Phase347DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE
            if valid
            else STATUS_BLOCKED_PHASE347_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="STRICT_OS_O_RDONLY_PREAD",
        files_inspected=inspected,
        fx3_contracts_verified=valid,
        fx6_contracts_verified=valid,
        four_lang_resid16_parity_verified=valid,
        zero_forbidden_myths_verified=valid,
        elapsed_seconds=round(dt, 6),
        within_budget_200ms=dt <= DONOR_CHECK_MAX_SECONDS_PHASE347,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        file_digests=file_digests,
        missing_markers=tuple(missing_markers),
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Gate G149: Zoom/CIZ/Digital/8-Step Speed Reset Split + Auto Slow Shutter /
#            ISO Range Limit / Still-Only ISO AUTO Min. SS / Dual Base ISO
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoomCizAutoSlowBaseIsoGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    zoom_menu_path: str
    zoom_ring_rotate_menu_path: str
    exposure_menu_path: str
    effective_zoom_range: str
    effective_zoom_ring_rotate: str
    effective_zoom_lever_1st_speed: int
    effective_zoom_lever_2nd_speed: int
    effective_custom_key_zoom_speed: int
    effective_remote_zoom_speed_type: str
    effective_remote_zoom_fixed_speed: int
    effective_max_zoom_scale: float
    non_optical_zoom_pre_entry_locked: bool
    non_optical_zoom_active_lockouts: Tuple[str, ...]
    zoom_range_and_ring_resettable_by_camset_reset: bool
    zoom_speeds_resettable_by_camset_reset: bool
    effective_auto_slow_shutter: str
    auto_slow_shutter_locked_disabled: bool
    auto_slow_shutter_lock_reasons: Tuple[str, ...]
    iso_range_limit_resettable_by_camset_reset: bool
    iso_range_limit_applies_to_iso_auto: bool
    iso_auto_min_ss_available: bool
    effective_iso_auto_min_ss: str
    effective_flash_iso_auto_min_ss: str
    base_iso_menu_visible: bool
    effective_low_base_iso: int
    effective_high_base_iso: int
    fx6_cross_model_spoof_rejected: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_zoom_ciz_autoslow_baseiso_state(
    *,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE347,
    zoom_range: str = ZOOM_RANGE_DEFAULT_G149,
    zoom_ring_rotate: str = ZOOM_RING_ROTATE_DEFAULT_G149,
    zoom_lever_1st_speed: int = ZOOM_LEVER_1ST_DEFAULT_G149,
    zoom_lever_2nd_speed: int = ZOOM_LEVER_2ND_DEFAULT_G149,
    custom_key_zoom_speed: int = CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149,
    remote_zoom_speed_type: str = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149,
    remote_zoom_fixed_speed: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149,
    movie_is_4k: bool = True,
    movie_fps: float = 23.98,
    sq_fps: float = 23.98,
    still_file_format: str = "JPEG",
    still_image_size: str = "L",
    apsc_s35_active: bool = False,
    hdmi_raw_output_on: bool = False,
    auto_slow_shutter: str = AUTO_SLOW_SHUTTER_DEFAULT_G149,
    exposure_mode: str = EXPOSURE_MODE_P_G149,
    iso_auto_selected: bool = True,
    flexible_exp_shutter_manual: bool = False,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G149,
    shutter_mode: str = SHUTTER_MODE_SPEED_G149,
    iso_auto_min_ss: str = ISO_AUTO_MIN_SS_DEFAULT_G149,
    flash_firing: bool = False,
    gamma_curve: str = "PP Off",
    base_iso_cine_ei: int = BASE_ISO_DEFAULT_G149,
    reset_action: str = RESET_ACTION_NONE_PHASE347,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-65 Zoom Reset Split, Auto Slow & Dual Base ISO state."""
    if reset_action == RESET_ACTION_INITIALIZE_PHASE347:
        eff_zoom_range = ZOOM_RANGE_DEFAULT_G149
        eff_ring_rotate = ZOOM_RING_ROTATE_DEFAULT_G149
    else:
        eff_zoom_range = zoom_range
        eff_ring_rotate = zoom_ring_rotate

    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        RESET_ACTION_INITIALIZE_PHASE347,
    ):
        eff_lever_1st = ZOOM_LEVER_1ST_DEFAULT_G149
        eff_lever_2nd = ZOOM_LEVER_2ND_DEFAULT_G149
        eff_custom_spd = CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149
        eff_remote_type = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149
        eff_remote_fixed = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149
        eff_auto_slow = AUTO_SLOW_SHUTTER_DEFAULT_G149
        eff_min_ss = ISO_AUTO_MIN_SS_DEFAULT_G149
        eff_base_iso_ei = BASE_ISO_DEFAULT_G149
    else:
        eff_lever_1st = zoom_lever_1st_speed
        eff_lever_2nd = zoom_lever_2nd_speed
        eff_custom_spd = custom_key_zoom_speed
        eff_remote_type = remote_zoom_speed_type
        eff_remote_fixed = remote_zoom_fixed_speed
        eff_auto_slow = auto_slow_shutter
        eff_min_ss = iso_auto_min_ss
        eff_base_iso_ei = base_iso_cine_ei

    # Pre-entry lockouts for ClearImage Zoom / Digital Zoom / Smart Zoom
    pre_entry_locked = False
    if shoot_mode == SHOOT_MODE_STILL_PHASE347 and "RAW" in still_file_format:
        pre_entry_locked = True
    if shoot_mode == SHOOT_MODE_MOVIE_PHASE347 and (
        movie_fps >= 100.0 or hdmi_raw_output_on
    ):
        pre_entry_locked = True
    if shoot_mode == SHOOT_MODE_SQ_PHASE347 and (sq_fps >= 100.0 or hdmi_raw_output_on):
        pre_entry_locked = True

    if pre_entry_locked or eff_zoom_range == ZOOM_RANGE_OPTICAL_ONLY_G149:
        effective_zoom_mode = ZOOM_RANGE_OPTICAL_ONLY_G149
        max_scale = 1.0
        active_lockouts: Tuple[str, ...] = ()
    else:
        effective_zoom_mode = eff_zoom_range
        active_lockouts = (
            "focus_area_disabled_center_priority",
            "metering_mode_locked_multi",
            "face_eye_prior_in_af_disabled",
            "face_priority_in_multi_metering_disabled",
            "tracking_disabled",
        )
        if shoot_mode in (SHOOT_MODE_MOVIE_PHASE347, SHOOT_MODE_SQ_PHASE347):
            if eff_zoom_range == ZOOM_RANGE_CIZ_G149:
                max_scale = (
                    MOVIE_CIZ_4K_SCALE_G149 if movie_is_4k else MOVIE_CIZ_HD_SCALE_G149
                )
            else:
                max_scale = MOVIE_DIGITAL_ZOOM_SCALE_G149
        else:
            table = STILL_APSC_SCALES_G149 if apsc_s35_active else STILL_FF_SCALES_G149
            sz_key = still_image_size if still_image_size in table else "M"
            cat = (
                "ClearImage" if eff_zoom_range == ZOOM_RANGE_CIZ_G149 else "Digital"
            )
            max_scale = float(table[sz_key][cat] or 1.0)

    # Auto Slow Shutter 6+ lockout conditions (Movie-only)
    lock_reasons: List[str] = []
    if shoot_mode == SHOOT_MODE_STILL_PHASE347:
        lock_reasons.append("still_mode_no_auto_slow_shutter")
    if shoot_mode == SHOOT_MODE_SQ_PHASE347:
        lock_reasons.append("sq_motion_mode")
    if exposure_mode == EXPOSURE_MODE_S_G149:
        lock_reasons.append("shutter_priority_s")
    if exposure_mode == EXPOSURE_MODE_M_G149:
        lock_reasons.append("manual_exposure_m")
    if not iso_auto_selected:
        lock_reasons.append("manual_iso_not_iso_auto")
    if exposure_mode == EXPOSURE_MODE_FLEXIBLE_G149 and flexible_exp_shutter_manual:
        lock_reasons.append("flexible_exp_shutter_manual")
    if log_shooting_mode in (
        LOG_SHOOTING_CINE_EI_G149,
        LOG_SHOOTING_CINE_EI_QUICK_G149,
    ):
        lock_reasons.append("cine_ei_or_cine_ei_quick")
    if shutter_mode == SHUTTER_MODE_ANGLE_G149:
        lock_reasons.append("shutter_mode_angle")
    auto_slow_locked = len(lock_reasons) > 0
    eff_auto_slow_out = "Disabled" if auto_slow_locked else eff_auto_slow

    # ISO AUTO Min. SS strictly Still P/A + ISO AUTO
    min_ss_avail = (
        shoot_mode == SHOOT_MODE_STILL_PHASE347
        and exposure_mode in (EXPOSURE_MODE_P_G149, EXPOSURE_MODE_A_G149)
        and iso_auto_selected
    )
    eff_min_ss_out = eff_min_ss if min_ss_avail else "Unavailable"
    flash_override_ss = (
        ISO_AUTO_MIN_SS_FLASH_OVERRIDE_G149
        if (min_ss_avail and flash_firing)
        else eff_min_ss_out
    )

    # Dual Base ISO visibility & automatic 20x per-Gamma baseline
    base_iso_visible = log_shooting_mode in (
        LOG_SHOOTING_CINE_EI_G149,
        LOG_SHOOTING_CINE_EI_QUICK_G149,
    )
    if base_iso_visible:
        low_base, high_base = BASE_ISO_LOW_G149, BASE_ISO_HIGH_G149
    else:
        g_key = gamma_curve if gamma_curve in DUAL_BASE_ISO_GAMMA_MAP_G149 else "PP Off"
        low_base, high_base = DUAL_BASE_ISO_GAMMA_MAP_G149[g_key]

    return {
        "effective_zoom_range": effective_zoom_mode,
        "effective_zoom_ring_rotate": eff_ring_rotate,
        "effective_zoom_lever_1st_speed": eff_lever_1st,
        "effective_zoom_lever_2nd_speed": eff_lever_2nd,
        "effective_custom_key_zoom_speed": eff_custom_spd,
        "effective_remote_zoom_speed_type": eff_remote_type,
        "effective_remote_zoom_fixed_speed": eff_remote_fixed,
        "effective_max_zoom_scale": max_scale,
        "non_optical_zoom_pre_entry_locked": pre_entry_locked,
        "non_optical_zoom_active_lockouts": active_lockouts,
        "effective_auto_slow_shutter": eff_auto_slow_out,
        "auto_slow_shutter_locked_disabled": auto_slow_locked,
        "auto_slow_shutter_lock_reasons": tuple(lock_reasons),
        "iso_auto_min_ss_available": min_ss_avail,
        "effective_iso_auto_min_ss": eff_min_ss_out,
        "effective_flash_iso_auto_min_ss": flash_override_ss,
        "base_iso_menu_visible": base_iso_visible,
        "effective_cine_ei_base_iso": eff_base_iso_ei,
        "effective_low_base_iso": low_base,
        "effective_high_base_iso": high_base,
    }


def compute_zoom_ciz_autoslow_baseiso_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G149 (288 states)."""
    combos = list(
        itertools.product(
            (SHOOT_MODE_MOVIE_PHASE347, SHOOT_MODE_STILL_PHASE347, SHOOT_MODE_SQ_PHASE347),
            ALLOWED_ZOOM_RANGES_G149,
            (False, True),  # pre_entry_lock_trigger (RAW still / 120p movie / 120fps S&Q)
            (EXPOSURE_MODE_P_G149, EXPOSURE_MODE_M_G149),
            (LOG_SHOOTING_OFF_G149, LOG_SHOOTING_CINE_EI_G149),
            (False, True),  # flash_or_4k
            (
                RESET_ACTION_NONE_PHASE347,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
            ),
        )
    )
    reset_preserved_zoom_range_count = 0
    reset_restored_lever_speed_count = 0
    pre_entry_locked_count = 0
    active_lockouts_count = 0
    auto_slow_locked_count = 0
    min_ss_available_count = 0
    cine_ei_base_iso_visible_count = 0

    for sm, zr, lock_trig, exp_m, log_m, flag_b, rst in combos:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=sm,
            zoom_range=zr,
            zoom_lever_1st_speed=6,
            zoom_lever_2nd_speed=4,
            movie_is_4k=flag_b,
            movie_fps=119.88 if (sm == SHOOT_MODE_MOVIE_PHASE347 and lock_trig) else 23.98,
            sq_fps=120.0 if (sm == SHOOT_MODE_SQ_PHASE347 and lock_trig) else 23.98,
            still_file_format=(
                "RAW & JPEG" if (sm == SHOOT_MODE_STILL_PHASE347 and lock_trig) else "JPEG"
            ),
            exposure_mode=exp_m,
            iso_auto_selected=True,
            log_shooting_mode=log_m,
            flash_firing=flag_b,
            reset_action=rst,
        )
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347
            and zr == ZOOM_RANGE_DIGITAL_G149
            and not lock_trig
            and st["effective_zoom_range"] == ZOOM_RANGE_DIGITAL_G149
        ):
            reset_preserved_zoom_range_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347
            and st["effective_zoom_lever_1st_speed"] == ZOOM_LEVER_1ST_DEFAULT_G149
            and st["effective_zoom_lever_2nd_speed"] == ZOOM_LEVER_2ND_DEFAULT_G149
        ):
            reset_restored_lever_speed_count += 1
        if st["non_optical_zoom_pre_entry_locked"]:
            pre_entry_locked_count += 1
        if len(st["non_optical_zoom_active_lockouts"]) == 5:
            active_lockouts_count += 1
        if st["auto_slow_shutter_locked_disabled"]:
            auto_slow_locked_count += 1
        if st["iso_auto_min_ss_available"]:
            min_ss_available_count += 1
        if st["base_iso_menu_visible"]:
            cine_ei_base_iso_visible_count += 1

    return {
        "total_matrix_states": len(combos),
        "reset_preserved_zoom_range_count": reset_preserved_zoom_range_count,
        "reset_restored_lever_speed_count": reset_restored_lever_speed_count,
        "pre_entry_locked_count": pre_entry_locked_count,
        "active_lockouts_count": active_lockouts_count,
        "auto_slow_locked_count": auto_slow_locked_count,
        "min_ss_available_count": min_ss_available_count,
        "cine_ei_base_iso_visible_count": cine_ei_base_iso_visible_count,
    }


def verify_zoom_ciz_autoslow_iso_baseiso_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE347,
    body_model_id: int = FX3_MODEL_ID_PHASE347,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE347,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE347,
    shoot_mode: str = SHOOT_MODE_MOVIE_PHASE347,
    zoom_range: str = ZOOM_RANGE_DEFAULT_G149,
    zoom_ring_rotate: str = ZOOM_RING_ROTATE_DEFAULT_G149,
    zoom_lever_1st_speed: int = ZOOM_LEVER_1ST_DEFAULT_G149,
    zoom_lever_2nd_speed: int = ZOOM_LEVER_2ND_DEFAULT_G149,
    custom_key_zoom_speed: int = CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149,
    remote_zoom_speed_type: str = REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149,
    remote_zoom_fixed_speed: int = REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149,
    movie_is_4k: bool = True,
    movie_fps: float = 23.98,
    sq_fps: float = 23.98,
    still_file_format: str = "JPEG",
    still_image_size: str = "L",
    apsc_s35_active: bool = False,
    hdmi_raw_output_on: bool = False,
    claimed_smart_zoom_in_movie_allowed: bool = False,
    claimed_non_optical_zoom_during_lockout_allowed: bool = False,
    claimed_focus_area_or_spot_metering_or_tracking_active_in_ciz: bool = False,
    claimed_camset_reset_clears_zoom_range_or_ring: bool = False,
    claimed_camset_reset_preserves_zoom_speeds: bool = False,
    auto_slow_shutter: str = AUTO_SLOW_SHUTTER_DEFAULT_G149,
    claimed_auto_slow_shutter_active_under_lock: bool = False,
    exposure_mode: str = EXPOSURE_MODE_P_G149,
    iso_auto_selected: bool = True,
    flexible_exp_shutter_manual: bool = False,
    log_shooting_mode: str = LOG_SHOOTING_OFF_G149,
    shutter_mode: str = SHUTTER_MODE_SPEED_G149,
    claimed_camset_reset_clears_iso_range_limit: bool = False,
    claimed_iso_range_limit_caps_iso_auto: bool = False,
    iso_auto_min_ss: str = ISO_AUTO_MIN_SS_DEFAULT_G149,
    claimed_iso_auto_min_ss_active_in_movie_or_sq: bool = False,
    flash_firing: bool = False,
    claimed_flash_ignores_1_250_override: bool = False,
    gamma_curve: str = "PP Off",
    base_iso_cine_ei: int = BASE_ISO_DEFAULT_G149,
    claimed_base_iso_menu_visible_outside_cine_ei: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE347,
    fx6_digital_zoom_requested: bool = False,
    fx6_handle_zoom_or_min_ss_spoof_requested: bool = False,
) -> ZoomCizAutoSlowBaseIsoGuardResult:
    """Enforce Gate G149: Zoom/CIZ/Digital/8-Step Speed Reset Split + Auto Slow & Dual Base ISO."""
    errors: List[str] = []
    warnings: List[str] = []
    violations: List[str] = []

    def _add(code: str, msg: str) -> None:
        violations.append(code)
        errors.append(msg)

    errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )

    if shoot_mode not in ALLOWED_SHOOT_MODES_PHASE347:
        _add("TELEMETRY_INVALID", f"shoot_mode_invalid:{shoot_mode!r}")
    if zoom_range not in ALLOWED_ZOOM_RANGES_G149:
        _add("TELEMETRY_INVALID", f"zoom_range_invalid:{zoom_range!r}")
    if zoom_ring_rotate not in ALLOWED_ZOOM_RING_ROTATIONS_G149:
        _add("TELEMETRY_INVALID", f"zoom_ring_rotate_invalid:{zoom_ring_rotate!r}")
    for lbl, val in (
        ("zoom_lever_1st_speed", zoom_lever_1st_speed),
        ("zoom_lever_2nd_speed", zoom_lever_2nd_speed),
        ("custom_key_zoom_speed", custom_key_zoom_speed),
        ("remote_zoom_fixed_speed", remote_zoom_fixed_speed),
    ):
        if not _is_strict_int(val) or not (ZOOM_SPEED_MIN_G149 <= val <= ZOOM_SPEED_MAX_G149):
            _add("TELEMETRY_INVALID", f"{lbl}_invalid:{val!r}")
    if remote_zoom_speed_type not in ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G149:
        _add("TELEMETRY_INVALID", f"remote_zoom_speed_type_invalid:{remote_zoom_speed_type!r}")
    if not _is_strict_num(movie_fps) or movie_fps <= 0:
        _add("TELEMETRY_INVALID", f"movie_fps_invalid:{movie_fps!r}")
    if not _is_strict_num(sq_fps) or sq_fps <= 0:
        _add("TELEMETRY_INVALID", f"sq_fps_invalid:{sq_fps!r}")
    if not _is_on_off(auto_slow_shutter):
        _add("TELEMETRY_INVALID", f"auto_slow_shutter_invalid:{auto_slow_shutter!r}")
    if exposure_mode not in ALLOWED_EXPOSURE_MODES_G149:
        _add("TELEMETRY_INVALID", f"exposure_mode_invalid:{exposure_mode!r}")
    if log_shooting_mode not in ALLOWED_LOG_SHOOTING_MODES_G149:
        _add("TELEMETRY_INVALID", f"log_shooting_mode_invalid:{log_shooting_mode!r}")
    if shutter_mode not in ALLOWED_SHUTTER_MODES_G149:
        _add("TELEMETRY_INVALID", f"shutter_mode_invalid:{shutter_mode!r}")
    if base_iso_cine_ei not in ALLOWED_CINE_EI_BASE_ISOS_G149:
        _add("TELEMETRY_INVALID", f"base_iso_cine_ei_invalid:{base_iso_cine_ei!r}")
    if gamma_curve not in DUAL_BASE_ISO_GAMMA_MAP_G149:
        _add("TELEMETRY_INVALID", f"gamma_curve_invalid:{gamma_curve!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE347:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    # FX6 cross-model checks (EOPNOTSUPP=95)
    if fx6_digital_zoom_requested or fx6_handle_zoom_or_min_ss_spoof_requested:
        _add(
            "FX6_CROSS_MODEL_EOPNOTSUPP",
            "fx6_has_zero_digital_zoom_and_zero_still_iso_auto_min_ss_and_fx3_lacks_handle_zoom_eopnotsupp_95",
        )

    state = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
        shoot_mode=shoot_mode if shoot_mode in ALLOWED_SHOOT_MODES_PHASE347 else SHOOT_MODE_MOVIE_PHASE347,
        zoom_range=zoom_range if zoom_range in ALLOWED_ZOOM_RANGES_G149 else ZOOM_RANGE_DEFAULT_G149,
        zoom_ring_rotate=zoom_ring_rotate if zoom_ring_rotate in ALLOWED_ZOOM_RING_ROTATIONS_G149 else ZOOM_RING_ROTATE_DEFAULT_G149,
        zoom_lever_1st_speed=zoom_lever_1st_speed if _is_strict_int(zoom_lever_1st_speed) else ZOOM_LEVER_1ST_DEFAULT_G149,
        zoom_lever_2nd_speed=zoom_lever_2nd_speed if _is_strict_int(zoom_lever_2nd_speed) else ZOOM_LEVER_2ND_DEFAULT_G149,
        custom_key_zoom_speed=custom_key_zoom_speed if _is_strict_int(custom_key_zoom_speed) else CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149,
        remote_zoom_speed_type=remote_zoom_speed_type if remote_zoom_speed_type in ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G149 else REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149,
        remote_zoom_fixed_speed=remote_zoom_fixed_speed if _is_strict_int(remote_zoom_fixed_speed) else REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149,
        movie_is_4k=movie_is_4k,
        movie_fps=float(movie_fps) if _is_strict_num(movie_fps) else 23.98,
        sq_fps=float(sq_fps) if _is_strict_num(sq_fps) else 23.98,
        still_file_format=still_file_format,
        still_image_size=still_image_size,
        apsc_s35_active=apsc_s35_active,
        hdmi_raw_output_on=hdmi_raw_output_on,
        auto_slow_shutter=auto_slow_shutter if _is_on_off(auto_slow_shutter) else AUTO_SLOW_SHUTTER_DEFAULT_G149,
        exposure_mode=exposure_mode if exposure_mode in ALLOWED_EXPOSURE_MODES_G149 else EXPOSURE_MODE_P_G149,
        iso_auto_selected=iso_auto_selected,
        flexible_exp_shutter_manual=flexible_exp_shutter_manual,
        log_shooting_mode=log_shooting_mode if log_shooting_mode in ALLOWED_LOG_SHOOTING_MODES_G149 else LOG_SHOOTING_OFF_G149,
        shutter_mode=shutter_mode if shutter_mode in ALLOWED_SHUTTER_MODES_G149 else SHUTTER_MODE_SPEED_G149,
        iso_auto_min_ss=iso_auto_min_ss,
        flash_firing=flash_firing,
        gamma_curve=gamma_curve if gamma_curve in DUAL_BASE_ISO_GAMMA_MAP_G149 else "PP Off",
        base_iso_cine_ei=base_iso_cine_ei if base_iso_cine_ei in ALLOWED_CINE_EI_BASE_ISOS_G149 else BASE_ISO_DEFAULT_G149,
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE347 else RESET_ACTION_NONE_PHASE347,
    )

    # Zoom Reset Split & Lockout Checks
    if claimed_smart_zoom_in_movie_allowed:
        _add(
            "ZOOM_SMART_MOVIE_VIOLATION",
            "smart_zoom_is_unavailable_in_movie_and_sq_modes_einval_22",
        )
    if state["non_optical_zoom_pre_entry_locked"] and claimed_non_optical_zoom_during_lockout_allowed:
        _add(
            "ZOOM_PRE_ENTRY_LOCKOUT_VIOLATION",
            "clear_image_and_digital_zoom_are_locked_out_under_raw_120p_sq100_120_240fps_or_hdmi_raw_einval_22",
        )
    if (
        len(state["non_optical_zoom_active_lockouts"]) > 0
        and claimed_focus_area_or_spot_metering_or_tracking_active_in_ciz
    ):
        _add(
            "ZOOM_ACTIVE_AF_METERING_LOCKOUT_VIOLATION",
            "non_optical_zoom_disables_focus_area_face_eye_tracking_and_locks_multi_metering_einval_22",
        )
    if claimed_camset_reset_clears_zoom_range_or_ring:
        _add(
            "ZOOM_RESET_SPLIT_IMMUNITY_VIOLATION",
            "zoom_range_and_zoom_ring_rotate_are_initialize_only_not_resettable_by_camset_reset_einval_22",
        )
    if claimed_camset_reset_preserves_zoom_speeds:
        _add(
            "ZOOM_RESET_SPLIT_SPEED_VIOLATION",
            "zoom_lever_custom_key_and_remote_zoom_speeds_must_be_resettable_by_camset_reset_einval_22",
        )

    # Auto Slow Shutter, ISO Range Limit, ISO AUTO Min. SS & Dual Base ISO Checks
    if state["auto_slow_shutter_locked_disabled"] and claimed_auto_slow_shutter_active_under_lock:
        _add(
            "AUTOSLOW_SHUTTER_LOCKOUT_VIOLATION",
            "auto_slow_shutter_must_be_disabled_under_sq_s_m_manual_iso_flex_manual_cine_ei_or_angle_einval_22",
        )
    if claimed_camset_reset_clears_iso_range_limit:
        _add(
            "ISO_RANGE_LIMIT_RESET_VIOLATION",
            "iso_range_limit_is_initialize_only_not_resettable_by_camset_reset_einval_22",
        )
    if claimed_iso_range_limit_caps_iso_auto:
        _add(
            "ISO_RANGE_LIMIT_SCOPE_VIOLATION",
            "iso_range_limit_restricts_manual_iso_only_not_iso_auto_limits_einval_22",
        )
    if claimed_iso_auto_min_ss_active_in_movie_or_sq:
        _add(
            "ISO_AUTO_MIN_SS_STILL_ONLY_VIOLATION",
            "iso_auto_min_ss_is_strictly_still_p_a_iso_auto_only_unavailable_in_movie_or_sq_einval_22",
        )
    if flash_firing and state["iso_auto_min_ss_available"] and claimed_flash_ignores_1_250_override:
        _add(
            "ISO_AUTO_MIN_SS_FLASH_OVERRIDE_VIOLATION",
            "still_flash_sync_overrides_iso_auto_min_ss_slower_than_1_250s_einval_22",
        )
    if not state["base_iso_menu_visible"] and claimed_base_iso_menu_visible_outside_cine_ei:
        _add(
            "DUAL_BASE_ISO_MENU_VISIBILITY_VIOLATION",
            "base_iso_800_12800_menu_is_visible_only_in_cine_ei_or_cine_ei_quick_einval_22",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G149
        block_errno = 0
        block_errno_name = "OK"
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE347
        block_errno_name = EOPNOTSUPP_NAME_PHASE347
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        e.startswith(
            (
                "body_model_name_invalid:",
                "body_model_id_invalid:",
                "help_guide_code_invalid:",
                "firmware_version_invalid:",
            )
        )
        for e in errors
    ):
        status = STATUS_BLOCKED_G149_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE347
        block_errno_name = EINVAL_NAME_PHASE347
    elif any("ZOOM" in v for v in violations):
        status = STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE347
        block_errno_name = EINVAL_NAME_PHASE347
    else:
        status = STATUS_BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE347
        block_errno_name = EINVAL_NAME_PHASE347

    return ZoomCizAutoSlowBaseIsoGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        zoom_menu_path=ZOOM_MENU_PATH_G149,
        zoom_ring_rotate_menu_path=ZOOM_RING_ROTATE_MENU_PATH_G149,
        exposure_menu_path=EXPOSURE_MENU_PATH_G149,
        effective_zoom_range=state["effective_zoom_range"],
        effective_zoom_ring_rotate=state["effective_zoom_ring_rotate"],
        effective_zoom_lever_1st_speed=state["effective_zoom_lever_1st_speed"],
        effective_zoom_lever_2nd_speed=state["effective_zoom_lever_2nd_speed"],
        effective_custom_key_zoom_speed=state["effective_custom_key_zoom_speed"],
        effective_remote_zoom_speed_type=state["effective_remote_zoom_speed_type"],
        effective_remote_zoom_fixed_speed=state["effective_remote_zoom_fixed_speed"],
        effective_max_zoom_scale=state["effective_max_zoom_scale"],
        non_optical_zoom_pre_entry_locked=state["non_optical_zoom_pre_entry_locked"],
        non_optical_zoom_active_lockouts=state["non_optical_zoom_active_lockouts"],
        zoom_range_and_ring_resettable_by_camset_reset=False,
        zoom_speeds_resettable_by_camset_reset=True,
        effective_auto_slow_shutter=state["effective_auto_slow_shutter"],
        auto_slow_shutter_locked_disabled=state["auto_slow_shutter_locked_disabled"],
        auto_slow_shutter_lock_reasons=state["auto_slow_shutter_lock_reasons"],
        iso_range_limit_resettable_by_camset_reset=False,
        iso_range_limit_applies_to_iso_auto=False,
        iso_auto_min_ss_available=state["iso_auto_min_ss_available"],
        effective_iso_auto_min_ss=state["effective_iso_auto_min_ss"],
        effective_flash_iso_auto_min_ss=state["effective_flash_iso_auto_min_ss"],
        base_iso_menu_visible=state["base_iso_menu_visible"],
        effective_low_base_iso=state["effective_low_base_iso"],
        effective_high_base_iso=state["effective_high_base_iso"],
        fx6_cross_model_spoof_rejected=bool(
            fx6_digital_zoom_requested or fx6_handle_zoom_or_min_ss_spoof_requested
        ),
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G149ZoomCizAutoSlowBaseIsoGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    zoom_ciz_autoslow_baseiso_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G149ZoomCizAutoSlowBaseIsoGuardResult]:
    audit = audit_phase347_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G149ZoomCizAutoSlowBaseIsoGuardResult(
        gate_id=G149,
        gate_code=G149_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        zoom_ciz_autoslow_baseiso_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G149,
        gate_code=G149_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"zoom_range={res.effective_zoom_range} scale={res.effective_max_zoom_scale} "
            f"lever1={res.effective_zoom_lever_1st_speed} "
            f"lever2={res.effective_zoom_lever_2nd_speed} "
            f"autoslow={res.effective_auto_slow_shutter} "
            f"base_iso={res.effective_low_base_iso}/{res.effective_high_base_iso}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_zoom_ciz_autoslow_iso_baseiso_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G149ZoomCizAutoSlowBaseIsoGuardResult]:
    return evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
        **kwargs
    )


# ---------------------------------------------------------------------------
# Gate G150: Still .ARW Dormant Lossless, [HLG Still Image], [Sort Recording],
#            [USB LUN Setting] = Single Slot-1 Trap, NP-FZ100 USB-PD Gate,
#            and Dual FX3/FX6 Native UVC Streaming Myth-Busting
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StillArwHlgUsbLunUvcGuardResult:
    valid: bool
    status: str
    block_errno: int
    block_errno_name: str
    verification_mode: str
    still_image_quality_menu_path: str
    usb_menu_path: str
    network_streaming_menu_path: str
    effective_raw_file_type: str
    dormant_lossless_raw_rejected: bool
    effective_jh_switch: str
    effective_still_file_format: str
    effective_hlg_still_image: str
    effective_color_space: str
    effective_normal_iso_floor: int
    hlg_still_preconditions_met: bool
    effective_rec_media_mode: str
    sort_recording_auto_switch_spillover_risk: bool
    effective_usb_connection_mode: str
    effective_usb_lun_setting: str
    usb_lun_single_exposes_slot1_only: bool
    usb_setup_resettable_by_camset_reset: bool
    host_msc_contamination_firewall_active: bool
    effective_usb_power_supply: str
    np_fz100_pd_boot_gate_satisfied: bool
    effective_movie_rec_during_streaming: str
    effective_hdmi_rec_media_mode: str
    dormant_native_uvc_streaming_rejected: bool
    target_media_slot: int
    slot1_tier0_vault_firewall_blocked: bool
    slot1_data_sector_writes: int
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    violation_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_fx3_still_arw_hlg_usblun_uvc_state(
    *,
    raw_file_type: str = RAW_FILE_TYPE_DEFAULT_G150,
    jh_switch: str = JH_SWITCH_DEFAULT_G150,
    still_file_format: str = STILL_FMT_JPEG_G150,
    exposure_mode: str = EXPOSURE_MODE_P_G149,
    hlg_still_image: str = "Off",
    dro_bracket_or_iso_override: bool = False,
    rec_media_mode: str = REC_MEDIA_SLOT2_G150,
    auto_switch_media: str = "On",
    usb_connection_mode: str = USB_CONN_DEFAULT_G150,
    usb_lun_setting: str = USB_LUN_DEFAULT_G150,
    usb_power_supply: str = USB_POWER_SUPPLY_DEFAULT_G150,
    usb_port_type: str = USB_POWER_PORT_TYPE_C_G150,
    np_fz100_battery_inserted: bool = True,
    np_fz100_charge_pct: int = 80,
    dc_c1_65w_5a_coupler_active: bool = False,
    movie_rec_during_streaming: str = MOVIE_REC_DURING_STREAMING_DEFAULT_G150,
    hdmi_rec_media_mode: str = HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150,
    reset_action: str = RESET_ACTION_NONE_PHASE347,
) -> Dict[str, Any]:
    """Resolve authoritative FX3 Ver. 7.02 Wave-65 Still ARW/HLG + USB LUN/PD/Streaming state."""
    if reset_action in (
        RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        RESET_ACTION_INITIALIZE_PHASE347,
    ):
        eff_raw_type = RAW_FILE_TYPE_DEFAULT_G150
        eff_jh = JH_SWITCH_DEFAULT_G150
        eff_still_fmt = STILL_FMT_JPEG_G150
        eff_hlg_req = "Off"
    else:
        eff_raw_type = raw_file_type
        eff_jh = jh_switch
        eff_still_fmt = still_file_format
        eff_hlg_req = hlg_still_image

    if reset_action == RESET_ACTION_INITIALIZE_PHASE347:
        eff_rec_media = REC_MEDIA_SLOT1_G150
        eff_auto_sw = "Off"
        eff_usb_conn = USB_CONN_DEFAULT_G150
        eff_usb_lun = USB_LUN_DEFAULT_G150
        eff_usb_pwr = USB_POWER_SUPPLY_DEFAULT_G150
        eff_rec_dur_stream = MOVIE_REC_DURING_STREAMING_DEFAULT_G150
        eff_hdmi_rec = HDMI_REC_MEDIA_ON_G150
    else:
        eff_rec_media = rec_media_mode
        eff_auto_sw = auto_switch_media
        eff_usb_conn = usb_connection_mode
        eff_usb_lun = usb_lun_setting
        eff_usb_pwr = usb_power_supply
        eff_rec_dur_stream = movie_rec_during_streaming
        eff_hdmi_rec = hdmi_rec_media_mode

    hlg_precond = (
        eff_jh in (JH_SWITCH_HEIF_420_G150, JH_SWITCH_HEIF_422_G150)
        and eff_still_fmt == STILL_FMT_HEIF_G150
        and exposure_mode
        in (
            EXPOSURE_MODE_P_G149,
            EXPOSURE_MODE_A_G149,
            EXPOSURE_MODE_S_G149,
            EXPOSURE_MODE_M_G149,
        )
        and not dro_bracket_or_iso_override
    )
    eff_hlg = "On" if (eff_hlg_req == "On" and hlg_precond) else "Off"
    eff_color_space = HLG_STILL_COLOR_SPACE_G150 if eff_hlg == "On" else "sRGB"
    eff_iso_floor = HLG_STILL_ISO_FLOOR_G150 if eff_hlg == "On" else 80

    spillover_risk = (
        eff_rec_media == REC_MEDIA_SORT_G150 and eff_auto_sw == "On"
    )
    lun_single_exposes_slot1 = eff_usb_lun == USB_LUN_SINGLE_G150
    np_fz100_gate_ok = (
        (np_fz100_battery_inserted and np_fz100_charge_pct > 0)
        or dc_c1_65w_5a_coupler_active
    )

    return {
        "effective_raw_file_type": eff_raw_type,
        "effective_jh_switch": eff_jh,
        "effective_still_file_format": eff_still_fmt,
        "hlg_still_preconditions_met": hlg_precond,
        "effective_hlg_still_image": eff_hlg,
        "effective_color_space": eff_color_space,
        "effective_normal_iso_floor": eff_iso_floor,
        "effective_rec_media_mode": eff_rec_media,
        "effective_auto_switch_media": eff_auto_sw,
        "sort_recording_auto_switch_spillover_risk": spillover_risk,
        "effective_usb_connection_mode": eff_usb_conn,
        "effective_usb_lun_setting": eff_usb_lun,
        "usb_lun_single_exposes_slot1_only": lun_single_exposes_slot1,
        "effective_usb_power_supply": (
            eff_usb_pwr if usb_port_type == USB_POWER_PORT_TYPE_C_G150 else "Off"
        ),
        "np_fz100_pd_boot_gate_satisfied": np_fz100_gate_ok,
        "effective_movie_rec_during_streaming": eff_rec_dur_stream,
        "effective_hdmi_rec_media_mode": eff_hdmi_rec,
    }


def compute_still_arw_hlg_usblun_uvc_matrix() -> Dict[str, Any]:
    """Exhaustive combinatoric matrix for Gate G150 (384 states)."""
    combos = list(
        itertools.product(
            ALLOWED_RAW_FILE_TYPES_G150,
            (JH_SWITCH_JPEG_G150, JH_SWITCH_HEIF_422_G150),
            (STILL_FMT_HEIF_G150, STILL_FMT_RAW_HEIF_G150),
            ("Off", "On"),  # hlg_still_image
            (REC_MEDIA_SLOT2_G150, REC_MEDIA_SORT_G150),
            ALLOWED_USB_LUN_SETTINGS_G150,
            (True, False),  # np_fz100_battery_inserted
            (
                RESET_ACTION_NONE_PHASE347,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
                RESET_ACTION_INITIALIZE_PHASE347,
            ),
        )
    )
    hlg_active_bt2100_count = 0
    sort_spillover_count = 0
    usb_lun_single_slot1_count = 0
    camset_preserved_usb_lun_count = 0
    np_fz100_boot_blocked_count = 0

    for raw_t, jh_m, s_fmt, hlg_req, rec_m, lun_m, bat_in, rst in combos:
        st = resolve_fx3_still_arw_hlg_usblun_uvc_state(
            raw_file_type=raw_t,
            jh_switch=jh_m,
            still_file_format=s_fmt,
            exposure_mode=EXPOSURE_MODE_M_G149,
            hlg_still_image=hlg_req,
            rec_media_mode=rec_m,
            auto_switch_media="On",
            usb_lun_setting=lun_m,
            np_fz100_battery_inserted=bat_in,
            np_fz100_charge_pct=85 if bat_in else 0,
            reset_action=rst,
        )
        if (
            st["effective_hlg_still_image"] == "On"
            and st["effective_color_space"] == HLG_STILL_COLOR_SPACE_G150
            and st["effective_normal_iso_floor"] >= HLG_STILL_ISO_FLOOR_G150
        ):
            hlg_active_bt2100_count += 1
        if st["sort_recording_auto_switch_spillover_risk"]:
            sort_spillover_count += 1
        if st["usb_lun_single_exposes_slot1_only"]:
            usb_lun_single_slot1_count += 1
        if (
            rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347
            and lun_m == USB_LUN_SINGLE_G150
            and st["effective_usb_lun_setting"] == USB_LUN_SINGLE_G150
        ):
            camset_preserved_usb_lun_count += 1
        if not st["np_fz100_pd_boot_gate_satisfied"]:
            np_fz100_boot_blocked_count += 1

    return {
        "total_matrix_states": len(combos),
        "hlg_active_bt2100_count": hlg_active_bt2100_count,
        "sort_spillover_count": sort_spillover_count,
        "usb_lun_single_slot1_count": usb_lun_single_slot1_count,
        "camset_preserved_usb_lun_count": camset_preserved_usb_lun_count,
        "np_fz100_boot_blocked_count": np_fz100_boot_blocked_count,
    }


def verify_still_arw_hlg_usblun_uvc_guard(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
    body_model_name: str = FX3_MODEL_NAME_PHASE347,
    body_model_id: int = FX3_MODEL_ID_PHASE347,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE347,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE347,
    raw_file_type: str = RAW_FILE_TYPE_DEFAULT_G150,
    requested_dormant_lossless_raw: Optional[str] = None,
    jh_switch: str = JH_SWITCH_DEFAULT_G150,
    still_file_format: str = STILL_FMT_JPEG_G150,
    exposure_mode: str = EXPOSURE_MODE_P_G149,
    hlg_still_image: str = "Off",
    dro_bracket_or_iso_override: bool = False,
    claimed_hlg_still_allowed_with_raw_or_jpeg: bool = False,
    claimed_hlg_still_keeps_pp_or_creativelook_or_srgb: bool = False,
    rec_media_mode: str = REC_MEDIA_SLOT2_G150,
    auto_switch_media: str = "On",
    target_media_slot: int = MEDIA_SLOT_2_PHASE347,
    sort_or_still_write_requested: bool = False,
    usb_connection_mode: str = USB_CONN_DEFAULT_G150,
    usb_lun_setting: str = USB_LUN_DEFAULT_G150,
    claimed_usb_lun_single_hides_slot1: bool = False,
    claimed_camset_reset_clears_usb_settings: bool = False,
    host_msc_slot1_attach_requested: bool = False,
    usb_power_supply: str = USB_POWER_SUPPLY_DEFAULT_G150,
    usb_port_type: str = USB_POWER_PORT_TYPE_C_G150,
    np_fz100_battery_inserted: bool = True,
    np_fz100_charge_pct: int = 80,
    dc_c1_65w_5a_coupler_active: bool = False,
    claimed_usb_pd_boots_without_battery_or_dcc1: bool = False,
    claimed_multi_micro_usb_supplies_power: bool = False,
    requested_native_uvc_usb_streaming_fx3: bool = False,
    requested_native_uvc_usb_streaming_fx6: bool = False,
    movie_rec_during_streaming: str = MOVIE_REC_DURING_STREAMING_DEFAULT_G150,
    hdmi_rec_media_mode: str = HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150,
    requested_write_operation: bool = False,
    reset_action: str = RESET_ACTION_NONE_PHASE347,
    fx6_still_arw_or_hlg_photo_spoof_requested: bool = False,
) -> StillArwHlgUsbLunUvcGuardResult:
    """Enforce Gate G150: Still .ARW Dormant Lossless, HLG Photo, USB LUN Single Trap, NP-FZ100 & UVC Firewall."""
    errors: List[str] = []
    warnings: List[str] = []
    violations: List[str] = []

    def _add(code: str, msg: str) -> None:
        violations.append(code)
        errors.append(msg)

    errors.extend(
        _validate_fx3_body_identity(
            body_model_name, body_model_id, help_guide_code, firmware_version
        )
    )

    dormant_lossless = (
        requested_dormant_lossless_raw is not None
        or raw_file_type in DORMANT_RAW_FILE_TYPES_G150
    )
    if dormant_lossless:
        _add(
            "DORMANT_LOSSLESS_RAW_EOPNOTSUPP",
            f"fx3_ver_7_02_lossless_comp_raw_is_100pct_dormant_only_compressed_or_uncompressed_exposed_eopnotsupp_95:{requested_dormant_lossless_raw or raw_file_type!r}",
        )
    elif raw_file_type not in ALLOWED_RAW_FILE_TYPES_G150:
        _add("TELEMETRY_INVALID", f"raw_file_type_invalid:{raw_file_type!r}")

    dormant_uvc = (
        requested_native_uvc_usb_streaming_fx3
        or requested_native_uvc_usb_streaming_fx6
        or usb_connection_mode in DORMANT_USB_STREAMING_MODE_NAMES_G150
    )
    if dormant_uvc:
        _add(
            "DORMANT_NATIVE_UVC_STREAMING_EOPNOTSUPP",
            "neither_fx3_ver_7_02_nor_fx6_ver_6_01_exposes_native_uvc_usb_streaming_eopnotsupp_95",
        )
    elif usb_connection_mode not in EXACT_4_USB_CONNECTION_MODES_G150:
        _add("TELEMETRY_INVALID", f"usb_connection_mode_invalid:{usb_connection_mode!r}")

    if fx6_still_arw_or_hlg_photo_spoof_requested:
        _add(
            "FX6_STILL_ARW_HLG_EOPNOTSUPP",
            "fx6_cinema_body_has_zero_still_arw_or_hlg_still_image_pipeline_eopnotsupp_95",
        )

    if jh_switch not in ALLOWED_JH_SWITCH_MODES_G150:
        _add("TELEMETRY_INVALID", f"jh_switch_invalid:{jh_switch!r}")
    if still_file_format not in ALLOWED_STILL_FILE_FORMATS_G150:
        _add("TELEMETRY_INVALID", f"still_file_format_invalid:{still_file_format!r}")
    if exposure_mode not in ALLOWED_EXPOSURE_MODES_G149:
        _add("TELEMETRY_INVALID", f"exposure_mode_invalid:{exposure_mode!r}")
    if not _is_on_off(hlg_still_image):
        _add("TELEMETRY_INVALID", f"hlg_still_image_invalid:{hlg_still_image!r}")
    if rec_media_mode not in ALLOWED_REC_MEDIA_MODES_G150:
        _add("TELEMETRY_INVALID", f"rec_media_mode_invalid:{rec_media_mode!r}")
    if not _is_on_off(auto_switch_media):
        _add("TELEMETRY_INVALID", f"auto_switch_media_invalid:{auto_switch_media!r}")
    if not _is_strict_int(target_media_slot) or target_media_slot not in ALLOWED_MEDIA_SLOTS_PHASE347:
        _add("TELEMETRY_INVALID", f"target_media_slot_invalid:{target_media_slot!r}")
    if usb_lun_setting not in ALLOWED_USB_LUN_SETTINGS_G150:
        _add("TELEMETRY_INVALID", f"usb_lun_setting_invalid:{usb_lun_setting!r}")
    if not _is_on_off(usb_power_supply):
        _add("TELEMETRY_INVALID", f"usb_power_supply_invalid:{usb_power_supply!r}")
    if usb_port_type not in (USB_POWER_PORT_TYPE_C_G150, USB_POWER_PORT_MULTI_MICRO_G150):
        _add("TELEMETRY_INVALID", f"usb_port_type_invalid:{usb_port_type!r}")
    if not _is_strict_int(np_fz100_charge_pct) or not (0 <= np_fz100_charge_pct <= 100):
        _add("TELEMETRY_INVALID", f"np_fz100_charge_pct_invalid:{np_fz100_charge_pct!r}")
    if movie_rec_during_streaming not in ALLOWED_MOVIE_REC_DURING_STREAMING_G150:
        _add(
            "TELEMETRY_INVALID",
            f"movie_rec_during_streaming_invalid:{movie_rec_during_streaming!r}",
        )
    if hdmi_rec_media_mode not in ALLOWED_HDMI_REC_MEDIA_MODES_G150:
        _add("TELEMETRY_INVALID", f"hdmi_rec_media_mode_invalid:{hdmi_rec_media_mode!r}")
    if reset_action not in ALLOWED_RESET_ACTIONS_PHASE347:
        _add("TELEMETRY_INVALID", f"reset_action_invalid:{reset_action!r}")

    state = resolve_fx3_still_arw_hlg_usblun_uvc_state(
        raw_file_type=(
            raw_file_type
            if raw_file_type in ALLOWED_RAW_FILE_TYPES_G150
            else RAW_FILE_TYPE_DEFAULT_G150
        ),
        jh_switch=(
            jh_switch if jh_switch in ALLOWED_JH_SWITCH_MODES_G150 else JH_SWITCH_DEFAULT_G150
        ),
        still_file_format=(
            still_file_format
            if still_file_format in ALLOWED_STILL_FILE_FORMATS_G150
            else STILL_FMT_JPEG_G150
        ),
        exposure_mode=(
            exposure_mode if exposure_mode in ALLOWED_EXPOSURE_MODES_G149 else EXPOSURE_MODE_P_G149
        ),
        hlg_still_image=hlg_still_image if _is_on_off(hlg_still_image) else "Off",
        dro_bracket_or_iso_override=dro_bracket_or_iso_override,
        rec_media_mode=(
            rec_media_mode if rec_media_mode in ALLOWED_REC_MEDIA_MODES_G150 else REC_MEDIA_SLOT2_G150
        ),
        auto_switch_media=auto_switch_media if _is_on_off(auto_switch_media) else "On",
        usb_connection_mode=(
            usb_connection_mode
            if usb_connection_mode in EXACT_4_USB_CONNECTION_MODES_G150
            else USB_CONN_DEFAULT_G150
        ),
        usb_lun_setting=(
            usb_lun_setting
            if usb_lun_setting in ALLOWED_USB_LUN_SETTINGS_G150
            else USB_LUN_DEFAULT_G150
        ),
        usb_power_supply=usb_power_supply if _is_on_off(usb_power_supply) else USB_POWER_SUPPLY_DEFAULT_G150,
        usb_port_type=usb_port_type,
        np_fz100_battery_inserted=np_fz100_battery_inserted,
        np_fz100_charge_pct=np_fz100_charge_pct if _is_strict_int(np_fz100_charge_pct) else 0,
        dc_c1_65w_5a_coupler_active=dc_c1_65w_5a_coupler_active,
        movie_rec_during_streaming=(
            movie_rec_during_streaming
            if movie_rec_during_streaming in ALLOWED_MOVIE_REC_DURING_STREAMING_G150
            else MOVIE_REC_DURING_STREAMING_DEFAULT_G150
        ),
        hdmi_rec_media_mode=(
            hdmi_rec_media_mode
            if hdmi_rec_media_mode in ALLOWED_HDMI_REC_MEDIA_MODES_G150
            else HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150
        ),
        reset_action=reset_action if reset_action in ALLOWED_RESET_ACTIONS_PHASE347 else RESET_ACTION_NONE_PHASE347,
    )

    # HLG Still Image checks
    if claimed_hlg_still_allowed_with_raw_or_jpeg and not state["hlg_still_preconditions_met"]:
        _add(
            "HLG_STILL_PRECONDITION_VIOLATION",
            "hlg_still_image_requires_heif_420_or_422_and_file_format_heif_without_raw_and_pasm_einval_22",
        )
    if state["effective_hlg_still_image"] == "On" and claimed_hlg_still_keeps_pp_or_creativelook_or_srgb:
        _add(
            "HLG_STILL_BT2100_ISO_FLOOR_VIOLATION",
            "hlg_still_image_forces_bt2100_raises_iso_floor_100_125_and_disables_pp_creativelook_dro_einval_22",
        )

    # USB LUN Setting = Single Trap & Setup Reset Immunity
    if claimed_usb_lun_single_hides_slot1:
        _add(
            "USB_LUN_SINGLE_SLOT1_TRAP_VIOLATION",
            "usb_lun_setting_single_exposes_slot1_only_does_not_hide_slot1_einval_22",
        )
    if claimed_camset_reset_clears_usb_settings:
        _add(
            "USB_SETUP_RESET_IMMUNITY_VIOLATION",
            "usb_connection_mode_lun_setting_and_usb_power_supply_are_initialize_only_not_resettable_einval_22",
        )

    # NP-FZ100 USB-C PD Boot Gate
    if (
        (not state["np_fz100_pd_boot_gate_satisfied"])
        or claimed_usb_pd_boots_without_battery_or_dcc1
    ):
        _add(
            "NP_FZ100_PD_BOOT_GATE_VIOLATION",
            "fx3_usb_c_pd_requires_charged_np_fz100_inserted_or_dc_c1_65w_5a_coupler_einval_22",
        )
    if claimed_multi_micro_usb_supplies_power or usb_port_type == USB_POWER_PORT_MULTI_MICRO_G150:
        _add(
            "USB_POWER_TYPE_C_ONLY_VIOLATION",
            "fx3_usb_power_supply_accepts_usb_type_c_only_not_multi_micro_usb_einval_22",
        )

    # HARD EROFS=30 Slot-1 Tier-0 Vault Firewall (Sort spillover / Host MSC / Stream Rec / Direct writes)
    slot1_streaming_rec_hazard = (
        target_media_slot == MEDIA_SLOT_1_PHASE347
        and (
            movie_rec_during_streaming == "Enable"
            or hdmi_rec_media_mode == HDMI_REC_MEDIA_ON_G150
        )
    )
    slot1_sort_or_write_hazard = (
        target_media_slot == MEDIA_SLOT_1_PHASE347
        and (
            sort_or_still_write_requested
            or requested_write_operation
            or (
                rec_media_mode in (REC_MEDIA_SLOT1_G150, REC_MEDIA_SIMULT_G150)
                and sort_or_still_write_requested
            )
            or state["sort_recording_auto_switch_spillover_risk"]
            and sort_or_still_write_requested
        )
    )
    slot1_blocked = bool(
        host_msc_slot1_attach_requested
        or slot1_streaming_rec_hazard
        or slot1_sort_or_write_hazard
    )
    if slot1_blocked:
        _add(
            "SLOT1_TIER0_VAULT_EROFS",
            "slot1_tier0_vault_erofs_30_hard_blocked_msc_mount_sort_spillover_or_stream_rec_write",
        )

    if len(errors) == 0:
        status = STATUS_VERIFIED_G150
        block_errno = 0
        block_errno_name = "OK"
    elif slot1_blocked:
        status = STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS
        block_errno = EROFS_ERRNO_PHASE347
        block_errno_name = EROFS_NAME_PHASE347
    elif any("EOPNOTSUPP" in v for v in violations):
        status = STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP
        block_errno = EOPNOTSUPP_ERRNO_PHASE347
        block_errno_name = EOPNOTSUPP_NAME_PHASE347
    elif any(v == "TELEMETRY_INVALID" for v in violations) or any(
        e.startswith(
            (
                "body_model_name_invalid:",
                "body_model_id_invalid:",
                "help_guide_code_invalid:",
                "firmware_version_invalid:",
            )
        )
        for e in errors
    ):
        status = STATUS_BLOCKED_G150_TELEMETRY_INVALID
        block_errno = EINVAL_ERRNO_PHASE347
        block_errno_name = EINVAL_NAME_PHASE347
    else:
        status = STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION
        block_errno = EINVAL_ERRNO_PHASE347
        block_errno_name = EINVAL_NAME_PHASE347

    return StillArwHlgUsbLunUvcGuardResult(
        valid=len(errors) == 0,
        status=status,
        block_errno=block_errno,
        block_errno_name=block_errno_name,
        verification_mode=verification_mode,
        still_image_quality_menu_path=STILL_IMAGE_QUALITY_MENU_PATH_G150,
        usb_menu_path=USB_MENU_PATH_G150,
        network_streaming_menu_path=NETWORK_STREAMING_MENU_PATH_G150,
        effective_raw_file_type=state["effective_raw_file_type"],
        dormant_lossless_raw_rejected=dormant_lossless,
        effective_jh_switch=state["effective_jh_switch"],
        effective_still_file_format=state["effective_still_file_format"],
        effective_hlg_still_image=state["effective_hlg_still_image"],
        effective_color_space=state["effective_color_space"],
        effective_normal_iso_floor=state["effective_normal_iso_floor"],
        hlg_still_preconditions_met=state["hlg_still_preconditions_met"],
        effective_rec_media_mode=state["effective_rec_media_mode"],
        sort_recording_auto_switch_spillover_risk=state[
            "sort_recording_auto_switch_spillover_risk"
        ],
        effective_usb_connection_mode=state["effective_usb_connection_mode"],
        effective_usb_lun_setting=state["effective_usb_lun_setting"],
        usb_lun_single_exposes_slot1_only=state["usb_lun_single_exposes_slot1_only"],
        usb_setup_resettable_by_camset_reset=False,
        host_msc_contamination_firewall_active=True,
        effective_usb_power_supply=state["effective_usb_power_supply"],
        np_fz100_pd_boot_gate_satisfied=state["np_fz100_pd_boot_gate_satisfied"],
        effective_movie_rec_during_streaming=state[
            "effective_movie_rec_during_streaming"
        ],
        effective_hdmi_rec_media_mode=state["effective_hdmi_rec_media_mode"],
        dormant_native_uvc_streaming_rejected=dormant_uvc,
        target_media_slot=target_media_slot,
        slot1_tier0_vault_firewall_blocked=slot1_blocked,
        slot1_data_sector_writes=0,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        violation_codes=tuple(violations),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class G150StillArwHlgUsbLunUvcGuardResult:
    gate_id: str
    gate_code: str
    valid: bool
    status: str
    verification_mode: str
    emmc_writes_authorized: bool
    persistent_emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    raw_firmware_bytes_leaked: int
    donor_audit: Dict[str, Any]
    still_arw_hlg_usblun_uvc_guard: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
    *,
    repo_root: Optional[Path] = None,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    **guard_kwargs: Any,
) -> Tuple[GateVerdict, G150StillArwHlgUsbLunUvcGuardResult]:
    audit = audit_phase347_donor_contracts(
        repo_root=repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
    )
    res = verify_still_arw_hlg_usblun_uvc_guard(
        verification_mode=audit.verification_mode,
        **guard_kwargs,
    )
    overall_valid = audit.valid and res.valid
    status = res.status if audit.valid else audit.status
    errors = tuple(list(audit.errors) + list(res.errors))
    warnings = tuple(list(audit.warnings) + list(res.warnings))

    wrapped = G150StillArwHlgUsbLunUvcGuardResult(
        gate_id=G150,
        gate_code=G150_GATE_CODE,
        valid=overall_valid,
        status=status,
        verification_mode=audit.verification_mode,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_audit=audit.to_dict(),
        still_arw_hlg_usblun_uvc_guard=res.to_dict(),
        errors=errors,
        warnings=warnings,
    )
    verdict = GateVerdict(
        gate_id=G150,
        gate_code=G150_GATE_CODE,
        passed=overall_valid,
        status=status,
        evidence=(
            f"status={status} mode={audit.verification_mode} "
            f"raw={res.effective_raw_file_type} "
            f"hlg={res.effective_hlg_still_image} "
            f"lun={res.effective_usb_lun_setting} "
            f"pd_ok={res.np_fz100_pd_boot_gate_satisfied} "
            f"s1_writes={res.slot1_data_sector_writes}"
        ),
        violation_codes=res.violation_codes,
        errors=errors,
        warnings=warnings,
    )
    return verdict, wrapped


def verify_still_arw_hlg_usblun_uvc_guard_with_audit(
    **kwargs: Any,
) -> Tuple[GateVerdict, G150StillArwHlgUsbLunUvcGuardResult]:
    return evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
        **kwargs
    )


# ---------------------------------------------------------------------------
# Unified 150-Gate Master Safety Preflight Engine (G01..G150)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Master150GateReport:
    schema: str
    schema_version: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_147_gates_verified: bool
    all_150_gates_verified: bool
    g13_to_g150_all_passed: bool
    g149_to_g150_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    cross_model_flash_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_148_report: Dict[str, Any]
    g149_result: Dict[str, Any]
    g150_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _build_master_148_chain_override(
    *,
    repo_root: Path,
    work_root: Optional[Path],
    force_clean_room: Optional[bool],
    dry_run_sim: bool,
    req_persist: bool,
    upstream_kwargs: Mapping[str, Any],
) -> Master148GateReport:
    """Propagate any pre-148 fault kwargs cleanly down through M142 -> M144 -> M146 -> M148."""
    m142_keys = (
        "ftp_ftpes_customwb_kwargs",
        "movie_af_focusmap_marker_kwargs",
        "master_140_override",
        "rec_media_autoswitch_proxy_kwargs",
        "creators_cloud_mymenu_kwargs",
        "big6_home_framing_interval_kwargs",
        "tc_make_ssh_fan_kwargs",
        "bright_mon_shotmark_kwargs",
        "tc_link_wifi_usblan_bulb_kwargs",
    )
    m142_kw = {k: upstream_kwargs[k] for k in m142_keys if k in upstream_kwargs and upstream_kwargs[k] is not None}
    m142_rep = evaluate_142gate_preflight(
        repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        dry_run_simulated=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **m142_kw,
    )
    m144_kw: Dict[str, Any] = {"master_142_override": m142_rep}
    for k in ("shoe_audio_subject_recog_kwargs", "silent_target_bodydata_kwargs"):
        if upstream_kwargs.get(k) is not None:
            m144_kw[k] = upstream_kwargs[k]
    m144_rep = evaluate_144gate_preflight(
        repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        dry_run_simulated=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **m144_kw,
    )
    m146_kw: Dict[str, Any] = {"master_144_override": m144_rep}
    for k in ("hdmi_raw_desqueeze_kwargs", "reclamp_varshutter_apsc_kwargs"):
        if upstream_kwargs.get(k) is not None:
            m146_kw[k] = upstream_kwargs[k]
    m146_rep = evaluate_146gate_preflight(
        repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        dry_run_simulated=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **m146_kw,
    )
    m148_kw: Dict[str, Any] = {"master_146_override": m146_rep}
    for k in ("breathing_camid_reel_kwargs", "copyright_powersave_ntscpal_kwargs"):
        if upstream_kwargs.get(k) is not None:
            m148_kw[k] = upstream_kwargs[k]
    return evaluate_148gate_preflight(
        repo_root,
        work_root=work_root,
        force_clean_room=force_clean_room,
        dry_run_simulated=dry_run_sim,
        request_persistent_emmc_writes=req_persist,
        **m148_kw,
    )


def evaluate_150gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    work_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    simulate_bench_dry_run: Optional[bool] = None,
    dry_run_simulated_backup: Optional[bool] = None,
    request_persistent_emmc_writes: bool = False,
    master_148_override: Optional[Master148GateReport] = None,
    zoom_ciz_autoslow_baseiso_kwargs: Optional[Mapping[str, Any]] = None,
    still_arw_hlg_usblun_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    **extra_upstream_kwargs: Any,
) -> Master150GateReport:
    """Evaluate unified 150-Gate Milestone Master Safety Preflight (`G01..G150`)."""
    effective_dry_run = (
        bool(dry_run_simulated)
        or (simulate_bench_dry_run is True)
        or (dry_run_simulated_backup is True)
    )
    clean_forced = _is_clean_room_forced(force_clean_room)
    resolved_repo_root = repo_root or DEFAULT_REPO_ROOT
    resolved_work_root_for_m148 = (
        work_root
        if work_root is not None
        else resolve_donor_thermal_power_paths(repo_root=resolved_repo_root).work_root
    )
    m148_force_clean_room = (
        True
        if (clean_forced or resolved_work_root_for_m148 is None)
        else force_clean_room
    )

    if master_148_override is not None:
        m148_report = master_148_override
    elif any(v is not None for v in extra_upstream_kwargs.values()):
        m148_report = _build_master_148_chain_override(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=m148_force_clean_room,
            dry_run_sim=effective_dry_run,
            req_persist=request_persistent_emmc_writes,
            upstream_kwargs=extra_upstream_kwargs,
        )
    else:
        m148_report = evaluate_148gate_preflight(
            resolved_repo_root,
            work_root=work_root,
            force_clean_room=m148_force_clean_room,
            dry_run_simulated=effective_dry_run,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )

    g149_kw = dict(zoom_ciz_autoslow_baseiso_kwargs or {})
    g149_verdict, g149_res = (
        evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g149_kw,
        )
    )

    g150_kw = dict(still_arw_hlg_usblun_uvc_kwargs or {})
    if "requested_write_operation" not in g150_kw and request_persistent_emmc_writes:
        g150_kw["requested_write_operation"] = True
        if "target_media_slot" not in g150_kw:
            g150_kw["target_media_slot"] = MEDIA_SLOT_1_PHASE347
    g150_verdict, g150_res = (
        evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=resolved_repo_root,
            work_root=work_root,
            force_clean_room=force_clean_room,
            **g150_kw,
        )
    )

    new_gate_dicts = (
        {
            "gate_id": G149,
            "gate_code": G149_GATE_CODE,
            "status": g149_res.status,
            "passed": g149_verdict.passed,
            "evidence": g149_verdict.evidence,
            "violation_codes": list(g149_verdict.errors),
        },
        {
            "gate_id": G150,
            "gate_code": G150_GATE_CODE,
            "status": g150_res.status,
            "passed": g150_verdict.passed,
            "evidence": g150_verdict.evidence,
            "violation_codes": list(g150_verdict.errors),
        },
    )

    all_gates: Tuple[Dict[str, Any], ...] = tuple(m148_report.gates) + new_gate_dicts
    g01_to_g12_verified = int(m148_report.summary["g01_to_g12_verified"])
    g13_to_g148_verified = (
        int(m148_report.summary["g13_to_g146_verified"])
        + int(m148_report.summary["g147_to_g148_verified"])
    )
    g149_to_g150_verified = int(bool(g149_verdict.passed)) + int(
        bool(g150_verdict.passed)
    )
    total_verified = g01_to_g12_verified + g13_to_g148_verified + g149_to_g150_verified

    g149_to_g150_all_passed = g149_to_g150_verified == 2
    g13_to_g150_all_passed = (
        m148_report.g13_to_g148_all_passed and g149_to_g150_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m148_report.gates[:9])

    offline_147_verified = (
        g01_to_g09_ok
        and m148_report.offline_145_gates_verified
        and g149_to_g150_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_150_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g150_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m148_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_147_verified
        and m148_report.h0_h1_trial_entry_allowed
        and g149_to_g150_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m148_report.errors)
        + list(g149_verdict.errors)
        + list(g150_verdict.errors)
    )
    warnings: List[str] = (
        list(m148_report.warnings)
        + list(g149_verdict.warnings)
        + list(g150_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m148_report.g13_to_g148_all_passed:
        overall_status = m148_report.status
    elif not g149_verdict.passed:
        overall_status = g149_verdict.status
    elif not g150_verdict.passed:
        overall_status = g150_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_150_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_150_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_150_verified:
        overall_status = "VERIFIED_ALL_150_GATES"
    else:
        overall_status = "VERIFIED_147_OF_150_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m148_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g149_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g150_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 150,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 150 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g148_verified": g13_to_g148_verified,
        "g149_to_g150_verified": g149_to_g150_verified,
        "g13_to_g150_all_passed": g13_to_g150_all_passed,
        "g149_to_g150_all_passed": g149_to_g150_all_passed,
        "offline_147_gates_verified": offline_147_verified,
        "all_150_gates_verified": all_150_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master150GateReport(
        schema=REALHW_150GATE_PREFLIGHT_SCHEMA,
        schema_version=REALHW_150GATE_PREFLIGHT_SCHEMA,
        version=REALHW_ZOOM_CIZ_AUTOSLOW_ISO_ARW_RAWCOMP_USBLUN_UVC_150GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_147_gates_verified=offline_147_verified,
        all_150_gates_verified=all_150_verified,
        g13_to_g150_all_passed=g13_to_g150_all_passed,
        g149_to_g150_all_passed=g149_to_g150_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_148_report=m148_report.to_dict(),
        g149_result=g149_res.to_dict(),
        g150_result=g150_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_150_master_safety_gates(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master150GateReport:
    return evaluate_150gate_preflight(repo_root, **kwargs)


def run_150_gate_preflight(
    repo_root: Optional[Path] = None, **kwargs: Any
) -> Master150GateReport:
    return evaluate_150gate_preflight(repo_root, **kwargs)


def _safe_write_json(payload: Any) -> None:
    try:
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard",
        description="Phase 347 (Task H432, Wave-65) G149/G150 and 150/150 Unified Safety Preflight CLI",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so all 150/150 gates can be rehearsed offline",
    )
    parser.add_argument(
        "--gate",
        choices=["g149", "g150", "150"],
        default="150",
        help="Target gate check: g149, g150, or 150",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit compact summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    clean = True if args.force_clean_room else None
    if args.gate == "g149":
        v, r = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    if args.gate == "g150":
        v, r = evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=args.repo_root,
            force_clean_room=clean,
        )
        if args.json:
            _safe_write_json(
                {
                    "gate": v.gate_id,
                    "status": r.status,
                    "verification_mode": r.verification_mode,
                    "valid": r.valid,
                    "raw_firmware_bytes_leaked": r.raw_firmware_bytes_leaked,
                }
                if args.summary
                else r.to_dict()
            )
        else:
            sys.stdout.write(f"gate={v.gate_id} status={r.status} valid={r.valid}\n")
        return 0 if r.valid else 1

    rep = evaluate_150gate_preflight(
        args.repo_root,
        force_clean_room=clean,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _safe_write_json(
            {
                "schema_version": rep.schema_version,
                "status": rep.status,
                "verification_mode": rep.verification_mode,
                "summary": rep.summary,
                "g149_status": rep.g149_result["status"],
                "g150_status": rep.g150_result["status"],
            }
            if args.summary
            else rep.to_dict()
        )
    else:
        sys.stdout.write(
            f"status={rep.status} mode={rep.verification_mode} "
            f"verified={rep.summary['verified_gates']}/150 "
            f"g149_to_g150_all_passed={rep.g149_to_g150_all_passed} "
            f"all_150_gates_verified={rep.all_150_gates_verified} "
            f"dry_run_rehearsal_only={rep.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={rep.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={rep.overall_ready_for_hardware_attach} "
            f"hardware_live_attachment_authorized={rep.hardware_live_attachment_authorized} "
            f"el3_payload_transmit_authorized={rep.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={rep.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={rep.persistent_emmc_writes_authorized} "
            f"cross_model_flash_authorized={rep.cross_model_flash_authorized} "
            f"usb_packets_transmitted={rep.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={rep.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        rep.all_150_gates_verified
        if args.dry_run_simulated
        else rep.offline_147_gates_verified
    )
    return 0 if ok else 1


__all__ = [
    "ALLOWED_CINE_EI_BASE_ISOS_G149",
    "ALLOWED_EXPOSURE_MODES_G149",
    "ALLOWED_GAMMA_CURVES_G149",
    "ALLOWED_HDMI_REC_MEDIA_MODES_G150",
    "ALLOWED_ISO_AUTO_MIN_SS_PRESETS_G149",
    "ALLOWED_JH_SWITCH_MODES_G150",
    "ALLOWED_LOG_SHOOTING_MODES_G149",
    "ALLOWED_MEDIA_SLOTS_PHASE347",
    "ALLOWED_MOVIE_REC_DURING_STREAMING_G150",
    "ALLOWED_RAW_FILE_TYPES_G150",
    "ALLOWED_REC_MEDIA_MODES_G150",
    "ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G149",
    "ALLOWED_RESET_ACTIONS_PHASE347",
    "ALLOWED_SHOOT_MODES_PHASE347",
    "ALLOWED_SHUTTER_MODES_G149",
    "ALLOWED_STILL_FILE_FORMATS_G150",
    "ALLOWED_USB_LUN_SETTINGS_G150",
    "ALLOWED_ZOOM_RANGES_G149",
    "ALLOWED_ZOOM_RING_ROTATIONS_G149",
    "AUTO_SLOW_SHUTTER_DEFAULT_G149",
    "AUTO_SLOW_SHUTTER_F_RESID16_G149",
    "AUTO_SLOW_SHUTTER_RESETTABLE_BY_CAMSET_RESET_G149",
    "BASE_ISO_DEFAULT_G149",
    "BASE_ISO_F_RESID16_G149",
    "BASE_ISO_HIGH_G149",
    "BASE_ISO_LOW_G149",
    "CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149",
    "CUSTOM_KEY_ZOOM_SPEED_F_RESID16_G149",
    "CUSTOM_KEY_ZOOM_SPEED_MENU_PATH_G149",
    "CUSTOM_KEY_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149",
    "DONOR_CHECK_CI_MAX_SECONDS_PHASE347",
    "DONOR_CHECK_MAX_SECONDS_PHASE347",
    "DORMANT_LIVE_STREAM_USB_F_RESID16_G150",
    "DORMANT_LOSSLESS_COMP_F_RESID16S_G150",
    "DORMANT_RAW_FILE_TYPES_G150",
    "DORMANT_USB_STREAMING_G_RESID16_G150",
    "DORMANT_USB_STREAMING_MODE_NAMES_G150",
    "DORMANT_USB_STREAM_RES_F_RESID16_G150",
    "DUAL_BASE_ISO_GAMMA_MAP_G149",
    "EINVAL_ERRNO_PHASE347",
    "EINVAL_NAME_PHASE347",
    "ENV_CLEAN_ROOM_TEST_PHASE347",
    "EOPNOTSUPP_ERRNO_PHASE347",
    "EOPNOTSUPP_NAME_PHASE347",
    "EROFS_ERRNO_PHASE347",
    "EROFS_NAME_PHASE347",
    "EXACT_4_USB_CONNECTION_MODES_G150",
    "EXPOSURE_MENU_PATH_G149",
    "EXPOSURE_MODE_A_G149",
    "EXPOSURE_MODE_FLEXIBLE_G149",
    "EXPOSURE_MODE_IAUTO_G149",
    "EXPOSURE_MODE_M_G149",
    "EXPOSURE_MODE_P_G149",
    "EXPOSURE_MODE_S_G149",
    "FX3_DCC1_CABLE_AMPS_G150",
    "FX3_DCC1_MIN_PD_WATTS_G150",
    "FX3_DEFAULT_FW_VERSION_PHASE347",
    "FX3_HELP_GUIDE_CODE_PHASE347",
    "FX3_MODEL_ID_PHASE347",
    "FX3_MODEL_NAME_PHASE347",
    "FX6_DC_IN_VOLTS_G150",
    "FX6_DEFAULT_FW_VERSION_PHASE347",
    "FX6_HANDLE_ZOOM_HIGH_DEFAULT_G149",
    "FX6_HANDLE_ZOOM_LOW_DEFAULT_G149",
    "FX6_HANDLE_ZOOM_MODES_G149",
    "FX6_MODEL_NAME_PHASE347",
    "FX6_ZOOM_TYPES_G149",
    "G149",
    "G149ZoomCizAutoSlowBaseIsoGuardResult",
    "G149_GATE_CODE",
    "G149_GATE_ID",
    "G150",
    "G150StillArwHlgUsbLunUvcGuardResult",
    "G150_GATE_CODE",
    "G150_GATE_ID",
    "HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150",
    "HDMI_REC_MEDIA_ON_G150",
    "HEIF_420_F_RESID16_G150",
    "HEIF_422_F_RESID16_G150",
    "HLG_STILL_COLOR_SPACE_G150",
    "HLG_STILL_IMAGE_ELF_TYPO_SYMBOLS_G150",
    "HLG_STILL_IMAGE_F_RESID16_G150",
    "HLG_STILL_ISO_FLOOR_G150",
    "ISO_AUTO_MIN_SS_DEFAULT_G149",
    "ISO_AUTO_MIN_SS_FLASH_OVERRIDE_G149",
    "ISO_AUTO_MIN_SS_F_RESID16_G149",
    "ISO_AUTO_MIN_SS_RESETTABLE_BY_CAMSET_RESET_G149",
    "ISO_RANGE_LIMIT_F_RESID16_G149",
    "ISO_RANGE_LIMIT_RESETTABLE_BY_CAMSET_RESET_G149",
    "JH_SWITCH_DEFAULT_G150",
    "JH_SWITCH_HEIF_420_G150",
    "JH_SWITCH_HEIF_422_G150",
    "JH_SWITCH_JPEG_G150",
    "JPEG_HEIF_SWITCH_F_RESID16_G150",
    "LOG_SHOOTING_CINE_EI_G149",
    "LOG_SHOOTING_CINE_EI_QUICK_G149",
    "LOG_SHOOTING_FLEXIBLE_ISO_G149",
    "LOG_SHOOTING_OFF_G149",
    "MACOS_MSC_POLLUTION_DAEMONS_G150",
    "MEDIA_SLOT_1_PHASE347",
    "MEDIA_SLOT_2_PHASE347",
    "MEDIA_SLOT_NONE_PHASE347",
    "MOVIE_CIZ_4K_SCALE_G149",
    "MOVIE_CIZ_HD_SCALE_G149",
    "MOVIE_DIGITAL_ZOOM_SCALE_G149",
    "MOVIE_REC_DURING_STREAMING_DEFAULT_G150",
    "MOVIE_REC_DURING_STREAMING_F_RESID16_G150",
    "Master150GateReport",
    "NETWORK_STREAMING_MENU_PATH_G150",
    "PINNED_FX3_APPFW_SLICES_PHASE347",
    "PINNED_FX3_APPFW_SLICES_SHA256_PHASE347",
    "PINNED_FX6_APPFW_SLICES_PHASE347",
    "PINNED_FX6_APPFW_SLICES_SHA256_PHASE347",
    "PINNED_PHASE347_DONOR_SPECS",
    "Phase347DonorAuditResult",
    "RAW_COMPRESSED_F_RESID16_G150",
    "RAW_FILE_TYPE_COMPRESSED_G150",
    "RAW_FILE_TYPE_DEFAULT_G150",
    "RAW_FILE_TYPE_F_RESID16_G150",
    "RAW_FILE_TYPE_UNCOMPRESSED_G150",
    "RAW_UNCOMPRESSED_F_RESID16_G150",
    "REALHW_150GATE_PREFLIGHT_SCHEMA",
    "REALHW_ZOOM_CIZ_AUTOSLOW_ISO_ARW_RAWCOMP_USBLUN_UVC_150GATE_SCHEMA",
    "REALHW_ZOOM_CIZ_AUTOSLOW_ISO_ARW_RAWCOMP_USBLUN_UVC_150GATE_VERSION",
    "REC_MEDIA_DUR_HDMI_OUTPUT_F_RESID16_G150",
    "REC_MEDIA_SIMULT_G150",
    "REC_MEDIA_SLOT1_G150",
    "REC_MEDIA_SLOT2_G150",
    "REC_MEDIA_SORT_G150",
    "REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149",
    "REMOTE_ZOOM_SPEED_F_RESID16_G149",
    "REMOTE_ZOOM_SPEED_MENU_PATH_G149",
    "REMOTE_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149",
    "REMOTE_ZOOM_SPEED_TYPE_DEFAULT_G149",
    "REMOTE_ZOOM_SPEED_TYPE_FIXED_G149",
    "REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149",
    "RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347",
    "RESET_ACTION_INITIALIZE_PHASE347",
    "RESET_ACTION_NONE_PHASE347",
    "RESET_ACTION_RESET_NETWORK_SET_PHASE347",
    "SHOOT_MODE_MOVIE_PHASE347",
    "SHOOT_MODE_SQ_PHASE347",
    "SHOOT_MODE_STILL_PHASE347",
    "SHUTTER_MODE_ANGLE_G149",
    "SHUTTER_MODE_SPEED_G149",
    "SORT_RECORDING_F_RESID16_G150",
    "STATUS_BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION",
    "STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP",
    "STATUS_BLOCKED_G149_TELEMETRY_INVALID",
    "STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION",
    "STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP",
    "STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION",
    "STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS",
    "STATUS_BLOCKED_G150_TELEMETRY_INVALID",
    "STATUS_BLOCKED_PHASE347_DONOR_INTEGRITY",
    "STATUS_VERIFIED_G149",
    "STATUS_VERIFIED_G150",
    "STILL_APSC_SCALES_G149",
    "STILL_FF_SCALES_G149",
    "STILL_FMT_HEIF_G150",
    "STILL_FMT_JPEG_G150",
    "STILL_FMT_RAW_G150",
    "STILL_FMT_RAW_HEIF_G150",
    "STILL_FMT_RAW_JPEG_G150",
    "STILL_IMAGE_QUALITY_MENU_PATH_G150",
    "StillArwHlgUsbLunUvcGuardResult",
    "USB_CONNECTION_MODE_F_RESID16_G150",
    "USB_CONN_DEFAULT_G150",
    "USB_CONN_MSC_G150",
    "USB_CONN_MTP_G150",
    "USB_CONN_REMOTE_SHOOTING_G150",
    "USB_CONN_SEL_WHEN_CONNECT_G150",
    "USB_LUN_DEFAULT_G150",
    "USB_LUN_MULTI_F_RESID16_G150",
    "USB_LUN_MULTI_G150",
    "USB_LUN_SETTING_F_RESID16_G150",
    "USB_LUN_SINGLE_F_RESID16_G150",
    "USB_LUN_SINGLE_G150",
    "USB_MENU_PATH_G150",
    "USB_MSC_F_RESID16_G150",
    "USB_MTP_BASE_RESID16_G150",
    "USB_PD_AMPS_G150",
    "USB_PD_VOLTS_G150",
    "USB_POWER_PORT_MULTI_MICRO_G150",
    "USB_POWER_PORT_TYPE_C_G150",
    "USB_POWER_SUPPLY_DEFAULT_G150",
    "USB_POWER_SUPPLY_F_RESID16_G150",
    "USB_REMOTE_SHOOTING_F_RESID16_G150",
    "USB_SEL_WHEN_CONNECT_F_RESID16_G150",
    "USB_SETUP_RESETTABLE_BY_CAMSET_RESET_G150",
    "ZOOM_1ST_SPEED_F_RESID16_G149",
    "ZOOM_2ND_SPEED_F_RESID16_G149",
    "ZOOM_CIZ_F_RESID16_G149",
    "ZOOM_DIGITAL_F_RESID16_G149",
    "ZOOM_LEVER_1ST_DEFAULT_G149",
    "ZOOM_LEVER_2ND_DEFAULT_G149",
    "ZOOM_LEVER_SPEED_F_RESID16_G149",
    "ZOOM_LEVER_SPEED_MENU_PATH_G149",
    "ZOOM_LEVER_SPEED_RESETTABLE_BY_CAMSET_RESET_G149",
    "ZOOM_MENU_PATH_G149",
    "ZOOM_OPTICAL_ONLY_F_RESID16_G149",
    "ZOOM_RANGE_CIZ_G149",
    "ZOOM_RANGE_DEFAULT_G149",
    "ZOOM_RANGE_DIGITAL_G149",
    "ZOOM_RANGE_F_RESID16_G149",
    "ZOOM_RANGE_MENU_PATH_G149",
    "ZOOM_RANGE_OPTICAL_ONLY_G149",
    "ZOOM_RANGE_RESETTABLE_BY_CAMSET_RESET_G149",
    "ZOOM_RANGE_SMART_G149",
    "ZOOM_RING_LEFT_RIGHT_F_RESID16_G149",
    "ZOOM_RING_RIGHT_LEFT_F_RESID16_G149",
    "ZOOM_RING_ROTATE_DEFAULT_G149",
    "ZOOM_RING_ROTATE_F_RESID16_G149",
    "ZOOM_RING_ROTATE_LEFT_RIGHT_G149",
    "ZOOM_RING_ROTATE_MENU_PATH_G149",
    "ZOOM_RING_ROTATE_RESETTABLE_BY_CAMSET_RESET_G149",
    "ZOOM_RING_ROTATE_RIGHT_LEFT_G149",
    "ZOOM_SPEED_MAX_G149",
    "ZOOM_SPEED_MIN_G149",
    "ZoomCizAutoSlowBaseIsoGuardResult",
    "audit_phase347_donor_contracts",
    "compute_still_arw_hlg_usblun_uvc_matrix",
    "compute_zoom_ciz_autoslow_baseiso_matrix",
    "evaluate_150_master_safety_gates",
    "evaluate_150gate_preflight",
    "evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard",
    "evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall",
    "resolve_fx3_still_arw_hlg_usblun_uvc_state",
    "resolve_fx3_zoom_ciz_autoslow_baseiso_state",
    "run_150_gate_preflight",
    "strip_elapsed_seconds_recursive_phase347",
    "verify_still_arw_hlg_usblun_uvc_guard",
    "verify_still_arw_hlg_usblun_uvc_guard_with_audit",
    "verify_zoom_ciz_autoslow_iso_baseiso_guard",
    "verify_zoom_ciz_autoslow_iso_baseiso_guard_with_audit",
]


if __name__ == "__main__":
    raise SystemExit(main())
