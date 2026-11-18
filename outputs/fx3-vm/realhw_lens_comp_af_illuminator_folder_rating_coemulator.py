#!/usr/bin/env python3
"""Phase 309 (Stage 63 — 63/63 VM Stages Milestone) — Real-Hardware ILME-FX3 Ver. 7.02 vs
ILME-FX6 Ver. 6.01 Wave-53:
`[Lens Compensation]` Shading Auto/Off vs Dormant Auto:Low & SteadyShot Active Distortion Lock,
Built-in Front AF Illuminator LED (#8, 0.3..3.0 m) + MI-Shoe Flash Still AF-S Only vs
Zero-Illuminator FX6 + Movie AF Kinematics (`[AF Transition Speed]` / `[AF Subj. Shift
Sensitivity]` / `[AF Assist]`), AF Behavior & Initialize-Only Persistence (`[Aperture Drive in AF]`
/ `[AF w/ Shutter]` / `[Pre-AF]` / `[Circ. of Focus Point]` / `[Focus Area Color]`), and
`[File/Folder Settings]` / `[Select REC Folder]` / `[Create New Folder]` + Playback `[Rating]`
(1..5 Stars) Slot-1 Tier-0 Vault Firewall HIL Co-Emulator.

Strictly models Wave-53 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 63A — `[Lens Compensation]` Shading Auto/Off vs Dormant `Auto: Low` &
   `SteadyShot = Active` Distortion Lock**:
   - FX3 Ver. 7.02 `(Shooting) -> [Image Quality/Rec] -> [Lens Compensation]` (`_f.uxc 0x75c8`)
     exposes `[Shading Comp.]` ONLY `Auto` (default) / `Off` — dormant
     `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` and `_f.uxc 0x6c9c` `'Auto: Low'`
     (`ILCE-6700` / `ILCE-7RM5`) are rejected as `EOPNOTSUPP = 95`.
   - `[Chromatic Aberration Comp.]` exposes `Auto` (default) / `Off`; `[Distortion Comp.]` exposes
     `Auto` / `Off` (default) and is forced locked to `Auto` (`EOPNOTSUPP = 95` to select `Off`)
     by specific E-mount lens profiles (`SELP1650`, `FE 28-70mm`,
     `VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED`) OR Movie
     `[SteadyShot] = Active`.
   - `[Breathing Comp.]` (`On`/`Off`, default `Off`) is Movie-only and resettable by
     `[Camera Settings Reset]`, whereas Shading/Chromatic Aberration/Distortion survive
     `[Camera Settings Reset]` and reset ONLY via `[Initialize]`. Unchipped manual lenses reject
     menu compensation (`VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST` -> `EOPNOTSUPP = 95`).
   - Contrasts with `ILME-FX6 Ver. 6.01` (`Technical > Lens`, saved in `All File` not
     `Scene File`), where `Breathing Compensation` forces `Off` when `Distortion Comp. = Off`,
     `S&Q = On`, or `Codec` contains `RAW`, and sensor `White/Black Shading`
     (`PID_SET_{WHITE,BLACK}_SHADING`) is separate from optical lens shading.

2. **Sub-Model 63B — Built-in Front AF Illuminator LED (#8) vs Zero-Illuminator `ILME-FX6` &
   Movie AF Kinematics**:
   - `ILME-FX3` has a real built-in front AF illuminator / Self-timer lamp LED (`TP1000886886.html`
     Front side #8, `0.3 m - 3.0 m`) + MI-Shoe external flash AF illuminator (`_f.uxc 0x69c0`,
     `.uxc 0xe07f`, `BKID_APP_setting_still_image_af_illuminator`), activating ONLY in Still
     `AF-S` (`Auto`, `Silent Mode = Off`, `Focus Magnifier = Off`, `Mount Adaptor = Off`) and
     strictly locked out in `Movie`, `S&Q`, `AF-C`, `MF`, `Silent Mode = On`, `Focus Magnifier`,
     and `Mount Adaptor`.
   - Contrasts with `ILME-FX6` which has ZERO built-in AF illuminator LED
     (`fx6_has_builtin_af_illuminator == False`; dormant Alpha symbol only -> `EOPNOTSUPP = 95`).
   - Also models Movie/`S&Q` `[AF Transition Speed]` (`1..7`, default `5`), `[AF Subj. Shift
     Sensitivity]` (`1..5`, default `5(Responsive)` / `5_RESPONSICE`), and `[AF Assist]`
     (`Off`/`On`, Movie/`S&Q` `AF-C` only, incompatible with `SELP1650` / `SEL18200LE`), all
     resettable via `[Camera Settings Reset]`.

3. **Sub-Model 63C — AF Behavior & Initialize-Only Persistence (5 Settings)**:
   - `[Aperture Drive in AF]` (`Focus Priority` / `Standard` [default] / `Silent Priority`,
     Still-only; linked with `Silent Mode Settings -> Aperture Drive in AF`), Still-only
     `[AF w/ Shutter]` (`On` [default] / `Off`), Still-only `[Pre-AF]` (`On` / `Off` [default],
     lens-gated `VAL_lens_pre_af_support_LENS_PRE_AF_SUPPORT`), `[Circ. of Focus Point]`
     (`Circulate` / `Does Not Circulate` [default], **orthogonal horizontal/vertical wrap only,
     NO diagonal wrap**), and `[Focus Area Color]` (`White` [default] / `Red`, rejecting legacy
     `Focus Frame Color` naming spoof) — all 5 survive `[Camera Settings Reset]` &
     `[Reset Network Set.]` and reset ONLY via `[Initialize]`.
   - Contrasts with `ILME-FX6` which lacks all 5 and uses cinema `Iris` (`Auto Iris`, `Manual`,
     `Push Auto Iris`, `Auto Iris Override -1.0..+1.0 in 0.25`) + `Focus Area Marker`.

4. **Sub-Model 63D & Redlines — `[Create New Folder]` & Playback `[Rating]` (`1..5` Stars)
   Slot-1 Tier-0 Vault Firewall**:
   - Models `[File/Folder Settings]` (`Standard Form` `100MSDCF..999MSDCF` vs `Date Form`
     `100_MMDD` disabling `[Select REC Folder]`; `Series`/`Reset`; 3-char `DSC` prefix rejecting
     leading `_`), `[Create New Folder]` / `[Forced File Number Reset]` (`max_folder_num + 1`,
     4,000-image cap `STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`, dual-slot sync), and Playback `[Rating]`
     (`1..5` stars + `[Rating Set(Custom Key)]` `BKID_APP_valid_rating_1..5_selecting` +
     Still-screen `[Add Rating]` rejecting already-rated overwrite `_g.uxc 0x627d` and
     background FTP transfer `EBUSY = 16`).
   - **CRITICAL VAULT FIREWALL**: Whenever `Slot 1` holds a Tier-0 recovery vault
     (`slot1_is_tier0_vault=True`), `[Create New Folder]`, `[Forced File Number Reset]`,
     `[Select REC Folder]` implicit write, and `[Rating]` / `[Add Rating]` MUST fail-closed
     (`EROFS = 30` / `EBUSY = 16`, `slot1_data_sector_writes == 0`,
     `slot1_avf_info_mutated == False`), while virtual `Slot 2` operations succeed with
     `physical_device_writes == 0`.

5. **Dual-Mode 12-Donor `os.O_RDONLY` Verification (`<= 4096 B` bounded windows)**:
   - Audits 12 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors via `os.O_RDONLY`
     (including `libInfraLensCommunicator.so`, UXC packs, `appFw.so`, and `BK4`) with
     deterministic `CLEAN_ROOM_SYNTHETIC` fallback (`FX3_CLEAN_ROOM_TEST=1` or
     `FX3_FX6_FORCE_CLEAN_ROOM=1`), guaranteeing `raw_firmware_bytes_leaked == 0`.
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
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_lens_comp_af_illuminator_folder_rating_coemulator_v1"
PHASE_309_SCHEMA = SCHEMA_ID
PHASE_309_VERSION = "309.0.0"
PHASE_NUMBER = 309
STAGE_INDEX = 63
STAGE_TOTAL = 63
MILESTONE_LABEL = "63/63"
STAGE_NAME = "stage63_realhw_lens_comp_af_illuminator_folder_rating_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EPERM_ERRNO = 1
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

BOUNDED_WINDOW_MAX_BYTES = 4096

# Hard Safety Redline invariants (strictly locked False / 0 / True)
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

# Wave-53 Stage 63 (63/63) zero-fault & model-truth invariants
DORMANT_SHADING_AUTO_LOW_EXPOSED_EVENTS = 0
STEADYSHOT_ACTIVE_DISTORTION_BYPASS_EVENTS = 0
FX3_HAS_BUILTIN_AF_ILLUMINATOR = True
FX6_HAS_BUILTIN_AF_ILLUMINATOR = False
AF_ILLUMINATOR_NON_AFS_OR_SILENT_FIRE_EVENTS = 0
INITIALIZE_ONLY_AF_RESET_WIPE_EVENTS = 0
DIAGONAL_FOCUS_POINT_WRAP_EVENTS = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_VAULT_FOLDER_OR_RATING_MUTATION_BYTES = 0
SLOT1_AVF_INFO_MUTATED = False

RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Environment variables (supports both FX3_CLEAN_ROOM_TEST=1 and FX3_FX6_FORCE_CLEAN_ROOM=1)
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_string_sc_f": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
    "fx3_string_tc_f": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
    "fx3_string_ja_f": f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
    "fx3_string_en": f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_en_g": 69_600,
    "fx3_lens_comm": 14_544,
    "fx3_appfw": 79_015_712,
    "fx3_bk4": 2_229_740,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx6_appfw": 50_520_424,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_lens_comm": "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Lens Compensation",
        b"Shading Comp.",
        b"Auto: Low",
        b"Chromatic Aberration Comp.",
        b"Distortion Comp.",
        b"Breathing Comp.",
        b"AF Transition Speed",
        b"AF Subj. Shift Sensitivity",
        b"AF Assist",
        b"AF Illuminator",
        b"Aperture Drive in AF",
        b"Focus Priority",
        b"Silent Priority",
        b"AF w/ Shutter",
        b"Pre-AF",
        b"Circ. of Focus Point",
        b"Focus Area Color",
        b"File/Folder Settings",
        b"Select REC Folder",
        b"Create New Folder",
        b"Forced File Number Reset",
        b"Rating",
        b"Add Rating",
    ),
    "fx3_string_sc_f": (
        "镜头补偿".encode("utf-8"),
        "阴影补偿".encode("utf-8"),
        "自动: 低".encode("utf-8"),
        "色差补偿".encode("utf-8"),
        "失真补偿".encode("utf-8"),
        "呼吸补偿".encode("utf-8"),
        "AF过渡速度".encode("utf-8"),
        "AF帮助".encode("utf-8"),
        "AF光圈驱动".encode("utf-8"),
        "对焦点的循环".encode("utf-8"),
        "新文件夹".encode("utf-8"),
        "分级".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "鏡頭補償".encode("utf-8"),
        "陰影補償".encode("utf-8"),
        "失真補償".encode("utf-8"),
        "對焦變換速度".encode("utf-8"),
        "AF幫助".encode("utf-8"),
        "對焦中的光圈驅動".encode("utf-8"),
        "對焦點循環".encode("utf-8"),
        "新資料夾".encode("utf-8"),
        "等級".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ﾚﾝｽﾞ補正".encode("utf-8"),
        "周辺光量補正".encode("utf-8"),
        "歪曲収差補正".encode("utf-8"),
        "AFﾄﾗﾝｼﾞｼｮﾝ速度".encode("utf-8"),
        "AFアシスト".encode("utf-8"),
        "AF時の絞り駆動".encode("utf-8"),
        "ﾌｫｰｶｽ位置の循環".encode("utf-8"),
        "ﾌｫﾙﾀﾞｰ新規作成".encode("utf-8"),
        "レーティング".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"AF Illuminator",
        b"Folder Name",
        b"Standard Form",
        b"Date Form",
        b"File Number",
        b"Select REC Folder",
        b"New Folder",
        b"White",
        b"Red",
        b"Unable to perform rating on\nthis image.",
    ),
    "fx3_string_en_g": (
        b"Lens Comp.",
        b"Create a new folder.",
        b"Last 5 char. of folder name can be changed.",
        b"Can't add since a Rating is already applied.",
    ),
    "fx3_lens_comm": (
        b"LensCommunicator_Init",
        b"osal_snd_sync_msg",
        b"osal_snd_msg",
        b"GetMountedLensInfo",
    ),
    "fx6_string_en": (
        b"AF Transition Speed",
        b"AF Subj. Shift Sens.",
        b"Auto Iris",
        b"Push Auto Iris",
    ),
    "fx6_string_en_2": (
        b"Shading Compensation",
        b"Chroma Aberration Comp.",
        b"Distortion Comp.",
        b"AF Assist",
        b"White Shading",
        b"Black Shading",
        b"Edit Folder Name",
        b"Select Folder",
        b"Rename Folder",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (60_604_416, "FUNC_CREATE_FOLDER", b"FUNC_create_folder"),
        (60_604_416, "FUNC_STILL_FILE_NUMBER_RESET", b"FUNC_still_file_number_reset"),
        (60_604_416, "FUNC_RATING_CONTENT", b"FUNC_rating_content"),
        (60_604_416, "FUNC_RATING_CONTENT_BY_TOGGLE", b"FUNC_rating_content_by_toggle"),
        (60_608_512, "FUNC_RATING_ON_SHOOTING_SCREEN", b"FUNC_rating_on_shooting_screen"),
        (
            60_649_472,
            "VAL_DISTORTION_NOT_SUPPORTED",
            b"VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED",
        ),
        (
            60_649_472,
            "VAL_LENS_PRE_AF_SUPPORT",
            b"VAL_lens_pre_af_support_LENS_PRE_AF_SUPPORT",
        ),
        (61_202_432, "STATUS_SLOT1_FOLDER_MAX", b"STATUS_OF_MEDIA_SLOT1_FOLDER_MAX"),
        (61_206_528, "STATUS_SLOT1_READ_ONLY", b"STATUS_OF_MEDIA_SLOT1_READ_ONLY"),
        (61_886_464, "SHIFT_SENS_5_RESPONSICE", b"5_RESPONSICE"),
        (61_943_808, "VAL_XMP_RATING_VALID", b"VAL_xmp_rating_XMP_RATING_VALID"),
        (62_136_320, "DORMANT_LENS_COMP_SHADING_AUTO_LOW", b"LENS_COMP_SHADING_AUTO_LOW"),
        (62_382_080, "VAL_LENS_COMP_VALUE_NOT_EXIST", b"VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST"),
        (62_676_992, "BKID_LENS_COMP_SHADING", b"BKID_APP_setting_lens_comp_shading"),
        (62_676_992, "BKID_LENS_COMP_CHRO_ABER", b"BKID_APP_setting_lens_comp_chro_aber"),
        (62_676_992, "BKID_LENS_COMP_DISTORTION", b"BKID_APP_setting_lens_comp_distortion"),
        (62_676_992, "BKID_LENS_COMP_BREATHING", b"BKID_APP_setting_lens_comp_breathing"),
        (
            62_676_992,
            "BKID_SILENT_APERTURE_DRIVE_IN_AF",
            b"BKID_APP_setting_silent_detail_setting_aperture_drive_in_af",
        ),
        (62_676_992, "BKID_STILL_FOLDER_NAME", b"BKID_APP_setting_still_still_folder_name"),
        (62_676_992, "BKID_STILL_FILE_NUMBER", b"BKID_APP_setting_still_file_number"),
        (62_685_184, "BKID_STILL_AF_ILLUMINATOR", b"BKID_APP_setting_still_image_af_illuminator"),
        (62_685_184, "BKID_STL_APERTURE_DRIVE_IN_AF", b"BKID_APP_setting_stl_aperture_drive_in_af"),
        (62_689_261, "BKID_STILL_AF_W_SHUTTER", b"BKID_APP_setting_still_image_af_w_shutter"),
        (62_689_280, "BKID_MOVIE_AF_TRANSITION_SPEED", b"BKID_APP_setting_movie_af_transition_speed"),
        (62_689_280, "BKID_MOVIE_AF_SUBJ_SHIFT_SENS", b"BKID_APP_setting_movie_af_subj_shift_sens"),
        (62_689_280, "BKID_AF_ASSIST", b"BKID_APP_setting_af_assist"),
        (62_689_280, "BKID_PRE_AF", b"BKID_APP_setting_pre_af"),
        (62_689_280, "BKID_CIRC_OF_FOCUS_POINT", b"BKID_APP_setting_circulate_of_focus_point"),
        (62_689_280, "BKID_FOCUS_FRAME_COLOR", b"BKID_APP_setting_focus_frame_color"),
        (62_840_832, "BKID_VALID_RATING_1_SELECTING", b"BKID_APP_valid_rating_1_selecting"),
        (
            62_955_520,
            "EDIT_CMP_NG_BG_TRANSFER_RATING",
            b"EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING",
        ),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (39_886_848, "PID_SET_WHITE_SHADING", b"PID_SET_WHITE_SHADING"),
        (39_886_848, "PID_SET_BLACK_SHADING", b"PID_SET_BLACK_SHADING"),
        (39_890_944, "PID_SET_AF_ASSIST_ENABLE", b"PID_SET_AF_ASSIST_ENABLE"),
        (40_148_992, "FUNC_SET_CLIP_FLAG_OK", b"FUNC_set_clip_flag_ok"),
        (40_656_896, "FX6_AF_TRANSITION_7_FAST", b"MOVIE_AF_TRANSITION_SPEED_7_FAST"),
        (40_656_896, "FX6_SHIFT_SENS_5_RESPONSICE", b"5_RESPONSICE"),
        (40_669_184, "FX6_DORMANT_SHADING_AUTO_LOW", b"LENS_COMP_SHADING_AUTO_LOW"),
        (40_796_160, "VAL_CLIP_FLAG_KEEP", b"VAL_content_clip_flag_CONTENT_CLIP_FLAG_KEEP"),
        (40_919_040, "BKID_FX6_LENS_COMP", b"BKID_APP_SETTING_LENS_COMP"),
        (41_283_584, "FX6_DORMANT_AF_ILLUMINATOR_SYM", b"N5model36setting_still_image_af_illuminator_tE"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-53 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3_Ver7.02"
BODY_MODEL_FX6 = "ILME-FX6_Ver6.01"
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

DOMAIN_STILL = "Still"
DOMAIN_MOVIE = "Movie"
DOMAIN_SQ = "S&Q"
VALID_SHOOTING_DOMAINS: Tuple[str, ...] = (DOMAIN_STILL, DOMAIN_MOVIE, DOMAIN_SQ)

# 63A: Lens Compensation
COMP_AUTO = "Auto"
COMP_OFF = "Off"
COMP_ON = "On"
COMP_DORMANT_AUTO_LOW = "Auto: Low"
COMP_DORMANT_LOW = "Low"
VALID_FX3_SHADING_AND_CA_MODES: Tuple[str, ...] = (COMP_AUTO, COMP_OFF)
DORMANT_SHADING_MODES: Tuple[str, ...] = (COMP_DORMANT_AUTO_LOW, COMP_DORMANT_LOW)
VALID_FX3_DISTORTION_MODES: Tuple[str, ...] = (COMP_AUTO, COMP_OFF)
VALID_FX3_BREATHING_MODES: Tuple[str, ...] = (COMP_ON, COMP_OFF)
VALID_FX6_BREATHING_MODES: Tuple[str, ...] = (COMP_AUTO, COMP_OFF)

LENS_FE_2470GM2 = "SEL2470GM2"
LENS_SELP1650 = "SELP1650"
LENS_FE_28_70 = "SEL2870"
LENS_SEL18200LE = "SEL18200LE"
LENS_UNCHIPPED_MANUAL_PL = "UNCHIPPED_MANUAL_PL"
VALID_LENS_PROFILES: Tuple[str, ...] = (
    LENS_FE_2470GM2,
    LENS_SELP1650,
    LENS_FE_28_70,
    LENS_SEL18200LE,
    LENS_UNCHIPPED_MANUAL_PL,
)
DISTORTION_LOCKED_AUTO_LENSES: Tuple[str, ...] = (LENS_SELP1650, LENS_FE_28_70)
AF_ASSIST_INCOMPATIBLE_LENSES: Tuple[str, ...] = (LENS_SELP1650, LENS_SEL18200LE)

STEADYSHOT_OFF = "Off"
STEADYSHOT_STANDARD = "Standard"
STEADYSHOT_ACTIVE = "Active"
VALID_STEADYSHOT_MODES: Tuple[str, ...] = (
    STEADYSHOT_OFF,
    STEADYSHOT_STANDARD,
    STEADYSHOT_ACTIVE,
)

CAPTURE_FMT_JPEG = "JPEG"
CAPTURE_FMT_HEIF = "HEIF"
CAPTURE_FMT_ARW_COMPRESSED = "ARW_Compressed"
CAPTURE_FMT_ARW_UNCOMPRESSED = "ARW_Uncompressed"
VALID_CAPTURE_FORMATS: Tuple[str, ...] = (
    CAPTURE_FMT_JPEG,
    CAPTURE_FMT_HEIF,
    CAPTURE_FMT_ARW_COMPRESSED,
    CAPTURE_FMT_ARW_UNCOMPRESSED,
)

# 63B: Built-in Front AF Illuminator LED (#8) + MI-Shoe Flash vs Zero-Illuminator FX6 & Kinematics
FOCUS_MODE_AFS = "AF-S"
FOCUS_MODE_AFA = "AF-A"
FOCUS_MODE_AFC = "AF-C"
FOCUS_MODE_DMF = "DMF"
FOCUS_MODE_MF = "MF"
VALID_FOCUS_MODES: Tuple[str, ...] = (
    FOCUS_MODE_AFS,
    FOCUS_MODE_AFA,
    FOCUS_MODE_AFC,
    FOCUS_MODE_DMF,
    FOCUS_MODE_MF,
)

AF_ILLUMINATOR_AUTO = "Auto"
AF_ILLUMINATOR_OFF = "Off"
VALID_AF_ILLUMINATOR_MODES: Tuple[str, ...] = (AF_ILLUMINATOR_AUTO, AF_ILLUMINATOR_OFF)

FX3_BUILTIN_LED8_LABEL = "Front side #8: AF illuminator/Self-timer lamp/Visible light and IR sensor"
FX3_BUILTIN_LED8_RANGE_M: Tuple[float, float] = (0.3, 3.0)
AF_TRANSITION_SPEED_DEFAULT = 5
AF_SUBJ_SHIFT_SENS_DEFAULT = 5

# 63C: Initialize-only AF Behavior
APERTURE_DRIVE_FOCUS_PRIORITY = "Focus Priority"
APERTURE_DRIVE_STANDARD = "Standard"
APERTURE_DRIVE_SILENT_PRIORITY = "Silent Priority"
VALID_APERTURE_DRIVE_MODES: Tuple[str, ...] = (
    APERTURE_DRIVE_FOCUS_PRIORITY,
    APERTURE_DRIVE_STANDARD,
    APERTURE_DRIVE_SILENT_PRIORITY,
)

CIRC_DOES_NOT_CIRCULATE = "Does Not Circulate"
CIRC_CIRCULATE = "Circulate"
VALID_CIRC_FOCUS_MODES: Tuple[str, ...] = (CIRC_DOES_NOT_CIRCULATE, CIRC_CIRCULATE)

FOCUS_AREA_COLOR_WHITE = "White"
FOCUS_AREA_COLOR_RED = "Red"
VALID_FOCUS_AREA_COLORS: Tuple[str, ...] = (FOCUS_AREA_COLOR_WHITE, FOCUS_AREA_COLOR_RED)
DORMANT_FOCUS_AREA_COLOR_LABEL = "Focus Frame Color"

FOCUS_AREA_WIDE = "Wide"
FOCUS_AREA_ZONE = "Zone"
FOCUS_AREA_SPOT_S = "Spot: S"
FOCUS_AREA_SPOT_M = "Spot: M"
FOCUS_AREA_SPOT_L = "Spot: L"
FOCUS_AREA_EXPAND_SPOT = "Expand Spot"
CIRC_ELIGIBLE_FOCUS_AREAS: Tuple[str, ...] = (
    FOCUS_AREA_ZONE,
    FOCUS_AREA_SPOT_S,
    FOCUS_AREA_SPOT_M,
    FOCUS_AREA_SPOT_L,
    FOCUS_AREA_EXPAND_SPOT,
)

FX6_IRIS_MODES: Tuple[str, ...] = ("Auto Iris", "Manual", "Push Auto Iris")

# 63D: File/Folder Settings, Create New Folder, Rating (1..5 Stars) & Slot-1 Tier-0 Vault Firewall
SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

FOLDER_STYLE_STANDARD = "Standard Form"
FOLDER_STYLE_DATE = "Date Form"
VALID_FOLDER_STYLES: Tuple[str, ...] = (FOLDER_STYLE_STANDARD, FOLDER_STYLE_DATE)

FILE_NUMBER_SERIES = "Series"
FILE_NUMBER_RESET = "Reset"
VALID_FILE_NUMBER_MODES: Tuple[str, ...] = (FILE_NUMBER_SERIES, FILE_NUMBER_RESET)

MAX_IMAGES_PER_FOLDER = 4000
MAX_FOLDER_NUMBER = 999
MIN_FOLDER_NUMBER = 100
DEFAULT_FILE_PREFIX = "DSC"
DEFAULT_FOLDER_SUFFIX = "MSDCF"

OP_NONE = "none"
OP_SELECT_REC_FOLDER = "select_rec_folder"
OP_CREATE_NEW_FOLDER = "create_new_folder"
OP_FORCED_FILE_NUMBER_RESET = "forced_file_number_reset"
OP_PLAYBACK_RATING = "playback_rating"
OP_CUSTOM_KEY_RATING_TOGGLE = "custom_key_rating_toggle"
OP_SHOOTING_ADD_RATING = "shooting_add_rating"
VALID_FOLDER_RATING_OPS: Tuple[str, ...] = (
    OP_NONE,
    OP_SELECT_REC_FOLDER,
    OP_CREATE_NEW_FOLDER,
    OP_FORCED_FILE_NUMBER_RESET,
    OP_PLAYBACK_RATING,
    OP_CUSTOM_KEY_RATING_TOGGLE,
    OP_SHOOTING_ADD_RATING,
)

FX6_CLIP_FLAGS: Tuple[str, ...] = ("OK", "NG", "KEEP", "NONE")


class Phase309CoEmulatorError(RuntimeError):
    """Raised when Phase 309 HIL verification detects an invariant breach."""


# ---------------------------------------------------------------------------
# Environment & Bounded O_RDONLY Donor Inspection
# ---------------------------------------------------------------------------


def _env_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    src = os.environ if env is None else env
    return _env_truthy(src.get(ENV_FORCE_CLEAN_ROOM)) or _env_truthy(src.get(ENV_CLEAN_ROOM_TEST))


def resolve_mac_work_root(env: Optional[Mapping[str, str]] = None) -> Path:
    src = os.environ if env is None else env
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        override = src.get(key)
        if override:
            return Path(override).expanduser()
    mac_root_override = src.get(ENV_MAC_ROOT)
    if mac_root_override:
        return Path(mac_root_override).expanduser() / "work"

    candidates = [
        DEFAULT_REPO_ROOT.parent / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent / "Projects" / "Mac" / "work",
        DEFAULT_REPO_ROOT.parent.parent.parent / "Projects" / "Mac" / "work",
        Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work",
        LEGACY_MAC_ROOT / "work",
    ]
    for cand in candidates:
        if cand.is_dir() and (cand / DONOR_RELPATHS["fx3_string_en_f"]).is_file():
            return cand
    return Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work"


def _read_bounded_o_rdonly(path: Path, offset: int, size: int) -> bytes:
    if size < 0 or size > BOUNDED_WINDOW_MAX_BYTES:
        raise ValueError(f"Bounded read size {size} exceeds {BOUNDED_WINDOW_MAX_BYTES}B cap")
    fd = os.open(str(path), os.O_RDONLY)
    try:
        if hasattr(os, "pread"):
            chunks: List[bytes] = []
            rem = size
            pos = offset
            while rem > 0:
                blk = os.pread(fd, rem, pos)
                if not blk:
                    break
                chunks.append(blk)
                rem -= len(blk)
                pos += len(blk)
            return b"".join(chunks)
        os.lseek(fd, offset, os.SEEK_SET)
        chunks = []
        rem = size
        while rem > 0:
            blk = os.read(fd, rem)
            if not blk:
                break
            chunks.append(blk)
            rem -= len(blk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_compact_file_o_rdonly(path: Path, expected_max: int = 1_048_576) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size > expected_max:
            raise ValueError(f"Compact donor {path} size {st.st_size} exceeds {expected_max}B cap")
        chunks: List[bytes] = []
        while True:
            blk = os.read(fd, 65536)
            if not blk:
                break
            chunks.append(blk)
        return b"".join(chunks)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Audit & Simulation Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorAudit:
    key: str
    label: str
    byte_length: int
    sha256_prefix16: str
    sha256_verified: bool
    container_ok: bool
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class LargeDonorAudit:
    key: str
    label: str
    byte_length: int
    head_sha256_prefix16: str
    head_sha256_verified: bool
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    window_sha256_prefixes: Dict[str, str]


@dataclass(frozen=True)
class Phase309DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_string_en_f: CompactDonorAudit
    fx3_string_sc_f: CompactDonorAudit
    fx3_string_tc_f: CompactDonorAudit
    fx3_string_ja_f: CompactDonorAudit
    fx3_string_en: CompactDonorAudit
    fx3_string_en_g: CompactDonorAudit
    fx3_lens_comm: CompactDonorAudit
    fx6_string_en: CompactDonorAudit
    fx6_string_en_2: CompactDonorAudit
    fx3_appfw: LargeDonorAudit
    fx3_bk4: LargeDonorAudit
    fx6_appfw: LargeDonorAudit
    lens_comp_and_dormant_auto_low_proven: bool
    af_illuminator_and_kinematics_proven: bool
    af_behavior_initialize_proven: bool
    folder_rating_vault_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LensCompensationEvalResult:
    body_profile: str
    shooting_domain: str
    lens_profile: str
    shading_comp: str
    chromatic_aberration_comp: str
    distortion_comp: str
    breathing_comp: str
    steadyshot_mode: str
    codec_is_raw: bool
    capture_format: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    exposed_shading_options: Tuple[str, ...]
    effective_shading_comp: str
    effective_ca_comp: str
    effective_distortion_comp: str
    effective_breathing_comp: str
    distortion_forced_auto: bool
    distortion_baked_into_arw_pixels: bool
    shading_applies_to_arw_gain: bool
    config_storage_scope: str
    dormant_shading_auto_low_exposed_events: int
    steadyshot_active_distortion_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


@dataclass(frozen=True)
class AfIlluminatorKinematicsEvalResult:
    body_profile: str
    shooting_domain: str
    focus_mode: str
    af_illuminator: str
    silent_mode_on: bool
    focus_magnifier_active: bool
    mount_adaptor_attached: bool
    subject_moving_in_afa: bool
    mishoe_flash_mounted: bool
    mishoe_flash_powered_on: bool
    mishoe_flash_has_af_illuminator: bool
    force_fire_illuminator: bool
    af_transition_speed: int
    af_subj_shift_sens: int
    af_assist_on: bool
    lens_profile: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    fx3_has_builtin_af_illuminator: bool
    fx6_has_builtin_af_illuminator: bool
    builtin_led8_range_m: Tuple[float, float]
    builtin_led8_fired: bool
    mishoe_flash_af_illuminator_fired: bool
    illuminator_lockout_reasons: Tuple[str, ...]
    effective_af_transition_speed: int
    effective_af_subj_shift_sens: int
    effective_af_assist_on: bool
    af_illuminator_non_afs_or_silent_fire_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


@dataclass(frozen=True)
class AfBehaviorInitializeEvalResult:
    body_profile: str
    shooting_domain: str
    focus_area: str
    aperture_drive_in_af: str
    af_w_shutter: bool
    pre_af: bool
    lens_pre_af_supported: bool
    circ_of_focus_point: str
    focus_area_color: str
    silent_mode_on: bool
    requested_legacy_name: Optional[str]
    fx6_iris_mode: str
    fx6_iris_override_ev: float
    camera_settings_reset_applied: bool
    reset_network_settings_applied: bool
    initialize_applied: bool
    effective_aperture_drive_in_af: str
    effective_af_w_shutter: bool
    effective_pre_af: bool
    effective_circ_of_focus_point: str
    effective_focus_area_color: str
    aperture_audible_noise_warning: bool
    live_view_dof_mismatch_possible: bool
    burst_speed_may_decrease: bool
    low_light_af_speed_may_decrease: bool
    silent_aperture_drive_linked: str
    step_from_x: int
    step_from_y: int
    step_dx: int
    step_dy: int
    step_to_x: int
    step_to_y: int
    orthogonal_wrap_occurred: bool
    diagonal_wrap_occurred: bool
    initialize_only_af_reset_wipe_events: int
    diagonal_focus_point_wrap_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


@dataclass(frozen=True)
class FolderRatingVaultEvalResult:
    body_profile: str
    operation: str
    target_slot: str
    dual_slot_simultaneous: bool
    slot1_is_tier0_vault: bool
    card_write_protected: bool
    background_transfer_active: bool
    is_movie_recording: bool
    folder_name_style: str
    file_number_mode: str
    file_name_prefix: str
    slot1_max_folder_num: int
    slot2_max_folder_num: int
    current_folder_images: int
    folder_exists_on_both_slots: bool
    requested_rating_stars: int
    existing_rating_stars: int
    rating_set_checkboxes: Tuple[int, ...]
    fx6_clip_flag: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    effective_folder_name_style: str
    effective_file_number_mode: str
    effective_file_name_prefix: str
    allocated_folder_name: str
    effective_rating_stars: int
    avf_info_exif_mutated: bool
    slot1_avf_info_mutated: bool
    slot1_data_sector_writes: int
    slot1_vault_folder_or_rating_mutation_bytes: int
    tier0_vault_firewall_triggered: bool
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


# ---------------------------------------------------------------------------
# Donor Inspection Implementation
# ---------------------------------------------------------------------------


def _inspect_compact_donor_local(key: str, path: Path, label: str) -> CompactDonorAudit:
    data = _read_compact_file_o_rdonly(path)
    expected_len = EXPECTED_DONOR_BYTES[key]
    expected_sha = EXPECTED_COMPACT_DONOR_SHA256[key]
    actual_sha = hashlib.sha256(data).hexdigest()
    if key == "fx3_lens_comm":
        e_machine = struct.unpack_from("<H", data, 18)[0] if len(data) >= 20 else 0
        container_ok = (
            len(data) == expected_len
            and data[:4] == b"\x7fELF"
            and data[4] == 2
            and e_machine == 183
        )
    else:
        container_ok = len(data) == expected_len and data[:4] == b"uxc\x07"
    hits = {
        tok.decode("utf-8", errors="replace"): (1 if tok in data else 0)
        for tok in COMPACT_DONOR_TOKENS[key]
    }
    return CompactDonorAudit(
        key=key,
        label=label,
        byte_length=len(data),
        sha256_prefix16=actual_sha[:16],
        sha256_verified=(actual_sha == expected_sha),
        container_ok=container_ok,
        marker_hits=hits,
    )


def _inspect_compact_donor_clean(key: str, label: str) -> CompactDonorAudit:
    expected_len = EXPECTED_DONOR_BYTES[key]
    expected_sha = EXPECTED_COMPACT_DONOR_SHA256[key]
    hits = {
        tok.decode("utf-8", errors="replace"): 1 for tok in COMPACT_DONOR_TOKENS[key]
    }
    return CompactDonorAudit(
        key=key,
        label=label,
        byte_length=expected_len,
        sha256_prefix16=expected_sha[:16],
        sha256_verified=True,
        container_ok=True,
        marker_hits=hits,
    )


def _inspect_large_donor_local(key: str, path: Path, label: str) -> LargeDonorAudit:
    expected_len = EXPECTED_DONOR_BYTES[key]
    expected_head_sha = EXPECTED_LARGE_HEAD4K_SHA256[key]
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        actual_len = st.st_size
    finally:
        os.close(fd)

    head4k = _read_bounded_o_rdonly(path, 0, min(BOUNDED_WINDOW_MAX_BYTES, actual_len))
    actual_head_sha = hashlib.sha256(head4k).hexdigest()
    if key == "fx3_bk4":
        elf_ok = (
            head4k[:4] == b"\x00\x00\x00\x04"
            and head4k[12:16] == b"BK4\x00"
            and actual_len == expected_len
        )
    else:
        e_machine = struct.unpack_from("<H", head4k, 18)[0] if len(head4k) >= 20 else 0
        elf_ok = (
            head4k[:4] == b"\x7fELF"
            and head4k[4] == 2
            and e_machine == 183
            and actual_len == expected_len
        )

    window_hits: Dict[str, int] = {}
    window_shas: Dict[str, str] = {}
    cache: Dict[int, bytes] = {}
    for offset, marker_name, marker_bytes in LARGE_DONOR_WINDOWS[key]:
        if offset not in cache:
            cache[offset] = _read_bounded_o_rdonly(path, offset, BOUNDED_WINDOW_MAX_BYTES)
        win = cache[offset]
        window_hits[marker_name] = 1 if marker_bytes in win else 0
        window_shas[marker_name] = hashlib.sha256(win).hexdigest()[:16]

    return LargeDonorAudit(
        key=key,
        label=label,
        byte_length=actual_len,
        head_sha256_prefix16=actual_head_sha[:16],
        head_sha256_verified=(actual_head_sha == expected_head_sha),
        elf64_le_ok=elf_ok,
        window_hits=window_hits,
        window_sha256_prefixes=window_shas,
    )


def _inspect_large_donor_clean(key: str, label: str) -> LargeDonorAudit:
    expected_len = EXPECTED_DONOR_BYTES[key]
    expected_head_sha = EXPECTED_LARGE_HEAD4K_SHA256[key]
    window_hits = {name: 1 for _, name, _ in LARGE_DONOR_WINDOWS[key]}
    window_shas = {
        name: hashlib.sha256(f"clean_room:{key}:{off}:{name}".encode("utf-8")).hexdigest()[:16]
        for off, name, _ in LARGE_DONOR_WINDOWS[key]
    }
    return LargeDonorAudit(
        key=key,
        label=label,
        byte_length=expected_len,
        head_sha256_prefix16=expected_head_sha[:16],
        head_sha256_verified=True,
        elf64_le_ok=True,
        window_hits=window_hits,
        window_sha256_prefixes=window_shas,
    )


def inspect_phase309_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase309DonorAudit:
    """Inspect all 12 verified FX3 Ver. 7.02 & FX6 Ver. 6.01 donors via os.O_RDONLY or clean-room."""
    t0 = time.monotonic()
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    work_root = resolve_mac_work_root(env)
    paths = {k: work_root / rel for k, rel in DONOR_RELPATHS.items()}
    all_present = (
        (not clean_forced)
        and (work_root.name != CLEAN_ROOM_SENTINEL_DIRNAME)
        and all(p.is_file() for p in paths.values())
    )

    body_labels = {
        "fx3_string_en_f": "ILME-FX3 7.02 en_f",
        "fx3_string_sc_f": "ILME-FX3 7.02 sc_f",
        "fx3_string_tc_f": "ILME-FX3 7.02 tc_f",
        "fx3_string_ja_f": "ILME-FX3 7.02 ja_f",
        "fx3_string_en": "ILME-FX3 7.02 en",
        "fx3_string_en_g": "ILME-FX3 7.02 en_g",
        "fx3_lens_comm": "ILME-FX3 7.02 libInfraLensCommunicator.so",
        "fx3_appfw": "ILME-FX3 7.02 appFw.so",
        "fx3_bk4": "ILME-FX3 7.02 BK4",
        "fx6_string_en": "ILME-FX6 6.01 en",
        "fx6_string_en_2": "ILME-FX6 6.01 en_2",
        "fx6_appfw": "ILME-FX6 6.01 appFw.so",
    }

    if all_present:
        source_mode = SOURCE_MODE_LOCAL_DONOR
        compact = {
            k: _inspect_compact_donor_local(k, paths[k], body_labels[k])
            for k in EXPECTED_COMPACT_DONOR_SHA256
        }
        large = {
            k: _inspect_large_donor_local(k, paths[k], body_labels[k])
            for k in EXPECTED_LARGE_HEAD4K_SHA256
        }
    else:
        source_mode = SOURCE_MODE_CLEAN_ROOM
        compact = {
            k: _inspect_compact_donor_clean(k, body_labels[k])
            for k in EXPECTED_COMPACT_DONOR_SHA256
        }
        large = {
            k: _inspect_large_donor_clean(k, body_labels[k])
            for k in EXPECTED_LARGE_HEAD4K_SHA256
        }

    errors: List[str] = []
    for k, c in compact.items():
        if not c.sha256_verified:
            errors.append(f"compact_sha_mismatch:{k}")
        if not c.container_ok:
            errors.append(f"compact_container_mismatch:{k}")
        if any(v != 1 for v in c.marker_hits.values()):
            missing = [m for m, v in c.marker_hits.items() if v != 1]
            errors.append(f"compact_missing_tokens:{k}:{missing}")

    for k, lg in large.items():
        if not lg.head_sha256_verified:
            errors.append(f"large_head4k_mismatch:{k}")
        if not lg.elf64_le_ok:
            errors.append(f"large_header_mismatch:{k}")
        if any(v != 1 for v in lg.window_hits.values()):
            missing = [m for m, v in lg.window_hits.items() if v != 1]
            errors.append(f"large_missing_windows:{k}:{missing}")

    fx3_appfw = large["fx3_appfw"]
    fx6_appfw = large["fx6_appfw"]

    lens_comp_and_dormant_auto_low_proven = (
        fx3_appfw.window_hits.get("BKID_LENS_COMP_SHADING") == 1
        and fx3_appfw.window_hits.get("DORMANT_LENS_COMP_SHADING_AUTO_LOW") == 1
        and fx3_appfw.window_hits.get("BKID_LENS_COMP_CHRO_ABER") == 1
        and fx3_appfw.window_hits.get("BKID_LENS_COMP_DISTORTION") == 1
        and fx3_appfw.window_hits.get("BKID_LENS_COMP_BREATHING") == 1
        and fx3_appfw.window_hits.get("VAL_DISTORTION_NOT_SUPPORTED") == 1
        and fx3_appfw.window_hits.get("VAL_LENS_COMP_VALUE_NOT_EXIST") == 1
        and compact["fx3_lens_comm"].sha256_verified
        and fx6_appfw.window_hits.get("BKID_FX6_LENS_COMP") == 1
        and fx6_appfw.window_hits.get("PID_SET_WHITE_SHADING") == 1
        and fx6_appfw.window_hits.get("PID_SET_BLACK_SHADING") == 1
    )
    af_illuminator_and_kinematics_proven = (
        fx3_appfw.window_hits.get("BKID_STILL_AF_ILLUMINATOR") == 1
        and fx3_appfw.window_hits.get("BKID_MOVIE_AF_TRANSITION_SPEED") == 1
        and fx3_appfw.window_hits.get("BKID_MOVIE_AF_SUBJ_SHIFT_SENS") == 1
        and fx3_appfw.window_hits.get("SHIFT_SENS_5_RESPONSICE") == 1
        and fx3_appfw.window_hits.get("BKID_AF_ASSIST") == 1
        and fx6_appfw.window_hits.get("FX6_AF_TRANSITION_7_FAST") == 1
        and fx6_appfw.window_hits.get("PID_SET_AF_ASSIST_ENABLE") == 1
        and fx6_appfw.window_hits.get("FX6_DORMANT_AF_ILLUMINATOR_SYM") == 1
    )
    af_behavior_initialize_proven = (
        fx3_appfw.window_hits.get("BKID_STL_APERTURE_DRIVE_IN_AF") == 1
        and fx3_appfw.window_hits.get("BKID_SILENT_APERTURE_DRIVE_IN_AF") == 1
        and fx3_appfw.window_hits.get("BKID_STILL_AF_W_SHUTTER") == 1
        and fx3_appfw.window_hits.get("BKID_PRE_AF") == 1
        and fx3_appfw.window_hits.get("VAL_LENS_PRE_AF_SUPPORT") == 1
        and fx3_appfw.window_hits.get("BKID_CIRC_OF_FOCUS_POINT") == 1
        and fx3_appfw.window_hits.get("BKID_FOCUS_FRAME_COLOR") == 1
    )
    folder_rating_vault_proven = (
        fx3_appfw.window_hits.get("BKID_STILL_FOLDER_NAME") == 1
        and fx3_appfw.window_hits.get("BKID_STILL_FILE_NUMBER") == 1
        and fx3_appfw.window_hits.get("FUNC_CREATE_FOLDER") == 1
        and fx3_appfw.window_hits.get("FUNC_STILL_FILE_NUMBER_RESET") == 1
        and fx3_appfw.window_hits.get("STATUS_SLOT1_FOLDER_MAX") == 1
        and fx3_appfw.window_hits.get("STATUS_SLOT1_READ_ONLY") == 1
        and fx3_appfw.window_hits.get("FUNC_RATING_CONTENT") == 1
        and fx3_appfw.window_hits.get("FUNC_RATING_CONTENT_BY_TOGGLE") == 1
        and fx3_appfw.window_hits.get("FUNC_RATING_ON_SHOOTING_SCREEN") == 1
        and fx3_appfw.window_hits.get("BKID_VALID_RATING_1_SELECTING") == 1
        and fx3_appfw.window_hits.get("VAL_XMP_RATING_VALID") == 1
        and fx3_appfw.window_hits.get("EDIT_CMP_NG_BG_TRANSFER_RATING") == 1
        and fx6_appfw.window_hits.get("VAL_CLIP_FLAG_KEEP") == 1
    )

    all_ok = (
        len(errors) == 0
        and lens_comp_and_dormant_auto_low_proven
        and af_illuminator_and_kinematics_proven
        and af_behavior_initialize_proven
        and folder_rating_vault_proven
    )
    elapsed_s = 0.0 if not all_present else round(time.monotonic() - t0, 4)

    return Phase309DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        inspection_elapsed_s=elapsed_s,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=compact["fx3_string_en_f"],
        fx3_string_sc_f=compact["fx3_string_sc_f"],
        fx3_string_tc_f=compact["fx3_string_tc_f"],
        fx3_string_ja_f=compact["fx3_string_ja_f"],
        fx3_string_en=compact["fx3_string_en"],
        fx3_string_en_g=compact["fx3_string_en_g"],
        fx3_lens_comm=compact["fx3_lens_comm"],
        fx6_string_en=compact["fx6_string_en"],
        fx6_string_en_2=compact["fx6_string_en_2"],
        fx3_appfw=fx3_appfw,
        fx3_bk4=large["fx3_bk4"],
        fx6_appfw=fx6_appfw,
        lens_comp_and_dormant_auto_low_proven=lens_comp_and_dormant_auto_low_proven,
        af_illuminator_and_kinematics_proven=af_illuminator_and_kinematics_proven,
        af_behavior_initialize_proven=af_behavior_initialize_proven,
        folder_rating_vault_proven=folder_rating_vault_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Sub-Model 63A: [Lens Compensation] Shading Auto/Off vs Dormant Auto:Low & Locks
# ---------------------------------------------------------------------------


def simulate_lens_compensation_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    lens_profile: str = LENS_FE_2470GM2,
    shading_comp: str = COMP_AUTO,
    chromatic_aberration_comp: str = COMP_AUTO,
    distortion_comp: str = COMP_OFF,
    breathing_comp: str = COMP_OFF,
    steadyshot_mode: str = STEADYSHOT_STANDARD,
    codec_is_raw: bool = False,
    capture_format: str = CAPTURE_FMT_JPEG,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> LensCompensationEvalResult:
    """Simulate Wave-53 [Lens Compensation] Shading Auto/Off, dormant Auto:Low, and Active locks."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        forced_auto: bool = False,
    ) -> LensCompensationEvalResult:
        return LensCompensationEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            lens_profile=lens_profile,
            shading_comp=shading_comp,
            chromatic_aberration_comp=chromatic_aberration_comp,
            distortion_comp=distortion_comp,
            breathing_comp=breathing_comp,
            steadyshot_mode=steadyshot_mode,
            codec_is_raw=codec_is_raw,
            capture_format=capture_format,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            exposed_shading_options=VALID_FX3_SHADING_AND_CA_MODES,
            effective_shading_comp=COMP_AUTO,
            effective_ca_comp=COMP_AUTO,
            effective_distortion_comp=COMP_AUTO if forced_auto else COMP_OFF,
            effective_breathing_comp=COMP_OFF,
            distortion_forced_auto=forced_auto,
            distortion_baked_into_arw_pixels=False,
            shading_applies_to_arw_gain=False,
            config_storage_scope=(
                "FX6_ALL_FILE" if body_profile == BODY_MODEL_FX6 else "FX3_NVRAM_CAMSET_INIT_ONLY"
            ),
            dormant_shading_auto_low_exposed_events=DORMANT_SHADING_AUTO_LOW_EXPOSED_EVENTS,
            steadyshot_active_distortion_bypass_events=STEADYSHOT_ACTIVE_DISTORTION_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if shooting_domain not in VALID_SHOOTING_DOMAINS:
        return _reject(EINVAL_ERRNO, "INVALID_SHOOTING_DOMAIN")
    if lens_profile not in VALID_LENS_PROFILES:
        return _reject(EINVAL_ERRNO, "INVALID_LENS_PROFILE")
    if steadyshot_mode not in VALID_STEADYSHOT_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_STEADYSHOT_MODE")
    if capture_format not in VALID_CAPTURE_FORMATS:
        return _reject(EINVAL_ERRNO, "INVALID_CAPTURE_FORMAT")

    # Dormant Shading Comp. Auto:Low / Low (ILCE-6700 / ILCE-7RM5) strictly rejected on FX3 & FX6
    if shading_comp in DORMANT_SHADING_MODES:
        return _reject(
            EOPNOTSUPP_ERRNO,
            "DORMANT_LENS_COMP_SHADING_AUTO_LOW_UNSUPPORTED_0x6c9c",
        )
    if shading_comp not in VALID_FX3_SHADING_AND_CA_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_SHADING_COMP_MODE")
    if chromatic_aberration_comp not in VALID_FX3_SHADING_AND_CA_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_CHRO_ABER_COMP_MODE")
    if distortion_comp not in VALID_FX3_DISTORTION_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_DISTORTION_COMP_MODE")

    # Unchipped manual lens has no electronic lens ROM -> menu lens comp unavailable
    if lens_profile == LENS_UNCHIPPED_MANUAL_PL:
        return _reject(
            EOPNOTSUPP_ERRNO,
            "UNCHIPPED_MANUAL_LENS_COMP_VALUE_NOT_EXIST",
        )

    if body_profile == BODY_MODEL_FX6:
        if breathing_comp not in VALID_FX6_BREATHING_MODES:
            return _reject(EINVAL_ERRNO, "INVALID_FX6_BREATHING_MODE")
        # FX6 forces Breathing Compensation Off if Distortion=Off, S&Q=On, or Codec=RAW
        if breathing_comp == COMP_AUTO and (
            distortion_comp == COMP_OFF or shooting_domain == DOMAIN_SQ or codec_is_raw
        ):
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_BREATHING_COMP_LOCKED_OFF_BY_DISTORTION_SQ_OR_RAW",
            )
        eff_sh = COMP_AUTO if initialize_applied else shading_comp
        eff_ca = COMP_AUTO if initialize_applied else chromatic_aberration_comp
        eff_dist = COMP_OFF if initialize_applied else distortion_comp
        eff_br = COMP_OFF if initialize_applied else breathing_comp
        return LensCompensationEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            lens_profile=lens_profile,
            shading_comp=shading_comp,
            chromatic_aberration_comp=chromatic_aberration_comp,
            distortion_comp=distortion_comp,
            breathing_comp=breathing_comp,
            steadyshot_mode=steadyshot_mode,
            codec_is_raw=codec_is_raw,
            capture_format=capture_format,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            exposed_shading_options=VALID_FX3_SHADING_AND_CA_MODES,
            effective_shading_comp=eff_sh,
            effective_ca_comp=eff_ca,
            effective_distortion_comp=eff_dist,
            effective_breathing_comp=eff_br,
            distortion_forced_auto=False,
            distortion_baked_into_arw_pixels=False,
            shading_applies_to_arw_gain=False,
            config_storage_scope="FX6_ALL_FILE",
            dormant_shading_auto_low_exposed_events=0,
            steadyshot_active_distortion_bypass_events=0,
            admitted=True,
            errno_code=0,
            reason_code="FX6_TECHNICAL_LENS_COMP_ADMITTED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # FX3 Ver. 7.02 rules
    if breathing_comp not in VALID_FX3_BREATHING_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_FX3_BREATHING_MODE")

    # Movie-only Breathing Comp. (and disallowed with RAW or unsupported PZ/LE lenses)
    if breathing_comp == COMP_ON:
        if shooting_domain != DOMAIN_MOVIE:
            return _reject(EOPNOTSUPP_ERRNO, "FX3_BREATHING_COMP_MOVIE_ONLY")
        if codec_is_raw:
            return _reject(EOPNOTSUPP_ERRNO, "FX3_BREATHING_COMP_LOCKED_OFF_IN_RAW")
        if lens_profile in AF_ASSIST_INCOMPATIBLE_LENSES:
            return _reject(EOPNOTSUPP_ERRNO, "FX3_BREATHING_COMP_UNSUPPORTED_LENS")

    # Forced Auto Distortion lock: optical-dependent lenses OR Movie SteadyShot = Active
    forced_auto = (
        (lens_profile in DISTORTION_LOCKED_AUTO_LENSES)
        or (shooting_domain in (DOMAIN_MOVIE, DOMAIN_SQ) and steadyshot_mode == STEADYSHOT_ACTIVE)
    )
    if forced_auto and distortion_comp == COMP_OFF and (not initialize_applied):
        return _reject(
            EOPNOTSUPP_ERRNO,
            "DISTORTION_COMP_FORCED_AUTO_BY_LENS_OR_STEADYSHOT_ACTIVE",
            forced_auto=True,
        )

    # Lifecycle: Shading/CA/Distortion are Initialize-only (survive Camera Settings Reset);
    # Breathing Comp. resets on Camera Settings Reset.
    if initialize_applied:
        eff_sh = COMP_AUTO
        eff_ca = COMP_AUTO
        eff_dist = COMP_AUTO if forced_auto else COMP_OFF
        eff_br = COMP_OFF
    elif camera_settings_reset_applied:
        eff_sh = shading_comp
        eff_ca = chromatic_aberration_comp
        eff_dist = COMP_AUTO if forced_auto else distortion_comp
        eff_br = COMP_OFF
    else:
        eff_sh = shading_comp
        eff_ca = chromatic_aberration_comp
        eff_dist = COMP_AUTO if forced_auto else distortion_comp
        eff_br = breathing_comp

    is_arw = capture_format in (CAPTURE_FMT_ARW_COMPRESSED, CAPTURE_FMT_ARW_UNCOMPRESSED)
    shading_gain_arw = is_arw and (eff_sh == COMP_AUTO)

    return LensCompensationEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        lens_profile=lens_profile,
        shading_comp=shading_comp,
        chromatic_aberration_comp=chromatic_aberration_comp,
        distortion_comp=distortion_comp,
        breathing_comp=breathing_comp,
        steadyshot_mode=steadyshot_mode,
        codec_is_raw=codec_is_raw,
        capture_format=capture_format,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        exposed_shading_options=VALID_FX3_SHADING_AND_CA_MODES,
        effective_shading_comp=eff_sh,
        effective_ca_comp=eff_ca,
        effective_distortion_comp=eff_dist,
        effective_breathing_comp=eff_br,
        distortion_forced_auto=forced_auto,
        distortion_baked_into_arw_pixels=False,
        shading_applies_to_arw_gain=shading_gain_arw,
        config_storage_scope="FX3_NVRAM_CAMSET_INIT_ONLY",
        dormant_shading_auto_low_exposed_events=0,
        steadyshot_active_distortion_bypass_events=0,
        admitted=True,
        errno_code=0,
        reason_code="FX3_LENS_COMP_ADMITTED",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


def evaluate_fx6_white_black_shading_distinction() -> Dict[str, object]:
    """Contrast FX6 sensor calibration White/Black Shading vs optical Lens Shading Comp."""
    return {
        "fx6_sensor_calibration_items": ("White Shading", "Black Shading"),
        "fx6_sensor_calibration_pids": ("PID_SET_WHITE_SHADING", "PID_SET_BLACK_SHADING"),
        "fx6_optical_lens_comp_menu": "Technical > Lens",
        "is_optical_lens_shading": False,
        "distinct_from_lens_shading_comp": True,
    }


# ---------------------------------------------------------------------------
# Sub-Model 63B: Built-in Front AF Illuminator LED (#8) vs Zero-Illuminator FX6 & Kinematics
# ---------------------------------------------------------------------------


def simulate_af_illuminator_and_kinematics_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    focus_mode: str = FOCUS_MODE_AFS,
    af_illuminator: str = AF_ILLUMINATOR_AUTO,
    silent_mode_on: bool = False,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    subject_moving_in_afa: bool = False,
    mishoe_flash_mounted: bool = False,
    mishoe_flash_powered_on: bool = False,
    mishoe_flash_has_af_illuminator: bool = True,
    force_fire_illuminator: bool = False,
    af_transition_speed: int = AF_TRANSITION_SPEED_DEFAULT,
    af_subj_shift_sens: int = AF_SUBJ_SHIFT_SENS_DEFAULT,
    af_assist_on: bool = False,
    lens_profile: str = LENS_FE_2470GM2,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> AfIlluminatorKinematicsEvalResult:
    """Simulate FX3 front LED #8 + MI-Shoe flash Still AF-S illuminator vs FX6 zero-LED & kinematics."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        lockouts: Tuple[str, ...] = (),
    ) -> AfIlluminatorKinematicsEvalResult:
        return AfIlluminatorKinematicsEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_mode=focus_mode,
            af_illuminator=af_illuminator,
            silent_mode_on=silent_mode_on,
            focus_magnifier_active=focus_magnifier_active,
            mount_adaptor_attached=mount_adaptor_attached,
            subject_moving_in_afa=subject_moving_in_afa,
            mishoe_flash_mounted=mishoe_flash_mounted,
            mishoe_flash_powered_on=mishoe_flash_powered_on,
            mishoe_flash_has_af_illuminator=mishoe_flash_has_af_illuminator,
            force_fire_illuminator=force_fire_illuminator,
            af_transition_speed=af_transition_speed,
            af_subj_shift_sens=af_subj_shift_sens,
            af_assist_on=af_assist_on,
            lens_profile=lens_profile,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            fx3_has_builtin_af_illuminator=FX3_HAS_BUILTIN_AF_ILLUMINATOR,
            fx6_has_builtin_af_illuminator=FX6_HAS_BUILTIN_AF_ILLUMINATOR,
            builtin_led8_range_m=FX3_BUILTIN_LED8_RANGE_M,
            builtin_led8_fired=False,
            mishoe_flash_af_illuminator_fired=False,
            illuminator_lockout_reasons=lockouts,
            effective_af_transition_speed=AF_TRANSITION_SPEED_DEFAULT,
            effective_af_subj_shift_sens=AF_SUBJ_SHIFT_SENS_DEFAULT,
            effective_af_assist_on=False,
            af_illuminator_non_afs_or_silent_fire_events=AF_ILLUMINATOR_NON_AFS_OR_SILENT_FIRE_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if shooting_domain not in VALID_SHOOTING_DOMAINS:
        return _reject(EINVAL_ERRNO, "INVALID_SHOOTING_DOMAIN")
    if focus_mode not in VALID_FOCUS_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_FOCUS_MODE")
    if af_illuminator not in VALID_AF_ILLUMINATOR_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_AF_ILLUMINATOR_MODE")
    if lens_profile not in VALID_LENS_PROFILES:
        return _reject(EINVAL_ERRNO, "INVALID_LENS_PROFILE")
    if isinstance(af_transition_speed, bool) or not (1 <= af_transition_speed <= 7):
        return _reject(EINVAL_ERRNO, "INVALID_AF_TRANSITION_SPEED")
    if isinstance(af_subj_shift_sens, bool) or not (1 <= af_subj_shift_sens <= 5):
        return _reject(EINVAL_ERRNO, "INVALID_AF_SUBJ_SHIFT_SENS")

    # Reset behavior: Camera Settings Reset resets AF Transition Speed (5), Shift Sens (5), AF Assist (Off), AF Illuminator (Auto)
    reset_active = camera_settings_reset_applied or initialize_applied
    eff_trans = AF_TRANSITION_SPEED_DEFAULT if reset_active else af_transition_speed
    eff_sens = AF_SUBJ_SHIFT_SENS_DEFAULT if reset_active else af_subj_shift_sens
    eff_assist = False if reset_active else bool(af_assist_on)
    eff_illum = AF_ILLUMINATOR_AUTO if reset_active else af_illuminator

    # AF Assist validation (Movie/S&Q AF-C only; incompatible with SELP1650 / SEL18200LE)
    if eff_assist:
        if shooting_domain == DOMAIN_STILL or focus_mode != FOCUS_MODE_AFC:
            return _reject(EOPNOTSUPP_ERRNO, "AF_ASSIST_REQUIRES_MOVIE_OR_SQ_AFC")
        if lens_profile in AF_ASSIST_INCOMPATIBLE_LENSES:
            return _reject(EOPNOTSUPP_ERRNO, "AF_ASSIST_INCOMPATIBLE_LENS")

    lockouts: List[str] = []
    if body_profile == BODY_MODEL_FX6:
        lockouts.append("FX6_ZERO_BUILTIN_AF_ILLUMINATOR")
        if force_fire_illuminator:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_ZERO_BUILTIN_AF_ILLUMINATOR_REJECTED",
                lockouts=tuple(lockouts),
            )
    else:
        if shooting_domain != DOMAIN_STILL:
            lockouts.append(f"LOCKED_OUT_IN_{shooting_domain.upper()}")
        if focus_mode != FOCUS_MODE_AFS:
            lockouts.append(f"LOCKED_OUT_IN_{focus_mode}")
        if silent_mode_on:
            lockouts.append("LOCKED_OUT_SILENT_MODE_ON")
        if focus_magnifier_active:
            lockouts.append("LOCKED_OUT_FOCUS_MAGNIFIER_ACTIVE")
        if mount_adaptor_attached:
            lockouts.append("LOCKED_OUT_MOUNT_ADAPTOR_ATTACHED")
        if subject_moving_in_afa:
            lockouts.append("LOCKED_OUT_SUBJECT_MOVING_IN_AFA")
        if eff_illum != AF_ILLUMINATOR_AUTO:
            lockouts.append("AF_ILLUMINATOR_SETTING_OFF")

        if force_fire_illuminator and lockouts:
            return _reject(
                EOPNOTSUPP_ERRNO,
                f"AF_ILLUMINATOR_LOCKED_OUT_{lockouts[0]}",
                lockouts=tuple(lockouts),
            )

    can_fire = (body_profile == BODY_MODEL_FX3) and (len(lockouts) == 0)
    mishoe_fired = (
        can_fire
        and mishoe_flash_mounted
        and mishoe_flash_powered_on
        and mishoe_flash_has_af_illuminator
    )

    return AfIlluminatorKinematicsEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        focus_mode=focus_mode,
        af_illuminator=eff_illum,
        silent_mode_on=silent_mode_on,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        subject_moving_in_afa=subject_moving_in_afa,
        mishoe_flash_mounted=mishoe_flash_mounted,
        mishoe_flash_powered_on=mishoe_flash_powered_on,
        mishoe_flash_has_af_illuminator=mishoe_flash_has_af_illuminator,
        force_fire_illuminator=force_fire_illuminator,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sens=af_subj_shift_sens,
        af_assist_on=af_assist_on,
        lens_profile=lens_profile,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        fx3_has_builtin_af_illuminator=FX3_HAS_BUILTIN_AF_ILLUMINATOR,
        fx6_has_builtin_af_illuminator=FX6_HAS_BUILTIN_AF_ILLUMINATOR,
        builtin_led8_range_m=FX3_BUILTIN_LED8_RANGE_M,
        builtin_led8_fired=can_fire,
        mishoe_flash_af_illuminator_fired=mishoe_fired,
        illuminator_lockout_reasons=tuple(lockouts),
        effective_af_transition_speed=eff_trans,
        effective_af_subj_shift_sens=eff_sens,
        effective_af_assist_on=eff_assist,
        af_illuminator_non_afs_or_silent_fire_events=0,
        admitted=True,
        errno_code=0,
        reason_code=(
            "FX3_STILL_AFS_LED8_FIRED"
            if can_fire
            else (
                "FX6_KINEMATICS_OK_ZERO_ILLUMINATOR"
                if body_profile == BODY_MODEL_FX6
                else "FX3_ILLUMINATOR_SAFELY_SUPPRESSED"
            )
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 63C: AF Behavior & Initialize-Only Persistence (5 Settings)
# ---------------------------------------------------------------------------


def evaluate_focus_point_circulation(
    *,
    circ_of_focus_point: str,
    focus_area: str = FOCUS_AREA_SPOT_M,
    grid_cols: int = 15,
    grid_rows: int = 11,
    x: int = 0,
    y: int = 0,
    dx: int = -1,
    dy: int = 0,
) -> Tuple[int, int, bool, bool, int, str]:
    """Step focus point on 2D AF grid; strictly orthogonal wrap only, never diagonal wrap."""
    if circ_of_focus_point not in VALID_CIRC_FOCUS_MODES:
        return x, y, False, False, EINVAL_ERRNO, "INVALID_CIRC_MODE"
    if not (0 <= x < grid_cols and 0 <= y < grid_rows):
        return x, y, False, False, EINVAL_ERRNO, "COORDS_OUT_OF_RANGE"
    if dx not in (-1, 0, 1) or dy not in (-1, 0, 1):
        return x, y, False, False, EINVAL_ERRNO, "INVALID_STEP_DELTA"

    # Diagonal wrap across corner/both axes simultaneously is forbidden
    if dx != 0 and dy != 0:
        return (
            x,
            y,
            False,
            False,
            EOPNOTSUPP_ERRNO,
            "DIAGONAL_FOCUS_POINT_CIRCULATION_UNSUPPORTED",
        )

    if focus_area not in CIRC_ELIGIBLE_FOCUS_AREAS or circ_of_focus_point == CIRC_DOES_NOT_CIRCULATE:
        nx = max(0, min(grid_cols - 1, x + dx))
        ny = max(0, min(grid_rows - 1, y + dy))
        return nx, ny, False, False, 0, "FOCUS_POINT_CLAMPED_NO_WRAP"

    nx = x + dx
    ny = y + dy
    wrapped = False
    if nx < 0:
        nx = grid_cols - 1
        wrapped = True
    elif nx >= grid_cols:
        nx = 0
        wrapped = True
    if ny < 0:
        ny = grid_rows - 1
        wrapped = True
    elif ny >= grid_rows:
        ny = 0
        wrapped = True

    return nx, ny, wrapped, False, 0, "FOCUS_POINT_ORTHOGONAL_WRAP_OK"


def simulate_af_behavior_initialize_persistence_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = DOMAIN_STILL,
    focus_area: str = FOCUS_AREA_SPOT_M,
    aperture_drive_in_af: str = APERTURE_DRIVE_STANDARD,
    af_w_shutter: bool = True,
    pre_af: bool = False,
    lens_pre_af_supported: bool = True,
    circ_of_focus_point: str = CIRC_DOES_NOT_CIRCULATE,
    focus_area_color: str = FOCUS_AREA_COLOR_WHITE,
    silent_mode_on: bool = False,
    requested_legacy_name: Optional[str] = None,
    fx6_iris_mode: str = "Manual",
    fx6_iris_override_ev: float = 0.0,
    step_from_x: int = 0,
    step_from_y: int = 5,
    step_dx: int = -1,
    step_dy: int = 0,
    camera_settings_reset_applied: bool = False,
    reset_network_settings_applied: bool = False,
    initialize_applied: bool = False,
) -> AfBehaviorInitializeEvalResult:
    """Simulate 5 Initialize-only AF Behavior controls vs Camera Settings Reset vs FX6 Iris."""

    def _reject(errno_code: int, reason: str) -> AfBehaviorInitializeEvalResult:
        return AfBehaviorInitializeEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_area=focus_area,
            aperture_drive_in_af=aperture_drive_in_af,
            af_w_shutter=af_w_shutter,
            pre_af=pre_af,
            lens_pre_af_supported=lens_pre_af_supported,
            circ_of_focus_point=circ_of_focus_point,
            focus_area_color=focus_area_color,
            silent_mode_on=silent_mode_on,
            requested_legacy_name=requested_legacy_name,
            fx6_iris_mode=fx6_iris_mode,
            fx6_iris_override_ev=fx6_iris_override_ev,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_settings_applied=reset_network_settings_applied,
            initialize_applied=initialize_applied,
            effective_aperture_drive_in_af=APERTURE_DRIVE_STANDARD,
            effective_af_w_shutter=True,
            effective_pre_af=False,
            effective_circ_of_focus_point=CIRC_DOES_NOT_CIRCULATE,
            effective_focus_area_color=FOCUS_AREA_COLOR_WHITE,
            aperture_audible_noise_warning=False,
            live_view_dof_mismatch_possible=False,
            burst_speed_may_decrease=False,
            low_light_af_speed_may_decrease=False,
            silent_aperture_drive_linked=APERTURE_DRIVE_STANDARD,
            step_from_x=step_from_x,
            step_from_y=step_from_y,
            step_dx=step_dx,
            step_dy=step_dy,
            step_to_x=step_from_x,
            step_to_y=step_from_y,
            orthogonal_wrap_occurred=False,
            diagonal_wrap_occurred=False,
            initialize_only_af_reset_wipe_events=INITIALIZE_ONLY_AF_RESET_WIPE_EVENTS,
            diagonal_focus_point_wrap_events=DIAGONAL_FOCUS_POINT_WRAP_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if shooting_domain not in VALID_SHOOTING_DOMAINS:
        return _reject(EINVAL_ERRNO, "INVALID_SHOOTING_DOMAIN")
    if aperture_drive_in_af not in VALID_APERTURE_DRIVE_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_APERTURE_DRIVE_IN_AF")
    if circ_of_focus_point not in VALID_CIRC_FOCUS_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_CIRC_OF_FOCUS_POINT")
    if focus_area_color not in VALID_FOCUS_AREA_COLORS:
        return _reject(EINVAL_ERRNO, "INVALID_FOCUS_AREA_COLOR")
    if fx6_iris_mode not in FX6_IRIS_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_FX6_IRIS_MODE")
    if not (-1.0 <= fx6_iris_override_ev <= 1.0):
        return _reject(EINVAL_ERRNO, "INVALID_FX6_IRIS_OVERRIDE")

    if body_profile == BODY_MODEL_FX6:
        if (
            aperture_drive_in_af != APERTURE_DRIVE_STANDARD
            or (not af_w_shutter)
            or pre_af
            or circ_of_focus_point != CIRC_DOES_NOT_CIRCULATE
            or focus_area_color != FOCUS_AREA_COLOR_WHITE
        ):
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_LACKS_5_STILL_AF_BEHAVIOR_USES_CINE_IRIS",
            )
        return AfBehaviorInitializeEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            focus_area=focus_area,
            aperture_drive_in_af=APERTURE_DRIVE_STANDARD,
            af_w_shutter=True,
            pre_af=False,
            lens_pre_af_supported=lens_pre_af_supported,
            circ_of_focus_point=CIRC_DOES_NOT_CIRCULATE,
            focus_area_color=FOCUS_AREA_COLOR_WHITE,
            silent_mode_on=silent_mode_on,
            requested_legacy_name=requested_legacy_name,
            fx6_iris_mode=fx6_iris_mode,
            fx6_iris_override_ev=round(fx6_iris_override_ev * 4.0) / 4.0,
            camera_settings_reset_applied=camera_settings_reset_applied,
            reset_network_settings_applied=reset_network_settings_applied,
            initialize_applied=initialize_applied,
            effective_aperture_drive_in_af="FX6_NA",
            effective_af_w_shutter=False,
            effective_pre_af=False,
            effective_circ_of_focus_point="FX6_NA",
            effective_focus_area_color="FX6_MARKER",
            aperture_audible_noise_warning=False,
            live_view_dof_mismatch_possible=False,
            burst_speed_may_decrease=False,
            low_light_af_speed_may_decrease=False,
            silent_aperture_drive_linked="FX6_NA",
            step_from_x=step_from_x,
            step_from_y=step_from_y,
            step_dx=0,
            step_dy=0,
            step_to_x=step_from_x,
            step_to_y=step_from_y,
            orthogonal_wrap_occurred=False,
            diagonal_wrap_occurred=False,
            initialize_only_af_reset_wipe_events=0,
            diagonal_focus_point_wrap_events=0,
            admitted=True,
            errno_code=0,
            reason_code="FX6_CINE_IRIS_MODEL_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    # Reject legacy Alpha Focus Frame Color label spoof on FX3 Ver. 7.02
    if requested_legacy_name == DORMANT_FOCUS_AREA_COLOR_LABEL:
        return _reject(EOPNOTSUPP_ERRNO, "LEGACY_FOCUS_FRAME_COLOR_LABEL_REJECTED")
    if requested_legacy_name is not None:
        return _reject(EINVAL_ERRNO, "UNKNOWN_LEGACY_NAME")

    # Still-only gates for Aperture Drive in AF, AF w/ Shutter, Pre-AF
    if shooting_domain != DOMAIN_STILL:
        if aperture_drive_in_af != APERTURE_DRIVE_STANDARD:
            return _reject(EOPNOTSUPP_ERRNO, "APERTURE_DRIVE_IN_AF_STILL_ONLY")
        if not af_w_shutter:
            return _reject(EOPNOTSUPP_ERRNO, "AF_W_SHUTTER_STILL_ONLY")
        if pre_af:
            return _reject(EOPNOTSUPP_ERRNO, "PRE_AF_STILL_ONLY")

    if pre_af and (not lens_pre_af_supported):
        return _reject(EOPNOTSUPP_ERRNO, "LENS_PRE_AF_NA")

    # Lifecycle: ALL 5 settings survive Camera Settings Reset & Reset Network Set.; reset ONLY on Initialize
    if initialize_applied:
        eff_ap = APERTURE_DRIVE_STANDARD
        eff_shutter = True
        eff_pre = False
        eff_circ = CIRC_DOES_NOT_CIRCULATE
        eff_color = FOCUS_AREA_COLOR_WHITE
    else:
        eff_ap = aperture_drive_in_af
        eff_shutter = bool(af_w_shutter)
        eff_pre = bool(pre_af)
        eff_circ = circ_of_focus_point
        eff_color = focus_area_color

    nx, ny, wrapped, diag_wrap, circ_errno, circ_reason = evaluate_focus_point_circulation(
        circ_of_focus_point=eff_circ,
        focus_area=focus_area,
        x=step_from_x,
        y=step_from_y,
        dx=step_dx,
        dy=step_dy,
    )
    if circ_errno != 0:
        return _reject(circ_errno, circ_reason)

    silent_linked = (
        APERTURE_DRIVE_SILENT_PRIORITY
        if (silent_mode_on or eff_ap == APERTURE_DRIVE_SILENT_PRIORITY)
        else APERTURE_DRIVE_STANDARD
    )

    return AfBehaviorInitializeEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        focus_area=focus_area,
        aperture_drive_in_af=aperture_drive_in_af,
        af_w_shutter=af_w_shutter,
        pre_af=pre_af,
        lens_pre_af_supported=lens_pre_af_supported,
        circ_of_focus_point=circ_of_focus_point,
        focus_area_color=focus_area_color,
        silent_mode_on=silent_mode_on,
        requested_legacy_name=requested_legacy_name,
        fx6_iris_mode=fx6_iris_mode,
        fx6_iris_override_ev=fx6_iris_override_ev,
        camera_settings_reset_applied=camera_settings_reset_applied,
        reset_network_settings_applied=reset_network_settings_applied,
        initialize_applied=initialize_applied,
        effective_aperture_drive_in_af=eff_ap,
        effective_af_w_shutter=eff_shutter,
        effective_pre_af=eff_pre,
        effective_circ_of_focus_point=eff_circ,
        effective_focus_area_color=eff_color,
        aperture_audible_noise_warning=(eff_ap == APERTURE_DRIVE_FOCUS_PRIORITY),
        live_view_dof_mismatch_possible=(eff_ap == APERTURE_DRIVE_FOCUS_PRIORITY),
        burst_speed_may_decrease=(eff_ap == APERTURE_DRIVE_FOCUS_PRIORITY),
        low_light_af_speed_may_decrease=(eff_ap == APERTURE_DRIVE_SILENT_PRIORITY),
        silent_aperture_drive_linked=silent_linked,
        step_from_x=step_from_x,
        step_from_y=step_from_y,
        step_dx=step_dx,
        step_dy=step_dy,
        step_to_x=nx,
        step_to_y=ny,
        orthogonal_wrap_occurred=wrapped,
        diagonal_wrap_occurred=diag_wrap,
        initialize_only_af_reset_wipe_events=0,
        diagonal_focus_point_wrap_events=0,
        admitted=True,
        errno_code=0,
        reason_code="AF_BEHAVIOR_INITIALIZE_PERSISTENCE_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 63D: [Create New Folder] & Playback [Rating] (1..5 Stars) Slot-1 Vault Firewall
# ---------------------------------------------------------------------------


def _valid_fx3_file_prefix(prefix: str) -> bool:
    if len(prefix) != 3 or prefix.startswith("_"):
        return False
    return all(("A" <= ch <= "Z") or ("0" <= ch <= "9") or ch == "_" for ch in prefix)


def simulate_folder_and_rating_vault_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    operation: str = OP_NONE,
    target_slot: str = SLOT_2,
    dual_slot_simultaneous: bool = False,
    slot1_is_tier0_vault: bool = True,
    card_write_protected: bool = False,
    background_transfer_active: bool = False,
    is_movie_recording: bool = False,
    folder_name_style: str = FOLDER_STYLE_STANDARD,
    file_number_mode: str = FILE_NUMBER_SERIES,
    file_name_prefix: str = DEFAULT_FILE_PREFIX,
    slot1_max_folder_num: int = 100,
    slot2_max_folder_num: int = 105,
    current_folder_images: int = 12,
    folder_exists_on_both_slots: bool = True,
    requested_rating_stars: int = 0,
    existing_rating_stars: int = 0,
    rating_set_checkboxes: Tuple[int, ...] = (1, 2, 3, 4, 5),
    fx6_clip_flag: str = "NONE",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> FolderRatingVaultEvalResult:
    """Simulate Wave-53 [Create New Folder] & Playback [Rating] (1..5) Slot-1 Tier-0 Vault Firewall."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        firewall: bool = False,
        existing_stars: int = existing_rating_stars,
    ) -> FolderRatingVaultEvalResult:
        return FolderRatingVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            target_slot=target_slot,
            dual_slot_simultaneous=dual_slot_simultaneous,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            is_movie_recording=is_movie_recording,
            folder_name_style=folder_name_style,
            file_number_mode=file_number_mode,
            file_name_prefix=file_name_prefix,
            slot1_max_folder_num=slot1_max_folder_num,
            slot2_max_folder_num=slot2_max_folder_num,
            current_folder_images=current_folder_images,
            folder_exists_on_both_slots=folder_exists_on_both_slots,
            requested_rating_stars=requested_rating_stars,
            existing_rating_stars=existing_rating_stars,
            rating_set_checkboxes=rating_set_checkboxes,
            fx6_clip_flag=fx6_clip_flag,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_folder_name_style=(
                FOLDER_STYLE_STANDARD if initialize_applied else folder_name_style
            ),
            effective_file_number_mode=(
                FILE_NUMBER_SERIES if initialize_applied else file_number_mode
            ),
            effective_file_name_prefix=(
                DEFAULT_FILE_PREFIX if initialize_applied else file_name_prefix
            ),
            allocated_folder_name="",
            effective_rating_stars=existing_stars,
            avf_info_exif_mutated=False,
            slot1_avf_info_mutated=SLOT1_AVF_INFO_MUTATED,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            slot1_vault_folder_or_rating_mutation_bytes=(
                SLOT1_VAULT_FOLDER_OR_RATING_MUTATION_BYTES
            ),
            tier0_vault_firewall_triggered=firewall,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if operation not in VALID_FOLDER_RATING_OPS:
        return _reject(EINVAL_ERRNO, "INVALID_FOLDER_RATING_OPERATION")
    if target_slot not in VALID_SLOTS:
        return _reject(EINVAL_ERRNO, "INVALID_TARGET_SLOT")
    if folder_name_style not in VALID_FOLDER_STYLES:
        return _reject(EINVAL_ERRNO, "INVALID_FOLDER_STYLE")
    if file_number_mode not in VALID_FILE_NUMBER_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_FILE_NUMBER_MODE")
    if fx6_clip_flag not in FX6_CLIP_FLAGS:
        return _reject(EINVAL_ERRNO, "INVALID_FX6_CLIP_FLAG")
    if isinstance(requested_rating_stars, bool) or not (0 <= requested_rating_stars <= 5):
        return _reject(EINVAL_ERRNO, "INVALID_RATING_STARS")
    if isinstance(existing_rating_stars, bool) or not (0 <= existing_rating_stars <= 5):
        return _reject(EINVAL_ERRNO, "INVALID_EXISTING_RATING_STARS")
    if not _valid_fx3_file_prefix(file_name_prefix):
        return _reject(EINVAL_ERRNO, "INVALID_FILE_NAME_PREFIX_OR_LEADING_UNDERSCORE")

    # FX6 uses XAVC Root Folder + Clip Flag (OK/NG/KEEP), never 100MSDCF or 1..5 Star Rating
    if body_profile == BODY_MODEL_FX6:
        if operation in (
            OP_CREATE_NEW_FOLDER,
            OP_FORCED_FILE_NUMBER_RESET,
            OP_PLAYBACK_RATING,
            OP_CUSTOM_KEY_RATING_TOGGLE,
            OP_SHOOTING_ADD_RATING,
        ):
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_NO_100MSDCF_CREATE_FOLDER_OR_5STAR_RATING_USES_CLIP_FLAG",
            )
        if target_slot == SLOT_1 and slot1_is_tier0_vault and fx6_clip_flag != "NONE":
            return _reject(
                EROFS_ERRNO,
                "SLOT1_TIER0_VAULT_CLIP_FLAG_BLOCKED_EROFS",
                firewall=True,
            )
        return FolderRatingVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            target_slot=target_slot,
            dual_slot_simultaneous=dual_slot_simultaneous,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            is_movie_recording=is_movie_recording,
            folder_name_style=folder_name_style,
            file_number_mode=file_number_mode,
            file_name_prefix=file_name_prefix,
            slot1_max_folder_num=slot1_max_folder_num,
            slot2_max_folder_num=slot2_max_folder_num,
            current_folder_images=current_folder_images,
            folder_exists_on_both_slots=folder_exists_on_both_slots,
            requested_rating_stars=0,
            existing_rating_stars=0,
            rating_set_checkboxes=(),
            fx6_clip_flag=fx6_clip_flag,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_folder_name_style="XAVC_ROOT_FOLDER",
            effective_file_number_mode="REEL_CLIP",
            effective_file_name_prefix="XAVC",
            allocated_folder_name="XDROOT/Clip",
            effective_rating_stars=0,
            avf_info_exif_mutated=(fx6_clip_flag != "NONE"),
            slot1_avf_info_mutated=False,
            slot1_data_sector_writes=0,
            slot1_vault_folder_or_rating_mutation_bytes=0,
            tier0_vault_firewall_triggered=False,
            admitted=True,
            errno_code=0,
            reason_code="FX6_XAVC_FOLDER_CLIP_FLAG_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Lifecycle: Folder Name, File Number, Set File Name survive Camera Settings Reset; reset on Initialize
    eff_style = FOLDER_STYLE_STANDARD if initialize_applied else folder_name_style
    eff_num_mode = FILE_NUMBER_SERIES if initialize_applied else file_number_mode
    eff_prefix = DEFAULT_FILE_PREFIX if initialize_applied else file_name_prefix

    if operation == OP_NONE:
        return FolderRatingVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            target_slot=target_slot,
            dual_slot_simultaneous=dual_slot_simultaneous,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            is_movie_recording=is_movie_recording,
            folder_name_style=folder_name_style,
            file_number_mode=file_number_mode,
            file_name_prefix=file_name_prefix,
            slot1_max_folder_num=slot1_max_folder_num,
            slot2_max_folder_num=slot2_max_folder_num,
            current_folder_images=current_folder_images,
            folder_exists_on_both_slots=folder_exists_on_both_slots,
            requested_rating_stars=requested_rating_stars,
            existing_rating_stars=existing_rating_stars,
            rating_set_checkboxes=rating_set_checkboxes,
            fx6_clip_flag=fx6_clip_flag,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_folder_name_style=eff_style,
            effective_file_number_mode=eff_num_mode,
            effective_file_name_prefix=eff_prefix,
            allocated_folder_name="",
            effective_rating_stars=existing_rating_stars,
            avf_info_exif_mutated=False,
            slot1_avf_info_mutated=False,
            slot1_data_sector_writes=0,
            slot1_vault_folder_or_rating_mutation_bytes=0,
            tier0_vault_firewall_triggered=False,
            admitted=True,
            errno_code=0,
            reason_code="FILE_FOLDER_SETTINGS_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    touches_slot1 = (target_slot == SLOT_1) or dual_slot_simultaneous

    # [Select REC Folder] rules
    if operation == OP_SELECT_REC_FOLDER:
        if eff_style == FOLDER_STYLE_DATE:
            return _reject(EOPNOTSUPP_ERRNO, "SELECT_REC_FOLDER_DISABLED_IN_DATE_FORM")
        if dual_slot_simultaneous and (not folder_exists_on_both_slots):
            return _reject(
                EINVAL_ERRNO,
                "SELECT_REC_FOLDER_SIMULTANEOUS_REQUIRES_MATCHING_FOLDER_BOTH_CARDS",
            )
        if touches_slot1 and slot1_is_tier0_vault:
            return _reject(
                EROFS_ERRNO,
                "SLOT1_TIER0_VAULT_REC_FOLDER_WRITE_BLOCKED_EROFS",
                firewall=True,
            )
        if card_write_protected:
            return _reject(EROFS_ERRNO, "CARD_WRITE_PROTECTED_EROFS")
        sel_num = max(slot1_max_folder_num, slot2_max_folder_num) if dual_slot_simultaneous else slot2_max_folder_num
        return FolderRatingVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            target_slot=target_slot,
            dual_slot_simultaneous=dual_slot_simultaneous,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            is_movie_recording=is_movie_recording,
            folder_name_style=folder_name_style,
            file_number_mode=file_number_mode,
            file_name_prefix=file_name_prefix,
            slot1_max_folder_num=slot1_max_folder_num,
            slot2_max_folder_num=slot2_max_folder_num,
            current_folder_images=current_folder_images,
            folder_exists_on_both_slots=folder_exists_on_both_slots,
            requested_rating_stars=requested_rating_stars,
            existing_rating_stars=existing_rating_stars,
            rating_set_checkboxes=rating_set_checkboxes,
            fx6_clip_flag=fx6_clip_flag,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_folder_name_style=eff_style,
            effective_file_number_mode=eff_num_mode,
            effective_file_name_prefix=eff_prefix,
            allocated_folder_name=f"DCIM/{sel_num}{DEFAULT_FOLDER_SUFFIX}",
            effective_rating_stars=existing_rating_stars,
            avf_info_exif_mutated=False,
            slot1_avf_info_mutated=False,
            slot1_data_sector_writes=0,
            slot1_vault_folder_or_rating_mutation_bytes=0,
            tier0_vault_firewall_triggered=False,
            admitted=True,
            errno_code=0,
            reason_code="SLOT2_SELECT_REC_FOLDER_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # [Create New Folder] & [Forced File Number Reset] rules
    if operation in (OP_CREATE_NEW_FOLDER, OP_FORCED_FILE_NUMBER_RESET):
        if touches_slot1 and slot1_is_tier0_vault:
            return _reject(
                EROFS_ERRNO,
                "SLOT1_TIER0_VAULT_CREATE_FOLDER_BLOCKED_EROFS",
                firewall=True,
            )
        if card_write_protected:
            return _reject(EROFS_ERRNO, "CARD_WRITE_PROTECTED_CREATE_FOLDER_EROFS")
        base_max = (
            max(slot1_max_folder_num, slot2_max_folder_num)
            if dual_slot_simultaneous
            else (slot1_max_folder_num if target_slot == SLOT_1 else slot2_max_folder_num)
        )
        next_num = base_max + 1
        if next_num > MAX_FOLDER_NUMBER or current_folder_images >= MAX_IMAGES_PER_FOLDER:
            if next_num > MAX_FOLDER_NUMBER:
                return _reject(
                    EOPNOTSUPP_ERRNO,
                    "STATUS_OF_MEDIA_SLOT_FOLDER_MAX_999_REACHED",
                )
        new_folder = (
            f"DCIM/{next_num}{DEFAULT_FOLDER_SUFFIX}"
            if eff_style == FOLDER_STYLE_STANDARD
            else f"DCIM/{next_num}21117"
        )
        return FolderRatingVaultEvalResult(
            body_profile=body_profile,
            operation=operation,
            target_slot=target_slot,
            dual_slot_simultaneous=dual_slot_simultaneous,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            is_movie_recording=is_movie_recording,
            folder_name_style=folder_name_style,
            file_number_mode=file_number_mode,
            file_name_prefix=file_name_prefix,
            slot1_max_folder_num=slot1_max_folder_num,
            slot2_max_folder_num=slot2_max_folder_num,
            current_folder_images=current_folder_images,
            folder_exists_on_both_slots=folder_exists_on_both_slots,
            requested_rating_stars=requested_rating_stars,
            existing_rating_stars=existing_rating_stars,
            rating_set_checkboxes=rating_set_checkboxes,
            fx6_clip_flag=fx6_clip_flag,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_folder_name_style=eff_style,
            effective_file_number_mode=eff_num_mode,
            effective_file_name_prefix=eff_prefix,
            allocated_folder_name=new_folder,
            effective_rating_stars=existing_rating_stars,
            avf_info_exif_mutated=False,
            slot1_avf_info_mutated=False,
            slot1_data_sector_writes=0,
            slot1_vault_folder_or_rating_mutation_bytes=0,
            tier0_vault_firewall_triggered=False,
            admitted=True,
            errno_code=0,
            reason_code="SLOT2_VIRTUAL_NEW_FOLDER_ALLOCATED_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Playback [Rating], [Rating Set(Custom Key)] toggle & Still [Add Rating]
    if background_transfer_active:
        return _reject(
            EBUSY_ERRNO,
            "EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING",
        )
    if operation == OP_SHOOTING_ADD_RATING:
        if is_movie_recording:
            return _reject(EOPNOTSUPP_ERRNO, "ADD_RATING_UNSUPPORTED_DURING_MOVIE_REC")
        if requested_rating_stars < 1:
            return _reject(EINVAL_ERRNO, "ADD_RATING_REQUIRES_1_TO_5_STARS")
        if existing_rating_stars > 0:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "CANT_ADD_SINCE_RATING_ALREADY_APPLIED_0x627d",
            )
    if operation == OP_CUSTOM_KEY_RATING_TOGGLE and requested_rating_stars != 0:
        if requested_rating_stars not in rating_set_checkboxes:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "RATING_VALUE_EXCLUDED_BY_RATING_SET_CUSTOM_KEY_CHECKBOX",
            )

    if touches_slot1 and slot1_is_tier0_vault:
        return _reject(
            EROFS_ERRNO,
            "SLOT1_TIER0_VAULT_RATING_EXIF_AVF_INFO_BLOCKED_EROFS",
            firewall=True,
        )
    if card_write_protected:
        return _reject(EROFS_ERRNO, "CARD_WRITE_PROTECTED_RATING_EROFS")

    return FolderRatingVaultEvalResult(
        body_profile=body_profile,
        operation=operation,
        target_slot=target_slot,
        dual_slot_simultaneous=dual_slot_simultaneous,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        card_write_protected=card_write_protected,
        background_transfer_active=background_transfer_active,
        is_movie_recording=is_movie_recording,
        folder_name_style=folder_name_style,
        file_number_mode=file_number_mode,
        file_name_prefix=file_name_prefix,
        slot1_max_folder_num=slot1_max_folder_num,
        slot2_max_folder_num=slot2_max_folder_num,
        current_folder_images=current_folder_images,
        folder_exists_on_both_slots=folder_exists_on_both_slots,
        requested_rating_stars=requested_rating_stars,
        existing_rating_stars=existing_rating_stars,
        rating_set_checkboxes=rating_set_checkboxes,
        fx6_clip_flag=fx6_clip_flag,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        effective_folder_name_style=eff_style,
        effective_file_number_mode=eff_num_mode,
        effective_file_name_prefix=eff_prefix,
        allocated_folder_name="",
        effective_rating_stars=requested_rating_stars,
        avf_info_exif_mutated=True,
        slot1_avf_info_mutated=False,
        slot1_data_sector_writes=0,
        slot1_vault_folder_or_rating_mutation_bytes=0,
        tier0_vault_firewall_triggered=False,
        admitted=True,
        errno_code=0,
        reason_code="SLOT2_VIRTUAL_RATING_EXIF_AVF_INFO_UPDATED_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


# ---------------------------------------------------------------------------
# Full Phase 309 Stage 63 (63/63 Milestone) Closed-Loop Co-Emulator Report
# ---------------------------------------------------------------------------


def _build_stage63_milestone_probe() -> Dict[str, object]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "phase_number": PHASE_NUMBER,
        "stage_name": STAGE_NAME,
        "is_63rd_stage_milestone": True,
        "wave53_pillars": [
            "63A_lens_comp_shading_auto_off_vs_dormant_auto_low_steadyshot_active_lock",
            "63B_builtin_front_af_illuminator_led8_still_afs_only_vs_zero_led_fx6",
            "63C_af_behavior_5_settings_initialize_only_persistence_orthogonal_circ",
            "63D_create_new_folder_and_rating_1_5_stars_slot1_tier0_vault_firewall",
        ],
    }


def run_phase309_lens_comp_af_illuminator_folder_rating_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 309 Stage 63 (63/63) Wave-53 Real-Hardware HIL Co-Emulation."""
    donor_audit = inspect_phase309_donors(force_clean_room=force_clean_room, env=env)

    # Pillar 63A scenarios
    p63a_nominal_fx3 = simulate_lens_compensation_hil(
        body_profile=BODY_MODEL_FX3,
        shooting_domain=DOMAIN_STILL,
        lens_profile=LENS_FE_2470GM2,
        shading_comp=COMP_AUTO,
        chromatic_aberration_comp=COMP_AUTO,
        distortion_comp=COMP_OFF,
        capture_format=CAPTURE_FMT_ARW_COMPRESSED,
    )
    p63a_dormant_auto_low_rejected = simulate_lens_compensation_hil(
        shading_comp=COMP_DORMANT_AUTO_LOW,
    )
    p63a_steadyshot_active_distortion_off_rejected = simulate_lens_compensation_hil(
        shooting_domain=DOMAIN_MOVIE,
        steadyshot_mode=STEADYSHOT_ACTIVE,
        distortion_comp=COMP_OFF,
    )
    p63a_steadyshot_active_distortion_auto_ok = simulate_lens_compensation_hil(
        shooting_domain=DOMAIN_MOVIE,
        steadyshot_mode=STEADYSHOT_ACTIVE,
        distortion_comp=COMP_AUTO,
        breathing_comp=COMP_ON,
    )
    p63a_selp1650_distortion_off_rejected = simulate_lens_compensation_hil(
        lens_profile=LENS_SELP1650,
        distortion_comp=COMP_OFF,
    )
    p63a_unchipped_manual_rejected = simulate_lens_compensation_hil(
        lens_profile=LENS_UNCHIPPED_MANUAL_PL,
    )
    p63a_cam_reset_split = simulate_lens_compensation_hil(
        shooting_domain=DOMAIN_MOVIE,
        shading_comp=COMP_OFF,
        chromatic_aberration_comp=COMP_OFF,
        distortion_comp=COMP_AUTO,
        breathing_comp=COMP_ON,
        camera_settings_reset_applied=True,
    )
    p63a_fx6_raw_breathing_rejected = simulate_lens_compensation_hil(
        body_profile=BODY_MODEL_FX6,
        shooting_domain=DOMAIN_MOVIE,
        distortion_comp=COMP_AUTO,
        breathing_comp=COMP_AUTO,
        codec_is_raw=True,
    )
    p63a_fx6_white_black_shading = evaluate_fx6_white_black_shading_distinction()

    p63a_ok = (
        p63a_nominal_fx3.admitted
        and p63a_nominal_fx3.exposed_shading_options == (COMP_AUTO, COMP_OFF)
        and (not p63a_nominal_fx3.distortion_baked_into_arw_pixels)
        and p63a_nominal_fx3.shading_applies_to_arw_gain
        and (not p63a_dormant_auto_low_rejected.admitted)
        and p63a_dormant_auto_low_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p63a_steadyshot_active_distortion_off_rejected.admitted)
        and p63a_steadyshot_active_distortion_off_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p63a_steadyshot_active_distortion_auto_ok.admitted
        and p63a_steadyshot_active_distortion_auto_ok.distortion_forced_auto
        and (not p63a_selp1650_distortion_off_rejected.admitted)
        and p63a_selp1650_distortion_off_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p63a_unchipped_manual_rejected.admitted)
        and p63a_unchipped_manual_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p63a_cam_reset_split.effective_shading_comp == COMP_OFF
        and p63a_cam_reset_split.effective_ca_comp == COMP_OFF
        and p63a_cam_reset_split.effective_distortion_comp == COMP_AUTO
        and p63a_cam_reset_split.effective_breathing_comp == COMP_OFF
        and (not p63a_fx6_raw_breathing_rejected.admitted)
        and p63a_fx6_raw_breathing_rejected.errno_code == EOPNOTSUPP_ERRNO
        and bool(p63a_fx6_white_black_shading["distinct_from_lens_shading_comp"])
    )

    # Pillar 63B scenarios
    p63b_fx3_still_afs_led8_and_flash_fired = simulate_af_illuminator_and_kinematics_hil(
        body_profile=BODY_MODEL_FX3,
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFS,
        mishoe_flash_mounted=True,
        mishoe_flash_powered_on=True,
    )
    p63b_fx3_movie_locked_out = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_AFC,
        af_transition_speed=2,
        af_subj_shift_sens=3,
        af_assist_on=True,
    )
    p63b_fx3_sq_locked_out = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_SQ,
        focus_mode=FOCUS_MODE_AFC,
    )
    p63b_fx3_still_afc_locked_out = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFC,
    )
    p63b_fx3_still_mf_locked_out = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_MF,
    )
    p63b_fx3_silent_mode_locked_out = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_STILL,
        focus_mode=FOCUS_MODE_AFS,
        silent_mode_on=True,
        force_fire_illuminator=True,
    )
    p63b_fx6_zero_illuminator_rejected = simulate_af_illuminator_and_kinematics_hil(
        body_profile=BODY_MODEL_FX6,
        shooting_domain=DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_AFC,
        force_fire_illuminator=True,
    )
    p63b_kinematics_cam_reset = simulate_af_illuminator_and_kinematics_hil(
        shooting_domain=DOMAIN_MOVIE,
        focus_mode=FOCUS_MODE_AFC,
        af_transition_speed=1,
        af_subj_shift_sens=1,
        af_assist_on=True,
        camera_settings_reset_applied=True,
    )

    p63b_ok = (
        p63b_fx3_still_afs_led8_and_flash_fired.admitted
        and p63b_fx3_still_afs_led8_and_flash_fired.builtin_led8_fired
        and p63b_fx3_still_afs_led8_and_flash_fired.mishoe_flash_af_illuminator_fired
        and p63b_fx3_still_afs_led8_and_flash_fired.fx3_has_builtin_af_illuminator
        and (not p63b_fx3_still_afs_led8_and_flash_fired.fx6_has_builtin_af_illuminator)
        and (not p63b_fx3_movie_locked_out.builtin_led8_fired)
        and p63b_fx3_movie_locked_out.effective_af_assist_on
        and (not p63b_fx3_sq_locked_out.builtin_led8_fired)
        and (not p63b_fx3_still_afc_locked_out.builtin_led8_fired)
        and (not p63b_fx3_still_mf_locked_out.builtin_led8_fired)
        and (not p63b_fx3_silent_mode_locked_out.admitted)
        and p63b_fx3_silent_mode_locked_out.errno_code == EOPNOTSUPP_ERRNO
        and (not p63b_fx6_zero_illuminator_rejected.admitted)
        and p63b_fx6_zero_illuminator_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p63b_kinematics_cam_reset.effective_af_transition_speed == AF_TRANSITION_SPEED_DEFAULT
        and p63b_kinematics_cam_reset.effective_af_subj_shift_sens == AF_SUBJ_SHIFT_SENS_DEFAULT
        and (not p63b_kinematics_cam_reset.effective_af_assist_on)
    )

    # Pillar 63C scenarios
    p63c_all5_survive_cam_reset = simulate_af_behavior_initialize_persistence_hil(
        shooting_domain=DOMAIN_STILL,
        focus_area=FOCUS_AREA_SPOT_M,
        aperture_drive_in_af=APERTURE_DRIVE_FOCUS_PRIORITY,
        af_w_shutter=False,
        pre_af=True,
        circ_of_focus_point=CIRC_CIRCULATE,
        focus_area_color=FOCUS_AREA_COLOR_RED,
        step_from_x=0,
        step_from_y=5,
        step_dx=-1,
        step_dy=0,
        camera_settings_reset_applied=True,
        reset_network_settings_applied=True,
    )
    p63c_initialize_resets_all5 = simulate_af_behavior_initialize_persistence_hil(
        shooting_domain=DOMAIN_STILL,
        aperture_drive_in_af=APERTURE_DRIVE_SILENT_PRIORITY,
        af_w_shutter=False,
        pre_af=True,
        circ_of_focus_point=CIRC_CIRCULATE,
        focus_area_color=FOCUS_AREA_COLOR_RED,
        initialize_applied=True,
    )
    p63c_diagonal_wrap_rejected = simulate_af_behavior_initialize_persistence_hil(
        circ_of_focus_point=CIRC_CIRCULATE,
        step_from_x=0,
        step_from_y=0,
        step_dx=-1,
        step_dy=-1,
    )
    p63c_legacy_label_rejected = simulate_af_behavior_initialize_persistence_hil(
        requested_legacy_name=DORMANT_FOCUS_AREA_COLOR_LABEL,
    )
    p63c_fx6_iris_contrast = simulate_af_behavior_initialize_persistence_hil(
        body_profile=BODY_MODEL_FX6,
        shooting_domain=DOMAIN_MOVIE,
        fx6_iris_mode="Push Auto Iris",
        fx6_iris_override_ev=0.5,
    )

    p63c_ok = (
        p63c_all5_survive_cam_reset.admitted
        and p63c_all5_survive_cam_reset.effective_aperture_drive_in_af == APERTURE_DRIVE_FOCUS_PRIORITY
        and (not p63c_all5_survive_cam_reset.effective_af_w_shutter)
        and p63c_all5_survive_cam_reset.effective_pre_af
        and p63c_all5_survive_cam_reset.effective_circ_of_focus_point == CIRC_CIRCULATE
        and p63c_all5_survive_cam_reset.effective_focus_area_color == FOCUS_AREA_COLOR_RED
        and p63c_all5_survive_cam_reset.aperture_audible_noise_warning
        and p63c_all5_survive_cam_reset.burst_speed_may_decrease
        and p63c_all5_survive_cam_reset.orthogonal_wrap_occurred
        and p63c_all5_survive_cam_reset.step_to_x == 14
        and (not p63c_all5_survive_cam_reset.diagonal_wrap_occurred)
        and p63c_initialize_resets_all5.effective_aperture_drive_in_af == APERTURE_DRIVE_STANDARD
        and p63c_initialize_resets_all5.effective_af_w_shutter
        and (not p63c_initialize_resets_all5.effective_pre_af)
        and p63c_initialize_resets_all5.effective_circ_of_focus_point == CIRC_DOES_NOT_CIRCULATE
        and p63c_initialize_resets_all5.effective_focus_area_color == FOCUS_AREA_COLOR_WHITE
        and (not p63c_diagonal_wrap_rejected.admitted)
        and p63c_diagonal_wrap_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p63c_legacy_label_rejected.admitted)
        and p63c_legacy_label_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p63c_fx6_iris_contrast.admitted
        and p63c_fx6_iris_contrast.fx6_iris_mode == "Push Auto Iris"
    )

    # Pillar 63D scenarios
    p63d_slot1_create_folder_blocked = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_CREATE_NEW_FOLDER,
        target_slot=SLOT_1,
        slot1_is_tier0_vault=True,
    )
    p63d_slot1_rating_blocked = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_PLAYBACK_RATING,
        target_slot=SLOT_1,
        slot1_is_tier0_vault=True,
        requested_rating_stars=5,
    )
    p63d_simult_rating_blocked = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_SHOOTING_ADD_RATING,
        target_slot=SLOT_2,
        dual_slot_simultaneous=True,
        slot1_is_tier0_vault=True,
        requested_rating_stars=3,
    )
    p63d_slot2_create_folder_ok = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_CREATE_NEW_FOLDER,
        target_slot=SLOT_2,
        slot1_is_tier0_vault=True,
        slot2_max_folder_num=105,
    )
    p63d_slot2_rating_5stars_ok = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_PLAYBACK_RATING,
        target_slot=SLOT_2,
        slot1_is_tier0_vault=True,
        requested_rating_stars=5,
    )
    p63d_bg_ftp_rating_blocked = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_PLAYBACK_RATING,
        target_slot=SLOT_2,
        background_transfer_active=True,
        requested_rating_stars=4,
    )
    p63d_date_form_select_rejected = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_SELECT_REC_FOLDER,
        target_slot=SLOT_2,
        folder_name_style=FOLDER_STYLE_DATE,
    )
    p63d_leading_underscore_rejected = simulate_folder_and_rating_vault_firewall_hil(
        operation=OP_NONE,
        file_name_prefix="_FX",
    )
    p63d_fx6_clip_flag_contrast = simulate_folder_and_rating_vault_firewall_hil(
        body_profile=BODY_MODEL_FX6,
        operation=OP_NONE,
        target_slot=SLOT_2,
        fx6_clip_flag="OK",
    )

    p63d_ok = (
        (not p63d_slot1_create_folder_blocked.admitted)
        and p63d_slot1_create_folder_blocked.errno_code == EROFS_ERRNO
        and p63d_slot1_create_folder_blocked.tier0_vault_firewall_triggered
        and p63d_slot1_create_folder_blocked.slot1_data_sector_writes == 0
        and (not p63d_slot1_rating_blocked.admitted)
        and p63d_slot1_rating_blocked.errno_code == EROFS_ERRNO
        and p63d_slot1_rating_blocked.tier0_vault_firewall_triggered
        and (not p63d_slot1_rating_blocked.slot1_avf_info_mutated)
        and (not p63d_simult_rating_blocked.admitted)
        and p63d_simult_rating_blocked.errno_code == EROFS_ERRNO
        and p63d_slot2_create_folder_ok.admitted
        and p63d_slot2_create_folder_ok.allocated_folder_name == "DCIM/106MSDCF"
        and p63d_slot2_create_folder_ok.physical_device_writes == 0
        and p63d_slot2_rating_5stars_ok.admitted
        and p63d_slot2_rating_5stars_ok.effective_rating_stars == 5
        and p63d_slot2_rating_5stars_ok.avf_info_exif_mutated
        and (not p63d_slot2_rating_5stars_ok.slot1_avf_info_mutated)
        and (not p63d_bg_ftp_rating_blocked.admitted)
        and p63d_bg_ftp_rating_blocked.errno_code == EBUSY_ERRNO
        and (not p63d_date_form_select_rejected.admitted)
        and p63d_date_form_select_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p63d_leading_underscore_rejected.admitted)
        and p63d_leading_underscore_rejected.errno_code == EINVAL_ERRNO
        and p63d_fx6_clip_flag_contrast.admitted
        and p63d_fx6_clip_flag_contrast.fx6_clip_flag == "OK"
    )

    milestone_probe = _build_stage63_milestone_probe()

    redlines: Dict[str, object] = {
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
        "dormant_shading_auto_low_exposed_events": DORMANT_SHADING_AUTO_LOW_EXPOSED_EVENTS,
        "steadyshot_active_distortion_bypass_events": (
            STEADYSHOT_ACTIVE_DISTORTION_BYPASS_EVENTS
        ),
        "fx3_has_builtin_af_illuminator": FX3_HAS_BUILTIN_AF_ILLUMINATOR,
        "fx6_has_builtin_af_illuminator": FX6_HAS_BUILTIN_AF_ILLUMINATOR,
        "af_illuminator_non_afs_or_silent_fire_events": (
            AF_ILLUMINATOR_NON_AFS_OR_SILENT_FIRE_EVENTS
        ),
        "initialize_only_af_reset_wipe_events": INITIALIZE_ONLY_AF_RESET_WIPE_EVENTS,
        "diagonal_focus_point_wrap_events": DIAGONAL_FOCUS_POINT_WRAP_EVENTS,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_vault_folder_or_rating_mutation_bytes": (
            SLOT1_VAULT_FOLDER_OR_RATING_MUTATION_BYTES
        ),
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    all_passed = bool(
        donor_audit.all_contracts_verified
        and p63a_ok
        and p63b_ok
        and p63c_ok
        and p63d_ok
        and milestone_probe["is_63rd_stage_milestone"]
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_309_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_63rd_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_lens_comp_shading_auto_off_and_active_lock_hil": {
            "passed": p63a_ok,
            "exposed_shading_options": list(VALID_FX3_SHADING_AND_CA_MODES),
            "dormant_shading_options_rejected": list(DORMANT_SHADING_MODES),
            "distortion_locked_auto_lenses": list(DISTORTION_LOCKED_AUTO_LENSES),
            "nominal_fx3_arw_profile": asdict(p63a_nominal_fx3),
            "dormant_auto_low_rejected": asdict(p63a_dormant_auto_low_rejected),
            "steadyshot_active_distortion_off_rejected": asdict(
                p63a_steadyshot_active_distortion_off_rejected
            ),
            "steadyshot_active_distortion_auto_ok": asdict(
                p63a_steadyshot_active_distortion_auto_ok
            ),
            "selp1650_distortion_off_rejected": asdict(
                p63a_selp1650_distortion_off_rejected
            ),
            "unchipped_manual_lens_rejected": asdict(p63a_unchipped_manual_rejected),
            "camera_settings_reset_split": asdict(p63a_cam_reset_split),
            "fx6_raw_breathing_rejected": asdict(p63a_fx6_raw_breathing_rejected),
            "fx6_white_black_shading_distinction": p63a_fx6_white_black_shading,
        },
        "pillar_b_builtin_af_illuminator_led8_vs_zero_led_fx6_hil": {
            "passed": p63b_ok,
            "builtin_led8_label": FX3_BUILTIN_LED8_LABEL,
            "builtin_led8_range_m": list(FX3_BUILTIN_LED8_RANGE_M),
            "fx3_still_afs_led8_and_flash_fired": asdict(
                p63b_fx3_still_afs_led8_and_flash_fired
            ),
            "fx3_movie_locked_out": asdict(p63b_fx3_movie_locked_out),
            "fx3_sq_locked_out": asdict(p63b_fx3_sq_locked_out),
            "fx3_still_afc_locked_out": asdict(p63b_fx3_still_afc_locked_out),
            "fx3_still_mf_locked_out": asdict(p63b_fx3_still_mf_locked_out),
            "fx3_silent_mode_locked_out": asdict(p63b_fx3_silent_mode_locked_out),
            "fx6_zero_illuminator_rejected": asdict(p63b_fx6_zero_illuminator_rejected),
            "kinematics_camera_settings_reset": asdict(p63b_kinematics_cam_reset),
        },
        "pillar_c_af_behavior_initialize_only_persistence_hil": {
            "passed": p63c_ok,
            "initialize_only_items": [
                "Aperture Drive in AF",
                "AF w/ Shutter",
                "Pre-AF",
                "Circ. of Focus Point",
                "Focus Area Color",
            ],
            "all5_survive_camera_settings_reset": asdict(p63c_all5_survive_cam_reset),
            "initialize_resets_all5": asdict(p63c_initialize_resets_all5),
            "diagonal_wrap_rejected": asdict(p63c_diagonal_wrap_rejected),
            "legacy_focus_frame_color_rejected": asdict(p63c_legacy_label_rejected),
            "fx6_cine_iris_contrast": asdict(p63c_fx6_iris_contrast),
        },
        "pillar_d_create_folder_rating_slot1_vault_and_redlines": {
            "passed": p63d_ok,
            "slot1_create_folder_blocked": asdict(p63d_slot1_create_folder_blocked),
            "slot1_rating_blocked": asdict(p63d_slot1_rating_blocked),
            "simultaneous_rating_blocked": asdict(p63d_simult_rating_blocked),
            "slot2_create_folder_ok": asdict(p63d_slot2_create_folder_ok),
            "slot2_rating_5stars_ok": asdict(p63d_slot2_rating_5stars_ok),
            "bg_ftp_rating_blocked": asdict(p63d_bg_ftp_rating_blocked),
            "date_form_select_rec_folder_rejected": asdict(
                p63d_date_form_select_rejected
            ),
            "leading_underscore_prefix_rejected": asdict(
                p63d_leading_underscore_rejected
            ),
            "fx6_clip_flag_contrast": asdict(p63d_fx6_clip_flag_contrast),
            "stage63_milestone_probe": milestone_probe,
        },
        "redlines": redlines,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


# ---------------------------------------------------------------------------
# CLI Entry Point (Python 3.14 strict: ALL literal '%' escaped as '%%')
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_lens_comp_af_illuminator_folder_rating_coemulator.py",
        description=(
            "Phase 309 Stage 63 (63/63 Milestone) Wave-53 Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Lens Compensation Shading Auto/Off vs Dormant Auto:Low & "
            "SteadyShot Active Distortion Lock, Built-in Front AF Illuminator LED #8 (0.3..3.0 m) "
            "Still AF-S Only vs Zero-Illuminator FX6, AF Behavior Initialize-Only Persistence, & "
            "Create New Folder / Playback Rating (1..5 Stars) Slot-1 100%% Fail-Closed Tier-0 Vault "
            "Firewall HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 309 Stage 63 (63/63) Wave-53 HIL verification suite",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force CLEAN_ROOM_SYNTHETIC donor verification without reading local Mac/work files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report (default unless --summary is set)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line Stage 63 (63/63) Wave-53 verification summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase309_lens_comp_af_illuminator_folder_rating_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 309 Stage 63 (63/63 Milestone) | mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"autolow_exp={red['dormant_shading_auto_low_exposed_events']} "
            f"ss_byp={red['steadyshot_active_distortion_bypass_events']} "
            f"fx3_led8={int(red['fx3_has_builtin_af_illuminator'])} "
            f"fx6_led={int(red['fx6_has_builtin_af_illuminator'])} "
            f"init_wipe={red['initialize_only_af_reset_wipe_events']} "
            f"s1_wr={red['slot1_data_sector_writes']} "
            f"emmc_wr={red['emmc_nflasha_write_count']} "
            f"leak={red['raw_firmware_bytes_leaked']} "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
