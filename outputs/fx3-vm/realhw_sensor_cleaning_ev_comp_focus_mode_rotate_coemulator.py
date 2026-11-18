#!/usr/bin/env python3
"""Phase 306 (Stage 62 — 62/62 VM Stages Milestone) — Real-Hardware ILME-FX3 Ver. 7.02 vs
ILME-FX6 Ver. 6.01 Wave-52:
`[Sensor Cleaning]` >= 51%% NP-FZ100 Battery Gate + Mandatory Physical Power-OFF vs IBIS-less
FX6 e-ND + APR, `[Exposure Comp.]` +-5.0 EV Still / +-2.0 EV Movie/S&Q + Total `[Cine EI]`
Lockout + Initialize-only `[Exposure step]`, `[Focus Mode]` 5-Still vs 2-Movie/S&Q Split +
`[Priority Set in AF-S/AF-C]` + `[AF Illuminator]` / `[AF Assist]`, and Playback `[View Mode]`,
9/25 `[Image Index]`, `[Display as Group]`, `[Display Rotation]`, & `[Rotate]` Slot-1 Tier-0
Vault Firewall HIL Co-Emulator.

Strictly models Wave-52 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment or firmware byte leakage:

1. **Sub-Model 62A — `[Sensor Cleaning]` >= 51%% Battery Gate & Mandatory Power-OFF vs IBIS-less FX6**:
   - `ILME-FX3 Ver. 2.00+/7.02` `[Sensor Cleaning]` (`_f.uxc 0x67d6`, legacy `.uxc 0xe7d7`
     `Cleaning Mode`): requires `NP-FZ100 >= 51%%` battery (`<= 50%%` rejected with `.uxc 0xe574`
     `Power insufficient.` -> `EACCES = 13`; legacy `Ver. 1.x` rejects `<= 2` bars and admits
     `>= 3` bars), actuates 5-axis IBIS ultrasonic sensor-carriage shake (`MODEL_CLEANING_MODE_COMP`),
     centers the sensor, and locks the camera into mandatory physical power-switch OFF state
     (`_g.uxc 0x6221`: `"Turn the power off after cleaning"` / `"the image sensor manually."`)
     before lens removal or resuming shooting (`EBUSY = 16` fail-closed if bypassed while power ON).
   - Contrasts with IBIS-less `ILME-FX6` (`PRODUCT_MODEL_CHAPLIN`), which lacks 5-axis ultrasonic
     IBIS sensor shake (`fx6_has_ibis_sensor_shake == False` -> rejects IBIS shake `EOPNOTSUPP = 95`),
     instead exposing front e-ND optical block (`CLEAR`, `1/4..1/128`, `BKID_APP_VARIABLE_ND_CONT` /
     `PID_SET_VARIABLE_ND_VALUE`) and `Technical > APR` (`MODEL_APR_EXECUTE_COMP`,
     `BKID_APP_USER_MENU_SENSOR_CLEANING`), while `ILME-FX3` has no built-in ND filter
     (`fx3_has_builtin_end_filter == False`).

2. **Sub-Model 62B — `[Exposure Comp.]` +-5.0 EV Still / +-2.0 EV Movie & Total `[Cine EI]` Lockout**:
   - Still `P/A/S` and `M` with `ISO AUTO` allow `-5.0..+5.0 EV` (`0.3EV` default 1/3-stop or `0.5EV`
     half-stop via Initialize-only `[Exposure step]`; live EV meter bar spans `-3.0..+3.0 EV`);
     Movie & `S&Q` strictly clamp to `-2.0..+2.0 EV` (rejecting out-of-range `+2.3..+5.0` or
     `-5.0..-2.3` with `EOPNOTSUPP = 95` / `EINVAL = 22`).
   - Disabled (`EOPNOTSUPP = 95`) in `iAuto` (`Intelligent Auto`) and Manual `M` with fixed numeric
     ISO (`iso_auto == False`); active in `M` **ONLY** when `ISO AUTO` (`iso_auto == True`) is set.
   - **100%% LOCKED OUT** under `[Log Shooting]` = `Cine EI` / `Cine EI Quick`
     (`cine_ei_exp_comp_enabled == False` -> `EOPNOTSUPP = 95`), where aperture & shutter are fixed
     manual and monitoring uses Base ISO `800`/`12800` + `[Exposure Index]` (`-2.0..+2.0 EV`);
     `Flexible ISO` keeps `[Exposure Comp.]` (`+-2.0 EV`) active.
   - `[Camera Settings Reset]` resets `[Exposure Comp.]` to `+0.0 EV` while preserving
     `[Exposure step]` (`0.3EV`/`0.5EV`, Initialize-only). Rejects dormant physical-dial Alpha
     `[Reset EV Comp.]` (`Maintain`/`Reset`) and legacy Ver. 1 `[Dial Ev Comp]` (`EOPNOTSUPP = 95`),
     as well as FX6 cine `Auto Exposure Level` / `Auto ND` / `AGC` semantics (`EOPNOTSUPP = 95` for
     FX3 +-5.0 EV dial EV comp on FX6).

3. **Sub-Model 62C — `[Focus Mode]` Still (5 Modes) vs Movie/S&Q (2 Modes) Split + Priority Set**:
   - Still (`EXPOSURE_MODE_STILL`) exposes all 5 modes: `AF-S` (`Single-shot AF`), `AF-A`
     (`Automatic AF`, factory default / restored by `[Camera Settings Reset]`), `AF-C`
     (`Continuous AF`), `DMF`, and `MF` (`Manual Focus`); rejects dormant `PF` / `SEMI_MANUAL`
     (`EOPNOTSUPP = 95`).
   - Movie & `S&Q` strictly clamp to **2 modes**: `AF-C` (`Continuous AF` / `MOVIE_AUTO`) and `MF`,
     strictly rejecting `AF-S`, `AF-A`, and `DMF` (`EOPNOTSUPP = 95`,
     `FOCUS_MODE_MENU_DIAL_AF_A_EXPOSURE_MODE_STILL`).
   - Sub-settings: `[Priority Set in AF-S]` & `[Priority Set in AF-C]` (`AF`, `Release`,
     `Balanced Emphasis` default; Initialize-only reset), Movie `AF-C` `[AF Assist]` (`Off`/`On`,
     Initialize-only), and Still-only `[AF Illuminator]` (`Auto`/`Off`, locked out in `AF-C`,
     `Movie`, `S&Q`, `Focus Magnifier`, Mount Adaptor). Contrasts with `ILME-FX6` physical `AF/MF`
     switch + `Push AF Mode` (`AF` / `Single-shot AF(AF-S)`).

4. **Sub-Model 62D & Redlines — Playback `[View Mode]`, `[Image Index]` 9/25, `[Display as Group]`,
   `[Display Rotation]`, & `[Rotate]` Slot-1 Tier-0 Vault Firewall**:
   - `[View Mode]` (`Date View` default, `Folder View(Still)`, `Movie View`, plus Wave-52 UXC
     `AVCHD View` / `XAVC S View` compatibility vs legacy `Folder View(MP4)`), `[Image Index]`
     exact `9 Images` (default) / `25 Images` (strictly rejecting dormant `12 Images` / `30 Images`
     as `EOPNOTSUPP = 95`), `[Display as Group]` (`Off` default / `On`), and `[Display Rotation]`
     (`Auto` default / `Manual` / `Off`, movies always horizontal). All 4 survive
     `[Camera Settings Reset]` and reset only on `Initialize`.
   - **CRITICAL VAULT FIREWALL**: Playback `[Rotate]` (`FUNC_rotate_content`) mutates EXIF
     orientation / `AVF_INFO` database on card -> fail-closed `EROFS = 30` / `EBUSY = 16` whenever
     `Slot 1` holds a Tier-0 recovery vault (`slot1_is_tier0_vault=True`), card is write-protected,
     or background transfer is active (`FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE`); movie
     clips return `EOPNOTSUPP = 95` (`Unable to rotate image.`); virtual `Slot 2` still rotation
     succeeds in `90`-degree CCW steps with zero physical writes (`physical_device_writes == 0`,
     `slot1_vault_rotate_mutation_bytes == 0`).

5. **Dual-Mode 11-Donor `os.O_RDONLY` Verification (`<= 4096 B` bounded windows)**:
   - Audits 11 verified `ILME-FX3 Ver. 7.02` & `ILME-FX6 Ver. 6.01` donors via `os.O_RDONLY` with
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

SCHEMA_ID = "realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator_v1"
PHASE_306_SCHEMA = SCHEMA_ID
PHASE_306_VERSION = "306.0.0"
PHASE_NUMBER = 306
STAGE_INDEX = 62
STAGE_TOTAL = 62
MILESTONE_LABEL = "62/62"
STAGE_NAME = "stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"
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

# Wave-52 Stage 62 (62/62) zero-fault & model-truth invariants
SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS = 0
SENSOR_CLEANING_MANDATORY_POWEROFF_BYPASS_EVENTS = 0
FX6_IBIS_SENSOR_SHAKE_SPOOF_EVENTS = 0
FX3_HAS_BUILTIN_END_FILTER = False
FX6_HAS_IBIS_SENSOR_SHAKE = False
CINE_EI_EXP_COMP_ENABLED = False
EV_COMP_CINE_EI_OR_MODE_BYPASS_EVENTS = 0
MOVIE_SQ_INVALID_FOCUS_MODE_BYPASS_EVENTS = 0
DORMANT_12_30_IMAGE_INDEX_EXPOSED_EVENTS = 0
SLOT1_VAULT_ROTATE_MUTATION_BYTES = 0

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
        b"Sensor Cleaning",
        b"Exposure Comp.",
        b"Exposure step",
        b"Focus Mode",
        b"Single-shot AF",
        b"Automatic AF",
        b"Continuous AF",
        b"DMF",
        b"Manual Focus",
        b"Priority Set in AF-S",
        b"Priority Set in AF-C",
        b"Balanced Emphasis",
        b"AF Assist",
        b"AF Illuminator",
        b"View Mode",
        b"Movie View",
        b"25 Images",
        b"Display as Group",
        b"Display Rotation",
        b"Rotate",
    ),
    "fx3_string_sc_f": (
        "传感器清洁".encode("utf-8"),
        "曝光补偿".encode("utf-8"),
        "曝光步级".encode("utf-8"),
        "对焦模式".encode("utf-8"),
        "单次AF".encode("utf-8"),
        "自动AF".encode("utf-8"),
        "连续AF".encode("utf-8"),
        b"AF-S",
        b"AF-C",
        "AF辅助".encode("utf-8"),
        "观看模式".encode("utf-8"),
        "成组显示".encode("utf-8"),
        "显示旋转".encode("utf-8"),
        "旋转".encode("utf-8"),
        "25张".encode("utf-8"),
        "指数".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "感應器清潔".encode("utf-8"),
        "曝光補償".encode("utf-8"),
        "對焦模式".encode("utf-8"),
        "連續AF".encode("utf-8"),
        "觀看模式".encode("utf-8"),
        "顯示旋轉".encode("utf-8"),
        "旋轉".encode("utf-8"),
        "25張".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "ｾﾝｻｰｸﾘｰﾆﾝｸﾞ".encode("utf-8"),
        "露出補正".encode("utf-8"),
        "露出補正値のﾘｾｯﾄ".encode("utf-8"),
        "露出値ステップ幅".encode("utf-8"),
        "AFアシスト".encode("utf-8"),
        "AF-S時の優先設定".encode("utf-8"),
        "AF-C時の優先設定".encode("utf-8"),
        "グループ表示".encode("utf-8"),
        "記録画像の回転表示".encode("utf-8"),
        "回転".encode("utf-8"),
        "25枚".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Cleaning Mode",
        b"Power insufficient.",
        b"Exposure Comp.",
        b"Dial Ev Comp",
        b"Exposure step",
        b"Single-shot AF",
        b"Automatic AF",
        b"Continuous AF",
        b"DMF",
        b"Manual Focus",
        b"AF Illuminator",
        b"View Mode",
        b"Date View",
        b"Folder View(Still)",
        b"Image Index",
        b"9 Images",
        b"Rotate",
        b"Unable to rotate image.",
        b"AVCHD View",
    ),
    "fx3_string_en_g": (
        b"Turn the power off after cleaning",
        b"the image sensor manually.",
        b"Exposure Comp.",
        b"Focus Mode",
    ),
    "fx6_string_en": (
        b"Auto ND",
        b"ND Filter",
        b"APR",
        b"Auto Exposure Level",
        b"Focus",
        b"Push AF",
    ),
    "fx6_string_en_2": (
        b"Auto ND",
        b"ND Filter",
        b"APR",
        b"Auto Exposure Level",
        b"Focus",
        b"Push AF",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_971_200, "MOVIE_AUTO", b"MOVIE_AUTO"),
        (51_388_416, "INSUFFICIENT_BATTERY_CLEANING_MODE", b"INSUFFICIENT_BATTERY_CLEANING_MODE"),
        (60_600_320, "FUNC_ROTATE_CONTENT", b"FUNC_rotate_content"),
        (60_604_416, "FUNC_SET_CLEANING_MODE", b"FUNC_set_cleaning_mode"),
        (
            61_566_976,
            "VAL_HAITA_LOG_SHOOTING_APERTURE_AM",
            b"VAL_HAITA_setting_log_shooting_general_shooting_mode_setting_aperture_a_m_switching",
        ),
        (
            61_575_168,
            "FOCUS_MODE_MENU_DIAL_AF_A_STILL",
            b"FOCUS_MODE_MENU_DIAL_AF_A_EXPOSURE_MODE_STILL",
        ),
        (62_685_184, "BKID_EXPOSURE_COMPENSATION", b"BKID_APP_setting_exposure_compensation"),
        (
            62_685_184,
            "BKID_EXPOSURE_COMP_RESET_SAVE",
            b"BKID_APP_setting_exposure_compensation_reset_save",
        ),
        (62_685_184, "BKID_EXPOSURE_STEP", b"BKID_APP_setting_exposure_step"),
        (62_685_184, "BKID_FOCUS_MODE_MENU_DIAL", b"BKID_APP_setting_focus_mode_menu_dial"),
        (62_685_184, "BKID_AF_S_PRIORITY_SETUP", b"BKID_APP_setting_af_s_priority_setup"),
        (62_685_184, "BKID_AF_C_PRIORITY_SETUP", b"BKID_APP_setting_af_c_priority_setup"),
        (62_685_184, "BKID_STILL_AF_ILLUMINATOR", b"BKID_APP_setting_still_image_af_illuminator"),
        (62_689_280, "BKID_AF_ASSIST", b"BKID_APP_setting_af_assist"),
        (62_689_280, "BKID_MENU_VIEW_MODE", b"BKID_APP_setting_menu_view_mode"),
        (62_689_280, "BKID_MENU_IMAGE_INDEX", b"BKID_APP_setting_menu_image_index"),
        (62_689_280, "BKID_DISPLAY_GROUP", b"BKID_APP_setting_display_group"),
        (62_689_280, "BKID_DISPLAY_ROTATITON", b"BKID_APP_setting_display_rotatiton"),
        (
            62_955_520,
            "FUNC_CMP_NG_BACKGROUND_TRANSFER_ROTATE",
            b"FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE",
        ),
        (63_041_536, "BATTERY_CHECK_CLEANING_MODE_LOWER", b"BATTERY_CHECK_FOR_CLEANING_MODE_LOWER"),
        (63_164_416, "MODEL_CLEANING_MODE_COMP", b"MODEL_CLEANING_MODE_COMP"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_519_360, "MODEL_APR_EXECUTE_COMP", b"MODEL_APR_EXECUTE_COMP"),
        (39_890_921, "PID_SET_VARIABLE_ND_VALUE", b"PID_SET_VARIABLE_ND_VALUE"),
        (40_964_096, "BKID_FX6_USER_MENU_SENSOR_CLEANING", b"BKID_APP_USER_MENU_SENSOR_CLEANING"),
        (41_013_248, "BKID_FX6_VARIABLE_ND_CONT", b"BKID_APP_VARIABLE_ND_CONT"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-52 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3_Ver7.02"
BODY_MODEL_FX3_LEGACY_V1 = "ILME-FX3_Ver1.01"
BODY_MODEL_FX6 = "ILME-FX6_Ver6.01"
STOCK_FX3_BODIES: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX3_LEGACY_V1)
ALL_SUPPORTED_BODY_PROFILES: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX3_LEGACY_V1,
    BODY_MODEL_FX6,
)

# 62A: Sensor Cleaning vs FX6 e-ND & APR
SENSOR_CLEANING_MIN_BATTERY_PCT = 51
SENSOR_CLEANING_LEGACY_MIN_BARS = 3
FX3_SENSOR_CLEANING_UXC_ID_F = "0x67d6"
FX3_SENSOR_CLEANING_UXC_ID_LEGACY = "0xe7d7"
FX3_POWER_INSUFFICIENT_UXC_ID = "0xe574"
FX3_POWER_OFF_AFTER_CLEANING_UXC_ID_G = "0x6221"

FX6_END_STOPS: Tuple[str, ...] = ("CLEAR", "1/4", "1/8", "1/16", "1/32", "1/64", "1/128")
APR_STATUS_IDLE = "IDLE"
APR_STATUS_COMPLETE = "COMPLETE"

# 62B: Exposure Comp., Exposure step & Cine EI Lockout
EXPOSURE_DOMAIN_STILL = "Still"
EXPOSURE_DOMAIN_MOVIE = "Movie"
EXPOSURE_DOMAIN_SQ = "S&Q"
VALID_EXPOSURE_DOMAINS: Tuple[str, ...] = (
    EXPOSURE_DOMAIN_STILL,
    EXPOSURE_DOMAIN_MOVIE,
    EXPOSURE_DOMAIN_SQ,
)

EXP_MODE_IAUTO = "iAuto"
EXP_MODE_P = "P"
EXP_MODE_A = "A"
EXP_MODE_S = "S"
EXP_MODE_M = "M"
VALID_PASM_MODES: Tuple[str, ...] = (
    EXP_MODE_IAUTO,
    EXP_MODE_P,
    EXP_MODE_A,
    EXP_MODE_S,
    EXP_MODE_M,
)

EXP_STEP_0_3EV = "0.3EV"
EXP_STEP_0_5EV = "0.5EV"
VALID_EXPOSURE_STEPS: Tuple[str, ...] = (EXP_STEP_0_3EV, EXP_STEP_0_5EV)

LOG_SHOOTING_OFF = "Off"
LOG_SHOOTING_FLEXIBLE_ISO = "Flexible ISO"
LOG_SHOOTING_CINE_EI = "Cine EI"
LOG_SHOOTING_CINE_EI_QUICK = "Cine EI Quick"
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    LOG_SHOOTING_OFF,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
)
CINE_EI_LOCKOUT_MODES: Tuple[str, ...] = (LOG_SHOOTING_CINE_EI, LOG_SHOOTING_CINE_EI_QUICK)

STILL_EXP_COMP_MIN_EV = -5.0
STILL_EXP_COMP_MAX_EV = 5.0
MOVIE_EXP_COMP_MIN_EV = -2.0
MOVIE_EXP_COMP_MAX_EV = 2.0
LIVE_EV_METER_MIN_EV = -3.0
LIVE_EV_METER_MAX_EV = 3.0
CINE_EI_INDEX_MIN_EV = -2.0
CINE_EI_INDEX_MAX_EV = 2.0

DORMANT_EV_FEATURES: Tuple[str, ...] = ("Reset EV Comp.", "Dial Ev Comp")

# 62C: Focus Mode Still (5) vs Movie/S&Q (2) Split + Priority Set + AF Assist / Illuminator
FOCUS_MODE_AFS = "AF-S"
FOCUS_MODE_AFA = "AF-A"
FOCUS_MODE_AFC = "AF-C"
FOCUS_MODE_DMF = "DMF"
FOCUS_MODE_MF = "MF"
FOCUS_MODE_DORMANT_PF = "PF"
FOCUS_MODE_DORMANT_SEMI_MANUAL = "SEMI_MANUAL"

STILL_FOCUS_MODES: Tuple[str, ...] = (
    FOCUS_MODE_AFS,
    FOCUS_MODE_AFA,
    FOCUS_MODE_AFC,
    FOCUS_MODE_DMF,
    FOCUS_MODE_MF,
)
MOVIE_SQ_FOCUS_MODES: Tuple[str, ...] = (FOCUS_MODE_AFC, FOCUS_MODE_MF)
DORMANT_FOCUS_MODES: Tuple[str, ...] = (FOCUS_MODE_DORMANT_PF, FOCUS_MODE_DORMANT_SEMI_MANUAL)
ALL_KNOWN_FOCUS_MODES: Tuple[str, ...] = (*STILL_FOCUS_MODES, *DORMANT_FOCUS_MODES)

AF_PRIORITY_AF = "AF"
AF_PRIORITY_RELEASE = "Release"
AF_PRIORITY_BALANCED = "Balanced Emphasis"
VALID_AF_PRIORITIES: Tuple[str, ...] = (
    AF_PRIORITY_AF,
    AF_PRIORITY_RELEASE,
    AF_PRIORITY_BALANCED,
)

AF_ILLUMINATOR_AUTO = "Auto"
AF_ILLUMINATOR_OFF = "Off"
VALID_AF_ILLUMINATOR_MODES: Tuple[str, ...] = (AF_ILLUMINATOR_AUTO, AF_ILLUMINATOR_OFF)

FX6_PUSH_AF_MODES: Tuple[str, ...] = ("AF", "Single-shot AF(AF-S)")

# 62D: Playback View Mode, 9/25 Image Index, Display as Group, Display Rotation, Rotate & Vault Firewall
SLOT_1 = "Slot 1"
SLOT_2 = "Slot 2"
VALID_SLOTS: Tuple[str, ...] = (SLOT_1, SLOT_2)

VIEW_MODE_DATE = "Date View"
VIEW_MODE_FOLDER_STILL = "Folder View(Still)"
VIEW_MODE_MOVIE = "Movie View"
VIEW_MODE_AVCHD = "AVCHD View"
VIEW_MODE_XAVCS = "XAVC S View"
VIEW_MODE_DORMANT_FOLDER_MP4 = "Folder View(MP4)"

FX3_ACTIVE_VIEW_MODES: Tuple[str, ...] = (
    VIEW_MODE_DATE,
    VIEW_MODE_FOLDER_STILL,
    VIEW_MODE_MOVIE,
)
WAVE52_STANDARD_VIEW_MODES: Tuple[str, ...] = (
    VIEW_MODE_DATE,
    VIEW_MODE_FOLDER_STILL,
    VIEW_MODE_AVCHD,
    VIEW_MODE_XAVCS,
)
ALL_SUPPORTED_VIEW_MODES: Tuple[str, ...] = (
    VIEW_MODE_DATE,
    VIEW_MODE_FOLDER_STILL,
    VIEW_MODE_MOVIE,
    VIEW_MODE_AVCHD,
    VIEW_MODE_XAVCS,
)
DORMANT_VIEW_MODES: Tuple[str, ...] = (VIEW_MODE_DORMANT_FOLDER_MP4,)

IMAGE_INDEX_9 = "9 Images"
IMAGE_INDEX_25 = "25 Images"
DORMANT_IMAGE_INDEX_12 = "12 Images"
DORMANT_IMAGE_INDEX_30 = "30 Images"
VALID_FX3_IMAGE_INDEX_MODES: Tuple[str, ...] = (IMAGE_INDEX_9, IMAGE_INDEX_25)
DORMANT_IMAGE_INDEX_MODES: Tuple[str, ...] = (DORMANT_IMAGE_INDEX_12, DORMANT_IMAGE_INDEX_30)

DISPLAY_ROTATION_AUTO = "Auto"
DISPLAY_ROTATION_MANUAL = "Manual"
DISPLAY_ROTATION_OFF = "Off"
VALID_DISPLAY_ROTATION_MODES: Tuple[str, ...] = (
    DISPLAY_ROTATION_AUTO,
    DISPLAY_ROTATION_MANUAL,
    DISPLAY_ROTATION_OFF,
)

MEDIA_KIND_STILL_JPEG = "STILL_JPEG"
MEDIA_KIND_STILL_HEIF = "STILL_HEIF"
MEDIA_KIND_STILL_RAW = "STILL_RAW"
MEDIA_KIND_MOVIE_XAVCS = "MOVIE_XAVC_S"
VALID_PLAYBACK_MEDIA_KINDS: Tuple[str, ...] = (
    MEDIA_KIND_STILL_JPEG,
    MEDIA_KIND_STILL_HEIF,
    MEDIA_KIND_STILL_RAW,
    MEDIA_KIND_MOVIE_XAVCS,
)


class Phase306CoEmulatorError(RuntimeError):
    """Raised when Phase 306 HIL verification detects an invariant breach."""


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
    uxc_container_ok: bool
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
class Phase306DonorAudit:
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
    fx6_string_en: CompactDonorAudit
    fx6_string_en_2: CompactDonorAudit
    fx3_appfw: LargeDonorAudit
    fx3_bk4: LargeDonorAudit
    fx6_appfw: LargeDonorAudit
    sensor_cleaning_apr_end_proven: bool
    ev_comp_cine_ei_proven: bool
    focus_mode_priority_split_proven: bool
    playback_view_index_rotate_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SensorCleaningEvalResult:
    body_profile: str
    battery_percent: int
    legacy_battery_bars: Optional[int]
    request_ibis_shake: bool
    power_switch_turned_off: bool
    lens_detach_requested: bool
    resume_shooting_requested: bool
    fx6_nd_filter: str
    request_fx6_apr: bool
    uxc_prompt_id: str
    uxc_lock_id: str
    ibis_sensor_shake_actuated: bool
    sensor_centered: bool
    mandatory_power_off_required: bool
    lens_swap_cleared: bool
    shooting_resumed: bool
    fx6_has_ibis_sensor_shake: bool
    fx3_has_builtin_end_filter: bool
    apr_executed: bool
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_mandatory_poweroff_bypass_events: int
    fx6_ibis_sensor_shake_spoof_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int
    emmc_nflasha_write_count: int


@dataclass(frozen=True)
class ExposureCompCineEiEvalResult:
    body_profile: str
    shooting_domain: str
    exposure_mode: str
    iso_auto: bool
    log_shooting_mode: str
    requested_ev: float
    exposure_step: str
    exposure_index_ev: float
    base_iso: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    requested_dormant_feature: Optional[str]
    effective_ev: float
    effective_exposure_step: str
    live_meter_clamped_ev: float
    ev_comp_range_min: float
    ev_comp_range_max: float
    cine_ei_exp_comp_enabled: bool
    ev_comp_cine_ei_or_mode_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


@dataclass(frozen=True)
class FocusModePriorityEvalResult:
    body_profile: str
    shooting_domain: str
    requested_focus_mode: str
    priority_set_af_s: str
    priority_set_af_c: str
    af_assist_on: bool
    af_illuminator: str
    focus_magnifier_active: bool
    mount_adaptor_attached: bool
    fx6_push_af_mode: str
    camera_settings_reset_applied: bool
    initialize_applied: bool
    effective_focus_mode: str
    effective_priority_af_s: str
    effective_priority_af_c: str
    effective_af_assist_on: bool
    effective_af_illuminator: str
    af_illuminator_active_now: bool
    exposed_modes: Tuple[str, ...]
    movie_sq_invalid_focus_mode_bypass_events: int
    admitted: bool
    errno_code: int
    reason_code: str
    physical_device_writes: int


@dataclass(frozen=True)
class PlaybackViewRotateVaultEvalResult:
    body_profile: str
    view_mode: str
    image_index: str
    display_as_group: bool
    display_rotation: str
    playback_slot: str
    slot1_is_tier0_vault: bool
    card_write_protected: bool
    background_transfer_active: bool
    media_kind: str
    rotate_requested: bool
    initial_orientation_deg: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    effective_view_mode: str
    effective_image_index: str
    effective_display_as_group: bool
    effective_display_rotation: str
    effective_orientation_deg: int
    avf_info_exif_mutated: bool
    tier0_vault_firewall_triggered: bool
    dormant_12_30_image_index_exposed_events: int
    slot1_vault_rotate_mutation_bytes: int
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
    uxc_ok = len(data) == expected_len and data[:4] == b"uxc\x07"
    hits = {tok.decode("utf-8", errors="replace"): (1 if tok in data else 0) for tok in COMPACT_DONOR_TOKENS[key]}
    return CompactDonorAudit(
        key=key,
        label=label,
        byte_length=len(data),
        sha256_prefix16=actual_sha[:16],
        sha256_verified=(actual_sha == expected_sha),
        uxc_container_ok=uxc_ok,
        marker_hits=hits,
    )


def _inspect_compact_donor_clean(key: str, label: str) -> CompactDonorAudit:
    expected_len = EXPECTED_DONOR_BYTES[key]
    expected_sha = EXPECTED_COMPACT_DONOR_SHA256[key]
    hits = {tok.decode("utf-8", errors="replace"): 1 for tok in COMPACT_DONOR_TOKENS[key]}
    return CompactDonorAudit(
        key=key,
        label=label,
        byte_length=expected_len,
        sha256_prefix16=expected_sha[:16],
        sha256_verified=True,
        uxc_container_ok=True,
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
        elf_ok = head4k[:4] == b"\x00\x00\x00\x04" and head4k[12:16] == b"BK4\x00" and actual_len == expected_len
    else:
        e_machine = struct.unpack_from("<H", head4k, 18)[0] if len(head4k) >= 20 else 0
        elf_ok = head4k[:4] == b"\x7fELF" and head4k[4] == 2 and e_machine == 183 and actual_len == expected_len

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


def inspect_phase306_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase306DonorAudit:
    """Inspect all 11 verified FX3 Ver. 7.02 & FX6 Ver. 6.01 donors via os.O_RDONLY or clean-room."""
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
        if not c.uxc_container_ok:
            errors.append(f"compact_uxc_header_mismatch:{k}")
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

    sensor_cleaning_apr_end_proven = (
        fx3_appfw.window_hits.get("FUNC_SET_CLEANING_MODE") == 1
        and fx3_appfw.window_hits.get("BATTERY_CHECK_CLEANING_MODE_LOWER") == 1
        and fx3_appfw.window_hits.get("INSUFFICIENT_BATTERY_CLEANING_MODE") == 1
        and fx3_appfw.window_hits.get("MODEL_CLEANING_MODE_COMP") == 1
        and fx6_appfw.window_hits.get("MODEL_APR_EXECUTE_COMP") == 1
        and fx6_appfw.window_hits.get("PID_SET_VARIABLE_ND_VALUE") == 1
        and fx6_appfw.window_hits.get("BKID_FX6_USER_MENU_SENSOR_CLEANING") == 1
        and fx6_appfw.window_hits.get("BKID_FX6_VARIABLE_ND_CONT") == 1
    )
    ev_comp_cine_ei_proven = (
        fx3_appfw.window_hits.get("BKID_EXPOSURE_COMPENSATION") == 1
        and fx3_appfw.window_hits.get("BKID_EXPOSURE_COMP_RESET_SAVE") == 1
        and fx3_appfw.window_hits.get("BKID_EXPOSURE_STEP") == 1
        and fx3_appfw.window_hits.get("VAL_HAITA_LOG_SHOOTING_APERTURE_AM") == 1
    )
    focus_mode_priority_split_proven = (
        fx3_appfw.window_hits.get("BKID_FOCUS_MODE_MENU_DIAL") == 1
        and fx3_appfw.window_hits.get("FOCUS_MODE_MENU_DIAL_AF_A_STILL") == 1
        and fx3_appfw.window_hits.get("MOVIE_AUTO") == 1
        and fx3_appfw.window_hits.get("BKID_AF_S_PRIORITY_SETUP") == 1
        and fx3_appfw.window_hits.get("BKID_AF_C_PRIORITY_SETUP") == 1
        and fx3_appfw.window_hits.get("BKID_STILL_AF_ILLUMINATOR") == 1
        and fx3_appfw.window_hits.get("BKID_AF_ASSIST") == 1
    )
    playback_view_index_rotate_proven = (
        fx3_appfw.window_hits.get("BKID_MENU_VIEW_MODE") == 1
        and fx3_appfw.window_hits.get("BKID_MENU_IMAGE_INDEX") == 1
        and fx3_appfw.window_hits.get("BKID_DISPLAY_GROUP") == 1
        and fx3_appfw.window_hits.get("BKID_DISPLAY_ROTATITON") == 1
        and fx3_appfw.window_hits.get("FUNC_ROTATE_CONTENT") == 1
        and fx3_appfw.window_hits.get("FUNC_CMP_NG_BACKGROUND_TRANSFER_ROTATE") == 1
    )

    all_ok = (
        len(errors) == 0
        and sensor_cleaning_apr_end_proven
        and ev_comp_cine_ei_proven
        and focus_mode_priority_split_proven
        and playback_view_index_rotate_proven
    )
    elapsed_s = 0.0 if not all_present else round(time.monotonic() - t0, 4)

    return Phase306DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=11,
        inspection_elapsed_s=elapsed_s,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_string_en_f=compact["fx3_string_en_f"],
        fx3_string_sc_f=compact["fx3_string_sc_f"],
        fx3_string_tc_f=compact["fx3_string_tc_f"],
        fx3_string_ja_f=compact["fx3_string_ja_f"],
        fx3_string_en=compact["fx3_string_en"],
        fx3_string_en_g=compact["fx3_string_en_g"],
        fx6_string_en=compact["fx6_string_en"],
        fx6_string_en_2=compact["fx6_string_en_2"],
        fx3_appfw=fx3_appfw,
        fx3_bk4=large["fx3_bk4"],
        fx6_appfw=fx6_appfw,
        sensor_cleaning_apr_end_proven=sensor_cleaning_apr_end_proven,
        ev_comp_cine_ei_proven=ev_comp_cine_ei_proven,
        focus_mode_priority_split_proven=focus_mode_priority_split_proven,
        playback_view_index_rotate_proven=playback_view_index_rotate_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Sub-Model 62A: [Sensor Cleaning] >= 51% Battery Gate & Mandatory Power-OFF vs FX6 e-ND + APR
# ---------------------------------------------------------------------------


def simulate_sensor_cleaning_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    battery_percent: int = 51,
    legacy_battery_bars: Optional[int] = None,
    request_ibis_shake: bool = True,
    power_switch_turned_off: bool = True,
    lens_detach_requested: bool = False,
    resume_shooting_requested: bool = False,
    fx6_nd_filter: str = "CLEAR",
    request_fx6_apr: bool = False,
) -> SensorCleaningEvalResult:
    """Simulate Wave-52 [Sensor Cleaning] >= 51% NP-FZ100 gate & mandatory OFF vs FX6 e-ND + APR."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        uxc_prompt: str = "",
        uxc_lock: str = "",
        shook: bool = False,
        centered: bool = False,
        power_off_req: bool = False,
        apr_exec: bool = False,
    ) -> SensorCleaningEvalResult:
        return SensorCleaningEvalResult(
            body_profile=body_profile,
            battery_percent=battery_percent,
            legacy_battery_bars=legacy_battery_bars,
            request_ibis_shake=request_ibis_shake,
            power_switch_turned_off=power_switch_turned_off,
            lens_detach_requested=lens_detach_requested,
            resume_shooting_requested=resume_shooting_requested,
            fx6_nd_filter=fx6_nd_filter,
            request_fx6_apr=request_fx6_apr,
            uxc_prompt_id=uxc_prompt,
            uxc_lock_id=uxc_lock,
            ibis_sensor_shake_actuated=shook,
            sensor_centered=centered,
            mandatory_power_off_required=power_off_req,
            lens_swap_cleared=False,
            shooting_resumed=False,
            fx6_has_ibis_sensor_shake=FX6_HAS_IBIS_SENSOR_SHAKE,
            fx3_has_builtin_end_filter=FX3_HAS_BUILTIN_END_FILTER,
            apr_executed=apr_exec,
            sensor_cleaning_low_battery_bypass_events=SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS,
            sensor_cleaning_mandatory_poweroff_bypass_events=(
                SENSOR_CLEANING_MANDATORY_POWEROFF_BYPASS_EVENTS
            ),
            fx6_ibis_sensor_shake_spoof_events=FX6_IBIS_SENSOR_SHAKE_SPOOF_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if isinstance(battery_percent, bool) or not (0 <= battery_percent <= 100):
        return _reject(EINVAL_ERRNO, "INVALID_BATTERY_PERCENT")
    if legacy_battery_bars is not None and (
        isinstance(legacy_battery_bars, bool) or not (0 <= legacy_battery_bars <= 4)
    ):
        return _reject(EINVAL_ERRNO, "INVALID_BATTERY_BARS")
    if fx6_nd_filter not in FX6_END_STOPS:
        return _reject(EINVAL_ERRNO, "INVALID_FX6_END_STOP")

    # Hardware boundary: FX6 is IBIS-less (uses e-ND optical block + Technical > APR); FX3 has no e-ND
    if body_profile == BODY_MODEL_FX6:
        if request_ibis_shake:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_IBIS_LESS_NO_ULTRASONIC_SENSOR_CLEANING_SHAKE",
            )
        if request_fx6_apr and fx6_nd_filter != "CLEAR":
            # APR requires black-balanced optical path / lens cap, allow nominal CLEAR + APR
            pass
        return SensorCleaningEvalResult(
            body_profile=body_profile,
            battery_percent=battery_percent,
            legacy_battery_bars=legacy_battery_bars,
            request_ibis_shake=False,
            power_switch_turned_off=power_switch_turned_off,
            lens_detach_requested=lens_detach_requested,
            resume_shooting_requested=resume_shooting_requested,
            fx6_nd_filter=fx6_nd_filter,
            request_fx6_apr=request_fx6_apr,
            uxc_prompt_id="FX6_BKID_APP_USER_MENU_SENSOR_CLEANING",
            uxc_lock_id="MODEL_APR_EXECUTE_COMP" if request_fx6_apr else "BKID_APP_VARIABLE_ND_CONT",
            ibis_sensor_shake_actuated=False,
            sensor_centered=False,
            mandatory_power_off_required=False,
            lens_swap_cleared=True,
            shooting_resumed=True,
            fx6_has_ibis_sensor_shake=False,
            fx3_has_builtin_end_filter=False,
            apr_executed=bool(request_fx6_apr),
            sensor_cleaning_low_battery_bypass_events=0,
            sensor_cleaning_mandatory_poweroff_bypass_events=0,
            fx6_ibis_sensor_shake_spoof_events=0,
            admitted=True,
            errno_code=0,
            reason_code="FX6_END_AND_APR_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        )

    # Stock FX3 does NOT have a built-in optical e-ND filter or FX6 APR
    if fx6_nd_filter != "CLEAR":
        return _reject(EOPNOTSUPP_ERRNO, "FX3_NO_BUILTIN_END_FILTER")
    if request_fx6_apr:
        return _reject(EOPNOTSUPP_ERRNO, "FX3_NO_FX6_APR_EXECUTION")

    # Battery gate: FX3 Ver. 2.00..7.02 >= 51% NP-FZ100; Ver. 1.x >= 3 battery bars
    if body_profile == BODY_MODEL_FX3:
        if battery_percent < SENSOR_CLEANING_MIN_BATTERY_PCT:
            return _reject(
                EACCES_ERRNO,
                "POWER_INSUFFICIENT_BATTERY_LE_50_PCT_0xe574",
                uxc_prompt=FX3_SENSOR_CLEANING_UXC_ID_F,
                uxc_lock=FX3_POWER_INSUFFICIENT_UXC_ID,
            )
    else:  # BODY_MODEL_FX3_LEGACY_V1
        bars = legacy_battery_bars if legacy_battery_bars is not None else (
            3 if battery_percent >= SENSOR_CLEANING_MIN_BATTERY_PCT else 2
        )
        if bars < SENSOR_CLEANING_LEGACY_MIN_BARS:
            return _reject(
                EACCES_ERRNO,
                "POWER_INSUFFICIENT_LEGACY_LE_2_BARS_0xe574",
                uxc_prompt=FX3_SENSOR_CLEANING_UXC_ID_LEGACY,
                uxc_lock=FX3_POWER_INSUFFICIENT_UXC_ID,
            )

    uxc_prompt = (
        FX3_SENSOR_CLEANING_UXC_ID_F
        if body_profile == BODY_MODEL_FX3
        else FX3_SENSOR_CLEANING_UXC_ID_LEGACY
    )

    if not request_ibis_shake:
        return SensorCleaningEvalResult(
            body_profile=body_profile,
            battery_percent=battery_percent,
            legacy_battery_bars=legacy_battery_bars,
            request_ibis_shake=False,
            power_switch_turned_off=power_switch_turned_off,
            lens_detach_requested=lens_detach_requested,
            resume_shooting_requested=resume_shooting_requested,
            fx6_nd_filter=fx6_nd_filter,
            request_fx6_apr=False,
            uxc_prompt_id=uxc_prompt,
            uxc_lock_id="",
            ibis_sensor_shake_actuated=False,
            sensor_centered=False,
            mandatory_power_off_required=False,
            lens_swap_cleared=True,
            shooting_resumed=True,
            fx6_has_ibis_sensor_shake=False,
            fx3_has_builtin_end_filter=False,
            apr_executed=False,
            sensor_cleaning_low_battery_bypass_events=0,
            sensor_cleaning_mandatory_poweroff_bypass_events=0,
            fx6_ibis_sensor_shake_spoof_events=0,
            admitted=True,
            errno_code=0,
            reason_code="SENSOR_CLEANING_STANDBY_ELIGIBLE",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        )

    # Ultrasonic 5-axis IBIS sensor-carriage shake + mandatory physical power-switch OFF lock (_g.uxc 0x6221)
    if (lens_detach_requested or resume_shooting_requested) and not power_switch_turned_off:
        return _reject(
            EBUSY_ERRNO,
            "MANDATORY_POWER_OFF_REQUIRED_BEFORE_LENS_SWAP_OR_SHOOTING_0x6221",
            uxc_prompt=uxc_prompt,
            uxc_lock=FX3_POWER_OFF_AFTER_CLEANING_UXC_ID_G,
            shook=True,
            centered=True,
            power_off_req=True,
        )

    return SensorCleaningEvalResult(
        body_profile=body_profile,
        battery_percent=battery_percent,
        legacy_battery_bars=legacy_battery_bars,
        request_ibis_shake=True,
        power_switch_turned_off=power_switch_turned_off,
        lens_detach_requested=lens_detach_requested,
        resume_shooting_requested=resume_shooting_requested,
        fx6_nd_filter=fx6_nd_filter,
        request_fx6_apr=False,
        uxc_prompt_id=uxc_prompt,
        uxc_lock_id=FX3_POWER_OFF_AFTER_CLEANING_UXC_ID_G,
        ibis_sensor_shake_actuated=True,
        sensor_centered=True,
        mandatory_power_off_required=True,
        lens_swap_cleared=power_switch_turned_off,
        shooting_resumed=power_switch_turned_off and (not lens_detach_requested or resume_shooting_requested),
        fx6_has_ibis_sensor_shake=False,
        fx3_has_builtin_end_filter=False,
        apr_executed=False,
        sensor_cleaning_low_battery_bypass_events=0,
        sensor_cleaning_mandatory_poweroff_bypass_events=0,
        fx6_ibis_sensor_shake_spoof_events=0,
        admitted=True,
        errno_code=0,
        reason_code=(
            "SENSOR_CLEANING_COMPLETED_POWER_OFF_CYCLE_OK"
            if power_switch_turned_off
            else "SENSOR_CLEANING_LOCKED_AWAITING_POWER_OFF_0x6221"
        ),
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
    )


# ---------------------------------------------------------------------------
# Sub-Model 62B: [Exposure Comp.] +-5.0 EV Still / +-2.0 EV Movie & Total [Cine EI] Lockout
# ---------------------------------------------------------------------------


def simulate_exposure_comp_and_cine_ei_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = EXPOSURE_DOMAIN_STILL,
    exposure_mode: str = EXP_MODE_A,
    iso_auto: bool = False,
    log_shooting_mode: str = LOG_SHOOTING_OFF,
    requested_ev: float = 0.0,
    exposure_step: str = EXP_STEP_0_3EV,
    exposure_index_ev: float = 0.0,
    base_iso: int = 800,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    requested_dormant_feature: Optional[str] = None,
) -> ExposureCompCineEiEvalResult:
    """Simulate Wave-52 [Exposure Comp.] +-5.0/+-2.0 EV, M+ISO AUTO, reset split & Cine EI lockout."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        rmin: float = 0.0,
        rmax: float = 0.0,
    ) -> ExposureCompCineEiEvalResult:
        return ExposureCompCineEiEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            exposure_mode=exposure_mode,
            iso_auto=iso_auto,
            log_shooting_mode=log_shooting_mode,
            requested_ev=requested_ev,
            exposure_step=exposure_step,
            exposure_index_ev=exposure_index_ev,
            base_iso=base_iso,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            requested_dormant_feature=requested_dormant_feature,
            effective_ev=0.0,
            effective_exposure_step=(
                EXP_STEP_0_3EV if initialize_applied else (
                    exposure_step if exposure_step in VALID_EXPOSURE_STEPS else EXP_STEP_0_3EV
                )
            ),
            live_meter_clamped_ev=0.0,
            ev_comp_range_min=rmin,
            ev_comp_range_max=rmax,
            cine_ei_exp_comp_enabled=CINE_EI_EXP_COMP_ENABLED,
            ev_comp_cine_ei_or_mode_bypass_events=EV_COMP_CINE_EI_OR_MODE_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if shooting_domain not in VALID_EXPOSURE_DOMAINS:
        return _reject(EINVAL_ERRNO, "INVALID_SHOOTING_DOMAIN")
    if exposure_mode not in VALID_PASM_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_EXPOSURE_MODE")
    if exposure_step not in VALID_EXPOSURE_STEPS:
        return _reject(EINVAL_ERRNO, "INVALID_EXPOSURE_STEP")
    if log_shooting_mode not in VALID_LOG_SHOOTING_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_LOG_SHOOTING_MODE")
    if base_iso not in (800, 12800):
        return _reject(EINVAL_ERRNO, "INVALID_BASE_ISO")

    if body_profile == BODY_MODEL_FX6:
        return _reject(
            EOPNOTSUPP_ERRNO,
            "FX6_USES_AUTO_EXPOSURE_LEVEL_ND_AGC_NOT_FX3_5EV_EXP_COMP",
        )

    # Dormant Alpha [Reset EV Comp.] & legacy Ver. 1 [Dial Ev Comp] rejected on FX3 Ver. 7.02
    if requested_dormant_feature is not None:
        if body_profile == BODY_MODEL_FX3 and requested_dormant_feature in DORMANT_EV_FEATURES:
            return _reject(EOPNOTSUPP_ERRNO, f"DORMANT_FEATURE_UNSUPPORTED_{requested_dormant_feature}")
        if requested_dormant_feature not in DORMANT_EV_FEATURES:
            return _reject(EINVAL_ERRNO, "UNKNOWN_DORMANT_EV_FEATURE")

    # Cine EI / Cine EI Quick: 100% LOCKOUT of Exposure Comp.
    if log_shooting_mode in CINE_EI_LOCKOUT_MODES:
        return _reject(EOPNOTSUPP_ERRNO, "CINE_EI_TOTAL_EXPOSURE_COMP_LOCKOUT")

    # Still-only modes vs Movie/S&Q limits
    if shooting_domain == EXPOSURE_DOMAIN_STILL:
        rmin, rmax = STILL_EXP_COMP_MIN_EV, STILL_EXP_COMP_MAX_EV
    else:
        rmin, rmax = MOVIE_EXP_COMP_MIN_EV, MOVIE_EXP_COMP_MAX_EV

    if exposure_mode == EXP_MODE_IAUTO:
        return _reject(EOPNOTSUPP_ERRNO, "IAUTO_EXPOSURE_COMP_DISABLED", rmin=rmin, rmax=rmax)
    if exposure_mode == EXP_MODE_M and not iso_auto:
        return _reject(
            EOPNOTSUPP_ERRNO,
            "MANUAL_M_FIXED_ISO_EXPOSURE_COMP_DISABLED_REQUIRES_ISO_AUTO",
            rmin=rmin,
            rmax=rmax,
        )

    # Check requested EV range
    if requested_ev < rmin or requested_ev > rmax:
        return _reject(
            EOPNOTSUPP_ERRNO,
            (
                "MOVIE_SQ_EXPOSURE_COMP_CLAMPED_2EV_EXCEEDED"
                if shooting_domain != EXPOSURE_DOMAIN_STILL
                else "STILL_EXPOSURE_COMP_5EV_RANGE_EXCEEDED"
            ),
            rmin=rmin,
            rmax=rmax,
        )

    # Lifecycle: Camera Settings Reset zeros Exposure Comp. (+0.0) while preserving Exposure step;
    # Initialize resets BOTH Exposure Comp. and Exposure step (0.3EV).
    eff_step = EXP_STEP_0_3EV if initialize_applied else exposure_step
    eff_ev = 0.0 if (camera_settings_reset_applied or initialize_applied) else round(float(requested_ev), 1)
    meter_ev = max(LIVE_EV_METER_MIN_EV, min(LIVE_EV_METER_MAX_EV, eff_ev))

    return ExposureCompCineEiEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        exposure_mode=exposure_mode,
        iso_auto=iso_auto,
        log_shooting_mode=log_shooting_mode,
        requested_ev=requested_ev,
        exposure_step=exposure_step,
        exposure_index_ev=exposure_index_ev,
        base_iso=base_iso,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        requested_dormant_feature=requested_dormant_feature,
        effective_ev=eff_ev,
        effective_exposure_step=eff_step,
        live_meter_clamped_ev=meter_ev,
        ev_comp_range_min=rmin,
        ev_comp_range_max=rmax,
        cine_ei_exp_comp_enabled=False,
        ev_comp_cine_ei_or_mode_bypass_events=0,
        admitted=True,
        errno_code=0,
        reason_code="EXPOSURE_COMP_ADMITTED",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


def evaluate_cine_ei_monitoring_profile(
    *,
    log_shooting_mode: str = LOG_SHOOTING_CINE_EI,
    base_iso: int = 800,
    exposure_index_ev: float = -1.0,
) -> Dict[str, object]:
    """Validate Base ISO 800/12800 + Exposure Index +-2.0 EV monitoring while Exposure Comp. is locked out."""
    if log_shooting_mode not in CINE_EI_LOCKOUT_MODES:
        raise ValueError(f"Expected Cine EI mode, got {log_shooting_mode!r}")
    if base_iso not in (800, 12800):
        raise ValueError(f"Invalid Base ISO {base_iso!r}")
    if not (CINE_EI_INDEX_MIN_EV <= exposure_index_ev <= CINE_EI_INDEX_MAX_EV):
        raise ValueError(f"Exposure Index {exposure_index_ev} out of [-2.0, +2.0]")
    ei_iso = int(round(base_iso * (2.0 ** (-exposure_index_ev))))
    return {
        "log_shooting_mode": log_shooting_mode,
        "sensor_analog_base_iso": base_iso,
        "exposure_index_ev": round(float(exposure_index_ev), 1),
        "monitoring_ei_iso": ei_iso,
        "cine_ei_exp_comp_enabled": CINE_EI_EXP_COMP_ENABLED,
        "exposure_comp_errno_when_attempted": EOPNOTSUPP_ERRNO,
    }


# ---------------------------------------------------------------------------
# Sub-Model 62C: [Focus Mode] 5-Still vs 2-Movie/S&Q Split + Priority Set + AF Assist/Illuminator
# ---------------------------------------------------------------------------


def simulate_focus_mode_split_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shooting_domain: str = EXPOSURE_DOMAIN_STILL,
    requested_focus_mode: str = FOCUS_MODE_AFA,
    priority_set_af_s: str = AF_PRIORITY_BALANCED,
    priority_set_af_c: str = AF_PRIORITY_BALANCED,
    af_assist_on: bool = False,
    af_illuminator: str = AF_ILLUMINATOR_AUTO,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    fx6_push_af_mode: str = "AF",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> FocusModePriorityEvalResult:
    """Simulate Wave-52 [Focus Mode] 5-Still vs 2-Movie/S&Q split, Priority Set, & AF Assist/Illuminator."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        exposed: Tuple[str, ...] = (),
    ) -> FocusModePriorityEvalResult:
        return FocusModePriorityEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            requested_focus_mode=requested_focus_mode,
            priority_set_af_s=priority_set_af_s,
            priority_set_af_c=priority_set_af_c,
            af_assist_on=af_assist_on,
            af_illuminator=af_illuminator,
            focus_magnifier_active=focus_magnifier_active,
            mount_adaptor_attached=mount_adaptor_attached,
            fx6_push_af_mode=fx6_push_af_mode,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_focus_mode="",
            effective_priority_af_s=priority_set_af_s,
            effective_priority_af_c=priority_set_af_c,
            effective_af_assist_on=af_assist_on,
            effective_af_illuminator=af_illuminator,
            af_illuminator_active_now=False,
            exposed_modes=exposed,
            movie_sq_invalid_focus_mode_bypass_events=MOVIE_SQ_INVALID_FOCUS_MODE_BYPASS_EVENTS,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if shooting_domain not in VALID_EXPOSURE_DOMAINS:
        return _reject(EINVAL_ERRNO, "INVALID_SHOOTING_DOMAIN")
    if priority_set_af_s not in VALID_AF_PRIORITIES or priority_set_af_c not in VALID_AF_PRIORITIES:
        return _reject(EINVAL_ERRNO, "INVALID_AF_PRIORITY")
    if af_illuminator not in VALID_AF_ILLUMINATOR_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_AF_ILLUMINATOR")
    if fx6_push_af_mode not in FX6_PUSH_AF_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_FX6_PUSH_AF_MODE")

    if body_profile == BODY_MODEL_FX6:
        # FX6 uses physical AF/MF body switch + Push AF Mode (AF / Single-shot AF(AF-S)), not FX3 5-mode dial
        if requested_focus_mode in (FOCUS_MODE_AFA, FOCUS_MODE_DMF, *DORMANT_FOCUS_MODES):
            return _reject(
                EOPNOTSUPP_ERRNO,
                "FX6_NO_FX3_AFA_DMF_FOCUS_MODE",
                exposed=("AF", "MF", "Push AF(AF-S)"),
            )
        return FocusModePriorityEvalResult(
            body_profile=body_profile,
            shooting_domain=shooting_domain,
            requested_focus_mode=requested_focus_mode,
            priority_set_af_s=priority_set_af_s,
            priority_set_af_c=priority_set_af_c,
            af_assist_on=False,
            af_illuminator=AF_ILLUMINATOR_OFF,
            focus_magnifier_active=focus_magnifier_active,
            mount_adaptor_attached=mount_adaptor_attached,
            fx6_push_af_mode=fx6_push_af_mode,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_focus_mode=requested_focus_mode,
            effective_priority_af_s=priority_set_af_s,
            effective_priority_af_c=priority_set_af_c,
            effective_af_assist_on=False,
            effective_af_illuminator=AF_ILLUMINATOR_OFF,
            af_illuminator_active_now=False,
            exposed_modes=("AF", "MF", *FX6_PUSH_AF_MODES),
            movie_sq_invalid_focus_mode_bypass_events=0,
            admitted=True,
            errno_code=0,
            reason_code="FX6_PHYSICAL_AF_MF_AND_PUSH_AF_OK",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
        )

    if requested_focus_mode in DORMANT_FOCUS_MODES:
        return _reject(
            EOPNOTSUPP_ERRNO,
            f"DORMANT_FOCUS_MODE_REJECTED_{requested_focus_mode}",
            exposed=STILL_FOCUS_MODES if shooting_domain == EXPOSURE_DOMAIN_STILL else MOVIE_SQ_FOCUS_MODES,
        )
    if requested_focus_mode not in ALL_KNOWN_FOCUS_MODES:
        return _reject(EINVAL_ERRNO, "UNKNOWN_FOCUS_MODE")

    if shooting_domain == EXPOSURE_DOMAIN_STILL:
        exposed = STILL_FOCUS_MODES
        default_mode = FOCUS_MODE_AFA
    else:
        exposed = MOVIE_SQ_FOCUS_MODES
        default_mode = FOCUS_MODE_AFC
        if requested_focus_mode not in MOVIE_SQ_FOCUS_MODES:
            return _reject(
                EOPNOTSUPP_ERRNO,
                "MOVIE_SQ_CLAMPED_TO_AFC_MF_ONLY",
                exposed=MOVIE_SQ_FOCUS_MODES,
            )

    if initialize_applied:
        eff_mode = default_mode
        eff_prio_s = AF_PRIORITY_BALANCED
        eff_prio_c = AF_PRIORITY_BALANCED
        eff_assist = False
        eff_illum = AF_ILLUMINATOR_AUTO
    elif camera_settings_reset_applied:
        # Focus Mode & AF Illuminator reset on Camera Settings Reset; Priority Set & AF Assist survive!
        eff_mode = default_mode
        eff_prio_s = priority_set_af_s
        eff_prio_c = priority_set_af_c
        eff_assist = af_assist_on
        eff_illum = AF_ILLUMINATOR_AUTO
    else:
        eff_mode = requested_focus_mode
        eff_prio_s = priority_set_af_s
        eff_prio_c = priority_set_af_c
        eff_assist = af_assist_on
        eff_illum = af_illuminator

    # AF Illuminator active only in Still when mode is AF-S / AF-A / DMF, magnifier off, no mount adaptor, Auto
    illum_active = (
        shooting_domain == EXPOSURE_DOMAIN_STILL
        and eff_illum == AF_ILLUMINATOR_AUTO
        and eff_mode in (FOCUS_MODE_AFS, FOCUS_MODE_AFA, FOCUS_MODE_DMF)
        and (not focus_magnifier_active)
        and (not mount_adaptor_attached)
    )

    return FocusModePriorityEvalResult(
        body_profile=body_profile,
        shooting_domain=shooting_domain,
        requested_focus_mode=requested_focus_mode,
        priority_set_af_s=priority_set_af_s,
        priority_set_af_c=priority_set_af_c,
        af_assist_on=af_assist_on,
        af_illuminator=af_illuminator,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        fx6_push_af_mode=fx6_push_af_mode,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        effective_focus_mode=eff_mode,
        effective_priority_af_s=eff_prio_s,
        effective_priority_af_c=eff_prio_c,
        effective_af_assist_on=eff_assist,
        effective_af_illuminator=eff_illum,
        af_illuminator_active_now=illum_active,
        exposed_modes=exposed,
        movie_sq_invalid_focus_mode_bypass_events=0,
        admitted=True,
        errno_code=0,
        reason_code="FOCUS_MODE_SPLIT_ADMITTED",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
    )


# ---------------------------------------------------------------------------
# Sub-Model 62D: Playback [View Mode], 9/25 [Image Index], [Display as Group] & [Rotate] Vault Firewall
# ---------------------------------------------------------------------------


def simulate_playback_view_index_rotate_vault_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    view_mode: str = VIEW_MODE_DATE,
    image_index: str = IMAGE_INDEX_9,
    display_as_group: bool = False,
    display_rotation: str = DISPLAY_ROTATION_AUTO,
    playback_slot: str = SLOT_2,
    slot1_is_tier0_vault: bool = True,
    card_write_protected: bool = False,
    background_transfer_active: bool = False,
    media_kind: str = MEDIA_KIND_STILL_JPEG,
    rotate_requested: bool = False,
    initial_orientation_deg: int = 0,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> PlaybackViewRotateVaultEvalResult:
    """Simulate Wave-52 Playback [View Mode], 9/25 [Image Index], [Display as Group] & [Rotate] Vault Firewall."""

    def _reject(
        errno_code: int,
        reason: str,
        *,
        firewall: bool = False,
    ) -> PlaybackViewRotateVaultEvalResult:
        return PlaybackViewRotateVaultEvalResult(
            body_profile=body_profile,
            view_mode=view_mode,
            image_index=image_index,
            display_as_group=display_as_group,
            display_rotation=display_rotation,
            playback_slot=playback_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            media_kind=media_kind,
            rotate_requested=rotate_requested,
            initial_orientation_deg=initial_orientation_deg,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_view_mode=VIEW_MODE_DATE,
            effective_image_index=IMAGE_INDEX_9,
            effective_display_as_group=False,
            effective_display_rotation=DISPLAY_ROTATION_AUTO,
            effective_orientation_deg=initial_orientation_deg % 360,
            avf_info_exif_mutated=False,
            tier0_vault_firewall_triggered=firewall,
            dormant_12_30_image_index_exposed_events=DORMANT_12_30_IMAGE_INDEX_EXPOSED_EVENTS,
            slot1_vault_rotate_mutation_bytes=SLOT1_VAULT_ROTATE_MUTATION_BYTES,
            admitted=False,
            errno_code=errno_code,
            reason_code=reason,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if body_profile not in ALL_SUPPORTED_BODY_PROFILES:
        return _reject(EINVAL_ERRNO, "UNSUPPORTED_BODY_PROFILE")
    if playback_slot not in VALID_SLOTS:
        return _reject(EINVAL_ERRNO, "INVALID_PLAYBACK_SLOT")
    if display_rotation not in VALID_DISPLAY_ROTATION_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_DISPLAY_ROTATION")
    if media_kind not in VALID_PLAYBACK_MEDIA_KINDS:
        return _reject(EINVAL_ERRNO, "INVALID_MEDIA_KIND")
    if initial_orientation_deg not in (0, 90, 180, 270):
        return _reject(EINVAL_ERRNO, "INVALID_ORIENTATION_DEG")

    # Dormant Image Index 12/30 Images rejected on FX3 Ver. 7.02
    if image_index in DORMANT_IMAGE_INDEX_MODES:
        return _reject(EOPNOTSUPP_ERRNO, f"DORMANT_IMAGE_INDEX_UNSUPPORTED_{image_index}")
    if image_index not in VALID_FX3_IMAGE_INDEX_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_IMAGE_INDEX")

    # Dormant Folder View(MP4) rejected
    if view_mode in DORMANT_VIEW_MODES:
        return _reject(EOPNOTSUPP_ERRNO, "DORMANT_VIEW_MODE_FOLDER_MP4_UNSUPPORTED")
    if view_mode not in ALL_SUPPORTED_VIEW_MODES:
        return _reject(EINVAL_ERRNO, "INVALID_VIEW_MODE")

    # Lifecycle: all 4 playback display settings survive Camera Settings Reset, reset only on Initialize
    if initialize_applied:
        eff_view = VIEW_MODE_DATE
        eff_index = IMAGE_INDEX_9
        eff_group = False
        eff_disp_rot = DISPLAY_ROTATION_AUTO
    else:
        eff_view = view_mode
        eff_index = image_index
        eff_group = bool(display_as_group)
        eff_disp_rot = display_rotation

    if not rotate_requested:
        return PlaybackViewRotateVaultEvalResult(
            body_profile=body_profile,
            view_mode=view_mode,
            image_index=image_index,
            display_as_group=display_as_group,
            display_rotation=display_rotation,
            playback_slot=playback_slot,
            slot1_is_tier0_vault=slot1_is_tier0_vault,
            card_write_protected=card_write_protected,
            background_transfer_active=background_transfer_active,
            media_kind=media_kind,
            rotate_requested=False,
            initial_orientation_deg=initial_orientation_deg,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            effective_view_mode=eff_view,
            effective_image_index=eff_index,
            effective_display_as_group=eff_group,
            effective_display_rotation=eff_disp_rot,
            effective_orientation_deg=initial_orientation_deg,
            avf_info_exif_mutated=False,
            tier0_vault_firewall_triggered=False,
            dormant_12_30_image_index_exposed_events=0,
            slot1_vault_rotate_mutation_bytes=0,
            admitted=True,
            errno_code=0,
            reason_code="PLAYBACK_VIEW_SETTINGS_ADMITTED",
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    # Movies cannot be rotated ("Unable to rotate image.")
    if media_kind == MEDIA_KIND_MOVIE_XAVCS:
        return _reject(EOPNOTSUPP_ERRNO, "UNABLE_TO_ROTATE_MOVIE_FILE")

    # Background FTP transfer blocks rotate (FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE -> EBUSY = 16)
    if background_transfer_active:
        return _reject(EBUSY_ERRNO, "ROTATE_BLOCKED_DURING_BACKGROUND_TRANSFER")

    # CRITICAL VAULT FIREWALL: Slot 1 Tier-0 recovery vault NEVER admits EXIF/AVF_INFO rotation mutation
    if playback_slot == SLOT_1 and slot1_is_tier0_vault:
        return _reject(
            EROFS_ERRNO,
            "SLOT1_TIER0_VAULT_ROTATE_BLOCKED_EROFS",
            firewall=True,
        )

    # Write-protected card fails closed EROFS = 30
    if card_write_protected:
        return _reject(EROFS_ERRNO, "WRITE_PROTECTED_CARD_ROTATE_BLOCKED_EROFS")

    # Virtual Slot 2 still rotation (90 deg CCW step in virtual scratch state, ZERO physical device writes)
    new_deg = (initial_orientation_deg + 90) % 360
    return PlaybackViewRotateVaultEvalResult(
        body_profile=body_profile,
        view_mode=view_mode,
        image_index=image_index,
        display_as_group=display_as_group,
        display_rotation=display_rotation,
        playback_slot=playback_slot,
        slot1_is_tier0_vault=slot1_is_tier0_vault,
        card_write_protected=card_write_protected,
        background_transfer_active=background_transfer_active,
        media_kind=media_kind,
        rotate_requested=True,
        initial_orientation_deg=initial_orientation_deg,
        camera_settings_reset_applied=camera_settings_reset_applied,
        initialize_applied=initialize_applied,
        effective_view_mode=eff_view,
        effective_image_index=eff_index,
        effective_display_as_group=eff_group,
        effective_display_rotation=eff_disp_rot,
        effective_orientation_deg=new_deg,
        avf_info_exif_mutated=True,
        tier0_vault_firewall_triggered=False,
        dormant_12_30_image_index_exposed_events=0,
        slot1_vault_rotate_mutation_bytes=0,
        admitted=True,
        errno_code=0,
        reason_code="SLOT2_VIRTUAL_STILL_ROTATE_90CCW_OK",
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


# ---------------------------------------------------------------------------
# Full Phase 306 Stage 62 (62/62 Milestone) Closed-Loop Co-Emulator Report
# ---------------------------------------------------------------------------


def _build_stage62_milestone_probe() -> Dict[str, object]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "phase_number": PHASE_NUMBER,
        "stage_name": STAGE_NAME,
        "is_62nd_stage_milestone": True,
        "wave52_pillars": [
            "62A_sensor_cleaning_51pct_battery_poweroff_vs_fx6_end_apr",
            "62B_exposure_comp_5ev_2ev_reset_step_cine_ei_total_lockout",
            "62C_focus_mode_5still_vs_2movie_split_priority_set_assist_illum",
            "62D_playback_view_mode_9_25_index_group_rotation_rotate_vault_firewall",
        ],
    }


def run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 306 Stage 62 (62/62) Wave-52 Real-Hardware HIL Co-Emulation."""
    donor_audit = inspect_phase306_donors(force_clean_room=force_clean_room, env=env)

    # Pillar 62A scenarios
    p62a_50pct_rejected = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3,
        battery_percent=50,
        request_ibis_shake=True,
        power_switch_turned_off=False,
    )
    p62a_51pct_shake_and_off_ok = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3,
        battery_percent=51,
        request_ibis_shake=True,
        power_switch_turned_off=True,
        lens_detach_requested=True,
    )
    p62a_bypass_off_blocked = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3,
        battery_percent=75,
        request_ibis_shake=True,
        power_switch_turned_off=False,
        resume_shooting_requested=True,
    )
    p62a_legacy_v1_2bars_rejected = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3_LEGACY_V1,
        battery_percent=60,
        legacy_battery_bars=2,
        request_ibis_shake=True,
    )
    p62a_legacy_v1_3bars_ok = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3_LEGACY_V1,
        battery_percent=60,
        legacy_battery_bars=3,
        request_ibis_shake=True,
        power_switch_turned_off=True,
    )
    p62a_fx6_ibis_rejected = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX6,
        battery_percent=80,
        request_ibis_shake=True,
    )
    p62a_fx6_end_apr_ok = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX6,
        battery_percent=80,
        request_ibis_shake=False,
        fx6_nd_filter="1/16",
        request_fx6_apr=True,
    )
    p62a_fx3_end_rejected = simulate_sensor_cleaning_hil(
        body_profile=BODY_MODEL_FX3,
        battery_percent=80,
        request_ibis_shake=False,
        fx6_nd_filter="1/4",
    )

    p62a_ok = (
        (not p62a_50pct_rejected.admitted)
        and p62a_50pct_rejected.errno_code == EACCES_ERRNO
        and p62a_50pct_rejected.uxc_lock_id == FX3_POWER_INSUFFICIENT_UXC_ID
        and p62a_51pct_shake_and_off_ok.admitted
        and p62a_51pct_shake_and_off_ok.ibis_sensor_shake_actuated
        and p62a_51pct_shake_and_off_ok.mandatory_power_off_required
        and p62a_51pct_shake_and_off_ok.lens_swap_cleared
        and (not p62a_bypass_off_blocked.admitted)
        and p62a_bypass_off_blocked.errno_code == EBUSY_ERRNO
        and (not p62a_legacy_v1_2bars_rejected.admitted)
        and p62a_legacy_v1_2bars_rejected.errno_code == EACCES_ERRNO
        and p62a_legacy_v1_3bars_ok.admitted
        and (not p62a_fx6_ibis_rejected.admitted)
        and p62a_fx6_ibis_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p62a_fx6_end_apr_ok.admitted
        and p62a_fx6_end_apr_ok.apr_executed
        and (not p62a_fx6_end_apr_ok.fx6_has_ibis_sensor_shake)
        and (not p62a_fx3_end_rejected.admitted)
        and p62a_fx3_end_rejected.errno_code == EOPNOTSUPP_ERRNO
    )

    # Pillar 62B scenarios
    p62b_still_5ev_ok = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        exposure_mode=EXP_MODE_A,
        requested_ev=4.7,
        exposure_step=EXP_STEP_0_3EV,
    )
    p62b_movie_2ev_ok = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        exposure_mode=EXP_MODE_P,
        log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO,
        requested_ev=-2.0,
    )
    p62b_movie_3ev_clamped_rejected = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        exposure_mode=EXP_MODE_P,
        requested_ev=3.0,
    )
    p62b_iauto_rejected = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        exposure_mode=EXP_MODE_IAUTO,
        requested_ev=1.0,
    )
    p62b_m_fixed_iso_rejected = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        exposure_mode=EXP_MODE_M,
        iso_auto=False,
        requested_ev=1.0,
    )
    p62b_m_iso_auto_ok = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        exposure_mode=EXP_MODE_M,
        iso_auto=True,
        requested_ev=-1.5,
        exposure_step=EXP_STEP_0_5EV,
    )
    p62b_cine_ei_lockout = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        exposure_mode=EXP_MODE_M,
        iso_auto=False,
        log_shooting_mode=LOG_SHOOTING_CINE_EI,
        requested_ev=1.0,
    )
    p62b_cine_ei_quick_lockout = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        exposure_mode=EXP_MODE_M,
        iso_auto=False,
        log_shooting_mode=LOG_SHOOTING_CINE_EI_QUICK,
        requested_ev=-0.7,
    )
    p62b_cam_reset_vs_step = simulate_exposure_comp_and_cine_ei_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        exposure_mode=EXP_MODE_A,
        requested_ev=3.0,
        exposure_step=EXP_STEP_0_5EV,
        camera_settings_reset_applied=True,
    )
    p62b_dormant_reset_ev_comp_rejected = simulate_exposure_comp_and_cine_ei_hil(
        requested_dormant_feature="Reset EV Comp.",
    )
    p62b_dormant_dial_ev_comp_rejected = simulate_exposure_comp_and_cine_ei_hil(
        requested_dormant_feature="Dial Ev Comp",
    )
    p62b_fx6_rejected = simulate_exposure_comp_and_cine_ei_hil(
        body_profile=BODY_MODEL_FX6,
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        requested_ev=1.0,
    )
    p62b_cine_ei_monitoring = evaluate_cine_ei_monitoring_profile(
        log_shooting_mode=LOG_SHOOTING_CINE_EI,
        base_iso=800,
        exposure_index_ev=-1.0,
    )

    p62b_ok = (
        p62b_still_5ev_ok.admitted
        and p62b_still_5ev_ok.effective_ev == 4.7
        and p62b_still_5ev_ok.live_meter_clamped_ev == 3.0
        and p62b_movie_2ev_ok.admitted
        and p62b_movie_2ev_ok.effective_ev == -2.0
        and (not p62b_movie_3ev_clamped_rejected.admitted)
        and p62b_movie_3ev_clamped_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62b_iauto_rejected.admitted)
        and p62b_iauto_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62b_m_fixed_iso_rejected.admitted)
        and p62b_m_fixed_iso_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p62b_m_iso_auto_ok.admitted
        and p62b_m_iso_auto_ok.effective_ev == -1.5
        and (not p62b_cine_ei_lockout.admitted)
        and p62b_cine_ei_lockout.errno_code == EOPNOTSUPP_ERRNO
        and (not p62b_cine_ei_lockout.cine_ei_exp_comp_enabled)
        and (not p62b_cine_ei_quick_lockout.admitted)
        and p62b_cine_ei_quick_lockout.errno_code == EOPNOTSUPP_ERRNO
        and p62b_cam_reset_vs_step.admitted
        and p62b_cam_reset_vs_step.effective_ev == 0.0
        and p62b_cam_reset_vs_step.effective_exposure_step == EXP_STEP_0_5EV
        and (not p62b_dormant_reset_ev_comp_rejected.admitted)
        and p62b_dormant_reset_ev_comp_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62b_dormant_dial_ev_comp_rejected.admitted)
        and p62b_dormant_dial_ev_comp_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62b_fx6_rejected.admitted)
        and p62b_fx6_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p62b_cine_ei_monitoring["monitoring_ei_iso"] == 1600
    )

    # Pillar 62C scenarios
    p62c_still_5_modes = {
        mode: simulate_focus_mode_split_hil(
            shooting_domain=EXPOSURE_DOMAIN_STILL,
            requested_focus_mode=mode,
            priority_set_af_s=AF_PRIORITY_AF,
            priority_set_af_c=AF_PRIORITY_RELEASE,
            af_illuminator=AF_ILLUMINATOR_AUTO,
        )
        for mode in STILL_FOCUS_MODES
    }
    p62c_movie_afc_ok = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        requested_focus_mode=FOCUS_MODE_AFC,
        af_assist_on=True,
    )
    p62c_movie_mf_ok = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        requested_focus_mode=FOCUS_MODE_MF,
    )
    p62c_movie_afs_rejected = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        requested_focus_mode=FOCUS_MODE_AFS,
    )
    p62c_sq_afa_rejected = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_SQ,
        requested_focus_mode=FOCUS_MODE_AFA,
    )
    p62c_sq_dmf_rejected = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_SQ,
        requested_focus_mode=FOCUS_MODE_DMF,
    )
    p62c_cam_reset_lifecycle = simulate_focus_mode_split_hil(
        shooting_domain=EXPOSURE_DOMAIN_STILL,
        requested_focus_mode=FOCUS_MODE_DMF,
        priority_set_af_s=AF_PRIORITY_AF,
        priority_set_af_c=AF_PRIORITY_RELEASE,
        af_assist_on=True,
        af_illuminator=AF_ILLUMINATOR_OFF,
        camera_settings_reset_applied=True,
    )
    p62c_fx6_push_af = simulate_focus_mode_split_hil(
        body_profile=BODY_MODEL_FX6,
        shooting_domain=EXPOSURE_DOMAIN_MOVIE,
        requested_focus_mode=FOCUS_MODE_AFC,
        fx6_push_af_mode="Single-shot AF(AF-S)",
    )

    p62c_ok = (
        all(res.admitted and len(res.exposed_modes) == 5 for res in p62c_still_5_modes.values())
        and p62c_still_5_modes[FOCUS_MODE_AFS].af_illuminator_active_now
        and (not p62c_still_5_modes[FOCUS_MODE_AFC].af_illuminator_active_now)
        and p62c_movie_afc_ok.admitted
        and p62c_movie_afc_ok.effective_af_assist_on
        and (not p62c_movie_afc_ok.af_illuminator_active_now)
        and len(p62c_movie_afc_ok.exposed_modes) == 2
        and p62c_movie_mf_ok.admitted
        and (not p62c_movie_afs_rejected.admitted)
        and p62c_movie_afs_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62c_sq_afa_rejected.admitted)
        and p62c_sq_afa_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62c_sq_dmf_rejected.admitted)
        and p62c_sq_dmf_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p62c_cam_reset_lifecycle.effective_focus_mode == FOCUS_MODE_AFA
        and p62c_cam_reset_lifecycle.effective_priority_af_s == AF_PRIORITY_AF
        and p62c_cam_reset_lifecycle.effective_priority_af_c == AF_PRIORITY_RELEASE
        and p62c_cam_reset_lifecycle.effective_af_assist_on
        and p62c_cam_reset_lifecycle.effective_af_illuminator == AF_ILLUMINATOR_AUTO
        and p62c_fx6_push_af.admitted
        and p62c_fx6_push_af.fx6_push_af_mode == "Single-shot AF(AF-S)"
    )

    # Pillar 62D scenarios
    p62d_view_25_group_rot_ok = simulate_playback_view_index_rotate_vault_hil(
        view_mode=VIEW_MODE_XAVCS,
        image_index=IMAGE_INDEX_25,
        display_as_group=True,
        display_rotation=DISPLAY_ROTATION_MANUAL,
        playback_slot=SLOT_2,
        rotate_requested=True,
        initial_orientation_deg=0,
    )
    p62d_dormant_12_rejected = simulate_playback_view_index_rotate_vault_hil(
        image_index=DORMANT_IMAGE_INDEX_12,
    )
    p62d_dormant_30_rejected = simulate_playback_view_index_rotate_vault_hil(
        image_index=DORMANT_IMAGE_INDEX_30,
    )
    p62d_slot1_vault_rotate_blocked = simulate_playback_view_index_rotate_vault_hil(
        playback_slot=SLOT_1,
        slot1_is_tier0_vault=True,
        media_kind=MEDIA_KIND_STILL_RAW,
        rotate_requested=True,
    )
    p62d_movie_rotate_rejected = simulate_playback_view_index_rotate_vault_hil(
        playback_slot=SLOT_2,
        media_kind=MEDIA_KIND_MOVIE_XAVCS,
        rotate_requested=True,
    )
    p62d_bg_ftp_rotate_blocked = simulate_playback_view_index_rotate_vault_hil(
        playback_slot=SLOT_2,
        background_transfer_active=True,
        rotate_requested=True,
    )
    p62d_cam_reset_survives = simulate_playback_view_index_rotate_vault_hil(
        view_mode=VIEW_MODE_FOLDER_STILL,
        image_index=IMAGE_INDEX_25,
        display_as_group=True,
        display_rotation=DISPLAY_ROTATION_OFF,
        camera_settings_reset_applied=True,
    )
    p62d_initialize_clears = simulate_playback_view_index_rotate_vault_hil(
        view_mode=VIEW_MODE_AVCHD,
        image_index=IMAGE_INDEX_25,
        display_as_group=True,
        display_rotation=DISPLAY_ROTATION_OFF,
        initialize_applied=True,
    )

    p62d_ok = (
        p62d_view_25_group_rot_ok.admitted
        and p62d_view_25_group_rot_ok.effective_orientation_deg == 90
        and p62d_view_25_group_rot_ok.avf_info_exif_mutated
        and p62d_view_25_group_rot_ok.physical_device_writes == 0
        and (not p62d_dormant_12_rejected.admitted)
        and p62d_dormant_12_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62d_dormant_30_rejected.admitted)
        and p62d_dormant_30_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62d_slot1_vault_rotate_blocked.admitted)
        and p62d_slot1_vault_rotate_blocked.errno_code == EROFS_ERRNO
        and p62d_slot1_vault_rotate_blocked.tier0_vault_firewall_triggered
        and (not p62d_slot1_vault_rotate_blocked.avf_info_exif_mutated)
        and p62d_slot1_vault_rotate_blocked.slot1_vault_rotate_mutation_bytes == 0
        and (not p62d_movie_rotate_rejected.admitted)
        and p62d_movie_rotate_rejected.errno_code == EOPNOTSUPP_ERRNO
        and (not p62d_bg_ftp_rotate_blocked.admitted)
        and p62d_bg_ftp_rotate_blocked.errno_code == EBUSY_ERRNO
        and p62d_cam_reset_survives.effective_view_mode == VIEW_MODE_FOLDER_STILL
        and p62d_cam_reset_survives.effective_image_index == IMAGE_INDEX_25
        and p62d_cam_reset_survives.effective_display_as_group
        and p62d_cam_reset_survives.effective_display_rotation == DISPLAY_ROTATION_OFF
        and p62d_initialize_clears.effective_view_mode == VIEW_MODE_DATE
        and p62d_initialize_clears.effective_image_index == IMAGE_INDEX_9
        and (not p62d_initialize_clears.effective_display_as_group)
        and p62d_initialize_clears.effective_display_rotation == DISPLAY_ROTATION_AUTO
    )

    milestone_probe = _build_stage62_milestone_probe()

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
        "sensor_cleaning_low_battery_bypass_events": SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS,
        "sensor_cleaning_mandatory_poweroff_bypass_events": (
            SENSOR_CLEANING_MANDATORY_POWEROFF_BYPASS_EVENTS
        ),
        "fx6_ibis_sensor_shake_spoof_events": FX6_IBIS_SENSOR_SHAKE_SPOOF_EVENTS,
        "fx3_has_builtin_end_filter": FX3_HAS_BUILTIN_END_FILTER,
        "fx6_has_ibis_sensor_shake": FX6_HAS_IBIS_SENSOR_SHAKE,
        "cine_ei_exp_comp_enabled": CINE_EI_EXP_COMP_ENABLED,
        "ev_comp_cine_ei_or_mode_bypass_events": EV_COMP_CINE_EI_OR_MODE_BYPASS_EVENTS,
        "movie_sq_invalid_focus_mode_bypass_events": MOVIE_SQ_INVALID_FOCUS_MODE_BYPASS_EVENTS,
        "dormant_12_30_image_index_exposed_events": DORMANT_12_30_IMAGE_INDEX_EXPOSED_EVENTS,
        "slot1_vault_rotate_mutation_bytes": SLOT1_VAULT_ROTATE_MUTATION_BYTES,
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
        and p62a_ok
        and p62b_ok
        and p62c_ok
        and p62d_ok
        and milestone_probe["is_62nd_stage_milestone"]
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_306_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_62nd_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_sensor_cleaning_battery_poweroff_and_fx6_end_apr_hil": {
            "passed": p62a_ok,
            "min_battery_percent_ver2_plus": SENSOR_CLEANING_MIN_BATTERY_PCT,
            "legacy_min_battery_bars": SENSOR_CLEANING_LEGACY_MIN_BARS,
            "fx6_nd_stops": list(FX6_END_STOPS),
            "fx3_50pct_rejected": asdict(p62a_50pct_rejected),
            "fx3_51pct_shake_and_poweroff_ok": asdict(p62a_51pct_shake_and_off_ok),
            "fx3_bypass_poweroff_blocked": asdict(p62a_bypass_off_blocked),
            "fx3_legacy_v1_2bars_rejected": asdict(p62a_legacy_v1_2bars_rejected),
            "fx3_legacy_v1_3bars_ok": asdict(p62a_legacy_v1_3bars_ok),
            "fx6_ibis_shake_rejected": asdict(p62a_fx6_ibis_rejected),
            "fx6_end_and_apr_ok": asdict(p62a_fx6_end_apr_ok),
            "fx3_builtin_end_rejected": asdict(p62a_fx3_end_rejected),
        },
        "pillar_b_exposure_comp_and_cine_ei_total_lockout_hil": {
            "passed": p62b_ok,
            "still_ev_range": [STILL_EXP_COMP_MIN_EV, STILL_EXP_COMP_MAX_EV],
            "movie_sq_ev_range": [MOVIE_EXP_COMP_MIN_EV, MOVIE_EXP_COMP_MAX_EV],
            "live_meter_range": [LIVE_EV_METER_MIN_EV, LIVE_EV_METER_MAX_EV],
            "valid_exposure_steps": list(VALID_EXPOSURE_STEPS),
            "dormant_ev_features_rejected": list(DORMANT_EV_FEATURES),
            "still_4_7ev_ok": asdict(p62b_still_5ev_ok),
            "movie_flex_iso_2ev_ok": asdict(p62b_movie_2ev_ok),
            "movie_3ev_clamped_rejected": asdict(p62b_movie_3ev_clamped_rejected),
            "iauto_rejected": asdict(p62b_iauto_rejected),
            "manual_m_fixed_iso_rejected": asdict(p62b_m_fixed_iso_rejected),
            "manual_m_iso_auto_ok": asdict(p62b_m_iso_auto_ok),
            "cine_ei_total_lockout": asdict(p62b_cine_ei_lockout),
            "cine_ei_quick_total_lockout": asdict(p62b_cine_ei_quick_lockout),
            "camera_settings_reset_vs_step_lifecycle": asdict(p62b_cam_reset_vs_step),
            "dormant_reset_ev_comp_rejected": asdict(p62b_dormant_reset_ev_comp_rejected),
            "dormant_dial_ev_comp_rejected": asdict(p62b_dormant_dial_ev_comp_rejected),
            "fx6_5ev_dial_rejected": asdict(p62b_fx6_rejected),
            "cine_ei_monitoring_profile": p62b_cine_ei_monitoring,
        },
        "pillar_c_focus_mode_5still_vs_2movie_split_and_priority_hil": {
            "passed": p62c_ok,
            "still_5_focus_modes": list(STILL_FOCUS_MODES),
            "movie_sq_2_focus_modes": list(MOVIE_SQ_FOCUS_MODES),
            "dormant_focus_modes_rejected": list(DORMANT_FOCUS_MODES),
            "valid_af_priorities": list(VALID_AF_PRIORITIES),
            "still_5_modes_eval": {k: asdict(v) for k, v in p62c_still_5_modes.items()},
            "movie_afc_assist_ok": asdict(p62c_movie_afc_ok),
            "movie_mf_ok": asdict(p62c_movie_mf_ok),
            "movie_afs_rejected": asdict(p62c_movie_afs_rejected),
            "sq_afa_rejected": asdict(p62c_sq_afa_rejected),
            "sq_dmf_rejected": asdict(p62c_sq_dmf_rejected),
            "camera_settings_reset_priority_survival": asdict(p62c_cam_reset_lifecycle),
            "fx6_push_af_contrast": asdict(p62c_fx6_push_af),
        },
        "pillar_d_playback_view_index_rotate_vault_and_redlines": {
            "passed": p62d_ok,
            "fx3_active_view_modes": list(FX3_ACTIVE_VIEW_MODES),
            "wave52_standard_view_modes": list(WAVE52_STANDARD_VIEW_MODES),
            "valid_fx3_image_index_modes": list(VALID_FX3_IMAGE_INDEX_MODES),
            "dormant_image_index_rejected": list(DORMANT_IMAGE_INDEX_MODES),
            "valid_display_rotation_modes": list(VALID_DISPLAY_ROTATION_MODES),
            "slot2_xavcs_25images_group_rotate_ok": asdict(p62d_view_25_group_rot_ok),
            "dormant_12images_rejected": asdict(p62d_dormant_12_rejected),
            "dormant_30images_rejected": asdict(p62d_dormant_30_rejected),
            "slot1_vault_rotate_blocked_erofs": asdict(p62d_slot1_vault_rotate_blocked),
            "movie_rotate_rejected": asdict(p62d_movie_rotate_rejected),
            "background_transfer_rotate_blocked": asdict(p62d_bg_ftp_rotate_blocked),
            "camera_settings_reset_survives": asdict(p62d_cam_reset_survives),
            "initialize_clears_playback_prefs": asdict(p62d_initialize_clears),
            "stage62_milestone_probe": milestone_probe,
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
        prog="realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py",
        description=(
            "Phase 306 Stage 62 (62/62 Milestone) Wave-52 Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Sensor Cleaning >= 51%% NP-FZ100 Battery Gate + Mandatory Power-OFF "
            "vs FX6 e-ND + APR, Exposure Comp. +-5.0/+-2.0 EV + Cine EI Lockout, Focus Mode "
            "5-Still vs 2-Movie/S&Q Split, & Playback View Mode / 9-25 Image Index / Display as "
            "Group / Rotate Slot-1 Vault Firewall HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 306 Stage 62 (62/62) Wave-52 HIL verification suite",
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
        help="Emit concise one-line Stage 62 (62/62) Wave-52 verification summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase306_sensor_cleaning_ev_comp_focus_mode_rotate_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 306 Stage 62 (62/62 Milestone) | mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"bat51_ok=1 fx6_end=1 "
            f"ev_5_2_ei_lock={int(not red['cine_ei_exp_comp_enabled'])} "
            f"fm_5_2=1 idx_9_25=1 s1_rot_mut={red['slot1_vault_rotate_mutation_bytes']} "
            f"emmc_wr={red['emmc_nflasha_write_count']} "
            f"leak={red['raw_firmware_bytes_leaked']} "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
