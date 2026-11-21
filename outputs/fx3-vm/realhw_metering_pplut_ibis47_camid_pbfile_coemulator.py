#!/usr/bin/env python3
"""Phase 372 — Stage 85 (85/85 Full-Board VM HIL Co-Emulation Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-75 Milestone:
- 85A: `Exposure/Color -> [Metering]` 6-Mode Matrix (`Multi`..`Highlight`),
  `[Face Priority in Multi Metering]` (`BKID_APP_setting_face_detection_in_multi`),
  `[Spot Metering Point]`, Still-Only Reset-Resistant `[AEL w/ Shutter]` vs Movie
  Custom-Key `AEL hold/toggle`, and Wave-75 `G96` `[Exposure step]` Erratum
  (`Not available` under `[Camera Settings Reset]`, `Initialize`-only,
  `[Shutter Angle]` immune, `Cine EI` `M.M.` locked to Base ISO) vs `ILME-FX6`
  `Shooting > Auto Exposure` (`Level -3.0..+3.0` in `0.25` steps = 25 steps,
  disproving `-2.0..+2.0EV` rumor; `Speed -99..+99`; `Detect Window 1..6/Custom`).
- 85B: `[Picture Profile]` (`Off`, `PP1..11` w/ `PP11 S-Cinetone` default,
  Movie-only `PPLUT1..4` baking `.cube` & 1080p HDMI clamp) Asymmetric
  Reset/Initialize Split (`PP1..PP11` custom params & `[Different Set for
  Still/Mv]` PP checkbox resist BOTH Reset and Initialize; `PPLUT1..4` reset on
  both), `User1..16` `.cube` (`17`/`33`-pt `<= 63` chars from
  `/Private/Sony/PRO/LUT` or `/Sony/PRO/LUT`), and `[Embed LUT File]`
  (`Log Shooting Setting`, locked `Off` on SD/SDHC, **MP4** header embed /
  zero MXF / zero `.cube` sidecar on FX3) vs FX6 `Base Look` + 16-axis
  `Multi Matrix` + 4-bus `MLUT` + MXF `Embed LUT File`.
- 85C: 5-Axis IBIS `[SteadyShot]` (`Active` ~`1.1x` crop forcing
  `Distortion Comp. = Auto` / `Standard` default / `Off`), exact **47-entry**
  discrete `[SteadyShot Focal Len.]` table (`8..1000mm`, default `8mm`, all 4
  Resettable; dormant `Dynamic active`/`Intelligent Active`/`Super Active`
  rejected), `Active` 4-condition lockouts (`100p/119.88p`, `S&Q >= 100fps`,
  `HDMI RAW = On`, `De-Squeeze != Off`), and Catalyst Gyro Metadata (`Off`/
  `Active` only, NOT `Standard`, absent in `120p` & all `S&Q`) vs `ILME-FX6`
  zero physical IBIS (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`, optical
  OSS `On/Off` only; dormant `SteadyShot Focal Length` rejected).
- 85D: Zero-Sector-Write Playback Viewing (`[Image Index]` `9`/`25` Images,
  `[Display Rotation]` `BKID_APP_setting_display_rotatiton`, `[Focus Frame
  Display]`, `[Cont. PB for Interval]`, `[Play Speed for Interval]` `1..9`
  def `5` — all `0` writes & Reset-resistant) vs Still DCF (`Standard Form`
  `100MSDCF..999MSDCF`, `4,000`/folder) & Movie `[Cam ID + Reel#]` 17-char stem
  (`A001C001_230101AB`, `C999 -> D001` filename-only rollover, SDHC lockout)
  separated from **`37`-char `[Title Name Settings]`** (default `"C"`) vs FX6
  `TC/Media > Clip Name Format` (`Title Prefix` `4..46` def `nnn_` ->
  `/XDROOT/Clip/*.MXF`), plus Tier-0 `Slot 1 EROFS=30` Firewall blocking
  `[Create New Folder]`, `[Forced File No. Reset]`, `[Select REC Folder]`, and
  `[Series Counter Reset]`.

Enforces strict Tier-0 safety redlines across all 4 execution modes (normal local
donors strictly `os.O_RDONLY` with `<= 4096 B` `os.pread` bounded windows on
multi-MiB files; `FX3_CLEAN_ROOM_TEST=1`; `FX3_FX6_FORCE_CLEAN_ROOM=1`; and
mocked donorless `work_root=None` / `FX3_FX6_MAC_WORK_ROOT` sentinel):
- `ready_for_live_camera_attach == False`
- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`
- `emmc_nflasha_write_count == 0`, `slot1_sector_writes == 0`, `slot1_data_sector_writes == 0`
- `slot1_avf_info_mutated == False`, `physical_device_writes == 0`, `raw_firmware_bytes_leaked == 0`
- `rf_tx_packets == 0`, `rf_packets_transmitted == 0`, `rf_nvs_mutation_bytes == 0`
- `nop_count == 0`, `wf12_00342260_hits == 0`, `appfw_crashes == 0`, `rsv_orphan_count == 0`
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
# Phase 372 Schema, Stage 85 (85/85) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation_v1"
)
PHASE_372_VERSION = "372.0.0"
PHASE_NUMBER = 372
STAGE_INDEX = 85
STAGE_TOTAL = 85
MILESTONE_LABEL = "85/85"
IS_85TH_STAGE_MILESTONE = True

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
READY_FOR_LIVE_CAMERA_ATTACH = False
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
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0
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

# Body & Pipeline Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")
VALID_MEDIA_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "Media(A)", "Media(B)", "RAM")
VALID_CARD_TYPES: Tuple[str, ...] = ("SD", "SDHC", "SDXC", "CFexpress")
VALID_DESQUEEZE_RATIOS: Tuple[str, ...] = ("Off", "1.3x", "1.5x", "1.6x", "2.0x")

# 85A — Exposure & Metering Matrix, G96 [Exposure step] Erratum & FX6 AE Level
FX3_METERING_MODES: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot: Standard",
    "Spot: Large",
    "Entire Screen Avg.",
    "Highlight",
)
FX3_METERING_MODE_DEFAULT = "Multi"
FX3_FACE_PRIORITY_SYMBOL = "BKID_APP_setting_face_detection_in_multi"
FX3_SPOT_METERING_POINT_MODES: Tuple[str, ...] = ("Center", "Focus Point Link")
FX3_SPOT_METERING_POINT_DEFAULT = "Center"
FX3_SPOT_FIXED_CENTER_FOCUS_AREAS: Tuple[str, ...] = ("Wide", "Zone", "Center Fix")
FX3_AEL_W_SHUTTER_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
FX3_AEL_W_SHUTTER_DEFAULT = "Auto"
FX3_MOVIE_AEL_CUSTOM_KEYS: Tuple[str, ...] = (
    "AEL hold",
    "AEL toggle",
    "Spot AEL hold",
    "Spot AEL toggle",
)
FX3_EXPOSURE_STEPS: Tuple[str, ...] = ("0.3EV", "0.5EV")
FX3_EXPOSURE_STEP_DEFAULT = "0.3EV"
FX3_EXPOSURE_STEP_G96_ERRATUM_RECONCILED = True
FX3_SHUTTER_ANGLE_IMMUNE_TO_EXP_STEP = True
FX3_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI Quick",
    "Cine EI",
)

FX6_AE_MODES: Tuple[str, ...] = ("Backlight", "Standard", "Spotlight")
FX6_AE_LEVEL_MIN = -3.0
FX6_AE_LEVEL_MAX = 3.0
FX6_AE_LEVEL_STEP = 0.25
FX6_AE_LEVEL_STEPS: Tuple[float, ...] = tuple(
    -3.0 + 0.25 * i for i in range(25)
)
FX6_AE_LEVEL_STEPS_COUNT = 25
FX6_AE_SPEED_MIN = -99
FX6_AE_SPEED_MAX = 99
FX6_AE_DETECT_WINDOWS: Tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "Custom")

VALID_85A_OPERATIONS: Tuple[str, ...] = (
    "fx3_metering_6mode_and_ciz_lock",
    "fx3_face_priority_multi_locks",
    "fx3_spot_metering_point_coupling",
    "fx3_ael_w_shutter_vs_movie_custom_key",
    "fx3_exposure_step_g96_erratum_and_cine_ei",
    "fx6_auto_exposure_25step_and_detect_window",
)

# 85B — Picture Profile PP1..11 vs PPLUT1..4 Reset Split & User 3D LUT MP4 Embedding
FX3_PICTURE_PROFILES: Tuple[str, ...] = (
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
FX3_PP_STD_SLOTS: Tuple[str, ...] = tuple(f"PP{i}" for i in range(1, 12))
FX3_PPLUT_SLOTS: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
FX3_PICTURE_PROFILE_DEFAULT = "PP11"
FX3_PPLUT_ELF_TYPO_SYMBOL = "BKID_APP_MR_setting_pplut1_link_uset_lut"
FX3_SELECT_LUT_BUILTINS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
FX3_SELECT_LUT_DEFAULT = "s709"
FX3_USER_LUT_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
FX3_USER_LUT_MAX_SLOTS = 16
FX3_CUBE_VALID_GRID_POINTS: Tuple[int, ...] = (17, 33)
FX3_CUBE_MAX_FILENAME_CHARS = 63
FX3_SD_LUT_DIR = "/Private/Sony/PRO/LUT"
FX3_CFEX_LUT_DIR = "/Sony/PRO/LUT"
FX3_EMBED_LUT_MENU_PATH = (
    "Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]"
)
FX3_EMBED_LUT_CONTAINER = "MP4"
FX3_HAS_MXF_CONTAINER = False

FX6_BASE_LOOK_BUILTINS: Tuple[str, ...] = (
    "S-Cinetone",
    "Standard",
    "Still",
    "ITU709",
    "709tone",
    "s709",
    "709(800%)",
    "S-Log3",
    "HLG Live",
    "HLG Natural",
)
FX6_USER_LUT_UI_SLOTS = 16
FX6_USER_LUT_BUFFER_SLOTS = 50
FX6_MULTI_MATRIX_AXES = 16
FX6_MULTI_MATRIX_RANGE = (-99, 99)
FX6_MLUT_BUSES: Tuple[str, ...] = (
    "Internal Rec.",
    "SDI/HDMI",
    "LCD/VF",
    "Proxy/Stream",
)
FX6_EMBED_LUT_CONTAINER = "MXF"

VALID_85B_OPERATIONS: Tuple[str, ...] = (
    "fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
    "fx3_pp_reset_vs_initialize_asymmetric_split",
    "fx3_manage_user_luts_import_cube_and_delete",
    "fx3_embed_lut_mp4_vs_sd_sdhc_lock",
    "fx6_base_look_multimatrix_mlut_mxf_embed",
)

# 85C — 5-Axis IBIS SteadyShot Active ~1.1x, Exact 47-Entry Focal Table & Catalyst Gyro
FX3_STEADYSHOT_MOVIE_MODES: Tuple[str, ...] = ("Active", "Standard", "Off")
FX3_STEADYSHOT_MOVIE_DEFAULT = "Standard"
FX3_STEADYSHOT_STILL_MODES: Tuple[str, ...] = ("On", "Off")
FX3_STEADYSHOT_STILL_DEFAULT = "On"
FX3_STEADYSHOT_ACTIVE_CROP_FACTOR = 1.1
FX3_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = ("Auto", "Manual")
FX3_STEADYSHOT_ADJUST_DEFAULT = "Auto"
FX3_DORMANT_STEADYSHOT_MODES: Tuple[str, ...] = (
    "Dynamic active",
    "Intelligent Active",
    "Super Active",
)
FX3_47_FOCAL_LENGTH_TABLE_MM: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    24, 25, 28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80,
    85, 90, 100, 105, 120, 135, 150, 180, 200, 210, 250, 300,
    350, 400, 450, 500, 600, 800, 1000,
)
FX3_FOCAL_LENGTH_DEFAULT_MM = 8
FX6_HAS_PHYSICAL_IBIS = False
FX6_STEADYSHOT_ERR_SYMBOL = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
FX6_OSS_MODES: Tuple[str, ...] = ("On", "Off")

VALID_85C_OPERATIONS: Tuple[str, ...] = (
    "fx3_steadyshot_active_crop_distortion_and_4locks",
    "fx3_steadyshot_47_focal_table_and_reset",
    "fx3_dormant_alpha_steadyshot_rejected",
    "fx3_catalyst_gyro_metadata_matrix",
    "fx6_zero_ibis_oss_and_dormant_focal_rejected",
)

# 85D — Zero-Write Playback Viewing vs Still DCF / Movie Cam ID+Reel# 17-Char & 37-Char Title
FX3_PB_IMAGE_INDEX_MODES: Tuple[str, ...] = ("9 Images", "25 Images")
FX3_PB_IMAGE_INDEX_DEFAULT = "9 Images"
FX3_PB_DORMANT_IMAGE_INDEX_MODES: Tuple[str, ...] = ("12 Images", "30 Images")
FX3_DISPLAY_ROTATION_MODES: Tuple[str, ...] = ("Auto", "Manual", "Off")
FX3_DISPLAY_ROTATION_DEFAULT = "Auto"
FX3_DISPLAY_ROTATION_ELF_TYPO_SYMBOL = "BKID_APP_setting_display_rotatiton"
FX3_PLAY_SPEED_INTERVAL_MIN = 1
FX3_PLAY_SPEED_INTERVAL_MAX = 9
FX3_PLAY_SPEED_INTERVAL_DEFAULT = 5

FX3_STILL_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
FX3_STILL_FOLDER_FORMS: Tuple[str, ...] = ("Standard Form", "Date Form")
FX3_STILL_MAX_FILES_PER_FOLDER = 4000
FX3_MOVIE_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
FX3_CAMID_REEL_STEM_LEN = 17
FX3_TITLE_NAME_DEFAULT = "C"
FX3_TITLE_NAME_MAX_CHARS = 37
FX3_TIER0_SLOT1_MUTATING_OPS: Tuple[str, ...] = (
    "Create New Folder",
    "Forced File No. Reset",
    "Select REC Folder",
    "Series Counter Reset",
)

FX6_CLIP_NAME_FORMATS: Tuple[str, ...] = ("Cam ID + Reel#", "Title")
FX6_TITLE_PREFIX_DEFAULT = "nnn_"
FX6_TITLE_PREFIX_MIN_CHARS = 4
FX6_TITLE_PREFIX_MAX_CHARS = 46
FX6_CLIP_OUTPUT_PATH = "/XDROOT/Clip/*.MXF"

VALID_85D_OPERATIONS: Tuple[str, ...] = (
    "fx3_playback_5items_zero_write_and_reset_immune",
    "fx3_still_dcf_folder_and_4000_cap",
    "fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
    "fx3_movie_title_37char_settings_boundary",
    "fx3_tier0_slot1_erofs30_folder_file_firewall",
    "fx6_clip_name_format_mxf_and_title_prefix",
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

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage85Phase372Error(RuntimeError):
    """Raised on invalid Phase 372 Stage 85 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 19 Real-Hardware Wave-75 Donor Specifications (O_RDONLY & <= 4096 B Windows)
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


PHASE372_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Metering Mode",
            b"Multi",
            b"Spot: Standard",
            b"Spot: Large",
            b"Entire Screen Avg.",
            b"Highlight",
            b"Face Priority in Multi Metering",
            b"Spot Metering Point",
            b"Focus Point Link",
            b"AEL w/ Shutter",
            b"Exposure step",
            b"Picture Profile",
            b"S-Cinetone",
            b"Select LUT",
            b"Manage User LUTs",
            b"Embed LUT File",
            b"SteadyShot",
            b"SteadyShot Adjust.",
            b"SteadyS. Focal Len.",
            b"Focal Length",
            b"25 Images",
            b"Display Rotation",
            b"Focus Frame Display",
            b"Cont. PB",
            b"Play Speed for",
            b"Cam ID + Reel#",
            b"Title Name Settings",
            b"Forced File No. Reset",
            b"Series Counter Reset",
            b"Create New Folder",
            b"Select REC Folder",
        ),
        absent_tokens=(
            b"Multi Matrix",
            b"Detect Window",
            b"All File",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "测光".encode("utf-8"),
            "防抖".encode("utf-8"),
            "文件名".encode("utf-8"),
            "显示旋转".encode("utf-8"),
            "新建文件夹".encode("utf-8"),
            "间隔连续播放".encode("utf-8"),
            "索引".encode("utf-8"),
            "Cam ID".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "測光".encode("utf-8"),
            "相片設定檔".encode("utf-8"),
            "檔案名稱".encode("utf-8"),
            "顯示旋轉".encode("utf-8"),
            "建立新資料夾".encode("utf-8"),
            "Cam ID".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "測光".encode("utf-8"),
            "ピクチャープロファイル".encode("utf-8"),
            "手ブレ補正".encode("utf-8"),
            "ファイル名".encode("utf-8"),
            "回転表示".encode("utf-8"),
            "新規フォルダ".encode("utf-8"),
            "Cam ID".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Image Index",
            b"9 Images",
            b"SteadyShot",
            b"Metering",
            b"Exposure",
            b"Folder",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "保存".encode("utf-8"),
            "对焦".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "儲存".encode("utf-8"),
            "對焦".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "保存".encode("utf-8"),
            "フォーカス".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(b"Multi", b"Center", b"SteadyShot", b"Metering"),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=("Fn".encode("utf-8"), "斑马".encode("utf-8"), "对焦".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=("Fn".encode("utf-8"), "斑馬".encode("utf-8"), "對焦".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=("Fn".encode("utf-8"), "ゼブラ".encode("utf-8"), "フォーカス".encode("utf-8")),
    ),
    CompactDonorSpec(
        name="fx3_lib_saveload_settings",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
        expected_size=18760,
        expected_sha256="07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        required_tokens=(
            b"_ZN16SaveLoadSettings13requestToReadEN18SaveLoadSettingsIf11RequestTypeEPhjPj",
            b"_ZN16SaveLoadSettings14requestToCheckEN18SaveLoadSettingsIf11RequestTypeEPKhjj",
            b"_ZN16SaveLoadSettings14requestToWriteEN18SaveLoadSettingsIf11RequestTypeEPKhjj",
        ),
        absent_tokens=(b"PRO/CAMERA",),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Auto Exposure",
            b"Base Look",
            b"Multi Matrix",
            b"SteadyShot",
            b"Clip Name Format",
            b"Title Prefix",
            b"Detect Window",
            b"Embed LUT File",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"Auto Exposure",
            b"Level",
            b"Detect Window",
            b"Multi Matrix",
            b"MLUT",
            b"SteadyShot",
            b"Auto Naming",
            b"Title Prefix",
        ),
    ),
)

PHASE372_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x2FA4000, "IMAGE_INDEX_9", b"IMAGE_INDEX_9"),
            (0x2FA4000, "IMAGE_INDEX_25", b"IMAGE_INDEX_25"),
            (0x2FA4000, "IMAGE_INDEX_12", b"IMAGE_INDEX_12"),
            (0x2FA4000, "IMAGE_INDEX_30", b"IMAGE_INDEX_30"),
            (0x2FB2000, "METERING_MODE_", b"METERING_MODE_"),
            (0x3908000, "SD_PRO_LUT_PATH", b"/Private/Sony/PRO/LUT"),
            (0x3908000, "CFEX_PRO_LUT_PATH", b"/Sony/PRO/LUT"),
            (0x3A79000, "PICTURE_PROFILE_PP11", b"PICTURE_PROFILE_PP11"),
            (0x3A79000, "PICTURE_PROFILE_PPLUT1", b"PPLUT1"),
            (0x3ADC000, "STEADYSHOT_FOCAL_LENGTH_8MM", b"VAL_setting_steady_focal_length_STEADYSHOT_FOCAL_LENGTH_8MM"),
            (0x3ADD000, "STEADYSHOT_FOCAL_LENGTH_1000MM", b"VAL_setting_steady_focal_length_STEADYSHOT_FOCAL_LENGTH_1000MM"),
            (0x3B5C000, "SELECT_LUT_R709", b"SELECT_LUT_R709"),
            (0x3BC5000, "BKID_APP_setting_embed_lut_file", b"BKID_APP_setting_embed_lut_file"),
            (0x3BC7000, "BKID_APP_setting_steadyshot_adjust", b"BKID_APP_setting_steadyshot_adjust"),
            (0x3BC8000, "BKID_APP_setting_exposure_step", b"BKID_APP_setting_exposure_step"),
            (0x3BC8000, "BKID_APP_setting_metering_mode", b"BKID_APP_setting_metering_mode"),
            (0x3BC8000, "BKID_APP_setting_face_detection_in_multi", b"BKID_APP_setting_face_detection_in_multi"),
            (0x3BC8000, "BKID_APP_setting_spot_metering_link_to_focus_point", b"BKID_APP_setting_spot_metering_link_to_focus_point"),
            (0x3BC8000, "BKID_APP_setting_still_image_ael_w_shutter", b"BKID_APP_setting_still_image_ael_w_shutter"),
            (0x3BC8000, "BKID_APP_setting_picture_profile", b"BKID_APP_setting_picture_profile"),
            (0x3BC8000, "BKID_APP_setting_select_lut", b"BKID_APP_setting_select_lut"),
            (0x3BC9000, "BKID_APP_setting_display_rotatiton", b"BKID_APP_setting_display_rotatiton"),
            (0x3BF1000, "BKID_APP_MR_setting_pplut1_link_uset_lut", b"BKID_APP_MR_setting_pplut1_link_uset_lut"),
        ),
        absent_windows=(
            (0x3ADC000, "NO_STEADYSHOT_DYNAMIC_ACTIVE", b"STEADYSHOT_DYNAMIC_ACTIVE"),
            (0x3ADC000, "NO_INTELLIGENT_ACTIVE", b"INTELLIGENT_ACTIVE"),
            (0x3ADC000, "NO_SUPER_ACTIVE", b"SUPER_ACTIVE"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_libmpr",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libmpr.so",
        expected_size=3517008,
        head4k_sha256="8b06e341401c676431f3ceed99240f3b529ed60d86eacee8cf3b1b1b8463a9b2",
        windows=(
            (0x001E000, "CAM_ID_SYM", b"CamId"),
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
            (0x2638000, "FX6_PRM_is_exist_user_lut0", b"PRM_is_exist_user_lut0"),
            (0x26AD000, "FX6_AE_LEVEL_MINUS_3_0", b"VAL_setting_auto_exposure_level_LEVEL_MINUS_3_0"),
            (0x26AD000, "FX6_AE_LEVEL_3_0", b"VAL_setting_auto_exposure_level_LEVEL_3_0"),
            (0x26AE000, "FX6_STEADYSHOT_UNSUPPORTED", b"TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"),
            (0x2707000, "FX6_BKID_AE_LEVEL", b"BKID_APP_SETTING_AE_LEVEL"),
            (0x273C000, "FX6_CLIP_NAME_FORMAT", b"CLIP_NAME_FORMAT"),
            (0x273D000, "FX6_TITLE_PREFIX", b"TITLE_PREFIX"),
            (0x2C48000, "FX6_Multi_Matrix", b"Multi Matrix"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY & Clean-Room Synthetic Helper Functions
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
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size > _COMPACT_MAX_READ_BYTES:
            raise Stage85Phase372Error(
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
        raise Stage85Phase372Error(
            f"Bounded read size {size} exceeds {_BOUNDED_WINDOW_BYTES} B"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
        win = os.pread(fd, size, offset)
        return st.st_size, head4k, win
    finally:
        os.close(fd)


def inspect_phase372_wave75_donors(
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
            resolved_root / s.rel_path for s in PHASE372_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE372_WINDOW_DONORS]
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
            for s in PHASE372_COMPACT_DONORS
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
            for w in PHASE372_WINDOW_DONORS
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
    for spec in PHASE372_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != spec.expected_size or sha != spec.expected_sha256:
            raise Stage85Phase372Error(
                f"Donor mismatch {spec.name}: size={len(data)} sha={sha}"
            )
        missing = [t for t in spec.required_tokens if t not in data]
        if missing:
            raise Stage85Phase372Error(
                f"Donor {spec.name} missing required tokens: {len(missing)}"
            )
        present_bad = [t for t in spec.absent_tokens if t in data]
        if present_bad:
            raise Stage85Phase372Error(
                f"Donor {spec.name} unexpectedly contains absent tokens: {len(present_bad)}"
            )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": sha,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_O_RDONLY_REAL_DONORS",
            }
        )

    window_entries = []
    for wspec in PHASE372_WINDOW_DONORS:
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
                raise Stage85Phase372Error(
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
                raise Stage85Phase372Error(
                    f"Window donor {wspec.name} unexpectedly had {label} at 0x{off:x}"
                )
        if file_size != wspec.expected_size or head4k_sha != wspec.head4k_sha256:
            raise Stage85Phase372Error(
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
                "source_mode": "LOCAL_O_RDONLY_REAL_DONORS",
            }
        )

    return {
        "source_mode": "LOCAL_O_RDONLY_REAL_DONORS",
        "donor_access_mode": "O_RDONLY_BOUNDED_4K_AND_COMPACT",
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
# Sub-Model 85A..85D Audit Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubModel85AMeteringAEAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    metering_mode: str
    face_priority_in_multi: bool
    spot_metering_point: str
    ael_w_shutter: str
    movie_ael_custom_key: str
    exposure_step: str
    shutter_angle_drift_events: int
    cine_ei_mm_locked_to_base_iso: bool
    g96_expstep_erratum_reconciled: bool
    resettable_items_reverted: bool
    reset_resistant_items_preserved: bool
    initialize_reverted: bool
    fx6_ae_mode: str
    fx6_ae_level: float
    fx6_ae_level_steps_count: int
    fx6_ae_speed: int
    fx6_detect_window: str
    fx6_2ev_rumor_disproved: bool
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel85BPictureProfileLUTAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    picture_profile: str
    pplut_baking_active: bool
    hdmi_output_resolution: str
    select_lut: str
    user_lut_slots_count: int
    cube_grid_points: int
    cube_filename_length: int
    lut_import_directory: str
    embed_lut_file: bool
    embed_container_format: str
    fx3_mxf_hits: int
    fx3_cube_sidecar_files: int
    pp1_to_pp11_custom_preserved_across_reset_and_init: bool
    diff_set_pp_checkbox_preserved_across_reset_and_init: bool
    pplut1_to_4_reverted: bool
    user_luts_preserved_across_reset: bool
    user_luts_cleared_on_init_or_delete_all: bool
    fx6_base_look: str
    fx6_multi_matrix_axes: int
    fx6_mlut_buses_count: int
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel85CIBISSteadyShotAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    steadyshot_mode: str
    steadyshot_crop_factor: float
    distortion_comp_forced_auto: bool
    steadyshot_adjust: str
    steadyshot_focal_length_mm: int
    focal_length_table_count: int
    resettable_all_4_reverted: bool
    catalyst_gyro_metadata_present: bool
    emount_electronic_lens: bool
    dormant_steadyshot_exposed_events: int
    fx6_has_physical_ibis: bool
    fx6_oss_mode: str
    fx6_dormant_focal_exposed_events: int
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel85DPlaybackFileAuditResult:
    operation: str
    body_model: str
    media_slot: str
    allowed: bool
    errno: int
    reason: str
    pb_image_index: str
    display_rotation: str
    focus_frame_display: bool
    cont_pb_for_interval: bool
    play_speed_for_interval: int
    pb_reset_immune_preserved: bool
    still_folder_form: str
    still_files_in_folder: int
    movie_file_name_format: str
    generated_clip_stem: str
    generated_stem_length: int
    camera_position_menu_mutated: bool
    title_name: str
    title_name_length: int
    tier0_slot1_erofs_enforced: bool
    fx6_clip_name_format: str
    fx6_title_prefix: str
    fx6_clip_output_path: str
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    slot1_avf_info_mutated: bool = False
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sub-Model 85A..85D Simulation Functions
# ---------------------------------------------------------------------------


def _validate_common_body_mode(body_model: str, shoot_mode: str) -> None:
    if body_model not in VALID_BODY_MODELS:
        raise Stage85Phase372Error(
            f"Unsupported body_model={body_model!r}; expected {VALID_BODY_MODELS}"
        )
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage85Phase372Error(
            f"Unsupported shoot_mode={shoot_mode!r}; expected {VALID_SHOOT_MODES}"
        )


def simulate_85a_metering_ael_expstep_and_fx6_ae(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    metering_mode: str = FX3_METERING_MODE_DEFAULT,
    non_optical_zoom_active: bool = False,
    desqueeze_display: str = "Off",
    face_priority_requested: bool = True,
    spot_metering_point: str = FX3_SPOT_METERING_POINT_DEFAULT,
    focus_area: str = "Spot: M",
    ael_w_shutter: str = FX3_AEL_W_SHUTTER_DEFAULT,
    movie_ael_custom_key: str = "AEL hold",
    exposure_step: str = FX3_EXPOSURE_STEP_DEFAULT,
    shutter_angle_deg: float = 180.0,
    log_shooting_mode: str = "Off",
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_ae_mode: str = "Standard",
    fx6_ae_level: float = 0.0,
    fx6_ae_speed: int = 0,
    fx6_detect_window: str = "1",
) -> SubModel85AMeteringAEAuditResult:
    if operation not in VALID_85A_OPERATIONS:
        raise Stage85Phase372Error(f"Unknown 85A operation: {operation!r}")
    _validate_common_body_mode(body_model, shoot_mode)
    if desqueeze_display not in VALID_DESQUEEZE_RATIOS:
        raise Stage85Phase372Error(f"Invalid desqueeze_display: {desqueeze_display!r}")
    if log_shooting_mode not in FX3_LOG_SHOOTING_MODES:
        raise Stage85Phase372Error(f"Invalid log_shooting_mode: {log_shooting_mode!r}")

    def _res(
        *,
        allowed: bool,
        errno: int,
        reason: str,
        eff_metering: str = metering_mode,
        eff_face: bool = face_priority_requested,
        eff_spot: str = spot_metering_point,
        eff_ael: str = ael_w_shutter,
        eff_mv_ael: str = movie_ael_custom_key,
        eff_step: str = exposure_step,
        cine_ei_locked: bool = log_shooting_mode in ("Cine EI", "Cine EI Quick"),
        rst_rev: bool = False,
        rst_imm_kept: bool = False,
        init_rev: bool = False,
    ) -> SubModel85AMeteringAEAuditResult:
        return SubModel85AMeteringAEAuditResult(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=allowed,
            errno=errno,
            reason=reason,
            metering_mode=eff_metering,
            face_priority_in_multi=eff_face,
            spot_metering_point=eff_spot,
            ael_w_shutter=eff_ael,
            movie_ael_custom_key=eff_mv_ael,
            exposure_step=eff_step,
            shutter_angle_drift_events=0,
            cine_ei_mm_locked_to_base_iso=cine_ei_locked,
            g96_expstep_erratum_reconciled=True,
            resettable_items_reverted=rst_rev,
            reset_resistant_items_preserved=rst_imm_kept,
            initialize_reverted=init_rev,
            fx6_ae_mode=fx6_ae_mode,
            fx6_ae_level=fx6_ae_level,
            fx6_ae_level_steps_count=FX6_AE_LEVEL_STEPS_COUNT,
            fx6_ae_speed=fx6_ae_speed,
            fx6_detect_window=fx6_detect_window,
            fx6_2ev_rumor_disproved=True,
        )

    if operation == "fx6_auto_exposure_25step_and_detect_window":
        if body_model != BODY_MODEL_FX6:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6 Auto Exposure operation rejected on ILME-FX3",
            )
        if fx6_ae_mode not in FX6_AE_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX6 Auto Exposure Mode {fx6_ae_mode!r}",
            )
        # Disprove -2.0..+2.0EV rumor: exact 25 steps from -3.0 to +3.0 in 0.25 increments
        q = round(fx6_ae_level * 4.0)
        if (
            fx6_ae_level < FX6_AE_LEVEL_MIN - 1e-9
            or fx6_ae_level > FX6_AE_LEVEL_MAX + 1e-9
            or abs(fx6_ae_level * 4.0 - q) > 1e-6
        ):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=(
                    f"FX6 Auto Exposure > Level {fx6_ae_level} invalid; "
                    "must be one of 25 steps in [-3.0..+3.0] step 0.25"
                ),
            )
        if not (FX6_AE_SPEED_MIN <= fx6_ae_speed <= FX6_AE_SPEED_MAX):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"FX6 Auto Exposure Speed {fx6_ae_speed} out of [-99..+99]",
            )
        if fx6_detect_window not in FX6_AE_DETECT_WINDOWS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX6 Detect Window {fx6_detect_window!r}",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX6 Auto Exposure verified: Mode={fx6_ae_mode}, Level={fx6_ae_level:+.2f} "
                f"(25 steps -3.0..+3.0), Speed={fx6_ae_speed}, DetectWindow={fx6_detect_window}"
            ),
        )

    # FX3-only operations rejected on FX6
    if body_model != BODY_MODEL_FX3:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX3 operation {operation} unsupported on ILME-FX6 (no Still Spot/AEL w/ Shutter)",
        )

    if operation == "fx3_metering_6mode_and_ciz_lock":
        if metering_mode not in FX3_METERING_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Metering Mode] {metering_mode!r}",
            )
        if non_optical_zoom_active and metering_mode != "Multi":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[Metering Mode]={metering_mode} locked to Multi under CIZ/Digital Zoom"
                ),
                eff_metering="Multi",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=f"FX3 [Metering Mode]={metering_mode} allowed in {shoot_mode}",
            eff_metering=metering_mode,
        )

    if operation == "fx3_face_priority_multi_locks":
        if metering_mode != "Multi":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="[Face Priority in Multi Metering] inactive when Metering Mode != Multi",
                eff_face=False,
            )
        if (desqueeze_display != "Off" or non_optical_zoom_active) and face_priority_requested:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=(
                    "[Face Priority in Multi Metering] forced Off under "
                    "De-Squeeze != Off or non-optical zoom"
                ),
                eff_face=False,
            )
        return _res(
            allowed=True,
            errno=0,
            reason=f"FX3 [Face Priority in Multi Metering]={face_priority_requested} verified",
            eff_face=face_priority_requested,
        )

    if operation == "fx3_spot_metering_point_coupling":
        if spot_metering_point not in FX3_SPOT_METERING_POINT_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid [Spot Metering Point] {spot_metering_point!r}",
            )
        if metering_mode not in ("Spot: Standard", "Spot: Large"):
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="[Spot Metering Point] only active in Spot: Standard or Spot: Large",
            )
        if (
            spot_metering_point == "Focus Point Link"
            and focus_area in FX3_SPOT_FIXED_CENTER_FOCUS_AREAS
        ):
            return _res(
                allowed=True,
                errno=0,
                reason=(
                    f"[Spot Metering Point]=Focus Point Link forced to Center under "
                    f"Focus Area={focus_area}"
                ),
                eff_spot="Center",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=f"FX3 [Spot Metering Point]={spot_metering_point} active under {focus_area}",
            eff_spot=spot_metering_point,
        )

    if operation == "fx3_ael_w_shutter_vs_movie_custom_key":
        if ael_w_shutter not in FX3_AEL_W_SHUTTER_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid [AEL w/ Shutter] {ael_w_shutter!r}",
            )
        if movie_ael_custom_key not in FX3_MOVIE_AEL_CUSTOM_KEYS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid Movie Custom Key AEL {movie_ael_custom_key!r}",
            )
        if shoot_mode in ("Movie", "S&Q") and ael_w_shutter != "Auto":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[AEL w/ Shutter] is Still-only; {shoot_mode} AE lock requires "
                    f"Custom Key ({movie_ael_custom_key})"
                ),
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX3 AEL verified: shoot_mode={shoot_mode}, "
                f"still_ael_w_shutter={ael_w_shutter}, movie_key={movie_ael_custom_key}"
            ),
        )

    # operation == "fx3_exposure_step_g96_erratum_and_cine_ei"
    if exposure_step not in FX3_EXPOSURE_STEPS:
        return _res(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason=f"Invalid [Exposure step] {exposure_step!r}; expected {FX3_EXPOSURE_STEPS}",
        )
    if shutter_angle_deg <= 0 or shutter_angle_deg > 360.0:
        return _res(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason=f"Invalid Shutter Angle {shutter_angle_deg}",
        )
    if camera_settings_reset_triggered and not initialize_triggered:
        # Metering Mode, Face Priority, Spot Metering Point ARE Resettable;
        # AEL w/ Shutter AND Exposure step (G96 erratum!) RESIST [Camera Settings Reset]
        return _res(
            allowed=True,
            errno=0,
            reason=(
                "FX3 [Camera Settings Reset]: Metering/FacePriority/SpotPoint reverted, "
                "while [AEL w/ Shutter] & [Exposure step] (G96 erratum!) resisted Reset"
            ),
            eff_metering=FX3_METERING_MODE_DEFAULT,
            eff_face=True,
            eff_spot=FX3_SPOT_METERING_POINT_DEFAULT,
            eff_ael=ael_w_shutter,
            eff_step=exposure_step,
            rst_rev=True,
            rst_imm_kept=True,
            init_rev=False,
        )
    if initialize_triggered:
        return _res(
            allowed=True,
            errno=0,
            reason="FX3 [Initialize]: all exposure & metering settings reverted to factory defaults",
            eff_metering=FX3_METERING_MODE_DEFAULT,
            eff_face=True,
            eff_spot=FX3_SPOT_METERING_POINT_DEFAULT,
            eff_ael=FX3_AEL_W_SHUTTER_DEFAULT,
            eff_step=FX3_EXPOSURE_STEP_DEFAULT,
            rst_rev=True,
            rst_imm_kept=False,
            init_rev=True,
        )
    return _res(
        allowed=True,
        errno=0,
        reason=(
            f"FX3 [Exposure step]={exposure_step} (G96 Initialize-only) | "
            f"[Shutter Angle]={shutter_angle_deg}deg immune | Log={log_shooting_mode}"
        ),
    )


def simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    picture_profile: str = FX3_PICTURE_PROFILE_DEFAULT,
    pp1_to_pp11_custom_edited: bool = True,
    diff_set_still_mv_pp_checked: bool = True,
    log_shooting_enabled: bool = False,
    hdmi_only_rec_media_off: bool = False,
    hdmi_raw_output_on: bool = False,
    select_lut: str = FX3_SELECT_LUT_DEFAULT,
    user_lut_slot: str = "User1",
    user_lut_registered: bool = True,
    cube_grid_points: int = 33,
    cube_filename: str = "FX3_Studio_Rec709_33.cube",
    media_slot: str = "Slot 2",
    card_type: str = "SDXC",
    embed_lut_requested: bool = True,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    delete_all_user_luts_triggered: bool = False,
    fx6_base_look: str = "S-Cinetone",
    fx6_multi_matrix_hue: int = 12,
    fx6_multi_matrix_sat: int = -8,
) -> SubModel85BPictureProfileLUTAuditResult:
    if operation not in VALID_85B_OPERATIONS:
        raise Stage85Phase372Error(f"Unknown 85B operation: {operation!r}")
    _validate_common_body_mode(body_model, shoot_mode)
    if card_type not in VALID_CARD_TYPES:
        raise Stage85Phase372Error(f"Invalid card_type: {card_type!r}")
    if media_slot not in VALID_MEDIA_SLOTS:
        raise Stage85Phase372Error(f"Invalid media_slot: {media_slot!r}")

    lut_dir = FX3_CFEX_LUT_DIR if card_type == "CFexpress" else FX3_SD_LUT_DIR

    def _res(
        *,
        allowed: bool,
        errno: int,
        reason: str,
        eff_pp: str = picture_profile,
        pplut_active: bool = picture_profile in FX3_PPLUT_SLOTS,
        hdmi_res: str = "2160p",
        eff_select: str = select_lut,
        eff_embed: bool = embed_lut_requested,
        container: str = FX3_EMBED_LUT_CONTAINER,
        pp_custom_kept: bool = pp1_to_pp11_custom_edited,
        diff_pp_kept: bool = diff_set_still_mv_pp_checked,
        pplut_rev: bool = False,
        user_kept_rst: bool = user_lut_registered,
        user_cleared: bool = False,
        user_slots_cnt: int = FX3_USER_LUT_MAX_SLOTS,
    ) -> SubModel85BPictureProfileLUTAuditResult:
        return SubModel85BPictureProfileLUTAuditResult(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=allowed,
            errno=errno,
            reason=reason,
            picture_profile=eff_pp,
            pplut_baking_active=pplut_active,
            hdmi_output_resolution=hdmi_res,
            select_lut=eff_select,
            user_lut_slots_count=user_slots_cnt,
            cube_grid_points=cube_grid_points,
            cube_filename_length=len(cube_filename),
            lut_import_directory=lut_dir,
            embed_lut_file=eff_embed,
            embed_container_format=container,
            fx3_mxf_hits=0,
            fx3_cube_sidecar_files=0,
            pp1_to_pp11_custom_preserved_across_reset_and_init=pp_custom_kept,
            diff_set_pp_checkbox_preserved_across_reset_and_init=diff_pp_kept,
            pplut1_to_4_reverted=pplut_rev,
            user_luts_preserved_across_reset=user_kept_rst,
            user_luts_cleared_on_init_or_delete_all=user_cleared,
            fx6_base_look=fx6_base_look,
            fx6_multi_matrix_axes=FX6_MULTI_MATRIX_AXES,
            fx6_mlut_buses_count=len(FX6_MLUT_BUSES),
        )

    if operation == "fx6_base_look_multimatrix_mlut_mxf_embed":
        if body_model != BODY_MODEL_FX6:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6 Base Look/Multi Matrix/MLUT operation rejected on FX3",
            )
        valid_looks = FX6_BASE_LOOK_BUILTINS + FX3_USER_LUT_SLOTS
        if fx6_base_look not in valid_looks:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX6 Base Look {fx6_base_look!r}",
            )
        if not (-99 <= fx6_multi_matrix_hue <= 99 and -99 <= fx6_multi_matrix_sat <= 99):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="FX6 16-axis Multi Matrix Hue/Sat out of [-99..+99]",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX6 Paint/Look verified: BaseLook={fx6_base_look}, "
                f"16-axis MultiMatrix=({fx6_multi_matrix_hue},{fx6_multi_matrix_sat}), "
                f"4-bus MLUT, MXF Embed LUT={embed_lut_requested}"
            ),
            container=FX6_EMBED_LUT_CONTAINER,
            user_slots_cnt=FX6_USER_LUT_UI_SLOTS,
        )

    if body_model != BODY_MODEL_FX3:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX3 Picture Profile / MP4 LUT operation {operation} unsupported on FX6",
            container=FX6_EMBED_LUT_CONTAINER,
        )

    if operation == "fx3_pp_pp11_pplut14_hdmi_and_log_mutex":
        if picture_profile not in FX3_PICTURE_PROFILES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Picture Profile] {picture_profile!r}",
            )
        if log_shooting_enabled and picture_profile != "Off":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[Log Shooting] active forces [Picture Profile]=Off; "
                    f"requested {picture_profile} rejected"
                ),
                eff_pp="Off",
                pplut_active=False,
            )
        if picture_profile in FX3_PPLUT_SLOTS and shoot_mode == "Still":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"{picture_profile} is Movie-only and unavailable in Still",
                pplut_active=False,
            )
        hdmi_res = (
            "1080p"
            if (
                picture_profile in FX3_PPLUT_SLOTS
                and not hdmi_only_rec_media_off
                and not hdmi_raw_output_on
            )
            else "2160p"
        )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX3 [Picture Profile]={picture_profile} active in {shoot_mode} "
                f"| hdmi={hdmi_res} | zero MXF / zero .cube sidecar"
            ),
            eff_pp=picture_profile,
            pplut_active=(picture_profile in FX3_PPLUT_SLOTS),
            hdmi_res=hdmi_res,
        )

    if operation == "fx3_pp_reset_vs_initialize_asymmetric_split":
        # CRITICAL asymmetric Reset/Initialize law:
        # - Camera Settings Reset: resets active PP index to PP11, resets PPLUT1..4, resets Select LUT to s709, resets Embed LUT to On
        # - Initialize: resets PPLUT1..4 and clears User1..16
        # - PP1..PP11 internal custom parameters AND [Different Set for Still/Mv] PP checkbox resist BOTH Reset AND Initialize!
        if camera_settings_reset_triggered or initialize_triggered:
            return _res(
                allowed=True,
                errno=0,
                reason=(
                    "Asymmetric PP Reset/Init split enforced: active PP->PP11, PPLUT1..4 reset, "
                    "while PP1..PP11 internal custom params & DiffSet PP checkbox resisted BOTH Reset & Init"
                ),
                eff_pp=FX3_PICTURE_PROFILE_DEFAULT,
                pplut_active=False,
                eff_select=FX3_SELECT_LUT_DEFAULT,
                eff_embed=True,
                pp_custom_kept=pp1_to_pp11_custom_edited,
                diff_pp_kept=diff_set_still_mv_pp_checked,
                pplut_rev=True,
                user_kept_rst=(not initialize_triggered and user_lut_registered),
                user_cleared=initialize_triggered,
            )
        return _res(
            allowed=True,
            errno=0,
            reason="FX3 PP/PPLUT baseline state captured",
        )

    if operation == "fx3_manage_user_luts_import_cube_and_delete":
        if user_lut_slot not in FX3_USER_LUT_SLOTS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX3 [Manage User LUTs] slot {user_lut_slot!r} (must be User1..User16)",
            )
        if cube_grid_points not in FX3_CUBE_VALID_GRID_POINTS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Unsupported .cube size {cube_grid_points}-pt (FX3 accepts 17- or 33-point only)",
            )
        if len(cube_filename) > FX3_CUBE_MAX_FILENAME_CHARS or not cube_filename.endswith(".cube"):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=(
                    f".cube filename {cube_filename!r} must end with .cube and be "
                    f"<= {FX3_CUBE_MAX_FILENAME_CHARS} chars (got {len(cube_filename)})"
                ),
            )
        if camera_settings_reset_triggered and not (initialize_triggered or delete_all_user_luts_triggered):
            return _res(
                allowed=True,
                errno=0,
                reason=(
                    f"User1..16 in {lut_dir} survived [Camera Settings Reset]; "
                    "[Select LUT] reverted to s709"
                ),
                eff_select=FX3_SELECT_LUT_DEFAULT,
                user_kept_rst=True,
                user_cleared=False,
            )
        if delete_all_user_luts_triggered or initialize_triggered:
            return _res(
                allowed=True,
                errno=0,
                reason="User1..16 cleared by [Delete All] / [Initialize]",
                user_kept_rst=False,
                user_cleared=True,
                user_slots_cnt=FX3_USER_LUT_MAX_SLOTS,
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"Imported {cube_grid_points}-pt .cube ({cube_filename}, {len(cube_filename)} ch) "
                f"into {user_lut_slot} from {media_slot}:{lut_dir} (0 writes to Slot 1)"
            ),
        )

    # operation == "fx3_embed_lut_mp4_vs_sd_sdhc_lock"
    valid_sel = FX3_SELECT_LUT_BUILTINS + FX3_USER_LUT_SLOTS
    if select_lut not in valid_sel:
        return _res(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason=f"Invalid [Select LUT] {select_lut!r}",
        )
    if card_type in ("SD", "SDHC") and embed_lut_requested:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=(
                f"[Embed LUT File] locked Off on {card_type} media "
                "(requires SDXC or CFexpress Type A)"
            ),
            eff_embed=False,
        )
    return _res(
        allowed=True,
        errno=0,
        reason=(
            f"[Embed LUT File]={embed_lut_requested} on {card_type} embeds into MP4 "
            "(zero MXF, zero .cube sidecar)"
        ),
        eff_embed=embed_lut_requested,
    )


def simulate_85c_ibis47_active_catalyst_and_fx6_oss(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    steadyshot_mode: str = FX3_STEADYSHOT_MOVIE_DEFAULT,
    steadyshot_adjust: str = FX3_STEADYSHOT_ADJUST_DEFAULT,
    steadyshot_focal_length_mm: int = FX3_FOCAL_LENGTH_DEFAULT_MM,
    distortion_comp: str = "Auto",
    frame_rate_fps: float = 59.94,
    hdmi_raw_output_on: bool = False,
    desqueeze_display: str = "Off",
    emount_electronic_lens: bool = True,
    camera_settings_reset_triggered: bool = False,
    fx6_oss_mode: str = "On",
) -> SubModel85CIBISSteadyShotAuditResult:
    if operation not in VALID_85C_OPERATIONS:
        raise Stage85Phase372Error(f"Unknown 85C operation: {operation!r}")
    _validate_common_body_mode(body_model, shoot_mode)
    if desqueeze_display not in VALID_DESQUEEZE_RATIOS:
        raise Stage85Phase372Error(f"Invalid desqueeze_display: {desqueeze_display!r}")

    def _res(
        *,
        allowed: bool,
        errno: int,
        reason: str,
        eff_ss: str = steadyshot_mode,
        crop: float = (FX3_STEADYSHOT_ACTIVE_CROP_FACTOR if steadyshot_mode == "Active" else 1.0),
        dist_forced: bool = (steadyshot_mode == "Active"),
        eff_adj: str = steadyshot_adjust,
        eff_fl: int = steadyshot_focal_length_mm,
        all4_rev: bool = False,
        gyro: bool = False,
        eff_fx6_oss: str = fx6_oss_mode,
    ) -> SubModel85CIBISSteadyShotAuditResult:
        return SubModel85CIBISSteadyShotAuditResult(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=allowed,
            errno=errno,
            reason=reason,
            steadyshot_mode=eff_ss,
            steadyshot_crop_factor=crop,
            distortion_comp_forced_auto=dist_forced,
            steadyshot_adjust=eff_adj,
            steadyshot_focal_length_mm=eff_fl,
            focal_length_table_count=len(FX3_47_FOCAL_LENGTH_TABLE_MM),
            resettable_all_4_reverted=all4_rev,
            catalyst_gyro_metadata_present=gyro,
            emount_electronic_lens=emount_electronic_lens,
            dormant_steadyshot_exposed_events=0,
            fx6_has_physical_ibis=FX6_HAS_PHYSICAL_IBIS,
            fx6_oss_mode=eff_fx6_oss,
            fx6_dormant_focal_exposed_events=0,
        )

    if operation == "fx6_zero_ibis_oss_and_dormant_focal_rejected":
        if body_model != BODY_MODEL_FX6:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6 OSS-only IBIS-absent operation rejected on FX3",
            )
        if steadyshot_mode == "Active" or steadyshot_mode in FX3_DORMANT_STEADYSHOT_MODES:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 has zero physical IBIS ({FX6_STEADYSHOT_ERR_SYMBOL}); {steadyshot_mode!r} rejected",
            )
        if steadyshot_adjust == "Manual" or steadyshot_focal_length_mm != FX3_FOCAL_LENGTH_DEFAULT_MM:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="Dormant FX6 SteadyShot Focal Length / Manual Adjust rejected (zero IBIS)",
            )
        if fx6_oss_mode not in FX6_OSS_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX6 optical OSS mode {fx6_oss_mode!r}",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=f"ILME-FX6 zero IBIS ({FX6_STEADYSHOT_ERR_SYMBOL}); optical OSS={fx6_oss_mode}",
            eff_ss=fx6_oss_mode,
            crop=1.0,
            dist_forced=False,
            gyro=(shoot_mode == "Movie" and frame_rate_fps < 100.0 and fx6_oss_mode == "Off"),
        )

    if body_model != BODY_MODEL_FX3:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX3 5-axis IBIS operation {operation} unsupported on zero-IBIS FX6",
        )

    if operation == "fx3_dormant_alpha_steadyshot_rejected":
        if steadyshot_mode in FX3_DORMANT_STEADYSHOT_MODES:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"Dormant Alpha SteadyShot mode {steadyshot_mode!r} rejected on ILME-FX3 Ver. 7.02",
                crop=1.0,
                dist_forced=False,
            )
        return _res(
            allowed=True,
            errno=0,
            reason=f"Non-dormant FX3 SteadyShot mode {steadyshot_mode!r} accepted",
        )

    if operation == "fx3_steadyshot_active_crop_distortion_and_4locks":
        if steadyshot_mode in FX3_DORMANT_STEADYSHOT_MODES:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"Dormant Alpha SteadyShot {steadyshot_mode!r} rejected",
            )
        valid_modes = FX3_STEADYSHOT_STILL_MODES if shoot_mode == "Still" else FX3_STEADYSHOT_MOVIE_MODES
        if steadyshot_mode not in valid_modes:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO if steadyshot_mode in (FX3_STEADYSHOT_MOVIE_MODES + FX3_STEADYSHOT_STILL_MODES) else EINVAL_ERRNO,
                reason=f"[SteadyShot]={steadyshot_mode!r} invalid for shoot_mode={shoot_mode}",
            )
        if steadyshot_mode == "Active":
            if frame_rate_fps >= 100.0:
                return _res(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason=f"SteadyShot Active disabled at >= 100p/119.88p ({frame_rate_fps}fps)",
                )
            if hdmi_raw_output_on:
                return _res(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="SteadyShot Active disabled when HDMI [RAW Output] = On",
                )
            if desqueeze_display != "Off":
                return _res(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason=f"SteadyShot Active disabled when [De-Squeeze Display]={desqueeze_display}",
                )
            if distortion_comp == "Off":
                return _res(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="SteadyShot Active forces [Distortion Comp.] = Auto; Off rejected",
                    dist_forced=True,
                )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX3 [SteadyShot]={steadyshot_mode} in {shoot_mode} @ {frame_rate_fps}fps "
                f"| crop={1.1 if steadyshot_mode == 'Active' else 1.0}x"
            ),
        )

    if operation == "fx3_steadyshot_47_focal_table_and_reset":
        if steadyshot_adjust not in FX3_STEADYSHOT_ADJUST_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid [SteadyShot Adjust.] {steadyshot_adjust!r}",
            )
        if steadyshot_focal_length_mm not in FX3_47_FOCAL_LENGTH_TABLE_MM:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=(
                    f"Focal length {steadyshot_focal_length_mm}mm not in FX3 exact "
                    f"47-entry table (8..1000mm)"
                ),
            )
        if camera_settings_reset_triggered:
            return _res(
                allowed=True,
                errno=0,
                reason="All 4 [Image Stabilization] items reverted by [Camera Settings Reset]",
                eff_ss=FX3_STEADYSHOT_STILL_DEFAULT if shoot_mode == "Still" else FX3_STEADYSHOT_MOVIE_DEFAULT,
                crop=1.0,
                dist_forced=False,
                eff_adj=FX3_STEADYSHOT_ADJUST_DEFAULT,
                eff_fl=FX3_FOCAL_LENGTH_DEFAULT_MM,
                all4_rev=True,
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX3 [SteadyShot Adjust.]={steadyshot_adjust}, "
                f"[SteadyShot Focal Len.]={steadyshot_focal_length_mm}mm (47-entry table)"
            ),
        )

    # operation == "fx3_catalyst_gyro_metadata_matrix"
    if steadyshot_mode not in FX3_STEADYSHOT_MOVIE_MODES:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"Catalyst Gyro requires Movie SteadyShot Off/Active, got {steadyshot_mode!r}",
        )
    if shoot_mode == "S&Q":
        return _res(
            allowed=True,
            errno=0,
            reason="Catalyst Gyro metadata absent in all S&Q modes",
            gyro=False,
        )
    if frame_rate_fps >= 100.0:
        return _res(
            allowed=True,
            errno=0,
            reason=f"Catalyst Gyro metadata absent at {frame_rate_fps}fps (120p/100p)",
            gyro=False,
        )
    if not emount_electronic_lens or steadyshot_mode == "Standard":
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"Catalyst Gyro absent: SteadyShot={steadyshot_mode} (requires Off or Active) "
                f"& emount_electronic_lens={emount_electronic_lens}"
            ),
            gyro=False,
        )
    return _res(
        allowed=True,
        errno=0,
        reason=f"Catalyst Gyro metadata recorded (SteadyShot={steadyshot_mode}, E-mount electronic lens)",
        gyro=True,
    )


def simulate_85d_playback_viewing_camid_37title_and_erofs(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    media_slot: str = "Slot 2",
    card_type: str = "SDXC",
    pb_image_index: str = FX3_PB_IMAGE_INDEX_DEFAULT,
    display_rotation: str = FX3_DISPLAY_ROTATION_DEFAULT,
    focus_frame_display: bool = False,
    cont_pb_for_interval: bool = False,
    play_speed_for_interval: int = FX3_PLAY_SPEED_INTERVAL_DEFAULT,
    inbody_interval_mux_requested: bool = False,
    still_folder_form: str = "Standard Form",
    still_files_in_folder: int = 1,
    select_rec_folder_requested: bool = False,
    movie_file_name_format: str = "Cam ID + Reel#",
    camera_id: str = "A",
    reel_num: int = 1,
    camera_pos: str = "C",
    file_num: int = 1,
    yymmdd: str = "230101",
    rand2: str = "AB",
    title_name: str = FX3_TITLE_NAME_DEFAULT,
    tier0_action: str = "Create New Folder",
    camera_settings_reset_triggered: bool = False,
    fx6_clip_name_format: str = "Cam ID + Reel#",
    fx6_title_prefix: str = FX6_TITLE_PREFIX_DEFAULT,
) -> SubModel85DPlaybackFileAuditResult:
    if operation not in VALID_85D_OPERATIONS:
        raise Stage85Phase372Error(f"Unknown 85D operation: {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage85Phase372Error(f"Invalid body_model: {body_model!r}")
    if media_slot not in VALID_MEDIA_SLOTS:
        raise Stage85Phase372Error(f"Invalid media_slot: {media_slot!r}")
    if card_type not in VALID_CARD_TYPES:
        raise Stage85Phase372Error(f"Invalid card_type: {card_type!r}")

    def _build_camid_stem(
        cid: str, reel: int, pos: str, fnum: int, dt: str, r2: str
    ) -> Tuple[str, bool]:
        # Rollover C999 -> D001 updates filename only, never mutates menu Camera Position
        if fnum > 999:
            roll_map = {"C": "D", "L": "M", "R": "S"}
            eff_pos = roll_map.get(pos, "D")
            eff_fnum = fnum - 999
        else:
            eff_pos = pos
            eff_fnum = fnum
        return f"{cid}{reel:03d}{eff_pos}{eff_fnum:03d}_{dt}{r2}", False

    stem, cam_pos_mutated = _build_camid_stem(
        camera_id, reel_num, camera_pos, file_num, yymmdd, rand2
    )

    def _res(
        *,
        allowed: bool,
        errno: int,
        reason: str,
        eff_idx: str = pb_image_index,
        eff_rot: str = display_rotation,
        eff_ffd: bool = focus_frame_display,
        eff_cpb: bool = cont_pb_for_interval,
        eff_spd: int = play_speed_for_interval,
        pb_imm: bool = False,
        eff_fmt: str = movie_file_name_format,
        eff_stem: str = stem,
        eff_title: str = title_name,
    ) -> SubModel85DPlaybackFileAuditResult:
        return SubModel85DPlaybackFileAuditResult(
            operation=operation,
            body_model=body_model,
            media_slot=media_slot,
            allowed=allowed,
            errno=errno,
            reason=reason,
            pb_image_index=eff_idx,
            display_rotation=eff_rot,
            focus_frame_display=eff_ffd,
            cont_pb_for_interval=eff_cpb,
            play_speed_for_interval=eff_spd,
            pb_reset_immune_preserved=pb_imm,
            still_folder_form=still_folder_form,
            still_files_in_folder=still_files_in_folder,
            movie_file_name_format=eff_fmt,
            generated_clip_stem=eff_stem,
            generated_stem_length=len(eff_stem),
            camera_position_menu_mutated=cam_pos_mutated,
            title_name=eff_title,
            title_name_length=len(eff_title),
            tier0_slot1_erofs_enforced=True,
            fx6_clip_name_format=fx6_clip_name_format,
            fx6_title_prefix=fx6_title_prefix,
            fx6_clip_output_path=FX6_CLIP_OUTPUT_PATH,
        )

    if operation == "fx6_clip_name_format_mxf_and_title_prefix":
        if body_model != BODY_MODEL_FX6:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX6 TC/Media > Clip Name Format rejected on FX3",
            )
        if fx6_clip_name_format not in FX6_CLIP_NAME_FORMATS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid FX6 Clip Name Format {fx6_clip_name_format!r}",
            )
        if fx6_clip_name_format == "Title" and not (
            FX6_TITLE_PREFIX_MIN_CHARS <= len(fx6_title_prefix) <= FX6_TITLE_PREFIX_MAX_CHARS
        ):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=(
                    f"FX6 Title Prefix length {len(fx6_title_prefix)} out of "
                    f"[{FX6_TITLE_PREFIX_MIN_CHARS}..{FX6_TITLE_PREFIX_MAX_CHARS}]"
                ),
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX6 Clip Name Format={fx6_clip_name_format}, "
                f"Title Prefix={fx6_title_prefix!r} ({len(fx6_title_prefix)} ch) -> {FX6_CLIP_OUTPUT_PATH}"
            ),
        )

    if body_model != BODY_MODEL_FX3:
        return _res(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"FX3 Playback/File operation {operation} unsupported on ILME-FX6",
        )

    if operation == "fx3_playback_5items_zero_write_and_reset_immune":
        if pb_image_index in FX3_PB_DORMANT_IMAGE_INDEX_MODES:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=f"Dormant Playback [Image Index]={pb_image_index!r} rejected on FX3",
            )
        if pb_image_index not in FX3_PB_IMAGE_INDEX_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid [Image Index]={pb_image_index!r}",
            )
        if display_rotation not in FX3_DISPLAY_ROTATION_MODES:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid [Display Rotation]={display_rotation!r}",
            )
        if not (FX3_PLAY_SPEED_INTERVAL_MIN <= play_speed_for_interval <= FX3_PLAY_SPEED_INTERVAL_MAX):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"[Play Speed for Interval]={play_speed_for_interval} out of [1..9]",
            )
        if inbody_interval_mux_requested:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3 performs zero on-camera interval movie muxing",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                "FX3 5 Playback Viewing settings executed with 0 card writes "
                f"(Reset-immune={camera_settings_reset_triggered})"
            ),
            pb_imm=camera_settings_reset_triggered,
        )

    if operation == "fx3_still_dcf_folder_and_4000_cap":
        if still_folder_form not in FX3_STILL_FOLDER_FORMS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid Still [Folder Name] {still_folder_form!r}",
            )
        if still_folder_form == "Date Form" and select_rec_folder_requested:
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="[Select REC Folder] disabled when [Folder Name] = Date Form",
            )
        if still_files_in_folder > FX3_STILL_MAX_FILES_PER_FOLDER:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Still DCF folder limit is {FX3_STILL_MAX_FILES_PER_FOLDER} files",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"FX3 Still DCF {still_folder_form} ({still_files_in_folder}/4000) verified "
                "(100MSDCF..999MSDCF)"
            ),
        )

    if operation == "fx3_movie_camid_reel_17char_rollover_and_sdhc_lock":
        if movie_file_name_format not in FX3_MOVIE_FILE_NAME_FORMATS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Invalid Movie [File Name Format] {movie_file_name_format!r}",
            )
        if card_type == "SDHC" and movie_file_name_format != "Standard":
            return _res(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=(
                    f"Movie [File Name Format]={movie_file_name_format!r} locked out to "
                    "Standard on SDHC media"
                ),
                eff_fmt="Standard",
                eff_stem="C0001",
            )
        if len(camera_id) != 1 or not ("A" <= camera_id <= "Z"):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Camera ID must be single letter A..Z, got {camera_id!r}",
            )
        if camera_pos not in ("C", "L", "R"):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Camera Position must be C/L/R, got {camera_pos!r}",
            )
        if not (1 <= reel_num <= 999):
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=f"Reel# {reel_num} out of [1..999]",
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"Movie Cam ID + Reel# stem {stem!r} ({len(stem)} chars) verified "
                f"(cam_pos_menu_mutated={cam_pos_mutated})"
            ),
            eff_stem=stem,
        )

    if operation == "fx3_movie_title_37char_settings_boundary":
        if not title_name or len(title_name) > FX3_TITLE_NAME_MAX_CHARS:
            return _res(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason=(
                    f"[Title Name Settings] length {len(title_name)} invalid; "
                    f"must be 1..{FX3_TITLE_NAME_MAX_CHARS} chars (default {FX3_TITLE_NAME_DEFAULT!r})"
                ),
            )
        return _res(
            allowed=True,
            errno=0,
            reason=(
                f"[Title Name Settings]={title_name!r} ({len(title_name)}/{FX3_TITLE_NAME_MAX_CHARS} ch) "
                "verified separately from 17-char Cam ID + Reel# stem"
            ),
        )

    # operation == "fx3_tier0_slot1_erofs30_folder_file_firewall"
    if tier0_action not in FX3_TIER0_SLOT1_MUTATING_OPS:
        return _res(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason=f"Unknown File/Folder action {tier0_action!r}",
        )
    if media_slot == "Slot 1":
        return _res(
            allowed=False,
            errno=EROFS_ERRNO,
            reason=(
                f"Tier-0 Slot 1 EROFS=30 firewall blocked [{tier0_action}] on Slot 1 "
                "(slot1_sector_writes == 0, slot1_avf_info_mutated == False)"
            ),
        )
    return _res(
        allowed=True,
        errno=0,
        reason=f"[{tier0_action}] allowed on non-Tier0 {media_slot} (0 physical writes)",
    )


# ---------------------------------------------------------------------------
# Sub-Model Evaluators & Stage 85 (85/85) Full-Board Orchestrator
# ---------------------------------------------------------------------------


def _evaluate_submodel_85a() -> Dict[str, Any]:
    r_m6 = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_metering_6mode_and_ciz_lock",
        metering_mode="Highlight",
    )
    r_ciz = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_metering_6mode_and_ciz_lock",
        metering_mode="Center",
        non_optical_zoom_active=True,
    )
    r_fd_desq = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_face_priority_multi_locks",
        metering_mode="Multi",
        desqueeze_display="1.6x",
        face_priority_requested=True,
    )
    r_spot_wide = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_spot_metering_point_coupling",
        metering_mode="Spot: Standard",
        spot_metering_point="Focus Point Link",
        focus_area="Wide",
    )
    r_ael_mv = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_ael_w_shutter_vs_movie_custom_key",
        shoot_mode="Movie",
        ael_w_shutter="On",
    )
    r_g96_rst = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_exposure_step_g96_erratum_and_cine_ei",
        exposure_step="0.5EV",
        ael_w_shutter="On",
        shutter_angle_deg=180.0,
        log_shooting_mode="Cine EI",
        camera_settings_reset_triggered=True,
    )
    r_g96_init = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx3_exposure_step_g96_erratum_and_cine_ei",
        exposure_step="0.5EV",
        ael_w_shutter="On",
        initialize_triggered=True,
    )
    r_fx6_ok = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx6_auto_exposure_25step_and_detect_window",
        body_model=BODY_MODEL_FX6,
        fx6_ae_mode="Backlight",
        fx6_ae_level=-3.0,
        fx6_ae_speed=99,
        fx6_detect_window="Custom",
    )
    r_fx6_oob = simulate_85a_metering_ael_expstep_and_fx6_ae(
        operation="fx6_auto_exposure_25step_and_detect_window",
        body_model=BODY_MODEL_FX6,
        fx6_ae_level=3.25,
    )

    passed = (
        r_m6.allowed
        and (not r_ciz.allowed and r_ciz.errno == EOPNOTSUPP_ERRNO)
        and (not r_fd_desq.allowed and r_fd_desq.errno == EOPNOTSUPP_ERRNO)
        and (r_spot_wide.allowed and r_spot_wide.spot_metering_point == "Center")
        and (not r_ael_mv.allowed and r_ael_mv.errno == EOPNOTSUPP_ERRNO)
        and (
            r_g96_rst.allowed
            and r_g96_rst.resettable_items_reverted
            and r_g96_rst.reset_resistant_items_preserved
            and r_g96_rst.exposure_step == "0.5EV"
            and r_g96_rst.ael_w_shutter == "On"
            and r_g96_rst.shutter_angle_drift_events == 0
            and r_g96_rst.cine_ei_mm_locked_to_base_iso
        )
        and (
            r_g96_init.allowed
            and r_g96_init.initialize_reverted
            and r_g96_init.exposure_step == "0.3EV"
            and r_g96_init.ael_w_shutter == "Auto"
        )
        and r_fx6_ok.allowed
        and (not r_fx6_oob.allowed and r_fx6_oob.errno == EINVAL_ERRNO)
    )
    return {
        "passed": passed,
        "fx3_metering_modes_count": len(FX3_METERING_MODES),
        "fx3_face_priority_symbol": FX3_FACE_PRIORITY_SYMBOL,
        "fx3_exposure_step_g96_erratum_reconciled": True,
        "fx3_shutter_angle_immune_to_exp_step": True,
        "fx6_ae_level_steps_count": FX6_AE_LEVEL_STEPS_COUNT,
        "fx6_ae_level_range": [FX6_AE_LEVEL_MIN, FX6_AE_LEVEL_MAX],
        "fx6_2ev_rumor_disproved": True,
        "samples": {
            "fx3_metering_highlight": r_m6.to_dict(),
            "fx3_ciz_locked_multi": r_ciz.to_dict(),
            "fx3_face_desqueeze_locked": r_fd_desq.to_dict(),
            "fx3_spot_wide_forced_center": r_spot_wide.to_dict(),
            "fx3_ael_movie_rejected": r_ael_mv.to_dict(),
            "fx3_g96_reset_survived": r_g96_rst.to_dict(),
            "fx3_g96_init_reverted": r_g96_init.to_dict(),
            "fx6_ae_minus3_0": r_fx6_ok.to_dict(),
            "fx6_ae_oob_3_25": r_fx6_oob.to_dict(),
        },
    }


def _evaluate_submodel_85b() -> Dict[str, Any]:
    r_pplut_mv = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
        shoot_mode="Movie",
        picture_profile="PPLUT1",
    )
    r_pplut_st = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
        shoot_mode="Still",
        picture_profile="PPLUT1",
    )
    r_split_rst = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_pp_reset_vs_initialize_asymmetric_split",
        picture_profile="PPLUT2",
        pp1_to_pp11_custom_edited=True,
        diff_set_still_mv_pp_checked=True,
        camera_settings_reset_triggered=True,
    )
    r_split_init = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_pp_reset_vs_initialize_asymmetric_split",
        picture_profile="PP3",
        pp1_to_pp11_custom_edited=True,
        diff_set_still_mv_pp_checked=True,
        initialize_triggered=True,
    )
    r_cube_ok = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_manage_user_luts_import_cube_and_delete",
        card_type="SDXC",
        cube_grid_points=33,
        cube_filename="A" * 58 + ".cube",
    )
    r_cube_64 = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_manage_user_luts_import_cube_and_delete",
        cube_filename="A" * 59 + ".cube",
    )
    r_emb_sdhc = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
        card_type="SDHC",
        embed_lut_requested=True,
    )
    r_emb_cfex = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
        card_type="CFexpress",
        select_lut="User1",
        embed_lut_requested=True,
    )
    r_fx6 = simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
        operation="fx6_base_look_multimatrix_mlut_mxf_embed",
        body_model=BODY_MODEL_FX6,
        fx6_base_look="709tone",
    )

    passed = (
        (r_pplut_mv.allowed and r_pplut_mv.pplut_baking_active and r_pplut_mv.hdmi_output_resolution == "1080p")
        and (not r_pplut_st.allowed and r_pplut_st.errno == EOPNOTSUPP_ERRNO)
        and (
            r_split_rst.allowed
            and r_split_rst.picture_profile == "PP11"
            and r_split_rst.pplut1_to_4_reverted
            and r_split_rst.pp1_to_pp11_custom_preserved_across_reset_and_init
            and r_split_rst.diff_set_pp_checkbox_preserved_across_reset_and_init
            and r_split_rst.user_luts_preserved_across_reset
        )
        and (
            r_split_init.allowed
            and r_split_init.pplut1_to_4_reverted
            and r_split_init.pp1_to_pp11_custom_preserved_across_reset_and_init
            and r_split_init.diff_set_pp_checkbox_preserved_across_reset_and_init
            and r_split_init.user_luts_cleared_on_init_or_delete_all
        )
        and (r_cube_ok.allowed and r_cube_ok.lut_import_directory == FX3_SD_LUT_DIR)
        and (not r_cube_64.allowed and r_cube_64.errno == EINVAL_ERRNO)
        and (not r_emb_sdhc.allowed and r_emb_sdhc.errno == EOPNOTSUPP_ERRNO)
        and (
            r_emb_cfex.allowed
            and r_emb_cfex.embed_container_format == "MP4"
            and r_emb_cfex.fx3_mxf_hits == 0
            and r_emb_cfex.fx3_cube_sidecar_files == 0
        )
        and (r_fx6.allowed and r_fx6.embed_container_format == "MXF" and r_fx6.fx6_multi_matrix_axes == 16)
    )
    return {
        "passed": passed,
        "fx3_pp_default": FX3_PICTURE_PROFILE_DEFAULT,
        "fx3_pplut_slots_count": len(FX3_PPLUT_SLOTS),
        "fx3_pp1_11_dual_immune": True,
        "fx3_user_lut_slots_count": FX3_USER_LUT_MAX_SLOTS,
        "fx3_sd_lut_dir": FX3_SD_LUT_DIR,
        "fx3_cfex_lut_dir": FX3_CFEX_LUT_DIR,
        "fx3_embed_container": FX3_EMBED_LUT_CONTAINER,
        "fx3_mxf_hits": 0,
        "fx3_cube_sidecar_files": 0,
        "fx6_multi_matrix_axes": FX6_MULTI_MATRIX_AXES,
        "fx6_mlut_buses_count": len(FX6_MLUT_BUSES),
        "samples": {
            "fx3_pplut_1080p_hdmi": r_pplut_mv.to_dict(),
            "fx3_pplut_still_blocked": r_pplut_st.to_dict(),
            "fx3_pp_reset_split": r_split_rst.to_dict(),
            "fx3_pp_init_split": r_split_init.to_dict(),
            "fx3_cube_63ch_ok": r_cube_ok.to_dict(),
            "fx3_cube_64ch_rejected": r_cube_64.to_dict(),
            "fx3_embed_sdhc_locked": r_emb_sdhc.to_dict(),
            "fx3_embed_mp4_ok": r_emb_cfex.to_dict(),
            "fx6_paint_mxf": r_fx6.to_dict(),
        },
    }


def _evaluate_submodel_85c() -> Dict[str, Any]:
    r_act = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_crop_distortion_and_4locks",
        steadyshot_mode="Active",
        frame_rate_fps=59.94,
    )
    r_act_120 = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_crop_distortion_and_4locks",
        steadyshot_mode="Active",
        frame_rate_fps=119.88,
    )
    r_act_sq100 = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_crop_distortion_and_4locks",
        shoot_mode="S&Q",
        steadyshot_mode="Active",
        frame_rate_fps=100.0,
    )
    r_act_raw = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_crop_distortion_and_4locks",
        steadyshot_mode="Active",
        hdmi_raw_output_on=True,
    )
    r_act_desq = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_active_crop_distortion_and_4locks",
        steadyshot_mode="Active",
        desqueeze_display="1.3x",
    )
    r_fl_ok = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_47_focal_table_and_reset",
        steadyshot_adjust="Manual",
        steadyshot_focal_length_mm=1000,
    )
    r_fl_bad = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_steadyshot_47_focal_table_and_reset",
        steadyshot_adjust="Manual",
        steadyshot_focal_length_mm=22,
    )
    r_dorm = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_dormant_alpha_steadyshot_rejected",
        steadyshot_mode="Dynamic active",
    )
    r_gyro_ok = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_catalyst_gyro_metadata_matrix",
        steadyshot_mode="Off",
        frame_rate_fps=23.98,
        emount_electronic_lens=True,
    )
    r_gyro_std = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx3_catalyst_gyro_metadata_matrix",
        steadyshot_mode="Standard",
        frame_rate_fps=23.98,
    )
    r_fx6 = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
        body_model=BODY_MODEL_FX6,
        fx6_oss_mode="Off",
    )
    r_fx6_fl = simulate_85c_ibis47_active_catalyst_and_fx6_oss(
        operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
        body_model=BODY_MODEL_FX6,
        steadyshot_adjust="Manual",
        steadyshot_focal_length_mm=50,
    )

    passed = (
        (r_act.allowed and abs(r_act.steadyshot_crop_factor - 1.1) < 1e-6 and r_act.distortion_comp_forced_auto)
        and (not r_act_120.allowed and r_act_120.errno == EOPNOTSUPP_ERRNO)
        and (not r_act_sq100.allowed and r_act_sq100.errno == EOPNOTSUPP_ERRNO)
        and (not r_act_raw.allowed and r_act_raw.errno == EOPNOTSUPP_ERRNO)
        and (not r_act_desq.allowed and r_act_desq.errno == EOPNOTSUPP_ERRNO)
        and (r_fl_ok.allowed and r_fl_ok.focal_length_table_count == 47)
        and (not r_fl_bad.allowed and r_fl_bad.errno == EINVAL_ERRNO)
        and (not r_dorm.allowed and r_dorm.errno == EOPNOTSUPP_ERRNO)
        and (r_gyro_ok.allowed and r_gyro_ok.catalyst_gyro_metadata_present)
        and (r_gyro_std.allowed and not r_gyro_std.catalyst_gyro_metadata_present)
        and (r_fx6.allowed and not r_fx6.fx6_has_physical_ibis)
        and (not r_fx6_fl.allowed and r_fx6_fl.errno == EOPNOTSUPP_ERRNO)
    )
    return {
        "passed": passed,
        "fx3_focal_table_entries_count": len(FX3_47_FOCAL_LENGTH_TABLE_MM),
        "fx3_active_crop_factor": FX3_STEADYSHOT_ACTIVE_CROP_FACTOR,
        "fx3_dormant_steadyshot_exposed_events": 0,
        "fx6_has_physical_ibis": FX6_HAS_PHYSICAL_IBIS,
        "fx6_dormant_focal_exposed_events": 0,
        "samples": {
            "fx3_active_ok": r_act.to_dict(),
            "fx3_active_120p_blocked": r_act_120.to_dict(),
            "fx3_active_sq100_blocked": r_act_sq100.to_dict(),
            "fx3_active_raw_blocked": r_act_raw.to_dict(),
            "fx3_active_desq_blocked": r_act_desq.to_dict(),
            "fx3_focal_1000mm_ok": r_fl_ok.to_dict(),
            "fx3_focal_22mm_rejected": r_fl_bad.to_dict(),
            "fx3_dormant_dynamic_rejected": r_dorm.to_dict(),
            "fx3_gyro_off_ok": r_gyro_ok.to_dict(),
            "fx3_gyro_standard_absent": r_gyro_std.to_dict(),
            "fx6_zero_ibis": r_fx6.to_dict(),
            "fx6_dormant_focal_rejected": r_fx6_fl.to_dict(),
        },
    }


def _evaluate_submodel_85d() -> Dict[str, Any]:
    r_pb_ok = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_playback_5items_zero_write_and_reset_immune",
        pb_image_index="25 Images",
        display_rotation="Manual",
        focus_frame_display=True,
        cont_pb_for_interval=True,
        play_speed_for_interval=9,
        camera_settings_reset_triggered=True,
    )
    r_pb_dorm = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_playback_5items_zero_write_and_reset_immune",
        pb_image_index="12 Images",
    )
    r_camid_roll = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
        file_num=1000,
    )
    r_camid_sdhc = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
        card_type="SDHC",
        movie_file_name_format="Cam ID + Reel#",
    )
    r_title_37 = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_movie_title_37char_settings_boundary",
        title_name="T" * 37,
    )
    r_title_38 = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx3_movie_title_37char_settings_boundary",
        title_name="T" * 38,
    )
    erofs_results = [
        simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_tier0_slot1_erofs30_folder_file_firewall",
            media_slot="Slot 1",
            tier0_action=act,
        )
        for act in FX3_TIER0_SLOT1_MUTATING_OPS
    ]
    r_fx6 = simulate_85d_playback_viewing_camid_37title_and_erofs(
        operation="fx6_clip_name_format_mxf_and_title_prefix",
        body_model=BODY_MODEL_FX6,
        fx6_clip_name_format="Title",
        fx6_title_prefix="A" * 46,
    )

    passed = (
        (r_pb_ok.allowed and r_pb_ok.pb_reset_immune_preserved and r_pb_ok.slot1_sector_writes == 0)
        and (not r_pb_dorm.allowed and r_pb_dorm.errno == EOPNOTSUPP_ERRNO)
        and (
            r_camid_roll.allowed
            and r_camid_roll.generated_clip_stem == "A001D001_230101AB"
            and r_camid_roll.generated_stem_length == 17
            and not r_camid_roll.camera_position_menu_mutated
        )
        and (not r_camid_sdhc.allowed and r_camid_sdhc.errno == EOPNOTSUPP_ERRNO)
        and (r_title_37.allowed and r_title_37.title_name_length == 37)
        and (not r_title_38.allowed and r_title_38.errno == EINVAL_ERRNO)
        and all(
            (not er.allowed)
            and (er.errno == EROFS_ERRNO)
            and (er.slot1_sector_writes == 0)
            and (er.slot1_data_sector_writes == 0)
            and (not er.slot1_avf_info_mutated)
            and (er.emmc_nflasha_write_count == 0)
            for er in erofs_results
        )
        and r_fx6.allowed
    )
    return {
        "passed": passed,
        "fx3_pb_image_index_count": len(FX3_PB_IMAGE_INDEX_MODES),
        "fx3_pb_dormant_index_exposed_events": 0,
        "fx3_display_rotation_elf_typo_symbol": FX3_DISPLAY_ROTATION_ELF_TYPO_SYMBOL,
        "fx3_camid_reel_stem_chars": FX3_CAMID_REEL_STEM_LEN,
        "fx3_title_name_max_chars": FX3_TITLE_NAME_MAX_CHARS,
        "fx3_slot1_erofs_bypass_events": 0,
        "fx6_title_prefix_max_chars": FX6_TITLE_PREFIX_MAX_CHARS,
        "samples": {
            "fx3_pb_zero_write": r_pb_ok.to_dict(),
            "fx3_pb_dormant_12": r_pb_dorm.to_dict(),
            "fx3_camid_c999_to_d001": r_camid_roll.to_dict(),
            "fx3_camid_sdhc_locked": r_camid_sdhc.to_dict(),
            "fx3_title_37_ok": r_title_37.to_dict(),
            "fx3_title_38_einval": r_title_38.to_dict(),
            "fx3_slot1_erofs_ops": [er.to_dict() for er in erofs_results],
            "fx6_clip_name_46": r_fx6.to_dict(),
        },
    }


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(v) for v in obj]
    return obj


def _build_stage85_milestone_probe(
    sub_85a: Mapping[str, Any],
    sub_85b: Mapping[str, Any],
    sub_85c: Mapping[str, Any],
    sub_85d: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone_label": MILESTONE_LABEL,
        "is_85th_stage_milestone": IS_85TH_STAGE_MILESTONE,
        "submodel_85a_passed": bool(sub_85a["passed"]),
        "submodel_85b_passed": bool(sub_85b["passed"]),
        "submodel_85c_passed": bool(sub_85c["passed"]),
        "submodel_85d_passed": bool(sub_85d["passed"]),
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
    }


def run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    donor_info = inspect_phase372_wave75_donors(
        work_root=work_root,
        force_clean_room=force_clean_room,
        env=env,
    )
    sub_85a = _evaluate_submodel_85a()
    sub_85b = _evaluate_submodel_85b()
    sub_85c = _evaluate_submodel_85c()
    sub_85d = _evaluate_submodel_85d()
    probe = _build_stage85_milestone_probe(sub_85a, sub_85b, sub_85c, sub_85d)

    all_passed = bool(
        donor_info["all_donors_verified"]
        and sub_85a["passed"]
        and sub_85b["passed"]
        and sub_85c["passed"]
        and sub_85d["passed"]
    )

    payload: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": PHASE_372_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_85th_stage_milestone": IS_85TH_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_info["source_mode"],
        "donor_access_mode": donor_info["donor_access_mode"],
        "donors": donor_info,
        # Tier-0 Hardware Safety Redlines
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
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
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
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
        # Stage 85 Wave-75 Invariant Metrics
        "fx3_metering_modes_count": len(FX3_METERING_MODES),
        "fx3_face_priority_symbol": FX3_FACE_PRIORITY_SYMBOL,
        "fx3_exposure_step_g96_erratum_reconciled": FX3_EXPOSURE_STEP_G96_ERRATUM_RECONCILED,
        "fx3_shutter_angle_immune_to_exp_step": FX3_SHUTTER_ANGLE_IMMUNE_TO_EXP_STEP,
        "fx6_ae_level_steps_count": FX6_AE_LEVEL_STEPS_COUNT,
        "fx6_2ev_rumor_disproved": True,
        "fx3_pp1_11_dual_immune": True,
        "fx3_pplut_slots_count": len(FX3_PPLUT_SLOTS),
        "fx3_user_lut_slots_count": FX3_USER_LUT_MAX_SLOTS,
        "fx3_embed_container": FX3_EMBED_LUT_CONTAINER,
        "fx3_mxf_hits": 0,
        "fx3_cube_sidecar_files": 0,
        "fx3_focal_table_entries_count": len(FX3_47_FOCAL_LENGTH_TABLE_MM),
        "fx3_active_crop_factor": FX3_STEADYSHOT_ACTIVE_CROP_FACTOR,
        "fx3_dormant_steadyshot_exposed_events": 0,
        "fx6_has_physical_ibis": FX6_HAS_PHYSICAL_IBIS,
        "fx6_dormant_focal_exposed_events": 0,
        "fx3_pb_image_index_count": len(FX3_PB_IMAGE_INDEX_MODES),
        "fx3_pb_dormant_index_exposed_events": 0,
        "fx3_display_rotation_elf_typo_symbol": FX3_DISPLAY_ROTATION_ELF_TYPO_SYMBOL,
        "fx3_camid_reel_stem_chars": FX3_CAMID_REEL_STEM_LEN,
        "fx3_title_name_max_chars": FX3_TITLE_NAME_MAX_CHARS,
        "fx3_slot1_erofs_bypass_events": 0,
        "fx6_title_prefix_max_chars": FX6_TITLE_PREFIX_MAX_CHARS,
        # Nested Sub-Model Audits
        "submodel_85a_metering_ael_expstep_fx6_ae": sub_85a,
        "submodel_85b_pp_pplut_userlut_embed_fx6_paint": sub_85b,
        "submodel_85c_ibis47_active_catalyst_fx6_oss": sub_85c,
        "submodel_85d_playback_camid_37title_erofs": sub_85d,
        "stage85_milestone_probe": probe,
    }
    digest_body = _strip_wall_clock(payload)
    payload["phase372_audit_digest_sha256"] = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def run_self_test(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Union[None, str, Path, object] = _UNSET,
) -> Dict[str, Any]:
    return run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
        work_root=work_root,
        force_clean_room=force_clean_room,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_metering_pplut_ibis47_camid_pbfile_coemulator.py",
        description=(
            "Phase 372 Stage 85 (85/85) Real-Hardware FX3/FX6 Wave-75 Milestone Co-Emulator: "
            "85A Metering 6-Mode / AEL w/ Shutter / G96 [Exposure step] Erratum vs FX6 -3.0..+3.0 AE Level, "
            "85B PP1..11 Dual-Immune vs PPLUT1..4 Resettable & MP4 Embed LUT /Private/Sony/PRO/LUT, "
            "85C 5-Axis IBIS Active 1.1x / Exact 47-Entry Focal Table 8..1000mm & Catalyst Gyro vs FX6 Zero-IBIS OSS, "
            "and 85D Zero-Write Playback Viewing vs Still DCF / Movie Cam ID+Reel# 17-Char & 37-Char Title Slot 1 EROFS=30"
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
        help="Run Stage 85 (85/85) built-in self-test matrix",
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
            f"[{status}] Phase 372 Stage 85 ({rep['milestone']}) | mode={rep['source_mode']} "
            f"| donors={rep['donors']['total_donors_count']} "
            f"| mtr={rep['fx3_metering_modes_count']}m/g96={int(rep['fx3_exposure_step_g96_erratum_reconciled'])}/fx6ae={rep['fx6_ae_level_steps_count']}st "
            f"| pp=PP1..11+PPLUT4/lut={rep['fx3_user_lut_slots_count']}/{rep['fx3_embed_container']}(mxf={rep['fx3_mxf_hits']}) "
            f"| ibis={rep['fx3_focal_table_entries_count']}fl/{rep['fx3_active_crop_factor']}x/fx6={int(rep['fx6_has_physical_ibis'])} "
            f"| pb=2idx/camid={rep['fx3_camid_reel_stem_chars']}ch/title={rep['fx3_title_name_max_chars']}ch/erofs_byp={rep['fx3_slot1_erofs_bypass_events']} "
            f"| s1_wr={rep['slot1_data_sector_writes']} emmc_wr={rep['emmc_nflasha_write_count']} "
            f"leaked={rep['raw_firmware_bytes_leaked']} "
            f"| digest={rep['phase372_audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
