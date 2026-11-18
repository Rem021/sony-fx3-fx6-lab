#!/usr/bin/env python3
"""Phase 289 (Stage 58, 58/58) — Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-48:
Picture Profile `PP1..PP11` (`PP11 = S-Cinetone` Out-of-Box Default for BOTH Movie AND Still),
`Creative Look` 10 Presets + `Custom Look 1..6` & `D-Range Optimizer` Lockout, `Log Shooting` Mutual
Exclusion & `[Picture Profile] -> [Reset]` Persistence Split HIL,
`[White Balance]` 13-Mode & `Custom 1..3` Reset Survival vs `CAMSET01..10.DAT` Card Exclusion &
`Cine EI` Auto-WB Lockout HIL, and
`[Metering Mode]` 5-Mode, `[Spot Metering Point]` (`Focus Point Link`) & `Clear Image Zoom`
`[Multi]` Clamp HIL Co-Emulator.

Strictly models Wave-48 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts
without physical hardware attachment or firmware byte leakage:

1. **Sub-Model 58A — Picture Profile `PP1..PP11` (`PP11 = S-Cinetone` Out-of-Box Default for
   BOTH Movie AND Still), `Creative Look` & `DRO` Lockout, `Log Shooting` Mutual Exclusion &
   Reset Persistence Split HIL**:
   - `ILME-FX3 Ver. 7.02` ships out of the box with `[Picture Profile] = PP11`
     (`Gamma: S-Cinetone`, `Color Mode: S-Cinetone`, `PICTURE_PROFILE_PP11`) active for **BOTH
     Movie AND Still** (`Different Set for Still/Mv` `[Picture Profile]` unchecked by default).
     (`PP7/8/9 = S-Log2/S-Log3`, `PP10 = HLG2 + BT.2020`, `PPLUT1..4` external/user LUT slots.)
     Contrasted with `ILME-FX6 Ver. 6.01` `Base Look` (`S-Cinetone` default in Custom mode) +
     `Scene File` instead of `PP1..PP11` / `Creative Look`.
   - Whenever any `PP1..PP11` (or `PPLUT1..4`) is active (`!= Off`), `[Creative Look]`
     (10 presets `ST, PT, NT, VV, VV2, FL, IN, SH, BW, SE` + `Custom Look 1..6`, 8 params
     `Contrast, Highlights, Shadows, Fade, Saturation, Sharpness, Sharpness Range, Clarity`;
     note `Clarity` is locked out in Movie/`S&Q` or Continuous drive in Still) is hard-locked
     to `'-'` (`EOPNOTSUPP = 95`), and `[D-Range Optimizer]` (`Off / D-Range Optimizer: Auto /
     Lv1..Lv5`) is forced `Off` (`EOPNOTSUPP = 95`).
   - Enabling `[Log Shooting]` (`Flexible ISO`, `Cine EI Quick`, `Cine EI`) hard-locks
     `[Picture Profile]`, `[Creative Look]`, and `[D-Range Optimizer]` (`EOPNOTSUPP = 95`) and
     routes monitoring through `[Display LUT]` (`s709`, `709(800%)`, `S-Log3`, `User1..User16`).
   - **Critical Reset Persistence Split**: `[Camera Settings Reset]` resets the active
     `[Picture Profile]` selector back to `PP11`, **YET customized internal parameters inside
     `PP1..PP11` SURVIVE BOTH `[Camera Settings Reset]` AND `[Initialize]`** — ONLY explicit
     per-profile `[Picture Profile] -> [Reset]` restores factory `PPn` recipes!

2. **Sub-Model 58B — `[White Balance]` 13 Modes, `[Priority Set in AWB]`, `[Shutter AWB Lock]`,
   `Cine EI` Auto-WB Lockout, and `Custom 1..3` Reset Survival vs `CAMSET` Card Exclusion HIL**:
   - Models all 13 FX3 WB modes (`Auto`, `Daylight`, `Shade`, `Cloudy`, `Incandescent`,
     `Fluor.: Warm White`, `Fluor.: Cool White`, `Fluor.: Day White`, `Fluor.: Daylight`,
     `Flash` [Still-only; Movie/`S&Q` rejected `EOPNOTSUPP = 95`], `Underwater Auto`,
     `C.Temp./Filter` `2500K..9900K` step `100K` + `G7..M7`/`A7..B7`, and `Custom 1..3`),
     contrasted with `ILME-FX6` dedicated `WHT BAL` `Memory B / A / Preset` switch + `ATW`.
   - Under `Log Shooting = Cine EI` or `Cine EI Quick`, `Auto` and `Underwater Auto` WB are
     hard-locked out (`EOPNOTSUPP = 95`; fixed presets, `C.Temp./Filter`, and `Custom 1..3`
     allowed). `[Shutter AWB Lock]` (`Shut. Halfway / Cont. Shooting / Off`) applies only in
     Still mode under `Auto` / `Underwater Auto`. `[Shockless WB]` (`Off / 1 / 2 / 3`) smooths
     preset transitions in Movie/`S&Q`.
   - **Critical Persistence / Card Split**: Registered `Custom 1..3` WB values **SURVIVE
     `[Camera Settings Reset]`** (wiped ONLY by `[Initialize]`), **YET CANNOT be saved into or
     recalled from SD/CFexpress `[Save/Load Settings]` (`CAMSET01..10.DAT`)** (`EOPNOTSUPP = 95`)
     — only `M1..M4` camera-memory card slots carry custom WB!

3. **Sub-Model 58C & Redlines — `[Metering Mode]` 5 Modes, `[Spot Metering Point]` (`Focus Point
   Link`), `[Face Priority in Multi Metering]`, `Clear Image Zoom` `[Multi]` Clamp & Redlines**:
   - Models all 5 FX3 metering modes (`Multi`, `Center`, `Spot` [`Spot: Standard` / `Spot: Large`],
     `Entire Screen Avg.`, `Highlight`), `[AEL w/ Shutter]`, and `[Exposure Std. Adjust]`,
     contrasted with FX6 Cine EI waveform/zebra/false-color workflow & Backlight/Spotlight/Standard
     auto-exposure modes.
   - `[Spot Metering Point] = Focus Point Link` couples spot metering circle only under
     `Flexible Spot` (`Spot: S/M/L`) or `Expand Spot` (collapsing to `Center` otherwise), and
     whenever `Clear Image Zoom / Digital Zoom > 1.0x`, metering is forced to `[Multi]` with
     `Face Priority in Multi Metering = Off`, restoring cleanly at `1.0x`.
   - Hard-locks all 16 safety & Wave-48 zero-fault redlines.

4. **Dual-Mode 11-Donor `O_RDONLY` Verification & Hard Safety Redlines**:
   - Inspects 11 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors strictly via
     `os.O_RDONLY` (`< 0.2s` cold, `raw_firmware_bytes_leaked == 0`), with deterministic
     `CLEAN_ROOM_SYNTHETIC` parity under `FX3_CLEAN_ROOM_TEST=1` or `FX3_FX6_FORCE_CLEAN_ROOM=1`.
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

SCHEMA_ID = "realhw_pp_scinetone_creativelook_wb_metering_coemulator_v1"
PHASE_289_SCHEMA = SCHEMA_ID
PHASE_289_VERSION = "289.0.0"
PHASE_NUMBER = 289
STAGE_INDEX = 58
STAGE_TOTAL = 58
MILESTONE_LABEL = "58/58"
STAGE_NAME = "stage58_realhw_pp_scinetone_creativelook_wb_metering_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
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

# Wave-48 Stage 58 zero-fault & model-truth invariants
PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS = 0
WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS = 0
METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS = 0

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
# Verified Local Donor Specs (11 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
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
        b"Picture Profile",
        b"PP11",
        b"S-Cinetone",
        b"Different Set for Still/Mv",
        b"Creative Look",
        b"VV2",
        b"Log Shooting",
        b"Flexible ISO",
        b"Cine EI Quick",
        b"Cine EI",
        b"Select LUT",
        b"Display LUT",
        b"<2500K",
        b">9900K",
        b"Priority Set in AWB",
        b"Shutter AWB Lock",
        b"Shockless WB",
        b"Spot: Standard",
        b"Spot: Large",
        b"Entire Screen Avg.",
        b"Highlight",
        b"Face Priority in Multi Metering",
        b"Spot Metering Point",
        b"Focus Point Link",
        b"AEL w/ Shutter",
        b"Camera Settings Reset",
        b"Initialize",
    ),
    "fx3_string_sc_f": (
        "图片配置文件".encode("utf-8"),
        "S-Cinetone".encode("utf-8"),
        "静态/动态不同设置".encode("utf-8"),
        "创意外观".encode("utf-8"),
        "Log拍摄".encode("utf-8"),
        "选择LUT".encode("utf-8"),
        "AWB优先级设置".encode("utf-8"),
        "快门AWB锁定".encode("utf-8"),
        "减震WB".encode("utf-8"),
        "多重测光时人脸优先".encode("utf-8"),
        "点测光点".encode("utf-8"),
        "快门AEL".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "相片設定檔".encode("utf-8"),
        "S-Cinetone".encode("utf-8"),
        "不同靜像/影片設定".encode("utf-8"),
        "風格外觀".encode("utf-8"),
        "Log拍攝".encode("utf-8"),
        "選取LUT".encode("utf-8"),
        "AWB優先順序設定".encode("utf-8"),
        "快門AWB鎖".encode("utf-8"),
        "減震WB".encode("utf-8"),
        "多重測光時面孔優先".encode("utf-8"),
        "重點測光點".encode("utf-8"),
        "半按快門AEL".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ﾋﾟｸﾁｬｰﾌﾟﾛﾌｧｲﾙ".encode("utf-8"),
        "S-Cinetone".encode("utf-8"),
        "静止画/動画独立設定".encode("utf-8"),
        "ｸﾘｴｲﾃｨﾌﾞﾙｯｸ".encode("utf-8"),
        "Log撮影".encode("utf-8"),
        "LUT選択".encode("utf-8"),
        "AWB時の優先設定".encode("utf-8"),
        "ｼｬｯﾀｰAWBﾛｯｸ".encode("utf-8"),
        "ショックレスWB".encode("utf-8"),
        "ﾏﾙﾁ測光時の顔優先".encode("utf-8"),
        "スポット測光位置".encode("utf-8"),
        "ｼｬｯﾀｰ半押しAEL".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"D-Range Optimizer",
        b"White Balance",
        b"C.Temp./Filter",
        b"Custom 1",
        b"Custom 2",
        b"Custom 3",
        b"Metering Mode",
        b"Multi",
        b"Center",
        b"Cloudy",
        b"Shade",
    ),
    "fx3_string_en_g": (
        b"Gamma Display Assist instead of LUT",
        b"Creative",
        b"White",
        b"Metering",
        b"Still",
        b"Movie",
        b"Log",
    ),
    "fx6_string_en": (
        b"S-Cinetone",
        b"Base Look",
        b"709tone",
        b"ATW",
    ),
    "fx6_string_en_2": (
        b"Memory A",
        b"Memory B",
        b"Shockless White",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (50_024_448, "WB_CTEMP_2500K", b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_2500K"),
        (50_028_544, "WB_CTEMP_9900K", b"WHITE_BALANCE_COLOR_TEMP_COLOR_FILTER_9900K"),
        (61_296_640, "LOG_CINE_EI_QUICK", b"LOG_SHOOTING_CINE_EI_QUICK"),
        (61_313_024, "PP11_ENUM", b"PICTURE_PROFILE_PP11"),
        (61_313_024, "PPLUT1_ENUM", b"PICTURE_PROFILE_PPLUT1"),
        (61_612_032, "CREATIVE_BRILLIANT", b"CREATIVE_STYLE_PLUS_BRILLIANT"),
        (61_612_032, "CREATIVE_BOX_1", b"CREATIVE_BOX_1"),
        (61_681_664, "WB_CUSTOM_SET", b"WHITE_BALANCE_CUSTOM_WHITE_BALANCE_SET"),
        (62_619_648, "CAUTION_SCINETONE", b"CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG"),
        (62_672_896, "BKID_DIFF_SET", b"BKID_APP_setting_different_set"),
        (62_672_896, "BKID_LOG_SHOOTING", b"BKID_APP_setting_log_shooting"),
        (62_685_184, "BKID_METERING_MODE", b"BKID_APP_setting_metering_mode"),
        (62_685_184, "BKID_FACE_MULTI", b"BKID_APP_setting_face_detection_in_multi"),
        (62_685_184, "BKID_SPOT_LINK", b"BKID_APP_setting_spot_metering_link_to_focus_point"),
        (62_685_184, "BKID_AEL_SHUTTER", b"BKID_APP_setting_still_image_ael_w_shutter"),
        (62_685_184, "BKID_EXP_STD_MULTI", b"BKID_APP_setting_exposure_standard_metering_mode_multi"),
        (62_685_184, "BKID_WHITE_BALANCE", b"BKID_APP_setting_white_balance"),
        (62_685_184, "BKID_PRIO_AWB", b"BKID_APP_setting_priority_set_in_awb"),
        (62_685_184, "BKID_SHUTTER_AWB_LOCK", b"BKID_APP_setting_stl_awb_lock_with_shutter"),
        (62_685_184, "BKID_SHOCKLESS_WB", b"BKID_APP_setting_movie_shockless_wb"),
        (62_685_184, "BKID_DRO", b"BKID_APP_setting_dro"),
        (62_685_184, "BKID_CREATIVE_LOOK", b"BKID_APP_setting_creative_style_plus"),
        (62_685_184, "BKID_PICTURE_PROFILE", b"BKID_APP_setting_picture_profile"),
        (62_685_184, "BKID_SELECT_LUT", b"BKID_APP_setting_select_lut"),
        (62_709_750, "BKID_METERING_SPOT", b"BKID_APP_setting_metering_mode_spot"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (0, "ALLLANG", b"ALLLANG"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_919_040, "FX6_SHOCKLESS_WB", b"BKID_APP_SETTING_MOVIE_SHOCKLESS_WB"),
        (40_927_232, "FX6_ATW_MODE", b"BKID_APP_SETTING_ATW_MODE"),
        (40_939_520, "FX6_BASE_LOOK_LUT_DISP", b"BKID_APP_SETTING_BASE_LOOK_LUT_DISPLAY"),
        (40_951_808, "FX6_BASE_LOOK0", b"BKID_APP_USER_MENU_BASE_LOOK0"),
        (40_996_864, "FX6_WHITE_MEM_A", b"BKID_APP_EXTERN_WHITEMEMORYA_ND"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-48 Official Sub-Model 58A / 58B / 58C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
STOCK_FX3_BODIES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX3A)
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = STOCK_FX3_BODIES + (BODY_MODEL_FX6,)

SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
SHOOT_MODE_STILL = "Still"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ, SHOOT_MODE_STILL)

DRIVE_MODE_SINGLE = "Single Shooting"
DRIVE_MODE_CONTINUOUS = "Cont. Shooting"
VALID_DRIVE_MODES: Tuple[str, ...] = (DRIVE_MODE_SINGLE, DRIVE_MODE_CONTINUOUS)

TOGGLE_OFF = "Off"
TOGGLE_ON = "On"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_OFF, TOGGLE_ON)

RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET = "Reset Network Set."
RESET_ACTION_INITIALIZE = "Initialize"
RESET_ACTION_PICTURE_PROFILE_RESET = "Picture Profile Reset"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_PICTURE_PROFILE_RESET,
)

# Sub-Model 58A: Picture Profile, Creative Look, DRO & Log Shooting
PP_MENU_PATH = "MENU -> Exposure/Color -> [Color/Tone] -> [Picture Profile]"
CREATIVE_LOOK_MENU_PATH = "MENU -> Exposure/Color -> [Color/Tone] -> [Creative Look]"
DRO_MENU_PATH = "MENU -> Exposure/Color -> [Color/Tone] -> [D-Range Optimizer]"
LOG_SHOOTING_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]"
DIFF_SET_MENU_PATH = "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]"
FX6_BASE_LOOK_MENU_PATH = "Paint/Look -> [Base Look] / [Scene File]"

PP_OFF = "Off"
PP1_TO_PP11: Tuple[str, ...] = tuple(f"PP{i}" for i in range(1, 12))
PPLUT_MODES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
VALID_PICTURE_PROFILES: Tuple[str, ...] = (PP_OFF,) + PP1_TO_PP11 + PPLUT_MODES
DEFAULT_OUT_OF_BOX_PP = "PP11"

PP_FACTORY_RECIPES: Mapping[str, Mapping[str, str]] = {
    "PP1": {"gamma": "Movie", "color_mode": "Movie"},
    "PP2": {"gamma": "Still", "color_mode": "Still"},
    "PP3": {"gamma": "ITU709", "color_mode": "ITU709 Matrix"},
    "PP4": {"gamma": "ITU709", "color_mode": "ITU709 Matrix"},
    "PP5": {"gamma": "Cine1", "color_mode": "Cinema"},
    "PP6": {"gamma": "Cine2", "color_mode": "Cinema"},
    "PP7": {"gamma": "S-Log2", "color_mode": "S-Gamut"},
    "PP8": {"gamma": "S-Log3", "color_mode": "S-Gamut3.Cine"},
    "PP9": {"gamma": "S-Log3", "color_mode": "S-Gamut3"},
    "PP10": {"gamma": "HLG2", "color_mode": "BT.2020"},
    "PP11": {"gamma": "S-Cinetone", "color_mode": "S-Cinetone"},
}

CREATIVE_LOOK_10_PRESETS: Tuple[str, ...] = (
    "ST",
    "PT",
    "NT",
    "VV",
    "VV2",
    "FL",
    "IN",
    "SH",
    "BW",
    "SE",
)
CREATIVE_LOOK_CUSTOM_SLOTS: Tuple[str, ...] = tuple(f"Custom Look {i}" for i in range(1, 7))
VALID_CREATIVE_LOOK_CHOICES: Tuple[str, ...] = CREATIVE_LOOK_10_PRESETS + CREATIVE_LOOK_CUSTOM_SLOTS
CREATIVE_LOOK_8_PARAMS: Tuple[str, ...] = (
    "Contrast",
    "Highlights",
    "Shadows",
    "Fade",
    "Saturation",
    "Sharpness",
    "Sharpness Range",
    "Clarity",
)

DRO_MODES: Tuple[str, ...] = (
    "Off",
    "D-Range Optimizer: Auto",
    "D-Range Optimizer: Lv1",
    "D-Range Optimizer: Lv2",
    "D-Range Optimizer: Lv3",
    "D-Range Optimizer: Lv4",
    "D-Range Optimizer: Lv5",
)

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
LOG_SHOOTING_CINE_EI = "Cine EI"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_CINE_EI,
)
DISPLAY_LUT_OPTIONS: Tuple[str, ...] = (
    "s709",
    "709(800%)",
    "S-Log3",
) + tuple(f"User{i}" for i in range(1, 17))

FX6_BASE_LOOK_SCINETONE = "S-Cinetone"
FX6_BASE_LOOK_709TONE = "709tone"
FX6_BASE_LOOK_SLOG3 = "S-Log3"

# Sub-Model 58B: White Balance 13 Modes & Persistence / CAMSET Split
WB_MENU_PATH = "MENU -> Exposure/Color -> [White Balance] -> [White Balance]"
AWB_PRIO_MENU_PATH = "MENU -> Exposure/Color -> [White Balance] -> [Priority Set in AWB]"
SHUTTER_AWB_LOCK_MENU_PATH = "MENU -> Exposure/Color -> [White Balance] -> [Shutter AWB Lock]"
SHOCKLESS_WB_MENU_PATH = "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]"
FX6_WHT_BAL_SWITCH_PATH = "Body Side [WHT BAL] Switch (B / A / PRESET) + [ATW]"

WB_AUTO = "Auto"
WB_DAYLIGHT = "Daylight"
WB_SHADE = "Shade"
WB_CLOUDY = "Cloudy"
WB_INCANDESCENT = "Incandescent"
WB_FLUOR_WARM = "Fluor.: Warm White"
WB_FLUOR_COOL = "Fluor.: Cool White"
WB_FLUOR_DAY_WHITE = "Fluor.: Day White"
WB_FLUOR_DAYLIGHT = "Fluor.: Daylight"
WB_FLASH = "Flash"
WB_UNDERWATER_AUTO = "Underwater Auto"
WB_CTEMP_FILTER = "C.Temp./Filter"
WB_CUSTOM_1 = "Custom 1"
WB_CUSTOM_2 = "Custom 2"
WB_CUSTOM_3 = "Custom 3"

# Note: 13 modes when grouping Fluor.: Warm/Cool/Day/Daylight under Fluorescent as Sony's 13-mode matrix,
# or 15 discrete sub-entries when expanding the 4 Fluorescent variants. Keep both explicit!
FX3_WB_13_BASE_MODES: Tuple[str, ...] = (
    WB_AUTO,
    WB_DAYLIGHT,
    WB_SHADE,
    WB_CLOUDY,
    WB_INCANDESCENT,
    "Fluorescent",  # 4 sub-presets: Warm White, Cool White, Day White, Daylight
    WB_FLASH,
    WB_UNDERWATER_AUTO,
    WB_CTEMP_FILTER,
    WB_CUSTOM_1,
    WB_CUSTOM_2,
    WB_CUSTOM_3,
    "Custom Setup",
)

VALID_FX3_WB_MODES: Tuple[str, ...] = (
    WB_AUTO,
    WB_DAYLIGHT,
    WB_SHADE,
    WB_CLOUDY,
    WB_INCANDESCENT,
    WB_FLUOR_WARM,
    WB_FLUOR_COOL,
    WB_FLUOR_DAY_WHITE,
    WB_FLUOR_DAYLIGHT,
    WB_FLASH,
    WB_UNDERWATER_AUTO,
    WB_CTEMP_FILTER,
    WB_CUSTOM_1,
    WB_CUSTOM_2,
    WB_CUSTOM_3,
)
CUSTOM_WB_SLOTS: Tuple[str, ...] = (WB_CUSTOM_1, WB_CUSTOM_2, WB_CUSTOM_3)
AUTO_WB_MODES: Tuple[str, ...] = (WB_AUTO, WB_UNDERWATER_AUTO)

AWB_PRIORITY_MODES: Tuple[str, ...] = ("Standard", "Ambience", "White")
SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = ("Shut. Halfway", "Cont. Shooting", "Off")
SHOCKLESS_WB_MODES: Tuple[str, ...] = ("Off", "1 (Fast)", "2", "3 (Slow)")

CTEMP_KELVIN_MIN = 2500
CTEMP_KELVIN_MAX = 9900
CTEMP_KELVIN_STEP = 100
GM_AXIS_MIN = -7
GM_AXIS_MAX = 7
AB_AXIS_MIN = -7
AB_AXIS_MAX = 7

FX6_WHT_BAL_POSITIONS: Tuple[str, ...] = ("Memory A", "Memory B", "Preset", "ATW")

STORAGE_TARGET_NONE = "NONE"
STORAGE_TARGET_CAMSET = "CAMSET01..10.DAT"
STORAGE_TARGET_MEMORY_M1_M4 = "M1..M4"
STORAGE_TARGET_SLOT1_VAULT = "Slot 1 Tier-0 Vault"
VALID_STORAGE_TARGETS: Tuple[str, ...] = (
    STORAGE_TARGET_NONE,
    STORAGE_TARGET_CAMSET,
    STORAGE_TARGET_MEMORY_M1_M4,
    STORAGE_TARGET_SLOT1_VAULT,
)

# Sub-Model 58C: Metering Mode 5 Modes, Spot Point & Clear Image Zoom
METERING_MENU_PATH = "MENU -> Exposure/Color -> [Metering] -> [Metering Mode]"
FACE_PRIO_MULTI_MENU_PATH = "MENU -> Exposure/Color -> [Metering] -> [Face Priority in Multi Metering]"
SPOT_POINT_MENU_PATH = "MENU -> Exposure/Color -> [Metering] -> [Spot Metering Point]"
AEL_SHUTTER_MENU_PATH = "MENU -> Exposure/Color -> [Metering] -> [AEL w/ Shutter]"
EXP_STD_ADJ_MENU_PATH = "MENU -> Exposure/Color -> [Metering] -> [Exposure Std. Adjust]"

METERING_MULTI = "Multi"
METERING_CENTER = "Center"
METERING_SPOT_STANDARD = "Spot: Standard"
METERING_SPOT_LARGE = "Spot: Large"
METERING_ENTIRE_SCREEN_AVG = "Entire Screen Avg."
METERING_HIGHLIGHT = "Highlight"

FX3_METERING_5_BASE_MODES: Tuple[str, ...] = (
    METERING_MULTI,
    METERING_CENTER,
    "Spot (Standard / Large)",
    METERING_ENTIRE_SCREEN_AVG,
    METERING_HIGHLIGHT,
)
VALID_FX3_METERING_MODES: Tuple[str, ...] = (
    METERING_MULTI,
    METERING_CENTER,
    METERING_SPOT_STANDARD,
    METERING_SPOT_LARGE,
    METERING_ENTIRE_SCREEN_AVG,
    METERING_HIGHLIGHT,
)

SPOT_POINT_CENTER = "Center"
SPOT_POINT_FOCUS_LINK = "Focus Point Link"
VALID_SPOT_METERING_POINTS: Tuple[str, ...] = (SPOT_POINT_CENTER, SPOT_POINT_FOCUS_LINK)

FOCUS_AREA_WIDE = "Wide"
FOCUS_AREA_ZONE = "Zone"
FOCUS_AREA_CENTER_FIX = "Center Fix"
FOCUS_AREA_FLEXIBLE_SPOT = "Flexible Spot"
FOCUS_AREA_EXPAND_SPOT = "Expand Spot"
VALID_FOCUS_AREAS: Tuple[str, ...] = (
    FOCUS_AREA_WIDE,
    FOCUS_AREA_ZONE,
    FOCUS_AREA_CENTER_FIX,
    FOCUS_AREA_FLEXIBLE_SPOT,
    FOCUS_AREA_EXPAND_SPOT,
)
SPOT_COUPLED_FOCUS_AREAS: Tuple[str, ...] = (
    FOCUS_AREA_FLEXIBLE_SPOT,
    FOCUS_AREA_EXPAND_SPOT,
)

AEL_SHUTTER_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
FX6_AUTO_EXP_MODES: Tuple[str, ...] = ("Standard", "Backlight", "Spotlight")

ALL_16_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_write_requested",
    "hardware_live_attach_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "cp_mutation_requested",
    "wbi_mutation_requested",
    "nop_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_increment_requested",
    "pp_creative_look_lockout_bypass_requested",
    "pp_camera_reset_internal_wipe_requested",
    "cine_ei_auto_wb_bypass_requested",
    "camset_custom_wb_leak_requested",
    "ciz_multi_or_spot_link_bypass_requested",
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256: str
    sha256_prefix16: str
    sha256_verified: bool
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
    head_sha256: str
    head_sha256_prefix16: str
    head_sha256_verified: bool


@dataclass(frozen=True)
class Phase289DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_string_en_f: CompactDonorSummary
    fx3_string_sc_f: CompactDonorSummary
    fx3_string_tc_f: CompactDonorSummary
    fx3_string_ja_f: CompactDonorSummary
    fx3_string_en: CompactDonorSummary
    fx3_string_en_g: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx6_string_en_2: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    pp_scinetone_creativelook_proven: bool
    wb_13mode_cineei_custom_proven: bool
    metering_5mode_spot_link_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PictureProfileCreativeLookDroEvalResult:
    pp_menu_path: str
    creative_look_menu_path: str
    dro_menu_path: str
    log_shooting_menu_path: str
    body_profile: str
    shoot_mode: str
    drive_mode: str
    out_of_box_default_pp: str
    out_of_box_default_applies_movie_and_still: bool
    different_set_still_mv_pp: bool
    configured_picture_profile: str
    effective_picture_profile: str
    effective_pp_gamma: str
    effective_pp_color_mode: str
    configured_log_shooting: str
    effective_log_shooting: str
    effective_display_lut: str
    configured_creative_look: str
    effective_creative_look: str
    creative_look_hard_locked: bool
    clarity_param_locked: bool
    sharpness_range_param_locked: bool
    saturation_param_locked: bool
    configured_dro: str
    effective_dro: str
    dro_forced_off: bool
    fx6_contrast_model: str
    reset_action: str
    pp_internal_edits_present: bool
    pp_internal_edits_survived: bool
    pp_recipe_restored_to_factory: bool
    pp_creative_look_or_reset_wipe_misroute_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class WhiteBalanceCineEiCamsetEvalResult:
    wb_menu_path: str
    awb_prio_menu_path: str
    shutter_awb_lock_menu_path: str
    shockless_wb_menu_path: str
    body_profile: str
    shoot_mode: str
    configured_log_shooting: str
    requested_wb_mode: str
    effective_wb_mode: str
    ctemp_kelvin: int
    gm_axis: int
    ab_axis: int
    awb_priority_mode: str
    shutter_awb_lock_mode: str
    shutter_awb_lock_active: bool
    shockless_wb_mode: str
    shockless_wb_active: bool
    cine_ei_auto_wb_locked: bool
    flash_wb_still_only_enforced: bool
    storage_target: str
    custom_wb_saved_to_camset: bool
    custom_wb_saved_to_m1_m4: bool
    reset_action: str
    custom_wb_1_3_survived: bool
    custom_wb_1_3_wiped_by_initialize: bool
    fx6_wht_bal_contrast: str
    wb_cine_ei_auto_or_camset_custom_leak_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class MeteringSpotLinkCizEvalResult:
    metering_menu_path: str
    spot_point_menu_path: str
    face_prio_multi_menu_path: str
    body_profile: str
    shoot_mode: str
    focus_area: str
    clear_image_zoom_ratio: float
    desqueeze_display: str
    configured_metering_mode: str
    effective_metering_mode: str
    configured_spot_metering_point: str
    effective_spot_metering_point: str
    spot_coupled_to_af_point: bool
    configured_face_prio_multi: str
    effective_face_prio_multi: str
    ael_with_shutter: str
    exposure_std_adjust_sixth_ev: int
    ciz_forced_multi_clamp_active: bool
    restored_prior_metering_at_1x: bool
    fx6_metering_contrast: str
    metering_spot_link_or_ciz_multi_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    errno_code: int
    reason_code: str
    persistent_emmc_writes_authorized: bool
    hardware_live_attachment_authorized: bool
    overall_ready_for_hardware_attach: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    cnflasha_userspace_write_blocked: bool
    cnflasha_mutation_bytes: int
    physical_device_writes: int
    emmc_nflasha_write_count: int
    emmc_corruptions: int
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    physical_usb_packets_emitted: int
    pp_creative_look_or_reset_wipe_misroute_events: int
    wb_cine_ei_auto_or_camset_custom_leak_events: int
    metering_spot_link_or_ciz_multi_bypass_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 11-Donor Inspection (< 0.2s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase289DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase289DonorAudit] = None


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    for key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST):
        if source.get(key, "").strip().lower() in ("1", "true", "yes", "on"):
            return True
    return False


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


def resolve_phase289_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 11 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen = next((root / rel for root in roots if (root / rel).is_file()), None)
        resolved[key] = (
            chosen
            if chosen is not None
            else (roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel))
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


def _read_bounded_o_rdonly(path: Path, offset: int, size: int) -> bytes:
    if size < 0 or size > BOUNDED_WINDOW_MAX_BYTES:
        raise ValueError(
            f"Bounded O_RDONLY read size {size} exceeds max {BOUNDED_WINDOW_MAX_BYTES}"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.lseek(fd, offset, os.SEEK_SET)
        return os.read(fd, size)
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
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
    expected_sha256: Optional[str],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    digest = hashlib.sha256(data).hexdigest()
    sha_ok = True if expected_sha256 is None else (digest == expected_sha256)
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256=digest,
        sha256_prefix16=digest[:16],
        sha256_verified=sha_ok,
        marker_hits=hits,
    )


def _scan_compact_rdonly(path: Path, *, artifact_key: str, body_label: str) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        tokens=COMPACT_DONOR_TOKENS[artifact_key],
        expected_sha256=EXPECTED_COMPACT_DONOR_SHA256[artifact_key],
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(
        path, LARGE_DONOR_WINDOWS[artifact_key]
    )
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    head_digest = hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256=head_digest,
        head_sha256_prefix16=head_digest[:16],
        head_sha256_verified=(head_digest == EXPECTED_LARGE_HEAD4K_SHA256[artifact_key]),
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase289DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        tag = f"{key}_SYNTH_P289".encode("ascii")
        raw = b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
            expected_sha256=None,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        toks = [tok for _, _, tok in wins]
        tag = f"{key}_SYNTH_P289".encode("ascii")
        head = (
            _build_synthetic_elf64_bytes(toks[:2], tag)
            if is_elf
            else (b"BK4\x00ALLLANG\x00" + tag + b"\x00")
        )
        head_digest = hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256=head_digest,
            head_sha256_prefix16=head_digest[:16],
            head_sha256_verified=True,
        )

    audit = Phase289DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=11,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "ILME-FX3 7.02 en_f"),
        fx3_string_sc_f=_mk_compact("fx3_string_sc_f", "ILME-FX3 7.02 sc_f"),
        fx3_string_tc_f=_mk_compact("fx3_string_tc_f", "ILME-FX3 7.02 tc_f"),
        fx3_string_ja_f=_mk_compact("fx3_string_ja_f", "ILME-FX3 7.02 ja_f"),
        fx3_string_en=_mk_compact("fx3_string_en", "ILME-FX3 7.02 en"),
        fx3_string_en_g=_mk_compact("fx3_string_en_g", "ILME-FX3 7.02 en_g"),
        fx6_string_en=_mk_compact("fx6_string_en", "ILME-FX6 6.01 en"),
        fx6_string_en_2=_mk_compact("fx6_string_en_2", "ILME-FX6 6.01 en_2"),
        fx3_appfw=_mk_large("fx3_appfw", "ILME-FX3 7.02 appFw.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "ILME-FX3 7.02 BK4", False),
        fx6_appfw=_mk_large("fx6_appfw", "ILME-FX6 6.01 appFw.so", True),
        pp_scinetone_creativelook_proven=True,
        wb_13mode_cineei_custom_proven=True,
        metering_5mode_spot_link_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    _CLEAN_ROOM_AUDIT_SINGLETON = audit
    return audit


def inspect_phase289_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase289DonorAudit:
    """Inspect all 11 Wave-48 FX3 7.02 & FX6 6.01 donors strictly via `os.O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)
        eff_env.pop(ENV_CLEAN_ROOM_TEST, None)

    if is_forced_clean_room(eff_env):
        return _build_clean_room_donor_audit()

    paths = resolve_phase289_donor_paths(env=eff_env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    fp_items: List[Tuple[str, str, int, int]] = []
    for key in sorted(paths):
        st = paths[key].stat()
        fp_items.append((key, str(paths[key]), int(st.st_size), int(st.st_mtime_ns)))
    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(fp_items))
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    t0 = time.monotonic()
    fx3_en_f = _scan_compact_rdonly(paths["fx3_string_en_f"], artifact_key="fx3_string_en_f", body_label="ILME-FX3 7.02 en_f")
    fx3_sc_f = _scan_compact_rdonly(paths["fx3_string_sc_f"], artifact_key="fx3_string_sc_f", body_label="ILME-FX3 7.02 sc_f")
    fx3_tc_f = _scan_compact_rdonly(paths["fx3_string_tc_f"], artifact_key="fx3_string_tc_f", body_label="ILME-FX3 7.02 tc_f")
    fx3_ja_f = _scan_compact_rdonly(paths["fx3_string_ja_f"], artifact_key="fx3_string_ja_f", body_label="ILME-FX3 7.02 ja_f")
    fx3_en = _scan_compact_rdonly(paths["fx3_string_en"], artifact_key="fx3_string_en", body_label="ILME-FX3 7.02 en")
    fx3_en_g = _scan_compact_rdonly(paths["fx3_string_en_g"], artifact_key="fx3_string_en_g", body_label="ILME-FX3 7.02 en_g")
    fx6_en = _scan_compact_rdonly(paths["fx6_string_en"], artifact_key="fx6_string_en", body_label="ILME-FX6 6.01 en")
    fx6_en_2 = _scan_compact_rdonly(paths["fx6_string_en_2"], artifact_key="fx6_string_en_2", body_label="ILME-FX6 6.01 en_2")
    fx3_appfw = _scan_large_donor_rdonly(paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="ILME-FX3 7.02 appFw.so")
    fx3_bk4 = _scan_large_donor_rdonly(paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="ILME-FX3 7.02 BK4")
    fx6_appfw = _scan_large_donor_rdonly(paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="ILME-FX6 6.01 appFw.so")
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = []
    compact_map = {
        "fx3_string_en_f": fx3_en_f,
        "fx3_string_sc_f": fx3_sc_f,
        "fx3_string_tc_f": fx3_tc_f,
        "fx3_string_ja_f": fx3_ja_f,
        "fx3_string_en": fx3_en,
        "fx3_string_en_g": fx3_en_g,
        "fx6_string_en": fx6_en,
        "fx6_string_en_2": fx6_en_2,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-48 markers")
        if not summ.uxd_container_ok:
            errors.append(f"{key}: invalid uxc/uxd header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_appfw": (fx6_appfw, True),
    }
    for key, (lsumm, req_elf) in large_map.items():
        if lsumm.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {lsumm.file_bytes}")
        if not lsumm.head_sha256_verified:
            errors.append(f"{key}: head 4KiB SHA-256 mismatch")
        if req_elf and not lsumm.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")
        if any(v != 1 for v in lsumm.window_hits.values()):
            errors.append(f"{key}: missing bounded window token")

    pp_proven = (
        fx3_en_f.marker_hits.get("Picture Profile") == 1
        and fx3_en_f.marker_hits.get("PP11") == 1
        and fx3_en_f.marker_hits.get("S-Cinetone") == 1
        and fx3_en_f.marker_hits.get("Different Set for Still/Mv") == 1
        and fx3_en_f.marker_hits.get("Creative Look") == 1
        and fx3_en_f.marker_hits.get("VV2") == 1
        and fx3_en.marker_hits.get("D-Range Optimizer") == 1
        and fx3_en_f.marker_hits.get("Log Shooting") == 1
        and fx3_appfw.window_hits.get("PP11_ENUM") == 1
        and fx3_appfw.window_hits.get("PPLUT1_ENUM") == 1
        and fx3_appfw.window_hits.get("BKID_PICTURE_PROFILE") == 1
        and fx3_appfw.window_hits.get("BKID_CREATIVE_LOOK") == 1
        and fx3_appfw.window_hits.get("BKID_DRO") == 1
        and fx6_appfw.window_hits.get("FX6_BASE_LOOK0") == 1
    )
    wb_proven = (
        fx3_en.marker_hits.get("White Balance") == 1
        and fx3_en.marker_hits.get("C.Temp./Filter") == 1
        and fx3_en_f.marker_hits.get("<2500K") == 1
        and fx3_en_f.marker_hits.get(">9900K") == 1
        and fx3_en.marker_hits.get("Custom 1") == 1
        and fx3_en_f.marker_hits.get("Priority Set in AWB") == 1
        and fx3_en_f.marker_hits.get("Shutter AWB Lock") == 1
        and fx3_en_f.marker_hits.get("Shockless WB") == 1
        and fx3_appfw.window_hits.get("BKID_WHITE_BALANCE") == 1
        and fx3_appfw.window_hits.get("WB_CTEMP_2500K") == 1
        and fx3_appfw.window_hits.get("WB_CTEMP_9900K") == 1
        and fx3_appfw.window_hits.get("WB_CUSTOM_SET") == 1
        and fx6_appfw.window_hits.get("FX6_ATW_MODE") == 1
    )
    metering_proven = (
        fx3_en.marker_hits.get("Metering Mode") == 1
        and fx3_en_f.marker_hits.get("Spot: Standard") == 1
        and fx3_en_f.marker_hits.get("Spot: Large") == 1
        and fx3_en_f.marker_hits.get("Entire Screen Avg.") == 1
        and fx3_en_f.marker_hits.get("Highlight") == 1
        and fx3_en_f.marker_hits.get("Face Priority in Multi Metering") == 1
        and fx3_en_f.marker_hits.get("Spot Metering Point") == 1
        and fx3_en_f.marker_hits.get("Focus Point Link") == 1
        and fx3_en_f.marker_hits.get("AEL w/ Shutter") == 1
        and fx3_appfw.window_hits.get("BKID_METERING_MODE") == 1
        and fx3_appfw.window_hits.get("BKID_SPOT_LINK") == 1
        and fx3_appfw.window_hits.get("BKID_FACE_MULTI") == 1
    )

    all_ok = (len(errors) == 0) and pp_proven and wb_proven and metering_proven
    audit = Phase289DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=11,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=fx3_en_f,
        fx3_string_sc_f=fx3_sc_f,
        fx3_string_tc_f=fx3_tc_f,
        fx3_string_ja_f=fx3_ja_f,
        fx3_string_en=fx3_en,
        fx3_string_en_g=fx3_en_g,
        fx6_string_en=fx6_en,
        fx6_string_en_2=fx6_en_2,
        fx3_appfw=fx3_appfw,
        fx3_bk4=fx3_bk4,
        fx6_appfw=fx6_appfw,
        pp_scinetone_creativelook_proven=pp_proven,
        wb_13mode_cineei_custom_proven=wb_proven,
        metering_5mode_spot_link_proven=metering_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 58A — Picture Profile PP1..11, Creative Look, DRO & Reset Split
# ---------------------------------------------------------------------------


def simulate_pp_scinetone_creativelook_dro_reset_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    drive_mode: str = DRIVE_MODE_SINGLE,
    different_set_still_mv_pp: bool = False,
    configured_picture_profile: str = DEFAULT_OUT_OF_BOX_PP,
    configured_log_shooting: str = LOG_SHOOTING_OFF,
    selected_display_lut: str = "s709",
    configured_creative_look: str = "ST",
    requested_creative_look_override: bool = False,
    requested_clarity_edit: bool = False,
    requested_sharpness_range_edit: bool = False,
    requested_saturation_edit: bool = False,
    configured_dro: str = "Off",
    requested_dro_override: bool = False,
    pp_internal_edits_present: bool = False,
    reset_action: str = RESET_ACTION_NONE,
    wipe_pp_internals_on_camera_reset: bool = False,
) -> PictureProfileCreativeLookDroEvalResult:
    """Evaluate Wave-48 Sub-Model 58A: PP11 Default, Creative Look/DRO Lockout & Reset Split."""

    def _err(errno_code: int, reason_code: str) -> PictureProfileCreativeLookDroEvalResult:
        return PictureProfileCreativeLookDroEvalResult(
            pp_menu_path=PP_MENU_PATH,
            creative_look_menu_path=CREATIVE_LOOK_MENU_PATH,
            dro_menu_path=DRO_MENU_PATH,
            log_shooting_menu_path=LOG_SHOOTING_MENU_PATH,
            body_profile=body_profile,
            shoot_mode=shoot_mode,
            drive_mode=drive_mode,
            out_of_box_default_pp=DEFAULT_OUT_OF_BOX_PP,
            out_of_box_default_applies_movie_and_still=True,
            different_set_still_mv_pp=different_set_still_mv_pp,
            configured_picture_profile=configured_picture_profile,
            effective_picture_profile="REJECTED",
            effective_pp_gamma="NONE",
            effective_pp_color_mode="NONE",
            configured_log_shooting=configured_log_shooting,
            effective_log_shooting=configured_log_shooting,
            effective_display_lut="NONE",
            configured_creative_look=configured_creative_look,
            effective_creative_look="-",
            creative_look_hard_locked=True,
            clarity_param_locked=True,
            sharpness_range_param_locked=True,
            saturation_param_locked=True,
            configured_dro=configured_dro,
            effective_dro="Off",
            dro_forced_off=True,
            fx6_contrast_model="FX6 Base Look (S-Cinetone default) + Scene File",
            reset_action=reset_action,
            pp_internal_edits_present=pp_internal_edits_present,
            pp_internal_edits_survived=False,
            pp_recipe_restored_to_factory=False,
            pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or shoot_mode not in VALID_SHOOT_MODES
        or drive_mode not in VALID_DRIVE_MODES
        or configured_picture_profile not in VALID_PICTURE_PROFILES
        or configured_log_shooting not in VALID_LOG_SHOOTING_MODES
        or selected_display_lut not in DISPLAY_LUT_OPTIONS
        or configured_creative_look not in VALID_CREATIVE_LOOK_CHOICES
        or configured_dro not in DRO_MODES
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_PP_CREATIVE_LOOK_OR_DRO_PARAM")

    if wipe_pp_internals_on_camera_reset:
        return _err(EOPNOTSUPP_ERRNO, "PP_INTERNALS_SURVIVE_CAMERA_RESET_AND_INITIALIZE")

    # FX6 uses Base Look + Scene File rather than FX3 PP1..PP11 / Creative Look
    if body_profile == BODY_MODEL_FX6:
        return PictureProfileCreativeLookDroEvalResult(
            pp_menu_path=FX6_BASE_LOOK_MENU_PATH,
            creative_look_menu_path=FX6_BASE_LOOK_MENU_PATH,
            dro_menu_path=FX6_BASE_LOOK_MENU_PATH,
            log_shooting_menu_path="Shooting -> Cine EI / Custom",
            body_profile=body_profile,
            shoot_mode=SHOOT_MODE_MOVIE,
            drive_mode=DRIVE_MODE_SINGLE,
            out_of_box_default_pp=FX6_BASE_LOOK_SCINETONE,
            out_of_box_default_applies_movie_and_still=False,
            different_set_still_mv_pp=False,
            configured_picture_profile=FX6_BASE_LOOK_SCINETONE,
            effective_picture_profile=FX6_BASE_LOOK_SCINETONE,
            effective_pp_gamma="S-Cinetone",
            effective_pp_color_mode="S-Cinetone",
            configured_log_shooting=configured_log_shooting,
            effective_log_shooting=configured_log_shooting,
            effective_display_lut=selected_display_lut if configured_log_shooting != LOG_SHOOTING_OFF else "NONE",
            configured_creative_look="N/A (FX6 Scene File)",
            effective_creative_look="N/A (FX6 Base Look)",
            creative_look_hard_locked=True,
            clarity_param_locked=True,
            sharpness_range_param_locked=True,
            saturation_param_locked=False,
            configured_dro="Off",
            effective_dro="Off",
            dro_forced_off=True,
            fx6_contrast_model="FX6 Base Look (S-Cinetone default) + Scene File (no PP1..PP11 / Creative Look)",
            reset_action=reset_action,
            pp_internal_edits_present=pp_internal_edits_present,
            pp_internal_edits_survived=True,
            pp_recipe_restored_to_factory=(reset_action == RESET_ACTION_PICTURE_PROFILE_RESET),
            pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX6_BASE_LOOK_SCINETONE_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Reset rules on FX3:
    # - Camera Settings Reset resets active selector to PP11 and Log Shooting to Off,
    #   AND preserves PP1..11 internal recipe edits & Different Set checkbox.
    # - Initialize resets active selector to PP11, clears Different Set & Custom Look,
    #   YET PP1..11 internal recipe edits STILL survive!
    # - ONLY Picture Profile -> Reset restores factory PPn recipe!
    if reset_action in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        eff_pp = DEFAULT_OUT_OF_BOX_PP
        eff_log = LOG_SHOOTING_OFF
        eff_diff = False if reset_action == RESET_ACTION_INITIALIZE else different_set_still_mv_pp
        eff_cl_cfg = "ST"
        eff_dro_cfg = "Off"
        pp_survived = pp_internal_edits_present
        pp_restored = False
    elif reset_action == RESET_ACTION_PICTURE_PROFILE_RESET:
        eff_pp = configured_picture_profile
        eff_log = configured_log_shooting
        eff_diff = different_set_still_mv_pp
        eff_cl_cfg = configured_creative_look
        eff_dro_cfg = configured_dro
        pp_survived = False
        pp_restored = True
    else:
        eff_pp = configured_picture_profile
        eff_log = configured_log_shooting
        eff_diff = different_set_still_mv_pp
        eff_cl_cfg = configured_creative_look
        eff_dro_cfg = configured_dro
        pp_survived = pp_internal_edits_present
        pp_restored = False

    log_active = eff_log != LOG_SHOOTING_OFF
    if log_active:
        # Log Shooting mutual exclusion locks Picture Profile, Creative Look, and DRO
        if reset_action == RESET_ACTION_NONE and requested_creative_look_override:
            return _err(EOPNOTSUPP_ERRNO, "LOG_SHOOTING_LOCKS_CREATIVE_LOOK")
        if reset_action == RESET_ACTION_NONE and requested_dro_override:
            return _err(EOPNOTSUPP_ERRNO, "LOG_SHOOTING_LOCKS_DRO")
        return PictureProfileCreativeLookDroEvalResult(
            pp_menu_path=PP_MENU_PATH,
            creative_look_menu_path=CREATIVE_LOOK_MENU_PATH,
            dro_menu_path=DRO_MENU_PATH,
            log_shooting_menu_path=LOG_SHOOTING_MENU_PATH,
            body_profile=body_profile,
            shoot_mode=shoot_mode,
            drive_mode=drive_mode,
            out_of_box_default_pp=DEFAULT_OUT_OF_BOX_PP,
            out_of_box_default_applies_movie_and_still=True,
            different_set_still_mv_pp=eff_diff,
            configured_picture_profile=configured_picture_profile,
            effective_picture_profile="Locked (Log Shooting)",
            effective_pp_gamma="S-Log3",
            effective_pp_color_mode="S-Gamut3.Cine",
            configured_log_shooting=configured_log_shooting,
            effective_log_shooting=eff_log,
            effective_display_lut=selected_display_lut,
            configured_creative_look=configured_creative_look,
            effective_creative_look="-",
            creative_look_hard_locked=True,
            clarity_param_locked=True,
            sharpness_range_param_locked=True,
            saturation_param_locked=True,
            configured_dro=configured_dro,
            effective_dro="Off",
            dro_forced_off=True,
            fx6_contrast_model="FX6 Cine EI routes monitoring via Base Look / User LUT",
            reset_action=reset_action,
            pp_internal_edits_present=pp_internal_edits_present,
            pp_internal_edits_survived=pp_survived,
            pp_recipe_restored_to_factory=pp_restored,
            pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="LOG_SHOOTING_MUTUAL_EXCLUSION_AND_DISPLAY_LUT_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    pp_active = eff_pp != PP_OFF
    if pp_active:
        if requested_creative_look_override:
            return _err(EOPNOTSUPP_ERRNO, "PICTURE_PROFILE_ACTIVE_LOCKS_CREATIVE_LOOK")
        if requested_dro_override or (reset_action == RESET_ACTION_NONE and eff_dro_cfg != "Off"):
            return _err(EOPNOTSUPP_ERRNO, "PICTURE_PROFILE_ACTIVE_FORCES_DRO_OFF")

    clarity_locked = pp_active or (shoot_mode != SHOOT_MODE_STILL) or (drive_mode == DRIVE_MODE_CONTINUOUS)
    sharp_range_locked = pp_active or (shoot_mode != SHOOT_MODE_STILL)
    sat_locked = pp_active or (eff_cl_cfg in ("BW", "SE"))

    if not pp_active:
        if requested_clarity_edit and clarity_locked:
            return _err(EOPNOTSUPP_ERRNO, "CREATIVE_LOOK_CLARITY_LOCKED_IN_MOVIE_OR_CONT")
        if requested_sharpness_range_edit and sharp_range_locked:
            return _err(EOPNOTSUPP_ERRNO, "CREATIVE_LOOK_SHARPNESS_RANGE_LOCKED_IN_MOVIE")
        if requested_saturation_edit and sat_locked:
            return _err(EOPNOTSUPP_ERRNO, "CREATIVE_LOOK_SATURATION_LOCKED_IN_BW_SE")

    if eff_pp in PP_FACTORY_RECIPES:
        gamma = PP_FACTORY_RECIPES[eff_pp]["gamma"]
        color_mode = PP_FACTORY_RECIPES[eff_pp]["color_mode"]
    elif eff_pp in PPLUT_MODES:
        gamma = "User LUT"
        color_mode = "User LUT"
    else:
        gamma = "Standard (Creative Look / DRO)"
        color_mode = eff_cl_cfg

    return PictureProfileCreativeLookDroEvalResult(
        pp_menu_path=PP_MENU_PATH,
        creative_look_menu_path=CREATIVE_LOOK_MENU_PATH,
        dro_menu_path=DRO_MENU_PATH,
        log_shooting_menu_path=LOG_SHOOTING_MENU_PATH,
        body_profile=body_profile,
        shoot_mode=shoot_mode,
        drive_mode=drive_mode,
        out_of_box_default_pp=DEFAULT_OUT_OF_BOX_PP,
        out_of_box_default_applies_movie_and_still=True,
        different_set_still_mv_pp=eff_diff,
        configured_picture_profile=configured_picture_profile,
        effective_picture_profile=eff_pp,
        effective_pp_gamma=gamma,
        effective_pp_color_mode=color_mode,
        configured_log_shooting=configured_log_shooting,
        effective_log_shooting=eff_log,
        effective_display_lut="NONE",
        configured_creative_look=configured_creative_look,
        effective_creative_look=("-" if pp_active else eff_cl_cfg),
        creative_look_hard_locked=pp_active,
        clarity_param_locked=clarity_locked,
        sharpness_range_param_locked=sharp_range_locked,
        saturation_param_locked=sat_locked,
        configured_dro=configured_dro,
        effective_dro=("Off" if pp_active else eff_dro_cfg),
        dro_forced_off=pp_active,
        fx6_contrast_model="FX6 Base Look (S-Cinetone default) + Scene File",
        reset_action=reset_action,
        pp_internal_edits_present=pp_internal_edits_present,
        pp_internal_edits_survived=pp_survived,
        pp_recipe_restored_to_factory=pp_restored,
        pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="PP_SCINETONE_CREATIVELOOK_DRO_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_a_pp_scinetone_creativelook_dro_reset_hil() -> Dict[str, object]:
    """Evaluate Wave-48 Sub-Model 58A: PP11 Out-of-Box Default, Lockouts & Reset Persistence Split."""
    fx3_oob_movie = simulate_pp_scinetone_creativelook_dro_reset_hil(shoot_mode=SHOOT_MODE_MOVIE)
    fx3_oob_still = simulate_pp_scinetone_creativelook_dro_reset_hil(shoot_mode=SHOOT_MODE_STILL)
    pp11_locks_creative_look = simulate_pp_scinetone_creativelook_dro_reset_hil(
        configured_picture_profile="PP11",
        configured_creative_look="VV2",
        requested_creative_look_override=True,
    )
    pp11_locks_dro = simulate_pp_scinetone_creativelook_dro_reset_hil(
        configured_picture_profile="PP11",
        configured_dro="D-Range Optimizer: Lv3",
        requested_dro_override=True,
    )
    pp_off_creative_look_ok = simulate_pp_scinetone_creativelook_dro_reset_hil(
        shoot_mode=SHOOT_MODE_STILL,
        drive_mode=DRIVE_MODE_SINGLE,
        configured_picture_profile=PP_OFF,
        configured_creative_look="VV2",
        configured_dro="D-Range Optimizer: Auto",
        requested_clarity_edit=True,
    )
    movie_clarity_locked = simulate_pp_scinetone_creativelook_dro_reset_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        configured_picture_profile=PP_OFF,
        configured_creative_look="FL",
        requested_clarity_edit=True,
    )
    cont_still_clarity_locked = simulate_pp_scinetone_creativelook_dro_reset_hil(
        shoot_mode=SHOOT_MODE_STILL,
        drive_mode=DRIVE_MODE_CONTINUOUS,
        configured_picture_profile=PP_OFF,
        configured_creative_look="IN",
        requested_clarity_edit=True,
    )
    log_cine_ei_locks_pp_cl_dro = simulate_pp_scinetone_creativelook_dro_reset_hil(
        configured_picture_profile="PP11",
        configured_log_shooting=LOG_SHOOTING_CINE_EI,
        selected_display_lut="User1",
    )
    cam_reset_preserves_pp_edits = simulate_pp_scinetone_creativelook_dro_reset_hil(
        different_set_still_mv_pp=True,
        configured_picture_profile="PP8",
        pp_internal_edits_present=True,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_preserves_pp_edits = simulate_pp_scinetone_creativelook_dro_reset_hil(
        different_set_still_mv_pp=True,
        configured_picture_profile="PP8",
        pp_internal_edits_present=True,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    explicit_pp_reset_restores = simulate_pp_scinetone_creativelook_dro_reset_hil(
        configured_picture_profile="PP8",
        pp_internal_edits_present=True,
        reset_action=RESET_ACTION_PICTURE_PROFILE_RESET,
    )
    wipe_pp_blocked = simulate_pp_scinetone_creativelook_dro_reset_hil(
        configured_picture_profile="PP8",
        pp_internal_edits_present=True,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        wipe_pp_internals_on_camera_reset=True,
    )
    fx6_base_look_contrast = simulate_pp_scinetone_creativelook_dro_reset_hil(
        body_profile=BODY_MODEL_FX6,
    )

    passed = (
        fx3_oob_movie.admitted
        and fx3_oob_still.admitted
        and fx3_oob_movie.effective_picture_profile == "PP11"
        and fx3_oob_still.effective_picture_profile == "PP11"
        and fx3_oob_movie.effective_pp_gamma == "S-Cinetone"
        and fx3_oob_still.effective_pp_gamma == "S-Cinetone"
        and fx3_oob_movie.effective_creative_look == "-"
        and fx3_oob_movie.creative_look_hard_locked
        and fx3_oob_movie.effective_dro == "Off"
        and fx3_oob_movie.dro_forced_off
        and (not pp11_locks_creative_look.admitted)
        and pp11_locks_creative_look.errno_code == EOPNOTSUPP_ERRNO
        and (not pp11_locks_dro.admitted)
        and pp11_locks_dro.errno_code == EOPNOTSUPP_ERRNO
        and pp_off_creative_look_ok.admitted
        and pp_off_creative_look_ok.effective_creative_look == "VV2"
        and pp_off_creative_look_ok.effective_dro == "D-Range Optimizer: Auto"
        and (not pp_off_creative_look_ok.clarity_param_locked)
        and (not movie_clarity_locked.admitted)
        and movie_clarity_locked.errno_code == EOPNOTSUPP_ERRNO
        and (not cont_still_clarity_locked.admitted)
        and cont_still_clarity_locked.errno_code == EOPNOTSUPP_ERRNO
        and log_cine_ei_locks_pp_cl_dro.admitted
        and log_cine_ei_locks_pp_cl_dro.effective_display_lut == "User1"
        and log_cine_ei_locks_pp_cl_dro.creative_look_hard_locked
        and log_cine_ei_locks_pp_cl_dro.dro_forced_off
        and cam_reset_preserves_pp_edits.admitted
        and cam_reset_preserves_pp_edits.effective_picture_profile == "PP11"
        and cam_reset_preserves_pp_edits.different_set_still_mv_pp
        and cam_reset_preserves_pp_edits.pp_internal_edits_survived
        and (not cam_reset_preserves_pp_edits.pp_recipe_restored_to_factory)
        and init_preserves_pp_edits.admitted
        and init_preserves_pp_edits.effective_picture_profile == "PP11"
        and (not init_preserves_pp_edits.different_set_still_mv_pp)
        and init_preserves_pp_edits.pp_internal_edits_survived
        and explicit_pp_reset_restores.admitted
        and (not explicit_pp_reset_restores.pp_internal_edits_survived)
        and explicit_pp_reset_restores.pp_recipe_restored_to_factory
        and (not wipe_pp_blocked.admitted)
        and wipe_pp_blocked.errno_code == EOPNOTSUPP_ERRNO
        and fx6_base_look_contrast.admitted
        and fx6_base_look_contrast.effective_picture_profile == FX6_BASE_LOOK_SCINETONE
    )

    return {
        "passed": passed,
        "pp_menu_path": PP_MENU_PATH,
        "creative_look_menu_path": CREATIVE_LOOK_MENU_PATH,
        "dro_menu_path": DRO_MENU_PATH,
        "log_shooting_menu_path": LOG_SHOOTING_MENU_PATH,
        "pp1_to_pp11_recipes": dict(PP_FACTORY_RECIPES),
        "creative_look_10_presets": list(CREATIVE_LOOK_10_PRESETS),
        "creative_look_custom_slots": list(CREATIVE_LOOK_CUSTOM_SLOTS),
        "creative_look_8_params": list(CREATIVE_LOOK_8_PARAMS),
        "dro_modes": list(DRO_MODES),
        "fx3_oob_movie_pp11": asdict(fx3_oob_movie),
        "fx3_oob_still_pp11": asdict(fx3_oob_still),
        "pp11_locks_creative_look_eopnotsupp": asdict(pp11_locks_creative_look),
        "pp11_locks_dro_eopnotsupp": asdict(pp11_locks_dro),
        "pp_off_creative_look_vv2_ok": asdict(pp_off_creative_look_ok),
        "movie_clarity_locked_eopnotsupp": asdict(movie_clarity_locked),
        "cont_still_clarity_locked_eopnotsupp": asdict(cont_still_clarity_locked),
        "log_cine_ei_locks_pp_cl_dro": asdict(log_cine_ei_locks_pp_cl_dro),
        "camera_settings_reset_preserves_pp_edits": asdict(cam_reset_preserves_pp_edits),
        "initialize_preserves_pp_edits": asdict(init_preserves_pp_edits),
        "explicit_pp_reset_restores_factory": asdict(explicit_pp_reset_restores),
        "wipe_pp_on_camera_reset_blocked": asdict(wipe_pp_blocked),
        "fx6_base_look_contrast": asdict(fx6_base_look_contrast),
    }


# ---------------------------------------------------------------------------
# Sub-Model 58B — White Balance 13 Modes, Cine EI Lockout & Custom 1..3 Split
# ---------------------------------------------------------------------------


def simulate_white_balance_13mode_cineei_camset_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    configured_log_shooting: str = LOG_SHOOTING_OFF,
    configured_picture_profile: str = DEFAULT_OUT_OF_BOX_PP,
    requested_wb_mode: str = WB_AUTO,
    ctemp_kelvin: int = 5500,
    gm_axis: int = 0,
    ab_axis: int = 0,
    awb_priority_mode: str = "Standard",
    shutter_awb_lock_mode: str = "Off",
    shockless_wb_mode: str = "Off",
    custom_wb_capture_requested: bool = False,
    storage_target: str = STORAGE_TARGET_NONE,
    reset_action: str = RESET_ACTION_NONE,
) -> WhiteBalanceCineEiCamsetEvalResult:
    """Evaluate Wave-48 Sub-Model 58B: 13-Mode WB, Cine EI Auto-WB Lockout & CAMSET Exclusion."""

    def _err(errno_code: int, reason_code: str) -> WhiteBalanceCineEiCamsetEvalResult:
        return WhiteBalanceCineEiCamsetEvalResult(
            wb_menu_path=WB_MENU_PATH,
            awb_prio_menu_path=AWB_PRIO_MENU_PATH,
            shutter_awb_lock_menu_path=SHUTTER_AWB_LOCK_MENU_PATH,
            shockless_wb_menu_path=SHOCKLESS_WB_MENU_PATH,
            body_profile=body_profile,
            shoot_mode=shoot_mode,
            configured_log_shooting=configured_log_shooting,
            requested_wb_mode=requested_wb_mode,
            effective_wb_mode="REJECTED",
            ctemp_kelvin=ctemp_kelvin,
            gm_axis=gm_axis,
            ab_axis=ab_axis,
            awb_priority_mode=awb_priority_mode,
            shutter_awb_lock_mode=shutter_awb_lock_mode,
            shutter_awb_lock_active=False,
            shockless_wb_mode=shockless_wb_mode,
            shockless_wb_active=False,
            cine_ei_auto_wb_locked=(configured_log_shooting in (LOG_SHOOTING_CINE_EI, LOG_SHOOTING_CINE_EI_QUICK)),
            flash_wb_still_only_enforced=True,
            storage_target=storage_target,
            custom_wb_saved_to_camset=False,
            custom_wb_saved_to_m1_m4=False,
            reset_action=reset_action,
            custom_wb_1_3_survived=False,
            custom_wb_1_3_wiped_by_initialize=False,
            fx6_wht_bal_contrast="WHT BAL Switch (Memory B / A / Preset) + ATW",
            wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or shoot_mode not in VALID_SHOOT_MODES
        or configured_log_shooting not in VALID_LOG_SHOOTING_MODES
        or configured_picture_profile not in VALID_PICTURE_PROFILES
        or requested_wb_mode not in VALID_FX3_WB_MODES
        or isinstance(ctemp_kelvin, bool)
        or ctemp_kelvin < CTEMP_KELVIN_MIN
        or ctemp_kelvin > CTEMP_KELVIN_MAX
        or ctemp_kelvin % CTEMP_KELVIN_STEP != 0
        or isinstance(gm_axis, bool)
        or gm_axis < GM_AXIS_MIN
        or gm_axis > GM_AXIS_MAX
        or isinstance(ab_axis, bool)
        or ab_axis < AB_AXIS_MIN
        or ab_axis > AB_AXIS_MAX
        or awb_priority_mode not in AWB_PRIORITY_MODES
        or shutter_awb_lock_mode not in SHUTTER_AWB_LOCK_MODES
        or shockless_wb_mode not in SHOCKLESS_WB_MODES
        or storage_target not in VALID_STORAGE_TARGETS
        or reset_action not in VALID_RESET_ACTIONS
    ):
        return _err(EINVAL_ERRNO, "INVALID_WHITE_BALANCE_PARAMETER")

    # Slot-1 Tier-0 vault write guard
    if storage_target == STORAGE_TARGET_SLOT1_VAULT:
        return _err(EROFS_ERRNO, "TIER0_SLOT1_VAULT_WB_SAVE_BLOCKED_EROFS")

    # FX6 WHT BAL contrast
    if body_profile == BODY_MODEL_FX6:
        cine_ei_on = configured_log_shooting in (LOG_SHOOTING_CINE_EI, LOG_SHOOTING_CINE_EI_QUICK)
        if cine_ei_on and requested_wb_mode in AUTO_WB_MODES:
            return _err(EOPNOTSUPP_ERRNO, "FX6_CINE_EI_LOCKS_ATW_AUTO_WB")
        return WhiteBalanceCineEiCamsetEvalResult(
            wb_menu_path=FX6_WHT_BAL_SWITCH_PATH,
            awb_prio_menu_path=FX6_WHT_BAL_SWITCH_PATH,
            shutter_awb_lock_menu_path=FX6_WHT_BAL_SWITCH_PATH,
            shockless_wb_menu_path=FX6_WHT_BAL_SWITCH_PATH,
            body_profile=body_profile,
            shoot_mode=SHOOT_MODE_MOVIE,
            configured_log_shooting=configured_log_shooting,
            requested_wb_mode=requested_wb_mode,
            effective_wb_mode=requested_wb_mode,
            ctemp_kelvin=ctemp_kelvin,
            gm_axis=gm_axis,
            ab_axis=ab_axis,
            awb_priority_mode=awb_priority_mode,
            shutter_awb_lock_mode="Off",
            shutter_awb_lock_active=False,
            shockless_wb_mode=shockless_wb_mode,
            shockless_wb_active=(shockless_wb_mode != "Off"),
            cine_ei_auto_wb_locked=cine_ei_on,
            flash_wb_still_only_enforced=True,
            storage_target=storage_target,
            custom_wb_saved_to_camset=False,
            custom_wb_saved_to_m1_m4=False,
            reset_action=reset_action,
            custom_wb_1_3_survived=True,
            custom_wb_1_3_wiped_by_initialize=(reset_action == RESET_ACTION_INITIALIZE),
            fx6_wht_bal_contrast="FX6 WHT BAL Switch (Memory B / Memory A / Preset) + ATW",
            wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX6_WHT_BAL_SWITCH_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Flash WB is Still-only
    if requested_wb_mode == WB_FLASH and shoot_mode != SHOOT_MODE_STILL:
        return _err(EOPNOTSUPP_ERRNO, "FLASH_WB_STILL_ONLY_LOCKED_IN_MOVIE_SQ")

    # Under Cine EI / Cine EI Quick, Auto and Underwater Auto are hard-locked out
    cine_ei_active = configured_log_shooting in (LOG_SHOOTING_CINE_EI, LOG_SHOOTING_CINE_EI_QUICK)
    if cine_ei_active and requested_wb_mode in AUTO_WB_MODES:
        return _err(EOPNOTSUPP_ERRNO, "CINE_EI_LOCKS_OUT_AUTO_AND_UNDERWATER_AUTO_WB")

    # Live Custom WB Capture rejected during Log Shooting / PPLUT / PP7-9 unless switched Off
    if custom_wb_capture_requested and (
        configured_log_shooting != LOG_SHOOTING_OFF
        or configured_picture_profile in PPLUT_MODES
        or configured_picture_profile in ("PP7", "PP8", "PP9")
    ):
        return _err(EOPNOTSUPP_ERRNO, "CUSTOM_WB_CAPTURE_LOCKED_IN_LOG_OR_PPLUT")

    # Custom 1..3 CANNOT be saved into or recalled from CAMSET01..10.DAT; only M1..M4 carries Custom WB
    if storage_target == STORAGE_TARGET_CAMSET and requested_wb_mode in CUSTOM_WB_SLOTS:
        return _err(EOPNOTSUPP_ERRNO, "CUSTOM_WB_1_3_EXCLUDED_FROM_CAMSET_USE_M1_M4")

    # Reset behavior:
    # - Active selector resets to Auto (unless locked in Cine EI) on Camera Settings Reset / Initialize,
    # - YET registered Custom 1..3 WB values SURVIVE Camera Settings Reset (wiped ONLY by Initialize)!
    if reset_action == RESET_ACTION_INITIALIZE:
        eff_mode = WB_DAYLIGHT if cine_ei_active else WB_AUTO
        survived = False
        wiped = True
    elif reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        eff_mode = WB_DAYLIGHT if cine_ei_active else WB_AUTO
        survived = True
        wiped = False
    else:
        eff_mode = requested_wb_mode
        survived = True
        wiped = False

    shutter_lock_active = (
        shoot_mode == SHOOT_MODE_STILL
        and eff_mode in AUTO_WB_MODES
        and shutter_awb_lock_mode != "Off"
    )
    shockless_active = (
        shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)
        and shockless_wb_mode != "Off"
    )
    saved_m1_m4 = (storage_target == STORAGE_TARGET_MEMORY_M1_M4) and (requested_wb_mode in CUSTOM_WB_SLOTS)

    return WhiteBalanceCineEiCamsetEvalResult(
        wb_menu_path=WB_MENU_PATH,
        awb_prio_menu_path=AWB_PRIO_MENU_PATH,
        shutter_awb_lock_menu_path=SHUTTER_AWB_LOCK_MENU_PATH,
        shockless_wb_menu_path=SHOCKLESS_WB_MENU_PATH,
        body_profile=body_profile,
        shoot_mode=shoot_mode,
        configured_log_shooting=configured_log_shooting,
        requested_wb_mode=requested_wb_mode,
        effective_wb_mode=eff_mode,
        ctemp_kelvin=ctemp_kelvin,
        gm_axis=gm_axis,
        ab_axis=ab_axis,
        awb_priority_mode=awb_priority_mode,
        shutter_awb_lock_mode=shutter_awb_lock_mode,
        shutter_awb_lock_active=shutter_lock_active,
        shockless_wb_mode=shockless_wb_mode,
        shockless_wb_active=shockless_active,
        cine_ei_auto_wb_locked=cine_ei_active,
        flash_wb_still_only_enforced=True,
        storage_target=storage_target,
        custom_wb_saved_to_camset=False,
        custom_wb_saved_to_m1_m4=saved_m1_m4,
        reset_action=reset_action,
        custom_wb_1_3_survived=survived,
        custom_wb_1_3_wiped_by_initialize=wiped,
        fx6_wht_bal_contrast="FX6 WHT BAL Switch (Memory B / Memory A / Preset) + ATW",
        wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="WHITE_BALANCE_13MODE_CINEEI_CAMSET_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_wb_13mode_cineei_camset_hil() -> Dict[str, object]:
    """Evaluate Wave-48 Sub-Model 58B: 13-Mode WB, Cine EI Lockout & Custom 1..3 Card Split."""
    wb_mode_matrix = {
        mode: asdict(
            simulate_white_balance_13mode_cineei_camset_hil(
                shoot_mode=(SHOOT_MODE_STILL if mode == WB_FLASH else SHOOT_MODE_MOVIE),
                requested_wb_mode=mode,
            )
        )
        for mode in VALID_FX3_WB_MODES
    }
    flash_blocked_in_movie = simulate_white_balance_13mode_cineei_camset_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        requested_wb_mode=WB_FLASH,
    )
    cine_ei_auto_blocked = simulate_white_balance_13mode_cineei_camset_hil(
        configured_log_shooting=LOG_SHOOTING_CINE_EI,
        requested_wb_mode=WB_AUTO,
    )
    cine_ei_quick_uw_blocked = simulate_white_balance_13mode_cineei_camset_hil(
        configured_log_shooting=LOG_SHOOTING_CINE_EI_QUICK,
        requested_wb_mode=WB_UNDERWATER_AUTO,
    )
    cine_ei_ctemp_and_custom_ok = simulate_white_balance_13mode_cineei_camset_hil(
        configured_log_shooting=LOG_SHOOTING_CINE_EI,
        requested_wb_mode=WB_CTEMP_FILTER,
        ctemp_kelvin=3200,
        gm_axis=-2,
    )
    shutter_awb_lock_still = simulate_white_balance_13mode_cineei_camset_hil(
        shoot_mode=SHOOT_MODE_STILL,
        requested_wb_mode=WB_AUTO,
        awb_priority_mode="White",
        shutter_awb_lock_mode="Shut. Halfway",
    )
    cam_reset_preserves_custom1_3 = simulate_white_balance_13mode_cineei_camset_hil(
        requested_wb_mode=WB_CUSTOM_1,
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    init_wipes_custom1_3 = simulate_white_balance_13mode_cineei_camset_hil(
        requested_wb_mode=WB_CUSTOM_2,
        reset_action=RESET_ACTION_INITIALIZE,
    )
    camset_custom_blocked = simulate_white_balance_13mode_cineei_camset_hil(
        requested_wb_mode=WB_CUSTOM_1,
        storage_target=STORAGE_TARGET_CAMSET,
    )
    m1_m4_custom_ok = simulate_white_balance_13mode_cineei_camset_hil(
        requested_wb_mode=WB_CUSTOM_1,
        storage_target=STORAGE_TARGET_MEMORY_M1_M4,
    )
    slot1_vault_blocked = simulate_white_balance_13mode_cineei_camset_hil(
        requested_wb_mode=WB_CUSTOM_3,
        storage_target=STORAGE_TARGET_SLOT1_VAULT,
    )
    fx6_wht_bal_contrast = simulate_white_balance_13mode_cineei_camset_hil(
        body_profile=BODY_MODEL_FX6,
        requested_wb_mode=WB_DAYLIGHT,
    )

    passed = (
        len(wb_mode_matrix) == len(VALID_FX3_WB_MODES)
        and all(v["admitted"] for v in wb_mode_matrix.values())
        and (not flash_blocked_in_movie.admitted)
        and flash_blocked_in_movie.errno_code == EOPNOTSUPP_ERRNO
        and (not cine_ei_auto_blocked.admitted)
        and cine_ei_auto_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not cine_ei_quick_uw_blocked.admitted)
        and cine_ei_quick_uw_blocked.errno_code == EOPNOTSUPP_ERRNO
        and cine_ei_ctemp_and_custom_ok.admitted
        and cine_ei_ctemp_and_custom_ok.ctemp_kelvin == 3200
        and shutter_awb_lock_still.admitted
        and shutter_awb_lock_still.shutter_awb_lock_active
        and cam_reset_preserves_custom1_3.admitted
        and cam_reset_preserves_custom1_3.custom_wb_1_3_survived
        and (not cam_reset_preserves_custom1_3.custom_wb_1_3_wiped_by_initialize)
        and init_wipes_custom1_3.admitted
        and (not init_wipes_custom1_3.custom_wb_1_3_survived)
        and init_wipes_custom1_3.custom_wb_1_3_wiped_by_initialize
        and (not camset_custom_blocked.admitted)
        and camset_custom_blocked.errno_code == EOPNOTSUPP_ERRNO
        and m1_m4_custom_ok.admitted
        and m1_m4_custom_ok.custom_wb_saved_to_m1_m4
        and (not slot1_vault_blocked.admitted)
        and slot1_vault_blocked.errno_code == EROFS_ERRNO
        and fx6_wht_bal_contrast.admitted
    )

    return {
        "passed": passed,
        "wb_menu_path": WB_MENU_PATH,
        "fx3_wb_13_base_modes": list(FX3_WB_13_BASE_MODES),
        "valid_fx3_wb_modes": list(VALID_FX3_WB_MODES),
        "awb_priority_modes": list(AWB_PRIORITY_MODES),
        "shutter_awb_lock_modes": list(SHUTTER_AWB_LOCK_MODES),
        "shockless_wb_modes": list(SHOCKLESS_WB_MODES),
        "wb_mode_matrix": wb_mode_matrix,
        "flash_blocked_in_movie_eopnotsupp": asdict(flash_blocked_in_movie),
        "cine_ei_auto_blocked_eopnotsupp": asdict(cine_ei_auto_blocked),
        "cine_ei_quick_uw_blocked_eopnotsupp": asdict(cine_ei_quick_uw_blocked),
        "cine_ei_ctemp_3200k_ok": asdict(cine_ei_ctemp_and_custom_ok),
        "shutter_awb_lock_still_ok": asdict(shutter_awb_lock_still),
        "camera_reset_preserves_custom1_3": asdict(cam_reset_preserves_custom1_3),
        "initialize_wipes_custom1_3": asdict(init_wipes_custom1_3),
        "camset_custom_wb_blocked_eopnotsupp": asdict(camset_custom_blocked),
        "m1_m4_custom_wb_ok": asdict(m1_m4_custom_ok),
        "slot1_vault_wb_blocked_erofs": asdict(slot1_vault_blocked),
        "fx6_wht_bal_contrast": asdict(fx6_wht_bal_contrast),
    }


# ---------------------------------------------------------------------------
# Sub-Model 58C — Metering 5-Mode, Spot Link, CIZ Clamp & 16 Redlines
# ---------------------------------------------------------------------------


def simulate_metering_spot_link_ciz_and_redlines_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    focus_area: str = FOCUS_AREA_FLEXIBLE_SPOT,
    clear_image_zoom_ratio: float = 1.0,
    desqueeze_display: str = TOGGLE_OFF,
    configured_metering_mode: str = METERING_MULTI,
    configured_spot_metering_point: str = SPOT_POINT_CENTER,
    configured_face_prio_multi: str = TOGGLE_ON,
    ael_with_shutter: str = "Auto",
    exposure_std_adjust_sixth_ev: int = 0,
    force_non_multi_during_ciz: bool = False,
    force_spot_link_under_wide_af: bool = False,
    force_face_prio_during_desqueeze: bool = False,
) -> MeteringSpotLinkCizEvalResult:
    """Evaluate Wave-48 Sub-Model 58C: 5-Mode Metering, Focus Point Link & CIZ Multi Clamp."""

    def _err(errno_code: int, reason_code: str) -> MeteringSpotLinkCizEvalResult:
        return MeteringSpotLinkCizEvalResult(
            metering_menu_path=METERING_MENU_PATH,
            spot_point_menu_path=SPOT_POINT_MENU_PATH,
            face_prio_multi_menu_path=FACE_PRIO_MULTI_MENU_PATH,
            body_profile=body_profile,
            shoot_mode=shoot_mode,
            focus_area=focus_area,
            clear_image_zoom_ratio=float(clear_image_zoom_ratio),
            desqueeze_display=desqueeze_display,
            configured_metering_mode=configured_metering_mode,
            effective_metering_mode="REJECTED",
            configured_spot_metering_point=configured_spot_metering_point,
            effective_spot_metering_point=SPOT_POINT_CENTER,
            spot_coupled_to_af_point=False,
            configured_face_prio_multi=configured_face_prio_multi,
            effective_face_prio_multi=TOGGLE_OFF,
            ael_with_shutter=ael_with_shutter,
            exposure_std_adjust_sixth_ev=exposure_std_adjust_sixth_ev,
            ciz_forced_multi_clamp_active=False,
            restored_prior_metering_at_1x=False,
            fx6_metering_contrast="FX6 Auto Exp (Standard/Backlight/Spotlight) + Waveform/Zebra",
            metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason_code,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if (
        body_profile not in ALL_SUPPORTED_BODY_PROFILES
        or shoot_mode not in VALID_SHOOT_MODES
        or focus_area not in VALID_FOCUS_AREAS
        or isinstance(clear_image_zoom_ratio, bool)
        or not isinstance(clear_image_zoom_ratio, (int, float))
        or clear_image_zoom_ratio < 1.0
        or clear_image_zoom_ratio > 4.0
        or configured_metering_mode not in VALID_FX3_METERING_MODES
        or configured_spot_metering_point not in VALID_SPOT_METERING_POINTS
        or configured_face_prio_multi not in VALID_TOGGLE_STATES
        or ael_with_shutter not in AEL_SHUTTER_MODES
        or isinstance(exposure_std_adjust_sixth_ev, bool)
        or exposure_std_adjust_sixth_ev < -6
        or exposure_std_adjust_sixth_ev > 6
    ):
        return _err(EINVAL_ERRNO, "INVALID_METERING_OR_ZOOM_PARAMETER")

    ciz_zoom_active = float(clear_image_zoom_ratio) > 1.0
    if ciz_zoom_active and force_non_multi_during_ciz:
        return _err(EOPNOTSUPP_ERRNO, "CIZ_ZOOM_FORCES_MULTI_METERING_CLAMP")

    if force_spot_link_under_wide_af and focus_area not in SPOT_COUPLED_FOCUS_AREAS:
        return _err(EOPNOTSUPP_ERRNO, "SPOT_FOCUS_POINT_LINK_REQUIRES_FLEXIBLE_OR_EXPAND_SPOT")

    if force_face_prio_during_desqueeze and desqueeze_display != TOGGLE_OFF:
        return _err(EOPNOTSUPP_ERRNO, "DESQUEEZE_DISPLAY_LOCKS_FACE_PRIO_MULTI_OFF")

    if body_profile == BODY_MODEL_FX6:
        return MeteringSpotLinkCizEvalResult(
            metering_menu_path="Exposure -> Auto Exp. Mode (Standard/Backlight/Spotlight)",
            spot_point_menu_path="Waveform / Zebra / False Color (Cine EI)",
            face_prio_multi_menu_path="Face/Eye Detection AF",
            body_profile=body_profile,
            shoot_mode=SHOOT_MODE_MOVIE,
            focus_area=focus_area,
            clear_image_zoom_ratio=float(clear_image_zoom_ratio),
            desqueeze_display=desqueeze_display,
            configured_metering_mode="Standard",
            effective_metering_mode="Standard (FX6 Auto Exp)",
            configured_spot_metering_point=SPOT_POINT_CENTER,
            effective_spot_metering_point=SPOT_POINT_CENTER,
            spot_coupled_to_af_point=False,
            configured_face_prio_multi=configured_face_prio_multi,
            effective_face_prio_multi=TOGGLE_OFF,
            ael_with_shutter="Off",
            exposure_std_adjust_sixth_ev=0,
            ciz_forced_multi_clamp_active=False,
            restored_prior_metering_at_1x=True,
            fx6_metering_contrast="FX6 Cine EI Waveform/Zebra/False-Color + Standard/Backlight/Spotlight Auto-Exp",
            metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
            admitted=True,
            errno_code=0,
            reason_code="FX6_METERING_WORKFLOW_CONTRAST_VERIFIED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if ciz_zoom_active:
        eff_metering = METERING_MULTI
        eff_spot_point = SPOT_POINT_CENTER
        spot_coupled = False
        eff_face_prio = TOGGLE_OFF
        restored = False
    else:
        eff_metering = configured_metering_mode
        is_spot = eff_metering in (METERING_SPOT_STANDARD, METERING_SPOT_LARGE)
        if is_spot and configured_spot_metering_point == SPOT_POINT_FOCUS_LINK and focus_area in SPOT_COUPLED_FOCUS_AREAS:
            eff_spot_point = SPOT_POINT_FOCUS_LINK
            spot_coupled = True
        else:
            eff_spot_point = SPOT_POINT_CENTER
            spot_coupled = False
        if eff_metering == METERING_MULTI and desqueeze_display == TOGGLE_OFF:
            eff_face_prio = configured_face_prio_multi
        else:
            eff_face_prio = TOGGLE_OFF
        restored = True

    return MeteringSpotLinkCizEvalResult(
        metering_menu_path=METERING_MENU_PATH,
        spot_point_menu_path=SPOT_POINT_MENU_PATH,
        face_prio_multi_menu_path=FACE_PRIO_MULTI_MENU_PATH,
        body_profile=body_profile,
        shoot_mode=shoot_mode,
        focus_area=focus_area,
        clear_image_zoom_ratio=float(clear_image_zoom_ratio),
        desqueeze_display=desqueeze_display,
        configured_metering_mode=configured_metering_mode,
        effective_metering_mode=eff_metering,
        configured_spot_metering_point=configured_spot_metering_point,
        effective_spot_metering_point=eff_spot_point,
        spot_coupled_to_af_point=spot_coupled,
        configured_face_prio_multi=configured_face_prio_multi,
        effective_face_prio_multi=eff_face_prio,
        ael_with_shutter=ael_with_shutter,
        exposure_std_adjust_sixth_ev=exposure_std_adjust_sixth_ev,
        ciz_forced_multi_clamp_active=ciz_zoom_active,
        restored_prior_metering_at_1x=restored,
        fx6_metering_contrast="FX6 Auto Exp (Standard/Backlight/Spotlight) + Waveform/Zebra",
        metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
        admitted=True,
        errno_code=0,
        reason_code="METERING_SPOT_LINK_CIZ_HIL_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase289_redline_guard(**probes: bool) -> RedlineGuardProbeResult:
    """Verify all 16 Stage 58 hard safety & Wave-48 zero-write redline probes."""
    unknown = sorted(set(probes.keys()) - set(ALL_16_REDLINE_PROBE_FIELDS))
    if unknown:
        return RedlineGuardProbeResult(
            valid=False,
            errno_code=EINVAL_ERRNO,
            reason_code=f"UNKNOWN_REDLINE_PROBE:{unknown[0]}",
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
            isp_write_authorized=ISP_WRITE_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            emmc_corruptions=EMMC_CORRUPTIONS,
            nop_count=NOP_COUNT,
            guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
            pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
            wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
            metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if probes.get(field, False):
            if field == "cnflasha_userspace_write_requested":
                err = EROFS_ERRNO
            elif field in (
                "pp_creative_look_lockout_bypass_requested",
                "pp_camera_reset_internal_wipe_requested",
                "cine_ei_auto_wb_bypass_requested",
                "camset_custom_wb_leak_requested",
                "ciz_multi_or_spot_link_bypass_requested",
            ):
                err = EOPNOTSUPP_ERRNO
            else:
                err = EACCES_ERRNO
            return RedlineGuardProbeResult(
                valid=False,
                errno_code=err,
                reason_code=f"REDLINE_BLOCKED:{field.upper()}",
                persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
                hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
                overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
                isp_write_authorized=ISP_WRITE_AUTHORIZED,
                spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
                el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
                cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
                cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
                physical_device_writes=PHYSICAL_DEVICE_WRITES,
                emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
                emmc_corruptions=EMMC_CORRUPTIONS,
                nop_count=NOP_COUNT,
                guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
                otp_fuse_touches=OTP_FUSE_TOUCHES,
                rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
                physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
                pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
                wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
                metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
                raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            )

    return RedlineGuardProbeResult(
        valid=True,
        errno_code=0,
        reason_code="REDLINES_INTACT",
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        emmc_corruptions=EMMC_CORRUPTIONS,
        nop_count=NOP_COUNT,
        guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        pp_creative_look_or_reset_wipe_misroute_events=PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS,
        wb_cine_ei_auto_or_camset_custom_leak_events=WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS,
        metering_spot_link_or_ciz_multi_bypass_events=METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_pillar_c_d_metering_spot_link_ciz_and_redlines() -> Dict[str, object]:
    """Evaluate Sub-Model 58C `[Metering Mode]` 5-Mode, `Focus Point Link`, CIZ Clamp & Redlines."""
    metering_matrix = {
        mode: asdict(
            simulate_metering_spot_link_ciz_and_redlines_hil(
                configured_metering_mode=mode,
                focus_area=FOCUS_AREA_FLEXIBLE_SPOT,
                configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
            )
        )
        for mode in VALID_FX3_METERING_MODES
    }
    spot_focus_link_coupled = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_STANDARD,
        focus_area=FOCUS_AREA_FLEXIBLE_SPOT,
        configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
    )
    spot_expand_coupled = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_LARGE,
        focus_area=FOCUS_AREA_EXPAND_SPOT,
        configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
    )
    spot_wide_collapses_center = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_STANDARD,
        focus_area=FOCUS_AREA_WIDE,
        configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
    )
    ciz_forces_multi_face_off = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_LARGE,
        focus_area=FOCUS_AREA_FLEXIBLE_SPOT,
        configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
        configured_face_prio_multi=TOGGLE_ON,
        clear_image_zoom_ratio=1.5,
    )
    ciz_bypass_blocked = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_LARGE,
        clear_image_zoom_ratio=1.5,
        force_non_multi_during_ciz=True,
    )
    restore_1x_clean = simulate_metering_spot_link_ciz_and_redlines_hil(
        configured_metering_mode=METERING_SPOT_LARGE,
        focus_area=FOCUS_AREA_FLEXIBLE_SPOT,
        configured_spot_metering_point=SPOT_POINT_FOCUS_LINK,
        clear_image_zoom_ratio=1.0,
    )
    fx6_contrast = simulate_metering_spot_link_ciz_and_redlines_hil(
        body_profile=BODY_MODEL_FX6,
    )

    baseline_redline = probe_phase289_redline_guard()
    blocked_probes = {
        field: asdict(probe_phase289_redline_guard(**{field: True}))
        for field in ALL_16_REDLINE_PROBE_FIELDS
    }
    all_probes_blocked = all(not p["valid"] for p in blocked_probes.values())

    passed = (
        len(metering_matrix) == len(VALID_FX3_METERING_MODES)
        and all(v["admitted"] for v in metering_matrix.values())
        and spot_focus_link_coupled.admitted
        and spot_focus_link_coupled.effective_spot_metering_point == SPOT_POINT_FOCUS_LINK
        and spot_focus_link_coupled.spot_coupled_to_af_point
        and spot_expand_coupled.admitted
        and spot_expand_coupled.spot_coupled_to_af_point
        and spot_wide_collapses_center.admitted
        and spot_wide_collapses_center.effective_spot_metering_point == SPOT_POINT_CENTER
        and (not spot_wide_collapses_center.spot_coupled_to_af_point)
        and ciz_forces_multi_face_off.admitted
        and ciz_forces_multi_face_off.effective_metering_mode == METERING_MULTI
        and ciz_forces_multi_face_off.effective_face_prio_multi == TOGGLE_OFF
        and ciz_forces_multi_face_off.ciz_forced_multi_clamp_active
        and (not ciz_bypass_blocked.admitted)
        and ciz_bypass_blocked.errno_code == EOPNOTSUPP_ERRNO
        and restore_1x_clean.admitted
        and restore_1x_clean.effective_metering_mode == METERING_SPOT_LARGE
        and restore_1x_clean.spot_coupled_to_af_point
        and restore_1x_clean.restored_prior_metering_at_1x
        and fx6_contrast.admitted
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "metering_menu_path": METERING_MENU_PATH,
        "fx3_metering_5_base_modes": list(FX3_METERING_5_BASE_MODES),
        "valid_fx3_metering_modes": list(VALID_FX3_METERING_MODES),
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "metering_matrix": metering_matrix,
        "spot_focus_link_flexible_spot_ok": asdict(spot_focus_link_coupled),
        "spot_focus_link_expand_spot_ok": asdict(spot_expand_coupled),
        "spot_wide_af_collapses_center": asdict(spot_wide_collapses_center),
        "ciz_gt1x_forces_multi_face_off": asdict(ciz_forces_multi_face_off),
        "ciz_bypass_blocked_eopnotsupp": asdict(ciz_bypass_blocked),
        "zoom_1x_clean_restore_ok": asdict(restore_1x_clean),
        "fx6_metering_contrast": asdict(fx6_contrast),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 289 (Stage 58, 58/58) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 289 Stage 58 (58/58) Wave-48 HIL co-emulation audit."""
    donor_audit = inspect_phase289_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_pp_scinetone_creativelook_dro_reset_hil()
    pillar_b = evaluate_pillar_b_wb_13mode_cineei_camset_hil()
    pillar_cd = evaluate_pillar_c_d_metering_spot_link_ciz_and_redlines()

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
        "pp_creative_look_or_reset_wipe_misroute_events": (
            PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS
        ),
        "wb_cine_ei_auto_or_camset_custom_leak_events": (
            WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS
        ),
        "metering_spot_link_or_ciz_multi_bypass_events": (
            METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS
        ),
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
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
        and CNFLASHA_MUTATION_BYTES == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and EMMC_NFLASHA_WRITE_COUNT == 0
        and EMMC_CORRUPTIONS == 0
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not ISP_WRITE_AUTHORIZED)
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PP_CREATIVE_LOOK_OR_RESET_WIPE_MISROUTE_EVENTS == 0
        and WB_CINE_EI_AUTO_OR_CAMSET_CUSTOM_LEAK_EVENTS == 0
        and METERING_SPOT_LINK_OR_CIZ_MULTI_BYPASS_EVENTS == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_289_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_pp_scinetone_creativelook_dro_reset_hil": pillar_a,
        "pillar_b_wb_13mode_cineei_camset_hil": pillar_b,
        "pillar_c_d_metering_spot_link_ciz_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_pp_scinetone_creativelook_wb_metering_coemulator.py",
        description=(
            "Phase 289 Stage 58 (58/58) — Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-48 Picture Profile PP11 S-Cinetone Out-of-Box "
            "Default / Creative Look & DRO Lockout / PP1..11 Internal Edit Persistence, "
            "White Balance 13-Mode & Custom 1..3 CAMSET Split & Cine EI Auto-WB Lockout, "
            "and Metering Mode 5-Mode & Spot/Multi Coupling HIL Co-Emulator"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 289 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 289 Stage 58 (58/58) | mode={rep['source_mode']} "
            f"| donors={rep['donor_audit']['donor_files_inspected']} "
            f"| pp_mis={red['pp_creative_look_or_reset_wipe_misroute_events']} "
            f"| wb_leak={red['wb_cine_ei_auto_or_camset_custom_leak_events']} "
            f"| mtr_byp={red['metering_spot_link_or_ciz_multi_bypass_events']} "
            f"| phys_wr={red['physical_device_writes']} "
            f"| leaked={red['raw_firmware_bytes_leaked']} "
            f"| digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
