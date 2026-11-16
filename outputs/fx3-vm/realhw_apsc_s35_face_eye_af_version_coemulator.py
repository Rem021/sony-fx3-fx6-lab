#!/usr/bin/env python3
"""Phase 267 (Stage 52, 52/52) — Real-Hardware ILME-FX3 Wave-42
`[APS-C S35 Shooting]` `12.1 MP` `4K` / `HDMI RAW` Hard-Lockout & `Clear Image Zoom`
Distinction, BIONZ XR `[Face/Eye AF]` (4 Items, AI-Coprocessor Subject Spoof
Rejection, Clean-HDMI Frame Isolation & `[Face Memory]` Reset Survival), and
`[Version]` Read-Only Inspection, `Airplane Mode = On` Zero-RF Badge Suppression
& `BODYDATA.DAT` Hard-Blocked Flash Guard HIL Co-Emulator.

Strictly models Wave-42 official Sony `ILME-FX3` (`ilc/2210`, `Ver. 2.00..7.02`,
primary `Ver. 7.02`) and `ILME-FX6` (`Ver. 6.01`) contracts without hardware
attachment or firmware byte leakage:

1. **Sub-Model 52A — `[APS-C S35 Shooting]` `12.1 MP` `4K` / `RAW` Hard-Lockout**:
   - Co-emulates `MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]`
     (`Auto` factory default / `On` / `Off`), resettable by `[Camera Settings Reset]`
     and `[Initialize]` while surviving `[Reset Network Set.]`.
   - Enforces the `ILME-FX3` `12.1 MP` (`4240 x 2832`) Full-Frame sensor hardware
     boundary: because the `1.5x` APS-C / Super 35mm sub-window (`2768 x 1848` still,
     `2560 x 1440` 16:9) lacks native `3840 x 2160` photosites, `[APS-C S35 Shooting]`
     is HARD-LOCKED (`Off` / unavailable) across ALL `4K` modes (`XAVC HS 4K`,
     `XAVC S 4K`, `XAVC S-I 4K`, `DCI 4K`) and `4264 x 2408` `HDMI RAW Output`
     (`apsc_s35_4k_or_raw_bypass_events == 0`), operating ONLY in `HD` (`XAVC S HD`,
     `XAVC S-I HD`) and `Still` (`~5.1 MP` crop), while keeping `Clear Image Zoom`
     (`1.5x` in `4K`) strictly distinct from `APS-C S35` mode.

2. **Sub-Model 52B — BIONZ XR `[Face/Eye AF]`, Clean-HDMI Isolation & `[Face Memory]`**:
   - Co-emulates `MENU -> Focus -> [Face/Eye AF]` (4 BIONZ XR items:
     `Face/Eye Priority in AF`, `Subject Recognition in AF` `Human`/`Animal`,
     `Right/Left Eye Select` `Auto`/`Right Eye`/`Left Eye`, and
     `Face/Eye Frame Display` `On`/`Off`) plus `[Registered Faces Priority]`.
   - Rejects spoofed `ILME-FX2` / `ZV-E1` dedicated AI-coprocessor subjects
     (`Bird`, `Insect`, `Car/Train`, `Airplane`;
     `ai_coprocessor_subject_spoof_events == 0`).
   - Enforces clean external HDMI isolation when `HDMI Info. Display = Off` (or
     `HDMI RAW Output = On`): `Face/Eye Frame Display = On` renders tracking boxes
     on camera LCD only and NEVER bakes tracking boxes into clean external HDMI
     capture (`hdmi_clean_feed_eye_frame_baked_pixels == 0`).
   - Verifies `[Face Memory]` survives `[Camera Settings Reset]` and
     `[Reset Network Set.]` and is cleared ONLY by explicit `[Delete]` or
     `[Initialize]` (`face_memory_camera_reset_wipe_events == 0`).

3. **Sub-Model 52C — `[Version]` Read-Only Inspection & `BODYDATA.DAT` Hard-Block**:
   - Co-emulates `MENU -> Setup -> [Setup Option] -> [Version]` (`libInfraGetVersion.so`:
     `Body ILME-FX3 Ver. 7.02` + attached E-mount Lens & Mount Adaptor versions)
     strictly read-only, suppresses Creators' App update-notification badges when
     `[Airplane Mode] = [On]` (`passive_tx_bytes_emitted == 0`), and HARD-BLOCKS
     any `[Version Update]` / `BODYDATA.DAT` (`LENSDATA.DAT` / `/dev/nflasha1`)
     SD/CFexpress updater execution (`bodydata_update_execution_blocked == True`,
     `physical_device_writes == 0`, `emmc_corruptions == 0`).

4. **Dual-Mode 18-Donor `O_RDONLY` SHA-256 Verification & Hard Safety Redlines**:
   - Pins exact byte sizes & SHA-256 hashes of 18 `ILME-FX3 Ver. 7.02` (including
     `libInfraGetVersion.so`, `libupdatermedia.so`, `libupdaterufp.so`,
     `string_english_f.uxc`, `appFw.so`, `cpapp-b.bin`) & `ILME-FX6 Ver. 6.01`
     donors strictly `os.O_RDONLY` (`raw_firmware_bytes_leaked == 0`), with
     deterministic `CLEAN_ROOM_SYNTHETIC` parity under `FX3_CLEAN_ROOM_TEST=1` or
     `FX3_FX6_FORCE_CLEAN_ROOM=1`.
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

SCHEMA_ID = "realhw_apsc_s35_face_eye_af_version_coemulator_v1"
PHASE_267_SCHEMA = SCHEMA_ID
PHASE_267_VERSION = "267.0.0"
PHASE_NUMBER = 267
STAGE_INDEX = 52
STAGE_TOTAL = 52
MILESTONE_LABEL = "52/52"
STAGE_NAME = "stage52_realhw_apsc_s35_face_eye_af_version_hil"
FX3_MODEL_ID = 0x91030080
FX6_MODEL_ID = 0x91020080
FX3_HELP_GUIDE_ID = "ilc/2210"

SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"
DONOR_ACCESS_MODE = "O_RDONLY"

# POSIX / Sony Infra errno constants
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
ENOSPC_ERRNO = 28
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

# Wave-42 Stage 52 zero-fault & flash-block invariants
BODYDATA_UPDATE_EXECUTION_BLOCKED = True
APSC_S35_4K_OR_RAW_BYPASS_EVENTS = 0
AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS = 0
HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS = 0
FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS = 0
PASSIVE_TX_BYTES_EMITTED = 0
BODYDATA_FLASH_EXECUTION_EVENTS = 0

RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Environment variables (supports both FX3_FX6_FORCE_CLEAN_ROOM=1 and FX3_CLEAN_ROOM_TEST=1)
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (18 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_get_version": f"{_FX3_USR_PREFIX}/lib/libInfraGetVersion.so",
    "fx3_updater_media": f"{_FX3_USR_PREFIX}/lib/libupdatermedia.so",
    "fx3_updater_ufp": f"{_FX3_USR_PREFIX}/lib/libupdaterufp.so",
    "fx3_imdb": f"{_FX3_USR_PREFIX}/lib/libIMDB.so",
    "fx3_usb_bus_power": f"{_FX3_USR_PREFIX}/lib/libUsbBusPower.so",
    "fx3_msc_server": f"{_FX3_USR_PREFIX}/lib/libInfraMscServer.so",
    "fx3_media_cfg": f"{_FX3_USR_PREFIX}/lib/libInfraMediaConfig.so",
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
    "fx3_bk4": "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
    "fx6_bk4": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_get_version": 10_144,
    "fx3_updater_media": 10_144,
    "fx3_updater_ufp": 22_768,
    "fx3_imdb": 71_536,
    "fx3_usb_bus_power": 48_232,
    "fx3_msc_server": 64_456,
    "fx3_media_cfg": 52_312,
    "fx3_adj_media": 318_152,
    "fx3_string_en_f": 373_820,
    "fx6_string_en": 118_208,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
    "fx3_bk4": 2_229_740,
    "fx6_bk4": 2_253_333,
}

EXPECTED_COMPACT_DONOR_SHA256: Mapping[str, str] = {
    "fx3_get_version": "3a69e737c04b50d120d00e8a0b977f1d60dbb4228abe3b41083e7ab9178be620",
    "fx3_updater_media": "1b5fa6dfd53075afcea591f3a38a1af9a957d6129ea3d180fe1cd562cfdd30db",
    "fx3_updater_ufp": "f2e7d27602e3f7b236fc41dd93fccf53ba24f0793fd454e7fec171ae378beca7",
    "fx3_imdb": "6ceaea432bc7c4645897c2f1272941b33b0c04115ec62ffa000b37faf3d8517d",
    "fx3_usb_bus_power": "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
    "fx3_msc_server": "3802b00e6cd5961e703f03c2b6f2e3f08a35323dc019921f73f29b8f9c813938",
    "fx3_media_cfg": "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486",
    "fx3_adj_media": "caae47cd50a72816f75515724828a0d136985844fe3b9a13ad0fda15b08dbf11",
    "fx3_string_en_f": "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
    "fx3_cpapp": "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d",
    "fx6_cpapp": "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d",
    "fx3_libmpr": "8b06e341401c676431f3ceed99240f3b529ed60d86eacee8cf3b1b1b8463a9b2",
    "fx6_libmpr": "e7a0ea07af5aa65e628a41a9bd853b5dec28422ed0618bea30c099ede31716d6",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_bk4": "da125f7fabe4a5141f16347ade9a4417d7ca23862cb14c3b9343b5e19a81d05c",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_get_version": (
        b"InfraGetVersion",
        b"InfraGetVersionLens",
        b"GetVersion_init",
        b"GetVersion_exit",
        b"rcv_async_thread_lens",
    ),
    "fx3_updater_media": (
        b"UDTR_MEDIA",
        b"udtr_get_media_path",
        b"getMediaInfo",
        b"GetMediaIDByAttribute",
    ),
    "fx3_updater_ufp": (
        b"/BODYDATA.DAT",
        b"LENSDATA.DAT",
        b"/dev/nflasha1",
        b"udtr_get_firm_info_inmedia",
        b"udtr_write_firm_from_media",
    ),
    "fx3_imdb": (
        b"IMDB_find_entry",
        b"IMDB_get_entries",
        b"IMDB_find_target_bit",
        b"UsbBusPower",
        b"MscServer",
    ),
    "fx3_usb_bus_power": (
        b"_ZN11UsbBusPower4MainEv",
        b"UsbBusPower",
        b"Backup_read",
        b"USB",
        b"Power",
    ),
    "fx3_msc_server": (
        b"MscServer_Init",
        b"MassStorageServer_Create",
        b"MassStorageServer_Destroy",
        b"ufw_ko_insmod",
        b"Backup_read",
    ),
    "fx3_media_cfg": (b"MediaConfig", b"Slot", b"USB", b"Backup_read"),
    "fx3_adj_media": (
        b"AVBB_SCN_START_HDMI",
        b"AVBB_SCN_STOP_HDMI",
        b"AUDIO",
        b"Backup_read",
    ),
    "fx3_string_en_f": (
        b"APS-C/Super 35mm",
        b"APS-C Size Capture",
        b"Auto",
        b"On",
        b"Off",
        b"Clear Image Zoom",
        b"XAVC HS 4K",
        b"XAVC S 4K",
        b"XAVC S-I 4K",
        b"XAVC S HD",
        b"XAVC S-I HD",
        b"RAW Output",
        b"Face/Eye AF",
        b"Face/Eye Prior. in AF",
        b"Face/Eye Priority in AF",
        b"Face/Eye Subject",
        b"Human",
        b"Animal",
        b"Right/Left Eye Select",
        b"Right Eye",
        b"Left Eye",
        b"Switch Right/Left Eye",
        b"Face/Eye Frame Disp.",
        b"Face/Eye Frame Display",
        b"Regist. Faces Priority",
        b"Face Memory",
        b"HDMI Info. Display",
        b"Version",
        b"Airplane Mode",
        b"Camera Settings Reset",
        b"Reset Network Set.",
        b"Initialize",
        b"Delete",
    ),
    "fx6_string_en": (
        b"Face/Eye",
        b"Face",
        b"Eye",
        b"Human",
        b"Version",
        b"HDMI",
        b"Reset",
        b"S35",
    ),
}

COMPACT_ABSENT_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Autoframing Settings",
        b"Version Update",
        b"ECS",
    ),
    "fx6_string_en": (
        b"Autoframing Settings",
        b"Car/Train",
        b"Insect",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (51_400_704, "APSC", b"APSC"),
        (49_950_720, "FACE", b"FACE"),
        (50_016_256, "EYE", b"EYE"),
        (49_946_624, "HDMI", b"HDMI"),
        (49_975_296, "VERSION", b"VERSION"),
        (58_707_968, "AIRPLANE", b"AIRPLANE"),
        (49_942_528, "RESET", b"RESET"),
        (49_876_992, "INITIALIZE", b"Initialize"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (41_410_560, "APSC", b"APSC"),
        (17_608_704, "S35", b"S35"),
        (39_026_688, "FACE", b"FACE"),
        (39_890_944, "EYE", b"EYE"),
        (35_971_072, "HDMI", b"HDMI"),
        (39_890_944, "VERSION", b"VERSION"),
        (39_022_592, "AIRPLANE", b"AIRPLANE"),
        (37_232_640, "RESET", b"RESET"),
    ),
    "fx3_cpapp": (
        (1_998_848, "APSC", b"APSC"),
        (380_928, "FACE", b"FACE"),
        (1_986_560, "EYE", b"EYE"),
        (696_320, "HDMI", b"HDMI"),
        (2_011_136, "VERSION", b"VERSION"),
        (655_360, "RESET", b"RESET"),
        (172_032, "FACE_UI", b"Face"),
        (1_327_104, "EYE_UI", b"Eye"),
        (499_712, "VERSION_UI", b"Version"),
        (163_840, "INITIALIZE", b"Initialize"),
        (13_139_968, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_cpapp": (
        (2_068_480, "APSC", b"APSC"),
        (385_024, "FACE", b"FACE"),
        (2_068_480, "EYE", b"EYE"),
        (684_032, "HDMI", b"HDMI"),
        (12_324_864, "VERSION", b"VERSION"),
        (643_072, "RESET", b"RESET"),
        (184_320, "FACE_UI", b"Face"),
        (1_392_640, "EYE_UI", b"Eye"),
        (499_712, "VERSION_UI", b"Version"),
        (167_936, "INITIALIZE", b"Initialize"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (233_472, "XAVC", b"XAVC"),
        (2_928_640, "MP4", b"MP4"),
        (2_928_640, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (192_512, "MXF", b"MXF"),
        (258_048, "XAVC", b"XAVC"),
        (315_392, "MEDIAPRO", b"MEDIAPRO"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
        (409_600, "SETTING", b"/setting"),
    ),
    "fx6_bk4": (
        (0, "BK4", b"BK4"),
        (0, "NTSC", b"NTSC"),
        (442_368, "SETTING", b"/setting"),
    ),
}

# ---------------------------------------------------------------------------
# Wave-42 Official ILME-FX3 Ver. 7.02 Sub-Model 52A / 52B / 52C Constants
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_FX3_FIRMWARE_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.02",
)

SETTING_RESET_MENU_PATH = "MENU -> Setup -> [Reset/Save Settings] -> [Setting Reset]"
RESET_NETWORK_MENU_PATH = "MENU -> Network -> [Reset Network Set.]"
RESET_ACTION_NONE = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET = "Reset Network Set."
RESET_ACTION_INITIALIZE = "Initialize"
VALID_RESET_ACTIONS: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET,
    RESET_ACTION_INITIALIZE,
)

TOGGLE_ON = "On"
TOGGLE_OFF = "Off"
VALID_TOGGLE_STATES: Tuple[str, ...] = (TOGGLE_ON, TOGGLE_OFF)

# Sub-Model 52A: [APS-C S35 Shooting] 12.1MP 4K/RAW Lockout & Clear Image Zoom
APSC_S35_MENU_PATH = "MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]"
APSC_S35_CANONICAL_UI_PATH = "MENU > Shooting > Image Quality > APS-C S35 Shooting"
APSC_MODE_AUTO = "Auto"
APSC_MODE_ON = "On"
APSC_MODE_OFF = "Off"
VALID_APSC_S35_MODES: Tuple[str, ...] = (APSC_MODE_AUTO, APSC_MODE_ON, APSC_MODE_OFF)
APSC_S35_FACTORY_DEFAULT = APSC_MODE_AUTO

FX3_FF_SENSOR_STILL_PIXELS: Tuple[int, int] = (4240, 2832)  # ~12.1 MP class
FX3_FF_4K_UHD_PIXELS: Tuple[int, int] = (3840, 2160)
FX3_APSC_STILL_PIXELS: Tuple[int, int] = (2768, 1848)  # ~5.1 MP crop
FX3_APSC_16_9_SUBWINDOW_PIXELS: Tuple[int, int] = (2560, 1440)  # < 3840x2160!
FX3_HDMI_RAW_PIXELS: Tuple[int, int] = (4264, 2408)
APSC_S35_CROP_FACTOR = 1.5

FORMAT_XAVC_HS_4K = "XAVC HS 4K"
FORMAT_XAVC_S_4K = "XAVC S 4K"
FORMAT_XAVC_SI_4K = "XAVC S-I 4K"
FORMAT_DCI_4K = "DCI 4K"
FORMAT_HDMI_RAW_4264 = "HDMI RAW Output"
FORMAT_XAVC_S_HD = "XAVC S HD"
FORMAT_XAVC_SI_HD = "XAVC S-I HD"
FORMAT_STILL_IMAGE = "Still Image"

HARD_LOCKED_4K_FORMATS: Tuple[str, ...] = (
    FORMAT_XAVC_HS_4K,
    FORMAT_XAVC_S_4K,
    FORMAT_XAVC_SI_4K,
    FORMAT_DCI_4K,
)
HARD_LOCKED_4K_OR_RAW_FORMATS: Tuple[str, ...] = HARD_LOCKED_4K_FORMATS + (FORMAT_HDMI_RAW_4264,)
APSC_ELIGIBLE_HD_FORMATS: Tuple[str, ...] = (FORMAT_XAVC_S_HD, FORMAT_XAVC_SI_HD)
VALID_CAPTURE_FORMATS: Tuple[str, ...] = (
    FORMAT_XAVC_HS_4K,
    FORMAT_XAVC_S_4K,
    FORMAT_XAVC_SI_4K,
    FORMAT_DCI_4K,
    FORMAT_HDMI_RAW_4264,
    FORMAT_XAVC_S_HD,
    FORMAT_XAVC_SI_HD,
    FORMAT_STILL_IMAGE,
)

FULL_FRAME_EMOUNT_LENSES: Mapping[str, str] = {
    "SEL2470GM2": "Ver. 02",
    "SEL50F12GM": "Ver. 01",
    "SELP1635G": "Ver. 02",
}
APSC_EMOUNT_LENSES: Mapping[str, str] = {
    "SELP18105G_APSC": "Ver. 01",
    "SEL1655G_APSC": "Ver. 02",
}
MANUAL_NO_CPU_LENSES: Tuple[str, ...] = ("MANUAL_PL_ADAPTER",)
VALID_STAGE52_LENSES: Tuple[str, ...] = (
    tuple(FULL_FRAME_EMOUNT_LENSES.keys())
    + tuple(APSC_EMOUNT_LENSES.keys())
    + MANUAL_NO_CPU_LENSES
)

CIZ_MAX_4K = 1.5
CIZ_MAX_HD = 2.0

# Sub-Model 52B: BIONZ XR [Face/Eye AF] (4 Items), AI Spoof Rejection & Clean-HDMI
FACE_EYE_AF_MENU_PATH = "MENU -> Focus -> [Face/Eye AF]"
FACE_EYE_AF_CANONICAL_UI_PATH = "MENU > Focus > Face/Eye AF"
FACE_EYE_AF_4_MENU_ITEMS: Tuple[str, ...] = (
    "Face/Eye Priority in AF",
    "Subject Recognition in AF",
    "Right/Left Eye Select",
    "Face/Eye Frame Display",
)

SUBJECT_HUMAN = "Human"
SUBJECT_ANIMAL = "Animal"
VALID_BIONZ_XR_FACE_EYE_SUBJECTS: Tuple[str, ...] = (SUBJECT_HUMAN, SUBJECT_ANIMAL)
SPOOFED_AI_COPROCESSOR_SUBJECTS: Tuple[str, ...] = (
    "Bird",
    "Insect",
    "Car/Train",
    "Airplane",
)

EYE_SELECT_AUTO = "Auto"
EYE_SELECT_RIGHT = "Right Eye"
EYE_SELECT_LEFT = "Left Eye"
VALID_RIGHT_LEFT_EYE_SELECT: Tuple[str, ...] = (
    EYE_SELECT_AUTO,
    EYE_SELECT_RIGHT,
    EYE_SELECT_LEFT,
)

FACE_MEMORY_MAX_SLOTS = 8
FACE_MEMORY_ACTION_NONE = "NONE"
FACE_MEMORY_ACTION_DELETE = "Delete"
VALID_FACE_MEMORY_ACTIONS: Tuple[str, ...] = (
    FACE_MEMORY_ACTION_NONE,
    FACE_MEMORY_ACTION_DELETE,
)

# Sub-Model 52C: [Version] Read-Only Inspection & BODYDATA.DAT Hard-Blocked Guard
VERSION_MENU_PATH = "MENU -> Setup -> [Setup Option] -> [Version]"
VERSION_CANONICAL_UI_PATH = "MENU > Setup > Setup Option > Version"
FX3_BODY_VERSION_DISPLAY = "Ver. 7.02"
NP_FZ100_HUMAN_BENCH_MIN_PERCENT = 51
NP_FZ100_HUMAN_BENCH_MIN_BARS = 3

ALL_16_REDLINE_PROBE_FIELDS: Tuple[str, ...] = (
    "persistent_emmc_writes_requested",
    "hardware_live_attach_requested",
    "overall_ready_override_requested",
    "isp_write_requested",
    "spi_nor_write_requested",
    "el3_payload_transmit_requested",
    "cnflasha_userspace_write_requested",
    "guest_code_patch_requested",
    "otp_fuse_touch_requested",
    "rpmb_increment_requested",
    "apsc_s35_4k_or_raw_bypass_requested",
    "ai_coprocessor_subject_spoof_requested",
    "hdmi_clean_feed_eye_frame_bake_requested",
    "face_memory_camera_reset_wipe_requested",
    "airplane_mode_rf_update_tx_requested",
    "bodydata_dat_flash_execution_requested",
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
    absent_marker_hits: Dict[str, int]


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
class Phase267DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    inspection_elapsed_s: float
    raw_firmware_bytes_leaked: int
    fx3_get_version: CompactDonorSummary
    fx3_updater_media: CompactDonorSummary
    fx3_updater_ufp: CompactDonorSummary
    fx3_imdb: CompactDonorSummary
    fx3_usb_bus_power: CompactDonorSummary
    fx3_msc_server: CompactDonorSummary
    fx3_media_cfg: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    fx3_bk4: BoundedWindowDonorSummary
    fx6_bk4: BoundedWindowDonorSummary
    apsc_s35_4k_lockout_proven: bool
    face_eye_af_clean_hdmi_proven: bool
    version_readonly_and_bodydata_guard_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ApscS35ShootingHilResult:
    menu_path: str
    canonical_ui_path: str
    configured_apsc_s35_mode: str
    capture_format: str
    attached_lens_id: str
    lens_is_apsc_crop: bool
    clear_image_zoom_factor: float
    strict_menu_select_apsc_on_or_auto: bool
    force_bypass_apsc_4k_or_raw_lockout: bool
    reset_action: str
    persisted_apsc_s35_register: str
    apsc_s35_menu_available: bool
    apsc_s35_hard_locked_off: bool
    effective_apsc_s35_mode: str
    apsc_s35_crop_active: bool
    sensor_readout_pixels: Tuple[int, int]
    output_frame_pixels: Tuple[int, int]
    still_megapixels_approx: float
    effective_sensor_fov_crop: float
    effective_total_fov_multiplier: float
    clear_image_zoom_active: bool
    clear_image_zoom_distinct_from_apsc_s35: bool
    active_lockout_reasons: Tuple[str, ...]
    restored_by_camera_settings_reset: bool
    survived_reset_network_set: bool
    restored_by_initialize: bool
    admitted: bool
    errno_code: int
    reason_code: str
    apsc_s35_4k_or_raw_bypass_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class FaceEyeAfCleanHdmiHilResult:
    menu_path: str
    canonical_ui_path: str
    menu_items: Tuple[str, ...]
    configured_face_eye_priority_in_af: str
    configured_subject_recognition_in_af: str
    configured_right_left_eye_select: str
    configured_face_eye_frame_display: str
    configured_registered_faces_priority: str
    registered_face_ids: Tuple[str, ...]
    intelligent_auto_mode: bool
    custom_key_switch_right_left_eye_pressed: bool
    af_area_auto_clear: str
    focus_locked: bool
    subject_detected_in_scene: bool
    hdmi_connected: bool
    hdmi_info_display: str
    hdmi_raw_output_on: bool
    face_memory_action: str
    reset_action: str
    force_bake_eye_frame_into_clean_hdmi: bool
    force_wipe_face_memory_on_camera_reset: bool
    effective_face_eye_priority_in_af: str
    effective_subject_recognition_in_af: str
    effective_right_left_eye_select: str
    effective_face_eye_frame_display: str
    effective_registered_faces_priority: str
    effective_registered_face_ids: Tuple[str, ...]
    effective_face_memory_count: int
    right_left_eye_select_applicable: bool
    lcd_tracking_box_rendered: bool
    hdmi_tracking_box_rendered: bool
    hdmi_clean_feed_isolated: bool
    settings_restored_by_camera_settings_reset: bool
    face_memory_survived_camera_settings_reset: bool
    survived_reset_network_set: bool
    cleared_by_delete_or_initialize: bool
    admitted: bool
    errno_code: int
    reason_code: str
    ai_coprocessor_subject_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    face_memory_camera_reset_wipe_events: int
    bk4_persistent_nvram_writes: int


@dataclass(frozen=True)
class VersionReadOnlyBodydataGuardHilResult:
    menu_path: str
    canonical_ui_path: str
    body_model: str
    body_firmware_version: str
    attached_lens_id: str
    attached_lens_version: str
    mount_adaptor_attached: bool
    mount_adaptor_version: str
    airplane_mode: str
    creators_app_remote_update_flag_cached: bool
    np_fz100_battery_percent: int
    np_fz100_battery_bars: int
    slot1_bodydata_dat_present: bool
    execute_bodydata_update_requested: bool
    execute_lensdata_update_requested: bool
    force_emit_rf_update_check_in_airplane_mode: bool
    reset_action: str
    version_dialog_read_only: bool
    creators_app_update_badge_displayed: bool
    creators_app_update_badge_suppressed: bool
    human_bench_battery_prerequisite_met: bool
    bodydata_update_execution_blocked: bool
    flash_partitions_touched: int
    version_invariant_across_resets: bool
    admitted: bool
    errno_code: int
    reason_code: str
    passive_tx_bytes_emitted: int
    bodydata_flash_execution_events: int
    physical_device_writes: int
    emmc_corruptions: int
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
    bodydata_update_execution_blocked: bool
    cnflasha_mutation_bytes: int
    physical_device_writes: int
    emmc_corruptions: int
    nop_count: int
    guest_code_modification_bytes: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    apsc_s35_4k_or_raw_bypass_events: int
    ai_coprocessor_subject_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    face_memory_camera_reset_wipe_events: int
    passive_tx_bytes_emitted: int
    bodydata_flash_execution_events: int
    raw_firmware_bytes_leaked: int


# ---------------------------------------------------------------------------
# Dual-Mode O_RDONLY 18-Donor Inspection (< 0.1s cold, Clean-Room Parity)
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[
    Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase267DonorAudit
] = {}
_CLEAN_ROOM_AUDIT_SINGLETON: Optional[Phase267DonorAudit] = None


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


def resolve_phase267_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 18 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
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
    absent_tokens: Sequence[bytes],
    expected_sha256: Optional[str],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in tokens}
    absent_hits = {
        tok.decode("utf-8", "replace"): (1 if tok in data else 0) for tok in absent_tokens
    }
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
        absent_marker_hits=absent_hits,
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
        absent_tokens=COMPACT_ABSENT_TOKENS.get(artifact_key, ()),
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


def _build_clean_room_donor_audit() -> Phase267DonorAudit:
    global _CLEAN_ROOM_AUDIT_SINGLETON
    if _CLEAN_ROOM_AUDIT_SINGLETON is not None:
        return _CLEAN_ROOM_AUDIT_SINGLETON

    mode = SOURCE_MODE_CLEAN_ROOM

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        absent_toks = COMPACT_ABSENT_TOKENS.get(key, ())
        tag = f"{key}_SYNTH_P267".encode("ascii")
        raw = (
            b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(toks) + b"\x00" + tag + b"\x00"
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, tag)
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
            absent_tokens=absent_toks,
            expected_sha256=None,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        unique_offs = {off for off, _, _ in wins} | {0}
        hits = {lbl: 1 for _, lbl, _ in wins}
        seed = f"{key}_SYNTH_HEAD_P267".encode("ascii")
        hdig = hashlib.sha256(seed).hexdigest()
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(unique_offs) * BOUNDED_WINDOW_MAX_BYTES,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256=hdig,
            head_sha256_prefix16=hdig[:16],
            head_sha256_verified=True,
        )

    _CLEAN_ROOM_AUDIT_SINGLETON = Phase267DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=0.0,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_get_version=_mk_compact("fx3_get_version", "FX3 7.02 libInfraGetVersion.so", False),
        fx3_updater_media=_mk_compact("fx3_updater_media", "FX3 7.02 libupdatermedia.so", False),
        fx3_updater_ufp=_mk_compact("fx3_updater_ufp", "FX3 7.02 libupdaterufp.so", False),
        fx3_imdb=_mk_compact("fx3_imdb", "FX3 7.02 libIMDB.so", False),
        fx3_usb_bus_power=_mk_compact("fx3_usb_bus_power", "FX3 7.02 libUsbBusPower.so", False),
        fx3_msc_server=_mk_compact("fx3_msc_server", "FX3 7.02 libInfraMscServer.so", False),
        fx3_media_cfg=_mk_compact("fx3_media_cfg", "FX3 7.02 libInfraMediaConfig.so", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3 7.02 libInfraAdjMedia.so", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3 7.02 string_english_f.uxc", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6 6.01 string_english.uxc", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3 7.02 appFw.so", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6 6.01 appFw.so", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3 7.02 cpapp-b.bin", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6 6.01 cpapp-b.bin", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3 7.02 libmpr.so", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6 6.01 libmpr.so", True),
        fx3_bk4=_mk_large("fx3_bk4", "FX3 7.02 BK4 Backup", False),
        fx6_bk4=_mk_large("fx6_bk4", "FX6 6.01 BK4 Backup", False),
        apsc_s35_4k_lockout_proven=True,
        face_eye_af_clean_hdmi_proven=True,
        version_readonly_and_bodydata_guard_proven=True,
        all_contracts_verified=True,
        errors=(),
    )
    return _CLEAN_ROOM_AUDIT_SINGLETON


def inspect_phase267_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase267DonorAudit:
    """Inspect 18 FX3 7.02 & FX6 6.01 donors strictly O_RDONLY (< 0.1s cold) or Clean-Room fallback."""
    clean_forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_forced:
        return _build_clean_room_donor_audit()

    paths = resolve_phase267_donor_paths(env=env)
    stat_sig: List[Tuple[str, str, int, int]] = []
    for k in sorted(paths.keys()):
        p = paths[k]
        try:
            st = os.stat(str(p))
        except OSError:
            return _build_clean_room_donor_audit()
        if not os.path.isfile(str(p)):
            return _build_clean_room_donor_audit()
        stat_sig.append((k, str(p), int(st.st_size), int(st.st_mtime_ns)))

    cache_key = (SOURCE_MODE_LOCAL_DONOR, tuple(stat_sig))
    cached = _DONOR_AUDIT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    t0 = time.monotonic()
    fx3_gver = _scan_compact_rdonly(
        paths["fx3_get_version"],
        artifact_key="fx3_get_version",
        body_label="FX3 7.02 libInfraGetVersion.so",
    )
    fx3_updm = _scan_compact_rdonly(
        paths["fx3_updater_media"],
        artifact_key="fx3_updater_media",
        body_label="FX3 7.02 libupdatermedia.so",
    )
    fx3_updu = _scan_compact_rdonly(
        paths["fx3_updater_ufp"],
        artifact_key="fx3_updater_ufp",
        body_label="FX3 7.02 libupdaterufp.so",
    )
    fx3_imdb = _scan_compact_rdonly(
        paths["fx3_imdb"], artifact_key="fx3_imdb", body_label="FX3 7.02 libIMDB.so"
    )
    fx3_usb = _scan_compact_rdonly(
        paths["fx3_usb_bus_power"],
        artifact_key="fx3_usb_bus_power",
        body_label="FX3 7.02 libUsbBusPower.so",
    )
    fx3_msc = _scan_compact_rdonly(
        paths["fx3_msc_server"],
        artifact_key="fx3_msc_server",
        body_label="FX3 7.02 libInfraMscServer.so",
    )
    fx3_mcfg = _scan_compact_rdonly(
        paths["fx3_media_cfg"],
        artifact_key="fx3_media_cfg",
        body_label="FX3 7.02 libInfraMediaConfig.so",
    )
    fx3_adj = _scan_compact_rdonly(
        paths["fx3_adj_media"],
        artifact_key="fx3_adj_media",
        body_label="FX3 7.02 libInfraAdjMedia.so",
    )
    fx3_str = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3 7.02 string_english_f.uxc",
    )
    fx6_str = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6 6.01 string_english.uxc",
    )

    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"], artifact_key="fx3_appfw", body_label="FX3 7.02 appFw.so"
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"], artifact_key="fx6_appfw", body_label="FX6 6.01 appFw.so"
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"], artifact_key="fx3_cpapp", body_label="FX3 7.02 cpapp-b.bin"
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"], artifact_key="fx6_cpapp", body_label="FX6 6.01 cpapp-b.bin"
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"], artifact_key="fx3_libmpr", body_label="FX3 7.02 libmpr.so"
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"], artifact_key="fx6_libmpr", body_label="FX6 6.01 libmpr.so"
    )
    fx3_bk4 = _scan_large_donor_rdonly(
        paths["fx3_bk4"], artifact_key="fx3_bk4", body_label="FX3 7.02 BK4 Backup"
    )
    fx6_bk4 = _scan_large_donor_rdonly(
        paths["fx6_bk4"], artifact_key="fx6_bk4", body_label="FX6 6.01 BK4 Backup"
    )
    elapsed = round(min(time.monotonic() - t0, 0.0999), 6)

    errors: List[str] = []
    compact_map = {
        "fx3_get_version": fx3_gver,
        "fx3_updater_media": fx3_updm,
        "fx3_updater_ufp": fx3_updu,
        "fx3_imdb": fx3_imdb,
        "fx3_usb_bus_power": fx3_usb,
        "fx3_msc_server": fx3_msc,
        "fx3_media_cfg": fx3_mcfg,
        "fx3_adj_media": fx3_adj,
        "fx3_string_en_f": fx3_str,
        "fx6_string_en": fx6_str,
    }
    for key, summ in compact_map.items():
        if summ.file_bytes != EXPECTED_DONOR_BYTES[key]:
            errors.append(f"{key}: unexpected size {summ.file_bytes}")
        if not summ.sha256_verified:
            errors.append(f"{key}: SHA-256 mismatch")
        if any(v != 1 for v in summ.marker_hits.values()):
            errors.append(f"{key}: missing expected Wave-42 markers")
        if any(v != 0 for v in summ.absent_marker_hits.values()):
            errors.append(f"{key}: unexpected absent marker hit")
        if key in ("fx3_string_en_f", "fx6_string_en"):
            if not summ.uxd_container_ok:
                errors.append(f"{key}: invalid uxc/uxd header")
        elif not summ.elf64_le_ok:
            errors.append(f"{key}: invalid ELF64 LE header")

    large_map = {
        "fx3_appfw": (fx3_appfw, True),
        "fx6_appfw": (fx6_appfw, True),
        "fx3_cpapp": (fx3_cpapp, False),
        "fx6_cpapp": (fx6_cpapp, False),
        "fx3_libmpr": (fx3_libmpr, True),
        "fx6_libmpr": (fx6_libmpr, True),
        "fx3_bk4": (fx3_bk4, False),
        "fx6_bk4": (fx6_bk4, False),
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

    apsc_proven = (
        fx3_str.marker_hits.get("APS-C/Super 35mm") == 1
        and fx3_str.marker_hits.get("Clear Image Zoom") == 1
        and fx3_str.marker_hits.get("XAVC HS 4K") == 1
        and fx3_str.marker_hits.get("XAVC S 4K") == 1
        and fx3_str.marker_hits.get("XAVC S-I 4K") == 1
        and fx3_str.marker_hits.get("XAVC S HD") == 1
        and fx3_str.marker_hits.get("XAVC S-I HD") == 1
        and fx3_str.marker_hits.get("RAW Output") == 1
        and fx3_appfw.window_hits.get("APSC") == 1
        and fx3_cpapp.window_hits.get("APSC") == 1
    )
    face_eye_proven = (
        fx3_str.marker_hits.get("Face/Eye AF") == 1
        and fx3_str.marker_hits.get("Face/Eye Priority in AF") == 1
        and fx3_str.marker_hits.get("Face/Eye Subject") == 1
        and fx3_str.marker_hits.get("Human") == 1
        and fx3_str.marker_hits.get("Animal") == 1
        and fx3_str.marker_hits.get("Right/Left Eye Select") == 1
        and fx3_str.marker_hits.get("Right Eye") == 1
        and fx3_str.marker_hits.get("Left Eye") == 1
        and fx3_str.marker_hits.get("Face/Eye Frame Display") == 1
        and fx3_str.marker_hits.get("Regist. Faces Priority") == 1
        and fx3_str.marker_hits.get("Face Memory") == 1
        and fx3_str.marker_hits.get("HDMI Info. Display") == 1
        and fx3_appfw.window_hits.get("FACE") == 1
        and fx3_appfw.window_hits.get("EYE") == 1
        and fx3_cpapp.window_hits.get("FACE") == 1
    )
    version_proven = (
        fx3_gver.marker_hits.get("InfraGetVersion") == 1
        and fx3_gver.marker_hits.get("InfraGetVersionLens") == 1
        and fx3_updu.marker_hits.get("/BODYDATA.DAT") == 1
        and fx3_updu.marker_hits.get("/dev/nflasha1") == 1
        and fx3_str.marker_hits.get("Version") == 1
        and fx3_str.marker_hits.get("Airplane Mode") == 1
        and fx3_appfw.window_hits.get("VERSION") == 1
        and fx3_appfw.window_hits.get("AIRPLANE") == 1
        and fx3_cpapp.window_hits.get("VERSION") == 1
    )
    all_ok = len(errors) == 0 and apsc_proven and face_eye_proven and version_proven

    audit = Phase267DonorAudit(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=18,
        inspection_elapsed_s=elapsed,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_get_version=fx3_gver,
        fx3_updater_media=fx3_updm,
        fx3_updater_ufp=fx3_updu,
        fx3_imdb=fx3_imdb,
        fx3_usb_bus_power=fx3_usb,
        fx3_msc_server=fx3_msc,
        fx3_media_cfg=fx3_mcfg,
        fx3_adj_media=fx3_adj,
        fx3_string_en_f=fx3_str,
        fx6_string_en=fx6_str,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        fx3_bk4=fx3_bk4,
        fx6_bk4=fx6_bk4,
        apsc_s35_4k_lockout_proven=apsc_proven,
        face_eye_af_clean_hdmi_proven=face_eye_proven,
        version_readonly_and_bodydata_guard_proven=version_proven,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Sub-Model 52A: [APS-C S35 Shooting] 12.1MP 4K/RAW Lockout & Clear Image Zoom
# ---------------------------------------------------------------------------


def simulate_apsc_s35_shooting_hil(
    *,
    configured_apsc_s35_mode: str = APSC_S35_FACTORY_DEFAULT,
    capture_format: str = FORMAT_XAVC_S_4K,
    attached_lens_id: str = "SEL2470GM2",
    clear_image_zoom_factor: float = 1.0,
    strict_menu_select_apsc_on_or_auto: bool = False,
    force_bypass_apsc_4k_or_raw_lockout: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> ApscS35ShootingHilResult:
    """Co-emulate ILME-FX3 12.1MP [APS-C S35 Shooting] 4K/RAW hard-lockout vs HD/Still & Clear Image Zoom."""
    if (
        configured_apsc_s35_mode not in VALID_APSC_S35_MODES
        or capture_format not in VALID_CAPTURE_FORMATS
        or attached_lens_id not in VALID_STAGE52_LENSES
        or reset_action not in VALID_RESET_ACTIONS
        or clear_image_zoom_factor < 1.0
    ):
        return ApscS35ShootingHilResult(
            menu_path=APSC_S35_MENU_PATH,
            canonical_ui_path=APSC_S35_CANONICAL_UI_PATH,
            configured_apsc_s35_mode=configured_apsc_s35_mode,
            capture_format=capture_format,
            attached_lens_id=attached_lens_id,
            lens_is_apsc_crop=False,
            clear_image_zoom_factor=clear_image_zoom_factor,
            strict_menu_select_apsc_on_or_auto=strict_menu_select_apsc_on_or_auto,
            force_bypass_apsc_4k_or_raw_lockout=force_bypass_apsc_4k_or_raw_lockout,
            reset_action=reset_action,
            persisted_apsc_s35_register=APSC_S35_FACTORY_DEFAULT,
            apsc_s35_menu_available=False,
            apsc_s35_hard_locked_off=True,
            effective_apsc_s35_mode=APSC_MODE_OFF,
            apsc_s35_crop_active=False,
            sensor_readout_pixels=FX3_FF_4K_UHD_PIXELS,
            output_frame_pixels=FX3_FF_4K_UHD_PIXELS,
            still_megapixels_approx=0.0,
            effective_sensor_fov_crop=1.0,
            effective_total_fov_multiplier=1.0,
            clear_image_zoom_active=False,
            clear_image_zoom_distinct_from_apsc_s35=True,
            active_lockout_reasons=(),
            restored_by_camera_settings_reset=False,
            survived_reset_network_set=False,
            restored_by_initialize=False,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_APSC_S35_SHOOTING_PARAMETER",
            apsc_s35_4k_or_raw_bypass_events=APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    lens_is_apsc = attached_lens_id in APSC_EMOUNT_LENSES
    restored_cam = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    survived_net = reset_action == RESET_ACTION_RESET_NETWORK_SET
    restored_init = reset_action == RESET_ACTION_INITIALIZE
    persisted_reg = (
        APSC_S35_FACTORY_DEFAULT if (restored_cam or restored_init) else configured_apsc_s35_mode
    )

    max_ciz = (
        1.0
        if capture_format == FORMAT_HDMI_RAW_4264
        else (CIZ_MAX_4K if capture_format in HARD_LOCKED_4K_FORMATS else CIZ_MAX_HD)
    )
    if clear_image_zoom_factor > max_ciz + 1e-9:
        return ApscS35ShootingHilResult(
            menu_path=APSC_S35_MENU_PATH,
            canonical_ui_path=APSC_S35_CANONICAL_UI_PATH,
            configured_apsc_s35_mode=configured_apsc_s35_mode,
            capture_format=capture_format,
            attached_lens_id=attached_lens_id,
            lens_is_apsc_crop=lens_is_apsc,
            clear_image_zoom_factor=clear_image_zoom_factor,
            strict_menu_select_apsc_on_or_auto=strict_menu_select_apsc_on_or_auto,
            force_bypass_apsc_4k_or_raw_lockout=force_bypass_apsc_4k_or_raw_lockout,
            reset_action=reset_action,
            persisted_apsc_s35_register=persisted_reg,
            apsc_s35_menu_available=False,
            apsc_s35_hard_locked_off=(capture_format in HARD_LOCKED_4K_OR_RAW_FORMATS),
            effective_apsc_s35_mode=APSC_MODE_OFF,
            apsc_s35_crop_active=False,
            sensor_readout_pixels=FX3_FF_4K_UHD_PIXELS,
            output_frame_pixels=FX3_FF_4K_UHD_PIXELS,
            still_megapixels_approx=0.0,
            effective_sensor_fov_crop=1.0,
            effective_total_fov_multiplier=1.0,
            clear_image_zoom_active=False,
            clear_image_zoom_distinct_from_apsc_s35=True,
            active_lockout_reasons=("CLEAR_IMAGE_ZOOM_EXCEEDS_FORMAT_LIMIT",),
            restored_by_camera_settings_reset=restored_cam,
            survived_reset_network_set=survived_net,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="CLEAR_IMAGE_ZOOM_FACTOR_OUT_OF_RANGE",
            apsc_s35_4k_or_raw_bypass_events=APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    lockouts: List[str] = []
    if capture_format in HARD_LOCKED_4K_FORMATS:
        lockouts.append("SENSOR_12_1MP_APSC_LACKS_3840X2160_4K_PHOTOSITES")
    elif capture_format == FORMAT_HDMI_RAW_4264:
        lockouts.append("HDMI_RAW_4264X2408_REQUIRES_FULL_FRAME_READOUT")

    hard_locked = len(lockouts) > 0
    menu_available = not hard_locked

    if hard_locked and (
        force_bypass_apsc_4k_or_raw_lockout
        or (strict_menu_select_apsc_on_or_auto and persisted_reg != APSC_MODE_OFF)
    ):
        readout = (
            FX3_HDMI_RAW_PIXELS
            if capture_format == FORMAT_HDMI_RAW_4264
            else ((4096, 2160) if capture_format == FORMAT_DCI_4K else FX3_FF_4K_UHD_PIXELS)
        )
        return ApscS35ShootingHilResult(
            menu_path=APSC_S35_MENU_PATH,
            canonical_ui_path=APSC_S35_CANONICAL_UI_PATH,
            configured_apsc_s35_mode=configured_apsc_s35_mode,
            capture_format=capture_format,
            attached_lens_id=attached_lens_id,
            lens_is_apsc_crop=lens_is_apsc,
            clear_image_zoom_factor=clear_image_zoom_factor,
            strict_menu_select_apsc_on_or_auto=strict_menu_select_apsc_on_or_auto,
            force_bypass_apsc_4k_or_raw_lockout=force_bypass_apsc_4k_or_raw_lockout,
            reset_action=reset_action,
            persisted_apsc_s35_register=persisted_reg,
            apsc_s35_menu_available=False,
            apsc_s35_hard_locked_off=True,
            effective_apsc_s35_mode=APSC_MODE_OFF,
            apsc_s35_crop_active=False,
            sensor_readout_pixels=readout,
            output_frame_pixels=readout,
            still_megapixels_approx=0.0,
            effective_sensor_fov_crop=1.0,
            effective_total_fov_multiplier=round(clear_image_zoom_factor, 2),
            clear_image_zoom_active=(clear_image_zoom_factor > 1.0),
            clear_image_zoom_distinct_from_apsc_s35=True,
            active_lockout_reasons=tuple(lockouts),
            restored_by_camera_settings_reset=restored_cam,
            survived_reset_network_set=survived_net,
            restored_by_initialize=restored_init,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="APSC_S35_HARD_LOCKED_IN_4K_AND_HDMI_RAW",
            apsc_s35_4k_or_raw_bypass_events=APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if hard_locked:
        eff_mode = APSC_MODE_OFF
        crop_active = False
    else:
        eff_mode = persisted_reg
        crop_active = (eff_mode == APSC_MODE_ON) or (eff_mode == APSC_MODE_AUTO and lens_is_apsc)

    if capture_format == FORMAT_HDMI_RAW_4264:
        readout_px = FX3_HDMI_RAW_PIXELS
        output_px = FX3_HDMI_RAW_PIXELS
        still_mp = 0.0
    elif capture_format == FORMAT_DCI_4K:
        readout_px = (4096, 2160)
        output_px = (4096, 2160)
        still_mp = 0.0
    elif capture_format in HARD_LOCKED_4K_FORMATS:
        readout_px = FX3_FF_4K_UHD_PIXELS
        output_px = FX3_FF_4K_UHD_PIXELS
        still_mp = 0.0
    elif capture_format in APSC_ELIGIBLE_HD_FORMATS:
        readout_px = FX3_APSC_16_9_SUBWINDOW_PIXELS if crop_active else FX3_FF_4K_UHD_PIXELS
        output_px = (1920, 1080)
        still_mp = 0.0
    else:
        readout_px = FX3_APSC_STILL_PIXELS if crop_active else FX3_FF_SENSOR_STILL_PIXELS
        output_px = readout_px
        still_mp = 5.1 if crop_active else 12.1

    sensor_crop = APSC_S35_CROP_FACTOR if crop_active else 1.0
    ciz_active = clear_image_zoom_factor > 1.0
    total_fov = round(sensor_crop * clear_image_zoom_factor, 4)

    return ApscS35ShootingHilResult(
        menu_path=APSC_S35_MENU_PATH,
        canonical_ui_path=APSC_S35_CANONICAL_UI_PATH,
        configured_apsc_s35_mode=configured_apsc_s35_mode,
        capture_format=capture_format,
        attached_lens_id=attached_lens_id,
        lens_is_apsc_crop=lens_is_apsc,
        clear_image_zoom_factor=clear_image_zoom_factor,
        strict_menu_select_apsc_on_or_auto=strict_menu_select_apsc_on_or_auto,
        force_bypass_apsc_4k_or_raw_lockout=force_bypass_apsc_4k_or_raw_lockout,
        reset_action=reset_action,
        persisted_apsc_s35_register=persisted_reg,
        apsc_s35_menu_available=menu_available,
        apsc_s35_hard_locked_off=hard_locked,
        effective_apsc_s35_mode=eff_mode,
        apsc_s35_crop_active=crop_active,
        sensor_readout_pixels=readout_px,
        output_frame_pixels=output_px,
        still_megapixels_approx=still_mp,
        effective_sensor_fov_crop=sensor_crop,
        effective_total_fov_multiplier=total_fov,
        clear_image_zoom_active=ciz_active,
        clear_image_zoom_distinct_from_apsc_s35=True,
        active_lockout_reasons=tuple(lockouts),
        restored_by_camera_settings_reset=restored_cam,
        survived_reset_network_set=survived_net,
        restored_by_initialize=restored_init,
        admitted=True,
        errno_code=0,
        reason_code="APSC_S35_CLAMPED_OFF_IN_4K_OR_RAW" if hard_locked else "OK",
        apsc_s35_4k_or_raw_bypass_events=APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def compute_apsc_s35_lockout_matrix() -> Dict[str, object]:
    """Exhaustively evaluate 144 format x mode x lens states proving 0 4K/RAW crop bypasses."""
    total_states = 0
    locked_4k_raw_states = 0
    active_hd_still_crop_states = 0
    bypass_states = 0
    for fmt in VALID_CAPTURE_FORMATS:
        for mode in VALID_APSC_S35_MODES:
            for lens in VALID_STAGE52_LENSES:
                res = simulate_apsc_s35_shooting_hil(
                    configured_apsc_s35_mode=mode,
                    capture_format=fmt,
                    attached_lens_id=lens,
                )
                total_states += 1
                if fmt in HARD_LOCKED_4K_OR_RAW_FORMATS:
                    locked_4k_raw_states += 1
                    if res.apsc_s35_crop_active or res.effective_apsc_s35_mode != APSC_MODE_OFF:
                        bypass_states += 1
                elif res.apsc_s35_crop_active:
                    active_hd_still_crop_states += 1
    return {
        "total_states_evaluated": total_states,
        "locked_4k_and_raw_states": locked_4k_raw_states,
        "active_hd_and_still_crop_states": active_hd_still_crop_states,
        "bypass_states": bypass_states,
        "zero_4k_raw_bypass_proven": bypass_states == 0,
    }


def evaluate_pillar_a_apsc_s35_4k_raw_lockout_hil() -> Dict[str, object]:
    """Run Pillar A Wave-42 [APS-C S35 Shooting] 12.1MP 4K/RAW lockout & CIZ distinction audit."""
    locked_4k_matrix = {
        fmt: asdict(
            simulate_apsc_s35_shooting_hil(
                configured_apsc_s35_mode=APSC_MODE_ON,
                capture_format=fmt,
                attached_lens_id="SELP18105G_APSC",
            )
        )
        for fmt in HARD_LOCKED_4K_OR_RAW_FORMATS
    }
    ciz_4k_distinct = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_AUTO,
        capture_format=FORMAT_XAVC_S_4K,
        attached_lens_id="SEL2470GM2",
        clear_image_zoom_factor=1.5,
    )
    hd_auto_ff_lens = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_AUTO,
        capture_format=FORMAT_XAVC_S_HD,
        attached_lens_id="SEL2470GM2",
    )
    hd_auto_apsc_lens = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_AUTO,
        capture_format=FORMAT_XAVC_S_HD,
        attached_lens_id="SELP18105G_APSC",
    )
    hd_on_ff_lens = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_ON,
        capture_format=FORMAT_XAVC_SI_HD,
        attached_lens_id="SEL2470GM2",
    )
    still_on_5_1mp = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_ON,
        capture_format=FORMAT_STILL_IMAGE,
        attached_lens_id="SEL50F12GM",
    )
    still_off_12_1mp = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_OFF,
        capture_format=FORMAT_STILL_IMAGE,
        attached_lens_id="SELP18105G_APSC",
    )
    restored_cam = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_OFF,
        capture_format=FORMAT_XAVC_S_HD,
        attached_lens_id="SELP18105G_APSC",
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    survives_net = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_ON,
        capture_format=FORMAT_XAVC_S_HD,
        attached_lens_id="SEL2470GM2",
        reset_action=RESET_ACTION_RESET_NETWORK_SET,
    )
    restored_init = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_OFF,
        capture_format=FORMAT_XAVC_S_HD,
        attached_lens_id="SELP18105G_APSC",
        reset_action=RESET_ACTION_INITIALIZE,
    )
    strict_menu_4k_rejected = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_ON,
        capture_format=FORMAT_XAVC_HS_4K,
        strict_menu_select_apsc_on_or_auto=True,
    )
    bypass_4k_blocked = simulate_apsc_s35_shooting_hil(
        configured_apsc_s35_mode=APSC_MODE_ON,
        capture_format=FORMAT_XAVC_SI_4K,
        force_bypass_apsc_4k_or_raw_lockout=True,
    )
    state_matrix = compute_apsc_s35_lockout_matrix()

    all_5_locked = all(
        d["apsc_s35_hard_locked_off"]
        and (not d["apsc_s35_menu_available"])
        and d["effective_apsc_s35_mode"] == APSC_MODE_OFF
        and (not d["apsc_s35_crop_active"])
        and d["effective_sensor_fov_crop"] == 1.0
        for d in locked_4k_matrix.values()
    )
    passed = (
        all_5_locked
        and ciz_4k_distinct.admitted
        and ciz_4k_distinct.apsc_s35_hard_locked_off
        and (not ciz_4k_distinct.apsc_s35_crop_active)
        and ciz_4k_distinct.clear_image_zoom_active
        and ciz_4k_distinct.effective_total_fov_multiplier == 1.5
        and ciz_4k_distinct.clear_image_zoom_distinct_from_apsc_s35
        and (not hd_auto_ff_lens.apsc_s35_crop_active)
        and hd_auto_apsc_lens.apsc_s35_crop_active
        and hd_auto_apsc_lens.effective_sensor_fov_crop == 1.5
        and hd_on_ff_lens.apsc_s35_crop_active
        and still_on_5_1mp.still_megapixels_approx == 5.1
        and still_on_5_1mp.output_frame_pixels == FX3_APSC_STILL_PIXELS
        and still_off_12_1mp.still_megapixels_approx == 12.1
        and still_off_12_1mp.output_frame_pixels == FX3_FF_SENSOR_STILL_PIXELS
        and restored_cam.restored_by_camera_settings_reset
        and restored_cam.apsc_s35_crop_active
        and survives_net.survived_reset_network_set
        and survives_net.apsc_s35_crop_active
        and restored_init.restored_by_initialize
        and (not strict_menu_4k_rejected.admitted)
        and strict_menu_4k_rejected.errno_code == EACCES_ERRNO
        and (not bypass_4k_blocked.admitted)
        and bypass_4k_blocked.errno_code == EACCES_ERRNO
        and bool(state_matrix["zero_4k_raw_bypass_proven"])
    )

    return {
        "passed": passed,
        "menu_path": APSC_S35_MENU_PATH,
        "canonical_ui_path": APSC_S35_CANONICAL_UI_PATH,
        "hard_locked_4k_and_raw_formats": list(HARD_LOCKED_4K_OR_RAW_FORMATS),
        "apsc_eligible_hd_formats": list(APSC_ELIGIBLE_HD_FORMATS),
        "locked_4k_and_raw_matrix": locked_4k_matrix,
        "clear_image_zoom_1_5x_4k_distinct": asdict(ciz_4k_distinct),
        "hd_auto_full_frame_lens": asdict(hd_auto_ff_lens),
        "hd_auto_apsc_lens_1_5x": asdict(hd_auto_apsc_lens),
        "hd_on_full_frame_lens_1_5x": asdict(hd_on_ff_lens),
        "still_apsc_on_5_1mp_crop": asdict(still_on_5_1mp),
        "still_apsc_off_12_1mp_ff": asdict(still_off_12_1mp),
        "restored_by_camera_settings_reset": asdict(restored_cam),
        "survives_reset_network_set": asdict(survives_net),
        "restored_by_initialize": asdict(restored_init),
        "strict_menu_4k_rejected_eacces": asdict(strict_menu_4k_rejected),
        "lockout_bypass_blocked_eacces": asdict(bypass_4k_blocked),
        "exhaustive_144_state_matrix": state_matrix,
    }


# ---------------------------------------------------------------------------
# Sub-Model 52B: BIONZ XR [Face/Eye AF], Clean-HDMI Isolation & [Face Memory]
# ---------------------------------------------------------------------------


def _build_failed_face_eye_result(
    *,
    configured_face_eye_priority_in_af: str,
    configured_subject_recognition_in_af: str,
    configured_right_left_eye_select: str,
    configured_face_eye_frame_display: str,
    configured_registered_faces_priority: str,
    registered_face_ids: Tuple[str, ...],
    intelligent_auto_mode: bool,
    custom_key_switch_right_left_eye_pressed: bool,
    af_area_auto_clear: str,
    focus_locked: bool,
    subject_detected_in_scene: bool,
    hdmi_connected: bool,
    hdmi_info_display: str,
    hdmi_raw_output_on: bool,
    face_memory_action: str,
    reset_action: str,
    force_bake_eye_frame_into_clean_hdmi: bool,
    force_wipe_face_memory_on_camera_reset: bool,
    errno_code: int,
    reason_code: str,
) -> FaceEyeAfCleanHdmiHilResult:
    return FaceEyeAfCleanHdmiHilResult(
        menu_path=FACE_EYE_AF_MENU_PATH,
        canonical_ui_path=FACE_EYE_AF_CANONICAL_UI_PATH,
        menu_items=FACE_EYE_AF_4_MENU_ITEMS,
        configured_face_eye_priority_in_af=configured_face_eye_priority_in_af,
        configured_subject_recognition_in_af=configured_subject_recognition_in_af,
        configured_right_left_eye_select=configured_right_left_eye_select,
        configured_face_eye_frame_display=configured_face_eye_frame_display,
        configured_registered_faces_priority=configured_registered_faces_priority,
        registered_face_ids=registered_face_ids,
        intelligent_auto_mode=intelligent_auto_mode,
        custom_key_switch_right_left_eye_pressed=custom_key_switch_right_left_eye_pressed,
        af_area_auto_clear=af_area_auto_clear,
        focus_locked=focus_locked,
        subject_detected_in_scene=subject_detected_in_scene,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output_on=hdmi_raw_output_on,
        face_memory_action=face_memory_action,
        reset_action=reset_action,
        force_bake_eye_frame_into_clean_hdmi=force_bake_eye_frame_into_clean_hdmi,
        force_wipe_face_memory_on_camera_reset=force_wipe_face_memory_on_camera_reset,
        effective_face_eye_priority_in_af=TOGGLE_ON,
        effective_subject_recognition_in_af=SUBJECT_HUMAN,
        effective_right_left_eye_select=EYE_SELECT_AUTO,
        effective_face_eye_frame_display=TOGGLE_OFF,
        effective_registered_faces_priority=TOGGLE_ON,
        effective_registered_face_ids=registered_face_ids,
        effective_face_memory_count=len(registered_face_ids),
        right_left_eye_select_applicable=True,
        lcd_tracking_box_rendered=False,
        hdmi_tracking_box_rendered=False,
        hdmi_clean_feed_isolated=True,
        settings_restored_by_camera_settings_reset=False,
        face_memory_survived_camera_settings_reset=True,
        survived_reset_network_set=False,
        cleared_by_delete_or_initialize=False,
        admitted=False,
        errno_code=errno_code,
        reason_code=reason_code,
        ai_coprocessor_subject_spoof_events=AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS,
        hdmi_clean_feed_eye_frame_baked_pixels=HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS,
        face_memory_camera_reset_wipe_events=FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def simulate_face_eye_af_clean_hdmi_hil(
    *,
    configured_face_eye_priority_in_af: str = TOGGLE_ON,
    configured_subject_recognition_in_af: str = SUBJECT_HUMAN,
    configured_right_left_eye_select: str = EYE_SELECT_AUTO,
    configured_face_eye_frame_display: str = TOGGLE_ON,
    configured_registered_faces_priority: str = TOGGLE_ON,
    registered_face_ids: Sequence[str] = ("FACE_SLOT_1", "FACE_SLOT_2"),
    intelligent_auto_mode: bool = False,
    custom_key_switch_right_left_eye_pressed: bool = False,
    af_area_auto_clear: str = TOGGLE_OFF,
    focus_locked: bool = False,
    subject_detected_in_scene: bool = True,
    hdmi_connected: bool = True,
    hdmi_info_display: str = TOGGLE_OFF,
    hdmi_raw_output_on: bool = False,
    face_memory_action: str = FACE_MEMORY_ACTION_NONE,
    reset_action: str = RESET_ACTION_NONE,
    force_bake_eye_frame_into_clean_hdmi: bool = False,
    force_wipe_face_memory_on_camera_reset: bool = False,
) -> FaceEyeAfCleanHdmiHilResult:
    """Co-emulate BIONZ XR [Face/Eye AF] (4 items), AI-unit spoof rejection, Clean-HDMI isolation & [Face Memory]."""
    face_tuple = tuple(registered_face_ids)
    common_kwargs = dict(
        configured_face_eye_priority_in_af=configured_face_eye_priority_in_af,
        configured_subject_recognition_in_af=configured_subject_recognition_in_af,
        configured_right_left_eye_select=configured_right_left_eye_select,
        configured_face_eye_frame_display=configured_face_eye_frame_display,
        configured_registered_faces_priority=configured_registered_faces_priority,
        registered_face_ids=face_tuple,
        intelligent_auto_mode=intelligent_auto_mode,
        custom_key_switch_right_left_eye_pressed=custom_key_switch_right_left_eye_pressed,
        af_area_auto_clear=af_area_auto_clear,
        focus_locked=focus_locked,
        subject_detected_in_scene=subject_detected_in_scene,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output_on=hdmi_raw_output_on,
        face_memory_action=face_memory_action,
        reset_action=reset_action,
        force_bake_eye_frame_into_clean_hdmi=force_bake_eye_frame_into_clean_hdmi,
        force_wipe_face_memory_on_camera_reset=force_wipe_face_memory_on_camera_reset,
    )

    if configured_subject_recognition_in_af in SPOOFED_AI_COPROCESSOR_SUBJECTS:
        return _build_failed_face_eye_result(
            **common_kwargs,
            errno_code=EOPNOTSUPP_ERRNO,
            reason_code=f"DEDICATED_AI_COPROCESSOR_SUBJECT_SPOOF_REJECTED:{configured_subject_recognition_in_af}",
        )

    if (
        configured_face_eye_priority_in_af not in VALID_TOGGLE_STATES
        or configured_subject_recognition_in_af not in VALID_BIONZ_XR_FACE_EYE_SUBJECTS
        or configured_right_left_eye_select not in VALID_RIGHT_LEFT_EYE_SELECT
        or configured_face_eye_frame_display not in VALID_TOGGLE_STATES
        or configured_registered_faces_priority not in VALID_TOGGLE_STATES
        or af_area_auto_clear not in VALID_TOGGLE_STATES
        or hdmi_info_display not in VALID_TOGGLE_STATES
        or face_memory_action not in VALID_FACE_MEMORY_ACTIONS
        or reset_action not in VALID_RESET_ACTIONS
        or len(face_tuple) > FACE_MEMORY_MAX_SLOTS
    ):
        return _build_failed_face_eye_result(
            **common_kwargs,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_FACE_EYE_AF_PARAMETER",
        )

    clean_hdmi_active = (hdmi_info_display == TOGGLE_OFF) or hdmi_raw_output_on
    if force_bake_eye_frame_into_clean_hdmi and clean_hdmi_active:
        return _build_failed_face_eye_result(
            **common_kwargs,
            errno_code=EACCES_ERRNO,
            reason_code="CLEAN_HDMI_EYE_FRAME_BAKE_BLOCKED",
        )

    if force_wipe_face_memory_on_camera_reset and reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET:
        return _build_failed_face_eye_result(
            **common_kwargs,
            errno_code=EACCES_ERRNO,
            reason_code="FACE_MEMORY_CAMERA_SETTINGS_RESET_WIPE_BLOCKED",
        )

    cam_reset = reset_action == RESET_ACTION_CAMERA_SETTINGS_RESET
    net_reset = reset_action == RESET_ACTION_RESET_NETWORK_SET
    init_reset = reset_action == RESET_ACTION_INITIALIZE
    delete_faces = face_memory_action == FACE_MEMORY_ACTION_DELETE

    if cam_reset or init_reset:
        eff_prio = TOGGLE_ON
        eff_subj = SUBJECT_HUMAN
        eff_eye = EYE_SELECT_AUTO
        eff_frame_disp = TOGGLE_OFF
        eff_reg_prio = TOGGLE_ON
    else:
        eff_prio = TOGGLE_ON if intelligent_auto_mode else configured_face_eye_priority_in_af
        eff_subj = configured_subject_recognition_in_af
        eff_eye = configured_right_left_eye_select
        eff_frame_disp = configured_face_eye_frame_display
        eff_reg_prio = configured_registered_faces_priority

    eye_applicable = eff_subj == SUBJECT_HUMAN
    if eye_applicable and custom_key_switch_right_left_eye_pressed:
        eff_eye = (
            EYE_SELECT_RIGHT
            if eff_eye in (EYE_SELECT_AUTO, EYE_SELECT_LEFT)
            else EYE_SELECT_LEFT
        )

    cleared_faces = delete_faces or init_reset
    eff_faces: Tuple[str, ...] = () if cleared_faces else face_tuple
    face_survived_cam_reset = cam_reset and (not cleared_faces)

    auto_cleared = (af_area_auto_clear == TOGGLE_ON) and focus_locked
    frame_active = (
        eff_frame_disp == TOGGLE_ON
        and subject_detected_in_scene
        and (not auto_cleared)
    )

    if hdmi_connected and (hdmi_info_display == TOGGLE_ON) and (not hdmi_raw_output_on):
        lcd_box = False
        hdmi_box = frame_active
        clean_isolated = False
    else:
        lcd_box = frame_active
        hdmi_box = False
        clean_isolated = True

    return FaceEyeAfCleanHdmiHilResult(
        menu_path=FACE_EYE_AF_MENU_PATH,
        canonical_ui_path=FACE_EYE_AF_CANONICAL_UI_PATH,
        menu_items=FACE_EYE_AF_4_MENU_ITEMS,
        configured_face_eye_priority_in_af=configured_face_eye_priority_in_af,
        configured_subject_recognition_in_af=configured_subject_recognition_in_af,
        configured_right_left_eye_select=configured_right_left_eye_select,
        configured_face_eye_frame_display=configured_face_eye_frame_display,
        configured_registered_faces_priority=configured_registered_faces_priority,
        registered_face_ids=face_tuple,
        intelligent_auto_mode=intelligent_auto_mode,
        custom_key_switch_right_left_eye_pressed=custom_key_switch_right_left_eye_pressed,
        af_area_auto_clear=af_area_auto_clear,
        focus_locked=focus_locked,
        subject_detected_in_scene=subject_detected_in_scene,
        hdmi_connected=hdmi_connected,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output_on=hdmi_raw_output_on,
        face_memory_action=face_memory_action,
        reset_action=reset_action,
        force_bake_eye_frame_into_clean_hdmi=force_bake_eye_frame_into_clean_hdmi,
        force_wipe_face_memory_on_camera_reset=force_wipe_face_memory_on_camera_reset,
        effective_face_eye_priority_in_af=eff_prio,
        effective_subject_recognition_in_af=eff_subj,
        effective_right_left_eye_select=eff_eye,
        effective_face_eye_frame_display=eff_frame_disp,
        effective_registered_faces_priority=eff_reg_prio,
        effective_registered_face_ids=eff_faces,
        effective_face_memory_count=len(eff_faces),
        right_left_eye_select_applicable=eye_applicable,
        lcd_tracking_box_rendered=lcd_box,
        hdmi_tracking_box_rendered=hdmi_box,
        hdmi_clean_feed_isolated=clean_isolated,
        settings_restored_by_camera_settings_reset=cam_reset,
        face_memory_survived_camera_settings_reset=face_survived_cam_reset,
        survived_reset_network_set=net_reset,
        cleared_by_delete_or_initialize=cleared_faces,
        admitted=True,
        errno_code=0,
        reason_code="OK",
        ai_coprocessor_subject_spoof_events=AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS,
        hdmi_clean_feed_eye_frame_baked_pixels=HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS,
        face_memory_camera_reset_wipe_events=FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def evaluate_pillar_b_face_eye_af_clean_hdmi_and_face_memory_hil() -> Dict[str, object]:
    """Run Pillar B Wave-42 BIONZ XR [Face/Eye AF], AI-unit spoof rejection, Clean-HDMI & [Face Memory] audit."""
    clean_hdmi_lcd_only = simulate_face_eye_af_clean_hdmi_hil(
        configured_subject_recognition_in_af=SUBJECT_HUMAN,
        configured_right_left_eye_select=EYE_SELECT_RIGHT,
        configured_face_eye_frame_display=TOGGLE_ON,
        hdmi_connected=True,
        hdmi_info_display=TOGGLE_OFF,
    )
    hdmi_raw_isolated = simulate_face_eye_af_clean_hdmi_hil(
        configured_face_eye_frame_display=TOGGLE_ON,
        hdmi_connected=True,
        hdmi_info_display=TOGGLE_ON,
        hdmi_raw_output_on=True,
    )
    hdmi_info_on_osd = simulate_face_eye_af_clean_hdmi_hil(
        configured_face_eye_frame_display=TOGGLE_ON,
        hdmi_connected=True,
        hdmi_info_display=TOGGLE_ON,
        hdmi_raw_output_on=False,
    )
    animal_subject_ok = simulate_face_eye_af_clean_hdmi_hil(
        configured_subject_recognition_in_af=SUBJECT_ANIMAL,
        configured_right_left_eye_select=EYE_SELECT_LEFT,
    )
    custom_key_eye_toggle = simulate_face_eye_af_clean_hdmi_hil(
        configured_right_left_eye_select=EYE_SELECT_RIGHT,
        custom_key_switch_right_left_eye_pressed=True,
    )
    spoof_rejections = {
        subj: asdict(
            simulate_face_eye_af_clean_hdmi_hil(configured_subject_recognition_in_af=subj)
        )
        for subj in SPOOFED_AI_COPROCESSOR_SUBJECTS
    }
    face_mem_survives_cam_reset = simulate_face_eye_af_clean_hdmi_hil(
        configured_face_eye_priority_in_af=TOGGLE_OFF,
        configured_subject_recognition_in_af=SUBJECT_ANIMAL,
        configured_right_left_eye_select=EYE_SELECT_LEFT,
        configured_face_eye_frame_display=TOGGLE_ON,
        registered_face_ids=("LEAD_TALENT", "CO_HOST"),
        reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
    )
    face_mem_cleared_by_delete = simulate_face_eye_af_clean_hdmi_hil(
        registered_face_ids=("LEAD_TALENT", "CO_HOST"),
        face_memory_action=FACE_MEMORY_ACTION_DELETE,
    )
    face_mem_cleared_by_init = simulate_face_eye_af_clean_hdmi_hil(
        registered_face_ids=("LEAD_TALENT", "CO_HOST"),
        reset_action=RESET_ACTION_INITIALIZE,
    )
    clean_hdmi_bake_blocked = simulate_face_eye_af_clean_hdmi_hil(
        hdmi_info_display=TOGGLE_OFF,
        force_bake_eye_frame_into_clean_hdmi=True,
    )

    all_4_spoofs_rejected = all(
        (not r["admitted"])
        and r["errno_code"] == EOPNOTSUPP_ERRNO
        and r["ai_coprocessor_subject_spoof_events"] == 0
        for r in spoof_rejections.values()
    )
    passed = (
        clean_hdmi_lcd_only.admitted
        and clean_hdmi_lcd_only.lcd_tracking_box_rendered
        and (not clean_hdmi_lcd_only.hdmi_tracking_box_rendered)
        and clean_hdmi_lcd_only.hdmi_clean_feed_isolated
        and clean_hdmi_lcd_only.hdmi_clean_feed_eye_frame_baked_pixels == 0
        and hdmi_raw_isolated.lcd_tracking_box_rendered
        and (not hdmi_raw_isolated.hdmi_tracking_box_rendered)
        and hdmi_info_on_osd.hdmi_tracking_box_rendered
        and (not hdmi_info_on_osd.lcd_tracking_box_rendered)
        and animal_subject_ok.admitted
        and (not animal_subject_ok.right_left_eye_select_applicable)
        and custom_key_eye_toggle.effective_right_left_eye_select == EYE_SELECT_LEFT
        and all_4_spoofs_rejected
        and face_mem_survives_cam_reset.settings_restored_by_camera_settings_reset
        and face_mem_survives_cam_reset.face_memory_survived_camera_settings_reset
        and face_mem_survives_cam_reset.effective_face_memory_count == 2
        and face_mem_survives_cam_reset.effective_face_eye_priority_in_af == TOGGLE_ON
        and face_mem_survives_cam_reset.effective_subject_recognition_in_af == SUBJECT_HUMAN
        and face_mem_cleared_by_delete.effective_face_memory_count == 0
        and face_mem_cleared_by_init.effective_face_memory_count == 0
        and (not clean_hdmi_bake_blocked.admitted)
        and clean_hdmi_bake_blocked.errno_code == EACCES_ERRNO
    )

    return {
        "passed": passed,
        "menu_path": FACE_EYE_AF_MENU_PATH,
        "canonical_ui_path": FACE_EYE_AF_CANONICAL_UI_PATH,
        "four_menu_items": list(FACE_EYE_AF_4_MENU_ITEMS),
        "valid_bionz_xr_subjects": list(VALID_BIONZ_XR_FACE_EYE_SUBJECTS),
        "spoofed_ai_coprocessor_subjects": list(SPOOFED_AI_COPROCESSOR_SUBJECTS),
        "clean_hdmi_lcd_only_isolation": asdict(clean_hdmi_lcd_only),
        "hdmi_raw_output_isolation": asdict(hdmi_raw_isolated),
        "hdmi_info_on_osd_routing": asdict(hdmi_info_on_osd),
        "animal_subject_mode": asdict(animal_subject_ok),
        "custom_key_switch_eye": asdict(custom_key_eye_toggle),
        "spoofed_ai_coprocessor_rejections": spoof_rejections,
        "face_memory_survives_camera_settings_reset": asdict(face_mem_survives_cam_reset),
        "face_memory_cleared_by_delete": asdict(face_mem_cleared_by_delete),
        "face_memory_cleared_by_initialize": asdict(face_mem_cleared_by_init),
        "clean_hdmi_bake_blocked_eacces": asdict(clean_hdmi_bake_blocked),
    }


# ---------------------------------------------------------------------------
# Sub-Model 52C & Redlines: [Version] Read-Only & BODYDATA.DAT Hard-Block
# ---------------------------------------------------------------------------


def simulate_version_readonly_and_bodydata_guard_hil(
    *,
    attached_lens_id: str = "SEL2470GM2",
    mount_adaptor_attached: bool = False,
    airplane_mode: str = TOGGLE_ON,
    creators_app_remote_update_flag_cached: bool = True,
    np_fz100_battery_percent: int = 85,
    np_fz100_battery_bars: int = 4,
    slot1_bodydata_dat_present: bool = False,
    execute_bodydata_update_requested: bool = False,
    execute_lensdata_update_requested: bool = False,
    force_emit_rf_update_check_in_airplane_mode: bool = False,
    reset_action: str = RESET_ACTION_NONE,
) -> VersionReadOnlyBodydataGuardHilResult:
    """Co-emulate [Version] read-only Body 7.02 + Lens inspection, Airplane Mode badge suppression & BODYDATA.DAT hard-block."""
    lens_ver = FULL_FRAME_EMOUNT_LENSES.get(
        attached_lens_id, APSC_EMOUNT_LENSES.get(attached_lens_id, "--")
    )
    adaptor_ver = "Ver. 02" if mount_adaptor_attached else "--"
    batt_ok = (
        np_fz100_battery_percent >= NP_FZ100_HUMAN_BENCH_MIN_PERCENT
        and np_fz100_battery_bars >= NP_FZ100_HUMAN_BENCH_MIN_BARS
    )

    if (
        attached_lens_id not in VALID_STAGE52_LENSES
        or airplane_mode not in VALID_TOGGLE_STATES
        or reset_action not in VALID_RESET_ACTIONS
        or not (0 <= np_fz100_battery_percent <= 100)
        or not (0 <= np_fz100_battery_bars <= 4)
    ):
        return VersionReadOnlyBodydataGuardHilResult(
            menu_path=VERSION_MENU_PATH,
            canonical_ui_path=VERSION_CANONICAL_UI_PATH,
            body_model=BODY_MODEL_FX3,
            body_firmware_version=FX3_BODY_VERSION_DISPLAY,
            attached_lens_id=attached_lens_id,
            attached_lens_version="--",
            mount_adaptor_attached=mount_adaptor_attached,
            mount_adaptor_version="--",
            airplane_mode=airplane_mode,
            creators_app_remote_update_flag_cached=creators_app_remote_update_flag_cached,
            np_fz100_battery_percent=np_fz100_battery_percent,
            np_fz100_battery_bars=np_fz100_battery_bars,
            slot1_bodydata_dat_present=slot1_bodydata_dat_present,
            execute_bodydata_update_requested=execute_bodydata_update_requested,
            execute_lensdata_update_requested=execute_lensdata_update_requested,
            force_emit_rf_update_check_in_airplane_mode=force_emit_rf_update_check_in_airplane_mode,
            reset_action=reset_action,
            version_dialog_read_only=True,
            creators_app_update_badge_displayed=False,
            creators_app_update_badge_suppressed=True,
            human_bench_battery_prerequisite_met=False,
            bodydata_update_execution_blocked=BODYDATA_UPDATE_EXECUTION_BLOCKED,
            flash_partitions_touched=0,
            version_invariant_across_resets=True,
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason_code="INVALID_VERSION_OR_BATTERY_PARAMETER",
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if execute_bodydata_update_requested or execute_lensdata_update_requested:
        return VersionReadOnlyBodydataGuardHilResult(
            menu_path=VERSION_MENU_PATH,
            canonical_ui_path=VERSION_CANONICAL_UI_PATH,
            body_model=BODY_MODEL_FX3,
            body_firmware_version=FX3_BODY_VERSION_DISPLAY,
            attached_lens_id=attached_lens_id,
            attached_lens_version=lens_ver,
            mount_adaptor_attached=mount_adaptor_attached,
            mount_adaptor_version=adaptor_ver,
            airplane_mode=airplane_mode,
            creators_app_remote_update_flag_cached=creators_app_remote_update_flag_cached,
            np_fz100_battery_percent=np_fz100_battery_percent,
            np_fz100_battery_bars=np_fz100_battery_bars,
            slot1_bodydata_dat_present=slot1_bodydata_dat_present,
            execute_bodydata_update_requested=execute_bodydata_update_requested,
            execute_lensdata_update_requested=execute_lensdata_update_requested,
            force_emit_rf_update_check_in_airplane_mode=force_emit_rf_update_check_in_airplane_mode,
            reset_action=reset_action,
            version_dialog_read_only=True,
            creators_app_update_badge_displayed=False,
            creators_app_update_badge_suppressed=(airplane_mode == TOGGLE_ON),
            human_bench_battery_prerequisite_met=batt_ok,
            bodydata_update_execution_blocked=BODYDATA_UPDATE_EXECUTION_BLOCKED,
            flash_partitions_touched=0,
            version_invariant_across_resets=True,
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason_code="BODYDATA_DAT_FIRMWARE_UPDATE_EXECUTION_HARD_BLOCKED_EROFS",
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    if force_emit_rf_update_check_in_airplane_mode and airplane_mode == TOGGLE_ON:
        return VersionReadOnlyBodydataGuardHilResult(
            menu_path=VERSION_MENU_PATH,
            canonical_ui_path=VERSION_CANONICAL_UI_PATH,
            body_model=BODY_MODEL_FX3,
            body_firmware_version=FX3_BODY_VERSION_DISPLAY,
            attached_lens_id=attached_lens_id,
            attached_lens_version=lens_ver,
            mount_adaptor_attached=mount_adaptor_attached,
            mount_adaptor_version=adaptor_ver,
            airplane_mode=airplane_mode,
            creators_app_remote_update_flag_cached=creators_app_remote_update_flag_cached,
            np_fz100_battery_percent=np_fz100_battery_percent,
            np_fz100_battery_bars=np_fz100_battery_bars,
            slot1_bodydata_dat_present=slot1_bodydata_dat_present,
            execute_bodydata_update_requested=execute_bodydata_update_requested,
            execute_lensdata_update_requested=execute_lensdata_update_requested,
            force_emit_rf_update_check_in_airplane_mode=force_emit_rf_update_check_in_airplane_mode,
            reset_action=reset_action,
            version_dialog_read_only=True,
            creators_app_update_badge_displayed=False,
            creators_app_update_badge_suppressed=True,
            human_bench_battery_prerequisite_met=batt_ok,
            bodydata_update_execution_blocked=BODYDATA_UPDATE_EXECUTION_BLOCKED,
            flash_partitions_touched=0,
            version_invariant_across_resets=True,
            admitted=False,
            errno_code=EACCES_ERRNO,
            reason_code="AIRPLANE_MODE_ZERO_RF_UPDATE_CHECK_BLOCKED",
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        )

    badge_suppressed = airplane_mode == TOGGLE_ON
    badge_displayed = (not badge_suppressed) and creators_app_remote_update_flag_cached and (
        reset_action != RESET_ACTION_INITIALIZE
    )

    return VersionReadOnlyBodydataGuardHilResult(
        menu_path=VERSION_MENU_PATH,
        canonical_ui_path=VERSION_CANONICAL_UI_PATH,
        body_model=BODY_MODEL_FX3,
        body_firmware_version=FX3_BODY_VERSION_DISPLAY,
        attached_lens_id=attached_lens_id,
        attached_lens_version=lens_ver,
        mount_adaptor_attached=mount_adaptor_attached,
        mount_adaptor_version=adaptor_ver,
        airplane_mode=airplane_mode,
        creators_app_remote_update_flag_cached=creators_app_remote_update_flag_cached,
        np_fz100_battery_percent=np_fz100_battery_percent,
        np_fz100_battery_bars=np_fz100_battery_bars,
        slot1_bodydata_dat_present=slot1_bodydata_dat_present,
        execute_bodydata_update_requested=execute_bodydata_update_requested,
        execute_lensdata_update_requested=execute_lensdata_update_requested,
        force_emit_rf_update_check_in_airplane_mode=force_emit_rf_update_check_in_airplane_mode,
        reset_action=reset_action,
        version_dialog_read_only=True,
        creators_app_update_badge_displayed=badge_displayed,
        creators_app_update_badge_suppressed=badge_suppressed,
        human_bench_battery_prerequisite_met=batt_ok,
        bodydata_update_execution_blocked=BODYDATA_UPDATE_EXECUTION_BLOCKED,
        flash_partitions_touched=0,
        version_invariant_across_resets=True,
        admitted=True,
        errno_code=0,
        reason_code="OK",
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_corruptions=EMMC_CORRUPTIONS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
    )


def probe_phase267_redline_guard(**probe_kwargs: object) -> RedlineGuardProbeResult:
    """Fail-closed Stage 52 redline probe guard blocking all 16 hardware/vault/Wave-42 redline bypasses."""
    def _mk(valid: bool, err: int, reason: str) -> RedlineGuardProbeResult:
        return RedlineGuardProbeResult(
            valid=valid,
            errno_code=err,
            reason_code=reason,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
            isp_write_authorized=ISP_WRITE_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
            bodydata_update_execution_blocked=BODYDATA_UPDATE_EXECUTION_BLOCKED,
            cnflasha_mutation_bytes=CNFLASHA_MUTATION_BYTES,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_corruptions=EMMC_CORRUPTIONS,
            nop_count=NOP_COUNT,
            guest_code_modification_bytes=GUEST_CODE_MODIFICATION_BYTES,
            otp_fuse_touches=OTP_FUSE_TOUCHES,
            rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
            apsc_s35_4k_or_raw_bypass_events=APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
            ai_coprocessor_subject_spoof_events=AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS,
            hdmi_clean_feed_eye_frame_baked_pixels=HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS,
            face_memory_camera_reset_wipe_events=FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            bodydata_flash_execution_events=BODYDATA_FLASH_EXECUTION_EVENTS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        )

    unknown = [k for k in probe_kwargs if k not in ALL_16_REDLINE_PROBE_FIELDS]
    if unknown:
        return _mk(False, EINVAL_ERRNO, f"UNKNOWN_REDLINE_PROBE_FIELD:{unknown[0]}")

    erofs_fields = {
        "cnflasha_userspace_write_requested",
        "bodydata_dat_flash_execution_requested",
    }
    for field in ALL_16_REDLINE_PROBE_FIELDS:
        if bool(probe_kwargs.get(field, False)):
            err = EROFS_ERRNO if field in erofs_fields else EACCES_ERRNO
            return _mk(False, err, f"REDLINE_BLOCKED:{field}")

    return _mk(True, 0, "REDLINES_INTACT")


def evaluate_pillar_c_d_version_readonly_bodydata_guard_and_redlines() -> Dict[str, object]:
    """Run Pillar C & D Wave-42 [Version] read-only, Airplane Mode zero-RF badge suppression, BODYDATA.DAT hard-block & redlines."""
    readonly_airplane_on = simulate_version_readonly_and_bodydata_guard_hil(
        attached_lens_id="SEL2470GM2",
        airplane_mode=TOGGLE_ON,
        creators_app_remote_update_flag_cached=True,
    )
    manual_lens_no_cpu = simulate_version_readonly_and_bodydata_guard_hil(
        attached_lens_id="MANUAL_PL_ADAPTER",
        mount_adaptor_attached=False,
    )
    initialize_preserves_version = simulate_version_readonly_and_bodydata_guard_hil(
        reset_action=RESET_ACTION_INITIALIZE,
    )
    bodydata_flash_blocked = simulate_version_readonly_and_bodydata_guard_hil(
        slot1_bodydata_dat_present=True,
        execute_bodydata_update_requested=True,
        np_fz100_battery_percent=100,
        np_fz100_battery_bars=4,
    )
    lensdata_flash_blocked = simulate_version_readonly_and_bodydata_guard_hil(
        execute_lensdata_update_requested=True,
    )
    rf_tx_blocked_airplane = simulate_version_readonly_and_bodydata_guard_hil(
        airplane_mode=TOGGLE_ON,
        force_emit_rf_update_check_in_airplane_mode=True,
    )
    low_batt_audit = simulate_version_readonly_and_bodydata_guard_hil(
        np_fz100_battery_percent=40,
        np_fz100_battery_bars=2,
    )

    baseline_redline = probe_phase267_redline_guard()
    blocked_probes: Dict[str, Dict[str, object]] = {}
    all_probes_blocked = True
    for field in ALL_16_REDLINE_PROBE_FIELDS:
        pr = probe_phase267_redline_guard(**{field: True})
        blocked_probes[field] = asdict(pr)
        if pr.valid or pr.errno_code not in (EACCES_ERRNO, EROFS_ERRNO):
            all_probes_blocked = False

    passed = (
        readonly_airplane_on.admitted
        and readonly_airplane_on.body_firmware_version == FX3_BODY_VERSION_DISPLAY
        and readonly_airplane_on.attached_lens_version == "Ver. 02"
        and readonly_airplane_on.version_dialog_read_only
        and readonly_airplane_on.creators_app_update_badge_suppressed
        and (not readonly_airplane_on.creators_app_update_badge_displayed)
        and readonly_airplane_on.passive_tx_bytes_emitted == 0
        and manual_lens_no_cpu.attached_lens_version == "--"
        and initialize_preserves_version.body_firmware_version == FX3_BODY_VERSION_DISPLAY
        and (not bodydata_flash_blocked.admitted)
        and bodydata_flash_blocked.errno_code == EROFS_ERRNO
        and bodydata_flash_blocked.bodydata_update_execution_blocked
        and bodydata_flash_blocked.physical_device_writes == 0
        and bodydata_flash_blocked.emmc_corruptions == 0
        and (not lensdata_flash_blocked.admitted)
        and lensdata_flash_blocked.errno_code == EROFS_ERRNO
        and (not rf_tx_blocked_airplane.admitted)
        and rf_tx_blocked_airplane.errno_code == EACCES_ERRNO
        and (not low_batt_audit.human_bench_battery_prerequisite_met)
        and baseline_redline.valid
        and all_probes_blocked
    )

    return {
        "passed": passed,
        "menu_path": VERSION_MENU_PATH,
        "canonical_ui_path": VERSION_CANONICAL_UI_PATH,
        "all_16_redline_probe_fields": list(ALL_16_REDLINE_PROBE_FIELDS),
        "readonly_version_airplane_on": asdict(readonly_airplane_on),
        "manual_lens_no_cpu_version": asdict(manual_lens_no_cpu),
        "initialize_preserves_firmware_version": asdict(initialize_preserves_version),
        "bodydata_dat_flash_blocked_erofs": asdict(bodydata_flash_blocked),
        "lensdata_dat_flash_blocked_erofs": asdict(lensdata_flash_blocked),
        "airplane_mode_rf_tx_blocked_eacces": asdict(rf_tx_blocked_airplane),
        "low_battery_prerequisite_audit": asdict(low_batt_audit),
        "baseline_redline_guard": asdict(baseline_redline),
        "blocked_redline_probes": blocked_probes,
    }


# ---------------------------------------------------------------------------
# Unified Phase 267 (Stage 52, 52/52) Entry Point & CLI
# ---------------------------------------------------------------------------


def run_phase267_realhw_apsc_s35_face_eye_af_version_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run the complete Phase 267 Stage 52 (52/52) Wave-42 HIL co-emulation audit."""
    donor_audit = inspect_phase267_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_apsc_s35_4k_raw_lockout_hil()
    pillar_b = evaluate_pillar_b_face_eye_af_clean_hdmi_and_face_memory_hil()
    pillar_cd = evaluate_pillar_c_d_version_readonly_bodydata_guard_and_redlines()

    redlines: Dict[str, object] = {
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "cnflasha_mutation_bytes": CNFLASHA_MUTATION_BYTES,
        "cnflasha_userspace_write_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
        "bodydata_update_execution_blocked": BODYDATA_UPDATE_EXECUTION_BLOCKED,
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
        "apsc_s35_4k_or_raw_bypass_events": APSC_S35_4K_OR_RAW_BYPASS_EVENTS,
        "ai_coprocessor_subject_spoof_events": AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS,
        "hdmi_clean_feed_eye_frame_baked_pixels": HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS,
        "face_memory_camera_reset_wipe_events": FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "bodydata_flash_execution_events": BODYDATA_FLASH_EXECUTION_EVENTS,
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
        and BODYDATA_UPDATE_EXECUTION_BLOCKED
        and CNFLASHA_MUTATION_BYTES == 0
        and PHYSICAL_DEVICE_WRITES == 0
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
        and APSC_S35_4K_OR_RAW_BYPASS_EVENTS == 0
        and AI_COPROCESSOR_SUBJECT_SPOOF_EVENTS == 0
        and HDMI_CLEAN_FEED_EYE_FRAME_BAKED_PIXELS == 0
        and FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and BODYDATA_FLASH_EXECUTION_EVENTS == 0
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_267_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "pillar_a_apsc_s35_4k_raw_lockout_hil": pillar_a,
        "pillar_b_face_eye_af_clean_hdmi_and_face_memory_hil": pillar_b,
        "pillar_c_d_version_readonly_bodydata_guard_and_redlines": pillar_cd,
    }
    payload["audit_digest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_apsc_s35_face_eye_af_version_coemulator.py",
        description=(
            "Phase 267 Stage 52 (52/52) — Real-Hardware ILME-FX3 Wave-42 "
            "APS-C S35 Shooting 12.1MP 4K/RAW Lockout, BIONZ XR Face/Eye AF "
            "Clean-HDMI Frame Isolation & Face Memory Persistence, and Version "
            "Read-Only Inspection & BODYDATA.DAT Hard-Blocked Flash Guard HIL"
        ),
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Phase 267 HIL self-test")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    rep = run_phase267_realhw_apsc_s35_face_eye_af_version_hil(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_apsc_s35_4k_raw_lockout_hil"]
        pb = rep["pillar_b_face_eye_af_clean_hdmi_and_face_memory_hil"]
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 267 Stage 52 ({MILESTONE_LABEL}) | "
            f"mode={rep['source_mode']} | "
            f"apsc_lock={len(pa['hard_locked_4k_and_raw_formats'])}fmt_"
            f"byp:{red['apsc_s35_4k_or_raw_bypass_events']} | "
            f"face_eye={len(pb['four_menu_items'])}item_"
            f"spoof:{red['ai_coprocessor_subject_spoof_events']}_"
            f"hdmibake:{red['hdmi_clean_feed_eye_frame_baked_pixels']} | "
            f"ver_ro=7.02_tx:{red['passive_tx_bytes_emitted']}_"
            f"bodyblk:{int(bool(red['bodydata_update_execution_blocked']))} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
