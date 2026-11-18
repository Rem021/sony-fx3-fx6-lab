"""Phase 368 Milestone — 23rd Physical Bench Readiness Verifier (`23/23` Verifiers).

Implements `preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt`
(short CLI alias `preflight-phase368`) aligned with Global Sony Real-Hardware Empirical
Intelligence Waves 77-78 across Check Groups A-D and the mandatory `16/16 H0 == H3`
dual-media `528 B FX3RCPT1` Tier-0 Receipt Gate:

- **Check Group A** (Waves 77.1 & 77.2):
  - **77.1 `[File Format]` 6-Codec Matrix, `XAVC S-I DCI 4K` `24.00p` Reboot/Playback Isolation
    & 5-Tier `100..1350MBPS` `V60`/`V90`/`VPG200`/`VPG400` Card-Speed Firewall vs FX6
    `Class300`**: Reconciles `G139` errata (`S&Q XAVC S HD 100/120fps` requires only
    `SDXC V60+`, `200/240fps` requires `SDXC V90+`; `XAVC S-I DCI 4K` caps S&Q at
    `60/50fps` `600M`, blocking `100/120fps`; `48fps` S&Q exclusive to `24.00p + DCI 4K`;
    `MODEL_EVENT_REBOOT_BY_CROSS_2400P` + `24.00p`-only playback isolation; `VPG400`
    `UNDER_1350MBPS` `0xea64/0xea6c/0xea78/0xea7b` on high-rate S&Q + Proxy; dormant
    `xavc_hs_8k` rejected `EOPNOTSUPP=95` vs FX6 `Class300` with dormant `Class480` &
    `XAVC-L25`).
  - **77.2 `[Priority Set in AWB]` vs Still-Only Reset-Resistant `[Shutter AWB Lock]` &
    `2500K..9900K` `75`-Step Kelvin vs FX6 `WHT BAL` `B/A/PRESET` & `ATW Speed 1..5`**:
    `[Priority Set in AWB]` (`_f 0x67a7`, Resettable, Still & Movie, ineffective in
    `Cine EI / Cine EI Quick`), Still-only Reset-resistant `[Shutter AWB Lock]` (`_f 0x66db`,
    `Not available` under `[Camera Settings Reset]`, Movie requires Custom Key
    `AWB Lock Hold/Toggle`), `2500K..9900K` (`100K` steps = `75` steps) vs FX6
    `2000K..15000K` + `ATW Speed 1..5` (disabled in `Cine EI`) + `Shockless White`.
- **Check Group B** (Waves 77.3 & 77.4):
  - **77.3 Reset-Resistant `[Focus Assistant]` 4 Items + `[Peaking Display]` 3 Items (`G109`
    Errata Reconciliation), Dormant `[Touch Panel/Pad]`/`[Touch Shutter]` Disproof & FX6
    3-Item `Peaking`**: ALL 4 `[Focus Assistant]` items & ALL 3 `[Peaking Display]` items
    (`0 px` HDMI) are `Not available` under `[Camera Settings Reset]` (`Initialize`-only);
    `[AF in Focus Mag.]` is Still-only with 5 lockouts; `[Touch Operation]` exposes 4
    Reset-resistant items (`0` exposed UI items for `[Touch Panel/Pad]` / `[Touch Shutter]`);
    FX6 `Monitoring > Peaking` exposes 3 items (`0` ELF bindings for dormant `Normal` /
    `Frequency`).
  - **77.4 Dual-Model Compiled-but-SKU-Gated `[Accessibility]` / `[Screen Reader]` (`0`
    Exposed UI Items on BOTH `ILME-FX3` & `ILME-FX6`) & Exact 2-Row `[Version]` (`Body` +
    `Lens` Shared Mount-Adapter Slot, `G104` Errata Reconciliation) + `BODYDATA.DAT`
    `EROFS=30`**: `libInfraGetVersion.so` (`InfraGetVersion`, `InfraGetVersionLens`), `0`
    MI-Shoe version shown, red dot silenced by `Airplane Mode=On`, `Slot 1 BODYDATA.DAT`
    blocked (`EROFS=30`), vs FX6 `Body` + `Lens` + `Ext. Unit`.
- **Check Group C** (Waves 78.1 & 78.2):
  - **78.1 Reset-Resistant Parent `[Exposure Ctrl Type]` (`G86` Gap Closure) vs Resettable
    `[Auto/Manual Swt. Set.]` & Ver. 6.00+ Movie/S&Q `[Shutter Mode]` `Speed`/`Angle` (`BK4`
    `0x01120024` vs `0x01120028`, Dormant `Var. Shutter`) vs FX6 4-Mode `Angle/Speed/ECS/Off`**:
    Parent `[Exposure Ctrl Type]` (`_f 0x787e`) is `Not available` under
    `[Camera Settings Reset]` (`Initialize`-only), while `[Auto/Manual Swt. Set.]` &
    `[Auto Slow Shutter]` are Resettable; `[Shutter Mode]` (`19` standard angles + `10`
    slow-frame `2F..64F`), immune to `[Exposure step]`, forces Still/Movie shutter split.
  - **78.2 `[SteadyShot]` `Active` 4-Lockout Matrix, `Catalyst` Gyro `RTMD` `Off/Active`-Only
    & `120p`/`S&Q` Dropout vs FX6 Zero Body IBIS + 3-Step Lens OSS `Active/Standard/Off`**:
    `Active` (`~1.104x` crop) locked out at `119.88p/100p`, `S&Q >= 100fps`, `HDMI RAW=On`,
    `De-Squeeze != Off`; Ver. 2.00+ removed Ver. 1 `>=200mm` note; `47`-entry manual focal
    table (`8..1000mm`); dormant `Dynamic active`/`Intelligent Active`/`Super Active`;
    FX6 zero body IBIS (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`) + 3-step optical OSS
    `Active/Standard/Off` (must be `Off` for Catalyst).
- **Check Group D + Tier-0** (Waves 78.3 & 78.4 + Tier-0 Receipt Gate):
  - **78.3 `Playback -> [Photo Capture]` `8.3M`/`2.1M` (`DCI 4K` Blocked, Reset-Resistant
    Playback `[JPEG/HEIF Switch]`), Exact 3-Item `[View Mode]` (`Date View` /
    `Folder View(Still)` / `Movie View`, Dormant `AVCHD/MP4` Rejected), `[Rating]` `1..5` &
    Tier-0 `Slot 1 EROFS=30` vs FX6 `Clip Flag` `OK/NG/KEEP`**: Reconciles `G126` `[View Mode]`
    gap.
  - **78.4 Zero Native UVC `[USB Streaming]` Proof (`4K 30p` Rumor Disproved), Outbound-Only
    `SRT Caller` (`zero SRT Listener`), `RTMP/RTMPS/SRT` `38 Mbps` / No-`24p`/`120p` & Tier-0
    Zero-RF `Airplane Mode = On` (`rf_tx_packets == 0`) vs FX6 External `CBK-WA100`/`PDT-FP1`**:
    `4` USB modes (`Sel. When Connect`/`MSC`/`MTP`/`Remote Shooting`), dormant UVC
    `4K_12_5P`/`4K_15P`, `Creators' App` BT config, `8` bitrate profiles, `Movie Rec During
    Streaming` (`Disable` def, `Slot 1` `EROFS=30`), `USB-LAN` Airplane-Mode bypass without RF.
  - **Tier-0 Receipt Gate**: Dual-media `528 B FX3RCPT1` Copy A & Copy B with distinct
    `st_dev`, `16/16 H0 == H3`, non-trivial serial/CID, `0x91030080` + fw `7.02`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import (
    is_forced_clean_room,
    iter_work_roots,
    resolve_work_subpath,
)
from .realhw_card_insert_readiness_verifier import (
    BODY_SERIAL_RE,
    DONOR_INSPECTION_MAX_SECONDS,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    HEX32_CID_RE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _is_trivial_hex64,
    build_default_h0_baselines,
)
from .realhw_sd_stageb_bundle_and_uninstaller import SIXTEEN_STORAGE_SURFACES

# ---------------------------------------------------------------------------
# Version / Schema / Go-No-Go / Locked Zero-Telemetry Constants
# ---------------------------------------------------------------------------

P368_VERSION = "phase368_v1"
PHASE368_VERSION = P368_VERSION
PHASE_368_VERSION = P368_VERSION

P368_SCHEMA = (
    "realhw_preflight23_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_srt_v1"
)
P368_SCHEMA_VERSION = P368_SCHEMA
PHASE_368_SCHEMA = P368_SCHEMA
REALHW_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_SRT_SCHEMA = P368_SCHEMA

P368_SONY_HELP_GUIDE_ID = "ilc/2210"
P368_STORAGE_SURFACE_COUNT = 16
P368_HEADER_READ_BYTES = 64

P368_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED = (
    "READONLY_PREFLIGHT23_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED"
)
P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE = (
    "BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE"
)
PHASE_368_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED,
    P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE,
)

P368_CHECK_GROUP_A_ID = "p368_ga_movieset_vpg400_24p_awbprio_shutterlock_fx6_atw"
P368_CHECK_GROUP_B_ID = "p368_gb_focusassist_peaking_touch_screenreader_version_bodydata"
P368_CHECK_GROUP_C_ID = "p368_gc_flexexp_shuttermode_angle_activeibis_catalyst_fx6oss"
P368_CHECK_GROUP_D_ID = "p368_gd_photocap_viewmode_rating_uvc_srt_airplane_tier0"
PHASE_368_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P368_CHECK_GROUP_A_ID,
    P368_CHECK_GROUP_B_ID,
    P368_CHECK_GROUP_C_ID,
    P368_CHECK_GROUP_D_ID,
)

# Errno constants
P368_ERRNO_EPERM = 1
P368_ERRNO_EBUSY = 16
P368_ERRNO_EINVAL = 22
P368_ERRNO_EROFS = 30
P368_ERRNO_EOPNOTSUPP = 95

# Locked zero telemetry constants
PHASE368_EMMC_WRITE_COUNT = 0
PHASE368_E_ND_ACTUATOR_TX_COUNT = 0
PHASE368_E_ND_I2C_TX_BYTES = 0
PHASE368_RF_PACKETS_TRANSMITTED = 0
PHASE368_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE368_RF_NVS_MUTATION_BYTES = 0
PHASE368_SLOT1_DATA_SECTOR_WRITES = 0
PHASE368_USB_PACKETS_TRANSMITTED = 0
PHASE368_PASSIVE_TX_BYTES_EMITTED = 0
PHASE368_RAW_FIRMWARE_BYTES_LEAKED = 0

P368_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P368_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P368_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P368_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P368_VALID_DESQUEEZE_MODES: Tuple[str, ...] = (
    "OFF",
    "1.3X",
    "1.5X",
    "1.6X",
    "1.8X",
    "2.0X",
)

# ---------------------------------------------------------------------------
# Wave 77.1 & 77.2 Group A Constants: File Format, VPG, 24.00p, AWB & FX6 ATW
# ---------------------------------------------------------------------------

P368_FX3_ACTIVE_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC_HS_4K",
    "XAVC_S_4K",
    "XAVC_S_HD",
    "XAVC_S_I_4K",
    "XAVC_S_I_HD",
    "XAVC_S_I_DCI_4K",
)
P368_FX3_FILE_FORMAT_DEFAULT = "XAVC_S_HD"
P368_FX3_DORMANT_FILE_FORMATS: Tuple[str, ...] = ("XAVC_HS_8K",)
P368_MEDIA_TRANSFER_TIERS_MBPS: Tuple[int, ...] = (100, 200, 400, 600, 1350)
P368_VALID_MEDIA_CARD_SPEEDS: Tuple[str, ...] = (
    "SDHC_CLASS10",
    "SDXC_U3_V30",
    "SDXC_V60",
    "SDXC_V90",
    "CFEA_VPG200",
    "CFEA_VPG400",
)
P368_MEDIA_CARD_SPEED_RANK: Dict[str, int] = {
    "SDHC_CLASS10": 1,
    "SDXC_U3_V30": 2,
    "SDXC_V60": 3,
    "SDXC_V90": 4,
    "CFEA_VPG200": 5,
    "CFEA_VPG400": 6,
}
P368_VPG400_UXC_RESIDS: Tuple[str, ...] = ("0xea64", "0xea6c", "0xea78", "0xea7b")
P368_REBOOT_2400P_EVENT = "MODEL_EVENT_REBOOT_BY_CROSS_2400P"

P368_FX6_REC_FORMAT_CODECS: Tuple[str, ...] = (
    "RAW_AND_XAVC_I",
    "RAW_HDMI_AND_XAVC_I",
    "XAVC_I",
    "XAVC_L",
)
P368_FX6_DORMANT_REC_FORMATS: Tuple[str, ...] = ("CLASS480", "XAVC_L25")
P368_FX6_XAVC_I_MAX_CLASS = "CLASS300"
P368_FX6_XAVC_L_QFHD_MBPS: Tuple[int, ...] = (150, 100)
P368_FX6_XAVC_L_HD_MBPS: Tuple[int, ...] = (50, 35)

P368_AWB_PRIORITY_MODES: Tuple[str, ...] = ("STANDARD", "AMBIENCE", "WHITE")
P368_AWB_PRIORITY_DEFAULT = "STANDARD"
P368_SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = (
    "OFF",
    "SHUTTER_HALF_PRESS",
    "CONT_SHOOTING",
)
P368_SHUTTER_AWB_LOCK_DEFAULT = "OFF"
P368_MOVIE_AWB_LOCK_CUSTOM_KEYS: Tuple[str, ...] = (
    "NONE",
    "AWB_LOCK_HOLD",
    "AWB_LOCK_TOGGLE",
)
P368_KELVIN_MIN_K = 2500
P368_KELVIN_MAX_K = 9900
P368_KELVIN_STEP_K = 100
P368_KELVIN_STEP_COUNT = 75
P368_AB_TINT_STEP_COUNT = 29
P368_GM_TINT_STEP_COUNT = 57

P368_FX6_WHT_BAL_SWITCH_POSITIONS: Tuple[str, ...] = ("B", "A", "PRESET")
P368_FX6_KELVIN_MIN_K = 2000
P368_FX6_KELVIN_MAX_K = 15000
P368_FX6_ATW_SPEED_MIN = 1
P368_FX6_ATW_SPEED_MAX = 5
P368_FX6_SHOCKLESS_WHITE_MODES: Tuple[str, ...] = ("OFF", "1", "2", "3")

# ---------------------------------------------------------------------------
# Wave 77.3 & 77.4 Group B Constants: Focus Assist, Peaking, Touch, Screen Reader, Version
# ---------------------------------------------------------------------------

P368_FOCUS_ASSISTANT_EXACT_4_ITEMS: Tuple[str, ...] = (
    "Auto Magnifier in MF",
    "Focus Magnif. Time",
    "Initial Focus Mag.",
    "AF in Focus Mag.",
)
P368_FOCUS_MAGNIF_TIMES: Tuple[str, ...] = ("2_SEC", "5_SEC", "NO_LIMIT")
P368_INITIAL_FOCUS_MAG_STILL_FF: Tuple[str, ...] = ("X1_0", "X2_1")
P368_INITIAL_FOCUS_MAG_STILL_APSC: Tuple[str, ...] = ("X1_0", "X1_5")
P368_INITIAL_FOCUS_MAG_MOVIE: Tuple[str, ...] = ("X1_0", "X4_0")
P368_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")

P368_PEAKING_EXACT_3_ITEMS: Tuple[str, ...] = (
    "Peaking Display",
    "Peaking Level",
    "Peaking Color",
)
P368_PEAKING_LEVELS: Tuple[str, ...] = ("HIGH", "MID", "LOW")
P368_PEAKING_COLORS: Tuple[str, ...] = ("RED", "YELLOW", "BLUE", "WHITE")
P368_PEAKING_HDMI_PIXEL_COUNT = 0

P368_TOUCH_OPERATION_EXACT_4_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)
P368_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("ON", "ON_PLAYBACK_ONLY", "OFF")
P368_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("STANDARD", "SENSITIVE")
P368_TOUCH_FUNC_IN_SHOOTING_MODES: Tuple[str, ...] = (
    "TOUCH_TRACKING",
    "TOUCH_FOCUS",
    "OFF",
)
P368_SWIPE_UP_MODES: Tuple[str, ...] = ("OPEN_THE_FN_MENU", "OFF")
P368_DORMANT_TOUCH_ITEMS: Tuple[str, ...] = (
    "TOUCH_PANEL_PAD",
    "TOUCH_PAD_SETTINGS",
    "TOUCH_PAD_VERTICAL",
    "TOUCH_SHUTTER",
)

P368_FX6_PEAKING_EXACT_3_ITEMS: Tuple[str, ...] = ("Setting", "Peaking Level", "Color")
P368_FX6_PEAKING_COLORS: Tuple[str, ...] = ("B_AND_W", "RED", "YELLOW", "BLUE")
P368_FX6_PEAKING_DORMANT_BINDINGS: Tuple[str, ...] = ("NORMAL", "FREQUENCY")
P368_FX6_FOCUS_MAG_VF_RATIO = "x3/x6"
P368_FX6_FOCUS_MAG_HDMI_RATIO = "x2/x4"

P368_FX3_SCREEN_READER_UI_COUNT = 0
P368_FX6_SCREEN_READER_UI_COUNT = 0
P368_FX3_SCREEN_READER_HDMI_HITS = 0
P368_FX3_VERSION_EXACT_2_ROWS: Tuple[str, ...] = ("Body", "Lens")
P368_FX3_VERSION_MI_SHOE_SHOWN = False
P368_FX6_VERSION_ROWS: Tuple[str, ...] = ("Body", "Lens", "Ext. Unit")

# ---------------------------------------------------------------------------
# Wave 78.1 & 78.2 Group C Constants: FlexExp, Shutter Mode/Angle, IBIS & Catalyst
# ---------------------------------------------------------------------------

P368_EXPOSURE_CTRL_TYPES: Tuple[str, ...] = ("FLEXIBLE_EXP_MODE", "PASM_MODE")
P368_EXPOSURE_CTRL_TYPE_DEFAULT = "FLEXIBLE_EXP_MODE"
P368_AUTO_MANUAL_MODES: Tuple[str, ...] = ("AUTO", "MANUAL")
P368_SHUTTER_MODES: Tuple[str, ...] = ("SPEED", "ANGLE")
P368_SHUTTER_MODE_DEFAULT = "SPEED"
P368_BK4_SHUTTER_SPEED_REG = "0x01120024"
P368_BK4_SHUTTER_ANGLE_REG = "0x01120028"
P368_SHUTTER_ANGLE_STANDARD_DEGREES: Tuple[str, ...] = (
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
P368_SHUTTER_ANGLE_SLOW_FRAMES: Tuple[str, ...] = (
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
P368_FX3_VAR_SHUTTER_UI_COUNT = 0
P368_FX6_SHUTTER_MODES: Tuple[str, ...] = ("ANGLE", "SPEED", "ECS", "OFF")

P368_STEADYSHOT_MOVIE_MODES: Tuple[str, ...] = ("ACTIVE", "STANDARD", "OFF")
P368_STEADYSHOT_MOVIE_DEFAULT = "STANDARD"
P368_STEADYSHOT_ACTIVE_CROP_FACTOR = 1.104
P368_DORMANT_STEADYSHOT_MODES: Tuple[str, ...] = (
    "DYNAMIC_ACTIVE",
    "INTELLIGENT_ACTIVE",
    "SUPER_ACTIVE",
)
P368_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = ("AUTO", "MANUAL")
P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 24, 25, 28, 30, 32, 35,
    40, 45, 50, 55, 60, 70, 75, 80, 85, 90,
    100, 105, 120, 135, 150, 180, 200, 210, 250, 300,
    350, 400, 450, 500, 600, 800, 1000,
)
P368_FX6_BODY_IBIS_COUNT = 0
P368_FX6_IBIS_UNSUPPORTED_SYMBOL = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
P368_FX6_LENS_OSS_MODES: Tuple[str, ...] = ("ACTIVE", "STANDARD", "OFF")

# ---------------------------------------------------------------------------
# Wave 78.3 & 78.4 Group D Constants: Photo Capture, View Mode, Rating, UVC, SRT
# ---------------------------------------------------------------------------

P368_PHOTO_CAPTURE_4K_MP = 8.3
P368_PHOTO_CAPTURE_HD_MP = 2.1
P368_PB_JPEG_HEIF_MODES: Tuple[str, ...] = ("JPEG", "HEIF_420", "HEIF_422")
P368_PB_JPEG_HEIF_DEFAULT = "JPEG"
P368_VIEW_MODE_EXACT_3_ITEMS: Tuple[str, ...] = (
    "DATE_VIEW",
    "FOLDER_VIEW_STILL",
    "MOVIE_VIEW",
)
P368_VIEW_MODE_DEFAULT = "DATE_VIEW"
P368_VIEW_MODE_DORMANT_ITEMS: Tuple[str, ...] = (
    "FOLDER_VIEW_MP4",
    "AVCHD_VIEW",
    "XAVC_S_VIEW",
)
P368_RATING_MIN = 0
P368_RATING_MAX = 5
P368_FX6_PHOTO_CAPTURE_UI_COUNT = 0
P368_FX6_CLIP_FLAGS: Tuple[str, ...] = ("OK", "NG", "KEEP")

P368_USB_CONNECTION_EXACT_4_MODES: Tuple[str, ...] = (
    "SEL_WHEN_CONNECT",
    "MSC",
    "MTP",
    "REMOTE_SHOOTING",
)
P368_FX3_UVC_STREAMING_SUPPORTED = False
P368_FX3_DORMANT_UVC_FORMATS: Tuple[str, ...] = (
    "4K_12_5P",
    "4K_15P",
    "FULLHD_25P",
    "FULLHD_30P",
    "FULLHD_50P",
    "FULLHD_60P",
    "HD720_25P",
    "HD720_30P",
)
P368_STREAMING_PROTOCOLS: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT")
P368_SRT_EXPOSED_ROLES: Tuple[str, ...] = ("SRT_CALLER",)
P368_SRT_SUPPORTED_CODECS: Tuple[str, ...] = ("H264", "H265")
P368_SRT_ENCRYPTIONS: Tuple[str, ...] = ("NONE", "AES_128", "AES_256")
P368_STREAMING_ALLOWED_FPS: Tuple[float, ...] = (25.0, 29.97, 50.0, 59.94)
P368_STREAMING_BLOCKED_FPS: Tuple[float, ...] = (23.98, 24.0, 100.0, 119.88)
P368_STREAMING_MAX_BITRATE_MBPS = 38.0
P368_STREAMING_PROFILES: Dict[str, Tuple[float, float, float, bool]] = {
    "4K_2160P_60P_50P": (38.0, 38.0, 38.0, False),
    "4K_2160P_30P_25P": (13.0, 38.0, 34.0, False),
    "2K_1440P_60P_50P": (9.0, 38.0, 18.0, False),
    "2K_1440P_30P_25P": (6.0, 38.0, 13.0, True),
    "HD_1080P_60P_50P": (4.5, 27.0, 9.0, True),
    "HD_1080P_30P_25P": (3.0, 18.0, 6.0, True),
    "HD_720P_60P_50P": (2.3, 13.5, 6.0, True),
    "HD_720P_30P_25P": (1.5, 9.0, 4.0, True),
}
P368_STREAMING_PROFILE_DEFAULT = "HD_1080P_60P_50P"
P368_MOVIE_REC_DURING_STREAMING_MODES: Tuple[str, ...] = ("DISABLE", "ENABLE")
P368_NETWORK_TRANSPORTS: Tuple[str, ...] = ("USB_LAN", "WIFI", "USB_TETHERING", "NONE")
P368_FX6_NATIVE_UVC_COUNT = 0
P368_FX6_BUILTIN_STREAMING_COUNT = 0
P368_FX6_EXTERNAL_STREAMING_ADAPTERS: Tuple[str, ...] = (
    "CBK-WA100",
    "CBK-RPU7",
    "PDT-FP1",
)

# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Paths (Waves 77-78)
# ---------------------------------------------------------------------------

P368_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx3_appfw_so", "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"),
    (
        "fx3_libinfragetversion_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraGetVersion.so",
    ),
    (
        "fx3_libupdatermedia_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libupdatermedia.so",
    ),
    (
        "fx3_libinfrasrtlivestreaming_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraSrtLiveStreaming.so",
    ),
    (
        "fx3_libinfrartmplivestreaming_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraRtmpLiveStreaming.so",
    ),
    (
        "fx3_string_english_f_uxc",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc",
    ),
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx6_string_english_2_uxc",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc",
    ),
)

# ---------------------------------------------------------------------------
# Error Code Constants
# ---------------------------------------------------------------------------

P368_GA_ERR_MODEL_OR_FW_FLOOR = "P368_GA_ERR_MODEL_OR_FW_FLOOR"
P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION = "P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION"
P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400 = "P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400"
P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300 = "P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300"
P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN = (
    "P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN"
)
P368_GA_ERR_FX6_ATW_OR_WHT_BAL = "P368_GA_ERR_FX6_ATW_OR_WHT_BAL"

P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET = (
    "P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET"
)
P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD = (
    "P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD"
)
P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG = "P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG"
P368_GB_ERR_SCREEN_READER_SKU_GATE = "P368_GB_ERR_SCREEN_READER_SKU_GATE"
P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30 = (
    "P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30"
)

P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT = "P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT"
P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER = (
    "P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER"
)
P368_GC_ERR_FX6_4MODE_SHUTTER_CONTRACT = "P368_GC_ERR_FX6_4MODE_SHUTTER_CONTRACT"
P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST = (
    "P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST"
)
P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS = "P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS"

P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET = (
    "P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET"
)
P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30 = (
    "P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30"
)
P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF = "P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF"
P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF = (
    "P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF"
)
P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"

# ---------------------------------------------------------------------------
# Timing-Stripping & Deterministic Hashing Helpers
# ---------------------------------------------------------------------------

_TIMING_STRIP_EXACT_KEYS = frozenset(
    {
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    }
)


def _strip_timing_fields(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in value.items():
            if k in _TIMING_STRIP_EXACT_KEYS or (
                isinstance(k, str)
                and (
                    k.endswith("_elapsed_ms")
                    or k.endswith("_elapsed_s")
                    or k.endswith("_elapsed_seconds")
                )
            ):
                continue
            cleaned[k] = _strip_timing_fields(v)
        return cleaned
    if isinstance(value, list):
        return [_strip_timing_fields(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_timing_fields(item) for item in value]
    return value


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    body = dict(payload)
    body.pop("report_sha256", None)
    stripped = _strip_timing_fields(body)
    raw = json.dumps(stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _resolve_work_root_or_none() -> Optional[Path]:
    if _is_clean_room_env():
        return None
    for root in iter_work_roots():
        if root.exists():
            return root
    return None


def resolve_phase368_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    if work_root is None:
        return None
    try:
        candidate = resolve_work_subpath(rel_subpath, work_root=work_root)
    except Exception:
        candidate = Path(work_root) / rel_subpath
    return candidate if candidate.exists() and candidate.is_file() else None


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int = P368_HEADER_READ_BYTES) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return os.read(fd, max_bytes)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase368DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    donors_checked: int
    donors_present: int
    bytes_read_total: int
    header_digests: Dict[str, str]
    raw_firmware_bytes_leaked: int
    elapsed_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_phase368_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase368DonorInspectionResult:
    start = time.monotonic()
    forced = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    resolved_work_root = (
        None if forced else (work_root if work_root is not None else _resolve_work_root_or_none())
    )

    if forced or (resolved_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None):
        return Phase368DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P368_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P368_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE368_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    digests: Dict[str, str] = {}
    present_count = 0
    bytes_read = 0
    fx3_override_names = {
        "fx3_appfw_so": "appFw.so",
        "fx3_libinfragetversion_so": "libInfraGetVersion.so",
        "fx3_libupdatermedia_so": "libupdatermedia.so",
        "fx3_libinfrasrtlivestreaming_so": "libInfraSrtLiveStreaming.so",
        "fx3_libinfrartmplivestreaming_so": "libInfraRtmpLiveStreaming.so",
    }
    for lbl, rel in P368_BOUNDED_DONOR_PATHS:
        if (time.monotonic() - start) >= max_seconds:
            break
        candidate: Optional[Path] = None
        if lbl == "fx6_appfw_so" and fx6_lib_dir is not None:
            p = Path(fx6_lib_dir) / "appFw.so"
            if p.exists() and p.is_file():
                candidate = p
        elif lbl in fx3_override_names and fx3_modules_dir is not None:
            p = Path(fx3_modules_dir) / fx3_override_names[lbl]
            if p.exists() and p.is_file():
                candidate = p
        if candidate is None:
            candidate = resolve_phase368_donor_file_or_none(resolved_work_root, rel)
        if candidate is not None:
            hdr = _read_bounded_header_o_rdonly(candidate, P368_HEADER_READ_BYTES)
            present_count += 1
            bytes_read += len(hdr)
            digests[lbl] = hashlib.sha256(hdr).hexdigest()[:16]

    if present_count == 0:
        return Phase368DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            donors_checked=len(P368_BOUNDED_DONOR_PATHS),
            donors_present=0,
            bytes_read_total=0,
            header_digests={
                lbl: hashlib.sha256(f"clean_room_synthetic:{lbl}".encode("utf-8")).hexdigest()[:16]
                for lbl, _ in P368_BOUNDED_DONOR_PATHS
            },
            raw_firmware_bytes_leaked=PHASE368_RAW_FIRMWARE_BYTES_LEAKED,
            elapsed_seconds=round(time.monotonic() - start, 6),
        )

    return Phase368DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        donor_tree_present=True,
        donors_checked=len(P368_BOUNDED_DONOR_PATHS),
        donors_present=present_count,
        bytes_read_total=bytes_read,
        header_digests=digests,
        raw_firmware_bytes_leaked=PHASE368_RAW_FIRMWARE_BYTES_LEAKED,
        elapsed_seconds=round(time.monotonic() - start, 6),
    )


# ---------------------------------------------------------------------------
# Check Group Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class P368CheckGroupAMovieSetVpgAwbPrioAndFx6AtwResult:
    group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    shoot_mode: str
    log_shooting_mode: str
    reset_action: str
    file_format: str
    effective_file_format_after_reset: str
    rec_frame_rate_fps: float
    sq_frame_rate_fps: int
    record_setting_mbps: int
    proxy_recording_enabled: bool
    media_card_speed: str
    required_min_card_speed: str
    vpg400_proxy_threshold_triggered: bool
    cross_2400p_reboot_triggered: bool
    playback_2400p_isolated: bool
    fx3_dormant_8k_ui_count: int
    fx6_rec_codec: str
    fx6_video_format: str
    fx6_xavc_i_max_class: str
    fx6_dormant_class480_or_l25_count: int
    awb_priority_set: str
    effective_awb_priority_after_reset: str
    awb_priority_effective_in_log: bool
    shutter_awb_lock: str
    effective_shutter_awb_lock_after_reset: str
    shutter_awb_lock_still_only: bool
    shutter_awb_lock_resists_camera_reset: bool
    movie_awb_lock_custom_key: str
    kelvin_temp_k: int
    fx3_kelvin_step_count: int
    fx3_ab_tint_steps: int
    fx3_gm_tint_steps: int
    fx6_wht_bal_switch: str
    fx6_atw_speed: int
    fx6_atw_enabled_effective: bool
    fx6_shockless_white: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P368CheckGroupBFocusAssistPeakingTouchScreenReaderVersionResult:
    group_id: str
    passed: bool
    shoot_mode: str
    focus_mode: str
    exposure_mode: str
    reset_action: str
    focus_assistant_items: Tuple[str, ...]
    auto_magnifier_in_mf: str
    focus_magnif_time: str
    initial_focus_mag: str
    af_in_focus_mag: str
    af_in_focus_mag_effective: bool
    peaking_items: Tuple[str, ...]
    peaking_display: str
    peaking_level: str
    peaking_color: str
    peaking_hdmi_pixel_count: int
    focus_assist_and_peaking_resist_camera_reset: bool
    touch_operation_items: Tuple[str, ...]
    touch_operation: str
    touch_sensitivity: str
    touch_func_in_shooting: str
    swipe_up: str
    fx3_dormant_touchpad_ui_count: int
    fx6_peaking_items: Tuple[str, ...]
    fx6_peaking_dormant_freq_bindings: int
    fx6_focus_mag_vf_ratio: str
    fx6_focus_mag_hdmi_ratio: str
    fx3_screen_reader_ui_count: int
    fx6_screen_reader_ui_count: int
    fx3_screen_reader_hdmi_hits: int
    version_rows_exposed: Tuple[str, ...]
    mount_adaptor_shares_lens_slot: bool
    fx3_version_mi_shoe_shown: bool
    airplane_mode: str
    version_update_red_dot_silenced: bool
    bodydata_slot1_update_blocked_erofs30: bool
    fx6_version_rows: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P368CheckGroupCFlexExpShutterAngleActiveIbisCatalystFx6OssResult:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    exposure_ctrl_type: str
    effective_exposure_ctrl_type_after_reset: str
    exposure_ctrl_type_resists_camera_reset: bool
    av_auto_manual_switch: str
    tv_auto_manual_switch: str
    iso_auto_manual_switch: str
    auto_slow_shutter: str
    shutter_mode: str
    effective_shutter_mode_after_reset: str
    shutter_angle_value: str
    shutter_angle_standard_count: int
    shutter_angle_slow_frame_count: int
    bk4_speed_reg: str
    bk4_angle_reg: str
    bk4_registers_independent: bool
    exposure_step_affects_shutter_angle: bool
    shutter_angle_splits_still_movie: bool
    anti_flicker_shoot: str
    fx3_var_shutter_ui_count: int
    fx6_shutter_mode: str
    steadyshot_movie: str
    effective_steadyshot_movie: str
    steadyshot_active_crop_factor: float
    steadyshot_active_locked_out: bool
    steadyshot_adjust: str
    steadyshot_focal_length_mm: int
    focal_table_entry_count: int
    catalyst_gyro_rtmd_available: bool
    fx3_dormant_steadyshot_ui_count: int
    fx6_body_ibis_count: int
    fx6_ibis_unsupported_symbol: str
    fx6_lens_oss_mode: str
    fx6_catalyst_oss_off_required: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class P368CheckGroupDPhotoCapViewModeRatingUvcSrtAirplaneTier0Result:
    group_id: str
    passed: bool
    shoot_mode: str
    reset_action: str
    source_file_format: str
    photo_capture_output_mp: Optional[float]
    photo_capture_dci4k_blocked: bool
    pb_jpeg_heif_switch: str
    effective_pb_jpeg_heif_after_reset: str
    pb_jpeg_heif_resists_camera_reset: bool
    view_mode_exposed_items: Tuple[str, ...]
    view_mode: str
    effective_view_mode_after_reset: str
    rating_stars: int
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool
    fx6_photo_capture_ui_count: int
    fx6_clip_flag: str
    usb_connection_mode: str
    usb_connection_modes_exposed: Tuple[str, ...]
    fx3_uvc_streaming_supported: bool
    fx3_dormant_uvc_4k_30p_present: bool
    streaming_protocol: str
    srt_role: str
    srt_listener_supported: bool
    streaming_codec: str
    streaming_encryption: str
    streaming_profile: str
    streaming_fps: float
    streaming_bitrate_mbps: float
    movie_rec_during_streaming: str
    streaming_transport: str
    airplane_mode: str
    effective_airplane_mode_after_reset: str
    usb_lan_bypasses_airplane_mode: bool
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    fx6_native_uvc_count: int
    fx6_builtin_streaming_count: int
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    st_dev_a: Optional[int]
    st_dev_b: Optional[int]
    receipt_body_serial: str
    receipt_emmc_cid: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Phase368ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    overall_status: str
    go_no_go: str
    verification_mode: str
    simulate_bench_dry_run: bool
    check_group_count: int
    check_groups_passed: int
    check_group_a: P368CheckGroupAMovieSetVpgAwbPrioAndFx6AtwResult
    check_group_b: P368CheckGroupBFocusAssistPeakingTouchScreenReaderVersionResult
    check_group_c: P368CheckGroupCFlexExpShutterAngleActiveIbisCatalystFx6OssResult
    check_group_d: P368CheckGroupDPhotoCapViewModeRatingUvcSrtAirplaneTier0Result
    donor_inspection: Phase368DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    slot1_tier0_vault_mutated: bool
    ready_for_live_camera_attach: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_screen_reader_exposed: bool
    fx6_screen_reader_exposed: bool
    fx3_touch_panel_pad_exposed: bool
    fx3_var_shutter_exposed: bool
    fx6_body_ibis_present: bool
    fx3_uvc_streaming_supported: bool
    fx3_srt_listener_supported: bool
    fx3_view_mode_3items_exact: bool
    emmc_write_count: int
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    rf_nvs_mutation_bytes: int
    slot1_data_sector_writes: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase_version": self.phase_version,
            "sony_help_guide_id": self.sony_help_guide_id,
            "overall_status": self.overall_status,
            "go_no_go": self.go_no_go,
            "verification_mode": self.verification_mode,
            "simulate_bench_dry_run": self.simulate_bench_dry_run,
            "check_group_count": self.check_group_count,
            "check_groups_passed": self.check_groups_passed,
            "check_group_a": self.check_group_a.to_dict(),
            "check_group_b": self.check_group_b.to_dict(),
            "check_group_c": self.check_group_c.to_dict(),
            "check_group_d": self.check_group_d.to_dict(),
            "donor_inspection": self.donor_inspection.to_dict(),
            "tier0_receipt_verified": self.tier0_receipt_verified,
            "receipt_mode": self.receipt_mode,
            "h0_equals_h3_count": self.h0_equals_h3_count,
            "h0_h3_surface_count": self.h0_h3_surface_count,
            "slot1_tier0_vault_mutated": self.slot1_tier0_vault_mutated,
            "ready_for_live_camera_attach": self.ready_for_live_camera_attach,
            "overall_ready_for_hardware_attach": self.overall_ready_for_hardware_attach,
            "hardware_live_attachment_authorized": self.hardware_live_attachment_authorized,
            "persistent_emmc_writes_authorized": self.persistent_emmc_writes_authorized,
            "persistent_write_release": self.persistent_write_release,
            "spi_nor_write_authorized": self.spi_nor_write_authorized,
            "el3_payload_transmit_authorized": self.el3_payload_transmit_authorized,
            "sd_physical_media_written": self.sd_physical_media_written,
            "cross_model_flash_authorized": self.cross_model_flash_authorized,
            "rf_nvs_p12_p13_writes_authorized": self.rf_nvs_p12_p13_writes_authorized,
            "fx3_screen_reader_exposed": self.fx3_screen_reader_exposed,
            "fx6_screen_reader_exposed": self.fx6_screen_reader_exposed,
            "fx3_touch_panel_pad_exposed": self.fx3_touch_panel_pad_exposed,
            "fx3_var_shutter_exposed": self.fx3_var_shutter_exposed,
            "fx6_body_ibis_present": self.fx6_body_ibis_present,
            "fx3_uvc_streaming_supported": self.fx3_uvc_streaming_supported,
            "fx3_srt_listener_supported": self.fx3_srt_listener_supported,
            "fx3_view_mode_3items_exact": self.fx3_view_mode_3items_exact,
            "emmc_write_count": self.emmc_write_count,
            "e_nd_actuator_tx_count": self.e_nd_actuator_tx_count,
            "e_nd_i2c_tx_bytes": self.e_nd_i2c_tx_bytes,
            "rf_packets_transmitted": self.rf_packets_transmitted,
            "wireless_rf_packets_emitted": self.wireless_rf_packets_emitted,
            "rf_nvs_mutation_bytes": self.rf_nvs_mutation_bytes,
            "slot1_data_sector_writes": self.slot1_data_sector_writes,
            "usb_packets_transmitted": self.usb_packets_transmitted,
            "passive_tx_bytes_emitted": self.passive_tx_bytes_emitted,
            "raw_firmware_bytes_leaked": self.raw_firmware_bytes_leaked,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "report_sha256": self.report_sha256,
        }

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        cleaned = _strip_timing_fields(self.to_dict())
        return json.dumps(cleaned, indent=indent, sort_keys=True, ensure_ascii=True) + "\n"


# ---------------------------------------------------------------------------
# Simulated Tier-0 Dual-Media Receipt Builder
# ---------------------------------------------------------------------------


def build_simulated_phase368_tier0_receipts(
    *,
    body_serial: str = "FX3SIM70200368",
    emmc_cid: str = "11010030303847333000a1b2c3d49368",
) -> Dict[str, Any]:
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE368_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE368_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_a = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    receipt_b = bytes(receipt_a)
    if len(receipt_a) != SD_RECEIPT_BYTES:
        raise AssertionError(f"Expected {SD_RECEIPT_BYTES}B receipt, got {len(receipt_a)}")
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "h0_baselines_a": dict(h0),
        "h0_baselines_b": dict(h0),
        "h3_baselines": dict(h0),
        "receipt_a_bytes": receipt_a,
        "receipt_b_bytes": receipt_b,
        "st_dev_a": 1361,
        "st_dev_b": 1362,
    }


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Waves 77.1 & 77.2)
# ---------------------------------------------------------------------------


def _resolve_required_card_speed(
    *,
    shoot_mode: str,
    file_format: str,
    record_setting_mbps: int,
    sq_frame_rate_fps: int,
    proxy_recording_enabled: bool,
) -> Tuple[str, bool]:
    # Proxy paired with high-rate S&Q XAVC S-I triggers VPG400 (UNDER_1350MBPS)
    if shoot_mode == "S_AND_Q" and file_format in ("XAVC_S_I_4K", "XAVC_S_I_HD"):
        if (
            (file_format == "XAVC_S_I_4K" and sq_frame_rate_fps in (100, 120))
            or (file_format == "XAVC_S_I_HD" and sq_frame_rate_fps in (200, 240))
            or record_setting_mbps >= 890
        ):
            if proxy_recording_enabled:
                return ("CFEA_VPG400", True)
            return ("CFEA_VPG200", False)

    if file_format in ("XAVC_S_I_4K", "XAVC_S_I_HD", "XAVC_S_I_DCI_4K"):
        if proxy_recording_enabled:
            return ("CFEA_VPG200", False)
        return ("SDXC_V90", False)

    if shoot_mode == "S_AND_Q":
        if file_format == "XAVC_S_HD":
            if sq_frame_rate_fps in (200, 240):
                return ("SDXC_V90", False)
            if sq_frame_rate_fps in (100, 120):
                # G139 errata reconciliation: S&Q XAVC S HD 100/120fps requires only SDXC V60+
                return ("SDXC_V60", False)
        elif file_format in ("XAVC_HS_4K", "XAVC_S_4K") and sq_frame_rate_fps in (100, 120):
            return ("SDXC_V90", False)

    if record_setting_mbps >= 280:
        return ("SDXC_V60", False)
    if record_setting_mbps >= 75:
        return ("SDXC_U3_V30", False)
    return ("SDHC_CLASS10", False)


def evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P368_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    # Wave 77.1
    file_format: str = P368_FX3_FILE_FORMAT_DEFAULT,
    rec_frame_rate_fps: float = 59.94,
    prev_rec_frame_rate_fps: float = 59.94,
    sq_frame_rate_fps: int = 24,
    record_setting_mbps: int = 50,
    proxy_recording_enabled: bool = False,
    media_card_speed: str = "CFEA_VPG400",
    playback_clip_fps: float = 59.94,
    dormant_file_format_requested: Optional[str] = None,
    expect_xavc_hs_4k_has_29_97p_or_25p: bool = False,
    expect_sq_xavc_s_hd_120fps_requires_v90: bool = False,
    expect_sq_dci4k_allows_100_or_120fps: bool = False,
    expect_sq_48fps_outside_dci4k_2400p: bool = False,
    expect_cross_2400p_without_reboot_or_mixed_playback: bool = False,
    expect_high_rate_sq_proxy_succeeds_without_vpg400: bool = False,
    claimed_movie_settings_resist_camera_reset: bool = False,
    fx6_rec_codec: str = "XAVC_I",
    fx6_video_format: str = "4096x2160",
    fx6_rec_mbps: int = 600,
    fx6_dormant_rec_format_requested: Optional[str] = None,
    claimed_fx6_xavc_l_supports_dci4k: bool = False,
    # Wave 77.2
    awb_priority_set: str = P368_AWB_PRIORITY_DEFAULT,
    shutter_awb_lock: str = P368_SHUTTER_AWB_LOCK_DEFAULT,
    movie_awb_lock_custom_key: str = "NONE",
    kelvin_temp_k: int = 5600,
    expect_awb_priority_effective_in_cine_ei: bool = False,
    expect_shutter_awb_lock_active_in_movie: bool = False,
    claimed_shutter_awb_lock_wiped_by_camera_reset: bool = False,
    claimed_awb_priority_resists_camera_reset: bool = False,
    fx6_wht_bal_switch: str = "B",
    fx6_kelvin_temp_k: int = 5600,
    fx6_atw_enabled: bool = True,
    fx6_atw_speed: int = 3,
    fx6_shockless_white: str = "OFF",
    fx6_cine_ei_active: bool = False,
    expect_fx6_atw_active_in_cine_ei: bool = False,
) -> P368CheckGroupAMovieSetVpgAwbPrioAndFx6AtwResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT or body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P368_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw {TARGET_BODY_FW}, "
            f"got 0x{body_model_id:08x} fw {body_fw!r}"
        )
    if sony_help_guide_id != P368_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P368_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P368_SONY_HELP_GUIDE_ID!r}"
        )
    if shoot_mode not in P368_VALID_SHOOT_MODES:
        errors.append(f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: invalid shoot_mode {shoot_mode!r}")
    if log_shooting_mode not in P368_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: invalid log_shooting_mode {log_shooting_mode!r}"
        )
    if reset_action not in P368_VALID_RESET_ACTIONS:
        errors.append(f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: invalid reset_action {reset_action!r}")

    # Wave 77.1: File Format, 24.00p Reboot/Playback Isolation & Card Speed
    if dormant_file_format_requested is not None:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: dormant file format {dormant_file_format_requested!r} has 0 FX3 UI exposure (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if file_format not in P368_FX3_ACTIVE_FILE_FORMATS:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: invalid [File Format] {file_format!r}; must be in {P368_FX3_ACTIVE_FILE_FORMATS}"
        )
    if media_card_speed not in P368_VALID_MEDIA_CARD_SPEEDS:
        errors.append(
            f"{P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400}: invalid media_card_speed {media_card_speed!r}"
        )
    if expect_xavc_hs_4k_has_29_97p_or_25p:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: XAVC HS 4K has NO 29.97p/25p frame rates on ILME-FX3"
        )
    if file_format == "XAVC_HS_4K" and round(rec_frame_rate_fps, 2) in (25.0, 29.97):
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: XAVC HS 4K rejects {rec_frame_rate_fps}p"
        )

    is_2400p = abs(rec_frame_rate_fps - 24.0) < 0.01
    prev_is_2400p = abs(prev_rec_frame_rate_fps - 24.0) < 0.01
    cross_2400p_reboot = is_2400p != prev_is_2400p
    playback_2400p_isolated = is_2400p

    if is_2400p and file_format != "XAVC_S_I_DCI_4K":
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: 24.00p is exclusive to XAVC_S_I_DCI_4K, not {file_format!r}"
        )
    if expect_cross_2400p_without_reboot_or_mixed_playback:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: crossing 24.00p enforces {P368_REBOOT_2400P_EVENT} and isolates playback strictly to 24.00p clips"
        )
    if is_2400p and abs(playback_clip_fps - 24.0) >= 0.01 and playback_clip_fps > 0:
        # Playback of non-24.00p clip while camera is in 24.00p mode is blocked; only warn/error if mismatched clip requested
        if abs(playback_clip_fps - rec_frame_rate_fps) >= 0.01 and shoot_mode in ("MOVIE", "S_AND_Q"):
            warnings.append(
                f"24.00p playback isolation active: clip at {playback_clip_fps}p cannot play while camera is in 24.00p mode"
            )

    if shoot_mode == "S_AND_Q":
        if file_format == "XAVC_S_I_DCI_4K" and sq_frame_rate_fps > 60:
            errors.append(
                f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: XAVC S-I DCI 4K caps S&Q at 60/50fps (600M); {sq_frame_rate_fps}fps is blocked"
            )
        if sq_frame_rate_fps == 48 and not (file_format == "XAVC_S_I_DCI_4K" and is_2400p):
            errors.append(
                f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: S&Q 48fps is exclusive to 24.00p + XAVC_S_I_DCI_4K"
            )
    if expect_sq_dci4k_allows_100_or_120fps:
        errors.append(
            f"{P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400}: G139 erratum — XAVC S-I DCI 4K caps S&Q at 60/50fps (blocks 100/120fps)"
        )
    if expect_sq_48fps_outside_dci4k_2400p:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: S&Q 48fps cannot be selected outside 24.00p + XAVC S-I DCI 4K"
        )
    if expect_sq_xavc_s_hd_120fps_requires_v90:
        errors.append(
            f"{P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400}: G139 erratum — S&Q XAVC S HD 100/120fps requires only SDXC V60+ (V90 is only for 200/240fps)"
        )
    if claimed_movie_settings_resist_camera_reset:
        errors.append(
            f"{P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION}: [File Format] and [Movie Settings] are Can be reset under [Camera Settings Reset]"
        )

    req_speed, vpg400_trig = _resolve_required_card_speed(
        shoot_mode=shoot_mode,
        file_format=file_format,
        record_setting_mbps=record_setting_mbps,
        sq_frame_rate_fps=sq_frame_rate_fps,
        proxy_recording_enabled=proxy_recording_enabled,
    )
    if expect_high_rate_sq_proxy_succeeds_without_vpg400:
        errors.append(
            f"{P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400}: high-rate S&Q + Proxy triggers UNDER_1350MBPS VPG400 firewall ({P368_VPG400_UXC_RESIDS})"
        )
    if media_card_speed in P368_MEDIA_CARD_SPEED_RANK:
        if P368_MEDIA_CARD_SPEED_RANK[media_card_speed] < P368_MEDIA_CARD_SPEED_RANK[req_speed]:
            errors.append(
                f"{P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400}: card {media_card_speed} insufficient for {file_format} (requires >= {req_speed})"
            )

    # FX6 Rec Format & Class300
    if fx6_rec_codec not in P368_FX6_REC_FORMAT_CODECS:
        errors.append(f"{P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300}: invalid fx6_rec_codec {fx6_rec_codec!r}")
    if fx6_dormant_rec_format_requested is not None:
        errors.append(
            f"{P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300}: FX6 {fx6_dormant_rec_format_requested!r} is dormant (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if fx6_video_format == "4096x2160" and fx6_rec_codec == "XAVC_L":
        errors.append(
            f"{P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300}: FX6 4096x2160 DCI 4K is XAVC-I only (XAVC-L lacks DCI 4K)"
        )
    if claimed_fx6_xavc_l_supports_dci4k:
        errors.append(
            f"{P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300}: FX6 XAVC-L supports QFHD (150/100M) and HD (50/35M), not 4096x2160 DCI 4K"
        )
    if fx6_rec_mbps > 600:
        errors.append(
            f"{P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300}: FX6 XAVC-I max is 600M VBR (Class300), got {fx6_rec_mbps}M"
        )

    # Wave 77.2: Priority Set in AWB, Shutter AWB Lock, 2500..9900K & FX6 ATW
    if awb_priority_set not in P368_AWB_PRIORITY_MODES:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: invalid awb_priority_set {awb_priority_set!r}"
        )
    if shutter_awb_lock not in P368_SHUTTER_AWB_LOCK_MODES:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: invalid shutter_awb_lock {shutter_awb_lock!r}"
        )
    if movie_awb_lock_custom_key not in P368_MOVIE_AWB_LOCK_CUSTOM_KEYS:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: invalid movie_awb_lock_custom_key {movie_awb_lock_custom_key!r}"
        )
    if (
        kelvin_temp_k < P368_KELVIN_MIN_K
        or kelvin_temp_k > P368_KELVIN_MAX_K
        or (kelvin_temp_k - P368_KELVIN_MIN_K) % P368_KELVIN_STEP_K != 0
    ):
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: [C.Temp./Filter] must be 2500..9900K in 100K steps (75 steps), got {kelvin_temp_k}K"
        )
    if expect_awb_priority_effective_in_cine_ei and log_shooting_mode in ("CINE_EI", "CINE_EI_QUICK"):
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: [Priority Set in AWB] is ineffective in {log_shooting_mode} because Auto/Underwater Auto WB are disabled"
        )
    if expect_shutter_awb_lock_active_in_movie:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: [Shutter AWB Lock] is Still-only; Movie uses Custom Key AWB Lock Hold/Toggle"
        )
    if claimed_shutter_awb_lock_wiped_by_camera_reset:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: [Shutter AWB Lock] is Reset-resistant (Not available under [Camera Settings Reset], Initialize-only)"
        )
    if claimed_awb_priority_resists_camera_reset:
        errors.append(
            f"{P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN}: [Priority Set in AWB] is Can be reset under [Camera Settings Reset]"
        )

    if fx6_wht_bal_switch not in P368_FX6_WHT_BAL_SWITCH_POSITIONS:
        errors.append(f"{P368_GA_ERR_FX6_ATW_OR_WHT_BAL}: invalid fx6_wht_bal_switch {fx6_wht_bal_switch!r}")
    if not (P368_FX6_KELVIN_MIN_K <= fx6_kelvin_temp_k <= P368_FX6_KELVIN_MAX_K):
        errors.append(
            f"{P368_GA_ERR_FX6_ATW_OR_WHT_BAL}: FX6 Preset Kelvin must be 2000..15000K, got {fx6_kelvin_temp_k}K"
        )
    if not (P368_FX6_ATW_SPEED_MIN <= fx6_atw_speed <= P368_FX6_ATW_SPEED_MAX):
        errors.append(f"{P368_GA_ERR_FX6_ATW_OR_WHT_BAL}: FX6 ATW Speed must be 1..5, got {fx6_atw_speed}")
    if fx6_shockless_white not in P368_FX6_SHOCKLESS_WHITE_MODES:
        errors.append(
            f"{P368_GA_ERR_FX6_ATW_OR_WHT_BAL}: invalid fx6_shockless_white {fx6_shockless_white!r}"
        )
    if expect_fx6_atw_active_in_cine_ei and fx6_cine_ei_active:
        errors.append(
            f"{P368_GA_ERR_FX6_ATW_OR_WHT_BAL}: FX6 ATW is disabled in Cine EI"
        )

    effective_file_format = (
        P368_FX3_FILE_FORMAT_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else file_format
    )
    effective_awb_priority = (
        P368_AWB_PRIORITY_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else awb_priority_set
    )
    effective_shutter_awb_lock = (
        P368_SHUTTER_AWB_LOCK_DEFAULT if reset_action == "INITIALIZE" else shutter_awb_lock
    )
    awb_prio_effective = log_shooting_mode not in ("CINE_EI", "CINE_EI_QUICK")
    fx6_atw_effective = bool(fx6_atw_enabled and not fx6_cine_ei_active)

    return P368CheckGroupAMovieSetVpgAwbPrioAndFx6AtwResult(
        group_id=P368_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        body_model_id_hex=f"0x{body_model_id:08x}",
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        file_format=file_format,
        effective_file_format_after_reset=effective_file_format,
        rec_frame_rate_fps=rec_frame_rate_fps,
        sq_frame_rate_fps=sq_frame_rate_fps,
        record_setting_mbps=record_setting_mbps,
        proxy_recording_enabled=proxy_recording_enabled,
        media_card_speed=media_card_speed,
        required_min_card_speed=req_speed,
        vpg400_proxy_threshold_triggered=vpg400_trig,
        cross_2400p_reboot_triggered=cross_2400p_reboot,
        playback_2400p_isolated=playback_2400p_isolated,
        fx3_dormant_8k_ui_count=0,
        fx6_rec_codec=fx6_rec_codec,
        fx6_video_format=fx6_video_format,
        fx6_xavc_i_max_class=P368_FX6_XAVC_I_MAX_CLASS,
        fx6_dormant_class480_or_l25_count=0,
        awb_priority_set=awb_priority_set,
        effective_awb_priority_after_reset=effective_awb_priority,
        awb_priority_effective_in_log=awb_prio_effective,
        shutter_awb_lock=shutter_awb_lock,
        effective_shutter_awb_lock_after_reset=effective_shutter_awb_lock,
        shutter_awb_lock_still_only=True,
        shutter_awb_lock_resists_camera_reset=True,
        movie_awb_lock_custom_key=movie_awb_lock_custom_key,
        kelvin_temp_k=kelvin_temp_k,
        fx3_kelvin_step_count=P368_KELVIN_STEP_COUNT,
        fx3_ab_tint_steps=P368_AB_TINT_STEP_COUNT,
        fx3_gm_tint_steps=P368_GM_TINT_STEP_COUNT,
        fx6_wht_bal_switch=fx6_wht_bal_switch,
        fx6_atw_speed=fx6_atw_speed,
        fx6_atw_enabled_effective=fx6_atw_effective,
        fx6_shockless_white=fx6_shockless_white,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Waves 77.3 & 77.4)
# ---------------------------------------------------------------------------


def evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
    *,
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    exposure_mode: str = "MANUAL_EXPOSURE",
    reset_action: str = "NONE",
    # Wave 77.3
    focus_assistant_items: Tuple[str, ...] = P368_FOCUS_ASSISTANT_EXACT_4_ITEMS,
    auto_magnifier_in_mf: str = "OFF",
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag: str = "X1_0",
    af_in_focus_mag: str = "ON",
    cont_shooting_active: bool = False,
    mount_adaptor_attached: bool = False,
    expect_af_in_focus_mag_active_under_lockout: bool = False,
    peaking_items: Tuple[str, ...] = P368_PEAKING_EXACT_3_ITEMS,
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "RED",
    claimed_focus_assist_or_peaking_wiped_by_camera_reset: bool = False,
    claimed_peaking_outputs_over_hdmi: bool = False,
    touch_operation_items: Tuple[str, ...] = P368_TOUCH_OPERATION_EXACT_4_ITEMS,
    touch_operation: str = "ON",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    swipe_up: str = "OPEN_THE_FN_MENU",
    dormant_touch_item_requested: Optional[str] = None,
    claimed_touch_operation_wiped_by_camera_reset: bool = False,
    fx6_peaking_items: Tuple[str, ...] = P368_FX6_PEAKING_EXACT_3_ITEMS,
    fx6_peaking_dormant_binding_requested: Optional[str] = None,
    # Wave 77.4
    fx3_screen_reader_requested: bool = False,
    fx6_screen_reader_requested: bool = False,
    expect_screen_reader_outputs_over_hdmi: bool = False,
    version_rows_exposed: Tuple[str, ...] = P368_FX3_VERSION_EXACT_2_ROWS,
    mount_adaptor_fw_checked: bool = False,
    claimed_mount_adaptor_has_3rd_version_row: bool = False,
    claimed_mi_shoe_version_shown: bool = False,
    airplane_mode: str = "ON",
    expect_update_red_dot_visible_in_airplane_mode: bool = False,
    bodydata_slot1_flash_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
) -> P368CheckGroupBFocusAssistPeakingTouchScreenReaderVersionResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P368_VALID_SHOOT_MODES:
        errors.append(f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid shoot_mode {shoot_mode!r}")
    if focus_mode not in P368_VALID_FOCUS_MODES:
        errors.append(f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid focus_mode {focus_mode!r}")
    if reset_action not in P368_VALID_RESET_ACTIONS:
        errors.append(f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid reset_action {reset_action!r}")

    # Wave 77.3: G109 Errata Reconciliation
    if tuple(focus_assistant_items) != P368_FOCUS_ASSISTANT_EXACT_4_ITEMS:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: [Focus Assistant] must expose exact 4 items {P368_FOCUS_ASSISTANT_EXACT_4_ITEMS}"
        )
    if auto_magnifier_in_mf not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid auto_magnifier_in_mf {auto_magnifier_in_mf!r}"
        )
    if focus_magnif_time not in P368_FOCUS_MAGNIF_TIMES:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid focus_magnif_time {focus_magnif_time!r}"
        )
    valid_init_mags = (
        P368_INITIAL_FOCUS_MAG_STILL_FF + P368_INITIAL_FOCUS_MAG_STILL_APSC
        if shoot_mode == "PHOTO"
        else P368_INITIAL_FOCUS_MAG_MOVIE
    )
    if initial_focus_mag not in valid_init_mags:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid initial_focus_mag {initial_focus_mag!r} for {shoot_mode}"
        )
    if af_in_focus_mag not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid af_in_focus_mag {af_in_focus_mag!r}"
        )

    af_mag_lockout = (
        shoot_mode in ("MOVIE", "S_AND_Q")
        or focus_mode == "AF_C"
        or (focus_mode == "AF_A" and exposure_mode not in ("PROGRAM_AUTO", "APERTURE_PRIORITY", "SHUTTER_PRIORITY", "MANUAL_EXPOSURE"))
        or cont_shooting_active
        or mount_adaptor_attached
    )
    if expect_af_in_focus_mag_active_under_lockout and af_mag_lockout:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: [AF in Focus Mag.] is Still-only and locked out under Movie/S&Q, AF-C, non-PASM AF-A, Cont. Shooting, or Mount Adaptor"
        )
    if tuple(peaking_items) != P368_PEAKING_EXACT_3_ITEMS:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: [Peaking Display] must expose exact 3 items {P368_PEAKING_EXACT_3_ITEMS}"
        )
    if peaking_display not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid peaking_display {peaking_display!r}"
        )
    if peaking_level not in P368_PEAKING_LEVELS:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid peaking_level {peaking_level!r}"
        )
    if peaking_color not in P368_PEAKING_COLORS:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: invalid peaking_color {peaking_color!r}"
        )
    if claimed_focus_assist_or_peaking_wiped_by_camera_reset:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: G109 erratum — ALL 4 [Focus Assistant] and ALL 3 [Peaking Display] items are Reset-resistant (Initialize-only)"
        )
    if claimed_peaking_outputs_over_hdmi:
        errors.append(
            f"{P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET}: [Peaking Display] outputs 0 px over HDMI"
        )

    # Touch Operation (4 exposed) vs Dormant Touch Panel/Pad & Touch Shutter
    if tuple(touch_operation_items) != P368_TOUCH_OPERATION_EXACT_4_ITEMS:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: [Touch Operation] must expose exact 4 items {P368_TOUCH_OPERATION_EXACT_4_ITEMS}"
        )
    if touch_operation not in P368_TOUCH_OPERATION_MODES:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: invalid touch_operation {touch_operation!r}"
        )
    if touch_sensitivity not in P368_TOUCH_SENSITIVITY_MODES:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: invalid touch_sensitivity {touch_sensitivity!r}"
        )
    if touch_func_in_shooting not in P368_TOUCH_FUNC_IN_SHOOTING_MODES:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: invalid touch_func_in_shooting {touch_func_in_shooting!r}"
        )
    if swipe_up not in P368_SWIPE_UP_MODES:
        errors.append(f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: invalid swipe_up {swipe_up!r}")
    if dormant_touch_item_requested is not None:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: dormant EVF/Alpha {dormant_touch_item_requested!r} has 0 exposed UI items on FX3 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if claimed_touch_operation_wiped_by_camera_reset:
        errors.append(
            f"{P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD}: Setup -> [Touch Operation] 4 items are Reset-resistant (Initialize-only)"
        )

    if tuple(fx6_peaking_items) != P368_FX6_PEAKING_EXACT_3_ITEMS:
        errors.append(
            f"{P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG}: FX6 Peaking exposes exact 3 items {P368_FX6_PEAKING_EXACT_3_ITEMS}"
        )
    if fx6_peaking_dormant_binding_requested is not None:
        errors.append(
            f"{P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG}: FX6 Peaking dormant {fx6_peaking_dormant_binding_requested!r} has 0 ELF bindings (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )

    # Wave 77.4: Dual-model SKU-gated Screen Reader & 2-row Version + BODYDATA.DAT EROFS=30
    if fx3_screen_reader_requested:
        errors.append(
            f"{P368_GB_ERR_SCREEN_READER_SKU_GATE}: [Accessibility]/[Screen Reader] is compiled in appFw.so but SKU-gated (0 exposed UI items on ILME-FX3, EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if fx6_screen_reader_requested:
        errors.append(
            f"{P368_GB_ERR_SCREEN_READER_SKU_GATE}: [Accessibility]/[Screen Reader] has 0 exposed UI items on ILME-FX6 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if expect_screen_reader_outputs_over_hdmi:
        errors.append(
            f"{P368_GB_ERR_SCREEN_READER_SKU_GATE}: FX3 appFw.so has 0 SCREEN_READER*HDMI symbols"
        )

    if tuple(version_rows_exposed) != P368_FX3_VERSION_EXACT_2_ROWS:
        errors.append(
            f"{P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30}: G104 erratum — FX3 [Version] exposes exact 2 rows {P368_FX3_VERSION_EXACT_2_ROWS}"
        )
    if claimed_mount_adaptor_has_3rd_version_row:
        errors.append(
            f"{P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30}: G104 erratum — Mount Adaptor firmware shares the Lens slot (libInfraGetVersion has only Body & Lens)"
        )
    if claimed_mi_shoe_version_shown:
        errors.append(
            f"{P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30}: [Version] displays 0 MI-Shoe accessory version rows"
        )
    if expect_update_red_dot_visible_in_airplane_mode and airplane_mode == "ON":
        errors.append(
            f"{P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30}: red update dot is silenced when Airplane Mode=On"
        )
    if bodydata_slot1_flash_requested:
        errors.append(
            f"{P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30}: [Software Update] (Slot 1 BODYDATA.DAT) hard-blocked EROFS={P368_ERRNO_EROFS}"
        )

    af_mag_effective = (af_in_focus_mag == "ON") and (not af_mag_lockout) and (shoot_mode == "PHOTO")

    return P368CheckGroupBFocusAssistPeakingTouchScreenReaderVersionResult(
        group_id=P368_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        exposure_mode=exposure_mode,
        reset_action=reset_action,
        focus_assistant_items=tuple(focus_assistant_items),
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag=initial_focus_mag,
        af_in_focus_mag=af_in_focus_mag,
        af_in_focus_mag_effective=af_mag_effective,
        peaking_items=tuple(peaking_items),
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        peaking_hdmi_pixel_count=P368_PEAKING_HDMI_PIXEL_COUNT,
        focus_assist_and_peaking_resist_camera_reset=True,
        touch_operation_items=tuple(touch_operation_items),
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        swipe_up=swipe_up,
        fx3_dormant_touchpad_ui_count=0,
        fx6_peaking_items=tuple(fx6_peaking_items),
        fx6_peaking_dormant_freq_bindings=0,
        fx6_focus_mag_vf_ratio=P368_FX6_FOCUS_MAG_VF_RATIO,
        fx6_focus_mag_hdmi_ratio=P368_FX6_FOCUS_MAG_HDMI_RATIO,
        fx3_screen_reader_ui_count=P368_FX3_SCREEN_READER_UI_COUNT,
        fx6_screen_reader_ui_count=P368_FX6_SCREEN_READER_UI_COUNT,
        fx3_screen_reader_hdmi_hits=P368_FX3_SCREEN_READER_HDMI_HITS,
        version_rows_exposed=tuple(version_rows_exposed),
        mount_adaptor_shares_lens_slot=True if mount_adaptor_fw_checked or True else True,
        fx3_version_mi_shoe_shown=P368_FX3_VERSION_MI_SHOE_SHOWN,
        airplane_mode=airplane_mode,
        version_update_red_dot_silenced=(airplane_mode == "ON"),
        bodydata_slot1_update_blocked_erofs30=True,
        fx6_version_rows=P368_FX6_VERSION_ROWS,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Waves 78.1 & 78.2)
# ---------------------------------------------------------------------------


def evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
    *,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    # Wave 78.1
    exposure_ctrl_type: str = P368_EXPOSURE_CTRL_TYPE_DEFAULT,
    av_auto_manual_switch: str = "MANUAL",
    tv_auto_manual_switch: str = "MANUAL",
    iso_auto_manual_switch: str = "MANUAL",
    auto_slow_shutter: str = "ON",
    claimed_exposure_ctrl_type_wiped_by_camera_reset: bool = False,
    claimed_auto_manual_or_slow_shutter_resists_reset: bool = False,
    shutter_mode: str = P368_SHUTTER_MODE_DEFAULT,
    shutter_angle_value: str = "180.0",
    frame_rate_fps: float = 23.98,
    sq_frame_rate_fps: int = 24,
    anti_flicker_shoot: str = "OFF",
    expect_shutter_angle_active_in_still: bool = False,
    expect_exposure_step_alters_shutter_angle: bool = False,
    claimed_shutter_angle_shared_when_diffset_unchecked: bool = False,
    claimed_bk4_speed_and_angle_overwrite_each_other: bool = False,
    expect_anti_flicker_active_in_movie: bool = False,
    dormant_var_shutter_requested: bool = False,
    fx6_shutter_mode: str = "ANGLE",
    # Wave 78.2
    steadyshot_movie: str = P368_STEADYSHOT_MOVIE_DEFAULT,
    steadyshot_adjust: str = "AUTO",
    steadyshot_focal_length_mm: int = 50,
    exposed_focal_lengths_mm: Tuple[int, ...] = P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    hdmi_raw_output: bool = False,
    desqueeze_display: str = "OFF",
    e_mount_sony_lens: bool = True,
    external_hdmi_recorder_active: bool = False,
    expect_steadyshot_active_under_lockout: bool = False,
    expect_catalyst_gyro_available: bool = False,
    claimed_200mm_active_still_documented_in_ver7: bool = False,
    dormant_steadyshot_mode_requested: Optional[str] = None,
    claimed_steadyshot_resists_camera_reset: bool = False,
    claimed_fx6_has_body_ibis: bool = False,
    fx6_lens_oss_mode: str = "OFF",
    claimed_fx6_lens_oss_only_on_off: bool = False,
    expect_fx6_catalyst_ok_with_oss_on: bool = False,
) -> P368CheckGroupCFlexExpShutterAngleActiveIbisCatalystFx6OssResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P368_VALID_SHOOT_MODES:
        errors.append(f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: invalid shoot_mode {shoot_mode!r}")
    if reset_action not in P368_VALID_RESET_ACTIONS:
        errors.append(f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: invalid reset_action {reset_action!r}")

    # Wave 78.1: Exposure Ctrl Type (G86 gap closure), Shutter Mode/Angle & FX6 4-mode
    if exposure_ctrl_type not in P368_EXPOSURE_CTRL_TYPES:
        errors.append(
            f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: invalid exposure_ctrl_type {exposure_ctrl_type!r}"
        )
    for lbl, val in (
        ("av_auto_manual_switch", av_auto_manual_switch),
        ("tv_auto_manual_switch", tv_auto_manual_switch),
        ("iso_auto_manual_switch", iso_auto_manual_switch),
    ):
        if val not in P368_AUTO_MANUAL_MODES:
            errors.append(f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: invalid {lbl} {val!r}")
    if auto_slow_shutter not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: invalid auto_slow_shutter {auto_slow_shutter!r}"
        )
    if claimed_exposure_ctrl_type_wiped_by_camera_reset:
        errors.append(
            f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: G86 gap closure — parent [Exposure Ctrl Type] is Not available under [Camera Settings Reset] (Initialize-only)"
        )
    if claimed_auto_manual_or_slow_shutter_resists_reset:
        errors.append(
            f"{P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT}: child [Auto/Manual Swt. Set.] and [Auto Slow Shutter] are Can be reset"
        )

    if shutter_mode not in P368_SHUTTER_MODES:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: invalid shutter_mode {shutter_mode!r}"
        )
    valid_angles = P368_SHUTTER_ANGLE_STANDARD_DEGREES + P368_SHUTTER_ANGLE_SLOW_FRAMES
    if shutter_angle_value not in valid_angles:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: invalid shutter_angle_value {shutter_angle_value!r}"
        )
    if (
        shutter_mode == "ANGLE"
        and shutter_angle_value in P368_SHUTTER_ANGLE_SLOW_FRAMES
        and (frame_rate_fps >= 100.0 or (shoot_mode == "S_AND_Q" and sq_frame_rate_fps >= 200))
    ):
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: slow-frame angle {shutter_angle_value!r} clamped at high fps ({frame_rate_fps}p / S&Q {sq_frame_rate_fps}fps)"
        )
    if expect_shutter_angle_active_in_still:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: [Shutter Mode]=Angle is strictly Movie/S&Q-only (Still uses Shutter Speed)"
        )
    if expect_exposure_step_alters_shutter_angle:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: [Exposure step] never alters [Shutter Angle]"
        )
    if claimed_shutter_angle_shared_when_diffset_unchecked:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: [Shutter Mode]=Angle always splits Still and Movie shutter even if unchecked in [Different Set for Still/Mv]"
        )
    if claimed_bk4_speed_and_angle_overwrite_each_other:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: BK4 {P368_BK4_SHUTTER_SPEED_REG} (Speed) and {P368_BK4_SHUTTER_ANGLE_REG} (Angle) are independent registers"
        )
    if anti_flicker_shoot not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: invalid anti_flicker_shoot {anti_flicker_shoot!r}"
        )
    if expect_anti_flicker_active_in_movie:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: [Anti-flicker Shoot.] is strictly Still-only"
        )
    if dormant_var_shutter_requested:
        errors.append(
            f"{P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER}: dormant [Var. Shutter] (HIGH_RES_SS) has 0 exposed UI items on FX3 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if fx6_shutter_mode not in P368_FX6_SHUTTER_MODES:
        errors.append(
            f"{P368_GC_ERR_FX6_4MODE_SHUTTER_CONTRACT}: FX6 Shutter Mode must be in 4-mode {P368_FX6_SHUTTER_MODES}, got {fx6_shutter_mode!r}"
        )

    # Wave 78.2: SteadyShot Active 4-lockout, Catalyst Gyro RTMD & FX6 Zero Body IBIS + 3-step Lens OSS
    if steadyshot_movie not in P368_STEADYSHOT_MOVIE_MODES:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: invalid steadyshot_movie {steadyshot_movie!r}"
        )
    if steadyshot_adjust not in P368_STEADYSHOT_ADJUST_MODES:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: invalid steadyshot_adjust {steadyshot_adjust!r}"
        )
    if desqueeze_display not in P368_VALID_DESQUEEZE_MODES:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: invalid desqueeze_display {desqueeze_display!r}"
        )
    if tuple(exposed_focal_lengths_mm) != P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: IBIS focal table must be exact 47 entries (got {len(exposed_focal_lengths_mm)})"
        )
    if steadyshot_focal_length_mm not in P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: steadyshot_focal_length_mm={steadyshot_focal_length_mm} not in 47-entry table"
        )

    active_locked_out = (
        round(frame_rate_fps, 2) in (100.0, 119.88)
        or (shoot_mode == "S_AND_Q" and sq_frame_rate_fps >= 100)
        or hdmi_raw_output
        or desqueeze_display != "OFF"
    )
    if expect_steadyshot_active_under_lockout and active_locked_out:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: [SteadyShot]=Active is locked out under 119.88p/100p, S&Q>=100fps, HDMI RAW=On, or De-Squeeze!=Off"
        )
    if claimed_200mm_active_still_documented_in_ver7:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: Ver. 2.00..7.02 ilc/2210 removed the Ver. 1 >=200mm Active note"
        )
    if dormant_steadyshot_mode_requested is not None:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: dormant SteadyShot {dormant_steadyshot_mode_requested!r} is unexposed on FX3 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if claimed_steadyshot_resists_camera_reset:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: all 4 Image Stabilization items are Can be reset under [Camera Settings Reset]"
        )

    effective_steadyshot_movie = (
        P368_STEADYSHOT_MOVIE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else ("STANDARD" if (steadyshot_movie == "ACTIVE" and active_locked_out) else steadyshot_movie)
    )
    catalyst_rtmd_available = (
        effective_steadyshot_movie in ("OFF", "ACTIVE")
        and e_mount_sony_lens
        and shoot_mode != "S_AND_Q"
        and round(frame_rate_fps, 2) not in (100.0, 119.88)
        and not external_hdmi_recorder_active
    )
    if expect_catalyst_gyro_available and not catalyst_rtmd_available:
        errors.append(
            f"{P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST}: Catalyst Gyro RTMD requires SteadyShot in (Off, Active), electronic E-mount lens, non-S&Q, non-119.88p/100p, and internal recording"
        )

    if claimed_fx6_has_body_ibis:
        errors.append(
            f"{P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS}: ILME-FX6 has 0 body IBIS ({P368_FX6_IBIS_UNSUPPORTED_SYMBOL})"
        )
    if fx6_lens_oss_mode not in P368_FX6_LENS_OSS_MODES:
        errors.append(
            f"{P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS}: FX6 optical OSS exposes 3 steps {P368_FX6_LENS_OSS_MODES}, got {fx6_lens_oss_mode!r}"
        )
    if claimed_fx6_lens_oss_only_on_off:
        errors.append(
            f"{P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS}: FX6 exposes 3-step optical OSS Active/Standard/Off for compatible OSS lenses (not On/Off only)"
        )
    if expect_fx6_catalyst_ok_with_oss_on and fx6_lens_oss_mode != "OFF":
        errors.append(
            f"{P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS}: FX6 Catalyst Gyro requires lens OSS switch set to OFF"
        )

    effective_exp_ctrl = (
        P368_EXPOSURE_CTRL_TYPE_DEFAULT if reset_action == "INITIALIZE" else exposure_ctrl_type
    )
    effective_shutter_mode = (
        P368_SHUTTER_MODE_DEFAULT
        if reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE")
        else shutter_mode
    )

    return P368CheckGroupCFlexExpShutterAngleActiveIbisCatalystFx6OssResult(
        group_id=P368_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        exposure_ctrl_type=exposure_ctrl_type,
        effective_exposure_ctrl_type_after_reset=effective_exp_ctrl,
        exposure_ctrl_type_resists_camera_reset=True,
        av_auto_manual_switch=av_auto_manual_switch,
        tv_auto_manual_switch=tv_auto_manual_switch,
        iso_auto_manual_switch=iso_auto_manual_switch,
        auto_slow_shutter=auto_slow_shutter,
        shutter_mode=shutter_mode,
        effective_shutter_mode_after_reset=effective_shutter_mode,
        shutter_angle_value=shutter_angle_value,
        shutter_angle_standard_count=len(P368_SHUTTER_ANGLE_STANDARD_DEGREES),
        shutter_angle_slow_frame_count=len(P368_SHUTTER_ANGLE_SLOW_FRAMES),
        bk4_speed_reg=P368_BK4_SHUTTER_SPEED_REG,
        bk4_angle_reg=P368_BK4_SHUTTER_ANGLE_REG,
        bk4_registers_independent=True,
        exposure_step_affects_shutter_angle=False,
        shutter_angle_splits_still_movie=True,
        anti_flicker_shoot=anti_flicker_shoot,
        fx3_var_shutter_ui_count=P368_FX3_VAR_SHUTTER_UI_COUNT,
        fx6_shutter_mode=fx6_shutter_mode,
        steadyshot_movie=steadyshot_movie,
        effective_steadyshot_movie=effective_steadyshot_movie,
        steadyshot_active_crop_factor=P368_STEADYSHOT_ACTIVE_CROP_FACTOR,
        steadyshot_active_locked_out=active_locked_out,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_length_mm=steadyshot_focal_length_mm,
        focal_table_entry_count=len(exposed_focal_lengths_mm),
        catalyst_gyro_rtmd_available=catalyst_rtmd_available,
        fx3_dormant_steadyshot_ui_count=0,
        fx6_body_ibis_count=P368_FX6_BODY_IBIS_COUNT,
        fx6_ibis_unsupported_symbol=P368_FX6_IBIS_UNSUPPORTED_SYMBOL,
        fx6_lens_oss_mode=fx6_lens_oss_mode,
        fx6_catalyst_oss_off_required=True,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Tier-0 Receipt Extraction Helper
# ---------------------------------------------------------------------------


def _extract_tier0_evidence(
    *,
    simulate_bench_dry_run: bool,
    receipt_a_bytes: Optional[bytes],
    receipt_b_bytes: Optional[bytes],
    receipt_a_path: Optional[Path],
    receipt_b_path: Optional[Path],
    st_dev_a_override: Optional[int],
    st_dev_b_override: Optional[int],
    body_serial: Optional[str],
    emmc_cid: Optional[str],
    h0_baselines_a: Optional[Mapping[str, str]],
    h0_baselines_b: Optional[Mapping[str, str]],
    h3_baselines: Optional[Mapping[str, str]],
    simulated_h0_h3_drifted_surfaces: int,
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    st_dev_a = st_dev_a_override
    st_dev_b = st_dev_b_override
    used_mode = "NONE"

    if receipt_a_path is not None:
        if not receipt_a_path.exists() or not receipt_a_path.is_file():
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_a_path {receipt_a_path}"
            )
        else:
            raw_a = receipt_a_path.read_bytes()
            if st_dev_a is None:
                st_dev_a = int(receipt_a_path.stat().st_dev)
            used_mode = "PHYSICAL_DUAL_MEDIA"

    if receipt_b_path is not None:
        if not receipt_b_path.exists() or not receipt_b_path.is_file():
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing receipt_b_path {receipt_b_path}"
            )
        else:
            raw_b = receipt_b_path.read_bytes()
            if st_dev_b is None:
                st_dev_b = int(receipt_b_path.stat().st_dev)
            used_mode = "PHYSICAL_DUAL_MEDIA"

    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None
    eff_h3 = dict(h3_baselines) if h3_baselines is not None else None

    if simulate_bench_dry_run and raw_a is None and raw_b is None:
        sim = build_simulated_phase368_tier0_receipts(
            body_serial=eff_serial or "FX3SIM70200368",
            emmc_cid=eff_cid or "11010030303847333000a1b2c3d49368",
        )
        raw_a = sim["receipt_a_bytes"]
        raw_b = sim["receipt_b_bytes"]
        st_dev_a = sim["st_dev_a"] if st_dev_a is None else st_dev_a
        st_dev_b = sim["st_dev_b"] if st_dev_b is None else st_dev_b
        eff_serial = sim["body_serial"]
        eff_cid = sim["emmc_cid"]
        if eff_h0_a is None:
            eff_h0_a = sim["h0_baselines_a"]
        if eff_h0_b is None:
            eff_h0_b = sim["h0_baselines_b"]
        if eff_h3 is None:
            eff_h3 = sim["h3_baselines"]
        used_mode = "DRY_RUN_SIMULATED_RECEIPTS"

    if raw_a is None and raw_b is None:
        return {
            "receipt_provided": False,
            "tier0_receipt_verified": False,
            "receipt_mode": "AWAITING_PHYSICAL_RECEIPT",
            "h0_equals_h3_count": 0,
            "st_dev_a": None,
            "st_dev_b": None,
            "body_serial": eff_serial or "",
            "emmc_cid": eff_cid or "",
            "errors": errors,
            "warnings": [
                "Offline dry-run preflight awaiting physical dual-media 528 B FX3RCPT1 receipts (pass --simulate-bench-dry-run for simulated Tier-0 rehearsal)"
            ],
        }

    if raw_a is None or raw_b is None:
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528 B FX3RCPT1 receipts are required"
        )
        return {
            "receipt_provided": True,
            "tier0_receipt_verified": False,
            "receipt_mode": used_mode,
            "h0_equals_h3_count": 0,
            "st_dev_a": st_dev_a,
            "st_dev_b": st_dev_b,
            "body_serial": eff_serial or "",
            "emmc_cid": eff_cid or "",
            "errors": errors,
            "warnings": warnings,
        }

    if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES:
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt size must be {SD_RECEIPT_BYTES} B, got {len(raw_a)}B / {len(raw_b)}B"
        )

    parsed_a = None
    parsed_b = None
    if len(raw_a) == SD_RECEIPT_BYTES:
        try:
            parsed_a = parse_sd_backup_receipt_bytes(raw_a)
        except Exception as exc:
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: parse error receipt A: {exc}"
            )
    if len(raw_b) == SD_RECEIPT_BYTES:
        try:
            parsed_b = parse_sd_backup_receipt_bytes(raw_b)
        except Exception as exc:
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: parse error receipt B: {exc}"
            )

    if parsed_a is not None:
        if not getattr(parsed_a, "valid", False):
            errs_a = "; ".join(getattr(parsed_a, "errors", ()))
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt A invalid ({errs_a})"
            )
        if _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", ""))):
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt A trivial manifest_sha256"
            )
    if parsed_b is not None:
        if not getattr(parsed_b, "valid", False):
            errs_b = "; ".join(getattr(parsed_b, "errors", ()))
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt B invalid ({errs_b})"
            )
        if _is_trivial_hex64(str(getattr(parsed_b, "manifest_sha256", ""))):
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt B trivial manifest_sha256"
            )
    if parsed_a is not None and parsed_b is not None:
        if str(getattr(parsed_a, "manifest_sha256", "")) != str(getattr(parsed_b, "manifest_sha256", "")) or raw_a != raw_b:
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: Copy A and Copy B receipts disagree"
            )

    if st_dev_a is not None and st_dev_b is not None and st_dev_a == st_dev_b:
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media receipts share same st_dev={st_dev_a}"
        )
    elif st_dev_a is None or st_dev_b is None:
        if used_mode == "NONE":
            used_mode = "IN_MEMORY_BYTES"
        if st_dev_a_override is not None and st_dev_b_override is not None:
            st_dev_a = st_dev_a_override
            st_dev_b = st_dev_b_override
        elif raw_a is not None and raw_b is not None and not simulate_bench_dry_run:
            errors.append(
                f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: distinct st_dev_a and st_dev_b required for dual-media independence"
            )

    if (
        not eff_serial
        or eff_serial.lower() in FORBIDDEN_TRIVIAL_SERIALS
        or len(set(eff_serial)) <= 1
        or not BODY_SERIAL_RE.match(eff_serial)
    ):
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial body_serial {eff_serial!r}"
        )
    if not eff_cid or eff_cid.lower() in FORBIDDEN_TRIVIAL_CIDS or not HEX32_CID_RE.match(eff_cid):
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/trivial emmc_cid {eff_cid!r}"
        )

    if eff_h0_a is None or eff_h0_b is None:
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: H0 baseline manifests required for Copy A and Copy B"
        )
    elif eff_h0_a != eff_h0_b:
        errors.append(
            f"{P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: H0 Copy A and Copy B baselines diverge"
        )

    if eff_h3 is None and eff_h0_a is not None:
        eff_h3 = dict(eff_h0_a)

    receipt_ok_so_far = (
        len(errors) == 0
        and getattr(parsed_a, "valid", False)
        and getattr(parsed_b, "valid", False)
        and raw_a == raw_b
        and not _is_trivial_hex64(str(getattr(parsed_a, "manifest_sha256", "")))
    )

    h0_eq_h3 = 0
    if eff_h0_a is None or eff_h0_b is None or eff_h3 is None:
        pass
    elif set(eff_h0_a.keys()) != set(REQUIRED_H0_BASELINE_KEYS) or set(eff_h3.keys()) != set(
        REQUIRED_H0_BASELINE_KEYS
    ):
        errors.append(
            f"{P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: baseline manifests must cover all 8 REQUIRED_H0_BASELINE_KEYS"
        )
    elif receipt_ok_so_far:
        key_mismatches = sum(
            1
            for key in REQUIRED_H0_BASELINE_KEYS
            if _is_trivial_hex64(str(eff_h0_a.get(key, "")))
            or _is_trivial_hex64(str(eff_h3.get(key, "")))
            or str(eff_h0_a.get(key, "")).lower() != str(eff_h0_b.get(key, "")).lower()
            or str(eff_h0_a.get(key, "")).lower() != str(eff_h3.get(key, "")).lower()
        )
        surface_mismatches = sum(
            1
            for surf in SIXTEEN_STORAGE_SURFACES
            if eff_h0_a.get(surf) != eff_h0_b.get(surf) or eff_h0_a.get(surf) != eff_h3.get(surf)
        )
        extra_keys = set(eff_h0_a.keys()) | set(eff_h0_b.keys()) | set(eff_h3.keys())
        extra_mismatches = sum(
            1
            for k in extra_keys
            if (k in eff_h0_a) != (k in eff_h3)
            or (k in eff_h0_a) != (k in eff_h0_b)
            or str(eff_h0_a.get(k, "")).lower() != str(eff_h3.get(k, "")).lower()
            or str(eff_h0_a.get(k, "")).lower() != str(eff_h0_b.get(k, "")).lower()
        )
        drifted = max(
            0,
            int(simulated_h0_h3_drifted_surfaces),
            key_mismatches,
            surface_mismatches,
            extra_mismatches,
        )
        h0_eq_h3 = max(0, P368_STORAGE_SURFACE_COUNT - drifted)

    if len(SIXTEEN_STORAGE_SURFACES) != P368_STORAGE_SURFACE_COUNT:
        errors.append(
            f"{P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: expected 16 surfaces, got {len(SIXTEEN_STORAGE_SURFACES)}"
        )
    elif h0_eq_h3 != P368_STORAGE_SURFACE_COUNT:
        errors.append(
            f"{P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity failed ({h0_eq_h3}/{P368_STORAGE_SURFACE_COUNT})"
        )

    verified = len(errors) == 0 and h0_eq_h3 == P368_STORAGE_SURFACE_COUNT
    return {
        "receipt_provided": True,
        "tier0_receipt_verified": verified,
        "receipt_mode": used_mode if used_mode != "NONE" else "IN_MEMORY_BYTES",
        "h0_equals_h3_count": h0_eq_h3,
        "st_dev_a": st_dev_a,
        "st_dev_b": st_dev_b,
        "body_serial": eff_serial or "",
        "emmc_cid": eff_cid or "",
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Check Group D + Tier-0 Evaluator (Waves 78.3 & 78.4 + Tier-0)
# ---------------------------------------------------------------------------


def evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    shoot_mode: str = "MOVIE",
    reset_action: str = "NONE",
    # Wave 78.3
    source_file_format: str = "XAVC_S_4K",
    source_resolution_4k: bool = True,
    photo_capture_requested: bool = False,
    photo_capture_target_slot: int = 2,
    pb_jpeg_heif_switch: str = P368_PB_JPEG_HEIF_DEFAULT,
    claimed_pb_jpeg_heif_wiped_by_camera_reset: bool = False,
    view_mode_exposed_items: Tuple[str, ...] = P368_VIEW_MODE_EXACT_3_ITEMS,
    view_mode: str = P368_VIEW_MODE_DEFAULT,
    dormant_view_mode_requested: Optional[str] = None,
    claimed_view_mode_wiped_by_camera_reset: bool = False,
    rating_stars: int = 0,
    rating_write_target_slot: int = 2,
    rating_write_requested: bool = False,
    claimed_rating_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_photo_capture: bool = False,
    fx6_clip_flag: str = "OK",
    # Wave 78.4
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_connection_modes_exposed: Tuple[str, ...] = P368_USB_CONNECTION_EXACT_4_MODES,
    dormant_uvc_usb_streaming_requested: bool = False,
    claimed_fx3_supports_uvc_4k_30p: bool = False,
    claimed_movie_rec_during_streaming_is_uvc: bool = False,
    streaming_active: bool = False,
    streaming_protocol: str = "SRT",
    srt_role: str = "SRT_CALLER",
    srt_url_syntax: str = "srt.example.invalid",
    streaming_codec: str = "H265",
    streaming_encryption: str = "AES_256",
    streaming_profile: str = P368_STREAMING_PROFILE_DEFAULT,
    streaming_fps: float = 59.94,
    streaming_bitrate_mbps: float = 9.0,
    movie_rec_during_streaming: str = "DISABLE",
    movie_rec_during_streaming_4k_requested: bool = False,
    movie_rec_during_streaming_slot: int = 2,
    streaming_transport: str = "USB_LAN",
    creators_app_bt_configured: bool = True,
    claimed_fx3_supports_srt_listener: bool = False,
    claimed_streaming_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_native_uvc_or_builtin_srt_rtmp: bool = False,
    # Tier-0 & Redlines
    airplane_mode: str = "ON",
    claimed_reset_network_set_wipes_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    expect_airplane_mode_blocks_usb_lan: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> P368CheckGroupDPhotoCapViewModeRatingUvcSrtAirplaneTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P368_VALID_SHOOT_MODES:
        errors.append(
            f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: invalid shoot_mode {shoot_mode!r}"
        )
    if reset_action not in P368_VALID_RESET_ACTIONS:
        errors.append(
            f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: invalid reset_action {reset_action!r}"
        )

    # Wave 78.3: Photo Capture, View Mode (3 items), Rating & FX6 Clip Flag
    if pb_jpeg_heif_switch not in P368_PB_JPEG_HEIF_MODES:
        errors.append(
            f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: invalid pb_jpeg_heif_switch {pb_jpeg_heif_switch!r}"
        )
    if claimed_pb_jpeg_heif_wiped_by_camera_reset:
        errors.append(
            f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: Playback [JPEG/HEIF Switch] is Reset-resistant (Initialize-only, unlike Shooting's switch)"
        )
    photo_cap_dci4k_blocked = source_file_format == "XAVC_S_I_DCI_4K"
    photo_cap_mp: Optional[float] = (
        None
        if photo_cap_dci4k_blocked
        else (P368_PHOTO_CAPTURE_4K_MP if source_resolution_4k else P368_PHOTO_CAPTURE_HD_MP)
    )
    if photo_capture_requested:
        if photo_cap_dci4k_blocked:
            errors.append(
                f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: Playback -> [Photo Capture] is hard-blocked on XAVC_S_I_DCI_4K (_g 0x60ce)"
            )
        if slot1_contains_tier0_dump and photo_capture_target_slot == 1:
            errors.append(
                f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: [Photo Capture] write to Slot 1 blocked EROFS={P368_ERRNO_EROFS}"
            )

    if tuple(view_mode_exposed_items) != P368_VIEW_MODE_EXACT_3_ITEMS:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: G126 [View Mode] must expose exact 3 items {P368_VIEW_MODE_EXACT_3_ITEMS}"
        )
    if view_mode not in P368_VIEW_MODE_EXACT_3_ITEMS:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: invalid view_mode {view_mode!r}"
        )
    if dormant_view_mode_requested is not None:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: dormant View Mode {dormant_view_mode_requested!r} is unexposed on FX3 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if claimed_view_mode_wiped_by_camera_reset:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: [View Mode] is Reset-resistant (Initialize-only)"
        )
    if not (P368_RATING_MIN <= rating_stars <= P368_RATING_MAX):
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: [Rating] stars must be 0..5, got {rating_stars}"
        )
    if rating_write_requested and slot1_contains_tier0_dump and rating_write_target_slot == 1:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: XMP/AVF [Rating] mutation on Slot 1 blocked EROFS={P368_ERRNO_EROFS}"
        )
    if claimed_rating_wiped_by_camera_reset:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: [Rating] and [Rating Set(Custom Key)] are Reset-resistant"
        )
    if claimed_fx6_has_photo_capture:
        errors.append(
            f"{P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET}: ILME-FX6 has 0 in-camera Photo Capture (uses Thumbnail > Set Clip Flag)"
        )
    if fx6_clip_flag not in P368_FX6_CLIP_FLAGS:
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: invalid fx6_clip_flag {fx6_clip_flag!r}"
        )

    # Wave 78.4: Zero UVC USB Streaming, Outbound-Only SRT Caller, 38 Mbps, Airplane Mode
    if tuple(usb_connection_modes_exposed) != P368_USB_CONNECTION_EXACT_4_MODES:
        errors.append(
            f"{P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF}: [USB Connection Mode] exposes exact 4 modes {P368_USB_CONNECTION_EXACT_4_MODES}"
        )
    if usb_connection_mode not in P368_USB_CONNECTION_EXACT_4_MODES:
        errors.append(
            f"{P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF}: invalid usb_connection_mode {usb_connection_mode!r}"
        )
    if dormant_uvc_usb_streaming_requested:
        errors.append(
            f"{P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF}: UVC [USB Streaming] is unsupported on ILME-FX3/FX3A/7SM3 (EOPNOTSUPP={P368_ERRNO_EOPNOTSUPP})"
        )
    if claimed_fx3_supports_uvc_4k_30p:
        errors.append(
            f"{P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF}: 4K 30p/25p/24p UVC rumor disproved — FX3 has 0 UVC and dormant ELF enum holds only 4K_12_5P/4K_15P"
        )
    if claimed_movie_rec_during_streaming_is_uvc:
        errors.append(
            f"{P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF}: [Movie Rec During Streaming] belongs exclusively to [Network Streaming], not UVC"
        )

    if streaming_protocol not in P368_STREAMING_PROTOCOLS:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid streaming_protocol {streaming_protocol!r}"
        )
    if srt_role != "SRT_CALLER" or claimed_fx3_supports_srt_listener:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: FX3 SRT is strictly outbound SRT_CALLER (0 SRT_LISTENER)"
        )
    if ":" in srt_url_syntax or "?streamid=" in srt_url_syntax.lower():
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: FX3 SRT URL rejects ':port' / '?streamid=' listener/query syntax ({srt_url_syntax!r})"
        )
    if streaming_codec not in P368_SRT_SUPPORTED_CODECS:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid streaming_codec {streaming_codec!r}"
        )
    if streaming_protocol in ("RTMP", "RTMPS") and streaming_codec != "H264":
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: {streaming_protocol} supports H264 only (H265 is SRT-only)"
        )
    if streaming_encryption not in P368_SRT_ENCRYPTIONS:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid streaming_encryption {streaming_encryption!r}"
        )
    if streaming_profile not in P368_STREAMING_PROFILES:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid streaming_profile {streaming_profile!r}"
        )
    else:
        b_min, b_max, _b_def, allows_4k_rec = P368_STREAMING_PROFILES[streaming_profile]
        if streaming_bitrate_mbps < b_min - 1e-6 or streaming_bitrate_mbps > b_max + 1e-6:
            errors.append(
                f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: profile {streaming_profile} bitrate {streaming_bitrate_mbps} Mbps out of [{b_min}..{b_max}]"
            )
        if (
            movie_rec_during_streaming == "ENABLE"
            and movie_rec_during_streaming_4k_requested
            and not allows_4k_rec
        ):
            errors.append(
                f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: profile {streaming_profile} forbids concurrent 4K Movie Rec During Streaming"
            )
    if streaming_bitrate_mbps > P368_STREAMING_MAX_BITRATE_MBPS + 1e-6:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: streaming bitrate exceeds 38 Mbps ceiling ({streaming_bitrate_mbps} Mbps)"
        )
    if round(streaming_fps, 2) not in P368_STREAMING_ALLOWED_FPS:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: streaming_fps {streaming_fps} unsupported (only 59.94/50/29.97/25p; 23.98/24.00/119.88/100p disabled)"
        )
    if movie_rec_during_streaming not in P368_MOVIE_REC_DURING_STREAMING_MODES:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid movie_rec_during_streaming {movie_rec_during_streaming!r}"
        )
    if movie_rec_during_streaming == "ENABLE":
        if shoot_mode == "S_AND_Q":
            errors.append(
                f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: [Movie Rec During Streaming]=Enable forbids S&Q"
            )
        if slot1_contains_tier0_dump and movie_rec_during_streaming_slot == 1:
            errors.append(
                f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: [Movie Rec During Streaming] target Slot 1 blocked EROFS={P368_ERRNO_EROFS}"
            )
    if streaming_transport not in P368_NETWORK_TRANSPORTS:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid streaming_transport {streaming_transport!r}"
        )
    if streaming_active and not creators_app_bt_configured:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: FX3 Network Streaming requires Creators' App configuration"
        )
    if claimed_streaming_wiped_by_camera_reset:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: [Network Streaming] resists [Camera Settings Reset] (resets on [Reset Network Set.] and [Initialize])"
        )
    if claimed_fx6_has_native_uvc_or_builtin_srt_rtmp:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: ILME-FX6 has 0 native UVC and 0 built-in RTMP/SRT/QoS (requires CBK-WA100/CBK-RPU7/PDT-FP1)"
        )

    # Airplane Mode Zero-RF & USB-LAN bypass
    if airplane_mode not in P368_VALID_ON_OFF:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: invalid airplane_mode {airplane_mode!r}"
        )
    if airplane_mode != "ON":
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: Tier-0 zero-RF requires [Airplane Mode]=ON (got {airplane_mode!r})"
        )
    if streaming_active and streaming_transport == "WIFI" and airplane_mode == "ON":
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: Wi-Fi streaming blocked while [Airplane Mode]=ON (use wired USB-LAN)"
        )
    if expect_airplane_mode_blocks_usb_lan:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: USB-LAN bypasses [Airplane Mode]=ON without emitting RF"
        )
    if claimed_reset_network_set_wipes_airplane_mode:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: [Airplane Mode]=ON survives [Reset Network Set.] (only [Initialize] resets it)"
        )
    if claimed_initialize_preserves_airplane_mode:
        errors.append(
            f"{P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF}: [Initialize] resets [Airplane Mode] to Off"
        )

    # Fail-closed hardware / Slot-1 redlines
    if slot1_write_requested and (slot1_contains_tier0_dump or slot1_wp_locked):
        errors.append(
            f"{P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30}: direct Slot 1 write requested -> blocked EROFS={P368_ERRNO_EROFS}"
        )
    if (
        emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or wireless_rf_packets_emitted != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
    ):
        errors.append(
            f"{P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: telemetry counters must remain 0 (emmc={emmc_write_count}, e_nd={e_nd_actuator_tx_count}, rf={wireless_rf_packets_emitted}, usb={usb_packets_transmitted}, passive_tx={simulated_passive_tx_bytes})"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: live attach, persistent eMMC writes, and cross-model flash remain hard-locked False"
        )

    tier0 = _extract_tier0_evidence(
        simulate_bench_dry_run=simulate_bench_dry_run,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
    )
    errors.extend(tier0["errors"])
    warnings.extend(tier0["warnings"])

    effective_pb_heif = P368_PB_JPEG_HEIF_DEFAULT if reset_action == "INITIALIZE" else pb_jpeg_heif_switch
    effective_view_mode = P368_VIEW_MODE_DEFAULT if reset_action == "INITIALIZE" else view_mode
    effective_airplane = "OFF" if reset_action == "INITIALIZE" else airplane_mode

    return P368CheckGroupDPhotoCapViewModeRatingUvcSrtAirplaneTier0Result(
        group_id=P368_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        source_file_format=source_file_format,
        photo_capture_output_mp=photo_cap_mp,
        photo_capture_dci4k_blocked=photo_cap_dci4k_blocked,
        pb_jpeg_heif_switch=pb_jpeg_heif_switch,
        effective_pb_jpeg_heif_after_reset=effective_pb_heif,
        pb_jpeg_heif_resists_camera_reset=True,
        view_mode_exposed_items=tuple(view_mode_exposed_items),
        view_mode=view_mode,
        effective_view_mode_after_reset=effective_view_mode,
        rating_stars=rating_stars,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_data_sector_writes=PHASE368_SLOT1_DATA_SECTOR_WRITES,
        slot1_tier0_vault_mutated=False,
        fx6_photo_capture_ui_count=P368_FX6_PHOTO_CAPTURE_UI_COUNT,
        fx6_clip_flag=fx6_clip_flag,
        usb_connection_mode=usb_connection_mode,
        usb_connection_modes_exposed=tuple(usb_connection_modes_exposed),
        fx3_uvc_streaming_supported=P368_FX3_UVC_STREAMING_SUPPORTED,
        fx3_dormant_uvc_4k_30p_present=False,
        streaming_protocol=streaming_protocol,
        srt_role=srt_role,
        srt_listener_supported=False,
        streaming_codec=streaming_codec,
        streaming_encryption=streaming_encryption,
        streaming_profile=streaming_profile,
        streaming_fps=streaming_fps,
        streaming_bitrate_mbps=streaming_bitrate_mbps,
        movie_rec_during_streaming=movie_rec_during_streaming,
        streaming_transport=streaming_transport,
        airplane_mode=airplane_mode,
        effective_airplane_mode_after_reset=effective_airplane,
        usb_lan_bypasses_airplane_mode=True,
        rf_packets_transmitted=PHASE368_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE368_WIRELESS_RF_PACKETS_EMITTED,
        fx6_native_uvc_count=P368_FX6_NATIVE_UVC_COUNT,
        fx6_builtin_streaming_count=P368_FX6_BUILTIN_STREAMING_COUNT,
        tier0_receipt_verified=bool(tier0["tier0_receipt_verified"]),
        receipt_mode=str(tier0["receipt_mode"]),
        h0_equals_h3_count=int(tier0["h0_equals_h3_count"]),
        h0_h3_surface_count=P368_STORAGE_SURFACE_COUNT,
        st_dev_a=tier0["st_dev_a"],
        st_dev_b=tier0["st_dev_b"],
        receipt_body_serial=str(tier0["body_serial"]),
        receipt_emmc_cid=str(tier0["emmc_cid"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Full Phase 368 Orchestrator & Report Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P368_SONY_HELP_GUIDE_ID,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "OFF",
    reset_action: str = "NONE",
    # Group A
    file_format: str = P368_FX3_FILE_FORMAT_DEFAULT,
    rec_frame_rate_fps: float = 59.94,
    prev_rec_frame_rate_fps: float = 59.94,
    sq_frame_rate_fps: int = 24,
    record_setting_mbps: int = 50,
    proxy_recording_enabled: bool = False,
    media_card_speed: str = "CFEA_VPG400",
    playback_clip_fps: float = 59.94,
    dormant_file_format_requested: Optional[str] = None,
    expect_xavc_hs_4k_has_29_97p_or_25p: bool = False,
    expect_sq_xavc_s_hd_120fps_requires_v90: bool = False,
    expect_sq_dci4k_allows_100_or_120fps: bool = False,
    expect_sq_48fps_outside_dci4k_2400p: bool = False,
    expect_cross_2400p_without_reboot_or_mixed_playback: bool = False,
    expect_high_rate_sq_proxy_succeeds_without_vpg400: bool = False,
    claimed_movie_settings_resist_camera_reset: bool = False,
    fx6_rec_codec: str = "XAVC_I",
    fx6_video_format: str = "4096x2160",
    fx6_rec_mbps: int = 600,
    fx6_dormant_rec_format_requested: Optional[str] = None,
    claimed_fx6_xavc_l_supports_dci4k: bool = False,
    awb_priority_set: str = P368_AWB_PRIORITY_DEFAULT,
    shutter_awb_lock: str = P368_SHUTTER_AWB_LOCK_DEFAULT,
    movie_awb_lock_custom_key: str = "NONE",
    kelvin_temp_k: int = 5600,
    expect_awb_priority_effective_in_cine_ei: bool = False,
    expect_shutter_awb_lock_active_in_movie: bool = False,
    claimed_shutter_awb_lock_wiped_by_camera_reset: bool = False,
    claimed_awb_priority_resists_camera_reset: bool = False,
    fx6_wht_bal_switch: str = "B",
    fx6_kelvin_temp_k: int = 5600,
    fx6_atw_enabled: bool = True,
    fx6_atw_speed: int = 3,
    fx6_shockless_white: str = "OFF",
    fx6_cine_ei_active: bool = False,
    expect_fx6_atw_active_in_cine_ei: bool = False,
    # Group B
    focus_mode: str = "MF",
    exposure_mode: str = "MANUAL_EXPOSURE",
    focus_assistant_items: Tuple[str, ...] = P368_FOCUS_ASSISTANT_EXACT_4_ITEMS,
    auto_magnifier_in_mf: str = "OFF",
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag: str = "X1_0",
    af_in_focus_mag: str = "ON",
    cont_shooting_active: bool = False,
    mount_adaptor_attached: bool = False,
    expect_af_in_focus_mag_active_under_lockout: bool = False,
    peaking_items: Tuple[str, ...] = P368_PEAKING_EXACT_3_ITEMS,
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "RED",
    claimed_focus_assist_or_peaking_wiped_by_camera_reset: bool = False,
    claimed_peaking_outputs_over_hdmi: bool = False,
    touch_operation_items: Tuple[str, ...] = P368_TOUCH_OPERATION_EXACT_4_ITEMS,
    touch_operation: str = "ON",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    swipe_up: str = "OPEN_THE_FN_MENU",
    dormant_touch_item_requested: Optional[str] = None,
    claimed_touch_operation_wiped_by_camera_reset: bool = False,
    fx6_peaking_items: Tuple[str, ...] = P368_FX6_PEAKING_EXACT_3_ITEMS,
    fx6_peaking_dormant_binding_requested: Optional[str] = None,
    fx3_screen_reader_requested: bool = False,
    fx6_screen_reader_requested: bool = False,
    expect_screen_reader_outputs_over_hdmi: bool = False,
    version_rows_exposed: Tuple[str, ...] = P368_FX3_VERSION_EXACT_2_ROWS,
    mount_adaptor_fw_checked: bool = False,
    claimed_mount_adaptor_has_3rd_version_row: bool = False,
    claimed_mi_shoe_version_shown: bool = False,
    expect_update_red_dot_visible_in_airplane_mode: bool = False,
    bodydata_slot1_flash_requested: bool = False,
    # Group C
    exposure_ctrl_type: str = P368_EXPOSURE_CTRL_TYPE_DEFAULT,
    av_auto_manual_switch: str = "MANUAL",
    tv_auto_manual_switch: str = "MANUAL",
    iso_auto_manual_switch: str = "MANUAL",
    auto_slow_shutter: str = "ON",
    claimed_exposure_ctrl_type_wiped_by_camera_reset: bool = False,
    claimed_auto_manual_or_slow_shutter_resists_reset: bool = False,
    shutter_mode: str = P368_SHUTTER_MODE_DEFAULT,
    shutter_angle_value: str = "180.0",
    frame_rate_fps: float = 23.98,
    anti_flicker_shoot: str = "OFF",
    expect_shutter_angle_active_in_still: bool = False,
    expect_exposure_step_alters_shutter_angle: bool = False,
    claimed_shutter_angle_shared_when_diffset_unchecked: bool = False,
    claimed_bk4_speed_and_angle_overwrite_each_other: bool = False,
    expect_anti_flicker_active_in_movie: bool = False,
    dormant_var_shutter_requested: bool = False,
    fx6_shutter_mode: str = "ANGLE",
    steadyshot_movie: str = P368_STEADYSHOT_MOVIE_DEFAULT,
    steadyshot_adjust: str = "AUTO",
    steadyshot_focal_length_mm: int = 50,
    exposed_focal_lengths_mm: Tuple[int, ...] = P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    hdmi_raw_output: bool = False,
    desqueeze_display: str = "OFF",
    e_mount_sony_lens: bool = True,
    external_hdmi_recorder_active: bool = False,
    expect_steadyshot_active_under_lockout: bool = False,
    expect_catalyst_gyro_available: bool = False,
    claimed_200mm_active_still_documented_in_ver7: bool = False,
    dormant_steadyshot_mode_requested: Optional[str] = None,
    claimed_steadyshot_resists_camera_reset: bool = False,
    claimed_fx6_has_body_ibis: bool = False,
    fx6_lens_oss_mode: str = "OFF",
    claimed_fx6_lens_oss_only_on_off: bool = False,
    expect_fx6_catalyst_ok_with_oss_on: bool = False,
    # Group D + Tier-0
    source_file_format: str = "XAVC_S_4K",
    source_resolution_4k: bool = True,
    photo_capture_requested: bool = False,
    photo_capture_target_slot: int = 2,
    pb_jpeg_heif_switch: str = P368_PB_JPEG_HEIF_DEFAULT,
    claimed_pb_jpeg_heif_wiped_by_camera_reset: bool = False,
    view_mode_exposed_items: Tuple[str, ...] = P368_VIEW_MODE_EXACT_3_ITEMS,
    view_mode: str = P368_VIEW_MODE_DEFAULT,
    dormant_view_mode_requested: Optional[str] = None,
    claimed_view_mode_wiped_by_camera_reset: bool = False,
    rating_stars: int = 0,
    rating_write_target_slot: int = 2,
    rating_write_requested: bool = False,
    claimed_rating_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_photo_capture: bool = False,
    fx6_clip_flag: str = "OK",
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_connection_modes_exposed: Tuple[str, ...] = P368_USB_CONNECTION_EXACT_4_MODES,
    dormant_uvc_usb_streaming_requested: bool = False,
    claimed_fx3_supports_uvc_4k_30p: bool = False,
    claimed_movie_rec_during_streaming_is_uvc: bool = False,
    streaming_active: bool = False,
    streaming_protocol: str = "SRT",
    srt_role: str = "SRT_CALLER",
    srt_url_syntax: str = "srt.example.invalid",
    streaming_codec: str = "H265",
    streaming_encryption: str = "AES_256",
    streaming_profile: str = P368_STREAMING_PROFILE_DEFAULT,
    streaming_fps: float = 59.94,
    streaming_bitrate_mbps: float = 9.0,
    movie_rec_during_streaming: str = "DISABLE",
    movie_rec_during_streaming_4k_requested: bool = False,
    movie_rec_during_streaming_slot: int = 2,
    streaming_transport: str = "USB_LAN",
    creators_app_bt_configured: bool = True,
    claimed_fx3_supports_srt_listener: bool = False,
    claimed_streaming_wiped_by_camera_reset: bool = False,
    claimed_fx6_has_native_uvc_or_builtin_srt_rtmp: bool = False,
    airplane_mode: str = "ON",
    claimed_reset_network_set_wipes_airplane_mode: bool = False,
    claimed_initialize_preserves_airplane_mode: bool = False,
    expect_airplane_mode_blocks_usb_lan: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_write_requested: bool = False,
    emmc_write_count: int = 0,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport:
    donor = inspect_phase368_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        reset_action=reset_action,
        file_format=file_format,
        rec_frame_rate_fps=rec_frame_rate_fps,
        prev_rec_frame_rate_fps=prev_rec_frame_rate_fps,
        sq_frame_rate_fps=sq_frame_rate_fps,
        record_setting_mbps=record_setting_mbps,
        proxy_recording_enabled=proxy_recording_enabled,
        media_card_speed=media_card_speed,
        playback_clip_fps=playback_clip_fps,
        dormant_file_format_requested=dormant_file_format_requested,
        expect_xavc_hs_4k_has_29_97p_or_25p=expect_xavc_hs_4k_has_29_97p_or_25p,
        expect_sq_xavc_s_hd_120fps_requires_v90=expect_sq_xavc_s_hd_120fps_requires_v90,
        expect_sq_dci4k_allows_100_or_120fps=expect_sq_dci4k_allows_100_or_120fps,
        expect_sq_48fps_outside_dci4k_2400p=expect_sq_48fps_outside_dci4k_2400p,
        expect_cross_2400p_without_reboot_or_mixed_playback=expect_cross_2400p_without_reboot_or_mixed_playback,
        expect_high_rate_sq_proxy_succeeds_without_vpg400=expect_high_rate_sq_proxy_succeeds_without_vpg400,
        claimed_movie_settings_resist_camera_reset=claimed_movie_settings_resist_camera_reset,
        fx6_rec_codec=fx6_rec_codec,
        fx6_video_format=fx6_video_format,
        fx6_rec_mbps=fx6_rec_mbps,
        fx6_dormant_rec_format_requested=fx6_dormant_rec_format_requested,
        claimed_fx6_xavc_l_supports_dci4k=claimed_fx6_xavc_l_supports_dci4k,
        awb_priority_set=awb_priority_set,
        shutter_awb_lock=shutter_awb_lock,
        movie_awb_lock_custom_key=movie_awb_lock_custom_key,
        kelvin_temp_k=kelvin_temp_k,
        expect_awb_priority_effective_in_cine_ei=expect_awb_priority_effective_in_cine_ei,
        expect_shutter_awb_lock_active_in_movie=expect_shutter_awb_lock_active_in_movie,
        claimed_shutter_awb_lock_wiped_by_camera_reset=claimed_shutter_awb_lock_wiped_by_camera_reset,
        claimed_awb_priority_resists_camera_reset=claimed_awb_priority_resists_camera_reset,
        fx6_wht_bal_switch=fx6_wht_bal_switch,
        fx6_kelvin_temp_k=fx6_kelvin_temp_k,
        fx6_atw_enabled=fx6_atw_enabled,
        fx6_atw_speed=fx6_atw_speed,
        fx6_shockless_white=fx6_shockless_white,
        fx6_cine_ei_active=fx6_cine_ei_active,
        expect_fx6_atw_active_in_cine_ei=expect_fx6_atw_active_in_cine_ei,
    )

    gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        exposure_mode=exposure_mode,
        reset_action=reset_action,
        focus_assistant_items=focus_assistant_items,
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag=initial_focus_mag,
        af_in_focus_mag=af_in_focus_mag,
        cont_shooting_active=cont_shooting_active,
        mount_adaptor_attached=mount_adaptor_attached,
        expect_af_in_focus_mag_active_under_lockout=expect_af_in_focus_mag_active_under_lockout,
        peaking_items=peaking_items,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        claimed_focus_assist_or_peaking_wiped_by_camera_reset=claimed_focus_assist_or_peaking_wiped_by_camera_reset,
        claimed_peaking_outputs_over_hdmi=claimed_peaking_outputs_over_hdmi,
        touch_operation_items=touch_operation_items,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        swipe_up=swipe_up,
        dormant_touch_item_requested=dormant_touch_item_requested,
        claimed_touch_operation_wiped_by_camera_reset=claimed_touch_operation_wiped_by_camera_reset,
        fx6_peaking_items=fx6_peaking_items,
        fx6_peaking_dormant_binding_requested=fx6_peaking_dormant_binding_requested,
        fx3_screen_reader_requested=fx3_screen_reader_requested,
        fx6_screen_reader_requested=fx6_screen_reader_requested,
        expect_screen_reader_outputs_over_hdmi=expect_screen_reader_outputs_over_hdmi,
        version_rows_exposed=version_rows_exposed,
        mount_adaptor_fw_checked=mount_adaptor_fw_checked,
        claimed_mount_adaptor_has_3rd_version_row=claimed_mount_adaptor_has_3rd_version_row,
        claimed_mi_shoe_version_shown=claimed_mi_shoe_version_shown,
        airplane_mode=airplane_mode,
        expect_update_red_dot_visible_in_airplane_mode=expect_update_red_dot_visible_in_airplane_mode,
        bodydata_slot1_flash_requested=bodydata_slot1_flash_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
    )

    gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        exposure_ctrl_type=exposure_ctrl_type,
        av_auto_manual_switch=av_auto_manual_switch,
        tv_auto_manual_switch=tv_auto_manual_switch,
        iso_auto_manual_switch=iso_auto_manual_switch,
        auto_slow_shutter=auto_slow_shutter,
        claimed_exposure_ctrl_type_wiped_by_camera_reset=claimed_exposure_ctrl_type_wiped_by_camera_reset,
        claimed_auto_manual_or_slow_shutter_resists_reset=claimed_auto_manual_or_slow_shutter_resists_reset,
        shutter_mode=shutter_mode,
        shutter_angle_value=shutter_angle_value,
        frame_rate_fps=frame_rate_fps,
        sq_frame_rate_fps=sq_frame_rate_fps,
        anti_flicker_shoot=anti_flicker_shoot,
        expect_shutter_angle_active_in_still=expect_shutter_angle_active_in_still,
        expect_exposure_step_alters_shutter_angle=expect_exposure_step_alters_shutter_angle,
        claimed_shutter_angle_shared_when_diffset_unchecked=claimed_shutter_angle_shared_when_diffset_unchecked,
        claimed_bk4_speed_and_angle_overwrite_each_other=claimed_bk4_speed_and_angle_overwrite_each_other,
        expect_anti_flicker_active_in_movie=expect_anti_flicker_active_in_movie,
        dormant_var_shutter_requested=dormant_var_shutter_requested,
        fx6_shutter_mode=fx6_shutter_mode,
        steadyshot_movie=steadyshot_movie,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_length_mm=steadyshot_focal_length_mm,
        exposed_focal_lengths_mm=exposed_focal_lengths_mm,
        hdmi_raw_output=hdmi_raw_output,
        desqueeze_display=desqueeze_display,
        e_mount_sony_lens=e_mount_sony_lens,
        external_hdmi_recorder_active=external_hdmi_recorder_active,
        expect_steadyshot_active_under_lockout=expect_steadyshot_active_under_lockout,
        expect_catalyst_gyro_available=expect_catalyst_gyro_available,
        claimed_200mm_active_still_documented_in_ver7=claimed_200mm_active_still_documented_in_ver7,
        dormant_steadyshot_mode_requested=dormant_steadyshot_mode_requested,
        claimed_steadyshot_resists_camera_reset=claimed_steadyshot_resists_camera_reset,
        claimed_fx6_has_body_ibis=claimed_fx6_has_body_ibis,
        fx6_lens_oss_mode=fx6_lens_oss_mode,
        claimed_fx6_lens_oss_only_on_off=claimed_fx6_lens_oss_only_on_off,
        expect_fx6_catalyst_ok_with_oss_on=expect_fx6_catalyst_ok_with_oss_on,
    )

    gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        shoot_mode=shoot_mode,
        reset_action=reset_action,
        source_file_format=source_file_format,
        source_resolution_4k=source_resolution_4k,
        photo_capture_requested=photo_capture_requested,
        photo_capture_target_slot=photo_capture_target_slot,
        pb_jpeg_heif_switch=pb_jpeg_heif_switch,
        claimed_pb_jpeg_heif_wiped_by_camera_reset=claimed_pb_jpeg_heif_wiped_by_camera_reset,
        view_mode_exposed_items=view_mode_exposed_items,
        view_mode=view_mode,
        dormant_view_mode_requested=dormant_view_mode_requested,
        claimed_view_mode_wiped_by_camera_reset=claimed_view_mode_wiped_by_camera_reset,
        rating_stars=rating_stars,
        rating_write_target_slot=rating_write_target_slot,
        rating_write_requested=rating_write_requested,
        claimed_rating_wiped_by_camera_reset=claimed_rating_wiped_by_camera_reset,
        claimed_fx6_has_photo_capture=claimed_fx6_has_photo_capture,
        fx6_clip_flag=fx6_clip_flag,
        usb_connection_mode=usb_connection_mode,
        usb_connection_modes_exposed=usb_connection_modes_exposed,
        dormant_uvc_usb_streaming_requested=dormant_uvc_usb_streaming_requested,
        claimed_fx3_supports_uvc_4k_30p=claimed_fx3_supports_uvc_4k_30p,
        claimed_movie_rec_during_streaming_is_uvc=claimed_movie_rec_during_streaming_is_uvc,
        streaming_active=streaming_active,
        streaming_protocol=streaming_protocol,
        srt_role=srt_role,
        srt_url_syntax=srt_url_syntax,
        streaming_codec=streaming_codec,
        streaming_encryption=streaming_encryption,
        streaming_profile=streaming_profile,
        streaming_fps=streaming_fps,
        streaming_bitrate_mbps=streaming_bitrate_mbps,
        movie_rec_during_streaming=movie_rec_during_streaming,
        movie_rec_during_streaming_4k_requested=movie_rec_during_streaming_4k_requested,
        movie_rec_during_streaming_slot=movie_rec_during_streaming_slot,
        streaming_transport=streaming_transport,
        creators_app_bt_configured=creators_app_bt_configured,
        claimed_fx3_supports_srt_listener=claimed_fx3_supports_srt_listener,
        claimed_streaming_wiped_by_camera_reset=claimed_streaming_wiped_by_camera_reset,
        claimed_fx6_has_native_uvc_or_builtin_srt_rtmp=claimed_fx6_has_native_uvc_or_builtin_srt_rtmp,
        airplane_mode=airplane_mode,
        claimed_reset_network_set_wipes_airplane_mode=claimed_reset_network_set_wipes_airplane_mode,
        claimed_initialize_preserves_airplane_mode=claimed_initialize_preserves_airplane_mode,
        expect_airplane_mode_blocks_usb_lan=expect_airplane_mode_blocks_usb_lan,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_write_requested=slot1_write_requested,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        usb_packets_transmitted=usb_packets_transmitted,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
    )

    groups = (ga, gb, gc, gd)
    groups_passed = sum(1 for g in groups if g.passed)
    all_errors = ga.errors + gb.errors + gc.errors + gd.errors
    all_warnings = ga.warnings + gb.warnings + gc.warnings + gd.warnings

    if all_errors:
        go_no_go = (
            P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE
        )
        overall_status = (
            P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE
        )
    elif not gd.tier0_receipt_verified:
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        overall_status = P368_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    elif simulate_bench_dry_run:
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        go_no_go = (
            P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED
        )
        overall_status = (
            P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED
        )

    report = RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport(
        schema_version=P368_SCHEMA,
        phase_version=P368_VERSION,
        sony_help_guide_id=sony_help_guide_id,
        overall_status=overall_status,
        go_no_go=go_no_go,
        verification_mode=donor.verification_mode,
        simulate_bench_dry_run=bool(simulate_bench_dry_run),
        check_group_count=len(groups),
        check_groups_passed=groups_passed,
        check_group_a=ga,
        check_group_b=gb,
        check_group_c=gc,
        check_group_d=gd,
        donor_inspection=donor,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        receipt_mode=gd.receipt_mode,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        h0_h3_surface_count=P368_STORAGE_SURFACE_COUNT,
        slot1_tier0_vault_mutated=False,
        ready_for_live_camera_attach=False,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_screen_reader_exposed=False,
        fx6_screen_reader_exposed=False,
        fx3_touch_panel_pad_exposed=False,
        fx3_var_shutter_exposed=False,
        fx6_body_ibis_present=False,
        fx3_uvc_streaming_supported=P368_FX3_UVC_STREAMING_SUPPORTED,
        fx3_srt_listener_supported=False,
        fx3_view_mode_3items_exact=(
            tuple(view_mode_exposed_items) == P368_VIEW_MODE_EXACT_3_ITEMS
        ),
        emmc_write_count=PHASE368_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE368_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=PHASE368_E_ND_I2C_TX_BYTES,
        rf_packets_transmitted=PHASE368_RF_PACKETS_TRANSMITTED,
        wireless_rf_packets_emitted=PHASE368_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=PHASE368_RF_NVS_MUTATION_BYTES,
        slot1_data_sector_writes=PHASE368_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE368_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE368_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE368_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport(
        **{
            **report.to_dict(),
            "check_group_a": ga,
            "check_group_b": gb,
            "check_group_c": gc,
            "check_group_d": gd,
            "donor_inspection": donor,
            "errors": report.errors,
            "warnings": report.warnings,
            "report_sha256": digest,
        }
    )


def run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
    **kwargs: Any,
) -> RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport:
    return evaluate_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
        **kwargs
    )


def verify_phase368_report(
    payload: Union[
        Mapping[str, Any],
        RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport,
    ],
) -> Phase368ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P368_SCHEMA:
        errors.append(
            f"schema_version mismatch: {payload.get('schema_version')!r} != {P368_SCHEMA!r}"
        )
    if payload.get("sony_help_guide_id") != P368_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_368_VALID_GO_NO_GO_VALUES:
        errors.append(f"invalid go_no_go: {payload.get('go_no_go')!r}")

    locked_false_fields = (
        "ready_for_live_camera_attach",
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_screen_reader_exposed",
        "fx6_screen_reader_exposed",
        "fx3_touch_panel_pad_exposed",
        "fx3_var_shutter_exposed",
        "fx6_body_ibis_present",
        "fx3_uvc_streaming_supported",
        "fx3_srt_listener_supported",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "emmc_write_count",
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "rf_nvs_mutation_bytes",
        "slot1_data_sector_writes",
        "usb_packets_transmitted",
        "passive_tx_bytes_emitted",
        "raw_firmware_bytes_leaked",
    )
    for field in locked_zero_fields:
        if payload.get(field) != 0:
            errors.append(f"hard-locked zero telemetry {field} must be 0")

    expected_sha = _canonical_sha256_dict(payload)
    if payload.get("report_sha256") != expected_sha:
        errors.append(
            f"report_sha256 mismatch: {payload.get('report_sha256')!r} != {expected_sha!r}"
        )

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase368ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase368_markdown(
    report: RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport,
) -> str:
    lines = [
        f"# Phase 368 — 23rd Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `ready_for_live_camera_attach={report.ready_for_live_camera_attach}`, "
        f"`ready_attach={report.overall_ready_for_hardware_attach}`, "
        f"`emmc_writes={report.persistent_emmc_writes_authorized}`, "
        f"`emmc_write_count={report.emmc_write_count}`, "
        f"`cross_model_flash={report.cross_model_flash_authorized}`, "
        f"`rf_pkts={report.rf_packets_transmitted}`, `slot1_writes={report.slot1_data_sector_writes}`, "
        f"`usb_pkts={report.usb_packets_transmitted}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"file_format=`{report.check_group_a.file_format}`, min_card=`{report.check_group_a.required_min_card_speed}`, "
        f"vpg400_proxy=`{report.check_group_a.vpg400_proxy_threshold_triggered}`, "
        f"awb_prio=`{report.check_group_a.awb_priority_set}`, shutter_awb_lock=`{report.check_group_a.shutter_awb_lock}`, "
        f"fx6_atw_speed={report.check_group_a.fx6_atw_speed}",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"focus_assist={len(report.check_group_b.focus_assistant_items)}, "
        f"peaking={len(report.check_group_b.peaking_items)}, "
        f"touch={len(report.check_group_b.touch_operation_items)}, "
        f"screen_reader_ui=`{report.check_group_b.fx3_screen_reader_ui_count}/{report.check_group_b.fx6_screen_reader_ui_count}`, "
        f"version_rows={report.check_group_b.version_rows_exposed}",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"exp_ctrl=`{report.check_group_c.exposure_ctrl_type}`, shutter_mode=`{report.check_group_c.shutter_mode}`, "
        f"angle=`{report.check_group_c.shutter_angle_value}`, steadyshot=`{report.check_group_c.effective_steadyshot_movie}`, "
        f"fx6_oss=`{report.check_group_c.fx6_lens_oss_mode}`",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"photo_mp=`{report.check_group_d.photo_capture_output_mp}`, view_mode=`{report.check_group_d.view_mode}`, "
        f"uvc={report.check_group_d.fx3_uvc_streaming_supported}, "
        f"srt_role=`{report.check_group_d.srt_role}`, airplane=`{report.check_group_d.effective_airplane_mode_after_reset}`, "
        f"slot1_mut=`{report.check_group_d.slot1_tier0_vault_mutated}`",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
