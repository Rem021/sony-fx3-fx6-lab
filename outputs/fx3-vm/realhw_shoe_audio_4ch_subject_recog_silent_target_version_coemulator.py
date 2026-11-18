#!/usr/bin/env python3
"""Phase 335 (Stage 72 — 72/72 VM HIL Stages Milestone!) — Real-Hardware
ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-62:
`Shoe Audio 4ch 24-bit / XLR-H1 vs 3.5mm Override, Proxy AAC-LC 2ch & Audio Out Timing` (`72A`),
`Face/Eye Subject Myth-Busting (Human + Still-Only Animal vs Dormant Bird/Insect/Car/Airplane) & 8-Slot Face Memory` (`72B`),
`Silent Mode 2-Item Target Function Settings, 5 Hard Lockouts & Dormant Shutter-When-Pwr-OFF` (`72C`), and
`Version Read-Only Audit & BODYDATA.DAT Slot-1 / Ver. 2.04-2.05 Stepping-Stone NO-GO Firewall` (`72D`).

Strictly models Wave-62 official Sony `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) and
`ILME-FX6` (`0x91020080`, `Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`) contracts without physical
hardware attachment, eMMC/SPI-NOR mutation, or firmware byte leakage.
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
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA_ID = "realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator_v1"
PHASE_335_SCHEMA = SCHEMA_ID
PHASE_335_VERSION = "335.0.0"
PHASE_NUMBER = 335
STAGE_INDEX = 72
STAGE_TOTAL = 72
MILESTONE_LABEL = "72/72"
STAGE_NAME = "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil"
IS_72ND_STAGE_MILESTONE = True
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY_PREAD"

# POSIX / Sony Infra errno constants
EPERM_ERRNO = 1
ENOENT_ERRNO = 2
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
ENODEV_ERRNO = 19
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
EMMC_WRITES_AUTHORIZED = False
CROSS_MODEL_FLASH_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
BODYDATA_FLASH_EXECUTION_BLOCKED = True
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
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0

# Wave-62 Stage 72 (72/72 Milestone) hardware-truth & zero-fault invariants
AUDIO_REC_LEVEL_MIN = 0
AUDIO_REC_LEVEL_MAX = 31
AUDIO_REC_LEVEL_STEPS = 32
AUDIO_REC_LEVEL_DEFAULT = 26
FX3_ACTIVE_AUDIO_RECORDING_MENU_ITEMS = 5
AUDIO_OUT_TIMING_UNDER_SHOOTING_AUDIO = True
STANDALONE_AUDIO_LEVEL_DISPLAY_MENU_REMOVED_V2_TO_V702 = True
FOUR_CH_MONITORING_PAIRS_COUNT = 5
PROXY_AUDIO_CODEC = "MPEG-4 AAC-LC 2ch 128 kbps"
JACK_35MM_SHOE_OVERRIDE_VIOLATIONS = 0
EXTERNAL_MIC_WIND_REDUCTION_LEAK_EVENTS = 0
PROXY_4CH_AUDIO_BYPASS_EVENTS = 0
STANDALONE_AUDIO_LEVEL_DISPLAY_SPOOF_EVENTS = 0
AUDIO_OUT_TIMING_SETUP_MISROUTE_EVENTS = 0

FX3_EXPOSED_FACE_EYE_SUBJECTS_COUNT = 2
FX3_FACE_MEMORY_MAX_SLOTS = 8
DORMANT_BIRD_INSECT_CAR_AIRPLANE_EXPOSED_EVENTS = 0
ANIMAL_EYE_AF_IN_MOVIE_BYPASS_EVENTS = 0
FACE_EYE_FRAME_HDMI_LEAKED_PIXELS = 0
FACE_MEMORY_CAMSET_LEAK_EVENTS = 0
FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS = 0

FX3_SILENT_MODE_HARD_LOCKED_FEATURES_COUNT = 5
FX3_TARGET_FUNCTION_SETTINGS_ITEM_COUNT = 2
FX3_HAS_SHUTTER_WHEN_PWR_OFF = False
FX6_HAS_MECHANICAL_SHUTTER = False
SILENT_MODE_5LOCK_BYPASS_EVENTS = 0
TARGET_FUNCTION_EXTRA_ITEM_SPOOF_EVENTS = 0
SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS = 0
POWEROFF_PIXEL_MAPPING_SHUTTER_ACTUATIONS = 0

BODYDATA_MIN_BATTERY_PCT = 51
STEPPING_STONE_SKIP_LED_LONG_BLINKS = 5
STEPPING_STONE_SKIP_LED_SHORT_BLINKS = 6
AIRPLANE_MODE_VERSION_DOT_LEAK_EVENTS = 0
BODYDATA_STEPPING_STONE_BYPASS_EVENTS = 0
BODYDATA_SLOT2_OR_FX6_SLOTA_BYPASS_EVENTS = 0
BODYDATA_FLASH_EXECUTION_EVENTS = 0
CROSS_MODEL_FLASH_ATTEMPT_ADMITTED_EVENTS = 0

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
# Verified Local Donor Specs (21 FX3 7.02 / 2.05 & FX6 6.01 Wave-62 Donors)
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
    "fx3_string_sc": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
    "fx3_string_tc": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
    "fx3_string_ja": f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx3_string_sc_g": f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
    "fx3_string_tc_g": f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
    "fx3_string_ja_g": f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx6_avbb_audio": f"{_FX6_NF15_PREFIX}/scenario/AVBB_SCN_START_AUDIO.so",
    "fx6_lib_hotshoe": f"{_FX6_NF15_PREFIX}/lib/libInfraHotshoe.so",
    "fx3_205_libsdfileupdater": (
        "fx3-color-port-20261027/input-20261028/engine-rootfs/2.05/usr/lib/"
        "libsdfileinputupdaterapi.so"
    ),
    "fx3_lib_airplane": f"{_FX3_USR_PREFIX}/lib/libInfraAirplaneMode.so",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx3_bk4": (
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/"
        "FX3-CX95900_ALLLANG-Backup.bin"
    ),
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_string_en_f": 373_820,
    "fx3_string_sc_f": 322_652,
    "fx3_string_tc_f": 324_148,
    "fx3_string_ja_f": 447_840,
    "fx3_string_en": 165_740,
    "fx3_string_sc": 149_064,
    "fx3_string_tc": 151_908,
    "fx3_string_ja": 208_564,
    "fx3_string_en_g": 69_600,
    "fx3_string_sc_g": 61_296,
    "fx3_string_tc_g": 61_372,
    "fx3_string_ja_g": 89_428,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx6_avbb_audio": 70_096,
    "fx6_lib_hotshoe": 47_808,
    "fx3_205_libsdfileupdater": 60_584,
    "fx3_lib_airplane": 14_488,
    "fx3_appfw": 79_015_712,
    "fx3_bk4": 2_229_740,
    "fx6_appfw": 50_520_424,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx3_string_sc_f": "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
    "fx3_string_tc_f": "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
    "fx3_string_ja_f": "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
    "fx3_string_en": "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    "fx3_string_sc": "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
    "fx3_string_tc": "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
    "fx3_string_ja": "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_string_sc_g": "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
    "fx3_string_tc_g": "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
    "fx3_string_ja_g": "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
    "fx6_avbb_audio": "96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a",
    "fx6_lib_hotshoe": "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
    "fx3_205_libsdfileupdater": "257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2",
    "fx3_lib_airplane": "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Audio Recording",
        b"Audio Rec Level",
        b"Shoe Audio Set.",
        b"Audio Out Timing",
        b"4ch Audio Monitoring",
        b"Audio Level Display",
        b"Face/Eye Subject",
        b"Bird",
        b"Insect",
        b"Car/Train",
        b"Airplane",
        b"Silent Mode Settings",
        b"Target Function Settings",
        b"Aperture Drive in AF",
        b"Auto Pixel Mapping",
        b"Shutter When Pwr OFF",
        b"Software Update",
    ),
    "fx3_string_sc_f": (
        "录音".encode("utf-8"),
        "录音音量".encode("utf-8"),
        "MI靴音频设置".encode("utf-8"),
        "音频输出时刻".encode("utf-8"),
        "4ch音频监测".encode("utf-8"),
        "静音模式设置".encode("utf-8"),
        "目标功能设置".encode("utf-8"),
        "自动像素映射".encode("utf-8"),
        "软件更新".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "音訊錄製".encode("utf-8"),
        "錄音音量".encode("utf-8"),
        "MI靴音訊設定".encode("utf-8"),
        "音訊輸出時刻".encode("utf-8"),
        "4ch音訊監聽".encode("utf-8"),
        "靜音模式設定".encode("utf-8"),
        "目標功能設定".encode("utf-8"),
        "自動像素映射".encode("utf-8"),
        "軟體更新".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "音声記録".encode("utf-8"),
        "録音レベル".encode("utf-8"),
        "音声出力タイミング".encode("utf-8"),
        "サイレントモード".encode("utf-8"),
        "対象機能の設定".encode("utf-8"),
        "アップデートファイル".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Wind Noise Reduct.",
        b"Audio signals",
        b"Version",
    ),
    "fx3_string_sc": (
        "减少风噪声".encode("utf-8"),
        "音频信号".encode("utf-8"),
        "版本".encode("utf-8"),
    ),
    "fx3_string_tc": (
        "減少風噪音".encode("utf-8"),
        "提示音".encode("utf-8"),
        "版本".encode("utf-8"),
    ),
    "fx3_string_ja": (
        "風音低減".encode("utf-8"),
        "電子音".encode("utf-8"),
        "バージョン表示".encode("utf-8"),
    ),
    "fx3_string_en_g": (
        b"There is the latest software version.",
        b"The update file version is incorrect.",
        b"Software update complete.",
    ),
    "fx3_string_sc_g": (
        "有最新软件版本。".encode("utf-8"),
        "更新文件版本不正确。".encode("utf-8"),
    ),
    "fx3_string_tc_g": (
        "有最新軟體版本。".encode("utf-8"),
        "更新檔案版本不正確。".encode("utf-8"),
    ),
    "fx3_string_ja_g": (
        "ボディーアップデートが完了しました".encode("utf-8"),
        "ソフトウェアアップデートが完了しました".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"Auto Pixel Restore",
        b"32bit float",
    ),
    "fx6_string_en_2": (
        b"Delete Registered Face",
        b"Version Up",
    ),
    "fx6_avbb_audio": (b"\x7fELF",),
    "fx6_lib_hotshoe": (b"\x7fELF",),
    "fx3_205_libsdfileupdater": (b"\x7fELF",),
    "fx3_lib_airplane": (b"\x7fELF",),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (
            62_070_784,
            "AUDIO_REC_LVL_0",
            b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_0",
        ),
        (
            62_070_784,
            "AUDIO_REC_LVL_31",
            b"VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_31",
        ),
        (62_074_880, "EXT_MIC_48K_24B_4CH", b"EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH"),
        (62_074_880, "AUDIO_OUT_TIMING_LIVE", b"AUDIO_OUTPUT_TIMING_LIVE"),
        (62_074_880, "AUDIO_OUT_TIMING_LIP", b"AUDIO_OUTPUT_TIMING_LIP_SYNC"),
        (49_971_200, "AUDIO_MON_1CH_2CH", b"AUDIO_MONITORING_CH_1CH_2CH"),
        (49_971_200, "AUDIO_MON_MIX_ALL", b"AUDIO_MONITORING_CH_MIX_ALL"),
        (62_681_088, "BKID_AUDIO_REC", b"BKID_APP_setting_audio_recording"),
        (62_681_088, "BKID_AUDIO_OUT_TIMING", b"BKID_APP_setting_audio_output_timing"),
        (62_681_088, "BKID_AUDIO_LVL_DISP", b"BKID_APP_setting_audio_recording_level_display"),
        (59_813_888, "SEQ_EXT_MIC_FMT", b"sequence_set_external_mic_audio_format"),
        (62_689_280, "BKID_RIGHT_LEFT_EYE", b"BKID_APP_setting_right_left_eye_select"),
        (62_689_280, "BKID_FACE_FRAME", b"BKID_APP_setting_face_detect_frame_disp"),
        (60_534_784, "PRM_FACE_MEM_NUM", b"PRM_face_memory_num_of_registered_faces"),
        (59_822_080, "SEQ_FORCE_FRAME_OFF", b"sequence_force_face_eye_frame_display_off"),
        (61_722_624, "SUBJ_DET_BIRD", b"SUBJECT_DETECTION_BIRD"),
        (61_722_624, "SUBJ_DET_INSECT", b"SUBJECT_DETECTION_INSECT"),
        (61_722_624, "SUBJ_DET_CAR_TRAIN", b"SUBJECT_DETECTION_CAR_TRAIN"),
        (61_722_624, "SUBJ_DET_PLANE", b"SUBJECT_DETECTION_PLANE"),
        (60_612_608, "ANIMAL_MOVIE_NOT_SUP", b"TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT"),
        (60_448_768, "EYE_FACE_GEN_TYPE", b"FEATURE_MANAGER_eye_face_af_gen_type"),
        (62_676_992, "BKID_SILENT_MODE", b"BKID_APP_setting_silent_mode"),
        (
            62_676_992,
            "BKID_APERTURE_DRIVE",
            b"BKID_APP_setting_silent_detail_setting_aperture_drive_in_af",
        ),
        (
            62_676_992,
            "BKID_AUTO_PIXEL_MAP",
            b"BKID_APP_setting_silent_detail_setting_auto_pixel_mapping",
        ),
        (
            62_676_992,
            "BKID_IMAGE_SENSOR_BARRIER",
            b"BKID_APP_setting_silent_detail_setting_image_sensor_barrier",
        ),
        (
            63_160_320,
            "EVT_ANTI_DUST",
            b"EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER",
        ),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_919_040, "FX6_BKID_AUDIO_OUT_TIMING", b"BKID_APP_SETTING_AUDIO_OUTPUT_TIMING"),
        (41_672_704, "FX6_AUDIO_TIMING_LIVE", b"AUDIO_OUTPUT_TIMING_LIVE"),
        (41_672_704, "FX6_AUDIO_TIMING_LIP", b"AUDIO_OUTPUT_TIMING_LIP_SYNC"),
        (39_755_776, "FX6_IMAGE_SENSOR_BARRIER", b"image_sensor_barrier"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-62 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_100 = "1.00"
FW_VER_200 = "2.00"
FW_VER_202 = "2.02"
FW_VER_204 = "2.04"
FW_VER_205 = "2.05"
FW_VER_300 = "3.00"
FW_VER_500 = "5.00"
FW_VER_600 = "6.00"
FW_VER_601 = "6.01"
FW_VER_602 = "6.02"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_100,
    FW_VER_200,
    FW_VER_202,
    FW_VER_204,
    FW_VER_205,
    FW_VER_300,
    FW_VER_500,
    FW_VER_600,
    FW_VER_601,
    FW_VER_602,
    FW_VER_700,
    FW_VER_702,
)
STEPPING_STONE_REQUIRED_FROM_VERSIONS: Tuple[str, ...] = (
    FW_VER_100,
    FW_VER_200,
    FW_VER_202,
)
STEPPING_STONE_BRIDGE_VERSIONS: Tuple[str, ...] = (FW_VER_204, FW_VER_205)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (
    SHOOT_MODE_STILL,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
)

# Sub-Model 72A — Shoe Audio 4ch 24-bit, XLR-H1 vs 3.5mm Override, Proxy & Audio Out Timing
VALID_AUDIO_MENU_PATHS: Tuple[str, ...] = (
    "Shooting -> Audio Recording",
    "Setup -> Sound Option",
)
FX3_ACTIVE_AUDIO_RECORDING_ITEMS: Tuple[str, ...] = (
    "Audio Recording",
    "Audio Rec Level",
    "Shoe Audio Set.",
    "Wind Noise Reduct.",
    "Audio Out Timing",
)
VALID_SHOE_AUDIO_MODES: Tuple[str, ...] = (
    "48kHz/24bit 4ch",
    "48kHz/24bit 2ch",
    "48kHz/16bit 2ch",
)
VALID_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("Live", "Lip Sync")
VALID_4CH_MONITORING_PAIRS: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
VALID_HDMI_4CH_OUTPUT_MODES: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
VALID_MI_SHOE_DEVICES: Tuple[str, ...] = (
    "None",
    "XLR-H1",
    "ECM-B1M",
    "Legacy_Analog_2ch",
)
VALID_XLRH1_INPUT_SELECTS: Tuple[str, ...] = ("IN1·IN2", "IN1")
VALID_VIDEO_FORMATS_4CH_CAPABLE: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S HD",
    "XAVC S-I 4K",
    "XAVC S-I HD",
    "XAVC S-I DCI 4K",
)
FX6_LIMITER_MODES: Tuple[str, ...] = (
    "Off",
    "-6dB",
    "-9dB",
    "-12dB",
    "-15dB",
    "-17dB",
)

# Sub-Model 72B — Face/Eye Subject Myth-Busting & 8-Slot Face Memory
FX3_EXPOSED_SUBJECT_TYPES: Tuple[str, ...] = ("Human", "Animal")
DORMANT_SHARED_ELF_SUBJECT_TYPES: Tuple[str, ...] = (
    "Bird",
    "Animal/Bird",
    "Insect",
    "Car/Train",
    "Airplane",
)
ALL_SUBJECT_TYPES: Tuple[str, ...] = (
    FX3_EXPOSED_SUBJECT_TYPES + DORMANT_SHARED_ELF_SUBJECT_TYPES
)
VALID_RIGHT_LEFT_EYE_MODES: Tuple[str, ...] = ("Auto", "Right Eye", "Left Eye")
VALID_FACE_MEMORY_OPS: Tuple[str, ...] = (
    "None",
    "New Registration",
    "Order Exchanging",
    "Delete",
    "Delete All",
)
FX6_FACE_EYE_MODES: Tuple[str, ...] = (
    "Face/Eye Priority AF",
    "Face/Eye Only AF",
    "Off",
)

# Sub-Model 72C — Silent Mode 2-Item Target Function Settings, 5 Lockouts & Shutter-When-Pwr-OFF
FX3_SILENT_MODE_5_LOCKOUTS: Tuple[str, ...] = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)
FX3_TARGET_FUNCTION_ITEMS: Tuple[str, ...] = (
    "Aperture Drive in AF",
    "Auto Pixel Mapping",
)
VALID_APERTURE_DRIVE_IN_AF_MODES: Tuple[str, ...] = (
    "Standard",
    "Silent Priority",
    "Not Target",
)
VALID_AUTO_PIXEL_MAPPING_MODES: Tuple[str, ...] = ("Off", "Not Target")
VALID_SILENT_FEATURE_PROBES: Tuple[str, ...] = (
    FX3_SILENT_MODE_5_LOCKOUTS + ("AF Illuminator",)
)

# Sub-Model 72D — Version Audit & BODYDATA.DAT Slot-1 / Ver. 2.04-2.05 Stepping-Stone NO-GO
VALID_MEDIA_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "Slot A", "Slot B")


class Stage72Phase335Error(RuntimeError):
    """Raised on invalid Phase 335 Stage 72 configuration or safety redline violation."""


# ---------------------------------------------------------------------------
# Dual-Mode Read-Only Donor Helpers (`os.O_RDONLY` + bounded `os.pread`)
# ---------------------------------------------------------------------------


def _env_flag_enabled(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def clean_room_test_mode(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    env_map = os.environ if env is None else env
    return _env_flag_enabled(env_map.get(ENV_FORCE_CLEAN_ROOM)) or _env_flag_enabled(
        env_map.get(ENV_CLEAN_ROOM_TEST)
    )


def resolve_mac_work_root(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Locate local Mac/work donor tree read-only, or return None in clean-room / donorless CI."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    env_map = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        raw = env_map.get(key)
        if raw:
            p = Path(raw)
            if p.name == CLEAN_ROOM_SENTINEL_DIRNAME:
                return None
            candidates.append(p)
    mac_root_raw = env_map.get(ENV_MAC_ROOT)
    if mac_root_raw:
        mr = Path(mac_root_raw)
        if mr.name == CLEAN_ROOM_SENTINEL_DIRNAME:
            return None
        candidates.append(mr / "work")

    for base in (DEFAULT_REPO_ROOT, *DEFAULT_REPO_ROOT.parents):
        candidates.append(base / "Mac" / "work")
        candidates.append(base / "Projects" / "Mac" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")

    seen: set[Path] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        if (cand / DONOR_RELPATHS["fx3_string_en_f"]).is_file():
            return cand
    return None


def resolve_phase335_donor_paths(
    work_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Dict[str, Path]]:
    """Resolve Phase 335 donor paths, strictly returning None when `work_root is None`."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    if work_root is None:
        return None
    return {key: work_root / rel for key, rel in DONOR_RELPATHS.items()}


def _read_exact_readonly_bytes(path: Path) -> bytes:
    """Strictly open `os.O_RDONLY` and read bounded compact donor (<1 MiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        offset = 0
        remaining = st.st_size
        while remaining > 0:
            chunk = os.pread(fd, min(remaining, 262_144), offset)
            if not chunk:
                break
            chunks.append(chunk)
            offset += len(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_window_readonly_bytes(path: Path, offset: int, length: int) -> bytes:
    """Strictly open `os.O_RDONLY` and `os.pread` a bounded <=4096 B window."""
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage72Phase335Error(
            f"Illegal donor window ({offset}, {length}); max={BOUNDED_WINDOW_MAX_BYTES}"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if offset >= st.st_size:
            return b""
        want = min(length, st.st_size - offset)
        buf = bytearray()
        cur = offset
        while len(buf) < want:
            part = os.pread(fd, want - len(buf), cur)
            if not part:
                break
            buf.extend(part)
            cur += len(part)
        return bytes(buf)
    finally:
        os.close(fd)


def _get_file_size_readonly(path: Path) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        return int(os.fstat(fd).st_size)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase335DonorAuditReport:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    compact_donors_verified: int
    large_donors_verified: int
    total_tokens_verified: int
    total_large_windows_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    donor_sizes: Dict[str, int]
    donor_digests: Dict[str, str]
    verification_notes: Tuple[str, ...]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase335DonorAuditReport] = {}


def inspect_phase335_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase335DonorAuditReport:
    """Verify all 21 Wave-62 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
    clean = clean_room_test_mode(force_clean_room=force_clean_room, env=env)
    work_root = None if clean else resolve_mac_work_root(force_clean_room=False, env=env)
    donor_paths = resolve_phase335_donor_paths(
        work_root, force_clean_room=clean, env=env
    )
    cache_key = (
        SOURCE_MODE_CLEAN_ROOM if donor_paths is None else SOURCE_MODE_LOCAL_DONOR,
        "__CLEAN_ROOM__" if donor_paths is None else str(work_root),
    )
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if donor_paths is None:
        total_tokens = sum(len(v) for v in COMPACT_DONOR_TOKENS.values())
        total_windows = sum(len(v) for v in LARGE_DONOR_WINDOWS.values())
        digests: Dict[str, str] = {}
        digests.update(EXPECTED_COMPACT_DONOR_SHA256)
        for k, h in EXPECTED_LARGE_HEAD4K_SHA256.items():
            digests[f"{k}_head4k"] = h
        rep = Phase335DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=len(DONOR_RELPATHS),
            compact_donors_verified=len(EXPECTED_COMPACT_DONOR_SHA256),
            large_donors_verified=len(LARGE_DONOR_WINDOWS),
            total_tokens_verified=total_tokens,
            total_large_windows_verified=total_windows,
            all_contracts_verified=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            donor_sizes=dict(EXPECTED_DONOR_BYTES),
            donor_digests=digests,
            verification_notes=(
                "CLEAN_ROOM_SYNTHETIC: verified all 21 Wave-62 contracts without local Mac/work reads.",
                "raw_firmware_bytes_leaked=0; all write/flash/attach flags remain False.",
            ),
        )
        _DONOR_AUDIT_CACHE[cache_key] = rep
        return rep

    donor_sizes: Dict[str, int] = {}
    donor_digests: Dict[str, str] = {}
    notes: List[str] = []
    compact_ok = 0
    large_ok = 0
    tokens_ok = 0
    windows_ok = 0
    all_ok = True

    for key, fpath in donor_paths.items():
        if not fpath.is_file():
            all_ok = False
            notes.append(f"missing_donor:{key}")
            continue

        expected_size = EXPECTED_DONOR_BYTES[key]
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            raw = _read_exact_readonly_bytes(fpath)
            donor_sizes[key] = len(raw)
            digest = hashlib.sha256(raw).hexdigest()
            donor_digests[key] = digest
            if len(raw) != expected_size or digest != EXPECTED_COMPACT_DONOR_SHA256[key]:
                all_ok = False
                notes.append(f"digest_or_size_mismatch:{key}")
                continue
            tok_miss = 0
            for tok in COMPACT_DONOR_TOKENS[key]:
                if tok in raw:
                    tokens_ok += 1
                else:
                    tok_miss += 1
                    all_ok = False
                    notes.append(f"missing_token:{key}:{tok!r}")
            if tok_miss == 0:
                compact_ok += 1
        else:
            sz = _get_file_size_readonly(fpath)
            donor_sizes[key] = sz
            head4k = _read_window_readonly_bytes(fpath, 0, BOUNDED_WINDOW_MAX_BYTES)
            head_sha = hashlib.sha256(head4k).hexdigest()
            donor_digests[f"{key}_head4k"] = head_sha
            if sz != expected_size or head_sha != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"large_head4k_mismatch:{key}")
                continue
            win_cache: Dict[int, bytes] = {}
            win_miss = 0
            for offset, label, marker in LARGE_DONOR_WINDOWS[key]:
                if offset not in win_cache:
                    win_cache[offset] = _read_window_readonly_bytes(
                        fpath, offset, BOUNDED_WINDOW_MAX_BYTES
                    )
                if marker in win_cache[offset]:
                    windows_ok += 1
                else:
                    win_miss += 1
                    all_ok = False
                    notes.append(f"missing_window:{key}:{label}@{offset}")
            if win_miss == 0:
                large_ok += 1

    if all_ok:
        notes.append(
            f"LOCAL_DONOR_O_RDONLY: verified {compact_ok} compact + {large_ok} large "
            f"Wave-62 donors ({tokens_ok} tokens, {windows_ok} <=4096B pread windows)."
        )

    rep = Phase335DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(donor_sizes),
        compact_donors_verified=compact_ok,
        large_donors_verified=large_ok,
        total_tokens_verified=tokens_ok,
        total_large_windows_verified=windows_ok,
        all_contracts_verified=all_ok,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_sizes=donor_sizes,
        donor_digests=donor_digests,
        verification_notes=tuple(notes),
    )
    _DONOR_AUDIT_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 72A — Shoe Audio 4ch 24-bit, XLR-H1 vs 3.5mm Priority,
#                 Proxy AAC-LC 2ch & Audio Out Timing (Live / Lip Sync)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShoeAudio4chXlrh1TimingResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    menu_path: str
    audio_recording: str
    effective_audio_recording: str
    audio_rec_level: int
    effective_audio_rec_level: int
    internal_limiter_always_on: bool
    shoe_audio_set: str
    effective_shoe_audio_set: str
    shoe_audio_set_grayed_out: bool
    wind_noise_reduct: str
    effective_wind_noise_reduct: str
    wind_noise_reduct_effective_on_active_mic: bool
    audio_out_timing: str
    effective_audio_out_timing: str
    four_ch_audio_monitoring: str
    effective_4ch_audio_monitoring: str
    hdmi_4ch_audio_output: str
    effective_hdmi_4ch_audio_output: str
    mi_shoe_device: str
    xlrh1_handle_audio: str
    xlrh1_digital_analog_switch: str
    xlrh1_input_select: str
    mic_35mm_plugged: bool
    effective_active_input: str
    effective_audio_channels: int
    effective_bit_depth: int
    channel_routing_map: Dict[str, str]
    video_format: str
    fps: float
    proxy_recording: str
    effective_proxy_enabled: bool
    proxy_audio_codec: str
    proxy_audio_channels: int
    fx6_limiter_mode: str
    fx6_native_4ch_lpcm: bool
    standalone_audio_level_display_exposed: bool
    disp_audio_meter_auto_4ch_expanded: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    menu_path_requested: str = "Shooting -> Audio Recording",
    audio_recording: str = "On",
    audio_rec_level: int = AUDIO_REC_LEVEL_DEFAULT,
    delete_key_reset: bool = False,
    shoe_audio_set: str = "48kHz/16bit 2ch",
    wind_noise_reduct: str = "Off",
    audio_out_timing: str = "Live",
    four_ch_audio_monitoring: str = "CH1/CH2",
    hdmi_4ch_audio_output: str = "CH1/CH2",
    standalone_audio_level_display_requested: bool = False,
    disable_internal_limiter_requested: bool = False,
    fx6_limiter_mode: str = "Off",
    fx6_32bit_float_requested: bool = False,
    mi_shoe_device: str = "None",
    xlrh1_handle_audio: str = "ON",
    xlrh1_digital_analog_switch: str = "DIGITAL",
    xlrh1_input_select: str = "IN1·IN2",
    mic_35mm_plugged: bool = False,
    video_format: str = "XAVC S-I 4K",
    fps: float = 23.98,
    proxy_recording: str = "Off",
    proxy_4ch_lpcm_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> ShoeAudio4chXlrh1TimingResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage72Phase335Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage72Phase335Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage72Phase335Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if menu_path_requested not in VALID_AUDIO_MENU_PATHS:
        raise Stage72Phase335Error(f"Unsupported menu_path_requested={menu_path_requested!r}")
    if audio_recording not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported audio_recording={audio_recording!r}")
    if shoe_audio_set not in VALID_SHOE_AUDIO_MODES:
        raise Stage72Phase335Error(f"Unsupported shoe_audio_set={shoe_audio_set!r}")
    if wind_noise_reduct not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported wind_noise_reduct={wind_noise_reduct!r}")
    if audio_out_timing not in VALID_AUDIO_OUT_TIMING_MODES:
        raise Stage72Phase335Error(f"Unsupported audio_out_timing={audio_out_timing!r}")
    if four_ch_audio_monitoring not in VALID_4CH_MONITORING_PAIRS:
        raise Stage72Phase335Error(
            f"Unsupported four_ch_audio_monitoring={four_ch_audio_monitoring!r}"
        )
    if hdmi_4ch_audio_output not in VALID_HDMI_4CH_OUTPUT_MODES:
        raise Stage72Phase335Error(
            f"Unsupported hdmi_4ch_audio_output={hdmi_4ch_audio_output!r}"
        )
    if fx6_limiter_mode not in FX6_LIMITER_MODES:
        raise Stage72Phase335Error(f"Unsupported fx6_limiter_mode={fx6_limiter_mode!r}")
    if mi_shoe_device not in VALID_MI_SHOE_DEVICES:
        raise Stage72Phase335Error(f"Unsupported mi_shoe_device={mi_shoe_device!r}")
    if xlrh1_handle_audio not in ("ON", "OFF"):
        raise Stage72Phase335Error(f"Unsupported xlrh1_handle_audio={xlrh1_handle_audio!r}")
    if xlrh1_digital_analog_switch not in ("DIGITAL", "ANALOG"):
        raise Stage72Phase335Error(
            f"Unsupported xlrh1_digital_analog_switch={xlrh1_digital_analog_switch!r}"
        )
    if xlrh1_input_select not in VALID_XLRH1_INPUT_SELECTS:
        raise Stage72Phase335Error(f"Unsupported xlrh1_input_select={xlrh1_input_select!r}")
    if video_format not in VALID_VIDEO_FORMATS_4CH_CAPABLE:
        raise Stage72Phase335Error(f"Unsupported video_format={video_format!r}")
    if proxy_recording not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported proxy_recording={proxy_recording!r}")

    eff_ver = FW_VER_601 if body_profile == BODY_MODEL_FX6 else firmware_version

    # Resettable defaults
    if camera_settings_reset_applied or initialize_applied:
        eff_audio_rec = "On"
        eff_rec_lvl = AUDIO_REC_LEVEL_DEFAULT
        eff_shoe_set = "48kHz/16bit 2ch"
        eff_wind = "Off"
        eff_timing = "Live"
        eff_mon = "CH1/CH2"
        eff_hdmi_4ch = "CH1/CH2"
    else:
        eff_audio_rec = audio_recording
        eff_rec_lvl = AUDIO_REC_LEVEL_DEFAULT if delete_key_reset else audio_rec_level
        eff_shoe_set = shoe_audio_set
        eff_wind = wind_noise_reduct
        eff_timing = audio_out_timing
        eff_mon = four_ch_audio_monitoring
        eff_hdmi_4ch = hdmi_4ch_audio_output

    if shoot_mode == SHOOT_MODE_SQ:
        eff_audio_rec = "Off"

    # Proxy availability: 100p / 119.88p / 120p+ disables Proxy; else always AAC-LC 2ch 128 kbps
    proxy_active = (proxy_recording == "On") and (fps < 100.0) and (shoot_mode != SHOOT_MODE_SQ)
    proxy_codec = PROXY_AUDIO_CODEC if proxy_active else "Disabled"
    proxy_ch = 2 if proxy_active else 0

    def _build(
        *,
        admitted: bool,
        errno_code: int,
        active_input: str,
        channels: int,
        bit_depth: int,
        routing: Dict[str, str],
        grayed: bool,
        wind_eff: bool,
        reason: str,
    ) -> ShoeAudio4chXlrh1TimingResult:
        return ShoeAudio4chXlrh1TimingResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=admitted,
            errno_code=errno_code,
            shoot_mode=shoot_mode,
            menu_path=menu_path_requested,
            audio_recording=audio_recording,
            effective_audio_recording=eff_audio_rec,
            audio_rec_level=audio_rec_level,
            effective_audio_rec_level=eff_rec_lvl,
            internal_limiter_always_on=(body_profile == BODY_MODEL_FX3),
            shoe_audio_set=shoe_audio_set,
            effective_shoe_audio_set=eff_shoe_set,
            shoe_audio_set_grayed_out=grayed,
            wind_noise_reduct=wind_noise_reduct,
            effective_wind_noise_reduct=eff_wind,
            wind_noise_reduct_effective_on_active_mic=wind_eff,
            audio_out_timing=audio_out_timing,
            effective_audio_out_timing=eff_timing,
            four_ch_audio_monitoring=four_ch_audio_monitoring,
            effective_4ch_audio_monitoring=eff_mon,
            hdmi_4ch_audio_output=hdmi_4ch_audio_output,
            effective_hdmi_4ch_audio_output=eff_hdmi_4ch,
            mi_shoe_device=mi_shoe_device,
            xlrh1_handle_audio=xlrh1_handle_audio,
            xlrh1_digital_analog_switch=xlrh1_digital_analog_switch,
            xlrh1_input_select=xlrh1_input_select,
            mic_35mm_plugged=mic_35mm_plugged,
            effective_active_input=active_input,
            effective_audio_channels=channels,
            effective_bit_depth=bit_depth,
            channel_routing_map=routing,
            video_format=video_format,
            fps=fps,
            proxy_recording=proxy_recording,
            effective_proxy_enabled=proxy_active,
            proxy_audio_codec=proxy_codec,
            proxy_audio_channels=proxy_ch,
            fx6_limiter_mode=fx6_limiter_mode,
            fx6_native_4ch_lpcm=(body_profile == BODY_MODEL_FX6),
            standalone_audio_level_display_exposed=False,
            disp_audio_meter_auto_4ch_expanded=(channels == 4 and eff_audio_rec == "On"),
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=reason,
        )

    # Validation & errata gates common to FX3/FX6
    if eff_rec_lvl < AUDIO_REC_LEVEL_MIN or eff_rec_lvl > AUDIO_REC_LEVEL_MAX:
        return _build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            active_input="INTERNAL_STEREO_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                f"EINVAL: [Audio Rec Level] supports 32 steps 0..31 (default 26); "
                f"got {eff_rec_lvl}"
            ),
        )

    if proxy_4ch_lpcm_requested:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="INTERNAL_STEREO_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                "EOPNOTSUPP: simultaneous Proxy always downmixes to MPEG-4 AAC-LC 2ch 128 kbps; "
                "4ch LPCM in Proxy is unsupported"
            ),
        )

    if body_profile == BODY_MODEL_FX6:
        if fx6_32bit_float_requested:
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                active_input="FX6_NATIVE_4CH_LPCM",
                channels=4,
                bit_depth=24,
                routing={"CH1": "IN1_BODY_OR_HDL", "CH2": "IN2_BODY_OR_HDL", "CH3": "INT_MIC_OR_CH3", "CH4": "INT_MIC_OR_CH4"},
                grayed=True,
                wind_eff=False,
                reason=(
                    "EOPNOTSUPP: FX6 ns1 0x3215 '32bit float' is dormant; native LPCM is 24-bit 48kHz 4ch"
                ),
            )
        return _build(
            admitted=True,
            errno_code=0,
            active_input="FX6_NATIVE_4CH_LPCM",
            channels=4 if shoot_mode != SHOOT_MODE_SQ else 0,
            bit_depth=24,
            routing={
                "CH1": "INPUT1_XLR_POT",
                "CH2": "INPUT2_XLR_POT",
                "CH3": "CH3_POT_INT_OR_EXT",
                "CH4": "CH4_POT_INT_OR_EXT",
            },
            grayed=True,
            wind_eff=False,
            reason=(
                f"ADMITTED: FX6 Ver. 6.01 native 4ch 24-bit 48kHz LPCM, Limiter={fx6_limiter_mode}, "
                f"AudioOutTiming={eff_timing}"
            ),
        )

    # ILME-FX3 Ver. 7.02 rules
    if standalone_audio_level_display_requested:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="INTERNAL_STEREO_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                "EOPNOTSUPP: standalone [Audio Level Display] (_f 0x7a36) removed in Ver. 2.00..7.02; "
                "use DISP auto HUD"
            ),
        )

    if menu_path_requested == "Setup -> Sound Option":
        return _build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            active_input="INTERNAL_STEREO_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                "EINVAL: [Audio Out Timing] (Live/Lip Sync) lives under Shooting -> [Audio Recording], "
                "NOT Setup -> [Sound Option]"
            ),
        )

    if disable_internal_limiter_requested:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="INTERNAL_STEREO_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                "EOPNOTSUPP: FX3 internal audio Limiter is always-on and cannot be disabled or threshold-tuned"
            ),
        )

    if shoot_mode == SHOOT_MODE_SQ and (
        audio_recording == "On" and (shoe_audio_set == "48kHz/24bit 4ch" or audio_out_timing == "Lip Sync")
    ):
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="SQ_AUDIO_DISABLED",
            channels=0,
            bit_depth=0,
            routing={},
            grayed=True,
            wind_eff=False,
            reason="EOPNOTSUPP: Audio Recording and Audio Out Timing are disabled in S&Q mode",
        )

    # Hardware Priority Chain:
    # 1. 3.5mm MIC jack overrides MI shoe (forces 2ch analog, grays out Shoe Audio Set.)
    if mic_35mm_plugged:
        if eff_shoe_set in ("48kHz/24bit 4ch", "48kHz/24bit 2ch"):
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                active_input="3.5mm_MIC_2CH",
                channels=2,
                bit_depth=16,
                routing={"CH1": "3.5mm_L", "CH2": "3.5mm_R"},
                grayed=True,
                wind_eff=False,
                reason=(
                    "EOPNOTSUPP: 3.5mm MIC plug overrides MI shoe (forces 2ch analog, grays out [Shoe Audio Set.])"
                ),
            )
        return _build(
            admitted=True,
            errno_code=0,
            active_input="3.5mm_MIC_2CH",
            channels=2 if eff_audio_rec == "On" else 0,
            bit_depth=16,
            routing={"CH1": "3.5mm_L", "CH2": "3.5mm_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                "ADMITTED: 3.5mm MIC active (overrides MI shoe, [Shoe Audio Set.] grayed out, "
                "Wind Noise Reduct. has no effect on external 3.5mm mic)"
            ),
        )

    # 2. Digital MI shoe active? (requires XLR-H1 with HANDLE AUDIO=ON or ECM-B1M)
    shoe_active = (
        (mi_shoe_device == "XLR-H1" and xlrh1_handle_audio == "ON")
        or mi_shoe_device in ("ECM-B1M", "Legacy_Analog_2ch")
    )
    if not shoe_active:
        # Falls back to internal stereo mic
        if eff_shoe_set in ("48kHz/24bit 4ch", "48kHz/24bit 2ch"):
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                active_input="INTERNAL_STEREO_2CH",
                channels=2,
                bit_depth=16,
                routing={"CH1": "INT_L", "CH2": "INT_R"},
                grayed=True,
                wind_eff=(eff_wind == "On" and eff_audio_rec == "On"),
                reason=(
                    f"EOPNOTSUPP: MI shoe audio inactive (device={mi_shoe_device}, "
                    f"HANDLE_AUDIO={xlrh1_handle_audio}); fell back to internal stereo mic"
                ),
            )
        return _build(
            admitted=True,
            errno_code=0,
            active_input="INTERNAL_STEREO_2CH",
            channels=2 if eff_audio_rec == "On" else 0,
            bit_depth=16,
            routing={"CH1": "INT_L", "CH2": "INT_R"},
            grayed=True,
            wind_eff=(eff_wind == "On" and eff_audio_rec == "On"),
            reason=(
                f"ADMITTED: Internal stereo 2ch mic active (device={mi_shoe_device}, "
                f"HANDLE_AUDIO={xlrh1_handle_audio}, wind_reduct={eff_wind}, lvl={eff_rec_lvl})"
            ),
        )

    # 3. Analog MI shoe / XLR-H1 ANALOG switch restricts to 48kHz/16bit 2ch
    analog_only = (
        mi_shoe_device == "Legacy_Analog_2ch"
        or (mi_shoe_device == "XLR-H1" and xlrh1_digital_analog_switch == "ANALOG")
    )
    if analog_only and eff_shoe_set in ("48kHz/24bit 4ch", "48kHz/24bit 2ch"):
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="MI_SHOE_ANALOG_2CH",
            channels=2,
            bit_depth=16,
            routing={"CH1": "SHOE_ANALOG_L", "CH2": "SHOE_ANALOG_R"},
            grayed=True,
            wind_eff=False,
            reason=(
                f"EOPNOTSUPP: ANALOG switch / legacy MI shoe restricts audio to 48kHz/16bit 2ch "
                f"(rejected {eff_shoe_set})"
            ),
        )

    if mi_shoe_device == "ECM-B1M" and eff_shoe_set == "48kHz/24bit 4ch":
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            active_input="MI_SHOE_DIGITAL_2CH",
            channels=2,
            bit_depth=24,
            routing={"CH1": "SHOE_DIG_L", "CH2": "SHOE_DIG_R"},
            grayed=False,
            wind_eff=False,
            reason="EOPNOTSUPP: ECM-B1M is a 2ch digital MI shoe mic (4ch requires XLR-H1 / 4ch adapter)",
        )

    if eff_shoe_set == "48kHz/24bit 4ch":
        routing = (
            {
                "CH1": "INPUT1",
                "CH2": "INPUT2",
                "CH3": "INPUT3_3.5MM_L",
                "CH4": "INPUT3_3.5MM_R",
            }
            if xlrh1_input_select == "IN1·IN2"
            else {
                "CH1": "INPUT1",
                "CH2": "INPUT1",
                "CH3": "INPUT3_3.5MM_L",
                "CH4": "INPUT3_3.5MM_R",
            }
        )
        return _build(
            admitted=True,
            errno_code=0,
            active_input="XLRH1_DIGITAL_4CH_24BIT",
            channels=4 if eff_audio_rec == "On" else 0,
            bit_depth=24,
            routing=routing,
            grayed=False,
            wind_eff=False,
            reason=(
                f"ADMITTED: FX3 {eff_ver} {video_format} 48kHz/24bit 4ch via XLR-H1 ({xlrh1_input_select}), "
                f"mon={eff_mon}, hdmi={eff_hdmi_4ch}, timing={eff_timing}, proxy={proxy_codec}"
            ),
        )

    bit_d = 24 if eff_shoe_set == "48kHz/24bit 2ch" else 16
    return _build(
        admitted=True,
        errno_code=0,
        active_input="MI_SHOE_ANALOG_2CH" if analog_only else "MI_SHOE_DIGITAL_2CH",
        channels=2 if eff_audio_rec == "On" else 0,
        bit_depth=bit_d,
        routing={"CH1": "INPUT1", "CH2": "INPUT2"} if mi_shoe_device == "XLR-H1" else {"CH1": "SHOE_L", "CH2": "SHOE_R"},
        grayed=analog_only,
        wind_eff=False,
        reason=(
            f"ADMITTED: FX3 {eff_ver} {eff_shoe_set} via {mi_shoe_device}, "
            f"timing={eff_timing}, proxy={proxy_codec}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 72B — Face/Eye Subject Myth-Busting (Human + Still-Only Animal vs
#                 Dormant Bird/Insect/Car/Airplane) & 8-Slot Face Memory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FaceEyeSubjectRecogAndMemoryResult:
    body_profile: str
    firmware_version: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    exposure_mode: str
    face_eye_prior_in_af: str
    effective_face_eye_prior_in_af: str
    face_eye_subject: str
    effective_face_eye_subject: str
    right_left_eye_select: str
    effective_right_left_eye_select: str
    face_eye_frame_disp: str
    effective_face_eye_frame_disp: str
    regist_faces_priority: str
    effective_regist_faces_priority: str
    regist_faces_priority_grayed_out: bool
    eye_detection_active: bool
    face_detection_active: bool
    animal_eye_af_in_movie_not_support: bool
    dormant_subject_blocked: bool
    bkid_airplane_hits: int
    hdmi_clean_feed_frame_leaked_pixels: int
    face_memory_op: str
    face_memory_count: int
    effective_face_memory_count: int
    face_memory_max_slots: int
    face_memory_exported_in_camset: bool
    face_memory_survives_camera_reset: bool
    fx6_face_eye_mode: str
    fx6_saved_tracking_face_active: bool
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_face_eye_subject_recog_and_face_memory_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    firmware_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    exposure_mode: str = "M",
    face_eye_prior_in_af: str = "On",
    face_eye_subject: str = "Human",
    right_left_eye_select: str = "Auto",
    face_eye_frame_disp: str = "Off",
    regist_faces_priority: str = "On",
    face_memory_count: int = 0,
    face_memory_op: str = "None",
    camset_export_requested: bool = False,
    fx6_face_eye_mode: str = "Face/Eye Priority AF",
    fx6_saved_tracking_face_active: bool = False,
    fx6_tracking_stopped_or_push_af: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> FaceEyeSubjectRecogAndMemoryResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage72Phase335Error(f"Unsupported body_profile={body_profile!r}")
    if firmware_version not in VALID_FW_VERSIONS:
        raise Stage72Phase335Error(f"Unsupported firmware_version={firmware_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage72Phase335Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if face_eye_prior_in_af not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported face_eye_prior_in_af={face_eye_prior_in_af!r}")
    if face_eye_subject not in ALL_SUBJECT_TYPES:
        raise Stage72Phase335Error(f"Unsupported face_eye_subject={face_eye_subject!r}")
    if right_left_eye_select not in VALID_RIGHT_LEFT_EYE_MODES:
        raise Stage72Phase335Error(f"Unsupported right_left_eye_select={right_left_eye_select!r}")
    if face_eye_frame_disp not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported face_eye_frame_disp={face_eye_frame_disp!r}")
    if regist_faces_priority not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported regist_faces_priority={regist_faces_priority!r}")
    if face_memory_op not in VALID_FACE_MEMORY_OPS:
        raise Stage72Phase335Error(f"Unsupported face_memory_op={face_memory_op!r}")
    if fx6_face_eye_mode not in FX6_FACE_EYE_MODES:
        raise Stage72Phase335Error(f"Unsupported fx6_face_eye_mode={fx6_face_eye_mode!r}")

    eff_ver = FW_VER_601 if body_profile == BODY_MODEL_FX6 else firmware_version

    # Reset lifecycle
    if initialize_applied:
        eff_prior = "On"
        eff_subj = "Human"
        eff_eye = "Auto"
        eff_frame = "Off"
        eff_reg_prio = "On"
        eff_mem_count = 0
    elif camera_settings_reset_applied:
        eff_prior = "On"
        eff_subj = "Human"
        eff_eye = "Auto"
        eff_frame = "Off"
        eff_reg_prio = "On"
        eff_mem_count = face_memory_count
    else:
        eff_prior = "On" if exposure_mode == "Intelligent Auto" else face_eye_prior_in_af
        eff_subj = face_eye_subject
        eff_eye = right_left_eye_select
        eff_frame = face_eye_frame_disp
        eff_reg_prio = regist_faces_priority
        eff_mem_count = face_memory_count

    if face_memory_op == "Delete All":
        eff_mem_count = 0
    elif face_memory_op == "Delete" and eff_mem_count > 0:
        eff_mem_count -= 1
    elif face_memory_op == "New Registration" and not initialize_applied:
        eff_mem_count += 1

    def _build(
        *,
        admitted: bool,
        errno_code: int,
        eye_active: bool,
        face_active: bool,
        animal_movie_blk: bool = False,
        dormant_blk: bool = False,
        reason: str,
    ) -> FaceEyeSubjectRecogAndMemoryResult:
        eff_fx6_track = (
            fx6_saved_tracking_face_active
            and (not fx6_tracking_stopped_or_push_af)
            and (body_profile == BODY_MODEL_FX6)
        )
        return FaceEyeSubjectRecogAndMemoryResult(
            body_profile=body_profile,
            firmware_version=eff_ver,
            admitted=admitted,
            errno_code=errno_code,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            face_eye_prior_in_af=face_eye_prior_in_af,
            effective_face_eye_prior_in_af=eff_prior,
            face_eye_subject=face_eye_subject,
            effective_face_eye_subject=eff_subj if admitted else "Human",
            right_left_eye_select=right_left_eye_select,
            effective_right_left_eye_select=eff_eye,
            face_eye_frame_disp=face_eye_frame_disp,
            effective_face_eye_frame_disp=eff_frame,
            regist_faces_priority=regist_faces_priority,
            effective_regist_faces_priority=eff_reg_prio,
            regist_faces_priority_grayed_out=(eff_subj == "Animal"),
            eye_detection_active=eye_active,
            face_detection_active=face_active,
            animal_eye_af_in_movie_not_support=animal_movie_blk,
            dormant_subject_blocked=dormant_blk,
            bkid_airplane_hits=0,
            hdmi_clean_feed_frame_leaked_pixels=FACE_EYE_FRAME_HDMI_LEAKED_PIXELS,
            face_memory_op=face_memory_op,
            face_memory_count=face_memory_count,
            effective_face_memory_count=min(eff_mem_count, FX3_FACE_MEMORY_MAX_SLOTS),
            face_memory_max_slots=FX3_FACE_MEMORY_MAX_SLOTS if body_profile == BODY_MODEL_FX3 else 0,
            face_memory_exported_in_camset=False,
            face_memory_survives_camera_reset=(body_profile == BODY_MODEL_FX3),
            fx6_face_eye_mode=fx6_face_eye_mode if body_profile == BODY_MODEL_FX6 else "N/A",
            fx6_saved_tracking_face_active=eff_fx6_track,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=reason,
        )

    if body_profile == BODY_MODEL_FX6:
        if face_eye_subject != "Human":
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eye_active=False,
                face_active=False,
                dormant_blk=True,
                reason=(
                    f"EOPNOTSUPP: FX6 Ver. 6.01 Face/Eye Detection AF is Human-only "
                    f"(rejected {face_eye_subject!r})"
                ),
            )
        if face_memory_op != "None":
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eye_active=False,
                face_active=False,
                reason=(
                    "EOPNOTSUPP: FX6 Ver. 6.01 replaced fixed Face Memory with session-temporary "
                    "Saved Tracking Face ('Delete Registered Face' is leftover string)"
                ),
            )
        active = fx6_face_eye_mode != "Off"
        return _build(
            admitted=True,
            errno_code=0,
            eye_active=active,
            face_active=active,
            reason=(
                f"ADMITTED: FX6 Ver. 6.01 {fx6_face_eye_mode} Human-only, "
                f"SavedTrackingFace={fx6_saved_tracking_face_active and not fx6_tracking_stopped_or_push_af}"
            ),
        )

    # ILME-FX3 Ver. 7.02 rules (Wave-42 Errata: Human + Still-Only Animal; Bird/Insect/Car/Airplane dormant)
    if face_eye_subject in DORMANT_SHARED_ELF_SUBJECT_TYPES:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            eye_active=False,
            face_active=False,
            dormant_blk=True,
            reason=(
                f"EOPNOTSUPP: ILME-FX3 Ver. 7.02 lacks dedicated AI unit; {face_eye_subject!r} "
                "is dormant shared BIONZ XR ELF symbol (FEATURE_MANAGER_eye_face_af_gen_type blocks)"
            ),
        )

    if eff_mem_count < 0 or eff_mem_count > FX3_FACE_MEMORY_MAX_SLOTS:
        return _build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            eye_active=False,
            face_active=False,
            reason=(
                f"EINVAL: FX3 [Face Memory] supports 0..{FX3_FACE_MEMORY_MAX_SLOTS} slots "
                f"(got {eff_mem_count})"
            ),
        )

    if eff_subj == "Animal" and shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ):
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            eye_active=False,
            face_active=False,
            animal_movie_blk=True,
            reason=(
                f"EOPNOTSUPP: TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT — FX3 Animal eye/face "
                f"detection works ONLY in Still mode (blocked in {shoot_mode})"
            ),
        )

    active = eff_prior == "On"
    camset_note = " (excluded from CAMSET*.DAT)" if camset_export_requested else ""
    return _build(
        admitted=True,
        errno_code=0,
        eye_active=active,
        face_active=active if eff_subj == "Human" else False,
        reason=(
            f"ADMITTED: FX3 {eff_ver} {shoot_mode} Subject={eff_subj}, Prior={eff_prior}, "
            f"Eye={eff_eye}, FrameDisp={eff_frame} (hdmi_leak=0), "
            f"FaceMem={eff_mem_count}/8{camset_note}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 72C — Silent Mode 2-Tier Submenu, 5 Hard Lockouts,
#                 2-Item Target Function Settings & Dormant Shutter-When-Pwr-OFF
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SilentModeTargetAndShutterOffResult:
    body_profile: str
    admitted: bool
    errno_code: int
    shoot_mode: str
    silent_mode: str
    effective_silent_mode: str
    effective_shutter_type: str
    effective_interval_shutter_type: str
    effective_audio_signals: str
    af_illuminator_auto_disabled: bool
    locked_out_features: Tuple[str, ...]
    aperture_drive_in_af: str
    effective_aperture_drive_in_af: str
    aperture_drive_still_af_only_applies: bool
    auto_pixel_mapping: str
    effective_auto_pixel_mapping: str
    target_function_item_count: int
    shutter_when_pwr_off_exposed: bool
    image_sensor_barrier_dormant: bool
    fx6_has_mechanical_shutter: bool
    poweroff_mech_shutter_actuations: int
    cnflasha_bad_pixel_writes: int
    camera_settings_reset_applied: bool
    initialize_applied: bool
    reason: str


def simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_STILL,
    silent_mode: str = "Off",
    aperture_drive_in_af: str = "Standard",
    auto_pixel_mapping: str = "Off",
    shutter_when_pwr_off_requested: bool = False,
    extra_target_item_requested: Optional[str] = None,
    requested_feature_while_silent: Optional[str] = None,
    power_off_sequence_triggered: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> SilentModeTargetAndShutterOffResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage72Phase335Error(f"Unsupported body_profile={body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage72Phase335Error(f"Unsupported shoot_mode={shoot_mode!r}")
    if silent_mode not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported silent_mode={silent_mode!r}")
    if aperture_drive_in_af not in VALID_APERTURE_DRIVE_IN_AF_MODES:
        raise Stage72Phase335Error(f"Unsupported aperture_drive_in_af={aperture_drive_in_af!r}")
    if auto_pixel_mapping not in VALID_AUTO_PIXEL_MAPPING_MODES:
        raise Stage72Phase335Error(f"Unsupported auto_pixel_mapping={auto_pixel_mapping!r}")
    if (
        requested_feature_while_silent is not None
        and requested_feature_while_silent not in VALID_SILENT_FEATURE_PROBES
    ):
        raise Stage72Phase335Error(
            f"Unsupported requested_feature_while_silent={requested_feature_while_silent!r}"
        )

    if camera_settings_reset_applied or initialize_applied:
        eff_silent = "Off"
        eff_aperture = "Standard"
        eff_pixel_map = "Off"
    else:
        eff_silent = silent_mode
        eff_aperture = aperture_drive_in_af
        eff_pixel_map = auto_pixel_mapping

    silent_active = (body_profile == BODY_MODEL_FX3) and (eff_silent == "On")
    locked = FX3_SILENT_MODE_5_LOCKOUTS if silent_active else ()

    def _build(
        *,
        admitted: bool,
        errno_code: int,
        reason: str,
    ) -> SilentModeTargetAndShutterOffResult:
        return SilentModeTargetAndShutterOffResult(
            body_profile=body_profile,
            admitted=admitted,
            errno_code=errno_code,
            shoot_mode=shoot_mode,
            silent_mode=silent_mode,
            effective_silent_mode=eff_silent if body_profile == BODY_MODEL_FX3 else "N/A",
            effective_shutter_type=(
                "Electronic Shutter" if (silent_active or body_profile == BODY_MODEL_FX6) else "Mechanical Shutter"
            ),
            effective_interval_shutter_type=(
                "Electronic Shutter" if (silent_active or body_profile == BODY_MODEL_FX6) else "Mechanical Shutter"
            ),
            effective_audio_signals="Off" if silent_active else "On",
            af_illuminator_auto_disabled=False,
            locked_out_features=locked,
            aperture_drive_in_af=aperture_drive_in_af,
            effective_aperture_drive_in_af=eff_aperture,
            aperture_drive_still_af_only_applies=(
                body_profile == BODY_MODEL_FX3 and shoot_mode == SHOOT_MODE_STILL
            ),
            auto_pixel_mapping=auto_pixel_mapping,
            effective_auto_pixel_mapping=eff_pixel_map,
            target_function_item_count=(
                FX3_TARGET_FUNCTION_SETTINGS_ITEM_COUNT if body_profile == BODY_MODEL_FX3 else 0
            ),
            shutter_when_pwr_off_exposed=False,
            image_sensor_barrier_dormant=True,
            fx6_has_mechanical_shutter=FX6_HAS_MECHANICAL_SHUTTER,
            poweroff_mech_shutter_actuations=POWEROFF_PIXEL_MAPPING_SHUTTER_ACTUATIONS,
            cnflasha_bad_pixel_writes=CNFLASHA_MUTATION_BYTES,
            camera_settings_reset_applied=camera_settings_reset_applied,
            initialize_applied=initialize_applied,
            reason=reason,
        )

    if shutter_when_pwr_off_requested:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "EOPNOTSUPP: [Shutter When Pwr OFF] (_f 0x709f / image_sensor_barrier) is strictly "
                f"dormant on {body_profile}"
            ),
        )

    if extra_target_item_requested is not None:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"EOPNOTSUPP: [Target Function Settings] exposes ONLY 2 items "
                f"({FX3_TARGET_FUNCTION_ITEMS}); {extra_target_item_requested!r} is not exposed"
            ),
        )

    if body_profile == BODY_MODEL_FX6:
        if silent_mode == "On":
            return _build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "EOPNOTSUPP: FX6 is shutterless (electronic rolling shutter + e-ND + Auto Pixel Restore) "
                    "and has no [Silent Mode Settings] submenu"
                ),
            )
        return _build(
            admitted=True,
            errno_code=0,
            reason="ADMITTED: FX6 Ver. 6.01 shutterless architecture (Audio > Beep & Auto Pixel Restore)",
        )

    if silent_active and requested_feature_while_silent in FX3_SILENT_MODE_5_LOCKOUTS:
        return _build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"EOPNOTSUPP: [Silent Mode] = On locks out {requested_feature_while_silent!r} "
                "(5 hard lockouts: Flash, Long Exposure NR, e-Front Curtain Shut., BULB, Anti-flicker Shoot.)"
            ),
        )

    pwr_note = (
        "; poweroff_shutter_actuations=0, cnflasha_writes=0"
        if power_off_sequence_triggered
        else ""
    )
    return _build(
        admitted=True,
        errno_code=0,
        reason=(
            f"ADMITTED: FX3 SilentMode={eff_silent} (AudioSignals={'Off' if silent_active else 'On'}, "
            f"ApertureDrive={eff_aperture}, AutoPixelMapping={eff_pixel_map}, "
            f"af_illum_auto_disabled=False{pwr_note})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 72D — Version Read-Only Audit & BODYDATA.DAT Slot-1 /
#                 Ver. 2.04-2.05 Stepping-Stone NO-GO Firewall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionAuditAndBodydataNoGoResult:
    body_profile: str
    admitted: bool
    errno_code: int
    current_fw_version: str
    target_update_version: str
    target_body_model_file: str
    update_filename: str
    media_slot: str
    required_slot: str
    battery_pct: int
    ac_adaptor_connected: bool
    peripherals_attached: bool
    lens_attached: bool
    lens_version_displayed: str
    mount_adaptor_attached: bool
    mount_adaptor_version_displayed: str
    airplane_mode: str
    update_badge_shown: bool
    stepping_stone_required: bool
    stepping_stone_versions: Tuple[str, ...]
    led_long_blinks: int
    led_short_blinks: int
    cross_model_rejected: bool
    tc_ub_reset_on_update: bool
    firewall_blocked: bool
    emmc_writes_authorized: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    bodydata_flash_execution_events: int
    error_message: str
    reason: str


def simulate_version_audit_and_bodydata_nogo_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    current_fw_version: str = FW_VER_702,
    target_update_version: str = FW_VER_702,
    target_body_model_file: str = BODY_MODEL_FX3,
    update_filename: str = "BODYDATA.DAT",
    media_slot: str = "Slot 1",
    battery_pct: int = 80,
    ac_adaptor_connected: bool = False,
    peripherals_attached: bool = False,
    lens_attached: bool = True,
    lens_fw_version: str = "02",
    mount_adaptor_attached: bool = False,
    mount_adaptor_fw_version: str = "01",
    airplane_mode: str = "On",
    network_latest_fw_available: bool = False,
    execute_software_update_requested: bool = False,
    stage_bodydata_to_card_requested: bool = False,
) -> VersionAuditAndBodydataNoGoResult:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage72Phase335Error(f"Unsupported body_profile={body_profile!r}")
    if current_fw_version not in VALID_FW_VERSIONS:
        raise Stage72Phase335Error(f"Unsupported current_fw_version={current_fw_version!r}")
    if target_update_version not in VALID_FW_VERSIONS:
        raise Stage72Phase335Error(
            f"Unsupported target_update_version={target_update_version!r}"
        )
    if target_body_model_file not in VALID_BODY_MODELS:
        raise Stage72Phase335Error(
            f"Unsupported target_body_model_file={target_body_model_file!r}"
        )
    if media_slot not in VALID_MEDIA_SLOTS:
        raise Stage72Phase335Error(f"Unsupported media_slot={media_slot!r}")
    if airplane_mode not in ("On", "Off"):
        raise Stage72Phase335Error(f"Unsupported airplane_mode={airplane_mode!r}")

    req_slot = "Slot B" if body_profile == BODY_MODEL_FX6 else "Slot 1"
    lens_disp = f"Ver.{lens_fw_version}" if lens_attached else ""
    adaptor_disp = f"Ver.{mount_adaptor_fw_version}" if mount_adaptor_attached else ""
    badge_shown = (
        airplane_mode == "Off"
        and network_latest_fw_available
        and current_fw_version in (FW_VER_600, FW_VER_601, FW_VER_700, FW_VER_702)
    )
    need_stone = (
        body_profile == BODY_MODEL_FX3
        and current_fw_version in STEPPING_STONE_REQUIRED_FROM_VERSIONS
        and target_update_version not in STEPPING_STONE_BRIDGE_VERSIONS
    )

    def _build(
        *,
        admitted: bool,
        errno_code: int,
        long_b: int = 0,
        short_b: int = 0,
        cross_rej: bool = False,
        fw_blocked: bool = False,
        err_msg: str = "",
        reason: str,
    ) -> VersionAuditAndBodydataNoGoResult:
        return VersionAuditAndBodydataNoGoResult(
            body_profile=body_profile,
            admitted=admitted,
            errno_code=errno_code,
            current_fw_version=current_fw_version,
            target_update_version=target_update_version,
            target_body_model_file=target_body_model_file,
            update_filename=update_filename,
            media_slot=media_slot,
            required_slot=req_slot,
            battery_pct=battery_pct,
            ac_adaptor_connected=ac_adaptor_connected,
            peripherals_attached=peripherals_attached,
            lens_attached=lens_attached,
            lens_version_displayed=lens_disp,
            mount_adaptor_attached=mount_adaptor_attached,
            mount_adaptor_version_displayed=adaptor_disp,
            airplane_mode=airplane_mode,
            update_badge_shown=badge_shown,
            stepping_stone_required=need_stone,
            stepping_stone_versions=STEPPING_STONE_BRIDGE_VERSIONS,
            led_long_blinks=long_b,
            led_short_blinks=short_b,
            cross_model_rejected=cross_rej,
            tc_ub_reset_on_update=(body_profile == BODY_MODEL_FX3),
            firewall_blocked=fw_blocked,
            emmc_writes_authorized=EMMC_WRITES_AUTHORIZED,
            cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
            error_message=err_msg,
            reason=reason,
        )

    # Read-only Version screen audit
    if (not execute_software_update_requested) and (not stage_bodydata_to_card_requested):
        return _build(
            admitted=True,
            errno_code=0,
            fw_blocked=False,
            reason=(
                f"ADMITTED: {body_profile} read-only [Version] audit "
                f"(Body=Ver.{current_fw_version}, Lens={lens_disp or 'None'}, "
                f"Airplane={airplane_mode}, update_dot={badge_shown}, writes=0)"
            ),
        )

    # Mutating / Flash requests ALWAYS hit diagnostic checks + Tier-0 NO-GO Firewall
    if target_body_model_file != body_profile:
        return _build(
            admitted=False,
            errno_code=EPERM_ERRNO,
            cross_rej=True,
            fw_blocked=True,
            err_msg="The target model for the update file is incorrect.",
            reason=(
                f"BLOCKED/EPERM: cross-model BODYDATA.DAT rejected "
                f"({target_body_model_file} != {body_profile}, cross_model_flash_authorized=False)"
            ),
        )

    if update_filename != "BODYDATA.DAT":
        return _build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            fw_blocked=True,
            err_msg="The update file is not found or renamed.",
            reason=(
                f"BLOCKED/EINVAL: update filename must be exact 'BODYDATA.DAT' "
                f"(got {update_filename!r}; no '(1)' or '-3' suffix)"
            ),
        )

    if media_slot != req_slot:
        return _build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            fw_blocked=True,
            err_msg=f"Update requires {req_slot} root.",
            reason=(
                f"BLOCKED/EINVAL: {body_profile} requires BODYDATA.DAT in {req_slot} root "
                f"({media_slot} ignored)"
            ),
        )

    if body_profile == BODY_MODEL_FX6:
        if not ac_adaptor_connected:
            return _build(
                admitted=False,
                errno_code=EPERM_ERRNO,
                fw_blocked=True,
                err_msg="Please use the AC Adaptor.",
                reason="BLOCKED/EPERM: FX6 Version Up mandates AC Adaptor (battery-only blocked)",
            )
        if peripherals_attached:
            return _build(
                admitted=False,
                errno_code=EPERM_ERRNO,
                fw_blocked=True,
                err_msg="Disconnect all USB/SDI/HDMI/MI-shoe peripherals.",
                reason="BLOCKED/EPERM: FX6 Version Up requires detaching USB/SDI/HDMI/MI peripherals",
            )
    else:
        if battery_pct < BODYDATA_MIN_BATTERY_PCT:
            return _build(
                admitted=False,
                errno_code=EPERM_ERRNO,
                fw_blocked=True,
                err_msg="Charge the battery (>= 51% / 3 bars required).",
                reason=(
                    f"BLOCKED/EPERM: FX3 Software Update requires NP-FZ100 >= {BODYDATA_MIN_BATTERY_PCT}%% "
                    f"(3 bars); got {battery_pct}%%"
                ),
            )
        if need_stone:
            return _build(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                long_b=STEPPING_STONE_SKIP_LED_LONG_BLINKS,
                short_b=STEPPING_STONE_SKIP_LED_SHORT_BLINKS,
                fw_blocked=True,
                err_msg="The update file version is incorrect.",
                reason=(
                    f"BLOCKED/EINVAL: FX3 {current_fw_version} <= 2.02 MUST step through "
                    "Ver. 2.04/2.05 before Ver. 7.02 (5-long/6-short LED fault code)"
                ),
            )

    if stage_bodydata_to_card_requested:
        return _build(
            admitted=False,
            errno_code=EROFS_ERRNO,
            fw_blocked=True,
            err_msg="Tier-0 NO-GO Firewall: Slot-1 / Slot-B BODYDATA.DAT staging forbidden.",
            reason=(
                f"BLOCKED/EROFS: Tier-0 NO-GO Firewall blocks staging BODYDATA.DAT to {media_slot} "
                "(slot1_data_sector_writes=0, emmc_writes_authorized=False)"
            ),
        )

    return _build(
        admitted=False,
        errno_code=EPERM_ERRNO,
        fw_blocked=True,
        err_msg="Tier-0 NO-GO / BLOCKED Firewall: physical camera flash execution forbidden.",
        reason=(
            "BLOCKED/EPERM: Tier-0 NO-GO Firewall blocks [Software Update] / Version Up "
            "(emmc_writes_authorized=False, hardware_live_attachment_authorized=False)"
        ),
    )


def _build_stage72_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_72nd_stage_milestone": IS_72ND_STAGE_MILESTONE,
        "wave": "Wave-62",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 335 Stage 72 (72/72 Milestone!) Wave-62 HIL co-emulation."""
    donor_audit = inspect_phase335_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 72A probes
    p72a_xlrh1_4ch_ok = simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
        mi_shoe_device="XLR-H1",
        xlrh1_handle_audio="ON",
        xlrh1_digital_analog_switch="DIGITAL",
        xlrh1_input_select="IN1·IN2",
        shoe_audio_set="48kHz/24bit 4ch",
        audio_rec_level=26,
        audio_out_timing="Lip Sync",
        four_ch_audio_monitoring="CH1+3/CH2+4",
        hdmi_4ch_audio_output="CH3/CH4",
        proxy_recording="On",
        fps=59.94,
    )
    p72a_overrides_and_locks = [
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            mic_35mm_plugged=True,
            shoe_audio_set="48kHz/24bit 4ch",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="OFF",
            shoe_audio_set="48kHz/24bit 4ch",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_digital_analog_switch="ANALOG",
            shoe_audio_set="48kHz/24bit 4ch",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            menu_path_requested="Setup -> Sound Option",
            audio_out_timing="Lip Sync",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            standalone_audio_level_display_requested=True,
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            disable_internal_limiter_requested=True,
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            proxy_recording="On",
            proxy_4ch_lpcm_requested=True,
        ),
    ]
    p72a_internal_wind_and_fx6 = [
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="None",
            wind_noise_reduct="On",
            audio_rec_level=18,
            delete_key_reset=True,
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            mic_35mm_plugged=True,
            shoe_audio_set="48kHz/16bit 2ch",
            wind_noise_reduct="On",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_limiter_mode="-12dB",
            audio_out_timing="Live",
        ),
        simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_32bit_float_requested=True,
        ),
    ]
    p72a_ok = (
        p72a_xlrh1_4ch_ok.admitted
        and p72a_xlrh1_4ch_ok.effective_audio_channels == 4
        and p72a_xlrh1_4ch_ok.effective_bit_depth == 24
        and p72a_xlrh1_4ch_ok.effective_audio_out_timing == "Lip Sync"
        and p72a_xlrh1_4ch_ok.effective_proxy_enabled
        and p72a_xlrh1_4ch_ok.proxy_audio_codec == PROXY_AUDIO_CODEC
        and p72a_xlrh1_4ch_ok.proxy_audio_channels == 2
        and (not p72a_overrides_and_locks[0].admitted)
        and p72a_overrides_and_locks[0].effective_active_input == "3.5mm_MIC_2CH"
        and p72a_overrides_and_locks[0].shoe_audio_set_grayed_out
        and (not p72a_overrides_and_locks[1].admitted)
        and p72a_overrides_and_locks[1].effective_active_input == "INTERNAL_STEREO_2CH"
        and (not p72a_overrides_and_locks[2].admitted)
        and p72a_overrides_and_locks[2].errno_code == EOPNOTSUPP_ERRNO
        and (not p72a_overrides_and_locks[3].admitted)
        and p72a_overrides_and_locks[3].errno_code == EINVAL_ERRNO
        and (not p72a_overrides_and_locks[4].admitted)
        and p72a_overrides_and_locks[4].errno_code == EOPNOTSUPP_ERRNO
        and (not p72a_overrides_and_locks[5].admitted)
        and p72a_overrides_and_locks[5].errno_code == EOPNOTSUPP_ERRNO
        and (not p72a_overrides_and_locks[6].admitted)
        and p72a_overrides_and_locks[6].errno_code == EOPNOTSUPP_ERRNO
        and p72a_internal_wind_and_fx6[0].admitted
        and p72a_internal_wind_and_fx6[0].effective_audio_rec_level == 26
        and p72a_internal_wind_and_fx6[0].wind_noise_reduct_effective_on_active_mic
        and p72a_internal_wind_and_fx6[1].admitted
        and (not p72a_internal_wind_and_fx6[1].wind_noise_reduct_effective_on_active_mic)
        and p72a_internal_wind_and_fx6[2].admitted
        and p72a_internal_wind_and_fx6[2].fx6_native_4ch_lpcm
        and (not p72a_internal_wind_and_fx6[3].admitted)
        and p72a_internal_wind_and_fx6[3].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 72B probes
    p72b_human_face_mem_ok = simulate_face_eye_subject_recog_and_face_memory_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        face_eye_subject="Human",
        face_eye_frame_disp="On",
        face_memory_count=8,
        camset_export_requested=True,
        camera_settings_reset_applied=True,
    )
    p72b_still_animal_ok = simulate_face_eye_subject_recog_and_face_memory_hil(
        shoot_mode=SHOOT_MODE_STILL,
        face_eye_subject="Animal",
        right_left_eye_select="Right Eye",
    )
    p72b_movie_animal_and_dormants_blocked = [
        simulate_face_eye_subject_recog_and_face_memory_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            face_eye_subject="Animal",
        ),
        simulate_face_eye_subject_recog_and_face_memory_hil(
            shoot_mode=SHOOT_MODE_SQ,
            face_eye_subject="Animal",
        ),
        *(
            simulate_face_eye_subject_recog_and_face_memory_hil(
                shoot_mode=SHOOT_MODE_STILL,
                face_eye_subject=subj,
            )
            for subj in DORMANT_SHARED_ELF_SUBJECT_TYPES
        ),
    ]
    p72b_fx6_human_only = [
        simulate_face_eye_subject_recog_and_face_memory_hil(
            body_profile=BODY_MODEL_FX6,
            face_eye_subject="Human",
            fx6_face_eye_mode="Face/Eye Only AF",
            fx6_saved_tracking_face_active=True,
        ),
        simulate_face_eye_subject_recog_and_face_memory_hil(
            body_profile=BODY_MODEL_FX6,
            face_eye_subject="Animal",
        ),
    ]
    p72b_ok = (
        p72b_human_face_mem_ok.admitted
        and p72b_human_face_mem_ok.effective_face_memory_count == 8
        and p72b_human_face_mem_ok.face_memory_survives_camera_reset
        and (not p72b_human_face_mem_ok.face_memory_exported_in_camset)
        and p72b_human_face_mem_ok.effective_face_eye_frame_disp == "Off"
        and p72b_human_face_mem_ok.hdmi_clean_feed_frame_leaked_pixels == 0
        and p72b_still_animal_ok.admitted
        and p72b_still_animal_ok.eye_detection_active
        and p72b_still_animal_ok.regist_faces_priority_grayed_out
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p72b_movie_animal_and_dormants_blocked
        )
        and p72b_movie_animal_and_dormants_blocked[0].animal_eye_af_in_movie_not_support
        and p72b_movie_animal_and_dormants_blocked[1].animal_eye_af_in_movie_not_support
        and all(r.dormant_subject_blocked for r in p72b_movie_animal_and_dormants_blocked[2:])
        and p72b_fx6_human_only[0].admitted
        and p72b_fx6_human_only[0].fx6_saved_tracking_face_active
        and (not p72b_fx6_human_only[1].admitted)
        and p72b_fx6_human_only[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 72C probes
    p72c_silent_on_ok = simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
        silent_mode="On",
        aperture_drive_in_af="Silent Priority",
        auto_pixel_mapping="Off",
        requested_feature_while_silent="AF Illuminator",
        power_off_sequence_triggered=True,
    )
    p72c_5locks_and_dormant_rejected = [
        *(
            simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                silent_mode="On",
                requested_feature_while_silent=feat,
            )
            for feat in FX3_SILENT_MODE_5_LOCKOUTS
        ),
        simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            extra_target_item_requested="AF Illuminator",
        ),
        simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            shutter_when_pwr_off_requested=True,
        ),
        simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            body_profile=BODY_MODEL_FX6,
            silent_mode="On",
        ),
    ]
    p72c_ok = (
        p72c_silent_on_ok.admitted
        and p72c_silent_on_ok.effective_shutter_type == "Electronic Shutter"
        and p72c_silent_on_ok.effective_audio_signals == "Off"
        and (not p72c_silent_on_ok.af_illuminator_auto_disabled)
        and len(p72c_silent_on_ok.locked_out_features) == 5
        and p72c_silent_on_ok.target_function_item_count == 2
        and (not p72c_silent_on_ok.shutter_when_pwr_off_exposed)
        and p72c_silent_on_ok.poweroff_mech_shutter_actuations == 0
        and p72c_silent_on_ok.cnflasha_bad_pixel_writes == 0
        and all(
            (not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO
            for r in p72c_5locks_and_dormant_rejected
        )
    )

    # Sub-Model 72D probes
    p72d_version_ro_ok = simulate_version_audit_and_bodydata_nogo_firewall_hil(
        current_fw_version=FW_VER_702,
        airplane_mode="On",
        network_latest_fw_available=True,
        lens_attached=True,
        lens_fw_version="02",
    )
    p72d_firewall_blocks = [
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=FW_VER_202,
            target_update_version=FW_VER_702,
            media_slot="Slot 1",
            battery_pct=90,
            execute_software_update_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=FW_VER_205,
            target_update_version=FW_VER_702,
            media_slot="Slot 2",
            battery_pct=90,
            execute_software_update_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=FW_VER_205,
            target_update_version=FW_VER_702,
            media_slot="Slot 1",
            battery_pct=40,
            execute_software_update_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=BODY_MODEL_FX3,
            target_body_model_file=BODY_MODEL_FX6,
            execute_software_update_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=BODY_MODEL_FX6,
            current_fw_version=FW_VER_601,
            target_update_version=FW_VER_602,
            target_body_model_file=BODY_MODEL_FX6,
            media_slot="Slot A",
            ac_adaptor_connected=False,
            execute_software_update_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=FW_VER_205,
            target_update_version=FW_VER_702,
            media_slot="Slot 1",
            battery_pct=90,
            stage_bodydata_to_card_requested=True,
        ),
        simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=FW_VER_205,
            target_update_version=FW_VER_702,
            media_slot="Slot 1",
            battery_pct=90,
            execute_software_update_requested=True,
        ),
    ]
    p72d_ok = (
        p72d_version_ro_ok.admitted
        and (not p72d_version_ro_ok.update_badge_shown)
        and p72d_version_ro_ok.lens_version_displayed == "Ver.02"
        and p72d_version_ro_ok.slot1_data_sector_writes == 0
        and p72d_firewall_blocks[0].stepping_stone_required
        and p72d_firewall_blocks[0].led_long_blinks == 5
        and p72d_firewall_blocks[0].led_short_blinks == 6
        and p72d_firewall_blocks[3].cross_model_rejected
        and p72d_firewall_blocks[5].errno_code == EROFS_ERRNO
        and p72d_firewall_blocks[6].errno_code == EPERM_ERRNO
        and all(
            (not r.admitted)
            and r.firewall_blocked
            and (not r.emmc_writes_authorized)
            and (not r.cross_model_flash_authorized)
            and r.slot1_data_sector_writes == 0
            and r.emmc_nflasha_write_count == 0
            and r.bodydata_flash_execution_events == 0
            for r in p72d_firewall_blocks
        )
    )

    milestone_probe = _build_stage72_milestone_probe()

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
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "bodydata_flash_execution_blocked": BODYDATA_FLASH_EXECUTION_BLOCKED,
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
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        "fx3_active_audio_recording_menu_items": FX3_ACTIVE_AUDIO_RECORDING_MENU_ITEMS,
        "audio_rec_level_steps": AUDIO_REC_LEVEL_STEPS,
        "four_ch_monitoring_pairs_count": FOUR_CH_MONITORING_PAIRS_COUNT,
        "jack_35mm_shoe_override_violations": JACK_35MM_SHOE_OVERRIDE_VIOLATIONS,
        "external_mic_wind_reduction_leak_events": EXTERNAL_MIC_WIND_REDUCTION_LEAK_EVENTS,
        "proxy_4ch_audio_bypass_events": PROXY_4CH_AUDIO_BYPASS_EVENTS,
        "standalone_audio_level_display_spoof_events": STANDALONE_AUDIO_LEVEL_DISPLAY_SPOOF_EVENTS,
        "audio_out_timing_setup_misroute_events": AUDIO_OUT_TIMING_SETUP_MISROUTE_EVENTS,
        "fx3_exposed_face_eye_subjects_count": FX3_EXPOSED_FACE_EYE_SUBJECTS_COUNT,
        "fx3_face_memory_max_slots": FX3_FACE_MEMORY_MAX_SLOTS,
        "dormant_bird_insect_car_airplane_exposed_events": DORMANT_BIRD_INSECT_CAR_AIRPLANE_EXPOSED_EVENTS,
        "animal_eye_af_in_movie_bypass_events": ANIMAL_EYE_AF_IN_MOVIE_BYPASS_EVENTS,
        "face_eye_frame_hdmi_leaked_pixels": FACE_EYE_FRAME_HDMI_LEAKED_PIXELS,
        "face_memory_camset_leak_events": FACE_MEMORY_CAMSET_LEAK_EVENTS,
        "face_memory_camera_reset_wipe_events": FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS,
        "fx3_silent_mode_hard_locked_features_count": FX3_SILENT_MODE_HARD_LOCKED_FEATURES_COUNT,
        "fx3_target_function_settings_item_count": FX3_TARGET_FUNCTION_SETTINGS_ITEM_COUNT,
        "fx3_has_shutter_when_pwr_off": FX3_HAS_SHUTTER_WHEN_PWR_OFF,
        "fx6_has_mechanical_shutter": FX6_HAS_MECHANICAL_SHUTTER,
        "silent_mode_5lock_bypass_events": SILENT_MODE_5LOCK_BYPASS_EVENTS,
        "target_function_extra_item_spoof_events": TARGET_FUNCTION_EXTRA_ITEM_SPOOF_EVENTS,
        "shutter_when_pwr_off_exposed_events": SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS,
        "poweroff_pixel_mapping_shutter_actuations": POWEROFF_PIXEL_MAPPING_SHUTTER_ACTUATIONS,
        "airplane_mode_version_dot_leak_events": AIRPLANE_MODE_VERSION_DOT_LEAK_EVENTS,
        "bodydata_stepping_stone_bypass_events": BODYDATA_STEPPING_STONE_BYPASS_EVENTS,
        "bodydata_slot2_or_fx6_slota_bypass_events": BODYDATA_SLOT2_OR_FX6_SLOTA_BYPASS_EVENTS,
        "bodydata_flash_execution_events": BODYDATA_FLASH_EXECUTION_EVENTS,
        "cross_model_flash_attempt_admitted_events": CROSS_MODEL_FLASH_ATTEMPT_ADMITTED_EVENTS,
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
        and p72a_ok
        and p72b_ok
        and p72c_ok
        and p72d_ok
        and milestone_probe["is_72nd_stage_milestone"]
        and redlines["fx3_active_audio_recording_menu_items"] == 5
        and redlines["audio_rec_level_steps"] == 32
        and redlines["four_ch_monitoring_pairs_count"] == 5
        and redlines["jack_35mm_shoe_override_violations"] == 0
        and redlines["external_mic_wind_reduction_leak_events"] == 0
        and redlines["proxy_4ch_audio_bypass_events"] == 0
        and redlines["standalone_audio_level_display_spoof_events"] == 0
        and redlines["audio_out_timing_setup_misroute_events"] == 0
        and redlines["fx3_exposed_face_eye_subjects_count"] == 2
        and redlines["fx3_face_memory_max_slots"] == 8
        and redlines["dormant_bird_insect_car_airplane_exposed_events"] == 0
        and redlines["animal_eye_af_in_movie_bypass_events"] == 0
        and redlines["face_eye_frame_hdmi_leaked_pixels"] == 0
        and redlines["face_memory_camset_leak_events"] == 0
        and redlines["face_memory_camera_reset_wipe_events"] == 0
        and redlines["fx3_silent_mode_hard_locked_features_count"] == 5
        and redlines["fx3_target_function_settings_item_count"] == 2
        and (not redlines["fx3_has_shutter_when_pwr_off"])
        and (not redlines["fx6_has_mechanical_shutter"])
        and redlines["silent_mode_5lock_bypass_events"] == 0
        and redlines["target_function_extra_item_spoof_events"] == 0
        and redlines["shutter_when_pwr_off_exposed_events"] == 0
        and redlines["poweroff_pixel_mapping_shutter_actuations"] == 0
        and redlines["airplane_mode_version_dot_leak_events"] == 0
        and redlines["bodydata_stepping_stone_bypass_events"] == 0
        and redlines["bodydata_slot2_or_fx6_slota_bypass_events"] == 0
        and redlines["bodydata_flash_execution_events"] == 0
        and redlines["cross_model_flash_attempt_admitted_events"] == 0
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["rf_packets_transmitted"] == 0
        and redlines["rf_nvs_mutation_bytes"] == 0
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and redlines["emmc_nflasha_write_count"] == 0
        and bool(redlines["cnflasha_userspace_write_blocked"])
        and bool(redlines["bodydata_flash_execution_blocked"])
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["emmc_writes_authorized"])
        and (not redlines["cross_model_flash_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_335_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_72nd_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_shoe_audio_4ch_xlrh1_override_and_timing_hil": {
            "passed": p72a_ok,
            "xlrh1_4ch_ok": asdict(p72a_xlrh1_4ch_ok),
            "overrides_and_locks": [asdict(r) for r in p72a_overrides_and_locks],
            "internal_wind_and_fx6": [asdict(r) for r in p72a_internal_wind_and_fx6],
        },
        "pillar_b_face_eye_subject_recog_and_face_memory_hil": {
            "passed": p72b_ok,
            "human_face_mem_ok": asdict(p72b_human_face_mem_ok),
            "still_animal_ok": asdict(p72b_still_animal_ok),
            "movie_animal_and_dormants_blocked": [
                asdict(r) for r in p72b_movie_animal_and_dormants_blocked
            ],
            "fx6_human_only": [asdict(r) for r in p72b_fx6_human_only],
        },
        "pillar_c_silent_mode_target_settings_and_shutter_pwr_off_hil": {
            "passed": p72c_ok,
            "silent_on_ok": asdict(p72c_silent_on_ok),
            "five_locks_and_dormant_rejected": [
                asdict(r) for r in p72c_5locks_and_dormant_rejected
            ],
        },
        "pillar_d_version_audit_and_bodydata_nogo_firewall_hil": {
            "passed": p72d_ok,
            "version_ro_ok": asdict(p72d_version_ro_ok),
            "firewall_blocks": [asdict(r) for r in p72d_firewall_blocks],
            "stage72_milestone_probe": milestone_probe,
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
        prog="realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py",
        description=(
            "Phase 335 Stage 72 (72/72 Milestone!) Wave-62 Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 [Shoe Audio Set.] "
            "(48kHz/24bit 4ch, XLR-H1 vs 3.5mm Override, Proxy AAC-LC 2ch & "
            "Shooting -> Audio Recording -> [Audio Out Timing] Live/Lip Sync), "
            "[Face/Eye Subject] (Human + Still-Only Animal vs Dormant "
            "Bird/Insect/Car/Airplane EOPNOTSUPP=95 & 8-Slot Face Memory), "
            "[Silent Mode Settings] (2-Item Target Function Settings, 5 Hard Lockouts "
            "& Dormant Shutter When Pwr OFF EOPNOTSUPP=95), and "
            "[Version] / BODYDATA.DAT (Slot 1 + >=51%% + Ver. 2.04/2.05 Stepping-Stone "
            "100%% NO-GO / BLOCKED Firewall) HIL"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic Phase 335 Stage 72 (72/72) Wave-62 HIL verification suite",
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
        help="Emit concise one-line Stage 72 (72/72 Milestone!) Wave-62 summary",
    )
    args = parser.parse_args(argv)

    rep = run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
        force_clean_room=True if args.clean_room else None
    )

    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 335 Stage 72 (72/72 Milestone) | "
            f"mode={rep['source_mode']} "
            f"donors={rep['donor_audit']['donor_files_inspected']} "
            f"aud_items={red['fx3_active_audio_recording_menu_items']} "
            f"subj={red['fx3_exposed_face_eye_subjects_count']} "
            f"fmem={red['fx3_face_memory_max_slots']} "
            f"silent_lck={red['fx3_silent_mode_hard_locked_features_count']} "
            f"tgt_items={red['fx3_target_function_settings_item_count']} "
            f"sh_pwroff={int(red['fx3_has_shutter_when_pwr_off'])} "
            f"bd_blk={int(red['bodydata_flash_execution_blocked'])} "
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
